"""Renbanana (Choco Banana sudoku + German Chocolate + renban bananas) — CP-SAT
candidate generator (#380).

    uv run --with ortools docs/research/renbanana_cpsat.py hunt \
        --objective chocolate --seeds 0-19 --target 4 --limit 120 --out DIR
    uv run --with ortools docs/research/renbanana_cpsat.py bound \
        --objective chocolate --limit 300
    uv run --with ortools docs/research/renbanana_cpsat.py verify DIR/cand_00.json

Rules (`renbanana/FEASIBILITY.md`): normal 9x9 sudoku; a free chocolate/banana
shading that is *not* part of the solution check; every maximal chocolate group
is a rectangle; every maximal banana group is not; orthogonally adjacent
chocolate digits differ by >= 5; every banana group's digits are distinct and
consecutive.

Pipeline — the two known-good stages, never a joint shading+digit search:

- **Stage 1, shadings only.** The chocolate-rectangle rule goes in exactly via
  the lemma "connected + no 2x2 window holding exactly three of the colour <=>
  every group is a rectangle". The banana size cap goes in *structurally* with
  component labels: each banana cell picks a label, adjacent banana cells share
  it, at most 9 cells carry one label. Cutting oversized components one at a
  time instead does not work — 2313 cuts found nothing in 150 s. The
  banana-non-rectangle rule is lazy: solve, find a rectangular banana
  component, forbid exactly that pattern, re-solve.
- **Stage 2/3, digits on a fixed shading.** Sudoku, the whisper on chocolate
  adjacencies, AllDifferent plus max - min == size - 1 per banana group. A
  shading with no digit fill is cut whole and stage 1 continues.

Objectives. `chocolate` (total chocolate cells) and `variety` (distinct
rectangle shapes) live in the shading layer, so stage 1 maximises them.
`circles` (circle-bearing groups weighted by the circle's value) and
`circleable` (count of groups that could carry a circle) depend on digits, so
they are maximised in stage 3 on each fixed shading. Weighting `circles` by
value is deliberate: a plain count optimises into nearly all 1s and 2s (#377).

Diversity is the load-bearing part. Random weights go on the shading *and* the
digits — weights on digits alone converge on one shading with permuted digits
(Zombo seeds 200 and 201 came out identical). A new candidate must differ from
every earlier grid in the batch on *either* Hamming distance >= 12 on the
shading *or* its rectangle-shape multiset. Either-or: requiring both
over-filters and starves the pool.

Nothing enters the pool unverified — every candidate is re-checked from scratch
by `renbanana_verify.py`, written from the rules rather than from this encoding.

# ponytail: research prototype — a shipped generator is a separate decision.
"""

import argparse
import collections
import functools
import gc
import json
import random
import sys
import time
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import renbanana_verify as rv

N = 9
CELLS = [(r, c) for r in range(N) for c in range(N)]
IDX = {p: i for i, p in enumerate(CELLS)}
MAX_BANANA = 9  # a renban group holds distinct consecutive digits, so <= 9 cells
NOISE = 100  # per-variable random weight range for diversity
BIG = 100_000  # objective multiplier: the objective outranks all noise
SHADING_SLICE = 5.0  # seconds for one stage-1 solve inside a seed's budget
DIGIT_SLICE = 30.0  # seconds for one digit solve on a fixed shading
STATUS = {
    cp.OPTIMAL: "optimal",
    cp.FEASIBLE: "feasible",
    cp.INFEASIBLE: "infeasible",
    cp.UNKNOWN: "unknown",
    cp.MODEL_INVALID: "model invalid",
}


def neighbours(r, c):
    return [
        (a, b)
        for a, b in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
        if 0 <= a < N and 0 <= b < N
    ]


ADJACENT = [(p, q) for p in CELLS for q in neighbours(*p) if IDX[q] > IDX[p]]

CATALOGUE = json.loads(
    (Path(__file__).parent / "renbanana" / "rectangle-catalogue.json").read_text()
)


@functools.cache
def circle_cells_at(a, b, ro, co):
    """Which cells of an `a` by `b` rectangle whose top-left sits at box offset
    (ro, co) can hold the digit `a*b` -- straight from the #377 catalogue.

    The catalogue is layer B: the rectangle's own constraints plus the boxes,
    and nothing from the rest of the grid. A real grid only adds constraints,
    so a real circle cell is always one of these. Empty means no digits
    whatever put a circle on that rectangle in that position, which is a fact
    stage 1 can act on instead of stage 3 rediscovering it per shading.
    """
    if max(a, b) > 8:
        return ()
    key, flip = (f"{a}x{b}", False) if a <= b else (f"{b}x{a}", True)
    if flip:  # transposing swaps rows and cols; the 3x3 boxes are symmetric
        ro, co = co, ro
    cells = CATALOGUE[key]["B"].get(f"{ro},{co}", {}).get("circle_cells", [])
    return tuple((c, r) if flip else (r, c) for r, c in cells)


@functools.cache
def support_at(a, b, ro, co):
    """Per-cell digit domains for an `a` by `b` rectangle at box offset
    (ro, co), straight from the #377 catalogue: cell (i, j) may only hold a
    digit that some legal filling puts there.

    Layer B again -- the rectangle and the boxes, nothing outside -- so a real
    grid can only narrow these further and the domains are sound. Handing them
    to the digit stage replaces a search CP-SAT would otherwise redo on every
    shading with an enumeration already on disk.
    """
    if max(a, b) > 8:
        return None
    key, flip = (f"{a}x{b}", False) if a <= b else (f"{b}x{a}", True)
    if flip:
        ro, co = co, ro
    sup = CATALOGUE[key]["B"].get(f"{ro},{co}", {}).get("support")
    if not sup or not sup[0]:
        return None  # absent, or an empty entry: nothing can be filled here
    if flip:  # stored rows are the other orientation's columns
        sup = [[sup[j][i] for j in range(len(sup))] for i in range(len(sup[0]))]
    # Frozen sets, cached: the domains are read once per placement per solve and
    # a membership test should not walk a list. The whole catalogue is a few
    # hundred entries, so the cache never needs evicting.
    return tuple(tuple(frozenset(cell) for cell in row) for row in sup)


@functools.cache
def fillings_at(a, b, ro, co):
    """How many ways an `a` by `b` rectangle at box offset (ro, co) can be
    filled at all, from the same catalogue. Zero means no grid anywhere holds
    that rectangle in that position -- 4x5 and 5x5 are dead at every offset,
    3x3 only at (0,0) -- so stage 1 can rule the placement out instead of
    handing stage 1's answer to a digit solve that must fail.

    A side above 8 is off the catalogue and always zero: a column of an `a` by
    `b` rectangle holds ceil(a/2) cells of one parity class, distinct and drawn
    from a 4-element set, so ceil(a/2) <= 4 and no side exceeds 8.
    """
    if max(a, b) > 8:
        return 0
    key, flip = (f"{a}x{b}", False) if a <= b else (f"{b}x{a}", True)
    if flip:
        ro, co = co, ro
    return CATALOGUE[key]["B"].get(f"{ro},{co}", {}).get("count", 0)


# Rectangle shapes a rectangle can take: no side exceeds 8 (RECTANGLE-CATALOGUE.md,
# the low/high checkerboard bound), and the shape must fit the grid.
# Shapes a rectangle can take: no side exceeds 8, and the #377 catalogue must
# leave it at least one box offset where a filling exists. That drops 2x8 and
# every a x b with a >= 3, b >= 7, along with 4x5, 4x6, 5x5, 5x6 and 6x6 --
# shapes the variety objective would otherwise chase and never place.
SHAPES = [
    (a, b)
    for a in range(1, 9)
    for b in range(1, 9)
    if any(
        CATALOGUE[f"{min(a, b)}x{max(a, b)}"]["B"].get(f"{ro},{co}", {}).get("count", 0)
        for ro in range(3)
        for co in range(3)
    )
]


# ---------------------------------------------------------------- stage 1


class Shadings:
    """The shading-layer model: legal chocolate/banana patterns, digits ignored.

    Exact for the chocolate-rectangle rule and the banana size cap; the
    banana-non-rectangle rule arrives as cuts, each forbidding one genuinely
    illegal pattern. So an INFEASIBLE from this model is a proof, and its
    optimum is a true upper bound on any shading-layer objective.
    """

    def __init__(
        self,
        objective=None,
        rng=None,
        lemmas=True,
        cap=None,
        require_shapes=(),
        require_family=(),
        require_count=1,
        circled=(),
    ):
        m = cp.CpModel()
        self.m = m
        self.choc = {p: m.new_bool_var(f"c{p}") for p in CELLS}
        self.cuts = []

        # Rule 3, exactly: no 2x2 window holds exactly three chocolate cells.
        for r in range(N - 1):
            for c in range(N - 1):
                window = [
                    self.choc[r, c],
                    self.choc[r, c + 1],
                    self.choc[r + 1, c],
                    self.choc[r + 1, c + 1],
                ]
                m.add(sum(window) != 3)

        # Banana size cap, structurally. Each banana cell carries exactly one
        # label; adjacent banana cells share theirs; a label covers <= 9 cells.
        # Labels are restricted to "min cell index in the component", which is
        # always available to every member, so the restriction loses nothing.
        lab = {
            (p, ell): m.new_bool_var(f"l{p}_{ell}")
            for p in CELLS
            for ell in range(IDX[p] + 1)
        }
        for p in CELLS:
            m.add(sum(lab[p, ell] for ell in range(IDX[p] + 1)) == 1 - self.choc[p])
        for p, q in ADJACENT:
            lo, hi = (p, q) if IDX[p] < IDX[q] else (q, p)
            for ell in range(IDX[lo] + 1):
                # both banana and `lo` labelled ell  =>  `hi` labelled ell
                m.add_bool_or(
                    [self.choc[p], self.choc[q], lab[lo, ell].negated(), lab[hi, ell]]
                )
            for ell in range(IDX[lo] + 1, IDX[hi] + 1):
                # a label above `lo`'s index cannot be shared with it
                m.add_bool_or([self.choc[p], self.choc[q], lab[hi, ell].negated()])
        for ell in range(len(CELLS)):
            covering = [lab[p, ell] for p in CELLS if IDX[p] >= ell]
            m.add(sum(covering) <= MAX_BANANA)

        self._forbid_dead_placements()

        if lemmas:
            self._where_the_fives_go()

        if cap is not None:
            m.add(sum(self.choc.values()) <= cap)

        for a, b in require_shapes:
            spots = self._spots(a, b) + ([] if a == b else self._spots(b, a))
            if not spots:
                raise SystemExit(f"shape {a}x{b} cannot fit the grid")
            m.add_bool_or(spots)

        for (a, b), wanted in collections.Counter(circled).items():
            spots = self._spots(a, b, circleable=True)
            if a != b:
                spots += self._spots(b, a, circleable=True)
            if len(spots) < wanted:
                raise SystemExit(f"fewer than {wanted} {a}x{b} spots can be circled")
            m.add(sum(spots) >= wanted)

        if require_family:
            # Distinct maximal components never overlap, so summing one spot
            # per placement counts components. The implication runs one way,
            # so the solver may leave a real component's spot false -- which
            # makes >= a genuine lower bound, never an overcount.
            spots = [
                spot
                for a, b in sorted(set(require_family))
                for spot in self._spots(a, b)
            ]
            if len(spots) < require_count:
                raise SystemExit("that family cannot fit the grid that often")
            m.add(sum(spots) >= require_count)

        self.terms = []
        if objective == "chocolate":
            self.terms.append(BIG * sum(self.choc.values()))
        elif objective == "variety":
            self.terms.append(BIG * sum(self._shape_present()))
        if rng is not None:
            self.terms.append(
                sum(rng.randint(-NOISE, NOISE) * v for v in self.choc.values())
            )
        if self.terms:
            m.maximize(sum(self.terms))

    def _forbid_dead_placements(self):
        """Rule out every maximal chocolate rectangle the #377 catalogue proves
        cannot be filled where it sits.

        Two kinds. A shape dead at layer L -- 2x8, 4x8, 7x7 and the rest --
        cannot be filled anywhere at all. A shape dead only at some box offsets
        -- 3x3 at (0,0), 4x4 at eight of nine, 4x5 and 5x5 and 6x6 everywhere --
        can be filled in the abstract but not in that position mod 3.

        Both are proofs about the rectangle and the boxes alone, so they hold in
        every grid and the model stays exact: an INFEASIBLE here is still a
        proof and the optimum is still a true ceiling. It removes 634 of the
        1936 placements a 9x9 has room for, every one of which used to reach
        the digit stage only to fail there.
        """
        for a in range(1, N + 1):
            for b in range(1, N + 1):
                for r in range(N - a + 1):
                    for c in range(N - b + 1):
                        if fillings_at(a, b, r % 3, c % 3):
                            continue
                        inside = [(r + i, c + j) for i in range(a) for j in range(b)]
                        border = {
                            q for p in inside for q in neighbours(*p) if q not in inside
                        }
                        # not (all inside chocolate and all border banana)
                        self.m.add_bool_or(
                            [self.choc[p].negated() for p in inside]
                            + [self.choc[q] for q in border]
                        )

    def _where_the_fives_go(self):
        """The one digit fact cheap enough to state on the shading alone, and the
        difference between a useful bound and a vacuous one.

        No chocolate group of size >= 2 holds a 5: a chocolate neighbour d needs
        |5 - d| >= 5, so d <= 0 or d >= 10. The nine 5s form a permutation, one
        per row, column and box, and each must land on a banana cell or a lone
        1x1 chocolate cell. Asserting that a legal placement *exists* is implied
        by every real grid, so the model stays a relaxation and its optimum stays
        a true ceiling. Without it the chocolate optimum is 81 — an all-chocolate
        grid is one legal rectangle with no banana groups to break.
        """
        m = self.m
        lone = {}
        for p in CELLS:
            here = m.new_bool_var(f"lone{p}")
            m.add_implication(here, self.choc[p])
            for q in neighbours(*p):
                m.add_implication(here, self.choc[q].negated())
            lone[p] = here
        five = {p: m.new_bool_var(f"five{p}") for p in CELLS}
        for p in CELLS:
            m.add_bool_or([five[p].negated(), self.choc[p].negated(), lone[p]])
        for i in range(N):
            m.add_exactly_one([five[i, c] for c in range(N)])
            m.add_exactly_one([five[r, i] for r in range(N)])
        for br in range(3):
            for bc in range(3):
                m.add_exactly_one(
                    [five[br * 3 + r, bc * 3 + c] for r in range(3) for c in range(3)]
                )

    def _shape_present(self):
        """One bool per rectangle shape, true only if some maximal chocolate
        component really has that shape. Implication one way only: the solver
        cannot claim a shape it has not placed."""
        present = []
        for a, b in SHAPES:
            here = self.m.new_bool_var(f"has{a}x{b}")
            self.m.add_bool_or([here.negated(), *self._spots(a, b)])
            present.append(here)
        return present

    def _spots(self, a, b, circleable=False):
        """One bool per placement of an `a` by `b` maximal chocolate component:
        true only if those cells are chocolate and every bordering cell banana.
        Implication one way only, so a spot is never forced true by the shading.

        `circleable` keeps only the placements the #377 catalogue says can hold
        a circle. A 2x2 whose top-left sits at box offset (0,0) never holds a 4
        whatever the rest of the grid does, so sampling one wastes a whole
        digit solve to learn what is already enumerated.
        """
        spots = []
        for r in range(N - a + 1):
            for c in range(N - b + 1):
                if circleable and not circle_cells_at(a, b, r % 3, c % 3):
                    continue
                inside = [(r + i, c + j) for i in range(a) for j in range(b)]
                border = {q for p in inside for q in neighbours(*p) if q not in inside}
                spot = self.m.new_bool_var(f"p{a}x{b}@{r},{c}")
                for p in inside:
                    self.m.add_implication(spot, self.choc[p])
                for q in border:
                    self.m.add_implication(spot, self.choc[q].negated())
                spots.append(spot)
        return spots

    def forbid_component(self, group):
        """Cut exactly one illegal pattern: these cells banana with a fully
        chocolate border. Valid forever — no legal grid contains it."""
        border = {q for p in group for q in neighbours(*p) if q not in group}
        self.m.add_bool_or(
            [self.choc[p] for p in group] + [self.choc[q].negated() for q in border]
        )
        self.cuts.append(("component", tuple(group)))

    def forbid_shading(self, is_choc):
        """Cut one whole shading — it has no digit fill, or duplicates the pool."""
        self.m.add_bool_or(
            [self.choc[p].negated() if is_choc[p] else self.choc[p] for p in CELLS]
        )
        self.cuts.append(("shading", tuple(p for p in CELLS if is_choc[p])))

    def replay(self, cuts):
        """Re-apply cuts learned on an earlier seed. Every cut forbids a pattern
        no legal grid contains, so it stays valid in any later model — and one
        seed's 120 s is nowhere near the ~40 cut rounds the loop needs from
        cold, so relearning them per seed starves the batch."""
        for kind, cells in cuts:
            if kind == "component":
                self.forbid_component(list(cells))
            else:
                choc = dict.fromkeys(CELLS, False) | dict.fromkeys(cells, True)
                self.forbid_shading(choc)

    def solve(self, seconds, workers):
        s = cp.CpSolver()
        s.parameters.max_time_in_seconds = seconds
        s.parameters.num_workers = workers
        status = s.solve(self.m)
        if status not in (cp.OPTIMAL, cp.FEASIBLE):
            return status, None
        return status, {p: s.value(self.choc[p]) == 1 for p in CELLS}


def legal_shading(model, seconds, workers, log, slice_seconds=None):
    """Stage 1 to a shading that also satisfies the lazy banana-non-rectangle
    rule. Returns (status, shading, cuts) — shading None when none was found.

    `slice_seconds` caps one solve. Random weights make the optimum unprovable,
    so an uncapped solve burns the whole seed budget proving what it already
    found and the cut loop never gets a second round. `bound` leaves it off:
    there the proof is the point.
    """
    deadline = time.monotonic() + seconds
    cuts = 0
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            return cp.UNKNOWN, None, cuts
        if slice_seconds:
            left = min(left, slice_seconds)
        status, is_choc = model.solve(left, workers)
        if is_choc is None:
            return status, None, cuts
        offenders = [g for g in rv.components(is_choc, False) if rv.is_rectangle(g)]
        if not offenders:
            return status, is_choc, cuts
        for g in offenders:
            model.forbid_component(g)
            cuts += 1
        log(f"    stage 1: {len(offenders)} rectangular banana group(s) cut")


# ---------------------------------------------------------------- stage 2/3


def digit_model(is_choc, objective=None, rng=None, circled=()):
    """Digits on a fixed shading: sudoku, the whisper on chocolate adjacencies,
    renban per banana group. Returns (model, digit vars, objective value var).

    `circled` names shapes that must actually carry a circle, e.g. 2x2 -> some
    chocolate 2x2 on this shading holds a 4. That is a digit fact, not a
    shading one, so it cannot be stated in stage 1: forcing the shape there and
    the circle here is what separates "a 2x2 exists" from "a 2x2 is clued".
    """
    m = cp.CpModel()
    d = {p: m.new_int_var(1, 9, f"d{p}") for p in CELLS}
    for i in range(N):
        m.add_all_different([d[i, c] for c in range(N)])
        m.add_all_different([d[r, i] for r in range(N)])
    for br in range(3):
        for bc in range(3):
            m.add_all_different(
                [d[br * 3 + r, bc * 3 + c] for r in range(3) for c in range(3)]
            )

    # The whisper, stated as the checkerboard it forces rather than left for
    # the solver to rediscover on every shading. If a chocolate cell has a
    # chocolate neighbour then |a - b| >= 5 puts one of them at 4 or below and
    # the other at 6 or above, so 5 cannot appear and the classes alternate.
    # A lone 1x1 keeps the full domain, 5 included.
    high = {}
    for p in CELLS:
        if is_choc[p] and any(is_choc[q] for q in neighbours(*p)):
            hi = m.new_bool_var(f"hi{p}")
            m.add(d[p] >= 6).only_enforce_if(hi)
            m.add(d[p] <= 4).only_enforce_if(hi.negated())
            high[p] = hi
    for p, q in ADJACENT:
        if is_choc[p] and is_choc[q]:
            m.add(high[p] != high[q])
            gap = m.new_int_var(-8, 8, f"g{p}{q}")
            m.add(gap == d[p] - d[q])
            abs_gap = m.new_int_var(0, 8, f"a{p}{q}")
            m.add_abs_equality(abs_gap, gap)
            m.add(abs_gap >= 5)

    # Per-cell domains from the catalogue, for every chocolate rectangle.
    for group in rv.components(is_choc, True):
        rows, cols = rv.shape(group)
        r0, c0 = min(group)
        sup = support_at(rows, cols, r0 % 3, c0 % 3)
        if sup is None:
            continue
        for i in range(rows):
            for j in range(cols):
                m.add_allowed_assignments(
                    [d[r0 + i, c0 + j]], [(v,) for v in sup[i][j]]
                )

    for group in rv.components(is_choc, False):
        m.add_all_different([d[p] for p in group])
        lo = m.new_int_var(1, 9, "lo")
        hi = m.new_int_var(1, 9, "hi")
        m.add_min_equality(lo, [d[p] for p in group])
        m.add_max_equality(hi, [d[p] for p in group])
        m.add(hi - lo == len(group) - 1)

    for (a, b), wanted in collections.Counter(circled).items():
        groups = [
            g
            for g in rv.components(is_choc, True)
            if tuple(sorted(rv.shape(g))) == (a, b)
        ]
        if len(groups) < wanted:
            return None, None, None
        # One indicator per group, so asking for two circled 2x3s asks for two
        # different rectangles rather than the same one twice.
        carries = []
        for i, g in enumerate(groups):
            r0, c0 = min(g)
            rows, cols = rv.shape(g)
            picks = []
            for dr, dc in circle_cells_at(rows, cols, r0 % 3, c0 % 3):
                p = (r0 + dr, c0 + dc)
                hit = m.new_bool_var(f"circ{a}x{b}_{i}_{p}")
                m.add(d[p] == len(g)).only_enforce_if(hit)
                picks.append(hit)
            if not picks:
                continue
            here = m.new_bool_var(f"has_circ{a}x{b}_{i}")
            m.add_bool_or([here.negated(), *picks])
            carries.append(here)
        if len(carries) < wanted:
            return None, None, None
        m.add(sum(carries) >= wanted)

    value = None
    terms = []
    if objective in ("circles", "circleable"):
        groups = rv.components(is_choc, True)
        bearing = []
        for group in groups:
            area = len(group)
            rows, cols = rv.shape(group)
            r0, c0 = min(group)
            hits = []
            # Only the catalogue's circle cells can ever hold the area, so the
            # rest are not candidates and never become variables.
            for dr, dc in circle_cells_at(rows, cols, r0 % 3, c0 % 3):
                p = (r0 + dr, c0 + dc)
                hit = m.new_bool_var(f"h{p}")
                m.add(d[p] == area).only_enforce_if(hit)
                m.add(d[p] != area).only_enforce_if(hit.negated())
                hits.append(hit)
            if not hits:  # this rectangle cannot be circled where it sits
                continue
            can = m.new_bool_var(f"can{group[0]}")
            m.add_max_equality(can, hits)
            bearing.append((area, can))
        value = sum(
            (area if objective == "circles" else 1) * can for area, can in bearing
        )
        terms.append(BIG * value)
    if rng is not None:
        for p in CELLS:
            for k in range(1, 10):
                pick = m.new_bool_var(f"n{p}_{k}")
                m.add(d[p] == k).only_enforce_if(pick)
                m.add(d[p] != k).only_enforce_if(pick.negated())
                terms.append(rng.randint(-NOISE, NOISE) * pick)
    if terms:
        m.maximize(sum(terms))
    return m, d, value


def fill_digits(is_choc, seconds, workers, objective=None, rng=None, circled=()):
    """Best digit fill for a fixed shading, or None if the shading admits none."""
    m, d, value = digit_model(is_choc, objective, rng, circled)
    if m is None:  # the shading has no group of a shape a circle was asked of
        return cp.INFEASIBLE, None, None
    s = cp.CpSolver()
    s.parameters.max_time_in_seconds = seconds
    s.parameters.num_workers = workers
    status = s.solve(m)
    if status not in (cp.OPTIMAL, cp.FEASIBLE):
        return status, None, None
    grid = {p: s.value(d[p]) for p in CELLS}
    return status, grid, (s.value(value) if value is not None else None)


# ---------------------------------------------------------------- profiles


def profile(grid, is_choc):
    """The feature profile recorded per candidate."""
    choc_groups = rv.components(is_choc, True)
    shapes = sorted(tuple(sorted(rv.shape(g))) for g in choc_groups)
    circleable = [g for g in choc_groups if any(grid[p] == len(g) for p in g)]
    return {
        "shapes": [f"{a}x{b}" for a, b in shapes],
        "chocolate_cells": sum(1 for p in CELLS if is_choc[p]),
        "chocolate_groups": len(choc_groups),
        "largest_rectangle": max((len(g) for g in choc_groups), default=0),
        "circleable_groups": len(circleable),
        "banana_groups": len(rv.components(is_choc, False)),
    }


def circle_cells(grid, is_choc):
    """One placeable circle per chocolate group that can carry one."""
    out = []
    for group in rv.components(is_choc, True):
        for p in group:
            if grid[p] == len(group):
                out.append(list(p))
                break
    return out


def score(objective, grid, is_choc):
    prof = profile(grid, is_choc)
    if objective == "chocolate":
        return prof["chocolate_cells"]
    if objective == "variety":
        return len(set(prof["shapes"]))
    if objective == "circleable":
        return prof["circleable_groups"]
    if objective == "circles":
        return sum(
            len(g)
            for g in rv.components(is_choc, True)
            if any(grid[p] == len(g) for p in g)
        )
    raise ValueError(objective)


def diverse_enough(is_choc, prof, pool, min_distance):
    """A candidate joins the pool if it differs from every member on *either*
    Hamming distance on the shading *or* the rectangle-shape multiset."""
    for other in pool:
        hamming = sum(
            1 for p in CELLS if is_choc[p] != (other["shading"][p[0]][p[1]] == "C")
        )
        if hamming < min_distance and sorted(prof["shapes"]) == sorted(
            other["profile"]["shapes"]
        ):
            return False
    return True


# ---------------------------------------------------------------- hunt


def as_json(objective, value, seed, grid, is_choc, prof):
    return {
        "objective": objective,
        "value": value,
        "seed": seed,
        "grid": ["".join(str(grid[r, c]) for c in range(N)) for r in range(N)],
        "shading": [
            "".join("C" if is_choc[r, c] else "b" for c in range(N)) for r in range(N)
        ],
        "circles": circle_cells(grid, is_choc),
        "profile": prof,
    }


def hunt(
    objective,
    seeds,
    target,
    limit,
    outdir,
    workers,
    min_distance,
    progress,
    lemmas=True,
    caps=(None,),
    require_shapes=(),
    require_family=(),
    require_count=1,
    circled=(),
):
    """Sample seeds until `target` diverse candidates are found, or seeds run out.

    `caps` descends the objective. Maximising `chocolate` pins every shading at
    the proved ceiling of 50, and a ceiling shading need not admit any digit
    fill — the run then grinds through equally-optimal, equally-unfillable
    patterns. Capping the objective at v walks the search down to where grids
    actually exist, and the first v that yields one is the best value found.
    Every cut is valid at every cap, so the cut set carries across the sweep.
    """
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    pool = []
    learned = []  # cuts carried across seeds; each is valid in every model
    stats = {
        "shadings": 0,
        "digit_feasible": 0,
        "digit_infeasible": 0,
        "diversity_rejected": 0,
        "seeds_run": 0,
        "seconds": 0.0,
    }

    def log(line):
        print(line, flush=True)
        if progress:
            with Path(progress).open("a") as f:
                f.write(line + "\n")

    for cap in caps:
        if len(pool) >= target:
            break
        if cap is not None:
            log(f"== cap {objective} <= {cap}")
        for seed in seeds:
            if len(pool) >= target:
                break
            stats["seeds_run"] += 1
            started = time.monotonic()
            rng = random.Random(seed)
            model = Shadings(
                objective,
                rng,
                lemmas,
                cap,
                require_shapes,
                require_family,
                require_count,
            )
            model.replay(learned)
            model.cuts = []  # replayed cuts are already in `learned`, not new
            deadline = started + limit
            log(f"seed {seed}: start ({objective}, {limit}s)")
            while time.monotonic() < deadline:
                left = deadline - time.monotonic()
                status, is_choc, _ = legal_shading(
                    model, left, workers, log, SHADING_SLICE
                )
                if is_choc is None:
                    log(f"seed {seed}: no further shading ({STATUS[status]})")
                    break
                stats["shadings"] += 1
                layer = (
                    sum(1 for p in CELLS if is_choc[p])
                    if objective == "chocolate"
                    else len(
                        {
                            tuple(sorted(rv.shape(g)))
                            for g in rv.components(is_choc, True)
                        }
                    )
                )
                # Feasibility first, bare: a noise or objective term turns an
                # UNSAT proof into a long optimisation, and "no digit fill" has to
                # be a verdict rather than a timeout. Only a shading that survives
                # gets the second, weighted solve.
                fill_seconds = min(DIGIT_SLICE, max(1.0, deadline - time.monotonic()))
                fill_status, grid, _ = fill_digits(
                    is_choc, fill_seconds, workers, circled=circled
                )
                model.forbid_shading(is_choc)  # this shading is spent either way
                if grid is not None:
                    digit_objective = (
                        objective if objective in ("circles", "circleable") else None
                    )
                    _, better, _ = fill_digits(
                        is_choc,
                        min(DIGIT_SLICE, max(1.0, deadline - time.monotonic())),
                        workers,
                        digit_objective,
                        random.Random(seed ^ 0x5EED),
                        circled,
                    )
                    grid = better or grid
                if grid is None:
                    stats["digit_infeasible"] += 1
                    log(
                        f"seed {seed}: shading {stats['shadings']} "
                        f"(layer {layer}) has no digit fill ({STATUS[fill_status]})"
                    )
                    continue
                stats["digit_feasible"] += 1
                bad = rv.check(grid, is_choc)
                if bad:
                    log(f"seed {seed}: REJECTED by the checker: {bad[0]}")
                    continue
                prof = profile(grid, is_choc)
                if not diverse_enough(is_choc, prof, pool, min_distance):
                    stats["diversity_rejected"] += 1
                    log(
                        f"seed {seed}: shading {stats['shadings']} too close to the pool"
                    )
                    continue
                value = score(objective, grid, is_choc)
                record = as_json(objective, value, seed, grid, is_choc, prof)
                path = out / f"cand_{len(pool):02d}.json"
                path.write_text(json.dumps(record, indent=1))
                pool.append(record)
                log(
                    f"seed {seed}: CANDIDATE {len(pool)}/{target} {objective}={value} "
                    f"shapes={prof['shapes']} -> {path.name}"
                )
                break
            learned.extend(model.cuts)
            del model  # a seed's model is large; do not hold two at once
            gc.collect()
            stats["seconds"] += time.monotonic() - started
            log(
                f"seed {seed}: done in {time.monotonic() - started:.0f}s, "
                f"pool {len(pool)}, {len(learned)} cuts carried"
            )

    (out / "stats.json").write_text(json.dumps(stats, indent=1))
    log(f"BATCH DONE {json.dumps(stats)}")
    return pool, stats


def bound(objective, limit, workers, lemmas=True):
    """Shading-layer-only ceiling: the best `objective` any legal shading reaches,
    digits ignored. Exact, because the shading model is exact plus valid cuts."""
    if objective not in ("chocolate", "variety"):
        print(f"{objective}: no cheap shading-only bound (it depends on digits)")
        return None
    model = Shadings(objective, None, lemmas)
    status, is_choc, cuts = legal_shading(model, limit, workers, print)
    if is_choc is None:
        print(f"bound {objective}: nothing found in {limit}s ({STATUS[status]})")
        return None, False
    best = (
        sum(1 for p in CELLS if is_choc[p])
        if objective == "chocolate"
        else len({tuple(sorted(rv.shape(g))) for g in rv.components(is_choc, True)})
    )
    proven = status == cp.OPTIMAL
    print(
        f"bound {objective}: {best} "
        f"({'proved optimal' if proven else 'best found, not proved'}), {cuts} cuts"
    )
    return best, proven


def parse_family(text):
    """`2xN,3x3` -> every (a, b) it names, both orientations. `N` on one side
    stands for every second side from 2 up that still fits an 8-cell rectangle,
    so `2xN` means a genuinely two-dimensional group, never a 1xN strip."""
    out = set()
    for token in filter(None, text.split(",")):
        lo, hi = token.lower().split("x")
        sides = range(2, 9) if hi == "n" else [int(hi)]
        a = int(lo)
        for b in sides:
            if (a, b) in SHAPES:
                out.add((a, b))
                out.add((b, a))
    return tuple(sorted(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("hunt", help="sample diverse candidates under an objective")
    h.add_argument(
        "--objective",
        required=True,
        choices=["chocolate", "circles", "variety", "circleable"],
    )
    h.add_argument("--seeds", default="0-19", help="inclusive range, e.g. 0-19")
    h.add_argument("--target", type=int, default=4)
    h.add_argument("--limit", type=float, default=120, help="seconds per seed")
    h.add_argument("--out", required=True)
    h.add_argument("--workers", type=int, default=8)
    h.add_argument("--min-distance", type=int, default=12)
    h.add_argument("--progress", default=None)
    h.add_argument(
        "--caps",
        default="",
        help="descending objective caps to sweep, e.g. 50,48,46; empty = uncapped",
    )
    h.add_argument(
        "--require-shape",
        default="",
        help="comma-separated shapes every shading must contain, e.g. 2x4,3x3; "
        "either orientation counts",
    )
    h.add_argument(
        "--circled",
        default="",
        help="shapes that must carry a circle, e.g. 2x2,2x3 -- a 2x2 holding a "
        "4 and a 2x3 holding a 6. Repeat a shape to demand that many distinct "
        "ones (2x3,2x3 = two circled 2x3s). Checked in the digit stage, so "
        "pair it with --require-shape to force the shape itself",
    )
    h.add_argument(
        "--require-family",
        default="",
        help="shape family every shading must draw from, e.g. 2xN,3xN or 2x4; "
        "'N' matches every second side from 2 up, either orientation",
    )
    h.add_argument(
        "--require-count",
        type=int,
        default=1,
        help="how many maximal components --require-family must place",
    )
    h.add_argument(
        "--no-lemmas",
        action="store_true",
        help="drop the 5-placement lemma from the shading model",
    )

    b = sub.add_parser("bound", help="shading-layer-only upper bound")
    b.add_argument(
        "--objective",
        required=True,
        choices=["chocolate", "circles", "variety", "circleable"],
    )
    b.add_argument("--limit", type=float, default=300)
    b.add_argument("--workers", type=int, default=8)
    b.add_argument("--no-lemmas", action="store_true")

    v = sub.add_parser("verify", help="re-check a candidate from scratch")
    v.add_argument("path")

    a = ap.parse_args()
    if a.cmd == "hunt":
        first, last = (int(x) for x in a.seeds.split("-"))
        hunt(
            a.objective,
            range(first, last + 1),
            a.target,
            a.limit,
            a.out,
            min(a.workers, 8),
            a.min_distance,
            a.progress,
            not a.no_lemmas,
            tuple(int(v) for v in a.caps.split(",")) if a.caps else (None,),
            tuple(
                tuple(int(v) for v in s.split("x"))
                for s in a.require_shape.split(",")
                if s
            ),
            parse_family(a.require_family),
            a.require_count,
            tuple(
                tuple(sorted(int(v) for v in s.split("x")))
                for s in a.circled.split(",")
                if s
            ),
        )
    elif a.cmd == "bound":
        bound(a.objective, a.limit, min(a.workers, 8), not a.no_lemmas)
    else:
        grid, is_choc, circles = rv.load(a.path)
        bad = rv.check(grid, is_choc, circles)
        print("\n".join(bad) or "LEGAL")


if __name__ == "__main__":
    main()

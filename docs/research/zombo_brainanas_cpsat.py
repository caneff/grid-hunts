"""Zombo Brainanas (Infections + Choco Banana) — CP-SAT generator prototype.

    uv run --with ortools docs/research/zombo_brainanas_cpsat.py sample 3 [limit] [rect]
    uv run --with ortools docs/research/zombo_brainanas_cpsat.py hunt 0 100 600 outdir [rect] [want] [min_distance]
    uv run --with ortools docs/research/zombo_brainanas_cpsat.py verify out.json
    uv run --with ortools docs/research/zombo_brainanas_cpsat.py strip full.json out.json [seed]

Rules (map #342): normal 9x9 sudoku. Patient zero = digit equal to its box
number, exactly one per row and column, infected. Infected cells infect every
orthogonally adjacent smaller digit, to closure. Zombo: every connected group
of the "rectangle colour" is a rectangle. Brainana: every connected group of
the other colour is not. Cluster: a circled digit equals the size of its own
group. `rect` picks the rectangle colour: 1 = infected groups are rectangles
(the map's rules), 0 = the swap (uninfected chocolate, infected bananas).

Modelling. Digits, infection and closure are exact. The rectangle rule is exact
through the lemma "connected + no 2x2 window with exactly three cells of the
colour <=> rectangle". The non-rectangle rule and a banana circle are enforced
lazily: solve, check, and when a banana component is a rectangle (or a circled
banana has the wrong size) add a cut forbidding exactly that component pattern
(its cells one colour, its orthogonal border the other), then re-solve. Every
cut excludes only invalid solutions, so uniqueness proofs stay exact. A circle
in a rectangle is exact: some rectangle of area == digit around it is the
component. Clued bananas are requested exactly: a library of small
non-rectangular polyominoes (3..MAX_POCKET cells) placed with a full border of
the other colour and a cell whose digit equals the size.

# ponytail: research prototype — the shipped generator is a wayfinder decision.
"""

import contextlib
import ctypes
import gc
import glob
import json
import random
import sys
import threading
from pathlib import Path

from ortools.sat.python import cp_model as cp

N = 9
CELLS = [(r, c) for r in range(N) for c in range(N)]
RECT = 1  # colour whose groups are rectangles: 1 infected, 0 uninfected
CIRCLE_WEIGHT = 10_000  # > the noise range (~2200), so circles come first
WORKERS = 8  # CP-SAT workers per solve; peak memory scales with it


def box(r, c):
    return (r // 3) * 3 + c // 3 + 1


def nb(p):
    r, c = p
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        q = (r + dr, c + dc)
        if 0 <= q[0] < N and 0 <= q[1] < N:
            yield q


def isrect(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return len(cells) == (max(rs) - min(rs) + 1) * (max(cs) - min(cs) + 1)


def rects(max_area=9):
    """Every axis-aligned rectangle of area <= max_area as (cells, border)."""
    out = []
    for h in range(1, 10):
        for w in range(1, 10):
            if h * w > max_area:
                continue
            for r in range(N - h + 1):
                for c in range(N - w + 1):
                    cells = frozenset(
                        (r + i, c + j) for i in range(h) for j in range(w)
                    )
                    border = frozenset(q for p in cells for q in nb(p)) - cells
                    out.append((cells, border))
    return out


def polyominoes(max_size=6):
    """Fixed non-rectangular polyominoes of size 3..max_size, normalised to the origin."""
    shapes = {frozenset([(0, 0)])}
    out = []
    for size in range(2, max_size + 1):
        nxt = set()
        for sh in shapes:
            for r, c in sh:
                for q in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if q in sh:
                        continue
                    grown = sh | {q}
                    mr = min(r for r, _ in grown)
                    mc = min(c for _, c in grown)
                    nxt.add(frozenset((r - mr, c - mc) for r, c in grown))
        shapes = nxt
        if size >= 3:
            out += [sh for sh in shapes if not isrect(sh)]
    return out


MAX_POCKET = 9  # every non-rectangle pocket a real grid can hold; 440k placements


def placements(max_size=MAX_POCKET):
    """Every placement of a pocket shape as (cells, border)."""
    out = []
    for sh in polyominoes(max_size):
        h = max(r for r, _ in sh) + 1
        w = max(c for _, c in sh) + 1
        for r0 in range(N - h + 1):
            for c0 in range(N - w + 1):
                cells = frozenset((r0 + r, c0 + c) for r, c in sh)
                border = frozenset(q for p in cells for q in nb(p)) - cells
                out.append((cells, border))
    return out


RECTS = rects()
ALL_RECTS = rects(81)
POCKETS = placements()
BIG_POCKET_CELLS = (
    None  # hunt CLI: keep 8/9-cell pockets only where they touch these cells
)


def build(
    givens=None,
    circles=None,
    cuts=(),
    seed=0,
    min_pockets=0,
    objective=False,
    avoid=(),
    min_distance=12,
    min_infected=0,
    min_circles=0,
    min_per_box=0,
    min_cross=0,
    big_pocket_cells=None,
    fix_shade=None,
    bonus=None,
    bonus_edges=None,
    pocket_weight=0,
    min_groups=0,
    dots=None,
):
    """The model. givens {cell: digit}; circles {cell: digit or None}.
    dots: None (no dot rule) or the set of dotted edges {frozenset({p, q})}: a
    black dot joins an infected cell and an uninfected neighbour in 1:2 ratio
    (the uninfected one is the double), and every other edge is not such a pair."""
    m = cp.CpModel()
    x = {p: m.NewIntVar(1, 9, f"x{p}") for p in CELLS}
    inf = {p: m.NewBoolVar(f"i{p}") for p in CELLS}
    pz = {p: m.NewBoolVar(f"z{p}") for p in CELLS}
    # rect[p]: p has the rectangle colour; ban[p]: the banana colour
    rect = {p: inf[p] if RECT else inf[p].Not() for p in CELLS}
    ban = {p: rect[p].Not() for p in CELLS}
    for r in range(N):
        m.AddAllDifferent([x[r, c] for c in range(N)])
        m.AddAllDifferent([x[c, r] for c in range(N)])
    for b in range(3):
        for bb in range(3):
            m.AddAllDifferent(
                [
                    x[r, c]
                    for r in range(3 * b, 3 * b + 3)
                    for c in range(3 * bb, 3 * bb + 3)
                ]
            )
    for p in CELLS:
        m.Add(x[p] == box(*p)).OnlyEnforceIf(pz[p])
        m.Add(x[p] != box(*p)).OnlyEnforceIf(pz[p].Not())
        m.AddImplication(pz[p], inf[p])
    for r in range(N):
        m.AddExactlyOne(pz[r, c] for c in range(N))
        m.AddExactlyOne(pz[c, r] for c in range(N))
    # Spread and closure. lt: x[p] < x[q].
    for p in CELLS:
        srcs = []
        for q in nb(p):
            lt = m.NewBoolVar("")
            m.Add(x[p] < x[q]).OnlyEnforceIf(lt)
            m.Add(x[p] > x[q]).OnlyEnforceIf(lt.Not())
            m.AddBoolOr([inf[q].Not(), lt.Not(), inf[p]])  # spread
            s = m.NewBoolVar("")
            m.AddBoolAnd([inf[q], lt]).OnlyEnforceIf(s)
            m.AddBoolOr([inf[q].Not(), lt.Not()]).OnlyEnforceIf(s.Not())
            srcs.append(s)
        m.AddBoolOr([*srcs, pz[p], inf[p].Not()])  # closure: infected needs a source
    # Rectangle rule: no 2x2 window with exactly three rectangle-colour cells.
    for r in range(N - 1):
        for c in range(N - 1):
            m.Add(
                sum([rect[r, c], rect[r + 1, c], rect[r, c + 1], rect[r + 1, c + 1]])
                != 3
            )
    # Banana rule, exact: no banana group is a rectangle. One clause per
    # rectangle (2025 of them): some cell inside is rect-colour or some border
    # cell is banana. Replaces the lazy per-violation cuts, which cost a full
    # re-solve each; only banana circles stay lazy.
    for cells, border in ALL_RECTS:
        m.AddBoolOr([rect[q] for q in cells] + [ban[q] for q in border])
    for p, v in (givens or {}).items():
        m.Add(x[p] == v)
    for p, v in (fix_shade or {}).items():  # template: fix the shading of these cells
        m.Add(inf[p] == v)
    if dots is not None:
        for p in CELLS:
            for q in nb(p):
                if q < p:
                    continue
                for a, b in ((p, q), (q, p)):  # a infected, b not
                    if frozenset((p, q)) in dots:
                        m.Add(inf[a] != inf[b])
                        m.Add(x[b] == 2 * x[a]).OnlyEnforceIf([inf[a], inf[b].Not()])
                    else:
                        m.Add(x[b] != 2 * x[a]).OnlyEnforceIf([inf[a], inf[b].Not()])
    for p, v in (circles or {}).items():
        if v is not None:
            m.Add(x[p] == v)
        # circle in a rectangle: some rectangle of area == digit around p is its group
        opts = []
        for cells, border in RECTS:
            if p not in cells:
                continue
            comp = m.NewBoolVar("")
            m.AddBoolAnd(
                [rect[q] for q in cells] + [ban[q] for q in border]
            ).OnlyEnforceIf(comp)
            m.Add(x[p] == len(cells)).OnlyEnforceIf(comp)
            opts.append(comp)
        m.AddBoolOr([*opts, ban[p]])
    for ban_cells, rect_cells, circle in cuts:
        if circle is None or circle in (circles or {}):
            lits = [rect[q] for q in ban_cells] + [ban[q] for q in rect_cells]
            if circle is not None and (circles or {})[circle] is None:
                # Open circle: the shape may stay if its digit becomes the size.
                e = m.NewBoolVar("")
                m.Add(x[circle] == len(ban_cells)).OnlyEnforceIf(e)
                m.Add(x[circle] != len(ban_cells)).OnlyEnforceIf(e.Not())
                lits.append(e)
            m.AddBoolOr(lits)
    pocket_clue, pocket_at = [], []
    open_circles = [p for p, v in (circles or {}).items() if v is None]
    if min_pockets or open_circles:
        # Clued bananas: a pocket shape, all banana, fully bordered by rectangle
        # colour, holding a cell whose digit equals the pocket size.
        placed = []
        eq = {}  # (cell, digit) -> literal, shared by every placement

        def is_digit(p, k):
            if (p, k) not in eq:
                eq[p, k] = m.NewBoolVar("")
                m.Add(x[p] == k).OnlyEnforceIf(eq[p, k])
                m.Add(x[p] != k).OnlyEnforceIf(eq[p, k].Not())
            return eq[p, k]

        pockets = POCKETS
        if big_pocket_cells is None:
            big_pocket_cells = BIG_POCKET_CELLS
        if big_pocket_cells is not None:
            # Pockets above 7 cells only where a circle there matters.
            pockets = [
                pl for pl in POCKETS if len(pl[0]) <= 7 or pl[0] & big_pocket_cells
            ]
        if not min_pockets:  # open circles only need the shapes through them
            through = frozenset(open_circles)
            pockets = [pl for pl in pockets if pl[0] & through]
        for cells, border in pockets:
            b = m.NewBoolVar("")
            m.AddBoolAnd(
                [ban[q] for q in cells] + [rect[q] for q in border]
            ).OnlyEnforceIf(b)
            m.AddBoolOr([is_digit(p, len(cells)) for p in cells]).OnlyEnforceIf(b)
            placed.append(b)
        if min_pockets:
            m.Add(sum(placed) >= min_pockets)
        # Open circle in a pocket, exact: if p is banana, some placed pocket
        # through p has p's digit as its size. No lazy round needed.
        for p in open_circles:
            opts = []
            for (cells, _), b in zip(pockets, placed, strict=True):
                if p in cells:
                    c = m.NewBoolVar("")
                    m.AddImplication(c, b)
                    m.AddImplication(c, is_digit(p, len(cells)))
                    opts.append(c)
            m.AddBoolOr([*opts, rect[p]])
        if objective or min_per_box:
            # Pocket circles count too: cell p holds k inside a placed k-pocket.
            by_cell = {}
            for (cells, _), b in zip(pockets, placed, strict=True):
                for p in cells:
                    by_cell.setdefault((p, len(cells)), []).append(b)
            for (p, k), bs in by_cell.items():
                c = m.NewBoolVar("")
                m.AddImplication(c, is_digit(p, k))
                m.AddBoolOr(bs).OnlyEnforceIf(c)
                pocket_clue.append(c)
                pocket_at.append(((p, k), c))
    roots = []
    if min_groups or pocket_weight:
        # Exact count of uninfected groups: every uninfected cell carries the
        # label of its group and a distance to the group's one root (label ==
        # own index); a non-root needs a neighbour of the same label one step
        # closer. Labels agree across adjacent uninfected cells, so a group has
        # exactly one root and sum(roots) is the number of groups. ~300 bools:
        # a cardinality over the 200k-placement library blew 16 GB.
        idx = {p: p[0] * N + p[1] for p in CELLS}
        label = {p: m.NewIntVar(0, N * N - 1, "") for p in CELLS}
        dist = {p: m.NewIntVar(0, N * N - 1, "") for p in CELLS}
        for p in CELLS:
            root = m.NewBoolVar("")
            m.AddImplication(root, ban[p])
            m.Add(label[p] == idx[p]).OnlyEnforceIf(root)
            m.Add(dist[p] == 0).OnlyEnforceIf(root)
            parents = []
            for q in nb(p):
                if q > p:  # each edge once: same label when both uninfected
                    m.Add(label[p] == label[q]).OnlyEnforceIf([ban[p], ban[q]])
                par = m.NewBoolVar("")
                m.AddImplication(par, ban[q])
                m.Add(dist[q] == dist[p] - 1).OnlyEnforceIf(par)
                parents.append(par)
            m.AddBoolOr([*parents, root, rect[p]])
            roots.append(root)
        if min_groups:
            m.Add(sum(roots) >= min_groups)
    if objective or min_circles or min_per_box:
        # Circle-able rectangle cells: digit equals the area of the rectangle.
        clue, clue_at = [], []
        for cells, border in RECTS:
            comp = m.NewBoolVar("")
            m.AddBoolAnd(
                [rect[q] for q in cells] + [ban[q] for q in border]
            ).OnlyEnforceIf(comp)
            for p in cells:
                hit = m.NewBoolVar("")
                m.AddImplication(hit, comp)
                m.Add(x[p] == len(cells)).OnlyEnforceIf(hit)
                clue.append(hit)
                clue_at.append(((p, len(cells)), hit))
        m.circle_at = {}  # cell -> bools, one per way the cell can be a circle
        for (p, _), h in clue_at + pocket_at:
            m.circle_at.setdefault(p, []).append(h)
    if min_circles:  # rectangle circles only; pocket circles come on top
        m.Add(sum(clue) >= min_circles)
    if min_per_box:  # spread: box b carries >= min_per_box[b] circles (int = every box)
        if isinstance(min_per_box, int):
            min_per_box = dict.fromkeys(range(1, N + 1), min_per_box)
        by_box = {b: [] for b in range(1, N + 1)}
        for (p, _), h in clue_at:
            by_box[box(*p)].append(h)
        for (p, _), c in pocket_at:
            by_box[box(*p)].append(c)
        for b, k in min_per_box.items():
            m.Add(sum(by_box[b]) >= k)
    if objective:
        # Random weights on digits AND on the shading: without the shading
        # term every seed converged on one shading with permuted digits.
        rng = random.Random(seed)
        noise = sum(rng.randint(0, 3) * x[p] for p in CELLS) + 20 * sum(
            rng.randint(-1, 1) * inf[p] for p in CELLS
        )
        # bonus {cell: weight}: extra objective on infected cells, e.g. chocolate
        # in the upper-left quadrant so boxes 1-2 are not all banana.
        extra = sum(w * inf[p] for p, w in (bonus or {}).items())
        # bonus_edges {(p, q): weight}: reward neighbours of different shading,
        # i.e. many small groups of both colours where deductions live.
        for (p, q), w in (bonus_edges or {}).items():
            d = m.NewBoolVar("")
            m.Add(inf[p] != inf[q]).OnlyEnforceIf(d)
            m.Add(inf[p] == inf[q]).OnlyEnforceIf(d.Not())
            extra += w * d
        if pocket_weight:  # per uninfected group, clued or not
            extra += pocket_weight * sum(roots)
        m.Maximize(CIRCLE_WEIGHT * (sum(clue) + sum(pocket_clue)) + noise + extra)
    for old in avoid:
        # A new shading must differ from each earlier one in >= min_distance cells.
        m.Add(sum(inf[p].Not() if old[p] else inf[p] for p in CELLS) >= min_distance)
    if min_cross:
        # Reach: adjacent infected pairs straddling a box border, i.e. rectangles
        # poking out of their patient zero's box. Known grids score 3-12.
        pairs = []
        for p in CELLS:
            for q in ((p[0] + 1, p[1]), (p[0], p[1] + 1)):
                if q in CELLS and box(*p) != box(*q):
                    both = m.NewBoolVar("")
                    m.AddBoolAnd([inf[p], inf[q]]).OnlyEnforceIf(both)
                    m.AddBoolOr([inf[p].Not(), inf[q].Not()]).OnlyEnforceIf(both.Not())
                    pairs.append(both)
        m.Add(sum(pairs) >= min_cross)
    if min_infected:  # choco/banana balance: bare hunts land at 27-33 infected
        m.Add(sum(inf.values()) >= min_infected)
    return m, x, inf


def comps(shade, val):
    seen, out = set(), []
    for p in CELLS:
        if shade[p] == val and p not in seen:
            st, cur = [p], []
            seen.add(p)
            while st:
                a = st.pop()
                cur.append(a)
                for q in nb(a):
                    if shade[q] == val and q not in seen:
                        seen.add(q)
                        st.append(q)
            out.append(frozenset(cur))
    return out


def violation(sol, shade, circles):
    """A cut (banana cells, rect cells, circle) for the first lazy rule this solution
    breaks, else None. `circle` is the circle the cut depends on (None for a
    rectangle-shaped banana): a cut is only valid while that circle is present."""
    for comp in comps(shade, 1 - RECT):
        border = frozenset(q for p in comp for q in nb(p)) - comp
        if isrect(comp):
            return (comp, border, None)
        for p in comp:
            if p in circles and sol[p] != len(comp):
                return (comp, border, p)
    for comp in comps(shade, RECT):
        assert isrect(comp), "rectangle lemma broken"
    return None


class FirstSolution(cp.CpSolverSolutionCallback):
    """Wall time of the first feasible solution, to tell finding from improving.
    With `stop_at`, halt once the objective reaches that many circles: on seed 5
    the solver found a grid at 173s and then improved it until the 400s limit."""

    def __init__(self, stop_at=0, stall=0):
        super().__init__()
        self.at = None
        self.stop_at = stop_at
        self.stall = stall  # seconds without improvement before giving up
        self.last = None

    def on_solution_callback(self):
        now = self.WallTime()
        if self.at is None:
            self.at = f"{now:.0f}s"
        if self.stop_at and self.ObjectiveValue() >= CIRCLE_WEIGHT * self.stop_at:
            self.StopSearch()
        self.last = now

    def stalled(self):
        return (
            self.stall
            and self.last is not None
            and self.WallTime() - self.last > self.stall
        )


def release_heap():
    """Give freed solver memory back to the OS. CP-SAT frees its model, but
    glibc keeps the pages in the heap: repeated solves in one process grew RSS
    by 0.4-0.8 GB each and died of std::bad_alloc on the fourth (measured with
    the pocket library, 8 workers, 9 GB address-space cap). With this trim RSS
    stays flat at ~1.5 GB across five solves."""
    gc.collect()
    with contextlib.suppress(OSError, AttributeError):  # not glibc
        ctypes.CDLL("libc.so.6").malloc_trim(0)


def solve_with_watchdog(s, m, cb):
    """Solve in a thread; stop when the objective has not improved for cb.stall
    seconds. Half the sampling budget went to proving optimality (seed 701:
    feasible at 178s, OPTIMAL at 489s)."""
    out = {}

    def run():
        out["st"] = s.Solve(m, cb)

    t = threading.Thread(target=run)
    t.start()
    while t.is_alive():
        t.join(1)
        if cb.stalled():
            s.StopSearch()
    return out["st"]


def solve_valid(
    givens=None,
    circles=None,
    cuts=None,
    exclude=(),
    seed=0,
    limit=120,
    min_pockets=0,
    objective=False,
    avoid=(),
    min_distance=12,
    min_infected=0,
    min_circles=0,
    log=None,
    stop_at=11,
    min_per_box=0,
    min_cross=0,
    stall=60,
    fix_shade=None,
    bonus=None,
    bonus_edges=None,
    pocket_weight=0,
    min_groups=0,
    dots=None,
):
    """A valid solution (sol, shade) or None. `exclude`: solutions to forbid. Grows `cuts` in place."""
    cuts = cuts if cuts is not None else []
    circles = circles or {}
    hint = exclude[0] if exclude else None  # uniqueness: search near the known solution
    rounds, first_at = 0, None
    while True:
        rounds += 1
        m, x, inf = build(
            givens,
            circles,
            cuts,
            seed,
            min_pockets,
            objective,
            avoid,
            min_distance,
            min_infected,
            min_circles,
            min_per_box,
            min_cross,
            fix_shade=fix_shade,
            bonus=bonus,
            bonus_edges=bonus_edges,
            pocket_weight=pocket_weight,
            min_groups=min_groups,
            dots=dots,
        )
        for sol in exclude:  # not all cells equal
            diffs = []
            for p, v in sol.items():
                d = m.NewBoolVar("")
                m.Add(x[p] != v).OnlyEnforceIf(d)
                m.Add(x[p] == v).OnlyEnforceIf(d.Not())
                diffs.append(d)
            m.AddBoolOr(diffs)
        if hint:
            for p, v in hint.items():
                m.AddHint(x[p], v)
        s = cp.CpSolver()
        s.parameters.random_seed = seed
        s.parameters.num_workers = WORKERS
        s.parameters.max_time_in_seconds = limit
        cb = FirstSolution(stop_at if objective else 0, stall if objective else 0)
        st = solve_with_watchdog(s, m, cb) if cb.stall else s.Solve(m, cb)
        if first_at is None:
            first_at = cb.at
        if log:
            log(
                f"    round {rounds}: {s.StatusName(st)} in {s.WallTime():.0f}s"
                f" (first feasible {cb.at})"
            )
        ok = st in (cp.OPTIMAL, cp.FEASIBLE)
        name = s.StatusName(st)
        sol = {p: s.Value(x[p]) for p in CELLS} if ok else None
        shade = {p: s.Value(inf[p]) for p in CELLS} if ok else None
        del m, s, cb, x, inf
        release_heap()
        if not ok:
            if st == cp.UNKNOWN and objective:
                return None  # sampling timed out before any feasible grid
            if st == cp.UNKNOWN:
                raise TimeoutError("uniqueness search hit the time limit")
            assert st == cp.INFEASIBLE, f"solver status {name}"
            return None
        cut = violation(sol, shade, circles)
        if cut is None:
            if log:
                log(f"    valid after {rounds} rounds, first feasible {first_at}")
            return sol, shade
        cuts.append(cut)
        hint = sol  # repair the last grid rather than restart


def unique(givens, circles, cuts, limit=300, known=None, dots=None):
    """True iff exactly one valid solution is proved. A time limit counts as
    not proved, so a stripper that trusts this keeps the given: sound, never lean.
    `known`: a solution already in hand, so only the second-solution search runs."""
    try:
        first = known or solve_valid(givens, circles, cuts, limit=limit, dots=dots)[0]
        return (
            solve_valid(givens, circles, cuts, exclude=[first], limit=limit, dots=dots)
            is None
        )
    except TimeoutError:
        return False


def strip(items, keep, test):
    """Greedy batch removal: drop half the remaining items at once, halve the
    batch on failure, and pin an item only when it fails alone. Far fewer
    uniqueness proofs than one-at-a-time when most items are droppable."""
    items = dict(items)
    order = [q for q in items if q not in keep]
    i, k = 0, max(1, len(order) // 2)
    while i < len(order):
        chunk = order[i : i + k]
        trial = {q: v for q, v in items.items() if q not in chunk}
        if test(trial):
            items, i = trial, i + k
        elif k > 1:
            k //= 2
        else:
            i += 1
    return items


def show(sol, shade, givens=None, circles=None):
    rows = []
    for r in range(N):
        cells = []
        for c in range(N):
            p = (r, c)
            d = str(sol[p]) if givens is None or p in givens else "."
            if circles and p in circles:
                d = f"({sol[p]})" if givens is None or p in givens else "( )"
            cells.append(f"{d:>3}{'*' if shade[p] else ' '}")
        rows.append("".join(cells))
    return "\n".join(rows)


def circle_candidates(sol, shade):
    """Cells whose digit equals the size of their own group."""
    out = {}
    for val in (0, 1):
        for comp in comps(shade, val):
            for p in comp:
                if sol[p] == len(comp):
                    out[p] = sol[p]
    return out


def uninfected_groups(shade):
    """Sizes of the uninfected groups (4-connected), largest first."""
    seen, sizes = set(), []
    for p in CELLS:
        if shade[p] or p in seen:
            continue
        stack, n = [p], 0
        seen.add(p)
        while stack:
            q = stack.pop()
            n += 1
            for r in nb(q):
                if not shade[r] and r not in seen:
                    seen.add(r)
                    stack.append(r)
        sizes.append(n)
    return sorted(sizes, reverse=True)


def clued_bananas(sol, shade, circ):
    return [c for c in comps(shade, 1 - RECT) if any(p in circ for p in c)]


def sample(
    seed,
    limit=20,
    min_pockets=0,
    avoid=(),
    min_distance=12,
    min_infected=0,
    log=None,
    min_per_box=0,
    min_cross=0,
):
    """A random valid grid with many circle-able cells and >= min_pockets clued
    bananas, whose shading differs from every shading in `avoid` by >= min_distance cells."""
    return solve_valid(
        seed=seed,
        limit=limit,
        min_pockets=min_pockets,
        objective=True,
        avoid=avoid,
        min_distance=min_distance,
        min_infected=min_infected,
        log=log,
        min_per_box=min_per_box,
        min_cross=min_cross,
    )


def generate(seed, sol, shade, log=print, keep_bananas=True):
    """Strip givens, then circles, while the puzzle stays unique. With
    keep_bananas, a circle in a banana is never dropped: the clued brainanas
    are the point of the puzzle, not a uniqueness aid."""
    rng = random.Random(seed)
    circles = circle_candidates(sol, shade)
    protected = {p for p in circles if shade[p] != RECT} if keep_bananas else set()
    cuts = []
    order = list(CELLS)
    rng.shuffle(order)

    def test_givens(trial):
        ok = unique(trial, circles, cuts, known=sol)
        log(f"  {len(trial)} givens: {'unique' if ok else 'not unique'}")
        return ok

    givens = strip({p: sol[p] for p in order}, set(), test_givens)

    def test_circles(trial):
        ok = unique(givens, trial, cuts, known=sol)
        log(f"  {len(trial)} circles: {'unique' if ok else 'not unique'}")
        return ok

    circles = strip(circles, protected, test_circles)
    assert unique(givens, circles, [], known=sol), (
        "stripped puzzle failed a fresh uniqueness proof"
    )
    return givens, circles


def dump(path, sol, shade, givens, circles):
    Path(path).write_text(
        json.dumps(
            {
                "rect": RECT,
                "grid": ["".join(str(sol[r, c]) for c in range(N)) for r in range(N)],
                "infected": [
                    "".join("*" if shade[r, c] else "." for c in range(N))
                    for r in range(N)
                ],
                "givens": sorted(givens),
                "circles": sorted(circles),
            },
            indent=1,
        )
    )


def hunt(
    first,
    last,
    limit,
    outdir,
    want=2,
    min_distance=12,
    min_infected=0,
    min_per_box=0,
    do_strip=False,
    avoid_glob=None,
    min_cross=0,
):
    """Overnight: sample seeds needing >= `want` clued bananas, strip each hit.
    `avoid_glob`: where to read earlier shadings from before each seed (default:
    this outdir); several arms hunting the same class share one via a glob, or
    two arms converge on the same grid from different noise (seeds 704 and 900)."""
    out = Path(outdir)
    out.mkdir(exist_ok=True)
    progress = out / "PROGRESS.md"

    def log(line):
        with progress.open("a") as fh:
            fh.write(line + "\n")

    def seen():
        files = sorted(
            map(Path, glob.glob(avoid_glob))  # noqa: PTH207 absolute pattern
            if avoid_glob
            else out.glob("full_*.json")
        )
        grids = {}
        for f in files:
            d = json.loads(f.read_text())
            grids["".join(d["infected"])] = {
                p: int(d["infected"][p[0]][p[1]] == "*") for p in CELLS
            }
        return list(grids.values())

    for seed in range(first, last):
        found = sample(
            seed,
            limit,
            min_pockets=want,
            avoid=seen(),
            min_distance=min_distance,
            min_infected=min_infected,
            log=log,
            min_per_box=min_per_box,
            min_cross=min_cross,
        )
        if found is None:
            log(f"seed {seed}: no grid with {want} clued bananas within {limit}s")
            continue
        sol, shade = found
        circ = circle_candidates(sol, shade)
        pockets = clued_bananas(sol, shade, circ)
        log(
            f"seed {seed}: {len(circ)} circles, {len(pockets)} clued bananas"
            f" sizes {sorted(len(c) for c in pockets)}, {sum(shade.values())} infected"
        )
        (out / f"grid_{seed}.txt").write_text(show(sol, shade, circles=circ) + "\n")
        dump(out / f"full_{seed}.json", sol, shade, dict(sol), circ)
        if not do_strip:  # stripping takes hours per grid; sample-only by default
            continue
        givens, circles = generate(seed, sol, shade, log=lambda s: None)
        dump(out / f"puzzle_{seed}.json", sol, shade, givens, circles)
        (out / f"puzzle_{seed}.txt").write_text(
            show(sol, shade, givens, circles) + "\n"
        )
        log(f"  seed {seed}: stripped to {len(givens)} givens, {len(circles)} circles")
    log("HUNT DONE")


def main():
    global RECT
    cmd = sys.argv[1]
    if cmd == "sample":
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        RECT = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        for seed in range(int(sys.argv[2])):
            found = sample(seed, limit)
            if found is None:
                print(f"seed {seed}: no grid within {limit}s")
                continue
            sol, shade = found
            circ = circle_candidates(sol, shade)
            pockets = clued_bananas(sol, shade, circ)
            print(
                f"seed {seed}: rect comps {sorted(len(c) for c in comps(shade, RECT))},"
                f" {len(circ)} circles, {len(pockets)} clued bananas"
            )
            print(show(sol, shade, circles=circ))
    elif cmd == "hunt":
        RECT = int(sys.argv[6]) if len(sys.argv) > 6 else 1
        want = int(sys.argv[7]) if len(sys.argv) > 7 else 2
        dist = int(sys.argv[8]) if len(sys.argv) > 8 else 12
        min_inf = int(sys.argv[9]) if len(sys.argv) > 9 else 0
        per_box = sys.argv[10] if len(sys.argv) > 10 else "0"
        # "1" = every box >= 1; "9:2,1:1" = box 9 >= 2 and box 1 >= 1
        per_box = (
            {int(b): int(k) for b, k in (t.split(":") for t in per_box.split(","))}
            if ":" in per_box
            else int(per_box)
        )
        do_strip = bool(int(sys.argv[11])) if len(sys.argv) > 11 else False
        avoid_glob = sys.argv[12] if len(sys.argv) > 12 else None
        min_cross = int(sys.argv[13]) if len(sys.argv) > 13 else 0
        if len(sys.argv) > 14:  # box number: large pockets only touching that box
            global BIG_POCKET_CELLS
            b = int(sys.argv[14])
            BIG_POCKET_CELLS = frozenset(p for p in CELLS if box(*p) == b)
        hunt(
            int(sys.argv[2]),
            int(sys.argv[3]),
            int(sys.argv[4]),
            sys.argv[5],
            want,
            dist,
            min_inf,
            per_box,
            do_strip,
            avoid_glob,
            min_cross,
        )
    elif cmd == "strip":
        d = json.loads(Path(sys.argv[2]).read_text())
        RECT = d.get("rect", 1)
        sol = {(r, c): int(d["grid"][r][c]) for r, c in CELLS}
        shade = {(r, c): int(d["infected"][r][c] == "*") for r, c in CELLS}
        givens, circles = generate(
            int(sys.argv[4]) if len(sys.argv) > 4 else 0, sol, shade
        )
        dump(sys.argv[3], sol, shade, givens, circles)
        print(show(sol, shade, givens, circles))
        print(f"{len(givens)} givens, {len(circles)} circles -> {sys.argv[3]}")
    elif cmd == "verify":
        d = json.loads(Path(sys.argv[2]).read_text())
        RECT = d.get("rect", 1)
        sol = {(r, c): int(d["grid"][r][c]) for r, c in CELLS}
        givens = {tuple(p): sol[tuple(p)] for p in d["givens"]}
        circles = {tuple(p): sol[tuple(p)] for p in d["circles"]}
        print("unique" if unique(givens, circles, []) else "NOT unique")


if __name__ == "__main__":
    main()

"""Probe: invert the Renbanana pipeline — fix the digits, solve for a shading.

The shading-first pipeline wastes almost everything it does. Across every hunt
in #380 only ~2.7% of legal shadings admit any digit fill, and no shading-layer
constraint we added moved that number. Inverting it makes every candidate
digit-valid by construction, but only if the other direction is not just as
thin. This measures that: of K random solved sudoku grids, how many admit a
legal Renbanana shading at all?

    uv run --with ortools docs/research/renbanana/tools/probe_inverted.py \
        --grids 100 --seconds 20 --workers 1 --out docs/research/renbanana/probe-inverted

One worker by default and one process, ever: this box is shared (AGENTS.md).

Why the model is sharper here than stage 1. With the digits known, the whisper
stops being a digit-stage question and becomes a plain clause — an adjacent
pair differing by less than 5 simply cannot both be chocolate. The renban rule
stops being lazy too: component labels already exist in stage 1 for the size
cap, and with fixed digits a label plus a digit is enough to state both halves
of renban exactly (at most one cell of each digit per label; no gap between two
digits present in a label). Only the banana-non-rectangle rule stays lazy, cut
one pattern at a time exactly as stage 1 does.

So an INFEASIBLE from this model is a proof: that solved grid carries no legal
Renbanana shading at all.
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import renbanana_cpsat as rc
import renbanana_verify as rv

N = 9
CELLS = [(r, c) for r in range(N) for c in range(N)]
IDX = {p: i for i, p in enumerate(CELLS)}
ADJACENT = [(p, q) for p in CELLS for q in rv.neighbours(*p) if IDX[q] > IDX[p]]


def random_grid(seed, seconds, workers, steer=0):
    """A solved sudoku, steered somewhere random by hinting every cell.

    Hints rather than a random objective: the objective makes CP-SAT prove an
    optimum we do not care about, while a hint costs nothing and still lands
    the search in a different corner each seed.

    `steer` demands at least that many whisper-legal adjacencies -- orthogonal
    pairs differing by 5 or more. Those pairs are the only places two chocolate
    cells may touch, so they are the raw material every chocolate rectangle
    above 1x1 is built from. A uniform random grid has about 37 of them and the
    23 grids we know are legal average 49, ranges barely overlapping, so the
    uniform sample is simply the wrong population to draw from.
    """
    rng = random.Random(seed)
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
    if steer:
        far = []
        for p, q in ADJACENT:
            v = m.new_bool_var(f"far{p}{q}")
            gap = m.new_int_var(-8, 8, f"gap{p}{q}")
            m.add(gap == d[p] - d[q])
            far_abs = m.new_int_var(0, 8, f"abs{p}{q}")
            m.add_abs_equality(far_abs, gap)
            m.add(far_abs >= 5).only_enforce_if(v)
            m.add(far_abs <= 4).only_enforce_if(v.negated())
            far.append(v)
        m.add(sum(far) >= steer)
    for p in CELLS:
        m.add_hint(d[p], rng.randint(1, 9))
    s = cp.CpSolver()
    s.parameters.max_time_in_seconds = seconds
    s.parameters.num_workers = workers
    s.parameters.random_seed = seed
    if s.solve(m) not in (cp.OPTIMAL, cp.FEASIBLE):
        return None
    return {p: s.value(d[p]) for p in CELLS}


class Shadings:
    """Legal shadings of one *fixed* solved grid. Exact but for rule 4."""

    def __init__(self, grid, min_chocolate=0, drop="none", want_circled=0):
        m = cp.CpModel()
        self.m = m
        self.grid = grid
        self.drop = drop
        self.choc = {p: m.new_bool_var(f"c{p}") for p in CELLS}

        # Rule 3: no 2x2 window holds exactly three chocolate cells.
        for r in range(N - 1):
            for c in range(N - 1):
                m.add(
                    sum(self.choc[r + i, c + j] for i in range(2) for j in range(2))
                    != 3
                )

        # Rule 5, now a plain clause: this pair cannot both be chocolate.
        for p, q in [] if drop == "whisper" else ADJACENT:
            if abs(grid[p] - grid[q]) < 5:
                m.add_bool_or([self.choc[p].negated(), self.choc[q].negated()])

        # Component labels for the banana groups, as in stage 1: every banana
        # cell carries exactly one label, adjacent banana cells share it, and a
        # label is the least cell index in its component.
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
                m.add_bool_or(
                    [self.choc[p], self.choc[q], lab[lo, ell].negated(), lab[hi, ell]]
                )
            for ell in range(IDX[lo] + 1, IDX[hi] + 1):
                m.add_bool_or([self.choc[p], self.choc[q], lab[hi, ell].negated()])

        # Pin each label to be *exactly* its component's least cell index, not
        # merely at most it. Without this a label is only bounded above, so two
        # disjoint components can both claim a label below both their minimums
        # and renban then lands on their union -- a gap in one component
        # plugged by a digit from the other. Requiring that whoever uses label
        # `ell` shares it with the cell whose index *is* `ell` closes that: the
        # owner cell lies in exactly one component, so no second component can
        # claim the label. It rules no legal grid out, since a component can
        # always take its own least index.
        for ell in range(len(CELLS)):
            owner = CELLS[ell]
            for p in CELLS:
                if IDX[p] >= ell and p != owner:
                    m.add_implication(lab[p, ell], lab[owner, ell])

        # Rule 6 as a strong filter, not as the last word. Per label: at most
        # one cell of each digit (distinct), and no digit missing between two
        # that are present (consecutive).
        #
        # Not exact, because a label is only pinned to be *at most* the least
        # cell index in its component, so two disjoint components may pick the
        # same label. Renban then lands on their union, and a gap in one
        # component can be plugged by a digit from the other -- which is how a
        # banana group holding 1, 4 and 8 once came back as legal. It never
        # rules a legal shading out (the solver can always give each component
        # its own least index), so an INFEASIBLE is still a proof; it just lets
        # some illegal ones through. `solve` catches those and cuts them.
        for ell in range(len(CELLS)):
            members = [p for p in CELLS if IDX[p] >= ell]
            here = {}
            for v in range(1, 10):
                same = [lab[p, ell] for p in members if grid[p] == v]
                if not same:
                    continue
                if drop != "renban-distinct":
                    m.add(sum(same) <= 1)
                seen = m.new_bool_var(f"v{ell}_{v}")
                m.add(sum(same) == 1).only_enforce_if(seen)
                m.add(sum(same) == 0).only_enforce_if(seen.negated())
                here[v] = seen
            for v in here:
                for u in here:
                    for w in here:
                        if u < v < w and drop != "renban-consecutive":
                            m.add_bool_or(
                                [here[u].negated(), here[w].negated(), here[v]]
                            )

        if min_chocolate:
            m.add(sum(self.choc.values()) >= min_chocolate)

        self._forbid_dead_placements()
        self.impossible = False
        if want_circled:
            self._require_circled(want_circled)
        self.cuts = 0

    def circled_placements(self):
        """Every rectangle this grid could hold that would carry a circle.

        A group of `k` cells carries a circle when one of its cells holds the
        digit `k`, so a rectangle only counts if some cell of it holds `a*b`
        *and* the catalogue allows a circle on that cell at that box offset.
        Both halves come off the #377 catalogue plus this grid's digits, so the
        list is settled before the solver sees the model -- and a grid whose
        list is too short is refused without a solve at all.

        Only rectangles with both sides at least 2: a 1xk group's circle is a
        different (and much commoner) thing, and the shapes worth hunting are
        the ones the pool has never held two of.
        """
        out = []
        for a in range(2, N + 1):
            for b in range(2, N + 1):
                if max(a, b) > 8:
                    continue
                for r0 in range(N - a + 1):
                    for c0 in range(N - b + 1):
                        if self._is_dead(a, b, r0, c0):
                            continue
                        sites = rc.circle_cells_at(a, b, r0 % 3, c0 % 3)
                        if any(self.grid[r0 + i, c0 + j] == a * b for i, j in sites):
                            out.append((a, b, r0, c0))
        return out

    def _require_circled(self, want):
        """Demand `want` maximal chocolate rectangles that each carry a circle.

        One bool per surviving placement, meaning "this exact rectangle is a
        maximal chocolate group": every cell inside chocolate, every bordering
        cell banana. Two such rectangles cannot overlap -- a shared cell would
        sit inside one and on the other's banana border -- so demanding two
        selected placements is already demanding two disjoint ones, with no
        pairwise clause to write.
        """
        places = self.circled_placements()
        self.circled_sites = len(places)
        if len(places) < want:
            # Fewer candidate rectangles than the objective needs: the grid is
            # refused here, from the catalogue, without a solve.
            self.impossible = True
            return
        sel = []
        for a, b, r0, c0 in places:
            inside = [(r0 + i, c0 + j) for i in range(a) for j in range(b)]
            border = {
                q for p in inside for q in rv.neighbours(*p) if q not in set(inside)
            }
            v = self.m.new_bool_var(f"circ{a}x{b}@{r0},{c0}")
            for p in inside:
                self.m.add_implication(v, self.choc[p])
            for q in border:
                self.m.add_implication(v, self.choc[q].negated())
            sel.append(v)
        self.m.add(sum(sel) >= want)

    def _forbid_dead_placements(self):
        """Rule out every maximal chocolate rectangle the #377 catalogue proves
        cannot exist here, before the solver looks at one.

        Three kinds, all read straight off the catalogue rather than searched
        for again on every solve:

        - a shape with no legal filling anywhere (2x8, 4x8, 7x7 and the rest);
        - a shape with no legal filling at *this* box offset (3x3 at (0,0), 4x4
          at eight of nine, and so on);
        - a placement whose actual digits fall outside the per-cell support the
          catalogue records for that shape at that offset.

        The first two are facts about the rectangle and the boxes alone, so they
        hold in any grid. The third is this grid's digits checked against the
        enumeration. A dead placement is forbidden as a *maximal* rectangle:
        every cell chocolate with a wholly banana border.
        """
        self.dead = 0
        for a in range(1, N + 1):
            for b in range(1, N + 1):
                sup = rc.support_at(a, b, 0, 0) if max(a, b) <= 8 else None
                for r0 in range(N - a + 1):
                    for c0 in range(N - b + 1):
                        if not self._is_dead(a, b, r0, c0):
                            continue
                        inside = [(r0 + i, c0 + j) for i in range(a) for j in range(b)]
                        border = {
                            q
                            for p in inside
                            for q in rv.neighbours(*p)
                            if q not in set(inside)
                        }
                        self.m.add_bool_or(
                            [self.choc[p].negated() for p in inside]
                            + [self.choc[q] for q in border]
                        )
                        self.dead += 1
        del sup

    def _is_dead(self, a, b, r0, c0):
        """True when the catalogue says this placement cannot be filled."""
        if max(a, b) > 8:
            return True  # no side above 8 survives the parity bound
        sup = rc.support_at(a, b, r0 % 3, c0 % 3)
        if sup is None:
            return True  # dead shape, or dead at this box offset
        if len(sup) != a or len(sup[0]) != b:
            return False  # catalogue orientation not usable here; leave it be
        return any(
            self.grid[r0 + i, c0 + j] not in sup[i][j]
            for i in range(a)
            for j in range(b)
        )

    def forbid_component(self, group):
        border = {q for p in group for q in rv.neighbours(*p) if q not in group}
        self.m.add_bool_or(
            [self.choc[p] for p in group] + [self.choc[q].negated() for q in border]
        )
        self.cuts += 1

    def offenders(self, is_choc):
        """Banana groups this shading may not contain, each cut one at a time.

        Rule 4 -- a rectangular banana group -- was always lazy. Rule 6 joins
        it because the label encoding above is a filter rather than a proof:
        two components sharing a label can satisfy it while one of them is not
        a renban at all. Both kinds of cut forbid one pattern that no legal
        grid contains, so both stay valid for the life of the model, and the
        loop returns only a shading that survives every rule.
        """
        bad = []
        for g in rv.components(is_choc, False):
            if rv.is_rectangle(g) and self.drop != "non-rectangle":
                bad.append(g)
                continue
            digits = [self.grid[p] for p in g]
            if len(set(digits)) != len(digits):
                if self.drop != "renban-distinct":
                    bad.append(g)
            elif (
                max(digits) - min(digits) != len(digits) - 1
                and self.drop != "renban-consecutive"
            ):
                bad.append(g)
        return bad

    def solve(self, seconds, workers, seed):
        """Loop the lazy rule-4 cuts until the shading is clean or time runs out."""
        if self.impossible:
            return cp.INFEASIBLE, None
        deadline = time.monotonic() + seconds
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return cp.UNKNOWN, None
            s = cp.CpSolver()
            s.parameters.max_time_in_seconds = left
            s.parameters.num_workers = workers
            s.parameters.random_seed = seed
            status = s.solve(self.m)
            if status not in (cp.OPTIMAL, cp.FEASIBLE):
                return status, None
            is_choc = {p: s.value(self.choc[p]) == 1 for p in CELLS}
            bad = self.offenders(is_choc)
            if not bad:
                return status, is_choc
            for g in bad:
                self.forbid_component(g)


def profile(is_choc):
    shapes = sorted(rv.shape(g) for g in rv.components(is_choc, True))
    return {
        "chocolate": sum(is_choc.values()),
        "groups": len(shapes),
        "shapes": ["x".join(map(str, s)) for s in shapes],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grids", type=int, default=100)
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--min-chocolate", type=int, default=0)
    ap.add_argument("--steer", type=int, default=0)
    ap.add_argument(
        "--want-circled",
        type=int,
        default=0,
        help="demand this many maximal chocolate rectangles (both sides >= 2) "
        "that each carry a circle; 2 is the thing no pool grid holds",
    )
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument(
        "--grids-from",
        type=Path,
        help="JSONL of grids to test instead of generating them; each row "
        "carries a `grid` of nine digit strings. Rows are taken every "
        "--stride starting at --start, so N processes shard one file.",
    )
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    a.out.mkdir(parents=True, exist_ok=True)
    log = a.out / "probe.jsonl"
    tally = {"feasible": 0, "infeasible": 0, "unknown": 0}
    refused = 0
    began = time.monotonic()

    if a.grids_from:
        supplied = [
            json.loads(line)["grid"]
            for line in a.grids_from.read_text().splitlines()
            if line.strip()
        ]
        # De-duplicated: the pair count writes one witness per geometry and the
        # same solved grid answers many of them.
        supplied = list(dict.fromkeys(tuple(g) for g in supplied))
        work = list(enumerate(supplied))[a.start :: a.stride][: a.grids]
        log = a.out / f"probe-{a.start}.jsonl"
    else:
        work = [(s, None) for s in range(a.start, a.start + a.grids)]

    for done, (seed, supplied_grid) in enumerate(work, 1):
        if supplied_grid is not None:
            grid = {
                (r, c): int(supplied_grid[r][c]) for r in range(N) for c in range(N)
            }
        else:
            grid = random_grid(seed, 30.0, a.workers, a.steer)
        if grid is None:
            print(f"seed {seed}: no grid at steer >= {a.steer}", flush=True)
            continue
        model = Shadings(grid, a.min_chocolate, want_circled=a.want_circled)
        t0 = time.monotonic()
        status, is_choc = model.solve(a.seconds, a.workers, seed)
        took = time.monotonic() - t0

        row = {
            "seed": seed,
            "status": cp.CpSolver().status_name(status).lower(),
            "seconds": round(took, 1),
            "cuts": model.cuts,
        }
        if a.want_circled:
            row["circled_sites"] = getattr(model, "circled_sites", 0)
            row["refused_before_solve"] = model.impossible
            refused += model.impossible
        if is_choc is not None:
            tally["feasible"] += 1
            row["profile"] = profile(is_choc)
            row["grid"] = ["".join(str(grid[r, c]) for c in range(N)) for r in range(N)]
            row["shading"] = [
                "".join("C" if is_choc[r, c] else "b" for c in range(N))
                for r in range(N)
            ]
            bad = rv.check(grid, is_choc)
            row["verified"] = not bad
            if bad:
                row["violations"] = bad[:5]
            else:
                # A grid that clears every rule is written where the rest of
                # the tooling reads candidates, not left inside a probe log.
                # Shards share the directory, so the file name carries the
                # shard as well as the count.
                keep = a.out / f"cand_{a.start:03d}_{tally['feasible'] - 1:03d}.json"
                keep.write_text(
                    json.dumps(
                        {
                            "objective": f"want-circled-{a.want_circled}"
                            if a.want_circled
                            else "inverted",
                            "value": len(rc.circle_cells(grid, is_choc)),
                            "seed": f"inverted+{seed}",
                            "grid": row["grid"],
                            "shading": row["shading"],
                            "circles": rc.circle_cells(grid, is_choc),
                            "profile": rc.profile(grid, is_choc),
                        },
                        indent=1,
                    )
                    + "\n"
                )
        elif status == cp.INFEASIBLE:
            tally["infeasible"] += 1
        else:
            tally["unknown"] += 1

        with log.open("a") as f:
            f.write(json.dumps(row) + "\n")
        print(
            f"seed {seed}: {row['status']} in {row['seconds']}s "
            f"({model.cuts} cuts) — {tally['feasible']}/{done} feasible",
            flush=True,
        )

    total = sum(tally.values())
    print(
        f"\n{tally['feasible']}/{total} grids admit a legal shading "
        f"({100 * tally['feasible'] / max(total, 1):.0f}%); "
        f"{tally['infeasible']} proved impossible "
        f"({refused} refused from the catalogue before any solve), "
        f"{tally['unknown']} timed out; "
        f"{time.monotonic() - began:.0f}s total",
        flush=True,
    )


if __name__ == "__main__":
    main()

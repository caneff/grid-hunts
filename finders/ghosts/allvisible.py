"""Ghosts, all visible: the ghost digits alone make the sudoku unique.

    uv run finders/ghosts/allvisible.py --seed 1 --seconds 600 --out DIR

Every ghost is shown with its digit, and those digits are the only givens. A
ghost's digit is its ghost-neighbour count, so a ghost shape plus the grid fix
the givens. One ghost must hold 8. Uniqueness is plain sudoku uniqueness of
those givens: hidden ghosts, if the rules allowed them, only add constraints.

CEGAR over grid and shape together (fixing the grid first leaves 1-13 shapes,
see 2026-09-15-ghosts-all-visible.md):
  master  digits x, ghosts g; g ⇒ Σ g(neighbours) = digit; some ghost holds 8;
          necessary conditions for a unique sudoku (≥ 17 givens, digits 1-8
          all given, ≤ 1 ghost-free row per band and column per stack);
          one cut per counterexample; Σ g ≤ bound.
  check   sudoku with the ghost digits given and the master grid forbidden,
          fewest cells changed. A second grid Y cuts every (grid, shape) that
          Y also satisfies: OR over cells of (g[c] ∧ digit[c] ≠ Y[c]).
A unique shape tightens the bound to |shape| - 1; cuts stay valid.
"""

import argparse
import json
import random
import time
from pathlib import Path

from ortools.sat.python import cp_model

N = 9
CELLS = [(r, c) for r in range(N) for c in range(N)]
BANDS = [range(3), range(3, 6), range(6, 9)]


def neighbours(r, c):
    return [
        (r + a, c + b)
        for a in (-1, 0, 1)
        for b in (-1, 0, 1)
        if (a or b) and 0 <= r + a < N and 0 <= c + b < N
    ]


def shares_house(p, q):
    return (
        p[0] == q[0]
        or p[1] == q[1]
        or (p[0] // 3 == q[0] // 3 and p[1] // 3 == q[1] // 3)
    )


def line_pairs():
    """Two rows of one band, or two columns of one stack, as aligned cell lists."""
    for a in range(N):
        for b in range(a + 1, N):
            if a // 3 == b // 3:
                yield [(a, i) for i in range(N)], [(b, i) for i in range(N)]
                yield [(i, a) for i in range(N)], [(i, b) for i in range(N)]


def sudoku(m):
    x = {cell: [m.new_bool_var(f"x{cell}{d}") for d in range(1, 10)] for cell in CELLS}
    for cell in CELLS:
        m.add_exactly_one(x[cell])
    for d in range(9):
        for i in range(N):
            m.add_exactly_one(x[i, c][d] for c in range(N))
            m.add_exactly_one(x[r, i][d] for r in range(N))
        for br in (0, 3, 6):
            for bc in (0, 3, 6):
                m.add_exactly_one(
                    x[br + a, bc + b][d] for a in range(3) for b in range(3)
                )
    return x


def solver(seed, limit):
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.random_seed = seed
    s.parameters.max_time_in_seconds = limit
    return s


def digits_of(s, x):
    return {
        cell: next(d + 1 for d in range(9) if s.value(x[cell][d])) for cell in CELLS
    }


class Master:
    def __init__(self, rng, min_ghosts):
        self.m = m = cp_model.CpModel()
        self.x = x = sudoku(m)
        self.g = g = {cell: m.new_bool_var(f"g{cell}") for cell in CELLS}
        for r, c in CELLS:
            digit = sum((d + 1) * x[r, c][d] for d in range(9))
            m.add(sum(g[n] for n in neighbours(r, c)) == digit).only_enforce_if(g[r, c])
        # on[c][d]: cell c is a ghost holding digit d+1
        self.on = on = {}
        for cell in CELLS:
            on[cell] = []
            for d in range(9):
                v = m.new_bool_var(f"on{cell}{d}")
                m.add_implication(v, g[cell])
                m.add_implication(v, x[cell][d])
                m.add_bool_or([v, g[cell].Not(), x[cell][d].Not()])
                on[cell].append(v)
        for d in range(8):  # digits 1-8 each given at least once
            m.add_bool_or([on[cell][d] for cell in CELLS])
        m.add_bool_or([on[cell][7] for cell in CELLS])  # an 8-ghost (already implied)
        self.size = sum(g.values())
        m.add(self.size >= min_ghosts)
        for band in BANDS:  # ≤ 1 ghost-free row per band, column per stack
            rows_hit = []
            cols_hit = []
            for i in band:
                rh = m.new_bool_var(f"rh{i}")
                m.add_bool_or([g[i, c] for c in range(N)]).only_enforce_if(rh)
                rows_hit.append(rh)
                ch = m.new_bool_var(f"ch{i}")
                m.add_bool_or([g[r, i] for r in range(N)]).only_enforce_if(ch)
                cols_hit.append(ch)
            m.add(sum(rows_hit) >= 2)
            m.add(sum(cols_hit) >= 2)
        # Two-line cycles. Two rows of one band hold the same digits, so column c
        # links to the column c' where row r1 holds row r2's digit at c. A cycle
        # of links with no ghost in either row can rotate: a second solution.
        # (Length 2 is the deadly rectangle; lengths 3+ were the 6-cell
        # counterexamples.) Forbid it with a rank that strictly drops along every
        # ghost-free link. Same for two columns of one stack.
        for line_a, line_b in line_pairs():
            h = [m.new_int_var(0, N - 1, "h") for _ in range(N)]
            for i in range(N):
                free = [g[line_a[i]].Not(), g[line_b[i]].Not()]
                for j in range(N):
                    if i == j:
                        continue
                    for d in range(9):
                        m.add(h[j] < h[i]).only_enforce_if(
                            [*free, x[line_b[i]][d], x[line_a[j]][d]]
                        )
        # Band hexagons. In one band each row and box holds one a and one b. If
        # three columns (one per stack) each hold both inside the band, swapping
        # a and b on those 6 cells keeps every house: one must be a ghost. Same
        # for a stack and three rows. has[...] is implied by x (true whenever the
        # line holds d in the band), so the clause only fires on a real hexagon.
        for transpose in (False, True):

            def at(i, j, transpose=transpose):
                return (j, i) if transpose else (i, j)

            for band in BANDS:
                has = {}
                for j in range(N):
                    for d in range(9):
                        v = m.new_bool_var("has")
                        for i in band:
                            m.add_implication(x[at(i, j)][d], v)
                        has[j, d] = v
                for j0 in range(3):
                    for j1 in range(3, 6):
                        for j2 in range(6, 9):
                            for a in range(9):
                                for b in range(a + 1, 9):
                                    lits = []
                                    for j in (j0, j1, j2):
                                        lits += [has[j, a].Not(), has[j, b].Not()]
                                        lits += [
                                            on[at(i, j)][d]
                                            for i in band
                                            for d in (a, b)
                                        ]
                                    m.add_bool_or(lits)
                # Band segments: two columns in different stacks holding the same
                # three digits inside the band can trade them (a 3-cycle). Rows
                # and boxes keep their sets, so one of the 6 cells is a ghost.
                for j0 in range(N):
                    for j1 in range(j0 + 1, N):
                        if j0 // 3 == j1 // 3:
                            continue
                        ghosts = [g[at(i, j)] for i in band for j in (j0, j1)]
                        for a in range(9):
                            for b in range(a + 1, 9):
                                for c in range(b + 1, 9):
                                    m.add_bool_or(
                                        ghosts
                                        + [
                                            has[j, d].Not()
                                            for j in (j0, j1)
                                            for d in (a, b, c)
                                        ]
                                    )
        for cell in CELLS:
            m.add_hint(x[cell][rng.randrange(9)], 1)
        self.cuts = 0
        self.lit = {}

    def _same(self, p, q):
        """Literal that holds only if cells p and q hold the same digit."""
        key = ("eq", p, q)
        if key not in self.lit:
            v = self.m.new_bool_var(f"eq{p}{q}")
            for d in range(9):
                self.m.add_bool_or([v.Not(), self.x[p][d].Not(), self.x[q][d]])
            self.lit[key] = v
        return self.lit[key]

    def _differ(self, p, q):
        """Literal that holds only if cells p and q hold different digits."""
        key = ("ne", p, q)
        if key not in self.lit:
            v = self.m.new_bool_var(f"ne{p}{q}")
            for d in range(9):
                self.m.add_bool_or([v.Not(), self.x[p][d].Not(), self.x[q][d].Not()])
            self.lit[key] = v
        return self.lit[key]

    def cut(self, S, Y):
        """Y swaps digits on D. The swap stays valid in any grid whose digits on D
        repeat S's equality pattern there (a relabeling), so such a grid needs a
        ghost in D."""
        D = [cell for cell in CELLS if Y[cell] != S[cell]]
        lits = [self.g[cell] for cell in D]
        for i, p in enumerate(D):
            for q in D[i + 1 :]:
                if S[p] == S[q]:
                    lits.append(self._differ(p, q))
                elif not shares_house(p, q):
                    lits.append(self._same(p, q))
        self.m.add_bool_or(lits)
        self.cuts += 1

    def tighten(self, k):
        self.m.add(self.size <= k)

    def solve(self, rng, limit):
        s = solver(rng.randrange(1 << 30), limit)
        st = s.solve(self.m)
        if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return (
                "shape",
                digits_of(s, self.x),
                {cell for cell in CELLS if s.value(self.g[cell])},
            )
        return ("infeasible" if st == cp_model.INFEASIBLE else "timeout"), None, None


def second_solution(S, shape, rng, limit):
    """Another sudoku agreeing with S on the shape, fewest changed cells; None if unique."""
    m = cp_model.CpModel()
    x = sudoku(m)
    for cell in shape:
        m.add(x[cell][S[cell] - 1] == 1)
    same = [x[cell][S[cell] - 1] for cell in CELLS if cell not in shape]
    m.add_bool_or([v.Not() for v in same])
    m.maximize(sum(same))
    s = solver(rng.randrange(1 << 30), limit)
    st = s.solve(m)
    if st == cp_model.INFEASIBLE:
        return None
    if st == cp_model.UNKNOWN:
        raise RuntimeError("uniqueness check timed out with no answer")
    return digits_of(s, x)


def verify(S, shape):
    """Fresh check: givens are neighbour counts, sudoku-consistent, an 8, unique."""
    counts_ok = all(
        sum(n in shape for n in neighbours(*cell)) == S[cell] for cell in shape
    )
    has_eight = any(S[cell] == 8 for cell in shape)
    m = cp_model.CpModel()
    x = sudoku(m)
    for cell in shape:
        m.add(x[cell][S[cell] - 1] == 1)
    s = solver(0, 120)
    if s.solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return False
    first = digits_of(s, x)
    m.add_bool_or([x[cell][first[cell] - 1].Not() for cell in CELLS])
    return counts_ok and has_eight and first == S and s.solve(m) == cp_model.INFEASIBLE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--min-ghosts", type=int, default=17)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    t0 = time.monotonic()
    deadline = t0 + a.seconds
    master = Master(rng, a.min_ghosts)
    end = "time"
    while time.monotonic() < deadline:
        kind, S, shape = master.solve(rng, max(1.0, deadline - time.monotonic()))
        if kind != "shape":
            end = kind
            break
        Y = second_solution(S, shape, rng, 30)
        if Y is None:
            ok = verify(S, shape)
            rec = {
                "seed": a.seed,
                "ghosts": len(shape),
                "verified": ok,
                "cuts": master.cuts,
                "elapsed_s": round(time.monotonic() - t0, 1),
                "solution": [[S[r, c] for c in range(N)] for r in range(N)],
                "shape": sorted(shape),
            }
            with (a.out / "progress.jsonl").open("a") as f:
                f.write(json.dumps(rec) + "\n")
            print(
                f"unique: {len(shape)} ghosts verified={ok} cuts={master.cuts} t={rec['elapsed_s']}s",
                flush=True,
            )
            master.tighten(len(shape) - 1)
        else:
            master.cut(S, Y)
            if master.cuts % 10 == 0:
                diff = sum(Y[c] != S[c] for c in CELLS)
                print(
                    f"  {master.cuts} cuts, shape {len(shape)}, diff {diff}, "
                    f"t={time.monotonic() - t0:.0f}s",
                    flush=True,
                )
    print(f"end={end} cuts={master.cuts} t={time.monotonic() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()

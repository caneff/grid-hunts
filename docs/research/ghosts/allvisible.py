"""Ghosts, all visible: the ghost digits alone make the sudoku unique.

    uv run docs/research/ghosts/allvisible.py --grids 5 --seed 1 --out DIR

Every ghost is shown with its digit, and those digits are the only givens. A
ghost's digit is its ghost-neighbour count, so a ghost shape fixes its givens.
One ghost must hold 8. Uniqueness is plain sudoku uniqueness of those givens:
hidden ghosts, if the rules allowed them, only add constraints.

Per grid: a random solution S that admits an 8-ghost (probe model). Then
CEGAR on the shape alone:
  master  g[c] bools; g ⇒ Σ g(neighbours) = S[c]; some 8-cell is a ghost;
          one clause per counterexample; Σ g ≤ bound.
  check   sudoku with S given on the shape, S forbidden, fewest cells changed.
          A second grid Y adds the clause OR{g[c] : Y[c] ≠ S[c]}.
A unique shape tightens the bound to |shape| − 1; the clauses stay valid, as
they depend on S only. The grid ends when the master is infeasible (the last
shape is minimum for S) or its time runs out.
"""

import argparse
import json
import random
import time
from pathlib import Path

from ortools.sat.python import cp_model

N = 9
CELLS = [(r, c) for r in range(N) for c in range(N)]


def neighbours(r, c):
    return [(r + a, c + b) for a in (-1, 0, 1) for b in (-1, 0, 1)
            if (a or b) and 0 <= r + a < N and 0 <= c + b < N]


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
                m.add_exactly_one(x[br + a, bc + b][d] for a in range(3) for b in range(3))
    return x


def solver(seed, limit):
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.random_seed = seed
    s.parameters.max_time_in_seconds = limit
    return s


def digits_of(s, x):
    return {cell: next(d + 1 for d in range(9) if s.value(x[cell][d])) for cell in CELLS}


def random_solution(rng):
    """A sudoku solution that admits a ghost shape with an 8 (probe model)."""
    m = cp_model.CpModel()
    x = sudoku(m)
    g = {cell: m.new_bool_var(f"g{cell}") for cell in CELLS}
    for r, c in CELLS:
        digit = sum((d + 1) * x[r, c][d] for d in range(9))
        m.add(sum(g[n] for n in neighbours(r, c)) == digit).only_enforce_if(g[r, c])
    eight = []
    for cell in CELLS:
        e = m.new_bool_var(f"e{cell}")
        m.add_implication(e, g[cell])
        m.add_implication(e, x[cell][7])
        eight.append(e)
    m.add_bool_or(eight)
    for cell in CELLS:
        m.add_hint(x[cell][rng.randrange(9)], 1)
    s = solver(rng.randrange(1 << 30), 60)
    s.parameters.randomize_search = True
    assert s.solve(m) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    return digits_of(s, x)


class Master:
    def __init__(self, S):
        self.m = m = cp_model.CpModel()
        self.g = g = {cell: m.new_bool_var(f"g{cell}") for cell in CELLS}
        for r, c in CELLS:
            if S[r, c] == 9:
                m.add(g[r, c] == 0)
            else:
                m.add(sum(g[n] for n in neighbours(r, c)) == S[r, c]).only_enforce_if(g[r, c])
        m.add_bool_or([g[cell] for cell in CELLS if S[cell] == 8])
        self.size = sum(g.values())
        self.bound = None

    def cut(self, diff):
        self.m.add_bool_or([self.g[cell] for cell in diff])

    def tighten(self, k):
        self.m.add(self.size <= k)

    def solve(self, rng, limit):
        s = solver(rng.randrange(1 << 30), limit)
        st = s.solve(self.m)
        if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return "shape", {cell for cell in CELLS if s.value(self.g[cell])}
        return ("infeasible" if st == cp_model.INFEASIBLE else "timeout"), None


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
    Y = digits_of(s, x)
    return [cell for cell in CELLS if Y[cell] != S[cell]]


def verify(S, shape):
    """Fresh check: givens are neighbour counts, sudoku-consistent, one 8, unique."""
    counts_ok = all(sum(n in shape for n in neighbours(*cell)) == S[cell] for cell in shape)
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


def hunt(S, rng, deadline, log):
    master = Master(S)
    best, cuts = None, 0
    while time.monotonic() < deadline:
        kind, shape = master.solve(rng, max(1.0, deadline - time.monotonic()))
        if kind != "shape":
            return best, cuts, kind
        diff = second_solution(S, shape, rng, 30)
        if diff is None:
            best = sorted(shape)
            log(f"  unique shape: {len(shape)} ghosts after {cuts} cuts")
            master.tighten(len(shape) - 1)
        else:
            master.cut(diff)
            cuts += 1
            if cuts % 200 == 0:
                log(f"  {cuts} cuts, last diff {len(diff)} cells, shape {len(shape)}")
    return best, cuts, "time"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grids", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--grid-seconds", type=float, default=120)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)

    def log(msg):
        print(msg, flush=True)

    for i in range(a.grids):
        t0 = time.monotonic()
        S = random_solution(rng)
        best, cuts, end = hunt(S, rng, t0 + a.grid_seconds, log)
        ok = best is not None and verify(S, set(map(tuple, best)))
        rec = {
            "grid": i, "seed": a.seed, "ghosts": len(best) if best else None, "verified": ok,
            "end": end, "cuts": cuts, "wall_s": round(time.monotonic() - t0, 1),
            "solution": [[S[r, c] for c in range(N)] for r in range(N)],
            "shape": best,
        }
        with open(a.out / "progress.jsonl", "a") as f:
            f.write(json.dumps(rec) + "\n")
        log(f"grid {i}: ghosts={rec['ghosts']} verified={ok} end={end} cuts={cuts} wall={rec['wall_s']}s")


if __name__ == "__main__":
    main()

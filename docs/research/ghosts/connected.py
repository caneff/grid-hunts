"""Ghosts, all visible and orthogonally connected: do such shapes exist?

    uv run docs/research/ghosts/connected.py --size 20 [--force 72,73,79] [--ban 57]

Shape-only CP-SAT model: ghost booleans, each ghost's given is its
ghost-neighbour count (1-8), givens distinct within every row, column and box,
pins honoured, and the ghost count within --min..--max. --eight also demands a
given of 8.

Connectivity is enforced by lazy cuts rather than a flow encoding: solve, flood
fill the shape, and for every component that is not the whole shape add one
clause — some cell of the component is not a ghost, or some boundary cell is,
or the witness ghost outside it is not. Then re-solve. The witness keeps the
clause sound for a shape that is only that component.
"""

import argparse
import time

from ortools.sat.python import cp_model

from shapes import BOX, CELLS, NEIGH, ORTH, count_solutions, givens


def components(shape):
    """Orthogonally connected components of a shape, as lists of cells."""
    left, out = set(shape), []
    while left:
        start = left.pop()
        comp, stack = [start], [start]
        while stack:
            for j in ORTH[stack.pop()]:
                if j in left:
                    left.discard(j)
                    comp.append(j)
                    stack.append(j)
        out.append(comp)
    return out


def boundary(comp):
    cells = set(comp)
    return {j for i in comp for j in ORTH[i] if j not in cells}


def solve_connected(m, g, seconds, workers, log):
    """Solve with lazy connectivity cuts. Returns (shape, cuts) or (None, cuts)."""
    s = cp_model.CpSolver()
    s.parameters.num_workers = workers
    cuts = 0
    start = time.monotonic()
    while True:
        s.parameters.max_time_in_seconds = max(1.0, seconds - (time.monotonic() - start))
        st = s.solve(m)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            log(f"{s.status_name(st)} after {cuts} connectivity cuts")
            return None, cuts
        shape = {i for i in range(81) if s.value(g[i])}
        comps = components(shape)
        if len(comps) == 1:
            return shape, cuts
        for comp in comps:
            witness = next(i for i in shape if i not in comp)
            m.add_bool_or([g[i].Not() for i in comp] + [g[b] for b in boundary(comp)] + [g[witness].Not()])
            cuts += 1
        if time.monotonic() - start > seconds:
            log(f"time after {cuts} connectivity cuts")
            return None, cuts


def build(size_min, size_max, force, ban, eight):
    m = cp_model.CpModel()
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    n = [m.new_int_var(0, 8, f"n{i}") for i in range(81)]
    for i in range(81):
        m.add(n[i] == sum(g[j] for j in NEIGH[i]))
        m.add(n[i] >= 1).only_enforce_if(g[i])
        for j in range(i + 1, 81):
            if CELLS[i][0] == CELLS[j][0] or CELLS[i][1] == CELLS[j][1] or BOX[i] == BOX[j]:
                m.add(n[i] != n[j]).only_enforce_if([g[i], g[j]])
    for i in force:
        m.add(g[i] == 1)
    for i in ban:
        m.add(g[i] == 0)
    if eight:
        e = [m.new_bool_var(f"e{i}") for i in range(81)]
        for i in range(81):
            m.add(n[i] == 8).only_enforce_if(e[i])
            m.add_implication(e[i], g[i])
        m.add_bool_or(e)
    m.add(sum(g) >= size_min)
    m.add(sum(g) <= size_max)
    return m, g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", dest="size_min", type=int, default=16)
    ap.add_argument("--max", dest="size_max", type=int, default=40)
    ap.add_argument("--force", default="")
    ap.add_argument("--ban", default="")
    ap.add_argument("--eight", action="store_true")
    ap.add_argument("--seconds", type=float, default=120)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    force = [int(x) for x in a.force.split(",") if x]
    ban = [int(x) for x in a.ban.split(",") if x]
    t0 = time.monotonic()
    m, g = build(a.size_min, a.size_max, force, ban, a.eight)
    shape, cuts = solve_connected(m, g, a.seconds, a.workers, print)
    print(f"size {a.size_min}-{a.size_max}: {'shape' if shape else 'none'} "
          f"after {cuts} cuts in {time.monotonic() - t0:.1f}s")
    if shape is None:
        return
    print("ghosts", len(shape))
    gv = givens(shape)
    sols = count_solutions(gv, 2) if gv else None
    print("shape", sorted(shape))
    print("givens admissible:", gv is not None, "sudoku solutions (cap 2):", sols)
    for r in range(9):
        print(" ".join(f"{gv.get(r * 9 + c, '.') if gv else '?'}" for c in range(9)))


if __name__ == "__main__":
    main()

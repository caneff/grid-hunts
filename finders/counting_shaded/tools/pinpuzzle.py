"""6x6 counting-shaded puzzle search: shown shaded cells + one given digit.

    uv run pinpuzzle.py [--latin] [--both] [--self] --shaded 30,35

Solutions are (grid, shading) pairs under: sudoku 2x3 (or Latin), shaded
cells orthogonally connected (and unshaded too with --both), shaded digit =
shaded king-neighbour count (+1 with --self). For every cell not shown and
every digit, count solutions at cap 2 and print the unique ones."""

import argparse
import json
import sys
from pathlib import Path

from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gridenum as G

N = 6
NN = 36
ap = argparse.ArgumentParser()
ap.add_argument("--latin", action="store_true")
ap.add_argument("--both", action="store_true")
ap.add_argument("--self", action="store_true")
ap.add_argument("--shaded", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
G.geometry(6, 2, 3)
G.LATIN = a.latin
shown = [int(x) for x in a.shaded.split(",")]


def model(given):
    m = cp_model.CpModel()
    v = [m.new_int_var(1, N, f"v{i}") for i in range(NN)]
    g = [m.new_bool_var(f"g{i}") for i in range(NN)]
    for k in range(N):
        m.add_all_different([v[k * N + c] for c in range(N)])
        m.add_all_different([v[c * N + k] for c in range(N)])
    if not a.latin:
        for b in range(N):
            m.add_all_different([v[i] for i in range(NN) if G.BOX[i] == b])
    m.add(sum(g) >= 1)
    G.add_connectivity(m, g, NN, "s")
    if a.both:
        m.add(sum(g) <= NN - 1)
        G.add_connectivity(m, [x.Not() for x in g], NN, "u")
    for i in range(NN):
        m.add(
            v[i] == sum(g[j] for j in G.NEIGH[i]) + (1 if a.self else 0)
        ).only_enforce_if(g[i])
    for i in shown:
        m.add(g[i] == 1)
    for i, d in given.items():
        m.add(v[i] == d)
    return m, v, g


def count(given, cap=2):
    m, v, g = model(given)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 8
    sols = []
    while len(sols) < cap:
        if s.solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
        sol = ([s.value(x) for x in v], [s.value(x) for x in g])
        sols.append(sol)
        lits = [g[i].Not() if sol[1][i] else g[i] for i in range(NN)]
        for i in range(NN):
            b = m.new_bool_var(f"df{len(sols)}_{i}")
            m.add(v[i] != sol[0][i]).only_enforce_if(b)
            lits.append(b)
        m.add_bool_or(lits)
    return sols


name = lambda i: f"r{i // N + 1}c{i % N + 1}"
base = count({}, 2)
print(f"no given: {len(base)}+ solutions")
hits = []
for j in range(NN):
    if j in shown:
        continue
    for d in range(1, N + 1):
        sols = count({j: d}, 2)
        if len(sols) == 1:
            grid, sh = sols[0]
            shape = [i for i in range(NN) if sh[i]]
            hits.append(
                {
                    "given": {name(j): d},
                    "cell": j,
                    "digit": d,
                    "shape": shape,
                    "grid": grid,
                }
            )
            print(
                f"UNIQUE with {name(j)}={d} ({'shaded' if sh[j] else 'unshaded'} in the solution), shading size {len(shape)}"
            )
print(f"{len(hits)} unique one-given puzzles")
with Path(a.out).open("w") as fh:
    for h in hits:
        fh.write(
            json.dumps(
                {**h, "latin": a.latin, "both": a.both, "self": a.self, "shown": shown}
            )
            + "\n"
        )

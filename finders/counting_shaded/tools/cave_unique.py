"""Is a 6x6 Latin counting-shaded puzzle unique from a subset of its cave clues?

Rules modelled: Latin square 1-6; shading with shaded and unshaded each
orthogonally connected; a shaded cell's digit = its shaded king-neighbour
count; each given digit = number of same-colour cells seen orthogonally from
it, itself included. Solutions are (grid, shading) pairs, counted at cap 2 by
solve-then-forbid."""

import itertools
import json
import sys
from pathlib import Path

from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gridenum as G

N = 6
NN = 36
G.geometry(6, 2, 3)
G.LATIN = True
DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def ray(i, d):
    r, c = divmod(i, N)
    out = []
    while True:
        r += d[0]
        c += d[1]
        if not (0 <= r < N and 0 <= c < N):
            return out
        out.append(r * N + c)


def seen(i, region):
    return 1 + sum(
        len(list(itertools.takewhile(lambda j: j in region, ray(i, d)))) for d in DIRS
    )


def model(givens, digits=True, shading=()):
    m = cp_model.CpModel()
    v = [m.new_int_var(1, N, f"v{i}") for i in range(NN)]
    g = [m.new_bool_var(f"g{i}") for i in range(NN)]
    for k in range(N):
        m.add_all_different([v[k * N + c] for c in range(N)])
        m.add_all_different([v[c * N + k] for c in range(N)])
    size = m.new_int_var(1, NN - 1, "size")
    m.add(sum(g) == size)
    G.add_connectivity(m, g, NN, "s")
    G.add_connectivity(m, [x.Not() for x in g], NN, "u")
    for i in range(NN):
        m.add(v[i] == sum(g[j] for j in G.NEIGH[i])).only_enforce_if(g[i])
    for i in shading:
        m.add(g[i] == (1 if shading[i] else 0))
    for i, d in givens.items():
        if digits:
            m.add(v[i] == d)
        terms = []
        for dd in DIRS:
            prev = None
            for j in ray(i, dd):
                same = m.new_bool_var(f"same{i}_{j}")
                m.add(g[i] == g[j]).only_enforce_if(same)
                m.add(g[i] != g[j]).only_enforce_if(same.Not())
                vis = m.new_bool_var(f"vis{i}_{j}")
                if prev is None:
                    m.add(vis == same)
                else:
                    m.add_min_equality(vis, [prev, same])
                terms.append(vis)
                prev = vis
        m.add(v[i] == 1 + sum(terms))
    return m, v, g


def count(givens, cap=2, digits=True, shading=()):
    m, v, g = model(givens, digits, shading)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 8
    sols = []
    while len(sols) < cap:
        st = s.solve(m)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
        sol = ([s.value(x) for x in v], [s.value(x) for x in g])
        sols.append(sol)
        lits = [g[i].Not() if sol[1][i] else g[i] for i in range(NN)]
        for i in range(NN):
            b = m.new_bool_var(f"diff{len(sols)}_{i}")
            m.add(v[i] != sol[0][i]).only_enforce_if(b)
            lits.append(b)
        m.add_bool_or(lits)
    return sols


rows = (
    [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
    if sys.argv[1] != "/dev/null"
    else []
)
for k, row in enumerate(rows):
    sh = set(row["shape"])
    un = set(range(NN)) - sh
    grid = row["grid"]
    clues = {i: grid[i] for i in range(NN) if grid[i] == seen(i, un if i in un else sh)}
    name = lambda i: f"r{i // N + 1}c{i % N + 1}"
    print(
        f"grid {k + 1}: cave clues {[name(i) + '=' + str(d) for i, d in clues.items()]}"
    )
    sols = count(clues)
    print(
        f"  all {len(clues)} clues: {len(sols)} solution(s)"
        + ("" if len(sols) == 1 else " (not unique)")
    )
    if len(sols) == 1:
        assert sols[0][0] == grid and [i for i in range(NN) if sols[0][1][i]] == sorted(
            sh
        )
        minimal = []
        for r in range(1, len(clues)):
            for sub in itertools.combinations(clues, r):
                if any(set(mn) <= set(sub) for mn in minimal):
                    continue
                if len(count({i: clues[i] for i in sub})) == 1:
                    minimal.append(sub)
                    print(
                        f"  UNIQUE from {[name(i) + '=' + str(clues[i]) for i in sub]}"
                    )
        if not minimal:
            print("  no proper subset is unique")
    else:
        a, b = sols[0], sols[1]
        print("  second solution shading:", "".join("#" if x else "." for x in b[1]))

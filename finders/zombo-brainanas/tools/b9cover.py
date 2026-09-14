"""Which pairs of box-9 cells can both be circles (rect or pocket, pockets to 9)?
Cover loop, model built once: each round maximises the number of still-open
pairs realised; every pair the witness realises is feasible. INFEASIBLE settles
the rest. Resumes from b9cover.json; rounds append to b9cover.log."""
import sys, time, json, itertools, os
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
from ortools.sat.python import cp_model as cp
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
cells = [(r, c) for r in range(6, 9) for c in range(6, 9)]
key = lambda a, b: f"r{a[0]+1}c{a[1]+1}+r{b[0]+1}c{b[1]+1}"
res = json.load(open(Z + "b9cover.json")) if os.path.exists(Z + "b9cover.json") else {}
uncovered = {q for q in itertools.combinations(cells, 2) if key(*q) not in res}
t0 = time.time()
m, x, inf = zb.build(min_pockets=1, min_per_box={9: 2}, big_pocket_cells=frozenset(cells))
anyc = {}
for p in cells:
    b = m.NewBoolVar(""); m.AddBoolOr(m.circle_at.get(p, [])).OnlyEnforceIf(b)
    m.AddBoolAnd([l.Not() for l in m.circle_at.get(p, [])]).OnlyEnforceIf(b.Not()); anyc[p] = b
pair = {}
for a, c in uncovered:
    pb = m.NewBoolVar(""); m.AddBoolAnd([anyc[a], anyc[c]]).OnlyEnforceIf(pb)
    m.AddBoolOr([anyc[a].Not(), anyc[c].Not()]).OnlyEnforceIf(pb.Not()); pair[a, c] = pb
print(f"built in {time.time()-t0:.0f}s; {len(res)} settled, {len(uncovered)} open", flush=True)
rounds = 0
while uncovered:
    rounds += 1; t = time.time()
    m.AddBoolOr([pair[q] for q in uncovered])  # subset of last round's clause: cumulative is sound
    m.Maximize(sum(pair[q] for q in uncovered))
    while True:  # CEGAR on banana circles (dead with exact Brainana, kept for safety)
        s = cp.CpSolver(); s.parameters.num_workers = 8; s.parameters.max_time_in_seconds = 900; s.parameters.random_seed = rounds
        cb = zb.FirstSolution(stall=90)
        st = zb.solve_with_watchdog(s, m, cb)
        if st == cp.INFEASIBLE:
            for q in uncovered: res[key(*q)] = dict(verdict="infeasible", secs=round(time.time() - t))
            print(f"round {rounds}: INFEASIBLE -> {len(uncovered)} pairs settled ({time.time()-t:.0f}s)", flush=True)
            uncovered = set(); break
        if st not in (cp.OPTIMAL, cp.FEASIBLE):
            for q in uncovered: res[key(*q)] = dict(verdict="unknown")
            print(f"round {rounds}: UNKNOWN after {time.time()-t:.0f}s; {len(uncovered)} pairs open", flush=True)
            uncovered = set(); break
        sol = {p: s.Value(x[p]) for p in zb.CELLS}; shade = {p: s.Value(inf[p]) for p in zb.CELLS}
        cut = zb.violation(sol, shade, {})
        if cut is not None:
            bc, rc, _ = cut; Rl = lambda q: inf[q] if zb.RECT else inf[q].Not()
            m.AddBoolOr([Rl(q) for q in bc] + [Rl(q).Not() for q in rc]); continue
        circ = zb.circle_candidates(sol, shade)
        realised = [p for p in cells if p in circ]
        grid = ["".join(str(sol[(i, j)]) for j in range(9)) for i in range(9)]
        infd = ["".join("*" if shade[(i, j)] else "." for j in range(9)) for i in range(9)]
        new = [q for q in itertools.combinations(realised, 2) if q in uncovered]
        for q in new:
            uncovered.discard(q)
            res[key(*q)] = dict(verdict="feasible", secs=round(time.time() - t), grid=grid, infected=infd, circles=[list(p) for p in circ])
        print(f"round {rounds}: box-9 circles at {[f'r{p[0]+1}c{p[1]+1}' for p in realised]}, {len(new)} new pairs, {len(uncovered)} left ({time.time()-t:.0f}s)", flush=True)
        break
    json.dump(res, open(Z + "b9cover.json", "w"), indent=0)
print("DONE", flush=True)

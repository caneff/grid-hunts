"""Ceiling of an upper-left objective with a fixed box-9 pair. usage: ceiling.py choc|edges seed"""
import sys, time; sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
mode, seed = sys.argv[1], int(sys.argv[2])
Q = [p for p in zb.CELLS if p[0] < 5 and p[1] < 5]
E = {(p, q): 50000 for p in Q for q in ((p[0]+1, p[1]), (p[0], p[1]+1)) if q in Q}
kw = dict(bonus={p: 50000 for p in Q}) if mode == "choc" else dict(bonus_edges=E)
t = time.time(); rounds = []
found = zb.solve_valid(circles={(6,7): None, (8,6): None}, fix_shade={(6,7): 1, (8,6): 0}, seed=seed, limit=300,
                       min_pockets=1, objective=True, log=rounds.append, stall=120, stop_at=99, **kw)
sol, sh = found; circ = zb.circle_candidates(sol, sh)
edges = sum(sh[p] != sh[q] for (p, q) in E)
print(f"{mode} seed {seed}: {len(circ)} circles, {sum(sh.values())} infected, {sum(sh[p] for p in Q)}/25 quadrant infected, {edges}/40 quadrant edges alternate, {time.time()-t:.0f}s")
print(zb.show(sol, sh, circles=circ))

"""Per feasible pair class: can both circles be infected (II) / both uninfected (UU)? -> kinds2.log"""
import sys, time, os, itertools
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
shard, n = int(sys.argv[1]), int(sys.argv[2])
reps = [((7, 7), (7, 8)), ((7, 7), (8, 8)), ((7, 7), (9, 8)), ((7, 8), (8, 7)), ((7, 8), (9, 7)), ((7, 9), (8, 7)), ((7, 9), (9, 7)), ((8, 7), (8, 8)), ((8, 7), (9, 8)), ((8, 8), (9, 7)), ((8, 9), (9, 7)), ((9, 7), (9, 8)), ((7, 7), (8, 7)), ((7, 7), (9, 7)), ((7, 8), (8, 9)), ((7, 8), (9, 9)), ((7, 9), (8, 9)), ((7, 9), (9, 9)), ((8, 9), (9, 9)), ((9, 8), (9, 9)), ((7, 7), (7, 9)), ((7, 7), (8, 9)), ((7, 7), (9, 9)), ((7, 8), (8, 8)), ((7, 8), (9, 8)), ((7, 9), (8, 8)), ((7, 9), (9, 8)), ((8, 7), (8, 9)), ((8, 7), (9, 9)), ((9, 7), (9, 9))]
nm = lambda p: f"r{p[0]}c{p[1]}"
for i, (a, b) in enumerate(reps):
    if i % n != shard: continue
    A, B = (a[0]-1, a[1]-1), (b[0]-1, b[1]-1)
    for combo, sh in (("IU", {A: 1, B: 0}), ("UI", {A: 0, B: 1})):
        t = time.time(); rounds = []
        try:
            found = zb.solve_valid(circles={A: None, B: None}, seed=i, limit=120, log=rounds.append, fix_shade=sh)
            res = "feasible" if found else "infeasible"
        except TimeoutError:
            res = "unknown"
        open(Z + "kinds2.log", "a").write(f"{nm(a)}+{nm(b)} {combo}: {res} ({time.time()-t:.0f}s, {len(rounds)} rounds)\n")
open(Z + "kinds2.log", "a").write(f"SHARD {shard} DONE\n")

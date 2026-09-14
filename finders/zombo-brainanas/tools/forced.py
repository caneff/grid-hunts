"""Which cells have forced shading in every valid grid? usage: forced.py shard nshards -> forced.log"""
import sys, time, os
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
shard, n = int(sys.argv[1]), int(sys.argv[2])
for i, p in enumerate(zb.CELLS):
    if i % n != shard: continue
    for v, word in ((0, "uninfected"), (1, "infected")):
        t = time.time(); rounds = []
        try:
            found = zb.solve_valid(seed=i, limit=60, log=rounds.append, fix_shade={p: v})
            res = "possible" if found else f"IMPOSSIBLE -> always {'infected' if v == 0 else 'uninfected'}"
        except TimeoutError:
            res = "unknown"
        open(Z + "forced.log", "a").write(f"r{p[0]+1}c{p[1]+1} {word}: {res} ({time.time()-t:.0f}s)\n")
open(Z + "forced.log", "a").write(f"SHARD {shard} DONE\n")

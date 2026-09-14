"""Per box-9 pair kind: can the grid have >= 5 brainanas? No avoid, no objective. usage: kinds5.py shard nshards"""
import sys, time, os, re
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/scratch-zombo/"
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
shard, n = int(sys.argv[1]), int(sys.argv[2])
kinds = []
for line in open(Z + "kinds2.log").read().splitlines() + open(Z + "kinds.log").read().splitlines():
    m = re.match(r"(r\dc\d)\+(r\dc\d) (II|IU|UI|UU): feasible", line)
    if not m: continue
    a = tuple(int(x) - 1 for x in re.findall(r"\d", m[1])); b = tuple(int(x) - 1 for x in re.findall(r"\d", m[2]))
    k = m[3]; kinds.append((f"{m[1]}_{m[2]}_{k}", {a: int(k[0] == "I"), b: int(k[1] == "I")}, a, b))
kinds.sort()
def log(s): open(Z + "hunt/plant/kinds5.log", "a").write(s + "\n")
for i, (name, sh, a, b) in enumerate(kinds):
    if i % n != shard: continue
    t = time.time()
    try:
        f = zb.solve_valid(circles={a: None, b: None}, fix_shade=sh, min_pockets=1, min_groups=5, limit=600)
        v = "FEASIBLE" if f else "infeasible"
    except TimeoutError:
        v = "TIMEOUT"
    log(f"{name}: {v} {time.time()-t:.0f}s")
    if f: zb.dump(Z + f"hunt/groups/full_5_{name}.json", *f, dict(f[0]), zb.circle_candidates(*f))
log(f"SHARD {shard} DONE")

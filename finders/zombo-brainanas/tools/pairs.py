"""Every box-9 pair as two open circles (rect in-model, pocket by lazy cut, any size).
usage: pairs.py shard nshards [limit]  -> pairs_<shard>.json, pairs.log"""
import sys, json, itertools, time, os
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
shard, n = int(sys.argv[1]), int(sys.argv[2]); limit = int(sys.argv[3]) if len(sys.argv) > 3 else 120
TOTAL = int(sys.argv[4]) if len(sys.argv) > 4 else 600  # seconds per pair across all rounds
cells = [(r, c) for r in range(6, 9) for c in range(6, 9)]
name = lambda p: f"r{p[0]+1}c{p[1]+1}"
res = {}
for i, (a, b) in enumerate(itertools.combinations(cells, 2)):
    if i % n != shard: continue
    k = f"{name(a)}+{name(b)}"; t = time.time(); rounds = []
    def log(line):  # per-round visibility + total budget
        rounds.append(line)
        open(Z + "pairs_rounds.log", "a").write(f"{k} {line.strip()} [{round(time.time()-t)}s]\n")
        if time.time() - t > TOTAL and "valid after" not in line:
            raise TimeoutError("total budget")
    try:
        found = zb.solve_valid(circles={a: None, b: None}, seed=i, limit=limit, log=log)
        verdict = "feasible" if found else "infeasible"
    except TimeoutError:
        found, verdict = None, "unknown"
    r = dict(verdict=verdict, secs=round(time.time() - t), rounds=len(rounds))
    if found:
        sol, sh = found; circ = zb.circle_candidates(sol, sh)
        r.update(grid=["".join(str(sol[i, j]) for j in range(9)) for i in range(9)],
                 infected=["".join("*" if sh[i, j] else "." for j in range(9)) for i in range(9)],
                 circles=[list(p) for p in circ], box9=[name(p) for p in circ if p[0] >= 6 and p[1] >= 6])
    res[k] = r
    json.dump(res, open(Z + f"pairs_{shard}.json", "w"), indent=0)
    open(Z + "pairs.log", "a").write(f"{k}: {verdict} in {r['secs']}s, {len(rounds)} rounds" + (f", box9 circles {r['box9']}" if found else "") + "\n")
open(Z + "pairs.log", "a").write(f"SHARD {shard} DONE\n")

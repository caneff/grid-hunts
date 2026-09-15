import json, sys, time
from collections import Counter
sys.path.insert(0, "docs/research/2026-09-14-galaxy-copycat")
from copycat_rsl_solver import build, parse_cell
from ortools.sat.python import cp_model
D = "docs/research/2026-09-14-galaxy-copycat/boards/"
base = json.load(open(D + "board14-four-lines.json"))
seed = json.load(open(D + "board14-forced.json"))
lines = {r["cells"]: r for r in map(json.loads, open(D + "board14-pair4.lines.jsonl"))}
pairs = [json.loads(l) for l in open(D + "board14-pair4.pairs.jsonl") if l.startswith("{")]
rank = {(r["X"], r["Y"]): r for r in map(json.loads, (l for l in open(D + "board14-pair4.rank.jsonl") if l.startswith("{")))}
def msets(name):
    return {tuple(ms) for v in lines[name]["sums"].values() for ms in v}
def add_values(m, digit, cc):
    val = [[m.NewIntVar(1, 9, "") for c in range(9)] for r in range(9)]
    for r in range(9):
        for c in range(9):
            m.Add(val[r][c] == digit[r][c]).OnlyEnforceIf(cc[r][c].Not())
            m.Add(val[r][c] == digit[8 - r][8 - c]).OnlyEnforceIf(cc[r][c])
    return val
out = []
t0 = time.time()
for p in pairs:
    if tuple(lines[p["X"]]["struct"]) != (2, 2) or tuple(lines[p["Y"]]["struct"]) != (2, 2):
        continue
    shared = [ms for ms in msets(p["X"]) & msets(p["Y"]) if len(set(ms)) < 4]
    ok = []
    for ms in sorted(shared):
        setup = {**seed, "lines": dict(base["lines"], X=p["X"].split("-"), Y=p["Y"].split("-")), "pairs": [*base["pairs"], ["X", "Y"]]}
        m, digit, cc, _ = build(setup)
        val = add_values(m, digit, cc)
        cnt = Counter(ms)
        cells = [parse_cell(c) for c in p["X"].split("-")]
        for v in range(1, 10):
            b = []
            for r, c in cells:
                x = m.NewBoolVar(""); m.Add(val[r][c] == v).OnlyEnforceIf(x); m.Add(val[r][c] != v).OnlyEnforceIf(x.Not()); b.append(x)
            m.Add(sum(b) == cnt[v])
        sv = cp_model.CpSolver(); sv.parameters.num_search_workers = 1; sv.parameters.max_time_in_seconds = 60
        if sv.Solve(m) in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            ok.append(ms)
    if ok:
        r = rank.get((p["X"], p["Y"]), {})
        out.append({"X": p["X"], "Y": p["Y"], "repeat_msets": ok, "all_msets": sorted(msets(p["X"]) & msets(p["Y"])), "new_fixed": r.get("new_fixed")})
        print(json.dumps(out[-1]), flush=True)
print(f"{len(out)} pairs with a feasible repeated value, {time.time()-t0:.0f}s")
json.dump(out, open(".scratch/copycat-rsl/p22/repeats.json", "w"))

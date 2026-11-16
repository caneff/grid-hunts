"""SCRATCH: count solutions (to 3) of the complex-region jigsaw finds, own visibility encoding, with and without inner 7s."""
from ortools.sat.python import cp_model
from sky7Jcx_shape import stats
cells = [(r, c) for r in range(9) for c in range(9)]
def line(t):
    i = int(t[1:-1]) - 1; seq = [(i, c) for c in range(9)] if t[0] == "r" else [(r, i) for r in range(9)]
    return seq[::-1] if t[-1] in "RB" else seq
def count(REG, G, out, givens):
    m = cp_model.CpModel(); x = {p: m.NewIntVar(1, 9, "") for p in cells}
    for i in range(9):
        m.AddAllDifferent([x[i, c] for c in range(9)]); m.AddAllDifferent([x[r, i] for r in range(9)])
    for k in "ABCDEFGHI":
        rc = [p for p in cells if REG[p[0]][p[1]] == k]; assert len(rc) == 9; assert sorted(G[p] for p in rc) == list(range(1, 10)); m.AddAllDifferent([x[p] for p in rc])
    if givens:
        for p in cells:
            if G[p] == 7: m.Add(x[p] == 7)
    for t in out.split():
        seq = line(t); vb = []
        for j, p in enumerate(seq):
            bb = m.NewBoolVar("")
            if j == 0: m.Add(bb == 1)
            else:
                gt = []
                for q in seq[:j]:
                    g = m.NewBoolVar(""); m.Add(x[p] > x[q]).OnlyEnforceIf(g); m.Add(x[p] <= x[q]).OnlyEnforceIf(g.Not()); gt.append(g)
                m.AddBoolAnd(gt).OnlyEnforceIf(bb); m.AddBoolOr([g.Not() for g in gt]).OnlyEnforceIf(bb.Not())
            vb.append(bb)
        m.Add(sum(vb) == 7)
    n = [0]
    class C(cp_model.CpSolverSolutionCallback):
        def on_solution_callback(s):
            n[0] += 1
            if n[0] >= 3: s.StopSearch()
    s = cp_model.CpSolver(); s.parameters.enumerate_all_solutions = True; s.parameters.num_workers = 1; s.parameters.max_time_in_seconds = 300
    st = s.Solve(m, C()); return (str(n[0]) if st == cp_model.OPTIMAL else f">={n[0]}") + " " + s.StatusName(st)
import json, sys
F = json.load(open(sys.argv[1]))
for k, d in enumerate(F):
    reg = d["reg"]; REG = [reg[i*9:i*9+9] for i in range(9)]; g = d["grid"]
    G = {(r, c): int(g[r*9+c]) for r in range(9) for c in range(9)}
    pos = []
    for t in d["out"].split():
        seq = line(t); pos.append([G[p] for p in seq].index(7) + 1)
    vis_ok = all(sum(1 for j, p in enumerate(line(t)) if all(G[p] > G[q] for q in line(t)[:j])) == 7 for t in d["out"].split())
    print(k, d["found"].split(" (")[0], "| boundary %d, max line %d, straight %d, min span %d" % stats(reg), "| 7 at cells", sorted(pos), "c6=%d c5=%d" % (pos.count(6), pos.count(5)), "| clues read 7:", vis_ok, "| with 7s:", count(REG, G, d["out"], True), "| no givens:", count(REG, G, d["out"], False), flush=True)

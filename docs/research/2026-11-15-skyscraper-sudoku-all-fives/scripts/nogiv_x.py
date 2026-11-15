"""SCRATCH cross-check of nogiv.py on an independent visibility encoding: no givens, all value-lines shown; count to 3. Args: page_boards.json id,id,..."""
import sys, json, re
from ortools.sat.python import cp_model
D = {"boards": json.load(open(sys.argv[1]))}
IDS = set(sys.argv[2].split(","))
cells = [(r, c) for r in range(9) for c in range(9)]
def line(t):
    i = int(t[1:-1]) - 1; seq = [(i, c) for c in range(9)] if t[0] == "r" else [(r, i) for r in range(9)]
    return seq[::-1] if t[-1] in "RB" else seq
def vis(v):
    m = n = 0
    for a in v:
        if a > m: m = a; n += 1
    return n
ALL = [s + str(i) + e for i in range(1, 10) for s, ends in (("r", "LR"), ("c", "TB")) for e in ends]
for b in D["boards"]:
    if b["id"] not in IDS: continue
    V = {"7J": 7}.get(b["v"], b["v"]); G = {p: int(b["grid"][p[0] * 9 + p[1]]) for p in cells}
    lay = [t for t in ALL if vis([G[p] for p in line(t)]) == V]
    rg = b.get("reg"); key = (lambda p: rg[p[0] * 9 + p[1]]) if rg else (lambda p: (p[0] // 3, p[1] // 3))
    m = cp_model.CpModel(); x = {p: m.NewIntVar(1, 9, "") for p in cells}
    for i in range(9):
        m.AddAllDifferent([x[i, c] for c in range(9)]); m.AddAllDifferent([x[r, i] for r in range(9)])
    for k in {key(p) for p in cells}: m.AddAllDifferent([x[p] for p in cells if key(p) == k])
    for t in lay:
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
        m.Add(sum(vb) == V)
    sols = []
    class C(cp_model.CpSolverSolutionCallback):
        def on_solution_callback(s):
            sols.append({p: s.Value(x[p]) for p in cells})
            if len(sols) >= 3: s.StopSearch()
    s = cp_model.CpSolver(); s.parameters.enumerate_all_solutions = True; s.parameters.num_workers = 1; s.parameters.max_time_in_seconds = 120
    st = s.Solve(m, C())
    print(b["id"], len(lay), "clues;", len(sols), "solution(s)", s.StatusName(st), "matches grid:", bool(sols) and sols[0] == G, flush=True)

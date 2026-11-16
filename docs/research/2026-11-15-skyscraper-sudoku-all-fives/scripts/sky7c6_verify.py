"""SCRATCH: independent check of the sixth-cell box board: solutions to 3, own visibility encoding; distances of each clue's 7."""
from ortools.sat.python import cp_model
cells = [(r, c) for r in range(9) for c in range(9)]
def line(t):
    i = int(t[1:-1]) - 1; seq = [(i, c) for c in range(9)] if t[0] == "r" else [(r, i) for r in range(9)]
    return seq[::-1] if t[-1] in "RB" else seq
G0 = "285631947317924856469875321598716432642593718731482695124367589956148273873259164"; OUT = "c1T r3R r4R c4B c6T r7L c7B"
G = {(r, c): int(G0[r * 9 + c]) for r, c in cells}
def vis(s):
    m = n = 0
    for d in s:
        if d > m: m = d; n += 1
    return n
print("lines reading 7:", [t for t in [f"{a}{i}{s}" for a in "rc" for i in range(1, 10) for s in ("LR" if a == "r" else "TB")] if vis([G[p] for p in line(t)]) == 7])
print("cell of the 7 per clue:", {t: [G[p] for p in line(t)].index(7) + 1 for t in OUT.split()})
m = cp_model.CpModel(); x = {p: m.NewIntVar(1, 9, "") for p in cells}
for i in range(9):
    m.AddAllDifferent([x[i, c] for c in range(9)]); m.AddAllDifferent([x[r, i] for r in range(9)])
    m.AddAllDifferent([x[3 * (i // 3) + a, 3 * (i % 3) + b] for a in range(3) for b in range(3)])
for p in cells:
    if G[p] == 7: m.Add(x[p] == 7)
for t in OUT.split():
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
st = s.Solve(m, C()); print("solutions", n[0], s.StatusName(st))

"""SCRATCH: count solutions (to 3) of the complex-region jigsaw finds, own visibility encoding, with and without inner 7s."""
from ortools.sat.python import cp_model
from sky7Jcx_shape import stats
cells = [(r, c) for r in range(9) for c in range(9)]
def line(t):
    i = int(t[1:-1]) - 1; seq = [(i, c) for c in range(9)] if t[0] == "r" else [(r, i) for r in range(9)]
    return seq[::-1] if t[-1] in "RB" else seq
A = ("345621789 476912358 529843167 698754231 213467895 134578926 752389614 861295473 987136542", "r1L c1T r4R c4B r5L c5T r6L c6T r9R c9B")
B7 = ("751289643 862395174 123478965 234517896 987164532 498756321 619843257 576932418 345621789", "r3L c3T r4L c4T r5R c5B r6R c6B r9L c9T")
C8 = ("546193278 712984365 369875421 498761532 987652143 125346789 234517896 653428917 871239654", "r3R c3B r4R c4B r5R c5B r6L c6T r7L c7T")
B = {"jcx1": ("AAAAABBBB CCCAABDBE CCCADBDBE FFCADBDEE FCCGDDDDE FFFGHIEEE FFGGHIIIE FGGHHIIII GGGHHHHHI",) + A,
     "jcx2": ("AAAAABBBB CACAABDBE CCCABBDBE FFCCDDDEE FCCGDHIEE FFFGDHIEE FFGGDHIIE FGGHDHHII GGGHHHIII",) + A,
     "jcx3": ("AAAAABBBB CACAABDBE CCCADBDBE FFCCDBDEE FCCGDDDDE FFFGHIEEE FFGGHIIIE FGGHHIHII GGGHHHHII",) + A,
     "jcx4": ("AAAAABBBB CACAABDBE CCCADBDBE FFCCDBDEE FCCGDDDDE FFFGGHEEE FFGGIHHHE FGGIIHIHH GGIIIIIHH",) + A,
     "jcx5": ("AAABBBBBB AAAAABBBC DEEAEEEEC DDEEECCCC DDDFFFFCC DGGFHIFFC DGFFHIIII DGHHHHIII GGGGGHHHI",) + B7,
     "jcx6": ("AABBCCCCC AAABBCBCC AADDBBBBC EAADDDDDF EEEEEDGDF EGGGGGGFF EEHHHHGGF IIHIHHHFF IIIIIIHFF",) + C8}
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
for name, (reg, grid, out) in B.items():
    REG = reg.split(); G0 = grid.split(); G = {(r, c): int(G0[r][c]) for r in range(9) for c in range(9)}
    print(name, "boundary %d, max line %d, straight %d, min span %d" % stats(reg.replace(" ", "")), "| with 7s:", count(REG, G, out, True), "| no givens:", count(REG, G, out, False), flush=True)

"""SCRATCH: feasibility probe. For Latin squares showing 10 outside 7s (stage 1 of sky7J2s), can 9 connected
regions holding 1-9 be drawn under stricter shape rules? No uniqueness check. sky7Jcxp.py <ngrids> <per_solve_s>"""
import sys, time, importlib.util
args = sys.argv; spec = importlib.util.spec_from_file_location("t", args[0].replace("sky7Jcxp.py", "sky7J2s.py"))
sys.argv = [args[0].replace("sky7Jcxp.py", "sky7J2s.py"), "0", "0", "0"]
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T); sys.argv = args
cp_model, cells, N = T.cp_model, T.cells, T.N
NG, PER = int(args[1]), float(args[2])
LEVELS = [("line<=6 span>=2", 6, 2), ("line<=5 span>=2", 5, 2), ("line<=5 span>=3", 5, 3), ("line<=4 span>=3", 4, 3)]
for g in range(NG):
    s1 = T.solver(300, seed=g + 500); st = s1.Solve(T.g1)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): print("stage 1", s1.StatusName(st), flush=True); break
    G = {p: s1.Value(T.x1[p]) for p in cells}; T.ban_grid(G)
    row = []
    for name, ml, sp in LEVELS:
        t0 = time.time()
        m, reg = T.region_model(G, maxdeg=0, maxline=ml, span=True, span_min=sp, nobox=False, asym=False)
        s = T.solver(PER); st = s.Solve(m)
        row.append(f"{name}: {s.StatusName(st)} {time.time()-t0:.0f}s")
        if st == cp_model.INFEASIBLE: break  # stricter levels are infeasible too
    print(f"grid {g+1} " + " ".join("".join(str(G[(r, c)]) for c in range(N)) for r in range(N)) + " | " + "; ".join(row), flush=True)

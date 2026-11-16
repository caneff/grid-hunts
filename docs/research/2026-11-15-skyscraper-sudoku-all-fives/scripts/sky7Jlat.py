"""SCRATCH: Latin squares showing 10 outside 7s (with a clued line starting 12 or 21),
each tiled into 9 connected regions holding 1-9, at most one region degenerate (all in
one row or one column); no other region rule. sky7Jlat.py <total_cap_s> <per_grid_s> <max_found>"""
import sys, time, importlib.util
spec = importlib.util.spec_from_file_location("t", sys.argv[0].replace("sky7Jlat.py", "sky7J2s.py"))
args = sys.argv; sys.argv = [args[0].replace("sky7Jlat.py", "sky7J2s.py"), "0", "0", "0"]
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T); sys.argv = args
cp_model, cells, N, K, NAMES = T.cp_model, T.cells, T.N, T.K, T.NAMES
CAP, PER, MAXF = float(args[1]), float(args[2]), int(args[3])
t0 = time.time(); found = ngrid = 0
while time.time() - t0 < CAP and found < MAXF:
    s1 = T.solver(300, seed=ngrid); st = s1.Solve(T.g1)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): print("stage 1", s1.StatusName(st), flush=True); break
    G = {p: s1.Value(T.x1[p]) for p in cells}; lay = [t for t in NAMES if s1.Value(T.oc[t])]
    T.ban_grid(G); ngrid += 1
    m, reg = T.region_model(G, maxdeg=1, span=False, nobox=False, asym=False)
    s = T.solver(PER); st = s.Solve(m)
    gtxt = " ".join("".join(str(G[(r, c)]) for c in range(N)) for r in range(N))
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        found += 1; R = {p: next(k for k in range(K) if s.Value(reg[p, k])) for p in cells}
        print(f"FOUND {found} (grid {ngrid}, {time.time()-t0:.0f}s)", flush=True)
        print("  regions " + " ".join("".join("ABCDEFGHI"[R[(r, c)]] for c in range(N)) for r in range(N)), flush=True)
        print("  grid    " + gtxt, flush=True); print("  outside " + " ".join(lay), flush=True)
    else:
        print(f"grid {ngrid}: {s.StatusName(st)} ({time.time()-t0:.0f}s)  {gtxt}", flush=True)
print(f"done: {found} found, {ngrid} grids, {time.time()-t0:.0f}s", flush=True)

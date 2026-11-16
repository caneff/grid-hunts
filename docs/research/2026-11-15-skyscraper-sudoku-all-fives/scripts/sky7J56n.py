"""SCRATCH: neighbourhood variant: stage-1 grids stay within <dist> cells of <base> grid (a grid known to tile). jigsaw all-7s, every inner 7 given, 10 outside 7s, 4 clued lines with the 7 in cell 6 and 2 in cell 5
(the caps). Complex regions: no straight region, at most 6 cells of a region in a row or column, each region
spanning >= 2 rows and columns. Stage 1 draws a Latin square with that clue pattern; stage 2 loops tilings, cutting
each rival by putting two of its equal digits in one region; after a unique board it asks for more region edges.
Each find is also counted with no inner givens. sky7J56n.py <total_cap_s> <per_grid_s> <base81> <dist> [seed0]"""
import sys, time, importlib.util
args = sys.argv; spec = importlib.util.spec_from_file_location("t", args[0].replace("sky7J56n.py", "sky7J2s.py"))
sys.argv = [args[0].replace("sky7J56n.py", "sky7J2s.py"), "0", "0", "0"]
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T); sys.argv = args
cp_model, cells, N, K, L = T.cp_model, T.cells, T.N, T.K, T.L
CAP, PER = float(args[1]), float(args[2]); BASE, DIST = args[3], int(args[4]); SEED0 = int(args[5]) if len(args) > 5 else 900
g1, x1 = T.g1, T.x1
c6, c5 = [], []
for t in T.NAMES:
    for pos, acc in ((5, c6), (4, c5)):
        b = g1.NewBoolVar(""); g1.AddImplication(b, T.oc[t]); g1.Add(x1[T.LINES[t][pos]] == 7).OnlyEnforceIf(b); acc.append(b)
g1.Add(sum(c6) >= 4); g1.Add(sum(c5) >= 2)
dif = []
for p in cells:
    b = g1.NewBoolVar(""); g1.Add(x1[p] != int(BASE[p[0] * 9 + p[1]])).OnlyEnforceIf(b); g1.Add(x1[p] == int(BASE[p[0] * 9 + p[1]])).OnlyEnforceIf(b.Not()); dif.append(b)
g1.Add(sum(dif) <= DIST); g1.Add(sum(dif) >= 1)
edges = [((r, c), (r, c + 1)) for r in range(N) for c in range(N - 1)] + [((r, c), (r + 1, c)) for r in range(N - 1) for c in range(N)]
T0 = time.time(); ngrid = nfound = 0
while time.time() - T0 < CAP:
    s1 = T.solver(300, seed=SEED0 + ngrid); st = s1.Solve(g1)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): print("stage 1", s1.StatusName(st), flush=True); break
    G = {p: s1.Value(x1[p]) for p in cells}; T.ban_grid(G); ngrid += 1
    lay = [t for t in T.NAMES if s1.Value(T.oc[t])]; gs = "".join(str(G[p]) for p in cells)
    m, reg = T.region_model(G, maxdeg=0, maxline=6, span=True, span_min=2, nobox=False, asym=False); same = {}
    bnd = []
    for p, q in edges:
        b = m.NewBoolVar(""); bnd.append(b)
        for k in range(K): m.AddBoolOr([b.Not(), reg[p, k].Not(), reg[q, k].Not()])
    def same_lit(p, q):
        key = (min(p, q), max(p, q))
        if key not in same:
            s = m.NewBoolVar("")
            for k in range(K): m.Add(reg[p, k] == reg[q, k]).OnlyEnforceIf(s)
            same[key] = s
        return same[key]
    t0 = time.time(); it = nf = 0; msg = "time cap"
    while time.time() - t0 < PER:
        it += 1
        s = T.solver(max(5, PER - (time.time() - t0))); st = s.Solve(m)
        if st == cp_model.INFEASIBLE: msg = "no tiling" if it == 1 else "no layout left"; break
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): msg = "layout search timed out"; break
        R = {p: next(k for k in range(K) if s.Value(reg[p, k])) for p in cells}
        rv, uniq = T.rivals_of(G, R, lay, givens=True)
        if uniq and not rv:
            nb = sum(R[p] != R[q] for p, q in edges); nf += 1; nfound += 1
            rv0, u0 = T.rivals_of(G, R, lay, givens=False)
            print(f"FOUND grid {ngrid} #{nf} edges {nb} no-givens {'unique' if u0 and not rv0 else 'not unique' if rv0 else 'unknown'} (pass {it}, {time.time()-T0:.0f}s)", flush=True)
            print("  regions " + " ".join("".join("ABCDEFGHI"[R[(r, c)]] for c in range(N)) for r in range(N)), flush=True)
            print("  grid    " + " ".join(gs[i:i + 9] for i in range(0, 81, 9)), flush=True); print("  outside " + " ".join(lay), flush=True)
            m.Add(sum(bnd) >= nb + 1); continue
        if not rv: msg = "rival check timed out"; break
        for G2 in rv:
            byd = {}
            for p in cells: byd.setdefault(G2[p], []).append(p)
            m.AddBoolOr([same_lit(p, q) for ps in byd.values() for i, p in enumerate(ps) for q in ps[i + 1:]])
    print(f"grid {ngrid} [{gs}] differs {sum(gs[i] != BASE[i] for i in range(81))}: {msg} after {it} passes, {nf} found, {time.time()-t0:.0f}s ({time.time()-T0:.0f}s total)", flush=True)
print(f"done: {nfound} found over {ngrid} grids, {time.time()-T0:.0f}s", flush=True)

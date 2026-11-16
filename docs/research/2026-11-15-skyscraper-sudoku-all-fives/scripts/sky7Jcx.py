"""SCRATCH: all inner 7s given, 10 outside 7s, complex regions: no straight region, at most 6 cells of a region in
one row or column, each region spans >= 2 rows and >= 2 columns. On each fixed grid, loop tilings and cut each rival
by putting two of its equal digits in one region; after each unique board, demand a different layout with more
region-boundary edges. sky7Jcx.py <per_grid_s> grid ..."""
import sys, time, importlib.util
args = sys.argv; spec = importlib.util.spec_from_file_location("t", args[0].replace("sky7Jcx.py", "sky7J2s.py"))
sys.argv = [args[0].replace("sky7Jcx.py", "sky7J2s.py"), "0", "0", "0"]
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T); sys.argv = args
cp_model, cells, N, K, L = T.cp_model, T.cells, T.N, T.K, T.L
PER = float(args[1])
edges = [((r, c), (r, c + 1)) for r in range(N) for c in range(N - 1)] + [((r, c), (r + 1, c)) for r in range(N - 1) for c in range(N)]
for g in args[2:]:
    G = {(r, c): int(g[r * 9 + c]) for r in range(N) for c in range(N)}
    lay = [t for t in T.NAMES if L.sky([G[p] for p in T.LINES[t]]) == 7]
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
    print(f"grid {g[:9]}.. outside {len(lay)}: {' '.join(lay)}", flush=True)
    t0 = time.time(); it = nf = 0
    while time.time() - t0 < PER:
        it += 1
        s = T.solver(max(5, PER - (time.time() - t0))); st = s.Solve(m)
        if st == cp_model.INFEASIBLE: print(f"  pass {it}: no layout left ({time.time()-t0:.0f}s)", flush=True); break
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): print(f"  pass {it}: layout search timed out", flush=True); break
        R = {p: next(k for k in range(K) if s.Value(reg[p, k])) for p in cells}
        rv, uniq = T.rivals_of(G, R, lay, givens=True)
        if uniq and not rv:
            nb = sum(R[p] != R[q] for p, q in edges); nf += 1
            print(f"FOUND {g[:9]} #{nf} boundary {nb} (pass {it}, {time.time()-t0:.0f}s)", flush=True)
            print("  regions " + " ".join("".join("ABCDEFGHI"[R[(r, c)]] for c in range(N)) for r in range(N)), flush=True)
            print("  grid    " + " ".join(g[i:i + 9] for i in range(0, 81, 9)), flush=True); print("  outside " + " ".join(lay), flush=True)
            m.Add(sum(bnd) >= nb + 1)
            continue
        if not rv: print(f"  pass {it}: rival check timed out", flush=True); break
        for G2 in rv:
            byd = {}
            for p in cells: byd.setdefault(G2[p], []).append(p)
            m.AddBoolOr([same_lit(p, q) for ps in byd.values() for i, p in enumerate(ps) for q in ps[i + 1:]])
    else:
        print(f"  time cap after {it} passes, {nf} found", flush=True)

"""SCRATCH: for a fixed Latin square with its 10 outside 7s, search tilings (9 connected regions
holding 1-9, at most one degenerate) for a unique board; each rival is cut by putting two of its
equal digits in one region. sky7Jloop.py <per_grid_s>"""
import sys, time, importlib.util
spec = importlib.util.spec_from_file_location("t", sys.argv[0].replace("sky7Jloop.py", "sky7J2s.py"))
args = sys.argv; sys.argv = [args[0].replace("sky7Jloop.py", "sky7J2s.py"), "0", "0", "0"]
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T); sys.argv = args
cp_model, cells, N, K = T.cp_model, T.cells, T.N, T.K
PER = float(args[1])
GRIDS = {"#1": ("721384965 132457896 243561789 865293174 374129658 987612543 698745321 519876432 456938217", "r2L c2T r3L c3T c4T r6R r7R c7B r8R c8B"),
         "#3": ("345791268 426983175 659874321 798165432 987612543 134527689 213456897 572348916 861239754", "r3R c3B r4R c4B r5R c5B r6L c6T r7L c7T")}
for name, (grid, out) in GRIDS.items():
    G0 = grid.split(); G = {(r, c): int(G0[r][c]) for r in range(N) for c in range(N)}; lay = out.split()
    m, reg = T.region_model(G, maxdeg=1, span=False, nobox=False, asym=False); same = {}
    def same_lit(p, q):
        key = (min(p, q), max(p, q))
        if key not in same:
            s = m.NewBoolVar("")
            for k in range(K): m.Add(reg[p, k] == reg[q, k]).OnlyEnforceIf(s)
            same[key] = s
        return same[key]
    t0 = time.time(); it = 0
    while time.time() - t0 < PER:
        it += 1
        s = T.solver(max(5, PER - (time.time() - t0))); st = s.Solve(m)
        if st == cp_model.INFEASIBLE: print(f"{name} pass {it}: no tiling left, so no unique board on this grid ({time.time()-t0:.0f}s)", flush=True); break
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): print(f"{name} pass {it}: tiling search timed out", flush=True); break
        R = {p: next(k for k in range(K) if s.Value(reg[p, k])) for p in cells}
        rv, uniq = T.rivals_of(G, R, lay)
        if uniq and not rv:
            print(f"FOUND {name} (pass {it}, {time.time()-t0:.0f}s)", flush=True)
            print("  regions " + " ".join("".join("ABCDEFGHI"[R[(r, c)]] for c in range(N)) for r in range(N)), flush=True)
            print("  grid    " + grid, flush=True); print("  outside " + out, flush=True)
            break
        if not rv: print(f"{name} pass {it}: rival check timed out", flush=True); break
        for G2 in rv:
            byd = {}
            for p in cells: byd.setdefault(G2[p], []).append(p)
            m.AddBoolOr([same_lit(p, q) for ps in byd.values() for i, p in enumerate(ps) for q in ps[i + 1:]])
        if it == 1 or it % 5 == 0: print(f"{name} pass {it}: {len(rv)} rivals cut ({time.time()-t0:.0f}s)", flush=True)
    else:
        print(f"{name}: no unique board in {PER:.0f}s", flush=True)

"""SCRATCH (no inside givens; apart from the one straight region, no region has 7+ cells in one row or column: the outside 7s alone must make the board unique): over many Latin squares (stage 1 of sky7J2s), for each with its 10 outside 7s, search tilings (9 connected regions
holding 1-9, at most one degenerate) for a unique board; each rival is cut by putting two of its
equal digits in one region. sky7Jng4.py <total_cap_s> <per_grid_s> <max_found> [seed0]"""
import sys, time, importlib.util
spec = importlib.util.spec_from_file_location("t", sys.argv[0].replace("sky7Jng4.py", "sky7J2s.py"))
args = sys.argv; sys.argv = [args[0].replace("sky7Jng4.py", "sky7J2s.py"), "0", "0", "0"]
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T); sys.argv = args
cp_model, cells, N, K = T.cp_model, T.cells, T.N, T.K
CAP, PER, MAXF = float(args[1]), float(args[2]), int(args[3]); SEED0 = int(args[4]) if len(args) > 4 else 100
T0 = time.time(); found = 0; ngrid = 0
T.ban_grid({p: int("721384965132457896243561789865293174374129658987612543698745321519876432456938217"[p[0] * 9 + p[1]]) for p in cells})
T.ban_grid({p: int("345791268426983175659874321798165432987612543134527689213456897572348916861239754"[p[0] * 9 + p[1]]) for p in cells})
def grids():
    global ngrid
    while time.time() - T0 < CAP and found < MAXF:
        s1 = T.solver(300, seed=ngrid + SEED0); st = s1.Solve(T.g1)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): print("stage 1", s1.StatusName(st), flush=True); return
        G = {p: s1.Value(T.x1[p]) for p in cells}; T.ban_grid(G); ngrid += 1
        yield f"g{ngrid}", (" ".join("".join(str(G[(r, c)]) for c in range(N)) for r in range(N)), " ".join(t for t in T.NAMES if s1.Value(T.oc[t])))
for name, (grid, out) in grids():
    G0 = grid.split(); G = {(r, c): int(G0[r][c]) for r in range(N) for c in range(N)}; lay = out.split()
    m, reg = T.region_model(G, maxdeg=1, maxline=6, span=False, nobox=False, asym=False); same = {}
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
        rv, uniq = T.rivals_of(G, R, lay, givens=False)
        if uniq and not rv:
            found += 1; print(f"FOUND {found} {name} (pass {it}, {time.time()-T0:.0f}s total)", flush=True)
            print("  regions " + " ".join("".join("ABCDEFGHI"[R[(r, c)]] for c in range(N)) for r in range(N)), flush=True)
            print("  grid    " + grid, flush=True); print("  outside " + out, flush=True)
            break
        if not rv: print(f"{name} pass {it}: rival check timed out", flush=True); break
        for G2 in rv:
            byd = {}
            for p in cells: byd.setdefault(G2[p], []).append(p)
            m.AddBoolOr([same_lit(p, q) for ps in byd.values() for i, p in enumerate(ps) for q in ps[i + 1:]])
    else:
        print(f"{name}: no unique board in {PER:.0f}s", flush=True)
print(f"done: {found} found, {ngrid} grids, {time.time()-T0:.0f}s", flush=True)

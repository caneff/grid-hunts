"""SCRATCH: two-stage jigsaw hunt, all 7s. Stage 1 picks a 9x9 Latin square showing
10 outside 7s with a clued line starting 12 or 21 (a whole-grid 1-2 swap survives
any region layout otherwise). Stage 2 draws regions on that fixed grid under Chris's
rules (each region spans >=3 rows and >=3 columns, no 3x3-box region, no rotation or
reflection symmetry), then cuts rivals: each rival dies once two of its equal digits
share a region. A grid gets PER seconds, then the next grid.
sky7J2s.py <total_cap_s> <per_grid_s> <max_found> [target_outside]"""
import sys, time, importlib.util
from ortools.sat.python import cp_model
from sudoku_kit import cpsat
sp = importlib.util.spec_from_file_location("s", sys.argv[0].replace("sky7J2s.py", "sky5lib.py")); L = importlib.util.module_from_spec(sp); sp.loader.exec_module(L)
N = K = 9; V = 7; TARGET = int(sys.argv[4]) if len(sys.argv) > 4 else 10
cells, LINES, NAMES = L.cells, L.LINES, L.NAMES
CAP, PER, MAXF = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])

def solver(t, seed=0):
    s = cp_model.CpSolver(); s.parameters.max_time_in_seconds = t; s.parameters.num_workers = 1; s.parameters.random_seed = seed
    return s

# ---- stage 1: grid model
g1, x1 = cpsat.sudoku_model(N, [])
oc = {t: g1.NewBoolVar(t) for t in NAMES}
for t in NAMES: g1.Add(L.vis_expr(g1, x1, LINES[t], "g" + t) == V).OnlyEnforceIf(oc[t])
g1.Add(sum(oc.values()) == TARGET)
st12 = []
for t in NAMES:
    a, b = LINES[t][0], LINES[t][1]
    s = g1.NewBoolVar("")
    g1.Add(x1[a] + x1[b] == 3).OnlyEnforceIf(s)  # {1,2} in the first two cells
    g1.AddImplication(s, oc[t]); st12.append(s)
g1.AddBoolOr(st12)

def ban_grid(G):
    bs = []
    for p in cells:
        b = g1.NewBoolVar(""); g1.Add(x1[p] != G[p]).OnlyEnforceIf(b); bs.append(b)
    g1.AddBoolOr(bs)

def nbrs(r, c):
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if 0 <= r + dr < N and 0 <= c + dc < N: yield r + dr, c + dc

def region_model(G, maxdeg=None, maxline=None, span=True, span_axes=(0, 1), span_min=3, nobox=True, asym=True):
    m = cp_model.CpModel()
    reg = {(p, k): m.NewBoolVar("") for p in cells for k in range(K)}
    root = {(p, k): m.NewBoolVar("") for p in cells for k in range(K)}
    dep = {p: m.NewIntVar(0, 8, "") for p in cells}
    for p in cells: m.AddExactlyOne(reg[p, k] for k in range(K))
    ridx = []
    for k in range(K):
        if G is not None:
            for d in range(1, 10): m.AddExactlyOne(reg[p, k] for p in cells if G[p] == d)
        m.AddExactlyOne(root[p, k] for p in cells)
        for i, p in enumerate(cells):
            m.AddImplication(root[p, k], reg[p, k])
            for q in cells[:i]: m.AddImplication(root[p, k], reg[q, k].Not())
        v = m.NewIntVar(0, 80, ""); m.Add(v == sum(i * root[p, k] for i, p in enumerate(cells))); ridx.append(v)
    for k in range(K - 1): m.Add(ridx[k] < ridx[k + 1])
    for p in cells:
        for k in range(K):
            opts = []
            for q in nbrs(*p):
                b = m.NewBoolVar(""); m.AddImplication(b, reg[q, k]); m.Add(dep[q] < dep[p]).OnlyEnforceIf(b); opts.append(b)
            m.AddBoolOr(opts + [root[p, k], reg[p, k].Not()])
    degs = []
    for k in range(K):
        if maxdeg is not None:  # degenerate region: all 9 cells in one row or one column
            for axis in (0, 1):
                d = m.NewBoolVar("")
                for i in range(N):
                    whole = [reg[p, k] for p in cells if p[axis] == i]
                    w = m.NewBoolVar(""); m.Add(sum(whole) == N).OnlyEnforceIf(w); m.Add(sum(whole) < N).OnlyEnforceIf(w.Not())
                    if maxline is not None: m.Add(sum(whole) <= maxline).OnlyEnforceIf(w.Not())  # near-straight ban
                    m.AddImplication(w, d)
                    degs.append((d, w))
                d_any = d
                m.AddBoolOr([w for dd, w in degs if dd is d]).OnlyEnforceIf(d)
                degs.append((d, None))
    if maxdeg is not None:
        m.Add(sum({id(d): d for d, w in degs}.values()) <= maxdeg)
    for k in range(K):
        for axis in span_axes:
            occ = []
            for i in range(N):
                o = m.NewBoolVar(""); lc = [p for p in cells if p[axis] == i]
                m.AddBoolOr([reg[p, k] for p in lc]).OnlyEnforceIf(o)
                for p in lc: m.AddImplication(reg[p, k], o)
                occ.append(o)
            if span: m.Add(sum(occ) >= span_min)
        for br in range(3):
            for bc in range(3):
                if nobox: m.AddBoolOr([reg[(3 * br + i, 3 * bc + j), k].Not() for i in range(3) for j in range(3)])
    edges = [((r, c), (r, c + 1)) for r in range(N) for c in range(N - 1)] + [((r, c), (r + 1, c)) for r in range(N - 1) for c in range(N)]
    same_e = {}
    for p, q in edges:
        zs = []
        for k in range(K):
            z = m.NewBoolVar(""); m.AddImplication(z, reg[p, k]); m.AddImplication(z, reg[q, k]); m.AddBoolOr([reg[p, k].Not(), reg[q, k].Not(), z]); zs.append(z)
        e = m.NewBoolVar(""); m.Add(e == sum(zs)); same_e[p, q] = same_e[q, p] = e
    syms = [lambda r, c: (c, N - 1 - r), lambda r, c: (N - 1 - r, N - 1 - c), lambda r, c: (N - 1 - c, r),
            lambda r, c: (r, N - 1 - c), lambda r, c: (N - 1 - r, c), lambda r, c: (c, r), lambda r, c: (N - 1 - c, N - 1 - r)]
    for f in syms:
        ds = []
        for p, q in edges:
            d = m.NewBoolVar(""); m.Add(same_e[p, q] != same_e[f(*p), f(*q)]).OnlyEnforceIf(d); ds.append(d)
        if asym: m.AddBoolOr(ds)
    return m, reg

def rivals_of(G, R, lay, givens=True):
    m2, x2 = cpsat.sudoku_model(N, [[p for p in cells if R[p] == k] for k in range(K)])
    if givens:
        for p in cells:
            if G[p] == V: m2.Add(x2[p] == V)
    for t in lay: m2.Add(L.vis_expr(m2, x2, LINES[t], "q" + t) == V)
    out = []
    while len(out) < 20:
        bs = []
        for H in [G] + out:
            b_any = []
            for p in cells:
                b = m2.NewBoolVar(""); m2.Add(x2[p] != H[p]).OnlyEnforceIf(b); b_any.append(b)
            bs.append(b_any)
        for b_any in bs[len(bs) - 1:] if out else bs: m2.AddBoolOr(b_any)
        s = solver(120); st = s.Solve(m2)
        if st == cp_model.INFEASIBLE: return out, True
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): return out, None
        out.append({p: s.Value(x2[p]) for p in cells})
    return out, False

t0 = time.time(); found = ngrid = 0
while time.time() - t0 < CAP and found < MAXF:
    s1 = solver(300, seed=ngrid); st = s1.Solve(g1)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("stage 1", s1.StatusName(st), flush=True); break
    G = {p: s1.Value(x1[p]) for p in cells}; lay = [t for t in NAMES if s1.Value(oc[t])]
    ban_grid(G); ngrid += 1; tg = time.time()
    print(f"grid {ngrid} ({time.time()-t0:.0f}s): " + " ".join("".join(str(G[(r, c)]) for c in range(N)) for r in range(N)) + "  outside " + " ".join(lay), flush=True)
    m, reg = region_model(G); same = {}
    def same_lit(p, q):
        key = (min(p, q), max(p, q))
        if key not in same:
            s = m.NewBoolVar("")
            for k in range(K): m.Add(reg[p, k] == reg[q, k]).OnlyEnforceIf(s)
            same[key] = s
        return same[key]
    it = 0
    while time.time() - tg < PER and found < MAXF:
        it += 1
        s = solver(max(5, PER - (time.time() - tg))); st = s.Solve(m)
        if st == cp_model.INFEASIBLE:
            print(f"  pass {it}: no region layout left for this grid", flush=True); break
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print(f"  pass {it}: region search timed out", flush=True); break
        R = {p: next(k for k in range(K) if s.Value(reg[p, k])) for p in cells}
        rv, uniq = rivals_of(G, R, lay)
        if uniq and not rv:
            found += 1
            print(f"FOUND {found} (grid {ngrid}, pass {it}, {time.time()-t0:.0f}s) {TARGET + 9} clues: {TARGET} outside + 9 inside", flush=True)
            print("  regions " + " ".join("".join("ABCDEFGHI"[R[(r, c)]] for c in range(N)) for r in range(N)), flush=True)
            print("  grid    " + " ".join("".join(str(G[(r, c)]) for c in range(N)) for r in range(N)), flush=True)
            print("  outside " + " ".join(lay), flush=True)
            m.AddBoolOr([reg[p, R[p]].Not() for p in cells])  # next layout differs
            break  # one board per grid keeps the finds varied
        if not rv:
            print(f"  pass {it}: rival check timed out", flush=True); break
        for G2 in rv:
            byd = {}
            for p in cells: byd.setdefault(G2[p], []).append(p)
            m.AddBoolOr([same_lit(p, q) for ps in byd.values() for i, p in enumerate(ps) for q in ps[i + 1:]])
        print(f"  pass {it}: {len(rv)} rivals cut ({time.time()-tg:.0f}s on this grid)", flush=True)
print(f"done: {found} found, {ngrid} grids, {time.time()-t0:.0f}s", flush=True)

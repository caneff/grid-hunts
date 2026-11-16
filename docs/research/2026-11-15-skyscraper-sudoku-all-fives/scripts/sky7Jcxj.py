"""SCRATCH: joint feasibility. One model: a Latin square showing <target> outside 7s (a clued line starting 12/21)
plus 9 connected regions holding 1-9, no straight region, at most <maxline> cells of a region in a row or column,
each region spanning >= <span> rows and columns. No uniqueness check. sky7Jcxj.py <per_s> target:maxline:span ..."""
import sys, time, importlib.util
args = sys.argv; spec = importlib.util.spec_from_file_location("t", args[0].replace("sky7Jcxj.py", "sky7J2s.py"))
sys.argv = [args[0].replace("sky7Jcxj.py", "sky7J2s.py"), "0", "0", "0"]
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T); sys.argv = args
cp_model, cells, N, K, L = T.cp_model, T.cells, T.N, T.K, T.L
PER = float(args[1])
for cfg in args[2:]:
    tgt, ml, sp = map(int, cfg.split(":")); t0 = time.time()
    m, reg = T.region_model(None, maxdeg=0, maxline=ml, span=True, span_min=sp, nobox=False, asym=False)
    y = {(p, d): m.NewBoolVar("") for p in cells for d in range(1, 10)}
    x = {p: m.NewIntVar(1, 9, "") for p in cells}
    for p in cells: m.AddExactlyOne(y[p, d] for d in range(1, 10)); m.Add(x[p] == sum(d * y[p, d] for d in range(1, 10)))
    for i in range(N):
        for d in range(1, 10):
            m.AddExactlyOne(y[(i, c), d] for c in range(N)); m.AddExactlyOne(y[(r, i), d] for r in range(N))
    for k in range(K):
        for d in range(1, 10):
            zs = []
            for p in cells:
                z = m.NewBoolVar(""); m.AddImplication(z, reg[p, k]); m.AddImplication(z, y[p, d]); m.AddBoolOr([reg[p, k].Not(), y[p, d].Not(), z]); zs.append(z)
            m.Add(sum(zs) == 1)
    oc = {t: m.NewBoolVar(t) for t in T.NAMES}
    for t in T.NAMES: m.Add(L.vis_expr(m, x, T.LINES[t], "j" + t) == 7).OnlyEnforceIf(oc[t])
    m.Add(sum(oc.values()) == tgt)
    st12 = []
    for t in T.NAMES:
        a, b = T.LINES[t][0], T.LINES[t][1]; s = m.NewBoolVar(""); m.Add(x[a] + x[b] == 3).OnlyEnforceIf(s); m.AddImplication(s, oc[t]); st12.append(s)
    m.AddBoolOr(st12)
    s = T.solver(PER); st = s.Solve(m)
    print(f"outside {tgt}, line<={ml}, span>={sp}: {s.StatusName(st)} {time.time()-t0:.0f}s", flush=True)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("  regions " + " ".join("".join("ABCDEFGHI"[next(k for k in range(K) if s.Value(reg[(r, c), k]))] for c in range(N)) for r in range(N)), flush=True)
        print("  grid    " + " ".join("".join(str(s.Value(x[(r, c)])) for c in range(N)) for r in range(N)), flush=True)
        print("  outside " + " ".join(t for t in T.NAMES if s.Value(oc[t])), flush=True)

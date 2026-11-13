"""SCRATCH: cut-loop hunt, new rule. Full top circled, r1L circled, r2L not,
5 of 6 top first cells circled with the uncircled one in c1-c3, 11 outside,
outside values = one 1 + ten in 5-8, 36 circles total."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nrmodel as M
from ortools.sat.python import cp_model

cells, K, allpos = M.cells, M.K, M.allpos
NOUT = int(sys.argv[2]) if len(sys.argv) > 2 else 11
ALTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alts_new.jsonl" if NOUT == 11 else f"alts_new{NOUT}.jsonl")
TOP = [f"c{i}T" for i in range(1, 7)]


def gname(p):
    return f"r{p[0]+1}c{p[1]+1}"


def fix_common(h):
    m = h["m"]
    if not os.environ.get("FREETOTAL"): m.Add(sum(h["oc"].values()) + sum(h["gc"].values()) == 36)


def master():
    h = M.build(); m, oc, gc, val, y = h["m"], h["oc"], h["gc"], h["val"], h["y"]
    for t in (TOP if NOUT != 10 else TOP[3:]) + ["r1L"]:
        m.Add(oc[t] == 1)
    if NOUT == 10:  # the top clue over the uncircled first cell is dropped
        for c in range(3):
            m.Add(oc[f"c{c+1}T"] == gc[(0, c)])
    m.Add(oc["r2L"] == 0)
    m.Add(sum(oc.values()) == NOUT)
    for p in [(0, 3), (0, 4), (0, 5)]:
        m.Add(gc[p] == 1)
    m.Add(sum(gc[(0, c)] for c in range(3)) == 2)
    ones, highs = [], []
    for t in allpos:
        m.AddLinearExpressionInDomain(val[t], cp_model.Domain.FromValues([1, 5, 6, 7, 8] if NOUT in (10, 11) else [1, 2, 3, 4, 5, 6, 7, 8])).OnlyEnforceIf(oc[t])
        hb = m.NewBoolVar(""); m.AddLinearExpressionInDomain(val[t], cp_model.Domain(5, 8)).OnlyEnforceIf(hb)
        m.AddLinearExpressionInDomain(val[t], cp_model.Domain.FromIntervals([[1, 4], [9, 9]])).OnlyEnforceIf(hb.Not())
        hh = m.NewBoolVar(""); m.AddBoolAnd([oc[t], hb]).OnlyEnforceIf(hh); m.AddBoolOr([oc[t].Not(), hb.Not()]).OnlyEnforceIf(hh.Not()); highs.append(hh)
        e1 = m.NewBoolVar(""); m.Add(val[t] == 1).OnlyEnforceIf(e1); m.Add(val[t] != 1).OnlyEnforceIf(e1.Not())
        h1 = m.NewBoolVar(""); m.AddBoolAnd([oc[t], e1]).OnlyEnforceIf(h1)
        m.AddBoolOr([oc[t].Not(), e1.Not()]).OnlyEnforceIf(h1.Not()); ones.append(h1)
    m.Add(sum(ones) == (0 if NOUT == 10 else 1))
    m.Add(sum(highs) == 10)
    fix_common(h)
    # swap twin: at most one of 7,8,9 absent from every circle
    used = {}
    for w in (7, 8, 9):
        hs = []
        for t in allpos:
            e = m.NewBoolVar(""); m.Add(val[t] == w).OnlyEnforceIf(e); m.AddImplication(e, oc[t]); hs.append(e)
        for p in cells:
            e = m.NewBoolVar(""); m.AddImplication(e, gc[p]); m.AddImplication(e, y[p, w]); hs.append(e)
        u = m.NewBoolVar(""); m.AddBoolOr(hs).OnlyEnforceIf(u); m.Add(sum(hs) == 0).OnlyEnforceIf(u.Not()); used[w] = u
    m.Add(sum(used.values()) >= 2)
    return h


def solver(t):
    s = cp_model.CpSolver(); s.parameters.num_workers = 4; s.parameters.max_time_in_seconds = t; return s


def read(s, h):
    D = {p: s.Value(h["iv"][p]) for p in cells}
    G = {p: s.Value(h["reg"][p]) for p in cells}
    return D, G


h = master(); m, oc, gc, iv, x = h["m"], h["oc"], h["gc"], h["iv"], h["x"]
lay = {t: oc[t] for t in allpos} | {gname(p): gc[p] for p in cells}


def cut(D2, G2):
    alts = [oc[t] for t in allpos if M.nrval(D2, G2, t) is None]
    val2 = {t: M.nrval(D2, G2, t) for t in allpos} | {gname(p): D2[p] for p in cells}
    for w in range(1, 10):
        cnt = sum(lay[t] for t in lay if val2[t] == w)
        if isinstance(cnt, int):
            continue
        bad = m.NewBoolVar("")
        m.Add(cnt >= 1).OnlyEnforceIf(bad); m.Add(cnt != w).OnlyEnforceIf(bad); alts.append(bad)
    eq = m.NewBoolVar("")
    for p in cells:
        m.Add(iv[p] == D2[p]).OnlyEnforceIf(eq); m.AddImplication(eq, x[p, G2[p]])
    m.AddBoolOr(alts + [eq])


def key(D, G):
    return ("".join(str(D[p]) for p in cells), "".join(str(G[p]) for p in cells))


seen = set()
if os.path.exists(ALTS):
    for ln in open(ALTS):
        d, g = json.loads(ln)
        if (d, g) in seen: continue
        seen.add((d, g)); cut({p: int(d[i]) for i, p in enumerate(cells)}, {p: int(g[i]) for i, p in enumerate(cells)})
for bf in filter(None, os.environ.get("BANS", "").split(":")):
    for ln in open(bf):
        if "  circles " in ln:
            Lb = set(ln.split("  circles ", 1)[1].split())
            m.AddBoolOr([lay[t].Not() if t in Lb else lay[t] for t in lay])
            print("banned found layout", flush=True)
        if "  regions " in ln and os.environ.get("BANREG"):
            rg = "".join(ln.split("  regions ", 1)[1].split())
            m.AddBoolOr([x[p, "ABCD".index(rg[i])].Not() for i, p in enumerate(cells)])
        if "  digits " in ln and os.environ.get("BANGRID"):
            dg = "".join(ln.split("  digits ", 1)[1].split())
            bs = []
            for i, p in enumerate(cells):
                b = m.NewBoolVar(""); m.Add(iv[p] != int(dg[i])).OnlyEnforceIf(b); bs.append(b)
            m.AddBoolOr(bs)
print("loaded cuts", len(seen), flush=True)
t0 = time.time(); it = 0; found = 0
CAP = float(sys.argv[1]) if len(sys.argv) > 1 else 1800
while time.time() - t0 < CAP:
    it += 1
    s = solver(300); st = s.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("master", s.StatusName(st), f"{time.time()-t0:.0f}s", flush=True); break
    L = [t for t, c in lay.items() if s.Value(c)]; D, G = read(s, h)
    h2 = M.build(); m2 = h2["m"]
    for t in allpos:
        m2.Add(h2["oc"][t] == (1 if t in L else 0))
    for p in cells:
        m2.Add(h2["gc"][p] == (1 if gname(p) in L else 0))
    def excl(Dx, Gx):
        bs = []
        for p in cells:
            b = m2.NewBoolVar(""); m2.Add(h2["iv"][p] != Dx[p]).OnlyEnforceIf(b); bs.append(b)
        m2.AddBoolOr(bs + [h2["x"][p, Gx[p]].Not() for p in cells])
    excl(D, G)
    s2 = solver(300); st2 = s2.Solve(m2)
    print(f"it {it} circles {len(L)} second {s2.StatusName(st2)} {time.time()-t0:.0f}s", flush=True)
    if st2 == cp_model.INFEASIBLE:
        found += 1
        print(f"FOUND {found}")
        print("  regions", " ".join("".join("ABCD"[G[(r, c)]] for c in range(6)) for r in range(6)))
        print("  digits ", " ".join("".join(str(D[(r, c)]) for c in range(6)) for r in range(6)))
        print("  outside", " ".join(f"{t}={s.Value(h['val'][t])}" for t in allpos if t in L))
        print("  circles", " ".join(L), flush=True)
        m.AddBoolOr([lay[t].Not() if t in L else lay[t] for t in lay])
        if os.environ.get("BANREG"):
            m.AddBoolOr([x[p, G[p]].Not() for p in cells])
        if os.environ.get("BANGRID"):
            gb = []
            for p in cells:
                b = m.NewBoolVar(""); m.Add(iv[p] != D[p]).OnlyEnforceIf(b); gb.append(b)
            m.AddBoolOr(gb)
        if found >= int(os.environ.get("MAXFOUND", 3)): break
        continue
    if st2 not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("check timeout"); break
    new = [(D, G)]
    while len(new) < 21:
        D2, G2 = read(s2, h2); new.append((D2, G2)); excl(D2, G2)
        s2 = solver(60); st2 = s2.Solve(m2)
        if st2 not in (cp_model.OPTIMAL, cp_model.FEASIBLE): break
    added = 0
    with open(ALTS, "a") as fh:
        for D2, G2 in new:
            k = key(D2, G2)
            if k in seen: continue
            seen.add(k); cut(D2, G2); added += 1; fh.write(json.dumps(list(k)) + "\n")
    print(f"  cuts +{added} (total {len(seen)})", flush=True)
else:
    print("time cap", flush=True)

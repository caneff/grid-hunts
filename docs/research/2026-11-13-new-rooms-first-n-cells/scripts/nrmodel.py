"""SCRATCH: new-rule model (cells 1..N in first cell's region, N+1 out; clue = cell N)."""
from ortools.sat.python import cp_model
N, K, S = 6, 4, 9
cells = [(r, c) for r in range(N) for c in range(N)]
lines = {f"r{i+1}": [(i, c) for c in range(N)] for i in range(N)}
lines |= {f"c{i+1}": [(r, i) for r in range(N)] for i in range(N)}
allpos = [f"r{i}{s}" for i in range(1, 7) for s in "LR"] + [f"c{i}{s}" for i in range(1, 7) for s in "TB"]
def seq(t):
    ln = lines[t[:-1]]
    return ln[::-1] if t[-1] in "RB" else ln
def nrval(D, G, t):
    ln = seq(t); f = D[ln[0]]
    if f > N: return None
    rg = [G[q] for q in ln]
    if all(z == rg[0] for z in rg[:f]) and (f == N or rg[f] != rg[0]): return D[ln[f - 1]]
    return None
def build():
    m = cp_model.CpModel()
    def nbrs(r, c):
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if 0 <= r + dr < N and 0 <= c + dc < N:
                yield r + dr, c + dc


    m = cp_model.CpModel()
    x = {(p, k): m.NewBoolVar("") for p in cells for k in range(K)}
    root = {(p, k): m.NewBoolVar("") for p in cells for k in range(K)}
    dep = {p: m.NewIntVar(0, S - 1, "") for p in cells}
    for p in cells:
        m.AddExactlyOne(x[p, k] for k in range(K))
    for k in range(K):
        m.Add(sum(x[p, k] for p in cells) == S)
        m.AddExactlyOne(root[p, k] for p in cells)
        for i, p in enumerate(cells):
            m.AddImplication(root[p, k], x[p, k])
            for q in cells[:i]:
                m.AddImplication(root[p, k], x[q, k].Not())
    ridx = []
    for k in range(K):
        v = m.NewIntVar(0, 35, "")
        m.Add(v == sum(i * root[p, k] for i, p in enumerate(cells)))
        ridx.append(v)
    for k in range(K - 1):
        m.Add(ridx[k] < ridx[k + 1])
    for p in cells:
        for k in range(K):
            opts = []
            for q in nbrs(*p):
                b = m.NewBoolVar("")
                m.AddImplication(b, x[q, k])
                m.Add(dep[q] < dep[p]).OnlyEnforceIf(b)
                opts.append(b)
            m.AddBoolOr(opts + [root[p, k], x[p, k].Not()])
    y = {(p, n): m.NewBoolVar("") for p in cells for n in range(1, 10)}
    iv = {}
    for p in cells:
        m.AddExactlyOne(y[p, n] for n in range(1, 10))
        iv[p] = m.NewIntVar(1, 9, "")
        m.Add(iv[p] == sum(n * y[p, n] for n in range(1, 10)))
    lines = {f"r{i+1}": [(i, c) for c in range(N)] for i in range(N)}
    lines |= {f"c{i+1}": [(r, i) for r in range(N)] for i in range(N)}
    for ln in lines.values():
        for n in range(1, 10):
            m.AddAtMostOne(y[p, n] for p in ln)
    for k in range(K):
        for n in range(1, 10):
            zs = []
            for p in cells:
                z = m.NewBoolVar("")
                m.AddImplication(z, x[p, k])
                m.AddImplication(z, y[p, n])
                m.AddBoolOr([x[p, k].Not(), y[p, n].Not(), z])
                zs.append(z)
            m.Add(sum(zs) == 1)
    reg = {p: m.NewIntVar(0, K - 1, "") for p in cells}
    for p in cells:
        m.Add(reg[p] == sum(k * x[p, k] for k in range(K)))


    def seq(t):
        ln = lines[t[:-1]]
        return ln[::-1] if t[-1] in "RB" else ln


    allpos = [f"r{i}{s}" for i in range(1, 7) for s in "LR"] + [f"c{i}{s}" for i in range(1, 7) for s in "TB"]
    ok, val = {}, {}
    for t in allpos:
        ln = seq(t)
        same = [None]
        for j in range(1, N):
            b = m.NewBoolVar("")
            m.Add(reg[ln[j]] == reg[ln[0]]).OnlyEnforceIf(b)
            m.Add(reg[ln[j]] != reg[ln[0]]).OnlyEnforceIf(b.Not())
            same.append(b)
        o = m.NewBoolVar("")
        oks = []
        vv = m.NewIntVar(1, 9, "")
        for n in range(1, N + 1):
            lits = [y[ln[0], n]] + same[1:n] + ([same[n].Not()] if n < N else [])
            on = m.NewBoolVar("")
            m.AddBoolAnd(lits).OnlyEnforceIf(on)
            m.AddBoolOr([l.Not() for l in lits]).OnlyEnforceIf(on.Not())
            oks.append(on)
            m.Add(vv == iv[ln[n - 1]]).OnlyEnforceIf(on)
        m.AddMaxEquality(o, oks)
        ok[t], val[t] = o, vv

    oc = {t: m.NewBoolVar("") for t in allpos}  # outside circled
    for t in allpos:
        m.AddImplication(oc[t], ok[t])
    gc = {p: m.NewBoolVar("") for p in cells}  # grid circled
    for w in range(1, 10):
        hits = []
        for t in allpos:
            e = m.NewBoolVar("")
            m.Add(val[t] == w).OnlyEnforceIf(e)
            m.Add(val[t] != w).OnlyEnforceIf(e.Not())
            h = m.NewBoolVar("")
            m.AddBoolAnd([oc[t], e]).OnlyEnforceIf(h)
            m.AddBoolOr([oc[t].Not(), e.Not()]).OnlyEnforceIf(h.Not())
            hits.append(h)
        for p in cells:
            h = m.NewBoolVar("")
            m.AddBoolAnd([gc[p], y[p, w]]).OnlyEnforceIf(h)
            m.AddBoolOr([gc[p].Not(), y[p, w].Not()]).OnlyEnforceIf(h.Not())
            hits.append(h)
        nw = m.NewBoolVar("")
        m.Add(sum(hits) == w).OnlyEnforceIf(nw)
        m.Add(sum(hits) == 0).OnlyEnforceIf(nw.Not())

    return dict(m=m, x=x, y=y, iv=iv, reg=reg, oc=oc, gc=gc, ok=ok, val=val)

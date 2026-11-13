"""SCRATCH: new Chaos Rooms rule. N = first digit; cells 1..N in first cell's region,
cell N+1 (if any) in another; clue = digit in cell N. Counting circles inside+outside.

newrule.py --out c1T,c2T,c3T,r1L,r2L --noout r3L --fullside B --firstcirc 5
          [--nout 12] [--total 36] [--forbid "r6c3=1"] [--time 120]
"""
import argparse
from ortools.sat.python import cp_model

N, K, S = 6, 4, 9
cells = [(r, c) for r in range(N) for c in range(N)]
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="")
ap.add_argument("--noout", default="")
ap.add_argument("--fullside", default="")
ap.add_argument("--firstcirc", type=int, default=-1)
ap.add_argument("--nout", type=int, default=12)
ap.add_argument("--total", type=int, default=0)
ap.add_argument("--extra", default="", help="constraint like 'lowfirst!=1'")
ap.add_argument("--gcirc", default="")
ap.add_argument("--time", type=float, default=120)
A = ap.parse_args()


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

for t in filter(None, A.out.split(",")):
    m.Add(oc[t] == 1)
for t in filter(None, A.noout.split(",")):
    m.Add(oc[t] == 0)
m.Add(sum(oc.values()) == A.nout)
side = A.fullside
firsts = []
if side:
    ts = [f"c{i}{side}" if side in "TB" else f"r{i}{side}" for i in range(1, 7)]
    for t in ts:
        m.Add(oc[t] == 1)
    firsts = [seq(t)[0] for t in ts]
    if A.firstcirc >= 0:
        m.Add(sum(gc[p] for p in firsts) == A.firstcirc)
for t in filter(None, A.gcirc.split(",")):
    r_, c_ = t[1:].split("c")
    m.Add(gc[(int(r_) - 1, int(c_) - 1)] == 1)
if A.total:
    m.Add(sum(oc.values()) + sum(gc.values()) == A.total)
if A.extra == "tenhigh":
    ones = []
    for t in allpos:
        m.AddLinearExpressionInDomain(val[t], cp_model.Domain.FromValues([1, 5, 6, 7, 8])).OnlyEnforceIf(oc[t])
        e1 = m.NewBoolVar("")
        m.Add(val[t] == 1).OnlyEnforceIf(e1)
        m.Add(val[t] != 1).OnlyEnforceIf(e1.Not())
        h1 = m.NewBoolVar("")
        m.AddBoolAnd([oc[t], e1]).OnlyEnforceIf(h1)
        m.AddBoolOr([oc[t].Not(), e1.Not()]).OnlyEnforceIf(h1.Not())
        ones.append(h1)
    m.Add(sum(ones) == 1)
if A.extra == "uncfirst!=1":
    # the uncircled first cell of the full side is not 1
    for p in firsts:
        m.Add(y[p, 1] == 0).OnlyEnforceIf(gc[p].Not())

s = cp_model.CpSolver()
s.parameters.num_workers = 1
s.parameters.max_time_in_seconds = A.time
st = s.Solve(m)
print(s.StatusName(st), f"{s.WallTime():.1f}s")
if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    for r in range(N):
        rg = "".join("ABCD"[s.Value(reg[(r, c)])] for c in range(N))
        dg = "".join(str(s.Value(iv[(r, c)])) for c in range(N))
        print(rg, dg)
    print("outside:", " ".join(f"{t}={s.Value(val[t])}" for t in allpos if s.Value(oc[t])))
    gcs = [f"r{p[0]+1}c{p[1]+1}" for p in cells if s.Value(gc[p])]
    print(f"grid circles ({len(gcs)}):", " ".join(gcs))

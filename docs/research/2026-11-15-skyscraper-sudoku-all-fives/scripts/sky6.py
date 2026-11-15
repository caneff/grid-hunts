"""SCRATCH: 9x9 Skyscraper Sudoku, clues are only 6s: every 5 in the grid given,
outside clues all equal 6. Maximise outside 5-clues subject to a unique solution.
Cut loop: master picks a grid + clued lines (clued => visibility 6); checker
looks for a second grid; the second grid becomes a cut.

sky5.py <min_out> [cap_seconds]
"""
import sys, time
from ortools.sat.python import cp_model
from sudoku_kit import cpsat

N = 9
cells = [(r, c) for r in range(N) for c in range(N)]
LINES = {}
for i in range(N):
    row = [(i, c) for c in range(N)]
    col = [(r, i) for r in range(N)]
    LINES[f"r{i+1}L"], LINES[f"r{i+1}R"] = row, row[::-1]
    LINES[f"c{i+1}T"], LINES[f"c{i+1}B"] = col, col[::-1]
NAMES = list(LINES)


def vis_expr(m, x, seq, tag):
    pm = x[seq[0]]
    bs = [1]
    for i in range(1, N):
        b = m.NewBoolVar(f"b{tag}{i}")
        m.Add(x[seq[i]] > pm).OnlyEnforceIf(b)
        m.Add(x[seq[i]] <= pm).OnlyEnforceIf(b.Not())
        nm = m.NewIntVar(1, N, f"p{tag}{i}")
        m.AddMaxEquality(nm, [pm, x[seq[i]]])
        pm = nm
        bs.append(b)
    return sum(bs)


def model():
    m, x = cpsat.sudoku_model(N, cpsat.boxes(N, 3, 3))
    return m, x


def sky(v):
    cnt = mx = 0
    for d in v:
        if d > mx:
            cnt, mx = cnt + 1, d
    return cnt


def solver(t, w=4):
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = t
    s.parameters.num_workers = w
    return s


MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 20
CAP = float(sys.argv[2]) if len(sys.argv) > 2 else 3000

m, x = model()
oc = {t: m.NewBoolVar(t) for t in NAMES}
for t in NAMES:
    m.Add(vis_expr(m, x, LINES[t], t) == 6).OnlyEnforceIf(oc[t])
five = {p: m.NewBoolVar("") for p in cells}
for p in cells:
    m.Add(x[p] == 6).OnlyEnforceIf(five[p])
    m.Add(x[p] != 6).OnlyEnforceIf(five[p].Not())
tot = sum(oc.values())
m.Add(tot >= MIN)
m.Maximize(tot)

t0 = time.time()
it = 0
while time.time() - t0 < CAP:
    it += 1
    s = solver(600)
    st = s.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(f"master {s.StatusName(st)} at >= {MIN} outside, {time.time()-t0:.0f}s", flush=True)
        break
    G = {p: s.Value(x[p]) for p in cells}
    L = [t for t in NAMES if s.Value(oc[t])]
    m2, x2 = model()
    for p in cells:
        if G[p] == 6:
            m2.Add(x2[p] == 6)
    for t in L:
        m2.Add(vis_expr(m2, x2, LINES[t], "q" + t) == 6)
    bs = []
    for p in cells:
        b = m2.NewBoolVar("")
        m2.Add(x2[p] != G[p]).OnlyEnforceIf(b)
        bs.append(b)
    m2.AddBoolOr(bs)
    s2 = solver(600)
    st2 = s2.Solve(m2)
    print(f"it {it} outside {len(L)} ({s.StatusName(st)}) second {s2.StatusName(st2)} {time.time()-t0:.0f}s", flush=True)
    if st2 == cp_model.INFEASIBLE:
        print("FOUND", len(L) + 9, "clues:", len(L), "outside + 9 inside")
        print("  grid   ", " ".join("".join(str(G[(r, c)]) for c in range(N)) for r in range(N)))
        print("  outside", " ".join(L), flush=True)
        break
    if st2 not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("check timeout", flush=True)
        break
    # cut every rival found, up to 20 per pass: each must be ruled out --
    # master clues some line the rival does not show as 6, or puts a 6 where
    # the rival has none, or is the rival itself
    rivals = []
    while len(rivals) < 20:
        G2 = {p: s2.Value(x2[p]) for p in cells}
        rivals.append(G2)
        bs2 = []
        for p in cells:
            b = m2.NewBoolVar(""); m2.Add(x2[p] != G2[p]).OnlyEnforceIf(b); bs2.append(b)
        m2.AddBoolOr(bs2)
        s2 = solver(60); st2 = s2.Solve(m2)
        if st2 not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
    for G2 in rivals:
        alts = [oc[t] for t in NAMES if sky([G2[p] for p in LINES[t]]) != 6]
        alts += [five[p] for p in cells if G2[p] != 6]
        eq = m.NewBoolVar("")
        for p in cells:
            m.Add(x[p] == G2[p]).OnlyEnforceIf(eq)
        m.AddBoolOr(alts + [eq])
    print(f"  cut {len(rivals)} rivals", flush=True)
else:
    print("time cap", flush=True)

"""SCRATCH: 9x9 Skyscraper Sudoku, clues are only 5s: every 5 in the grid given,
outside clues all equal 5. Maximise outside 5-clues subject to a unique solution.
Cut loop: master picks a grid + clued lines (clued => visibility 5); checker
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



def second(G, lay):
    m2, x2 = model()
    for p in cells:
        if G[p] == 5: m2.Add(x2[p] == 5)
    for t in lay: m2.Add(vis_expr(m2, x2, LINES[t], "q" + t) == 5)
    bs = []
    for p in cells:
        b = m2.NewBoolVar(""); m2.Add(x2[p] != G[p]).OnlyEnforceIf(b); bs.append(b)
    m2.AddBoolOr(bs)
    s2 = solver(600); st2 = s2.Solve(m2)
    if st2 == cp_model.INFEASIBLE: return "INFEASIBLE", None
    if st2 in (cp_model.OPTIMAL, cp_model.FEASIBLE): return "FEASIBLE", {p: s2.Value(x2[p]) for p in cells}
    return "UNKNOWN", None

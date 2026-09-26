"""Pair sweep: 33 at r5c1, QR 10 at the r6c6 window, QQRR 5 in a corner, r4c1 <= 7,
no bands, no entered digits. One small solve per interior seeing pair, that pair's
7-digit tie forced, 1 CP-SAT worker each, a pool of processes per corner.
Usage: pair_sweep.py <corner> <procs> <per-pair timeout> <log> [<hunt> [<workers> [retry]]]
<hunt> is r5c1 (default: cage r5c1, r4c1 <= 7) or r1c5 (cage r1c5, r1c4 <= 7).
<workers> is CP-SAT workers per pair (default 1). `retry` re-runs only the pairs whose
last logged result is a timeout; otherwise pairs already logged are skipped."""

import sys
import time
from multiprocessing import Pool

import hunt_common
from hunt_common import HUNTS

# isort: split
import checker
import model
import oracle
from ortools.sat.python import cp_model

from examples._shared import cpsat

corner, procs, timeout, logp = (
    sys.argv[1],
    int(sys.argv[2]),
    float(sys.argv[3]),
    sys.argv[4],
)
hunt = sys.argv[5] if len(sys.argv) > 5 else "r5c1"
workers = int(sys.argv[6]) if len(sys.argv) > 6 else 1
retry = len(sys.argv) > 7 and sys.argv[7] == "retry"
n = 9
TEN = (5, 5)
CAGE, TARGET, SEED = HUNTS[hunt]
PIN = checker.CORNERS[corner]
SEEDS = [SEED]


def build(pair):
    q = model.build(n, ranked_cells=[CAGE, PIN])
    m = q.m
    pairs = model.add_seeing_tie(q)
    m.Add(pairs[pair] == 1)
    m.AddLinearConstraint(q.rank[TEN[0]][TEN[1]], 10, 10)
    m.AddAllowedAssignments(
        [q.x[TEN[0]][TEN[1]]], [(d,) for d in model.leading_digits(n, 10, 10)]
    )
    m.Add(q.q[CAGE] == 33)
    m.Add(q.q[PIN] == 5)
    m.Add(q.x[TARGET[0]][TARGET[1]] <= 7)
    for row_i, row in enumerate(SEEDS[0].split("/")):
        for c, d in enumerate(row):
            m.AddHint(q.x[row_i][c], int(d))
    return q


def solve_pair(pair):
    t0 = time.monotonic()
    q = build(pair)
    s = cpsat.solver(timeout, reproducible=False)
    s.parameters.num_workers = workers
    res = s.Solve(q.m)
    dt = time.monotonic() - t0
    a, b = pair
    tag = f"r{a[0] + 1}c{a[1] + 1}=r{b[0] + 1}c{b[1] + 1}"
    if res == cp_model.INFEASIBLE:
        return f"pair {tag} infeasible {dt:.1f}s"
    if res == cpsat.UNKNOWN:
        return f"pair {tag} timeout {dt:.1f}s"
    if res not in cpsat.SOLVED:
        return f"pair {tag} Error {s.StatusName(res)}"
    grid = [[s.Value(q.x[r][c]) for c in range(n)] for r in range(n)]
    ranks, _nums, cr = oracle.rank_grid(grid)
    assert ranks == [[s.Value(v) for v in row] for row in q.rank]
    lines = [f"HIT pair {tag} {dt:.1f}s"]
    for ta, tb, num, la, lb in oracle.seven_digit_ties(ranks):
        lines.append(hunt_common.tie_line(ta, tb, num, la, lb, cr[ta[0]][ta[1]]))
    lines.append(
        f"  QQRR cage {cr[CAGE[0]][CAGE[1]]} corner {cr[PIN[0]][PIN[1]]} QR r6c6 {ranks[TEN[0]][TEN[1]]} bounded cell {grid[TARGET[0]][TARGET[1]]}"
    )
    lines.append(hunt_common.grid_line(grid))
    return "\n".join(lines)


if __name__ == "__main__":
    interior = [(r, c) for r in range(1, n - 1) for c in range(1, n - 1)]
    pairs = [
        (a, b)
        for i, a in enumerate(interior)
        for b in interior[i + 1 :]
        if model.sees(n, a, b)
    ]
    # Pairs nearest the cage first: it pulls on its neighbours and every tie so far sat beside it.
    dist = lambda c: abs(c[0] - CAGE[0]) + abs(c[1] - CAGE[1])
    pairs.sort(key=lambda p: (min(dist(p[0]), dist(p[1])), p))
    import os
    import re

    last = {}  # pair -> last logged status
    if os.path.exists(logp):
        for line in open(logp):
            m = re.match(r"(HIT )?pair r(\d)c(\d)=r(\d)c(\d) (\w+)", line)
            if m:
                last[
                    ((int(m[2]) - 1, int(m[3]) - 1), (int(m[4]) - 1, int(m[5]) - 1))
                ] = "HIT" if m[1] else m[6]
    if retry:
        pairs = [p for p in pairs if last.get(p) == "timeout"]
        skipped = len(last) - len(pairs)
    else:
        skipped = len([p for p in pairs if p in last])
        pairs = [p for p in pairs if p not in last]
    log = open(logp, "a")

    def out(s):
        print(s, file=log, flush=True)

    out(
        f"sweep{' retry' if retry else ''}: hunt={hunt} cage=r{CAGE[0] + 1}c{CAGE[1] + 1} bound=r{TARGET[0] + 1}c{TARGET[1] + 1}<=7 corner={corner} procs={procs} workers={workers} per-pair timeout={timeout:.0f}s pairs={len(pairs)} (skipped {skipped} already logged)"
    )
    start = time.monotonic()
    counts = {"infeasible": 0, "timeout": 0, "HIT": 0}
    with Pool(procs) as pool:
        for line in pool.imap_unordered(solve_pair, pairs):
            out(line)
            for k in counts:
                if k in line.split()[:3]:
                    counts[k] += 1
    out(f"done: corner={corner} {time.monotonic() - start:.0f}s {counts}")

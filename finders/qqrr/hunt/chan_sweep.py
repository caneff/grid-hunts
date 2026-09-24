"""Channelled pair sweep. Same hunts as pair_sweep.py (QR 10 at r6c6, QQRR 33 at the cage,
QQRR 5 in a corner, bounded cell <= 7, no bands, no digits) but the 7-digit tie is posted
digit by digit: each window rank r gets tens/units vars (r = 10 t + u, t >= 1 iff wide), the
pair's slot pattern (which window of A and of B is one digit wide, different slots) is fixed
per task, and the two 7-digit sequences are equated element-wise. 12 patterns per pair.
Usage: chan_sweep.py <corner> <procs> <per-task timeout> <log> <hunt> [<workers>] [pairs=r7c2=r7c5,...] [from=<pair_sweep log>]
Resumes from the log: a (pair, pattern) already logged is skipped."""

import os
import re
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import checker
import model
import oracle
from ortools.sat.python import cp_model

from examples._shared import cpsat

corner, procs, timeout, logp, hunt = (
    sys.argv[1],
    int(sys.argv[2]),
    float(sys.argv[3]),
    sys.argv[4],
    sys.argv[5],
)
workers = int(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6].isdigit() else 1
only = None
FLAGS = {a for a in sys.argv[6:] if a in ("nohint", "tables", "lin2")}
TEN = (5, 5)
for a in sys.argv[6:]:
    if a.startswith("ten="):
        m_ = re.match(r"ten=r(\d)c(\d)", a)
        TEN = (int(m_[1]) - 1, int(m_[2]) - 1)
for a in sys.argv[6:]:
    if a.startswith("from="):
        # the pairs whose last result in a pair_sweep.py log is a timeout
        last = {}
        for line in open(a[5:]):
            m_ = re.match(r"(HIT )?pair r(\d)c(\d)=r(\d)c(\d) (\w+)", line)
            if m_:
                last[
                    ((int(m_[2]) - 1, int(m_[3]) - 1), (int(m_[4]) - 1, int(m_[5]) - 1))
                ] = "HIT" if m_[1] else m_[6]
        only = {p for p, st in last.items() if st == "timeout"}
    if a.startswith("pairs="):
        only = set()
        for t in a[6:].split(","):
            m_ = re.match(r"r(\d)c(\d)=r(\d)c(\d)", t)
            only.add(
                ((int(m_[1]) - 1, int(m_[2]) - 1), (int(m_[3]) - 1, int(m_[4]) - 1))
            )
n = 9
HUNTS = {
    "r5c1": (
        (4, 0),
        (3, 0),
        "591247638/672183954/438695127/865934271/927516483/143872569/284369715/716458392/359721846",
    ),
    "r1c5": (
        (0, 4),
        (0, 3),
        "356791428/974286531/128534967/215948673/483617295/697352814/562873149/749165382/831429756",
    ),
}
CAGE, TARGET, SEED = HUNTS[hunt]
PIN = checker.CORNERS[corner]


def build(pair, ia, ib):
    q = model.build(n, ranked_cells=[CAGE, PIN])
    m = q.m
    m.AddLinearConstraint(q.rank[TEN[0]][TEN[1]], 10, 10)
    m.AddAllowedAssignments(
        [q.x[TEN[0]][TEN[1]]], [(d,) for d in model.leading_digits(n, 10, 10)]
    )
    m.Add(q.q[CAGE] == 33)
    m.Add(q.q[PIN] == 5)
    m.Add(q.x[TARGET[0]][TARGET[1]] <= 7)
    if "nohint" not in FLAGS:
        for row_i, row in enumerate(SEED.split("/")):
            for c, d in enumerate(row):
                m.AddHint(q.x[row_i][c], int(d))
    # tens/units per window, channelled to the rank and its width literal
    tens, units = {}, {}

    def digits(wr, wc):
        if (wr, wc) not in tens:
            t = m.NewIntVar(0, 6, f"t{wr}{wc}")
            u = m.NewIntVar(0, 9, f"u{wr}{wc}")
            m.Add(q.rank[wr][wc] == 10 * t + u)
            w = q.wide[wr][wc]
            m.Add(t >= 1).OnlyEnforceIf(w)
            m.Add(t == 0).OnlyEnforceIf(w.Not())
            if "tables" in FLAGS:
                # the tens digit follows the top-left digit through the leading-digit band
                allowed = []
                for d in range(1, n + 1):
                    lo, hi = model.leading_digit_band(n, d)
                    allowed += [(d, tt) for tt in range(lo // 10, hi // 10 + 1)]
                m.AddAllowedAssignments([q.x[wr][wc], t], allowed)
            tens[(wr, wc)], units[(wr, wc)] = t, u
        return tens[(wr, wc)], units[(wr, wc)]

    def seq(cell, narrow):
        out = []
        for k, (wr, wc) in enumerate(model.windows_of(n, *cell)):
            t, u = digits(wr, wc)
            if k == narrow:
                m.Add(q.wide[wr][wc] == 0)
                out.append(u)
            else:
                m.Add(q.wide[wr][wc] == 1)
                out.append(t)
                out.append(u)
        return out

    a, b = pair
    sa, sb = seq(a, ia), seq(b, ib)
    assert len(sa) == len(sb) == 7
    for da, db in zip(sa, sb):
        m.Add(da == db)
    m.Add(
        q.num[a[0]][a[1]] == q.num[b[0]][b[1]]
    )  # redundant, keeps the big-number view consistent
    return q


def solve(task):
    pair, ia, ib = task
    t0 = time.monotonic()
    q = build(pair, ia, ib)
    s = cpsat.solver(timeout, reproducible=False)
    s.parameters.num_workers = workers
    if "lin2" in FLAGS:
        s.parameters.linearization_level = 2
    res = s.Solve(q.m)
    dt = time.monotonic() - t0
    a, b = pair
    tag = f"r{a[0] + 1}c{a[1] + 1}=r{b[0] + 1}c{b[1] + 1} slots {ia}{ib}"
    if res == cp_model.INFEASIBLE:
        return f"pair {tag} infeasible {dt:.1f}s"
    if res == cpsat.UNKNOWN:
        return f"pair {tag} timeout {dt:.1f}s"
    if res not in cpsat.SOLVED:
        return f"pair {tag} Error {s.StatusName(res)}"
    grid = [[s.Value(q.x[r][c]) for c in range(n)] for r in range(n)]
    ranks, nums, cr = oracle.rank_grid(grid)
    assert ranks == [[s.Value(v) for v in row] for row in q.rank]
    ties = oracle.seven_digit_ties(ranks)
    assert any({ta, tb} == {a, b} for ta, tb, *_ in ties), (
        "solver tie not confirmed by the oracle"
    )
    lines = [f"HIT pair {tag} {dt:.1f}s"]
    for ta, tb, num, la, lb in ties:
        lines.append(
            f"  tie r{ta[0] + 1}c{ta[1] + 1} {'|'.join(map(str, la))} = r{tb[0] + 1}c{tb[1] + 1} {'|'.join(map(str, lb))}, number {num}, QQRR {cr[ta[0]][ta[1]]}"
        )
    lines.append(
        f"  QQRR cage {cr[CAGE[0]][CAGE[1]]} corner {cr[PIN[0]][PIN[1]]} QR r6c6 {ranks[TEN[0]][TEN[1]]} bounded cell {grid[TARGET[0]][TARGET[1]]}"
    )
    lines.append("  grid " + "/".join("".join(map(str, r)) for r in grid))
    return "\n".join(lines)


if __name__ == "__main__":
    interior = [(r, c) for r in range(1, n - 1) for c in range(1, n - 1)]
    pairs = [
        (a, b)
        for i, a in enumerate(interior)
        for b in interior[i + 1 :]
        if model.sees(n, a, b)
    ]
    if only is not None:
        pairs = [p for p in pairs if p in only]
    dist = lambda c: abs(c[0] - CAGE[0]) + abs(c[1] - CAGE[1])
    pairs.sort(key=lambda p: (min(dist(p[0]), dist(p[1])), p))
    tasks = [
        (p, ia, ib) for p in pairs for ia in range(4) for ib in range(4) if ia != ib
    ]
    done = set()
    if os.path.exists(logp):
        for line in open(logp):
            m_ = re.match(r"(?:HIT )?pair r(\d)c(\d)=r(\d)c(\d) slots (\d)(\d) ", line)
            if m_:
                done.add(
                    (
                        (
                            (int(m_[1]) - 1, int(m_[2]) - 1),
                            (int(m_[3]) - 1, int(m_[4]) - 1),
                        ),
                        int(m_[5]),
                        int(m_[6]),
                    )
                )
    skipped = len([t for t in tasks if t in done])
    tasks = [t for t in tasks if t not in done]
    log = open(logp, "a")

    def out(s):
        print(s, file=log, flush=True)

    out(
        f"chan sweep: hunt={hunt} cage=r{CAGE[0] + 1}c{CAGE[1] + 1} bound=r{TARGET[0] + 1}c{TARGET[1] + 1}<=7 corner={corner} procs={procs} workers={workers} per-task timeout={timeout:.0f}s tasks={len(tasks)} pairs={len(pairs)} (skipped {skipped} already logged)"
    )
    start = time.monotonic()
    counts = {"infeasible": 0, "timeout": 0, "HIT": 0}
    with Pool(procs) as pool:
        for line in pool.imap_unordered(solve, tasks):
            out(line)
            for k in counts:
                if k in line.split()[:6]:
                    counts[k] += 1
    out(f"done: corner={corner} {time.monotonic() - start:.0f}s {counts}")

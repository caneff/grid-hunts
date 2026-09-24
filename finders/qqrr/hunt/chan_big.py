"""Big channelled finder: one solve per (hunt, QR-10 window, corner), the tie pair and the
slot pattern left as decisions. Digit channelling as in chan_sweep.py: per window tens/units,
per interior cell an `active` literal and a one-hot narrow-slot choice that fixes the four
width literals and defines a 7-digit sequence; a pair literal makes both cells active, the
sequences equal and the narrow slots different; at least one pair literal is true.
Usage: chan_big.py <hunt r5c1|r1c5> <ten rXcY (window top-left)> <corner> <workers> <timeout> <log> [count] [flags...]
flags: tables lin2 hint warm forbid-known criteria=<name,...>. `forbid-known` posts a nogood on every grid already in big-*.log. Writes every grid found (up to count, default 2) and the verdict.
`warm` hints every cell from the nearest earlier hit (same hunt; prefer same window and corner) read from big-*.log.
`criteria=` names entries of CRITERIA: each has an optional `model` (posts constraints) and an optional
`accept` (oracle-side filter on a found grid; a rejected grid is forbidden and the loop continues)."""

import glob
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import checker
import model
import oracle
from ortools.sat.python import cp_model

from examples._shared import cpsat

hunt, ten_s, corner, workers, timeout, logp = (
    sys.argv[1],
    sys.argv[2],
    sys.argv[3],
    int(sys.argv[4]),
    float(sys.argv[5]),
    sys.argv[6],
)
count = int(sys.argv[7]) if len(sys.argv) > 7 and sys.argv[7].isdigit() else 2
FLAGS = set(sys.argv[7:])
m_ = re.match(r"r(\d)c(\d)", ten_s)
TEN = (int(m_[1]) - 1, int(m_[2]) - 1)
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
LOGS = Path(
    os.environ.get(
        "HUNT_LOGS", Path(__file__).resolve().parents[3] / ".scratch" / "place"
    )
)
CAGE, TARGET, SEED = HUNTS[hunt]
PIN = checker.CORNERS[corner]
log = open(logp, "a")


def out(s):
    print(s, file=log, flush=True)


q = model.build(n, ranked_cells=[CAGE, PIN])
m = q.m
m.AddLinearConstraint(q.rank[TEN[0]][TEN[1]], 10, 10)
m.AddAllowedAssignments(
    [q.x[TEN[0]][TEN[1]]], [(d,) for d in model.leading_digits(n, 10, 10)]
)
m.Add(q.q[CAGE] == 33)
m.Add(q.q[PIN] == 5)
m.Add(q.x[TARGET[0]][TARGET[1]] <= 7)


def earlier_hits(h=None):
    """(ten, corner, grid) for every hit of hunt h (default: this one) in the finder logs, nearest first."""
    hits = []
    for p in glob.glob(str(LOGS / ("big-%s-*.log" % (h or hunt)))):
        _, _, t, c = p.rsplit("/", 1)[-1][:-4].split("-")[:4]
        for line in open(p):
            if line.startswith("  grid "):
                hits.append((t, c, line.split()[1]))
    return sorted(hits, key=lambda h: (h[0] != ten_s) + (h[1] != corner))


def q34_zone(r, c):
    """Top-left cells of every window sharing a cell with one of (r, c)'s four windows."""
    return [
        (wr, wc)
        for wr in range(r - 2, r + 2)
        for wc in range(c - 2, c + 2)
        if 0 <= wr <= n - 2 and 0 <= wc <= n - 2
    ]


Q34_CELLS = [(r, c) for r in range(1, n - 1) for c in range(1, n - 1)]


def q34_model(m, q):
    """Some interior cell has QQRR 34..36 and none of its four windows shares a cell with the QR-1 window."""
    top = (n - 1) ** 2
    bounds = [
        [model.number_bounds(len(model.windows_of(n, r, c)), top) for c in range(n)]
        for r in range(n)
    ]
    sel = []
    for r, c in Q34_CELLS:
        qq = q.q.get((r, c)) or model.add_cell_rank(
            m, q.num, bounds, (r, c), f"q{r}{c}"
        )
        q.q[(r, c)] = qq
        b = m.NewBoolVar(f"q34_{r}{c}")
        sel.append(b)
        m.AddLinearConstraint(qq, 34, 36).OnlyEnforceIf(b)
        for wr, wc in q34_zone(r, c):
            m.Add(q.rank[wr][wc] != 1).OnlyEnforceIf(b)
    m.AddBoolOr(sel)


def q34_accept(grid, ranks, nums, cr):
    ones = {
        (wr, wc) for wr in range(n - 1) for wc in range(n - 1) if ranks[wr][wc] == 1
    }
    return [
        (r, c)
        for r, c in Q34_CELLS
        if 34 <= cr[r][c] <= 36 and not ones & set(q34_zone(r, c))
    ]


CRITERIA = {"q34": {"model": q34_model, "accept": q34_accept}}
CRIT = [c for f in FLAGS if f.startswith("criteria=") for c in f[9:].split(",")]
for name in CRIT:
    if name not in CRITERIA:
        raise SystemExit(f"unknown criterion {name}; known: {sorted(CRITERIA)}")
    if "model" in CRITERIA[name]:
        CRITERIA[name]["model"](m, q)
warm_from = None
if "warm" in FLAGS:
    hits = earlier_hits()

    def passes(h):
        g = [[int(d) for d in row] for row in h[2].split("/")]
        rk, nm, cr = oracle.rank_grid(g)
        return all(
            CRITERIA[c]["accept"](g, rk, nm, cr)
            for c in CRIT
            if "accept" in CRITERIA[c]
        )

    hits.sort(
        key=lambda h: not passes(h)
    )  # stable: criterion-passing hits first, nearest first within each
    if hits:
        warm_from = hits[0]
if "hint" in FLAGS or warm_from:
    src = warm_from[2] if warm_from else SEED
    for row_i, row in enumerate(src.split("/")):
        for c, d in enumerate(row):
            m.AddHint(q.x[row_i][c], int(d))
known = 0
if "forbid-known" in FLAGS:
    _cells = {(r, c): q.x[r][c] for r in range(n) for c in range(n)}
    for g in sorted({h[2] for hh in HUNTS for h in earlier_hits(hh)}):
        known += 1
        cpsat.forbid(
            m,
            _cells,
            {(r, c): int(g.split("/")[r][c]) for r in range(n) for c in range(n)},
            tag=f"known{known}",
        )
tens, units = {}, {}
for wr in range(n - 1):
    for wc in range(n - 1):
        t = m.NewIntVar(0, 6, f"t{wr}{wc}")
        u = m.NewIntVar(0, 9, f"u{wr}{wc}")
        m.Add(q.rank[wr][wc] == 10 * t + u)
        w = q.wide[wr][wc]
        m.Add(t >= 1).OnlyEnforceIf(w)
        m.Add(t == 0).OnlyEnforceIf(w.Not())
        if "tables" in FLAGS:
            allowed = []
            for d in range(1, n + 1):
                lo, hi = model.leading_digit_band(n, d)
                allowed += [(d, tt) for tt in range(lo // 10, hi // 10 + 1)]
            m.AddAllowedAssignments([q.x[wr][wc], t], allowed)
        tens[(wr, wc)], units[(wr, wc)] = t, u
interior = [(r, c) for r in range(1, n - 1) for c in range(1, n - 1)]
act, nar, seq = {}, {}, {}
for cell in interior:
    wins = model.windows_of(n, *cell)
    a = m.NewBoolVar(f"act{cell[0]}{cell[1]}")
    act[cell] = a
    ns = [m.NewBoolVar(f"nar{cell[0]}{cell[1]}_{i}") for i in range(4)]
    nar[cell] = ns
    m.Add(sum(ns) == a)
    sq = [m.NewIntVar(0, 9, f"seq{cell[0]}{cell[1]}_{k}") for k in range(7)]
    seq[cell] = sq
    for i in range(4):
        digits = []
        for k, (wr, wc) in enumerate(wins):
            if k == i:
                m.AddImplication(ns[i], q.wide[wr][wc].Not())
                digits.append(units[(wr, wc)])
            else:
                m.AddImplication(ns[i], q.wide[wr][wc])
                digits += [tens[(wr, wc)], units[(wr, wc)]]
        for k in range(7):
            m.Add(sq[k] == digits[k]).OnlyEnforceIf(ns[i])
pairs = {}
for i, a in enumerate(interior):
    for b in interior[i + 1 :]:
        if not model.sees(n, a, b):
            continue
        p = m.NewBoolVar(f"tie{a[0]}{a[1]}_{b[0]}{b[1]}")
        pairs[(a, b)] = p
        m.AddImplication(p, act[a])
        m.AddImplication(p, act[b])
        for k in range(7):
            m.Add(seq[a][k] == seq[b][k]).OnlyEnforceIf(p)
        for i_ in range(4):
            m.AddBoolOr([nar[a][i_].Not(), nar[b][i_].Not(), p.Not()])
        m.Add(q.num[a[0]][a[1]] == q.num[b[0]][b[1]]).OnlyEnforceIf(p)
m.AddBoolOr(list(pairs.values()))

cells = {(r, c): q.x[r][c] for r in range(n) for c in range(n)}
out(
    f"big: hunt={hunt} cage=r{CAGE[0] + 1}c{CAGE[1] + 1} bound=r{TARGET[0] + 1}c{TARGET[1] + 1}<=7 ten=r{TEN[0] + 1}c{TEN[1] + 1} corner={corner} workers={workers} timeout={timeout:.0f}s flags={sorted(FLAGS)}"
)
if warm_from:
    out(f"  warm start from {warm_from[0]} {warm_from[1]} {warm_from[2]}")
if known:
    out(f"  {known} known grids forbidden")
start = time.monotonic()
deadline = start + timeout
found = 0
status = None
rejected = 0
while found < count:
    s = cpsat.solver(max(deadline - time.monotonic(), 0.0), reproducible=False)
    s.parameters.num_workers = workers
    if "lin2" in FLAGS:
        s.parameters.linearization_level = 2
    res = s.Solve(m)
    if res == cpsat.UNKNOWN:
        status = "timeout"
        break
    if res == cp_model.INFEASIBLE:
        status = "infeasible" if not found else ("unique" if found == 1 else "multiple")
        break
    if res not in cpsat.SOLVED:
        raise RuntimeError(s.StatusName(res))
    grid = [[s.Value(q.x[r][c]) for c in range(n)] for r in range(n)]
    ranks, nums, cr = oracle.rank_grid(grid)
    assert ranks == [[s.Value(v) for v in row] for row in q.rank]
    ties = oracle.seven_digit_ties(ranks)
    assert ties, "solver tie not confirmed by the oracle"
    witness, ok = {}, True
    for name in CRIT:
        acc = CRITERIA[name].get("accept")
        if acc is None:
            continue
        w = acc(grid, ranks, nums, cr)
        if not w:
            ok = False
            rejected += 1
            out(
                f"  rejected by {name}: " + "/".join("".join(map(str, r)) for r in grid)
            )
            cpsat.forbid(
                m, cells, {rc: grid[rc[0]][rc[1]] for rc in cells}, tag=f"rej{rejected}"
            )
            break
        witness[name] = w
    if not ok:
        continue
    found += 1
    for name, w in witness.items():
        out(f"  {name}: " + " ".join(f"r{r + 1}c{c + 1}={cr[r][c]}" for r, c in w))
    out(f"HIT {found} {time.monotonic() - start:.1f}s")
    for ta, tb, num, la, lb in ties:
        out(
            f"  tie r{ta[0] + 1}c{ta[1] + 1} {'|'.join(map(str, la))} = r{tb[0] + 1}c{tb[1] + 1} {'|'.join(map(str, lb))}, number {num}, QQRR {cr[ta[0]][ta[1]]}"
        )
    out(
        f"  QQRR cage {cr[CAGE[0]][CAGE[1]]} corner {cr[PIN[0]][PIN[1]]} QR r{TEN[0] + 1}c{TEN[1] + 1} {ranks[TEN[0]][TEN[1]]} bounded cell {grid[TARGET[0]][TARGET[1]]}"
    )
    out("  grid " + "/".join("".join(map(str, r)) for r in grid))
    cpsat.forbid(m, cells, {rc: grid[rc[0]][rc[1]] for rc in cells}, tag=str(found))
if status is None:
    status = "multiple"
out(
    f"{status}: hunt={hunt} ten=r{TEN[0] + 1}c{TEN[1] + 1} corner={corner} {time.monotonic() - start:.1f}s found={found} rejected={rejected}"
)

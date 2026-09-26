"""Usage: check_3436.py; logs from $HUNT_LOGS (default .scratch/place).
Which found grids already hold a cell of QQRR 34-36 none of whose windows is the QR-1 window."""

import glob

import hunt_common as hc

# isort: split
import oracle

seen = {}
for p in sorted(glob.glob(str(hc.LOGS / "big-*.log"))):
    for g in hc.logged_grids(p):
        seen.setdefault(g, p.split("/")[-1])
for g, src in seen.items():
    grid = [[int(d) for d in row] for row in g.split("/")]
    ranks, nums, cr = oracle.rank_grid(grid)
    ones = {
        (wr, wc)
        for wr in range(len(ranks))
        for wc in range(len(ranks))
        if ranks[wr][wc] == 1
    }
    clean = [f"r{r + 1}c{c + 1}" for r, c in hc.q34_accept(ranks, cr)]
    print(
        src,
        "QR1",
        sorted(f"r{a + 1}c{b + 1}" for a, b in ones),
        "clean:",
        clean,
        "grid",
        g,
    )

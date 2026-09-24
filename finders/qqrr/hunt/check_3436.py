"""Usage: check_3436.py; logs from $HUNT_LOGS (default .scratch/place).
Which found grids already hold a cell of QQRR 34-36 none of whose windows is the QR-1 window."""

import glob
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import oracle

LOGS = Path(
    os.environ.get(
        "HUNT_LOGS", Path(__file__).resolve().parents[3] / ".scratch" / "place"
    )
)
seen = {}
for p in sorted(glob.glob(str(LOGS / "big-*.log"))):
    for line in open(p):
        if line.startswith("  grid "):
            seen.setdefault(line.split()[1], p.split("/")[-1])
for g, src in seen.items():
    grid = [[int(d) for d in row] for row in g.split("/")]
    ranks, nums, cr = oracle.rank_grid(grid)
    ones = {(wr, wc) for wr in range(8) for wc in range(8) if ranks[wr][wc] == 1}
    zone = lambda r, c: [
        (wr, wc)
        for wr in range(r - 2, r + 2)
        for wc in range(c - 2, c + 2)
        if 0 <= wr <= 7 and 0 <= wc <= 7
    ]
    clean = [
        f"r{r + 1}c{c + 1}"
        for r in range(1, 8)
        for c in range(1, 8)
        if 34 <= cr[r][c] <= 36 and not ones & set(zone(r, c))
    ]
    print(
        src,
        "QR1",
        sorted(f"r{a + 1}c{b + 1}" for a, b in ones),
        "clean:",
        clean,
        "grid",
        g,
    )

"""What the hunt scripts share (#605): the hunt table, the log directory, the q34 criterion, the
HIT-block log lines and their parser. Importing it puts finders/qqrr and the repo root on
sys.path, so a script imports it before `checker`, `model`, `oracle` and `examples`."""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "finders" / "qqrr"))
sys.path.insert(0, str(ROOT))

# cage cell, bounded cell, seed grid (a found grid satisfying all but the tie)
HUNTS = {
    # r5c1 seed: the first br grid found with the bands kept; everything but r4c1 <= 7 holds.
    "r5c1": (
        (4, 0),
        (3, 0),
        "591247638/672183954/438695127/865934271/927516483/143872569/284369715/716458392/359721846",
    ),
    # r1c5 seed: #593 rerun grid 1 (hypotheses on, br): 33 at r1c5, QR 10, r1c4 = 7.
    "r1c5": (
        (0, 4),
        (0, 3),
        "356791428/974286531/128534967/215948673/483617295/697352814/562873149/749165382/831429756",
    ),
}
LOGS = Path(os.environ.get("HUNT_LOGS", ROOT / ".scratch" / "place"))


def q34_zone(n, r, c):
    """Top-left cells of every window sharing a cell with one of (r, c)'s four windows."""
    return [
        (wr, wc)
        for wr in range(r - 2, r + 2)
        for wc in range(c - 2, c + 2)
        if 0 <= wr <= n - 2 and 0 <= wc <= n - 2
    ]


def q34_cells(n):
    return [(r, c) for r in range(1, n - 1) for c in range(1, n - 1)]


def q34_accept(ranks, cr):
    """Interior cells of QQRR 34..36 none of whose windows shares a cell with a QR-1 window.
    `ranks` is the window-rank table, `cr` the cell QQRR table."""
    n = len(ranks) + 1
    ones = {
        (wr, wc) for wr in range(n - 1) for wc in range(n - 1) if ranks[wr][wc] == 1
    }
    return [
        (r, c)
        for r, c in q34_cells(n)
        if 34 <= cr[r][c] <= 36 and not ones & set(q34_zone(n, r, c))
    ]


def tie_line(ta, tb, num, la, lb, qqrr):
    return (
        f"  tie r{ta[0] + 1}c{ta[1] + 1} {'|'.join(map(str, la))} = "
        f"r{tb[0] + 1}c{tb[1] + 1} {'|'.join(map(str, lb))}, number {num}, QQRR {qqrr}"
    )


def grid_line(grid):
    return "  grid " + "/".join("".join(map(str, r)) for r in grid)


TIE = re.compile(r"  tie (r\dc\d) [\d|]+ = (r\dc\d) [\d|]+, number (\d+), QQRR (\d+)")


def parse_hits(text):
    """Each complete HIT block of a finder log as {"ties": [(a, b, number, qqrr)], "grid": str},
    read by the `  tie ` and `  grid ` markers, so any number of tie lines parses. chan_big
    prints a HIT only with at least one tie, so a block with no tie or no grid was cut short
    by a kill and is left out."""
    hits = []
    for line in text.split("\n"):
        if line.startswith("HIT"):
            hits.append({"ties": [], "grid": None})
        elif hits and line.startswith("  tie "):
            hits[-1]["ties"].append(TIE.match(line).groups())
        elif hits and line.startswith("  grid "):
            hits[-1]["grid"] = line.split()[1]
    return [h for h in hits if h["ties"] and h["grid"]]


def logged_grids(path):
    """Every `  grid ` line of a finder log, as its slash-joined digit string."""
    return [
        line.split()[1]
        for line in Path(path).read_text().split("\n")
        if line.startswith("  grid ")
    ]

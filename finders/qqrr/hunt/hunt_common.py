"""What the hunt scripts share (#605): the hunt table, the log directory, the q34 criterion, the
HIT-block log lines and their parser. Importing it puts finders/qqrr and the repo root on
sys.path, so a script imports it before `checker`, `model`, `oracle` and `examples`."""

import os
import re
import sys
from pathlib import Path
from typing import NamedTuple

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


def grid_text(rows):
    """Nine rows as the slash-joined text a HIT block and examples.jsonl carry."""
    return "/".join("".join(map(str, r)) for r in rows)


def grid_line(grid):
    return "  grid " + grid_text(grid)


def qqrr_line(cage, corner, ten, ten_rank, bound):
    """The cage line of a HIT block: the cage's and the corner's QQRR, the QR window at `ten`
    and its rank, and the bounded cell's digit."""
    return (
        f"  QQRR cage {cage} corner {corner} QR r{ten[0] + 1}c{ten[1] + 1} {ten_rank} "
        f"bounded cell {bound}"
    )


TIE = re.compile(r"  tie (r\dc\d) [\d|]+ = (r\dc\d) [\d|]+, number (\d+), QQRR (\d+)")


class Tie(NamedTuple):
    """One logged 7-digit tie: the two cells, the shared number and the QQRR, as logged."""

    a: str
    b: str
    number: str
    qqrr: str


GRID = re.compile(r"  grid (\d{9}(?:/\d{9}){8})")


def parse_hits(text):
    """Each complete HIT block of a finder log as {"ties": [Tie], "grid": str},
    read by the `  tie ` and `  grid ` markers, so any number of tie lines parses. chan_big
    prints a HIT only with at least one tie, so a block with no tie or no grid was cut short
    by a kill and is left out. A marker line that does not match its whole form makes its
    block incomplete too."""
    hits = []
    malformed = set()  # indexes of blocks holding a malformed marker line
    for line in text.split("\n"):
        if line.startswith("HIT"):
            hits.append({"ties": [], "grid": None})
        elif hits and line.startswith("  tie "):
            m = TIE.fullmatch(line)
            if m:
                hits[-1]["ties"].append(Tie(*m.groups()))
            else:
                malformed.add(len(hits) - 1)
        elif hits and line.startswith("  grid "):
            m = GRID.fullmatch(line)
            if m:
                hits[-1]["grid"] = m[1]
            else:
                malformed.add(len(hits) - 1)
    return [
        h for i, h in enumerate(hits) if h["ties"] and h["grid"] and i not in malformed
    ]


def logged_grids(path):
    """Every well-formed `  grid ` line of a finder log, as its slash-joined digit string."""
    return [
        m[1]
        for line in Path(path).read_text().split("\n")
        if (m := GRID.fullmatch(line))
    ]

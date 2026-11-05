"""SCRATCH: which single outside digit finishes a board, over every grid left.

Takes the fixed border and pinned inner cells, lists every grid, and prints each clue digit
that leaves exactly one grid, with the cell it reads, then how many grids each clue digit
leaves otherwise. One worker.

Usage: nr_one_more.py BORDER PINS
"""

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, clue_name, line_cells, outside
from nr_outside_finish import all_grids


def nm(k):
    return f"r{k[0] + 1}c{k[1] + 1}"


def main(border, pin_text):
    pins = [(int(p[0]) - 1, int(p[1]) - 1, int(p[2])) for p in pin_text.split(",")]
    grids = all_grids(border, pins)
    rings = [outside(g) for g in grids]
    print("grids", len(grids))
    for g in grids:
        print(" ", " ".join("".join(map(str, row)) for row in g))
    for clue in CLUES:
        by = collections.Counter(r[clue] for r in rings)
        if len(by) < 2:
            continue
        cells = line_cells(clue)
        target = cells[grids[0][cells[0][0]][cells[0][1]] - 1]
        print(clue_name(clue), "reads", nm(target), dict(sorted(by.items())))


if __name__ == "__main__":
    main(*sys.argv[1:])

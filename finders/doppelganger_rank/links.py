"""A hit's SudokuMaker link (#66 § Links, #71), in the layout of Chris's
opening (`docs/research/2026-10-22-doppelganger-rank-opening.png`).

Rows and columns of the canvas are numbered from 1, and the canvas is
n + 4 square: 13x13 at 9x9.

- The n x n grid at r1..n c1..n, its boxes as regions.
- The row notespace at c(n+3) r1..n, row k's missing digit at its k-th
  cell; the column notespace at r(n+3) c1..n. Neither is a region: the
  drawing shades them and borders nothing.
- The box notespace in the canvas's bottom-right corner, one cell per box
  laid out as the boxes are (r11-13 c11-13 at 9x9), each cell its own
  region, as the drawing borders each.
- Every other cell is in no region.

Every rank clue, the board's and the added ones, is cosmetic text (type
2002) at the centre of the cell just past its line's end: above the
canvas for a column's top, left of it for a row's left end, in column or
row n + 1 for the other two ends. The solution, the notespaces' missing
digits included, is entered, never given. The link declares `minDigit` 0
and carries no answer check and no rule constraint.

    uv run finders/doppelganger_rank/hunt.py links DIR

writes `DIR/links/<seed>.txt` for each verified hit of the hunt in DIR, the
driver's `links DIR` on this module's `link_doc`.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# isort: split
import rules

TEXT = {
    "type": "text",
    "size": 0.5,
    "angle": 0,
    "strokeWidth": 0.02,
    "stroke": "#ffffff",
    "fill": "#000000",
}


def notespaces(n, box):
    """The three notespaces' canvas cells, (row, column) from 1, by the
    unit kind each holds the missing digits of: "r", "c" and "b"."""
    bh, bw = box
    side = n + 4
    down, across = n // bh, n // bw
    return {
        "r": [(r, n + 3) for r in range(1, n + 1)],
        "c": [(n + 3, c) for c in range(1, n + 1)],
        "b": [
            (side - down + 1 + i, side - across + 1 + j)
            for i in range(down)
            for j in range(across)
        ],
    }


def text_point(place, n):
    line, end = place
    k = int(line[1:]) - 0.5
    return {
        "top": [k, -0.5],
        "bottom": [k, n + 0.5],
        "left": [-0.5, k],
        "right": [n + 0.5, k],
    }[end]


def link_doc(record):
    """The SudokuMaker document of a hit record (`hunt.py`'s `record`)."""
    n, box = record["size"], tuple(record["box"])
    grid = [tuple(map(int, row)) for row in record["solution"]]
    side = n + 4
    cells = [{} for _ in range(side * side)]
    regions = [-1] * (side * side)

    def at(r, c):
        return (r - 1) * side + (c - 1)

    _rows, _cols, boxes = rules.houses(n, box)
    for k, box_cells in enumerate(boxes.values()):
        for r, c in box_cells:
            cells[at(r + 1, c + 1)] = {"value": grid[r][c]}
            regions[at(r + 1, c + 1)] = k
    missing = rules.read(grid, box).missing
    for kind, places in notespaces(n, box).items():
        for k, cell in enumerate(places, start=1):
            cells[at(*cell)] = {"value": missing[f"{kind}{k}"]}
            if kind == "b":
                regions[at(*cell)] = n + k - 1

    clues = record["clues"]
    text = {
        "name": "Rank clues",
        "type": 2002,
        "params": [{**TEXT, "text": str(c["rank"])} for c in clues],
        "symbols": [
            [*text_point((c["line"], c["end"]), n), i] for i, c in enumerate(clues)
        ],
    }
    return {
        "formatVersion": "1.6.0",
        "puzzle": {
            "name": "",
            "author": "",
            "type": "custom",
            "width": side,
            "height": side,
            "minDigit": 0,
            "maxDigit": n,
            "cells": cells,
            "constraints": [
                {"type": 0},
                {"type": 1, "regions": regions},
                text,
            ],
        },
    }

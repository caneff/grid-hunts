"""SCRATCH: an empty 9x9 SudokuMaker board with plain boxes and 7 circles: six on box centres, one off centre.

usage: aqre_box_seven_link.py OUT_FILE

Circles are cosmetic ellipses (type 2002), in the form `finders/qqrr/opener.json` uses. Boxes 2 and 8 hold no circle.
The off-centre circle is r4c5, an edge of box 5. No digits are entered.
"""

import sys

from sudoku_kit.link_codec import encode_link

CIRCLES = [(2, 2), (2, 8), (5, 2), (5, 8), (8, 2), (8, 8), (4, 5)]

regions = [(r // 3) * 3 + c // 3 for r in range(9) for c in range(9)]
doc = {
    "formatVersion": "1.6.0",
    "puzzle": {
        "name": "",
        "author": "",
        "type": "custom",
        "width": 9,
        "height": 9,
        "minDigit": 1,
        "maxDigit": 9,
        "cells": [{} for _ in range(81)],
        "constraints": [
            {"type": 0},
            {"type": 1, "regions": regions},
            {
                "name": "Circles",
                "type": 2002,
                "params": [{"type": "ellipse", "rx": 0.42, "ry": 0.42, "angle": 0, "fill": "#ffffff00", "stroke": "#000000", "strokeWidth": 0.04}],
                "symbols": [[c - 0.5, r - 0.5] for r, c in CIRCLES],
            },
        ],
    },
}
with open(sys.argv[1], "w") as f:
    f.write(encode_link(doc) + "\n")

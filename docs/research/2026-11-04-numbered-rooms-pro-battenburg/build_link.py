"""SCRATCH: the SudokuMaker link of the 5-given puzzle.

`link_template.json` is the board of sudokumaker-custom-constraints'
examples/numbered-rooms/PUZZLE_LINK.txt with its puzzle removed: its name, author,
given and type-408 clues. It keeps the 11x11 layout and the enterable outside
cells with the Numbered Rooms rule. This script adds the five given outside
digits, the rules text and the marks.

The marks are cosmetic text, so the app's own solver does not read them and
reports more than one solution. The uniqueness proof is `nr_verify_sat.py`.

Usage: build_link.py OUT_FILE
"""

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from nr import marks, outside
from sudoku_kit.link_codec import decode_puzzle, encode_link

GRID = [
    [int(d) for d in row]
    for row in (
        "863479125 924158367 715326894 192685473 647931582 "
        "358247619 239814756 586793241 471562938"
    ).split()
]
GIVENS = {("L", 4): 1, ("L", 7): 9, ("R", 6): 8, ("T", 3): 6, ("B", 4): 8}
SIDE = 11
RULES = (
    "Normal sudoku rules apply on the inner 9x9. Numbered Rooms: every outside "
    "cell holds a digit, and that digit is in the Nth cell looking into the grid "
    "from it, where N is the digit in the first cell. That Nth cell is a target; "
    "a cell can be the target of more than one outside cell. Battenburg on "
    "targets: a mark at the corner of four cells of the 9x9 means those four "
    "cells are a checkerboard of target and not target. All such 2x2s are marked, "
    "so no unmarked 2x2 is one."
)
MARK = {
    "type": "text",
    "text": "▚",
    "size": 0.5,
    "angle": 0,
    "strokeWidth": 0,
    "stroke": "#ffffff",
    "fill": "#000000",
}


def outside_index(clue):
    side, i = clue
    return {
        "L": (i + 1) * SIDE,
        "R": (i + 1) * SIDE + SIDE - 1,
        "T": i + 1,
        "B": (SIDE - 1) * SIDE + i + 1,
    }[side]


def outside_outlines():
    """A closed square round each of the 36 outside cells, in canvas units."""
    corners = []
    for i in range(1, SIDE - 1):
        corners += [(0, i), (SIDE - 1, i), (i, 0), (i, SIDE - 1)]
    return [
        [
            {"x": x, "y": y},
            {"x": x + 1, "y": y},
            {"x": x + 1, "y": y + 1},
            {"x": x, "y": y + 1},
            {"x": x, "y": y},
        ]
        for x, y in corners
    ]


def build(template):
    doc = copy.deepcopy(template)
    puzzle = doc["puzzle"]
    puzzle["name"] = "Numbered Rooms with Battenburg targets"
    puzzle["author"] = ""
    puzzle["comment"] = RULES
    puzzle["cells"] = [{} for _ in range(SIDE * SIDE)]
    for clue, value in GIVENS.items():
        puzzle["cells"][outside_index(clue)] = {"given": True, "value": value}
    for constraint in puzzle["constraints"]:
        if constraint.get("name") == "Outside Cell Outlines":
            constraint["lines"] = outside_outlines()
    puzzle["constraints"] = [
        *puzzle["constraints"],
        {
            "name": "Battenburg marks",
            "type": 2002,
            "params": [MARK],
            "symbols": [[c + 2, r + 2, 0] for r, c in sorted(marks(GRID))],
        },
    ]
    return doc


def main(out):
    ring = outside(GRID)
    assert all(ring[clue] == value for clue, value in GIVENS.items())
    template = json.loads((HERE / "link_template.json").read_text())
    link = encode_link(build(template))
    back = decode_puzzle(link)["puzzle"]
    given = {i: c["value"] for i, c in enumerate(back["cells"]) if c}
    assert given == {outside_index(c): v for c, v in GIVENS.items()}
    points = next(c for c in back["constraints"] if c["type"] == 2002)["symbols"]
    assert {(y - 2, x - 2) for x, y, _ in points} == set(marks(GRID))
    Path(out).write_text(link + "\n")
    print(f"{len(given)} givens, {len(points)} marks, no solution digit in the link")


if __name__ == "__main__":
    main(sys.argv[1])

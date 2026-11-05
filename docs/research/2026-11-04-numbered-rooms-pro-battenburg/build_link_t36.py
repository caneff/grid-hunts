"""SCRATCH: the SudokuMaker link of a board read from a grid. No givens. Defaults to the 27-mark
board; ROWS picks another.

Reuses build_link.py's board. Not a unique puzzle. The marks are cosmetic text, so the
app's own solver does not read them.

Usage: build_link_t36.py OUT_FILE [ROWS]
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_link as B
from nr import is_sudoku, marks, targets
from sudoku_kit.link_codec import decode_puzzle, encode_link

ROWS = "918732456 465819327 273456819 346578291 187294563 529361748 851927634 792643185 634185972"
GRID = [[int(d) for d in row] for row in ROWS.split()]
B.GRID = GRID
B.GIVENS = {}


def main(out, rows=ROWS):
    grid = [[int(d) for d in row] for row in rows.split()]
    B.GRID = grid
    assert is_sudoku(grid)
    hit = len(targets(grid))
    board = marks(grid)
    doc = B.build(json.loads((HERE / "link_template.json").read_text()))
    doc["puzzle"]["name"] = f"Numbered Rooms with Battenburg targets, {len(board)} marks, {hit} targets"
    link = encode_link(doc)
    back = decode_puzzle(link)["puzzle"]
    assert not any(back["cells"])
    points = next(c for c in back["constraints"] if c["type"] == 2002)["symbols"]
    assert {(y - 2, x - 2) for x, y, _ in points} == set(board)
    Path(out).write_text(link + "\n")
    print(f"0 givens, {len(points)} marks")


if __name__ == "__main__":
    main(*sys.argv[1:])

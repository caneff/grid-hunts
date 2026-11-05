"""SCRATCH: the SudokuMaker link of the 20-mark board that pins the border. No givens.

Reuses build_link.py's board. Not a unique puzzle: the border has 175,079 fillings. The
marks are cosmetic text, so the app's own solver does not read them.

Usage: build_link_20.py OUT_FILE
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_link as B
from nr import marks
from nr_force_verify import GRID
from sudoku_kit.link_codec import decode_puzzle, encode_link

B.GRID = GRID
B.GIVENS = {}
EXPECTED = (
    "r1c2 r1c3 r2c6 r3c2 r3c3 r3c4 r3c6 r4c2 r4c6 r4c7 r4c8 "
    "r5c1 r5c2 r5c6 r6c2 r6c3 r6c6 r7c2 r7c3 r8c3"
).split()


def main(out):
    board = marks(GRID)
    assert sorted(f"r{r + 1}c{c + 1}" for r, c in board) == sorted(EXPECTED)
    doc = B.build(json.loads((HERE / "link_template.json").read_text()))
    doc["puzzle"]["name"] = "Numbered Rooms with Battenburg targets, 20 marks"
    link = encode_link(doc)
    back = decode_puzzle(link)["puzzle"]
    assert not any(back["cells"])
    points = next(c for c in back["constraints"] if c["type"] == 2002)["symbols"]
    assert {(y - 2, x - 2) for x, y, _ in points} == set(board)
    Path(out).write_text(link + "\n")
    print(f"0 givens, {len(points)} marks")


if __name__ == "__main__":
    main(sys.argv[1])

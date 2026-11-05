"""SCRATCH: draw a 36-target grid. Pink is a target; marks and outside digits are read
from the grid by the reader.

Usage: render_full_targets.py OUT_PNG [ROWS]
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from finders.hunt.render import GridCanvas
from nr import marks, outside, targets
from render_board8 import mark

ROWS = "621483759 359721684 487596321 168942537 593617248 274835916 915378462 846259173 732164895"
PINK_FILL = "#ee6a8c"
BLUE = "#2f55d4"
CELL = 76


def main(out, rows=ROWS):
    grid = [[int(d) for d in row] for row in rows.split()]
    hit = targets(grid)
    assert len(hit) == 36
    canvas = GridCanvas(11, 11, cell=CELL, margin=16)
    for r, c in hit:
        canvas.shade_cell(r + 1, c + 1, PINK_FILL)
    left, top = canvas.margin, canvas.margin
    for i in range(12):
        x, y = left + i * CELL, top + i * CELL
        low = top + (CELL if i in (0, 11) else 0)
        high = top + 11 * CELL - (CELL if i in (0, 11) else 0)
        canvas.draw.line((x, low, x, high), fill="#c8c8c8", width=1)
        canvas.draw.line((low, y, high, y), fill="#c8c8c8", width=1)
    for i in range(10):
        x, y = left + (i + 1) * CELL, top + (i + 1) * CELL
        width = 5 if i % 3 == 0 else 1
        canvas.draw.line((x, top + CELL, x, top + 10 * CELL), fill="black", width=width)
        canvas.draw.line((left + CELL, y, left + 10 * CELL, y), fill="black", width=width)
    for r in range(9):
        for c in range(9):
            canvas.digit(r + 1, c + 1, grid[r][c], color="black")
    places = {"L": lambda i: (i + 1, 0), "R": lambda i: (i + 1, 10), "T": lambda i: (0, i + 1), "B": lambda i: (10, i + 1)}
    for (side, i), v in outside(grid).items():
        canvas.digit(*places[side](i), v, color=BLUE)
    for r, c in marks(grid):
        mark(canvas, r, c)
    temporary = f"{out}.tmp.png"
    canvas.image.save(temporary)
    os.replace(temporary, out)


if __name__ == "__main__":
    main(*sys.argv[1:])

"""SCRATCH: draw what the current board forces, from the nr_board5.py run.

Pink is a target, green is not. A blue outline marks a colour he did not draw that
the board forces. Black digits outside are his givens. Blue digits are his; red
digits are newly forced. Small digits are the options left, shown for cells with at
most four. The values below are copied from that run's output.

Usage: render_board5.py OUT_PNG
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from finders.hunt.render import GridCanvas
from nr_board4 import cell
from nr_board5 import BOARD, COLOURS, RING

PINK = "#ee6a8c"
GREEN = "#d3f492"
BLUE = "#2f55d4"
RED = "#c40000"
HIS = {(0, 0): 9, (8, 0): 6, (8, 5): 4}
NEW = {(3, 8): 9, (6, 0): 1, (8, 7): 9, (8, 8): 2}
NEW_PINK = ["r1c8"]
NEW_GREEN = ["r1c7", "r4c9", "r7c9"]
OPTIONS = {
    "r1c2": "3568",
    "r1c6": "28",
    "r1c9": "56",
    "r6c1": "2345",
    "r8c1": "27",
    "r8c9": "348",
    "r9c2": "57",
    "r9c3": "3578",
    "r9c4": "1357",
    "r9c5": "1357",
    "r9c7": "3578",
}
OUTSIDE_NEW = {("L", 6): "1", ("L", 0): "56", ("B", 8): "348"}
CELL = 76


def ring_place(clue):
    side, i = clue
    return {
        "L": (i + 1, 0),
        "R": (i + 1, 10),
        "T": (0, i + 1),
        "B": (10, i + 1),
    }[side]


def outline(canvas, r, c):
    x0, y0, x1, y1 = canvas._cell_box(r, c)
    canvas.draw.rectangle((x0 + 4, y0 + 4, x1 - 4, y1 - 4), outline=BLUE, width=4)


def mark(canvas, r, c):
    """The checkerboard symbol at the corner of window (r, c), 9x9 indices."""
    x = canvas.margin + (c + 2) * canvas.cell
    y = canvas.margin + (r + 2) * canvas.cell
    s = 11
    canvas.draw.rectangle((x - s, y - s, x + s, y + s), fill="white", outline="black")
    canvas.draw.rectangle((x - s, y - s, x, y), fill="black")
    canvas.draw.rectangle((x, y, x + s, y + s), fill="black")


def main(out):
    canvas = GridCanvas(11, 11, cell=CELL, margin=16)
    for name, want in COLOURS:
        r, c = cell(name)
        canvas.shade_cell(r + 1, c + 1, PINK if want else GREEN)
    for name in NEW_PINK:
        r, c = cell(name)
        canvas.shade_cell(r + 1, c + 1, PINK)
    for name in NEW_GREEN:
        r, c = cell(name)
        canvas.shade_cell(r + 1, c + 1, GREEN)

    left, top = canvas.margin, canvas.margin
    for i in range(12):
        x = left + i * CELL
        y = top + i * CELL
        edge = 0 if i in (0, 11) else 1
        ends = (top + (CELL if i in (0, 11) else 0), top + 11 * CELL - (CELL if i in (0, 11) else 0))
        canvas.draw.line((x, ends[0], x, ends[1]), fill="#c8c8c8", width=1 + edge * 0)
        canvas.draw.line((ends[0], y, ends[1], y), fill="#c8c8c8", width=1)
    for i in range(10):
        x = left + (i + 1) * CELL
        y = top + (i + 1) * CELL
        width = 5 if i % 3 == 0 else 1
        canvas.draw.line((x, top + CELL, x, top + 10 * CELL), fill="black", width=width)
        canvas.draw.line((left + CELL, y, left + 10 * CELL, y), fill="black", width=width)

    for name in NEW_PINK + NEW_GREEN:
        r, c = cell(name)
        outline(canvas, r + 1, c + 1)
    for name, text in OPTIONS.items():
        r, c = cell(name)
        canvas.digit(r + 1, c + 1, text, color=RED, font_size=19)
    for (r, c), v in HIS.items():
        canvas.digit(r + 1, c + 1, v, color=BLUE)
    for (r, c), v in NEW.items():
        canvas.digit(r + 1, c + 1, v, color=RED)
    for clue, v in RING.items():
        canvas.digit(*ring_place(clue), v, color="black")
    for clue, text in OUTSIDE_NEW.items():
        size = None if len(text) == 1 else 22
        canvas.digit(*ring_place(clue), text, color=RED, font_size=size)
    for r, c in BOARD:
        mark(canvas, r, c)

    temporary = f"{out}.tmp.png"
    canvas.image.save(temporary)
    os.replace(temporary, out)


if __name__ == "__main__":
    main(sys.argv[1])

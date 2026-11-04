"""SCRATCH: draw what the sixth board plus mark r3c4 forces, negative rule on.

Reads nr_board8.py's JSON. Pink is a target, green is not. A blue outline marks a
colour he did not draw. Black digits are his givens, blue his entered digits, red the
newly forced ones. Small red digits are the options left, for at most four.

Usage: render_board8.py IN_JSON OUT_PNG
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from finders.hunt.render import GridCanvas
from nr_board7 import BOARD, DIGITS, GREEN, PINK, RING, cell

PINK_FILL = "#ee6a8c"
GREEN_FILL = "#d3f492"
BLUE = "#2f55d4"
RED = "#c40000"
CELL = 76
EXTRA_MARK = (2, 3)


def place(name):
    side, i = name[0], int(name[1:]) - 1
    return {"L": (i + 1, 0), "R": (i + 1, 10), "T": (0, i + 1), "B": (10, i + 1)}[side]


def mark(canvas, r, c, color="black"):
    x = canvas.margin + (c + 2) * canvas.cell
    y = canvas.margin + (r + 2) * canvas.cell
    s = 11
    canvas.draw.rectangle((x - s, y - s, x + s, y + s), fill="white", outline=color)
    canvas.draw.rectangle((x - s, y - s, x, y), fill=color)
    canvas.draw.rectangle((x, y, x + s, y + s), fill=color)


def main(source, out):
    data = json.loads(Path(source).read_text())
    canvas = GridCanvas(11, 11, cell=CELL, margin=16)
    for name in PINK + data["pink"]:
        r, c = cell(name)
        canvas.shade_cell(r + 1, c + 1, PINK_FILL)
    for name in GREEN + data["green"]:
        r, c = cell(name)
        canvas.shade_cell(r + 1, c + 1, GREEN_FILL)

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

    for name in data["pink"] + data["green"]:
        r, c = cell(name)
        x0, y0, x1, y1 = canvas._cell_box(r + 1, c + 1)
        canvas.draw.rectangle((x0 + 4, y0 + 4, x1 - 4, y1 - 4), outline=BLUE, width=4)

    for name, allowed in data["options"].items():
        r, c = cell(name)
        if (r, c) in DIGITS:
            canvas.digit(r + 1, c + 1, DIGITS[r, c], color=BLUE)
        elif len(allowed) == 1:
            canvas.digit(r + 1, c + 1, allowed[0], color=RED)
        elif len(allowed) <= 4:
            canvas.digit(r + 1, c + 1, "".join(map(str, allowed)), color=RED, font_size=19)

    for clue, v in RING.items():
        side, i = clue
        canvas.digit(*place(f"{side}{i + 1}"), v, color="black")
    for name, allowed in data["outside"].items():
        if len(allowed) == 1:
            canvas.digit(*place(name), allowed[0], color=RED)
        elif len(allowed) <= 4:
            canvas.digit(*place(name), "".join(map(str, allowed)), color=RED, font_size=19)

    for r, c in BOARD:
        mark(canvas, r, c)
    mark(canvas, *EXTRA_MARK, color=BLUE)

    temporary = f"{out}.tmp.png"
    canvas.image.save(temporary)
    os.replace(temporary, out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

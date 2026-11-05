"""Draw what a board forces, from the JSON that nr_check.py json=FILE writes.

Pink is always a target, green never, white open. Black digits are what the board file
gives, red digits are forced, and small red digits are the options left, for at most
four. Marks are from the board file.

Usage: render_forced.py BOARD_JSON FORCED_JSON OUT_PNG
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from finders.hunt.render import GridCanvas
from render_board8 import mark, place

PINK_FILL = "#ee6a8c"
GREEN_FILL = "#d3f492"
RED = "#c40000"
CELL = 76


def cell(name):
    return int(name[1]) - 1, int(name[3]) - 1


def main(board_path, forced_path, out):
    board = json.loads(Path(board_path).read_text())
    forced = json.loads(Path(forced_path).read_text())
    canvas = GridCanvas(11, 11, cell=CELL, margin=16)
    for name, (yes, no) in forced["status"].items():
        r, c = cell(name)
        if yes and not no:
            canvas.shade_cell(r + 1, c + 1, PINK_FILL)
        elif no and not yes:
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
    for name, allowed in forced["options"].items():
        r, c = cell(name)
        if name in board.get("digits", {}):
            canvas.digit(r + 1, c + 1, allowed[0], color="black")
        elif len(allowed) == 1:
            canvas.digit(r + 1, c + 1, allowed[0], color=RED)
        elif len(allowed) <= 4:
            canvas.digit(r + 1, c + 1, "".join(map(str, allowed)), color=RED, font_size=19)
    for name, allowed in forced["outside"].items():
        if name in board.get("outside", {}):
            canvas.digit(*place(name), allowed[0], color="black")
        elif len(allowed) == 1:
            canvas.digit(*place(name), allowed[0], color=RED)
        elif len(allowed) <= 4:
            canvas.digit(*place(name), "".join(map(str, allowed)), color=RED, font_size=19)
    for name in board["marks"]:
        mark(canvas, *cell(name))
    temporary = f"{out}.tmp.png"
    canvas.image.save(temporary)
    os.replace(temporary, out)


if __name__ == "__main__":
    main(*sys.argv[1:])

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

N = 6
CELL = 48
PAD = 16
W = N * CELL
row = json.loads(Path(sys.argv[1]).read_text().splitlines()[0])
sh = set(row["shape"])
grid = row["grid"]
sets = [[2, 21, 22, 30], [2, 21, 22, 32]]
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
img = Image.new("RGB", (2 * (W + PAD) + PAD, 2 * (W + PAD) + PAD), "white")
d = ImageDraw.Draw(img)


def board(ox, oy, marks, solved):
    for i in range(N * N):
        r, c = divmod(i, N)
        x = ox + c * CELL
        y = oy + r * CELL
        if solved and i in sh:
            d.rectangle([x, y, x + CELL, y + CELL], fill=(170, 170, 170))
        if solved:
            d.text(
                (x + CELL / 2, y + CELL / 2),
                str(grid[i]),
                fill="black",
                font=font,
                anchor="mm",
            )
        if i in marks:
            d.ellipse(
                [x + 5, y + 5, x + CELL - 5, y + CELL - 5], outline=(200, 0, 0), width=3
            )
    for t in range(N + 1):
        w = 3 if t in (0, N) else 1
        d.line([ox, oy + t * CELL, ox + W, oy + t * CELL], fill="black", width=w)
        d.line([ox + t * CELL, oy, ox + t * CELL, oy + W], fill="black", width=w)


for k, marks in enumerate(sets):
    oy = PAD + k * (W + PAD)
    board(PAD, oy, marks, False)
    board(PAD + W + PAD, oy, marks, True)
img.save(sys.argv[2])

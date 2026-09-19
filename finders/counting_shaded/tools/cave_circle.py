"""Circle the cells of a 6x6 Latin solution whose digit is a valid Cave clue
(count of same-colour cells seen orthogonally, itself included)."""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

N = 6


def seen(i, region):
    r, c = divmod(i, N)
    k = 1
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        rr, cc = r + dr, c + dc
        while 0 <= rr < N and 0 <= cc < N and (rr * N + cc) in region:
            k += 1
            rr += dr
            cc += dc
    return k


rows = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
CELL = 48
PAD = 16
W = N * CELL
img = Image.new("RGB", (len(rows) * (W + PAD) + PAD, W + 2 * PAD), "white")
d = ImageDraw.Draw(img)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
for k, row in enumerate(rows):
    sh = set(row["shape"])
    un = set(range(N * N)) - sh
    grid = row["grid"]
    cave = [i for i in un if grid[i] == seen(i, un)]
    wall = [i for i in sh if grid[i] == seen(i, sh)]
    print(
        f"grid {k + 1}: cave clues {[f'r{i // N + 1}c{i % N + 1}' for i in cave]}; shaded cells whose digit counts shaded seen: {[f'r{i // N + 1}c{i % N + 1}' for i in wall]}"
    )
    ox = PAD + k * (W + PAD)
    oy = PAD
    for i in range(N * N):
        r, c = divmod(i, N)
        x = ox + c * CELL
        y = oy + r * CELL
        if i in sh:
            d.rectangle([x, y, x + CELL, y + CELL], fill=(170, 170, 170))
        d.text(
            (x + CELL / 2, y + CELL / 2),
            str(grid[i]),
            fill="black",
            font=font,
            anchor="mm",
        )
        if i in cave or i in wall:
            d.ellipse(
                [x + 5, y + 5, x + CELL - 5, y + CELL - 5], outline=(200, 0, 0), width=3
            )
    for t in range(N + 1):
        w = 3 if t in (0, N) else 1
        d.line([ox, oy + t * CELL, ox + W, oy + t * CELL], fill="black", width=w)
        d.line([ox + t * CELL, oy, ox + t * CELL, oy + W], fill="black", width=w)
img.save(sys.argv[2])
print("wrote", sys.argv[2])

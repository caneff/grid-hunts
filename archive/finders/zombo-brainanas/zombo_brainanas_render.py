"""zombo_brainanas_render.py full.json out.png — shaded grid: green infected, red patient zero,
cream uninfected, circles, and every possible Cocci Dot (white dot on an edge between
consecutive uninfected digits)."""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

d = json.loads(Path(sys.argv[1]).read_text())
N = 9
C = 70
M = 20
W = N * C + 2 * M
img = Image.new("RGB", (W, W), "white")
dr = ImageDraw.Draw(img)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
circles = {tuple(p) for p in d["circles"]}
box = lambda r, c: (r // 3) * 3 + c // 3 + 1
for r in range(N):
    for c in range(N):
        x0, y0 = M + c * C, M + r * C
        inf = d["infected"][r][c] == "*"
        pz = inf and int(d["grid"][r][c]) == box(r, c)
        dr.rectangle(
            [x0, y0, x0 + C, y0 + C],
            fill=(190, 40, 40) if pz else (70, 120, 70) if inf else (255, 245, 200),
        )
        if (r, c) in circles:
            dr.ellipse(
                [x0 + 8, y0 + 8, x0 + C - 8, y0 + C - 8], outline="black", width=4
            )
        t = d["grid"][r][c]
        bb = dr.textbbox((0, 0), t, font=font)
        dr.text(
            (x0 + C / 2 - (bb[2] - bb[0]) / 2, y0 + C / 2 - (bb[3] - bb[1]) / 2 - 4),
            t,
            fill="white" if inf else "black",
            font=font,
        )
for i in range(N + 1):
    w = 4 if i % 3 == 0 else 1
    dr.line([M + i * C, M, M + i * C, M + N * C], fill="black", width=w)
    dr.line([M, M + i * C, M + N * C, M + i * C], fill="black", width=w)
g = d["grid"]
infd = d["infected"]
for r in range(N):
    for c in range(N):
        for a, b in ((r + 1, c), (r, c + 1)):
            if (
                a < N
                and b < N
                and infd[r][c] != "*"
                and infd[a][b] != "*"
                and abs(int(g[r][c]) - int(g[a][b])) == 1
            ):
                cx, cy = M + (c + b + 1) * C / 2, M + (r + a + 1) * C / 2
                dr.ellipse(
                    [cx - 9, cy - 9, cx + 9, cy + 9],
                    fill="white",
                    outline="black",
                    width=3,
                )
img.save(sys.argv[2])

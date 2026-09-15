"""Picture of a Ghosts grid: digits on white, ghost cells circled.

    uv run --with pillow docs/research/ghosts/render.py out.png

The grid is the probe's 8-ghost solution (2026-09-15-ghosts-eight-probe.md);
`*` after a digit marks a ghost.
"""

import sys

from PIL import Image, ImageDraw, ImageFont

GRID = """
5  8  1  9  2  4  3  6  7
9  3* 4* 7  6  8  1  2  5
2  6* 7* 5* 3* 1* 9  4  8
4* 7* 8* 6* 1  9  2  5  3
3* 5* 6* 4* 7  2* 8  1  9
1  9  2  3* 8  5* 4* 7  6
8  4  3  1  5* 7* 6* 9  2
7  2  9  8  4* 6* 5* 3* 1*
6  1  5  2  9  3* 7  8  4
"""

N = 9
CELL = 72
MARGIN = 24
SIDE = N * CELL + 2 * MARGIN
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def render(rows):
    img = Image.new("RGB", (SIDE, SIDE), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, int(CELL * 0.5))
    for r, row in enumerate(rows):
        for c, tok in enumerate(row):
            cx = MARGIN + c * CELL + CELL / 2
            cy = MARGIN + r * CELL + CELL / 2
            if tok.endswith("*"):
                rad = CELL * 0.38
                draw.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), outline="black", width=3)
            draw.text((cx, cy), tok[0], fill="black", font=font, anchor="mm")
    for i in range(N + 1):
        w = 5 if i % 3 == 0 else 1
        p = MARGIN + i * CELL
        draw.line((MARGIN, p, SIDE - MARGIN, p), fill="black", width=w)
        draw.line((p, MARGIN, p, SIDE - MARGIN), fill="black", width=w)
    return img


if __name__ == "__main__":
    rows = [line.split() for line in GRID.strip().splitlines()]
    render(rows).save(sys.argv[1])

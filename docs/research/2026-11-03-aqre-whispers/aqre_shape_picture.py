"""SCRATCH: draw the second forced-9 shape with each way it can hold the circled 8.

For each distinct r4 placement in one orientation-free view, it draws the shape with a valid shading and digits
from `holds_eight`: grey is shaded, white is the unshaded 5, blue ring is the circled 8, and a dashed line marks
the row of the 8 circles. Ways that differ only by the mirror or the board position are drawn once.
"""

import os
import sys
from pathlib import Path

import aqre_r5_eight_regions as eight_regions
from jigsaw_r5_diversity import shape_key
from PIL import Image, ImageDraw, ImageFont

SHAPE = [(0, 2), (0, 3), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2), (2, 3), (3, 1)]
ROW = 3
CELL = 64
PAD = 34
CAPTION = 34


def images():
    seen = set()
    for flip in (False, True):
        cells = [(r, -c if flip else c) for r, c in SHAPE]
        for _ in range(4):
            cells = [(c, -r) for r, c in cells]
            top, left = min(r for r, _ in cells), min(c for _, c in cells)
            seen.add(frozenset((r - top, c - left) for r, c in cells))
    return seen


def main(out):
    eight_regions.ROW = ROW
    ways = {}
    key = shape_key(SHAPE)
    for image in images():
        height, width = max(r for r, _ in image) + 1, max(c for _, c in image) + 1
        for dr in range(10 - height):
            for dc in range(10 - width):
                cells = frozenset((r + dr, c + dc) for r, c in image)
                on_row = [c for r, c in cells if r == ROW]
                if len(on_row) != 2 or shape_key(sorted(cells)) != key:
                    continue
                for c8 in on_row:
                    got = eight_regions.holds_eight(cells, (ROW, c8))
                    if not got:
                        continue
                    top, left = min(r for r, _ in cells), min(c for _, c in cells)
                    rel = frozenset((r - top, c - left) for r, c in cells)
                    pair = (ROW - top, c8 - left)
                    mirrored_w = max(c for _, c in rel)
                    twin = (frozenset((r, mirrored_w - c) for r, c in rel), (pair[0], mirrored_w - pair[1]))
                    label = min((sorted(rel), pair), (sorted(twin[0]), twin[1]))
                    ways.setdefault(str(label), (rel, top, left, got, c8))
    print(f"{len(ways)} ways up to the mirror", flush=True)
    columns = min(4, len(ways))
    rows = (len(ways) + columns - 1) // columns
    tile_w = 4 * CELL + PAD
    tile_h = 5 * CELL + PAD + CAPTION
    picture = Image.new("RGB", (columns * tile_w + PAD, rows * tile_h + PAD), "white")
    draw = ImageDraw.Draw(picture)
    digit_font = ImageFont.load_default(size=30)
    caption_font = ImageFont.load_default(size=20)
    for i, (rel, top, left, (hole, place), c8) in enumerate(ways.values()):
        x0 = PAD + (i % columns) * tile_w
        y0 = PAD + (i // columns) * tile_h + CAPTION
        row_y = y0 + (ROW - top) * CELL + CELL / 2
        draw.text((x0, y0 - CAPTION), f"way {i + 1}: dashes mark the row", font=caption_font, fill="black")
        for r, c in rel:
            x, y = x0 + c * CELL, y0 + r * CELL
            cell = (r + top, c + left)
            shaded = cell != tuple(hole)
            draw.rectangle((x, y, x + CELL, y + CELL), fill="#b8b8b8" if shaded else "white", outline="#888888")
            digit = place[cell] if shaded else 5
            draw.text((x + CELL / 2, y + CELL / 2), str(digit), font=digit_font, fill="black", anchor="mm")
            if digit == 8:
                draw.ellipse((x + 5, y + 5, x + CELL - 5, y + CELL - 5), outline="#2471a3", width=4)
        for r, c in rel:
            x, y = x0 + c * CELL, y0 + r * CELL
            for (dr, dc), line in (((-1, 0), (x, y, x + CELL, y)), ((1, 0), (x, y + CELL, x + CELL, y + CELL)), ((0, -1), (x, y, x, y + CELL)), ((0, 1), (x + CELL, y, x + CELL, y + CELL))):
                if (r + dr, c + dc) not in rel:
                    draw.line(line, fill="black", width=5)
        for x in range(int(x0 - 14), int(x0 + 4 * CELL + 14), 14):
            draw.line((x, row_y + CELL / 2 - 1, x + 7, row_y + CELL / 2 - 1), fill="#c0392b", width=2)
            draw.line((x, row_y - CELL / 2 + 1, x + 7, row_y - CELL / 2 + 1), fill="#c0392b", width=2)
    temp = out / "second-shape.tmp.png"
    picture.save(temp)
    os.replace(temp, out / "second-shape.png")
    print(picture.size, flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

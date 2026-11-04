"""SCRATCH: draw every shape that can hold the 8 and 9 four columns apart, with each way it does.

Regions are grown on r5, with the 8 in any column 1-5, and mirror images drawn once. Each tile shows one valid
filling from `holds_eight`: grey is shaded, white is the unshaded 5, the blue ring is the circled 8, and dashes
mark the row of circles. Tiles are grouped by free shape, and holed shapes are left out.
"""

import os
import sys
from collections import defaultdict
from pathlib import Path

import aqre_r5_eight_regions as eight_regions
from aqre_r5_eight_sheet import has_hole
from jigsaw_r5_diversity import shape_key
from PIL import Image, ImageDraw, ImageFont

ROW = 4
CELL = 52
PAD = 30
CAPTION = 30
PER_ROW = 4
SPAN = 9


def main(out):
    eight_regions.ROW = ROW
    groups = defaultdict(dict)
    for c in range(5):
        for cells in eight_regions.grow((ROW, c)):
            on_row = [q for r, q in cells if r == ROW]
            if len(on_row) != 2 or abs(on_row[0] - on_row[1]) != 4 or eight_regions.straight(cells):
                continue
            got = eight_regions.holds_eight(cells, (ROW, c))
            if not got or has_hole(sorted(cells)):
                continue
            top, left = min(r for r, _ in cells), min(q for _, q in cells)
            rel = frozenset((r - top, q - left) for r, q in cells)
            root = (ROW - top, c - left)
            width = max(q for _, q in rel)
            twin = (sorted((r, width - q) for r, q in rel), (root[0], width - root[1]))
            label = min((sorted(rel), root), twin)
            groups[shape_key(sorted(cells))].setdefault(str(label), (rel, top, left, got))
    tiles = [(i, way) for i, key in enumerate(sorted(groups, key=str)) for way in groups[key].values()]
    print(f"{len(groups)} shapes, {len(tiles)} ways up to the mirror: {[len(groups[k]) for k in sorted(groups, key=str)]}", flush=True)
    tile_w = 6 * CELL + PAD
    tile_h = 6 * CELL + PAD + CAPTION
    rows = (len(tiles) + PER_ROW - 1) // PER_ROW
    picture = Image.new("RGB", (PER_ROW * tile_w + PAD, rows * tile_h + PAD), "white")
    draw = ImageDraw.Draw(picture)
    digit_font = ImageFont.load_default(size=26)
    caption_font = ImageFont.load_default(size=19)
    for n, (shape, (rel, top, left, (hole, place))) in enumerate(tiles):
        x0 = PAD + (n % PER_ROW) * tile_w
        y0 = PAD + (n // PER_ROW) * tile_h + CAPTION
        draw.text((x0, y0 - CAPTION), f"shape {'ABCDEFGH'[shape]}, way {n + 1}", font=caption_font, fill="black")
        for r, q in rel:
            x, y = x0 + q * CELL, y0 + r * CELL
            cell = (r + top, q + left)
            shaded = cell != tuple(hole)
            digit = place[cell] if shaded else 5
            draw.rectangle((x, y, x + CELL, y + CELL), fill="#b8b8b8" if shaded else "white", outline="#888888")
            draw.text((x + CELL / 2, y + CELL / 2), str(digit), font=digit_font, fill="black", anchor="mm")
            if digit == 8:
                draw.ellipse((x + 4, y + 4, x + CELL - 4, y + CELL - 4), outline="#2471a3", width=4)
        for r, q in rel:
            x, y = x0 + q * CELL, y0 + r * CELL
            for (dr, dq), line in (((-1, 0), (x, y, x + CELL, y)), ((1, 0), (x, y + CELL, x + CELL, y + CELL)), ((0, -1), (x, y, x, y + CELL)), ((0, 1), (x + CELL, y, x + CELL, y + CELL))):
                if (r + dr, q + dq) not in rel:
                    draw.line(line, fill="black", width=5)
        row_top = y0 + (ROW - top) * CELL
        for x in range(x0 - 12, x0 + 5 * CELL + 12, 14):
            draw.line((x, row_top, x + 7, row_top), fill="#c0392b", width=2)
            draw.line((x, row_top + CELL, x + 7, row_top + CELL), fill="#c0392b", width=2)
    temp = out / "gap4-shapes.tmp.png"
    picture.save(temp)
    os.replace(temp, out / "gap4-shapes.png")
    print(picture.size, flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

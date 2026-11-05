"""SCRATCH: draw every free shape, and every shape with a circle cell, that tops out at 6.

usage: aqre_top_six_picture.py OUT_PNG

The tests are `aqre_top_six_shapes.holds`. Pairs count once under rotation and reflection. Each circled cell's digit is
its count, as in the runs. Prints each as text, with its best shading, so the picture can be checked against it.
"""

import os
import sys

from aqre_r5_region_max import lines_of
from aqre_top_six_shapes import free_shapes, has_hole, holds, normal
from PIL import Image, ImageDraw, ImageFont

CELL = 40
PAD = 26
CAPTION = 44


def transforms(cells):
    now = list(cells)
    for _ in range(4):
        now = [(c, -r) for r, c in now]
        yield list(now)
        yield [(r, -c) for r, c in now]


def pair_key(shape, root):
    keys = []
    marked = [(*x, x == root) for x in shape]
    now = marked
    for _ in range(4):
        now = [(c, -r, m) for r, c, m in now]
        for version in (now, [(r, -c, m) for r, c, m in now]):
            top, left = min(x[0] for x in version), min(x[1] for x in version)
            keys.append(tuple(sorted((r - top, c - left, m) for r, c, m in version)))
    return min(keys)


def shade_of(cells, root, lines):
    """One 6 shading of the shape, for the printed check."""
    return holds(cells, 6, lines, root) if root else holds(cells, 6, lines)


def main(path):
    alone = []
    pairs = {}
    for shape in free_shapes():
        if has_hole(shape):
            continue
        lines = lines_of(set(shape))
        if not (holds(shape, 8, lines) or holds(shape, 7, lines)):
            alone.append(shape)
        for root in shape:
            if not (holds(shape, 8, lines, root) or holds(shape, 7, lines, root)):
                pairs.setdefault(pair_key(shape, root), (shape, root))
    print(f"shapes alone: {len(alone)}; shape and circle pairs, free: {len(pairs)}", flush=True)
    tiles = [(s, None, "any circle") for s in alone]
    tiles += [(s, r, f"circle ({r[0]},{r[1]})") for s, r in pairs.values() if s not in alone]
    print(f"tiles: {len(tiles)}", flush=True)
    for shape, root, label in tiles:
        print(label, "holds 6:", shade_of(shape, root, lines_of(set(shape))))
        for r in range(max(a for a, _ in shape) + 1):
            print("  ", "".join("O" if (r, c) == root else "X" if (r, c) in shape else "." for c in range(max(b for _, b in shape) + 1)))
    per_row = min(4, len(tiles))
    width = max(max(c for _, c in s) + 1 for s, _, _ in tiles)
    height = max(max(r for r, _ in s) + 1 for s, _, _ in tiles)
    tile_w, tile_h = width * CELL + PAD * 2, height * CELL + PAD + CAPTION
    rows = (len(tiles) + per_row - 1) // per_row
    image = Image.new("RGB", (per_row * tile_w + PAD, rows * tile_h + PAD), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=16)
    for i, (shape, root, _) in enumerate(tiles):
        ox = PAD + (i % per_row) * tile_w
        oy = PAD + (i // per_row) * tile_h
        cells = set(shape)
        for r, c in shape:
            x, y = ox + c * CELL, oy + r * CELL
            draw.rectangle((x, y, x + CELL, y + CELL), fill=(232, 238, 248), outline=(190, 190, 190))
            if (r, c) == root:
                draw.ellipse((x + 6, y + 6, x + CELL - 6, y + CELL - 6), outline=(20, 20, 20), width=3)
        for r, c in shape:
            x, y = ox + c * CELL, oy + r * CELL
            for (dr, dc), edge in (((-1, 0), (x, y, x + CELL, y)), ((1, 0), (x, y + CELL, x + CELL, y + CELL)), ((0, -1), (x, y, x, y + CELL)), ((0, 1), (x + CELL, y, x + CELL, y + CELL))):
                if (r + dr, c + dc) not in cells:
                    draw.line(edge, fill=(20, 20, 20), width=3)
        caption = "tops out at 6 with any circle" if root is None else f"#{i}: 6 with this circle"
        draw.text((ox, oy + (max(r for r, _ in shape) + 1) * CELL + 6), caption, fill=(20, 20, 20), font=font)
    tmp = path + ".tmp.png"
    image.save(tmp)
    os.replace(tmp, path)
    print(f"wrote {path}: {image.size}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])

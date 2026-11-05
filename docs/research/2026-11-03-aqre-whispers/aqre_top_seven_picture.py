"""SCRATCH: draw every free shape, and every shape with a circle cell, that can be 7 but not 8.

usage: aqre_top_seven_picture.py DIR

Reads free-circle-classes.pickle and top-six-shapes logic. Two sheets, both listing shapes once under rotation and
reflection, sorted by bounding box:

A: shapes that top out at 7 with no circle, on the shape alone. A dot marks a circle cell that can hold the circled 7.
   An unmarked cell tops out at 6 with the circle there.
B: shapes that can hold 8 with no circle, but with some circle cell where the circled 8 is impossible and the circled 7
   is possible. A dot marks each such cell.

Counts are checked against the earlier run: 345 shapes, and 4,887 pairs before the shape's own symmetry.
"""

import os
import pickle
import sys
from collections import defaultdict
from pathlib import Path

from aqre_r5_region_max import lines_of
from aqre_top_six_shapes import holds
from PIL import Image, ImageDraw, ImageFont

CELL = 16
GAP = 16
PER_ROW = 18


def seven_not_eight(entry):
    any_7 = any(entry[o][1] or entry[o][2] for o in (True, False))
    return any_7 and not entry[True][0]


def sheet(title, items, path):
    items = sorted(items, key=lambda x: (max(r for r, _ in x[0]) + 1, max(c for _, c in x[0]) + 1, x[0]))
    width = max(max(c for _, c in s) + 1 for s, _ in items)
    height = max(max(r for r, _ in s) + 1 for s, _ in items)
    side = max(width, height)
    tile = side * CELL + GAP
    rows = (len(items) + PER_ROW - 1) // PER_ROW
    image = Image.new("RGB", (PER_ROW * tile + GAP, rows * tile + GAP + 40), "white")
    draw = ImageDraw.Draw(image)
    draw.text((GAP, 10), title, fill=(20, 20, 20), font=ImageFont.load_default(size=20))
    for i, (shape, marks) in enumerate(items):
        ox = GAP + (i % PER_ROW) * tile
        oy = 40 + (i // PER_ROW) * tile
        cells = set(shape)
        for r, c in shape:
            x, y = ox + c * CELL, oy + r * CELL
            draw.rectangle((x, y, x + CELL, y + CELL), fill=(232, 238, 248), outline=(200, 200, 200))
            if (r, c) in marks:
                draw.ellipse((x + 4, y + 4, x + CELL - 4, y + CELL - 4), fill=(20, 60, 160))
        for r, c in shape:
            x, y = ox + c * CELL, oy + r * CELL
            for (dr, dc), edge in (((-1, 0), (x, y, x + CELL, y)), ((1, 0), (x, y + CELL, x + CELL, y + CELL)), ((0, -1), (x, y, x, y + CELL)), ((0, 1), (x + CELL, y, x + CELL, y + CELL))):
                if (r + dr, c + dc) not in cells:
                    draw.line(edge, fill=(20, 20, 20), width=2)
    tmp = str(path) + ".tmp.png"
    image.save(tmp)
    os.replace(tmp, path)
    print(f"wrote {path}: {image.size}, {len(items)} shapes, {sum(len(m) for _, m in items)} marks", flush=True)


def main(out):
    with (out / "free-circle-classes.pickle").open("rb") as f:
        pairs = pickle.load(f)
    by_shape = defaultdict(set)
    for p in pairs.values():
        if seven_not_eight(p["entry"]):
            by_shape[p["shape"]].add(p["root"])
    shapes = {p["shape"] for p in pairs.values()}
    alone = {}
    for shape in shapes:
        lines = lines_of(set(shape))
        alone[shape] = 8 if holds(shape, 8, lines) else 7 if holds(shape, 7, lines) else 6
    # marks hold one cell per symmetry class of pair, so widen them to the shape's every equal cell
    full = defaultdict(set)
    total = 0
    for shape in shapes:
        lines = lines_of(set(shape))
        for root in shape:
            if not holds(shape, 8, lines, root) and holds(shape, 7, lines, root):
                full[shape].add(root)
                total += 1
    print(f"pairs before symmetry {total}, free pairs {sum(seven_not_eight(p['entry']) for p in pairs.values())}", flush=True)
    if total != 4887 or sum(v == 7 for v in alone.values()) != 345:
        raise SystemExit("COUNT FAILED")
    a = [(s, full[s]) for s in shapes if alone[s] == 7]
    b = [(s, full[s]) for s in shapes if alone[s] == 8 and full[s]]
    print(f"sheet A marks {sum(len(m) for _, m in a)}, sheet B marks {sum(len(m) for _, m in b)}, 8-able shapes with no such cell {sum(alone[s] == 8 and not full[s] for s in shapes)}", flush=True)
    sheet(f"A: {len(a)} shapes that can be 7 but not 8. Dot = circle here can be the 7; no dot = tops out at 6 with the circle there", a, out / "top-seven-a.png")
    sheet(f"B: {len(b)} shapes that can hold 8, with circle cells where they can be 7 but not 8 (dots)", b, out / "top-seven-b.png")


if __name__ == "__main__":
    main(Path(sys.argv[1]))

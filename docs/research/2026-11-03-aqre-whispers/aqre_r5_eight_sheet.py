"""SCRATCH: a representative sheet of the regions that can be the circled 8.

Free shapes (rotations and reflections as one) are grouped into families by bounding box and
longest straight run. Each family shows one shape, its most frequent in the catalogue, with a
valid shading and digits: grey is shaded, white is the unshaded 5, the circle is the 8. A
caption gives the box, the longest run and how many free shapes the family holds.
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from jigsaw_r5_diversity import shape_key
from PIL import Image, ImageDraw, ImageFont

CELL = 26
PAD = 14
CAPTION = 18
PER_ROW = 9
TILE = 9 * CELL + PAD


def longest_run(cells):
    cells = set(cells)
    best = 0
    for r, c in cells:
        for dr, dc in ((0, 1), (1, 0)):
            if (r - dr, c - dc) not in cells:
                length, x, y = 0, r, c
                while (x, y) in cells:
                    length += 1
                    x, y = x + dr, y + dc
                best = max(best, length)
    return best


def box(cells):
    rows = [r for r, _ in cells]
    cols = [c for _, c in cells]
    return tuple(sorted((max(rows) - min(rows) + 1, max(cols) - min(cols) + 1)))


def has_hole(cells):
    """True when empty cells are walled off from outside the shape's bounding box."""
    cells = set(cells)
    rows = [r for r, _ in cells]
    cols = [c for _, c in cells]
    top, bottom, left, right = min(rows) - 1, max(rows) + 1, min(cols) - 1, max(cols) + 1
    seen, stack = {(top, left)}, [(top, left)]
    while stack:
        r, c = stack.pop()
        for x, y in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if top <= x <= bottom and left <= y <= right and (x, y) not in cells and (x, y) not in seen:
                seen.add((x, y))
                stack.append((x, y))
    return len(seen) + len(cells) != (bottom - top + 1) * (right - left + 1)


def main(out):
    catalogue = json.loads((out / "eight-regions-r5.json").read_text())
    by_shape = defaultdict(list)
    for entry in catalogue:
        cells = [tuple(x) for x in entry["cells"]]
        by_shape[shape_key(cells)].append(entry)
    families = defaultdict(list)
    holed = placements = 0
    for key, entries in by_shape.items():
        cells = [tuple(x) for x in entries[0]["cells"]]
        if has_hole(cells):
            holed += 1
            continue
        placements += len(entries)
        families[box(cells), longest_run(cells)].append((len(entries), key, entries))
    print(f"{holed} holed shapes left out; {len(by_shape) - holed} shapes, {placements} placements remain", flush=True)
    order = sorted(families, key=lambda k: (k[0][1], k[0][0], k[1]))
    print(f"{len(by_shape)} free shapes in {len(families)} families; {len(catalogue)} placements", flush=True)
    print("shapes per family:", sum(len(v) for v in families.values()), flush=True)
    rows = (len(order) + PER_ROW - 1) // PER_ROW
    width = PER_ROW * TILE + PAD
    image = Image.new("RGB", (width, rows * (TILE + CAPTION) + PAD), "white")
    draw = ImageDraw.Draw(image)
    digit_font = ImageFont.load_default(size=15)
    caption_font = ImageFont.load_default(size=13)
    for i, family in enumerate(order):
        members = families[family]
        _, _, entries = max(members, key=lambda m: (m[0], m[1]))
        entry = next((e for e in entries if sum(x[0] == 4 for x in e["cells"]) == 1), entries[0])
        cells = [tuple(x) for x in entry["cells"]]
        digits = {(r, c): d for r, c, d in entry["digits"]}
        hole = tuple(entry["hole"])
        top = min(r for r, _ in cells)
        left = min(c for _, c in cells)
        tile_x = PAD + (i % PER_ROW) * TILE
        tile_y = PAD + (i // PER_ROW) * (TILE + CAPTION)
        for r, c in cells:
            x = tile_x + (c - left) * CELL
            y = tile_y + CAPTION + (r - top) * CELL
            shaded = (r, c) != hole
            draw.rectangle((x, y, x + CELL, y + CELL), fill="#b8b8b8" if shaded else "white", outline="#888888")
            digit = 5 if not shaded else digits[r, c]
            draw.text((x + CELL / 2, y + CELL / 2), str(digit), font=digit_font, fill="black", anchor="mm")
            if digit == 8:
                draw.ellipse((x + 2, y + 2, x + CELL - 2, y + CELL - 2), outline="#2471a3", width=2)
        for r, c in cells:
            x = tile_x + (c - left) * CELL
            y = tile_y + CAPTION + (r - top) * CELL
            for (dr, dc), line in (
                ((-1, 0), (x, y, x + CELL, y)),
                ((1, 0), (x, y + CELL, x + CELL, y + CELL)),
                ((0, -1), (x, y, x, y + CELL)),
                ((0, 1), (x + CELL, y, x + CELL, y + CELL)),
            ):
                if (r + dr, c + dc) not in cells:
                    draw.line(line, fill="black", width=3)
        (a, b), run = family
        draw.text((tile_x, tile_y), f"{a}x{b} run {run}: {len(members)}", font=caption_font, fill="black")
    temp = out / "eight-shapes-2.tmp.png"
    image.save(temp)
    os.replace(temp, out / "eight-shapes-2.png")
    print(image.size, flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

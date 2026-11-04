"""SCRATCH: a cheap screen of every 8-region shape, on every row r1-r5, before any enumeration. 8 processes.

Each row's regions are grown fresh with the 8 in columns 1-5, at most two row cells, not straight, not holed,
and each is tested for holding the circled 8 by `holds_eight`. Duplicates under the left-right mirror are
removed, and under the flip and 180 turn on r5 only. A placement is dead when the free cells split into a part
whose size is not a multiple of 9, since regions cannot fill it. Geometry only, so a live placement may
still have no layout.

Controls: r5 must give the catalogue's 29,535 regions before holes and the mirror are taken out, and the
chosen shape must give the enumerator's placement counts, 0 14 28 28 14 for r1 to r5, all two-cell.

Writes shape-screen.json. Two-cell placements fit the split enumerator as it stands. A one-cell placement
leaves the row's 9 in the ninth region, which it would need adding.
"""

import json
import multiprocessing
import sys
from collections import Counter, defaultdict
from pathlib import Path

import aqre_r5_eight_regions as eight_regions
from aqre_r5_chosen_eight import SHAPE
from aqre_r5_cover import FULL, components, mask_of, mirror
from aqre_r5_eight_sheet import box, has_hole, longest_run
from aqre_r5_oriented import canonical
from jigsaw_r5_diversity import shape_key

WORKERS = 8
FORK = multiprocessing.get_context("fork")


def one_root(args):
    row, c = args
    eight_regions.ROW = row
    out = []
    for cells in eight_regions.grow((row, c)):
        if eight_regions.straight(cells) or not eight_regions.holds_eight(cells, (row, c)):
            continue
        out.append(sorted(cells))
    return row, c, out


def main(out):
    shapes = defaultdict(lambda: {r: Counter() for r in range(5)})
    example = {}
    raw = Counter()
    holed = Counter()
    with FORK.Pool(WORKERS) as pool:
        for row, c, found in pool.imap_unordered(one_root, [(r, q) for r in range(5) for q in range(5)]):
            raw[row] += len(found)
            for cells in found:
                key = shape_key(cells)
                if key not in example:
                    example[key] = (cells, has_hole(cells))
                if example[key][1]:
                    holed[row] += 1
                    continue
                mask = mask_of(cells)
                if not (canonical(mask, c) if row == 4 else (c < 4 or mask <= mirror(mask))):
                    continue
                held = sum(r == row for r, _ in cells)
                shapes[key][row]["all", held] += 1
                if all(bin(part).count("1") % 9 == 0 for part in components(FULL & ~mask)):
                    shapes[key][row]["live", held] += 1
            print(f"r{row + 1}c{c + 1}: {len(found):,} regions can be the 8", flush=True)
    print("regions per row before holes and mirror:", [raw[r] for r in range(5)], "holed:", [holed[r] for r in range(5)], flush=True)
    chosen = shapes[shape_key(SHAPE)]
    print("chosen shape, r1 to r5, all placements:", [dict(chosen[r]) for r in range(5)], flush=True)
    summary = []
    totals = Counter()
    for key, rows in shapes.items():
        cells = example[key][0]
        summary.append({
            "cells": cells,
            "box": box(cells),
            "run": longest_run(cells),
            "rows": {f"r{r + 1}": {"live_two": rows[r]["live", 2], "live_one": rows[r]["live", 1], "all_two": rows[r]["all", 2], "all_one": rows[r]["all", 1]} for r in range(5)},
        })
        two = sum(rows[r]["live", 2] for r in range(5))
        one = sum(rows[r]["live", 1] for r in range(5))
        totals["shapes"] += 1
        totals["shapes, a live two-cell placement"] += two > 0
        totals["shapes, only two-cell live placements"] += two > 0 and one == 0
        totals["shapes, only one-cell live placements"] += one > 0 and two == 0
        totals["shapes, no live placement"] += one == 0 and two == 0
        for r in range(5):
            for held, name in ((2, "two-cell"), (1, "one-cell")):
                totals[f"r{r + 1} {name} placements, all"] += rows[r]["all", held]
                totals[f"r{r + 1} {name} placements, live"] += rows[r]["live", held]
    (out / "shape-screen.json").write_text(json.dumps(summary))
    for name, value in sorted(totals.items()):
        print(f"{name}: {value:,}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

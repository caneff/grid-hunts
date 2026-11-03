"""SCRATCH: region geometry only, no shading or whispers. Nine connected 9-cell
regions of a 9x9, exactly eight touching r5. A random walk of border swaps samples
layouts, reaching eight from the 3x3 boxes by never lowering the r5 touch count, then
holding it at eight. This is a sample, not an enumeration: it shows what exists, and
says nothing about what cannot.
"""

import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

from finders.hunt.render import GridCanvas
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver, sudoku_model

ROW = 4
SEEDS = range(6)
SECONDS_PER_SEED = 20.0
SAMPLE_EVERY = 300
STEPS = ((0, 1), (1, 0), (0, -1), (-1, 0))
CELLS = [(r, c) for r in range(9) for c in range(9)]
COLOURS = ["#f4a6a6", "#a6d8f4", "#b6e3a8", "#f7d794", "#d3b6f0", "#f4b6dc", "#a8e6d9", "#d9d9a0", "#c9c9c9"]


def around(cell):
    for dr, dc in STEPS:
        r, c = cell[0] + dr, cell[1] + dc
        if 0 <= r < 9 and 0 <= c < 9:
            yield r, c


def joined(cells):
    cells = set(cells)
    seen, stack = set(), [next(iter(cells))]
    while stack:
        cell = stack.pop()
        if cell not in seen:
            seen.add(cell)
            stack += [n for n in around(cell) if n in cells]
    return seen == cells


def touches(region):
    return len({region[ROW, c] for c in range(9)})


def shape_key(cells):
    """The free polyomino: the same under rotation and reflection."""
    forms = []
    for flip in (False, True):
        pts = [(c, r) if flip else (r, c) for r, c in cells]
        for _ in range(4):
            pts = [(c, -r) for r, c in pts]
            lo_r, lo_c = min(p[0] for p in pts), min(p[1] for p in pts)
            forms.append(tuple(sorted((r - lo_r, c - lo_c) for r, c in pts)))
    return min(forms)


def measure(region):
    groups = [[cell for cell in CELLS if region[cell] == k] for k in range(9)]
    keys = [shape_key(cells) for cells in groups]
    return {
        "shapes": len(set(keys)),
        "straight": sum(
            len({c for _, c in cells}) == 1 or len({r for r, _ in cells}) == 1
            for cells in groups
        ),
        "min_width": min(len({c for _, c in cells}) for cells in groups),
        "widest": max(len({c for _, c in cells}) for cells in groups),
        "squat": sum(
            max(r for r, _ in cells) - min(r for r, _ in cells) <= 3
            and max(c for _, c in cells) - min(c for _, c in cells) <= 3
            for cells in groups
        ),
    }


def walk(seed, seconds):
    rng = random.Random(seed)
    region = {cell: (cell[0] // 3) * 3 + cell[1] // 3 for cell in CELLS}
    samples = []
    start = time.time()
    moves = 0
    while time.time() - start < seconds:
        a, b = rng.sample(CELLS, 2)
        ra, rb = region[a], region[b]
        moves += 1
        if ra == rb:
            continue
        if not any(region[n] == rb for n in around(a)):
            continue
        if not any(region[n] == ra for n in around(b)):
            continue
        before = touches(region)
        region[a], region[b] = rb, ra
        after = touches(region)
        fine = after == 8 if before == 8 else after >= before and after <= 8
        if fine:
            fine = joined([x for x in CELLS if region[x] == ra]) and joined(
                [x for x in CELLS if region[x] == rb]
            )
        if not fine:
            region[a], region[b] = ra, rb
        elif touches(region) == 8 and moves % SAMPLE_EVERY < 40:
            samples.append(dict(region))
    return samples


def fill(region):
    regions = [[cell for cell in CELLS if region[cell] == k] for k in range(9)]
    m, x = sudoku_model(9, None, regions=regions)
    s = solver(60.0)
    status = s.solve(m)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return s.status_name(status), [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    return s.status_name(status), None


def draw(region, path):
    canvas = GridCanvas(9, 9, cell=64, margin=24)
    for r, c in CELLS:
        canvas.shade_cell(r, c, COLOURS[region[r, c]])
    canvas.box_lines(9, 9, thin=1, thick=5)
    for r, c in CELLS:
        x0, y0 = 24 + c * 64, 24 + r * 64
        if c < 8 and region[r, c] != region[r, c + 1]:
            canvas.draw.line((x0 + 64, y0, x0 + 64, y0 + 64), fill="black", width=5)
        if r < 8 and region[r, c] != region[r + 1, c]:
            canvas.draw.line((x0, y0 + 64, x0 + 64, y0 + 64), fill="black", width=5)
    for c in range(9):
        canvas.circle(ROW, c, color="#444444", width=3, radius_frac=0.14)
    temp = path.with_suffix(".tmp.png")
    canvas.image.save(temp)
    os.replace(temp, path)


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pool = []
    for seed in SEEDS:
        found = walk(seed, SECONDS_PER_SEED)
        print(f"seed {seed}: {len(found)} layouts sampled", flush=True)
        pool += found
    if not pool:
        print("no layout reached eight regions on r5", flush=True)
        return
    stats = [measure(region) for region in pool]
    for key in ("shapes", "straight", "squat", "widest", "min_width"):
        print(f"{key}: {sorted(Counter(s[key] for s in stats).items())}", flush=True)
    order = sorted(
        range(len(pool)),
        key=lambda i: (stats[i]["straight"], -stats[i]["shapes"], -stats[i]["min_width"]),
    )
    for rank, i in enumerate(order[:40]):
        status, grid = fill(pool[i])
        print(f"candidate {rank}: {stats[i]}, sudoku fill {status}", flush=True)
        if grid:
            assert touches(pool[i]) == 8
            assert all(
                joined([x for x in CELLS if pool[i][x] == k])
                and sum(pool[i][x] == k for x in CELLS) == 9
                for k in range(9)
            )
            print("\n".join("".join(str(pool[i][r, c]) for c in range(9)) for r in range(9)), flush=True)
            (out / "layout-r5.json").write_text(json.dumps({
                "region": [[pool[i][r, c] for c in range(9)] for r in range(9)],
                "digits": grid,
                "measure": stats[i],
            }))
            draw(pool[i], out / "layout-r5.png")
            print("picture", out / "layout-r5.png", flush=True)
            return
    print("no candidate among the 40 took a sudoku fill", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])

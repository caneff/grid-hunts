"""SCRATCH: jigsaw sudoku (nine irregular connected 9-cell regions), digits 1-9,
Aqre shading, 5-whispers on shaded cells, a circle counting shaded cells in its
region, and every region with at least one shaded cell so each holds a valid
circle. Layouts are random, from border swaps on the 3x3 boxes.
"""

import json
import os
import random
import sys
from pathlib import Path

from connected import add_flow_connectivity
from finders.hunt.render import GridCanvas
from ortools.sat.python import cp_model
from shapes import ORTH
from sudoku_kit.cpsat import solver, sudoku_model

TIME_LIMIT = 180.0
SEEDS = (1, 2, 3)
SWAPS = 4000
STEPS = ((0, 1), (1, 0), (0, -1), (-1, 0))


def neighbours(cell):
    for dr, dc in STEPS:
        r, c = cell[0] + dr, cell[1] + dc
        if 0 <= r < 9 and 0 <= c < 9:
            yield r, c


def connected(cells):
    cells = set(cells)
    seen, stack = set(), [next(iter(cells))]
    while stack:
        cell = stack.pop()
        if cell not in seen:
            seen.add(cell)
            stack += [n for n in neighbours(cell) if n in cells]
    return seen == cells


def layout(seed):
    """Region index per cell: swap two border cells while all regions stay joined."""
    rng = random.Random(seed)
    region = {(r, c): (r // 3) * 3 + c // 3 for r in range(9) for c in range(9)}
    cells = list(region)
    for _ in range(SWAPS):
        a, b = rng.sample(cells, 2)
        ra, rb = region[a], region[b]
        if ra == rb:
            continue
        if not any(region[n] == rb for n in neighbours(a)):
            continue
        if not any(region[n] == ra for n in neighbours(b)):
            continue
        region[a], region[b] = rb, ra
        if not (
            connected([x for x in cells if region[x] == ra])
            and connected([x for x in cells if region[x] == rb])
        ):
            region[a], region[b] = ra, rb
    return region


def build(regions):
    m, x = sudoku_model(9, regions)
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    add_flow_connectivity(m, g)
    shaded = lambda r, c: g[r * 9 + c]
    for a in range(9):
        for b in range(6):
            for line in (
                [shaded(a, b + k) for k in range(4)],
                [shaded(b + k, a) for k in range(4)],
            ):
                m.add_bool_or(line)
                m.add_bool_or([v.Not() for v in line])
    even_low = m.new_bool_var("even_low")
    for r in range(9):
        for c in range(9):
            low = even_low if (r + c) % 2 == 0 else even_low.Not()
            m.add(x[r, c] <= 4).only_enforce_if(shaded(r, c), low)
            m.add(x[r, c] >= 6).only_enforce_if(shaded(r, c), low.Not())
    for i in range(81):
        for j in ORTH[i]:
            if i < j:
                gap = m.new_int_var(0, 8, f"gap{i}_{j}")
                m.add_abs_equality(gap, x[i // 9, i % 9] - x[j // 9, j % 9])
                m.add(gap >= 5).only_enforce_if(g[i], g[j])
    for cells in regions:
        m.add(sum(shaded(r, c) for r, c in cells) >= 1)
    return m, x, g


def violations(digits, shade, regions):
    """Every rule a filled grid breaks, read with no solver."""
    found = []
    full = set(range(1, 10))
    for i in range(9):
        if set(digits[i]) != full:
            found.append(f"row {i + 1} digits")
        if {digits[r][i] for r in range(9)} != full:
            found.append(f"column {i + 1} digits")
    for k, cells in enumerate(regions):
        if {digits[r][c] for r, c in cells} != full:
            found.append(f"region {k} digits")
        if not any(shade[r][c] for r, c in cells):
            found.append(f"region {k} has no shaded cell")
    for a in range(9):
        for b in range(6):
            if len({shade[a][b + k] for k in range(4)}) == 1:
                found.append(f"four in a line, row {a + 1} from column {b + 1}")
            if len({shade[b + k][a] for k in range(4)}) == 1:
                found.append(f"four in a line, column {a + 1} from row {b + 1}")
    for r in range(9):
        for c in range(9):
            for rr, cc in ((r, c + 1), (r + 1, c)):
                if rr < 9 and cc < 9 and shade[r][c] and shade[rr][cc]:
                    if abs(digits[r][c] - digits[rr][cc]) < 5:
                        found.append(f"whisper r{r + 1}c{c + 1}-r{rr + 1}c{cc + 1}")
    cells = [(r, c) for r in range(9) for c in range(9) if shade[r][c]]
    if cells and not connected(cells):
        found.append("shaded not connected")
    return found


def controls(digits, shade, regions):
    swapped = [row[:] for row in digits]
    swapped[0][0], swapped[0][1] = swapped[0][1], swapped[0][0]
    assert any("digits" in v for v in violations(swapped, shade, regions)), "digits"
    blank = [[False] * 9 for _ in range(9)]
    assert any("four" in v for v in violations(digits, blank, regions)), "line"
    assert any("no shaded" in v for v in violations(digits, blank, regions)), "region"
    full = [[True] * 9 for _ in range(9)]
    assert any("whisper" in v for v in violations(digits, full, regions)), "whisper"
    apart = [[False] * 9 for _ in range(9)]
    apart[0][0] = apart[8][8] = True
    assert any("connected" in v for v in violations(digits, apart, regions)), "connect"


def draw(digits, shade, region, spots, path):
    canvas = GridCanvas(9, 9, cell=64, margin=24)
    for r in range(9):
        for c in range(9):
            if shade[r][c]:
                canvas.shade_cell(r, c, "#b8b8b8")
    for spot in spots:
        canvas.circle(*spot, color="#2471a3", width=4)
    for r in range(9):
        for c in range(9):
            canvas.digit(r, c, digits[r][c])
    canvas.box_lines(9, 9, thin=1, thick=5)
    size, margin = 64, 24
    for r in range(9):
        for c in range(9):
            x0, y0 = margin + c * size, margin + r * size
            if c < 8 and region[r, c] != region[r, c + 1]:
                canvas.draw.line((x0 + size, y0, x0 + size, y0 + size), fill="black", width=5)
            if r < 8 and region[r, c] != region[r + 1, c]:
                canvas.draw.line((x0, y0 + size, x0 + size, y0 + size), fill="black", width=5)
    temp = path.with_suffix(".tmp.png")
    canvas.image.save(temp)
    os.replace(temp, path)


def solve(seed, out):
    region = layout(seed)
    regions = [[cell for cell, k in region.items() if k == i] for i in range(9)]
    assert all(len(cells) == 9 and connected(cells) for cells in regions)
    print(f"seed {seed}: region rows")
    print("\n".join("".join(str(region[r, c]) for c in range(9)) for r in range(9)), flush=True)
    m, x, g = build(regions)
    s = solver(TIME_LIMIT)
    status = s.solve(m)
    print(f"seed {seed}: status {s.status_name(status)} in {s.wall_time:.1f}s", flush=True)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return
    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
    controls(digits, shade, regions)
    print(f"seed {seed}: reader violations {violations(digits, shade, regions) or 'none'} (controls fired)", flush=True)
    print("\n".join(
        " ".join(("#" if shade[i][j] else ".") + str(digits[i][j]) for j in range(9))
        for i in range(9)
    ), flush=True)
    spots, counts = [], []
    for cells in regions:
        count = sum(shade[r][c] for r, c in cells)
        counts.append(count)
        spots.append(next(cell for cell in cells if digits[cell[0]][cell[1]] == count))
    print(f"seed {seed}: region counts {counts}, shaded total {sum(counts)}", flush=True)
    print(f"seed {seed}: circles {[f'r{r + 1}c{c + 1}' for r, c in spots]}", flush=True)
    (out / f"grid-7-seed{seed}.json").write_text(json.dumps({
        "digits": digits, "shaded": shade, "regions": regions, "counts": counts,
    }))
    draw(digits, shade, region, spots, out / f"grid-7-seed{seed}.png")
    print(f"seed {seed}: picture {out / f'grid-7-seed{seed}.png'}", flush=True)


if __name__ == "__main__":
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    for seed in SEEDS:
        solve(seed, out_dir)

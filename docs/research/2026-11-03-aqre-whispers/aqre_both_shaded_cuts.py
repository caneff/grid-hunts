"""SCRATCH: the both-shaded rule set with connectivity kept by lazy cuts.

The model without connectivity solves in seconds, while the flow encoding ended
UNKNOWN at 600 s. Each round floods the shading and, for every component but the
largest, adds: some cell of the component is unshaded, or a boundary cell is
shaded, or the witness (a shaded cell of the largest component) is unshaded. The
witness keeps the cut sound for a grid whose shading is only that component. A
wall-clock limit ending the loop proves nothing.
"""

import json
import os
import sys
import time
from pathlib import Path

from aqre_both_shaded_feasible import BOXES, box_of, build, negative_errors
from aqre_shaded_whispers_feasible import violations
from finders.hunt.render import GridCanvas
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver

WALL_LIMIT = 900.0
STEPS = ((0, 1), (1, 0), (0, -1), (-1, 0))


def components(shade):
    left = {(r, c) for r in range(9) for c in range(9) if shade[r][c]}
    found = []
    while left:
        stack, group = [left.pop()], set()
        while stack:
            r, c = stack.pop()
            group.add((r, c))
            for dr, dc in STEPS:
                if (r + dr, c + dc) in left:
                    left.remove((r + dr, c + dc))
                    stack.append((r + dr, c + dc))
        found.append(group)
    return sorted(found, key=len, reverse=True)


def main(out_dir):
    m, x, g = build(connect=False)
    start = time.time()
    rounds = cuts = 0
    fewest = 99
    while True:
        left = WALL_LIMIT - (time.time() - start)
        if left <= 0:
            print(f"UNKNOWN: wall limit after {rounds} rounds, {cuts} cuts; fewest components {fewest}", flush=True)
            return 0
        s = solver(left)
        status = s.solve(m)
        rounds += 1
        if status == cp_model.INFEASIBLE:
            print(f"INFEASIBLE after {rounds} rounds, {cuts} cuts, {time.time() - start:.1f}s", flush=True)
            return 0
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print(f"UNKNOWN: {s.status_name(status)} after {rounds} rounds, {cuts} cuts; fewest components {fewest}", flush=True)
            return 0
        shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
        groups = components(shade)
        fewest = min(fewest, len(groups))
        if rounds % 25 == 1:
            print(f"round {rounds}: {len(groups)} components, sizes {[len(a) for a in groups]}, {cuts} cuts, {time.time() - start:.0f}s", flush=True)
        if len(groups) == 1:
            break
        witness = next(iter(groups[0]))
        for group in groups[1:]:
            boundary = {
                (r + dr, c + dc)
                for r, c in group
                for dr, dc in STEPS
                if 0 <= r + dr < 9 and 0 <= c + dc < 9 and (r + dr, c + dc) not in group
            }
            m.add_bool_or(
                [g[r * 9 + c].Not() for r, c in group]
                + [g[r * 9 + c] for r, c in boundary]
                + [g[witness[0] * 9 + witness[1]].Not()]
            )
            cuts += 1

    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    print(f"FOUND after {rounds} rounds, {cuts} cuts, {time.time() - start:.1f}s", flush=True)
    broken = violations(digits, shade) + negative_errors(digits, shade)
    print(f"reader violations {broken or 'none'}", flush=True)
    print("\n".join(
        " ".join(("#" if shade[i][j] else ".") + str(digits[i][j]) for j in range(9))
        for i in range(9)
    ), flush=True)
    print("shaded total", sum(map(sum, shade)), flush=True)
    canvas = GridCanvas(9, 9, cell=64, margin=24)
    for i in range(9):
        for j in range(9):
            if shade[i][j]:
                canvas.shade_cell(i, j, "#b8b8b8")
    for br, bc in BOXES:
        box = box_of(br, bc)
        count = sum(shade[i][j] for i, j in box)
        spot = next(cell for cell in box if digits[cell[0]][cell[1]] == count)
        print(f"box r{br + 1}c{bc + 1}: count {count}, circle r{spot[0] + 1}c{spot[1] + 1}", flush=True)
        canvas.circle(*spot, color="#2471a3", width=4)
    for i in range(9):
        for j in range(9):
            canvas.digit(i, j, digits[i][j])
    canvas.box_lines(3, 3, thin=1, thick=5)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "grid-6.json").write_text(json.dumps({"digits": digits, "shaded": shade}))
    temp = out / "grid-6.tmp.png"
    canvas.image.save(temp)
    os.replace(temp, out / "grid-6.png")
    print("picture", out / "grid-6.png", flush=True)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

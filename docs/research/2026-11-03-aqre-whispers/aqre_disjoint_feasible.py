"""SCRATCH, not a finder: feasibility of digits 0-8, Aqre shading, whispers on
shaded cells, and box shaded counts that are all different.

Modes, one solve each, single worker:
  distinct  box shaded counts are a permutation of 0-8; circles sit anywhere
  centre, corner, edge  also, all nine circles sit at one position within their
            box, which makes them one disjoint set

Grid symmetry leaves only those three position classes. The d -> 8-d digit swap
does NOT preserve a circle (it changes digit, not count), so orientation stays
a variable here.
"""

import json
import os
import sys
from pathlib import Path

from connected import add_flow_connectivity
from finders.hunt.render import GridCanvas
from ortools.sat.python import cp_model
from shapes import ORTH
from sudoku_kit.cpsat import boxes, solver, sudoku_model

N = 9
TIME_LIMIT = 600.0
POSITIONS = {"centre": (1, 1), "corner": (0, 0), "edge": (0, 1)}
BOXES = [(br, bc) for br in (0, 3, 6) for bc in (0, 3, 6)]


def build(mode, distinct=True):
    m, x = sudoku_model(N, boxes(N, 3, 3))  # x is digit + 1
    g = [m.new_bool_var(f"g{i}") for i in range(N * N)]
    add_flow_connectivity(m, g)
    shaded = lambda r, c: g[r * N + c]
    for a in range(N):
        for b in range(N - 3):
            for line in (
                [shaded(a, b + k) for k in range(4)],
                [shaded(b + k, a) for k in range(4)],
            ):
                m.add_bool_or(line)
                m.add_bool_or([v.Not() for v in line])
    even_low = m.new_bool_var("even_low")
    for r in range(N):
        for c in range(N):
            low = even_low if (r + c) % 2 == 0 else even_low.Not()
            m.add(x[r, c] <= 4).only_enforce_if(shaded(r, c), low)
            m.add(x[r, c] >= 6).only_enforce_if(shaded(r, c), low.Not())
    for i in range(N * N):
        for j in ORTH[i]:
            if i < j:
                gap = m.new_int_var(0, N - 1, f"gap{i}_{j}")
                m.add_abs_equality(gap, x[i // N, i % N] - x[j // N, j % N])
                m.add(gap >= 5).only_enforce_if(g[i], g[j])
    counts = []
    for br, bc in BOXES:
        count = sum(shaded(r, c) for r in range(br, br + 3) for c in range(bc, bc + 3))
        counts.append(count)
        if mode in POSITIONS:
            dr, dc = POSITIONS[mode]
            m.add(x[br + dr, bc + dc] - 1 == count)
    if distinct:
        m.add_all_different(counts)
        m.add(sum(g) == 36)  # redundant: 0+1+...+8, posted to help the solver
    return m, x, g


def violations(digits, shade, mode):
    """Every rule a filled grid breaks, read with no solver."""
    found = []
    full = set(range(9))
    for i in range(9):
        if set(digits[i]) != full:
            found.append(f"row {i + 1} digits")
        if {digits[r][i] for r in range(9)} != full:
            found.append(f"column {i + 1} digits")
    for br, bc in BOXES:
        if {digits[r][c] for r in range(br, br + 3) for c in range(bc, bc + 3)} != full:
            found.append(f"box r{br + 1}c{bc + 1} digits")
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
    cells = {(r, c) for r in range(9) for c in range(9) if shade[r][c]}
    seen, stack = set(), [next(iter(cells))] if cells else []
    while stack:
        cell = stack.pop()
        if cell not in seen:
            seen.add(cell)
            for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                if (cell[0] + dr, cell[1] + dc) in cells:
                    stack.append((cell[0] + dr, cell[1] + dc))
    if seen != cells:
        found.append(f"shaded not connected: {len(seen)} of {len(cells)}")
    counts = [
        sum(shade[r][c] for r in range(br, br + 3) for c in range(bc, bc + 3))
        for br, bc in BOXES
    ]
    if sorted(counts) != list(range(9)):
        found.append(f"box counts {counts}")
    if mode in POSITIONS:
        dr, dc = POSITIONS[mode]
        for (br, bc), count in zip(BOXES, counts):
            if digits[br + dr][bc + dc] != count:
                found.append(f"circle in box r{br + 1}c{bc + 1}")
    return found


def controls(digits, shade, mode):
    """Each rule of the reader must fire on a grid broken in that rule."""
    swapped = [row[:] for row in digits]
    swapped[0][0], swapped[0][1] = swapped[0][1], swapped[0][0]
    assert any("digits" in v for v in violations(swapped, shade, mode)), "digits"
    blank = [[False] * 9 for _ in range(9)]
    assert any("four" in v for v in violations(digits, blank, mode)), "line"
    assert any("box counts" in v for v in violations(digits, blank, mode)), "counts"
    full = [[True] * 9 for _ in range(9)]
    assert any("whisper" in v for v in violations(digits, full, mode)), "whisper"
    apart = [[False] * 9 for _ in range(9)]
    apart[0][0] = apart[8][8] = True
    assert any("connected" in v for v in violations(digits, apart, mode)), "connect"
    if mode in POSITIONS:
        dr, dc = POSITIONS[mode]
        moved = [row[:] for row in digits]
        moved[dr][dc] = (moved[dr][dc] + 1) % 9
        assert any("circle" in v for v in violations(moved, shade, mode)), "circle"


def draw(digits, shade, spots, path):
    canvas = GridCanvas(9, 9, cell=64, margin=24)
    for r in range(9):
        for c in range(9):
            if shade[r][c]:
                canvas.shade_cell(r, c, "#b8b8b8")
    for spot in spots:
        canvas.circle(*spot, color="#c0392b", width=4)
    for r in range(9):
        for c in range(9):
            canvas.digit(r, c, digits[r][c])
    canvas.box_lines(3, 3, thin=1, thick=5)
    temp = path.with_suffix(".tmp.png")
    canvas.image.save(temp)
    os.replace(temp, path)


def solve(mode, out):
    m, x, g = build(mode)
    s = solver(TIME_LIMIT)
    status = s.solve(m)
    name = s.status_name(status)
    print(f"{mode}: status {name} in {s.wall_time:.1f}s", flush=True)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return
    digits = [[s.value(x[r, c]) - 1 for c in range(9)] for r in range(9)]
    shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
    controls(digits, shade, mode)
    print(f"{mode}: reader violations {violations(digits, shade, mode) or 'none'}", flush=True)
    spots = []
    counts = []
    for br, bc in BOXES:
        box = [(r, c) for r in range(br, br + 3) for c in range(bc, bc + 3)]
        count = sum(shade[r][c] for r, c in box)
        counts.append(count)
        spots.append(next(cell for cell in box if digits[cell[0]][cell[1]] == count))
    print(f"{mode}: box counts {counts}, shaded total {sum(counts)}", flush=True)
    print("\n".join(
        " ".join(("#" if shade[r][c] else ".") + str(digits[r][c]) for c in range(9))
        for r in range(9)
    ), flush=True)
    (out / f"grid-3-{mode}.json").write_text(
        json.dumps({"digits": digits, "shaded": shade, "counts": counts, "spots": spots})
    )
    draw(digits, shade, spots, out / f"grid-3-{mode}.png")
    print(f"{mode}: picture {out / f'grid-3-{mode}.png'}", flush=True)


if __name__ == "__main__":
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    solve("distinct", out_dir)

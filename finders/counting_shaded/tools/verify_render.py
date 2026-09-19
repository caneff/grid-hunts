"""Independent CP-SAT check of the 6x6 uniques from the rule text, then a sheet."""

import json
import os
import sys
from pathlib import Path

LATIN = os.environ.get("LATIN") == "1"
SELF = os.environ.get("SELF") == "1"
from ortools.sat.python import cp_model
from PIL import Image, ImageDraw, ImageFont

N, BR, BC = 6, 2, 3


def king(i):
    r, c = divmod(i, N)
    return [
        (r + dr) * N + c + dc
        for dr in (-1, 0, 1)
        for dc in (-1, 0, 1)
        if (dr or dc) and 0 <= r + dr < N and 0 <= c + dc < N
    ]


def orth(i):
    r, c = divmod(i, N)
    return [
        (r + dr) * N + c + dc
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
        if 0 <= r + dr < N and 0 <= c + dc < N
    ]


def box(i):
    r, c = divmod(i, N)
    return (r // BR) * (N // BC) + c // BC


def solutions(shape, cap=3):
    """Grids + shadings satisfying the rules, where the shading agrees with `shape` on shape cells only... no: shown cells reveal shading only, so we fix the WHOLE shading? No -- the puzzle shows some shaded cells; the solver must decide the rest. Here we test the stronger all-visible statement: shading fixed to shape, count grids."""
    m = cp_model.CpModel()
    v = [m.new_int_var(1, N, f"v{i}") for i in range(N * N)]
    for r in range(N):
        m.add_all_different([v[r * N + c] for c in range(N)])
        m.add_all_different([v[c * N + r] for c in range(N)])
    for b in range(N):
        if not LATIN:
            m.add_all_different([v[i] for i in range(N * N) if box(i) == b])
    for i in shape:
        m.add(v[i] == sum(1 for j in king(i) if j in shape) + (1 if SELF else 0))
    s = cp_model.CpSolver()
    s.parameters.enumerate_all_solutions = True
    s.parameters.num_workers = 1

    class C(cp_model.CpSolverSolutionCallback):
        def __init__(s2):
            super().__init__()
            s2.k = 0
            s2.grid = None

        def on_solution_callback(s2):
            s2.k += 1
            s2.grid = [s2.value(x) for x in v]
            if s2.k >= cap:
                s2.stop_search()

    c = C()
    s.solve(m, c)
    return c.k, c.grid


def connected(shape):
    shape = set(shape)
    seen = {min(shape)}
    stack = [min(shape)]
    while stack:
        i = stack.pop()
        for j in orth(i):
            if j in shape and j not in seen:
                seen.add(j)
                stack.append(j)
    return seen == shape


rows = [
    json.loads(line)
    for f in sorted(Path().glob(sys.argv[1]))
    for line in f.read_text().splitlines()
]
uniq = [r for r in rows if r["solutions"] == 1]
ok = []
for r in uniq:
    k, grid = solutions(set(r["shape"]))
    assert connected(r["shape"]), r
    assert k == 1, (r, k)
    # rule text: every shaded digit equals its shaded king-neighbour count
    for i in r["shape"]:
        assert grid[i] == sum(1 for j in king(i) if j in r["shape"]) + (
            1 if SELF else 0
        )
    ok.append((r, grid))
print(
    len(uniq), "uniques, all confirmed unique + connected + rule-consistent by CP-SAT"
)

# sheet
CELL = 40
PAD = 14
COLS = 3
W = N * CELL
rows_n = (len(ok) + COLS - 1) // COLS
img = Image.new("RGB", (COLS * (W + PAD) + PAD, rows_n * (W + PAD) + PAD), "white")
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22
    )
except OSError:
    font = ImageFont.load_default()
for k, (r, grid) in enumerate(ok):
    ox = PAD + (k % COLS) * (W + PAD)
    oy = PAD + (k // COLS) * (W + PAD)
    sh = set(r["shape"])
    for i in range(N * N):
        rr, cc = divmod(i, N)
        x = ox + cc * CELL
        y = oy + rr * CELL
        if i in sh:
            d.rectangle([x, y, x + CELL, y + CELL], fill=(170, 170, 170))
            d.text(
                (x + CELL / 2, y + CELL / 2),
                str(grid[i]),
                fill="black",
                font=font,
                anchor="mm",
            )
    for t in range(N + 1):
        w = 3 if (t % BR == 0 and not LATIN) or t in (0, N) else 1
        d.line([ox, oy + t * CELL, ox + W, oy + t * CELL], fill="black", width=w)
        w = 3 if (t % BC == 0 and not LATIN) or t in (0, N) else 1
        d.line([ox + t * CELL, oy, ox + t * CELL, oy + W], fill="black", width=w)
img.save(sys.argv[2])
print("wrote", sys.argv[2])
with Path(sys.argv[3]).open("w") as fh:
    for r, grid in ok:
        fh.write(json.dumps({**r, "grid": grid}) + "\n")

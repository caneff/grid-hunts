"""6x6 shadings with two forced cells: every shape with a grid, sudoku and Latin, rendered.
uv run --with pillow pairsheet.py 11,30 out.png"""

import sys
from pathlib import Path

from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gridenum as G
from PIL import Image, ImageDraw, ImageFont

G.geometry(6, 2, 3)
pair = tuple(int(x) for x in sys.argv[1].split(","))


def collector(g, n):
    class C(cp_model.CpSolverSolutionCallback):
        def __init__(s2):
            super().__init__()
            s2.shapes = []

        def on_solution_callback(s2):
            sh = [i for i in range(36) if s2.value(g[i])]
            s2.shapes.append((sh, {i: s2.value(n[i]) for i in sh}))

    return C()


found = []
for latin in (False, True):
    G.LATIN = latin
    for size in range(4, 25):
        m, g, n = G.build(size, force=pair, min_distinct=0)
        s = cp_model.CpSolver()
        s.parameters.num_workers = 1
        s.parameters.enumerate_all_solutions = True

        c = collector(g, n)
        s.solve(m, c)
        withgrid = [
            (sh, gv, G.count(gv, 2)) for sh, gv in c.shapes if G.count(gv, 2) >= 1
        ]
        for sh, gv, k in withgrid:
            found.append((latin, size, sh, gv, k))
        if c.shapes:
            print(
                f"{'Latin' if latin else 'sudoku'} size {size}: {len(c.shapes)} shapes, {len(withgrid)} with a grid, {sum(1 for t in withgrid if t[2] == 1)} unique"
            )
print("total with a grid:", len(found))
found.sort(key=lambda t: (t[0], t[4] != 1, t[1]))
sel = found[:8]


def solve_grid(gv, latin):
    m = cp_model.CpModel()
    v = [m.new_int_var(1, 6, f"v{i}") for i in range(36)]
    for k in range(6):
        m.add_all_different([v[k * 6 + c] for c in range(6)])
        m.add_all_different([v[c * 6 + k] for c in range(6)])
    if not latin:
        for b in range(6):
            m.add_all_different([v[i] for i in range(36) if G.BOX[i] == b])
    for i, dv in gv.items():
        m.add(v[i] == dv)
    s = cp_model.CpSolver()
    s.solve(m)
    return [s.value(x) for x in v]


if sel:
    CELL = 44
    PAD = 14
    W = 6 * CELL
    cols = min(4, len(sel))
    rows = (len(sel) + cols - 1) // cols
    img = Image.new("RGB", (cols * (W + PAD) + PAD, rows * (W + PAD) + PAD), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22
    )
    for k, (latin, size, sh, gv, cnt) in enumerate(sel):
        grid = solve_grid(gv, latin)
        ox = PAD + (k % cols) * (W + PAD)
        oy = PAD + (k // cols) * (W + PAD)
        print(
            f"#{k + 1}: {'Latin' if latin else 'sudoku'} size {size} {'UNIQUE' if cnt == 1 else '2+ grids'} shape {sh}"
        )
        for i in range(36):
            r, c = divmod(i, 6)
            x = ox + c * CELL
            y = oy + r * CELL
            if i in sh:
                d.rectangle([x, y, x + CELL, y + CELL], fill=(170, 170, 170))
            d.text(
                (x + CELL / 2, y + CELL / 2),
                str(grid[i]),
                fill="black",
                font=font,
                anchor="mm",
            )
        for t in range(7):
            wr = 3 if (t in (0, 6) or (not latin and t % 2 == 0)) else 1
            wc = 3 if (t in (0, 6) or (not latin and t % 3 == 0)) else 1
            d.line([ox, oy + t * CELL, ox + W, oy + t * CELL], fill="black", width=wr)
            d.line([ox + t * CELL, oy, ox + t * CELL, oy + W], fill="black", width=wc)
    img.save(sys.argv[2])

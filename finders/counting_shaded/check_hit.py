"""Independently verify an all-visible shaded cell shape and render it.

    uv run --with pillow finders/counting_shaded/check_hit.py hits.jsonl LINE out.png puzzle.png

Checks, with no code shared with shapes.py: each shaded cell's digit equals its
shaded-neighbour count, some shaded cell shows 8, and CP-SAT finds exactly one sudoku
with those givens. Writes the solved grid (shaded cells circled) and the puzzle view
(shaded cells circled with their digits, other cells blank).
"""

import json
import sys
from pathlib import Path

from ortools.sat.python import cp_model
from PIL import Image, ImageDraw, ImageFont

CELL, MARGIN = 72, 24
SIDE = 9 * CELL + 2 * MARGIN
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def draw(digits, shaded, show_all, path):
    img = Image.new("RGB", (SIDE, SIDE), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, int(CELL * 0.5))
    for r in range(9):
        for c in range(9):
            cx, cy = MARGIN + c * CELL + CELL / 2, MARGIN + r * CELL + CELL / 2
            if (r, c) in shaded:
                rad = CELL * 0.38
                d.ellipse(
                    (cx - rad, cy - rad, cx + rad, cy + rad), outline="black", width=3
                )
            if show_all or (r, c) in shaded:
                d.text(
                    (cx, cy), str(digits[r][c]), fill="black", font=font, anchor="mm"
                )
    for i in range(10):
        w = 5 if i % 3 == 0 else 1
        p = MARGIN + i * CELL
        d.line((MARGIN, p, SIDE - MARGIN, p), fill="black", width=w)
        d.line((p, MARGIN, p, SIDE - MARGIN), fill="black", width=w)
    img.save(path)


def main():
    rec = json.loads(Path(sys.argv[1]).read_text().splitlines()[int(sys.argv[2])])
    shaded = {divmod(i, 9) for i in rec["shape"]}
    given = {}
    for r, c in shaded:
        n = sum(
            (r + a, c + b) in shaded for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b
        )
        given[r, c] = n
    assert all(1 <= n <= 8 for n in given.values()), "a shaded cell count outside 1-8"
    assert 8 in given.values(), "no shaded cell shows 8"

    m = cp_model.CpModel()
    x = {(r, c): m.new_int_var(1, 9, f"x{r}{c}") for r in range(9) for c in range(9)}
    for i in range(9):
        m.add_all_different(x[i, c] for c in range(9))
        m.add_all_different(x[r, i] for r in range(9))
    for br in (0, 3, 6):
        for bc in (0, 3, 6):
            m.add_all_different(x[br + a, bc + b] for a in range(3) for b in range(3))
    for cell, n in given.items():
        m.add(x[cell] == n)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.enumerate_all_solutions = True
    sols = []

    class Collect(cp_model.CpSolverSolutionCallback):
        def on_solution_callback(self):
            sols.append([[self.value(x[r, c]) for c in range(9)] for r in range(9)])
            if len(sols) >= 2:
                self.stop_search()

    s.solve(m, Collect())
    print(
        f"shaded cells={len(shaded)} givens={len(given)} eights={sum(v == 8 for v in given.values())} "
        f"solutions_found={len(sols)} (stops at 2)"
    )
    assert len(sols) == 1, "not unique"
    for row in sols[0]:
        print(
            " ".join(
                f"{v}{'*' if (r, c) in shaded else ' '}"
                for r, c, v in ((sols[0].index(row), c, v) for c, v in enumerate(row))
            )
        )
    draw(sols[0], shaded, True, sys.argv[3])
    draw(sols[0], shaded, False, sys.argv[4])
    print("UNIQUE OK")


if __name__ == "__main__":
    main()

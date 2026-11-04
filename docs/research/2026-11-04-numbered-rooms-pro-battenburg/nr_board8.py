"""SCRATCH: the sixth board plus mark r3c4, negative rule on: what is forced.

All his digits and colours are held, pencil marks left out. Writes each cell's digits
and the status of each uncoloured cell, and each outside cell's digits, to OUT_JSON.
Grids are counted to a cap and re-read by the reader. One worker; a timeout raises.

Usage: nr_board8.py OUT_JSON
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nr_board7 as B
from nr import CLUES, build, clue_name, is_sudoku, line_cells, marks, outside, show, targets
from nr_board7 import COLOURS, DIGITS, ENTERED, RING, can, cell, model, run
from sudoku_kit.cpsat import SOLVED

B.BOARD = frozenset(B.BOARD | {(2, 3)})
EVERYTHING = ENTERED + COLOURS
CAP = 200


def outside_options(clue):
    cells = line_cells(clue)
    pr, pc = cells[0]
    options = []
    for v in range(1, 10):
        def post(m, x, t, v=v):
            _ = t
            for i, (r, c) in enumerate(cells):
                lit = m.NewBoolVar("pointer")
                m.Add(x[pr, pc] == i + 1).OnlyEnforceIf(lit)
                m.Add(x[pr, pc] != i + 1).OnlyEnforceIf(lit.Not())
                m.Add(x[r, c] == v).OnlyEnforceIf(lit)
        if can(EVERYTHING, True, post):
            options.append(v)
    return options


def main(out):
    found = []
    while len(found) < CAP:
        m, x, b, _ = model(EVERYTHING, True)
        for grid in found:
            m.AddBoolOr([b[r, c, grid[r][c]].Not() for r in range(9) for c in range(9)])
        s, status = run(m)
        if status not in SOLVED:
            break
        grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
        assert is_sudoku(grid) and marks(grid) == B.BOARD
        ring = outside(grid)
        assert all(ring[k] == v for k, v in RING.items())
        tt = targets(grid)
        assert all((cell(n) in tt) == bool(w) for _, n, w in COLOURS)
        assert all(grid[k[0]][k[1]] == v for k, v in DIGITS.items())
        found.append(grid)
    capped = len(found) == CAP
    print(f"grids: {len(found)}{' (capped)' if capped else ''}")
    print(show(found[0]))

    options = {}
    for r in range(9):
        row = []
        for c in range(9):
            allowed = [
                d
                for d in range(1, 10)
                if can(EVERYTHING, True, lambda m, x, t, r=r, c=c, d=d: m.Add(x[r, c] == d))
            ]
            options[f"r{r + 1}c{c + 1}"] = allowed
            row.append("".join(map(str, allowed)) if len(allowed) < 9 else ".")
        print(f"r{r + 1}", " ".join(f"{v:>9}" for v in row), flush=True)

    coloured = {cell(n) for _, n, _ in COLOURS}
    pink, green, open_cells = [], [], []
    for r in range(9):
        for c in range(9):
            if (r, c) in coloured:
                continue
            yes = can(EVERYTHING, True, lambda m, x, t, r=r, c=c: m.Add(t[r, c] == 1))
            no = can(EVERYTHING, True, lambda m, x, t, r=r, c=c: m.Add(t[r, c] == 0))
            name = f"r{r + 1}c{c + 1}"
            (pink if yes and not no else green if no and not yes else open_cells).append(name)
    print("uncoloured forced pink:", pink)
    print("uncoloured forced green:", green)
    print("uncoloured open:", open_cells)

    ring_options = {}
    for clue in CLUES:
        if clue in RING:
            continue
        ring_options[clue_name(clue)] = outside_options(clue)
    print("outside:", {k: v for k, v in ring_options.items() if len(v) <= 4}, flush=True)

    Path(out).write_text(
        json.dumps(
            {
                "options": options,
                "pink": pink,
                "green": green,
                "open": open_cells,
                "outside": ring_options,
                "grids": len(found),
                "capped": capped,
            }
        )
    )
    _ = build


if __name__ == "__main__":
    main(sys.argv[1])

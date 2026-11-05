"""Every matching end-clue pair a board allows, with its digits, alone and together.

Negative rule on. For each line, the digits its two end clues can share; then for each two
and three lines, every digit combination that one grid allows. Every answer comes from the
repo's full model, with the grid re-read by the reader. One worker; a timeout raises.

Usage: nr_pairs_detail.py BOARD_JSON LINE [LINE ...]   e.g. r9 c5 c8
"""

import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, line_cells, marks, outside
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver


def pair(line):
    i = int(line[1:]) - 1
    return (("L", i), ("R", i)) if line[0] == "r" else (("T", i), ("B", i))


def nm(k):
    return f"r{k[0] + 1}c{k[1] + 1}"


def grid_for(board, wants):
    m, x, b, _ = build(board, {})
    for line, d in wants:
        for clue in pair(line):
            cells = line_cells(clue)
            first = cells[0]
            lits = []
            for i, target in enumerate(cells):
                lit = m.NewBoolVar("hit")
                m.AddBoolAnd([b[first[0], first[1], i + 1], b[target[0], target[1], d]]).OnlyEnforceIf(lit)
                m.AddBoolOr([b[first[0], first[1], i + 1].Not(), b[target[0], target[1], d].Not()]).OnlyEnforceIf(lit.Not())
                lits.append(lit)
            m.AddBoolOr(lits)
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError(str(wants))
    if status not in SOLVED:
        return None
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid) and marks(grid) == board
    ring = outside(grid)
    for line, d in wants:
        u, v = pair(line)
        assert ring[u] == ring[v] == d
    return grid


def reads(grid, line):
    cells = line_cells(pair(line)[0])
    return nm(cells[grid[cells[0][0]][cells[0][1]] - 1])


def main(path, *lines):
    board = frozenset((int(n[1]) - 1, int(n[3]) - 1) for n in json.loads(Path(path).read_text())["marks"])
    options = {}
    for line in lines:
        options[line] = []
        for d in range(1, 10):
            grid = grid_for(board, [(line, d)])
            if grid:
                options[line].append(d)
                print(f"{line} = {d}: both read {reads(grid, line)}", flush=True)
    for size in (2, 3):
        for group in itertools.combinations(lines, size):
            combos = []
            for values in itertools.product(*(options[line] for line in group)):
                if grid_for(board, list(zip(group, values, strict=True))):
                    combos.append(" ".join(f"{line}={d}" for line, d in zip(group, values, strict=True)))
            print(" + ".join(group), "together:", combos or "never", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])

"""Which one-mark variants allow two lines with matching end clues in the same grid.

Reads nr_pair_variants.py's record. For each variant and each two of its pair lines, asks the
repo's full model, negative rule on, for one grid where both lines' end clues match; the grid
is re-read by the reader. One worker; a timeout raises.

Usage: nr_pair_two.py BOARD_JSON VARIANTS_JSONL
"""

import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, marks, outside
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver


def cell(name):
    return int(name[1]) - 1, int(name[3]) - 1


def pair(line):
    i = int(line[1:]) - 1
    return (("L", i), ("R", i)) if line[0] == "r" else (("T", i), ("B", i))


def ends(line):
    i = int(line[1:]) - 1
    return ((i, 0), (i, 8)) if line[0] == "r" else ((0, i), (8, i))


def main(path, variants):
    base = frozenset(cell(n) for n in json.loads(Path(path).read_text())["marks"])
    for row in map(json.loads, Path(variants).read_text().splitlines()):
        label, lines = row["variant"], sorted(row["lines"])
        if len(lines) < 2:
            continue
        kind, name = label.split()[0], label.split()[-1]
        board = base if kind == "as" else base - {cell(name)} if kind == "remove" else base | {cell(name)}
        both = []
        for a, b in itertools.combinations(lines, 2):
            m, x, _, _ = build(board, {})
            for line in (a, b):
                p, q = ends(line)
                m.Add(x[p] + x[q] == 10)
            s = solver(120.0)
            status = s.Solve(m)
            if status == UNKNOWN:
                raise TimeoutError(f"{label} {a} {b}")
            if status not in SOLVED:
                continue
            grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
            assert is_sudoku(grid) and marks(grid) == board
            ring = outside(grid)
            values = []
            for line in (a, b):
                u, v = pair(line)
                assert ring[u] == ring[v]
                values.append(f"{line}={ring[u]}")
            both.append(" + ".join(values))
        print(label, "|", both if both else "no two at once", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])

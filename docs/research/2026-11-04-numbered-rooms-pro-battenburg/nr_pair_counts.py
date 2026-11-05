"""Exact solutions left on a board for each choice of matching end-clue pairs.

Negative rule on. Enumerates the board's borders, keeps those where every named line's ends
sum to 10 (so its two clues read one cell), finds that cell, and counts fillings with each
chosen digit pinned there, using count_fills.c. Sums over borders.

Usage: nr_pair_counts.py BOARD_JSON COUNT_FILLS LINES DIGITS [DIGITS ...]
  LINES like r9,c5,c8 and each DIGITS like 7,2,1, one digit per line.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr_full_targets_edges import BORDER, model
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver


class Keep(cp_model.CpSolverSolutionCallback):
    def __init__(self, b):
        super().__init__()
        self.b, self.rows = b, []

    def on_solution_callback(self):
        self.rows.append({k: next(d for d in range(1, 10) if self.Value(self.b[k, d])) for k in BORDER})


def ends(line):
    i = int(line[1:]) - 1
    return ((i, 0), (i, 8)) if line[0] == "r" else ((0, i), (8, i))


def target(border, line):
    """The cell both end clues read, when the ends sum to 10."""
    i = int(line[1:]) - 1
    a, z = ends(line)
    if border[a] + border[z] != 10:
        return None
    pos = border[a] - 1
    return (i, pos) if line[0] == "r" else (pos, i)


def main(path, binary, line_text, *choices):
    board = frozenset((int(n[1]) - 1, int(n[3]) - 1) for n in json.loads(Path(path).read_text())["marks"])
    m, b = model(board, True)
    s = solver(120.0)
    s.parameters.enumerate_all_solutions = True
    s.parameters.num_workers = 1
    keep = Keep(b)
    assert s.StatusName(s.Solve(m, keep)) == "OPTIMAL"
    lines = line_text.split(",")
    for choice in choices:
        digits = [int(d) for d in choice.split(",")]
        total = 0
        for border in keep.rows:
            cells = [target(border, line) for line in lines]
            if None in cells:
                continue
            pins = []
            ok = True
            for (r, c), d in zip(cells, digits, strict=True):
                if (r, c) in border:
                    ok = ok and border[(r, c)] == d
                else:
                    pins.append(f"{r + 1}{c + 1}{d}")
            if not ok:
                continue
            text = "".join(str(border[k]) for k in BORDER)
            done = subprocess.run([binary, *pins], input=text + "\n", capture_output=True, text=True, check=True)
            total += int(done.stdout.split()[1])
        print(" ".join(f"{line}={d}" for line, d in zip(lines, digits, strict=True)), total, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])

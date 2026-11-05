"""SCRATCH: check the 32 borders and the fill counts for the 36-target grid's marks.

1. The repo's full model with those 13 marks and the negative rule, with every listed
   border forbidden, must be infeasible, so the border-only enumeration missed nothing.
2. Each border pinned in the full model: a completion is re-read by the reader, and a
   border with no completion must have fill count 0.
3. Each border's fill count is compared with a CP-SAT count capped at CAP.

Usage: nr_full_targets_check.py COUNTS_FILE
One worker; a timeout raises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, marks
from nr_full_targets_edges import BOARD, BORDER
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

CAP = 30


def run(m):
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    return s, status in SOLVED


def main(path):
    counts = {}
    for line in Path(path).read_text().split("\n"):
        if line:
            text, count = line.split()
            counts[text] = int(count)
    m, x, b, _ = build(BOARD, {})
    for text in counts:
        m.AddBoolOr([b[r, c, int(d)].Not() for (r, c), d in zip(BORDER, text, strict=True)])
    print("full model with all borders forbidden feasible:", run(m)[1], flush=True)
    for text, count in counts.items():
        found = []
        while len(found) < CAP:
            m, x, b, _ = build(BOARD, {})
            for (r, c), d in zip(BORDER, text, strict=True):
                m.Add(x[r, c] == int(d))
            for grid in found:
                m.AddBoolOr([b[r, c, grid[r][c]].Not() for r in range(9) for c in range(9)])
            s, ok = run(m)
            if not ok:
                break
            grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
            assert is_sudoku(grid) and marks(grid) == BOARD
            found.append(grid)
        assert len(found) == min(count, CAP), (text, count, len(found))
    print("borders", len(counts), "with fills", sum(v > 0 for v in counts.values()))
    print("total", sum(counts.values()), "min", min(counts.values()), "max", max(counts.values()))


if __name__ == "__main__":
    main(sys.argv[1])

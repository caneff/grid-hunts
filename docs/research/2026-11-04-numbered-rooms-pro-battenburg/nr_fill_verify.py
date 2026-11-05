"""SCRATCH: cross-check fill_climb's winners. Re-reads each grid as a sudoku, counts its
border's fillings with count_fills.c, and lists the forced inner cells.

Usage: nr_fill_verify.py COUNT_FILLS_BINARY
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import is_sudoku
from nr_full_targets_edges import BORDER

WINNERS = {
    "fewest fills": "213794856 579628431 468513729 145872693 932456178 786139542 827341965 351967284 694285317",
    "most forced": "321945768 587263914 964781352 132678549 475392186 896514237 219856473 758439621 643127895",
}


def main(binary):
    for label, rows in WINNERS.items():
        grid = [[int(d) for d in row] for row in rows.split()]
        assert is_sudoku(grid)
        border = "".join(str(grid[r][c]) for r, c in BORDER)
        done = subprocess.run([binary], input=border + "\n", capture_output=True, text=True, check=True)
        count = done.stdout.split()[1]
        masks = [int(v) for v in done.stderr.split()[1:]]
        cells = [(r, c) for r in range(1, 8) for c in range(1, 8)]
        forced = {}
        for (r, c), mask in zip(cells, masks, strict=True):
            options = [d for d in range(1, 10) if mask >> d & 1]
            assert grid[r][c] in options
            if len(options) == 1:
                forced[f"r{r + 1}c{c + 1}"] = options[0]
        print(label, "fills", count, "forced", forced)


if __name__ == "__main__":
    main(sys.argv[1])

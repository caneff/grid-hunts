"""Run nr_verify_sat.py on each hit a nr_min_outside.py run printed, with the given clues added.

Usage: nr_verify_hits.py RUN_OUTPUT GIVENS   e.g. GIVENS "L9=7,R9=7"
"""

import ast
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main(path, givens):
    for line in Path(path).read_text().splitlines():
        if not line[:1].isdigit() or "grids alone" not in line:
            continue
        head, grid = line.split(" grids alone ")
        clues = ast.literal_eval(head.split(" ", 1)[1])
        rows = grid.split(" ", 1)[1].split()
        done = subprocess.run(
            [sys.executable, str(HERE / "nr_verify_sat.py"), "/".join(rows), ",".join([givens, *clues])],
            capture_output=True,
            text=True,
        )
        print(",".join(clues), done.stdout.split()[-1], flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])

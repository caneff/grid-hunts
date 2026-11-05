"""SCRATCH: which digits an outside cell can hold on a board, on the repo's full model.

No outside digit is pinned beyond the JSON's. Each hit is re-read by the reader.

Usage: nr_outside_options.py BOARD_JSON [negative] CLUE [CLUE ...]   e.g. B9 R9
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import outside
from nr_check import Board


def main(path, *args):
    negative = "negative" in args
    data = json.loads(Path(path).read_text())
    for name in args:
        if name == "negative":
            continue
        key = (name[0], int(name[1:]) - 1)
        allowed = []
        for d in range(1, 10):
            board = Board({**data, "outside": {**data.get("outside", {}), name: d}}, negative)
            grid = board.solve(board.items)
            if grid:
                assert outside(grid)[key] == d
                allowed.append(d)
        print(name, allowed, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])

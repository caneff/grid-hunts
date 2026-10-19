"""The halver + lockout-line hunt (spec #52, #56): add lockout lines to an
empty 9x9, no givens and no given halvers, until it has exactly one
(digits, halvers) solution.

The loop, its ranking, `verify`, `summary` and the CLI are the shared
target-grid hunt (`finders/halver/halver_hunt.py`, whose docstring states
them); this module gives it the lockout line type and the empty board.
`verify` re-reads a hit with `brute.py`, the C backtracking search. `record`
writes the line table, the solution (digits and halvers) and a SudokuMaker
link (`sudoku_kit.link_codec.encode_link`) of an empty 9x9 with the hit's
lines as lockout lines (type 407) with `"solverIgnored": true`, so
SudokuMaker, which knows nothing about halvers, does not mark the answer
wrong. Nothing else is entered.

    uv run finders/halver_lockout/hunt.py --out DIR --seeds 0:3
    uv run finders/halver_lockout/hunt.py verify DIR
    uv run finders/halver_lockout/hunt.py summary DIR
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))

# isort: split
import brute
import candidates
import halver_hunt
import rules
from halver_hunt import BOX, Hit, N, TargetLoopFinder, summary
from protocol import Empty, Verdict

__all__ = [
    "DEFAULTS",
    "Empty",
    "HalverLockoutFinder",
    "Hit",
    "Verdict",
    "link_doc",
    "main",
    "summary",
]

DEFAULTS = {
    "max_cells": 8,
    "pool": 20,
    "time_limit": 30.0,
    "max_lines": 40,
    "max_seconds": 600.0,
    "verify_seconds": 600.0,
}


def link_doc(added):
    """An empty 9x9 document with `added` as its lockout lines, left out of
    SudokuMaker's own checking."""
    bh, bw = BOX
    regions = [(r // bh) * (N // bw) + c // bw for r in range(N) for c in range(N)]
    paths = [[r * N + c for r, c in candidates.path_of(line)] for line in added]
    return {
        "formatVersion": "1.6.0",
        "puzzle": {
            "name": "",
            "author": "",
            "cells": [{} for _ in range(N * N)],
            "constraints": [
                {"type": 0},
                {"type": 1, "regions": regions},
                {"type": rules.LOCKOUT_LINE, "solverIgnored": True, "lines": paths},
            ],
        },
    }


class HalverLockoutFinder(TargetLoopFinder):
    """The lockout hunt's finder, from the empty board."""

    rules, candidates, brute = rules, candidates, brute
    end = "diamond"

    def link_doc(self, added):
        return link_doc(added)


def main(argv):
    return halver_hunt.main(HalverLockoutFinder, argv, DEFAULTS)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

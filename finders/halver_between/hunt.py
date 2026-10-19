"""The halver + between-line hunt (spec #39, #41): add between lines to Chris's
board until it has exactly one (digits, halvers) solution.

The loop, its ranking, `verify`, `summary` and the CLI are the shared
target-grid hunt (`finders/halver/halver_hunt.py`, whose docstring states
them); this module gives it the between line type, Chris's board as the
start, and the link. `verify` re-reads a hit with `brute.py`. `record`
writes the line table and a SudokuMaker link
(`sudoku_kit.link_codec.encode_link`): Chris's lines plus the added ones, in
his line style, with every entered digit, colour and pencil mark cleared.

    uv run finders/halver_between/hunt.py --out DIR --seeds 0:3
    uv run finders/halver_between/hunt.py verify DIR
    uv run finders/halver_between/hunt.py summary DIR
"""

import copy
import json
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
from halver_hunt import Hit, N, TargetLoopFinder
from protocol import Empty, Verdict

__all__ = [
    "BOARD",
    "BOARD_DOC",
    "DEFAULTS",
    "Empty",
    "HalverBetweenFinder",
    "Hit",
    "Verdict",
    "link_doc",
    "main",
]

BOARD_DOC = json.loads((HERE / "board.json").read_text())
BOARD = rules.lines_from_doc(BOARD_DOC)
DEFAULTS = {
    "max_cells": 8,
    "pool": 20,
    "time_limit": 30.0,
    "max_lines": 40,
    "max_seconds": 120.0,
    "verify_seconds": 600.0,
}


def link_doc(added):
    """Chris's document with `added` drawn as more between lines in his line's
    style, and every cell's entered digits, colours and pencil marks cleared."""
    doc = copy.deepcopy(BOARD_DOC)
    doc["puzzle"]["cells"] = [{} for _ in doc["puzzle"]["cells"]]
    (group,) = [
        c for c in doc["puzzle"]["constraints"] if c.get("type") == rules.BETWEEN_LINE
    ]
    for line in added:
        group["lines"].append([r * N + c for r, c in candidates.path_of(line)])
    return doc


class HalverBetweenFinder(TargetLoopFinder):
    """The between hunt's finder, from Chris's board."""

    rules, candidates, brute = rules, candidates, brute
    board = tuple(BOARD)
    end = "circle"

    link_doc = staticmethod(link_doc)


def main(argv):
    return halver_hunt.main(HalverBetweenFinder, argv, DEFAULTS)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

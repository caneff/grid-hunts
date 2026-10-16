"""A SudokuMaker link becomes a solver setup with no checkout beside this
repo (#750): the link is decoded by the sudoku-kit library, and nothing is
shelled out to on the way.

The link is built here from a document with two region sum lines (type 404)
and two givens, so the expected setup is read off the document by hand.

    uv run finders/galaxy-copycat/test_setup_from_link.py
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import copycat_rsl_solver
from sudoku_kit.link_codec import encode_link

cells = [{} for _ in range(81)]
cells[0] = {"given": True, "value": 5}
cells[40] = {"given": True, "value": 9}
cells[80] = {"value": 3}  # entered, not given
DOC = {
    "formatVersion": 5,
    "puzzle": {
        "cells": cells,
        "constraints": [
            {"type": 404, "lines": [[0, 1, 2], [9, 18]]},
            {"type": 7, "lines": [[3, 4]]},
            {"type": 404, "lines": [[80, 79]]},
        ],
    },
}


def no_shell(*args, **kwargs):
    # The command line holds the link, so it stays out of the message.
    raise AssertionError("setup_from_link shelled out")


subprocess.run = no_shell
setup = copycat_rsl_solver.setup_from_link(encode_link(DOC))
assert setup == {
    "lines": {
        "L1": ["r1c1", "r1c2", "r1c3"],
        "L2": ["r2c1", "r3c1"],
        "L3": ["r9c9", "r9c8"],
    },
    "givens": {"r1c1": 5, "r5c5": 9},
}, setup
print("test_setup_from_link.py: ok")

"""Pins `minimizer.strip`: it removes givens while the puzzle stays unique and keeps the ones it must."""

import sys
from pathlib import Path

from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_checks import check, finish
from minimizer import strip
from sudoku_kit.uniqueness import check_uniqueness

SOLUTION = {(0, 0): 1, (0, 1): 2, (1, 0): 2, (1, 1): 1}
CELLS = list(SOLUTION)


def build_model(givens):
    m = cp_model.CpModel()
    x = {c: m.NewIntVar(1, 2, f"x{c}") for c in CELLS}
    m.Add(x[(0, 0)] != x[(0, 1)])
    m.Add(x[(1, 0)] != x[(1, 1)])
    m.Add(x[(0, 0)] != x[(1, 0)])
    m.Add(x[(0, 1)] != x[(1, 1)])
    for c, v in givens.items():
        m.Add(x[c] == v)
    return m, x


def is_unique(givens):
    m, x = build_model(givens)
    return check_uniqueness(m, [x[c] for c in CELLS]).unique


check("the fully given puzzle is unique (sanity)", is_unique(SOLUTION))

stripped = strip(SOLUTION, keep=set(), test=is_unique)
check("at least one given was removed", len(stripped) < len(SOLUTION))
check("the stripped puzzle is still unique", is_unique(stripped))
check(
    "every remaining given is a real given, not an invented value",
    set(stripped.items()) <= set(SOLUTION.items()),
)
check(
    "stripping this 2x2 Latin square reaches its true minimum: one clue",
    len(stripped) == 1,
)

kept = strip(SOLUTION, keep={(0, 0)}, test=is_unique)
check("a kept item survives stripping", (0, 0) in kept)

finish()

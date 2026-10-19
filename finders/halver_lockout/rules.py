"""The halver + lockout-line rule check (spec #52): the lockout line on the
shared halver layer (`finders/halver/halver_rules.py`), which holds the board
model, its five-status uniqueness check, the per-mark check of a forced
deduction and cell naming. This module re-exports those names, so a caller
of the lockout check reads them all from here.

A lockout line's ends are its diamonds. Their values differ by at least
`GAP` (4), and every body cell's value is strictly below the smaller diamond
or strictly above the larger one: never between them, never equal to either.
Values are real values, so a halved 7 is 3.5; the model compares doubled
values, where the gap is 2 * `GAP`. The gap is 4 on every line of a 9x9
board. `gap` is a parameter only so a 4x4 test board, whose values never
differ by 4, can run at SudokuMaker's own 4x4 gap of 2.

`RuleModel(lines)` builds the board with each line's lockout rule on top,
posted by `post_lockout`. `line_holds` reads one line against one solution
in plain Python, with no solver. `load_lines` and `lines_from_doc` read the
lockout lines (SudokuMaker constraint type 407) of a decoded document.
"""

import json
import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "halver"))

# isort: split
import halver_rules
from halver_rules import (
    HalverModel,
    Line,
    MarkCheck,
    RuleCheck,
    Solution,
    cell_name,
    line_name,
    mark_name,
    parse_cell,
)

__all__ = [
    "GAP",
    "LOCKOUT_LINE",
    "Line",
    "MarkCheck",
    "RuleCheck",
    "RuleModel",
    "Solution",
    "cell_name",
    "line_holds",
    "line_name",
    "lines_from_doc",
    "load_lines",
    "mark_name",
    "parse_cell",
    "post_lockout",
]

LOCKOUT_LINE = 407  # SudokuMaker's constraint type for a lockout line
GAP = 4  # the least difference between a line's two diamonds' values


def line_holds(solution, line, gap=GAP):
    """True when the diamonds differ by at least `gap` and every body cell's
    value is strictly outside them."""
    lo, hi = sorted((solution.doubled(line.a), solution.doubled(line.b)))
    if hi - lo < 2 * gap:
        return False
    return all(not lo <= solution.doubled(cell) <= hi for cell in line.body)


def post_lockout(m, dv, line, index, gap=GAP):
    """Post one lockout line on the doubled values: the diamonds at least
    2 * `gap` apart, each body cell below the smaller or above the larger."""
    if not line.body:
        raise ValueError(f"line {line_name(line)} has no body cell")
    if line.a == line.b:
        raise ValueError(f"line {line_name(line)} has one cell as both diamonds")
    a_larger = m.NewBoolVar(f"big{index}")
    m.Add(dv[line.a] - dv[line.b] >= 2 * gap).OnlyEnforceIf(a_larger)
    m.Add(dv[line.b] - dv[line.a] >= 2 * gap).OnlyEnforceIf(a_larger.Not())
    for k, cell in enumerate(line.body):
        below = m.NewBoolVar(f"below{index}_{k}")
        small, large = (line.b, line.a), (line.a, line.b)
        for larger, (lo, hi) in ((a_larger, small), (a_larger.Not(), large)):
            m.Add(dv[cell] < dv[lo]).OnlyEnforceIf([below, larger])
            m.Add(dv[cell] > dv[hi]).OnlyEnforceIf([below.Not(), larger])


class RuleModel(HalverModel):
    """The halver board with lockout lines. A 9x9 board with 3x3 boxes and
    a gap of 4 unless told otherwise."""

    def __init__(self, lines, n=9, box=(3, 3), gap=GAP):
        super().__init__(partial(post_lockout, gap=gap), lines, n, box)


def load_lines(path):
    """The lockout lines of a decoded SudokuMaker document file, in its
    order."""
    try:
        return lines_from_doc(json.loads(path.read_text()))
    except ValueError as error:
        raise ValueError(f"{path}: {error}") from error


def lines_from_doc(doc):
    """The lockout lines of a decoded SudokuMaker document, in its order."""
    return halver_rules.lines_from_doc(doc, LOCKOUT_LINE, "lockout")

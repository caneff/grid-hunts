"""The halver + between-line rule check (spec #39): the between line on the
shared halver layer (`finders/halver/halver_rules.py`, spec #52), which holds
the board model, its five-status uniqueness check, the per-mark check of a
forced deduction and cell naming. This module re-exports those names, so a
caller of the between check reads them all from here.

`RuleModel(lines)` builds the board with each line's between rule on top,
posted by `post_between`. `line_holds` reads one line against one solution in
plain Python, with no solver, so a caller can test a candidate line against a
known grid cheaply. `load_lines` and `lines_from_doc` read the between lines
of a decoded SudokuMaker document.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "halver"))

# isort: split
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
    "BETWEEN_LINE",
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
    "post_between",
]

BETWEEN_LINE = 403  # SudokuMaker's constraint type for a between line


def line_holds(solution, line):
    """True when every body cell's value is strictly between the circles'."""
    lo, hi = sorted((solution.doubled(line.a), solution.doubled(line.b)))
    return all(lo < solution.doubled(cell) < hi for cell in line.body)


def post_between(m, dv, line, index):
    """Post one between line: each body cell strictly between the circles'
    doubled values, whichever circle is larger. Equal circles leave no body
    value possible."""
    if not line.body:
        raise ValueError(f"line {line_name(line)} has no body cell")
    if line.a == line.b:
        raise ValueError(f"line {line_name(line)} has one cell as both circles")
    a_larger = m.NewBoolVar(f"big{index}")
    m.Add(dv[line.a] > dv[line.b]).OnlyEnforceIf(a_larger)
    m.Add(dv[line.a] < dv[line.b]).OnlyEnforceIf(a_larger.Not())
    for cell in line.body:
        m.Add(dv[cell] < dv[line.a]).OnlyEnforceIf(a_larger)
        m.Add(dv[cell] > dv[line.b]).OnlyEnforceIf(a_larger)
        m.Add(dv[cell] > dv[line.a]).OnlyEnforceIf(a_larger.Not())
        m.Add(dv[cell] < dv[line.b]).OnlyEnforceIf(a_larger.Not())


class RuleModel(HalverModel):
    """The halver board with between lines. A 9x9 board with 3x3 boxes
    unless told otherwise."""

    def __init__(self, lines, n=9, box=(3, 3)):
        super().__init__(post_between, lines, n, box)


def load_lines(path):
    """The between lines of a decoded SudokuMaker document file, in its order."""
    try:
        return lines_from_doc(json.loads(path.read_text()))
    except ValueError as error:
        raise ValueError(f"{path}: {error}") from error


def lines_from_doc(doc):
    """The between lines of a decoded SudokuMaker document, in its order."""
    n = round(len(doc["puzzle"]["cells"]) ** 0.5)
    groups = [
        c["lines"]
        for c in doc["puzzle"]["constraints"]
        if c.get("type") == BETWEEN_LINE
    ]
    if not groups:
        raise ValueError(f"no between lines (constraint type {BETWEEN_LINE})")
    lines = []
    for group in groups:
        for path_cells in group:
            cells = [divmod(i, n) for i in path_cells]
            lines.append(Line(cells[0], tuple(cells[1:-1]), cells[-1]))
    return lines

"""The halver + between-line rule check (spec #39): a CP-SAT model of the two
rules, its five-status uniqueness check, and the per-mark check of a forced
deduction.

`RuleModel(lines)` builds the board once: digits, one halver boolean per cell
and a doubled value per cell, with each line's between rule on top.
`add_line` puts one more line on the same model, so a caller that adds lines
one at a time never rebuilds the board. `sample` draws one solution, steered
by random digit hints, and `hint` makes a given solution the one a later
`check` tries first. `check` decides uniqueness over the
digits and the halvers together and leaves the model alone; `mark_holds`
solves once with the mark negated, so a mark holds exactly when that solve is
infeasible. Neither ever reads a timeout as unique or as held.

`line_holds` reads one line against one solution in plain Python, with no
solver, so a caller can test a candidate line against a known grid cheaply.

Cells are (row, column) from 0; `cell_name` and `parse_cell` convert to and
from the rNcM form the spec and the report use.
"""

import json
from typing import NamedTuple

from ortools.sat.python import cp_model
from sudoku_kit import cpsat
from sudoku_kit.uniqueness import check_uniqueness

BETWEEN_LINE = 403  # SudokuMaker's constraint type for a between line


class Line(NamedTuple):
    """A between line: circle `a`, the `body` cells in path order, circle `b`."""

    a: tuple
    body: tuple
    b: tuple


class Solution(NamedTuple):
    """A full answer: `digits` row by row, and the set of halver cells."""

    digits: tuple
    halvers: frozenset

    def doubled(self, cell):
        """The cell's doubled value: its digit on a halver, twice it elsewhere."""
        digit = self.digits[cell[0]][cell[1]]
        return digit if cell in self.halvers else 2 * digit


class RuleCheck(NamedTuple):
    """One of the five statuses of `sudoku_kit.uniqueness`, with its
    witnesses read back as `Solution`s: `first` whenever a solution was
    found, `second` only on "not_unique"."""

    status: str
    first: Solution | None = None
    second: Solution | None = None


class MarkCheck(NamedTuple):
    """ "held" (no solution breaks the mark), "not_held" with a solution that
    breaks it as `counterexample`, or "timeout" (no verdict)."""

    status: str
    counterexample: Solution | None = None


def cell_name(cell):
    return f"r{cell[0] + 1}c{cell[1] + 1}"


def parse_cell(name):
    row, col = name.lower().removeprefix("r").split("c")
    return int(row) - 1, int(col) - 1


def line_name(line):
    body = " ".join(cell_name(cell) for cell in line.body)
    return f"{cell_name(line.a)} | {body} | {cell_name(line.b)}"


def line_holds(solution, line):
    """True when every body cell's value is strictly between the circles'."""
    lo, hi = sorted((solution.doubled(line.a), solution.doubled(line.b)))
    return all(lo < solution.doubled(cell) < hi for cell in line.body)


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


def _houses(n, box):
    bh, bw = box
    if bh * bw != n:
        raise ValueError(f"{bh}x{bw} boxes do not hold {n} cells")
    rows = [[(r, c) for c in range(n)] for r in range(n)]
    cols = [[(r, c) for r in range(n)] for c in range(n)]
    boxes = [
        [(br + dr, bc + dc) for dr in range(bh) for dc in range(bw)]
        for br in range(0, n, bh)
        for bc in range(0, n, bw)
    ]
    return rows, cols, boxes


class RuleModel:
    """Digits, halvers and doubled values for an n x n board with the given
    between lines. A 9x9 board with 3x3 boxes unless told otherwise."""

    def __init__(self, lines, n=9, box=(3, 3)):
        self.n = n
        rows, cols, boxes = _houses(n, box)
        self.model, self.x = cpsat.sudoku_model(n, None, regions=boxes)
        m, x = self.model, self.x
        self.h = {cell: m.NewBoolVar(f"h{cell}") for cell in x}
        self.dv = {cell: m.NewIntVar(1, 2 * n, f"dv{cell}") for cell in x}
        for cell in x:
            m.Add(self.dv[cell] == x[cell]).OnlyEnforceIf(self.h[cell])
            m.Add(self.dv[cell] == 2 * x[cell]).OnlyEnforceIf(self.h[cell].Not())
        for house in rows + cols + boxes:
            m.AddExactlyOne(self.h[cell] for cell in house)
        # One halver per row, so a row's halver digit is well defined; the n
        # of them all differ, so each digit sits in exactly one halver.
        halver_digit = [m.NewIntVar(1, n, f"hd{r}") for r in range(n)]
        for r, row in enumerate(rows):
            for cell in row:
                m.Add(halver_digit[r] == x[cell]).OnlyEnforceIf(self.h[cell])
        m.AddAllDifferent(halver_digit)
        self.lines = []
        for line in lines:
            self.add_line(line)

    def add_line(self, line):
        """Post one between line: each body cell strictly between the
        circles' doubled values, whichever circle is larger. Equal circles
        leave no body value possible."""
        if not line.body:
            raise ValueError(f"line {line_name(line)} has no body cell")
        if line.a == line.b:
            raise ValueError(f"line {line_name(line)} has one cell as both circles")
        m, dv = self.model, self.dv
        a_larger = m.NewBoolVar(f"big{len(self.lines)}")
        m.Add(dv[line.a] > dv[line.b]).OnlyEnforceIf(a_larger)
        m.Add(dv[line.a] < dv[line.b]).OnlyEnforceIf(a_larger.Not())
        for cell in line.body:
            m.Add(dv[cell] < dv[line.a]).OnlyEnforceIf(a_larger)
            m.Add(dv[cell] > dv[line.b]).OnlyEnforceIf(a_larger)
            m.Add(dv[cell] > dv[line.a]).OnlyEnforceIf(a_larger.Not())
            m.Add(dv[cell] < dv[line.b]).OnlyEnforceIf(a_larger.Not())
        self.lines.append(line)

    def _variables(self):
        return [self.x[cell] for cell in self.x] + [self.h[cell] for cell in self.x]

    def _solution(self, values):
        n = self.n
        cells = list(self.x)
        digits = dict(zip(cells, values[: len(cells)], strict=True))
        halvers = frozenset(
            c for c, v in zip(cells, values[len(cells) :], strict=True) if v
        )
        grid = tuple(tuple(digits[r, c] for c in range(n)) for r in range(n))
        return Solution(grid, halvers)

    def sample(self, rng, time_limit):
        """One solution, steered by a random digit hint per cell, on one
        worker; None when the solve reached its time limit first. Any other
        status without a solution raises: the lines a caller samples always
        have one."""
        m = self.model.clone()
        m.ClearHints()
        for var in self.x.values():
            m.AddHint(m.GetIntVarFromProtoIndex(var.Index()), rng.randint(1, self.n))
        solver = cpsat.solver(time_limit)
        status = solver.Solve(m)
        if status in cpsat.SOLVED:
            return self._solution([solver.Value(v) for v in self._variables()])
        if status == cpsat.UNKNOWN:
            return None
        raise ValueError(f"sampling got solver status {solver.StatusName(status)}")

    def hint(self, solution):
        """Give the model `solution` as its hint, so a check finds it first."""
        self.model.ClearHints()
        for cell, var in self.x.items():
            self.model.AddHint(var, solution.digits[cell[0]][cell[1]])
            self.model.AddHint(self.h[cell], cell in solution.halvers)

    def check(self, time_limit=10.0):
        """The five-status uniqueness of digits and halvers together, on one
        worker. Leaves the model unchanged."""
        result = check_uniqueness(
            self.model, self._variables(), time_limit=time_limit, workers=1
        )
        return RuleCheck(
            result.status,
            self._solution(result.first) if result.first else None,
            self._solution(result.second) if result.second else None,
        )

    def mark_holds(self, mark, time_limit=10.0):
        """Whether every solution agrees with `mark` (a `marks.json` entry):
        one solve of a copy of the model with the mark negated."""
        m = self.model.clone()
        x = {c: m.GetIntVarFromProtoIndex(v.Index()) for c, v in self.x.items()}
        h = {c: m.GetBoolVarFromProtoIndex(v.Index()) for c, v in self.h.items()}
        kind = mark["kind"]
        if kind == "digit":
            m.Add(x[parse_cell(mark["cell"])] != mark["digit"])
        elif kind == "candidates":
            for digit in mark["digits"]:
                m.Add(x[parse_cell(mark["cell"])] != digit)
        elif kind == "digit_in":
            for cell in map(parse_cell, mark["cells"]):
                m.Add(x[cell] != mark["digit"])
        elif kind == "halver":
            m.Add(h[parse_cell(mark["cell"])] == 0)
        elif kind == "halver_digit_in":
            for cell in map(parse_cell, mark["cells"]):
                is_digit = m.NewBoolVar(f"is{cell}")
                m.Add(x[cell] == mark["digit"]).OnlyEnforceIf(is_digit)
                m.Add(x[cell] != mark["digit"]).OnlyEnforceIf(is_digit.Not())
                m.AddBoolOr([h[cell].Not(), is_digit.Not()])
        else:
            raise ValueError(f"unknown mark kind {kind!r}: {mark}")
        solver = cpsat.solver(time_limit)
        status = solver.Solve(m)
        if status == cp_model.INFEASIBLE:
            return MarkCheck("held")
        if status in cpsat.SOLVED:
            values = [solver.Value(x[c]) for c in self.x] + [
                solver.Value(h[c]) for c in self.x
            ]
            return MarkCheck("not_held", self._solution(values))
        if status == cpsat.UNKNOWN:
            return MarkCheck("timeout")
        raise ValueError(f"mark check got solver status {solver.StatusName(status)}")


def mark_name(mark):
    """The mark in words, as the report prints it."""
    kind = mark["kind"]
    if kind == "digit":
        return f"{mark['cell']} = {mark['digit']}"
    if kind == "candidates":
        return f"{mark['cell']} in {{{','.join(map(str, mark['digits']))}}}"
    if kind == "digit_in":
        return f"{mark['digit']} in {' or '.join(mark['cells'])}"
    if kind == "halver":
        return f"{mark['cell']} is a halver"
    if kind == "halver_digit_in":
        return f"a halver {mark['digit']} in {' or '.join(mark['cells'])}"
    raise ValueError(f"unknown mark kind {kind!r}: {mark}")

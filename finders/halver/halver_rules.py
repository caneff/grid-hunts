"""The shared halver layer's CP-SAT side (spec #52): the halver board model,
for any line type, and the results of the questions asked of it.

`HalverModel(post, lines)` builds the board once: digits, one halver boolean
per cell and a doubled value per cell. Each row, column and box has exactly
one halver, the halver digits all differ, and a cell's doubled value is its
digit on a halver and twice its digit elsewhere. A line type plugs in through
`post(model, dv, line, index)`, which puts one of its lines on the model as
constraints on the doubled values `dv` (`index` counts the lines already
posted, for naming variables). `add_line` posts one more line on the same
model, so a caller that adds lines one at a time never rebuilds the board.
`sample` draws one solution, steered by random digit hints, and `hint` makes
a given solution the one a later uniqueness check tries first. The model asks
no other question itself: `variables` names its digits and halvers and
`solution` reads a {name: value} back as a `Solution`, and
`halver_query.uniqueness` and `halver_query.holds` put the board-question
driver's `unique` and `forced` on it (spec #65, #98). `RuleCheck` and
`MarkCheck` are what those two return.

A line is a `Line`: two ends and its body cells in path order. Cells are
(row, column) from 0; `cell_name` and `parse_cell` convert to and from the
rNcM form the specs and the reports use. `lines_from_doc` reads one line
type's lines from a decoded SudokuMaker document, and `lines_alone` reads
them from a board that holds nothing else, refusing one that does.
"""

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from sudoku_kit import cpsat

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "query"))

# isort: split
from conditions import All, Any_, Eq


class Line(NamedTuple):
    """A line: end `a`, the `body` cells in path order, end `b`."""

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


def parse_cell(name, n=None):
    """The (row, column) from 0 of a cell named rNcM. A ValueError naming the
    cell when row or column is 0, or past the board when `n`, its size, is
    given."""
    row, col = name.lower().removeprefix("r").split("c")
    row, col = int(row), int(col)
    if row < 1 or col < 1 or (n is not None and max(row, col) > n):
        board = "" if n is None else f" on a {n}x{n} board"
        raise ValueError(f"no cell {name}{board}")
    return row - 1, col - 1


def mark_cells(mark):
    """The cell names a `marks.json` entry reads."""
    return [mark["cell"]] if "cell" in mark else mark.get("cells", [])


def check_mark_cells(mark, n):
    """Raises a ValueError naming the first cell of `mark` that `parse_cell`
    refuses on an n x n board."""
    for name in mark_cells(mark):
        parse_cell(name, n)


def line_name(line):
    body = " ".join(cell_name(cell) for cell in line.body)
    return f"{cell_name(line.a)} | {body} | {cell_name(line.b)}"


def parse_line(row):
    """The line `line_name` printed as `row`."""
    a, body, b = (part.split() for part in row.split("|"))
    return Line(parse_cell(a[0]), tuple(map(parse_cell, body)), parse_cell(b[0]))


def lines_from_doc(doc, constraint_type, kind):
    """The lines of one SudokuMaker constraint type in a decoded document, in
    its order: each path's first and last cells are the ends. Raises a
    ValueError naming `kind` and the type when the document has none, and
    one naming the cell when a path leaves the board."""
    n = round(len(doc["puzzle"]["cells"]) ** 0.5)
    groups = [
        c["lines"]
        for c in doc["puzzle"]["constraints"]
        if c.get("type") == constraint_type
    ]
    if not groups:
        raise ValueError(f"no {kind} lines (constraint type {constraint_type})")
    lines = []
    for group in groups:
        for path_cells in group:
            off = [i for i in path_cells if not 0 <= i < n * n]
            if off:
                raise ValueError(
                    f"{kind} line {path_cells} has cell {off[0]} off the board"
                )
            cells = [divmod(i, n) for i in path_cells]
            lines.append(Line(cells[0], tuple(cells[1:-1]), cells[-1]))
    return lines


def lines_alone(doc, constraint_type, kind):
    """The lines of `lines_from_doc` from a 9x9 document that holds nothing
    else: beside the given-digits and regions elements (types 0 and 1), any
    other constraint, or a cell marked `"given": true`, raises a ValueError
    naming it, so a board is refused rather than left partly unchecked.
    Digits entered in cells, never given, are not read."""
    cells = len(doc["puzzle"]["cells"])
    if cells != 81:
        raise ValueError(f"{cells} cells, and only 9x9 is checked")
    lines = lines_from_doc(doc, constraint_type, kind)
    allowed = {0, 1, constraint_type}
    other = sorted(
        {c.get("type") for c in doc["puzzle"]["constraints"]} - allowed, key=str
    )
    if other:
        raise ValueError(f"constraint type {other[0]} on a {kind}-only board")
    given = [i for i, cell in enumerate(doc["puzzle"]["cells"]) if cell.get("given")]
    if given:
        raise ValueError(f"given digit in {cell_name(divmod(given[0], 9))}")
    return lines


def _houses(n, box):
    boxes = cpsat.boxes(n, *box)
    rows = [[(r, c) for c in range(n)] for r in range(n)]
    cols = [[(r, c) for r in range(n)] for c in range(n)]
    return rows, cols, boxes


class HalverModel:
    """Digits, halvers and doubled values for an n x n board with the given
    lines, each put on by the line type's `post`. A 9x9 board with 3x3 boxes
    unless told otherwise."""

    def __init__(self, post, lines, n=9, box=(3, 3)):
        self.post = post
        self.n = n
        rows, cols, boxes = _houses(n, box)
        self.model, self.x = cpsat.sudoku_model(n, boxes)
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
        """Post one more line with the line type's `post`."""
        self.post(self.model, self.dv, line, len(self.lines))
        self.lines.append(line)

    def variables(self):
        """The model's variables by name, digits then halvers: `r1c1` the
        digit, `h_r1c1` 1 on a halver."""
        names = {cell_name(c): v for c, v in self.x.items()}
        names |= {f"h_{cell_name(c)}": v for c, v in self.h.items()}
        return names

    def solution(self, values):
        """`values`, a {name: value} over `variables`, as a `Solution`."""
        n = self.n
        grid = tuple(
            tuple(values[cell_name((r, c))] for c in range(n)) for r in range(n)
        )
        halvers = frozenset(c for c in self.x if values[f"h_{cell_name(c)}"])
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
            return self.solution(
                {k: solver.Value(v) for k, v in self.variables().items()}
            )
        if status == cpsat.UNKNOWN:
            return None
        raise ValueError(f"sampling got solver status {solver.StatusName(status)}")

    def hint(self, solution):
        """Give the model `solution` as its hint, so a check finds it first."""
        self.model.ClearHints()
        for cell, var in self.x.items():
            self.model.AddHint(var, solution.digits[cell[0]][cell[1]])
            self.model.AddHint(self.h[cell], cell in solution.halvers)


class MarkKind(NamedTuple):
    """One kind of `marks.json` entry: `name` puts the mark in words, as the
    reports print it, and `condition` is what every solution must meet for
    the mark to hold."""

    name: Callable
    condition: Callable


def _all_halvers_with_digit(mark):
    return Any_(
        tuple(All((Eq(f"h_{c}", 1), Eq(c, mark["digit"]))) for c in mark["cells"])
    )


# The one table of mark kinds: a new kind is one entry here.
MARK_KINDS = {
    "digit": MarkKind(
        lambda m: f"{m['cell']} = {m['digit']}",
        lambda m: Eq(m["cell"], m["digit"]),
    ),
    "candidates": MarkKind(
        lambda m: f"{m['cell']} in {{{','.join(map(str, m['digits']))}}}",
        lambda m: Any_(tuple(Eq(m["cell"], d) for d in m["digits"])),
    ),
    "digit_in": MarkKind(
        lambda m: f"{m['digit']} in {' or '.join(m['cells'])}",
        lambda m: Any_(tuple(Eq(c, m["digit"]) for c in m["cells"])),
    ),
    "halver": MarkKind(
        lambda m: f"{m['cell']} is a halver",
        lambda m: Eq(f"h_{m['cell']}", 1),
    ),
    "halver_digit_in": MarkKind(
        lambda m: f"a halver {m['digit']} in {' or '.join(m['cells'])}",
        _all_halvers_with_digit,
    ),
}


def mark_kind(mark):
    """The `MARK_KINDS` entry of `mark`; a ValueError naming an unknown kind."""
    kind = mark["kind"]
    if kind not in MARK_KINDS:
        raise ValueError(f"unknown mark kind {kind!r}: {mark}")
    return MARK_KINDS[kind]


def mark_name(mark):
    """The mark in words, as the reports print it."""
    return mark_kind(mark).name(mark)


def mark_condition(mark):
    """A `marks.json` entry as a condition on the board's variables."""
    return mark_kind(mark).condition(mark)


def read_marks(path, n):
    """The marks in the JSON file `path` for an n x n board. A ValueError
    names `path` and what is wrong: unreadable, not JSON, not a list of
    marks, an unknown kind, a missing field or a cell off the board."""
    try:
        marks = json.loads(Path(path).read_text())
        if not isinstance(marks, list) or not all(isinstance(m, dict) for m in marks):
            raise ValueError("not a list of marks")
        for mark in marks:
            mark_name(mark)
            check_mark_cells(mark, n)
    except KeyError as error:
        raise ValueError(f"{path}: a mark lacks {error}") from error
    except (OSError, ValueError, TypeError) as error:
        raise ValueError(f"{path}: {error}") from error
    return marks

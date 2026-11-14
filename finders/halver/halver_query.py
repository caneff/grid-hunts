"""The halver finders on the board-question driver (spec #65, #94, #95):
`finders/query/query.py`'s finder contract over `HalverModel`, for any line
type.

`HalverQuery(post, lines, doc, line_color)` is a 9x9 halver board with the
line type's `lines`, read from the decoded SudokuMaker document `doc`. Its
variables are named by cell: `r1c1` the digit, `h_r1c1` 1 on a halver.
`draw` shades halver cells in one tint and draws each line through its cell
centres in the line type's colour, its two ends ringed, and each marked
line in `DROP_COLOR`, the second colour every line type shares. `link` mints a short
link of `doc` with every cell's entries cleared and, given a solution, its
digits entered; SudokuMaker has no halvers, so the picture is what shows them.
`mark` reads a `marks.json` entry as a condition on those variables
(`condition`).

For a `HalverModel` already built, hinted or grown line by line (the halver
reports, the hunt's loop), `uniqueness(board, time_limit)` is the driver's
`unique` on it, a `RuleCheck`, and `holds(board, mark, time_limit)` its
`forced` on a `marks.json` entry, a `MarkCheck`, asked on a copy of the
model. Their witnesses come back as `Solution`s. Neither reads a timeout as
unique or as held (#98).
"""

import copy
import sys
from pathlib import Path

FINDERS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FINDERS / "hunt"))
sys.path.insert(0, str(FINDERS / "query"))

# isort: split
import query
from halver_rules import (
    HalverModel,
    MarkCheck,
    RuleCheck,
    cell_name,
    check_mark_cells,
    mark_condition,
    parse_cell,
)
from short_link import mint

N = 9
BOX = (3, 3)
HALVER_TINT = (255, 214, 120)
DROP_COLOR = (220, 60, 140)


class HalverQuery:
    size = (N, N)

    def __init__(self, post, lines, doc, line_color):
        self.post = post
        self.clues = list(lines)
        self.doc = doc
        self.line_color = line_color

    def build(self, clues):
        board = HalverModel(self.post, clues, N, BOX)
        return board.model, board.variables()

    def cell_of(self, name):
        return parse_cell(name.removeprefix("h_"))

    def draw(self, canvas, solution, marked=()):
        """Draw the lines (those indexed in `marked` in `DROP_COLOR`), and, given a
        `solution`, its halver tints and digits, onto `canvas`."""
        cells = [(r, c) for r in range(N) for c in range(N)]
        if solution is not None:
            for cell in cells:
                if solution[f"h_{cell_name(cell)}"]:
                    canvas.shade_cell(*cell, HALVER_TINT)
        width = max(2, canvas.cell // 6)
        for k, line in enumerate(self.clues):
            color = DROP_COLOR if k in marked else self.line_color
            canvas.path([line.a, *line.body, line.b], color, width)
            for end in (line.a, line.b):
                canvas.circle(*end, color=color, width=width, fill="white")
        canvas.box_lines(*BOX)
        if solution is not None:
            for cell in cells:
                canvas.digit(*cell, solution[cell_name(cell)])

    def link(self, solution):
        """A short link of `doc` with every cell cleared, and `solution`'s digits
        entered when given."""
        doc = copy.deepcopy(self.doc)
        doc["puzzle"]["cells"] = [
            {"value": solution[cell_name(divmod(i, N))]} if solution else {}
            for i in range(N * N)
        ]
        return mint(doc)

    def mark(self, entry):
        """The `marks.json` entry as a condition (`halver_rules.MARK_KINDS`)."""
        return mark_condition(entry)


def load_marks(path, n):
    """The marks in the JSON file `path` for an n x n board, read by the
    driver's `read_entries` (a list of objects, each with the fields its
    kind needs), each kind one of `halver_rules.MARK_KINDS` and each cell on
    the board. A ValueError names `path` and what is wrong."""
    try:
        entries = query.read_entries(mark_condition, Path(path))
        marks = [fields["mark"] for _, fields in entries]
        for mark in marks:
            check_mark_cells(mark, n)
    except (OSError, ValueError, TypeError) as error:
        raise ValueError(f"{path}: {error}") from error
    return marks


def uniqueness(board, time_limit=10.0):
    """The driver's `unique` on `board` as it stands, hints included."""
    status, solutions = query.unique_on(board.model, board.variables(), time_limit)
    return RuleCheck(status, *map(board.solution, solutions))


def holds(board, mark, time_limit=10.0):
    """The driver's `forced` on the `marks.json` entry `mark`, asked on a copy
    of `board`'s model, which it leaves unchanged. A ValueError names a cell
    of `mark` that is not on the board."""
    check_mark_cells(mark, board.n)
    model = board.model.clone()
    variables = {
        k: model.GetIntVarFromProtoIndex(v.Index())
        for k, v in board.variables().items()
    }
    status, solutions = query.forced_on(
        model, variables, mark_condition(mark), time_limit
    )
    return MarkCheck(status, *map(board.solution, solutions))

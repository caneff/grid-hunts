"""The halver finders on the board-question driver (spec #65, #94, #95):
`finders/query/query.py`'s finder contract over `HalverModel`, for any line
type.

`HalverQuery(post, lines, doc, line_color)` is a 9x9 halver board with the
line type's `lines`, read from the decoded SudokuMaker document `doc`. Its
variables are named by cell: `r1c1` the digit, `h_r1c1` 1 on a halver.
`draw` shades halver cells in one tint and draws each line through its cell
centres in the line type's colour, its two ends ringed. `link` mints a short
link of `doc` with every cell's entries cleared and, given a solution, its
digits entered; SudokuMaker has no halvers, so the picture is what shows them.
`mark` reads a `marks.json` entry as a condition on those variables.
"""

import copy
import sys
from pathlib import Path

FINDERS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FINDERS / "hunt"))
sys.path.insert(0, str(FINDERS / "query"))

# isort: split
from conditions import All, Any_, Eq
from halver_rules import HalverModel, cell_name, parse_cell
from short_link import mint

N = 9
BOX = (3, 3)
HALVER_TINT = (255, 214, 120)


class HalverQuery:
    size = (N, N)

    def __init__(self, post, lines, doc, line_color):
        self.post = post
        self.clues = list(lines)
        self.doc = doc
        self.line_color = line_color

    def build(self, clues):
        board = HalverModel(self.post, clues, N, BOX)
        names = {cell_name(c): v for c, v in board.x.items()}
        names |= {f"h_{cell_name(c)}": v for c, v in board.h.items()}
        return board.model, names

    def cell_of(self, name):
        return parse_cell(name.removeprefix("h_"))

    def draw(self, canvas, solution):
        cells = [(r, c) for r in range(N) for c in range(N)]
        if solution is not None:
            for cell in cells:
                if solution[f"h_{cell_name(cell)}"]:
                    canvas.shade_cell(*cell, HALVER_TINT)
        width = max(2, canvas.cell // 6)
        for line in self.clues:
            canvas.path([line.a, *line.body, line.b], self.line_color, width)
            for end in (line.a, line.b):
                canvas.circle(*end, color=self.line_color, width=width, fill="white")
        canvas.box_lines(*BOX)
        if solution is not None:
            for cell in cells:
                canvas.digit(*cell, solution[cell_name(cell)])

    def link(self, solution):
        doc = copy.deepcopy(self.doc)
        doc["puzzle"]["cells"] = [
            {"value": solution[cell_name(divmod(i, N))]} if solution else {}
            for i in range(N * N)
        ]
        return mint(doc)

    def mark(self, entry):
        """A `marks.json` entry as a condition: what every solution must
        meet for the mark to hold."""
        kind = entry["kind"]
        cells = entry.get("cells", [])
        if kind == "digit":
            return Eq(entry["cell"], entry["digit"])
        if kind == "candidates":
            return Any_(tuple(Eq(entry["cell"], d) for d in entry["digits"]))
        if kind == "digit_in":
            return Any_(tuple(Eq(c, entry["digit"]) for c in cells))
        if kind == "halver":
            return Eq(f"h_{entry['cell']}", 1)
        if kind == "halver_digit_in":
            return Any_(
                tuple(All((Eq(f"h_{c}", 1), Eq(c, entry["digit"]))) for c in cells)
            )
        raise ValueError(f"unknown mark kind {kind!r}: {entry}")

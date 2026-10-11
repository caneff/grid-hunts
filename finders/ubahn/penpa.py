"""A found U-Bahn network as a Penpa+ link (#774), standard library only.

The wire format and the layout of three published U-Bahn links:
docs/research/2026-10-10-u-bahn-penpa-link.md (§ numbers below are its).
The board is the grid with `k` rows of outside numbers above and `k` columns
of them to its left, ordinary cells of the table, with one row and one column
of icons beside the grid; the top-left `(k-1)` square is left out of the cell
list. The `k` kinds run from the outside in: [blank,] cross, branch,
straight, turn (Chris's ruling on #774); the blank number is the option's
fifth. The link opens in the Line tool and carries a lines-only answer check
(`sol_loopline`, § 3).

The hybrid link (#795) is the same board with chosen circles and chosen
numbers: `Hybrid(circles, numbers)` names them in `hybrid.py`'s cells, `(r, c)`
for a grid cell, `(r, -k)` and `(-k, c)` for a number cell in strip k (1 the
innermost). Every number cell not named is drawn empty, the grid is dotted and
the rules text is the combined puzzle's; the answer check is the plain link's.

`link` returns the URL as one string. A link is a 10 KB blob: write it to a
file, never to chat.
"""

import base64
import copy
import json
import sys
import zlib
from itertools import pairwise
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
# isort: split
import network

PAGE = "https://swaroopg92.github.io/penpa-edit/"
CELL_SIZE = 38
MARGIN = 2  # hidden cells on every side of the table (§ 1.4)

# The kinds from the outside in, as `network.KIND_NAMES` spells them.
PIECE_ORDER = ("cross", "branch", "straight", "turn")
KINDS_WITH_BLANK = ("blank", *PIECE_ORDER)

# Abbreviations applied to the whole payload text, in this order (§ 1.2).
COMPRESS_SUB = (
    ("z", "zZ"),
    ('"qa"', "z9"),
    ('"pu_q"', "zQ"),
    ('"pu_a"', "zA"),
    ('"grid"', "zG"),
    ('"edit_mode"', "zM"),
    ('"surface"', "zS"),
    ('"line"', "zL"),
    ('"lineE"', "zE"),
    ('"wall"', "zW"),
    ('"cage"', "zC"),
    ('"number"', "zN"),
    ('"symbol"', "zY"),
    ('"special"', "zP"),
    ('"board"', "zB"),
    ('"command_redo"', "zR"),
    ('"command_undo"', "zU"),
    ('"command_replay"', "z8"),
    ('"numberS"', "z1"),
    ('"freeline"', "zF"),
    ('"freelineE"', "z2"),
    ('"thermo"', "zT"),
    ('"arrows"', "z3"),
    ('"direction"', "zD"),
    ('"squareframe"', "z0"),
    ('"polygon"', "z5"),
    ('"deletelineE"', "z4"),
    ('"killercages"', "z6"),
    ('"nobulbthermo"', "z7"),
    ('"__a"', "z_"),
    ("null", "zO"),
)

# The question layer's keys, in the order Penpa+ writes them (§ 1.5).
LAYER_KEYS = (
    "command_redo",
    "command_undo",
    "command_replay",
    "surface",
    "number",
    "numberS",
    "symbol",
    "freeline",
    "freelineE",
    "thermo",
    "arrows",
    "direction",
    "squareframe",
    "polygon",
    "line",
    "lineE",
    "wall",
    "cage",
    "deletelineE",
    "killercages",
    "nobulbthermo",
)
_LAYER_EMPTY = {
    "command_redo": {"__a": []},
    "command_undo": {"__a": []},
    "command_replay": {"__a": []},
    "thermo": [],
    "arrows": [],
    "direction": [],
    "squareframe": [],
    "polygon": [],
    "killercages": [],
    "nobulbthermo": [],
}

# The answer check: lines only, in the one style the check counts (§ 3).
CHECK_FLAGS = (
    "sol_surface_exact",
    "sol_surface",
    "sol_number",
    "sol_loopline_exact",
    "sol_loopline",
    "sol_ignoreloopline",
    "sol_loopedge_exact",
    "sol_loopedge",
    "sol_ignoreborder",
    "sol_wall",
    "sol_square",
    "sol_circle",
    "sol_tri",
    "sol_arrow",
    "sol_math",
    "sol_battleship",
    "sol_tent",
    "sol_star",
    "sol_akari",
    "sol_mine",
)
OR_FLAGS = (
    "sol_or_surface",
    "sol_or_number",
    "sol_or_loopline",
    "sol_or_loopedge",
    "sol_or_wall",
    "sol_or_square",
    "sol_or_circle",
    "sol_or_tri",
    "sol_or_arrow",
    "sol_or_math",
    "sol_or_battleship",
    "sol_or_tent",
    "sol_or_star",
    "sol_or_akari",
    "sol_or_mine",
)

# The `mode` object as the published U-Bahn link with a check writes it:
# the Line tool, normal submode, style 3 (green), in the solver's layer.
_MODE = {
    "qa": "pu_a",
    "grid": ["1", "2", "1"],
    "pu_q": {
        "edit_mode": "number",
        "surface": ["", 1],
        "line": ["5", 2],
        "lineE": ["1", 21],
        "wall": ["", 2],
        "cage": ["1", 10],
        "number": ["1", 1],
        "symbol": ["cross", 1],
        "special": ["thermo", ""],
        "board": ["", ""],
        "move": ["1", ""],
        "combi": ["battleship", ""],
        "sudoku": ["1", 1],
    },
    "pu_a": {
        "edit_mode": "line",
        "surface": ["", 8],
        "line": ["1", 3],
        "lineE": ["1", 3],
        "wall": ["", 3],
        "cage": ["1", 10],
        "number": ["1", 2],
        "symbol": ["circle_L", 1],
        "special": ["thermo", ""],
        "board": ["", ""],
        "move": ["1", ""],
        "combi": ["battleship", ""],
        "sudoku": ["1", 9],
    },
}

# The cross icon's four flags are [right, down, left, up] (§ 1.5). Per piece,
# the icon beside a row of outside numbers and beside a column of them.
# The turn's icon sits in the one cell the innermost row and column share.
ICONS = {
    "cross": ([1, 1, 1, 1], [1, 1, 1, 1]),
    "branch": ([1, 1, 1, 0], [1, 1, 0, 1]),
    "straight": ([1, 0, 1, 0], [0, 1, 0, 1]),
    "turn": ([1, 1, 0, 0], [1, 1, 0, 0]),
}
BLANK_ICON = "□"  # a number's text: a blank cell has no arm to draw
CIRCLE = [1, "circle_L", 1]  # a symbol: the plain white ring, under the lines

TITLE = "U-Bahn"
RULES = (
    "Draw a totally connected loop network through the centers of some "
    "cells, which may branch or turn, but may not have any dead ends. "
    "Lines of the network cross cells only through their centers."
    "\n"
    "A number outside the grid says how many cells of the kind beside it "
    "(from the outside in: {kinds}) the row or column holds."
)
HYBRID_TITLE = "U-Bahn Choco-Banana"
# The combined puzzle's rules as Chris pasted them (#795).
HYBRID_RULES = (
    "U-Bahn:\n"
    "Draw in the dotted grid a single connected network of lines going "
    "through the centers of some orthogonally adjacent cells, which may "
    "branch or turn, but may not have any dead ends.\n"
    "Cells above and to the left of the grid have a value that indicates "
    "how many times a given tile (i.e. a blank, cross, branch, straight "
    "line, or turn), including its rotations, will appear in that row or "
    "column.\n"
    "Choco-Banana:\n"
    "Assign each grid cell a digit from 0 to 4 as follows: empty cell = 0, "
    "corner = 1, straight line = 2, branch = 3, cross = 4.\n"
    "Among both grid cells and clue cells, every group of orthogonally "
    "connected cells with even values is a rectangle (chocolate), and every "
    "group of orthogonally connected cells with odd values is not a "
    "rectangle (banana). Note: squares are rectangles.\n"
    "A digit in a circle counts the number of cells of the chocolate or "
    "banana region that circle lies in."
)
DOTTED_GRID = ["2", "2", "1"]  # dotted gridlines, no lattice points, a frame
_ESCAPES = ((",", "%2C"), ("\n", "%2D"), ("&", "%2E"), ("=", "%2F"))
# What the rules text calls a kind, where it is not the kind's own name.
_KIND_WORDS = {"blank": "no arm at all"}


class Hybrid(NamedTuple):
    """What the hybrid link shows: the cells that carry a circle and the
    number cells whose outside number is printed, in `hybrid.py`'s cells."""

    circles: frozenset
    numbers: frozenset


def _json(value):
    return json.dumps(value, separators=(",", ":"))


def _escape(text):
    """A header field: the characters the header's own syntax uses, spelt
    the way Penpa+ reads them back (§ 1.3)."""
    for plain, escaped in _ESCAPES:
        text = text.replace(plain, escaped)
    return text


def deflate_base64(text):
    """Raw deflate, then base64 without padding: Penpa+'s `encrypt_data`
    (§ 1.2)."""
    deflater = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = deflater.compress(text.encode("utf-8")) + deflater.flush()
    return base64.b64encode(packed).decode("ascii").rstrip("=")


def center_point(nx, ny):
    """The index of the point nearest the middle of an `nx` by `ny` table
    (§ 1.4): a vertex where both counts are even, a cell centre where both
    are odd, an edge midpoint when they differ. Checked against the five
    published headers for square tables only; the mixed case is read from
    the same geometry."""
    nx0, ny0 = nx + 2 * MARGIN, ny + 2 * MARGIN
    size = nx0 * ny0
    x, y = MARGIN + nx // 2, MARGIN + ny // 2
    if nx % 2 == 0 and ny % 2 == 0:
        return size + (x - 1) + (y - 1) * nx0
    if nx % 2 == 1 and ny % 2 == 1:
        return x + y * nx0
    if nx % 2 == 0:
        # Middle of a vertical edge: the right edge of the cell left of it.
        return 3 * size + (x - 1) + y * nx0
    # Middle of a horizontal edge: the bottom edge of the cell above it.
    return 2 * size + x + (y - 1) * nx0


def _layer(**filled):
    layer = {}
    for key in LAYER_KEYS:
        value = filled.get(key)
        if value is None:
            value = copy.deepcopy(_LAYER_EMPTY.get(key, {}))
        layer[key] = value
    return layer


class _Table(NamedTuple):
    """The board's geometry: `strips` rows and columns of outside numbers
    round a `rows` by `cols` grid, on an `nx` by `ny` table padded to
    `nx0` wide (§ 1.4)."""

    strips: int
    nx: int
    ny: int
    nx0: int

    @property
    def size(self):
        return self.nx0 * (self.ny + 2 * MARGIN)

    @property
    def grid_origin(self):
        """Padded x and y of the grid's first cell."""
        return MARGIN + self.strips

    def cell(self, x, y):
        """Cell-centre index of padded (x, y)."""
        return x + y * self.nx0

    def grid_cell(self, r, c):
        """Cell-centre index of grid cell (r, c)."""
        g = self.grid_origin
        return self.cell(g + c, g + r)

    def vertex(self, x, y):
        """Index of the vertex at the bottom-right corner of padded (x, y)."""
        return self.size + self.cell(x, y)

    def board_cell(self, cell):
        """Cell-centre index of a cell in `hybrid.py`'s scheme: a grid cell
        `(r, c)`, or a number cell `(r, -k)` or `(-k, c)`. Raises ValueError
        on a cell this table does not hold."""
        r, c = cell
        rows, cols = self.ny - self.strips, self.nx - self.strips
        in_grid = 0 <= r < rows and 0 <= c < cols
        in_row_strip = 0 <= r < rows and -self.strips <= c < 0
        in_col_strip = 0 <= c < cols and -self.strips <= r < 0
        if not (in_grid or in_row_strip or in_col_strip):
            raise ValueError(f"cell {cell} is off the board")
        g = self.grid_origin
        return self.cell(g + c, g + r)

    def number_cell(self, cell):
        """Cell-centre index of a number cell `(r, -k)` or `(-k, c)`. Raises
        ValueError on a grid cell or a cell this table does not hold."""
        if min(cell) >= 0:
            raise ValueError(f"cell {cell} is a grid cell, not a number cell")
        return self.board_cell(cell)

    def cell_list(self):
        """Cell-centre indices of the table, row by row, without the notch."""
        k = self.strips
        return [
            self.cell(x, y)
            for y in range(MARGIN, self.ny + MARGIN)
            for x in range(MARGIN, self.nx + MARGIN)
            if not (x < MARGIN + k - 1 and y < MARGIN + k - 1)
        ]


def _table(rows, cols, blank_number):
    strips = len(KINDS_WITH_BLANK if blank_number else PIECE_ORDER)
    nx, ny = cols + strips, rows + strips
    return _Table(strips, nx, ny, nx + 2 * MARGIN)


def _deltas(indices):
    """The first index, then each step to the next (§ 1.4)."""
    return [indices[0]] + [b - a for a, b in pairwise(indices)]


def _rules_text(kinds):
    return RULES.format(kinds=", ".join(_KIND_WORDS.get(k, k) for k in kinds))


def payload(rows, cols, found, blank_number=False, hybrid=None):
    """The inflated, unabbreviated text of the `p` parameter: 19 lines. A
    `hybrid` draws only its numbers and circles, dotted, under the combined
    rules; none draws every number, solid, under the U-Bahn rules."""
    kinds = KINDS_WITH_BLANK if blank_number else PIECE_ORDER
    t = _table(rows, cols, blank_number)
    g = t.grid_origin

    row_numbers, col_numbers = network.outside_numbers(found, rows, cols)
    # The table cells whose number is printed; None prints every one.
    shown = None if hybrid is None else {t.number_cell(c) for c in hybrid.numbers}
    number = {}
    for j, name in enumerate(kinds):
        kind = network.KIND_NAMES.index(name)
        for c in range(cols):
            at = t.cell(g + c, MARGIN + j)
            if shown is None or at in shown:
                number[at] = [str(col_numbers[c][kind]), 1, "1"]
        for r in range(rows):
            at = t.cell(MARGIN + j, g + r)
            if shown is None or at in shown:
                number[at] = [str(row_numbers[r][kind]), 1, "1"]

    symbol = {}
    for j, name in enumerate(kinds):
        if name == "blank":
            number[t.cell(g - 1, MARGIN + j)] = [BLANK_ICON, 1, "1"]
            number[t.cell(MARGIN + j, g - 1)] = [BLANK_ICON, 1, "1"]
            continue
        beside_rows, beside_cols = ICONS[name]
        # The icon of the row of numbers at y sits in the last number column,
        # and the icon of the column at x in the last number row; the
        # innermost kind's two icons are the one cell where those meet.
        symbol[t.cell(g - 1, MARGIN + j)] = [beside_rows, "cross", 1]
        symbol[t.cell(MARGIN + j, g - 1)] = [beside_cols, "cross", 1]

    # Thick dividers along the right of the last number column and the bottom
    # of the last number row, in vertex indices (§ 1.4), style 21.
    divider = {}
    for y in range(MARGIN, t.ny + MARGIN):
        divider[f"{t.vertex(g - 1, y - 1)},{t.vertex(g - 1, y)}"] = 21
    for x in range(MARGIN, t.nx + MARGIN):
        divider[f"{t.vertex(x - 1, g - 1)},{t.vertex(x, g - 1)}"] = 21

    mode = _MODE
    if hybrid is not None:
        mode = {**_MODE, "grid": DOTTED_GRID}
        for cell in hybrid.circles:
            symbol[t.board_cell(cell)] = copy.copy(CIRCLE)

    question = _layer(number=number, symbol=symbol, lineE=divider)
    center = center_point(t.nx, t.ny)
    header = [
        "square",
        str(t.nx),
        str(t.ny),
        str(CELL_SIZE),
        "0",
        "1",
        "1",
        str((t.nx + 1) * CELL_SIZE),
        str((t.ny + 1) * CELL_SIZE),
        str(center),
        str(center),
        "0",
        "0",
        "0",
        "0",
        "Title: " + _escape(TITLE if hybrid is None else HYBRID_TITLE),
        "Author: ",
        "",
        _escape(_rules_text(kinds) if hybrid is None else HYBRID_RULES),
        "OFF",
        "false",
    ]
    lines = [
        ",".join(header),
        _json([0, 0, 0, 0]),
        f'{_json(mode["grid"])}~"line"~["1",3]',
        _json(question),
        "",
        _json(_deltas(t.cell_list())),
        "[]",
        _json({flag: flag == "sol_loopline" for flag in CHECK_FLAGS}),
        '"x"',
        '"x"',
        "[3,1,3]",
        _json(mode),
        '"x"',
        "0",
        _json(_layer()),
        "x",
        _json(dict.fromkeys(OR_FLAGS, False)),
        "[]",
        "Congratulations!",
    ]
    return "\n".join(lines)


def answer(rows, cols, found, blank_number=False):
    """The inflated text of the `a` parameter: the network's segments as
    `"<low>,<high>,1"` between cell-centre indices, sorted the way
    JavaScript sorts strings, in the second of six arrays (§ 3, § 5 step 9)."""
    t = _table(rows, cols, blank_number)
    segments = sorted(
        "{},{},1".format(*sorted((t.grid_cell(*a), t.grid_cell(*b)))) for a, b in found
    )
    return _json([[], segments, [], [], [], []])


def abbreviate(text):
    """`COMPRESS_SUB` applied to the whole payload text, in order (§ 1.2)."""
    for plain, token in COMPRESS_SUB:
        text = text.replace(plain, token)
    return text


def link(rows, cols, found, blank_number=False, hybrid=None):
    """The Penpa+ solve link for a network on a `rows` by `cols` board: its
    outside numbers as the numbers round the grid, its edges as the embedded
    answer. With a `Hybrid`, only its numbers and circles are shown; the
    answer is the same. Raises ValueError, naming the cell, on a circle or a
    number that is not on the board."""
    text = abbreviate(payload(rows, cols, found, blank_number, hybrid))
    return (
        f"{PAGE}#m=solve&p={deflate_base64(text)}"
        f"&a={deflate_base64(answer(rows, cols, found, blank_number))}"
    )

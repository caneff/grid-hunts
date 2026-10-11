"""The hybrid rules read straight off a network, with no solver (#782):
U-Bahn with Choco-Banana laid over the grid cells and the number cells.

The board is the grid plus strips of number cells above it and to its left,
one strip per kind. A cell is `(r, c)`: a grid cell has both at 0 or more, as
in `network.py`; `(r, -k)` is row r's number cell in strip k and `(-k, c)` is
column c's, strip 1 the innermost. From the inside out the strips count turn,
straight, branch, cross, which is `network.KINDS` order, so strip k counts
kind k - 1; the blank strip is the optional fifth. The corner where both are
negative holds the icon cells and the area off the board, and no cell of it
is on the board.

Rules as Chris ruled them: spec #781.
"""

import re
import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import network
import penpa

# What a grid cell of each kind is worth. A number cell is worth its outside
# number.
PIECE_VALUE = {
    network.BLANK: 0,
    network.TURN: 1,
    network.STRAIGHT: 2,
    network.BRANCH: 3,
    network.CROSS: 4,
}


def strips(blank_strip=False):
    """How many strips of number cells each side has."""
    return 5 if blank_strip else 4


class Conditions(NamedTuple):
    """What a hybrid grid is asked to meet: the board, the circled cells,
    the piece-count condition (a `network.Exactly`, or None), whether the
    blank strip is on, and the fewest banana regions it may have (0 asks for
    none)."""

    rows: int
    cols: int
    circles: frozenset = frozenset()
    exactly: network.Exactly | None = None
    blank_strip: bool = False
    min_bananas: int = 0


class Sampled(NamedTuple):
    """An engine's grid for a seed: `status` is "found" with the network, or
    "infeasible" (no grid meets the conditions) or "timeout" with None."""

    status: str
    network: frozenset | None


class Classified(NamedTuple):
    """An engine's classification of a set of conditions, in the uniqueness
    check's words: "infeasible" for no grid, "unique" for exactly one,
    "not_unique" for more, "timeout" when the time limit was reached.
    `network` is the first grid found, or None when there is none."""

    status: str
    network: frozenset | None


def number_cells(rows, cols, blank_strip=False):
    """{number cell: (the kind it counts, the grid cells it counts over)},
    every row's then every column's, strip by strip."""
    lines = {}
    for k in range(1, strips(blank_strip) + 1):
        for r in range(rows):
            lines[r, -k] = (k - 1, [(r, c) for c in range(cols)])
        for c in range(cols):
            lines[-k, c] = (k - 1, [(r, c) for r in range(rows)])
    return lines


def values(net, rows, cols, blank_strip=False):
    """{cell: its value} for every cell of the board: the grid cells, then
    each row's and each column's number cells. Only for a network with no
    dead end."""
    kinds = network.kind_grid(net, rows, cols)
    row_numbers, col_numbers = network.outside_numbers(net, rows, cols)
    depth = strips(blank_strip)
    board = {
        (r, c): PIECE_VALUE[kinds[r * cols + c]]
        for r in range(rows)
        for c in range(cols)
    }
    for k in range(1, depth + 1):
        board.update({(r, -k): row_numbers[r][k - 1] for r in range(rows)})
        board.update({(-k, c): col_numbers[c][k - 1] for c in range(cols)})
    return board


def cell_name(cell):
    """A cell as the reasons name it: `r2c3` for a grid cell, `r2:turn` for
    row 2's turn number cell, `c3:cross` for column 3's cross number cell."""
    r, c = cell
    if r < 0:
        return f"c{c + 1}:{network.KIND_NAMES[-r - 1]}"
    if c < 0:
        return f"r{r + 1}:{network.KIND_NAMES[-c - 1]}"
    return f"r{r + 1}c{c + 1}"


def parse_cell(text):
    """The cell `cell_name` writes as `text`. Raises ValueError, naming what
    is wrong."""
    match = re.fullmatch(r"r([1-9][0-9]*)c([1-9][0-9]*)", text)
    if match:
        return int(match[1]) - 1, int(match[2]) - 1
    match = re.fullmatch(r"([rc])([1-9][0-9]*):([a-z]+)", text)
    if not match:
        raise ValueError(f"a cell is rKcK, rK:PIECE or cK:PIECE, got {text!r}")
    axis, number, name = match.groups()
    if name not in network.KIND_NAMES:
        raise ValueError(
            f"no piece named {name!r}: a number cell counts "
            f"{', '.join(network.KIND_NAMES)}"
        )
    strip = -network.KIND_NAMES.index(name) - 1
    return (int(number) - 1, strip) if axis == "r" else (strip, int(number) - 1)


def regions(board):
    """The board's regions, each a frozenset of cells: the orthogonally
    connected sets of cells whose values share a parity. A cell that is not
    on the board (an icon cell, the area off it) joins nothing, so it is a
    wall. In reading order of each region's first cell."""
    found = []
    seen = set()
    for start in sorted(board):
        if start in seen:
            continue
        parity = board[start] % 2
        region = set()
        stack = [start]
        while stack:
            cell = stack.pop()
            if cell in region or cell not in board or board[cell] % 2 != parity:
                continue
            region.add(cell)
            r, c = cell
            stack += [(r - 1, c), (r, c + 1), (r + 1, c), (r, c - 1)]
        seen |= region
        found.append(frozenset(region))
    return found


def bananas(board):
    """The board's banana regions: its regions of odd values, in `regions`'
    order."""
    return [region for region in regions(board) if board[min(region)] % 2]


def valid_circles(board):
    """The cells a circle could sit on, sorted: every cell, grid cell or
    number cell, whose value is the number of cells of its region."""
    return sorted(
        cell
        for region in regions(board)
        for cell in region
        if board[cell] == len(region)
    )


def _box(region):
    """(top, left, height, width) of the smallest box that holds the region."""
    top, left = (min(cell[i] for cell in region) for i in (0, 1))
    bottom, right = (max(cell[i] for cell in region) for i in (0, 1))
    return top, left, bottom - top + 1, right - left + 1


def failures(net, rows, cols, circles=(), blank_strip=False, *, min_bananas=0):
    """Every reason these edges and circles are not a hybrid grid, [] when
    they are one. `circles` are cells of the board. A set of edges that is no
    U-Bahn network fails on that alone; a network then answers for each
    region and each circle: an even region is a rectangle, an odd region is
    not, and a circled cell's value is its region's size. Last, a grid with
    fewer than `min_bananas` banana regions fails on their number."""
    broken = network.why_not_network(net, rows, cols)
    if broken:
        return [broken]
    board = values(net, rows, cols, blank_strip)
    found = regions(board)
    reasons = []
    for region in found:
        name = cell_name(min(region))
        top, left, height, width = _box(region)
        full = len(region) == height * width
        if board[min(region)] % 2:
            if full:
                reasons.append(f"banana at {name} is a {height}x{width} rectangle")
        elif top < 0 and left < 0:
            # The box reaches from one side's number cells to the other's, so
            # it holds the corner, where no cell is on the board.
            reasons.append(f"chocolate at {name} would need an icon cell")
        elif not full:
            reasons.append(
                f"chocolate at {name} is not a rectangle: "
                f"{len(region)} cells in a {height}x{width} box"
            )
    size = {cell: len(region) for region in found for cell in region}
    for cell in sorted(circles):
        if cell not in board:
            reasons.append(f"circle off the board: {cell}")
        elif board[cell] != size[cell]:
            reasons.append(
                f"circle at {cell_name(cell)}: value {board[cell]}, "
                f"region of {size[cell]} cells"
            )
    count = len(bananas(board))
    if count < min_bananas:
        reasons.append(
            f"{count} banana region{'' if count == 1 else 's'}, "
            f"fewer than the {min_bananas} asked for"
        )
    return reasons


def why_not_hybrid(net, rows, cols, circles=(), blank_strip=False, *, min_bananas=0):
    """Why these edges and circles are not a hybrid grid, or "" when they
    are one: the first of `failures`."""
    reasons = failures(net, rows, cols, circles, blank_strip, min_bananas=min_bananas)
    return next(iter(reasons), "")


def icon_arms(cell):
    """The (north, east, south, west) arms of the piece the icon cell at
    `cell` shows, or None when it is no icon cell: the head of a strip, in
    the strip's last row or column before the grid. The blank strip's icon
    has no arm."""
    r, c = cell
    if -1 not in (r, c) or max(r, c) >= 0:
        return None
    name = network.KIND_NAMES[-min(r, c) - 1]
    if name == "blank":
        return (0, 0, 0, 0)
    right, down, left, up = penpa.ICONS[name][0 if c == -1 else 1]
    return (up, right, down, left)


def _icon(cell):
    """What the icon cell at `cell` shows, or "" when it is none."""
    cell_arms = icon_arms(cell)
    if cell_arms is None:
        return ""
    return network.DRAWN[cell_arms] if any(cell_arms) else penpa.BLANK_ICON


def drawing(net, rows, cols, circles=(), blank_strip=False):
    """The board as one string per board row: a number cell as its value, a
    grid cell as its piece, an icon cell as the piece its strip counts, and a
    circled cell in brackets. Only for a network with no dead end."""
    board = values(net, rows, cols, blank_strip)
    depth = strips(blank_strip)
    width = max(len(str(v)) for v in board.values())
    circled = set(circles)

    def drawn(cell):
        left, right = "()" if cell in circled else "  "
        if min(cell) < 0:
            text = str(board[cell]) if cell in board else _icon(cell)
            return f"{left}{text:^{width}}{right}"
        _, east, _, west = cell_arms = network.arms(net, cell)
        if cell not in circled:
            left, right = " ─"[west], " ─"[east]
        piece = network.DRAWN[cell_arms]
        return f"{left}{piece:{' ─'[west]}>{width}}{right}"

    return [
        "".join(drawn((r, c)) for c in range(-depth, cols)).rstrip()
        for r in range(-depth, rows)
    ]

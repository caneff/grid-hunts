"""The U-Bahn rules read straight off a network, with no solver (#773).

A network is a frozenset of edges. An edge joins the centres of two
orthogonally adjacent cells and is written `((r, c), (r2, c2))`, the earlier
cell first. A cell's arms are the edges at it that are in the network; the
arms give its kind: one of the four pieces, or blank for no arm.
`why_not_network` is the rule check `verify` and the brute-force test run.
`model.py` takes the board's geometry (`all_edges`, `arm_edges`) and the
kinds' numbering from here and states the rules itself.

The rules and their sources: docs/research/2026-10-10-u-bahn-cpsat-finder.md.
"""

import re
from typing import NamedTuple

# What a cell can be, in the order a row's or column's outside numbers are
# given: the four pieces, then blank. This is the one statement of the order.
KIND_NAMES = ("turn", "straight", "branch", "cross", "blank")
TURN, STRAIGHT, BRANCH, CROSS, BLANK = KINDS = range(len(KIND_NAMES))

# A cell's kind drawn from its (north, east, south, west) arms.
_DRAWN = {
    (0, 0, 0, 0): " ",
    (1, 0, 1, 0): "│",
    (0, 1, 0, 1): "─",
    (1, 1, 0, 0): "└",
    (0, 1, 1, 0): "┌",
    (0, 0, 1, 1): "┐",
    (1, 0, 0, 1): "┘",
    (0, 1, 1, 1): "┬",
    (1, 0, 1, 1): "┤",
    (1, 1, 0, 1): "┴",
    (1, 1, 1, 0): "├",
    (1, 1, 1, 1): "┼",
}


def all_edges(rows, cols):
    """Every edge of the board: the horizontal ones row by row, then the
    vertical ones."""
    horizontal = [((r, c), (r, c + 1)) for r in range(rows) for c in range(cols - 1)]
    vertical = [((r, c), (r + 1, c)) for r in range(rows - 1) for c in range(cols)]
    return horizontal + vertical


def arm_edges(cell):
    """The four edges a cell's arms could use: north, east, south, west. On
    the border some of them leave the board and are no edge of it."""
    r, c = cell
    return (
        ((r - 1, c), (r, c)),
        ((r, c), (r, c + 1)),
        ((r, c), (r + 1, c)),
        ((r, c - 1), (r, c)),
    )


def arms(network, cell):
    """Which of the cell's (north, east, south, west) arms the network has."""
    return tuple(int(e in network) for e in arm_edges(cell))


def kind_of(cell_arms):
    """The kind of a cell with these arms: its piece, BLANK for no arm, or
    None for a dead end."""
    north, east, south, west = cell_arms
    count = north + east + south + west
    if count == 2:
        return STRAIGHT if north == south else TURN
    return {0: BLANK, 1: None, 3: BRANCH, 4: CROSS}[count]


def kind_grid(network, rows, cols):
    """The kind of every cell, flat and row by row; None marks a dead end."""
    return tuple(
        kind_of(arms(network, (r, c))) for r in range(rows) for c in range(cols)
    )


def why_not_network(network, rows, cols):
    """Why these edges are not a U-Bahn network, or "" when they are one:
    every edge on the board, at least one edge, no dead end, all of it
    connected."""
    stray = set(network) - set(all_edges(rows, cols))
    if stray:
        return f"edge off the board: {sorted(stray)[0]}"
    if not network:
        return "no edge is on"
    kinds = kind_grid(network, rows, cols)
    if None in kinds:
        r, c = divmod(kinds.index(None), cols)
        return f"dead end at r{r + 1}c{c + 1}"
    reached = set()
    stack = [next(iter(network))[0]]
    while stack:
        cell = stack.pop()
        if cell in reached:
            continue
        reached.add(cell)
        for edge in arm_edges(cell):
            if edge in network:
                stack.extend(edge)
    used = sum(1 for k in kinds if k != BLANK)
    if len(reached) != used:
        return f"not connected: {len(reached)} of {used} used cells reached"
    return ""


def outside_numbers(network, rows, cols):
    """(row numbers, column numbers): for each row, then each column, how
    many cells of each kind it holds, in `KINDS` order. Only for a network
    with no dead end."""
    kinds = kind_grid(network, rows, cols)

    def count(cells):
        held = [kinds[r * cols + c] for r, c in cells]
        return tuple(held.count(k) for k in KINDS)

    return (
        tuple(count([(r, c) for c in range(cols)]) for r in range(rows)),
        tuple(count([(r, c) for r in range(rows)]) for c in range(cols)),
    )


def drawing(network, rows, cols):
    """The network as one string per row, a box-drawing character per cell."""
    return [
        "".join(_DRAWN[arms(network, (r, c))] for c in range(cols)) for r in range(rows)
    ]


class Exactly(NamedTuple):
    """The condition "exactly `count` cells of `kind` in row or column
    `index`": `axis` is "r" or "c", `index` counts from 0."""

    count: int
    kind: int
    axis: str
    index: int

    def on_board(self, rows, cols):
        """Whether the board has the row or column the condition names."""
        return self.index < (rows if self.axis == "r" else cols)

    def cells(self, rows, cols):
        """The cells of the row or column the condition names."""
        if self.axis == "r":
            return [(self.index, c) for c in range(cols)]
        return [(r, self.index) for r in range(rows)]

    def holds(self, network, rows, cols):
        """Whether the network meets the condition, by counting its cells.
        Only for a condition that is on the board."""
        held = [kind_of(arms(network, cell)) for cell in self.cells(rows, cols)]
        return held.count(self.kind) == self.count

    @classmethod
    def parse(cls, text):
        """The condition written `N:PIECE:rK` or `N:PIECE:cK`, as in
        `2:cross:r2` or `3:blank:c1`. Raises ValueError, naming what is
        wrong."""
        match = re.fullmatch(r"([0-9]+):([a-z]+):([rc])([1-9][0-9]*)", text)
        if not match:
            raise ValueError(f"a condition is N:PIECE:rK or N:PIECE:cK, got {text!r}")
        count, name, axis, number = match.groups()
        if name not in KIND_NAMES:
            raise ValueError(
                f"no piece named {name!r}: a condition counts {', '.join(KIND_NAMES)}"
            )
        return cls(int(count), KIND_NAMES.index(name), axis, int(number) - 1)

    def text(self):
        """The condition as `parse` reads it."""
        return f"{self.count}:{KIND_NAMES[self.kind]}:{self.axis}{self.index + 1}"

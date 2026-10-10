"""The CP-SAT model of a U-Bahn network (#773).

One boolean per edge is the decision; everything else is channelled from the
edges. Per cell, one table over its arms lists the 12 legal arm patterns and
the piece each one makes (blank for no arm), so a dead end has no row. The
pieces and blank cells of a row or column sum to its outside numbers. Connectivity has two encodings: `flow`
(single-commodity flow, what the finder searches with) and `tree` (a spanning
tree with level labels, the independent check). Both hang off the same root,
the first used cell in reading order.

Flows and trees are not unique per network, so the model has many solutions
for one network: count networks by solve, forbid on the edge variables,
re-solve (`uniqueness`), never by `enumerate_all_solutions`.

    docs/research/2026-10-10-u-bahn-cpsat-finder.md, section 4
"""

import sys
from pathlib import Path
from typing import NamedTuple

from ortools.sat.python import cp_model

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
# isort: split
from network import (
    BLANK,
    BRANCH,
    CROSS,
    KINDS,
    STRAIGHT,
    TURN,
    all_edges,
    arms_on_board,
    rows_and_columns,
)
from uniqueness import check_uniqueness

# The 12 legal (north, east, south, west) arm patterns of a cell and the kind
# each makes. The 4 patterns with one arm, the dead ends, are left out.
PATTERNS = (
    ((0, 0, 0, 0), BLANK),
    ((1, 0, 1, 0), STRAIGHT),
    ((0, 1, 0, 1), STRAIGHT),
    ((1, 1, 0, 0), TURN),
    ((0, 1, 1, 0), TURN),
    ((0, 0, 1, 1), TURN),
    ((1, 0, 0, 1), TURN),
    ((0, 1, 1, 1), BRANCH),
    ((1, 0, 1, 1), BRANCH),
    ((1, 1, 0, 1), BRANCH),
    ((1, 1, 1, 0), BRANCH),
    ((1, 1, 1, 1), CROSS),
)


class Built(NamedTuple):
    """A built model and its edge variables, keyed by edge."""

    m: cp_model.CpModel
    edge: dict


def _add_pieces(m, edge, cells):
    """Channel each cell's kind from its arms. Returns `kind[cell, k]`
    booleans and `used[cell]`, the cell is not blank. An arm that would leave the board has no variable, so only the
    patterns without it are listed."""
    kind, used = {}, {}
    for cell in cells:
        on_board = arms_on_board(cell, edge)
        for k in KINDS:
            kind[cell, k] = m.new_bool_var(f"k{cell}_{k}")
        used[cell] = kind[cell, BLANK].Not()
        m.add_allowed_assignments(
            [*on_board.values()] + [kind[cell, k] for k in KINDS],
            [
                tuple(pattern[i] for i in on_board)
                + tuple(int(k == made) for k in KINDS)
                for pattern, made in PATTERNS
                if sum(pattern) == sum(pattern[i] for i in on_board)
            ],
        )
    return kind, used


def _add_root(m, cells, used):
    """`root[cell]`: exactly one cell, used, with no used cell before it. A
    function of the network, so the root adds no choice of its own; it also
    makes the network non-empty."""
    root = {cell: m.new_bool_var(f"root{cell}") for cell in cells}
    m.add_exactly_one(root.values())
    for i, cell in enumerate(cells):
        m.add_implication(root[cell], used[cell])
        for earlier in cells[:i]:
            m.add_implication(root[cell], used[earlier].Not())
    return root


def _add_flow(m, edge, cells, used, root, cap):
    """The root supplies one unit of flow per used cell; each used cell
    absorbs one; flow crosses only edges that are on. `cap` bounds the number
    of used cells."""
    inflow = {cell: [] for cell in cells}
    outflow = {cell: [] for cell in cells}
    for (a, b), on in edge.items():
        for source, sink in ((a, b), (b, a)):
            f = m.new_int_var(0, cap, f"f{source}_{sink}")
            m.add(f <= cap * on)
            outflow[source].append(f)
            inflow[sink].append(f)
    for cell in cells:
        supply = m.new_int_var(0, cap, f"s{cell}")
        m.add(supply <= cap * root[cell])
        m.add(sum(inflow[cell]) + supply == sum(outflow[cell]) + used[cell])


def _add_tree(m, edge, cells, used, root, cap):
    """Every used cell but the root has exactly one parent across an edge
    that is on, one level nearer the root, which sits at level 0."""
    level = {cell: m.new_int_var(0, cap - 1, f"l{cell}") for cell in cells}
    parents = {cell: [] for cell in cells}
    for (a, b), on in edge.items():
        for child, parent in ((a, b), (b, a)):
            p = m.new_bool_var(f"p{child}_{parent}")
            m.add_implication(p, on)
            m.add(level[child] == level[parent] + 1).only_enforce_if(p)
            parents[child].append(p)
    for cell in cells:
        m.add(level[cell] == 0).only_enforce_if(root[cell])
        m.add(sum(parents[cell]) + root[cell] == used[cell])


def build(rows, cols, connectivity, *, exactly=None, numbers=None):
    """The model of every U-Bahn network on a `rows` x `cols` board.

    `connectivity` is "flow" or "tree". `exactly` is a `network.Exactly`
    condition to hold. `numbers` is a full set of outside numbers, as
    `network.outside_numbers` returns it, to hold.
    """
    m = cp_model.CpModel()
    edge = {e: m.new_bool_var(f"e{e}") for e in all_edges(rows, cols)}
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    kind, used = _add_pieces(m, edge, cells)

    cap = rows * cols
    if exactly is not None:
        m.add(
            sum(kind[cell, exactly.kind] for cell in exactly.cells(rows, cols))
            == exactly.count
        )
    if numbers is not None:
        for held, counts in rows_and_columns(rows, cols, numbers):
            for k, count in zip(KINDS, counts, strict=True):
                m.add(sum(kind[cell, k] for cell in held) == count)
        # The numbers fix how many cells are used: size the flow to that.
        cap = rows * cols - sum(counts[BLANK] for counts in numbers[0])

    root = _add_root(m, cells, used)
    add_connectivity = {"flow": _add_flow, "tree": _add_tree}[connectivity]
    add_connectivity(m, edge, cells, used, root, cap)
    return Built(m, edge)


def uniqueness(rows, cols, numbers, connectivity, *, time_limit, workers):
    """Whether one full set of outside numbers has exactly one network.

    Returns `(status, network)`: `status` is `check_uniqueness`'s ("unique",
    "not_unique", "infeasible", "timeout", "invalid") and `network` is the
    first network found, or None when there is none. A timeout is never
    unique.
    """
    built = build(rows, cols, connectivity, numbers=numbers)
    edges = list(built.edge)
    result = check_uniqueness(
        built.m,
        [built.edge[e] for e in edges],
        time_limit=time_limit,
        workers=workers,
    )
    if result.first is None:
        return result.status, None
    found = frozenset(e for e, on in zip(edges, result.first, strict=True) if on)
    return result.status, found

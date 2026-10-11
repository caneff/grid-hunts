"""The CP-SAT model of the hybrid (#783): U-Bahn with Choco-Banana over the
grid cells and the number cells, built from the conditions.

It is the plain model (`model.py`, flow connectivity, the piece-count
condition) with the hybrid's rules stated on top of its `kind` booleans. No
outside number is given: each number cell's value is the count the network
makes it.

- **Parity.** A grid cell is odd when it is a turn or a branch; a number cell
  is odd when its count is, one XOR over its row or column.
- **Chocolate.** No 2x2 window holds exactly three even cells, a cell off
  the board (an icon cell, the corner) counting as not even. Three even
  cells of a window are one region with a notch, and a region with no such
  window is a rectangle.
- **Banana.** One clause per rectangle of board cells: all of it odd with
  every bordering cell even is forbidden.
- **Circle.** The circled cell's region is stated outright: a membership
  boolean per cell near it, closed under same-parity neighbours, connected
  by a flow from the circled cell, and as many as the cell's value. The
  same statement serves a circle in a chocolate and in a banana; the two
  rules above shape the region.
- **At least N banana regions** (#792). Every odd cell takes one of N
  labels, two odd cells side by side take the same one, and every label is
  taken: a label is the same all over a region, so N labels are N regions.

This is the `cpsat` engine of `hybrid_finder.py`. An engine offers two calls
over a `hybrid.Conditions`: `grid` (a grid for a seed, a `hybrid.Sampled`)
and `classify` (a `hybrid.Classified`).

Flows are not unique per grid, so grids are counted by solve, forbid on the
edge variables, re-solve, as in `model.py`.
"""

import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hybrid
import model
from network import KINDS


def _neighbours(cell):
    r, c = cell
    return ((r - 1, c), (r, c + 1), (r + 1, c), (r, c - 1))


def _add_parity(m, kind, conditions):
    """`value[cell]`, a linear expression, and `odd[cell]`, a boolean, for
    every cell of the board."""
    rows, cols = conditions.rows, conditions.cols
    value, odd = {}, {}
    for cell in product(range(rows), range(cols)):
        value[cell] = sum(hybrid.PIECE_VALUE[k] * kind[cell, k] for k in KINDS)
        odd[cell] = m.new_bool_var(f"odd{cell}")
        m.add(
            odd[cell] == sum(kind[cell, k] for k in KINDS if hybrid.PIECE_VALUE[k] % 2)
        )
    lines = hybrid.number_cells(rows, cols, conditions.blank_strip)
    for cell, (k, held) in lines.items():
        counted = [kind[c, k] for c in held]
        value[cell] = sum(counted)
        odd[cell] = m.new_bool_var(f"odd{cell}")
        # An odd number of these is true: the count's parity is `odd`.
        m.add_bool_xor([*counted, odd[cell].Not()])
    return value, odd


def _add_chocolate(m, odd):
    """No 2x2 window with exactly three even cells."""
    top, left = (min(cell[i] for cell in odd) for i in (0, 1))
    bottom, right = (max(cell[i] for cell in odd) for i in (0, 1))
    for r, c in product(range(top, bottom), range(left, right)):
        window = [(r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)]
        for lone in window:
            three = [cell for cell in window if cell != lone]
            if all(cell in odd for cell in three):
                m.add_bool_or(
                    [odd[cell] for cell in three]
                    + ([odd[lone].Not()] if lone in odd else [])
                )


def _add_banana(m, odd):
    """No rectangle of odd cells with every bordering cell even."""
    top, left = (min(cell[i] for cell in odd) for i in (0, 1))
    bottom, right = (max(cell[i] for cell in odd) for i in (0, 1))
    for r, c in product(range(top, bottom + 1), range(left, right + 1)):
        for r2, c2 in product(range(r, bottom + 1), range(c, right + 1)):
            inside = set(product(range(r, r2 + 1), range(c, c2 + 1)))
            if not all(cell in odd for cell in inside):
                continue
            border = {
                near
                for cell in inside
                for near in _neighbours(cell)
                if near in odd and near not in inside
            }
            m.add_bool_or(
                [odd[cell].Not() for cell in sorted(inside)]
                + [odd[cell] for cell in sorted(border)]
            )


def _add_circle(m, value, odd, circle, largest):
    """The circled cell's value is the size of its region. `largest` bounds
    the value, so only cells within `largest - 1` steps can be in the region."""
    steps = {circle: 0}
    queue = [circle]
    for cell in queue:
        if steps[cell] == largest - 1:
            continue
        for near in _neighbours(cell):
            if near in odd and near not in steps:
                steps[near] = steps[cell] + 1
                queue.append(near)
    inside = {cell: m.new_bool_var(f"in{circle}_{cell}") for cell in steps}
    m.add(inside[circle] == 1)
    m.add(sum(inside.values()) == value[circle])
    mine = odd[circle]
    for cell, member in inside.items():
        # A member shares the circled cell's parity.
        m.add_bool_or([member.Not(), mine.Not(), odd[cell]])
        m.add_bool_or([member.Not(), mine, odd[cell].Not()])
        # A member's neighbour of that parity is a member. One too far to
        # have a boolean would make the region larger than any value.
        for near in _neighbours(cell):
            if near in odd:
                joins = [inside[near]] if near in inside else []
                m.add_bool_or([member.Not(), mine.Not(), odd[near].Not(), *joins])
                m.add_bool_or([member.Not(), mine, odd[near], *joins])
    # Connected: the circled cell supplies one unit of flow per member, each
    # member absorbs one, and flow passes only between members.
    cap = largest
    inflow = {cell: [] for cell in inside}
    outflow = {cell: [] for cell in inside}
    for source in inside:
        for sink in _neighbours(source):
            if sink in inside:
                f = m.new_int_var(0, cap, f"g{circle}_{source}_{sink}")
                m.add(f <= cap * inside[source])
                m.add(f <= cap * inside[sink])
                outflow[source].append(f)
                inflow[sink].append(f)
    supply = m.new_int_var(0, cap, f"t{circle}")
    for cell, member in inside.items():
        m.add(
            sum(inflow[cell]) + (supply if cell == circle else 0)
            == sum(outflow[cell]) + member
        )


def _add_bananas(m, odd, wanted):
    """At least `wanted` regions of odd cells. A grid with that many has the
    labelling asked for, a region past the `wanted`-th taking any label."""
    label = {
        (cell, k): m.new_bool_var(f"label{cell}_{k}")
        for cell in odd
        for k in range(wanted)
    }
    for cell in odd:
        # An odd cell has one label, an even cell none.
        m.add(sum(label[cell, k] for k in range(wanted)) == odd[cell])
        for near in _neighbours(cell):
            if near in odd:
                for k in range(wanted):
                    m.add_bool_or(
                        [label[cell, k].Not(), odd[near].Not(), label[near, k]]
                    )
    for k in range(wanted):
        m.add_bool_or([label[cell, k] for cell in odd])


def build(conditions):
    """The model of every hybrid grid that meets the conditions, as a
    `model.Built`. Raises ValueError on a circle that is off the board."""
    rows, cols, circles = conditions.rows, conditions.cols, conditions.circles
    built = model.build(rows, cols, "flow", exactly=conditions.exactly)
    value, odd = _add_parity(built.m, built.kind, conditions)
    for circle in sorted(circles):
        if circle not in odd:
            raise ValueError(f"circle off the board: {circle}")
    _add_chocolate(built.m, odd)
    _add_banana(built.m, odd)
    lines = hybrid.number_cells(rows, cols, conditions.blank_strip)
    for circle in sorted(circles):
        # A piece is worth 4 at most; a number cell counts a row or column.
        largest = (
            len(lines[circle][1])
            if circle in lines
            else max(hybrid.PIECE_VALUE.values())
        )
        _add_circle(built.m, value, odd, circle, largest)
    if conditions.min_bananas:
        _add_bananas(built.m, odd, conditions.min_bananas)
    return built


def grid(conditions, rng, *, time_limit):
    """One grid that meets the conditions, steered by `rng`: the same grid on
    every run of a seed. A limit of zero or less is a timeout."""
    if time_limit <= 0:
        return hybrid.Sampled("timeout", None)
    return hybrid.Sampled(*model.sample(build(conditions), rng, time_limit=time_limit))


def classify(conditions, *, time_limit, workers):
    """Whether the conditions have no grid, exactly one, or more than one.
    A time limit reached is "timeout", never one of the other three; a limit
    of zero or less is reached before any solve."""
    if time_limit <= 0:
        return hybrid.Classified("timeout", None)
    status, found = model.network_uniqueness(
        build(conditions), time_limit=time_limit, workers=workers
    )
    if status == "invalid":
        raise RuntimeError("the hybrid model is invalid")
    return hybrid.Classified(status, found)

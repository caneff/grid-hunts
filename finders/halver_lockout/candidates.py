"""Candidate lockout lines for the hunt (spec #52, #55): the separating-line
walk on the shared drawing rules (`finders/halver/halver_shapes.py`), which
this module re-exports, so the hunt reads them all from here.

`shape_violation(path, lines)` is the shared shape check, its refusals
naming a line's ends as diamonds.

`separating_paths(target, second, lines, max_cells)` lists every path of at
most `max_cells` cells that `shape_violation` accepts, that holds in `target`
and that fails in `second` under `rules.line_holds`, shortest first, each
line once (a path and its reverse are one line). It walks out from each
diamond and keeps a body only while some closing diamond could still put
every target value on it outside the diamonds' range, so it never builds a
path the target already breaks.
"""

from functools import partial

import rules

# isort: split
import halver_shapes
from halver_shapes import free_cell_count, line_of, new_cells, no_space, path_of

__all__ = [
    "free_cell_count",
    "line_of",
    "new_cells",
    "no_space",
    "path_of",
    "separating_paths",
    "shape_violation",
]

shape_violation = partial(halver_shapes.shape_violation, end="diamond")


def separating_paths(target, second, lines, max_cells, gap=rules.GAP):
    """Lockout lines of at most `max_cells` cells that hold in `target` and fail in `second`,
    shortest first, each line once; `gap` is the least difference between a line's diamonds."""
    # The state is (below, above): the largest body value under the first
    # diamond's and the smallest over it. `least` is the diamonds' least
    # difference, in doubled values.
    least = 2 * gap

    def initial(lowest, highest):
        return lowest - 1, highest + 1

    def closes(start, v, state):
        below, above = state
        return (v - start >= least and v < above) or (start - v >= least and v > below)

    def extend(start, v, state, lowest, highest):
        below, above = state
        new_below = max(below, v) if v < start else below
        new_above = min(above, v) if v > start else above
        # The closing diamond goes over the first, under every body value
        # above it, or under the first, over every body value below it.
        over = start + least <= min(highest, new_above - 1)
        under = start - least >= max(lowest, new_below + 1)
        return (new_below, new_above) if over or under else None

    return halver_shapes.separating_paths(
        target,
        second,
        lines,
        max_cells,
        holds=partial(rules.line_holds, gap=gap),
        initial=initial,
        closes=closes,
        extend=extend,
    )

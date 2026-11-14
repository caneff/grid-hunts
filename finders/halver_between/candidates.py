"""Candidate between lines for the hunt (spec #39, #41): the separating-line
walk on the shared drawing rules (`finders/halver/halver_shapes.py`), which
this module re-exports, so the hunt reads them all from here.

`shape_violation(path, lines)` is the shared shape check, its refusals
naming a line's ends as circles.

`separating_paths(target, second, lines, max_cells)` lists every path of at
most `max_cells` cells that `shape_violation` accepts, that holds in `target`
and that fails in `second`, shortest first, each line once (a path and its
reverse are one line). It walks out from each circle and keeps a body only
while its target doubled values all sit on one side of that circle, so it never
builds a path the target already breaks.
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

shape_violation = partial(halver_shapes.shape_violation, end="circle")


# The state is [low, high], the span of the body's target doubled values.
def _initial(lowest, highest):
    return highest + 1, lowest - 1


def _closes(start, v, state):
    low, high = state
    return min(start, v) < low and high < max(start, v)


def _extend(start, v, state, lowest, highest):
    low, high = min(state[0], v), max(state[1], v)
    if not (high < start or low > start):
        return None  # body doubled values straddle the first circle
    if low <= lowest or high >= highest:
        return None  # no circle's doubled value lies beyond this body
    return low, high


def separating_paths(target, second, lines, max_cells):
    """Every line of at most `max_cells` cells that holds in `target` and fails
    in `second`, shortest first; see the module docstring."""
    return halver_shapes.separating_paths(
        target,
        second,
        lines,
        max_cells,
        holds=rules.line_holds,
        initial=_initial,
        closes=_closes,
        extend=_extend,
    )

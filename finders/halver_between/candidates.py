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
from halver_shapes import (
    STEPS,
    crossing,
    free_cell_count,
    line_of,
    new_cells,
    no_space,
    occupied,
    path_of,
)

__all__ = [
    "free_cell_count",
    "line_of",
    "new_cells",
    "no_space",
    "path_of",
    "separating_paths",
    "shape_violation",
]

MIN_DOUBLED, MAX_DOUBLED = 1, 18  # a halved 1, a normal 9

shape_violation = partial(halver_shapes.shape_violation, end="circle")


def separating_paths(target, second, lines, max_cells):
    on_line, bodies, diagonals = occupied(lines)
    n = len(target.digits)
    cells = [(r, c) for r in range(n) for c in range(n)]
    doubled = {cell: target.doubled(cell) for cell in cells}
    found = []

    def step_ok(p, q, own_diagonals):
        cross = crossing(p, q)
        return cross is None or (cross not in diagonals and cross not in own_diagonals)

    def walk(path, low, high, own_diagonals):
        """Extend `path` (circle first, body after) whose body's target
        doubled values span [low, high]; `own_diagonals` holds its diagonal
        steps."""
        last = path[-1]
        start = doubled[path[0]]
        for dr, dc in STEPS:
            q = (last[0] + dr, last[1] + dc)
            if not (0 <= q[0] < n and 0 <= q[1] < n) or q in path:
                continue
            if not step_ok(last, q, own_diagonals):
                continue
            step = frozenset((last, q))
            diagonals_after = (
                own_diagonals | {step} if crossing(last, q) else own_diagonals
            )
            v = doubled[q]
            # q as the closing circle.
            if (
                len(path) >= 2
                and q not in bodies
                and path[0] < q
                and min(start, v) < low
                and high < max(start, v)
            ):
                candidate = (*path, q)
                if not rules.line_holds(second, line_of(candidate)):
                    found.append(candidate)
            # q as one more body cell, leaving room for the closing circle.
            if len(path) + 2 > max_cells or q in on_line or v == start:
                continue
            new_low, new_high = min(low, v), max(high, v)
            if not (new_high < start or new_low > start):
                continue  # body doubled values straddle the first circle
            if new_low <= MIN_DOUBLED or new_high >= MAX_DOUBLED:
                continue  # no circle's doubled value lies beyond this body
            walk((*path, q), new_low, new_high, diagonals_after)

    for a in cells:
        if a not in bodies:
            walk((a,), MAX_DOUBLED + 1, MIN_DOUBLED - 1, frozenset())
    found.sort(key=len)
    return found

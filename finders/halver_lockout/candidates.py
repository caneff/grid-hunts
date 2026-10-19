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

shape_violation = partial(halver_shapes.shape_violation, end="diamond")


def separating_paths(target, second, lines, max_cells, gap=rules.GAP):
    on_line, bodies, diagonals = occupied(lines)
    n = len(target.digits)
    cells = [(r, c) for r in range(n) for c in range(n)]
    doubled = {cell: target.doubled(cell) for cell in cells}
    spread = 2 * gap  # the diamonds' least difference, in doubled values
    lowest, highest = 1, 2 * n  # a halved 1, a normal n
    found = []

    def step_ok(p, q, own_diagonals):
        cross = crossing(p, q)
        return cross is None or (cross not in diagonals and cross not in own_diagonals)

    def walk(path, below, above, own_diagonals):
        """Extend `path` (diamond first, body after). `below` is the largest
        body value under the first diamond's, `above` the smallest over it;
        `own_diagonals` holds the path's diagonal steps."""
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
            # q as the closing diamond: far enough from the first, with every
            # body value beyond it on its side.
            if (
                len(path) >= 2
                and q not in bodies
                and path[0] < q
                and (
                    (v - start >= spread and v < above)
                    or (start - v >= spread and v > below)
                )
            ):
                candidate = (*path, q)
                if not rules.line_holds(second, line_of(candidate), gap=gap):
                    found.append(candidate)
            # q as one more body cell, leaving room for the closing diamond.
            if len(path) + 2 > max_cells or q in on_line or v == start:
                continue
            new_below = max(below, v) if v < start else below
            new_above = min(above, v) if v > start else above
            # The closing diamond goes over the first, under every body value
            # above it, or under the first, over every body value below it.
            over = start + spread <= min(highest, new_above - 1)
            under = start - spread >= max(lowest, new_below + 1)
            if over or under:
                walk((*path, q), new_below, new_above, diagonals_after)

    for a in cells:
        if a not in bodies:
            walk((a,), lowest - 1, highest + 1, frozenset())
    found.sort(key=len)
    return found

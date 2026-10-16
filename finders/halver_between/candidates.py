"""Candidate between lines for the hunt (spec #39, #41): Chris's shape rules
(Q8), and the walk that lists every line separating two solutions.

A path is a tuple of (row, column) cells from 0: circle, body cells in order,
circle. `shape_violation(path, lines)` reads one path against the lines
already drawn and returns None when it may be drawn, or the first rule it
breaks:

- every step is a king step, and no cell is visited twice;
- there is at least one body cell;
- a body cell is on no other line, as body or circle;
- a circle is on no other line's body (sharing a circle is fine);
- no step crosses another line's step, or one of its own, diagonally (the two
  diagonals of one 2x2).

`separating_paths(target, second, lines, max_cells)` lists every path of at
most `max_cells` cells that `shape_violation` accepts, that holds in `target`
and that fails in `second`, shortest first, each line once (a path and its
reverse are one line). It walks out from each circle and keeps a body only
while its target doubled values all sit on one side of that circle, so it never
builds a path the target already breaks.

`new_cells`, `free_cell_count` and `no_space` count the space a line takes
and what is left: cells, not solver time, are what runs out (truths note,
section 6).
"""

import itertools

import rules

STEPS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]
MIN_DOUBLED, MAX_DOUBLED = 1, 18  # a halved 1, a normal 9


def path_of(line):
    return (line.a, *line.body, line.b)


def line_of(path):
    return rules.Line(path[0], tuple(path[1:-1]), path[-1])


def _crossing(p, q):
    """The other diagonal of the 2x2 a diagonal step p -> q cuts, or None
    for an orthogonal step."""
    if p[0] == q[0] or p[1] == q[1]:
        return None
    return frozenset(((p[0], q[1]), (q[0], p[1])))


def _occupied(lines):
    """(every cell on a line, every body cell, each diagonal step's cells ->
    the line it belongs to)."""
    on_line, bodies, diagonals = set(), set(), {}
    for line in lines:
        cells = path_of(line)
        on_line.update(cells)
        bodies.update(line.body)
        for p, q in itertools.pairwise(cells):
            if _crossing(p, q) is not None:
                diagonals[frozenset((p, q))] = line
    return on_line, bodies, diagonals


def _king(p, q):
    return p != q and abs(p[0] - q[0]) <= 1 and abs(p[1] - q[1]) <= 1


def shape_violation(path, lines):
    seen = set()
    for cell in path:
        if cell in seen:
            return f"revisits {rules.cell_name(cell)}"
        seen.add(cell)
    steps = list(itertools.pairwise(path))
    for p, q in steps:
        if not _king(p, q):
            return f"{rules.cell_name(p)} -> {rules.cell_name(q)} is not a king step"
    if len(path) < 3:
        return "no body cell"
    on_line, bodies, diagonals = _occupied(lines)
    for cell in path[1:-1]:
        if cell in on_line:
            return f"body cell {rules.cell_name(cell)} is already on a line"
    for cell in (path[0], path[-1]):
        if cell in bodies:
            return f"circle {rules.cell_name(cell)} is another line's body cell"
    own = {frozenset(step) for step in steps if _crossing(*step) is not None}
    for p, q in steps:
        cross = _crossing(p, q)
        if cross is None:
            continue
        if cross in diagonals:
            return (
                f"crosses line {rules.line_name(diagonals[cross])} diagonally "
                f"at {rules.cell_name(p)} -> {rules.cell_name(q)}"
            )
        if cross in own:
            return f"crosses itself at {rules.cell_name(p)} -> {rules.cell_name(q)}"
    return None


def new_cells(path, lines):
    """How many cells drawing `path` takes from the cells a later body could
    use: its body cells, and each circle that is on no line yet."""
    on_line = _occupied(lines)[0]
    return len(path) - 2 + sum(c not in on_line for c in (path[0], path[-1]))


def free_cell_count(lines, n):
    """How many cells of an n x n board are on no line, so could still be a
    body cell."""
    return n * n - len(_occupied(lines)[0])


def no_space(target, second, lines):
    """True when every cell whose value differs between `target` and
    `second` is a body cell of a drawn line, so no new line can tell them
    apart."""
    bodies = _occupied(lines)[1]
    n = len(target.digits)
    return all(
        (r, c) in bodies
        for r in range(n)
        for c in range(n)
        if target.doubled((r, c)) != second.doubled((r, c))
    )


def separating_paths(target, second, lines, max_cells):
    on_line, bodies, diagonals = _occupied(lines)
    n = len(target.digits)
    cells = [(r, c) for r in range(n) for c in range(n)]
    doubled = {cell: target.doubled(cell) for cell in cells}
    found = []

    def step_ok(p, q, own_diagonals):
        cross = _crossing(p, q)
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
                own_diagonals | {step} if _crossing(last, q) else own_diagonals
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

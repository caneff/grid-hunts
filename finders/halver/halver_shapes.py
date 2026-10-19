"""The drawing rules every line type on halver cells shares (spec #39 Q8,
spec #52), and the cell counts a hunt ranks candidate lines by. Each line
type's candidate module (`halver_between/candidates.py`,
`halver_lockout/candidates.py`) re-exports these and adds its own
separating-line walk.

A path is a tuple of (row, column) cells from 0: an end, body cells in order,
the other end. The ends are a between line's circles and a lockout line's
diamonds; `end` names them in a refusal. `shape_violation(path, lines, end)`
reads one path against the lines already drawn and returns None when it may
be drawn, or the first rule it breaks:

- every step is a king step, and no cell is visited twice;
- there is at least one body cell;
- a body cell is on no other line, as body or end;
- an end is on no other line's body (sharing an end is fine);
- no step crosses another line's step, or one of its own, diagonally (the two
  diagonals of one 2x2).

`new_cells`, `free_cell_count` and `no_space` count the space a line takes
and what is left: cells, not solver time, are what runs out (halver_between
truths note, section 6).
"""

import itertools

from halver_rules import Line, cell_name, line_name

STEPS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]


def path_of(line):
    return (line.a, *line.body, line.b)


def line_of(path):
    return Line(path[0], tuple(path[1:-1]), path[-1])


def crossing(p, q):
    """The other diagonal of the 2x2 a diagonal step p -> q cuts, or None
    for an orthogonal step."""
    if p[0] == q[0] or p[1] == q[1]:
        return None
    return frozenset(((p[0], q[1]), (q[0], p[1])))


def occupied(lines):
    """(every cell on a line, every body cell, each diagonal step's cells ->
    the line it belongs to)."""
    on_line, bodies, diagonals = set(), set(), {}
    for line in lines:
        cells = path_of(line)
        on_line.update(cells)
        bodies.update(line.body)
        for p, q in itertools.pairwise(cells):
            if crossing(p, q) is not None:
                diagonals[frozenset((p, q))] = line
    return on_line, bodies, diagonals


def _king(p, q):
    return p != q and abs(p[0] - q[0]) <= 1 and abs(p[1] - q[1]) <= 1


def shape_violation(path, lines, end):
    seen = set()
    for cell in path:
        if cell in seen:
            return f"revisits {cell_name(cell)}"
        seen.add(cell)
    steps = list(itertools.pairwise(path))
    for p, q in steps:
        if not _king(p, q):
            return f"{cell_name(p)} -> {cell_name(q)} is not a king step"
    if len(path) < 3:
        return "no body cell"
    on_line, bodies, diagonals = occupied(lines)
    for cell in path[1:-1]:
        if cell in on_line:
            return f"body cell {cell_name(cell)} is already on a line"
    for cell in (path[0], path[-1]):
        if cell in bodies:
            return f"{end} {cell_name(cell)} is another line's body cell"
    own = {frozenset(step) for step in steps if crossing(*step) is not None}
    for p, q in steps:
        cross = crossing(p, q)
        if cross is None:
            continue
        if cross in diagonals:
            return (
                f"crosses line {line_name(diagonals[cross])} diagonally "
                f"at {cell_name(p)} -> {cell_name(q)}"
            )
        if cross in own:
            return f"crosses itself at {cell_name(p)} -> {cell_name(q)}"
    return None


def new_cells(path, lines):
    """How many cells drawing `path` takes from the cells a later body could
    use: its body cells, and each end that is on no line yet."""
    on_line = occupied(lines)[0]
    return len(path) - 2 + sum(c not in on_line for c in (path[0], path[-1]))


def free_cell_count(lines, n):
    """How many cells of an n x n board are on no line, so could still be a
    body cell."""
    return n * n - len(occupied(lines)[0])


def no_space(target, second, lines):
    """True when every cell whose value differs between `target` and
    `second` is a body cell of a drawn line, so no new line can tell them
    apart."""
    bodies = occupied(lines)[1]
    n = len(target.digits)
    return all(
        (r, c) in bodies
        for r in range(n)
        for c in range(n)
        if target.doubled((r, c)) != second.doubled((r, c))
    )

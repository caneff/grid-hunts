"""SCRATCH: the rule of Numbered Rooms with enterable outside digits, pro-Battenburg.

Rule, as ruled by Chris on 2026-11-04. Each of the 36 outside cells holds the
digit of its target: the Nth cell from that edge, where N is the first cell's
digit. A window, a 2x2 of the 9x9, is marked exactly when its four cells are a
checkerboard of target and not target.

The reader functions take a full grid and use no solver. `build` and `solve`
are the CP-SAT model on sudoku_kit's board. A grid is nine lists of digits.
"""

from ortools.sat.python import cp_model
from sudoku_kit.cpsat import SOLVED, UNKNOWN, boxes, solver, sudoku_model

CLUES = [(side, i) for side in "LRTB" for i in range(9)]
WINDOWS = [(r, c) for r in range(8) for c in range(8)]


def line_cells(clue):
    """The nine cells of a clue's line, nearest its outside cell first."""
    side, i = clue
    if side == "L":
        return [(i, c) for c in range(9)]
    if side == "R":
        return [(i, 8 - c) for c in range(9)]
    if side == "T":
        return [(r, i) for r in range(9)]
    return [(8 - r, i) for r in range(9)]


def clue_name(clue):
    side, i = clue
    return f"{side}{i + 1}"


# Reader: no solver.


def target_of(grid, clue):
    cells = line_cells(clue)
    r, c = cells[0]
    return cells[grid[r][c] - 1]


def targets(grid):
    return {target_of(grid, clue) for clue in CLUES}


def outside(grid):
    ring = {}
    for clue in CLUES:
        r, c = target_of(grid, clue)
        ring[clue] = grid[r][c]
    return ring


def marks(grid):
    t = targets(grid)
    found = set()
    for r, c in WINDOWS:
        a, f = (r, c) in t, (r, c + 1) in t
        d, e = (r + 1, c) in t, (r + 1, c + 1) in t
        if a == e and f == d and a != f:
            found.add((r, c))
    return frozenset(found)


def is_sudoku(grid):
    want = set(range(1, 10))
    for i in range(9):
        if set(grid[i]) != want or {grid[r][i] for r in range(9)} != want:
            return False
    for br in range(0, 9, 3):
        for bc in range(0, 9, 3):
            box = {grid[br + r][bc + c] for r in range(3) for c in range(3)}
            if box != want:
                return False
    return True


def random_grid(rng):
    """A random sudoku grid by shuffled backtracking."""
    grid = [[0] * 9 for _ in range(9)]
    rows = [set() for _ in range(9)]
    cols = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]

    def place(n):
        if n == 81:
            return True
        r, c = divmod(n, 9)
        box = r // 3 * 3 + c // 3
        digits = list(range(1, 10))
        rng.shuffle(digits)
        for d in digits:
            if d in rows[r] or d in cols[c] or d in boxes[box]:
                continue
            grid[r][c] = d
            rows[r].add(d)
            cols[c].add(d)
            boxes[box].add(d)
            if place(n + 1):
                return True
            rows[r].remove(d)
            cols[c].remove(d)
            boxes[box].remove(d)
        grid[r][c] = 0
        return False

    place(0)
    return grid


def show(grid):
    return "\n".join("".join(str(d) for d in row) for row in grid)


# Model.


def build(mark_set=None, ring=None, pin=None):
    """(model, x, b, t). `mark_set` None turns the Battenburg rule off."""
    m, x = sudoku_model(9, boxes(9, 3, 3))
    b = {}
    for (r, c), var in x.items():
        lits = [m.NewBoolVar(f"b{r}{c}{d}") for d in range(1, 10)]
        m.AddMapDomain(var, lits, 1)
        for d, lit in enumerate(lits, 1):
            b[r, c, d] = lit

    reached = {cell: [] for cell in x}
    for clue in CLUES:
        cells = line_cells(clue)
        pr, pc = cells[0]
        for i, cell in enumerate(cells):
            reached[cell].append(b[pr, pc, i + 1])
    t = {}
    for cell, lits in reached.items():
        t[cell] = m.NewBoolVar(f"t{cell}")
        m.AddBoolOr(lits + [t[cell].Not()])
        for lit in lits:
            m.AddImplication(lit, t[cell])

    if mark_set is not None:
        for r, c in WINDOWS:
            a, f = t[r, c], t[r, c + 1]
            d, e = t[r + 1, c], t[r + 1, c + 1]
            if (r, c) in mark_set:
                m.AddImplication(a, e)
                m.AddImplication(e, a)
                m.AddImplication(f, d)
                m.AddImplication(d, f)
                m.AddBoolOr(a, f)
                m.AddBoolOr(a.Not(), f.Not())
            else:
                m.AddBoolOr(a.Not(), f, d, e.Not())
                m.AddBoolOr(a, f.Not(), d.Not(), e)

    for clue, v in (ring or {}).items():
        cells = line_cells(clue)
        pr, pc = cells[0]
        for i, (r, c) in enumerate(cells):
            m.AddImplication(b[pr, pc, i + 1], b[r, c, v])
    for (r, c), v in (pin or {}).items():
        m.Add(x[r, c] == v)
    return m, x, b, t


def solve(mark_set=None, ring=None, pin=None, exclude=(), limit=60.0):
    """A grid meeting the conditions, or None when proven none. One worker.

    Raises TimeoutError at `limit`: a timeout is never read as no grid.
    """
    m, x, b, _ = build(mark_set, ring, pin)
    for grid in exclude:
        m.AddBoolOr(
            [b[r, c, grid[r][c]].Not() for r in range(9) for c in range(9)]
        )
    s = solver(limit)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError(f"CP-SAT hit the {limit}s limit; no verdict")
    if status not in SOLVED:
        return None
    return [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]


def min_hitting_set(sets, limit=60.0):
    """A smallest set of clues meeting every set in `sets`, proven by CP-SAT."""
    m = cp_model.CpModel()
    use = {clue: m.NewBoolVar(clue_name(clue)) for clue in CLUES}
    for group in sets:
        m.AddBoolOr([use[clue] for clue in group])
    m.Minimize(sum(use.values()))
    s = solver(limit)
    if s.Solve(m) != cp_model.OPTIMAL:
        raise TimeoutError("hitting set not proven minimum")
    return [clue for clue in CLUES if s.Value(use[clue])]


def min_outside_givens(grid, use_marks=True, limit=60.0, max_rounds=400):
    """The fewest outside givens that leave only `grid`, or why there is none.

    Implicit hitting set. Each second grid shows a set of outside cells that
    differ, and the givens must hold one of them. Returns a dict with `status`:
    "minimum" (proven for this grid and its marks), "not_separable" (a second
    grid has the same marks and all 36 outside digits), or "capped".
    """
    mark_set = marks(grid) if use_marks else None
    ring = outside(grid)
    twin = solve(mark_set, ring, exclude=[grid], limit=limit)
    if twin is not None:
        return {"status": "not_separable", "second": twin, "rounds": 0}
    sets = []
    for rounds in range(1, max_rounds + 1):
        chosen = min_hitting_set(sets)
        held = {c: ring[c] for c in chosen}
        alt = solve(mark_set, held, exclude=[grid], limit=limit)
        if alt is None:
            return {"status": "minimum", "givens": chosen, "rounds": rounds}
        sets.append(_shrunk_difference(grid, alt, mark_set, ring, held, limit))
    return {"status": "capped", "lower_bound": len(chosen), "rounds": max_rounds}


def _shrunk_difference(grid, alt, mark_set, ring, held, limit):
    """The outside cells a second grid differs on, made as few as it can.

    Holds each differing cell in turn at the target grid's digit and keeps the
    hold when a second grid still exists. A smaller set is a stronger cut.
    """
    held = dict(held)
    other = outside(alt)
    for clue in [c for c in CLUES if other[c] != ring[c]]:
        if other[clue] == ring[clue]:
            continue
        trial = solve(mark_set, held | {clue: ring[clue]}, exclude=[grid], limit=limit)
        if trial is not None:
            held[clue] = ring[clue]
            alt, other = trial, outside(trial)
    return [c for c in CLUES if other[c] != ring[c]]

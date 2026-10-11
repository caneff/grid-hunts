"""The hybrid's rules on PySAT with CaDiCaL (#784, #785): U-Bahn with
Choco-Banana laid over the grid cells and the number cells (spec #781).

Two engines beside `hybrid_model.py`, behind the finder's `--engine` flag,
both on the clauses `rules` builds. The network's own rules are
`sat_model.py`'s clauses. The hybrid's are stated here from the spec and from
`hybrid.py`'s reader, not carried over from the CP-SAT model, so that the
engines check each other:

- A cell's value: a grid cell's is its piece's, a number cell's is a count
  of one kind over its row or column, kept in unary by `_at_least`. Each
  cell has one variable for "its value is odd".
- Chocolate: no 2x2 window holds exactly three even cells, a cell off the
  board counting as not even. Three even cells of a window are in one
  region, and a region is a rectangle exactly when no window holds three of
  its cells.
- Banana: one clause per rectangle of board cells forbids "every cell of it
  odd and every cell beside it even", which is an odd region that is that
  rectangle.
- Circle: the cells of the circled cell's region are counted and the count
  is the cell's value (`_add_circle`). The chocolate and banana clauses
  shape the region, so a circle lists no rectangle and no bent shape.

Connectivity is not encoded. `listing` solves, and a full grid whose network
is in several parts is refused with `sat_model.cut_clauses`, the connectivity
cut, and the solve goes on, on the same solver, so what it learned is kept.
That is all the `lazy` engine does. The `propagator` engine also connects
`_Watcher`, which follows the edges as the solver decides them and raises a
conflict as soon as the edges that are on can no longer be joined.
"""

import sys
import time
from pathlib import Path
from typing import NamedTuple

from pysat.engines import Propagator
from pysat.solvers import Cadical195

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hybrid
import sat_model
from network import BLANK, KINDS

# How an engine keeps the network in one part.
LAZY = "lazy"
PROPAGATOR = "propagator"


class Listing(NamedTuple):
    """Grids that meet a set of conditions, in the order found: all of them
    when there are fewer than the cap asked for and `timed_out` is False.
    `cuts` is how many connectivity cuts the solves added, each a clause for
    a full grid whose network is in several parts, and `conflicts` how many
    conflicts the propagator raised while some edge was still undecided."""

    grids: tuple
    timed_out: bool
    cuts: int
    conflicts: int


class _Watcher(Propagator):
    """The connectivity propagator: it is told each edge the solver turns
    on or off, and refuses an assignment in which two edges that are on are
    kept apart by edges that are off."""

    def __init__(self, edge):
        super().__init__()
        self.ends = {var: e for e, var in edge.items()}
        self.on = {}
        # The variables assigned at each decision level. One the solver has
        # fixed is on no level and outlives every backtrack.
        self.levels = [[]]
        self.fixed = set()
        self.changed = False
        self.pending = []
        self.conflicts = self.late = 0

    def on_assignment(self, lit, fixed=False):
        var = abs(lit)
        self.on[var] = lit > 0
        if fixed:
            self.fixed.add(var)
        else:
            self.levels[-1].append(var)
        self.changed = True

    def on_new_level(self):
        self.levels.append([])

    def on_backtrack(self, to):
        while len(self.levels) > to + 1:
            for var in self.levels.pop():
                if var not in self.fixed:
                    self.on.pop(var, None)

    def propagate(self):
        if self.changed:
            self.changed = False
            clause = self._refusal()
            if clause:
                self.pending.append(clause)
                if len(self.on) < len(self.ends):
                    self.conflicts += 1
                else:
                    self.late += 1
        return []

    def add_clause(self):
        return self.pending.pop() if self.pending else []

    def _refusal(self):
        """A clause the current assignment breaks, or None when the edges
        that are on can still be joined. With the cells one of them reaches
        over edges not turned off, and another edge that is on outside those
        cells: if both are on, some edge leaving those cells is on. That
        holds for every network, whatever is assigned."""
        on = [var for var, is_on in self.on.items() if is_on]
        if len(on) < 2:
            return None
        beside = {}
        for var, (a, b) in self.ends.items():
            if self.on.get(var, True):
                beside.setdefault(a, []).append(b)
                beside.setdefault(b, []).append(a)
        reach, stack = set(), [self.ends[on[0]][0]]
        while stack:
            cell = stack.pop()
            if cell not in reach:
                reach.add(cell)
                stack += beside[cell]
        apart = next((var for var in on if self.ends[var][0] not in reach), None)
        if apart is None:
            return None
        leaving = [
            var for var, (a, b) in self.ends.items() if (a in reach) != (b in reach)
        ]
        return [-on[0], -apart, *leaving]


def _at_least(pool, clauses, literals, top, true):
    """Count how many of `literals` are true, in unary: returns `g`, where
    `g[j]` is true exactly when at least `j` of them are, for `j` from 0 to
    `top`. `true` is a variable that is always true."""
    row = [true] + [-true] * top
    for literal in literals:
        new = [true]
        for j in range(1, top + 1):
            # At least j already, or this one after at least j - 1.
            g = pool.id()
            had, below = row[j], row[j - 1]
            clauses += [
                [-had, g],
                [-literal, -below, g],
                [-g, had, literal],
                [-g, had, below],
            ]
            new.append(g)
        row = new
    return row


def _add_values(pool, clauses, kind, conditions, true):
    """Returns `(count, odd)`: `count[number cell]` is its value in unary, as
    `_at_least` gives it up to one more than its row or column can hold, and
    `odd[cell]` is the variable "this cell's value is odd", for every cell of
    the board."""
    rows, cols, _, _, blank_strip = conditions
    odd = {}
    for cell in ((r, c) for r in range(rows) for c in range(cols)):
        odd[cell] = pool.id()
        clauses += [
            [-kind[cell, k], odd[cell] if hybrid.PIECE_VALUE[k] % 2 else -odd[cell]]
            for k in KINDS
        ]
    count = {}
    for cell, (k, over) in hybrid.number_cells(rows, cols, blank_strip).items():
        counted = [kind[held, k] for held in over]
        count[cell] = _at_least(pool, clauses, counted, len(over) + 1, true)
        odd[cell] = pool.id()
        # The value is j when at least j are counted and not j + 1.
        clauses += [
            [-count[cell][j], count[cell][j + 1], odd[cell] if j % 2 else -odd[cell]]
            for j in range(len(over) + 1)
        ]
    return count, odd


def _chocolate(odd):
    """The clauses that make every even region a rectangle."""
    clauses = []
    corners = {(r - dr, c - dc) for r, c in odd for dr in (0, 1) for dc in (0, 1)}
    for r, c in sorted(corners):
        window = [(r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)]
        for fourth in window:
            three = [cell for cell in window if cell != fourth]
            if all(cell in odd for cell in three):
                # Not all three even, unless the fourth is even too.
                unless = [-odd[fourth]] if fourth in odd else []
                clauses.append([odd[cell] for cell in three] + unless)
    return clauses


def _banana(odd):
    """The clauses that keep every odd region from being a rectangle."""
    clauses = []
    board_rows = sorted({r for r, _ in odd})
    board_cols = sorted({c for _, c in odd})
    for top in board_rows:
        for left in board_cols:
            for bottom in range(top, board_rows[-1] + 1):
                for right in range(left, board_cols[-1] + 1):
                    held = [range(top, bottom + 1), range(left, right + 1)]
                    inside = [(r, c) for r in held[0] for c in held[1]]
                    if any(cell not in odd for cell in inside):
                        continue
                    beside = [(r, c) for r in (top - 1, bottom + 1) for c in held[1]]
                    beside += [(r, c) for r in held[0] for c in (left - 1, right + 1)]
                    clauses.append(
                        [-odd[cell] for cell in inside]
                        + [odd[cell] for cell in beside if cell in odd]
                    )
    return clauses


def _neighbours(cell):
    r, c = cell
    return [(r - 1, c), (r, c + 1), (r + 1, c), (r, c - 1)]


def _add_circle(pool, clauses, odd, value, circle, true):
    """The circled cell's value is the number of cells of its region.
    `value` is that value in unary, with a last entry no value reaches.

    The region is found in rounds. Round 0 reaches the circled cell alone; a
    cell is reached in a round when its value has the circled cell's parity
    and it, or a cell beside it, was reached in the round before. Each round
    reaches at least one cell more until the whole region is reached, so
    after as many rounds as the largest value the cells reached number the
    region's size, or more than any value when the region is larger than
    that."""
    top = len(value) - 1
    reached = {circle: true}
    same = {}
    for _ in range(top - 1):
        before, reached = reached, {circle: true}
        near = {n for cell in before for n in _neighbours(cell) if n in odd}
        for cell in sorted((near | set(before)) - {circle}):
            if cell not in same:
                same[cell] = pool.id()
                clauses += [
                    [-same[cell], -odd[cell], odd[circle]],
                    [-same[cell], odd[cell], -odd[circle]],
                    [same[cell], odd[cell], odd[circle]],
                    [same[cell], -odd[cell], -odd[circle]],
                ]
            sources = [before[n] for n in (cell, *_neighbours(cell)) if n in before]
            reached[cell] = pool.id()
            clauses += [[-reached[cell], same[cell]], [-reached[cell], *sources]]
            clauses += [[-source, -same[cell], reached[cell]] for source in sources]
    size = _at_least(pool, clauses, list(reached.values()), top, true)
    for j in range(1, top + 1):
        clauses += [[-size[j], value[j]], [size[j], -value[j]]]


def _piece_value(pool, clauses, kind, cell, true):
    """A grid cell's value in unary, as `_at_least` would give it, up to one
    more than any piece is worth."""
    top = max(hybrid.PIECE_VALUE.values()) + 1
    value = [true] + [pool.id() for _ in range(top)]
    clauses += [
        [-kind[cell, k], value[j] if hybrid.PIECE_VALUE[k] >= j else -value[j]]
        for k in KINDS
        for j in range(1, top + 1)
    ]
    return value


def rules(conditions):
    """Every rule but connectivity, for these conditions. Returns `(clauses,
    edge, blank)`: the edge variables keyed by edge and each grid cell's
    blank variable. Raises ValueError on a circle that is off the board."""
    rows, cols, circles, exactly, _ = conditions
    pool, edge, kind, clauses = sat_model.network_rules(rows, cols)
    true = pool.id()
    clauses.append([true])
    count, odd = _add_values(pool, clauses, kind, conditions, true)
    clauses += _chocolate(odd)
    clauses += _banana(odd)
    for circle in sorted(circles):
        if circle not in odd:
            raise ValueError(f"circle off the board: {circle}")
        value = count.get(circle) or _piece_value(pool, clauses, kind, circle, true)
        _add_circle(pool, clauses, odd, value, circle, true)
    if exactly is not None:
        counted = [kind[cell, exactly.kind] for cell in exactly.cells(rows, cols)]
        held = _at_least(pool, clauses, counted, exactly.count + 1, true)
        clauses += [[held[exactly.count]], [-held[exactly.count + 1]]]
    return clauses, edge, {cell: var for (cell, k), var in kind.items() if k == BLANK}


def listing(conditions, connectivity, *, cap, time_limit, rng=None):
    """Up to `cap` grids that meet the conditions, as a `Listing`. A time
    limit of zero or less is reached before any solve. `rng` steers the
    search: it picks which way each edge is tried first, so a seed gives the
    same grids every run and another seed other ones."""
    deadline = time.monotonic() + time_limit
    clauses, edge, blank = rules(conditions)
    grids, cuts, answer = [], 0, True
    watcher = _Watcher(edge)
    with Cadical195(bootstrap_with=clauses) as solver:
        if connectivity == PROPAGATOR:
            solver.connect_propagator(watcher)
            for var in edge.values():
                solver.observe(var)
        if rng is not None:
            solver.set_phases(
                [var if rng.random() < 0.5 else -var for var in edge.values()]
            )
        while len(grids) < cap:
            answer = sat_model.solve(solver, deadline)
            if not answer:
                break
            found = sat_model.edges_on(solver, edge)
            cut = sat_model.cut_clauses(edge, blank, found)
            if cut:
                solver.append_formula(cut)
                cuts += len(cut)
                continue
            grids.append(found)
            sat_model.forbid(solver, edge, found)
    # A conflict the propagator raised on a full set of edges is a cut.
    return Listing(tuple(grids), answer is None, cuts + watcher.late, watcher.conflicts)


def sampled(found):
    """A `Listing` capped at one grid, as a `hybrid.Sampled`."""
    if found.grids:
        return hybrid.Sampled("found", found.grids[0])
    return hybrid.Sampled("timeout" if found.timed_out else "infeasible", None)


def classified(found):
    """A `Listing` capped at two grids, as a `hybrid.Classified`."""
    status = (
        "timeout"
        if found.timed_out
        else ("infeasible", "unique", "not_unique")[len(found.grids)]
    )
    return hybrid.Classified(status, next(iter(found.grids), None))


class Engine(NamedTuple):
    """A PySAT engine as `hybrid_finder.ENGINES` holds one: `connectivity`
    says how it keeps the network in one part."""

    connectivity: str

    def grid_listing(self, conditions, rng, *, time_limit):
        """The `Listing` behind `grid`: the one grid, with the solve's cut
        and conflict counts."""
        return listing(
            conditions, self.connectivity, cap=1, time_limit=time_limit, rng=rng
        )

    def classify_listing(self, conditions, *, time_limit):
        """The `Listing` behind `classify`: up to two grids, with the cut
        and conflict counts."""
        return listing(conditions, self.connectivity, cap=2, time_limit=time_limit)

    def grid(self, conditions, rng, *, time_limit):
        """One grid that meets the conditions, steered by `rng`: the same
        grid on every run of a seed."""
        return sampled(self.grid_listing(conditions, rng, time_limit=time_limit))

    def classify(self, conditions, *, time_limit, workers):
        """Whether the conditions have no grid, exactly one, or more than
        one. A time limit reached is "timeout", never one of the other
        three, and one limit covers the whole answer. CaDiCaL runs on one
        thread whatever `workers` says."""
        return classified(self.classify_listing(conditions, time_limit=time_limit))

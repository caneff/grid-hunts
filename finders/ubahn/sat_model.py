"""A second uniqueness check for U-Bahn, on PySAT with CaDiCaL (#776).

A prototype beside `model.py`, which stays the reference. One boolean per
edge, as there; each cell's kind is channelled from its arms by clauses, and
the outside numbers are cardinality constraints. Connectivity is not encoded:
the solver hands each full assignment to `_Connectivity.check_model`, which
flood fills it and, when the network is in several parts, gives back one
clause per part. Both solves of a uniqueness check run on one solver, so a
clause added in the first is still there in the second.

    docs/research/2026-10-10-u-bahn-optimization-queue.md,
    section "PySAT with lazy connectivity cuts"
"""

import sys
import time
from itertools import product
from pathlib import Path
from typing import NamedTuple

from pysat.card import CardEnc
from pysat.engines import Propagator
from pysat.formula import IDPool
from pysat.solvers import Cadical195

sys.path.insert(0, str(Path(__file__).resolve().parent))
from network import BLANK, KINDS, all_edges, arms_on_board, kind_of, rows_and_columns

# CaDiCaL takes no wall-clock limit and cannot be interrupted through PySAT,
# so a solve runs in slices of this many conflicts with the clock read
# between them.
CONFLICTS_PER_SLICE = 2000


class _Connectivity(Propagator):
    """The lazy connectivity check: it sees full assignments only."""

    def __init__(self, edge, blank):
        super().__init__()
        self.is_lazy = True
        self.edge = edge
        self.blank = blank
        self.pending = []
        self.cuts = 0

    def check_model(self, model):
        true = {lit for lit in model if lit > 0}
        on = {e for e, var in self.edge.items() if var in true}
        parts = _parts(on)
        if len(parts) <= 1:
            return True
        for part in parts:
            # A used cell of this part and one outside it are joined only
            # if some edge leaves the part.
            inside = min(part)
            outside = min(
                cell for other in parts if other is not part for cell in other
            )
            leaving = [
                var for (a, b), var in self.edge.items() if (a in part) != (b in part)
            ]
            self.pending.append([self.blank[inside], self.blank[outside], *leaving])
        self.cuts += len(parts)
        return False

    def add_clause(self):
        return self.pending.pop() if self.pending else []


def _parts(on):
    """The connected parts of a set of edges, each a set of cells."""
    neighbours = {}
    for a, b in on:
        neighbours.setdefault(a, []).append(b)
        neighbours.setdefault(b, []).append(a)
    parts, seen = [], set()
    for start in neighbours:
        if start in seen:
            continue
        part, stack = set(), [start]
        while stack:
            cell = stack.pop()
            if cell in part:
                continue
            part.add(cell)
            stack.extend(neighbours[cell])
        seen |= part
        parts.append(part)
    return parts


def _piece_clauses(edge, kind, cells):
    """Each cell's kind channelled from its arms: every assignment of the
    arms that are on the board either is a dead end, and is forbidden, or
    fixes all five kind booleans."""
    clauses = []
    for cell in cells:
        on_board = arms_on_board(cell, edge)
        for bits in product((0, 1), repeat=len(on_board)):
            arms = [0, 0, 0, 0]
            for i, bit in zip(on_board, bits, strict=True):
                arms[i] = bit
            unless = [
                -var if bit else var
                for var, bit in zip(on_board.values(), bits, strict=True)
            ]
            made = kind_of(arms)
            if made is None:
                clauses.append(unless)
                continue
            clauses.extend(
                [*unless, kind[cell, k] if k == made else -kind[cell, k]] for k in KINDS
            )
    return clauses


def _solve(solver, deadline):
    """True, False, or None when the clock ran out first."""
    while time.monotonic() < deadline:
        solver.conf_budget(CONFLICTS_PER_SLICE)
        answer = solver.solve_limited()
        if answer is not None:
            return answer
    return None


def _add_rules(solver, rows, cols, numbers):
    """Every rule but connectivity, as clauses on `solver`. Returns the edge
    variables keyed by edge and each cell's blank variable, or None when a
    count is outside its row or column, which no board can hold."""
    held_counts = rows_and_columns(rows, cols, numbers)
    if any(
        not 0 <= count <= len(held) for held, counts in held_counts for count in counts
    ):
        return None
    pool = IDPool()
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    edge = {e: pool.id(e) for e in all_edges(rows, cols)}
    kind = {(cell, k): pool.id((cell, k)) for cell in cells for k in KINDS}
    solver.append_formula(_piece_clauses(edge, kind, cells))
    # A network has at least one edge.
    solver.add_clause(list(edge.values()))
    for held, counts in held_counts:
        for k, count in zip(KINDS, counts, strict=True):
            solver.append_formula(
                CardEnc.equals(
                    [kind[cell, k] for cell in held], bound=count, vpool=pool
                )
            )
    return edge, {cell: kind[cell, BLANK] for cell in cells}


def _edges_on(solver, edge):
    """The edges the solver's model turns on."""
    true = {lit for lit in solver.get_model() if lit > 0}
    return frozenset(e for e, var in edge.items() if var in true)


def _forbid(solver, edge, found):
    """Rule out exactly this set of edges."""
    solver.add_clause([-var if e in found else var for e, var in edge.items()])


def uniqueness(rows, cols, numbers, *, time_limit):
    """Whether one full set of outside numbers has exactly one network.

    Returns `(status, network, cuts)`. `status` and `network` are as
    `model.uniqueness` returns them, without "invalid"; `cuts` is how many
    connectivity clauses the check added. A timeout is never unique.
    """
    deadline = time.monotonic() + time_limit
    with Cadical195() as solver:
        rules = _add_rules(solver, rows, cols, numbers)
        if rules is None:
            return "infeasible", None, 0
        edge, blank = rules
        connectivity = _Connectivity(edge, blank)
        solver.connect_propagator(connectivity)
        for var in (*edge.values(), *blank.values()):
            solver.observe(var)

        answer = _solve(solver, deadline)
        if answer is None:
            return "timeout", None, connectivity.cuts
        if not answer:
            return "infeasible", None, connectivity.cuts
        found = _edges_on(solver, edge)
        _forbid(solver, edge, found)
        answer = _solve(solver, deadline)
        status = {None: "timeout", False: "unique", True: "not_unique"}[answer]
        return status, found, connectivity.cuts


class Fillings(NamedTuple):
    """How many fillings a set of outside numbers has in one part and how
    many in several, and whether the count stopped at its cap."""

    connected: int
    not_connected: int
    capped: bool


def fillings(rows, cols, numbers, *, cap):
    """Count the fillings of a full set of outside numbers: the sets of edges
    with no dead end and those numbers, connected or not. Stops after `cap`
    of them. The ones in one part are the networks; the others are what a
    connectivity cut has to refuse."""
    connected = not_connected = 0
    with Cadical195() as solver:
        rules = _add_rules(solver, rows, cols, numbers)
        if rules is None:
            return Fillings(0, 0, False)
        edge, _ = rules
        while solver.solve():
            if connected + not_connected == cap:
                return Fillings(connected, not_connected, True)
            found = _edges_on(solver, edge)
            if len(_parts(found)) == 1:
                connected += 1
            else:
                not_connected += 1
            _forbid(solver, edge, found)
    return Fillings(connected, not_connected, False)

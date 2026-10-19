"""PROTOTYPE for #36 -- throwaway, not production. No tests on purpose.

Question: can one query driver answer every board question (feasible, unique,
enumerate, forced mark, max, drop-one) if each finder hands it only a solve
oracle, not its model? Tried on halver_between only. Zombo (a solve-check-cut
loop, the case a solve oracle exists for) was dropped: Chris is done with it
(2026-10-19), so the lazy-cut fit is untested.

The whole contract a finder supplies (`Board`):

    clues                       the droppable clues of the setup, any type
    without(clue) -> Board      the same board with one clue removed
    solve(require, forbid, time_limit) -> Found | Infeasible | Timeout
                                one valid solution meeting every condition in
                                `require` and equal to none of `forbid`
    show(solution) -> str       a text drawing

A solution is a dict from a finder-chosen key to an int. Conditions are a
tiny algebra over those keys (Eq, Gt, Not, All, Any) that the driver builds
and the finder compiles; `cpsat_literal` compiles one onto any CP-SAT model,
so a finder on CP-SAT writes no compiler of its own.

Every answer carries `complete`: True only when the last solve proved the
space empty. A timeout or a cap is never read as unique, held, maximal or
complete. `sink` gets each solution the moment it is found.
"""

from typing import Any, NamedTuple, Protocol


class Eq(NamedTuple):
    key: Any
    value: int


class Gt(NamedTuple):
    key: Any
    value: int


class Not(NamedTuple):
    cond: Any


class All(NamedTuple):
    conds: tuple


class Any_(NamedTuple):
    conds: tuple


def holds(cond, solution):
    """The plain-Python reading of a condition on one solution."""
    match cond:
        case Eq(key, value):
            return solution[key] == value
        case Gt(key, value):
            return solution[key] > value
        case Not(inner):
            return not holds(inner, solution)
        case All(conds):
            return all(holds(c, solution) for c in conds)
        case Any_(conds):
            return any(holds(c, solution) for c in conds)
    raise ValueError(f"unknown condition {cond!r}")


def cpsat_literal(m, var_of, cond):
    """A Bool literal of CP-SAT model `m` that is true exactly when `cond`
    holds; `var_of(key)` is the model variable behind a solution key."""
    match cond:
        case Not(inner):
            return cpsat_literal(m, var_of, inner).Not()
        case Eq(key, value) | Gt(key, value):
            b = m.NewBoolVar("")
            v = var_of(key)
            if isinstance(cond, Eq):
                m.Add(v == value).OnlyEnforceIf(b)
                m.Add(v != value).OnlyEnforceIf(b.Not())
            else:
                m.Add(v > value).OnlyEnforceIf(b)
                m.Add(v <= value).OnlyEnforceIf(b.Not())
            return b
        case All(conds) | Any_(conds):
            lits = [cpsat_literal(m, var_of, c) for c in conds]
            b = m.NewBoolVar("")
            if isinstance(cond, All):
                m.AddBoolAnd(lits).OnlyEnforceIf(b)
                m.AddBoolOr([lit.Not() for lit in lits]).OnlyEnforceIf(b.Not())
            else:
                m.AddBoolOr(lits).OnlyEnforceIf(b)
                m.AddBoolAnd([lit.Not() for lit in lits]).OnlyEnforceIf(b.Not())
            return b
    raise ValueError(f"unknown condition {cond!r}")


class Found(NamedTuple):
    solution: dict


class Infeasible(NamedTuple):
    pass


class Timeout(NamedTuple):
    pass


class Board(Protocol):
    clues: list

    def without(self, clue) -> "Board": ...

    def solve(self, require, forbid, time_limit) -> Found | Infeasible | Timeout: ...

    def show(self, solution) -> str: ...


class Answer(NamedTuple):
    question: str
    status: str
    complete: bool
    solutions: tuple = ()
    detail: Any = None


def _quiet(_solution):
    pass


def feasible(board, time_limit, sink=_quiet):
    r = board.solve([], [], time_limit)
    if isinstance(r, Found):
        sink(r.solution)
        return Answer("feasible", "feasible", True, (r.solution,))
    if isinstance(r, Infeasible):
        return Answer("feasible", "infeasible", True)
    return Answer("feasible", "timeout", False)


def unique(board, time_limit, sink=_quiet, require=()):
    """The five statuses of sudoku_kit.uniqueness, less "invalid"."""
    first = board.solve(list(require), [], time_limit)
    if isinstance(first, Infeasible):
        return Answer("unique", "infeasible", True)
    if isinstance(first, Timeout):
        return Answer("unique", "timeout", False)
    sink(first.solution)
    second = board.solve(list(require), [first.solution], time_limit)
    if isinstance(second, Infeasible):
        return Answer("unique", "unique", True, (first.solution,))
    if isinstance(second, Timeout):
        return Answer("unique", "timeout", False, (first.solution,))
    sink(second.solution)
    return Answer("unique", "not_unique", True, (first.solution, second.solution))


def enumerate_all(board, time_limit, cap, sink=_quiet):
    """Every solution up to `cap`; complete only when one more solve proved
    there is none left."""
    found = []
    while len(found) < cap:
        r = board.solve([], found, time_limit)
        if isinstance(r, Infeasible):
            return Answer("enumerate", f"{len(found)} solutions", True, tuple(found))
        if isinstance(r, Timeout):
            return Answer(
                "enumerate", f"at least {len(found)} (timeout)", False, tuple(found)
            )
        found.append(r.solution)
        sink(r.solution)
    return Answer("enumerate", f"at least {cap} (cap)", False, tuple(found))


def forced(board, cond, time_limit, sink=_quiet):
    """Whether every solution meets `cond`: one solve with it negated."""
    r = board.solve([Not(cond)], [], time_limit)
    if isinstance(r, Infeasible):
        return Answer("forced", "held", True)
    if isinstance(r, Timeout):
        return Answer("forced", "timeout", False)
    sink(r.solution)
    return Answer("forced", "not_held", True, (r.solution,))


def maximum(board, key, time_limit, sink=_quiet):
    """The largest value `key` takes in any solution, by climbing: each step
    asks for a solution above the best so far. Needs no objective support
    from the finder, so it works on a lazy-cut model too."""
    best = None
    while True:
        require = [] if best is None else [Gt(key, best[key])]
        r = board.solve(require, [], time_limit)
        if isinstance(r, Infeasible):
            if best is None:
                return Answer("maximum", "infeasible", True)
            return Answer("maximum", str(best[key]), True, (best,))
        if isinstance(r, Timeout):
            if best is None:
                return Answer("maximum", "timeout", False)
            return Answer("maximum", f"at least {best[key]} (timeout)", False, (best,))
        best = r.solution
        sink(best)


def drop_one(board, time_limit, sink=_quiet):
    """For a unique board, each clue's verdict: "needed" when the board
    without it is no longer unique, "droppable" when it still is, or the
    status that gave no verdict. Complete only when every clue got one."""
    base = unique(board, time_limit, sink)
    if base.status != "unique":
        return Answer("drop_one", f"board is {base.status}", base.complete)
    verdicts = {}
    for clue in board.clues:
        r = unique(board.without(clue), time_limit, sink)
        verdicts[clue] = {"unique": "droppable", "not_unique": "needed"}.get(
            r.status, r.status
        )
    droppable = sum(v == "droppable" for v in verdicts.values())
    complete = all(v in ("droppable", "needed") for v in verdicts.values())
    return Answer(
        "drop_one", f"{droppable} of {len(verdicts)} droppable", complete, (), verdicts
    )

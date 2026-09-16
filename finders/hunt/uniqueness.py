"""Uniqueness check on a raw CpModel (#483/#486): solve, exclude the
solution found, re-solve, and expect infeasible. Works on any `CpModel` and
list of decision variables -- no gridfind, no finder-specific structure.
See `finders/zombo_brainanas_cpsat.py`'s `unique()`/`solve_valid()` for the
circle-hunt version this generalizes.
"""

from typing import NamedTuple

from ortools.sat.python import cp_model


class UniquenessResult(NamedTuple):
    """`status` is one of "unique", "not_unique", "infeasible", "timeout",
    "invalid" -- five outcomes, since a model with no givens at all is a
    real, distinct case from one with two solutions. `first`/`second` are
    witnesses -- tuples of values aligned with the `variables` passed to
    `check_uniqueness` -- with `second` set only when `status` is
    "not_unique"."""

    status: str
    first: tuple | None = None
    second: tuple | None = None

    @property
    def unique(self):
        return self.status == "unique"


def _solve(model, time_limit, workers):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    return solver.Solve(model), solver


def _terminal(status, first):
    """The `UniquenessResult` for a status that isn't feasible/optimal, or
    `None` when the solve succeeded and the caller should extract a
    witness and continue. `first` is the witness from the first solve, or
    `None` when classifying that first solve itself -- its presence is
    what tells an INFEASIBLE retry (unique) apart from an INFEASIBLE first
    solve (no solution at all)."""
    if status == cp_model.MODEL_INVALID:
        return UniquenessResult("invalid", first)
    if status == cp_model.UNKNOWN:
        return UniquenessResult("timeout", first)
    if status == cp_model.INFEASIBLE:
        return (
            UniquenessResult("unique", first)
            if first is not None
            else UniquenessResult("infeasible")
        )
    return None


def check_uniqueness(model, variables, *, time_limit=10.0, workers=1):
    """True (via `.unique`) iff `model` has exactly one solution over
    `variables`. A timeout or an invalid model is reported as such and
    never as unique -- a stripper that trusted either would keep a clue
    that isn't actually load-bearing: sound, never lean.

    Mutates `model`: adds the exclusion constraint that rules the first
    solution out, so a caller that needs the model unchanged afterwards
    should pass a copy (`fresh = cp_model.CpModel(); fresh.CopyFrom(model)`).
    """
    variables = list(variables)
    status, solver = _solve(model, time_limit, workers)
    terminal = _terminal(status, None)
    if terminal is not None:
        return terminal
    first = tuple(solver.Value(v) for v in variables)

    diffs = []
    for v, value in zip(variables, first, strict=True):
        d = model.NewBoolVar("")
        model.Add(v != value).OnlyEnforceIf(d)
        model.Add(v == value).OnlyEnforceIf(d.Not())
        diffs.append(d)
    model.AddBoolOr(diffs)

    status, solver = _solve(model, time_limit, workers)
    terminal = _terminal(status, first)
    if terminal is not None:
        return terminal
    second = tuple(solver.Value(v) for v in variables)
    return UniquenessResult("not_unique", first, second)

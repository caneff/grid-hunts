"""Solve-with-watchdog plus a stall callback (#483/#486): stop a CP-SAT solve
that has gone quiet instead of letting it run to its full time limit. Half
of zombo-brainanas's sampling budget went to proving optimality after the
real answer was already found (seed 701: feasible at 178s, OPTIMAL at 489s).
See `finders/zombo_brainanas_cpsat.py`'s `FirstSolution`/`solve_with_watchdog`
for the circle-hunt version this generalizes.
"""

import threading

from ortools.sat.python import cp_model


class StallWatchdog(cp_model.CpSolverSolutionCallback):
    """Tracks the wall time of the first solution (`first_at`) and reports
    `stalled()` once `stall` seconds have passed with no progress -- from
    the last solution found, or from `start()` if none has been found yet,
    so a solve that never finds anything still ends. `stall=0` never
    stalls. `stalled()` never stalls before `start()` or a solution has
    armed the clock -- there's nothing to measure elapsed time against
    yet."""

    def __init__(self, stall):
        super().__init__()
        self.stall = stall
        self.first_at = None
        self._last = None

    def start(self):
        """Arm the clock at the solve's own start, so a solve that never
        finds any solution still has something to measure against
        (`solve_with_watchdog` calls this before the solve begins)."""
        self._last = self.WallTime()

    def on_solution_callback(self):
        now = self.WallTime()
        if self.first_at is None:
            self.first_at = now
        self._last = now

    def stalled(self):
        if not self.stall or self._last is None:
            return False
        return self.WallTime() - self._last > self.stall


def solve_with_watchdog(solver, model, callback):
    """Solve `model` in a thread, polling `callback.stalled()` and calling
    `solver.StopSearch()` the moment it reports a stall. The poll interval
    is `callback.stall` seconds (capped at 1s) when `callback` declares a
    `stall`, else 1s -- a stall limit under a second isn't worth much if
    polling only happens once a second regardless. `callback.start()` is
    called (if present) right before the solve begins, so its clock can
    measure from the solve's actual start rather than from whenever the
    first poll happens to land.

    `solver` and `callback` are duck-typed (a `CpSolver` and a
    `StallWatchdog`, or any objects with the same `Solve`/`StopSearch`/
    `stalled` methods, `start`/`stall` optional): `solve_with_watchdog`
    itself has no CP-SAT dependency, only `StallWatchdog` does.

    An exception in the solve thread propagates out of this call, once the
    thread has finished, instead of being swallowed and surfacing as a
    `KeyError` on the missing status.
    """
    result = {}

    def run():
        try:
            result["status"] = solver.Solve(model, callback)
        except BaseException as exc:  # re-raised below, never swallowed
            result["error"] = exc

    start = getattr(callback, "start", None)
    if start is not None:
        start()

    thread = threading.Thread(target=run)
    thread.start()
    stall = getattr(callback, "stall", None)
    poll_interval = min(1.0, stall) if stall else 1.0
    while thread.is_alive():
        thread.join(poll_interval)
        if callback.stalled():
            solver.StopSearch()
    if "error" in result:
        raise result["error"]
    return result["status"]

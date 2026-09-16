"""StallWatchdog's timing and solve_with_watchdog's stop-on-stall loop
(#486).

`StallWatchdog.stalled()` is tested with a fake clock, since a real CP-SAT
solve's wall time can't be driven deterministically from a test. Two fake
solver/callback objects, not real CP-SAT ones, are used to test
`solve_with_watchdog`'s coordination logic itself -- it only needs
`.Solve()`/`.StopSearch()` and `.stalled()` (`.start()` and `.stall` are
read only if present), so this exercises the real coordination code
without betting on any particular CP-SAT model being slow enough on every
machine. A real-clock test then checks a small stall limit with no
solutions at all is honoured close to that limit, not to the fixed 1s poll
this used to have regardless of how small `stall` was. A short real CP-SAT
smoke test at the end checks the pieces work together.

    uv run finders/hunt/test_watchdog.py
"""

import sys
import threading
import time
from pathlib import Path

from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parent))
from watchdog import StallWatchdog, solve_with_watchdog

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


class FakeClockCallback(StallWatchdog):
    """A StallWatchdog driven by a clock the test controls, instead of a
    live solve's WallTime()."""

    def __init__(self, stall):
        super().__init__(stall)
        self.now = 0.0

    def WallTime(self):
        return self.now


cb = FakeClockCallback(stall=5)
check("not stalled before the clock is started or any solution found", not cb.stalled())
cb.now = 1.0
cb.on_solution_callback()
check("first_at records the first solution's wall time", cb.first_at == 1.0)
cb.now = 3.0
check("not stalled within the stall window", not cb.stalled())
cb.now = 7.0
check("stalled once the window elapses with no new solution", cb.stalled())
cb.now = 7.5
cb.on_solution_callback()
check("a new solution clears the stall", not cb.stalled())
check(
    "first_at still holds the first solution's time, not the second's",
    cb.first_at == 1.0,
)

# A solve that never finds any solution still has to end: `start()` (what
# solve_with_watchdog calls before the solve begins) arms the clock at t=0
# so `stalled()` can measure from the solve's own start, not from whenever
# a solution happens to arrive.
never_found = FakeClockCallback(stall=5)
never_found.now = 0.0
never_found.start()
check("armed at t=0, immediately not stalled", not never_found.stalled())
never_found.now = 4.0
check("still within the window, no solution ever found", not never_found.stalled())
never_found.now = 6.0
check(
    "a solve making no progress at all stalls once its own window elapses",
    never_found.stalled(),
)

# stall=0 disables the watchdog entirely, matching zombo-brainanas's own
# "0 means never stall" convention.
disabled = FakeClockCallback(stall=0)
disabled.now = 0.0
disabled.start()
disabled.now = 10_000.0
check(
    "stall=0 never reports stalled, however long the solve runs", not disabled.stalled()
)

# stalled() before start() (or before any solution) is never stalled --
# there's no clock running yet to have elapsed against.
unarmed = FakeClockCallback(stall=5)
unarmed.now = 10_000.0
check("never stalled if the clock was never armed", not unarmed.stalled())


class FakeSolver:
    """Blocks in Solve() until StopSearch() is called -- a stand-in for a
    CP-SAT solve that never returns on its own because it keeps searching
    for a better solution."""

    def __init__(self):
        self._stop = threading.Event()

    def Solve(self, model, callback):
        self._stop.wait(timeout=5)
        return "STOPPED" if self._stop.is_set() else "NEVER_STOPPED"

    def StopSearch(self):
        self._stop.set()


class FakeStalledAfter:
    """Reports stalled only once `calls_before` polls have happened, so the
    test controls exactly when solve_with_watchdog should stop the solve.
    No `.start()`/`.stall` -- solve_with_watchdog must tolerate a callback
    that doesn't have them."""

    def __init__(self, calls_before):
        self.calls_before = calls_before
        self.calls = 0

    def stalled(self):
        self.calls += 1
        return self.calls > self.calls_before


solver = FakeSolver()
callback = FakeStalledAfter(calls_before=0)
start = time.monotonic()
status = solve_with_watchdog(solver, model=None, callback=callback)
elapsed = time.monotonic() - start
check("a stalled solve is stopped, not left to finish on its own", status == "STOPPED")
check(
    "the watchdog stops it near its own poll interval, not the solver's timeout",
    elapsed < 3,
)


class RealClockCallback(StallWatchdog):
    """A StallWatchdog measuring real elapsed time from `start()`, for a
    real-time test of a small stall limit -- FakeClockCallback's
    test-driven clock can't stand in here since solve_with_watchdog's poll
    loop sleeps in real time regardless of what a fake clock says."""

    def __init__(self, stall):
        super().__init__(stall)
        self._t0 = None

    def start(self):
        self._t0 = time.monotonic()
        super().start()

    def WallTime(self):
        return time.monotonic() - self._t0


# The scenario Codex flagged in round 2: a solve with no solutions at all
# and a stall limit under a second. Before the fix, the clock only armed
# on the first poll (~1s in, on the old fixed 1s cadence) and polling
# never sped up for a small `stall`, so this could take ~2s regardless of
# asking for 0.3s. `start()` now arms the clock immediately and the poll
# interval is bounded by `stall`, so this should finish close to 0.3s.
no_solution_solver = FakeSolver()
small_stall_cb = RealClockCallback(stall=0.3)
start = time.monotonic()
status = solve_with_watchdog(no_solution_solver, model=None, callback=small_stall_cb)
elapsed = time.monotonic() - start
check("a sub-second stall limit with no solutions stops the solve", status == "STOPPED")
check(
    "it stops close to the requested limit, not the old ~2s floor",
    elapsed < 1.0,
)


class FakeRaisingSolver:
    """A solve that dies mid-search (a callback exception, a solver crash)
    instead of returning a status."""

    def Solve(self, model, callback):
        raise RuntimeError("solver crashed")

    def StopSearch(self):
        pass


try:
    solve_with_watchdog(
        FakeRaisingSolver(), model=None, callback=FakeStalledAfter(calls_before=999)
    )
    check("an exception in the solve thread propagates out, not KeyError", False)
except RuntimeError as exc:
    check(
        "an exception in the solve thread propagates out, not KeyError",
        str(exc) == "solver crashed",
    )
except KeyError:
    check("an exception in the solve thread propagates out, not KeyError", False)

# Real CP-SAT smoke test: an instantly-solved model finds its one solution
# and stops cleanly, without ever looking stalled.
m = cp_model.CpModel()
x = m.NewBoolVar("x")
m.Add(x == 1)
real_solver = cp_model.CpSolver()
real_solver.parameters.max_time_in_seconds = 5
real_solver.parameters.num_workers = 1
real_cb = StallWatchdog(stall=2)
real_status = solve_with_watchdog(real_solver, m, real_cb)
check(
    "a trivial real solve finishes normally through the same wrapper",
    real_status in (cp_model.OPTIMAL, cp_model.FEASIBLE),
)
check("its first solution's wall time was recorded", real_cb.first_at is not None)

sys.exit(0 if ok else 1)

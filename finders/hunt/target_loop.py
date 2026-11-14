"""The target-grid loop (#130), the one search the halver hunts
(`finders/halver/halver_hunt.py`) and the Doppelganger rank hunt
(`finders/doppelganger_rank/hunt.py`) run, each through its own hooks.

One seed: sample a target solution. While the check says `not_unique`, add
one step (a line, a clue) that holds in the target and fails in the second
solution. Stop at `unique`, a hit, returned as `Found`. Otherwise the seed
ends `Empty(reason)`, the reason opening with its class:

- `budget:` the seed's `--max-seconds` ran out, or `max_steps` steps were
  added and it is still not unique (the check after the last permitted step
  runs first, so a finish at the cap is a hit): a budget, never a proof;
- `timeout:` a solve reached `--time-limit` (no verdict);
- the hooks' own reasons: a sample that proves the board has no solution,
  no space, no separating step.

`Budget` holds the seed's seconds: every solve gets the smaller of
`--time-limit` and the seconds the seed has left, and `ran_out` names which
of the two a solve that reached its limit hit. A hunt that solves again
after the loop (the Doppelganger minimiser) reads the same `Budget`.

The hooks, one object per seed (`Hooks` gives the optional ones' defaults):

- `sample(limit)`: the target; None when the solve reached `limit`; or an
  `Empty` of the hook's own.
- `check(target, limit)`: an object with `status` (`unique`, `not_unique`
  or `timeout`) and the solutions `first` and `second`.
- `no_space(target, second, steps)`: an `Empty` when no step can fit, else
  None.
- `separate(target, second, steps, limit)`: the step to add, or an `Empty`.
  Here `limit` is `Budget.limit` itself, a callable giving the seconds left,
  not a number: a separating step may solve more than once.
- `add(choice)`: put the step on the board; returns the step's log fields.
- `log(fields)`: one step's log line: `step`, `check_s`, and the fields
  `add` returned, or `status: unique` at the finish.
"""

import time
from typing import Any, NamedTuple

from protocol import Empty


class Found(NamedTuple):
    """The seed's target and the check that called the board unique."""

    target: Any
    check: Any


class Budget:
    """The seed's seconds, from the moment it is made."""

    def __init__(self, time_limit, max_seconds, clock=time.monotonic):
        self.time_limit = time_limit
        self.max_seconds = max_seconds
        self.clock = clock
        self.deadline = clock() + max_seconds

    def limit(self):
        """The seconds the next solve gets."""
        return min(self.time_limit, self.deadline - self.clock())

    def ran_out(self, limit, what):
        """The Empty for a solve that reached `limit`: the seed's budget when
        that was what was left, `--time-limit` otherwise."""
        if limit < self.time_limit:
            return Empty(f"budget: {self.max_seconds:g} s ran out during {what}")
        return Empty(f"timeout: {what} ({self.time_limit:g} s)")


class Hooks:
    """The optional hooks' defaults: room for every step, no log."""

    def no_space(self, target, second, steps):
        return None

    def log(self, fields):
        pass


def target_loop(hooks, budget, max_steps, unit):
    """Run one seed (the module docstring). `unit` names a step in plural in
    the reasons: `lines`, `clues`."""
    sample_limit = budget.limit()
    target = hooks.sample(sample_limit)
    if isinstance(target, Empty):
        return target
    if target is None:
        return budget.ran_out(sample_limit, "sampling a target")
    steps = 0
    while True:
        check_limit = budget.limit()
        if check_limit <= 0:
            return Empty(f"budget: {budget.max_seconds:g} s after {steps} {unit}")
        t0 = budget.clock()
        check = hooks.check(target, check_limit)
        check_s = round(budget.clock() - t0, 3)
        if check.status == "unique":
            hooks.log({"step": steps, "check_s": check_s, "status": "unique"})
            return Found(target, check)
        if check.status == "timeout":
            return budget.ran_out(check_limit, f"the check after {steps} {unit}")
        if check.status != "not_unique":
            raise ValueError(
                f"check returned {check.status} on {unit} the target obeys"
            )
        if steps >= max_steps:
            return Empty(f"budget: {steps} {unit} added and still not unique")
        second = check.first if check.first != target else check.second
        empty = hooks.no_space(target, second, steps)
        if empty is not None:
            return empty
        choice = hooks.separate(target, second, steps, budget.limit)
        if isinstance(choice, Empty):
            return choice
        fields = hooks.add(choice) or {}
        steps += 1
        hooks.log({"step": steps, "check_s": check_s, **fields})

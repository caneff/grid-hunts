"""Pins `target_loop` (#130) on fake hooks and a fake clock: no solver.

- A hit: the loop adds one step per `not_unique` check and returns the
  unique check, logging each step and the finish.
- The seed's seconds run out: before a check, and during a check (a solve
  given less than `--time-limit`), each a `budget:` reason; a solve that
  reaches the full `--time-limit` is `timeout:`.
- The step cap: the check after the last permitted step runs first, so a
  finish at the cap is a hit and one step short is `budget:`.
- No space and no separation end the seed with the hook's own reason.
- A sample that times out ends the seed; a sample's own Empty passes through.
- A check status other than unique, not_unique or timeout raises.

    uv run finders/hunt/test_target_loop.py
"""

import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_checks import check, finish
from protocol import Empty
from target_loop import Budget, Found, Hooks, target_loop


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class Check(NamedTuple):
    status: str
    first: object = None
    second: object = None


TARGET, OTHER = "target", "other"


class Fake(Hooks):
    """Unique once `finish_at` steps are added. Each check costs
    `check_cost` seconds of the fake clock; `statuses` overrides a check's
    status by step."""

    def __init__(self, clock, finish_at=3, check_cost=0.0, statuses=None):
        self.clock, self.finish_at, self.check_cost = clock, finish_at, check_cost
        self.statuses = statuses or {}
        self.added, self.limits, self.logged = [], [], []
        self.space, self.separable, self.sampled = True, True, TARGET

    def sample(self, limit):
        self.limits.append(limit)
        return self.sampled

    def check(self, target, limit):
        self.limits.append(limit)
        self.clock.now += self.check_cost
        step = len(self.added)
        status = self.statuses.get(step)
        if status is None:
            status = "unique" if step >= self.finish_at else "not_unique"
        return Check(status, target, OTHER)

    def no_space(self, target, second, steps):
        if not self.space:
            return Empty(f"no space: after {steps} steps")
        return None

    def separate(self, target, second, steps, limit):
        assert (target, second) == (TARGET, OTHER), (target, second)
        if not self.separable:
            return Empty(f"no separating step after {steps}")
        return f"step{steps + 1}"

    def add(self, choice):
        self.added.append(choice)
        return {"choice": choice}

    def log(self, fields):
        self.logged.append(fields)


def run(fake, clock, max_steps=10, time_limit=30.0, max_seconds=100.0):
    budget = Budget(time_limit, max_seconds, clock=clock)
    return target_loop(fake, budget, max_steps=max_steps, unit="steps")


clock = Clock()
fake = Fake(clock)
found = run(fake, clock)
check(
    "a hit returns the target and the unique check",
    found == Found(TARGET, Check("unique", TARGET, OTHER)),
)
check(
    "a hit adds one step per not_unique check",
    fake.added == ["step1", "step2", "step3"],
)
check(
    "every step is logged with its number, then the finish",
    [e["step"] for e in fake.logged] == [1, 2, 3, 3]
    and fake.logged[-1]["status"] == "unique"
    and fake.logged[0]["choice"] == "step1",
)
check("each solve gets at most --time-limit", all(0 < s <= 30.0 for s in fake.limits))

# The seed's seconds run out before a check.
clock = Clock()
fake = Fake(clock, check_cost=40.0)
check(
    "seconds gone before a check is budget:",
    run(fake, clock) == Empty("budget: 100 s after 3 steps"),
)

# During a check: the solve was given what the seed had left, less than
# --time-limit.
clock = Clock()
fake = Fake(clock, check_cost=40.0, statuses={2: "timeout"})
check(
    "a check cut short by the seed's seconds is budget:",
    run(fake, clock) == Empty("budget: 100 s ran out during the check after 2 steps"),
)
clock = Clock()
fake = Fake(clock, statuses={1: "timeout"})
check(
    "a check that reaches --time-limit is timeout:",
    run(fake, clock) == Empty("timeout: the check after 1 steps (30 s)"),
)

# The step cap.
clock = Clock()
check(
    "a finish at the step cap is a hit",
    isinstance(run(Fake(clock), clock, max_steps=3), Found),
)
check(
    "one step short of a finish at the cap is budget:",
    run(Fake(clock), clock, max_steps=2)
    == Empty("budget: 2 steps added and still not unique"),
)

# No space and no separation.
fake = Fake(clock)
fake.space = False
check(
    "no space ends the seed with the hook's reason",
    run(fake, clock) == Empty("no space: after 0 steps"),
)
check("no space adds nothing", fake.added == [])
fake = Fake(clock, finish_at=5)
fake.separable = False
check(
    "no separation ends the seed with the hook's reason",
    run(fake, clock) == Empty("no separating step after 0"),
)

# The sample.
fake = Fake(clock)
fake.sampled = None
check(
    "a sample that reaches --time-limit is timeout:",
    run(fake, clock) == Empty("timeout: sampling a target (30 s)"),
)
fake.sampled = Empty("infeasible: no grid")
check(
    "a sample's own Empty passes through",
    run(fake, clock) == Empty("infeasible: no grid"),
)

# A check status the loop cannot read.
try:
    run(Fake(clock, statuses={0: "infeasible"}), clock)
    check("an unreadable check status raises", False)
except ValueError as error:
    check("an unreadable check status raises", "infeasible" in str(error))

finish()

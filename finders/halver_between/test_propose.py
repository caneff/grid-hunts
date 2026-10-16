"""The target-grid loop's stops, on a board started near a finish: the
recorded hit of `hit_fixture.py` with its seventh line taken away, so seed 0
needs a few more lines and gets them in about a second.

- A seed that finishes in exactly `--max-lines` lines is a hit: the check
  after the last permitted line runs before the budget refuses. One line
  fewer, and the seed ends on the line budget.
- Every solve gets at most the seconds the seed has left, never the whole
  `--time-limit` past the budget.
- A check that times out ends the seed as `Empty("timeout ...")`, or as a
  budget Empty when the seed's seconds were what ran out; it never crashes
  the hunt and is never a hit.

    uv run finders/halver_between/test_propose.py
"""

import random
import sys
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# isort: split
import hit_fixture
import hunt
import rules

START = hit_fixture.ADDED[:6] + hit_fixture.ADDED[7:]


def finder(max_lines=40, time_limit=30.0, max_seconds=120.0):
    return hunt.HalverBetweenFinder(
        max_cells=8,
        pool=3,
        time_limit=time_limit,
        max_lines=max_lines,
        max_seconds=max_seconds,
        verify_seconds=600.0,
        start=START,
    )


def propose(f):
    return f.propose(random.Random(0))


# With no budget in reach, seed 0 finishes after k more lines.
free = propose(finder())
assert isinstance(free, hunt.Hit), free
k = len(free.added) - len(START)
assert k >= 1, free

# The same seed with exactly k lines allowed is the same hit; with k - 1 it
# ends on the line budget.
at_limit = propose(finder(max_lines=k))
assert at_limit == free, at_limit
short = propose(finder(max_lines=k - 1))
assert isinstance(short, hunt.Empty), short
assert short.reason == f"budget: {k - 1} lines added and still not unique", short

# Every sample and check gets at most the seconds the seed has left.
limits = []
real_check, real_sample = rules.RuleModel.check, rules.RuleModel.sample


def check(self, time_limit):
    limits.append(time_limit)
    return real_check(self, time_limit=time_limit)


def sample(self, rng, time_limit):
    limits.append(time_limit)
    return real_sample(self, rng, time_limit)


with (
    mock.patch.object(rules.RuleModel, "check", check),
    mock.patch.object(rules.RuleModel, "sample", sample),
):
    bounded = propose(finder(time_limit=30.0, max_seconds=5.0))
assert isinstance(bounded, hunt.Hit), bounded
assert limits and all(0 < s <= 5.0 for s in limits), limits


# A check that times out ends the seed as Empty, named for the limit that
# was reached.
def timed_out(self, time_limit):
    return rules.RuleCheck("timeout")


with mock.patch.object(rules.RuleModel, "check", timed_out):
    plain = propose(finder(time_limit=10.0))
    budget = propose(finder(time_limit=30.0, max_seconds=5.0))
assert plain == hunt.Empty("timeout: the check after 0 lines (10s)"), plain
assert budget == hunt.Empty("budget: 5 s ran out during the check after 0 lines"), (
    budget
)

print("ok")

"""The rule check on Chris's board: its lines alone leave more than one
solution, a check's timeout is reported as a timeout, never as unique, and a
mark check's timeout never as held. A `digit_in` mark holds exactly when
every solution puts the digit in one of its cells, read on the 4x4 case of
test_brute.py, whose answer is known. A sample is a solution, None on a
timeout, and an error on lines with no solution. Workers pinned to 1.

    uv run finders/halver_between/test_rules.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rules

HERE = Path(__file__).resolve().parent
LINES = rules.load_lines(HERE / "board.json")

# The fixture's lines are the table of Chris's board switch on #39, circles
# first and last.
assert [rules.line_name(line) for line in LINES] == [
    "r4c3 | r4c4 r5c4 r5c5 r4c5 r4c6 r5c6 r6c6 r6c5 r6c4 | r6c3",
    "r8c3 | r7c3 r6c2 | r6c1",
    "r6c1 | r7c1 r8c1 r8c2 r9c2 r9c3 | r9c4",
    "r4c1 | r3c1 r2c1 r2c2 r3c2 | r4c2",
    "r7c9 | r8c9 r8c8 r8c7 | r7c7",
    "r9c4 | r9c5 r9c6 r8c6 r7c5 r7c4 | r8c3",
], LINES

base = rules.RuleModel(LINES)
result = base.check(time_limit=60)
assert result.status == "not_unique", result.status
# Both witnesses obey every line, read in plain Python, and they differ.
for solution in (result.first, result.second):
    assert all(rules.line_holds(solution, line) for line in LINES)
    assert len(solution.halvers) == 9
assert result.first != result.second

# A check given no time is a timeout, and a timeout is never unique.
rushed = base.check(time_limit=1e-6)
assert rushed.status == "timeout", rushed.status

# A mark check given no time is a timeout too, never "held".
mark = {"kind": "digit", "cell": "r6c1", "digit": 6}
assert base.mark_holds(mark, time_limit=10).status == "held"
rushed_mark = base.mark_holds(mark, time_limit=1e-6)
assert rushed_mark.status == "timeout", rushed_mark

# digit_in on the 4x4 case whose one answer has rows 3214 / 4123 / 2341 /
# 1432: the 1 of row 1 is at r1c3, so "1 in r1c4 or r1c3 or r1c2" holds (the
# 1 in the middle cell, so every listed cell is read) and "1 in r1c1 or r1c2"
# does not.
small = rules.RuleModel(
    [
        rules.Line((2, 3), ((3, 2), (2, 1)), (1, 0)),
        rules.Line((1, 3), ((1, 2), (0, 2)), (1, 1)),
    ],
    n=4,
    box=(2, 2),
)
held = small.mark_holds(
    {"kind": "digit_in", "cells": ["r1c4", "r1c3", "r1c2"], "digit": 1}
)
assert held.status == "held", held
broken = small.mark_holds({"kind": "digit_in", "cells": ["r1c1", "r1c2"], "digit": 1})
assert broken.status == "not_held", broken
assert broken.counterexample.digits[0][2] == 1, broken

# A sample is a solution, or None when its solve has no time; lines with no
# solution at all raise rather than read as a timeout. The third line's
# circles are equal in the 4x4 case's one answer, so no solution is left.
rng = random.Random(39)
drawn = small.sample(rng, time_limit=10)
assert all(rules.line_holds(drawn, line) for line in small.lines), drawn
assert base.sample(rng, time_limit=1e-6) is None
small.add_line(rules.Line((2, 0), ((2, 1), (2, 2)), (2, 3)))
try:
    small.sample(rng, time_limit=10)
except ValueError as error:
    assert "INFEASIBLE" in str(error), error
else:
    raise AssertionError("a sample of lines with no solution returned")

print("ok")

"""The rule check on Chris's board: L1-L5 alone leave more than one solution,
and a timeout is reported as a timeout, never as unique. Workers pinned to 1.

    uv run finders/halver_between/test_rules.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rules

HERE = Path(__file__).resolve().parent
LINES = rules.load_lines(HERE / "board.json")

# The fixture's lines are #39's table, circles first and last.
assert [rules.line_name(line) for line in LINES] == [
    "r4c3 | r4c4 r5c4 r5c5 r4c5 r4c6 r5c6 r6c6 r6c5 r6c4 | r6c3",
    "r8c3 | r7c3 r6c2 | r6c1",
    "r6c1 | r7c1 r8c1 r8c2 r9c2 r9c3 | r9c4",
    "r4c1 | r3c1 r2c1 r2c2 r3c2 | r4c2",
    "r8c3 | r8c4 r7c5 r8c6 r9c6 r9c5 | r9c4",
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
assert not rushed.unique

print("ok")

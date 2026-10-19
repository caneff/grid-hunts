"""The backtracking check settles the 23-line board of #54's note (#59): the
target-grid loop's 23 lines, `fixtures/unique_23.json`, the unique fixture
without the 30 three-cell lines #54 added. Within the lockout hunt's own
verify budget (`hunt.DEFAULTS["verify_seconds"]`) on one worker it returns
the one solution the CP-SAT check finds. #54's run did not apply the drawing
rules (4 of the lines cross an earlier one diagonally), so the board times
the search; it is not a hit. Slow (about 200 s), so it runs in `just test-slow`, not the gate.

    uv run finders/halver_lockout/test_unique_23.py
"""

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import brute
import hunt
import rules

BUDGET = hunt.DEFAULTS["verify_seconds"]

lines = rules.load_lines(HERE / "fixtures" / "unique_23.json")
assert len(lines) == 23, len(lines)
answer = rules.RuleModel(lines).check(time_limit=120)
assert answer.status == "unique", answer.status

started = time.monotonic()
found = brute.solutions(lines, 9, (3, 3), limit=2, deadline=started + BUDGET)
seconds = time.monotonic() - started
assert found == [(answer.first.digits, answer.first.halvers)], found

print(f"ok unique in {seconds:.1f} s")

"""Spec #52 end to end, in the gate, on one recorded hit (`hit_fixture.py`):

- the hit's 24 lines check `unique` with the CP-SAT rule model, and its one
  solution is the recorded one;
- every line keeps the drawing rules against the lines before it;
- `record` writes the very link the decision log publishes, which decodes
  back to exactly the hit's lines as type 407 with `"solverIgnored": true`
  and nothing entered, and `candidate_from_record` reads the record back to
  the same hit;
- `verify` passes the hit (the backtracking check finds one solution, the
  hit's own), and refuses it with an illegal line, with a solution that is
  not the backtracking check's, and when its search has no time.

About 35 s, most of it the two backtracking searches. What this seam is
blind to. Seam: `just check`. Blind to: the slow hunt test
(`just test-slow`), a hunt's own output, and how a found grid reads once it
is built into a puzzle link. So it is blind to whether the hunt still finds
hits: that is `test_hunt.py`'s job, a full hunt in `just test-slow`.

    uv run finders/halver_lockout/test_spec_52_e2e.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# isort: split
import candidates
import hit_fixture
import hunt
import rules
from sudoku_kit.link_codec import decode_puzzle

ADDED = hit_fixture.ADDED

check = rules.RuleModel(list(ADDED)).check(time_limit=60)
assert check.status == "unique", check.status
assert check.first == hit_fixture.SOLUTION, check.first

drawn = []
for line in ADDED:
    reason = candidates.shape_violation(candidates.path_of(line), drawn)
    assert reason is None, (rules.line_name(line), reason)
    drawn.append(line)

finder = hunt.HalverLockoutFinder(**hunt.DEFAULTS)
hit = hunt.Hit(ADDED, hit_fixture.SOLUTION)
record = finder.record(hit)
assert record["link"] == hit_fixture.LINK, record["link"]
doc = decode_puzzle(record["link"])
assert rules.lines_from_doc(doc) == list(ADDED)
lockout = [c for c in doc["puzzle"]["constraints"] if c.get("type") == 407]
assert len(lockout) == 1 and lockout[0]["solverIgnored"] is True, lockout
assert {c["type"] for c in doc["puzzle"]["constraints"]} == {0, 1, 407}
assert all(cell == {} for cell in doc["puzzle"]["cells"]), "entered marks kept"
assert record["table"] == [
    f"L{i} | {row}" for i, row in enumerate(hit_fixture.TABLE, start=1)
], record["table"]
assert record["digits"] == hit_fixture.DIGITS, record["digits"]
assert record["halvers"] == hit_fixture.HALVERS, record["halvers"]
assert finder.candidate_from_record(record) == hit

assert finder.verify(hit) == hunt.Verdict(True), finder.verify(hit)

# r8c3 is the body of L6, r8c2 | r8c3 | r8c4.
reused = rules.Line((7, 1), ((7, 2),), (8, 3))
illegal = finder.verify(hunt.Hit((*ADDED, reused), hit.solution))
assert not illegal.ok, illegal
assert illegal.reason.endswith("body cell r8c3 is already on a line"), illegal

no_halvers = rules.Solution(hit.solution.digits, frozenset())
other = finder.verify(hunt.Hit(ADDED, no_halvers))
assert other == hunt.Verdict(
    False, "the backtracking check's one solution is not the hit's"
), other

finder.verify_seconds = 0.0
rushed = finder.verify(hit)
assert rushed == hunt.Verdict(
    False, "the backtracking check reached its 0 s limit: no verdict"
), rushed

print("ok")

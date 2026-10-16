"""Spec #39 end to end, in the gate, on one recorded hit (`hit_fixture.py`):

- Chris's six lines plus the hit's 11 check `unique` with the CP-SAT rule
  model, and each of his 23 marks holds in that one solution;
- every added line keeps Chris's shape rules against the lines before it;
- `record` writes the line table and the very link the decision log
  publishes, which decodes back to exactly his six lines plus the hit's, in
  his line style, with every entered digit, colour and pencil mark cleared,
  and `candidate_from_record` reads the record back to the same hit;
- `verify` passes the hit (the backtracking check finds one solution, the
  hit's own), and refuses it with an illegal added line, with a solution
  that is not the backtracking check's, and when its search has no time.

What this seam is blind to. Seam: `just check`. Blind to: the slow
halver/between hunt test (`just test-slow`), a hunt's own output, and how a
found grid reads once it is built into a puzzle link. So it is blind to
whether the hunt still finds hits: that is `test_hunt.py`'s job, a full hunt
run in `just test-slow`.

    uv run finders/halver_between/test_spec_39_e2e.py
"""

import json
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
LINES = hunt.BOARD + list(ADDED)

# Unique, and Chris's marks hold in the one solution.
board = rules.RuleModel(LINES)
check = board.check(time_limit=60)
assert check.status == "unique", check.status
marks = json.loads((HERE / "marks.json").read_text())
assert len(marks) == 23, len(marks)
for mark in marks:
    held = board.mark_holds(mark, time_limit=60)
    assert held.status == "held", (rules.mark_name(mark), held)

# Each added line is a legal shape on the lines drawn before it.
drawn = list(hunt.BOARD)
for line in ADDED:
    reason = candidates.shape_violation(candidates.path_of(line), drawn)
    assert reason is None, (rules.line_name(line), reason)
    drawn.append(line)

# The record: the published link, decoding to the board's lines plus the
# hit's, in Chris's style, nothing entered; the table numbered on from L7.
finder = hunt.HalverBetweenFinder(
    max_cells=8,
    pool=20,
    time_limit=30.0,
    max_lines=40,
    max_seconds=120.0,
    verify_seconds=600.0,
)
hit = hunt.Hit(ADDED, check.first)
record = finder.record(hit)
assert record["link"] == hit_fixture.LINK, record["link"]
doc = decode_puzzle(record["link"])
assert rules.lines_from_doc(doc) == LINES
assert all(cell == {} for cell in doc["puzzle"]["cells"]), "entered marks kept"
(group,) = [
    c for c in doc["puzzle"]["constraints"] if c.get("type") == rules.BETWEEN_LINE
]
(board_group,) = [
    c
    for c in hunt.BOARD_DOC["puzzle"]["constraints"]
    if c.get("type") == rules.BETWEEN_LINE
]
assert group["style"] == board_group["style"], group["style"]
assert record["table"] == [
    f"L{i} | {row}" for i, row in enumerate(hit_fixture.TABLE, start=7)
], record["table"]
assert finder.candidate_from_record(record) == hit

# verify passes the hit, and refuses each kind of bad hit with its reason.
assert finder.verify(hit) == hunt.Verdict(True), finder.verify(hit)

reused = rules.Line((4, 0), ((4, 1),), (3, 1))  # r5c2 is the first line's body
illegal = finder.verify(hunt.Hit((*ADDED, reused), check.first))
assert not illegal.ok, illegal
assert illegal.reason.endswith("body cell r5c2 is already on a line"), illegal

no_halvers = rules.Solution(check.first.digits, frozenset())
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

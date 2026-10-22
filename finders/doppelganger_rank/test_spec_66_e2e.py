"""Spec #66 end to end, in the gate, on one recorded 9x9 hit
(`fixtures/hit_9x9.json`, seed 72 of the hunt of record, #72: the fewest
added clues, 11, of its 16 hits):

- Chris's four opening clues plus the hit's 11 check `unique`, the one grid
  is the hit's solution, and each of his five marks holds in it.
- `verify` passes the hit: the rule reader finds every rule and clue kept,
  and the second model re-proves it unique. It refuses the hit with its
  last added clue dropped, naming a second grid that keeps every other
  clue, and refuses it as timed out, never unique, when the re-proof gets
  no time.
- `record` writes the recorded hit back, `candidate_from_record` reads it
  to the same hit, and its link is the one the hunt wrote, the solution
  entered in the grid.

What this seam is blind to. Seam: `just check`. Blind to: the slow 9x9
hunt test (`test_hunt_9x9.py`, `just test-slow`), so to whether the hunt
still finds a 9x9 hit, and to how the hit reads as a puzzle.

    uv run finders/doppelganger_rank/test_spec_66_e2e.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# isort: split
import hunt
import rules
from check import read_board
from links import link_doc
from model import RankModel
from sudoku_kit.link_codec import decode_puzzle, encode_link

fixture = json.loads((HERE / "fixtures" / "hit_9x9.json").read_text())
record = fixture["record"]
n, box, opening, marks = read_board(HERE / "fixtures" / "opening_9x9.json")
finder = hunt.DoppelgangerRankFinder(None, 30.0, 36, 300.0, 0, 4)
hit = finder.candidate_from_record(record)
assert record["clues"][:4] == opening and hit.added == 11, record

# Unique, its one grid the hit's, and Chris's marks hold in it.
check = RankModel(n, box, record["clues"]).check(time_limit=60)
assert check.status == "unique" and check.first == hit.solution, check
reading = rules.read(hit.solution, box)
for mark in marks:
    if mark["kind"] == "digit":
        r, c = rules.parse_cell(mark["cell"])
        assert hit.solution[r][c] == mark["digit"], mark
    else:
        assert reading.missing[mark["unit"]] == mark["digit"], mark

# verify passes the hit, and refuses a loose one and a rushed one.
assert finder.verify(hit) == hunt.Verdict(True), finder.verify(hit)
loose = hit._replace(clues=hit.clues[:-1], added=10)
verdict = finder.verify(loose)
assert verdict.reason.startswith("not unique: a second grid "), verdict
words = verdict.reason.removeprefix("not unique: a second grid ").split()
second = tuple(tuple(map(int, word)) for word in words[1::2])
other = rules.read(second, box)
assert second != hit.solution and not other.violations, second
assert not other.broken_clues(loose.clues), other.broken_clues(loose.clues)
rushed = hunt.DoppelgangerRankFinder(None, 1e-9, 36, 300.0, 0, 4)
assert rushed.verify(hit) == (False, "timeout: the re-proof reached 1e-09 s")

# The record, read back, and the link the hunt wrote for it.
assert finder.record(hit) == record, finder.record(hit)
assert encode_link(link_doc(record)) == fixture["link"]
cells = decode_puzzle(fixture["link"])["puzzle"]["cells"]
side = n + 4
for r, row in enumerate(hit.solution):
    for c, digit in enumerate(row):
        assert cells[r * side + c] == {"value": digit}, (r, c, cells[r * side + c])

print("ok")

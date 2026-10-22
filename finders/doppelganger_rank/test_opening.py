"""The check on Chris's 9x9 opening (#68): four rank clues, five marks
(`fixtures/opening_9x9.json`, read from #66 § The opening board). The
expectation is the result first recorded in
`docs/research/2026-10-22-doppelganger-rank-decision-log.md`, written after
that run:

- The opening is not unique: the check prints two different solutions, and
  the rule reader finds every rule and all four clues kept in each.
- Every mark held: r1c1 = 8, r1c9 = 1, r5c1 = 9, r5c9 = 0, c9 misses 9.
  Each printed solution keeps each mark. Exit 0.

The leading-digit buckets (#75) took the five mark proofs from 49.9 s to
under 1 s on one worker. The test gives each solve 10 s: the model without
them times out on three marks, so a lost speed-up fails here, and a slower
machine still has ten times the room it needs.

    uv run finders/doppelganger_rank/test_opening.py
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import rules
from printed import solutions

BOARD = HERE / "fixtures" / "opening_9x9.json"

done = subprocess.run(
    [sys.executable, str(HERE / "check.py"), str(BOARD), "--time-limit", "10"],
    capture_output=True,
    text=True,
)
out = done.stdout.splitlines()
assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
assert out[0] == "4 rank clues: not_unique", out
assert out[-5:] == [
    "held      r1c1 = 8",
    "held      r1c9 = 1",
    "held      r5c1 = 9",
    "held      r5c9 = 0",
    "held      c9 misses 9",
], out

board = json.loads(BOARD.read_text())
printed = solutions(out)
assert len(printed) == 2 and printed[0] != printed[1], printed
for grid in printed:
    reading = rules.read(grid, (3, 3))
    assert reading.violations == [], (grid, reading.violations)
    assert reading.broken_clues(board["clues"]) == [], grid
    assert grid[0][0] == 8 and grid[0][8] == 1, grid
    assert grid[4][0] == 9 and grid[4][8] == 0, grid
    assert reading.missing["c9"] == 9, grid

print("test_opening: ok")

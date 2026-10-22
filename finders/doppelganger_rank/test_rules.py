"""The rule reader on hand-worked 4x4 grids: every Doppelganger rule, each
unit's missing digit, all 16 numbers and their ranks, and each rank clue.

- Grid A keeps every rule. Its 16 numbers are all different, so they rank
  1 to 16; column 1 read from the top is 0143, a number with a leading 0,
  and it ranks lowest.
- The Klein grid (cell = row xor column) breaks the box rule and every row
  misses 4, but its numbers still rank: each of 0123, 1032, 2301 and 3210 is
  made four times, so the four share a rank and the next three ranks are
  skipped (1, 5, 9, 13).
- Grid Z keeps every rule but the 0 rule: three of its 0s sit where two or
  three of the units miss the same digit.

    uv run finders/doppelganger_rank/test_rules.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rules

BOX = (2, 2)

GRID_A = ((0, 3, 4, 2), (1, 2, 3, 0), (4, 0, 2, 1), (3, 1, 0, 4))
a = rules.read(GRID_A, BOX)
assert a.violations == [], a.violations
assert a.missing == {
    "r1": 1, "r2": 4, "r3": 3, "r4": 2,
    "c1": 2, "c2": 4, "c3": 1, "c4": 3,
    "b1": 4, "b2": 1, "b3": 2, "b4": 3,
}, a.missing  # fmt: skip
# Each number by hand, then its rank among the 16 sorted by hand:
# 0143 0234 0321 0342 1023 1204 1230 2014 2430 3104 3201 3410 4013 4021 4102 4320
assert a.numbers == {
    ("r1", "left"): "0342", ("r1", "right"): "2430",
    ("r2", "left"): "1230", ("r2", "right"): "0321",
    ("r3", "left"): "4021", ("r3", "right"): "1204",
    ("r4", "left"): "3104", ("r4", "right"): "4013",
    ("c1", "top"): "0143", ("c1", "bottom"): "3410",
    ("c2", "top"): "3201", ("c2", "bottom"): "1023",
    ("c3", "top"): "4320", ("c3", "bottom"): "0234",
    ("c4", "top"): "2014", ("c4", "bottom"): "4102",
}, a.numbers  # fmt: skip
assert a.ranks == {
    ("r1", "left"): 4, ("r1", "right"): 9,
    ("r2", "left"): 7, ("r2", "right"): 3,
    ("r3", "left"): 14, ("r3", "right"): 6,
    ("r4", "left"): 10, ("r4", "right"): 13,
    ("c1", "top"): 1, ("c1", "bottom"): 12,
    ("c2", "top"): 11, ("c2", "bottom"): 5,
    ("c3", "top"): 16, ("c3", "bottom"): 2,
    ("c4", "top"): 8, ("c4", "bottom"): 15,
}, a.ranks  # fmt: skip

held = [
    {"line": "c1", "end": "top", "rank": 1},
    {"line": "r3", "end": "left", "rank": 14},
]
assert a.broken_clues(held) == [], a.broken_clues(held)
wrong = [
    {"line": "c1", "end": "top", "rank": 2},
    {"line": "r2", "end": "right", "rank": 3},
]
assert a.broken_clues(wrong) == ["c1 from the top ranks 1, not 2"], a.broken_clues(
    wrong
)

KLEIN = ((0, 1, 2, 3), (1, 0, 3, 2), (2, 3, 0, 1), (3, 2, 1, 0))
k = rules.read(KLEIN, BOX)
assert k.numbers[("r1", "left")] == "0123" == k.numbers[("c4", "bottom")]
assert sorted(k.ranks.values()) == [1] * 4 + [5] * 4 + [9] * 4 + [13] * 4, k.ranks
assert k.ranks[("r1", "left")] == 1 and k.ranks[("r2", "left")] == 5, k.ranks
assert k.ranks[("r3", "right")] == 5 and k.ranks[("c4", "top")] == 13, k.ranks
assert "b1 holds 0 twice" in k.violations, k.violations
assert "b1 holds 1 twice" in k.violations, k.violations
assert "r1 and r2 both miss 4" in k.violations, k.violations
assert "c1 and c2 both miss 4" in k.violations, k.violations
assert k.missing["b1"] is None, k.missing  # two 0s: no single missing digit

GRID_Z = ((0, 1, 2, 3), (2, 3, 0, 4), (1, 0, 4, 2), (3, 4, 1, 0))
z = rules.read(GRID_Z, BOX)
assert z.violations == [
    "r1c1 holds 0 and its row, column and box miss 4, 4, 4",
    "r2c3 holds 0 and its row, column and box miss 1, 3, 1",
    "r3c2 holds 0 and its row, column and box miss 3, 2, 2",
], z.violations

no_zero = ((1, 3, 4, 2), *GRID_A[1:])
assert "r1 has no 0" in rules.read(no_zero, BOX).violations
too_big = ((0, 3, 5, 2), *GRID_A[1:])
assert "r1c3 holds 5, outside 0..4" in rules.read(too_big, BOX).violations

print("test_rules: ok")

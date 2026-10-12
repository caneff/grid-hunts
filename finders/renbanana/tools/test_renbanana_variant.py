"""`difference` and `banana_rule` on the shared Renbanana pieces (#759).

    uv run finders/renbanana/tools/test_renbanana_variant.py

The defaults must leave Renbanana alone (`test_renbanana_model.py` and the
rest are the guard); these tests drive the new parameters: the published
opener grid passes at renban/5 and fails at nabner/4 on a consecutive pair in
one banana group, a nabner group repeating a digit across two boxes is a
violation, and the model's rule-5 pieces move their boundary with
`difference`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import renbanana_model as rm
import renbanana_verify as rv
from test_renbanana_model import digits_and_shading, pin, status_of

# The published "German Chocolate Renbanana" (docs/research/renbanana/
# OPENER-UNIQUE.md, "Published version"): digits from the puzzle's metadata,
# shading solved for with probe_circle_pattern --givens (its only
# solution; the doc does not record it).
PUBLISHED_DIGITS = [
    "796831452",
    "845276139",
    "123459786",
    "954382617",
    "381764295",
    "672915348",
    "517693824",
    "269148573",
    "438527961",
]
PUBLISHED_SHADING = [
    "bbbCbCbbC",
    "bCbCbbCbC",
    "CbCbbCbCb",
    "bbbCbCbCb",
    "bbbbCbbCb",
    "bCCCbbbCb",
    "CbbbCCCbb",
    "bCbCbbbCb",
    "bbbbCbbbC",
]
PUBLISHED_CIRCLES = [
    (int(s[1]) - 1, int(s[3]) - 1)
    for s in [
        "r1c6",
        "r1c9",
        "r2c3",
        "r2c4",
        "r2c6",
        "r2c7",
        "r2c8",
        "r3c1",
        "r3c7",
        "r4c1",
        "r4c6",
        "r4c9",
        "r6c8",
        "r7c6",
        "r8c3",
        "r8c4",
        "r9c8",
        "r9c9",
    ]
]


def published():
    grid = {(r, c): int(PUBLISHED_DIGITS[r][c]) for r, c in rv.cells()}
    is_choc = {(r, c): PUBLISHED_SHADING[r][c] == "C" for r, c in rv.cells()}
    return grid, is_choc


def test_published_grid_passes_renban_difference_5():
    grid, is_choc = published()
    assert rv.check(grid, is_choc, PUBLISHED_CIRCLES) == []
    assert rv.check(grid, is_choc, PUBLISHED_CIRCLES, 5, "renban") == []


def test_published_grid_fails_nabner_difference_4():
    grid, is_choc = published()
    bad = rv.check(grid, is_choc, difference=4, banana_rule="nabner")
    pairs = [line for line in bad if "holds consecutive digits" in line]
    assert pairs, bad
    assert all(line.startswith("rule 6: banana group at") for line in pairs)


def test_nabner_names_the_consecutive_pair():
    grid = dict.fromkeys(rv.cells(), 9)
    grid[0, 0], grid[0, 1], grid[1, 0] = 4, 5, 8
    is_choc = dict.fromkeys(rv.cells(), True)
    for p in ((0, 0), (0, 1), (1, 0)):
        is_choc[p] = False
    got = [x for x in rv.check(grid, is_choc, banana_rule="nabner") if "rule 6" in x]
    assert got == [
        "rule 6: banana group at (0, 0) holds consecutive digits "
        "4 at r1c1 and 5 at r1c2"
    ]


def test_nabner_repeat_across_two_boxes_is_a_violation():
    # an L of banana cells r3c3, r3c4, r4c4: r3c3 and r4c4 are in different
    # boxes and hold the same 7; r3c4 holds 1, two away from neither
    grid = dict.fromkeys(rv.cells(), 9)
    grid[2, 2], grid[2, 3], grid[3, 3] = 7, 1, 7
    is_choc = dict.fromkeys(rv.cells(), True)
    for p in ((2, 2), (2, 3), (3, 3)):
        is_choc[p] = False
    got = [x for x in rv.check(grid, is_choc, banana_rule="nabner") if "rule 6" in x]
    assert got == [
        "rule 6: banana group at (2, 2) repeats digits 7 at r3c3 and 7 at r4c4"
    ]
    # the same group with 1 and 3 and 7 is a legal nabner group
    grid[3, 3] = 3
    got = [x for x in rv.check(grid, is_choc, banana_rule="nabner") if "rule 6" in x]
    assert got == []


def test_unknown_banana_rule_is_refused():
    grid, is_choc = published()
    try:
        rv.check(grid, is_choc, banana_rule="renbn")
    except ValueError:
        return
    raise AssertionError("a misspelt banana_rule was accepted")


def test_difference_moves_the_rule_5_boundary():
    grid = dict.fromkeys(rv.cells(), 1)
    grid[4, 4], grid[4, 5] = 3, 7  # a gap of 4
    is_choc = dict.fromkeys(rv.cells(), False)
    is_choc[4, 4] = is_choc[4, 5] = True
    five = [x for x in rv.check(grid, is_choc) if "rule 5" in x]
    four = [x for x in rv.check(grid, is_choc, difference=4) if "rule 5" in x]
    assert len(five) == 1 and four == []


def test_model_difference():
    pair = {(4, 4), (4, 5)}
    for diff, lo, hi, want in (
        (4, 3, 7, "OPTIMAL"),  # a gap of 4 passes at 4
        (4, 3, 6, "INFEASIBLE"),
        (5, 3, 7, "INFEASIBLE"),
    ):
        m, d, choc = digits_and_shading()
        rm.whisper(m, d, choc, difference=diff)
        pin(m, choc, pair)
        m.add(d[4, 4] == lo)
        m.add(d[4, 5] == hi)
        assert status_of(m) == want, ("whisper", diff, lo, hi)

        is_choc = dict.fromkeys(rm.CELLS, False) | dict.fromkeys(pair, True)
        m, d, _ = digits_and_shading()
        rm.whisper_on_shading(m, d, is_choc, difference=diff)
        m.add(d[4, 4] == lo)
        m.add(d[4, 5] == hi)
        assert status_of(m) == want, ("whisper_on_shading", diff, lo, hi)

        grid = dict.fromkeys(rm.CELLS, 1)
        grid[4, 4], grid[4, 5] = lo, hi
        m, _, choc = digits_and_shading()
        rm.whisper_on_digits(m, choc, grid, difference=diff)
        pin(m, choc, pair)
        assert status_of(m) == want, ("whisper_on_digits", diff, lo, hi)


if __name__ == "__main__":
    test_published_grid_passes_renban_difference_5()
    test_published_grid_fails_nabner_difference_4()
    test_nabner_names_the_consecutive_pair()
    test_nabner_repeat_across_two_boxes_is_a_violation()
    test_unknown_banana_rule_is_refused()
    test_difference_moves_the_rule_5_boundary()
    test_model_difference()
    print("OK")

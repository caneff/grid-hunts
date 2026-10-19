"""The lockout candidate module (#55): a path in, accepted or refused under
the drawing rules, each rule by name on its own fixture. Then the separating
lines the hunt draws from: on the not-unique fixture's two solutions, every
listed line is legal, holds in the target and fails in the second solution,
once each and shortest first; on a 4x4 board it lists exactly what a brute
force over every king path finds. Then the cell-counting helpers.

    uv run finders/halver_lockout/test_candidates.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import candidates
import rules
from rules import Line, parse_cell


def path(*names):
    return tuple(parse_cell(name) for name in names)


def line(*names):
    cells = path(*names)
    return Line(cells[0], cells[1:-1], cells[-1])


# L1 runs straight along row 4; L2 takes a diagonal step r7c3 -> r6c2.
DRAWN = [line("r4c3", "r4c4", "r4c5"), line("r8c3", "r7c3", "r6c2", "r6c1")]


def violation(*names):
    return candidates.shape_violation(path(*names), DRAWN)


# Accepted: free cells; a diamond shared with L1 (r4c3); both diamonds
# shared with L1, through the free r5c4.
assert violation("r1c4", "r1c5", "r1c6") is None
assert violation("r4c3", "r3c3", "r2c3") is None
assert violation("r4c3", "r5c4", "r4c5") is None


# Refused, one rule each, the reason naming it.
def refuses(reason, *names):
    got = violation(*names)
    assert got is not None and reason in got, (names, got)


rules_seen = [
    ("is not a king step", ("r1c4", "r1c6", "r1c7")),
    ("revisits r1c5", ("r1c4", "r1c5", "r2c4", "r1c5", "r1c6")),
    ("no body cell", ("r1c4", "r1c5")),
    # A body cell on L1's body, then on L1's diamond.
    ("body cell r4c4 is already on a line", ("r3c3", "r4c4", "r3c5")),
    ("body cell r4c3 is already on a line", ("r3c3", "r4c3", "r5c3")),
    ("diamond r4c4 is another line's body cell", ("r4c4", "r3c4", "r2c4")),
    # r6c3 -> r7c2 crosses L2's r7c3 -> r6c2 (its diamond r8c3 is shared).
    ("crosses line r8c3 | r7c3 r6c2 | r6c1", ("r6c3", "r7c2", "r8c3")),
    # r1c5 -> r2c6 and r2c5 -> r1c6 are the two diagonals of one 2x2.
    ("crosses itself", ("r1c5", "r2c6", "r2c5", "r1c6")),
]
for reason, names in rules_seen:
    refuses(reason, *names)


def separates(target, second, found, lines, gap):
    drawn = Line(found[0], tuple(found[1:-1]), found[-1])
    return (
        rules.line_holds(target, drawn, gap=gap)
        and not rules.line_holds(second, drawn, gap=gap)
        and candidates.shape_violation(found, lines) is None
    )


def same_lines(paths):
    """Each path with its reverse, as one line."""
    return [frozenset((p, p[::-1])) for p in paths]


def king_paths(prefix, n, cap):
    """Every king path of 3 to `cap` cells on an n x n board that starts
    with `prefix`."""
    if len(prefix) >= 3:
        yield prefix
    if len(prefix) == cap:
        return
    r, c = prefix[-1]
    for q in ((r + dr, c + dc) for dr, dc in candidates.STEPS):
        if 0 <= q[0] < n and 0 <= q[1] < n and q not in prefix:
            yield from king_paths((*prefix, q), n, cap)


def lists_brute_force(lines, n, box, gap, cap):
    """The walk lists, once each and shortest first, exactly the lines a
    brute force over every king path of at most `cap` cells finds on the
    board's two witnesses. Returns the brute force's line lengths."""
    check = rules.RuleModel(lines, n=n, box=box, gap=gap).check(time_limit=60)
    assert check.status == "not_unique", check.status
    target, second = check.first, check.second
    brute = {
        pair
        for a in ((r, c) for r in range(n) for c in range(n))
        for p in king_paths((a,), n, cap)
        if separates(target, second, p, lines, gap)
        for pair in same_lines([p])
    }
    found = candidates.separating_paths(target, second, lines, max_cells=cap, gap=gap)
    assert all(separates(target, second, p, lines, gap) for p in found)
    assert len(set(same_lines(found))) == len(found), "a line listed twice"
    assert [len(p) for p in found] == sorted(len(p) for p in found)
    assert set(same_lines(found)) == brute, (len(found), len(brute))
    return {len(next(iter(pair))) for pair in brute}


# On 4x4 (2x2 boxes, gap 2), with one line drawn. Values there run 0.5 to
# 4, so few lines hold: on these witnesses none is longer than four cells,
# and the walk, run to six, lists none either.
SMALL = [line("r1c1", "r2c2", "r3c3")]
assert lists_brute_force(SMALL, 4, (2, 2), gap=2, cap=6) == {3, 4}

# On 9x9, at the gap of 4, with the not-unique fixture's three lines drawn.
FIXTURE = rules.load_lines(HERE / "fixtures" / "not_unique.json")
assert lists_brute_force(FIXTURE, 9, (3, 3), gap=rules.GAP, cap=5) == {3, 4, 5}

# The cell-counting helpers. A line with both diamonds already drawn takes
# only its body; a fresh line takes every cell.
assert candidates.new_cells(path("r4c3", "r5c4", "r4c5"), DRAWN) == 1
assert candidates.new_cells(path("r1c4", "r1c5", "r1c6"), DRAWN) == 3
assert candidates.free_cell_count(DRAWN, 9) == 81 - 7
assert candidates.free_cell_count([], 9) == 81
check = rules.RuleModel(SMALL, n=4, box=(2, 2), gap=2).check(time_limit=60)
target, second = check.first, check.second
cells = [(r, c) for r in range(4) for c in range(4)]
differ = [cell for cell in cells if target.doubled(cell) != second.doubled(cell)]
assert not candidates.no_space(target, second, [])
cover = Line((0, 0), tuple(differ), (0, 0))
assert candidates.no_space(target, second, [cover])
assert not candidates.no_space(target, second, [cover._replace(body=differ[1:])])

print("ok")

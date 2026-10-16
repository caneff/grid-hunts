"""The candidate-line function: a path in, accepted or rejected under Chris's
shape rules (spec #39, Q8), on his board's six lines. Then the enumeration
the hunt draws from: every line it gives is a legal shape that holds in the
target and fails in the second solution, and at three cells it gives exactly
what a naive walk over every king path finds.

    uv run finders/halver_between/test_candidates.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import candidates
import rules
from rules import parse_cell

HERE = Path(__file__).resolve().parent
BOARD = rules.load_lines(HERE / "board.json")


def path(*names):
    return tuple(parse_cell(name) for name in names)


def violation(*names):
    return candidates.shape_violation(path(*names), BOARD)


# Accepted: free cells; a circle shared with L1 (r4c3); and both circles
# shared, r8c3 (L2 and L6) and r9c4 (L3 and L6), through the free r8c4.
assert violation("r1c4", "r1c5", "r1c6") is None
assert violation("r4c3", "r3c4", "r2c5") is None
assert violation("r8c3", "r8c4", "r9c4") is None


# Rejected, one rule each, with the reason naming it.
def rejects(reason, *names):
    got = violation(*names)
    assert got is not None and reason in got, (names, got)


rejects("king step", "r1c4", "r1c6", "r1c7")
rejects("revisits", "r1c4", "r1c5", "r2c4", "r1c5", "r1c6")
rejects("no body", "r1c4", "r1c5")
# A body cell already in L1's body.
rejects("r4c4 is already on a line", "r3c3", "r4c4", "r3c5")
# A body cell that is L1's circle.
rejects("r4c3 is already on a line", "r3c3", "r4c3", "r5c3")
# A circle on L1's body.
rejects("circle r4c4", "r4c4", "r3c4", "r2c4")
# Crossing L2's r7c3 -> r6c2 step diagonally.
rejects("crosses line r8c3 | r7c3 r6c2 | r6c1", "r6c3", "r7c2", "r8c3")
# Crossing itself: r1c5 -> r2c6 and r2c5 -> r1c6 are the two diagonals of
# one 2x2.
rejects("crosses itself", "r1c5", "r2c6", "r2c5", "r1c6")

# The enumeration, on the board's own two witnesses.
check = rules.RuleModel(BOARD).check(time_limit=60)
assert check.status == "not_unique", check.status
target, second = check.first, check.second


def legal_separating(found):
    line = rules.Line(found[0], tuple(found[1:-1]), found[-1])
    return (
        candidates.shape_violation(found, BOARD) is None
        and rules.line_holds(target, line)
        and not rules.line_holds(second, line)
    )


found = list(candidates.separating_paths(target, second, BOARD, max_cells=5))
assert found, "no separating line on the board"
assert all(legal_separating(p) for p in found)
# One entry per line: a path and its reverse are the same line.
assert len({frozenset((p, p[::-1])) for p in found}) == len(found)
# Short first.
assert [len(p) for p in found] == sorted(len(p) for p in found)

# Up to four cells (so bodies of one and two cells), the pruned walk finds
# exactly the lines a naive walk over every king path does.
cells = [(r, c) for r in range(9) for c in range(9)]


def king_paths(prefix, length):
    if len(prefix) == length:
        yield prefix
        return
    last = prefix[-1]
    for q in cells:
        if q not in prefix and abs(q[0] - last[0]) <= 1 and abs(q[1] - last[1]) <= 1:
            yield from king_paths((*prefix, q), length)


naive = {
    frozenset((p, p[::-1]))
    for length in (3, 4)
    for a in cells
    for p in king_paths((a,), length)
    if legal_separating(p)
}
pruned = {
    frozenset((p, p[::-1]))
    for p in candidates.separating_paths(target, second, BOARD, max_cells=4)
}
assert any(len(next(iter(line))) == 4 for line in naive), "no four-cell line"
assert pruned == naive, (len(pruned), len(naive))

print("ok")

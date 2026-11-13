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
from halver_query import uniqueness
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


def rejects(reason, *names):
    got = violation(*names)
    assert got is not None and reason in got, (names, got)


rejects("king step", "r1c4", "r1c6", "r1c7")
rejects("revisits", "r1c4", "r1c5", "r2c4", "r1c5", "r1c6")
rejects("no body", "r1c4", "r1c5")
rejects("r4c4 is already on a line", "r3c3", "r4c4", "r3c5")
rejects("r4c3 is already on a line", "r3c3", "r4c3", "r5c3")
rejects("circle r4c4", "r4c4", "r3c4", "r2c4")
rejects("crosses line r8c3 | r7c3 r6c2 | r6c1", "r6c3", "r7c2", "r8c3")
rejects("crosses itself", "r1c5", "r2c6", "r2c5", "r1c6")

check = uniqueness(rules.RuleModel(BOARD), time_limit=60)
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
assert len({frozenset((p, p[::-1])) for p in found}) == len(found)
assert [len(p) for p in found] == sorted(len(p) for p in found)

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

# A 6x6 board (no 9x9 constant in the walk): stub solutions with doubled
# values 1..12 give exactly the lines a naive walk finds.
import random


class Stub:
    def __init__(self, values):
        self.digits = values
        self.values = values

    def doubled(self, cell):
        return self.values[cell[0]][cell[1]]


rng = random.Random(6)
cells6 = [(r, c) for r in range(6) for c in range(6)]
grid_a = [[rng.randint(1, 12) for _ in range(6)] for _ in range(6)]
grid_b = [[rng.randint(1, 12) for _ in range(6)] for _ in range(6)]
target6, second6 = Stub(grid_a), Stub(grid_b)


def legal6(p):
    line = rules.Line(p[0], tuple(p[1:-1]), p[-1])
    return (
        candidates.shape_violation(p, [], n=6) is None
        and rules.line_holds(target6, line)
        and not rules.line_holds(second6, line)
    )


def king_paths6(prefix, length):
    if len(prefix) == length:
        yield prefix
        return
    last = prefix[-1]
    for q in cells6:
        if q not in prefix and abs(q[0] - last[0]) <= 1 and abs(q[1] - last[1]) <= 1:
            yield from king_paths6((*prefix, q), length)


naive6 = {
    frozenset((p, p[::-1]))
    for length in (3, 4)
    for a in cells6
    for p in king_paths6((a,), length)
    if legal6(p)
}
pruned6 = {
    frozenset((p, p[::-1]))
    for p in candidates.separating_paths(target6, second6, [], max_cells=4)
}
assert naive6, "no 6x6 line"
assert pruned6 == naive6, (len(pruned6), len(naive6))

print("ok")

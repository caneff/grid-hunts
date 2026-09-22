"""The QQRR oracle against hand-worked cases.

Expected values below were computed by hand from the rule in
`OPENER_NOTES.md`, not by running the oracle: a 4x4 grid built to tie at both
levels (four windows read 1234, two read 2143, two read 3412), and the
unpadded concatenation on mixed one- and two-digit ranks.

    uv run finders/qqrr/test_oracle.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oracle

GRID = [
    [1, 2, 1, 2],
    [3, 4, 3, 4],
    [1, 2, 1, 2],
    [3, 4, 3, 4],
]

# Window values by top-left cell: 1234 2143 1234 / 3412 4321 3412 / 1234 2143 1234.
# SQL RANK: 1234 x4 -> 1, 2143 x2 -> 5, 3412 x2 -> 7, 4321 -> 9.
WINDOW_RANKS = [
    [1, 5, 1],
    [7, 9, 7],
    [1, 5, 1],
]

# Each cell reads its windows' ranks in reading order of their top-left cells.
CELL_NUMBERS = [
    [1, 15, 51, 1],
    [17, 1579, 5197, 17],
    [71, 7915, 9751, 71],
    [1, 15, 51, 1],
]

# 1 x4 -> 1, 15 x2 -> 5, 17 x2 -> 7, 51 x2 -> 9, 71 x2 -> 11, then 13..16.
CELL_RANKS = [
    [1, 5, 9, 1],
    [7, 13, 14, 7],
    [11, 15, 16, 11],
    [1, 5, 9, 1],
]

assert oracle.window_values(GRID) == [
    [1234, 2143, 1234],
    [3412, 4321, 3412],
    [1234, 2143, 1234],
]
assert oracle.window_ranks(GRID) == WINDOW_RANKS
assert oracle.cell_numbers(WINDOW_RANKS) == CELL_NUMBERS
assert oracle.cell_ranks(CELL_NUMBERS) == CELL_RANKS

# Unpadded concatenation: a two-digit rank widens the number, and two
# different rank lists can read as one number (1,23 and 12,3 are both 123).
assert oracle.concat([1, 23, 4, 56]) == 123456
assert oracle.concat([12, 3]) == 123
assert oracle.concat([1, 23]) == 123
assert oracle.concat([64]) == 64

# Window membership at 9x9: a corner reads one window, an edge two, an
# interior cell four, always in reading order of the top-left cells.
assert oracle.windows_of(9, 0, 0) == [(0, 0)]
assert oracle.windows_of(9, 8, 8) == [(7, 7)]
assert oracle.windows_of(9, 0, 4) == [(0, 3), (0, 4)]
assert oracle.windows_of(9, 4, 0) == [(3, 0), (4, 0)]
assert oracle.windows_of(9, 4, 4) == [(3, 3), (3, 4), (4, 3), (4, 4)]

# SQL RANK on its own: ties share the lower rank and the next rank is skipped.
assert oracle.sql_rank([30, 10, 20, 10]) == [4, 1, 3, 1]

print("ok test_oracle")

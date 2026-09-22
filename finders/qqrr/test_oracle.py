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
from grids import TIE_WITNESS, parse

# The first tie-sample preset in docs/research/2026-09-22-qqrr-explorer.html.
TIE_SAMPLE_TR7 = parse(
    "365741298/947286513/128395467/216938754/483517629/579462831/651873942/734629185/892154376"
)

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

# The 7-digit tie (#601), read off the witness by hand: r4c6 concatenates
# 2|25|12|46 and r5c4 concatenates 22|51|24|6, both 2251246, one box.
assert oracle.seven_digit_ties(oracle.window_ranks(TIE_WITNESS)) == [
    ((3, 5), (4, 3), 2251246, [2, 25, 12, 46], [22, 51, 24, 6])
]
# The tie-sample grids' only tie is 18 = 1|8 in column 1, an edge cell: no hit.
assert oracle.seven_digit_ties(oracle.window_ranks(TIE_SAMPLE_TR7)) == []


# Near misses, planted on a rank table whose every rank is two digits wide,
# so no interior number ties until a plant makes one. r5c5 reads the windows
# with top-left cells r4c4, r4c5, r5c4, r5c5; r5c7 and r7c7 read their own four.
def planted(plants):
    table = [[10 + (8 * r + c) % 55 for c in range(8)] for r in range(8)]
    for (r, c), ranks in plants.items():
        for (wr, wc), rank in zip(oracle.windows_of(9, r, c), ranks, strict=True):
            table[wr][wc] = rank
    return oracle.seven_digit_ties(table)


assert planted({}) == []
# 1|23|45|61 and 12|3|45|61 in one row: the tie.
assert planted({(4, 4): [1, 23, 45, 61], (4, 6): [12, 3, 45, 61]}) == [
    ((4, 4), (4, 6), 1234561, [1, 23, 45, 61], [12, 3, 45, 61])
]
# The same number in cells that share no row, column or box.
assert planted({(4, 4): [1, 23, 45, 61], (6, 6): [12, 3, 45, 61]}) == []
# The same rank list twice: equal numbers, no coincidence.
assert planted({(4, 4): [1, 23, 45, 61], (4, 6): [1, 23, 45, 61]}) == []
# A coincidence six digits long.
assert planted({(4, 4): [1, 2, 34, 56], (4, 6): [12, 3, 4, 56]}) == []

print("ok test_oracle")

"""The QQRR rule on a full grid, in plain Python, with no solver in sight.

Every grid the CP-SAT model returns is re-ranked here and the two must agree;
this file is the independent reading of the rule, so it never imports the
model. The rule (`OPENER_NOTES.md`):

- window value: a 2x2 window's digits read TL, TR, BL, BR, concatenated;
- quad rank: SQL RANK of that value among all windows;
- cell number: the ranks of the windows containing a cell, concatenated
  unpadded, in reading order of the windows' top-left cells;
- quad quad rank rank: SQL RANK of the cell number among all cells.

Grids are lists of rows; windows are keyed by their top-left cell (row, col).
"""


def sql_rank(values):
    """SQL RANK, 1 = smallest: ties share the lower rank, ranks after skip."""
    return [1 + sum(1 for u in values if u < v) for v in values]


def concat(ranks):
    """Concatenate ranks unpadded: [1, 23] and [12, 3] both read 123."""
    return int("".join(str(r) for r in ranks))


def windows_of(n, r, c):
    """Top-left cells of the windows containing cell (r, c), reading order."""
    return [
        (wr, wc)
        for wr in (r - 1, r)
        for wc in (c - 1, c)
        if 0 <= wr <= n - 2 and 0 <= wc <= n - 2
    ]


def window_values(grid):
    n = len(grid)
    return [
        [
            1000 * grid[r][c]
            + 100 * grid[r][c + 1]
            + 10 * grid[r + 1][c]
            + grid[r + 1][c + 1]
            for c in range(n - 1)
        ]
        for r in range(n - 1)
    ]


def _rank_table(table):
    """SQL RANK over every entry of a 2-D table, returned in the same shape."""
    flat = [v for row in table for v in row]
    ranks = sql_rank(flat)
    w = len(table[0])
    return [ranks[i : i + w] for i in range(0, len(ranks), w)]


def window_ranks(grid):
    return _rank_table(window_values(grid))


def cell_numbers(ranks):
    n = len(ranks) + 1
    return [
        [concat([ranks[wr][wc] for wr, wc in windows_of(n, r, c)]) for c in range(n)]
        for r in range(n)
    ]


def cell_ranks(numbers):
    return _rank_table(numbers)


def rank_grid(grid):
    """Everything the rule derives from a full grid, in one call."""
    ranks = window_ranks(grid)
    numbers = cell_numbers(ranks)
    return ranks, numbers, cell_ranks(numbers)

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


def seven_digit_ties(ranks):
    """Pairs of interior cells that see each other, whose cell numbers are
    equal and 7 digits long and whose window-rank lists differ (#601).

    `ranks` is a window-rank table (`window_ranks`). Each entry is (a, b,
    number, ranks of a, ranks of b), cells in reading order; the empty list
    when the table gives none.
    """
    n = len(ranks) + 1
    numbers = cell_numbers(ranks)
    interior = [(r, c) for r in range(1, n - 1) for c in range(1, n - 1)]
    box = int(n**0.5)
    out = []
    for i, a in enumerate(interior):
        for b in interior[i + 1 :]:
            same_house = (
                a[0] == b[0]
                or a[1] == b[1]
                or (a[0] // box, a[1] // box) == (b[0] // box, b[1] // box)
            )
            number = numbers[a[0]][a[1]]
            lists = [
                [ranks[wr][wc] for wr, wc in windows_of(n, *cell)] for cell in (a, b)
            ]
            if (
                same_house
                and number == numbers[b[0]][b[1]]
                and len(str(number)) == 7
                and lists[0] != lists[1]
            ):
                out.append((a, b, number, *lists))
    return out

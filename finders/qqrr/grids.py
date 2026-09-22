"""Seeded full sudoku grids for the tests: the base pattern under band, stack
and digit shuffles. Every grid is a valid 9x9 sudoku, none comes from a solver,
and the same seed gives the same grid every run."""


def random_sudoku(rng):
    base = [[(3 * (r % 3) + r // 3 + c) % 9 + 1 for c in range(9)] for r in range(9)]
    rows = [
        r
        for band in rng.sample(range(3), 3)
        for r in rng.sample([3 * band + i for i in range(3)], 3)
    ]
    cols = [
        c
        for stack in rng.sample(range(3), 3)
        for c in rng.sample([3 * stack + i for i in range(3)], 3)
    ]
    digits = rng.sample(range(1, 10), 9)
    return [[digits[base[r][c] - 1] for c in cols] for r in rows]


def parse(text):
    """A grid from its rows of digits joined by slashes, as the explorer stores it."""
    return [[int(d) for d in row] for row in text.split("/")]


# A full sudoku grid holding one 7-digit tie between interior cells that see
# each other (#601): r4c6 reads window ranks 2|25|12|46 and r5c4 reads
# 22|51|24|6, both 2251246, in the middle box. Found by the model with the tie
# constraint and no clues, confirmed by `oracle.seven_digit_ties`.
TIE_WITNESS = parse(
    "645378921/871259634/329614587/953827146/264195378/718463295/537941862/482536719/196782453"
)

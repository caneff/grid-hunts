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

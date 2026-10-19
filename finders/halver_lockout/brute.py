"""The independent check of a halver + lockout-line board: the shared halver
layer's backtracking search in C (`finders/halver/halver_brute_c.py`, #59)
with the lockout line's narrowing step, probing and branching on the
diamonds first. It shares no code with the CP-SAT model in
`rules.py`, so a modelling bug in one shows up as a disagreement with the
other.

`solutions(lines, n, box, limit, deadline, gap, search)` returns up to `limit`
solutions, each a (digits row by row, frozenset of halver cells) pair, in
search order. Given a `deadline` (a `time.monotonic()` reading), it raises
`OutOfTime` at the first search node past it, so a caller gets no count
rather than a short one. A line is any (diamond a, body cells, diamond b)
triple of (row, column) cells from 0. `gap` is the least difference between
the diamonds' values, 4 unless given. `search` is the C search unless given;
`halver_brute.solutions`, the Python search, returns the same solutions.

A lockout line keeps a diamond's doubled value only when the other diamond
has one at least 2 * gap away that leaves every body cell a doubled value
outside the closed range between the two, and keeps only body doubled values
outside at least one such range. A pair of diamond values also needs room:
for every house, as many distinct digits with a value outside the range as
the body has cells in that house, at most one of them halved.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "halver"))

# isort: split
import halver_brute_c
from halver_brute import OutOfTime

__all__ = ["OutOfTime", "lockout_narrowing", "solutions"]

GAP = 4


def solutions(
    lines, n, box, limit, deadline=None, gap=GAP, search=halver_brute_c.solutions
):
    def narrowing(body, houses, n):
        return lockout_narrowing(body, houses, n, gap)

    return search(narrowing, lines, n, box, limit, deadline, probe_ends=True)


def _bits(mask):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def lockout_narrowing(body, houses, n, gap=GAP):
    """The lockout line's narrowing step for one line with these body
    cells."""
    crowd = max(sum(1 for p in body if p in house) for house in houses)
    every = (1 << (2 * n + 1)) - 2  # doubled values 1..2n
    # outside[lo, hi]: the doubled values strictly below lo or above hi, for
    # each pair of diamonds that leaves room: `crowd` distinct digits with a
    # value there, at most one of them halved.
    outside = {}
    for lo in range(1, 2 * n + 1):
        for hi in range(lo + 2 * gap, 2 * n + 1):
            plain = {d for d in range(1, n + 1) if not lo <= 2 * d <= hi}
            halved = {d for d in range(1, n + 1) if not lo <= d <= hi}
            if len(plain) >= crowd or (
                halved and len(plain) >= crowd - 1 and len(plain | halved) >= crowd
            ):
                outside[lo, hi] = every & ~(((1 << (hi + 1)) - 1) & ~((1 << lo) - 1))

    def narrow(end_a, end_b, bodies):
        keep_a = keep_b = kept = 0
        for x in _bits(end_a):
            for y in _bits(end_b):
                span = outside.get((x, y) if x < y else (y, x))
                if span is not None and all(v & span for v in bodies):
                    keep_a |= 1 << x
                    keep_b |= 1 << y
                    kept |= span
        if not keep_a:
            return None
        return keep_a, keep_b, kept

    return narrow

"""The independent check of a halver + between-line board: the shared halver
layer's backtracking search (`finders/halver/halver_brute.py`) with the
between line's narrowing step. It shares no code with the CP-SAT model in
`rules.py`, so a modelling bug in one shows up as a disagreement with the
other.

`solutions(lines, n, box, limit, deadline)` returns up to `limit` solutions,
each a (digits row by row, frozenset of halver cells) pair, in search order.
Given a `deadline` (a `time.monotonic()` reading), it raises `OutOfTime` at
the first search node past it, so a caller gets no count rather than a short
one. A line is any (circle a, body cells, circle b) triple of (row, column)
cells from 0.

A between line keeps a circle's doubled value only when the other circle has
one that leaves every body cell a doubled value strictly between the two, and
keeps only body doubled values strictly between the lowest such low end and
the highest such high end. A pair of circle values also needs room: for every
house, as many distinct digits in the open interval as the body has cells in
that house, at most one of them halved.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "halver"))

# isort: split
import halver_brute
from halver_brute import OutOfTime

__all__ = ["OutOfTime", "between_narrowing", "solutions"]


def solutions(lines, n, box, limit, deadline=None):
    return halver_brute.solutions(between_narrowing, lines, n, box, limit, deadline)


def _bits(mask):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def between_narrowing(body, houses, n):
    """The between line's narrowing step for one line with these body cells."""
    crowd = max(sum(1 for p in body if p in house) for house in houses)
    # room[lo][hi]: whether the open interval (lo, hi) of doubled values
    # holds `crowd` distinct digits, at most one of them halved.
    room = [[False] * (2 * n + 2) for _ in range(2 * n + 2)]
    for lo in range(1, 2 * n + 1):
        for hi in range(lo + 1, 2 * n + 1):
            plain = {d for d in range(1, n + 1) if lo < 2 * d < hi}
            halved = {d for d in range(1, n + 1) if lo < d < hi}
            room[lo][hi] = len(plain) >= crowd or (
                halved and len(plain) >= crowd - 1 and len(plain | halved) >= crowd
            )
    spans = {
        (lo, hi): ((1 << hi) - 1) & ~((1 << (lo + 1)) - 1)
        for lo in range(1, 2 * n + 1)
        for hi in range(lo + 1, 2 * n + 1)
    }

    def narrow(end_a, end_b, bodies):
        keep_a = keep_b = between = 0
        for x in _bits(end_a):
            for y in _bits(end_b):
                if x == y:
                    continue
                lo, hi = (x, y) if x < y else (y, x)
                span = spans[lo, hi]
                if room[lo][hi] and all(v & span for v in bodies):
                    keep_a |= 1 << x
                    keep_b |= 1 << y
                    between |= span
        if not keep_a:
            return None
        return keep_a, keep_b, between

    return narrow

"""The second uniqueness model of a Doppelganger + Full Rank board (#70,
spec #66, Chris's ruling Q12 option (a)), the re-proof `hunt.py`'s
`verify` runs on a hit. It is written apart from `model.py` and shares no
code with it, nor with `rules.py`, beyond `sudoku_kit`, so a bug in the
hunt's model cannot pass its own hit. The encoding differs throughout:

- A cell is n + 1 booleans `y[r, c, d]`, one per digit 0..n, exactly one
  true, and an order ladder `ge[r, c, k]` (the digit is at least k) tied
  to them by clauses. No integer digit, no AllDifferent.
- A unit holds each digit at most once and 0 exactly once. Its missing
  digit is a boolean per digit, `miss[u, d]`, true exactly when no cell of
  the unit holds d. Two units of a kind never miss the same digit, and at
  a 0 no two of its row, column and box miss the same digit, each a
  cardinality bound on booleans.
- A number is never summed. Two numbers compare digit by digit from their
  reading ends as a chain of clauses: `less` and `same` at each position
  from the two cells' ladders, then "the rest of the other is below the
  rest of mine" from the next position back. A tie is below neither way.
  A clue's rank is 1 plus how many of the other 4n - 1 numbers are below.

`reprove(n, box, clues, time_limit)` is `sudoku_kit`'s five-status
uniqueness over the cell booleans, on one worker, with the grids read back
as digits. A timeout is never unique.
"""

from typing import NamedTuple

from ortools.sat.python import cp_model
from sudoku_kit.uniqueness import check_uniqueness


class Reproof(NamedTuple):
    """One of `sudoku_kit.uniqueness`'s five statuses, with its witness
    grids: `first` whenever a solution was found, `second` on not_unique."""

    status: str
    first: tuple | None = None
    second: tuple | None = None


def _units(n, box):
    """Each kind's units (rows, columns, boxes), each a list of cells."""
    bh, bw = box
    rows = [[(r, c) for c in range(n)] for r in range(n)]
    cols = [[(r, c) for r in range(n)] for c in range(n)]
    boxes = [
        [(top + i, left + j) for i in range(bh) for j in range(bw)]
        for top in range(0, n, bh)
        for left in range(0, n, bw)
    ]
    return rows, cols, boxes


def _reading(n, line, end):
    """The cells a clue's number reads, from its end: `r3` `right` reads
    row 3 from column n back to column 1."""
    i = int(line[1:]) - 1
    cells = [(i, j) for j in range(n)] if line[0] == "r" else [(j, i) for j in range(n)]
    return cells[::-1] if end in ("right", "bottom") else cells


def _all_readings(n):
    ends = {"r": ("left", "right"), "c": ("top", "bottom")}
    return {
        (f"{kind}{i}", end): _reading(n, f"{kind}{i}", end)
        for kind in "rc"
        for i in range(1, n + 1)
        for end in ends[kind]
    }


class _Board:
    def __init__(self, n, box, clues):
        self.n = n
        self.m = m = cp_model.CpModel()
        cells = [(r, c) for r in range(n) for c in range(n)]
        self.y = y = {
            (r, c, d): m.NewBoolVar(f"y{r}{c}_{d}")
            for r, c in cells
            for d in range(n + 1)
        }
        self.ge = ge = {}
        for r, c in cells:
            m.AddExactlyOne(y[r, c, d] for d in range(n + 1))
            for k in range(1, n + 1):
                ge[r, c, k] = m.NewBoolVar(f"ge{r}{c}_{k}")
                for d in range(n + 1):
                    m.AddImplication(
                        y[r, c, d], ge[r, c, k] if d >= k else ge[r, c, k].Not()
                    )

        kinds = _units(n, box)
        unit_of = {}
        for kind, units in enumerate(kinds):
            misses = []
            for u, unit in enumerate(units):
                m.AddExactlyOne(y[r, c, 0] for r, c in unit)
                miss = {}
                for d in range(1, n + 1):
                    m.AddAtMostOne(y[r, c, d] for r, c in unit)
                    miss[d] = m.NewBoolVar(f"miss{kind}{u}_{d}")
                    # At most one cell holds d, so the sum is 0 or 1.
                    m.Add(miss[d] + sum(y[r, c, d] for r, c in unit) == 1)
                misses.append(miss)
                for cell in unit:
                    unit_of[kind, cell] = miss
            for d in range(1, n + 1):
                m.AddAtMostOne(miss[d] for miss in misses)

        for cell in cells:
            zero = y[(*cell, 0)]
            three = [unit_of[kind, cell] for kind in range(3)]
            for d in range(1, n + 1):
                for i in range(3):
                    for j in range(i + 1, 3):
                        # Not (zero and both miss d).
                        m.AddBoolOr(zero.Not(), three[i][d].Not(), three[j][d].Not())

        readings = _all_readings(n)
        for k, clue in enumerate(clues):
            mine = (clue["line"], clue["end"])
            below = [
                self._below(readings[other], readings[mine], f"{k}_{o}")
                for o, other in enumerate(readings)
                if other != mine
            ]
            m.Add(sum(below) == clue["rank"] - 1)

    def _less_same(self, a, b, tag):
        """Booleans for "b's digit is below a's" and "they are equal"."""
        m, y, ge, n = self.m, self.y, self.ge, self.n
        less = m.NewBoolVar(f"less{tag}")
        same = m.NewBoolVar(f"same{tag}")
        m.AddBoolOr(y[(*a, 0)].Not(), less.Not())
        m.AddBoolOr(y[(*a, 0)].Not(), y[(*b, 0)].Not(), same)
        m.AddBoolOr(y[(*a, 0)].Not(), same.Not(), y[(*b, 0)])
        for d in range(1, n + 1):
            at_d = y[(*a, d)].Not()
            # a holds d: b is below exactly when b's digit is not at least d.
            m.AddBoolOr(at_d, less.Not(), ge[(*b, d)].Not())
            m.AddBoolOr(at_d, ge[(*b, d)], less)
            m.AddBoolOr(at_d, y[(*b, d)].Not(), same)
            m.AddBoolOr(at_d, same.Not(), y[(*b, d)])
        return less, same

    def _below(self, theirs, mine, tag):
        """A boolean true exactly when the number read along `theirs` is
        strictly below the one read along `mine`."""
        m = self.m
        rest = None
        for i in reversed(range(self.n)):
            less, same = self._less_same(mine[i], theirs[i], f"{tag}_{i}")
            if rest is None:
                rest = less
                continue
            here = m.NewBoolVar(f"below{tag}_{i}")
            # here <=> less or (same and rest)
            m.AddBoolOr(less.Not(), here)
            m.AddBoolOr(same.Not(), rest.Not(), here)
            m.AddBoolOr(here.Not(), less, same)
            m.AddBoolOr(here.Not(), less, rest)
            rest = here
        return rest

    def grid(self, values):
        n = self.n
        on = dict(zip(self.y, values, strict=True))
        return tuple(
            tuple(next(d for d in range(n + 1) if on[r, c, d]) for c in range(n))
            for r in range(n)
        )


def reprove(n, box, clues, time_limit):
    """The board's five-status uniqueness on the second model."""
    board = _Board(n, box, clues)
    result = check_uniqueness(
        board.m, list(board.y.values()), time_limit=time_limit, workers=1
    )
    return Reproof(
        result.status,
        board.grid(result.first) if result.first else None,
        board.grid(result.second) if result.second else None,
    )

"""The QQRR rule as a CP-SAT model, one encoding decision per function.

`build` returns a `Model` holding the digit variables `x`, every window's
value `v` and rank `rank`, every cell's number `num`, and a cell rank `q` for
each cell in `ranked_cells` only. The rule is the oracle's (`oracle.py`); the
encoding follows the speed list on map #591:

- a rank is `1 + count(strictly less)`, one reified strict-less literal per
  ordered pair, so ties come free of any equality literal;
- a cell number is the unpadded concatenation of its windows' ranks, written
  as one linear equality per combination of the later ranks' widths under
  enforcement literals, never as a multiplication;
- a cell rank counts only the cells whose number can fall below this one's
  upper bound, which drops every interior cell from a corner's count;
- the leading-digit bound (map #321, #324) is posted on every window as two
  linear inequalities; `leading_digits` reads the same band backwards to
  pre-prune a clued window's top-left cell.
"""

import itertools
from dataclasses import dataclass

from ortools.sat.python import cp_model


@dataclass
class Model:
    n: int
    m: cp_model.CpModel
    x: list  # x[r][c]: the digit in cell (r, c)
    v: list  # v[wr][wc]: the window value, top-left cell (wr, wc)
    rank: list  # rank[wr][wc]: the window's quad rank
    num: list  # num[r][c]: the cell number
    q: dict  # (r, c) -> the cell's quad quad rank rank, for ranked cells only
    wide: list  # wide[wr][wc]: true when the window's rank is two digits wide


def windows_of(n, r, c):
    return [
        (wr, wc)
        for wr in (r - 1, r)
        for wc in (c - 1, c)
        if 0 <= wr <= n - 2 and 0 <= wc <= n - 2
    ]


def add_rank(m, values, mine, name, lo=1, hi=None):
    """`1 + count(u < mine for u in values)` as a new int var.

    `values` excludes `mine`. The two literals per pair make the count exact:
    `b` forces `u < mine`, `not b` forces `u >= mine`.
    """
    lits = []
    for i, u in enumerate(values):
        b = m.NewBoolVar(f"{name}_lt{i}")
        m.Add(u <= mine - 1).OnlyEnforceIf(b)
        m.Add(u >= mine).OnlyEnforceIf(b.Not())
        lits.append(b)
    hi = len(values) + 1 if hi is None else hi
    r = m.NewIntVar(lo, hi, name)
    m.Add(r == 1 + sum(lits))
    return r


def add_width(m, rank, name):
    """A literal that is true exactly when `rank` is two digits wide."""
    b = m.NewBoolVar(name)
    m.Add(rank >= 10).OnlyEnforceIf(b)
    m.Add(rank <= 9).OnlyEnforceIf(b.Not())
    return b


def add_cell_number(m, ranks, top, name, widths=None):
    """The unpadded concatenation of `ranks` (int vars in 1..`top`, `top` < 100).

    Each rank after the first is one or two digits wide, which sets the
    power of ten under every earlier rank. One linear equality per width
    combination, enforced by the width literals it assumes. `widths` are the
    literals for `ranks[1:]` (one per window, shared by every cell reading
    that window); minted here when the caller has none.
    """
    k = len(ranks)
    num = m.NewIntVar(*number_bounds(k, top), name)
    if widths is None:
        widths = [add_width(m, r, f"{name}_w{i}") for i, r in enumerate(ranks[1:], 1)]
    for case in itertools.product((1, 2), repeat=k - 1):
        lits = [b if w == 2 else b.Not() for b, w in zip(widths, case, strict=True)]
        shift = 0
        terms = []
        for r, w in zip(reversed(ranks), reversed((1, *case)), strict=True):
            terms.append(r * 10**shift)
            shift += w
        m.Add(num == sum(terms)).OnlyEnforceIf(lits)
    return num


def number_bounds(k, top):
    """The smallest and largest number `k` ranks in 1..`top` can concatenate to."""
    assert top < 100, "widths beyond two digits are not encoded"
    return int("1" * k), int(str(top) * k)


def leading_digit_band(n, d):
    """Ranks a window whose top-left digit is `d` can take, on a full latin square.

    Over the (n-1) rows holding top-left cells, each smaller digit sits in
    n-2 or n-1 of them (only column n-1 can hide one), and at most n-2 other
    windows share the digit `d`. Map #321, #324: tight at 9x9.
    """
    return (n - 2) * (d - 1) + 1, (n - 2) * (d - 1) + (n - 1)


def leading_digits(n, lo, hi):
    """Top-left digits whose band meets the rank band [lo, hi]."""
    return [
        d
        for d in range(1, n + 1)
        if not (leading_digit_band(n, d)[1] < lo or leading_digit_band(n, d)[0] > hi)
    ]


def build(n=9, ranked_cells=()):
    """The model for an n x n sudoku grid under the QQRR rule.

    The leading-digit bound is posted on every window. It is sound only on a
    full latin square with digits 1..n, which is every grid the houses allow.
    """
    m = cp_model.CpModel()
    x = [[m.NewIntVar(1, n, f"x{r}{c}") for c in range(n)] for r in range(n)]
    for i in range(n):
        m.AddAllDifferent(x[i])
        m.AddAllDifferent([x[r][i] for r in range(n)])
    box = int(n**0.5)
    assert box * box == n, "boxes need a square size"
    for br in range(0, n, box):
        for bc in range(0, n, box):
            m.AddAllDifferent(
                [x[r][c] for r in range(br, br + box) for c in range(bc, bc + box)]
            )

    w = n - 1
    top = w * w
    v = [[m.NewIntVar(1111, 9999, f"v{r}{c}") for c in range(w)] for r in range(w)]
    for r in range(w):
        for c in range(w):
            m.Add(
                v[r][c]
                == 1000 * x[r][c]
                + 100 * x[r][c + 1]
                + 10 * x[r + 1][c]
                + x[r + 1][c + 1]
            )
    flat = [v[r][c] for r in range(w) for c in range(w)]
    rank = [[None] * w for _ in range(w)]
    for r in range(w):
        for c in range(w):
            mine = v[r][c]
            others = [u for u in flat if u is not mine]
            rank[r][c] = add_rank(m, others, mine, f"rank{r}{c}", hi=top)
            m.Add(rank[r][c] >= (n - 2) * (x[r][c] - 1) + 1)
            m.Add(rank[r][c] <= (n - 2) * (x[r][c] - 1) + (n - 1))

    wide = [
        [add_width(m, rank[r][c], f"wide{r}{c}") for c in range(w)] for r in range(w)
    ]
    num = [[None] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            wins = windows_of(n, r, c)
            num[r][c] = add_cell_number(
                m,
                [rank[wr][wc] for wr, wc in wins],
                top,
                f"num{r}{c}",
                widths=[wide[wr][wc] for wr, wc in wins[1:]],
            )
    bounds = [
        [number_bounds(len(windows_of(n, r, c)), top) for c in range(n)]
        for r in range(n)
    ]
    q = {}
    for r, c in ranked_cells:
        q[(r, c)] = add_cell_rank(m, num, bounds, (r, c), f"q{r}{c}")
    return Model(n, m, x, v, rank, num, q, wide)


def add_cell_rank(m, num, bounds, cell, name):
    """The cell's rank among all cells, counting only cells that can lie below it."""
    r, c = cell
    ceiling = bounds[r][c][1]
    others = [
        u
        for rr, row in enumerate(num)
        for cc, u in enumerate(row)
        if (rr, cc) != cell and bounds[rr][cc][0] < ceiling
    ]
    return add_rank(m, others, num[r][c], name, hi=len(num) * len(num[0]))


def add_tie_pair(m, num_a, num_b, wide_a, wide_b, name):
    """A literal that, when true, makes two interior cells a 7-digit tie (#601).

    `wide_a` and `wide_b` are the four width literals of each cell's windows,
    in reading order. The numbers are equal and 7 digits wide, so exactly one
    window per cell has a one-digit rank; the rank lists differ exactly when
    that window sits in a different slot, which is "no slot is narrow in both".
    """
    p = m.NewBoolVar(name)
    m.Add(num_a == num_b).OnlyEnforceIf(p)
    m.Add(sum(wide_a) == 3).OnlyEnforceIf(p)
    m.Add(sum(wide_b) == 3).OnlyEnforceIf(p)
    for a, b in zip(wide_a, wide_b, strict=True):
        m.AddBoolOr([a, b, p.Not()])
    return p


def sees(n, a, b):
    """Two distinct cells of an n x n grid share a row, a column or a box."""
    box = int(n**0.5)
    return a != b and (
        a[0] == b[0]
        or a[1] == b[1]
        or (a[0] // box, a[1] // box) == (b[0] // box, b[1] // box)
    )


def add_seeing_tie(q):
    """Require a 7-digit tie between two interior cells that see each other.

    One `add_tie_pair` literal per unordered pair of interior cells (rows and
    columns 1..n-2) in one row, column or box, and at least one of them true.
    Returns the pair literals keyed by the two cells in reading order.
    """
    n = q.n
    interior = [(r, c) for r in range(1, n - 1) for c in range(1, n - 1)]
    pairs = {}
    for i, a in enumerate(interior):
        for b in interior[i + 1 :]:
            if not sees(n, a, b):
                continue
            pairs[(a, b)] = add_tie_pair(
                q.m,
                q.num[a[0]][a[1]],
                q.num[b[0]][b[1]],
                *(
                    [q.wide[wr][wc] for wr, wc in windows_of(n, *cell)]
                    for cell in (a, b)
                ),
                f"tie{a[0]}{a[1]}_{b[0]}{b[1]}",
            )
    q.m.AddBoolOr(list(pairs.values()))
    return pairs

"""The Doppelganger + Full Rank board as a CP-SAT model (spec #66), for an
n x n board with boxes `box` tall and wide: 4x4 (2x2), 6x6 (2x3), 9x9 (3x3).

- A digit 0..n per cell, and a missing digit 1..n per row, column and box.
  A unit's n cells all differ and none is its missing digit, so they are
  exactly the other n of 0..n: one 0 and n - 1 of 1..n.
- The missing digits all differ across the rows, across the columns and
  across the boxes. At a 0, its row's, column's and box's missing digits
  all differ, posted under a literal that is true exactly at a 0.
- Each of the 4n numbers is a linear expression of its digits, read away
  from its end, a 0 as the digit 0. A rank clue posts its rank as 1 plus a
  count of reified strictly-less literals, one per other number (QQRR's
  encoding, `finders/qqrr/model.py`'s `add_rank`): `b` forces the other
  number below, `not b` at or above, so a tie counts as not below and needs
  no equality literal. Every number takes part in a clue's count; only
  clued numbers are counted.
- A number's leading digit is the cell at its end, so the 4n leading cells
  are the four edge lines c1, cn, r1 and rn (#75, ISS's `FullRank`:
  `docs/research/2026-10-22-doppelganger-rank-iss-buckets.md`). Each edge
  line holds every digit but its missing one, so `cnt[0] = 4` numbers lead
  with 0 and `cnt[d] = 4 - #{edge lines missing d}` with d. A clue leading
  with d has its rank in `below(d) + 1 .. below(d) + cnt[d]`, `below(d)`
  the sum of `cnt` over smaller digits. A clue's literal `b` is decided by
  the leading digits when they differ (smaller is below), and the whole
  numbers are compared only when they are equal.

`check` is `sudoku_kit`'s five-status uniqueness over the grid's digits
alone, since the missing digits follow from them. `mark_holds` solves once
with the mark negated, so a mark holds exactly when that solve is
infeasible. Neither reads a timeout as unique or as held. `sample` is one
solve steered by a random digit hint per cell: the hunt's target grid.
"""

from typing import NamedTuple

import rules
from ortools.sat.python import cp_model
from sudoku_kit import cpsat
from sudoku_kit.uniqueness import check_uniqueness


class RuleCheck(NamedTuple):
    """One of `sudoku_kit.uniqueness`'s five statuses, with its witness
    grids: `first` whenever a solution was found, `second` on not_unique."""

    status: str
    first: tuple | None = None
    second: tuple | None = None


class MarkCheck(NamedTuple):
    """`held`, `not_held` with a grid that breaks the mark, or `timeout`."""

    status: str
    counterexample: tuple | None = None


class RankModel:
    def __init__(self, n, box, clues):
        self.n = n
        self.model = m = cp_model.CpModel()
        rows, cols, boxes = rules.houses(n, box)
        self.x = x = {
            (r, c): m.NewIntVar(0, n, f"x{r}{c}") for r in range(n) for c in range(n)
        }
        self.miss = {}
        for units in (rows, cols, boxes):
            for name, cells in units.items():
                miss = self.miss[name] = m.NewIntVar(1, n, f"miss_{name}")
                m.AddAllDifferent(x[cell] for cell in cells)
                for cell in cells:
                    m.Add(x[cell] != miss)
            m.AddAllDifferent(self.miss[name] for name in units)

        box_of = {cell: name for name, cells in boxes.items() for cell in cells}
        for (r, c), digit in x.items():
            zero = m.NewBoolVar(f"zero{r}{c}")
            m.Add(digit == 0).OnlyEnforceIf(zero)
            m.Add(digit >= 1).OnlyEnforceIf(zero.Not())
            three = [self.miss[f"r{r + 1}"], self.miss[f"c{c + 1}"]]
            three.append(self.miss[box_of[r, c]])
            for i in range(3):
                for j in range(i + 1, 3):
                    m.Add(three[i] != three[j]).OnlyEnforceIf(zero)

        self.numbers = {
            place: sum(
                x[cell] * 10 ** (n - 1 - i)
                for i, cell in enumerate(rules.line_cells(n, place))
            )
            for place in rules.places(n)
        }
        self.lead = {
            place: x[rules.line_cells(n, place)[0]] for place in rules.places(n)
        }
        edges = ["c1", f"c{n}", "r1", f"r{n}"]
        self.cnt = [4]
        for d in range(1, n + 1):
            missed = []
            for line in edges:
                b = m.NewBoolVar(f"miss_{line}_is_{d}")
                m.Add(self.miss[line] == d).OnlyEnforceIf(b)
                m.Add(self.miss[line] != d).OnlyEnforceIf(b.Not())
                missed.append(b)
            self.cnt.append(4 - sum(missed))
        self.clues = []
        for clue in clues:
            self.add_clue(clue)

    def add_clue(self, clue):
        """Post one rank clue, `{"line", "end", "rank"}`."""
        m = self.model
        place = (clue["line"], clue["end"])
        mine, lead = self.numbers[place], self.lead[place]
        tag = len(self.clues)
        leads_with = [m.NewBoolVar(f"lead_{tag}_is_{d}") for d in range(self.n + 1)]
        m.AddExactlyOne(leads_with)
        for d, is_d in enumerate(leads_with):
            m.Add(lead == d).OnlyEnforceIf(is_d)
            below_d = sum(self.cnt[:d])
            m.Add(below_d + 1 <= clue["rank"]).OnlyEnforceIf(is_d)
            m.Add(clue["rank"] <= below_d + self.cnt[d]).OnlyEnforceIf(is_d)
        below = []
        for other, number in self.numbers.items():
            if other == place:
                continue
            name = f"{tag}_{other[0]}_{other[1]}"
            b = m.NewBoolVar(f"lt_{name}")
            same = m.NewBoolVar(f"same_lead_{name}")
            m.Add(self.lead[other] == lead).OnlyEnforceIf(same)
            m.Add(self.lead[other] != lead).OnlyEnforceIf(same.Not())
            m.Add(self.lead[other] <= lead).OnlyEnforceIf(b)
            m.Add(self.lead[other] >= lead).OnlyEnforceIf(b.Not())
            m.Add(number <= mine - 1).OnlyEnforceIf(b, same)
            m.Add(number >= mine).OnlyEnforceIf(b.Not(), same)
            below.append(b)
        m.Add(1 + sum(below) == clue["rank"])
        self.clues.append(clue)

    def _copy(self, hints=None):
        """A copy of the model and its grid variables, in `self.x`'s order,
        with no hint but `hints`, one value per variable in that order."""
        m = self.model.clone()
        m.ClearHints()
        x = [m.GetIntVarFromProtoIndex(v.Index()) for v in self.x.values()]
        for var, value in zip(x, hints or (), strict=hints is not None):
            m.AddHint(var, value)
        return m, x

    def _grid(self, values):
        n = self.n
        return tuple(tuple(values[r * n + c] for c in range(n)) for r in range(n))

    def check(self, time_limit=10.0, hint=None, workers=1):
        """The five-status uniqueness of the grid's digits, on `workers`
        CP-SAT workers. `hint`, a grid, is a solution hint for both solves, a
        warm start that changes no verdict. Leaves the model unchanged."""
        m, x = self.model, list(self.x.values())
        if hint is not None:
            m, x = self._copy([hint[r][c] for r, c in self.x])
        result = check_uniqueness(m, x, time_limit=time_limit, workers=workers)
        return RuleCheck(
            result.status,
            self._grid(result.first) if result.first else None,
            self._grid(result.second) if result.second else None,
        )

    def sample(self, rng, time_limit=10.0):
        """One grid of the clues, steered by a random digit hint per cell,
        on one worker: `RuleCheck("found", grid)`, `RuleCheck("infeasible")`
        when the clues have none, or `RuleCheck("timeout")`. Leaves the model
        unchanged."""
        m, x = self._copy([rng.randint(0, self.n) for _ in self.x])
        solver = cpsat.solver(time_limit)
        # Presolve's symmetry breaking pins the grid whatever the hints say:
        # 6 grids in 40 seeds on an empty 4x4, every one with r1c1 = 0.
        solver.parameters.symmetry_level = 0
        status = solver.Solve(m)
        if status in cpsat.SOLVED:
            return RuleCheck("found", self._grid([solver.Value(v) for v in x]))
        if status == cp_model.INFEASIBLE:
            return RuleCheck("infeasible")
        if status == cpsat.UNKNOWN:
            return RuleCheck("timeout")
        raise ValueError(f"sampling got solver status {solver.StatusName(status)}")

    def mark_holds(self, mark, time_limit=10.0):
        """Whether every solution keeps `mark`, a board file's
        `{"kind": "digit", "cell", "digit"}` or `{"kind": "missing", "unit",
        "digit"}`: one solve of a copy of the model with the mark negated."""
        m, grid = self._copy()
        x = dict(zip(self.x, grid, strict=True))
        if mark["kind"] == "digit":
            r, c = rules.parse_cell(mark["cell"])
            m.Add(x[r, c] != mark["digit"])
        else:
            miss = m.GetIntVarFromProtoIndex(self.miss[mark["unit"]].Index())
            m.Add(miss != mark["digit"])
        solver = cpsat.solver(time_limit)
        status = solver.Solve(m)
        if status == cp_model.INFEASIBLE:
            return MarkCheck("held")
        if status in cpsat.SOLVED:
            return MarkCheck(
                "not_held", self._grid([solver.Value(v) for v in x.values()])
            )
        if status == cpsat.UNKNOWN:
            return MarkCheck("timeout")
        raise ValueError(f"mark check got solver status {solver.StatusName(status)}")

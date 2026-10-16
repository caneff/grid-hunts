"""The two-stage uniqueness proof must never print UNIQUE without earning it.

Three seams (#402):

- `two_stage`, the verdict control flow, driven here by fake stages so every
  branch is reachable in milliseconds.
- `pin_circle_sizes`, the stage-1 circle constraint: it must keep a real
  solution's shading (the relaxation holds) and still bite.
- `digit_fills`, the stage-2 enumeration on one fixed shading.

    uv run finders/renbanana/tools/test_prove_two_stage.py
"""

import sys
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prove_two_stage as pts
import renbanana_cpsat as R
import renbanana_verify as rv

CAND = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "research"
    / "renbanana"
    / "candidates-fully-circled"
    / "cand_00.json"
)
GRID, SHADING, _ = rv.load(CAND)


def size_reading(grid, is_choc):
    """Every cell whose digit equals its group size: the 12-circle pick."""
    size = rv.group_sizes(is_choc)
    return [p for p in R.CELLS if grid[p] == size[p]]


CIRCLES = size_reading(GRID, SHADING)


def transposed(cells):
    return {(c, r): v for (r, c), v in cells.items()}


class FakeStages:
    """Stage 1 hands out `shadings` in order, then `end`; stage 2 answers each
    shading from `answers` (exhausted flag, grids). Records every forbid."""

    def __init__(self, shadings, answers, end=cp.INFEASIBLE):
        self.shadings = list(shadings)
        self.answers = list(answers)
        self.end = end
        self.forbidden = []
        self.limits = []

    def next_shading(self):
        if len(self.forbidden) < len(self.shadings):
            return cp.FEASIBLE, self.shadings[len(self.forbidden)]
        return self.end, None

    def fills(self, is_choc, limit):
        self.limits.append(limit)
        return self.answers[len(self.forbidden)]

    def forbid(self, is_choc):
        self.forbidden.append(is_choc)

    def run(self, circled):
        return pts.two_stage(self.next_shading, self.fills, self.forbid, circled)


def test_one_fill_with_both_stages_exhausted_is_unique():
    other = transposed(SHADING)
    stages = FakeStages([other, SHADING], [(True, []), (True, [GRID])])
    verdict, sols, survivors = stages.run(CIRCLES)
    assert verdict == "UNIQUE", verdict
    assert sols == [(GRID, SHADING)]
    assert survivors == 2
    assert stages.forbidden == [other, SHADING], "each shading is cut once handled"


def test_two_fills_across_shadings_is_not_unique_and_stops():
    # Transposing a legal grid and its shading keeps every rule, so with no
    # circles both are genuine solutions.
    t_grid, t_shading = transposed(GRID), transposed(SHADING)
    stages = FakeStages(
        [SHADING, t_shading, SHADING],
        [(True, [GRID]), (True, [t_grid]), (True, [])],
    )
    verdict, sols, survivors = stages.run(())
    assert verdict == "NOT UNIQUE", verdict
    assert len(sols) == 2
    assert survivors == 2, "the search stops at the second solution"
    assert stages.limits == [2, 1], "stage 2 is only asked for what is still needed"


def test_no_fill_anywhere_is_no_solution():
    stages = FakeStages([SHADING], [(True, [])])
    assert stages.run(CIRCLES)[0] == "NO SOLUTION"


def test_a_stage_one_timeout_is_never_unique():
    stages = FakeStages([SHADING], [(True, [GRID])], end=cp.UNKNOWN)
    assert stages.run(CIRCLES)[0] == "NOT PROVED"


def test_a_stage_two_timeout_is_never_unique():
    other = transposed(SHADING)
    stages = FakeStages([SHADING, other], [(True, [GRID]), (False, [])])
    assert stages.run(CIRCLES)[0] == "NOT PROVED"


def test_a_fill_that_fails_verification_is_never_unique():
    bad = dict(GRID)
    bad[0, 0], bad[0, 1] = bad[0, 1], bad[0, 0]  # breaks the columns
    stages = FakeStages([SHADING], [(True, [bad])])
    assert stages.run(CIRCLES)[0] == "NOT PROVED"


def pinned_to(model, is_choc):
    for p in R.CELLS:
        model.m.add(model.choc[p] == int(is_choc[p]))


def test_pinning_circle_sizes_keeps_the_real_shading():
    model = R.Shadings()
    pts.pin_circle_sizes(model, CIRCLES)
    pinned_to(model, SHADING)
    status, found = model.solve(30.0, 1)
    assert found == SHADING, R.STATUS[status]


def test_pinning_circle_sizes_rules_out_an_uncircleable_rectangle():
    # A 2x2 whose top-left sits at box offset (0,0) never holds a 4 (catalogue),
    # so a circle on any of its cells rules that maximal rectangle out.
    assert not R.circle_cells_at(2, 2, 0, 0)
    corner = [(0, 0), (0, 1), (1, 0), (1, 1)]
    border = [(0, 2), (1, 2), (2, 0), (2, 1)]

    def with_corner(circled):
        model = R.Shadings(lemmas=False)
        pts.pin_circle_sizes(model, circled)
        for p in corner:
            model.m.add(model.choc[p] == 1)
        for p in border:
            model.m.add(model.choc[p] == 0)
        return model.solve(30.0, 1)[0]

    assert with_corner([]) in (cp.OPTIMAL, cp.FEASIBLE), "the corner alone is legal"
    status = with_corner([(0, 0)])
    assert status == cp.INFEASIBLE, R.STATUS[status]


def test_digit_fills_finds_only_the_known_grid_and_exhausts():
    exhausted, grids = pts.digit_fills(SHADING, CIRCLES, 2, 60.0, 1)
    assert exhausted, "the search must finish, not merely return a grid"
    assert grids == [GRID]


def test_digit_fills_out_of_time_is_never_exhausted():
    exhausted, grids = pts.digit_fills(SHADING, CIRCLES, 2, 0.0, 1)
    assert (exhausted, grids) == (False, [])


def test_digit_fills_on_a_solver_timeout_is_never_exhausted():
    real = pts.cp.CpSolver

    class TimesOut(real):
        def solve(self, model):
            return cp.UNKNOWN

    pts.cp.CpSolver = TimesOut
    try:
        exhausted, grids = pts.digit_fills(SHADING, CIRCLES, 2, 60.0, 1)
    finally:
        pts.cp.CpSolver = real
    assert (exhausted, grids) == (False, [])


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("OK")

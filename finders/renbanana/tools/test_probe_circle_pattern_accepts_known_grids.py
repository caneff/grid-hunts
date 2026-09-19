"""The circle-pattern probe must accept every grid we already know is legal.

`probe_circle_pattern` reports UNIQUE when its second-solution search comes
back INFEASIBLE. Every solution it emits is re-checked by `renbanana_verify`,
so an under-constrained model fails loud; an over-constrained one does not --
it just rules the real second solution out and prints a false UNIQUE. This
test guards that direction only: each known (grid, shading), pinned, with
every cell that reads its own group size circled, must stay FEASIBLE. It says
nothing about a wrong UNIQUE from a model that is too loose; that still rests
on the re-verification.

    uv run finders/renbanana/tools/test_probe_circle_pattern_accepts_known_grids.py [--cover]

Run it from the repo root. `--cover` (in `just check`, about 7s) solves only
the few grids that between them circle every group shape the pool circles;
the full run (`just test-finders-slow`, about 3 minutes) solves all of them.
"""

import sys
from pathlib import Path

sys.path.insert(0, "finders/renbanana/tools")
sys.path.insert(0, "finders")
import probe_circle_pattern as pcp
import renbanana_verify as rv
from ortools.sat.python import cp_model as cp

POOL = Path("docs/research/renbanana")
CANDIDATES = sorted(POOL.glob("candidates*/cand_*.json"))
CIRCLE_PATTERN_GRIDS = 119  # the circle-pattern pool #401 names
# Hand-picked legal grids for the large chocolate shapes the pool never circles
# (#498). Made with `renbanana_cpsat`, not `probe_circle_pattern`, and each one
# re-checked by `renbanana_verify`. A size-5 group cannot be circled (no
# multi-cell chocolate group holds a 5), and 1x8 and 1x9 do not exist in a
# legal grid (RECTANGLE-CATALOGUE.md "Circle 5 is impossible"; FEASIBILITY.md
# 1x8 and 1x9 rows). So the pool holds an uncircled 1x5 run, a circled 1x6 and
# 1x7, and a circled 3x3.
WITNESSES = sorted(POOL.glob("candidates-circle-witnesses/*.json"))


def group_sizes(is_choc):
    return {
        p: len(g)
        for colour in (True, False)
        for g in rv.components(is_choc, colour)
        for p in g
    }


def status(grid, is_choc, circled):
    m, _, _ = pcp.build(
        circled,
        [p for p in pcp.CELLS if is_choc[p]],
        [p for p in pcp.CELLS if not is_choc[p]],
        list(grid.items()),
    )
    s = cp.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = 60
    return s.status_name(s.solve(m))


def circled_shapes(path):
    """The group shapes this grid circles: (h, w) for a chocolate rectangle,
    the size for a banana group -- the cases the size encoding tells apart."""
    grid, is_choc, _ = rv.load(path)
    shapes = set()
    for colour in (True, False):
        for g in rv.components(is_choc, colour):
            if not any(grid[p] == len(g) for p in g):
                continue
            if colour:
                shapes.add(
                    ("chocolate", len({r for r, _ in g}), len({c for _, c in g}))
                )
            else:
                shapes.add(("banana", len(g)))
    return shapes


def covering_grids():
    """A few grids that between them circle every shape the pool circles."""
    shapes = {p: circled_shapes(p) for p in CANDIDATES}
    need = set().union(*shapes.values())
    picked = []
    while need:
        best = max(CANDIDATES, key=lambda p: len(shapes[p] & need))
        picked.append(best)
        need -= shapes[best]
    return picked


def chocolate_groups(path):
    """(short side, long side, circled) for every chocolate group of a grid, circled meaning some
    cell of it reads the group's size."""
    grid, is_choc, _ = rv.load(path)
    return {
        (*sorted(rv.shape(g)), any(grid[p] == len(g) for p in g))
        for g in rv.components(is_choc, True)
    }


def assert_accepted(paths):
    rejected = []
    for path in paths:
        grid, is_choc, _ = rv.load(path)
        assert not rv.check(grid, is_choc), f"{path} is not a legal grid"
        sizes = group_sizes(is_choc)
        reads = [p for p in pcp.CELLS if grid[p] == sizes[p]]
        name = status(grid, is_choc, reads)
        print(f"{path.parent.name}/{path.name}: circles={len(reads)} {name}")
        if name not in ("OPTIMAL", "FEASIBLE"):
            rejected.append(path)
    assert not rejected, f"valid grids rejected: {rejected}"


def test_every_known_grid_is_accepted():
    pattern = [p for p in CANDIDATES if p.parent.name == "candidates-circle-pattern"]
    assert len(pattern) == CIRCLE_PATTERN_GRIDS, f"{len(pattern)} circle-pattern grids"
    assert len(CANDIDATES) > len(pattern), "the older verified witnesses are missing"
    assert_accepted(CANDIDATES + WITNESSES)


def test_a_grid_for_every_circled_shape_is_accepted():
    assert_accepted(covering_grids() + WITNESSES)


def test_witnesses_cover_the_large_chocolate_shapes():
    """Straight runs of 5, 6 and 7, and a 3x3, are in the pool; the 6, 7 and the
    3x3 carry a circle. Without them an edit that caps `run` at 4 or botches
    the 3x3 area would pass the known-grid guard."""
    have = set().union(*(chocolate_groups(p) for p in WITNESSES))
    for need in [(1, 5, False), (1, 6, True), (1, 7, True), (3, 3, True)]:
        assert need in have, f"no witness has chocolate {need} (short, long, circled)"


def test_a_circle_on_a_cell_that_misreads_its_size_is_refused():
    """The other half of the circle constraint: if it accepted anything, the
    test above would pass on a model that ignores circles altogether."""
    grid, is_choc, _ = rv.load(CANDIDATES[0])
    sizes = group_sizes(is_choc)
    for colour in (True, False):
        wrong = next(
            p for p in pcp.CELLS if is_choc[p] == colour and grid[p] != sizes[p]
        )
        assert status(grid, is_choc, [wrong]) == "INFEASIBLE", wrong


if __name__ == "__main__":
    test_a_circle_on_a_cell_that_misreads_its_size_is_refused()
    test_witnesses_cover_the_large_chocolate_shapes()
    if "--cover" in sys.argv[1:]:
        test_a_grid_for_every_circled_shape_is_accepted()
    else:
        test_every_known_grid_is_accepted()
    print("PASS")

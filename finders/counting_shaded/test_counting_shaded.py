"""Soundness suite for the counting shaded finder.

    uv run pytest finders/counting_shaded

Covers the places this hunt actually went wrong: a filter that disagreed
between C and Python, a hand-rolled solution counter with no independent
check, and a CP-SAT encoding that reported infeasible for the wrong reason.
Every claim here is falsifiable against a second implementation — the C
against Python, the bitmask counter against CP-SAT, one shape model against
the other — and every "nothing found" claim is paired with a positive control,
so a filter that rejects everything fails the suite instead of passing it.
"""

import json
import random
from pathlib import Path

import connected
import fastclimb
import pytest
import recheck_pins
import shapes
import verify_all
from ortools.sat.python import cp_model

HERE = Path(__file__).resolve().parent
# Notes, hit logs and images stayed under docs/research/counting_shaded when the code moved.
EXAMPLES = (
    HERE.parents[1]
    / "docs"
    / "research"
    / "counting_shaded"
    / "examples-verified.jsonl"
)


@pytest.fixture(autouse=True)
def default_settings():
    """Every test starts from: no pins, 8 not required."""
    fastclimb.require_eight(False)
    fastclimb.pins()
    yield
    fastclimb.require_eight(False)
    fastclimb.pins()


# Connected, admissible, shows an 8, and its givens have exactly two solutions.
# (No connected shape is unique under sudoku rules: the connected note's exhaustive result.)
ADMISSIBLE_TWO_SOLUTIONS = frozenset({13, 14, 15, 21, 22, 23, 24, 31, 32, 33, 41})


def random_blob(rng, size, start=()):
    """A connected blob of `size` cells grown from the `start` cells (one random cell if none)."""
    shape = set(start) or {rng.randrange(81)}
    while len(shape) < size:
        shape.add(
            rng.choice([j for i in shape for j in shapes.ORTH[i] if j not in shape])
        )
    return shape


def cpsat_count(given, cap=2):
    """Solutions of a sudoku with these givens, counted by CP-SAT, up to cap."""
    m = cp_model.CpModel()
    x = {(r, c): m.new_int_var(1, 9, "") for r in range(9) for c in range(9)}
    for i in range(9):
        m.add_all_different([x[i, c] for c in range(9)])
        m.add_all_different([x[r, i] for r in range(9)])
    for br in (0, 3, 6):
        for bc in (0, 3, 6):
            m.add_all_different([x[br + a, bc + b] for a in range(3) for b in range(3)])
    for i, n in given.items():
        m.add(x[divmod(i, 9)] == n)
    found = []

    class Collect(cp_model.CpSolverSolutionCallback):
        def on_solution_callback(self):
            found.append(1)
            if len(found) >= cap:
                self.stop_search()

    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.enumerate_all_solutions = True
    s.solve(m, Collect())
    return len(found)


# --- tables -----------------------------------------------------------------


def test_neighbour_box_and_orth_tables():
    for i in range(81):
        r, c = divmod(i, 9)
        assert shapes.CELLS[i] == (r, c)
        assert shapes.BOX[i] == (r // 3) * 3 + c // 3
        assert sorted(shapes.NEIGH[i]) == sorted(
            (r + a) * 9 + c + b
            for a in (-1, 0, 1)
            for b in (-1, 0, 1)
            if (a or b) and 0 <= r + a <= 8 and 0 <= c + b <= 8
        )
        assert sorted(shapes.ORTH[i]) == sorted(
            (r + a) * 9 + c + b
            for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 <= r + a <= 8 and 0 <= c + b <= 8
        )
    assert [len(shapes.NEIGH[i]) for i in (0, 4, 40)] == [3, 5, 8]


def test_houses_cover_every_cell_three_times():
    seen = {}
    for house in recheck_pins.HOUSES:
        assert len(house) == 9
        for i in house:
            seen[i] = seen.get(i, 0) + 1
    assert len(seen) == 81 and set(seen.values()) == {3}


# --- filters ----------------------------------------------------------------


def test_connectivity_is_required():
    blob = {0, 1, 9, 10}
    assert shapes.connected(blob)
    assert not shapes.connected(blob | {40})
    assert shapes.givens(blob | {40}) is None
    assert fastclimb.count(blob | {40}, 2) == -1


def test_diagonal_touch_is_not_connected():
    assert not shapes.connected({0, 10})  # r1c1 and r2c2 touch only at a corner


def test_repeated_given_in_a_house_is_rejected():
    # An L of three: the two ends both see one shaded cell, and they share a box.
    shape = {0, 1, 9}
    given = {i: sum(j in shape for j in shapes.NEIGH[i]) for i in shape}
    assert given[1] == given[9] and shapes.BOX[1] == shapes.BOX[9]
    assert shapes.givens(shape) is None


def test_pins_force_and_ban():
    # An admissible shape, so a rejection below is the pin's doing.
    blob = set(ADMISSIBLE_TWO_SOLUTIONS)
    assert shapes.givens(blob) is not None, "control: unpinned, the shape is admissible"
    assert fastclimb.count(blob, 2) >= 0
    outside = next(i for i in range(81) if i not in blob)
    fastclimb.pins(force=[outside])
    assert shapes.givens(blob) is None, "a shape missing a forced cell must be rejected"
    assert fastclimb.count(blob, 2) == -1
    inside = next(iter(blob))
    fastclimb.pins(force=[inside])
    assert shapes.givens(blob) is not None, "control: a forced cell the shape holds"
    assert fastclimb.count(blob, 2) >= 0
    fastclimb.pins(ban=[inside])
    assert shapes.givens(blob) is None, "a shape using a banned cell must be rejected"
    assert fastclimb.count(blob, 2) == -1


def test_require_eight_flag_changes_the_verdict():
    row = json.loads(EXAMPLES.read_text().splitlines()[0])
    shape = set(row["shape"])
    given = {i: sum(j in shape for j in shapes.NEIGH[i]) for i in shape}
    assert 8 in given.values(), "fixture should show an 8 (the old hunt demanded one)"
    # This example predates connectivity, so compare on the flag alone.
    fastclimb.require_eight(True)
    assert shapes.REQUIRE_EIGHT and shapes.eight_ok(given)
    given_without = {i: n for i, n in given.items() if n != 8}
    assert not shapes.eight_ok(given_without)
    fastclimb.require_eight(False)
    assert shapes.eight_ok(given_without)


@pytest.mark.parametrize(
    "eight,force,ban", [(False, (), ()), (True, (), ()), (False, (30, 31), (0,))]
)
def test_c_and_python_filters_agree(eight, force, ban):
    rng = random.Random(11)
    fastclimb.require_eight(eight)
    fastclimb.pins(force, ban)
    admissible = 0
    for _ in range(4000):
        # a forced case grows from its forced cells, else no random blob would hold them
        shape = random_blob(rng, rng.randrange(max(3, len(force)), 24), start=force)
        if rng.random() < 0.3:
            shape ^= {rng.randrange(81)}
        g = shapes.givens(shape)
        want = shapes.count_solutions(g, 50) if shapes.eight_ok(g) else -1
        assert fastclimb.count(shape, 50) == want, sorted(shape)
        admissible += want >= 0
    assert admissible > 0, "control: this filter setting must accept something"


# --- counter ----------------------------------------------------------------


def test_bitmask_counter_matches_cpsat():
    rng = random.Random(5)
    checked = unique = 0
    while checked < 25:
        shape = random_blob(rng, rng.randrange(8, 26))
        g = shapes.givens(shape)
        if g is None:
            continue
        checked += 1
        mine = shapes.count_solutions(g, 2)
        assert mine == cpsat_count(g, 2), sorted(shape)
        unique += mine == 1
    assert checked == 25
    # Random blobs are never unique, so the sample adds stored unique examples (their
    # givens, since they predate connectivity); the counter must agree on those too.
    for line in EXAMPLES.read_text().splitlines()[:5]:
        shape = set(json.loads(line)["shape"])
        g = {i: sum(j in shape for j in shapes.NEIGH[i]) for i in shape}
        mine = shapes.count_solutions(g, 2)
        assert mine == cpsat_count(g, 2), sorted(shape)
        unique += mine == 1
    assert unique > 0, "control: the sample must hold a unique shape to compare on"


def test_counter_reports_zero_for_contradictory_givens():
    # Two 3s in one row cannot both be digits of a solution.
    assert shapes.count_solutions({0: 3, 4: 3}, 2) == 0


def test_counter_counts_a_known_unique_example():
    row = json.loads(EXAMPLES.read_text().splitlines()[0])
    given = {int(k[1]) * 9 - 9 + int(k[3]) - 1: v for k, v in row["givens"].items()}
    assert shapes.count_solutions(given, 2) == 1
    assert cpsat_count(given, 2) == 1


# --- verifier ---------------------------------------------------------------


def test_verifier_accepts_every_stored_example():
    rows = [json.loads(line) for line in EXAMPLES.read_text().splitlines()]
    assert len(rows) >= 200
    for row in rows:
        sol, _given = verify_all.check([divmod(i, 9) for i in row["shape"]])
        assert sol is not None and sol == row["solution"], row["shape"]


def test_verifier_rejects_a_non_unique_shape():
    """An admissible shape with an 8 and two solutions: only the uniqueness
    re-solve can reject it (a 1-8 or no-8 filter would reject it first)."""
    shape = ADMISSIBLE_TWO_SOLUTIONS
    g = shapes.givens(shape)
    assert g is not None and 8 in g.values(), "control: passes the admissibility filters"
    assert all(1 <= n <= 8 for n in g.values())
    assert shapes.count_solutions(g, 2) == 2, "control: the shape is not unique"
    assert verify_all.check([divmod(i, 9) for i in shape])[0] is None


def test_verifier_rejects_an_inadmissible_shape():
    assert verify_all.check([(0, 0), (0, 1), (0, 2)])[0] is None


# --- shape models -----------------------------------------------------------


@pytest.mark.parametrize(
    "force,ban,feasible",
    [
        ((), (), True),
        ((72, 73, 79), (), True),
        ((72, 73), (57,), True),
        ((72, 73, 79), (57,), False),
    ],
)
def test_both_shape_models_agree_on_feasibility(force, ban, feasible):
    """connected.build (pairwise !=) against recheck_pins.model (all_different)."""
    m, _g = connected.build(3, 81, list(force), list(ban), False)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 4
    s.parameters.max_time_in_seconds = 60
    st = s.solve(m)
    got_a = st in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    status_b, shape_b = recheck_pins.solve(list(force), list(ban), seconds=60)
    got_b = shape_b is not None
    assert got_a == got_b == feasible, (s.status_name(st), status_b)
    if feasible:
        assert recheck_pins.admissible(shape_b)
        assert all(i in shape_b for i in force) and not any(i in shape_b for i in ban)


def test_lazy_connectivity_cuts_return_a_connected_shape():
    m, g = connected.build(10, 30, [], [], False)
    shape, _cuts = connected.solve_connected(m, g, 60, 4, lambda msg: None)
    assert shape is not None, "control: connected admissible shapes exist"
    assert len(connected.components(shape)) == 1
    assert shapes.connected(shape)
    assert shapes.givens(shape) is not None


def test_gridenum_six_by_six_counter_and_size_12(tmp_path):
    """The 6x6 enumerator: counter agrees with a full grid, size 12 has exactly
    two unique shapes up to symmetry (docs/research/counting_shaded/six-by-six-unique.jsonl)."""
    import gridenum

    gridenum.geometry(6, 2, 3)
    full = [1, 2, 3, 4, 5, 6, 4, 5, 6, 1, 2, 3, 2, 3, 1, 5, 6, 4]
    full += [5, 6, 4, 2, 3, 1, 3, 1, 2, 6, 4, 5, 6, 4, 5, 3, 1, 2]
    assert gridenum.count(dict(enumerate(full)), 2) == 1
    assert gridenum.count({}, 2) == 2
    status, shapes, solvable, unique = gridenum.enumerate_native(
        12, (), (), 120, tmp_path, lambda _m: None, symmetry=True
    )
    assert (status, shapes, solvable, unique) == ("exhausted", 66, 19, 2)


def test_build_dir_is_a_cache_merge_cleanup_sweeps():
    # merge-cleanup (#559) sweeps an ignored file unasked only when it sits in
    # a cache-named directory (here `target`) whose own .gitignore is `*`.
    assert fastclimb.BUILD.name == "target"
    assert "*" in (fastclimb.BUILD / ".gitignore").read_text().splitlines()


def test_build_dir_is_outside_scratch_so_a_worker_sweep_cannot_delete_it():
    # #633: a `rm -rf .scratch` sweep must never reach this tracked anchor.
    # Checked relative to the repo, not the absolute path: a checkout under
    # a directory that happens to be named .scratch (e.g. a seam worktree)
    # would otherwise fail this test for a reason the sweep can't cause.
    assert ".scratch" not in fastclimb.BUILD.relative_to(fastclimb.REPO).parts


# --- depth-first shape enumerator (#506): the second engine, sharing nothing with CP-SAT ---

R9C12 = (72, 73)


def dfs(size, force=R9C12, ban=(), all_digits=True, symmetry=False, seconds=0, **kw):
    fastclimb.pins(force, ban)
    return fastclimb.enumerate_shapes(size, all_digits, symmetry, seconds=seconds, **kw)


def window_ban(rows, cols):
    """Every cell outside the rows x cols window, as a ban list."""
    return [i for i in range(81) if i // 9 not in rows or i % 9 not in cols]


@pytest.mark.parametrize(
    "size, shapes_found, solvable",
    [(21, 2, 2), (20, 2, 2), (19, 2, 0), (18, 0, 0), (17, 0, 0)],
)
def test_dfs_matches_record_pinned_r9c12_all_digits(size, shapes_found, solvable):
    # docs/research/2026-09-16-counting-shaded-connected.md, "No unique shading
    # exists under r9c1 + r9c2": two shapes at 21 and at 20, none below, no unique.
    r = dfs(size)
    assert r.exhausted
    assert (r.shapes, r.solvable, r.unique) == (shapes_found, solvable, 0)


@pytest.mark.parametrize(
    "size, shapes_found",
    [(22, 1), (23, 0), (24, 1), (25, 0), (26, 0), (27, 0), (28, 0), (29, 0), (30, 0)],
)
def test_dfs_matches_record_pinned_r9c12_without_all_digits(size, shapes_found):
    # Same note: one shape at 22 and one at 24, none at 23 or 25 and up.
    r = dfs(size, all_digits=False)
    assert r.exhausted
    assert r.shapes == shapes_found
    # the 24-cell shape has no grid ("pinned-r9c12-24-nogrid"); the 22-cell one does
    assert r.solvable == (1 if size == 22 else 0)


def test_dfs_solvable_shapes_are_admissible_and_solvable_by_the_python_counter():
    r = dfs(21)
    assert len(r.solvable_shapes) == r.solvable == 2
    for shape, k in r.solvable_shapes:
        assert len(shape) == 21 and set(R9C12) <= shape
        g = shapes.givens(shape)
        assert shapes.eight_ok(g)
        assert shapes.count_solutions(g, 2) == k >= 1


def test_dfs_agrees_with_cpsat_native_enumeration_pinned(tmp_path):
    import shapeenum

    for size in (19, 20):
        fastclimb.pins(R9C12)
        status, n, solvable, unique = shapeenum.enumerate_native(
            size, R9C12, (), 120, tmp_path, lambda _m: None
        )
        assert status == "exhausted"  # a timed-out CP-SAT count proves nothing
        r = dfs(size)
        assert (r.shapes, r.solvable, r.unique) == (n, solvable, unique)


def test_dfs_reports_timeout_not_exhaustion():
    # Unpinned size 21 cannot finish in a few milliseconds; a cut-off run must
    # say so rather than report a count as if the size were exhausted.
    r = dfs(21, force=(), seconds=0.05, symmetry=True)
    assert not r.exhausted


def test_dfs_unpinned_size_17_matches_cpsat_native_symmetry_record():
    # `shapeenum.py --size 17 --mode native --symmetry` (CP-SAT, 70 s): 26 shapes
    # up to the 8 dihedral images, 12 solvable, none unique.
    r = dfs(17, force=(), symmetry=True)
    assert r.exhausted
    assert (r.shapes, r.solvable, r.unique) == (26, 12, 0)


def test_dfs_flags_a_solvable_list_cut_short_by_max_stored():
    full = dfs(21)
    assert not full.truncated
    capped = dfs(21, max_stored=1)
    assert capped.solvable == 2 and len(capped.solvable_shapes) == 1
    assert capped.truncated


@pytest.mark.parametrize("cap", [0, 1])
def test_dfs_refuses_a_cap_that_would_call_every_solvable_shape_unique(cap):
    with pytest.raises(ValueError, match="cap below 2"):
        dfs(21, cap=cap)


def test_dfs_refuses_symmetry_with_pins():
    with pytest.raises(ValueError, match="symmetry with pins"):
        dfs(19, symmetry=True)


@pytest.mark.parametrize("size", [0, 82])
def test_dfs_refuses_a_size_outside_the_board(size):
    with pytest.raises(ValueError, match="size not in 1-81"):
        dfs(size)


def test_dfs_all_digits_prune_keeps_a_shape_whose_only_eight_is_two_steps_out(tmp_path):
    # Size 14 inside rows 0-4 x columns 1-6: three shapes carry all of 1-8. One shows
    # its only 8 on a cell two steps from the partial shape when the walk reaches it;
    # a prune that undercounts that cell's reach drops it. CP-SAT is the second opinion.
    import shapeenum

    ban = window_ban(range(5), range(1, 7))
    fastclimb.pins((), ban)
    status, n, solvable, unique = shapeenum.enumerate_native(
        14, (), ban, 120, tmp_path, lambda _m: None
    )
    assert status == "exhausted"
    r = dfs(14, force=(), ban=ban)
    assert r.exhausted
    assert (r.shapes, r.solvable, r.unique) == (n, solvable, unique)
    assert r.shapes == 3


# --- one flow encoding, one neighbour table ---------------------------------


def _defined_names(path):
    import ast

    return {
        n.name
        for n in ast.walk(ast.parse(path.read_text()))
        if isinstance(n, ast.FunctionDef)
    }


def test_flow_connectivity_and_neighbour_table_are_defined_once():
    owners = {
        name: [p.name for p in HERE.glob("*.py") if name in _defined_names(p)]
        for name in ("add_flow_connectivity", "neighbours")
    }
    assert owners == {"add_flow_connectivity": ["shapes.py"], "neighbours": []}


def _flow_feasible(shape, **kwargs):
    m = cp_model.CpModel()
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    for i in range(81):
        m.add(g[i] == (1 if i in shape else 0))
    shapes.add_flow_connectivity(m, g, **kwargs)
    s = cp_model.CpSolver()
    return s.solve(m) in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_flow_connectivity_matches_the_flood_fill():
    rng = random.Random(5)
    seen = set()
    for _ in range(40):
        shape = {rng.randrange(81)}
        while len(shape) < rng.randint(2, 9):
            shape.add(rng.choice([j for i in shape for j in shapes.ORTH[i]]))
        if rng.random() < 0.5:
            shape.add(rng.randrange(81))  # often a stray, disconnected cell
        want = shapes.connected(shape)
        seen.add(want)
        assert _flow_feasible(shape) == want
    assert seen == {True, False}
    line = set(range(9))
    assert _flow_feasible(line, cap=9)
    assert not _flow_feasible(line | {40}, cap=10)

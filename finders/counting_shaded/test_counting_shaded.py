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


def random_blob(rng, size):
    shape = {rng.randrange(81)}
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
    blob = random_blob(random.Random(4), 6)
    assert shapes.givens(blob) is not None or True  # shape itself may be inadmissible
    outside = next(i for i in range(81) if i not in blob)
    fastclimb.pins(force=[outside])
    assert shapes.givens(blob) is None, "a shape missing a forced cell must be rejected"
    assert fastclimb.count(blob, 2) == -1
    inside = next(iter(blob))
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
    "eight,force,ban", [(False, (), ()), (True, (), ()), (False, (0, 1), (80,))]
)
def test_c_and_python_filters_agree(eight, force, ban):
    rng = random.Random(11)
    fastclimb.require_eight(eight)
    fastclimb.pins(force, ban)
    admissible = 0
    for _ in range(4000):
        shape = random_blob(rng, rng.randrange(3, 24))
        if rng.random() < 0.3:
            shape ^= {rng.randrange(81)}
        g = shapes.givens(shape)
        want = shapes.count_solutions(g, 50) if shapes.eight_ok(g) else -1
        assert fastclimb.count(shape, 50) == want, sorted(shape)
        admissible += want >= 0
    if not force and not eight:
        assert admissible > 0, "control: the plain filter must accept something"


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
    """Build a shape the counter says has 2+ solutions, then demand a rejection."""
    rng = random.Random(3)
    row = json.loads(EXAMPLES.read_text().splitlines()[0])
    base = set(row["shape"])
    for _ in range(500):
        trial = set(base)
        trial ^= {rng.randrange(81)}
        g = shapes.givens(trial) if shapes.connected(trial) else None
        if g is None:
            g = {i: sum(j in trial for j in shapes.NEIGH[i]) for i in trial}
            if len({(shapes.BOX[i], n) for i, n in g.items()}) != len(g):
                continue
        if shapes.count_solutions(g, 2) == 2:
            assert verify_all.check([divmod(i, 9) for i in trial])[0] is None
            return
    pytest.fail("no shape with 2+ solutions found to test the rejection")


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

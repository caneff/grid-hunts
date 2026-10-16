"""The shared Renbanana encodings, one behaviour at a time (#663).

    uv run finders/renbanana/tools/test_renbanana_model.py

Each encoding is pinned to a small board and the solver's verdict read back:
a legal pin must solve, an illegal one must be INFEASIBLE (a proof, not a
timeout -- the status is compared by name). The last test checks that the
hunt and the four probes use these definitions rather than their own copies.
"""

import collections
import sys
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import renbanana_model as rm
import renbanana_verify as rv

DATA_ROOT = Path(__file__).resolve().parents[3] / "docs" / "research" / "renbanana"


def status_of(m):
    s = cp.CpSolver()
    s.parameters.max_time_in_seconds = 30
    s.parameters.num_workers = 1
    return s.status_name(s.solve(m))


def digits_and_shading():
    m = cp.CpModel()
    d = {p: m.new_int_var(1, 9, f"d{p}") for p in rm.CELLS}
    choc = {p: m.new_bool_var(f"c{p}") for p in rm.CELLS}
    return m, d, choc


def pin(m, choc, chocolate):
    for p in rm.CELLS:
        m.add(choc[p] == (1 if p in chocolate else 0))


def test_sudoku():
    path = sorted(DATA_ROOT.glob("candidates*/cand_*.json"))[0]
    grid, _, _ = rv.load(path)
    m, d, _ = digits_and_shading()
    rm.sudoku(m, d)
    for p in rm.CELLS:
        m.add(d[p] == grid[p])
    assert status_of(m) == "OPTIMAL"
    m, d, _ = digits_and_shading()
    rm.sudoku(m, d)
    m.add(d[0, 0] == 4)
    m.add(d[0, 8] == 4)  # same row
    assert status_of(m) == "INFEASIBLE"
    m, d, _ = digits_and_shading()
    rm.sudoku(m, d)
    m.add(d[0, 0] == 4)
    m.add(d[2, 2] == 4)  # same box
    assert status_of(m) == "INFEASIBLE"
    m, d, _ = digits_and_shading()
    rm.sudoku(m, d)
    m.add(d[0, 0] == 4)
    m.add(d[8, 0] == 4)  # same column
    assert status_of(m) == "INFEASIBLE"


def test_rectangle_lemma():
    block = {(0, 0), (0, 1), (1, 0), (1, 1)}
    m, _, choc = digits_and_shading()
    rm.rectangle_lemma(m, choc)
    pin(m, choc, block)
    assert status_of(m) == "OPTIMAL"
    m, _, choc = digits_and_shading()
    rm.rectangle_lemma(m, choc)
    pin(m, choc, block - {(1, 1)})  # an L: three of a 2x2 window
    assert status_of(m) == "INFEASIBLE"


def test_whisper():
    pair = {(4, 4), (4, 5)}
    for lo, hi, want in (
        (3, 4, "INFEASIBLE"),
        (3, 7, "INFEASIBLE"),  # a gap of 4: the boundary
        (2, 7, "OPTIMAL"),
    ):
        m, d, choc = digits_and_shading()
        rm.whisper(m, d, choc)
        pin(m, choc, pair)
        m.add(d[4, 4] == lo)
        m.add(d[4, 5] == hi)
        assert status_of(m) == want, (lo, hi)
    m, d, choc = digits_and_shading()  # banana neighbours are unconstrained
    rm.whisper(m, d, choc)
    pin(m, choc, set())
    m.add(d[4, 4] == 3)
    m.add(d[4, 5] == 4)
    assert status_of(m) == "OPTIMAL"


def test_whisper_on_a_fixed_shading():
    is_choc = dict.fromkeys(rm.CELLS, False) | {(4, 4): True, (4, 5): True}
    for lo, hi, want in (
        (3, 4, "INFEASIBLE"),
        (3, 7, "INFEASIBLE"),  # a gap of 4: the boundary
        (2, 7, "OPTIMAL"),
    ):
        m, d, _ = digits_and_shading()
        rm.whisper_on_shading(m, d, is_choc)
        m.add(d[4, 4] == lo)
        m.add(d[4, 5] == hi)
        assert status_of(m) == want, (lo, hi)


def test_whisper_on_digits():
    """Fixed digits: an adjacent pair under 5 apart cannot both be chocolate."""
    grid = dict.fromkeys(rm.CELLS, 1)
    grid[4, 4], grid[4, 5], grid[3, 4] = 3, 7, 8
    for pair, want in (
        ({(4, 4), (4, 5)}, "INFEASIBLE"),  # 3 and 7: gap 4
        ({(4, 4), (3, 4)}, "OPTIMAL"),  # 3 and 8: gap 5
    ):
        m, _, choc = digits_and_shading()
        rm.whisper_on_digits(m, choc, grid)
        pin(m, choc, pair)
        assert status_of(m) == want, pair


def test_maximal_rectangle_literals():
    """Chocolate 2x2 inside, banana border: all literals hold; a chocolate
    border cell breaks it."""
    block = {(3, 3), (3, 4), (4, 3), (4, 4)}
    border = set(rm.border_of(2, 2, 3, 3))
    assert len(border) == 8
    for extra, want in ((set(), "OPTIMAL"), ({(2, 3)}, "INFEASIBLE")):
        m, _, choc = digits_and_shading()
        for lit in rm.maximal_chocolate_lits(choc, 2, 2, 3, 3):
            m.add(lit == 1)
        pin(m, choc, block | extra)
        assert status_of(m) == want, extra


def test_forbid_banana_rectangles():
    m, _, choc = digits_and_shading()
    rm.forbid_banana_rectangles(m, choc)
    pin(m, choc, set())  # all banana: one 9x9 rectangle
    assert status_of(m) == "INFEASIBLE"
    m, _, choc = digits_and_shading()
    rm.forbid_banana_rectangles(m, choc)
    pin(m, choc, {(0, 0)})  # banana minus a corner: not a rectangle
    assert status_of(m) == "OPTIMAL"


def test_banana_labels():
    m, _, choc = digits_and_shading()
    lab = rm.banana_labels(m, choc)
    pin(m, choc, {(0, 0)})
    s = cp.CpSolver()
    s.parameters.num_workers = 1
    assert s.solve(m) == cp.OPTIMAL
    held = {
        p: [e for e in range(rm.IDX[p] + 1) if s.value(lab[p, e])] for p in rm.CELLS
    }
    assert held[0, 0] == []  # chocolate carries no label
    assert all(len(held[p]) == 1 for p in rm.CELLS if p != (0, 0))
    assert held[0, 1] == held[1, 1] == held[1, 0]  # banana neighbours share it


def test_banana_labels_pin_and_sharing():
    """Banana cells (0,1) and (0,2) only; every other cell is chocolate."""
    banana = {(0, 1), (0, 2)}
    chocolate = set(rm.CELLS) - banana
    for pin_labels, want in ((True, "INFEASIBLE"), (False, "OPTIMAL")):
        # Label 0 belongs to (0,0), which is chocolate: only an unpinned model
        # lets (0,1) take it.
        m, _, choc = digits_and_shading()
        lab = rm.banana_labels(m, choc, pin=pin_labels)
        pin(m, choc, chocolate)
        m.add(lab[(0, 1), 0] == 1)
        assert status_of(m) == want, pin_labels
    # Adjacent banana cells share a label. Both labels here are at or below
    # (0,1)'s index, so only the share clause can refuse the split pin.
    for second, want in ((0, "OPTIMAL"), (1, "INFEASIBLE")):
        m, _, choc = digits_and_shading()
        lab = rm.banana_labels(m, choc, pin=False)
        pin(m, choc, chocolate)
        m.add(lab[(0, 1), 0] == 1)
        m.add(lab[(0, 2), second] == 1)
        assert status_of(m) == want, second


SHARED = (
    "sudoku",
    "rectangle_lemma",
    "whisper",
    "whisper_on_shading",
    "whisper_on_digits",
    "banana_labels",
    "forbid_banana_rectangles",
    "forbid_dead_chocolate",
    "maximal_chocolate_lits",
    "chocolate_spot",
    "forbid_banana_group",
)


def calls_while(build):
    """Which shared encodings `build()` calls through the model module."""
    seen = collections.Counter()
    real = {name: getattr(rm, name) for name in SHARED}

    def spy(name):
        def wrapped(*a, **k):
            seen[name] += 1
            return real[name](*a, **k)

        return wrapped

    for name in SHARED:
        setattr(rm, name, spy(name))
    try:
        build()
    finally:
        for name in SHARED:
            setattr(rm, name, real[name])
    return seen


def test_encodings_have_one_definition():
    """Each builder reaches the shared encodings it needs through the model
    module. A builder that stops calling one -- because it carries its own
    copy again -- fails here. The builders and the encodings they use:"""
    import max_house_circles as mh
    import probe_circle_pattern as pc
    import probe_inverted as pi
    import prove_pair as pp
    import renbanana_cpsat as rc

    path = sorted(DATA_ROOT.glob("candidates*/cand_*.json"))[0]
    grid, is_choc, _ = rv.load(path)
    house = mh.house("row5")
    wanted = {
        "rc.Shadings": (
            lambda: rc.Shadings(),
            {"rectangle_lemma", "banana_labels", "forbid_dead_chocolate"},
        ),
        "rc.digit_model": (
            lambda: rc.digit_model(is_choc),
            {"sudoku", "whisper_on_shading"},
        ),
        "pi.random_grid": (lambda: pi.random_grid(0, 5, 1), {"sudoku"}),
        "pi.Shadings": (
            lambda: pi.Shadings(grid),
            {
                "rectangle_lemma",
                "whisper_on_digits",
                "banana_labels",
                "forbid_dead_chocolate",
            },
        ),
        "pp.JointPair": (
            lambda: pp.JointPair([(2, 2, 0, 0), (2, 3, 4, 4)], renban=False),
            {"sudoku", "rectangle_lemma", "whisper", "forbid_banana_rectangles"}
            | {"forbid_dead_chocolate"},
        ),
        "pp.JointPair.labels": (
            lambda: pp.JointPair([(2, 2, 0, 0), (2, 3, 4, 4)]),
            {"banana_labels"},
        ),
        "pc.build": (
            lambda: pc.build([]),
            {
                "sudoku",
                "rectangle_lemma",
                "whisper",
                "forbid_banana_rectangles",
                "banana_labels",
            },
        ),
        "mh.shading_model": (
            lambda: mh.shading_model(house),
            {"rectangle_lemma", "forbid_banana_rectangles"},
        ),
        "mh.digits_on": (
            lambda: mh.digits_on(is_choc, house, 0, 1, 1),
            {"sudoku", "whisper_on_shading"},
        ),
    }
    for name, (build, need) in wanted.items():
        got = calls_while(build)
        assert need <= set(got), f"{name} no longer calls {sorted(need - set(got))}"

    # Calls made directly by a builder, beyond the ones forbid_dead_chocolate
    # makes for it: two pinned rectangles, one maximal-literal set per placement.
    pair = [(2, 2, 0, 0), (2, 3, 4, 4)]
    model = None

    def build_pair():
        nonlocal model
        model = pp.JointPair(pair, renban=False)

    got = calls_while(build_pair)
    assert got["maximal_chocolate_lits"] >= model.dead + len(pair), "prove_pair pins"
    got = calls_while(lambda: mh.shading_model(house))
    assert got["maximal_chocolate_lits"] >= len(rm.PLACEMENTS), "max_house rect"
    spots = calls_while(lambda: rc.Shadings().spot(2, 2, 3, 3))
    assert spots["chocolate_spot"] == 1
    cuts = calls_while(lambda: rc.Shadings().forbid_component([(0, 0)]))
    assert cuts["forbid_banana_group"] == 1


if __name__ == "__main__":
    test_sudoku()
    test_rectangle_lemma()
    test_whisper()
    test_whisper_on_a_fixed_shading()
    test_whisper_on_digits()
    test_maximal_rectangle_literals()
    test_forbid_banana_rectangles()
    test_banana_labels()
    test_banana_labels_pin_and_sharing()
    test_encodings_have_one_definition()
    print("OK")

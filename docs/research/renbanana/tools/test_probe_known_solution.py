"""`--unique` with a solution already in hand must not re-find it.

The proof is the *second*-solution search; the first solve only recovers a
grid we may already have on disk. These tests pin that: supplied a known
solution, `prove_unique` runs exactly one solve and hands it the whole budget.

The solver is stubbed, so the real CP-SAT model is never solved here -- what
is under test is the control flow, not the constraints.

    uv run --with ortools docs/research/renbanana/tools/test_probe_known_solution.py
"""

import contextlib
import sys
import tempfile
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_circle_pattern as pcp  # noqa: E402
import renbanana_verify as rv  # noqa: E402

CAND = (
    Path(__file__).resolve().parents[1] / "candidates-fully-circled" / "cand_00.json"
)
REAL_SOLVER = cp.CpSolver


class Args:
    seconds = 300.0
    workers = 1


def bare_model():
    """Just the variables `prove_unique` touches -- enough for `block`."""
    m = cp.CpModel()
    choc = {p: m.new_bool_var("") for p in pcp.CELLS}
    d = {p: m.new_int_var(1, 9, "") for p in pcp.CELLS}
    return m, choc, d


@contextlib.contextmanager
def stub_solver(statuses, answers, calls):
    """Replace CpSolver with one that returns `statuses` in order and reads
    variables out of `answers` (keyed by id), appending each call's budget to
    `calls`. No real solve happens -- the control flow is what is under test."""

    class Fake:
        def __init__(self):
            self.parameters = REAL_SOLVER().parameters
            self.wall_time = 0.0

        def solve(self, m):
            calls.append(self.parameters.max_time_in_seconds)
            return statuses[len(calls) - 1]

        def value(self, var):
            return answers[id(var)]

        def status_name(self, st):
            return REAL_SOLVER().status_name(st)

    cp.CpSolver = Fake
    try:
        yield
    finally:
        cp.CpSolver = REAL_SOLVER


def answers_for(choc, d, grid, is_choc):
    out = {id(d[p]): grid[p] for p in pcp.CELLS}
    out.update({id(choc[p]): int(is_choc[p]) for p in pcp.CELLS})
    return out


def test_known_solution_skips_the_first_solve():
    grid, is_choc, circles = rv.load(CAND)
    m, choc, d = bare_model()
    calls = []
    with stub_solver([cp.INFEASIBLE], answers_for(choc, d, grid, is_choc), calls):
        verdict = pcp.prove_unique(m, choc, d, circles, Args(), known=(grid, is_choc))
    assert len(calls) == 1, f"expected one solve, got {len(calls)}"
    assert calls[0] == Args.seconds, "the second search must get the whole budget"
    assert verdict == "UNIQUE"


def test_without_a_known_solution_it_solves_twice():
    grid, is_choc, circles = rv.load(CAND)
    m, choc, d = bare_model()
    calls = []
    answers = answers_for(choc, d, grid, is_choc)
    with stub_solver([cp.FEASIBLE, cp.INFEASIBLE], answers, calls):
        verdict = pcp.prove_unique(m, choc, d, circles, Args())
    assert calls == [Args.seconds / 2, Args.seconds]
    assert verdict == "UNIQUE"


def test_a_timed_out_second_search_is_never_unique():
    grid, is_choc, circles = rv.load(CAND)
    m, choc, d = bare_model()
    with stub_solver([cp.UNKNOWN], answers_for(choc, d, grid, is_choc), []):
        verdict = pcp.prove_unique(m, choc, d, circles, Args(), known=(grid, is_choc))
    assert verdict == "NOT PROVED"


def test_load_known_reads_a_single_candidate_file():
    grid, is_choc, _ = rv.load(CAND)
    got = pcp.load_known(CAND)
    assert got == [(grid, is_choc)]


def test_a_supplied_solution_is_checked_against_the_clue_set():
    """A file that does not satisfy the clues must be refused, not blocked.

    Blocking a point the model never contained leaves the second search
    INFEASIBLE for the wrong reason, which prints a false UNIQUE.
    """
    grid, is_choc, circles = rv.load(CAND)
    sizes = {p: len(g) for c in (True, False) for g in rv.components(is_choc, c) for p in g}
    unsatisfied = next(
        p for p in pcp.CELLS if p not in set(circles) and grid[p] != sizes[p]
    )
    assert pcp.clue_complaints(
        (grid, is_choc), [*circles, unsatisfied], (), (), ()
    ), "a circle the grid does not satisfy must be reported"
    assert pcp.clue_complaints((grid, is_choc), circles, (), (), []) == []


def test_a_supplied_solution_is_checked_against_givens_and_shading():
    grid, is_choc, circles = rv.load(CAND)
    banana = next(p for p in pcp.CELLS if not is_choc[p])
    chocolate = next(p for p in pcp.CELLS if is_choc[p])
    assert pcp.clue_complaints((grid, is_choc), circles, (banana,), (), [])
    assert pcp.clue_complaints((grid, is_choc), circles, (), (chocolate,), [])
    assert pcp.clue_complaints((grid, is_choc), circles, (chocolate,), (banana,), []) == []
    p0 = pcp.CELLS[0]
    bad_given = (p0, 1 + grid[p0] % 9)
    assert pcp.clue_complaints((grid, is_choc), circles, (), (), [bad_given])
    assert pcp.clue_complaints((grid, is_choc), circles, (), (), [(p0, grid[p0])]) == []


class Flags:
    def __init__(self, **kw):
        self.unique = self.known = self.known_solution = None
        self.enumerate = self.out = None
        self.__dict__.update(kw)


def test_known_blocks_are_refused_under_unique():
    """`--known` blocks pool solutions out of the model. Under `--unique` the
    second search would then miss a real second solution and report a proof."""
    assert pcp.flag_complaint(Flags(unique=True, known="pool/"))
    assert pcp.flag_complaint(Flags(known="pool/")) is None


def test_enumerate_only_flags_are_refused_under_unique():
    """`--unique` returns before the enumerate branch, so `--out` writes
    nothing and `--enumerate` is dropped -- the no-op `flag_complaint` exists
    to refuse."""
    assert pcp.flag_complaint(Flags(unique=True, enumerate=50))
    assert pcp.flag_complaint(Flags(unique=True, out="results.txt"))
    assert pcp.flag_complaint(Flags(enumerate=50, out="results.txt")) is None


def test_known_solution_outside_unique_is_refused():
    assert pcp.flag_complaint(Flags(known_solution="cand_00.json"))
    assert pcp.flag_complaint(Flags(unique=True, known_solution="cand_00.json")) is None

def test_an_out_file_named_json_falls_through_to_the_streamed_parser(tmp=None):
    """`--out` files get `.json` names too, so it is the `grid` key that says
    a file is a candidate, not the suffix."""
    grid, is_choc, _ = rv.load(CAND)
    body = "\n".join(["--- solution 1   after 0s", *pcp.render(grid, is_choc)])
    out = Path(tempfile.mkdtemp()) / "run.json"
    out.write_text(body + "\n")
    assert pcp.load_known(out) == [(grid, is_choc)]


if __name__ == "__main__":
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_"):
            fn()
    print("OK")

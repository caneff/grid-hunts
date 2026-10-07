"""`probe_circle_pattern --enumerate` calls a run exhaustive only on INFEASIBLE.

An UNKNOWN that stops the loop before the time budget is spent is not a proof
that no more solutions exist (#746). The seam is `enumerate_all`'s printout and
its `--out` footer; the solver is a stub that returns one scripted status.

    uv run finders/renbanana/tools/test_probe_circle_enumerate_exhaustion.py
"""

import contextlib
import io
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_circle_pattern as pcp

EXHAUSTED = "search exhausted"
NOT_EXHAUSTED = "there may be more"


class StubSolver:
    """Returns `status` on its first solve, after 1 s of a larger budget."""

    status = pcp.cp.UNKNOWN
    parameters = SimpleNamespace()
    wall_time = 1.0

    def solve(self, _model):
        return type(self).status

    def status_name(self, st):
        return st.name


def run_enumerate(status):
    """(stdout, footer) of an enumerate run whose only solve ends in `status`."""
    StubSolver.status = status
    real = pcp.cp.CpSolver
    pcp.cp.CpSolver = StubSolver
    try:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "sols.txt"
            a = SimpleNamespace(workers=1, enumerate=10, seconds=1800.0, out=str(out))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                pcp.enumerate_all(None, {}, {}, [], a)
            return buf.getvalue(), out.read_text()
    finally:
        pcp.cp.CpSolver = real


def test_unknown_before_the_budget_is_spent_is_not_exhausted():
    text, footer = run_enumerate(pcp.cp.UNKNOWN)
    assert NOT_EXHAUSTED in text and EXHAUSTED not in text, text
    assert "UNKNOWN" in text, text
    assert "cap or time limit hit" in footer and "exhaustive" not in footer, footer
    assert "UNKNOWN" in footer, footer


def test_infeasible_last_solve_is_exhausted():
    text, footer = run_enumerate(pcp.cp.INFEASIBLE)
    assert EXHAUSTED in text and NOT_EXHAUSTED not in text, text
    assert footer.strip().endswith("-- exhaustive"), footer


def test_real_solver_on_a_contradictory_clue_set_is_exhausted():
    m, choc, d = pcp.build([], givens=[((0, 0), 1), ((0, 1), 1)])
    a = SimpleNamespace(workers=1, enumerate=10, seconds=60.0, out=None)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        pcp.enumerate_all(m, choc, d, [], a)
    assert "distinct solutions: 0  (search exhausted" in buf.getvalue(), buf.getvalue()


if __name__ == "__main__":
    test_unknown_before_the_budget_is_spent_is_not_exhausted()
    test_infeasible_last_solve_is_exhausted()
    test_real_solver_on_a_contradictory_clue_set_is_exhausted()
    print("OK")

"""The candidate-carrying human solver on the design-of-record boards.

Board 28 is the design of record (docs/research/2026-09-14-galaxy-copycat-design.md,
"Ruling (2026-09-17)"): seeded from board 14's link state, it must solve with
no case split. Board 27 is the near-miss that needs one: the solver must
still reach the same wall the doc records, and no further, or a regression
either loosened a rule (finds more than it should) or broke one (finds
less).

The solutions below are hard-coded rather than recomputed from
`.scratch/copycat-rsl/b14-residual.npz` (gitignored, scratch-only) so this
test runs on a bare checkout; they were read off that residual set once,
against each board's lines and pairs, and match the doc's own description of
each board.

    uv run finders/galaxy-copycat/test_human_solver.py
"""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import human_solver
from human_solver import Human, load_board, seed_from_link

BOARDS = (
    Path(__file__).resolve().parents[2]
    / "docs/research/2026-09-14-galaxy-copycat/boards"
)
FORCED = json.loads((BOARDS / "board14-forced.json").read_text())
LINK = BOARDS / "board14-link-state.json"

BOARD28_SOLUTION = [
    1, 2, 4, 5, 3, 8, 9, 6, 7,
    3, 6, 8, 4, 7, 9, 1, 5, 2,
    9, 7, 5, 1, 2, 6, 4, 8, 3,
    8, 5, 2, 6, 9, 3, 7, 1, 4,
    7, 1, 6, 8, 4, 2, 5, 3, 9,
    4, 9, 3, 7, 5, 1, 6, 2, 8,
    5, 3, 9, 2, 6, 4, 8, 7, 1,
    2, 8, 7, 9, 1, 5, 3, 4, 6,
    6, 4, 1, 3, 8, 7, 2, 9, 5,
]  # fmt: skip
BOARD28_COPYCATS = [6, 13, 20, 27, 43, 50, 57, 71, 73]

BOARD27_SOLUTION = [
    2, 3, 4, 8, 9, 7, 1, 5, 6,
    1, 6, 8, 4, 5, 3, 7, 9, 2,
    5, 7, 9, 1, 2, 6, 4, 8, 3,
    8, 9, 2, 6, 7, 5, 3, 1, 4,
    3, 1, 6, 2, 4, 8, 9, 7, 5,
    4, 5, 7, 9, 3, 1, 6, 2, 8,
    7, 2, 5, 3, 6, 9, 8, 4, 1,
    9, 8, 3, 5, 1, 4, 2, 6, 7,
    6, 4, 1, 7, 8, 2, 5, 3, 9,
]  # fmt: skip
BOARD27_COPYCATS = [8, 13, 20, 27, 43, 50, 57, 69, 73]


def test_board28_solves_in_six_rungs_with_no_case_split():
    lines, pairs = load_board(BOARDS / "board28-pair43x25-solved.json")
    h = Human(lines, pairs, FORCED, BOARD28_SOLUTION, BOARD28_COPYCATS)
    seed_from_link(h, LINK)
    h.run()
    assert h.solved(), h.placed()
    assert h.placed() == (81, 9)
    assert len(h.log) == 6, h.log


def test_board27_stops_at_fifty_seven_digits_seven_rungs():
    lines, pairs = load_board(BOARDS / "board27-pair34x52.json")
    h = Human(lines, pairs, FORCED, BOARD27_SOLUTION, BOARD27_COPYCATS)
    seed_from_link(h, LINK)
    h.run()
    assert not h.solved()
    assert h.placed() == (57, 7)
    assert len(h.log) == 7, h.log


HERE = Path(__file__).resolve().parent
BOARD28 = BOARDS / "board28-pair43x25-solved.json"


def run_cli(*args, cwd):
    return subprocess.run(
        [sys.executable, str(HERE / "human_solver.py"), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_cli_no_arguments_prints_usage_without_traceback():
    r = run_cli(cwd=HERE)
    assert r.returncode != 0
    assert "usage" in r.stderr.lower(), r.stderr
    assert "Traceback" not in r.stderr, r.stderr


def test_cli_from_its_own_directory_finds_default_inputs():
    r = run_cli(
        f"../../{BOARD28.relative_to(human_solver.REPO_ROOT)}",
        "--seed",
        f"../../{LINK.relative_to(human_solver.REPO_ROOT)}",
        "--no-check",
        cwd=HERE,
    )
    assert r.returncode == 0, r.stderr
    assert "solved placed (81, 9) rungs 6" in r.stdout, r.stdout


def call_main(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = human_solver.main(list(argv))
        except SystemExit as e:  # argparse refusals
            code = e.code
    return code, out.getvalue(), err.getvalue()


def with_absent_npz(fn):
    saved = human_solver.RESIDUAL_NPZ
    with tempfile.TemporaryDirectory() as d:
        human_solver.RESIDUAL_NPZ = Path(d) / "absent.npz"
        try:
            fn(human_solver.RESIDUAL_NPZ)
        finally:
            human_solver.RESIDUAL_NPZ = saved


def test_cli_no_check_runs_without_the_npz_and_says_so():
    def body(npz):
        code, out, err = call_main(str(BOARD28), "--seed", str(LINK), "--no-check")
        assert code == 0, err
        assert "solution check skipped" in out, out
        assert "solved placed (81, 9) rungs 6" in out, out

    with_absent_npz(body)


def test_cli_plain_and_batch_modes_name_the_missing_npz():
    def body(npz):
        for argv in ([str(BOARD28)], ["batch"]):
            code, _out, err = call_main(*argv)
            assert code == 1, (argv, code)
            assert str(npz) in err, err

    with_absent_npz(body)


def test_cli_refuses_unknown_flags_and_a_dangling_seed():
    for argv in ([str(BOARD28), "--no-lock"], [str(BOARD28), "--seed"]):
        code, _out, err = call_main(*argv)
        assert code == 2, (argv, code)
        assert "usage" in err.lower(), err


def test_default_npz_resolves_from_the_repo_root():
    assert human_solver.RESIDUAL_NPZ == (
        human_solver.REPO_ROOT / ".scratch/copycat-rsl/b14-residual.npz"
    )
    assert Path(__file__).resolve().parents[2] == human_solver.REPO_ROOT


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("OK")

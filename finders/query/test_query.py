"""The board-question driver's own suite (spec #65, #94, #95), on the toy
finder.

Drives `query.py` as a subprocess on `toy_finder.py` (one row of distinct
digits) and asserts what lands in the output directory: each answer's
`answers.jsonl` line and label, its picture, and the last printed line. The
forced-mark tests drive the conditions helper through condition files.

    uv run finders/query/test_query.py
"""

import json
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
QUERY = HERE / "query.py"
TOY = HERE / "toy_finder.py"
sys.path.insert(0, str(HERE))
from query import CELL, MARGIN, MARK_COLOR, MARK_RADIUS

WHITE = (255, 255, 255)


def board(tmp, **fields):
    path = Path(tmp) / "board.json"
    path.write_text(json.dumps(fields))
    return path


def cli(board_path, out, *questions, extra=()):
    return subprocess.run(
        [
            sys.executable,
            str(QUERY),
            str(TOY),
            str(board_path),
            *questions,
            "--out",
            str(out),
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def answers(out):
    return [
        json.loads(line) for line in (out / "answers.jsonl").read_text().splitlines()
    ]


def corner(image, board_index, col):
    """A pixel near the top-left corner of cell (0, col) of the board drawn
    `board_index`-th from the left: off the digit, inside the cell."""
    board_width = 3 * CELL + 2 * MARGIN
    x = board_index * (board_width + MARGIN) + MARGIN + col * CELL + 6
    return image.getpixel((x, MARGIN + 6))


def test_not_unique_board():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[[0, 1]])
        r = cli(b, out, "feasible", "unique")
        assert r.returncode == 0, r.stderr
        feasible, unique = answers(out)
        assert feasible["question"] == "feasible", feasible
        assert feasible["status"] == "feasible", feasible
        assert feasible["label"] == "complete", feasible
        assert len(feasible["solutions"]) == 1 and feasible["solutions"][0]["c0"] == 1
        assert unique["status"] == "not_unique", unique
        assert unique["label"] == "complete", unique
        first, second = unique["solutions"]
        assert first != second and first["c0"] == second["c0"] == 1, unique
        assert "links" not in unique, "the toy has no link hook"

        pictures = [out / a["picture"] for a in (feasible, unique)]
        assert all(p.is_file() for p in pictures), pictures
        single = Image.open(pictures[0])
        double = Image.open(pictures[1]).convert("RGB")
        assert double.width == 2 * single.width + MARGIN, (double.size, single.size)
        for side in (0, 1):
            assert corner(double, side, 0) == WHITE, "c0 agrees: not shaded"
            for col in (1, 2):
                assert corner(double, side, col) != WHITE, f"c{col} differs: shaded"

        last = r.stdout.strip().splitlines()[-1]
        assert last == f"pictures: {pictures[0]} {pictures[1]}", last


def test_unique_and_infeasible_boards():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "unique"
        r = cli(board(tmp, width=3, clues=[[0, 1], [1, 2]]), out, "unique")
        assert r.returncode == 0, r.stderr
        (unique,) = answers(out)
        assert unique["status"] == "unique" and unique["label"] == "complete"
        assert unique["solutions"] == [{"c0": 1, "c1": 2, "c2": 3}], unique

        out = Path(tmp) / "infeasible"
        r = cli(board(tmp, width=3, clues=[[0, 1], [1, 1]]), out, "feasible", "unique")
        assert r.returncode == 0, r.stderr
        for answer in answers(out):
            assert answer["status"] == "infeasible", answer
            assert answer["label"] == "complete", answer
            assert answer["solutions"] == [], answer
            assert (out / answer["picture"]).is_file(), answer


def test_time_limit_is_capped():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[])
        r = cli(b, out, "feasible", "unique", extra=["--time-limit", "1e-9"])
        assert r.returncode == 0, r.stderr
        for answer in answers(out):
            assert answer["status"] == "timeout", answer
            assert answer["label"] == "capped", answer
            assert (out / answer["picture"]).is_file(), answer


def test_killed_run_keeps_answers_found():
    """The second question's build holds for a minute; the first answer's
    line and picture are on disk before the kill."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[[0, 1]], hold_after_builds=1)
        proc = subprocess.Popen(
            [
                sys.executable,
                str(QUERY),
                str(TOY),
                str(b),
                "feasible",
                "unique",
                "--out",
                str(out),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        lines = out / "answers.jsonl"
        deadline = time.monotonic() + 30
        while (
            not (lines.is_file() and lines.read_text()) and time.monotonic() < deadline
        ):
            time.sleep(0.05)
        assert proc.poll() is None, "the run ended before the kill"
        proc.send_signal(signal.SIGKILL)
        proc.wait()
        (feasible,) = answers(out)
        assert feasible["question"] == "feasible" and feasible["label"] == "complete"
        assert (out / feasible["picture"]).is_file(), feasible


def condition(tmp, name, cond):
    path = Path(tmp) / f"{name}.json"
    path.write_text(json.dumps(cond))
    return path


def ring(image, col):
    """A pixel on the left of the mark ring of cell (0, col): off the digit."""
    x = MARGIN + col * CELL + CELL // 2 - round(MARK_RADIUS * CELL) + 1
    return image.getpixel((x, MARGIN + CELL // 2))


def test_forced_conditions():
    """Each condition file is one answer, in the order given. On the board
    c0 = 1 the row is 1 2 3 or 1 3 2: every condition kind compiles, the
    held ones are held, and the one that fails shows a counterexample that
    breaks it, its cell ringed."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[[0, 1]])
        files = [
            condition(tmp, "any", {"any": [{"eq": ["c1", 2]}, {"eq": ["c1", 3]}]}),
            condition(tmp, "not-gt", {"not": {"gt": ["c0", 1]}}),
            condition(tmp, "all", {"all": [{"gt": ["c1", 1]}, {"gt": ["c2", 1]}]}),
            condition(tmp, "fails", {"eq": ["c2", 3]}),
        ]
        extra = [x for f in files for x in ("--condition", str(f))]
        r = cli(b, out, "forced", extra=extra)
        assert r.returncode == 0, r.stderr
        found = answers(out)
        assert [a["question"] for a in found] == ["forced"] * 4, found
        statuses = [(a["status"], a["label"]) for a in found]
        assert statuses == [("held", "complete")] * 3 + [("not_held", "complete")]
        assert found[0]["condition"] == json.loads(files[0].read_text()), found[0]
        assert all(a["solutions"] == [] for a in found[:3]), found

        broken = found[3]
        assert broken["solutions"] == [{"c0": 1, "c1": 3, "c2": 2}], broken
        image = Image.open(out / broken["picture"]).convert("RGB")
        assert ring(image, 2) == MARK_COLOR, "the condition's cell is ringed"
        assert ring(image, 0) == ring(image, 1) == WHITE, "no other cell is"

        last = r.stdout.strip().splitlines()[-1]
        pictures = " ".join(str(out / a["picture"]) for a in found)
        assert last == f"pictures: {pictures}", last


def test_forced_time_limit_is_capped():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[])
        cond = condition(tmp, "c", {"gt": ["c0", 0]})
        r = cli(
            b, out, "forced", extra=["--condition", str(cond), "--time-limit", "1e-9"]
        )
        assert r.returncode == 0, r.stderr
        (answer,) = answers(out)
        assert (answer["status"], answer["label"]) == ("timeout", "capped"), answer
        assert (out / answer["picture"]).is_file(), answer


def test_forced_refusals():
    with tempfile.TemporaryDirectory() as tmp:
        b = board(tmp, width=3, clues=[])
        r = cli(b, Path(tmp) / "none", "forced")
        assert r.returncode == 2, r.stderr
        assert "forced needs --condition or --marks" in r.stderr, r.stderr

        r = cli(b, Path(tmp) / "unused", "unique", extra=["--condition", str(b)])
        assert r.returncode == 2, r.stderr
        assert "--condition and --marks need the forced question" in r.stderr

        bad = condition(tmp, "bad", {"eq": ["c9", 1]})
        r = cli(b, Path(tmp) / "key", "forced", extra=["--condition", str(bad)])
        assert r.returncode == 2 and "no variable 'c9'" in r.stderr, r.stderr

        bad = condition(tmp, "kind", {"lt": ["c0", 1]})
        r = cli(b, Path(tmp) / "kind", "forced", extra=["--condition", str(bad)])
        assert r.returncode == 2 and "unknown condition" in r.stderr, r.stderr

        marks = condition(tmp, "marks", [{"kind": "digit", "cell": "r1c1", "digit": 1}])
        r = cli(b, Path(tmp) / "marks", "forced", extra=["--marks", str(marks)])
        assert r.returncode == 2, r.stderr
        assert "has no mark hook" in r.stderr, r.stderr
        assert not (Path(tmp) / "key").exists(), "a refused run writes nothing"


def test_refusals():
    with tempfile.TemporaryDirectory() as tmp:
        b = board(tmp, width=3, clues=[])
        r = cli(b, Path(tmp) / "out", "sideways")
        assert r.returncode == 2 and "sideways" in r.stderr, r.stderr
        r = cli(b, Path(tmp) / "out2", "unique", extra=["--time-limit", "0"])
        assert r.returncode == 2 and "time-limit" in r.stderr, r.stderr


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"ok: {test.__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

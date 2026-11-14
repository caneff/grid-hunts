"""The board-question driver's own suite (spec #65, #94, #95), on the toy
finder.

Drives `query.py` as a subprocess on `toy_finder.py` (one row of distinct
digits) and asserts what lands in the output directory: each answer's
`answers.jsonl` line and label, its picture, and the last printed line. The
forced-mark tests drive the conditions helper through condition files. The
max tests climb boards whose largest value is known by hand.

    uv run finders/query/test_query.py
"""

import contextlib
import io
import json
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ortools.sat.python import cp_model
from PIL import Image

HERE = Path(__file__).resolve().parent
QUERY = HERE / "query.py"
TOY = HERE / "toy_finder.py"
sys.path.insert(0, str(HERE))
import query
from query import CAPTION_HEIGHT, CELL, MARGIN, MARK_COLOR, MARK_RADIUS

WHITE = (255, 255, 255)


def board(tmp, **fields):
    path = Path(tmp) / "board.json"
    path.write_text(json.dumps(fields))
    return path


def argv(board_path, out, questions, extra):
    return [
        sys.executable,
        str(QUERY),
        str(TOY),
        str(board_path),
        *questions,
        "--out",
        str(out),
        *extra,
    ]


def cli(board_path, out, *questions, extra=()):
    return subprocess.run(
        argv(board_path, out, questions, extra),
        capture_output=True,
        text=True,
        check=False,
    )


def start(board_path, out, *questions, extra=()):
    return subprocess.Popen(
        argv(board_path, out, questions, extra),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def wait_for_lines(out, k, deadline_s=30):
    lines = out / "answers.jsonl"
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        if lines.is_file() and len(lines.read_text().splitlines()) >= k:
            return
        time.sleep(0.05)
    raise AssertionError(f"{lines} did not reach {k} line(s) in {deadline_s} s")


def answers(out):
    return [
        json.loads(line) for line in (out / "answers.jsonl").read_text().splitlines()
    ]


def corner(image, board_index, col):
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
        infeasible = answers(out)
        assert len(infeasible) == 2, infeasible  # feasible and unique, one line each
        for answer in infeasible:
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
        capped = answers(out)
        assert len(capped) == 2, capped  # feasible and unique, one line each
        for answer in capped:
            assert answer["status"] == "timeout", answer
            assert answer["label"] == "capped", answer
            assert (out / answer["picture"]).is_file(), answer


def test_killed_run_keeps_answers_found():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[[0, 1]], hold_after_builds=1)
        proc = start(b, out, "feasible", "unique")
        wait_for_lines(out, 1)
        assert proc.poll() is None, "the run ended before the kill"
        proc.send_signal(signal.SIGKILL)
        proc.wait()
        (feasible,) = answers(out)
        assert feasible["question"] == "feasible" and feasible["label"] == "complete"
        assert (out / feasible["picture"]).is_file(), feasible


def test_a_failed_mint_is_recorded_and_the_run_goes_on():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[[0, 1]], mint_fails=True)
        r = cli(b, out, "feasible", "unique")
        assert r.returncode == 0, r.stderr
        found = answers(out)
        assert [(a["question"], a["status"]) for a in found] == [
            ("feasible", "feasible"),
            ("unique", "not_unique"),
        ], found
        for a in found:
            assert "links" not in a, a
            assert "mint refused: the toy's injected failure" in a["link_error"], a
            assert (out / a["picture"]).is_file(), a
        assert "mint refused" in r.stderr, r.stderr
        assert r.stdout.strip().splitlines()[-1].startswith("pictures: "), r.stdout


def test_a_failed_picture_save_leaves_no_partial_file():
    """The picture's save dies after writing part of the file: the run stops
    with that error, and the output directory holds no half picture and no
    `.partial` or `.tmp` file."""
    real_save = Image.Image.save

    def dying_save(self, fp, *args, **kwargs):
        Path(fp).write_bytes(b"half a picture")
        raise OSError("disk full")

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[[0, 1]])
        Image.Image.save = dying_save
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    query.main([str(TOY), str(b), "feasible", "--out", str(out)])
                except OSError as error:
                    assert "disk full" in str(error), error
                else:
                    raise AssertionError("the failed save was swallowed")
        finally:
            Image.Image.save = real_save
        left = sorted(p.name for p in out.iterdir())
        assert not [n for n in left if "partial" in n or n.endswith(".tmp")], left
        assert not [n for n in left if n.endswith(".png")], left


def condition(tmp, name, cond):
    path = Path(tmp) / f"{name}.json"
    path.write_text(json.dumps(cond))
    return path


def ring(image, col):
    x = MARGIN + col * CELL + CELL // 2 - round(MARK_RADIUS * CELL) + 1
    return image.getpixel((x, MARGIN + CELL // 2))


def test_forced_conditions():
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
        refused = []

        def refuse(name, *question, extra=()):
            out = Path(tmp) / name
            refused.append(out)
            return cli(b, out, *question, extra=list(extra))

        r = refuse("none", "forced")
        assert r.returncode == 2, r.stderr
        assert "forced needs --condition or --marks" in r.stderr, r.stderr

        r = refuse("unused", "unique", extra=["--condition", str(b)])
        assert r.returncode == 2, r.stderr
        assert "--condition and --marks need the forced question" in r.stderr

        bad = condition(tmp, "bad", {"eq": ["c9", 1]})
        r = refuse("key", "forced", extra=["--condition", str(bad)])
        assert r.returncode == 2 and "no variable 'c9'" in r.stderr, r.stderr

        bad = condition(tmp, "kind", {"lt": ["c0", 1]})
        r = refuse("kind", "forced", extra=["--condition", str(bad)])
        assert r.returncode == 2 and "unknown condition" in r.stderr, r.stderr

        marks = condition(tmp, "marks", [{"kind": "digit", "cell": "r1c1", "digit": 1}])
        r = refuse("marks", "forced", extra=["--marks", str(marks)])
        assert r.returncode == 2, r.stderr
        assert "has no mark hook" in r.stderr, r.stderr

        assert len(refused) == 5, refused
        written = [out.name for out in refused if out.exists()]
        assert not written, f"a refused run wrote its --out: {written}"


def test_enumerate_lists_every_solution_then_complete():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        r = cli(board(tmp, width=3, clues=[[0, 1]]), out, "enumerate")
        assert r.returncode == 0, r.stderr
        *found, end = answers(out)
        assert [(a["status"], a["label"]) for a in found] == [
            ("solution", "complete")
        ] * 2, found
        rows = sorted(
            tuple(a["solutions"][0][f"c{i}"] for i in range(3)) for a in found
        )
        assert rows == [(1, 2, 3), (1, 3, 2)], rows
        assert (end["status"], end["label"], end["count"]) == (
            "exhausted",
            "complete",
            2,
        )
        assert end["solutions"] == [], end
        assert all((out / a["picture"]).is_file() for a in (*found, end))
        last = r.stdout.strip().splitlines()[-1]
        pictures = " ".join(str(out / a["picture"]) for a in (*found, end))
        assert last == f"pictures: {pictures}", last


def test_enumerate_at_its_cap_is_capped():
    with tempfile.TemporaryDirectory() as tmp:
        b = board(tmp, width=4, clues=[])
        for limit, extra in ((10, ()), (3, ("--limit", "3"))):
            out = Path(tmp) / f"out{limit}"
            r = cli(b, out, "enumerate", extra=extra)
            assert r.returncode == 0, r.stderr
            *found, end = answers(out)
            assert [a["status"] for a in found] == ["solution"] * limit, found
            rows = {tuple(a["solutions"][0].values()) for a in found}
            assert len(rows) == limit, "each solution once"
            assert (end["status"], end["label"]) == ("limit", "capped"), end
            assert end["count"] == limit, end

        out = Path(tmp) / "exact"
        r = cli(
            board(tmp, width=3, clues=[[0, 1]]),
            out,
            "enumerate",
            extra=["--limit", "2"],
        )
        assert r.returncode == 0, r.stderr
        *found, end = answers(out)
        assert len(found) == 2 and (end["status"], end["label"]) == ("limit", "capped")


def test_enumerate_time_limit_is_capped():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[])
        r = cli(b, out, "enumerate", extra=["--time-limit", "1e-9"])
        assert r.returncode == 0, r.stderr
        (end,) = answers(out)
        assert (end["status"], end["label"], end["count"]) == ("timeout", "capped", 0)


def test_enumerate_writes_each_solution_as_found():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[[0, 1]], hold_after_builds=1)
        proc = start(b, out, "enumerate")
        wait_for_lines(out, 1)
        assert proc.poll() is None, "the run ended before the kill"
        proc.send_signal(signal.SIGKILL)
        proc.wait()
        assert (out / "answers.jsonl").is_file(), "no solution on disk before the kill"
        (first,) = answers(out)
        assert (first["status"], first["label"]) == ("solution", "complete"), first
        assert (out / first["picture"]).is_file(), first


def caption_strip(image):
    return image.crop((0, image.height - CAPTION_HEIGHT, image.width, image.height))


def test_max_climbs_to_the_true_maximum():
    """A row of 4 with c3 = 4: each of c0, c1, c2 reaches 3 and no higher.
    One solution puts 1, 2 and 3 in c0..c2, so a run that stops at its
    first solve gets 3 on at most one of them. Each improving witness is a
    capped answer as it is found; the closing answer is complete, with a
    witness that reaches the maximum, drawn with the value in a caption
    below the board."""
    with tempfile.TemporaryDirectory() as tmp:
        b = board(tmp, width=4, clues=[[3, 4]])
        for key in ("c0", "c1", "c2"):
            out = Path(tmp) / key
            r = cli(b, out, "max", extra=["--max", key])
            assert r.returncode == 0, r.stderr
            *climbed, answer = answers(out)
            assert climbed, "no witness written on the way up"
            assert {(a["status"], a["label"]) for a in climbed} == {
                ("witness", "capped")
            }, climbed
            values = [a["value"] for a in climbed]
            assert values == sorted(set(values)) and values[-1] == 3, values
            assert (answer["status"], answer["label"]) == ("max", "complete"), answer
            assert (answer["key"], answer["value"]) == (key, 3), answer
            (witness,) = answer["solutions"]
            assert witness[key] == 3 and witness["c3"] == 4, witness
            assert f"{key} = 3" in r.stdout, r.stdout
            last = r.stdout.strip().splitlines()[-1]
            first = last.removeprefix("pictures: ").split()[0]
            assert first == str(out / answer["picture"]), last

        image = Image.open(out / answer["picture"]).convert("RGB")
        board_height = CELL + 2 * MARGIN
        assert image.height == board_height + CAPTION_HEIGHT, image.size
        colors = {c for _, c in caption_strip(image).getcolors(1 << 20)}
        assert colors != {WHITE}, "the caption strip carries text"


def test_max_time_limit_is_capped():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=4, clues=[])
        r = cli(b, out, "max", extra=["--max", "c0", "--time-limit", "1e-9"])
        assert r.returncode == 0, r.stderr
        (answer,) = answers(out)
        assert (answer["status"], answer["label"]) == ("timeout", "capped"), answer
        assert (out / answer["picture"]).is_file(), answer


def test_max_writes_each_witness_as_found():
    """The first build checks `--max`, so the hold starts after two builds."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=4, clues=[[3, 4]], hold_after_builds=2)
        proc = start(b, out, "max", extra=["--max", "c0"])
        wait_for_lines(out, 1)
        assert proc.poll() is None, "the run ended before the kill"
        proc.send_signal(signal.SIGKILL)
        proc.wait()
        (first,) = answers(out)
        assert (first["status"], first["label"]) == ("witness", "capped"), first
        assert first["value"] == first["solutions"][0]["c0"], first
        assert (out / first["picture"]).is_file(), first


def test_max_timeout_after_a_best_is_capped():
    real_solve = query.solve
    calls = []

    def solve_then_time_out(question, model, variables, time_limit):
        calls.append(question)
        if len(calls) > 1:
            return "timeout", []
        return real_solve(question, model, variables, time_limit)

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=4, clues=[[3, 4]])
        query.solve = solve_then_time_out
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                assert (
                    query.main(
                        [str(TOY), str(b), "max", "--max", "c0", "--out", str(out)]
                    )
                    == 0
                )
        finally:
            query.solve = real_solve
        witness, end = answers(out)
        assert (witness["status"], witness["label"]) == ("witness", "capped")
        assert (end["status"], end["label"]) == ("timeout", "capped"), end
        assert end["value"] == witness["value"] is not None, (witness, end)
        assert end["solutions"] == witness["solutions"], end


def test_max_on_an_infeasible_board():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[[0, 1], [1, 1]])
        r = cli(b, out, "max", extra=["--max", "c2"])
        assert r.returncode == 0, r.stderr
        (answer,) = answers(out)
        assert (answer["status"], answer["label"]) == ("infeasible", "complete")
        assert answer["value"] is None and answer["solutions"] == [], answer


def test_enumerate_and_max_refusals():
    with tempfile.TemporaryDirectory() as tmp:
        b = board(tmp, width=3, clues=[])
        r = cli(b, Path(tmp) / "a", "max")
        assert r.returncode == 2 and "max needs --max" in r.stderr, r.stderr
        r = cli(b, Path(tmp) / "b", "unique", extra=["--max", "c0"])
        assert r.returncode == 2 and "--max needs the max question" in r.stderr
        r = cli(b, Path(tmp) / "c", "max", extra=["--max", "c9"])
        assert r.returncode == 2 and "no variable 'c9'" in r.stderr, r.stderr
        r = cli(b, Path(tmp) / "d", "enumerate", extra=["--limit", "0"])
        assert r.returncode == 2 and "--limit must be at least 1" in r.stderr
        r = cli(b, Path(tmp) / "e", "unique", extra=["--limit", "3"])
        assert r.returncode == 2 and "--limit needs the enumerate question" in r.stderr
        assert not any((Path(tmp) / x).exists() for x in "abcde")


def test_drop_one_names_the_droppable_clues():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[[0, 1], [1, 2], [0, 1]])
        r = cli(b, out, "drop-one")
        assert r.returncode == 0, r.stderr
        *per_clue, end = answers(out)
        assert [(a["clue"], a["status"], a["label"]) for a in per_clue] == [
            (0, "droppable", "complete"),
            (1, "needed", "complete"),
            (2, "droppable", "complete"),
        ], per_clue
        assert all(a["question"] == "drop-one" for a in [*per_clue, end])
        assert all((out / a["picture"]).is_file() for a in per_clue), per_clue
        assert (end["status"], end["label"]) == ("done", "complete"), end
        assert (end["droppable"], end["capped"]) == ([0, 2], []), end
        assert "droppable: 0, 2" in r.stdout, r.stdout
        last = r.stdout.strip().splitlines()[-1]
        rest = " ".join(str(out / a["picture"]) for a in per_clue)
        assert last == f"pictures: {out / end['picture']} {rest}", last

        image = Image.open(out / end["picture"]).convert("RGB")
        assert corner(image, 0, 0) != WHITE, "the droppable clue's cell is plain"
        assert corner(image, 0, 1) == WHITE, "the needed clue's cell is coloured"
        assert corner(image, 0, 2) == WHITE, "a cell with no clue is coloured"


def test_drop_one_time_limit_is_capped():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[[0, 1], [1, 2], [0, 1]])
        r = cli(b, out, "drop-one", extra=["--time-limit", "1e-9"])
        assert r.returncode == 0, r.stderr
        *per_clue, end = answers(out)
        assert [(a["status"], a["label"]) for a in per_clue] == [
            ("timeout", "capped")
        ] * 3, per_clue
        assert (end["status"], end["label"]) == ("timeout", "capped"), end
        assert (end["droppable"], end["capped"]) == ([], [0, 1, 2]), end
        image = Image.open(out / end["picture"]).convert("RGB")
        assert corner(image, 0, 0) == WHITE, "a capped clue is drawn droppable"


def test_drop_one_writes_each_clue_as_found():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[[0, 1], [1, 2]], hold_after_builds=1)
        proc = start(b, out, "drop-one")
        wait_for_lines(out, 1)
        assert proc.poll() is None, "the run ended before the kill"
        proc.send_signal(signal.SIGKILL)
        proc.wait()
        assert (out / "answers.jsonl").is_file(), "no clue on disk before the kill"
        (first,) = answers(out)
        assert (first["clue"], first["status"]) == (0, "needed"), first
        assert (out / first["picture"]).is_file(), first


def test_refusals():
    with tempfile.TemporaryDirectory() as tmp:
        b = board(tmp, width=3, clues=[])
        r = cli(b, Path(tmp) / "out", "sideways")
        assert r.returncode == 2 and "invalid choice: 'sideways'" in r.stderr
        r = cli(b, Path(tmp) / "out2", "unique", extra=["--time-limit", "0"])
        assert r.returncode == 2, r.stderr
        assert "--time-limit must be above 0" in r.stderr, r.stderr


def test_an_out_already_answered_is_refused():
    """A second run into the same --out would append to the first run's
    answers.jsonl and overwrite the pictures its lines name: refused, the
    first run's answers left as they were."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        b = board(tmp, width=3, clues=[[0, 1]])
        assert cli(b, out, "feasible").returncode == 0
        before = (out / "answers.jsonl").read_text()
        r = cli(b, out, "unique")
        assert r.returncode == 2, r.stderr
        assert "answers.jsonl exists: give a fresh --out" in r.stderr, r.stderr
        assert (out / "answers.jsonl").read_text() == before


def test_unique_on_an_invalid_model_raises():
    model = cp_model.CpModel()
    x = model.NewIntVar(0, 5, "x")
    model.proto.constraints.add().linear.vars.append(99)
    try:
        query.unique_on(model, {"x": x}, 1.0)
    except ValueError as error:
        assert "invalid" in str(error), error
    else:
        raise AssertionError("an invalid model gave a status")


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"ok: {test.__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

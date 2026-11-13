"""Forced marks on Chris's halver + between board end to end (spec #65, #95).

Runs `finders/query/query.py halver_between board.json forced` as a
subprocess, minting offline (`short_link.fake_mint`), and asserts what lands
in the output directory:

- `--marks marks.json`: all 23 of Chris's marks `held`, complete, the
  verdicts `report.py` gives;
- `--marks` of five more marks, one per kind, and a `--condition` file:
  the marks' verdicts match the recorded list `MORE_MARKS`, and each
  counterexample breaks its mark read in plain Python, is a valid solution,
  has the mark's cells ringed in its picture, and its short link rebuilds
  to the board with the counterexample entered;
- a tiny time limit: every answer capped, never held;
- a malformed marks file (not a list, an entry missing a field, not JSON)
  is refused, naming the file and the reason, and nothing is written.

WHAT A GREEN RUN DOES NOT COVER: whether the picture reads well to Chris.

    uv run finders/halver_between/test_forced_e2e.py
"""

import json
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
MARKS = HERE / "marks.json"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "query"))

import rules
import test_query_e2e as e2e

# isort: split
from query import CELL, MARGIN, MARK_COLOR, MARK_RADIUS

# One mark per kind, with its verdict on board.json as `report.py` gives it
# (re-derived by the spec #65 review).
MORE_MARKS = [
    ({"kind": "digit", "cell": "r1c1", "digit": 1}, "not_held"),
    ({"kind": "halver", "cell": "r5c5"}, "not_held"),
    ({"kind": "halver_digit_in", "cells": ["r1c1", "r1c2"], "digit": 1}, "not_held"),
    ({"kind": "candidates", "cell": "r9c4", "digits": [2]}, "not_held"),
    ({"kind": "digit_in", "cells": ["r8c4", "r8c5"], "digit": 1}, "held"),
]
CONDITION = {"any": [{"eq": ["r5c5", 5]}, {"gt": ["h_r5c5", 0]}]}


def run(out, *extra):
    return e2e.run(out, *extra, questions=("forced",))


def mark_reads(mark, solution):
    """Whether `solution` (a `rules.Solution`) agrees with `mark`."""

    def digit(name):
        r, c = rules.parse_cell(name)
        return solution.digits[r][c]

    cells = mark.get("cells", [mark.get("cell")])
    kind = mark["kind"]
    if kind == "digit":
        return digit(mark["cell"]) == mark["digit"]
    if kind == "candidates":
        return digit(mark["cell"]) in mark["digits"]
    if kind == "digit_in":
        return any(digit(c) == mark["digit"] for c in cells)
    if kind == "halver":
        return rules.parse_cell(mark["cell"]) in solution.halvers
    if kind == "halver_digit_in":
        return any(
            rules.parse_cell(c) in solution.halvers and digit(c) == mark["digit"]
            for c in cells
        )
    raise ValueError(kind)


def ring(image, cell):
    """A pixel on the left of the mark ring of `cell`: off its digit."""
    r, c = cell
    x = MARGIN + c * CELL + CELL // 2 - round(MARK_RADIUS * CELL) + 1
    return image.getpixel((x, MARGIN + r * CELL + CELL // 2))


def main():
    lines = rules.load_lines(e2e.BOARD)
    marks = json.loads(MARKS.read_text())
    assert len(marks) == 23, len(marks)
    with tempfile.TemporaryDirectory() as tmp, e2e.short_link.fake_mint() as fake:
        out = Path(tmp) / "marks"
        r = run(out, "--marks", str(MARKS))
        assert r.returncode == 0, r.stderr
        found = e2e.answers(out)
        assert [a["mark"] for a in found] == marks, found
        verdicts = [(a["status"], a["label"]) for a in found]
        assert verdicts == [("held", "complete")] * 23, verdicts
        print("ok: all 23 of Chris's marks held, complete, as the recorded list says")

        more = Path(tmp) / "more.json"
        more.write_text(json.dumps([mark for mark, _ in MORE_MARKS]))
        condition = Path(tmp) / "condition.json"
        condition.write_text(json.dumps(CONDITION))
        out = Path(tmp) / "more"
        r = run(out, "--condition", str(condition), "--marks", str(more))
        assert r.returncode == 0, r.stderr
        cond_answer, *found = e2e.answers(out)
        assert cond_answer["condition"] == CONDITION, cond_answer
        assert "mark" not in cond_answer, cond_answer
        assert (cond_answer["status"], cond_answer["label"]) == (
            "not_held",
            "complete",
        ), cond_answer
        assert [a["mark"] for a in found] == [mark for mark, _ in MORE_MARKS]
        assert [a["status"] for a in found] == [v for _, v in MORE_MARKS], found
        assert all(a["label"] == "complete" for a in found), found

        for answer in [cond_answer, *found]:
            image = Image.open(out / answer["picture"]).convert("RGB")
            links = e2e.links_of(out, answer, fake)
            mark = answer.get("mark")
            cells = (
                [rules.parse_cell("r5c5")]
                if mark is None
                else [
                    rules.parse_cell(c) for c in mark.get("cells", [mark.get("cell")])
                ]
            )
            assert all(ring(image, x) == MARK_COLOR for x in cells), answer
            if answer["status"] == "held":
                assert answer["solutions"] == [], answer
                assert links == [e2e.board_with(None)], answer
                continue
            (values,) = answer["solutions"]
            solution = e2e.as_solution(values)
            assert e2e.is_valid(solution, lines), answer
            if mark is None:
                assert values["r5c5"] != 5 and not values["h_r5c5"], values
            else:
                assert not mark_reads(mark, solution), (mark, values)
            assert links == [e2e.board_with(values)], answer
        print("ok: each counterexample breaks its mark, ringed, with its link")

        out = Path(tmp) / "capped"
        r = run(out, "--marks", str(more), "--time-limit", "1e-9")
        assert r.returncode == 0, r.stderr
        capped = e2e.answers(out)
        assert len(capped) == len(MORE_MARKS), capped
        for answer in capped:
            assert (answer["status"], answer["label"]) == ("timeout", "capped"), answer
            assert (out / answer["picture"]).is_file(), answer
        print("ok: a tiny time limit gives capped answers, never held")

        for name, text, reason in (
            ("object", json.dumps(MORE_MARKS[0][0]), "not a list of marks"),
            ("field", json.dumps([{"kind": "digit"}]), "mark 0 has no 'cell'"),
            ("entry", json.dumps(["r1c1"]), "mark 0 is not an object"),
            ("syntax", "[{", "Expecting"),
        ):
            bad = Path(tmp) / f"{name}.json"
            bad.write_text(text)
            out = Path(tmp) / f"refused-{name}"
            r = run(out, "--marks", str(bad))
            assert r.returncode == 2, (name, r.stderr)
            assert f"{bad}: " in r.stderr and reason in r.stderr, (name, r.stderr)
            assert "Traceback" not in r.stderr, r.stderr
            assert not out.exists(), out
        print("ok: a malformed marks file is refused, naming the file and reason")
    return 0


if __name__ == "__main__":
    sys.exit(main())

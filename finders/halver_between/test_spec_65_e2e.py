"""Spec #65 end to end: one `query.py` run asks Chris's halver + between board
all six board questions.

WHAT A GREEN RUN DOES NOT COVER (`AGENTS.md` § End-to-end seam, Blind to):
the slow tests (`just test-slow`: the halver/between and halver/lockout
hunts, the lockout 23-line board, the five slowest U-Bahn suites and the
Doppelganger rank 9x9 hunt), a hunt's own output, and how a found grid reads
once it is built into a puzzle link.

Runs `finders/query/query.py halver_between board.json feasible unique
forced enumerate max drop-one` as one subprocess, minting offline
(`short_link.fake_mint`), and asserts each `answers.jsonl` line's question,
status and label in order, that each picture exists, that each link decodes
to the board with the answer's solution entered, and that the last line
names max's closing picture first. What each question finds is asserted in
its own suite: `test_query_e2e.py` (feasible, unique, enumerate),
`test_forced_e2e.py` (forced), `test_drop_one_e2e.py` (drop-one) and
`finders/query/test_query.py` (every question on the toy finder); this test
only proves they run together, through one entry, into one directory.

    uv run finders/halver_between/test_spec_65_e2e.py
"""

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import test_query_e2e as e2e

MARKS = [
    {"kind": "digit_in", "cells": ["r8c4", "r8c5"], "digit": 1},
    {"kind": "digit", "cell": "r1c1", "digit": 1},
]
QUESTIONS = ("feasible", "unique", "forced", "enumerate", "max", "drop-one")


def main():
    lines = e2e.rules.load_lines(e2e.BOARD)
    with tempfile.TemporaryDirectory() as tmp, e2e.short_link.fake_mint() as fake:
        marks = Path(tmp) / "marks.json"
        marks.write_text(json.dumps(MARKS))
        out = Path(tmp) / "out"
        r = e2e.run(
            out,
            "--marks",
            str(marks),
            "--limit",
            "2",
            "--max",
            "r1c1",
            questions=QUESTIONS,
        )
        assert r.returncode == 0, r.stderr
        found = e2e.answers(out)
        by_question = {q: [a for a in found if a["question"] == q] for q in QUESTIONS}
        assert [a["question"] for a in found] == [
            q for q in QUESTIONS for _ in by_question[q]
        ], "answers out of question order"

        def shape(question):
            return [(a["status"], a["label"]) for a in by_question[question]]

        assert shape("feasible") == [("feasible", "complete")]
        assert shape("unique") == [("not_unique", "complete")]
        assert shape("forced") == [("held", "complete"), ("not_held", "complete")]
        assert shape("enumerate") == [("solution", "complete")] * 2 + [
            ("limit", "capped")
        ]
        *climbed, best = by_question["max"]
        assert climbed and {(a["status"], a["label"]) for a in climbed} == {
            ("witness", "capped")
        }, climbed
        assert (best["status"], best["label"]) == ("max", "complete"), best
        assert best["value"] == climbed[-1]["value"] == best["solutions"][0]["r1c1"]
        *per_line, closing = by_question["drop-one"]
        assert len(per_line) == len(lines), per_line
        assert {a["label"] for a in per_line} == {"complete"}, per_line
        assert (closing["status"], closing["label"]) == ("done", "complete")
        print("ok: all six questions answered, each line labelled, in order")

        for a in found:
            assert (out / a["picture"]).is_file(), a
            entered = a["solutions"] or [None]
            expected = [e2e.board_with(s) for s in entered]
            assert e2e.links_of(out, a, fake) == expected, a
        for s in [*by_question["feasible"], *by_question["enumerate"][:2]]:
            assert e2e.is_valid(e2e.as_solution(s["solutions"][0]), lines), s
        print("ok: every answer has its picture and a link that decodes to it")

        last = r.stdout.strip().splitlines()[-1]
        shown = last.removeprefix("pictures: ").split()
        assert shown[0] == str(out / best["picture"]), last
        assert sorted(shown) == sorted(str(out / a["picture"]) for a in found)
        print("ok: the last line names every picture, max's closing one first")
    return 0


if __name__ == "__main__":
    sys.exit(main())

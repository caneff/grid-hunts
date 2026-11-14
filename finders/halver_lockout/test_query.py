"""The lockout finder on the board-question driver (spec #65, #94): `unique`
on the unique and not-unique fixtures through `finders/query/query.py`, and
a board `check.py` refuses is refused here too. Each link is the hunt's
`link_doc` of the board's lines with the solution entered, whatever else the
board file carries: a board saved without `"solverIgnored"` still links to
one SudokuMaker leaves out of its own checking.

    uv run finders/halver_lockout/test_query.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUERY = HERE.parent / "query" / "query.py"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))

import short_link
from sudoku_kit.link_codec import SHORT_LINK


def ask(board, out):
    return subprocess.run(
        [
            sys.executable,
            str(QUERY),
            "halver_lockout",
            str(board),
            "unique",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def main():
    with tempfile.TemporaryDirectory() as tmp, short_link.fake_mint() as fake:
        for name, status, count in (
            ("unique", "unique", 1),
            ("not_unique", "not_unique", 2),
        ):
            out = Path(tmp) / name
            r = ask(HERE / "fixtures" / f"{name}.json", out)
            assert r.returncode == 0, r.stderr
            (answer,) = [
                json.loads(x) for x in (out / "answers.jsonl").read_text().splitlines()
            ]
            assert (answer["status"], answer["label"]) == (status, "complete"), answer
            assert len(answer["solutions"]) == count, answer
            assert (out / answer["picture"]).is_file(), answer
            links = (out / answer["links"]).read_text().split()
            assert len(links) == count and all(SHORT_LINK.fullmatch(x) for x in links)
            print(f"ok: {name}.json is {status}, complete, with {count} link(s)")

        plain = json.loads((HERE / "fixtures" / "unique.json").read_text())
        for constraint in plain["puzzle"]["constraints"]:
            constraint.pop("solverIgnored", None)
        board = Path(tmp) / "plain.json"
        board.write_text(json.dumps(plain))
        out = Path(tmp) / "plain"
        r = ask(board, out)
        assert r.returncode == 0, r.stderr
        (answer,) = [
            json.loads(x) for x in (out / "answers.jsonl").read_text().splitlines()
        ]
        (solution,) = answer["solutions"]
        # Built from the fixture's own file, not from `hunt.link_doc`: its
        # constraints as saved (the lines solver-ignored), cells empty but for
        # the solution.
        saved = json.loads((HERE / "fixtures" / "unique.json").read_text())
        expected = {
            "formatVersion": saved["formatVersion"],
            "puzzle": {
                "name": "",
                "author": "",
                "cells": [
                    {"value": solution[f"r{i // 9 + 1}c{i % 9 + 1}"]} for i in range(81)
                ],
                "constraints": saved["puzzle"]["constraints"],
            },
        }
        (link,) = (out / answer["links"]).read_text().split()
        assert short_link.fake_doc(fake, link) == expected, link
        print("ok: the link is the board file's own document with the solution entered")

        bad = json.loads((HERE / "fixtures" / "unique.json").read_text())
        bad["puzzle"]["cells"][0] = {"value": 5, "given": True}
        board = Path(tmp) / "given.json"
        board.write_text(json.dumps(bad))
        r = ask(board, Path(tmp) / "given")
        assert r.returncode == 2, (r.returncode, r.stderr)
        assert r.stderr.splitlines()[-1] == "query.py: error: given digit in r1c1", (
            r.stderr
        )
        assert not (Path(tmp) / "given").exists(), "a refused board writes nothing"
        print("ok: a board check.py refuses is refused")
    return 0


if __name__ == "__main__":
    sys.exit(main())

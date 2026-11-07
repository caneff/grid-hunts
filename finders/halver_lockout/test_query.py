"""The lockout finder on the board-question driver (spec #65, #94): `unique`
on the unique and not-unique fixtures through `finders/query/query.py`, and
a board `check.py` refuses is refused here too.

    uv run finders/halver_lockout/test_query.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUERY = HERE.parent / "query" / "query.py"
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
    with tempfile.TemporaryDirectory() as tmp, short_link.fake_mint():
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

        bad = json.loads((HERE / "fixtures" / "unique.json").read_text())
        bad["puzzle"]["cells"][0] = {"value": 5, "given": True}
        board = Path(tmp) / "given.json"
        board.write_text(json.dumps(bad))
        r = ask(board, Path(tmp) / "given")
        assert r.returncode != 0 and "given digit in r1c1" in r.stderr, r.stderr
        print("ok: a board check.py refuses is refused")
    return 0


if __name__ == "__main__":
    sys.exit(main())

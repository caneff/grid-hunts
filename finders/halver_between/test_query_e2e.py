"""Board questions on Chris's halver + between board end to end (spec #65, #94).

Runs `finders/query/query.py halver_between board.json feasible unique` as a
subprocess, minting offline (`short_link.fake_mint`), with every image viewer
on PATH replaced by one that records being called, and asserts what lands in
the output directory: each answer's line and label, two solutions that obey
every line with the differing cells shaded, the short links rebuilt to the
board with each solution entered, and no window opened. A tiny time limit
gives capped answers.

WHAT A GREEN RUN DOES NOT COVER: how a link reads once opened in
sudokumaker.app, and whether the picture reads well to Chris.

    uv run finders/halver_between/test_query_e2e.py
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
QUERY = HERE.parent / "query" / "query.py"
BOARD = HERE / "board.json"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
sys.path.insert(0, str(HERE.parent / "query"))

import rules

# isort: split
import short_link
from query import CELL, MARGIN
from sudoku_kit.link_codec import SHORT_LINK

WHITE = (255, 255, 255)
VIEWERS = ("xdg-open", "display", "eog", "feh", "wslview", "explorer.exe", "open")


def run(out, *extra, fake_bin):
    env = {
        k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")
    }
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        [
            sys.executable,
            str(QUERY),
            "halver_between",
            str(BOARD),
            "feasible",
            "unique",
            "--out",
            str(out),
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def fake_viewers(tmp):
    """A bin directory whose every viewer appends its name to `opened`."""
    fake_bin = Path(tmp) / "bin"
    fake_bin.mkdir()
    opened = Path(tmp) / "opened"
    for name in VIEWERS:
        script = fake_bin / name
        script.write_text(f"#!/bin/sh\necho {name} >> {opened}\n")
        script.chmod(0o755)
    return fake_bin, opened


def answers(out):
    lines = (out / "answers.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines]


def as_solution(values):
    digits = tuple(
        tuple(values[f"r{r + 1}c{c + 1}"] for c in range(9)) for r in range(9)
    )
    halvers = frozenset(
        (r, c) for r in range(9) for c in range(9) if values[f"h_r{r + 1}c{c + 1}"]
    )
    return rules.Solution(digits, halvers)


def is_valid(solution, lines):
    rows = [set(row) for row in solution.digits]
    cols = [{solution.digits[r][c] for r in range(9)} for c in range(9)]
    full = set(range(1, 10))
    return (
        all(s == full for s in rows + cols)
        and len({solution.digits[r][c] for r, c in solution.halvers}) == 9
        and all(rules.line_holds(solution, line) for line in lines)
    )


def board_with(values):
    """board.json with every cell's entries cleared and, given a solution,
    its digits entered."""
    doc = copy.deepcopy(json.loads(BOARD.read_text()))
    doc["puzzle"]["cells"] = [
        {"value": values[f"r{i // 9 + 1}c{i % 9 + 1}"]} if values else {}
        for i in range(81)
    ]
    return doc


def corner(image, board_index, cell):
    r, c = cell
    board_width = 9 * CELL + 2 * MARGIN
    x = board_index * (board_width + MARGIN) + MARGIN + c * CELL + 6
    return image.getpixel((x, MARGIN + r * CELL + 6))


def links_of(out, answer, fake):
    links = (out / answer["links"]).read_text().split()
    assert all(SHORT_LINK.fullmatch(link) for link in links), links
    return [short_link.fake_doc(fake, link) for link in links]


def main():
    lines = rules.load_lines(BOARD)
    with tempfile.TemporaryDirectory() as tmp, short_link.fake_mint() as fake:
        fake_bin, opened = fake_viewers(tmp)
        out = Path(tmp) / "out"
        r = run(out, fake_bin=fake_bin)
        assert r.returncode == 0, r.stderr
        feasible, unique = answers(out)
        assert (feasible["status"], feasible["label"]) == ("feasible", "complete")
        assert (unique["status"], unique["label"]) == ("not_unique", "complete")
        assert len(feasible["solutions"]) == 1, feasible
        assert is_valid(as_solution(feasible["solutions"][0]), lines)
        first, second = unique["solutions"]
        assert first != second, unique
        assert all(is_valid(as_solution(s), lines) for s in (first, second))
        print("ok: feasible, then not_unique with two valid solutions, complete")

        pictures = [out / a["picture"] for a in (feasible, unique)]
        image = Image.open(pictures[1]).convert("RGB")
        a, b = as_solution(first), as_solution(second)
        cells = [(r, c) for r in range(9) for c in range(9)]
        on_lines = {x for line in lines for x in (line.a, *line.body, line.b)}
        plain = [x for x in cells if x not in a.halvers | b.halvers | on_lines]
        differ = [x for x in plain if a.digits[x[0]][x[1]] != b.digits[x[0]][x[1]]]
        same = [x for x in plain if x not in differ]
        assert differ and same, (differ, same)
        for side in (0, 1):
            assert all(corner(image, side, x) != WHITE for x in differ), "unshaded"
            assert all(corner(image, side, x) == WHITE for x in same), "shaded"
        print("ok: the not_unique picture shades exactly the cells that differ")

        assert links_of(out, feasible, fake) == [board_with(feasible["solutions"][0])]
        assert links_of(out, unique, fake) == [board_with(first), board_with(second)]
        print("ok: each link is a short link of the board with its solution entered")

        last = r.stdout.strip().splitlines()[-1]
        assert last == f"pictures: {pictures[0]} {pictures[1]}", last
        assert all(p.is_file() for p in pictures), pictures
        assert not opened.exists(), opened.read_text()
        print("ok: the last line names the pictures, and no viewer ran")

        out = Path(tmp) / "capped"
        r = run(out, "--time-limit", "1e-9", fake_bin=fake_bin)
        assert r.returncode == 0, r.stderr
        for answer in answers(out):
            assert (answer["status"], answer["label"]) == ("timeout", "capped"), answer
            assert (out / answer["picture"]).is_file(), answer
            assert links_of(out, answer, fake) == [board_with(None)], answer
        print("ok: a tiny time limit gives capped answers, never a verdict")
    return 0


if __name__ == "__main__":
    sys.exit(main())

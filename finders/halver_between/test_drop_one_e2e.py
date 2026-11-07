"""Drop-one on a unique halver + between board end to end (spec #65, #97).

Runs `finders/query/query.py halver_between unique_9x9.json drop-one` as a
subprocess, minting offline (`short_link.fake_mint`), and asserts what lands
in the output directory: one complete answer per line, in order, then a
closing answer naming lines 7, 14 and 15 (counted from 0) as droppable, the
set the prototype of #36 and a direct uniqueness loop agree on; its picture
draws exactly those lines in the second colour. A tiny time limit gives
capped answers and calls no line droppable.

WHAT A GREEN RUN DOES NOT COVER: whether the picture reads well to Chris,
and how the link reads once opened in sudokumaker.app.

    uv run finders/halver_between/test_drop_one_e2e.py
"""

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
QUERY = HERE.parent / "query" / "query.py"
UNIQUE = HERE / "unique_9x9.json"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "halver"))
sys.path.insert(0, str(HERE.parent / "hunt"))
sys.path.insert(0, str(HERE.parent / "query"))

import itertools

import short_link
from halver_query import DROP_COLOR
from halver_rules import parse_cell
from query import CELL, MARGIN
from sudoku_kit.link_codec import SHORT_LINK

DROPPABLE = [7, 14, 15]
STEP = 6  # pixels past a segment's middle
CLEAR = 10  # pixels: twice a line's half width


def run(out, *extra):
    return subprocess.run(
        [
            sys.executable,
            str(QUERY),
            "halver_between",
            str(UNIQUE),
            "drop-one",
            "--out",
            str(out),
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def answers(out):
    lines = (out / "answers.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines]


def centre_of(name):
    r, c = parse_cell(name)
    return MARGIN + c * CELL + CELL / 2, MARGIN + r * CELL + CELL / 2


def distance(p, a, b):
    """From point `p` to the segment from `a` to `b`."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def own_points(names):
    """For each line, the points on its path that no other line comes within
    `CLEAR` pixels of: a step past the middle of each of its segments, off the
    grid lines at the cell edge and outside the end rings."""
    segments = [
        [(centre_of(a), centre_of(b)) for a, b in itertools.pairwise(line)]
        for line in names
    ]
    points = {}
    for i, own in enumerate(segments):
        others = [s for j, segs in enumerate(segments) if j != i for s in segs]
        points[i] = []
        for a, b in own:
            length = math.dist(a, b)
            t = 0.5 + STEP / length
            p = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            if all(distance(p, *s) > CLEAR for s in others):
                points[i].append((round(p[0]), round(p[1])))
    return points


def main():
    names = json.loads(UNIQUE.read_text())
    with tempfile.TemporaryDirectory() as tmp, short_link.fake_mint():
        out = Path(tmp) / "out"
        r = run(out)
        assert r.returncode == 0, r.stderr
        *per_line, end = answers(out)
        assert [a["clue"] for a in per_line] == list(range(len(names))), per_line
        assert all(a["label"] == "complete" for a in per_line), per_line
        assert [a["clue"] for a in per_line if a["status"] == "droppable"] == (
            DROPPABLE
        ), per_line
        assert (end["status"], end["label"]) == ("done", "complete"), end
        assert (end["droppable"], end["capped"]) == (DROPPABLE, []), end
        for a in [*per_line, end]:
            assert (out / a["picture"]).is_file(), a
            links = (out / a["links"]).read_text().split()
            assert links and all(SHORT_LINK.fullmatch(x) for x in links), links
        print("ok: drop-one on unique_9x9.json gives lines 7, 14 and 15, complete")

        image = Image.open(out / end["picture"]).convert("RGB")
        owned = own_points(names)
        assert all(owned.values()), owned
        for i, points in owned.items():
            for point in points:
                drawn = image.getpixel(point) == DROP_COLOR
                assert drawn == (i in DROPPABLE), (i, point, image.getpixel(point))
        assert r.stdout.strip().splitlines()[-1].startswith("pictures: "), r.stdout
        print("ok: the closing picture draws exactly the droppable lines in colour")

        out = Path(tmp) / "capped"
        r = run(out, "--time-limit", "1e-9")
        assert r.returncode == 0, r.stderr
        *per_line, end = answers(out)
        assert {(a["status"], a["label"]) for a in per_line} == {
            ("timeout", "capped")
        }, per_line
        assert (end["status"], end["label"], end["droppable"]) == (
            "timeout",
            "capped",
            [],
        ), end
        print("ok: a tiny time limit labels drop-one capped and drops nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())

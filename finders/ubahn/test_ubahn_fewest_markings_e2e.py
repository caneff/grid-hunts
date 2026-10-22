"""Spec #29 end to end, through the commands Chris runs: `fewest-markings`
with a circle as fixed background, then `verify`, `render` and `links` on
the example it wrote, a rerun, and the refusal on `--engine cpsat`.

One chain on the 4x4 board with r2c4 circled, each step reading the files
the step before wrote. The brute force gives the answer to expect: the
grids with r2c4 a valid circle, each by its checkerboard windows.
`test_ubahn_fewest_markings.py` takes the command's rules one at a time and
`test_ubahn_hybrid_render.py` the picture's; this one is that the spec's
two halves fit together, a ring on the circle that is a condition and none
on the grid's other valid circles in the picture of a `fewest-markings`
example.

Blind to: a hunt's own output on a board above
4x4 (the 7x7 run of record is made by hand), and how a found grid reads once
it is built into a puzzle link. The link is decoded here, not opened:
whether Penpa+ draws the symbols and the circle where they belong is seen
only in a browser (`penpa-browser-check.mjs`, outside the gate). The picture
is read by pixel for its rings and symbols; nothing but an open of the PNG
says it reads cleanly as a puzzle.

One CaDiCaL thread; the circle breaks the reflection so every set is solved.

A slow test, outside the gate: `just test-slow` runs it (tests/all.sh's
`finder_slow`). Its time on one core is in
`docs/research/2026-10-22-ubahn-suite-times.md`.

    uv run finders/ubahn/test_ubahn_fewest_markings_e2e.py
"""

import json
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import brute
import hybrid
import hybrid_finder
import hybrid_render
from cli_checks import check, finish, run_cli
from penpa_decode import Decoded, battenberg_vertices
from verified_io import read_verified

BOARD = ["--rows", "4", "--cols", "4", "--timeout", "20"]
CIRCLE = "r2c4"


def pixels(image, box, colour):
    """How many pixels of a box of the picture are this colour."""
    x0, y0, x1, y1 = box
    return sum(
        image.getpixel((x, y)) == colour for x in range(x0, x1) for y in range(y0, y1)
    )


# The brute force's answer: of the 4x4 grids with the circle valid, each by
# its checkerboard windows, the smallest set of windows only one grid has.
held = {}
for net in brute.hybrid_grids(4, 4):
    board = hybrid.values(net, 4, 4)
    if hybrid.parse_cell(CIRCLE) in hybrid.valid_circles(board):
        held.setdefault(tuple(hybrid.checkerboard_windows(board)), []).append(net)
minimum = min(len(windows) for windows, nets in held.items() if len(nets) == 1)
((windows, (grid,)),) = [
    (windows, nets)
    for windows, nets in held.items()
    if len(windows) == minimum and len(nets) == 1
]
names = [hybrid.cell_name(window) for window in windows]
check(
    f"the brute force has one answer to drive: {minimum} markings, {names}",
    minimum > 0,
)

with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "fewest"
    example = out / "+".join(name.replace(":", "-") for name in names)
    r = run_cli(
        HERE / "hybrid_finder.py",
        "fewest-markings",
        *BOARD,
        "--circles",
        CIRCLE,
        "--out",
        out,
    )
    report = r.stdout
    check(
        f"fewest-markings, {CIRCLE} circled, no --engine: the brute force's "
        f"minimum, proven on pysat-lazy, and its one set with its directory "
        f"({report.splitlines()[-2:]}, stderr: {r.stderr[-300:]})",
        r.returncode == 0
        and report.splitlines()[-2:]
        == [
            f"minimum {minimum}: proven on pysat-lazy, 1 unique set of "
            f"{minimum} markings",
            f"unique: {' '.join(names)}: {example} (seed 0)",
        ],
    )

    r = run_cli(HERE / "hybrid_finder.py", "verify", example)
    stamp, verdicts = read_verified(example / "verified.jsonl")
    check(
        "verify, the solver-free reader, passes the example",
        r.returncode == 0
        and stamp == {"verified_examples": 1}
        and [v["ok"] for v in verdicts] == [True],
    )
    (record,) = [
        json.loads(line)
        for line in (example / "examples.jsonl").read_text().splitlines()
    ]
    found = hybrid_finder.HybridFinder(hybrid.Conditions(4, 4)).candidate_from_record(
        record
    )
    check(
        "the example is the brute force's grid, and its record carries the "
        "circle, the negative constraint and its checkerboard windows as "
        "exactly its markings",
        found.network == grid
        and record["circles"] == [CIRCLE]
        and record["battenberg_only"] is True
        and sorted(record["battenberg"])
        == sorted(record["checkerboard_windows"])
        == sorted(names),
    )

    r = run_cli(HERE / "hybrid_finder.py", "render", example)
    # The same grid drawn in process, for where each cell's box is.
    drawn = hybrid_render.Picture(
        grid, 4, 4, [hybrid.parse_cell(CIRCLE)], False, windows
    )
    with Image.open(example / "renders" / "0.png") as image:
        image.load()
        ring = hybrid_render.GIVEN_RING
        others = [
            hybrid.cell_name(cell)
            for cell in hybrid.valid_circles(drawn.board)
            if hybrid.cell_name(cell) != CIRCLE
        ]
        check(
            f"render: the circle that is a condition is ringed in the second "
            f"colour ({r.stderr[-200:]})",
            r.returncode == 0
            and pixels(image, drawn.box(hybrid.parse_cell(CIRCLE)), ring) > 200,
        )
        # A marking's symbol reaches 12 pixels into each cell round its
        # window's centre, so a cell is read clear of that corner.
        inner = [
            (x0 + 14, y0 + 14, x1 - 14, y1 - 14)
            for x0, y0, x1, y1 in map(drawn.box, hybrid.valid_circles(drawn.board))
            if (x0, y0, x1, y1) != drawn.box(hybrid.parse_cell(CIRCLE))
        ]
        check(
            f"render: the grid's other valid circles carry no ring ({others})",
            len(others) > 0 and not any(pixels(image, box, ring) for box in inner),
        )
        centres = [drawn.box(window)[2:] for window in windows]
        check(
            "render: each marking's window carries the heavier checkerboard "
            "symbol in the second colour",
            all(
                pixels(image, (x - 12, y - 12, x + 12, y + 12), ring) > 100
                for x, y in centres
            ),
        )

    r = run_cli(HERE / "hybrid_finder.py",
        "--circles", CIRCLE, "--battenberg", " ".join(names), "--battenberg-only",
        "links", example,
    )  # fmt: skip
    links = sorted((example / "links").glob("*.txt"))
    check(
        f"links writes the example's link, its markings on exactly the "
        f"set's windows ({r.stderr[-200:]})",
        r.returncode == 0
        and len(links) == 1
        and battenberg_vertices(Decoded(links[0].read_text().strip()), 4)
        == set(windows),
    )

    before = (out / "sets.jsonl").read_text()
    r = run_cli(
        HERE / "hybrid_finder.py",
        "fewest-markings",
        *BOARD,
        "--circles",
        CIRCLE,
        "--out",
        out,
    )
    check(
        "a rerun into the finished directory: the same report, no set solved again",
        r.returncode == 0
        and r.stdout == report
        and (out / "sets.jsonl").read_text() == before,
    )

    r = run_cli(
        HERE / "hybrid_finder.py",
        "fewest-markings",
        *BOARD,
        "--engine",
        "cpsat",
        "--out",
        Path(d) / "unused",
    )
    check(
        "fewest-markings on cpsat is refused by name, exit 2, before any solve",
        r.returncode == 2
        and "--engine cpsat" in r.stderr
        and not (Path(d) / "unused").exists(),
    )

finish()

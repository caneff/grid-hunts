"""Spec #20 end to end, through the commands Chris runs: the enumeration
with Battenberg markings, a hunt on the default engine with a marking,
`verify`, `classify` with and without the negative constraint, `render`,
`links --battenberg`, and the refusal on `--engine cpsat`.

One chain on the 4x4 board, each step reading the files the step before
wrote. The other Battenberg tests each take one command against the brute
force or the rule reader; this one is that the commands fit together.

Blind to: the slow renbanana tests, a hunt's own output on a board above
4x4, and how a found grid reads once it is built into a puzzle link. The
link is decoded here, not opened: whether Penpa+ draws the checkerboard
symbol on the right corner and the rules text reads right is seen only in a
browser (`penpa-browser-check.mjs`, outside the gate). The picture is read
here for existing and decoding only; `test_ubahn_hybrid_render.py` reads its
pixels, and nothing but an open of the PNG says the symbols read as clues.

One CaDiCaL thread; about ten seconds.

    uv run finders/ubahn/test_ubahn_battenberg_e2e.py
"""

import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
from cli_checks import check, finish, read_jsonl, run_cli
from penpa_decode import Decoded, battenberg_vertices
from verified_io import read_verified

BOARD = ["--rows", "4", "--cols", "4", "--timeout", "10"]
# The decision log's 4x4 answers (§ Hybrid: Battenberg markings, the 4x4
# answers), the brute force's: the flags and the word `classify` must give.
ANSWERS = (
    (("--battenberg", "r1c3"), "unique"),
    (("--battenberg", "c1:turn c2:turn r3c1", "--battenberg-only"), "unique"),
    (("--battenberg-only",), "not_unique"),
    (("--battenberg", "c1:turn", "--battenberg-only"), "infeasible"),
    (("--battenberg", "r1c1"), "infeasible"),
)

r = run_cli(HERE / "brute.py", "4", "4", "--battenberg", "r1c3")
check(
    f"the enumeration: 18 valid 4x4 grids, one with a marking at r1c3 "
    f"({r.stdout.splitlines()[1:]})",
    r.returncode == 0
    and "valid hybrid grids, no condition: 18" in r.stdout
    and "Battenberg markings r1c3: unique (1)" in r.stdout,
)

with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "hunt"
    r = run_cli(HERE /
        "hybrid_finder.py", *BOARD, "--battenberg", "r1c3",
        "--out", str(out), "--seeds=0:6", "--workers", "1",
    )  # fmt: skip
    examples = read_jsonl(out / "examples.jsonl") if r.returncode == 0 else []
    check(
        f"hunt, r1c3 marked, no --engine: the one grid, once, on pysat-lazy "
        f"({r.stderr[-300:]})",
        len(examples) == 1 and examples[0]["engine"] == "pysat-lazy",
    )
    check(
        "hunt: the record carries the marking it was asked for and lists "
        "the grid's three checkerboard windows",
        bool(examples)
        and examples[0]["battenberg"] == ["r1c3"]
        and examples[0]["battenberg_only"] is False
        and examples[0]["checkerboard_windows"] == ["r1:turn", "r1c3", "r2:turn"],
    )

    r = run_cli(HERE / "hybrid_finder.py", "verify", str(out))
    stamp, verdicts = read_verified(out / "verified.jsonl")
    check(
        "verify, the solver-free reader, passes the hunt's example",
        r.returncode == 0
        and stamp == {"verified_examples": 1}
        and [v["ok"] for v in verdicts] == [True],
    )

    for flags, word in ANSWERS:
        r = run_cli(HERE / "hybrid_finder.py", "classify", *BOARD, *flags)
        check(
            f"classify, {' '.join(flags)}: {word}",
            r.returncode == 0 and r.stdout.startswith(f"{word}:"),
        )

    r = run_cli(HERE / "hybrid_finder.py", "render", str(out))
    pictures = sorted((out / "renders").glob("*.png"))
    decodes = False
    if len(pictures) == 1:
        with Image.open(pictures[0]) as image:
            image.load()
            decodes = image.format == "PNG"
    check(
        f"render writes the example's picture, a PNG that decodes ({r.stderr[-200:]})",
        r.returncode == 0 and decodes,
    )

    r = run_cli(
        HERE / "hybrid_finder.py", "--battenberg", "r1c3 r1:turn", "links", str(out)
    )
    links = sorted((out / "links").glob("*.txt"))
    check(
        f"links --battenberg writes the example's link ({r.stderr[-200:]})",
        r.returncode == 0 and len(links) == 1,
    )
    if len(links) == 1:
        check(
            "the link decodes to a marking on each of the two named windows "
            "and on no other",
            battenberg_vertices(Decoded(links[0].read_text().strip()), 4)
            == {(0, 2), (0, -1)},
        )

for flags in (("--battenberg", "r1c3"), ("--battenberg-only",)):
    r = run_cli(
        HERE / "hybrid_finder.py", "classify", *BOARD, "--engine", "cpsat", *flags
    )
    check(
        f"classify on cpsat with {flags[0]} is refused by name, exit 2",
        r.returncode == 2 and f"{flags[0]} is on the PySAT engines only" in r.stderr,
    )

finish()

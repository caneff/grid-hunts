"""Spec #781 end to end, through the commands Chris runs: the enumeration,
a hunt on the default engine with each kind of condition, `verify`,
`render`, `classify` on every engine, the timing script's run and report,
and the plain finder beside them.

One chain on small boards, each step reading the files the step before
wrote. The other hybrid tests each take one command against the brute
force; this one is that the commands fit together.

Blind to: the app (this puzzle has no SudokuMaker link), and how a rendered
picture reads to a person. The pictures are checked here for existing and
decoding only; `test_ubahn_hybrid_render.py` reads pixels at chosen points,
and nothing but an open of the PNG says the board reads as the puzzle.

One solver thread throughout; about fifteen seconds.

    uv run finders/ubahn/test_ubahn_hybrid_e2e.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
from subprocess_env import success_env
from verified_io import read_verified

BOARD = ["--rows", "4", "--cols", "4", "--timeout", "10"]
ENGINES = ("cpsat", "pysat-lazy", "pysat-propagator")
# The decision log's 4x4 answers (§ Hybrid), brute force's: the condition and
# the word `classify` must give for it.
ANSWERS = (
    ((), "not_unique"),
    (("--circles", "c1:turn r2c4"), "unique"),
    (("--circles", "r2c2 r2c4"), "infeasible"),
    (("--blank-strip",), "not_unique"),
)

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def run_script(script, *args):
    return subprocess.run(
        [sys.executable, str(HERE / script), *args],
        capture_output=True,
        text=True,
        env=success_env(),
    )


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def verified(script, out, examples):
    """Whether `verify` read every example of the hunt in `out` and passed
    each one. Its exit status is 0 whatever the verdicts, so the verdicts
    are read from the file it writes."""
    r = run_script(script, "verify", str(out))
    if r.returncode != 0:
        return False
    stamp, verdicts = read_verified(out / "verified.jsonl")
    return (
        stamp == {"verified_examples": len(examples)}
        and len(verdicts) == len(examples)
        and all(v["ok"] is True for v in verdicts)
    )


r = run_script("brute.py", "4", "4", "--circles", "c1:turn r2c4")
check(
    f"the enumeration: 18 valid 4x4 grids, one with c1:turn and r2c4 circled "
    f"({r.stdout.splitlines()[1:]})",
    r.returncode == 0
    and "valid hybrid grids, no condition: 18" in r.stdout
    and "circles c1:turn r2c4: unique (1)" in r.stdout,
)


with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "hunt"
    r = run_script(
        "hybrid_finder.py", *BOARD, "--circles", "r2c2",
        "--out", str(out), "--seeds=0:20", "--workers", "1",
    )  # fmt: skip
    examples = read_jsonl(out / "examples.jsonl") if r.returncode == 0 else []
    check(
        f"hunt, r2c2 circled, no --engine: examples on pysat-lazy ({r.stderr[-300:]})",
        bool(examples) and all(ex["engine"] == "pysat-lazy" for ex in examples),
    )
    check(
        "hunt: every record carries the circle it was asked for",
        all(ex["circles"] == ["r2c2"] for ex in examples),
    )

    check(
        "verify, the solver-free reader, passes every example of the hunt",
        verified("hybrid_finder.py", out, examples),
    )

    # Number-cell circles together with the piece-count condition: the
    # decision log's two grids, on the default engine.
    both = Path(d) / "both"
    r = run_script(
        "hybrid_finder.py", *BOARD, "--circles", "c1:turn c4:turn",
        "--exactly", "2:cross:r2",
        "--out", str(both), "--seeds=0:20", "--workers", "1",
    )  # fmt: skip
    found = read_jsonl(both / "examples.jsonl") if r.returncode == 0 else []
    check(
        f"hunt, c1:turn and c4:turn circled with 2 crosses in r2: both grids, "
        f"each once, verified ({len(found)})",
        len(found) == 2
        and all(
            ex["circles"] == ["c1:turn", "c4:turn"] and ex["exactly"] == "2:cross:r2"
            for ex in found
        )
        and verified("hybrid_finder.py", both, found),
    )

    r = run_script("hybrid_finder.py", "render", str(out))
    pictures = sorted(p.name for p in (out / "renders").glob("*.png"))
    check(
        f"render writes one picture per example ({len(pictures)})",
        r.returncode == 0 and len(pictures) == len(examples),
    )
    sizes = set()
    for name in pictures:
        with Image.open(out / "renders" / name) as image:
            image.load()
            sizes.add(image.size)
    check(f"render: every picture decodes, all one size ({sizes})", len(sizes) == 1)

    for engine in ENGINES:
        for flags, word in ANSWERS:
            r = run_script(
                "hybrid_finder.py", "classify", *BOARD, "--engine", engine, *flags
            )
            check(
                f"classify on {engine}, {' '.join(flags) or 'no condition'}: {word}",
                r.returncode == 0 and r.stdout.startswith(f"{word}:"),
            )
        r = run_script(
            "hybrid_finder.py", "classify", "--rows", "4", "--cols", "4",
            "--engine", engine, "--timeout", "0",
        )  # fmt: skip
        check(
            f"classify on {engine} with no time: timeout, never an answer",
            r.returncode == 0 and r.stdout.startswith("timeout:"),
        )

    progress = []
    for engine in ENGINES:
        progress.append(str(Path(d) / f"{engine}.jsonl"))
        r = run_script(
            "time_engines.py", "run", "--engine", engine, "--progress", progress[-1],
            "--case", "6x6", "--seeds", "0:2",
        )  # fmt: skip
        check(
            f"timing run on {engine}: two solves of 6x6 on record ({r.stderr[-200:]})",
            r.returncode == 0
            and sum("solve" in line for line in read_jsonl(Path(progress[-1]))) == 2,
        )
    r = run_script("time_engines.py", "report", *progress)
    check(
        "timing report: a 6x6 row per engine, found and timed out apart",
        r.returncode == 0
        and all(f"| 6x6 | {engine} | 2 | 2 | 0 | 0 " in r.stdout for engine in ENGINES),
    )
    check(
        "timing report: the bar is read against cpsat and, with no 8x8 or "
        "10x10 run, says unknown for both PySAT engines",
        all(
            f"- `{engine}` is at least 2 times faster than `cpsat` at 8x8 and "
            "10x10: unknown" in r.stdout
            for engine in ENGINES[1:]
        ),
    )

    plain = Path(d) / "plain"
    r = run_script(
        "ubahn_finder.py", "--rows", "4", "--cols", "4", "--timeout", "10",
        "--out", str(plain), "--seeds=0:3", "--workers", "1",
    )  # fmt: skip
    config = json.loads((plain / "run.json").read_text())["config"]
    check(
        f"the plain finder still hunts, with no engine in its config ({config})",
        r.returncode == 0 and "engine" not in config,
    )
    check(
        "the plain finder's verify passes every example of its own hunt",
        verified("ubahn_finder.py", plain, read_jsonl(plain / "examples.jsonl")),
    )

sys.exit(0 if ok else 1)

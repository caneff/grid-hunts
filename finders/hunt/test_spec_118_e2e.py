"""Spec #118 at the `just check` seam: the dormant counting_shaded and qqrr finders
run through the one home of each drifted copy. The retired sampler is archived and
out of the gate, `connected.py` finds a connected shape on the shared flow encoding,
both C helpers load through the one loader, and the qqrr tie finder's `verify` and
`--warm-from` read the rule and the grid text from `hunt_common`.

WHAT A GREEN RUN DOES NOT COVER: the slow suites (`just test-slow`), any hunt long
enough for its output to matter (connected.py runs one small size range, the tie
finder verifies hand-written records and hunts nothing), two processes racing a
rebuild of the real libraries (test_c_library.py races a toy one), and how a found
grid reads once it is built into a puzzle link.

    uv run finders/hunt/test_spec_118_e2e.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from cli_checks import check, finish, run_cli
from verified_io import read_verified

CONNECTED = ROOT / "finders" / "counting_shaded" / "connected.py"
TIE_FINDER = ROOT / "finders" / "qqrr" / "hunt" / "tie_finder.py"
# Found by chan_big.py in the 34-36 hunt (docs/research/2026-09-22-qqrr-tie-r5c1.md).
GOOD = "436781529/978265134/125394876/217839465/354176982/689452713/763948251/591627348/842513697"


def python(code):
    """Run `code` in a fresh interpreter, so each library loads as a hunt loads it."""
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT
    )


# The retired sampler is archived with its README, the uncited script is gone, and
# the gate lists nothing under archive/.
check(
    "gridfirst.py is archived with its README",
    (ROOT / "archive/finders/gridfirst.py").is_file()
    and (ROOT / "archive/finders/gridfirst.md").is_file(),
)
check(
    "gridfirst.py and maxpinned.py are gone from counting_shaded",
    not any(
        (ROOT / "finders/counting_shaded" / name).exists()
        for name in ("gridfirst.py", "maxpinned.py")
    ),
)
listed = subprocess.run(
    ["bash", "tests/all.sh", "--list"], capture_output=True, text=True, cwd=ROOT
)
check(
    f"the gate lists suites and none under archive/ (exit {listed.returncode})",
    listed.returncode == 0 and listed.stdout and "archive/" not in listed.stdout,
)

# connected.py on the shared flow encoding: a small size range gives a shape, and the
# shape it prints is orthogonally connected.
r = run_cli(CONNECTED, "--min", "4", "--max", "8", "--workers", "1", "--seconds", "60")
shape_lines = [ln for ln in r.stdout.splitlines() if ln.startswith("shape [")]
check(
    f"connected.py --min 4 --max 8 prints a shape (exit {r.returncode})",
    r.returncode == 0 and len(shape_lines) == 1,
)
if shape_lines:
    cells = set(json.loads(shape_lines[0].removeprefix("shape ")))
    seen, todo = set(), [min(cells)]
    while todo:
        i = todo.pop()
        if i in seen:
            continue
        seen.add(i)
        r_, c_ = divmod(i, 9)
        steps = (i - 9, i + 9, i - 1 if c_ else -1, i + 1 if c_ < 8 else -1)
        todo.extend(j for j in steps if j in cells)
    check(f"... and the shape is connected ({sorted(cells)})", seen == cells)

# Both C helpers load through the one loader, each in a fresh process.
loaded = python(
    "import sys; sys.path[:0] = ['finders/counting_shaded', 'finders/halver'];"
    "import fastclimb, halver_brute_c;"
    "print(fastclimb.c_library is halver_brute_c.c_library,"
    " fastclimb.c_library.__file__.endswith('finders/hunt/c_library.py'),"
    " fastclimb.LIB is not None, halver_brute_c._lib is not None)"
)
check(
    f"fastclimb and halver_brute_c load through finders/hunt/c_library.py "
    f"({loaded.stdout.strip()} {loaded.stderr[-300:]})",
    loaded.returncode == 0 and loaded.stdout.split() == ["True"] * 4,
)

# The tie finder verifies against hunt_common's rule: the found grid holds, and the
# same grid filed under another corner is refused, naming the corner and its number.
hc = python(
    "import sys; sys.path.insert(0, 'finders/qqrr/hunt'); import hunt_common as hc;"
    "print(hc.CORNER_RANK, hc.CAGE_QQRR, hc.WINDOW_RANK, hc.BOUND_MAX)"
)
corner_rank, cage_qqrr, window_rank, bound_max = map(int, hc.stdout.split())
check(
    "hunt_common holds the tie hunt's rule (corner 5, cage 33, QR 10, bound 7)",
    (corner_rank, cage_qqrr, window_rank, bound_max) == (5, 33, 10, 7),
)
with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "hunt"
    out.mkdir()
    base = {"grid": GOOD, "hunt": "r1c5", "ten": "r7c7", "corner": "bl", "q34": True}
    records = [base, dict(base, corner="tl")]
    (out / "examples.jsonl").write_text("".join(json.dumps(x) + "\n" for x in records))
    (out / "progress.jsonl").write_text(
        "".join(
            json.dumps({"event": "seed_done", "seed": k, "outcome": "example"}) + "\n"
            for k in range(len(records))
        )
    )
    (out / "state.json").write_text(
        json.dumps({"seed": len(records) - 1, "state": {"found": []}})
    )
    r = run_cli(TIE_FINDER, "verify", str(out))
    check(f"tie_finder verify exits 0 ({r.stderr[-300:]})", r.returncode == 0)
    _stamp, verdicts = read_verified(out / "verified.jsonl")
    check("the found grid verifies", verdicts[0]["ok"] is True)
    reason = verdicts[1].get("reason", "")
    check(
        f"the grid under another corner is refused naming the corner ({reason})",
        verdicts[1]["ok"] is False
        and "corner QQRR" in reason
        and f"not {corner_rank}" in reason,
    )

    # --warm-from reads examples.jsonl through the hunt-files reader: a bad record
    # that is not the last line is refused, named by its record number.
    src = Path(d) / "warm"
    src.mkdir()
    (src / "examples.jsonl").write_text(
        json.dumps(base)
        + "\n"
        + json.dumps(dict(base, grid="not a grid"))
        + "\n"
        + json.dumps(base)
        + "\n"
    )
    r = run_cli(
        TIE_FINDER,
        "--out",
        str(Path(d) / "warm-out"),
        "--seeds=0:1",
        *("--hunt", "r1c5", "--ten", "r7c7", "--corner", "bl", "--timeout", "1"),
        "--workers",
        "1",
        "--warm-from",
        str(src),
    )
    check(
        f"--warm-from over a bad record refuses, naming record 2 (exit {r.returncode})",
        r.returncode == 2 and "examples.jsonl record 2" in r.stderr,
    )

finish()

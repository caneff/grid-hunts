"""The qqrr tie finder's `hunt` CLI run (#491), black-box.

`hunt verify DIR` over a hand-written examples.jsonl holding a grid the 34-36
hunt found (explorer preset "33 at r1c5, r1c4 < 8, QR 10 at r7c7 ... bl #1")
and three corruptions of it; then a fresh hunt with a solve cap too short to
find anything, for the config run.json records and the empty seed's reason.
One CP-SAT worker; about ten seconds in all.

    uv run finders/qqrr/hunt/test_tie_finder.py
"""

import json
import resource
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "finders" / "hunt"))
from subprocess_env import success_env

HERE = Path(__file__).resolve().parent
FINDER = HERE / "tie_finder.py"
# Found by chan_big.py in the 34-36 hunt (docs/research/2026-09-22-qqrr-tie-r5c1.md).
GOOD = "436781529/978265134/125394876/217839465/354176982/689452713/763948251/591627348/842513697"
# The tie hunt's first br grid (same doc): cage 33 at r5c1, a tie, QR 10 at r6c6, but r4c1 = 8.
BR1 = "591247638/672183954/438695127/865934271/927516483/143872569/284369715/716458392/359721846"
# hunt_common's r1c5 seed grid: everything but the tie holds at QR r6c6, corner br.
SEED_R1C5 = "356791428/974286531/128534967/215948673/483617295/697352814/562873149/749165382/831429756"
# GOOD with r1c1 and r1c2 swapped: row 1 still holds 1..9, column 1 and box 1 do not.
NOT_SUDOKU = "346781529" + GOOD[9:]

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(FINDER), *args],
        capture_output=True,
        text=True,
        env=success_env(),
    )


def record(grid, **over):
    rec = {"grid": grid, "hunt": "r1c5", "ten": "r7c7", "corner": "bl", "q34": True}
    rec.update(over)
    return rec


with tempfile.TemporaryDirectory() as d:
    out = Path(d)
    cases = [
        ("the found grid", record(GOOD), True, ""),
        (
            "the found grid filed under another corner",
            record(GOOD, corner="tl"),
            False,
            "corner",
        ),
        (
            "the found grid filed under another QR-10 window",
            record(GOOD, ten="r6c6"),
            False,
            "QR",
        ),
        ("a grid that is not a sudoku", record(NOT_SUDOKU), False, "sudoku"),
        (
            "the found grid filed under the other cage",
            record(GOOD, hunt="r5c1"),
            False,
            "cage",
        ),
        (
            "a grid with no tie",
            record(SEED_R1C5, ten="r6c6", corner="br"),
            False,
            "tie",
        ),
        (
            "a grid over the bound",
            record(BR1, hunt="r5c1", ten="r6c6", corner="br", q34=False),
            False,
            "bounded",
        ),
        (
            "a grid with no 34-36 cell",
            record(BR1, hunt="r5c1", ten="r6c6", corner="br"),
            False,
            "34-36",
        ),
    ]
    (out / "examples.jsonl").write_text(
        "".join(json.dumps(rec) + "\n" for _, rec, _, _ in cases)
    )
    r = run_cli("verify", str(out))
    check("hunt verify exits 0", r.returncode == 0)
    verdicts = [
        json.loads(line) for line in (out / "verified.jsonl").read_text().splitlines()
    ]
    for (name, _, want, reason), v in zip(cases, verdicts, strict=True):
        check(f"verify: {name} -> {want}", v["ok"] is want)
        if reason:
            check(f"verify: {name} says why ({reason})", reason in v.get("reason", ""))

with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "hunt"
    args = ["--out", str(out), "--seeds=0:1", "--workers", "1"]
    config = ["--hunt", "r1c5", "--ten", "r7c7", "--corner", "bl", "--q34"]
    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
    r = run_cli(*args, *config, "--timeout", "5")
    cpu = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime - before
    check("a hunt capped at 5 s exits 0", r.returncode == 0)
    # --workers 1 reaches the solver: cpsat.solver's portfolio default of 8
    # workers spent 29 s of CPU over a 5 s cap, one worker 7 (measured
    # 2026-09-27). A shorter cap ends inside single-threaded presolve and
    # cannot tell the two apart.
    check(f"--workers 1 solves on one worker ({cpu:.1f} s CPU < 15)", cpu < 15)
    run_json = json.loads((out / "run.json").read_text())
    check(
        "run.json records the finder's config",
        run_json.get("config")
        == {"hunt": "r1c5", "ten": "r7c7", "corner": "bl", "timeout": 5.0, "q34": True},
    )
    events = [
        json.loads(line) for line in (out / "progress.jsonl").read_text().splitlines()
    ]
    check(
        "the capped seed is empty with reason timeout",
        [(e["outcome"], e.get("empty_reason")) for e in events]
        == [("empty", "timeout")],
    )

    r = run_cli(*args, *config, "--timeout", "9")
    check("resuming under another timeout refuses", r.returncode == 2)

with tempfile.TemporaryDirectory() as d:
    r = run_cli("--out", str(Path(d) / "hunt"), "--seeds=0:1", "--ten", "r7c7")
    check(
        "a hunt missing --hunt/--corner/--timeout refuses (exit 2)", r.returncode == 2
    )
    for flag in ("--hunt", "--corner", "--timeout"):
        check(f"the refusal names the missing {flag}", flag in r.stderr)

with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "hunt"
    flags = ["--hunt", "r1c5", "--corner", "bl", "--timeout", "1", "--ten", "r9c9"]
    r = run_cli("--out", str(out), "--seeds=0:1", *flags)
    check("a hunt with a window off the board refuses (exit 2)", r.returncode == 2)
    check("the refused hunt wrote no run.json", not (out / "run.json").exists())

sys.exit(0 if ok else 1)

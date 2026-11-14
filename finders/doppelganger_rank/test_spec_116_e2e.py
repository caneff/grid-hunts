"""Spec #116 at the `just check` seam, through the commands:

- Story 1: a halver report given a marks file it cannot read (missing, not
  JSON) exits 2 with the reason on stderr and nothing on stdout, never the 1
  of "a mark did not hold"; the lockout check does the same.
- Story 2: a mark on `r0c1`, or on a cell past the board, is refused by name
  with exit 2 by the Doppelganger rank check and by both halver reports.
- The Doppelganger rank check prints its marks in `halver_report`'s format,
  `held` and `NOT HELD` with a breaking solution, and keeps the 0/1 exit.
- A 4x4 Doppelganger rank hunt runs the shared target-grid loop on the
  driver's CLI shell: `summary DIR` splits its seeds with the loop's
  `budget` bucket (never `capped`), and `links DIR` reports what it wrote.

WHAT A GREEN RUN DOES NOT COVER: the halver hunts, which run only in the
slow group (`just test-slow`: halver_between/test_hunt.py,
halver_lockout/test_hunt.py) and the Doppelganger rank 9x9 hunt; a hunt
directory written before #130 renamed `capped` to `budget`, whose summary
now refuses; and how a minted link renders in sudokumaker.app (links are
minted offline here).

    uv run finders/doppelganger_rank/test_spec_116_e2e.py
"""

import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINDERS = HERE.parent
sys.path.insert(0, str(FINDERS / "hunt"))

# isort: split
import short_link
from cli_checks import check, check_refusal, finish, run_cli

CHECK = HERE / "check.py"
HUNT = HERE / "hunt.py"
BETWEEN_REPORT = FINDERS / "halver_between" / "report.py"
LOCKOUT_CHECK = FINDERS / "halver_lockout" / "check.py"
LOCKOUT_BOARD = FINDERS / "halver_lockout" / "fixtures" / "unique.json"
RANK_BOARD = json.loads((HERE / "fixtures" / "unique_4x4.json").read_text())
SPLIT = re.compile(
    r"\d+ seeds .*: found \d+, duplicate \d+, proven infeasible \d+, "
    r"timed out \d+, budget \d+ \(a budget ran out: no proof\), "
    r"no separating clue \d+, rejected \d+"
)


def refused_quietly(name, result, text):
    """Exit 2, `text` on stderr, and no verdict line on stdout."""
    check_refusal(name, result, text)
    check(f"{name}: nothing on stdout ({result.stdout[-200:]!r})", result.stdout == "")


def write(path, content):
    path.write_text(content if isinstance(content, str) else json.dumps(content))
    return path


with short_link.fake_mint(), tempfile.TemporaryDirectory() as name:
    tmp = Path(name)
    missing = tmp / "missing.json"
    not_json = write(tmp / "not_json.json", "{not json")

    # Story 1: an unreadable marks file is exit 2, never "a mark did not hold".
    for label, marks in (("missing", missing), ("not JSON", not_json)):
        refused_quietly(
            f"between report, marks file {label}",
            run_cli(BETWEEN_REPORT, "--marks", marks),
            str(marks),
        )
        refused_quietly(
            f"lockout check, marks file {label}",
            run_cli(LOCKOUT_CHECK, LOCKOUT_BOARD, "--marks", marks),
            str(marks),
        )

    # Story 2: an off-board cell is refused by name in both finders.
    for cell in ("r0c1", "r1c10"):
        off = write(tmp / f"{cell}.json", [{"kind": "digit", "cell": cell, "digit": 5}])
        refused_quietly(
            f"between report, mark on {cell}",
            run_cli(BETWEEN_REPORT, "--marks", off),
            cell,
        )
        refused_quietly(
            f"lockout check, mark on {cell}",
            run_cli(LOCKOUT_CHECK, LOCKOUT_BOARD, "--marks", off),
            cell,
        )
    for cell in ("r0c1", "r5c1"):
        board = {**RANK_BOARD, "marks": [{"kind": "digit", "cell": cell, "digit": 1}]}
        refused_quietly(
            f"Doppelganger check, mark on {cell} of a 4x4",
            run_cli(CHECK, write(tmp / f"rank_{cell}.json", board)),
            cell,
        )

    # The Doppelganger check prints through halver_report: held, then NOT HELD.
    # The fixture's first three marks hold; its fourth is false on purpose.
    true_marks = RANK_BOARD["marks"][:3]
    done = run_cli(CHECK, write(tmp / "held.json", {**RANK_BOARD, "marks": true_marks}))
    verdicts = [line for line in done.stdout.splitlines() if line.startswith("held ")]
    check(
        f"Doppelganger check: every mark held, exit 0 ({done.returncode})",
        done.returncode == 0 and len(verdicts) == len(true_marks),
    )
    wrong = {**RANK_BOARD, "marks": [{"kind": "digit", "cell": "r1c1", "digit": 1}]}
    done = run_cli(CHECK, write(tmp / "wrong.json", wrong))
    lines = done.stdout.splitlines()
    check(
        f"Doppelganger check: a false mark is NOT HELD with its breaker, exit 1 "
        f"({done.returncode}: {lines[-2:]})",
        done.returncode == 1
        and "NOT HELD  r1c1 = 1" in lines
        and lines[-1].startswith("  broken by: "),
    )

    # A 4x4 hunt on the shared loop and the driver's shell.
    empty = write(
        tmp / "empty.json", {"size": 4, "box": [2, 2], "clues": [], "marks": []}
    )
    out = tmp / "hunt"
    done = run_cli(HUNT, "--board", empty, "--out", out, "--seeds", "0:3")
    check(f"4x4 hunt exits 0 ({done.stderr[-300:]})", done.returncode == 0)
    summary = run_cli(HUNT, "summary", out)
    check(
        "summary DIR splits the seeds with the loop's budget bucket",
        summary.returncode == 0
        and any(SPLIT.fullmatch(line) for line in summary.stdout.splitlines())
        and "capped" not in summary.stdout,
    )
    links = run_cli(HUNT, "links", out)
    check(
        f"links DIR says what it wrote ({links.stdout!r})",
        links.returncode == 0 and f"links to {out / 'links'}" in links.stdout,
    )

finish()

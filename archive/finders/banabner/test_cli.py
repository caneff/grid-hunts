"""The Banabner finder's own flags, through the CLI (#761).

    uv run finders/banabner/test_cli.py

`--help` lists the finder's flags, and a hunt started with no `--timeout` is
refused before any solve.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAIL = []


def check(name, ok, detail=""):
    print(f"{'ok  ' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        FAIL.append(name)


def finder(*args):
    return subprocess.run(
        [sys.executable, str(HERE / "banabner_finder.py"), *args],
        capture_output=True,
        text=True,
    )


def main():
    shown = finder("--help")
    check("--help exits 0", shown.returncode == 0, shown.stderr[-300:])
    for flag in ("--timeout", "--max-choc-side", "--no-speedups"):
        check(f"--help names {flag}", flag in shown.stdout)
    refused = finder("--out", str(HERE / "never-written"), "--seeds", "0:1")
    check(
        "a hunt with no --timeout is refused",
        refused.returncode == 2 and "a hunt needs --timeout" in refused.stderr,
        refused.stderr[-300:],
    )
    check("the refused hunt wrote nothing", not (HERE / "never-written").exists())

    print(f"\n{len(FAIL)} failing" if FAIL else "\nall checks pass")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

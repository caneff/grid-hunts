"""`tests/all.sh --jobs`: the gate's runner, on a throwaway tree of fake suites.

A copy of the runner sits in a temp tree with three fake suites, so the real
suites are never run. The checks: `--jobs 2` runs two sleeping suites in about
the time of one, a failing suite is named with its whole output and exits 1
with the count line, a failure starts no suite that had not started, and a
`--jobs` that is not a positive integer is refused.

    uv run tests/test_all_sh.py
"""

import subprocess
import sys
import tempfile
import time
from pathlib import Path

ALL = Path(__file__).resolve().parent / "all.sh"
SLEEP = 1.5

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def tree(root, suites):
    """A copy of the runner over `suites`, {file name: script body}, without
    its line that lists this test; returns the copy's path."""
    (root / "tests").mkdir(parents=True)
    lines = ALL.read_text().splitlines(keepends=True)
    (root / "tests" / "all.sh").write_text(
        "".join(line for line in lines if "tests/test_all_sh.py" not in line)
    )
    (root / "finders" / "fake").mkdir(parents=True)
    for name, body in suites.items():
        (root / "finders" / "fake" / name).write_text(body)
    return root / "tests" / "all.sh"


def run(script, *args):
    start = time.monotonic()
    r = subprocess.run(
        ["bash", str(script), *args], capture_output=True, text=True, timeout=120
    )
    return r, time.monotonic() - start


sleeper = f"import time\ntime.sleep({SLEEP})\n"

with tempfile.TemporaryDirectory() as d:
    script = tree(Path(d) / "sleepers", {"test_a.py": sleeper, "test_b.py": sleeper})
    r, serial = run(script, "--group", "test", "--jobs", "1")
    check(
        f"--jobs 1: both suites pass, one after the other ({serial:.1f} s)",
        r.returncode == 0
        and r.stdout.splitlines()[-1] == "2 of 2 suites passed (group: test)"
        and serial >= 2 * SLEEP,
    )
    r, parallel = run(script, "--group", "test", "--jobs", "2")
    check(
        f"--jobs 2: both suites pass in the time of one ({parallel:.1f} s)",
        r.returncode == 0
        and r.stdout.splitlines()[-1] == "2 of 2 suites passed (group: test)"
        and parallel < serial - SLEEP / 2,
    )

with tempfile.TemporaryDirectory() as d:
    script = tree(
        Path(d) / "failing",
        {
            "test_a_bad.py": "print('the reason')\nraise SystemExit(1)\n",
            "test_b_never.py": "open('started', 'w').close()\n",
        },
    )
    r, _ = run(script, "--group", "test", "--jobs", "1")
    lines = r.stdout.splitlines()
    check(
        "a failing suite is named with its output, the count line names it, "
        f"exit 1, and the next suite never starts ({lines})",
        r.returncode == 1
        and lines[0] == "FAIL uv run finders/fake/test_a_bad.py"
        and "the reason" in lines
        and lines[-1]
        == "0 of 2 suites passed before uv run finders/fake/test_a_bad.py "
        "failed (group: test)"
        and not (Path(d) / "failing" / "started").exists(),
    )

with tempfile.TemporaryDirectory() as d:
    script = tree(Path(d) / "refused", {})
    for value in ("0", "-1", "x"):
        r, _ = run(script, "--jobs", value)
        check(
            f"--jobs {value} is refused, exit 2, naming the value",
            r.returncode == 2 and f"not '{value}'" in r.stderr and not r.stdout,
        )

sys.exit(0 if ok else 1)

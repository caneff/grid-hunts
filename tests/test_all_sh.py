"""`tests/all.sh`: the gate's runner, on a throwaway tree of fake suites.

A copy of the runner sits in a temp tree with fake suites, so the real suites
are never run. The checks: with no flag and no `GATE_JOBS` suites run one at a
time; `--jobs 2` and `GATE_JOBS=2` run two at once; a failure is named with
its output, starts no further suite and still lets the running one finish
before the count line; a suite whose shell is killed fails the run; an empty
selection is `0 of 0`; a `--jobs` that is not a positive integer is refused.

    uv run tests/test_all_sh.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ALL = Path(__file__).resolve().parent / "all.sh"

ok = True

# A suite that logs its start and its end, with a pause between, to the file
# `log` at the tree's root: one at a time reads start end start end, two at
# once start start.
LOGGER = """\
import time
from pathlib import Path

log = Path(__file__).resolve().parents[2] / "log"
with log.open("a") as f:
    f.write("start {name}\\n")
time.sleep(0.5)
with log.open("a") as f:
    f.write("end {name}\\n")
"""
# A suite that kills the runner's own shell for it, as the OOM killer might:
# of the processes above it that run `all.sh`, the one just below the runner
# itself. Nothing at or above the runner is touched.
KILLER = """\
import os
import signal


def read(pid):
    with open(f"/proc/{pid}/cmdline", "rb") as f:
        cmdline = f.read()
    with open(f"/proc/{pid}/stat") as f:
        stat = f.read()
    return b"all.sh" in cmdline, int(stat[stat.rindex(")") + 2 :].split()[1])


chain = []
pid = os.getppid()
while pid > 1:
    runs_all, parent = read(pid)
    if runs_all:
        chain.append(pid)
    elif chain:
        break
    pid = parent
if len(chain) >= 2:
    os.kill(chain[-2], signal.SIGKILL)
"""


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


def run(script, *args, gate_jobs=None):
    env = {k: v for k, v in os.environ.items() if k != "GATE_JOBS"}
    if gate_jobs is not None:
        env["GATE_JOBS"] = gate_jobs
    return subprocess.run(
        ["bash", str(script), "--group", "test", *args],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def starts_and_ends(root):
    log = root / "log"
    words = [line.split()[0] for line in log.read_text().splitlines()]
    log.unlink()
    return words


with tempfile.TemporaryDirectory() as d:
    root = Path(d) / "loggers"
    script = tree(
        root,
        {f"test_{n}.py": LOGGER.format(name=n) for n in "ab"},
    )
    for label, args, env, want in (
        ("no flag, no GATE_JOBS", (), None, ["start", "end", "start", "end"]),
        ("--jobs 1", ("--jobs", "1"), None, ["start", "end", "start", "end"]),
        ("--jobs 2", ("--jobs", "2"), None, ["start", "start", "end", "end"]),
        ("GATE_JOBS=2", (), "2", ["start", "start", "end", "end"]),
        ("--jobs 1 over GATE_JOBS=2", ("--jobs", "1"), "2", ["start", "end"] * 2),
    ):
        r = run(script, *args, gate_jobs=env)
        check(
            f"{label}: both suites pass, run as {want} ({r.stdout.splitlines()[-1:]})",
            r.returncode == 0
            and r.stdout.splitlines()[-1] == "2 of 2 suites passed (group: test)"
            and starts_and_ends(root) == want,
        )

with tempfile.TemporaryDirectory() as d:
    root = Path(d) / "failing"
    script = tree(
        root,
        {
            "test_a_bad.py": "print('the reason')\nraise SystemExit(1)\n",
            "test_b_slow.py": LOGGER.format(name="b"),
            "test_c_never.py": LOGGER.format(name="c"),
        },
    )
    r = run(script, "--jobs", "2")
    lines = r.stdout.splitlines()
    check(
        "--jobs 2, one suite fails: it is named with its output, the suite "
        "already running finishes before the count line, the next never "
        f"starts, exit 1 ({lines})",
        r.returncode == 1
        and lines[0] == "FAIL uv run finders/fake/test_a_bad.py"
        and "the reason" in lines
        and lines[-2] == "PASS uv run finders/fake/test_b_slow.py"
        and lines[-1]
        == "1 of 3 suites passed, 1 failed: uv run finders/fake/test_a_bad.py "
        "(group: test)"
        and starts_and_ends(root) == ["start", "end"]
        and r.stderr == "",
    )

with tempfile.TemporaryDirectory() as d:
    script = tree(
        Path(d) / "killed",
        {"test_a_ok.py": "pass\n", "test_b_killed.py": KILLER},
    )
    r = run(script, "--jobs", "2")
    check(
        "a suite whose shell is killed is not a pass: exit 1, naming that "
        f"nothing was reported ({r.stdout.splitlines()[-1:]})",
        r.returncode == 1
        and r.stdout.splitlines()[-1]
        == "1 of 2 suites passed, the rest reported nothing (group: test)",
    )

with tempfile.TemporaryDirectory() as d:
    script = tree(Path(d) / "empty", {})
    r = run(script)
    check(
        f"no suite selected: nothing runs, 0 of 0 ({r.stdout.splitlines()})",
        r.returncode == 0
        and r.stdout.splitlines() == ["0 of 0 suites passed (group: test)"],
    )
    for value in ("0", "-1", "x"):
        r = run(script, "--jobs", value)
        check(
            f"--jobs {value} is refused, exit 2, naming the value",
            r.returncode == 2 and f"not '{value}'" in r.stderr and not r.stdout,
        )

sys.exit(0 if ok else 1)

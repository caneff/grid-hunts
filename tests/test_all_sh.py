"""`tests/all.sh`: the gate's runner, on a throwaway tree of fake suites.

A copy of the runner sits in a temp tree with fake suites, so the real suites
are never run. The checks: with no flag and no `GATE_JOBS` suites run one at a
time; `--jobs 2` and `GATE_JOBS=2` run two at once; a failure is named with
its output, starts no further suite and still lets the running one finish
before the count line; a suite whose shell is killed fails the run; an empty
selection is `0 of 0`; a `--jobs` that is not a positive integer is refused.
`--changed <base>` narrows to the diff `<base>...HEAD`: one finder folder
selects that folder plus lint and the runner's test; each shared path widens
the run to every suite and the count line names it; a docs-only diff selects
lint and the runner's test; `--list --changed` prints the selection.

    uv run tests/test_all_sh.py
"""

import os
import re
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
import re
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
        "".join(
            line
            for line in lines
            if "printf 'test\\t%s\\n' \"$runner_test\"" not in line
        )
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

BASE_ENV = {
    k: v for k, v in os.environ.items() if k != "GATE_JOBS" and not k.startswith("GIT_")
}
GIT_ENV = {
    **BASE_ENV,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
}


def git(root, *args):
    subprocess.run(
        ["git", *args], cwd=root, env=GIT_ENV, check=True, capture_output=True
    )


def fake_map(runner):
    """The runner with its data map swapped for one mapped data directory,
    whatever the real map holds."""
    swapped, count = re.subn(
        r'^data_map=".*"$',
        'data_map="docs/research/fake-data/=fake"',
        runner,
        flags=re.MULTILINE,
    )
    assert count == 1, f"{count} data_map lines in tests/all.sh"
    return swapped


def changed_tree(root):
    """A git tree holding the whole runner, a stub runner test, three fake
    finder folders and one file at each shared path, committed as `main`."""
    files = {
        # A mapped data directory, so the mapping loop has a test of its own.
        "tests/all.sh": fake_map(ALL.read_text()),
        "tests/test_all_sh.py": "pass\n",
        "finders/fake/test_a.py": "pass\n",
        "finders/other-one/test_b.py": "pass\n",
        "finders/hunt/test_h.py": "pass\n",
        "finders/loose.py": "",
        "pyproject.toml": "",
        "uv.lock": "",
        "justfile": "",
        ".github/workflows/ci.yml": "",
        "docs/note.md": "",
        "AGENTS.md": "",
        "finders/fake/README.md": "",
        "finders/fake-two/test_f.py": "pass\n",
        "archive/finders/old/test_o.py": "pass\n",
    }
    for name, body in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(body)
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root / "tests" / "all.sh"


def touch_on_branch(root, *names):
    git(root, "checkout", "-q", "-B", "work", "main")
    for name in names:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        with (root / name).open("a") as f:
            f.write("# change\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change")


def changed(script, *args):
    return subprocess.run(
        ["bash", str(script), "--changed", "main", *args],
        capture_output=True,
        text=True,
        timeout=120,
        # The fake tree's pyproject.toml and uv.lock are empty files.
        env={**BASE_ENV, "UV_NO_PROJECT": "1"},
    )


LINT = [
    "uvx ruff check finders tests",
    "uvx ruff format --check finders tests",
    "uv lock --check",
]
RUNNER = "uv run tests/test_all_sh.py"
ALL_TESTS = [
    "uv run finders/fake-two/test_f.py",
    "uv run finders/fake/test_a.py",
    "uv run finders/hunt/test_h.py",
    "uv run finders/other-one/test_b.py",
]


def listing(script, *args):
    r = changed(script, "--list", *args)
    return r.returncode, r.stdout.splitlines()


def count_line(script, *args):
    r = changed(script, "--group", "test", *args)
    return r.returncode, r.stdout.splitlines()[-1]


with tempfile.TemporaryDirectory() as d:
    root = Path(d) / "changed"
    root.mkdir()
    script = changed_tree(root)

    touch_on_branch(root, "finders/other-one/test_b.py")
    got = listing(script)
    check(
        "--list --changed, one finder folder: lint, the runner's test and "
        f"that folder only ({got})",
        got == (0, [*LINT, RUNNER, "uv run finders/other-one/test_b.py"]),
    )
    got = count_line(script)
    check(
        "--changed run, one finder folder: counts the narrowed suites, no "
        f"widened note ({got})",
        got == (0, "2 of 2 suites passed (group: test)"),
    )

    touch_on_branch(root, "finders/fake/test_a.py")
    got = listing(script)
    check(
        f"--list --changed, finders/fake does not select finders/fake-two ({got})",
        got == (0, [*LINT, RUNNER, "uv run finders/fake/test_a.py"]),
    )

    for path in (
        "finders/hunt/test_h.py",
        "finders/loose.py",
        "pyproject.toml",
        "uv.lock",
        "tests/new_helper.py",
        "justfile",
        ".github/workflows/ci.yml",
        ".python-version",
        "conftest.py",
        "finders/loose.txt",
    ):
        touch_on_branch(root, "finders/other-one/test_b.py", path)
        rc, lines = listing(script)
        check(
            f"--list --changed, {path}: widens to every suite ({lines})",
            rc == 0 and sorted(lines) == sorted([*LINT, RUNNER, *ALL_TESTS]),
        )
        got = count_line(script)
        check(
            f"--changed run, {path}: the count line names the path ({got})",
            got == (0, f"5 of 5 suites passed (group: test) (widened: {path})"),
        )

    touch_on_branch(root, "pyproject.toml", "justfile")
    got = count_line(script)
    check(
        f"two shared paths: the note names the first one in diff order ({got})",
        got == (0, "5 of 5 suites passed (group: test) (widened: justfile)"),
    )

    # A path git quotes when core.quotepath is on must still be seen.
    touch_on_branch(root, "docs/research/other/donn\u00e9e.csv")
    got = count_line(script)
    check(
        f"a non-ASCII unmapped docs/ file widens, naming it unquoted ({got})",
        got
        == (
            0,
            "5 of 5 suites passed (group: test) "
            "(widened: docs/research/other/donn\u00e9e.csv)",
        ),
    )

    # A file moved out of shared code is both a deletion and an addition.
    git(root, "checkout", "-q", "-B", "work", "main")
    git(root, "mv", "finders/hunt/test_h.py", "finders/fake/test_h.py")
    git(root, "commit", "-q", "-m", "move")
    got = count_line(script)
    check(
        f"a rename out of finders/hunt/ widens, naming the old path ({got})",
        got
        == (
            0,
            "5 of 5 suites passed (group: test) (widened: finders/hunt/test_h.py)",
        ),
    )

    # `main` moving on after the branch was cut is not the branch's change.
    touch_on_branch(root, "finders/other-one/test_b.py")
    git(root, "checkout", "-q", "main")
    (root / "justfile").write_text("# main moved\n")
    git(root, "commit", "-q", "-am", "main moves")
    git(root, "checkout", "-q", "work")
    got = listing(script)
    git(root, "checkout", "-q", "main")
    git(root, "reset", "-q", "--hard", "HEAD~1")
    check(
        f"a commit on the base after the branch was cut does not widen it ({got})",
        got == (0, [*LINT, RUNNER, "uv run finders/other-one/test_b.py"]),
    )

    touch_on_branch(root, "docs/research/fake-data/rows.csv")
    got = listing(script)
    check(
        f"a mapped data directory selects that finder only ({got})",
        got == (0, [*LINT, RUNNER, "uv run finders/fake/test_a.py"]),
    )

    # Retired finders' data stays under docs/research/ and maps to no suite.
    touch_on_branch(root, "docs/research/renbanana/CIRCLES.json")
    got = count_line(script)
    check(
        f"data of a retired finder maps to no suite, so it widens ({got})",
        got
        == (
            0,
            "5 of 5 suites passed (group: test) "
            "(widened: docs/research/renbanana/CIRCLES.json)",
        ),
    )

    touch_on_branch(root, "archive/finders/old/test_o.py")
    got = listing(script)
    check(
        f"a change under archive/ selects only lint and the runner's test ({got})",
        got == (0, [*LINT, RUNNER]),
    )

    touch_on_branch(root, "docs/research/other/data.csv")
    got = count_line(script)
    check(
        f"an unmapped non-.md file under docs/ widens, naming the file ({got})",
        got
        == (
            0,
            "5 of 5 suites passed (group: test) "
            "(widened: docs/research/other/data.csv)",
        ),
    )

    touch_on_branch(root, "docs/research/other/notes.md")
    got = listing(script)
    check(
        f"a .md outside the data map is docs only ({got})",
        got == (0, [*LINT, RUNNER]),
    )

    touch_on_branch(root, "docs/note.md", "AGENTS.md", "finders/fake/README.md")
    got = listing(script)
    check(
        "--list --changed, docs only (even a .md inside a finder folder): "
        f"lint and the runner's test ({got})",
        got == (0, [*LINT, RUNNER]),
    )

    touch_on_branch(root, "finders/fake/test_a.py", "docs/note.md")
    got = listing(script)
    check(
        f"--list --changed, a finder folder plus a doc: the folder runs ({got})",
        got == (0, [*LINT, RUNNER, "uv run finders/fake/test_a.py"]),
    )

    git(root, "checkout", "-q", "main")
    got = listing(script)
    check(
        f"--changed with an empty diff: lint and the runner's test ({got})",
        got == (0, [*LINT, RUNNER]),
    )
    r = subprocess.run(
        ["bash", str(script), "--changed", "no-such-ref", "--list"],
        capture_output=True,
        text=True,
    )
    check(
        "--changed with an unknown base is refused, exit 2, naming it",
        r.returncode == 2 and "no-such-ref" in r.stderr and not r.stdout,
    )
    r = subprocess.run(
        ["bash", str(script), "--changed"], capture_output=True, text=True
    )
    check(
        "--changed with no value is refused, exit 2",
        r.returncode == 2 and "--changed needs a value" in r.stderr,
    )

# The real tree: retired finders live under archive/finders/ with a README and
# no suite under archive/ is in the gate.
REPO = ALL.parent.parent
r = subprocess.run(
    ["bash", str(ALL), "--list"], capture_output=True, text=True, cwd=REPO
)
check(
    "the real gate lists no suite under archive/",
    r.returncode == 0 and r.stdout and "archive/" not in r.stdout,
)
RETIRED = (
    "renbanana",
    "banabner",
    "galaxy-copycat",
    "copycat-scan",
    "lmd-hybrid-scan",
)
for name in RETIRED:
    tracked = subprocess.run(
        ["git", "ls-files", f"finders/{name}"],
        capture_output=True,
        text=True,
        cwd=REPO,
    ).stdout
    check(
        f"{name} is archived with a README and no file of it is left in finders/",
        (REPO / "archive" / "finders" / name / "README.md").is_file() and not tracked,
    )

sys.exit(0 if ok else 1)

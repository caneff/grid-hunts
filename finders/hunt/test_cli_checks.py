"""Tests for cli_checks, the shared check/finish/read_jsonl/run_cli helpers.

Run by name: `uv run finders/hunt/test_cli_checks.py`."""

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cli_checks
from subprocess_env import IDLE_LOAD

ok = True


def verify(name, cond):
    """This file's own check: cli_checks is the thing under test, so it is
    not used to judge itself."""
    global ok
    print(f"{'ok' if cond else 'FAIL'}: {name}")
    if not cond:
        ok = False


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    header = f"import sys\nsys.path.insert(0, {str(HERE)!r})\nfrom cli_checks import check, finish\n"

    passing = tmp / "passing.py"
    passing.write_text(header + "check('one', True)\ncheck('two', 1 == 1)\nfinish()\n")
    r = cli_checks.run_cli(passing)
    verify("all checks pass: exit 0", r.returncode == 0)
    verify("a passing check prints `ok: <name>`", r.stdout == "ok: one\nok: two\n")

    failing = tmp / "failing.py"
    failing.write_text(
        header
        + "check('good', True)\ncheck('bad', False)\ncheck('later', True)\nfinish()\n"
    )
    r = cli_checks.run_cli(failing)
    verify("one failing check: exit 1", r.returncode == 1)
    verify(
        "a failing check prints `FAIL: <name>` and later checks still run",
        r.stdout == "ok: good\nFAIL: bad\nok: later\n",
    )

    echo = tmp / "echo.py"
    echo.write_text(
        "import os, sys\n"
        "print(repr(sys.argv[1:]))\n"
        "print(os.environ['HUNT_FAKE_LOAD1'])\n"
    )
    # A parent that is itself busy: the idle value must come from run_cli,
    # not from the environment the test happens to run in.
    os.environ["HUNT_FAKE_LOAD1"] = "99"
    r = cli_checks.run_cli(echo, 4, Path("x"), "s")
    lines = r.stdout.splitlines()
    verify(
        "run_cli passes non-string arguments through str", lines[0] == "['4', 'x', 's']"
    )
    verify("run_cli runs the child with the load gate idle", lines[1] == IDLE_LOAD)
    verify("run_cli returns text output", isinstance(r.stdout, str))

    data = tmp / "d.jsonl"
    data.write_text('{"a": 1}\n\n{"b": 2}\n')
    verify(
        "read_jsonl skips blank lines",
        cli_checks.read_jsonl(data) == [{"a": 1}, {"b": 2}],
    )

sys.exit(0 if ok else 1)

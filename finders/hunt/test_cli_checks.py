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

    r = cli_checks.run_cli(echo, env={"HUNT_FAKE_LOAD1": "25"})
    verify(
        "run_cli's env overrides reach the child (a test of the load gate)",
        r.stdout.splitlines()[1] == "25",
    )

    exits = tmp / "exits.py"
    exits.write_text(
        "import sys\nprint('hunt: refusing -- reason X', file=sys.stderr)\n"
        "sys.exit(int(sys.argv[1]))\n"
    )
    seen = []
    cli_checks.check = lambda name, cond: seen.append((name, cond))
    cli_checks.check_refusal(
        "exit 2 with the text", cli_checks.run_cli(exits, 2), "reason X"
    )
    cli_checks.check_refusal(
        "exit 1 with the text", cli_checks.run_cli(exits, 1), "reason X"
    )
    cli_checks.check_refusal(
        "exit 2 with other text", cli_checks.run_cli(exits, 2), "reason Y"
    )
    cli_checks.check_refusal("exit 0", cli_checks.run_cli(exits, 0), "reason X")
    verify(
        "check_refusal passes only on exit 2 with the text on stderr",
        [c for _, c in seen] == [True, False, False, False],
    )
    verify(
        "check_refusal's check names the given name and shows stderr",
        seen[0][0].startswith("exit 2 with the text") and "reason X" in seen[0][0],
    )

    data = tmp / "d.jsonl"
    data.write_text('{"a": 1}\n\n{"b": 2}\n')
    verify(
        "read_jsonl skips blank lines",
        cli_checks.read_jsonl(data) == [{"a": 1}, {"b": 2}],
    )
    verify(
        "read_jsonl of a missing file is [] only with missing_ok",
        cli_checks.read_jsonl(tmp / "nope.jsonl", missing_ok=True) == [],
    )

sys.exit(0 if ok else 1)

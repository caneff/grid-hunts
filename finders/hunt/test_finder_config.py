"""A finder's own config and an empty seed's reason, black-box on the `hunt`
CLI (#491, forced by the qqrr pilot finder).

A real finder has knobs of its own -- which board, which corner, how long a
solve may take -- that the driver's argv does not name. The finder hands them
to the driver as `finder.config`; run.json records it, and a resume under a
different config refuses rather than mixing two searches in one directory.
A seed that finds nothing can say why (`protocol.Empty`), so a solver's
timeout and its proof of infeasibility stay apart in progress.jsonl.

    uv run finders/hunt/test_finder_config.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from subprocess_env import success_env

HERE = Path(__file__).resolve().parent
CONFIG_FINDER = HERE / "toy_config_finder.py"

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def run_cli(out, seeds, *extra):
    return subprocess.run(
        [
            sys.executable,
            str(CONFIG_FINDER),
            "--out",
            str(out),
            f"--seeds={seeds}",
            *extra,
        ],
        capture_output=True,
        text=True,
        env=success_env(),
    )


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "hunt"
    r = run_cli(out, "0:40", "--parity", "odd")
    check("fresh hunt with a finder config exits 0", r.returncode == 0)
    run_json = json.loads((out / "run.json").read_text())
    check(
        "run.json records the finder's config",
        run_json.get("config") == {"parity": "odd"},
    )
    examples = read_jsonl(out / "examples.jsonl")
    check(
        "the config reached the finder (every example has an odd count)",
        examples and all(sum(e["grid"]) % 2 == 1 for e in examples),
    )

    # Every resume that goes ahead rewrites summary.json, even over a range
    # already done, so its absence afterwards is what shows nothing ran.
    (out / "summary.json").unlink()
    before = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
    r = run_cli(out, "0:40", "--parity", "even")
    check("resume under a different config refuses (exit 2)", r.returncode == 2)
    check("the refusal names the config", "config" in r.stderr)
    after = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
    check("a refused resume writes nothing", before == after)

    r = run_cli(out, "0:40", "--parity", "odd")
    check("resume under the same config exits 0", r.returncode == 0)

with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "hunt"
    r = run_cli(out, "0:40", "--parity", "odd")
    events = read_jsonl(out / "progress.jsonl")
    empties = [e for e in events if e["outcome"] == "empty"]
    check("some seeds come back empty", len(empties) > 0)
    check(
        "an empty seed's reason lands on its progress event",
        all(e.get("empty_reason") == "toy: nothing this seed" for e in empties),
    )
    summary = json.loads((out / "summary.json").read_text())
    check("summary.json counts empty seeds", summary["empty"] == len(empties))
    others = [e for e in events if e["outcome"] != "empty"]
    check(
        "a non-empty seed carries no empty_reason",
        others and not any("empty_reason" in e for e in others),
    )

sys.exit(0 if ok else 1)

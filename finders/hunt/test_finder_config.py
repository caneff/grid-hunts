"""Pins a finder's `config`: run.json records it, the finder receives it, a resume under another config refuses, and `Empty()` needs a reason."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_checks import check, check_refusal, finish, read_jsonl, run_cli

HERE = Path(__file__).resolve().parent
CONFIG_FINDER = HERE / "toy_config_finder.py"


def config_hunt(out, seeds, *extra):
    return run_cli(CONFIG_FINDER, "--out", out, f"--seeds={seeds}", *extra)


with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "hunt"
    r = config_hunt(out, "0:40", "--parity", "odd")
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
    r = config_hunt(out, "0:40", "--parity", "even")
    check_refusal("resume under a different config refuses", r, "finder config differs")
    after = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
    check("a refused resume writes nothing", before == after)

    r = config_hunt(out, "0:40", "--parity", "odd")
    check("resume under the same config exits 0", r.returncode == 0)

with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "hunt"
    r = config_hunt(out, "0:40", "--parity", "odd")
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

from protocol import Empty

try:
    Empty()
    reasonless = True
except TypeError:
    reasonless = False
check("Empty() with no reason is refused", not reasonless)

finish()

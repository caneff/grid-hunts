"""Box-safe defaults for the hunt CLI: `--workers` and the load gate (#488).

Black-box through the `hunt` CLI in a subprocess, same style as
test_toy_hunt.py: exit codes and output files only, never an internal of
driver.py. A finder that records `self.workers` into its own output is how
"the finder receives N" is observed from outside. The 1-minute load is
injected via the `HUNT_FAKE_LOAD1` env var rather than a CLI flag, so
production argv never carries a test-only knob.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_checks import check, check_refusal, finish, run_cli

HERE = Path(__file__).resolve().parent

WORKERS_FINDER = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict

class WorkersFinder:
    def propose(self, rng):
        return (0,)

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"workers": self.workers}}

    def key(self, candidate):
        return candidate

sys.exit(run(WorkersFinder(), sys.argv[1:]))
"""

_script_dir = tempfile.TemporaryDirectory()
WORKERS_SCRIPT = Path(_script_dir.name) / "workers_finder.py"
WORKERS_SCRIPT.write_text(WORKERS_FINDER)


def workers_hunt(out, extra_args, env=None):
    return run_cli(WORKERS_SCRIPT, "--out", out, "--seeds", "0:1", *extra_args, env=env)


with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = workers_hunt(out, [])
    check(
        f"no --workers exits 0 (stderr: {result.stderr[-500:]})", result.returncode == 0
    )
    examples = [
        json.loads(line)
        for line in (out / "examples.jsonl").read_text().splitlines()
        if line
    ]
    check("without --workers, the finder receives 3", examples[0]["workers"] == 3)

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = workers_hunt(out, ["--workers", "8"])
    check(
        f"--workers 8 exits 0 (stderr: {result.stderr[-500:]})", result.returncode == 0
    )
    examples = [
        json.loads(line)
        for line in (out / "examples.jsonl").read_text().splitlines()
        if line
    ]
    check("--workers 8 passes 8 to the finder", examples[0]["workers"] == 8)

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = workers_hunt(out, [], env={"HUNT_FAKE_LOAD1": "25"})
    check_refusal("load 25 refuses", result, "is above 24")
    check("load 25 refuses before any seed runs", not (out / "progress.jsonl").exists())

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = workers_hunt(out, ["--force-load"], env={"HUNT_FAKE_LOAD1": "25"})
    check(
        f"load 25 with --force-load exits 0 (stderr: {result.stderr[-500:]})",
        result.returncode == 0,
    )
    check("load 25 with --force-load runs the seed", (out / "progress.jsonl").exists())

with tempfile.TemporaryDirectory() as tmp:
    # A box-safety flag added on resume must not read as a differing search
    # (#487's argv-equality check), or the gate's "use --force-load" advice
    # is advice resume then refuses to take.
    out = Path(tmp) / "hunt-out"
    first = workers_hunt(out, [])
    check(f"base hunt exits 0 (stderr: {first.stderr[-500:]})", first.returncode == 0)
    resumed = workers_hunt(out, ["--force-load"])
    check(
        f"resuming with --force-load added is not an argv mismatch "
        f"(stderr: {resumed.stderr[-500:]})",
        resumed.returncode == 0,
    )

with tempfile.TemporaryDirectory() as tmp:
    # An exported-but-empty HUNT_FAKE_LOAD1 (the ordinary shape of
    # `export HUNT_FAKE_LOAD1=$X` with X unset) is not an override -- it
    # must read as "no override", never crash. Empty falls through to the
    # real box load, so compare against a run with the var unset (`None`
    # deletes the key, see subprocess_env.success_env), not a fixed exit
    # code.
    out = Path(tmp) / "hunt-out"
    result = workers_hunt(out, [], env={"HUNT_FAKE_LOAD1": ""})
    ref_out = Path(tmp) / "hunt-out-unset"
    reference = workers_hunt(ref_out, [], env={"HUNT_FAKE_LOAD1": None})
    check(
        f"empty HUNT_FAKE_LOAD1 does not crash (stderr: {result.stderr[-500:]})",
        "Traceback" not in result.stderr,
    )
    check(
        "empty HUNT_FAKE_LOAD1 behaves exactly like no override at all "
        f"(exit {result.returncode} vs {reference.returncode})",
        result.returncode == reference.returncode,
    )

with tempfile.TemporaryDirectory() as tmp:
    # A non-numeric override is a broken test setup, not a real load --
    # refuse cleanly rather than an uncaught traceback.
    out = Path(tmp) / "hunt-out"
    result = workers_hunt(out, [], env={"HUNT_FAKE_LOAD1": "not-a-number"})
    check_refusal(
        "non-numeric HUNT_FAKE_LOAD1 refuses cleanly", result, "is not a valid load"
    )
    check("and prints no traceback", "Traceback" not in result.stderr)

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = workers_hunt(out, [], env={"HUNT_FAKE_LOAD1": "24"})
    check(
        f"load exactly 24 runs (stderr: {result.stderr[-500:]})",
        result.returncode == 0,
    )

with tempfile.TemporaryDirectory() as tmp:
    # --workers 0 would hand a CP-SAT finder "pick automatically": the
    # whole box.
    out = Path(tmp) / "hunt-out"
    result = workers_hunt(out, ["--workers", "0"])
    check_refusal("--workers 0 refuses", result, "--workers must be at least 1, got 0")

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = workers_hunt(out, ["--workers", "-1"])
    check_refusal(
        "--workers -1 refuses", result, "--workers must be at least 1, got -1"
    )

with tempfile.TemporaryDirectory() as tmp:
    # `nan` parses as a float and `nan > LOAD_LIMIT` is False, so the naive
    # comparison lets a hunt start unconditionally regardless of the real
    # box load. A negative override is equally
    # nonsensical and must not silently pass the gate either.
    out = Path(tmp) / "hunt-out"
    result = workers_hunt(out, [], env={"HUNT_FAKE_LOAD1": "nan"})
    check_refusal(
        "HUNT_FAKE_LOAD1=nan refuses instead of bypassing the gate",
        result,
        "'nan' is not a valid load",
    )

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = workers_hunt(out, [], env={"HUNT_FAKE_LOAD1": "-1"})
    check_refusal("HUNT_FAKE_LOAD1=-1 refuses", result, "'-1' is not a valid load")

finish()

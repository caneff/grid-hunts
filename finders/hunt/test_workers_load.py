"""Box-safe defaults for the hunt CLI: `--workers` and the load gate (#488).

Black-box through the `hunt` CLI in a subprocess, same style as
test_toy_hunt.py: exit codes and output files only, never an internal of
driver.py. A finder that records `self.workers` into its own output is how
"the finder receives N" is observed from outside. The 1-minute load is
injected via the `HUNT_FAKE_LOAD1` env var rather than a CLI flag, so
production argv never carries a test-only knob.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from subprocess_env import success_env

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

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def run_cli(out, extra_args, env=None):
    full_env = success_env(env)
    return subprocess.run(
        [
            sys.executable,
            "-c",
            WORKERS_FINDER,
            "--out",
            str(out),
            "--seeds",
            "0:1",
            *extra_args,
        ],
        capture_output=True,
        text=True,
        env=full_env,
    )


with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = run_cli(out, [])
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
    result = run_cli(out, ["--workers", "8"])
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
    result = run_cli(out, [], env={"HUNT_FAKE_LOAD1": "25"})
    check(
        f"load 25 exits nonzero (stderr: {result.stderr[-500:]})",
        result.returncode != 0,
    )
    check("load 25 refuses before any seed runs", not (out / "progress.jsonl").exists())

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = run_cli(out, ["--force-load"], env={"HUNT_FAKE_LOAD1": "25"})
    check(
        f"load 25 with --force-load exits 0 (stderr: {result.stderr[-500:]})",
        result.returncode == 0,
    )
    check("load 25 with --force-load runs the seed", (out / "progress.jsonl").exists())

with tempfile.TemporaryDirectory() as tmp:
    # A box-safety flag added on resume must not read as a differing search
    # (#488 review C1/P2): the box's load, not the search, changed between
    # the two invocations, and #487's argv-equality resume check must not
    # conflate the two -- otherwise the gate's own "use --force-load" advice
    # is advice resume then refuses to take.
    out = Path(tmp) / "hunt-out"
    first = run_cli(out, [])
    check(f"base hunt exits 0 (stderr: {first.stderr[-500:]})", first.returncode == 0)
    resumed = run_cli(out, ["--force-load"])
    check(
        f"resuming with --force-load added is not an argv mismatch "
        f"(stderr: {resumed.stderr[-500:]})",
        resumed.returncode == 0,
    )

with tempfile.TemporaryDirectory() as tmp:
    # A genuine search-space change (--seeds) must still refuse -- box-safety
    # flags are excluded from the resume comparison, not argv equality itself.
    out = Path(tmp) / "hunt-out"
    first = run_cli(out, [])
    check(
        f"base hunt for genuine-mismatch check exits 0 (stderr: {first.stderr[-500:]})",
        first.returncode == 0,
    )
    mismatched = subprocess.run(
        [sys.executable, "-c", WORKERS_FINDER, "--out", str(out), "--seeds", "0:5"],
        capture_output=True,
        text=True,
        env=success_env(),
    )
    check(
        "a genuinely differing --seeds still refuses",
        mismatched.returncode != 0,
    )

with tempfile.TemporaryDirectory() as tmp:
    # An exported-but-empty HUNT_FAKE_LOAD1 (the ordinary shape of
    # `export HUNT_FAKE_LOAD1=$X` with X unset) is not an override -- it
    # must read as "no override", never crash (#488 review C2). "No
    # override" itself falls through to the real box's load (driver.py's
    # `if not override`), so it can't be pinned to a fixed exit code the
    # way every other case here is (#526 review C1/S1/P1) -- it's compared
    # against a reference call with the var truly unset (`None` deletes the
    # key -- see subprocess_env.success_env) instead, so both sides see the
    # same real load and the check holds however busy the box is.
    out = Path(tmp) / "hunt-out"
    result = run_cli(out, [], env={"HUNT_FAKE_LOAD1": ""})
    ref_out = Path(tmp) / "hunt-out-unset"
    reference = run_cli(ref_out, [], env={"HUNT_FAKE_LOAD1": None})
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
    # refuse cleanly rather than an uncaught traceback (#488 review C2).
    out = Path(tmp) / "hunt-out"
    result = run_cli(out, [], env={"HUNT_FAKE_LOAD1": "not-a-number"})
    check(
        f"non-numeric HUNT_FAKE_LOAD1 refuses cleanly, no traceback "
        f"(stderr: {result.stderr[-500:]})",
        result.returncode == 2 and "Traceback" not in result.stderr,
    )

with tempfile.TemporaryDirectory() as tmp:
    # LOAD_LIMIT's boundary: exactly 24 must run (refusal is "above 24").
    out = Path(tmp) / "hunt-out"
    result = run_cli(out, [], env={"HUNT_FAKE_LOAD1": "24"})
    check(
        f"load exactly 24 runs (stderr: {result.stderr[-500:]})",
        result.returncode == 0,
    )

with tempfile.TemporaryDirectory() as tmp:
    # --workers 0 would hand a CP-SAT finder "pick automatically" -- the
    # whole box, the exact failure this ticket exists to prevent
    # (#488 review C3).
    out = Path(tmp) / "hunt-out"
    result = run_cli(out, ["--workers", "0"])
    check(
        f"--workers 0 refuses (stderr: {result.stderr[-500:]})",
        result.returncode != 0,
    )

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = run_cli(out, ["--workers", "-1"])
    check(
        f"--workers -1 refuses (stderr: {result.stderr[-500:]})",
        result.returncode != 0,
    )

with tempfile.TemporaryDirectory() as tmp:
    # `nan` parses as a float and `nan > LOAD_LIMIT` is False, so the naive
    # comparison lets a hunt start unconditionally regardless of the real
    # box load (Codex pass 1, PR 520). A negative override is equally
    # nonsensical and must not silently pass the gate either.
    out = Path(tmp) / "hunt-out"
    result = run_cli(out, [], env={"HUNT_FAKE_LOAD1": "nan"})
    check(
        f"HUNT_FAKE_LOAD1=nan refuses instead of bypassing the gate "
        f"(stderr: {result.stderr[-500:]})",
        result.returncode != 0,
    )

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = run_cli(out, [], env={"HUNT_FAKE_LOAD1": "-1"})
    check(
        f"HUNT_FAKE_LOAD1=-1 refuses (stderr: {result.stderr[-500:]})",
        result.returncode != 0,
    )

sys.exit(0 if ok else 1)

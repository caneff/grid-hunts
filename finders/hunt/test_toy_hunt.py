"""A fresh toy hunt through the `hunt` CLI, black-box (#484).

Runs finders/hunt/toy_finder.py as a subprocess and checks only what a
caller of the hunt CLI can see: exit code, the four output files, and their
contents -- never an internal of driver.py or toy_finder.py.

    uv run finders/hunt/test_toy_hunt.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedupe import D4, canonical_key

HERE = Path(__file__).resolve().parent
TOY_FINDER = HERE / "toy_finder.py"

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "hunt-out"
    result = subprocess.run(
        [sys.executable, str(TOY_FINDER), "--out", str(out), "--seeds", "0:200"],
        capture_output=True,
        text=True,
    )
    check(f"exit code 0 (stderr: {result.stderr[-500:]})", result.returncode == 0)

    for name in ("examples.jsonl", "summary.json", "progress.jsonl", "run.json"):
        check(f"{name} was written", (out / name).exists())

    examples = [
        json.loads(line)
        for line in (out / "examples.jsonl").read_text().splitlines()
        if line
    ]
    summary = json.loads((out / "summary.json").read_text())
    run_info = json.loads((out / "run.json").read_text())
    progress = [
        json.loads(line)
        for line in (out / "progress.jsonl").read_text().splitlines()
        if line
    ]

    check(
        "summary.json's example count matches examples.jsonl's line count",
        summary.get("examples") == len(examples),
    )
    check(
        "run.json records the argv used",
        run_info.get("argv") == ["--out", str(out), "--seeds", "0:200"],
    )
    check(
        "progress.jsonl has one seed_done event per seed in the range",
        sum(1 for e in progress if e.get("event") == "seed_done") == 200,
    )

    # Toy finder's own trivial verifier rejects an odd shading count -- see
    # toy_finder.py. A candidate it rejects must be absent from
    # examples.jsonl: recheck the rule ourselves against every line written.
    all_even = all(sum(ex["grid"]) % 2 == 0 for ex in examples)
    check("no rejected (odd-count) candidate reached examples.jsonl", all_even)

    check(
        "at least one example was found over 200 seeds",
        len(examples) > 0,
    )

    keys = [canonical_key(tuple(ex["grid"]), D4) for ex in examples]
    check("no two examples are equal under D4", len(keys) == len(set(keys)))

    # A fresh hunt only: rerunning on the same --out must refuse rather than
    # silently mix in more output (dedupe isn't reloaded across runs; #487
    # is where a real resume makes that safe).
    rerun = subprocess.run(
        [sys.executable, str(TOY_FINDER), "--out", str(out), "--seeds", "0:5"],
        capture_output=True,
        text=True,
    )
    check("rerunning on the same --out refuses (nonzero exit)", rerun.returncode != 0)
    check(
        "a refused rerun leaves examples.jsonl untouched",
        len(
            [line for line in (out / "examples.jsonl").read_text().splitlines() if line]
        )
        == len(examples),
    )

with tempfile.TemporaryDirectory() as tmp:
    # Two processes racing on the same fresh --out must not both start: the
    # existence check alone has a TOCTOU window, so this launches both
    # without waiting between them and lets the OS-level exclusive create
    # decide the winner (#507 review).
    out = Path(tmp) / "hunt-out"
    procs = [
        subprocess.Popen(
            [sys.executable, str(TOY_FINDER), "--out", str(out), "--seeds", "0:50"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for _ in range(2)
    ]
    for p in procs:
        p.communicate()
    exit_codes = sorted(p.returncode for p in procs)
    check(
        f"racing on a fresh --out: exactly one wins (exit codes {exit_codes})",
        exit_codes == [0, 2],
    )
    examples = [
        json.loads(line)
        for line in (out / "examples.jsonl").read_text().splitlines()
        if line
    ]
    summary = json.loads((out / "summary.json").read_text())
    check(
        "the loser's seeds never reached the winner's output",
        summary.get("seeds_done") == 50 and summary.get("examples") == len(examples),
    )

with tempfile.TemporaryDirectory() as tmp:
    # An empty seed range is a completed hunt that found nothing, not an
    # error: all four files must still exist, summary.json's counts zero.
    out = Path(tmp) / "hunt-out"
    result = subprocess.run(
        [sys.executable, str(TOY_FINDER), "--out", str(out), "--seeds", "5:5"],
        capture_output=True,
        text=True,
    )
    check(
        f"empty range exits 0 (stderr: {result.stderr[-500:]})", result.returncode == 0
    )
    for name in ("examples.jsonl", "summary.json", "progress.jsonl", "run.json"):
        check(f"empty range still writes {name}", (out / name).exists())
    summary = json.loads((out / "summary.json").read_text())
    check(
        "empty range's summary.json has zero seeds_done and examples",
        summary.get("seeds_done") == 0 and summary.get("examples") == 0,
    )

with tempfile.TemporaryDirectory() as tmp:
    # A finder whose declared symmetry group isn't closed under composition
    # ([identity, rotate90] on a 2x2 board is missing rotate180 and
    # rotate270) must be refused before any output file exists (#508) --
    # not partway through the seed loop, on the first candidate that
    # reaches canonical_key.
    out = Path(tmp) / "hunt-out"
    bad_finder_script = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict

class PartialGroupFinder:
    symmetry = [(0, 1, 2, 3), (1, 3, 0, 2)]

    def propose(self, rng):
        return (0, 0, 0, 0)

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate)}}

    def key(self, candidate):
        return candidate

sys.exit(run(PartialGroupFinder(), sys.argv[1:]))
"""
    result = subprocess.run(
        [sys.executable, "-c", bad_finder_script, "--out", str(out), "--seeds", "0:5"],
        capture_output=True,
        text=True,
    )
    # Exact code 2 and the refusal message, not just "nonzero" -- an
    # unrelated crash (an uncaught exception exits 1 with a traceback) would
    # also satisfy a bare nonzero check without proving the pre-flight gate
    # ran at all (#508 review).
    check(
        f"a finder with a partial symmetry group exits 2 (stderr: "
        f"{result.stderr[-300:]})",
        result.returncode == 2,
    )
    check(
        "the refusal names the invalid symmetry group",
        "invalid symmetry group" in result.stderr,
    )
    check(
        "a finder with a partial symmetry group writes nothing",
        not out.exists(),
    )

with tempfile.TemporaryDirectory() as tmp:
    # A typo'd string symmetry (e.g. "d4" instead of dedupe.D4) must not
    # slip past the pre-flight gate: the old `isinstance(symmetry, str)`
    # dispatch treated every string as a built-in group and let it reach
    # `canonical_key` uncaught mid-loop, after output already existed
    # (#508 review).
    out = Path(tmp) / "hunt-out"
    typo_finder_script = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict

class TypoSymmetryFinder:
    symmetry = "d4"

    def propose(self, rng):
        return (0, 0, 0, 0)

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate)}}

    def key(self, candidate):
        return candidate

sys.exit(run(TypoSymmetryFinder(), sys.argv[1:]))
"""
    result = subprocess.run(
        [sys.executable, "-c", typo_finder_script, "--out", str(out), "--seeds", "0:5"],
        capture_output=True,
        text=True,
    )
    check(
        f"a typo'd string symmetry exits 2 (stderr: {result.stderr[-300:]})",
        result.returncode == 2,
    )
    check(
        "a typo'd string symmetry writes nothing",
        not out.exists(),
    )

sys.exit(0 if ok else 1)

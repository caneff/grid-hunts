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
from subprocess_env import success_env

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
        env=success_env(),
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

    # A completed hunt is a run.json-bearing --out, so rerunning it goes
    # through the resume path (#487) -- and a differing --seeds is a
    # differing argv, which that path refuses rather than silently mixing
    # in output under a range the recorded run never agreed to. See
    # test_hunt_resume.py for resuming with the *same* argv.
    rerun = subprocess.run(
        [sys.executable, str(TOY_FINDER), "--out", str(out), "--seeds", "0:5"],
        capture_output=True,
        text=True,
        env=success_env(),
    )
    check(
        "rerunning with a differing --seeds refuses (nonzero exit)",
        rerun.returncode != 0,
    )
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
            env=success_env(),
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
        env=success_env(),
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
        env=success_env(),
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
        env=success_env(),
    )
    check(
        f"a typo'd string symmetry exits 2 (stderr: {result.stderr[-300:]})",
        result.returncode == 2,
    )
    check(
        "a typo'd string symmetry writes nothing",
        not out.exists(),
    )

with tempfile.TemporaryDirectory() as tmp:
    # A structurally valid, closed custom group (#511's own checks all pass)
    # whose maps are simply the wrong length for the finder's real key()
    # must not reach canonical_key uncaught mid-loop, after run.json and
    # summary.json already exist (#509). `validate_group`'s pre-flight
    # derives n from the group's own maps (4 here) and never sees the
    # finder's actual 9-cell key, so it passes cleanly -- the mismatch only
    # surfaces inside canonical_key on the first verified candidate.
    out = Path(tmp) / "hunt-out"
    mismatched_length_script = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict

class MismatchedLengthFinder:
    symmetry = [(0, 1, 2, 3), (1, 3, 0, 2), (2, 0, 3, 1), (3, 2, 1, 0)]

    def propose(self, rng):
        return (0,) * 9

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate)}}

    def key(self, candidate):
        return candidate

sys.exit(run(MismatchedLengthFinder(), sys.argv[1:]))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            mismatched_length_script,
            "--out",
            str(out),
            "--seeds",
            "0:5",
        ],
        capture_output=True,
        text=True,
        env=success_env(),
    )
    check(
        f"a symmetry group whose map length doesn't match key() exits 2 "
        f"(stderr: {result.stderr[-300:]})",
        result.returncode == 2,
    )
    check(
        "the refusal names the length mismatch",
        "a custom cell map must be a permutation of range(9), got (0, 1, 2, 3)"
        in result.stderr,
    )
    check(
        "a mismatched-length symmetry group leaves only .lock behind (#519, "
        "see driver.py's _cleanup_partial_output)",
        out.exists() and {p.name for p in out.iterdir()} == {".lock"},
    )

with tempfile.TemporaryDirectory() as tmp:
    # A generator-typed `symmetry` is a second shape of the same bug: the
    # pre-flight's `list(maps)` drains it during validation, so the *same*
    # exhausted generator object reaches canonical_key's custom-group path
    # on the first verified candidate and fails "must not be empty" --
    # with output already on disk, same as the length mismatch above (noted
    # on #509: "the fix this ticket lands should cover both").
    out = Path(tmp) / "hunt-out"
    generator_symmetry_script = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict

class GeneratorSymmetryFinder:
    symmetry = (m for m in [(0, 1, 2, 3), (1, 3, 0, 2), (2, 0, 3, 1), (3, 2, 1, 0)])

    def propose(self, rng):
        return (0, 0, 0, 0)

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate)}}

    def key(self, candidate):
        return candidate

sys.exit(run(GeneratorSymmetryFinder(), sys.argv[1:]))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            generator_symmetry_script,
            "--out",
            str(out),
            "--seeds",
            "0:5",
        ],
        capture_output=True,
        text=True,
        env=success_env(),
    )
    check(
        f"a generator-typed symmetry group exits 2 (stderr: {result.stderr[-300:]})",
        result.returncode == 2,
    )
    check(
        "the refusal names the exhausted-generator failure",
        "must not be empty" in result.stderr,
    )
    check(
        "a generator-typed symmetry group leaves only .lock behind (#519, "
        "see driver.py's _cleanup_partial_output)",
        out.exists() and {p.name for p in out.iterdir()} == {".lock"},
    )

with tempfile.TemporaryDirectory() as tmp:
    # A ValueError raised by the finder's own key() -- nothing to do with
    # the symmetry group -- must not be relabelled a symmetry failure and
    # must not have its output silently removed: finder.key() is called
    # outside the try that catches canonical_key's ValueError (#509 review,
    # finding P1).
    out = Path(tmp) / "hunt-out"
    finder_bug_script = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict

class FinderOwnBugFinder:
    symmetry = [(0, 1, 2, 3), (1, 3, 0, 2), (2, 0, 3, 1), (3, 2, 1, 0)]

    def propose(self, rng):
        return (0, 0, 0, 0)

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate)}}

    def key(self, candidate):
        raise ValueError("finder's own bug: bad int literal")

sys.exit(run(FinderOwnBugFinder(), sys.argv[1:]))
"""
    result = subprocess.run(
        [sys.executable, "-c", finder_bug_script, "--out", str(out), "--seeds", "0:5"],
        capture_output=True,
        text=True,
        env=success_env(),
    )
    check(
        "a finder's own ValueError from key() is not relabelled an invalid "
        f"symmetry group (stderr: {result.stderr[-300:]})",
        "invalid symmetry group" not in result.stderr,
    )
    check(
        "a finder's own ValueError from key() still surfaces (nonzero exit)",
        result.returncode != 0,
    )

with tempfile.TemporaryDirectory() as tmp:
    # The built-in D4 group raising on a non-square grid is a separate,
    # out-of-scope bug (#509 is about custom groups only) -- it must not be
    # caught and relabelled "invalid symmetry group" (#509 review, C3).
    out = Path(tmp) / "hunt-out"
    d4_mismatch_script = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict

class NonSquareD4Finder:
    def propose(self, rng):
        return (0,) * 6

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate)}}

    def key(self, candidate):
        return candidate

sys.exit(run(NonSquareD4Finder(), sys.argv[1:]))
"""
    result = subprocess.run(
        [sys.executable, "-c", d4_mismatch_script, "--out", str(out), "--seeds", "0:5"],
        capture_output=True,
        text=True,
        env=success_env(),
    )
    check(
        "a non-square grid under the built-in D4 group is not relabelled "
        f"an invalid symmetry group (stderr: {result.stderr[-300:]})",
        "invalid symmetry group" not in result.stderr,
    )
    check(
        "D4 needs a square grid still surfaces its own message",
        "D4 needs a square grid" in result.stderr,
    )

with tempfile.TemporaryDirectory() as tmp:
    # A --out that already holds content this run didn't write (and that
    # isn't one of the four hunt output files) must survive a symmetry
    # refusal: cleanup removes only what this run itself may have created,
    # never a blanket rmtree of the whole directory (#509 review, C1).
    out = Path(tmp) / "hunt-out"
    out.mkdir()
    sentinel = out / "notes.txt"
    sentinel.write_text("unrelated content the driver never wrote\n")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            mismatched_length_script,
            "--out",
            str(out),
            "--seeds",
            "0:5",
        ],
        capture_output=True,
        text=True,
        env=success_env(),
    )
    check(
        f"a mismatched-length refusal into a --out holding unrelated content "
        f"still exits 2 (stderr: {result.stderr[-300:]})",
        result.returncode == 2,
    )
    check(
        "unrelated content in --out survives the cleanup",
        sentinel.exists()
        and sentinel.read_text() == "unrelated content the driver never wrote\n",
    )
    check(
        "the hunt's own output files are still removed from --out",
        not (out / "run.json").exists() and not (out / "summary.json").exists(),
    )
    check(
        "--out/.lock survives the cleanup (#519): unlinking it here while "
        "this process's own finally block still holds its flock would let "
        "a second process's fresh .lock (a new inode, same path) be locked "
        "while this process is still inside its own now-meaningless unlock",
        (out / ".lock").exists(),
    )

with tempfile.TemporaryDirectory() as tmp:
    # A symmetry mismatch that surfaces on a *resume*, not a fresh hunt,
    # must not delete a prior attempt's genuine completed results -- only
    # this attempt's own output, if any (#509 review, finding V1). Hand-
    # built the same way test_hunt_resume.py hand-corrupts its resume
    # fixtures: a completed, confirmed seed 0 (matching progress.jsonl and
    # examples.jsonl, the way an uninterrupted prior run would leave them)
    # and an untouched seed 1, so resuming over the same 2-seed range must
    # reprocess only seed 1 -- with a finder whose key() no longer matches
    # the declared group.
    out = Path(tmp) / "hunt-out"
    out.mkdir()
    argv = ["--out", str(out), "--seeds", "0:2"]
    (out / "run.json").write_text(
        json.dumps(
            {
                "argv": argv,
                "git_sha": "0" * 40,
                "start_time": "2026-01-01T00:00:00+00:00",
            }
        )
    )
    (out / "progress.jsonl").write_text(
        json.dumps({"event": "seed_done", "seed": 0, "outcome": "example"}) + "\n"
    )
    base_examples = (
        json.dumps({"grid": [0, 1, 2, 3], "__dedupe_key__": [0, 1, 2, 3]}) + "\n"
    )
    (out / "examples.jsonl").write_text(base_examples)
    (out / "summary.json").write_text(
        json.dumps(
            {"seeds_done": 1, "examples": 1, "rejected": 0, "duplicates": 0, "empty": 0}
        )
    )

    resumed = subprocess.run(
        [sys.executable, "-c", mismatched_length_script, *argv],
        capture_output=True,
        text=True,
        env=success_env(),
    )
    check(
        f"resuming into a symmetry mismatch still exits 2 (stderr: "
        f"{resumed.stderr[-300:]})",
        resumed.returncode == 2,
    )
    check(
        "the prior run's genuine example survives a resume-time symmetry mismatch",
        out.exists() and (out / "examples.jsonl").read_text() == base_examples,
    )
    check(
        "run.json from the base hunt is left in place, not deleted",
        (out / "run.json").exists(),
    )

with tempfile.TemporaryDirectory() as tmp:
    # Skipping cleanup on resume isn't enough on its own: `_resume` would
    # otherwise reconcile (trimming an orphaned example) and rewrite
    # summary.json *before* the loop ever reaches a seed's key, mutating
    # those files ahead of a SymmetryMismatch raised deep inside the loop
    # (#509 Codex pass 1, finding 1). #525 moves the symmetry check ahead
    # of reconciliation and any write instead, so nothing needs restoring
    # -- this test proves that by orphaning an example and checking every
    # hunt file is still exactly what the base hunt produced. Built via a
    # genuine base hunt (not hand-crafted files) so run.json/summary.json/
    # progress.jsonl/examples.jsonl are exactly what the driver itself
    # would produce, then progress.jsonl is truncated to orphan the one
    # example -- forcing reconciliation to actually want to trim
    # examples.jsonl and rewrite summary.json on the next invocation, if
    # the symmetry check didn't refuse first.
    out = Path(tmp) / "hunt-out"
    valid_script = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict

class ValidGroupFinder:
    symmetry = [(0, 1, 2, 3), (1, 3, 0, 2), (2, 0, 3, 1), (3, 2, 1, 0)]

    def propose(self, rng):
        return (0, 1, 2, 3)

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate)}}

    def key(self, candidate):
        return candidate

sys.exit(run(ValidGroupFinder(), sys.argv[1:]))
"""
    base = subprocess.run(
        [sys.executable, "-c", valid_script, "--out", str(out), "--seeds", "0:1"],
        capture_output=True,
        text=True,
        env=success_env(),
    )
    check(
        f"base hunt for the byte-for-byte-unchanged test exits 0 (stderr: "
        f"{base.stderr[-300:]})",
        base.returncode == 0,
    )

    (out / "progress.jsonl").write_bytes(b"")  # orphan the one example

    snapshot = {
        name: (out / name).read_bytes()
        for name in ("run.json", "summary.json", "progress.jsonl", "examples.jsonl")
        if (out / name).exists()
    }

    resumed = subprocess.run(
        [
            sys.executable,
            "-c",
            mismatched_length_script,
            "--out",
            str(out),
            "--seeds",
            "0:1",
        ],
        capture_output=True,
        text=True,
        env=success_env(),
    )
    check(
        f"resuming an orphan-example hunt into a symmetry mismatch still "
        f"exits 2 (stderr: {resumed.stderr[-300:]})",
        resumed.returncode == 2,
    )
    check(
        "every hunt file is still byte-for-byte what the base hunt wrote "
        "-- the symmetry check refused before reconciliation could rewrite "
        "anything",
        all(
            (out / name).exists() and (out / name).read_bytes() == content
            for name, content in snapshot.items()
        ),
    )

with tempfile.TemporaryDirectory() as tmp:
    # #525 review, C2/P1: the symmetry probe must check the seeds
    # reconciliation will *actually* leave un-done, not a raw read of
    # progress.jsonl -- reconciliation can un-done a seed progress.jsonl
    # claims is finished (its example never made it to examples.jsonl), and
    # a probe using the raw set skips exactly that seed, checks a
    # well-formed later one instead, and passes -- clearing the way for
    # reconciliation's truncate/rewrite to run before the loop reprocesses
    # the un-done seed for real and raises, now with no restore path.
    # Seed 0 here is hand-marked done-with-an-example but examples.jsonl
    # has no such example, forcing reconciliation to un-done it; its
    # candidate is the one that doesn't fit the group, while seed 1 (what a
    # raw-done-set probe would check instead) fits fine. The two
    # `randint` draws below are `random.Random(0)`/`random.Random(1)`'s
    # own first draw -- the only way `propose` can tell seeds apart, since
    # it only ever sees an already-seeded `rng`, never the seed itself.
    out = Path(tmp) / "hunt-out"
    out.mkdir()
    argv = ["--out", str(out), "--seeds", "0:2"]
    (out / "run.json").write_text(
        json.dumps(
            {
                "argv": argv,
                "git_sha": "0" * 40,
                "start_time": "2026-01-01T00:00:00+00:00",
            }
        )
    )
    (out / "progress.jsonl").write_text(
        json.dumps({"event": "seed_done", "seed": 0, "outcome": "example"}) + "\n"
    )
    progress_before = (out / "progress.jsonl").read_text()
    reconciled_probe_script = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict

class ReconciledFirstSeedFinder:
    symmetry = [(0, 1, 2, 3), (1, 3, 0, 2), (2, 0, 3, 1), (3, 2, 1, 0)]

    def propose(self, rng):
        if rng.randint(0, 10 ** 9) == 906691059:  # random.Random(0)'s draw
            return (0,) * 9
        return (0, 1, 2, 3)

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate)}}

    def key(self, candidate):
        return candidate

sys.exit(run(ReconciledFirstSeedFinder(), sys.argv[1:]))
"""
    resumed = subprocess.run(
        [sys.executable, "-c", reconciled_probe_script, *argv],
        capture_output=True,
        text=True,
    )
    check(
        f"resuming a reconcilable-away 'done' seed into a symmetry mismatch "
        f"still exits 2 (stderr: {resumed.stderr[-300:]})",
        resumed.returncode == 2,
    )
    check(
        "progress.jsonl is untouched -- the check ran before reconciliation "
        "could trim the seed it depends on",
        (out / "progress.jsonl").read_text() == progress_before,
    )
    check(
        "no summary.json was written -- the mismatch surfaced before the "
        "loop, not mid-loop after a truncate/rewrite",
        not (out / "summary.json").exists(),
    )
    check(
        "examples.jsonl was never created",
        not (out / "examples.jsonl").exists(),
    )

with tempfile.TemporaryDirectory() as tmp:
    # Codex pass 1 on PR 530, finding 1: a resume whose entire seed range
    # is already done never gives the live probe an un-done seed to check
    # -- so a group that no longer fits the shape already durable in
    # examples.jsonl (here: the group was a length-9 identity while the
    # recorded key is length 4, as if the declared symmetry changed after
    # a run that used a different one completed) must be caught by
    # comparing the group against the recorded key length directly, with
    # no finder call at all. `propose` raises if called, so a probe that
    # still tried to call it (instead of catching this from the recorded
    # length alone) would fail loudly rather than silently passing.
    out = Path(tmp) / "hunt-out"
    out.mkdir()
    argv = ["--out", str(out), "--seeds", "0:1"]
    (out / "run.json").write_text(
        json.dumps(
            {
                "argv": argv,
                "git_sha": "0" * 40,
                "start_time": "2026-01-01T00:00:00+00:00",
            }
        )
    )
    (out / "progress.jsonl").write_text(
        json.dumps({"event": "seed_done", "seed": 0, "outcome": "example"}) + "\n"
    )
    base_examples = (
        json.dumps({"grid": [0, 1, 2, 3], "__dedupe_key__": [0, 1, 2, 3]}) + "\n"
    )
    (out / "examples.jsonl").write_text(base_examples)
    progress_before = (out / "progress.jsonl").read_text()
    all_done_stale_shape_script = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict

class AllDoneStaleShapeFinder:
    symmetry = [(0, 1, 2, 3, 4, 5, 6, 7, 8)]

    def propose(self, rng):
        raise AssertionError("propose() must not be called -- every seed "
                              "in range is already done")

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate)}}

    def key(self, candidate):
        return candidate

sys.exit(run(AllDoneStaleShapeFinder(), sys.argv[1:]))
"""
    resumed = subprocess.run(
        [sys.executable, "-c", all_done_stale_shape_script, *argv],
        capture_output=True,
        text=True,
    )
    check(
        f"resuming an already-fully-done hunt into a stale recorded shape "
        f"still exits 2 (stderr: {resumed.stderr[-500:]})",
        resumed.returncode == 2,
    )
    check(
        "progress.jsonl is untouched",
        (out / "progress.jsonl").read_text() == progress_before,
    )
    check(
        "examples.jsonl is untouched",
        (out / "examples.jsonl").read_text() == base_examples,
    )
    check("no summary.json was written", not (out / "summary.json").exists())

with tempfile.TemporaryDirectory() as tmp:
    # Codex pass 1 on PR 530, finding 2: the probe's save_state()/
    # load_state() round-trip must snapshot a deep copy, not the live
    # object save_state() returns -- a finder whose save_state() hands
    # back the same mutable object it keeps mutating (here, a list
    # `propose` appends to in place, rather than returning a fresh copy
    # each time) would otherwise see the probe's own extra propose() call
    # bleed into the "restored" state, since restoring a reference to an
    # already-mutated object restores nothing.
    #
    # A genuine base hunt (one seed) completes normally, then state.json
    # is deleted to simulate a kill before its save landed -- the same
    # technique test_hunt_resume.py's negative-seed-no-state case uses.
    # Reconciliation then un-dones that one seed (a stateful finder with
    # no state.json can never prove it "caught up"), so on resume the
    # probe's first (and only) candidate is that same seed's, starting
    # from the finder's fresh (empty) log -- a live-reference bug is not
    # masked by anything already in it.
    out = Path(tmp) / "hunt-out"
    live_reference_script = f"""
import sys
sys.path.insert(0, {str(HERE)!r})
from driver import run
from protocol import Verdict

class LiveReferenceStateFinder:
    symmetry = [(0, 1, 2, 3), (1, 3, 0, 2), (2, 0, 3, 1), (3, 2, 1, 0)]

    def __init__(self):
        self.log = []

    def propose(self, rng):
        self.log.append(1)
        return (0, 1, 2, 3)

    def verify(self, candidate):
        return Verdict(ok=True)

    def record(self, candidate):
        return {{"grid": list(candidate), "log_len_at_find": len(self.log)}}

    def key(self, candidate):
        return candidate

    def save_state(self):
        return self.log

    def load_state(self, state):
        self.log = state

sys.exit(run(LiveReferenceStateFinder(), sys.argv[1:]))
"""
    base = subprocess.run(
        [
            sys.executable,
            "-c",
            live_reference_script,
            "--out",
            str(out),
            "--seeds",
            "0:1",
        ],
        capture_output=True,
        text=True,
    )
    check(
        f"base hunt for the live-reference-state test exits 0 (stderr: "
        f"{base.stderr[-500:]})",
        base.returncode == 0,
    )
    (out / "state.json").unlink()  # simulate a kill before the save landed

    resumed = subprocess.run(
        [
            sys.executable,
            "-c",
            live_reference_script,
            "--out",
            str(out),
            "--seeds",
            "0:1",
        ],
        capture_output=True,
        text=True,
    )
    check(
        f"resume with a live-reference save_state and no state.json exits "
        f"0 (stderr: {resumed.stderr[-500:]})",
        resumed.returncode == 0,
    )
    examples = [
        json.loads(line)
        for line in (out / "examples.jsonl").read_text().splitlines()
        if line
    ]
    check(
        "the probe's own extra propose() call didn't leak into seed 0's "
        "real log_len_at_find",
        len(examples) == 1 and examples[0]["log_len_at_find"] == 1,
    )

sys.exit(0 if ok else 1)

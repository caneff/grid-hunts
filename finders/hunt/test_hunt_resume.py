"""Hunt resume after a kill, black-box on the `hunt` CLI (#487).

Runs the toy finders in this directory as subprocesses and checks only what
a caller of the hunt CLI can see: exit code, stderr, and the output files --
never an internal of driver.py, except the tests that drive `driver.run()`
directly in-process to pin an exact interleaving a live kill can't reliably
reproduce (see each one's own comment for why). Kinds of interruption
exercised:

- A genuine `SIGKILL` mid-hunt, via a finder that sleeps a few ms per seed so
  the kill reliably lands before the range completes (no timing race).
- A hand-corrupted trailing line, for the one case a real kill can leave
  that a timing race can't reliably reproduce: a write caught mid-syscall.
- A hand-truncated last progress.jsonl line, simulating a kill between an
  example's append to examples.jsonl and that seed's own progress event --
  the orphan-example case (#487, added scope from the Codex pass on #507).
- A hand-rolled-back state.json, simulating a kill between a seed's
  progress.jsonl event and its state.json save (#812 Codex pass 1).
- A precisely-timed thread barrier reproducing the fresh-vs-resume
  classify-before-lock race a real kill/schedule-delay combination can
  trigger but can't reliably reproduce on demand (#812 Codex pass 1).
- A hand-truncated progress.jsonl paired with a `_hunt_loop` monkeypatch
  that stops a resume right after reconciliation's own writes, pinning the
  state a *second* kill mid-rerun would leave behind -- render-artifact
  reconciliation, an orphan renders/<seed>.png (#522).

    uv run finders/hunt/test_hunt_resume.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedupe import D4, canonical_key
from render import GridCanvas
from subprocess_env import success_env
from toy_tiny_key_finder import TinyKeyFinder

HERE = Path(__file__).resolve().parent
SLOW_FINDER = HERE / "toy_slow_finder.py"
STATEFUL_FINDER = HERE / "toy_stateful_finder.py"
TINY_KEY_FINDER = HERE / "toy_tiny_key_finder.py"
TOY_FINDER = HERE / "toy_finder.py"

ok = True


class TinyKeyRenderFinder(TinyKeyFinder):
    # toy_render_finder.py's own rule (an even shaded-cell count passes)
    # isn't a guaranteed accept on any one seed -- the #522 render-orphan
    # tests below need the same deterministic-accept property the
    # "orphan-example" case above TinyKeyFinder for, plus a render. Shared
    # here rather than redefined per block (#522 standards review, S3).
    def render(self, candidate):
        return GridCanvas(2, 2, cell=10).image


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def run_cli(finder, out, seeds):
    # `--seeds`, `seeds` as two argv items reads a negative seeds range
    # (e.g. "-3:-2") as an unrecognized option on argparse versions that
    # don't special-case a leading "-" followed by a digit (Python <3.14
    # here) -- the single `--seeds=<value>` token sidesteps that ambiguity
    # on every version (#516).
    return subprocess.run(
        [sys.executable, str(finder), "--out", str(out), f"--seeds={seeds}"],
        capture_output=True,
        text=True,
        env=success_env(),
    )


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def kill_partway(finder, out, seeds, min_seed_done_events=3, extra_args=()):
    """Start `finder` on `seeds`, SIGKILL it once progress.jsonl has grown,
    and return once the process has exited. The finder must sleep per seed
    (see toy_slow_finder.py) so this doesn't race a hunt that finishes
    before the kill lands."""
    proc = subprocess.Popen(
        [
            sys.executable,
            str(finder),
            "--out",
            str(out),
            f"--seeds={seeds}",
            *extra_args,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=success_env(),
    )
    progress_path = out / "progress.jsonl"
    deadline = time.time() + 10
    while time.time() < deadline:
        if (
            progress_path.exists()
            and len(read_jsonl(progress_path)) >= min_seed_done_events
        ):
            break
        if proc.poll() is not None:
            break
        time.sleep(0.005)
    proc.kill()
    proc.wait(timeout=10)
    return proc


with tempfile.TemporaryDirectory() as tmp:
    # Reference: an uninterrupted hunt over the same seed range, to compare
    # the resumed hunt's final output against.
    ref = Path(tmp) / "ref"
    ref_result = run_cli(TOY_FINDER, ref, "0:60")
    check(
        f"reference hunt exits 0 (stderr: {ref_result.stderr[-300:]})",
        ref_result.returncode == 0,
    )
    ref_examples = read_jsonl(ref / "examples.jsonl")
    ref_summary = json.loads((ref / "summary.json").read_text())

    out = Path(tmp) / "killed"
    kill_partway(SLOW_FINDER, out, "0:60")
    progress_before = read_jsonl(out / "progress.jsonl")
    check(
        "the kill left a genuine partial hunt (some seeds done, not all)",
        0 < len(progress_before) < 60,
    )

    resumed = run_cli(SLOW_FINDER, out, "0:60")
    check(
        f"resume after a kill exits 0 (stderr: {resumed.stderr[-300:]})",
        resumed.returncode == 0,
    )

    progress_after = read_jsonl(out / "progress.jsonl")
    seeds_seen = [e["seed"] for e in progress_after if e.get("event") == "seed_done"]
    check(
        "exactly one seed_done event per seed, no seed runs twice",
        sorted(seeds_seen) == list(range(60)),
    )

    resumed_examples = read_jsonl(out / "examples.jsonl")
    resumed_keys = [canonical_key(tuple(e["grid"]), D4) for e in resumed_examples]
    check(
        "no duplicate example after resume",
        len(resumed_keys) == len(set(resumed_keys)),
    )
    ref_keys = {canonical_key(tuple(e["grid"]), D4) for e in ref_examples}
    check(
        "resume finds the same examples as an uninterrupted hunt over the same range",
        set(resumed_keys) == ref_keys,
    )

    resumed_summary = json.loads((out / "summary.json").read_text())
    check(
        "summary.json after resume matches the uninterrupted reference",
        resumed_summary == ref_summary,
    )

with tempfile.TemporaryDirectory() as tmp:
    # A toy finder that saves state (#487 AC: "gets it back on resume").
    # seeds_seen is a counter this finder can only get right by continuing
    # from a saved value, not by restarting at zero.
    out = Path(tmp) / "stateful"
    kill_partway(STATEFUL_FINDER, out, "0:40")
    progress_before = read_jsonl(out / "progress.jsonl")
    check(
        "the kill left a genuine partial stateful hunt",
        0 < len(progress_before) < 40,
    )
    state_before = json.loads((out / "state.json").read_text())
    # save_state runs right after progress.jsonl's write in the same
    # iteration, not atomically with it -- a kill between the two can
    # leave state.json one seed behind progress.jsonl, so this tolerates
    # that gap instead of demanding exact equality.
    check(
        "state.json was written before the kill, within one seed of progress.jsonl",
        0 <= len(progress_before) - state_before["state"].get("seeds_seen", -1) <= 1,
    )

    resumed = run_cli(STATEFUL_FINDER, out, "0:40")
    check(
        f"resume of a stateful hunt exits 0 (stderr: {resumed.stderr[-300:]})",
        resumed.returncode == 0,
    )
    state_after = json.loads((out / "state.json").read_text())
    check(
        "state.json's counter reflects every seed, proving load_state picked up the saved value",
        state_after["state"].get("seeds_seen") == 40,
    )
    check(
        "state.json records which seed it reflects, ending at the last one",
        state_after.get("seed") == 39,
    )
    progress_after = read_jsonl(out / "progress.jsonl")
    seeds_seen = [e["seed"] for e in progress_after if e.get("event") == "seed_done"]
    check(
        "stateful resume: exactly one seed_done event per seed",
        sorted(seeds_seen) == list(range(40)),
    )

with tempfile.TemporaryDirectory() as tmp:
    # #812 Codex pass 1, finding 2: a kill between a seed's progress.jsonl
    # event and its state.json save leaves that seed marked done with its
    # contribution to state never captured -- and since a done seed never
    # reruns, that contribution would be lost forever with nothing else
    # looking wrong. Simulated by hand: progress.jsonl confirms one more
    # seed than state.json reflects.
    out = Path(tmp) / "state-behind"
    result = run_cli(STATEFUL_FINDER, out, "0:10")
    check(
        f"base stateful hunt exits 0 (stderr: {result.stderr[-300:]})",
        result.returncode == 0,
    )
    state_path = out / "state.json"
    real_state = json.loads(state_path.read_text())
    check(
        "the base hunt's state.json reflects the last seed", real_state.get("seed") == 9
    )
    # Roll state.json back one seed, as if seed 9's save never landed.
    state_path.write_text(json.dumps({"seed": 8, "state": {"seeds_seen": 9}}))

    rerun = run_cli(STATEFUL_FINDER, out, "0:10")
    check(
        f"resume after a state/progress gap exits 0 (stderr: {rerun.stderr[-300:]})",
        rerun.returncode == 0,
    )
    final_progress = read_jsonl(out / "progress.jsonl")
    seeds_seen = [e["seed"] for e in final_progress if e.get("event") == "seed_done"]
    check(
        "the seed state.json hadn't caught up to reruns exactly once, not zero times",
        sorted(seeds_seen) == list(range(10)),
    )
    final_state = json.loads(state_path.read_text())
    check(
        "state.json ends caught up to the last seed again",
        final_state.get("seed") == 9 and final_state["state"].get("seeds_seen") == 10,
    )

with tempfile.TemporaryDirectory() as tmp:
    # #516: simulates a kill between negative seed -3's progress.jsonl
    # event and its state.json save by removing state.json after a
    # completed run, as if that one save never landed. progress.jsonl's
    # seed_done event for -3 survives either way, so the witness is
    # whether state.json comes back at all, not whether -3 reappears there.
    out = Path(tmp) / "negative-seed-no-state"
    result = run_cli(STATEFUL_FINDER, out, "-3:-2")
    check(
        f"base negative-seed stateful hunt exits 0 (stderr: {result.stderr[-300:]})",
        result.returncode == 0,
    )
    state_path = out / "state.json"
    real_state = json.loads(state_path.read_text())
    check(
        "the base hunt's state.json reflects the negative seed",
        real_state.get("seed") == -3,
    )
    # Remove state.json entirely, as if seed -3's save never landed.
    state_path.unlink()

    rerun = run_cli(STATEFUL_FINDER, out, "-3:-2")
    check(
        f"resume after a negative-seed state gap exits 0 (stderr: {rerun.stderr[-300:]})",
        rerun.returncode == 0,
    )
    check(
        "state.json exists again after resume, proving seed -3 actually reran "
        "instead of staying done on the absent-state sentinel collision",
        state_path.exists(),
    )
    if state_path.exists():
        final_state = json.loads(state_path.read_text())
        check(
            "state.json reflects the negative seed again",
            final_state.get("seed") == -3
            and final_state["state"].get("seeds_seen") == 1,
        )
        final_progress = read_jsonl(out / "progress.jsonl")
        seeds_seen = [
            e["seed"] for e in final_progress if e.get("event") == "seed_done"
        ]
        check(
            "exactly one seed_done event for the negative seed after resume",
            seeds_seen == [-3],
        )

with tempfile.TemporaryDirectory() as tmp:
    # #516 Codex pass 2: the CLI itself must accept a negative --seeds
    # range as two separate argv tokens ("--seeds", "-3:-2"), not only the
    # "--seeds=-3:-2" single-token form the rest of this file uses -- a
    # real user invoking the CLI by hand types the two-token form, and
    # argparse's own heuristic for telling a negative-looking value apart
    # from an unrecognized option only accepts it on Python 3.14+ without
    # `_merge_seeds_token`'s help.
    out = Path(tmp) / "two-token-negative-seeds"
    result = subprocess.run(
        [sys.executable, str(TOY_FINDER), "--out", str(out), "--seeds", "-3:-1"],
        capture_output=True,
        text=True,
        env=success_env(),
    )
    check(
        f"--seeds and a negative range as two argv tokens exits 0 "
        f"(stderr: {result.stderr[-300:]})",
        result.returncode == 0,
    )
    progress = read_jsonl(out / "progress.jsonl")
    seeds_seen = [e["seed"] for e in progress if e.get("event") == "seed_done"]
    check("both negative seeds ran", sorted(seeds_seen) == [-3, -2])

with tempfile.TemporaryDirectory() as tmp:
    # Only two possible keys exist for this finder, so a broken dedupe
    # rebuild (e.g. "seen" defaulting to empty on resume) would show up as
    # a real duplicate line, not a coincidence the toy 4x4 finders' bigger
    # key space could hide (#487 review: the original 4x4-based resume
    # tests all still passed with dedupe-rebuild removed entirely).
    out = Path(tmp) / "tiny-key"
    kill_partway(TINY_KEY_FINDER, out, "0:50")
    progress_before = read_jsonl(out / "progress.jsonl")
    check(
        "the kill left a genuine partial tiny-key hunt",
        0 < len(progress_before) < 50,
    )
    check(
        "collisions were already happening before the kill (key space of 2 over several seeds)",
        any(e.get("outcome") == "duplicate" for e in progress_before),
    )

    resumed = run_cli(TINY_KEY_FINDER, out, "0:50")
    check(
        f"resume of a tiny-key hunt exits 0 (stderr: {resumed.stderr[-300:]})",
        resumed.returncode == 0,
    )
    examples = read_jsonl(out / "examples.jsonl")
    check(
        "dedupe was really rebuilt from the durable log: exactly the 2 possible keys ever appear, not one per resume",
        {tuple(e["grid"]) for e in examples} == {(0,), (1,)} and len(examples) == 2,
    )
    progress_after = read_jsonl(out / "progress.jsonl")
    seeds_seen = [e["seed"] for e in progress_after if e.get("event") == "seed_done"]
    check(
        "tiny-key resume: exactly one seed_done event per seed",
        sorted(seeds_seen) == list(range(50)),
    )

with tempfile.TemporaryDirectory() as tmp:
    # A half-written trailing line in examples.jsonl, as a real kill
    # mid-write() can leave -- not reproducible via timing, so it's
    # hand-corrupted here. progress.jsonl still confirms the seed as an
    # "example", so this is the "file behind progress" reconciliation
    # direction: the confirmed seed must rerun and rewrite the example,
    # not leave summary.json overcounting a line that no longer exists.
    out = Path(tmp) / "corrupted"
    result = run_cli(TOY_FINDER, out, "0:100")
    check(
        f"base hunt for corruption test exits 0 (stderr: {result.stderr[-300:]})",
        result.returncode == 0,
    )

    examples_path = out / "examples.jsonl"
    examples_text = examples_path.read_text()
    last_line = examples_text.splitlines()[-1]
    examples_path.write_text(examples_text[: -(len(last_line) // 2)])

    rerun = run_cli(TOY_FINDER, out, "0:100")
    check(
        f"resume after a half-written trailing example line exits 0 (stderr: {rerun.stderr[-300:]})",
        rerun.returncode == 0,
    )

    final_progress = read_jsonl(out / "progress.jsonl")
    seeds_seen = [e["seed"] for e in final_progress if e.get("event") == "seed_done"]
    check(
        "a half-written trailing line doesn't break resume: every seed still runs exactly once",
        sorted(seeds_seen) == list(range(100)),
    )
    final_examples = read_jsonl(out / "examples.jsonl")
    final_keys = [canonical_key(tuple(e["grid"]), D4) for e in final_examples]
    check(
        "no duplicate example after resuming past a half-written line",
        len(final_keys) == len(set(final_keys)),
    )
    final_summary = json.loads((out / "summary.json").read_text())
    check(
        "summary.json's example count matches examples.jsonl's actual line count after reconciliation",
        final_summary.get("examples") == len(final_examples),
    )

with tempfile.TemporaryDirectory() as tmp:
    # The other reconciliation direction: an example is fully written to
    # examples.jsonl, but the kill lands before its progress.jsonl event --
    # simulated by dropping progress.jsonl's last event by hand, so
    # examples.jsonl has one more line than progress confirms. A single
    # seed with the tiny-key finder is used so that seed's outcome is
    # deterministically "example" (nothing has been seen yet to duplicate
    # against) -- with the toy finder's own rule, the last seed in a range
    # is only an "example" outcome about half the time, which would make
    # this test flaky rather than exercise the orphan path at all.
    out = Path(tmp) / "orphan"
    result = run_cli(TINY_KEY_FINDER, out, "0:1")
    check(
        f"base hunt for orphan-example test exits 0 (stderr: {result.stderr[-300:]})",
        result.returncode == 0,
    )
    base_progress = read_jsonl(out / "progress.jsonl")
    check(
        "the one seed's outcome is deterministically 'example'",
        len(base_progress) == 1 and base_progress[0].get("outcome") == "example",
    )

    progress_path = out / "progress.jsonl"
    progress_path.write_text("")

    rerun = run_cli(TINY_KEY_FINDER, out, "0:1")
    check(
        f"resume after an orphaned example line exits 0 (stderr: {rerun.stderr[-300:]})",
        rerun.returncode == 0,
    )

    final_progress = read_jsonl(out / "progress.jsonl")
    seeds_seen = [e["seed"] for e in final_progress if e.get("event") == "seed_done"]
    check(
        "an orphaned example's seed reruns exactly once, not zero or twice",
        seeds_seen == [0],
    )
    final_examples = read_jsonl(out / "examples.jsonl")
    check(
        "no duplicate example after resolving an orphaned example",
        len(final_examples) == 1,
    )
    final_summary = json.loads((out / "summary.json").read_text())
    check(
        "summary.json's example count matches examples.jsonl's actual line count for an orphan too",
        final_summary.get("examples") == len(final_examples) == 1,
    )

with tempfile.TemporaryDirectory() as tmp:
    # #522: a kill between an accepted seed's render write and its
    # progress.jsonl event leaves renders/<seed>.png durable while progress
    # doesn't confirm it -- the same setup as the orphan-example case above,
    # but with a render-capable finder. Reconciliation trims that seed's
    # line back out of examples.jsonl on resume, and the seed then reruns
    # and overwrites the same PNG (deterministic), self-healing before this
    # resume process even exits -- so a single real kill followed by a
    # resume that's allowed to finish can't witness the gap either way. The
    # only way the PNG stays a genuine orphan is a second kill landing
    # during that rerun, before it reaches its own render or progress
    # write again -- not reproducible by timing (the seed's own sleep is
    # 10ms, far shorter than a subprocess's own startup), so this drives
    # driver.run() in-process instead, the same exception this file's own
    # docstring carries for the #812 thread-barrier test below, and stops
    # it exactly where that second kill would land: after reconciliation's
    # own writes, before `_hunt_loop` reruns anything.
    import driver as driver_module

    out = Path(tmp) / "render-orphan"
    argv = ["--out", str(out), "--seeds=0:1"]
    finder = TinyKeyRenderFinder()
    code = driver_module.run(finder, argv)
    check("base hunt for render-orphan test exits 0", code == 0)

    base_progress = read_jsonl(out / "progress.jsonl")
    check(
        "the one seed's outcome is deterministically 'example' (render-orphan base)",
        len(base_progress) == 1 and base_progress[0].get("outcome") == "example",
    )
    check(
        "the base hunt wrote the seed's render",
        (out / "renders" / "0.png").exists(),
    )

    # Simulate the first kill landing between the render write and the
    # progress.jsonl flush.
    (out / "progress.jsonl").write_text("")

    # #522 correctness review, C2: a stray file that only *looks*
    # seed-numbered to Python's own permissive `int()` (underscores, here)
    # must not be swept up as if seed 10 -- no seed anywhere near 10 ran in
    # this hunt, so a stem-parse that's too loose would delete it as an
    # unconfirmed "seed 10" the same as a genuine orphan.
    decoy = out / "renders" / "1_0.png"
    decoy.write_bytes(b"not a real seed file")

    class _StopBeforeRerun(Exception):
        pass

    def _boom(*a, **k):
        raise _StopBeforeRerun

    orig_hunt_loop = driver_module._hunt_loop
    driver_module._hunt_loop = _boom
    try:
        try:
            driver_module.run(finder, argv)
            check("resume reached _hunt_loop unexpectedly (render-orphan)", False)
        except _StopBeforeRerun:
            pass
    finally:
        driver_module._hunt_loop = orig_hunt_loop

    check(
        "reconciliation removes a render whose example didn't survive it, "
        "before the seed gets a chance to rerun and self-heal (#522)",
        not (out / "renders" / "0.png").exists(),
    )
    check(
        "a stray file that only int()-parses as a seed (underscores) is "
        "left alone, not swept up as an unconfirmed seed (#522 C2)",
        decoy.exists(),
    )

with tempfile.TemporaryDirectory() as tmp:
    # #522 correctness review, C1: the seed `_reconcile_renders` deletes for
    # is always about to rerun in this same resume -- but `_render_example`
    # swallows a render failure into `render_error` rather than raising, so
    # deleting first is a bet that the rerun's own render succeeds. For a
    # stateless finder that bet is safe even lost: `_repair_renders` (#524)
    # retries any missing render for a confirmed example on a *later*
    # resume, so nothing is lost for good. A stateful finder gets no such
    # retry (`_repair_renders` skips it outright -- a second `propose()`
    # could corrupt state), so deleting its stray render eagerly can turn a
    # merely-unconfirmed-but-intact picture into a permanently missing one.
    # `_reconcile_renders` must skip a stateful finder the same way
    # `_repair_renders` does, leaving the stray file in place rather than
    # betting on a rerun with no safety net.
    #
    # This test pins that carve-out's current, deliberate cost, not a
    # desired end state: a stateful finder can still hit #522's exact
    # failure sequence (a PNG left with no matching example after a second
    # kill), just with the delete-then-lose-it-for-good risk traded away
    # instead. The carve-out -- and this test -- come out once #538 gives a
    # stateful finder a state-safe render-repair path.
    import driver as driver_module
    from protocol import Verdict
    from render import GridCanvas
    from toy_stateful_finder import StatefulToyFinder

    class StatefulRenderFinder(StatefulToyFinder):
        def propose(self, rng):
            self.seeds_seen += 1
            return (rng.randint(0, 1),)

        def verify(self, candidate):
            return Verdict(ok=True)

        def render(self, candidate):
            return GridCanvas(2, 2, cell=10).image

    out = Path(tmp) / "render-orphan-stateful"
    argv = ["--out", str(out), "--seeds=0:1"]
    finder = StatefulRenderFinder()
    code = driver_module.run(finder, argv)
    check("base hunt for stateful render-orphan test exits 0", code == 0)

    base_progress = read_jsonl(out / "progress.jsonl")
    check(
        "the one seed's outcome is deterministically 'example' (stateful render-orphan base)",
        len(base_progress) == 1 and base_progress[0].get("outcome") == "example",
    )
    check(
        "the base hunt wrote the seed's render (stateful)",
        (out / "renders" / "0.png").exists(),
    )
    original_png = (out / "renders" / "0.png").read_bytes()

    # Simulate the same kill landing between the render write and the
    # progress.jsonl flush as the stateless case above.
    (out / "progress.jsonl").write_text("")

    # A full resume-to-completion reruns seed 0 and rewrites renders/0.png
    # either way, self-healing regardless of whether reconciliation deleted
    # it first -- the same masking the render-orphan case above exists to
    # avoid. Stopping before `_hunt_loop` the same way isolates exactly
    # what reconciliation itself did to the file.
    class _StopBeforeRerun(Exception):
        pass

    def _boom(*a, **k):
        raise _StopBeforeRerun

    resume_finder = StatefulRenderFinder()
    orig_hunt_loop = driver_module._hunt_loop
    driver_module._hunt_loop = _boom
    try:
        try:
            driver_module.run(resume_finder, argv)
            check(
                "resume reached _hunt_loop unexpectedly (stateful render-orphan)",
                False,
            )
        except _StopBeforeRerun:
            pass
    finally:
        driver_module._hunt_loop = orig_hunt_loop

    check(
        "a stateful finder's stray render survives reconciliation untouched -- a "
        "deliberate gap (no repair safety net exists yet) pinned until #538, not "
        "the desired end state (#522 C1)",
        (out / "renders" / "0.png").exists()
        and (out / "renders" / "0.png").read_bytes() == original_png,
    )

with tempfile.TemporaryDirectory() as tmp:
    # #522 correctness review, C3/spec P3: nothing above proves
    # `_reconcile_renders` spares a *confirmed* seed's render -- a version
    # that deleted every PNG unconditionally would still pass every check
    # so far. A two-seed range where seed 0's example is confirmed and
    # untouched, and seed 1's progress event is the one dropped, is meant to
    # witness both halves in the same resume: seed 0's PNG survives
    # byte-for-byte, seed 1's stray PNG goes.
    #
    # #522 verification pass, disputed: a first version of this block ran
    # the resume to full completion, and `_resume` calls `_repair_renders`
    # (#524) right after `_reconcile_renders`, before `_hunt_loop` -- so an
    # unconditional-delete bug that wrongly deleted seed 0's PNG too would
    # have `_repair_renders` silently regenerate it (`propose(seed)` is
    # deterministic, byte-for-byte identical) before this test ever looked,
    # passing regardless. Neutering `_repair_renders` for this resume
    # removes that safety net -- the same way the render-orphan case above
    # stops `_hunt_loop` to remove *its* masking self-heal -- so a wrongly
    # deleted seed 0 has nothing left to regenerate it (it's already
    # "done", so `_hunt_loop` skips it too) and the byte-for-byte check
    # below actually tests what its name claims.
    import driver as driver_module

    out = Path(tmp) / "render-orphan-mixed"
    argv = ["--out", str(out), "--seeds=0:2"]
    finder = TinyKeyRenderFinder()
    code = driver_module.run(finder, argv)
    check("base hunt for mixed render-orphan test exits 0", code == 0)

    base_progress = read_jsonl(out / "progress.jsonl")
    base_outcomes = {e["seed"]: e.get("outcome") for e in base_progress}
    check(
        "both seeds are deterministically accepted (mixed render-orphan base)",
        base_outcomes == {0: "example", 1: "example"},
    )
    seed0_png = (out / "renders" / "0.png").read_bytes()
    check(
        "both seeds wrote their render (mixed render-orphan base)",
        (out / "renders" / "0.png").exists() and (out / "renders" / "1.png").exists(),
    )

    # Drop only seed 1's progress event, simulating the kill landing
    # between its render write and its own progress.jsonl flush -- seed 0's
    # line stays confirmed.
    progress_lines = (out / "progress.jsonl").read_text().splitlines(keepends=True)
    (out / "progress.jsonl").write_text(progress_lines[0])

    def _no_repair(finder, out, progress_lines, progress_events):
        return progress_lines, progress_events

    resume_finder = TinyKeyRenderFinder()
    orig_repair_renders = driver_module._repair_renders
    driver_module._repair_renders = _no_repair
    try:
        code = driver_module.run(resume_finder, argv)
    finally:
        driver_module._repair_renders = orig_repair_renders
    check("resume for mixed render-orphan test exits 0", code == 0)

    check(
        "seed 0's confirmed render survives resume byte-for-byte with no "
        "repair step to mask a reconciliation bug that over-deleted -- "
        "reconciliation only touches the seed that didn't survive it (#522 C3/P3)",
        (out / "renders" / "0.png").exists()
        and (out / "renders" / "0.png").read_bytes() == seed0_png,
    )
    check(
        "seed 1's render still matches examples.jsonl after resuming past "
        "its own dropped progress event",
        (out / "renders" / "1.png").exists(),
    )

with tempfile.TemporaryDirectory() as tmp:
    # Argv mismatch refuses to start and writes nothing to any hunt file.
    # (This block's base hunt already leaves .lock behind, so it can't
    # witness whether .lock specifically stays absent on a refusal -- see
    # the next block for that.)
    out = Path(tmp) / "mismatch"
    result = run_cli(TOY_FINDER, out, "0:30")
    check(
        f"base hunt for argv-mismatch test exits 0 (stderr: {result.stderr[-300:]})",
        result.returncode == 0,
    )

    before = sorted(p.name for p in out.iterdir())
    before_contents = {name: (out / name).read_bytes() for name in before}

    rerun = run_cli(TOY_FINDER, out, "0:99")
    check("a differing argv (seeds) exits non-zero", rerun.returncode != 0)

    after = sorted(p.name for p in out.iterdir())
    after_contents = {name: (out / name).read_bytes() for name in after}
    check(
        "a differing argv writes nothing -- not one new file, not one changed byte",
        before == after and before_contents == after_contents,
    )

with tempfile.TemporaryDirectory() as tmp:
    # #812 Codex pass 1, finding 1: classifying --out as fresh or resumed
    # (and checking argv) *before* acquiring the lock is itself a race, so
    # the fix moved that classification inside the lock -- meaning a
    # refusal now does create .lock (an acceptable, harmless side effect of
    # correctly serializing access), even though it still writes no hunt
    # data. Hand-written run.json, no CLI run first, so this is a clean
    # before/after on exactly that.
    out = Path(tmp) / "mismatch-lock-ok"
    out.mkdir()
    (out / "run.json").write_text(
        json.dumps({"argv": ["--out", str(out), "--seeds", "0:30"], "git_sha": "x"})
    )
    check("no .lock exists before the refused rerun", not (out / ".lock").exists())

    rerun = run_cli(TOY_FINDER, out, "0:99")
    check(
        "a differing argv against a hand-written run.json exits non-zero",
        rerun.returncode != 0,
    )
    check(
        ".lock may now exist (locking runs before the argv check), "
        "but run.json itself is untouched and no hunt-data file appears",
        {p.name for p in out.iterdir()} <= {"run.json", ".lock"}
        and (out / "run.json").read_text()
        == json.dumps({"argv": ["--out", str(out), "--seeds", "0:30"], "git_sha": "x"}),
    )

with tempfile.TemporaryDirectory() as tmp:
    # #812 Codex pass 1, finding 1, reproduced directly: two processes on
    # the same fresh --out, where the second reads "no run.json" before the
    # first has even started, but only reaches its own lock acquisition
    # after the first has finished a complete hunt and released it. A real
    # timing race (like the pre-existing "racing on a fresh --out" test)
    # can't reliably land in that exact window, so this drives driver.run()
    # in-process across two threads and pins the ordering with a barrier:
    # thread B is paused inside a patched fcntl.flock, right where it would
    # otherwise acquire the lock, until the main thread has run a complete
    # hunt (thread A) to completion on the same --out.
    import threading
    from unittest import mock

    sys.path.insert(0, str(HERE))
    import driver as driver_module
    from toy_finder import ToyFinder

    out = Path(tmp) / "toctou"
    out.mkdir()
    argv = ["--out", str(out), "--seeds", "0:30"]

    b_ready = threading.Event()
    release_b = threading.Event()
    real_flock = driver_module.fcntl.flock

    def _patched_flock(fd, op):
        if threading.current_thread().name == "hunt-B":
            b_ready.set()
            release_b.wait(timeout=10)
        return real_flock(fd, op)

    driver_module.fcntl.flock = _patched_flock
    b_result = {}
    # This drives driver.run() in-process, so it reads the real
    # HUNT_FAKE_LOAD1/os.environ at call time, not a subprocess env dict --
    # force the gate idle here too so a busy box doesn't refuse either
    # thread's hunt (#526).
    try:
        with mock.patch.dict(os.environ, {"HUNT_FAKE_LOAD1": "0"}):
            b_thread = threading.Thread(
                target=lambda: b_result.__setitem__(
                    "code", driver_module.run(ToyFinder(), argv)
                ),
                name="hunt-B",
            )
            b_thread.start()
            check("thread B reached its lock acquisition", b_ready.wait(timeout=10))

            a_code = driver_module.run(ToyFinder(), argv)
            check(
                "thread A's hunt (run first, in the main thread) exits 0", a_code == 0
            )
            a_progress = read_jsonl(out / "progress.jsonl")
            check(
                "thread A ran the full range before B's lock was released",
                len(a_progress) == 30,
            )

            release_b.set()
            b_thread.join(timeout=15)
    finally:
        driver_module.fcntl.flock = real_flock

    check("thread B's call returned", "code" in b_result)
    final_progress = read_jsonl(out / "progress.jsonl")
    seeds_seen = [e["seed"] for e in final_progress if e.get("event") == "seed_done"]
    check(
        "B's stale 'no run.json yet' belief doesn't overwrite A's completed hunt: "
        "still exactly one seed_done per seed",
        sorted(seeds_seen) == list(range(30)),
    )
    final_summary = json.loads((out / "summary.json").read_text())
    check(
        "summary.json still matches a single, uninterrupted 0:30 hunt",
        final_summary.get("seeds_done") == 30,
    )

with tempfile.TemporaryDirectory() as tmp:
    # Git sha mismatch warns but proceeds.
    out = Path(tmp) / "sha-mismatch"
    result = run_cli(TOY_FINDER, out, "0:30")
    check(
        f"base hunt for sha-mismatch test exits 0 (stderr: {result.stderr[-300:]})",
        result.returncode == 0,
    )

    run_info = json.loads((out / "run.json").read_text())
    run_info["git_sha"] = "0" * 40
    (out / "run.json").write_text(json.dumps(run_info))

    rerun = run_cli(TOY_FINDER, out, "0:30")
    check(
        f"a differing git sha proceeds (exit 0, stderr: {rerun.stderr[-300:]})",
        rerun.returncode == 0,
    )
    check("a differing git sha prints a warning", "sha" in rerun.stderr.lower())

for base_no_verify, resume_no_verify, label in (
    (True, False, "no-verify-then-verify"),
    (False, True, "verify-then-no-verify"),
):
    with tempfile.TemporaryDirectory() as tmp:
        # #527: a killed --no-verify hunt resumed without the flag would
        # verify later seeds inline while earlier seeds kept unverified
        # candidates (and the inverse) -- the resume identity must pin the
        # verification mode, refusing a mode-changing resume and writing
        # nothing, the same as a seeds mismatch does above. A genuinely
        # killed, partial hunt is required here: a base hunt run to
        # completion has no un-done seed left for a wrongly-accepted resume
        # to touch, so it can't tell the fix from the bug (#527 review C1).
        out = Path(tmp) / label
        base_extra = ("--no-verify",) if base_no_verify else ()
        kill_partway(SLOW_FINDER, out, "0:60", extra_args=base_extra)
        progress_before = read_jsonl(out / "progress.jsonl")
        check(
            f"the kill left a genuine partial {label} hunt",
            0 < len(progress_before) < 60,
        )

        before = sorted(p.name for p in out.iterdir())
        before_contents = {name: (out / name).read_bytes() for name in before}

        resume_extra = ["--no-verify"] if resume_no_verify else []
        resumed = subprocess.run(
            [
                sys.executable,
                str(SLOW_FINDER),
                "--out",
                str(out),
                "--seeds=0:60",
                *resume_extra,
            ],
            capture_output=True,
            text=True,
            env=success_env(),
        )
        check(
            f"resuming a mode-changing {label} hunt refuses",
            resumed.returncode != 0,
        )
        after = sorted(p.name for p in out.iterdir())
        after_contents = {name: (out / name).read_bytes() for name in after}
        check(
            "a mode-changing resume writes nothing -- not one new file, not one changed byte",
            before == after and before_contents == after_contents,
        )

sys.exit(0 if ok else 1)

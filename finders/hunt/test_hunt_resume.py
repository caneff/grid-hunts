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
  the orphan-example case.
- A hand-rolled-back state.json, simulating a kill between a seed's
  progress.jsonl event and its state.json save.
- A precisely-timed thread barrier reproducing the fresh-vs-resume
  classify-before-lock race, which a live kill can't reliably hit.

    uv run finders/hunt/test_hunt_resume.py
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_checks import check, check_refusal, finish, read_jsonl, run_cli
from dedupe import D4, canonical_key
from subprocess_env import pin_idle_load, success_env
from toy_render_finder import ToyRenderFinder
from toy_stateful_finder import StatefulToyFinder
from toy_tiny_key_finder import TinyKeyFinder

pin_idle_load()

HERE = Path(__file__).resolve().parent
SLOW_FINDER = HERE / "toy_slow_finder.py"
STATEFUL_FINDER = HERE / "toy_stateful_finder.py"
TINY_KEY_FINDER = HERE / "toy_tiny_key_finder.py"
TOY_FINDER = HERE / "toy_finder.py"


def seeded_hunt(finder, out, seeds):
    # One `--seeds=<value>` token, so a negative range like "-3:-2" cannot
    # read as an option (#516). The two-token form has its own test below.
    return run_cli(finder, "--out", out, f"--seeds={seeds}")


def run_verify(finder, out):
    return run_cli(finder, "verify", out)


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
            and len(read_jsonl(progress_path, missing_ok=True)) >= min_seed_done_events
        ):
            break
        if proc.poll() is not None:
            break
        time.sleep(0.005)
    proc.kill()
    proc.wait(timeout=10)
    return proc


with tempfile.TemporaryDirectory() as tmp:
    ref = Path(tmp) / "ref"
    ref_result = seeded_hunt(TOY_FINDER, ref, "0:60")
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

    resumed = seeded_hunt(SLOW_FINDER, out, "0:60")
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

    resumed = seeded_hunt(STATEFUL_FINDER, out, "0:40")
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
    # A kill between a seed's progress.jsonl event and its state.json save
    # leaves that seed marked done with its contribution to state never
    # captured, and a done seed never reruns. Simulated by hand:
    # progress.jsonl confirms one more seed than state.json reflects.
    out = Path(tmp) / "state-behind"
    result = seeded_hunt(STATEFUL_FINDER, out, "0:10")
    check(
        f"base stateful hunt exits 0 (stderr: {result.stderr[-300:]})",
        result.returncode == 0,
    )
    state_path = out / "state.json"
    real_state = json.loads(state_path.read_text())
    check(
        "the base hunt's state.json reflects the last seed", real_state.get("seed") == 9
    )
    state_path.write_text(json.dumps({"seed": 8, "state": {"seeds_seen": 9}}))

    # Mark seed 9's progress event so a rerun is visible: a rerun writes a
    # fresh event without the mark, while a resume that skips seed 9 leaves
    # the marked one in place (the seed numbers alone are the same either way).
    marked = [
        {**e, "stale_mark": True} if e.get("seed") == 9 else e
        for e in read_jsonl(out / "progress.jsonl")
    ]
    (out / "progress.jsonl").write_text("".join(json.dumps(e) + "\n" for e in marked))

    rerun = seeded_hunt(STATEFUL_FINDER, out, "0:10")
    check(
        f"resume after a state/progress gap exits 0 (stderr: {rerun.stderr[-300:]})",
        rerun.returncode == 0,
    )
    final_progress = read_jsonl(out / "progress.jsonl")
    seeds_seen = [e["seed"] for e in final_progress if e.get("event") == "seed_done"]
    check(
        "the seed state.json hadn't caught up to reruns exactly once, not zero times",
        sorted(seeds_seen) == list(range(10))
        and not any(e.get("stale_mark") for e in final_progress),
    )
    final_state = json.loads(state_path.read_text())
    check(
        "state.json ends caught up to the last seed again",
        final_state.get("seed") == 9 and final_state["state"].get("seeds_seen") == 10,
    )

with tempfile.TemporaryDirectory() as tmp:
    # Removing state.json after a completed run simulates a kill between
    # negative seed -3's progress event and its state save. progress's
    # event for -3 survives either way, so the witness is whether
    # state.json comes back.
    out = Path(tmp) / "negative-seed-no-state"
    result = seeded_hunt(STATEFUL_FINDER, out, "-3:-2")
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
    state_path.unlink()

    rerun = seeded_hunt(STATEFUL_FINDER, out, "-3:-2")
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
    # The CLI accepts a negative --seeds range as two argv tokens, the form
    # a user types by hand; argparse alone takes it only on Python 3.14+,
    # so this needs `_merge_seeds_token`.
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
    # key space could hide.
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

    resumed = seeded_hunt(TINY_KEY_FINDER, out, "0:50")
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
    # An unreadable line that is not the last is no kill's work: the resume
    # refuses it by file and line and leaves the directory as it was.
    out = Path(tmp) / "bad-middle"
    check(
        "base hunt for the bad-middle test exits 0",
        seeded_hunt(TOY_FINDER, out, "0:30").returncode == 0,
    )
    examples_path = out / "examples.jsonl"
    kept = examples_path.read_text().splitlines()
    examples_path.write_text("\n".join([kept[0], "{not json", *kept[1:]]) + "\n")
    before = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
    rerun = seeded_hunt(TOY_FINDER, out, "0:30")
    check_refusal(
        "a bad middle line refuses the resume, naming the file and line",
        rerun,
        "examples.jsonl line 2",
    )
    check(
        "a refused resume changes no file",
        before == {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()},
    )

with tempfile.TemporaryDirectory() as tmp:
    # A half-written trailing line in examples.jsonl, hand-corrupted.
    # progress.jsonl still confirms the seed as an
    # "example", so this is the "file behind progress" reconciliation
    # direction: the confirmed seed must rerun and rewrite the example,
    # not leave summary.json overcounting a line that no longer exists.
    out = Path(tmp) / "corrupted"
    result = seeded_hunt(TOY_FINDER, out, "0:100")
    check(
        f"base hunt for corruption test exits 0 (stderr: {result.stderr[-300:]})",
        result.returncode == 0,
    )

    examples_path = out / "examples.jsonl"
    examples_text = examples_path.read_text()
    last_line = examples_text.splitlines()[-1]
    examples_path.write_text(examples_text[: -(len(last_line) // 2)])

    rerun = seeded_hunt(TOY_FINDER, out, "0:100")
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
    result = seeded_hunt(TINY_KEY_FINDER, out, "0:1")
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

    rerun = seeded_hunt(TINY_KEY_FINDER, out, "0:1")
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
    # A hunt and its resume touch no pictures (#119): a picture left in
    # renders/ -- a stale one, one of a seed the resume reruns, a temp file --
    # stays byte for byte, and the resume writes no new one.
    import driver as driver_module

    out = Path(tmp) / "stray-renders"
    argv = ["--out", str(out), "--seeds=0:2"]
    code = driver_module.run(TinyKeyFinder(), argv)
    check("base hunt for stray-renders test exits 0", code == 0)
    check("a render-less hunt writes no renders/", not (out / "renders").exists())

    (out / "renders").mkdir()
    strays = {"0.png": b"stale", "9.png": b"orphan", "7.tmp-1.png": b"temp"}
    for name, data in strays.items():
        (out / "renders" / name).write_bytes(data)
    progress_lines = (out / "progress.jsonl").read_text().splitlines(keepends=True)
    (out / "progress.jsonl").write_text(progress_lines[0])

    code = driver_module.run(TinyKeyFinder(), argv)
    check("resume over stray pictures exits 0", code == 0)
    check(
        "the resume leaves every stray picture untouched and adds none",
        {p.name: p.read_bytes() for p in (out / "renders").iterdir()} == strays,
    )

with tempfile.TemporaryDirectory() as tmp:
    # The same for a finder that has `render`: its hunt draws nothing, and a
    # resume leaves a populated renders/ byte for byte (#119).
    import driver as driver_module

    out = Path(tmp) / "render-finder-resume"
    argv = ["--out", str(out), "--seeds=0:6"]
    code = driver_module.run(ToyRenderFinder(), argv)
    check("base hunt for the render-finder resume test exits 0", code == 0)
    check(
        "a hunt of a finder with render still writes no renders/",
        not (out / "renders").exists(),
    )

    (out / "renders").mkdir()
    pictures = {"0.png": b"drawn", "3.png": b"drawn too"}
    for name, data in pictures.items():
        (out / "renders" / name).write_bytes(data)
    progress_lines = (out / "progress.jsonl").read_text().splitlines(keepends=True)
    (out / "progress.jsonl").write_text(progress_lines[0])

    code = driver_module.run(ToyRenderFinder(), argv)
    check("resume of a finder with render exits 0", code == 0)
    check(
        "the resume leaves a render finder's pictures untouched and adds none",
        {p.name: p.read_bytes() for p in (out / "renders").iterdir()} == pictures,
    )

with tempfile.TemporaryDirectory() as tmp:
    # This block's base hunt already leaves .lock behind, so it can't
    # witness whether .lock stays absent on a refusal; the next block does.
    out = Path(tmp) / "mismatch"
    result = seeded_hunt(TOY_FINDER, out, "0:30")
    check(
        f"base hunt for argv-mismatch test exits 0 (stderr: {result.stderr[-300:]})",
        result.returncode == 0,
    )

    before = sorted(p.name for p in out.iterdir())
    before_contents = {name: (out / name).read_bytes() for name in before}

    rerun = seeded_hunt(TOY_FINDER, out, "0:99")
    check_refusal("a differing argv (seeds) refuses", rerun, "argv differs")

    after = sorted(p.name for p in out.iterdir())
    after_contents = {name: (out / name).read_bytes() for name in after}
    check(
        "a differing argv writes nothing -- not one new file, not one changed byte",
        before == after and before_contents == after_contents,
    )

with tempfile.TemporaryDirectory() as tmp:
    # Classifying --out as fresh or resumed (and checking argv) happens
    # inside the lock, so a refusal creates .lock (harmless) but writes no
    # hunt data. Hand-written run.json, no CLI run first, so this is a
    # clean before/after on exactly that.
    out = Path(tmp) / "mismatch-lock-ok"
    out.mkdir()
    (out / "run.json").write_text(
        json.dumps({"argv": ["--out", str(out), "--seeds", "0:30"], "git_sha": "x"})
    )
    check("no .lock exists before the refused rerun", not (out / ".lock").exists())

    rerun = seeded_hunt(TOY_FINDER, out, "0:99")
    check_refusal(
        "a differing argv against a hand-written run.json refuses",
        rerun,
        "argv differs",
    )
    check(
        ".lock may now exist (locking runs before the argv check), "
        "but run.json itself is untouched and no hunt-data file appears",
        {p.name for p in out.iterdir()} <= {"run.json", ".lock"}
        and (out / "run.json").read_text()
        == json.dumps({"argv": ["--out", str(out), "--seeds", "0:30"], "git_sha": "x"}),
    )

with tempfile.TemporaryDirectory() as tmp:
    # Two hunts on the same fresh --out, where the second reads "no
    # run.json" before the first starts but reaches its lock only after the
    # first has finished and released it. A real timing race can't reliably
    # land in that window, so driver.run() runs in-process across two
    # threads: thread B pauses inside a patched fcntl.flock until thread A
    # finishes a whole hunt.
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
    import hunt_files

    real_flock = hunt_files.fcntl.flock

    def _patched_flock(fd, op):
        if threading.current_thread().name == "hunt-B":
            b_ready.set()
            release_b.wait(timeout=10)
        return real_flock(fd, op)

    hunt_files.fcntl.flock = _patched_flock
    b_result = {}
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
        hunt_files.fcntl.flock = real_flock

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
    out = Path(tmp) / "sha-mismatch"
    result = seeded_hunt(TOY_FINDER, out, "0:30")
    check(
        f"base hunt for sha-mismatch test exits 0 (stderr: {result.stderr[-300:]})",
        result.returncode == 0,
    )

    run_info = json.loads((out / "run.json").read_text())
    run_info["git_sha"] = "0" * 40
    (out / "run.json").write_text(json.dumps(run_info))

    rerun = seeded_hunt(TOY_FINDER, out, "0:30")
    check(
        f"a differing git sha proceeds (exit 0, stderr: {rerun.stderr[-300:]})",
        rerun.returncode == 0,
    )
    check(
        "a differing git sha prints the sha warning",
        "warning -- git sha differs from the recorded run" in rerun.stderr,
    )

for base_no_verify, resume_no_verify, label in (
    (True, False, "no-verify-then-verify"),
    (False, True, "verify-then-no-verify"),
):
    with tempfile.TemporaryDirectory() as tmp:
        # #527: a resume that flips --no-verify mixes verified and
        # unverified candidates, so the resume identity pins the
        # verification mode and refuses, writing nothing, as a seeds
        # mismatch does above. A killed, partial hunt is needed: a
        # completed one has no un-done seed for a wrong resume to touch.
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
        check_refusal(
            f"resuming a mode-changing {label} hunt refuses", resumed, "argv differs"
        )
        after = sorted(p.name for p in out.iterdir())
        after_contents = {name: (out / name).read_bytes() for name in after}
        check(
            "a mode-changing resume writes nothing -- not one new file, not one changed byte",
            before == after and before_contents == after_contents,
        )

with tempfile.TemporaryDirectory() as tmp:
    # #517: a resume that reconciles or appends to examples.jsonl deletes
    # verified.jsonl, whose verdicts describe the old file. Same
    # setup as the orphan-example case above (the one seed reruns after
    # reconciliation trims its example), with `hunt verify` run first.
    out = Path(tmp) / "verify-then-resume"
    seeded_hunt(TINY_KEY_FINDER, out, "0:1")
    verified = run_verify(TINY_KEY_FINDER, out)
    check(
        f"hunt verify before the resume exits 0 (stderr: {verified.stderr[-300:]})",
        verified.returncode == 0 and (out / "verified.jsonl").exists(),
    )
    (out / "progress.jsonl").write_text("")
    rerun = seeded_hunt(TINY_KEY_FINDER, out, "0:1")
    check(
        f"resume that reconciles examples.jsonl exits 0 (stderr: {rerun.stderr[-300:]})",
        rerun.returncode == 0,
    )
    check(
        "a resume that reconciles and re-appends examples.jsonl deletes verified.jsonl",
        not (out / "verified.jsonl").exists(),
    )

with tempfile.TemporaryDirectory() as tmp:
    # #517: a resume with nothing left to run leaves examples.jsonl alone,
    # so a current verified.jsonl survives it byte for byte.
    out = Path(tmp) / "verify-then-noop-resume"
    seeded_hunt(TINY_KEY_FINDER, out, "0:5")
    verified = run_verify(TINY_KEY_FINDER, out)
    check(
        f"hunt verify of a finished hunt exits 0 (stderr: {verified.stderr[-300:]})",
        verified.returncode == 0,
    )
    before = (out / "verified.jsonl").read_bytes()
    rerun = seeded_hunt(TINY_KEY_FINDER, out, "0:5")
    check(
        f"resume of a finished hunt exits 0 (stderr: {rerun.stderr[-300:]})",
        rerun.returncode == 0,
    )
    check(
        "a resume that changes nothing keeps a current verified.jsonl",
        (out / "verified.jsonl").exists()
        and (out / "verified.jsonl").read_bytes() == before,
    )

with tempfile.TemporaryDirectory() as tmp:
    # #517: a resume that appends a new example (the kill landed before the
    # range finished) deletes verified.jsonl even with no reconciliation.
    out = Path(tmp) / "verify-then-append"
    kill_partway(SLOW_FINDER, out, "0:200")
    verified = run_verify(SLOW_FINDER, out)
    check(
        f"hunt verify of a killed hunt exits 0 (stderr: {verified.stderr[-300:]})",
        verified.returncode == 0,
    )
    check(
        "verify of a killed hunt wrote verified.jsonl",
        (out / "verified.jsonl").exists(),
    )
    rerun = seeded_hunt(SLOW_FINDER, out, "0:200")
    check(
        f"resume of the killed hunt exits 0 (stderr: {rerun.stderr[-300:]})",
        rerun.returncode == 0,
    )
    check(
        "a resume that appends examples deletes verified.jsonl",
        not (out / "verified.jsonl").exists(),
    )

with tempfile.TemporaryDirectory() as tmp:
    # #664: a finder with only one of load_state/save_state is refused at
    # launch, before any hunt file exists.
    import driver as driver_module

    class LoadOnlyFinder(StatefulToyFinder):
        save_state = None

    class SaveOnlyFinder(StatefulToyFinder):
        load_state = None

    for label, dirname, cls in (
        ("load_state only", "half-load", LoadOnlyFinder),
        ("save_state only", "half-save", SaveOnlyFinder),
    ):
        out = Path(tmp) / dirname
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = driver_module.run(cls(), ["--out", str(out), "--seeds=0:3"])
        check(
            f"a finder with {label} is refused at launch (exit 2, stderr: "
            f"{stderr.getvalue()[-300:]})",
            code == 2 and "a stateful finder needs both" in stderr.getvalue(),
        )
        check(
            f"a finder with {label} leaves no hunt file behind",
            not out.exists() or not any(out.iterdir()),
        )

finish()

"""The hunt driver: `run(finder, argv)` (#483/#484/#487).

A thin loop over a finder's `propose`/`verify`/`record`/`key`: it owns the
output directory, inline verification, dedupe and resume after a kill -- no
finder rule, no search strategy. A fresh `--out` (no `run.json`) starts a
new hunt; an `--out` that already has one resumes it: seeds with a
`seed_done` event are skipped, the dedupe set is rebuilt from the durable
log, and a finder's optional `save_state`/`load_state` round-trip through
state.json. A differing argv versus the recorded run refuses to start; a
differing git sha only warns. `--no-verify` skips `finder.verify` while
searching, and `hunt verify DIR` (#489) runs it afterwards over everything
`--no-verify` saved, writing one verdict per examples.jsonl line to
verified.jsonl. A finder's optional `render` (#490) gets a picture saved to
renders/<seed>.png right after that seed's example is accepted; a finder
with no `render` gets no renders/ directory at all. `--workers` (default 3,
set on the finder before the first seed) and the 1-minute load gate
(refuses above 24 unless `--force-load`) are #488. A resume also
reconciles renders/ itself for a stateless finder (#522, `_reconcile_renders`).

    uv run finders/hunt/toy_finder.py --out DIR --seeds START:END
    uv run finders/hunt/toy_finder.py --out DIR --seeds START:END --no-verify
    uv run finders/hunt/toy_finder.py verify DIR

Every accepted example carries a driver-owned `__dedupe_key__` field
alongside whatever `finder.record()` returned, so the dedupe set can be
rebuilt from examples.jsonl on resume the way the ticket asks -- the
double-underscore name is meant to never collide with a finder's own
field. progress.jsonl's per-seed `outcome` (empty/rejected/duplicate/
example) is what lets summary.json's counts rebuild without trusting a
summary.json snapshot a kill may have left stale.

`_process_seed` writes, in order: the example (if any) to examples.jsonl,
that seed's event to progress.jsonl, then (`_hunt_loop`) the finder's saved
state to state.json. A kill can catch any prefix of that sequence, leaving
progress.jsonl's tail ahead of either or both of the other two logs --
`_reconcile` trims progress.jsonl's tail, seed by seed, until it's not
ahead of anything, before resume rebuilds anything from the logs.
"""

import argparse
import fcntl
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedupe import D4, IDENTITY, canonical_key, validate_group
from protocol import DEFAULT_WORKERS, Verdict

OUTPUT_FILES = (
    "examples.jsonl",
    "summary.json",
    "progress.jsonl",
    "run.json",
    "state.json",
    "verified.jsonl",
    "renders",  # a directory, not a file -- (out / name).exists() covers both
)
REPO_ROOT = Path(__file__).resolve().parents[2]

_OUTCOME_COUNT_KEY = {
    "empty": "empty",
    "rejected": "rejected",
    "duplicate": "duplicates",
    "example": "examples",
}

_DEDUPE_KEY_FIELD = "__dedupe_key__"

LOAD_LIMIT = 24


def _load1():
    """The 1-minute load average, or `HUNT_FAKE_LOAD1` when set.

    The env var is the injection point for tests (#488): a hunt started
    through the CLI in a subprocess has no way to hand in a fake load
    function, so the override travels as an env var instead of a
    production-visible CLI flag.
    """
    override = os.environ.get("HUNT_FAKE_LOAD1")
    if not override:
        return os.getloadavg()[0]
    value = float(override)
    if not math.isfinite(value) or value < 0:
        raise ValueError(
            f"HUNT_FAKE_LOAD1={override!r} is not a finite, non-negative load"
        )
    return value


def _check_load(args):
    if args.force_load:
        return None
    try:
        load = _load1()
    except ValueError:
        print(
            f"hunt: refusing to run -- HUNT_FAKE_LOAD1={os.environ.get('HUNT_FAKE_LOAD1')!r} "
            "is not a valid load",
            file=sys.stderr,
        )
        return 2
    if load > LOAD_LIMIT:
        print(
            f"hunt: refusing to run -- 1-minute load {load} is above {LOAD_LIMIT} "
            "(use --force-load to run anyway)",
            file=sys.stderr,
        )
        return 2
    return None


def _parse_seeds(text):
    start, _, end = text.partition(":")
    if not _:
        raise argparse.ArgumentTypeError(f"--seeds wants START:END, got {text!r}")
    return int(start), int(end)


def _merge_seeds_token(argv):
    """Merge a bare `--seeds VALUE` two-token pair into one `--seeds=VALUE`
    token before argparse ever sees it.

    `--seeds` accepts a negative start (e.g. "-3:-2"), and argparse's own
    heuristic for telling a negative-looking value apart from an
    unrecognized option is version-dependent: the two-token form only
    parses on Python 3.14+ here, and raises "expected one argument" on
    3.11-3.13 (#516 Codex pass 2) even though `--seeds=-3:-2` parses on
    every version. Merging ourselves removes that ambiguity everywhere,
    without touching the caller's own argv (used verbatim for run.json's
    recorded-run comparison) -- this returns a new list.
    """
    merged = []
    i = 0
    while i < len(argv):
        if argv[i] == "--seeds" and i + 1 < len(argv):
            merged.append(f"--seeds={argv[i + 1]}")
            i += 2
            continue
        merged.append(argv[i])
        i += 1
    return merged


def _parse_args(argv):
    parser = argparse.ArgumentParser(prog="hunt")
    parser.add_argument("--out", required=True)
    parser.add_argument("--seeds", required=True, type=_parse_seeds)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--force-load", action="store_true")
    parser.add_argument("--no-verify", action="store_true")
    return parser.parse_args(_merge_seeds_token(argv))


def _parse_verify_args(argv):
    parser = argparse.ArgumentParser(prog="hunt verify")
    parser.add_argument("dir")
    return parser.parse_args(argv)


def _git_sha():
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _write_json_atomic(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(path)


def _write_text_atomic(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def _resume_key(argv):
    """The parts of `argv` that define a hunt's search space and how its
    results are trustworthy: `--out`, `--seeds`, and `--no-verify` (#527 --
    a killed `--no-verify` hunt resumed without the flag would verify later
    seeds inline while earlier seeds kept unverified candidates, and the
    inverse). Box-safety knobs (`--workers`, `--force-load`) are excluded on
    purpose (#488 review C1/P2) -- the box's load or a chosen worker count
    differing between two invocations of the same hunt is not a differing
    search, and the load gate's own "use --force-load" advice must not be
    something the resume check then refuses."""
    args = _parse_args(argv)
    return (args.out, args.seeds, args.no_verify)


def _refuse(out_arg, why):
    print(f"hunt: refusing to run -- {out_arg} already has {why}", file=sys.stderr)
    return 2


class SymmetryMismatch(Exception):
    """A custom symmetry group that passes `validate_group`'s pre-flight but
    fails inside `canonical_key` on the first verified candidate (#509). A
    driver-local type, not ValueError, so `run` can single it out without
    swallowing an unrelated finder bug.
    """


def _cleanup_partial_output(out):
    """Remove only the files this run may itself have written -- the
    OUTPUT_FILES set -- leaving anything else in `out` untouched (#509
    review, finding C1): the pre-flight this mirrors never touches a
    pre-existing directory at all, so a blanket `rmtree` here would
    destroy content this run never created. A file that can't be removed
    (a symlink, a read-only parent, ...) is reported instead of silently
    left behind (#509 review, C2) -- swallowing that failure would violate
    "no partial output files" with no signal it happened.

    `.lock` is deliberately excluded (#519): `run()`'s `finally` still
    holds this process's `flock` on it here, and unlinking would let a
    second process re-`open` the path as a fresh inode and lock that one
    -- two processes each believing they hold `--out`'s lock. The pre-
    flight (`other_files` above) ignores a lone `.lock`, so leaving it
    behind never blocks a later run -- the same state a normal completed
    hunt already leaves `--out` in.

    Since `.lock` always exists here (`_acquire_lock` created it before
    any call to this function), `out` itself is therefore never removed
    on this path -- only its OUTPUT_FILES contents.

    `renders/` (#490) is the one OUTPUT_FILES entry that's a directory, not
    a file -- `unlink()` raises `IsADirectoryError` on it, so it gets
    `rmtree` instead.
    """
    failures = []
    for name in OUTPUT_FILES:
        path = out / name
        try:
            if name == "renders":
                if path.is_dir():
                    shutil.rmtree(path)
            else:
                path.unlink()
        except FileNotFoundError:
            pass
        except OSError as e:
            failures.append(f"{name}: {e}")
    if failures:
        print(
            "hunt: warning -- could not remove partial output: " + "; ".join(failures),
            file=sys.stderr,
        )


def _acquire_lock(out):
    """Exclusive, non-blocking flock on out/.lock -- the one lock a hunt
    and `hunt verify` (#489/#523 Codex pass 1) both take, so `hunt verify`
    can't read examples.jsonl mid-write by a running hunt and publish a
    verified.jsonl that silently omits the tail, and two verify runs can't
    race on the same verified.jsonl.tmp. `flock` is tied to the open fd, so
    a SIGKILLed holder releases it the instant the process dies -- no stale
    lock to clean up before the next run. Returns the lock fd, or None if
    another process already holds it."""
    out.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(out / ".lock", os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(lock_fd)
        return None
    return lock_fd


def _release_lock(lock_fd):
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    os.close(lock_fd)


def _to_hashable(value):
    """Undo JSON's list-ifying of a dedupe key's tuple(s) on the way back
    in, so a key nested more than one level deep still hashes."""
    if isinstance(value, list):
        return tuple(_to_hashable(v) for v in value)
    return value


def _read_valid_lines(path):
    """Every complete, parseable line in `path`, plus its raw text.

    A kill can only ever leave the last line half-written -- every earlier
    line was already flushed whole -- so this stops at the first line that
    fails to parse and treats it and everything after it as the casualty.
    """
    if not path.exists():
        return [], []
    valid_lines = []
    parsed = []
    with path.open() as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                break
            valid_lines.append(line if line.endswith("\n") else line + "\n")
            parsed.append(obj)
    return valid_lines, parsed


def _validate_symmetry(finder):
    """Refuse before any output exists if `finder.symmetry` is a custom
    group that doesn't form one (#508/#511) -- a resume validates it again
    since it reruns `canonical_key` on every un-skipped seed the same as a
    fresh hunt would."""
    symmetry = getattr(finder, "symmetry", D4)
    if symmetry in (D4, IDENTITY):
        return None
    try:
        validate_group(symmetry)
    except ValueError as e:
        print(f"hunt: refusing to run -- invalid symmetry group: {e}", file=sys.stderr)
        return 2
    return None


def _truncate_to_valid(path, valid_lines):
    if not path.exists():
        return
    _write_text_atomic(path, "".join(valid_lines))


def _state_seed(finder, out):
    """The seed number the finder's last saved state reflects, or None if
    this finder doesn't save state or hasn't saved any yet -- None, since
    `--seeds` accepts negative integers and no numeric sentinel is safe
    from colliding with a real one (#516)."""
    if not hasattr(finder, "load_state"):
        return None
    state_path = out / "state.json"
    if not state_path.exists():
        return None
    return json.loads(state_path.read_text()).get("seed")


def _reconcile(
    finder, out, progress_lines, progress_events, examples_lines, examples_records
):
    """Trim progress.jsonl's tail until it's not ahead of examples.jsonl or
    state.json, so a seed a kill left half-durable reruns instead of being
    treated as done with a gap.

    `_process_seed` writes, in order, an accepted example to
    examples.jsonl, that seed's event to progress.jsonl, then (`_hunt_loop`)
    the finder's state to state.json -- so in a clean log progress.jsonl's
    claimed example count always equals examples.jsonl's line count, and
    its last confirmed seed is always <= the seed state.json last saved.
    A kill can leave progress.jsonl ahead on either count:

    - ahead of examples.jsonl: that example's own line was lost (truncated
      as invalid, or corrupted by something that left it valid-but-wrong).
    - ahead of state.json: the seed's own contribution to the finder's
      state was never saved -- and since a "done" seed never reruns, that
      contribution would otherwise be lost for good with no error, because
      nothing about the hunt looks broken (#812 Codex pass 1, finding 2).

    Only progress.jsonl's very tail can ever be ahead -- every earlier line
    was already durable everywhere before the kill happened -- so this
    drops progress.jsonl's last event and rechecks both conditions, one
    seed at a time, until neither gap remains. Every dropped seed is no
    longer "done", so it reruns and rewrites everything it should have made
    durable the first time.
    """
    state_seed = _state_seed(finder, out)
    tracks_state = hasattr(finder, "load_state")
    while progress_events:
        example_confirmed = sum(
            1 for e in progress_events if e.get("outcome") == "example"
        )
        examples_ok = example_confirmed <= len(examples_records)
        # A seed_done event always carries "seed" (_process_seed sets it
        # unconditionally); this default only guards a line corrupted in a
        # way _read_valid_lines still parses. It must not default to a
        # numeric sentinel -- that's the exact collision #516 fixed for
        # state_seed -- so an event missing "seed" reads as "always ahead
        # of any real state_seed," never confirmed, always rerun.
        last_seed = progress_events[-1].get("seed", float("inf"))
        state_ok = not tracks_state or (
            state_seed is not None and last_seed <= state_seed
        )
        if examples_ok and state_ok:
            break
        del progress_events[-1]
        del progress_lines[-1]

    example_confirmed = sum(1 for e in progress_events if e.get("outcome") == "example")
    if len(examples_records) > example_confirmed:
        examples_records = examples_records[:example_confirmed]
        examples_lines = examples_lines[:example_confirmed]
    return progress_lines, progress_events, examples_lines, examples_records


_SEED_STEM = re.compile(r"-?\d+")


def _reconcile_renders(finder, out, progress_events):
    """Delete a stray renders/<seed>.png left by a seed whose example
    didn't survive `_reconcile` (#522): a kill between an accepted seed's
    render write and its progress.jsonl event leaves examples.jsonl's line
    for that seed trimmed away on this resume, but the render itself
    untouched. The seed then reruns in `_hunt_loop` and normally overwrites
    the same file (the seed is deterministic), self-healing before this
    resume even finishes -- but a second kill landing during that rerun,
    before it reaches its own render or progress write, leaves the file
    orphaned for good if the hunt is never resumed a third time: nothing
    else would ever revisit it.

    Compares every PNG on disk against progress.jsonl's post-reconcile
    confirmed "example" seeds -- not examples.jsonl, whose records don't
    all carry a seed field (a finder's own `record()` decides that) -- and
    removes anything that isn't there for a real, confirmed reason.
    `_SEED_STEM` requires the whole stem to be an optionally-negative run of
    digits, not just whatever `int()` tolerates (underscores, surrounding
    whitespace, a leading "+") -- a stray file that only looks
    seed-numbered by `int()`'s loose grammar must not be silently swept up.

    Only for a finder with no `save_state`/`load_state`, the same carve-out
    `_repair_renders` makes and for the same reason it does: a stateless
    finder's missing render always gets retried by `_repair_renders` on a
    *later* resume if this one's own rerun happens to fail (#524), so
    deleting the stray file first costs nothing even in the worst case. A
    stateful finder gets no such retry, so deleting eagerly would bet an
    intact picture against a rerun's render with no safety net if that bet
    is lost (#522 correctness review, finding C1) -- left alone instead,
    same as `_repair_renders` leaves a stateful finder's missing render.

    This means a stateful finder can still hit #522's exact failure
    sequence: reconciliation trims the unconfirmed seed's line out of
    examples.jsonl, this carve-out leaves its PNG in place, and a second
    kill before the rerun finishes leaves that PNG with no matching
    example -- a deliberate, known gap, not a theoretical one (pinned by
    the stateful test in test_hunt_resume.py). It stays open until #538
    gives a stateful finder a state-safe render-repair path; only then can
    this carve-out come out too, since only then does deleting eagerly stop
    betting on a rerun with no way back.
    """
    if hasattr(finder, "load_state"):
        return
    renders_dir = out / "renders"
    if not renders_dir.is_dir():
        return
    confirmed = {e["seed"] for e in progress_events if e.get("outcome") == "example"}
    for png in renders_dir.glob("*.png"):
        if not _SEED_STEM.fullmatch(png.stem):
            continue
        if int(png.stem) not in confirmed:
            png.unlink(missing_ok=True)


def _repair_renders(finder, out, progress_lines, progress_events):
    """Resume re-attempts a missing renders/<seed>.png for every
    already-accepted example (#524 Codex pass 1): a transient render
    failure (a full disk, a bug in the finder's own render() since fixed)
    must not leave examples.jsonl and renders/ permanently mismatched with
    no error, just because the seed's outcome was already durable as
    "example" -- a done seed never reruns, so nothing else would ever
    retry it.

    Only for a finder with no `save_state`/`load_state`: `propose()` is the
    only way to regenerate the seed's candidate without the record it wrote
    (finder.record() need not be invertible), and a stateful finder's
    `propose` can have side effects state.json owns (toy_stateful_finder.py
    increments a counter there) -- calling it again here to repair a render
    would double that side effect. A stateful finder's missing render stays
    unrepaired rather than risk silently corrupting its state -- the same
    reason `_reconcile_renders` (#522) also skips a stateful finder outright
    rather than delete a stray render it can't safely regenerate here. #538
    tracks giving a stateful finder a state-safe repair path; until then,
    both carve-outs stay.
    """
    render = getattr(finder, "render", None)
    if render is None or hasattr(finder, "load_state"):
        return progress_lines, progress_events
    for i, event in enumerate(progress_events):
        if event.get("outcome") != "example":
            continue
        seed = event["seed"]
        if (out / "renders" / f"{seed}.png").exists():
            continue
        candidate = finder.propose(random.Random(seed))
        new_event = dict(event)
        new_event.pop("render_error", None)
        _render_example(finder, out, seed, candidate, new_event)
        if new_event != event:
            progress_events[i] = new_event
            progress_lines[i] = json.dumps(new_event) + "\n"
    return progress_lines, progress_events


def _save_state(finder, out, seed):
    save = getattr(finder, "save_state", None)
    if save is None:
        return
    _write_json_atomic(out / "state.json", {"seed": seed, "state": save()})


def _load_state(finder, out):
    load = getattr(finder, "load_state", None)
    state_path = out / "state.json"
    if load is None or not state_path.exists():
        return
    load(json.loads(state_path.read_text())["state"])


def _render_example(finder, out, seed, candidate, event):
    """Write the finder's optional picture of an accepted example to
    renders/<seed>.png -- a finder with no `render` writes nothing, so the
    renders/ directory only ever appears for a finder that offers one.

    The example is already durable in examples.jsonl by the time this runs
    (#490 correctness review C1), so a presentation-layer fault -- a
    missing font, a full disk, a bug in the finder's own render() -- must
    not take the whole hunt down with it: it's recorded on the seed's own
    event instead, the same way a rejection's reason is."""
    render = getattr(finder, "render", None)
    if render is None:
        return
    try:
        renders_dir = out / "renders"
        renders_dir.mkdir(exist_ok=True)
        render(candidate).save(renders_dir / f"{seed}.png")
    except Exception as e:
        event["render_error"] = f"{type(e).__name__}: {e}"


def _propose_and_key(finder, seed, symmetry, no_verify=False):
    """The propose -> verify -> key -> canonical_key sequence, shared by
    `_process_seed` (which writes the outcome) and
    `_check_symmetry_before_mutation` (which only wants the key) so the
    two can't drift on what counts as a mismatch (#509 review, P1; #525
    review, S3). Returns `(candidate, verdict, key)`; `verdict` and `key`
    are `None` when there's nothing further to compute -- no candidate,
    or a rejected one. `no_verify` (#489) skips the call to
    `finder.verify` the same way `_process_seed` always has -- a
    candidate that would be rejected is treated as accepted, so `hunt
    verify DIR` can check it later.
    """
    candidate = finder.propose(random.Random(seed))
    if candidate is None:
        return candidate, None, None
    verdict = Verdict(ok=True) if no_verify else finder.verify(candidate)
    if not verdict.ok:
        return candidate, verdict, None
    cell_values = finder.key(candidate)
    try:
        key = canonical_key(cell_values, symmetry)
    except ValueError as e:
        # Only a custom group's own shape can raise here -- D4's "needs a
        # square grid" is a separate, out-of-scope bug (#509 review, C3)
        # and finder.key() itself is called above, outside this try, so a
        # finder's own ValueError is never relabelled as a symmetry
        # failure (#509 review, P1).
        if symmetry in (D4, IDENTITY):
            raise
        raise SymmetryMismatch(str(e)) from e
    return candidate, verdict, key


def _process_seed(
    finder, seed, seen, symmetry, examples_f, progress_f, counts, out, no_verify
):
    """Run one seed and append its outcome to examples.jsonl/progress.jsonl,
    updating `seen` and `counts` in place. Shared by the fresh and resumed
    loops so the two can't drift apart on what a seed's outcome means."""
    candidate, verdict, key = _propose_and_key(finder, seed, symmetry, no_verify)
    event = {"event": "seed_done", "seed": seed}
    if candidate is None:
        counts["empty"] += 1
        event["outcome"] = "empty"
    elif not verdict.ok:
        counts["rejected"] += 1
        event["outcome"] = "rejected"
        if verdict.reason:
            event["rejected_reason"] = verdict.reason
    elif key in seen:
        counts["duplicates"] += 1
        event["outcome"] = "duplicate"
    else:
        seen.add(key)
        record = dict(finder.record(candidate))
        record[_DEDUPE_KEY_FIELD] = list(key)
        examples_f.write(json.dumps(record) + "\n")
        examples_f.flush()
        counts["examples"] += 1
        event["outcome"] = "example"
        _render_example(finder, out, seed, candidate, event)

    progress_f.write(json.dumps(event) + "\n")
    progress_f.flush()
    counts["seeds_done"] += 1


def _hunt_loop(
    finder, out, seed_start, seed_end, seen, counts, no_verify, skip=frozenset()
):
    symmetry = getattr(finder, "symmetry", D4)
    with (
        (out / "examples.jsonl").open("a") as examples_f,
        (out / "progress.jsonl").open("a") as progress_f,
    ):
        for seed in range(seed_start, seed_end):
            if seed in skip:
                continue
            _process_seed(
                finder,
                seed,
                seen,
                symmetry,
                examples_f,
                progress_f,
                counts,
                out,
                no_verify=no_verify,
            )
            _write_json_atomic(out / "summary.json", dict(counts))
            _save_state(finder, out, seed)


def _fresh(finder, argv, args, out):
    seed_start, seed_end = args.seeds
    _write_json_atomic(
        out / "run.json",
        {
            "argv": list(argv),
            "git_sha": _git_sha(),
            "start_time": datetime.now(UTC).isoformat(),
        },
    )

    counts = {
        "seeds_done": 0,
        "examples": 0,
        "rejected": 0,
        "duplicates": 0,
        "empty": 0,
    }
    _write_json_atomic(out / "summary.json", dict(counts))

    _hunt_loop(
        finder, out, seed_start, seed_end, set(), counts, no_verify=args.no_verify
    )
    return 0


def _check_symmetry_before_mutation(
    finder, symmetry, seed_start, seed_end, done_seeds, examples_records, no_verify
):
    """Refuse a resume whose custom symmetry group no longer fits the
    finder's key shape, before `_resume` writes anything -- two checks,
    both run ahead of any write (#525; `_repair_renders`, #524, moved
    ahead of the same check on rebase):

    1. The group against the key length already durable in
       examples.jsonl, with no finder call at all -- catches a resume
       whose entire seed range is already done, where check 2 below never
       has an un-done seed to probe and so would otherwise never notice a
       stale recorded shape (Codex pass 1 on PR 530, finding 1).
    2. The first not-yet-done seed's *actual* key -- for a finder whose
       `key()` shape changed since the run being resumed last succeeded,
       where the group's own length still happens to match the *old*
       recorded shape and check 1 can't see the drift without a real
       candidate (#525 review C2/P1's own regression test depends on
       this).

    `symmetry in (D4, IDENTITY)` skips both: D4's own "needs a square
    grid" ValueError is a separate, out-of-scope bug (#509 review C3),
    never converted to `SymmetryMismatch` either way, so neither check
    can ever produce a refusal on that path -- running them anyway would
    only spend an unconditional extra propose/verify per resume for
    nothing (#525 review C4, #529).

    `done_seeds` must be the reconciled set `_hunt_loop` will actually
    skip, not a raw read of progress.jsonl (#525 review C2/P1). Calling
    `finder.propose`/`verify` again for check 2 is only safe for a
    stateless finder; a stateful one's `save_state`/`load_state`
    round-trips the in-memory state around the probe so it can't
    double-count whatever the probed seed did (#525 review C1) --
    `_resume` must call `_load_state` before this runs, so the snapshot
    taken here is the resumed state, not the finder's fresh default. That
    snapshot is a deep copy (`json.loads(json.dumps(...))`), not the live
    object `save_state()` returned -- a finder that mutates its own saved
    state in place (rather than returning a fresh one each call) would
    otherwise see the probe's mutation bleed into the "restored" state
    too, since restoring a reference restores nothing (Codex pass 1 on
    PR 530, finding 2).
    """
    if symmetry in (D4, IDENTITY):
        return

    if examples_records:
        key_len = len(examples_records[0][_DEDUPE_KEY_FIELD])
        try:
            canonical_key(tuple(range(key_len)), symmetry)
        except ValueError as e:
            raise SymmetryMismatch(str(e)) from e

    save = getattr(finder, "save_state", None)
    load = getattr(finder, "load_state", None)
    pristine = json.loads(json.dumps(save())) if save else None
    try:
        for seed in range(seed_start, seed_end):
            if seed in done_seeds:
                continue
            _, _, key = _propose_and_key(finder, seed, symmetry, no_verify)
            if key is not None:
                return
    finally:
        if save and load:
            load(pristine)


def _resume(finder, argv, args, out, prior):
    current_sha = _git_sha()
    if prior.get("git_sha") != current_sha:
        print(
            "hunt: warning -- git sha differs from the recorded run "
            f"({prior.get('git_sha')!r} vs {current_sha!r}), resuming anyway",
            file=sys.stderr,
        )

    seed_start, seed_end = args.seeds

    progress_lines, progress_events = _read_valid_lines(out / "progress.jsonl")
    examples_lines, examples_records = _read_valid_lines(out / "examples.jsonl")

    # Reconciliation itself only edits these in-memory lists -- every write
    # (`_truncate_to_valid`, `_repair_renders`, summary.json) is held off
    # until the symmetry check below has passed, so nothing is on disk yet
    # for it to protect (#525; #525 review C2/P1 -- `_repair_renders` (#524)
    # writes too, and moved ahead of the same check on rebase).
    progress_lines, progress_events, examples_lines, examples_records = _reconcile(
        finder, out, progress_lines, progress_events, examples_lines, examples_records
    )

    done_seeds = {e["seed"] for e in progress_events if e.get("event") == "seed_done"}
    seen = {_to_hashable(r[_DEDUPE_KEY_FIELD]) for r in examples_records}
    symmetry = getattr(finder, "symmetry", D4)

    # Loaded before the probe, not after: the probe's save_state/
    # load_state round-trip (see `_check_symmetry_before_mutation`) must
    # snapshot the resumed state, not the finder's fresh default.
    _load_state(finder, out)
    _check_symmetry_before_mutation(
        finder,
        symmetry,
        seed_start,
        seed_end,
        done_seeds,
        examples_records,
        args.no_verify,
    )

    _truncate_to_valid(out / "progress.jsonl", progress_lines)
    _truncate_to_valid(out / "examples.jsonl", examples_lines)
    _reconcile_renders(finder, out, progress_events)

    progress_lines, progress_events = _repair_renders(
        finder, out, progress_lines, progress_events
    )
    _truncate_to_valid(out / "progress.jsonl", progress_lines)

    counts = {
        "seeds_done": 0,
        "examples": 0,
        "rejected": 0,
        "duplicates": 0,
        "empty": 0,
    }
    for e in progress_events:
        counts["seeds_done"] += 1
        count_key = _OUTCOME_COUNT_KEY.get(e.get("outcome"))
        if count_key:
            counts[count_key] += 1
    _write_json_atomic(out / "summary.json", dict(counts))

    _hunt_loop(
        finder,
        out,
        seed_start,
        seed_end,
        seen,
        counts,
        skip=done_seeds,
        no_verify=args.no_verify,
    )
    return 0


def _run_verify(finder, argv):
    """`hunt verify DIR` (#489): run `finder.verify` over every line in
    DIR/examples.jsonl and write one verdict per line to DIR/verified.jsonl
    -- the deferred half of a `--no-verify` hunt. Returns the process exit
    code: 0 on success, 2 when DIR has no examples.jsonl to verify.

    Reads examples.jsonl through `_read_valid_lines` -- the same kill
    tolerance `run`'s own resume gives progress.jsonl/examples.jsonl. Each
    verified.jsonl line carries its own record, not just position, so it
    still joins back to examples.jsonl after a resume appends more lines.
    A record that fails to turn into a candidate and verify (most likely a
    finder with no `candidate_from_record` whose record() isn't itself
    verify-able, but possibly a genuine bug in `verify` itself -- the
    driver can't tell which) refuses with both named as possible causes,
    rather than propagating a raw traceback. verified.jsonl is published
    only on a complete, successful run: a failure partway discards the
    scratch verdicts and the .tmp file, leaving whatever verified.jsonl
    already existed (absent, or a previously complete file) untouched (#527).

    Takes the same out/.lock a hunt takes (`_acquire_lock`), before
    examples.jsonl is even opened -- so this can't read a hunt's
    still-being-written examples.jsonl and publish a verified.jsonl that
    silently omits the tail, and two `hunt verify` runs can't race on the
    same verified.jsonl.tmp (#489/#523 Codex pass 1)."""
    args = _parse_verify_args(argv)
    out = Path(args.dir)

    lock_fd = _acquire_lock(out)
    if lock_fd is None:
        print(
            f"hunt verify: refusing -- {args.dir} is locked (a hunt or "
            "another verify is using it)",
            file=sys.stderr,
        )
        return 2
    try:
        examples_path = out / "examples.jsonl"
        if not examples_path.exists():
            print(
                f"hunt verify: refusing -- {args.dir} has no examples.jsonl",
                file=sys.stderr,
            )
            return 2

        to_candidate = getattr(finder, "candidate_from_record", lambda record: record)
        _, records = _read_valid_lines(examples_path)
        verified_path = out / "verified.jsonl"
        tmp = verified_path.with_suffix(verified_path.suffix + ".tmp")
        verified_count = 0
        with tmp.open("w") as verified_f:
            for record in records:
                try:
                    verdict = finder.verify(to_candidate(record))
                except Exception as e:
                    print(
                        "hunt verify: refusing -- turning a record from "
                        "examples.jsonl into a candidate and verifying it "
                        f"raised ({type(e).__name__}: {e}). Either record() "
                        "isn't itself a verify-able candidate and the finder "
                        "needs a candidate_from_record, or this is a bug in "
                        f"verify() itself -- {verified_count} verdict(s) "
                        "already computed this run were discarded, and any "
                        "previously published verified.jsonl was left "
                        "untouched.",
                        file=sys.stderr,
                    )
                    tmp.unlink(missing_ok=True)
                    return 2
                entry = {"record": record, "ok": verdict.ok}
                if verdict.reason:
                    entry["reason"] = verdict.reason
                verified_f.write(json.dumps(entry) + "\n")
                verified_count += 1
        tmp.replace(verified_path)
        return 0
    finally:
        _release_lock(lock_fd)


def run(finder, argv):
    """Run or resume a hunt for `finder` over the seed range in `argv`, or
    (`argv[0] == "verify"`) run deferred verification -- see
    `_run_verify`.

    A fresh `--out` (no run.json) starts a new hunt, refusing when it
    already holds any other output file with no run.json to explain it. An
    `--out` with a run.json resumes: already-done seeds are skipped, the
    dedupe set is rebuilt from examples.jsonl, summary.json's counts from
    progress.jsonl, and a finder's optional state round-trips through
    state.json. Every one of those checks and decisions is made only after
    this process holds --out's lock (see below), and re-reads --out fresh
    at that point rather than trusting anything observed before acquiring
    it -- a decision made from a pre-lock read can be stale by the time the
    lock is granted. Returns the process exit code: 0 on a completed hunt,
    2 on a refusal (an occupied fresh --out, a resume whose argv doesn't
    match the recorded run, or a second process already holding this
    --out's lock).
    """
    if argv and argv[0] == "verify":
        return _run_verify(finder, argv[1:])

    args = _parse_args(argv)
    if args.workers < 1:
        print(
            f"hunt: refusing to run -- --workers must be at least 1, got {args.workers}",
            file=sys.stderr,
        )
        return 2
    refusal = _check_load(args)
    if refusal is not None:
        return refusal
    finder.workers = args.workers
    refusal = _validate_symmetry(finder)
    if refusal is not None:
        return refusal
    out = Path(args.out)

    # Taken before anything about --out's state is inspected, not just
    # before anything is written: classifying --out as fresh or resumed by
    # reading run.json *before* acquiring this lock is itself a race
    # (#812 Codex pass 1, finding 1) -- a second process can see no
    # run.json, then, delayed by ordinary scheduling rather than by
    # blocking on this non-blocking lock, acquire it only after a first
    # process's complete fresh hunt has already finished and released it.
    # Acting on that stale "no run.json" belief overwrites the finished
    # hunt and replays every seed. Locking first makes every read below an
    # authoritative one.
    lock_fd = _acquire_lock(out)
    if lock_fd is None:
        return _refuse(args.out, "an active hunt (locked)")

    is_resume = False
    try:
        run_path = out / "run.json"
        if run_path.exists():
            is_resume = True
            prior = json.loads(run_path.read_text())
            prior_argv = prior.get("argv")
            if prior_argv is None or _resume_key(prior_argv) != _resume_key(argv):
                print(
                    "hunt: refusing to resume -- argv differs from the recorded run "
                    f"({prior_argv!r} vs {list(argv)!r})",
                    file=sys.stderr,
                )
                return 2
            return _resume(finder, argv, args, out, prior)
        other_files = [
            name
            for name in OUTPUT_FILES
            if name != "run.json" and (out / name).exists()
        ]
        if other_files:
            return _refuse(args.out, ", ".join(other_files))
        return _fresh(finder, argv, args, out)
    except SymmetryMismatch as e:
        # Same clean refusal `_validate_symmetry`'s pre-flight gives a
        # structurally-broken group -- this one only surfaces once a real
        # candidate exists. On a fresh hunt that output is only this
        # attempt's own, so it's torn down. On a resume, `_resume` checks
        # the symmetry group against the first un-done seed's key before
        # writing anything (#525), so the case this exists to guard --
        # the mismatch a resumed hunt would have hit on its very next seed
        # -- refuses with every hunt file untouched, no restore needed. A
        # mismatch a later seed raises once `_hunt_loop` is already
        # running is unguarded the same way any other mid-loop failure is.
        print(f"hunt: refusing to run -- invalid symmetry group: {e}", file=sys.stderr)
        if not is_resume:
            _cleanup_partial_output(out)
        return 2
    finally:
        _release_lock(lock_fd)

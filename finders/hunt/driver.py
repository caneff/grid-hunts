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
`--no-verify` saved, writing to verified.jsonl a stamp line (the count of
examples verified, #517) and then one verdict per examples.jsonl line. A
resume that may change examples.jsonl deletes verified.jsonl. A hunt and
its resume draw no pictures: `hunt render DIR` does, afterwards, over the
examples.jsonl a hunt left. It locks DIR, rebuilds each record with the
finder's `candidate_from_record` (or the record itself without one), draws it
with the finder's `render` and swaps renders/ for the complete set of
renders/<seed>.png in one step, so a kill leaves the previous set or none and
a re-run converges. `hunt summary DIR` and `hunt links DIR` (#121) report on
the hunt and write the short link of each verified hit; a completed hunt calls
the finder's `finish(out)`. A finder supplies only `describe_hit`,
`link_document` and `finish` (protocol.py). `--workers` (default 3,
set on the finder before the first seed) and the 1-minute load gate
(refuses above 24 unless `--force-load`) are #488. A
finder's own knobs travel as `finder.config`: run.json records it and a
resume under a different one refuses; a seed that found nothing may return
`Empty(reason)`, written as `empty_reason` (#491).

    uv run finders/hunt/toy_finder.py --out DIR --seeds START:END
    uv run finders/hunt/toy_finder.py --out DIR --seeds START:END --no-verify
    uv run finders/hunt/toy_finder.py verify DIR
    uv run finders/hunt/toy_render_finder.py render DIR

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
import contextlib
import json
import math
import os
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hunt_files
from dedupe import D4, IDENTITY, canonical_key, validate_group
from protocol import DEFAULT_WORKERS, Empty, Verdict

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
    3.11-3.13 even though `--seeds=-3:-2` parses on
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


def _parse_render_args(argv):
    parser = argparse.ArgumentParser(prog="hunt render")
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


def _resume_key(argv):
    """The parts of `argv` that define a hunt's search space and how its
    results are trustworthy: `--out`, `--seeds`, and `--no-verify` (#527 --
    a killed `--no-verify` hunt resumed without the flag would verify later
    seeds inline while earlier seeds kept unverified candidates, and the
    inverse). Box-safety knobs (`--workers`, `--force-load`) are excluded on
    purpose -- the box's load or a chosen worker count
    differing between two invocations of the same hunt is not a differing
    search, and the load gate's own "use --force-load" advice must not be
    something the resume check then refuses."""
    args = _parse_args(argv)
    return (args.out, args.seeds, args.no_verify)


def _finder_config(finder):
    """The finder's own knobs (#491) -- `finder.config`, or None -- as JSON
    reads them back, so a resume compares like with like against run.json.
    A finder parses its own flags and hands `run` the rest of argv; the
    config is what makes those flags part of the recorded search, since
    `_resume_key` only sees the driver's."""
    return json.loads(json.dumps(getattr(finder, "config", None)))


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
    OUTPUT_FILES set -- leaving anything else in `out` untouched: the
    pre-flight this mirrors never touches a pre-existing directory at all, so
    a blanket `rmtree` here would destroy content this run never created. A
    file that can't be removed (a symlink, a read-only parent, ...) is reported
    instead of silently left behind -- swallowing that failure would violate
    "no partial output files" with no signal it happened.

    `.lock` is deliberately excluded (#519): `run()`'s `finally` still
    holds this process's `flock` on it here, and unlinking would let a
    second process re-`open` the path as a fresh inode and lock that one
    -- two processes each believing they hold `--out`'s lock. The pre-
    flight (`other_files` above) ignores a lone `.lock`, so leaving it
    behind never blocks a later run -- the same state a normal completed
    hunt already leaves `--out` in.

    Since `.lock` always exists here (`hunt_files.acquire_lock` created it before
    any call to this function), `out` itself is therefore never removed
    on this path -- only its OUTPUT_FILES contents.

    `renders/` is the one OUTPUT_FILES entry that's a directory, not a file,
    and a hunt never writes it (`hunt render` does), so it is skipped.
    """
    failures = []
    for name in OUTPUT_FILES:
        if name == "renders":
            continue
        path = out / name
        try:
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


def _to_hashable(value):
    """Undo JSON's list-ifying of a dedupe key's tuple(s) on the way back
    in, so a key nested more than one level deep still hashes."""
    if isinstance(value, list):
        return tuple(_to_hashable(v) for v in value)
    return value


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
    if path.exists():
        hunt_files.rewrite_log(path, valid_lines)


def _state_seed(finder, out):
    """The seed number the finder's last saved state reflects, or None if
    this finder doesn't save state or hasn't saved any yet -- None, since
    `--seeds` accepts negative integers and no numeric sentinel is safe
    from colliding with a real one (#516)."""
    if not _is_stateful(finder):
        return None
    state_path = out / "state.json"
    if not state_path.exists():
        return None
    return hunt_files.read_json(state_path).get("seed")


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
      nothing about the hunt looks broken.

    Only progress.jsonl's very tail can ever be ahead -- every earlier line
    was already durable everywhere before the kill happened -- so this
    drops progress.jsonl's last event and rechecks both conditions, one
    seed at a time, until neither gap remains. Every dropped seed is no
    longer "done", so it reruns and rewrites everything it should have made
    durable the first time.
    """
    state_seed = _state_seed(finder, out)
    tracks_state = _is_stateful(finder)
    while progress_events:
        example_confirmed = sum(
            1 for e in progress_events if e.get("outcome") == "example"
        )
        examples_ok = example_confirmed <= len(examples_records)
        # A seed_done event always carries "seed" (_process_seed sets it
        # unconditionally); this default only guards a line corrupted in a
        # way `hunt_files.read_log` still parses. It must not default to a
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


def _state_hooks(finder):
    """`(has_load, has_save)`: which of `load_state`/`save_state` the finder
    has. The one place that reads them."""
    return (
        getattr(finder, "load_state", None) is not None,
        getattr(finder, "save_state", None) is not None,
    )


def _is_stateful(finder):
    """A finder with both `load_state` and `save_state` is stateful: its
    `propose()` can have side effects state.json owns. The one place that
    says so; `_validate_stateful` refuses a finder with only one of them."""
    return all(_state_hooks(finder))


def _validate_stateful(finder):
    """Refuse before any output exists a finder with only one of
    `load_state`/`save_state` (#664). Load-only never writes state.json, so
    every resume would trim each event back to the start and truncate
    examples.jsonl; save-only writes a state it never reads back."""
    has_load, has_save = _state_hooks(finder)
    if has_load == has_save:
        return None
    have, lack = (
        ("load_state", "save_state") if has_load else ("save_state", "load_state")
    )
    print(
        f"hunt: refusing to run -- the finder has {have} but not {lack}; "
        "a stateful finder needs both",
        file=sys.stderr,
    )
    return 2


@contextlib.contextmanager
def _restoring_state(finder):
    """Snapshot a stateful finder's state (a JSON round trip of
    `save_state()`, so a finder that mutates its saved object in place cannot
    bleed into the snapshot) and restore it on exit, even on an exception. A
    stateless finder passes through untouched."""
    if not _is_stateful(finder):
        yield
        return
    snapshot = json.loads(json.dumps(finder.save_state()))
    try:
        yield
    finally:
        finder.load_state(snapshot)


def _save_state(finder, out, seed):
    if not _is_stateful(finder):
        return
    hunt_files.write_json_atomic(
        out / "state.json", {"seed": seed, "state": finder.save_state()}
    )


def _load_state(finder, out):
    state_path = out / "state.json"
    if not _is_stateful(finder) or not state_path.exists():
        return
    finder.load_state(hunt_files.read_json(state_path)["state"])


def _propose_and_key(finder, seed, symmetry, no_verify=False):
    """The propose -> verify -> key -> canonical_key sequence, shared by
    `_process_seed` (which writes the outcome) and
    `_check_symmetry_before_mutation` (which only wants the key) so the two
    can't drift on what counts as a mismatch. Returns `(candidate, verdict,
    key)`; `verdict` and `key` are `None` when there's nothing further to
    compute -- no candidate, or a rejected one. `no_verify` (#489) skips the
    call to
    `finder.verify` the same way `_process_seed` always has -- a
    candidate that would be rejected is treated as accepted, so `hunt
    verify DIR` can check it later.
    """
    candidate = finder.propose(random.Random(seed))
    if _is_empty(candidate):
        return candidate, None, None
    verdict = Verdict(ok=True) if no_verify else finder.verify(candidate)
    if not verdict.ok:
        return candidate, verdict, None
    cell_values = finder.key(candidate)
    try:
        key = canonical_key(cell_values, symmetry)
    except ValueError as e:
        # Only a custom group's own shape can raise here -- D4's "needs a
        # square grid" is a separate, out-of-scope bug
        # and finder.key() itself is called above, outside this try, so a
        # finder's own ValueError is never relabelled as a symmetry
        # failure.
        if symmetry in (D4, IDENTITY):
            raise
        raise SymmetryMismatch(str(e)) from e
    return candidate, verdict, key


def _is_empty(candidate):
    """A seed that proposed nothing: None, or an `Empty` that may say why."""
    return candidate is None or isinstance(candidate, Empty)


def _process_seed(
    finder, seed, seen, symmetry, append_example, append_event, counts, out, no_verify
):
    """Run one seed and append its outcome to examples.jsonl/progress.jsonl,
    updating `seen` and `counts` in place. Shared by the fresh and resumed
    loops so the two can't drift apart on what a seed's outcome means."""
    candidate, verdict, key = _propose_and_key(finder, seed, symmetry, no_verify)
    event = {"event": "seed_done", "seed": seed}
    if _is_empty(candidate):
        counts["empty"] += 1
        event["outcome"] = "empty"
        if isinstance(candidate, Empty):
            event["empty_reason"] = candidate.reason
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
        append_example(record)
        counts["examples"] += 1
        event["outcome"] = "example"

    append_event(event)
    counts["seeds_done"] += 1


def _hunt_loop(
    finder, out, seed_start, seed_end, seen, counts, no_verify, skip=frozenset()
):
    symmetry = getattr(finder, "symmetry", D4)
    with (
        hunt_files.open_log(out / "examples.jsonl") as append_example,
        hunt_files.open_log(out / "progress.jsonl") as append_event,
    ):
        for seed in range(seed_start, seed_end):
            if seed in skip:
                continue
            _process_seed(
                finder,
                seed,
                seen,
                symmetry,
                append_example,
                append_event,
                counts,
                out,
                no_verify=no_verify,
            )
            hunt_files.write_json_atomic(out / "summary.json", dict(counts))
            _save_state(finder, out, seed)


def _fresh(finder, argv, args, out):
    seed_start, seed_end = args.seeds
    hunt_files.write_json_atomic(
        out / "run.json",
        {
            "argv": list(argv),
            "config": _finder_config(finder),
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
    hunt_files.write_json_atomic(out / "summary.json", dict(counts))

    _hunt_loop(
        finder, out, seed_start, seed_end, set(), counts, no_verify=args.no_verify
    )
    return 0


def _check_symmetry_before_mutation(
    finder, symmetry, seed_start, seed_end, done_seeds, examples_records, no_verify
):
    """Refuse a resume whose custom symmetry group no longer fits the
    finder's key shape, before `_resume` writes anything -- two checks,
    both run ahead of any write (#525):

    1. The group against the key length already durable in
       examples.jsonl, with no finder call at all -- catches a resume
       whose entire seed range is already done, where check 2 below never
       has an un-done seed to probe and so would otherwise never notice a
       stale recorded shape (PR 530).
    2. The first not-yet-done seed's *actual* key -- for a finder whose
       `key()` shape changed since the run being resumed last succeeded,
       where the group's own length still happens to match the *old*
       recorded shape and check 1 can't see the drift without a real
       candidate (a regression test depends on
       this).

    `symmetry in (D4, IDENTITY)` skips both: D4's own "needs a square
    grid" ValueError is a separate, out-of-scope bug,
    never converted to `SymmetryMismatch` either way, so neither check
    can ever produce a refusal on that path -- running them anyway would
    only spend an unconditional extra propose/verify per resume for
    nothing (#529).

    `done_seeds` must be the reconciled set `_hunt_loop` will actually
    skip, not a raw read of progress.jsonl. Calling
    `finder.propose`/`verify` again for check 2 is only safe for a
    stateless finder; a stateful one's `save_state`/`load_state`
    round-trips the in-memory state around the probe so it can't
    double-count whatever the probed seed did --
    `_resume` must call `_load_state` before this runs, so the snapshot
    taken here is the resumed state, not the finder's fresh default. That
    snapshot is a deep copy (`json.loads(json.dumps(...))`), not the live
    object `save_state()` returned -- a finder that mutates its own saved
    state in place (rather than returning a fresh one each call) would
    otherwise see the probe's mutation bleed into the "restored" state
    too, since restoring a reference restores nothing.
    """
    if symmetry in (D4, IDENTITY):
        return

    if examples_records:
        key_len = len(examples_records[0][_DEDUPE_KEY_FIELD])
        try:
            canonical_key(tuple(range(key_len)), symmetry)
        except ValueError as e:
            raise SymmetryMismatch(str(e)) from e

    with _restoring_state(finder):
        for seed in range(seed_start, seed_end):
            if seed in done_seeds:
                continue
            _, _, key = _propose_and_key(finder, seed, symmetry, no_verify)
            if key is not None:
                return


def _resume(finder, argv, args, out, prior):
    current_sha = _git_sha()
    if prior.get("git_sha") != current_sha:
        print(
            "hunt: warning -- git sha differs from the recorded run "
            f"({prior.get('git_sha')!r} vs {current_sha!r}), resuming anyway",
            file=sys.stderr,
        )

    seed_start, seed_end = args.seeds

    progress_lines, progress_events = hunt_files.read_log(
        out / "progress.jsonl", missing_ok=True
    )
    examples_lines, examples_records = hunt_files.read_log(
        out / "examples.jsonl", missing_ok=True
    )

    raw_examples_count = len(examples_lines)

    # Reconciliation itself only edits these in-memory lists -- every write
    # (`_truncate_to_valid`, summary.json) is held off
    # until the symmetry check below has passed, so nothing is on disk yet
    # for it to protect (#525).
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

    # verified.jsonl describes the examples.jsonl `hunt verify` read (#517).
    # This resume reconciled it, or has a seed left that may append to it
    # (whether one does is only known once it runs). Deleted before either
    # write, so a kill in between can't leave a stale file.
    if len(examples_lines) != raw_examples_count or any(
        seed not in done_seeds for seed in range(seed_start, seed_end)
    ):
        (out / "verified.jsonl").unlink(missing_ok=True)

    _truncate_to_valid(out / "progress.jsonl", progress_lines)
    _truncate_to_valid(out / "examples.jsonl", examples_lines)

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
    hunt_files.write_json_atomic(out / "summary.json", dict(counts))

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
    DIR/examples.jsonl and write a stamp line, then one verdict per line, to
    DIR/verified.jsonl
    -- the deferred half of a `--no-verify` hunt. Returns the process exit
    code: 0 on success, 2 when DIR has no examples.jsonl to verify.

    Reads the logs through `hunt_files.read_logs` -- the same kill
    tolerance `run`'s own resume gives them. Each
    verdict line carries its own record, not just position, so it joins back
    to examples.jsonl by content.
    A record that fails to turn into a candidate and verify (most likely a
    finder with no `candidate_from_record` whose record() isn't itself
    verify-able, but possibly a genuine bug in `verify` itself -- the
    driver can't tell which) refuses with both named as possible causes,
    rather than propagating a raw traceback. verified.jsonl is published
    only on a complete, successful run: a failure partway discards the
    scratch verdicts and the .tmp file, leaving whatever verified.jsonl
    already existed (absent, or a previously complete file) untouched (#527).

    Takes the same out/.lock a hunt takes (`hunt_files.acquire_lock`), before
    examples.jsonl is even opened -- so this can't read a hunt's
    still-being-written examples.jsonl and publish a verified.jsonl that
    silently omits the tail, and two `hunt verify` runs can't race on the
    same verified.jsonl.tmp (#489)."""
    args = _parse_verify_args(argv)
    out = Path(args.dir)

    lock_fd = hunt_files.acquire_lock(out)
    if lock_fd is None:
        print(
            f"hunt verify: refusing -- {args.dir} is locked (a hunt or "
            "another verify is using it)",
            file=sys.stderr,
        )
        return 2
    try:
        to_candidate = getattr(finder, "candidate_from_record", lambda record: record)
        try:
            _, records = hunt_files.read_logs(out)
        except hunt_files.HuntFileError as error:
            print(f"hunt verify: refusing -- {error}", file=sys.stderr)
            return 2
        # The stamp (#517): how many examples this pass verified, so a
        # reader can compare it to the count of examples.jsonl.
        lines = [json.dumps({"verified_examples": len(records)}) + "\n"]
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
                    f"verify() itself -- {len(lines) - 1} verdict(s) "
                    "already computed this run were discarded, and any "
                    "previously published verified.jsonl was left "
                    "untouched.",
                    file=sys.stderr,
                )
                return 2
            entry = {"record": record, "ok": verdict.ok}
            if verdict.reason:
                entry["reason"] = verdict.reason
            lines.append(json.dumps(entry) + "\n")
        hunt_files.rewrite_log(out / "verified.jsonl", lines)
        return 0
    finally:
        hunt_files.release_lock(lock_fd)


def _run_render(finder, argv):
    """`hunt render DIR`: draw a picture of every example in DIR/examples.jsonl
    to DIR/renders/<seed>.png, the post-pass that replaces drawing inside the
    hunt. Returns the exit code: 0 on success, 2 on a refusal (a finder with
    no `render`, DIR locked or without examples.jsonl, a record that fails to
    rebuild or draw).

    Takes the hunt's out/.lock, so it never reads a running hunt's logs. The
    k-th "example" event of progress.jsonl names the seed of the k-th
    examples.jsonl record; a record past the last event is an example a kill
    left unconfirmed, which a resume would trim, so it gets no picture. Every
    picture is drawn into renders.tmp/ first and renders/ is swapped for it
    whole (the old set moves to renders.old/, which is then removed), so a kill
    leaves the previous set or none, never a mix, and a re-run converges: it
    sweeps the two scratch directories a kill left. A failure partway
    removes renders.tmp/ and leaves renders/ as it was."""
    args = _parse_render_args(argv)
    out = Path(args.dir)
    render = getattr(finder, "render", None)
    if render is None:
        print("hunt render: refusing -- the finder has no render", file=sys.stderr)
        return 2

    lock_fd = hunt_files.acquire_lock(out)
    if lock_fd is None:
        print(
            f"hunt render: refusing -- {args.dir} is locked (a hunt or "
            "another verify or render is using it)",
            file=sys.stderr,
        )
        return 2
    try:
        try:
            seeded = hunt_files.read_examples(out)
        except hunt_files.HuntFileError as error:
            print(f"hunt render: refusing -- {error}", file=sys.stderr)
            return 2
        to_candidate = getattr(finder, "candidate_from_record", lambda record: record)
        drawn = {}
        for seed, record in seeded:
            try:
                drawn[seed] = render(to_candidate(record))
            except Exception as e:
                print(
                    f"hunt render: refusing -- seed {seed} did not draw "
                    f"({type(e).__name__}: {e}); renders/ was left as it was",
                    file=sys.stderr,
                )
                return 2

        def save_all(directory):
            for seed, image in drawn.items():
                hunt_files.write_image_atomic(directory / f"{seed}.png", image)

        try:
            hunt_files.swap_dir(out / "renders", save_all)
        except Exception as e:
            print(
                f"hunt render: refusing -- {type(e).__name__}: {e}; renders/ "
                "was left as it was",
                file=sys.stderr,
            )
            return 2
        return 0
    finally:
        hunt_files.release_lock(lock_fd)


def _run_summary(finder, argv):
    """`hunt summary DIR`: print the seed span, outcome counts and verified
    hits of the hunt in DIR (`hunt_dir.hunt_summary`), each hit worded by the
    finder's optional `describe_hit(record)`. Exit 2 on a bad argument list or
    a directory with no hunt."""
    import hunt_dir  # hunt_dir -> verified_io -> driver: imported late

    describe = getattr(finder, "describe_hit", None)
    return hunt_dir.summary_command(
        ["summary", *argv], lambda out: hunt_dir.hunt_summary(out, describe)
    )


def _run_links(finder, argv):
    """`hunt links DIR`: write DIR/links/<seed>.txt, the short link of the
    finder's `link_document(candidate)`, for each verified hit, replacing
    `links/` as one set. An unverified example gets none: run `verify DIR`
    first. Returns 0, or 2 on a refusal (a finder without `link_document`,
    DIR locked or holding no hunt, a hit that does not rebuild or mint)."""
    import hunt_dir
    from short_link import mint
    from verified_io import example_verdicts

    args = _parse_verify_args(argv)
    out = Path(args.dir)
    document = getattr(finder, "link_document", None)
    if document is None:
        print(
            "hunt links: refusing -- the finder has no link_document", file=sys.stderr
        )
        return 2
    lock_fd = hunt_files.acquire_lock(out)
    if lock_fd is None:
        print(f"hunt links: refusing -- {args.dir} is locked", file=sys.stderr)
        return 2
    try:
        try:
            run_json = hunt_files.read_json(out / "run.json")
            seeded = hunt_dir.seeded_examples(out)
            verdicts = example_verdicts(
                out, run_json["argv"], [record for _, record in seeded]
            )
            to_candidate = getattr(
                finder, "candidate_from_record", lambda record: record
            )
            built = {
                seed: mint(document(to_candidate(record))) + "\n"
                for (seed, record), verdict in zip(seeded, verdicts, strict=True)
                if verdict == "hit"
            }
            hunt_dir.replace_links(out, built)
        except Exception as e:
            print(
                f"hunt links: refusing -- {type(e).__name__}: {e}; links/ was "
                "left as it was",
                file=sys.stderr,
            )
            return 2
        return 0
    finally:
        hunt_files.release_lock(lock_fd)


def _finish(finder, out, code):
    """Call the finder's optional `finish(out)` once a hunt has completed
    (exit 0). A killed hunt never gets here, so the hook marks only a
    completed one."""
    hook = getattr(finder, "finish", None)
    if code == 0 and hook is not None:
        hook(out)
    return code


def run(finder, argv):
    """Run or resume a hunt for `finder` over the seed range in `argv`, or
    (`argv[0] == "verify"`) run deferred verification -- see
    `_run_verify` -- or (`argv[0] == "render"`) draw the pictures -- see
    `_run_render` -- or (`"summary"`, `"links"`) report on a hunt or write its
    short links -- see `_run_summary`, `_run_links`. A completed hunt calls the
    finder's optional `finish(out)`.

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
    if argv and argv[0] == "render":
        return _run_render(finder, argv[1:])
    if argv and argv[0] == "summary":
        return _run_summary(finder, argv[1:])
    if argv and argv[0] == "links":
        return _run_links(finder, argv[1:])

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
    refusal = _validate_stateful(finder) or _validate_symmetry(finder)
    if refusal is not None:
        return refusal
    out = Path(args.out)

    # Taken before anything about --out's state is inspected, not just
    # before anything is written: classifying --out as fresh or resumed by
    # reading run.json *before* acquiring this lock is itself a race
    # -- a second process can see no
    # run.json, then, delayed by ordinary scheduling rather than by
    # blocking on this non-blocking lock, acquire it only after a first
    # process's complete fresh hunt has already finished and released it.
    # Acting on that stale "no run.json" belief overwrites the finished
    # hunt and replays every seed. Locking first makes every read below an
    # authoritative one.
    lock_fd = hunt_files.acquire_lock(out)
    if lock_fd is None:
        return _refuse(args.out, "an active hunt (locked)")

    is_resume = False
    try:
        run_path = out / "run.json"
        if run_path.exists():
            is_resume = True
            prior = hunt_files.read_json(run_path)
            prior_argv = prior.get("argv")
            if prior_argv is None or _resume_key(prior_argv) != _resume_key(argv):
                print(
                    "hunt: refusing to resume -- argv differs from the recorded run "
                    f"({prior_argv!r} vs {list(argv)!r})",
                    file=sys.stderr,
                )
                return 2
            config = _finder_config(finder)
            if prior.get("config") != config:
                print(
                    "hunt: refusing to resume -- finder config differs from the "
                    f"recorded run ({prior.get('config')!r} vs {config!r})",
                    file=sys.stderr,
                )
                return 2
            return _finish(finder, out, _resume(finder, argv, args, out, prior))
        other_files = [
            name
            for name in OUTPUT_FILES
            if name != "run.json" and (out / name).exists()
        ]
        if other_files:
            return _refuse(args.out, ", ".join(other_files))
        return _finish(finder, out, _fresh(finder, argv, args, out))
    except hunt_files.HuntFileError as e:
        print(f"hunt: refusing to resume -- {e}", file=sys.stderr)
        return 2
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
        hunt_files.release_lock(lock_fd)

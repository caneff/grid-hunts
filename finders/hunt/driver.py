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
with the finder's `render` and replaces renders/ with the set of
renders/<seed>.png (`hunt_files.swap_dir` owns the swap). `hunt summary DIR`
and `hunt links DIR` (#121) report on the hunt and write the short link of each verified hit; a completed hunt calls
the finder's `finish(out)`. A finder supplies only `describe_hit` (or `summary_lines`),
`link_document` and `finish` (protocol.py). `--workers` (default 3,
set on the finder before the first seed) and the 1-minute load gate
(refuses above 24 unless `--force-load`) are box knobs (#488). A
finder's own knobs travel as `finder.config`: run.json records it and a
resume under a different one refuses; a seed that found nothing may return
`Empty(reason)`, written as `empty_reason` (#491).

    uv run finders/hunt/toy_finder.py --out DIR --seeds START:END
    uv run finders/hunt/toy_finder.py --out DIR --seeds START:END --no-verify
    uv run finders/hunt/toy_finder.py verify DIR
    uv run finders/hunt/toy_render_finder.py render DIR

Every accepted example carries a driver-owned `__dedupe_key__` field
alongside whatever `finder.record()` returned, so the dedupe set can be
rebuilt from examples.jsonl on resume; the double-underscore name avoids
a finder's own fields. progress.jsonl's per-seed `outcome` (empty/rejected/duplicate/
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
    "renders",
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
    """The 1-minute load, or `HUNT_FAKE_LOAD1` (#488): an env var because a
    subprocess-launched hunt cannot take a fake load function, and a test knob
    stays out of production argv.
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


def _parse_dir_args(prog, argv):
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("dir")
    return parser.parse_args(argv)


@contextlib.contextmanager
def _held_lock(prog, dir_arg):
    """Hold DIR's lock for the block and yield True, or print the refusal and
    yield False when a hunt or another subcommand holds it."""
    lock_fd = hunt_files.acquire_lock(Path(dir_arg))
    if lock_fd is None:
        print(
            f"{prog}: refusing -- {dir_arg} is locked (a hunt or another "
            "verify, render or links is using it)",
            file=sys.stderr,
        )
        yield False
        return
    try:
        yield True
    finally:
        hunt_files.release_lock(lock_fd)


def _candidate_builder(finder):
    """Rebuild a candidate from an examples.jsonl record: the finder's
    `candidate_from_record`, or the record itself without one."""
    return getattr(finder, "candidate_from_record", lambda record: record)


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
    results are trustworthy: `--out`, `--seeds`, and `--no-verify` (#527: resuming
    across a verify-mode change mixes verified and unverified examples).
    `--workers` and `--force-load` are excluded so the load gate's own
    "use --force-load" advice is never refused."""
    args = _parse_args(argv)
    return (args.out, args.seeds, args.no_verify)


def _finder_config(finder):
    """The finder's config (#491) as JSON reads it back, so a resume compares like
    with like against run.json. `_resume_key` only sees the driver's flags;
    the config records the finder's."""
    return json.loads(json.dumps(getattr(finder, "config", None)))


def _refuse(out_arg, why):
    print(f"hunt: refusing to run -- {out_arg} already has {why}", file=sys.stderr)
    return 2


class SymmetryMismatch(Exception):
    """A custom symmetry group that passes `validate_group`'s pre-flight but
    fails inside `canonical_key` on the first verified candidate (#509). A
    driver-local type, not ValueError, so `run` can catch it without
    swallowing an unrelated finder bug.
    """


def _cleanup_partial_output(out):
    """Remove only OUTPUT_FILES, never other content in `out`. A file that
    can't be removed is reported, not silently left behind.

    `.lock` is kept: this process still holds its flock, and unlinking lets a
    second process lock a fresh inode at the same path. The pre-flight in
    `run` (`other_files`) ignores a lone `.lock`, so it never blocks a later
    run.

    `renders/` is a directory a hunt never writes (`hunt render` does), so it
    is skipped.
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
    if isinstance(value, list):
        return tuple(_to_hashable(v) for v in value)
    return value


def _validate_symmetry(finder):
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
    """None when there is no saved state: `--seeds` accepts negatives, so no
    numeric sentinel is safe (#516)."""
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
        # Missing "seed" reads as ahead of any state so it reruns; a numeric
        # default could collide with a real negative seed (#516).
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
    return (
        getattr(finder, "load_state", None) is not None,
        getattr(finder, "save_state", None) is not None,
    )


def _is_stateful(finder):
    return all(_state_hooks(finder))


def _validate_stateful(finder):
    """Load-only never writes state.json, so every resume trims back to the
    start; save-only writes a state it never reads (#664)."""
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
    """Returns (candidate, verdict, key); verdict and key are None when there
    is no candidate or it was rejected. `no_verify` skips `finder.verify` and
    treats the candidate as accepted, for `hunt verify DIR` (#489) to check later.
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
        # finder.key() is outside this try so a finder's own ValueError is
        # never relabelled a symmetry failure.
        if symmetry in (D4, IDENTITY):
            raise
        raise SymmetryMismatch(str(e)) from e
    return candidate, verdict, key


def _is_empty(candidate):
    return candidate is None or isinstance(candidate, Empty)


def _process_seed(
    finder, seed, seen, symmetry, append_example, append_event, counts, no_verify
):
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
    finder's key shape. Two checks, both before any write (#525):

    1. The group against the key length recorded in examples.jsonl (covers a
       resume whose whole seed range is already done).
    2. The first un-done seed's real key (covers a `key()` shape that changed
       since the last run).

    D4 and IDENTITY skip both (#529). `done_seeds` must be the reconciled set.
    `_load_state` must run first so the probe snapshots resumed state, not
    the finder's fresh default.
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

    # Reconciliation only edits these lists; every write waits until the
    # symmetry check below passes (#525).
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

    # verified.jsonl describes the examples.jsonl it read (#517); delete it before
    # reconciling or appending so a kill cannot leave it stale.
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
    DIR/verified.jsonl -- the deferred half of a `--no-verify` hunt.
    Returns 0, or 2 when DIR has no examples.jsonl or a record fails to
    verify. Each verdict line carries its own record, so it joins back to
    examples.jsonl by content. verified.jsonl is published only on a
    complete run; a failure leaves any existing file untouched (#527).

    Takes the hunt's out/.lock before opening examples.jsonl, so it never
    reads a running hunt's half-written log."""
    args = _parse_dir_args("hunt verify", argv)
    out = Path(args.dir)

    with _held_lock("hunt verify", args.dir) as held:
        if not held:
            return 2
        to_candidate = _candidate_builder(finder)
        try:
            _, records = hunt_files.read_logs(out, stateful=_is_stateful(finder))
        except hunt_files.HuntFileError as error:
            print(f"hunt verify: refusing -- {error}", file=sys.stderr)
            return 2
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


def _run_render(finder, argv):
    """`hunt render DIR`: draw a picture of every example in DIR/examples.jsonl
    to DIR/renders/<seed>.png, a post-pass over a finished hunt. Returns 0, or
    2 on a refusal (a finder with no `render`, DIR locked or without
    examples.jsonl, a record that fails to rebuild or draw).

    Takes the hunt's out/.lock, so it never reads a running hunt's logs. The
    k-th "example" event of progress.jsonl names the seed of the k-th
    examples.jsonl record; a record past the last event is an example a kill
    left unconfirmed, which a resume would trim, so it gets no picture.
    renders/ is replaced as one set by `hunt_files.swap_dir`, which owns the
    swap mechanics and what a kill or a failure leaves behind."""
    args = _parse_dir_args("hunt render", argv)
    out = Path(args.dir)
    render = getattr(finder, "render", None)
    if render is None:
        print("hunt render: refusing -- the finder has no render", file=sys.stderr)
        return 2

    with _held_lock("hunt render", args.dir) as held:
        if not held:
            return 2
        try:
            seeded = hunt_files.read_examples(out, stateful=_is_stateful(finder))
        except hunt_files.HuntFileError as error:
            print(f"hunt render: refusing -- {error}", file=sys.stderr)
            return 2
        to_candidate = _candidate_builder(finder)
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
        print(f"wrote {len(drawn)} pictures to {out / 'renders'}")
        return 0


def _run_summary(finder, argv):
    """`hunt summary DIR`: print the seed span, outcome counts and verified
    hits of the hunt in DIR (`hunt_dir.hunt_summary`), each hit worded by the
    finder's optional `describe_hit(record)`, or the finder's own
    `summary_lines(out)` when it has one. Exit 2 on a bad argument list or
    a directory with no hunt."""
    import hunt_dir  # hunt_dir -> verified_io -> driver: imported late

    describe = getattr(finder, "describe_hit", None)
    own = getattr(finder, "summary_lines", None)
    return hunt_dir.summary_command(
        ["summary", *argv], own or (lambda out: hunt_dir.hunt_summary(out, describe))
    )


def _link_maker(finder):
    """The function that turns a candidate into the text of its link file: the
    finder's `link_text`, else the short link of its `link_document`; None
    when it has neither."""
    from short_link import mint

    text = getattr(finder, "link_text", None)
    if text is not None:
        return text
    document = getattr(finder, "link_document", None)
    return None if document is None else lambda candidate: mint(document(candidate))


def _run_links(finder, argv):
    """`hunt links DIR`: write DIR/links/<seed>.txt, the link of each verified
    hit, replacing `links/` as one set: the finder's `link_text(candidate)`
    verbatim, else the short link of its `link_document(candidate)`. A
    refusal from either names the seed. An unverified example gets none: run
    `verify DIR` first. Returns 0, or 2 on a refusal (a finder with neither
    hook, DIR locked or holding no hunt, a hit that does not rebuild or
    link)."""
    import hunt_dir
    from verified_io import example_verdicts

    args = _parse_dir_args("hunt links", argv)
    out = Path(args.dir)
    make = _link_maker(finder)
    if make is None:
        print(
            "hunt links: refusing -- the finder has no link_document or link_text",
            file=sys.stderr,
        )
        return 2
    with _held_lock("hunt links", args.dir) as held:
        if not held:
            return 2
        try:
            run_json = hunt_files.read_json(out / "run.json")
            seeded = hunt_files.read_examples(out, stateful=_is_stateful(finder))
            verdicts = example_verdicts(
                out, run_json["argv"], [record for _, record in seeded]
            )
            to_candidate = _candidate_builder(finder)
            built = {}
            for (seed, record), verdict in zip(seeded, verdicts, strict=True):
                if verdict != "hit":
                    continue
                try:
                    built[seed] = make(to_candidate(record)).removesuffix("\n") + "\n"
                except ValueError as e:
                    raise ValueError(f"seed {seed}: {e}") from e
            hunt_dir.replace_links(out, built)
            skipped = len(seeded) - len(built)
        except Exception as e:
            print(
                f"hunt links: refusing -- {type(e).__name__}: {e}; links/ was "
                "left as it was",
                file=sys.stderr,
            )
            return 2
        print(f"wrote {len(built)} links to {out / 'links'}")
        if skipped:
            print(f"{skipped} candidates skipped: not verified hits (`summary {out}`)")
        return 0


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
    dispatch `argv[0]` of `verify`, `render`, `summary` or `links` to its
    subcommand. A completed hunt calls the finder's optional `finish(out)`.
    Returns 0 on a completed hunt, 2 on a refusal.
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

    # Lock before reading run.json: classifying --out as fresh or resumed
    # from a pre-lock read can be stale once the lock is granted (a finished
    # hunt would be overwritten and replayed).
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
        # A fresh hunt's output is only this attempt's, so tear it down; a
        # resume refuses before writing, so there is nothing to restore.
        print(f"hunt: refusing to run -- invalid symmetry group: {e}", file=sys.stderr)
        if not is_resume:
            _cleanup_partial_output(out)
        return 2
    finally:
        hunt_files.release_lock(lock_fd)

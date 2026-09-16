"""The hunt driver: `run(finder, argv)` (#483/#484/#487).

A thin loop over a finder's `propose`/`verify`/`record`/`key`: it owns the
output directory, inline verification, dedupe and resume after a kill -- no
finder rule, no search strategy. A fresh `--out` (no `run.json`) starts a
new hunt; an `--out` that already has one resumes it: seeds with a
`seed_done` event are skipped, the dedupe set is rebuilt from the durable
log, and a finder's optional `save_state`/`load_state` round-trip through
state.json. A differing argv versus the recorded run refuses to start; a
differing git sha only warns. The grid helpers, CP-SAT helpers, the
`--workers`/load gate, deferred verification and the render hook are the
other later tickets (#485-#490) under the parent spec (#483).

    uv run finders/hunt/toy_finder.py --out DIR --seeds START:END

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
import os
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedupe import D4, IDENTITY, canonical_key, validate_group

OUTPUT_FILES = (
    "examples.jsonl",
    "summary.json",
    "progress.jsonl",
    "run.json",
    "state.json",
)
REPO_ROOT = Path(__file__).resolve().parents[2]

_OUTCOME_COUNT_KEY = {
    "empty": "empty",
    "rejected": "rejected",
    "duplicate": "duplicates",
    "example": "examples",
}

_DEDUPE_KEY_FIELD = "__dedupe_key__"


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
    return parser.parse_args(_merge_seeds_token(argv))


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


def _refuse(out_arg, why):
    print(f"hunt: refusing to run -- {out_arg} already has {why}", file=sys.stderr)
    return 2


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


def _process_seed(finder, seed, seen, symmetry, examples_f, progress_f, counts):
    """Run one seed and append its outcome to examples.jsonl/progress.jsonl,
    updating `seen` and `counts` in place. Shared by the fresh and resumed
    loops so the two can't drift apart on what a seed's outcome means."""
    candidate = finder.propose(random.Random(seed))
    event = {"event": "seed_done", "seed": seed}
    if candidate is None:
        counts["empty"] += 1
        event["outcome"] = "empty"
    else:
        verdict = finder.verify(candidate)
        if not verdict.ok:
            counts["rejected"] += 1
            event["outcome"] = "rejected"
            if verdict.reason:
                event["rejected_reason"] = verdict.reason
        else:
            key = canonical_key(finder.key(candidate), symmetry)
            if key in seen:
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

    progress_f.write(json.dumps(event) + "\n")
    progress_f.flush()
    counts["seeds_done"] += 1


def _hunt_loop(finder, out, seed_start, seed_end, seen, counts, skip=frozenset()):
    symmetry = getattr(finder, "symmetry", D4)
    with (
        (out / "examples.jsonl").open("a") as examples_f,
        (out / "progress.jsonl").open("a") as progress_f,
    ):
        for seed in range(seed_start, seed_end):
            if seed in skip:
                continue
            _process_seed(finder, seed, seen, symmetry, examples_f, progress_f, counts)
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

    _hunt_loop(finder, out, seed_start, seed_end, set(), counts)
    return 0


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
    progress_lines, progress_events, examples_lines, examples_records = _reconcile(
        finder, out, progress_lines, progress_events, examples_lines, examples_records
    )
    _truncate_to_valid(out / "progress.jsonl", progress_lines)
    _truncate_to_valid(out / "examples.jsonl", examples_lines)

    done_seeds = {e["seed"] for e in progress_events if e.get("event") == "seed_done"}
    seen = {_to_hashable(r[_DEDUPE_KEY_FIELD]) for r in examples_records}

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
    _load_state(finder, out)

    _hunt_loop(finder, out, seed_start, seed_end, seen, counts, skip=done_seeds)
    return 0


def run(finder, argv):
    """Run or resume a hunt for `finder` over the seed range in `argv`.

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
    args = _parse_args(argv)
    refusal = _validate_symmetry(finder)
    if refusal is not None:
        return refusal
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # Taken before anything about --out's state is inspected, not just
    # before anything is written: classifying --out as fresh or resumed by
    # reading run.json *before* acquiring this lock is itself a race
    # (#812 Codex pass 1, finding 1) -- a second process can see no
    # run.json, then, delayed by ordinary scheduling rather than by
    # blocking on this non-blocking lock, acquire it only after a first
    # process's complete fresh hunt has already finished and released it.
    # Acting on that stale "no run.json" belief overwrites the finished
    # hunt and replays every seed. Locking first makes every read below an
    # authoritative one. `flock` is tied to the open fd, so a SIGKILLed
    # holder releases it the instant the process dies -- no stale lock to
    # clean up before the next, real resume.
    lock_fd = os.open(out / ".lock", os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(lock_fd)
        return _refuse(args.out, "an active hunt (locked)")

    try:
        run_path = out / "run.json"
        if run_path.exists():
            prior = json.loads(run_path.read_text())
            if prior.get("argv") != list(argv):
                print(
                    "hunt: refusing to resume -- argv differs from the recorded run "
                    f"({prior.get('argv')!r} vs {list(argv)!r})",
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
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)

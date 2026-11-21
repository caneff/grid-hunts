"""A hunt directory read back: examples by seed, the `links/` beside them
(#774, #71), and the seeds and verdicts `summary DIR` reports."""

import json
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hunt_files
from verified_io import example_verdicts


class HuntRead(NamedTuple):
    """A hunt's run.json, its `seed_done` events, and its examples split by
    verdict: `hits` passed `verify`, `unchecked` await it, `rejected` pairs
    each refused record with the reason."""

    run: dict
    events: list
    hits: list
    unchecked: list
    rejected: list


def read_hunt(out):
    """The hunt in `out`, its examples split by `example_verdicts`."""
    out = Path(out)
    all_events, examples = hunt_files.read_logs(out)
    events = [e for e in all_events if e.get("event") == "seed_done"]
    run = hunt_files.read_json(out / "run.json")
    found = example_verdicts(out, run["argv"], examples)
    verdicts = list(zip(examples, found, strict=True))
    return HuntRead(
        run,
        events,
        [r for r, v in verdicts if v == "hit"],
        [r for r, v in verdicts if v == "unchecked"],
        [(r, v) for r, v in verdicts if v not in ("hit", "unchecked")],
    )


def seed_lines(events):
    """One line per seed that found nothing or was rejected, with why."""
    lines = []
    for e in events:
        if e["outcome"] == "empty":
            lines.append(
                f"seed {e['seed']}: {e.get('empty_reason', 'no reason given')}"
            )
        elif e["outcome"] == "rejected":
            reason = e.get("rejected_reason", "no reason given")
            lines.append(f"seed {e['seed']}: rejected, {reason}")
    return lines


def summary_command(argv, summary):
    """`hunt.py summary DIR`: print `summary(DIR)`'s lines; exit 2 on a bad
    argument list, a directory with no run.json, or a ValueError."""
    if len(argv) != 2:
        print("usage: hunt.py summary DIR", file=sys.stderr)
        return 2
    out = Path(argv[1])
    if not (out / "run.json").exists():
        print(f"hunt.py summary: {out} holds no hunt (no run.json)", file=sys.stderr)
        return 2
    try:
        text = summary(out)
    except ValueError as error:
        print(f"hunt.py summary: {error}", file=sys.stderr)
        return 2
    print("\n".join(text))
    return 0


def seed_span(events):
    """`N seeds (first..last)`, or `0 seeds` with none."""
    seeds = sorted(e["seed"] for e in events)
    return f"{len(seeds)} seeds" + (f" ({seeds[0]}..{seeds[-1]})" if seeds else "")


def default_counts(events):
    """The driver's outcome line: found, empty, timed out, duplicate, rejected
    -- an empty seed whose reason starts `timeout` counts as timed out."""
    outcome = Counter(e["outcome"] for e in events)
    timed_out = sum(
        1
        for e in events
        if e["outcome"] == "empty"
        and e.get("empty_reason", "").split(":")[0] == "timeout"
    )
    return (
        f"found {outcome['example']}, empty {outcome['empty'] - timed_out}, "
        f"timed out {timed_out}, duplicate {outcome['duplicate']}, "
        f"rejected {outcome['rejected']}"
    )


def _lines(text):
    return [text] if isinstance(text, str) else list(text)


class Wording(NamedTuple):
    """What a finder says in `summary DIR`; the layout is `summary_layout`'s.

    `hit_noun` and `tail(run)` and `none_note` word the headline; `counts(events)`
    is the outcome line, placed after the unchecked/rejected lines when
    `counts_last`. `describe_hit(record)`, `describe_unchecked(record)` and
    `describe_rejected(record, reason)` return a line or lines, and one left
    None lists nothing (`describe_hit` None prints the record as JSON);
    `hit_key` orders the hits."""

    hit_noun: str = "verified hits"
    tail: Callable = lambda run: ""
    none_note: str = ""
    counts: Callable = default_counts
    counts_last: bool = False
    describe_hit: Callable | None = None
    describe_unchecked: Callable | None = None
    describe_rejected: Callable | None = None
    hit_key: Callable | None = None


def summary_layout(hunt, wording):
    """The lines `summary DIR` prints for a `HuntRead`, in one order for every
    finder: the headline, the outcome line, the unchecked and rejected
    counts, each non-finding seed's reason, then the hit, unchecked and
    rejected records as `wording` words them. The verify hint is the driver's
    `verify DIR` whoever words the rest."""
    run, events, hits, unchecked, rejected = hunt
    span = seed_span(events)
    tail = wording.tail(run)
    if hits:
        headline = f"{len(hits)} {wording.hit_noun} in {span}{tail}"
    elif unchecked or rejected:
        headline = f"no verified hit in {span}{tail}"
    else:
        headline = f"none found in {span}{tail}{wording.none_note}"
    flags = []
    if unchecked:
        flags.append(
            f"{len(unchecked)} candidates unchecked: the hunt ran with "
            "--no-verify and `verify DIR` has not run"
        )
    if rejected:
        flags.append(f"{len(rejected)} candidates rejected by `verify DIR`")
    counts = [wording.counts(events)]
    text = [headline, *(flags + counts if wording.counts_last else counts + flags)]
    text.extend(seed_lines(events))
    describe = wording.describe_hit or _record_json
    ordered = sorted(hits, key=wording.hit_key) if wording.hit_key else hits
    for record in ordered:
        text.extend(_lines(describe(record)))
    if wording.describe_unchecked:
        for record in unchecked:
            text.extend(_lines(wording.describe_unchecked(record)))
    if wording.describe_rejected:
        for record, reason in rejected:
            text.extend(_lines(wording.describe_rejected(record, reason)))
    return text


def hunt_summary(out, describe_hit=None):
    """The lines `hunt summary DIR` prints for the driver's protocol: the
    layout of `summary_layout` with the default wording, each verified hit
    worded by the finder's `describe_hit(record)` (its record as JSON
    without one)."""
    return summary_layout(read_hunt(out), Wording(describe_hit=describe_hit))


def _record_json(record):
    shown = {k: v for k, v in record.items() if k != "__dedupe_key__"}
    return "hit " + json.dumps(shown, sort_keys=True)


def replace_links(out, built):
    """Replace `out/links/` with `{seed: link text}` as one set; returns it."""

    def write(directory):
        for seed, text in built.items():
            (directory / f"{seed}.txt").write_text(text)

    links = Path(out) / "links"
    hunt_files.swap_dir(links, write)
    return links

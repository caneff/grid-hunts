"""A hunt directory read back: examples by seed, the `links/` beside them, and
the seeds and verdicts `summary DIR` reports."""

import json
import sys
from collections import Counter
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


def hunt_summary(out, describe_hit=None):
    """The lines `hunt summary DIR` prints for the driver's protocol: the seed
    span, the outcome counts (found, empty, timed out, duplicate, rejected --
    an empty seed whose reason starts `timeout` counts as timed out), the
    unchecked and rejected candidates, each non-finding seed's reason and one
    line per verified hit, worded by the finder's `describe_hit(record)` (its
    record as JSON without one)."""
    _run, events, hits, unchecked, rejected = read_hunt(out)
    seeds = sorted(e["seed"] for e in events)
    span = f"{len(seeds)} seeds" + (f" ({seeds[0]}..{seeds[-1]})" if seeds else "")
    outcome = Counter(e["outcome"] for e in events)
    timed_out = sum(
        1
        for e in events
        if e["outcome"] == "empty"
        and e.get("empty_reason", "").split(":")[0] == "timeout"
    )
    describe = describe_hit or _record_json
    text = [
        f"{len(hits)} verified hits in {span}"
        if hits
        else f"no verified hit in {span}"
        if unchecked or rejected
        else f"none found in {span}",
        f"found {outcome['example']}, empty {outcome['empty'] - timed_out}, "
        f"timed out {timed_out}, duplicate {outcome['duplicate']}, "
        f"rejected {outcome['rejected']}",
    ]
    if unchecked:
        text.append(
            f"{len(unchecked)} candidates unchecked: the hunt ran with "
            "--no-verify and `verify DIR` has not run"
        )
    if rejected:
        text.append(f"{len(rejected)} candidates rejected by `verify DIR`")
    text.extend(seed_lines(events))
    text.extend(describe(record) for record in hits)
    return text


def _record_json(record):
    shown = {k: v for k, v in record.items() if k != "__dedupe_key__"}
    return "hit " + json.dumps(shown, sort_keys=True)


def seeded_examples(out):
    """[(seed, record)] for every example of the hunt in `out`, paired the
    way the driver pairs them (`hunt_files.read_examples`). Raises
    ValueError, naming it, on a missing or unreadable log."""
    return hunt_files.read_examples(out)


def replace_links(out, built):
    """Replace `out/links/` with `{seed: link text}` as one set; returns it."""

    def write(directory):
        for seed, text in built.items():
            (directory / f"{seed}.txt").write_text(text)

    links = Path(out) / "links"
    hunt_files.swap_dir(links, write)
    return links

"""A hunt directory read back: its examples by seed and the `links/` a
finder writes beside them (#774, #71), shared by the U-Bahn finders and
`doppelganger_rank`; and the seeds and verdicts a hunt's `summary DIR`
reports (`read_hunt`, `summary_command`), shared by the halver hunts and
`doppelganger_rank`."""

import json
import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verified_io import example_verdicts


def _jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


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
    events = [
        e for e in _jsonl(out / "progress.jsonl") if e.get("event") == "seed_done"
    ]
    examples = _jsonl(out / "examples.jsonl")
    run = json.loads((out / "run.json").read_text())
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
    """`hunt.py summary DIR`: print `summary(DIR)`'s lines. Exit 2, naming
    why, on a wrong argument list, a directory with no run.json, or a
    ValueError from `summary`."""
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


def seeded_examples(out):
    """[(seed, record)] for every example of the hunt in `out`, paired the
    way the driver pairs renders: the k-th "example" event of progress.jsonl
    is the k-th examples.jsonl record. Raises ValueError, naming it, on a
    missing or unpaired log."""
    out = Path(out)

    def lines(name):
        path = out / name
        if not path.is_file():
            raise ValueError(f"{out} has no {name}: not a hunt directory")
        return [json.loads(line) for line in path.read_text().splitlines() if line]

    records = lines("examples.jsonl")
    seeds = [
        e["seed"] for e in lines("progress.jsonl") if e.get("outcome") == "example"
    ]
    if len(seeds) != len(records):
        raise ValueError(
            f"{len(records)} examples but {len(seeds)} example events in progress.jsonl"
        )
    return list(zip(seeds, records, strict=True))


def replace_links(out, built):
    """Replace `out/links/` with `{seed: link text}`: a file left by an
    earlier example list or variant never stays. Returns the directory."""
    links = Path(out) / "links"
    links.mkdir(exist_ok=True)
    for stale in links.glob("*.txt"):
        stale.unlink()
    for seed, text in built.items():
        (links / f"{seed}.txt").write_text(text)
    return links

"""A hunt directory's examples, read by seed, and the `links/` a finder
writes beside them (#774, #71): shared by the U-Bahn finders and
`doppelganger_rank`."""

import json
from pathlib import Path


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

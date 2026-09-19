"""Merge the census output and annotate every configuration with its solution count.

    uv run finders/counting_shaded/batch_count.py .scratch/counting_shaded/*/configurations.jsonl \
        --out docs/research/counting_shaded/connected-corpus.jsonl

Nothing is rejected. A configuration with 40,000 solutions is as much a part of
the corpus as a unique one -- it is a valid connected all-visible shaded cell grid
either way, and the whole point of collecting before filtering is that we do
not yet know which properties will matter.

Each row gains `solutions`, the count from the bounded bitmask counter, and
`capped`, true when the count hit `--cap` and the real total is higher. Rows
are deduplicated across input files (the census processes dedupe only against
themselves) and, with --canonical, under the 8 square symmetries as well.

The counter runs over the givens alone, which is correct here: with every shaded cell
visible the shaded cell rule is redundant, since all solutions agree on the shaded cell
cells, so the board is a plain sudoku whose givens are the shaded cell digits. See
docs/research/2026-09-16-counting-shaded-connected.md.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from harvest import canonical
from shapes import NEIGH, connected, count_solutions


def givens_of(shape):
    """{cell: shaded-neighbour count} -- the givens the shape puts on the board."""
    s = set(shape)
    return {i: sum(j in s for j in NEIGH[i]) for i in s}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--cap", type=int, default=1000)
    ap.add_argument("--canonical", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()

    rows, seen, dupes = [], set(), 0
    for path in a.files:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = canonical(set(row["shape"])) if a.canonical else tuple(row["shape"])
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            rows.append(row)

    bad = 0
    by_size = defaultdict(Counter)
    for row in rows:
        shape = row["shape"]
        if not connected(set(shape)):
            bad += 1
            row["solutions"] = None
            continue
        gv = givens_of(shape)
        n = count_solutions(gv, a.cap)
        row["solutions"] = n
        row["capped"] = n >= a.cap
        bucket = "1" if n == 1 else f"{a.cap}+" if n >= a.cap else "2+"
        by_size[len(shape)][bucket] += 1

    print(f"{len(rows)} configurations ({dupes} duplicates dropped)")
    if bad:
        print(f"WARNING: {bad} rows are not connected")
    print(f"{'shaded':>7} {'unique':>7} {'2..cap':>7} {'cap+':>7}")
    for size in sorted(by_size):
        c = by_size[size]
        print(f"{size:>7} {c['1']:>7} {c['2+']:>7} {c[f'{a.cap}+']:>7}")
    total_unique = sum(c["1"] for c in by_size.values())
    print(f"unique overall: {total_unique} of {len(rows)}")
    fewest = min(
        (r for r in rows if r.get("solutions")),
        key=lambda r: r["solutions"],
        default=None,
    )
    if fewest:
        print(
            f"closest to unique: {fewest['solutions']} solutions "
            f"at {fewest['shaded']} shaded cells, shape {fewest['shape']}"
        )
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("w") as fh:
            for row in sorted(rows, key=lambda r: (r["shaded"], r["shape"])):
                fh.write(json.dumps(row) + "\n")
        print(f"wrote {a.out}")


if __name__ == "__main__":
    main()

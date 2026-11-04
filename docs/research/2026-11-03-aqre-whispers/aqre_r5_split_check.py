"""SCRATCH: a stronger check of `aqre_r5_split_enumerate.py`'s strict layouts. One worker.

For the placements that have layouts, the lists are cut to every region used by a known strict layout
plus a random sample. The join and a plain whole-board search must then return the same layouts, of any
class and strict, and the strict set must hold every known layout. Separately, each of the 490 layouts on
file is re-read cell by cell: nine connected regions of 9, the 8 region's mask, one forced 7, six low
regions with counts 1-6 matchable, read from the table and not through the join.
"""

import json
import pickle
import random
import sys
import time
from pathlib import Path

from aqre_jigsaw_feasible import connected
from aqre_r5_cover import mask_of
from aqre_r5_fixed_regions import can_match
from aqre_r5_split_count import ROW
from aqre_r5_split_enumerate import halves, join, placements, plain_search, region_of, strict, usable

SAMPLE = 15
LIMIT = 600.0


def reread(table, record):
    """Check one layout on file from its grid alone. Returns an error or None."""
    c8, n = record["c8"], record["n"]
    groups = {}
    for r, row in enumerate(record["region"]):
        for q, label in enumerate(row):
            groups.setdefault(label, []).append((r, q))
    if len(groups) != 9 or any(len(v) != 9 for v in groups.values()):
        return "not nine regions of 9"
    if any(not connected(set(v)) for v in groups.values()):
        return "a region is not connected"
    if {r for r, _ in groups[n]} & {ROW}:
        return "ninth region touches r5"
    if not {(ROW, c8), (ROW, n)} <= set(groups[c8]):
        return "8 region lacks its two r5 cells"
    sevens = 0
    lows = []
    for c, cells in groups.items():
        if c in (c8, n):
            continue
        if (ROW, c) not in cells or sum(r == ROW for r, _ in cells) != 1:
            return f"region {c} has wrong r5 cells"
        mask = mask_of(cells)
        entry = next((e for e in table[c] if e["mask"] == mask), None)
        if entry is None:
            return f"region {c} not in the table"
        able_8, shaded_7, unshaded_7, counts = entry[c % 2 == c8 % 2]
        if able_8:
            return f"region {c} can be the 8"
        if shaded_7 or unshaded_7:
            if shaded_7 == unshaded_7:
                return f"region {c} has an unforced 7"
            sevens += 1
        else:
            lows.append(counts)
    if sevens != 1 or not can_match(lows):
        return f"{sevens} sevens or unmatched low counts"
    return None


def main(out):
    with (out / "oriented.pickle").open("rb") as f:
        table = pickle.load(f)
    records = [json.loads(line) for line in (out / "split-layouts.jsonl").read_text().splitlines()]
    errors = [e for e in (reread(table, x) for x in records) if e]
    print(f"re-read {len(records)} layouts: {len(errors)} errors {errors[:3]}", flush=True)
    good = not errors
    rng = random.Random(11)
    seen = set()
    for eight, c8, n in placements(out):
        known = [x for x in records if x["c8"] == c8 and x["n"] == n and region_of_matches(x, eight, c8)]
        if not known or (eight, c8) in seen:
            continue
        seen.add((eight, c8))
        pairs = usable(table, eight, c8, n)
        free, ninth = halves(eight)
        wanted = set()
        for x in known:
            groups = {}
            for r, row in enumerate(x["region"]):
                for q, label in enumerate(row):
                    groups.setdefault(label, []).append((r, q))
            wanted |= {mask_of(v) for c, v in groups.items() if c not in (c8, n)}
        small = {}
        for c in pairs:
            pick = rng.sample(sorted(pairs[c]), min(SAMPLE, len(pairs[c])))
            keep = {k: pairs[c][k] for k in pick}
            keep.update({k: v for k, v in pairs[c].items() if v[0] in wanted})
            small[c] = keep
        begun = time.time()
        joined = list(join(free, small, ninth, {}))
        by_join = {frozenset(e[0] for e in y) for y in joined}
        strict_join = {frozenset(e[0] for e in y) for y in joined if strict(y)}
        try:
            plain = plain_search(small, eight, time.time() + LIMIT)
        except TimeoutError:
            print(f"8 in r5c{c8 + 1}, 9 in r5c{n + 1}: plain search capped, {sum(len(v) for v in small.values())} regions; join {len(by_join)} layouts", flush=True)
            continue
        by_plain = {frozenset(e[0] for e in y) for y in plain}
        strict_plain = {frozenset(e[0] for e in y) for y in plain if strict(y)}
        same = by_join == by_plain and strict_join == strict_plain and len(strict_join) >= len(known)
        good = good and same
        print(f"8 in r5c{c8 + 1}, 9 in r5c{n + 1}: {sum(len(v) for v in small.values())} regions, join {len(by_join)} layouts and {len(strict_join)} strict, plain {len(by_plain)} and {len(strict_plain)}, known {len(known)}, {time.time() - begun:.0f}s: {'ok' if same else 'FAILED'}", flush=True)
    print(f"CHECK {'PASSED' if good else 'FAILED'}", flush=True)


def region_of_matches(record, eight, c8):
    return all(bool(eight >> (r * 9 + q) & 1) == (label == c8) for r, row in enumerate(record["region"]) for q, label in enumerate(row))


if __name__ == "__main__":
    main(Path(sys.argv[1]))

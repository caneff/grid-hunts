"""SCRATCH: the 490 layouts read against Chris's wording of 2026-11-04.

Only one region may be able to be the 8 by shape alone, so colour is not known for that test. The
enumerator judged the other regions with colour known, and a shaded 8 on the low colour always fails,
so a region on the 8's opposite colour was never refused for its 8. This counts how many layouts have
no other r5 region able to be the 8 on either colour, and how each layout's 7 is forced.
"""

import json
import pickle
import sys
from collections import Counter
from pathlib import Path

from aqre_r5_cover import mask_of


def main(out):
    with (out / "oriented.pickle").open("rb") as f:
        table = pickle.load(f)
    by_mask = {c: {e["mask"]: e for e in table[c]} for c in table}
    records = [json.loads(line) for line in (out / "split-layouts.jsonl").read_text().splitlines()]
    kept = 0
    sevens = Counter()
    kept_sevens = Counter()
    others = Counter()
    for x in records:
        c8, n = x["c8"], x["n"]
        groups = {}
        for r, row in enumerate(x["region"]):
            for q, label in enumerate(row):
                groups.setdefault(label, []).append((r, q))
        able = 0
        kind = None
        for c, cells in groups.items():
            if c in (c8, n):
                continue
            e = by_mask[c][mask_of(cells)]
            able += e[True][0] or e[False][0]
            same = c % 2 == c8 % 2
            _, shaded_7, unshaded_7, _ = e[same]
            if shaded_7 or unshaded_7:
                kind = f"{'same' if same else 'opposite'} colour, forced {'shaded' if shaded_7 else 'unshaded'}"
        sevens[kind] += 1
        others[able] += 1
        if not able:
            kept += 1
            kept_sevens[kind] += 1
    print(f"{len(records)} layouts; other r5 regions able to be the 8 by shape alone: {sorted(others.items())}")
    print(f"{kept} layouts have no other 8-able r5 region")
    print("7 in all layouts:", sorted(sevens.items()))
    print("7 in those kept:", sorted(kept_sevens.items()))


if __name__ == "__main__":
    main(Path(sys.argv[1]))

"""SCRATCH: every layout for Chris's chosen 8 region, by splitting the board at r5. One worker.

For each of the 14 placements kept after symmetry, this lists how the rows above r5 fill from the
regions' up parts and the rows below from their down parts, with the ninth region on either side. It
joins the two where sizes match, then keeps a pair when every region's two parts form a listed region,
exactly one is a forced 7 and the six low regions can take counts 1-6. Regions are judged alone, with
the colour known from the 8, as in `aqre_r5_oriented.py`.

All layouts are written first, so an empty result is a proof for this shape on these lists. Then each
layout goes to the fixed-region solve, stopping at the first grid.

Self-check: on sampled lists holding a planted layout, the join must return the same layouts as a plain
whole-board search. On every placement the fillings listed must equal the memo's count.
"""

import json
import pickle
import random
import sys
import time
from pathlib import Path

from aqre_jigsaw_r5_staged import finish
from aqre_r5_cover import FULL, components, mask_of
from aqre_r5_fixed_regions import attempt, can_match
from aqre_r5_oriented import canonical
from aqre_r5_split_count import ALL_HALF, ROW, SHAPE, Filler, connected_pieces, split
from jigsaw_r5_diversity import shape_key

CELLS = [(r, q) for r in range(9) for q in range(9)]
SAMPLE = 40
CHECK_SECONDS = 300.0
FULL_SIZES = sum(8 << (4 * i) for i in range(7))


def usable(table, eight, c8, n):
    """For each root column: (up, down) -> (region mask, is it the 7, its low counts)."""
    parity = c8 % 2
    pairs = {}
    for c in range(9):
        if c in (c8, n):
            continue
        found = {}
        for e in table[c]:
            mask = e["mask"]
            if mask & eight or any(mask >> (ROW * 9 + q) & 1 for q in range(9) if q != c):
                continue
            able_8, shaded_7, unshaded_7, counts = e[c % 2 == parity]
            if able_8:
                continue
            if shaded_7 or unshaded_7:
                if shaded_7 != unshaded_7:
                    found[split(mask)] = (mask, True, ())
            elif counts:
                found[split(mask)] = (mask, False, tuple(counts))
        pairs[c] = found
    return pairs


def fillings(filler):
    """Yield each filling as a tuple of parts, one per root. Dead branches are cut by the memo."""
    memo = {}

    def live(free, unused, ninth_left):
        if not free:
            return int(not ninth_left and filler._finished(unused))
        key = free | unused << 36 | ninth_left << 43
        known = memo.get(key)
        if known is not None:
            return known
        total = 0
        if filler._viable(free, unused):
            low = free & -free
            for i, p in filler._choices(free, unused, low):
                total += live(free ^ p, unused ^ 1 << i, ninth_left)
            if ninth_left:
                for p in filler.ninth.get(low, ()):
                    if not p & ~free:
                        total += live(free ^ p, unused, False)
        memo[key] = total
        return total

    parts = [0] * len(filler.roots)

    def walk(free, unused, ninth_left):
        if not live(free, unused, ninth_left):
            return
        if not free:
            yield tuple(parts)
            return
        low = free & -free
        for i, p in filler._choices(free, unused, low):
            parts[i] = p
            yield from walk(free ^ p, unused ^ 1 << i, ninth_left)
            parts[i] = 0
        if ninth_left:
            for p in filler.ninth.get(low, ()):
                if not p & ~free:
                    yield from walk(free ^ p, unused, False)

    start = (filler.free, (1 << len(filler.roots)) - 1, filler.has_ninth)
    return live(*start), walk(*start)


def sizes_of(filling):
    return sum(bin(p).count("1") << (4 * i) for i, p in enumerate(filling))


def join(free, pairs, ninth, tally):
    """Yield each top and bottom pair whose parts all form listed regions, as region entries."""
    roots = sorted(pairs)
    lookups = [pairs[c] for c in roots]
    up = {c: {a for a, _ in pairs[c]} for c in roots}
    down = {c: {b for _, b in pairs[c]} for c in roots}
    for top_has in (True, False):
        top = Filler(free["top"], roots, up, ninth["top"] if top_has else set())
        bottom = Filler(free["bottom"], roots, down, ninth["bottom"] if not top_has else set())
        top_count, top_walk = fillings(top)
        bottom_count, bottom_walk = fillings(bottom)
        tally["top"] = tally.get("top", 0) + top_count
        tally["bottom"] = tally.get("bottom", 0) + bottom_count
        keep_top = top_count <= bottom_count
        kept, streamed = (top_walk, bottom_walk) if keep_top else (bottom_walk, top_walk)
        stored = {}
        listed = 0
        for filling in kept:
            listed += 1
            stored.setdefault(sizes_of(filling), []).append(filling)
        for filling in streamed:
            listed += 1
            for other in stored.get(FULL_SIZES - sizes_of(filling), ()):
                tally["matched"] = tally.get("matched", 0) + 1
                a, b = (other, filling) if keep_top else (filling, other)
                entries = []
                for i, lookup in enumerate(lookups):
                    entry = lookup.get((a[i], b[i]))
                    if entry is None:
                        break
                    entries.append(entry)
                else:
                    tally["listed"] = tally.get("listed", 0) + 1
                    yield entries
        if listed != top_count + bottom_count:
            raise AssertionError(f"listed {listed} fillings, memo counted {top_count + bottom_count}")


def strict(entries):
    sevens = sum(e[1] for e in entries)
    return sevens == 1 and can_match([e[2] for e in entries if not e[1]])


def halves(eight):
    top_taken, bottom_taken = split(eight)
    free = {"top": ALL_HALF & ~top_taken, "bottom": ALL_HALF & ~bottom_taken}
    return free, {side: connected_pieces(free[side], 9) for side in free}


def plain_search(pairs, eight, deadline):
    """Every layout by whole-board masks, sharing no half logic with the join."""
    options = sorted(([e for e in pairs[c].values()] for c in sorted(pairs)), key=len)
    found = []

    def go(i, used, chosen):
        if time.time() > deadline:
            raise TimeoutError
        if i == len(options):
            if len(components(FULL & ~used)) == 1:
                found.append(list(chosen))
            return
        for e in options[i]:
            if not e[0] & used:
                chosen.append(e)
                go(i + 1, used | e[0], chosen)
                chosen.pop()

    go(0, eight, [])
    return found


def self_check(pairs, eight):
    free, ninth = halves(eight)
    planted = next(join(free, pairs, ninth, {}), None)
    if planted is None:
        print("check: no layout of any class to plant", flush=True)
        return False
    rng = random.Random(3)
    planted_masks = {e[0] for e in planted}
    small = {}
    for c in pairs:
        pick = rng.sample(sorted(pairs[c]), min(SAMPLE, len(pairs[c])))
        keep = {k: pairs[c][k] for k in pick}
        keep.update({k: v for k, v in pairs[c].items() if v[0] in planted_masks})
        small[c] = keep
    joined = list(join(free, small, ninth, {}))
    plain = plain_search(small, eight, time.time() + CHECK_SECONDS)
    by_join = {frozenset(e[0] for e in x) for x in joined}
    by_plain = {frozenset(e[0] for e in x) for x in plain}
    strict_join = {frozenset(e[0] for e in x) for x in joined if strict(x)}
    strict_plain = {frozenset(e[0] for e in x) for x in plain if strict(x)}
    good = by_join == by_plain and frozenset(planted_masks) in by_join and strict_join == strict_plain and len(joined) == len(by_join)
    print(f"check: join {len(by_join)} layouts of any class, plain search {len(by_plain)}, strict {len(strict_join)} and {len(strict_plain)}: {'ok' if good else 'FAILED'}", flush=True)
    return good


def region_of(entries, roots, eight, c8, n):
    by_mask = {e[0]: c for e, c in zip(entries, roots)}
    region = {}
    for r, q in CELLS:
        bit = 1 << (r * 9 + q)
        if eight & bit:
            region[r, q] = c8
        else:
            region[r, q] = next((c for mask, c in by_mask.items() if mask & bit), n)
    return region


def placements(out):
    key = shape_key(SHAPE)
    for e in json.loads((out / "eight-regions-r5.json").read_text()):
        cells = [tuple(x) for x in e["cells"]]
        if shape_key(cells) != key:
            continue
        c8 = e["column"]
        eight = mask_of(cells)
        if canonical(eight, c8):
            yield eight, c8, next(q for r, q in cells if r == ROW and q != c8)


def main(out):
    with (out / "oriented.pickle").open("rb") as f:
        table = pickle.load(f)
    found = list(placements(out))
    print(f"{len(found)} placements", flush=True)
    eight, c8, n = found[0]
    if not self_check(usable(table, eight, c8, n), eight):
        print("self-check FAILED; nothing enumerated", flush=True)
        return
    layouts = []
    for number, (eight, c8, n) in enumerate(found, 1):
        begun = time.time()
        pairs = usable(table, eight, c8, n)
        roots = sorted(pairs)
        free, ninth = halves(eight)
        tally = {}
        kept = 0
        for entries in join(free, pairs, ninth, tally):
            if strict(entries):
                kept += 1
                layouts.append((c8, n, region_of(entries, roots, eight, c8, n)))
        print(
            f"placement {number}, 8 in r5c{c8 + 1}, 9 in r5c{n + 1}: {tally.get('top', 0):,} top and {tally.get('bottom', 0):,} bottom fillings, "
            f"{tally.get('matched', 0):,} size matches, {tally.get('listed', 0):,} with listed regions, {kept:,} layouts, {time.time() - begun:.0f}s",
            flush=True,
        )
    with (out / "split-layouts.tmp").open("w") as f:
        for c8, n, region in layouts:
            f.write(json.dumps({"c8": c8, "n": n, "region": [[region[r, q] for q in range(9)] for r in range(9)]}) + "\n")
    (out / "split-layouts.tmp").replace(out / "split-layouts.jsonl")
    print(f"ENUMERATION COMPLETE: {len(layouts):,} layouts across {len(found)} placements", flush=True)
    outcomes = {}
    for i, (c8, n, region) in enumerate(layouts, 1):
        outcome, digits, shade = attempt(region, ROW, n)
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        print(f"layout {i} of {len(layouts)}: {outcome}; tally {outcomes}", flush=True)
        if digits:
            finish(digits, shade, region, n, out)
            print("GRID FOUND", flush=True)
            return
    print(f"ALL LAYOUTS SOLVED: tally {outcomes}, no grid", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

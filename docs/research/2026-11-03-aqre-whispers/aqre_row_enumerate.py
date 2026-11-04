"""SCRATCH: every layout for Chris's chosen 8 shape with the 8 circles in any one row.

usage: aqre_row_enumerate.py DIR ROW [--loose] [--no-solve] [--only=N]   (ROW is 1-9 as in r4; 12 processes)

The rule, Chris 2026-11-04: the row's uncircled cell is the 9. Only one region can be the 8 by shape
alone, which fixes the checkerboard. Of the other row regions, one is a forced 7. Each of the rest tops
out at 6 once colour is known, which includes a 7 allowed only shaded on the wrong colour.
--loose judges the 8 with colour known instead, as the r5 enumerator did; it exists to reproduce r5.

Symmetry: only the left-right mirror keeps a row other than r5 and the checkerboard, so the 8 is in
columns 1-5, and in column 5 one image is kept. The top-bottom flip and the 180 turn change the row.
r5 alone also has those, and uses the placements its earlier runs used.

The shape holds two row cells two columns apart in every placement, counted below, so seven regions
hold one row cell each and the ninth is off the row. The rows above are filled from up parts, then each
root picks a whole region with that up part. The ninth is what is left, and it must be connected.
All layouts are written first, so an empty list is a proof for this shape, row and these lists.
"""

import json
import multiprocessing
import pickle
import sys
import time
from pathlib import Path

import aqre_r5_eight_regions as eight_regions
import aqre_r5_oriented as oriented
import aqre_r5_region_max as region_max
from aqre_jigsaw_r5_staged import draw, read_back
from aqre_r5_chosen_eight import SHAPE
from aqre_r5_cover import FULL, components, mask_of, mirror
from aqre_r5_fixed_regions import attempt, can_match
from aqre_r5_oriented import canonical, holds_coloured
from aqre_r5_region_max import holds, lines_of

WORKERS = 8
CELLS =[(r, q) for r in range(9) for q in range(9)]
STATE = {}
FORK = multiprocessing.get_context("fork")  # workers inherit STATE and each module's ROW


def set_row(row):
    eight_regions.ROW = row
    oriented.ROW = row
    region_max.ROW = row
    STATE["row"] = row


def classify(args):
    """One region's entry, as in `aqre_r5_oriented.build_catalogue`, plus a check of its 8 and 7."""
    cells, c, check = args
    root = (STATE["row"], c)
    lines = lines_of(cells)
    entry = {"mask": mask_of(cells)}
    for root_high in (True, False):
        eight = holds_coloured(cells, root, 8, lines, root_high)
        shaded_7 = holds_coloured(cells, root, 7, lines, root_high, True)
        unshaded_7 = holds_coloured(cells, root, 7, lines, root_high, False)
        counts = ()
        if not (eight or shaded_7 or unshaded_7):
            counts = tuple(v for v in range(1, 7) if holds_coloured(cells, root, v, lines, root_high))
        entry[root_high] = (eight, shaded_7, unshaded_7, counts)
    bad = 0
    if check:
        any_8 = entry[True][0] or entry[False][0]
        any_7 = any(entry[o][1] or entry[o][2] for o in (True, False))
        bad = any_8 != bool(eight_regions.holds_eight(cells, root)) or any_7 != holds(cells, root, 7, lines) or entry[False][0]
    return entry, bad


def build_table(out, row):
    path = out / f"oriented-row{row + 1}.pickle"
    if row == 4:
        path = out / "oriented.pickle"
    if path.exists():
        with path.open("rb") as f:
            return pickle.load(f)
    table = {}
    begun = time.time()
    with FORK.Pool(WORKERS) as pool:
        for c in range(5):
            regions = [x for x in eight_regions.grow((row, c)) if not eight_regions.straight(x) and sum(r == row for r, _ in x) == 1]
            jobs = [(cells, c, i % 500 == 0) for i, cells in enumerate(regions)]
            results = pool.map(classify, jobs, chunksize=200)
            table[c] = [e for e, _ in results]
            print(f"r{row + 1}c{c + 1}: {len(regions)} regions, {sum(b for _, b in results)} disagree of {sum(j[2] for j in jobs)} checked, {time.time() - begun:.0f}s", flush=True)
            if any(b for _, b in results):
                raise SystemExit("catalogue check FAILED")
    for c in range(5, 9):
        table[c] = [{**e, "mask": mirror(e["mask"])} for e in table[8 - c]]
    with (out / f"oriented-row{row + 1}.tmp").open("wb") as f:
        pickle.dump(table, f)
    (out / f"oriented-row{row + 1}.tmp").replace(path)
    return table


def images():
    seen = set()
    for flip in (False, True):
        cells = [(r, -c if flip else c) for r, c in SHAPE]
        for _ in range(4):
            cells = [(c, -r) for r, c in cells]
            top, left = min(r for r, _ in cells), min(c for _, c in cells)
            seen.add(frozenset((r - top, c - left) for r, c in cells))
    return seen


def placements(row):
    """(eight mask, 8 column, 9 column) for each placement that can be the 8 after symmetry."""
    found = []
    single = 0
    for image in images():
        height, width = max(r for r, _ in image) + 1, max(c for _, c in image) + 1
        for dr in range(10 - height):
            for dc in range(10 - width):
                cells = frozenset((r + dr, c + dc) for r, c in image)
                on_row = sorted(c for r, c in cells if r == row)
                for c8 in on_row:
                    if c8 > 4 or not eight_regions.holds_eight(cells, (row, c8)):
                        continue
                    if len(on_row) != 2:
                        single += 1
                        continue
                    mask = mask_of(cells)
                    keep = canonical(mask, c8) if row == 4 else (c8 < 4 or mask <= mirror(mask))
                    if keep:
                        found.append((mask, c8, next(q for q in on_row if q != c8)))
    return sorted(found, key=lambda x: (x[1], x[2], x[0])), single


def usable(table, eight, c8, n, row, loose):
    """For each root column, its usable regions as (mask, is it the 7, low counts)."""
    parity = c8 % 2
    pairs = {}
    row_bits = sum(1 << (row * 9 + q) for q in range(9))
    for c in range(9):
        if c in (c8, n):
            continue
        found = []
        for e in table[c]:
            mask = e["mask"]
            if mask & eight or mask & row_bits != 1 << (row * 9 + c):
                continue
            same = c % 2 == parity
            able_8, shaded_7, unshaded_7, counts = e[same]
            if able_8 or (not loose and e[True][0]):
                continue
            if shaded_7 or unshaded_7:
                if shaded_7 != unshaded_7:
                    found.append((mask, True, ()))
            elif counts:
                found.append((mask, False, tuple(counts)))
        pairs[c] = found
    return pairs


def above_bit(r, q, height):
    return 1 << (q * height + r)


def to_above(mask, row):
    """A region's cells above the row, in a column sweep so the frontier stays small."""
    out = 0
    for r in range(row):
        for q in range(9):
            if mask >> (r * 9 + q) & 1:
                out |= above_bit(r, q, row)
    return out


def pieces_above(free, row):
    def around(i):
        q, r = i // row, i % row
        for x, y in ((q - 1, r), (q + 1, r), (q, r - 1), (q, r + 1)):
            if 0 <= x < 9 and 0 <= y < row:
                yield x * row + y

    neighbours = {i: sum(1 << j for j in around(i)) for i in range(9 * row)}
    layer = {1 << i for i in range(9 * row) if free >> i & 1}
    for _ in range(8):
        grown = set()
        for piece in layer:
            edge = 0
            rest = piece
            while rest:
                low = rest & -rest
                rest ^= low
                edge |= neighbours[low.bit_length() - 1]
            edge &= free & ~piece
            while edge:
                low = edge & -edge
                edge ^= low
                grown.add(piece | low)
        layer = grown
    return layer


def fillings(free, roots, by_up, row, ninth):
    """Count the fillings above the row, and give a generator of each as one up part per root."""
    index = []
    empty = []
    anchors = []
    for c in roots:
        by_low = {}
        for p in by_up[c]:
            if p and not p & ~free:
                by_low.setdefault(p & -p, []).append(p)
        index.append(by_low)
        empty.append(0 in by_up[c])
        anchors.append(above_bit(row - 1, c, row) if row else 0)
    nine_low = {}
    for p in ninth:
        nine_low.setdefault(p & -p, []).append(p)
    memo = {}
    shift = 9 * row

    def live(left, unused, ninth_left):
        if not left:
            return int(not ninth_left and all(empty[i] for i in range(len(roots)) if unused >> i & 1))
        key = left | unused << shift | ninth_left << (shift + 8)
        known = memo.get(key)
        if known is not None:
            return known
        total = 0
        if all(empty[i] or left & anchors[i] for i in range(len(roots)) if unused >> i & 1):
            low = left & -left
            for i in range(len(roots)):
                if unused >> i & 1:
                    for p in index[i].get(low, ()):
                        if not p & ~left:
                            total += live(left ^ p, unused ^ 1 << i, ninth_left)
            if ninth_left:
                for p in nine_low.get(low, ()):
                    if not p & ~left:
                        total += live(left ^ p, unused, False)
        memo[key] = total
        return total

    parts = [0] * len(roots)

    def walk(left, unused, ninth_left):
        if not live(left, unused, ninth_left):
            return
        if not left:
            yield tuple(parts)
            return
        low = left & -left
        for i in range(len(roots)):
            if unused >> i & 1:
                for p in index[i].get(low, ()):
                    if not p & ~left:
                        parts[i] = p
                        yield from walk(left ^ p, unused ^ 1 << i, ninth_left)
                        parts[i] = 0
        if ninth_left:
            for p in nine_low.get(low, ()):
                if not p & ~left:
                    yield from walk(left ^ p, unused, False)

    start = (free, (1 << len(roots)) - 1, bool(ninth))
    return live(*start), walk(*start)


SWEEP = {r: {b: (b % 9) * 10 + b // 9 for b in range(81)} for r in range(9)}


def iter_bits(mask):
    while mask:
        low = mask & -mask
        mask ^= low
        yield low.bit_length() - 1


def sweep_key(part, row):
    """The cell of a region's part that a column sweep reaches first."""
    return min(iter_bits(part), key=lambda b: SWEEP[row][b])


def ninth_cells_of(eight, chosen):
    used = eight
    for e in chosen:
        used |= e[0]
    return FULL & ~used


def enumerate_placement(args):
    number, eight, c8, n, row, loose = args
    begun = time.time()
    pairs = usable(STATE["table"], eight, c8, n, row, loose)
    roots = sorted(pairs)
    by_up = {}
    free = sum(above_bit(r, q, row) for r in range(row) for q in range(9)) & ~to_above(eight, row)
    tops = 0
    leaves = [0]
    layouts = []
    above = pieces_above(free, row) if row else set()
    below = FULL & ~eight & ~sum(1 << (r * 9 + q) for r in range(row + 1) for q in range(9))
    cache = {}

    def by_low(i, up):
        """A root's regions with this up part, by the first cell below the row each one needs."""
        got = cache.get((i, up))
        if got is None:
            got = {"low": {}, "none": None, "need": 0}
            for e in by_up[roots[i]][up]:
                part = e[0] & below
                if part:
                    got["low"].setdefault(sweep_key(part, row), []).append((part, e))
                else:
                    got["none"] = e
            if got["none"] is None and row < 8:
                got["need"] = 1 << ((row + 1) * 9 + roots[i])
            cache[i, up] = got
        return got

    def go(left, tables, chosen, sevens, spare, ninth_cells):
        """Fill below the row, first cell of a column sweep first: a root's region or the ninth."""
        for table in tables:
            if table is not None and table["need"] and not left & table["need"]:
                return
        if not left:
            leaves[0] += 1
            for i, table in enumerate(tables):
                if table is None:
                    continue
                if table["none"] is None:
                    return
                chosen = [*chosen, table["none"]]
                sevens += table["none"][1]
            if sevens == 1 and len(components(ninth_cells_of(eight, chosen))) == 1 and can_match([e[2] for e in chosen if not e[1]]):
                layouts.append([e[0] for e in chosen])
            return
        cell = sweep_key(left, row)
        bit = 1 << cell
        for i, table in enumerate(tables):
            if table is None:
                continue
            for part, e in table["low"].get(cell, ()):
                if not part & ~left and sevens + e[1] <= 1:
                    tables[i] = None
                    go(left ^ part, tables, [*chosen, e], sevens + e[1], spare, ninth_cells)
                    tables[i] = table
        if spare:
            go(left ^ bit, tables, chosen, sevens, spare - 1, ninth_cells | bit)

    # One case per column for the 7: that root tries only forced 7s, the others only top-out-at-6s.
    for seven in roots:
        by_up.clear()
        cache.clear()
        for c in roots:
            by_up[c] = {}
            for entry in pairs[c]:
                if entry[1] == (c == seven):
                    by_up[c].setdefault(to_above(entry[0], row), []).append(entry)
        if not all(by_up.values()):
            continue
        for ninth in ([above, set()] if above else [set()]):
            total, walk = fillings(free, roots, by_up, row, ninth)
            tops += total
            for filling in walk:
                go(below, [by_low(i, p) for i, p in enumerate(filling)], [], 0, 0 if ninth else 9, 0)
    return number, eight, c8, n, tops, leaves[0], layouts, sum(len(v) for v in pairs.values()), time.time() - begun


def region_of(masks, eight, c8, n, row):
    region = {}
    roots = {}
    for mask in masks:
        roots[mask] = next(q for q in range(9) if mask >> (row * 9 + q) & 1)
    for r, q in CELLS:
        bit = 1 << (r * 9 + q)
        if eight & bit:
            region[r, q] = c8
        else:
            region[r, q] = next((roots[m] for m in masks if m & bit), n)
    return region


def solve_layout(args):
    region, row, n = args
    return (*attempt(region, row, n), region, n)


def save_grid(digits, shade, region, row, n, out):
    broken, regions, counts = read_back(digits, shade, region, row, n)
    print(f"FOUND. reader violations {broken or 'none'}", flush=True)
    print("\n".join("".join(str(region[r, q]) for q in range(9)) for r in range(9)), flush=True)
    print("\n".join(" ".join(("#" if shade[i][j] else ".") + str(digits[i][j]) for j in range(9)) for i in range(9)), flush=True)
    print(f"counts by column {counts}", flush=True)
    (out / f"grid-9-r{row + 1}.json").write_text(json.dumps({"digits": digits, "shaded": shade, "regions": regions, "counts": counts}))
    draw(digits, shade, region, [(row, q) for q in range(9) if q != n], out / f"grid-9-r{row + 1}.png")


def main():
    out = Path(sys.argv[1])
    row = int(sys.argv[2]) - 1
    loose = "--loose" in sys.argv
    set_row(row)
    STATE["table"] = build_table(out, row)
    found, single = placements(row)
    print(f"r{row + 1}: {len(found)} placements after symmetry, {single} placements with one row cell skipped; loose {loose}", flush=True)
    records = []
    with FORK.Pool(WORKERS) as pool:
        jobs = [(i, *p, row, loose) for i, p in enumerate(found, 1)]
        only = [x for x in sys.argv if x.startswith("--only=")]
        if only:
            jobs = [j for j in jobs if j[0] == int(only[0].split("=")[1])]
        # The same cells with the 8 and the 9 swapped have the same regions, so enumerate them once.
        swapped = {}
        for j in jobs:
            swapped.setdefault(j[1], []).append(j)
        jobs = [same[0] for same in swapped.values()]
        print(f"{len(jobs)} placements to enumerate after joining 8 and 9 swaps", flush=True)
        for number, eight, c8, n, tops, leaves, layouts, size, spent in pool.imap_unordered(enumerate_placement, jobs):
            print(f"placement {number}, 8 in r{row + 1}c{c8 + 1}, 9 in r{row + 1}c{n + 1}: {size:,} regions, {tops:,} fillings above, {leaves:,} whole boards, {len(layouts):,} layouts, {spent:.0f}s", flush=True)
            for _, _, c8_twin, n_twin, _, _ in swapped[eight]:
                records.extend((m, eight, c8_twin, n_twin) for m in layouts)
        print(f"ENUMERATION COMPLETE: {len(records):,} layouts across {len(found)} placements", flush=True)
        suffix = "-loose" if loose else ""
        with (out / f"row-layouts-r{row + 1}{suffix}.tmp").open("w") as f:
            for masks, eight, c8, n in records:
                region = region_of(masks, eight, c8, n, row)
                f.write(json.dumps({"c8": c8, "n": n, "region": [[region[r, q] for q in range(9)] for r in range(9)]}) + "\n")
        (out / f"row-layouts-r{row + 1}{suffix}.tmp").replace(out / f"row-layouts-r{row + 1}{suffix}.jsonl")
        if "--no-solve" in sys.argv:
            return
        outcomes = {}
        jobs = [(region_of(masks, eight, c8, n, row), row, n) for masks, eight, c8, n in records]
        for i, (outcome, digits, shade, region, n) in enumerate(pool.imap_unordered(solve_layout, jobs), 1):
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            if i % 50 == 0 or digits:
                print(f"solved {i} of {len(jobs)}: tally {outcomes}", flush=True)
            if digits:
                save_grid(digits, shade, region, row, n, out)
                print("GRID FOUND", flush=True)
                pool.terminate()
                return
        print(f"ALL LAYOUTS SOLVED: tally {outcomes}, no grid", flush=True)


if __name__ == "__main__":
    main()

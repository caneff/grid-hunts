"""SCRATCH: the row's 9 shares a region with another circle, on one 8 shape as a test. 8 processes.

usage: aqre_nine_shared.py DIR

The 8 region holds one row cell. Another circled region holds its own row cell and the 9's cell. The other six each
hold one row cell, and the ninth is off the row. Rules as in `aqre_row_enumerate.py`, with Chris's 8 test by shape
alone for every other region: one forced 7, the rest topping out at 6 with counts 1-6 matchable.

Each 8 placement runs one case per place of the 9, region to share it and column of the 7. Regions are filled above
the row first, then below cell by cell. A region with the 9 can leave the row through either of its two cells.

The shape tested has the median number of live one-cell placements. Each placement's enumeration stops at CAP seconds and
is recorded as capped. Results go to nine-shared-results.jsonl as each ends. The control compares the search with a
plain whole-board search, on lists cut to a found layout's regions plus a sample. It runs only if a layout is found.
"""

import contextlib
import io
import json
import pickle
import random
import signal
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import aqre_row_enumerate as e
from aqre_r5_chosen_eight import SHAPE as CHOSEN  # noqa: F401
from aqre_r5_cover import FULL, components, mask_of, mirror
from aqre_r5_eight_regions import grow, holds_eight, straight
from aqre_r5_fixed_regions import attempt, can_match
from aqre_r5_oriented import canonical

WORKERS = 8
CAP = 600
ROWS = (4, 3, 2, 1, 0)
SAMPLE = 15
TABLES = {}
SHARED = {}


def on_alarm(signum, frame):
    raise TimeoutError


def set_up():
    signal.signal(signal.SIGALRM, on_alarm)


def build_shared(out, row):
    """Regions with exactly two row cells, for each circle column: entries keyed also by the 9's column."""
    path = out / f"nine-shared-row{row + 1}.pickle"
    if path.exists():
        with path.open("rb") as f:
            return pickle.load(f)
    table = {c: [] for c in range(9)}
    begun = time.time()
    with e.FORK.Pool(WORKERS) as pool:
        for c in range(5):
            regions = [x for x in grow((row, c)) if not straight(x) and sum(r == row for r, _ in x) == 2]
            nines = [next(q for r, q in x if r == row and q != c) for x in regions]
            jobs = [(cells, c, i % 500 == 0) for i, cells in enumerate(regions)]
            results = pool.map(e.classify, jobs, chunksize=200)
            if any(bad for _, bad in results):
                raise SystemExit(f"catalogue check FAILED at r{row + 1}c{c + 1}")
            table[c] = [{**entry, "n": n} for (entry, _), n in zip(results, nines)]
            print(f"r{row + 1}c{c + 1}: {len(regions):,} two-cell regions, {time.time() - begun:.0f}s", flush=True)
    for c in range(5, 9):
        table[c] = [{**x, "mask": mirror(x["mask"]), "n": 8 - x["n"]} for x in table[8 - c]]
    with (out / f"nine-shared-row{row + 1}.tmp").open("wb") as f:
        pickle.dump(table, f)
    (out / f"nine-shared-row{row + 1}.tmp").replace(path)
    return table


def class_of(x, same):
    """(is it the 7, low counts), or None when the rules refuse this region beside this 8."""
    able_8, shaded_7, unshaded_7, counts = x[same]
    if able_8 or x[True][0]:
        return None
    if shaded_7 or unshaded_7:
        return (True, ()) if shaded_7 != unshaded_7 else None
    return (False, tuple(counts)) if counts else None


def lists_for(eight, c8, row):
    """Usable entries by root: one-cell regions, and two-cell regions by root and the 9's column."""
    one = {}
    two = {}
    bits = sum(1 << (row * 9 + q) for q in range(9))
    for c in range(9):
        if c == c8:
            continue
        same = c % 2 == c8 % 2
        found = []
        for x in TABLES[row][c]:
            mask = x["mask"]
            if mask & eight or mask & bits != 1 << (row * 9 + c):
                continue
            kind = class_of(x, same)
            if kind:
                found.append((mask, kind[0], kind[1]))
        one[c] = found
        two[c] = {}
        for x in SHARED[row][c]:
            mask = x["mask"]
            if mask & eight:
                continue
            kind = class_of(x, same)
            if kind:
                two[c].setdefault(x["n"], []).append((mask, kind[0], kind[1]))
    return one, two


def search_case(eight, row, roots, lists, k, n, ninth, free, below, cap_deadline=None):
    """All layouts for one case, given each root's lists; `k` is the root that shares the 9's cell."""
    layouts = []
    tops = boards = 0
    by_up = {}
    for c in roots:
        by_up[c] = {}
        for entry in lists[c]:
            by_up[c].setdefault(e.to_above(entry[0], row), []).append(entry)
    if not all(by_up.values()):
        return layouts, tops, boards
    cache = {}

    def by_low(i, up):
        got = cache.get((i, up))
        if got is None:
            got = {"low": {}, "none": None, "need": 0}
            for x in by_up[roots[i]][up]:
                part = x[0] & below
                if part:
                    got["low"].setdefault(e.sweep_key(part, row), []).append((part, x))
                else:
                    got["none"] = x
            if got["none"] is None and row < 8:
                got["need"] = 1 << ((row + 1) * 9 + roots[i])
                if roots[i] == k:
                    got["need"] |= 1 << ((row + 1) * 9 + n)
            cache[i, up] = got
        return got

    def go(left, tables, chosen, spare):
        nonlocal boards
        for table in tables:
            if table is not None and table["need"] and not left & table["need"]:
                return
        if not left:
            boards += 1
            for table in tables:
                if table is not None:
                    if table["none"] is None:
                        return
                    chosen = [*chosen, table["none"]]
            used = eight
            for x in chosen:
                used |= x[0]
            if sum(x[1] for x in chosen) == 1 and len(components(FULL & ~used)) == 1 and can_match([x[2] for x in chosen if not x[1]]):
                layouts.append(chosen)
            return
        cell = e.sweep_key(left, row)
        for i, table in enumerate(tables):
            if table is None:
                continue
            for part, x in table["low"].get(cell, ()):
                if not part & ~left:
                    tables[i] = None
                    go(left ^ part, tables, [*chosen, x], spare)
                    tables[i] = table
        if spare:
            go(left ^ (1 << cell), tables, chosen, spare - 1)

    for pieces in ([ninth, set()] if ninth else [set()]):
        total, walk = e.fillings(free, roots, by_up, row, pieces, {k: n})
        tops += total
        for filling in walk:
            go(below, [by_low(i, p) for i, p in enumerate(filling)], [], 0 if pieces else 9)
    return layouts, tops, boards


def cases(one, two, c8):
    """Each (9's column, sharing root, 7's column) with its lists."""
    for n in range(9):
        if n == c8:
            continue
        roots = [c for c in range(9) if c not in (c8, n)]
        for k in roots:
            if n not in two[k]:
                continue
            for seven in roots:
                lists = {}
                for c in roots:
                    pool = two[c][n] if c == k else [x for x in one[c] if not x[0] >> (e.STATE["row"] * 9 + n) & 1]
                    lists[c] = [x for x in pool if x[1] == (c == seven)]
                if all(lists.values()):
                    yield n, k, seven, roots, lists


def region_grid(chosen, roots_of, eight, c8, n):
    region = {}
    for r, q in e.CELLS:
        bit = 1 << (r * 9 + q)
        region[r, q] = c8 if eight & bit else next((roots_of[x[0]] for x in chosen if x[0] & bit), n)
    return region


def work(job):
    row, eight, c8 = job
    e.set_row(row)
    begun = time.time()
    signal.alarm(CAP)
    case_count = tops = boards = 0
    layouts = []
    try:
        one, two = lists_for(eight, c8, row)
        free = sum(e.above_bit(r, q, row) for r in range(row) for q in range(9)) & ~e.to_above(eight, row)
        below = FULL & ~eight & ~sum(1 << (r * 9 + q) for r in range(row + 1) for q in range(9))
        ninth = e.pieces_above(free, row) if row else set()
        for n, k, seven, roots, lists in cases(one, two, c8):
            case_count += 1
            found, t, b = search_case(eight, row, roots, lists, k, n, ninth, free, below)
            tops += t
            boards += b
            for chosen in found:
                roots_of = {x[0]: next(c for c in roots if x in lists[c]) for x in chosen}
                layouts.append((n, k, chosen, roots_of))
    except TimeoutError:
        return {"row": row, "eight": eight, "c8": c8, "result": "capped", "cases": case_count, "tops": tops, "boards": boards, "layouts": [], "seconds": time.time() - begun}
    finally:
        signal.alarm(0)
    enumerated = time.time() - begun
    outcomes = Counter()
    records = []
    for n, k, chosen, roots_of in layouts:
        region = region_grid(chosen, roots_of, eight, c8, n)
        grid = [[region[r, q] for q in range(9)] for r in range(9)]
        records.append({"c8": c8, "n": n, "k": k, "region": grid})
        with contextlib.redirect_stdout(io.StringIO()):
            outcome, digits, shade = attempt(region, row, n)
        outcomes[outcome] += 1
        if digits:
            return {"row": row, "eight": eight, "c8": c8, "result": "found", "digits": digits, "shade": shade, "n": n, "region": grid, "cases": case_count, "tops": tops, "boards": boards, "layouts": records, "outcomes": dict(outcomes), "seconds": time.time() - begun}
    return {"row": row, "eight": eight, "c8": c8, "result": "done", "cases": case_count, "tops": tops, "boards": boards, "layouts": records, "outcomes": dict(outcomes), "enumerated": enumerated, "seconds": time.time() - begun}


def control(row, eight, c8, record):
    """On lists cut to a found layout's regions plus a sample, the search must match a plain whole-board search."""
    one, two = lists_for(eight, c8, row)
    n, k = record["n"], record["k"]
    roots = [c for c in range(9) if c not in (c8, n)]
    groups = {}
    for r, line in enumerate(record["region"]):
        for q, label in enumerate(line):
            groups.setdefault(label, []).append((r, q))
    planted = {mask_of(groups[c]) for c in roots}
    rng = random.Random(5)
    free = sum(e.above_bit(r, q, row) for r in range(row) for q in range(9)) & ~e.to_above(eight, row)
    below = FULL & ~eight & ~sum(1 << (r * 9 + q) for r in range(row + 1) for q in range(9))
    ninth = e.pieces_above(free, row) if row else set()
    full = {}
    for c in roots:
        pool = two[c][n] if c == k else [x for x in one[c] if not x[0] >> (row * 9 + n) & 1]
        keep = {x for x in pool if x[0] in planted} | set(rng.sample(sorted(pool), min(SAMPLE, len(pool))))
        full[c] = sorted(keep)
    by_search = set()
    for seven in roots:
        lists = {c: [x for x in full[c] if x[1] == (c == seven)] for c in roots}
        if all(lists.values()):
            found, _, _ = search_case(eight, row, roots, lists, k, n, ninth, free, below)
            by_search |= {frozenset(x[0] for x in chosen) for chosen in found}
    by_plain = set()

    def plain(i, used, chosen):
        if i == len(roots):
            if sum(x[1] for x in chosen) == 1 and len(components(FULL & ~used)) == 1 and can_match([x[2] for x in chosen if not x[1]]):
                by_plain.add(frozenset(x[0] for x in chosen))
            return
        for x in full[roots[i]]:
            if not x[0] & used:
                plain(i + 1, used | x[0], [*chosen, x])

    plain(0, eight, [])
    good = by_search == by_plain and frozenset(planted) in by_search
    print(f"control: {sum(len(v) for v in full.values())} regions, search {len(by_search)} layouts, plain search {len(by_plain)}, planted found {frozenset(planted) in by_search}: {'ok' if good else 'FAILED'}", flush=True)


def one_cell_placements(cells_of_shape, row):
    e.SHAPE = cells_of_shape
    found = []
    for image in e.images():
        height, width = max(r for r, _ in image) + 1, max(c for _, c in image) + 1
        for dr in range(10 - height):
            for dc in range(10 - width):
                cells = frozenset((r + dr, c + dc) for r, c in image)
                on_row = [c for r, c in cells if r == row]
                if len(on_row) != 1 or on_row[0] > 4 or not holds_eight(cells, (row, on_row[0])):
                    continue
                mask = mask_of(cells)
                if not (canonical(mask, on_row[0]) if row == 4 else (on_row[0] < 4 or mask <= mirror(mask))):
                    continue
                if all(bin(part).count("1") % 9 == 0 for part in components(FULL & ~mask)):
                    found.append((row, mask, on_row[0]))
    return found


def main(out):
    screen = json.loads((out / "shape-screen.json").read_text())
    with_one = [x for x in screen if sum(v["live_one"] for v in x["rows"].values())]
    sizes = sorted(sum(v["live_one"] for v in x["rows"].values()) for x in with_one)
    middle = statistics.median_low(sizes)
    shape = next(x for x in with_one if sum(v["live_one"] for v in x["rows"].values()) == middle)
    cells = [tuple(c) for c in shape["cells"]]
    top, left = min(r for r, _ in cells), min(c for _, c in cells)
    print(f"test shape, median {middle} live one-cell placements of {len(sizes)} shapes, total over all shapes {sum(sizes):,}:", flush=True)
    for r in range(max(r for r, _ in cells) + 1 - top):
        print("   ", "".join("X" if (r + top, c + left) in cells else "." for c in range(max(c for _, c in cells) + 1 - left)), flush=True)
    for row in ROWS:
        e.set_row(row)
        TABLES[row] = e.build_table(out, row)
        SHARED[row] = build_shared(out, row)
    jobs = []
    for row in ROWS:
        e.set_row(row)
        here = one_cell_placements(cells, row)
        expected = shape["rows"][f"r{row + 1}"]["live_one"]
        print(f"r{row + 1}: {len(here)} placements, screen says {expected}", flush=True)
        if len(here) != expected:
            print("PLACEMENT COUNT FAILED", flush=True)
            return
        jobs.extend(here)
    results = out / "nine-shared-results.jsonl"
    begun = time.time()
    tally = Counter()
    outcomes = Counter()
    layouts = 0
    first = None
    with e.FORK.Pool(WORKERS, initializer=set_up) as pool:
        for i, x in enumerate(pool.imap_unordered(work, jobs), 1):
            with results.open("a") as f:
                f.write(json.dumps({k: v for k, v in x.items() if k not in ("digits", "shade", "region")}) + "\n")
            tally[x["result"]] += 1
            outcomes.update(x.get("outcomes", {}))
            layouts += len(x["layouts"])
            print(f"{i} of {len(jobs)}: r{x['row'] + 1}, 8 in c{x['c8'] + 1}, {x['result']}, {x['cases']} cases, {x['tops']:,} fillings, {x['boards']:,} boards, {len(x['layouts'])} layouts, {x['seconds']:.0f}s; totals {dict(tally)}, {layouts} layouts, solves {dict(outcomes)}, {time.time() - begun:.0f}s", flush=True)
            if x["layouts"] and first is None:
                first = (x["row"], x["eight"], x["c8"], x["layouts"][0])
            if x["result"] == "found":
                region = {(r, q): x["region"][r][q] for r in range(9) for q in range(9)}
                e.save_grid(x["digits"], x["shade"], region, x["row"], x["n"], out)
                print(f"GRID FOUND, r{x['row'] + 1}", flush=True)
                pool.terminate()
                break
    if first:
        e.set_row(first[0])
        control(*first)
    else:
        print("control not run: no layout found", flush=True)
    print(f"TEST SHAPE DONE: {dict(tally)}, {layouts} layouts, solves {dict(outcomes)}, {time.time() - begun:.0f}s", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

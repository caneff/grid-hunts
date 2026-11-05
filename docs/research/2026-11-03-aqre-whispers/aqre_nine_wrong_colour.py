"""SCRATCH: every 8 shape, with the shared region's circle and 9 both on the wrong colour.

usage: aqre_nine_wrong_colour.py DIR WORKERS

Chris's setup, 2026-11-04. Eight regions have their circles on the row. The 8 region holds one row cell and is the
only region that can hold an 8 by shape. Another circled region also holds the 9's cell. Its circle and 9 are each an
odd distance from the 8, so both are on the wrong colour once the 8 sets the colours. That leaves 3 unshaded cells, so
it tops out at 6, which the run checks. One other region is the forced 7, and the rest top out at 6.

Search and solve are `aqre_nine_shared.py`, with its case list narrowed here. Placements run in shuffled order, so the
pace seen early holds later. Each appends to nine-wrong-colour.jsonl as it ends, and a restart skips what is on file. A
placement's enumeration stops at CAP seconds and is recorded as capped, which proves nothing. It stops at the first grid.
"""

import json
import pickle
import random
import sys
import time
from collections import Counter
from pathlib import Path

import aqre_nine_shared as s
import aqre_row_enumerate as e

CAP = 1800
ROWS = (4, 3, 2, 1, 0)
RESULTS = "nine-wrong-colour.jsonl"


def narrowed_cases(one, two, c8):
    """Each (9's column, sharing root, 7's column) with the sharing circle and the 9 both on the wrong colour."""
    for n in range(9):
        if (n - c8) % 2 == 0:
            continue
        roots = [c for c in range(9) if c not in (c8, n)]
        for k in roots:
            if (k - n) % 2 or n not in two[k]:
                continue
            if any(x[1] for x in two[k][n]):
                raise ValueError(f"a region with circle c{k + 1} and 9 c{n + 1}, both wrong colour, can be the 7")
            for seven in roots:
                if seven == k:
                    continue
                lists = {}
                for c in roots:
                    pool = two[c][n] if c == k else [x for x in one[c] if not x[0] >> (e.STATE["row"] * 9 + n) & 1]
                    lists[c] = [x for x in pool if x[1] == (c == seven)]
                if all(lists.values()):
                    yield n, k, seven, roots, lists


def placements_of(job):
    index, cells, row = job
    e.set_row(row)
    return index, row, s.one_cell_placements(cells, row)


def all_placements(out, screen, workers):
    path = out / "nine-wrong-colour-placements.pickle"
    if path.exists():
        with path.open("rb") as f:
            return pickle.load(f)
    begun = time.time()
    with_one = [(i, x) for i, x in enumerate(screen) if sum(v["live_one"] for v in x["rows"].values())]
    jobs = [(i, [tuple(c) for c in x["cells"]], row) for i, x in with_one for row in ROWS]
    found = []
    with e.FORK.Pool(workers) as pool:
        for done, (index, row, here) in enumerate(pool.imap_unordered(placements_of, jobs), 1):
            expected = screen[index]["rows"][f"r{row + 1}"]["live_one"]
            if len(here) != expected:
                raise SystemExit(f"PLACEMENT COUNT FAILED: shape {index}, r{row + 1}, {len(here)} here, {expected} in the screen")
            found.extend((index, *p) for p in here)
            if done % 500 == 0:
                print(f"placements: {done} of {len(jobs)} shape-rows, {len(found):,} so far, {time.time() - begun:.0f}s", flush=True)
    print(f"{len(with_one)} shapes, {len(found):,} placements, {time.time() - begun:.0f}s; screen total {sum(sum(v['live_one'] for v in x['rows'].values()) for _, x in with_one):,}", flush=True)
    found.sort()
    random.Random(7).shuffle(found)
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as f:
        pickle.dump(found, f)
    tmp.replace(path)
    return found


def work(job):
    shape, row, eight, c8 = job
    x = s.work((row, eight, c8))
    x["shape"] = shape
    return x


def main(out, workers):
    s.cases = narrowed_cases
    s.CAP = CAP
    for row in ROWS:
        e.set_row(row)
        s.TABLES[row] = e.build_table(out, row)
        s.SHARED[row] = s.build_shared(out, row)
    screen = json.loads((out / "shape-screen.json").read_text())
    jobs = all_placements(out, screen, workers)
    results = out / RESULTS
    done = set()
    tally = Counter()
    outcomes = Counter()
    by_row = Counter()
    layouts = 0
    first = None
    if results.exists():
        for line in results.read_text().splitlines():
            x = json.loads(line)
            done.add((x["row"], x["eight"]))
            tally[x["result"]] += 1
            outcomes.update(x.get("outcomes", {}))
            by_row[x["row"] + 1] += len(x["layouts"])
            layouts += len(x["layouts"])
            if x["layouts"] and first is None:
                first = (x["row"], x["eight"], x["c8"], x["layouts"][0])
    todo = [j for j in jobs if (j[1], j[2]) not in done]
    print(f"{len(jobs):,} placements, {len(done):,} on file, {len(todo):,} to run on {workers} processes", flush=True)
    begun = last = time.time()
    with e.FORK.Pool(workers, initializer=s.set_up) as pool:
        for i, x in enumerate(pool.imap_unordered(work, todo), 1):
            with results.open("a") as f:
                f.write(json.dumps({k: v for k, v in x.items() if k not in ("digits", "shade", "region")}) + "\n")
            tally[x["result"]] += 1
            outcomes.update(x.get("outcomes", {}))
            by_row[x["row"] + 1] += len(x["layouts"])
            layouts += len(x["layouts"])
            if x["layouts"] and first is None:
                first = (x["row"], x["eight"], x["c8"], x["layouts"][0])
            now = time.time()
            if x["layouts"] or x["result"] != "done":
                print(f"shape {x['shape']}, r{x['row'] + 1}, 8 in c{x['c8'] + 1}: {x['result']}, {x['cases']} cases, {x['boards']:,} boards, {len(x['layouts'])} layouts, solves {x.get('outcomes', {})}, {x['seconds']:.0f}s", flush=True)
            if now - last >= 60 or i == len(todo):
                last = now
                left = (now - begun) / i * (len(todo) - i)
                print(f"{i:,} of {len(todo):,}, {now - begun:.0f}s, about {left / 3600:.1f} h left; totals {dict(tally)}, layouts {layouts} by row {dict(by_row)}, solves {dict(outcomes)}", flush=True)
            if x["result"] == "found":
                region = {(r, q): x["region"][r][q] for r in range(9) for q in range(9)}
                e.save_grid(x["digits"], x["shade"], region, x["row"], x["n"], out)
                print(f"GRID FOUND, shape {x['shape']}, r{x['row'] + 1}", flush=True)
                pool.terminate()
                break
    if first:
        e.set_row(first[0])
        s.control(*first)
    else:
        print("control not run: no layout found", flush=True)
    print(f"RUN DONE: totals {dict(tally)}, {layouts} layouts, by row {dict(by_row)}, solves {dict(outcomes)}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]))

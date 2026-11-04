"""SCRATCH: enumerate every two-cell placement of the other 55 shapes, with the 8 and 9 four apart first. 8 processes.

usage: aqre_all_two_cell.py DIR

Chris's go, 2026-11-04. Same rule and search as `aqre_row_enumerate.py`. A two-cell placement is one where the 8
region holds two cells of the row of circles, the 8 and the 9. His first shape is left out, as all its rows are done.
Placements that geometry kills are skipped, and the count kept must match shape-screen.json before anything runs.

Each placement appends to two-cell-results.jsonl as it ends, and a restart skips what is on file. A placement's
enumeration stops at CAP seconds and is recorded as capped, which proves nothing. A layout's solve keeps the fixed-
region caps. It stops at the first grid. An empty finish is a proof only for the placements not capped, on these lists.
"""

import contextlib
import io
import json
import signal
import sys
import time
from collections import Counter
from pathlib import Path

import aqre_row_enumerate as e
from aqre_r5_chosen_eight import SHAPE as CHOSEN
from aqre_r5_cover import FULL, components, mask_of
from aqre_r5_fixed_regions import attempt
from jigsaw_r5_diversity import shape_key

WORKERS = 8
CAP = 1800
ROWS = (4, 3, 2, 1)
TABLES = {}


def on_alarm(signum, frame):
    raise TimeoutError


def set_up():
    signal.signal(signal.SIGALRM, on_alarm)


def live(mask):
    return all(bin(part).count("1") % 9 == 0 for part in components(FULL & ~mask))


def work(job):
    shape, row, eight, twins = job
    e.STATE["table"] = TABLES[row]
    e.set_row(row)
    c8, n = twins[0]
    begun = time.time()
    signal.alarm(CAP)
    try:
        _, _, _, _, tops, boards, layouts, size, _ = e.enumerate_placement((0, eight, c8, n, row, False))
    except TimeoutError:
        return {"shape": shape, "row": row, "eight": eight, "twins": twins, "result": "capped", "seconds": time.time() - begun}
    finally:
        signal.alarm(0)
    enumerated = time.time() - begun
    outcomes = Counter()
    records = []
    for masks in layouts:
        for c8_twin, n_twin in twins:
            region = e.region_of(masks, eight, c8_twin, n_twin, row)
            records.append({"c8": c8_twin, "n": n_twin, "region": [[region[r, q] for q in range(9)] for r in range(9)]})
            with contextlib.redirect_stdout(io.StringIO()):
                outcome, digits, shade = attempt(region, row, n_twin)
            outcomes[outcome] += 1
            if digits:
                return {"shape": shape, "row": row, "eight": eight, "twins": twins, "result": "found", "digits": digits, "shade": shade, "c8": c8_twin, "n": n_twin, "region": records[-1]["region"], "layouts": records, "outcomes": dict(outcomes), "seconds": time.time() - begun}
    return {"shape": shape, "row": row, "eight": eight, "twins": twins, "result": "done", "regions": size, "tops": tops, "boards": boards, "layouts": records, "outcomes": dict(outcomes), "enumerated": enumerated, "seconds": time.time() - begun}


def main(out):
    screen = json.loads((out / "shape-screen.json").read_text())
    chosen = shape_key(CHOSEN)
    wanted = [x for x in screen if sum(v["live_two"] for v in x["rows"].values()) and shape_key([tuple(c) for c in x["cells"]]) != chosen]
    print(f"{len(wanted)} shapes", flush=True)
    for row in ROWS:
        e.set_row(row)
        TABLES[row] = e.build_table(out, row)
    jobs = []
    for index, record in enumerate(wanted):
        e.SHAPE = [tuple(c) for c in record["cells"]]
        for row in ROWS:
            e.set_row(row)
            found, _ = e.placements(row)
            kept = [p for p in found if live(p[0])]
            expected = record["rows"][f"r{row + 1}"]["live_two"]
            if len(kept) != expected:
                print(f"PLACEMENT COUNT FAILED: shape {index}, r{row + 1}, {len(kept)} here, {expected} in the screen", flush=True)
                return
            joined = {}
            for eight, c8, n in kept:
                joined.setdefault(eight, []).append((c8, n))
            for eight, twins in joined.items():
                gap = abs(twins[0][0] - twins[0][1])
                jobs.append(((gap != 4, index, ROWS.index(row)), (index, row, eight, twins)))
    jobs.sort(key=lambda j: (j[0], j[1][2]))
    results = out / "two-cell-results.jsonl"
    done = set()
    if results.exists():
        for line in results.read_text().splitlines():
            x = json.loads(line)
            done.add((x["row"], x["eight"]))
    todo = [j[1] for j in jobs if (j[1][1], j[1][2]) not in done]
    print(f"{len(jobs)} placements after joining 8 and 9 swaps, {sum(len(j[1][3]) for j in jobs)} before; {len(done)} on file, {len(todo)} to run; gap 4 first: {sum(not j[0][0] for j in jobs)}", flush=True)
    begun = time.time()
    tally = Counter()
    outcomes = Counter()
    layouts = 0
    with e.FORK.Pool(WORKERS, initializer=set_up) as pool:
        for i, x in enumerate(pool.imap_unordered(work, todo), 1):
            with results.open("a") as f:
                f.write(json.dumps({k: v for k, v in x.items() if k not in ("digits", "shade", "region")}) + "\n")
            tally[x["result"]] += 1
            outcomes.update(x.get("outcomes", {}))
            layouts += len(x.get("layouts", ()))
            gaps = abs(x["twins"][0][0] - x["twins"][0][1])
            print(f"{i} of {len(todo)}: shape {x['shape']}, gap {gaps}, r{x['row'] + 1}, 8 in c{x['twins'][0][0] + 1}, {x['result']}, {x.get('regions', 0):,} regions, {x.get('tops', 0):,} fillings, {x.get('boards', 0):,} boards, {len(x.get('layouts', ())):,} layouts, {x['seconds']:.0f}s; totals {dict(tally)}, {layouts} layouts, solves {dict(outcomes)}, {time.time() - begun:.0f}s", flush=True)
            if x["result"] == "found":
                region = {(r, q): x["region"][r][q] for r in range(9) for q in range(9)}
                e.save_grid(x["digits"], x["shade"], region, x["row"], x["n"], out)
                print(f"GRID FOUND in shape {x['shape']}, r{x['row'] + 1}", flush=True)
                pool.terminate()
                return
    print(f"ALL DONE: totals {dict(tally)}, {layouts} layouts, solves {dict(outcomes)}, no grid", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

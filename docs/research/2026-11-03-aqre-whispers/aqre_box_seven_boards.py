"""SCRATCH: every distinct board with the forced 7 on r1c1 and six circles on other box centres. 8 processes.

usage: aqre_box_seven_boards.py DIR [LIMIT_SECONDS]

Chris's go, 2026-11-05, after the whole r1c1 solve timed out. Two of boxes 2-9 hold no circle. The main diagonal flip keeps
r1c1, so 28 pairs of empty boxes fall to 16 boards. The model is `aqre_box_seven.build`, plain rules with no added facts. It
replaces `aqre_box_seven_survey.py`, which added the false fact that box 1's edges are shaded and gave no results.

Each board has one CP-SAT worker and its own cap. Each appends to box-seven-r1c1.jsonl as it ends, and a restart skips what is
on file. Every board runs, even after a grid is found. A found grid goes through the plain Python check. UNKNOWN at the cap
proves nothing.
"""

import json
import multiprocessing
import sys
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

from aqre_box_seven import CENTRES, build, check
from ortools.sat.python import cp_model

FORK = multiprocessing.get_context("fork")
WORKERS = 8
SEVEN = (0, 0)
FLIP = {1: 3, 3: 1, 2: 6, 6: 2, 5: 7, 7: 5, 4: 4, 8: 8}  # box index under the main diagonal; box 1 is index 0
LIMIT = {}


def boards():
    seen = []
    for pair in combinations(range(1, 9), 2):
        key = min(pair, tuple(sorted(FLIP[k] for k in pair)))
        if key not in seen:
            seen.append(key)
    return seen


def solve(empty):
    begun = time.time()
    m, x, g, value = build()
    for k in empty:
        for v in range(1, 8):
            m.add(value[k, v] == 0)
    m.add(value[0, 7] == 1)
    m.add(x[SEVEN] == 7)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = LIMIT["seconds"]
    status = s.status_name(s.solve(m))
    out = {"empty": empty, "status": status, "seconds": time.time() - begun}
    if status in ("OPTIMAL", "FEASIBLE"):
        digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
        shade = [[int(s.value(g[r, c])) for c in range(9)] for r in range(9)]
        circles = {k: CENTRES[k] for k in range(1, 9) if k not in empty}
        circles[0] = SEVEN
        out.update(digits=digits, shade=shade, check=check(digits, shade, circles))
    return out


def main(out, limit):
    LIMIT["seconds"] = limit
    jobs = boards()
    if len(jobs) != 16:
        raise SystemExit(f"BOARD COUNT FAILED: {len(jobs)}")
    results = out / "box-seven-r1c1.jsonl"
    done = set()
    tally = Counter()
    if results.exists():
        for line in results.read_text().splitlines():
            x = json.loads(line)
            done.add(tuple(x["empty"]))
            tally[x["status"]] += 1
    todo = [j for j in jobs if j not in done]
    print(f"{len(jobs)} boards, {len(done)} on file, {len(todo)} to run, cap {limit:.0f}s each, {WORKERS} processes", flush=True)
    begun = time.time()
    with FORK.Pool(WORKERS) as pool:
        for i, x in enumerate(pool.imap_unordered(solve, todo), 1):
            with results.open("a") as f:
                f.write(json.dumps(x) + "\n")
            tally[x["status"]] += 1
            print(f"{i} of {len(todo)}: no circle in boxes {x['empty'][0] + 1} and {x['empty'][1] + 1}: {x['status']}, {x['seconds']:.0f}s, plain check {x.get('check', 'n/a') or 'passes'}; totals {dict(tally)}, {time.time() - begun:.0f}s", flush=True)
            if "digits" in x:
                for r in range(9):
                    print(" ".join(f"{x['digits'][r][c]}{'#' if x['shade'][r][c] else '.'}" for c in range(9)), flush=True)
    print(f"BOARDS DONE: {dict(tally)}, {time.time() - begun:.0f}s", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), float(sys.argv[2]) if len(sys.argv) > 2 else 900.0)

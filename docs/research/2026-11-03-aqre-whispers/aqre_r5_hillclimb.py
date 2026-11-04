"""SCRATCH: hill-climb jigsaw layouts towards 8 circles in r5. One worker.

Score: on fixed regions, keep every rule but the circles (Aqre shading, 5-whispers on
shaded cells, sudoku, r5's uncircled cell the 9) and maximise how many of the 8 circled
cells equal their region's shaded count. 8 of 8 is a valid grid.

`check DIR K` scores K of the layouts logged by the fixed-region run: are they near
misses? `control DIR` tests the score on the known grid-8-r1. `climb DIR` hill-climbs:
swap two border cells touching a region whose circle missed, keep a layout whose score
does not drop, restart from a fresh layout after a stall. It samples, so failing says
nothing about r5 as a whole.
"""

import json
import random
import sys
import time
from pathlib import Path

from aqre_jigsaw_feasible import connected, neighbours
from aqre_jigsaw_r5_staged import finish, read_back
from aqre_r5_fixed_regions import CELLS, ROW, build, one_worker
from jigsaw_r5_diversity import measure, touches, walk
from ortools.sat.python import cp_model

SCORE_LIMIT = 20.0
STALL = 40
BUDGET = 3 * 3600.0


def score(region, row, n, limit=SCORE_LIMIT, hint=None):
    """(best score, digits, shade, misses) or None when no scored grid was reached."""
    m, x, g = build_soft(region, row, n)
    if hint:
        for r, c in CELLS:
            m.add_hint(x[0][r, c], hint[0][r][c])
            m.add_hint(g[r * 9 + c], int(hint[1][r][c]))
    s = one_worker(limit)
    status = s.solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    xs, marks = x
    digits = [[s.value(xs[r, c]) for c in range(9)] for r in range(9)]
    shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
    misses = [c for c, b in marks.items() if not s.value(b)]
    return 8 - len(misses), digits, shade, misses, s.status_name(status)


def build_soft(region, row, n):
    """`build` with connectivity and the circles turned into an objective."""
    regions = [[cell for cell in CELLS if region[cell] == k] for k in range(9)]
    m, x, g = build(region, row, n, True, circles=False)
    marks = {}
    for c in range(9):
        if c == n:
            continue
        b = m.new_bool_var(f"circle{c}")
        marks[c] = b
        total = sum(g[r * 9 + q] for r, q in regions[c])
        m.add(x[row, c] == total).only_enforce_if(b)
    m.maximize(sum(marks.values()))
    return m, (x, marks), g


def check(out, k):
    lines = (out / "fixed-r5.jsonl").read_text().splitlines()
    rng = random.Random(1)
    picks = rng.sample(lines, min(k, len(lines)))
    scores = []
    for i, line in enumerate(picks):
        old = json.loads(line)
        region = {cell: old["region"][cell[0]][cell[1]] for cell in CELLS}
        begun = time.time()
        got = score(region, ROW, old["n"], limit=60.0)
        spent = time.time() - begun
        print(f"layout {i + 1}, earlier {old['outcome']}: "
              f"{(str(got[0]) + ' of 8, ' + got[4]) if got else 'no scored grid'} in {spent:.1f}s", flush=True)
        scores.append(got[0] if got else None)
    print("scores", sorted(x for x in scores if x is not None), "unscored", scores.count(None), flush=True)


def control(out):
    known = json.loads((out / "grid-8-r1.json").read_text())
    region = {tuple(cell): k for k, cells in enumerate(known["regions"]) for cell in cells}
    got = score(region, 0, 4, limit=60.0, hint=(known["digits"], known["shaded"]))
    print(f"score on grid-8-r1, warm-started: {got[0] if got else None}", flush=True)
    broken = read_back(got[1], got[2], region, 0, 4)[0] if got else ["no grid"]
    print(f"reader: {broken or 'none'}", flush=True)
    ok = bool(got) and got[0] == 8 and not broken
    print("controls", "pass" if ok else "FAIL", flush=True)
    return ok


def swap_moves(region, misses, rng):
    """Border pairs where a cell of a missed region trades with a neighbouring region."""
    cells = [cell for cell in CELLS if region[cell] in misses]
    rng.shuffle(cells)
    for a in cells:
        ra = region[a]
        for b in rng.sample(CELLS, len(CELLS)):
            rb = region[b]
            if rb == ra:
                continue
            if not any(region[x] == rb for x in neighbours(a)):
                continue
            if not any(region[x] == ra for x in neighbours(b)):
                continue
            yield a, b


def legal_swap(region, a, b):
    ra, rb = region[a], region[b]
    if a[0] == ROW or b[0] == ROW:
        return False
    new = dict(region)
    new[a], new[b] = rb, ra
    if not connected([x for x in CELLS if new[x] == ra]):
        return False
    if not connected([x for x in CELLS if new[x] == rb]):
        return False
    if measure(new)["straight"]:
        return False
    return new


def relabel_for(region):
    from aqre_r5_fixed_regions import relabel

    pair = [c for c in range(9) if sum(region[ROW, x] == region[ROW, c] for x in range(9)) == 2]
    return relabel(region, ROW, pair[0]), pair[0]


def climb(out):
    start = time.time()
    rng = random.Random(7)
    best_seen = 0
    restart = 0
    evals = 0
    pool = [x for x in walk(11, 20.0) if measure(x)["straight"] == 0]
    while time.time() - start < BUDGET:
        restart += 1
        region, n = relabel_for(rng.choice(pool))
        assert touches(region) == 8
        got = score(region, ROW, n)
        evals += 1
        if not got:
            print(f"restart {restart}: no scored grid", flush=True)
            continue
        print(f"restart {restart}: start score {got[0]}", flush=True)
        stall = 0
        while stall < STALL and time.time() - start < BUDGET:
            if got[0] == 8:
                broken = finish(got[1], got[2], region, n, out)
                print(f"evals {evals}, restarts {restart}, clean {broken}", flush=True)
                return
            moved = False
            for a, b in swap_moves(region, got[3], rng):
                new = legal_swap(region, a, b)
                if new:
                    moved = True
                    break
            if not moved:
                break
            trial = score(new, ROW, n, hint=(got[1], got[2]))
            evals += 1
            if trial and trial[0] >= got[0]:
                if trial[0] > got[0]:
                    stall = 0
                    print(f"  score {trial[0]} after {evals} evals, {time.time() - start:.0f}s", flush=True)
                else:
                    stall += 1
                region, got = new, trial
                if got[0] > best_seen:
                    best_seen = got[0]
                    (out / "climb-best.json").write_text(json.dumps({
                        "score": got[0],
                        "n": n,
                        "digits": got[1],
                        "shaded": got[2],
                        "region": [[region[r, c] for c in range(9)] for r in range(9)],
                    }))
            else:
                stall += 1
    print(f"budget spent, no grid: best {best_seen} of 8, {evals} evals, {restart} restarts", flush=True)


if __name__ == "__main__":
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == "control":
        sys.exit(0 if control(out_dir) else 1)
    if sys.argv[1] == "check":
        check(out_dir, int(sys.argv[3]))
        sys.exit(0)
    climb(out_dir)

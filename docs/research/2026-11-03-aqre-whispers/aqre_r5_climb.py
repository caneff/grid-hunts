"""SCRATCH: hill-climb jigsaw layouts towards 8 circles in r5, one worker.

Every rule but connectivity stays hard on fixed regions, and the score is the fewest
separate shaded groups (aqre_r5_groups_score). 1 group is a valid grid, which the
separate reader then checks.

A move swaps two region cells off r5, keeping regions connected and none straight. A
move is kept when the layout still reaches the current group count or fewer, a limit
added to the model, warm-started from the current grid. After STALL rejected or equal
moves it restarts from another sampled layout. It samples, so failing says nothing about
r5 as a whole. It stops at the first grid.
"""

import json
import random
import sys
import time
from pathlib import Path

from aqre_jigsaw_feasible import connected, neighbours
from aqre_jigsaw_r5_staged import finish
from aqre_r5_fixed_regions import CELLS, ROW, one_worker, relabel
from aqre_r5_groups_score import build_groups, groups_of
from jigsaw_r5_diversity import measure, touches, walk
from ortools.sat.python import cp_model

EVAL_LIMIT = 20.0
STALL = 60
BUDGET = 2 * 3600.0


def evaluate(region, n, ceiling=None, hint=None):
    """(groups, digits, shade) from a capped solve, or None when none was reached."""
    m, x, g, roots = build_groups(region, ROW, n)
    if ceiling is not None:
        m.add(sum(roots) <= ceiling)
    if hint:
        for r, c in CELLS:
            m.add_hint(x[r, c], hint[0][r][c])
            m.add_hint(g[r * 9 + c], int(hint[1][r][c]))
    s = one_worker(EVAL_LIMIT)
    status = s.solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
    return len(groups_of(shade)), digits, shade


def propose(region, rng):
    off_row = [cell for cell in CELLS if cell[0] != ROW]
    while True:
        a, b = rng.sample(off_row, 2)
        ra, rb = region[a], region[b]
        if ra == rb:
            continue
        if not any(region[x] == rb for x in neighbours(a)):
            continue
        if not any(region[x] == ra for x in neighbours(b)):
            continue
        new = dict(region)
        new[a], new[b] = rb, ra
        if not connected([x for x in CELLS if new[x] == ra]):
            continue
        if not connected([x for x in CELLS if new[x] == rb]):
            continue
        if measure(new)["straight"]:
            continue
        return new


def main(out):
    start = time.time()
    rng = random.Random(7)
    pool = [x for seed in (21, 22, 23) for x in walk(seed, 20.0) if measure(x)["straight"] == 0]
    print(f"{len(pool)} layouts to start from", flush=True)
    best = 99
    evals = restarts = kept = 0
    while time.time() - start < BUDGET:
        raw = rng.choice(pool)
        assert touches(raw) == 8
        pair = [c for c in range(9) if sum(raw[ROW, x] == raw[ROW, c] for x in range(9)) == 2]
        n = rng.choice(pair)
        region = relabel(raw, ROW, n)
        got = evaluate(region, n)
        evals += 1
        if not got:
            continue
        restarts += 1
        print(f"restart {restarts}: {got[0]} groups, {time.time() - start:.0f}s, {evals} evals", flush=True)
        stall = 0
        while stall < STALL and time.time() - start < BUDGET:
            if got[0] < best:
                best = got[0]
                print(f"  best {best} groups, {evals} evals, {time.time() - start:.0f}s", flush=True)
                (out / "climb-best.json").write_text(json.dumps({
                    "groups": best,
                    "n": n,
                    "digits": got[1],
                    "shaded": got[2],
                    "region": [[region[r, c] for c in range(9)] for r in range(9)],
                }))
            if got[0] == 1:
                print(f"evals {evals}, restarts {restarts}, kept {kept}", flush=True)
                finish(got[1], got[2], region, n, out)
                return
            new = propose(region, rng)
            trial = evaluate(new, n, ceiling=got[0], hint=(got[1], got[2]))
            evals += 1
            if trial:
                kept += 1
                stall = 0 if trial[0] < got[0] else stall + 1
                region, got = new, trial
            else:
                stall += 1
    print(f"budget spent, no grid: best {best} groups, {evals} evals, {restarts} restarts, {kept} kept", flush=True)


if __name__ == "__main__":
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    main(out_dir)

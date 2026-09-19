"""counting shaded, all visible: harvest as many unique shapes (with an 8) as possible.

    uv run finders/counting_shaded/harvest.py --seconds 1800 --seed 1 --out DIR \
        [--roots docs/research/counting_shaded/allvisible-hits.jsonl]

Roots: shapes from --roots first, then shapes.climb runs (the settings that
produced the first hit). Each root's plateau is walked breadth-first: a move
toggles one cell or a cell plus a neighbour, and a result that is admissible,
keeps an 8, and has exactly one solution (counter capped at 2) is another
example. The walk stops after `--plateau` new shapes so the next root starts
elsewhere.

Shapes are deduplicated up to the 8 square symmetries (they preserve houses
and king adjacency). DIR/examples.jsonl gets one line per example with its
root id and its toggle distance from the root; DIR/summary.json is rewritten
after each root. Earlier experiments (aimed climb, windowed CP-SAT repair)
are in commit 6157c6e; see 2026-09-15-counting-shaded-all-visible.md.
"""

import argparse
import json
import random
import time
from collections import deque
from pathlib import Path

from shapes import NEIGH, climb, count_solutions, eight_ok, givens, seed_shape

SYMS = [
    lambda r, c: (r, c),
    lambda r, c: (c, 8 - r),
    lambda r, c: (8 - r, 8 - c),
    lambda r, c: (8 - c, r),
    lambda r, c: (r, 8 - c),
    lambda r, c: (8 - r, c),
    lambda r, c: (c, r),
    lambda r, c: (8 - c, 8 - r),
]
MOVES = [(i,) for i in range(81)] + [
    (i, j) for i in range(81) for j in NEIGH[i] if j > i
]


def canonical(shape):
    return min(
        tuple(sorted(f(i // 9, i % 9)[0] * 9 + f(i // 9, i % 9)[1] for i in shape))
        for f in SYMS
    )


def unique_example(shape):
    g = givens(shape)
    return eight_ok(g) and count_solutions(g, 2) == 1


def score_of(g, cap):
    """(solutions capped, cells that vary among them); (0, 0) = unsolvable."""
    vary = set()
    n = count_solutions(g, cap, vary)
    return (n, len(vary))


NEAR2 = [
    [
        j
        for j in range(81)
        if j != i and max(abs(i // 9 - j // 9), abs(i % 9 - j % 9)) <= 2
    ]
    for i in range(81)
]


def finish(shape, deadline):
    """Near miss: toggle a varying unshaded cell on, plus 0-2 toggles within
    distance 2 of it. Yields every unique shape found."""
    vary = set()
    count_solutions(givens(shape), 64, vary)
    for v in sorted(vary):
        if v in shape:
            continue
        near = NEAR2[v]
        base = shape | {v}
        combos = (
            [()]
            + [(a,) for a in near]
            + [(a, b) for k, a in enumerate(near) for b in near[k + 1 :]]
        )
        for extra in combos:
            if time.monotonic() > deadline:
                return
            trial = base.symmetric_difference(extra)
            if v in trial and unique_example(trial):
                yield trial


def fast_climb(rng, start, deadline, cap):
    """Greedy climb on (solutions, varying cells) from `start`; returns (best shape, best score)."""
    shape = start
    score = score_of(givens(shape), cap)
    best = (score, shape)
    while time.monotonic() < deadline and score[0] != 1:
        i = rng.randrange(81)
        move = {i}
        if rng.random() < 0.5:
            move.add(rng.choice(NEIGH[i]))
        trial = shape ^ move
        tg = givens(trial)
        if not eight_ok(tg):
            continue
        ts = score_of(tg, cap)
        if ts[0] == 0:
            continue
        if ts <= score or rng.random() < 0.02:
            shape, score = trial, ts
            if score < best[0]:
                best = (score, shape)
    return best[1], best[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=1800)
    ap.add_argument("--climb-seconds", type=float, default=40)
    ap.add_argument("--plateau", type=int, default=2000)
    ap.add_argument("--min-shaded", type=int, default=26)
    ap.add_argument("--roots", type=Path)
    ap.add_argument("--mode", choices=["fast", "classic"], default="fast")
    ap.add_argument("--cap", type=int, default=64)
    ap.add_argument("--finish-below", type=int, default=16)
    ap.add_argument("--finish-seconds", type=float, default=30)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    t0 = time.monotonic()
    seen = set()
    stats = {
        "seed": a.seed,
        "climbs": 0,
        "roots": 0,
        "examples": 0,
        "min_shaded": None,
        "max_shaded": None,
        "max_distance": 0,
    }
    pool = []
    given_roots = (
        [set(json.loads(line)["shape"]) for line in a.roots.read_text().splitlines()]
        if a.roots
        else []
    )

    def elapsed():
        return time.monotonic() - t0

    def record(shape, root_id, dist):
        key = canonical(shape)
        if key in seen:
            return 0
        seen.add(key)
        n = len(shape)
        stats["examples"] += 1
        stats["min_shaded"] = (
            n if stats["min_shaded"] is None else min(stats["min_shaded"], n)
        )
        stats["max_shaded"] = (
            n if stats["max_shaded"] is None else max(stats["max_shaded"], n)
        )
        stats["max_distance"] = max(stats["max_distance"], dist)
        with (a.out / "examples.jsonl").open("a") as ex_file:
            ex_file.write(
                json.dumps(
                    {"root": root_id, "distance": dist, "shaded": n, "shape": list(key)}
                )
                + "\n"
            )
        return 1

    while elapsed() < a.seconds:
        if given_roots:
            root = given_roots.pop(0)
        else:
            stats["climbs"] += 1
            end = t0 + min(elapsed() + a.climb_seconds, a.seconds)
            if a.mode == "fast":
                if pool and rng.random() < 0.5:
                    start = rng.choice(pool)[1]
                else:
                    start = seed_shape(rng, a.min_shaded)
                root, score = fast_climb(rng, start, end, a.cap)
                if 1 < score[0] <= a.finish_below:
                    t = elapsed()
                    found = list(
                        finish(root, t0 + min(elapsed() + a.finish_seconds, a.seconds))
                    )
                    stats["finishes"] = stats.get("finishes", 0) + 1
                    stats["finish_hits"] = stats.get("finish_hits", 0) + bool(found)
                    print(
                        f"climb {stats['climbs']}: finish from {score}: {len(found)} unique "
                        f"in {elapsed() - t:.1f}s",
                        flush=True,
                    )
                    if found:
                        root, score = found[0], (1, 0)
                        given_roots.extend(found[1:])
                if score[0] != 1:
                    if score[0] <= 10:
                        pool.append((score, root))
                        pool.sort(key=lambda p: p[0])
                        del pool[20:]
                    print(
                        f"climb {stats['climbs']}: miss (best {score}) t={elapsed():.0f}s",
                        flush=True,
                    )
                    continue
            else:
                root, _, score, _ = climb(rng, end, 2000, a.min_shaded)
                if score != 1:
                    print(
                        f"climb {stats['climbs']}: miss (best {score}) t={elapsed():.0f}s",
                        flush=True,
                    )
                    continue
        if not unique_example(root) or canonical(root) in seen:
            continue
        stats["roots"] += 1
        root_id = stats["roots"]
        new = record(root, root_id, 0)
        queue = deque([root])
        visited = {canonical(root)}
        while queue and new < a.plateau and elapsed() < a.seconds:
            cur = queue.popleft()
            order = MOVES[:]
            rng.shuffle(order)
            for mv in order:
                trial = cur.symmetric_difference(mv)
                key = canonical(trial)
                if key in visited:
                    continue
                visited.add(key)
                if not unique_example(trial):
                    continue
                queue.append(trial)
                new += record(trial, root_id, len(trial ^ root))
                if new >= a.plateau:
                    break
        stats["elapsed_s"] = round(elapsed())
        (a.out / "summary.json").write_text(json.dumps(stats))
        print(f"root {root_id}: +{new} examples; {json.dumps(stats)}", flush=True)
    print("done", json.dumps(stats), flush=True)


if __name__ == "__main__":
    main()

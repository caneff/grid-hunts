"""Ghosts, all visible: harvest as many unique shapes (with an 8) as possible.

    uv run docs/research/ghosts/harvest.py --seconds 1800 --seed 1 --out DIR

Loop: a shapes.py climb until a hit (or its time runs out); then a BFS over
the hit's plateau. Each plateau move toggles one cell or a cell plus a
neighbour; a result that is admissible, keeps an 8, and has exactly one
solution (counter capped at 2) is another example. The BFS stops after
`--plateau` new shapes so the next climb starts fresh elsewhere.

Shapes are deduplicated up to the 8 square symmetries (they preserve houses
and king adjacency). Every example goes to DIR/examples.jsonl with the climb
that found it; DIR/summary.json is rewritten after each climb.
"""

import argparse
import json
import math
import random
import time
from collections import deque
from pathlib import Path

from shapes import BOX, NEIGH, count_solutions, givens, has_eight, seed_shape

SYMS = [
    lambda r, c: (r, c), lambda r, c: (c, 8 - r), lambda r, c: (8 - r, 8 - c), lambda r, c: (8 - c, r),
    lambda r, c: (r, 8 - c), lambda r, c: (8 - r, c), lambda r, c: (c, r), lambda r, c: (8 - c, 8 - r),
]


def canonical(shape):
    return min(tuple(sorted(f(*divmod(i, 9))[0] * 9 + f(*divmod(i, 9))[1] for i in shape)) for f in SYMS)


def unique_example(shape):
    g = givens(shape)
    return g if has_eight(g) and count_solutions(g, 2) == 1 else None


def moves():
    for i in range(81):
        yield (i,)
        for j in NEIGH[i]:
            if j > i:
                yield (i, j)


MOVES = list(moves())


def aimed_climb(rng, deadline, cap, min_ghosts, aim):
    """shapes.climb with moves aimed at cells that differ between solutions."""
    shape = seed_shape(rng, min_ghosts)
    g = givens(shape)
    vary = set()
    score = count_solutions(g, cap, vary)
    best = (score, shape, g)
    steps = 0
    temp = 0.1
    while time.monotonic() < deadline and score != 1:
        if vary and rng.random() < aim:
            i = rng.choice(tuple(vary))
            if rng.random() < 0.5:
                i = rng.choice(NEIGH[i])
        else:
            i = rng.randrange(81)
        move = {i}
        if rng.random() < 0.5:
            move.add(rng.choice(NEIGH[i]))
        trial = shape ^ move
        tg = givens(trial)
        steps += 1
        if not has_eight(tg):
            continue
        tv = set()
        ts = count_solutions(tg, cap, tv)
        if ts == 0:
            continue
        worse = math.log(ts) - math.log(score)
        if worse <= 0 or rng.random() < math.exp(-worse / temp):
            shape, g, score, vary = trial, tg, ts, tv
            if score < best[0]:
                best = (score, shape, g)
        temp = max(0.01, temp * 0.9999)
    score, shape, g = best
    return shape, g, score, steps


class Lns:
    """Grid+ghost CP-SAT model reused across rounds. Ghosts outside the window
    are pinned by assumptions; every alternative solution seen is a cut."""

    def __init__(self, min_ghosts):
        from ortools.sat.python import cp_model
        self.cp = cp_model
        self.m = m = cp_model.CpModel()
        self.g = g = [m.new_bool_var(f"g{i}") for i in range(81)]
        self.x = x = [[m.new_bool_var(f"x{i}{d}") for d in range(9)] for i in range(81)]
        for i in range(81):
            m.add_exactly_one(x[i])
        for d in range(9):
            for k in range(9):
                m.add_exactly_one(x[k * 9 + c][d] for c in range(9))
                m.add_exactly_one(x[r * 9 + k][d] for r in range(9))
                m.add_exactly_one(x[i][d] for i in range(81) if BOX[i] == k)
        self.on = []
        eight = []
        for i in range(81):
            digit = sum((d + 1) * x[i][d] for d in range(9))
            m.add(sum(g[j] for j in NEIGH[i]) == digit).only_enforce_if(g[i])
            row = []
            for d in range(9):
                v = m.new_bool_var(f"on{i}{d}")
                m.add_implication(v, g[i])
                m.add_implication(v, x[i][d])
                m.add_bool_or([v, g[i].Not(), x[i][d].Not()])
                row.append(v)
            self.on.append(row)
            eight.append(row[7])
        m.add_bool_or(eight)
        m.add(sum(g) >= min_ghosts)
        self.cuts = set()

    def cut(self, Y):
        key = tuple(Y)
        if key in self.cuts:
            return
        self.cuts.add(key)
        self.m.add_bool_or([self.on[i][d] for i in range(81) for d in range(9) if d != Y[i] - 1])

    def step(self, rng, shape, S, window, limit):
        m = self.m
        m.clear_assumptions()
        m.add_assumptions([self.g[i] if i in shape else self.g[i].Not() for i in range(81) if i not in window])
        m.clear_hints()
        for i in range(81):
            m.add_hint(self.g[i], i in shape)
            m.add_hint(self.x[i][S[i] - 1], True)
        s = self.cp.CpSolver()
        s.parameters.num_workers = 1
        s.parameters.random_seed = rng.randrange(1 << 30)
        s.parameters.max_time_in_seconds = limit
        if s.solve(m) not in (self.cp.OPTIMAL, self.cp.FEASIBLE):
            return None
        return {i for i in range(81) if s.value(self.g[i])}


def lns_root(rng, deadline, min_ghosts, radius, log):
    """Seed a shape, then repair it with windowed CP-SAT rounds until unique."""
    shape = seed_shape(rng, min_ghosts)
    lns = Lns(min_ghosts)
    rounds = 0
    while time.monotonic() < deadline:
        sols = []
        n = count_solutions(givens(shape), 30, None, sols)
        if n == 1:
            return shape, rounds
        for Y in sols:
            lns.cut(Y)
        S = sols[0]
        diff = [i for i in range(81) if any(Y[i] != S[i] for Y in sols[1:])]
        centre = divmod(rng.choice(diff), 9)
        window = {r * 9 + c for r in range(9) for c in range(9)
                  if abs(r - centre[0]) <= radius and abs(c - centre[1]) <= radius}
        new = lns.step(rng, shape, S, window, min(5.0, max(0.5, deadline - time.monotonic())))
        rounds += 1
        if new is not None:
            shape = new
    return None, rounds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=1800)
    ap.add_argument("--climb-seconds", type=float, default=40)
    ap.add_argument("--plateau", type=int, default=300)
    ap.add_argument("--min-ghosts", type=int, default=26)
    ap.add_argument("--aim", type=float, default=0.7)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    seen = set()
    t0 = time.monotonic()
    climbs = hit_climbs = 0
    min_ghosts = None
    ex_file = open(a.out / "examples.jsonl", "a")

    def record(shape, g, climb_id, root):
        nonlocal min_ghosts
        key = canonical(shape)
        if key in seen:
            return False
        seen.add(key)
        min_ghosts = len(shape) if min_ghosts is None else min(min_ghosts, len(shape))
        ex_file.write(json.dumps({"seed": a.seed, "climb": climb_id, "root": root, "ghosts": len(shape),
                                  "shape": list(key)}) + "\n")
        return True

    while time.monotonic() - t0 < a.seconds:
        climbs += 1
        shape, g, score, _ = aimed_climb(rng, min(time.monotonic() + a.climb_seconds, t0 + a.seconds), 2000,
                                         a.min_ghosts, a.aim)
        if score != 1:
            print(f"climb {climbs}: miss (best {score}) t={time.monotonic() - t0:.0f}s", flush=True)
            continue
        hit_climbs += 1
        new = int(record(shape, g, climbs, True))
        queue = deque([shape])
        visited = {canonical(shape)}
        while queue and new < a.plateau and time.monotonic() - t0 < a.seconds:
            cur = queue.popleft()
            order = MOVES[:]
            rng.shuffle(order)
            for mv in order:
                trial = cur.symmetric_difference(mv)
                key = canonical(trial)
                if key in visited:
                    continue
                visited.add(key)
                tg = unique_example(trial)
                if tg is None:
                    continue
                queue.append(trial)
                new += record(trial, tg, climbs, False)
                if new >= a.plateau:
                    break
        ex_file.flush()
        summary = {"seed": a.seed, "elapsed_s": round(time.monotonic() - t0), "climbs": climbs,
                   "hit_climbs": hit_climbs, "examples": len(seen), "min_ghosts": min_ghosts}
        (a.out / "summary.json").write_text(json.dumps(summary))
        print(f"climb {climbs}: HIT +{new} examples, total {len(seen)} from {hit_climbs} hit climbs, "
              f"min ghosts {min_ghosts}, t={time.monotonic() - t0:.0f}s", flush=True)
    print("done", json.dumps({"climbs": climbs, "hit_climbs": hit_climbs, "examples": len(seen),
                              "min_ghosts": min_ghosts}), flush=True)


if __name__ == "__main__":
    main()

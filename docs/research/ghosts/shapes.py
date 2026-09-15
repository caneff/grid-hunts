"""Ghosts, all visible: search ghost shapes directly.

    uv run docs/research/ghosts/shapes.py --seconds 120 --seed 1 --out DIR

A shape fixes its givens: each ghost shows its ghost-neighbour count. So the
search needs no grid variables. A shape is admissible when its counts are
1-8, distinct within every row, column and box, and one count is 8. Each
admissible shape goes to a bitmask sudoku counter that stops at `cap`
solutions. Hill climbing toggles ghost cells and keeps a move that leaves the
shape admissible and does not raise the capped solution count; a count of 1 is
a hit.
"""

import argparse
import json
import math
import random
import time
from pathlib import Path

N = 9
CELLS = [(r, c) for r in range(N) for c in range(N)]
BOX = [(r // 3) * 3 + c // 3 for r, c in CELLS]
NEIGH = [[(r + a) * 9 + c + b for a in (-1, 0, 1) for b in (-1, 0, 1)
          if (a or b) and 0 <= r + a < N and 0 <= c + b < N] for r, c in CELLS]
PEERS = [{j for j in range(81) if j != i and (CELLS[i][0] == CELLS[j][0] or CELLS[i][1] == CELLS[j][1]
                                              or BOX[i] == BOX[j])} for i in range(81)]


def givens(shape):
    """{cell: digit} for a shape (a set of cell indices), or None if inadmissible."""
    out = {}
    for i in shape:
        n = sum(j in shape for j in NEIGH[i])
        if n == 0:
            return None
        out[i] = n
    for i, d in out.items():
        if any(out.get(j) == d for j in PEERS[i]):
            return None
    return out


def count_solutions(given, cap, varying=None, store=None):
    """Solutions of the sudoku with these givens, stopping at cap.

    If `varying` is a set, it receives the cells whose digit differs between
    the first solution found and any later one. If `store` is a list, it
    receives every solution found (81 digits)."""
    rows, cols, boxes = [0] * 9, [0] * 9, [0] * 9
    grid = [0] * 81
    for i, d in given.items():
        bit = 1 << d
        r, c = CELLS[i]
        if rows[r] & bit or cols[c] & bit or boxes[BOX[i]] & bit:
            return 0
        rows[r] |= bit
        cols[c] |= bit
        boxes[BOX[i]] |= bit
        grid[i] = d
    empty = [i for i in range(81) if not grid[i]]
    full = 0b1111111110
    found = 0
    first = None

    def search():
        nonlocal found, first
        best, best_opts, best_n = -1, 0, 10
        for i in empty:
            if grid[i]:
                continue
            r, c = CELLS[i]
            opts = full & ~(rows[r] | cols[c] | boxes[BOX[i]])
            n = bin(opts).count("1")
            if n < best_n:
                best, best_opts, best_n = i, opts, n
                if n <= 1:
                    break
        if best < 0:
            found += 1
            if store is not None:
                store.append(grid[:])
            if varying is not None:
                if first is None:
                    first = grid[:]
                else:
                    varying.update(i for i in empty if grid[i] != first[i])
            return found >= cap
        if best_n == 0:
            return False
        r, c, b = CELLS[best][0], CELLS[best][1], BOX[best]
        opts = best_opts
        while opts:
            bit = opts & -opts
            opts ^= bit
            rows[r] |= bit
            cols[c] |= bit
            boxes[b] |= bit
            grid[best] = bit.bit_length() - 1
            stop = search()
            rows[r] ^= bit
            cols[c] ^= bit
            boxes[b] ^= bit
            grid[best] = 0
            if stop:
                return True
        return False

    search()
    return found


def has_eight(given):
    return given is not None and 8 in given.values()


def seed_shape(rng, min_ghosts):
    """A random solvable admissible shape: grid and ghosts together in CP-SAT."""
    from ortools.sat.python import cp_model

    m = cp_model.CpModel()
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    x = [[m.new_bool_var(f"x{i}{d}") for d in range(9)] for i in range(81)]
    for i in range(81):
        m.add_exactly_one(x[i])
    for d in range(9):
        for k in range(9):
            m.add_exactly_one(x[k * 9 + c][d] for c in range(9))
            m.add_exactly_one(x[r * 9 + k][d] for r in range(9))
            m.add_exactly_one(x[i][d] for i in range(81) if BOX[i] == k)
    eight = []
    for i in range(81):
        digit = sum((d + 1) * x[i][d] for d in range(9))
        m.add(sum(g[j] for j in NEIGH[i]) == digit).only_enforce_if(g[i])
        e = m.new_bool_var(f"e{i}")
        m.add_implication(e, g[i])
        m.add_implication(e, x[i][7])
        eight.append(e)
    m.add_bool_or(eight)
    m.add(sum(g) >= min_ghosts)
    for i in range(81):
        m.add_hint(x[i][rng.randrange(9)], 1)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.random_seed = rng.randrange(1 << 30)
    s.parameters.randomize_search = True
    s.parameters.max_time_in_seconds = 30
    assert s.solve(m) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    return {i for i in range(81) if s.value(g[i])}


def climb(rng, deadline, cap, min_ghosts):
    shape = seed_shape(rng, min_ghosts)
    g = givens(shape)
    score = count_solutions(g, cap) if g else 0
    best = (score, shape, g)
    steps = 0
    temp = 0.1
    while time.monotonic() < deadline and score != 1:
        i = rng.randrange(81)
        move = {i}
        if rng.random() < 0.5:
            move.add(rng.choice(NEIGH[i]))
        trial = shape ^ move
        tg = givens(trial)
        steps += 1
        if not has_eight(tg):
            continue
        ts = count_solutions(tg, cap)
        if ts == 0:
            continue
        worse = math.log(ts) - math.log(score)
        if worse <= 0 or rng.random() < math.exp(-worse / temp):
            shape, g, score = trial, tg, ts
            if score < best[0]:
                best = (score, shape, g)
        temp = max(0.01, temp * 0.9999)
    score, shape, g = best
    return shape, g, score, steps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=120)
    ap.add_argument("--climb-seconds", type=float, default=20)
    ap.add_argument("--cap", type=int, default=2000)
    ap.add_argument("--min-ghosts", type=int, default=20)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    t0 = time.monotonic()
    climbs = hits = 0
    while time.monotonic() - t0 < a.seconds:
        shape, g, score, steps = climb(rng, min(time.monotonic() + a.climb_seconds, t0 + a.seconds), a.cap, a.min_ghosts)
        climbs += 1
        rec = {"seed": a.seed, "climb": climbs, "ghosts": len(shape), "solutions_capped": score,
               "steps": steps, "shape": sorted(shape), "givens": {str(k): v for k, v in (g or {}).items()}}
        if score == 1:
            hits += 1
            with open(a.out / "hits.jsonl", "a") as f:
                f.write(json.dumps(rec) + "\n")
        print(f"climb {climbs}: ghosts={len(shape)} solutions={score}{'+' if score >= a.cap else ''} "
              f"steps={steps} t={time.monotonic() - t0:.0f}s", flush=True)
    print(f"climbs={climbs} hits={hits}")


if __name__ == "__main__":
    main()

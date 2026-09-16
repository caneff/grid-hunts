"""Double-check the claim that r9c1+r9c2+r9c8 ghosts with r7c4 banned is impossible.

    uv run docs/research/ghosts/recheck_pins.py

Independent of connected.py: house distinctness is posted as add_all_different
over one variable per cell, where a non-ghost gets its own dummy value instead
of a count, rather than as pairwise != between ghosts. Positive controls run
first, so an encoding that forbids everything shows up as a failed control
rather than as a confirmation. A random sampler gives a second, non-solver
opinion.
"""

import random

from ortools.sat.python import cp_model

from shapes import BOX, CELLS, NEIGH

FORCE = [72, 73, 79]  # r9c1, r9c2, r9c8
BAN = [57]  # r7c4
HOUSES = ([[r * 9 + c for c in range(9)] for r in range(9)]
          + [[r * 9 + c for r in range(9)] for c in range(9)]
          + [[i for i in range(81) if BOX[i] == b] for b in range(9)])


def model(force, ban):
    m = cp_model.CpModel()
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    # v[i]: the given on a ghost, or a dummy unique to the cell otherwise.
    v = [m.new_int_var(1, 200, f"v{i}") for i in range(81)]
    for i in range(81):
        count = sum(g[j] for j in NEIGH[i])
        m.add(v[i] == count).only_enforce_if(g[i])
        m.add(count >= 1).only_enforce_if(g[i])
        m.add(v[i] == 100 + i).only_enforce_if(g[i].Not())
    for house in HOUSES:
        m.add_all_different([v[i] for i in house])
    for i in force:
        m.add(g[i] == 1)
    for i in ban:
        m.add(g[i] == 0)
    return m, g


def solve(force, ban, seconds=60):
    m, g = model(force, ban)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 8
    s.parameters.max_time_in_seconds = seconds
    st = s.solve(m)
    shape = {i for i in range(81) if s.value(g[i])} if st in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None
    return s.status_name(st), shape


def admissible(shape):
    """Plain-Python check: counts 1-8, distinct within every house."""
    given = {}
    for i in shape:
        n = sum(j in shape for j in NEIGH[i])
        if not 1 <= n <= 8:
            return False
        given[i] = n
    for house in HOUSES:
        vals = [given[i] for i in house if i in given]
        if len(vals) != len(set(vals)):
            return False
    return True


def main():
    print("positive controls")
    for label, force, ban in (("no pins", [], []), ("forced only", FORCE, []),
                              ("ban only", [], BAN), ("two forced + ban", FORCE[:2], BAN),
                              ("forced + ban a neighbour of r7c4", FORCE, [58])):
        st, shape = solve(force, ban)
        ok = shape is not None and admissible(shape) and all(i in shape for i in force) \
            and not any(i in shape for i in ban)
        print(f"  {label}: {st}" + (f", {len(shape)} ghosts, checks out: {ok}" if shape else ""))

    print("the claim")
    st, shape = solve(FORCE, BAN, seconds=300)
    print(f"  r9c1+r9c2+r9c8 forced, r7c4 banned: {st}")

    print("random sampler (no solver)")
    rng = random.Random(0)
    hits = 0
    for _ in range(2_000_000):
        shape = set(FORCE)
        for _ in range(rng.randrange(6, 36)):
            i = rng.randrange(81)
            if i not in BAN:
                shape.add(i)
        if admissible(shape):
            hits += 1
    print(f"  2,000,000 random shapes with the pins: {hits} admissible")
    rng = random.Random(0)
    control = 0
    for _ in range(200_000):
        shape = set(FORCE)
        for _ in range(rng.randrange(6, 36)):
            shape.add(rng.randrange(81))
        if admissible(shape):
            control += 1
    print(f"  control, same but r7c4 allowed: {control} admissible in 200,000")


if __name__ == "__main__":
    main()

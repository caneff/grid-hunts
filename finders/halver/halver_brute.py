"""The shared halver layer's independent check (spec #52): a backtracking
search over (digit, halver) per cell that counts the solutions of a halver
board up to a limit, for any line type. It shares no code with the CP-SAT
model in `halver_rules.py`, so a modelling bug in one shows up as a
disagreement with the other.

`solutions(narrowing, lines, n, box, limit, deadline)` returns up to `limit`
solutions, each a (digits row by row, frozenset of halver cells) pair, in
search order. Given a `deadline` (a `time.monotonic()` reading), it raises
`OutOfTime` at the first search node past it, so a caller gets no count
rather than a short one. A line is any (end a, body cells, end b) triple of
(row, column) cells from 0.

A line type plugs in through `narrowing(body, houses, n)`, called once per
line with its body and every house as cell indices (row * n + column). It
returns that line's narrowing step, `narrow(end_a, end_b, bodies)`: given
the doubled values still open at each end and at each body cell, as masks
with bit v set when the doubled value v is possible, it returns the masks
kept at end a, at end b and at every body cell, or None when no value of the
ends fits. The search keeps each line's answers, since the same masks recur
across branches.

Every cell keeps a 2n-bit mask of the choices still open: bit d-1 for a
plain d, bit n+d-1 for a halved d. Cells are compared by doubled value: a
halver's digit, twice a plain cell's. Before each branch the masks are
narrowed to a fixpoint:

- a cell down to one choice (once per branch) takes its digit from its houses' other cells,
  and, as a halver, takes the halver from its houses' other cells and its
  halved digit from every other cell;
- a digit with one place left in a house goes there;
- a house with one cell left that can be its halver gets it, and a house
  with a cell that can only be a halver clears the halver from the rest;
- a halved digit with one cell left gets it;
- each line's narrowing step keeps the doubled values it allows.

An empty mask, or a digit or halver with no place left, ends the branch. The
search then branches on whichever has the fewest options: one cell's
choices, or the cells left that can be one house's halver.
"""

import time


class OutOfTime(Exception):
    """The search passed its deadline before it could count to `limit`."""


def _houses(n, box):
    bh, bw = box
    rows = [[(r, c) for c in range(n)] for r in range(n)]
    cols = [[(r, c) for r in range(n)] for c in range(n)]
    boxes = [
        [(br + dr, bc + dc) for dr in range(bh) for dc in range(bw)]
        for br in range(0, n, bh)
        for bc in range(0, n, bw)
    ]
    return rows + cols + boxes


class _Contradiction(Exception):
    pass


def _bits(mask):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def solutions(narrowing, lines, n, box, limit, deadline=None):
    houses = [[r * n + c for r, c in house] for house in _houses(n, box)]
    size = n * n
    digit_bits = (1 << n) - 1
    halver_bits = digit_bits << n
    peers = [set() for _ in range(size)]
    for house in houses:
        for i in house:
            peers[i].update(house)
    for i in range(size):
        peers[i].discard(i)
    peers = [sorted(p) for p in peers]
    lines = [
        (a * n + ac, [r * n + c for r, c in body], b * n + bc)
        for (a, ac), body, (b, bc) in lines
    ]

    # Doubled-value masks: bit v set when the doubled value v is possible.
    plain_doubled = [
        sum(1 << (2 * (d + 1)) for d in range(n) if m >> d & 1) for m in range(1 << n)
    ]

    def doubled_values(mask):
        return plain_doubled[mask & digit_bits] | ((mask >> n) << 1)

    def choices_with_doubled(keep):
        """The choice bits whose doubled value is in the doubled-value mask
        `keep`."""
        bits = ((keep >> 1) & digit_bits) << n
        for d in range(n):
            if keep >> (2 * (d + 1)) & 1:
                bits |= 1 << d
        return bits

    lines = [(a, body, b, narrowing(body, houses, n), {}) for a, body, b in lines]

    def narrow_line(cells, line):
        # The narrowing depends only on the line's doubled-value masks, which
        # recur across branches, so each line keeps its answers.
        a, body, b, narrow, memo = line
        key = (
            doubled_values(cells[a]),
            doubled_values(cells[b]),
            *(doubled_values(cells[p]) for p in body),
        )
        if key not in memo:
            kept = narrow(key[0], key[1], key[2:])
            memo[key] = None if kept is None else tuple(map(choices_with_doubled, kept))
        kept = memo[key]
        if kept is None:
            raise _Contradiction
        bits_a, bits_b, body_bits = kept
        changed = restrict(cells, a, bits_a)
        changed |= restrict(cells, b, bits_b)
        for p in body:
            changed |= restrict(cells, p, body_bits)
        return changed

    def restrict(cells, i, keep):
        before = cells[i]
        after = before & keep
        if not after:
            raise _Contradiction
        if after != before:
            cells[i] = after
            return True
        return False

    def propagate(cells, settled):
        changed = True
        while changed:
            changed = False
            for i in range(size):
                mask = cells[i]
                if settled[i] or mask & (mask - 1):
                    continue
                settled[i] = True
                digit = (mask | mask >> n) & digit_bits
                clear = ~(digit | digit << n)
                if mask & halver_bits:
                    clear &= ~halver_bits
                    for j in range(size):
                        if j != i:
                            changed |= restrict(cells, j, ~mask)
                for j in peers[i]:
                    changed |= restrict(cells, j, clear)
            for house in houses:
                once = twice = 0
                halver_places = []
                for i in house:
                    d = (cells[i] | cells[i] >> n) & digit_bits
                    twice |= once & d
                    once |= d
                    if cells[i] & halver_bits:
                        halver_places.append(i)
                if once != digit_bits or not halver_places:
                    raise _Contradiction
                for d in _bits(once & ~twice):
                    for i in house:
                        if (cells[i] | cells[i] >> n) >> d & 1:
                            changed |= restrict(cells, i, (1 << d) | (1 << (n + d)))
                            break
                if len(halver_places) == 1:
                    changed |= restrict(cells, halver_places[0], halver_bits)
                only = [i for i in halver_places if not cells[i] & digit_bits]
                if len(only) > 1:
                    raise _Contradiction
                if only:
                    for i in halver_places:
                        if i != only[0]:
                            changed |= restrict(cells, i, digit_bits)
            once = twice = 0
            for mask in cells:
                h = mask >> n
                twice |= once & h
                once |= h
            if once != digit_bits:
                raise _Contradiction
            for d in _bits(once & ~twice):
                for i in range(size):
                    if cells[i] >> (n + d) & 1:
                        changed |= restrict(cells, i, 1 << (n + d))
                        break
            for line in lines:
                changed |= narrow_line(cells, line)

    found = []

    def search(cells, settled):
        if deadline is not None and time.monotonic() > deadline:
            raise OutOfTime
        try:
            propagate(cells, settled)
        except _Contradiction:
            return False
        best = None  # (option count, children)
        for i in range(size):
            count = cells[i].bit_count()
            if count > 1 and (best is None or count < best[0]):
                best = (count, [(i, 1 << bit) for bit in _bits(cells[i])])
        if best is None:
            grid = tuple(
                tuple(
                    (
                        (cells[r * n + c] | cells[r * n + c] >> n) & digit_bits
                    ).bit_length()
                    for c in range(n)
                )
                for r in range(n)
            )
            halvers = frozenset(
                divmod(i, n) for i in range(size) if cells[i] & halver_bits
            )
            found.append((grid, halvers))
            return len(found) >= limit
        for house in houses:
            places = [i for i in house if cells[i] & halver_bits]
            if len(places) > 1 and len(places) < best[0]:
                best = (len(places), [(i, halver_bits) for i in places])
        for i, keep in best[1]:
            child = list(cells)
            child[i] &= keep
            if search(child, list(settled)):
                return True
        return False

    search([(1 << (2 * n)) - 1] * size, [False] * size)
    return found

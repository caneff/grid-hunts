"""SCRATCH: count r5 half fillings for one placement of Chris's chosen 8 region. One worker.

The 8 region holds two r5 cells, so the other seven r5 cells are in seven different regions and the
ninth region is off r5. Each of the seven is its r5 cell, an up part and a down part. This counts how
the rows above r5 fill from up parts and the rows below from down parts, with the ninth region on
either side. Then it counts the pairs of fillings whose sizes match (up + down = 8 for every region).

Size matches are an upper bound on layouts: a matching pair still needs each region's two parts to
form a listed region, one forced 7 and counts 1-6 on the low regions. It does not solve digits.

The placement counted is the one with the most usable (up, down) pairs, the worst of the 14.
The bottom half is flipped onto the top half's coordinates, so one filler serves both.
"""

import json
import pickle
import random
import sys
import time
from pathlib import Path

from aqre_r5_cover import mask_of
from aqre_r5_oriented import canonical
from jigsaw_r5_diversity import shape_key

ROW = 4
SHAPE = [(0, 0), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2), (3, 0), (3, 1)]
STAGE_SECONDS = 600.0
MAX_ENTRIES = 30_000_000
ALL_HALF = (1 << 36) - 1


class Capped(Exception):
    pass


def half_bit(r, q):
    """The bit in half coordinates: columns sweep left to right, so the frontier stays small."""
    row = r if r < ROW else 8 - r
    return 1 << (q * 4 + row)


def split(mask):
    """(top, bottom) half masks of a 81-bit mask, ignoring r5."""
    top = bottom = 0
    for r in range(9):
        for q in range(9):
            if r != ROW and mask >> (r * 9 + q) & 1:
                if r < ROW:
                    top |= half_bit(r, q)
                else:
                    bottom |= half_bit(r, q)
    return top, bottom


def usable_pairs(table, eight, c8, n):
    """For each root column, the (up, down) half masks of regions usable beside this 8."""
    parity = c8 % 2
    pairs = {}
    for c in range(9):
        if c in (c8, n):
            continue
        found = set()
        for e in table[c]:
            mask = e["mask"]
            if mask & eight:
                continue
            if any(mask >> (ROW * 9 + q) & 1 for q in range(9) if q != c):
                continue
            able_8, shaded_7, unshaded_7, counts = e[c % 2 == parity]
            if able_8:
                continue
            if shaded_7 or unshaded_7:
                if shaded_7 == unshaded_7:
                    continue
            elif not counts:
                continue
            found.add(split(mask))
        pairs[c] = found
    return pairs


def connected_pieces(free, size):
    """Every connected set of `size` free half cells, as masks."""
    def around(cell):
        q, row = cell // 4, cell % 4
        for x, y in ((q - 1, row), (q + 1, row), (q, row - 1), (q, row + 1)):
            if 0 <= x < 9 and 0 <= y < 4:
                yield x * 4 + y

    neighbours = {i: sum(1 << j for j in around(i)) for i in range(36)}
    layer = {1 << i for i in range(36) if free >> i & 1}
    for _ in range(size - 1):
        grown = set()
        for piece in layer:
            edge = 0
            rest = piece
            while rest:
                low = rest & -rest
                rest ^= low
                edge |= neighbours[low.bit_length() - 1]
            edge &= free & ~piece
            while edge:
                low = edge & -edge
                edge ^= low
                grown.add(piece | low)
        layer = grown
    return layer


class Filler:
    """One half: free cells, seven roots' parts, and possibly the ninth region's pieces."""

    def __init__(self, free, roots, parts, ninth):
        self.free = free
        self.roots = roots
        self.anchors = [1 << (c * 4 + 3) for c in roots]
        self.can_empty = [0 in parts[c] for c in roots]
        self.index = []
        for c in roots:
            by_low = {}
            for p in parts[c]:
                if p and not p & ~free:
                    by_low.setdefault(p & -p, []).append(p)
            self.index.append(by_low)
        self.sizes = {p: bin(p).count("1") for c in roots for p in parts[c]}
        self.ninth = {}
        for p in ninth:
            self.ninth.setdefault(p & -p, []).append(p)
        self.has_ninth = bool(ninth)

    def _viable(self, free, unused):
        i = 0
        rest = unused
        while rest:
            if rest & 1 and not self.can_empty[i] and not free & self.anchors[i]:
                return False
            rest >>= 1
            i += 1
        return True

    def _choices(self, free, unused, low):
        i = 0
        rest = unused
        while rest:
            if rest & 1:
                for p in self.index[i].get(low, ()):
                    if not p & ~free:
                        yield i, p
            rest >>= 1
            i += 1

    def _finished(self, unused):
        return all(self.can_empty[i] for i in range(len(self.roots)) if unused >> i & 1)

    def count(self, deadline):
        """Fillings of the half, by a memo on free cells, unused roots and the ninth."""
        memo = {}

        def go(free, unused, ninth_left):
            if not free:
                return int(not ninth_left and self._finished(unused))
            key = free | unused << 36 | ninth_left << 43
            known = memo.get(key)
            if known is not None:
                return known
            if len(memo) % 100_000 == 0 and (time.time() > deadline or len(memo) > MAX_ENTRIES):
                raise Capped(len(memo))
            total = 0
            if self._viable(free, unused):
                low = free & -free
                for i, p in self._choices(free, unused, low):
                    total += go(free ^ p, unused ^ 1 << i, ninth_left)
                if ninth_left:
                    for p in self.ninth.get(low, ()):
                        if not p & ~free:
                            total += go(free ^ p, unused, False)
            memo[key] = total
            return total

        return go(self.free, (1 << len(self.roots)) - 1, self.has_ninth), len(memo)

    def by_sizes(self, deadline):
        """Fillings keyed by each root's part size, 4 bits per root."""
        memo = {}
        held = [0]

        def go(free, unused, ninth_left):
            if not free:
                return {0: 1} if not ninth_left and self._finished(unused) else {}
            key = free | unused << 36 | ninth_left << 43
            known = memo.get(key)
            if known is not None:
                return known
            if len(memo) % 10_000 == 0 and (time.time() > deadline or held[0] > MAX_ENTRIES):
                raise Capped(held[0])
            out = {}
            if self._viable(free, unused):
                low = free & -free
                for i, p in self._choices(free, unused, low):
                    shift = self.sizes[p] << (4 * i)
                    for v, n in go(free ^ p, unused ^ 1 << i, ninth_left).items():
                        out[v + shift] = out.get(v + shift, 0) + n
                if ninth_left:
                    for p in self.ninth.get(low, ()):
                        if not p & ~free:
                            for v, n in go(free ^ p, unused, False).items():
                                out[v] = out.get(v, 0) + n
            memo[key] = out
            held[0] += len(out)
            return out

        return go(self.free, (1 << len(self.roots)) - 1, self.has_ninth)

    def brute(self):
        """Every filling, unmemoised, each checked as an exact partition. For the self-check."""
        found = 0

        def go(free, unused, ninth_left, used):
            nonlocal found
            if not free:
                if not ninth_left and self._finished(unused):
                    seen = 0
                    for p in used:
                        assert not seen & p
                        seen |= p
                    assert seen == self.free
                    found += 1
                return
            low = free & -free
            for i, p in self._choices(free, unused, low):
                go(free ^ p, unused ^ 1 << i, ninth_left, used + [p])
            if ninth_left:
                for p in self.ninth.get(low, ()):
                    if not p & ~free:
                        go(free ^ p, unused, False, used + [p])

        go(self.free, (1 << len(self.roots)) - 1, self.has_ninth, [])
        return found

    def first(self, deadline):
        """One filling as {root index: part} plus any ninth, for the planted self-check."""
        tried = set()

        def go(free, unused, ninth_left, used):
            if not free:
                return used if not ninth_left and self._finished(unused) else None
            key = free | unused << 36 | ninth_left << 43
            if key in tried or time.time() > deadline or not self._viable(free, unused):
                return None
            tried.add(key)
            low = free & -free
            for i, p in self._choices(free, unused, low):
                got = go(free ^ p, unused ^ 1 << i, ninth_left, [*used, (i, p)])
                if got is not None:
                    return got
            if ninth_left:
                for p in self.ninth.get(low, ()):
                    if not p & ~free:
                        got = go(free ^ p, unused, False, [*used, (-1, p)])
                        if got is not None:
                            return got
            return None

        return go(self.free, (1 << len(self.roots)) - 1, self.has_ninth, [])


def self_check(free, roots, parts, ninth, name):
    """The memo and the size table must agree with plain enumeration on a planted sample."""
    full = Filler(free, roots, parts, ninth)
    planted = full.first(time.time() + 60.0)
    rng = random.Random(1)
    small = {}
    for c in roots:
        pool = sorted(parts[c])
        small[c] = set(rng.sample(pool, min(25, len(pool))))
    small_ninth = set(rng.sample(sorted(ninth), min(50, len(ninth))))
    if planted:
        for i, p in planted:
            if i < 0:
                small_ninth.add(p)
            else:
                small[roots[i]].add(p)
        for i, c in enumerate(roots):
            if not any(j == i for j, _ in planted) and 0 in parts[c]:
                small[c].add(0)
    test = Filler(free, roots, small, small_ninth if ninth else set())
    brute = test.brute()
    counted, _ = test.count(time.time() + 60.0)
    sized = sum(test.by_sizes(time.time() + 60.0).values())
    good = brute == counted == sized and (brute > 0 or not planted)
    print(f"  check {name}: planted {'yes' if planted else 'none in 60s'}, brute {brute}, memo {counted}, by sizes {sized}: {'ok' if good else 'FAILED'}", flush=True)
    return good


def draw(eight, c8, n):
    for r in range(9):
        row = ""
        for q in range(9):
            if (r, q) == (ROW, c8):
                row += "8"
            elif (r, q) == (ROW, n):
                row += "9"
            else:
                row += "#" if eight >> (r * 9 + q) & 1 else "."
        print("   ", row, flush=True)


def main(out):
    with (out / "oriented.pickle").open("rb") as f:
        table = pickle.load(f)
    key = shape_key(SHAPE)
    best = None
    seen = 0
    for e in json.loads((out / "eight-regions-r5.json").read_text()):
        cells = [tuple(x) for x in e["cells"]]
        if shape_key(cells) != key:
            continue
        c8 = e["column"]
        eight = mask_of(cells)
        if not canonical(eight, c8):
            continue
        n = next(q for r, q in cells if r == ROW and q != c8)
        pairs = usable_pairs(table, eight, c8, n)
        total = sum(len(v) for v in pairs.values())
        seen += 1
        print(f"placement {seen}: 8 in r5c{c8 + 1}, 9 in r5c{n + 1}, usable regions {total}, smallest column {min(len(v) for v in pairs.values())}", flush=True)
        if best is None or total > best[0]:
            best = (total, eight, c8, n, pairs)
    total, eight, c8, n, pairs = best
    print(f"counting 8 in r5c{c8 + 1}, 9 in r5c{n + 1}, {total} usable regions", flush=True)
    draw(eight, c8, n)
    roots = sorted(pairs)
    up = {c: {a for a, _ in pairs[c]} for c in roots}
    down = {c: {b for _, b in pairs[c]} for c in roots}
    for c in roots:
        print(f"  r5c{c + 1}: {len(pairs[c])} regions, {len(up[c])} up parts, {len(down[c])} down parts", flush=True)
    top_taken, bottom_taken = split(eight)
    free = {"top": ALL_HALF & ~top_taken, "bottom": ALL_HALF & ~bottom_taken}
    parts = {"top": up, "bottom": down}
    ninth = {}
    for side in free:
        begun = time.time()
        ninth[side] = connected_pieces(free[side], 9)
        print(f"{side}: {bin(free[side]).count('1')} free cells, {len(ninth[side])} ninth-region pieces, {time.time() - begun:.0f}s", flush=True)
    for side in free:
        for name, nine in (("with ninth", ninth[side]), ("no ninth", set())):
            if not self_check(free[side], roots, parts[side], nine, f"{side} {name}"):
                print("self-check FAILED; nothing counted", flush=True)
                return
    fillers = {(side, has): Filler(free[side], roots, parts[side], ninth[side] if has else set()) for side in free for has in (True, False)}
    counts = {}
    for (side, has), filler in fillers.items():
        begun = time.time()
        try:
            counts[side, has], states = filler.count(begun + STAGE_SECONDS)
            print(f"{side}, ninth {'here' if has else 'elsewhere'}: {counts[side, has]:,} fillings, {states:,} states, {time.time() - begun:.0f}s", flush=True)
        except Capped as e:
            print(f"{side}, ninth {'here' if has else 'elsewhere'}: CAPPED at {e.args[0]:,} states, {time.time() - begun:.0f}s", flush=True)
    sized = {}
    for (side, has), filler in fillers.items():
        if (side, has) not in counts:
            continue
        begun = time.time()
        try:
            sized[side, has] = filler.by_sizes(begun + STAGE_SECONDS)
            print(f"{side}, ninth {'here' if has else 'elsewhere'}: {len(sized[side, has]):,} size patterns, {time.time() - begun:.0f}s", flush=True)
        except Capped as e:
            print(f"{side}, ninth {'here' if has else 'elsewhere'}: size table CAPPED at {e.args[0]:,} entries, {time.time() - begun:.0f}s", flush=True)
    full = sum(8 << (4 * i) for i in range(len(roots)))
    for top_has in (True, False):
        a, b = sized.get(("top", top_has)), sized.get(("bottom", not top_has))
        place = "top" if top_has else "bottom"
        if a is None or b is None:
            print(f"ninth in {place}: size matches not counted, a table was capped", flush=True)
            continue
        matches = sum(n_a * b.get(full - v, 0) for v, n_a in a.items())
        patterns = sum(1 for v in a if full - v in b)
        print(f"ninth in {place}: {matches:,} matching pairs across {patterns:,} size patterns", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

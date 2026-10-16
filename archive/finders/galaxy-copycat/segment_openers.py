"""Which copycat-RSL line pairings force something, including single-cell segments.

Model (a relaxation, geometry-free, so anything it forces is truly forced):
- a line is a list of segment lengths; every segment sums to the line's S;
- a segment lies in one box, so its values are distinct digits 1-9 except
  that one copycat may duplicate one value (at most one copycat per box);
- the two lines of a pair have the same value multiset (so equal length).

For every pair of structures with equal length, we list the
feasible (S_A, S_B, min copycats over both lines) and flag the pairings
where the sums are pinned or a copycat is unavoidable.

Usage: python3 segment_openers.py [max_len]
"""

from __future__ import annotations

import sys
from collections import defaultdict
from functools import cache
from itertools import combinations

DIGITS = range(1, 10)


def partitions(n: int, smallest: int = 1) -> list[tuple[int, ...]]:
    if n == 0:
        return [()]
    out = []
    for first in range(smallest, n + 1):
        out.extend((first, *rest) for rest in partitions(n - first, first))
    return out


@cache
def segment_multisets(
    length: int, total: int
) -> tuple[tuple[tuple[int, ...], int], ...]:
    """All value multisets of a one-box segment: (sorted values, copycats used)."""
    found = [(base, 0) for base in combinations(DIGITS, length) if sum(base) == total]
    for base in combinations(DIGITS, length - 1):
        for dup in base:
            vals = tuple(sorted((*base, dup)))
            if sum(vals) == total:
                found.append((vals, 1))
    return tuple(found)


def line_multisets(parts: tuple[int, ...], s: int) -> dict[tuple[int, ...], int]:
    """Value multiset -> min copycats, for a line with these segments all summing s."""
    acc: dict[tuple[int, ...], int] = {(): 0}
    for length in parts:
        nxt: dict[tuple[int, ...], int] = {}
        for vals, cc in acc.items():
            for seg, seg_cc in segment_multisets(length, s):
                key = tuple(sorted(vals + seg))
                nxt[key] = min(nxt.get(key, 99), cc + seg_cc)
        acc = nxt
    return acc


def main() -> None:
    max_len = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    for n in range(4, max_len + 1):
        structs = partitions(n)
        print(f"\n== length {n}: structures {structs}")
        for i, a in enumerate(structs):
            for b in structs[i:]:
                if a == b:
                    continue
                # equal totals: len(a)*S_A == len(b)*S_B
                feas: dict[tuple[int, int], int] = {}
                for s_a in range(3, 46):
                    if (len(a) * s_a) % len(b):
                        continue
                    s_b = len(a) * s_a // len(b)
                    ma = line_multisets(a, s_a)
                    if not ma:
                        continue
                    mb = line_multisets(b, s_b)
                    for vals, cc_a in ma.items():
                        if vals in mb:
                            key = (s_a, s_b)
                            feas[key] = min(feas.get(key, 99), cc_a + mb[vals])
                if not feas:
                    print(f"  {a} vs {b}: IMPOSSIBLE")
                    continue
                min_cc = min(feas.values())
                sums = sorted(feas)
                tag = ""
                if len(sums) == 1:
                    tag += " SUMS PINNED"
                if min_cc > 0:
                    tag += f" COPYCAT FORCED (>= {min_cc})"
                by_cc = defaultdict(list)
                for k, v in feas.items():
                    by_cc[v].append(k)
                detail = "; ".join(
                    f"cc={cc}: {sorted(by_cc[cc])}" for cc in sorted(by_cc)
                )
                print(f"  {a} vs {b}:{tag or ' open'}  {detail}")


if __name__ == "__main__":
    main()

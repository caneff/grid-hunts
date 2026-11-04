"""SCRATCH: why does r2 have 0 fillings above it? Is that the rules, or a bug?

For each r2 placement this draws the 8 region and lists, for each root, how many regions are usable with
and without the class rules, and how many have nothing in r1. It then counts r1 fillings with any region
that fits, class rules off, using the same filler. Without class rules it should find fillings when the
geometry allows them, so a zero there comes from geometry, and a positive count puts the zero on the rules.
"""

import sys
from pathlib import Path

import aqre_row_enumerate as e
from aqre_r5_cover import mask_of


def main(out):
    row = 1
    e.set_row(row)
    table = e.build_table(out, row)
    e.STATE["table"] = table
    found, _ = e.placements(row)
    for number, (eight, c8, n) in enumerate(found, 1):
        print(f"placement {number}: 8 in r2c{c8 + 1}, 9 in r2c{n + 1}", flush=True)
        for r in range(5):
            print("   ", "".join("8" if (r, q) == (row, c8) else "9" if (r, q) == (row, n) else "#" if eight >> (r * 9 + q) & 1 else "." for q in range(9)), flush=True)
        pairs = e.usable(table, eight, c8, n, row, False)
        roots = sorted(pairs)
        free = sum(e.above_bit(0, q, 1) for q in range(9)) & ~e.to_above(eight, row)
        bits = sum(1 << (row * 9 + q) for q in range(9))
        anyway = {}
        for c in roots:
            anyway[c] = [x["mask"] for x in table[c] if not x["mask"] & eight and x["mask"] & bits == 1 << (row * 9 + c)]
        tops = {c: {e.to_above(m, row) for m in anyway[c]} for c in roots}
        ruled = {c: {e.to_above(x[0], row) for x in pairs[c]} for c in roots}
        for c in roots:
            print(f"    r2c{c + 1}: {len(pairs[c])} usable of {len(anyway[c])} that fit; none in r1: {sum(not x[0] & 511 for x in pairs[c])} usable, {sum(not m & 511 for m in anyway[c])} fit", flush=True)
        above = e.pieces_above(free, row)
        for name, parts in (("class rules on", ruled), ("class rules off", tops)):
            counted = sum(e.fillings(free, roots, parts, row, ninth)[0] for ninth in ([above, set()] if above else [set()]))
            print(f"    r1 fillings, {name}: {counted}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

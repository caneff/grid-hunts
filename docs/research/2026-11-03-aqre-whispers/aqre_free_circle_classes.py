"""SCRATCH: with circles free of any row, what can each shape and circle cell be? One process.

usage: aqre_free_circle_classes.py DIR

Chris's option A, 2026-11-05: 8 different circles, one region able to be the 8 by shape, which sets the colours, then
one region able to be the 7, the rest topping out at 6. Each hole-free free shape is tested with each cell as circle,
judged alone, using `aqre_r5_oriented.holds_coloured` with no 9 in the region. Pairs count once under rotation and
reflection, which keep the circle's colour relative to the region.

Classes, as `aqre_nine_shared.class_of`: able to be the 8 (colour-blind, so circle high). Otherwise, for a circle on the
8's colour (high) or on the other colour (low): `seven` when exactly one of shaded 7 and unshaded 7 is possible,
`both` when both are, so the rules refuse it, `top` when neither is and some count 1-6 fits.

Control: every one-cell region in the r5 catalogue must get the same entry here. Writes free-circle-classes.pickle.
"""

import pickle
import sys
import time
from collections import Counter
from pathlib import Path

import aqre_r5_oriented as oriented
from aqre_r5_oriented import holds_coloured
from aqre_r5_region_max import lines_of
from aqre_top_six_picture import pair_key
from aqre_top_six_shapes import free_shapes, has_hole, normal

oriented.ROW = -1


def entry_of(cells, root):
    lines = lines_of(set(cells))
    entry = {}
    for root_high in (True, False):
        eight = holds_coloured(cells, root, 8, lines, root_high)
        shaded_7 = holds_coloured(cells, root, 7, lines, root_high, True)
        unshaded_7 = holds_coloured(cells, root, 7, lines, root_high, False)
        counts = ()
        if not (eight or shaded_7 or unshaded_7):
            counts = tuple(v for v in range(1, 7) if holds_coloured(cells, root, v, lines, root_high))
        entry[root_high] = (eight, shaded_7, unshaded_7, counts)
    return entry


def kind(entry, root_high):
    _, shaded_7, unshaded_7, counts = entry[root_high]
    if shaded_7 or unshaded_7:
        return "seven" if shaded_7 != unshaded_7 else "both"
    return "top" if counts else "none"


def neighbours_in(cells, root):
    r, c = root
    return sum((r + a, c + b) in cells for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def main(out):
    begun = time.time()
    pairs = {}
    shapes = [s for s in free_shapes() if not has_hole(s)]
    for shape in shapes:
        for root in shape:
            key = pair_key(shape, root)
            if key not in pairs:
                pairs[key] = {"shape": shape, "root": root, "entry": entry_of(shape, root)}
    print(f"{len(shapes)} shapes, {len(pairs)} free shape and circle pairs, {time.time() - begun:.0f}s", flush=True)

    with (out / "oriented.pickle").open("rb") as f:
        table = pickle.load(f)
    checked = wrong = 0
    for c in range(5):
        for x in table[c]:
            cells = [(q // 9, q % 9) for q in range(81) if x["mask"] >> q & 1]
            if sum(r == 4 for r, _ in cells) != 1 or has_hole(cells):
                continue
            top, left = min(r for r, _ in cells), min(q for _, q in cells)
            key = pair_key(sorted(normal(cells)), (4 - top, c - left))
            checked += 1
            have = pairs[key]["entry"]
            for root_high in (True, False):
                if tuple(have[root_high][:3]) != tuple(x[root_high][:3]) or tuple(have[root_high][3]) != tuple(x[root_high][3]):
                    wrong += 1
                    break
    print(f"control against the r5 catalogue: {checked} one-cell regions, {wrong} differ", flush=True)
    if wrong or not checked:
        raise SystemExit("CONTROL FAILED")

    able = [p for p in pairs.values() if p["entry"][True][0]]
    other = [p for p in pairs.values() if not p["entry"][True][0]]
    print(f"able to be the 8: {len(able)} pairs on {len({p['shape'] for p in able})} shapes; not able: {len(other)} pairs on {len({p['shape'] for p in other})} shapes", flush=True)
    print(f"low-coloured root able to hold 8: {sum(bool(p['entry'][False][0]) for p in pairs.values())}", flush=True)
    joint = Counter((kind(p["entry"], True), kind(p["entry"], False)) for p in other)
    print("not able to be the 8, by (circle on the 8's colour, circle on the other colour):", flush=True)
    for (high, low), n in sorted(joint.items()):
        print(f"  {high:6} {low:6} {n}", flush=True)
    for root_high, name in ((True, "on the 8's colour"), (False, "on the other colour")):
        for want in ("seven", "top"):
            got = [p for p in other if kind(p["entry"], root_high) == want]
            print(f"{name}, {want}: {len(got)} pairs on {len({p['shape'] for p in got})} shapes", flush=True)
    for root_high, name in ((True, "on the 8's colour"), (False, "on the other colour")):
        tops = [p for p in other if kind(p["entry"], root_high) == "top"]
        print(f"{name}, tops by highest count: {sorted(Counter(max(p['entry'][root_high][3]) for p in tops).items())}", flush=True)
        print(f"{name}, tops able to hold each count: {[sum(v in p['entry'][root_high][3] for p in tops) for v in range(1, 7)]}", flush=True)
        print(f"{name}, tops by circle's neighbours in the shape: {sorted(Counter(neighbours_in(set(p['shape']), p['root']) for p in tops).items())}", flush=True)
    usable = {s for p in other for s in [p["shape"]] if kind(p["entry"], True) == "top" or kind(p["entry"], False) == "top"}
    print(f"shapes with a circle cell that tops out at 6 on at least one colour: {len(usable)} of {len(shapes)}", flush=True)
    with (out / "free-circle-classes.pickle").open("wb") as f:
        pickle.dump(pairs, f)
    print(f"done, {time.time() - begun:.0f}s", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

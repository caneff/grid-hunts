"""The catalogue builder: difference 5 is today's file, difference 4 matches a hand check.

1. At difference 5 the builder reproduces the committed catalogue byte for byte.
2. At difference 4 the 1x2 and 2x2 answers match the hand-worked values below,
   both from the builder and from the committed difference-4 catalogue.
3. A layer that hits the count cap takes its support from CP-SAT, and that
   support equals the enumerated one.
4. Every layer of a shape with both sides <= 4 is enumerated in full: the
   committed difference-4 catalogue has none truncated, and the three that the
   100,000 cap used to cut hold their full-enumeration counts (#767).

Hand work, difference 4. N(t) is the set of digits at least 4 from t:

    N(1) = 5..9      N(2) = 6..9      N(3) = 7 8 9     N(4) = 8 9
    N(5) = 1 9       N(6) = 1 2       N(7) = 1 2 3     N(8) = 1 2 3 4
    N(9) = 1..5

1x2: an ordered pair (t, u) with u in N(t), so 5+4+3+2+2+2+3+4+5 = 30. Every
N(t) is non-empty, so every digit sits in both cells, and the digit 2 (the area)
can be circled in both. A row's two cells are distinct already, so the box
offset changes nothing: all nine offsets hold the same 30.

2x2, cells [[p, q], [r, s]]: p-q, p-r, q-s and r-s are the four adjacencies;
p, s share nothing and neither do q, r. Choose p and s (81 ways), then q and r
independently from N(p) & N(s): L = sum over (p, s) of |N(p) & N(s)|^2 = 314.
In a box, two cells repeating a digit must be a diagonal pair, since a row
or column pair is already distinct. So a box only matters when it holds
a whole diagonal: the four offsets (ro, co) in {0,1}^2 put all four cells in one
box and need p, q, r, s all different; the other five split rows or columns so
that no diagonal shares a box, and equal L.
All different: L - (p = s) - (q = r) + (both) = 314 - 112 - 112 + 30 = 120,
using sum of |N(t)|^2 = 25+16+9+4+4+4+9+16+25 = 112 and 30 ordered edges.
A 5 in a 2x2 has both neighbours in {1, 9}, so they are 1 and 9, and the cell
diagonal to the 5 is in N(1) & N(9) = {5}: the same digit, banned in one box.
So the four one-box offsets lose the digit 5 and keep every other digit
(for example [[4, 8], [9, 1]] puts a 4 in the corner, so every cell can be
circled: a 2x2 area is 4), while the other five offsets keep all nine.

    uv run finders/renbanana/tools/test_build_rectangle_catalogue.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rectangle_catalogue as bc

ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = ROOT / "docs/research/renbanana"
ONE_BOX = {"0,0", "0,1", "1,0", "1,1"}
ALL_DIGITS = list(range(1, 10))
NO_FIVE = [d for d in ALL_DIGITS if d != 5]


def check_1x2(entry, label):
    """entry: (count, support, circle_cells) of one layer of the 1x2."""
    count, support, circles = entry
    assert count == 30, (label, count)
    assert support == [[ALL_DIGITS, ALL_DIGITS]], (label, support)
    assert circles == [[0, 0], [0, 1]], (label, circles)


def check_2x2(entries, label):
    """entries: {offset or 'L': (count, support, circle_cells)} for the 2x2."""
    all_nine = [[ALL_DIGITS] * 2] * 2
    no_five = [[NO_FIVE] * 2] * 2
    every_cell = [[0, 0], [0, 1], [1, 0], [1, 1]]
    for key, (count, support, circles) in entries.items():
        if key in ONE_BOX:
            assert (count, support) == (120, no_five), (label, key, count, support)
        else:
            assert (count, support) == (314, all_nine), (label, key, count, support)
        assert circles == every_cell, (label, key, circles)


def built(difference, shape, count_cap=bc.DEFAULT_COUNT_CAP):
    a, b = shape
    layers = {"L": bc.summarise(a, b, difference, None, count_cap)}
    for ro in range(3):
        for co in range(3):
            layers[f"{ro},{co}"] = bc.summarise(a, b, difference, (ro, co), count_cap)
    return {k: (v[0], v[2], v[3]) for k, v in layers.items()}, layers


def stored(catalogue, shape):
    e = catalogue[shape]
    out = {"L": (e["L_count"], e["L_support"], e["L_circle_cells"])}
    out.update(
        {k: (v["count"], v["support"], v["circle_cells"]) for k, v in e["B"].items()}
    )
    return out


# 1. Difference 5 is today's file, byte for byte.
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "d5.json"
    bc.main(["--difference", "5", "--out", str(out)])
    assert out.read_bytes() == (CATALOGUE / "rectangle-catalogue.json").read_bytes(), (
        "difference 5 no longer reproduces rectangle-catalogue.json"
    )

# 2. Difference 4 against the hand work, from the builder and the committed file.
one_by_two, _ = built(4, (1, 2))
for key, entry in one_by_two.items():
    check_1x2(entry, f"builder 1x2 {key}")
two_by_two, _ = built(4, (2, 2))
check_2x2(two_by_two, "builder 2x2")
committed = json.loads((CATALOGUE / "rectangle-catalogue-d4.json").read_text())
for key, entry in stored(committed, "1x2").items():
    check_1x2(entry, f"committed 1x2 {key}")
check_2x2(stored(committed, "2x2"), "committed 2x2")

# 3. The cap path: a cap below the count truncates, and CP-SAT support equals enumerated.
_, capped = built(4, (2, 2), count_cap=10)
_, full = built(4, (2, 2))
for key, (count, truncated, support, circles, _) in capped.items():
    assert truncated and count == 10, (key, truncated, count)
    assert (support, circles) == (full[key][2], full[key][3]), key
assert (
    bc.cpsat_support(2, 8, 5) == [] and bc.cpsat_support(3, 7, 5) == []
)  # L_count 0 at 5

# 4. Small shapes are never truncated, and the old truncated layers are exact.
for shape, entry in committed.items():
    a, b = map(int, shape.split("x"))
    if max(a, b) > bc.UNCAPPED_SIDE:
        continue
    assert not entry["L_truncated"], (shape, "L")
    for key, layer in entry["B"].items():
        assert not layer.get("truncated"), (shape, key)
assert committed["3x4"]["L_count"] == 139_524
assert committed["4x4"]["B"]["1,1"]["count"] == 200_400
assert committed["4x4"]["L_count"] == 2_107_212
assert bc.cap_for(4, 4, 100) is None and bc.cap_for(3, 5, 100) == 100

print("OK")

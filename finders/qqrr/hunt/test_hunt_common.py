"""The shared hunt helpers (#605): the q34 criterion is one definition, a HIT block parses by
its markers rather than by line offsets, and chan_sweep is driven by a call, not by sys.argv.
Seams: hunt_common's public functions and chan_sweep.configure.

    uv run finders/qqrr/hunt/test_hunt_common.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hunt_common as hc

# q34_zone: the windows sharing a cell with one of (r, c)'s four windows, by hand.
assert hc.q34_zone(9, 4, 4) == [(wr, wc) for wr in range(2, 6) for wc in range(2, 6)]
assert hc.q34_zone(9, 1, 1) == [(wr, wc) for wr in range(3) for wc in range(3)]

# q34_accept: a QQRR-35 cell qualifies unless a QR-1 window sits in its zone.
n = 9
ranks = [[5] * (n - 1) for _ in range(n - 1)]
cr = [[100] * n for _ in range(n)]
cr[3][3] = 35
cr[6][6] = 34
cr[2][2] = 40  # outside 34..36
assert hc.q34_accept(ranks, cr) == [(3, 3), (6, 6)]
ranks[1][1] = (
    1  # inside the zone of (3, 3) (windows rows 1..4, cols 1..4), not of (6, 6)
)
assert hc.q34_accept(ranks, cr) == [(6, 6)]
ranks[6][6] = 1
assert hc.q34_accept(ranks, cr) == []
# edge cells are never candidates
cr2 = [[100] * n for _ in range(n)]
cr2[0][3] = 35
cr2[8][8] = 35
assert hc.q34_accept([[5] * 8 for _ in range(8)], cr2) == []

# parse_hits: the grid is found by its marker, however many tie lines precede it.
TIE_A = "  tie r3c2 1|2 = r3c5 3|4, number 1234567, QQRR 12"
TIE_B = "  tie r4c2 5|6 = r4c5 7|8, number 7654321, QQRR 34"
QQRR = "  QQRR cage 33 corner 5 QR r6c6 10 bounded cell 7"
G1 = "111111111/222222222/333333333/444444444/555555555/666666666/777777777/888888888/999999999"
G2 = "999999999/888888888/777777777/666666666/555555555/444444444/333333333/222222222/111111111"
text = "\n".join(
    [
        "big: hunt=r5c1 ...",
        "  q34: r4c4=35",
        "HIT 1 3.0s",
        TIE_A,
        QQRR,
        "  grid " + G1,
        "HIT 2 9.0s",
        TIE_A,
        TIE_B,
        QQRR,
        "  grid " + G2,
        "timeout: hunt=r5c1 ...",
    ]
)
hits = hc.parse_hits(text)
assert [h["grid"] for h in hits] == [G1, G2]
assert [len(h["ties"]) for h in hits] == [1, 2]
assert hits[1]["ties"][1] == ("r4c2", "r4c5", "7654321", "34")
assert hc.parse_hits("no hits here\n") == []
# a log cut after a HIT line, or after HIT and one tie, parses to the complete blocks before it
done = "HIT 1 1s\n" + TIE_A + "\n" + QQRR + "\n  grid " + G1 + "\n"
assert [h["grid"] for h in hc.parse_hits(done + "HIT 2 2s\n")] == [G1]
assert [h["grid"] for h in hc.parse_hits(done + "HIT 2 2s\n" + TIE_B + "\n")] == [G1]
assert hc.parse_hits("HIT 1 1s\n") == []
# logged_grids reads every grid line of a log file
import tempfile

with tempfile.TemporaryDirectory() as d:
    log = Path(d) / "big-x.log"
    log.write_text(
        "HIT 1 1s\n" + TIE_A + "\n  grid " + G1 + "\nHIT 2 2s\n  grid " + G2 + "\n"
    )
    assert hc.logged_grids(log) == [G1, G2]

# tie_line and grid_line are what parse_hits reads back.
grid = [[(r + c) % 9 + 1 for c in range(9)] for r in range(9)]
assert hc.grid_line(grid) == "  grid " + "/".join(
    "".join(map(str, row)) for row in grid
)
line = hc.tie_line((2, 1), (2, 4), 1234567, [1, 2], [3, 4], 12)
assert line == "  tie r3c2 1|2 = r3c5 3|4, number 1234567, QQRR 12", line
assert hc.parse_hits("HIT 1 1s\n" + line + "\n" + hc.grid_line(grid))[0]["ties"] == [
    ("r3c2", "r3c5", "1234567", "12")
]

# HUNTS: one table, the seed a 9x9 grid of digits.
assert set(hc.HUNTS) == {"r5c1", "r1c5"}
for _cage, _target, seed in hc.HUNTS.values():
    assert len(seed.split("/")) == 9 and all(len(r) == 9 for r in seed.split("/"))

# chan_sweep is driven by a call: importing it runs nothing and reads no sys.argv.
import chan_sweep

chan_sweep.configure(["tr", "1", "5", "/dev/null", "r1c5", "2", "lin2", "ten=r5c5"])
assert chan_sweep.workers == 2
assert {"lin2"} == chan_sweep.FLAGS
assert chan_sweep.TEN == (4, 4)
assert hc.HUNTS["r1c5"][0] == chan_sweep.CAGE
chan_sweep.configure(["tl", "1", "5", "/dev/null", "r5c1"])
assert chan_sweep.workers == 1
assert set() == chan_sweep.FLAGS
assert chan_sweep.TEN == (5, 5)  # not carried over from the previous call
assert hc.HUNTS["r5c1"][0] == chan_sweep.CAGE
print("ok")

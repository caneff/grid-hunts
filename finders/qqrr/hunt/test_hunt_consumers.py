"""The hunt scripts that read finder logs do it through hunt_common (#641). Each consumer is
tested at its own seam, two ways: on a real log, for what it makes of a parsed tie or grid
(sync_presets' label, chan_big's order, check_3436's report); and with hunt_common's parser
swapped for a stub, to see the consumer take its input from the parser and not from its own
re-parse of the log. Seams: sync_presets.sync, chan_big.earlier_hits, check_3436.report.

    uv run finders/qqrr/hunt/test_hunt_consumers.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hunt_common as hc

# isort: split
import chan_big
import check_3436
import sync_presets

SEED_A = hc.HUNTS["r5c1"][2]
SEED_B = hc.HUNTS["r1c5"][2]
G_PLAIN = "/".join(["123456789"] * 9)  # differs from both seeds
ACROSS = "  tie r3c2 1|2 = r3c8 3|4, number 1234567, QQRR 35"
BOXONLY = "  tie r1c1 1|2 = r2c2 3|4, number 7654321, QQRR 34"


def hit(i, tie, grid):
    return f"HIT {i} 1.0s\n{tie}\n  QQRR cage 33 corner 5 QR r6c6 10 bounded cell 7\n  grid {grid}\n"


def write(d, name, text):
    (Path(d) / name).write_text(text)


class Stub:
    """Swap hunt_common.<name> for `fn` while the block runs."""

    def __init__(self, name, fn):
        self.name, self.fn = name, fn

    def __enter__(self):
        self.old = getattr(hc, self.name)
        setattr(hc, self.name, self.fn)

    def __exit__(self, *exc):
        setattr(hc, self.name, self.old)


with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp)

    # sync_presets: the label names number and QQRR each by its own field, in the right order.
    # its own directory: a q34 log beside the others would tie earlier_hits' best sort key
    q = d / "q34"
    q.mkdir()
    write(
        q, "big-r5c1-r5c5-tl-q34.log", hit(1, ACROSS, G_PLAIN) + hit(2, BOXONLY, SEED_A)
    )
    page = d / "explorer.html"
    page.write_text("x\nconst PRESETS=[\nold,\n];\n")
    assert sync_presets.sync(page, q) == 2
    text = page.read_text()
    assert "tie r3c2 = r3c8 (1234567, QQRR 35) · tl #1 · 34–36 hunt" in text, text
    assert "tie r1c1 = r2c2 (7654321, QQRR 34, box only) · tl #2" in text, text
    assert '"tl","4,0",{"4,4":"10"}],' in text, text
    assert sync_presets.sync(page, q) == 0  # grids already present are skipped
    # ... and the page is read through the parser: a stubbed hit is what lands in it.
    fake = hc.Tie("r2c2", "r2c3", "11", "22")
    with Stub("parse_hits", lambda t: [{"ties": [fake], "grid": "STUBGRID"}]):
        page.write_text("const PRESETS=[\n")
        assert sync_presets.sync(page, q) == 1
        assert page.read_text().count("tie r2c2 = r2c3 (11, QQRR 22)") == 1

    # chan_big.earlier_hits: this hunt's logs only, the nearest window and corner first.
    write(d, "big-r5c1-r5c5-tl.log", "  grid " + SEED_A + "\n")
    write(d, "big-r5c1-r1c1-tr.log", "  grid " + G_PLAIN + "\n")
    write(d, "big-r1c5-r5c5-tl.log", "  grid " + SEED_B + "\n")
    # the same grid in an earlier-sorting log: check_3436 names it for that one
    write(d, "big-r1c5-r1c1-bl.log", "  grid " + SEED_B + "\n")
    old_logs, chan_big.LOGS = chan_big.LOGS, d
    try:
        got = chan_big.earlier_hits("r5c1", "r5c5", "tl")
        assert got[0] == ("r5c5", "tl", SEED_A), got
        assert ("r1c1", "tr", G_PLAIN) in got and all(g != SEED_B for *_, g in got), got
        assert chan_big.earlier_hits("r5c1", "r1c1", "tr")[0] == ("r1c1", "tr", G_PLAIN)
        with Stub("logged_grids", lambda p: ["STUB/" + Path(p).name]):
            assert ("r5c5", "tl", "STUB/big-r5c1-r5c5-tl.log") in chan_big.earlier_hits(
                "r5c1", "r5c5", "tl"
            )
    finally:
        chan_big.LOGS = old_logs

    # check_3436: one line per distinct grid, named for the first log that holds it.
    lines = check_3436.report(d)
    srcs = {ln.split()[0] for ln in lines}
    assert len(lines) == 3 and srcs == {
        "big-r1c5-r1c1-bl.log",
        "big-r5c1-r1c1-tr.log",
        "big-r5c1-r5c5-tl.log",
    }, lines
    seed_b = next(ln for ln in lines if ln.startswith("big-r1c5-"))
    assert "QR1 ['r3c1'] clean: ['r7c8'] grid " + SEED_B in seed_b, seed_b
    assert all(
        " QR1 " in ln and " clean: " in ln and ln.endswith(" grid " + ln.split()[-1])
        for ln in lines
    )
    with Stub("logged_grids", lambda p: [SEED_A]):
        stubbed = check_3436.report(d)
    assert len(stubbed) == 1 and stubbed[0].endswith(" grid " + SEED_A), stubbed

print("ok")

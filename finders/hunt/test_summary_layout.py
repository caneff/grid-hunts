"""`hunt_dir.summary_layout`: the one `summary DIR` layout (#165).

Pure: a `HuntRead` in, lines out. The finders' own wording rides in a
`Wording`; the layout and the verify hint are the same for every finder.

    uv run finders/hunt/test_summary_layout.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_checks import check, finish
from hunt_dir import HuntRead, Wording, summary_layout


def events(*pairs):
    return [{"event": "seed_done", "seed": s, "outcome": o} for s, o in pairs]


EVENTS = events((0, "example"), (1, "duplicate"), (2, "rejected"))
HIT = {"id": 1}
BAD = {"id": 2}
READ = HuntRead({}, EVENTS, [HIT], [{"id": 3}], [(BAD, "why")])

# Default wording: the driver's own layout.
lines = summary_layout(READ, Wording())
check("headline", lines[0] == "1 verified hits in 3 seeds (0..2)")
check(
    "default counts",
    lines[1] == "found 1, empty 0, timed out 0, duplicate 1, rejected 1",
)
check(
    "unchecked line names `verify DIR`",
    lines[2] == "1 candidates unchecked: the hunt ran with --no-verify "
    "and `verify DIR` has not run",
)
check("rejected line", lines[3] == "1 candidates rejected by `verify DIR`")
check("hits are listed after the seed lines", lines[-1].startswith("hit {"))

# A finder's wording changes the words, never the order or the hint.
wording = Wording(
    hit_noun="hits",
    tail=lambda run: f", clock {run['c']}",
    none_note=": a search result",
    counts=lambda evs: "outcomes: " + str(len(evs)),
    counts_last=True,
    describe_hit=lambda r: [f"hit {r['id']}", "  row"],
    describe_unchecked=lambda r: f"unchecked {r['id']}",
    describe_rejected=lambda r, why: f"rejected {r['id']}: {why}",
    hit_key=lambda r: -r["id"],
)
read = HuntRead({"c": 5}, EVENTS, [{"id": 1}, {"id": 4}], [{"id": 3}], [(BAD, "why")])
lines = summary_layout(read, wording)
check("finder headline", lines[0] == "2 hits in 3 seeds (0..2), clock 5")
check(
    "hint is the same",
    "`verify DIR` has not run" in lines[1] and lines[2].endswith("`verify DIR`"),
)
check("counts_last puts counts after the flags", lines[3] == "outcomes: 3")
check(
    "records follow, hits ordered by hit_key",
    lines[-6:]
    == ["hit 4", "  row", "hit 1", "  row", "unchecked 3", "rejected 2: why"],
)

none = summary_layout(HuntRead({"c": 5}, [], [], [], []), wording)
check(
    "none found carries the note",
    none[0] == "none found in 0 seeds, clock 5: a search result",
)
check(
    "no verified hit",
    summary_layout(HuntRead({"c": 5}, [], [], [HIT], []), wording)[0]
    == "no verified hit in 0 seeds, clock 5",
)
finish()

"""The U-Bahn finder's `hunt` CLI run (#773), black-box.

A fresh 4x4 hunt with exactly 2 crosses in r2: every example it writes must
be one of the networks the brute-force enumeration finds unique under its
full set of outside numbers, and no two examples may be the same grid of kinds
under the board's symmetries. Then `hunt verify DIR` over hand-written
records, the flags and records the finder refuses, and a board that is not
square. One CP-SAT worker; about five seconds in all.

    uv run finders/ubahn/test_ubahn_hunt.py
"""

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import brute
import network
from cli_checks import check, finish, read_jsonl, run_cli
from dedupe import canonical_key
from ubahn_finder import Candidate, UbahnFinder
from verified_io import read_verified

FINDER = HERE / "ubahn_finder.py"
ROWS = COLS = 4
EXACTLY = "2:cross:r2"


def record(net, exactly=EXACTLY):
    """The record the finder writes for a 4x4 network, its `exactly` then
    replaced by `exactly`."""
    found = Candidate(ROWS, COLS, frozenset(net), None)
    return {**UbahnFinder(ROWS, COLS).record(found), "exactly": exactly}


def network_of(rec):
    """The network a record holds, read through the finder."""
    return UbahnFinder(rec["rows"], rec["cols"]).candidate_from_record(rec).network


def canonical(net, rows=ROWS, cols=COLS):
    """The dedupe key a hunt files `net` under."""
    finder = UbahnFinder(rows, cols)
    return canonical_key(finder.key(Candidate(rows, cols, net, None)), finder.symmetry)


def mirrored(net, cols):
    """The network reflected left to right."""
    return frozenset(
        tuple(sorted(((r, cols - 1 - c), (r2, cols - 1 - c2))))
        for (r, c), (r2, c2) in net
    )


def upturned(net, rows):
    """The network reflected top to bottom."""
    return frozenset(
        tuple(sorted(((rows - 1 - r, c), (rows - 1 - r2, c2))))
        for (r, c), (r2, c2) in net
    )


unique = brute.two_crosses_in_r2().unique
shared = sorted(brute.two_crosses_in_r2().valid - unique, key=sorted)

with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "hunt"
    config = ["--rows", "4", "--cols", "4", "--exactly", EXACTLY, "--timeout", "10"]
    r = run_cli(FINDER, *config, "--out", str(out), "--seeds=0:40", "--workers", "1")
    check(f"a 40-seed hunt exits 0 (stderr: {r.stderr[-500:]})", r.returncode == 0)

    examples = read_jsonl(out / "examples.jsonl")
    summary = json.loads((out / "summary.json").read_text())
    check(f"the hunt wrote examples ({len(examples)})", len(examples) >= 10)
    check(
        "every example is a network the brute force finds unique",
        all(network_of(ex) in unique for ex in examples),
    )
    check(
        "every example records its own full set of outside numbers",
        all(
            (
                tuple(map(tuple, ex["numbers"]["rows"])),
                tuple(map(tuple, ex["numbers"]["cols"])),
            )
            == network.outside_numbers(network_of(ex), ROWS, COLS)
            for ex in examples
        ),
    )
    check(
        "every row and column has five outside numbers, blank last, that "
        "add up to its length",
        all(
            len(counts) == 5
            and sum(counts) == 4
            and counts[network.BLANK]
            == sum(1 for cell in cells if not any(network.arms(network_of(ex), cell)))
            for ex in examples
            for axis, groups in (
                ("rows", [[(i, j) for j in range(4)] for i in range(4)]),
                ("cols", [[(j, i) for j in range(4)] for i in range(4)]),
            )
            for counts, cells in zip(ex["numbers"][axis], groups, strict=True)
        ),
    )
    keys = [canonical(network_of(ex)) for ex in examples]
    check(
        "every example's dedupe key is the one the finder files its network under",
        all(
            tuple(ex["__dedupe_key__"]) == key
            for ex, key in zip(examples, keys, strict=True)
        ),
    )
    check("no two examples share a grid of kinds under D4", len(set(keys)) == len(keys))
    check(
        f"the hunt met and dropped duplicates ({summary.get('duplicates')})",
        summary.get("duplicates", 0) > 0,
    )
    check(
        "every seed is accounted for",
        summary.get("seeds_done") == 40
        and summary["examples"] + summary["duplicates"] + summary["empty"] == 40
        and summary["rejected"] == 0,
    )
    config = json.loads((out / "run.json").read_text()).get("config")
    check(
        "run.json records the board, the condition and the timeout",
        (config["rows"], config["cols"], config["exactly"], config["timeout"])
        == (4, 4, EXACTLY, 10.0),
    )

with tempfile.TemporaryDirectory() as d:
    out = Path(d)
    good = min(unique, key=sorted)
    # The first edge of `good` switched off in its record: the finder cannot
    # draw a network with a dead end, so the record is damaged after it.
    (r0, c0), (r1, c1) = min(good)
    side, row, col = ("h", r0, c0) if r0 == r1 else ("v", r0, c0)
    dead_end = record(good)
    bits = dead_end[side][row]
    dead_end[side][row] = bits[:col] + "0" + bits[col + 1 :]
    good_blanks = sum(1 for c in range(COLS) if not any(network.arms(good, (0, c))))
    cases = [
        ("a unique network", record(good), True, ""),
        (
            "a network that shares its outside numbers",
            record(shared[0]),
            False,
            "not unique",
        ),
        (
            "a unique network filed under another condition",
            record(good, exactly="1:cross:r2"),
            False,
            "1:cross:r2",
        ),
        ("a network with a dead end", dead_end, False, "dead end"),
        (
            "a unique network filed under a row off its board",
            record(good, exactly="0:cross:r9"),
            False,
            "r9",
        ),
        (
            "a unique network filed under a column off its board",
            record(good, exactly="4:blank:c7"),
            False,
            "c7",
        ),
        (
            "a unique network filed under its own blank count in r1",
            record(good, exactly=f"{good_blanks}:blank:r1"),
            True,
            "",
        ),
        (
            "a unique network filed under another blank count in r1",
            record(good, exactly=f"{good_blanks + 1}:blank:r1"),
            False,
            ":blank:r1",
        ),
        (
            "two separate networks",
            record(
                frozenset(
                    e
                    for top in (0, 2)
                    for e in (
                        ((top, 0), (top, 1)),
                        ((top + 1, 0), (top + 1, 1)),
                        ((top, 0), (top + 1, 0)),
                        ((top, 1), (top + 1, 1)),
                    )
                ),
                exactly=None,
            ),
            False,
            "not connected",
        ),
    ]
    (out / "examples.jsonl").write_text(
        "".join(json.dumps(rec) + "\n" for _, rec, _, _ in cases)
    )
    (out / "progress.jsonl").write_text(
        "".join(
            json.dumps({"event": "seed_done", "seed": k, "outcome": "example"}) + "\n"
            for k in range(len(cases))
        )
    )
    r = run_cli(FINDER, "verify", str(out))
    check(f"hunt verify exits 0 (stderr: {r.stderr[-500:]})", r.returncode == 0)
    _, verdicts = read_verified(out / "verified.jsonl")
    for (name, _, want, reason), v in zip(cases, verdicts, strict=True):
        check(f"verify: {name} -> {want}", v["ok"] is want)
        if reason:
            check(f"verify: {name} says why ({reason})", reason in v.get("reason", ""))

with tempfile.TemporaryDirectory() as d:
    # A record `verify` cannot read is refused by name, never read as a
    # network with fewer edges or as a record with no condition.
    good = min(unique, key=sorted)
    for i, (name, damage, reason) in enumerate(
        (
            (
                "an edge row that is not 0s and 1s",
                {"h": ["x1x", *record(good)["h"][1:]]},
                "'x1x' of h",
            ),
            (
                "an edge row of the wrong length",
                {"v": ["1", *record(good)["v"][1:]]},
                "'1' of v",
            ),
            ("an empty condition", {"exactly": ""}, "N:KIND:rK"),
        )
    ):
        out = Path(d) / str(i)
        out.mkdir()
        (out / "examples.jsonl").write_text(
            json.dumps({**record(good), **damage}) + "\n"
        )
        (out / "progress.jsonl").write_text(
            json.dumps({"event": "seed_done", "seed": 0, "outcome": "example"}) + "\n"
        )
        r = run_cli(FINDER, "verify", str(out))
        check(
            f"verify refuses {name}, exit 2, naming {reason!r}",
            r.returncode == 2
            and reason in r.stderr
            and not (out / "verified.jsonl").exists(),
        )

with tempfile.TemporaryDirectory() as d:
    board = ["--rows", "4", "--cols", "4"]
    for i, (flags, reason) in enumerate(
        (
            ([*board, "--exactly", "2:cross"], "N:KIND:rK"),
            ([*board, "--exactly", "2:loop:r2"], "loop"),
            ([*board, "--exactly", "2:cross:r5"], "r5"),
            ([*board, "--exactly", "2:cross:r00"], "N:KIND:rK"),
            ([*board, "--exactly", ""], "N:KIND:rK"),
            (["--rows", "1", "--cols", "4"], "2x2"),
        )
    ):
        out = Path(d) / str(i)
        r = run_cli(FINDER, *flags, "--out", str(out), "--seeds=0:1", "--workers", "1")
        check(
            f"{' '.join(flags)} is refused, exit 2, naming {reason!r}",
            r.returncode == 2 and reason in r.stderr and not out.exists(),
        )

with tempfile.TemporaryDirectory() as d:
    # 2x8 has 16 cells, a square's count: D4 would take it for a 4x4.
    out = Path(d) / "hunt"
    r = run_cli(FINDER,
        "--rows", "2", "--cols", "8", "--timeout", "10",
        "--out", str(out), "--seeds=0:12", "--workers", "1",
    )  # fmt: skip
    check(f"a 2x8 hunt exits 0 (stderr: {r.stderr[-500:]})", r.returncode == 0)
    examples = read_jsonl(out / "examples.jsonl")
    nets = [network_of(ex) for ex in examples]
    check(f"the 2x8 hunt wrote examples ({len(examples)})", len(examples) >= 2)
    # On this board some sampled network shares its outside numbers with
    # another. The search itself must drop it, with the reason, and leave
    # `verify` nothing to reject.
    summary = json.loads((out / "summary.json").read_text())
    reasons = [
        e.get("empty_reason")
        for e in read_jsonl(out / "progress.jsonl")
        if e.get("outcome") == "empty"
    ]
    check(
        f"a seed whose network is not unique is empty, saying so ({reasons})",
        "not unique" in reasons and summary["rejected"] == 0,
    )
    check(
        "every 2x8 example is a network",
        all(not network.why_not_network(net, 2, 8) for net in nets),
    )
    check(
        "every 2x8 dedupe key is the finder's, the same for the network's four images",
        all(
            tuple(ex["__dedupe_key__"])
            == canonical(net, 2, 8)
            == canonical(mirrored(net, 8), 2, 8)
            == canonical(upturned(net, 2), 2, 8)
            == canonical(upturned(mirrored(net, 8), 2), 2, 8)
            for ex, net in zip(examples, nets, strict=True)
        ),
    )
    check(
        "no 2x8 example is the mirror image of another",
        all(mirrored(a, 8) != b for a in nets for b in nets if a != b),
    )

finish()

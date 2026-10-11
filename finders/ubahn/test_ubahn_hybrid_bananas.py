"""The condition "at least N banana regions" on the hybrid finder (#792).

A banana region is a region of odd values, over grid cells and number cells
together, as `hybrid.regions` finds them. The pinned 4x4 answers are the
decision log's, § Hybrid: at least N banana regions: of the 18 valid grids
16 have one banana region and 2 have two, so N = 2 leaves 2 grids, N = 3
none, and N = 2 with `r2c4` circled exactly one. The rule reader, the brute
force, each engine and the CLI must all say so. The condition is held to
the rule reader with a piece count on 5x5, listed in full, and with the
blank strip on 6x6, by seed.

One worker; about fifty seconds.

    uv run finders/ubahn/test_ubahn_hybrid_bananas.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import json
import random
import subprocess
import tempfile

import brute
import hybrid
import hybrid_finder
import hybrid_sat
import network
import time_bananas
from subprocess_env import success_env

FINDER = HERE / "hybrid_finder.py"
BOARD = ["--rows", "4", "--cols", "4", "--timeout", "20"]
TIME_LIMIT = 20.0
R2C4 = frozenset({(1, 3)})
WORDS = ("infeasible", "unique", "not_unique")

# The two 4x4 grids with two banana regions, as `hybrid.drawing` draws their
# grid cells, and a grid with one.
TWO_BANANAS = (
    ("┌─────┬──┐", "├──┬──┤  │", "└──┼──┤  │", "   └──┴──┘"),
    ("┌──┬──┐", "│  ├──┼──┐", "├──┴──┴──┤", "└────────┘"),
)
ONE_BANANA = ("┌──┬──┬──┐", "├──┼──┼──┤", "├──┼──┼──┤", "└──┴──┴──┘")

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def drawn(net):
    """The grid cells of a 4x4 network as `hybrid.drawing` draws them."""
    return tuple(line[13:] for line in hybrid.drawing(net, 4, 4)[4:])


def by_drawing(picture):
    (net,) = [net for net in brute.hybrid_grids(4, 4) if drawn(net) == picture]
    return net


TWO = {by_drawing(picture) for picture in TWO_BANANAS}
ONE = by_drawing(ONE_BANANA)


def test_reader():
    for net in TWO:
        check(
            "the reader passes a grid with two banana regions asked for two",
            hybrid.failures(net, 4, 4, min_bananas=2) == [],
        )
        check(
            "the reader refuses it asked for three, by name",
            hybrid.failures(net, 4, 4, min_bananas=3)
            == ["2 banana regions, fewer than the 3 asked for"],
        )
    check(
        "the reader refuses a grid with one banana region asked for two",
        hybrid.why_not_hybrid(ONE, 4, 4, min_bananas=2)
        == "1 banana region, fewer than the 2 asked for",
    )
    check(
        "a network that is none is refused on that alone",
        hybrid.failures(frozenset(), 4, 4, min_bananas=2)
        == [network.why_not_network(frozenset(), 4, 4)],
    )


def test_brute():
    for n, want in (
        (1, ("not_unique", 18)),
        (2, ("not_unique", 2)),
        (3, ("infeasible", 0)),
    ):
        check(
            f"brute force, at least {n}: {want}",
            brute.classify(4, 4, (), min_bananas=n) == want,
        )
    check(
        "brute force, at least 2 with r2c4 circled: one grid, where r2c4 alone has more",
        brute.classify(4, 4, [(1, 3)], min_bananas=2) == ("unique", 1)
        and brute.classify(4, 4, [(1, 3)])[1] > 1,
    )
    check(
        "brute force, at least 2 with the blank strip: none",
        brute.classify(4, 4, (), blank_strip=True, min_bananas=2) == ("infeasible", 0),
    )


def asked(side, n, circles=frozenset(), blank_strip=False, exactly=None):
    return hybrid.Conditions(side, side, circles, exactly, blank_strip, min_bananas=n)


def test_engine(name, engine):
    """An engine's two calls against the 4x4 answers."""

    def classify(conditions):
        return engine.classify(conditions, time_limit=TIME_LIMIT, workers=1)

    status, found = classify(asked(4, 2))
    check(
        f"{name}, 4x4, at least 2: not_unique, with one of the two grids",
        status == "not_unique" and found in TWO,
    )
    check(
        f"{name}, 4x4, at least 3: no grid, proven, not a timeout",
        classify(asked(4, 3)) == ("infeasible", None),
    )
    check(
        f"{name}, 4x4, at least 2 with the blank strip: no grid, proven",
        classify(asked(4, 2, blank_strip=True)) == ("infeasible", None),
    )
    (only,) = [net for net in TWO if not hybrid.why_not_hybrid(net, 4, 4, R2C4)]
    check(
        f"{name}, 4x4, at least 2 with r2c4 circled: the one grid",
        classify(asked(4, 2, R2C4)) == ("unique", only),
    )
    grids = {
        engine.grid(asked(4, 2), random.Random(seed), time_limit=TIME_LIMIT)
        for seed in range(8)
    }
    check(
        f"{name}, 4x4, at least 2: every seed's grid is one of the two",
        {status for status, _ in grids} == {"found"}
        and {net for _, net in grids} <= TWO,
    )
    check(
        f"{name}, 4x4, at least 3: a seed's answer is infeasible",
        engine.grid(asked(4, 3), random.Random(0), time_limit=TIME_LIMIT)
        == ("infeasible", None),
    )


def test_larger_board(name, exactly, total):
    """5x5, which no brute force reaches: every grid with this piece-count
    condition, `total` of them, split by the reader's own count of banana
    regions. Each engine must keep exactly the grids with enough of them.
    Returns {N: the grids with N or more}."""
    every = hybrid_sat.listing(
        hybrid.Conditions(5, 5, exactly=exactly),
        hybrid_sat.LAZY,
        cap=total + 1,
        time_limit=TIME_LIMIT,
    )
    count = {net: len(hybrid.bananas(hybrid.values(net, 5, 5))) for net in every.grids}
    most = max(count.values())
    check(
        f"5x5, {name}: {total} grids, some with two banana regions or more "
        f"(the most: {most})",
        len(count) == total and not every.timed_out and most >= 2,
    )
    kept = {}
    for n in range(1, most + 2):
        want = kept[n] = {net for net in count if count[net] >= n}
        for connectivity in (hybrid_sat.LAZY, hybrid_sat.PROPAGATOR):
            got = hybrid_sat.listing(
                asked(5, n, exactly=exactly),
                connectivity,
                cap=len(want) + 1,
                time_limit=TIME_LIMIT,
            )
            check(
                f"{connectivity}, 5x5, {name}, at least {n}: the reader's "
                f"{len(want)} grids exactly, each once",
                not got.timed_out
                and set(got.grids) == want
                and len(got.grids) == len(want),
            )
        status, found = hybrid_finder.ENGINES["cpsat"].classify(
            asked(5, n, exactly=exactly), time_limit=TIME_LIMIT, workers=1
        )
        word = WORDS[min(len(want), 2)]
        check(
            f"cpsat, 5x5, {name}, at least {n}: {word}",
            status == word and (found in want or not want),
        )
    return kept


def test_blank_strip(name, engine):
    """The condition with the blank strip, where a grid exists: no 5x5 grid
    has the strip, so 6x6, which is not listed in full. Each seed's grid is
    held to the rule reader on the board with the strip, and some seed's
    grid with no condition has fewer banana regions than are asked for
    here, so the condition is what gave these."""
    plain = hybrid.Conditions(6, 6, blank_strip=True)
    fewer, passed = 0, 0
    for seed in range(4):
        _, net = engine.grid(plain, random.Random(seed), time_limit=TIME_LIMIT)
        fewer += len(hybrid.bananas(hybrid.values(net, 6, 6, True))) < 3
        status, net = engine.grid(
            asked(6, 3, blank_strip=True), random.Random(seed), time_limit=TIME_LIMIT
        )
        passed += status == "found" and not hybrid.failures(
            net, 6, 6, blank_strip=True, min_bananas=3
        )
    check(
        f"{name}, 6x6 with the blank strip, at least 3: the reader passes all "
        f"4 seeds' grids ({passed}); with no condition {fewer} of 4 had fewer",
        passed == 4 and fewer >= 1,
    )


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(FINDER), *args],
        capture_output=True,
        text=True,
        env=success_env(),
    )


def hunt(d, name, *flags, seeds=6):
    """Run a hunt with these flags; returns (the examples' records, the
    `empty` reasons, summary.json, run.json's config)."""
    out = Path(d) / name
    r = run_cli(
        *BOARD, *flags, "--out", str(out), f"--seeds=0:{seeds}", "--workers", "1"
    )
    check(f"{name}: the hunt exits 0 (stderr: {r.stderr[-500:]})", r.returncode == 0)
    progress = (out / "progress.jsonl").read_text().splitlines()
    return (
        [
            json.loads(line)
            for line in (out / "examples.jsonl").read_text().splitlines()
        ],
        [
            e.get("empty_reason")
            for e in map(json.loads, progress)
            if e.get("outcome") == "empty"
        ],
        json.loads((out / "summary.json").read_text()),
        json.loads((out / "run.json").read_text()).get("config"),
    )


def test_verify():
    """The finder's `verify`, the rule reader, on the condition."""
    reader = hybrid_finder.HybridFinder(hybrid.Conditions(4, 4))
    for net in TWO:
        check(
            "verify passes a grid with two banana regions asked for two",
            reader.verify(hybrid_finder.Candidate(asked(4, 2), net)).ok,
        )
    verdict = reader.verify(hybrid_finder.Candidate(asked(4, 2), ONE))
    check(
        f"verify rejects a grid with one, naming the count ({verdict.reason!r})",
        not verdict.ok
        and verdict.reason == "1 banana region, fewer than the 2 asked for",
    )
    record = reader.record(hybrid_finder.Candidate(asked(4, 2), ONE))
    check("the record carries the condition", record["min_bananas"] == 2)
    check(
        "a record read back asks for what it was found under, so verify rejects it",
        reader.candidate_from_record(record).conditions == asked(4, 2)
        and not reader.verify(reader.candidate_from_record(record)).ok,
    )
    for bad in (-3, True, None, "2", 2.0):
        try:
            reader.candidate_from_record({**record, "min_bananas": bad})
            said = "no refusal"
        except ValueError as e:
            said = str(e)
        check(
            f"a record whose min_bananas is {bad!r} is refused, by name ({said})",
            said == f"min_bananas is {bad!r}: it is a whole number, 0 or more",
        )
    del record["min_bananas"]
    check(
        "a record of a hunt from before the condition asks for none",
        reader.candidate_from_record(record).conditions.min_bananas == 0,
    )


def test_cli(engine, d):
    flags = ("--engine", engine)
    examples, _, summary, config = hunt(
        d, f"{engine} two", *flags, "--min-bananas", "2"
    )
    reader = hybrid_finder.HybridFinder(hybrid.Conditions(4, 4))
    nets = {reader.candidate_from_record(ex).network for ex in examples}
    # The two grids are each other's image in the main diagonal, which the
    # hunt dedupes under, so they are one example.
    check(
        f"{engine}, --min-bananas 2: one example, one of the two grids, the "
        f"other seeds its repeats, none rejected by verify ({len(nets)} found)",
        len(examples) == 1
        and nets <= TWO
        and summary["duplicates"] == 5
        and summary["rejected"] == 0,
    )
    check(
        f"{engine}, --min-bananas 2: run.json and every record carry it",
        config.get("min_bananas") == 2
        and all(ex.get("min_bananas") == 2 for ex in examples),
    )
    examples, _, _, _ = hunt(
        d, f"{engine} two, r2c4", *flags, "--min-bananas", "2", "--circles", "r2c4"
    )
    check(
        f"{engine}, --min-bananas 2 with r2c4 circled: one example, a grid "
        "with two banana regions and r2c4 a valid circle",
        len(examples) == 1
        and reader.candidate_from_record(examples[0]).network in TWO
        and not hybrid.why_not_hybrid(
            reader.candidate_from_record(examples[0]).network, 4, 4, R2C4
        ),
    )
    examples, empty, _, _ = hunt(
        d, f"{engine} three", *flags, "--min-bananas", "3", seeds=2
    )
    check(
        f"{engine}, --min-bananas 3: every seed says no grid meets the conditions",
        not examples and empty == ["infeasible: no grid meets the conditions"] * 2,
    )
    for more, want in (
        (("--min-bananas", "2", "--exactly", "2:cross:r2"), "infeasible: no grid"),
        (("--min-bananas", "2"), "not_unique: more than one grid"),
        (("--min-bananas", "3"), "infeasible: no grid"),
        (("--min-bananas", "2", "--circles", "r2c4"), "unique: exactly one grid"),
        (("--min-bananas", "2", "--blank-strip"), "infeasible: no grid"),
    ):
        r = run_cli(*BOARD, *flags, *more, "classify")
        check(
            f"{engine}, classify {' '.join(more)}: {want}",
            r.returncode == 0 and r.stdout.splitlines()[:1] == [want],
        )


def test_flag():
    for bad in ("0", "-1"):
        r = run_cli(*BOARD, "--min-bananas", bad, "classify")
        check(
            f"--min-bananas {bad} is refused, by name",
            r.returncode == 2
            and r.stderr.strip()
            == f"hybrid_finder: --min-bananas takes 1 or more, got {bad}",
        )
    for bad in ("0", "-1"):
        r = subprocess.run(
            [sys.executable, str(HERE / "brute.py"), "4", "4", "--min-bananas", bad],
            capture_output=True,
            text=True,
            env=success_env(),
        )
        check(
            f"brute.py --min-bananas {bad} is refused the same way",
            r.returncode == 2
            and r.stderr.splitlines()[-1:]
            == [f"brute.py: error: --min-bananas takes 1 or more, got {bad}"],
        )
    check(
        "the usage text names the condition",
        "--min-bananas N" in run_cli("--help").stdout,
    )


def test_timing():
    """`time_bananas.py`, the script behind the decision log's 7x7 table: a
    row says what the engine answered and what the rule reader makes of it,
    and the table counts a timeout as a timeout."""
    row = time_bananas.measure(4, 2, 0, "pysat-lazy", TIME_LIMIT)
    check(
        "a timing row for 4x4, at least 2: found, two banana regions, passed "
        "by the reader",
        (row["status"], row["bananas"], row["reader_ok"]) == ("found", 2, True)
        and row["seconds"] >= 0,
    )
    row = time_bananas.measure(4, 3, 0, "pysat-lazy", TIME_LIMIT)
    check(
        "a timing row for 4x4, at least 3: infeasible, no grid for the reader",
        (row["status"], row["bananas"], row["reader_ok"])
        == ("infeasible", None, False),
    )
    rows = [
        {"min_bananas": 0, "status": "found", "seconds": 1.0, "reader_ok": True},
        {"min_bananas": 5, "status": "found", "seconds": 2.0, "reader_ok": True},
        {"min_bananas": 5, "status": "found", "seconds": 4.0, "reader_ok": True},
        {"min_bananas": 5, "status": "timeout", "seconds": 60.0, "reader_ok": False},
        {"min_bananas": 9, "status": "timeout", "seconds": 60.0, "reader_ok": False},
    ]
    check(
        "the timing table: a timeout is in its own column and out of the times",
        time_bananas.report(rows)[2:]
        == [
            "| none | 1 | 1 | 0 | 1 | 1.000 | 1.000 | 1.000 |",
            "| 5 | 3 | 2 | 1 | 2 | 3.000 | 3.000 | 4.000 |",
            "| 9 | 1 | 0 | 1 | 0 | - | - | - |",
        ],
    )


if __name__ == "__main__":
    test_reader()
    test_brute()
    for name, engine in hybrid_finder.ENGINES.items():
        test_engine(name, engine)
        test_blank_strip(name, engine)
    test_larger_board("no piece count", None, 31)
    two_branches = network.Exactly.parse("2:branch:r1")
    kept = test_larger_board("2 branches in r1", two_branches, 8)
    check(
        "5x5, 2 branches in r1: 7 grids have two banana regions and one has "
        "six, so at least 3 leaves exactly one",
        [len(kept[n]) for n in sorted(kept)] == [8, 8, 1, 1, 1, 1, 0],
    )
    for name, engine in hybrid_finder.ENGINES.items():
        (only,) = kept[3]
        check(
            f"{name}, 5x5, 2 branches in r1 with at least 3: the one grid",
            engine.classify(
                asked(5, 3, exactly=two_branches), time_limit=TIME_LIMIT, workers=1
            )
            == ("unique", only),
        )
    test_verify()
    test_timing()
    test_flag()
    with tempfile.TemporaryDirectory() as d:
        for name in hybrid_finder.ENGINES:
            test_cli(name, d)
    sys.exit(0 if ok else 1)

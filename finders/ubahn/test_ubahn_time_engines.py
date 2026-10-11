"""The three-engine timing script (#786), black-box on a 4x4 board.

`run` must account for every seed exactly once under the 4x4 answers of the
decision log (§ Hybrid: the 4x4 answers), and `report` must put each solve in
the right column. No time is asserted: where a time column is read, the
seconds are written by hand in the test, so the number is arithmetic on a
tally. One worker; a few seconds in all.

    uv run finders/ubahn/test_ubahn_time_engines.py
"""

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hybrid
import time_engines
from hybrid_finder import ENGINES

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def circled(*names):
    return hybrid.Conditions(4, 4, frozenset(map(hybrid.parse_cell, names)))


# The 4x4 board has 18 grids with no condition and none with r1c1 circled.
OPEN = time_engines.Case("4x4", "grid", hybrid.Conditions(4, 4))
NO_GRID = time_engines.Case("4x4 r1c1", "grid", circled("r1c1"))

# c1:turn r2c4 circled has exactly one grid, r2c2 four.
ONE_GRID = time_engines.Case("4x4 one", "classify", circled("c1:turn", "r2c4"))
CLASSIFIED = {
    "infeasible": time_engines.Case("4x4 none", "classify", circled("r1c1")),
    "unique": ONE_GRID,
    "not_unique": time_engines.Case("4x4 four", "classify", circled("r2c2")),
}

for engine in ENGINES:
    ran = time_engines.run(engine, OPEN, range(3), timeout=60.0)
    check(
        f"{engine}: one solve per seed, in order",
        [s.seed for s in ran.solves] == [0, 1, 2],
    )
    check(
        f"{engine}: every seed of the open 4x4 finds a grid",
        [s.status for s in ran.solves] == ["found"] * 3,
    )
    check(
        f"{engine}: a run names its engine, case, call, seeds asked and limit",
        ran[:5] == (engine, "4x4", "grid", 3, 60.0) and not ran.capped,
    )
    check(
        f"{engine}: cuts and conflicts are counted on the PySAT engines only",
        all(
            (s.cuts is not None and s.conflicts is not None)
            == engine.startswith("pysat")
            for s in ran.solves
        ),
    )
    ran = time_engines.run(engine, NO_GRID, range(2), timeout=60.0)
    check(
        f"{engine}: r1c1 circled is proven to have no grid, each seed",
        [s.status for s in ran.solves] == ["infeasible"] * 2,
    )
    for word, case in CLASSIFIED.items():
        ran = time_engines.run(engine, case, range(2), timeout=60.0)
        check(
            f"{engine}: classify says {word}, each repeat",
            [s.status for s in ran.solves] == [word] * 2,
        )

    # A limit of zero is reached before any solve, in every engine.
    ran = time_engines.run(engine, OPEN, range(5), timeout=0.0, cap_after=5)
    check(
        f"{engine}: a solve the limit stopped is a timeout",
        [s.status for s in ran.solves] == ["timeout"] * 5,
    )
    check(f"{engine}: five timeouts of five asked is not a cap", not ran.capped)
    ran = time_engines.run(engine, OPEN, range(5), timeout=0.0, cap_after=2)
    check(
        f"{engine}: the case stops when its first 2 seeds all time out",
        [s.seed for s in ran.solves] == [0, 1] and ran.capped and ran.asked == 5,
    )

# The cap reads the first seeds only: a timeout after a found grid stops
# nothing. One engine is enough, the rule is the script's.
first = time_engines.run("pysat-lazy", OPEN, range(1), timeout=60.0)
progress = []
ran = time_engines.run(
    "pysat-lazy",
    OPEN,
    range(4),
    timeout=0.0,
    cap_after=2,
    done=first.solves,
    progress=progress.append,
)
check(
    "a seed already solved is kept and not solved again",
    ran.solves[0] == first.solves[0] and [s.seed for s in progress] == [1, 2, 3],
)
check(
    "timeouts after a found first seed are no cap",
    [s.status for s in ran.solves] == ["found"] + ["timeout"] * 3 and not ran.capped,
)
ran = time_engines.run(
    "pysat-lazy", OPEN, range(1, 4), timeout=60.0, cap_after=2, done=ran.solves[1:3]
)
check(
    "a rerun over two recorded timeouts is capped with no new solve",
    [s.seed for s in ran.solves] == [1, 2] and ran.capped,
)


def raises(fn, error):
    try:
        fn()
    except error:
        return True
    return False


# A found grid is re-read by the rule reader: an engine that returns a
# network breaking a rule stops the run.
real = ENGINES["cpsat"]


class Broken:
    @staticmethod
    def grid(conditions, rng, *, time_limit):
        return hybrid.Sampled("found", frozenset())


try:
    ENGINES["cpsat"] = Broken
    check(
        "a found grid the rule reader refuses stops the run",
        raises(
            lambda: time_engines.run("cpsat", OPEN, range(1), timeout=60.0),
            RuntimeError,
        ),
    )
finally:
    ENGINES["cpsat"] = real

# A tally, not a measurement: the report's own words, on seconds written
# here by hand.
Solve, Ran = time_engines.Solve, time_engines.Ran


def ran_of(engine, case, rows, *, call="grid", asked=None, capped=False):
    """A `Ran` of hand-written solves: each row is `(status, seconds)` or
    `(status, seconds, cuts, conflicts)`."""
    solves = tuple(Solve(engine, case, seed, *row) for seed, row in enumerate(rows))
    return Ran(engine, case, call, asked or len(solves), 60.0, solves, capped)


HEAD = (
    "| Case | Engine | Seeds | Found | Proven impossible | Timed out "
    "| Solves timed | Median ms | Mean ms | 90th ms | Max ms "
    "| Cuts | Conflicts |"
)
TALLY = [
    ran_of(
        "cpsat",
        "8x8",
        [("found", 0.125), ("found", 0.25), ("found", 0.5), ("timeout", 60.0)],
    ),
    ran_of(
        "pysat-lazy",
        "8x8",
        [("found", 0.0625, cuts, 0) for cuts in (1, 2, 3, 4)],
    ),
    ran_of(
        "pysat-propagator",
        "8x8",
        [("found", 0.0625, 1, 7), ("found", 0.0625, 1, 9)],
    ),
    ran_of("cpsat", "10x10", [("found", 0.5)] * 2),
    ran_of("pysat-lazy", "10x10", [("found", 0.25, 0, 0)] * 2),
    ran_of("pysat-propagator", "10x10", [("found", 0.3125, 0, 0)] * 2),
    ran_of("cpsat", "none", [("infeasible", 0.5)] * 3, call="classify"),
    ran_of(
        "pysat-lazy",
        "none",
        [("timeout", 60.0, 0, 0)] * 20,
        call="classify",
        asked=100,
        capped=True,
    ),
    ran_of(
        "pysat-propagator",
        "none",
        [("infeasible", 0.25, 0, 3)] * 2,
        call="classify",
        asked=100,
    ),
    ran_of("cpsat", "one", [("unique", 0.5)] * 2, call="classify"),
]
text = time_engines.report(TALLY)
check("report has the table's columns", HEAD in text)
for name, row in {
    "a timed-out solve is its own column, labelled capped, and left out of "
    "the time columns": "| 8x8 | cpsat | 4 | 3 | 0 | 1 (capped) "
    "| 3 | 250.0 | 291.7 | 500.0 | 500.0 | - | - |",
    "the lazy engine's cuts, added up over its timed solves": "| 8x8 | pysat-lazy | 4 | 4 | 0 | 0 "
    "| 4 | 62.5 | 62.5 | 62.5 | 62.5 | 10 | 0 |",
    "the propagator engine's conflicts": "| 8x8 | pysat-propagator | 2 | 2 | 0 "
    "| 0 | 2 | 62.5 | 62.5 | 62.5 | 62.5 | 2 | 16 |",
    "a proof of no grid is its own column": "| none | cpsat | 3 | 0 | 3 | 0 "
    "| 3 | 500.0 | 500.0 | 500.0 | 500.0 | - | - |",
    "a case the cap rule stopped says so, with no time": "| none | pysat-lazy "
    "| 20 of 100 (capped: first 20 seeds all timed out) | 0 | 0 | 20 (capped) "
    "| 0 | - | - | - | - | - | - |",
    "a case cut short says incomplete": "| none | pysat-propagator "
    "| 2 of 100 (incomplete) | 0 | 2 | 0 "
    "| 2 | 250.0 | 250.0 | 250.0 | 250.0 | 0 | 6 |",
    "a classify that found a grid keeps its word": "| one | cpsat | 2 "
    "| 2 (unique) | 0 | 0 | 2 | 500.0 | 500.0 | 500.0 | 500.0 | - | - |",
}.items():
    check(f"report: {name}", row in text)
check(
    "report rows keep the order the runs came in",
    text.index("| 8x8 | cpsat")
    < text.index("| 8x8 | pysat-lazy")
    < text.index("| 10x10 | cpsat")
    < text.index("| none | cpsat"),
)

# The reading against the bar: CP-SAT's median over the engine's, and at
# least 2 at both 8x8 and 10x10 to meet it.
for name, row in {
    "250 over 62.5 is 4 times, capped by the CP-SAT timeout": "| 8x8 "
    "| pysat-lazy | 250.0 | 62.5 | 4.00 (capped) |",
    "500 over 250 is 2 times": "| 10x10 | pysat-lazy | 500.0 | 250.0 | 2.00 |",
    "500 over 312.5 is 1.6 times": "| 10x10 | pysat-propagator | 500.0 "
    "| 312.5 | 1.60 |",
    "an engine with no timed solve has no ratio": "| none | pysat-lazy "
    "| 500.0 | - | unknown (capped) |",
}.items():
    check(f"bar: {name}", row in text)
check(
    "bar: exactly 2 times at 10x10 and 4 at 8x8 meets it, capped",
    "- `pysat-lazy` is at least 2 times faster than `cpsat` at 8x8 and "
    "10x10: yes (capped)" in text,
)
check(
    "bar: 1.6 times at 10x10 does not meet it",
    "- `pysat-propagator` is at least 2 times faster than `cpsat` at 8x8 "
    "and 10x10: no" in text,
)
without = time_engines.report([r for r in TALLY if r.case != "10x10"])
check(
    "bar: with no 10x10 run the reading is unknown, never yes",
    "- `pysat-lazy` is at least 2 times faster than `cpsat` at 8x8 and "
    "10x10: unknown" in without,
)
check("report names no disagreement when the engines agree", "disagree" not in text)
split = time_engines.report(
    [
        ran_of("cpsat", "7x7", [("infeasible", 0.5)]),
        ran_of("pysat-lazy", "7x7", [("found", 0.5, 0, 0), ("timeout", 60.0, 0, 0)]),
    ]
)
check(
    "report says so when one engine finds a grid another proves away",
    "**The engines disagree on 7x7**" in split,
)
agree = time_engines.report(
    [
        ran_of("cpsat", "7x7", [("infeasible", 0.5)]),
        ran_of("pysat-lazy", "7x7", [("timeout", 60.0, 0, 0)]),
    ]
)
check("a timeout disagrees with nothing", "disagree" not in agree)

# Chris's cases (spec #781): no condition at four sizes, and the example's
# four circles at 7x7 for a grid and for classify.
EXAMPLE = frozenset(
    map(hybrid.parse_cell, ("r6:straight", "r6:turn", "r7:straight", "r7:turn"))
)
check(
    "the cases are the spec's six",
    list(time_engines.CASES.values())
    == [
        time_engines.Case("6x6", "grid", hybrid.Conditions(6, 6)),
        time_engines.Case("7x7", "grid", hybrid.Conditions(7, 7)),
        time_engines.Case("8x8", "grid", hybrid.Conditions(8, 8)),
        time_engines.Case("10x10", "grid", hybrid.Conditions(10, 10)),
        time_engines.Case(
            "7x7 example, grid", "grid", hybrid.Conditions(7, 7, EXAMPLE)
        ),
        time_engines.Case(
            "7x7 example, classify", "classify", hybrid.Conditions(7, 7, EXAMPLE)
        ),
    ]
    and list(time_engines.CASES) == [c.name for c in time_engines.CASES.values()],
)
check(
    "the cap is 20 seeds and the bar 2 times at 8x8 and 10x10",
    (time_engines.CAP_AFTER, time_engines.BAR, time_engines.BAR_CASES)
    == (20, 2, ("8x8", "10x10")),
)


def cli(*argv):
    """`main`'s exit code and what it printed; its progress lines and
    argparse's usage message are kept off the test's output."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = time_engines.main(list(argv))
        except SystemExit as e:
            code = e.code
    return code, out.getvalue()


def solve_lines(path):
    return sum('"solve"' in line for line in path.read_text().splitlines())


with tempfile.TemporaryDirectory() as tmp:
    lazy, cpsat = Path(tmp) / "lazy.jsonl", Path(tmp) / "cpsat.jsonl"
    run_lazy = ("run", "--engine", "pysat-lazy", "--progress", str(lazy))
    code, _ = cli(*run_lazy, "--case", "6x6", "--seeds", "0:2")
    check(
        "run: two seeds of 6x6 exit 0, a line per solve",
        code == 0 and solve_lines(lazy) == 2,
    )
    code, text = cli("report", str(lazy))
    check(
        "report: reads the progress file",
        code == 0 and "| 6x6 | pysat-lazy | 2 | 2 | 0 | 0 | 2 |" in text,
    )
    code, _ = cli(*run_lazy, "--case", "6x6", "--seeds", "0:3")
    check("run again: only the new seed is solved", solve_lines(lazy) == 3)
    _, text = cli("report", str(lazy))
    check(
        "report: the rerun is one row of three seeds",
        "| 6x6 | pysat-lazy | 3 | 3 | 0 | 0 | 3 |" in text
        and text.count("| 6x6 |") == 1,
    )
    code, _ = cli(*run_lazy, "--case", "6x6", "--seeds", "0:3", "--timeout", "5")
    check(
        "run: a file that holds the case at another limit is refused",
        code == 2 and solve_lines(lazy) == 3,
    )

    # A limit of zero times out every seed: the cap rule stops at 20.
    run_cpsat = ("run", "--engine", "cpsat", "--progress", str(cpsat))
    capped = (*run_cpsat, "--case", "8x8", "--seeds", "0:25", "--timeout", "0")
    code, _ = cli(*capped)
    check(
        "run: a capped case exits 0 after 20 solves",
        code == 0 and solve_lines(cpsat) == 20,
    )
    cli(*capped)
    check("run again: a capped case solves nothing more", solve_lines(cpsat) == 20)
    _, text = cli("report", str(lazy), str(cpsat))
    check(
        "report: two files are one table, the capped case labelled",
        "| 6x6 | pysat-lazy | 3 |" in text
        and "| 8x8 | cpsat | 20 of 25 (capped: first 20 seeds all timed out) "
        "| 0 | 0 | 20 (capped) | 0 |"
        in text,
    )

    # A run that dies leaves every case it was asked for in the file: the
    # one it never reached reads as incomplete, not as absent.
    died = Path(tmp) / "died.jsonl"
    real = ENGINES["pysat-lazy"]

    class Dies(type(real)):
        def grid_listing(self, conditions, rng, *, time_limit):
            if conditions.rows == 7:
                raise KeyboardInterrupt
            return super().grid_listing(conditions, rng, time_limit=time_limit)

    try:
        ENGINES["pysat-lazy"] = Dies(real.connectivity)
        with contextlib.suppress(KeyboardInterrupt):
            cli(
                "run",
                "--engine",
                "pysat-lazy",
                "--progress",
                str(died),
                "--case",
                "6x6",
                "--case",
                "7x7",
                "--case",
                "8x8",
                "--seeds",
                "0:2",
            )
    finally:
        ENGINES["pysat-lazy"] = real
    _, text = cli("report", str(died))
    check(
        "report: a killed run's cases are incomplete, the reached one kept",
        "| 6x6 | pysat-lazy | 2 | 2 |" in text
        and "| 7x7 | pysat-lazy | 0 of 2 (incomplete) | 0 | 0 | 0 | 0 |" in text
        and "| 8x8 | pysat-lazy | 0 of 2 (incomplete) |" in text,
    )

    for bad in (
        ("--case", "6x6", "--seeds", "5:5"),
        ("--case", "6x6", "--seeds", "x:3"),
        ("--case", "9x9"),
    ):
        code, _ = cli(*run_lazy, *bad)
        check(f"run: {' '.join(bad)} is refused", code == 2)
    code, _ = cli("run", "--engine", "clingo", "--progress", str(lazy))
    check("run: an unknown engine is refused", code == 2)
    check("the refusals solved nothing", solve_lines(lazy) == 3)


def progress_file(path, *lines):
    path.write_text("".join(json.dumps(line) + "\n" for line in lines))
    return str(path)


def asked(engine, count, case="8x8"):
    return {
        "asked": {
            "engine": engine,
            "case": case,
            "call": "grid",
            "asked": count,
            "timeout": 60.0,
        }
    }


def solved(engine, seed, status, seconds, case="8x8"):
    return {
        "solve": {
            "engine": engine,
            "case": case,
            "seed": seed,
            "status": status,
            "seconds": seconds,
        }
    }


# Hand-written progress files, no solver: a second run over other seeds.
with tempfile.TemporaryDirectory() as tmp:
    base = [asked("cpsat", 4, case) for case in ("8x8", "10x10")] + [
        solved("cpsat", seed, "found", 1.0, case)
        for case in ("8x8", "10x10")
        for seed in range(4)
    ]
    twice = []
    for case in ("8x8", "10x10"):
        twice += [
            asked("pysat-lazy", 2, case),
            solved("pysat-lazy", 0, "found", 0.1, case),
            solved("pysat-lazy", 1, "found", 0.1, case),
            asked("pysat-lazy", 2, case),
            solved("pysat-lazy", 2, "timeout", 60.0, case),
            solved("pysat-lazy", 3, "timeout", 60.0, case),
        ]
    _, text = cli(
        "report",
        progress_file(Path(tmp) / "cpsat.jsonl", *base),
        progress_file(Path(tmp) / "lazy.jsonl", *twice),
    )
    check(
        "report: a second run over other seeds counts every seed on file "
        "(4 seeds, 2 found, 2 timed out)",
        "| 8x8 | pysat-lazy | 4 | 2 | 0 | 2 (capped) | 2 |" in text,
    )
    check(
        "report: its timeouts label the ratio and the verdict capped",
        "| 8x8 | pysat-lazy | 1000.0 | 100.0 | 10.00 (capped) |" in text
        and "- `pysat-lazy` is at least 2 times faster than `cpsat` at 8x8 and "
        "10x10: yes (capped)"
        in text,
    )

    shrunk = progress_file(
        Path(tmp) / "shrunk.jsonl",
        asked("cpsat", 25),
        *(solved("cpsat", seed, "timeout", 60.0) for seed in range(20)),
        {"capped": {"engine": "cpsat", "case": "8x8"}},
        asked("cpsat", 20),
    )
    _, text = cli("report", shrunk)
    check(
        "report: a cap does not outlive a run that asks for no more seeds "
        "than were solved",
        "| 8x8 | cpsat | 20 | 0 | 0 | 20 (capped) |" in text and "20 of 20" not in text,
    )

    odd = progress_file(
        Path(tmp) / "odd.jsonl",
        asked("cpsat", 1),
        {"stopped": {"engine": "cpsat", "case": "8x8"}},
    )
    code, text = cli("report", odd)
    check(
        "report: a line of an unknown kind is refused, never read as a cap",
        code == 2 and "| 8x8 |" not in text,
    )

sys.exit(0 if ok else 1)

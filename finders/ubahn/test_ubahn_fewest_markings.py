"""The hybrid finder's `fewest-markings` (spec #29, #30), black-box on the
4x4 board, on each PySAT engine.

`fewest-markings` classifies every set of Battenberg markings of one size
under the negative constraint before any set of the next size, and stops at
the first size with a set that leaves exactly one grid. Under the negative
constraint a grid meets a set of markings exactly when the set is its
checkerboard windows, so the brute force's 18 grids give every answer here
with no solver: the minimum, the unique sets of that size and each size's
counts. Then the examples it writes, a rerun of a stopped run, a time limit
reached, the size cap, mirror sets, the workers and the refusals.

One CaDiCaL thread, but for the two-worker run; about a minute.

    uv run finders/ubahn/test_ubahn_fewest_markings.py
"""

import fcntl
import json
import math
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import brute
import hybrid
import hybrid_finder
import network
from subprocess_env import success_env
from verified_io import read_verified

FINDER = HERE / "hybrid_finder.py"
ENGINES = ("pysat-lazy", "pysat-propagator")
BOARD = ["--rows", "4", "--cols", "4", "--timeout", "20"]
# A 4x4 board's windows (decision log, § Hybrid: Battenberg markings, the 4x4
# answers).
WINDOWS = 33
WORDS = ("unique", "not_unique", "infeasible", "timeout")
# A record carries its own board and conditions.
READER = hybrid_finder.HybridFinder(hybrid.Conditions(4, 4))

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(FINDER), *map(str, args)],
        capture_output=True,
        text=True,
        env=success_env(),
    )


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def sets_tried(out):
    """The lines of the per-set file, its heading line left out."""
    return read_jsonl(out / "sets.jsonl")[1:]


def names(windows):
    """A set of windows, each by its name, whatever order a line gives them."""
    return frozenset(windows)


def mirror(windows):
    """A set of window names reflected in the main diagonal."""
    return names(hybrid.cell_name((c, r)) for r, c in map(hybrid.parse_cell, windows))


def by_brute(keep=lambda net: True):
    """{a set of window names: the grids whose checkerboard windows are
    exactly that set}, over the brute force's 4x4 grids that `keep` takes:
    the grids each set of markings leaves under the negative constraint."""
    held = {}
    for net in brute.hybrid_grids(4, 4):
        if keep(net):
            windows = hybrid.checkerboard_windows(hybrid.values(net, 4, 4))
            held.setdefault(names(map(hybrid.cell_name, windows)), []).append(net)
    return held


def counts(held, size):
    """The brute force's count of each answer word over the sets of one
    size."""
    grids = [len(nets) for windows, nets in held.items() if len(windows) == size]
    unique = sum(1 for n in grids if n == 1)
    return {
        "unique": unique,
        "not_unique": len(grids) - unique,
        "infeasible": math.comb(WINDOWS, size) - len(grids),
        "timeout": 0,
    }


def size_line(size, said):
    return f"size {size}: " + ", ".join(f"{said[word]} {word}" for word in WORDS)


def report(result, out):
    """A run's output with its own directory's name taken out, so two runs
    into two directories can be compared."""
    return result.stdout.replace(str(out), "DIR")


def directory(windows):
    """The name of a set's hunt directory under the run's own."""
    return "+".join(name.replace(":", "-") for name in windows)


def subdirectories(out):
    return sorted(p.name for p in out.iterdir() if p.is_dir())


HELD = by_brute()
MINIMUM = min(len(windows) for windows, nets in HELD.items() if len(nets) == 1)
SMALLEST = {
    windows: nets[0]
    for windows, nets in HELD.items()
    if len(windows) == MINIMUM and len(nets) == 1
}
check(
    f"the brute force has an answer to test against: a minimum of {MINIMUM} "
    f"with {len(SMALLEST)} unique sets, above size 1",
    MINIMUM > 1 and SMALLEST,
)

finished = {}
with tempfile.TemporaryDirectory() as d:
    for engine in ENGINES:
        out = Path(d) / engine
        r = run_cli("fewest-markings", *BOARD, "--engine", engine, "--out", out)
        finished[engine] = r
        lines = r.stdout.splitlines()
        check(
            f"{engine}: fewest-markings exits 0 (stderr: {r.stderr[-500:]})",
            r.returncode == 0,
        )
        want = [size_line(k, counts(HELD, k)) for k in range(MINIMUM + 1)]
        check(
            f"{engine}: each size's counts are the brute force's, and no size "
            f"past the minimum is tried ({lines[: MINIMUM + 2]})",
            lines[: MINIMUM + 1] == want
            and not any(line.startswith("size ") for line in lines[MINIMUM + 1 :]),
        )
        check(
            f"{engine}: the minimum is the brute force's {MINIMUM}, called "
            f"proven, the engine named ({lines[MINIMUM + 1 : MINIMUM + 2]})",
            lines[MINIMUM + 1 : MINIMUM + 2]
            == [
                f"minimum {MINIMUM}: proven on {engine}, {len(SMALLEST)} unique "
                f"sets of {MINIMUM} markings"
            ],
        )
        tried = sets_tried(out)
        found = {
            names(line["windows"]): line for line in tried if line["status"] == "unique"
        }
        check(
            f"{engine}: the unique sets are exactly the brute force's "
            f"({sorted(map(sorted, found))})",
            set(found) == set(SMALLEST),
        )
        check(
            f"{engine}: every set of every size up to the minimum has one line",
            Counter(line["size"] for line in tried)
            == {k: math.comb(WINDOWS, k) for k in range(MINIMUM + 1)}
            and len({names(line["windows"]) for line in tried}) == len(tried),
        )

        # Mirror sets: 4x4 with no other condition keeps the reflection in
        # the main diagonal, so one set of each mirror pair is solved and the
        # other is copied from it, each naming the other.
        line_of = {names(line["windows"]): line for line in tried}
        pairs = [
            (line, line_of[mirror(line["windows"])])
            for line in tried
            if mirror(line["windows"]) != names(line["windows"])
        ]
        check(
            f"{engine}: of each mirror pair one set was solved and the other "
            f"copied, with the same answer, each naming the other "
            f"({len(pairs) // 2} pairs)",
            len(pairs) > 2000
            and all(
                {a["how"], b["how"]} == {"solved", "mirror"}
                and a["status"] == b["status"]
                and names(a["mirror"]) == names(b["windows"])
                for a, b in pairs
            ),
        )
        own = [
            line for line in tried if mirror(line["windows"]) == names(line["windows"])
        ]
        check(
            f"{engine}: a set that is its own mirror is solved and names no "
            f"mirror ({len(own)} sets)",
            len(own) > 1
            and all(line["how"] == "solved" and line["mirror"] is None for line in own),
        )

        # The examples: one hunt directory per unique set, which `verify`,
        # `render` and `links` read.
        listed = [line for line in lines if line.startswith("unique: ")]
        want = {
            f"unique: {' '.join(line['windows'])}, mirror "
            f"{' '.join(line['mirror'])}: {out / directory(line['windows'])} (seed 0)"
            for line in found.values()
        }
        check(
            f"{engine}: the report lists each unique set with its mirror and "
            f"its hunt directory, and nothing else is in DIR ({listed})",
            len(listed) == len(SMALLEST)
            and set(listed) == want
            and subdirectories(out)
            == sorted(directory(line["windows"]) for line in found.values()),
        )
        for name in subdirectories(out):
            example = out / name
            (record,) = read_jsonl(example / "examples.jsonl")
            marked = names(record["battenberg"])
            r = run_cli("verify", example)
            verdicts = read_verified(example / "verified.jsonl")[1]
            check(
                f"{engine}, {name}: the example passes `verify` "
                f"(stderr: {r.stderr[-300:]})",
                r.returncode == 0 and [v["ok"] for v in verdicts] == [True],
            )
            check(
                f"{engine}, {name}: its record's checkerboard windows are "
                f"exactly its markings, a unique set, under the negative "
                f"constraint ({sorted(marked)})",
                marked in SMALLEST
                and names(record["checkerboard_windows"]) == marked
                and len(record["checkerboard_windows"]) == len(marked)
                and record["battenberg_only"] is True,
            )
            check(
                f"{engine}, {name}: its grid is the brute force's one grid for "
                f"that set",
                READER.candidate_from_record(record).network == SMALLEST.get(marked),
            )
            r = run_cli("render", example)
            r2 = run_cli(
                "links", example, "--battenberg", " ".join(sorted(marked)),
                "--battenberg-only",
            )  # fmt: skip
            check(
                f"{engine}, {name}: `render` and `links` read the directory "
                f"({r.stderr[-200:]}{r2.stderr[-200:]})",
                r.returncode == 0
                and r2.returncode == 0
                and (example / "renders" / "0.png").is_file()
                and (example / "links" / "0.txt").is_file(),
            )

    # A run stopped partway and started again: the per-set file of the
    # finished run cut off inside the last size, as a killed run leaves it.
    engine = ENGINES[0]
    done = Path(d) / engine
    whole = (done / "sets.jsonl").read_text().splitlines(keepends=True)
    # A set and its mirror are one write, so the cut falls before a solved set.
    cut = next(
        i
        for i in range(len(whole) - 800, len(whole))
        if json.loads(whole[i])["how"] == "solved"
    )
    for label, kept in (("inside the last size", cut), ("at once", 1)):
        again = Path(d) / f"again {label}"
        again.mkdir()
        (again / "sets.jsonl").write_text("".join(whole[:kept]))
        r = run_cli("fewest-markings", *BOARD, "--engine", engine, "--out", again)
        after = (again / "sets.jsonl").read_text().splitlines(keepends=True)
        check(
            f"a run stopped {label} and started again exits 0 and ends with "
            f"the same report (stderr: {r.stderr[-300:]})",
            r.returncode == 0 and report(r, again) == report(finished[engine], done),
        )
        tried = [json.loads(line) for line in after[1:]]
        check(
            f"stopped {label}: the lines on file are kept as they were and no "
            f"set is solved twice ({len(after) - kept} lines added)",
            after[:kept] == whole[:kept]
            and len(after) == len(whole)
            and len({names(line["windows"]) for line in tried}) == len(tried),
        )
    r = run_cli("fewest-markings", *BOARD, "--engine", engine, "--out", done)
    check(
        "a rerun into a finished directory: the same report, no line added",
        r.returncode == 0
        and r.stdout == finished[engine].stdout
        and (done / "sets.jsonl").read_text() == "".join(whole),
    )

    # Another run is in the directory: this one starts nothing.
    with (done / "sets.jsonl").open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        r = run_cli("fewest-markings", *BOARD, "--engine", engine, "--out", done)
    check(
        f"a run into a directory another run holds is refused "
        f"({r.stderr.strip()[-60:]!r})",
        r.returncode == 2 and "another run" in r.stderr and not r.stdout,
    )
    for flags, why in (
        (["--rows", 4, "--cols", 4, "--timeout", 5], "another time limit"),
        ([*BOARD, "--circles", "r2c4"], "another condition"),
        ([*BOARD, "--engine", ENGINES[1]], "another engine"),
    ):
        r = run_cli("fewest-markings", *flags, "--out", done)
        check(
            f"a run into a directory {why} wrote is refused "
            f"({r.stderr.strip()[:70]!r})",
            r.returncode == 2
            and "holds a run under" in r.stderr
            and not r.stdout
            and (done / "sets.jsonl").read_text() == "".join(whole),
        )

    # A set that reached the time limit below the answer's size: the set is
    # named and the minimum is not called proven. The finished run's file,
    # with one single marking's answer (and its mirror's) read as a timeout.
    stopped = Path(d) / "stopped below"
    stopped.mkdir()
    first = next(
        i for i, line in enumerate(whole) if i and json.loads(line)["size"] == 1
    )
    pair = [json.loads(line) for line in whole[first : first + 2]]
    timed = {names(line["windows"]) for line in pair}
    (stopped / "sets.jsonl").write_text(
        "".join(
            json.dumps({**json.loads(line), "status": "timeout"}) + "\n"
            if first <= i < first + 2
            else line
            for i, line in enumerate(whole)
        )
    )
    r = run_cli("fewest-markings", *BOARD, "--engine", engine, "--out", stopped)
    lines = r.stdout.splitlines()
    check(
        f"a single marking that timed out, and its mirror: both are named in "
        f"the report ({[line for line in lines if 'time limit' in line][:3]})",
        r.returncode == 0
        and pair[0]["mirror"] == pair[1]["windows"]
        and len(timed) == 2
        and all(
            f"time limit reached: {' '.join(line['windows'])}" in lines for line in pair
        )
        and size_line(1, {**counts(HELD, 1), "infeasible": WINDOWS - 2, "timeout": 2})
        in lines,
    )
    check(
        f"and the minimum is not called proven "
        f"({[line for line in lines if 'proven' in line]})",
        not any(line.startswith("minimum") for line in lines)
        and f"smallest found {MINIMUM}: not proven on {engine}, 2 sets of "
        f"{MINIMUM} or fewer markings reached the time limit"
        in lines
        and len([line for line in lines if line.startswith("unique: ")])
        == len(SMALLEST),
    )

    # A time limit too short for any set: every set is named as timed out,
    # none is read as "no grid", and nothing is proven.
    out = Path(d) / "no time"
    r = run_cli(
        "fewest-markings", "--rows", 4, "--cols", 4, "--timeout", 0,
        "--max-size", 1, "--out", out,
    )  # fmt: skip
    lines = r.stdout.splitlines()
    tried = sets_tried(out)
    check(
        f"a zero time limit: every set is a timeout, each named, and no "
        f"unique set is claimed up to the cap, not proven ({lines[-1:]})",
        r.returncode == 0
        and {line["status"] for line in tried} == {"timeout"}
        and len(tried) == 1 + WINDOWS
        and "time limit reached: no markings" in lines
        and all(
            f"time limit reached: {' '.join(line['windows'])}" in lines
            for line in tried
            if line["windows"]
        )
        and lines[-1]
        == f"no unique set found up to 1 on pysat-lazy: not proven, "
        f"{1 + WINDOWS} sets reached the time limit"
        and not subdirectories(out),
    )

    # The size cap, below the minimum.
    out = Path(d) / "capped"
    r = run_cli("fewest-markings", *BOARD, "--max-size", MINIMUM - 1, "--out", out)
    capped = r.stdout
    check(
        f"--max-size {MINIMUM - 1}, below the minimum: 'no unique set up to "
        f"{MINIMUM - 1}', exit 0 and no example ({r.stdout.splitlines()[-1:]})",
        r.returncode == 0
        and r.stdout.splitlines()
        == [
            *(size_line(k, counts(HELD, k)) for k in range(MINIMUM)),
            f"no unique set up to {MINIMUM - 1} on pysat-lazy",
        ]
        and not subdirectories(out),
    )

    # Two workers: the same report and the same answers, set for set.
    two = Path(d) / "two workers"
    r = run_cli(
        "fewest-markings", *BOARD, "--max-size", MINIMUM - 1, "--workers", 2,
        "--out", two,
    )  # fmt: skip

    def answers(directory):
        return sorted(
            (sorted(line["windows"]), line["status"], line["how"])
            for line in sets_tried(directory)
        )

    check(
        f"--workers 2: the same report as one worker, and the same answer on "
        f"file for every set (stderr: {r.stderr[-300:]})",
        r.returncode == 0 and r.stdout == capped and answers(two) == answers(out),
    )

    # A condition that breaks the reflection: r2c4 circled, whose image r4c2
    # is not. Every set is solved, none copied.
    def circled(net):
        return not hybrid.why_not_hybrid(net, 4, 4, [hybrid.parse_cell("r2c4")])

    out = Path(d) / "a circle"
    r = run_cli(
        "fewest-markings", *BOARD, "--circles", "r2c4", "--max-size", 1, "--out", out
    )
    tried = sets_tried(out)
    check(
        f"with r2c4 circled every set is solved and none names a mirror, and "
        f"the counts are the brute force's under the circle "
        f"({r.stdout.splitlines()[:2]})",
        r.returncode == 0
        and len(tried) == 1 + WINDOWS
        and all(line["how"] == "solved" and line["mirror"] is None for line in tried)
        and r.stdout.splitlines()[:2]
        == [size_line(k, counts(by_brute(circled), k)) for k in (0, 1)],
    )

    # A condition as fixed background, and a minimum of 0: with exactly 4
    # branches in row 2 one grid has no checkerboard window.
    exactly = network.Exactly.parse("4:branch:r2")
    held = by_brute(lambda net: exactly.holds(net, 4, 4))
    out = Path(d) / "exactly"
    r = run_cli("fewest-markings", *BOARD, "--exactly", exactly.text(), "--out", out)
    lines = r.stdout.splitlines()
    check(
        f"with {exactly.text()} the brute force has one grid with no "
        f"checkerboard window, and the command reports a minimum of 0 ({lines})",
        len(held[frozenset()]) == 1
        and r.returncode == 0
        and lines[:2]
        == [
            size_line(0, counts(held, 0)),
            "minimum 0: proven on pysat-lazy, 1 unique set of 0 markings",
        ]
        and lines[2:] == [f"unique: no markings: {out / 'no-markings'} (seed 0)"],
    )
    (record,) = read_jsonl(out / "no-markings" / "examples.jsonl")
    check(
        "its example carries the condition and the negative constraint, has no "
        "checkerboard window, and is the brute force's grid",
        record["exactly"] == exactly.text()
        and record["battenberg_only"] is True
        and record["battenberg"] == record["checkerboard_windows"] == []
        and READER.candidate_from_record(record).network == held[frozenset()][0]
        and run_cli("verify", out / "no-markings").returncode == 0,
    )

    # Refused before any solve, and before anything is written.
    unused = Path(d) / "unused"
    for flags, named in (
        (["--engine", "cpsat"], "--engine cpsat"),
        (["--battenberg", "c1:turn"], "--battenberg"),
        (["--max-size", -1], "--max-size"),
        (["--workers", 0], "--workers"),
    ):
        r = run_cli("fewest-markings", *BOARD, *flags, "--out", unused)
        check(
            f"fewest-markings {flags[0]} {flags[1]} is refused, exit 2, naming "
            f"the flag ({r.stderr.strip()!r})",
            r.returncode == 2
            and f"hybrid_finder fewest-markings: {named}" in r.stderr
            and not r.stdout
            and not unused.exists(),
        )

r = run_cli("--help")
check(
    "--help describes fewest-markings and its flags",
    r.returncode == 0
    and all(
        word in r.stdout
        for word in ("fewest-markings", "--max-size K", "--workers N", "sets.jsonl")
    ),
)

sys.exit(0 if ok else 1)

"""The hybrid finder's `--number-circles K` and its `climb` (#794), black-box
on the 4x4 board.

`--number-circles K` asks for at least K valid circles on number cells;
`climb` raises K until no grid reaches it or the time limit stops it. The
brute force's 18 grids hold 2 such cells at most (`test_ubahn_number_circles.py`),
so every example at K=2 is one of its 6, K=3 has no grid, and `climb` must
report a maximum of 2, proven, on every engine. About twenty seconds.

    uv run finders/ubahn/test_ubahn_number_circles_hunt.py
"""

import itertools
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import brute
import hunt_files
import hybrid
import hybrid_engines
from cli_checks import check, finish, read_jsonl, run_cli


def logged(out):
    """The steps of `out/climb.jsonl`, the run log's heading left out."""
    return read_jsonl(out / "climb.jsonl")[1:]


def write_log(out, steps, config):
    """A climb log as a run leaves it: the heading, then `steps`."""
    (out / "climb.jsonl").write_text(
        "".join(
            json.dumps(line) + "\n"
            for line in [{hunt_files.CONFIG_KEY: config}, *steps]
        )
    )


FINDER = HERE / "hybrid_finder.py"
BOARD = ["--rows", "4", "--cols", "4", "--timeout", "20"]
MOST = 2
READER = hybrid_engines.HybridFinder(hybrid.Conditions(4, 4))


def on_numbers(net):
    cells = hybrid.valid_circles(hybrid.values(net, 4, 4))
    return sum(1 for r, c in cells if r < 0 or c < 0)


WANT = {net for net in brute.hybrid_grids(4, 4) if on_numbers(net) >= MOST}

with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "at least 2"
    r = run_cli(FINDER, *BOARD, "--number-circles", MOST, "--out", out, "--seeds=0:20")
    check(f"at least {MOST}: the hunt exits 0 ({r.stderr[-300:]})", r.returncode == 0)
    examples = read_jsonl(out / "examples.jsonl")
    nets = [READER.candidate_from_record(ex).network for ex in examples]
    check(
        f"at least {MOST}: every example is one of the brute force's "
        f"{len(WANT)}, each once ({len(nets)})",
        nets and set(nets) <= WANT and len(set(nets)) == len(nets),
    )
    check(
        "every record carries the condition and names the number cells that "
        "are valid circles",
        all(
            ex["number_circles"] == MOST and len(ex["number_cell_circles"]) == MOST
            for ex in examples
        ),
    )
    config = json.loads((out / "run.json").read_text())["config"]
    check("run.json records the condition", config["number_circles"] == MOST)

    r = run_cli(FINDER, "verify", out)
    verdicts = read_jsonl(out / "verified.jsonl")[1:]
    check(
        "verify takes every example of the hunt",
        r.returncode == 0
        and len(verdicts) == len(examples)
        and all(v["ok"] for v in verdicts),
    )
    (out / "examples.jsonl").write_text(
        "".join(
            json.dumps({**ex, "number_circles": MOST + 1}) + "\n" for ex in examples
        )
    )
    r = run_cli(FINDER, "verify", out)
    verdicts = read_jsonl(out / "verified.jsonl")[1:]
    reason = f"{MOST} valid circles on number cells, fewer than {MOST + 1}"
    check(
        f"verify rejects every one of them at {MOST + 1} ({reason})",
        r.returncode == 0
        and len(verdicts) == len(examples) > 0
        and all(not v["ok"] and v["reason"] == reason for v in verdicts),
    )

    out = Path(d) / "at least 3"
    r = run_cli(
        FINDER, *BOARD, "--number-circles", MOST + 1, "--out", out, "--seeds=0:3"
    )
    reasons = [e.get("empty_reason") for e in read_jsonl(out / "progress.jsonl")]
    check(
        f"at least {MOST + 1}: no example, three seeds empty as infeasible ({reasons})",
        r.returncode == 0
        and not read_jsonl(out / "examples.jsonl")
        and len(reasons) == 3
        and all(reason and "infeasible" in reason for reason in reasons),
    )

    for k, line in ((MOST, "not_unique: more than one grid"), (MOST + 1, "infeasible: no grid")):  # fmt: skip
        r = run_cli(FINDER, "classify", *BOARD, "--number-circles", k)
        check(
            f"classify at least {k}: {line} ({r.stdout.splitlines()[:1]})",
            r.returncode == 0 and r.stdout.splitlines()[:1] == [line],
        )

    old = Path(d) / "old"
    run_cli(FINDER, *BOARD, "--out", old, "--seeds=0:2")
    (old / "examples.jsonl").write_text(
        "".join(
            json.dumps({k: v for k, v in ex.items() if "number" not in k or k == "numbers"})
            + "\n"
            for ex in read_jsonl(old / "examples.jsonl")
        )
    )  # fmt: skip
    r = run_cli(FINDER, "verify", old)
    old_verdicts = read_jsonl(old / "verified.jsonl")[1:]
    check(
        f"verify still reads a record with no number_circles ({r.stderr[-200:]})",
        r.returncode == 0
        and len(old_verdicts) == len(read_jsonl(old / "examples.jsonl")) > 0
        and all(v["ok"] for v in old_verdicts),
    )

    for engine in hybrid_engines.ENGINES:
        out = Path(d) / f"climb {engine}"
        r = run_cli(FINDER, "climb", *BOARD, "--engine", engine, "--out", out)
        lines = r.stdout.splitlines()
        check(
            f"climb on {engine}: maximum {MOST}, proven, and the engine named "
            f"({lines[-2:]}, stderr: {r.stderr[-300:]})",
            r.returncode == 0
            and lines[-2:-1]
            == [f"maximum {MOST}: proven on {engine}, at least {MOST + 1} has no grid"],
        )
        steps = logged(out)
        check(
            f"climb on {engine}: climb.jsonl holds each step, the last one "
            f"infeasible at {MOST + 1} ({[(s['at_least'], s['status']) for s in steps]})",
            steps[0]["at_least"] == 0
            and all(s["status"] == "found" for s in steps[:-1])
            and all(
                later["at_least"] == earlier["count"] + 1
                for earlier, later in itertools.pairwise(steps)
            )
            and (steps[-1]["at_least"], steps[-1]["status"])
            == (MOST + 1, "infeasible"),
        )  # fmt: skip
        best = out / steps[-2]["dir"]
        (net,) = [
            READER.candidate_from_record(ex).network
            for ex in read_jsonl(best / "examples.jsonl")
        ]
        check(
            f"climb on {engine}: the best grid is kept as a hunt directory, "
            f"named on the last line, and holds {MOST} by this test's count",
            net in WANT
            and steps[-2]["count"] == MOST
            and lines[-1] == f"best grid: {best} (seed 0)",
        )
        check(
            f"climb on {engine}: `verify` and `render` read that directory",
            run_cli(FINDER, "verify", best).returncode == 0
            and run_cli(FINDER, "render", best).returncode == 0
            and (best / "renders" / "0.png").is_file(),
        )

    r2 = run_cli(FINDER, "climb", *BOARD, "--engine", engine, "--out", out)
    check(
        "climb rerun into a finished directory: the same answer, no step added",
        r2.returncode == 0
        and r2.stdout.splitlines()[-2:] == lines[-2:]
        and logged(out) == steps,
    )

    r2 = run_cli(
        FINDER, "climb", "--rows", 4, "--cols", 4, "--timeout", 5, "--out", out
    )
    check(
        f"climb into a directory another time limit wrote is refused "
        f"({r2.stderr.strip()[:60]!r})",
        r2.returncode == 2 and "another config" in r2.stderr and logged(out) == steps,
    )

    r2 = run_cli(FINDER, "climb", *BOARD, "--engine", engine, "--from", 1, "--out", out)
    check(
        f"climb rerun with another --from is refused ({r2.stderr.strip()[-50:]!r})",
        r2.returncode == 2 and "--from" in r2.stderr,
    )

    held = hunt_files.acquire_lock(out, "climb.jsonl.lock")
    try:
        r2 = run_cli(FINDER, "climb", *BOARD, "--engine", engine, "--out", out)
    finally:
        hunt_files.release_lock(held)
    check(
        f"climb into a directory another climb holds is refused "
        f"({r2.stderr.strip()[-40:]!r})",
        r2.returncode == 2 and "climb.jsonl is locked" in r2.stderr and not r2.stdout,
    )

    other = {**steps[-1], "config": {**steps[-1]["config"], "rows": 5, "cols": 5}}
    gap = {**steps[-1], "at_least": steps[-1]["at_least"] + 1}
    for name, last in (("another board's step", other), ("a step out of order", gap)):
        mixed = Path(d) / f"climb mixed {name}"
        mixed.mkdir()
        write_log(mixed, [*steps[:-1], last], steps[0]["config"])
        r2 = run_cli(FINDER, "climb", *BOARD, "--engine", engine, "--out", mixed)
        check(
            f"climb on a log with {name} is refused, no maximum printed "
            f"({r2.stderr.strip()[-60:]!r})",
            r2.returncode == 2 and "maximum" not in r2.stdout,
        )

    # A climb killed mid-write leaves its last line cut short: the next run
    # drops it and goes on, the step's hunt directory read back.
    torn = Path(d) / "climb torn"
    torn.mkdir()
    cut = json.dumps(steps[1])[:30]
    write_log(torn, steps[:1], steps[0]["config"])
    with (torn / "climb.jsonl").open("a") as f:
        f.write(cut)
    r2 = run_cli(FINDER, "climb", *BOARD, "--engine", engine, "--out", torn)
    check(
        f"climb after a log cut short mid-line resumes with the whole steps "
        f"kept and the cut one dropped ({r2.stderr.strip()[-80:]!r})",
        r2.returncode == 0
        and r2.stdout.splitlines()[-2] == lines[-2]
        and [{**s, "seconds": None} for s in logged(torn)[1:]]
        == [{**s, "seconds": None} for s in steps[1:]]
        and logged(torn)[0] == steps[0],
    )

    again = Path(d) / "climb read back"
    run_cli(FINDER, "climb", *BOARD, "--out", again)
    first, *_ = logged(again)
    (again / "climb.jsonl").unlink()
    r2 = run_cli(FINDER, "climb", *BOARD, "--out", again)
    reread = logged(again)[0]
    check(
        f"climb reading a finished step back: the same count, the time not "
        f"on record ({r2.stdout.splitlines()[:1]})",
        r2.returncode == 0
        and reread == {**first, "seconds": None}
        and r2.stdout.splitlines()[0].endswith(", time not on record"),
    )

    bad = Path(d) / "climb rejected"
    args = ("climb", "--rows", 4, "--cols", 4, "--timeout", 0, "--out", bad)
    run_cli(FINDER, *args)
    (bad / "climb.jsonl").unlink()
    (bad / "at-least-0" / "progress.jsonl").write_text(
        json.dumps({"event": "seed_done", "seed": 0, "outcome": "rejected"}) + "\n"
    )
    r2 = run_cli(FINDER, *args)
    check(
        f"climb on a step `verify` rejected stops with no answer "
        f"({r2.stderr.strip()[-60:]!r})",
        r2.returncode == 2
        and "ended on" in r2.stderr
        and "no grid" not in r2.stdout
        and not logged(bad),
    )
    bad = Path(d) / "climb refused"
    (bad / "at-least-0").mkdir(parents=True)
    (bad / "at-least-0" / "summary.json").write_text("{}")
    r2 = run_cli(FINDER, "climb", *BOARD, "--out", bad)
    check(
        f"climb on a step the driver refuses stops with no answer "
        f"({r2.stderr.strip()[-40:]!r})",
        r2.returncode == 2 and "was refused" in r2.stderr and "grid" not in r2.stdout,
    )

    out = Path(d) / "climb stopped"
    out.mkdir()
    first = {**steps[0], "config": {**steps[0]["config"], "timeout": 0.0}}
    write_log(out, [first], first["config"])
    r = run_cli(FINDER,
        "climb", "--rows", 4, "--cols", 4, "--timeout", 0, "--engine", engine,
        "--out", out,
    )  # fmt: skip
    held, k = first["count"], first["count"] + 1
    tail = r.stdout.splitlines()[-3:]
    # The step line also prints the elapsed seconds, which a slow runner makes
    # 0.1 and not 0.0: match it up to the comma after "time limit reached".
    check(
        f"climb stopped by the time limit above a found grid: best found "
        f"{held}, not proven ({tail})",
        r.returncode == 0
        and len(tail) == 3
        and tail[0].startswith(f"at least {k}: timeout, time limit reached, ")
        and tail[1:]
        == [
            f"best found {held}: not proven, at least {k} reached the time "
            f"limit on {engine}",
            f"best grid: {out / first['dir']} (seed 0)",
        ],
    )

    out = Path(d) / "climb timeout"
    r = run_cli(FINDER, "climb", "--rows", 4, "--cols", 4, "--timeout", 0, "--out", out)
    check(
        f"climb with a zero time limit: nothing found, nothing proven "
        f"({r.stdout.splitlines()[-1:]})",
        r.returncode == 0
        and r.stdout.splitlines()[-1:]
        == ["no grid found: at least 0 reached the time limit on pysat-lazy"],
    )
    out = Path(d) / "climb from 3"
    r = run_cli(FINDER, "climb", *BOARD, "--from", MOST + 1, "--out", out)
    check(
        f"climb --from {MOST + 1}: no grid there, and no maximum claimed "
        f"({r.stdout.splitlines()[-1:]})",
        r.returncode == 0
        and r.stdout.splitlines()[-1:]
        == [f"no grid found: at least {MOST + 1} has no grid on pysat-lazy"],
    )

with tempfile.TemporaryDirectory() as d:
    unused = Path(d) / "unused"
    r = run_cli(
        FINDER, *BOARD, "--number-circles", "-1", "--out", unused, "--seeds=0:1"
    )
    check(
        f"--number-circles -1 is refused ({r.stderr.strip()!r})",
        r.returncode == 2 and "--number-circles" in r.stderr,
    )
    for flags, named in (
        (["--number-circles", 3], "--from"),
        (["--from", -1], "--from"),
    ):
        r = run_cli(FINDER, "climb", *BOARD, *flags, "--out", unused)
        check(
            f"climb {flags[0]} {flags[1]} is refused ({r.stderr.strip()!r})",
            r.returncode == 2 and named in r.stderr and not unused.exists(),
        )
r = run_cli(FINDER, "--help")
check(
    "--help names the flag and the climb",
    r.returncode == 0 and "--number-circles" in r.stdout and "climb" in r.stdout,
)

finish()

"""The hybrid finder's CLI on its PySAT engines (#784, #785), black-box.

`test_ubahn_hybrid_hunt.py` is the CLI's own test, on the CP-SAT engine. This
one runs the hunt and `classify` again with `--engine` naming each PySAT
engine: every example must be one of the brute force's valid hybrid grids for
its conditions and pass the hunt's own `verify`, which is the solver-free
rule reader, and `classify` must give the decision log's words, § Hybrid.
One CaDiCaL thread; about ten seconds an engine.

    uv run finders/ubahn/test_ubahn_hybrid_sat_hunt.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import brute
import hybrid
import hybrid_finder
import hybrid_sat
import network
from subprocess_env import success_env

FINDER = HERE / "hybrid_finder.py"
BOARD = ["--rows", "4", "--cols", "4", "--timeout", "10"]
ENGINES = ("pysat-lazy", "pysat-propagator")
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
        [sys.executable, str(FINDER), *args],
        capture_output=True,
        text=True,
        env=success_env(),
    )


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def meeting(names, exactly=None):
    """The brute force's 4x4 grids that meet these circles and this
    piece-count condition."""
    circles = [hybrid.parse_cell(name) for name in names]
    return {
        net
        for net in brute.hybrid_grids(4, 4)
        if not hybrid.why_not_hybrid(net, 4, 4, circles)
        and (exactly is None or network.Exactly.parse(exactly).holds(net, 4, 4))
    }


def hunt(d, engine, name, *flags, seeds=40):
    """Run a hunt on this engine with these flags; returns (the examples'
    records, their networks, the `empty` reasons, run.json's config)."""
    out = Path(d) / f"{engine} {name}"
    r = run_cli(
        *BOARD,
        "--engine",
        engine,
        *flags,
        "--out",
        str(out),
        f"--seeds=0:{seeds}",
        "--workers",
        "1",
    )
    label = f"{engine}, {name}"
    check(f"{label}: the hunt exits 0 (stderr: {r.stderr[-500:]})", r.returncode == 0)
    examples = read_jsonl(out / "examples.jsonl")
    summary = json.loads((out / "summary.json").read_text())
    check(
        f"{label}: every seed is accounted for, none rejected by verify",
        summary.get("seeds_done") == seeds
        and summary["examples"] + summary["duplicates"] + summary["empty"] == seeds
        and summary["rejected"] == 0,
    )
    check(
        f"{label}: every record names its engine",
        all(ex["engine"] == engine for ex in examples),
    )
    return (
        examples,
        [READER.candidate_from_record(ex).network for ex in examples],
        [
            e.get("empty_reason")
            for e in read_jsonl(out / "progress.jsonl")
            if e.get("outcome") == "empty"
        ],
        json.loads((out / "run.json").read_text()).get("config"),
    )


for engine in ENGINES:
    with tempfile.TemporaryDirectory() as d:
        examples, nets, _, config = hunt(d, engine, "no condition")
        want = meeting([])
        check(
            f"{engine}, no condition: the hunt wrote examples, each a "
            f"brute-force hybrid grid and no two the same ({len(nets)})",
            len(nets) >= 5 and set(nets) <= want and len(set(nets)) == len(nets),
        )
        check(
            f"{engine}, no condition: run.json records the engine",
            config is not None and config["engine"] == engine,
        )

        # r2c4 is off the main diagonal, so the conditions have no symmetry
        # and each grid is its own example.
        _, nets, _, _ = hunt(d, engine, "r2c4", "--circles", "r2c4")
        want = meeting(["r2c4"])
        check(
            f"{engine}, r2c4 circled: every example is one of the brute force's "
            f"{len(want)}, each once ({len(nets)} examples)",
            nets and set(nets) <= want and len(set(nets)) == len(nets),
        )

        _, nets, _, _ = hunt(
            d,
            engine,
            "two crosses",
            "--circles",
            "c1:turn c4:turn",
            "--exactly",
            "2:cross:r2",
        )
        want = meeting(["c1:turn", "c4:turn"], "2:cross:r2")
        check(
            f"{engine}, 2 crosses in r2, c1:turn and c4:turn circled: every "
            f"example is one of the brute force's {len(want)} ({len(nets)})",
            len(want) == 2 and nets and set(nets) <= want,
        )

        # Conditions with no grid: every seed is empty and says why.
        examples, _, reasons, _ = hunt(
            d, engine, "no grid", "--circles", "r2c2 r2c4", seeds=3
        )
        check(
            f"{engine}, r2c2 and r2c4 circled: no example, three seeds empty as "
            f"infeasible ({reasons})",
            not examples
            and len(reasons) == 3
            and all("infeasible" in reason for reason in reasons),
        )

    # `classify`: the decision log's table, § Hybrid, word for word.
    for flags, word, said in (
        ([], "not_unique", "more than one grid"),
        (["--circles", "r2c2"], "not_unique", "more than one grid"),
        (["--circles", "c1:turn r2c4"], "unique", "exactly one grid"),
        (["--circles", "r1:turn r4c2"], "unique", "exactly one grid"),
        (["--circles", "r2c2 r2c4"], "infeasible", "no grid"),
        (["--circles", "c4:turn r4:turn"], "infeasible", "no grid"),
        (["--circles", "r1c1"], "infeasible", "no grid"),
        (["--exactly", "2:cross:r2"], "not_unique", "more than one grid"),
        (["--exactly", "2:cross:r2", "--circles", "r2c4"], "infeasible", "no grid"),
    ):
        label = f"{engine}, classify {' '.join(flags) or 'no condition'}"
        r = run_cli("classify", *BOARD, "--engine", engine, *flags)
        first = r.stdout.splitlines()[:1]
        check(
            f"{label}: {word}, {said} ({first}, stderr: {r.stderr[-300:]})",
            r.returncode == 0 and first == [f"{word}: {said}"],
        )
        # A time limit reached is a timeout whatever the true answer is.
        r = run_cli(
            "classify", "--rows", "4", "--cols", "4", "--engine", engine, *flags,
            "--timeout", "0",
        )  # fmt: skip
        check(
            f"{label} with a zero time limit: timeout ({r.stdout.strip()!r})",
            r.returncode == 0
            and r.stdout.splitlines() == ["timeout: time limit reached"],
        )

    # The one grid of a unique condition is drawn under the answer.
    r = run_cli("classify", *BOARD, "--engine", engine, "--circles", "c1:turn r2c4")
    (only,) = meeting(["c1:turn", "r2c4"])
    check(
        f"{engine}, classify draws the one grid of a unique condition",
        r.stdout.splitlines()[1:] == hybrid.drawing(only, 4, 4, [(-1, 0), (1, 3)]),
    )

check(
    "--engine pysat-lazy is the PySAT engine with lazy connectivity cuts",
    hybrid_finder.ENGINES["pysat-lazy"] == hybrid_sat.Engine(hybrid_sat.LAZY),
)
check(
    "--engine pysat-propagator is the one with the connectivity propagator",
    hybrid_finder.ENGINES.get("pysat-propagator")
    == hybrid_sat.Engine(hybrid_sat.PROPAGATOR),
)
r = run_cli("--help")
check(
    f"--help names every engine ({', '.join(ENGINES)})",
    r.returncode == 0 and all(engine in r.stdout for engine in ENGINES),
)

sys.exit(0 if ok else 1)

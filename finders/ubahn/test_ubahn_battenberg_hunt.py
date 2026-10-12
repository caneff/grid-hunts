"""The hybrid finder's CLI under Battenberg markings (spec #20, #22),
black-box, on each PySAT engine.

`--battenberg "CELLS"` names the windows that carry a marking, each by its
top-left cell, and `--battenberg-only` turns the negative constraint on. On
4x4 every example of a hunt must be one of the brute force's grids for its
conditions and pass the hunt's own `verify`, which is the solver-free rule
reader, and `classify` must give the word of every row of the decision log's
table, § Hybrid: Battenberg markings, the 4x4 answers. Then the record's
fields, a record older than the condition, the refusals, and on 5x5 the
symmetry the markings leave.

One CaDiCaL thread; about forty seconds.

    uv run finders/ubahn/test_ubahn_battenberg_hunt.py
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
from dedupe import IDENTITY
from subprocess_env import success_env
from verified_io import read_verified

FINDER = HERE / "hybrid_finder.py"
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


def transposed(net):
    """The grid reflected in the main diagonal."""
    return frozenset(
        tuple(sorted(((r1, c1)[::-1], (r2, c2)[::-1]))) for (r1, c1), (r2, c2) in net
    )


def meeting(names, only=False):
    """The brute force's 4x4 grids that meet these markings."""
    marked = hybrid.parse_windows(" ".join(names), 4, 4)
    return {
        net
        for net in brute.hybrid_grids(4, 4)
        if not hybrid.why_not_hybrid(net, 4, 4, battenberg=marked, battenberg_only=only)
    }


def hunt(d, engine, name, *flags, side=4, seeds=20):
    """Run a hunt on this engine with these flags, then `verify` it; returns
    (the examples' records, their networks, the `empty` reasons, run.json's
    config)."""
    out = Path(d) / f"{engine} {name}"
    board = ["--rows", str(side), "--cols", str(side), "--timeout", "10"]
    r = run_cli(
        *board,
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
    r = run_cli("verify", str(out))
    _, verdicts = read_verified(out / "verified.jsonl") if examples else (None, [])
    check(
        f"{label}: `verify` passes every example ({len(verdicts)})",
        r.returncode == 0
        and len(verdicts) == len(examples)
        and all(v["ok"] for v in verdicts),
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


TABLE = (
    ([], "not_unique", "more than one grid"),
    (["--battenberg-only"], "not_unique", "more than one grid"),
    *(
        (["--battenberg", name], "unique", "exactly one grid")
        for name in ("c1:turn", "c2:turn", "r3c1", "r1:turn", "r2:turn", "r1c3")
    ),
    (
        ["--battenberg", "c1:turn c2:turn r3c1", "--battenberg-only"],
        "unique",
        "exactly one grid",
    ),
    (
        ["--battenberg", "r1:turn r2:turn r1c3", "--battenberg-only"],
        "unique",
        "exactly one grid",
    ),
    (["--battenberg", "c1:turn", "--battenberg-only"], "infeasible", "no grid"),
    (["--battenberg", "c1:turn r1:turn"], "infeasible", "no grid"),
    (["--battenberg", "r1c1"], "infeasible", "no grid"),
)

for engine in ENGINES:
    with tempfile.TemporaryDirectory() as d:
        # One marking: the one grid that has it, with all three of its
        # checkerboard windows on the record.
        examples, nets, _, config = hunt(
            d, engine, "c1:turn", "--battenberg", "c1:turn"
        )
        want = meeting(["c1:turn"])
        check(
            f"{engine}, c1:turn marked: one example, the brute force's one grid",
            len(want) == 1 and set(nets) == want and len(nets) == 1,
        )
        check(
            f"{engine}, c1:turn marked: the record carries the marking, the "
            f"negative constraint off, and the grid's checkerboard windows",
            [
                (ex["battenberg"], ex["battenberg_only"], ex["checkerboard_windows"])
                for ex in examples
            ]
            == [(["c1:turn"], False, ["c1:turn", "c2:turn", "r3c1"])],
        )
        check(
            f"{engine}, c1:turn marked: run.json carries the marking ({config})",
            config is not None
            and config.get("battenberg") == ["c1:turn"]
            and "battenberg_only" not in config,
        )

        # A record written before the condition has none of its fields: it
        # reads as no markings and the constraint off, and still verifies.
        old = Path(d) / f"{engine} old"
        old.mkdir()
        record = dict(examples[0])
        for field in ("battenberg", "battenberg_only", "checkerboard_windows"):
            del record[field]
        (old / "examples.jsonl").write_text(json.dumps(record) + "\n")
        r = run_cli("verify", str(old))
        asked = READER.candidate_from_record(record).conditions
        check(
            f"{engine}: a record older than the condition verifies, as no "
            f"markings and the constraint off (stderr: {r.stderr[-300:]})",
            r.returncode == 0
            and [v["ok"] for v in read_verified(old / "verified.jsonl")[1]] == [True]
            and asked.battenberg == frozenset()
            and asked.battenberg_only is False,
        )

        # A record whose two fields are not a list of names and a true or
        # false is refused by the field's name, never read as "off".
        for field, value in (
            ("battenberg_only", None),
            ("battenberg_only", "false"),
            ("battenberg_only", 0),
            ("battenberg", None),
            ("battenberg", [3]),
            ("battenberg", "r1c3"),
        ):
            try:
                READER.candidate_from_record({**examples[0], field: value})
                refused = "no error"
            except ValueError as e:
                refused = str(e)
            check(
                f"{engine}: a record with {field} {value!r} is refused, naming "
                f"the field ({refused!r})",
                refused.startswith(f"{field} is {value!r}"),
            )

        # `verify` re-reads the markings: the same grid on a record that
        # claims a marking it does not have, and one under the negative
        # constraint with a checkerboard window left unmarked.
        bad = Path(d) / f"{engine} bad"
        bad.mkdir()
        (bad / "examples.jsonl").write_text(
            json.dumps({**examples[0], "battenberg": ["r1c1"]})
            + "\n"
            + json.dumps({**examples[0], "battenberg_only": True})
            + "\n"
        )
        r = run_cli("verify", str(bad))
        verdicts = read_verified(bad / "verified.jsonl")[1]
        check(
            f"{engine}: `verify` rejects a marking that fails and a forbidden "
            f"checkerboard window, each by its window "
            f"({[v.get('reason') for v in verdicts]})",
            r.returncode == 0
            and [v["ok"] for v in verdicts] == [False, False]
            and "Battenberg marking at r1c1: not a checkerboard window"
            in verdicts[0]["reason"]
            and "checkerboard window at c2:turn has no Battenberg marking"
            in verdicts[1]["reason"],
        )

        # The negative constraint with no marking: the 16 grids with no
        # checkerboard window. No marking moves under the reflection in the
        # main diagonal, so a grid's transpose is a repeat.
        examples, nets, _, config = hunt(d, engine, "only", "--battenberg-only")
        want = meeting([], only=True)
        check(
            f"{engine}, --battenberg-only: every example is one of the brute "
            f"force's {len(want)}, none the transpose of another ({len(nets)})",
            len(want) == 16
            and len(nets) >= 5
            and set(nets) <= want
            and all(transposed(a) != b for a in nets for b in nets if a != b),
        )
        check(
            f"{engine}, --battenberg-only: every record has the constraint on "
            f"and lists no checkerboard window, and run.json has it on",
            all(
                ex["battenberg_only"] is True
                and ex["battenberg"] == []
                and ex["checkerboard_windows"] == []
                for ex in examples
            )
            and config.get("battenberg_only") is True,
        )

        # A grid's full set of markings under the negative constraint.
        _, nets, _, _ = hunt(
            d, engine, "all three", "--battenberg", "r1:turn r2:turn r1c3",
            "--battenberg-only", seeds=3,
        )  # fmt: skip
        want = meeting(["r1:turn", "r2:turn", "r1c3"], only=True)
        check(
            f"{engine}, a grid's three markings and the negative constraint: "
            f"one example, the brute force's one grid",
            len(want) == 1 and set(nets) == want and len(nets) == 1,
        )

        # One marking of three under the negative constraint: no grid.
        examples, _, reasons, _ = hunt(
            d, engine, "one of three", "--battenberg", "c1:turn",
            "--battenberg-only", seeds=3,
        )  # fmt: skip
        check(
            f"{engine}, c1:turn marked under the negative constraint: no "
            f"example, three seeds empty as infeasible ({reasons})",
            not examples
            and len(reasons) == 3
            and all("infeasible" in reason for reason in reasons),
        )

        # A marking and a circle in one run: r2c4 is a valid circle in the
        # one grid with the marking r3c1.
        examples, nets, _, _ = hunt(
            d, engine, "with a circle", "--battenberg", "r3c1", "--circles", "r2c4",
            seeds=3,
        )  # fmt: skip
        check(
            f"{engine}, r3c1 marked and r2c4 circled: the one grid, the record "
            f"carrying both",
            set(nets) == meeting(["r3c1"])
            and [(ex["battenberg"], ex["circles"]) for ex in examples]
            == [(["r3c1"], ["r2c4"])],
        )

        # The symmetry the markings leave, on 5x5 (the 4x4 grids with a
        # checkerboard window are too few). r2c2's window is its own image in
        # the main diagonal, so the reflection is kept and a grid's transpose
        # is a repeat; c3:straight's image is r3:straight, so a marking there
        # leaves no symmetry and a grid and its transpose are two examples.
        _, nets, _, _ = hunt(d, engine, "5x5 r2c2", "--battenberg", "r2c2", side=5)
        check(
            f"{engine}, 5x5 with r2c2 marked: no example is the transpose of "
            f"another ({len(nets)} examples)",
            len(nets) == 2
            and all(transposed(a) != b for a in nets for b in nets if a != b),
        )
        _, nets, _, _ = hunt(
            d, engine, "5x5 c3:straight", "--battenberg", "c3:straight", side=5
        )
        check(
            f"{engine}, 5x5 with c3:straight marked: a grid and its transpose "
            f"are two examples ({len(nets)} examples)",
            any(transposed(a) == b for a in nets for b in nets if a != b),
        )

    # `classify`: the decision log's table, word for word.
    for flags, word, said in TABLE:
        label = f"{engine}, classify {' '.join(flags) or 'no condition'}"
        r = run_cli(
            "classify", "--rows", "4", "--cols", "4", "--timeout", "10",
            "--engine", engine, *flags,
        )  # fmt: skip
        first = r.stdout.splitlines()[:1]
        check(
            f"{label}: {word}, {said} ({first}, stderr: {r.stderr[-300:]})",
            r.returncode == 0 and first == [f"{word}: {said}"],
        )

    # A window that is not wholly on the board is refused before any solve,
    # naming the cell that is off it.
    with tempfile.TemporaryDirectory() as d:
        for i, (name, off) in enumerate(
            (("r4c4", "r4c5"), ("r4:turn", "r5:turn"), ("r1:blank", "r1:blank"))
        ):
            out = Path(d) / str(i)
            flags = ["--rows", "4", "--cols", "4", "--engine", engine]
            flags += ["--battenberg", name]
            r = run_cli(*flags, "--out", str(out), "--seeds=0:1", "--workers", "1")
            check(
                f"{engine}: hunt --battenberg {name} is refused, exit 2, naming "
                f"{off} ({r.stderr.strip()[-120:]!r})",
                r.returncode == 2
                and f"--battenberg: window {name} is not wholly on" in r.stderr
                and f"{off} is off it" in r.stderr
                and not out.exists(),
            )
            r = run_cli("classify", *flags)
            check(
                f"{engine}: classify --battenberg {name} is refused, exit 2, "
                f"naming {off}",
                r.returncode == 2 and f"{off} is off it" in r.stderr and not r.stdout,
            )

# The CP-SAT engine has no model of the condition: either flag is refused by
# name before any solve.
with tempfile.TemporaryDirectory() as d:
    for i, (flags, named) in enumerate(
        (
            (["--battenberg", "c1:turn"], "--battenberg"),
            (["--battenberg-only"], "--battenberg-only"),
        )
    ):
        out = Path(d) / str(i)
        board = ["--rows", "4", "--cols", "4", "--engine", "cpsat"]
        r = run_cli(*board, *flags, "--out", str(out), "--seeds=0:1", "--workers", "1")
        reason = f"hybrid_finder: {named} is on the PySAT engines only"
        check(
            f"hunt --engine cpsat {' '.join(flags)} is refused, exit 2, naming "
            f"the flag ({r.stderr.strip()[-160:]!r})",
            r.returncode == 2 and reason in r.stderr and not out.exists(),
        )
        r = run_cli("classify", *board, *flags)
        check(
            f"classify --engine cpsat {' '.join(flags)} is refused, exit 2, "
            f"naming the flag",
            r.returncode == 2 and reason in r.stderr and not r.stdout,
        )

# `verify` and `render` read a record's own markings: the flags are refused
# there, not ignored.
for command in ("verify", "render"):
    for flags, named in (
        (["--battenberg", "c1:turn"], "--battenberg"),
        (["--battenberg-only"], "--battenberg-only"),
    ):
        r = run_cli(*flags, command, "nowhere")
        check(
            f"{command} {' '.join(flags)} is refused, exit 2, naming the flag",
            r.returncode == 2
            and f"hybrid_finder: {named} is not for `{command}`" in r.stderr,
        )

# The condition's symmetry counts markings: the reflection in the main
# diagonal is kept only when the marked windows map onto themselves.
for names, kept in (
    ("", True),
    ("r2c2", True),
    ("c3:straight r3:straight", True),
    ("c3:straight", False),
    ("r2c2 r1c2", False),
):
    marked = hybrid.parse_windows(names, 5, 5)
    group = hybrid_finder.condition_symmetry(hybrid.Conditions(5, 5, battenberg=marked))
    check(
        f"5x5 markings {names or 'none'}: the reflection is "
        f"{'kept' if kept else 'not a symmetry'}",
        (group != IDENTITY) is kept,
    )

r = run_cli("--help")
check(
    "--help describes --battenberg and --battenberg-only",
    r.returncode == 0
    and '--battenberg "CELL CELL ..."' in r.stdout
    and "--battenberg-only" in r.stdout
    and "checkerboard window" in r.stdout,
)

sys.exit(0 if ok else 1)

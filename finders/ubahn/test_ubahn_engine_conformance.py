"""One suite over every U-Bahn engine (spec #117, #138).

Every entry of `hybrid_engines.ENGINES` answers the same 4x4 cases through
both of its calls, a grid for a seed and a classification, and the answers
are judged by the solver-free rules: `hybrid.failures` for a grid and the
decision log's word (§ Hybrid, the 4x4 answers) for a classification. A rule
change that one engine misses fails here and names that engine. The cpsat
engine has no model of a Battenberg marking, so a case with one is an
expected refusal for it, not a skipped row. `brute.py` stays out of this: it
is independent of `network` (`.audit-ignore.md`), and the oracle here is the
rule reader.

One CaDiCaL thread; a few seconds.

    uv run finders/ubahn/test_ubahn_engine_conformance.py
"""

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import hybrid
import hybrid_engines
import network
from cli_checks import check, finish

TIME_LIMIT = 10.0
SEEDS = range(4)
REFUSAL = "Battenberg markings are on the PySAT engines only"


def cells(*names):
    return frozenset(hybrid.parse_cell(name) for name in names)


def cond(circles=(), exactly=None, marks=(), only=False, strip=False):
    return hybrid.Conditions(
        4,
        4,
        cells(*circles),
        exactly,
        strip,
        battenberg=hybrid.parse_windows(" ".join(marks), 4, 4),
        battenberg_only=only,
    )


# (label, conditions, the decision log's word), § Hybrid and § Hybrid:
# Battenberg markings, the 4x4 answers.
CASES = (
    ("no condition", cond(), "not_unique"),
    ("circles r2c2", cond(("r2c2",)), "not_unique"),
    ("circles c1:turn r2c4", cond(("c1:turn", "r2c4")), "unique"),
    ("circles r1:turn r4c2", cond(("r1:turn", "r4c2")), "unique"),
    ("circles r2c2 r2c4", cond(("r2c2", "r2c4")), "infeasible"),
    ("circles c4:turn r4:turn", cond(("c4:turn", "r4:turn")), "infeasible"),
    ("circles r1c1", cond(("r1c1",)), "infeasible"),
    (
        "2 crosses in r2, circles c1:turn c4:turn",
        cond(("c1:turn", "c4:turn"), network.Exactly.parse("2:cross:r2")),
        "not_unique",
    ),
    *(
        (f"marking {mark}", cond(marks=(mark,)), "unique")
        for mark in ("c1:turn", "c2:turn", "r3c1", "r1:turn", "r2:turn", "r1c3")
    ),
    ("marking r1c1", cond(marks=("r1c1",)), "infeasible"),
    ("blank strip", cond(strip=True), "not_unique"),
    ("blank strip, negative constraint", cond(only=True, strip=True), "not_unique"),
    (
        "markings c1:turn c2:turn r3c1, negative constraint",
        cond(marks=("c1:turn", "c2:turn", "r3c1"), only=True),
        "unique",
    ),
    (
        "markings r1:turn r2:turn r1c3, negative constraint",
        cond(marks=("r1:turn", "r2:turn", "r1c3"), only=True),
        "unique",
    ),
    ("negative constraint", cond(only=True), "not_unique"),
    ("negative constraint, marking c1:turn", cond(marks=("c1:turn",), only=True), "infeasible"),
    ("markings c1:turn r1:turn", cond(marks=("c1:turn", "r1:turn")), "infeasible"),
)  # fmt: skip


def refused(call):
    """The refusal's text when the call raises `ValueError`, else None."""
    try:
        call()
    except ValueError as e:
        return str(e)
    return None


def judged(name, label, conditions, found):
    """Whether a grid the engine gave passes the rule reader."""
    why = hybrid.failures(found, conditions)
    check(f"{name}, {label}: the grid passes the rule reader ({why})", not why)


def conform(name, engine, label, conditions, word):
    """One case through one engine's two calls."""

    def classify():
        return engine.classify(conditions, time_limit=TIME_LIMIT, workers=1)

    def grid(seed):
        return engine.grid(conditions, random.Random(seed), time_limit=TIME_LIMIT)

    if name not in hybrid_engines.PYSAT_ENGINES and (
        conditions.battenberg or conditions.battenberg_only
    ):
        for what, call in (("classify", classify), ("grid", lambda: grid(0))):
            text = refused(call)
            check(
                f"{name}, {label}: {what} is refused, naming the PySAT "
                f"engines ({text!r})",
                text is not None and REFUSAL in text,
            )
        return
    got = classify()
    check(
        f"{name}, {label}: classified {word} (got {got.status})",
        got.status == word,
    )
    if got.network is not None:
        judged(name, f"{label}, classification's grid", conditions, got.network)
    else:
        check(
            f"{name}, {label}: no grid given only when none is ({got.status})",
            word == "infeasible",
        )
    sampled = [grid(seed) for seed in SEEDS]
    want = "infeasible" if word == "infeasible" else "found"
    check(
        f"{name}, {label}: a grid for a seed reads {want} "
        f"({[s.status for s in sampled]})",
        all(s.status == want for s in sampled),
    )
    for s in sampled:
        if s.network is not None:
            judged(name, f"{label}, a grid for a seed", conditions, s.network)
    if word == "unique":
        check(
            f"{name}, {label}: every seed and the classification give the one grid",
            len({s.network for s in sampled} | {got.network}) == 1,
        )


for name, engine in hybrid_engines.ENGINES.items():
    for label, conditions, word in CASES:
        conform(name, engine, label, conditions, word)

finish()

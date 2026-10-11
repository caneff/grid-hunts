"""The U-Bahn baseline measurement (#777), black-box on a 4x4 board.

`measure` must account for every seed exactly once, agree seed by seed with
the finder's own `propose` (so the measured step is the finder's step, not a
copy of it), and dedupe the way the hunt driver does. `report` must label a
count a timeout stopped as capped. One CP-SAT worker; a few seconds in all.

    uv run finders/ubahn/test_ubahn_measure.py
"""

import contextlib
import io
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import measure_baseline
import model
from dedupe import canonical_key
from protocol import Empty
from ubahn_finder import UbahnFinder

ok = True


def check(name, cond):
    global ok
    status = "ok" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"{status}: {name}")


# Seeds 0:60 on 4x4 reach every cause the board can: unique, one duplicate
# and one not unique.
SEEDS = range(60)

REACHED = {}
for connectivity in ("flow", "tree"):
    outcomes = measure_baseline.measure(4, 4, connectivity, SEEDS, timeout=60.0)
    check(
        f"{connectivity}: one outcome per seed, in order",
        [o.seed for o in outcomes] == list(SEEDS),
    )
    REACHED[connectivity] = {o.cause for o in outcomes}
    check(
        f"{connectivity}: seeds reach unique, duplicate and not_unique",
        {"unique", "duplicate", "not_unique"} <= REACHED[connectivity],
    )
    check(
        f"{connectivity}: every cause is a known one",
        {o.cause for o in outcomes} <= set(measure_baseline.CAUSES),
    )
    check(
        f"{connectivity}: a proof is timed exactly when one ran",
        all(
            (o.prove_s is not None) == (o.cause != "timeout sampling") for o in outcomes
        ),
    )

    # Seed by seed, `propose` (what the hunt runs) and the measured split
    # (sample, then prove) must reach the same verdict and the same network.
    finder = UbahnFinder(4, 4, None, 60.0, connectivity=connectivity)
    finder.workers = 1
    seen = set()
    for o in outcomes:
        proposed = finder.propose(random.Random(o.seed))
        if isinstance(proposed, Empty):
            expected = {
                "not unique": "not_unique",
                "timeout proving uniqueness": "timeout proving",
                "timeout sampling a network": "timeout sampling",
            }.get(proposed.reason)
            check(
                f"{connectivity} seed {o.seed}: propose said {proposed.reason!r}",
                o.cause == expected,
            )
            continue
        key = canonical_key(finder.key(proposed), finder.symmetry)
        want = "duplicate" if key in seen else "unique"
        seen.add(key)
        check(
            f"{connectivity} seed {o.seed}: propose gave a network, {want}",
            o.cause == want,
        )

# A tally, not a measurement: the report's own words. Two unique, one
# duplicate, one not unique, one proof and one sample the limit stopped.
Outcome = measure_baseline.Outcome
rows = [
    Outcome(0, "unique", 0.010, 0.020),
    Outcome(1, "unique", 0.010, 0.020),
    Outcome(2, "not_unique", 0.030, 0.040),
    Outcome(3, "duplicate", 0.050, 0.060),
    Outcome(4, "timeout proving", 0.070, 60.0),
    Outcome(5, "timeout sampling", 60.0, None),
]
text = measure_baseline.report("6x6", "flow", rows, timeout=60.0)
check(
    "report names the sample size and who reached a verdict",
    "6 seeds, 5 sampled a network, 4 of those proved to a verdict" in text,
)
check("report shares unique over the decided only", "3 of 4 decided" in text)
for row in (
    "| unique | 2 |",
    "| duplicate | 1 |",
    "| not_unique | 1 |",
    "| timeout sampling (capped) | 1 |",
    "| timeout proving (capped) | 1 |",
):
    check(f"report row {row}", row in text)
check("report explains the capped counts", "are capped counts" in text)
check(
    "proof times leave the timed-out proof out",
    "| Uniqueness proof | 4 |" in text,
)
check(
    "sample times leave the timed-out sample out",
    "| Sampling a network | 5 |" in text,
)
clean = measure_baseline.report("6x6", "flow", rows[:4], timeout=60.0)
check("report has no capped word when nothing timed out", "capped" not in clean)
check("report still lists a zero timeout row", "| timeout proving | 0 |" in clean)

# Sampling stays on flow whatever encoding proves; the proof takes the one
# asked for. `uniqueness` builds its model with `build`, so each seed's
# calls are flow (sample) then tree (proof).
calls = {"build": [], "uniqueness": []}
real_build, real_uniqueness = model.build, model.uniqueness


def spy_build(rows, cols, connectivity, **kwargs):
    calls["build"].append(connectivity)
    return real_build(rows, cols, connectivity, **kwargs)


def spy_uniqueness(rows, cols, numbers, connectivity, **kwargs):
    calls["uniqueness"].append(connectivity)
    return real_uniqueness(rows, cols, numbers, connectivity, **kwargs)


model.build, model.uniqueness = spy_build, spy_uniqueness
try:
    measure_baseline.measure(4, 4, "tree", range(3), timeout=60.0)
finally:
    model.build, model.uniqueness = real_build, real_uniqueness
check(
    "sampling builds on flow, the proof on tree", calls["build"] == ["flow", "tree"] * 3
)
check("every proof is asked for tree", calls["uniqueness"] == ["tree"] * 3)


def raises(fn, error):
    """Whether `fn()` raises `error`; argparse's usage message is kept off
    the test's output."""
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            fn()
    except error:
        return True
    return False


real_prove, real_sample = UbahnFinder.prove, UbahnFinder.sample
try:
    UbahnFinder.prove = lambda self, found: "infeasible"
    check(
        "an unexpected proof status stops the run",
        raises(
            lambda: measure_baseline.measure(4, 4, "flow", [0], timeout=60.0),
            RuntimeError,
        ),
    )
    UbahnFinder.sample = lambda self, rng: Empty("infeasible: no network")
    check(
        "an empty sample that is not a timeout stops the run",
        raises(
            lambda: measure_baseline.measure(4, 4, "flow", [0], timeout=60.0),
            RuntimeError,
        ),
    )
    UbahnFinder.sample = lambda self, rng: Empty("timeout sampling a network")
    timed_out = measure_baseline.measure(4, 4, "flow", [0], timeout=60.0)
    check(
        "a sampling timeout is its own cause",
        [(o.cause, o.prove_s) for o in timed_out] == [("timeout sampling", None)],
    )
finally:
    UbahnFinder.prove, UbahnFinder.sample = real_prove, real_sample

for seeds in ("5:5", "7:3", "x:3", "3"):
    check(
        f"--seeds {seeds} is refused",
        raises(
            lambda seeds=seeds: measure_baseline.main(
                [
                    "--rows",
                    "4",
                    "--cols",
                    "4",
                    "--connectivity",
                    "flow",
                    "--seeds",
                    seeds,
                ]
            ),
            SystemExit,
        ),
    )

sys.exit(0 if ok else 1)

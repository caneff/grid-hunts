"""Baseline measurement of the U-Bahn finder's proposal step (#777). Run by
hand; no gate runs it (its test, `test_ubahn_measure.py`, covers the counting
on a 4x4 board).

    uv run finders/ubahn/measure_baseline.py --rows 6 --cols 6 \\
        --connectivity flow --seeds 0:200 --timeout 60

Runs the finder's own `sample` and `prove` (what `propose` is made of) for
each seed on one CP-SAT worker, with no `--exactly` condition, and prints a
Markdown section: the sample size, the share of proposals unique under their
full outside numbers, the time per sample and per uniqueness proof, and the
seeds counted by cause. A seed whose network repeats an earlier unique one
under the board's symmetries is a `duplicate`, keyed as the hunt driver keys
it; `verify` is not run, so a driver's "rejected" cause has no row here.
Sampling always runs on flow, as the shipped finder does; `--connectivity`
picks the encoding of the uniqueness proof only.
A solve the time limit stopped is a `timeout` cause and its time is the cap,
so it is left out of the time columns and its count is labelled capped.
One progress line per seed goes to stderr as it finishes.
"""

import argparse
import random
import statistics
import sys
import time
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
# isort: split
from dedupe import canonical_key
from protocol import Empty
from ubahn_finder import Candidate, UbahnFinder

# A seed ends in exactly one of these.
CAUSES = (
    "unique",
    "duplicate",
    "not_unique",
    "timeout sampling",
    "timeout proving",
)


class Outcome(NamedTuple):
    """One seed: its cause and the seconds spent sampling and proving.
    `prove_s` is None when no proof ran."""

    seed: int
    cause: str
    sample_s: float
    prove_s: float | None


def measure(rows, cols, connectivity, seeds, *, timeout, progress=None):
    """One `Outcome` per seed, in order. `progress` is called with each."""
    finder = UbahnFinder(rows, cols, None, timeout, connectivity=connectivity)
    finder.workers = 1
    seen = set()
    outcomes = []
    for seed in seeds:
        started = time.perf_counter()
        found = finder.sample(random.Random(seed))
        sample_s = time.perf_counter() - started
        prove_s = None
        if isinstance(found, Empty):
            # No condition is set, so every network exists and the only
            # empty answer the sampler can give is its time limit.
            if not found.reason.startswith("timeout"):
                raise RuntimeError(f"seed {seed}: sampling said {found.reason!r}")
            cause = "timeout sampling"
        else:
            started = time.perf_counter()
            status = finder.prove(found)
            prove_s = time.perf_counter() - started
            if status == "timeout":
                cause = "timeout proving"
            elif status == "not_unique":
                cause = "not_unique"
            elif status == "unique":
                candidate = Candidate(rows, cols, found, None)
                key = canonical_key(finder.key(candidate), finder.symmetry)
                cause = "duplicate" if key in seen else "unique"
                seen.add(key)
            else:
                raise RuntimeError(f"seed {seed}: the network's own numbers: {status}")
        outcome = Outcome(seed, cause, sample_s, prove_s)
        outcomes.append(outcome)
        if progress:
            progress(outcome)
    return outcomes


def _times(seconds):
    """n, median, mean, 90th percentile and max of `seconds`, in
    milliseconds; dashes for none."""
    if not seconds:
        return "0 | - | - | - | -"
    ms = sorted(s * 1000 for s in seconds)
    p90 = ms[min(len(ms) - 1, int(0.9 * len(ms)))]
    return (
        f"{len(ms)} | {statistics.median(ms):.1f} | {statistics.fmean(ms):.1f} "
        f"| {p90:.1f} | {ms[-1]:.1f}"
    )


def report(size, connectivity, outcomes, *, timeout):
    """The Markdown section for one board size and one encoding."""
    total = len(outcomes)
    count = {cause: sum(o.cause == cause for o in outcomes) for cause in CAUSES}
    proved = [o for o in outcomes if o.prove_s is not None]
    decided = [o for o in proved if o.cause != "timeout proving"]
    unique = count["unique"] + count["duplicate"]
    capped = count["timeout sampling"] + count["timeout proving"]

    lines = [
        f'#### {size}, `connectivity="{connectivity}"`',
        "",
        f"{total} seeds, {len(proved)} sampled a network, {len(decided)} of "
        f"those proved to a verdict, time limit {timeout:g} s per solve, "
        "one worker, no condition.",
        "",
    ]
    if decided:
        lines += [
            f"- **Unique under the full outside numbers: {unique} of "
            f"{len(decided)} decided proposals "
            f"({100 * unique / len(decided):.0f}%).** "
            f"{count['unique']} were new and {count['duplicate']} repeated an "
            "earlier one under the board's symmetries.",
            "",
        ]
    lines += ["| Cause | Seeds |", "| --- | --- |"]
    for cause in CAUSES:
        capped_label = (
            " (capped)" if cause.startswith("timeout") and count[cause] else ""
        )
        lines.append(f"| {cause}{capped_label} | {count[cause]} |")
    lines.append("")
    if capped:
        lines += [
            f"The {capped} timeout seeds are capped counts: the {timeout:g} s "
            "limit stopped them, so their unique-or-not answer is unknown and "
            "they are left out of the share and the time columns.",
            "",
        ]
    lines += [
        "| Step | Solves timed | Median ms | Mean ms | 90th ms | Max ms |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| Sampling a network | "
        f"{_times([o.sample_s for o in outcomes if o.cause != 'timeout sampling'])} |",
        f"| Uniqueness proof | {_times([o.prove_s for o in decided])} |",
        f"| Whole proposal | {_times([o.sample_s + o.prove_s for o in decided])} |",
        "",
    ]
    return "\n".join(lines)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--cols", type=int, required=True)
    parser.add_argument("--connectivity", choices=("flow", "tree"), required=True)
    parser.add_argument("--seeds", default="0:100", metavar="A:B")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)
    try:
        first, last = (int(x) for x in args.seeds.split(":"))
    except ValueError:
        parser.error(f"--seeds {args.seeds!r} is not A:B with whole numbers")
    if last <= first:
        parser.error(f"--seeds {args.seeds} names no seed: B must exceed A")

    def progress(o):
        proof = "-" if o.prove_s is None else f"{o.prove_s * 1000:.1f} ms"
        print(
            f"seed {o.seed}: {o.cause}, sample {o.sample_s * 1000:.1f} ms, "
            f"proof {proof}",
            file=sys.stderr,
            flush=True,
        )

    outcomes = measure(
        args.rows,
        args.cols,
        args.connectivity,
        range(first, last),
        timeout=args.timeout,
        progress=progress,
    )
    print(
        report(
            f"{args.rows}x{args.cols}",
            args.connectivity,
            outcomes,
            timeout=args.timeout,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

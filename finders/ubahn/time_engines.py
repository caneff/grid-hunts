"""Time the hybrid finder's three engines on the same fixed cases (#786,
spec #781). Run by hand, one engine at a time; no gate runs it (its test,
`test_ubahn_time_engines.py`, covers the counting on a 4x4 board).

    uv run finders/ubahn/time_engines.py run --engine cpsat \\
        --progress DIR/cpsat.jsonl [--case NAME ...] [--seeds 0:100] \\
        [--timeout 60]
    uv run finders/ubahn/time_engines.py report DIR/*.jsonl

`run` solves every seed of every case on one engine, in one process and on
one core, and appends one JSON line per solve to the progress file as the
solve ends, so a kill loses nothing; run again with the same file, it skips
the seeds the file already holds. `report` reads the progress files and
prints the Markdown tables.

The cases are Chris's (spec #781): a grid for a seed with no condition at
6x6, 7x7, 8x8 and 10x10, and the example condition at 7x7 for a grid and for
`classify`. `--case` names some of them; all of them run without it.

What a time is: the engine's own call, `grid` or `classify`, from the
conditions to the answer, the model or the clauses built inside it. Process
start and the imports are outside it, and so is the re-read of each found
grid by the rule reader, which stops the run on a grid that breaks a rule.

A solve the time limit stopped is `timeout`: it has its own column, its
count is labelled capped, and its time is the limit, so it is left out of
the time columns. An engine whose first 20 seeds of a case all time out
stops on that case, and the case is labelled capped.

Cuts and conflicts are the PySAT engines' own counts (`hybrid_sat.Listing`),
added up over a case's timed solves.

`classify` takes no seed, so its seeds are repeats of one call. The limit is
per solve inside the CP-SAT engine's `classify`, which makes up to two, and
over the whole call in the PySAT engines'; a `classify` that proves there is
no grid makes one solve in every engine, and the limit then means the same.
"""

import argparse
import json
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
import hybrid
import hybrid_sat
from hybrid_finder import ENGINES, Candidate, HybridFinder
from measure_baseline import seed_range, times
from ubahn_finder import DEFAULT_TIMEOUT

# An engine stops on a case when this many of its first seeds all time out.
CAP_AFTER = 20

# Chris's bar (spec #781): a PySAT engine wins only if it is at least this
# many times faster than CP-SAT at every one of these cases.
BAR = 2
# The engine the bar is read against, whatever the finder's default is.
BASE_ENGINE = "cpsat"
BAR_CASES = ("8x8", "10x10")

# The words of a call that found a grid.
FOUND = ("found", "unique", "not_unique")


class Case(NamedTuple):
    """One timed case: `call` is "grid" (a grid for a seed) or "classify"."""

    name: str
    call: str
    conditions: hybrid.Conditions


# The example of spec #781: circles on the straight and turn number cells of
# rows 6 and 7, as the spec writer read them off Chris's picture.
EXAMPLE = hybrid.Conditions(
    7,
    7,
    frozenset(
        map(hybrid.parse_cell, ("r6:straight", "r6:turn", "r7:straight", "r7:turn"))
    ),
)
CASES = {
    case.name: case
    for case in (
        *(Case(f"{n}x{n}", "grid", hybrid.Conditions(n, n)) for n in (6, 7, 8, 10)),
        Case("7x7 example, grid", "grid", EXAMPLE),
        Case("7x7 example, classify", "classify", EXAMPLE),
    )
}


class Solve(NamedTuple):
    """One timed call: `status` is the engine's own word, `seconds` the
    call's wall clock, and `cuts` and `conflicts` the PySAT engines' counts
    (`hybrid_sat.Listing`), None on the CP-SAT engine."""

    engine: str
    case: str
    seed: int
    status: str
    seconds: float
    cuts: int | None = None
    conflicts: int | None = None


def _call(engine, case, seed, timeout):
    """One call of the engine: `(status, network, cuts, conflicts)`."""
    solver, conditions = ENGINES[engine], case.conditions
    rng = random.Random(seed)
    if isinstance(solver, hybrid_sat.Engine):
        if case.call == "grid":
            found = solver.grid_listing(conditions, rng, time_limit=timeout)
            return (*hybrid_sat.sampled(found), found.cuts, found.conflicts)
        found = solver.classify_listing(conditions, time_limit=timeout)
        return (*hybrid_sat.classified(found), found.cuts, found.conflicts)
    if case.call == "grid":
        return (*solver.grid(conditions, rng, time_limit=timeout), None, None)
    return (*solver.classify(conditions, time_limit=timeout, workers=1), None, None)


class Ran(NamedTuple):
    """One engine on one case: the seeds asked for, the limit per solve, the
    solves that ran, and whether the cap rule stopped the case short."""

    engine: str
    case: str
    call: str
    asked: int
    timeout: float
    solves: tuple
    capped: bool = False


def run(engine, case, seeds, *, timeout, cap_after=CAP_AFTER, done=(), progress=None):
    """One engine on one case, as a `Ran`: one `Solve` per seed, in order,
    stopped short when the first `cap_after` seeds all timed out. A seed that
    has a solve in `done` keeps it and is not solved again; `progress` is
    called with each new solve. Raises RuntimeError on a found grid the rule
    reader refuses."""
    finder = HybridFinder(case.conditions, engine, timeout)
    seeds = list(seeds)
    known = {solve.seed: solve for solve in done}
    solves, capped = [], False
    for seed in seeds:
        if len(solves) == cap_after and all(s.status == "timeout" for s in solves):
            capped = True
            break
        if seed in known:
            solves.append(known[seed])
            continue
        started = time.perf_counter()
        status, found, cuts, conflicts = _call(engine, case, seed, timeout)
        seconds = time.perf_counter() - started
        if found is not None:
            verdict = finder.verify(Candidate(case.conditions, found))
            if not verdict.ok:
                raise RuntimeError(
                    f"{engine}, {case.name}, seed {seed}: {verdict.reason}"
                )
        solves.append(Solve(engine, case.name, seed, status, seconds, cuts, conflicts))
        if progress:
            progress(solves[-1])
    return Ran(engine, case.name, case.call, len(seeds), timeout, tuple(solves), capped)


def _timed(ran):
    """The solves of a run that reached an answer: the ones a time is read
    from."""
    return [solve for solve in ran.solves if solve.status != "timeout"]


def _short(ran):
    """Whether a limit, the cap rule or a kill left the run short of an
    answer for every seed asked."""
    return len(_timed(ran)) < ran.asked


def _row(ran):
    """One run's row of the table."""
    timed = _timed(ran)
    seeds = str(ran.asked)
    if ran.capped:
        seeds = (
            f"{len(ran.solves)} of {ran.asked} "
            f"(capped: first {len(ran.solves)} seeds all timed out)"
        )
    elif len(ran.solves) < ran.asked:
        seeds = f"{len(ran.solves)} of {ran.asked} (incomplete)"
    found = [solve.status for solve in timed if solve.status in FOUND]
    said = f" ({', '.join(sorted(set(found)))})" if ran.call == "classify" else ""
    timeouts = len(ran.solves) - len(timed)

    def total(counts):
        return "-" if not timed or None in counts else str(sum(counts))

    return (
        f"| {ran.case} | {ran.engine} | {seeds} "
        f"| {len(found)}{said if found else ''} "
        f"| {sum(solve.status == 'infeasible' for solve in timed)} "
        f"| {timeouts}{' (capped)' if timeouts else ''} "
        f"| {times([solve.seconds for solve in timed])} "
        f"| {total([solve.cuts for solve in timed])} "
        f"| {total([solve.conflicts for solve in timed])} |"
    )


def _median_ms(ran):
    """The median time of a run's timed solves in milliseconds, or None
    when it has none."""
    timed = _timed(ran)
    return statistics.median(solve.seconds for solve in timed) * 1000 if timed else None


def _bar(rans):
    """The lines that read the runs against the bar: per case, the base
    engine's median over each other engine's, and per engine whether that is
    at least `BAR` at every case of `BAR_CASES`."""
    base = {ran.case: ran for ran in rans if ran.engine == BASE_ENGINE}
    lines = [
        f"| Case | Engine | `{BASE_ENGINE}` median ms | Engine median ms "
        f"| Times faster than `{BASE_ENGINE}` |",
        "| --- | --- | --- | --- | --- |",
    ]
    ratios, capped = {}, {}
    for ran in rans:
        if ran.engine == BASE_ENGINE or ran.case not in base:
            continue
        ours, theirs = _median_ms(base[ran.case]), _median_ms(ran)
        label = " (capped)" if _short(base[ran.case]) or _short(ran) else ""
        known = ours is not None and theirs is not None
        ratio = ours / theirs if known else None
        if ran.case in BAR_CASES:
            ratios.setdefault(ran.engine, {})[ran.case] = ratio
            capped[ran.engine] = capped.get(ran.engine, False) or bool(label)

        def ms(value):
            return "-" if value is None else f"{value:.1f}"

        lines.append(
            f"| {ran.case} | {ran.engine} | {ms(ours)} | {ms(theirs)} "
            f"| {f'{ratio:.2f}' if known else 'unknown'}{label} |"
        )
    lines.append("")
    for engine in dict.fromkeys(r.engine for r in rans if r.engine != BASE_ENGINE):
        read = [ratios.get(engine, {}).get(case) for case in BAR_CASES]
        if any(ratio is not None and ratio < BAR for ratio in read):
            verdict = "no"
        elif None in read:
            verdict = "unknown"
        else:
            verdict = "yes"
        lines.append(
            f"- `{engine}` is at least {BAR} times faster than "
            f"`{BASE_ENGINE}` at {' and '.join(BAR_CASES)}: {verdict}"
            f"{' (capped)' if capped.get(engine) else ''}"
        )
    return lines


def _disagreements(rans):
    """A line per case where one engine found a grid and another proved
    there is none: the conditions decide that, not the engine or the seed."""
    lines = []
    for case in dict.fromkeys(ran.case for ran in rans):
        words = {
            ran.engine: {solve.status for solve in _timed(ran)}
            for ran in rans
            if ran.case == case
        }
        found = sorted(e for e, said in words.items() if said & set(FOUND))
        none = sorted(e for e, said in words.items() if "infeasible" in said)
        if found and none:
            lines += [
                f"**The engines disagree on {case}**: {', '.join(found)} found "
                f"a grid and {', '.join(none)} proved there is none.",
                "",
            ]
    return lines


def report(rans):
    """The Markdown tables for these runs: a row per run in the order
    given, then the reading against the bar."""
    lines = [
        "| Case | Engine | Seeds | Found | Proven impossible | Timed out "
        "| Solves timed | Median ms | Mean ms | 90th ms | Max ms "
        "| Cuts | Conflicts |",
        "| " + " | ".join(["---"] * 13) + " |",
        *map(_row, rans),
        "",
        *_disagreements(rans),
        *_bar(rans),
        "",
    ]
    return "\n".join(lines)


def read_progress(paths):
    """The runs these progress files hold, as `Ran`s in the order their
    cases were first asked for. A case asked for twice is one run with its
    latest limit. Its seeds asked are the latest count, or every seed with a
    solve on file when a second run over other seeds left more of them, so a
    timeout among them still shows the run as short. A cap stands only while
    seeds are missing. Raises ValueError on a line that is no `asked`,
    `solve` or `capped`."""
    asked, solves, capped = {}, {}, set()
    for path in paths:
        for line in Path(path).read_text().splitlines():
            ((kind, fields),) = json.loads(line).items()
            key = (fields["engine"], fields["case"])
            if kind == "asked":
                asked[key] = fields
                solves.setdefault(key, {})
            elif kind == "solve":
                solves[key][fields["seed"]] = Solve(**fields)
            elif kind == "capped":
                capped.add(key)
            else:
                raise ValueError(f"{path}: no progress line is a {kind!r}")
    rans = []
    for key, fields in asked.items():
        held = tuple(solve for _, solve in sorted(solves[key].items()))
        count = max(fields["asked"], len(held))
        rans.append(
            Ran(
                **{**fields, "asked": count},
                solves=held,
                capped=key in capped and len(held) < count,
            )
        )
    return rans


def _run(args):
    path = Path(args.progress)
    cases = [CASES[name] for name in args.case or CASES]
    before = {
        ran.case: ran
        for ran in (read_progress([path]) if path.exists() else [])
        if ran.engine == args.engine
    }
    for case in cases:
        held = before.get(case.name)
        if held and held.solves and held.timeout != args.timeout:
            raise ValueError(
                f"{path} holds {case.name} at a limit of {held.timeout:g} s, "
                f"not {args.timeout:g} s"
            )

    def append(kind, fields):
        with path.open("a") as f:
            f.write(json.dumps({kind: fields}) + "\n")

    def progress(solve):
        append("solve", solve._asdict())
        print(
            f"{solve.engine}, {solve.case}, seed {solve.seed}: {solve.status}, "
            f"{solve.seconds * 1000:.1f} ms",
            file=sys.stderr,
            flush=True,
        )

    # Every case is on file before the first solve, so a run that dies
    # leaves the cases it never reached as incomplete rows.
    for case in cases:
        append(
            "asked",
            {
                "engine": args.engine,
                "case": case.name,
                "call": case.call,
                "asked": len(args.seeds),
                "timeout": args.timeout,
            },
        )
    for case in cases:
        ran = run(
            args.engine,
            case,
            args.seeds,
            timeout=args.timeout,
            done=before[case.name].solves if case.name in before else (),
            progress=progress,
        )
        if ran.capped:
            append("capped", {"engine": args.engine, "case": case.name})
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    runs = commands.add_parser("run")
    runs.add_argument("--engine", choices=ENGINES, required=True)
    runs.add_argument("--progress", required=True, metavar="FILE")
    runs.add_argument("--case", action="append", choices=CASES)
    runs.add_argument("--seeds", default="0:100", metavar="A:B")
    runs.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    reports = commands.add_parser("report")
    reports.add_argument("progress", nargs="+", metavar="FILE")
    args = parser.parse_args(argv)
    try:
        if args.command == "report":
            print(report(read_progress(args.progress)))
            return 0
        args.seeds = seed_range(args.seeds)
        return _run(args)
    except ValueError as e:
        print(f"time_engines: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

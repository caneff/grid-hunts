"""Time the hybrid finder's "at least N banana regions" condition (#792): one
grid per seed for each N, on one engine, one thread. By hand, outside both
gates.

    uv run finders/ubahn/time_bananas.py run --progress FILE \\
        [--side 7] [--min-bananas 0,2,5] [--seeds 50] [--timeout 60] \\
        [--engine pysat-lazy]
    uv run finders/ubahn/time_bananas.py report FILE

`run` appends one JSON row to FILE as each solve ends, so a run that is
stopped keeps what it measured: the N asked for (0 for no condition), the
seed, the engine's status, the seconds around its `grid` call (the model's
build included), how many banana regions the grid has, and whether the rule
reader passes it with the condition. `report` prints the table of those
rows. A timeout is counted as a timeout: the median, mean and slowest are
over the grids found.

The run of record: `docs/research/2026-10-10-u-bahn-finder-decision-log.md`,
§ Hybrid: at least N banana regions.
"""

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hybrid
import hybrid_finder


def measure(side, wanted, seed, engine, timeout):
    """One row: the engine's grid for a seed, timed and re-read."""
    conditions = hybrid.Conditions(side, side, min_bananas=wanted)
    started = time.monotonic()
    status, net = hybrid_finder.ENGINES[engine].grid(
        conditions, random.Random(seed), time_limit=timeout
    )
    seconds = time.monotonic() - started
    return {
        "side": side,
        "min_bananas": wanted,
        "seed": seed,
        "engine": engine,
        "timeout": timeout,
        "status": status,
        "seconds": round(seconds, 3),
        "bananas": net and len(hybrid.bananas(hybrid.values(net, side, side))),
        "reader_ok": net is not None
        and not hybrid.failures(net, side, side, min_bananas=wanted),
    }


def report(rows):
    """The table of a progress file's rows, one line per N, as lines."""
    lines = [
        "| N | Seeds | Found | Timeouts | Reader passes | Median s | Mean s | Slowest s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for wanted in sorted({row["min_bananas"] for row in rows}):
        mine = [row for row in rows if row["min_bananas"] == wanted]
        found = [row["seconds"] for row in mine if row["status"] == "found"]
        times = ["-"] * 3
        if found:
            numbers = (statistics.median(found), statistics.mean(found), max(found))
            times = [f"{t:.3f}" for t in numbers]
        cells = [
            wanted or "none",
            len(mine),
            len(found),
            sum(row["status"] == "timeout" for row in mine),
            sum(row["reader_ok"] for row in mine),
            *times,
        ]
        lines.append("| " + " | ".join(map(str, cells)) + " |")
    return lines


def main(argv):
    parser = argparse.ArgumentParser(prog="time_bananas")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--progress", required=True, metavar="FILE")
    run.add_argument("--side", type=int, default=7)
    run.add_argument("--min-bananas", default="0,2,5", metavar="N,N,...")
    run.add_argument("--seeds", type=int, default=50)
    run.add_argument("--timeout", type=float, default=60.0)
    run.add_argument(
        "--engine",
        default=hybrid_finder.DEFAULT_ENGINE,
        choices=hybrid_finder.ENGINES,
    )
    commands.add_parser("report").add_argument("file")
    args = parser.parse_args(argv)
    if args.command == "report":
        rows = [json.loads(line) for line in Path(args.file).read_text().splitlines()]
        print("\n".join(report(rows)))
        return 0
    with Path(args.progress).open("a") as progress:
        for wanted in map(int, args.min_bananas.split(",")):
            for seed in range(args.seeds):
                row = measure(args.side, wanted, seed, args.engine, args.timeout)
                progress.write(json.dumps(row) + "\n")
                progress.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

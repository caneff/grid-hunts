"""The halver + between-line hunt (spec #39, #41): add between lines to Chris's
board until it has exactly one (digits, halvers) solution.

One seed is the target-grid loop. Sample a target solution of the board's
lines (random digit hints on a one-worker solve). Then, while the rule check
says `not_unique`, add one line that holds in the target and fails in the
second solution, from `candidates.separating_paths`. Stop at `unique`, a hit.
A seed ends `Empty(reason)` when no line of at most `--max-cells` cells
separates the two, when a check times out, or when the seed's budget
(`--max-lines` lines or `--max-seconds` seconds) runs out. None of those is a
proof that no finish exists.

Ranking: a pool of up to `--pool` distinct sampled solutions of the current
lines, plus the second solution. The pool members an added line leaves alive
stay (they are still solutions), and only as many draws as the line broke
top it back up. Cells
are the scarce resource (truths note, section 6), so a candidate scores the
pool solutions it breaks per new cell it takes: its body cells and any
circle no line has yet. Ties go to a candidate touching a cell whose halver
status differs between the target and the second solution, then the
shortest, then the seed's rng. Once the pool holds only the second solution,
that score prefers the line that takes the fewest new cells. A seed whose
target and second solution differ only on body cells of lines already drawn
ends `Empty("no space: ...")` at once.

`verify` re-reads a hit with `brute.py`, the backtracking check that shares
no code with the CP-SAT model: exactly one solution, the hit's own, and every
added line a legal shape. `record` writes the line table and a SudokuMaker
link (`sudoku_kit.link_codec.encode_link`): Chris's lines plus the added
ones, in his line style, with every entered digit, colour and pencil mark
cleared. `summary DIR` prints what a hunt found, or "none found" with its
seeds, its wall clock and each seed's reason.

    uv run finders/halver_between/hunt.py --out DIR --seeds 0:3
    uv run finders/halver_between/hunt.py verify DIR
    uv run finders/halver_between/hunt.py summary DIR

The driver's flags (`--out`, `--seeds`, `--workers`, ...) are its own
(finders/hunt/driver.py). Every CP-SAT call here runs on one worker.
"""

import argparse
import copy
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))

# isort: split
import brute
import candidates
import rules
from dedupe import IDENTITY
from driver import run
from protocol import Empty, Verdict
from sudoku_kit import cpsat
from sudoku_kit.link_codec import encode_link

BOARD_DOC = json.loads((HERE / "board.json").read_text())
BOARD = rules.lines_from_doc(BOARD_DOC)
N, BOX = 9, (3, 3)


class Hit(NamedTuple):
    """The added lines, in the order the loop added them, and the one
    solution of the board with them."""

    added: tuple
    solution: rules.Solution


def sample(board, rng, time_limit):
    """One solution of `board`'s model, steered by random digit hints, or
    None when the solve hit its time limit."""
    m = board.model.clone()
    m.ClearHints()
    for var in board.x.values():
        m.AddHint(m.GetIntVarFromProtoIndex(var.Index()), rng.randint(1, N))
    solver = cpsat.solver(time_limit)
    status = solver.Solve(m)
    if status not in cpsat.SOLVED:
        return None
    return board._solution(
        [solver.Value(board.x[c]) for c in board.x]
        + [solver.Value(board.h[c]) for c in board.x]
    )


def hint(board, solution):
    """Give the model `solution` as its hint, so a check finds it first."""
    board.model.ClearHints()
    for cell, var in board.x.items():
        board.model.AddHint(var, solution.digits[cell[0]][cell[1]])
        board.model.AddHint(board.h[cell], cell in solution.halvers)


def rank(paths, lines, target, second, pool, rng):
    """`paths` best first: most pool solutions broken per new cell taken,
    then touching a cell whose halver status differs between target and
    second, then shortest, then a random tie-break."""
    differs = target.halvers ^ second.halvers
    scored = []
    for path in paths:
        line = candidates.line_of(path)
        kills = sum(not rules.line_holds(s, line) for s in pool)
        cost = candidates.new_cells(path, lines)
        scored.append(
            (
                -kills / cost,
                not differs.intersection(path),
                len(path),
                rng.random(),
                path,
            )
        )
    scored.sort()
    return [entry[-1] for entry in scored]


class HalverBetweenFinder:
    symmetry = IDENTITY

    def __init__(self, max_cells, pool, time_limit, max_lines, max_seconds, log=None):
        self.max_cells = max_cells
        self.pool = pool
        self.time_limit = time_limit
        self.max_lines = max_lines
        self.max_seconds = max_seconds
        self.log = log
        self.config = {
            "max_cells": max_cells,
            "pool": pool,
            "time_limit": time_limit,
            "max_lines": max_lines,
            "max_seconds": max_seconds,
        }

    def _note(self, **fields):
        if self.log is not None:
            self.log.write(json.dumps(fields) + "\n")
            self.log.flush()

    def propose(self, rng):
        started = time.monotonic()
        board = rules.RuleModel(BOARD)
        target = sample(board, rng, self.time_limit)
        if target is None:
            return Empty(f"timeout sampling a target ({self.time_limit:g}s)")
        added = []
        survivors = set()  # pool solutions every added line holds in
        while True:
            elapsed = time.monotonic() - started
            if len(added) >= self.max_lines or elapsed >= self.max_seconds:
                return Empty(f"budget: {len(added)} lines / {elapsed:.0f} s")
            hint(board, target)
            t0 = time.monotonic()
            check = board.check(time_limit=self.time_limit)
            check_seconds = time.monotonic() - t0
            if check.status == "unique":
                self._note(step=len(added), check_s=check_seconds, status="unique")
                return Hit(tuple(added), check.first)
            if check.status == "timeout":
                return Empty(
                    f"timeout: check after {len(added)} added lines "
                    f"({self.time_limit:g}s)"
                )
            if check.status != "not_unique":
                raise ValueError(
                    f"check returned {check.status} on lines the target obeys"
                )
            second = check.first if check.first != target else check.second
            t0 = time.monotonic()
            lines = BOARD + added
            if candidates.no_space(target, second, lines):
                return Empty(
                    f"no space: after {len(added)} added lines the target and the "
                    "second solution differ only on body cells of drawn lines"
                )
            pool = survivors - {target}
            for _ in range(self.pool - len(pool)):
                drawn = sample(board, rng, self.time_limit)
                if drawn is not None and drawn != target:
                    pool.add(drawn)
            pool.add(second)
            pool_seconds = time.monotonic() - t0
            t0 = time.monotonic()
            paths = candidates.separating_paths(target, second, lines, self.max_cells)
            if not paths:
                return Empty(
                    f"no line of at most {self.max_cells} cells separates the "
                    f"target from the second solution after {len(added)} added lines"
                )
            best = rank(paths, lines, target, second, pool, rng)[0]
            rank_seconds = time.monotonic() - t0
            line = candidates.line_of(best)
            board.add_line(line)
            added.append(line)
            survivors = {s for s in pool if rules.line_holds(s, line)}
            self._note(
                step=len(added),
                check_s=round(check_seconds, 3),
                pool_s=round(pool_seconds, 3),
                rank_s=round(rank_seconds, 3),
                candidates=len(paths),
                pool=len(pool),
                kills=len(pool) - len(survivors),
                new_cells=candidates.new_cells(best, lines),
                free_left=candidates.free_cell_count([*lines, line]),
                line=rules.line_name(line),
            )

    def verify(self, hit):
        lines = list(BOARD)
        for line in hit.added:
            reason = candidates.shape_violation(candidates.path_of(line), lines)
            if reason is not None:
                return Verdict(False, f"{rules.line_name(line)}: {reason}")
            lines.append(line)
        found = brute.solutions(lines, N, BOX, limit=2)
        if len(found) != 1:
            return Verdict(
                False, f"the backtracking check finds {len(found)} solutions"
            )
        digits, halvers = found[0]
        if rules.Solution(digits, halvers) != hit.solution:
            return Verdict(
                False, "the backtracking check's one solution is not the hit's"
            )
        return Verdict(True)

    def record(self, hit):
        return {
            "lines": [
                {
                    "circle_a": rules.cell_name(line.a),
                    "body": [rules.cell_name(c) for c in line.body],
                    "circle_b": rules.cell_name(line.b),
                }
                for line in hit.added
            ],
            "table": [
                f"L{i} | {rules.line_name(line)}"
                for i, line in enumerate(hit.added, start=len(BOARD) + 1)
            ],
            "link": encode_link(link_doc(hit.added)),
            "digits": ["".join(map(str, row)) for row in hit.solution.digits],
            "halvers": [rules.cell_name(c) for c in sorted(hit.solution.halvers)],
        }

    def key(self, hit):
        return tuple(sorted(_canonical(line) for line in hit.added))

    def candidate_from_record(self, record):
        added = tuple(
            rules.Line(
                rules.parse_cell(line["circle_a"]),
                tuple(map(rules.parse_cell, line["body"])),
                rules.parse_cell(line["circle_b"]),
            )
            for line in record["lines"]
        )
        digits = tuple(tuple(int(d) for d in row) for row in record["digits"])
        halvers = frozenset(map(rules.parse_cell, record["halvers"]))
        return Hit(added, rules.Solution(digits, halvers))


def _canonical(line):
    """The line's cells as board indices, read from whichever end is smaller:
    a line and its reverse are one line."""
    path = tuple(r * N + c for r, c in candidates.path_of(line))
    return min(path, path[::-1])


def link_doc(added):
    """Chris's document with `added` drawn as more between lines in his line's
    style, and every cell's entered digits, colours and pencil marks cleared."""
    doc = copy.deepcopy(BOARD_DOC)
    doc["puzzle"]["cells"] = [{} for _ in doc["puzzle"]["cells"]]
    (group,) = [
        c for c in doc["puzzle"]["constraints"] if c.get("type") == rules.BETWEEN_LINE
    ]
    for line in added:
        group["lines"].append([r * N + c for r, c in candidates.path_of(line)])
    return doc


def summary(out):
    """What a hunt in `out` found, as lines of text."""
    events = [
        json.loads(line)
        for line in (out / "progress.jsonl").read_text().splitlines()
        if line.strip()
    ]
    events = [e for e in events if e.get("event") == "seed_done"]
    examples = [
        json.loads(line)
        for line in (out / "examples.jsonl").read_text().splitlines()
        if line.strip()
    ]
    started = datetime.fromisoformat(
        json.loads((out / "run.json").read_text())["start_time"]
    )
    last = datetime.fromtimestamp(
        (out / "progress.jsonl").stat().st_mtime, started.tzinfo
    )
    wall = (last - started).total_seconds()
    seeds = sorted(e["seed"] for e in events)
    span = f"{len(seeds)} seeds" + (f" ({seeds[0]}..{seeds[-1]})" if seeds else "")
    outcomes = Counter(e["outcome"] for e in events)
    text = []
    if examples:
        text.append(f"{len(examples)} hits in {span}, wall clock {wall:.0f} s")
    else:
        text.append(
            f"none found in {span}, wall clock {wall:.0f} s: a search result, "
            "not a proof that no finish exists"
        )
    text.append(
        "outcomes: " + ", ".join(f"{k} {v}" for k, v in sorted(outcomes.items()))
    )
    for e in events:
        if e["outcome"] == "empty":
            text.append(f"seed {e['seed']}: {e.get('empty_reason', 'no reason given')}")
        elif e["outcome"] == "rejected":
            text.append(f"seed {e['seed']}: rejected, {e.get('rejected_reason', '')}")
    for record in examples:
        text.append(f"hit, {len(record['lines'])} added lines: {record['link']}")
        text.extend(f"  {row}" for row in record["table"])
    return text


def main(argv):
    if argv and argv[0] == "summary":
        if len(argv) != 2:
            print("usage: hunt.py summary DIR", file=sys.stderr)
            return 2
        out = Path(argv[1])
        if not (out / "run.json").exists():
            print(
                f"hunt.py summary: {out} holds no hunt (no run.json)", file=sys.stderr
            )
            return 2
        print("\n".join(summary(out)))
        return 0
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--max-cells", type=int, default=8)
    parser.add_argument("--pool", type=int, default=20)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--max-lines", type=int, default=40)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    parser.add_argument("--step-log", type=Path)
    own, rest = parser.parse_known_args(argv)
    log = own.step_log.open("a") if own.step_log else None
    finder = HalverBetweenFinder(
        own.max_cells, own.pool, own.time_limit, own.max_lines, own.max_seconds, log
    )
    return run(finder, rest)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""The halver + between-line hunt (spec #39, #41): add between lines to Chris's
board until it has exactly one (digits, halvers) solution.

One seed is the target-grid loop. Sample a target solution of the board's
lines (random digit hints on a one-worker solve). Then, while the rule check
says `not_unique`, add one line that holds in the target and fails in the
second solution, from `candidates.separating_paths`. Stop at `unique`, a hit.
A seed ends `Empty(reason)` when no line of at most `--max-cells` cells
separates the two, when a solve reaches `--time-limit`, or when the seed's
budget runs out: `--max-lines` lines added and still not unique (the check
after the last permitted line runs first, so a finish at the limit is a
hit), or `--max-seconds` seconds. Every solve of a step gets the smaller of
`--time-limit` and the seconds the seed has left, so no step runs past the
budget by more than the walk and the ranking take. None of those Empty
reasons is a proof that no finish exists.

Ranking: a pool of up to `--pool` distinct sampled solutions of the current
lines, plus the second solution. The pool members an added line leaves alive
stay (they are still solutions), and only as many draws as the line broke
top it back up. A draw that reaches its time limit is left out of the pool
and counted in the step log as `pool_timeouts`; a smaller pool ranks less
well and is never wrong. Cells are the scarce resource (truths note,
section 6), so a candidate scores the pool solutions it breaks per new cell
it takes: its body cells and any circle no line has yet. Ties go to a
candidate touching a cell whose halver status differs between the target
and the second solution, then the shortest, then the seed's rng. Once the
pool holds only the second solution, that score prefers the line that takes
the fewest new cells. A seed whose target and second solution differ only on
body cells of lines already drawn ends `Empty("no space: ...")` at once.

`verify` re-reads a hit with `brute.py`, the backtracking check that shares
no code with the CP-SAT model: exactly one solution, the hit's own, and every
added line a legal shape. The backtracking search stops at
`--verify-seconds` and then refuses the hit with no verdict, never passes
it. `record` writes the line table and a SudokuMaker link
(`sudoku_kit.link_codec.encode_link`): Chris's lines plus the added ones, in
his line style, with every entered digit, colour and pencil mark cleared.
`summary DIR` prints the verified hits, or "none found" with the seeds, the
wall clock and each seed's reason; a `--no-verify` hunt's candidates are
counted as unchecked until `hunt.py verify DIR` has run, and then as hits or
as rejected by its verdicts.

    uv run finders/halver_between/hunt.py --out DIR --seeds 0:3
    uv run finders/halver_between/hunt.py verify DIR
    uv run finders/halver_between/hunt.py summary DIR

The driver's flags (`--out`, `--seeds`, `--no-verify`, ...) are its own
(finders/hunt/driver.py). Every CP-SAT call here runs on one worker and the
seeds run one after another, so `--workers` other than 1 is refused: a hunt
on more cores is several hunt.py processes over disjoint `--seeds` ranges.
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
from driver import _parse_args as driver_args
from driver import run
from protocol import Empty, Verdict
from sudoku_kit.link_codec import encode_link
from verified_io import read_verified

BOARD_DOC = json.loads((HERE / "board.json").read_text())
BOARD = rules.lines_from_doc(BOARD_DOC)
N, BOX = 9, (3, 3)
KNOBS = (
    "max_cells",
    "pool",
    "time_limit",
    "max_lines",
    "max_seconds",
    "verify_seconds",
)


class Hit(NamedTuple):
    """The added lines, in the order the loop added them, and the one
    solution of the board with them."""

    added: tuple
    solution: rules.Solution


def best_line(paths, lines, target, second, pool, rng):
    """The best of `paths`: most pool solutions broken per new cell taken,
    then touching a cell whose halver status differs between target and
    second, then shortest, then a random tie-break."""
    differs = target.halvers ^ second.halvers

    def score(path):
        kills = sum(not rules.line_holds(s, candidates.line_of(path)) for s in pool)
        cost = candidates.new_cells(path, lines)
        return (-kills / cost, not differs.intersection(path), len(path), rng.random())

    return min((*score(path), path) for path in paths)[-1]


class HalverBetweenFinder:
    """The hunt's finder. `start` is lines already added to Chris's board
    before the loop runs: a test starts the loop near a finish with it. They
    are part of every hit's added lines, and the `--max-lines` budget counts
    only the lines the loop adds after them."""

    symmetry = IDENTITY

    def __init__(
        self,
        max_cells,
        pool,
        time_limit,
        max_lines,
        max_seconds,
        verify_seconds,
        log=None,
        start=(),
    ):
        self.max_cells = max_cells
        self.pool = pool
        self.time_limit = time_limit
        self.max_lines = max_lines
        self.max_seconds = max_seconds
        self.verify_seconds = verify_seconds
        self.log = log
        self.start = tuple(start)

    @property
    def config(self):
        return {knob: getattr(self, knob) for knob in KNOBS}

    def _note(self, **fields):
        if self.log is not None:
            self.log.write(json.dumps(fields) + "\n")
            self.log.flush()

    def _ran_out(self, limit, what):
        """The Empty for a solve that reached `limit`: the seed's budget when
        that was what was left, the per-solve `--time-limit` otherwise."""
        if limit < self.time_limit:
            return Empty(f"budget: {self.max_seconds:g} s ran out during {what}")
        return Empty(f"timeout: {what} ({self.time_limit:g}s)")

    def propose(self, rng):
        deadline = time.monotonic() + self.max_seconds

        def limit():
            return min(self.time_limit, deadline - time.monotonic())

        added = list(self.start)
        board = rules.RuleModel(BOARD + added)
        sample_limit = limit()
        target = board.sample(rng, sample_limit)
        if target is None:
            return self._ran_out(sample_limit, "sampling a target")
        survivors = set()  # pool solutions every added line holds in
        while True:
            new = len(added) - len(self.start)
            check_limit = limit()
            if check_limit <= 0:
                return Empty(f"budget: {self.max_seconds:g} s after {new} lines")
            board.hint(target)
            t0 = time.monotonic()
            check = board.check(time_limit=check_limit)
            check_seconds = time.monotonic() - t0
            if check.status == "unique":
                self._note(step=new, check_s=check_seconds, status="unique")
                return Hit(tuple(added), check.first)
            if check.status == "timeout":
                return self._ran_out(check_limit, f"the check after {new} lines")
            if check.status != "not_unique":
                raise ValueError(
                    f"check returned {check.status} on lines the target obeys"
                )
            if new >= self.max_lines:
                return Empty(f"budget: {new} lines added and still not unique")
            second = check.first if check.first != target else check.second
            t0 = time.monotonic()
            lines = BOARD + added
            if candidates.no_space(target, second, lines):
                return Empty(
                    f"no space: after {new} added lines the target and the "
                    "second solution differ only on body cells of drawn lines"
                )
            pool = survivors - {target}
            pool_timeouts = 0
            for _ in range(self.pool - len(pool)):
                draw_limit = limit()
                if draw_limit <= 0:
                    break
                drawn = board.sample(rng, draw_limit)
                if drawn is None:
                    pool_timeouts += 1
                elif drawn != target:
                    pool.add(drawn)
            pool.add(second)
            pool_seconds = time.monotonic() - t0
            t0 = time.monotonic()
            paths = candidates.separating_paths(target, second, lines, self.max_cells)
            if not paths:
                return Empty(
                    f"no line of at most {self.max_cells} cells separates the "
                    f"target from the second solution after {new} added lines"
                )
            best = best_line(paths, lines, target, second, pool, rng)
            rank_seconds = time.monotonic() - t0
            line = candidates.line_of(best)
            board.add_line(line)
            added.append(line)
            survivors = {s for s in pool if rules.line_holds(s, line)}
            self._note(
                step=new + 1,
                check_s=round(check_seconds, 3),
                pool_s=round(pool_seconds, 3),
                rank_s=round(rank_seconds, 3),
                candidates=len(paths),
                pool=len(pool),
                pool_timeouts=pool_timeouts,
                kills=len(pool) - len(survivors),
                new_cells=candidates.new_cells(best, lines),
                free_left=candidates.free_cell_count([*lines, line], N),
                line=rules.line_name(line),
            )

    def verify(self, hit):
        lines = list(BOARD)
        for line in hit.added:
            reason = candidates.shape_violation(candidates.path_of(line), lines)
            if reason is not None:
                return Verdict(False, f"{rules.line_name(line)}: {reason}")
            lines.append(line)
        deadline = time.monotonic() + self.verify_seconds
        try:
            found = brute.solutions(lines, N, BOX, limit=2, deadline=deadline)
        except brute.OutOfTime:
            return Verdict(
                False,
                f"the backtracking check reached its {self.verify_seconds:g} s "
                "limit: no verdict",
            )
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


def _jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _verdicts(out, run_argv, examples):
    """Per example, "hit" (passed `verify`), "unchecked", or the reason
    `hunt.py verify` rejected it. A hunt without `--no-verify` wrote only
    examples that passed `verify`. Raises when verified.jsonl does not cover
    exactly this examples.jsonl."""
    if not driver_args(run_argv).no_verify:
        return ["hit"] * len(examples)
    path = out / "verified.jsonl"
    if not path.exists():
        return ["unchecked"] * len(examples)
    stamp, verdicts = read_verified(path)
    if stamp["verified_examples"] != len(examples):
        raise ValueError(
            f"{path} covers {stamp['verified_examples']} examples and "
            f"examples.jsonl holds {len(examples)}: run `hunt.py verify {out}` again"
        )
    by_record = {
        json.dumps(v["record"], sort_keys=True): (
            "hit" if v["ok"] else v.get("reason", "no reason given")
        )
        for v in verdicts
    }
    found = []
    for record in examples:
        verdict = by_record.get(json.dumps(record, sort_keys=True))
        if verdict is None:
            raise ValueError(
                f"{path} has no verdict for an example of examples.jsonl: "
                f"run `hunt.py verify {out}` again"
            )
        found.append(verdict)
    return found


def summary(out):
    """What a hunt in `out` found, as lines of text."""
    events = [
        e for e in _jsonl(out / "progress.jsonl") if e.get("event") == "seed_done"
    ]
    examples = _jsonl(out / "examples.jsonl")
    run_json = json.loads((out / "run.json").read_text())
    verdicts = _verdicts(out, run_json["argv"], examples)
    hits = [r for r, v in zip(examples, verdicts, strict=True) if v == "hit"]
    unchecked = [r for r, v in zip(examples, verdicts, strict=True) if v == "unchecked"]
    rejected = [
        (r, v)
        for r, v in zip(examples, verdicts, strict=True)
        if v not in ("hit", "unchecked")
    ]
    started = datetime.fromisoformat(run_json["start_time"])
    last = datetime.fromtimestamp(
        (out / "progress.jsonl").stat().st_mtime, started.tzinfo
    )
    wall = (last - started).total_seconds()
    seeds = sorted(e["seed"] for e in events)
    span = f"{len(seeds)} seeds" + (f" ({seeds[0]}..{seeds[-1]})" if seeds else "")
    outcomes = Counter(e["outcome"] for e in events)
    text = []
    if hits:
        text.append(f"{len(hits)} hits in {span}, wall clock {wall:.0f} s")
    elif unchecked or rejected:
        text.append(f"no verified hit in {span}, wall clock {wall:.0f} s")
    else:
        text.append(
            f"none found in {span}, wall clock {wall:.0f} s: a search result, "
            "not a proof that no finish exists"
        )
    if unchecked:
        text.append(
            f"{len(unchecked)} candidates unchecked: the hunt ran with "
            f"--no-verify and `hunt.py verify {out}` has not run"
        )
    if rejected:
        text.append(f"{len(rejected)} candidates rejected by `hunt.py verify`")
    text.append(
        "outcomes: " + ", ".join(f"{k} {v}" for k, v in sorted(outcomes.items()))
    )
    for e in events:
        if e["outcome"] == "empty":
            text.append(f"seed {e['seed']}: {e.get('empty_reason', 'no reason given')}")
        elif e["outcome"] == "rejected":
            reason = e.get("rejected_reason", "no reason given")
            text.append(f"seed {e['seed']}: rejected, {reason}")
    for record in hits:
        text.append(f"hit, {len(record['lines'])} added lines: {record['link']}")
        text.extend(f"  {row}" for row in record["table"])
    for record in unchecked:
        text.append(
            f"unchecked candidate, {len(record['lines'])} added lines: {record['link']}"
        )
        text.extend(f"  {row}" for row in record["table"])
    for record, reason in rejected:
        text.append(f"rejected candidate, {len(record['lines'])} added lines: {reason}")
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
        try:
            text = summary(out)
        except ValueError as error:
            print(f"hunt.py summary: {error}", file=sys.stderr)
            return 2
        print("\n".join(text))
        return 0
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--max-cells", type=int, default=8)
    parser.add_argument("--pool", type=int, default=20)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--max-lines", type=int, default=40)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    parser.add_argument("--verify-seconds", type=float, default=600.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--step-log", type=Path)
    own, rest = parser.parse_known_args(argv)
    if own.workers != 1:
        print(
            f"hunt.py: refusing to run -- --workers {own.workers}: every seed "
            "runs on one CP-SAT worker, one seed after another, so more workers "
            "would sit idle; run several hunt.py processes over disjoint "
            "--seeds ranges instead",
            file=sys.stderr,
        )
        return 2
    log = own.step_log.open("a") if own.step_log else None
    finder = HalverBetweenFinder(
        own.max_cells,
        own.pool,
        own.time_limit,
        own.max_lines,
        own.max_seconds,
        own.verify_seconds,
        log,
    )
    return run(finder, rest)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

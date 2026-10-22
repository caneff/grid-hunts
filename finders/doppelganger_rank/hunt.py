"""The Doppelganger + Full Rank hunt (spec #66, #69): add rank clues to a
board until it has exactly one grid, then drop each added clue it stays
unique without. The halver hunt's target-grid loop
(`finders/halver/halver_hunt.py`), on the shared hunt protocol, which gives
it the output directory, dedupe and resume.

    uv run finders/doppelganger_rank/hunt.py --board BOARD --out DIR --seeds 0:20
    uv run finders/doppelganger_rank/hunt.py verify DIR
    uv run finders/doppelganger_rank/hunt.py summary DIR
    uv run finders/doppelganger_rank/hunt.py links DIR

BOARD is a board file (`check.py`'s docstring gives the format). Its clues
start every seed; its marks are no constraint and are not read (Q11).

One seed: sample a target grid of the board's clues (`RankModel.sample`).
While the check says `not_unique`, add one clue at a free place whose rank
differs between the target and the second solution, valued from the
target, from `separating`'s list; a filter on where a clue may go is a
filter on that list. The clue added is the most restricting one
(`most_restricting`, #79): the fewest grids of a sample of the board's
solutions keep the target's rank at its place, ties broken by the seed's
rng. The sample is `--pool` draws of `RankModel.sample` on the current
clues, the target and repeats left out. Each added clue drops the sampled
grids it rules out, and when fewer than `--pool-floor` are left the next
pick draws a fresh sample. `--pool 0` draws none, so every place ties and
the pick is the seed's rng alone, #69's uniform pick. At `unique`, the hunt
protocol's minimiser (`finders/hunt/minimizer.py`) drops each added clue the
board stays unique without; the board's own clues are never dropped. The
one grid left is the target.

A seed that finds nothing ends `Empty(reason)`, the reason opening with its
class, which `summary` splits the seeds by:

- `infeasible:` the board's clues have no grid, a proof;
- `no separating clue:` the target and a second grid rank alike at every
  free place, so no rank clue can make this target unique, a proof for it;
- `timeout:` a solve reached `--time-limit` (no verdict);
- `capped:` `--max-clues` clues added and still not unique, or the seed's
  `--max-seconds` ran out: a budget, never a proof.

A minimiser solve that times out ends the seed `timeout:` too, since the
hit could then keep a clue it does not need.

`verify` re-reads a hit with the rule reader (`rules.py`): every
Doppelganger rule on its solution, and every clue's rank. Then it re-proves
the board unique on the second model (`reprove.py`, #70), which shares no
code with `model.py`, within `--time-limit`. It refuses a hit the re-proof
finds a second grid for (`not unique: a second grid ...`, naming it), and
one it reaches the time limit on (`timeout: ...`), never read as unique.
`record` writes the
board's size and box, every clue (the board's, then the `added` ones),
the added-clue count and the solution, so a record is read back with no
board file. `summary DIR` lists the verified hits, fewest added clues first,
or "none found"; the seed split; and each seed that found nothing with its
reason. `links DIR` writes a SudokuMaker link per verified hit
(`links.py`). The seeds run one after another, so `--workers` other than 1
is refused.

Every check of a seed is hinted with its target (#72), a warm start that
changes no verdict: on Chris's 9x9 opening it took the add loop's second
grids from 2.1 s to 1.1 s each and found a target's rank twin after 3 to 6
clues in place of 15 or 16 (`docs/research/2026-10-22-doppelganger-rank-
decision-log.md`). Every CP-SAT call runs on one worker but the
minimiser's, which run on `--proof-workers` (1 unless given). They answer
only unique or not, so more workers change no hit; the add loop stays on
one, since the second grid it reads would then change from run to run.
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))

# isort: split
import rules
from check import one_line, read_board
from dedupe import IDENTITY
from driver import run
from links import write_links
from minimizer import strip
from model import RankModel
from protocol import Empty, Verdict
from reprove import reprove
from verified_io import example_verdicts

__all__ = [
    "DEFAULTS",
    "DoppelgangerRankFinder",
    "Hit",
    "most_restricting",
    "separating",
]

DEFAULTS = {
    "time_limit": 30.0,
    "max_clues": 36,
    "max_seconds": 300.0,
    "pool": 16,
    "pool_floor": 4,
    "proof_workers": 1,
}
# The Empty reason's class, as `summary` names it in the split.
CLASSES = {
    "infeasible": "proven infeasible",
    "timeout": "timed out",
    "capped": "capped",
    "no separating clue": "no separating clue",
}


class Hit(NamedTuple):
    """Every clue of the unique board, the board's first and the `added` ones
    after, and its one grid."""

    n: int
    box: tuple
    clues: tuple
    added: int
    solution: tuple


def separating(target, second, box, taken):
    """Every place not in `taken` whose rank differs between the two grids,
    in `rules.places` order: a clue there, valued from the target, rules the
    second grid out."""
    a, b = rules.read(target, box).ranks, rules.read(second, box).ranks
    return [p for p in rules.places(len(target)) if p not in taken and a[p] != b[p]]


def most_restricting(places, target, sample, rng):
    """The place of `places` whose rank in `target` the fewest grids of
    `sample` share, ties broken by `rng`. `target` and each sampled grid are
    ranks by place, as `rules.read` gives them."""

    def score(place):
        share = sum(ranks[place] == target[place] for ranks in sample)
        return share, rng.random()

    return min(places, key=score)


def clue_of(place, rank):
    return {"line": place[0], "end": place[1], "rank": rank}


class DoppelgangerRankFinder:
    symmetry = IDENTITY

    def __init__(
        self,
        board,
        time_limit,
        max_clues,
        max_seconds,
        pool,
        pool_floor,
        proof_workers=1,
    ):
        self.board = board
        self.time_limit = time_limit
        self.max_clues = max_clues
        self.max_seconds = max_seconds
        self.pool = pool
        self.pool_floor = pool_floor
        self.proof_workers = proof_workers
        self.n, self.box, self.clues = None, None, []
        if board is not None:
            self.n, self.box, self.clues, _marks = read_board(Path(board))

    @property
    def config(self):
        return {
            "board": self.board,
            "clues": self.clues,
            "time_limit": self.time_limit,
            "max_clues": self.max_clues,
            "max_seconds": self.max_seconds,
            "pool": self.pool,
            "pool_floor": self.pool_floor,
            "proof_workers": self.proof_workers,
        }

    def target(self, rng, time_limit):
        """The seed's target: `RankModel.sample` on the board's clues."""
        return RankModel(self.n, self.box, self.clues).sample(rng, time_limit)

    def _draw(self, board, rng, limit, target):
        """`pool` draws of `board`'s solutions as ranks by place, the target
        and repeats left out. A draw that reaches its time limit is left
        out: a smaller sample ranks less well and is never wrong."""
        grids = set()
        for _ in range(self.pool):
            draw_limit = limit()
            if draw_limit <= 0:
                break
            drawn = board.sample(rng, draw_limit)
            if drawn.status == "found" and drawn.first != target:
                grids.add(drawn.first)
        return [rules.read(grid, self.box).ranks for grid in sorted(grids)]

    def _ran_out(self, limit, what):
        if limit < self.time_limit:
            return Empty(f"capped: {self.max_seconds:g} s ran out during {what}")
        return Empty(f"timeout: {what} ({self.time_limit:g} s)")

    def propose(self, rng):
        deadline = time.monotonic() + self.max_seconds

        def limit():
            return min(self.time_limit, deadline - time.monotonic())

        sample_limit = limit()
        sample = self.target(rng, sample_limit)
        if sample.status == "infeasible":
            return Empty("infeasible: the board's clues have no grid")
        if sample.status == "timeout":
            return self._ran_out(sample_limit, "sampling a target")
        target = sample.first
        ranks = rules.read(target, self.box).ranks
        board = RankModel(self.n, self.box, self.clues)
        taken = {(c["line"], c["end"]) for c in self.clues}
        added = 0
        pool = []
        while True:
            check_limit = limit()
            if check_limit <= 0:
                return Empty(f"capped: {self.max_seconds:g} s after {added} clues")
            check = board.check(time_limit=check_limit, hint=target)
            if check.status == "unique":
                break
            if check.status == "timeout":
                return self._ran_out(check_limit, f"the check after {added} clues")
            if check.status != "not_unique":
                raise ValueError(
                    f"check returned {check.status} on clues the target keeps"
                )
            if added >= self.max_clues:
                return Empty(f"capped: {added} clues added and still not unique")
            second = check.first if check.first != target else check.second
            places = separating(target, second, self.box, taken)
            if not places:
                return Empty(
                    f"no separating clue: after {added} clues the target and a "
                    "second grid rank alike at every free place"
                )
            if len(pool) < self.pool_floor:
                pool = self._draw(board, rng, limit, target)
            place = most_restricting(places, ranks, pool, rng)
            board.add_clue(clue_of(place, ranks[place]))
            pool = [grid for grid in pool if grid[place] == ranks[place]]
            taken.add(place)
            added += 1
        return self._minimise(board.clues, target, limit)

    def _minimise(self, clues, target, limit):
        timed_out = []

        def unique(trial):
            trial_limit = limit()
            board = RankModel(
                self.n, self.box, [clue_of(p, r) for p, r in trial.items()]
            )
            status = board.check(
                time_limit=max(trial_limit, 0),
                hint=target,
                workers=self.proof_workers,
            ).status
            if status == "timeout":
                timed_out.append(trial_limit)
            return status == "unique"

        items = {(c["line"], c["end"]): c["rank"] for c in clues}
        keep = {(c["line"], c["end"]) for c in self.clues}
        kept = strip(items, keep, unique)
        if timed_out:
            return self._ran_out(min(timed_out), "the minimiser")
        kept_clues = tuple(clue_of(p, r) for p, r in kept.items())
        return Hit(
            self.n, self.box, kept_clues, len(kept_clues) - len(self.clues), target
        )

    def verify(self, hit):
        n = hit.n
        if len(hit.solution) != n or any(len(row) != n for row in hit.solution):
            return Verdict(False, f"the solution is not a {n}x{n} grid")
        places = [(c["line"], c["end"]) for c in hit.clues]
        for place in places:
            if place not in rules.places(n):
                return Verdict(
                    False, f"no place {rules.place_name(place)} on a {n}x{n}"
                )
        if len(set(places)) != len(places):
            return Verdict(False, "two clues at one place")
        reading = rules.read(hit.solution, hit.box)
        broken = reading.violations + reading.broken_clues(hit.clues)
        if broken:
            return Verdict(False, "; ".join(broken))
        proof = reprove(n, hit.box, hit.clues, self.time_limit)
        if proof.status == "not_unique":
            second = proof.second if proof.first == hit.solution else proof.first
            return Verdict(False, f"not unique: a second grid {one_line(second)}")
        if proof.status == "timeout":
            return Verdict(
                False, f"timeout: the re-proof reached {self.time_limit:g} s"
            )
        if proof.status != "unique":
            return Verdict(False, f"the re-proof says {proof.status}")
        if proof.first != hit.solution:
            return Verdict(False, f"the re-proof's one grid is {one_line(proof.first)}")
        return Verdict(True)

    def record(self, hit):
        return {
            "size": hit.n,
            "box": list(hit.box),
            "clues": list(hit.clues),
            "added": hit.added,
            "solution": ["".join(map(str, row)) for row in hit.solution],
        }

    def key(self, hit):
        return tuple(sorted((c["line"], c["end"], c["rank"]) for c in hit.clues))

    def candidate_from_record(self, record):
        solution = tuple(tuple(map(int, row)) for row in record["solution"])
        return Hit(
            record["size"],
            tuple(record["box"]),
            tuple(record["clues"]),
            record["added"],
            solution,
        )


def _jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _hit_line(kind, record):
    clues = ", ".join(
        f"{rules.place_name((c['line'], c['end']))} {c['rank']}"
        for c in record["clues"]
    )
    return (
        f"{kind}, {record['added']} added clues: {clues}"
        f" | solution {' '.join(record['solution'])}"
    )


def summary(out):
    """What a hunt in `out` found, as lines of text."""
    events = [
        e for e in _jsonl(out / "progress.jsonl") if e.get("event") == "seed_done"
    ]
    examples = _jsonl(out / "examples.jsonl")
    run_json = json.loads((out / "run.json").read_text())
    verdicts = example_verdicts(out, run_json["argv"], examples)
    hits = [r for r, v in zip(examples, verdicts, strict=True) if v == "hit"]
    unchecked = [r for r, v in zip(examples, verdicts, strict=True) if v == "unchecked"]
    rejected = [
        (r, v)
        for r, v in zip(examples, verdicts, strict=True)
        if v not in ("hit", "unchecked")
    ]
    seeds = sorted(e["seed"] for e in events)
    span = f"{len(seeds)} seeds" + (f" ({seeds[0]}..{seeds[-1]})" if seeds else "")

    split = Counter()
    for e in events:
        if e["outcome"] == "example":
            split["found"] += 1
        elif e["outcome"] in ("duplicate", "rejected"):
            split[e["outcome"]] += 1
        else:
            reason = e.get("empty_reason", "")
            name = reason.split(":")[0]
            if name not in CLASSES:
                raise ValueError(
                    f"seed {e['seed']} ended with no known reason: {reason!r}"
                )
            split[CLASSES[name]] += 1

    if hits:
        text = [f"{len(hits)} verified hits in {span}"]
    elif unchecked or rejected:
        text = [f"no verified hit in {span}"]
    else:
        text = [f"none found in {span}"]
    text.append(
        f"{span}: found {split['found']}, duplicate {split['duplicate']}, "
        f"proven infeasible {split['proven infeasible']}, "
        f"timed out {split['timed out']}, "
        f"capped {split['capped']} (a budget ran out: no proof), "
        f"no separating clue {split['no separating clue']}, "
        f"rejected {split['rejected']}"
    )
    if unchecked:
        text.append(
            f"{len(unchecked)} candidates unchecked: the hunt ran with "
            f"--no-verify and `hunt.py verify {out}` has not run"
        )
    if rejected:
        text.append(f"{len(rejected)} candidates rejected by `hunt.py verify`")
    for e in events:
        if e["outcome"] == "empty":
            text.append(f"seed {e['seed']}: {e['empty_reason']}")
        elif e["outcome"] == "rejected":
            reason = e.get("rejected_reason", "no reason given")
            text.append(f"seed {e['seed']}: rejected, {reason}")
    text.extend(_hit_line("hit", r) for r in sorted(hits, key=lambda r: r["added"]))
    text.extend(_hit_line("unchecked candidate", r) for r in unchecked)
    for record, reason in rejected:
        text.append(_hit_line("rejected candidate", record) + f" | {reason}")
    return text


def main(argv):
    """`links DIR`, `summary DIR`, or the driver's commands with the finder built from
    its own flags."""
    if argv and argv[0] == "links":
        if len(argv) != 2:
            print("usage: hunt.py links DIR", file=sys.stderr)
            return 2
        out = Path(argv[1])
        try:
            written, skipped = write_links(out)
        except (OSError, ValueError) as error:
            print(f"hunt.py links: {error}", file=sys.stderr)
            return 2
        print(f"wrote {written} links to {out / 'links'}")
        if skipped:
            print(f"{skipped} candidates skipped: not verified hits (`summary {out}`)")
        return 0
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
    parser.add_argument("--board")
    for knob, default in DEFAULTS.items():
        parser.add_argument(
            "--" + knob.replace("_", "-"), type=type(default), default=default
        )
    parser.add_argument("--workers", type=int, default=1)
    own, rest = parser.parse_known_args(argv)
    if own.proof_workers < 1:
        print(
            f"hunt.py: refusing to run -- --proof-workers {own.proof_workers}: "
            "a proof needs at least one CP-SAT worker",
            file=sys.stderr,
        )
        return 2
    if own.workers != 1:
        print(
            f"hunt.py: refusing to run -- --workers {own.workers}: every seed "
            "runs on one CP-SAT worker, one seed after another; run several "
            "hunt.py processes over disjoint --seeds ranges instead",
            file=sys.stderr,
        )
        return 2
    if own.board is None and rest[:1] != ["verify"]:
        print("hunt.py: a hunt needs --board BOARD", file=sys.stderr)
        return 2
    try:
        finder = DoppelgangerRankFinder(
            own.board, **{knob: getattr(own, knob) for knob in DEFAULTS}
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"hunt.py: {own.board}: {error!s}", file=sys.stderr)
        return 2
    return run(finder, rest)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

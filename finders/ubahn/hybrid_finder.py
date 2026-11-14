"""The hybrid finder on the shared hunt protocol (#783): U-Bahn with
Choco-Banana laid over the grid cells and the number cells (spec #781).

Conditions in, valid hybrid grids out, one per seed, repeats removed. The
model is built from the conditions and solved once per seed, steered by the
seed (on cpsat its own random order and direction over the edges, on the
PySAT engines its own random first guess for each edge); nothing is sampled
first and thrown away. The solver is given no outside number. `verify` re-reads every grid
with `hybrid.py`, which states the rules with no solver.

Conditions are flags:

    --circles "CELL CELL ..."  circled cells: each one's value is the size of
                               its region. A grid cell is rKcK, a number cell
                               rK:KIND or cK:KIND (r6:straight, c1:turn).
    --exactly N:KIND:rK       exactly N of a kind in a row (or cK, a
                               column); KIND is turn, straight, branch,
                               cross or blank.
    --blank-strip              a fifth strip of number cells, for blank,
                               outside the cross. Off unless given.
    --min-bananas N            at least N banana regions (#792): N or more
                               separate regions of odd values, over grid
                               cells and number cells together. Every engine
                               builds it into the search; no finished grid
                               is thrown away for it.
    --number-circles K         at least K valid circles on number cells: K
                               or more number cells whose value is the size
                               of their region. A grid cell that is a valid
                               circle counts for nothing (#794).
    --battenberg "CELL CELL ..."  windows that carry a Battenberg marking
                               (spec #20): each is a checkerboard window,
                               its diagonal cells sharing a parity of value
                               and its side-by-side pairs differing. A
                               window is a 2x2 of board cells, grid cells,
                               number cells or both, named by its top-left
                               cell as `--circles` names a cell. A window
                               that is not wholly on the board is refused.
    --battenberg-only          the negative constraint: every window with no
                               marking is not a checkerboard window, the
                               windows in the number strips included. Both
                               flags are on the PySAT engines only; `--engine
                               cpsat` refuses them by name.
    --engine pysat-lazy        the solver the rules are written on: cpsat
                               (`hybrid_model.py`, connectivity as a flow),
                               pysat-lazy (`hybrid_sat.py`, a grid whose
                               network is in several parts is cut and the
                               solve goes on) or pysat-propagator (the same
                               clauses, with a propagator that refuses a
                               network broken apart before the grid is
                               full). pysat-lazy unless given.
    --timeout SECONDS          the limit on one solve, 60 unless given.
                               `classify` makes up to two solves: on cpsat
                               each has the whole limit, on the PySAT
                               engines one limit covers both.

    uv run finders/ubahn/hybrid_finder.py --out DIR --seeds 0:50 --workers 1 \\
        --rows 7 --cols 7 \\
        --circles "r6:straight r6:turn r7:straight r7:turn"
    uv run finders/ubahn/hybrid_finder.py verify DIR

`classify` takes the same conditions and says whether they have no grid,
exactly one, or more than one, in the uniqueness check's words, with the
first grid found drawn under the answer:

    uv run finders/ubahn/hybrid_finder.py classify --rows 4 --cols 4 \\
        --circles "c1:turn r2c4" [--workers 1]

`--workers` is cpsat's: the PySAT engines run on one thread whatever it says.

    infeasible: no grid
    unique: exactly one grid
    not_unique: more than one grid
    timeout: time limit reached

A time limit reached is always `timeout`, never one of the other three.

`climb` raises K in `--number-circles K` until no grid reaches it (#794). It
starts at `--from K` (0 unless given; `--number-circles` itself is refused),
hunts seed 0 for a grid with at least K, counts the grid's valid circles on
number cells with the rule reader, and asks next for one more than that
count. Each step is a hunt directory of its own, `DIR/at-least-K`, which
`verify` and `render` read, and a line of `DIR/climb.jsonl`, written as the
step ends (a last line cut short by a kill is dropped on the rerun). It stops
at the first K with no grid, or at the first step that reaches `--timeout`. Only the first is a proof: the maximum is called proven
when "at least one more" came back as no grid, and a time limit reached is a
best found with no proof.

A rerun into the same DIR, under the same conditions, engine, limit and
`--from`, goes on from the last step written; under any other it is refused,
and so is a second climb while one is running there. A climb that has ended
stays ended: one a time limit stopped is taken up again in a new DIR, with
`--from K` and a larger `--timeout`.

    uv run finders/ubahn/hybrid_finder.py climb --rows 7 --cols 7 \
        --timeout 3600 --out DIR

    at least 0: found, 3 valid circles on number cells, 0.1 s
    at least 4: found, 4 valid circles on number cells, 0.2 s
    at least 5: infeasible, no grid, 1.5 s
    maximum 4: proven on pysat-lazy, at least 5 has no grid
    best grid: DIR/at-least-4 (seed 0)

`fewest-markings` finds the fewest Battenberg markings that leave exactly
one grid with the negative constraint on (spec #29). The negative constraint
is always on and the command chooses the markings, so `--battenberg` is
refused; every other condition is fixed background to every solve. It
classifies no markings, then every set of 1 window, then every set of 2,
each set as `classify` would, and stops at the first size that has a
`unique` set, so every smaller set has an answer before the minimum is
named. `--max-size K` (3 unless given) is the last size it tries.
`--workers N` (1 unless given) splits one size's sets over N processes.

Each set tried is a line of `DIR/sets.jsonl`, written as its answer lands:
its windows, the answer, and whether it was solved or copied from its
mirror. When the conditions keep the reflection in the main diagonal (the
hunt's own dedupe rule, below) one set of each mirror pair is solved and
both are listed, each naming the other. A rerun into the same DIR, under the
same conditions, engine and limit, solves only the sets with no line; under
any other it is refused, and so is a second run while one is running there.
A last line a write cut short is dropped and solved again; any other line
that does not read is refused, naming it. Each unique set of the smallest
size is written, with the one grid its solve found, as seed 0 of a hunt
directory of its own under DIR, named for its windows, which `verify`,
`render` and `links` read; a rerun leaves a directory already written as it
is.

A size is finished even when a set reaches `--timeout`: the set is named in
the report and never read as "no grid". The minimum is called proven only
when no set of its size or smaller reached the limit. `--engine cpsat` is
refused: it has no model of a marking.

    uv run finders/ubahn/hybrid_finder.py fewest-markings --rows 4 --cols 4 \
        --out DIR [--max-size K] [--workers N]

    size 0: 0 unique, 1 not_unique, 0 infeasible, 0 timeout
    size 1: 0 unique, 0 not_unique, 33 infeasible, 0 timeout
    size 2: 0 unique, 0 not_unique, 528 infeasible, 0 timeout
    size 3: 2 unique, 0 not_unique, 5454 infeasible, 0 timeout
    minimum 3: proven on pysat-lazy, 2 unique sets of 3 markings
    unique: c1:turn c2:turn r3c1, mirror r1:turn r1c3 r2:turn: DIR/c1-turn+c2-turn+r3c1 (seed 0)
    unique: r1:turn r1c3 r2:turn, mirror c1:turn c2:turn r3c1: DIR/r1-turn+r1c3+r2-turn (seed 0)

`render DIR` is the driver's too (the finder's `render`) and draws every
example of the hunt in DIR as a picture,
`DIR/renders/<seed>.png` (`hybrid_render.py`, #791): the board with every
outside number, the network, chocolate in one colour and a tint per banana,
and a heavy ring in a second colour on every circle that is one of the
grid's conditions, with no ring on any other valid circle. A small
checkerboard symbol sits at the centre of every
checkerboard window of the grid, heavier and in the second colour on a window
that is a Battenberg marking of the hunt's conditions; a record from before
the condition is drawn as having no markings. A rerun replaces every picture
there. `--seed N --png FILE`
draws that one example to FILE instead. `--blank-strip` draws the fifth strip
on a record of a hunt that had none; a grid that is no hybrid grid on the
board drawn is refused and nothing is written.

    uv run finders/ubahn/hybrid_finder.py render DIR [--blank-strip]
    uv run finders/ubahn/hybrid_finder.py render DIR --seed N --png FILE

`links DIR` is the driver's (`hunt links DIR`, with this finder's `link_text`)
and writes a Penpa+ link per verified example of the hunt in `DIR` to
`DIR/links/<seed>.txt` (`penpa.py`, #795): the grid with the circles and the
numbers you supply and nothing else shown, drawn in the dotted grid under the
combined rules. `--circles "CELLS"` are the cells that carry a circle, grid
cells or number cells; `--numbers "CELLS"` are the number cells whose outside
number is printed, every other number cell left empty. One set of flags
applies to every example of the directory, so a hunt run with the same
`--circles` condition makes every example carry them. With neither flag the
board shows no circle and no number. A circled number cell shows its number
only if it is also in `--numbers`. The link's answer check is the plain
link's: the drawn lines, nothing else. `--battenberg "CELLS"` are the
windows that carry a Battenberg marking, each by its top-left cell: Penpa+'s
checkerboard symbol on the corner the window's four cells share, and one
sentence more of rules. `--battenberg-only` adds a second sentence, that
every checkerboard symbol is given, and is refused on an example with a
checkerboard window left unmarked. `--blank-strip` draws the fifth strip
on a record of a hunt that had none. A circle that is not valid on the grid
(its value is not its region's size), a marked window that is no
checkerboard window of the grid or is not wholly on the board, a number cell
off the board, a grid cell as a given number, or a grid that is no hybrid
grid on the board drawn, is refused by name and nothing is written. A rerun replaces every link there.
A link is never printed: the command reports the directory. The link does not
say whether the givens leave one solution; `classify` answers that for the
circles (it is given no outside number).

    uv run finders/ubahn/hybrid_finder.py links DIR --circles "r2c3 c1:turn" \
        --numbers "r1:cross c1:turn" [--blank-strip] \
        [--battenberg "r1c3 r1:turn"] [--battenberg-only]

The board's one symmetry is the reflection in the main diagonal, which swaps
the row and column number cells; a left-right mirror image is another
puzzle, since the number cells sit above and on the left only. A hunt
dedupes under that reflection when the board is square, every circle's
image is circled, every marked window's image is marked and there is no
kind-count condition, and under nothing otherwise.

The driver's flags (`--out`, `--seeds`, `--workers`, ...) are its own
(finders/hunt/driver.py).
"""

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
# isort: split
import hunt_files
import hybrid
import network
from driver import run
from hybrid_engines import DEFAULT_ENGINE, ENGINES, SAID, HybridFinder, LinkShown
from hybrid_searches import climb, fewest_markings
from ubahn_finder import DEFAULT_SIDE, DEFAULT_TIMEOUT


class Usage(ValueError):
    """A refusal of the flags as a whole, said as `hybrid_finder: <why>`."""


class Command(NamedTuple):
    """One subcommand: `run(own, rest)` returns the exit code, `rest` being
    the words from the subcommand's name on. A ValueError from a command that
    `refuses` is its refusal, said as `hybrid_finder <name>: <why>`; from any
    other it is a crash."""

    run: object
    refuses: bool = True


def parse_conditions(args):
    """The `hybrid.Conditions` the flags name. Raises ValueError, naming the
    flag, on a board with no network, a cell or condition that does not
    parse, one that is off the board, a number of banana regions under 1, a
    count of number-cell circles below 0, or a Battenberg marking whose
    window is not wholly on the board."""
    rows, cols = args.rows, args.cols
    if rows < 2 or cols < 2:
        raise ValueError("the smallest board with a network is 2x2")
    try:
        circles = hybrid.parse_circles(args.circles, rows, cols, args.blank_strip)
    except ValueError as e:
        raise ValueError(f"--circles: {e}") from e
    exactly = None
    if args.exactly is not None:
        try:
            exactly = network.Exactly.parse_on(args.exactly, rows, cols)
        except ValueError as e:
            raise ValueError(f"--exactly: {e}") from e
    hybrid.check_min_bananas(args.min_bananas)
    if args.number_circles < 0:
        raise ValueError(f"--number-circles is 0 or more, got {args.number_circles}")
    try:
        marked = hybrid.parse_windows(args.battenberg, rows, cols, args.blank_strip)
    except ValueError as e:
        raise ValueError(f"--battenberg: {e}") from e
    return hybrid.Conditions(
        rows,
        cols,
        circles,
        exactly,
        args.blank_strip,
        args.min_bananas or 0,
        args.number_circles,
        marked,
        args.battenberg_only,
    )


def classify(conditions, engine, timeout, workers):
    status, found = ENGINES[engine].classify(
        conditions, time_limit=timeout, workers=workers
    )
    lines = [f"{status}: {SAID[status]}"]
    if found is not None:
        lines += hybrid.drawing(
            found,
            conditions.rows,
            conditions.cols,
            conditions.circles,
            conditions.blank_strip,
        )
    return lines


def parse_cells(flag, text):
    try:
        return frozenset(map(hybrid.parse_cell, text.split()))
    except ValueError as e:
        raise ValueError(f"{flag}: {e}") from e


def _parser():
    """The flags every subcommand shares; a subcommand's own are its parser's."""
    parser = argparse.ArgumentParser(prog="hybrid_finder", add_help=False)
    parser.add_argument("--rows", type=int, default=DEFAULT_SIDE)
    parser.add_argument("--cols", type=int, default=DEFAULT_SIDE)
    parser.add_argument("--circles", default="", metavar="CELLS")
    parser.add_argument("--numbers", default="", metavar="CELLS")
    parser.add_argument("--exactly", metavar="N:KIND:rK")
    parser.add_argument("--blank-strip", action="store_true")
    parser.add_argument("--min-bananas", type=int, metavar="N")
    parser.add_argument("--number-circles", type=int, default=0, metavar="K")
    parser.add_argument("--battenberg", default="", metavar="CELLS")
    parser.add_argument("--battenberg-only", action="store_true")
    parser.add_argument("--engine", default=DEFAULT_ENGINE, choices=ENGINES)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    return parser


def _conditions(own):
    """The conditions the flags name, for a subcommand that solves. Raises
    Usage, naming the flag, on any `parse_conditions` refuses and on a
    Battenberg flag with `--engine cpsat`."""
    try:
        conditions = parse_conditions(own)
        # A new hybrid condition is written on the PySAT engines only
        # (Chris's ruling of 2026-10-12): cpsat has no model of these.
        for flag, given in (
            ("--battenberg", conditions.battenberg),
            ("--battenberg-only", conditions.battenberg_only),
        ):
            if given and own.engine == "cpsat":
                raise ValueError(
                    f"{flag} is on the PySAT engines only: --engine cpsat has "
                    f"no model of it"
                )
    except ValueError as e:
        raise Usage(e) from e
    return conditions


def _record_only(own, name):
    """Raises Usage when a flag of the markings is given to a subcommand that
    reads them off each record."""
    for flag, given in (
        ("--battenberg", own.battenberg),
        ("--battenberg-only", own.battenberg_only),
    ):
        if given:
            raise Usage(
                f"{flag} is not for `{name}`, which reads a record's own markings"
            )


def _verify(own, rest):
    _record_only(own, "verify")
    return run(HybridFinder(hybrid.Conditions(own.rows, own.cols)), rest)


def _render(own, rest):
    _record_only(own, "render")
    mine = argparse.ArgumentParser(prog="hybrid_finder render")
    mine.add_argument("dir")
    mine.add_argument("--seed", type=int)
    mine.add_argument("--png", metavar="FILE")
    args = mine.parse_args(rest[1:])
    if (args.seed is None) != (args.png is None):
        raise ValueError(
            "--seed N and --png FILE go together: "
            + ("--seed needs --png" if args.png is None else "--png needs --seed")
        )
    finder = HybridFinder(
        hybrid.Conditions(DEFAULT_SIDE, DEFAULT_SIDE, blank_strip=own.blank_strip)
    )
    if args.seed is None:
        return run(finder, ["render", args.dir])
    # One picture to a file of the caller's: the driver's `render` is the set.
    records = dict(hunt_files.read_examples(Path(args.dir)))
    if args.seed not in records:
        raise ValueError(f"seed {args.seed} has no example in {args.dir}")
    try:
        image = finder.render(finder.candidate_from_record(records[args.seed]))
    except ValueError as e:
        raise ValueError(f"seed {args.seed}: {e}") from e
    hunt_files.write_image_atomic(Path(args.png), image)
    print(f"wrote the picture of seed {args.seed} to {args.png}")
    return 0


def _links(own, rest):
    mine = argparse.ArgumentParser(prog="hybrid_finder links")
    mine.add_argument("dir")
    args = mine.parse_args(rest[1:])
    shown = LinkShown(
        parse_cells("--circles", own.circles),
        parse_cells("--numbers", own.numbers),
        parse_cells("--battenberg", own.battenberg),
        own.battenberg_only,
    )
    finder = HybridFinder(
        hybrid.Conditions(DEFAULT_SIDE, DEFAULT_SIDE, blank_strip=own.blank_strip),
        shown=shown,
    )
    code = run(finder, ["links", args.dir])
    if code == 0:
        given = f"{len(shown.circles)} circles and {len(shown.numbers)} numbers"
        if shown.battenberg:
            given = (
                f"{len(shown.circles)} circles, {len(shown.numbers)} numbers and "
                f"{len(shown.battenberg)} Battenberg markings"
            )
        print(f"{given} given")
    return code


def _classify(own, rest):
    conditions = _conditions(own)
    mine = argparse.ArgumentParser(prog="hybrid_finder classify")
    mine.add_argument("--workers", type=int, default=1)
    workers = mine.parse_args(rest[1:]).workers
    print("\n".join(classify(conditions, own.engine, own.timeout, workers)))
    return 0


def _climb(own, rest):
    conditions = _conditions(own)
    mine = argparse.ArgumentParser(prog="hybrid_finder climb")
    mine.add_argument("--out", required=True, metavar="DIR")
    mine.add_argument("--from", type=int, dest="start", metavar="K")
    args = mine.parse_args(rest[1:])
    if conditions.number_circles:
        raise ValueError(
            "climb raises K itself: start it at K with --from K, not --number-circles"
        )
    if args.start is not None and args.start < 0:
        raise ValueError(f"--from is 0 or more, got {args.start}")
    climb(conditions, own.engine, own.timeout, args.out, args.start)
    return 0


def _fewest_markings(own, rest):
    conditions = _conditions(own)
    mine = argparse.ArgumentParser(prog="hybrid_finder fewest-markings")
    mine.add_argument("--out", required=True, metavar="DIR")
    mine.add_argument("--max-size", type=int, default=3, metavar="K")
    mine.add_argument("--workers", type=int, default=1, metavar="N")
    args = mine.parse_args(rest[1:])
    if own.engine == "cpsat":
        raise ValueError(
            "--engine cpsat has no model of a Battenberg marking: "
            "fewest-markings is on the PySAT engines only"
        )
    if conditions.battenberg:
        raise ValueError(
            "--battenberg is not for fewest-markings, which chooses the markings itself"
        )
    if args.max_size < 0:
        raise ValueError(f"--max-size is 0 or more, got {args.max_size}")
    if args.workers < 1:
        raise ValueError(f"--workers is 1 or more, got {args.workers}")
    fewest_markings(
        conditions, own.engine, own.timeout, args.out, args.max_size, args.workers
    )
    return 0


def _hunt(own, rest):
    """Anything that is no subcommand of ours is the driver's: a hunt, or its
    own subcommands (`summary`, ...)."""
    return run(HybridFinder(_conditions(own), own.engine, own.timeout), rest)


# The one table of subcommands. `verify` and the driver's hunt let a
# ValueError through as a crash, as `classify` does.
COMMANDS = {
    "verify": Command(_verify, refuses=False),
    "render": Command(_render),
    "links": Command(_links),
    "classify": Command(_classify, refuses=False),
    "climb": Command(_climb),
    "fewest-markings": Command(_fewest_markings),
}
HUNT = Command(_hunt, refuses=False)


def main(argv):
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    own, rest = _parser().parse_known_args(argv)
    name = rest[0] if rest and rest[0] in COMMANDS else None
    command = COMMANDS[name] if name else HUNT
    try:
        if own.numbers and name != "links":
            raise Usage("--numbers is for `links` only")
        return command.run(own, rest)
    except Usage as e:
        print(f"hybrid_finder: {e}", file=sys.stderr)
    except ValueError as e:
        if not command.refuses:
            raise
        print(f"hybrid_finder {name}: {e}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

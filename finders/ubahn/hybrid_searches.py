"""The hybrid finder's two searches, each a loop of hunts or solves that
writes a log of its own: `climb` raises the number of valid circles on number
cells until no grid reaches it, `fewest_markings` finds the fewest Battenberg
markings that leave one grid. Both take the engines as a mapping
(`engines=`, `hybrid_engines.ENGINES` unless given), so a test can call them
with a fake engine (spec #117, #133). The command line is `hybrid_finder.py`.
"""

import fcntl
import itertools
import json
import multiprocessing
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
# isort: split
import hunt_files
import hybrid
from dedupe import IDENTITY
from driver import run
from hybrid_engines import (
    EMPTY_INFEASIBLE,
    EMPTY_TIMEOUT,
    ENGINES,
    SAID,
    Candidate,
    HybridFinder,
    condition_symmetry,
    mirror,
)

# The one seed every step of a climb hunts.
CLIMB_SEED = 0
# The one seed a unique set's example is written under by `fewest-markings`.
SET_SEED = 0


def _step(finder, seed, out):
    """Hunt one seed into `out`, a hunt directory of its own. Returns
    `(status, count)`: "found" with the rule reader's count of the grid's
    valid circles on number cells, or "infeasible" or "timeout" with None.
    Raises ValueError when the driver refuses the hunt or the seed ends any
    other way, a grid `verify` rejected among them."""
    argv = ["--out", str(out), f"--seeds={seed}:{seed + 1}", "--workers", "1"]
    if run(finder, argv):
        raise ValueError(f"the hunt in {out} was refused")
    event = json.loads((out / "progress.jsonl").read_text().splitlines()[-1])
    if event["outcome"] == "example":
        ((_, record),) = hunt_files.read_examples(out)
        return "found", len(record["number_cell_circles"])
    status = {EMPTY_INFEASIBLE: "infeasible", EMPTY_TIMEOUT: "timeout"}.get(
        event.get("empty_reason")
    )
    if event["outcome"] != "empty" or status is None:
        raise ValueError(f"the hunt in {out} ended on {event}")
    return status, None


def _steps_on_file(out, lines, asked, start):
    """The steps a climb wrote to `out/climb.jsonl`, checked as a chain: each
    is this climb's (`asked`), the first is at `start` when one is given, each
    later one is at one more than the count before it, and only the last may
    be other than "found". Raises ValueError, naming the step, on a log that
    is not one: two climbs wrote into it, or it was edited."""
    steps = [json.loads(line) for line in lines if line]
    for i, step in enumerate(steps):
        k = step["at_least"]
        if step["config"] != asked:
            raise ValueError(f"{out} holds a climb under {step['config']}")
        if i == 0 and start not in (None, k):
            raise ValueError(f"{out} holds a climb from {k}: --from {start} is another")
        if i and (steps[i - 1]["status"] != "found" or k != steps[i - 1]["count"] + 1):
            raise ValueError(
                f"{out}/climb.jsonl: the step at least {k} does not follow "
                f"the step before it"
            )
    return steps


def climb(conditions, engine, timeout, out, start=None, engines=ENGINES):
    """Raise K in "at least K valid circles on number cells" from `start`
    (0 when None) until no grid reaches it or a step reaches the time limit,
    printing each step as it ends and then the answer. Each step is a hunt of
    seed `CLIMB_SEED` in `out/at-least-K` and a line of `out/climb.jsonl`; a
    rerun goes on from the last line written. One climb at a time holds
    `out`. Raises ValueError on a step `_step` refuses, when another climb
    holds `out`, or when its log is not this climb's (`_steps_on_file`)."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    asked = {
        **HybridFinder(conditions, engine, timeout, engines).config,
        "number_circles": None,
        "seed": CLIMB_SEED,
    }

    def say(step):
        k, status = step["at_least"], step["status"]
        what = (
            f"{step['count']} valid circles on number cells"
            if status == "found"
            else SAID[status]
        )
        took = (
            "time not on record" if step["seconds"] is None else f"{step['seconds']} s"
        )
        print(f"at least {k}: {status}, {what}, {took}", flush=True)

    with (out / "climb.jsonl").open("a+") as log:
        # The lock is on the log itself, held until the answer is printed:
        # two climbs in one directory would each write steps the other
        # then reads as its own.
        try:
            fcntl.flock(log, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError(f"another climb is running in {out}") from None
        log.seek(0)
        steps = _steps_on_file(out, log.read().splitlines(), asked, start)
        for step in steps:
            say(step)
        while not steps or steps[-1]["status"] == "found":
            k = steps[-1]["count"] + 1 if steps else start or 0
            step_dir = out / f"at-least-{k}"
            # A hunt directory that already holds its seed's answer is read
            # back, not solved again, so its time is not this run's to state.
            read_back = (step_dir / "summary.json").is_file() and json.loads(
                (step_dir / "summary.json").read_text()
            ).get("seeds_done")
            began = time.monotonic()
            finder = HybridFinder(
                conditions.asking(number_circles=k), engine, timeout, engines
            )
            status, count = _step(finder, CLIMB_SEED, step_dir)
            steps.append(
                {
                    "at_least": k,
                    "status": status,
                    "count": count,
                    "seconds": (
                        None if read_back else round(time.monotonic() - began, 1)
                    ),
                    "dir": step_dir.name,
                    "config": asked,
                }
            )
            log.write(json.dumps(steps[-1]) + "\n")
            log.flush()
            say(steps[-1])
    *found, last = steps
    proven = last["status"] == "infeasible"
    stopped = (
        f"at least {last['at_least']} "
        f"{'has no grid' if proven else 'reached the time limit'}"
    )
    if not found:
        print(f"no grid found: {stopped} on {engine}")
        return
    best = found[-1]
    if proven:
        print(f"maximum {best['count']}: proven on {engine}, {stopped}")
    else:
        print(f"best found {best['count']}: not proven, {stopped} on {engine}")
    print(f"best grid: {out / best['dir']} (seed {CLIMB_SEED})")


def _set_name(names):
    """A set of windows, given by their names, as the report names it."""
    return " ".join(names) or "no markings"


class _HeldGrid(HybridFinder):
    """The finder of a hunt whose one seed is a grid already in hand: a
    unique set's grid as `classify` found it, written as an ordinary example
    with no second solve."""

    def __init__(self, conditions, engine, timeout, found, engines):
        super().__init__(conditions, engine, timeout, engines)
        self.found = found

    def propose(self, rng):
        return Candidate(self.conditions, self.found)


def _classify_sets(conditions, engine, timeout, sets, mirrored, path, engines):
    """Classify each set of windows as the conditions' markings and append
    its line to the per-set file at `path` as the answer lands; a unique
    set's line carries its one grid as a hunt's record. With `mirrored`, a
    set that is not its own mirror is followed by its mirror's line, copied
    from it, in the same write."""
    with path.open("a") as log:
        for windows in sets:
            began = time.monotonic()
            marked = conditions.asking(battenberg=windows)
            status, found = engines[engine].classify(
                marked, time_limit=timeout, workers=1
            )
            solved = {
                "size": len(windows),
                "windows": [hybrid.cell_name(window) for window in windows],
                "status": status,
                "how": "solved",
                "mirror": None,
                "seconds": round(time.monotonic() - began, 3),
            }
            if status == "unique":
                finder = HybridFinder(marked, engine, timeout, engines)
                solved["record"] = finder.record(Candidate(marked, found))
            lines = [solved]
            image = mirror(windows)
            if mirrored and image != windows:
                solved["mirror"] = [hybrid.cell_name(window) for window in image]
                lines.append(_mirror_line(conditions, engine, timeout, solved, engines))
            log.write("".join(json.dumps(line) + "\n" for line in lines))
            log.flush()


def _mirror_line(conditions, engine, timeout, solved, engines):
    """The line of a solved set's mirror, copied from the solved set's own:
    the same answer, and a unique set's grid reflected with it."""
    line = {
        **solved,
        "windows": solved["mirror"],
        "how": "mirror",
        "mirror": solved["windows"],
        "seconds": None,
    }
    if solved["status"] == "unique":
        image = conditions.asking(battenberg=map(hybrid.parse_cell, line["windows"]))
        finder = HybridFinder(image, engine, timeout, engines)
        found = finder.candidate_from_record(solved["record"]).network
        reflected = frozenset((mirror([a])[0], mirror([b])[0]) for a, b in found)
        line["record"] = finder.record(Candidate(image, reflected))
    return line


def _sets_on_file(path, asked):
    """{a set of windows: its line} from the per-set file at `path`, whose
    first line is the run's heading. Raises ValueError, naming the file,
    when the heading does not read or is another run's (`asked` is this
    one's config), or when a line is no set's line: it does not read, its
    answer is none of `SAID`'s words, or it is a unique set's with no grid."""
    heading, *lines = path.read_text().splitlines()
    try:
        held = json.loads(heading)["config"]
    except (ValueError, KeyError, TypeError) as e:
        raise ValueError(f"{path}: line 1 is no run's heading: {e!r}") from e
    if held != asked:
        raise ValueError(f"{path.parent} holds a run under {held}")
    tried = {}
    for number, line in enumerate(lines, 2):
        try:
            entry = json.loads(line)
            if entry["status"] not in SAID:
                raise ValueError(f"its answer is {entry['status']!r}")
            if entry["status"] == "unique" and "record" not in entry:
                raise ValueError("a unique set's line with no grid")
            if not {"mirror", "how"} <= entry.keys():
                raise ValueError("it does not say how it was answered")
            tried[frozenset(map(hybrid.parse_cell, entry["windows"]))] = entry
        except (ValueError, KeyError, TypeError) as e:
            raise ValueError(f"{path}: line {number} is no set's line: {e!r}") from e
    return tried


def _mend(log, path, conditions, engine, timeout, asked, engines):
    """Make the per-set file ready to read. A new file gets the run's
    heading. In one a write cut short, the last line with no end is dropped
    and a solved set whose mirror's line is missing gets that line copied
    again. Any other line that does not read is refused (`_sets_on_file`)."""
    text = path.read_text()
    if not text.endswith("\n"):
        log.truncate(text.rfind("\n") + 1)
    if "\n" not in text:
        log.write(json.dumps({"config": asked}) + "\n")
        log.flush()
    tried = _sets_on_file(path, asked)
    for line in list(tried.values()):
        image = line["mirror"] and frozenset(map(hybrid.parse_cell, line["mirror"]))
        if line["how"] == "solved" and image and image not in tried:
            log.write(
                json.dumps(_mirror_line(conditions, engine, timeout, line, engines))
                + "\n"
            )
    log.flush()


def fewest_markings(
    conditions, engine, timeout, out, max_size, workers, engines=ENGINES
):
    """Find the fewest Battenberg markings that leave exactly one grid under
    the negative constraint, with `conditions` as fixed background: classify
    every set of one size before any of the next, from no markings up to
    `max_size`, and stop at the first size with a unique set. One size's
    sets are split over `workers` processes. Each set is a line of
    `out/sets.jsonl`, and a rerun solves only the sets with no line. Prints
    each size's counts as the size ends, then every set that reached the
    time limit, the answer, and each unique set of the smallest size with
    the hunt directory under `out` that holds its grid. One run at a time
    holds `out`. Raises ValueError when another run holds `out`, when its
    file is another run's or does not read (`_sets_on_file`), when a worker
    dies, or on an example hunt `_step` refuses."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    conditions = conditions.asking(battenberg_only=True)
    asked = HybridFinder(conditions, engine, timeout, engines).config
    board = hybrid.board_cells(conditions.rows, conditions.cols, conditions.blank_strip)
    windows = hybrid.windows(board)
    mirrored = condition_symmetry(conditions) != IDENTITY
    path = out / "sets.jsonl"
    # A worker process is sent its engine by pickle, and the `cpsat` entry is
    # a module, which cannot be: it gets the one engine it solves with.
    mine = {engine: engines[engine]}
    timed, unique, size = [], [], 0
    with path.open("a+") as log:
        # Held until the answer is printed, as a climb holds its own log.
        try:
            fcntl.flock(log, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError(f"another run is in {out}") from None
        log.seek(0)
        _mend(log, path, conditions, engine, timeout, asked, engines)
        for size in range(max_size + 1):
            sets = list(itertools.combinations(windows, size))
            tried = _sets_on_file(path, asked)
            # Of a mirror pair the set that sorts first is the one solved.
            todo = [
                chosen
                for chosen in sets
                if frozenset(chosen) not in tried
                and not (mirrored and mirror(chosen) < chosen)
            ]
            crew = [
                multiprocessing.Process(
                    target=_classify_sets,
                    args=(conditions, engine, timeout, share, mirrored, path, mine),
                )
                for share in (todo[i::workers] for i in range(workers))
                if share
            ]
            for worker in crew:
                worker.start()
            for worker in crew:
                worker.join()
            if any(worker.exitcode for worker in crew):
                raise ValueError(f"a worker died at size {size}: rerun into {out}")
            tried = _sets_on_file(path, asked)
            try:
                lines = [tried[frozenset(chosen)] for chosen in sets]
            except KeyError as e:
                missing = _set_name(map(hybrid.cell_name, sorted(e.args[0])))
                raise ValueError(f"{path}: no line for {missing}") from e
            counts = {
                word: sum(1 for line in lines if line["status"] == word)
                for word in SAID
            }
            print(
                f"size {size}: " + ", ".join(f"{counts[word]} {word}" for word in SAID),
                flush=True,
            )
            timed += [line for line in lines if line["status"] == "timeout"]
            unique = [line for line in lines if line["status"] == "unique"]
            if unique:
                break
        for line in timed:
            print(f"time limit reached: {_set_name(line['windows'])}")
        sets_timed = f"{len(timed)} set{'' if len(timed) == 1 else 's'}"
        if not unique:
            if timed:
                print(
                    f"no unique set found up to {max_size} on {engine}: not "
                    f"proven, {sets_timed} reached the time limit"
                )
            else:
                print(f"no unique set up to {max_size} on {engine}")
            return
        if timed:
            print(
                f"smallest found {size}: not proven on {engine}, {sets_timed} of "
                f"{size} or fewer markings reached the time limit"
            )
        else:
            print(
                f"minimum {size}: proven on {engine}, {len(unique)} unique "
                f"set{'' if len(unique) == 1 else 's'} of {size} markings"
            )
        for line in unique:
            name = _set_name(line["windows"])
            if line["mirror"]:
                name += f", mirror {_set_name(line['mirror'])}"
            example = out / (
                "+".join(window.replace(":", "-") for window in line["windows"])
                or "no-markings"
            )
            # An example already written is left as it is: the hunt driver
            # holds a hunt directory to the `--out` it was first given.
            if not (example / "examples.jsonl").is_file():
                marked = conditions.asking(
                    battenberg=map(hybrid.parse_cell, line["windows"])
                )
                finder = HybridFinder(marked, engine, timeout, engines)
                found = finder.candidate_from_record(line["record"]).network
                _step(
                    _HeldGrid(marked, engine, timeout, found, engines),
                    SET_SEED,
                    example,
                )
            print(f"unique: {name}: {example} (seed {SET_SEED})")

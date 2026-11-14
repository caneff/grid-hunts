"""The hybrid finder's two searches (`climb`, `fewest_markings`) called with a
fake engine (spec #117, #133), and the split of `hybrid_finder.py` into
engines, searches and a command line that nothing else imports.

The fake engine answers from one grid held in hand, so no solver runs behind
a search under test: `grid` hands it back while it meets the asked number of
circles, `classify` calls a set of markings unique when it is exactly the
grid's checkerboard windows.

    uv run finders/ubahn/test_ubahn_hybrid_searches.py
"""

import contextlib
import io
import json
import random
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import hybrid
import hybrid_engines
import hybrid_searches
import network
from cli_checks import check, finish

ROWS, COLS = 3, 4  # not square, so no mirror pair is solved once for two
# Seed 1 of the real engine: a 3x4 grid with 2 valid circles on number cells
# and 2 checkerboard windows.
_, HELD = hybrid_engines.ENGINES["pysat-lazy"].grid(
    hybrid.Conditions(ROWS, COLS), random.Random(1), time_limit=30
)
BOARD = hybrid.values(HELD, ROWS, COLS, False)
CIRCLES = len(hybrid.number_cell_circles(BOARD))
WINDOWS = frozenset(hybrid.checkerboard_windows(BOARD))


class Fake:
    """An engine with one grid in hand, as `hybrid_engines.ENGINES` holds one."""

    def __init__(self):
        self.asked = []

    def grid(self, conditions, rng, *, time_limit):
        self.asked.append(conditions)
        if conditions.number_circles > CIRCLES:
            return hybrid.Sampled("infeasible", None)
        return hybrid.Sampled("found", HELD)

    def classify(self, conditions, *, time_limit, workers):
        # A worker process, so a refusal here is the worker dying.
        if not conditions.battenberg_only:
            raise AssertionError("fewest_markings left the negative constraint off")
        if conditions.battenberg == WINDOWS:
            return hybrid.Classified("unique", HELD)
        return hybrid.Classified("not_unique", HELD)


def said(call, *args, **kwargs):
    """What `call` printed."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        call(*args, **kwargs)
    return out.getvalue()


def main():
    # --- climb -----------------------------------------------------------------
    fake = Fake()
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "climb"
        text = said(
            hybrid_searches.climb,
            hybrid.Conditions(ROWS, COLS),
            "fake",
            5,
            out,
            engines={"fake": fake},
        )
        check(
            f"climb: the maximum is the fake's {CIRCLES}, proven on 'fake'",
            f"maximum {CIRCLES}: proven on fake" in text,
        )
        check(
            "climb: it asked for no circles, then for one more than the grid holds",
            [c.number_circles for c in fake.asked] == [0, CIRCLES + 1],
        )
        steps = [
            json.loads(line)
            for line in (out / "climb.jsonl").read_text().split("\n")
            if line
        ][1:]  # the run log's heading is the first line
        check(
            "climb: the log holds the found step, then the infeasible one",
            [s["status"] for s in steps] == ["found", "infeasible"],
        )

    # A climb log from before the run log (#134) has no heading: its first
    # line is a step. A rerun refuses it for that cause and leaves it as it is.
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "old"
        out.mkdir()
        old_log = json.dumps(
            {"at_least": 0, "status": "found", "count": 1, "seconds": 0.1,
             "dir": "at-least-0", "config": {"rows": ROWS}}
        ) + "\n"  # fmt: skip
        (out / "climb.jsonl").write_text(old_log)
        try:
            hybrid_searches.climb(
                hybrid.Conditions(ROWS, COLS), "fake", 5, out, engines={"fake": Fake()}
            )
            message = None
        except ValueError as e:
            message = str(e)
        check(
            f"climb: a log from before the run log is refused, naming the cause "
            f"({message!r})",
            message is not None
            and "predates the run log" in message
            and "new --out" in message
            and (out / "climb.jsonl").read_text() == old_log,
        )

    # --- fewest_markings -------------------------------------------------------
    fake = Fake()
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "fewest"
        size = len(WINDOWS)
        text = said(
            hybrid_searches.fewest_markings,
            hybrid.Conditions(ROWS, COLS),
            "fake",
            5,
            out,
            size,
            2,
            engines={"fake": fake},
        )
        check(
            f"fewest_markings: the minimum is the grid's {size} windows, proven",
            f"minimum {size}: proven on fake, 1 unique set of {size} markings" in text,
        )
        check(
            "fewest_markings: the unique set's example directory was written",
            any((p / "examples.jsonl").is_file() for p in out.iterdir() if p.is_dir()),
        )

    # --- Conditions.asking -----------------------------------------------------
    base = hybrid.Conditions(ROWS, COLS, circles=frozenset({(0, 0)}))
    check(
        "Conditions.asking changes only the fields named",
        base.asking(number_circles=3) == base._replace(number_circles=3)
        and base.asking(battenberg=[(0, 1)]).battenberg == frozenset({(0, 1)})
        and base.asking(battenberg_only=True).circles == base.circles,
    )

    mirror_line_checks()

    # --- no tool or test imports the command line ------------------------------
    imports_cli = [
        p.name
        for p in sorted(HERE.glob("*.py"))
        if p.name != "hybrid_finder.py"
        and any(
            line.split()[:2] in (["import", "hybrid_finder"], ["from", "hybrid_finder"])
            for line in p.read_text().splitlines()
        )
    ]
    check(
        f"nothing imports hybrid_finder, the command line ({imports_cli})",
        not imports_cli,
    )
    finish()


def mirror_line_checks():
    """`_mirror_line` copies a solved set's line to its mirror's: the same
    answer, the windows swapped, and a unique set's grid reflected with it."""
    asked = hybrid.Conditions(4, 4)
    grid = network.from_drawing(["┌┐┌┐", "└┼┤│", "┌┼┤│", "└┘└┘"])
    # Not a diagonal pair of windows: (0, 1) and its image (1, 0) are two sets.
    windows, image = [(0, 1)], [(1, 0)]
    solved_conditions = asked.asking(battenberg=map(tuple, windows))
    finder = hybrid_engines.HybridFinder(solved_conditions)
    solved = {
        "size": 1,
        "windows": [hybrid.cell_name(w) for w in windows],
        "status": "unique",
        "how": "solved",
        "mirror": [hybrid.cell_name(w) for w in image],
        "seconds": 1.5,
        "record": finder.record(hybrid_engines.Candidate(solved_conditions, grid)),
    }
    line = hybrid_searches._mirror_line(asked, "cpsat", 10.0, solved, {})
    reflected = frozenset(hybrid_engines.mirror(edge) for edge in grid)
    check(
        "_mirror_line: the mirror's line names the image's windows, says it was "
        "copied, and points back at the solved set",
        (line["windows"], line["how"], line["mirror"], line["seconds"])
        == (solved["mirror"], "mirror", solved["windows"], None)
        and line["status"] == "unique"
        and line["size"] == 1,
    )
    mirrored = finder.candidate_from_record(line["record"])
    check(
        "_mirror_line: a unique set's record holds the grid reflected, asked "
        "under the image's windows",
        mirrored.network == reflected
        and mirrored.network != grid
        and line["record"]["battenberg"] == solved["mirror"],
    )
    check(
        "_mirror_line: the solved line is left as it was",
        solved["how"] == "solved" and solved["seconds"] == 1.5,
    )
    other = {**solved, "status": "not_unique"}
    del other["record"]
    line = hybrid_searches._mirror_line(asked, "cpsat", 10.0, other, {})
    check(
        "_mirror_line: a set with no unique grid copies its answer and no record",
        line["status"] == "not_unique"
        and "record" not in line
        and line["windows"] == solved["mirror"],
    )


# A search starts its workers by `multiprocessing`, which imports this file again.
if __name__ == "__main__":
    main()

"""Board questions (spec #65, #94, #95): ask a fixed board whether it has any
solution, whether it has exactly one, and whether a mark holds in every
solution, for any CP-SAT finder.

    uv run finders/query/query.py FINDER BOARD QUESTION... --out DIR
        [--condition FILE]... [--marks FILE] [--time-limit S]

FINDER is a finder's name, read as `finders/<name>/query_finder.py`, or the
path of a `.py` file. Each QUESTION is `feasible`, `unique` or `forced`,
answered in order, each solve capped at `--time-limit` seconds (10 unless
given). `forced` gives one answer per condition: each `--condition` file's
(`conditions.py` gives the JSON form), then each entry of the `--marks` file,
a `marks.json` list the finder's `mark` hook translates. Run it under
`job-run`: it never opens a window.

The finder module's `load(board_path)` reads BOARD and returns the finder:

    clues                       the board's clue list
    size                        (rows, columns) of its picture
    build(clues)                a fresh CP-SAT model and its variables by
                                name, {name: IntVar}
    cell_of(name)               the (row, column) a variable belongs to
    draw(canvas, solution)      the board's clues and, unless `solution` is
                                None, its values, onto a `GridCanvas`
    link(solution)              optional: a SudokuMaker short link of the
                                board with `solution`, None for the board alone
    mark(entry)                 optional: a `marks.json` entry as a condition
                                (`conditions.py`), for `--marks`

A solution is a {name: value} dict. Each answer is written the moment it is
found: its picture `DIR/<k>-<question>.png` (k counts answers from 1), its links (when the finder has
the hook) one per line in `DIR/<k>-<question>.txt`, then its line of
`DIR/answers.jsonl`, so a line is on disk only with its picture and links;
each file is renamed into place whole, so a killed run leaves none half
written.
A line carries the question, its status, its label, its solutions and the
names of its picture and links. The label is `complete` when the status is
a verdict and `capped` when a solve reached its time limit: a timeout is
never read as feasible, infeasible or unique.

- feasible: `feasible` with one solution, or `infeasible`; the picture is
  that solution, or the board alone.
- forced: `held` when no solution breaks the condition (one solve with it
  negated, infeasible), or `not_held` with the solution that breaks it; the
  picture is that counterexample, or the board alone, with every cell the
  condition reads ringed. The line carries the condition, and the entry as
  `mark` when it came from `--marks`.
- unique: the five statuses of `sudoku_kit.uniqueness` (an `invalid` model
  raises); on `not_unique` the picture is both solutions side by side with
  the cells that differ shaded.

The last line printed is `pictures: <path> ...`, one path per answer.
"""

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

from ortools.sat.python import cp_model
from PIL import Image
from sudoku_kit import cpsat
from sudoku_kit.uniqueness import check_uniqueness

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hunt"))

# isort: split
import conditions
from render import GridCanvas

QUESTIONS = ("feasible", "unique", "forced")
DEFAULT_TIME_LIMIT = 10.0
VERDICTS = {"feasible", "infeasible", "unique", "not_unique", "held", "not_held"}
CELL = 64
MARGIN = 24  # around each board, and between two boards side by side
DIFF_TINT = (255, 90, 90)
DIFF_ALPHA = 0.45
MARK_COLOR = (200, 0, 200)
MARK_RADIUS = 0.44  # of a cell: outside a halver line's end ring (0.38)
MARK_WIDTH = 4


def load_finder(name, board_path):
    """The finder FINDER names, loaded on BOARD."""
    path = Path(name)
    if path.suffix != ".py":
        path = HERE.parent / name / "query_finder.py"
    if not path.is_file():
        raise ValueError(f"no finder {name!r}: {path} is not a file")
    spec = importlib.util.spec_from_file_location(f"query_finder_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load(board_path)


def solve(question, model, variables, time_limit):
    """`found` with one solution, `infeasible`, or `timeout`."""
    solver = cpsat.solver(time_limit)
    status = solver.Solve(model)
    if status in cpsat.SOLVED:
        return "found", [{k: solver.Value(v) for k, v in variables.items()}]
    if status == cp_model.INFEASIBLE:
        return "infeasible", []
    if status == cpsat.UNKNOWN:
        return "timeout", []
    raise ValueError(f"{question} got solver status {solver.StatusName(status)}")


def feasible(finder, time_limit):
    status, solutions = solve("feasible", *finder.build(finder.clues), time_limit)
    return ("feasible" if status == "found" else status), solutions


def forced(finder, cond, time_limit):
    model, variables = finder.build(finder.clues)
    model.AddBoolAnd([conditions.literal(model, variables, conditions.Not(cond))])
    status, solutions = solve("forced", model, variables, time_limit)
    return {"found": "not_held", "infeasible": "held"}.get(status, status), solutions


def unique(finder, time_limit):
    model, variables = finder.build(finder.clues)
    result = check_uniqueness(model, variables, time_limit=time_limit, workers=1)
    if result.status == "invalid":
        raise ValueError("unique: the finder's model is invalid")
    return result.status, [s for s in (result.first, result.second) if s]


ASK = {"feasible": feasible, "unique": unique}


def board_image(finder, solution, shaded=(), ringed=()):
    rows, cols = finder.size
    canvas = GridCanvas(rows, cols, cell=CELL, margin=MARGIN)
    finder.draw(canvas, solution)
    tint = Image.new("RGB", (CELL, CELL), DIFF_TINT)
    for r, c in shaded:
        x, y = MARGIN + c * CELL, MARGIN + r * CELL
        cell = canvas.image.crop((x, y, x + CELL, y + CELL))
        canvas.image.paste(Image.blend(cell, tint, DIFF_ALPHA), (x, y))
    for r, c in ringed:
        canvas.circle(r, c, color=MARK_COLOR, width=MARK_WIDTH, radius_frac=MARK_RADIUS)
    return canvas.image


def picture(finder, solutions, ringed=()):
    """One board with the `ringed` cells ringed, or two side by side with the
    cells that differ shaded."""
    if len(solutions) < 2:
        return board_image(finder, solutions[0] if solutions else None, (), ringed)
    first, second = solutions
    differ = {finder.cell_of(k) for k in first if first[k] != second[k]}
    left = board_image(finder, first, differ)
    right = board_image(finder, second, differ)
    image = Image.new("RGB", (2 * left.width + MARGIN, left.height), "white")
    image.paste(left, (0, 0))
    image.paste(right, (left.width + MARGIN, 0))
    return image


def write_answer(
    out, k, question, status, solutions, finder, time_limit, ringed=(), fields=None
):
    """Picture, links, then the answers.jsonl line, which carries `fields`
    too; the picture's path."""
    stem = f"{k}-{question}"
    picture_path = out / f"{stem}.png"
    partial = out / f"{stem}.partial.png"
    picture(finder, solutions, ringed).save(partial)
    partial.replace(picture_path)
    line = {
        "question": question,
        "status": status,
        "label": "complete" if status in VERDICTS else "capped",
        "time_limit": time_limit,
        **(fields or {}),
        "solutions": solutions,
        "picture": picture_path.name,
    }
    link = getattr(finder, "link", None)
    if link is not None:
        links = [link(s) for s in solutions] or [link(None)]
        links_path = out / f"{stem}.txt"
        partial = out / f"{stem}.partial.txt"
        partial.write_text("".join(f"{x}\n" for x in links))
        partial.replace(links_path)
        line["links"] = links_path.name
    with (out / "answers.jsonl").open("a") as f:
        f.write(json.dumps(line) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return picture_path


def positive(text):
    value = float(text)
    if not value > 0:
        raise argparse.ArgumentTypeError(f"--time-limit must be above 0, got {text}")
    return value


def main(argv):
    parser = argparse.ArgumentParser(
        prog="query.py", description=__doc__.split("\n\n")[0]
    )
    parser.add_argument("finder")
    parser.add_argument("board", type=Path)
    parser.add_argument("questions", nargs="+", choices=QUESTIONS, metavar="question")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--condition", type=Path, action="append", default=[])
    parser.add_argument("--marks", type=Path)
    parser.add_argument("--time-limit", type=positive, default=DEFAULT_TIME_LIMIT)
    args = parser.parse_args(argv)
    if (args.out / "answers.jsonl").exists():
        parser.error(f"{args.out / 'answers.jsonl'} exists: give a fresh --out")
    asks_forced = "forced" in args.questions
    if asks_forced and not (args.condition or args.marks):
        parser.error("forced needs --condition or --marks")
    if not asks_forced and (args.condition or args.marks):
        parser.error("--condition and --marks need the forced question")
    try:
        finder = load_finder(args.finder, args.board)
        marks = read_marks(finder, args.condition, args.marks) if asks_forced else []
    except ValueError as error:
        parser.error(str(error))
    args.out.mkdir(parents=True, exist_ok=True)
    pictures = []
    for question in args.questions:
        for status, solutions, ringed, fields in answer(
            question, finder, marks, args.time_limit
        ):
            print(f"{question}: {status}", flush=True)
            pictures.append(
                write_answer(
                    args.out,
                    len(pictures) + 1,
                    question,
                    status,
                    solutions,
                    finder,
                    args.time_limit,
                    ringed,
                    fields,
                )
            )
    print("pictures: " + " ".join(map(str, pictures)))
    return 0


def read_marks(finder, condition_files, marks_file):
    """Each forced condition, as (condition, its line's fields): the
    condition files', then the marks file's entries through the finder's
    `mark` hook. Raises a ValueError naming a file that does not read, or a
    variable the finder's model lacks, before any question is asked."""
    marks = []
    for path in condition_files:
        try:
            cond = conditions.from_json(json.loads(path.read_text()))
        except ValueError as error:
            raise ValueError(f"{path}: {error}") from None
        marks.append((cond, {"condition": conditions.to_json(cond)}))
    if marks_file is not None:
        hook = getattr(finder, "mark", None)
        if hook is None:
            raise ValueError("this finder has no mark hook: give --condition")
        for entry in json.loads(marks_file.read_text()):
            cond = hook(entry)
            fields = {"condition": conditions.to_json(cond), "mark": entry}
            marks.append((cond, fields))
    _, variables = finder.build(finder.clues)
    for cond, _ in marks:
        missing = [k for k in conditions.keys(cond) if k not in variables]
        if missing:
            raise ValueError(f"no variable {missing[0]!r} in the finder's model")
    return marks


def answer(question, finder, marks, time_limit):
    """Each answer to `question`: (status, solutions, ringed cells, fields)."""
    if question != "forced":
        status, solutions = ASK[question](finder, time_limit)
        yield status, solutions, (), None
        return
    for cond, fields in marks:
        status, solutions = forced(finder, cond, time_limit)
        ringed = [finder.cell_of(k) for k in conditions.keys(cond)]
        yield status, solutions, ringed, fields


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

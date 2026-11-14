"""Board questions (spec #65, #94, #95, #96, #97): ask a fixed board whether it
has any solution, whether it has exactly one, whether a mark holds in every
solution, what its solutions are, how high a named value can reach, and
which clues it stays unique without, for any CP-SAT finder.

    uv run finders/query/query.py FINDER BOARD QUESTION... --out DIR
        [--condition FILE]... [--marks FILE] [--limit N] [--max KEY]
        [--time-limit S]

FINDER is a finder's name, read as `finders/<name>/query_finder.py`, or the
path of a `.py` file. Each QUESTION is `feasible`, `unique`, `forced`,
`enumerate`, `max` or `drop-one`, answered in order, each solve capped at `--time-limit`
seconds (10 unless given). `forced` gives one answer per condition: each `--condition` file's
(`conditions.py` gives the JSON form), then each entry of the `--marks` file,
a `marks.json` list the finder's `mark` hook translates. Run it under
`job-run`: it never opens a window.

The finder module's `load(board_path)` reads BOARD and returns the finder:

    clues                       the board's clue list
    size                        (rows, columns) of its picture
    build(clues)                a fresh CP-SAT model and its variables by
                                name, {name: IntVar}
    cell_of(name)               the (row, column) a variable belongs to
    draw(canvas, solution, marked)
                                the board's clues and, unless `solution` is
                                None, its values, onto a `GridCanvas`; each
                                clue whose index is in `marked` in a second
                                colour
    link(solution)              optional: a SudokuMaker short link of the
                                board with `solution`, None for the board alone
    mark(entry)                 optional: a `marks.json` entry as a condition
                                (`conditions.py`), for `--marks`

A solution is a {name: value} dict. Each answer is written the moment it is
found: its picture `DIR/<k>-<question>.png` (k counts answers from 1), its links (when the finder has
the hook) one per line in `DIR/<k>-<question>.txt`, then its line of
`DIR/answers.jsonl`, so a line is on disk only with its picture and links.
A link that fails to mint (the network, the app refusing it) never loses
the answer: its line carries `link_error`, the reason, in place of `links`,
the reason is printed, and the run goes on.
The picture and links are each written by `hunt_files`' atomic writes, so a
failed save leaves no temp file; the line is appended in one write and flushed to disk, so a
killed run leaves whole lines and no half-written file.
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
- enumerate: one `solution` answer per solution, written as it is found,
  its picture that solution; then one closing answer carrying the `count`
  found: `exhausted` (complete) when a further solve was infeasible, `limit`
  (capped) when `--limit` solutions (10 unless given) were found, `timeout`
  (capped). Reaching the limit is capped even when no other solution exists:
  the run never asked.
- max: the largest value of the variable `--max` names, climbed with `Gt`,
  each step a fresh model asked for a solution above the best so far. Each
  improving solution is a `witness` answer (capped), written as it is
  found, so a killed climb keeps its best; then one closing answer: `max`
  (complete) only when the last step came back infeasible; `timeout`
  (capped) when a step reached its time limit, with the best found so far;
  `infeasible` when the board has no solution. Each line carries `key` and
  `value` (None with no solution); the picture is the witness solution, the
  value in a caption below the board.
- drop-one: for each clue in turn, the board rebuilt through `build` with
  that clue left out and asked `unique`: one answer per clue, carrying its
  index `clue` (from 0), `droppable` when the board stays unique without
  it, `needed` when it does not (or has no solution), `timeout` (capped)
  otherwise; the picture is the board, the clue in the second colour when
  droppable. Then one closing answer carrying `droppable` and `capped`, the
  clue indices of each: `done` (complete) when every clue got a verdict,
  `timeout` (capped) when any did not. A capped clue is never droppable.
  Its picture is the board with every droppable clue in the second colour.

The last line printed is `pictures: <path> ...`, one path per answer, the
picture to show first first: each closing `max` and `drop-one` answer's
(the best witness, the board with every droppable clue in the second
colour), then the rest in the order found.

A caller that holds its own model, built, hinted or grown line by line, asks
it through `unique_on(model, variables, time_limit)` and `forced_on(model,
variables, cond, time_limit)`, the same questions without a finder; the
halver layer's `uniqueness` and `holds` do (#98).
"""

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import NamedTuple

from ortools.sat.python import cp_model
from PIL import Image, ImageDraw, ImageFont
from sudoku_kit import cpsat
from sudoku_kit.uniqueness import check_uniqueness

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hunt"))

# isort: split
import conditions
import hunt_files
from render import DEFAULT_FONT, GridCanvas

QUESTIONS = ("feasible", "unique", "forced", "enumerate", "max", "drop-one")
DEFAULT_TIME_LIMIT = 10.0
DEFAULT_LIMIT = 10
VERDICTS = {
    *("feasible", "infeasible", "unique", "not_unique", "held", "not_held"),
    *("solution", "exhausted", "max", "droppable", "needed", "done"),
}
CAPTION_HEIGHT = 48
CAPTION_FONT_SIZE = 28
CELL = 64
MARGIN = 24  # around each board, and between two boards side by side
DIFF_TINT = (255, 90, 90)
DIFF_ALPHA = 0.45
MARK_COLOR = (200, 0, 200)
MARK_RADIUS = 0.44  # of a cell: outside a halver line's end ring (0.38)
MARK_WIDTH = 4


class Answer(NamedTuple):
    """One answer to a question: its status and solutions, the fields its
    line carries beside them, and how its picture is drawn (`ringed` cells,
    `marked` clues, a `caption`). A `summary` answer's picture is named
    first on the last printed line."""

    status: str
    solutions: tuple = ()
    fields: dict | None = None
    ringed: tuple = ()
    caption: str | None = None
    marked: tuple = ()
    summary: bool = False


def load_finder(name, board_path):
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
    """`found` with one solution, `infeasible`, or `timeout`; any other solver
    status raises ValueError."""
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
    return Answer("feasible" if status == "found" else status, solutions)


def forced_on(model, variables, cond, time_limit):
    """`forced` on a model the caller built: `held`, `not_held` with the
    solution that breaks `cond`, or `timeout`. Puts `cond`'s negation on
    `model`: hand over a fresh model or a clone."""
    model.AddBoolAnd([conditions.literal(model, variables, conditions.Not(cond))])
    status, solutions = solve("forced", model, variables, time_limit)
    return {"found": "not_held", "infeasible": "held"}.get(status, status), solutions


def forced(finder, cond, fields, time_limit):
    status, solutions = forced_on(*finder.build(finder.clues), cond, time_limit)
    ringed = tuple(finder.cell_of(k) for k in conditions.keys(cond))
    return Answer(status, solutions, fields, ringed)


def unique_on(model, variables, time_limit):
    """`unique` on a caller-built model: `sudoku_kit.uniqueness`'s statuses
    with the solutions found; `invalid` raises. Leaves `model` unchanged."""
    result = check_uniqueness(model, variables, time_limit=time_limit, workers=1)
    if result.status == "invalid":
        raise ValueError("unique: the finder's model is invalid")
    return result.status, [s for s in (result.first, result.second) if s]


def unique(finder, time_limit):
    return Answer(*unique_on(*finder.build(finder.clues), time_limit))


def build_with(finder, conds):
    model, variables = finder.build(finder.clues)
    for cond in conds:
        model.AddBoolAnd([conditions.literal(model, variables, cond)])
    return model, variables


def enumerate_solutions(finder, limit, time_limit):
    found = []
    while len(found) < limit:
        excluded = [
            conditions.Not(
                conditions.All(tuple(conditions.Eq(k, v) for k, v in s.items()))
            )
            for s in found
        ]
        status, solutions = solve(
            "enumerate", *build_with(finder, excluded), time_limit
        )
        if status != "found":
            closing = "exhausted" if status == "infeasible" else status
            yield Answer(closing, fields={"count": len(found)})
            return
        found.append(solutions[0])
        yield Answer("solution", solutions)
    yield Answer("limit", fields={"count": len(found)})


def climb(finder, key, time_limit):
    def answer(status, best):
        value = best[0][key] if best else None
        caption = None
        if value is not None:
            capped = status not in VERDICTS
            caption = f"{key} = {value}" + (", capped" if capped else "")
        return Answer(status, best, {"key": key, "value": value}, caption=caption)

    best = []
    while True:
        above = [conditions.Gt(key, best[0][key])] if best else []
        status, solutions = solve("max", *build_with(finder, above), time_limit)
        if status != "found":
            break
        best = solutions
        yield answer("witness", best)
    if status == "infeasible":
        status = "max" if best else "infeasible"
    yield answer(status, best)._replace(summary=True)


DROP_VERDICT = {"unique": "droppable", "not_unique": "needed", "infeasible": "needed"}


def drop_one(finder, time_limit):
    droppable, capped = [], []
    for i in range(len(finder.clues)):
        rest = finder.clues[:i] + finder.clues[i + 1 :]
        status, _ = unique_on(*finder.build(rest), time_limit)
        verdict = DROP_VERDICT.get(status, status)
        if verdict == "droppable":
            droppable.append(i)
        elif verdict != "needed":
            capped.append(i)
        yield Answer(
            verdict,
            fields={"clue": i},
            caption=f"clue {i}: {verdict}",
            marked=(i,) if verdict == "droppable" else (),
        )
    caption = "droppable: " + (", ".join(map(str, droppable)) or "none")
    if capped:
        caption += ", capped"
    yield Answer(
        "timeout" if capped else "done",
        fields={"droppable": droppable, "capped": capped},
        caption=caption,
        marked=tuple(droppable),
        summary=True,
    )


def board_image(finder, solution, shaded=(), ringed=(), marked=()):
    rows, cols = finder.size
    canvas = GridCanvas(rows, cols, cell=CELL, margin=MARGIN)
    finder.draw(canvas, solution, marked)
    tint = Image.new("RGB", (CELL, CELL), DIFF_TINT)
    for r, c in shaded:
        x, y = MARGIN + c * CELL, MARGIN + r * CELL
        cell = canvas.image.crop((x, y, x + CELL, y + CELL))
        canvas.image.paste(Image.blend(cell, tint, DIFF_ALPHA), (x, y))
    for r, c in ringed:
        canvas.circle(r, c, color=MARK_COLOR, width=MARK_WIDTH, radius_frac=MARK_RADIUS)
    return canvas.image


def captioned(image, caption):
    out = Image.new("RGB", (image.width, image.height + CAPTION_HEIGHT), "white")
    out.paste(image, (0, 0))
    font = ImageFont.truetype(DEFAULT_FONT, CAPTION_FONT_SIZE)
    centre = (image.width / 2, image.height + CAPTION_HEIGHT / 2)
    ImageDraw.Draw(out).text(centre, caption, fill="black", font=font, anchor="mm")
    return out


def picture(finder, solutions, ringed=(), caption=None, marked=()):
    if caption is not None:
        return captioned(picture(finder, solutions, ringed, marked=marked), caption)
    if len(solutions) < 2:
        solution = solutions[0] if solutions else None
        return board_image(finder, solution, (), ringed, marked)
    first, second = solutions
    differ = {finder.cell_of(k) for k in first if first[k] != second[k]}
    left = board_image(finder, first, differ)
    right = board_image(finder, second, differ)
    image = Image.new("RGB", (2 * left.width + MARGIN, left.height), "white")
    image.paste(left, (0, 0))
    image.paste(right, (left.width + MARGIN, 0))
    return image


def write_answer(out, k, question, answer, finder, time_limit):
    stem = f"{k}-{question}"
    picture_path = out / f"{stem}.png"
    image = picture(
        finder, answer.solutions, answer.ringed, answer.caption, answer.marked
    )
    hunt_files.write_image_atomic(picture_path, image)
    line = {
        "question": question,
        "status": answer.status,
        "label": "complete" if answer.status in VERDICTS else "capped",
        "time_limit": time_limit,
        **(answer.fields or {}),
        "solutions": answer.solutions,
        "picture": picture_path.name,
    }
    link = getattr(finder, "link", None)
    if link is not None:
        try:
            links = [link(s) for s in answer.solutions] or [link(None)]
        except (OSError, ValueError) as error:
            line["link_error"] = f"{type(error).__name__}: {error}"
            print(f"{stem}: no link: {line['link_error']}", file=sys.stderr)
        else:
            links_path = out / f"{stem}.txt"
            hunt_files.write_text_atomic(links_path, "".join(f"{x}\n" for x in links))
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


def count(text):
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"--limit must be at least 1, got {text}")
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
    parser.add_argument("--limit", type=count)
    parser.add_argument("--max", dest="max_key", metavar="KEY")
    parser.add_argument("--time-limit", type=positive, default=DEFAULT_TIME_LIMIT)
    args = parser.parse_args(argv)
    if (args.out / "answers.jsonl").exists():
        parser.error(f"{args.out / 'answers.jsonl'} exists: give a fresh --out")
    asks_forced = "forced" in args.questions
    if asks_forced and not (args.condition or args.marks):
        parser.error("forced needs --condition or --marks")
    if not asks_forced and (args.condition or args.marks):
        parser.error("--condition and --marks need the forced question")
    if args.limit is not None and "enumerate" not in args.questions:
        parser.error("--limit needs the enumerate question")
    if ("max" in args.questions) != (args.max_key is not None):
        parser.error(
            "max needs --max"
            if args.max_key is None
            else "--max needs the max question"
        )
    try:
        finder = load_finder(args.finder, args.board)
        marks = read_marks(finder, args.condition, args.marks) if asks_forced else []
        keys = [k for cond, _ in marks for k in conditions.keys(cond)]
        if args.max_key is not None:
            keys.append(args.max_key)
        if keys:
            conditions.require(finder.build(finder.clues)[1], keys)
    except ValueError as error:
        parser.error(str(error))
    args.out.mkdir(parents=True, exist_ok=True)
    pictures, summaries = [], []
    options = {
        "marks": marks,
        "limit": args.limit or DEFAULT_LIMIT,
        "max_key": args.max_key,
        "time_limit": args.time_limit,
    }
    for question in args.questions:
        for found in answers(question, finder, **options):
            shown = f" ({found.caption})" if found.caption else ""
            print(f"{question}: {found.status}{shown}", flush=True)
            k = len(pictures) + 1
            path = write_answer(args.out, k, question, found, finder, args.time_limit)
            pictures.append(path)
            if found.summary:
                summaries.append(path)
    shown = summaries + [p for p in pictures if p not in summaries]
    print("pictures: " + " ".join(map(str, shown)))
    return 0


def read_marks(finder, condition_files, marks_file):
    marks = []
    for path in condition_files:
        try:
            cond = conditions.from_json(json.loads(path.read_text()))
        except (OSError, ValueError) as error:
            raise ValueError(f"{path}: {error}") from None
        marks.append((cond, {"condition": conditions.to_json(cond)}))
    if marks_file is not None:
        hook = getattr(finder, "mark", None)
        if hook is None:
            raise ValueError("this finder has no mark hook: give --condition")
        try:
            marks += list(read_entries(hook, marks_file))
        except (OSError, ValueError) as error:
            raise ValueError(f"{marks_file}: {error}") from None
    return marks


def read_entries(hook, marks_file):
    """Each `marks.json` entry through `hook`, as (condition, its line's
    fields); a ValueError names what does not read: not JSON, not a list, an
    entry that is not an object or lacks a field the hook reads."""
    entries = json.loads(marks_file.read_text())
    if not isinstance(entries, list):
        raise ValueError("not a list of marks")
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"mark {i} is not an object")
        try:
            cond = hook(entry)
        except KeyError as error:
            raise ValueError(f"mark {i} has no {error}") from None
        yield cond, {"condition": conditions.to_json(cond), "mark": entry}


def answers(question, finder, marks, limit, max_key, time_limit):
    if question == "feasible":
        yield feasible(finder, time_limit)
    elif question == "unique":
        yield unique(finder, time_limit)
    elif question == "forced":
        for cond, fields in marks:
            yield forced(finder, cond, fields, time_limit)
    elif question == "enumerate":
        yield from enumerate_solutions(finder, limit, time_limit)
    elif question == "max":
        yield from climb(finder, max_key, time_limit)
    else:
        yield from drop_one(finder, time_limit)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

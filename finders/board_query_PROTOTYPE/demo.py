"""PROTOTYPE for #36 -- run every question type on two finders. Throwaway.

    uv run finders/board_query_PROTOTYPE/demo.py halver PROGRESS.jsonl

Each solution goes to PROGRESS.jsonl as it is found; each answer is printed
with its status and whether it is complete.
"""

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import query as q

LIMIT = 60.0


def report(answer, board, started):
    flag = "complete" if answer.complete else "NOT complete"
    print(
        f"{answer.question:9} {answer.status}  [{flag}, {time.time() - started:.1f}s]"
    )
    if answer.detail:
        for clue, verdict in answer.detail.items():
            print(f"    {verdict:9} {clue}")
    sys.stdout.flush()


def sink_to(path, board):
    out = path.open("w")

    def sink(solution):
        out.write(json.dumps({"at": time.time(), "grid": board.show(solution)}) + "\n")
        out.flush()

    return sink


def halver(progress):
    import halver_board as hb
    import rules

    lines = rules.load_lines(HERE.parent / "halver_between" / "board.json")
    board = hb.HalverBoard(lines)
    sink = sink_to(progress, board)
    for name, run in [
        ("feasible", lambda: q.feasible(board, LIMIT, sink)),
        ("unique", lambda: q.unique(board, LIMIT, sink)),
        ("enumerate", lambda: q.enumerate_all(board, LIMIT, 10, sink)),
        ("max r1c1", lambda: q.maximum(board, ("d", 0, 0), LIMIT, sink)),
        ("max r5c5", lambda: q.maximum(board, ("d", 4, 4), LIMIT, sink)),
    ]:
        print(f"-- {name}")
        t = time.time()
        report(run(), board, t)

    print("-- forced marks: driver vs rules.mark_holds")
    marks = json.loads((HERE.parent / "halver_between" / "marks.json").read_text())
    agree = 0
    for mark in marks:
        mine = q.forced(board, hb.mark_condition(mark), LIMIT, sink).status
        theirs = board.rm.mark_holds(mark, LIMIT).status
        agree += mine == theirs
        tag = "" if mine == theirs else "  <-- DISAGREE"
        print(f"    {mine:9} {theirs:9} {rules.mark_name(mark)}{tag}")
    print(f"    {agree} of {len(marks)} agree")

    names = json.loads((HERE.parent / "halver_between" / "unique_9x9.json").read_text())
    cells = [[rules.parse_cell(n) for n in group] for group in names]
    unique_board = hb.HalverBoard(
        [rules.Line(c[0], tuple(c[1:-1]), c[-1]) for c in cells]
    )
    print(f"-- drop_one on unique_9x9.json ({len(cells)} lines)")
    t = time.time()
    report(q.drop_one(unique_board, LIMIT, sink), unique_board, t)


if __name__ == "__main__":
    halver(Path(sys.argv[2]))

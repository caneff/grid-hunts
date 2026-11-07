"""The between finder's entry for board questions (spec #65, #94):
`finders/query/query.py halver_between BOARD QUESTION... --out DIR`.

BOARD is a decoded SudokuMaker document whose between lines (type 403) are
the board's clues, as `board.json` is; its lines are drawn grey.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "halver"))

import rules

# isort: split
from halver_query import HalverQuery

LINE_COLOR = (150, 150, 150)


def load(board_path):
    doc = json.loads(board_path.read_text())
    return HalverQuery(rules.post_between, rules.lines_from_doc(doc), doc, LINE_COLOR)

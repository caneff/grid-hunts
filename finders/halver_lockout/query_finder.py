"""The lockout finder's entry for board questions (spec #65, #94):
`finders/query/query.py halver_lockout BOARD QUESTION... --out DIR`.

BOARD is a lockout board as `check.py` reads it, refused on the same terms;
its lines are drawn blue.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "halver"))

import check
import rules

# isort: split
from halver_query import HalverQuery

LINE_COLOR = (70, 120, 210)


def load(board_path):
    lines = check.read_board(board_path)
    doc = json.loads(board_path.read_text())
    return HalverQuery(rules.post_lockout, lines, doc, LINE_COLOR)

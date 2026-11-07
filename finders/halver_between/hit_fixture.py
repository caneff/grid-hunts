"""One recorded hit of the hunt, for the gate's tests: the second pilot's
seed 1 (decision log, § Hunt of record), its 11 added lines as the log's
table prints them. Of the three
recorded hits it is the one the backtracking check reads fastest.
"""

import rules

TABLE = [
    "r4c1 | r5c2 | r6c3",
    "r3c9 | r4c8 | r5c7",
    "r5c7 | r6c8 | r7c7",
    "r3c8 | r4c7 | r5c7",
    "r2c9 | r2c8 | r3c9",
    "r3c3 | r2c4 r3c4 | r4c3",
    "r1c5 | r2c6 | r1c6",
    "r7c7 | r7c8 | r7c9",
    "r4c2 | r5c3 | r4c3",
    "r7c6 | r6c7 | r7c7",
    "r1c3 | r1c4 | r1c5",
]


ADDED = tuple(map(rules.parse_line, TABLE))

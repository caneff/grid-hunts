"""One recorded hit of the lockout hunt, for the gate's tests: the pilot's
seed 2 (decision log, § Hunt of record), its 24 lines as the log's table
prints them and its solution. Of the
three recorded hits it is the one the backtracking check reads fastest
(about 15 s, against 170 s and 294 s).
"""

import rules

TABLE = [
    "r8c4 | r7c4 | r8c5",
    "r8c2 | r7c3 | r8c4",
    "r4c6 | r5c5 | r6c5",
    "r2c7 | r3c7 | r4c6",
    "r2c7 | r3c8 | r4c7",
    "r8c2 | r8c3 | r8c4",
    "r4c3 | r5c4 | r6c5",
    "r8c4 | r9c5 | r8c5",
    "r4c7 | r4c8 | r5c7",
    "r4c3 | r4c4 | r4c5",
    "r5c7 | r6c8 | r6c7",
    "r5c7 | r5c6 | r6c7",
    "r6c7 | r7c7 r8c6 | r8c5",
    "r3c3 | r3c4 | r4c5",
    "r4c3 | r5c2 | r5c1",
    "r3c1 | r3c2 | r3c3",
    "r4c3 | r4c2 | r5c1",
    "r2c5 | r3c5 | r4c5",
    "r6c7 | r7c8 | r8c7",
    "r2c8 | r3c9 | r4c9",
    "r2c5 | r2c6 | r2c7",
    "r2c3 | r2c4 | r2c5",
    "r1c3 | r1c4 | r2c5",
    "r2c2 | r1c2 | r2c3",
]


ADDED = tuple(map(rules.parse_line, TABLE))

DIGITS = [
    "927835641",
    "348169725",
    "165427893",
    "734592186",
    "896314572",
    "512786934",
    "653278419",
    "481953267",
    "279641358",
]
HALVERS = ["r1c1", "r2c5", "r3c9", "r4c4", "r5c8", "r6c3", "r7c7", "r8c2", "r9c6"]
SOLUTION = rules.Solution(
    tuple(tuple(int(d) for d in row) for row in DIGITS),
    frozenset(map(rules.parse_cell, HALVERS)),
)

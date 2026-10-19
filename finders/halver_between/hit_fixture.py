"""One recorded hit of the hunt, for the gate's tests: the second pilot's
seed 1 (decision log, § Hunt of record), its 11 added lines as the log's
table prints them, and the link the log publishes for it. Of the three
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

LINK = "https://sudokumaker.app/?puzzle=N4IgZg9gTgtghgFwGoFMoGcCWEB2IBcABCAIwB0AbGQAwgA0xADgK4BerANigYaDnDG5EQ9YnGYIAFtB4gAwpMw4AygihxGokAGMUHDuh4BtYAF8GZi+d7XLNqw-tO7L228euP75988+vAf5BfiG+YYGhEeHB0ZExUQnxSaEAugw6uOhqcEoIhkQmIAgAnoxChNS2RaXlJOlQKADm2Dj5hEbUDJ0VDHWEfX0ATAzDhKPdE71T-SOzY10LPTPLQ3OjAMwMm4TbACwM+4SHAKwMp4Tn21cHN0dn9xdbTzu3hycP5xQMX4Q-AOwMAGEIEADgYYMIEJ+0MBsOB4IRkO+yN+cKBoMRIJSVXQEA4ADc0ABJRo4aAoAAmPDUzBQ6RKZR4u2o2xAHCUKDaRiMgwAnFtuut+UdBX11qNdn1jt1dsLdhDdn80u0KOdjj9dhrjsqjLs1YcKNsKIc-ts-ibtQweUCSBDhSRuiRhYMsVaKKM-n0-t0KMKKNQdX9zn9-kCKBDjhGw5b2oMgesgYqdYMfus3oMdbtRsdRv7k5c9hmrSQbT8U8nHaNBkNeZneicdf7vn13cmIesIXydcdhccWwGrRsDillSAssUuDxQOycJyp0VFNoANaz9BtahkPoZDgyYQAYjgh6PIGsIBQOApAAUILk2qAsKxyhuIeBMPpZHuwF-vyDaOkslAEBLuUoBSJgy6ruuNCjNuu7EAeR6HiepgodiphAA"

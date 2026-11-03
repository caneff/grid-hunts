"""SCRATCH: aqre_jigsaw_r1.py on 8 workers, one case: the 9 in r1c5, by Chris's go."""

import sys

import aqre_jigsaw_r1 as base
from sudoku_kit.cpsat import solver

WORKERS = 8
base.RELAX_LIMIT = 300.0
base.TIME_LIMIT = 1800.0


def parallel(limit):
    s = solver(limit, reproducible=False, seed=1)
    s.parameters.num_workers = WORKERS
    return s


base.solver = parallel
base.attempt(4, sys.argv[1])

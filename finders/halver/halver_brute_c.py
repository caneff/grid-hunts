"""The shared halver layer's backtracking search in C (#59): the search of
`halver_brute.py` with `probe_ends`, about a hundred times faster, through
ctypes. It shares no code with the CP-SAT model in `halver_rules.py`.

`solutions(narrowing, lines, n, box, limit, deadline, probe_ends)` takes the
arguments of `halver_brute.solutions` and returns the same solutions in the
same order. A deadline passed raises `halver_brute.OutOfTime`, never a short
count. Boards up to 9x9 and up to 256 lines.

A line type's narrowing step runs here once per line and end pair, never in
the search: `narrow(1 << x, 1 << y, every)` gives the doubled values the body
may take when the ends are x and y, or None when the pair fails. The C
search keeps an end pair while every body cell has a value in its body mask.
That reads a narrowing exactly when the narrowing has this form, as the
lockout and between narrowings do; `finders/halver_lockout/test_c_search.py`
checks the lockout one against the Python search.

The library is built with the system `gcc` on first import, or when
`halver_brute.c` is newer, into the git-ignored `target/` beside this file.
No `gcc`, or a build that fails, raises `RuntimeError`: there is no fallback
to the slow search.
"""

import ctypes
import os
import subprocess
import time
from pathlib import Path

import halver_brute
from halver_brute import OutOfTime

__all__ = ["OutOfTime", "solutions"]

HERE = Path(__file__).resolve().parent
SRC = HERE / "halver_brute.c"
# A committed `*` .gitignore keeps the build out of git, and merge-cleanup
# sweeps `target/` with the worktree (as `finders/counting_shaded/target/`).
BUILD = HERE / "target"
SO = BUILD / "halver_brute.so"
MAX_N, MAX_LINES = 9, 256

_IP = ctypes.POINTER(ctypes.c_int)


def _load():
    if not SO.exists() or SO.stat().st_mtime < SRC.stat().st_mtime:
        # Suites run side by side, so each build writes its own file and
        # renames it into place.
        partial = BUILD / f"halver_brute.{os.getpid()}.so"
        command = ["gcc", "-O2", "-shared", "-fPIC", "-o", str(partial), str(SRC)]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as error:
            raise RuntimeError(
                "halver_brute_c: no gcc on PATH; the C search needs the system gcc"
            ) from error
        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                f"halver_brute_c: building {SRC.name} failed:\n{error.stderr}"
            ) from error
        partial.replace(SO)
    lib = ctypes.CDLL(str(SO))
    lib.hb_solutions.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        _IP,
        ctypes.c_int,
        _IP,
        _IP,
        ctypes.c_int,
        _IP,
        ctypes.c_int,
        ctypes.c_double,
        _IP,
    ]
    lib.hb_solutions.restype = ctypes.c_int
    return lib


_lib = _load()


def _ints(values):
    return (ctypes.c_int * max(1, len(values)))(*values)


def solutions(narrowing, lines, n, box, limit, deadline=None, probe_ends=False):
    if n > MAX_N or len(lines) > MAX_LINES:
        raise ValueError(
            f"the C search takes up to {MAX_N}x{MAX_N} and {MAX_LINES} lines, "
            f"not {n}x{n} and {len(lines)}"
        )
    houses = [[r * n + c for r, c in house] for house in halver_brute._houses(n, box)]
    every = (1 << (2 * n + 1)) - 2  # doubled values 1..2n
    flat_lines, flat_pairs, ends = [], [], set()
    for (a, ac), body, (b, bc) in lines:
        end_a, end_b = a * n + ac, b * n + bc
        cells = [r * n + c for r, c in body]
        ends |= {end_a, end_b}
        flat_lines += [end_a, end_b, len(cells), *cells]
        narrow = narrowing(cells, houses, n)
        pairs = []
        for x in range(1, 2 * n + 1):
            for y in range(1, 2 * n + 1):
                kept = narrow(1 << x, 1 << y, [every] * len(cells))
                if kept is not None:
                    pairs += [x, y, kept[2]]
        flat_pairs += [len(pairs) // 3, *pairs]
    ends = sorted(ends) if probe_ends else []
    budget = -1.0
    if deadline is not None:
        budget = deadline - time.monotonic()
        if budget <= 0:
            raise OutOfTime
    out = (ctypes.c_int * (limit * n * n))()
    got = _lib.hb_solutions(
        n,
        len(houses),
        _ints([i for house in houses for i in house]),
        len(lines),
        _ints(flat_lines),
        _ints(flat_pairs),
        len(ends),
        _ints(ends),
        limit,
        budget,
        out,
    )
    if got < 0:
        raise OutOfTime
    found = []
    for k in range(got):
        cells = out[k * n * n : (k + 1) * n * n]
        grid = tuple(tuple(cells[r * n + c] & 15 for c in range(n)) for r in range(n))
        halvers = frozenset(divmod(i, n) for i in range(n * n) if cells[i] & 16)
        found.append((grid, halvers))
    return found

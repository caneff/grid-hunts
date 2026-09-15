"""ctypes wrapper for ghosts_fast.c, plus a parity test against shapes.py.

    uv run docs/research/ghosts/fastclimb.py --test

The .so is built on first import into the worktree's git-ignored .scratch.
"""

import ctypes
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "ghosts_fast.c"
BUILD = HERE.parents[2] / ".scratch" / "ghosts" / "build"
SO = BUILD / "ghosts_fast.so"


def _load():
    if not SO.exists() or SO.stat().st_mtime < SRC.stat().st_mtime:
        BUILD.mkdir(parents=True, exist_ok=True)
        subprocess.run(["gcc", "-O2", "-march=native", "-shared", "-fPIC", "-o", str(SO), str(SRC), "-lm"],
                       check=True)
    lib = ctypes.CDLL(str(SO))
    lib.gf_count.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.gf_climb.argtypes = [ctypes.c_char_p, ctypes.c_uint64, ctypes.c_double, ctypes.c_int,
                             ctypes.POINTER(ctypes.c_int64), ctypes.c_double, ctypes.c_double, ctypes.c_int]
    return lib


LIB = _load()


def _buf(shape):
    return ctypes.create_string_buffer(bytes(1 if i in shape else 0 for i in range(81)), 81)


def count(shape, cap):
    """Solutions up to cap; -1 if inadmissible or no 8."""
    return LIB.gf_count(_buf(shape), cap)


def climb(shape, seed, seconds, cap=2000, t_hi=1.0, t_lo=0.02, max_toggles=4):
    """(best shape, best solution count, steps); count 1 = unique."""
    buf = _buf(shape)
    steps = ctypes.c_int64()
    score = LIB.gf_climb(buf, seed, seconds, cap, ctypes.byref(steps), t_hi, t_lo, max_toggles)
    return {i for i in range(81) if buf.raw[i]}, score, steps.value


def _test():
    import json

    from shapes import count_solutions, givens, has_eight

    rng = random.Random(0)
    hit = set(json.loads(open(HERE / "allvisible-hits.jsonl").readline())["shape"])
    assert count(hit, 2) == 1
    checked = 0
    for _ in range(20000):
        shape = set(hit)
        for _ in range(rng.randrange(1, 6)):
            shape ^= {rng.randrange(81)}
        g = givens(shape)
        want = count_solutions(g, 50) if has_eight(g) else -1
        got = count(shape, 50)
        assert got == want, (sorted(shape), got, want)
        checked += want >= 0
    print(f"parity OK: 20000 shapes, {checked} admissible")
    shape, score, steps = climb(hit ^ {0, 1, 2, 40}, 7, 2.0)
    print(f"climb 2s: score {score}, steps {steps}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _test()

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
    lib.gf_require_eight.argtypes = [ctypes.c_int]
    lib.gf_set_pins.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.gf_climb.argtypes = [ctypes.c_char_p, ctypes.c_uint64, ctypes.c_double, ctypes.c_int,
                             ctypes.POINTER(ctypes.c_int64), ctypes.c_double, ctypes.c_double, ctypes.c_int]
    return lib


LIB = _load()


def _buf(shape):
    return ctypes.create_string_buffer(bytes(1 if i in shape else 0 for i in range(81)), 81)


def require_eight(on):
    """Demand (True) or drop (False) the ghost showing 8, matching shapes.REQUIRE_EIGHT."""
    import shapes
    shapes.REQUIRE_EIGHT = bool(on)
    LIB.gf_require_eight(1 if on else 0)


def pins(force=(), ban=()):
    """Pin cells on/off in both the C filter and shapes.py (indices 0-80)."""
    import shapes
    shapes.pins(force, ban)
    on = bytes(1 if i in set(force) else 0 for i in range(81))
    off = bytes(1 if i in set(ban) else 0 for i in range(81))
    LIB.gf_set_pins(on, off)


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

    import shapes
    from shapes import count_solutions, eight_ok, givens

    rng = random.Random(0)
    hit = set(json.loads(open(HERE / "allvisible-hits.jsonl").readline())["shape"])
    # The pre-connectivity hit is 8 separate blobs, so the filter now rejects it.
    require_eight(False)
    pins()
    assert count(hit, 2) == -1, "a disconnected shape must be rejected"

    for label, eight, force, ban in (("plain", False, (), ()), ("eight", True, (), ()),
                                     ("pins", False, (72, 73), (57,))):
        require_eight(eight)
        pins(force, ban)
        checked = admissible = 0
        for _ in range(20000):
            shape = set(hit)
            for _ in range(rng.randrange(1, 6)):
                shape ^= {rng.randrange(81)}
            if rng.random() < 0.5:  # connected blobs, or the filter only ever sees rejects
                start = rng.randrange(81)
                shape = {start}
                while len(shape) < rng.randrange(4, 20):
                    opts = [j for i in shape for j in shapes.ORTH[i] if j not in shape]
                    shape.add(rng.choice(opts))
            g = givens(shape)
            want = count_solutions(g, 50) if eight_ok(g) else -1
            got = count(shape, 50)
            assert got == want, (label, sorted(shape), got, want)
            checked += 1
            admissible += want >= 0
        print(f"parity OK ({label}): {checked} shapes, {admissible} admissible")
    require_eight(False)
    pins()


if __name__ == "__main__":
    if "--test" in sys.argv:
        _test()

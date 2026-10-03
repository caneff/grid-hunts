"""ctypes wrapper for counting_shaded_fast.c, plus a parity test against shapes.py.

    uv run finders/counting_shaded/fastclimb.py --test

The .so is built on first import into a git-ignored `target/` beside this file.
"""

import ctypes
import random
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "counting_shaded_fast.c"
REPO = HERE.parents[1]
DATA = (
    REPO / "docs" / "research" / "counting_shaded"
)  # notes, hits and images stayed there
# Named `target` and holding a committed `*` .gitignore so merge-cleanup's
# CACHE_DIRS sweeps the compiled artifact with the worktree instead of
# refusing cleanup; see #559. Kept outside `.scratch/` (#633), so a worker's
# "clear .scratch/" step (`rm -rf .scratch`) can't delete this tracked anchor.
BUILD = HERE / "target"
SO = BUILD / "counting_shaded_fast.so"


def _load():
    if not SO.exists() or SO.stat().st_mtime < SRC.stat().st_mtime:
        BUILD.mkdir(parents=True, exist_ok=True)
        (BUILD / ".gitignore").write_text("*\n")
        subprocess.run(
            [
                "gcc",
                "-O2",
                "-march=native",
                "-shared",
                "-fPIC",
                "-o",
                str(SO),
                str(SRC),
                "-lm",
            ],
            check=True,
        )
    lib = ctypes.CDLL(str(SO))
    lib.gf_count.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.gf_require_eight.argtypes = [ctypes.c_int]
    lib.gf_set_latin.argtypes = [ctypes.c_int]
    lib.gf_set_pins.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.gf_enumerate.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int64,
        ctypes.POINTER(ctypes.c_int64),
    ]
    lib.gf_climb.argtypes = [
        ctypes.c_char_p,
        ctypes.c_uint64,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int64),
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
    ]
    return lib


LIB = _load()


def _buf(shape):
    return ctypes.create_string_buffer(
        bytes(1 if i in shape else 0 for i in range(81)), 81
    )


def latin(on):
    """Latin-square mode: rows and columns only, no boxes (C filter and counter)."""
    LIB.gf_set_latin(1 if on else 0)


def require_eight(on):
    """Demand (True) or drop (False) the shaded cell showing 8, matching shapes.REQUIRE_EIGHT."""
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
    score = LIB.gf_climb(
        buf, seed, seconds, cap, ctypes.byref(steps), t_hi, t_lo, max_toggles
    )
    return {i for i in range(81) if buf.raw[i]}, score, steps.value


@dataclass
class Enumeration:
    """What `enumerate_shapes` found. `exhausted` False means the time limit cut it off."""

    exhausted: bool
    shapes: int
    solvable: int
    unique: int
    solvable_shapes: list  # [(set of cells, solutions up to cap)], at most max_stored

    @property
    def truncated(self):
        """True when more solvable shapes were found than `solvable_shapes` holds."""
        return self.solvable > len(self.solvable_shapes)


def enumerate_shapes(
    size, all_digits=True, symmetry=False, cap=2, seconds=0, max_stored=100000
):
    """Every connected admissible shape of `size` cells, by depth-first search.

    Honours `pins`, `require_eight` and `latin`; each shape goes through the same
    filter and counter as `count`. all_digits also demands a given of each of 1-8.
    symmetry keeps one shape per orbit of the 8 dihedral images (no pins).
    seconds > 0 cuts the search off; the result then says `exhausted=False`.
    """
    out = ctypes.create_string_buffer(81 * max_stored)
    ks = (ctypes.c_int * max_stored)()
    stats = (ctypes.c_int64 * 5)()
    rc = LIB.gf_enumerate(
        size, int(all_digits), int(symmetry), cap, seconds, out, ks, max_stored, stats
    )
    if rc:
        raise ValueError(
            "gf_enumerate: size not in 1-81, cap below 2, or symmetry with pins"
        )
    found = [
        ({i for i in range(81) if out.raw[81 * s + i]}, ks[s]) for s in range(stats[3])
    ]
    return Enumeration(bool(stats[4]), stats[0], stats[1], stats[2], found)


def _test():
    import json

    import shapes
    from shapes import count_solutions, eight_ok, givens

    rng = random.Random(0)
    hit = set(
        json.loads((DATA / "allvisible-hits.jsonl").read_text().splitlines()[0])[
            "shape"
        ]
    )
    # The pre-connectivity hit is 8 separate blobs, so the filter now rejects it.
    require_eight(False)
    pins()
    assert count(hit, 2) == -1, "a disconnected shape must be rejected"

    for label, eight, force, ban in (
        ("plain", False, (), ()),
        ("eight", True, (), ()),
        ("pins", False, (72, 73), (57,)),
    ):
        require_eight(eight)
        pins(force, ban)
        checked = admissible = 0
        for _ in range(20000):
            shape = set(hit)
            for _ in range(rng.randrange(1, 6)):
                shape ^= {rng.randrange(81)}
            if (
                rng.random() < 0.5
            ):  # connected blobs, or the filter only ever sees rejects
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

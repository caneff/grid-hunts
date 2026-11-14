"""Pins `c_library.load`: a stale library is rebuilt, concurrent loads of an absent
library each get a whole file, gcc writes to a temp file that is renamed into place
(so a build that dies half-way leaves no library behind), and a missing gcc or a
failed build raises `CBuildError` naming gcc and its stderr.

    uv run finders/hunt/test_c_library.py
"""

import ctypes
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c_library
from cli_checks import check, finish

HERE = Path(__file__).resolve().parent


def source(value):
    return f"int answer(void) {{ return {value}; }}\n"


def answer(lib):
    lib.answer.restype = ctypes.c_int
    return lib.answer()


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    src, so = tmp / "lib.c", tmp / "target" / "lib.so"

    # Stale rebuild: absent library builds; a newer source rebuilds into a new file.
    src.write_text(source(1))
    check("absent library builds", answer(c_library.load(src, so)) == 1)
    first_mtime = so.stat().st_mtime
    src.write_text(source(2))
    os.utime(src, (time.time() + 5, time.time() + 5))
    # A fresh process: dlopen caches by path in this one.
    probe = (
        "import sys, ctypes; sys.path.insert(0, sys.argv[1]); import c_library;"
        "lib = c_library.load(sys.argv[2], sys.argv[3]);"
        "lib.answer.restype = ctypes.c_int; print(lib.answer())"
    )
    out = subprocess.run(
        [sys.executable, "-c", probe, str(HERE), str(src), str(so)],
        capture_output=True,
        text=True,
    )
    check(
        f"stale library rebuilds ({out.stdout!r} {out.stderr[-200:]!r})",
        out.stdout.strip() == "2",
    )
    check("rebuild replaced the file", so.stat().st_mtime >= first_mtime)
    check("no temp file left", [p.name for p in so.parent.iterdir()] == ["lib.so"])

    # Eight concurrent loads of an absent library: every process gets a working one.
    so.unlink()
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", probe, str(HERE), str(src), str(so)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(8)
    ]
    results = [(*p.communicate(), p.returncode) for p in procs]
    check(
        f"8 concurrent loads all see the whole library ({results[0]})",
        all(r[0].strip() == "2" and r[2] == 0 for r in results),
    )
    check(
        "no temp file left after the race",
        [p.name for p in so.parent.iterdir()] == ["lib.so"],
    )

    # Flags and libs reach gcc.
    src.write_text("#include <math.h>\nint answer(void) { return (int)sqrt(16.0); }\n")
    so2 = tmp / "target" / "lib2.so"
    check(
        "libs link",
        answer(c_library.load(src, so2, flags=("-O2",), libs=("-lm",))) == 4,
    )

    # Failed build: named error with gcc's stderr.
    bad = tmp / "bad.c"
    bad.write_text("this is not C\n")
    try:
        c_library.load(bad, tmp / "target" / "bad.so")
        check("a failed build raises", False)
    except c_library.CBuildError as error:
        check(
            f"failed build names gcc and bad.c ({error})",
            "gcc" in str(error) and "bad.c" in str(error),
        )
        check("failed build carries gcc's stderr", "error" in str(error))
    check(
        "failed build leaves no file",
        not (tmp / "target" / "bad.so").exists()
        and [p.name for p in so.parent.iterdir() if p.name.startswith("bad")] == [],
    )

    # A gcc that writes half a library and dies: gcc was handed a temp file beside the
    # library, not the library's own path, and nothing is left at the library's path.
    # A build straight into the final path would leave the half-written file there.
    fake = tmp / "fake-bin"
    fake.mkdir()
    seen = tmp / "gcc-output-arg"
    (fake / "gcc").write_text(
        "#!/bin/sh\n"
        'while [ "$1" != "-o" ]; do shift; done\n'
        f'printf "%s" "$2" > "{seen}"\n'
        'printf "half a library" > "$2"\n'
        'echo "gcc: killed half-way" >&2\n'
        "exit 1\n"
    )
    (fake / "gcc").chmod(0o755)
    halfway = tmp / "target" / "halfway.so"
    saved = os.environ["PATH"]
    os.environ["PATH"] = f"{fake}:{saved}"
    try:
        c_library.load(src, halfway)
        check("a build that dies half-way raises", False)
    except c_library.CBuildError as error:
        check(
            f"a build that dies half-way names gcc's stderr ({error})",
            "half-way" in str(error),
        )
    finally:
        os.environ["PATH"] = saved
    output = Path(seen.read_text())
    check(
        f"gcc writes to a temp file beside the library ({output.name})",
        output != halfway and output.parent == halfway.parent,
    )
    check("a build that dies half-way leaves no library", not halfway.exists())
    check("... and no temp file", not output.exists())

    # Missing gcc: named error, a RuntimeError subclass.
    empty = tmp / "empty-path"
    empty.mkdir()
    saved = os.environ["PATH"]
    os.environ["PATH"] = str(empty)
    try:
        c_library.load(src, tmp / "target" / "nogcc.so")
        check("a missing gcc raises", False)
    except c_library.CBuildError as error:
        check(f"missing gcc names gcc ({error})", "gcc" in str(error))
        check("CBuildError is a RuntimeError", isinstance(error, RuntimeError))
    finally:
        os.environ["PATH"] = saved

finish()

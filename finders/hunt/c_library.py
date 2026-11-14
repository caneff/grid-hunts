"""The one loader for a C helper a finder compiles at run time (#144).

`load(src, so)` returns a `ctypes.CDLL` for `so`, first building it with the
system `gcc` when it is missing or older than `src`. Suites run side by side,
so a build goes to its own temp file beside `so` and is renamed into place:
`os.replace` is atomic, and no process loads a half-written library. No `gcc`,
or a build that fails, raises `CBuildError` naming gcc and its stderr."""

import ctypes
import os
import subprocess
import tempfile
from pathlib import Path


class CBuildError(RuntimeError):
    """The C helper could not be built: no gcc on PATH, or gcc failed."""


def load(src, so, *, flags=("-O2",), libs=()):
    """Load `so`, rebuilding it from `src` when stale. `flags` go before the
    source and `libs` after it, as gcc wants them."""
    src, so = Path(src), Path(so)
    if not so.exists() or so.stat().st_mtime < src.stat().st_mtime:
        _build(src, so, flags, libs)
    return ctypes.CDLL(str(so))


def _build(src, so, flags, libs):
    so.parent.mkdir(parents=True, exist_ok=True)
    fd, partial = tempfile.mkstemp(dir=so.parent, prefix=f"{so.stem}.", suffix=".so")
    os.close(fd)
    command = ["gcc", *flags, "-shared", "-fPIC", "-o", partial, str(src), *libs]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        Path(partial).replace(so)
    except FileNotFoundError as error:
        raise CBuildError(
            f"no gcc on PATH; building {src.name} needs the system gcc"
        ) from error
    except subprocess.CalledProcessError as error:
        raise CBuildError(f"gcc failed building {src.name}:\n{error.stderr}") from error
    finally:
        # Gone after a successful replace; left behind by a failed build.
        Path(partial).unlink(missing_ok=True)

"""Smoke test for the hunt drivers: each compiles, its repo-relative paths resolve, and
none reads a cwd-relative or absolute log or source path.
The scripts run a hunt at import (they read sys.argv), so this test never imports them."""

import py_compile
import re
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
scripts = sorted(p for p in HERE.glob("*.py") if p.name != Path(__file__).name)
assert scripts, "no hunt scripts found"
# The two directories the scripts reach with parents[1] (finders/qqrr) and parents[3] (repo root).
assert (HERE.parent / "model.py").exists() and (HERE.parent / "oracle.py").exists()
assert (ROOT / "examples" / "_shared" / "cpsat.py").exists()
with tempfile.TemporaryDirectory() as d:
    for p in [*scripts, HERE / "scheduler4.sh"]:
        text = p.read_text()
        assert "/home/" not in text, p
        assert 'glob.glob(".scratch' not in text, f"{p}: cwd-relative log glob"
        # parents index 1 is finders/qqrr, 3 is the repo root.
        for n in re.findall(r"__file__\)\.resolve\(\)\.parents\[(\d)\]", text):
            assert n in "13", (
                f"{p}: parents[{n}] is neither finders/qqrr nor the repo root"
            )
        if p.suffix == ".py":
            py_compile.compile(
                str(p), cfile=str(Path(d) / (p.name + "c")), doraise=True
            )
print("ok", len(scripts), "scripts")

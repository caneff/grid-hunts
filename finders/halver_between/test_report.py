"""The report command on Chris's board: L1-L5 leave more than one solution, and
every one of his marks (#39) holds in every solution. A mark that does not
hold fails this test and goes to Chris; the mark is never edited to pass.
Then a marks file with one false mark: the report says "not held" for it and
exits 1.

    uv run finders/halver_between/test_report.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE / "report.py"


def run(*args):
    return subprocess.run(
        [sys.executable, str(REPORT), *args], capture_output=True, text=True
    )


done = run()
assert done.returncode == 0, (done.returncode, done.stdout, done.stderr)
lines = done.stdout.splitlines()
assert lines[0] == "L1-L5: not_unique", lines[0]
marks = lines[1:]
assert marks == [
    "held      r1c1 = 1",
    "held      r1c2 = 9",
    "held      r4c1 = 2",
    "held      r4c2 = 8",
    "held      r6c1 = 6",
    "held      r6c2 = 7",
    "held      r7c3 = 7",
    "held      r8c2 = 6",
    "held      r8c3 = 8",
    "held      r9c4 = 3",
    "held      r8c2 is a halver",
    "held      r9c4 is a halver",
    "held      a halver 9 in r5c5 or r5c6",
    "held      a halver 8 in r2c1 or r3c1",
    "held      r4c3 in {1,9}",
    "held      r6c3 in {1,9}",
    "held      r7c2 in {1,9}",
    "held      r9c1 in {1,9}",
], "\n".join(marks)

# A false mark is reported as not held, with a solution that breaks it.
with tempfile.TemporaryDirectory() as tmp:
    wrong = Path(tmp) / "marks.json"
    wrong.write_text(json.dumps([{"kind": "digit", "cell": "r1c1", "digit": 2}]))
    done = run("--marks", str(wrong))
    assert done.returncode == 1, (done.returncode, done.stdout, done.stderr)
    out = done.stdout.splitlines()
    assert out[0] == "L1-L5: not_unique", out
    assert out[1] == "NOT HELD  r1c1 = 2", out
    assert out[2].startswith("  broken by: r1 "), out

print("ok")

"""The report command on Chris's board: its six lines leave more than one
solution, and every one of his 23 marks (the board switch on #39) holds in
every solution. A mark that does not hold fails this test and goes to Chris;
the mark is never edited to pass. Then a marks file with one false mark: the
report says "NOT HELD" for it, with a solution that breaks it, and exits 1.

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
assert lines[0] == "L1-L6: not_unique", lines[0]
marks = lines[1:]
assert marks == [
    "held      r6c1 = 6",
    "held      r6c2 = 7",
    "held      r7c3 = 7",
    "held      r8c2 = 6",
    "held      r8c3 = 8",
    "held      r1c1 in {1,9}",
    "held      r1c2 in {1,9}",
    "held      r4c3 in {1,9}",
    "held      r6c3 in {1,9}",
    "held      r7c2 in {1,9}",
    "held      r9c1 in {1,9}",
    "held      r2c1 in {7,8}",
    "held      r3c1 in {7,8}",
    "held      r9c4 in {2,3}",
    "held      r8c2 is a halver",
    "held      r9c4 is a halver",
    "held      a halver 9 in r5c5 or r5c6",
    "held      2 in r1c3 or r2c3 or r3c3",
    "held      2 in r7c1 or r8c1 or r9c2",
    "held      1 in r8c4 or r8c5 or r8c6",
    "held      9 in r8c4 or r8c5 or r8c6",
    "held      1 in r7c7 or r7c8 or r7c9 or r9c7 or r9c8 or r9c9",
    "held      9 in r7c7 or r7c8 or r7c9 or r9c7 or r9c8 or r9c9",
], "\n".join(marks)

# A false mark is reported as not held, with a solution that breaks it.
with tempfile.TemporaryDirectory() as tmp:
    wrong = Path(tmp) / "marks.json"
    wrong.write_text(json.dumps([{"kind": "digit", "cell": "r1c1", "digit": 2}]))
    done = run("--marks", str(wrong))
    assert done.returncode == 1, (done.returncode, done.stdout, done.stderr)
    out = done.stdout.splitlines()
    assert out[0] == "L1-L6: not_unique", out
    assert out[1] == "NOT HELD  r1c1 = 2", out
    assert out[2].startswith("  broken by: r1 "), out

print("ok")

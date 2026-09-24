"""Usage: sync_presets.py [<explorer.html>]; logs from $HUNT_LOGS (default .scratch/place).
Add every hit in big-*-q34.log to the explorer's PRESETS (newest first); grids already present are skipped."""

import glob
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOGS = Path(os.environ.get("HUNT_LOGS", ROOT / ".scratch" / "place"))
H = (
    sys.argv[1]
    if len(sys.argv) > 1
    else ROOT / "docs" / "research" / "2026-09-22-qqrr-explorer.html"
)
s = open(H).read()
BOUND = {"r5c1": ("r4c1", "4,0"), "r1c5": ("r1c4", "0,4")}
new = []
for p in sorted(glob.glob(str(LOGS / "big-*-q34.log"))):
    _, hunt, ten, corner, _ = p.rsplit("/", 1)[-1][:-4].split("-")
    m = re.match(r"r(\d)c(\d)", ten)
    wkey = f"{int(m[1]) - 1},{int(m[2]) - 1}"
    lines = open(p).read().split("\n")
    n = 0
    for i, l in enumerate(lines):
        if not l.startswith("HIT"):
            continue
        n += 1
        tie = re.match(
            r"  tie (r\dc\d) [\d|]+ = (r\dc\d) [\d|]+, number (\d+), QQRR (\d+)",
            lines[i + 1],
        )
        grid = lines[i + 3].split()[1]
        if grid in s:
            continue
        a, b = tie[1], tie[2]
        box = (int(a[1]) - 1) // 3 == (int(b[1]) - 1) // 3 and (int(a[3]) - 1) // 3 == (
            int(b[3]) - 1
        ) // 3
        boxonly = ", box only" if box and a[1] != b[1] and a[3] != b[3] else ""
        label = f"33 at {hunt}, {BOUND[hunt][0]} < 8, QR 10 at {ten} · tie {a} = {b} ({tie[3]}, QQRR {tie[4]}{boxonly}) · {corner} #{n} · 34–36 hunt"
        new.append(
            f'["{label}","{grid}","{corner}","{BOUND[hunt][1]}",{{"{wkey}":"10"}}],'
        )
if new:
    s = s.replace("const PRESETS=[\n", "const PRESETS=[\n" + "\n".join(new) + "\n", 1)
    open(H, "w").write(s)
print(f"added {len(new)}")

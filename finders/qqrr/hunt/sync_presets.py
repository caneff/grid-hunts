"""Usage: sync_presets.py [<explorer.html>]; logs from $HUNT_LOGS (default .scratch/place).
Add every hit in big-*-q34.log to the explorer's PRESETS (newest first); grids already present are skipped."""

import glob
import re
import sys

import hunt_common as hc

ROOT, LOGS = hc.ROOT, hc.LOGS
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
    n = 0
    for hit in hc.parse_hits(open(p).read()):
        n += 1
        grid = hit["grid"]
        if grid in s:
            continue
        tie = hit["ties"][0]
        a, b = tie[0], tie[1]
        box = (int(a[1]) - 1) // 3 == (int(b[1]) - 1) // 3 and (int(a[3]) - 1) // 3 == (
            int(b[3]) - 1
        ) // 3
        boxonly = ", box only" if box and a[1] != b[1] and a[3] != b[3] else ""
        label = f"33 at {hunt}, {BOUND[hunt][0]} < 8, QR 10 at {ten} · tie {a} = {b} ({tie[2]}, QQRR {tie[3]}{boxonly}) · {corner} #{n} · 34–36 hunt"
        new.append(
            f'["{label}","{grid}","{corner}","{BOUND[hunt][1]}",{{"{wkey}":"10"}}],'
        )
if new:
    s = s.replace("const PRESETS=[\n", "const PRESETS=[\n" + "\n".join(new) + "\n", 1)
    open(H, "w").write(s)
print(f"added {len(new)}")

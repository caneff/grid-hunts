"""Usage: sync_presets.py [<explorer.html>]; logs from $HUNT_LOGS (default .scratch/place).
Add every hit in big-*-q34.log to the explorer's PRESETS (newest first); grids already present are skipped."""

import glob
import re
import sys

import hunt_common as hc

BOUND = {"r5c1": ("r4c1", "4,0"), "r1c5": ("r1c4", "0,4")}


def sync(explorer, logs=None):
    """Add every hit of `logs`' big-*-q34.log (default $HUNT_LOGS) to the PRESETS of the explorer
    page at `explorer`, skipping grids it already holds. Returns the number added."""
    logs = hc.LOGS if logs is None else logs
    s = open(explorer).read()
    new = []
    for p in sorted(glob.glob(str(logs / "big-*-q34.log"))):
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
            a, b = tie.a, tie.b
            box = (int(a[1]) - 1) // 3 == (int(b[1]) - 1) // 3 and (
                int(a[3]) - 1
            ) // 3 == (int(b[3]) - 1) // 3
            boxonly = ", box only" if box and a[1] != b[1] and a[3] != b[3] else ""
            label = f"33 at {hunt}, {BOUND[hunt][0]} < 8, QR 10 at {ten} · tie {a} = {b} ({tie.number}, QQRR {tie.qqrr}{boxonly}) · {corner} #{n} · 34–36 hunt"
            new.append(
                f'["{label}","{grid}","{corner}","{BOUND[hunt][1]}",{{"{wkey}":"10"}}],'
            )
    if new:
        s = s.replace(
            "const PRESETS=[\n", "const PRESETS=[\n" + "\n".join(new) + "\n", 1
        )
        open(explorer, "w").write(s)
    return len(new)


if __name__ == "__main__":
    explorer = (
        sys.argv[1]
        if len(sys.argv) > 1
        else hc.ROOT / "docs" / "research" / "2026-09-22-qqrr-explorer.html"
    )
    print(f"added {sync(explorer)}")

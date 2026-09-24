"""Solver-setting measurement on timed-out channelled tasks (tr, r5c1 hunt).
Usage: measure.py <log>. Runs each task under several configs, 180 s each, sequentially."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
logp = sys.argv[1]
TASKS = [(((3, 1), (4, 2)), 3, 0), (((4, 2), (4, 4)), 0, 3), (((4, 2), (4, 5)), 0, 2)]
CONFIGS = [
    ("default 1w", [], 1),
    ("lin2 1w", ["lin2"], 1),
    ("nohint+tables 1w", ["nohint", "tables"], 1),
    ("nohint+tables+lin2 1w", ["nohint", "tables", "lin2"], 1),
    ("default 6w", [], 6),
    ("nohint+tables+lin2 6w", ["nohint", "tables", "lin2"], 6),
]
log = open(logp, "a")
for name, flags, w in CONFIGS:
    for task in TASKS:
        sys.argv = ["x", "tr", "1", "180", "/dev/null", "r5c1", str(w)] + flags
        if "chan_sweep" in sys.modules:
            del sys.modules["chan_sweep"]
        import chan_sweep as cs

        r = cs.solve(task)
        print(f"{name:26s} {r.splitlines()[0]}", file=log, flush=True)
print("measure done", file=log, flush=True)

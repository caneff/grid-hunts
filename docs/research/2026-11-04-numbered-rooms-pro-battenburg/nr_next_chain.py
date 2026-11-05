"""SCRATCH: the ordered non-pointer steps of each branch from nr_next_pair, for reading."""

import nr_next_pair as X

for label, pink, green in (("MAGENTA", X.M, X.P), ("PURPLE", X.P, X.M)):
    _, _, log, _ = X.branch(pink, green)
    print(label, "pointer eliminations:", sum("would hit" in line for line in log))
    for i, line in enumerate(log):
        if "would hit" not in line and ("target" in line.split("(")[0] or "only" in line or "already" in line or "route" in line):
            print(f"  {i}: {line}")
    print("  pointer steps on r1c1 r9c1 r8c1 r8c9:")
    for i, line in enumerate(log):
        if "would hit" in line and line[:4] in ("r1c1", "r9c1", "r8c1", "r8c9"):
            print(f"    {i}: {line}")

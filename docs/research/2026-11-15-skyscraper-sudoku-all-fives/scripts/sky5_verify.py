"""SCRATCH: re-check the sky5 find on custom-constraints' own add_visibility + sudoku_kit.solve_unique."""
import sys
sys.path.insert(0, "examples/skyscraper"); sys.path.insert(0, "examples/_shared")
from build_size import add_visibility, sky
from sudoku_kit import cpsat
G = "671239458 342518967 985647231 216753849 834921576 759864123 123496785 598372614 467185392".split()
OUT = "c1B r2L r3R c3T r4L c4T c4B c5T r6R c6B r7L c7B r8R c8T r9L c9B".split()
N = 9
def line(t):
    i = int(t[1:-1]) - 1
    seq = [(i, c) for c in range(N)] if t[0] == "r" else [(r, i) for r in range(N)]
    return seq[::-1] if t[-1] in "RB" else seq
g = {(r, c): int(G[r][c]) for r in range(N) for c in range(N)}
assert all(sky([g[p] for p in line(t)], None, None) == 5 for t in OUT), "a clue is not 5"
all5 = [s + str(i) + e for i in range(1, 10) for s, ends in (("r", "LR"), ("c", "TB")) for e in ends]
print("lines showing 5 in this grid:", sum(sky([g[p] for p in line(f"{t[0]}{t[1:-1]}{t[-1]}")], None, None) == 5 for t in all5))
m, x = cpsat.sudoku_model(N, cpsat.boxes(N, 3, 3))
for p, v in g.items():
    if v == 5: m.Add(x[p] == 5)
for t in OUT:
    add_visibility(m, x, line(t), 5, N, t, None)
first, uniq = cpsat.solve_unique(m, x, 60)
print("solution matches:", first is not None and all(first[p] == g[p] for p in g) if isinstance(first, dict) else first is not None, "unique:", uniq)

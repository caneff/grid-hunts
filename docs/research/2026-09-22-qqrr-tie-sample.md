# QQRR: tied cell numbers between cells that see each other, in a sample of opener completions

**Question (map #591, ticket #594, Chris 2026-09-22):** does any completion of the
opener hold two cells that see each other (row, column or box) whose cell numbers
are equal because different window-rank lists concatenate to the same digits
(the "coincidence" tie, e.g. `1|8 = 18`), so the two cells share a QQRR rank?
Always under the opener's clues and Chris's entered digits and uncircled marks.

**Sample.** Two count runs on the merged checker at `5fcb22a`, hypotheses on,
`--count 500 --workers 4 --timeout 300`, one per surviving corner. Both hit the
300 s ceiling, not the cap, so neither is a full enumeration:

| corner | completions found in 300 s | with a qualifying tie |
|---|---|---|
| tr | 120 | 21 |
| br | 125 | 14 |

**Every hit is the same shape.** Cell r4c1 reads the windows whose top-left cells
are r3c1 and r4c1; those carry the uncircled marks 1 and 8, so under the
hypotheses r4c1's number is always `1|8 = 18`. The tie appears whenever a
corner window in column 1 has quad rank 18: the window at r1c1 (then cell r1c1
reads `18`) in 31 grids, or the window at r8c1 (cell r9c1 reads `18`) in 4. The
tied cells are in the same column. Their QQRR is 1 when 18 is the smallest cell
number in the grid, otherwise 2. No hit involved a clued cell (r1c5 with QQRR 33,
or the corner carrying the 5), and no tied-window (equal four-digit value) tie
appeared at all.

**Not shown by this sample:** whether a tie exists anywhere other than column 1,
and whether one exists that does not rest on the marks 1 and 8. Both need a
model constraint, not a filter over a 300 s sample.

Four of the hit grids are presets at the top of
`docs/research/2026-09-22-qqrr-explorer.html`.

**Filter used** (run from the repo root; the logs are the checker's `--progress` output):

```python
import sys, re
sys.path.insert(0, "finders/qqrr")
import oracle
def grids(path):
    g, out = [], []
    for line in open(path):
        if re.fullmatch(r"([1-9] ){8}[1-9]\n", line):
            g.append([int(x) for x in line.split()])
            if len(g) == 9: out.append(g); g = []
        else: g = []
    return out
def sees(a, b):
    return a != b and (a[0]==b[0] or a[1]==b[1] or (a[0]//3==b[0]//3 and a[1]//3==b[1]//3))
for g in grids(sys.argv[1]):
    ranks, nums, cr = oracle.rank_grid(g)
    lists = {(r,c): [ranks[wr][wc] for wr,wc in oracle.windows_of(9,r,c)] for r in range(9) for c in range(9)}
    cells = list(lists)
    for i, a in enumerate(cells):
        for b in cells[i+1:]:
            if nums[a[0]][a[1]] == nums[b[0]][b[1]] and sees(a, b):
                print(a, b, nums[a[0]][a[1]], cr[a[0]][a[1]], "coincidence" if lists[a] != lists[b] else "tied-windows")
```

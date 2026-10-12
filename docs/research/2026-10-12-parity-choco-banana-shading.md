# Can a sudoku's parity be a Choco Banana shading?

Chris's question, 2026-10-12: in a normal 9x9 sudoku, shade the cells of one
parity. Can the result be a legal Choco Banana shading, where every shaded
(chocolate) group is a rectangle and every unshaded (banana) group is a
non-rectangle? No clues, no whisper, no renban: the shading rule only.

## Answer

| Case | Result | Time | Space covered |
|---|---|---|---|
| Odd cells shaded | proven impossible (CP-SAT `INFEASIBLE`) | 0.84 s | every sudoku grid |
| Even cells shaded | found (one grid) | 0.20 s | first grid only, not counted |

One run each, 1 worker, 300 s cap, neither reached it. The impossibility
rests on one engine and on the two encodings below being exact; no second
engine has repeated it.

The grid found, even cells in brackets (the shaded side):

```
 9 [2] 1   3 [6] 5   7 [8][4]
 3  7 [4]  9 [8] 1   5 [2][6]
[6][8] 5  [2] 7 [4]  3  1  9
[8][4] 3   5  1  7   9 [6][2]
 1  5 [2] [6][4] 9  [8] 7  3
 7  9 [6] [8][2] 3   1 [4] 5
[4] 3  7   1  9 [6] [2] 5 [8]
 5  1 [8] [4] 3 [2] [6] 9  7
[2][6] 9   7  5 [8] [4] 3  1
```

It was re-checked after the solve: rows, columns and boxes, then
`renbanana_verify.components` and `is_rectangle` on both sides, no violation.

## Method

A scratch script, not repo tooling. It builds the digits with
`renbanana_model.sudoku`, ties a parity boolean to each digit
(`d == 2 * half + odd`), and puts the shading rules on that boolean with the
repo's own `rectangle_lemma` (chocolate groups are rectangles) and
`forbid_banana_rectangles` (no banana group is a rectangle). Both are
documented exact in `finders/renbanana_model.py`.

Not done: counting the even-shaded grids, any clue set, any uniqueness.

## The script

```python
"""SCRATCH probe: does a sudoku grid exist whose parity classes form a
Choco Banana shading? Chocolate (shaded) groups are rectangles, banana
(unshaded) groups are non-rectangles. No clue, whisper or renban rule.
Encodings are grid-hunts' own (renbanana_model), both documented exact.

    uv run --project /home/caneff/src/grid-hunts python parity_probe.py OUT.jsonl
"""
import json, sys, time
sys.path.insert(0, "/home/caneff/src/grid-hunts/finders")
from ortools.sat.python import cp_model
from renbanana_model import CELLS, N, forbid_banana_rectangles, rectangle_lemma, sudoku
from renbanana_verify import components, is_rectangle

LIMIT = 300.0
out = open(sys.argv[1], "a")
for case, choc_is_odd in (("odd cells shaded", True), ("even cells shaded", False)):
    m = cp_model.CpModel()
    d = {p: m.new_int_var(1, 9, f"d{p}") for p in CELLS}
    odd = {p: m.new_bool_var(f"o{p}") for p in CELLS}
    for p in CELLS:
        half = m.new_int_var(0, 4, f"h{p}")
        m.add(d[p] == 2 * half + odd[p])
    sudoku(m, d)
    choc = {p: (odd[p] if choc_is_odd else odd[p].negated()) for p in CELLS}
    rectangle_lemma(m, choc)
    forbid_banana_rectangles(m, choc)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = LIMIT
    t = time.time()
    st = s.solve(m)
    row = {"case": case, "status": s.status_name(st), "seconds": round(time.time() - t, 2), "limit": LIMIT}
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        grid = {p: s.value(d[p]) for p in CELLS}
        is_choc = {p: (grid[p] % 2 == 1) == choc_is_odd for p in CELLS}
        bad = []
        for i in range(N):
            if sorted(grid[i, c] for c in range(N)) != list(range(1, 10)): bad.append(f"row {i}")
            if sorted(grid[r, i] for r in range(N)) != list(range(1, 10)): bad.append(f"col {i}")
        for b in range(9):
            if sorted(grid[b // 3 * 3 + i, b % 3 * 3 + j] for i in range(3) for j in range(3)) != list(range(1, 10)): bad.append(f"box {b}")
        bad += [f"choc group at {g[0]} not a rectangle" for g in components(is_choc, True) if not is_rectangle(g)]
        bad += [f"banana group at {g[0]} is a rectangle" for g in components(is_choc, False) if is_rectangle(g)]
        row["grid"] = ["".join(str(grid[r, c]) for c in range(N)) for r in range(N)]
        row["recheck_violations"] = bad
    out.write(json.dumps(row) + "\n"); out.flush()
    print(json.dumps(row))
```

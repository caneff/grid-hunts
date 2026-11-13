# New Rooms: Numbered Rooms where the first N cells share a region

Follows `2026-11-12-run-rooms-counting-circles.md` (the old run rule, Ballroom).
6x6, four connected 9-cell regions each holding 1-9, no repeats in rows or
columns, counting circles inside and outside the grid.

## Rule

N = the first digit looking in from a circled outside cell. Cells 1 to N are in
one region; cell N+1, if it exists, is in a different region. The clue is the
digit in cell N. So N = 1 is allowed (clue = first digit, cell 2 in another
region) and N = 6 needs no N+1 cell.

Chris switched from the old rule (cells 1 to N-1 in the first cell's region,
cell N outside it) because the new one reads more naturally. Ballroom stays on
the old rule.

## Findings

All solver results are from `scripts/nrmodel.py` (scratch CP-SAT model of the
new rule); "unique" means the second-solution check on that same model came
back INFEASIBLE. No independent uniqueness check exists. Each found layout was
re-checked against the rules in plain Python (`scripts/vb.py`).

- At most one clue can read 1, and if one does it is the only circle holding 1.
- A corner clued on both sides cannot be 1 (both clues would read 1).
- With all six clues c1T-c3T and r1L-r3L, the corner must be 2: 3 needs at
  least 10 cells in the corner region, 4 and 5 overflow too (hand proof).
  Chris ruled the 2 corner unusable for his opening, so r3L is trimmed.
- Opening with r3L trimmed and a full circled side with 5 of 6 first cells
  circled: only the top side works (bottom and right INFEASIBLE). There the
  uncircled first cell is forced to 1 and its clue reads 1.
- Full top, r1L and r2L both circled, r1c1-r1c3 circled: INFEASIBLE at 11, 12
  and 13 outside clues.
- Setup used for the hunts: full top and r1L circled, r2L not, the uncircled
  top first cell in c1-c3 (r1c4-r1c6 circled), outside values one 1 plus ten
  5-8 (plus extras from 2-4 above 11 clues), 36 circles.
  - 11 outside clues: feasible, unique layouts found.
  - 12: feasible, unique layouts found (extra clue r1L = 4).
  - 13, 14, 15: INFEASIBLE even with the 36-circle total dropped. Cause not
    worked out.
  - 10 (c3T dropped, no circled 1 outside): unique layouts found; there r1c3 is
    9, not 1, and the circled 1 sits in the grid.
- Region exhaustion, 11 clues: with the six region layouts in `drafts.md`
  banned, the master is INFEASIBLE (with 3,036 cuts and the swap-twin rule: at
  most one of 7, 8, 9 may have no circle). So every unique 11-clue layout in
  this setup uses one of those six. Two of the six were only seen in 12-clue
  drafts; 11-clue layouts on them were not hunted.

## Wording precedents (Logic Masters)

- Duality pack #3 "Chaotic X-Count" (000E38) states the new rule: "the first X
  cells in the corresponding row/column are in the same region (and the X+1th
  cell is in a different region)". There it is a pure region clue, not
  Numbered Rooms.
- Skybreaker (Dazed Out #8, 000SV4) states the old Ballroom rule as a separate
  "Chaos Clues" rule: "all cells up to the cell that contains the clued digit
  belong to the same region (The clued cell belongs to a different region)."
- Region Geometry (0009WX) and Region Geometry X (000A3X) require only that
  the first and Nth cells share a region.

The usual shape: the standard Numbered Rooms sentence unchanged, then the
region condition as a second sentence. Nobody adds an "N may not be 1" note.

## Files

- `drafts.md`: every unique 36-circle draft with its short link, regions,
  digits, outside clues and grid circles.
- `cuts-11.jsonl`: the alternative grids the 11-clue hunt cut on
  (digits, region labels); `cegar_new.py` loads them to resume.
- `scripts/`: snapshots of the scratch scripts. They hard-code the session
  scratchpad path and read hunt progress from `~/.cache/agent-jobs/`; edit the
  paths before rerunning.
  - `nrmodel.py`: the model. `newrule.py`: one-off feasibility CLI.
  - `cegar_new.py <cap-seconds> <outside-count>`: the cut loop. Env:
    `MAXFOUND`, `BANS` (colon-separated progress files to ban), `BANGRID`
    (skip found solution grids), `BANREG` (skip found region layouts),
    `FREETOTAL`. Rebuild of the 11-clue hunt:
    `MAXFOUND=1000 BANREG=1 uv run python cegar_new.py 10800 11`.
  - `vb.py`, `build_new.py`, `gen_newrooms.py`, `newrooms_list.json`: rule
    re-check, SudokuMaker link build (new-rule text), and the "New Rooms
    Drafts" artifact page.

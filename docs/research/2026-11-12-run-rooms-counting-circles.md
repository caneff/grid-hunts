# Run Rooms with counting circles: design findings

Session of 2026-11-12. Scratch CP-SAT model only (not a finder in this repo).
Every claim below was checked by a CP-SAT run, an independent Python checker,
or both; the proofs written out here are hand reasoning that matches the solver
verdicts.

## The ruleset

- 6x6 grid, four orthogonally connected 9-cell regions, each holding 1-9 once;
  no repeats in rows or columns.
- **Run rule (Numbered Rooms variant).** An outside clue looks into its line.
  Let X be the first digit. Cells 1..X-1 are in one region, cell X is in a
  different region, and the clue equals the digit in cell X. So X is 2-6, and
  X = 1 is never valid.
- **Counting circles** inside and outside the grid: a circled value w appears in
  exactly w circles. A circled outside cell is a run-rule clue with its value
  hidden. Uncircled outside cells carry no rule (no negative constraint).

## Findings

1. **No side can be fully clued.** Six valid clues on one side need six
   distinct first digits in 2-6. Solver: INFEASIBLE.
2. **A corner clued on both sides holds 3, 4 or 5.** 2 isolates the corner
   from its region; 6 makes the region an L of exactly 9 cells, which forces
   a clued next corner on that edge to X = 2 (also impossible).
3. **The total fixes the circled digit set.** Total = sum of the circled
   digits, so 45 - total = the sum of the uncircled digits.
4. **Swap twin.** If two digits from {1, 7, 8, 9} are both uncircled, swapping
   them everywhere preserves every rule: neither can be a first digit, and
   neither is read by a circled clue. Such a layout is never unique. It is a
   property of the digit set, not the total: the row-1 openings searched here
   forced sets like 1-6 (21), 2-7 (27), 1-7 or 2-6+8 (28) and 2-8 (35), each
   leaving two of {1, 7, 8, 9} uncircled, which explains why 50+ searched
   layouts at those totals all had 21+ solutions. Other sets with the same
   total (for example 35 without 2 and 8) are not ruled out.
5. **Supply.** The grid holds four copies of each digit, so a circled w >= 5
   needs at least w - 4 outside clues reading w. In a 36-circle puzzle with 9
   uncircled this forces 8,8,8,8,7,7,7,6,5 among the outside clues, every grid
   4-8 circled, and uncircled cells limited to 1, 2, 3 and 9.
6. **Corner opening.** Clues on c1-c3 top and r1-r3 left, with r1c1, r1c2 and
   r2c1 circled and r1c3, r3c1 left uncircled, force r1c1 = 3, r1c2 and r2c1 in
   {4,5,6}, r1c3 = r3c1 = 2, and both corner clues = 2. Circling r1c3 or r3c1
   breaks counting (four circled 2s).
7. **Totals for that opening** (with r1R/r2R/c5T/c6T and r1c5, r1c6, r2c6
   added): 30-32 impossible (the opening forces a circled 6 through r1R reading
   r1c2), 34 impossible, 35 never unique, 37 impossible; **36 works**.

## Search method that worked

Counterexample-guided loop: propose a layout plus grid that meets the design
rules, check uniqueness with a second model, harvest up to 20 alternate grids,
and add one cut per grid ("the layout must reject grid G unless G is its own
answer"). Cuts persist across runs. Asymmetric regions are enforced in the
model (for each of the 7 symmetries, some cell pair changes same-region
status). Re-optimizing a lexicographic score every round wasted most of the
runtime; threshold constraints with a feasibility solve were far faster.

## Results

Unique, asymmetric regions, 36 circles, all keeping the corner opening:

| Draft | Link |
|---|---|
| 5 | https://sudokumaker.app/p/TTzg8Q8mkz |
| 5b | https://sudokumaker.app/p/wtmchCPcLD |
| 6 (chosen) | https://sudokumaker.app/p/dq6GMRmzz9 |
| 7 | https://sudokumaker.app/p/KrCGD8Qf9Q |
| 8 | https://sudokumaker.app/p/QTqFm7NHpD |

Draft 6 solution: regions `AABBBB AAACBB DAACBB DACCCB DADCCC DDDDDC`,
digits `362745 457893 289461 615978 924136 173582`.

SudokuMaker's own solver cannot check these: it models neither the regions nor
the run rule.

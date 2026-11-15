# 9x9 Skyscraper Sudoku clued only with 5s

Question (Chris, 2026-11-15): the unique 9x9 Skyscraper Sudoku (3x3 boxes) with
the most clues, where every clue is a 5: given 5s inside the grid and outside
skyscraper clues equal to 5.

## Result: 25 clues (16 outside + all 9 inside 5s), and 25 is the maximum

- **Upper bound by hand: 29.** A line clued 5 at both ends needs 4 visible
  buildings before its 9 and 4 after, so its 9 is the middle cell; only one
  row (and one column) can hold its 9 in the middle, so at most 10 row clues
  and 10 column clues.
- **Solver bound: 16.** Maximising the number of lines that show 5, over all
  9x9 sudokus, solved OPTIMAL at 16 on the first pass (`scripts/sky5.py`), so
  no grid shows more than 16 fives on its frame.
- **That optimum is unique.** The first 16-line grid, with every 5 given and
  all 16 outside 5s shown, has exactly one solution, so no cut was needed.

Grid (rows):

    671239458
    342518967
    985647231
    216753849
    834921576
    759864123
    123496785
    598372614
    467185392

Outside 5-clues: c1B r2L r3R c3T r4L c4T c4B c5T r6R c6B r7L c7B r8R c8T r9L c9B
(rN = row N from the Left/Right, cN = column N from the Top/Bottom).
Inside givens: every 5.

## Verification

`scripts/sky5_verify.py` re-checks on sudokumaker-custom-constraints'
`examples/skyscraper/build_size.py` `add_visibility` and `sky`, with
`sudoku_kit.cpsat.solve_unique`: every listed clue reads 5, the grid shows
exactly 16 fives, and the board is unique. The hunt model itself
(`scripts/sky5.py`) is a scratch model; the re-check is on the repo model.
Run from the custom-constraints checkout:
`uv run --project ~/src/grid-hunts python <path>/sky5_verify.py`.

SudokuMaker link (built with the skyscraper example's `RingGlobal` lane, so it carries the two-clue DP component; opens with nothing entered, 16 of 40 frame cells shown, 25 givens):

https://sudokumaker.app/p/jhdKnQBbk8

# GLOSSARY

The ubiquitous language of this repo. Read this before exploring; it defines
the terms the docs and finders use, and points at the doc that holds each
detail.

## Glossary

- **finder** — code that searches for grids fitting a rule, under `finders/`.
  Unlike **generation**, which builds one example's puzzle, a finder explores a
  rule's space for candidates worth building on.
- **hunt** — one run of a finder: it writes candidates and a summary to an
  output directory. Not a finder: one finder runs many hunts.
- **hunt protocol** — the shared contract a finder follows so every hunt writes
  the same output directory, dedupes the same way, and can resume after a
  kill. It carries no finder rule.
- **finder rule** — a rule a finder states itself because gridfind has no layer
  for it. It stays a finder rule until it is **promoted**: turned into a
  gridfind layer with its fixtures.
- **board question** — one question asked of one fixed board: is it
  feasible, is it unique, list its solutions, the largest value of a named
  quantity, which clues can be dropped one at a time, or does a mark hold in
  every solution. Not a hunt: a hunt searches for boards, a board question
  asks about one (#36). _Avoid_: query, board query.
- **capped** — an answer to a board question that a time or count limit
  stopped before it was settled. A capped answer is never read as unique,
  held or complete. Its opposite is **complete**.

### U-Bahn terms (`finders/ubahn/`)

U-Bahn is a pencil puzzle, not a sudoku. **Line** and **path** already mean
other things above, so the U-Bahn finder never uses either word. Rules and
sources: `docs/research/2026-10-10-u-bahn-cpsat-finder.md`.

- **network** — the whole drawing of one U-Bahn solution: the set of edges
  that are on, an edge joining the centres of two orthogonally adjacent
  cells. A network has at least one edge, no dead end, never leaves the
  board, and is one connected whole.
- **arm** — one of the up to four edges at a cell that are in the network. A
  cell has 0, 2, 3 or 4 arms; a cell with one arm is a dead end.
- **piece** — what a cell's arms make: a **turn** (two arms at a right
  angle), a **straight** (two opposite arms), a **branch** (three) or a
  **cross** (four). A piece is the same piece in any rotation. A cell with
  no arm is **blank** and holds no piece.
- **kind** — what a cell is: one of the four pieces, or blank. Five in all,
  always in the order turn, straight, branch, cross, blank. A condition
  counts cells of one kind, and a hunt dedupes on the grid of kinds.
- **outside number** — how many cells of one kind a row or column holds. A
  U-Bahn puzzle gives the solver four per row and per column, one per piece;
  some puzzles also show a fifth, for blank. The finder records all five,
  and the **full set** is all of them. The blank number is the row's or
  column's length less the other four, so it tells the solver nothing new.
  Not a **clue**, which is a ring cell of an outside-clue group.

The hybrid lays Choco-Banana over a U-Bahn board (spec #781; rules read by
`finders/ubahn/hybrid.py`). A **value** is what a cell is worth there: a grid
cell's piece (blank 0, turn 1, straight 2, branch 3, cross 4), a number
cell's outside number. A hybrid **region** is a maximal orthogonally connected
set of cells whose values share a parity, grid cells and number cells
together; it is not the region-building **region** below, which shares a
digit.

- **number cell** — a cell of the board that holds one outside number. They
  lie in strips above the grid and to its left, one strip per kind: cross,
  branch, straight, turn from the outside in, with the blank strip an optional
  fifth outside the cross. The solver of a hybrid is given none of the
  numbers; each is read from the network.
- **icon cell** — the cell at the head of a strip, showing the piece the
  strip counts. Decoration, and a wall: no region holds one. The corner
  outside the icon cells is off the board.
- **chocolate** — a region of even values. It must be a rectangle; a square
  counts.
- **banana** — a region of odd values. It must not be a rectangle, so a
  single odd cell on its own is never one. Written **banana region** where
  bananas are counted: the finder's `--min-bananas N` asks for N or more.
- **circle** — a condition on one cell, grid cell or number cell: the cell's
  value equals the number of cells in its region. The circle itself carries
  no digit; a circled number cell shows its number only when that number is a
  **given number**. An uncircled cell promises nothing about size.
- **given number** — a number cell whose outside number is printed on the
  hybrid's Penpa+ link (`hybrid_finder.py links --numbers`). Every other
  number cell is drawn empty; the solver is not asked to enter any of them.
- **valid circle** — a cell a circle could sit on in a given grid: its value
  equals the number of cells in its region. Every circle of a grid's
  conditions is one; the picture (`hybrid_finder.py render`) rings a circle
  that is a condition and no other valid circle.
- **window** — a 2x2 of board cells, grid cells, number cells or both, all
  four on the board, so no window holds an icon cell. Named by its top-left
  cell: `r2c3`, `r4:turn`, `c1:straight`. With the blank strip on, its cells
  make windows like any other.
- **checkerboard window** — a window whose diagonal cells share a parity of
  value and whose side-by-side pairs differ: odd-even over even-odd, or
  even-odd over odd-even. `hybrid.checkerboard_windows` lists a grid's.
- **Battenberg marking** — a condition on one window: it is a checkerboard
  window (spec #20; the finder's `--battenberg "CELLS"`). A window with no
  marking is free, unless the **negative constraint** is on
  (`--battenberg-only`): then every window with no marking is not a
  checkerboard window, the windows in the number strips included.
- **mirror set** — the image of a set of Battenberg markings under the
  reflection in the main diagonal, each window going to the window named by
  its top-left cell's image; the two sets are a **mirror pair**. Where the
  conditions keep the reflection, `hybrid_finder.py fewest-markings` solves
  one set of a pair and copies the answer to the other. A set is always
  spelled with its windows in board order, columns' number cells first.
- **engine** — a solver the hybrid's rules are written on, picked by the
  finder's `--engine`: `cpsat`, `pysat-lazy` or `pysat-propagator`. Every
  engine answers the same two calls, a grid for a seed and a classification.
- **connectivity cut** — a clause added to a solve after it proposed a full
  grid whose network is in several parts: it refuses that grid and the solve
  goes on. Not the region-building **cut** in the glossary of
  `caneff/sudokumaker-custom-constraints`.

### Banabner terms (`archive/finders/banabner/`)

Dutch Chocolate Banabner is a sudoku with a chocolate and banana shading
(spec #758; rules read by `archive/finders/renbanana_verify.py` at difference 4 with
the nabner rule). **Chocolate**, **banana** and **circle** above are the
U-Bahn hybrid's; here they mean the following.

- **group** — a maximal orthogonally connected set of cells of one shading.
  A **chocolate group** is a rectangle; a **banana group** is not one.
- **Dutch Chocolate** — the chocolate rule: two orthogonally adjacent
  chocolate cells hold digits at least 4 apart. Renbanana's German Chocolate
  asks for 5.
- **nabner** — the banana rule: no two digits of one banana group are equal
  or consecutive. The reverse of Renbanana's renban, where a group's digits
  are a run. A nabner group holds at most five cells, and a 5-cell one holds
  exactly 1, 3, 5, 7 and 9.
- **circle** — a cell whose digit equals the number of cells in its group,
  chocolate or banana.
- **forced circle** — the circle on the 5 of a 5-cell banana group. Every
  such group has one whatever the shading, so it tells the solver nothing.
- **lineup** — the page that shows every checked grid of a puzzle type as a
  card, with filters and sorts: `archive/finders/banabner/build_lineup.py` builds the
  Banabner Lineup, `archive/finders/renbanana/tools/build_lineup.py` Renbanana's.
- **circle score** — the number a lineup ranks its grids by. On the Banabner
  Lineup it is the number of groups holding a circle, forced circles left
  out.

### Halver + between-line terms (`finders/halver_between/`)

A classic 9x9 sudoku with hidden halvers and between lines (spec #39).
**Line** and **circle** already mean other things above; in this section,
and only here, they mean the following.

- **halver** — one of nine cells, one per row, column and box, whose digits
  are 1 to 9 once each. The solver is not told which cells they are, so their
  places are part of the answer. Unique means one digit grid and one halver
  placement.
- **value** — a halver's digit / 2, exactly (a halved 7 is 3.5, a halved 1
  is 0.5); any other cell's digit. A halved 2k and a plain k share a value.
- **doubled value** — twice the value: a halver's digit, twice any other
  cell's digit. The code compares doubled values so every comparison is an
  integer one.
- **between line** (**line** here) — a king-step path with a circle at each
  end, whose body cells' values lie strictly between the two circles'
  values, whichever circle is larger. Circles of equal value leave no body
  value possible.
- **circle** — one end cell of a between line. Lines may share a circle.
- **body** — the cells of a between line other than its two circles. No
  body cell is ever the halved 1 (0.5) or a plain 9, the board's smallest
  and largest values.
- **mark** — a deduction Chris pencilled on the board (`marks.json`), checked
  against every solution and never posted as a constraint.
- **target grid** — one full solution of the current lines, picked by a hunt
  seed; the lines it adds hold in the target and rule out the current second
  solution.
- **second solution** — the solution other than the target that the rule
  check returns while the current lines are not unique.
- **separating line** — a line of a legal shape that holds in the target
  and fails in the second solution (`candidates.separating_paths`).
- **free cell** — a cell on no line, so still able to be a body cell. A new
  line takes its body cells and any circle not already on a line; cells,
  not solver time, are what a hunt seed runs out of.

### Halver + lockout-line terms (`finders/halver_lockout/`)

A classic 9x9 sudoku with hidden halvers and lockout lines, on an empty board
(spec #52). **halver**, **value**, **doubled value**, **mark**, **target
grid**, **second solution**, **separating line** and **free cell** mean what
the halver + between-line section says; those are the shared halver layer's
(`finders/halver/`). The between section's **line**, **circle** and **body**
do not apply here; in this section, and only here, these mean the following.

- **lockout line** (**line** here) — a king-step path with a diamond at each
  end. The two diamonds' values differ by at least the gap, and every body
  cell's value is strictly below the smaller diamond's or strictly above the
  larger one's, never between them or equal to either. SudokuMaker's
  constraint type 407.
- **diamond** — one end cell of a lockout line. Lines may share a diamond.
- **gap** — the least difference between a line's two diamonds' values: 4
  on every line, on values (so 8 on doubled values). A halved 1 (0.5) and a
  plain 9 are 8.5 apart but can never be a line's diamonds: no value lies
  outside them.
- **body** — the cells of a lockout line other than its two diamonds. A body
  may sit on both sides of the diamonds' range, and its cells take the
  board's extreme values (the halved 1, the plain 9) as freely as any other.

### Doppelganger + Full Rank terms (`finders/doppelganger_rank/`)

A 9x9 Doppelganger sudoku with Full Rank clues. Rules and sources:
`docs/research/2026-10-22-doppelganger-full-rank-rules.md`. **Clue** and
**value** already mean other things above; in this section they mean the
following.

- **doppelganger** — the board rule: every row, column and box holds one 0
  and eight of the digits 1 to 9. The solver is not told where the 0s are.
- **missing digit** — the one digit of 1 to 9 that a row, column or box does
  not hold. No two rows miss the same digit, nor two columns, nor two boxes;
  a 0's row, column and box miss three different digits.
- **notespace** — the cells outside the grid where the solver writes the
  missing digits: one cell per row in a strip right of the grid, one per
  column in a strip below it, and a 3x3 for the boxes.
- **rank clue** (**clue** here) — a number outside the grid at one end of a
  row or column: the rank, 1 the lowest, of the number that row or column
  makes read away from the clue, among the 36 numbers the 9 rows and 9
  columns make read both ways. A 0 is read as the digit 0, so every number
  has nine digits. Equal numbers share a rank: a number's rank is 1 more
  than how many of the 36 are strictly smaller.
- **mark** — a digit Chris entered on the opening board as a deduction from
  its clues, in the grid or the notespace: checked against every solution,
  never posted as a constraint. The halver section's **mark** in this rule.

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
  conditions is one; the picture (`hybrid_finder.py render`) rings them all.
- **engine** — a solver the hybrid's rules are written on, picked by the
  finder's `--engine`: `cpsat`, `pysat-lazy` or `pysat-propagator`. Every
  engine answers the same two calls, a grid for a seed and a classification.
- **connectivity cut** — a clause added to a solve after it proposed a full
  grid whose network is in several parts: it refuses that grid and the solve
  goes on. Not the region-building **cut** in the glossary of
  `caneff/sudokumaker-custom-constraints`.

### Banabner terms (`finders/banabner/`)

Dutch Chocolate Banabner is a sudoku with a chocolate and banana shading
(spec #758; rules read by `finders/renbanana_verify.py` at difference 4 with
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
  card, with filters and sorts: `finders/banabner/build_lineup.py` builds the
  Banabner Lineup, `finders/renbanana/tools/build_lineup.py` Renbanana's.
- **circle score** — the number a lineup ranks its grids by. On the Banabner
  Lineup it is the number of groups holding a circle, forced circles left
  out.

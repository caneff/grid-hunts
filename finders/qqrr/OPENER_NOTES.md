# QQRR opener — what the link holds and what Chris ruled

Source: `OPENER_LINK.txt` (decoded to `opener.json` via gridfind's `link_file.py`, 2026-09-21).
9x9, regular boxes, 0 givens, 40 non-given cells carry entered values or colors.
Nothing in the link is a solver-readable constraint: window-rank clues are
cosmetic symbols (type 2002), the cell clue is a cosmetic cage (type 2001).

## Rule (settled in the wayfinder grill)

- **Window value**: the four digits of a 2x2 window read TL, TR, BL, BR, concatenated.
- **Quad rank (QR)**: SQL `RANK` of a window's value among all 64 windows.
  1 = smallest; ties share the lower rank; ranks after a tie are skipped.
- **Cell number**: the up-to-four QRs of the windows containing a cell,
  concatenated **unpadded** in reading order of the windows' top-left cells.
  Corner cells read one QR, edge cells two, interior cells four.
- **Quad quad rank rank (QQRR)**: SQL `RANK` of a cell's number among all 81 cells.
  Same tie semantics. Given as a single-cell cage value.
- Plain 9x9 sudoku underneath. No custom component in this effort.

## Window-rank marks in the link

`"QR Ranks"` symbols, `[x, y]` = grid intersection. The mark sits on the point
between four cells, and the window it marks is those four cells: top-left
(row y-1, col x-1), 0-based. Fact, ruled at #598: all 6 marks have an entered
top-left digit inside their rank's leading-digit band under this mapping, and
the hypotheses-on run is feasible (multiple, 3.1 s).

| symbol | window TL (row, col) 0-based | Chris's status |
|---|---|---|
| `10` at (6,6), circled | (5,5) | **real QR clue** |
| `58+` at (4,4), circled | (3,3) | **assumption**: a QR clue of 58 or more will sit here |
| `51-56` at (5,2), circled | (1,4) | **assumption**: a QR clue between 51 and 56 inclusive will sit here |
| `9` at (2,3) | (2,1) | **hypothesis** (deduced while working): second run only, with the entered digits |
| `8` at (1,4) | (3,0) | **hypothesis** (deduced while working): second run only, with the entered digits |
| `1` at (1,3) | (2,0) | **hypothesis** (deduced while working): second run only, with the entered digits |

## Cell-rank marks

- **QQRR 33** cage on cell (row 0, col 4): a real clue.
- **Assumption (not in the link)**: a QQRR clue of **5** will sit in one of the four
  corners; which corner is undecided. The model treats it as a disjunction over
  the four corners (or four runs).

## Entered digits (non-given values Chris believes are forced from the above)

```
row 0: . . . 7 . . . . .
row 1: 9 . . 2 8 . . . .
row 2: 1 2 8 . . . . . .
row 3: 2 1 . 9 . . . . .
row 4: . . . . . . . . .
row 5: . . . . . 2 8 . .
row 6: . . . . . . . . .
row 7: . . . . . . . . .
row 8: 8 . . . . . . . .
```

Treated as hypotheses: the checker runs once with clues only and once with
clues plus these digits.

## Cell colors

Rows 0 and 7 carry color 512, columns 0 and 7 carry color 16 (528 where they
cross). Visual aid only, ignored (Chris, 2026-09-21).

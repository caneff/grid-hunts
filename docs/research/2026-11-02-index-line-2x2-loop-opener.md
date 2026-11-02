# Index line + anti-Battenberg: the 2x2 loop opener

Opener idea for the index line + anti-Battenberg 9x9 (#91). Counts come from
two scratch scripts, not a repo model; #91's checker is the repo model and has
not re-run them. No whole-puzzle layout has been tested for uniqueness.

## A 2x2 loop

An index line of four cells drawn around one 2x2 window holds 1 to 4. Of the
10 valid index fills, 4 survive anti-Battenberg. Each survivor has exactly two
digits in their own positions, and its swapped pair sits next to each other on
the loop. The odds always sit side by side, and each of the four orientations
has exactly one fill. With the diamond top-left, running clockwise:

| Fill (top/bottom) | Line from the diamond | Odd digits |
|---|---|---|
| 12/34 | 1243 | left column |
| 21/43 | 2134 | right column |
| 13/42 | 1324 | top row |
| 42/13 | 4231 | bottom row |

The line's positions 1,3 and 2,4 are the window's diagonals for any diamond
corner and direction, so the same four line fills hold for every drawing.

Checked on full 9x9 anti-Battenberg grids (CP-SAT, one worker): exactly these 4
of the 10 fills extend, at r1c1, across a box border at r1c3, and at r4c4.

## Two loops

Both loops below use the same drawing, diamond top-left and clockwise.

- **Same two rows, different boxes: impossible.** The rows' other cells must
  hold 5 to 9, and the third box's six cells in those rows cannot fit in five
  digits. Sudoku alone rules this out. CP-SAT agreed for r1c1 + r1c4 and
  r1c1 + r1c5: 0 of 16 pairs of the four fills extend. Those runs had
  anti-Battenberg on.
- **Sharing one row: 6 of 16 extend** (r1c1 + r2c4, and r1c1 + r2c5). Both loops
  are 13/42, or both are 42/13, or each is 12/34 or 21/43 (4 pairs).

## Shapes that do less

Local count over the shape's own cells only, for 3x3 shapes with every window
inside the shape: no position loses any digit. The ring of 8 around a box
centre keeps 312 of 764 fills with its diamond on a corner and 548 of 764 on an
edge. The 9-cell snake and spirals each keep 1128 of 2620.

The three 9-cell counts match for a reason: an orthogonal line alternates
checkerboard colours, so position parity equals cell colour on all of them.

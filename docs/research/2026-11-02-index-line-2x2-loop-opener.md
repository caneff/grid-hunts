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

- **Same two rows: 2 of 16 extend, when the placement works at all.** The two
  top rows must be disjoint, which leaves one loop 13/42 and the other 42/13,
  in either order. Every working placement gives exactly those two pairs.
  Tested for all 21 non-overlapping column pairs on r1-2, r2-3 and r3-4:
  - **r3-4 (across a band border):** 15 of 21 work. The 6 that fail are the
    side-by-side pairs (c1+c3, c2+c4, c3+c5, c4+c6, c5+c7, c6+c8): the window
    between the loops is forced to be a Battenberg, `3 4 / 2 1` or `2 1 / 3 4`.
  - **r1-2 and r2-3 (inside a band):** 5 of 21 work: left columns c1+c6, c2+c6,
    c3+c6, c3+c7, c3+c8. An earlier version of this note called all such pairs
    impossible, generalising from r1c1 + r1c4 and r1c1 + r1c5. Its counting
    argument only applies when a third box keeps all six cells in those rows.
- **Sharing one row: 6 of 16 extend** (r1c1 + r2c4, and r1c1 + r2c5). Both loops
  are 13/42, or both are 42/13, or each is 12/34 or 21/43 (4 pairs).

## Touching loops, any drawing

Two touching loops on the same two rows (columns c and c+2), each drawn from any
of its 8 diamond corner and direction choices:

- **r3-4:** all 6 column placements work, each with 16 pairs of fills. Only the
  pairs on c1+c3 were listed: the odds sit in columns in both loops, never rows.
- **r1-2 and r2-3:** 0 pairs extend, at all 6 column placements.
- **Same drawing:** none work on any of these rows, as above. On c1+c3, left
  diamond top-left clockwise needs the right loop's diamond bottom-right
  clockwise or bottom-left anticlockwise, for 4 fills: left 12/34 or 21/43, right
  43/21 or 34/12.

## Shapes that do less

Local count over the shape's own cells only, for 3x3 shapes with every window
inside the shape: no position loses any digit. The ring of 8 around a box
centre keeps 312 of 764 fills with its diamond on a corner and 548 of 764 on an
edge. The 9-cell snake and spirals each keep 1128 of 2620.

The three 9-cell counts match for a reason: an orthogonal line alternates
checkerboard colours, so position parity equals cell colour on all of them.

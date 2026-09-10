# Renbanana feasibility — German Chocolate + renban bananas

Question (#347): does a grid exist under standalone Choco Banana sudoku with a
German whisper on chocolate and a renban on every banana group? And if so, how
much does the rule set constrain on its own — enough to need no clues?

**Verdict: SAT, in 29 s. The rule set alone is far too loose to be clue-free —
one shading admits 312 digit grids.**

## The rules modelled

1. Normal 9x9 sudoku.
2. A free binary shading of every cell: chocolate or banana. Nothing derives
   it, and it is **not part of the solution check** — in the app it is colouring
   the solver does for themselves. A digit grid is valid iff *some* shading
   satisfies 3-6.
3. Every maximal orthogonally connected chocolate group is a rectangle.
4. Every maximal orthogonally connected banana group is not a rectangle. A 1x1
   cell and a 1xN strip are rectangles, so a banana group needs >= 3 cells in
   an L or worse.
5. German Chocolate: orthogonally adjacent chocolate digits differ by >= 5.
   (Dutch is the same rule at >= 4, so German is strictly stronger.)
6. Renbanana: every banana group's digits are distinct and consecutive — hence
   at most 9 cells.

"Group" is a *maximal* component, so no two chocolate groups touch orthogonally
and no two banana groups do: every rectangle's whole orthogonal border is
banana, and vice versa. Chocolate walls therefore cannot cross — a plus or a T
is not a rectangle.

## Witness

Chocolate in brackets, banana bare.

```
 4   6   2   7  [5]  9   1  [8] [3]
 9   3  [1] [6]  8  [2]  7   5   4
 5   8  [7] [1]  4   3  [9]  6   2
 1  [5]  6   2  [9]  7  [4]  3   8
[2]  9  [8]  4  [3]  6   5  [7] [1]
[7]  4  [3]  5   1  [8] [2]  9   6
 6   7  [9]  3  [2]  1   8   4   5
 8   1   5  [9]  6  [4]  3   2   7
 3   2  [4]  8   7   5  [6] [1] [9]
```

Verified independently of the model that produced it (`verify.py`, rewritten
from the rules rather than reusing the solver's encoding): sudoku holds, all 16
chocolate groups are rectangles, all 7 banana groups are non-rectangles, every
banana group is a renban, every chocolate adjacency differs by >= 5.

- Chocolate group sizes: 1x7, 2x6, 3x2, 4x1 — sixteen groups, the largest four
  cells.
- Banana group sizes: 4, 6, 6, 9, 9, 9, 9.

## How tight is it?

- **Shading is the easy half.** The shape rules plus the size cap yielded legal
  shadings in seconds — 33 cuts to the first one.
- **Digits are the filter.** Of the first 3 shadings passing rules 3, 4 and the
  cap, 2 admitted no digit fill at all; the third did.
- **But a surviving shading is loose.** Enumerating digit grids on the witness
  shading alone: **312**, exhaustively, in 0.7 s. Across all shadings the count
  is far larger.

So a clue-free puzzle is dead: the rules do not come close to pinning a grid.
Clues are needed, and circles (group size) are the ones that speak about the
shading — kropki and givens only constrain digits, which is not the
under-determined layer.

## Three hand lemmas worth having as solve deductions

Both derived by hand, both consistent with the witness.

- **No 5 in a chocolate group of size >= 2.** A chocolate neighbour of a 5 must
  differ by >= 5, so it would have to be <= 0 or >= 10. Every 5 on the grid is
  therefore banana or a lone 1x1 chocolate cell. The witness has its chocolate
  5 at r1c5 as a 1x1 group.
- **Chocolate rectangles are low/high checkerboards.** Two digits from
  {1,2,3,4} differ by <= 3, as do two from {6,7,8,9}. So every chocolate
  adjacency pairs a low with a high, and the rectangle's parity classes are
  fixed before any digit is placed. A width-*b* row of a rectangle holds
  ceil(b/2) cells of one class in one grid row, all distinct from a 4-element
  set, so no chocolate rectangle has a side longer than 8. Exhaustive
  enumeration sharpens this a long way — see `RECTANGLE-CATALOGUE.md`, which
  also gives the per-cell support matrices.

- **A chocolate circle is never a 5, and a circled chocolate 9 is a 3x3.** A
  circle gives its group's size, so a circled 5 would mean a five-cell group —
  2+ cells, so its 5 needs a chocolate neighbour differing by >= 5, impossible.
  A circled 9 rules out 1x9 and 9x1, which are a whole row or column and so
  contain the 5, leaving 3x3. Whether a 3x3 chocolate rectangle exists at all is
  unverified: its checkerboard puts five cells of one class in the rectangle,
  all needing low digits from the four-element set {1,2,3,4}, distinct within
  each row and column. Tight, but not obviously dead.

This is why circles are worth placing on chocolate rather than banana: on
chocolate the number is a rectangle area and factors into a short list of
shapes, while on banana it only says how many cells an L-or-worse blob has.

## Which chocolate rectangles can exist

A circle on chocolate reads the group's area, so this table is the list of
circle values the puzzle can actually offer. Every SAT row is a verified
witness: the shape was found by search, then digits were solved exactly on that
shading and the whole grid re-checked against all six rules from scratch.

| shape | area | verdict | note |
|---|---|---|---|
| 1x1 .. 1x4, 2x2 | 1-4 | SAT | 2x2 appears in the first witness |
| 1x5 | 5 | SAT | but a 5-cell group can never carry a circle — see below |
| 1x6 | 6 | SAT | |
| 2x3 | 6 | **SAT** | `witness-2x3.png`, block `2 8 3 / 8 2 9` at r1c3 |
| 1x7 | 7 | **SAT** | verified witness in `CIRCLE-VALUES.md`, plus a proof: legal only at cols 1-7 or 3-9, never 2-8 |
| 1x8 | 8 | **UNSAT** | dies at the shading stage, before digits |
| 2x4 | 8 | **SAT** | verified witness in `CIRCLE-VALUES.md` |
| 1x9, 9x1 | 9 | UNSAT | a whole row or column, so it contains the 5 |
| 3x3 | 9 | **SAT** | `witness-3x3.png`, block `1 8 2 / 7 1 8 / 2 9 3` at r6c1 |

**A rectangle existing is not the same as a circle being placeable in it.** A
circle reads its group's area, so the circled cell's digit must equal that area
and must live inside the group. The 2x3 witness above is `2 8 3 / 8 2 9`, which
holds no 6, so it cannot carry a circle. Confirmed circle values so far:

Resolved in #374 — **every value except 5 is placeable.** The verified
witnesses, the search rates and the 1x7 offset proof are in
**`CIRCLE-VALUES.md`**.

| circle | status |
|---|---|
| 1, 2, 3, 4, 6, 7, 8, 9 | **confirmed** — each with a verified witness in `CIRCLE-VALUES.md` |
| 5 | **impossible** — a 5-cell group has 2+ cells, and no multi-cell chocolate group may hold a 5 |

German's partner sets are what make this hard, and they are tiny: 6 pairs only
with 1, 4 only with 9, 3 with {8,9}, 7 with {1,2}, 2 with {7,8,9}, 9 with
{1,2,3,4}, 1 with {6,7,8,9}, and 5 with nothing. Consequences:

- A **circled 6** must sit at a *corner* of its 2x3, or an *end* of its 1x6: an
  edge-centre cell has two neighbours in the same row, and both would have to be
  1.
- A **circled 4** in a 2x2 needs a 9 on both of its neighbours, and those two
  sit in different rows and columns, so **the 2x2 must straddle a box boundary**
  or the 9s collide. The fourth cell touches both 9s, so it is at most 4. In a
  1x4 the circled 4 must be at an end.
- A **circled 9** forces a 3x3 straddling the box band, as above.

**A circled 9 is the strongest clue in the puzzle.** It forces a 3x3, and that
3x3 must straddle the box band — a box-aligned 3x3 holds all nine digits,
including the 5 that no multi-cell chocolate group may contain.

**Why 1x8 fails**, and it is the size cap, not the whisper: raising the banana
cap from 9 to 12 makes the shading satisfiable again (17 shadings found where
the capped model had none). A long thin strip runs a wall of banana down both
long edges, and chopping those into groups of at most 9 needs more chocolate,
which may not touch the strip. The whisper itself is not the obstacle — the
arithmetic is fine: a 1x8 strip has exactly one legal digit sequence up to
reversal, `4-9-3-8-2-7-1-6`, since the 5 is excluded and 4 and 6 each have only
one legal partner so they must be the ends. 1x7 admits 8 sequences and 1x6
admits 31.

## Method and caveats

Two stages, because solving shading and digits jointly converged badly.

- Stage 1 searches shadings only. Rule 3 goes in exactly via the standard
  lemma: a colour's components are all rectangles iff no 2x2 window holds
  exactly three of that colour. The renban size cap goes in structurally with
  component labels — adjacent banana cells share a label, and at most 9 banana
  cells may carry one label. Distinct components can always choose distinct
  labels, so this is equivalent to the cap, not stricter. Rule 4 stays lazy:
  solve, find a banana component that is a rectangle, cut exactly that pattern
  (its cells banana, its whole border chocolate).
- Stage 2 fixes the shading and solves digits: sudoku, the whisper on chocolate
  adjacencies, and per banana group AllDifferent plus max - min == size - 1.
  A shading whose stage 2 is UNSAT is cut whole and stage 1 continues.

Caveat: an earlier attempt enforced the size cap by cutting one oversized
banana component at a time. It never found a legal shading in 150 s (2313
cuts) — the solver simply kept producing one large blob. The cap has to be
structural. Anyone re-running this should not read that earlier failure as
evidence of infeasibility.

A faster model was tried for the shape questions, encoding renban up front
instead of by cuts: label each banana cell, force adjacent banana cells to share
a label, and require each label's digit set to be distinct and contiguous. **It
is unsound as written** — two disjoint components may take the same label, so
the constraint lands on their union and lets non-renban groups through. It
produced a "solution" with six broken banana groups. It is still useful as a
*shading generator*, since the shading rules it enforces are exact; the digits
are then solved exactly on that fixed shading and the result verified. Both new
witnesses came out of that pipeline. Anyone reviving the encoding must first
make labels canonical, so that at most one component can claim a label.

Scripts live in the repo, not a session scratchpad (#380). The pipeline above
is `docs/research/renbanana_cpsat.py`, with `renbanana_render.py` for pictures
and `renbanana_verify.py` — the checker written from the six rules rather than
from the solver's encoding — for the from-scratch re-check every candidate goes
through.

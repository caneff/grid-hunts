# Renbanana — which circle values are placeable on chocolate

Question (#374): a circle reads its group's size. On chocolate that group is a
rectangle, so the circled cell's digit must equal the rectangle's area *and*
sit inside the rectangle. Which of 1..9 can actually appear?

Rules, shapes and the earlier witnesses are in `FEASIBILITY.md`; this doc only
resolves the circle-value table. The digit half of every row below is settled
exhaustively in **`RECTANGLE-CATALOGUE.md`**, which enumerates every legal
chocolate rectangle and its support matrix — read that first if you want the
"which digits can sit where" answer rather than the "is it placeable" one.

**Verdict: every value except 5 is placeable. 1, 2, 3, 4, 6, 7, 8 and 9 all
have verified witnesses; 5 is impossible. The table is closed.**

## The table

| circle | status | witness / argument |
|---|---|---|
| 1 | **confirmed** | `[1]` alone at r1c3 in the 2x4 grid below (four such cells in that grid) |
| 2 | **confirmed** | 2x1 at r5c1 in the `FEASIBILITY.md` witness, digit 2 at r5c1 |
| 3 | **confirmed** | 3x1 at r5c3 in the `FEASIBILITY.md` witness, digit 3 at r6c3 |
| 4 | **confirmed** | 2x2 at r3c3, digit 4 at r4c4 — grid below |
| 5 | **impossible** | a 5-cell group has 2+ cells, and no multi-cell chocolate group may hold a 5 |
| 6 | **confirmed** | 2x3 at r3c7, digit 6 at r4c9 — grid below |
| 7 | **confirmed** | 1x7 at r5c3, digit 7 at r5c8 — grid below |
| 8 | **confirmed** | 2x4 at r6c6, digit 8 at r6c8 — grid below |
| 9 | confirmed earlier | 3x3 at r6c1, digit 9 at r8c2 (`witness-3x3.png`) |

Every "confirmed" row was re-checked from scratch by an independently written
checker (`verify.py`, rewritten from the six rules, not from the solver's
encoding): sudoku, chocolate components all rectangles, banana components all
non-rectangles, German whisper on every chocolate adjacency, renban on every
banana component, plus the circle demand itself.

## Shape rows resolved

`FEASIBILITY.md` left two shapes unresolved. Both are now settled.

| shape | area | verdict | evidence |
|---|---|---|---|
| 1x7 | 7 | **SAT** | the 1x7 grid below, verified; plus the offset proof below |
| 2x4 | 8 | **SAT** | the 2x4 grid below, verified |

### The 1x7 offset result (a proof, not a search)

A 1x7 chocolate strip is a shading question first. Running the shading stage to
exhaustion at each of the 27 horizontal positions gives a clean split:

- **cols 1-7 and cols 3-9: a legal shading exists**, in every one of the nine rows.
- **cols 2-8: NO legal shading exists**, in every one of the nine rows.

That second line is a proof, not a failed search. The shading model is a
relaxation — it enforces the chocolate-rectangle lemma and the banana size cap
exactly and adds the banana-non-rectangle rule only as cuts, each of which
forbids exactly one genuinely illegal pattern. When such a model returns
INFEASIBLE, no legal shading exists. Column offset 2 died after 5 to 37 cuts
depending on the row. By transposition the same holds for 7x1 at rows 2-8.

So a 1x7 must be flush against the left or right edge of the grid (and a 7x1
against the top or bottom). Same flavour as the 1x8 result, one notch weaker.

### Why 7 came for free once the shape appeared

The arithmetic side of a 1x7 is fully enumerated and it is unusually kind. A
1x7 chocolate strip lies in one sudoku row, so its seven digits are distinct,
adjacent pairs differ by >= 5, and 5 cannot appear. Exhaustive enumeration
gives **8 sequences up to reversal, and all 8 contain a 7**:

```
1 7 2 8 3 9 4      3 8 2 7 1 9 4      6 1 7 2 8 3 9
2 7 1 8 3 9 4      4 9 1 7 2 8 3      6 1 7 2 9 3 8
3 8 1 7 2 9 4      4 9 2 7 1 8 3
```

**Therefore circle 7 is placeable if and only if a 1x7 (or 7x1) chocolate group
exists in a full grid.** No separate "does the 7 land inside" step is needed —
it always does. So the circle question and the shape question are the same
question, and the witness below settles both.

It took real search: 535 legal shadings with a forced 1x7 were digit-UNSAT
across nine positions before position (row 5, cols 3-9) produced a digit-feasible
one on its fourth shading. That one immediately carried the circled 7, as the
enumeration guarantees. The witness strip reads `4 9 3 8 1 7 2`, which is the
reversal of `2 7 1 8 3 9 4` from the list above.

## Sanity checks run against a false negative

A null on circle 4 or 6 would have been a harness bug, not a finding. Neither
came out null, but the checks were run and are recorded here so a later reader
knows the pipeline was not simply lucky.

1. **Stage 2 on the existing `FEASIBILITY.md` witness, circle demand removed,
   returns SAT**, and the independent checker passes that grid with the group
   sizes the doc reports. The harness reproduces a known-good grid.
2. **The circle demand is an OR over the target rectangle's cells** — "some
   cell of this group holds the digit `k`" — not an equality on a fixed cell,
   and not quantified over all groups.
3. **Box-straddling rectangles were generated deliberately**, not left to
   chance. `RECTANGLE-CATALOGUE.md` shows why this matters: a box-aligned 2x2
   admits no 4 at all, so a cache of only box-aligned 2x2s would have produced
   a confident false negative on circle 4. The witness found has its 2x2 at
   offset (2,2).
4. **The corner rule for 6 was checked against the catalogue**, which shows the
   digit 6 in the support of a 2x3's corner cells only. The witness has its 6
   at a corner.

Two further crosschecks, both passed: every witness re-verified from scratch,
and the catalogue's independently computed 1x8 and 1x7 filling counts match the
counts derived here by a separate enumeration.

## Hand lemmas, all confirmed by the witnesses

German's partner sets are tiny: 6 pairs only with 1, 4 only with 9, 3 with
{8,9}, 7 with {1,2}, 2 with {7,8,9}, 9 with {1,2,3,4}, 1 with {6,7,8,9}, and 5
with nothing. Three predictions, all borne out:

- **A circled 4 in a 2x2 forces its two neighbours to 9, so the 2x2 must
  straddle a box boundary.** The witness below has its 2x2 at r3c3 — rows 3-4,
  spanning the horizontal band boundary — with 9 at r3c4 and 9 at r4c3.
- **A circled 6 sits at a corner of its 2x3, with both neighbours 1.** The
  witness below has 6 at r4c9, the corner of the 2x3 at r3c7, with 1 at r3c9
  and 1 at r4c8.
- **A circled 9 forces a 3x3 straddling the box band** — unchanged from
  `FEASIBILITY.md`, and now confirmed mechanically: the 3x3 catalogue at box
  offset (0,0) is empty against 1520 region-agnostic fillings.

All three are instances of one degree lemma, stated and computed in
`RECTANGLE-CATALOGUE.md`: inside a rectangle, a cell's two horizontal
neighbours share its grid row and its two vertical neighbours share its grid
column, so each pair must be *distinct* partners. A digit with exactly one
partner — 4 and 6 — can therefore never have two neighbours in one line, which
confines it to a corner and forces the equal-digit pair into different boxes.

## Verified witnesses

Chocolate in brackets, banana bare.

### Circles 8 and 1 — 2x4 at r6c6, digit 8 at r6c8; singleton 1 at r1c3

```
 4   3  [1]  9   7   6  [8]  2   5
 2  [5]  7  [3]  8  [1]  6  [9]  4
[9]  6   8   2  [4]  5   7  [1]  3
 6  [8] [2]  4   3  [7] [1]  5  [9]
 3  [1] [9]  5  [2]  8   4   6   7
 5   7   4  [1]  6  [9] [3] [8] [2]
[1]  2  [6]  7   5  [4] [9] [3] [8]
 7  [9]  5  [8] [1]  3   2   4   6
 8   4   3   6   9  [2]  5  [7] [1]
```

Chocolate group sizes: fourteen 1s, four 2s, one 4, one 8. Banana group sizes:
3, 3, 3, 4, 4, 5, 5, 6, 7, 7. The 2x4 is rows 6-7, cols 6-9, reading
`9 3 8 2 / 4 9 3 8`; the circled 8 can sit at r6c8 or r7c9. Four singleton
chocolate cells hold a 1 (r1c3, r2c6, r6c4, r7c1), any of which carries a
circled 1.

### Circle 7 — 1x7 at r5c3, digit 7 at r5c8

```
[1]  6  [9]  4   7   5  [8]  2   3
 3   7   5  [2]  8   9   6  [1]  4
 8   4  [2]  3  [6] [1] [7]  9  [5]
[9] [3]  8   7   1   2   4   5   6
 6   5  [4] [9] [3] [8] [1] [7] [2]
 7  [2]  1   5   4   6   3   8   9
[5]  8  [6] [1] [9] [4]  2  [3]  7
 2   1   7   6   5   3  [9]  4  [8]
 4  [9] [3] [8] [2] [7]  5   6  [1]
```

Chocolate group sizes: eleven 1s, two 2s, one 3, one 4, one 5, one 7. Banana
group sizes: 3, 3, 3, 6, 6, 8, 9, 9. The 1x7 is row 5, cols 3-9, reading
`4 9 3 8 1 7 2` — flush against the right edge, as the offset proof requires.

### Circle 4 — 2x2 at r3c3, digit 4 at r4c4

```
 5  [3] [8]  1  [2]  6  [9]  4  [7]
 4   9   2   8  [7]  5  [1]  3   6
[6]  7  [1] [9]  4   3   2  [8]  5
 3   6  [9] [4]  1  [2] [7]  5  [8]
[1] [8]  5   3  [9]  7   4   6   2
[7] [2]  4  [5]  6  [8]  3  [9] [1]
 2   4  [6]  7   5   9  [8]  1   3
[9]  5   3  [2]  8  [1]  6   7  [4]
 8   1   7   6  [3]  4   5   2  [9]
```

Chocolate group sizes: thirteen 1s, six 2s, two 4s. Banana group sizes: 3, 4,
5, 6, 6, 7, 8, 9. The 2x2 is rows 3-4, cols 3-4, reading `1 9 / 9 4`.

### Circle 6 — 2x3 at r3c7, digit 6 at r4c9

```
[2] [9] [1]  6   7  [8]  5   4  [3]
 5   3   4  [9]  2  [1]  6   7   8
 8   6   7  [3]  5   4  [2] [9] [1]
[7]  2  [5]  4  [8]  3  [9] [1] [6]
 1  [8]  3   2   6  [9]  4   5   7
 6   4  [9]  5  [1]  7  [3]  8  [2]
[4]  7   2  [1]  3   5  [8]  6  [9]
 3   5   8  [7]  9   6   1  [2]  4
[9] [1] [6]  8   4   2  [7]  3   5
```

Chocolate group sizes: eleven 1s, five 2s, two 3s, one 6. Banana group sizes:
3, 5, 5, 5, 6, 7, 8, 9. The 2x3 is rows 3-4, cols 7-9, reading `2 9 1 / 9 1 6`.

Circles 2 and 3 come from the `FEASIBILITY.md` witness, re-verified here: its
2x1 at r5c1 holds a 2 at r5c1, and its 3x1 at r5c3 holds a 3 at r6c3.

## Method

Two stages, as `FEASIBILITY.md` prescribes and for the reason it gives — a
joint shading+digit search returns UNKNOWN on questions a verified witness
already answers, so its UNKNOWNs are worthless.

**Stage 1, shadings only.** Booleans `b[r][c]`, 1 = chocolate.

- Chocolate rectangle rule, exactly: no 2x2 window holds exactly three
  chocolate cells.
- Banana size cap, structurally: a label 0..40 per cell; adjacent banana cells
  share a label; at most 9 banana cells carry any one label. Distinct
  components can always take distinct labels, so this is equivalent to the cap
  rather than stricter. 41 labels always suffice — a 9x9 grid has at most 41
  components of one colour.
- Banana non-rectangle rule, lazily: solve, find a banana component that is a
  rectangle, cut exactly that pattern (its cells banana, its whole border
  chocolate), repeat.
- To target a shape, force one rectangle: its cells chocolate, its whole
  orthogonal border banana. That makes it an exact maximal component.
- Vary `random_seed` per solve with `randomize_search` on, and no-good the
  whole 81-cell shading after each accepted one, or the enumerator returns
  near-identical grids.

**Stage 2, digits on a fixed shading.** Sudoku AllDifferents; a reified
`|d1-d2| >= 5` on every chocolate-chocolate adjacency; per banana component
(flood-filled from the fixed shading, so no labelling needed) AllDifferent and
`max - min == size - 1`; and for a circle question, an OR over the target
rectangle's cells that the digit equals the area. Runs in well under a second,
SAT or UNSAT.

**Stage 3, verify.** Re-check every hit with a checker written from the rules,
not from the solver's encoding. `FEASIBILITY.md` records two spurious SATs from
a loose renban encoding; nothing counts until re-verified.

### What the rates look like

Worth knowing before re-running any of this: **the digit stage is the filter,
by a wide margin.**

- Legal shadings come at roughly 1.5 per second.
- Of free legal shadings, about **3%** admit any digit fill at all (9 of 267).
- Of legal shadings carrying a forced 2x2, about **1%** (1 of 93); with a
  forced 1x7, under **0.2%** (1 of 536).
- But a digit-feasible shading is generous: the *first* digit-feasible shading
  with a forced 2x2 immediately admitted the circled 4, and of the cached
  digit-feasible shadings, one of six with a size-4 group and the single one
  with a size-6 group both admitted their circle on the first try.

So the productive loop is **generate free shadings, keep the digit-feasible
ones, then query that cache for every circle value at once** — the cache is
reusable across all nine questions. Forcing a rectangle position helps only for
shapes too rare to appear by chance (1x7, 2x4, 3x3), and it costs an order of
magnitude in digit-feasibility.

Scripts are throwaway and live in the session scratchpad; the description above
is the artifact.

## How many circles at once — the generator objective

The per-value questions above are "can this value ever appear". The generator
wants a different number: how many circles one grid can carry at once. That is
one model, not nine — fix a shading, solve digits exactly, and **maximize the
count of chocolate rectangles whose area equals a digit they contain**. Run to
optimality on 18 digit-feasible shadings (the cached ones plus the four witness
shadings above):

| | |
|---|---|
| chocolate groups per shading | 17 to 23 |
| circles placeable at once, optimum | **5 to 11** |
| best seen | 11 of 23 |

Every one of those solved to proven optimality in seconds, so these are exact
per-shading maxima, not lower bounds.

**The catch is what the optimum is made of.** The best grids are a wall of
small values:

```
11 circles: 1 1 1 1 1 1 2 2 2 2 2
11 circles: 1 1 1 1 1 2 2 2 2 2 3
 9 circles: 1 1 1 1 1 1 2 2 2
 6 circles: 1 1 2 3 4 7      <- the varied one, on the 1x7 witness shading
```

Maximizing *count* actively costs you the interesting values. The 2x4 witness
shading tops out at 5 circles when it keeps its 8, and the 2x2 witness shading
reaches 9 only by giving up its 4 — on that shading the optimum contains no 4
at all, even though a 4 is placeable there. Large circles and many circles pull
against each other, because a large circle needs a large rectangle and large
rectangles eat the cells that would have been singletons.

So the generator objective is **not** "maximize circles". It should weight by
value, or fix a target multiset of circle values and satisfy it. That is the
map's stated tension — bigger chocolate rectangles make better circles, renban
fights them — showing up as a measured trade-off rather than a hunch.

## What this means for the clue ladder

Circles are not the thin clue source that was feared. **Every value but 5 is
live**, including the whole small end (1, 2, 3, 4) which is easy to place —
every verified grid here carries ten or more singleton chocolate cells and
several dominoes. The large end is strong too and each large value pins a
shape hard: a circled 9 forces a 3x3 straddling the box band, an 8 forces a 2x4
(the only shape of that area), a 7 forces a 1x7 or 7x1 flush against a grid
edge.

The clue ladder does not need kropki brought forward on account of circle
scarcity — a single grid carries 5 to 11 circles at optimum, which is a real
clue budget. But temper it with the trade-off above: that budget is mostly 1s
and 2s, and a 1 or a 2 says very little, since singleton and domino chocolate
groups are everywhere. If the ladder needs circles that *cut*, it needs the
large values, and those come a few per grid at best. The real constraint is the
shading, not the circle rule.

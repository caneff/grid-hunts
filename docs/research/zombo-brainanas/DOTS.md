# Black boundary dots

Decision 2026-09-07: the second clue type is a **black boundary dot** — a black
dot joins an infected cell and an uninfected orthogonal neighbour whose digits
are in a 1:2 ratio. An uninfected neighbour is never smaller than the infected
digit (the infection would have taken it), so the uninfected cell is always the
double. Replaces Cocci Dots (consecutive uninfected digits).

## Why

- Shading is derived from the digits, so every clue is a digit clue. Circles
  say "this group has size N"; with five brainanas most groups are large and
  the box-9 sweep for one circle (`tools/pairone5.py`, 16 cases, 400 s each,
  4 workers) was cut after 11 cases: 7 INFEASIBLE, 4 UNKNOWN, no grid
  (`found/PROGRESS_pairone5.md`; the two shard logs interleave, so per-case
  attribution is not recorded). Chris scrapped the 5-brainana line on
  2026-09-07 ("scrap the idea of the 5 brainana for now"); no more hunting.
- Cocci Dots mark two uninfected cells, the default state in a brainana-heavy
  grid, and add kropki information only. A boundary dot marks a rectangle
  edge, which is where the propagation research puts the deductions.

## How many exist naturally

Count of infected–uninfected neighbour pairs in 1:2 ratio, over the 410 grids
in `found/` (no dot objective, just what the shading gives):

| dots | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|------|---|---|---|---|---|---|---|---|---|----|----|
| grids | 1 | 10 | 21 | 25 | 37 | 34 | 28 | 17 | 14 | 7 | 2 |

The 5-brainana witness `found/groups_5.json` has 58 boundary edges, 6 black
dots (r2c2/r2c3, r2c7/r2c6, r3c2/r3c1, r5c5/r5c4, r6c9/r5c9, r7c6/r7c7) and 6
white-style (+1) pairs.

## Open

- Uniqueness from circles plus dots with **no givens** (Chris: circles stay,
  they are what makes it feel like Choco Banana): not measured yet. The model
  now takes `dots=` (`zombo_brainanas_cpsat.py`: a dotted edge is opposite
  shading with the uninfected digit double the infected one; every undotted
  edge forbids that pair), so `unique({}, circles, [], known=sol, dots=D)` is
  the test. Candidate grids by circles/dots: `probe_circ13` (13/5),
  `dist25_400` (12/8), `probe_bal37` and `box9_704` (11/9).

## r9c7 + r9c9 circles, four pockets (2026-09-07)

With circles on r9c7 (uninfected) and r9c9 (infected), at least four
uninfected groups and the circles + chocolate objective, the shading space is
tiny: `tools/pair99g4.py` and `tools/pair99g4near.py` found four shadings in
total (`found/pair99g4_UI_w3_s0`, `found/pair99g4near_UI_w3_s0..s2`) and then
CP-SAT proved INFEASIBLE for any further shading at distance ≥ 1, in about
40 s each. The IU kind (r9c7 infected) has two shadings at distance ≥ 12
(`found/pair99g4_IU_*`), unexplored closer in.

Digit fills of those four UI shadings are finite too (`tools/pair99fills.py`,
all exhausted): 6, 12, 6 and 12 fills, 36 grids in `found/pair99fills_*`.
Most dot options: `pair99fills_n1_f04` (8 black + 18 white, 7 circles, 34
chocolate); best with 9 circles: `pair99digits_UI_d1` (= fill s0_f02, 7 black + 17 white). The s0 fills duplicate the `pair99digits_*` grids, so `found/` holds 27 of the 36.

## Which third circle pins the r9c7 / r9c9 shading (2026-09-07)

`tools/pinx.py`: circles open on r9c7, r9c9 and one cell X outside box 9, no
other constraint; a kind INFEASIBLE for X means a circle on X pins the other
kind. Logs in `probes/pinx_IU.log`, `probes/pinx_UI.log`, every cell decided
(no timeouts). U = pins UI (r9c7 uninfected, r9c9 infected), I = pins IU,
X = neither kind survives, . = no pin.

```
      c1 c2 c3 c4 c5 c6 c7 c8 c9
r1     .  .  .  .  .  U  U  .  .
r2     .  .  .  .  .  U  U  .  .
r3     .  .  .  .  .  U  U  .  .
r4     .  .  .  .  U  U  U  U  .
r5     .  .  .  U  U  U  .  U  U
r6     .  .  .  I  .  .  .  .  U
r7     .  .  X  U  U  U  #  #  #
r8     .  .  I  U  U  U  #  #  #
r9     .  .  U  U  X  U  #  #  #
```

29 cells pin UI, two pin IU (r6c4, r8c3), two kill both (r7c3, r9c5).

## Circles r6c8 + r9c7 + r9c9 with a white dot near r7c5 (2026-09-07)

Ask: a white dot between r7c5 and r7c6. Result: infeasible for both kinds, with
or without the 4-group floor. Splitting it: r7c6 uninfected alone is infeasible
for both kinds once r6c8 carries a circle (with only the box-9 pair, UI allows
it), and r7c5 uninfected alone is feasible only for IU. So r6c6–r7c6 is dead
too. Edge sweep of rows 6–9, cols 4–6 (`probes/tri68w/sweep.txt`, 26 of 34
cases decided before the hunt was stopped): IU allows r6c4–r7c4, r7c4–r7c5,
r7c4–r8c4, r8c4–r8c5, r8c4–r9c4, r8c5–r9c5; UI allows only r9c5–r9c6.
Scripts: `tools/tri68w.py`, `tools/tri68sweep.py`.

## Circles r9c7 + r8c9 + r6c8 (2026-09-07)

Kind = shading of (r9c7, r8c9). II and UU infeasible in seconds; IU and UI both
feasible, 10 circles each, chocolate 27–32 (`found/tri3_*`). With a white dot
on some edge of r6c6 (`tools/tri3w66.py`): **UI is infeasible** (17 s proof),
IU gives four grids (`found/tri3w66_IU_*`), the dot landing on r5c6–r6c6 or
r6c6–r6c7. So a white dot at r6c6 pins IU here (r9c7 infected, r8c9
uninfected), not UI.

With the white dot forced on r6c5–r7c5 instead (`tools/tri3wdot.py`): IU is
infeasible, UI gives three grids (`found/tri3wdot_r6c5r7c5_UI_*`, 10/9/9
circles, 32/29/29 chocolate, two pockets each). So r6c6 pins IU and r6c5–r7c5
pins UI for this circle triple.

More r6c5–r7c5 UI grids: seeds 3–10 all land (7–9 circles, 24–31 chocolate),
every one with exactly two pockets [n, 8]. Four pockets is **infeasible** with
this dot (proof in seconds); three pockets gives one grid (9 circles, 24
chocolate, pockets 37/12/8) and the second seed at distance ≥ 12 is infeasible.

White dot r6c4–r6c5, same triple: IU infeasible (with or without the 4-pocket
floor), UI feasible with four grids (`found/tri3wdot_r6c4r6c5_UI_*`, 8–9
circles, 28–32 chocolate); four pockets infeasible, one grid has three
(25/16/8). r6c5–r6c6 was started by mistake and stopped: IU infeasible, UI
undecided.

## Killing r9c7 = 9 with a white dot (circles r9c7 + r8c9 + r6c8)

Goal (Chris): r9c7 = 9 must be impossible. Without a dot it is possible: the
infected 3×3 is r7–9 c6–8 and r8c9 sits in a 7-cell banana r6c6–r6c9 +
r7c9–r9c9 (`probes/kill9/none_grid.txt`). A white dot that forces a cell of
that ring's neighbourhood uninfected merges the banana past 9. Sweep of 69
edges with r9c7 given 9, shading free (`tools/kill9.py`,
`probes/kill9/results.txt`, no timeouts):

Dots that **kill the 9** (23): r4c6–r5c6, r4c7–r5c7, r4c8–r5c8, r4c9–r5c9,
r5c4–r6c4, r5c5–r5c6, r5c5–r6c5, r5c7–r5c8, r5c7–r6c7, r5c8–r5c9, r5c8–r6c8,
r5c9–r6c9, r6c4–r6c5, r6c5–r6c6, r6c5–r7c5, r6c6–r7c6, r6c8–r6c9, r7c5–r7c6,
r7c5–r8c5, r7c6–r8c6, r8c5–r8c6, r8c6–r9c6, r9c5–r9c6. Every edge touching
r5c6–r5c9, r6c5, r6c6, r6c9, r7c5, r7c6, r8c5, r8c6 or r9c6 kills it; every
edge in rows 1–3 of cols 7–9, in cols 3–4, or on r4 horizontally leaves it.

Cross-check with the UI hunts: r6c4–r6c5 and r6c5–r7c5 both kill the 9 and
both give UI grids (2–3 pockets). The only dots that allowed four pockets
(r4c3–r4c4, r6c3–r6c4) do not kill the 9.

### Four pockets with a 9-killing dot

`tools/pocket4.py` over the 23 killing edges, shading free
(`probes/pocket4/results.txt`): only **r4c8–r5c8, r5c7–r5c8 and r8c6–r9c6**
allow four pockets, and all three land on the same UI grid,
`found/tri3wdot_r4c3r4c4_UI_w3_s0_g4` (6 circles, 28 chocolate, pockets
22/13/10/8), which carries those three dots naturally. A second 4-pocket
shading at distance ≥ 12 is infeasible for both r5c7–r5c8 and r8c6–r9c6. The
other 20 killers are NO4 by proof.

Ops note: two WSL crashes today came from running 7 solvers whose per-process
caps summed past the VM's memory. Keep it to two solvers at a time.

## UI r9c7 + r9c9, 4 pockets, circles in boxes 6 and 8, none in r6 of box 6

Filter over the exhaustive 36 fills of the 4 UI four-pocket shadings: **none**.
Every fill has exactly one box-6 circle and it is in row 6: rows 4–5 of box 6
are part of a rectangle wider than the box (no digit can circle it), and
r6c7–r6c9 belong to r9c7's 8-pocket, whose second 8 lands there. Box 8 has 1–2
circles in every fill. Library caveat as usual (pockets > 9 cells only next to
box 9).

## UI r9c7 + r9c9, two circles in box 8, a black dot inside box 1

Five earlier UI grids already qualify, all with two pockets (pair99_r9c7_r9c9_UI,
pair99var_UI_w6_s1/s3/s5, pairb24_r9c7_r9c9_UI). `tools/pair99b8d1.py` enforces
both in the model: four pockets is **infeasible** (proof); without the floor,
four new grids (`found/pair99b8d1_UI_*`), best UI_w3_s0 with 10 circles, 32
chocolate and three pockets 34/8/7.
Three-pocket floor: five shadings at distance ≥ 12 (`found/pair99b8d1_UI_*_g3`,
7–10 circles, 25–32 chocolate), the sixth infeasible, so that is the whole
three-pocket space at that spacing.

## UI r9c7 + r9c9, black dot in box 1 or 2, circle in box 6 off row 6 and in box 8 off column 6

`tools/pair99b68.py` (circle floors via `m.circle_at`, sound as lower bounds).
Four pockets infeasible for both UI and IU (proofs). Three pockets, UI: six
seeds all land (`found/pair99b68_UI_*_g3`, 7–10 circles, 25–32 chocolate); the
box-6 circle sits at r4c8, r4c9 or r5c8, the box-8 one at r7c5 or r9c4.

## Opener: r9c7 + r9c9 with a kropki on the would-be green ring

Chris's opener: if r9c7 were 9, r7–9 c6–8 is chocolate and r6c6–r6c9 +
r7c9–r9c9 are a 7-cell green block; any kropki domino adjacent to that block
grows it past what r9c9 can circle, so the 9 dies. `tools/pair99ring.py`
requires a white or black dot on a domino with a cell in r5c6–r5c9 or r6c5.
Three pockets, UI: six seeds all land (`found/pair99ring_UI_*_g3`, 8–11
circles, 25–32 chocolate). Four pockets: exactly one shading at distance ≥ 12
(`pair99ring_UI_w3_s0_g4`, 9 circles, 35 chocolate, pockets 24/9/8/5, opener
dot white r4c6–r5c6); the second seed is infeasible.
Aliases (sync dedupes by grid): the 4-pocket hit is `found/pair99g4_UI_w3_s0`
and the 3-pocket s0 is `found/pair99var_UI_w3_s0`; both already carried the
r4c6–r5c6 white dot.
Correction: the g4 run's distance-12 spacing hid the other three four-pocket
shadings. Over the exhaustive 36 fills, 28 carry an opener kropki: the
pair99g4_UI_w3_s0 and n1 shadings in every fill (white r4c6–r5c6, often plus
black r5c8–r6c8), the n0 and n2 shadings in 8 of 12 fills each (black
r6c4–r6c5 and/or black r5c8–r6c8 only). No fill of n0/n2 has a white opener.

### Library caveat, corrected

The pocket library only models pockets that carry a circle; uncircled
uninfected groups are free-form (validated by lazy cuts), and a circle's digit
caps its pocket at 9 cells, which the library covers. So shading enumerations
and fill enumerations above are exact. The library only affects circle
maximization: a circle in an 8/9-cell pocket away from box 9 is not counted in
the objective, so an optimizing hunt may pick a slightly worse fill.

## Minimal unique clue set (no givens)

`tools/minuniq.py` on `pair99g4_UI_w3_s0`: 7 clues, irreducible (greedy, 23
proofs): circles r9c7, r9c9; white r4c6–r5c6 (opener), r1c8–r2c8; black
r1c7–r2c7, r5c2–r6c2, r8c2–r9c2. Dots are positive-only clues (no negative
constraint). Result in `unique/pair99g4_UI_w3_s0.json`.
Circles + white dots only (`NO_BLACK=1`, dots stripped first): 9 clues —
circles r9c7, r9c9, r3c1, r6c9, r7c4, r9c2; white r4c6–r5c6, r3c6–r4c6,
r2c8–r2c9. With all nine circles, four white dots suffice (those three plus
r9c5–r9c6). `unique/pair99g4_UI_w3_s0_nb.json`.

### r6c8 circled, circles + white dots only

Eight of the 12 fills have r6c8 circleable (it is the pocket's second 8).
`KEEP=r6c8 NO_BLACK=1`: two are unique — `pair99digits_UI_d1` with 8 clues
(circles r6c8, r9c7, r9c9, r6c2, r9c2; white r4c6–r5c6, r3c2–r3c3,
r3c5–r4c5) and `pair99digits_UI_d0` with 10 (circles r6c8, r9c7, r9c9, r3c1,
r6c2, r9c2; white r4c6–r5c6, r3c6–r4c6, r2c7–r2c8, r2c8–r2c9). The other six
(d2, d3, n1_f02–f04, pair99g4near_UI_w3_s1) are not unique even with every
circle and white dot, so they need black dots. Pictures in `unique/`.

## Moving the second circle: r9c7 + another box-9 circle, 4 pockets, r9c9 ≠ 9

`tools/x9hunt.py` (r9c7 uninfected, X infected, four pockets, r9c9 ≠ 9, three
seeds at distance ≥ 12): feasible for X = r7c7 (3 grids), r7c8 (3), r7c9 (2),
r8c9 (2), r9c9 (1, the known shading with r9c9 = 6); infeasible by proof for
r8c7, r8c8, r9c8. `tools/x9kill.py` then tests every white dot near box 9 on
each grid with r9c7 given 9: **every one of the 11 grids has at least one white
dot that kills the 9** (`probes/x9/killers.txt`, no timeouts). Grids in the
lineup under "r9c7 + other box-9 circle".

### Unique sets for the moved circle (circles + white dots only)

`minuniq.py` with `SECOND=<cell> OPENER=<edge> NO_BLACK=1`: x9_r7c8_w3_s0 → 7
clues (circles r9c7, r7c8, r3c6; white r4c8–r5c8 opener, r4c5–r5c5, r2c9–r3c9,
r5c1–r6c1); x9_r7c9_w6_s1 → 7 (circles r9c7, r7c9, r6c2, r9c2; white
r4c6–r5c6 opener, r5c5–r5c6, r3c2–r3c3); x9_r8c9_w3_s0 → 8 (circles r9c7,
r8c9, r3c9, r4c7, r7c6, r8c1; white r6c7–r7c7 opener, r3c4–r4c4).
x9_r7c7_w3_s0 is not unique even with every circle and white dot. Pictures in
`unique/`. r9c9 ≠ 9 was a hunt filter only and plays no part in uniqueness.
Solve note (Chris, d1 with the r3c1 circle added and extra white dots
r1c5–r2c5, r9c5–r9c6): after sudoku stalls, the finish is the circled 6 at
r9c9. Its rectangle already holds r8–9 c8–9, cannot extend to r9c7 (the 8 has
no bigger infected neighbour), so r7c8 and r7c9 are infected; r7c8's only
possible source is r7c9, so r7c9 > r7c8 gives 5/3, and the rest is sudoku.

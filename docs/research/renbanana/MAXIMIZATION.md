# Renbanana: maximizing features (#380)

Variety of candidates under an objective function, in the shape of the Zombo
generator. Uniqueness is out of scope here — every grid below is a legal
digit fill under *some* legal shading, nothing more.

Two hunts have run so far, both on `--objective circles`. Every grid was
re-checked from its JSON with `renbanana_cpsat.py verify`; all report LEGAL.

All eleven live on one interactive page, `lineup.html` — filter by run or
shape, sort by any column below (or by `circles in one house`), toggle
digits, circles, group outlines and the `fullest house` wash, and hover a cell
to light up its whole group. Rebuild it after a hunt with
`uv run python docs/research/renbanana/tools/build_lineup.py`; a new pool
needs one line in that script's `POOLS`.

## Leaderboard

`circles` scores a grid by summing the value of every circled digit, where a
circle may sit on a cell whose digit equals the size of its own chocolate
group. It is a digit-layer objective, so stage 1 stays pure feasibility and
stage 3 maximizes it on each fixed shading.

| run | file | seed | circles | choc cells | groups | largest | circleable |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| forced 2x4 | `candidates-2x4/cand_00.json` | 2 | **17** | 34 | 18 | 8 | 6 |
| free | `candidates/cand_03.json` | 7 | 16 | 29 | 20 | 3 | 10 |
| forced 2x4 | `candidates-2x4/cand_01.json` | 4 | 16 | 32 | 18 | 8 | 6 |
| free | `candidates/cand_02.json` | 5 | 15 | 31 | 19 | 4 | 7 |
| free | `candidates/cand_07.json` | 11 | 15 | 33 | 18 | 6 | 6 |
| free | `candidates/cand_04.json` | 8 | 14 | 30 | 20 | 4 | 7 |
| free | `candidates/cand_05.json` | 9 | 13 | 29 | 20 | 4 | 8 |
| free | `candidates/cand_01.json` | 4 | 12 | 30 | 20 | 4 | 7 |
| free | `candidates/cand_06.json` | 10 | 12 | 30 | 19 | 3 | 7 |
| forced 2x4 | `candidates-2x4/cand_02.json` | 10 | 11 | 34 | 16 | 8 | 3 |
| free | `candidates/cand_00.json` | 2 | 9 | 33 | 18 | 4 | 5 |

No upper bound has been computed for `circles`; the shading-layer bound
machinery in `bound` only covers `chocolate` and `variety`.

## Yield

| run | seeds | shadings | digit-feasible | rate | diversity rejected | wall clock |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| free | 12 | 299 | 8 | 2.7% | 0 | 769 s |
| forced 2x4 | 12 | 410 | 3 | 0.7% | 0 | 1321 s |

Both runs used `--limit 120 --workers 8 --min-distance 12`. The diversity
filter never rejected anything in either run: distinct shadings that survive
to a digit fill are already far apart, so the Hamming-or-shape-multiset test
is not currently binding.

The free run's 2.7% matches the ~3% recorded in `FEASIBILITY.md`. The cost of
a candidate is roughly 96 s free and 440 s with the 2x4 forced.

## What the free run showed: circle score and circle quality pull apart

Every free candidate is dominated by 1x1 and 1x2 chocolate groups — typically
nine to thirteen singletons plus five to seven dominoes. The largest rectangle
anywhere in the free pool is a single 2x3. No 3x3, no 2x4, no 1x7 appeared by
chance in 299 shadings.

So the top free score of 16 is 16 because the grid holds twenty tiny groups,
not because it holds good ones. A circled 1 or 2 tells a solver almost
nothing. The plain `circles` objective rewards group *count*, and group count
is maximized by shattering the chocolate into singletons. This is the same
tension `RECTANGLE-CATALOGUE.md` predicted: a puzzle wanting large circles
fights the shading.

## Forcing a shape is the fix, and it is cheap enough

`--require-shape 2x4` makes stage 1 place at least one maximal 2x4 chocolate
component, either orientation. It is a hard constraint on the shading, not a
term in the objective, so it cannot be traded away.

The result answers the question directly: a 2x4 is placeable alongside a full
digit fill, and forcing it *raised* the ceiling rather than lowering it — 17
beats the free run's 16. Both top forced candidates carry a genuine 8-circle
on the 2x4, which is the kind of clue the free pool never produced.

The price is yield, not feasibility: 0.7% instead of 2.7%, about 4.5x the
search per candidate. Twelve seeds returned 3 of a target 8; the other nine
seeds each burned their full 120 s budget without a fill.

`candidates-2x4/cand_02.json` is worth a look despite its low score — it
carries a 1x5 alongside the 2x4, so two large groups do coexist. Its score is
low *because* those two groups eat sixteen cells that would otherwise be
scoring singletons.

## Most banana circles are forced, so they say nothing

A circle is legal on either colour — `renbanana_verify.check` tests a circled
digit against its own group's size whatever that group is shaded — and the
hunt's `circles` objective only ever scored chocolate groups. Recovering the
banana ones looked at first like finding a large pile of value: seven or eight
per grid against chocolate's three to ten.

Almost all of them are forced by the group's size alone.

A banana group of size k is a renban, so it holds the run [m, m+k-1]. A circle
needs a member equal to k, which happens exactly when m <= k. The run must fit
in 1..9, so m <= 10-k. The circle therefore fails only for m in [k+1, 10-k],
and that range is empty once k >= 5.

**Every banana group of five cells or more contains its own size, whatever its
digits.** Such a circle rules out no shading and no digit the solver did not
already have; it is a consequence of the group being big, not a clue about it.

The pool agrees exactly — 67 of 67 groups of size >= 5 carry a circle, against
11 of 15 below that:

| group size | groups | with a circle | forced by the lemma |
| ---: | ---: | ---: | :--- |
| 3 | 4 | 2 | no |
| 4 | 11 | 9 | no |
| 5 | 11 | 11 | yes |
| 6 | 12 | 12 | yes |
| 7 | 10 | 10 | yes |
| 8 | 13 | 13 | yes |
| 9 | 21 | 21 | yes |

So the banana side carries almost no usable circle value after all. Across all
eleven candidates only **11 informative banana circles** exist, about one per
grid, every one on a group of three or four cells. `lineup.html` draws those
solid and the forced ones dashed and hidden by default.

The general lesson for scoring: a circle is worth what it rules out, not what
its digit reads. A big chocolate circle is rare and forces a large rectangle;
a big banana circle is automatic.

## A circled 2x3 exists; a circled 2x2 is the hard one

Asking a rectangle to *exist* and asking it to *carry a circle* are different
requests, and only the second is interesting: the first three grids with two
2D chocolates each had six rectangles between them and not one circle on any.
`--require-shape` states the first in stage 1, `--circled` the second in
stage 3, and the two together are what a clued rectangle needs.

Run each circle alone before asking for both — the conjunction hides which
half is the blocker:

| demands | shadings | candidates |
| --- | ---: | ---: |
| a circled 2x3 | 226 | 3 |
| a circled 2x2 | 222 | 0 |
| both | 190 | 0 |

The three 2x3 grids verify LEGAL and hold a real 6, at box offsets (1,2),
(0,2) and (2,2). The 2x2 is what stalls.

**The degree lemma constrains both shapes, not just the 2x2.** A circled 2x2
needs a 4, whose only German partner is 9, and every cell of a 2x2 has two
chocolate neighbours — so both of the 4's neighbours are 9. They sit at
(r, c+1) and (r+1, c), which sudoku permits only across a box line.

The 2x3 is in exactly the same position. Its circle needs a 6, whose only
partner is 1, and the circle can only sit on a **corner**: a middle cell has
three chocolate neighbours, all of which would have to be 1, and two of those
land in one row. A corner has two neighbours, same as any 2x2 cell. So a
circled 2x3 must straddle a box line too — the requirement is not weaker.

The only difference is arithmetic. Both shapes need one straddling pair, and
the pair can straddle by row or by column. A 2x2 spans two columns, so it has
one adjacent column pair to straddle with; a 2x3 spans three, so it has two.
Where a 2x2 at column offset 0 or 1 must fall back on a row straddle, a 2x3 at
column offset 1 or 2 always has a column pair that works. That is the whole
gap: 7 live offsets against 5, and 76 of 112 placements against 28 of 64.

| shape | live offsets | placements surviving |
| --- | ---: | ---: |
| 2x2 | 5 of 9 | 28 of 64 (44%) |
| 2x3 | 7 of 9 | 76 of 112 (68%) |

**That 1.5x does not explain the search result, and the search result is not
yet significant.** At the 2x3's observed rate of 3 in 226, the chance of
seeing zero in 222 draws is 0.051 — right at the edge. So "a circled 2x2 is
harder than a circled 2x3" is a factor-of-1.5 structural claim that the
sampling has not yet confirmed and could not confirm at this sample size. The
honest reading: the 2x3 is demonstrably attainable, the 2x2 is unproven either
way, and only a longer 2x2 run settles it.

## Chocolate maximization is a dead end

Recorded here so it is not re-run. Maximizing total chocolate pins every
shading at the shading-layer ceiling of 50 cells, and a ceiling shading need
not admit any digit fill. In the calibration run, **86 shadings in the 44-50
cell band were all proved INFEASIBLE at the digit layer** — proofs, not
timeouts. The 50-cell bound is therefore unattainable, and the whole
high-chocolate band is dead once digits are required. For reference, the
candidates that do exist sit at 29-34 chocolate cells.

The same trap applies to any shading-layer objective: `chocolate` and
`variety` are maximized in stage 1, which knows nothing about digits, so the
optimum it finds is usually unfillable. `--caps` exists to walk the objective
back down to where grids live.

## How many circles can one house carry: six, so far

A different question from the rest of this doc. Not "how much circle value does
a grid hold" but "how many circles can share one row, column or box" —
chocolate, banana and forced alike, since the question is about crowding and
not about what each circle says.

**Six, witnessed and verified: `candidates-house/cand_00.json`, row 5.** The
best any of the 96 candidate files already in `candidates*/` manages is four,
and 36 of them reach it.

| r5 cell | digit | colour | group | circled |
| --- | ---: | --- | ---: | :--- |
| c1 | 2 | banana | 7 | |
| c2 | 9 | chocolate | 2 | |
| c3 | 8 | banana | 8 | yes |
| c4 | 3 | chocolate | 3 | yes |
| c5 | 5 | banana | 5 | yes |
| c6 | 1 | chocolate | 1 | yes |
| c7 | 7 | banana | 9 | |
| c8 | 4 | chocolate | 4 | yes |
| c9 | 6 | banana | 6 | yes |

The circles alternate colour along the row, and they have to. Two touching
cells of one colour are one group and so one size, while a house's digits are
distinct — so no two adjacent cells of a house are ever both circled unless
they differ in colour. Three more constraints fall out of the same reading:

- **A size-1 or size-2 circle is chocolate.** A one-cell banana group is a 1x1
  and a two-cell one a 1x2; rule 4 forbids both.
- **A size-5 circle is banana.** Any cell of a five-cell chocolate group has a
  chocolate neighbour, and 5 has no partner at a difference of 5 or more.
- **Sizes 6 and up are cheap on banana and dear on chocolate**, by the forced
  circle lemma above: a banana group of five cells or more always contains its
  own size, so the circle costs nothing but the group.

## The tool: `max_house_circles.py`

`tools/max_house_circles.py` asks one house for one level and answers
SAT-with-a-witness or IMPOSSIBLE. It splits the way the rest of the repo does,
and the split is right here because **group size is a pure shading fact** —
which cells are circle*able* is settled before a digit is placed.

- **Stage A, shading only.** Exact for rule 3, and — unlike `Shadings` —
  exact for rule 4 as well: one clause per rectangle placement forbidding
  "inside all banana, whole border chocolate", so no cuts. It measures each
  house cell's group size, takes chocolate sizes straight from the placement's
  area and banana sizes from a closed, rank-walked membership set, and counts a
  cell circleable only when its size is 1..9, the house's circled sizes are
  distinct, and the #377 catalogue allows a circle on that cell of that
  rectangle at that box offset. Every clause is a necessary condition, so
  **stage A INFEASIBLE at a level is a proof** that the level is unreachable.
- **Stage B, digits on the fixed shading.** Sudoku, whisper, renban, catalogue
  domains, and at least `level` cells of the house holding their own group's
  size. Stage A names a circle set; stage B is free to pick another on the same
  shading, which is what makes a good shading worth keeping.

A shading stage B refuses is forbidden and the hunt draws another.
`tools/test_max_house_circles.py` pins verified pool grids into both stages: the
sizes stage A measures must equal `renbanana_verify`'s, an illegal shading must
be refused, and stage B must reproduce a circle set the checker already sees.

## Where the joint model went wrong, twice

Recorded so it is not rebuilt. The obvious model — digits and shading in one
CP-SAT solve, group sizes from a labelling — is **too heavy to find even a
first solution in 180 s**, mostly from the per-label, per-value booleans that
renban distinctness needs. Splitting the layers is not a nicety here.

Worse, a labelling gets group size wrong in two ways a *maximizing* solver will
find and exploit:

1. **Label-uniform is not enough.** If two disjoint components may carry one
   label, the solver merges them to inflate a size until it matches a digit,
   and reports a circle that is not there.
2. **A label class must be connected, and "descend to the smallest index" does
   not do it.** A connected component need not have a monotonically decreasing
   index path to its own minimum — the cells (r1c9, r2c9, r2c8) are a
   component whose r2c8 has no smaller-index neighbour inside it. The fix is a
   free integer rank per cell and a walk down it to a root, which is where the
   label's name comes from.

## Two loose ends

- **Seven is unresolved.** Eighty stage-A shadings at level 7 in row 5 were all
  refused by digits, and stage A itself has not been run to INFEASIBLE at 7, 8
  or 9. So six is a floor, not a ceiling, and nothing here says where the
  ceiling is. Only rows have been hunted; columns are their transpose, boxes
  are untouched. **Boxes are the interesting case** (owner's call) and are
  where the next run goes. A row spends its adjacency in one line, so its
  circles have to alternate colour along it; a box is 3x3, and two circled
  cells that meet only at a corner are in different groups without needing
  different colours. The alternation argument that shapes the row result does
  not bind there, so the box ceiling need not match the row's.
- **The witness scores 22 on `circles`**, against the leaderboard's best of 17
  — from eleven chocolate circle sites on eighteen small groups, not from good
  ones. It is another instance of the count-versus-quality tension above, found
  by a hunt that was not looking for it.

## Not yet run

- `3x3` forced. The catalogue says it is placeable; it has never appeared by
  chance in either pool.
- The `variety` and `circleable` objectives as their own hunts.
- An upper bound for `circles`.
- Stage A at level 7, 8 and 9, run to INFEASIBLE or a witness — the ceiling on
  circles in one house. **Boxes first**, then rows; three box positions cover
  all nine up to symmetry (corner, edge, centre) and five row indices cover the
  eighteen rows and columns. Nothing has been run: this is a record of a
  method and one witness, not of a search.
- A circle objective weighted by rarity rather than by digit value, so a
  forced banana circle scores nothing and a large chocolate one scores a lot.

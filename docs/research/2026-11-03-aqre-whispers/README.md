# Aqre shading with 5-whispers: feasibility, 2026-11-03

Chris's idea: a 9x9 sudoku with Aqre shading (shaded cells one orthogonally
connected group, no 4 in a line of one colour in a row or column) and 5-whispers
(orthogonally adjacent cells differ by at least 5). A circle's digit is the
number of shaded cells in its 3x3 box, the standard Aqre count. The scripts here
are scratch models, not finders: the repo has no Aqre model. Each solve ran on
one CP-SAT worker.

## Results

No solve timed out.

| Whispers on | Digits | Box counts | Result | Time |
|---|---|---|---|---|
| unshaded pairs | 1-9 | free | found, `grid-1.json` | 0.2 s |
| shaded pairs | 1-9 | free | found, `grid-2.json` | 72.1 s |
| shaded pairs | 0-8 | free (the control) | found; no rule broken | 20.4 s |
| none, no digits | none | all different, 0-8 | found (shape only) | 14.0 s |
| shaded pairs | 0-8 | all different, 0-8 | **proven infeasible**, first model | 187.8 s |
| shaded pairs | 0-8 | all different, 0-8 | **proven infeasible**, second model | 167.0 s |

So nine circles with nine different values, one per box, cannot exist under
those rules with 0-8 digits. The shading rules alone allow counts 0 to 8, so the
digits and shaded whispers are what rule it out.

## Why: no box holds 8 whisper cells

Chris's proof, 2026-11-03. Take 0-8 digits and a gap of 5. A count of 8 leaves
only the box's 4 unshaded, because 4 has no partner. The 3 pairs only with 8 and
the 5 only with 0, so each may have one shaded neighbour at most, and each is
shaded with at least 2 shaded neighbours in the box. The box's checkerboard
colours show why: its 4 corners and centre cannot all be shaded (four digits per
side), so the 4 is on that colour and every edge cell is shaded.

An enumeration of one box alone agrees: at a gap of 5, 0 of 9 layouts work with
8 whisper cells and 32 of 36 with 7. At a gap of 4, 9 of 9 work with 8 and none
with 9. That box check is necessary only; it does not show a whole grid exists.

Consequences at a gap of 5, the same in 1-9 digits by shifting:

- Whispers on shaded cells: a box count is at most 7, so at most 8 different
  values (0-7, needing 0-8 digits) and 7 with 1-9 digits.
- Whispers on unshaded cells: at most 7 unshaded per box, so a count is at
  least 2, and at most 8 different values (2-9).
- Nine different values therefore need a gap below 5.

The two infeasible models share no encoding: `aqre_disjoint_feasible.py` uses
integer digits, an orientation variable, flow connectivity and a redundant total
of 36; `aqre_disjoint_recheck.py` uses one-hot digits, whispers as clauses,
level-based connectivity and one-hot box counts. Both run on CP-SAT, so a CP-SAT
bug would reach both.

With unshaded whispers the first grid has only 5 adjacent unshaded pairs, so
that rule barely constrains it. That is one grid, not a bound.

## What the shaded-whisper rules force

By hand, and `grid-2.json` agrees:

- The shaded group alternates: one checkerboard colour of shaded cells is all
  low and the other all high.
- The middle digit (5 in 1-9, 4 in 0-8) is never shaded.
- A house holds at most 8 shaded cells.
- A digit on the wrong checkerboard colour for the orientation must be unshaded.
- Swapping `d` for its mirror digit flips the orientation only without circles:
  the swap changes a circled digit but not its box count.

## Four circles in a 2x2 where four boxes meet

Chris's ask, 2026-11-03: back to 1-9 digits with 5-whispers on shaded cells and
no "all different" rule; four circles fill a 2x2 across a box crossing, and every
box holds a valid circle because every box has a shaded cell. The four crossings
are one case under reflection.

Found, `grid-4.json`, in 8.6 s after a warm start from a solve of the four boxes
alone (`aqre_crossing_circles.py DIR`). The circles are r3c3=4, r3c4=6, r4c3=2 and
r4c4=4, and the separate reader found no rule broken. The first attempt, without
the warm start or the every-box rule, ended UNKNOWN at 300 s, which proves nothing.

Not tested: uniqueness.

## The negative rule: adjacent unshaded cells within 4

Chris's ask, 2026-11-03: unshaded cells "within 5 of each other", read as a
difference of at most 4, so a same-colour neighbour pair is tested both ways and a
mixed pair is free. Digits 1-9, every box with a shaded cell.

Found, `grid-5.json`, in 68.6 s on one worker (`aqre_negative_feasible.py DIR`);
the separate reader found no rule broken. Box counts run from 1 to 6 in that grid.
One box alone allows every shaded count from 0 to 7, as before: 32 of 36 layouts at
7 and none at 8 or 9, so the new rule adds no per-box limit on the count.

Not tested: how forcing it is, or uniqueness.

## The both-shaded rule: open

Chris's ask, 2026-11-03: "any two neighboring cells that are at least 5 apart must
both be shaded", kept beside 5-whispers on shaded cells. Together a neighbouring
pair is both shaded exactly when its digits are at least 5 apart, so a cell is
shaded exactly when it has a neighbour at least 5 away, and the digits decide the
shading.

Not settled. No run proved infeasible, and none found a grid. One worker each:

| Run | Result |
|---|---|
| No connectivity | found, 2.5 s |
| Flow connectivity, first model | UNKNOWN at 300 s |
| Flow connectivity, tighter model and warm start | UNKNOWN at 600 s |
| Lazy cuts | UNKNOWN at 900 s: 207 rounds, 1372 cuts, fewest shaded groups 4 |

One box alone still allows 0 to 7 shaded cells; only one layout drops, at 5 shaded
(125 of 126). The lazy-cut groups never settled: round 176 reached sizes 17, 7, 6,
6, 5 and round 201 went back to nine groups.

## Jigsaw regions with 8 circles in r1: found

Chris's ask, 2026-11-03: irregular 9-cell regions replacing the boxes, and 8 circles
in r1. Rules otherwise as before: digits 1-9, Aqre shading, 5-whispers on shaded
cells. `aqre_jigsaw_r1.py DIR` has the solver choose the regions too.

By hand, and a first solve agrees (infeasible in 0.5 s):

- The eight circled digits are 1-8, since no region can reach a count of 9 (its 5
  cannot be shaded). So r1's uncircled cell is the 9, and those eight regions have
  counts 1 to 8.
- A region touching r1 and r9 is a straight column, which holds at most 7 shaded
  cells. So all nine regions touching r1 fails: exactly eight do, and the 9 in r1
  shares a region with a circled cell.

The 3x3 limit of 7 does not carry over: irregular shapes are not excluded from a
count of 8 by the box proof. No grid has shown a count of 8 yet.

One worker per solve; the mirror image covers columns 6-9. Nothing was proved or
found.

| 9 in | No shaded connectivity (120 s cap) | Full (300 s cap) |
|---|---|---|
| r1c5 | found, 75.5 s | UNKNOWN |
| r1c4 | found, 99.8 s | UNKNOWN |
| r1c3 | found, 65.9 s | UNKNOWN |
| r1c2 | UNKNOWN | UNKNOWN |
| r1c1 | found, 108.4 s | UNKNOWN |

The one-worker table above ended with nothing settled. With 8 workers, on Chris's
go, the 9 in r1c5 found a grid: `grid-8-r1.json`, 438.5 s for the full solve after
22.3 s without connectivity (`aqre_jigsaw_r1_parallel.py DIR`). The separate reader
found no rule broken. r1 reads 2 5 7 6 9 1 8 4 3, with region counts of 1 to 8 on the
eight circled cells, 41 shaded cells in all, and the ninth region's circle at r9c6.

Weakness of this grid: 6 of its 9 regions are straight columns, which add no
digit constraint beyond the column itself. Whether a layout with fewer columns exists
is untested, and so is uniqueness.

`aqre_jigsaw_feasible.py DIR`, three random layouts, was stopped before reporting
when the ask moved to r1, so random jigsaw layouts are untested.

## How varied regions can be with eight of nine on r5

Chris's ask, 2026-11-03: geometry alone, no shading or whispers. `jigsaw_r5_diversity.py
DIR` ran a random walk of border swaps on one core for 20 s on each of 6 seeds, 57,732
layouts in all. This is a correlated sample, so it shows what exists and bounds
nothing. Sampling favours typical layouts.

| Measure | Share of samples |
|---|---|
| All 9 regions different shapes (free polyominoes) | 48,710 (84%) |
| No straight region | 51,929 (90%) |
| Widest region spans 3 to 9 columns | all seen |

`layout-r5.json` has 9 different shapes, no straight region and every region at least
4 columns wide, and it takes a plain sudoku fill. So r5 removes r1's push towards
columns. The next section tests it with the shading rules.

## Jigsaw regions with 8 circles in r5: open

Chris's ask, 2026-11-03: the r1 rules with the 8 circles in r5. `aqre_jigsaw_r5.py DIR`
has the solver choose the regions, with r5's uncircled cell the 9, since no count reaches
9. That 9 may sit in any region, including the ninth. 8 workers per solve; 20 minute cap on
each full solve; the mirror image covers columns 6-9.

Nothing was proved or found: all five full solves ended UNKNOWN, 100 minutes in all. That
does not show 8 circles in r5 cannot work, and it does not show r5 is harder than r1, where
one case found a grid in 438.5 s.

| 9 in | No shaded connectivity | Full (flow connectivity, 20 minute cap) |
|---|---|---|
| r5c5 | found, 6.9 s | UNKNOWN |
| r5c4 | found, 38.2 s | UNKNOWN |
| r5c3 | found, 8.3 s | UNKNOWN |
| r5c2 | found, 35.8 s | UNKNOWN |
| r5c1 | found, 24.0 s | UNKNOWN |

The grids without connectivity show the gap. They hold 37 to 40 shaded cells in 10 to 16
separate groups, and the largest group has 7 to 14 cells. They do carry varied regions: 3
of the 5 have no straight region, and the other 2 have one each. Those grids keep every
rule but connectivity, so they do reach the 1-8 counts on r5, including a count of 8. They
were not put through the separate reader.

### Two stages: why the fills fail

Chris's go, 2026-11-03: `aqre_jigsaw_r5_staged.py DIR` picks regions and connected shading
first with no digits, then fills digits. The first 10 logged layouts all failed the fill.
Each of them failed for two independent reasons, so fixing one alone would not help. These
are 10 layouts, so the shares below describe them and bound nothing.
`aqre_r5_fill_diagnose.py`, `aqre_r5_fill_diagnose2.py` and `aqre_r5_class_layer.py` hold
the checks; the same checks pass the known `grid-8-r1.json` layout.

**One house's whispers cannot take its digits.** In all 10 layouts, at least one house fails
alone, using only its own cells, shaded pairs and r5 digits. The whisper partners are
narrow: 4 pairs only with 9, 3 with 8 and 9, 6 only with 1, 7 with 1 and 2. Two digits that
share a house must differ, so a shaded 4 or 6 cannot have two shaded neighbours in one house.
By hand, on two layouts:

- Layout 8: r5c6 is a shaded 6 with shaded cells above and below it in its region, which
  would both have to be 1.
- Layout 1: the count-8 region holds all of 1-4 and 6-9 on shaded cells. Its r5 digit 8 has
  two shaded region neighbours, which must come from 1, 2 and 3. That puts the region's 4 on
  a cell with two shaded region neighbours.

**Shaded colours run out across houses.** All 10 layouts stay infeasible with no whispers
and no r5 digits, so the checkerboard signs fail by themselves. A layer with only low, 5 and
high classes (4, 1 and 4 per house) refuses 7 of the 10. The other 3 need exact digits.

The first stage only limited each house to 4 shaded cells per colour, which misses both
reasons. Chris chose to restart with the fix, 2026-11-03: the first stage now has exact digits
on shaded cells and r5, whispers and house differences included, and classes on every cell.
That moves it closer to the full model that timed out. `aqre_jigsaw_r5_staged.py` here is the
fixed version. It refuses all 15 layouts in `layouts-r5.jsonl`, the ones logged before the job
was stopped, and still accepts `grid-8-r1.json`'s layout.

That run ended with no grid: 9 layout solves, all UNKNOWN at 900 s, and no fills. The VM
appears to have been suspended for about 4 h 20 during try 9, which logged 15,980 s; uptime
gained 2 h 04 over 6 h 24 of clock. Its 2 hour plain solve of the 9 in r5c5 was stopped on
Chris's word after a few minutes, with no full-solve result.

### Fixed regions, digits first, and scoring layouts

`aqre_r5_fixed_regions.py DIR` samples layouts with no straight region and solves digits and
shading on each, one worker. Stopped on Chris's word at 148 cases in about 19 minutes. All 148
were proven infeasible for that layout and that place for the 9, 51 without connectivity and
97 with it. None timed out and none found a grid. These layouts are correlated samples. The
per-region filter refused none, so it is not doing useful work. The solves do finish, in
seconds, unlike every model that chooses regions.

`aqre_r5_digits_first.py DIR` solves digits and shading with no regions, then looks for
regions. A grid takes about 1 s. The 30 minute run ended with no grid: 1,519 digit grids
were all refused regions, and the last try hit the budget with no digit grid. On 10 of the
first 679, all distinct, connected regions exist with the straight rule off, while connected regions with no
straight region do not exist. A Latin square's columns already form a connected partition,
so those allowed partitions are probably just columns, though the check did not print them.
A square solved with no regions in mind rarely has a jigsaw partition, on this evidence.

Two scores for hill-climbing fixed layouts, tested on sampled failed layouts:

- Circles matched, with the circles soft (`aqre_r5_hillclimb.py`): 7 of 8 layouts got no
  score in 60 s, and the other scored 2 of 8. Dropped as too slow.
- Fewest shaded groups, with the circles hard (`aqre_r5_groups_score.py`): all 12 got a score
  within 30 s, from 6 to 15 groups where 1 is a valid grid, 5 of them proven best. So these
  layouts are not near misses. `aqre_r5_climb.py DIR` climbs on this score.

The climb was stopped on Chris's word, at about 1 h 50 of its 2 hour cap: no grid in 6 starts and
over 500 evaluations. Its best was 3 groups, on its second start; later starts began at 8 to 11
groups and never beat it. It never enforced the one-8, one-7 rules either.

### Placing the 8 region first

Chris, 2026-11-04: place the 8 region first, then the other regions so that none of them can
be circled 8.

`aqre_r5_eight_regions.py DIR` is exhaustive over one space: connected 9-cell sets holding
the circled cell in r5c1-5 (the mirror covers the rest), at most one other r5 cell, not
straight, judged on the region alone. By hand, a count of 8 leaves one unshaded cell, which
must be the region's 5, so the circled 8 is shaded and the shaded cells split 4 and 4 by colour.

| Circled cell | Sets, not straight | Can be the circled 8 |
|---|---|---|
| r5c1 | 8,274 | 1,657 |
| r5c2 | 20,905 | 4,436 |
| r5c3 | 30,599 | 6,932 |
| r5c4 | 36,134 | 8,060 |
| r5c5 | 37,796 | 8,450 |

That is 29,535 of 133,708 (22%), in 805 free shapes; 1,592 hold a second r5 cell, the 9. A solver
cross-check on 70 of the sets agreed with this enumeration every time. So being able to hold
the 8 is not rare, but most shapes cannot, which gives room for the other regions to rule
themselves out. Passing means only that the region alone can do it, not that a grid exists.

`aqre_r5_one_eight.py DIR` keeps sampled layouts where exactly one circled region can be the 8
and the ninth region cannot count 8, then solves each on fixed regions. Stopped on Chris's new
ask at 271 cases, all proven infeasible for their own layout: 146 without connectivity and 125
with it, no timeouts. 54% failing before connectivity against 34% for unfiltered layouts, on
correlated samples, so this filter did not help.

Chris's ruling, 2026-11-04: place a valid 8 in both shading and digits. Then place a valid 7
that cannot itself be a valid 8 but still has digits and shading that work with the 8, and so
on. A ninth region holding r5's uncircled cell has no circle there and may be able to count 8.

Chris's ruling, 2026-11-04: both the 8 and the 7 are strict, where possible. A region counting 6
or less cannot be a valid 7 or 8, judged alone, and the 7 region cannot be a valid 8. Only the 24%
of regions that top out at 6 qualify for those six lower regions.

`aqre_r5_build_up.py DIR` does this as a randomised depth-first search. Each placement samples a
region's cells and commits the shading and digits the solver picks to fit the whole board with
placed cells fixed. Its controls walk `grid-8-r1.json` through every check, region by region,
and refuse a swapped-digit 8 region.

The first version picked shading and digits at random, before the board check, and only required
"cannot be the 8". Stopped after about 10 minutes at 3 regions placed: of 1,781 board checks,
1,668 were infeasible, 111 passed and 1 timed out.

`aqre_r5_region_max.py DIR 0` takes the same 133,708 regions, judged alone, and finds the highest
count each can hold, with that count's digit on its circled cell:

| Highest count | Regions | Share |
|---|---|---|
| 8 | 29,535 | 22% |
| 7 | 72,193 | 54% |
| 6 | 31,980 | 24% |
| 5 or less | 0 | 0% |

The 8 row matches the separate catalogue exactly, and a solver check on a 3,000 region sample
agreed in all 213 comparisons. So a region alone can never rule out holding 6: "a 5 region that
cannot be a 6" does not exist on shape and its own digits. A strict ladder would have to rule
out high counts using neighbouring regions, which this count ignores.

Unlike the circled 8, the circled 7 is not forced to be shaded. `aqre_r5_seven_unshaded.py`
splits the same regions, judged alone, among the 72,193 that can be a valid 7 but not a valid 8:

| The circled 7 can be | Regions | Share |
|---|---|---|
| Either | 26,709 | 37% |
| Shaded only | 23,126 | 32% |
| Unshaded only | 22,358 | 31% |

All 29,535 regions that can be a valid 8 can also be a valid 7 either way. An unshaded circled 7
makes the two unshaded cells the 5 and the 7. A solver check agreed in all 600 comparisons on a
sample of 300 regions.

Chris's ruling, 2026-11-04: the 7 region's shape must force its circled 7, either way. So the
7 region comes from the 45,484 shaded-only or unshaded-only regions above, and
`aqre_r5_build_up.py` now requires that. The version before this ruling reached 3 regions placed in
61 s, then no further by 5 minutes, with 246 of its first 274 board checks infeasible.

### Exact cover over the catalogues

Chris's go, 2026-11-04, with reflection and rotation symmetry accounted for. The left-right
mirror, top-bottom flip and 180 rotation keep r5 and the checkerboard, so one 8 region stays from
each group: 830, 2,221, 3,470, 4,034 and 2,124 in r5c1-5. A layout whose 8 region maps to itself
still appears in more than one version. The 90 degree turns and diagonals map r5 to c5, the same
problem turned, so c5 needs no separate search.

`aqre_r5_cover.py catalogue DIR` sorts regions by the strict rules into 8, forced-7 and top-out-at-6
lists; r5c5's are 8,450, 12,821 and 8,919 before symmetry. Of its 8,919 low regions, 8,495 can
take all of counts 1-6 and 424 cannot take a count of 1.

`aqre_r5_cover.py estimate DIR 300` ran 101,958 random probes through the cover and none finished:
none got past 3 of 8 circled regions, and only 55 reached 3. That estimates nothing about how many
layouts exist, since a probe can miss rare ones. `aqre_r5_cover_exists.py` asks the solver directly.

It answered INFEASIBLE for all 9 places of the 9, in 4-71 s each, with no ninth-region cuts, on these
rules: an 8 region, a forced 7 region that cannot be 8, and six regions that top out at 6, each judged
alone with either colour high. Its control, with looser lists, was UNKNOWN at 892 s after finding 21
covers that failed the final checks, so it never confirmed a full layout. `aqre_r5_one_each.py check`
tested the catalogues separately: all 1,192 regions from 149 sampled layouts sit in exactly one list.
Of those layouts, 80 have no region topping out at 6 and 69 have one.

Those lists are too strict. Chris's point, 2026-11-04: the 8 is always shaded, so its colour is high
everywhere. A region on the opposite colour can never be the 8, and its 7 could only be unshaded. So
the infeasible result above covers only the colour-blind reading of the rule.

Chris's ruling, 2026-11-04: only one r5 region can be the 8, and only one can be the 7.
`aqre_r5_eight_sheet.py DIR` draws one shape per family (bounding box and longest straight run) of the
regions that can be the 8. 19 of the 805 free shapes have a hole, which no region could fill, so they
are left out, leaving 786 shapes and 28,847 placements in 37 families. The catalogue and the 22% above
include those 19. The cover never uses them, since its check on free cells refuses a walled-off cell.

Chris likes the sheet's "3x4 run 4" shape, rows `X.X / X.X / XXX / XX.`, for the 8 region, since 8 circles
in r5 force its other r5 cell to be the 9. `aqre_r5_shape_query.py DIR` confirms it: all 32 placements
that can be the circled 8, with the circle in r5c1-5, hold exactly two r5 cells, the 8 and the 9, two
columns apart. The 12 placements it printed each have just 1 filling, so the digits and the 5 are forced
within the region; the other 20 were not printed. The r5 cell between the 8 and the 9 is in the shape's
notch, so its own region can only leave r5 through the notch's open side.

Chris's go, 2026-11-04: fix the 8 region to this shape for now. `aqre_r5_chosen_eight.py DIR` runs the
colour-aware cover on it. The broad `aqre_r5_oriented.py` cover was stopped at about 11 minutes in its
first case, with no result.

Result on 12 workers, forced 7, 14 placements in 6 cases, 900 s cap per case: all 6 UNKNOWN (9 in r5c1 to
r5c6, 57,094 to 71,326 candidates), 0 layouts, so the fixed-region solve never ran and no grid came out.
Nothing is proven for this shape. Chris ruled out any 7, 2026-11-04: the script now runs forced 7 only, and
the old run was stopped about 3 s into its first any-7 case with no output from it.

Idea for a full enumeration of one placement, not built or measured: the 8 region holds two r5 cells, so by
counting cells the other seven r5 cells are in seven different regions and the ninth region is off r5. Each
of those seven is its r5 cell, a connected part going up and a connected part going down, joined only through
that cell. So the rows above and below r5 can be filled separately from the regions' up and down parts, then
joined where each region's two parts total 8 cells and form a listed region. Counting each half's fillings
first shows whether this is workable. The top-bottom flip keeps r5 and the checkerboard, so both halves can
share one list of parts and one filler. Their fillings differ only by the cells the 8 region takes and by
which side holds the ninth region.

`aqre_r5_split_count.py DIR` counted one placement in 16 s on one worker: 8 in r5c1, 9 in r5c3, the most
usable regions of the 14 (31,886). Other placements were not counted.

| Ninth region | Top fillings | Bottom fillings | Pairs with matching sizes |
|---|---|---|---|
| in top | 265,958 | 121,423 | 1,736,643 |
| in bottom | 3,020 | 1,971,316 | 746,047 |

The 2,482,690 matching pairs are an upper bound on this placement's layouts: each pair still needs every
region's two parts to form a listed region, one forced 7 and counts 1-6 on the low regions. Checking them
is small enough to finish, where CP-SAT hit 900 s on 12 workers. Its self-check compares the memo and the
size table with plain enumeration on a sampled list holding one planted filling. It passes, but each of the
four samples had only 1 filling, so it is a thin test of the memo's adding up.

`aqre_r5_split_enumerate.py DIR` then enumerated all 14 placements in about 11 minutes on one worker, Chris's
go. It found 490 layouts, and the fixed-region solve proved all 490 infeasible (232 without connectivity, 258
with it), so no grid came out. Layouts per placement:

| 8 | 9 | Layouts |
|---|---|---|
| r5c2 | r5c4 | 33, 129 |
| r5c4 | r5c2 | 33, 129 |
| r5c4 | r5c6 | 83, 83 |
| r5c1, r5c3 or r5c5 | any | 0 in all 8 placements |

On these lists (regions judged alone, colour known from the 8, forced 7, six low regions able to take 1-6),
this shape gives no grid. CP-SAT had hit its 900 s cap on all six cases without finding any of the 490. This
covers this 8 shape only. The enumerator's own self-check is thin: its sampled lists held just the 1 planted
layout and no strict layouts.

`aqre_r5_split_check.py DIR` is the stronger check, and it passed. All 490 layouts re-read from their grids with
0 errors. On the 6 placements with layouts, cut to every region their known layouts use plus 15 sampled per
column (151 to 201 regions), the join and a plain whole-board search returned the same layouts, 33 to 132 of any
class and 33 to 129 strict, including every known layout. Limits: both searches share `usable` and the table,
so an error in the region lists would not show. Only 3 layouts in that test were not strict, and the search
comparison covers sampled lists, not the full ones.

Chris's wording, 2026-11-04: 8 circles in r5, none of them 9, so the 9 is placed at once. Only one region can
be the 8 by shape alone, which places the 8 and fixes the checkerboard colouring. Of the other r5 regions only
one can be the circled 7. Each of the rest either tops out at 6 by shape, or allows 7 only shaded, on the wrong
colour. The neighbours play no part. The enumerator differs in one way: it judged other regions' 8 with colour
known, so a region on the 8's opposite colour was never refused for being able to be the 8. By shape alone it
must be. `aqre_r5_ruling_recount.py DIR` reads the 490 layouts this way: 214 have no other 8-able r5 region and
276 have 1 to 3. So the enumerator's lists are looser than the rule here, and the "no grid" holds for the
stricter rule too. In all 490 the 7 is on the 8's colour and forced shaded, as Chris described.

### The same shape in other rows

Chris, 2026-11-04: same protocol, same shape, all 8 circles in another row. Off r5, the top-bottom flip and
the 180 turn change the row, so only the left-right mirror still removes duplicates: r4 has 28 placements where
r5 has 14, and its halves are unequal, 3 rows above and 5 below. r6-r9 flip onto r4-r1. `aqre_row_enumerate.py DIR
ROW` does any row, with Chris's 8 test (by shape alone). It fills the rows above first, then below cell by cell.
It also has two speedups on Chris's go: the same cells with the 8 and 9 swapped are enumerated once, and the
7's column is chosen first, so that root tries only forced 7s and the others only regions that top out at 6.

Test of the search: an earlier version of this code, with neither speedup, reproduced r5's 490 layouts exactly with
the 8 test loosened to match, on all 14 placements. The final version reproduced the 129 known layouts of one
r5 placement, in 147 s against 691 s. The final version has not rerun all of r5.

| Row | Placements | Enumerated after swaps | Layouts | Solve | Grids |
|---|---|---|---|---|---|
| r5 | 14 | all 14, loosened 8 test | 490, of which 214 meet the 8 test | all 490 infeasible | 0 |
| r4 | 28 | 16 | 10 | all 10 infeasible without connectivity | 0 |
| r3 | 28 | 16 | 0 | nothing to solve | 0 |
| r2 | 14 | 8 | 0 | nothing to solve | 0 |
| r1 | 0 | 0 | 0 | nothing to solve | 0 |

So this 8 shape gives no grid in any row on these lists, since r6-r9 flip onto r4-r1 and a column is a row
turned 90 degrees. Only r5 and r4 have layouts at all. r1 has no placement: the 8 and 9 sit in the leg row next
to the shape's 3-wide bar, and neither direction fits on the board. In all 14 r2 placements the legs go up and
the bar sits below, so the r2 cell between the 8 and 9 and the r1 cell above it are walled in. Those 2 cells
have no region at all, and `aqre_row2_zero_check.py DIR` shows 0 r1 fillings with the class rules off as well.
That 2-cell pocket is geometry, and needs no digit or shading rule. The rule-dropping run had not finished here.

r4 took about 6 minutes on 8 processes, and its layouts all have the 8 and 9 in r4c2 and r4c4, either way
round. An earlier r4 search with neither speedup and a cruder fill below the row was stopped at 51 minutes.

So far, every layout on either row has the 8 on an even column, which has only 4 cells of its colour in the
row. No odd-column 8 has given a layout. That is a pattern, not a proof.

`aqre_r5_oriented.py DIR` rebuilds the lists with colour known, then runs the cover: first with the
forced 7, then without it. Any layout found goes to the fixed-region solve. The hill-climb's best was 3
shaded groups, and the forced-7 build was stopped since the same rule was proven unable to finish it.

### A board from another session

Chris pasted a jigsaw board from another session's scratch run, with its plan of a circle 8
region and a circle 7 built around it. `aqre_pasted_board.py` re-checks it here, one worker.

- Regions are all 9 connected cells. By no-4-in-a-line alone, the most shaded cells per region
  are 7 for regions 1-7 and 8 for regions 8 and 9, as that note said.
- Sudoku fills: at least 1000, the cap.
- Whole-board shading with no whispers and free counts: found in 0.4 s, reader clean, counts
  5 6 5 3 7 4 5 4 3.
- With 5-whispers on shaded cells and free counts: UNKNOWN at 120 s, which proves nothing.
- Counts equal to the printed labels 1-8: INFEASIBLE in under 0.1 s, with and without whispers.
  That label reading was my own test, not the note's rule, so it says little about the board.

## Rulings

All 2026-11-03.

- Circles count shaded cells in their box. Regions are the 3x3 boxes.
- Chris first asked for 0-8 digits and "9 circles with different values", then
  dropped both: digits are 1-9 and values may repeat.
- Every grid has 9 valid circles, so every box has a shaded cell.
- Chris rejected both negative rules, unshaded-within-4 and both-shaded. Their
  sections above are kept as a record, and the both-shaded question stays
  unsettled because nothing more will be run on it.
- Not tested: uniqueness.
- 2026-11-04: 5-whispers on shaded cells stay. The pasted board's note just did not mention
  them. Circles stop at 8, since no region can count 9 under whispers.
- 2026-11-04: the 8 circles must share one row or column. The pasted board fails that as drawn:
  its best row touches 6 regions and its best column 5.
- 2026-11-04: place the 8 region first; no other region may be able to count 8.

## Rebuild

From the repo root, each with the folder holding these scripts on the path:

    PYTHONPATH=.:finders/counting_shaded:docs/research/2026-11-03-aqre-whispers \
      uv run python docs/research/2026-11-03-aqre-whispers/aqre_disjoint_recheck.py

`aqre_whispers_feasible.py DIR` and `aqre_shaded_whispers_feasible.py DIR` wrote
`grid-1` and `grid-2`; `aqre_disjoint_feasible.py DIR` is the first infeasible
solve.

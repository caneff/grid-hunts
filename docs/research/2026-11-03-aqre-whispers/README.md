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

## Rebuild

From the repo root, each with the folder holding these scripts on the path:

    PYTHONPATH=.:finders/counting_shaded:docs/research/2026-11-03-aqre-whispers \
      uv run python docs/research/2026-11-03-aqre-whispers/aqre_disjoint_recheck.py

`aqre_whispers_feasible.py DIR` and `aqre_shaded_whispers_feasible.py DIR` wrote
`grid-1` and `grid-2`; `aqre_disjoint_feasible.py DIR` is the first infeasible
solve.

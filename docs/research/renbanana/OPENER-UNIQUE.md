# Renbanana opener — the 18-circle puzzle, proved unique

Map #373. Rules: 9x9 sudoku with a free chocolate/banana shading; every
chocolate group is a rectangle; every banana group is not a rectangle and is a
renban; orthogonally adjacent chocolate cells differ by at least 5 (German
Chocolate); a circle's digit equals the size of its own group.

**Verdict (2026-10-07): the 18 circles below, with no givens and no shading
clues, have exactly one solution. Proved by CP-SAT (INFEASIBLE second solve,
not a timeout).**

## Circles

```
r1c6 r1c9 r2c2 r2c4 r2c6 r2c7 r2c8 r3c3 r3c7
r4c6 r4c9 r5c2 r6c8 r7c2 r7c6 r8c2 r9c8 r9c9
```

## Solution (`opener/solution.json`)

Digits, then shading (`C` chocolate, `b` banana):

```
936871452   CCbCbCbbC
478256139   bbbCbbCbC
521439786   bbCbbCbCb
354982617   bCbCbCbCb
187364295   CbbbCbbCb
692715348   CbbCbbbCb
715693824   bCbbCCCbb
269148573   bbCCbbbCb
843527961   CbbbCbbbC
```

## Proof

```
uv run finders/renbanana/tools/probe_circle_pattern.py \
  --cells r1c6,r1c9,r2c2,r2c4,r2c6,r2c7,r2c8,r3c3,r3c7,r4c6,r4c9,r5c2,r6c8,r7c2,r7c6,r8c2,r9c8,r9c9 \
  --unique --known-solution docs/research/renbanana/opener/solution.json \
  --seconds 1800 --workers 8
```

printed `verdict: UNIQUE (proved -- no second solution exists)`. The grid also
passes `renbanana_verify.check` with these 18 circles (no violations).

## How it got here

- The 11-circle setup (r1c6 r1c9 r2c6 r2c7 r2c8 r3c7 r4c6 r4c9 r6c8 r7c6 r9c8)
  has exactly 34 solutions (exhaustive enumeration after the #746 fix). In all
  34, r3c7 = 7 and r8c1 = 2. 16 of the 34 can be singled out by adding circles;
  all 16 share r1c3 = 6 on banana.
- Chris's design added r2c2 r2c4 r3c3 r5c2 r7c2 r8c2 r9c9 and, briefly, a given
  2 at r8c1. The given turned out unnecessary and was dropped.

## Drop-one sweep (2026-10-07)

Each circle removed alone, the other 17 run through `--unique` (8 workers,
900 s cap; no run hit the cap):

- **Necessary** (drop it and a second solution exists): r2c2 r2c8 r3c7 r4c9
  r5c2 r8c2. Dropping r8c2 leaves the same digits with a different shading.
- **Redundant alone** (17 remaining still UNIQUE, proved): r1c6 r1c9 r2c4
  r2c6 r2c7 r3c3 r4c6 r6c8 r7c2 r7c6 r9c8 r9c9.

Redundant one at a time does not mean redundant together; a greedy removal
pass over the twelve follows.

## Greedy pass and the 12-circle minimal set (2026-10-07)

Chris dropped r3c3. From the 17 remaining, each candidate was tried in turn
(Chris's additions first, opener circles last), dropped when the rest still
proved UNIQUE. No run hit the 900 s cap.

- Dropped: r2c4 r7c2 r9c9 r6c8 r9c8.
- Kept (second solution found when dropped): r1c6 r1c9 r2c6 r2c7 r4c6 r7c6.

**Result: 12 circles, unique and inclusion-minimal**

```
r1c6 r1c9 r2c2 r2c6 r2c7 r2c8 r3c7 r4c6 r4c9 r5c2 r7c6 r8c2
```

Minimal because removing circles only adds solutions: a circle that failed
to drop from a larger set also fails from this subset, and the six from the
drop-one sweep fail from the full set. Not shown to be the minimum count;
another removal order could reach a smaller set.

## Final puzzle (Chris, 2026-10-08)

The 12-circle minimal set plus r3c3, 13 circles, no givens:

```
r1c6 r1c9 r2c2 r2c6 r2c7 r2c8 r3c3 r3c7 r4c6 r4c9 r5c2 r7c6 r8c2
```

Unique: it is a superset of the proved-unique 12, and adding a circle cannot
add a solution. The solution is `opener/solution.json`.

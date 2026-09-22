# QQRR opener verdict (#593)

**An earlier eleven-run record for this ticket, held only on branch commits
up to `09f8990` and never landed on `main`, was invalidated by #598**:
`finders/qqrr/checker.py`'s `load_opener` mapped a "QR Ranks" symbol `[x,
y]` to the window whose top-left cell was `(row y, col x)`, but the symbol
sits on a grid intersection — the window it marks is the four cells around
that point, top-left `(row y-1, col x-1)`. #599 fixed the mapping (squash
`55cb83a`, on `main`). That eleven-run record included two hypothesis-group
split runs (entered digits alone, uncircled marks alone) built to localize
the mapping-bug-era infeasibility; this rerun's own diagnostic (run 9,
below) is feasible, so there is nothing left to localize and the split isn't
repeated here. This is a full rerun on the corrected checker; nothing below
is inherited from the earlier attempt.

Nine runs of `finders/qqrr/qqrr_cpsat.py` against `finders/qqrr/opener.json`,
each under `job-run --name qqrr-opener-<label>`, sequential (one solver
process live at a time — see Deviations), `--workers 16 --timeout 600`:

```
uv run finders/qqrr/qqrr_cpsat.py --corner <tl|tr|bl|br|none> [--hypotheses] \
  --workers 16 --timeout 600 --progress <path>.log
```

Eight per issue #591's protocol (hypotheses on then off, by corner for the
QQRR 5), plus a ninth diagnostic (hypotheses on, no corner) to separate the
corner pin from the hypotheses as a possible source of infeasibility.

**Deviation from the map's protocol, controller-authorized, not the worker's
own choice.** The map calls for the eight numbered runs at 4 in parallel / 6
workers when the box is quiet, else sequential at 16. The parallel launch and
a first sequential attempt at 16 were both denied by this session's
permission classifier ("Interfere With Workloads"), reported verbatim to the
controller (qqrr-17), which relayed Chris's ruling: run sequential at 16
workers throughout, one solver process live at a time — that ruling is what
every run below actually used. The controller also ordered run 9, past the
map's eight.

Real clues, every run — always fixed, `--hypotheses` or not, per
`finders/qqrr/checker.py`'s `load_opener`: window marks circled in the link
are `window_clues` (the window-symbol-to-grid mapping fixed by #599); the
cage is always a `cell_clue`; the corner is whichever `--corner` names. QR 10
at window top-left (row 5, col 5); QR band 58–64 at window (row 3, col 3);
QR band 51–56 at window (row 1, col 4); QQRR 33 at cell (row 0, col 4); QQRR
5 at the corner under test (tl/tr/bl/br), or absent on run 9. Hypotheses,
fixed only on the
`--hypotheses` runs, per `load_opener`'s `window_hypotheses`/
`digit_hypotheses`: the three uncircled QR marks — 9 at window (row 2, col
1), 8 at window (row 3, col 0), 1 at window (row 2, col 0) — and the 13
entered digits from `finders/qqrr/OPENER_NOTES.md`'s grid
(`finders/qqrr/test_checker.py` asserts this count). Plain sudoku
underneath. The rank tables below (window ranks, cell ranks) follow the QR
and QQRR tie-rank rule as `finders/qqrr/OPENER_NOTES.md` § Rule states it —
ties share the lower rank and ranks after a tie are skipped, so a repeated
value followed by a gap in a rank row is that rule, not a transcription
error.

## Runs

Every run's `--count` was 2 (`qqrr_cpsat.py`'s default), so `multiple` below
means "at least 2 solutions, search capped at 2" — CP-SAT stops as soon as it
finds the second, so `multiple` is a proven verdict (an exhibited solution),
`infeasible` a proven one too (a proof of no solution), and no run's status
was inferred from staying short of the 600s ceiling.

| # | corner | hypotheses | status | wall clock |
|---|---|---|---|---|
| 1 | tl | on | infeasible | 1.7s |
| 2 | tr | on | multiple | 3.5s |
| 3 | bl | on | infeasible | 1.6s |
| 4 | br | on | multiple | 3.2s |
| 5 | tl | off | infeasible | 34.7s |
| 6 | tr | off | multiple | 9.2s |
| 7 | bl | off | infeasible | 35.9s |
| 8 | br | off | multiple | 16.6s |
| 9 | none | on | multiple | 3.2s |

No run approached the 600s ceiling.

## Grid and rank tables, feasible runs

### Run 2 — corner tr, hypotheses on, solution 1

```
4 5 3 7 6 1 2 9 8
9 6 7 2 8 5 3 1 4
1 2 8 3 9 4 5 6 7
2 1 4 9 5 8 7 3 6
6 8 5 1 3 7 4 2 9
3 7 9 6 4 2 8 5 1
5 9 1 8 7 3 6 4 2
7 4 6 5 2 9 1 8 3
8 3 2 4 1 6 9 7 5
```

window ranks (by top-left cell)
```
26 33 20 49 37  2 13 64
62 41 44 11 55 32 15  4
 1  9 51 21 60 25 34 42
 8  5 28 61 35 57 46 16
43 54 30  3 18 47 24 14
19 50 63 39 22 10 53 29
36 58  6 56 45 17 38 23
48 27 40 31 12 59  7 52
```

cell ranks
```
 2 22 27 20 33  7  6 15  5
23 62 64 57 74 44 40 37 11
10 34 46 70 54 78 63 38  8
 1 19 36 75 58 81 61 65 30
13 35 48 41 50 66 80 72 17
31 69 77 42 43 55 73 60 16
18 56 47 51 68 59 53 76 25
28 67 49 52 79 71 39 45 21
 3 32 24 29 26 14  9 12  4
```

### Run 2 — corner tr, hypotheses on, solution 2

```
3 4 5 7 6 1 2 8 9
9 7 6 2 8 4 3 1 5
1 2 8 5 3 9 7 4 6
2 1 3 9 7 8 5 6 4
6 8 4 3 1 5 9 7 2
5 9 7 6 4 2 8 3 1
4 6 2 8 9 3 1 5 7
7 3 9 1 5 6 4 2 8
8 5 1 4 2 7 6 9 3
```

window ranks (by top-left cell)
```
19 27 34 47 37  2 10 56
60 47 39 12 52 26 18  7
 1  9 54 30 22 64 46 28
 8  3 20 61 50 55 32 40
43 53 25 16  4 35 63 44
36 62 47 42 24 10 51 15
29 38 13 56 59 16  4 33
45 21 58  4 31 41 23 14
```

cell ranks
```
 3 16 21 26 33  7  6 14  5
17 54 60 64 72 45 43 38  9
11 34 48 68 53 74 59 42 12
 2 18 36 76 62 56 81 71 22
13 35 44 55 52 49 77 63 28
30 70 75 58 41 47 65 80 31
27 66 79 73 69 57 37 50 15
23 61 67 39 51 78 40 46 25
 4 32 19 10  8 24 29 20  1
```

### Run 4 — corner br, hypotheses on, solution 1

```
3 5 6 7 9 1 4 2 8
9 7 4 2 8 6 5 3 1
1 2 8 5 3 4 9 6 7
2 1 5 9 4 8 6 7 3
4 8 3 6 1 7 2 9 5
6 9 7 3 5 2 8 1 4
5 6 2 8 7 3 1 4 9
7 4 9 1 6 5 3 8 2
8 3 1 4 2 9 7 5 6
```

window ranks (by top-left cell)
```
19 33 41 50 59  4 22 10
63 48 23 12 55 39 31 16
 1  9 54 30 17 28 62 42
 8  5 35 60 24 56 40 47
25 53 20 36  7 44 14 61
43 64 45 18 29 10 51  3
33 37 13 57 46 15  2 27
49 26 58  6 38 32 21 52
```

cell ranks
```
 3 16 25 28 33  9  7 20  1
17 55 65 70 75 49 45 57 14
11 35 46 58 52 78 68 63 15
 2 18 37 77 62 53 60 80 29
13 36 47 66 50 43 79 69 31
21 59 76 56 44 51 72 40 10
30 71 81 73 54 61 38 34  6
26 64 67 39 48 74 41 42 23
 4 32 22  8 12 27 24 19  5
```

### Run 4 — corner br, hypotheses on, solution 2

```
5 3 6 7 9 1 2 8 4
9 7 4 2 8 3 6 1 5
1 2 8 5 4 6 7 3 9
2 1 7 9 5 8 3 4 6
4 8 3 1 6 7 9 5 2
6 5 9 4 3 2 8 7 1
3 9 1 6 7 4 5 2 8
7 6 2 8 1 5 4 9 3
8 4 5 3 2 9 1 6 7
```

window ranks (by top-left cell)
```
31 19 40 48 59  2 13 55
64 46 22 12 52 18 36  4
 1  9 56 33 26 42 44 20
 8  7 50 62 34 54 17 25
27 53 15  6 39 48 63 30
38 35 61 23 16 10 57 43
21 58  5 41 45 24 29 14
47 37 11 51  3 32 28 60
```

cell ranks
```
 2 25 17 30 33 11  6 15  4
26 66 58 71 74 48 39 37 10
12 34 44 60 54 76 57 41  8
 1 18 36 79 67 63 72 73 19
13 35 52 45 50 68 78 56 21
22 64 77 38 51 70 75 81 24
29 69 40 49 61 55 53 80 31
20 59 47 46 42 43 62 65 16
 3 32 28 14  9  7 27 23  5
```

### Run 6 — corner tr, hypotheses off, solution 1

```
5 6 3 7 4 1 2 8 9
9 7 4 2 8 6 5 1 3
1 2 8 5 3 9 7 4 6
2 1 5 9 7 8 6 3 4
4 8 6 3 1 5 9 7 2
3 9 7 4 6 2 8 5 1
7 3 2 8 9 4 1 6 5
6 4 9 1 5 7 3 2 8
8 5 1 6 2 3 4 9 7
```

window ranks (by top-left cell)
```
32 37 19 46 23  2 11 56
60 46 24 12 53 42 30  3
 1  9 52 31 21 64 49 25
 8  6 35 61 50 54 39 18
27 55 37 15  4 34 63 43
20 62 46 26 36 10 51 29
45 16 13 57 59 22  7 41
40 28 58  4 33 44 16 14
```

cell ranks
```
 3 24 27 17 33  7  6 14  5
25 62 67 55 71 43 41 38 10
12 34 46 58 53 75 69 44  8
 2 18 36 74 61 57 81 73 20
13 35 51 64 50 47 76 68 16
21 60 77 66 40 45 63 80 30
19 56 79 72 59 65 37 48 23
32 70 54 39 49 78 42 52 29
 4 28 22 11  9 26 31 15  1
```

### Run 6 — corner tr, hypotheses off, solution 2

```
5 6 3 7 4 1 2 8 9
9 7 4 2 8 6 5 1 3
1 2 8 5 3 9 7 4 6
2 1 5 9 7 8 6 3 4
3 8 6 4 1 5 9 7 2
4 9 7 3 6 2 8 5 1
7 3 2 8 9 4 1 6 5
6 4 9 1 5 7 3 2 8
8 5 1 6 2 3 4 9 7
```

window ranks (by top-left cell)
```
32 37 19 47 24  2 11 56
60 47 25 12 53 42 30  3
 1  9 52 31 21 64 49 26
 8  6 35 62 50 54 38 17
20 55 39 22  4 34 63 43
28 61 44 18 36 10 51 29
46 15 13 57 59 23  7 41
40 27 58  4 33 45 15 14
```

cell ranks
```
 3 24 27 17 33  7  6 14  5
25 62 66 56 72 43 40 38 10
12 34 46 59 53 75 69 44  8
 2 18 36 74 61 58 81 73 20
13 35 51 64 50 47 76 67 16
19 57 77 68 41 45 63 80 30
22 60 79 70 55 65 37 48 23
32 71 54 39 49 78 42 52 29
 4 28 21 11  9 26 31 15  1
```

### Run 8 — corner br, hypotheses off, solution 1

```
6 5 3 7 4 9 1 2 8
9 7 4 2 8 1 5 6 3
1 2 8 6 3 5 7 4 9
2 1 5 9 7 8 4 3 6
4 8 7 3 5 6 9 1 2
3 9 6 4 1 2 8 5 7
5 4 2 8 9 3 6 7 1
7 3 9 1 6 4 2 8 5
8 6 1 5 2 7 3 9 4
```

window ranks (by top-left cell)
```
41 30 19 47 29 58  2 12
63 47 25 12 51  5 33 37
 1  9 55 38 16 35 49 28
 8  6 36 64 50 52 26 17
27 56 45 15 32 43 60  3
20 62 40 22  4 10 53 34
31 23 14 57 61 18 42 44
46 21 58  7 39 24 11 54
```

cell ranks
```
 3 29 24 16 33 23  9  7  1
30 68 61 56 72 43 34 40 15
11 35 46 59 53 47 48 63 27
 2 17 37 77 66 54 64 73 22
13 36 51 65 81 74 75 42  6
21 60 78 71 39 44 70 50  8
18 57 80 67 41 45 52 76 26
25 62 58 38 49 79 55 69 31
 4 32 19 10 12 28 20 14  5
```

### Run 8 — corner br, hypotheses off, solution 2

```
6 5 3 7 4 9 1 2 8
9 7 4 2 8 1 5 6 3
1 2 8 6 3 5 7 4 9
2 1 5 9 7 8 4 3 6
3 8 7 4 5 6 9 1 2
4 9 6 3 1 2 8 5 7
5 4 2 8 9 3 6 7 1
7 3 9 1 6 4 2 8 5
8 6 1 5 2 7 3 9 4
```

window ranks (by top-left cell)
```
41 30 19 46 29 58  2 12
63 46 24 12 51  5 33 38
 1  9 55 39 16 35 48 27
 8  6 36 64 50 52 25 17
20 56 49 26 32 43 60  3
28 62 37 15  4 10 53 34
31 22 14 57 61 18 42 44
45 21 58  7 40 23 11 54
```

cell ranks
```
 3 29 24 16 33 23  9  7  1
30 68 61 56 71 43 34 40 15
11 35 46 59 53 47 48 63 27
 2 17 37 77 67 54 64 72 21
13 36 51 65 81 74 75 41  6
18 57 78 73 42 44 70 50  8
22 60 80 66 39 45 52 76 26
25 62 58 38 49 79 55 69 31
 4 32 19 10 12 28 20 14  5
```

### Run 9 — no corner, hypotheses on, solution 1

```
4 6 5 7 9 1 3 8 2
9 3 7 2 8 6 5 1 4
1 2 8 4 3 5 9 7 6
2 1 3 9 5 8 4 6 7
5 8 6 3 7 4 1 2 9
7 4 9 1 6 2 8 3 5
6 9 2 8 4 3 7 5 1
3 5 4 6 1 7 2 9 8
8 7 1 5 2 9 6 4 3
```

window ranks (by top-left cell)
```
28 40 33 50 59  3 21 51
61 19 44 11 56 41 30  5
 1  9 53 25 16 36 63 49
 8  4 22 62 34 54 26 42
34 57 39 18 46 23  2 13
47 29 58  6 38 10 52 15
43 60 12 55 24 20 48 31
17 32 27 37  7 45 14 64
```

cell ranks
```
 3 21 27 25 33 10  6 19  4
22 60 67 62 74 51 45 40  8
11 34 38 70 54 77 68 44  9
 2 18 36 76 59 56 65 81 32
13 35 47 58 80 63 48 43 28
26 64 78 46 37 71 41 39 14
31 72 61 50 52 66 53 75 16
29 69 79 55 49 42 57 73 23
 1 17 24 20  7 12 30 15  5
```

### Run 9 — no corner, hypotheses on, solution 2

```
5 3 6 7 9 1 4 2 8
9 4 7 2 8 3 6 5 1
1 2 8 5 4 6 7 3 9
2 1 5 9 6 8 3 4 7
6 8 3 4 1 7 2 9 5
4 7 9 3 5 2 8 1 6
3 9 1 8 7 4 5 6 2
7 5 4 6 2 9 1 8 3
8 6 2 1 3 5 9 7 4
```

window ranks (by top-left cell)
```
32 18 40 49 60  2 23 11
62 27 45 12 52 19 39 30
 1  9 56 34 26 41 46 20
 8  3 36 64 42 53 15 29
43 55 16 22  5 44 14 63
28 50 61 17 31 10 51  4
21 58  6 57 47 24 35 38
48 33 25 37 13 59  7 54
```

cell ranks
```
 3 25 16 30 33  9  6 20  1
26 65 58 69 76 49 38 61 14
10 34 41 73 54 77 59 68 24
 2 17 36 80 66 62 70 74 18
13 35 42 67 51 44 78 55 23
31 71 79 56 39 47 72 37 11
22 63 45 50 57 64 53 46  7
19 60 48 52 81 75 40 43 29
 4 32 27 21 28 15  8 12  5
```

## Readout

**Which corners survive.** Two of four: tr and br, under both hypotheses
settings (runs 2, 4, 6, 8, all `multiple`). Corners tl and bl fail outright,
clues-only, hypotheses off entirely — runs 5 and 7 are both `infeasible`
before a single entered digit or uncircled mark enters the model. Adding the
hypotheses (runs 1, 3) doesn't newly break tl/bl; they were already broken.
So the QQRR-5 corner is real information: the five real clues (QR 10, QR
58–64, QR 51–56, QQRR 33, and QQRR 5 at that corner) rule out top-left and
bottom-left on their own, leaving top-right and bottom-right as the only
candidates. Nothing here distinguishes tr from br yet.

**Whether the entered digits can all stand.** Yes, at the two surviving
corners. Runs 2, 4 and 9 (hypotheses on, corner tr/br/none respectively) are
all `multiple` — the 13 entered digits and the three uncircled marks coexist
with the real clues at both live corners and with no corner fixed at all. The
earlier (pre-#599) run set's hypotheses-on infeasibility at every corner and
at none (its runs 1–4 and 9) was the mapping bug, not a genuine conflict in
the hypotheses: under the corrected window mapping, the hypotheses hold up
at both corners the clue set itself leaves open (tr, br) and with no corner
fixed. tl and bl stay infeasible with hypotheses on (runs 1, 3) too, but
that's the clue set closing those corners outright (runs 5, 7 show the same
without any hypotheses in play), not the digits or marks failing. (The old
record's hypotheses-off runs 5–8 were already `multiple`, so the mapping
bug's effect was confined to the hypotheses-on
half of that record.)

**How open the opener is.** Open at both surviving corners, hypotheses or
not: 3.2–16.6s to a second solution, well short of the 600s ceiling. tl and
bl are closed outright by the clue set. The next
useful move is likely a run that adds real clues (not hypotheses) at tr and
br specifically, since both remain a `multiple` result away from a unique
grid, or a targeted search for what single additional clue would separate
them.

## Raw progress files

`.scratch/{on,off}-{tl,tr,bl,br}.log`, `.scratch/on-none.log` — gitignored,
not shipped, and scoped to this ticket's task worktree, so they don't outlive
it. The grid, window-rank and cell-rank tables above are the durable copy;
re-run the invocation at the top of this doc to regenerate the logs.

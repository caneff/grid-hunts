# Halver + lockout lines: notes from the rule check (#54)

Facts found while building `finders/halver_lockout/` (spec #52). The hunt
slice builds on them.

## The gap, in doubled values

- A value is a halver's digit / 2, any other cell's digit (`GLOSSARY.md`).
  The lockout gap of 4 is on values, so the code's doubled values must
  differ by 8.
- SudokuMaker's own gap is half the digit count, rounded down
  (`LockoutLines` handler, `MinimumDifferenceComponent(floor(digitCount / 2))`
  in `caneff/sudokumaker-custom-constraints`,
  `examples/_shared/vendor/bundle.claude.js`, read 2026-10-19). Type 407
  stores `lines` as cell-index paths, ends first and last, as type 403 does.
- On 4x4 the values span 0.5 to 4, so a gap of 4 leaves every lockout line
  infeasible. The 4x4 agreement test therefore runs at a gap of 2,
  SudokuMaker's 4x4 gap.

## The backtracking check is slow on lockout boards

Measured on one worker, 2026-10-19:

| board | CP-SAT check | backtracking search |
| --- | --- | --- |
| 23 lines from the target-grid loop, unique | 27.0 s | no verdict in 20 min |
| the same plus 10 three-cell lines | 2.8 s | no verdict in 60 s |
| plus 20 | 0.3 s | 8.3 s |
| plus 30 (the gate's `fixtures/unique.json`) | 0.2 s | 1.0 s |
| four diamonds pairwise joined by six lines, infeasible | under 1 s | no verdict in 60 s |

- Why: a lockout body may take any value outside its diamonds' range, so
  one line's narrowing barely narrows. Every cell keeps most of its 18
  doubled values, and the shared search branches on halver placements
  (9 places per house) long before any diamond is set.
- Adding `between_narrowing`'s room check (a body's cells in one house need
  that many distinct digits outside the range) did not change either
  verdict.
- Branching on diamond cells first, tried in a scratch copy of
  `halver_brute.py`, settled the four-diamond board at once (0.0 s), but not
  the 23-line board within 60 s, with or without halver-house branching.
- **For the hunt:** `verify` re-reads each hit with this search. A hit near
  23 lines will not finish in `halver_between`'s 600 s verify budget unless
  the search gets stronger: a narrowing that reasons across lines, or a
  branching order the shared layer offers per line type.

## What settled it: end probing on a C search (#59)

Each approach tried on the two boards #59 names, one worker, 2026-10-19.
The 23-line board is `finders/halver_lockout/fixtures/unique_23.json`; the
four-diamond board, `fixtures/four_diamonds.json`, is four diamonds at
r2c2, r2c6, r6c2 and r6c6 joined pairwise by six lines that keep the
drawing rules. It has no solution because four values each at least 4 from
the others span 12, and values run 0.5 to 9. "Tree" is a Knuth random-probe
estimate of the search tree's size: it ran low on this tree, so read it as
a floor.

| approach | four diamonds | 23 lines |
| --- | --- | --- |
| #54's search | no verdict in 60 s | no verdict in 20 min (#54) |
| diamonds branched first, fewest choices | infeasible, 0.0 s (19 nodes) | no verdict in 300 s; tree ~4.6e7 |
| + pattern overlay (each digit and the halvers fill one of the 46,656 one-per-house placements) | — | no verdict in 120 s; 53-line board 3707 → 3440 nodes |
| + Hall sets on each house's digits | — | no verdict in 60 s; 53-line board 3707 → 3080 nodes |
| diamond values split low / high | infeasible, 0.0 s | no verdict in 60 s |
| diamonds in board order (by row, by column, by box, along lines) | — | by row: no verdict in 60 s; tree 3.9e6 (by row) to 8.5e7 |
| event-driven narrowing (same fixpoint), alone | no verdict in 60 s | 1.65x the node rate, no verdict |
| + every line-end choice probed at every node, diamonds first | infeasible, 0.0 s | no verdict in 590 s (64 nodes/s); tree ~1.2e5 |
| + dom/wdeg branching | — | no verdict in 120 s |
| probing in the top 4 levels only | — | no verdict in 590 s (9.2 M nodes) |
| the same search in C, no probing | — | no verdict in 60 s (168,000 nodes/s) |
| **the same search in C, end probing at every node** | **infeasible, 0.0 s** | **unique, 202.8 s** (`test_unique_23.py`; 401,745 nodes in the prototype) |

- Sudoku-side reasoning was not the gap: the overlay and Hall sets barely
  moved the node count. Probing was: trying each diamond value and dropping
  the ones that fail cut the tree about 1500 times, but costs about 135
  narrowings a node, which Python could not pay.
- The C search is `finders/halver/halver_brute_c.py` (`halver_brute.c`,
  built with the system gcc). A line type's narrowing reaches it as a table
  of the end pairs it allows, each with its body cells' doubled values, so
  no line code is ported. `halver_lockout`'s check runs on it;
  `halver_between` stays on the Python search, which gains the same
  event-driven narrowing and an opt-in `probe_ends`.
  `finders/halver_lockout/test_brute.py` checks the two searches give the
  same solutions in the same order on every 4x4 line and every 9x9 fixture.
- The 23-line board's check is `finders/halver_lockout/test_unique_23.py`,
  in `just test-slow`; the four-diamond board is in the gate.

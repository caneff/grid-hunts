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

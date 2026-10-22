# Doppelganger and Full Rank: the published rules

Research for a new finder, 2026-10-22. Rule text is quoted from the LMD pages;
where only a search snippet was seen, that is said. No existing Full Rank or
Doppelganger solver was found (web search for GitHub / CP-SAT / OR-Tools
solvers; GitHub's own search was not run, so absence there is not proven).

## Full Rank

Origin: Gliperal, "Full Rank Sudoku", 2023-04-03
(https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?chlang=en&id=000DHO,
snippet only):

> Normal sudoku rules apply. Considering all rows and columns as 9-digit
> numbers read from the direction of the clue and ranked from lowest (1) to
> highest (36), a clue represents where in the ranking that row/column lies.

Andrewsarchus, "Diamond Rank", 2026-01-20 (000R3I, fetched):

> A value in an external cell represents the rank of the number formed by
> reading the digits in that row or column from that direction, where (1) is
> the lowest such number and (36) is the highest. (The 36 numbers are
> distinct - no ties).

Plain rule: each of the 9 rows and 9 columns is read in both directions, 36
numbers; a clue outside the grid ranks the number read away from it, 1 lowest.
In plain sudoku the 36 are distinct, and exactly four start with each digit,
so rank 1-4 starts with 1, 5-8 with 2, and so on.

Variants seen: ties allowed with competition ranking ("Full Skyscraper Rank",
aqjhs, 000TR2: "One or more equal numbers are considered to be at rank N when
there are N-1 numbers of strictly lower rank"); an embedded 5x5 with leading
zeros (aqjhs, 000OMF, snippet); a rank on an arrow inside the grid
(Kaktuslav, 000PQX). No rows-only or 6x6 Full Rank found.

## Doppelganger (Kafkapharnaum)

Origin: Kafkapharnaum, "Doppelgangers", 2021-03-18
(https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=0005Q2):

> Every row, column, and box contains the digit 0 always, as well as eight out
> of the nine digits from 1 to 9 (ie, it's missing one digit that is not 0)
> – No two rows, no two columns, and no two boxes may be missing the same
> digit – For each 0 in the grid, the digits missing in its row, its column,
> and its box must be three different digits

The same page: "a zero always acts as itself – ie, the lowest possible value –
regardless of what digits it's replacing". Used at 6x6, 5x5 and 4x4 too
("Lesser Doppelganger", 0008UV). Some puzzles add tracking cells outside the
grid for each unit's missing digit; whether they are part of the answer varies.

A different rule shares the name: Andrewsarchus's "Doppelganger Landvermessung
U-Bahn" (000OEY) uses two 4x4 Doppelganger grids as U-Bahn clue strips, with
auxiliary grids the solver fills. Not the rule above.

## The two together

aqjhs, "pull prank", 2025-09-06
(https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?chlang=en&id=000OMG,
fetched), the one full-grid combination found:

> Every row, column, and box contains an empty cell always, as well as eight
> out of the nine digits from 1 to 9 (ie, it's missing one digit).
> [...] The digits on columns and rows, read in both directions, make a total
> of 36 eight-digit numbers. [...] There are no ties in rank.

Here the 0 is an empty cell and is skipped, so every number has eight digits.
Skipping is read from "eight-digit"; the page does not state it outright.

Open for a finder: whether the 0 is read as a digit (nine-digit numbers, 0 the
lowest) or skipped; and ties. A row and a column may miss the same digit, so
under either reading two of the 36 numbers can be equal unless a rule forbids
it: both published combinations state "no ties" as a rule.

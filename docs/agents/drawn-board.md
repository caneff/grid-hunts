# Checking a board Chris drew

Chris draws a board and asks whether it holds. Answer that question, not a
nearby one. In the weekly verify pass of 2026-11-08, sessions answered a
different question four times in one hunt.

## As drawn

- **Hold everything he drew**: every mark, pink and green colour, digit,
  pencil mark, outside clue and corner set. Never drop one to make the board
  feasible; a conflict is reported with the minimal set of his items that
  causes it.
- **Use the rule set he names and no other.** The negative rule is on only
  when he says "negative". Never toggle it to see what changes, and never
  add it back after a first answer.
- **Marks alone means marks alone.** Do not add digit logic (a digit-based
  deduction, a forced cell from the givens) when he asked about the marks.
- **Say which rule set you ran** in the first line of the answer, so a wrong
  reading is visible at once.

## Input shape

`nr_check.py` reads one JSON file; its docstring is the source for the keys:

```
{"marks": ["r2c1", ...], "pink": [...], "green": [...], "digits": {"r1c1": 9},
 "pencils": {"r2c1": "2367"}, "outside": {"T7": 5},
 "corners": [{"digit": 9, "cells": ["r4c1", "r7c1"]}]}
```

Run `uv run docs/research/2026-11-04-numbered-rooms-pro-battenburg/nr_check.py
BOARD_JSON [negative]`. Examples: `board34.json` in the same folder. A rule
family with no checker gets one that reads this same JSON.

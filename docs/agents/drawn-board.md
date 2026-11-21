# Checking a board Chris drew

Chris draws a board and asks whether it holds. Answer that question, not a
nearby one. In the weekly verify pass of 2026-11-08, sessions answered a
different question four times in one hunt.

## As drawn

- **Hold everything he drew**: every mark, pink and green colour, digit,
  pencil mark, outside clue and corner set. Never drop one to make the board
  feasible.
- **Use the rule set he names and no other.** The **negative constraint**
  (`GLOSSARY.md`; he says "negative") is on only when he says so. Never
  toggle it to see what changes, and never add it back after a first answer.
- **Marks alone means marks alone.** Do not add digit logic when he asked
  about the marks. `nr_check.py` has no marks-only mode: write a board JSON
  that holds only his `marks` (and `outside`, if he named it) and run that.
  On a file that also holds digits, only the first output line
  (`marks alone feasible:`) leaves them out; the grid, status map and digit
  table after it do not.
- Here `marks` are the drawn marks of the Numbered Rooms board, not the
  glossary's **mark** (a pencilled deduction).

## Input shape

The input is the board JSON `nr_check.py` reads (keys `marks`, `pink`,
`green`, `digits`, `pencils`, `outside`, `corners`); its docstring is the
source for them. Run:

```
uv run docs/research/2026-11-04-numbered-rooms-pro-battenburg/nr_check.py BOARD_JSON [negative]
```

`board34.json` in the same folder is an example.

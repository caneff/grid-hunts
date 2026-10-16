# Half Hearted: final version

Chris's board `mrHrMLKQCH` ("Half Hearted", 9 between lines), finished with
between lines only: no givens. Chris ruled this version final on 2026-10-16.
It is the last of his hand edits on hunt finish 11 (the hunt and its pages:
`2026-10-16-halver-between-hunt-decision-log.md`).

Link, no entered values: `2026-10-16-half-hearted-final-link.txt`.

## Lines (14)

B = a line of the original board it keeps; E = a line from the edits.

| Line | Circle | Body | Circle |
|---|---|---|---|
| B1 | r4c3 | r4c4 r5c4 r5c5 r4c5 r4c6 r5c6 r6c6 r6c5 r6c4 | r6c3 |
| B2 | r8c3 | r7c3 r6c2 | r6c1 |
| B3 | r6c1 | r7c1 r8c1 r8c2 r9c2 r9c3 | r9c4 |
| B4 | r4c2 | r3c2 r2c2 r2c1 r3c1 | r4c1 |
| B5 | r9c4 | r9c5 r9c6 r8c6 r7c5 r7c4 | r8c3 |
| B6 | r4c1 | r5c1 r5c2 | r4c2 |
| B7 | r9c7 | r9c8 | r9c9 |
| B8 | r7c8 | r7c9 r8c9 r8c8 r8c7 | r7c7 |
| E1 | r7c8 | r6c9 r5c9 r4c9 r5c8 | r4c8 |
| E2 | r7c8 | r6c8 r5c7 r4c7 r3c7 | r3c8 |
| E3 | r2c6 | r2c5 r2c4 r2c3 r1c3 | r1c4 |
| E4 | r4c2 | r3c3 r3c4 r3c5 | r3c6 |
| E5 | r2c8 | r2c7 r1c6 r1c5 | r1c4 |
| E6 | r2c8 | r2c9 r1c8 | r1c7 |

## Unique solution

Digits and halver placement both unique.

```
196427538
735869412
842531679
281754396
453196287
679283145
517648923
368912754
924375861
```

Halvers: r1c6 r2c7 r3c1 r4c3 r5c5 r6c9 r7c8 r8c2 r9c4.

## Checks (run 2026-10-16, scratch copy of `finders/halver_between`)

- `RuleModel(lines).check` (CP-SAT, digits plus halver booleans): `unique`.
- `brute.solutions` (backtracking, no shared code with the model): exactly 1
  solution in 1.8 s, equal to the one above.
- `candidates.shape_violation` on every line: none.

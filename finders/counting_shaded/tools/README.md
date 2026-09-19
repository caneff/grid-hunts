# counting_shaded research scripts

One-off probes behind `docs/research/2026-09-16-counting-shaded-connected.md`
(6x6 sections). Each imports `gridenum` from the parent folder; run with
`uv run --with pillow finders/counting_shaded/tools/<script>.py ...`.

- `verify_render.py UNIQUES_GLOB out.png out.jsonl` (env `LATIN=1`, `SELF=1`): independent CP-SAT check of all-visible uniques from the rule text, plus a sheet.
- `cave_circle.py uniques.jsonl out.png`: circle valid cave clues on both colours.
- `cave_unique.py uniques.jsonl`: is each grid unique from its cave clues, as digits or as marks, with subsets.
- `marks_sheet.py uniques.jsonl out.png`: the grid-1 four-mark puzzles, blank and solved.
- `regions.py uniques.jsonl out.json`: cut a Latin square into six connected 1-6 regions.
- `pinpuzzle.py --shaded 30,35 [--latin] [--both] [--self] --out hits.jsonl`: one-given puzzles with shown shaded cells.
- `pairsheet.py 11,30 out.png`: every shape with a grid for two forced cells, sudoku and Latin, rendered.
- `cc_search.py N BR BC latin|boxes`: shapes obeying the Counting Circles rule.

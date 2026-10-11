# grid-hunts

One-off grid finders: Python code that hunts, verifies and renders candidate
grids for puzzle rules, mostly on OR-Tools CP-SAT. Each finder lives under
`finders/`; its notes, hunt outputs and precomputed catalogues live under
`docs/research/`.

```
uv sync
uvx --from rust-just just check
```

Start with `AGENTS.md`. The history up to 2026-10-11 comes from
[caneff/sudokumaker-custom-constraints](https://github.com/caneff/sudokumaker-custom-constraints),
where the finders began; an issue number in a commit message from before that
date is that repo's.

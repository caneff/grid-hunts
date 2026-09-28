# A real hunt killed and resumed on the protocol (#626)

**Result: the protocol survives a real kill and resume.** The #491 qqrr tie
finder ran 4 seeds under `job-run`, was SIGKILLed mid-solve in seed 2, and the
same command resumed and finished. The output directory is
`2026-09-28-qqrr-tie-kill-resume/`. No grid was expected or found: this checks
the protocol's files, not the search.

**Run** (at `bcc6021`, 1 solver worker, `ulimit -v` 8 GB, box load about 4):

```
finders/qqrr/hunt/tie_finder.py --out docs/research/2026-09-28-qqrr-tie-kill-resume \
  --seeds 0:4 --workers 1 --hunt r1c5 --ten r7c7 --corner tr --timeout 60 --q34
```

1. `job-run --name qqrr-tie-killresume-626`, started 15:51. Seeds 0 and 1 each
   hit the 60 s cap (`seed_done`, `empty_reason: timeout`).
2. Once `progress.jsonl` held two lines, the python solver process was
   SIGKILLed during seed 2. job-run recorded `rc=137 cause=KILL`, 15:54.
   At that moment the directory held `run.json`, `summary.json`
   (`seeds_done: 2`), `state.json` (`seed: 1`) and two progress lines.
3. The identical command under `job-run --name qqrr-tie-killresume-626-resume`
   exited 0 at 15:56.

**After the resume**, read from the files:

| file | content |
|---|---|
| `progress.jsonl` | seeds 0, 1, 2, 3 once each, all `empty` / `timeout` (seeds 0 and 1 not repeated) |
| `summary.json` | 4 seeds, 0 examples, 4 empty |
| `state.json` | `seed: 3`, `found: []` |
| `run.json` | argv and config as launched, sha `bcc6021`; the resume kept the first run's record |
| `examples.jsonl` | empty |
| `renders/` | absent: the finder has no render hook |

**What this does not cover.** No grid was found, so a resume that has to
rebuild the dedupe set, reload a non-empty `found` state, or repair a render
was not exercised by this real run; `test_spec_483_e2e.py` and
`test_hunt_resume.py` cover those on toy finders. Every seed timed out, so
nothing here says whether the model is right (see
`2026-09-27-qqrr-tie-pilot.md`).

**Preflight** (`docs/agents/grid-finder-lessons.md`): this run is a protocol
lifecycle check, not a search. It claims no bound, draws on no corpus and
samples no space (questions 1-3, 6 do not apply); the control for a resume
artefact (5) is the uninterrupted toy reference in `test_spec_483_e2e.py`.
Decision log: 4 seeds at a 60 s cap because the kill needs a solve still
running (a seed's cost is its cap), and 1 worker per `AGENTS.md`.

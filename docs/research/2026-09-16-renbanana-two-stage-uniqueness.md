# Renbanana uniqueness in two stages: first bounded run (#402)

**Result: NOT PROVED at the 20-minute cap.** Stage 1 handed out 928 shadings
compatible with the 12 circles of `candidates-fully-circled/cand_00.json`;
stage 2 found no digit fill on any of them, so the true solution's shading
had not yet come up. No second solution was found either.

## The run

- Tool: `finders/renbanana/tools/prove_two_stage.py` at ec8035d (the round-1
  fixes in e260433 do not change the model or the verdict logic).
- Circles: the 12 cells of `cand_00` whose digit equals their group size —
  `r1c6,r1c9,r2c6,r2c7,r2c8,r3c7,r4c6,r5c8,r6c4,r6c7,r9c3,r9c6`.
- `--seconds 1150 --workers 1`, under `job-run --name prove-two-stage-402`
  and `timeout 1200`. Controller-bounded probe: one run, not repeated.
- Wall 1150.1 s. 928 survivors, 0 fills, verdict NOT PROVED.

## Throughput

| elapsed | survivors |
|---|---|
| ~2 min | 55 |
| ~12 min | 526 |
| 19 min | 928 |

About 0.8 survivors per second, so both stages together cost about 1.2 s per
survivor. The split between them was not measured: each survivor is a fresh
stage-1 CP-SAT solve with one more 81-literal cut, plus one digit solve.

## What it means

The split works as designed — digits are cheap and every survivor is decided —
but constraining only the circle *sizes* (the settled fallback) leaves stage 1
far too loose for this circle set: hundreds of shadings pass that carry no
fill. The survivor count is unbounded as measured; it does not say how many
remain. #401's shared size encoding alone did not fix the joint 12-circle
solve (#497), and this run says the same of the size-only relaxation. The
lever left is a tighter stage 1 that stays a relaxation — more digit facts
stateable on the shading, as the fives lemma and the catalogue circle cells
already are — or a cheaper per-survivor step than re-solving from scratch.

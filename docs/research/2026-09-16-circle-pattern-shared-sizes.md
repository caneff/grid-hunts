# probe_circle_pattern: shared group sizes (#401)

`finders/renbanana/tools/probe_circle_pattern.py` now computes every cell's
group size once — chocolate as row run × column run from maximal-interval
indicators, banana as the count under its canonical label — so a circle is one
`d == size` constraint and adds no variables. The old encoding added about 530
variables per circle (6332 for 12 circles).

## Guard

`test_probe_circle_pattern_accepts_known_grids.py` pins each of the 217 known
grids under `docs/research/renbanana/candidates*/`, with every cell that reads
its own group size circled, and requires FEASIBLE. It passed on the old
encoding and on the new one (about 3 minutes, one worker). It only guards
against rejecting a valid grid; a wrong UNIQUE from a model that is too loose
still rests on the `renbanana_verify` re-check of every emitted solution.

## Measurement

12 circles from `candidates-circle-pattern/cand_091.json`, nothing pinned, one
worker, 300 s cap, new encoding:

    uv run finders/renbanana/tools/probe_circle_pattern.py --cells r1c6,r1c9,r2c4,r2c7,r4c6,r4c3,r5c8,r6c6,r6c9,r7c2,r7c8,r9c2 --seconds 300 --workers 1
    status: UNKNOWN
    wall 300.0s

The box's load average was about 19 on 32 cores during the run. The old
encoding's recorded result for an unpinned 12-circle run was no first solution
in 8 minutes, from a different circle set. Removing the per-circle machinery did
not by itself make an unpinned 12-circle probe solve inside 5 minutes.

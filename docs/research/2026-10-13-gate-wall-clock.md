# The gate's wall clock, and which U-Bahn tests overlap (#18)

Measured 2026-10-13 on the shared box, one suite at a time, one core each
(`tests/all.sh --list`, each suite timed alone). XX
non-lint suites is 564 s; `finders/ubahn/` is 429 s of it.

## Slowest suites

| s | suite |
|---|---|
| 67 | `test_ubahn_fewest_markings.py` |
| 45 | `test_ubahn_hybrid_bananas.py` |
| 38 | `counting_shaded/test_counting_shaded.py` (pytest) |
| 38 | `test_ubahn_hybrid_hunt.py` |
| 37 | `test_ubahn_fewest_markings_e2e.py` |
| 37 | `test_ubahn_battenberg_hunt.py` |
| 36 | `test_ubahn_brute.py` |
| 26 | `renbanana/tools/test_probe_finds_known_grids.py --cover` |
| 23 | `test_ubahn_hybrid_sat_hunt.py` |
| 21 | `test_ubahn_hybrid_sat.py` |

## The overlap reading

Each suite's subprocess calls were timed. A CLI call costs about 0.5 s, most of
it start-up.

- **Trimmed.** `test_ubahn_battenberg_hunt.py` ran 11 `classify` rows per
  engine through the CLI; `test_ubahn_battenberg_sat.py`'s TABLE already runs
  every row, on both engines, in process (count and word). Four rows stay, one
  per word and per flag. `test_ubahn_hybrid_sat_hunt.py` ran 9; the same seven
  circle conditions are in `test_ubahn_hybrid_sat.py`'s table. Five rows stay.
  Gain: about 13 s of the serial sum.
- **Not trimmed, no overlap.**
  - `fewest_markings` (67 s): two full 4x4 enumerations, one per engine, 15 s
    and 19 s. No other suite classifies all 5,456 three-window sets on the
    propagator engine, so the run is its only witness.
  - `fewest_markings_e2e` (37 s): one 35 s `fewest-markings` run with `r2c4`
    circled, every set solved because the circle breaks the reflection. All
    four circles that have a unique set need 3 markings, so no cheaper
    circle exists. Its rerun check repeats `fewest_markings`'s but costs 0.6 s.
  - `hybrid_hunt`, `hybrid_bananas`, `hybrid_sat_hunt`, `number_circles_hunt`:
    each CLI call is a different flag combination or engine.
- **The enumeration is repeated, not a test overlap.** `brute.hybrid_grids(4, 4)`
  (16,372 edge sets judged by `hybrid.py`, 3.4 s; 3.8 s with the blank strip)
  is `@cache`d inside one process and run again by each of about twelve
  suites: about 40 s of the serial sum. Removing it means a shared cache across
  processes, which makes the oracle trust a file instead of the rule reader, or
  a faster `hybrid.why_not_hybrid` (it builds every failure reason per
  candidate). Both change the oracle; neither is a trim.

## CI

The gate step took 15 min 15 s on the push to main of run 38341110336 (one
suite at a time). The gate now runs 4 suites at once in CI (`GATE_JOBS=4`);
the figure after is in `AGENTS.md` § Commands.

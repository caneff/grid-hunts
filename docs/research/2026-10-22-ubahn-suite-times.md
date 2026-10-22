# U-Bahn suite times alone on one core (#77)

Each of the 22 `finders/ubahn/test_*.py` suites run by itself with
`uv run <file>`, one after another, no other job of this ticket running, on the
shared WSL box (1-minute load about 7 at the start). Wall clock in seconds,
all passed. The five slowest moved into `finder_slow` in `tests/all.sh` (run
by `just test-slow`).

Single readings on a shared box: other agents' load moves a suite by up to
about 2x between runs (the #77 review re-timed `brute` at 41 to 89 s), so
the cut between 5th and 6th place is thin (37.7 s against 31.2 s here; the
review's re-runs put `hybrid_sat_hunt` at 35 to 42 s). The order of the top
five matches `2026-10-13-gate-wall-clock.md`.

| # | suite | seconds | now |
|---|---|---|---|
| 1 | `test_ubahn_fewest_markings.py` | 71.1 | moved |
| 2 | `test_ubahn_hybrid_bananas.py` | 47.4 | moved |
| 3 | `test_ubahn_hybrid_hunt.py` | 40.0 | moved |
| 4 | `test_ubahn_fewest_markings_e2e.py` | 37.8 | moved |
| 5 | `test_ubahn_brute.py` | 37.7 | moved |
| 6 | `test_ubahn_battenberg_hunt.py` | 31.2 | stays |
| 7 | `test_ubahn_hybrid_sat.py` | 20.9 | stays |
| 8 | `test_ubahn_hybrid_sat_hunt.py` | 18.7 | stays |
| 9 | `test_ubahn_number_circles_hunt.py` | 17.6 | stays |
| 10 | `test_ubahn_battenberg_sat.py` | 16.4 | stays |
| 11 | `test_ubahn_hybrid_model.py` | 14.9 | stays |
| 12 | `test_ubahn_hybrid_e2e.py` | 13.6 | stays |
| 13 | `test_ubahn_number_circles.py` | 12.9 | stays |
| 14 | `test_ubahn_hybrid_links.py` | 10.7 | stays |
| 15 | `test_ubahn_battenberg_e2e.py` | 7.3 | stays |
| 16 | `test_ubahn_hunt.py` | 6.7 | stays |
| 17 | `test_ubahn_sat.py` | 5.5 | stays |
| 18 | `test_ubahn_hybrid_render.py` | 5.1 | stays |
| 19 | `test_ubahn_measure.py` | 4.9 | stays |
| 20 | `test_penpa.py` | 2.8 | stays |
| 21 | `test_ubahn_time_engines.py` | 1.1 | stays |
| 22 | `test_ubahn_hybrid.py` | 0.0 | stays |

# One entrypoint for the gate. The suites live in one place, tests/all.sh:
# every recipe that runs tests calls it with the group it wants.

# The gate: lint and every finder test but the slow ones, plus the test of the
# runner itself (tests/test_all_sh.py). CI runs it.
[doc("The gate: lint plus every finder test except the slow ones.")]
check: lint test

# ruff (check + format check) on finders/ and tests/, and uv.lock still
# matching pyproject.toml.
[doc("Lint the finders and check uv.lock matches pyproject.toml.")]
lint:
    bash tests/all.sh --group lint

[doc("Auto-fix and format the finders in place.")]
fmt:
    uvx ruff check --fix finders tests
    uvx ruff format finders tests

# Every finders/**/test_*.py, found by glob so a new test needs no edit here,
# and the runner's own test. The counting_shaded pytest suite runs here too.
[doc("Every finder test except the slow ones, found by glob.")]
test:
    bash tests/all.sh --group test

# The slow group: the suites listed in tests/all.sh's finder_slow, run by hand.
[doc("Slow finder tests, by hand.")]
test-slow:
    bash tests/all.sh --group slow

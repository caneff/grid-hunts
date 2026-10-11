# One entrypoint for the gate. The suites live in one place, tests/all.sh:
# every recipe that runs tests calls it with the group it wants.

# The gate: lint and every finder test but the slow ones. CI runs it.
[doc("The gate: lint plus every finder test except the slow ones.")]
check: lint test

# ruff (check + format check) on finders/, and uv.lock still matching
# pyproject.toml.
[doc("Lint the finders and check uv.lock matches pyproject.toml.")]
lint:
    bash tests/all.sh --group lint

[doc("Auto-fix and format the finders in place.")]
fmt:
    uvx ruff check --fix finders
    uvx ruff format finders

# Every finders/**/test_*.py, found by glob so a new test needs no edit here.
# The counting_shaded pytest suite runs here too.
[doc("Every finder test except the slow ones, found by glob.")]
test:
    bash tests/all.sh --group test

# The renbanana tests the gate runs as a subset (--cover) in full, plus the
# slow two-stage proof: a CP-SAT solve per known grid, minutes overall. Run by
# hand after touching probe_inverted.py, probe_circle_pattern.py or
# prove_two_stage.py.
[doc("Slow finder tests (a CP-SAT solve per known grid), by hand, minutes overall.")]
test-slow:
    bash tests/all.sh --group slow

[doc("The gate: lint plus every finder test except the slow ones.")]
check: lint test

[doc("Lint the finders and check uv.lock matches pyproject.toml.")]
lint:
    bash tests/all.sh --group lint

[doc("Auto-fix and format the finders in place.")]
fmt:
    uvx ruff check --fix finders tests
    uvx ruff format finders tests

[doc("Every finder test except the slow ones, found by glob.")]
test:
    bash tests/all.sh --group test

[doc("Slow finder tests, by hand.")]
test-slow:
    bash tests/all.sh --group slow

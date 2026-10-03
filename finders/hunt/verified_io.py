"""Reader of verified.jsonl for the `hunt verify` test suites (#517)."""

import json


def read_verified(path):
    """(stamp, verdicts): verified.jsonl's first line is the stamp
    {"verified_examples": N} (#517), every later line one verdict."""
    lines = [json.loads(line) for line in path.read_text().splitlines() if line]
    return lines[0], lines[1:]

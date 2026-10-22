"""verified.jsonl, the file `hunt verify DIR` writes (#489, #517): its
reader for the test suites, and each example's verdict for a hunt's
`summary`."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from driver import _parse_args as driver_args


def read_verified(path):
    """(stamp, verdicts): verified.jsonl's first line is the stamp
    {"verified_examples": N} (#517), every later line one verdict."""
    lines = [json.loads(line) for line in path.read_text().splitlines() if line]
    return lines[0], lines[1:]


def example_verdicts(out, run_argv, examples):
    """Per example, "hit" (passed `verify`), "unchecked", or the reason
    `hunt.py verify` rejected it. verified.jsonl, when there is one, is the
    verdict, whether or not the hunt verified as it ran: a later `verify`
    that rejects an example overrules the hunt's own. With none, a hunt
    without `--no-verify` wrote only examples that passed `verify`. Raises
    when verified.jsonl does not cover exactly this examples.jsonl."""
    path = out / "verified.jsonl"
    if not path.exists():
        hit = not driver_args(run_argv).no_verify
        return ["hit" if hit else "unchecked"] * len(examples)
    stamp, verdicts = read_verified(path)
    if stamp["verified_examples"] != len(examples):
        raise ValueError(
            f"{path} covers {stamp['verified_examples']} examples and "
            f"examples.jsonl holds {len(examples)}: run `hunt.py verify {out}` again"
        )
    by_record = {
        json.dumps(v["record"], sort_keys=True): (
            "hit" if v["ok"] else v.get("reason", "no reason given")
        )
        for v in verdicts
    }
    found = []
    for record in examples:
        verdict = by_record.get(json.dumps(record, sort_keys=True))
        if verdict is None:
            raise ValueError(
                f"{path} has no verdict for an example of examples.jsonl: "
                f"run `hunt.py verify {out}` again"
            )
        found.append(verdict)
    return found

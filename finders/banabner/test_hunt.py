"""A short Banabner hunt through the `hunt` CLI, black-box (#761).

Runs `banabner_finder.py` as a subprocess on one seed and checks what a caller
of the CLI sees: exit 0, at least one grid in examples.jsonl, and every
recorded grid passing `renbanana_verify.check` at difference 4 with the
nabner rule -- read from the record, not from the finder's own verdict.

    uv run finders/banabner/test_hunt.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hunt"))
import banabner_finder as bf
from subprocess_env import pin_idle_load, success_env

pin_idle_load()

SEED = "0:1"
TIMEOUT = "600"  # seconds for the one solve; seed 0 finds its grid well inside it
FAIL = []


def check(name, ok, detail=""):
    print(f"{'ok  ' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        FAIL.append(name)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "hunt"
        result = subprocess.run(
            [
                sys.executable,
                str(HERE / "banabner_finder.py"),
                "--out",
                str(out),
                "--seeds",
                SEED,
                "--workers",
                "1",
                "--timeout",
                TIMEOUT,
            ],
            capture_output=True,
            text=True,
            env=success_env(),
        )
        check("the hunt exits 0", result.returncode == 0, result.stderr[-500:])
        path = out / "examples.jsonl"
        lines = path.read_text().splitlines() if path.exists() else []
        records = [json.loads(line) for line in lines if line]
        check("the hunt records at least one grid", len(records) >= 1)
        for i, rec in enumerate(records):
            bad = bf.check(bf.Candidate(tuple(rec["grid"]), tuple(rec["shading"])))
            check(f"recorded grid {i} passes check", not bad, bad[0] if bad else "")

    print(f"\n{len(FAIL)} failing" if FAIL else "\nall checks pass")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

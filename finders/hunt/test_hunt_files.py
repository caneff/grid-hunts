"""hunt_files owns every file a hunt writes (spec #115): the lock, the
append-only logs and their torn-tail read, the atomic writes, the swap of a
directory, the paired example read and `run_log`. Each case goes through the
module's interface, not a whole hunt.

    uv run finders/hunt/test_hunt_files.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contextlib

import hunt_files
from cli_checks import check, finish

BAD = "(a bad line)"


def refused(call, *needles):
    """True when `call` raises HuntFileError whose text holds every needle."""
    try:
        call()
    except hunt_files.HuntFileError as error:
        return all(n in str(error) for n in needles)
    return False


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)

    # lock
    held = root / "locked"
    first = hunt_files.acquire_lock(held)
    check("the first holder gets the lock", first is not None)
    check("a second holder is refused", hunt_files.acquire_lock(held) is None)
    hunt_files.release_lock(first)
    again = hunt_files.acquire_lock(held)
    check("a released lock can be taken again", again is not None)
    hunt_files.release_lock(again)

    # log: append, read, torn tail, bad middle
    log = root / "log.jsonl"
    with hunt_files.open_log(log) as append:
        append({"a": 1})
        append({"a": 2})
    check(
        "lines appended are read back",
        hunt_files.read_log(log)[1] == [{"a": 1}, {"a": 2}],
    )
    with log.open("a") as f:
        f.write('{"a": 3, "b"')
    lines, records = hunt_files.read_log(log)
    check("a torn last line is dropped", records == [{"a": 1}, {"a": 2}])
    check("the raw lines keep their newline", lines == ['{"a": 1}\n', '{"a": 2}\n'])
    check(
        "a torn last line is not rewritten by a read",
        log.read_text().endswith('"b"'),
    )
    hunt_files.rewrite_log(log, lines)
    with hunt_files.open_log(log) as append:
        append({"a": 4})
    check(
        "rewrite_log keeps the lines a read kept, and an append follows whole",
        hunt_files.read_log(log)[1] == [{"a": 1}, {"a": 2}, {"a": 4}],
    )
    log.write_text('{"a": 1}\n' + BAD + '\n{"a": 3}\n')
    check(
        "an unreadable line that is not the last is refused by file and line",
        refused(lambda: hunt_files.read_log(log), "log.jsonl", "line 2"),
    )
    check(
        "a missing log is refused by name",
        refused(lambda: hunt_files.read_log(root / "no.jsonl"), "no.jsonl"),
    )
    check(
        "a missing log can read empty",
        hunt_files.read_log(root / "no.jsonl", missing_ok=True) == ([], []),
    )
    log.write_text('{"a": 1}\n\n{"a": 2}')
    check(
        "blank lines and a last line with no newline are kept",
        hunt_files.read_log(log)[1] == [{"a": 1}, {"a": 2}],
    )

    # atomic writes
    target = root / "out.json"
    hunt_files.write_json_atomic(target, {"x": 1})
    check("write_json_atomic writes", json.loads(target.read_text()) == {"x": 1})

    class Unserialisable:
        pass

    with contextlib.suppress(TypeError):
        hunt_files.write_json_atomic(target, {"x": Unserialisable()})
    check(
        "a failed JSON write leaves the old file",
        json.loads(target.read_text()) == {"x": 1},
    )
    check(
        "a failed JSON write leaves no temp file",
        sorted(p.name for p in root.glob("out.json*")) == ["out.json"],
    )

    class BadImage:
        def save(self, path, format=None):
            Path(path).write_bytes(b"half")
            raise OSError("disk full")

    png = root / "pic.png"
    png.write_bytes(b"old")
    with contextlib.suppress(OSError):
        hunt_files.write_image_atomic(png, BadImage())
    check("a failed image save leaves the old file", png.read_bytes() == b"old")
    check(
        "a failed image save leaves no temp file",
        sorted(p.name for p in root.glob("pic*")) == ["pic.png"],
    )

    from PIL import Image

    hunt_files.write_image_atomic(png, Image.new("RGB", (2, 2)))
    check("write_image_atomic writes a PNG", png.read_bytes()[:4] == b"\x89PNG")
    hunt_files.write_text_atomic(root / "t.txt", "hi\n")
    check("write_text_atomic writes", (root / "t.txt").read_text() == "hi\n")

    # swap_dir
    swapped = root / "set"
    hunt_files.swap_dir(swapped, lambda d: (d / "1.txt").write_text("one"))
    hunt_files.swap_dir(swapped, lambda d: (d / "2.txt").write_text("two"))
    check(
        "swap_dir replaces the whole set",
        sorted(p.name for p in swapped.iterdir()) == ["2.txt"],
    )

    def fails(d):
        (d / "3.txt").write_text("three")
        raise OSError("boom")

    with contextlib.suppress(OSError):
        hunt_files.swap_dir(swapped, fails)
    check(
        "a failed swap leaves the old set",
        sorted(p.name for p in swapped.iterdir()) == ["2.txt"],
    )
    check(
        "a failed swap leaves no scratch directory",
        sorted(p.name for p in root.glob("set*")) == ["set"],
    )
    (root / "set.tmp").mkdir()
    (root / "set.old").mkdir()
    hunt_files.swap_dir(swapped, lambda d: None)
    check(
        "a swap sweeps the scratch a kill left",
        sorted(p.name for p in root.glob("set*")) == ["set"],
    )

    # paired examples
    hunt = root / "hunt"
    hunt.mkdir()
    with (
        hunt_files.open_log(hunt / "examples.jsonl") as ex,
        hunt_files.open_log(hunt / "progress.jsonl") as pr,
    ):
        ex({"g": "a"})
        pr({"event": "seed_done", "seed": 3, "outcome": "example"})
        pr({"event": "seed_done", "seed": 4, "outcome": "empty"})
        ex({"g": "b"})
        pr({"event": "seed_done", "seed": 5, "outcome": "example"})
    check(
        "examples pair with their example events",
        hunt_files.read_examples(hunt) == [(3, {"g": "a"}), (5, {"g": "b"})],
    )
    with (hunt / "examples.jsonl").open("a") as f:
        f.write('{"g": "c"')
    check(
        "a torn last example line is dropped", len(hunt_files.read_examples(hunt)) == 2
    )
    with (hunt / "progress.jsonl").open("a") as f:
        f.write('{"event": "seed_done", "seed": 6, "outcome": "example"}\n')
        f.write('{"event": "seed_done", "seed": 7, "outcome": "emp')
    check(
        "an example event with no example line is not confirmed, as a resume reruns it",
        hunt_files.read_examples(hunt) == [(3, {"g": "a"}), (5, {"g": "b"})],
    )
    events, examples = hunt_files.read_logs(hunt)
    check(
        "read_logs trims the same way",
        [e["seed"] for e in events] == [3, 4, 5] and len(examples) == 2,
    )
    check(
        "a directory with no examples.jsonl is refused",
        refused(
            lambda: hunt_files.read_examples(root),
            "examples.jsonl",
            "not a hunt directory",
        ),
    )
    hunt_files.rewrite_log(
        hunt / "examples.jsonl", hunt_files.read_log(hunt / "examples.jsonl")[0]
    )
    with hunt_files.open_log(hunt / "examples.jsonl") as ex:
        ex({"g": "d"})
        ex({"g": "e"})
    check(
        "an example past the last event is dropped, the event before it now paired",
        hunt_files.read_examples(hunt)[-1] == (6, {"g": "d"})
        and len(hunt_files.read_examples(hunt)) == 3,
    )

    # run_log
    path = root / "runs" / "sets.jsonl"
    config = {"side": 9, "limit": 5}
    with hunt_files.run_log(path, config) as run:
        check("a new run log holds no lines", run.lines == [])
        run.append({"set": 1})
        run.append({"set": 2})
        try:
            hunt_files.run_log(path, config).__enter__()
            second = "entered"
        except hunt_files.LockHeld:
            second = "refused"
        check("run_log refuses a second holder of the lock", second == "refused")
    with hunt_files.run_log(path, config) as run:
        check(
            "run_log resumes the lines already written",
            run.lines == [{"set": 1}, {"set": 2}],
        )
        run.append({"set": 3})
    with path.open("a") as f:
        f.write('{"set": 4')
    with hunt_files.run_log(path, config) as run:
        check(
            "run_log drops a torn last line",
            run.lines == [{"set": 1}, {"set": 2}, {"set": 3}],
        )
        run.append({"set": 5})
    with hunt_files.run_log(path, config) as run:
        check(
            "a line appended after a torn one is whole",
            run.lines[-1] == {"set": 5} and len(run.lines) == 4,
        )

    def other_config():
        with hunt_files.run_log(path, {"side": 7, "limit": 5}):
            pass

    check(
        "run_log refuses a log written under another config",
        refused(other_config, "sets.jsonl", "config"),
    )
    check(
        "a refused open leaves the log as it was",
        len(hunt_files.read_log(path)[1]) == 5,
    )
    other = root / "other.jsonl"
    other.write_text('{"set": 1}\n')
    check(
        "run_log refuses a log with no config line",
        refused(
            lambda: hunt_files.run_log(other, config).__enter__(),
            "other.jsonl",
            "config",
        ),
    )
    with hunt_files.run_log(path, config):
        pass
    with hunt_files.run_log(path, config):
        pass
    check("a refused open released the lock", True)

finish()

"""Every file a hunt writes, and every read of one (spec #115).

A hunt directory holds append-only JSONL logs (`examples.jsonl`,
`progress.jsonl`), JSON files written whole (`run.json`, `summary.json`,
`state.json`), pictures and a lock. This module owns them all so a hunt killed
halfway reads the same way for the driver's resume, `summary DIR`, `links DIR`
and `verify DIR`.

- `acquire_lock` / `release_lock`: one non-blocking `flock` on `DIR/.lock`.
- `open_log`, `read_log`, `rewrite_log`: a kill can only leave the last line of
  a log half-written, so a read drops an unreadable last line and refuses any
  other unreadable line, naming the file and the line.
- `read_logs`, `read_examples`: the progress events and examples as a resume
  reads them, the k-th "example" event paired with the k-th example.
- `write_text_atomic`, `write_json_atomic`, `write_image_atomic`: write a
  temp file and rename it over the target; a failure leaves the old file and
  removes the temp file.
- `swap_dir`: write a whole directory beside the target, then swap it in.
- `run_log(path, config)`: a locked JSONL log for any search, keyed by the
  config it was started with, that resumes where a kill stopped.
"""

import contextlib
import fcntl
import json
import os
import shutil
from pathlib import Path

LOCK_NAME = ".lock"
CONFIG_KEY = "run_config"


class HuntFileError(ValueError):
    """A hunt file that cannot be read as it stands; the text names it. A
    ValueError so `summary_command` and the finders' CLIs report it as a
    refusal."""


class LockHeld(HuntFileError):
    """Another process holds the lock."""


def acquire_lock(out, name=LOCK_NAME):
    """Take an exclusive, non-blocking `flock` on `out/<name>`, creating `out`.
    Returns the lock's fd, or None when another process holds it. The lock
    belongs to the open fd, so a killed holder releases it at once."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    fd = os.open(out / name, os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def release_lock(fd):
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


def read_log(path, missing_ok=False):
    """`(lines, records)` of the JSONL log at `path`: each line with its
    newline, and the parsed object. A last line that does not parse is a
    kill's half-written write and is dropped; any other line that does not
    parse raises HuntFileError naming the file and the line. A missing file
    raises it too, unless `missing_ok`, which reads it as empty."""
    path = Path(path)
    if not path.is_file():
        if missing_ok:
            return [], []
        raise HuntFileError(f"{path.parent} has no {path.name}: not a hunt directory")
    numbered = [
        (number, line)
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if line.strip()
    ]
    lines, records = [], []
    for k, (number, line) in enumerate(numbered):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            if k == len(numbered) - 1:
                break
            raise HuntFileError(
                f"{path} line {number} does not read ({error}); only a last "
                "line cut short by a kill is dropped"
            ) from error
        lines.append(line + "\n")
    return lines, records


def rewrite_log(path, lines):
    """Replace the log at `path` with `lines` (as `read_log` returns them)."""
    write_text_atomic(Path(path), "".join(lines))


@contextlib.contextmanager
def open_log(path):
    """Append to the JSONL log at `path`: yields `append(obj)`, which writes
    one line and flushes it. The file must end in a whole line, which a resume
    ensures with `rewrite_log` first."""
    with Path(path).open("a") as f:

        def append(obj):
            f.write(json.dumps(obj) + "\n")
            f.flush()

        yield append


def _confirmed(events):
    return sum(1 for e in events if e.get("outcome") == "example")


def read_logs(out, stateful=False):
    """`(events, examples)` of the hunt in `out` as a resume reads them: the
    progress events and the example records, torn tails dropped. A kill leaves
    at most the last events ahead of examples.jsonl, and those seeds rerun, so
    trailing events whose example line is missing are dropped; an example line
    past the last "example" event is dropped too, since no event confirms it.
    A stateful finder's resume also reruns every seed past the one state.json
    last saved (all of them when it has not saved yet), so those events are
    dropped too. A state.json marks the hunt stateful; `stateful=True` covers
    a kill before the first save, when there is none yet."""
    out = Path(out)
    _, examples = read_log(out / "examples.jsonl")
    _, events = read_log(out / "progress.jsonl")
    state_path = out / "state.json"
    stateful = stateful or state_path.exists()
    state_seed = read_json(state_path).get("seed") if state_path.exists() else None
    while events and (
        _confirmed(events) > len(examples)
        # A missing "seed" reads as ahead of any state, as the resume does.
        or (
            stateful
            and (
                state_seed is None or events[-1].get("seed", float("inf")) > state_seed
            )
        )
    ):
        events.pop()
    return events, examples[: _confirmed(events)]


def read_examples(out, stateful=False):
    """`[(seed, record)]` for every example of the hunt in `out` (`read_logs`,
    which `stateful` is passed to), the k-th "example" event paired with the
    k-th record. Raises HuntFileError, naming the file, on a missing log."""
    events, examples = read_logs(out, stateful=stateful)
    seeds = [e["seed"] for e in events if e.get("outcome") == "example"]
    return list(zip(seeds, examples, strict=True))


def read_json(path):
    """The JSON file at `path`; HuntFileError names it when it is missing or
    does not read."""
    path = Path(path)
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as error:
        raise HuntFileError(f"{path.parent} has no {path.name}") from error
    except json.JSONDecodeError as error:
        raise HuntFileError(f"{path} does not read ({error})") from error


def _write_atomic(path, write):
    """`write(temp_path)` then rename it over `path`; a failure removes the
    temp file and leaves `path` as it was."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    try:
        write(tmp)
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def write_text_atomic(path, text):
    _write_atomic(path, lambda tmp: tmp.write_text(text))


def write_json_atomic(path, data):
    write_text_atomic(path, json.dumps(data))


def write_image_atomic(path, image):
    """Save the PIL `image` to `path` as a PNG, whatever its suffix."""
    _write_atomic(path, lambda tmp: image.save(tmp, format="PNG"))


def swap_dir(target, write):
    """Replace the directory `target` with the one `write(directory)` fills.
    It is filled beside `target` first, then swapped in by two renames: the old
    directory moves to `<target>.old`, the new one to `target`. A kill before
    the first rename leaves the old set, after the second the new one, and
    between them neither (the old set sits in `<target>.old`); a rerun
    converges, sweeping the scratch a kill left, so the old set is then gone
    and the rerun writes the whole new one. A failure in `write` removes the
    new directory and leaves `target` as it was; a failed removal of the
    scratch raises."""
    target = Path(target)
    new = target.with_name(target.name + ".tmp")
    old = target.with_name(target.name + ".old")
    for scratch in (new, old):
        if scratch.exists():
            shutil.rmtree(scratch)
    new.mkdir(parents=True)
    try:
        write(new)
        if target.exists():
            target.rename(old)
        new.rename(target)
    finally:
        shutil.rmtree(new, ignore_errors=True)
    if old.exists():
        shutil.rmtree(old)


class RunLog:
    """A locked, resumable JSONL log keyed by a run config. Entering takes
    the lock (LockHeld when another process holds it), reads the log, drops a
    torn last line, and refuses a log written under another config; `lines`
    then holds the lines already written and `append(obj)` adds one."""

    def __init__(self, path, config):
        self.path = Path(path)
        self.config = json.loads(json.dumps(config))
        self.lines = []
        self._fd = None
        self._file = None

    def __enter__(self):
        fd = acquire_lock(self.path.parent, self.path.name + ".lock")
        if fd is None:
            raise LockHeld(f"{self.path} is locked: another run is using it")
        try:
            self._start()
        except BaseException:
            release_lock(fd)
            raise
        self._fd = fd
        return self

    def _start(self):
        header = {CONFIG_KEY: self.config}
        raw, records = read_log(self.path, missing_ok=True)
        if records and records[0] != header:
            found = records[0].get(CONFIG_KEY) if isinstance(records[0], dict) else None
            if found is None:
                raise HuntFileError(
                    f"{self.path} has no config line first: not a run log"
                )
            raise HuntFileError(
                f"{self.path} was written under another config "
                f"({found!r} vs {self.config!r}); use a new log"
            )
        if not records:
            raw = [json.dumps(header) + "\n"]
        rewrite_log(self.path, raw)
        self.lines = records[1:]
        self._file = self.path.open("a")

    def append(self, obj):
        self._file.write(json.dumps(obj) + "\n")
        self._file.flush()
        self.lines.append(obj)

    def __exit__(self, *exc):
        self._file.close()
        release_lock(self._fd)
        return False


def run_log(path, config):
    """`with run_log(path, config) as log:` -- see `RunLog`."""
    return RunLog(path, config)

"""Shared subprocess env for the hunt CLI test suites (#526).

The load gate (#488) refuses above a 1-minute load of 24 unless
`HUNT_FAKE_LOAD1` overrides it; a success-directed subprocess test uses
`success_env` so a busy box cannot fail it. A test file that runs hunts
in-process, or launches one with no `env=`, calls `pin_idle_load` once at
import (#669). An override of `None` deletes the key."""

import os

IDLE_LOAD = "0"


def success_env(overrides=None):
    """`os.environ` with the load gate pinned idle, then `overrides` applied."""
    env = {**os.environ, "HUNT_FAKE_LOAD1": IDLE_LOAD}
    for key, value in (overrides or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


def pin_idle_load():
    """Pin the load gate idle for this process and every child it starts."""
    os.environ["HUNT_FAKE_LOAD1"] = IDLE_LOAD

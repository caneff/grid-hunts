"""The edges a narrowed run selects by, checked against the real tree.

`tests/all.sh --changed` runs a suite when Pants lists its file among the
dependents of a changed file, so an edge Pants does not see is a suite a
narrowed run skips in silence. This asks Pants for the whole graph once
(`pants dependencies --format=json finders::`) and checks four things:

- every suite file of the gate is owned by a Pants target, so Pants can list it;
- no import is ambiguous: Pants drops an import two targets could own;
- every `.py` file a finder source names in a string (the script a test starts
  as a subprocess, a file it reads) is a dependency of that source, at any
  distance. A name resolves to the source's sibling, else to every file of
  that name in the same finder folder; a name no file has (a temp script the
  test writes) is skipped;
- the known edges below: files whose change must select some suites and must
  not select others.

    uv run tests/test_pants_edges.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (file, why it is read, suites its change must select, suites it must not)
KNOWN_EDGES = [
    (
        "finders/hunt/verified_io.py",
        "the shared hunt layer: ubahn's finder imports it, and halver_lockout's "
        "hunt through finders/halver/halver_hunt.py",
        [
            "finders/ubahn/test_ubahn_hunt.py",
            "finders/halver_lockout/test_spec_52_e2e.py",
        ],
        ["finders/hunt/test_grid.py", "finders/qqrr/test_model.py"],
    ),
    (
        "finders/halver/halver_brute.c",
        "the shared halver layer's C source, data of finders/halver",
        [
            "finders/halver_between/test_brute.py",
            "finders/halver_lockout/test_brute.py",
        ],
        ["finders/ubahn/test_ubahn_brute.py"],
    ),
    (
        "finders/ubahn/fixtures/publ-knt.txt",
        "a finder's fixture is data of every Python file in its folder",
        ["finders/ubahn/test_penpa.py"],
        ["finders/hunt/test_grid.py"],
    ),
    (
        "finders/hunt/toy_finder.py",
        "test_toy_hunt.py starts it as a subprocess, which no import shows",
        ["finders/hunt/test_toy_hunt.py"],
        ["finders/hunt/test_grid.py"],
    ),
    (
        "finders/hunt/render.py",
        "ubahn imports `render` through finders/hunt on its sys.path, not "
        "counting_shaded's module of the same name",
        ["finders/ubahn/test_ubahn_hybrid_render.py"],
        ["finders/counting_shaded/test_counting_shaded.py"],
    ),
]

PY_NAME = re.compile(r"""["']([\w./-]*\w\.py)["']""")

ok = True


def check(name, cond):
    global ok
    print(f"{'ok' if cond else 'FAIL'}: {name}")
    ok = ok and cond


def graph():
    """{address: [direct dependency addresses]} for every target under finders/,
    and what Pants printed on stderr."""
    with tempfile.TemporaryDirectory() as work:
        r = subprocess.run(
            ["pants", "dependencies", "--format=json", "finders::"],
            capture_output=True,
            text=True,
            cwd=REPO,
            stdin=subprocess.DEVNULL,
            env={**os.environ, "PANTS_WORKDIR": work},
        )
    if r.returncode != 0:
        sys.exit(f"pants dependencies failed:\n{r.stderr}")
    return json.loads(r.stdout), r.stderr


def owner(deps, file):
    """The address of the target that owns `file`'s Python, or None."""
    return next((a for a in deps if a.split(":")[0] == file), None)


def closure(deps, start):
    seen, todo = set(), [start]
    while todo:
        a = todo.pop()
        if a not in seen:
            seen.add(a)
            todo.extend(deps.get(a, []))
    return {a.split(":")[0] for a in seen}


def tracked(*patterns):
    out = subprocess.run(
        ["git", "ls-files", *patterns], capture_output=True, text=True, cwd=REPO
    )
    return out.stdout.split()


def finder_folder(path):
    return "/".join(path.split("/")[:2])


if __name__ == "__main__":
    deps, stderr = graph()

    listing = subprocess.run(
        ["bash", "tests/all.sh", "--list"], capture_output=True, text=True, cwd=REPO
    ).stdout.splitlines()
    suite_files = [
        w for line in listing for w in line.split() if w.startswith("finders/")
    ]
    unowned = [f for f in suite_files if owner(deps, f) is None]
    check(
        f"every one of the gate's {len(suite_files)} finder suites has a Pants "
        f"target (a folder with no BUILD file has none): {unowned or 'none missing'}",
        suite_files and not unowned,
    )

    ambiguous = [line for line in stderr.splitlines() if "ambiguous" in line]
    check(
        f"no import is ambiguous to Pants: {ambiguous or 'none'}",
        not ambiguous,
    )

    py_files = tracked("finders/*.py")
    missing = []
    for src in py_files:
        address = owner(deps, src)
        if address is None:
            continue  # the suite check above names an unowned suite
        reach = closure(deps, address)
        here = src.rsplit("/", 1)[0]
        for name in sorted(set(PY_NAME.findall((REPO / src).read_text()))):
            sibling = f"{here}/{name}"
            if sibling in py_files:
                targets = [sibling]
            else:
                targets = [
                    f
                    for f in py_files
                    if finder_folder(f) == finder_folder(src)
                    and (f == name or f.endswith(f"/{name}"))
                ]
            missing += [f"{src} -> {t}" for t in targets if t != src and t not in reach]
    check(
        "every .py file a finder source names in a string is a dependency of "
        f"it (an `edges` entry in its BUILD file): {missing or 'none missing'}",
        not missing,
    )

    for file, why, must, must_not in KNOWN_EDGES:
        selects = {s for s in suite_files if file in closure(deps, owner(deps, s) or s)}
        lost = [s for s in must if s not in selects]
        extra = [s for s in must_not if s in selects]
        check(
            f"a change to {file} selects {must} and not {must_not} ({why}): "
            f"lost {lost or 'none'}, extra {extra or 'none'}",
            not lost and not extra,
        )

    sys.exit(0 if ok else 1)

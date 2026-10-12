"""The Banabner lineup builder on a fixture hunt directory (#763).

    uv run finders/banabner/test_build_lineup.py

The fixture is a hunt's `examples.jsonl` holding the two hand-checked grids
(`known_grid.json`, `known_grid_3x3.json`) and a rotated copy of the first. The
page must list the two distinct grids, with the circles and forced circles the
shading and digits imply. The known grid's circle cells are the controller's
hand-checked list (every cell whose digit equals its own group's size), so the
page is judged against that, not against the builder's own flood fill.
"""

import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_lineup as bl

KNOWN = json.loads((HERE / "known_grid.json").read_text())
SECOND = json.loads((HERE / "known_grid_3x3.json").read_text())
# Cells of KNOWN whose digit equals the size of their own group, by group kind.
KNOWN_CHOC = {(1, 4), (1, 8), (5, 7)}
KNOWN_BANANA = {(1, 6), (2, 2), (2, 4), (4, 7), (7, 6), (8, 1)}
KNOWN_FORCED = {(2, 0), (5, 5)}  # the 5 of each 5-cell banana
FAIL = []


def check(name, ok, detail=""):
    print(f"{'ok  ' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        FAIL.append(name)


def rotated(rec):
    """Rotate a grid a quarter turn: the same puzzle, so one card."""

    def turn(rows):
        return ["".join(rows[8 - c][r] for c in range(9)) for r in range(9)]

    return {"grid": turn(rec["grid"]), "shading": turn(rec["shading"])}


def write_hunt(path, records):
    path.mkdir()
    (path / "examples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))


def data_of(html):
    m = re.search(r"^const DATA=(.*);$", html, re.M)
    return json.loads(m.group(1))


def cells(pairs):
    return {tuple(p) for p in pairs}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        hunt = Path(tmp) / "hunt"
        write_hunt(hunt, [KNOWN, SECOND, rotated(KNOWN)])
        out = Path(tmp) / "lineup.html"
        bl.main([str(out), str(hunt)])
        html = out.read_text()
        data = data_of(html)

        check("the page lists each distinct grid once", len(data) == 2, str(len(data)))
        by = {d["grid"][0]: d for d in data}
        known = by[KNOWN["grid"][0]]
        check("chocolate circles", cells(known["circles"]) == KNOWN_CHOC)
        check("banana circles", cells(known["bcircles"]) == KNOWN_BANANA)
        check("forced circles", cells(known["forced"]) == KNOWN_FORCED)
        check(
            "circle score counts circled groups, forced left out",
            known["value"] == len(KNOWN_CHOC) + len(KNOWN_BANANA),
            str(known["value"]),
        )
        # Chris's ruling (#761): every size circle is drawn, banana groups and
        # 5-cell bananas included. The page draws a class's ring through its
        # ::after rule, and each toggle starts checked.
        for cls in ("c", "bc", "fc"):
            check(f"the .{cls} ring is drawn", f".cell.{cls}::after" in html)
        for box in ("circles", "bcircles", "forced"):
            check(
                f"the {box} toggle starts checked",
                f'<input id="{box}" type="checkbox" checked>' in html,
            )
        check("forced count", known["forcedCircles"] == 2)
        # The page's own record of checked grids: every one listed, best first.
        record = Path(tmp) / "record.html"
        checked = bl.ROOT / "docs/research/banabner/checked-grids"
        bl.main([str(record), str(checked)])
        scores = [d["value"] for d in data_of(record.read_text())]
        n = len((checked / "examples.jsonl").read_text().splitlines())
        check(f"the record's {n} grids all listed", len(scores) == n, str(len(scores)))
        check(
            "listed in circle-score order, best first",
            scores == sorted(scores, reverse=True) and scores[0] > scores[-1],
            str(scores),
        )
        check(
            "the record section is on the page",
            "no chocolate rectangle" in html.lower(),
        )
        check("title", "<title>Banabner Lineup</title>" in html)
        check("rules text names difference 4", "at least 4" in html)
        check("rules text names the nabner rule", "nabner" in html.lower())

        # A grid that breaks a rule is refused, not listed.
        bad = {
            "grid": [KNOWN["grid"][0][:8] + "6", *KNOWN["grid"][1:]],
            "shading": KNOWN["shading"],
        }
        bad_hunt = Path(tmp) / "bad"
        write_hunt(bad_hunt, [bad])
        try:
            bl.main([str(Path(tmp) / "bad.html"), str(bad_hunt)])
            refused = False
        except SystemExit:
            refused = True
        check("an illegal grid is refused", refused)

    print(f"\n{len(FAIL)} failing" if FAIL else "\nall checks pass")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

import json, sys, copy
from sudoku_kit.link_codec import encode_link
d = json.load(open(sys.argv[1]))
p = d["puzzle"]
assert all(c == {} for c in p["cells"]), "template has entered cells"
allc = [t.split("=")[0] for t in sys.argv[2].split()]
circ = [t for t in allc if t[-1] in "LRTB"]
gridc = {tuple(map(int, t[1:].split("c"))) for t in allc if t[-1] not in "LRTB"}
ids = []
for t in circ:
    n, sd = int(t[1]), t[2]
    if t[0] == "r":
        y, x = n, (0 if sd == "L" else 7)
    else:
        y, x = (0 if sd == "T" else 7), n
    ids.append(y * 8 + x)
for r in range(1, 7):
    for c in range(1, 7):
        if (r, c) in gridc:
            ids.append(r * 8 + c)
assert len(ids) == len(allc) == len(set(ids))
keep = []
for c in p["constraints"]:
    if c["type"] in (300, 200, 301): continue
    if c.get("name") == "Skyscrapers": continue
    keep.append(c)
keep.append({"type": 306, "cells": sorted(ids), "style": {"size": 0.75, "fill": "#ffffff00", "stroke": {"thickness": 0.03, "color": "#000000ff"}}})
p["constraints"] = keep
p["name"] = sys.argv[3]
p["comment"] = ("Regions: Divide the grid into four regions of 9 orthogonally connected cells. Each region contains the digits 1–9 once each. "
 "Digits don't repeat in any row or column.\n\n"
 "Numbered Rooms: Every circled outside cell is a Numbered Rooms clue. Let N be the first digit in the row/column, looking in from the clue. "
 "The clue is the Nth digit in that direction. Cells 1 to N in that direction all share one region, and the (N+1)th cell, if it exists, is in a different region.\n\n"
 "Counting circles: Each digit in a circle, inside or outside the grid, is exactly how many circles contain that digit.")
print(encode_link(d))

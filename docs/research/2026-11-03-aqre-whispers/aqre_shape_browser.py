"""SCRATCH: build a browsable page of every free 9-cell shape and what each circle cell can be.

usage: aqre_shape_browser.py DIR OUT_HTML

Reads free-circle-classes.pickle, widens each free pair to every equal cell, and adds the shape-alone top from
`aqre_top_six_shapes.holds`. Refuses to write unless the totals match the earlier runs.
"""

import json
import os
import pickle
import sys
from collections import Counter
from pathlib import Path

from aqre_r5_region_max import lines_of
from aqre_top_six_picture import pair_key
from aqre_top_six_shapes import holds

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aqre Region Shapes</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
/* Layout: a filter strip of real counts over a shape gallery, with a sticky inspector for one shape and circle cell. */
:root {
  --paper: #f3f5f7;
  --panel: #ffffff;
  --ink: #17202b;
  --muted: #566373;
  --rule: #d4dae1;
  --cell: #e3eaf3;
  --accent: #1f4fa8;
  --accent-soft: #d6e2f7;
  --display: "Archivo", "Helvetica Neue", Arial, sans-serif;
  --body: "IBM Plex Sans", "Segoe UI", Arial, sans-serif;
  --mono: "IBM Plex Mono", Consolas, monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #12171e; --panel: #1b222c; --ink: #e8edf3; --muted: #9daab9; --rule: #333e4b;
    --cell: #2a3543; --accent: #84aef5; --accent-soft: #24375a; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --paper: #12171e; --panel: #1b222c; --ink: #e8edf3; --muted: #9daab9; --rule: #333e4b;
  --cell: #2a3543; --accent: #84aef5; --accent-soft: #24375a; color-scheme: dark;
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--paper); color: var(--ink); font: 400 15px/1.45 var(--body); }
main { max-width: 1400px; margin: 0 auto; padding: 20px 16px 40px; display: grid; gap: 16px; }
h1 { font: 700 26px/1.15 var(--display); margin: 0 0 4px; text-wrap: balance; }
h2 { font: 700 17px/1.2 var(--display); margin: 0; }
p { margin: 0; max-width: 78ch; color: var(--muted); }
.sets { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 8px; }
.set { text-align: left; background: var(--panel); color: var(--ink); border: 1px solid var(--rule); border-radius: 6px; padding: 10px 12px; cursor: pointer; font: inherit; display: grid; gap: 2px; }
.set b { font: 700 22px/1.1 var(--display); font-variant-numeric: tabular-nums; }
.set span { color: var(--muted); font-size: 13px; line-height: 1.3; }
.set[aria-pressed="true"] { border-color: var(--accent); background: var(--accent-soft); box-shadow: inset 0 0 0 1px var(--accent); }
.controls { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; }
.controls label { display: flex; gap: 6px; align-items: center; font-size: 14px; }
select { font: inherit; color: var(--ink); background: var(--panel); border: 1px solid var(--rule); border-radius: 4px; padding: 4px 6px; max-width: 100%; }
#status { color: var(--muted); font-variant-numeric: tabular-nums; font-size: 14px; }
.work { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 16px; align-items: start; }
#gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(92px, 1fr)); gap: 6px; }
.tile { background: var(--panel); border: 1px solid var(--rule); border-radius: 4px; padding: 6px; cursor: pointer; display: grid; gap: 4px; justify-items: center; color: var(--muted); font: 400 11px/1 var(--mono); min-height: 92px; align-content: space-between; }
.tile[aria-pressed="true"] { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
.tile svg { width: 100%; height: 68px; }
.c { fill: var(--cell); stroke: var(--rule); stroke-width: .04; }
.edge { stroke: var(--ink); stroke-width: .09; stroke-linecap: square; }
.dot { fill: var(--accent); }
aside { position: sticky; top: 12px; background: var(--panel); border: 1px solid var(--rule); border-radius: 6px; padding: 14px; display: grid; gap: 12px; max-height: calc(100vh - 24px); overflow: auto; }
#big { width: 100%; max-height: 260px; }
#big .hit { cursor: pointer; fill: transparent; }
#big .hit:hover { fill: var(--accent-soft); opacity: .6; }
#big .hit:focus-visible { outline: none; stroke: var(--accent); stroke-width: .08; }
.ring { fill: none; stroke: var(--ink); stroke-width: .08; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { text-align: left; padding: 4px 6px; border-top: 1px solid var(--rule); vertical-align: top; }
thead th { border-top: 0; color: var(--muted); font-weight: 500; }
tbody th { font-weight: 500; }
td { font-variant-numeric: tabular-nums; }
.pill { display: inline-block; padding: 1px 7px; border-radius: 10px; background: var(--accent-soft); font-weight: 600; font-size: 12px; }
pre { margin: 0; font: 500 14px/1.15 var(--mono); }
.row { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
button.copy { font: inherit; font-size: 13px; color: var(--ink); background: transparent; border: 1px solid var(--rule); border-radius: 4px; padding: 2px 8px; cursor: pointer; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
details { font-size: 14px; color: var(--muted); max-width: 78ch; }
summary { cursor: pointer; color: var(--ink); }
@media (max-width: 860px) { .work { grid-template-columns: 1fr; } aside { position: static; max-height: none; order: -1; } }
</style>
</head>
<body>
<main>
  <header>
    <h1>Aqre Region Shapes</h1>
    <p>Every 9-cell jigsaw region without a hole, with rotations and reflections counted once, and what each circle cell can count. Rules are Aqre shading with 5-whispers on shaded cells, judged on the region alone.</p>
  </header>
  <section class="sets" id="sets" aria-label="Shape sets"></section>
  <div class="controls">
    <label for="mark">Dot the circle cells that</label>
    <select id="mark"></select>
    <label for="box">Size</label>
    <select id="box"></select>
    <span id="status" role="status"></span>
  </div>
  <div class="work">
    <section id="gallery" aria-label="Shapes"></section>
    <aside aria-label="Selected shape">
      <div class="row"><h2 id="title"></h2><button class="copy" id="copy" type="button">Copy shape</button></div>
      <svg id="big" role="img" aria-label="Selected shape. Choose a cell to place the circle there."></svg>
      <p style="font-size:13px">Choose a cell to place the circle there.</p>
      <div id="facts"></div>
      <pre id="text"></pre>
    </aside>
  </div>
  <details>
    <summary>How to read this</summary>
    <p>Shaded cells are low (1-4) on one checkerboard colour and high (6-9) on the other, with at most 4 of each. A 5 is never shaded. Adjacent shaded cells differ by at least 5. No 4 in a line of one colour inside the region. Shading outside the region and other regions are ignored, so "can" is necessary but not sufficient.</p>
    <p>A circle holds its region's shaded count. The "8's colour" is the colour of the forced 8's circle, which is the high colour. A forced 7 means exactly one of shaded 7 and unshaded 7 fits. Refused means both fit, so the colour does not decide it. Tops out at 6 means neither fits and some count from 1 to 6 does.</p>
  </details>
</main>
<script>
const DATA = __DATA__;
const SETS = [
  {id: "seven", n: "Can be 7, not 8", d: "No circle lets it hold 8; it can hold 7 alone", test: s => s.t === 7},
  {id: "circle", n: "Can hold 8, but some cells can't", d: "Dotted circle cells can be 7 but not 8", test: s => s.t === 8 && s.k.some(notEightButSeven)},
  {id: "six", n: "Tops out at 6", d: "At least one circle cell tops out at 6", test: s => s.k.some(c => !c.e && !anySeven(c))},
  {id: "rest", n: "No 7-not-8 cell", d: "Holds 8 alone, and every circle cell is either 8-able or tops out", test: s => s.t === 8 && !s.k.some(notEightButSeven)},
  {id: "all", n: "All shapes", d: "Every shape without a hole", test: () => true},
];
const MARKS = [
  {id: "seven", n: "can be 7 but not 8", test: notEightButSeven},
  {id: "eight", n: "can be the 8", test: c => c.e},
  {id: "six", n: "top out at 6 on either colour", test: c => !c.e && !anySeven(c)},
  {id: "h7", n: "are a forced 7 on the 8's colour", test: c => !c.e && kind(c.h) === "seven"},
  {id: "ht", n: "top out at 6 on the 8's colour", test: c => !c.e && kind(c.h) === "top"},
  {id: "l7", n: "are a forced 7 on the other colour", test: c => !c.e && kind(c.l) === "seven"},
  {id: "lt", n: "top out at 6 on the other colour", test: c => !c.e && kind(c.l) === "top"},
];
function kind(side) { if (side[0] || side[1]) return side[0] !== side[1] ? "seven" : "both"; return side[2].length ? "top" : "none"; }
function anySeven(c) { return c.h[0] || c.h[1] || c.l[0] || c.l[1]; }
function notEightButSeven(c) { return !c.e && anySeven(c); }
const NS = "http://www.w3.org/2000/svg";
const state = {set: "seven", mark: "seven", box: "all", shape: null, cell: 0};
try { const saved = location.hash.slice(1); if (SETS.some(s => s.id === saved)) state.set = saved; } catch (e) {}
const el = id => document.getElementById(id);
function dims(s) { return [Math.max(...s.c.map(x => x[0])) + 1, Math.max(...s.c.map(x => x[1])) + 1]; }
function draw(svg, s, marks, big) {
  const [h, w] = dims(s);
  svg.setAttribute("viewBox", `-0.15 -0.15 ${w + 0.3} ${h + 0.3}`);
  svg.replaceChildren();
  const add = (name, attrs) => { const n = document.createElementNS(NS, name); for (const k in attrs) n.setAttribute(k, attrs[k]); svg.append(n); return n; };
  const on = new Set(s.c.map(x => x[0] + "," + x[1]));
  s.c.forEach(([r, c]) => add("rect", {x: c, y: r, width: 1, height: 1, class: "c"}));
  s.c.forEach(([r, c]) => {
    if (!on.has((r - 1) + "," + c)) add("line", {x1: c, y1: r, x2: c + 1, y2: r, class: "edge"});
    if (!on.has((r + 1) + "," + c)) add("line", {x1: c, y1: r + 1, x2: c + 1, y2: r + 1, class: "edge"});
    if (!on.has(r + "," + (c - 1))) add("line", {x1: c, y1: r, x2: c, y2: r + 1, class: "edge"});
    if (!on.has(r + "," + (c + 1))) add("line", {x1: c + 1, y1: r, x2: c + 1, y2: r + 1, class: "edge"});
  });
  s.c.forEach(([r, c], i) => { if (marks(s.k[i])) add("circle", {cx: c + .5, cy: r + .5, r: big ? .13 : .2, class: "dot"}); });
  if (big) {
    const [r, c] = s.c[state.cell];
    add("circle", {cx: c + .5, cy: r + .5, r: .36, class: "ring"});
    s.c.forEach(([y, x], i) => {
      const hit = add("rect", {x, y, width: 1, height: 1, class: "hit", tabindex: 0, role: "button", "aria-label": `Place circle at row ${y + 1}, column ${x + 1}`});
      const pick = () => { state.cell = i; inspect(); };
      hit.addEventListener("click", pick);
      hit.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
    });
  }
}
function visible() {
  const set = SETS.find(s => s.id === state.set);
  return DATA.filter(s => set.test(s) && (state.box === "all" || dims(s).slice().sort((a, b) => a - b).join("x") === state.box));
}
function renderSets() {
  const box = el("sets");
  box.replaceChildren(...SETS.map(s => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "set"; b.setAttribute("aria-pressed", s.id === state.set);
    const count = DATA.filter(s.test).length;
    b.innerHTML = `<b>${count.toLocaleString()}</b><span><strong>${s.n}</strong><br>${s.d}</span>`;
    b.addEventListener("click", () => { state.set = s.id; try { location.hash = s.id; } catch (e) {} refresh(); });
    return b;
  }));
}
function inspect() {
  const s = state.shape;
  if (!s) { el("title").textContent = "No shape in this view"; el("big").replaceChildren(); el("facts").replaceChildren(); el("text").textContent = ""; return; }
  el("title").textContent = `Shape ${s.i}`;
  const m = MARKS.find(x => x.id === state.mark);
  draw(el("big"), s, m.test, true);
  const c = s.k[state.cell];
  const label = side => ({seven: "Forced 7", both: "Refused", top: "Tops out at 6", none: "No count fits"}[kind(side)]);
  const yes = v => v ? "yes" : "no";
  const counts = side => side[2].length ? side[2].join(", ") : "n/a";
  el("facts").innerHTML = `<p style="margin-bottom:8px">Highest count with no circle: <span class="pill">${s.t}</span>. With the circle here: <span class="pill">${c.e ? "can be the 8" : anySeven(c) ? "can be 7, not 8" : "tops out at 6"}</span></p>` + (c.e
    ? `<p>This region can be the 8, so under your rule only one region in the grid may use this circle cell.</p>`
    : `<table><thead><tr><th></th><th scope="col">On the 8's colour</th><th scope="col">On the other colour</th></tr></thead><tbody>
      <tr><th scope="row">As a non-8 region</th><td>${label(c.h)}</td><td>${label(c.l)}</td></tr>
      <tr><th scope="row">Shaded 7 fits</th><td>${yes(c.h[0])}</td><td>${yes(c.l[0])}</td></tr>
      <tr><th scope="row">Unshaded 7 fits</th><td>${yes(c.h[1])}</td><td>${yes(c.l[1])}</td></tr>
      <tr><th scope="row">Counts that fit</th><td>${counts(c.h)}</td><td>${counts(c.l)}</td></tr></tbody></table>`);
  const [h, w] = dims(s);
  const lines = [];
  for (let r = 0; r < h; r++) { let t = ""; for (let q = 0; q < w; q++) { const i = s.c.findIndex(x => x[0] === r && x[1] === q); t += i < 0 ? "." : i === state.cell ? "O" : "X"; } lines.push(t); }
  el("text").textContent = lines.join("\n");
}
function refresh() {
  renderSets();
  const list = visible();
  const m = MARKS.find(x => x.id === state.mark);
  if (!list.includes(state.shape)) { state.shape = list[0] || null; state.cell = 0; }
  const dots = list.reduce((n, s) => n + s.k.filter(m.test).length, 0);
  el("status").textContent = `${list.length.toLocaleString()} shapes, ${dots.toLocaleString()} dots`;
  const frag = document.createDocumentFragment();
  list.forEach(s => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "tile"; b.setAttribute("aria-pressed", s === state.shape); b.setAttribute("aria-label", `Shape ${s.i}`);
    const svg = document.createElementNS(NS, "svg");
    draw(svg, s, m.test, false);
    b.append(svg);
    const n = document.createElement("span"); n.textContent = s.i; b.append(n);
    b.addEventListener("click", () => { state.shape = s; state.cell = 0; document.querySelectorAll(".tile").forEach(t => t.setAttribute("aria-pressed", t === b)); inspect(); });
    frag.append(b);
  });
  el("gallery").replaceChildren(frag);
  inspect();
}
el("mark").innerHTML = MARKS.map(m => `<option value="${m.id}">${m.n}</option>`).join("");
const boxes = [...new Set(DATA.map(s => dims(s).slice().sort((a, b) => a - b).join("x")))].sort((a, b) => a.split("x")[0] - b.split("x")[0] || a.split("x")[1] - b.split("x")[1]);
el("box").innerHTML = `<option value="all">Any size</option>` + boxes.map(b => `<option value="${b}">${b}</option>`).join("");
el("mark").addEventListener("change", e => { state.mark = e.target.value; refresh(); });
el("box").addEventListener("change", e => { state.box = e.target.value; refresh(); });
el("copy").addEventListener("click", async () => { try { await navigator.clipboard.writeText(el("text").textContent); el("copy").textContent = "Copied"; } catch (e) { el("copy").textContent = "Copy refused"; } setTimeout(() => { el("copy").textContent = "Copy shape"; }, 1500); });
addEventListener("hashchange", () => { const h = location.hash.slice(1); if (SETS.some(s => s.id === h) && h !== state.set) { state.set = h; refresh(); } });
refresh();
</script>
</body>
</html>
"""


def main(out, target):
    with (out / "free-circle-classes.pickle").open("rb") as f:
        pairs = pickle.load(f)
    shapes = sorted({p["shape"] for p in pairs.values()}, key=lambda s: (max(r for r, _ in s) + 1, max(c for _, c in s) + 1, s))
    records = []
    tally = Counter()
    for i, shape in enumerate(shapes, 1):
        lines = lines_of(set(shape))
        top = 8 if holds(shape, 8, lines) else 7 if holds(shape, 7, lines) else 6
        tally["top", top] += 1
        cells = []
        for root in shape:
            entry = pairs[pair_key(shape, root)]["entry"]
            eight = bool(entry[True][0])
            high = [bool(entry[True][1]), bool(entry[True][2]), list(entry[True][3])]
            low = [bool(entry[False][1]), bool(entry[False][2]), list(entry[False][3])]
            seven = high[0] or high[1] or low[0] or low[1]
            tally["pair", 8 if eight else 7 if seven else 6] += 1
            cells.append({"e": int(eight), "h": [int(high[0]), int(high[1]), high[2]], "l": [int(low[0]), int(low[1]), low[2]]})
        records.append({"i": i, "t": top, "c": [list(x) for x in shape], "k": cells})
    print(dict(tally), flush=True)
    wanted = {("top", 6): 1, ("top", 7): 345, ("top", 8): 902, ("pair", 6): 16, ("pair", 7): 4887, ("pair", 8): 6329}
    if dict(tally) != wanted:
        raise SystemExit("TOTALS FAILED")
    data = json.dumps(records, separators=(",", ":"))
    tmp = target + ".tmp"
    with open(tmp, "w") as f:
        f.write(PAGE.replace("__DATA__", data))
    os.replace(tmp, target)
    print(f"wrote {target}, {os.path.getsize(target):,} bytes", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])

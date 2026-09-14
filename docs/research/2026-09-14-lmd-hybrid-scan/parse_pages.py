"""Parse the fetched LMD puzzle pages into docs/research/2026-09-14-lmd-hybrid-scan.md.

A puzzle is a hybrid hit when its page carries the Sudoku tag (tag_id=1001) or its
title or rules text contains "doku". Run from the repo root:
    uv run docs/research/2026-09-14-lmd-hybrid-scan/parse_pages.py
"""

import collections
import html
import re
from pathlib import Path

PAGES = Path(".scratch/lmdpages")
LISTINGS = Path(".scratch/lmdtags")
OUT = Path("docs/research/2026-09-14-lmd-hybrid-scan.md")
PUZZLE_URL = "https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id="

tags = {}
for line in Path(".scratch/taglist.txt").read_text().splitlines():
    p = line.split()
    if len(p) >= 2:
        tags[p[-1]] = " ".join(p[:-1])

# which genre tags each puzzle was listed under
listed_under = collections.defaultdict(set)
for f in LISTINGS.glob("*.html"):
    tid = f.name.split("_")[0]
    for pid in re.findall(
        r"zeigen\.php\?id=([0-9A-Z]+)",
        f.read_text(encoding="utf-8", errors="replace"),
    ):
        listed_under[pid].add(tid)

hits = collections.defaultdict(list)  # genre tag -> rows
n_pages = 0
for f in sorted(PAGES.glob("*.html")):
    pid = f.stem
    h = f.read_text(encoding="utf-8", errors="replace")
    n_pages += 1
    title = html.unescape(re.search(r"<title>([^<]*)", h).group(1))
    title = re.split(r" — | &mdash; ", title)[0].strip()
    page_tags = dict(re.findall(r'tag_id=(\d+)"[^>]*>([^<]+)', h))
    text = re.sub(r"<[^>]+>", " ", h)
    rules_hit = bool(re.search(r"doku", text, re.I))
    tagged = "1001" in page_tags
    if not (tagged or rules_hit):
        continue
    author = re.search(r'Benutzer/allgemein\.php\?name=([^"]+)"', h)
    how = "Sudoku tag" if tagged else "rules/title mention only"
    who = author.group(1).strip() if author else "?"
    for tid in listed_under[pid]:
        hits[tid].append((pid, title, who, how, sorted(set(page_tags.values()))))

total = sum(len(v) for v in hits.values())
lines = [
    "# LMD tag scan: every sudoku hybrid per genre tag",
    "",
    "Date: 2026-09-14. Source: every puzzle listed on the newest 3 pages (60 puzzles) of each of",
    f"{len(tags)} LMD genre tag listings, then each puzzle page opened once ({n_pages} pages, one request",
    "per 10 s, no retries). Companion to `2026-09-14-puzzle-genre-survey.md`, which cites a selection;",
    "this file keeps every hit. Scripts: `2026-09-14-lmd-hybrid-scan/`.",
    "",
    "A hit is a puzzle whose page carries the Sudoku tag (tag_id 1001), or whose title or rules text",
    'contains "doku". The `how` field says which. Tags with fewer than 60 puzzles were read in full;',
    "for larger tags only the newest 60 were read, so older hybrids are not listed.",
    "",
    f"Total: {total} hits across {len(hits)} genre tags.",
    "",
    "| Genre tag | Tag id | Hits | Listed |",
    "|---|---|---|---|",
]
by_name = sorted(hits, key=lambda t: tags.get(t, t))
for tid in by_name:
    listed = sum(1 for s in listed_under.values() if tid in s)
    lines.append(f"| {tags.get(tid, tid)} | {tid} | {len(hits[tid])} | {listed} |")
for tid in by_name:
    lines += ["", f"## {tags.get(tid, tid)} (tag {tid})", ""]
    for pid, title, who, how, ptags in sorted(hits[tid], key=lambda r: r[1].lower()):
        lines.append(
            f"- {title} — {who}, LMD {pid} ({PUZZLE_URL}{pid}) — {how}; tags: {', '.join(ptags)}"
        )
zero = sorted(tags[t] for t in tags if t not in hits)
lines += ["", "## Genre tags with no hit in the pages read", "", ", ".join(zero), ""]
OUT.write_text("\n".join(lines))
print(f"{n_pages} pages parsed, {total} hits, {len(hits)} tags")

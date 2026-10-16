"""Parse fetched LMD puzzle pages and catalogue every puzzle whose rules use a Copycat mechanic.

Input: .scratch/copycat/pages/<id>.html (fetched at one request per 10 s).
Output: a JSON catalogue on stdout; the markdown is written by hand from it.
"""

import html
import json
import pathlib
import re
import sys

PAGES = pathlib.Path(".scratch/copycat/pages")

PENCIL = {
    "shading": r"\bshade|shaded|unshaded|yin ?yang|nurikabe|tapa|cave\b|choco ?banana|LITS\b|star battle|minesweeper",
    "loop_or_path": r"\bloop\b|\bpath\b|maze|snake|masyu|slitherlink|yajilin|rat run|finkz",
    "region": r"\bregion(?:s)? (?:must|are|of)|divide the grid|chaos construction|fillomino|shikaku|galax|sausage|pentomin|pseudo",
}


def text_of(h: str) -> str:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    t = re.sub(r"<br\s*/?>|</p>|</li>|</div>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(re.sub(r"[ \t]+", " ", t))


def rules_block(t: str) -> str:
    """Text between the published line and the solution code line."""
    m = re.search(r"\(Published on.*?\)|\(Eingestellt am.*?\)", t)
    start = m.end() if m else 0
    m2 = re.search(
        r"Solution code:|Lösungscode:|Puzzles in my Copycat series|Solve in SudokuPad|Solve in Penpa",
        t[start:],
    )
    end = start + m2.start() if m2 else start + 6000
    return t[start:end].strip()


def classify(rules: str) -> str:
    r = rules.lower()
    if "copycat cell" in r or ("copycat" in r and "rotationally opposite" in r):
        return "copycat cells (Scojo)"
    if "copyrat" in r or ("copycat" in r and "180" in r):
        return "copycat cells (Scojo)"
    if re.search(
        r"copycat.{0,200}(same (composition|set|multiset)|gleiche zusammenstellung)",
        r,
        re.S,
    ):
        return "copycat lines (Phistomefel)"
    if "copycat" in r or "copy cat" in r:
        return "copycat (other wording)"
    return ""


def main() -> None:
    out = []
    for p in sorted(PAGES.glob("*.html")):
        h = p.read_text(encoding="utf-8", errors="replace")
        t = text_of(h)
        title = (
            html.unescape(re.search(r"<title>(.*?)</title>", h, re.S).group(1))
            .split(" — ")[0]
            .strip()
        )
        au = re.search(r'Benutzer/allgemein\.php\?name=([^"&]+)"[^>]*>([^<]+)<', h)
        author = html.unescape(au.group(2)) if au else "?"
        date = re.search(r"(?:Published on|Eingestellt am) (\d+\. \w+ \d{4})", t)
        tags = [
            html.unescape(n) for _, n in re.findall(r'tag_id=(\d+)"[^>]*>([^<]+)', h)
        ]
        rules = rules_block(t)
        kind = classify(rules)
        pencil = [k for k, rx in PENCIL.items() if re.search(rx, rules, re.I)]
        genre_tags = [g for g in tags if g != "Sudoku"]
        out.append(
            {
                "id": p.stem,
                "title": title,
                "author": author,
                "date": date.group(1) if date else "?",
                "tags": tags,
                "genre_tags": genre_tags,
                "copycat": kind,
                "pencil_signals": pencil,
                "rules": rules[:4000],
            }
        )
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

"""Fetch every LMD puzzle page listed in the saved tag listings, one request per 10 s.

Resumable: a page already under .scratch/lmdpages/<id>.html is skipped. Appends one
line per request to the progress file. Run from the repo root:
    uv run finders/lmd-hybrid-scan/fetch_pages.py
"""

import re
import time
import urllib.request
from pathlib import Path

LISTINGS = Path(".scratch/lmdtags")
OUT = Path(".scratch/lmdpages")
PROGRESS = Path(".scratch/PROGRESS_lmdpages.log")
SPACING = 10.0
UA = "Mozilla/5.0 (research scan; one request per 10 s)"

ids = sorted(
    {
        m
        for f in LISTINGS.glob("*.html")
        for m in re.findall(
            r"zeigen\.php\?id=([0-9A-Z]+)",
            f.read_text(encoding="utf-8", errors="replace"),
        )
    }
)
OUT.mkdir(parents=True, exist_ok=True)
todo = [i for i in ids if not (OUT / f"{i}.html").exists()]
with PROGRESS.open("a") as log:
    log.write(f"{time.strftime('%H:%M:%S')} START total={len(ids)} todo={len(todo)}\n")
    for n, pid in enumerate(todo, 1):
        url = f"https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id={pid}&chlang=en"
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                body, code = r.read(), r.status
            (OUT / f"{pid}.html").write_bytes(body)
            log.write(
                f"{time.strftime('%H:%M:%S')} {n}/{len(todo)} {pid} http={code} bytes={len(body)}\n"
            )
        except Exception as e:  # no retry; record and move on
            log.write(f"{time.strftime('%H:%M:%S')} {n}/{len(todo)} {pid} ERROR {e}\n")
        log.flush()
        time.sleep(max(0.0, SPACING - (time.time() - t0)))
    log.write(f"{time.strftime('%H:%M:%S')} DONE\n")

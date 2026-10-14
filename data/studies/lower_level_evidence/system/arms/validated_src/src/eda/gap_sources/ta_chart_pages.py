"""Tennis Abstract website-only women's charts: do the pages carry the full point log, and has the index grown?

Reads data/studies/gap_sources/women_charts.csv (lane A: women's website-only charts of 2018-26 linked to the
women's shot gap). Fetches three of them that the Hugging Face copy lacks (one each from 2019, 2023 and 2026,
the first in date order), and the chart index meta.html once, then compares the index's women's charts of
2018-26 with the copy read on 23 Sep 2026 (data/raw/point_shot_sources/tennis_abstract/).

robots.txt allows /charting/. Requests are 3 s apart and stop on a refusal.

Usage:
    ./python.sh src/eda/gap_sources/ta_chart_pages.py [--offline]   # --offline: from the saved pages, no request

Writes data/raw/gap_sources/tennisabstract/ (pages, receipts; gitignored) and
data/studies/gap_sources/ta_chart_pages.json.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW = PROJECT_ROOT / "data" / "raw" / "gap_sources" / "tennisabstract"
OLD_INDEX_DIR = PROJECT_ROOT / "data" / "raw" / "point_shot_sources" / "tennis_abstract"
OUT = PROJECT_ROOT / "data" / "studies" / "gap_sources" / "ta_chart_pages.json"
HEADERS = {"User-Agent": "tennis-predictions research (non-commercial)"}
CHART_ID = re.compile(r"(\d{8}-[MW]-[A-Za-z0-9_\-.'%]+?)\.html")   # the index links are relative


OFFLINE = "--offline" in sys.argv


def get(url: str, dest: Path, receipts: list) -> bytes | None:
    if OFFLINE:   # reuse the saved page; no request
        return dest.read_bytes() if dest.exists() else None
    time.sleep(3)
    r = requests.get(url, headers=HEADERS, timeout=60)
    body = r.content
    receipts.append({"url": url, "status": r.status_code, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                     "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    if r.status_code != 200:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return body


def women_2018_2026(html: str) -> set:
    return {c for c in CHART_ID.findall(html) if c[9] == "W" and "2018" <= c[:4] <= "2026"}


def main() -> int:
    w = pd.read_csv(PROJECT_ROOT / "data" / "studies" / "gap_sources" / "women_charts.csv")
    pick = []
    for year in (2019, 2023, 2026):
        cand = w[(w["year"] == year) & ~w["in_hf_copy"].astype(bool) & w["in_women_shots_gap"].astype(bool)]
        pick.append(cand.sort_values("chart_id").iloc[0])
    receipts, pages = [], []
    for row in pick:
        body = get(row["url"], RAW / "charts" / f"{row['chart_id']}.html", receipts)
        html = body.decode("utf-8", errors="replace") if body else ""
        m = re.search(r"var\s+pointlog\s*=\s*'(.*?)';", html, re.S)
        log = m.group(1) if m else ""
        last = receipts[-1] if receipts else {"status": 200 if body else None, "bytes": len(body or b"")}
        pages.append({"chart_id": row["chart_id"], "status": last["status"], "bytes": last["bytes"],
                      "pointlog_chars": len(log), "pointlog_rows": log.count("<tr"),
                      "sample": re.sub(r"<[^>]+>", " ", log)[:300]})
        if not body:
            break
    idx = get("https://www.tennisabstract.com/charting/meta.html", RAW / "meta.html", receipts)
    now = women_2018_2026(idx.decode("utf-8", errors="replace")) if idx else set()
    olds = sorted(OLD_INDEX_DIR.glob("*meta*.htm*"))
    before = women_2018_2026(olds[-1].read_text(encoding="utf-8", errors="replace")) if olds else set()
    out = {"pages": pages, "index": {"women_2018_2026_now": len(now), "women_2018_2026_on_23_sep": len(before),
                                     "new_since": len(now - before), "old_copy": olds[-1].name if olds else None},
           "receipts": receipts}
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "_receipts.jsonl").open("a", encoding="utf-8").write("".join(json.dumps(r) + "\n" for r in receipts))
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "receipts"}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

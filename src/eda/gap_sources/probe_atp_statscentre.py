"""Gap sources, lane B4: do the ATP Stats Centre (Infosys) static files exist for 2025-2026 matches?

Twenty requests at most, one every 2.5 seconds, to https://itp-atp-sls.infosys-platforms.com/static/prod/...,
with a Chrome user agent plus `Referer` and `Origin` https://www.atptour.com (what the atptour.com Stats
Centre page sends; documented in docs/research/granular-data-leads/README.md, row 14). URL templates are
glad94/infotennis `references/api-info/atp-infosys-api-info.json` (copied in the SirGenkii fork):
  match-beats     /static/prod/match-beats/{year}/{event}/{match}/data.json
  rally-analysis  /static/prod/rally-analysis/{year}/{event}/{match}/data.json
  key stats       /static/prod/stats-plus/{year}/{event}/{match}/keystats.json
  court vision    /static/prod/court-vision/{year}/{event}/{match}/data.json
Event ids are Tennis My Life `tourney_id` numbers ('2025-416' -> 416). ATP match codes are MS001 for the
final (MS002-003 semi-finals ...) and QS001 for the last qualifying match, so no match lookup is needed.

Most requests are HEAD (status and size only). Two are full GETs whose bodies are checked for the
`{"lastModified": <ms>, "response": "<base64>"}` shape: key names, and whether the base64 decodes to a
multiple of 16 bytes (an AES block size). Nothing is decrypted. A 403 with an XML body type is the storage
layer's answer for a missing object; any other 403, a 429 or a challenge page stops the run.

Writes data/studies/gap_sources/atp_statscentre_probe.csv. Run: ./python.sh src/eda/gap_sources/probe_atp_statscentre.py

Note: the table of 29 Sep 2026 was written before `shape()` learnt about the extra `"data": null` key, so
its two GET rows read "keys ['data', 'lastModified', 'response']"; the lane notes record the base64 check
made afterwards on a saved copy of one body.
"""
from __future__ import annotations

import base64
import binascii
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from curl_cffi import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "studies" / "gap_sources" / "atp_statscentre_probe.csv"
HOST = "https://itp-atp-sls.infosys-platforms.com"
PATHS = {"match-beats": "/static/prod/match-beats/{y}/{e}/{m}/data.json",
         "rally-analysis": "/static/prod/rally-analysis/{y}/{e}/{m}/data.json",
         "keystats": "/static/prod/stats-plus/{y}/{e}/{m}/keystats.json",
         "court-vision": "/static/prod/court-vision/{y}/{e}/{m}/data.json"}
HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/128.0.0.0 Safari/537.36"),
           "Referer": "https://www.atptour.com/", "Origin": "https://www.atptour.com",
           "Accept": "application/json, text/plain, */*"}
GAP_S = 2.5

# (year, event id, match code, file, method, level, what the match is)
SAMPLE = [
    (2025, 416, "MS001", "match-beats", "HEAD", "T1000", "Rome Masters 2025 final (after the SirGenkii dumps)"),
    (2025, 500, "MS001", "match-beats", "HEAD", "T500", "Halle 2025 final"),
    (2025, 418, "MS001", "rally-analysis", "HEAD", "T500", "Washington 2025 final"),
    (2025, 422, "MS001", "match-beats", "HEAD", "T1000", "Cincinnati 2025 final (retirement at 5-0)"),
    (2025, 5014, "MS001", "match-beats", "GET", "T1000", "Shanghai 2025 final"),
    (2025, 605, "MS001", "match-beats", "HEAD", "FIN", "ATP Finals 2025 final"),
    (2025, 421, "QS001", "match-beats", "HEAD", "TQ", "Canada Masters 2025 qualifying"),
    (2026, 339, "MS001", "match-beats", "HEAD", "T250", "Brisbane 2026 final"),
    (2026, 1536, "MS001", "match-beats", "HEAD", "T1000", "Madrid Masters 2026 final"),
    (2026, 311, "MS001", "rally-analysis", "HEAD", "T500", "Queen's Club 2026 final"),
    (2026, 421, "MS001", "match-beats", "GET", "T1000", "Canada Masters 2026 final"),
    (2026, 421, "MS001", "keystats", "HEAD", "T1000", "Canada Masters 2026 final"),
    (2026, 421, "MS001", "court-vision", "HEAD", "T1000", "Canada Masters 2026 final"),
    (2026, 422, "QS001", "match-beats", "HEAD", "TQ", "Cincinnati Masters 2026 qualifying"),
    (2026, 6242, "MS001", "match-beats", "HEAD", "T250", "Winston-Salem 2026 final"),
    (2025, 2907, "MS001", "match-beats", "HEAD", "CH", "Nottingham Challenger 2025 final"),
    (2025, 7341, "MS001", "match-beats", "HEAD", "CH", "Brest Challenger 2025 final"),
    (2026, 1214, "MS001", "match-beats", "HEAD", "CH", "Troyes Challenger 2026 final"),
    (2026, 1763, "MS001", "match-beats", "HEAD", "CH", "Genoa Challenger 2026 final"),
    (2026, 1763, "MS001", "rally-analysis", "HEAD", "CH", "Genoa Challenger 2026 final"),
]


def shape(body: bytes) -> str:
    try:
        d = json.loads(body)
    except ValueError:
        return "not JSON"
    if not isinstance(d, dict):
        return "JSON, not an object"
    keys = sorted(d)
    # the 29 Sep 2026 run found a third key, "data": null, next to the two documented ones
    if "data" in d and d["data"] is None:
        keys = [k for k in keys if k != "data"]
    if keys != ["lastModified", "response"]:
        return f"keys {keys}"
    try:
        raw = base64.b64decode(d["response"], validate=True)
    except (binascii.Error, ValueError):
        return "lastModified+response; response not base64"
    return (f"lastModified+response; base64 -> {len(raw)} bytes, multiple of 16: {len(raw) % 16 == 0}; "
            f"lastModified {datetime.fromtimestamp(int(d['lastModified']) / 1000, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")


def main() -> None:
    rows, last = [], 0.0
    for y, e, mcode, kind, method, level, what in SAMPLE:
        url = HOST + PATHS[kind].format(y=y, e=e, m=mcode)
        wait = GAP_S - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        last = time.time()
        r = requests.request(method, url, headers=HEADERS, impersonate="chrome", timeout=60, allow_redirects=False)
        ctype = r.headers.get("content-type", "")
        size = r.headers.get("content-length") or (str(len(r.content)) if method == "GET" else "")
        row = {"utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "year": y, "event_id": e,
               "match_code": mcode, "file": kind, "level": level, "match": what, "method": method, "url": url,
               "status": r.status_code, "bytes": size, "content_type": ctype,
               "last_modified": r.headers.get("last-modified", ""), "x_cache": r.headers.get("x-cache", ""),
               "exists": r.status_code == 200, "body_shape": shape(r.content) if method == "GET" and r.status_code == 200 else ""}
        rows.append(row)
        print(row["status"], size, kind, y, e, mcode, row["body_shape"])
        if r.status_code in (429, 503) or (r.status_code == 403 and "xml" not in ctype.lower()):
            row["note"] = "stopped: possible block"
            print("stopping: possible block", r.status_code, ctype)
            break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cols = ["utc", "year", "event_id", "match_code", "file", "level", "match", "method", "url", "status", "bytes",
            "content_type", "last_modified", "x_cache", "exists", "body_shape", "note"]
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in cols})


if __name__ == "__main__":
    main()

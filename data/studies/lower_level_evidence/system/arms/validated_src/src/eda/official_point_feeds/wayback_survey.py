"""What the Wayback Machine holds of the official point feeds, for editions and matches the project does not have.

Asks the Wayback Machine's capture index (the CDX API) for every archived copy of each feed's point-data URLs. Only
the index is downloaded: each answer is cached with a receipt under data/raw/point_sources/wayback_cdx/, paced and
stopped on a block like the adapters (feeds.FeedClient), under the owner's decision of 24 Sep 2026.

Queries (see QUERIES):
    ao_api            prod-scores-api.ausopen.com, every path: match centres, draws, daily results (2019 on)
    ao_domain         any *.ausopen.com JSON or XML whose path names SlamTracker, scores, a match, statistics or points
                      (the IBM-era site of 2011-2018 served SlamTracker files like the other Slams)
    ao_manhattan      prod-manhattan-api.ausopen.com, a second scores API seen in 2019 captures
    ao_match_pages    ausopen.com/match/..., the match pages (HTML) of 2019 on
    uso_slamtracker   *.usopen.org SlamTracker files (the live feed serves 2022 on)
    wim_slamtracker   *.wimbledon.com SlamTracker files (the live feeds serve 2019 and 2021 on)
    wta_pbp           api.wtatennis.com point-by-point documents (the API serves 2022 on)

Outputs (data/studies/official_point_feeds/):
    wayback_survey.json      per query: captures, distinct URLs, by URL family and year; point-data captures by feed
                             and edition year (fetched or not, and whether the live feed still serves that year)
    wayback_survey.csv       one row per query, URL family and year
    wayback_point_data.csv   one row per distinct capture of a point-data URL
Usage:
    ./python.sh src/eda/official_point_feeds/wayback_survey.py [--queries ao_api,ao_domain] [--max-requests 40]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlencode, urlsplit

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import feeds as F  # noqa: E402

SOURCE = "wayback_cdx"
CDX = "https://web.archive.org/cdx/search/cdx"
FIELDS = "timestamp,original,statuscode,mimetype,length,digest"
PAGE_ROWS = 20000
QUERIES = {
    "ao_api": {"url": "prod-scores-api.ausopen.com", "matchType": "host", "filter": ["statuscode:200"]},
    "ao_domain": {"url": "ausopen.com", "matchType": "domain",
                  "filter": ["statuscode:200", "mimetype:.*(json|xml).*",
                             "original:(?i).*(slamtracker|score|match|stats|point).*"]},
    "ao_manhattan": {"url": "prod-manhattan-api.ausopen.com", "matchType": "host", "filter": ["statuscode:200"]},
    "ao_match_pages": {"url": "ausopen.com/match/", "matchType": "prefix", "filter": ["statuscode:200"]},
    "uso_slamtracker": {"url": "usopen.org", "matchType": "domain",
                        "filter": ["statuscode:200", "original:(?i).*slamtracker.*"]},
    "wim_slamtracker": {"url": "wimbledon.com", "matchType": "domain",
                        "filter": ["statuscode:200", "original:(?i).*slamtracker.*"]},
    "wta_pbp": {"url": "api.wtatennis.com", "matchType": "host",
                "filter": ["statuscode:200", "original:(?i).*point-by-point.*"]},
}
# Editions the live feeds serve (and the project collects): Wayback years outside these are new.
LIVE_YEARS = {"ao": {2026}, "uso": set(range(2022, 2027)), "wim": {2019} | set(range(2021, 2027)),
              "wta": set(range(2022, 2027))}
YEAR_IN_PATH = re.compile(r"(?:^|[/.])((?:19|20)\d\d)(?=[/._-])")
# (month, day) before which a capture still holds the previous edition (AO mid-January, Wimbledon late June,
# US Open late August); approximate, and AO 2021 started on 8 February
EVENT_START = {"ao": (1, 12), "wim": (6, 20), "uso": (8, 20)}


def cdx_url(query: dict, resume_key: str | None = None) -> str:
    params = [("url", query["url"]), ("matchType", query["matchType"]), ("fl", FIELDS), ("output", "json"),
              ("limit", str(PAGE_ROWS)), ("showResumeKey", "true")]
    params += [("filter", f) for f in query.get("filter", [])]
    if resume_key:
        params.append(("resumeKey", resume_key))
    return f"{CDX}?{urlencode(params)}"


def parse_answer(payload) -> tuple[list[dict], str | None]:
    """CDX JSON rows (header first) as dicts, and the resume key when the answer was cut at PAGE_ROWS."""
    if not payload:
        return [], None
    header, *rows = payload
    resume = None
    if len(rows) >= 2 and rows[-2] == [] and len(rows[-1]) == 1:
        resume = rows[-1][0]
        rows = rows[:-2]
    return [dict(zip(header, r)) for r in rows if r], resume


def url_family(query: str, original: str) -> str:
    """A coarse name for what a URL serves, for counting."""
    path = urlsplit(original).path
    lowered = path.lower()
    if query == "ao_api" or "prod-scores-api" in original:
        for key in ("match-centre", "draws", "results", "schedule", "live"):
            if key in lowered:
                return key
        return "other:" + "/".join(p for p in path.split("/")[:3] if not p.isdigit())
    for key in ("slamtracker/history", "slamtracker/stats", "slamtracker/distance", "pointbypoint",
                "point-by-point", "matches/complete", "draws", "match-centre", "matchcentre", "scores"):
        if key in lowered:
            return key
    return "other"


# URLs that hold a match's points: the AO match centre (2020 on) and its 2019 "manhattan" API, and the IBM
# SlamTracker histories of every Slam; the WTA's point-by-point documents
POINT_DATA = re.compile(r"prod-scores-api\.ausopen\.com/match-centre/|prod-manhattan-api\.ausopen\.com/year/\d+/match/"
                        r"|/slamtracker/history/[^/]+\.json|/point-by-point", re.IGNORECASE)


def held_captures() -> set[tuple[str, str]]:
    """(timestamp, original) of every Wayback capture the AO adapter has already asked for."""
    path = P.raw_path("ausopen", "_receipts.jsonl")
    held = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line) if line.strip() else {}
            if r.get("name", "").startswith(("wayback/", "wayback-extra/")) and r.get("capture_timestamp"):
                held.add((r["capture_timestamp"], r.get("original")))
    return held


def capture_year(row: dict) -> int:
    return int(row["timestamp"][:4])


def edition_year(row: dict, feed: str | None = None) -> int | None:
    """The tournament year a URL names (a /2019/ path part or a 2019. subdomain). A URL without one (the AO match
    centre, the IBM-era live files) holds the latest edition at capture time: the capture's year, or the year
    before when the capture predates that year's event (EVENT_START); None when the feed is not given."""
    parts = urlsplit(row["original"])
    m = YEAR_IN_PATH.search(parts.path) or re.match(r"^((?:19|20)\d\d)\.", parts.netloc)
    if m:
        return int(m.group(1))
    if feed not in EVENT_START:
        return None
    ts = row["timestamp"]
    year, month_day = int(ts[:4]), (int(ts[4:6]), int(ts[6:8]))
    return year - 1 if month_day < EVENT_START[feed] else year


def run_queries(names: list[str], max_requests: int | None, pages: int) -> tuple[dict, dict]:
    receipts = P.receipts_for(SOURCE)
    client = F.FeedClient("chrome", min_interval=4.0, jitter=1.0, max_requests=max_requests)
    rows_by_query, info = {}, {}
    try:
        for name in names:
            rows, resume, page = [], None, 0
            while page < pages:
                dest = P.raw_path(SOURCE, f"{name}_{page}.json")
                receipt = P.fetch(client, cdx_url(QUERIES[name], resume), dest, receipts, name=f"{name}/{page}",
                                  validator=P.json_validator, extra={"query": name, "page": page})
                if receipt.get("status") != 200 or receipt.get("error"):
                    info[name] = {"error": receipt.get("error") or f"HTTP {receipt.get('status')}", "pages": page}
                    break
                found, resume = parse_answer(P.read_json(dest))
                rows.extend(found)
                page += 1
                if not resume:
                    break
            rows_by_query[name] = rows
            info.setdefault(name, {"pages": page, "cut_at_page_limit": bool(resume)})
            P.log(f"[wayback] {name}: {len(rows):,} captures in {page} page(s)")
    except (P.Blocked, P.BudgetExhausted) as stop:
        info["stopped"] = f"{type(stop).__name__}: {stop}"
        P.log(f"[wayback] STOPPED: {stop}")
    info["client"] = client.stats()
    return rows_by_query, info


def summarize(rows_by_query: dict) -> tuple[dict, list[dict]]:
    out, table = {}, []
    for name, rows in rows_by_query.items():
        feed = name.split("_")[0]
        live = LIVE_YEARS.get(feed, set())
        by = defaultdict(lambda: {"captures": 0, "urls": set(), "contents": set()})
        for r in rows:
            year = edition_year(r, feed) or capture_year(r)
            key = (url_family(name, r["original"]), year)
            by[key]["captures"] += 1
            by[key]["urls"].add(r["original"])
            by[key]["contents"].add((r["original"], r.get("digest")))
        families = Counter()
        for (family, year), v in sorted(by.items()):
            row = {"query": name, "family": family, "year": year, "captures": v["captures"],
                   "distinct_urls": len(v["urls"]), "distinct_contents": len(v["contents"]),
                   "live_feed_serves_year": year in live}
            table.append(row)
            families[family] += v["captures"]
        out[name] = {"captures": len(rows), "distinct_urls": len({r["original"] for r in rows}),
                     "by_family": dict(families.most_common()),
                     "years_not_served_live": sorted({y for (f, y) in by if y not in live})}
    return out, table


def point_data(rows_by_query: dict) -> tuple[dict, list[dict]]:
    """Every capture of a point-data URL, one per distinct content, with its edition year, whether the live feed
    still serves that year and whether the project has fetched it."""
    held = held_captures()
    seen, listing = set(), []
    for name, rows in rows_by_query.items():
        feed = name.split("_")[0]
        for r in rows:
            if not POINT_DATA.search(r["original"]) or (r["original"], r.get("digest")) in seen:
                continue
            seen.add((r["original"], r.get("digest")))
            year = edition_year(r, feed) or capture_year(r)
            listing.append({"feed": feed, "year": year, "timestamp": r["timestamp"], "original": r["original"],
                            "digest": r.get("digest"), "length": r.get("length"),
                            "live_feed_serves_year": year in LIVE_YEARS.get(feed, set()),
                            "fetched": (r["timestamp"], r["original"]) in held})
    summary = defaultdict(lambda: defaultdict(lambda: {"captures": 0, "fetched": 0}))
    for item in listing:
        cell = summary[item["feed"]][item["year"]]
        cell["captures"] += 1
        cell["fetched"] += int(item["fetched"])
        cell["live_feed_serves_year"] = item["live_feed_serves_year"]
    return {f: dict(sorted(v.items())) for f, v in summary.items()}, sorted(listing, key=lambda x: (x["feed"], x["year"], x["timestamp"]))


def main() -> int:
    P.configure_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--queries", default=",".join(QUERIES), help="comma list of query names")
    parser.add_argument("--max-requests", type=int, default=60)
    parser.add_argument("--pages", type=int, default=10, help="at most this many CDX pages per query")
    args = parser.parse_args()
    started = time.time()
    names = [n.strip() for n in args.queries.split(",") if n.strip()]
    rows_by_query, info = run_queries(names, args.max_requests, args.pages)
    summary, table = summarize(rows_by_query)
    points, listing = point_data(rows_by_query)
    out = {"generated_at": P.utc_now_iso(), "decision": F.DECISION, "queries": {n: QUERIES[n] for n in names},
           "fetch": info, "summary": summary, "point_data_by_feed_and_year": points,
           "seconds": round(time.time() - started, 1)}
    study = F.STUDY_ROOT
    study.mkdir(parents=True, exist_ok=True)
    (study / "wayback_survey.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    import csv

    with (study / "wayback_survey.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["query", "family", "year", "captures", "distinct_urls",
                                                    "distinct_contents", "live_feed_serves_year"])
        writer.writeheader()
        writer.writerows(table)
    with (study / "wayback_point_data.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["feed", "year", "timestamp", "original", "digest", "length",
                                                    "live_feed_serves_year", "fetched"])
        writer.writeheader()
        writer.writerows(listing)
    P.log(json.dumps(points, indent=1))
    return 1 if info.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())

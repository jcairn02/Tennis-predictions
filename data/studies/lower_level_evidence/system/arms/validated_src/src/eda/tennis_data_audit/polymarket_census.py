"""Read-only research census, not a production ingestion design.

Fetch all tennis-tagged events with stable keyset pagination, retaining raw pages
and request hashes. Classify locally against an explicit UTC research window.
Run with the deliberately selected standalone interpreter documented in the study.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
BASE = "https://gamma-api.polymarket.com"
START = "2025-09-10T00:00:00+00:00"
END = "2026-09-11T00:00:00+00:00"


def parse_date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except ValueError:
        return None


def unpack(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return value or []


def volume_value(record):
    """Preserve absent/null fields; missing volume is not measured zero volume."""
    for key in ("volumeNum", "volume"):
        if record.get(key) not in (None, ""):
            return float(record[key])
    return None


def get(url):
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read()
                return json.loads(body), body, dict(response.headers)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--out", default=str(ROOT / "data/studies/tennis_data_audit/polymarket"))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    raw = out / "raw"
    raw.mkdir(exist_ok=True)
    manifest = []

    def fetch(path, name):
        url = BASE + path
        filename = raw / (name + ".json.gz")
        meta_path = raw / (name + ".meta.json")
        if filename.exists() and meta_path.exists() and not args.refresh:
            body = gzip.decompress(filename.read_bytes())
            item = json.loads(meta_path.read_text(encoding="utf-8"))
            if item["url"] != url or item["sha256"] != hashlib.sha256(body).hexdigest():
                raise ValueError("Cache URL/hash mismatch: " + name)
            data = json.loads(body)
        else:
            data, body, headers = get(url)
            item = {"url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "http_date": headers.get("Date"), "sha256": hashlib.sha256(body).hexdigest(),
                    "bytes": len(body), "file": str(filename.relative_to(out))}
            filename.write_bytes(gzip.compress(body))
            meta_path.write_text(json.dumps(item, indent=2), encoding="utf-8")
        manifest.append(item)
        return data

    sports = fetch("/sports", "sports")
    tennis_sports = [s for s in sports if "864" in str(s.get("tags", "")).split(",")]
    fetch("/tags/slug/tennis", "tennis-tag")
    all_events = {}
    discoveries = {}
    # Tennis tag is the main census; primary tour tags independently test tagging gaps.
    queries = [("tennis", {"tag_id": 864})]
    for tid in sorted({s.get("primaryTagId") for s in tennis_sports if s.get("primaryTagId")}):
        queries.append(("tag-" + str(tid) + "-outside-tennis", {"tag_id": tid, "exclude_tag_id": 864}))
    for label, query in queries:
        cursor = None
        seen_cursors = set()
        ids = set()
        for page in range(1000):
            params = {**query, "limit": 500, "order": "id", "ascending": "true"}
            if cursor:
                params["after_cursor"] = cursor
            result = fetch("/events/keyset?" + urllib.parse.urlencode(params), f"{label}-{page:04d}")
            rows = result["events"]
            for event in rows:
                eid = str(event["id"])
                if eid in ids:
                    raise ValueError("Duplicate event within cursor sweep: " + eid)
                ids.add(eid)
                all_events.setdefault(eid, event)
            if page % 25 == 0 or not result.get("next_cursor"):
                print(f"{label}: page={page} events={len(rows)} cumulative={len(ids)} unique={len(all_events)}", flush=True)
            cursor = result.get("next_cursor")
            if not cursor:
                break
            if cursor in seen_cursors:
                raise ValueError("Repeated cursor")
            seen_cursors.add(cursor)
        else:
            raise RuntimeError("Pagination guard exhausted; census is incomplete")
        discoveries[label] = sorted(ids, key=int)

    low, high = parse_date(START), parse_date(END)
    event_rows, market_rows = [], []
    for eid, event in sorted(all_events.items(), key=lambda x: int(x[0])):
        slug = event.get("slug", "")
        date_match = re.search(r"(20\d\d-\d\d-\d\d)", slug)
        dates = {"startTime": event.get("startTime"), "eventDate": event.get("eventDate"),
                 "slug_date": date_match.group(1) if date_match else None, "endDate": event.get("endDate")}
        selected = next(((key, parse_date(value)) for key, value in dates.items() if parse_date(value)), (None, None))
        time_field, event_time = selected
        in_sport_window = bool(event_time and low <= event_time < high)
        created = parse_date(event.get("startDate")) or parse_date(event.get("createdAt"))
        closed = parse_date(event.get("closedTime"))
        if not closed:
            closes = [parse_date(m.get("closedTime")) for m in event.get("markets", [])]
            closed = max((x for x in closes if x), default=None)
        # Metadata overlap is a candidate universe, not proof of historical executable quotes.
        overlap = bool(created and created < high and (closed is None or closed >= low))
        series = [{"id": s.get("id"), "slug": s.get("slug"), "title": s.get("title")} for s in event.get("series", [])]
        row = {"id": eid, "slug": slug, "title": event.get("title"), "url": "https://polymarket.com/event/" + slug,
               "dates": dates, "date_basis": time_field, "sport_date": event_time.isoformat() if event_time else None,
               "in_sport_window": in_sport_window, "metadata_trading_overlap": overlap,
               "createdAt": event.get("createdAt"), "startDate": event.get("startDate"),
               "closedTime_derived": closed.isoformat() if closed else None,
               "closed": event.get("closed"), "volume": event.get("volume"), "series": series,
               "tags": [{"id": t.get("id"), "label": t.get("label"), "slug": t.get("slug")} for t in event.get("tags", [])],
               "gameId": event.get("gameId"), "seriesSlug": event.get("seriesSlug"),
               "eventMetadata": event.get("eventMetadata"), "sport": event.get("sport"),
               "market_count": len(event.get("markets", []))}
        event_rows.append(row)
        for m in event.get("markets", []):
            fields = ("id", "question", "slug", "conditionId", "questionID", "sportsMarketType", "line",
                      "gameStartTime", "eventStartTime", "startDate", "endDate", "createdAt", "closedTime",
                      "closed", "volume", "volumeNum", "resolutionSource", "description", "umaResolutionStatus",
                      "feesEnabled", "feeType", "feeSchedule", "acceptingOrders", "acceptingOrdersTimestamp",
                      "groupItemTitle", "gameId", "teamAID", "teamBID")
            mr = {k: m.get(k) for k in fields}
            mr.update({"event_id": eid, "event_slug": slug, "in_sport_window": in_sport_window,
                       "outcomes": unpack(m.get("outcomes")), "outcomePrices": unpack(m.get("outcomePrices")),
                       "clobTokenIds": unpack(m.get("clobTokenIds"))})
            market_rows.append(mr)

    (out / "events.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in event_rows), encoding="utf-8")
    with gzip.open(out / "markets.jsonl.gz", "wt", encoding="utf-8") as handle:
        for row in market_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    sport_events = [e for e in event_rows if e["in_sport_window"]]
    sport_markets = [m for m in market_rows if m["in_sport_window"]]
    unique_markets = {str(m["id"]): m for m in sport_markets}
    summary = {
        "research_start_inclusive": START, "research_end_exclusive": END,
        "retrieval_started_at": manifest[0]["retrieved_at"], "retrieval_finished_at": manifest[-1]["retrieved_at"],
        "tennis_sports_metadata": tennis_sports, "all_time_unique_events": len(event_rows),
        "discovery_counts": {k: len(v) for k, v in discoveries.items()},
        "supplemental_ids_outside_tennis_tag": sorted(set(all_events) - set(discoveries["tennis"]), key=int),
        "sport_window_events": len(sport_events), "sport_window_market_rows": len(sport_markets),
        "sport_window_unique_markets": len(unique_markets),
        "metadata_overlap_events": sum(e["metadata_trading_overlap"] for e in event_rows),
        "window_by_month": dict(sorted(Counter(e["sport_date"][:7] for e in sport_events).items())),
        "window_by_series": dict(Counter(s["slug"] for e in sport_events for s in e["series"])),
        "window_by_date_basis": dict(Counter(e["date_basis"] for e in sport_events)),
        "window_market_types": dict(Counter(m.get("sportsMarketType") or "not_set" for m in unique_markets.values())),
        "window_positive_volume_markets": sum(volume_value(m) is not None and volume_value(m) > 0 for m in unique_markets.values()),
        "window_zero_volume_markets": sum(volume_value(m) == 0 for m in unique_markets.values()),
        "window_missing_volume_markets": sum(volume_value(m) is None for m in unique_markets.values()),
        "window_missing_condition_id": sum(not m.get("conditionId") for m in unique_markets.values()),
        "window_missing_two_token_ids": sum(len(m["clobTokenIds"]) != 2 for m in unique_markets.values()),
        "window_missing_resolution_text": sum(not m.get("description") for m in unique_markets.values()),
        "window_closed_events": sum(bool(e["closed"]) for e in sport_events),
        "window_open_events": sum(not e["closed"] for e in sport_events),
        "notes": ["Complete cursor sweeps of discovered tags, not proof of every untagged/deleted event.",
                  "Sport-date hierarchy: startTime, eventDate, slug date, endDate fallback; inspect fallback cases.",
                  "Volumes are lifetime snapshot values, not turnover restricted to the research window.",
                  "Market rows may repeat under multiple event parents; use unique market IDs for market counts.",
                  "Metadata trading overlap does not prove continuous availability or any executable quote."]}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "request-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()

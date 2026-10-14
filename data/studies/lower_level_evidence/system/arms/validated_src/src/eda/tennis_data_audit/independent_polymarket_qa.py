"""Independent, offline QA of saved census artifacts; no fetch or production code.

Uses only the standard library. The research run explicitly selected the separate
ufc-monitor interpreter; it did not assert that the tennis environment was ready.
This writes only independent-qa.json and never modifies the census or its summary.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/studies/tennis_data_audit/polymarket"


def dt(value):
    if not value:
        return None
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result


def main():
    summary = json.loads((DATA / "summary.json").read_text(encoding="utf-8"))
    audited = json.loads((DATA / "audited-summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((DATA / "request-manifest.json").read_text(encoding="utf-8"))
    events = [json.loads(x) for x in (DATA / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    excluded = {e["id"] for e in events if any(s["slug"] == "cfb-2025" for s in e["series"])
                or (e.get("sport") or {}).get("sport") == "cfb"}
    low = dt(summary["research_start_inclusive"])
    high = dt(summary["research_end_exclusive"])
    retrieved = dt(summary["retrieval_finished_at"])
    sport = {e["id"] for e in events if e["in_sport_window"] and e["id"] not in excluded}
    overlap = {e["id"] for e in events if e["metadata_trading_overlap"] and e["id"] not in excluded}
    lookup = {e["id"]: e for e in events}
    counts = Counter()
    market_ids = {"sport": set(), "overlap": set()}
    closed_before, closed_missing = [], []
    with gzip.open(DATA / "markets.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            m = json.loads(line)
            if m["event_id"] in sport:
                counts["sport_window_contract_rows"] += 1
                market_ids["sport"].add(m["id"])
            if m["event_id"] not in overlap:
                continue
            counts["overlap_event_attached_contract_rows"] += 1
            market_ids["overlap"].add(m["id"])
            close = dt(m.get("closedTime"))
            item = {k: m.get(k) for k in ("id", "event_id", "question", "startDate", "createdAt", "closedTime", "closed")}
            if close and close < low:
                closed_before.append(item)
            if m.get("closed") and not close:
                closed_missing.append(item)
    page_groups = defaultdict(list)
    errors = []
    total_raw_rows = 0
    maximum_attached_markets = 0
    for entry in manifest:
        if "/events/keyset?" not in entry["url"]:
            continue
        raw_path = DATA.joinpath(*re.split(r"[\\/]", entry["file"]))
        body = gzip.decompress(raw_path.read_bytes())
        if hashlib.sha256(body).hexdigest() != entry["sha256"]:
            errors.append({"file": entry["file"], "problem": "hash mismatch"})
        page = json.loads(body)
        rows = page["events"]
        ids = [int(e["id"]) for e in rows]
        if ids != sorted(set(ids)):
            errors.append({"file": entry["file"], "problem": "IDs not strictly increasing within page"})
        for event in rows:
            maximum_attached_markets = max(maximum_attached_markets, len(event.get("markets", [])))
        total_raw_rows += len(rows)
        params = parse_qs(urlsplit(entry["url"]).query)
        key = (tuple(params.get("tag_id", [])), tuple(params.get("exclude_tag_id", [])))
        page_groups[key].append({"file": entry["file"], "rows": len(rows), "ids": ids,
                                "after_cursor": params.get("after_cursor", [None])[0],
                                "next_cursor": page.get("next_cursor")})
    sweeps = []
    for key, pages in page_groups.items():
        for previous, current in zip(pages, pages[1:]):
            if current["after_cursor"] != previous["next_cursor"]:
                errors.append({"file": current["file"], "problem": "cursor does not match preceding response"})
            if previous["ids"] and current["ids"] and max(previous["ids"]) >= min(current["ids"]):
                errors.append({"file": current["file"], "problem": "non-increasing page ID boundary"})
        if pages[-1]["next_cursor"]:
            errors.append({"file": pages[-1]["file"], "problem": "final page still has next cursor"})
        sweeps.append({"tag_id": key[0], "exclude_tag_id": key[1], "pages": len(pages),
                       "rows": sum(p["rows"] for p in pages), "last_page_rows": pages[-1]["rows"],
                       "last_page_has_next_cursor": bool(pages[-1]["next_cursor"])})
    selected = [lookup[eid] for eid in sport]
    future = [{k: e[k] for k in ("id", "title", "sport_date", "date_basis", "url")}
              for e in selected if dt(e["sport_date"]) > retrieved]
    flag_errors = []
    for e in events:
        chosen = next(((k, dt(e["dates"][k])) for k in ("startTime", "eventDate", "slug_date", "endDate")
                       if e["dates"].get(k)), (None, None))
        if chosen[0] != e["date_basis"] or bool(chosen[1] and low <= chosen[1] < high) != e["in_sport_window"]:
            flag_errors.append(e["id"])
    game_ids = Counter(str(e["gameId"]) for e in selected if e.get("gameId"))
    long_example = next((x for x in audited.get("examples", []) if x["theme"] == "Long"), None)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "Offline, independent standard-library pass over saved event/market rows and every keyset raw page. No network requests. Known football exclusions copied as an explicit scope rule, not independently exhaustive semantic labels.",
        "reproduce": "Run src/eda/tennis_data_audit/independent_polymarket_qa.py with Python 3.11+ from any cwd. The research run selected C:/Users/zerom/miniforge3/envs/ufc-monitor/python.exe explicitly.",
        "source_files": [{"file": name, "sha256": hashlib.sha256((DATA / name).read_bytes()).hexdigest()}
                         for name in ("summary.json", "audited-summary.json", "events.jsonl", "markets.jsonl.gz", "request-manifest.json")],
        "research_window": {"start_inclusive": low.isoformat(), "end_exclusive": high.isoformat(),
                            "calendar_days": (high-low).days, "snapshot_finished_at": retrieved.isoformat(),
                            "note": "UTC dates include all of September 10 in both boundary years: 366 calendar days. First and last monthly bins are partial; the final day extends beyond snapshot time."},
        "counts": {"all_events": len(events), "unique_event_ids": len(lookup), "known_football_exclusions": len(excluded),
                   "sport_window_event_records": len(sport), "metadata_overlap_event_records": len(overlap),
                   "sport_without_overlap_events": len(sport - overlap), "overlap_without_sport_events": len(overlap - sport),
                   **dict(counts), "sport_unique_contract_ids": len(market_ids["sport"]),
                   "overlap_unique_attached_contract_ids": len(market_ids["overlap"]),
                   "overlap_attached_contracts_closed_before_window": len(closed_before),
                   "overlap_attached_closed_contracts_missing_closed_time": len(closed_missing),
                   "unique_nonmissing_game_ids": len(game_ids), "events_missing_game_id": sum(not e.get("gameId") for e in selected),
                   "repeated_game_id_groups": sum(n > 1 for n in game_ids.values()),
                   "sport_window_events_scheduled_after_snapshot": len(future)},
        "pagination": {"pages": sum(len(p) for p in page_groups.values()), "raw_event_rows": total_raw_rows,
                       "maximum_attached_markets_per_raw_event": maximum_attached_markets,
                       "sweeps": sweeps, "hash_cursor_or_order_errors": errors,
                       "limitation": "Terminal cursors and stable IDs validate the saved sweeps, not recovery of deleted or untagged events, nor temporal consistency of mutable metadata across requests."},
        "date_selection_reproduction_errors": flag_errors,
        "closed_before_window_contracts": closed_before,
        "closed_without_close_time_contracts": closed_missing,
        "future_at_snapshot_event_records": future,
        "semantic_notes": [
            "409313 refers to contracts attached to metadata-overlapping event wrappers; it is not a per-contract trading-overlap count. The 25 contracts already closed before the window demonstrate the distinction.",
            "The 33320 sport-window event records and 406190 contracts are not unique physical matches, executable quotations, completed matches, or in-window transactions.",
            "Volume fields in the snapshot report lifetime totals. Positive lifetime volume is not an in-window activity count.",
            "Neither gameId nor exact title alone identifies every physical match; missing and reused IDs and multiple market wrappers require cross-source entity resolution.",
            "Series labels are current provider classifications and their earliest sport date is not independently verified product launch or first trading time.",
            "The sports date prioritizes startTime, eventDate, slug date, then endDate. Date-only and endDate fallback rows remain weaker event-time evidence; endDate often has a seven-day administrative offset.",
            "The analyzer's substring example theme Long can match a player's name (Longo). It must not be cited as evidence of match-duration products."
        ],
        "long_substring_example": long_example,
    }
    target = DATA / "independent-qa.json"
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(target), "counts": result["counts"], "pagination_errors": errors,
                      "date_selection_errors": flag_errors}, indent=2))


if __name__ == "__main__":
    main()

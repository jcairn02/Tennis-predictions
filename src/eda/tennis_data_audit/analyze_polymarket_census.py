"""Offline classification and quality checks for the saved Gamma census.

Counts Gamma event records and contracts, not deduplicated physical matches.
Tour-series labels are deliberately not promoted to an ATP/WTA competition tier.
"""
from collections import Counter, defaultdict
from datetime import datetime
import gzip
import json
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/studies/tennis_data_audit/polymarket"
DOCS = ROOT / "docs/research/tennis-data-audit"


def dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def volume_value(record):
    for key in ("volumeNum", "volume"):
        if record.get(key) not in (None, ""):
            return float(record[key])
    return None


def series_label(e):
    series = {s["slug"] for s in e["series"]}
    if "itf" in series:
        return "ITF series"
    if "atp-doubles" in series:
        return "ATP doubles series"
    if "wta-doubles" in series:
        return "WTA doubles series"
    if "atp" in series:
        return "ATP series (includes lower tiers / qualifying)"
    if "wta" in series:
        return "WTA series (includes qualifying / WTA 125)"
    if "wimbledon" in series:
        return "Wimbledon series only"
    return "Legacy / other tennis (no recognized series)"


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    events = [json.loads(line) for line in (DATA / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len({e["id"] for e in events}) == len(events)
    excluded = [e for e in events if any(s["slug"] == "cfb-2025" for s in e["series"])
                or (e.get("sport") or {}).get("sport") == "cfb"]
    exclude_ids = {e["id"] for e in excluded}
    eligible = [e for e in events if e["in_sport_window"] and e["id"] not in exclude_ids]
    eligible_ids = {e["id"] for e in eligible}
    lookup = {e["id"]: e for e in events}
    markets = []
    overlap_markets = []
    with gzip.open(DATA / "markets.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            m = json.loads(line)
            if m["event_id"] in eligible_ids:
                markets.append(m)
            if lookup[m["event_id"]]["metadata_trading_overlap"] and m["event_id"] not in exclude_ids:
                overlap_markets.append(m)
    assert len({m["id"] for m in markets}) == len(markets)
    by_event = defaultdict(list)
    for m in markets:
        by_event[m["event_id"]].append(m)
    classes = []
    for label, count in Counter(series_label(e) for e in eligible).most_common():
        group = [e for e in eligible if series_label(e) == label]
        group_markets = [m for e in group for m in by_event[e["id"]]]
        classes.append({"label": label, "events": count, "contracts": len(group_markets),
                        "first_date": min(e["sport_date"] for e in group),
                        "positive_volume_events": sum(volume_value(e) is not None and volume_value(e) > 0 for e in group),
                        "example_url": min(group, key=lambda e: e["sport_date"])["url"]})
    monthly = []
    for month in sorted({e["sport_date"][:7] for e in eligible}):
        group = [e for e in eligible if e["sport_date"].startswith(month)]
        monthly.append({"month": month, "events": len(group), "contracts": sum(e["market_count"] for e in group),
                        "itf_series_events": sum(series_label(e) == "ITF series" for e in group),
                        "positive_volume_events": sum(volume_value(e) is not None and volume_value(e) > 0 for e in group)})
    types = []
    for kind, count in Counter(m["sportsMarketType"] or "not_set" for m in markets).most_common():
        group = [m for m in markets if (m["sportsMarketType"] or "not_set") == kind]
        first = min(group, key=lambda m: lookup[m["event_id"]]["sport_date"])
        types.append({"type": kind, "contracts": count,
                      "positive_volume_contracts": sum(volume_value(m) is not None and volume_value(m) > 0 for m in group),
                      "first_sport_date": lookup[first["event_id"]]["sport_date"],
                      "example_question": first["question"], "example_url": lookup[first["event_id"]]["url"] + "/" + first["slug"]})
    game_ids = Counter(str(e["gameId"]) for e in eligible if e.get("gameId"))
    grouped_titles = defaultdict(list)
    for e in eligible:
        grouped_titles[e["title"].strip().casefold()].append(e)
    duplicate_titles = [v for v in grouped_titles.values() if len(v) > 1]
    offsets = []
    for e in eligible:
        if e["dates"].get("startTime") and e["dates"].get("endDate"):
            offsets.append((dt(e["dates"]["endDate"]) - dt(e["dates"]["startTime"])).total_seconds() / 86400)
    examples = []
    for needle in ("ITF Hurghada", "Cassis:", "Japan Open Tennis Championships, Qualification", "Laver Cup", "Davis Cup", "Battle of the Sexes", "Six Kings", "Garden Cup", "Next Gen", "Break a Racket", "Dress Code", "Code Violation", "Longest Match", "To Reach"):
        group = [e for e in events if needle.casefold() in e["title"].casefold() and (e["in_sport_window"] or e["metadata_trading_overlap"]) and e["id"] not in exclude_ids]
        if group:
            e = group[0]
            examples.append({"theme": needle, "id": e["id"], "title": e["title"], "url": e["url"], "date": e["sport_date"], "date_basis": e["date_basis"]})
    overlap_only = [e for e in events if e["metadata_trading_overlap"] and not e["in_sport_window"] and e["id"] not in exclude_ids]
    metrics = {
        "all_discovered_events": len(events), "known_non_tennis_excluded": len(excluded),
        "sport_window_tennis_events": len(eligible), "sport_window_contracts": len(markets),
        "positive_lifetime_volume_events": sum(volume_value(e) is not None and volume_value(e) > 0 for e in eligible),
        "positive_lifetime_volume_contracts": sum(volume_value(m) is not None and volume_value(m) > 0 for m in markets),
        "zero_lifetime_volume_contracts": sum(volume_value(m) == 0 for m in markets),
        "missing_lifetime_volume_contracts": sum(volume_value(m) is None for m in markets),
        "missing_lifetime_volume_events": sum(volume_value(e) is None for e in eligible),
        "zero_lifetime_volume_events": sum(volume_value(e) == 0 for e in eligible),
        "metadata_overlap_tennis_events": sum(e["metadata_trading_overlap"] and e["id"] not in exclude_ids for e in events),
        "metadata_overlap_contracts": len(overlap_markets),
        "metadata_overlap_only_events": len(overlap_only),
        "date_basis": dict(Counter(e["date_basis"] for e in eligible)),
        "missing_game_id": sum(not e.get("gameId") for e in eligible), "unique_nonmissing_game_ids": len(game_ids),
        "repeated_game_id_groups": sum(n > 1 for n in game_ids.values()),
        "repeated_exact_title_groups": len(duplicate_titles),
        "startTime_vs_eventDate_utc_day_disagreements": sum(bool(e["dates"].get("startTime") and e["dates"].get("eventDate") and e["dates"]["startTime"][:10] != e["dates"]["eventDate"][:10]) for e in eligible),
        "median_endDate_minus_startTime_days": statistics.median(offsets),
        "endDate_minus_startTime_at_least_6days": sum(n >= 6 for n in offsets),
        "title_encoding_replacement_events": sum("\ufffd" in e["title"] for e in eligible),
        "closed_contracts_half_half_snapshot": sum(bool(m["closed"]) and m["outcomePrices"] == ["0.5", "0.5"] for m in markets),
        "missing_condition_id": sum(not m.get("conditionId") for m in markets),
        "missing_resolution_text": sum(not m.get("description") for m in markets),
        "bad_token_outcome_alignment": sum(len(m["outcomes"]) != len(m["clobTokenIds"]) for m in markets),
        "classes": classes, "monthly": monthly, "market_types": types, "examples": examples,
        "excluded": [{k:e[k] for k in ("id", "title", "url")} for e in excluded],
        "limitations": ["Counts are Gamma event records and contracts, not physical matches or in-window fills.",
                        "Series are product classifications; ATP series includes Challenger and qualifying events.",
                        "Positive volume is lifetime, and zero does not prove a price was never offered.",
                        "A complete sweep of discovered tags does not recover deleted or all untagged events.",
                        "Excluding nine confirmed football records is not a complete semantic audit of every title."]}
    assert metrics["positive_lifetime_volume_contracts"] + metrics["zero_lifetime_volume_contracts"] + metrics["missing_lifetime_volume_contracts"] == len(markets)
    (DATA / "audited-summary.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA / "overlap-only-events.json").write_text(json.dumps(overlap_only, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA / "excluded-non-tennis.json").write_text(json.dumps(excluded, indent=2, ensure_ascii=False), encoding="utf-8")
    # A readable league/name inventory, with IDs and full event links retained in JSONL.
    leagues = defaultdict(list)
    for e in eligible:
        league = (e.get("eventMetadata") or {}).get("league") or (e["title"].split(":")[0] if ":" in e["title"] else e["title"])
        leagues[league].append(e)
    lines = ["# Polymarket competition and event-family inventory", "",
             "Observed Gamma event records in the sporting-date window, after removing nine confirmed football records. Provider league labels and title prefixes are retained; they are not canonical tournament editions or proof of complete draw coverage. Counts include separate event wrappers, such as exact-score groups. Full event URLs, IDs, dates, series and tags are in the [event inventory](../../../data/studies/tennis_data_audit/polymarket/events.jsonl).", "",
             "| Gamma league / title family | Event records | Contracts | Earliest date | Latest date | Example |", "|---|---:|---:|---|---|---|"]
    for league, group in sorted(leagues.items(), key=lambda x:(-len(x[1]),x[0])):
        dates = sorted(e["sport_date"][:10] for e in group)
        lines.append(f"| {league.replace('|','/')} | {len(group):,} | {sum(e['market_count'] for e in group):,} | {dates[0]} | {dates[-1]} | [Market]({group[0]['url']}) |")
    (DOCS / "polymarket-competition-inventory.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in metrics.items() if k not in ("examples","excluded","classes","monthly","market_types")}, indent=2))


if __name__ == "__main__":
    main()

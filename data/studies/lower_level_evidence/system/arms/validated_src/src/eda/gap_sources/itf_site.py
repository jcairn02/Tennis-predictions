"""Lane C1 of the gap-sources study: what the official ITF World Tennis Tour listings hold (29 Sep 2026).

Two official routes were examined:

* itftennis.com, the ITF website. Its draw pages are React components that call
  /tennis/api/TournamentApi/GetEventFilters and /tennis/api/TournamentApi/GetDrawsheet. Imperva
  (Incapsula) sits in front. GetEventFilters answered 200 JSON; the first GetDrawsheet request answered
  HTTP 403 with an Incapsula incident page, so no further request was sent to that host (see itf_http.py).
* api.itf-production.sports-data.stadion.io, the live-data API behind the ITF's "World Tennis Tour Live"
  and "Live Match Centre" pages (the widget SDK the ITF pages load, widgets.itf-production.sports-data
  .stadion.io/itf-widget-sdk.umd.js). No credentials are sent by the SDK for these calls and none are sent
  here. Its day list (custom/wttCompleteMatchList/<date>) answers only for dates within 14 days of today
  (HTTP 422 "date must be within 14 days of today" otherwise). Older day lists exist only as Internet
  Archive captures, which are read here too.

Subcommands (all requests paced and receipted by itf_http.Fetcher; cached bodies are reused):
    fetch-live     day lists for --start..--end (default: the 15 days ending 29 Sep 2026)
    fetch-wayback  every archived day list, match card, match statistics and drawsheet capture in the CDX files
    fetch-detail   statistics and point-by-point for two singles matches (one qualifying) per sampled event
    fetch-stats    statistics only for up to 4 qualifying and 4 main-draw singles matches per sampled live event
    build          writes data/studies/gap_sources/itf_site_events.csv (sampled events) and
                   itf_site_summary.json (window facts, per-week totals, block facts)

Usage: ./python.sh src/eda/gap_sources/itf_site.py {fetch-live,fetch-wayback,fetch-detail,build}
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import itf_http as H  # noqa: E402

STADION = "https://api.itf-production.sports-data.stadion.io/"
STADION_HOST = "api.itf-production.sports-data.stadion.io"
LIVE_DIR = H.RAW / "other" / STADION_HOST
WAYBACK_DIR = H.RAW / "other" / "web.archive.org"
OUT = H.ROOT / "data" / "studies" / "gap_sources"
EVENTS_CSV = OUT / "itf_site_events.csv"
SUMMARY_JSON = OUT / "itf_site_summary.json"

RESULT_STATUSES = {"complete", "walkover", "retired", "default", "defaulted", "abandoned"}
EVENT_FIELDS = ["sample_group", "tour", "grade", "event_name", "city", "country", "itf_tournament_key",
                "stadion_event_id", "start_date", "end_date", "iso_week_main_draw", "surface", "source",
                "list_dates", "window_complete", "qualifying_singles_listed", "qualifying_singles_with_result",
                "main_singles_listed", "main_singles_with_result", "main_singles_expected",
                "main_singles_live_streamed", "doubles_listed", "stats_qualifying_checked",
                "stats_qualifying_with_values", "stats_main_checked", "stats_main_with_values", "stat_types_seen",
                "core_serve_stats_seen", "pbp_matches_checked", "pbp_matches_with_points", "notes"]
CORE_STATS = ["Aces", "Double Faults", "Serve Points Played", "First Serve Percentage", "First Serve Points Won",
              "Second Serve Points Won", "Break Points Saved", "Serve Games Played"]


# ----------------------------------------------------------------------------------------------- fetching
def day_list_url(day: str) -> str:
    return f"{STADION}custom/wttCompleteMatchList/{day}"


def cmd_fetch_live(args) -> None:
    f = H.Fetcher(budget=args.budget)
    d, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    while d <= end:
        day = d.isoformat()
        r, _ = f.get(f"wttCompleteMatchList_{day}.json", day_list_url(day), expect="json")
        print(day, r.get("status"), r.get("bytes"), "cached" if r.get("cached") else "")
        d += timedelta(days=1)
    print("requests:", f.requests)


def wayback_rows(cdx_name: str) -> list[list[str]]:
    path = WAYBACK_DIR / cdx_name
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    return rows[1:]


def wayback_name(prefix: str, ts: str, original: str) -> str:
    tail = original.split(".io/", 1)[-1].split(".com/", 1)[-1]
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in tail)[:150]
    return f"{prefix}/{safe}__{ts}.json"


def cmd_fetch_wayback(args) -> None:
    f = H.Fetcher(budget=args.budget)
    todo = []
    for ts, original, status in ((r[1], r[2], r[4]) for r in wayback_rows("cdx_stadion_api.json")):
        tail = original.split("stadion.io/", 1)[-1]
        if status == "200" and tail.startswith(("custom/wttCompleteMatchList/", "custom/widgetMatchStats/",
                                                "custom/widgetMatch/")):
            todo.append(("stadion", ts, original))
    for ts, original, status, mime in ((r[1], r[2], r[4], r[3]) for r in wayback_rows("cdx_getdrawsheet.json")):
        if status == "200" and ts[:4] in ("2022", "2023", "2024") and ts in ("20220210004149", "20230902134937",
                                                                             "20240123050654"):
            todo.append(("itftennis", ts, original))
    for group, ts, original in todo:
        url = f"https://web.archive.org/web/{ts}id_/{original}"
        expect = "binary" if group == "itftennis" else "json"
        r, _ = f.get(wayback_name(group, ts, original), url, expect=expect)
        print(group, ts, original[-70:], r.get("status"), r.get("bytes"), "cached" if r.get("cached") else "")
    print("requests:", f.requests)


def cmd_fetch_stats(args) -> None:
    """Statistics only, for the wider per-event sample of the live window's sampled events."""
    f = H.Fetcher(budget=args.budget)
    for ev in sample_live_events(load_live_matches()):
        if not ev["complete"]:
            continue
        for m in stats_sample(ev):
            r, _ = f.get(f"widgetMatchStats/{m['id']}.json", f"{STADION}custom/widgetMatchStats/{m['id']}", expect="json")
            print(ev["tennisId"], m["draw"], m["round"], r.get("status"), r.get("bytes"), "cached" if r.get("cached") else "")
    print("requests:", f.requests)


def main_draw_check_2025(wb_rows: list[dict]) -> list[dict]:
    """Three women's and three men's completed main-draw singles matches from the archived day lists of
    2025-01-30 and 2025-05-16 (the Monday captures hold qualifying only), ids ordered, one per event."""
    out = []
    for gender in ("women", "men"):
        for day, n in (("2025-01-30", 1), ("2025-05-16", 2)):
            seen = set()
            pool = sorted((m for m in dedupe(wb_rows).values() if m["list_date"] == day and m["gender"] == gender
                           and (m["type"] or "").lower() == "singles" and m["result"]
                           and (m["draw"] or "").lower().startswith("main")
                           and (m["status"] or "").lower() != "walkover"), key=lambda m: m["id"])
            for m in pool:
                if m["tennisId"] not in seen and len(seen) < n:
                    seen.add(m["tennisId"])
                    out.append(m)
    return out


def cmd_fetch_detail(args) -> None:
    events = sample_live_events(load_live_matches()) + [e for e, _day in sample_wayback_events(load_wayback_matches())]
    f = H.Fetcher(budget=args.budget)
    extra = [{"tennisId": m["tennisId"], "matches": [m]} for m in main_draw_check_2025(load_wayback_matches())]
    for ev in events + extra:
        for m in (detail_matches(ev) if "event_id" in ev else ev["matches"]):
            for kind in ("widgetMatchStats", "pointByPoint"):
                r, _ = f.get(f"{kind}/{m['id']}.json", f"{STADION}custom/{kind}/{m['id']}", expect="json")
                print(ev["tennisId"], m["draw"], m["round"], kind, r.get("status"), r.get("bytes"),
                      "cached" if r.get("cached") else "")
    print("requests:", f.requests)


# ----------------------------------------------------------------------------------------------- parsing
def status_name(m: dict) -> str:
    return ((m.get("matchStatus") or {}).get("_name") or "").strip()


def has_result(m: dict) -> bool:
    return bool(m.get("winnerSideId")) or status_name(m).lower() in RESULT_STATUSES


def flatten_day(doc: dict, *, source: str, list_date: str, captured: str | None) -> list[dict]:
    rows = []
    for _key, t in (doc.get("data") or {}).items():
        ev = {k: v for k, v in t.items() if k != "courts"}
        for court, matches in (t.get("courts") or {}).items():
            for m in matches or []:
                disc = m.get("_drawDiscipline") or {}
                rows.append({
                    "source": source, "list_date": list_date, "captured": captured,
                    "event_name": ev.get("_name"), "tennisId": ev.get("tennisId"), "event_id": ev.get("id"),
                    "start": (ev.get("startDate") or "")[:10], "end": (ev.get("endDate") or "")[:10],
                    "grade": ((ev.get("eventCategory") or {}).get("type") or "").upper(),
                    "surface": (ev.get("surface") or {}).get("_name"),
                    "country": ((ev.get("venue") or {}).get("country") or {}).get("_name"),
                    "id": m.get("id"), "match_tennisId": m.get("tennisId"),
                    "gender": disc.get("gender"), "type": disc.get("type"), "draw": m.get("_drawName"),
                    "round": m.get("_roundName"), "status": status_name(m), "result": has_result(m),
                    "streamed": bool(m.get("isLiveStreamed")), "day": m.get("dateStartLocal"),
                })
    return rows


def load_live_matches() -> list[dict]:
    rows = []
    for path in sorted(LIVE_DIR.glob("wttCompleteMatchList_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if "data" not in doc:
            continue  # the 422 answers for dates outside the window
        rows += flatten_day(doc, source="stadion_live", list_date=path.stem.split("_")[-1], captured=None)
    return rows


def load_wayback_matches() -> list[dict]:
    rows = []
    for path in sorted((WAYBACK_DIR / "stadion").glob("custom_wttCompleteMatchList_*.json")):
        stem = path.stem  # custom_wttCompleteMatchList_2025-03-17__20250323034420
        list_date, ts = stem.split("_")[-3], stem.split("__")[-1]
        doc = json.loads(path.read_text(encoding="utf-8"))
        rows += flatten_day(doc, source="stadion_wayback", list_date=list_date, captured=ts)
    return rows


def dedupe(rows: list[dict]) -> dict[str, dict]:
    """One row per match id; a match listed on several days keeps its last-listed state."""
    out: dict[str, dict] = {}
    for r in sorted(rows, key=lambda r: (r["list_date"], r["captured"] or "")):
        out[r["id"]] = r
    return out


def city_of(name: str) -> str:
    parts = (name or "").split(" ", 1)
    return parts[1] if len(parts) == 2 and parts[0][:1] in "MW" and parts[0][1:].isdigit() else name


def iso_week(day: str) -> str:
    y, w, _ = date.fromisoformat(day).isocalendar()
    return f"{y}-W{w:02d}"


def main_draw_week(start: str) -> str:
    """ITF events are listed from their qualifying weekend; the main draw's ISO week is that of start + 2 days."""
    return iso_week((date.fromisoformat(start) + timedelta(days=2)).isoformat())


def events_of(matches: dict[str, dict]) -> dict[str, dict]:
    evs: dict[str, dict] = {}
    for m in matches.values():
        e = evs.setdefault(m["tennisId"], {"tennisId": m["tennisId"], "event_id": m["event_id"],
                                            "event_name": m["event_name"], "grade": m["grade"],
                                            "start": m["start"], "end": m["end"], "surface": m["surface"],
                                            "country": m["country"], "matches": [], "list_dates": set()})
        e["matches"].append(m)
        e["list_dates"].add(m["list_date"])
    for e in evs.values():
        genders = Counter(m["gender"] for m in e["matches"])
        e["tour"] = "W" if genders.get("women", 0) >= genders.get("men", 0) else "M"
    return evs


def counts(e: dict) -> dict:
    sing = [m for m in e["matches"] if (m["type"] or "").lower() == "singles"]
    q = [m for m in sing if "qualif" in (m["draw"] or "").lower()]
    md = [m for m in sing if (m["draw"] or "").lower().startswith("main")]
    return {"qualifying_singles_listed": len(q), "qualifying_singles_with_result": sum(m["result"] for m in q),
            "main_singles_listed": len(md), "main_singles_with_result": sum(m["result"] for m in md),
            "main_singles_live_streamed": sum(m["streamed"] for m in md),
            "doubles_listed": sum((m["type"] or "").lower() == "doubles" for m in e["matches"])}


def window_dates(live: list[dict]) -> tuple[str, str]:
    days = sorted({r["list_date"] for r in live})
    return days[0], days[-1]


def sample_live_events(live_rows: list[dict]) -> list[dict]:
    """Grade-spread picks per tour: 4 events whose whole week (qualifying weekend to final) lies inside the
    window (main draws in ISO week 39, 21-27 Sep 2026), then 2 events of ISO week 38 (14-20 Sep), the last
    week of the gap, whose qualifying and Monday matches fall before the window. Each event gets a
    ``group`` and ``complete`` flag."""
    evs = events_of(dedupe(live_rows))
    first, last = window_dates(live_rows)
    chosen = []
    for week, n, complete in (("2026-W39", 4, True), ("2026-W38", 2, False)):
        for tour in ("W", "M"):
            pool = sorted((e for e in evs.values() if e["tour"] == tour and e["tennisId"]
                           and main_draw_week(e["start"]) == week and e["end"] <= last
                           and (not complete or first <= e["start"])),
                          key=lambda e: (-int(e["grade"][1:] or 0), e["event_name"]))
            idx = sorted({round(i * (len(pool) - 1) / max(n - 1, 1)) for i in range(n)}) if pool else []
            for i in idx:
                chosen.append({**pool[i], "group": f"{'women' if tour == 'W' else 'men'}_2026_{week[-3:].lower()}",
                               "complete": complete})
    return chosen


def sample_wayback_events(wb_rows: list[dict]) -> list[tuple[dict, str]]:
    """6 women's and 3 men's 2025 events, grade-spread picks among those listed on the archived Mondays
    2025-03-17 and 2025-06-09 (qualifying days, so these single-day views show qualifying draws)."""
    evs = events_of(dedupe(wb_rows))
    by_day = defaultdict(list)
    for e in evs.values():
        if e["tennisId"]:
            for d in e["list_dates"]:
                by_day[d].append(e)
    picks = {"W": {"2025-03-17": 3, "2025-06-09": 3}, "M": {"2025-03-17": 2, "2025-06-09": 1}}
    out = []
    for tour, plan in picks.items():
        for day, n in plan.items():
            pool = sorted((e for e in by_day.get(day, []) if e["tour"] == tour),
                          key=lambda e: (-int(e["grade"][1:] or 0), e["event_name"]))
            idx = sorted({round(i * (len(pool) - 1) / max(n - 1, 1)) for i in range(n)}) if pool else []
            out += [(pool[i], day) for i in idx]
    return out


def detail_matches(ev: dict) -> list[dict]:
    """One completed qualifying singles match and one completed main-draw singles match (a streamed one if any)."""
    sing = [m for m in ev["matches"] if (m["type"] or "").lower() == "singles" and m["result"]]
    q = sorted((m for m in sing if "qualif" in (m["draw"] or "").lower()), key=lambda m: m["id"])
    md = sorted((m for m in sing if (m["draw"] or "").lower().startswith("main")),
                key=lambda m: (not m["streamed"], m["id"]))
    return [x for x in (q[:1] + md[:1])]


def stats_sample(ev: dict, per_draw: int = 4) -> list[dict]:
    """The detail matches plus up to ``per_draw`` completed singles matches per draw, one per round in turn
    (rounds cycled from the first), ids ordered, so the statistics check spans early and late rounds."""
    chosen = {m["id"]: m for m in detail_matches(ev)}
    sing = [m for m in ev["matches"] if (m["type"] or "").lower() == "singles" and m["result"]
            and (m["status"] or "").lower() != "walkover"]
    for draw_test in (lambda d: "qualif" in d, lambda d: d.startswith("main")):
        pool = [m for m in sing if draw_test((m["draw"] or "").lower())]
        by_round = defaultdict(list)
        for m in sorted(pool, key=lambda m: m["id"]):
            by_round[m["round"]].append(m)
        rounds = sorted(by_round, key=lambda r: -len(by_round[r]))  # earliest (largest) round first
        picked = [m for m in chosen.values() if m in pool]
        i = 0
        while len(picked) < per_draw and any(by_round.values()):
            r = rounds[i % len(rounds)]
            if by_round[r]:
                m = by_round[r].pop(0)
                if m["id"] not in chosen:
                    chosen[m["id"]] = m
                    picked.append(m)
            i += 1
    return list(chosen.values())


def stats_of(match_id: str) -> tuple[bool | None, list[str], bool | None]:
    """(stats present with values, stat names, point-by-point present) from the saved detail responses."""
    sp, pp = LIVE_DIR / "widgetMatchStats" / f"{match_id}.json", LIVE_DIR / "pointByPoint" / f"{match_id}.json"
    has_stats, names, has_pbp = None, [], None
    if sp.exists():
        doc = json.loads(sp.read_text(encoding="utf-8"))
        items = doc.get("data") or []
        names = sorted({i.get("_name") for i in items if isinstance(i, dict) and i.get("_name")})
        has_stats = any(stat_value_present(i) for i in items if isinstance(i, dict))
    if pp.exists():
        doc = json.loads(pp.read_text(encoding="utf-8"))
        has_pbp = any((side.get("points") or []) for st in (doc.get("data") or []) for g in (st.get("games") or [])
                      for side in (g.get("sides") or []))
    return has_stats, names, has_pbp


def stats_columns(matches: list[dict]) -> dict:
    """Statistics and point-by-point coverage over the matches whose detail responses were saved."""
    out = Counter()
    names: set[str] = set()
    for m in matches:
        has_stats, ns, has_pbp = stats_of(m["id"])
        draw = "qualifying" if "qualif" in (m["draw"] or "").lower() else "main"
        if has_stats is not None:
            out[f"stats_{draw}_checked"] += 1
            out[f"stats_{draw}_with_values"] += int(bool(has_stats))
            names |= set(ns)
        if has_pbp is not None:
            out["pbp_matches_checked"] += 1
            out["pbp_matches_with_points"] += int(bool(has_pbp))
    return {"stats_qualifying_checked": out["stats_qualifying_checked"],
            "stats_qualifying_with_values": out["stats_qualifying_with_values"],
            "stats_main_checked": out["stats_main_checked"], "stats_main_with_values": out["stats_main_with_values"],
            "stat_types_seen": len(names), "core_serve_stats_seen": "; ".join(c for c in CORE_STATS if c in names),
            "pbp_matches_checked": out["pbp_matches_checked"],
            "pbp_matches_with_points": out["pbp_matches_with_points"]}


def stat_value_present(item: dict) -> bool:
    for side in item.get("sides") or item.get("values") or []:
        if isinstance(side, dict):
            v = side.get("value") if "value" in side else side.get("valueDisplay")
            if v not in (None, "", "0", 0, "0%", "0/0"):
                return True
    for k in ("valueDisplay", "value"):
        if item.get(k) not in (None, "", "0", 0):
            return True
    return False


def expected_main(grade: str) -> int:
    """Singles main draws are 32 players at every WTT grade (31 matches); W100 events too (Regulations 2026)."""
    return 31


# ----------------------------------------------------------------------------------------------- build
def cmd_build(args) -> None:
    live = load_live_matches()
    wb = load_wayback_matches()
    first, last = window_dates(live)
    live_matches = dedupe(live)
    live_events = events_of(live_matches)

    rows = []
    for ev in sample_live_events(live):
        c = counts(ev)
        rows.append({
            "sample_group": ev["group"], "tour": ev["tour"],
            "grade": ev["grade"], "event_name": ev["event_name"], "city": city_of(ev["event_name"]),
            "country": ev["country"], "itf_tournament_key": ev["tennisId"], "stadion_event_id": ev["event_id"],
            "start_date": ev["start"], "end_date": ev["end"], "iso_week_main_draw": main_draw_week(ev["start"]),
            "surface": ev["surface"], "source": "stadion live day lists (ITF World Tennis Tour Live API)",
            "list_dates": f"{min(ev['list_dates'])}..{max(ev['list_dates'])}", "window_complete": ev["complete"], **c,
            "main_singles_expected": expected_main(ev["grade"]),
            **stats_columns(stats_sample(ev) if ev["complete"] else detail_matches(ev)),
            "notes": ("statistics checked on up to 4 qualifying and 4 main-draw matches; point-by-point on 2"
                      if ev["complete"] else "week 38: qualifying (12-14 Sep) precedes the 14-day window, so the "
                      "qualifying count is partial" + (" (the main draw is complete)" if c["main_singles_with_result"]
                                                       >= expected_main(ev["grade"]) else "; main draw partial too")
                      + "; statistics and point-by-point checked on one or two matches")})

    # 2025 events: single-day Internet Archive captures of the same day list.
    wb_matches = dedupe(wb)
    for e, day in sample_wayback_events(wb):
        day_matches = {"matches": [m for m in e["matches"] if m["list_date"] == day]}
        c = counts(day_matches)
        cap = sorted({m["captured"] for m in day_matches["matches"]})
        tour = e["tour"]
        rows.append({
            "sample_group": f"{'women' if tour == 'W' else 'men'}_2025", "tour": tour, "grade": e["grade"],
            "event_name": e["event_name"], "city": city_of(e["event_name"]), "country": e["country"],
            "itf_tournament_key": e["tennisId"], "stadion_event_id": e["event_id"], "start_date": e["start"],
            "end_date": e["end"], "iso_week_main_draw": main_draw_week(e["start"]), "surface": e["surface"],
            "source": f"Internet Archive capture {','.join(cap)} of the day list for {day}",
            "list_dates": day, "window_complete": False, **c, "main_singles_expected": expected_main(e["grade"]),
            **stats_columns(detail_matches(e)),
            "notes": "one day of the event only (the capture); full draw counts not determined; "
                     "statistics and point-by-point read from the live API on 29 Sep 2026"})

    OUT.mkdir(parents=True, exist_ok=True)
    with EVENTS_CSV.open("w", newline="", encoding="utf-8") as handle:
        w = csv.DictWriter(handle, fieldnames=EVENT_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in EVENT_FIELDS})

    # Totals over the live window, by main-draw ISO week and tour (singles only).
    weekly = defaultdict(Counter)
    for m in live_matches.values():
        if (m["type"] or "").lower() != "singles":
            continue
        e = live_events[m["tennisId"]]
        k = (main_draw_week(e["start"]), e["tour"])
        weekly[k]["events"] += 0
        draw = "qualifying" if "qualif" in (m["draw"] or "").lower() else "main"
        weekly[k][f"{draw}_listed"] += 1
        weekly[k][f"{draw}_with_result"] += int(m["result"])
    for (wk, tour) in weekly:
        weekly[(wk, tour)]["events"] = sum(1 for e in live_events.values()
                                           if main_draw_week(e["start"]) == wk and e["tour"] == tour)
    wb_days = defaultdict(Counter)
    for m in wb_matches.values():
        if (m["type"] or "").lower() != "singles":
            continue
        draw = "qualifying" if "qualif" in (m["draw"] or "").lower() else "main"
        wb_days[(m["list_date"], m["gender"])][f"{draw}_listed"] += 1
        wb_days[(m["list_date"], m["gender"])][f"{draw}_with_result"] += int(m["result"])
    for (d, g) in list(wb_days):
        wb_days[(d, g)]["events"] = len({m["tennisId"] for m in wb_matches.values()
                                         if m["list_date"] == d and m["gender"] == g})
    receipts = H.load_receipts()
    blocked = H.read_json_file(H.BLOCKED, {})
    summary = {
        "built_at": H.utc_now(),
        "itftennis_com": {
            "robots_txt": "User-agent: * / Disallow: /umbraco/ / Allow: / (fetched 2026-09-29)",
            "front": "Imperva (x-cdn: Imperva; visid_incap/incap_ses/nlbi cookies; ABP script on pages)",
            "requests": {k: {x: v.get(x) for x in ("url", "status", "bytes", "retrieved_at", "problem")}
                         for k, v in receipts.items() if urlsplit(v.get("url", "")).hostname == H.ITF_HOST},
            "api_endpoints_in_page_bundle": "31 /tennis/api/* paths in bundle.js, e.g. TournamentApi/GetCalendar, "
                                            "GetEventFilters, GetDrawsheet, GetOrderOfPlay, PlayerApi/GetPlayerActivity",
            "drawsheet_parameters": "circuitCode (MT/WT), eventClassificationCode (M main, Q qualifying), matchTypeCode "
                                    "(S/D), tournamentId (numeric, from GetEventFilters), tourType (N), weekNumber=0",
            "blocked": blocked.get(H.ITF_HOST),
        },
        "wayback_cdx": {
            "itftennis_GetDrawsheet_captures": len(wayback_rows("cdx_getdrawsheet.json")),
            "itftennis_GetDrawsheet_captures_with_parameters": sum("?" in r[2] for r in wayback_rows("cdx_getdrawsheet.json")),
            "stadion_api_captures": len(wayback_rows("cdx_stadion_api.json")),
            "stadion_day_list_captures": sorted(r[2].rsplit("/", 1)[-1] + " (captured " + r[1][:8] + ")"
                                                for r in wayback_rows("cdx_stadion_api.json")
                                                if "wttCompleteMatchList/" in r[2] and r[4] == "200"),
        },
        "stadion_live_window": {"first_list_date": first, "last_list_date": last,
                                "out_of_window_answer": "HTTP 422 'date must be within 14 days of today'",
                                "matches": len(live_matches), "events": len(live_events)},
        "stadion_live_by_main_draw_week": {f"{wk} {tour}": dict(c) for (wk, tour), c in sorted(weekly.items())},
        "stadion_wayback_days": {f"{d} {g}": dict(c) for (d, g), c in sorted(wb_days.items())},
        "sampled_events": len(rows),
        "main_draw_2025_statistics_check": [
            {"list_date": m["list_date"], "event": m["event_name"], "itf_tournament_key": m["tennisId"],
             "round": m["round"], "match_id": m["id"], "match_tennisId": m["match_tennisId"],
             **dict(zip(("stats_with_values", "stat_names", "pbp_with_points"), stats_of(m["id"])))}
            for m in main_draw_check_2025(wb)],
    }
    for item in summary["main_draw_2025_statistics_check"]:
        item["stat_names"] = len(item["stat_names"])
    SUMMARY_JSON.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {H.rel(EVENTS_CSV) if hasattr(H, 'rel') else EVENTS_CSV} ({len(rows)} rows) and {SUMMARY_JSON}")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("fetch-live")
    a.add_argument("--start", default="2026-09-15")
    a.add_argument("--end", default="2026-09-29")
    a.add_argument("--budget", type=int, default=40)
    b = sub.add_parser("fetch-wayback")
    b.add_argument("--budget", type=int, default=40)
    c = sub.add_parser("fetch-detail")
    c.add_argument("--budget", type=int, default=40)
    c2 = sub.add_parser("fetch-stats")
    c2.add_argument("--budget", type=int, default=60)
    sub.add_parser("build")
    args = p.parse_args()
    try:
        {"fetch-live": cmd_fetch_live, "fetch-wayback": cmd_fetch_wayback, "fetch-detail": cmd_fetch_detail,
         "fetch-stats": cmd_fetch_stats, "build": cmd_build}[args.cmd](args)
    except H.Blocked as err:
        print("STOPPED (blocked):", err)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

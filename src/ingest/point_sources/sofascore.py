"""SofaScore: a player's whole match list, then every singles match's point-by-point record and box score.

Endpoints (public JSON behind SofaScore's own site; no key):
    https://api.sofascore.com/api/v1/team/<team_id>/events/last/<page>   30 events per page, newest first,
                                                                          ``hasNextPage``; the page after the last is HTTP 404
    https://api.sofascore.com/api/v1/event/<event_id>/point-by-point     sets -> games -> point states (HTTP 404 when none)
    https://api.sofascore.com/api/v1/event/<event_id>/statistics         serve/return box score by period (HTTP 404 when none)
    https://api.sofascore.com/api/v1/event/<event_id>                    event detail (venue, per-set durations); optional

Raw layout under data/raw/point_sources/sofascore/:
    teams/<team_id>/events_last_<page>.json      listing pages (refetched with --refresh-listings: pages are
                                                 offsets from the newest match, so they shift as matches are added)
    events/<event_id>/point-by-point.json        present only when the record exists
    events/<event_id>/statistics.json
    events/<event_id>/event.json                 with --with-detail
    _receipts.jsonl                              one line per fetch, HTTP 404 included

Staged (data/dump/points/sofascore/): events.parquet, points.parquet, statistics.parquet, all strings.
Summary: data/studies/point_shot_sources/scrape/sofascore_summary.json.

Usage:
    ./python.sh -m src.ingest.point_sources.sofascore                       # the ten career-coverage players
    ./python.sh -m src.ingest.point_sources.sofascore --team-ids 105607,210033 --since-year 2022
    ./python.sh -m src.ingest.point_sources.sofascore --limit 20 --max-requests 60   # dry run
    ./python.sh -m src.ingest.point_sources.sofascore --stage-only         # rebuild Parquet from the raw files

Point record shape, as observed (24 Sep 2026): sets are listed last-first and games last-first; the points
of a game are chronological score states *after* each point, the game-winning point being implied
(the game's ``score.scoring`` names the winner) except in tiebreaks, where the final state is listed;
``score.serving`` is the server (1 home, 2 away); ``homePointType``/``awayPointType`` and
``pointDescription`` are undocumented integer codes and are kept verbatim.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P

SOURCE = "sofascore"
API = "https://api.sofascore.com/api/v1"
IMPERSONATE = "chrome"
HEADERS = {"Accept": "*/*", "Referer": "https://www.sofascore.com/", "Origin": "https://www.sofascore.com"}
MAX_PAGES = 200  # safety stop per team: 6,000 events
REGULAR_POINTS = {"0", "15", "30", "40", "A"}

EVENT_COLUMNS = [
    "event_id", "custom_id", "slug", "start_timestamp", "start_utc", "tournament_id", "tournament_name",
    "unique_tournament_id", "unique_tournament_name", "category_id", "category_name", "category_slug",
    "season_id", "season_name", "season_year", "round", "round_name", "round_slug", "cup_round_type",
    "status_code", "status_type", "status_description", "winner_code", "first_to_serve", "ground_type",
    "final_result_only", "feed_locked", "filter_category", "filter_tournament", "filter_level",
    "home_id", "home_name", "home_slug", "home_type", "home_country", "home_ranking", "home_seed", "home_sub_ids",
    "away_id", "away_name", "away_slug", "away_type", "away_country", "away_ranking", "away_seed", "away_sub_ids",
    "home_sets", "away_sets", "home_set1", "away_set1", "home_set2", "away_set2", "home_set3", "away_set3",
    "home_set4", "away_set4", "home_set5", "away_set5", "home_tb1", "away_tb1", "home_tb2", "away_tb2",
    "home_tb3", "away_tb3", "home_tb4", "away_tb4", "home_tb5", "away_tb5", "time_set1", "time_set2",
    "time_set3", "time_set4", "time_set5", "listed_for_teams", "listed_pages", "doubles",
    "pbp_status", "pbp_sets", "pbp_games", "pbp_points", "pbp_retrieved_at", "pbp_sha256",
    "stats_status", "stats_periods", "stats_retrieved_at", "stats_sha256", "listing_file",
]
POINT_COLUMNS = ["event_id", "set", "game", "point", "home_point", "away_point", "point_description",
                 "home_point_type", "away_point_type", "game_home_score", "game_away_score", "serving", "scoring",
                 "tiebreak", "set_index", "game_index", "source_file", "source_sha256", "retrieved_at"]
STAT_COLUMNS = ["event_id", "period", "group", "key", "name", "home", "away", "home_value", "away_value",
                "compare_code", "statistics_type", "value_type", "render_type", "source_file", "source_sha256",
                "retrieved_at"]


# --------------------------------------------------------------------------------------
# parsing (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def is_doubles(event: dict) -> bool:
    home, away = event.get("homeTeam") or {}, event.get("awayTeam") or {}
    return bool(home.get("subTeams") or away.get("subTeams") or home.get("type") == 2 or away.get("type") == 2)


def flatten_event(event: dict) -> dict:
    """The listing fields of one event as flat strings (see EVENT_COLUMNS)."""
    g = lambda d, *keys: _dig(d, keys)
    home, away = event.get("homeTeam") or {}, event.get("awayTeam") or {}
    hs, as_ = event.get("homeScore") or {}, event.get("awayScore") or {}
    tm = event.get("time") or {}
    filters = event.get("eventFilters") or {}
    ts = event.get("startTimestamp")
    row = {
        "event_id": event.get("id"), "custom_id": event.get("customId"), "slug": event.get("slug"),
        "start_timestamp": ts,
        "start_utc": dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else None,
        "tournament_id": g(event, "tournament", "id"), "tournament_name": g(event, "tournament", "name"),
        "unique_tournament_id": g(event, "tournament", "uniqueTournament", "id"),
        "unique_tournament_name": g(event, "tournament", "uniqueTournament", "name"),
        "category_id": g(event, "tournament", "category", "id"),
        "category_name": g(event, "tournament", "category", "name"),
        "category_slug": g(event, "tournament", "category", "slug"),
        "season_id": g(event, "season", "id"), "season_name": g(event, "season", "name"),
        "season_year": g(event, "season", "year"),
        "round": g(event, "roundInfo", "round"), "round_name": g(event, "roundInfo", "name"),
        "round_slug": g(event, "roundInfo", "slug"), "cup_round_type": g(event, "roundInfo", "cupRoundType"),
        "status_code": g(event, "status", "code"), "status_type": g(event, "status", "type"),
        "status_description": g(event, "status", "description"),
        "winner_code": event.get("winnerCode"), "first_to_serve": event.get("firstToServe"),
        "ground_type": event.get("groundType"), "final_result_only": event.get("finalResultOnly"),
        "feed_locked": event.get("feedLocked"),
        "filter_category": ";".join(filters.get("category") or []) or None,
        "filter_tournament": ";".join(filters.get("tournament") or []) or None,
        "filter_level": ";".join(filters.get("level") or []) or None,
        "home_sets": hs.get("current"), "away_sets": as_.get("current"),
        "doubles": is_doubles(event),
    }
    for side, team in (("home", home), ("away", away)):
        row[f"{side}_id"] = team.get("id")
        row[f"{side}_name"] = team.get("name")
        row[f"{side}_slug"] = team.get("slug")
        row[f"{side}_type"] = team.get("type")
        row[f"{side}_country"] = g(team, "country", "alpha3") or g(team, "country", "name")
        row[f"{side}_ranking"] = team.get("ranking")
        row[f"{side}_seed"] = event.get(f"{side}TeamSeed")
        row[f"{side}_sub_ids"] = ";".join(str(t.get("id")) for t in team.get("subTeams") or []) or None
    for n in range(1, 6):
        row[f"home_set{n}"] = hs.get(f"period{n}")
        row[f"away_set{n}"] = as_.get(f"period{n}")
        row[f"home_tb{n}"] = hs.get(f"period{n}TieBreak")
        row[f"away_tb{n}"] = as_.get(f"period{n}TieBreak")
        row[f"time_set{n}"] = tm.get(f"period{n}")
    return row


def _dig(d, keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def point_rows(event_id, pbp: list) -> list[dict]:
    """One row per listed point state, in match order (sets and games ascending)."""
    rows = []
    sets = sorted(pbp, key=lambda x: _num(x.get("set")))
    for set_index, st in enumerate(sets, 1):
        games = sorted(st.get("games") or [], key=lambda x: _num(x.get("game")))
        for game_index, game in enumerate(games, 1):
            score = game.get("score") or {}
            points = game.get("points") or []
            tiebreak = any(str(p.get("homePoint")) not in REGULAR_POINTS or str(p.get("awayPoint")) not in REGULAR_POINTS
                           for p in points)
            for n, p in enumerate(points, 1):
                rows.append({
                    "event_id": event_id, "set": st.get("set"), "game": game.get("game"), "point": n,
                    "home_point": p.get("homePoint"), "away_point": p.get("awayPoint"),
                    "point_description": p.get("pointDescription"),
                    "home_point_type": p.get("homePointType"), "away_point_type": p.get("awayPointType"),
                    "game_home_score": score.get("homeScore"), "game_away_score": score.get("awayScore"),
                    "serving": score.get("serving"), "scoring": score.get("scoring"),
                    "tiebreak": tiebreak, "set_index": set_index, "game_index": game_index,
                })
    return rows


def _num(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("inf")


def pbp_shape(pbp: list) -> dict:
    """Sets, games and listed points of a record, plus games per set in match order."""
    sets = sorted(pbp, key=lambda x: _num(x.get("set")))
    games = [len(st.get("games") or []) for st in sets]
    points = sum(len(g.get("points") or []) for st in sets for g in st.get("games") or [])
    return {"sets": len(sets), "games": sum(games), "points": points, "games_per_set": games}


def statistic_rows(event_id, statistics: list) -> list[dict]:
    rows = []
    for period in statistics:
        for group in period.get("groups") or []:
            for item in group.get("statisticsItems") or []:
                rows.append({
                    "event_id": event_id, "period": period.get("period"), "group": group.get("groupName"),
                    "key": item.get("key"), "name": item.get("name"), "home": item.get("home"),
                    "away": item.get("away"), "home_value": item.get("homeValue"), "away_value": item.get("awayValue"),
                    "compare_code": item.get("compareCode"), "statistics_type": item.get("statisticsType"),
                    "value_type": item.get("valueType"), "render_type": item.get("renderType"),
                })
    return rows


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
def team_listing_pages(team_id: str) -> list[Path]:
    folder = P.raw_path(SOURCE, "teams", str(team_id))
    if not folder.exists():
        return []
    pages = []
    for path in folder.glob("events_last_*.json"):
        try:
            pages.append((int(path.stem.rsplit("_", 1)[1]), path))
        except ValueError:
            continue
    return [p for _, p in sorted(pages)]


def fetch_listings(client: P.Client, receipts, team_id: str, *, refresh: bool) -> dict:
    """Download a team's listing pages until the API says there is no next page (or answers 404)."""
    if refresh:  # old pages would otherwise be reused: the 404 receipt of the old last page must not stick
        for path in team_listing_pages(team_id):
            path.unlink()
    pages, events, note = 0, 0, ""
    for page in range(MAX_PAGES):
        dest = P.raw_path(SOURCE, "teams", str(team_id), f"events_last_{page}.json")
        name = f"teams/{team_id}/events_last_{page}"
        receipt = P.fetch(client, f"{API}/team/{team_id}/events/last/{page}", dest, receipts, name=name,
                          refresh=refresh, validator=P.json_validator, extra={"team_id": team_id, "page": page})
        if receipt.get("status") == 404:
            note = f"404 after page {page - 1}"
            break
        if receipt.get("error"):
            note = f"page {page}: {receipt['error']}"
            break
        body = P.read_json(dest)
        pages += 1
        events += len(body.get("events") or [])
        if not body.get("hasNextPage"):
            note = f"hasNextPage false at page {page}"
            break
    else:
        note = f"stopped at the {MAX_PAGES}-page safety limit"
    return {"team_id": team_id, "pages": pages, "events_listed": events, "end": note}


def load_events(team_ids: list[str]) -> dict[int, dict]:
    """Every listed event across the teams, keyed by event id, with which teams and pages listed it."""
    events: dict[int, dict] = {}
    for team_id in team_ids:
        for path in team_listing_pages(team_id):
            page = int(path.stem.rsplit("_", 1)[1])
            for event in P.read_json(path).get("events") or []:
                entry = events.setdefault(event["id"], {"event": event, "teams": [], "pages": [], "file": P.rel(path)})
                if team_id not in entry["teams"]:
                    entry["teams"].append(team_id)
                entry["pages"].append(f"{team_id}:{page}")
    return events


def wanted(event: dict, *, singles_only: bool, since_year: int | None, until_year: int | None,
           statuses: set[str] | None) -> bool:
    if singles_only and is_doubles(event):
        return False
    ts = event.get("startTimestamp")
    year = dt.datetime.fromtimestamp(ts, dt.timezone.utc).year if ts else None
    if since_year and (year is None or year < since_year):
        return False
    if until_year and (year is None or year > until_year):
        return False
    if statuses and _dig(event, ("status", "type")) not in statuses:
        return False
    return True


def fetch_event_docs(client: P.Client, receipts, event_id: int, *, parts: tuple[str, ...], refresh: bool) -> dict:
    out = {}
    for part in parts:
        url = f"{API}/event/{event_id}" + ("" if part == "event" else f"/{part}")
        dest = P.raw_path(SOURCE, "events", str(event_id), f"{part}.json")
        receipt = P.fetch(client, url, dest, receipts, name=f"events/{event_id}/{part}", refresh=refresh,
                          validator=P.json_validator, extra={"event_id": event_id, "part": part})
        out[part] = receipt
    return out


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def stage(team_ids: list[str], receipts) -> dict:
    events = load_events(team_ids)
    event_rows, point_rows_all, stat_rows_all = [], [], []
    for event_id, entry in sorted(events.items(), key=lambda kv: -(kv[1]["event"].get("startTimestamp") or 0)):
        row = flatten_event(entry["event"])
        row["listed_for_teams"] = ";".join(entry["teams"])
        row["listed_pages"] = ";".join(entry["pages"])
        row["listing_file"] = entry["file"]
        pbp_receipt = receipts.get(f"events/{event_id}/point-by-point") or {}
        row["pbp_status"] = pbp_receipt.get("error") or pbp_receipt.get("status")
        row["pbp_retrieved_at"] = pbp_receipt.get("retrieved_at")
        row["pbp_sha256"] = pbp_receipt.get("sha256")
        pbp_path = P.raw_path(SOURCE, "events", str(event_id), "point-by-point.json")
        if pbp_receipt.get("status") == 200 and pbp_path.exists():
            pbp = P.read_json(pbp_path).get("pointByPoint") or []
            shape = pbp_shape(pbp)
            row.update(pbp_sets=shape["sets"], pbp_games=shape["games"], pbp_points=shape["points"])
            for r in point_rows(event_id, pbp):
                r.update(source_file=P.rel(pbp_path), source_sha256=pbp_receipt.get("sha256"),
                         retrieved_at=pbp_receipt.get("retrieved_at"))
                point_rows_all.append(r)
        stats_receipt = receipts.get(f"events/{event_id}/statistics") or {}
        row["stats_status"] = stats_receipt.get("error") or stats_receipt.get("status")
        row["stats_retrieved_at"] = stats_receipt.get("retrieved_at")
        row["stats_sha256"] = stats_receipt.get("sha256")
        stats_path = P.raw_path(SOURCE, "events", str(event_id), "statistics.json")
        if stats_receipt.get("status") == 200 and stats_path.exists():
            statistics = P.read_json(stats_path).get("statistics") or []
            row["stats_periods"] = ";".join(str(p.get("period")) for p in statistics)
            for r in statistic_rows(event_id, statistics):
                r.update(source_file=P.rel(stats_path), source_sha256=stats_receipt.get("sha256"),
                         retrieved_at=stats_receipt.get("retrieved_at"))
                stat_rows_all.append(r)
        event_rows.append(row)
    now = P.utc_now_iso()
    out = {}
    for name, columns, rows in (("events", EVENT_COLUMNS, event_rows), ("points", POINT_COLUMNS, point_rows_all),
                                ("statistics", STAT_COLUMNS, stat_rows_all)):
        dest = P.dump_path(SOURCE, f"{name}.parquet")
        table = [[P.s(r.get(c)) for c in columns] for r in rows]
        stats = P.stage_table(SOURCE, dest, columns, table, source_file=P.rel(P.raw_path(SOURCE)), retrieved_at=now,
                              extra={"teams": ";".join(team_ids)})
        out[name] = {"rows": stats["rows"], "dest": stats["dest"], "bytes": stats["bytes"]}
        P.log(f"[{SOURCE}] staged {stats['dest']}: {stats['rows']:,} rows")
    return out


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def summarize_events(events: dict[int, dict], receipts, selected: set[int]) -> dict:
    by_cat_year, by_status, pbp_by_cat_year = Counter(), Counter(), Counter()
    for event_id, entry in events.items():
        e = entry["event"]
        ts = e.get("startTimestamp")
        year = dt.datetime.fromtimestamp(ts, dt.timezone.utc).year if ts else None
        cat = _dig(e, ("tournament", "category", "name"))
        kind = "doubles" if is_doubles(e) else "singles"
        by_cat_year[f"{kind}|{cat}|{year}"] += 1
        by_status[f"{kind}|{_dig(e, ('status', 'type'))}"] += 1
        if event_id in selected:
            r = receipts.get(f"events/{event_id}/point-by-point") or {}
            outcome = r.get("error") or r.get("status") or "not fetched"
            pbp_by_cat_year[f"{cat}|{year}|{outcome}"] += 1
    return {"listed_by_kind_category_year": dict(sorted(by_cat_year.items())),
            "listed_by_kind_status": dict(sorted(by_status.items())),
            "selected_pbp_outcome_by_category_year": dict(sorted(pbp_by_cat_year.items()))}


def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    if args.team_ids:
        team_ids = [t.strip() for t in args.team_ids.split(",") if t.strip()]
        labels = {t: t for t in team_ids}
    else:
        labels = {v: k for k, v in P.study_players().items()}
        team_ids = list(labels)
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "started_at": P.utc_now_iso(), "args": vars(args), "teams": {}, "errors": []}
    client = None
    if not args.stage_only:
        client = P.Client(IMPERSONATE, min_interval=args.min_interval, jitter=args.jitter,
                          max_requests=args.max_requests, headers=HEADERS)
    try:
        if not args.stage_only:
            for team_id in team_ids:
                have = team_listing_pages(team_id)
                if have and not args.refresh_listings:
                    summary["teams"][team_id] = {"team_id": team_id, "pages": len(have), "end": "reused existing pages"}
                    continue
                info = fetch_listings(client, receipts, team_id, refresh=args.refresh_listings)
                info["label"] = labels.get(team_id)
                summary["teams"][team_id] = info
                P.log(f"[{SOURCE}] {labels.get(team_id, team_id)}: {info['pages']} pages, {info['events_listed']} events ({info['end']})")
        events = load_events(team_ids)
        statuses = set(args.statuses.split(",")) if args.statuses else None
        selected = [eid for eid, entry in events.items()
                    if wanted(entry["event"], singles_only=not args.doubles, since_year=args.since_year,
                              until_year=args.until_year, statuses=statuses)]
        selected.sort(key=lambda eid: -(events[eid]["event"].get("startTimestamp") or 0))
        if args.limit:
            selected = selected[:args.limit]
        summary["events_listed"] = len(events)
        summary["events_selected"] = len(selected)
        P.log(f"[{SOURCE}] {len(events)} distinct events listed; {len(selected)} selected")
        parts = tuple(p for p in ("point-by-point", "statistics") if p not in (args.skip or ()))
        if args.with_detail:
            parts += ("event",)
        outcomes = Counter()
        if not args.stage_only:
            for n, event_id in enumerate(selected, 1):
                docs = fetch_event_docs(client, receipts, event_id, parts=parts, refresh=args.refresh)
                for part, receipt in docs.items():
                    outcomes[f"{part}:{receipt.get('error') or receipt.get('status')}" + (":cached" if receipt.get("skipped") else "")] += 1
                if n % 50 == 0 or n == len(selected):
                    P.log(f"[{SOURCE}] {n}/{len(selected)} events; requests={client.requests}; " +
                          ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items())))
    except (P.Blocked, P.BudgetExhausted) as stop:
        summary["stopped"] = f"{type(stop).__name__}: {stop}"
        P.log(f"[{SOURCE}] STOPPED: {stop}")
        events = load_events(team_ids)
        selected = selected if "selected" in locals() else []
    summary["fetch_outcomes"] = dict(sorted(outcomes.items())) if "outcomes" in locals() else {}
    if client is not None:
        summary["client"] = client.stats()
    if not args.no_stage:
        summary["staged"] = stage(team_ids, receipts)
    summary.update(summarize_events(events, receipts, set(selected)))
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = P.write_summary("sofascore_summary.json", summary)
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--team-ids", help="comma list of SofaScore team ids (default: the ten study players)")
    parser.add_argument("--since-year", type=int, help="skip events before this calendar year")
    parser.add_argument("--until-year", type=int, help="skip events after this calendar year")
    parser.add_argument("--statuses", default=None, help="comma list of status types to fetch (default: all)")
    parser.add_argument("--doubles", action="store_true", help="also fetch doubles events (default: singles only)")
    parser.add_argument("--with-detail", action="store_true", help="also fetch /event/<id> (venue, set durations)")
    parser.add_argument("--skip", nargs="*", choices=["point-by-point", "statistics"], help="parts not to fetch")
    parser.add_argument("--limit", type=int, help="fetch only the N most recent selected events (dry runs)")
    parser.add_argument("--max-requests", type=int, help="stop after this many HTTP requests")
    parser.add_argument("--min-interval", type=float, default=1.0, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=0.6)
    parser.add_argument("--refresh", action="store_true", help="refetch event documents already on disk (404s included)")
    parser.add_argument("--refresh-listings", action="store_true", help="refetch the listing pages (new matches)")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rebuild the Parquet tables and summary")
    parser.add_argument("--no-stage", action="store_true", help="fetch only; skip the Parquet rebuild")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    return 1 if summary.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())

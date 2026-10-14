"""Does TennisLive.net list men's ITF World Tennis Tour results after June 2026 (ISO weeks 27-36)?

A follow-up to tennislive_probe.py (same site, same fetch layer and stops). No file the project holds lists
these matches: Polymarket gives winners only, the Live Tennis API index on disk ends on 13 Aug 2026.

Events (seeded draw, ``--seed``):
    * 8 men's M15/M25 events, one in each of ISO weeks 27, 28, 30, 31, 32, 34, 35, 36 (M25 in weeks 27, 30, 32,
      35; M15 in the others), and 3 women's events for comparison (W15 in week 29, W35/W50 in week 33,
      W75/W100 in week 36).
    * Weeks 28-36 come from Wikipedia's "2026 ITF Men's / Women's World Tennis Tour (July–September)" pages
      (MediaWiki API, wikitext; two requests, cached in data/raw/gap_sources/wikipedia/). They give each event's
      city, surface, level, ITF draw link, winner with the final's score, runner-up, semifinalists and
      quarterfinalists.
    * Week 27 (29 Jun - 5 Jul) is on Wikipedia's April-June page, which is not read. It comes from the Live
      Tennis API index (data/dump/matches/live_tennis_api_zenodo/, tier 270 = ITF men; its
      scheduled_time_utc is Israel local time in v1.0.0, taken as UTC+3, and UTC in v1.0.2, staged since
      8 Oct 2026) and its players table.

On TennisLive, for each event:
    1. **Find it.** The season listing of one of its players (winner first, then the others). The listing
       API and the slug rules are tennislive_probe.py's. The event is the listing group whose name has the
       event's level and city and whose dates fall in its week. Cities with an event every week (Monastir)
       put the previous week's final in that window, so the group nearest mid-week comes first. The pick
       is kept only if the event's final is dated in its week and has Wikipedia's finalists; otherwise the
       next candidate is read.
    2. **List it.** The group's tournament page (``/atp-men/<event>-2026[-n]/`` or ``/wta-women/...``), which loads
       its lists from ``/api/tournament-section?tour=<atp|wta>&slug=<event>&section=results`` (read from the
       site's tournament.js). Every singles match listed is counted by draw (main or qualifying), round and
       result.
    3. **Read 3 main-draw matches** (seeded): point-by-point, the completeness verdict against the page's own
       final score, and the statistics block. These use tennislive_probe.py's parsers and rules.

Pace and stops: those of tennislive_probe.StrictClient. At least 2 s after each answer plus up to 1 s of
jitter; any HTTP 403 or 429, Cloudflare challenge or CAPTCHA stops the run at once. This follow-up's budget is
300 requests, counted in the lane's ledger (data/raw/gap_sources/tennislive/_requests.jsonl) from line
FOLLOWUP_START + 1. Every answer is cached with a receipt, so a rerun resumes from the cache.

Usage:
    ./python.sh src/eda/gap_sources/tennislive_itf_after_june.py [--seed 20260929]
    ./python.sh src/eda/gap_sources/tennislive_itf_after_june.py --offline      # rebuild the outputs from the cache

Writes data/studies/gap_sources/tennislive_itf_after_june.csv (one row per event),
tennislive_itf_after_june_matches.csv (the matches read), tennislive_itf_after_june_summary.json, and raw
answers under data/raw/gap_sources/tennislive/ (same receipts) and data/raw/gap_sources/wikipedia/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.gap_sources import tennislive_probe as T    # noqa: E402
from src.ingest.point_sources import common as P         # noqa: E402
from src.ingest.point_sources import tennislive as TL    # noqa: E402
from src.ingest.public_dump import common as C           # noqa: E402
from src.ingest.public_dump import live_tennis_api_zenodo as LTA    # noqa: E402

WIKI = T.RAW / "wikipedia"
WIKI_PAGES = {("M", "itf_men_2026_jul_sep"): "2026 ITF Men's World Tennis Tour (July–September)",
              ("W", "itf_women_2026_jul_sep"): "2026 ITF Women's World Tennis Tour (July–September)"}
LTA_MATCHES = PROJECT_ROOT / "data" / "dump" / "matches" / "live_tennis_api_zenodo" / "matches.parquet"
LTA_PLAYERS = PROJECT_ROOT / "data" / "dump" / "players" / "live_tennis_api_zenodo" / "players.parquet"
OUT = T.OUT
FOLLOWUP_START = 449          # lines in the lane's ledger before this follow-up began (29 Sep 2026)
FOLLOWUP_BUDGET = 300
MEN_WEEKS = {27: "M25", 28: "M15", 30: "M25", 31: "M15", 32: "M25", 34: "M15", 35: "M25", 36: "M15"}
WOMEN_WEEKS = {29: ("W15",), 33: ("W35", "W50"), 36: ("W75", "W100")}
MONTHS = {"July": 7, "August": 8, "September": 9}
LEVEL = re.compile(r"\b([MW](?:15|25|35|50|75|100))(\+H)?\b")


# ------------------------------------------------------------------------------------------ events
def wiki_text(key: str) -> str:
    return json.loads((WIKI / f"{key}.json").read_text(encoding="utf-8"))["parse"]["wikitext"]


def wiki_names(cell: str) -> list[str]:
    """Player names in a table cell: '{{flagicon|X}} [[Link|Name]]' or '{{flagicon|X}} Name', <br/>-separated."""
    names = []
    for part in re.split(r"<br\s*/?>", cell):
        m = re.search(r"\{\{flagicon\|[^}]*\}\}\s*(.+)", part)
        if not m:
            continue
        text = m.group(1)
        link = re.search(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", text)
        name = link.group(1) if link else re.sub(r"'''|''", "", text)
        name = re.sub(r"\s+", " ", name).strip(" '")
        if name:
            names.append(name)
    return names


def wiki_events(tour: str, key: str) -> pd.DataFrame:
    """Singles rows of a Wikipedia ITF tour page: week, event, level, winner, final score, and the last eight."""
    text = wiki_text(key)
    rows, week = [], None
    for chunk in re.split(r"\n\|-[^\n]*", text):
        cells = [c for c in re.split(r"\n\|(?!-)", "\n" + chunk.strip()) if c.strip()]
        for i, cell in enumerate(cells):
            body = cell.split("|", 1)[1] if re.match(r"\s*(rowspan|style)", cell) and "|" in cell else cell
            m = re.fullmatch(r"\s*(July|August|September) (\d+)\s*", body)
            if m:
                week = dt.date(2026, MONTHS[m.group(1)], int(m.group(2)))
                continue
            if week is None or "<br" not in body or not LEVEL.search(body) or "flagicon" in body:
                continue
            level = LEVEL.search(body)
            place = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", body.split("<br")[0 if tour == "M" else 0])
            parts = [re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", p).strip() for p in re.split(r"<br\s*/?>", body)]
            # men: "City, Country / Surface / M25 / draws"; women may start with the tournament's own name
            city_country = next((p for p in parts if "," in p and not LEVEL.search(p)), parts[0])
            surface = next((p for p in parts if re.match(r"^(Hard|Clay|Grass|Carpet)", p)), None)
            draws = re.search(r"\[(https://www\.itftennis\.com/\S+)", body)
            rest = cells[i + 1:i + 5]
            winner = wiki_names(rest[0]) if rest else []
            score = re.split(r"<br\s*/?>", rest[0])[-1].strip() if rest else None
            rows.append({"tour": tour, "week_start": week, "iso_week": week.isocalendar()[1],
                         "level": level.group(1), "hospitality": bool(level.group(2)),
                         "city": city_country.split(",")[0].strip(), "country": city_country.split(",")[-1].strip(),
                         "surface": surface, "itf_draws_url": draws.group(1) if draws else None,
                         "winner": winner[0] if winner else None, "final_score": score,
                         "runner_up": (wiki_names(rest[1]) or [None])[0] if len(rest) > 1 else None,
                         "semifinalists": ";".join(wiki_names(rest[2])) if len(rest) > 2 else None,
                         "quarterfinalists": ";".join(wiki_names(rest[3])) if len(rest) > 3 else None,
                         "names_source": "wikipedia", "wiki_place": place.strip()})
            break
    return pd.DataFrame(rows)


def index_events(week: int, tier: str = "270") -> pd.DataFrame:
    """Events of one ISO week in the Live Tennis API index, with the names of their players (most matches first)."""
    m = pd.read_parquet(LTA_MATCHES)
    m = m[m["tier_key"].astype(str).eq(tier)].copy()
    naive = pd.to_datetime(m["scheduled_time_utc"], errors="coerce")
    m["utc"] = naive if LTA.staged_time_zone(LTA_MATCHES) == "UTC" else naive - pd.Timedelta(hours=3)
    m = m[m["utc"].dt.year.eq(2026)]
    players_table = pd.read_parquet(LTA_PLAYERS)
    names = players_table.set_index(players_table["player_id"].astype(str))["name"]
    # the index names one event two ways (two feeds): "ITF M25 Skopje Men" and "M25 Skopje"; both are one event
    m["level"] = m["tournament"].str.extract(r"\b([MW](?:15|25|35|50|75|100))\b", expand=False)
    m["city"] = (m["tournament"].str.replace(r"^(ITF\s+)?[MW]\d+\s*(\+\s*H)?\s*", "", regex=True)
                 .str.replace(r"\s+(Men|Women)$", "", regex=True).str.replace(r"\s*\([^)]*\)\s*$", "", regex=True)
                 .str.replace(r"\s*\+\s*H\b", "", regex=True).str.strip())
    m["week"] = m["utc"].dt.isocalendar().week.astype(int)
    rows = []
    for (level, city), g in m[m["level"].notna()].groupby(["level", "city"]):
        wk = int(g["utc"].median().isocalendar().week)
        if wk != week:
            continue
        g = g[g["week"].between(week - 1, week)]
        counts = Counter(str(x) for x in list(g["player1_id"]) + list(g["player2_id"]) if pd.notna(x))
        players = [names.get(p) for p, _ in counts.most_common() if p in names.index]
        rows.append({"tour": "M" if tier == "270" else "W", "week_start": dt.date.fromisocalendar(2026, week, 1),
                     "iso_week": week, "level": level, "hospitality": bool(g["tournament"].str.contains(r"\+\s*H").any()),
                     "city": city, "country": None, "surface": g["surface"].iloc[0], "itf_draws_url": None,
                     "winner": None, "final_score": None, "runner_up": None, "semifinalists": None,
                     "quarterfinalists": ";".join(p for p in players if p), "names_source": "live_tennis_api_index",
                     "wiki_place": " / ".join(sorted(g["tournament"].unique())), "index_matches": len(g),
                     "index_first_utc": str(g["utc"].min())})
    return pd.DataFrame(rows)


def draw_events(seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    men = wiki_events("M", "itf_men_2026_jul_sep")
    women = wiki_events("W", "itf_women_2026_jul_sep")
    picks = []
    for week, level in MEN_WEEKS.items():
        pool = index_events(week) if week == 27 else men[men["iso_week"].eq(week)]
        pool = pool[pool["level"].eq(level)]
        if len(pool):
            picks.append({**pool.iloc[int(rng.integers(len(pool)))].to_dict(), "pool": len(pool)})
    for week, levels in WOMEN_WEEKS.items():
        pool = women[women["iso_week"].eq(week) & women["level"].isin(levels)]
        if len(pool):
            picks.append({**pool.iloc[int(rng.integers(len(pool)))].to_dict(), "pool": len(pool)})
    return pd.DataFrame(picks)


# ------------------------------------------------------------------------------------------ TennisLive
def fold(text) -> str:
    return re.sub(r"[^a-z0-9]+", " ", T.ascii_fold(text).lower()).strip()


def event_in(matches: list[dict], ev: dict) -> list[dict]:
    """Candidate listing groups of this event, best first: the group names the level and the city, and the
    player's matches in it fall within the week (3 days before its Monday for qualifying, to 8 days after).
    Cities with an event every week (Monastir, Kursumlijska Banja...) put the previous week's final inside that
    window, so the group whose matches sit nearest the middle of the week comes first."""
    week = pd.Timestamp(ev["week_start"])
    lo, hi = week - pd.Timedelta(days=3), week + pd.Timedelta(days=8)
    mid = week + pd.Timedelta(days=3, hours=12)
    city = fold(ev["city"])
    city_words = [w for w in city.split() if len(w) >= 3]
    level = ev["level"].lower()
    groups: dict[str, list] = {}
    for m in matches:
        t = T.match_time(m)
        name = fold(m["tournament"])
        if t is None or not lo <= t <= hi or level not in name.split():
            continue
        if city in name or any(w in name.split() for w in city_words) or \
                any(T.SequenceMatcher(None, w, x).ratio() >= 0.8 for w in city_words for x in name.split() if len(x) >= 4):
            groups.setdefault(m.get("tournament_url") or m["tournament"], []).append({**m, "t": t})
    ranked = sorted(groups.values(), key=lambda ms: abs((pd.Series([x["t"] for x in ms]).median() - mid).total_seconds()))
    return [ms[0] for ms in ranked]


def final_check(ev: dict, final: dict | None) -> dict:
    """Is the listed final this event's? Its date falls in the event's week (Thursday to the next Monday), and
    where Wikipedia names the finalists, they are the listed final's players."""
    week = pd.Timestamp(ev["week_start"])
    out = {"final_date": final["start"].strftime("%Y-%m-%d") if final and final.get("start") is not None else None}
    out["final_in_week"] = bool(final and final.get("start") is not None and
                                week + pd.Timedelta(days=3) <= final["start"] <= week + pd.Timedelta(days=8, hours=23))
    names = [n for n in (ev.get("winner"), ev.get("runner_up")) if isinstance(n, str) and n.strip()]
    if final and names:
        listed = [T.words(x) for x in str(final["players"]).split(" | ")]
        out["final_players_agree"] = all(any(T.name_agreement(T.words(n), x) or T.loose_agreement(T.words(n), x)
                                             for x in listed) for n in names)
    else:
        out["final_players_agree"] = None
    return out


def locate(resolver: T.Resolver, ev: dict, attempts: list[str]) -> dict | None:
    """The event's listing group, through the season listing of one of its players (winner first)."""
    tour = "atp" if ev["tour"] == "M" else "wta"
    names = [n for n in [ev.get("winner"), ev.get("runner_up")] +
             str(ev.get("semifinalists") or "").split(";") + str(ev.get("quarterfinalists") or "").split(";")
             if isinstance(n, str) and n.strip() and n != "nan"]
    seen = set()
    for search_too in (False, True):
        for name in names[:6]:
            slugs = resolver.slugs.known(name, tour) + [T.guess_slug(name)]
            if search_too:
                slugs = resolver.search_slugs(name, tour, attempts)
            for slug in slugs:
                if not slug or (tour, slug) in seen or (tour, slug) in resolver.bad_slugs:
                    continue
                seen.add((tour, slug))
                outcome, matches, _ = resolver.season(tour, slug, 2026, pd.Timestamp(ev["week_start"]))
                attempts.append(f"'{slug}' 2026: {outcome}, {len(matches)} listed")
                if outcome in ("absent", "not ok"):
                    resolver.bad_slugs.add((tour, slug))
                    continue
                hits = event_in(matches, ev)
                if hits:
                    via = "site search" if search_too else resolver.slugs.provenance(name, tour, slug)
                    return {**hits[0], "via_player": name, "via_slug": slug, "via": via,
                            "candidates": [h.get("tournament_url") for h in hits]}
        if not search_too and len(attempts) > 12:
            break
    return None


def tournament_page(site: T.Site, url: str) -> tuple[str, str | None]:
    """A tournament page (``/atp-men/<slug>/`` or ``/wta-women/<slug>/``), cached like the match pages."""
    m = re.fullmatch(r"/(atp-men|wta-women)/([^/]+)/?", url or "")
    if not m:
        return "bad url", None
    dest = T.FOLDER / "tournaments" / m.group(1) / f"{m.group(2)}.html.gz"
    r = site._get(T.SITE + url, dest, f"tournaments/{m.group(1)}/{m.group(2)}", validator=P.html_validator,
                  compress=True)
    if site.ok(r, dest):
        return "200", P.read_bytes(dest).decode("utf-8", errors="replace")
    return ("not fetched" if r.get("not_fetched") else str(r.get("error") or r.get("status"))), None


def tournament_section(site: T.Site, url: str, section: str) -> tuple[str, dict | None]:
    """``/api/tournament-section?tour=<atp|wta>&slug=<slug>&section=<live|upcoming|results|draw>``: the lazily
    loaded lists of a tournament page (read from the site's tournament.js; same token and headers as the other
    JSON endpoints)."""
    m = re.fullmatch(r"/(atp-men|wta-women)/([^/]+)/?", url or "")
    if not m:
        return "bad url", None
    tour = "atp" if m.group(1) == "atp-men" else "wta"
    dest = T.FOLDER / "tournaments" / m.group(1) / f"{m.group(2)}__{section}.json"
    name = f"tournaments/{m.group(1)}/{m.group(2)}/{section}"
    if not site.offline and not site.final(name, dest):
        site.ensure_session()
    api = f"{T.SITE}/api/tournament-section?tour={tour}&slug={quote(m.group(2))}&section={section}"
    headers = {**TL.API_HEADERS, "X-TennisLive-Token": site.token or "", "Referer": T.SITE + url}
    r = site._get(api, dest, name, validator=T.api_validator, compress=False, headers=headers)
    return site._json_outcome(r, dest)


MAIN_ROUNDS = ["round_1", "round_2", "round_3", "round_4", "quarterfinal", "semifinal", "final"]


def section_matches(payload: dict) -> list[dict]:
    """Every match of a tournament section, with its discipline, draw, round and result."""
    rows = []
    for group in ((payload or {}).get("data") or {}).get("groups") or []:
        for match in group.get("matches") or []:
            stage = str(match.get("stageCode") or group.get("stageCode") or "")
            players = match.get("players") or []
            games = T.listed_games(players) if len(players) == 2 else []
            rows.append({"url": match.get("url") or None, "state": match.get("state"), "doubles": bool(match.get("doubles")),
                         "stage": stage, "draw": "qualifying" if "qualif" in stage else "main",
                         "players": " | ".join(str(p.get("name")) for p in players), "games": games,
                         "sets": " ".join(f"{(p0 if not isinstance(p0, dict) else p0.get('score'))}-"
                                          f"{(p1 if not isinstance(p1, dict) else p1.get('score'))}"
                                          for p0, p1 in zip(*(p.get("sets") or [] for p in players))) if len(players) == 2 else "",
                         "winner_id": match.get("winnerId"), "end_reason": match.get("endReason"),
                         "start": T.match_time({"ts": match.get("startTimestamp"), "start_times": []})})
    return rows


def has_result(m: dict) -> bool:
    return m["state"] in ("finished", "retired", "walkover", "awarded") and (bool(m["games"]) or m["winner_id"] is not None)


def read_match(site: T.Site, url: str) -> dict:
    status, html, _ = site.match_page(url)
    out = {"match_url": url, "page_status": status}
    if html is None:
        return {**out, "pbp_available": False, "stats_available": False, "verdict": "no page"}
    info = T.inspect(html)
    official = T.official_sets(info["tl_score"]) if info.get("tl_score") else []
    v, kind, sk = T.verdict(official, info)
    total = sum(official)
    with_points = int(info.get("games_listed") or 0) - int(info.get("games_without_points") or 0)
    return {**out, "tl_score": info.get("tl_score"), "tl_names": info.get("tl_names"), "tl_round": info.get("tl_round"),
            "tl_date": info.get("tl_date"), "score_games": " ".join(str(x) for x in official),
            "games_by_set": " ".join(str(x) for x in info["record_games"]), "points_listed": info.get("points_listed"),
            "games_without_points": info.get("games_without_points"), "pbp_available": bool(info.get("points_listed")),
            "pbp_unavailable_notice": info.get("pbp_unavailable_notice"),
            "point_game_share": round(min(with_points, total) / total, 3) if total else None,
            "verdict": v, "completeness": kind, "short_kind": sk, "stats_available": info["stats_available"],
            "stats_rows": info["stats_rows"], "stats_names": info["stats_names"]}


def expected_main(matches: list[dict]) -> int | None:
    """Main-draw singles matches a full draw has: a 32-draw has 31 (its first round, 16, sets the size)."""
    first = sum(1 for m in matches if not m["doubles"] and m["draw"] == "main" and m["stage"] == "round_1")
    if not first:
        return None
    size = 32 if first <= 16 else 64 if first <= 32 else 128
    return size - 1


def run(args) -> int:
    P.configure_stdout()
    started = time.time()
    events = draw_events(args.seed)
    if args.limit:
        events = events.head(args.limit)
    receipts = C.Receipts(T.SOURCE, root=T.RAW)
    client = None if args.offline else T.StrictClient(budget=FOLLOWUP_START + FOLLOWUP_BUDGET)
    site = T.Site(client, receipts, args.offline)
    resolver = T.Resolver(site)
    event_rows, match_rows, stopped = [], [], None
    try:
        for n, (_, ev) in enumerate(events.iterrows()):
            before = client.requests if client else 0
            attempts: list[str] = []
            row = {k: ev.get(k) for k in ("tour", "iso_week", "week_start", "level", "hospitality", "city", "country",
                                          "surface", "names_source", "winner", "runner_up", "final_score",
                                          "itf_draws_url", "pool")}
            fs = row["final_score"]
            fs = fs if isinstance(fs, str) and fs.strip() and fs != "nan" else None
            # Wikipedia writes a tiebreak as 7–6<sup>(7–5)</sup>; the set's games are what is compared
            row["final_score"] = re.sub(r"<sup>.*?</sup>", "", fs).replace("–", "-").strip() if fs else None
            hit = locate(resolver, ev.to_dict(), attempts)
            row.update(found=hit is not None, via_player=(hit or {}).get("via_player"), via_slug=(hit or {}).get("via_slug"),
                       via=(hit or {}).get("via"), tl_tournament=(hit or {}).get("tournament"), attempts=" || ".join(attempts))
            if hit and hit.get("tournament_url"):
                tried = []
                for url in [hit["tournament_url"]] + [u for u in (hit.get("candidates") or [])[1:] if u]:
                    tried.append(url)
                    page_status, html = tournament_page(site, url)
                    status, payload = tournament_section(site, url, "results")
                    matches = section_matches(payload) if status == "ok" else []
                    main = [m for m in matches if not m["doubles"] and m["draw"] == "main"]
                    final = next((m for m in main if m["stage"] == "final"), None)
                    check = final_check(ev.to_dict(), final)
                    if check["final_in_week"] and check["final_players_agree"] is not False:
                        break
                rt = TL.runtime_object(html) if html else {}
                row.update(tl_tournament_url=url, candidates_tried=";".join(tried), tournament_page_status=page_status,
                           tl_total_singles=(rt.get("tournamentDetailTotalCounts") or {}).get("singles"),
                           tl_total_doubles=(rt.get("tournamentDetailTotalCounts") or {}).get("doubles"),
                           results_section_status=status, **check)
                singles = [m for m in matches if not m["doubles"]]
                main = [m for m in singles if m["draw"] == "main"]
                qual = [m for m in singles if m["draw"] == "qualifying"]
                rounds = Counter(m["stage"] for m in main)
                final = next((m for m in main if m["stage"] == "final"), None)
                row.update(main_singles_listed=len(main), main_singles_with_result=sum(has_result(m) for m in main),
                           main_expected=expected_main(matches),
                           main_by_round=";".join(f"{r}:{rounds[r]}" for r in MAIN_ROUNDS if rounds.get(r)),
                           qual_singles_listed=len(qual), qual_singles_with_result=sum(has_result(m) for m in qual),
                           doubles_listed=sum(1 for m in matches if m["doubles"]),
                           main_with_page_url=sum(1 for m in main if m["url"]),
                           tl_final=(final or {}).get("players"), tl_final_sets=(final or {}).get("sets"),
                           final_agrees=(bool(final) and bool(row["final_score"]) and
                                         T.official_sets(final.get("sets")) == T.official_sets(row["final_score"]))
                           if row["final_score"] else None)
                pool = [m for m in main if m["url"] and has_result(m)]
                rng = np.random.default_rng(args.seed + n)
                picks = [pool[i] for i in sorted(rng.choice(len(pool), size=min(3, len(pool)), replace=False))] if pool else []
                reads = []
                for m in picks:
                    rec = read_match(site, m["url"])
                    rec.update(event=f"{row['tour']}|w{row['iso_week']}|{row['level']}|{row['city']}", round=m["stage"],
                               listed_players=m["players"], listed_sets=m["sets"],
                               listed_score_agrees=(T.official_sets(m["sets"]) == T.official_sets(rec.get("tl_score") or "")))
                    reads.append(rec)
                    match_rows.append(rec)
                v = Counter(r["verdict"] for r in reads)
                row.update(matches_read=len(reads), read_pages_200=sum(r["page_status"] == "200" for r in reads),
                           read_with_points=sum(bool(r.get("pbp_available")) for r in reads),
                           read_complete=v.get("complete", 0), read_only_set_closing_missing=v.get("only set-closing games missing", 0),
                           read_other_shortfall=sum(c for k, c in v.items() if str(k).startswith("other shortfall")),
                           read_no_points=v.get("no points", 0),
                           read_with_statistics=sum(bool(r.get("stats_available")) for r in reads),
                           read_median_games_with_points=float(pd.Series([r.get("point_game_share") for r in reads],
                                                                         dtype="float").median()) if reads else None)
            event_rows.append(row)
            P.log(f"{row['tour']} w{row['iso_week']} {row['level']} {row['city']}: found={row['found']} "
                  f"{row.get('tl_tournament_url')}; main {row.get('main_singles_with_result')}/{row.get('main_singles_listed')} "
                  f"(expected {row.get('main_expected')}), qual {row.get('qual_singles_with_result')}/{row.get('qual_singles_listed')}; "
                  f"read {row.get('matches_read')}: points {row.get('read_with_points')}, complete {row.get('read_complete')}, "
                  f"closers-only {row.get('read_only_set_closing_missing')}, stats {row.get('read_with_statistics')}; "
                  f"requests this run={(client.requests - before) if client else 0}")
    except (P.Blocked, P.BudgetExhausted) as stop:
        stopped = f"{type(stop).__name__}: {stop}"
        P.log(f"STOPPED: {stopped}")
    ledger = [json.loads(x) for x in T.LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    mine = ledger[FOLLOWUP_START:]
    for row in event_rows:                        # the ledger's requests that belong to this event
        slugs = set(re.findall(r"'([^']+)' 2026", row.get("attempts") or ""))
        tournaments = [u.strip("/").split("/")[-1] for u in str(row.get("candidates_tried") or "").split(";") if u]
        row["requests"] = sum(1 for x in mine if any(f"/{t}/" in x["url"] or f"slug={t}&" in x["url"] for t in tournaments)
                              or any(f"slug={s}&" in x["url"] or x["url"].endswith(f"/{s}/") for s in slugs))
    ev_frame, m_frame = pd.DataFrame(event_rows), pd.DataFrame(match_rows)
    ev_frame.to_csv(OUT / "tennislive_itf_after_june.csv", index=False)
    m_frame.to_csv(OUT / "tennislive_itf_after_june_matches.csv", index=False)
    summary = summarize(ev_frame, m_frame)
    summary.update(
        generated_at=C.utc_now_iso(), seed=args.seed, stopped=stopped, seconds=round(time.time() - started, 1),
        client=client.stats() if client else "offline",
        requests={"tennislive_total": len(mine), "budget": FOLLOWUP_BUDGET,
                  "by_kind_status": dict(sorted(Counter(f"{kind_of(x['url'])}|{x['status']}" for x in mine).items())),
                  "refusals": [x for x in mine if x["status"] in (403, 429) or (x.get("note") or "").startswith("challenge")],
                  "first_at": mine[0]["at"] if mine else None, "last_at": mine[-1]["at"] if mine else None,
                  "wikipedia_mediawiki_api": [{k: r.get(k) for k in ("name", "url", "retrieved_at", "status", "sha256")}
                                              for r in C.Receipts("wikipedia", root=T.RAW).all().values()]},
        wikipedia_revisions={key: json.loads((WIKI / f"{key}.json").read_text(encoding="utf-8"))["parse"].get("revid")
                             for _, key in WIKI_PAGES})
    (OUT / "tennislive_itf_after_june_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n",
                                                               encoding="utf-8")
    P.log(json.dumps(summary["by_tour"], indent=1, default=str))
    return 1 if stopped else 0


def kind_of(url: str) -> str:
    return "tournament section" if "/api/tournament-section" in url else \
        "tournament page" if re.search(r"/(atp-men|wta-women)/", url) else T.request_kind(url)


def summarize(ev: pd.DataFrame, ms: pd.DataFrame) -> dict:
    out = {"definitions": {
        "main_singles_with_result": "main-draw singles matches in the tournament page's results section that "
                                    "are finished (or retired / walkover) with a score or a winner",
        "main_expected": "31 for a 32-draw (the first round's size sets the draw)",
        "qual_singles_listed": "qualifying singles matches listed in the same section",
        "read_*": "three main-draw singles matches per event (seeded), read on their match pages; the verdict "
                  "compares games per set with the page's own final score (tennislive_probe.py rules)"},
        "by_tour": {}, "events": len(ev)}
    for tour, g in ev.groupby("tour"):
        mm = ms[ms["event"].str.startswith(f"{tour}|")] if len(ms) else ms
        out["by_tour"][tour] = {
            "events": int(len(g)), "found": int(g["found"].sum()),
            "main_listed_with_result": int(pd.to_numeric(g.get("main_singles_with_result"), errors="coerce").sum()),
            "main_expected": int(pd.to_numeric(g.get("main_expected"), errors="coerce").sum()),
            "events_with_full_main_draw": int((pd.to_numeric(g.get("main_singles_with_result"), errors="coerce")
                                               >= pd.to_numeric(g.get("main_expected"), errors="coerce")).sum()),
            "qual_listed": int(pd.to_numeric(g.get("qual_singles_listed"), errors="coerce").sum()),
            "events_with_qualifying": int(pd.to_numeric(g.get("qual_singles_listed"), errors="coerce").gt(0).sum()),
            "matches_read": int(len(mm)),
            "with_points": int(mm["pbp_available"].astype(bool).sum()) if len(mm) else 0,
            "complete": int(mm["verdict"].eq("complete").sum()) if len(mm) else 0,
            "only_set_closing_missing": int(mm["verdict"].eq("only set-closing games missing").sum()) if len(mm) else 0,
            "other_shortfall": int(mm["verdict"].astype(str).str.startswith("other shortfall").sum()) if len(mm) else 0,
            "with_statistics": int(mm["stats_available"].astype(bool).sum()) if len(mm) else 0,
            "median_games_with_points": float(pd.to_numeric(mm["point_game_share"], errors="coerce").median()) if len(mm) else None,
            "median_games_with_points_among_point_records": float(pd.to_numeric(
                mm.loc[mm["pbp_available"].astype(bool), "point_game_share"], errors="coerce").median()) if len(mm) else None,
            "no_point_pages_with_unavailable_notice": int((~mm["pbp_available"].astype(bool)
                                                           & mm["pbp_unavailable_notice"].eq(True)).sum()) if len(mm) else 0,
            "finals_in_event_week": int(g["final_in_week"].eq(True).sum()),
            "final_players_agree_with_wikipedia": int(g["final_players_agree"].eq(True).sum()),
            "final_agrees_with_wikipedia": {"compared": int(g["final_agrees"].notna().sum()),
                                            "agree": int(g["final_agrees"].eq(True).sum())} if "final_agrees" in g else None}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=20260929)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--select-only", action="store_true", help="print the drawn events and stop (no HTTP)")
    parser.add_argument("--limit", type=int, help="only the first N drawn events")
    parser.add_argument("--locate-only", action="store_true", help="find the events and their pages; read no match")
    args = parser.parse_args()
    P.configure_stdout()
    events = draw_events(args.seed)
    if args.select_only:
        pd.set_option("display.width", 250)
        print(events[["tour", "iso_week", "week_start", "level", "hospitality", "city", "country", "surface",
                      "winner", "runner_up", "final_score", "names_source", "pool"]].to_string())
        return 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())

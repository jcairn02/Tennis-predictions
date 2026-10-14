"""TennisLive.net: a player's match list per season, then every match page's point-by-point and statistics.

How the site is read (observed 24 Sep 2026; the women's tour on 8 Oct 2026):
    GET /<atp|wta>/<slug>/                             the player page; its window.TENNISLIVE_RUNTIME JSON carries a
                                                       per-session request token, the seasons of the career table and
                                                       the latest 50 matches
    GET /api/player-matches?tour=<atp|wta>&slug=<slug>&discipline=singles&year=<season>&surface=all&offset=<n>
                                                       one season's matches (limit 60 per page), with the token and the
                                                       same-origin fetch headers a browser sends; robots.txt disallows
                                                       this path (the owner chose to read it; see common.py)
    GET /<atp|wta>/match/<p1>-VS-<p2>/<tournament>-<year>/
                                                       the match page: metadata in its runtime JSON, then server-side
                                                       HTML with every game's point states and the match statistics

Players are named by slug; a women's player as ``wta:<slug>`` (or every bare slug with --tour wta).

Raw layout under data/raw/point_sources/tennislive/:
    players/<slug>/page.html.gz                        an ATP player's page of the latest run
    players/<slug>/matches_<season>_<offset>.json      API pages (the current season is refetched each run)
    players/wta/<slug>/...                             the same for a WTA player
    matches/<atp|wta>/<p1>-VS-<p2>/<tournament>-<year>.html.gz
                                                       match pages (HTTP 404 is recorded and not retried)
    calendar/, tournaments/, session/                  the event mode (tennislive_events.py)
    _receipts.jsonl

Staged (data/dump/points/tennislive/): index.parquet (every match of every player listing on disk), matches.parquet
(every match page on disk, whether a player listing, the event mode's samples or the gap mode asked for it;
`sampled_in` and `gaps_in` name the sample and the gaps), games.parquet,
points.parquet, statistics.parquet, all strings; events.parquet and listed.parquet come from tennislive_events.py.
Summary: data/studies/point_shot_sources/scrape/tennislive_summary.json.

Usage:
    ./python.sh -m src.ingest.point_sources.tennislive                       # the ten career-coverage players
    ./python.sh -m src.ingest.point_sources.tennislive --slugs brandon-holt --seasons 2022,2023 --limit 5
    ./python.sh -m src.ingest.point_sources.tennislive --slugs wta:anna-siskova --seasons 2026 --skip-matches
    ./python.sh -m src.ingest.point_sources.tennislive --stage-only

Point record shape: each game block shows the games score before and after, the server, the score states
after each point in fixed player order (player 1 first), markers such as "BP" on a state, and the game's
winner; the game-winning point is implied except in tiebreaks. No clock time is shown.
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

from bs4 import BeautifulSoup, NavigableString, Tag

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P

SOURCE = "tennislive"
SITE = "https://www.tennislive.net"
IMPERSONATE = "safari"
API_HEADERS = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest", "Sec-Fetch-Dest": "empty",
               "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin"}
STUDY_SLUGS = {"CH12": "jan-choinski", "G0BY": "daniil-glinka", "H09P": "brandon-holt", "H0A4": "nick-hardt",
               "O0A2": "gauthier-onclin", "P0HY": "samuele-pieri", "P0I6": "gabriele-piraino",
               "S0GZ": "nikolas-sanchez-izquierdo", "V0F6": "nicolas-villalon", "W09E": "adam-walton"}
REGULAR_POINTS = {"0", "15", "30", "40", "A", "AD"}
MATCH_URL = re.compile(r"^/(?P<tour>atp|wta)/match/(?P<players>[^/]+)/(?P<tournament>[^/]+)/?$")
TOURS = ("atp", "wta")
# the event mode's frozen samples (tennislive_events.py): which sample asked for a page
SAMPLES_CSV = P.PROJECT_ROOT / "data" / "studies" / "gap_downloads" / "tennislive_samples.csv"
# the gap mode's per-target tables (tennislive_gaps.py, tennislive_<gap>_matches.csv.gz): which gaps want a page
GAP_TABLES = P.PROJECT_ROOT / "data" / "studies" / "gap_downloads"

INDEX_COLUMNS = ["slug", "player_tour", "season", "match_id", "url", "state", "doubles", "start_timestamp", "start_utc",
                 "start_times", "stage", "stage_code", "tournament_id", "tournament_name", "tournament_url",
                 "tournament_country", "surface", "surface_code", "tournament_rank", "round_id", "tour", "info",
                 "player1_id", "player1_name", "player1_url", "player1_seed", "player1_ranking", "player1_sets_won",
                 "player1_sets", "player2_id", "player2_name", "player2_url", "player2_seed", "player2_ranking",
                 "player2_sets_won", "player2_sets", "set_winners", "winner_id", "end_reason", "focus_result",
                 "index_file"]
MATCH_COLUMNS = ["url", "players_slug", "tournament_slug", "tour", "page_status", "page_sha256", "retrieved_at",
                 "state", "status_label", "end_reason", "best_of", "score", "sets", "tournament_rank",
                 "player1_id", "player1_name", "player1_url", "player1_seed", "player1_ranking", "player1_ranking_date",
                 "player1_sets_won", "player2_id", "player2_name", "player2_url", "player2_seed", "player2_ranking",
                 "player2_ranking_date", "player2_sets_won", "set_winners", "winner_id", "doubles",
                 "tournament_id", "tournament_name", "tournament_url", "tournament_country", "surface", "surface_code",
                 "stage", "stage_code", "start_times", "reference_timestamp", "reference_utc", "date_shown",
                 "start_shown", "round_shown",
                 "surface_shown", "tour_shown", "format_shown", "pbp_available", "pbp_unavailable_notice", "sets_listed",
                 "games_listed", "games_without_points", "points_listed", "first_server_index", "stats_available",
                 "stats_rows", "listed_for_slugs", "sampled_in", "gaps_in"]
GAME_COLUMNS = ["url", "set", "game", "before", "after", "server_index", "server_name", "outcome", "winner_index",
                "label", "states", "markers", "points_listed", "tiebreak"]
POINT_COLUMNS = ["url", "set", "game", "point", "state", "player1_point", "player2_point", "markers", "tiebreak",
                 "server_index"]
STAT_COLUMNS = ["url", "period", "name", "player1_value", "player1_detail", "player2_value", "player2_detail", "note"]


# --------------------------------------------------------------------------------------
# parsing (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def runtime_object(html: str) -> dict:
    """The window.TENNISLIVE_RUNTIME JSON a page embeds ({} when absent)."""
    marker = "window.TENNISLIVE_RUNTIME = "
    start = html.find(marker)
    if start < 0:
        return {}
    start += len(marker)
    end = html.find("</script>", start)
    text = html[start:end].strip().rstrip(";")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def player_ref(spec: str, default_tour: str = "atp") -> tuple[str, str]:
    """(tour, slug) of a player named on the command line: 'wta:anna-siskova' -> ('wta', 'anna-siskova'); a bare
    slug takes ``default_tour``."""
    tour, sep, slug = spec.strip().partition(":")
    if sep and tour in TOURS:
        return tour, slug.strip()
    return default_tour, spec.strip()


def player_key(tour: str, slug: str) -> str:
    """How a player is written in the staged tables: the bare slug for the ATP (the ten careers' form), else
    'wta:<slug>'."""
    return slug if tour == "atp" else f"{tour}:{slug}"


def player_parts(tour: str, slug: str) -> tuple[str, ...]:
    """A player's raw folder below the source: players/<slug>/ for the ATP (the layout the ten careers were
    collected in), players/wta/<slug>/ for the WTA. The same parts name the receipts."""
    return ("players", slug) if tour == "atp" else ("players", tour, slug)


def index_rows(slug: str, season: str, payload: dict, index_file: str, tour: str = "atp") -> list[dict]:
    """One row per match in a player-matches API page (or the page-embedded initial selection)."""
    rows = []
    data = payload.get("data") if "data" in payload else payload
    for group in (data or {}).get("groups") or []:
        for n, match in enumerate(group.get("matches") or []):
            players = match.get("players") or []
            p1 = players[0] if len(players) > 0 else {}
            p2 = players[1] if len(players) > 1 else {}
            ts = match.get("startTimestamp")
            start_times = group.get("startTimes") or []
            rows.append({
                "slug": slug, "player_tour": tour, "season": season, "match_id": match.get("id"), "url": match.get("url"),
                "state": match.get("state"), "doubles": match.get("doubles"), "start_timestamp": ts,
                "start_utc": _utc(ts), "start_times": ";".join(str(x) for x in start_times),
                "stage": match.get("stage") or group.get("stage"), "stage_code": match.get("stageCode") or group.get("stageCode"),
                "tournament_id": group.get("tournamentId") or group.get("id"), "tournament_name": group.get("name"),
                "tournament_url": group.get("url"), "tournament_country": group.get("country"),
                "surface": group.get("surface"), "surface_code": group.get("surfaceCode"),
                "tournament_rank": group.get("rank"), "round_id": group.get("roundId"), "tour": group.get("tour"),
                "info": group.get("info"),
                "player1_id": p1.get("id"), "player1_name": p1.get("name"), "player1_url": p1.get("url"),
                "player1_seed": p1.get("seed"), "player1_ranking": p1.get("ranking"), "player1_sets_won": p1.get("setsWon"),
                "player1_sets": _sets(p1.get("sets")),
                "player2_id": p2.get("id"), "player2_name": p2.get("name"), "player2_url": p2.get("url"),
                "player2_seed": p2.get("seed"), "player2_ranking": p2.get("ranking"), "player2_sets_won": p2.get("setsWon"),
                "player2_sets": _sets(p2.get("sets")),
                "set_winners": ";".join(str(x) for x in match.get("setWinners") or []),
                "winner_id": match.get("winnerId"), "end_reason": match.get("endReason"),
                "focus_result": match.get("focusResult"), "index_file": index_file,
            })
    return rows


def _sets(sets) -> str | None:
    """Set scores as text: a set is an int, or {"score": 7, "detail": 7} for a tiebreak set -> "7(7)"."""
    if not sets:
        return None
    out = []
    for item in sets:
        if isinstance(item, dict):
            score, detail = item.get("score"), item.get("detail")
            out.append(f"{score}({detail})" if detail is not None else str(score))
        else:
            out.append(str(item))
    return " ".join(out)


def _utc(ts) -> str | None:
    try:
        return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else None
    except (TypeError, ValueError, OSError):
        return None


def parse_match_page(html: str) -> dict:
    """Metadata, games, points and statistics of one match page."""
    rt = runtime_object(html)
    summary = rt.get("matchDetailInitialSummary") or {}
    table = rt.get("matchDetailTableMatch") or {}
    group = rt.get("matchDetailTableGroup") or {}
    # only the <main> element holds the records; skipping the header, scripts and footer halves the parse time
    start, end = html.find("<main"), html.rfind("</main>")
    soup = BeautifulSoup(html[start:end + 7] if 0 <= start < end else html, "html.parser")
    i18n = rt.get("i18n") or {}
    unavailable_text = i18n.get("match_progress_unavailable") or "Complete game and point progress is not available"
    stats_unavailable_text = i18n.get("match_statistics_unavailable") or "Statistics are not available"
    main = soup.find("main") or soup
    main_text = main.get_text(" ", strip=True)
    games = parse_progress(main)
    statistics = parse_statistics(main)
    shown = parse_meta_list(main)
    players = table.get("players") or summary.get("players") or []
    p1 = players[0] if len(players) > 0 else {}
    p2 = players[1] if len(players) > 1 else {}
    played = [g for g in games if g["game"] > 0]
    first_server = next((g["server_index"] for g in games if g["game"] == 0), None)
    if first_server is None and played:
        first_server = played[0]["server_index"]
    meta = {
        "state": summary.get("state") or table.get("state"), "status_label": summary.get("statusLabel"),
        "end_reason": summary.get("endReason") or table.get("endReason"), "best_of": summary.get("bestOf"),
        "score": summary.get("score"), "sets": _sets_pairs(summary.get("sets")),
        "tournament_rank": summary.get("tournamentRank"),
        "player1_id": p1.get("id"), "player1_name": p1.get("name"), "player1_url": p1.get("url"),
        "player1_seed": p1.get("seed"), "player1_ranking": p1.get("ranking"), "player1_ranking_date": p1.get("rankingDate"),
        "player1_sets_won": p1.get("setsWon"),
        "player2_id": p2.get("id"), "player2_name": p2.get("name"), "player2_url": p2.get("url"),
        "player2_seed": p2.get("seed"), "player2_ranking": p2.get("ranking"), "player2_ranking_date": p2.get("rankingDate"),
        "player2_sets_won": p2.get("setsWon"),
        "set_winners": ";".join(str(x) for x in table.get("setWinners") or []),
        "winner_id": table.get("winnerId"), "doubles": rt.get("matchDetailDoubles"),
        "tournament_id": group.get("id"), "tournament_name": group.get("name"), "tournament_url": group.get("url"),
        "tournament_country": group.get("country"), "surface": group.get("surface"), "surface_code": group.get("surfaceCode"),
        "stage": group.get("stage"), "stage_code": group.get("stageCode"),
        "start_times": ";".join(str(x) for x in group.get("startTimes") or []),
        "reference_timestamp": rt.get("matchDetailReferenceTimestamp"),
        "reference_utc": _utc(rt.get("matchDetailReferenceTimestamp")),
        "date_shown": shown.get("Date"), "start_shown": shown.get("Start"),      # the sidebar's start (often blank)
        "round_shown": shown.get("Round"), "surface_shown": shown.get("Surface"),
        "tour_shown": shown.get("Tour"), "format_shown": shown.get("Format"),
        "pbp_available": bool(played), "pbp_unavailable_notice": unavailable_text.rstrip(".") in main_text,
        "sets_listed": len({g["set"] for g in played}), "games_listed": len(played),
        "games_without_points": sum(1 for g in played if not g["points"]),
        "points_listed": sum(len(g["points"]) for g in played), "first_server_index": first_server,
        "stats_available": bool(statistics), "stats_rows": len(statistics),
        "stats_unavailable_notice": stats_unavailable_text.rstrip(".") in main_text,
        "player_names": rt.get("matchDetailPlayerNames") or [p1.get("name"), p2.get("name")],
    }
    return {"meta": meta, "games": games, "statistics": statistics}


def _sets_pairs(sets) -> str | None:
    if not sets:
        return None
    return " ".join(f"{a}-{b}" for a, b in sets if isinstance((a, b), tuple))


def parse_meta_list(root) -> dict:
    """The sidebar's <dl> of Date / Start / Round / Surface / Tour / Format."""
    out = {}
    for dl in root.find_all("dl"):
        for div in dl.find_all("div", recursive=False):
            dt_, dd = div.find("dt"), div.find("dd")
            if dt_ and dd:
                out.setdefault(dt_.get_text(strip=True), dd.get_text(" ", strip=True))
    return out


def parse_progress(root) -> list[dict]:
    """Every game block: the start marker as game 0, then the games of each set in order."""
    games = []
    for panel in root.select("section[data-set-panel]"):
        try:
            set_no = int(panel.get("data-set-panel"))
        except (TypeError, ValueError):
            continue
        game_no = 0
        for block in panel.select("div.tl-progress-game"):
            game = parse_game_block(block)
            if game is None:
                continue
            # A block whose games score does not move and that lists no points is the set's start marker (who
            # serves first). A block whose score moves is a game even when its points are missing, which the
            # site does for some opening games of a set: it is kept, with no points, so that games stay countable.
            if game["outcome"] is None and not game["points"] and game["before"] == game["after"]:
                game["game"] = 0
            else:
                game_no += 1
                game["game"] = game_no
            game["set"] = set_no
            games.append(game)
    return games


def parse_game_block(block: Tag) -> dict | None:
    strong = block.find("strong")
    if strong is None:
        return None
    after = strong.get_text(strip=True)
    before = None
    prev = strong.find_previous_sibling("span")
    if prev is not None:
        before = prev.get_text(" ", strip=True).replace("→", "").strip()
    ball = block.find(attrs={"data-progress-server-ball": True})
    server_index = None
    if ball is not None:
        try:
            server_index = int(ball.get("data-player-index"))
        except (TypeError, ValueError):
            server_index = None
    server_name = None
    if ball is not None and ball.parent is not None:
        text = ball.parent.get_text(" ", strip=True)
        server_name = re.sub(r"\s+serves?$", "", text).strip() or None
    outcome_tag = block.find(attrs={"data-progress-outcome": True})
    outcome = outcome_tag.get_text(" ", strip=True) if outcome_tag is not None else None
    points: list[dict] = []
    if outcome_tag is not None and outcome_tag.parent is not None:
        for node in outcome_tag.parent.children:
            if isinstance(node, NavigableString):
                for token in str(node).split():
                    if re.fullmatch(r"[0-9A]+-[0-9A]+", token):
                        points.append({"state": token, "markers": []})
            elif isinstance(node, Tag):
                if node is outcome_tag:
                    break
                title = node.get("title") or node.get("aria-label")
                if title and points:
                    points[-1]["markers"].append(title)
    label_parts = []
    for side in block.find_all("div", recursive=False):
        if side.find("strong") is None and side.find(attrs={"data-progress-server-ball": True}) is None:
            text = side.get_text(" ", strip=True)
            if text:
                label_parts.append(text)
    tiebreak = any(part not in REGULAR_POINTS for p in points for part in p["state"].split("-"))
    return {"before": before, "after": after, "server_index": server_index, "server_name": server_name,
            "outcome": outcome, "points": points, "label": " | ".join(label_parts) or None, "tiebreak": tiebreak}


def parse_statistics(root) -> list[dict]:
    rows = []
    for panel in root.select("[data-live-stats-panel]"):
        period = panel.get("data-live-stats-panel")
        for row in panel.select("div.tl-match-stat-row"):
            values = row.select("strong.tl-match-stat-value")
            label = row.select_one(".tl-match-stat-label")
            if len(values) < 2 or label is None:
                continue
            note = row.select_one(".tl-match-stat-note")
            rows.append({"period": period, "name": label.get_text(" ", strip=True),
                         "player1_value": _stat_value(values[0]), "player1_detail": _stat_detail(values[0]),
                         "player2_value": _stat_value(values[1]), "player2_detail": _stat_detail(values[1]),
                         "note": note.get_text(" ", strip=True) if note is not None else None})
    return rows


def _stat_value(strong: Tag) -> str | None:
    span = strong.find("span")
    return span.get_text(strip=True) if span is not None else strong.get_text(strip=True)


def _stat_detail(strong: Tag) -> str | None:
    detail = strong.find(attrs={"data-stat-detail": True})
    return detail.get_text(strip=True) if detail is not None else None


def winner_index(outcome: str | None, names: list) -> int | None:
    if not outcome:
        return None
    for i, name in enumerate(names):
        if name and outcome.startswith(str(name)):
            return i
    return None


def match_path_parts(url: str) -> tuple[str, str, str] | None:
    m = MATCH_URL.match(url or "")
    return (m.group("tour"), m.group("players"), m.group("tournament")) if m else None


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
def fetch_player_index(client: P.Client, receipts, slug: str, *, seasons: list[str] | None, refresh: bool,
                       this_year: int, tour: str = "atp") -> dict:
    """The player page (fresh, for the session token) and one API page per season and offset."""
    parts = player_parts(tour, slug)
    folder = "/".join(parts)
    page_dest = P.raw_path(SOURCE, *parts, "page.html.gz")
    receipt = P.fetch(client, f"{SITE}/{tour}/{slug}/", page_dest, receipts, name=f"{folder}/page", refresh=True,
                      validator=P.html_validator, compress=True, extra={"slug": slug, "tour": tour})
    if receipt.get("error") or receipt.get("status") != 200:
        return {"slug": slug, "tour": tour, "error": receipt.get("error") or f"HTTP {receipt.get('status')}", "pages": 0}
    html = P.read_bytes(page_dest).decode("utf-8", errors="replace")
    rt = runtime_object(html)
    token = rt.get("playerLiveRequestToken") or ""
    career = ((rt.get("playerDetailStatisticsPreload") or {}).get("careerRows")) or []
    available = [str(row.get("year")) for row in career if str(row.get("year", "")).isdigit()]
    wanted = [s_ for s_ in (seasons or available) if s_ in available] if seasons else available
    out = {"slug": slug, "tour": tour, "name": rt.get("playerDetailName"), "seasons_available": available,
           "seasons_fetched": [], "pages": 0, "matches_listed": 0, "errors": []}
    headers = {**API_HEADERS, "X-TennisLive-Token": token, "Referer": f"{SITE}/{tour}/{slug}/"}
    for season in wanted:
        offset, total = 0, None
        while True:
            dest = P.raw_path(SOURCE, *parts, f"matches_{season}_{offset}.json")
            url = (f"{SITE}/api/player-matches?tour={tour}&slug={slug}&discipline=singles&year={season}"
                   f"&surface=all&offset={offset}")
            receipt = P.fetch(client, url, dest, receipts, name=f"{folder}/matches_{season}_{offset}",
                              refresh=refresh or int(season) >= this_year, validator=P.json_validator,
                              headers=headers, extra={"slug": slug, "tour": tour, "season": season, "offset": offset})
            if receipt.get("error") or receipt.get("status") != 200:
                out["errors"].append(f"{season}/{offset}: {receipt.get('error') or receipt.get('status')}")
                break
            payload = P.read_json(dest)
            data = payload.get("data") or {}
            if payload.get("status") != "ok":
                out["errors"].append(f"{season}/{offset}: {payload.get('error') or 'status not ok'}")
                break
            out["pages"] += 1
            count = sum(len(g.get("matches") or []) for g in data.get("groups") or [])
            out["matches_listed"] += count
            total = data.get("total")
            limit = data.get("limit") or 60
            offset += limit
            if total is None or offset >= int(total) or count == 0:
                break
        out["seasons_fetched"].append(season)
    return out


def player_index_files(slug: str, tour: str = "atp") -> list[Path]:
    folder = P.raw_path(SOURCE, *player_parts(tour, slug))
    return sorted(folder.glob("matches_*_*.json")) if folder.exists() else []


def players_on_disk() -> list[tuple[str, str]]:
    """(tour, slug) of every player whose listing pages are on disk."""
    out = []
    root = P.raw_path(SOURCE, "players")
    if not root.exists():
        return out
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        if folder.name in TOURS and folder.name != "atp":       # players/wta/<slug>/
            out += [(folder.name, sub.name) for sub in sorted(folder.iterdir()) if player_index_files(sub.name, folder.name)]
        elif player_index_files(folder.name):
            out.append(("atp", folder.name))
    return out


def load_index(players: list) -> list[dict]:
    """Every listed match of the given players, each a (tour, slug) pair or a slug as written on the command line."""
    rows = []
    for player in players:
        tour, slug = player if isinstance(player, tuple) else player_ref(player)
        for path in player_index_files(slug, tour):
            season = path.stem.split("_")[1]
            rows.extend(index_rows(slug, season, P.read_json(path), P.rel(path), tour=tour))
    return rows


def match_dest(url: str) -> Path | None:
    parts = match_path_parts(url)
    if parts is None:
        return None
    tour, players, tournament = parts
    return P.raw_path(SOURCE, "matches", tour, players, f"{tournament}.html.gz")


def fetch_match(client: P.Client, receipts, url: str, *, refresh: bool, extra: dict | None = None) -> dict:
    """A match page; ``extra`` goes into its receipt (the event mode names the sample that asked for it)."""
    dest = match_dest(url)
    if dest is None:
        return {"error": f"not a match url: {url}"}
    return P.fetch(client, SITE + url, dest, receipts, name=f"matches{url}", refresh=refresh,
                   validator=P.html_validator, compress=True, extra={"match_url": url, **(extra or {})})


def page_receipts(receipts) -> dict[str, dict]:
    """Match URL -> the receipt of its page, for every match page asked for (by a listing or a sample)."""
    out = {}
    for name, r in receipts.all().items():
        if name.startswith("matches/") and r.get("match_url"):
            out[r["match_url"]] = r
    return out


def sampled_pages() -> dict[str, str]:
    """Match URL -> the event mode's sample that drew it (a page fetched earlier for a career keeps its receipt)."""
    if not SAMPLES_CSV.exists():
        return {}
    import csv

    with SAMPLES_CSV.open(encoding="utf-8", newline="") as handle:
        return {row["url"]: row["sample"] for row in csv.DictReader(handle) if row.get("url")}


def gap_pages() -> dict[str, str]:
    """Match URL -> the gaps whose targets the gap mode (tennislive_gaps.py) linked to the page and asks it for,
    from its per-target tables ('challenger_points_2018_2021', or two gaps joined by ';')."""
    import csv
    import gzip

    out: dict[str, set] = {}
    for path in sorted(GAP_TABLES.glob("tennislive_*_matches.csv.gz")):
        with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("tl_url") and row.get("tl_selected") == "True":
                    out.setdefault(row["tl_url"], set()).add(row["gap"])
    return {url: ";".join(sorted(gaps)) for url, gaps in out.items()}


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def stage(receipts, players: list | None = None) -> dict:
    """Rebuild the staged tables: the listings of ``players`` (default: every player on disk) and every match
    page a listing or a sample asked for."""
    players = players_on_disk() if players is None else players
    index = load_index(players)
    listed_for: dict[str, list[str]] = {}
    for row in index:
        key = player_key(row["player_tour"], row["slug"])
        if row["url"] and key not in listed_for.setdefault(row["url"], []):
            listed_for[row["url"]].append(key)
    asked = page_receipts(receipts)
    sampled = sampled_pages()
    gaps = gap_pages()
    match_rows, game_rows, point_rows, stat_rows = [], [], [], []
    for url in sorted(set(listed_for) | set(asked)):
        receipt = receipts.get(f"matches{url}") or {}
        parts = match_path_parts(url) or (None, None, None)
        row = {"url": url, "tour": parts[0], "players_slug": parts[1], "tournament_slug": parts[2],
               "page_status": receipt.get("error") or receipt.get("status"), "page_sha256": receipt.get("sha256"),
               "retrieved_at": receipt.get("retrieved_at"), "listed_for_slugs": ";".join(listed_for.get(url, [])) or None,
               "sampled_in": receipt.get("sample") or sampled.get(url), "gaps_in": gaps.get(url)}
        dest = match_dest(url)
        if receipt.get("status") == 200 and not receipt.get("error") and dest and dest.exists():
            parsed = parse_match_page(P.read_bytes(dest).decode("utf-8", errors="replace"))
            names = parsed["meta"].pop("player_names")
            parsed["meta"].pop("stats_unavailable_notice", None)
            row.update(parsed["meta"])
            for g in parsed["games"]:
                if g["game"] == 0:
                    continue
                game_rows.append({"url": url, "set": g["set"], "game": g["game"], "before": g["before"], "after": g["after"],
                                  "server_index": g["server_index"], "server_name": g["server_name"],
                                  "outcome": g["outcome"], "winner_index": winner_index(g["outcome"], names),
                                  "label": g["label"], "states": " ".join(p["state"] for p in g["points"]),
                                  "markers": ";".join(f"{n}:{'|'.join(p['markers'])}" for n, p in enumerate(g["points"], 1) if p["markers"]) or None,
                                  "points_listed": len(g["points"]), "tiebreak": g["tiebreak"]})
                for n, p in enumerate(g["points"], 1):
                    a, _, b = p["state"].partition("-")
                    point_rows.append({"url": url, "set": g["set"], "game": g["game"], "point": n, "state": p["state"],
                                       "player1_point": a, "player2_point": b, "markers": "|".join(p["markers"]) or None,
                                       "tiebreak": g["tiebreak"], "server_index": g["server_index"]})
            for st in parsed["statistics"]:
                stat_rows.append({"url": url, **st})
        match_rows.append(row)
    now = P.utc_now_iso()
    out = {}
    for name, columns, rows in (("index", INDEX_COLUMNS, index), ("matches", MATCH_COLUMNS, match_rows),
                                ("games", GAME_COLUMNS, game_rows), ("points", POINT_COLUMNS, point_rows),
                                ("statistics", STAT_COLUMNS, stat_rows)):
        dest = P.dump_path(SOURCE, f"{name}.parquet")
        table = [[P.s(r.get(c)) for c in columns] for r in rows]
        stats = P.stage_table(SOURCE, dest, columns, table, source_file=P.rel(P.raw_path(SOURCE)), retrieved_at=now,
                              extra={"slugs": ";".join(player_key(t, s_) for t, s_ in players)})
        out[name] = {"rows": stats["rows"], "dest": stats["dest"], "bytes": stats["bytes"]}
        P.log(f"[{SOURCE}] staged {stats['dest']}: {stats['rows']:,} rows")
    return out


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    specs = [s_ for s_ in args.slugs.split(",") if s_.strip()] if args.slugs else list(STUDY_SLUGS.values())
    players = [player_ref(s_, args.tour) for s_ in specs]
    seasons = [s_.strip() for s_ in args.seasons.split(",") if s_.strip()] if args.seasons else None
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "started_at": P.utc_now_iso(), "args": vars(args), "players": {}}
    client = None
    if not args.stage_only:
        client = P.Client(IMPERSONATE, min_interval=args.min_interval, jitter=args.jitter, max_requests=args.max_requests)
    this_year = dt.date.today().year
    outcomes = Counter()
    selected: list[dict] = []
    try:
        if not args.stage_only and not args.skip_index:
            for tour, slug in players:
                info = fetch_player_index(client, receipts, slug, seasons=seasons, refresh=args.refresh_index,
                                          this_year=this_year, tour=tour)
                summary["players"][player_key(tour, slug)] = info
                P.log(f"[{SOURCE}] {player_key(tour, slug)}: {info.get('pages', 0)} index pages, "
                      f"{info.get('matches_listed', 0)} matches ({', '.join(info.get('errors') or []) or 'ok'})")
        index = load_index(players)
        seen = set()
        for row in sorted(index, key=lambda r: -(int(r["start_timestamp"] or 0))):
            url = row["url"]
            if not url or url in seen or not match_path_parts(url):
                continue
            if not args.doubles and row.get("doubles"):
                continue
            if args.states and row.get("state") not in args.states.split(","):
                continue
            if seasons and str(row.get("season")) not in seasons:
                continue
            seen.add(url)
            selected.append(row)
        if args.limit:
            selected = selected[:args.limit]
        summary["matches_listed"] = len({r["url"] for r in index if r["url"]})
        summary["matches_selected"] = len(selected)
        P.log(f"[{SOURCE}] {summary['matches_listed']} distinct matches listed; {len(selected)} selected")
        if not args.stage_only and not args.skip_matches:
            for n, row in enumerate(selected, 1):
                receipt = fetch_match(client, receipts, row["url"], refresh=args.refresh)
                outcomes[f"page:{receipt.get('error') or receipt.get('status')}" + (":cached" if receipt.get("skipped") else "")] += 1
                if n % 50 == 0 or n == len(selected):
                    P.log(f"[{SOURCE}] {n}/{len(selected)} pages; requests={client.requests}; " +
                          ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items())))
    except (P.Blocked, P.BudgetExhausted) as stop:
        summary["stopped"] = f"{type(stop).__name__}: {stop}"
        P.log(f"[{SOURCE}] STOPPED: {stop}")
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    if client is not None:
        summary["client"] = client.stats()
    if not args.no_stage:
        summary["staged"] = stage(receipts)
        summary.update(summarize())
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = P.write_summary("tennislive_summary.json", summary)
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def summarize() -> dict:
    """Listed matches by season and state, and page outcomes by season, from the staged files."""
    import pyarrow.parquet as pq

    out = {}
    index_path = P.dump_path(SOURCE, "index.parquet")
    matches_path = P.dump_path(SOURCE, "matches.parquet")
    if index_path.exists():
        idx = pq.read_table(index_path, columns=["url", "season", "state", "doubles"]).to_pylist()
        by = Counter(f"{r['season']}|{'doubles' if r['doubles'] == 'TRUE' else 'singles'}|{r['state']}" for r in idx)
        out["listed_by_season_kind_state"] = dict(sorted(by.items()))
    if matches_path.exists():
        m = pq.read_table(matches_path, columns=["url", "tournament_slug", "page_status", "pbp_available", "stats_available",
                                                 "reference_utc"]).to_pylist()
        by = Counter()
        for r in m:
            year = (r["reference_utc"] or "")[:4] or (r["tournament_slug"] or "")[-4:]
            status = r["page_status"] or "not fetched"
            pbp = "pbp" if r["pbp_available"] == "TRUE" else ("no pbp" if status == "200" else "")
            by[f"{year}|{status}|{pbp}".rstrip("|")] += 1
        out["pages_by_year_status_pbp"] = dict(sorted(by.items()))
    return out


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--slugs", help="comma list of TennisLive player slugs, a women's player as wta:<slug> "
                                        "(default: the ten study players)")
    parser.add_argument("--tour", choices=TOURS, default="atp", help="the tour of every bare slug (default atp)")
    parser.add_argument("--seasons", help="comma list of seasons to index and fetch (default: every season listed)")
    parser.add_argument("--states", default="finished", help="comma list of match states to fetch pages for")
    parser.add_argument("--doubles", action="store_true", help="also fetch doubles matches (default: singles only)")
    parser.add_argument("--limit", type=int, help="fetch only the N most recent selected match pages (dry runs)")
    parser.add_argument("--max-requests", type=int, help="stop after this many HTTP requests")
    parser.add_argument("--min-interval", type=float, default=1.5, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=1.0)
    parser.add_argument("--refresh", action="store_true", help="refetch match pages already on disk (404s included)")
    parser.add_argument("--refresh-index", action="store_true", help="refetch every season's index pages")
    parser.add_argument("--skip-index", action="store_true", help="use the index pages already on disk")
    parser.add_argument("--skip-matches", action="store_true", help="index only; fetch no match pages")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rebuild the Parquet tables and summary")
    parser.add_argument("--no-stage", action="store_true", help="fetch only; skip the Parquet rebuild")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    return 1 if summary.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())

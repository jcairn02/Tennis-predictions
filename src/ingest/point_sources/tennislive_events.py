"""TennisLive.net by event: every tournament of 2018-2026 the site lists, each listed whole from its results section,
and two seeded samples of match pages (work package P4 of docs/studies/gap_downloads/collection-plan.md).

The player adapter (tennislive.py) lists one career at a time. A results section lists a whole event in one request:
qualifying, main draw and doubles, each match with its score, winner, page URL and start time.

How the site is read (observed 8 Oct 2026):
    GET /<YYYY-MM-DD>/   a date page. Its window.TENNISLIVE_RUNTIME JSON holds `tournamentCatalog` (every event of the
                         date's week, Monday to Sunday, that has a tournament page), `homepageTournamentMenu` (every
                         event with a match that day, an event without a page included, its url empty) and
                         `homepageTournaments` (every match of that day, by event and round: as many as the page's
                         matchCounts.all on the days checked). The collection plan expected no calendar ("events are
                         found through players"); the date pages are one, so no player listing is needed here.
    GET /                the home page, read for the session token when no page has been read in this run
    GET /api/tournament-section?tour=<atp|wta>&slug=<event>&section=results
                         the whole event by round, with the token and same-origin headers of tennislive.API_HEADERS.
                         A token from another session is refused with HTTP 403 (gap probe, 29 Sep 2026): one new
                         session is opened, and a second refusal stops the run.
    GET /<atp|wta>/match/<p1>-VS-<p2>/<event>/   a match page (tennislive.parse_match_page), for the samples only

Steps:
1. Calendar: the Wednesday date page of every ISO week from 2018-W01 to the last complete week.
2. Events: every event the catalogs and menus name, once (by tour and TennisLive id), with the weeks it was seen in,
   classified from its rank and name (event_kind): itf, challenger, wta125, tour, slam, finals; team, junior and
   other events are not listed.
3. Results: one results-section request per target event that has a page, newest first. An answer fetched while
   matches were still to be played is fetched again on a later run.
4. Events without a page (--pageless-days): their matches only appear on date pages, so the date pages of every
   day of their weeks (Saturday before to Sunday) are read as well.
5. Samples, drawn once every target event is listed and frozen in data/studies/gap_downloads/tennislive_samples.csv
   (seeded; one match per event):
   * itf_main_since_june_2026: 200 main-draw singles pages of ITF events since 1 June 2026, 100 a tour;
   * itf_qualifying_2019_2026: 200 ITF qualifying singles pages of 2019-2026, 100 a tour, 12-13 a year.
6. Stage (data/dump/points/tennislive/, all strings): events.parquet (one row per event), listed.parquet (every match
   of every results section, and of the date pages of events without a page), and tennislive.stage() for the pages
   (matches, games, points, statistics; `sampled_in` names the sample).
7. Evidence (data/studies/gap_downloads/): tennislive_events.csv.gz (each event: weeks, results, counts),
   tennislive_editions.csv.gz (each edition of the data map's match table and the event it links to by player
   pairs), tennislive_samples.csv (each sampled page: points, completeness, statistics), tennislive_summary.json and
   a line in runs.jsonl.

Raw (data/raw/point_sources/tennislive/, the player adapter's folder and receipts, gzipped as served):
    calendar/<date>.html.gz   session/<stamp>.html.gz   tournaments/<atp-men|wta-women>/<event>__results.json.gz
    matches/<atp|wta>/<p1>-VS-<p2>/<event>.html.gz   _receipts.jsonl   _logs/

Pace and stops are common.Client's: Safari's TLS fingerprint, one request at a time, 1.5 s + up to 1 s between
starts by default, a --max-requests budget, and a stop on HTTP 429, a challenge or a second 403. Every answer is
kept with a receipt and nothing is asked twice. TennisLive's terms forbid automated extraction and its robots.txt
disallows /api/; collected under the owner's decision of 8 Oct 2026 (docs/decisions/2026-10-08-scraping-approved.md).

Usage:
    ./python.sh -m src.ingest.point_sources.tennislive_events --weeks 2026-W27:2026-W36 --limit 12 --max-requests 60
    ./python.sh -m src.ingest.point_sources.tennislive_events --pageless-days --max-requests 25000
    ./python.sh -m src.ingest.point_sources.tennislive_events --stage-only
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

import pandas as pd

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import tennislive as TL

SOURCE = TL.SOURCE
SITE = TL.SITE
STUDY = P.PROJECT_ROOT / "data" / "studies" / "gap_downloads"
MAP_MATCHES = P.PROJECT_ROOT / "data" / "studies" / "data_map" / "matches.parquet"
TODAY = {"day": None}            # tests set the day a run stands on; None: the calendar's
SAMPLES_CSV = TL.SAMPLES_CSV
FIRST_WEEK = "2018-W01"
KINDS = ("itf", "challenger", "wta125", "tour", "slam", "finals")
SECTION_DIRS = {"atp": "atp-men", "wta": "wta-women"}
EVENT_URL = re.compile(r"^/(?P<dir>atp-men|wta-women)/(?P<slug>[^/#?]+)/?$")
# states a match can stay in; anything else (scheduled, live, interrupted ...) is still to be played
FINAL_STATES = {"finished", "retired", "walkover", "awarded", "cancelled", "canceled", "abandoned", "defaulted"}
SETTLE_DAYS = 7        # a results answer fetched this long after the last listed start is final, whatever it says
TEAM = re.compile(r"davis cup|fed cup|billie jean king|bjk cup|united cup|atp cup|laver cup|hopman|olympic|"
                  r"team cup|world team", re.I)
ITF_NAME = re.compile(r"(?:^|[\s(])(?:[MW]\d{2,3}(?:\+H)?|F\d{1,2})(?=[\s)]|$)")
BLOCK_WORDS = ("captcha", "challenge", "blocked", "too many", "rate limit", "access denied", "token", "session", "csrf")
SAMPLES = {"itf_main_since_june_2026": {"draw": "main", "since": "2026-06-01", "years": None},
           "itf_qualifying_2019_2026": {"draw": "qualifying", "since": None, "years": list(range(2019, 2027))}}
SAMPLE_SEED = 20261008
SAMPLE_PER_TOUR = 100

EVENT_COLUMNS = ["key", "url", "slug", "tl_id", "tour", "info", "rank", "kind", "name", "display_name", "label",
                 "menu_name", "group_name", "country", "country_iso2", "surface", "surface_code", "in_catalog",
                 "in_menu", "weeks", "first_week", "last_week", "wednesday_matches", "section_status",
                 "section_retrieved_at", "section_sha256", "section_file", "section_settled", "total_singles",
                 "total_doubles", "singles_main", "singles_main_played", "singles_qualifying",
                 "singles_qualifying_played", "doubles", "first_start_utc", "last_start_utc", "day_pages"]
LISTED_COLUMNS = ["event_key", "event_url", "event_id", "event_name", "event_kind", "event_rank", "tour", "listed_from",
                  "group_id", "stage", "stage_code", "round_id", "round", "draw", "discipline", "mixed", "junior",
                  "match_id", "identity", "url", "state", "set_label", "end_reason", "played", "winner_id",
                  "winner_side", "set_winners", "score", "player1_id", "player1_name", "player1_url", "player1_seed",
                  "player1_ranking", "player1_flag", "player1_sets_won", "player1_sets", "player1_members",
                  "player2_id", "player2_name", "player2_url", "player2_seed", "player2_ranking", "player2_flag",
                  "player2_sets_won", "player2_sets", "player2_members", "start_timestamp", "start_utc",
                  "group_start_time", "observed_started_at", "observed_current_set_started_at",
                  "observed_finished_at", "finished_at", "interrupted_at", "recently_finished_until",
                  "recently_interrupted_until", "duration", "draw_position", "storage",
                  "favorite_key", "current_set", "points", "server", "break_point", "point_markers", "source_file",
                  "source_sha256", "retrieved_at"]


# --------------------------------------------------------------------------------------
# weeks (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def parse_week(text: str) -> dt.date:
    """'2026-W27' -> the Monday of that ISO week."""
    m = re.fullmatch(r"\s*(\d{4})-W(\d{1,2})\s*", text or "")
    if not m:
        raise ValueError(f"not an ISO week like 2026-W27: {text!r}")
    return dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)


def last_complete_week(today: dt.date) -> dt.date:
    """The Monday of the last ISO week whose Sunday is before ``today``."""
    return today - dt.timedelta(days=today.weekday() + 7)


def wednesdays(first: dt.date, last: dt.date) -> list[dt.date]:
    """The Wednesday of every ISO week from the week of ``first`` to the week of ``last``."""
    monday = first - dt.timedelta(days=first.weekday())
    end = last - dt.timedelta(days=last.weekday())
    out = []
    while monday <= end:
        out.append(monday + dt.timedelta(days=2))
        monday += dt.timedelta(days=7)
    return out


def week_days(monday: dt.date) -> list[dt.date]:
    """The days whose date pages hold an event of this week: the Saturday before (qualifying) to the Sunday."""
    return [monday + dt.timedelta(days=n) for n in range(-2, 7)]


# --------------------------------------------------------------------------------------
# parsing (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def token_of(rt: dict) -> str | None:
    """A page's per-session request token (the same value under several names)."""
    for key in ("matchesRequestToken", "searchRequestToken", "tournamentDetailRequestToken", "playerLiveRequestToken",
                "matchDetailRequestToken"):
        if rt.get(key):
            return rt[key]
    return ((rt.get("account") or {}).get("csrfToken")) or None


def parse_calendar(html: str) -> dict:
    """The parts of a date page this mode reads."""
    rt = TL.runtime_object(html)
    return {"date": rt.get("matchesDate"), "week_label": (rt.get("footer") or {}).get("weekLabel"),
            "catalog": rt.get("tournamentCatalog") or [], "menu": rt.get("homepageTournamentMenu") or [],
            "groups": rt.get("homepageTournaments") or [], "match_count": (rt.get("matchCounts") or {}).get("all"),
            "token": token_of(rt)}


def norm_url(url) -> str | None:
    """An event URL as the catalog writes it ('/atp-men/<slug>/'), else None (an event without a page). A full URL,
    or a path Git Bash has prefixed with its own folder ('C:/Program Files/Git/atp-men/<slug>/'), is read too."""
    m = re.search(r"(?:^|/)(?P<dir>atp-men|wta-women)/(?P<slug>[^/#?\s]+)/?(?:[#?].*)?$", str(url or "").strip())
    return f"/{m.group('dir')}/{m.group('slug')}/" if m else None


def event_kind(tour: str | None, rank, name: str | None, info: str | None = None) -> str:
    """What an event is, from TennisLive's rank (0 ITF M15/W15 and 2018 Futures; 1 Challenger, WTA 125 and women's
    ITF W25-W100; 2 the 250s and 500s; 3 the 1000s; 4 the Slams; 5 team ties; 6 exhibitions, juniors and
    catch-alls) and its name."""
    n = str(name or "")
    low = n.lower()
    if str(info or "").upper() == "JUNIOR" or "junior" in low:
        return "junior"
    if TEAM.search(low):
        return "team"
    try:
        rank = int(rank)
    except (TypeError, ValueError):
        return "other"
    if rank >= 5:
        return "other"
    if rank == 4:
        return "slam"
    if "finals" in low or "elite trophy" in low:
        return "finals"
    if rank in (2, 3):
        return "tour"
    if rank == 0:
        return "itf"
    if tour == "atp":
        return "itf" if ITF_NAME.search(n) else "challenger"
    # WTA rank 1: W25-W100 name their level; a WTA 125 is named '<tournament> - <city>'; the 2018 ITF events of
    # $25,000 and more carry only their city
    if ITF_NAME.search(n):
        return "itf"
    return "wta125" if " - " in n or "125" in n else "itf"


def collect_events(pages: list[tuple[dt.date, dict]]) -> dict[str, dict]:
    """Every event the date pages name, keyed by '<tour>:<TennisLive id>', with what each source says of it.
    ``pages`` are (the date page's Monday, parse_calendar of it)."""
    events: dict[str, dict] = {}

    def entry(tour, tid, url) -> dict | None:
        if tour not in SECTION_DIRS or tid in (None, ""):
            return None
        key = f"{tour}:{tid}"
        ev = events.setdefault(key, {"key": key, "tl_id": tid, "tour": tour, "url": None, "weeks": set(),
                                     "in_catalog": False, "in_menu": False, "wednesday_matches": 0})
        if url and not ev["url"]:
            ev["url"] = url
        return ev

    for monday, cal in pages:
        week = monday.isoformat()
        for item in cal["catalog"]:
            ev = entry(item.get("tour"), item.get("id"), norm_url(item.get("url")))
            if ev is None:
                continue
            ev["in_catalog"] = True
            ev["weeks"].add(week)
            for src, dst in (("name", "name"), ("displayName", "display_name"), ("label", "label"), ("info", "info"),
                             ("rank", "rank"), ("country", "country"), ("countryIso2", "country_iso2"),
                             ("surface", "surface"), ("surfaceCode", "surface_code")):
                if ev.get(dst) in (None, "") and item.get(src) not in (None, ""):
                    ev[dst] = item.get(src)
        for item in cal["menu"]:
            ev = entry(item.get("tour"), item.get("id"), norm_url(item.get("url")))
            if ev is None:
                continue
            ev["in_menu"] = True
            ev["weeks"].add(week)
            ev.setdefault("menu_name", item.get("name"))
            for src, dst in (("info", "info"), ("rank", "rank"), ("country", "country"), ("countryIso2", "country_iso2"),
                             ("surface", "surface"), ("surfaceCode", "surface_code")):
                if ev.get(dst) in (None, "") and item.get(src) not in (None, ""):
                    ev[dst] = item.get(src)
        for group in cal["groups"]:
            ev = entry(group.get("tour"), group.get("tournamentId"), norm_url(group.get("url")))
            if ev is None:
                continue
            ev.setdefault("group_name", group.get("name"))
            ev["wednesday_matches"] += group["n"] if "n" in group else len(group.get("matches") or [])
            for src, dst in (("info", "info"), ("rank", "rank")):
                if ev.get(dst) in (None, "") and group.get(src) not in (None, ""):
                    ev[dst] = group.get(src)
    for ev in events.values():
        weeks = sorted(ev["weeks"])
        ev["first_week"], ev["last_week"] = (weeks[0], weeks[-1]) if weeks else (None, None)
        name = ev.get("name") or ev.get("menu_name") or re.sub(r"^(ATP|WTA)\s+", "", ev.get("group_name") or "")
        ev["name"] = name or None
        ev["kind"] = event_kind(ev["tour"], ev.get("rank"), name, ev.get("info"))
        m = EVENT_URL.match(ev["url"] or "")
        ev["slug"] = m.group("slug") if m else None
    return events


def section_target(url: str) -> tuple[str, Path] | None:
    """(receipt name, raw path) of an event's results section."""
    m = EVENT_URL.match(url or "")
    if not m:
        return None
    return (f"tournaments/{m.group('dir')}/{m.group('slug')}/results",
            P.raw_path(SOURCE, "tournaments", m.group("dir"), f"{m.group('slug')}__results.json.gz"))


def section_validator(body: bytes):
    """JSON whose status is 'ok'; an answer that speaks of a block, the token or the session is a refusal."""
    problem = P.json_validator(body)
    if problem:
        return problem
    try:
        payload = json.loads(body)
    except ValueError:
        return "response is not valid JSON"
    if isinstance(payload, dict) and payload.get("status") != "ok":
        text = json.dumps(payload, ensure_ascii=False)[:600]
        if any(w in text.lower() for w in BLOCK_WORDS):
            return f"refused: {text[:200]}"
        return f"status not ok: {text[:200]}"
    return None


def _ts(value) -> int | None:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value or None


def section_settled(payload: dict, retrieved_at: str | None) -> bool:
    """Whether a results answer is final: every match in it is over, or it was fetched SETTLE_DAYS after the last
    listed start."""
    starts, still_open = [], 0
    for group in ((payload or {}).get("data") or {}).get("groups") or []:
        for m in group.get("matches") or []:
            if m.get("state") not in FINAL_STATES:
                still_open += 1
            ts = _ts(m.get("startTimestamp"))
            if ts:
                starts.append(ts)
    if not still_open:
        return True
    if not starts or not retrieved_at:
        return False
    fetched = dt.datetime.fromisoformat(retrieved_at).timestamp()
    return fetched >= max(starts) + SETTLE_DAYS * 86400


def set_text(sets) -> str | None:
    return TL._sets(sets)


def score_text(sets1, sets2) -> str | None:
    """'7-6(6) 1-6 6-3' from the two players' set lists (a tiebreak set is {'score': 7, 'detail': 8}; the loser's
    tiebreak points are written)."""
    if not sets1 or not sets2:
        return None
    out = []
    for a, b in zip(sets1, sets2):
        ga = a.get("score") if isinstance(a, dict) else a
        gb = b.get("score") if isinstance(b, dict) else b
        da = a.get("detail") if isinstance(a, dict) else None
        db = b.get("detail") if isinstance(b, dict) else None
        text = f"{ga}-{gb}"
        details = [d for d in (da, db) if d is not None]
        if details:
            text += f"({min(details)})"
        out.append(text)
    return " ".join(out)


def stage_key(stage_code, round_id) -> str | None:
    """The stage a match's round and draw are read from: its stage code, except that a 'match' group of round 0 opens
    the qualifying (the 128-player qualifying draws of 19 men's Futures of 2018 start with one, a day or two before
    'qualifying_round_1'): it is read as qualifying_round_0. A 'match' group of a later round (a play-off) and the
    Finals' 'round_robin' and 'bronze' stay in the main draw."""
    if stage_code == "match" and str(round_id) == "0":
        return "qualifying_round_0"
    return stage_code


def round_codes(stage_codes) -> dict[str, str]:
    """TennisLive's stage codes of one event in the map's round form. Main draw: final F, semifinal SF, quarterfinal
    QF, and round_N named by the bracket it opens (round_1 of rounds 1-2 before the quarter-finals is R32).
    Qualifying: the qualifying_round_N in order are Q1, Q2 ..., and the last qualifying round ('qualifying') follows
    them."""
    codes = {str(c) for c in stage_codes if c}
    rounds = sorted(int(c.split("_")[1]) for c in codes if re.fullmatch(r"round_\d+", c))
    out = {"final": "F", "semifinal": "SF", "quarterfinal": "QF"}
    if rounds:
        total = max(rounds) + 3
        for n in rounds:
            out[f"round_{n}"] = f"R{2 ** (total - n + 1)}"
    qual = sorted(int(c.rsplit("_", 1)[1]) for c in codes if re.fullmatch(r"qualifying_round_\d+", c))
    for i, n in enumerate(qual, 1):
        out[f"qualifying_round_{n}"] = f"Q{i}"
    if "qualifying" in codes:
        out["qualifying"] = f"Q{len(qual) + 1}"
    return {c: out[c] for c in codes if c in out}


def played(m: dict) -> bool:
    """A match that was played to a result: over, not a walkover, with a winner or set scores."""
    state, end = m.get("state"), str(m.get("endReason") or "").lower()
    if state not in ("finished", "retired", "awarded") or end == "walkover":
        return False
    players = m.get("players") or []
    return m.get("winnerId") is not None or any(p.get("sets") for p in players)


def match_row(m: dict, group: dict, ev: dict, rounds: dict, start_time, source: dict, listed_from: str) -> dict:
    players = m.get("players") or []
    p = [players[i] if len(players) > i else {} for i in (0, 1)]
    winner = m.get("winnerId")
    winner_side = next((i + 1 for i, x in enumerate(p) if winner is not None and x.get("id") == winner), None)
    stage_code = m.get("stageCode") or group.get("stageCode")
    key = stage_key(stage_code, group.get("roundId"))
    row = {"event_key": ev["key"], "event_url": ev.get("url"), "event_id": group.get("tournamentId") or ev.get("tl_id"),
           "event_name": group.get("name"), "event_kind": ev.get("kind"), "event_rank": ev.get("rank"),
           "tour": group.get("tour") or ev.get("tour"), "listed_from": listed_from, "group_id": group.get("id"),
           "stage": group.get("stage"), "stage_code": stage_code, "round_id": group.get("roundId"),
           "round": rounds.get(str(key)), "draw": "qualifying" if str(key or "").startswith("qualif") else "main",
           "discipline": "doubles" if m.get("doubles") else "singles", "mixed": m.get("mixed"), "junior": m.get("junior"),
           "match_id": m.get("id"), "identity": m.get("identity"), "url": m.get("url") or None, "state": m.get("state"),
           "set_label": m.get("setLabel"), "end_reason": m.get("endReason"), "played": played(m), "winner_id": winner,
           "winner_side": winner_side, "set_winners": ";".join(str(x) for x in m.get("setWinners") or []),
           "score": score_text(p[0].get("sets"), p[1].get("sets")),
           "start_timestamp": m.get("startTimestamp"), "start_utc": TL._utc(m.get("startTimestamp")),
           "group_start_time": start_time, "observed_started_at": m.get("observedStartedAt"),
           "observed_current_set_started_at": m.get("observedCurrentSetStartedAt"),
           "observed_finished_at": m.get("observedFinishedAt"), "finished_at": m.get("finishedAt"),
           "interrupted_at": m.get("interruptedAt"), "recently_finished_until": m.get("recentlyFinishedUntil"),
           "recently_interrupted_until": m.get("recentlyInterruptedUntil"), "duration": m.get("duration"),
           "draw_position": m.get("drawPosition"),
           "storage": m.get("storage"), "favorite_key": m.get("favoriteKey"), "current_set": m.get("currentSet"),
           "points": m.get("points"), "server": m.get("server"), "break_point": m.get("breakPoint"),
           "point_markers": m.get("pointMarkers") or None, **source}
    for n, x in enumerate(p, 1):
        members = [mm.get("name") for mm in x.get("members") or [] if mm.get("name")]
        row.update({f"player{n}_id": x.get("id"), f"player{n}_name": x.get("name"), f"player{n}_url": x.get("url"),
                    f"player{n}_seed": x.get("seed"), f"player{n}_ranking": x.get("ranking"),
                    f"player{n}_flag": x.get("flag"), f"player{n}_sets_won": x.get("setsWon"),
                    f"player{n}_sets": set_text(x.get("sets")), f"player{n}_members": " / ".join(members) or None})
    return row


def section_rows(payload: dict, ev: dict, source: dict) -> list[dict]:
    """Every match of a results answer, in its order, with the event's round names."""
    groups = ((payload or {}).get("data") or {}).get("groups") or []
    rounds = round_codes(stage_key(m.get("stageCode") or g.get("stageCode"), g.get("roundId"))
                         for g in groups for m in g.get("matches") or [])
    rows = []
    for group in groups:
        times = group.get("startTimes") or []
        for i, m in enumerate(group.get("matches") or []):
            rows.append(match_row(m, group, ev, rounds, times[i] if i < len(times) else None, source, "results section"))
    return rows


def day_rows(groups_by_day: list[tuple[str, dict, dict]], ev: dict) -> list[dict]:
    """An event's matches from the date pages that hold it (an event without a page): each match once (a match
    shown on two days, as one suspended overnight, keeps its last showing)."""
    rounds = round_codes(stage_key(m.get("stageCode") or g.get("stageCode"), g.get("roundId"))
                         for _, g, _ in groups_by_day for m in g.get("matches") or [])
    seen: dict = {}
    for day, group, source in sorted(groups_by_day, key=lambda x: x[0]):
        times = group.get("startTimes") or []
        for i, m in enumerate(group.get("matches") or []):
            key = m.get("identity") or m.get("id")
            seen[key] = match_row(m, group, ev, rounds, times[i] if i < len(times) else None, source, f"date page {day}")
    return list(seen.values())


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
class Session:
    """The request token of a page read in this run's session; the JSON endpoint refuses a token from another."""

    def __init__(self, client, receipts):
        self.client, self.receipts = client, receipts
        self.token: str | None = None
        self.opened = 0

    def note(self, html: str) -> None:
        token = token_of(TL.runtime_object(html))
        if token:
            self.token = token

    def ensure(self) -> str:
        if not self.token:
            self.renew()
        return self.token

    def renew(self) -> None:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = P.raw_path(SOURCE, "session", f"{stamp}.html.gz")
        r = P.fetch(self.client, SITE + "/", dest, self.receipts, name=f"session/{stamp}", refresh=True,
                    validator=P.html_validator, compress=True)
        if r.get("status") != 200 or r.get("error") or not dest.exists():
            raise P.Blocked(f"the home page did not open a session: {r.get('error') or r.get('status')}")
        self.token = None
        self.note(P.read_bytes(dest).decode("utf-8", errors="replace"))
        if not self.token:
            raise P.Blocked("the home page carried no request token")
        self.opened += 1


class Stalls:
    """Requests in a row that got no answer at all (the client's retries timed out) count as a block. TennisLive
    dropped this address silently for about 35 minutes on 9 Oct 2026, after some 12,200 requests in seven hours: no
    HTTP 403 or 429, only connections that never answered, which the client records as errors and passes."""

    def __init__(self, limit: int = 2):
        self.limit, self.row = limit, 0

    def note(self, r: dict) -> dict:
        if r.get("status") is None and "timed out" in str(r.get("error") or "").lower():
            self.row += 1
            if self.row >= self.limit:
                raise P.Blocked(f"no answer to {self.row} requests in a row (the last: {str(r.get('error'))[:120]})")
        elif r.get("status") is not None:
            self.row = 0
        return r


def fetch_day(client, receipts, session: Session, day: dt.date, refresh: bool = False) -> dict:
    """A date page; refresh: asked again even when held (the bet-day linker reads today's and tomorrow's: 22 Oct
    2026)."""
    name, dest = f"calendar/{day.isoformat()}", P.raw_path(SOURCE, "calendar", f"{day.isoformat()}.html.gz")
    r = P.fetch(client, f"{SITE}/{day.isoformat()}/", dest, receipts, name=name, refresh=refresh,
                validator=P.html_validator, compress=True, extra={"date": day.isoformat()})
    if not r.get("skipped") and r.get("status") == 200 and dest.exists():
        session.note(P.read_bytes(dest).decode("utf-8", errors="replace"))
    return r


def fetch_section(client, receipts, session: Session, ev: dict, force: bool = False) -> dict:
    """An event's results section; fetched again when the answer on disk was not final, or always with force (the
    bet-day linker, 22 Oct 2026: an event under way lists only its finished matches, so an answer of the morning reads
    as final while the day's later results are missing)."""
    name, dest = section_target(ev["url"])
    previous = receipts.get(name)
    refresh = force
    if previous and previous.get("status") == 200 and not previous.get("error") and dest.exists() and not force:
        refresh = not section_settled(P.read_json(dest), previous.get("retrieved_at"))
        if not refresh:
            return {**previous, "skipped": True}
    api = f"{SITE}/api/tournament-section?tour={ev['tour']}&slug={quote(ev['slug'])}&section=results"
    for attempt in (1, 2):
        headers = {**TL.API_HEADERS, "X-TennisLive-Token": session.ensure(), "Referer": SITE + ev["url"]}
        try:
            r = P.fetch(client, api, dest, receipts, name=name, refresh=refresh, validator=section_validator,
                        compress=True, headers=headers,
                        extra={"event_url": ev["url"], "event_id": ev["tl_id"], "tour": ev["tour"]})
        except P.Blocked:
            if attempt == 2:
                raise
            session.token = None        # a stale token answers 403: one new session, then a refusal stops the run
            continue
        if str(r.get("error") or "").startswith("refused"):
            if attempt == 2:
                raise P.Blocked(f"results section refused twice for {ev['url']}: {r['error']}")
            session.token = None
            continue
        return r
    return {}


# --------------------------------------------------------------------------------------
# reading what is on disk
# --------------------------------------------------------------------------------------
def read_day(receipts, day: dt.date) -> dict | None:
    r = receipts.get(f"calendar/{day.isoformat()}") or {}
    dest = P.raw_path(SOURCE, "calendar", f"{day.isoformat()}.html.gz")
    if r.get("status") != 200 or r.get("error") or not dest.exists():
        return None
    cal = parse_calendar(P.read_bytes(dest).decode("utf-8", errors="replace"))
    cal["receipt"] = r
    return cal


def read_section(receipts, ev: dict) -> tuple[dict | None, dict]:
    target = section_target(ev.get("url"))
    if target is None:
        return None, {}
    name, dest = target
    r = receipts.get(name) or {}
    if r.get("status") != 200 or r.get("error") or not dest.exists():
        return None, r
    return P.read_json(dest), r


def light(cal: dict) -> dict:
    """A parsed date page without its matches (counted instead), to hold hundreds in memory."""
    keep = ("tour", "tournamentId", "url", "name", "info", "rank")
    return {**cal, "groups": [{**{k: g.get(k) for k in keep}, "n": len(g.get("matches") or [])} for g in cal["groups"]]}


def week_page(receipts, monday: dt.date, today: dt.date | None = None) -> dict | None:
    """A week's calendar page: its Wednesday's; for the current week (today inside it), before that page is on disk, the
    latest page of the week dated before today (since 13 Oct 2026: --through-yesterday reads the week in progress)."""
    cal = read_day(receipts, monday + dt.timedelta(days=2))
    if cal is not None or today is None or not (monday <= today < monday + dt.timedelta(days=7)):
        return cal
    for k in range((today - monday).days - 1, -1, -1):
        cal = read_day(receipts, monday + dt.timedelta(days=k))
        if cal is not None:
            return cal
    return None


def calendar_events(receipts, mondays: list[dt.date], today: dt.date | None = None) -> tuple[dict[str, dict], dict]:
    """The events of the Wednesday pages on disk for these weeks (the week in progress: week_page), and what was read."""
    pages, missing = [], []
    for monday in mondays:
        cal = week_page(receipts, monday, today)
        if cal is None:
            missing.append(monday.isoformat())
            continue
        pages.append((monday, light(cal)))
    stats = {"weeks": len(mondays), "pages_read": len(pages), "weeks_without_page": missing,
             "dates_not_as_asked": [str(m) for m, c in pages if c["date"] != (m + dt.timedelta(days=2)).isoformat()]}
    return collect_events(pages), stats


def targets_of(events: dict[str, dict], kinds) -> list[dict]:
    """Events to list: the wanted kinds that have a page, newest first."""
    out = [ev for ev in events.values() if ev["kind"] in kinds and ev.get("url")]
    return sorted(out, key=lambda ev: (ev["last_week"] or "", ev["first_week"] or "", ev["key"]), reverse=True)


def pageless_of(events: dict[str, dict], kinds) -> list[dict]:
    return [ev for ev in events.values() if ev["kind"] in kinds and not ev.get("url")]


def pageless_days(events: list[dict]) -> list[dt.date]:
    """Every date page that can hold a match of these events: the Saturday before to the Sunday of each week."""
    days = set()
    for ev in events:
        for week in ev["weeks"]:
            days.update(week_days(dt.date.fromisoformat(week)))
    return sorted(days)


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def provenance(r: dict, path: Path) -> dict:
    return {"source_file": P.rel(path), "source_sha256": r.get("sha256"), "retrieved_at": r.get("retrieved_at")}


def listed_rows(receipts, events: dict[str, dict], kinds, counts: dict):
    """Every match of every results answer on disk, then of the date pages of the events without a page. Fills
    ``counts`` (event key -> per-event counts) on the way."""
    for ev in sorted(events.values(), key=lambda e: (e["first_week"] or "", e["key"])):
        if ev["kind"] not in kinds or not ev.get("url"):
            continue
        payload, r = read_section(receipts, ev)
        c = counts.setdefault(ev["key"], {})
        c.update(section_status=r.get("error") or r.get("status") or "not fetched",
                 section_retrieved_at=r.get("retrieved_at"), section_sha256=r.get("sha256"),
                 section_file=r.get("dest"))
        if payload is None:
            continue
        c["section_settled"] = section_settled(payload, r.get("retrieved_at"))
        totals = (payload.get("data") or {}).get("totalCounts") or {}
        c.update(total_singles=totals.get("singles"), total_doubles=totals.get("doubles"))
        rows = section_rows(payload, ev, provenance(r, section_target(ev["url"])[1]))
        tally_event(c, rows)
        yield from rows
    pageless = {ev["key"]: ev for ev in pageless_of(events, kinds)}
    wanted: dict[dt.date, set] = defaultdict(set)
    for key, ev in pageless.items():
        for day in pageless_days([ev]):
            wanted[day].add(key)
    groups: dict[str, list] = defaultdict(list)
    pages: Counter = Counter()
    for day in sorted(wanted):                    # one date page at a time: only these events' groups are kept
        cal = read_day(receipts, day)
        if cal is None:
            continue
        source = provenance(cal["receipt"], P.raw_path(SOURCE, "calendar", f"{day.isoformat()}.html.gz"))
        for g in cal["groups"]:
            key = f"{g.get('tour')}:{g.get('tournamentId')}"
            if key in wanted[day]:
                groups[key].append((day.isoformat(), g, source))
        pages.update(wanted[day])
    for key, ev in sorted(pageless.items()):
        c = counts.setdefault(key, {})
        c.update(section_status="no tournament page", day_pages=pages.get(key, 0))
        rows = day_rows(groups.get(key, []), ev)
        tally_event(c, rows)
        yield from rows


def tally_event(c: dict, rows: list[dict]) -> None:
    singles = [r for r in rows if r["discipline"] == "singles"]
    c["singles_main"] = sum(r["draw"] == "main" for r in singles)
    c["singles_main_played"] = sum(r["draw"] == "main" and r["played"] for r in singles)
    c["singles_qualifying"] = sum(r["draw"] == "qualifying" for r in singles)
    c["singles_qualifying_played"] = sum(r["draw"] == "qualifying" and r["played"] for r in singles)
    c["doubles"] = len(rows) - len(singles)
    starts = sorted(r["start_utc"] for r in rows if r["start_utc"])
    c["first_start_utc"], c["last_start_utc"] = (starts[0], starts[-1]) if starts else (None, None)


def stage(receipts, events: dict[str, dict], kinds) -> tuple[dict, dict]:
    """events.parquet and listed.parquet from what is on disk (the pages are tennislive.stage's)."""
    counts: dict[str, dict] = {}
    now = P.utc_now_iso()
    dest = P.dump_path(SOURCE, "listed.parquet")
    rows = ([P.s(r.get(c)) for c in LISTED_COLUMNS] for r in listed_rows(receipts, events, kinds, counts))
    listed = P.stage_table(SOURCE, dest, LISTED_COLUMNS, rows, source_file=P.rel(P.raw_path(SOURCE, "tournaments")),
                           retrieved_at=now, extra={"mode": "events"})
    P.log(f"[{SOURCE}] staged {listed['dest']}: {listed['rows']:,} rows")
    event_rows = []
    for ev in sorted(events.values(), key=lambda e: (e["first_week"] or "", e["key"])):
        row = {**ev, **counts.get(ev["key"], {})}
        row["weeks"] = ";".join(sorted(ev["weeks"]))
        event_rows.append(row)
    dest = P.dump_path(SOURCE, "events.parquet")
    staged = P.stage_table(SOURCE, dest, EVENT_COLUMNS, [[P.s(r.get(c)) for c in EVENT_COLUMNS] for r in event_rows],
                           source_file=P.rel(P.raw_path(SOURCE, "calendar")), retrieved_at=now, extra={"mode": "events"})
    P.log(f"[{SOURCE}] staged {staged['dest']}: {staged['rows']:,} rows")
    out = {"listed": {k: listed[k] for k in ("rows", "dest", "bytes")},
           "events": {k: staged[k] for k in ("rows", "dest", "bytes")}}
    return out, counts


# --------------------------------------------------------------------------------------
# samples
# --------------------------------------------------------------------------------------
def sample_pool(listed: pd.DataFrame, events: pd.DataFrame, spec: dict) -> pd.DataFrame:
    """Played singles matches with a page, of ITF events, in the sample's draw and dates."""
    itf = set(events.loc[events["kind"].eq("itf"), "key"])
    f = listed[listed["event_key"].isin(itf) & listed["discipline"].eq("singles") & listed["played"].eq("TRUE")
               & listed["url"].notna() & listed["draw"].eq(spec["draw"])].copy()
    first = events.set_index("key")["first_week"]
    f["day"] = f["start_utc"].str[:10].fillna(f["event_key"].map(first))
    f["year"] = pd.to_numeric(f["day"].str[:4], errors="coerce")
    f = f[f["day"].notna()]
    if spec["since"]:
        f = f[f["day"] >= spec["since"]]
    if spec["years"]:
        f = f[f["year"].isin(spec["years"])]
    return f


def draw_sample(pool: pd.DataFrame, name: str, seed: int, per_tour: int = SAMPLE_PER_TOUR,
                years: list[int] | None = None) -> pd.DataFrame:
    """One match per event, ``per_tour`` a tour; with ``years``, the tour's matches spread evenly over them (the
    first years take the remainder). Events are drawn in a seeded order; a stratum with fewer events than its
    quota takes a second match from its events, and so on."""
    rng = random.Random(f"{seed}:{name}")
    picks = []
    for tour in ("atp", "wta"):
        t = pool[pool["tour"].eq(tour)]
        strata = [(None, t)] if not years else [(y, t[t["year"].eq(y)]) for y in years]
        quotas = [per_tour // len(strata) + (1 if i < per_tour % len(strata) else 0) for i in range(len(strata))]
        for (year, s), quota in zip(strata, quotas):
            by_event = {k: sorted(g["url"].tolist()) for k, g in s.groupby("event_key")}
            order = sorted(by_event)
            rng.shuffle(order)
            for urls in by_event.values():
                rng.shuffle(urls)
            chosen, depth = [], 0
            while len(chosen) < quota and any(len(by_event[k]) > depth for k in order):
                for k in order:
                    if len(chosen) >= quota:
                        break
                    if len(by_event[k]) > depth:
                        chosen.append(by_event[k][depth])
                depth += 1
            picks += [{"sample": name, "tour": tour, "stratum": year, "url": u} for u in chosen]
    return pd.DataFrame(picks, columns=["sample", "tour", "stratum", "url"])


def freeze_samples(seed: int, per_tour: int) -> pd.DataFrame:
    """The frozen samples, drawn from the staged listing the first time."""
    if SAMPLES_CSV.exists():
        return pd.read_csv(SAMPLES_CSV, dtype=str, keep_default_na=False, na_values=[""])
    listed = pd.read_parquet(P.dump_path(SOURCE, "listed.parquet"),
                             columns=["event_key", "tour", "discipline", "played", "url", "draw", "start_utc",
                                      "stage_code", "round", "score", "player1_name", "player2_name", "event_name"])
    events = pd.read_parquet(P.dump_path(SOURCE, "events.parquet"), columns=["key", "kind", "first_week"])
    frames = []
    for name, spec in SAMPLES.items():
        pool = sample_pool(listed, events, spec)
        picked = draw_sample(pool, name, seed, per_tour, spec["years"])
        frames.append(picked.merge(pool.drop(columns=["tour"]).drop_duplicates("url"), on="url", how="left"))
    out = pd.concat(frames, ignore_index=True)
    out.insert(1, "seed", seed)
    STUDY.mkdir(parents=True, exist_ok=True)
    out.to_csv(SAMPLES_CSV, index=False)
    P.log(f"[{SOURCE}] samples drawn and frozen in {P.rel(SAMPLES_CSV)}: "
          + ", ".join(f"{k} {v}" for k, v in out["sample"].value_counts().sort_index().items()))
    return out


def fetch_samples(client, receipts, samples: pd.DataFrame, stalls: Stalls | None = None) -> Counter:
    outcomes = Counter()
    stalls = stalls or Stalls()
    for n, row in enumerate(samples.itertuples(index=False), 1):
        r = stalls.note(TL.fetch_match(client, receipts, row.url, refresh=False, extra={"sample": row.sample}))
        outcomes[f"{row.sample}:{r.get('error') or r.get('status')}" + (":cached" if r.get("skipped") else "")] += 1
        if n % 50 == 0 or n == len(samples):
            P.log(f"[{SOURCE}] sample pages {n}/{len(samples)}; requests={client.requests}; "
                  + ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items())))
    return outcomes


def page_record(html: str, score: str | None) -> dict:
    """What a match page holds against the listed score: points, completeness (verify_scrape's rules), the share of
    the score's games listed with their points, and the statistics block."""
    from src.eda.point_shot_sources.verify_scrape import COMPLETE, completeness, official_sets, short_kind

    parsed = TL.parse_match_page(html)
    meta = parsed["meta"]
    per_set, last_after = {}, {}
    for g in parsed["games"]:
        if g["game"] > 0:
            per_set[g["set"]] = max(per_set.get(g["set"], 0), g["game"])
            m = re.fullmatch(r"(\d+)-(\d+)", str(g["after"] or "").strip())
            last_after[g["set"]] = int(m.group(1)) + int(m.group(2)) if m else None
    sets = list(range(1, max(per_set) + 1)) if per_set else []
    record = [per_set.get(s_, 0) for s_ in sets]
    official = official_sets(score) if score else []
    if not official and meta.get("score"):
        official = official_sets(meta["score"])
    if not meta.get("points_listed"):
        verdict = "no points"
    else:
        kind = completeness(official, record)
        if kind is None:
            verdict = "no score to compare"
        elif kind in COMPLETE:
            verdict = "complete"
        elif kind == "short":
            verdict = ("only set-closing games missing"
                       if short_kind(official, record, [last_after.get(s_) for s_ in sets]) == "set closers only"
                       else "other shortfall")
        else:
            verdict = "other shortfall (more games than the score)"
    total = sum(official)
    with_points = int(meta.get("games_listed") or 0) - int(meta.get("games_without_points") or 0)
    return {"page_score": meta.get("score"), "score_games": " ".join(str(x) for x in official),
            "record_games": " ".join(str(x) for x in record), "points_listed": meta.get("points_listed"),
            "games_listed": meta.get("games_listed"), "games_without_points": meta.get("games_without_points"),
            "pbp_available": bool(meta.get("points_listed")), "pbp_unavailable_notice": meta.get("pbp_unavailable_notice"),
            "point_game_share": round(min(with_points, total) / total, 3) if total else None, "verdict": verdict,
            "stats_available": bool(parsed["statistics"]), "stats_rows": len(parsed["statistics"]),
            "round_shown": meta.get("round_shown"), "date_shown": meta.get("date_shown")}


def sample_records(receipts, samples: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in samples.to_dict(orient="records"):
        r = receipts.get(f"matches{row['url']}") or {}
        dest = TL.match_dest(row["url"])
        out = {**row, "page_status": r.get("error") or r.get("status") or "not fetched",
               "page_retrieved_at": r.get("retrieved_at")}
        if r.get("status") == 200 and not r.get("error") and dest and dest.exists():
            out.update(page_record(P.read_bytes(dest).decode("utf-8", errors="replace"), row.get("score")))
        rows.append(out)
    return pd.DataFrame(rows)


def sample_summary(records: pd.DataFrame) -> dict:
    out = {}
    if records.empty or "verdict" not in records:
        return out
    for (sample, tour), g in records.groupby(["sample", "tour"]):
        fetched = g[g["page_status"].astype(str).eq("200")]
        v = fetched["verdict"].value_counts()
        share = pd.to_numeric(fetched["point_game_share"], errors="coerce")
        cell = {"sampled": int(len(g)), "pages": int(len(fetched)),
                "with_points": int(fetched["pbp_available"].eq(True).sum()),
                "complete": int(v.get("complete", 0)), "only_set_closing_missing": int(v.get("only set-closing games missing", 0)),
                "other_shortfall": int(sum(n for k, n in v.items() if str(k).startswith("other shortfall"))),
                "no_points": int(v.get("no points", 0)), "with_statistics": int(fetched["stats_available"].eq(True).sum()),
                "median_games_with_points": float(share.median()) if share.notna().any() else None}
        if sample.startswith("itf_qualifying"):
            last = fetched["stage_code"].eq("qualifying")
            cell["final_qualifying_round"] = {"pages": int(last.sum()),
                                              "with_points": int((last & fetched["pbp_available"].eq(True)).sum())}
            cell["earlier_rounds"] = {"pages": int((~last).sum()),
                                      "with_points": int((~last & fetched["pbp_available"].eq(True)).sum())}
            years = {}
            for y, gy in fetched.groupby(fetched["stratum"].astype(str)):
                years[y] = {"pages": int(len(gy)), "with_points": int(gy["pbp_available"].eq(True).sum())}
            cell["by_year"] = years
        out[f"{sample}|{tour}"] = cell
    return out


# --------------------------------------------------------------------------------------
# evidence: the map's editions against the events
# --------------------------------------------------------------------------------------
def map_editions() -> pd.DataFrame:
    """The map's matches of the editions P4 lists (ITF and Challenger / WTA 125 of 2018-2026, tour level and Slams
    of 2018-2026), as the result files and point sources made them: matches the TennisLive listing itself added
    are left out."""
    if not MAP_MATCHES.exists():
        return pd.DataFrame()
    m = pd.read_parquet(MAP_MATCHES, columns=["uid", "tour", "level", "draw", "year", "d", "name1", "name2", "tname",
                                              "creator"])
    m = m[~m["creator"].fillna("").str.startswith("tennislive")]
    group = m["level"].map({"ITF": "itf", "ITFQ": "itf", "CH": "challenger", "CHQ": "challenger", "GS": "tour",
                            "GSQ": "tour", "FIN": "tour", "T1000": "tour", "T500": "tour", "T250": "tour", "TQ": "tour"})
    m = m.assign(group=group)[group.notna() & m["year"].between(2018, 2026)].copy()
    week = pd.to_datetime(m["d"]).dt.isocalendar()
    m["edition"] = (m["tour"] + "|" + m["tname"].fillna("") + "|" + m["year"].astype(str) + "|w"
                    + week["week"].astype(str).str.zfill(2))
    return m


def link_editions(editions: pd.DataFrame, listed: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Each map edition and the TennisLive event holding most of its matches: same tour, the same pair of surnames
    (the map's own key), played 10 days before to 21 days after the map's date."""
    from src.eda.data_map.measure import pair_key, surname_key

    if editions.empty:
        return pd.DataFrame()
    e = editions.copy()
    e["pair"] = pair_key(e["name1"].map(surname_key), e["name2"].map(surname_key))
    s = listed[listed["discipline"].eq("singles")].copy()
    s["tour"] = s["tour"].map({"atp": "M", "wta": "W"})
    s["pair"] = pair_key(s["player1_name"].map(surname_key), s["player2_name"].map(surname_key))
    first = events.set_index("key")["first_week"]
    s["day"] = pd.to_datetime(s["start_utc"].str[:10].fillna(s["event_key"].map(first)), errors="coerce")
    cand = e[["uid", "edition", "tour", "pair", "d"]].dropna(subset=["pair"]).merge(
        s[["tour", "pair", "day", "event_key"]].dropna(subset=["pair"]), on=["tour", "pair"])
    delta = (cand["day"] - pd.to_datetime(cand["d"])).dt.days
    cand = cand[delta.between(-10, 21)]
    hits = cand.drop_duplicates(["uid", "event_key"]).groupby(["edition", "event_key"]).size().rename("matches_linked")
    hits = hits.reset_index().sort_values(["edition", "matches_linked"], ascending=[True, False])
    best = hits.drop_duplicates("edition").set_index("edition")
    second = hits[hits.duplicated("edition")].drop_duplicates("edition").set_index("edition")["matches_linked"]
    out = e.groupby("edition").agg(tour=("tour", "first"), tname=("tname", "first"), year=("year", "first"),
                                   group=("group", "first"), levels=("level", lambda x: ";".join(sorted(set(x)))),
                                   d_min=("d", "min"), d_max=("d", "max"), matches=("uid", "size"),
                                   creators=("creator", lambda x: ";".join(sorted(set(x))))).reset_index()
    out["event_key"] = out["edition"].map(best["event_key"])
    out["matches_linked"] = out["edition"].map(best["matches_linked"]).fillna(0).astype(int)
    out["next_best_linked"] = out["edition"].map(second).fillna(0).astype(int)
    ev = events.set_index("key")
    for c in ("url", "name", "kind", "section_status", "first_week"):
        out[f"tl_{c}"] = out["event_key"].map(ev[c]) if c in ev else None
    out["linked"] = out["matches_linked"] > 0
    return out


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def dates_inside_weeks(ev: pd.DataFrame) -> dict:
    """The weekly-venue check of the plan (a week's Monastir is not the week before's): each listed event's matches
    are dated from the Saturday before its first catalog week to the Monday after its last."""
    if "first_start_utc" not in ev:
        return {}
    e = ev.dropna(subset=["first_start_utc", "last_start_utc", "first_week", "last_week"])
    first = pd.to_datetime(e["first_week"]) - pd.Timedelta(days=2)
    last = pd.to_datetime(e["last_week"]) + pd.Timedelta(days=8)
    inside = (pd.to_datetime(e["first_start_utc"].str[:10]) >= first) & (pd.to_datetime(e["last_start_utc"].str[:10]) < last)
    outside = e[~inside]
    return {"events_with_dated_matches": int(len(e)), "inside": int(inside.sum()),
            "outside_examples": outside[["key", "name", "first_week", "last_week", "first_start_utc",
                                         "last_start_utc"]].head(25).astype(str).to_dict(orient="records")}


def summarize(events: dict[str, dict], counts: dict, kinds, editions: pd.DataFrame, records: pd.DataFrame,
              cal_stats: dict) -> dict:
    """The run's counts: events by kind and page, target events listed by year, tour and kind, the map's editions
    linked, and the samples."""
    ev = pd.DataFrame([{**e, **counts.get(e["key"], {})} for e in events.values()])
    out = {"calendar": cal_stats, "events": {}, "editions": {}, "samples": sample_summary(records)}
    if ev.empty:
        return out
    for c in ("section_status", "singles_main_played", "singles_qualifying_played"):
        if c not in ev:
            ev[c] = None
    ev["year"] = ev["first_week"].str[:4]
    ev["has_page"] = ev["url"].notna()
    out["events"]["by_kind_tour_page"] = {f"{k}|{t}|{'page' if p else 'no page'}": int(n) for (k, t, p), n in
                                          ev.groupby(["kind", "tour", "has_page"]).size().items()}
    out["events"]["examples_by_kind_tour_rank"] = {f"{k}|{t}|{r}": g["name"].dropna().head(8).tolist()
                                                   for (k, t, r), g in ev.groupby(["kind", "tour", "rank"], dropna=False)}
    tgt = ev[ev["kind"].isin(kinds)]
    out["events"]["targets_by_year_tour_kind"] = {
        f"{y}|{t}|{k}": {"events": int(len(g)), "with_page": int(g["has_page"].sum()),
                         "listed": int(g["section_status"].astype(str).isin(["200", "no tournament page"]).sum()),
                         "singles_main_played": int(pd.to_numeric(g["singles_main_played"], errors="coerce").sum()),
                         "singles_qualifying_played": int(pd.to_numeric(g["singles_qualifying_played"],
                                                                        errors="coerce").sum())}
        for (y, t, k), g in tgt.groupby(["year", "tour", "kind"])}
    out["events"]["section_status"] = {str(k): int(v) for k, v in
                                       tgt["section_status"].astype(str).value_counts().items()}
    out["events"]["dates_inside_weeks"] = dates_inside_weeks(tgt)
    if not editions.empty:
        out["editions"]["by_group_tour_year"] = {
            f"{g_}|{t}|{y}": {"editions": int(len(g)), "linked": int(g["linked"].sum()),
                              "map_matches": int(g["matches"].sum()), "matches_linked": int(g["matches_linked"].sum())}
            for (g_, t, y), g in editions.groupby(["group", "tour", "year"])}
        out["editions"]["all"] = {"editions": int(len(editions)), "linked": int(editions["linked"].sum()),
                                  "map_matches": int(editions["matches"].sum()),
                                  "matches_linked": int(editions["matches_linked"].sum())}
    return out


def make_client(args) -> P.Client:
    return P.Client(TL.IMPERSONATE, min_interval=args.min_interval, jitter=args.jitter, max_requests=args.max_requests)


def week_range(weeks: str | None, today: dt.date, current: bool = False) -> tuple[dt.date, dt.date]:
    """The Mondays of the first and last weeks read: --weeks FROM:TO, else 2018-W01 to the last complete week (to the
    week in progress with current=True: --through-yesterday)."""
    last_full = last_complete_week(today) + dt.timedelta(days=7 if current else 0)
    if not weeks:
        return parse_week(FIRST_WEEK), last_full
    a, _, b = weeks.partition(":")
    first, last = parse_week(a), parse_week(b) if b else last_full
    if last > last_full:
        raise SystemExit(f"--weeks ends after the last {'week read' if current else 'complete week'} (the week of "
                         f"{last_full})")
    return first, last


def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    today = TODAY["day"] or dt.date.today()
    current = bool(getattr(args, "through_yesterday", False))
    first, last = week_range(args.weeks, today, current)
    kinds = tuple(k.strip() for k in args.kinds.split(",") if k.strip())
    only = {norm_url(u.strip()) for u in args.only.split(",")} if args.only else None
    mondays = [d - dt.timedelta(days=2) for d in wednesdays(first, last)]
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "mode": "events", "started_at": P.utc_now_iso(), "args": vars(args),
               "weeks": f"{first} .. {last}"}
    client = None if args.stage_only else make_client(args)
    session = Session(client, receipts)
    stalls = Stalls()
    outcomes = Counter()
    full_range = not (args.weeks or args.limit or args.only or args.kinds != ",".join(KINDS))
    events, cal_stats = {}, {}
    try:
        if client is not None and not args.skip_calendar:
            for n, monday in enumerate(mondays, 1):
                # a complete week: its Wednesday page; the week in progress: each day's page up to yesterday (a page is
                # fetched once, so never on its own day)
                days = ([monday + dt.timedelta(days=k) for k in range((today - monday).days)]
                        if monday <= today < monday + dt.timedelta(days=7) else [monday + dt.timedelta(days=2)])
                for day in days:
                    r = stalls.note(fetch_day(client, receipts, session, day))
                    outcomes[f"calendar:{r.get('error') or r.get('status')}" + (":cached" if r.get("skipped") else "")] += 1
                if n % 50 == 0 or n == len(mondays):
                    P.log(f"[{SOURCE}] calendar {n}/{len(mondays)}; requests={client.requests}; "
                          + ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items()) if k.startswith("calendar")))
        events, cal_stats = calendar_events(receipts, mondays, today)
        targets = [ev for ev in targets_of(events, kinds) if only is None or ev["url"] in only]
        if args.limit:
            targets = targets[:args.limit]
        P.log(f"[{SOURCE}] {len(events):,} events in {cal_stats['pages_read']} weeks; {len(targets):,} to list")
        if client is not None and not args.skip_results:
            for n, ev in enumerate(targets, 1):
                r = stalls.note(fetch_section(client, receipts, session, ev))
                outcomes[f"results:{r.get('error') or r.get('status')}" + (":cached" if r.get("skipped") else "")] += 1
                if n % 100 == 0 or n == len(targets):
                    P.log(f"[{SOURCE}] results {n}/{len(targets)} (week {ev['first_week']}); requests={client.requests}; "
                          + ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items()) if k.startswith("results")))
        if client is not None and args.pageless_days:
            days = [d for d in pageless_days([ev for ev in pageless_of(events, kinds) if only is None]) if d < today]
            for n, day in enumerate(days, 1):
                r = stalls.note(fetch_day(client, receipts, session, day))
                outcomes[f"day:{r.get('error') or r.get('status')}" + (":cached" if r.get("skipped") else "")] += 1
                if n % 100 == 0 or n == len(days):
                    P.log(f"[{SOURCE}] date pages of events without a page {n}/{len(days)}; requests={client.requests}")
    except (P.Blocked, P.BudgetExhausted) as stop:
        summary["stopped"] = f"{type(stop).__name__}: {stop}"
        P.log(f"[{SOURCE}] STOPPED: {stop}")
        events, cal_stats = calendar_events(receipts, mondays, today)
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    if args.no_stage:
        summary.update(client=client.stats() if client else None, finished_at=P.utc_now_iso(),
                       seconds=round(time.time() - started, 1))
        return summary
    # The staged tables are shared and always hold every week on disk, the week in progress included, whatever this run
    # fetched: on 13 Oct 2026 a --weeks run restaged only its own two weeks over the full listing
    # (docs/studies/data_gaps_2026/process_log.md)
    all_mondays = [d - dt.timedelta(days=2) for d in wednesdays(*week_range(None, today, current=True))]
    events, cal_stats = calendar_events(receipts, all_mondays, today)
    kinds = tuple(KINDS)
    summary["staged_range"] = f"{all_mondays[0]} .. {all_mondays[-1]} (every week on disk)"
    staged, counts = stage(receipts, events, kinds)
    summary["staged"] = staged

    # samples: drawn once every target event of the full range is listed, then frozen
    records = pd.DataFrame()
    everything_listed = all(counts.get(ev["key"], {}).get("section_status") in (200, 404)
                            for ev in targets_of(events, kinds))
    if SAMPLES_CSV.exists() or (full_range and everything_listed and not summary.get("stopped")):
        samples = freeze_samples(args.seed, args.per_tour)
        if client is not None and not args.skip_samples and not summary.get("stopped"):
            try:
                outcomes.update(fetch_samples(client, receipts, samples, stalls))
            except (P.Blocked, P.BudgetExhausted) as stop:
                summary["stopped"] = f"{type(stop).__name__}: {stop}"
                P.log(f"[{SOURCE}] STOPPED: {stop}")
        records = sample_records(receipts, samples)
        records.to_csv(SAMPLES_CSV, index=False)
    else:
        P.log(f"[{SOURCE}] samples wait until every target event of the full range is listed")
    if not args.no_pages:
        summary["staged"].update(TL.stage(receipts))
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    summary["client"] = client.stats() if client else None
    summary["session_pages_opened"] = session.opened

    # evidence: each event, and each edition of the map against the events
    editions = pd.DataFrame()
    ev_frame = pd.DataFrame([{**{c: e.get(c) for c in EVENT_COLUMNS}, **counts.get(k, {}),
                              "weeks": ";".join(sorted(e["weeks"]))} for k, e in events.items()],
                            columns=EVENT_COLUMNS)
    try:
        listed = pd.read_parquet(P.dump_path(SOURCE, "listed.parquet"),
                                 columns=["event_key", "tour", "discipline", "start_utc", "player1_name", "player2_name"])
        editions = link_editions(map_editions(), listed, ev_frame)
    except (OSError, ValueError, KeyError) as err:
        P.log(f"[{SOURCE}] editions not linked: {err}")
    STUDY.mkdir(parents=True, exist_ok=True)
    if not editions.empty:
        editions.to_csv(STUDY / "tennislive_editions.csv.gz", index=False)
        ev_frame["map_editions_linked"] = ev_frame["key"].map(editions.groupby("event_key").size()).fillna(0).astype(int)
    if not ev_frame.empty:
        ev_frame.sort_values(["first_week", "key"]).to_csv(STUDY / "tennislive_events.csv.gz", index=False)
    summary.update(summarize(events, counts, kinds, editions, records, cal_stats))
    errors = [r for r in receipts.all().values() if r.get("error") and not r["name"].startswith("players/")]
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["events_selected"] = len(targets_of(events, kinds))
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = P.write_summary("tennislive_summary.json", summary, root=STUDY)
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--weeks", help=f"ISO weeks FROM:TO, e.g. 2026-W27:2026-W36 (default {FIRST_WEEK} to the last "
                                        "complete week)")
    parser.add_argument("--kinds", default=",".join(KINDS), help=f"event kinds to list (default {','.join(KINDS)})")
    parser.add_argument("--limit", type=int, help="list only the N newest target events (trials)")
    parser.add_argument("--only", help="comma list of event URLs (/atp-men/<event>/) to list, of those in the weeks")
    parser.add_argument("--pageless-days", action="store_true",
                        help="also read every date page of the weeks of events without a tournament page")
    parser.add_argument("--max-requests", type=int, default=20_000, help="stop after this many HTTP requests")
    parser.add_argument("--min-interval", type=float, default=1.5, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=1.0)
    parser.add_argument("--skip-calendar", action="store_true", help="use the date pages on disk")
    parser.add_argument("--skip-results", action="store_true", help="fetch no results section")
    parser.add_argument("--skip-samples", action="store_true", help="draw the samples but fetch no match page")
    parser.add_argument("--seed", type=int, default=SAMPLE_SEED, help="the samples' seed")
    parser.add_argument("--per-tour", type=int, default=SAMPLE_PER_TOUR, help="sample pages per tour and sample")
    parser.add_argument("--through-yesterday", action="store_true",
                        help="also read the week in progress, each day's page up to yesterday (the daily feed of "
                             "doubles and start and finish times; data_gaps_2026)")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rebuild the tables and evidence from raw")
    parser.add_argument("--no-stage", action="store_true", help="fetch only; skip staging and evidence")
    parser.add_argument("--no-pages", action="store_true", help="leave the match-page tables as they are (faster)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    return 1 if summary.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())

"""WTA's own API (api.wtatennis.com): the calendar, every edition's match list, then each match's point data.

How the API is read (observed 24 Sep 2026; plain GETs, no login, no key, no header beyond an honest User-Agent):
    GET /tennis/tournaments/?page=<n>&pageSize=100&excludeLevels=ITF&from=<Y>-01-01&to=<Y>-12-31
        the calendar: every edition whose dates overlap the window, keyed by tournamentGroup.id and year (an
        edition can start in the previous December). pageInfo.numPages is 0 even when entries exist, so pages
        are counted from numEntries. Third-party code reports that without excludeLevels the dates are ignored
        and the whole list since 1960 comes back, so excludeLevels is always sent.
    GET /tennis/tournaments/<id>/<year>/matches
        every match of the edition: MatchID LS... main singles, LD... main doubles, RS... qualifying singles
        (DrawLevelType M/Q, DrawMatchType S/D), state, players, set scores, start stamp. The "account: wta"
        header the site sends changes nothing here (identical rows with and without it, 1045/2024).
    GET /tennis/tournaments/<id>/<year>/matches/<MatchID>/<endpoint>
        point-by-point            server, point winner, game score after the point, UTC time (1 s) per point
        events                    the umpire device's log: Point, Ace, Fault (firstServe true: a first-serve
                                  fault; without it: a double fault), Let, Challenge, Suspension, violations,
                                  state changes and corrections, with millisecond UTC times; each point carries
                                  its server and whether it was played on the first serve. Its conventions vary
                                  by year (src/eda/official_point_feeds/verify_wta.py reads them)
        win-probability-momentum  per point, each side's momentum and win probability (served from 2025; the
                                  probability is filled only in 2026)
        advanced-stats            match and set totals: winners and errors by wing, fault reasons, rallies, net
        stats                     the box score, match (setnum 0) and per set
    An absent document is HTTP 404 with an empty body; it is recorded as a terminal answer and not asked again.

Collected under the owner's decision of 24 Sep 2026 (docs/decisions/2026-09-24-official-point-feeds.md), regardless
of wtatennis.com's terms, which forbid automated access and harvesting, and within the decision's limits: about 2 s
between requests plus jitter, a --max-requests budget on every run (required here), everything cached with a
receipt, and a stop on any block (feeds.FeedClient). A 404 is this API's ordinary "no such document", so it does
not count towards the failure streak; a long run of them stops the run instead (--stop-after-absences, whose
default is each batch's own limit, set from its measured coverage). The
--sample mode is the bounded coverage measurement that precedes any bulk slice; bulk scope is the owner's to
approve.

Raw layout under data/raw/point_sources/wta/:
    calendar/<year>_<page>.json                     the calendar pages
    tournaments/<id>_<year>/matches.json            match lists (refetched while the edition is not past)
    matches/<id>_<year>/<MatchID>/<endpoint>.json.gz
    _receipts.jsonl

Staged (data/dump/points/wta/), all strings: editions.parquet (every year on disk), and one file per table and year,
<table>/<year>.parquet, for matches, points (point-by-point), events, stats, advanced (long) and momentum (long).
Staging streams the documents, so a year of tens of thousands of logs fits in memory. Run summaries:
data/studies/official_point_feeds/wta_summary.json (bulk) and wta_<mode>_summary.json (calendar, sample, stage), with
one line per run in runs.jsonl.

Resuming: every answer is cached with a receipt, so rerunning the same command asks only for what is missing or
failed. A document is written whole and then renamed into place, and a receipt line cut short by an interrupted run
is skipped on reading, so an interruption at any moment loses nothing but the request in flight. Errors in a row
(a network outage) pause the run for --pause-after-errors seconds and resume, up to --max-pauses times; a block
(403, 429, a challenge, a redirect or a connection reset) stops it for a report.

Usage:
    ./python.sh -m src.ingest.point_sources.wta --calendar-only --years 2019-2026 --max-requests 20
    ./python.sh -m src.ingest.point_sources.wta --sample --years 2020-2026 --max-requests 1500   # coverage
    ./python.sh -m src.ingest.point_sources.wta --years 2020 --tiers 1000,500,250,125,finals \
        --endpoints events --max-requests 6000                                                # a bulk slice
    ./python.sh -m src.ingest.point_sources.wta --stage-only --years 2019-2026

A bulk slice is the owner's to approve (docs/studies/official_point_feeds/README.md has the proposal).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import random
import sys
import time
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import feeds as F
from src.ingest.public_dump import common as C

SOURCE = "wta"
API = "https://api.wtatennis.com/tennis"
USER_AGENT = "tennis-predictions research (non-commercial; python-requests)"
PAGE_SIZE = 100
ENDPOINTS = ("point-by-point", "events", "win-probability-momentum", "advanced-stats", "stats")
POINT_ENDPOINTS = ("point-by-point", "events")
DRAWS = {("M", "S"): "main_singles", ("Q", "S"): "qual_singles", ("M", "D"): "main_doubles", ("Q", "D"): "qual_doubles"}
# calendar "level" -> tier. 2019-2020 editions carry the names used before the 2021 renaming (Premier Mandatory and
# Premier 5 became WTA 1000, Premier WTA 500, International WTA 250, 125K WTA 125); tournamentGroup.level is the
# group's current level, not the edition's, so it is kept but not used. The United Cup is "team".
TIERS = {"WTA 1000": "1000", "Premier Mandatory": "1000", "Premier 5": "1000", "WTA 500": "500", "Premier": "500",
         "WTA 250": "250", "International": "250", "WTA 125": "125", "125K": "125", "Grand Slam": "slam",
         "Finals": "finals"}
TEAM_GROUPS = {"UNITED CUP"}
SAMPLE_SEED = 20260924
SAMPLE_EDITIONS = {"1000": 2, "500": 2, "250": 2, "125": 2, "slam": 1, "finals": 1, "team": 1}
SAMPLE_SPARES = 3  # extra candidates a cell may try when a drawn edition turns out never to have been played

# The collection plan: every endpoint, in batches the owner approves (B1 and B2 one at a time; B3-B9 together on
# 29 Sep 2026: "finish B2, then continue with B3 etc..."). A batch runs only when its status is "approved" (--batch);
# src/eda/official_point_feeds/wta_todo.py turns the plan and the receipts into the to-do list. Tiers without WTA
# point data (Slams, the United Cup) are left out of the point batches; see NOT_SERVED.
# "absences" is the batch's --stop-after-absences. 404s in a row stop a run as a sign the API changed, so each limit
# sits above the longest run of 404s the batch's measured coverage allows; 0 turns the stop off (errors and blocks
# still stop the run). Matches are asked edition by edition, doubles (LD) then main (LS) then qualifying (RS) singles.
POINT_TIERS = ("1000", "500", "250", "125", "finals")
ABSENCES_DEFAULT = 150
BATCHES = [
    {"id": "B1", "endpoints": ("events",), "years": "2020-2026", "tiers": POINT_TIERS, "draws": None, "from_date": None,
     "status": "approved", "approved_on": "2026-09-24", "absences": 150,
     "note": "the umpire's point log, every draw (option B of the scope proposal)"},
    {"id": "B2", "endpoints": ("events",), "years": "2019", "tiers": POINT_TIERS, "draws": None, "from_date": None,
     "status": "approved", "approved_on": "2026-09-25", "absences": 150,
     "note": "the point log for 2019 (present for both 2019 finals checked); to start when B1 is done"},
    {"id": "B3", "endpoints": ("stats",), "years": "2019-2026", "tiers": POINT_TIERS, "draws": None, "from_date": None,
     "status": "approved", "approved_on": "2026-09-29", "absences": 1500,
     "note": "box score; present for every sampled main-singles match; qualifying, doubles and 2019 unmeasured. "
             "Absence limit: 2019's log is empty before 1 April (about 1,050 matches in a row), and so may its box "
             "score be"},
    {"id": "B4", "endpoints": ("advanced-stats",), "years": "2025-2026", "tiers": POINT_TIERS, "draws": None,
     "from_date": None, "status": "approved", "approved_on": "2026-09-29", "absences": 400,
     "note": "full detail (by wing, forced errors, rallies, net, fault reasons); qualifying and doubles unmeasured. "
             "Absence limit: if both lack it, one edition's qualifying and the next one's doubles run to about 70"},
    {"id": "B5", "endpoints": ("win-probability-momentum",), "years": "2026", "tiers": POINT_TIERS, "draws": None,
     "from_date": None, "status": "approved", "approved_on": "2026-09-29", "absences": 1000,
     "note": "real win probabilities; some finals hold a one-point stub; qualifying and doubles unmeasured. "
             "Absence limit: 2 of 4 sampled WTA 125 main-singles matches lack it, so whole editions may"},
    {"id": "B6", "endpoints": ("win-probability-momentum",), "years": "2025", "tiers": POINT_TIERS, "draws": None,
     "from_date": None, "status": "approved", "approved_on": "2026-09-29", "absences": 1000,
     "note": "momentum only (the probability is unfilled). Absence limit as B5; in the event the three editions of 29-30 "
             "Dec 2024 lacked it but for Auckland's doubles (117 404s in a row at most), and every match from 6 Jan 2025 "
             "on has it but for scattered gaps"},
    {"id": "B7", "endpoints": ("advanced-stats",), "years": "2021-2024", "tiers": POINT_TIERS, "draws": None,
     "from_date": None, "status": "approved", "approved_on": "2026-09-29", "absences": 400,
     "note": "zeros in 2021, winner and unforced-error totals in 2022-24. Absence limit as B4"},
    {"id": "B8", "endpoints": ("point-by-point",), "years": "2022-2026", "tiers": POINT_TIERS, "draws": None,
     "from_date": "2022-03-14", "status": "approved", "approved_on": "2026-09-29", "absences": 0,
     "note": "a second point record; none from October 2025 to February 2026 in the sample, 2026 finals missing. "
             "Absence stop off: months without it mean thousands of 404s in a row; 2022-24, where every sampled "
             "match had it, is run first with --stop-after-absences 400"},
    {"id": "B9", "endpoints": ("stats",), "years": "2024-2026", "tiers": ("slam",), "draws": None, "from_date": None,
     "status": "approved", "approved_on": "2026-09-29", "absences": 600,
     "note": "Slam box scores (their point data comes from the Slams' own feeds, not the WTA's). Absence limit: a "
             "Slam's qualifying (112 matches) and the next one's doubles (63) may both lack it"},
]
NOT_SERVED = [  # measured on the 24 Sep 2026 sample and in the batches; the evidence is in
    # docs/studies/official_point_feeds/README.md
    {"what": "point-by-point before mid-March 2022", "endpoints": ("point-by-point",), "years": "2019-2022",
     "why": "404 for all 125 sampled matches of 2020-21 and early 2022 and both 2019 finals; present from Charleston "
            "(4 Apr 2022)"},
    {"what": "win probability before 2025", "endpoints": ("win-probability-momentum",), "years": "2019-2024",
     "why": "404 for all 105 sampled main-singles matches of 2020-24; 2019 not asked"},
    {"what": "advanced statistics before 2021", "endpoints": ("advanced-stats",), "years": "2019-2020",
     "why": "404 for all 16 sampled matches of 2020; 2019 not asked"},
    {"what": "point-by-point from October 2025 to March 2026", "endpoints": ("point-by-point",), "years": "2025-2026",
     "why": "batch B8: all 3,112 matches of the editions that began in those six months answer 404; it is patchy "
            "from June to September 2025 and back for most matches from April 2026"},
    {"what": "the point log before April 2019", "endpoints": ("events",), "years": "2019",
     "why": "batch B2: all 1,088 logs from Brisbane and Auckland (31 Dec 2018) to Guadalajara (11 Mar 2019), and "
            "Monterrey's and Charleston's qualifying (30-31 Mar), are served empty; points from 1 April 2019, with one "
            "earlier exception (Acapulco qualifying RS008, 24 Feb)"},
    {"what": "15 of 2019's 64 editions", "endpoints": ENDPOINTS, "years": "2019",
     "why": "their match lists answer 404 (Miami, Rome and Toronto among them), so no match of theirs can be asked"},
    {"what": "Slam point data (events, point-by-point, win probability)", "endpoints": ("events", "point-by-point",
     "win-probability-momentum"), "years": "2019-2026",
     "why": "logs empty and point-by-point 404 for every sampled Slam match of 2024-26; Slam matches of 2020-23 are "
            "not listed at all, nor the 2024 Australian Open's and Wimbledon's (empty match lists, batch B9)"},
    {"what": "United Cup", "endpoints": ENDPOINTS, "years": "2023-2026", "why": "its match list is empty every year"},
    {"what": "qualifying doubles", "endpoints": ENDPOINTS, "years": "2019-2026",
     "why": "no WTA match list holds a qualifying-doubles draw"},
    {"what": "years before 2019", "endpoints": ENDPOINTS, "years": "-2018",
     "why": "the one 2018 log asked (Charleston final) was empty, and 2019's logs hold points only from 1 April; "
            "the 2016 list uses an older format"},
]

EDITION_COLUMNS = ["tournament_id", "year", "tier", "level", "group_level", "group_name", "title", "start_date",
                   "end_date", "surface", "in_outdoor", "city", "country", "singles_draw_size", "doubles_draw_size",
                   "prize_money", "prize_money_currency", "live_scoring_id", "status", "calendar_file"]
MATCH_KEYS = ["MatchID", "EventID", "EventYear", "DrawLevelType", "DrawMatchType", "RoundID", "MatchState",
              "ResultString", "ScoreString", "NumSets", "ScoreSys", "Winner", "MatchTimeStamp", "MatchTimeTotal",
              "LastUpdated", "DateSeq", "CourtID", "Serve", "PointA", "PointB", "Message",
              "PlayerIDA", "PlayerNameFirstA", "PlayerNameLastA", "PlayerCountryA", "EntryTypeA", "SeedA",
              "PlayerIDA2", "PlayerNameFirstA2", "PlayerNameLastA2", "PlayerCountryA2",
              "PlayerIDB", "PlayerNameFirstB", "PlayerNameLastB", "PlayerCountryB", "EntryTypeB", "SeedB",
              "PlayerIDB2", "PlayerNameFirstB2", "PlayerNameLastB2", "PlayerCountryB2",
              "ScoreSet1A", "ScoreSet1B", "ScoreSet2A", "ScoreSet2B", "ScoreSet3A", "ScoreSet3B",
              "ScoreSet4A", "ScoreSet4B", "ScoreSet5A", "ScoreSet5B",
              "ScoreTbSet1", "ScoreTbSet2", "ScoreTbSet3", "ScoreTbSet4", "BinPacketBase64",
              # kept for the match-timing clock (docs/decisions/2026-10-05-match-timing.md): whether MatchTimeStamp is
              # a scheduled estimate rather than the actual start (true for most Slam rows), and the court
              "estimatedStartTime", "isEstimatedStartTime", "Venue"]
MATCH_COLUMNS = (["tournament_id", "year", "match_id", "tier", "draw", "walkover"] + MATCH_KEYS +
                 [f"{e.replace('-', '_')}_status" for e in ENDPOINTS] + ["listing_file", "listing_retrieved_at"])
POINT_COLUMNS = ["tournament_id", "year", "match_id", "match_status", "point_number", "set", "game", "server",
                 "point_winner", "game_score_a", "game_score_b", "set_score_a", "set_score_b", "set_tb_a", "set_tb_b",
                 "timestamp"]
EVENT_COLUMNS = ["tournament_id", "year", "match_id", "index", "name", "type", "reason", "player", "first_serve",
                 "server", "receiver", "score", "set", "game", "game_score", "match_score", "match_state",
                 "match_time", "timestamp", "timestamp_local", "player_id", "umpire_id", "court_id", "last_updated",
                 "attributes"]
LONG_COLUMNS = ["tournament_id", "year", "match_id", "path", "value"]
STAT_KEYS = ["eventyear", "eventid", "matchid", "setnum", "settime", "scorea", "scoreb", "scoretb", "acesa", "acesb",
             "dblflta", "dblfltb", "ptswon1stserva", "ptswon1stservb", "ptsplayed1stserva", "ptsplayed1stservb",
             "ptstotwonserva", "ptstotwonservb", "totservplayeda", "totservplayedb", "breakptsconva", "breakptsconvb",
             "breakptsplayeda", "breakptsplayedb", "servgamesplayeda", "servgamesplayedb", "pts1stservlosta",
             "pts1stservlostb", "totptswona", "totptswonb", "acesssa", "acesssb"]  # the box score's fields, 2020-2026
STAT_COLUMNS = ["tournament_id", "year", "match_id"] + STAT_KEYS + ["other"]


# --------------------------------------------------------------------------------------
# classification and parsing (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def tier_of(entry: dict) -> str:
    """Tier of a calendar entry: 1000/500/250/125/slam/finals/team, else the level text in lower case."""
    group = entry.get("tournamentGroup") or {}
    if (group.get("name") or "").upper() in TEAM_GROUPS:
        return "team"
    level = entry.get("level") or group.get("level") or ""
    return TIERS.get(level, level.lower() or "unknown")


def draw_of(match: dict) -> str:
    return DRAWS.get((match.get("DrawLevelType"), match.get("DrawMatchType")),
                     f"{match.get('DrawLevelType')}{match.get('DrawMatchType')}")


def is_walkover(match: dict) -> bool:
    """No ball struck: MatchState W, or a result string naming a walkover."""
    result = (match.get("ResultString") or "").lower()
    return match.get("MatchState") == "W" or "w/o" in result or "walkover" in result


def is_played(match: dict) -> bool:
    return match.get("MatchState") == "F" and not is_walkover(match)


def flatten_edition(entry: dict, calendar_file: str) -> dict:
    group = entry.get("tournamentGroup") or {}
    return {
        "tournament_id": str(group.get("id")), "year": int(entry["year"]), "tier": tier_of(entry),
        "level": entry.get("level"), "group_level": group.get("level"), "group_name": group.get("name"),
        "title": entry.get("title"), "start_date": entry.get("startDate"), "end_date": entry.get("endDate"),
        "surface": entry.get("surface"), "in_outdoor": entry.get("inOutdoor"), "city": entry.get("city"),
        "country": entry.get("country"), "singles_draw_size": entry.get("singlesDrawSize"),
        "doubles_draw_size": entry.get("doublesDrawSize"), "prize_money": entry.get("prizeMoney"),
        "prize_money_currency": entry.get("prizeMoneyCurrency"), "live_scoring_id": entry.get("liveScoringId"),
        "status": entry.get("status"), "calendar_file": calendar_file,
    }


def point_rows(tid: str, year: int, mid: str, payload: dict) -> list[dict]:
    """One row per point of a point-by-point document, in the document's order.

    ``scoreAfterPoint.sets`` holds the final score of the point's set, not the running score (third-party
    report, confirmed on 1045/2024/LS001: point 1 already reads 1-6), so it is kept as the set's result."""
    rows = []
    status = payload.get("matchStatus")
    for p in payload.get("points") or []:
        after = p.get("scoreAfterPoint") or {}
        game = after.get("gameScore") or {}
        sets = {s.get("team"): s for s in after.get("sets") or [] if s.get("setNumber") == p.get("setNumber")}
        a, b = sets.get("A") or {}, sets.get("B") or {}
        rows.append({
            "tournament_id": tid, "year": year, "match_id": mid, "match_status": status,
            "point_number": p.get("pointNumber"), "set": p.get("setNumber"), "game": p.get("gameNumber"),
            "server": p.get("server"), "point_winner": p.get("pointWinner"),
            "game_score_a": game.get("teamAScore"), "game_score_b": game.get("teamBScore"),
            "set_score_a": a.get("score"), "set_score_b": b.get("score"),
            "set_tb_a": a.get("tieBreakScore"), "set_tb_b": b.get("tieBreakScore"), "timestamp": p.get("timestamp"),
        })
    return rows


def event_rows(tid: str, year: int, mid: str, payload: dict) -> list[dict]:
    """One row per record of an events document; the Attributes object is also kept verbatim as JSON."""
    rows = []
    for e in payload.get("Events") or []:
        attrs = e.get("Attributes") or {}
        rows.append({
            "tournament_id": tid, "year": year, "match_id": mid, "index": e.get("Index"), "name": e.get("Name"),
            "type": attrs.get("type"), "reason": attrs.get("reason"), "player": attrs.get("player"),
            "first_serve": attrs.get("firstServe"), "server": attrs.get("server"), "receiver": attrs.get("receiver"),
            "score": attrs.get("score"), "set": e.get("Set"), "game": e.get("Game"), "game_score": e.get("GameScore"),
            "match_score": e.get("MatchScore"), "match_state": e.get("MatchState"), "match_time": e.get("MatchTime"),
            "timestamp": e.get("Timestamp"), "timestamp_local": e.get("TimestampLocal"), "player_id": e.get("PlayerId"),
            "umpire_id": e.get("ITFUmpireID"), "court_id": e.get("CourtID"), "last_updated": e.get("LastUpdated"),
            "attributes": attrs,
        })
    return rows


def stats_rows(tid: str, year: int, mid: str, payload) -> list[dict]:
    """The box score: one row per set (setnum 0 is the match), every field kept (any field not in STAT_KEYS goes
    into ``other`` as JSON)."""
    out = []
    for row in (payload if isinstance(payload, list) else []):
        if isinstance(row, dict):
            other = {k: v for k, v in row.items() if k not in STAT_KEYS}
            out.append({"tournament_id": tid, "year": year, "match_id": mid, **row, "other": other or None})
    return out


def flatten(value, prefix: str = ""):
    """(path, leaf) pairs of a JSON value, lists indexed as [n]; empty containers are kept as leaves."""
    if isinstance(value, dict) and value:
        for key, child in value.items():
            yield from flatten(child, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list) and value:
        for n, child in enumerate(value):
            yield from flatten(child, f"{prefix}[{n}]")
    else:
        yield prefix, value


def long_rows(tid: str, year: int, mid: str, payload) -> list[dict]:
    return [{"tournament_id": tid, "year": year, "match_id": mid, "path": path, "value": value}
            for path, value in flatten(payload)]


def has_points(payload) -> bool:
    """A document with at least one point (point-by-point) or one scoring record (events)."""
    if not isinstance(payload, dict):
        return False
    if "points" in payload:
        return bool(payload.get("points"))
    return any(e.get("Name") in ("Point", "Ace", "Fault") for e in payload.get("Events") or [])


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
def make_client(min_interval: float, jitter: float, max_requests: int | None) -> F.FeedClient:
    """FeedClient over a plain python-requests session: the API answers it, so no browser fingerprint is used."""
    import requests

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return F.FeedClient("requests", min_interval=min_interval, jitter=jitter, max_requests=max_requests,
                        session=session)


class TooManyErrors(F.Stopped):
    """Errors in a row (a network outage, say): the run pauses and resumes, up to --max-pauses times."""


class TooManyAbsences(F.Stopped):
    """404s in a row, a sign the API changed: the run stops for a report."""


def note(errors: F.FailureStreak, absences: F.FailureStreak, receipt: dict) -> None:
    """Feed a receipt to the two streaks: errors count towards ``errors``, 404s towards ``absences``."""
    if receipt.get("skipped"):
        return
    absent = receipt.get("status") == 404 and not receipt.get("error")
    try:
        errors.note({**receipt, "status": 200} if absent else receipt)
    except F.Stopped as stop:
        raise TooManyErrors(str(stop)) from None
    try:
        absences.note(receipt if absent else {**receipt, "status": 200, "error": None})
    except F.Stopped as stop:
        raise TooManyAbsences(str(stop)) from None


def batch_by_id(batch_id: str) -> dict:
    batch = next((b for b in BATCHES if b["id"] == batch_id), None)
    if batch is None:
        raise SystemExit(f"no batch {batch_id!r}; the plan has {', '.join(b['id'] for b in BATCHES)}")
    return batch


HARD_STOPS = ("Blocked", "TooManyAbsences", "TooManyErrors")  # a run that ended this way is not followed by another


def wait_for_process(pid: int) -> None:
    """Return once process ``pid`` has exited (at once when there is no such process)."""
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if handle:
            kernel32.WaitForSingleObject(handle, 0xFFFFFFFF)
            kernel32.CloseHandle(handle)
        return
    import os

    while True:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(30)


def previous_hard_stop(summary_path: Path) -> str | None:
    """How the last bulk run stopped, when it was a block or a streak (HARD_STOPS), else None."""
    if not summary_path.exists():
        return None
    import json

    stopped = json.loads(summary_path.read_text(encoding="utf-8")).get("stopped") or ""
    return stopped if stopped.startswith(HARD_STOPS) else None


def apply_batch(args) -> dict | None:
    """Fill the run's selection from --batch, refusing a batch the owner has not approved. --years may narrow it, and
    an explicit --stop-after-absences overrides the batch's limit."""
    if not args.batch:
        if args.stop_after_absences is None:
            args.stop_after_absences = ABSENCES_DEFAULT
        return None
    batch = batch_by_id(args.batch)
    if batch["status"] != "approved":
        raise SystemExit(f"batch {batch['id']} is {batch['status']}, not approved: its scope is the owner's to approve")
    if args.sample or args.calendar_only or args.stage_only:
        raise SystemExit("--batch runs a bulk slice; it does not combine with --sample, --calendar-only or --stage-only")
    planned = parse_years(batch["years"])
    wanted = parse_years(args.years) if args.years else planned
    outside = sorted(set(wanted) - set(planned))
    if outside:
        raise SystemExit(f"years {outside} are outside batch {batch['id']} ({batch['years']})")
    args.years = ",".join(str(y) for y in wanted)
    args.endpoints = ",".join(batch["endpoints"])
    args.tiers = ",".join(batch["tiers"]) if batch["tiers"] else None
    args.draws = ",".join(batch["draws"]) if batch["draws"] else None
    args.from_date = batch["from_date"]
    if args.stop_after_absences is None:
        args.stop_after_absences = batch.get("absences", ABSENCES_DEFAULT)
    return batch


def calendar_url(year: int, page: int) -> str:
    return (f"{API}/tournaments/?page={page}&pageSize={PAGE_SIZE}&excludeLevels=ITF"
            f"&from={year}-01-01&to={year}-12-31")


def matches_url(tid: str, year: int) -> str:
    return f"{API}/tournaments/{tid}/{year}/matches"


def endpoint_url(tid: str, year: int, mid: str, endpoint: str) -> str:
    return f"{API}/tournaments/{tid}/{year}/matches/{mid}/{endpoint}"


def listing_dest(tid: str, year: int) -> Path:
    return P.raw_path(SOURCE, "tournaments", f"{tid}_{year}", "matches.json")


def endpoint_dest(tid: str, year: int, mid: str, endpoint: str) -> Path:
    return P.raw_path(SOURCE, "matches", f"{tid}_{year}", mid, f"{endpoint}.json.gz")


def endpoint_name(tid: str, year: int, mid: str, endpoint: str) -> str:
    return f"matches/{tid}/{year}/{mid}/{endpoint}"


def fetch_calendar(client: P.Client, receipts, year: int, *, refresh: bool) -> dict:
    """Every page of one year's calendar."""
    out = {"year": year, "pages": 0, "entries": 0, "errors": []}
    page = 0
    while True:
        dest = P.raw_path(SOURCE, "calendar", f"{year}_{page}.json")
        receipt = P.fetch(client, calendar_url(year, page), dest, receipts, name=f"calendar/{year}/{page}",
                          refresh=refresh, validator=P.json_validator, extra={"year": year, "page": page})
        if receipt.get("error") or receipt.get("status") != 200:
            out["errors"].append(f"page {page}: {receipt.get('error') or receipt.get('status')}")
            break
        payload = P.read_json(dest)
        content = payload.get("content") or []
        total = (payload.get("pageInfo") or {}).get("numEntries")
        out["pages"] += 1
        out["entries"] += len(content)
        page += 1
        if not content or total is None or page * PAGE_SIZE >= int(total):
            break
    return out


def calendar_years() -> list[int]:
    """Years with calendar pages on disk."""
    folder = P.raw_path(SOURCE, "calendar")
    return sorted({int(p.stem.split("_")[0]) for p in folder.glob("*_*.json")}) if folder.exists() else []


def load_editions(years: list[int]) -> list[dict]:
    """Editions of the given years from the calendar pages on disk, one per (tournament id, year)."""
    wanted, seen = set(years), {}
    folder = P.raw_path(SOURCE, "calendar")
    for path in sorted(folder.glob("*_*.json")) if folder.exists() else []:
        for entry in P.read_json(path).get("content") or []:
            if entry.get("year") is None or int(entry["year"]) not in wanted:
                continue
            edition = flatten_edition(entry, P.rel(path))
            seen.setdefault((edition["tournament_id"], edition["year"]), edition)
    return sorted(seen.values(), key=lambda e: (e["year"], e["start_date"] or "", int(e["tournament_id"])))


def fetch_listing(client: P.Client, receipts, edition: dict, *, refresh: bool) -> dict:
    tid, year = edition["tournament_id"], edition["year"]
    return P.fetch(client, matches_url(tid, year), listing_dest(tid, year), receipts,
                   name=f"tournaments/{tid}/{year}/matches", refresh=refresh or edition.get("status") != "past",
                   validator=P.json_validator, extra={"tournament_id": tid, "year": year, "tier": edition["tier"]})


def load_listing(tid: str, year: int) -> list[dict]:
    dest = listing_dest(tid, year)
    return (P.read_json(dest).get("matches") or []) if dest.exists() else []


def fetch_endpoint(client: P.Client, receipts, tid: str, year: int, mid: str, endpoint: str, *,
                   refresh: bool, extra: dict | None = None) -> dict:
    return P.fetch(client, endpoint_url(tid, year, mid, endpoint), endpoint_dest(tid, year, mid, endpoint), receipts,
                   name=endpoint_name(tid, year, mid, endpoint), refresh=refresh, validator=P.json_validator,
                   compress=True, extra={"tournament_id": tid, "year": year, "match_id": mid, "endpoint": endpoint,
                                         **(extra or {})})


def endpoint_status(receipts, tid: str, year: int, mid: str, endpoint: str) -> str | None:
    """"200", "404", an error text, or None when never asked."""
    receipt = receipts.get(endpoint_name(tid, year, mid, endpoint))
    if not receipt:
        return None
    return receipt.get("error") or str(receipt.get("status"))


# --------------------------------------------------------------------------------------
# selection: the coverage sample and bulk slices
# --------------------------------------------------------------------------------------
def _rng(*parts) -> random.Random:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def sample_cells(editions: list[dict], *, seed: int = SAMPLE_SEED,
                 per_tier: dict | None = None) -> list[tuple[tuple, list[dict]]]:
    """Each (year, tier) cell's candidate editions, in a seeded random order.

    Candidates are past editions with a singles draw (the calendar keeps 2020's cancelled events without one)
    or team events, which never list one. A candidate that turns out to have no played match (an event
    cancelled after its draw size was set) is replaced by the next one; see run()."""
    per_tier = per_tier or SAMPLE_EDITIONS
    cells: dict[tuple, list[dict]] = {}
    for e in editions:
        if e.get("status") == "past" and e["tier"] in per_tier and (e["singles_draw_size"] or e["tier"] == "team"):
            cells.setdefault((e["year"], e["tier"]), []).append(e)
    out = []
    for (year, tier), group in sorted(cells.items()):
        group = sorted(group, key=lambda e: int(e["tournament_id"]))
        _rng(seed, year, tier).shuffle(group)
        out.append(((year, tier), group))
    return out


def sample_matches(edition: dict, matches: list[dict], *, seed: int = SAMPLE_SEED) -> list[tuple[dict, tuple]]:
    """(match, endpoints) pairs for one sampled edition; empty when it has no played match.

    Main singles: the final and one other match, each with all five endpoints. Qualifying singles, main doubles
    and qualifying doubles: one match each, with the two point-level endpoints. Slams and team events, where
    the WTA's own point feed is not expected (third-party report for the Slams), get the final's point
    endpoints and box score and one other main singles match's point endpoints only."""
    rng = _rng(seed, edition["tournament_id"], edition["year"])
    played = sorted((m for m in matches if is_played(m)), key=lambda m: m["MatchID"])
    by_draw: dict[str, list[dict]] = {}
    for m in played:
        by_draw.setdefault(draw_of(m), []).append(m)
    light = edition["tier"] in ("slam", "team")
    out = []
    singles = by_draw.get("main_singles") or []
    final = next((m for m in singles if str(m.get("RoundID")) == "F"), None)
    if final is not None:
        out.append((final, POINT_ENDPOINTS + ("stats",) if light else ENDPOINTS))
    others = [m for m in singles if m is not final]
    if others:
        out.append((rng.choice(others), POINT_ENDPOINTS if light else ENDPOINTS))
    if not light:
        for draw in ("qual_singles", "main_doubles", "qual_doubles"):
            if by_draw.get(draw):
                out.append((rng.choice(by_draw[draw]), POINT_ENDPOINTS))
    return out


def parse_years(text: str | None) -> list[int]:
    """"2020-2026" or "2020,2022" -> sorted list of years."""
    if not text:
        return []
    years: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            years.update(range(int(a), int(b) + 1))
        elif part:
            years.add(int(part))
    return sorted(years)


def split_list(text: str | None) -> list[str] | None:
    return [x.strip() for x in text.split(",") if x.strip()] if text else None


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def match_row(edition: dict, m: dict, receipts, listing: dict) -> dict:
    tid, year, mid = edition["tournament_id"], edition["year"], m.get("MatchID")
    row = {"tournament_id": tid, "year": year, "match_id": mid, "tier": edition["tier"], "draw": draw_of(m),
           "walkover": is_walkover(m), "listing_file": listing.get("dest"),
           "listing_retrieved_at": listing.get("retrieved_at")}
    row.update({k: m.get(k) for k in MATCH_KEYS})
    for endpoint in ENDPOINTS:
        row[f"{endpoint.replace('-', '_')}_status"] = endpoint_status(receipts, tid, year, mid, endpoint)
    return row


def year_matches(year: int, receipts):
    """(edition, match, listing receipt) for every listed match of the year's editions."""
    for edition in load_editions([year]):
        tid = edition["tournament_id"]
        listing = receipts.get(f"tournaments/{tid}/{year}/matches") or {}
        for m in load_listing(tid, year):
            yield edition, m, listing


def document_rows(year: int, receipts, endpoint: str, to_rows, columns: list[str]):
    """Staged rows of one endpoint's saved documents for one year, one document at a time."""
    for edition, m, _ in year_matches(year, receipts):
        tid, mid = edition["tournament_id"], m.get("MatchID")
        dest = endpoint_dest(tid, year, mid, endpoint)
        if endpoint_status(receipts, tid, year, mid, endpoint) != "200" or not dest.exists():
            continue
        for r in to_rows(tid, year, mid, P.read_json(dest)):
            yield [P.s(r.get(c)) for c in columns]


def stage_stream(name: str, dest: Path, columns: list[str], rows, *, now: str, extra: dict) -> dict:
    """Write rows to string Parquet as they come (C.stage_rows batches them), with the provenance sidecar."""
    prov = C.Provenance(SOURCE, P.rel(P.raw_path(SOURCE)), None, now, extra)
    stats = C.stage_rows(columns, ((i + 1, r) for i, r in enumerate(rows)), dest, prov)
    C.write_meta(dest, {"branch": "points", "source": SOURCE, "table": name, "dest": P.rel(dest), "rows": stats["rows"],
                        "columns": stats["columns"], "bytes": stats["bytes"], "retrieved_at": now, **extra})
    P.log(f"[{SOURCE}] staged {stats['dest']}: {stats['rows']:,} rows")
    return {"rows": stats["rows"], "dest": stats["dest"], "bytes": stats["bytes"]}


def stage(years: list[int], receipts) -> dict:
    """Rebuild the staged tables from the raw files: editions.parquet for every year on disk, and one file per table
    and year (matches/<year>.parquet, events/<year>.parquet, ...) for ``years``, written as the documents are read so
    that memory stays flat however many matches a year holds."""
    now = P.utc_now_iso()
    on_disk = calendar_years()
    out = {"editions": stage_stream("editions", P.dump_path(SOURCE, "editions.parquet"), EDITION_COLUMNS,
                                    ([P.s(e.get(c)) for c in EDITION_COLUMNS] for e in load_editions(on_disk)),
                                    now=now, extra={"years": ";".join(str(y) for y in on_disk)})}
    for year in years:
        extra = {"year": str(year)}
        tables = (
            ("matches", MATCH_COLUMNS, ([P.s(match_row(e, m, receipts, lst).get(c)) for c in MATCH_COLUMNS]
                                        for e, m, lst in year_matches(year, receipts))),
            ("points", POINT_COLUMNS, document_rows(year, receipts, "point-by-point", point_rows, POINT_COLUMNS)),
            ("events", EVENT_COLUMNS, document_rows(year, receipts, "events", event_rows, EVENT_COLUMNS)),
            ("stats", STAT_COLUMNS, document_rows(year, receipts, "stats", stats_rows, STAT_COLUMNS)),
            ("advanced", LONG_COLUMNS, document_rows(year, receipts, "advanced-stats", long_rows, LONG_COLUMNS)),
            ("momentum", LONG_COLUMNS, document_rows(year, receipts, "win-probability-momentum", long_rows, LONG_COLUMNS)),
        )
        for name, columns, rows in tables:
            out[f"{name}/{year}"] = stage_stream(name, P.dump_path(SOURCE, name, f"{year}.parquet"), columns, rows,
                                                 now=now, extra=extra)
    return out


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def outcome_key(kind: str, receipt: dict) -> str:
    return f"{kind}:{receipt.get('error') or receipt.get('status')}" + (":cached" if receipt.get("skipped") else "")


def select_bulk(editions: list[dict], args) -> list[tuple[dict, dict, tuple]]:
    """(edition, match, endpoints) for a bulk slice, oldest year first, editions by start date."""
    tiers = set(split_list(args.tiers) or [])
    draws = set(split_list(args.draws) or [])
    endpoints = tuple(split_list(args.endpoints) or ENDPOINTS)
    out = []
    for edition in editions:
        if tiers and edition["tier"] not in tiers:
            continue
        for m in sorted(load_listing(edition["tournament_id"], edition["year"]), key=lambda m: m["MatchID"]):
            if not is_played(m) or (draws and draw_of(m) not in draws):
                continue
            out.append((edition, m, endpoints))
    return out


def run(args) -> dict:
    P.configure_stdout()
    batch = apply_batch(args)
    if args.after_pid:
        # queued behind a running batch: wait for it, and start only if it did not end on a block or a streak
        P.log(f"[{SOURCE}] {P.utc_now_iso()} waiting for process {args.after_pid} to finish")
        wait_for_process(args.after_pid)
        stop = previous_hard_stop(F.STUDY_ROOT / "wta_summary.json")
        if stop:
            raise SystemExit(f"the previous run stopped with {stop!r}; not starting (the decision: stop and report)")
        P.log(f"[{SOURCE}] {P.utc_now_iso()} process {args.after_pid} has finished; starting")
    started = time.time()
    years = parse_years(args.years)
    if not years:
        raise SystemExit("--years is required (for example --years 2020-2026)")
    if not args.stage_only and not args.max_requests:
        raise SystemExit("--max-requests is required for every run that makes requests (the decision's budget rule)")
    mode = "stage" if args.stage_only else "calendar" if args.calendar_only else "sample" if args.sample else "bulk"
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "mode": mode, "batch": batch and batch["id"], "started_at": P.utc_now_iso(),
               "args": vars(args), "decision": F.DECISION, "years": years,
               "receipts_unreadable_lines": receipts.unreadable_lines}
    client = None if args.stage_only else make_client(args.min_interval, args.jitter, args.max_requests)
    errors_streak = F.FailureStreak(args.stop_after_failures)
    absences_streak = F.FailureStreak(args.stop_after_absences)
    this_year = dt.date.today().year
    outcomes: Counter = Counter()
    selected: dict[tuple, tuple] = {}  # (tournament id, year, MatchID) -> (edition, match, endpoints), once each
    try:
        if client is not None:
            summary["calendar"] = [fetch_calendar(client, receipts, y, refresh=args.refresh_calendar or y >= this_year)
                                   for y in years]
        editions = load_editions(years)
        summary["editions"] = dict(sorted(Counter(f"{e['year']}|{e['tier']}" for e in editions).items()))

        def listing(edition: dict) -> list[dict]:
            receipt = fetch_listing(client, receipts, edition, refresh=args.refresh)
            outcomes[outcome_key("listing", receipt)] += 1
            note(errors_streak, absences_streak, receipt)
            return load_listing(edition["tournament_id"], edition["year"])

        def endpoints_of(edition: dict, m: dict, endpoints: tuple, progress: str = "") -> None:
            for endpoint in endpoints:
                receipt = fetch_endpoint(client, receipts, edition["tournament_id"], edition["year"], m["MatchID"],
                                         endpoint, refresh=args.refresh,
                                         extra={"tier": edition["tier"], "draw": draw_of(m), "round": m.get("RoundID"),
                                                "sampled": bool(args.sample), "batch": batch and batch["id"]})
                outcomes[outcome_key(endpoint, receipt)] += 1
                note(errors_streak, absences_streak, receipt)
            selected[(edition["tournament_id"], edition["year"], m["MatchID"])] = (edition, m, endpoints)
            if len(selected) % 25 == 0:
                rate = client.requests / max(time.time() - started, 1)
                P.log(f"[{SOURCE}] {P.utc_now_iso()} {progress} {len(selected)} matches; requests={client.requests} "
                      f"({rate * 3600:.0f}/h); " + ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items())))

        def sample_pass() -> None:
            # cell by cell: draw candidates in seeded order until the cell has its editions with played matches
            sampled = summary["sampled_editions"] = []
            for (year, tier), candidates in sample_cells(editions, seed=args.seed):
                want, tried = SAMPLE_EDITIONS[tier], 0
                for edition in candidates:
                    if sum(1 for e in sampled if (e["year"], e["tier"]) == (year, tier)) >= want \
                            or tried >= want + SAMPLE_SPARES:
                        break
                    tried += 1
                    picks = sample_matches(edition, listing(edition), seed=args.seed)
                    entry = {"year": year, "tier": tier, "tournament_id": edition["tournament_id"],
                             "title": edition["title"]}
                    if not picks:
                        summary.setdefault("sample_skipped", []).append({**entry, "reason": "no played match listed"})
                        continue
                    sampled.append({**entry, "matches": len(picks)})
                    for m, endpoints in picks:
                        endpoints_of(edition, m, endpoints)

        def bulk_pass() -> None:
            # year by year, oldest first; each year's listings, then its matches' endpoints
            tiers = set(split_list(args.tiers) or [])
            chosen = [e for e in editions if (not tiers or e["tier"] in tiers)
                      and (not args.from_date or (e["start_date"] or "") >= args.from_date)]
            summary["editions_selected"] = len(chosen)
            done = 0
            for year in years:
                of_year = [e for e in chosen if e["year"] == year]
                for edition in of_year:
                    listing(edition)
                plan = select_bulk(of_year, args)
                if args.limit:
                    plan = plan[:max(0, args.limit - done)]
                P.log(f"[{SOURCE}] {P.utc_now_iso()} {year}: {len(of_year)} editions, {len(plan)} matches, "
                      f"{sum(len(e) for _, _, e in plan)} endpoint requests at most (cached ones are skipped)")
                for n, (edition, m, endpoints) in enumerate(plan, 1):
                    endpoints_of(edition, m, endpoints, progress=f"{year} {n}/{len(plan)}")
                done += len(plan)

        work = None if client is None or args.calendar_only else sample_pass if args.sample else bulk_pass
        pauses = summary["pauses"] = []
        while work is not None:
            try:
                work()
                break
            except TooManyErrors as stop:  # a network outage, say: wait, then pick up where it stopped
                if len(pauses) >= args.max_pauses:
                    raise
                pauses.append({"at": P.utc_now_iso(), "after": str(stop), "requests": client.requests})
                P.log(f"[{SOURCE}] {P.utc_now_iso()} {stop}; pausing {args.pause_after_errors:.0f} s "
                      f"({len(pauses)} of {args.max_pauses}), then resuming")
                time.sleep(args.pause_after_errors)
                errors_streak.count = 0
        summary["matches_selected"] = len(selected)
        if selected:
            P.log(f"[{SOURCE}] {P.utc_now_iso()} {len(selected)} matches; requests={client.requests}; " +
                  ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items())))
    except (P.Blocked, P.BudgetExhausted, F.Stopped) as stop:
        summary["stopped"] = f"{type(stop).__name__}: {stop}"
        P.log(f"[{SOURCE}] {P.utc_now_iso()} STOPPED: {stop}")
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    if client is not None:
        summary["client"] = client.stats()
    if not args.no_stage and not args.calendar_only:
        summary["staged"] = stage(years, receipts)  # one file per table and year: other years' files are left as they are
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts"] = dict(sorted(Counter(
        f"{r['name'].split('/')[0]}:{r.get('error') and 'error' or r.get('status')}" for r in receipts.all().values()).items()))
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = F.write_summary("wta_summary.json" if mode == "bulk" else f"wta_{mode}_summary.json", summary)
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--batch", help="run an approved batch of the collection plan (BATCHES), e.g. B1; "
                                        "--years may narrow it")
    parser.add_argument("--years", help="editions' years, e.g. 2020-2026 or 2020,2022 (required without --batch)")
    parser.add_argument("--after-pid", type=int, help="first wait for this process (a running batch) to exit; do not "
                                                      "start if the last bulk run ended on a block or a streak")
    parser.add_argument("--calendar-only", action="store_true", help="fetch the calendars only")
    parser.add_argument("--sample", action="store_true", help="the seeded coverage sample instead of a bulk slice")
    parser.add_argument("--seed", type=int, default=SAMPLE_SEED)
    parser.add_argument("--tiers", help="bulk: comma list of tiers (1000,500,250,125,slam,finals,team)")
    parser.add_argument("--draws", help="bulk: comma list of draws (main_singles,qual_singles,main_doubles,qual_doubles)")
    parser.add_argument("--endpoints", help=f"bulk: comma list of endpoints (default: {','.join(ENDPOINTS)})")
    parser.add_argument("--from-date", help="bulk: only editions starting on or after this date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, help="only the first N selected matches")
    parser.add_argument("--max-requests", type=int, help="stop after this many HTTP requests (required unless --stage-only)")
    parser.add_argument("--min-interval", type=float, default=2.0, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=1.0, help="up to this many extra seconds, drawn at random")
    parser.add_argument("--stop-after-failures", type=int, default=5,
                        help="stop after this many errors in a row (0: never)")
    parser.add_argument("--stop-after-absences", type=int, default=None,
                        help="stop after this many 404 answers in a row, a sign the API changed (0: never; default: "
                             f"the batch's own limit, else {ABSENCES_DEFAULT})")
    parser.add_argument("--pause-after-errors", type=float, default=600,
                        help="after --stop-after-failures errors in a row, wait this many seconds and resume")
    parser.add_argument("--max-pauses", type=int, default=12,
                        help="stop for good after this many such pauses (a block always stops at once)")
    parser.add_argument("--refresh", action="store_true", help="refetch documents already answered (404s included)")
    parser.add_argument("--refresh-calendar", action="store_true", help="refetch past years' calendar pages")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rebuild the Parquet tables")
    parser.add_argument("--no-stage", action="store_true", help="fetch only; skip the Parquet rebuild")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    return 1 if summary.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())

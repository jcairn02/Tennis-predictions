"""TDI Tennis Results (results.tennisdata.com): ATP Tour and Challenger point-by-point pages.

Collected under the owner's decision of 25 Sep 2026 (docs/decisions/2026-09-25-tdi-tennis-results.md), which
extends the 24 Sep decision on the official feeds to this site regardless of its no-scraping terms, within the
same limits: about 2 s between requests plus jitter, a --max-requests budget on every run (required here),
everything cached with a receipt and nothing fetched twice, a stop and report on any block (HTTP 403 or 429, a
challenge, a redirect, a connection reset) with no escalation, and no logins, CAPTCHAs or decryption.

Endpoints (server-rendered Next.js pages; the data is in the React Server Components payload, the
self.__next_f.push([1, "..."]) strings, JSON-decoded and joined):
    https://results.tennisdata.com/en                         the default listing (the last few days' matches),
                                                               with the tournament filter (id, title, city) and
                                                               the player filter (id, full, first and last name)
    https://results.tennisdata.com/en?date=YYYY-MM-DD         one day's completed matches, inside a rolling window
                                                               (on 25 Sep 2026 it began at 25 Jun: 24 Jun, listed
                                                               in full the day before, was gone); an older date is
                                                               answered with the default listing
    https://results.tennisdata.com/en?tournamentId=<uuid>     one tournament's matches inside the window
    https://results.tennisdata.com/en/results/<match uuid>    one match: HTTP 200 inside the window, and HTTP 404
                                                               with every point still in the page outside it

A listing shows one card per completed match: a link to /en/results/<match uuid>, the round, the tournament's
name, a UTC timestamp (a "$D..." date) and, for each player in order, an element keyed by the player's uuid
(the filter's player id) with country, short name, seed or entry note, set scores and a check mark for the
winner. Singles cards have two players; doubles cards four, the first two one team and the last two the other.

A match page holds:
    <title>            "A vs B | 2025#339#MS020 | Tennis Results": the ATP year, tournament id and match code
                       (MS, QS, MD, QD); the meta description adds the event, the place and the score
    the header         "Completed on <$D date> at <tournament> in <place>", then each player keyed by uuid: the ATP
                       headshot URL (whose last part is the ATP player id), the full name, country, short name and
                       seed; the scoreboard's games per set, tiebreak points in <sup>
    the points         ExpandedPointDetails objects, one per point, id <match uuid>-<set>-<game>-<point>: time,
                       completedDateUtc, winner, teamServing, playerServing/Receiving, both scores after the point,
                       rally (SERVE, FAULT, LET, ACE, POINT_COMPLETE), pointBreakdown (outcome, serve, totalShots,
                       winningShotType, errorType, situation), break, deuce, game and set flags and the streak
    the statistics     the Summary tab: for the match and each set, rows of "value A | label | value B" under
                       category headings, TennisViz ratings included

Raw layout under data/raw/point_sources/tdi/ (every page gzipped):
    listings/home/<sweep>.html.gz                     the default listing, once per sweep
    listings/date/<day>.html.gz                       a settled day (more than --settle-days before the
                                                      sweep's last day): read once, ever
    listings/date/<day>@<sweep>.html.gz               a day still filling up: read once per sweep
    listings/tournament/<id>@<sweep>.html.gz          a tournament's listing: read once per sweep
    matches/<first two characters>/<match uuid>.html.gz   a match page, kept when it answered 200, or 404 with
                                                      points; a 404 without points is recorded as absent
    _receipts.jsonl                                   one line per fetch (URL, time, status, bytes, SHA-256)
    _sweeps.jsonl                                     one line when a sweep starts (its plan) and one when it ends
    _run.lock                                         held by the running process; the OS releases it if the
                                                      process dies

A sweep is one pass over the listings: the default listing, every day of its plan oldest first (the window's
oldest day is partial and slides continuously), then every tournament of the sweep's own default listing. Its
plan is written to _sweeps.jsonl when it starts. A run that is interrupted (a block, the budget, a crash, a
closed terminal) is continued by running the same command again: the open sweep is resumed with the same plan,
and nothing already saved is asked for again.

Match pages are fetched in batches, each a separate run with its own budget; the ids come from the id index (the
listings), the Wayback Machine's list (--wayback-ids) or --ids. A batch that is interrupted loses at most the
page in flight: the next batch asks only for pages not yet saved. A run exits 0 when it ends normally or by using
up its budget, and 1 when it was stopped (a block, a failure streak, or failed staging).

Staged (data/dump/points/tdi/, strings): listing_pages.parquet (one row per listing page read), listing_cards
(one row per card seen), match_ids (one row per distinct match id: the id index), filter_tournaments and
filter_players (the default listing's filter lists); matches (one row per match page asked for), points (one
row per point, pointBreakdown flattened and the rally kept), statistics (one row per statistic, period and
category) and players (TDI player uuid, ATP id, names and country as the pages show them). Tour or Challenger
is the level of the ATP tournament id in Jeff Sackmann's archive (data/dump/matches/sackmann_archive/atp),
else "challenger" when the tournament's name says so, else "unknown". Reports in
data/studies/official_point_feeds/: tdi_listing_days.csv, tdi_listing_tournaments.csv and tdi_summary.json;
each run adds a line to runs.jsonl.

Usage:
    ./python.sh -m src.ingest.point_sources.tdi --max-requests 200                  # start or resume a sweep
    ./python.sh -m src.ingest.point_sources.tdi --max-requests 4 --dates 2026-06-24 --tournaments 0   # a pilot
    ./python.sh -m src.ingest.point_sources.tdi --pages --max-requests 500 --no-stage   # a batch of match pages
    ./python.sh -m src.ingest.point_sources.tdi --wayback-ids --max-requests 500        # the Wayback ids' pages
    ./python.sh -m src.ingest.point_sources.tdi --recent 10 --max-requests 1000         # weekly forward capture
    ./python.sh -m src.ingest.point_sources.tdi --stage-only                        # rebuild the tables, no HTTP

Forward capture: --recent 10 once a week reads the last ten days (the week, plus the days still filling up) and
fetches every new match's page, about 500 requests. The listing keeps about three months, so a missed week is
caught up by the next run; a gap of more than about 90 days loses matches.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import datetime as dt
import gzip
import html as html_lib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import feeds as F

SOURCE = "tdi"
SITE = "https://results.tennisdata.com"
DECISION = "docs/decisions/2026-09-25-tdi-tennis-results.md"
IMPERSONATE = "chrome"
DAYS_BACK = 95    # the window keeps about 93 days; two more, so the first days asked show where it ends
SETTLE_DAYS = 3   # matches appear about 15 minutes after they end; a day this far back is complete
SWEEPS = P.raw_path(SOURCE, "_sweeps.jsonl")
LOCK = P.raw_path(SOURCE, "_run.lock")

PUSH = re.compile(r'self\.__next_f\.push\(\[1,"([^"\\]*(?:\\.[^"\\]*)*)"\]\)')
ROW_HEAD = re.compile(r"([0-9a-f]{1,8}):")
REF = re.compile(r"^\$(?:L|@)?([0-9a-f]{1,8})$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
RESULT_HREF = re.compile(r"^/en/results/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$")
COUNTRY = re.compile(r"^[A-Z]{3}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CHECK_MARK = "M20 6 9 17l-5-5"  # the path of the check icon on the winner's row

PAGE_COLUMNS = [
    "name", "kind", "key", "sweep", "settled", "url", "status", "absent", "error", "retrieved_at", "bytes",
    "sha256", "cards", "singles", "doubles", "other_cards", "stamp_days", "listing_status", "tournament_titles",
    "title_matches", "rsc_chunks_undecoded", "source_file",
]
CARD_COLUMNS = [
    "match_id", "found_by", "listing_kind", "listing_key", "sweep", "listing_status", "stamp", "stamp_day",
    "stamp_matches_listing_day", "round", "tournament", "header_extra", "players", "draw_type",
    "team1_player_ids", "team1_names", "team1_countries", "team1_entry", "team1_scores", "team1_winner_mark",
    "team2_player_ids", "team2_names", "team2_countries", "team2_entry", "team2_scores", "team2_winner_mark",
    "retrieved_at", "source_file",
]
ID_COLUMNS = [
    "match_id", "listing_day", "stamp", "stamp_day", "round", "tournament", "tournament_id", "tournament_title",
    "draw_type", "team1_player_ids", "team1_names", "team2_player_ids", "team2_names", "found_by", "sightings",
    "in_date_listing", "in_tournament_listing", "in_home_listing", "first_seen", "last_seen", "conflicts",
]
TOURNAMENT_COLUMNS = ["tournament_id", "title", "city", "first_sweep", "last_sweep", "sweeps"]
PLAYER_COLUMNS = ["player_id", "full_name", "first_name", "last_name", "first_sweep", "last_sweep", "sweeps"]


# --------------------------------------------------------------------------------------
# the React Server Components payload (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def rsc_text(html: str) -> tuple[str, int]:
    """The page's RSC payload, every self.__next_f.push([1, "..."]) string JSON-decoded and joined in page order,
    and how many strings could not be decoded (kept verbatim)."""
    out, bad = [], 0
    for chunk in PUSH.findall(html):
        try:
            out.append(json.loads('"' + chunk + '"'))
        except ValueError:
            out.append(chunk)
            bad += 1
    return "".join(out), bad


def rsc_rows(text: str, imports: dict | None = None) -> dict:
    """The payload's rows by id, read in sequence: "<hex id>:<JSON>\\n" decoded; a text row
    ("<id>:T<hex byte length>,<text>", no newline after it) kept as text and skipped by its length; other rows
    (an upper-case tag such as I for imports or HL for hints) ignored to the end of their line. When ``imports``
    is given, it receives each import row's client component name ("<id>:I[<module>,[<chunks>],"<name>"]")."""
    decoder = json.JSONDecoder()
    rows, pos, n = {}, 0, len(text)
    while pos < n:
        m = ROW_HEAD.match(text, pos)
        line_end = text.find("\n", pos)
        next_line = n if line_end < 0 else line_end + 1
        if not m:
            pos = next_line
            continue
        rid, j = m.group(1), m.end()
        head = text[j:j + 1]
        if head == "T":
            comma = text.find(",", j)
            try:
                size = int(text[j + 1:comma], 16)
            except ValueError:
                pos = next_line
                continue
            k, used = comma + 1, 0
            while used < size and k < n:
                used += len(text[k].encode("utf-8"))
                k += 1
            rows[rid], pos = text[comma + 1:k], k
        elif head.isupper():
            if head == "I" and imports is not None:
                with contextlib.suppress(ValueError, IndexError, TypeError):
                    value, _ = decoder.raw_decode(text, j + 1)
                    imports[rid] = value[2] if len(value) > 2 else None
            pos = next_line
        else:
            try:
                value, end = decoder.raw_decode(text, j)
            except ValueError:
                pos = next_line
                continue
            rows[rid] = value
            pos = end + 1 if text[end:end + 1] == "\n" else end
    return rows


def page_rows(html: str) -> tuple[dict, int]:
    text, bad = rsc_text(html)
    return rsc_rows(text), bad


def page_parts(html: str) -> tuple[dict, dict, int]:
    """A page's rows, its client component names by row id, and the undecodable push strings."""
    text, bad = rsc_text(html)
    imports = {}
    rows = rsc_rows(text, imports)
    return rows, imports, bad


def is_element(node) -> bool:
    """A React element as RSC writes it: ["$", type, key, props]."""
    return isinstance(node, list) and len(node) == 4 and node[0] == "$" and isinstance(node[3], dict)


def resolve(node, rows: dict, seen: frozenset):
    """A "$L<id>", "$@<id>" or "$<id>" reference replaced by its row, once per path so a cycle ends."""
    if isinstance(node, str):
        m = REF.match(node)
        if m and m.group(1) in rows and m.group(1) not in seen:
            return rows[m.group(1)], seen | {m.group(1)}
    return node, seen


def filter_lists(rows: dict) -> dict:
    """The listing's filter lists: ``tournaments`` [{id, title, city}] and ``players`` [{id, full_name, ...}]."""
    out = {"tournaments": None, "players": None}

    def visit(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in out and out[key] is None and isinstance(value, list) and value \
                        and all(isinstance(x, dict) and "id" in x for x in value):
                    out[key] = value
                else:
                    visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    for value in rows.values():
        visit(value)
    return out


def card_elements(rows: dict) -> list:
    """Every match card of a listing (an element linking to /en/results/<uuid>), first sighting of each id."""
    found, seen = [], set()

    def visit(node):
        if is_element(node):
            m = RESULT_HREF.match(str(node[3].get("href") or ""))
            if m:
                if m.group(1) not in seen:
                    seen.add(m.group(1))
                    found.append(node)
                return
            visit(node[3].get("children"))
        elif isinstance(node, list):
            for item in node:
                visit(item)

    for value in rows.values():
        visit(value)
    return found


def card_events(card, rows: dict, match_id: str) -> list[tuple]:
    """The card's content in document order, references followed: ("text", s), ("date", s), ("player", uuid) ...
    ("end_player", uuid), ("set", n) ... ("end_set", n) and ("check",) for the winner's check mark."""
    events = []

    def visit(node, seen):
        node, seen = resolve(node, rows, seen)
        if is_element(node):
            kind, key, props = node[1], node[2], node[3]
            if isinstance(props.get("date"), str):
                events.append(("date", props["date"]))
            if kind == "path" and props.get("d") == CHECK_MARK:
                events.append(("check",))
            player = isinstance(key, str) and key != match_id and bool(UUID.match(key))
            score_cell = isinstance(key, str) and key.isdigit()
            if player:
                events.append(("player", key))
            if score_cell:
                events.append(("set", key))
            visit(props.get("children"), seen)
            if score_cell:
                events.append(("end_set", key))
            if player:
                events.append(("end_player", key))
        elif isinstance(node, list):
            for item in node:
                visit(item, seen)
        elif isinstance(node, str):
            if not node.startswith("$"):
                events.append(("text", node))
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            events.append(("text", str(node)))

    visit(card[3].get("children"), frozenset())
    return events


def stamp_day(stamp: str | None) -> str | None:
    """The UTC day of a card's timestamp ("$D2026-06-24T16:12:33.456Z" -> "2026-06-24")."""
    value = (stamp or "").removeprefix("$D")
    return value[:10] if DAY.match(value[:10]) else None


def card_record(card, rows: dict) -> dict:
    """One card as a flat record: the header (round, tournament), the timestamp and the players in order,
    grouped into two teams when there are two (singles) or four (doubles)."""
    match_id = RESULT_HREF.match(card[3]["href"]).group(1)
    events = card_events(card, rows, match_id)
    header, stamp, players, current, set_no = [], None, [], None, None
    for event in events:
        tag = event[0]
        if tag == "date" and stamp is None:
            stamp = event[1]
        elif tag == "player":
            current = {"id": event[1], "texts": [], "scores": {}, "check": False}
            players.append(current)
        elif tag == "end_player":
            current = None
        elif tag == "set":
            set_no = event[1]
        elif tag == "end_set":
            set_no = None
        elif tag == "check" and current is not None:
            current["check"] = True
        elif tag == "text":
            text = event[1].strip()
            if not text:
                continue
            if current is None:
                if not players:
                    header.append(text)
            elif set_no is not None:
                current["scores"].setdefault(set_no, []).append(text)
            else:
                current["texts"].append(text)
    for p in players:
        texts = p.pop("texts")
        p["country"] = next((t for t in texts if COUNTRY.match(t)), None)
        rest = [t for t in texts if t != p["country"]]
        joined = " ".join(rest)
        entry = re.search(r"\(\s*([^()]*?)\s*\)", joined.replace("( ", "(").replace(" )", ")"))
        p["entry"] = entry.group(1).replace(" ", "") if entry else None
        p["name"] = next((t for t in rest if t not in ("(", ")") and re.search(r"[^\W\d_]", t)), None)
    record = {"match_id": match_id, "round": header[0] if header else None,
              "tournament": header[1] if len(header) > 1 else None,
              "header_extra": " | ".join(header[2:]) or None, "stamp": (stamp or "").removeprefix("$D") or None,
              "players": len(players)}
    record["stamp_day"] = stamp_day(stamp)
    half = len(players) // 2 if len(players) in (2, 4) else None
    record["draw_type"] = {2: "singles", 4: "doubles"}.get(len(players), "unknown")
    teams = (players[:half], players[half:]) if half else (players, [])
    for n, team in enumerate(teams, 1):
        record.update({
            f"team{n}_player_ids": ";".join(p["id"] for p in team) or None,
            f"team{n}_names": ";".join(p["name"] or "" for p in team) or None,
            f"team{n}_countries": ";".join(p["country"] or "" for p in team) or None,
            f"team{n}_entry": next((p["entry"] for p in team if p["entry"]), None),
            f"team{n}_scores": " ".join(f"{k}:{'/'.join(v)}" for p in team for k, v in sorted(p["scores"].items(),
                                                                                             key=lambda kv: int(kv[0])))
                               or None,
            f"team{n}_winner_mark": any(p["check"] for p in team) if team else None,
        })
    return record


def listing_cards(rows: dict) -> list[dict]:
    return [card_record(card, rows) for card in card_elements(rows)]


def date_listing_status(day: str, cards: list[dict]) -> str:
    """How a ?date= listing stands: its cards' UTC days all equal the day asked ("in_window"), none do (the
    default listing served for a day outside the window: "outside_window"), some do ("mixed"), or no cards."""
    if not cards:
        return "empty"
    on_day = sum(1 for c in cards if c["stamp_day"] == day)
    if on_day == len(cards):
        return "in_window"
    return "outside_window" if on_day == 0 else "mixed"


def title_key(title: str | None) -> str:
    return " ".join((title or "").split()).casefold()


def tournament_listing_status(title: str | None, cards: list[dict]) -> tuple[str, bool | None]:
    """How a ?tournamentId= listing stands: one tournament name on every card ("one_tournament") or several
    (a default listing served in its place would show several), and whether that name is the filter's title."""
    if not cards:
        return "empty", None
    names = {title_key(c["tournament"]) for c in cards}
    return ("one_tournament" if len(names) == 1 else "several_tournaments"), title_key(title) in names


# --------------------------------------------------------------------------------------
# match pages (pure functions; tested offline)
# --------------------------------------------------------------------------------------
TITLE = re.compile(r"^(?P<teams>.*?) \| (?P<code>(?P<year>\d{4})#(?P<tournament>\d+)#(?P<match>(?P<event>[A-Z]+)\d+))"
                   r" \| Tennis Results\s*$")
DESCRIPTION = re.compile(r"^Match (?P<code>\S+) - (?P<event>.+?) at (?P<place>.+?)\s*[\r\n]+\s*(?P<score>.*?)\s*$", re.S)
POINT_ID = re.compile(r"^(?P<match>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
                      r"-(?P<set>\d{2})-(?P<game>\d{2})-(?P<point>\d{3})$")
HEADSHOT = re.compile(r"/player-headshot/(?P<atp>[^/?#]+)$")
LAZY = re.compile(r"^\$L([0-9a-f]{1,8})$")
VENUE = re.compile(r"^\s*at\s+(?P<tournament>.+?)(?:\s+in\s+(?P<place>.+?))?\s*$", re.S)
EVENT_CODES = {"MS": ("singles", "main"), "QS": ("singles", "qualifying"), "MD": ("doubles", "main"),
               "QD": ("doubles", "qualifying")}
POINT_KEYS = {"__typename", "ace", "complete", "completedDateUtc", "gameNumber", "gamePoint", "gameWon", "id",
              "isBreakPoint", "isBreakSave", "isDeuce", "playerReceiving", "playerServing", "pointBreakdown",
              "pointNumber", "pointSequence", "rally", "serving", "setNumber", "setPoint", "setWon", "streak",
              "teamAGamesWon", "teamAScore", "teamBGamesWon", "teamBScore", "teamServing", "time", "winner"}
BREAKDOWN_KEYS = {"outcome", "serve", "totalShots", "winningShotType", "errorType", "situation"}


def element_name(node, imports: dict) -> str:
    """An element's type, a client component's name when the type is a "$L<id>" import."""
    kind = node[1]
    if isinstance(kind, str):
        m = LAZY.match(kind)
        return (imports.get(m.group(1)) or kind) if m else kind
    return str(kind)


def walk(node, rows: dict, visit, seen: frozenset = frozenset()) -> bool:
    """Children depth first in document order, references followed once per path. ``visit("element", el)`` may
    return "skip" (not its children) or "stop" (end the walk); ``visit("text", s)`` sees each text. False once
    stopped."""
    node, seen = resolve(node, rows, seen)
    if is_element(node):
        said = visit("element", node)
        if said == "stop":
            return False
        return True if said == "skip" else walk(node[3].get("children"), rows, visit, seen)
    if isinstance(node, list):
        return all(walk(item, rows, visit, seen) for item in node)
    if isinstance(node, str):
        return not (node.strip() and not node.startswith("$") and visit("text", node) == "stop")
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return visit("text", str(node)) != "stop"
    return True


def node_text(node, rows: dict, imports: dict | None = None, skip: tuple = ()) -> str:
    """Every text under ``node`` joined; elements named in ``skip`` are left out."""
    parts = []

    def visit(kind, value):
        if kind == "text":
            parts.append(value)
        elif skip and element_name(value, imports or {}) in skip:
            return "skip"

    walk(node, rows, visit)
    return "".join(parts).strip()


def find_elements(rows: dict, test) -> list:
    """Every element in the rows (their own content, props included, references not followed) that passes
    ``test(element)``, in row order."""
    found = []

    def visit(node):
        if is_element(node):
            if test(node):
                found.append(node)
            for value in node[3].values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, dict):
            for value in node.values():
                visit(value)

    for value in rows.values():
        visit(value)
    return found


def page_title(html: str) -> str | None:
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    return html_lib.unescape(m.group(1)).strip() if m else None


def title_fields(title: str | None) -> dict:
    """The ATP code of "A vs B | 2025#339#MS020 | Tennis Results": year, tournament id, match code and event."""
    m = TITLE.match(title or "")
    if not m:
        return {"teams_text": None, "atp_code": None, "atp_year": None, "atp_tournament_id": None,
                "atp_match_code": None, "event_code": None, "draw_type": None, "draw": None}
    draw_type, draw = EVENT_CODES.get(m.group("event"), (None, None))
    return {"teams_text": m.group("teams"), "atp_code": m.group("code"), "atp_year": m.group("year"),
            "atp_tournament_id": m.group("tournament"), "atp_match_code": m.group("match"),
            "event_code": m.group("event"), "draw_type": draw_type, "draw": draw}


def description_fields(rows: dict) -> dict:
    """The meta description, "Match <code> - Men's Singles at <place> \\r\\n <score>", split up."""
    metas = find_elements(rows, lambda e: e[1] == "meta" and e[3].get("name") == "description")
    text = metas[0][3].get("content") if metas else None
    m = DESCRIPTION.match(text or "")
    return {"description": text, "description_event": m.group("event") if m else None,
            "description_place": m.group("place") if m else None, "description_score": m.group("score") if m else None}


def score_cell(cell, rows: dict) -> str:
    """One set of the scoreboard: games, and the tiebreak points of a <sup> ("7/5" for 7 with 5 in the tiebreak)."""
    games, tiebreak = [], []

    def visit(kind, value):
        if kind == "text":
            games.append(value)
        elif value[1] == "sup":
            tiebreak.append(node_text(value, rows))
            return "skip"

    walk(cell[3].get("children"), rows, visit)
    return "".join(games).strip() + ("/" + "".join(tiebreak) if tiebreak else "")


def player_details(block, rows: dict, imports: dict) -> dict:
    """What an element keyed by a player's uuid shows: the ATP id (the headshot URL's last part), the full name,
    the country, the short name and the seed or entry note (the initials of the avatar's fallback left out)."""
    out, texts = {}, []

    def visit(kind, value):
        if kind == "text":
            texts.append(value.strip())
            return None
        name = element_name(value, imports)
        if name == "AvatarFallback":
            return "skip"
        src = value[3].get("src")
        if isinstance(src, str) and HEADSHOT.search(src):
            out.setdefault("atp_id", HEADSHOT.search(src).group("atp"))
            out.setdefault("full_name", value[3].get("alt"))
        return None

    walk(block, rows, visit)
    texts = [t for t in texts if t]
    country = next((t for t in texts if COUNTRY.match(t)), None)
    if country:
        out["country"] = country
    entry = re.search(r"\(([^()]*)\)", "".join(texts))
    if entry:
        out["entry"] = entry.group(1).strip()
    name = next((t for t in texts if t != country and t not in ("(", ")") and re.search(r"[^\W\d_]", t)
                 and not (entry and t == entry.group(1).strip())), None)
    if name:
        out["short_name"] = name
    return out


def match_header(rows: dict, imports: dict, match_id: str) -> dict:
    """The header above the tabs: the h1, "Completed on <date> at <tournament> in <place>", the players in order
    of first appearance (team A's, then team B's) and the scoreboard's first two rows of set cells."""
    heads = [e for e in find_elements(rows, lambda e: e[1] == "h1") if " vs " in node_text(e, rows)]
    out = {"h1": node_text(heads[0], rows) if heads else None, "completed_on": None, "venue": None,
           "tournament": None, "place": None, "players": [], "score_rows": []}
    if not heads:
        return out
    root = next(value for value in rows.values() if any(e is heads[0] for e in find_in(value)))
    players, order, cells = {}, [], []

    def visit(kind, value):
        if kind == "text":
            return None
        name, key, props = element_name(value, imports), value[2], value[3]
        if name == "Tabs":
            return "stop"
        kids = props.get("children")
        if isinstance(kids, list) and kids and isinstance(kids[0], str) and kids[0].startswith("Completed on"):
            dates = find_in(kids, lambda e: isinstance(e[3].get("date"), str))
            out["completed_on"] = dates[0][3]["date"].removeprefix("$D") if dates else None
            out["venue"] = "".join(k for k in kids[1:] if isinstance(k, str)).strip() or None
            return "skip"
        if isinstance(key, str) and key != match_id and UUID.match(key):
            if key not in players:
                players[key] = {"player_id": key}
                order.append(key)
            for field, v in player_details(value, rows, imports).items():
                players[key].setdefault(field, v)
            return "skip"
        if isinstance(key, str) and key.isdigit() and value[1] == "div":
            if key == "1" or not cells:
                cells.append([])
            cells[-1].append(f"{key}:{score_cell(value, rows)}")
            return "skip"
        return None

    walk(root, rows, visit)
    venue = VENUE.match(out["venue"] or "")
    if venue:
        out["tournament"], out["place"] = venue.group("tournament"), venue.group("place")
    out["players"] = [players[k] for k in order]
    out["score_rows"] = [" ".join(row) for row in cells[:2]]
    return out


def find_in(node, test=lambda e: True) -> list:
    """Every element inside ``node`` (props included, references not followed) passing ``test``."""
    return find_elements({"_": node}, test)


def team_fields(header: dict) -> dict:
    """The header's players as two teams: the first half team A, the second team B (two or four players)."""
    players = header["players"]
    half = len(players) // 2 if len(players) in (2, 4) else None
    teams = (players[:half], players[half:]) if half else ([], [])
    out = {"players_in_header": len(players)}
    for side, team, score in zip("ab", teams, header["score_rows"] + [None, None]):
        out.update({
            f"team_{side}_player_ids": ";".join(p["player_id"] for p in team) or None,
            f"team_{side}_atp_ids": ";".join(p.get("atp_id") or "" for p in team) or None,
            f"team_{side}_names": ";".join(p.get("full_name") or "" for p in team) or None,
            f"team_{side}_short_names": ";".join(p.get("short_name") or "" for p in team) or None,
            f"team_{side}_countries": ";".join(p.get("country") or "" for p in team) or None,
            f"team_{side}_entry": next((p["entry"] for p in team if p.get("entry")), None),
            f"team_{side}_scores": score,
        })
    return out


PATH_REF = re.compile(r"^\$([0-9a-f]{1,8})((?::[^:]+)+)$")


def deref(value, rows: dict, depth: int = 0):
    """An RSC path reference ("$62:props:children:props:details:2:streak": a value the payload wrote once, pointed
    back to) replaced by the value it names, following lazy references on the way; anything else as it is."""
    m = PATH_REF.match(value) if isinstance(value, str) else None
    if not m or m.group(1) not in rows or depth > 8:
        return value
    node = rows[m.group(1)]
    for part in m.group(2).split(":")[1:]:
        node, _ = resolve(node, rows, frozenset())
        if is_element(node) and part == "props":
            node = node[3]
        elif isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return value
        node = deref(node, rows, depth + 1)
    return node


def resolved_point(point: dict, rows: dict) -> dict:
    """A point object with path references replaced, at its top level and one level down (the scores, the
    breakdown, the streak and the rally's events)."""
    out = {}
    for key, value in point.items():
        value = deref(value, rows)
        if isinstance(value, dict):
            value = {k: deref(v, rows) for k, v in value.items()}
        elif isinstance(value, list):
            value = [deref(v, rows) for v in value]
        out[key] = value
    return out


def match_points(rows: dict) -> list[dict]:
    """Every ExpandedPointDetails object of the page, once each, in (set, game, point) order of its id, with path
    references resolved."""
    found = {}

    def visit(node):
        if isinstance(node, dict):
            if node.get("__typename") == "ExpandedPointDetails" and isinstance(node.get("id"), str):
                found.setdefault(node["id"], node)
                return
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    for value in rows.values():
        visit(value)

    def key(p):
        m = POINT_ID.match(p["id"])
        return (int(m.group("set")), int(m.group("game")), int(m.group("point"))) if m else (10 ** 6, 0, 0)

    return sorted((resolved_point(p, rows) for p in found.values()), key=lambda p: (key(p), p["id"]))


def point_team_names(rows: dict) -> tuple:
    """The names the point tables use for team A and team B (the PointBreakdown component's props)."""
    for value in rows.values():
        stack = [value]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if isinstance(node.get("teamA"), str) and isinstance(node.get("teamB"), str) and "details" in node:
                    return node["teamA"], node["teamB"]
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    return None, None


def sets_text(sets) -> str | None:
    """A score's sets as "1:6/0 2:4/0": set number, games and tiebreak points, as the point object gives them."""
    items = sorted((s for s in sets or [] if isinstance(s, dict)), key=lambda s: s.get("setNumber") or 0)
    return " ".join(f"{s.get('setNumber')}:{s.get('setScore')}/{s.get('setTieBreakerScore')}" for s in items) or None


def point_record(point: dict) -> dict:
    """One point flattened: identity, clock, score after the point, flags, pointBreakdown, and the rally's events
    in sequence ("SERVE/FAULT/SERVE/POINT_COMPLETE"); any unknown key kept under ``extra``."""
    m = POINT_ID.match(point.get("id") or "")
    as_dict = lambda value: value if isinstance(value, dict) else {}  # noqa: E731 (an unresolved reference reads empty)
    a, b = as_dict(point.get("teamAScore")), as_dict(point.get("teamBScore"))
    rally = point.get("rally") if isinstance(point.get("rally"), list) else []
    rally = sorted((r for r in rally if isinstance(r, dict)), key=lambda r: r.get("sequence") or 0)
    kinds = [str(r.get("type")) for r in rally]
    breakdown, streak = as_dict(point.get("pointBreakdown")), as_dict(point.get("streak"))
    extra = {k: v for k, v in point.items() if k not in POINT_KEYS}
    extra.update({f"unresolved.{k}": v for k, v in point.items()
                  if k in ("teamAScore", "teamBScore", "pointBreakdown", "streak", "rally") and isinstance(v, str)})
    extra.update({f"pointBreakdown.{k}": v for k, v in breakdown.items() if k not in BREAKDOWN_KEYS})
    extra.update({f"rally.{k}": True for r in rally for k in r if k not in ("type", "sequence")})
    return {
        "point_id": point.get("id"), "id_match": m.group("match") if m else None,
        "id_set": int(m.group("set")) if m else None, "id_game": int(m.group("game")) if m else None,
        "id_point": int(m.group("point")) if m else None,
        "set": point.get("setNumber"), "game": point.get("gameNumber"), "point": point.get("pointNumber"),
        "point_sequence": point.get("pointSequence"), "time": point.get("time"),
        "completed_utc": point.get("completedDateUtc"), "winner": point.get("winner"),
        "team_serving": point.get("teamServing"), "player_serving": point.get("playerServing"),
        "player_receiving": point.get("playerReceiving"), "serving": point.get("serving"),
        "team_a_game_score": a.get("gameScore"), "team_b_game_score": b.get("gameScore"),
        "team_a_sets": sets_text(a.get("sets")), "team_b_sets": sets_text(b.get("sets")),
        "team_a_games_won": point.get("teamAGamesWon"), "team_b_games_won": point.get("teamBGamesWon"),
        "ace": point.get("ace"), "is_break_point": point.get("isBreakPoint"), "is_break_save": point.get("isBreakSave"),
        "is_deuce": point.get("isDeuce"), "game_point": point.get("gamePoint"), "set_point": point.get("setPoint"),
        "game_won": point.get("gameWon"), "set_won": point.get("setWon"), "complete": point.get("complete"),
        "streak_owner": streak.get("owner"), "streak_count": streak.get("count"),
        "outcome": breakdown.get("outcome"), "serve": breakdown.get("serve"), "total_shots": breakdown.get("totalShots"),
        "winning_shot_type": breakdown.get("winningShotType"), "error_type": breakdown.get("errorType"),
        "situation": breakdown.get("situation"), "rally": "/".join(kinds) or None, "rally_events": len(kinds),
        "faults": kinds.count("FAULT"), "lets": kinds.count("LET"), "extra": extra or None,
    }


def match_statistics(rows: dict, imports: dict) -> list[dict]:
    """The Summary tab's statistics: for the match ("match") and each set, every row of "value A | label | value B"
    with the category heading above it."""
    tabs = find_elements(rows, lambda e: e[3].get("animationGroup") == "stats-sets" and element_name(e, imports) == "Tabs")
    if not tabs:
        return []
    contents = []

    def gather(kind, value):
        if kind == "element" and element_name(value, imports) == "TabsContent":
            contents.append(value)
            return "skip"
        return None

    walk(tabs[0], rows, gather)
    out = []
    for content in contents:
        period = str(content[3].get("value"))
        period = "match" if period == "all" else period
        heading = [None]

        def visit(kind, value, period=period, heading=heading):
            if kind == "text":
                heading[0] = value.strip()
                return None
            kids = value[3].get("children")
            if isinstance(kids, list) and len(kids) == 3:
                parts = [resolve(k, rows, frozenset())[0] for k in kids]
                if all(is_element(x) for x in parts) and parts[1][1] == "p" and isinstance(parts[1][3].get("children"), str):
                    out.append({"period": period, "order": len(out) + 1, "category": heading[0],
                                "label": parts[1][3]["children"].strip(), "team_a": node_text(parts[0], rows),
                                "team_b": node_text(parts[2], rows)})
                    return "skip"
            return None

        walk(content[3].get("children"), rows, visit)
    return out


def parse_match_page(html: str, match_id: str) -> dict:
    """Everything a match page holds, as flat fields plus its point and statistic rows."""
    rows, imports, bad = page_parts(html)
    title = page_title(html)
    header = match_header(rows, imports, match_id)
    team_a_name, team_b_name = point_team_names(rows)
    record = {"title": title, **title_fields(title), **description_fields(rows),
              **{k: header[k] for k in ("h1", "completed_on", "venue", "tournament", "place")},
              **team_fields(header), "point_team_a_name": team_a_name, "point_team_b_name": team_b_name,
              "rsc_chunks_undecoded": bad}
    return {"match": record, "players": header["players"], "points": [point_record(p) for p in match_points(rows)],
            "statistics": match_statistics(rows, imports)}


# --------------------------------------------------------------------------------------
# sweeps, names and fetching
# --------------------------------------------------------------------------------------
def today_utc() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def read_sweeps() -> list[dict]:
    """The lines of _sweeps.jsonl; a line cut short by an interrupted write is skipped."""
    if not SWEEPS.exists():
        return []
    out = []
    for line in SWEEPS.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict) and item.get("sweep"):
            out.append(item)
    return out


def append_sweep_line(item: dict) -> None:
    SWEEPS.parent.mkdir(parents=True, exist_ok=True)
    text = SWEEPS.read_text(encoding="utf-8") if SWEEPS.exists() else ""
    with SWEEPS.open("a", encoding="utf-8") as handle:
        if text and not text.endswith("\n"):
            handle.write("\n")  # the line before was cut short: start on a fresh line
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def open_sweep(args) -> dict:
    """The sweep this run works on: the one named by --sweep, else the latest unfinished one (resumed with its
    own plan), else a new one planned from today (UTC)."""
    lines = read_sweeps()
    started = {x["sweep"]: x for x in lines if x.get("event") == "started"}
    finished = {x["sweep"] for x in lines if x.get("event") == "finished"}
    if args.sweep:
        if args.sweep not in started:
            raise SystemExit(f"unknown sweep {args.sweep!r}; known: {', '.join(sorted(started)) or 'none'}")
        return started[args.sweep]
    unfinished = sorted((s for s in started if s not in finished), key=lambda s: started[s]["at"])
    if unfinished and not args.new_sweep:
        P.log(f"[{SOURCE}] resuming sweep {unfinished[-1]} (started {started[unfinished[-1]]['at']})")
        return started[unfinished[-1]]
    now = dt.datetime.now(dt.timezone.utc)
    while now.strftime("%Y%m%dT%H%M%SZ") in started:  # labels are unique: a sweep's pages are named after it
        now += dt.timedelta(seconds=1)
    last = now.date()
    recent = getattr(args, "recent", None)
    item = {"sweep": now.strftime("%Y%m%dT%H%M%SZ"), "event": "started", "at": P.utc_now_iso(),
            "kind": "recent" if recent else "full",
            "first_day": (last - dt.timedelta(days=recent if recent else args.days_back)).isoformat(),
            "last_day": last.isoformat(), "settle_days": args.settle_days,
            "tournaments_from": None if recent else "the sweep's default listing"}
    append_sweep_line(item)
    P.log(f"[{SOURCE}] new {item['kind']} sweep {item['sweep']}: days {item['first_day']} to {item['last_day']}")
    return item


def plan_days(sweep: dict) -> list[str]:
    first, last = dt.date.fromisoformat(sweep["first_day"]), dt.date.fromisoformat(sweep["last_day"])
    return [(first + dt.timedelta(days=n)).isoformat() for n in range((last - first).days + 1)]


def is_settled(day: str, sweep: dict) -> bool:
    return dt.date.fromisoformat(day) < dt.date.fromisoformat(sweep["last_day"]) - dt.timedelta(days=sweep["settle_days"])


def home_name(sweep: dict) -> str:
    return f"list/home/{sweep['sweep']}"


def date_name(day: str, sweep: dict) -> str:
    return f"list/date/{day}" if is_settled(day, sweep) else f"list/date/{day}@{sweep['sweep']}"


def tournament_name(tournament_id: str, sweep: dict) -> str:
    return f"list/tournament/{tournament_id}@{sweep['sweep']}"


def listing_dest(name: str) -> Path:
    """list/date/2026-06-24 -> data/raw/point_sources/tdi/listings/date/2026-06-24.html.gz"""
    parts = name.split("/")[1:]
    return P.raw_path(SOURCE, "listings", *parts[:-1], parts[-1] + ".html.gz")


def page_validator(body: bytes):
    problem = P.html_validator(body)
    if problem:
        return problem
    return None if b"self.__next_f.push" in body else "no React Server Components payload in the page"


def read_page(receipt: dict | None) -> str | None:
    """A saved page's HTML, or None when none was saved (or the file is gone)."""
    if not receipt or receipt.get("status") != 200 or receipt.get("error"):
        return None
    path = listing_dest(receipt["name"])
    return P.read_bytes(path).decode("utf-8") if path.exists() else None


def done(receipt: dict | None) -> bool:
    """A fetch that needs no retry: a saved page or a terminal absence."""
    if not receipt or receipt.get("error"):
        return False
    return bool(receipt.get("absent")) or receipt.get("status") == 404 or \
        (receipt.get("status") == 200 and listing_dest(receipt["name"]).exists())


def fetch_listing(client, receipts, name: str, url: str, extra: dict) -> dict:
    return P.fetch(client, url, listing_dest(name), receipts, name=name, validator=page_validator, compress=True,
                   extra=extra)


@contextlib.contextmanager
def run_lock():
    """One fetching run at a time. The lock is an OS lock on _run.lock, released when this process ends however
    it ends, so a crashed run never leaves a stale lock (and the file itself is never deleted)."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    handle = open(LOCK, "a+b")
    locked = False
    try:
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError:
            raise SystemExit(f"another TDI run is fetching (it holds {P.rel(LOCK)}); let it finish first")
        yield
    finally:
        if locked and os.name == "nt":
            import msvcrt
            handle.seek(0)
            with contextlib.suppress(OSError):
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        handle.close()


# Listing pages saved on 24 Sep 2026 by the research session (access-routes-tdi-and-open-data.md) in its temporary
# folders, and the receipt names they are kept under. 2026-06-24 is the one that matters: on 25 Sep that day had
# left the window, so this copy is the only listing of its 45 matches. The URL is inferred from each file's name.
RESEARCH_DIRS = (
    Path(r"C:\Users\zerom\AppData\Local\Temp\claude\c--Users-zerom-Documents-Tennis-predictions"
         r"\8164789c-86ab-4a3d-ba88-48b4071395c8\scratchpad\tdi_probe\payloads"),
    Path(r"C:\Users\zerom\AppData\Local\Temp\claude\c--Users-zerom-Documents-Tennis-predictions"
         r"\32cd6efa-2a3b-4713-9d9c-7eb5d6088786\scratchpad\A_tour\probes\tdi"),
)
RESEARCH_LISTINGS = {  # file -> (kind, key, URL)
    "list_date_2026_06_24.html": ("date", "2026-06-24", f"{SITE}/en?date=2026-06-24"),
    "list_date_2026_06_23.html": ("date", "2026-06-23", f"{SITE}/en?date=2026-06-23"),
    "home_en.html": ("home", None, f"{SITE}/en"),
    "home_20260518.html": ("date", "2026-05-18", f"{SITE}/en?date=2026-05-18"),
    "home_20260801.html": ("date", "2026-08-01", f"{SITE}/en?date=2026-08-01"),
    "list_playerId_19dcceef_6fcd_465c_849f_4b487fecd1d4.html":
        ("player", "19dcceef-6fcd-465c-849f-4b487fecd1d4", f"{SITE}/en?playerId=19dcceef-6fcd-465c-849f-4b487fecd1d4"),
}


def import_research_listings(receipts) -> dict:
    """Keep the research session's saved listing pages beside this adapter's own, each with a receipt marked
    ``imported`` (source file, its time, SHA-256). A page already imported is left alone."""
    out = Counter()
    for file_name, (kind, key, url) in RESEARCH_LISTINGS.items():
        source = next((d / file_name for d in RESEARCH_DIRS if (d / file_name).exists()), None)
        if source is None:
            out["missing"] += 1
            P.log(f"[{SOURCE}] research listing {file_name} is gone; nothing imported for it")
            continue
        taken = dt.datetime.fromtimestamp(source.stat().st_mtime, dt.timezone.utc)
        label = "research-" + taken.strftime("%Y%m%dT%H%MZ")
        name = f"list/{kind}/{label}" if kind == "home" else f"list/{kind}/{key}@{label}"
        if done(receipts.get(name)):
            out["already imported"] += 1
            continue
        body = source.read_bytes()
        problem = page_validator(body)
        dest = listing_dest(name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        part.write_bytes(gzip.compress(body))
        os.replace(part, dest)
        receipts.record({"name": name, "url": url, "dest": P.rel(dest), "retrieved_at": taken.isoformat(timespec="seconds"),
                         "sweep": label, "kind": kind, "key": key, "status": 200, "error": problem,
                         "bytes": len(body), "sha256": P.sha256_bytes(body), "compressed": True, "imported": True,
                         "imported_from": str(source), "status_note": "not saved with the file; the research "
                         "session reports every request of 24 Sep answered 200 (access-routes-tdi-and-open-data.md)"})
        out["imported"] += 1
        P.log(f"[{SOURCE}] imported {file_name} as {name}")
    return dict(out)


WAYBACK_IDS = P.PROJECT_ROOT / "data" / "studies" / "granular_data_leads" / "tdi_wayback_match_ids.csv"


def match_name(match_id: str) -> str:
    return f"match/{match_id}"


def match_url(match_id: str) -> str:
    return f"{SITE}/en/results/{match_id}"


def match_dest(match_id: str) -> Path:
    return P.raw_path(SOURCE, "matches", match_id[:2], f"{match_id}.html.gz")


def point_ids_in(body: bytes, match_id: str) -> int:
    """How many distinct point ids of this match (<uuid>-<set>-<game>-<point>) the page carries."""
    return len(set(re.findall(re.escape(match_id).encode() + rb"-\d{2}-\d{2}-\d{3}", body)))


def match_saved(receipt: dict | None) -> bool:
    return bool(receipt) and bool(receipt.get("document")) and not receipt.get("error") \
        and match_dest(receipt["match_id"]).exists()


def match_done(receipt: dict | None) -> bool:
    """A match page that needs no fetch: saved (a 200, or a 404 that carries points), or a 404 without points."""
    if not receipt or receipt.get("error"):
        return False
    return bool(receipt.get("absent")) or match_saved(receipt)


def fetch_match(client, receipts, match_id: str, extra: dict | None = None) -> dict:
    """GET one match page. Unlike common.fetch, an HTTP 404 is kept when it carries this match's points (an old
    match outside the window is served that way); a 404 without them is recorded as absent and never asked
    again. A 200 is kept whether or not it has points; any other status is an error, retried by the next run.
    Blocked and BudgetExhausted propagate so the run stops."""
    name, dest = match_name(match_id), match_dest(match_id)
    previous = receipts.get(name)
    if match_done(previous):
        return {**previous, "skipped": True}
    receipt = {"name": name, "url": match_url(match_id), "dest": P.rel(dest), "retrieved_at": P.utc_now_iso(),
               "match_id": match_id, **(extra or {})}
    try:
        response = client.get(receipt["url"])
    except (P.Blocked, P.BudgetExhausted):
        raise
    except Exception as err:
        receipt["error"] = f"{type(err).__name__}: {err}"
        return receipts.record(receipt)
    body = response.content
    receipt.update(status=response.status_code, content_type=response.headers.get("content-type"),
                   final_url=str(response.url))
    if response.status_code not in (200, 404):
        receipt["error"] = f"HTTP {response.status_code}"
        return receipts.record(receipt)
    points = point_ids_in(body, match_id)
    if response.status_code == 404 and not points:
        receipt["absent"] = "HTTP 404 without points"
        return receipts.record(receipt)
    problem = page_validator(body)
    if problem:
        receipt["error"] = problem
        return receipts.record(receipt)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(gzip.compress(body))
    os.replace(part, dest)
    receipt.update(bytes=len(body), sha256=P.sha256_bytes(body), compressed=True, document=True, point_ids=points)
    return receipts.record(receipt)


def match_state(receipt: dict) -> str:
    """"200", "404_with_points", "absent" or "error", with ":cached" for an answer from an earlier run."""
    if receipt.get("error"):
        state = "error"
    elif receipt.get("absent"):
        state = "absent"
    else:
        state = "404_with_points" if receipt.get("status") == 404 else str(receipt.get("status"))
    return state + (":cached" if receipt.get("skipped") else "")


def index_ids() -> list[str]:
    """The id index's matches (staged by the listing sweeps), oldest stamp first."""
    import pyarrow.parquet as pq

    path = P.dump_path(SOURCE, "match_ids.parquet")
    if not path.exists():
        raise SystemExit("no id index yet: run a listing sweep, or --stage-only, first")
    rows = pq.read_table(path, columns=["match_id", "stamp"]).to_pylist()
    return [r["match_id"] for r in sorted(rows, key=lambda r: (r["stamp"] or "", r["match_id"]))]


def wayback_ids() -> list[str]:
    """The match ids the Wayback Machine's captures of the listings preserve (granular_data_leads study)."""
    if not WAYBACK_IDS.exists():
        return []
    with WAYBACK_IDS.open(encoding="utf-8", newline="") as handle:
        ids = [(row.get("tdi_match_id") or "").strip() for row in csv.DictReader(handle)]
    return list(dict.fromkeys(i for i in ids if UUID.match(i)))


def fetch_pages(client, receipts, streak, ids: list[str], source: str, outcomes: Counter, report: dict) -> None:
    """Fetch every page of ``ids`` not yet done, in order, keeping ``report`` current (it survives a stop). A page
    kept from a 404 counts as a document for the failure streak."""
    todo = [m for m in ids if not match_done(receipts.get(match_name(m)))]
    report.update(source=source, ids=len(ids), done_before=len(ids) - len(todo), fetched=0, remaining=len(todo))
    P.log(f"[{SOURCE}] {len(ids)} match ids ({source}); {len(ids) - len(todo)} done before; {len(todo)} to fetch")
    for n, match_id in enumerate(todo, 1):
        receipt = fetch_match(client, receipts, match_id, {"id_source": source})
        if not receipt.get("skipped"):
            report["fetched"] += 1
        if match_done(receipt):
            report["remaining"] -= 1
        outcomes[f"match:{match_state(receipt)}"] += 1
        streak.note({**receipt, "status": 200} if receipt.get("document") else receipt)
        if n % 50 == 0 or n == len(todo):
            P.log(f"[{SOURCE}] {n}/{len(todo)} pages; requests={client.requests}; " +
                  ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items())))


def outcome_key(prefix: str, receipt: dict) -> str:
    state = receipt.get("error") and "error" or receipt.get("absent") and "absent" or receipt.get("status")
    return f"{prefix}:{state}" + (":cached" if receipt.get("skipped") else "")


def describe_page(kind: str, key: str, html: str | None, title: str | None = None) -> str:
    """One log line's worth about a saved listing page."""
    if html is None:
        return "no page saved"
    rows, _ = page_rows(html)
    cards = listing_cards(rows)
    days = Counter(c["stamp_day"] for c in cards)
    span = f"{min(d for d in days if d)}..{max(d for d in days if d)}" if any(days) else "-"
    if kind == "date":
        status = date_listing_status(key, cards)
    elif kind == "tournament":
        status = "/".join(str(x) for x in tournament_listing_status(title, cards))
    else:
        status = "default listing"
    return f"{len(cards)} cards, stamped {span}: {status}"


def sweep_listings(client, receipts, streak, sweep: dict, args, outcomes: Counter) -> dict:
    """The sweep's listings in order: the default listing, the days oldest first, then the tournaments."""
    tag = sweep["sweep"]
    receipt = fetch_listing(client, receipts, home_name(sweep), f"{SITE}/en", {"sweep": tag, "kind": "home"})
    outcomes[outcome_key("home", receipt)] += 1
    streak.note(receipt)
    home = read_page(receipt)
    if home is None:
        raise F.Stopped(f"the default listing of sweep {tag} was not saved ({receipt.get('error') or receipt.get('status')})")
    tournaments = filter_lists(page_rows(home)[0])["tournaments"] or []
    P.log(f"[{SOURCE}] default listing: {describe_page('home', tag, home)}; {len(tournaments)} tournaments in the filter")
    wanted_days = set(args.dates.split(",")) if args.dates else None
    planned = [home_name(sweep)]
    for day in plan_days(sweep):
        name = date_name(day, sweep)
        planned.append(name)
        if wanted_days is not None and day not in wanted_days:
            continue
        receipt = fetch_listing(client, receipts, name, f"{SITE}/en?date={day}",
                                {"sweep": tag, "kind": "date", "key": day, "settled": is_settled(day, sweep)})
        outcomes[outcome_key("date", receipt)] += 1
        streak.note(receipt)
        if not receipt.get("skipped"):
            P.log(f"[{SOURCE}] date {day}: {describe_page('date', day, read_page(receipt))}")
    limit = len(tournaments) if args.tournaments is None else args.tournaments
    if sweep.get("kind", "full") != "full":  # a recent sweep reads the days only
        tournaments = []
    for n, t in enumerate(tournaments):
        name = tournament_name(t["id"], sweep)
        planned.append(name)
        if n >= limit:
            continue
        receipt = fetch_listing(client, receipts, name, f"{SITE}/en?tournamentId={t['id']}",
                                {"sweep": tag, "kind": "tournament", "key": t["id"], "title": t.get("title")})
        outcomes[outcome_key("tournament", receipt)] += 1
        streak.note(receipt)
        if not receipt.get("skipped"):
            P.log(f"[{SOURCE}] tournament {(t.get('title') or '').strip()}: "
                  f"{describe_page('tournament', t['id'], read_page(receipt), t.get('title'))}")
    missing = [name for name in planned if not done(receipts.get(name))]
    if not missing:
        append_sweep_line({"sweep": tag, "event": "finished", "at": P.utc_now_iso(), "listings": len(planned)})
        P.log(f"[{SOURCE}] sweep {tag} finished: {len(planned)} listings")
    else:
        P.log(f"[{SOURCE}] sweep {tag} open: {len(missing)} of {len(planned)} listings still to read; "
              "run the same command again to continue")
    return {"sweep": tag, "planned": len(planned), "missing": len(missing), "finished": not missing,
            "missing_examples": missing[:10]}


# --------------------------------------------------------------------------------------
# staging: the id index and the listing reports
# --------------------------------------------------------------------------------------
def listing_receipts(receipts) -> list[dict]:
    return [r for name, r in sorted(receipts.all().items()) if name.startswith("list/")]


def stage_listings(receipts) -> dict:
    sweeps = {x["sweep"]: x for x in read_sweeps() if x.get("event") == "started"}
    pages, cards, filters = [], [], {"tournaments": {}, "players": {}}
    for receipt in listing_receipts(receipts):
        name = receipt["name"]
        kind = name.split("/")[1]
        key = receipt.get("key") or (receipt.get("sweep") if kind == "home" else None)
        sweep = receipt.get("sweep")
        page = {"name": name, "kind": kind, "key": key, "sweep": sweep, "settled": receipt.get("settled"),
                "url": receipt.get("url"), "status": receipt.get("status"), "absent": receipt.get("absent"),
                "error": receipt.get("error"), "retrieved_at": receipt.get("retrieved_at"),
                "bytes": receipt.get("bytes"), "sha256": receipt.get("sha256"),
                "source_file": P.rel(listing_dest(name))}
        html = read_page(receipt)
        if html is not None:
            rows, bad = page_rows(html)
            found = listing_cards(rows)
            if kind == "date":
                status = date_listing_status(key, found)
            elif kind == "tournament":
                status, matches = tournament_listing_status(receipt.get("title"), found)
                page["title_matches"] = matches
            else:
                status = "player" if kind == "player" else "default"
            if kind == "home":
                lists = filter_lists(rows)
                for group, items in lists.items():
                    for item in items or []:
                        entry = filters[group].setdefault(item.get("id"), {**item, "sweeps": set()})
                        entry["sweeps"].add(sweep)
            page.update(cards=len(found), singles=sum(c["draw_type"] == "singles" for c in found),
                        doubles=sum(c["draw_type"] == "doubles" for c in found),
                        other_cards=sum(c["draw_type"] == "unknown" for c in found),
                        stamp_days=";".join(f"{d}:{n}" for d, n in sorted(Counter(c["stamp_day"] or "" for c in found).items())) or None,
                        listing_status=status, tournament_titles=";".join(sorted({c["tournament"] or "" for c in found})) or None,
                        rsc_chunks_undecoded=bad)
            for c in found:
                cards.append({**c, "found_by": f"{kind}:{key}", "listing_kind": kind, "listing_key": key, "sweep": sweep,
                              "listing_status": status,
                              "stamp_matches_listing_day": (c["stamp_day"] == key) if kind == "date" else None,
                              "retrieved_at": receipt.get("retrieved_at"), "source_file": page["source_file"]})
        pages.append(page)
    ids = id_index(cards, filters["tournaments"])
    out = {}
    tables = (("listing_pages", PAGE_COLUMNS, pages), ("listing_cards", CARD_COLUMNS, cards), ("match_ids", ID_COLUMNS, ids),
              ("filter_tournaments", TOURNAMENT_COLUMNS, filter_rows(filters["tournaments"], "tournament_id")),
              ("filter_players", PLAYER_COLUMNS, filter_rows(filters["players"], "player_id")))
    now = P.utc_now_iso()
    for name, columns, rows in tables:
        dest = P.dump_path(SOURCE, f"{name}.parquet")
        table = [[P.s(r.get(c)) for c in columns] for r in rows]
        stats = P.stage_table(SOURCE, dest, columns, table, source_file=P.rel(P.raw_path(SOURCE, "listings")),
                              retrieved_at=now, extra={"listing_sweeps": ";".join(sorted(sweeps))})
        out[name] = {"rows": stats["rows"], "dest": stats["dest"], "bytes": stats["bytes"]}
        P.log(f"[{SOURCE}] staged {stats['dest']}: {stats['rows']:,} rows")
    out["reports"] = listing_reports(pages, cards, ids, filters["tournaments"])
    return out


def filter_rows(items: dict, id_column: str) -> list[dict]:
    out = []
    for item_id, item in sorted(items.items()):
        sweeps = sorted(s for s in item.pop("sweeps") if s)
        out.append({id_column: item_id, **{k: v for k, v in item.items() if k != "id"},
                    "first_sweep": sweeps[0] if sweeps else None, "last_sweep": sweeps[-1] if sweeps else None,
                    "sweeps": len(sweeps)})
        item["sweeps"] = set(sweeps)
    return out


def id_index(cards: list[dict], tournaments: dict) -> list[dict]:
    """One row per match id: its listing day (from an in-window date listing whose day equals its stamp), the
    tournament id (from a tournament listing), the players, and every listing it was found in."""
    by_id = defaultdict(list)
    for c in cards:
        by_id[c["match_id"]].append(c)
    out = []
    for match_id, seen in sorted(by_id.items()):
        dated = [c for c in seen if c["listing_kind"] == "date" and c["stamp_matches_listing_day"]]
        tours = sorted({c["listing_key"] for c in seen if c["listing_kind"] == "tournament"})
        first = seen[0]
        conflicts = []
        for field in ("stamp", "round", "tournament", "team1_player_ids", "team2_player_ids"):
            values = {c[field] for c in seen if c[field] is not None}
            if len(values) > 1:
                conflicts.append(f"{field}:{'|'.join(sorted(values))}")
        if len(tours) > 1:
            conflicts.append(f"tournament_id:{'|'.join(tours)}")
        stamps = sorted(c["retrieved_at"] or "" for c in seen)
        out.append({
            "match_id": match_id, "listing_day": dated[0]["listing_key"] if dated else None,
            "stamp": first["stamp"], "stamp_day": first["stamp_day"], "round": first["round"],
            "tournament": first["tournament"], "tournament_id": tours[0] if len(tours) == 1 else (";".join(tours) or None),
            "tournament_title": (tournaments.get(tours[0]) or {}).get("title", "").strip() or None if len(tours) == 1 else None,
            "draw_type": first["draw_type"], "team1_player_ids": first["team1_player_ids"], "team1_names": first["team1_names"],
            "team2_player_ids": first["team2_player_ids"], "team2_names": first["team2_names"],
            "found_by": ";".join(sorted({c["found_by"] for c in seen})), "sightings": len(seen),
            "in_date_listing": bool(dated), "in_tournament_listing": bool(tours),
            "in_home_listing": any(c["listing_kind"] == "home" for c in seen),
            "first_seen": stamps[0] or None, "last_seen": stamps[-1] or None, "conflicts": "; ".join(conflicts) or None,
        })
    return out


def listing_reports(pages: list[dict], cards: list[dict], ids: list[dict], tournaments: dict) -> dict:
    """Counts per day and per tournament, and where the date and tournament listings disagree."""
    by_id = {r["match_id"]: r for r in ids}
    date_pages = [p for p in pages if p["kind"] == "date"]
    in_window_days = sorted({p["key"] for p in date_pages if p.get("listing_status") in ("in_window", "mixed")})
    stamped, stamped_in_tournaments = defaultdict(set), defaultdict(set)  # day -> ids stamped that day
    for c in cards:
        if c["stamp_day"]:
            stamped[c["stamp_day"]].add(c["match_id"])
            if c["listing_kind"] == "tournament":
                stamped_in_tournaments[c["stamp_day"]].add(c["match_id"])
    day_rows = []
    for p in sorted(date_pages, key=lambda p: (p["key"], p["name"])):
        on_page = [c for c in cards if c["source_file"] == p["source_file"]]
        in_window = p.get("listing_status") in ("in_window", "mixed")
        day_rows.append({
            "day": p["key"], "name": p["name"], "settled": p["settled"], "retrieved_at": p["retrieved_at"],
            "listing_status": p.get("listing_status"), "cards": p.get("cards"), "singles": p.get("singles"),
            "doubles": p.get("doubles"), "stamp_days": p.get("stamp_days"),
            "also_in_tournament_listing": sum(1 for c in on_page if by_id[c["match_id"]]["in_tournament_listing"]),
            "in_no_tournament_listing": sum(1 for c in on_page if not by_id[c["match_id"]]["in_tournament_listing"]),
            # completeness: every id stamped this day in any listing, against this page
            "stamped_this_day_in_any_listing": len(stamped[p["key"]]) if in_window else None,
            "stamped_this_day_in_tournament_listings": len(stamped_in_tournaments[p["key"]]) if in_window else None,
            "stamped_this_day_not_on_this_page": len(stamped[p["key"]] - {c["match_id"] for c in on_page}) if in_window else None,
        })
    tour_rows = []
    for p in sorted((p for p in pages if p["kind"] == "tournament"), key=lambda p: p["name"]):
        on_page = [c for c in cards if c["source_file"] == p["source_file"]]
        info = tournaments.get(p["key"]) or {}
        days = sorted(c["stamp_day"] for c in on_page if c["stamp_day"])
        tour_rows.append({
            "tournament_id": p["key"], "title": (info.get("title") or "").strip(), "city": info.get("city"),
            "sweep": p["sweep"], "listing_status": p.get("listing_status"), "title_matches": p.get("title_matches"),
            "card_titles": p.get("tournament_titles"), "cards": p.get("cards"), "singles": p.get("singles"),
            "doubles": p.get("doubles"), "first_day": days[0] if days else None, "last_day": days[-1] if days else None,
            "also_in_date_listing": sum(1 for c in on_page if by_id[c["match_id"]]["in_date_listing"]),
            "in_no_date_listing": sum(1 for c in on_page if not by_id[c["match_id"]]["in_date_listing"]),
        })
    for name, rows in (("tdi_listing_days.csv", day_rows), ("tdi_listing_tournaments.csv", tour_rows)):
        path = F.STUDY_ROOT / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["empty"])
            writer.writeheader()
            writer.writerows(rows)
    only_date = [r for r in ids if r["in_date_listing"] and not r["in_tournament_listing"]]
    only_tour = [r for r in ids if r["in_tournament_listing"] and not r["in_date_listing"]]

    def why(r):  # where a one-sided id sits: a day outside the dates read in the window, or inside it
        return "outside_days_read" if r["stamp_day"] not in in_window_days else "inside_days_read"

    status = Counter(p.get("listing_status") for p in date_pages)
    return {
        "date_listings": dict(sorted(status.items(), key=lambda kv: str(kv[0]))),
        "in_window_days": {"count": len(in_window_days), "first": in_window_days[0] if in_window_days else None,
                           "last": in_window_days[-1] if in_window_days else None},
        "cards_off_their_listing_day": sum(1 for c in cards if c["listing_kind"] == "date" and c["listing_status"] == "mixed"
                                           and not c["stamp_matches_listing_day"]),
        "most_cards_on_a_date_listing": max((p.get("cards") or 0 for p in date_pages
                                             if p.get("listing_status") in ("in_window", "mixed")), default=0),
        "in_window_pages_missing_ids_stamped_that_day": {r["name"]: r["stamped_this_day_not_on_this_page"] for r in day_rows
                                                          if r["stamped_this_day_not_on_this_page"]},
        "match_ids": len(ids),
        "match_ids_by_draw_type": dict(Counter(r["draw_type"] for r in ids)),
        "match_ids_in_date_listings": sum(r["in_date_listing"] for r in ids),
        "match_ids_in_tournament_listings": sum(r["in_tournament_listing"] for r in ids),
        "only_in_date_listings": dict(Counter(why(r) for r in only_date)),
        "only_in_tournament_listings": dict(Counter(why(r) for r in only_tour)),
        "only_in_date_listings_examples": [r["match_id"] for r in only_date[:10]],
        "only_in_tournament_listings_examples": [(r["match_id"], r["stamp_day"]) for r in only_tour[:10]],
        "ids_with_conflicts": sum(1 for r in ids if r["conflicts"]),
        "tournament_listings": dict(Counter(f"{r['listing_status']}|title_matches={r['title_matches']}" for r in tour_rows)),
        "files": ["data/studies/official_point_feeds/tdi_listing_days.csv",
                  "data/studies/official_point_feeds/tdi_listing_tournaments.csv"],
    }


# --------------------------------------------------------------------------------------
# staging: the match pages
# --------------------------------------------------------------------------------------
TOUR_LEVELS = {"A", "M", "F", "G", "D", "O"}
MATCH_COLUMNS = [
    "match_id", "in_index", "in_wayback_list", "id_source", "record", "record_reason", "http_status", "retrieved_at",
    "bytes", "sha256", "title", "teams_text", "atp_code", "atp_year", "atp_tournament_id", "atp_match_code",
    "event_code", "draw_type", "draw", "description", "description_event", "description_place", "description_score",
    "h1", "completed_on", "venue", "tournament", "place", "level", "level_source", "sackmann_level",
    "sackmann_name", "players_in_header",
    "team_a_player_ids", "team_a_atp_ids", "team_a_names", "team_a_short_names", "team_a_countries", "team_a_entry",
    "team_a_scores",
    "team_b_player_ids", "team_b_atp_ids", "team_b_names", "team_b_short_names", "team_b_countries", "team_b_entry",
    "team_b_scores",
    "point_team_a_name", "point_team_b_name", "points", "points_with_outcome", "points_with_completed_utc",
    "first_point_time", "last_point_time", "point_id_mismatches", "points_extra_keys", "stats_periods", "stats_rows",
    "listing_day", "stamp", "round", "listing_tournament", "tournament_id", "listing_draw_type", "found_by",
    "rsc_chunks_undecoded", "source_file",
]
POINT_COLUMNS = [
    "match_id", "point_id", "id_match", "id_set", "id_game", "id_point", "set", "game", "point", "point_sequence",
    "time", "completed_utc", "winner", "team_serving", "player_serving", "player_receiving", "serving",
    "team_a_game_score", "team_b_game_score", "team_a_sets", "team_b_sets", "team_a_games_won", "team_b_games_won",
    "ace", "is_break_point", "is_break_save", "is_deuce", "game_point", "set_point", "game_won", "set_won",
    "complete", "streak_owner", "streak_count", "outcome", "serve", "total_shots", "winning_shot_type",
    "error_type", "situation", "rally", "rally_events", "faults", "lets", "extra", "source_file", "retrieved_at",
]
STAT_COLUMNS = ["match_id", "period", "order", "category", "label", "team_a", "team_b", "source_file", "retrieved_at"]
PAGE_PLAYER_COLUMNS = ["player_id", "atp_id", "atp_ids_seen", "full_name", "short_name", "country", "matches",
                       "first_completed_on", "last_completed_on", "filter_full_name"]


def sackmann_levels() -> dict[int, tuple]:
    """ATP tournament id -> (level, name, year) in Jeff Sackmann's archive (tour-level and qual_chall files, 2018
    on), from the latest year that has the id: A, M, F, G, D or O for tour-level events, C for Challengers. The
    archive's 2026 files end with May, so a later event's level is its id's level in an earlier edition."""
    import pyarrow.parquet as pq

    base = P.PROJECT_ROOT / "data" / "dump" / "matches" / "sackmann_archive" / "atp"
    files = []
    for path in base.glob("atp_matches_*.parquet"):
        m = re.match(r"^atp_matches_(?:qual_chall_)?(\d{4})\.parquet$", path.name)
        if m and int(m.group(1)) >= 2018:
            files.append((int(m.group(1)), path.name, path))
    out = {}
    for year, _, path in sorted(files):
        for r in pq.read_table(path, columns=["tourney_id", "tourney_name", "tourney_level"]).to_pylist():
            tail = (r["tourney_id"] or "").split("-")[-1]
            if tail.isdigit():
                out[int(tail)] = (r["tourney_level"], r["tourney_name"], year)
    return out


def match_level(tournament_id, names: list, levels: dict) -> dict:
    """Tour or Challenger: the level of the ATP tournament id in Sackmann's archive (``level_source`` names the
    edition's year), else "challenger" when a name of the tournament says so, else "unknown"."""
    found = levels.get(int(tournament_id)) if str(tournament_id or "").isdigit() else None
    out = {"sackmann_level": found[0] if found else None, "sackmann_name": found[1] if found else None}
    source = f"sackmann_{found[2]}" if found and len(found) > 2 else "sackmann"
    if found and found[0] == "C":
        return {**out, "level": "challenger", "level_source": source}
    if found and found[0] in TOUR_LEVELS:
        return {**out, "level": "tour", "level_source": source}
    if any("challenger" in (n or "").casefold() for n in names):
        return {**out, "level": "challenger", "level_source": "name"}
    return {**out, "level": "unknown", "level_source": None}


def read_table(name: str) -> list[dict]:
    import pyarrow.parquet as pq

    path = P.dump_path(SOURCE, f"{name}.parquet")
    return pq.read_table(path).to_pylist() if path.exists() else []


def stage_matches(receipts) -> dict:
    """matches, points, statistics and players from every saved match page, with every id of the index and of
    the Wayback list accounted for (fetched or not). Points are streamed to Parquet page by page."""
    listed = {r["match_id"]: r for r in read_table("match_ids")}
    filter_names = {r["player_id"]: r.get("full_name") for r in read_table("filter_players")}
    wayback = set(wayback_ids())
    fetched = {r["match_id"]: r for name, r in receipts.all().items() if name.startswith("match/") and r.get("match_id")}
    all_ids = sorted(set(listed) | wayback | set(fetched))
    levels = sackmann_levels()
    match_rows, stat_rows, players = [], [], {}

    def point_stream():
        for match_id in all_ids:
            receipt, entry = fetched.get(match_id), listed.get(match_id) or {}
            row = {"match_id": match_id, "in_index": match_id in listed, "in_wayback_list": match_id in wayback,
                   "listing_day": entry.get("listing_day"), "stamp": entry.get("stamp"), "round": entry.get("round"),
                   "listing_tournament": entry.get("tournament"), "tournament_id": entry.get("tournament_id"),
                   "listing_draw_type": entry.get("draw_type"), "found_by": entry.get("found_by")}
            match_rows.append(row)
            if receipt is None:
                row["record"] = "not fetched"
                continue
            row.update(id_source=receipt.get("id_source"), http_status=receipt.get("status"),
                       retrieved_at=receipt.get("retrieved_at"), bytes=receipt.get("bytes"), sha256=receipt.get("sha256"))
            path = match_dest(match_id)
            if receipt.get("error") or receipt.get("absent") or not path.exists():
                row.update(record="error" if receipt.get("error") or not receipt.get("absent") else "absent",
                           record_reason=receipt.get("error") or receipt.get("absent") or "the saved page is missing")
                continue
            try:
                parsed = parse_match_page(P.read_bytes(path).decode("utf-8"), match_id)
            except Exception as err:  # kept on disk and reported; never fetched again
                row.update(record="unreadable", record_reason=f"{type(err).__name__}: {err}")
                continue
            m, pts = parsed["match"], parsed["points"]
            times = sorted(p["time"] for p in pts if p["time"])
            row.update(m)
            row.update(match_level(m["atp_tournament_id"], [m["tournament"], entry.get("tournament")], levels))
            row.update(record="points" if pts else "no points", record_reason=None if pts else "the page carries no point",
                       points=len(pts), points_with_outcome=sum(1 for p in pts if p["outcome"]),
                       points_with_completed_utc=sum(1 for p in pts if p["completed_utc"]),
                       first_point_time=times[0] if times else None, last_point_time=times[-1] if times else None,
                       point_id_mismatches=sum(1 for p in pts if p["id_match"] != match_id),
                       points_extra_keys=";".join(sorted({k for p in pts for k in (p["extra"] or {})})) or None,
                       stats_periods=";".join(dict.fromkeys(s["period"] for s in parsed["statistics"])) or None,
                       stats_rows=len(parsed["statistics"]), source_file=P.rel(path))
            prov = {"match_id": match_id, "source_file": P.rel(path), "retrieved_at": receipt.get("retrieved_at")}
            stat_rows.extend({**s, **prov} for s in parsed["statistics"])
            for p in parsed["players"]:
                seen = players.setdefault(p["player_id"], {"player_id": p["player_id"], "atp_ids": Counter(), "matches": 0,
                                                             "dates": []})
                seen["matches"] += 1
                seen["atp_ids"][p.get("atp_id")] += 1
                for field in ("full_name", "short_name", "country"):
                    seen.setdefault(field, p.get(field))
                if m["completed_on"]:
                    seen["dates"].append(m["completed_on"])
            for p in pts:
                values = {**p, **prov}
                yield [P.s(values.get(c)) for c in POINT_COLUMNS]

    now = P.utc_now_iso()
    out = {}

    def stage(name, columns, rows):
        stats = P.stage_table(SOURCE, P.dump_path(SOURCE, f"{name}.parquet"), columns, rows,
                              source_file=P.rel(P.raw_path(SOURCE, "matches")), retrieved_at=now)
        out[name] = {"rows": stats["rows"], "dest": stats["dest"], "bytes": stats["bytes"]}
        P.log(f"[{SOURCE}] staged {stats['dest']}: {stats['rows']:,} rows")

    stage("points", POINT_COLUMNS, point_stream())
    stage("matches", MATCH_COLUMNS, ([P.s(r.get(c)) for c in MATCH_COLUMNS] for r in match_rows))
    stage("statistics", STAT_COLUMNS, ([P.s(r.get(c)) for c in STAT_COLUMNS] for r in stat_rows))
    player_rows = []
    for pid, p in sorted(players.items()):
        atp_ids = [a for a, _ in p["atp_ids"].most_common() if a]
        dates = sorted(p["dates"])
        player_rows.append({"player_id": pid, "atp_id": atp_ids[0] if atp_ids else None,
                            "atp_ids_seen": ";".join(atp_ids) or None, "full_name": p.get("full_name"),
                            "short_name": p.get("short_name"), "country": p.get("country"), "matches": p["matches"],
                            "first_completed_on": dates[0] if dates else None, "last_completed_on": dates[-1] if dates else None,
                            "filter_full_name": filter_names.get(pid)})
    stage("players", PAGE_PLAYER_COLUMNS, ([P.s(r.get(c)) for c in PAGE_PLAYER_COLUMNS] for r in player_rows))
    out["pages"] = pages_summary(match_rows)
    return out


def pages_summary(rows: list[dict]) -> dict:
    """Counts of the staged match pages: records, answers, level, draw and month, and outcome fill."""
    docs = [r for r in rows if r.get("record") in ("points", "no points")]
    month = lambda r: (r.get("completed_on") or r.get("stamp") or "")[:7] or "?"  # noqa: E731
    fill = defaultdict(lambda: [0, 0])
    for r in docs:
        cell = fill[f"{r.get('level')}|{month(r)}"]
        cell[0] += int(r.get("points_with_outcome") or 0)
        cell[1] += int(r.get("points") or 0)
    return {
        "records": dict(Counter(r.get("record") for r in rows)),
        "records_by_id_list": dict(Counter(f"{'index' if r['in_index'] else ''}{'+' if r['in_index'] and r['in_wayback_list'] else ''}"
                                           f"{'wayback' if r['in_wayback_list'] else ''}|{r.get('record')}" for r in rows)),
        "documents_by_http_status": dict(Counter(str(r.get("http_status")) for r in docs)),
        "documents_by_level_draw": dict(sorted(Counter(f"{r.get('level')}|{r.get('draw_type')}|{r.get('draw')}" for r in docs).items())),
        "documents_by_month": dict(sorted(Counter(month(r) for r in docs).items())),
        "level_sources": dict(Counter(str(r.get("level_source")) for r in docs)),
        "unknown_level_tournaments": dict(Counter(r.get("tournament") for r in docs if r.get("level") == "unknown").most_common(20)),
        "points": sum(int(r.get("points") or 0) for r in docs),
        "outcome_fill_by_level_month": {k: round(v[0] / v[1], 3) if v[1] else None for k, v in sorted(fill.items())},
        "point_id_mismatches": sum(int(r.get("point_id_mismatches") or 0) for r in docs),
        "points_extra_keys": dict(Counter(r.get("points_extra_keys") for r in docs if r.get("points_extra_keys"))),
        "without_atp_code": sum(1 for r in docs if not r.get("atp_code")),
        "players_in_header": dict(Counter(str(r.get("players_in_header")) for r in docs)),
    }


def stage_all(receipts) -> dict:
    out = stage_listings(receipts)
    out.update(stage_matches(receipts))
    return out


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "started_at": P.utc_now_iso(), "args": vars(args), "decision": DECISION}
    outcomes = Counter()
    client = None
    try:
        if args.import_research:
            with run_lock():
                summary["imported"] = import_research_listings(receipts)
        elif not args.stage_only:
            if not args.max_requests:
                raise SystemExit("--max-requests is required for a run that fetches (the decision's budget rule)")
            with run_lock():
                client = F.FeedClient(IMPERSONATE, min_interval=args.min_interval, jitter=args.jitter,
                                      max_requests=args.max_requests)
                streak = F.FailureStreak(args.stop_after_failures)
                pages = bool(args.pages or args.wayback_ids or args.ids)
                try:
                    if pages:
                        ids, source = page_ids(args)
                        summary["matches_selected"] = len(ids)
                        summary["pages"] = {}
                        fetch_pages(client, receipts, streak, ids, source, outcomes, summary["pages"])
                    else:
                        sweep = open_sweep(args)
                        summary["sweep"] = sweep
                        summary["listings"] = sweep_listings(client, receipts, streak, sweep, args, outcomes)
                        if args.recent:  # forward capture: the new days' ids into the index, then their pages
                            stage_listings(receipts)
                            ids = index_ids()
                            summary["matches_selected"] = len(ids)
                            summary["pages"] = {}
                            fetch_pages(client, receipts, streak, ids, "index", outcomes, summary["pages"])
                except P.BudgetExhausted as stop:  # the batch's end, not a fault: the next run carries on
                    summary["budget_used_up"] = str(stop)
                    P.log(f"[{SOURCE}] budget used up; run again to continue")
                except (P.Blocked, F.Stopped) as stop:
                    summary["stopped"] = f"{type(stop).__name__}: {stop}"
                    P.log(f"[{SOURCE}] STOPPED: {stop}")
                    P.log(f"[{SOURCE}] nothing is lost: the next run asks only for what is not saved")
    finally:
        summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
        if client is not None:
            summary["client"] = client.stats()
    if not args.no_stage:
        try:
            summary["staged"] = stage_all(receipts)
        except Exception as err:  # the fetches are saved whatever staging does
            summary["staging_failed"] = f"{type(err).__name__}: {err}"
            summary["stopped"] = summary.get("stopped") or f"staging failed: {type(err).__name__}: {err}"
            P.log(f"[{SOURCE}] STAGING FAILED ({type(err).__name__}: {err}); the fetched pages are kept; "
                  "fix and rerun with --stage-only")
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts"] = dict(sorted(Counter(
        f"{'match' if r['name'].startswith('match/') else '/'.join(r['name'].split('/')[:2])}:"
        f"{match_state(r) if r['name'].startswith('match/') else r.get('error') and 'error' or r.get('absent') and 'absent' or r.get('status')}"
        for r in receipts.all().values()).items()))
    summary["receipts_with_errors"] = len(errors)
    summary["receipts_unreadable_lines"] = receipts.unreadable_lines
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = F.write_summary("tdi_summary.json", summary)
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def page_ids(args) -> tuple[list[str], str]:
    """The match ids a page run works through: --ids, else the index's (--pages) and the Wayback list's
    (--wayback-ids), in that order, each once."""
    if args.ids:
        return [i.strip() for i in args.ids.split(",") if UUID.match(i.strip())], "ids"
    ids, sources = [], []
    if args.pages:
        ids += index_ids()
        sources.append("index")
    if args.wayback_ids:
        ids += wayback_ids()
        sources.append("wayback")
    return list(dict.fromkeys(ids)), "+".join(sources)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-requests", type=int, help="stop after this many HTTP requests (required to fetch)")
    parser.add_argument("--pages", action="store_true", help="fetch the match pages of the id index not yet saved")
    parser.add_argument("--wayback-ids", action="store_true",
                        help="fetch the match pages of the Wayback Machine's ids (tdi_wayback_match_ids.csv)")
    parser.add_argument("--ids", help="comma list of match ids whose pages to fetch (pilots)")
    parser.add_argument("--recent", type=int, metavar="N",
                        help="forward capture: a sweep of the default listing and the last N days (no tournament "
                             "listings), then the pages of every indexed match not yet saved")
    parser.add_argument("--dates", help="comma list of days: read only these of the sweep's days this run (pilots)")
    parser.add_argument("--tournaments", type=int, help="read only the first N tournament listings this run (pilots)")
    parser.add_argument("--sweep", help="work on this sweep (default: resume the latest unfinished one, else start one)")
    parser.add_argument("--new-sweep", action="store_true", help="start a new sweep even if one is unfinished")
    parser.add_argument("--days-back", type=int, default=DAYS_BACK, help="a new sweep's first day, counted back from today")
    parser.add_argument("--settle-days", type=int, default=SETTLE_DAYS,
                        help="a day more than this many days before the sweep's last day is read once, ever")
    parser.add_argument("--min-interval", type=float, default=2.0, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=1.0, help="up to this many extra seconds, drawn at random")
    parser.add_argument("--stop-after-failures", type=int, default=5,
                        help="stop after this many fetches in a row without a document (0: never)")
    parser.add_argument("--import-research", action="store_true",
                        help="no HTTP; keep the research session's saved listing pages of 24 Sep (RESEARCH_LISTINGS)")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rebuild the tables and reports")
    parser.add_argument("--no-stage", action="store_true", help="fetch only; skip the table rebuild")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    return 1 if summary.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())

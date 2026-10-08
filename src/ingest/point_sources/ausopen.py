"""Australian Open 2026 match centre: the six events' draws, then every match's point commentary and set statistics.

Endpoints (public JSON on Tennis Australia's scores API, an AWS API Gateway; no key):
    https://prod-scores-api.ausopen.com/event/<nid>/draws        one event's draw with every match id
    https://prod-scores-api.ausopen.com/match-centre/<MID>       one match (no year in the id; the current edition)
    https://web.archive.org/cdx/search/cdx?url=prod-scores-api.ausopen.com/match-centre/...
                                                                 --wayback: the Wayback Machine's captures of match
                                                                 centres, fetched as .../web/<timestamp>id_/<url>
    https://web.archive.org/cdx/search/cdx?url=prod-scores-api.ausopen.com/event/...
                                                                 --wayback-draws: its copies of earlier editions'
                                                                 draws (every match and score, no points)

The API serves only the current edition (2026 on 24 Sep 2026; 2022-2025 already answer "No Results" or
"match id not found"), so 2026 will probably vanish when the 2027 draws are made in January 2027. An unknown
path is answered with HTTP 403 {"message": "Missing Authentication Token"}, which is API Gateway's "no such
route"; it is recorded as an absent document, while any other 403 stops the run (feeds.FeedClient).
Collected under the owner's decision of 24 Sep 2026 (docs/decisions/2026-09-24-official-point-feeds.md).

Raw layout under data/raw/point_sources/ausopen/:
    draws/<event>_<nid>.json            the six draws (MS, WS, MQ, WQ, MD, WD)
    match-centre/<MID>.json             every match of the draws, verbatim
    wayback/cdx.json                    the capture list; wayback/<timestamp>_<MID>.json one capture per content digest
    wayback_draws/                      the draws' capture list and <timestamp>_<event nid>.json, one per content
    _receipts.jsonl                     one line per fetch (URL, time, status, bytes, SHA-256)

Staged (data/dump/points/ausopen/), all strings: matches.parquet (every match of the draws, plus one row per
Wayback capture), points.parquet (one row per point, with the parsed outcome, stroke side and server),
set_statistics.parquet (every statistic of every set and of the match, one row per statistic),
archived_draws.parquet (every match of each earlier edition's archived draw, from the event's most complete copy,
linked to the match's Wayback captures with points).
Summary: data/studies/official_point_feeds/ausopen_summary.json.

Record shape (observed 24 Sep 2026): ``commentary`` lists entries newest first; an entry's id is
<MID>-<set>-<game>-<point>, zero-padded. Point 000 of each game is a "serve" entry naming the server ("F. Martin
is serving game 13", no timestamp); every other entry is one point, typed "point", or "game", "set" or "match"
for the point that ended one, with ``winner`` (1 = first team, 2 = second), a Unix ``timestamp``, the elapsed
``duration`` and the point ``score`` after it, written server first ("15 - 40", "AD - 40", tiebreak "1 - 3",
"Game"). The text names who hit the last shot: "<name> wins the point with a Forehand Winner", "<name> loses
the point with a Backhand Forced Error", an Ace, a Double Fault or a Service Winner, occasionally no detail.
``stats`` holds key, serve and rally statistics per set and for the match ("All"); teamA is the first team.

Usage:
    ./python.sh -m src.ingest.point_sources.ausopen                          # draws and all 604 matches
    ./python.sh -m src.ingest.point_sources.ausopen --matches MS701,WQ101 --max-requests 8
    ./python.sh -m src.ingest.point_sources.ausopen --wayback                # also the 2022-2025 captures
    ./python.sh -m src.ingest.point_sources.ausopen --wayback-draws          # and the archived draws of 2019-2025
    ./python.sh -m src.ingest.point_sources.ausopen --stage-only             # rebuild Parquet from the raw files
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import feeds as F

SOURCE = "ausopen"
API = "https://prod-scores-api.ausopen.com"
IMPERSONATE = "chrome"
HEADERS = {"Accept": "application/json"}
YEAR = 2026
# 2026 event ids (lane B notes, 24 Sep 2026) and the matches each draw should hold
EVENTS = {"MS": 257391, "WS": 257400, "MQ": 257390, "WQ": 257399, "MD": 257388, "WD": 257397}
EXPECTED_MATCHES = {"MS": 127, "WS": 127, "MQ": 112, "WQ": 112, "MD": 63, "WD": 63}
WAYBACK = "https://web.archive.org"
WAYBACK_CDX = (f"{WAYBACK}/cdx/search/cdx?url=prod-scores-api.ausopen.com/match-centre/&matchType=prefix"
               "&fl=timestamp,original,statuscode,mimetype,length,digest&filter=statuscode:200&output=json&limit=20000")
WAYBACK_DRAWS_CDX = (f"{WAYBACK}/cdx/search/cdx?url=prod-scores-api.ausopen.com/event/&matchType=prefix"
                     "&fl=timestamp,original,statuscode,mimetype,length,digest&filter=statuscode:200"
                     "&filter=original:.*/draws$&output=json&limit=20000")
DRAW_URL = re.compile(r"/event/(?P<nid>\d+)/draws$")
FINISHED = {"CMP", "RET", "W/O"}

ENTRY_ID = re.compile(r"^(?P<match>.+)-(?P<set>\d+)-(?P<game>\d+)-(?P<point>\d+)$")
POINT_TEXT = re.compile(r"^(?P<subject>.+?) (?P<verb>wins|win|loses|lose) the point(?: with (?:an|a) (?P<detail>.+?))?\.?$")
SERVE_TEXT = re.compile(r"^(?P<server>.+?) is serving game (?P<game>\d+)$")
# detail -> (outcome, stroke side, the verb it goes with); the subject of the sentence hit the shot described
OUTCOMES = {
    "Ace": ("ace", None, "win"),
    "Service Winner": ("service_winner", None, "win"),
    "Forehand Winner": ("winner", "forehand", "win"),
    "Backhand Winner": ("winner", "backhand", "win"),
    "Double Fault": ("double_fault", None, "lose"),
    "Forehand Forced Error": ("forced_error", "forehand", "lose"),
    "Backhand Forced Error": ("forced_error", "backhand", "lose"),
    "Forehand Unforced Error": ("unforced_error", "forehand", "lose"),
    "Backhand Unforced Error": ("unforced_error", "backhand", "lose"),
}
POINT_TYPES = {"point", "game", "set", "match"}
REGULAR_POINTS = {"0", "15", "30", "40", "AD"}

MATCH_COLUMNS = [
    "record_key", "route", "year", "event", "event_name", "event_nid", "scoring_format", "match_id", "match_uuid",
    "round_name", "date", "actual_start_time", "duration", "court_id", "court_name", "session",
    "match_status", "match_status_name", "match_state", "winner_team",
    "team1_id", "team1_names", "team1_player_ids", "team1_tour_ids", "team1_seed", "team1_entry_status", "team1_score",
    "team2_id", "team2_names", "team2_player_ids", "team2_tour_ids", "team2_seed", "team2_entry_status", "team2_score",
    "record", "record_reason", "fetch_status", "commentary_entries", "serve_entries", "points", "sets_with_points",
    "first_point_utc", "last_point_utc", "stats_sets", "stats_rows", "unexpected_entry_types",
    "capture_timestamp", "capture_url", "draw_file", "source_file", "source_sha256", "retrieved_at",
]
POINT_COLUMNS = [
    "record_key", "route", "year", "event", "match_id", "seq", "entry_id", "set", "game", "point", "tiebreak", "type",
    "timestamp", "utc", "duration", "winner", "score", "games_score", "is_game_complete", "commentary",
    "subject", "verb", "subject_role", "subject_team", "subject_name_team", "detail", "outcome", "stroke_side",
    "mapped", "verb_agrees", "game_server_name", "game_server_team", "game_server_player_id", "point_server_team",
    "source_file", "source_sha256", "retrieved_at",
]
STAT_COLUMNS = [
    "record_key", "route", "year", "event", "match_id", "group", "block", "set", "stat",
    "team1_primary", "team1_secondary", "team1_subscript", "team1_is_leading",
    "team2_primary", "team2_secondary", "team2_subscript", "team2_is_leading",
    "source_file", "source_sha256", "retrieved_at",
]
ARCHIVED_DRAW_COLUMNS = [
    "year", "event", "event_name", "event_nid", "match_id", "match_uuid", "round_name", "date",
    # the match's clock and court where a capture has them (the match-timing rule, docs/decisions/2026-10-05-...)
    "actual_start_time", "duration", "court_id", "court_name", "session", "match_status",
    "match_status_name", "winner_team", "team1_names", "team1_tour_ids", "team1_seed", "team1_score",
    "team2_names", "team2_tour_ids", "team2_seed", "team2_score",
    "points_capture", "points_capture_status", "points_captures", "draw_capture", "draw_captures_of_event",
    "draw_matches_finished", "source_file", "source_sha256", "retrieved_at",
]


def gateway_not_found(response) -> str | None:
    """API Gateway's answer for a path it has no route for (HTTP 403 "Missing Authentication Token"), else None."""
    if response.status_code != 403:
        return None
    if (response.headers.get("x-amzn-errortype") or "").startswith("MissingAuthenticationToken"):
        return "API Gateway: Missing Authentication Token (no such route)"
    try:
        message = json.loads(response.content[:4096]).get("message")
    except Exception:
        return None
    return "API Gateway: Missing Authentication Token (no such route)" if message == "Missing Authentication Token" else None


WAYBACK_CAPTURE = re.compile(r"^(?:https?://web\.archive\.org)?/web/(?P<timestamp>\d{14})id_/(?P<original>.+)$")


def wayback_moved(response) -> str | None:
    """The Wayback Machine's answer when it does not play a listed capture back: a redirect to another capture of the
    same URL (observed 24 Sep 2026 for MS403 of 14 Feb 2021). Recorded as an absence and not followed; any other
    redirect still stops the run. The target, when it is a listed capture, is fetched on its own turn."""
    if not 300 <= response.status_code < 400:
        return None
    target = WAYBACK_CAPTURE.match(response.headers.get("location") or "")
    asked = WAYBACK_CAPTURE.match(str(response.url or ""))
    if not target or not asked or target.group("original") != asked.group("original"):
        return None
    return f"Wayback redirects this capture to capture {target.group('timestamp')} (not followed)"


def draw_dest(event: str) -> Path:
    return P.raw_path(SOURCE, "draws", f"{event}_{EVENTS[event]}.json")


def match_dest(match_id: str) -> Path:
    return P.raw_path(SOURCE, "match-centre", f"{match_id}.json")


def wayback_dest(timestamp: str, match_id: str) -> Path:
    return P.raw_path(SOURCE, "wayback", f"{timestamp}_{re.sub(r'[^A-Za-z0-9]+', '_', match_id)}.json")


def draw_capture_dest(timestamp: str, nid: str) -> Path:
    return P.raw_path(SOURCE, "wayback_draws", f"{timestamp}_{nid}.json")


# --------------------------------------------------------------------------------------
# parsing (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def parse_commentary(text: str | None) -> dict:
    """What one commentary sentence says: a serve line, a described point, or neither (unmapped)."""
    text = (text or "").strip()
    serve = SERVE_TEXT.match(text)
    if serve:
        return {"kind": "serve", "server": serve.group("server"), "serve_game": int(serve.group("game"))}
    point = POINT_TEXT.match(text)
    if not point:
        return {"kind": "unmapped", "mapped": False, "outcome": "unmapped"}
    verb = point.group("verb")
    role = "winner" if verb.startswith("win") else "loser"
    detail = point.group("detail")
    out = {"kind": "point", "subject": point.group("subject"), "verb": verb, "subject_role": role, "detail": detail}
    if detail is None:
        out.update(outcome="unspecified", stroke_side=None, mapped=True, verb_agrees=None)
    elif detail in OUTCOMES:
        outcome, side, goes_with = OUTCOMES[detail]
        out.update(outcome=outcome, stroke_side=side, mapped=True, verb_agrees=verb.startswith(goes_with))
    else:
        out.update(outcome="unmapped", stroke_side=None, mapped=False, verb_agrees=None)
    return out


def name_key(name: str | None) -> str:
    """A name compared without case or repeated spaces ("M. Mcdonald" is "M. McDonald")."""
    return " ".join((name or "").split()).casefold()


def name_variants(name: str | None) -> set[str]:
    """A name, and the same name with a hyphenated surname cut at its hyphen: the commentary can use a player's
    earlier name ("V. Tomova" for "V. Tomova-Traycheva", 2026 qualifying)."""
    tokens = (name or "").split()
    if not tokens:
        return set()
    out = {name_key(name)}
    if "-" in tokens[-1].strip("-"):
        out.add(name_key(" ".join(tokens[:-1] + [tokens[-1].split("-")[0]])))
    return out


def team_forms(teams: list) -> list[dict]:
    """For each team (1, 2): the name forms the commentary uses, and each player's names -> player uuid."""
    out = []
    for team in teams or []:
        players = [p for p in team.get("players") or [] if isinstance(p, dict)]
        forms, uuids = set(), {}
        for p in players:
            for key in ("short_name", "full_name", "last_name"):
                for form in name_variants(p.get(key)):
                    forms.add(form)
                    uuids.setdefault(form, p.get("uuid"))
        if len(players) > 1:
            for key in ("last_name", "short_name"):
                names = [sorted(name_variants(p.get(key)), key=len) for p in players]
                if all(names):
                    forms.add("/".join(n[-1] for n in names))  # the full names
                    forms.add("/".join(n[0] for n in names))   # hyphenated surnames cut
        out.append({"forms": forms, "uuids": uuids})
    return out


def name_team(name: str | None, forms: list[dict]) -> int | None:
    """1 or 2 when exactly one team goes by ``name``, else None."""
    key = name_key(name)
    hits = [i + 1 for i, team in enumerate(forms) if key and key in team["forms"]]
    return hits[0] if len(hits) == 1 else None


def player_id(name: str | None, forms: list[dict], team: int | None) -> str | None:
    return forms[team - 1]["uuids"].get(name_key(name)) if team else None


def entry_key(entry: dict) -> tuple[int, int, int] | None:
    m = ENTRY_ID.match(str(entry.get("id") or ""))
    return (int(m.group("set")), int(m.group("game")), int(m.group("point"))) if m else None


def chronological(commentary: list) -> list:
    """The entries in match order: by id when every id parses, else the list reversed (it runs newest first)."""
    entries = list(commentary or [])
    if entries and all(entry_key(e) for e in entries):
        return sorted(entries, key=entry_key)
    return list(reversed(entries))


def is_tiebreak(game_no: int | None, scores: list[str]) -> bool:
    """A game at 6-6 (game 13), or one whose point scores leave the 0/15/30/40/AD ladder."""
    if game_no == 13:
        return True
    for score in scores:
        parts = [x.strip() for x in str(score or "").split("-")]
        if len(parts) == 2 and all(parts) and any(x not in REGULAR_POINTS for x in parts):
            return True
    return False


def tiebreak_server(first_server: int | None, point_no: int | None) -> int | None:
    """Server of a tiebreak's n-th point: the first serves once, then each side twice in turn."""
    if first_server not in (1, 2) or not point_no:
        return None
    return first_server if (point_no // 2) % 2 == 0 else 3 - first_server


def utc(ts) -> str | None:
    try:
        return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if ts else None
    except (TypeError, ValueError, OSError):
        return None


def point_rows(payload: dict) -> list[dict]:
    """One row per point of a match-centre document, in match order, with the parsed sentence and the server."""
    forms = team_forms(payload.get("teams"))
    entries = chronological(payload.get("commentary"))
    servers, scores = {}, {}
    for e in entries:
        key = entry_key(e)
        game = key[:2] if key else (e.get("set"), None)
        if e.get("type") == "serve":
            said = parse_commentary(e.get("commentary"))
            name = said.get("server")
            team = name_team(name, forms)
            servers[game] = {"name": name, "team": team, "player_id": player_id(name, forms, team)}
        elif e.get("type") in POINT_TYPES:
            scores.setdefault(game, []).append(e.get("score"))
    rows = []
    for e in entries:
        if e.get("type") not in POINT_TYPES:
            continue
        key = entry_key(e)
        set_no, game_no, point_no = key if key else (e.get("set"), None, None)
        said = parse_commentary(e.get("commentary"))
        winner = e.get("winner") if e.get("winner") in (1, 2) else None
        role = said.get("subject_role")
        subject_team = (winner if role == "winner" else 3 - winner) if winner and role else None
        server = servers.get((set_no, game_no)) or {}
        tiebreak = is_tiebreak(game_no, scores.get((set_no, game_no), []))
        point_server = tiebreak_server(server.get("team"), point_no) if tiebreak else server.get("team")
        rows.append({
            "seq": len(rows) + 1, "entry_id": e.get("id"), "set": set_no, "game": game_no, "point": point_no,
            "tiebreak": tiebreak, "type": e.get("type"), "timestamp": e.get("timestamp"), "utc": utc(e.get("timestamp")),
            "duration": e.get("duration"), "winner": e.get("winner"), "score": e.get("score"),
            "games_score": e.get("games_score"), "is_game_complete": e.get("is_game_complete"),
            "commentary": e.get("commentary"), "subject": said.get("subject"), "verb": said.get("verb"),
            "subject_role": role, "subject_team": subject_team, "subject_name_team": name_team(said.get("subject"), forms),
            "detail": said.get("detail"), "outcome": said.get("outcome"), "stroke_side": said.get("stroke_side"),
            "mapped": said.get("mapped"), "verb_agrees": said.get("verb_agrees"),
            "game_server_name": server.get("name"), "game_server_team": server.get("team"),
            "game_server_player_id": server.get("player_id"), "point_server_team": point_server,
        })
    return rows


def stat_rows(payload: dict) -> list[dict]:
    """Every statistic of every block and set ("All" = the match), one row each, values verbatim."""
    rows = []
    stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
    for group, blocks in stats.items():
        for block in blocks or []:
            for st in block.get("sets") or []:
                for item in st.get("stats") or []:
                    row = {"group": group, "block": block.get("name"), "set": st.get("set"), "stat": item.get("name")}
                    for n, side in ((1, "teamA"), (2, "teamB")):
                        value = item.get(side) or {}
                        row.update({f"team{n}_primary": value.get("primary"), f"team{n}_secondary": value.get("secondary"),
                                    f"team{n}_subscript": value.get("subscript"),
                                    f"team{n}_is_leading": value.get("is_leading_stat")})
                    rows.append(row)
    return rows


def set_scores(team: dict) -> str | None:
    """A team's set scores as text, the tiebreak points in brackets: "6 7(7)"."""
    out = []
    for item in sorted(team.get("score") or [], key=lambda x: x.get("set") or 0):
        tb = item.get("tie_break")
        out.append(f"{item.get('game')}" + (f"({tb})" if tb is not None else ""))
    return " ".join(out) or None


def match_meta(match: dict, lookup: dict) -> dict:
    """The descriptive fields of a match, from a draw entry or a match-centre document.

    ``lookup`` maps team uuid -> team, player uuid -> player, round uuid -> name and court id -> name (the draw's
    lists); a match-centre document carries its teams' players inline instead."""
    status = match.get("match_status") or {}
    row = {"match_id": match.get("match_id"), "match_uuid": match.get("uuid") or match.get("id"),
           "round_name": match.get("round_name") or lookup.get("rounds", {}).get(match.get("round_id")),
           "date": match.get("date"), "actual_start_time": match.get("actual_start_time"),
           "duration": match.get("duration"), "court_id": match.get("court_id"),
           "court_name": lookup.get("courts", {}).get(str(match.get("court_id"))), "session": match.get("session"),
           "match_status": status.get("abbr"), "match_status_name": status.get("name"),
           "match_state": match.get("match_state"), "winner_team": None}
    for n, team in enumerate((match.get("teams") or [])[:2], 1):
        if not isinstance(team, dict):  # a place not yet filled (later rounds of a draw copied before they were played)
            continue
        info = lookup.get("teams", {}).get(str(team.get("team_id"))) or team
        players = [lookup.get("players", {}).get(p) if isinstance(p, str) else p for p in info.get("players") or []]
        players = [p for p in players if p]
        row.update({f"team{n}_id": team.get("team_id"), f"team{n}_names": ";".join(p.get("full_name") or "" for p in players) or None,
                    f"team{n}_player_ids": ";".join(p.get("uuid") or "" for p in players) or None,
                    f"team{n}_tour_ids": ";".join(p.get("tour_id") or "" for p in players) or None,
                    f"team{n}_seed": info.get("seed") or None, f"team{n}_entry_status": info.get("entry_status"),
                    f"team{n}_score": set_scores(team)})
        if team.get("status") == "Winner":
            row["winner_team"] = n
    return row


def draw_lookup(draw: dict) -> dict:
    return {"teams": {str(t.get("uuid")): t for t in draw.get("teams") or []},
            "players": {p.get("uuid"): p for p in draw.get("players") or []},
            "rounds": {r.get("uuid"): r.get("name") for r in draw.get("rounds") or []},
            "courts": {str(c.get("uuid")): c.get("name") for c in draw.get("courts") or []}}


def is_match_document(payload) -> bool:
    """A match-centre document, as against the API's {"message": "match id not found"} answer."""
    return isinstance(payload, dict) and "commentary" in payload


def document_record(receipt: dict | None, payload) -> tuple[str, str | None]:
    """How a match stands: ("points" | "empty" | "absent" | "error" | "not fetched", reason).

    ``payload`` is the saved document, or None when no file was saved or it is missing."""
    if not receipt:
        return "not fetched", None
    if receipt.get("error"):
        return "error", receipt["error"]
    if receipt.get("absent"):
        return "absent", receipt["absent"]
    if receipt.get("status") == 404:
        return "absent", "HTTP 404"
    if payload is None:
        return "error", "the saved file is missing"
    if not is_match_document(payload):
        message = payload.get("message") or payload.get("error") if isinstance(payload, dict) else None
        return "absent", f"no match document ({message or str(payload)[:80]})"
    points = [e for e in payload.get("commentary") or [] if e.get("type") in POINT_TYPES]
    if points:
        return "points", None
    status = (payload.get("match_status") or {}).get("abbr")
    if status == "W/O":
        return "empty", "walkover: no point was played"
    return "empty", f"no point in the commentary (status {status})"


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
def fetch_draw(client: F.FeedClient, receipts, event: str, *, refresh: bool) -> dict:
    return P.fetch(client, f"{API}/event/{EVENTS[event]}/draws", draw_dest(event), receipts, name=f"draws/{event}",
                   refresh=refresh, validator=P.json_validator, absent=gateway_not_found,
                   extra={"event": event, "event_nid": EVENTS[event]})


def fetch_match(client: F.FeedClient, receipts, match_id: str, *, refresh: bool) -> dict:
    return P.fetch(client, f"{API}/match-centre/{match_id}", match_dest(match_id), receipts,
                   name=f"match-centre/{match_id}", refresh=refresh, validator=P.json_validator,
                   absent=gateway_not_found, extra={"match_id": match_id})


def load_draws(events: list[str]) -> dict[str, dict]:
    return {event: P.read_json(draw_dest(event)) for event in events if draw_dest(event).exists()}


def draw_matches(draws: dict[str, dict]) -> list[dict]:
    """Every match of the draws, in draw order: {"event", "match_id", "match", "lookup", "file"}."""
    out = []
    for event, draw in draws.items():
        lookup = draw_lookup(draw)
        for match in draw.get("matches") or []:
            out.append({"event": event, "match_id": match.get("match_id"), "match": match, "lookup": lookup,
                        "file": P.rel(draw_dest(event)), "draw": draw})
    return out


def cdx_rows(payload) -> list[dict]:
    """The Wayback CDX answer (JSON rows, header first) as dicts, one per distinct content of each URL."""
    if not payload:
        return []
    header, *rows = payload
    seen, out = set(), []
    for values in rows:
        row = dict(zip(header, values))
        key = (row.get("original"), row.get("digest"))
        if key in seen:
            continue
        seen.add(key)
        row["match_id"] = (row.get("original") or "").split("?")[0].rstrip("/").rsplit("/", 1)[-1]
        out.append(row)
    return out


def fetch_wayback(client: F.FeedClient, receipts, streak: F.FailureStreak, outcomes: Counter, *, refresh: bool) -> dict:
    cdx_dest = P.raw_path(SOURCE, "wayback", "cdx.json")
    receipt = P.fetch(client, WAYBACK_CDX, cdx_dest, receipts, name="wayback/cdx", refresh=refresh,
                      validator=P.json_validator)
    outcomes[f"wayback-cdx:{receipt.get('error') or receipt.get('status')}" + (":cached" if receipt.get("skipped") else "")] += 1
    if receipt.get("status") != 200 or receipt.get("error"):
        return {"cdx": receipt.get("error") or receipt.get("status"), "captures": 0}
    rows = cdx_rows(P.read_json(cdx_dest))
    for row in rows:
        url = f"{WAYBACK}/web/{row['timestamp']}id_/{row['original']}"
        receipt = P.fetch(client, url, wayback_dest(row["timestamp"], row["match_id"]), receipts,
                          name=f"wayback/{row['timestamp']}/{row['match_id']}", refresh=refresh,
                          validator=P.json_validator, absent=wayback_moved,
                          extra={"match_id": row["match_id"], "capture_timestamp": row["timestamp"],
                                 "original": row["original"], "digest": row.get("digest")})
        outcomes[f"wayback:{receipt.get('error') or receipt.get('status')}" + (":cached" if receipt.get("skipped") else "")] += 1
        streak.note(receipt)
    return {"cdx": 200, "captures": len(rows)}


def draw_capture_rows(payload) -> list[dict]:
    """The Wayback's copies of event draws, one per distinct content of each URL, with the event id; the current
    edition's six draws, held live, are left out."""
    live = {str(nid) for nid in EVENTS.values()}
    out = []
    for row in cdx_rows(payload):
        m = DRAW_URL.search((row.get("original") or "").split("?")[0])
        if m and m.group("nid") not in live:
            out.append({**row, "nid": m.group("nid")})
    return out


def fetch_wayback_draws(client: F.FeedClient, receipts, streak: F.FailureStreak, outcomes: Counter, *,
                        refresh: bool) -> dict:
    """The archived draws of earlier editions: every match and score of 2019-2025, qualifying and doubles included,
    which gives the Wayback's point captures of those years a denominator."""
    cdx_dest = P.raw_path(SOURCE, "wayback_draws", "cdx.json")
    receipt = P.fetch(client, WAYBACK_DRAWS_CDX, cdx_dest, receipts, name="wayback-draws/cdx", refresh=refresh,
                      validator=P.json_validator)
    outcomes[f"wayback-draws-cdx:{receipt.get('error') or receipt.get('status')}" + (":cached" if receipt.get("skipped") else "")] += 1
    if receipt.get("status") != 200 or receipt.get("error"):
        return {"cdx": receipt.get("error") or receipt.get("status"), "captures": 0}
    rows = draw_capture_rows(P.read_json(cdx_dest))
    for row in rows:
        url = f"{WAYBACK}/web/{row['timestamp']}id_/{row['original']}"
        receipt = P.fetch(client, url, draw_capture_dest(row["timestamp"], row["nid"]), receipts,
                          name=f"wayback-draws/{row['timestamp']}/{row['nid']}", refresh=refresh,
                          validator=P.json_validator, absent=wayback_moved,
                          extra={"event_nid": row["nid"], "capture_timestamp": row["timestamp"],
                                 "original": row["original"], "digest": row.get("digest")})
        outcomes[f"wayback-draws:{receipt.get('error') or receipt.get('absent') and 'absent' or receipt.get('status')}"
                 + (":cached" if receipt.get("skipped") else "")] += 1
        streak.note(receipt)
    return {"cdx": 200, "captures": len(rows)}


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def saved_document(receipt: dict | None, path: Path):
    """The JSON saved for a fetch, or None when none was saved (or the file is gone)."""
    if receipt and receipt.get("status") == 200 and not receipt.get("error") and path.exists():
        return P.read_json(path)
    return None


def document_rows(payload, receipt: dict, source_file: str, base: dict) -> tuple[dict, list[dict], list[dict]]:
    """Summary fields, point rows and statistic rows of one fetched document, each carrying ``base``."""
    record, reason = document_record(receipt, payload)
    info = {"record": record, "record_reason": reason,
            "fetch_status": receipt.get("error") or receipt.get("absent") or receipt.get("status"),
            "source_file": source_file if payload is not None else None,
            "source_sha256": receipt.get("sha256"), "retrieved_at": receipt.get("retrieved_at")}
    points, stats = [], []
    if is_match_document(payload):
        entries = payload.get("commentary") or []
        prov = {"source_file": source_file, "source_sha256": receipt.get("sha256"), "retrieved_at": receipt.get("retrieved_at")}
        points = [{**base, **r, **prov} for r in point_rows(payload)]
        stats = [{**base, **r, **prov} for r in stat_rows(payload)]
        stamps = [p["timestamp"] for p in points if p["timestamp"]]
        types = Counter(e.get("type") for e in entries if e.get("type") not in POINT_TYPES | {"serve"})
        info.update(commentary_entries=len(entries), serve_entries=sum(1 for e in entries if e.get("type") == "serve"),
                    points=len(points), sets_with_points=len({p["set"] for p in points}) if points else 0,
                    first_point_utc=utc(min(stamps)) if stamps else None, last_point_utc=utc(max(stamps)) if stamps else None,
                    stats_sets=";".join(sorted({str(r["set"]) for r in stats}, key=lambda x: (not x.isdigit(), x.zfill(3)))) or None,
                    stats_rows=len(stats), unexpected_entry_types=";".join(f"{k}:{v}" for k, v in sorted(types.items())) or None)
    return info, points, stats


def stage(receipts, events: list[str]) -> dict:
    match_rows, point_rows_all, stat_rows_all = [], [], []
    for item in draw_matches(load_draws(events)):
        draw, match, match_id = item["draw"], item["match"], item["match_id"]
        event_info = draw.get("event") or {}
        base = {"record_key": f"{YEAR}/{match_id}", "route": "api", "year": YEAR, "event": item["event"],
                "match_id": match_id}
        receipt = receipts.get(f"match-centre/{match_id}")
        path = match_dest(match_id)
        payload = saved_document(receipt, path)
        info, points, stats = document_rows(payload, receipt or {}, P.rel(path), base)
        row = {**base, "event_name": event_info.get("name"), "event_nid": event_info.get("nid"),
               "scoring_format": event_info.get("scoring_format"), **match_meta(match, item["lookup"]), **info,
               "draw_file": item["file"]}
        match_rows.append(row)
        point_rows_all.extend(points)
        stat_rows_all.extend(stats)
    wayback = wayback_rows(receipts)
    for row in wayback:
        match_rows.append(row["match"])
        point_rows_all.extend(row["points"])
        stat_rows_all.extend(row["stats"])
    archived = archived_draw_rows(receipts, [row["match"] for row in wayback])
    now = P.utc_now_iso()
    out = {}
    for name, columns, rows in (("matches", MATCH_COLUMNS, match_rows), ("points", POINT_COLUMNS, point_rows_all),
                                ("set_statistics", STAT_COLUMNS, stat_rows_all),
                                ("archived_draws", ARCHIVED_DRAW_COLUMNS, archived)):
        dest = P.dump_path(SOURCE, f"{name}.parquet")
        table = [[P.s(r.get(c)) for c in columns] for r in rows]
        stats = P.stage_table(SOURCE, dest, columns, table, source_file=P.rel(P.raw_path(SOURCE)), retrieved_at=now,
                              extra={"events": ";".join(events)})
        out[name] = {"rows": stats["rows"], "dest": stats["dest"], "bytes": stats["bytes"]}
        P.log(f"[{SOURCE}] staged {stats['dest']}: {stats['rows']:,} rows")
    return out


def wayback_rows(receipts) -> list[dict]:
    """One staged match row per fetched Wayback capture, with its points and statistics."""
    out = []
    for name, receipt in sorted(receipts.all().items()):
        if not name.startswith("wayback/") or name == "wayback/cdx":
            continue
        match_id, stamp = receipt.get("match_id"), receipt.get("capture_timestamp")
        path = wayback_dest(stamp, match_id)
        payload = saved_document(receipt, path)
        date = payload.get("date") if isinstance(payload, dict) else None
        year = int(date[:4]) if date and date[:4].isdigit() else int(stamp[:4])
        event_info = (payload.get("event") or {}) if isinstance(payload, dict) else {}
        prefix = re.match(r"^[A-Z]+", match_id or "")
        base = {"record_key": f"{year}/{match_id}@{stamp}", "route": "wayback", "year": year,
                "event": prefix.group(0) if prefix else None, "match_id": match_id}
        info, points, stats = document_rows(payload, receipt, P.rel(path), base)
        meta = match_meta(payload, {}) if is_match_document(payload) else {"match_id": match_id}
        row = {**base, "event_name": event_info.get("event_name") or event_info.get("title"),
               "event_nid": event_info.get("nid"), "scoring_format": event_info.get("scoring_format"), **meta, **info,
               "capture_timestamp": stamp, "capture_url": receipt.get("url")}
        out.append({"match": row, "points": points, "stats": stats})
    return out


def draw_capture_payloads(receipts) -> list[dict]:
    """Every fetched archived draw that lists matches: {"timestamp", "nid", "payload", "receipt", "path"}."""
    out = []
    for name, receipt in sorted(receipts.all().items()):
        if not name.startswith("wayback-draws/") or name == "wayback-draws/cdx":
            continue
        path = draw_capture_dest(receipt.get("capture_timestamp"), receipt.get("event_nid"))
        payload = saved_document(receipt, path)
        if isinstance(payload, dict) and payload.get("matches"):
            out.append({"timestamp": receipt["capture_timestamp"], "nid": receipt["event_nid"], "payload": payload,
                        "receipt": receipt, "path": path})
    return out


def draw_year(payload: dict, timestamp: str) -> int:
    """The edition a draw belongs to, as the draw states it, else the capture's year."""
    year = str((payload.get("year") or {}).get("year") or "")
    return int(year) if year.isdigit() else int(timestamp[:4])


def finished_matches(payload: dict) -> int:
    return sum(1 for m in payload.get("matches") or [] if (m.get("match_status") or {}).get("abbr") in FINISHED)


def draw_of_record(captures: list[dict]) -> dict:
    """Of an event's archived draws, the one with the most finished matches, the latest among equals."""
    return max(captures, key=lambda c: (finished_matches(c["payload"]), c["timestamp"]))


def best_points_capture(rows: list[dict]) -> dict | None:
    """Of a match's Wayback captures, a finished one with points if there is one, else the one with most points."""
    with_points = [r for r in rows if r.get("record") == "points"]
    if not with_points:
        return None
    return max(with_points, key=lambda r: (r.get("match_status") in FINISHED, int(r.get("points") or 0)))


def archived_draw_rows(receipts, wayback_matches: list[dict]) -> list[dict]:
    """One row per match of every archived draw (each event's draw of record), linked to the match's Wayback
    captures with points when there are any."""
    by_match = defaultdict(list)
    for r in wayback_matches:
        by_match[(int(r["year"]), r["match_id"])].append(r)
    events = defaultdict(list)
    for c in draw_capture_payloads(receipts):
        events[(draw_year(c["payload"], c["timestamp"]), c["nid"])].append(c)
    out = []
    for (year, nid), captures in sorted(events.items()):
        chosen = draw_of_record(captures)
        payload, receipt = chosen["payload"], chosen["receipt"]
        lookup = draw_lookup(payload)
        event_info = payload.get("event") or {}
        for match in payload.get("matches") or []:
            meta = match_meta(match, lookup)
            prefix = re.match(r"^[A-Z]+", meta.get("match_id") or "")
            linked = by_match.get((year, meta.get("match_id")), [])
            best = best_points_capture(linked)
            out.append({**meta, "year": year, "event": prefix.group(0) if prefix else None,
                        "event_name": event_info.get("name"), "event_nid": event_info.get("nid") or nid,
                        "points_capture": best["record_key"] if best else None,
                        "points_capture_status": best.get("match_status") if best else None,
                        "points_captures": sum(1 for r in linked if r.get("record") == "points"),
                        "draw_capture": chosen["timestamp"], "draw_captures_of_event": len(captures),
                        "draw_matches_finished": finished_matches(payload), "source_file": P.rel(chosen["path"]),
                        "source_sha256": receipt.get("sha256"), "retrieved_at": receipt.get("retrieved_at")})
    return out


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def summarize(events: list[str], receipts) -> dict:
    """Matches listed per event against the expected counts, and each record's standing, from the staged table."""
    import pyarrow.parquet as pq

    out = {"draws": {}}
    draws = load_draws(events)
    for event in events:
        listed = len((draws.get(event) or {}).get("matches") or [])
        out["draws"][event] = {"listed": listed, "expected": EXPECTED_MATCHES[event], "as_expected": listed == EXPECTED_MATCHES[event]}
    path = P.dump_path(SOURCE, "matches.parquet")
    if path.exists():
        rows = pq.read_table(path, columns=["route", "year", "event", "record", "record_reason", "points"]).to_pylist()
        out["records_by_route_event"] = dict(sorted(Counter(f"{r['route']}|{r['year']}|{r['event']}|{r['record']}" for r in rows).items()))
        out["empty_or_absent_reasons"] = dict(sorted(Counter(f"{r['route']}|{r['record']}|{r['record_reason']}"
                                                             for r in rows if r["record"] != "points").items()))
        out["points_by_route"] = {route: sum(int(r["points"] or 0) for r in rows if r["route"] == route)
                                  for route in sorted({r["route"] for r in rows})}
    return out


def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    events = [e.strip().upper() for e in args.events.split(",")] if args.events else list(EVENTS)
    unknown = [e for e in events if e not in EVENTS]
    if unknown:
        raise SystemExit(f"unknown events {unknown}; known: {', '.join(EVENTS)}")
    wanted_ids = {m.strip().upper() for m in args.matches.split(",")} if args.matches else None
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "started_at": P.utc_now_iso(), "args": vars(args), "decision": F.DECISION}
    client = None
    if not args.stage_only:
        client = F.FeedClient(IMPERSONATE, not_found=gateway_not_found, min_interval=args.min_interval,
                              jitter=args.jitter, max_requests=args.max_requests, headers=HEADERS)
    streak = F.FailureStreak(args.stop_after_failures)
    outcomes = Counter()
    selected: list[dict] = []
    try:
        if not args.stage_only:
            for event in events:
                receipt = fetch_draw(client, receipts, event, refresh=args.refresh_draws)
                outcomes[f"draw:{receipt.get('error') or receipt.get('absent') or receipt.get('status')}" + (":cached" if receipt.get("skipped") else "")] += 1
                streak.note(receipt)
        listed = draw_matches(load_draws(events))
        selected = [m for m in listed if wanted_ids is None or m["match_id"] in wanted_ids]
        if args.limit:
            selected = selected[:args.limit]
        summary["matches_listed"] = len(listed)
        summary["matches_selected"] = len(selected)
        P.log(f"[{SOURCE}] {len(listed)} matches in {len(events)} draws; {len(selected)} selected")
        if not args.stage_only:
            for n, item in enumerate(selected, 1):
                receipt = fetch_match(client, receipts, item["match_id"], refresh=args.refresh)
                outcomes[f"match-centre:{receipt.get('error') or receipt.get('absent') or receipt.get('status')}" + (":cached" if receipt.get("skipped") else "")] += 1
                if receipt.get("status") == 200 and not receipt.get("skipped") and not receipt.get("error") \
                        and not is_match_document(P.read_json(match_dest(item["match_id"]))):
                    receipt = {**receipt, "absent": "saved, but not a match document"}  # e.g. "match id not found"
                streak.note(receipt)
                if n % 50 == 0 or n == len(selected):
                    P.log(f"[{SOURCE}] {n}/{len(selected)} matches; requests={client.requests}; " +
                          ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items())))
            if args.wayback or args.wayback_draws:
                wayback_client = F.FeedClient(IMPERSONATE, not_found=wayback_moved, min_interval=args.wayback_interval,
                                              jitter=args.jitter,
                                              max_requests=(args.max_requests - client.requests) if args.max_requests else None)
                try:
                    if args.wayback:
                        summary["wayback"] = fetch_wayback(wayback_client, receipts, streak, outcomes, refresh=args.refresh)
                        P.log(f"[{SOURCE}] wayback: {summary['wayback']}")
                    if args.wayback_draws:
                        summary["wayback_draws"] = fetch_wayback_draws(wayback_client, receipts, streak, outcomes,
                                                                       refresh=args.refresh)
                        P.log(f"[{SOURCE}] wayback draws: {summary['wayback_draws']}")
                finally:
                    summary["wayback_client"] = wayback_client.stats()
    except (P.Blocked, P.BudgetExhausted, F.Stopped) as stop:
        summary["stopped"] = f"{type(stop).__name__}: {stop}"
        P.log(f"[{SOURCE}] STOPPED: {stop}")
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    if client is not None:
        summary["client"] = client.stats()
        if "wayback_client" in summary:  # runs.jsonl keeps only "client": carry the Wayback requests there too
            summary["client"]["wayback"] = summary["wayback_client"]
    if not args.no_stage:
        try:
            summary["staged"] = stage(receipts, events)
            summary.update(summarize(events, receipts))
        except Exception as err:  # keep the run's record: its fetches are done and cached whatever staging does
            summary["stopped"] = f"staging failed: {type(err).__name__}: {err}"
            P.log(f"[{SOURCE}] STAGING FAILED ({type(err).__name__}: {err}); the fetched documents are kept; "
                  "fix and rerun with --stage-only")
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts"] = dict(sorted(Counter(
        f"{r['name'].split('/')[0]}:{r.get('error') and 'error' or r.get('absent') and 'absent' or r.get('status')}"
        for r in receipts.all().values()).items()))
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = F.write_summary("ausopen_summary.json", summary)
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--events", help=f"comma list of events (default: all of {','.join(EVENTS)})")
    parser.add_argument("--matches", help="comma list of match ids to fetch (default: every match of the draws)")
    parser.add_argument("--limit", type=int, help="fetch only the first N selected matches, in draw order (dry runs)")
    parser.add_argument("--max-requests", type=int, help="stop after this many HTTP requests")
    parser.add_argument("--min-interval", type=float, default=2.0, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=1.0, help="up to this many extra seconds, drawn at random")
    parser.add_argument("--stop-after-failures", type=int, default=5,
                        help="stop after this many fetches in a row without a document (0: never)")
    parser.add_argument("--refresh", action="store_true", help="refetch match documents already held (absences included)")
    parser.add_argument("--refresh-draws", action="store_true", help="refetch the six draws")
    parser.add_argument("--wayback", action="store_true", help="also fetch the Wayback Machine's match-centre captures")
    parser.add_argument("--wayback-draws", action="store_true",
                        help="also fetch the Wayback Machine's copies of earlier editions' draws (no points)")
    parser.add_argument("--wayback-interval", type=float, default=4.0, help="seconds between Wayback requests")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rebuild the Parquet tables and summary")
    parser.add_argument("--no-stage", action="store_true", help="fetch only; skip the Parquet rebuild")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    return 1 if summary.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())

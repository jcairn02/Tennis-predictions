"""The Australian Open's and Roland-Garros's Infosys match-centre files, decrypted: AO 2025, RG 2025 and RG 2026.

The two Slams' match centres are built by Infosys. Their pages load each match's data from
itp-ao-sls / itp-rg-sls.infosys-platforms.com as JSON envelopes ``{lastModified, response, data: null}``, in which
``response`` is AES-128-CBC ciphertext (base64) that the page's own script decrypts in the visitor's browser. The key
is derived from ``lastModified`` alone (``key_iv``). The derivation follows the public implementation in
nipunagarwalla/courtside (backend/scrapers/infosys/decrypt.py, taken from atptour.com's main.js); the same derivation
opens the AO and RG files (checked on 7 Oct 2026 on the RG 2025 and 2026 finals and the AO 2025 final).

Collected under the owner's decision of 7 Oct 2026 (docs/decisions/2026-10-07-serve-speed-acquisition.md), which
allows decryption for these files only. The other limits of 24 Sep 2026 stand: about 2 s between requests plus
jitter, a --max-requests budget, everything cached with a receipt and nothing fetched twice, a stop and report on any
block (HTTP 429, a challenge page, a redirect, a connection reset, or a 403 that is not S3's "no such object" on a
route that has already served a file), and no logins, tokens or CAPTCHA solving. Requests carry the Origin and Referer
that the Slam's own page sends.

Editions and routes (the only routes that serve these years; probes of 24 Sep and 7 Oct 2026):
    AO 2025  static/prod/match-beats/2025/580/<MID>/data.json        MatchBeats: every point, with the server, the
                                                                       serve number, the serve's speed (km/h) and a
                                                                       first-serve fault's speed
    RG 2025  static/prod/match-centre/2025/520/<MID>/data.json       six blocks: mbData (MatchBeats), stats (key
                                                                       statistics per set: Max Speed, 1st and 2nd
                                                                       Serve Average Speed and the box score), rally
                                                                       (rally analysis: serve speed, direction, side),
                                                                       mbStatus (court, match date), insights, quiz
    RG 2026  prod/api/match-beats/data/year/2026/eventId/520/matchId/<MID>          MatchBeats
             prod/api/stats-plus/v1/keystats/year/2026/eventId/520/matchId/<MID>    key statistics

    RG 2019-2024  static/prod/match-beats/<year>/520/<MID>/data.json     MatchBeats. Raw only (RAW_ONLY below)

RG 2019-2024 were found served on 9 Oct 2026 (probes of each final on the match-centre, match-beats and API routes;
2022-2024 also serve the API routes and 2024 the match-centre file) and are collected under the owner's decision of
8 Oct 2026 (docs/decisions/2026-10-08-scraping-approved.md: every RG edition) for the Roland-Garros first-serve
recount (docs/studies/rg_first_serve_recount/). They are fetched with --no-stage and read from the raw files by that
study. They are never staged into the shared tables: the serve-speed panel reads points.parquet and prefers this
source, so new rows there would change its speeds. A run that names them without --no-stage is refused.

    AO 2013-2024, AO 2026, RG 2013-2018   match-beats, then match-beats-api: raw only, likewise

These are probed (each final) and fetched where served, for the service-game fix of the owner's decision of 9 Oct 2026
(docs/decisions/2026-10-09-roland-garros-box-scores.md, point 3): a match's MatchBeats file names who served first,
which settles whose service games Sackmann's rows give the wrong player.

Matches: singles only, main draw and qualifying, the final round first (the final calibrates a route: it always has
a file):
    AO  MS/WS 701, 601-602, 501-504, 401-408, 301-316, 201-232, 101-164;  MQ/WQ 301-316, 201-232, 101-164
    RG  SM/SD 001-127 (001 the final ... 064-127 the first round);         QM/QD 016-127 (016-031 the last round)
A code without a file is answered by S3 with HTTP 403 AccessDenied (static routes) or by the API with HTTP 404; both
are recorded as absent. A family whose first --skip-family-after codes on a route are all absent is not pressed
further on that route.

Raw (data/raw/point_sources/infosys_slams/<slam>/<year>/<route>/<MID>.json.gz): the envelope exactly as served,
gzipped, plus _receipts.jsonl. Decryption happens at staging, from the raw files.

Staged (data/dump/points/infosys_slams/; strings throughout, as the rest of the dump):
    blocks.parquet    one row per block of every file: lastModified, the decryption's outcome and the decrypted
                      JSON text, so nothing the file holds is lost
    matches.parquet   one row per match code asked: what each route answered, players (Infosys ids, names,
                      countries), court, status, winner, match date (RG 2025), point counts
    points.parquet    every MatchBeats point, its fields verbatim, with set and game numbers
    keystats.parquet  every key statistic of every set ("set0" is the match), RG 2025 and 2026
    rally.parquet     every rally-analysis entry, RG 2025
Summary: data/studies/serve_speed_acquisition/infosys_slams_summary.json (and runs.jsonl).

Usage:
    ./python.sh -m src.ingest.point_sources.infosys_slams                                  # all three editions
    ./python.sh -m src.ingest.point_sources.infosys_slams --editions AO2025 --families MS --max-requests 10
    ./python.sh -m src.ingest.point_sources.infosys_slams --matches SM001,SM002 --editions RG2025
    ./python.sh -m src.ingest.point_sources.infosys_slams --stage-only                     # rebuild from raw
    ./python.sh -m src.ingest.point_sources.infosys_slams --editions RG2019,RG2020,RG2021,RG2022,RG2023,RG2024 \
        --no-stage --summary-dir data/studies/rg_first_serve_recount/collection           # the recount's raw files
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import feeds as F

SOURCE = "infosys_slams"
IMPERSONATE = "chrome"
DECISION = "docs/decisions/2026-10-07-serve-speed-acquisition.md"
STUDY_ROOT = P.PROJECT_ROOT / "data" / "studies" / "serve_speed_acquisition"
HOSTS = {"AO": "https://itp-ao-sls.infosys-platforms.com", "RG": "https://itp-rg-sls.infosys-platforms.com"}
SITES = {"AO": "https://ausopen.com", "RG": "https://www.rolandgarros.com"}
EVENT_IDS = {"AO": 580, "RG": 520}
ROUTES = {
    "match-beats": "/static/prod/match-beats/{year}/{event}/{mid}/data.json",
    "match-centre": "/static/prod/match-centre/{year}/{event}/{mid}/data.json",
    "match-beats-api": "/prod/api/match-beats/data/year/{year}/eventId/{event}/matchId/{mid}",
    "keystats-api": "/prod/api/stats-plus/v1/keystats/year/{year}/eventId/{event}/matchId/{mid}",
}
# the block a single-envelope route holds, named as in the RG match-centre file
ROUTE_BLOCK = {"match-beats": "mbData", "match-beats-api": "mbData", "keystats-api": "stats"}
EDITIONS = {  # "<slam><year>": (slam, year, routes in fetch order)
    "AO2025": ("AO", 2025, ("match-beats",)),
    "RG2025": ("RG", 2025, ("match-centre",)),
    "RG2026": ("RG", 2026, ("match-beats-api", "keystats-api")),
    **{f"RG{y}": ("RG", y, ("match-beats",)) for y in range(2019, 2025)},
    # for the service-game fix of 9 Oct 2026 (module docstring): probed, and fetched where served
    **{f"AO{y}": ("AO", y, ("match-beats", "match-beats-api")) for y in range(2013, 2025)},
    "AO2026": ("AO", 2026, ("match-beats", "match-beats-api", "keystats-api")),
    **{f"RG{y}": ("RG", y, ("match-beats", "match-beats-api")) for y in range(2013, 2019)},
    # the box-score source of later editions (decision of 9 Oct 2026, docs/decisions/2026-10-09-ao-rg-box-scores-from-
    # feeds.md): the key statistics and the point file; a year's routes are probed on its final before a run
    **{f"{s}{y}": (s, y, ("match-beats", "match-beats-api", "keystats-api")) for s in ("AO", "RG")
       for y in range(2027, 2031)},
}
# fetched raw, never staged into the shared tables: the RG first-serve recount, its service-game fix, and the later
# editions' box scores (slam_infosys_overrides.py reads their raw files)
RAW_ONLY = frozenset({f"RG{y}" for y in (*range(2013, 2025), *range(2027, 2031))}
                     | {f"AO{y}" for y in (*range(2013, 2025), 2026, *range(2027, 2031))})
DEFAULT_EDITIONS = [e for e in EDITIONS if e not in RAW_ONLY]
FAMILIES = {"AO": ("MS", "WS", "MQ", "WQ"), "RG": ("SM", "SD", "QM", "QD")}
# (round digit, matches, round) at the AO; (first number, matches, round) at RG
AO_MAIN = ((7, 1, "F"), (6, 2, "SF"), (5, 4, "QF"), (4, 8, "R16"), (3, 16, "R32"), (2, 32, "R64"), (1, 64, "R128"))
AO_QUAL = ((3, 16, "Q3"), (2, 32, "Q2"), (1, 64, "Q1"))
RG_MAIN = ((1, 1, "F"), (2, 2, "SF"), (4, 4, "QF"), (8, 8, "R16"), (16, 16, "R32"), (32, 32, "R64"), (64, 64, "R128"))
RG_QUAL = ((16, 16, "Q3"), (32, 32, "Q2"), (64, 64, "Q1"))
S3_DENIED = b"<Code>AccessDenied</Code>"

POINT_FIELDS = ["pointId", "point", "server", "serve", "serveSpeed", "faultSrvSpd", "scorer", "result", "stroke",
                "hand", "tm1GameScore", "tm2GameScore", "tm1Rally", "tm2Rally", "rallyLengthMissing", "isBrkPt",
                "brkPts", "brkPtsLost", "isCrucialPt", "isCspPt", "serveRating", "tm1WinProb", "tm2WinProb",
                "currentMatchDuration"]
STAT_FIELDS = ["order", "name", "player1", "player2", "tm1Player1", "tm1Player2", "tm2Player1", "tm2Player2",
               "influence"]
RALLY_FIELDS = ["pointId", "set", "score", "serve", "serveSpeed", "serveDir", "courtSide", "pointEndType", "shotType",
                "hand", "crucialPoint", "t1BreakPoint", "t2BreakPoint", "t1NetPoint", "t2NetPoint", "tieBreak",
                "setPoint"]
KEYS = ["slam", "year", "match_id"]
MATCH_COLUMNS = KEYS + [
    "event_id", "family", "tour", "draw", "round_from_code", "routes", "route_status", "files", "blocks_ok",
    "blocks_empty", "blocks_failed", "event_type", "court_name", "is_match_complete", "match_status", "match_winner",
    "match_date", "sets_completed", "p1_id", "p1_name", "p1_first_name", "p1_last_name", "p1_country", "p2_id",
    "p2_name", "p2_first_name", "p2_last_name", "p2_country", "points", "points_timed", "first_serve_points_timed",
    "keystats_sets", "rally_entries", "last_modified_utc", "source_files"]


# --------------------------------------------------------------------------------------
# decryption
# --------------------------------------------------------------------------------------
def to_base(n: int, base: int) -> str:
    """``n`` written in ``base`` with JavaScript's digits (Number.prototype.toString(base))."""
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while n:
        n, r = divmod(n, base)
        out = digits[r] + out
    return out or "0"


def key_iv(last_modified_ms: int) -> tuple[bytes, bytes]:
    """The AES-128 key and IV of an envelope: key = "#" + 14 characters derived from lastModified + "$", IV = the key
    in upper case. The 14 characters: lastModified's decimal digits read as hexadecimal and written in base 36, then
    (year + reversed year) x (day + reversed two-digit day) of lastModified's UTC date in base 24, padded with zeros
    or cut to 14."""
    t = datetime.fromtimestamp(last_modified_ms / 1000, tz=timezone.utc)
    day, year = t.day, t.year
    body = to_base(int(str(last_modified_ms), 16), 36) + \
        to_base((year + int(str(year)[::-1])) * (day + int(f"{day:02d}"[::-1])), 24)
    key = "#" + (body + "0" * 14)[:14] + "$"
    return key.encode("utf-8"), key.upper().encode("utf-8")


def decrypt(envelope: dict):
    """The plain JSON of one envelope: its ``data`` when ``response`` is empty (a file served in the clear, or one
    with nothing in it), else the decrypted ``response``. Raises ValueError when the derived key does not open it."""
    from Crypto.Cipher import AES  # imported here so the plan and the tests of the rest run without it

    text = (envelope.get("response") or "").strip()
    if not text:
        return envelope.get("data")
    key, iv = key_iv(int(envelope["lastModified"]))
    raw = base64.b64decode(text + "=" * (-len(text) % 4))
    if not raw or len(raw) % 16:
        raise ValueError(f"ciphertext of {len(raw)} bytes is not a whole number of AES blocks")
    plain = AES.new(key, AES.MODE_CBC, iv).decrypt(raw)
    pad = plain[-1]
    if not 1 <= pad <= 16 or plain[-pad:] != bytes([pad]) * pad:
        raise ValueError("bad padding: the derived key does not open this envelope")
    return json.loads(plain[:-pad].decode("utf-8"))


def blocks_of(route: str, doc: dict) -> dict[str, dict]:
    """A saved file's envelopes by block name: a route's single envelope, or the match-centre file's six."""
    if "response" in doc or "lastModified" in doc:
        return {ROUTE_BLOCK[route]: doc}
    return {name: env for name, env in doc.items() if isinstance(env, dict)}


def envelope_validator(body: bytes):
    """None when the body is an Infosys envelope (or a file of envelopes), else the problem."""
    problem = P.json_validator(body)
    if problem:
        return problem
    try:
        doc = json.loads(body)
    except ValueError:
        return "response is not JSON"
    if not isinstance(doc, dict):
        return "not an Infosys envelope (not a JSON object)"
    if "lastModified" in doc or "response" in doc:
        return None
    if any(isinstance(v, dict) and ("lastModified" in v or "response" in v) for v in doc.values()):
        return None
    return f"not an Infosys envelope (keys {sorted(doc)[:6]})"


# --------------------------------------------------------------------------------------
# the plan
# --------------------------------------------------------------------------------------
def is_qualifying(slam: str, family: str) -> bool:
    return family[1] == "Q" if slam == "AO" else family[0] == "Q"


def match_codes(slam: str, family: str) -> list[tuple[str, str]]:
    """(match id, round) for every match of a family, the final round first."""
    if slam == "AO":
        rounds = AO_QUAL if is_qualifying(slam, family) else AO_MAIN
        return [(f"{family}{r}{n:02d}", rnd) for r, k, rnd in rounds for n in range(1, k + 1)]
    rounds = RG_QUAL if is_qualifying(slam, family) else RG_MAIN
    return [(f"{family}{n:03d}", rnd) for first, k, rnd in rounds for n in range(first, first + k)]


def family_tour(slam: str, family: str) -> str:
    women = family[0] == "W" if slam == "AO" else family[1] == "D"
    return "W" if women else "M"


def round_lookup() -> dict[tuple[str, str], str]:
    return {(slam, mid): rnd for slam, fams in FAMILIES.items() for fam in fams for mid, rnd in match_codes(slam, fam)}


def url_of(slam: str, year: int, route: str, mid: str) -> str:
    return HOSTS[slam] + ROUTES[route].format(year=year, event=EVENT_IDS[slam], mid=mid)


def dest_of(slam: str, year: int, route: str, mid: str) -> Path:
    return P.raw_path(SOURCE, slam, str(year), route, f"{mid}.json.gz")


def receipt_name(slam: str, year: int, route: str, mid: str) -> str:
    return f"{slam}/{year}/{route}/{mid}"


def site_headers(slam: str) -> dict:
    """What the Slam's match-centre page sends with its requests to the Infosys host (a cross-origin fetch)."""
    site = SITES[slam]
    return {"Origin": site, "Referer": site + "/", "Accept": "application/json, text/plain, */*"}


class Calibration:
    """The routes that have served a file to these headers. Only there is S3's HTTP 403 AccessDenied read as "no
    such object"; on any other route it is a refusal, and the run stops (feeds.FeedClient)."""

    def __init__(self, receipts):
        self.ok: set[tuple[str, str]] = set()
        for name, rec in receipts.all().items():
            parts = name.split("/")
            if len(parts) == 4 and rec.get("status") == 200 and not rec.get("error"):
                self.ok.add((parts[0], parts[2]))
        self.current: tuple[str, str] | None = None

    def not_found(self, response) -> str | None:
        if response.status_code == 403 and S3_DENIED in response.content[:4096] and self.current in self.ok:
            return "S3 AccessDenied on a calibrated route: no such object"
        return None


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
def outcome_of(receipt: dict) -> str:
    what = receipt.get("error") and "error" or receipt.get("absent") and "absent" or str(receipt.get("status"))
    return what + (":cached" if receipt.get("skipped") else "")


def fetch_family(client, receipts, cal: Calibration, slam: str, year: int, route: str, family: str,
                 codes: list[tuple[str, str]], args, outcomes: Counter) -> dict | None:
    """Fetch one family's files on one route. Returns a note when the family was given up (its first codes all
    absent), else None."""
    cal.current = (slam, route)
    misses, seen = 0, False
    for mid, _ in codes:
        receipt = P.fetch(client, url_of(slam, year, route, mid), dest_of(slam, year, route, mid), receipts,
                          name=receipt_name(slam, year, route, mid), refresh=args.refresh,
                          validator=envelope_validator, compress=True, headers=site_headers(slam),
                          absent=cal.not_found, extra={"slam": slam, "year": year, "route": route, "match_id": mid})
        outcomes[f"{slam}{year}:{route}:{outcome_of(receipt)}"] += 1
        if receipt.get("status") == 200 and not receipt.get("error"):
            cal.ok.add((slam, route))
            seen = True
        elif not seen and (receipt.get("absent") or receipt.get("status") == 404):
            misses += 1
            if args.skip_family_after and misses >= args.skip_family_after:
                return {"edition": f"{slam}{year}", "route": route, "family": family,
                        "reason": f"the first {misses} codes are absent", "last_code": mid}
    return None


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def s(value) -> str | None:
    return P.s(value)


def utc_of(ms) -> str | None:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError):
        return None


def num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def players_of(blocks: dict[str, object]) -> list[dict]:
    """The two players (id, name, first and last name, country) from MatchBeats, else the key statistics, else the
    match status block."""
    mb = blocks.get("mbData")
    if isinstance(mb, dict) and isinstance(mb.get("playerData"), dict):
        pd_ = mb["playerData"]
        return [{"id": pd_.get(f"tm{t}Ply1Id"), "name": pd_.get(f"tm{t}Ply1Name"),
                 "first": pd_.get(f"tm{t}Ply1FirstName"), "last": pd_.get(f"tm{t}Ply1LastName"),
                 "country": pd_.get(f"tm{t}Ply1Country")} for t in (1, 2)]
    st = blocks.get("stats")
    if isinstance(st, dict) and isinstance(st.get("players"), list) and len(st["players"]) >= 2:
        return [{"id": p.get("player1Id"), "name": p.get("player1Name"), "first": p.get("player1FirstName"),
                 "last": p.get("player1LastName"), "country": p.get("player1Country")} for p in st["players"][:2]]
    ms = blocks.get("mbStatus")
    if isinstance(ms, dict) and isinstance(ms.get("playerData"), dict):
        pd_ = ms["playerData"]
        return [{"id": pd_.get(f"tm{t}Ply1Id"), "name": pd_.get(f"tm{t}Ply1Name"),
                 "first": pd_.get(f"tm{t}Ply1FirstName"), "last": pd_.get(f"tm{t}Ply1LastName"),
                 "country": pd_.get(f"tm{t}Ply1Country")} for t in (1, 2)]
    return [{}, {}]


def point_rows(base: list, mb: dict) -> list[list]:
    rows = []
    for si, st in enumerate(mb.get("setData") or [], 1):
        set_no = st.get("set", si) if isinstance(st, dict) else si
        set_fields = json.dumps({k: v for k, v in st.items() if k != "gameData"}, ensure_ascii=False, sort_keys=True)
        for gi, game in enumerate(st.get("gameData") or [], 1):
            game_fields = json.dumps({k: v for k, v in game.items() if k != "pointData"}, ensure_ascii=False,
                                     sort_keys=True)
            for seq, p in enumerate(game.get("pointData") or [], 1):
                other = {k: v for k, v in p.items() if k not in POINT_FIELDS}
                rows.append(base + [s(set_no), s(game.get("game", gi)), str(seq)] + [s(p.get(k)) for k in POINT_FIELDS]
                            + [json.dumps(other, ensure_ascii=False, sort_keys=True) if other else None,
                               game_fields, set_fields])
    return rows


def stat_rows(base: list, stats: dict) -> list[list]:
    rows = []
    for set_key, entries in (stats.get("setStats") or {}).items():
        for e in entries or []:
            other = {k: v for k, v in e.items() if k not in STAT_FIELDS}
            rows.append(base + [set_key] + [s(e.get(k)) for k in STAT_FIELDS]
                        + [json.dumps(other, ensure_ascii=False, sort_keys=True) if other else None])
    return rows


def rally_rows(base: list, rally: dict) -> list[list]:
    rows = []
    for cat in rally.get("rallyData") or []:
        for list_name, entries in cat.items():
            if not isinstance(entries, list):
                continue
            for e in entries:
                if not isinstance(e, dict):
                    continue
                other = {k: v for k, v in e.items() if k not in RALLY_FIELDS}
                rows.append(base + [s(cat.get("name")), list_name] + [s(e.get(k)) for k in RALLY_FIELDS]
                            + [json.dumps(other, ensure_ascii=False, sort_keys=True) if other else None])
    return rows


def stage(receipts, editions: list[str]) -> dict:
    """Decrypt every saved file of the editions and write the five tables."""
    rounds = round_lookup()
    block_rows, points, stats, rallies, match_rows = [], [], [], [], []
    by_match: dict[tuple, dict] = defaultdict(dict)
    for name, rec in receipts.all().items():
        parts = name.split("/")
        if len(parts) == 4 and f"{parts[0]}{parts[1]}" in editions:
            by_match[(parts[0], int(parts[1]), parts[3])][parts[2]] = rec
    failures = Counter()
    for (slam, year, mid), recs in sorted(by_match.items()):
        family = mid[:2]
        decrypted: dict[str, object] = {}
        files, counts, last_modified = [], Counter(), []
        for route, rec in sorted(recs.items()):
            path = dest_of(slam, year, route, mid)
            if rec.get("status") != 200 or rec.get("error") or not path.exists():
                continue
            files.append(P.rel(path))
            for block, env in blocks_of(route, P.read_json(path)).items():
                base = [slam, str(year), mid, route, block]
                lm = env.get("lastModified")
                try:
                    plain = decrypt(env)
                    outcome = "ok" if plain not in (None, {}, []) else "empty"
                except Exception as err:  # a key that does not open the file, or text that is not JSON
                    plain, outcome = None, f"failed: {type(err).__name__}: {err}"
                    failures[f"{slam}{year}:{route}:{block}"] += 1
                counts["ok" if outcome == "ok" else "empty" if outcome == "empty" else "failed"] += 1
                if lm:
                    last_modified.append(int(lm))
                block_rows.append(base + [s(lm), utc_of(lm), str(len(env.get("response") or "")), outcome,
                                          json.dumps(plain, ensure_ascii=False) if plain is not None else None,
                                          P.rel(path), rec.get("sha256"), rec.get("retrieved_at")])
                if outcome != "ok":
                    continue
                decrypted.setdefault(block, plain)
                keys = [slam, str(year), mid, route]
                if block == "mbData" and isinstance(plain, dict):
                    points.extend(point_rows(keys, plain))
                elif block == "stats" and isinstance(plain, dict):
                    stats.extend(stat_rows(keys, plain))
                elif block == "rally" and isinstance(plain, dict):
                    rallies.extend(rally_rows(keys, plain))
        mb = decrypted.get("mbData") if isinstance(decrypted.get("mbData"), dict) else {}
        st = decrypted.get("stats") if isinstance(decrypted.get("stats"), dict) else {}
        ms = decrypted.get("mbStatus") if isinstance(decrypted.get("mbStatus"), dict) else {}
        pts = [p for set_ in mb.get("setData") or [] for g in set_.get("gameData") or [] for p in g.get("pointData") or []]
        timed = [p for p in pts if (num(p.get("serveSpeed")) or 0) > 0]
        rally_n = sum(len(v) for c in (decrypted.get("rally") or {}).get("rallyData") or [] for v in c.values()
                      if isinstance(v, list)) if isinstance(decrypted.get("rally"), dict) else 0
        p1, p2 = players_of(decrypted)
        first = lambda *vals: next((v for v in vals if v not in (None, "")), None)  # noqa: E731
        match_rows.append([
            slam, str(year), mid, str(EVENT_IDS[slam]), family, family_tour(slam, family),
            "qual" if is_qualifying(slam, family) else "main", rounds.get((slam, mid)),
            json.dumps(sorted(recs)), json.dumps({r: outcome_of(x).replace(":cached", "") for r, x in sorted(recs.items())}),
            str(len(files)), str(counts["ok"]), str(counts["empty"]), str(counts["failed"]),
            s(first(mb.get("eventType"))), s(first(mb.get("courtName"), st.get("courtName"), ms.get("courtName"))),
            s(first(mb.get("isMatchComplete"), st.get("matchCompleted"))),
            s(first(mb.get("matchStatus"), ms.get("matchStatus"))), s(first(mb.get("matchWinner"), ms.get("matchWinner"))),
            s(ms.get("matchDate")), s(first(mb.get("setsComplete"), st.get("setsCompleted"))),
            s(p1.get("id")), s(p1.get("name")), s(p1.get("first")), s(p1.get("last")), s(p1.get("country")),
            s(p2.get("id")), s(p2.get("name")), s(p2.get("first")), s(p2.get("last")), s(p2.get("country")),
            str(len(pts)), str(len(timed)), str(sum(1 for p in timed if str(p.get("serve")) == "1")),
            str(len(st.get("setStats") or {})), str(rally_n),
            utc_of(max(last_modified)) if last_modified else None, json.dumps(files)])
    out = {"decrypt_failures": dict(failures)}
    retrieved = max((r.get("retrieved_at") or "" for recs in by_match.values() for r in recs.values()), default=None)
    tables = [
        ("blocks.parquet", KEYS + ["route", "block", "last_modified", "last_modified_utc", "response_chars",
                                   "decrypt_outcome", "json", "source_file", "source_sha256", "retrieved_at"], block_rows),
        ("matches.parquet", MATCH_COLUMNS, match_rows),
        ("points.parquet", KEYS + ["route", "set", "game", "seq"] + POINT_FIELDS
         + ["other_fields", "game_fields", "set_fields"], points),
        ("keystats.parquet", KEYS + ["route", "set_key"] + STAT_FIELDS + ["other_fields"], stats),
        ("rally.parquet", KEYS + ["route", "category", "list"] + RALLY_FIELDS + ["other_fields"], rallies),
    ]
    for file, header, rows in tables:
        st_ = P.stage_table(SOURCE, P.dump_path(SOURCE, file), header, rows, source_file=P.rel(P.raw_path(SOURCE)),
                            retrieved_at=retrieved, extra={"decision": DECISION})
        out[file] = {"rows": st_["rows"], "bytes": st_["bytes"]}
        P.log(f"[{SOURCE}] staged {file}: {st_['rows']:,} rows")
    return out


def summarize(editions: list[str]) -> dict:
    """Per edition and family: codes asked, files, absences, matches with points, with timed points, decrypt failures."""
    import pyarrow.parquet as pq

    path = P.dump_path(SOURCE, "matches.parquet")
    if not path.exists():
        return {}
    rows = pq.read_table(path).to_pylist()
    out = {}
    for r in rows:
        key = f"{r['slam']}{r['year']}|{r['family']}"
        if f"{r['slam']}{r['year']}" not in editions:
            continue
        d = out.setdefault(key, Counter())
        d["codes"] += 1
        d["with_file"] += int(r["files"] or 0) > 0
        d["with_points"] += int(r["points"] or 0) > 0
        d["with_timed_points"] += int(r["points_timed"] or 0) > 0
        d["with_keystats"] += int(r["keystats_sets"] or 0) > 0
        d["blocks_failed"] += int(r["blocks_failed"] or 0)
        for route, status in json.loads(r["route_status"]).items():
            d[f"{route}:{status}"] += 1
    return {k: dict(v) for k, v in sorted(out.items())}


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    editions = [e.strip().upper() for e in args.editions.split(",")] if args.editions else list(DEFAULT_EDITIONS)
    unknown = [e for e in editions if e not in EDITIONS]
    if unknown:
        raise SystemExit(f"unknown editions {unknown}; known: {', '.join(EDITIONS)}")
    raw_only = sorted(set(editions) & RAW_ONLY)
    if raw_only and not args.no_stage:
        raise SystemExit(f"{', '.join(raw_only)} are fetched raw only (module docstring): add --no-stage")
    families = {f.strip().upper() for f in args.families.split(",")} if args.families else None
    wanted = {m.strip().upper() for m in args.matches.split(",")} if args.matches else None
    only_routes = {r.strip() for r in args.routes.split(",")} if args.routes else None
    if only_routes and not only_routes <= set(ROUTES):
        raise SystemExit(f"unknown routes {sorted(only_routes - set(ROUTES))}; known: {', '.join(ROUTES)}")
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "started_at": P.utc_now_iso(), "args": vars(args), "decision": DECISION}
    client = None
    outcomes, skipped = Counter(), []
    if not args.stage_only:
        cal = Calibration(receipts)
        client = F.FeedClient(IMPERSONATE, not_found=cal.not_found, min_interval=args.min_interval, jitter=args.jitter,
                              max_requests=args.max_requests)
        try:
            for edition in editions:
                slam, year, routes = EDITIONS[edition]
                for family in FAMILIES[slam]:
                    if families and family not in families:
                        continue
                    codes = [(m, r) for m, r in match_codes(slam, family) if wanted is None or m in wanted]
                    for route in routes:
                        if only_routes and route not in only_routes:
                            continue
                        note = fetch_family(client, receipts, cal, slam, year, route, family, codes, args, outcomes)
                        if note:
                            skipped.append(note)
                            P.log(f"[{SOURCE}] {edition} {family} on {route}: given up ({note['reason']})")
                    P.log(f"[{SOURCE}] {edition} {family} done; requests={client.requests}; "
                          + ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items()) if k.startswith(edition)))
        except (P.Blocked, P.BudgetExhausted, F.Stopped) as stop:
            summary["stopped"] = f"{type(stop).__name__}: {stop}"
            P.log(f"[{SOURCE}] STOPPED: {stop}")
        summary["client"] = client.stats()
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    summary["families_given_up"] = skipped
    if not args.no_stage:
        try:
            summary["staged"] = stage(receipts, editions)
            summary["by_edition_family"] = summarize(editions)
        except Exception as err:  # keep the run's record: its fetches are done and cached whatever staging does
            summary["stopped"] = f"staging failed: {type(err).__name__}: {err}"
            P.log(f"[{SOURCE}] STAGING FAILED ({type(err).__name__}: {err}); the fetched files are kept; "
                  "fix and rerun with --stage-only")
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts"] = dict(sorted(Counter(
        f"{'/'.join(r['name'].split('/')[:3])}:{outcome_of(r)}" for r in receipts.all().values()).items()))
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = P.write_summary("infosys_slams_summary.json", summary,
                           root=Path(args.summary_dir) if args.summary_dir else STUDY_ROOT)
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--editions", help=f"comma list (default: all of {','.join(EDITIONS)})")
    parser.add_argument("--families", help="comma list of match families, e.g. MS,WS or SM,SD (default: all)")
    parser.add_argument("--matches", help="comma list of match ids (default: every code of the families)")
    parser.add_argument("--routes", help=f"comma list of routes to fetch (default: each edition's own; known: "
                                         f"{', '.join(ROUTES)})")
    parser.add_argument("--max-requests", type=int, default=2400, help="stop after this many HTTP requests")
    parser.add_argument("--min-interval", type=float, default=2.0, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=1.0, help="up to this many extra seconds, drawn at random")
    parser.add_argument("--skip-family-after", type=int, default=8,
                        help="give a family up on a route when its first N codes are all absent (0: never)")
    parser.add_argument("--refresh", action="store_true", help="fetch files already held (and absences) again")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; decrypt the raw files and rebuild the tables")
    parser.add_argument("--no-stage", action="store_true", help="fetch only")
    parser.add_argument("--summary-dir", help=f"folder for the run summary (default: {P.rel(STUDY_ROOT)})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    P.log(f"[{SOURCE}] done in {summary['seconds']} s; {summary['receipts_with_errors']} receipts with errors"
          + (f"; stopped: {summary['stopped']}" if summary.get("stopped") else ""))
    return 1 if summary.get("stopped") or summary["receipts_with_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())

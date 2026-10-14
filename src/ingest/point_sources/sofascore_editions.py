"""SofaScore by tournament edition: the point-by-point record and box score of every match in a data-map gap.

The player adapter (sofascore.py) lists SofaScore one player at a time. A gap on the data map is a set of
known matches that lack a level of detail, so this lists SofaScore one tournament edition at a time, the
route src/eda/gap_sources/sofascore_probe.py measured on a sample on 29 Sep 2026 (for the ATP tour-level
gap: 450 of 452 listed, complete points for 34 of 36 checked; docs/research/gap-sources/README.md).

1. **Targets.** The gap's matches: its ``select`` under ``gaps:`` in data/data_map.yaml applied to
   data/studies/data_map/matches.parquet (best grain below ``below``). The first run freezes them in
   data/studies/gap_downloads/sofascore_<gap>_matches.csv (gzipped, .csv.gz, for the big ITF gaps of P7),
   because what this collects lifts matches out of the gap once the map is rebuilt; --refresh-targets
   derives them again.
2. **Editions.** The targets grouped by tour, tournament, year and ISO week of the tournament start.
3. **Locate.** SofaScore's day listing of the edition's category on a few days of its week; the
   tournament season whose singles events name the most of the edition's known matches is taken.
4. **List.** Every event of that season, 30 a page (qualifying included).
5. **Link.** Each target to the singles event whose players both share a name word with it, starting
   10 days before to 21 after the tournament start; on a tie, the one in the target's draw, then one its winner
   won (Tennis My Life's and Sackmann's matches name the winner first), then one that was played. A target is
   left unlinked when its event names another of the edition's known matches better (its own match is then not
   in the listing).
6. **Fetch.** ``/point-by-point`` for every linked event, newest first; then ``/statistics``. If SofaScore
   blocks the run part-way, the points are what it has. With --defer-uncovered, events SofaScore lists with
   ``coverage: -1`` are left for a later run (P7: almost every ITF event of January 2025 to February 2026, which
   hold no record); the evidence marks them "deferred (coverage -1)".

Endpoints (public JSON behind SofaScore's site, no key; observed 29 Sep 2026):
    /api/v1/sport/tennis/<date>/0/categories                    categories with events that day (WTA 125 only)
    /api/v1/category/<id>/scheduled-events/<date>               that day's events
    /api/v1/unique-tournament/<id>/season/<id>/events/last/<n>  30 events a page, newest first
    /api/v1/event/<id>/point-by-point, /api/v1/event/<id>/statistics   HTTP 404 when absent

Raw, verbatim JSON gzipped, with receipts (data/raw/point_sources/sofascore_editions/, gitignored):
    categories/<date>.json.gz  day/<category>/<date>.json.gz  season/<utid>_<sid>/last_<n>.json.gz
    events/<event_id>/point-by-point.json.gz  events/<event_id>/statistics.json.gz  _receipts.jsonl
Staged (data/dump/points/sofascore_editions/, all strings): events.parquet (every event of the located
seasons, sofascore.py's columns plus the season it was listed in), points.parquet, statistics.parquet; each
streamed to Parquet as the raw files are read (the ITF gaps hold tens of millions of points).
Evidence (data/studies/gap_downloads/): sofascore_<gap>_matches.csv (each target, its event, what was
fetched; .csv.gz for the gaps in GZIPPED), sofascore_<gap>_editions.csv, sofascore_<gap>_summary.json, runs.jsonl.

Pace and stops are common.Client's: a Chrome TLS fingerprint, one request at a time, a minimum interval
with jitter, a --max-requests budget, and a stop on HTTP 403, 429 or a challenge. Every answer is cached
with a receipt, so a rerun asks only for what is missing. When SofaScore challenges the plain client,
--browser makes the same requests inside a Chrome tab the owner opened (browser.py; the Chrome command is
in docs/studies/gap_downloads/README.md). SofaScore's terms forbid automated extraction; collected on the
owner's decision of 23 Sep 2026 (docs/studies/point_shot_sources/README.md#direct-download-24-september-2026).

Usage:
    ./python.sh -m src.ingest.point_sources.sofascore_editions                    # the ATP tour-level gap
    ./python.sh -m src.ingest.point_sources.sofascore_editions --limit 3 --max-requests 60   # a trial
    ./python.sh -m src.ingest.point_sources.sofascore_editions --gap itf_detail --editions "M|M15 Monastir|2024|w50"
                                                                                  # a trial at chosen editions
    ./python.sh -m src.ingest.point_sources.sofascore_editions --browser          # inside a Chrome tab
    ./python.sh -m src.ingest.point_sources.sofascore_editions --stage-only       # no HTTP: rebuild from raw
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import sofascore as S

SOURCE = "sofascore_editions"
API = S.API
MATCHES = P.PROJECT_ROOT / "data" / "studies" / "data_map" / "matches.parquet"
CATALOG = P.PROJECT_ROOT / "data" / "data_map.yaml"
STUDY = P.PROJECT_ROOT / "data" / "studies" / "gap_downloads"
DEFAULT_GAP = "atp_points_2025"
PARTS = ("point-by-point", "statistics")
# the big ITF gaps (work package P7, ~200,000 targets): their per-target tables are written gzipped (~60 MB plain)
GZIPPED = {"itf_points_2025_2026", "itf_detail"}

GRAIN_RANK = {"result": 1, "stats": 2, "point": 3, "shot": 4}
DEFERRED = "deferred (coverage -1)"   # a part left for a later run by --defer-uncovered
# SofaScore category ids (observed 29 Sep 2026); WTA 125 is read from the day's category list
FIXED_CATEGORY = {("M", "ITF"): 785, ("W", "ITF"): 213, ("M", "CH"): 72, ("M", "tour"): 3, ("W", "tour"): 6}
# days after the tournament start whose listing is read, in order, until the edition is found; the last two look
# at the week before, where Tennis My Life dates some Challengers a week late (Targu Mures and Manama, 2025)
OFFSETS = {"ITF": [2, 4, 1, 5], "CH": [2, 4, 1, 5, -1, -3, -5], "CHQ": [0, -1, 1, 2, -3, -5],
           "tour": [2, 4, 1, 6, 0, -1, -3, -5], "GS": [2, 5, 8, 11, 0]}
FULL_BOX = {"aces", "doubleFaults", "firstServeAccuracy", "firstServePointsAccuracy", "secondServePointsAccuracy",
            "breakPointsSaved"}
PARTICLES = {"jr", "sr", "ii", "iii", "iv", "de", "da", "van", "von", "del", "der", "la", "le", "di", "dos", "du"}
MAX_SEASON_PAGES = 25  # safety stop per season: 750 events
LINK_DAYS = (-10, 21)
WINNER_FIRST = {"tml", "sackmann"}  # the map's matches from these files name the winner first (winner_name)

TARGET_COLUMNS = ["gap", "edition", "uid", "tour", "level", "draw", "year", "d", "tname", "name1", "name2",
                  "creator", "best", "sources"]
LINK_COLUMNS = ["listed", "event_id", "link_score", "utid", "sid", "ss_tournament", "ss_home", "ss_away",
                "ss_round", "ss_start_utc", "ss_status", "ss_winner_code", "ss_first_to_serve", "link_note"]
FETCH_COLUMNS = ["pbp_status", "pbp_sets", "pbp_games", "pbp_points", "score_games", "pbp_verdict",
                 "stats_status", "stats_keys", "stats_full_box"]
EDITION_COLUMNS = ["gap", "edition", "tour", "tname", "year", "levels", "d_min", "d_max", "targets", "known", "utid",
                   "sid", "ss_tournament", "located_by", "locate_hits", "locate_tried", "season_pages", "season_events",
                   "season_singles", "targets_linked"]
INTEGER_COLUMNS = ["event_id", "link_score", "utid", "sid", "ss_winner_code", "ss_first_to_serve", "pbp_sets",
                   "pbp_games", "pbp_points", "score_games", "stats_keys"]
EVENT_COLUMNS = [c for c in S.EVENT_COLUMNS if c not in ("listed_for_teams", "listed_pages", "listing_file")] + [
    "listed_in_season", "listing_file"]


# --------------------------------------------------------------------------------------
# names and linking (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def words(name) -> frozenset:
    """Lower-case ASCII name words of three letters or more, particles left out; the two-letter words when a
    name has no longer one (Li Tu)."""
    text = "".join(ch for ch in unicodedata.normalize("NFKD", str(name or "")) if not unicodedata.combining(ch))
    parts = [w for w in re.split(r"[^a-z]+", text.lower()) if w and w not in PARTICLES]
    return frozenset(w for w in parts if len(w) >= 3) or frozenset(w for w in parts if len(w) == 2)


def team_words(team: dict) -> frozenset:
    return words(team.get("name")) | words(team.get("shortName")) | words((team.get("slug") or "").replace("-", " "))


def pair_score(a: frozenset, b: frozenset, home: frozenset, away: frozenset) -> int:
    """Name words the two pairs share in the better orientation; 0 unless both players share a word."""
    best = 0
    for x, y in ((home, away), (away, home)):
        s1, s2 = len(a & x), len(b & y)
        if s1 and s2:
            best = max(best, s1 + s2)
    return best


def singles(events: list[dict]) -> list[dict]:
    """The singles events, each with its players' name words attached (``_hw``, ``_aw``)."""
    out = []
    for event in events:
        if S.is_doubles(event):
            continue
        event["_hw"] = team_words(event.get("homeTeam") or {})
        event["_aw"] = team_words(event.get("awayTeam") or {})
        out.append(event)
    return out


def is_qualifying(event: dict) -> bool:
    """SofaScore files qualifying under its own round names or a tournament name ending ', Qualifying'; some
    qualifying events carry no round name at all (Roland Garros 2023)."""
    return ("qualif" in str(S._dig(event, ("roundInfo", "name")) or "").lower()
            or "qualifying" in str(S._dig(event, ("tournament", "name")) or "").lower())


def is_played(event: dict) -> bool:
    """SofaScore also lists matches that never took place (cancelled, postponed), at times beside the same pair's
    played one a day or a round later (Sofia, Sumter, Buenos Aires and Kobe Challengers, 2025)."""
    return S._dig(event, ("status", "type")) == "finished"


def won_by(event: dict, winner: frozenset) -> bool:
    """Whether the event's winning side (``winnerCode``) shares a name word with ``winner``."""
    side = {1: "_hw", 2: "_aw"}.get(event.get("winnerCode"))
    return bool(side and event[side] & winner)


def best_event(a: frozenset, b: frozenset, d0: pd.Timestamp, d1: pd.Timestamp, events: list[dict],
               draw: str | None = None, winner: frozenset | None = None):
    """(event, score): the singles event sharing the most name words with (a, b) in the date window; on a tie,
    the one in the same draw (``qual`` or ``main``, when given; two players can meet in the qualifying and
    again in the main draw), then one ``winner`` won (when given; at the Finals a pair can meet in the round
    robin and again in the final), then one that was played, then the one nearest the tournament start.
    (None, 0) when none shares a word with both players.

    A shared first name is enough for one player, by design: SofaScore shows a player's current name on old
    matches (married names: Jaksic now Jovic, Rueffer now Papadakis), and a check of surnames lost about 150
    correct links in the first five gaps of P6 to remove about 30 wrong ones (11 Oct 2026)."""
    best, best_key = None, None
    lo, hi = (d0 + pd.Timedelta(days=LINK_DAYS[0])).timestamp(), (d1 + pd.Timedelta(days=LINK_DAYS[1])).timestamp()
    for event in events:
        ts = event.get("startTimestamp") or 0
        if not lo <= ts <= hi:
            continue
        score = pair_score(a, b, event["_hw"], event["_aw"])
        if score:
            same_draw = draw is None or (draw == "qual") == is_qualifying(event)
            won = winner is None or won_by(event, winner)
            key = (score, same_draw, won, is_played(event), -abs(ts - d0.timestamp()))
            if best_key is None or key > best_key:
                best, best_key = event, key
    return best, (best_key[0] if best_key else 0)


def claimed_by_other(event: dict, score: int, known: pd.DataFrame) -> bool:
    """True when one of the edition's known matches shares more name words with the event than the target does:
    the event is that match, and the target's own is not in the listing. (Costa do Sauipe 2025: Gima v Hernandez
    Serrano took the event of Gima v Varillas through the shared first name Juan.)"""
    return any(pair_score(a, b, event["_hw"], event["_aw"]) > score for a, b in zip(known["w1"], known["w2"]))


def level_group(levels) -> str:
    """Which category and listing days an edition needs, from its levels."""
    lv = set(levels)
    if lv & {"ITF", "ITFQ"}:
        return "ITF"
    if lv == {"CHQ"}:
        return "CHQ"
    if lv & {"CH", "CHQ"}:
        return "CH"
    if lv & {"GS", "GSQ"}:
        return "GS"
    return "tour"


def pbp_verdict(pbp: list, event: dict) -> dict:
    """Compare a point record's games per set with the event's set scores.

    *complete*: every set has as many games as its score; *complete to retirement*: one game more at a
    retirement (the record also lists the game in progress); *short*: games missing; else *other*."""
    sets = sorted(pbp, key=lambda s: s.get("set") or 0)
    games = {s.get("set"): len(s.get("games") or []) for s in sets}
    points = sum(len(g.get("points") or []) for s in sets for g in s.get("games") or [])
    hs, as_ = event.get("homeScore") or {}, event.get("awayScore") or {}
    want = {}
    for n in range(1, 6):
        h, a = hs.get(f"period{n}"), as_.get(f"period{n}")
        if h is not None and a is not None:
            want[n] = int(h) + int(a)
    status = event.get("status") or {}
    retired = status.get("code") == 92 or "retired" in str(status.get("description") or "").lower()
    extra = sum(games.values()) - sum(want.values())
    if not want:
        verdict = "no score to compare"
    elif all(games.get(n) == g for n, g in want.items()) and len(games) == len(want):
        verdict = "complete"
    elif retired and 0 <= extra <= 1:
        verdict = "complete to retirement"
    elif all(games.get(n, 0) <= g for n, g in want.items()):
        verdict = "short"
    else:
        verdict = "other"
    return {"pbp_sets": len(sets), "pbp_games": sum(games.values()), "pbp_points": points,
            "score_games": sum(want.values()), "pbp_verdict": verdict}


def uncovered(event: dict) -> bool:
    """SofaScore's own mark of an event it holds no detail for, ``coverage: -1`` in its listing. Observed 13 Oct 2026 on
    almost every ITF singles event of January 2025 to February 2026; of 1,403 flagged events fetched in P6 and P7, 8 had
    a point record. Events without the mark can lack records too (Challengers of 2022-23)."""
    return event.get("coverage") == -1


def stats_check(statistics: list) -> dict:
    keys = set()
    for period in statistics:
        if period.get("period") == "ALL":
            for group in period.get("groups") or []:
                keys |= {item.get("key") for item in group.get("statisticsItems") or []}
    return {"stats_keys": len(keys), "stats_full_box": FULL_BOX <= keys}


# --------------------------------------------------------------------------------------
# targets
# --------------------------------------------------------------------------------------
def gap_select(gap: str) -> dict:
    gaps = {g["id"]: g for g in yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["gaps"]}
    if gap not in gaps:
        raise SystemExit(f"no gap '{gap}' in {P.rel(CATALOG)}; known: {', '.join(gaps)}")
    if "below" not in gaps[gap]["select"]:   # a `missing` gap's matches are not in the map's list to link
        raise SystemExit(f"gap '{gap}' has no `below` grain: its matches are not in the map's list")
    return gaps[gap]["select"]


def in_select(m: pd.DataFrame, select: dict) -> pd.Series:
    sel = m["tour"].isin(select["tours"]) & m["level"].isin(select["levels"]) & m["year"].isin(select["years"])
    return sel & (m["best"].map(GRAIN_RANK) < GRAIN_RANK[select["below"]])


def edition_key(frame: pd.DataFrame) -> pd.Series:
    """Tour, tournament name, year and ISO week of the tournament start (the map's ``d``)."""
    week = pd.to_datetime(frame["d"]).dt.isocalendar().week.astype(str).str.zfill(2)
    return frame["tour"] + "|" + frame["tname"].fillna("") + "|" + frame["year"].astype(str) + "|w" + week


def table_path(gap: str, kind: str) -> Path:
    """A gap's per-target table (``matches``; ``link_check``, verify_links.py's): sofascore_<gap>_<kind>.csv, gzipped
    for the gaps in GZIPPED."""
    return STUDY / f"sofascore_{gap}_{kind}.csv{'.gz' if gap in GZIPPED else ''}"


def targets_path(gap: str) -> Path:
    return table_path(gap, "matches")


def load_targets(gap: str, refresh: bool) -> tuple[pd.DataFrame, str]:
    """The gap's matches: frozen in the evidence table after the first run, else derived from the map."""
    path = targets_path(gap)
    if path.exists() and not refresh:
        t = pd.read_csv(path, usecols=TARGET_COLUMNS, parse_dates=["d"], keep_default_na=False, na_values=[""])
        return t, f"frozen in {P.rel(path)}"
    m = pd.read_parquet(MATCHES)
    t = m[in_select(m, gap_select(gap))].copy()
    t.insert(0, "gap", gap)
    t["edition"] = edition_key(t)
    built = dt.datetime.fromtimestamp(MATCHES.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return t[TARGET_COLUMNS].sort_values(["d", "edition", "uid"]).reset_index(drop=True), f"derived from {P.rel(MATCHES)} built {built}"


def known_matches(targets: pd.DataFrame) -> pd.DataFrame:
    """The map's matches of the targets' tournaments, gap or not, to locate editions with; the targets alone
    when the map's table is absent."""
    if not MATCHES.exists():
        return targets[["tour", "tname", "year", "d", "name1", "name2"]].copy()
    m = pd.read_parquet(MATCHES, columns=["tour", "tname", "year", "d", "name1", "name2"])
    keys = targets[["tour", "tname", "year"]].drop_duplicates()
    return m.merge(keys, on=["tour", "tname", "year"])


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
class Lister:
    """SofaScore's answers, fetched with receipts or (offline) read from the cache only."""

    def __init__(self, client, receipts, offline: bool):
        self.client, self.receipts, self.offline = client, receipts, offline

    def get(self, url: str, rel_path: str, name: str):
        dest = P.raw_path(SOURCE, rel_path)
        if self.offline:
            r = self.receipts.get(name) or {}
        else:
            r = P.fetch(self.client, url, dest, self.receipts, name=name, validator=P.json_validator,
                        compress=dest.suffix == ".gz")
        if r.get("status") == 200 and not r.get("error") and dest.exists():
            return P.read_json(dest)
        return None

    def status(self, name: str):
        r = self.receipts.get(name) or {}
        return r.get("error") or r.get("status") or ("not fetched" if not r else None)

    def categories(self, day: str) -> list[dict]:
        doc = self.get(f"{API}/sport/tennis/{day}/0/categories", f"categories/{day}.json.gz", f"categories/{day}")
        return (doc or {}).get("categories") or []

    def day_events(self, category: int, day: str) -> list[dict]:
        doc = self.get(f"{API}/category/{category}/scheduled-events/{day}", f"day/{category}/{day}.json.gz",
                       f"day/{category}/{day}")
        return (doc or {}).get("events") or []

    def season_events(self, utid: int, sid: int) -> tuple[list[dict], int]:
        events, pages = [], 0
        for page in range(MAX_SEASON_PAGES):
            doc = self.get(f"{API}/unique-tournament/{utid}/season/{sid}/events/last/{page}",
                           f"season/{utid}_{sid}/last_{page}.json.gz", f"season/{utid}_{sid}/last_{page}")
            if doc is None:
                break
            pages += 1
            events.extend(doc.get("events") or [])
            if not doc.get("hasNextPage"):
                break
        return events, pages

    def event_part(self, event_id, part: str):
        return self.get(f"{API}/event/{event_id}/{part}", f"events/{event_id}/{part}.json.gz", f"events/{event_id}/{part}")


def category_for(lister: Lister, tour: str, group: str, day: str) -> int:
    key = (tour, "CH" if group in ("CH", "CHQ") else "ITF" if group == "ITF" else "tour")
    if key in FIXED_CATEGORY:
        return FIXED_CATEGORY[key]
    for c in lister.categories(day):   # WTA 125: its category carries "125" in its name
        if "125" in (c.get("category") or {}).get("name", ""):
            return c["category"]["id"]
    return FIXED_CATEGORY[(tour, "tour")]


def locate(lister: Lister, tour: str, levels, d0: pd.Timestamp, d1: pd.Timestamp, known: pd.DataFrame) -> dict:
    """The SofaScore tournament season holding an edition: read day listings until one names enough of its
    known matches (two, or one when fewer than four are known)."""
    group = level_group(levels)
    need = 2 if len(known) >= 4 else 1
    tried = []
    for off in OFFSETS[group]:
        day = (d0 + pd.Timedelta(days=off)).strftime("%Y-%m-%d")
        cat = category_for(lister, tour, group, day)
        events = singles(lister.day_events(cat, day))
        tried.append(f"{cat}/{day}:{len(events)}")
        hits, names = Counter(), {}
        for a, b in zip(known["w1"], known["w2"]):
            event, _ = best_event(a, b, d0, d1, events)
            if event is not None:
                key = (S._dig(event, ("tournament", "uniqueTournament", "id")), S._dig(event, ("season", "id")))
                hits[key] += 1
                names[key] = S._dig(event, ("tournament", "name"))
        if hits:
            key, n = hits.most_common(1)[0]
            if n >= need and key[0] and key[1]:
                return {"utid": key[0], "sid": key[1], "ss_tournament": names[key], "located_by": f"{cat}/{day}",
                        "locate_hits": n, "locate_tried": ";".join(tried)}
    return {"utid": None, "sid": None, "ss_tournament": None, "located_by": None, "locate_hits": 0,
            "locate_tried": ";".join(tried)}


def link_row(event, score: int, loc: dict) -> dict:
    row = {"listed": event is not None, "link_score": score or None, "utid": loc.get("utid"), "sid": loc.get("sid"),
           "ss_tournament": loc.get("ss_tournament")}
    if event is not None:
        ts = event.get("startTimestamp")
        row.update(event_id=event.get("id"), ss_home=S._dig(event, ("homeTeam", "name")),
                   ss_away=S._dig(event, ("awayTeam", "name")), ss_round=S._dig(event, ("roundInfo", "name")),
                   ss_start_utc=dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else None,
                   ss_status=S._dig(event, ("status", "description")), ss_winner_code=event.get("winnerCode"),
                   ss_first_to_serve=event.get("firstToServe"))
    return row


def list_and_link(lister: Lister, targets: pd.DataFrame, known: pd.DataFrame, limit: int | None = None,
                  log_every: int = 10, only: set | None = None):
    """Locate and list every edition, newest first, and link its targets; with ``only``, only the editions named
    (their keys, as in the editions table), and with ``limit``, only the newest ``limit`` of those; the others'
    targets stay unlinked. Returns (edition rows, target rows, linked events)."""
    ed_rows, rows, linked = [], [], {}
    editions = targets.sort_values("d", ascending=False, kind="stable").groupby("edition", sort=False)
    tried = 0
    for i, (edition, em) in enumerate(editions, 1):
        tour, tname, year = em["tour"].iloc[0], em["tname"].iloc[0], int(em["year"].iloc[0])
        d0, d1 = pd.Timestamp(em["d"].min()), pd.Timestamp(em["d"].max())
        kn = known[(known["tour"] == tour) & (known["tname"] == tname) & (known["year"] == year)
                   & known["d"].between(d0 - pd.Timedelta(days=3), d1 + pd.Timedelta(days=3))]
        kn = kn if len(kn) else em
        skip = ("not in --editions" if only is not None and edition not in only
                else "beyond --limit" if limit is not None and tried >= limit else None)
        if skip:
            loc = {"utid": None, "sid": None, "ss_tournament": None, "located_by": None, "locate_hits": 0,
                   "locate_tried": f"not tried: {skip}"}
        else:
            tried += 1
            loc = locate(lister, tour, em["level"].unique(), d0, d1, kn)
        events, pages = lister.season_events(int(loc["utid"]), int(loc["sid"])) if loc["utid"] else ([], 0)
        season_singles = singles(events)
        n_linked = 0
        for t in em.itertuples(index=False):
            winner = t.w1 if t.creator in WINNER_FIRST else None
            event, score = best_event(t.w1, t.w2, d0, d1, season_singles, t.draw, winner) if season_singles else (None, 0)
            note = None
            if event is not None and claimed_by_other(event, score, kn):
                note = f"event {event.get('id')} names another known match better"
                event, score = None, 0
            rows.append({**{c: getattr(t, c) for c in TARGET_COLUMNS}, **link_row(event, score, loc), "link_note": note})
            if event is not None:
                n_linked += 1
                linked[event["id"]] = event
        ed_rows.append({"gap": em["gap"].iloc[0], "edition": edition, "tour": tour, "tname": tname, "year": year,
                        "levels": ";".join(sorted(em["level"].unique())), "d_min": d0.date(), "d_max": d1.date(),
                        "targets": len(em), "known": len(kn), **loc, "season_pages": pages,
                        "season_events": len(events), "season_singles": len(season_singles), "targets_linked": n_linked})
        if i % log_every == 0 or i == editions.ngroups:
            P.log(f"[{SOURCE}] {i}/{editions.ngroups} editions; {sum(r['listed'] for r in rows)}/{len(rows)} targets "
                  f"linked; requests={getattr(lister.client, 'requests', 0)}")
    return ed_rows, rows, linked


def fetch_parts(lister: Lister, events: dict, parts, log_every: int = 100) -> Counter:
    """Each part for every linked event, newest first, one part after the other."""
    order = sorted(events, key=lambda eid: -(events[eid].get("startTimestamp") or 0))
    outcomes = Counter()
    for part in parts:
        for n, event_id in enumerate(order, 1):
            name = f"events/{event_id}/{part}"
            before = lister.receipts.get(name)
            lister.event_part(event_id, part)
            outcome = lister.status(name)
            outcomes[f"{part}:{outcome}" + (":cached" if before and lister.receipts.get(name) is before else "")] += 1
            if n % log_every == 0 or n == len(order):
                P.log(f"[{SOURCE}] {part}: {n}/{len(order)}; requests={lister.client.requests}; " +
                      ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items()) if k.startswith(part)))
    return outcomes


def fetch_results(lister: Lister, rows: list[dict], linked: dict, defer: bool = False) -> None:
    """What was fetched for each linked target: statuses, record shape and completeness, box score. With ``defer``, a
    part never asked for of an event marked uncovered is "deferred (coverage -1)" rather than "not fetched"."""
    for row in rows:
        row.update({c: None for c in FETCH_COLUMNS})
        if not row["listed"]:
            continue
        event_id, event = row["event_id"], linked[row["event_id"]]
        row["pbp_status"] = lister.status(f"events/{event_id}/point-by-point")
        row["stats_status"] = lister.status(f"events/{event_id}/statistics")
        if defer and uncovered(event):
            for key in ("pbp_status", "stats_status"):
                if row[key] == "not fetched":
                    row[key] = DEFERRED
        path = P.raw_path(SOURCE, "events", str(event_id), "point-by-point.json.gz")
        if row["pbp_status"] == 200 and path.exists():
            row.update(pbp_verdict(P.read_json(path).get("pointByPoint") or [], event))
        path = P.raw_path(SOURCE, "events", str(event_id), "statistics.json.gz")
        if row["stats_status"] == 200 and path.exists():
            row.update(stats_check(P.read_json(path).get("statistics") or []))


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def season_listings() -> dict[int, dict]:
    """Every event of every season listing on disk, keyed by event id, with the season and file it came from."""
    events: dict[int, dict] = {}
    root = P.raw_path(SOURCE, "season")
    if not root.exists():
        return events
    for folder in sorted(root.iterdir()):
        pages = sorted(folder.glob("last_*.json.gz"), key=lambda p: int(p.name.split("_")[1].split(".")[0]))
        for path in pages:
            for event in P.read_json(path).get("events") or []:
                events.setdefault(event["id"], {"event": event, "season": folder.name, "file": P.rel(path)})
    return events


def stage(receipts) -> dict:
    """Rebuild the staged tables from every season listing and event document on disk.

    Each table is streamed to Parquet as the raw files are read: the points first, then the statistics, then the
    events, which carry each record's shape. The ITF gaps of P7 hold tens of millions of point rows, too many to
    gather in memory first."""
    listed = season_listings()
    order = sorted(listed, key=lambda eid: -(listed[eid]["event"].get("startTimestamp") or 0))
    shapes, periods = {}, {}

    def documents(part: str):
        """(event_id, provenance, document) for every event whose ``part`` is on disk, in the events' order."""
        for event_id in order:
            r = receipts.get(f"events/{event_id}/{part}") or {}
            path = P.raw_path(SOURCE, "events", str(event_id), f"{part}.json.gz")
            if r.get("status") == 200 and path.exists():
                yield event_id, {"source_file": P.rel(path), "source_sha256": r.get("sha256"),
                                 "retrieved_at": r.get("retrieved_at")}, P.read_json(path)

    def point_rows():
        for event_id, provenance, doc in documents("point-by-point"):
            pbp = doc.get("pointByPoint") or []
            shapes[event_id] = S.pbp_shape(pbp)
            for p in S.point_rows(event_id, pbp):
                yield {**p, **provenance}

    def stat_rows():
        for event_id, provenance, doc in documents("statistics"):
            statistics = doc.get("statistics") or []
            periods[event_id] = ";".join(str(p.get("period")) for p in statistics)
            for s in S.statistic_rows(event_id, statistics):
                yield {**s, **provenance}

    def event_rows():
        for event_id in order:
            entry = listed[event_id]
            row = S.flatten_event(entry["event"])
            row.update(listed_in_season=entry["season"], listing_file=entry["file"])
            for part, prefix in (("point-by-point", "pbp"), ("statistics", "stats")):
                r = receipts.get(f"events/{event_id}/{part}") or {}
                row[f"{prefix}_status"] = r.get("error") or r.get("status")
                row[f"{prefix}_retrieved_at"], row[f"{prefix}_sha256"] = r.get("retrieved_at"), r.get("sha256")
            if event_id in shapes:
                shape = shapes[event_id]
                row.update(pbp_sets=shape["sets"], pbp_games=shape["games"], pbp_points=shape["points"])
            if event_id in periods:
                row["stats_periods"] = periods[event_id]
            yield row

    now = P.utc_now_iso()
    out = {}
    for name, columns, rows in (("points", S.POINT_COLUMNS, point_rows()), ("statistics", S.STAT_COLUMNS, stat_rows()),
                                ("events", EVENT_COLUMNS, event_rows())):
        dest = P.dump_path(SOURCE, f"{name}.parquet")
        stats = P.stage_table(SOURCE, dest, columns, ([P.s(r.get(c)) for c in columns] for r in rows),
                              source_file=P.rel(P.raw_path(SOURCE)), retrieved_at=now)
        out[name] = {"rows": stats["rows"], "dest": stats["dest"], "bytes": stats["bytes"]}
        P.log(f"[{SOURCE}] staged {stats['dest']}: {stats['rows']:,} rows")
    return {name: out[name] for name in ("events", "points", "statistics")}


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def make_client(args):
    """The plain Chrome-fingerprint client, or with --browser the same requests inside a Chrome tab the owner
    opened with a debugging port (browser.py)."""
    if args.browser:
        from src.ingest.point_sources import browser as B

        return B.BrowserClient(args.browser, origin=S.SITE, url_map={S.API_HOST + "/": S.SITE + "/"},
                               token_key="sofa.captcha.token", min_interval=args.min_interval, jitter=args.jitter,
                               max_requests=args.max_requests, headers={"Accept": "*/*"})
    return P.Client(S.IMPERSONATE, min_interval=args.min_interval, jitter=args.jitter, max_requests=args.max_requests,
                    headers=S.HEADERS)


def tally(rows: pd.DataFrame, editions: pd.DataFrame) -> dict:
    """Counts for the summary: overall and by year and level."""
    def cell(g: pd.DataFrame) -> dict:
        return {"targets": int(len(g)), "listed": int(g["listed"].sum()),
                "points_any": int(g["pbp_status"].eq(200).sum()),
                "points_complete": int(g["pbp_verdict"].isin(["complete", "complete to retirement"]).sum()),
                "points_absent": int(g["pbp_status"].eq(404).sum()),
                "points_not_fetched": int((g["listed"] & g["pbp_status"].eq("not fetched")).sum()),
                "points_deferred": int(g["pbp_status"].eq(DEFERRED).sum()),
                "full_box_score": int(g["stats_full_box"].eq(True).sum()),
                "stats_any": int(g["stats_status"].eq(200).sum())}
    out = {"all": cell(rows), "editions": int(len(editions)), "editions_located": int(editions["utid"].notna().sum()),
           "by_year_level": {f"{y}|{lv}": cell(g) for (y, lv), g in rows.groupby(["year", "level"])},
           "pbp_verdicts": {str(k): int(v) for k, v in rows["pbp_verdict"].value_counts(dropna=False).items()}}
    missing = editions[editions["utid"].isna()]
    out["editions_not_located"] = missing[["edition", "locate_tried"]].to_dict(orient="records")
    return out


def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    STUDY.mkdir(parents=True, exist_ok=True)
    targets, origin = load_targets(args.gap, args.refresh_targets)
    only = set(args.editions) if args.editions else None
    if only is not None and not only <= set(targets["edition"]):
        raise SystemExit(f"--editions: not editions of gap {args.gap}: {', '.join(sorted(only - set(targets['edition'])))}")
    P.log(f"[{SOURCE}] gap {args.gap}: {len(targets):,} target matches in {targets['edition'].nunique()} editions ({origin})")
    targets_file = targets_path(args.gap)
    if not targets_file.exists() or args.refresh_targets:   # freeze the targets before anything is fetched
        targets.assign(d=targets["d"].dt.date).to_csv(targets_file, index=False)
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "gap": args.gap, "targets_from": origin, "started_at": P.utc_now_iso(),
               "args": vars(args)}
    client = None if args.stage_only else make_client(args)
    lister = Lister(client, receipts, offline=args.stage_only)
    if client is not None:
        P.log(f"[{SOURCE}] requests via {client.impersonate}; budget {args.max_requests}; "
              f"interval {args.min_interval}s + up to {args.jitter}s")
    targets = targets.assign(w1=targets["name1"].map(words), w2=targets["name2"].map(words))
    known = known_matches(targets)
    known = known.assign(w1=known["name1"].map(words), w2=known["name2"].map(words))
    ed_rows, rows, linked, outcomes = [], [], {}, Counter()
    try:
        ed_rows, rows, linked = list_and_link(lister, targets, known, args.limit, only=only)
        P.log(f"[{SOURCE}] listed: {sum(r['listed'] for r in rows)}/{len(rows)} targets linked to "
              f"{len(linked)} events")
        if not args.stage_only:
            fetch = linked
            if args.defer_uncovered:
                fetch = {eid: e for eid, e in linked.items() if not uncovered(e)}
                P.log(f"[{SOURCE}] deferring {len(linked) - len(fetch)} events SofaScore lists with coverage -1")
            outcomes = fetch_parts(lister, fetch, [p for p in PARTS if p not in (args.skip or ())])
    except (P.Blocked, P.BudgetExhausted) as stop:
        summary["stopped"] = f"{type(stop).__name__}: {stop}"
        P.log(f"[{SOURCE}] STOPPED: {stop}")
        # what the run reached, from the cache: editions it had not listed stay unlinked
        lister.offline = True
        ed_rows, rows, linked = list_and_link(lister, targets, known, args.limit, log_every=10 ** 6, only=only)
    finally:
        if client is not None and hasattr(client, "close"):
            client.close()
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    if client is not None:
        summary["client"] = client.stats()
    fetch_results(lister, rows, linked, defer=args.defer_uncovered)
    frame = pd.DataFrame(rows, columns=TARGET_COLUMNS + LINK_COLUMNS + FETCH_COLUMNS)
    editions = pd.DataFrame(ed_rows, columns=EDITION_COLUMNS)
    for table in (frame, editions):
        for c in INTEGER_COLUMNS:
            if c in table:
                table[c] = pd.to_numeric(table[c], errors="coerce").astype("Int64")
    frame["listed"] = frame["listed"].astype(bool)
    frame.assign(d=pd.to_datetime(frame["d"]).dt.date).sort_values(["d", "edition", "uid"]).to_csv(targets_file, index=False)
    editions.sort_values(["d_min", "edition"]).to_csv(STUDY / f"sofascore_{args.gap}_editions.csv", index=False)
    if not args.no_stage:
        summary["staged"] = stage(receipts)
    summary.update(tally(frame, editions))
    summary["matches_selected"] = int(frame["listed"].sum())
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = P.write_summary(f"sofascore_{args.gap}_summary.json", summary, root=STUDY)
    P.log(f"[{SOURCE}] {json.dumps(summary['all'])}")
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--gap", default=DEFAULT_GAP, help=f"gap id under gaps: in data/data_map.yaml (default {DEFAULT_GAP})")
    parser.add_argument("--refresh-targets", action="store_true",
                        help="derive the gap's matches from the current map instead of the frozen list")
    parser.add_argument("--skip", nargs="*", choices=list(PARTS), help="parts not to fetch")
    parser.add_argument("--defer-uncovered", action="store_true",
                        help="leave events SofaScore lists with coverage -1 (no detail held) for a later run")
    parser.add_argument("--limit", type=int, help="only the N newest editions (trials)")
    parser.add_argument("--editions", nargs="+", metavar="KEY",
                        help="only these editions, by their keys in the editions table, e.g. 'M|M15 Monastir|2024|w50' "
                             "(trials at chosen venues)")
    parser.add_argument("--max-requests", type=int, default=10_000, help="stop after this many HTTP requests")
    parser.add_argument("--min-interval", type=float, default=1.0, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=0.6)
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rebuild the tables from the raw files")
    parser.add_argument("--no-stage", action="store_true", help="fetch only; skip the Parquet rebuild")
    parser.add_argument("--browser", nargs="?", const="http://localhost:9222", metavar="CDP_URL",
                        help="make the requests inside a Chrome tab reached over the DevTools Protocol at this URL "
                             "(bare flag: http://localhost:9222); see src/ingest/point_sources/browser.py")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    return 1 if summary.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())

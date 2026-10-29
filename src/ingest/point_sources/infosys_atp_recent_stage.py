"""Work package P9's ATP Stats Centre files of 2025-2026 (tour level and Challengers), decrypted at staging.

The raw envelopes are infosys_atp_recent.py's, kept as served under data/raw/point_sources/infosys_atp_recent/. The
key statistics of 2026 that the daily speed collector already holds (data/raw/point_sources/infosys_atp_daily/, its
own staging reading the match as completed) are read from there, as work package P9 asks: they were not fetched again.
Decryption is the site's own (infosys_slams.decrypt, approved for every edition: docs/decisions/2026-10-08-scraping-
approved.md), done in memory: no plain copy is written (Court Vision alone would be about 1.4 MB a match); the raw
envelopes are the complete copy and decrypt again the same way.

The guard (``guard``; the plan's step 2): nothing under data/raw/point_sources/infosys_atp/ (the 2015-2021 backfill's
folder) and nothing before 2022 is decrypted here. So these tables stay apart from data/dump/points/infosys_atp/, which
the serve-speed history reads (src/eda/serve_speed_tabpfn/panel.py, live_panel.py).

Tables (data/dump/points/infosys_atp_recent/; strings throughout, as the rest of the dump; every row carries its source
file, the SHA-256 of the body as served and the retrieval time):
    matches.parquet        one row per (year, event, match code) with a file: routes held, players (ATP ids, names,
                           countries), court, status, winner and sets as MatchBeats gives them, the score read from its
                           games, counts (points, timed points, timed first-serve points, classified endings, key-
                           statistic sets and whether they carry a speed, rally entries, Court Vision points), each
                           route's lastModified, and ManTennisData's event name, series, level and start date (the
                           files carry no date)
    points.parquet         every MatchBeats point, its fields verbatim (server, serve number, serve speed, a first-
                           serve fault's speed, scorer, ending, stroke, hand, rally counts, break and crucial-point
                           flags, the match clock), with set and game numbers. Where a match has both copies, the
                           points are the static copy's (its core: the record the rally analysis and box-score checks
                           agree with) and the API's newer-format copy adds, joined by point id, its eight point fields,
                           its own ending (result_newer) and its game's momentum scores (NEWER_COLUMNS); a match with
                           one copy takes its own. The matches table's matchbeats_copy says which; how the two copies
                           differ is counted per match in data/studies/serve_speed_acquisition/
                           infosys_atp_recent_matchbeats_copies.csv.gz
    keystats.parquet       every key statistic of every set ("set0" is the match), the speeds among them
    rally.parquet          every rally-analysis entry (serve speed, direction, court side, ending, shot)
    court_vision.parquet   every Court Vision point record's scalar fields with the served a-number names (a81 the
                           point id, a16 the serve's speed with its unit, a95 the ending ...), its score block (a35)
                           and summary positions (a27-a34) as JSON
    court_vision_shots.parquet   one row per stroke of every Court Vision trajectory (a12, split at each "hit"):
                           the hit, the peak before the bounce, the net crossing, the bounce, the peak after it and the
                           last tracked position, x/y/z in metres, as SirGenkii's per-stroke table has them
    court_vision_matches.parquet one row per Court Vision file with an entry: how many entries it has (one for the
                           whole match in the 2018-21 files; 2026's hold snapshots as the match goes on, 87 for Canada
                           2026's final), each entry's top-level fields (a75-a82) as a JSON list, the players (a79),
                           and the last entry's summary statistics (a49, about 18 KB; each entry's covers the match so
                           far, so the last one's is the match's; the raw file holds them all)
Summary: data/studies/serve_speed_acquisition/infosys_atp_recent_stage_summary.json

Run: ./python.sh -m src.ingest.point_sources.infosys_atp_recent_stage
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import infosys_atp as A
from src.ingest.point_sources import infosys_atp_stage as S
from src.ingest.point_sources import infosys_slams as I

SOURCE = "infosys_atp_recent"
DAILY = "infosys_atp_daily"
DECISION = "docs/decisions/2026-10-08-scraping-approved.md"
RAW = P.raw_path(SOURCE)
DAILY_RAW = P.raw_path(DAILY)
BACKFILL_RAW = P.raw_path("infosys_atp")
FIRST_YEAR = 2022
STUDY_ROOT = P.PROJECT_ROOT / "data" / "studies" / "serve_speed_acquisition"
SUMMARY = STUDY_ROOT / "infosys_atp_recent_stage_summary.json"
# Both MatchBeats copies are kept apart (the API builds a newer format; choose_matchbeats picks one per match); a key
# statistics file and its API twin are the same document, so the static one is kept
KIND = {"keystats": "keystats", "keystats-api": "keystats", "match-beats": "match-beats",
        "match-beats-api": "match-beats-api", "rally-analysis": "rally-analysis", "court-vision": "court-vision"}
PREFER = ("keystats", "match-beats", "rally-analysis", "court-vision", "keystats-api", "match-beats-api")
NEWER_FIELDS = ("firstServer", "lastHitter", "serveClassId", "tm1Shot", "tm2Shot", "pointDuration", "tm1AtNet",
                "tm2AtNet")
CORE_FIELDS = ("pointId", "server", "serve", "serveSpeed", "faultSrvSpd", "scorer", "result", "tm1GameScore",
               "tm2GameScore")
# the points table's columns from the newer copy: its eight point fields, its own ending (beside the static copy's,
# where a match has both), and its game's momentum scores
NEWER_COLUMNS = list(NEWER_FIELDS) + ["result_newer", "game_momentum_tm1", "game_momentum_tm2"]
DIFFERENCES = STUDY_ROOT / "infosys_atp_recent_matchbeats_copies.csv.gz"
KEYS = ["year", "event_id", "match_id"]
PROV = ["source_file", "source_sha256", "retrieved_at"]
CV_FIELDS = S.CV_FIELDS
CV_NESTED = ["a27", "a28", "a29", "a30", "a31", "a32", "a33", "a34"]
SHOT_PARTS = ("hit", "peak_pre", "net", "bounce", "peak_post", "last")
MATCH_COLUMNS = KEYS + [
    "family", "draw", "round_from_code", "series", "level", "tournament_name", "tournament_start", "routes",
    "files", "event_type", "court_id", "court_name", "is_match_complete", "match_status", "match_winner",
    "sets_completed", "score_from_points", "winner_from_points", "matchbeats_copy", "p1_id", "p1_name",
    "p1_first_name", "p1_last_name", "p1_country", "p2_id",
    "p2_name", "p2_first_name", "p2_last_name", "p2_country", "keystats_p1_id", "keystats_p2_id", "points",
    "points_timed", "first_serve_points_timed", "points_classified", "keystats_sets", "keystats_speed",
    "rally_entries", "rally_timed", "cv_points", "cv_timed", "last_modified_utc", "route_last_modified",
    "source_files", "source_sha256", "retrieved_at"]


class Refused(RuntimeError):
    """A file this staging must not decrypt (the guard)."""


def guard(path: Path | str, year) -> None:
    """Refuse any file under the 2015-2021 backfill's raw folder, and any year before 2022."""
    p = Path(path).resolve()
    b = BACKFILL_RAW.resolve()
    if p == b or b in p.parents:
        raise Refused(f"{p} is under {P.rel(BACKFILL_RAW)}: not staged here")
    try:
        y = int(year)
    except (TypeError, ValueError):
        raise Refused(f"year {year!r} unknown: not staged")
    if y < FIRST_YEAR:
        raise Refused(f"{y} is before {FIRST_YEAR}: not staged here")


def open_file(path: Path, year) -> object:
    """The decrypted document of one raw envelope, after the guard."""
    guard(path, year)
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return I.decrypt(json.load(fh))


# --------------------------------------------------------------------------------------
# which files
# --------------------------------------------------------------------------------------
def collect(receipts=None, daily_receipts=None, complete=None) -> dict[tuple, dict[str, dict]]:
    """{(year, event, MID): {kind: {route, path, sha256, retrieved_at, folder}}}: this collector's served files, plus
    the daily collector's key statistics of completed matches. Key statistics with two files (a static file and its
    API twin, the same document) keep the static one; both MatchBeats copies are kept (kinds "match-beats" and
    "match-beats-api")."""
    from src.ingest.point_sources import infosys_atp_recent as R
    receipts = receipts if receipts is not None else P.receipts_for(SOURCE)
    out: dict[tuple, dict[str, dict]] = defaultdict(dict)

    def add(rec: dict, folder: str) -> None:
        parts = str(rec.get("name", "")).split("/")
        if len(parts) != 4 or not parts[0].isdigit() or not parts[1].isdigit() or parts[2] not in KIND:
            return
        path = P.PROJECT_ROOT / rec["dest"]
        if not A.served(rec) or not path.exists():
            return
        key = (parts[0], parts[1], parts[3].upper())
        kind = KIND[parts[2]]
        have = out[key].get(kind)
        if have and PREFER.index(have["route"]) <= PREFER.index(parts[2]):
            return
        out[key][kind] = {"route": parts[2], "path": path, "sha256": rec.get("sha256"),
                          "retrieved_at": rec.get("retrieved_at"), "folder": folder}

    for rec in receipts.all().values():
        add(rec, SOURCE)
    daily = daily_receipts if daily_receipts is not None else (
        R.receipts_at(DAILY_RAW) if (DAILY_RAW / "_receipts.jsonl").exists() else None)
    if daily is not None:
        done = complete() if complete is not None else R.daily_complete()
        for rec in daily.all().values():
            parts = str(rec.get("name", "")).split("/")
            if len(parts) == 4 and parts[0].isdigit() and parts[1].isdigit() and done is not None \
                    and (int(parts[0]), int(parts[1]), parts[3].upper()) in done:
                key = (parts[0], parts[1], parts[3].upper())
                if "keystats" not in out.get(key, {}):
                    add(rec, DAILY)
    return dict(out)


def mtd_events() -> dict[tuple[str, str], dict]:
    """ManTennisData's event name, series, level and start date by (year, event id)."""
    import pyarrow.parquet as pq
    path = A.MTD_ROOT / "atp_tournaments.parquet"
    if not path.exists():
        return {}
    out = {}
    for t in pq.read_table(path, columns=["id", "name", "series_id", "series_category_id", "start_dtm"]).to_pylist():
        year, _, event = str(t["id"]).partition("-")
        if year.isdigit() and event.isdigit():
            out[(year, str(int(event)))] = t
    return out


# --------------------------------------------------------------------------------------
# rows
# --------------------------------------------------------------------------------------
def prov(f: dict) -> list:
    return [P.rel(f["path"]), f.get("sha256"), f.get("retrieved_at")]


def score_from_points(mb: dict) -> str | None:
    """The match score read from MatchBeats' games: each set's games from its last game's set score, with the
    tie-break's points in brackets for the loser of a 7-6 set ("6-4 7-6(5)"), from player 1's side."""
    sets = []
    for st in mb.get("setData") or []:
        games = [g for g in st.get("gameData") or [] if isinstance(g, dict)]
        if not games:
            continue
        last = games[-1]
        a, b = last.get("tm1SetScore"), last.get("tm2SetScore")
        if a is None or b is None:
            return None
        text = f"{a}-{b}"
        if last.get("isTieBreak") and {int(a), int(b)} == {6, 7}:
            pts = [p for p in last.get("pointData") or [] if isinstance(p, dict)]
            if pts:
                t1, t2 = pts[-1].get("tm1GameScore"), pts[-1].get("tm2GameScore")
                try:
                    lost = min(int(t1), int(t2))
                    text += f"({lost})"
                except (TypeError, ValueError):
                    pass
        sets.append(text)
    return " ".join(sets) or None


def set_won(a: int, b: int) -> int:
    """1 or 2 when a set's games make it won (6 or more and two clear, or 7-6), else 0 (unfinished)."""
    if (a >= 6 and a - b >= 2) or (a == 7 and b == 6):
        return 1
    if (b >= 6 and b - a >= 2) or (b == 7 and a == 6):
        return 2
    return 0


def winner_from_points(mb: dict) -> int:
    """The player (1 or 2) who won two sets, by each set's games in MatchBeats' last game of the set; 0 when no one
    has (a retirement or a walkover, or a file without its last games). Some complete matches are never marked
    finished in their MatchBeats file and name no winner (matchWinner 0); this reads it from the games instead."""
    won = {1: 0, 2: 0}
    for st in mb.get("setData") or []:
        games = [g for g in st.get("gameData") or [] if isinstance(g, dict)]
        if not games:
            continue
        try:
            w = set_won(int(games[-1].get("tm1SetScore")), int(games[-1].get("tm2SetScore")))
        except (TypeError, ValueError):
            return 0
        if w:
            won[w] += 1
    return 1 if won[1] >= 2 and won[1] > won[2] else 2 if won[2] >= 2 and won[2] > won[1] else 0


def matchbeats_points(mb: dict) -> list[dict]:
    return [p for st in mb.get("setData") or [] for g in st.get("gameData") or []
            for p in g.get("pointData") or [] if isinstance(p, dict)]


def is_newer_format(mb: dict) -> bool:
    """A MatchBeats document in the newer format: its points carry the fields the API's copy adds."""
    return any(k in p for p in matchbeats_points(mb)[:5] for k in NEWER_FIELDS[:3])


def core(mb: dict) -> list[tuple]:
    """Each point's core, in order: id, server, serve number, speeds, scorer, ending and score."""
    return [tuple(str(p.get(k)) for k in CORE_FIELDS) for p in matchbeats_points(mb)]


def compare_matchbeats(static: dict, api: dict) -> dict:
    """How a match's two MatchBeats copies differ, point by point on the point id: points in each, matched, timed in
    each, the core fields that differ (with counts) and the endings' pairs (static -> newer)."""
    a = {str(p.get("pointId")): p for p in matchbeats_points(static)}
    b = {str(p.get("pointId")): p for p in matchbeats_points(api)}
    both = [k for k in a if k in b]
    fields = Counter(f for k in both for f in CORE_FIELDS if str(a[k].get(f)) != str(b[k].get(f)))
    endings = Counter(f"{a[k].get('result')}->{b[k].get('result')}" for k in both
                      if str(a[k].get("result")) != str(b[k].get("result")))
    timed = lambda d: sum(1 for p in d.values() if (I.num(p.get("serveSpeed")) or 0) > 0)  # noqa: E731
    return {"points_static": len(a), "points_api": len(b), "points_matched": len(both),
            "timed_static": timed(a), "timed_api": timed(b), "newer_format": is_newer_format(api),
            "core_identical": not fields and len(both) == len(a) == len(b),
            "fields_differing": json.dumps(dict(fields), sort_keys=True),
            "endings_differing": json.dumps(dict(endings), sort_keys=True)}


def newer_details(mb: dict | None) -> dict[str, list]:
    """{point id: [the NEWER_FIELDS, the point's ending, the game's two momentum scores]} of a newer-format copy."""
    out: dict[str, list] = {}
    for st in (mb or {}).get("setData") or []:
        for g in st.get("gameData") or []:
            if not isinstance(g, dict):
                continue
            mom = [P.s(g.get("momentumScoreTeam1")), P.s(g.get("momentumScoreTeam2"))]
            for p in g.get("pointData") or []:
                if isinstance(p, dict):
                    out[str(p.get("pointId"))] = [P.s(p.get(k)) for k in NEWER_FIELDS] + [P.s(p.get("result"))] + mom
    return out


def shots(trajectory) -> list[dict]:
    """A Court Vision trajectory (a12: positions labelled hit, peak, net, bounce, last) split into strokes at each
    "hit". A peak before the stroke's bounce is its peak_pre, after it its peak_post; positions that do not fit go to
    ``extra``."""
    strokes, cur = [], None
    for pos in trajectory or []:
        if not isinstance(pos, dict):
            continue
        label = str(pos.get("a73") or "")
        xyz = (pos.get("a70"), pos.get("a71"), pos.get("a72"))
        if label == "hit" or cur is None:
            cur = {"labels": [], "extra": []}
            strokes.append(cur)
        cur["labels"].append(label)
        if label == "peak":
            part = "peak_post" if "bounce" in cur else "peak_pre"
        elif label in ("hit", "net", "bounce", "last"):
            part = label
        else:
            part = None
        if part is None or part in cur:
            cur["extra"].append({k: v for k, v in pos.items()})
        else:
            cur[part] = xyz
    return strokes


def num_or_none(v) -> str | None:
    return None if v is None else P.s(v)


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
class Stager:
    """Streams each route's rows into its table and keeps a per-match summary for matches.parquet."""

    def __init__(self, files: dict[tuple, dict[str, dict]]):
        self.files = files
        self.facts: dict[tuple, dict] = defaultdict(dict)
        self.counts: Counter = Counter()
        self.failures: list[dict] = []

    def docs(self, kind: str):
        """(key, file, decrypted document) for every file of a kind, in key order; failures are counted."""
        for key in sorted(self.files, key=lambda k: (k[0], int(k[1]), k[2])):
            f = self.files[key].get(kind)
            if not f:
                continue
            try:
                doc = open_file(f["path"], key[0])
            except Refused:
                raise
            except Exception as err:  # noqa: BLE001 - a key that does not open the file, text that is not JSON
                self.counts[f"failed:{kind}"] += 1
                self.failures.append({"file": P.rel(f["path"]), "error": f"{type(err).__name__}: {err}"})
                continue
            self.counts[f"decrypted:{kind}"] += 1
            if not isinstance(doc, dict):
                self.counts[f"not_a_document:{kind}"] += 1
                continue
            yield key, f, doc

    def open_one(self, key, f: dict, kind: str):
        """One file's decrypted document, or None (a failure is counted)."""
        try:
            doc = open_file(f["path"], key[0])
        except Refused:
            raise
        except Exception as err:  # noqa: BLE001 - a key that does not open the file, text that is not JSON
            self.counts[f"failed:{kind}"] += 1
            self.failures.append({"file": P.rel(f["path"]), "error": f"{type(err).__name__}: {err}"})
            return None
        self.counts[f"decrypted:{kind}"] += 1
        if not isinstance(doc, dict):
            self.counts[f"not_a_document:{kind}"] += 1
            return None
        return doc

    def points(self):
        """Every MatchBeats point. With both copies, the static copy's points (its core: the record the rally analysis
        and the box-score checks agree with) and the newer copy's details joined by point id (NEWER_COLUMNS); with one
        copy, its own points (an API-only copy gives its details itself). Owner, 27 Oct 2026: the newer format
        wanted; how it joins is an agent's choice (process log, judgment call 10)."""
        self.copy_differences: list[dict] = []
        for key in sorted(self.files, key=lambda k: (k[0], int(k[1]), k[2])):
            fl = self.files[key]
            have = {name: (f, self.open_one(key, f, name)) for name in ("match-beats", "match-beats-api")
                    if (f := fl.get(name))}
            have = {name: v for name, v in have.items() if v[1] is not None}
            if not have:
                continue
            static, api = have.get("match-beats"), have.get("match-beats-api")
            if static and api:
                name, why = "match-beats", "static core, newer details from match-beats-api" \
                    if is_newer_format(api[1]) else "static; the api copy is not in the newer format"
                diff = compare_matchbeats(static[1], api[1])
                self.copy_differences.append({"year": key[0], "event_id": key[1], "match_id": key[2], **diff})
                self.counts["matchbeats:core identical"] += diff["core_identical"]
                details = newer_details(api[1]) if is_newer_format(api[1]) else {}
                own = False
            else:
                name, why = ("match-beats", "static only") if static else ("match-beats-api", "api only")
                details = newer_details(have[name][1]) if is_newer_format(have[name][1]) else {}
                own = True
            self.counts[f"matchbeats:{why}"] += 1
            f, mb = have[name]
            pts = matchbeats_points(mb)
            timed = [p for p in pts if (I.num(p.get("serveSpeed")) or 0) > 0]
            p1, p2 = S.players({"match-beats": mb})
            self.facts[key].update(
                mb=True, mb_copy=f"{name}: {why}", event_type=mb.get("eventType"), court_id=mb.get("courtId"),
                court_name=mb.get("courtName"), is_match_complete=mb.get("isMatchComplete"),
                match_status=mb.get("matchStatus"), match_winner=mb.get("matchWinner"),
                sets_completed=mb.get("setsComplete"), score=score_from_points(mb),
                winner_points=winner_from_points(mb), points=len(pts), points_timed=len(timed),
                first_serve_points_timed=sum(1 for p in timed if str(p.get("serve")) == "1"),
                points_classified=sum(1 for p in pts if str(p.get("result")) in S.ENDINGS), players_mb=(p1, p2))
            ordered = [p for st in mb.get("setData") or [] for g in st.get("gameData") or []
                       for p in g.get("pointData") or []]                      # point_rows' own order
            rows = I.point_rows(list(key) + [f["route"]], mb)
            empty = [None] * len(NEWER_COLUMNS)
            for row, p in zip(rows, ordered):
                d = details.get(str(p.get("pointId"))) if isinstance(p, dict) else None
                if d is None:
                    extra = empty
                elif own:                  # one copy: its ending is already in `result`, so result_newer stays empty
                    extra = d[:len(NEWER_FIELDS)] + [None] + d[len(NEWER_FIELDS) + 1:]
                else:
                    extra = d
                yield row + extra + prov(f)

    def keystats(self):
        for key, f, ks in self.docs("keystats"):
            ks = ks.get("stats", ks) if isinstance(ks.get("stats"), dict) else ks
            s0 = (ks.get("setStats") or {}).get("set0") or []
            speed = any(e.get("name") == "1st Serve Average Speed" and any((I.num(e.get(k)) or 0) > 0
                                                                            for k in ("player1", "player2"))
                        for e in s0 if isinstance(e, dict))
            self.facts[key].update(keystats_sets=len(ks.get("setStats") or {}), keystats_speed=speed,
                                   ks_complete=ks.get("matchCompleted"), ks_sets=ks.get("setsCompleted"),
                                   ks_court=ks.get("courtId"), players_ks=S.players({"keystats": ks}))
            for row in I.stat_rows(list(key) + [f["route"]], ks):
                yield row + prov(f)

    def rally(self):
        for key, f, ra in self.docs("rally-analysis"):
            entries = [e for c in ra.get("rallyData") or [] for v in c.values() if isinstance(v, list) for e in v
                       if isinstance(e, dict)]
            self.facts[key].update(rally_entries=len(entries),
                                   rally_timed=sum(1 for e in entries if (I.num(e.get("serveSpeed")) or 0) > 0),
                                   ra_complete=ra.get("matchCompleted"), ra_sets=ra.get("setsCompleted"),
                                   players_ra=S.players({"rally-analysis": ra}))
            for row in I.rally_rows(list(key) + [f["route"]], ra):
                yield row + prov(f)

    def court_vision(self):
        """The point records; one row per file is kept aside for court_vision_matches.parquet."""
        self.cv_match_rows: list[list] = []
        for key, f, cv in self.docs("court-vision"):
            recs = list(S.cv_point_records(cv))
            self.facts[key].update(cv_points=len(recs),
                                   cv_timed=sum(1 for r in recs if S.cv_speed(r.get("a16")) is not None))
            base = list(key) + [f["route"]]
            entries = [e for e in cv.get("courtVisionData") or [] if isinstance(e, dict)]
            if entries:
                tops = [{k: v for k, v in e.items() if k not in ("a50", "a49", "a79")} for e in entries]
                players = next((e["a79"] for e in entries if e.get("a79")), None)
                self.cv_match_rows.append(base + [str(len(entries)), json.dumps(tops, ensure_ascii=False, sort_keys=True),
                                                  json.dumps(players, ensure_ascii=False, sort_keys=True),
                                                  json.dumps(entries[-1].get("a49"), ensure_ascii=False,
                                                             sort_keys=True)] + prov(f))
            for rec in recs:
                scalars = {k: v for k, v in rec.items() if not isinstance(v, (dict, list))}
                other = {k: v for k, v in scalars.items() if k not in CV_FIELDS}
                nested = {k: rec[k] for k in CV_NESTED if k in rec}
                yield (base + [P.s(rec.get(k)) for k in CV_FIELDS]
                       + [json.dumps(other, ensure_ascii=False, sort_keys=True),
                          json.dumps(rec.get("a35"), ensure_ascii=False, sort_keys=True) if "a35" in rec else None,
                          json.dumps(nested, ensure_ascii=False, sort_keys=True) if nested else None] + prov(f))

    def court_vision_shots(self):
        for key, f, cv in self.docs("court-vision"):
            base = list(key) + [f["route"]]
            for rec in S.cv_point_records(cv):
                for i, st in enumerate(shots(rec.get("a12")), 1):
                    coords = []
                    for part in SHOT_PARTS:
                        xyz = st.get(part) or (None, None, None)
                        coords += [num_or_none(v) for v in xyz]
                    yield (base + [P.s(rec.get("a81")), str(i), "|".join(st["labels"])] + coords
                           + [json.dumps(st["extra"], ensure_ascii=False) if st["extra"] else None] + prov(f))

    def court_vision_matches(self):
        yield from getattr(self, "cv_match_rows", [])

    def match_rows(self, events: dict, last_modified: dict):
        for key in sorted(self.files, key=lambda k: (k[0], int(k[1]), k[2])):
            year, event, mid = key
            fx, fl = self.facts.get(key, {}), self.files[key]
            p1, p2 = fx.get("players_mb") or fx.get("players_ks") or fx.get("players_ra") or ({}, {})
            k1, k2 = fx.get("players_ks") or ({}, {})
            t = events.get((year, str(int(event))), {})
            family = mid[:2]
            first = lambda *vals: next((v for v in vals if v not in (None, "")), None)  # noqa: E731
            lms = {f["route"]: last_modified.get(f["path"]) for f in fl.values()}
            yield list(key) + [
                family, "qual" if family == "QS" else "main", S.round_from_code(event, mid), t.get("series_id"),
                t.get("series_category_id"), t.get("name"), t.get("start_dtm"),
                json.dumps(sorted(f["route"] for f in fl.values())), str(len(fl)), P.s(fx.get("event_type")),
                P.s(first(fx.get("court_id"), fx.get("ks_court"))), P.s(fx.get("court_name")),
                P.s(first(fx.get("is_match_complete"), fx.get("ks_complete"), fx.get("ra_complete"))),
                P.s(fx.get("match_status")), P.s(fx.get("match_winner")),
                P.s(first(fx.get("sets_completed"), fx.get("ks_sets"), fx.get("ra_sets"))), fx.get("score"),
                P.s(fx.get("winner_points")) if fx.get("mb") else None, fx.get("mb_copy"),
                P.s(p1.get("id")), P.s(p1.get("name")), P.s(p1.get("first")), P.s(p1.get("last")),
                P.s(p1.get("country")), P.s(p2.get("id")), P.s(p2.get("name")), P.s(p2.get("first")),
                P.s(p2.get("last")), P.s(p2.get("country")), P.s(k1.get("id")), P.s(k2.get("id")),
                str(fx.get("points", 0)), str(fx.get("points_timed", 0)), str(fx.get("first_serve_points_timed", 0)),
                str(fx.get("points_classified", 0)), str(fx.get("keystats_sets", 0)),
                P.s(bool(fx.get("keystats_speed"))), str(fx.get("rally_entries", 0)), str(fx.get("rally_timed", 0)),
                str(fx.get("cv_points", 0)), str(fx.get("cv_timed", 0)),
                max((v for v in lms.values() if v), default=None), json.dumps(lms, sort_keys=True),
                json.dumps({f["route"]: P.rel(f["path"]) for f in fl.values()}, sort_keys=True),
                json.dumps({f["route"]: f.get("sha256") for f in fl.values()}, sort_keys=True),
                max((f.get("retrieved_at") or "" for f in fl.values()), default=None) or None]


def envelope_times(files: dict) -> dict[Path, str]:
    """Each file's plain lastModified (UTC), read from the envelope without decrypting."""
    out = {}
    for fl in files.values():
        for f in fl.values():
            try:
                with gzip.open(f["path"], "rt", encoding="utf-8") as fh:
                    out[f["path"]] = A.utc_of(json.load(fh).get("lastModified"))
            except (OSError, ValueError):
                out[f["path"]] = None
    return out


def stage(plan_years=None, receipts=None, daily_receipts=None, complete=None, dump: Path | None = None,
          summary_path: Path | None = SUMMARY) -> dict:
    """Decrypt and write the seven tables; returns the summary (also written to ``summary_path``)."""
    t0 = time.time()
    files = collect(receipts, daily_receipts, complete)
    if plan_years:
        files = {k: v for k, v in files.items() if int(k[0]) in {int(y) for y in plan_years}}
    for key, fl in files.items():           # the guard, before anything is read
        for f in fl.values():
            guard(f["path"], key[0])
    dump = dump or P.dump_path(SOURCE)
    st = Stager(files)
    lm = envelope_times(files)
    out: dict = {"source": SOURCE, "started_at": P.utc_now_iso(), "decision": DECISION, "matches": len(files),
                 "files": sum(len(v) for v in files.values()),
                 "files_by_folder": dict(Counter(f["folder"] for v in files.values() for f in v.values())),
                 "files_by_route": dict(Counter(f["route"] for v in files.values() for f in v.values()))}
    tables = [
        ("points.parquet", KEYS + ["route", "set", "game", "seq"] + I.POINT_FIELDS
         + ["other_fields", "game_fields", "set_fields"] + NEWER_COLUMNS + PROV, st.points),
        ("keystats.parquet", KEYS + ["route", "set_key"] + I.STAT_FIELDS + ["other_fields"] + PROV, st.keystats),
        ("rally.parquet", KEYS + ["route", "category", "list"] + I.RALLY_FIELDS + ["other_fields"] + PROV, st.rally),
        ("court_vision.parquet", KEYS + ["route"] + CV_FIELDS + ["other_fields", "score_block", "positions"] + PROV,
         st.court_vision),
        ("court_vision_shots.parquet", KEYS + ["route", "point_id", "stroke_idx", "labels"]
         + [f"{c}_{part}" for part in SHOT_PARTS for c in ("x", "y", "z")] + ["extra"] + PROV,
         st.court_vision_shots),
        ("court_vision_matches.parquet", KEYS + ["route", "entries", "entry_fields", "players", "last_summary"] + PROV,
         st.court_vision_matches),
    ]
    staged = {}
    for name, header, rows in tables:
        res = P.stage_table(SOURCE, dump / name, header, rows(), source_file=P.rel(RAW), retrieved_at=None,
                            extra={"decision": DECISION})
        staged[name] = {"rows": res["rows"], "bytes": res["bytes"]}
        P.log(f"[{SOURCE}] staged {name}: {res['rows']:,} rows")
    res = P.stage_table(SOURCE, dump / "matches.parquet", MATCH_COLUMNS, st.match_rows(mtd_events(), lm),
                        source_file=P.rel(RAW), retrieved_at=None, extra={"decision": DECISION})
    staged["matches.parquet"] = {"rows": res["rows"], "bytes": res["bytes"]}
    P.log(f"[{SOURCE}] staged matches.parquet: {res['rows']:,} rows")
    by_year: dict[str, Counter] = defaultdict(Counter)
    for key, fx in st.facts.items():
        c = by_year[key[0]]
        c["matches_with_a_document"] += 1
        c["with_points"] += bool(fx.get("points"))
        c["with_timed_points"] += bool(fx.get("points_timed"))
        c["with_keystats"] += bool(fx.get("keystats_sets"))
        c["with_keystats_speed"] += bool(fx.get("keystats_speed"))
        c["with_rally"] += bool(fx.get("rally_entries"))
        c["with_court_vision"] += bool(fx.get("cv_points"))
    diffs = getattr(st, "copy_differences", [])
    if summary_path is not None:                       # every match with both copies, how they differ (gzipped CSV)
        import pandas as pd
        pd.DataFrame(diffs, columns=["year", "event_id", "match_id", "points_static", "points_api", "points_matched",
                                     "timed_static", "timed_api", "newer_format", "core_identical",
                                     "fields_differing", "endings_differing"]).to_csv(
            DIFFERENCES, index=False, compression="gzip")
    ending_pairs: Counter = Counter()
    for d in diffs:
        ending_pairs.update(json.loads(d["endings_differing"]))
    out.update(staged=staged, by_year={y: dict(c) for y, c in sorted(by_year.items())},
               matchbeats_copies={k.split(":", 1)[1]: v for k, v in st.counts.items() if k.startswith("matchbeats:")},
               matchbeats_both_copies={"matches": len(diffs),
                                       "core_identical": sum(1 for d in diffs if d["core_identical"]),
                                       "points_matched": sum(d["points_matched"] for d in diffs),
                                       "endings_differing": sum(ending_pairs.values()),
                                       "ending_pairs_static_to_newer": dict(ending_pairs.most_common(12)),
                                       "timed_points_static": sum(d["timed_static"] for d in diffs),
                                       "timed_points_api": sum(d["timed_api"] for d in diffs)},
               decryption={k: v for k, v in st.counts.items() if not k.startswith("matchbeats:")},
               failures=st.failures[:50], failures_total=len(st.failures),
               finished_at=P.utc_now_iso(), seconds=round(time.time() - t0, 1))
    if summary_path is not None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def main() -> int:
    P.configure_stdout()
    out = stage()
    P.log(f"[{SOURCE}] {out['matches']:,} matches, {out['files']:,} files staged in {out['seconds']} s; "
          f"{out['failures_total']} decryption failures; summary {P.rel(SUMMARY)}")
    return 1 if out["failures_total"] else 0


if __name__ == "__main__":
    sys.exit(main())

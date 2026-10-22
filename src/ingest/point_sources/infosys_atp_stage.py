"""The ATP Stats Centre's Infosys files of 2018 to October 2021, decrypted: the staged tables.

The files atptour.com's Stats Centre pages load from itp-atp-sls.infosys-platforms.com were downloaded on 8 Oct 2026
(src/ingest/point_sources/infosys_atp.py, kept encrypted as served under data/raw/point_sources/infosys_atp/) and
decrypted later that day on the owner's instruction (docs/decisions/2026-10-08-scraping-approved.md, "Backfill
decryption authorized subsequently") by src/ingest/point_sources/infosys_atp_decrypt.py, into plain JSON with every
field kept: data/dump/points/infosys_atp/decrypted/<year>/<event>/<route>/<MID>.json (audit:
data/studies/serve_speed_acquisition/infosys_atp_decryption/). This module reads those plain files, makes no request
and decrypts nothing, and writes the tables the AO's and RG's files have (src/ingest/point_sources/infosys_slams.py),
with that module's parsers:

    matches.parquet       one row per (year, event, match code) with a file: the routes it has, the players (Infosys
                          ids, names, countries), court, status, winner and sets as MatchBeats gives them, the round of
                          a main-draw code by its bracket number (None for qualifying codes and for the round-robin
                          events: the ATP and Next Gen Finals, the Laver Cup), counts (points, timed points, timed
                          first-serve points, points whose ending is classified, key-statistic sets and whether they
                          carry a speed, rally entries, Court Vision points), each route's lastModified (from the
                          download's inventory) and whether the code was in the plan or a calibration file
    points.parquet        every MatchBeats point, its fields verbatim, with set and game numbers
    keystats.parquet      every key statistic of every set ("set0" is the match)
    rally.parquet         every rally-analysis entry
    court_vision.parquet  every Court Vision point record's scalar fields, with the served a-number names (a81 the point
                          id; a16 the serve's speed, "NA" when not timed, as text with its unit where the file has one);
                          the trajectories stay in the JSON
Strings throughout, as the rest of the dump. No blocks table: the decrypted JSON files are the complete copy.

What the files hold (observed, 8 Oct 2026): 2015-2017 nothing (the host served no file); 2018 the ATP Finals (15
matches, timed); 2019 the ATP and Next Gen Finals and 2020 Vienna, Paris, Sofia and the ATP Finals (194 matches, every
point but no serve speed); 2021 every event to 17 Oct with a file per match, but points only at 9 events (Newport,
Washington, Metz, Nur-Sultan, the Laver Cup, Sofia, San Diego, Indian Wells and one Mallorca match) and serve speeds
only at Washington, San Diego and Indian Wells (169 matches). The other 2021 MatchBeats files hold no point.

Run: ./python.sh -m src.ingest.point_sources.infosys_atp_stage
Summary: data/studies/serve_speed_acquisition/infosys_atp_stage_summary.json
"""
from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import infosys_slams as I

SOURCE = "infosys_atp"
DECISION = "docs/decisions/2026-10-08-scraping-approved.md"
DECRYPTED = P.dump_path(SOURCE, "decrypted")
STUDY_ROOT = P.PROJECT_ROOT / "data" / "studies" / "serve_speed_acquisition"
INVENTORY = STUDY_ROOT / "infosys_atp_files.csv"                       # the download's inventory: lastModified
DECRYPTION = STUDY_ROOT / "infosys_atp_decryption" / "files.csv"        # the decryption's audit: purpose, checks
ROUTES = ("keystats", "match-beats", "rally-analysis", "court-vision")
ROUND_ROBIN_EVENTS = {"605", "7696", "9210"}                             # ATP Finals, Next Gen Finals, Laver Cup
ENDINGS = {"A", "P", "DF", "W", "FE", "UE"}         # a classified MatchBeats ending ("N": not); "P" and "DF" both
                                                    # end a double fault (the key statistics' counts, 2018-2021)
KEYS = ["year", "event_id", "match_id"]
MATCH_COLUMNS = KEYS + [
    "family", "draw", "round_from_code", "purpose", "routes", "files", "event_type", "court_id", "court_name",
    "is_match_complete", "match_status", "match_winner", "sets_completed", "p1_id", "p1_name", "p1_first_name",
    "p1_last_name", "p1_country", "p2_id", "p2_name", "p2_first_name", "p2_last_name", "p2_country", "points",
    "points_timed", "first_serve_points_timed", "points_classified", "keystats_sets", "keystats_speed",
    "rally_entries", "rally_timed", "cv_points", "cv_timed", "last_modified_utc", "source_files"]
CV_FIELDS = ["a81", "a13", "a14", "a15", "a16", "a21", "a95", "a97", "a98", "a99", "a100", "a101", "a102"]


def round_from_code(event: str, mid: str) -> str | None:
    """A main-draw code's round by its bracket number (MS001 the final ... MS064-127 the first of 128); None for
    qualifying codes and at the round-robin events, whose codes are not a bracket."""
    if event in ROUND_ROBIN_EVENTS or not mid.upper().startswith("MS"):
        return None
    try:
        n = int(mid[2:])
    except ValueError:
        return None
    return {0: "F", 1: "SF", 2: "QF", 3: "R16", 4: "R32", 5: "R64", 6: "R128"}.get(int(math.floor(math.log2(n)))) \
        if n >= 1 else None


def players(docs: dict) -> list[dict]:
    """The two players from MatchBeats, else the key statistics, else the rally analysis."""
    mb, ks, ra = docs.get("match-beats"), docs.get("keystats"), docs.get("rally-analysis")
    if isinstance(mb, dict) and isinstance(mb.get("playerData"), dict) and mb["playerData"].get("tm1Ply1Id"):
        return I.players_of({"mbData": mb})
    if isinstance(ks, dict) and isinstance(ks.get("players"), list) and len(ks["players"]) >= 2:
        return I.players_of({"stats": ks})
    if isinstance(ra, dict) and isinstance(ra.get("playerDetails"), list) and len(ra["playerDetails"]) >= 2:
        return [{"id": p.get("player1Id"), "name": p.get("player1Name"), "first": None, "last": None,
                 "country": p.get("player1Country")} for p in ra["playerDetails"][:2]]
    return [{}, {}]


def cv_point_records(doc: dict):
    """Court Vision's point records: the values of each courtVisionData entry's a50 map."""
    for entry in doc.get("courtVisionData") or []:
        if isinstance(entry, dict):
            for rec in (entry.get("a50") or {}).values():
                if isinstance(rec, dict):
                    yield rec


def cv_speed(value) -> float | None:
    text = str(value or "").upper().replace("KPH", "").strip()
    try:
        v = float(text)
    except ValueError:
        return None
    return v if v > 0 else None


def cv_rows(base: list, doc: dict) -> list[list]:
    rows = []
    for rec in cv_point_records(doc):
        scalars = {k: v for k, v in rec.items() if not isinstance(v, (dict, list))}
        other = {k: v for k, v in scalars.items() if k not in CV_FIELDS}
        rows.append(base + [P.s(rec.get(k)) for k in CV_FIELDS] + [json.dumps(other, ensure_ascii=False, sort_keys=True)])
    return rows


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def challenger_keys() -> set[tuple]:
    """(year, event, route, MID) of the Challenger point files fetched into the adapter's raw folder for the P6 data
    issues: staged on their own (infosys_challengers_stage.py), never here, whose tables the serve-speed backfill reads
    (owner, 14 Oct 2026)."""
    from src.ingest.point_sources.infosys_challengers_stage import CHALLENGER_PURPOSES
    return {(str(r.get("year")), str(r.get("event_id")), str(r.get("route")), str(r.get("match_id")).upper())
            for r in P.receipts_for("infosys_atp").all().values() if r.get("purpose") in CHALLENGER_PURPOSES}


def stage() -> dict:
    left_out = challenger_keys()
    files = sorted(p for p in DECRYPTED.rglob("*.json") if len(p.relative_to(DECRYPTED).parts) == 4
                   and (*p.relative_to(DECRYPTED).parts[:3], p.stem.upper()) not in left_out)
    if not files:
        raise SystemExit(f"no decrypted file under {P.rel(DECRYPTED)}: run src/ingest/point_sources/infosys_atp_decrypt.py")
    inventory = {(r["year"], r["event_id"], r["route"], r["match_id"].upper()): r for r in read_csv(INVENTORY)}
    purpose = {(r["year"], r["event_id"], r["route"], r["match_id"].upper()): r["purpose"] for r in read_csv(DECRYPTION)}
    by_match: dict[tuple, dict] = {}
    for path in files:
        year, event, route, name = path.relative_to(DECRYPTED).parts
        if route not in ROUTES:
            continue
        by_match.setdefault((year, event, name[:-5].upper()), {})[route] = path
    points, stats, rallies, cvs, match_rows = [], [], [], [], []
    counts = Counter()
    for (year, event, mid), paths in sorted(by_match.items(), key=lambda kv: (kv[0][0], int(kv[0][1]), kv[0][2])):
        docs = {route: json.loads(path.read_text(encoding="utf-8")) for route, path in paths.items()}
        keys = [year, event, mid]
        mb = docs.get("match-beats") if isinstance(docs.get("match-beats"), dict) else {}
        ks = docs.get("keystats") if isinstance(docs.get("keystats"), dict) else {}
        ra = docs.get("rally-analysis") if isinstance(docs.get("rally-analysis"), dict) else {}
        cv = docs.get("court-vision") if isinstance(docs.get("court-vision"), dict) else {}
        if mb:
            points.extend(I.point_rows(keys + ["match-beats"], mb))
        if ks:
            stats.extend(I.stat_rows(keys + ["keystats"], ks))
        if ra:
            rallies.extend(I.rally_rows(keys + ["rally-analysis"], ra))
        if cv:
            cvs.extend(cv_rows(keys + ["court-vision"], cv))
        pts = [p for set_ in mb.get("setData") or [] for g in set_.get("gameData") or [] for p in g.get("pointData") or []]
        timed = [p for p in pts if (I.num(p.get("serveSpeed")) or 0) > 0]
        rally_entries = [e for c in ra.get("rallyData") or [] for v in c.values() if isinstance(v, list) for e in v
                         if isinstance(e, dict)]
        s0 = (ks.get("setStats") or {}).get("set0") or []
        ks_speed = any(e.get("name") == "1st Serve Average Speed" and any((I.num(e.get(k)) or 0) > 0
                                                                          for k in ("player1", "player2"))
                       for e in s0 if isinstance(e, dict))
        cv_pts = list(cv_point_records(cv))
        p1, p2 = players(docs)
        lm = [inventory.get((year, event, route, mid), {}).get("last_modified_utc") for route in sorted(paths)]
        purposes = {purpose.get((year, event, route, mid), "unknown") for route in paths}
        family = mid[:2]
        first = lambda *vals: next((v for v in vals if v not in (None, "")), None)  # noqa: E731
        match_rows.append(keys + [
            family, "qual" if family == "QS" else "main", round_from_code(event, mid),
            "+".join(sorted(purposes)), json.dumps(sorted(paths)), str(len(paths)),
            P.s(mb.get("eventType")), P.s(first(mb.get("courtId"), ks.get("courtId"))), P.s(mb.get("courtName")),
            P.s(first(mb.get("isMatchComplete"), ks.get("matchCompleted"), ra.get("matchCompleted"))),
            P.s(mb.get("matchStatus")), P.s(mb.get("matchWinner")),
            P.s(first(mb.get("setsComplete"), ks.get("setsCompleted"), ra.get("setsCompleted"))),
            P.s(p1.get("id")), P.s(p1.get("name")), P.s(p1.get("first")), P.s(p1.get("last")), P.s(p1.get("country")),
            P.s(p2.get("id")), P.s(p2.get("name")), P.s(p2.get("first")), P.s(p2.get("last")), P.s(p2.get("country")),
            str(len(pts)), str(len(timed)), str(sum(1 for p in timed if str(p.get("serve")) == "1")),
            str(sum(1 for p in pts if str(p.get("result")) in ENDINGS)), str(len(ks.get("setStats") or {})),
            P.s(bool(ks_speed)), str(len(rally_entries)),
            str(sum(1 for e in rally_entries if (I.num(e.get("serveSpeed")) or 0) > 0)), str(len(cv_pts)),
            str(sum(1 for r in cv_pts if cv_speed(r.get("a16")) is not None)),
            max((x for x in lm if x), default=None), json.dumps([P.rel(paths[r]) for r in sorted(paths)])])
        counts[f"{year}|matches"] += 1
        counts[f"{year}|with_points"] += bool(pts)
        counts[f"{year}|with_timed_points"] += bool(timed)
        counts[f"{year}|with_keystats_speed"] += bool(ks_speed)
    retrieved = max((r.get("retrieved_at") or "" for r in inventory.values()), default=None) or None
    out = {}
    tables = [
        ("matches.parquet", MATCH_COLUMNS, match_rows),
        ("points.parquet", KEYS + ["route", "set", "game", "seq"] + I.POINT_FIELDS
         + ["other_fields", "game_fields", "set_fields"], points),
        ("keystats.parquet", KEYS + ["route", "set_key"] + I.STAT_FIELDS + ["other_fields"], stats),
        ("rally.parquet", KEYS + ["route", "category", "list"] + I.RALLY_FIELDS + ["other_fields"], rallies),
        ("court_vision.parquet", KEYS + ["route"] + CV_FIELDS + ["other_fields"], cvs),
    ]
    for file, header, rows in tables:
        st = P.stage_table(SOURCE, P.dump_path(SOURCE, file), header, rows, source_file=P.rel(DECRYPTED),
                           retrieved_at=retrieved, extra={"decision": DECISION})
        out[file] = {"rows": st["rows"], "bytes": st["bytes"]}
        P.log(f"[{SOURCE}] staged {file}: {st['rows']:,} rows")
    out["by_year"] = {}
    for key, n in sorted(counts.items()):
        y, what = key.split("|")
        out["by_year"].setdefault(y, {})[what] = n
    return out


def main() -> int:
    P.configure_stdout()
    t0 = time.time()
    summary = {"source": SOURCE, "started_at": P.utc_now_iso(), "decision": DECISION,
               "decrypted_folder": P.rel(DECRYPTED), "staged": stage()}
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - t0, 1)
    path = STUDY_ROOT / "infosys_atp_stage_summary.json"
    path.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

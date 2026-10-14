"""R2-skeptic: my own parse of the raw files behind the Roland-Garros first-serve recount (no use of the lead's
staged tables or code, except the adapter's decrypt/blocks_of, which is the site's own step).

Writes, in data/studies/rg_first_serve_recount/review/R2-skeptic/:
    api_raw.parquet      one row per RG match code and team (A/B), 2019-2025, read from
                         data/raw/point_sources/rolandgarros/matches/<year>/<code>.json.gz: names, ids, winner,
                         endCause, status, round, court; match statistics (aces, double faults, first serve in/served,
                         win on 1st won/den, win on 2nd won/den, break points won/opps, receiving won/den, total won);
                         the same summed over the set statistics (set_*), for an internal check
    mb_points.parquet    every MatchBeats point, RG 2019-2025 (decrypted raw files; the 2025 match-centre file):
                         year, code, route, set, game, idx, server, serve, scorer, result, serveSpeed, faultSrvSpd,
                         pointId, tie-break flag
    mb_meta.parquet      one row per MatchBeats file: players per slot, status, completeness, decrypt problems
    og_stats.parquet     the Olympic results files: one row per unit, athlete and statistic (TOT and per set)
    og_units.parquet     one row per Olympic unit: status, description, players, WLT, schedule
    og_pbp.parquet       one row per Olympic play-by-play action: period, id, order, result, server, speed
    sack_rows.parquet    Sackmann's raw CSV rows of RG 2019-2025 (main and qualifying, both tours) and the Olympics
                         2024, with source_file and source_row (row number, header = 0) as the build names them

Usage: ./python.sh src/eda/rg_first_serve_recount/review/R2-skeptic/raw_tables.py
"""
from __future__ import annotations

import csv
import gzip
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"
RAW = ROOT / "data" / "raw" / "point_sources"
SACK = ROOT / "data" / "raw" / "public_dump" / "sackmann_archive"
FRAC = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")
STATS = ["aces", "doubleFaults", "firstServeRateIn", "winRateOnFirstServe", "winRateOnSecondServe", "breakPoint",
         "returnPoints", "totalPointsWon"]


def frac(v):
    m = FRAC.match(str(v)) if v is not None else None
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def integer(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------------------------------------ RG API
def api_rows() -> pd.DataFrame:
    rows = []
    for path in sorted((RAW / "rolandgarros" / "matches").glob("*/*.json.gz")):
        year, code = int(path.parent.name), path.name.split(".")[0]
        doc = json.loads(gzip.open(path).read())
        m = doc.get("match") or {}
        md = m.get("matchData") or {}
        sec = doc.get("matchStatisticsSection") or {}
        ms = sec.get("matchStatistics") or {}
        sets = [v for k, v in sec.items() if k.startswith("setStatistics") and isinstance(v, dict)]
        for t, o in (("A", "B"), ("B", "A")):
            team = m.get(f"team{t}") or {}
            pl = (team.get("players") or [{}])[0] or {}
            opp = ((m.get(f"team{o}") or {}).get("players") or [{}])[0] or {}
            rec = {"year": year, "code": code, "team": t, "type": md.get("type"), "round_label": md.get("roundLabel"),
                   "round_num": md.get("round"), "court": md.get("courtName"), "status": md.get("status"),
                   "duration": md.get("durationInMinutes"), "date": md.get("dateSchedule"),
                   "first": pl.get("firstName"), "last": pl.get("lastName"), "rg_id": pl.get("id"),
                   "opp_first": opp.get("firstName"), "opp_last": opp.get("lastName"),
                   "winner": team.get("winner"), "end_cause": team.get("endCause"),
                   "sets_score": json.dumps([(s.get("score"), s.get("tieBreak")) for s in team.get("sets") or []]),
                   "has_stats": bool(ms)}

            def val(block, stat, side):
                x = (block.get(stat) or {}).get(f"team{side}Value")
                return x
            rec["ace"] = integer(val(ms, "aces", t))
            rec["df"] = integer(val(ms, "doubleFaults", t))
            rec["first_in"], rec["svpt"] = frac(val(ms, "firstServeRateIn", t))
            rec["first_won"], rec["first_won_den"] = frac(val(ms, "winRateOnFirstServe", t))
            rec["second_won"], rec["second_won_den"] = frac(val(ms, "winRateOnSecondServe", t))
            rec["bp_won"], rec["bp_opps"] = frac(val(ms, "breakPoint", t))
            rec["ret_won"], rec["ret_den"] = frac(val(ms, "returnPoints", t))
            rec["total_won"] = integer(val(ms, "totalPointsWon", t))
            rec["first_in_text"] = val(ms, "firstServeRateIn", t)
            # the set statistics summed
            tot = {k: 0 for k in ("ace", "df", "first_in", "svpt", "first_won", "second_won", "second_den")}
            ok = bool(sets)
            for s in sets:
                fi, sv = frac(val(s, "firstServeRateIn", t))
                fw, _ = frac(val(s, "winRateOnFirstServe", t))
                sw, sd = frac(val(s, "winRateOnSecondServe", t))
                a, d = integer(val(s, "aces", t)), integer(val(s, "doubleFaults", t))
                if None in (fi, sv, fw, sw, sd, a, d):
                    ok = False
                    continue
                for k, x in zip(tot, (a, d, fi, sv, fw, sw, sd)):
                    tot[k] += x
            rec.update({f"set_{k}": (v if ok else None) for k, v in tot.items()})
            rec["n_sets_stats"] = len(sets)
            rows.append(rec)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ MatchBeats
def mb_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    from src.ingest.point_sources import common as P
    from src.ingest.point_sources import infosys_slams as I
    pts, meta = [], []
    base = RAW / "infosys_slams" / "RG"
    for path in sorted(base.glob("*/*/*.json.gz")):
        year, route, code = int(path.parts[-3]), path.parts[-2], path.name.split(".")[0]
        if route not in ("match-beats", "match-centre", "match-beats-api"):
            continue
        rec = {"year": year, "code": code, "route": route}
        try:
            blocks = I.blocks_of(route, P.read_json(path))
        except Exception as err:          # noqa: BLE001 - recorded
            meta.append({**rec, "problem": f"read: {err}"})
            continue
        if "mbData" not in blocks:
            meta.append({**rec, "problem": "no mbData"})
            continue
        try:
            doc = I.decrypt(blocks["mbData"])
        except Exception as err:          # noqa: BLE001 - recorded
            meta.append({**rec, "problem": f"decrypt: {err}"})
            continue
        if not isinstance(doc, dict) or not doc.get("setData"):
            meta.append({**rec, "problem": "empty"})
            continue
        pdat = doc.get("playerData") or {}
        meta.append({**rec, "problem": None, "court": doc.get("courtName"), "complete": doc.get("isMatchComplete"),
                     "status": doc.get("matchStatus"), "winner_slot": doc.get("matchWinner"),
                     "event_type": doc.get("eventType"),
                     **{f"p{k}_{f}": pdat.get(f"tm{k}Ply1{F}") for k in (1, 2)
                        for f, F in (("first", "FirstName"), ("last", "LastName"), ("id", "Id"), ("name", "Name"))}})
        i = 0
        for s in doc.get("setData") or []:
            for g in s.get("gameData") or []:
                for p in g.get("pointData") or []:
                    i += 1
                    pts.append({"year": year, "code": code, "route": route, "set": s.get("set"),
                                "game": g.get("game"), "tb": bool(g.get("isTieBreak")), "idx": i,
                                "pointId": p.get("pointId"), "server": str(p.get("server")),
                                "serve": str(p.get("serve")), "scorer": str(p.get("scorer")),
                                "result": p.get("result"), "speed": p.get("serveSpeed"),
                                "fault_speed": p.get("faultSrvSpd"), "is_bp": p.get("isBrkPt")})
    return pd.DataFrame(pts), pd.DataFrame(meta)


# ------------------------------------------------------------------------------------------------ Olympics
def og_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    stats, units, pbp = [], [], []
    for path in sorted((RAW / "olympics" / "OG2024" / "RES_ByRSC_H2H").glob("*.json.gz")):
        unit = path.name.split(".")[0]
        doc = json.loads(gzip.open(path).read()).get("results") or {}
        eu = doc.get("eventUnit") or {}
        items = doc.get("items") or []
        u = {"unit": unit, "description": eu.get("description"), "status": (doc.get("status") or {}).get("code"),
             "sched_status": ((doc.get("schedule") or {}).get("status") or {}).get("code"),
             "court": ((doc.get("schedule") or {}).get("location") or {}).get("shortDescription"),
             "match_status": next((e.get("ei_value") for e in doc.get("extendedInfos") or []
                                   if e.get("ei_code") == "MATCH_STATUS"), None),
             "n_items": len(items)}
        for k, it in enumerate(items):
            pa = it.get("participant") or {}
            side = "home" if k == 0 else "away"
            u.update({f"{side}_code": it.get("athleteCode"), f"{side}_name": pa.get("name"),
                      f"{side}_given": pa.get("givenName"), f"{side}_family": pa.get("familyName"),
                      f"{side}_wlt": it.get("resultWLT"), f"{side}_irm": it.get("irm")})
            for st in it.get("statsItems") or []:
                ext = {e.get("code"): e.get("value") for e in st.get("extendedStatsItems") or []}
                stats.append({"unit": unit, "athlete_code": it.get("athleteCode"), "side": side,
                              "code": st.get("code"), "pos": st.get("pos"), "value": integer(st.get("value")),
                              "attempt": integer(st.get("attempt")), "points_won": integer(ext.get("POINTS_WON")),
                              "ext_ace": integer(ext.get("ACE"))})
        units.append(u)
        for per in doc.get("playByPlay") or []:
            for a in per.get("actions") or []:
                ext = a.get("extendedActions") or []
                server = next((e.get("pbpea_value") for e in ext if e.get("pbpea_code") == "SERVER"), None)
                pbp.append({"unit": unit, "period": per.get("subcode"), "pbpa_period": a.get("pbpa_period"),
                            "id": a.get("pbpa_id"), "order": a.get("pbpa_order"), "action": a.get("pbpa_Action"),
                            "desc": a.get("pbpa_ActionDesc"), "result": a.get("pbpa_Result"),
                            "speed": a.get("pbpa_Speed"), "server": server,
                            "score_h": a.get("pbpa_ScoreH"), "score_a": a.get("pbpa_ScoreA")})
    return pd.DataFrame(stats), pd.DataFrame(units), pd.DataFrame(pbp)


# ------------------------------------------------------------------------------------------------ Sackmann
def sack_rows() -> pd.DataFrame:
    frames = []
    files = []
    for y in range(2019, 2026):
        files += [SACK / "atp" / f"atp_matches_{y}.csv", SACK / "atp" / f"atp_matches_qual_chall_{y}.csv",
                  SACK / "wta" / f"wta_matches_{y}.csv", SACK / "wta" / f"wta_matches_qual_itf_{y}.csv"]
    for f in files:
        if not f.exists():
            continue
        with open(f, encoding="utf-8", newline="") as fh:
            rows = list(csv.reader(fh))
        head = rows[0]
        keep = []
        for i, r in enumerate(rows[1:], 1):
            d = dict(zip(head, r))
            name = d.get("tourney_name", "")
            if (d.get("tourney_id", "").endswith("-520") or "roland" in name.lower() or "olympic" in name.lower()):
                d["source_row"] = i
                keep.append(d)
        df = pd.DataFrame(keep)
        df["source_file"] = f.relative_to(ROOT).as_posix()
        df["tour"] = "M" if f.parent.name == "atp" else "W"
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    a = api_rows()
    a.to_parquet(OUT / "api_raw.parquet", index=False)
    print("api", a.shape, a.groupby("year").size().to_dict())
    s = sack_rows()
    s.to_parquet(OUT / "sack_rows.parquet", index=False)
    print("sackmann", s.shape, s.groupby(["tourney_name"]).size().to_dict())
    st, un, pb = og_tables()
    st.to_parquet(OUT / "og_stats.parquet", index=False)
    un.to_parquet(OUT / "og_units.parquet", index=False)
    pb.to_parquet(OUT / "og_pbp.parquet", index=False)
    print("olympics", st.shape, un.shape, pb.shape)
    pts, meta = mb_tables()
    pts.to_parquet(OUT / "mb_points.parquet", index=False)
    meta.to_parquet(OUT / "mb_meta.parquet", index=False)
    print("mb", pts.shape, meta.shape, meta["problem"].value_counts(dropna=False).to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""R2-skeptic (round 2): my own parse of Roland Garros's raw records, 2019-2026.

Nothing of the lead's code or tables is used here; only the adapter's decrypt/blocks_of/read_json (the site's own
decryption step).

Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    api.parquet       one row per RG match code and team (A/B), from
                      data/raw/point_sources/rolandgarros/matches/<year>/<code>.json.gz: names, ids, winner, endCause,
                      status, round label, court, duration, the set scores (games, tie-break points), the match
                      statistics (aces, double faults, first serve in/served, win on 1st won/den, win on 2nd won/den,
                      break points won/opportunities, receiving won/den, total points won) and the set statistics summed
    mb_points.parquet every MatchBeats point, 2019-2026 (one route per match: match-beats, else match-centre, else
                      match-beats-api): set, game, tie-break flag, point order, server, serve, scorer, result,
                      serve and fault speeds, pointId, firstServer
    mb_meta.parquet   one row per MatchBeats file used: players per slot, status, completeness, winner, problems
    keystats.parquet  RG's Infosys key statistics (2025 match-centre 'stats' block, 2026 keystats-api), set0, per player
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/parse.py
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
RAW = ROOT / "data" / "raw" / "point_sources"
FRAC = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")


def frac(v):
    m = FRAC.match(str(v)) if v is not None else None
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def integer(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


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
            oteam = m.get(f"team{o}") or {}
            rec = {"year": year, "code": code, "team": t, "type": md.get("type"), "round_label": md.get("roundLabel"),
                   "court": md.get("courtName"), "status": md.get("status"), "status_label": md.get("statusLabel"),
                   "duration": md.get("durationInMinutes"), "date": md.get("dateSchedule"),
                   "first": pl.get("firstName"), "last": pl.get("lastName"), "rg_id": pl.get("id"),
                   "opp_first": opp.get("firstName"), "opp_last": opp.get("lastName"),
                   "winner": team.get("winner"), "end_cause": team.get("endCause"),
                   "opp_end_cause": oteam.get("endCause"), "has_service": team.get("hasService"),
                   "set_games": json.dumps([s.get("score") for s in team.get("sets") or []]),
                   "set_tb": json.dumps([s.get("tieBreak") for s in team.get("sets") or []]),
                   "opp_set_games": json.dumps([s.get("score") for s in oteam.get("sets") or []]),
                   "opp_set_tb": json.dumps([s.get("tieBreak") for s in oteam.get("sets") or []]),
                   "has_stats": bool(ms)}

            def val(block, stat, side):
                return (block.get(stat) or {}).get(f"team{side}Value")
            rec["ace"] = integer(val(ms, "aces", t))
            rec["df"] = integer(val(ms, "doubleFaults", t))
            rec["first_in"], rec["svpt"] = frac(val(ms, "firstServeRateIn", t))
            rec["first_won"], rec["first_won_den"] = frac(val(ms, "winRateOnFirstServe", t))
            rec["second_won"], rec["second_won_den"] = frac(val(ms, "winRateOnSecondServe", t))
            rec["bp_won"], rec["bp_opps"] = frac(val(ms, "breakPoint", t))
            rec["ret_won"], rec["ret_den"] = frac(val(ms, "returnPoints", t))
            rec["total_won"] = integer(val(ms, "totalPointsWon", t))
            tot = {k: 0 for k in ("ace", "df", "first_in", "svpt", "first_won", "second_won")}
            ok = bool(sets)
            for s in sets:
                fi, sv = frac(val(s, "firstServeRateIn", t))
                fw, _ = frac(val(s, "winRateOnFirstServe", t))
                sw, _ = frac(val(s, "winRateOnSecondServe", t))
                a, d = integer(val(s, "aces", t)), integer(val(s, "doubleFaults", t))
                if None in (fi, sv, fw, sw, a, d):
                    ok = False
                    continue
                for k, x in zip(tot, (a, d, fi, sv, fw, sw)):
                    tot[k] += x
            rec.update({f"set_{k}": (v if ok else None) for k, v in tot.items()})
            rec["n_set_blocks"] = len(sets)
            rows.append(rec)
    return pd.DataFrame(rows)


def mb_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    from src.ingest.point_sources import common as P
    from src.ingest.point_sources import infosys_slams as I
    order = {"match-beats": 0, "match-centre": 1, "match-beats-api": 2}
    files: dict[tuple, tuple] = {}
    for path in sorted((RAW / "infosys_slams" / "RG").glob("*/*/*.json.gz")):
        year, route, code = int(path.parts[-3]), path.parts[-2], path.name.split(".")[0]
        if route not in order:
            continue
        key = (year, code)
        if key not in files or order[route] < order[files[key][0]]:
            files[key] = (route, path)
    pts, meta = [], []
    for (year, code), (route, path) in sorted(files.items()):
        rec = {"year": year, "code": code, "route": route}
        try:
            blocks = I.blocks_of(route, P.read_json(path))
            doc = I.decrypt(blocks["mbData"]) if "mbData" in blocks else None
        except Exception as err:   # noqa: BLE001 - recorded, never silently dropped
            meta.append({**rec, "problem": f"{type(err).__name__}: {err}"})
            continue
        if not isinstance(doc, dict) or not doc.get("setData"):
            meta.append({**rec, "problem": "empty"})
            continue
        pdat = doc.get("playerData") or {}
        meta.append({**rec, "problem": None, "court": doc.get("courtName"), "complete": doc.get("isMatchComplete"),
                     "status": doc.get("matchStatus"), "winner_slot": doc.get("matchWinner"),
                     "sets_complete": doc.get("setsComplete"), "event_type": doc.get("eventType"),
                     **{f"p{k}_{f}": pdat.get(f"tm{k}Ply1{F}") for k in (1, 2)
                        for f, F in (("first", "FirstName"), ("last", "LastName"), ("id", "Id"), ("name", "Name"))}})
        i = 0
        for si, s in enumerate(doc.get("setData") or [], 1):
            for gi, g in enumerate(s.get("gameData") or [], 1):
                for p in g.get("pointData") or []:
                    i += 1
                    pts.append({"year": year, "code": code, "set": s.get("set", si), "set_i": si,
                                "game": g.get("game", gi), "game_i": gi, "tb": bool(g.get("isTieBreak")),
                                "game_winner": g.get("gameWinner"), "idx": i, "pointId": p.get("pointId"),
                                "server": str(p.get("server")), "serve": str(p.get("serve")),
                                "scorer": str(p.get("scorer")), "result": p.get("result"),
                                "speed": p.get("serveSpeed"), "fault_speed": p.get("faultSrvSpd"),
                                "first_server": p.get("firstServer"), "tm1_score": p.get("tm1GameScore"),
                                "tm2_score": p.get("tm2GameScore")})
    return pd.DataFrame(pts), pd.DataFrame(meta)


def keystats() -> pd.DataFrame:
    from src.ingest.point_sources import common as P
    from src.ingest.point_sources import infosys_slams as I
    rows = []
    for year, route in ((2025, "match-centre"), (2026, "keystats-api")):
        for path in sorted((RAW / "infosys_slams" / "RG" / str(year) / route).glob("*.json.gz")):
            code = path.name.split(".")[0]
            try:
                blocks = I.blocks_of(route, P.read_json(path))
                doc = I.decrypt(blocks["stats"]) if "stats" in blocks else None
            except Exception as err:   # noqa: BLE001
                rows.append({"year": year, "code": code, "problem": str(err)})
                continue
            if not isinstance(doc, dict) or not (doc.get("setStats") or {}).get("set0"):
                continue
            st = {r.get("name"): r for r in doc["setStats"]["set0"]}
            players = doc.get("players") or [{}, {}]
            for j, k in ((0, "1"), (1, "2")):
                o = "2" if k == "1" else "1"

                def v(name, who=k):
                    return (st.get(name) or {}).get(f"player{who}")
                fi, sv = frac(v("First Serve"))
                bw, bo = frac(v("Break Points Won", o))
                pl = players[j] if j < len(players) else {}
                rows.append({"year": year, "code": code, "slot": int(k), "problem": None,
                             "first": pl.get("player1FirstName"), "last": pl.get("player1LastName"),
                             "completed": doc.get("matchCompleted"),
                             "ks_ace": integer(v("Aces")), "ks_df": integer(v("Double Faults")), "ks_svpt": sv,
                             "ks_first_in": fi, "ks_first_won": frac(v("Win On 1st Serve"))[0],
                             "ks_second_won": frac(v("Win On 2nd Serve"))[0], "ks_bp_faced": bo,
                             "ks_bp_saved": (bo - bw) if bo is not None and bw is not None else None})
    return pd.DataFrame(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    a = api_rows()
    a.to_parquet(OUT / "api.parquet", index=False)
    print("api", a.shape, a.groupby("year").size().to_dict(), "with stats:", int(a["has_stats"].sum()))
    k = keystats()
    k.to_parquet(OUT / "keystats.parquet", index=False)
    print("keystats", k.shape, k.groupby("year").size().to_dict())
    pts, meta = mb_tables()
    pts.to_parquet(OUT / "mb_points.parquet", index=False)
    meta.to_parquet(OUT / "mb_meta.parquet", index=False)
    print("mb", pts.shape, meta.shape, meta.groupby(["year", "route"]).size().to_dict(),
          meta["problem"].value_counts(dropna=False).to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Source reconciliation, Part G (serve speed): checks of the readers and of two definitional facts. Reads no result.

1. Hand checks (the brief's rule 8). For every reader, 5 random linked valid records with a speed (seed 20261016):
   the staged rows of that match are re-read and recounted here by a plain loop, independently of spd_readers'
   vectorised aggregation (point copies: the player's points, first serves in, timed first serves in and their mean;
   aggregates: the published values re-parsed from the staged row), and the source's player names are printed beside
   the snapshot's names for the side the record was placed on. The printout is what was read by eye; reader_checks.json
   keeps the keys, both computations and the names.
2. Definitional facts, point by point: the rally analysis's speed against MatchBeats' for the same pointId (the ATP host
   and RG 2025), and the rally reader's server against MatchBeats' server (spd_readers.rally_servers, against the
   per-point shot-parity rule of shot_level.points that the panel's "infosys" point means used).

Run: ./python.sh src/eda/source_reconciliation/spd_checks.py   (after spd_build.py)
Writes speed/reader_checks.json
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import spd_readers as R  # noqa: E402

OUT = C.OUT / "speed"
SEED = 20261016
PER_READER = 5


def ok_speed(v) -> float | None:
    try:
        x = float(str(v).replace("KPH", "").replace("KMH", "").strip())
    except ValueError:
        return None
    return x if 40.0 < x <= 270.0 else None


def recount(points: list[tuple]) -> dict:
    """points: (slot, serve number, is double fault, speed or None) for every point of the match."""
    out = {}
    for slot in (1, 2):
        mine = [p for p in points if p[0] == slot]
        first_in = [p for p in mine if p[1] == 1 and not p[2]]
        timed = [p[3] for p in first_in if p[3] is not None]
        out[slot] = {"points": len(mine), "first_in": len(first_in), "timed_first_in": len(timed),
                     "mean": (sum(timed) / len(timed)) if timed else None}
    return out


# ------------------------------------------------------------------------------------------------ per-source recounts
def rc_mb(src: str, key: str) -> dict:
    if src == "mb_slams":
        slam, year, mid = key.split("_", 2)
        p = pd.read_parquet(R.DUMP_PTS / "infosys_slams" / "points.parquet",
                            filters=[("slam", "==", slam), ("match_id", "==", mid)])
        p = p[p["year"].astype(str).eq(year)]
        dfs = {"DF"}
    else:
        year, ev, mid = key.split("_", 2)
        p = pd.read_parquet(R.DUMP_PTS / "infosys_atp" / "points.parquet", filters=[("match_id", "==", mid)])
        p = p[p["year"].astype(str).eq(year) & p["event_id"].astype(str).eq(ev)]
        dfs = {"DF", "P"}
    pts = [(int(s), int(sv), str(res) in dfs, ok_speed(sp)) for s, sv, res, sp in
           zip(p["server"], p["serve"], p["result"], p["serveSpeed"]) if str(s) in ("1", "2")]
    return recount(pts)


def rc_ra_atp(key: str) -> dict:
    """The ATP host's rally entries, the server taken from MatchBeats by pointId (an independent server)."""
    year, ev, mid = key.split("_", 2)
    r = pd.read_parquet(R.DUMP_PTS / "infosys_atp" / "rally.parquet", filters=[("match_id", "==", mid)])
    r = r[r["year"].astype(str).eq(year) & r["event_id"].astype(str).eq(ev)].drop_duplicates("pointId")
    p = pd.read_parquet(R.DUMP_PTS / "infosys_atp" / "points.parquet", filters=[("match_id", "==", mid)])
    p = p[p["year"].astype(str).eq(year) & p["event_id"].astype(str).eq(ev)]
    srv = dict(zip(p["pointId"], p["server"]))
    pts = [(int(srv[pid]), int(sv), str(pet).upper() == "DOUBLE FAULT", ok_speed(sp))
           for pid, sv, pet, sp in zip(r["pointId"], r["serve"], r["pointEndType"], r["serveSpeed"]) if pid in srv]
    return recount(pts)


def _parity_servers(entries: list[dict]) -> dict:
    """A second, loop-based implementation of the set-parity server rule (spd_readers.rally_servers)."""
    shot_no = R.INFOSYS_SHOT
    votes: dict = {}
    for e in entries:
        s, g, k = (int(x) for x in e["pointId"].split("_")[:3])
        shot = shot_no.get(e["category"], 0)
        team = 1 if e["list"].startswith("t1") else 2
        if shot == 0 or str(e.get("pointEndType")).upper() == "DOUBLE FAULT":
            continue
        hitter_serves = shot % 2 == 1
        gsrv = team if hitter_serves else 3 - team
        if e.get("tieBreak") in (True, "true", "TRUE", 1, "1"):
            gsrv = gsrv if (k // 2) % 2 == 0 else 3 - gsrv
        first = gsrv if g % 2 == 1 else 3 - gsrv
        votes.setdefault(s, []).append(first)
    first_of = {s: (1 if v.count(1) > len(v) / 2 else 2 if v.count(2) > len(v) / 2 else 0) for s, v in votes.items()}
    out = {}
    for e in entries:
        s, g, k = (int(x) for x in e["pointId"].split("_")[:3])
        f = first_of.get(s, 0)
        if not f:
            continue
        gs = f if g % 2 == 1 else 3 - f
        if e.get("tieBreak") in (True, "true", "TRUE", 1, "1"):
            gs = gs if (k // 2) % 2 == 0 else 3 - gs
        out[e["pointId"]] = gs
    return out


def rc_ra_handoff(key: str) -> dict:
    """The raw handoff line(s) of this match: the copy with the most rally entries, servers by a loop re-implementation."""
    year = key.split("_")[0]
    best = None
    for folder in ("infosys_full", "infosys_deep"):
        for path in sorted((C.HANDOFF / folder).glob(f"{year}_data.jsonl*")):
            op = gzip.open if str(path).endswith(".gz") else open
            with op(path, "rt", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if key.split("_", 2)[2] not in line.upper():
                        continue
                    rec = json.loads(line)
                    k = f"{rec.get('year')}_{rec.get('tournament_id')}_{str(rec.get('match_id')).upper()}"
                    if k != key:
                        continue
                    ents = []
                    for cat in ((rec.get("rally_analysis") or {}).get("rallyData") or []):
                        for lst in ("t1win", "t1err", "t2win", "t2err"):
                            for pt in cat.get(lst) or []:
                                ents.append({"category": cat.get("name"), "list": lst, **pt})
                    if best is None or len(ents) > len(best[0]):
                        best = (ents, rec.get("player1_name"), rec.get("player2_name"), folder)
    if best is None:
        return {"error": "raw line not found"}
    ents = {e["pointId"]: e for e in best[0]}
    srv = _parity_servers(list(ents.values()))
    pts = [(srv[pid], int(e.get("serve") or 0), str(e.get("pointEndType")).upper() == "DOUBLE FAULT",
            ok_speed(e.get("serveSpeed"))) for pid, e in ents.items() if pid in srv]
    out = recount(pts)
    out["names"] = [best[1], best[2]]
    out["folder"] = best[3]
    return out


def rc_ra_sirgenkii(key: str) -> dict:
    base = R.DUMP_PTS / "sirgenkii_infotennis"
    year, tid, mid = key.split("_", 2)
    res = pd.read_parquet(base / "atp_results.parquet")
    res = res[res["year"].astype(str).eq(year) & res["tournament_id"].astype(str).eq(tid)
              & res["match_id"].astype(str).eq(mid)].iloc[0]
    ra = pd.read_parquet(base / "atp_rally_analysis.parquet")
    ra = ra[ra["year"].astype(str).eq(year) & ra["tournament_id"].astype(str).eq(tid)
            & ra["match_id"].astype(str).eq(mid)].drop_duplicates("point_id")
    names = {"1": "Serve", "2": "Return", "3": "3rd shot", "4": "4th shot", "5": "5th shot", "6": "6th shot",
             "7": "7th shot", "8": "8th shot", "9+_odd": "9+_odd", "10+_even": "10+_even"}
    ents = []
    for _, x in ra.iterrows():
        team = 1 if str(x["player_id"]).upper() == str(res["player1_id"]).upper() else 2
        ents.append({"pointId": str(x["point_id"]), "category": names.get(str(x["shot_number"]), "UNCLASSIFIED"),
                     "list": f"t{team}{'win' if str(x['outcome']) == 'W' else 'err'}", "serve": x["serve"],
                     "serveSpeed": x["serve_speed"], "pointEndType": x["point_end_type"],
                     "tieBreak": str(x["tie_break"]) == "1"})
    srv = _parity_servers(ents)
    pts = [(srv[e["pointId"]], int(e["serve"]), str(e["pointEndType"]).upper() == "DOUBLE FAULT",
            ok_speed(e["serveSpeed"])) for e in ents if e["pointId"] in srv]
    out = recount(pts)
    out["names"] = [res["player1_name"], res["player2_name"]]
    return out


def rc_ibm(key: str) -> dict:
    site, year, event, mid = key.split("_", 3)
    p = pd.read_parquet(R.DUMP_PTS / site / "points.parquet", filters=[("event", "==", event), ("match_id", "==", mid)])
    p = p[p["year"].astype(str).eq(year)]
    pts = []
    for srv, win, sn, dfl, sp in zip(p["PointServer"], p["PointWinner"], p["ServeNumber"], p["DoubleFault"],
                                     p["Speed_KMH"]):
        if str(srv) not in ("1", "2") or str(win) not in ("1", "2"):
            continue
        is_df = str(dfl) not in ("0", "", "nan", "None")
        sv = 2 if is_df else int(float(sn or 0))
        pts.append((int(srv), sv, is_df, ok_speed(sp) if str(sp) not in ("0", "") else None))
    return recount(pts)


def rc_sackmann(key: str) -> dict:
    year, slam, num = key.split("-", 2)
    p = pd.read_parquet(R.DUMP_PTS / "sackmann_archive" / "slam_pointbypoint" / f"{year}-{slam}-points.parquet")
    p = p[p["match_id"].astype(str).eq(key)]
    pts = []
    for _, x in p.iterrows():
        if "X" in str(x["PointNumber"]) or "Y" in str(x["PointNumber"]):
            continue
        srv, win = str(x["PointServer"]), str(x["PointWinner"])
        if srv not in ("1", "2") or win not in ("1", "2"):
            continue
        is_df = any(str(x.get(c, 0)) not in ("0", "", "nan", "None") for c in ("P1DoubleFault", "P2DoubleFault"))
        sn = str(x.get("ServeNumber", ""))
        if sn in ("1", "2"):
            sv = int(sn)
        else:
            fin = any(str(x.get(c, 0)) not in ("0", "", "nan") for c in ("P1FirstSrvIn", "P2FirstSrvIn"))
            sv = 1 if fin else 2
        sp = x.get("Speed_KMH")
        pts.append((int(srv), sv, is_df, ok_speed(sp) if str(sp) not in ("0", "") else None))
    return recount(pts)


def rc_hawkeye(key: str) -> dict:
    slam, year, mid = key.split("_", 2)
    m = pd.read_parquet(R.DUMP_PTS / "slam_ball_tracking" / "matches.parquet")
    m = m[m["slam"].astype(str).eq(slam) & m["year"].astype(str).eq(year) & m["match_id"].astype(str).eq(mid)].iloc[0]
    p = pd.read_parquet(R.DUMP_PTS / "slam_ball_tracking" / "points" / f"{slam}_{year}.parquet")
    p = p[p["match_id"].astype(str).eq(mid)]
    pts = []
    for sid, sn, pet, sp in zip(p["server_id"], p["serve_num"], p["point_end_type"], p["serve_speed_kph"]):
        if str(pet) == "Faulty Serve":
            continue
        slot = 1 if str(sid) == str(m["player1_id"]) else 2 if str(sid) == str(m["player2_id"]) else 0
        if slot:
            pts.append((slot, int(float(sn)), str(pet) == "DoubleFault", ok_speed(str(sp).split(" ")[0])))
    out = recount(pts)
    out["names"] = [m["player1"], m["player2"]]
    return out


def rc_stat(src: str, key: str, pno: int) -> dict:
    """The published values re-read from the staged row(s)."""
    if src == "ks_mantd":
        y = int(key.split("-")[0])
        t = pd.read_parquet(R.MTD_DIR / f"atp_matches_{y}.parquet")
        row = t[t["id"].astype(str).eq(key)].iloc[0]
        s = "win" if pno == 1 else "los"
        return {"v1": row[f"{s}_average_first_serves_kmh"], "v2": row[f"{s}_average_second_serve_kmh"],
                "first_in": row[f"{s}_first_serves_in"], "first_total": row[f"{s}_first_serves_total"],
                "name": row["winner_name" if pno == 1 else "loser_name"], "raw_file": row["_source_file"],
                "raw_row": int(row["_row"])}
    if src in ("ks_atp", "ks_rg"):
        if src == "ks_atp":
            year, ev, mid = key.split("_", 2)
            k = pd.read_parquet(R.DUMP_PTS / "infosys_atp" / "keystats.parquet", filters=[("match_id", "==", mid)])
            k = k[k["year"].astype(str).eq(year) & k["event_id"].astype(str).eq(ev)]
        else:
            slam, year, mid = key.split("_", 2)
            k = pd.read_parquet(R.DUMP_PTS / "infosys_slams" / "keystats.parquet", filters=[("match_id", "==", mid)])
            k = k[k["slam"].astype(str).eq(slam) & k["year"].astype(str).eq(year)]
        k = k[k["set_key"].astype(str).eq("set0")]
        return {r["name"]: r[f"player{pno}"] for _, r in k.iterrows()
                if r["name"] in ("1st Serve Average Speed", "2nd Serve Average Speed", "Max Speed", "1st Serve",
                                 "First Serve")}
    if src == "ks_sirgenkii":
        year, tid, mid = key.split("_", 2)
        base = R.DUMP_PTS / "sirgenkii_infotennis"
        res = pd.read_parquet(base / "atp_results.parquet")
        res = res[res["year"].astype(str).eq(year) & res["tournament_id"].astype(str).eq(tid)
                  & res["match_id"].astype(str).eq(mid)].iloc[0]
        pid = res["player1_id"] if pno == 1 else res["player2_id"]
        k = pd.read_parquet(base / "atp_key_stats.parquet")
        k = k[k["year"].astype(str).eq(year) & k["tournament_id"].astype(str).eq(tid) & k["match_id"].astype(str).eq(mid)
              & k["set_n"].astype(str).eq("0") & k["player_id"].astype(str).str.upper().eq(str(pid).upper())]
        return {"v1": k["serve1_avg_speed"].tolist(), "v2": k["serve2_avg_speed"].tolist(),
                "max": k["max_speed"].tolist(), "name": res["player1_name" if pno == 1 else "player2_name"]}
    if src == "ks_handoff":
        year = key.split("_")[0]
        vals = []
        for folder in ("infosys_full", "infosys_deep"):
            for path in sorted((C.HANDOFF / folder).glob(f"{year}_data.jsonl*")):
                op = gzip.open if str(path).endswith(".gz") else open
                with op(path, "rt", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if key.split("_", 2)[2] not in line.upper() or "Serve Average Speed" not in line:
                            continue
                        rec = json.loads(line)
                        if f"{rec.get('year')}_{rec.get('tournament_id')}_{str(rec.get('match_id')).upper()}" != key:
                            continue
                        s0 = rec["keystats"]["setStats"]["set0"]
                        d = {e["name"]: e[f"player{pno}"] for e in s0}
                        vals.append({"folder": folder, "1st": d.get("1st Serve Average Speed"),
                                     "2nd": d.get("2nd Serve Average Speed"), "max": d.get("Max Speed"),
                                     "first": d.get("1st Serve"), "name": rec.get(f"player{pno}_name")})
        return {"copies": vals}
    if src == "ibm_stat":
        site, year, event, mid = key.split("_", 3)
        st = pd.read_parquet(R.DUMP_PTS / site / "statistics.parquet",
                             filters=[("event", "==", event), ("match_id", "==", mid), ("period", "==", "match"),
                                      ("team", "==", f"team_{pno}")])
        st = st[st["year"].astype(str).eq(year)]
        return {k: v for k, v in zip(st["key"], st["value"]) if k in ("f_srv_a_spd", "s_srv_a_spd", "t_f_spd",
                                                                      "f_srv_p", "t_f_srv")}
    if src == "ao_mc":
        a = pd.read_parquet(R.DUMP_PTS / "ausopen" / "set_statistics.parquet", filters=[("record_key", "==", key)])
        a = a[a["set"].astype(str).eq("All") & a["stat"].isin(["1st Serve Average", "2nd serve average",
                                                                "Fastest serve", "1st serve in"])]
        return {s: (p, q) for s, p, q in zip(a["stat"], a[f"team{pno}_primary"], a[f"team{pno}_secondary"])}
    return {}


def hand_checks(rec: pd.DataFrame, s0p: pd.DataFrame) -> list[dict]:
    rng = np.random.default_rng(SEED)
    names = s0p.drop_duplicates(["match_id", "side"]).set_index(["match_id", "side"])["player_name"]
    out = []
    for src in R.READERS:
        g = rec[rec["src"].eq(src) & rec["valid"]]
        g = g[(g["n1"] >= 10) if g["kind"].iloc[0] == "points" else g["v1"].notna()]
        pick = g.iloc[rng.choice(len(g), size=min(PER_READER, len(g)), replace=False)]
        for _, r in pick.iterrows():
            key, pno = r["key"], int(r["pno"])
            if src in ("mb_slams", "mb_atp"):
                indep = rc_mb(src, key)
            elif src == "ra_atp":
                indep = rc_ra_atp(key)
            elif src == "ra_handoff":
                indep = rc_ra_handoff(key)
            elif src == "ra_sirgenkii":
                indep = rc_ra_sirgenkii(key)
            elif src == "ibm_pts":
                indep = rc_ibm(key)
            elif src == "sackmann_pts":
                indep = rc_sackmann(key)
            elif src == "hawkeye_pts":
                indep = rc_hawkeye(key)
            else:
                indep = rc_stat(src, key, pno)
            other = "B" if r["side"] == "A" else "A"
            row = {"reader": src, "key": key, "slot": pno, "match_id": r["match_id"], "side": r["side"],
                   "source_name": r["pname"], "stage0_name_on_side": names.get((r["match_id"], r["side"])),
                   "stage0_name_other_side": names.get((r["match_id"], other)), "link": r["link"],
                   "side_link": r["side_link"], "side_names": r["side_names"]}
            if r["kind"] == "points":
                mine = {"points": int(r["npts"]), "first_in": int(r["f1"]), "timed_first_in": int(r["n1"]),
                        "mean": float(r["s1"])}
                ind = indep.get(pno) if isinstance(indep, dict) else None
                row.update({"reader_value": mine, "recount": ind,
                            "recount_names": indep.get("names") if isinstance(indep, dict) else None,
                            "counts_equal": bool(ind and ind["timed_first_in"] == mine["timed_first_in"]
                                                 and ind["first_in"] == mine["first_in"]),
                            "mean_equal": bool(ind and ind["mean"] is not None and abs(ind["mean"] - mine["mean"]) < 1e-9)})
            else:
                row.update({"reader_value": {"v1": r["v1"], "v2": r["v2"], "vmax": r["vmax"], "vfin": r["vfin"],
                                             "vftot": r["vftot"]}, "staged": indep})
            out.append(row)
    return out


def definitional() -> dict:
    """Rally analysis against MatchBeats point by point (speed and server)."""
    res = {}
    for src, keycols in (("infosys_atp", ["year", "event_id", "match_id"]), ("infosys_slams", ["slam", "year", "match_id"])):
        p = pd.read_parquet(R.DUMP_PTS / src / "points.parquet", columns=keycols + ["pointId", "server", "serveSpeed"])
        r = pd.read_parquet(R.DUMP_PTS / src / "rally.parquet", columns=keycols + ["category", "list", "pointId", "serve",
                                                                                 "serveSpeed", "pointEndType",
                                                                                 "tieBreak"])
        for t in (p, r):
            t["key"] = t[keycols].astype(str).agg("_".join, axis=1)
        r = r.drop_duplicates(["key", "pointId"]).reset_index(drop=True)
        r["srv_set"] = R.rally_servers(r)
        shot = r["category"].map(R.INFOSYS_SHOT).fillna(0).astype(int)
        team = np.where(r["list"].astype(str).str.startswith("t1"), 1, 2)
        r["srv_point"] = np.where(shot > 0, np.where(shot % 2 == 1, team, 3 - team), 0)
        j = r.merge(p[["key", "pointId", "server", "serveSpeed"]], on=["key", "pointId"], suffixes=("_ra", "_mb"))
        j["server"] = pd.to_numeric(j["server"], errors="coerce")
        a, b = pd.to_numeric(j["serveSpeed_ra"], errors="coerce"), pd.to_numeric(j["serveSpeed_mb"], errors="coerce")
        t = (a > 0) & (b > 0)
        d = (a - b)[t]
        cls = j["srv_point"] > 0
        res[src] = {"joined_points": int(len(j)), "timed_both": int(t.sum()),
                    "rally_minus_matchbeats_kmh": {str(k): int(v) for k, v in d.value_counts().items()},
                    "mean_difference_kmh": float(d.mean()) if len(d) else None,
                    "server_per_point_rule_agrees_on_classified": float((j.loc[cls, "srv_point"]
                                                                         == j.loc[cls, "server"]).mean()),
                    "server_per_point_rule_by_year": {str(y): float(g_["ok"].mean()) for y, g_ in
                                                      j[cls].assign(ok=j["srv_point"] == j["server"]).groupby(
                                                          j[cls]["key"].str.split("_").str[0 if src == "infosys_atp"
                                                                                          else 1])},
                    "server_set_rule_assigned_share": float((j["srv_set"] > 0).mean()),
                    "server_set_rule_agrees": float((j.loc[j["srv_set"] > 0, "srv_set"]
                                                     == j.loc[j["srv_set"] > 0, "server"]).mean())}
    return res


def main() -> int:
    rec = pd.read_parquet(OUT / "records.parquet")
    _, s0p = C.stage0(["match_id"], ["match_id", "side", "player_name"])
    checks = hand_checks(rec, s0p)
    for c in checks:
        print(json.dumps(c, default=str))
    d = definitional()
    print(json.dumps(d, indent=1))
    pts = [c for c in checks if "counts_equal" in c]
    C.write_json(OUT / "reader_checks.json", {
        "seed": SEED, "per_reader": PER_READER, "reads_results": False,
        "point_readers": {"checked": len(pts), "counts_equal": int(sum(c["counts_equal"] for c in pts)),
                          "mean_equal": int(sum(c["mean_equal"] for c in pts))},
        "checks": checks, "definitional": d})
    return 0


if __name__ == "__main__":
    sys.exit(main())

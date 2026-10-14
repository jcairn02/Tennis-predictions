"""Design R1 (speed-data engineer), step 1: every per-player match serve-speed record the project holds, one row per
(source, Stage 0 match, side), with values, counts and the half-timed gate. Reads no match result.

Sources (values, not just presence):
    point tables  data/studies/shot_level/stage1_points_<src>.parquet for slam_pbp, slam_tracking, slamtracker, infosys,
                  sirgenkii: recomputed here per source (stage1_match_stats keeps only the first source in its priority
                  order), oriented with the shot-level link (stage1_stats.oriented). First serves in = serve 1 on a point
                  that is not a double fault; second serves in = serve 2, not a double fault; max = fastest timed serve
                  that started a point.
    infosys_slams data/dump/points/infosys_slams/points.parquet (AO 2025, RG 2025, RG 2026): the same definitions from
                  MatchBeats (result 'DF' = double fault), plus the first-serve fault speed (faultSrvSpd on serve-2
                  points); RG's key statistics kept alongside. Stage 0 match and side from speeds.parquet.
    mantennisdata speeds.parquet: the ATP Stats Centre key statistics (1st/2nd serve average, max, first serves in).
    handoff_ks    the Hugging Face handoff's decrypted ATP key statistics (2018-24), the same Stats Centre numbers,
                  linked through the shot-level 'infosys' link (key = year_tournament_code, a1 orientation).
    ausopen_mc    the AO match centre's plain "1st Serve Average" etc. (AO 2026 and Wayback captures), linked through the
                  shot-level 'ausopen' link.
Values outside 40-270 km/h are missing (the project's rule).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/engineer_records.py
Writes data/studies/serve_speed_tabpfn/design/engineer_records.parquet and engineer_handoff_ks.parquet (cache).
"""
from __future__ import annotations

import gzip
import json
import multiprocessing as mp
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

LO, HI = 40.0, 270.0
FIRST = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")
HANDOFF_KS = EC.OUT / "engineer_handoff_ks.parquet"
COLS = ["source", "basis", "source_key", "match_id", "side", "spd1", "n1", "f1", "spd1_sum", "spd1_sumsq", "spd2",
        "n2", "f2", "spd_max", "fault1", "nfault1", "ks_spd1", "ks_first_in", "ks_first_total", "points_missing"]


def plaus(x) -> np.ndarray:
    x = pd.to_numeric(pd.Series(x), errors="coerce").to_numpy(dtype=float)
    return np.where((x > LO) & (x <= HI), x, np.nan)


# ------------------------------------------------------------------------------------------------
def point_source(name: str, links: pd.DataFrame) -> pd.DataFrame:
    from src.eda.shot_level import stage1_stats as ST
    from src.eda.shot_level.points import END
    p = ST.oriented(name, links)
    p = p[p["server"].isin([1, 2])]
    sp = plaus(p["speed"])
    df = p["end"].to_numpy() == END["df"]
    sn = p["serve_no"].to_numpy()
    f1, f2 = (sn == 1) & ~df, (sn == 2) & ~df
    t1, t2 = f1 & np.isfinite(sp), f2 & np.isfinite(sp)
    g = pd.DataFrame({"match_id": p["match_id"].to_numpy(), "side": np.where(p["server"].to_numpy() == 1, "A", "B"),
                      "f1": f1, "n1": t1, "s1": np.where(t1, sp, 0.0), "q1": np.where(t1, sp * sp, 0.0),
                      "f2": f2, "n2": t2, "s2": np.where(t2, sp, 0.0),
                      "mx": np.where((f1 | f2) & np.isfinite(sp), sp, np.nan)})
    a = g.groupby(["match_id", "side"]).agg(f1=("f1", "sum"), n1=("n1", "sum"), spd1_sum=("s1", "sum"),
                                            spd1_sumsq=("q1", "sum"), f2=("f2", "sum"), n2=("n2", "sum"),
                                            s2=("s2", "sum"), spd_max=("mx", "max")).reset_index()
    a["spd1"] = a["spd1_sum"] / a["n1"].where(a["n1"] > 0)
    a["spd2"] = a["s2"] / a["n2"].where(a["n2"] > 0)
    keys = p.drop_duplicates("match_id").set_index("match_id")["key"]
    a["source_key"] = a["match_id"].map(keys)
    a["source"], a["basis"] = name, "point_mean"
    return a


def infosys_slams(sp_tab: pd.DataFrame) -> pd.DataFrame:
    p = pd.read_parquet(EC.INFO_SLAMS / "points.parquet", columns=["slam", "year", "match_id", "server", "serve",
                                                                  "serveSpeed", "faultSrvSpd", "result"])
    p = p[p["server"].astype(str).isin(["1", "2"])]
    spd, flt = plaus(p["serveSpeed"]), plaus(p["faultSrvSpd"])
    df = p["result"].astype(str).eq("DF").to_numpy()
    sv = p["serve"].astype(str).to_numpy()
    f1, f2 = (sv == "1") & ~df, (sv == "2") & ~df
    t1, t2 = f1 & np.isfinite(spd), f2 & np.isfinite(spd)
    fl = (sv == "2") & np.isfinite(flt)
    g = pd.DataFrame({"source_key": p["slam"].astype(str) + "_" + p["year"].astype(str) + "_" + p["match_id"].astype(str),
                      "player_no": p["server"].astype(int).to_numpy(), "f1": f1, "n1": t1, "s1": np.where(t1, spd, 0.0),
                      "q1": np.where(t1, spd * spd, 0.0), "f2": f2, "n2": t2, "s2": np.where(t2, spd, 0.0),
                      "mx": np.where((f1 | f2) & np.isfinite(spd), spd, np.nan), "fl": fl,
                      "sf": np.where(fl, flt, 0.0)})
    a = g.groupby(["source_key", "player_no"]).agg(f1=("f1", "sum"), n1=("n1", "sum"), spd1_sum=("s1", "sum"),
                                                   spd1_sumsq=("q1", "sum"), f2=("f2", "sum"), n2=("n2", "sum"),
                                                   s2=("s2", "sum"), spd_max=("mx", "max"), nfault1=("fl", "sum"),
                                                   sf=("sf", "sum")).reset_index()
    a["spd1"] = a["spd1_sum"] / a["n1"].where(a["n1"] > 0)
    a["spd2"] = a["s2"] / a["n2"].where(a["n2"] > 0)
    a["fault1"] = a["sf"] / a["nfault1"].where(a["nfault1"] > 0)
    s = sp_tab[sp_tab["source"].eq("infosys_slams")][["source_key", "player_no", "match_id", "side", "ks_spd1",
                                                      "ks_first_in", "ks_first_total"]]
    a = a.merge(s, on=["source_key", "player_no"], how="left")
    a["source"], a["basis"] = "infosys_slams", "point_mean"
    return a


def mantennisdata(sp_tab: pd.DataFrame) -> pd.DataFrame:
    m = sp_tab[sp_tab["source"].eq("mantennisdata")].copy()
    out = pd.DataFrame({"source": "mantennisdata", "basis": "keystat_atp", "source_key": m["source_key"],
                        "match_id": m["match_id"], "side": m["side"], "spd1": m["ks_spd1"], "n1": m["ks_first_in"],
                        "f1": m["ks_first_in"], "spd2": m["ks_spd2"],
                        "n2": m["ks_first_total"] - m["ks_first_in"], "spd_max": m["ks_max"], "ks_spd1": m["ks_spd1"],
                        "ks_first_in": m["ks_first_in"], "ks_first_total": m["ks_first_total"]})
    return out


def side_of(a1: pd.Series, player_no: pd.Series) -> np.ndarray:
    """Stage 0 side of a source player: player 1 is A when a1 is True; unknown when a1 is missing."""
    t = a1.eq(True).fillna(False).to_numpy(dtype=bool)
    f = a1.eq(False).fillna(False).to_numpy(dtype=bool)
    one = (player_no.astype(int) == 1).to_numpy(dtype=bool)
    return np.select([(t & one) | (f & ~one), (t & ~one) | (f & one)], ["A", "B"], default=None)


# ------------------------------------------------------------------------------------------------
def _handoff_file(path: str) -> list[tuple]:
    rows = []
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "Serve Average Speed" not in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            ks = (r.get("keystats") or {}) if isinstance(r.get("keystats"), dict) else {}
            s0 = ((ks.get("setStats") or {}).get("set0")) or []
            d = {e.get("name"): (e.get("player1"), e.get("player2")) for e in s0 if isinstance(e, dict)}
            if "1st Serve Average Speed" not in d:
                continue
            ra = r.get("rally_analysis") if isinstance(r.get("rally_analysis"), dict) else {}
            pm = ra.get("pointsMissing")
            for no in (0, 1):
                fs = FIRST.match(str((d.get("1st Serve") or (None, None))[no] or ""))
                rows.append((str(r.get("year")), str(r.get("tournament_id")), str(r.get("match_id")).upper(), no + 1,
                             (d.get("1st Serve Average Speed") or (None, None))[no],
                             (d.get("2nd Serve Average Speed") or (None, None))[no],
                             (d.get("Max Speed") or (None, None))[no],
                             int(fs.group(1)) if fs else np.nan, int(fs.group(2)) if fs else np.nan,
                             None if pm is None else bool(pm), path.split("atp_pipeline_handoff")[-1]))
    return rows


def handoff_ks() -> pd.DataFrame:
    if HANDOFF_KS.exists():
        return pd.read_parquet(HANDOFF_KS)
    files = sorted(str(p) for d in ("infosys_deep", "infosys_full") for p in (EC.HANDOFF / d).glob("*_data.jsonl*"))
    with mp.Pool(min(6, len(files))) as pool:
        parts = pool.map(_handoff_file, files, chunksize=1)
    h = pd.DataFrame([r for p in parts for r in p], columns=["k_year", "k_tid", "k_code", "player_no", "v1", "v2",
                                                             "vmax", "first_in", "first_total", "points_missing",
                                                             "file"])
    for c in ("v1", "v2", "vmax"):
        h[c] = plaus(h[c])
    # the two folders overlap: keep one copy per match and player, preferring one that has a speed
    h = h.sort_values(["k_year", "k_tid", "k_code", "player_no", "v1"], na_position="last")
    h = h.drop_duplicates(["k_year", "k_tid", "k_code", "player_no"]).reset_index(drop=True)
    h.to_parquet(HANDOFF_KS, index=False)
    return h


def handoff(links: pd.DataFrame) -> pd.DataFrame:
    h = handoff_ks()
    h["source_key"] = h["k_year"] + "_" + h["k_tid"] + "_" + h["k_code"]
    lk = links[links["source"].eq("infosys") & links["match_id"].notna() & links["a1"].notna()][["key", "match_id", "a1"]]
    lk = lk.drop_duplicates("key")
    h = h.merge(lk.rename(columns={"key": "source_key"}), on="source_key", how="left")
    side = side_of(h["a1"], h["player_no"])
    return pd.DataFrame({"source": "handoff_ks", "basis": "keystat_atp", "source_key": h["source_key"],
                         "match_id": h["match_id"], "side": side, "spd1": h["v1"], "n1": h["first_in"],
                         "f1": h["first_in"], "spd2": h["v2"], "n2": h["first_total"] - h["first_in"],
                         "spd_max": h["vmax"], "ks_spd1": h["v1"], "ks_first_in": h["first_in"],
                         "ks_first_total": h["first_total"], "points_missing": h["points_missing"]})


def ausopen_mc(links: pd.DataFrame) -> pd.DataFrame:
    a = pd.read_parquet(EC.AO_STATS, columns=["record_key", "set", "stat", "team1_primary", "team1_secondary",
                                              "team2_primary", "team2_secondary"])
    a = a[a["set"].eq("All") & a["stat"].isin(["1st Serve Average", "2nd serve average", "Fastest serve",
                                                "1st serve in"])].drop_duplicates(["record_key", "stat"])
    rows = []
    for no in (1, 2):
        w = a.pivot_table(index="record_key", columns="stat", values=f"team{no}_primary", aggfunc="first")
        sec = a[a["stat"].eq("1st serve in")].set_index("record_key")[f"team{no}_secondary"]
        fs = sec.astype(str).str.extract(FIRST)
        w = w.assign(player_no=no, first_in=pd.to_numeric(fs[0], errors="coerce").reindex(w.index),
                     first_total=pd.to_numeric(fs[1], errors="coerce").reindex(w.index))
        rows.append(w.reset_index())
    w = pd.concat(rows, ignore_index=True)
    lk = links[links["source"].eq("ausopen") & links["match_id"].notna() & links["a1"].notna()][["key", "match_id", "a1"]]
    w = w.merge(lk.drop_duplicates("key").rename(columns={"key": "record_key"}), on="record_key", how="left")
    side = side_of(w["a1"], w["player_no"])
    return pd.DataFrame({"source": "ausopen_mc", "basis": "mc_rounded", "source_key": w["record_key"],
                         "match_id": w["match_id"], "side": side, "spd1": plaus(w.get("1st Serve Average")),
                         "n1": w["first_in"], "f1": w["first_in"], "spd2": plaus(w.get("2nd serve average")),
                         "n2": w["first_total"] - w["first_in"], "spd_max": plaus(w.get("Fastest serve")),
                         "ks_first_in": w["first_in"], "ks_first_total": w["first_total"]})


def main() -> None:
    EC.OUT.mkdir(parents=True, exist_ok=True)
    links = pd.read_parquet(EC.SHOT / "stage0_source_matches.parquet", columns=["source", "key", "match_id", "a1"])
    remap = EC.id_map()
    sp_tab = pd.read_parquet(EC.SPEEDS)
    parts = []
    for name in EC.POINT_SOURCES:
        EC.log(f"point table {name}")
        parts.append(point_source(name, links))
    EC.log("infosys_slams")
    parts.append(infosys_slams(sp_tab))
    EC.log("mantennisdata")
    parts.append(mantennisdata(sp_tab))
    EC.log("handoff key statistics (cached after the first run)")
    parts.append(handoff(links))
    EC.log("AO match centre")
    parts.append(ausopen_mc(links))
    rec = pd.concat([p.reindex(columns=EC_COLS) for p in parts], ignore_index=True)
    # point tables and the two non-acquisition links point at the pre-rebuild Stage 0: move the 42 re-keyed ids
    old = rec["source"].isin(EC.POINT_SOURCES + ["handoff_ks", "ausopen_mc"])
    rec.loc[old, "match_id"] = rec.loc[old, "match_id"].map(lambda x: remap.get(x, x))
    rec["linked"] = rec["match_id"].notna() & rec["side"].notna()
    rec["timed"] = rec["spd1"].notna()
    rec["timed_share"] = np.where(rec["basis"].eq("point_mean") & (rec["f1"] > 0), rec["n1"] / rec["f1"], np.nan)
    rec["gate_half"] = np.where(rec["basis"].eq("point_mean"), rec["timed_share"] >= 0.5, rec["timed"])
    rec.to_parquet(EC.RECORDS, index=False)
    EC.log(f"wrote {EC.RECORDS.name}: {len(rec):,} rows")
    print(rec.groupby(["source", "basis"]).agg(rows=("source", "size"), linked=("linked", "sum"),
                                                timed=("timed", "sum"), gate=("gate_half", "sum")).to_string())


EC_COLS = COLS

if __name__ == "__main__":
    main()

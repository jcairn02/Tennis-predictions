"""Design R1 (speed-data engineer), step 8: what the draft panel gives the windows. Presence and counts only; reads no
match result (the model frame is read without a_won and p_mkt).

Window rule (x_raw's, speed_build.window_feature): a player's history match h counts for target t when it is his own
earlier match (an earlier tournament date, or an earlier round of the same event) and obs_t - obs_h <= 14 (short) or
<= 364 (long) days.

Targets
    frame   the model frame (63,737 matches, 2013-2026): players and keys from the pre-rebuild Stage 0 (the frame's own),
            the clock day obs from timing.parquet (rebuilt; the 40 re-keyed women's 2026 ids through the id map)
    stage0  Stage 0's main-tour main draws 2015-2026 (rebuilt): to validate against the acquisition's scenario N2
History: the draft panel (engineer_panel0.parquet) without implausible values or fewer than 10 timed first serves in,
         optionally plus Flashscore's presence (--flashscore: both players timed; unoriented, presence only)

Run: ./python.sh src/eda/serve_speed_tabpfn/design/engineer_coverage.py [--flashscore]
Writes data/studies/serve_speed_tabpfn/design/engineer_coverage.json, engineer_coverage_frame.csv,
engineer_window_levels.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

PANEL0 = EC.OUT / "engineer_panel0.parquet"
SHORT, LONG = 14.0, 364.0
LGROUPS = ["slam_main", "slam_qual", "tour_main", "tour_qual", "ch_main", "ch_qual", "team", "itf"]
MAIN_TOUR = {"slam_main", "tour_main"}


def history(flashscore: bool) -> pd.DataFrame:
    p = pd.read_parquet(PANEL0)
    p = p[~p["implausible"] & (p["n1"] >= 10)]
    h = p[["tour", "player_id", "tournament_date", "tournament_id", "round_order", "obs", "lgroup", "source",
           "match_id"]].copy()
    if flashscore:
        from src.eda.serve_speed_sources import coverage as CV
        EC.log("Flashscore crawl (presence, both players)")
        fs = CV.flashscore_crawl()
        rows = EC.player_rows()
        add = rows[rows["match_id"].isin(fs)]
        have = set(h["match_id"] + "|" + h["player_id"].astype(str))
        add = add[~(add["match_id"] + "|" + add["player_id"].astype(str)).isin(have)]
        EC.log(f"  Flashscore adds {len(add)} player-matches beyond the panel")
        h = pd.concat([h, add[["tour", "player_id", "tournament_date", "tournament_id", "round_order", "obs",
                               "lgroup", "match_id"]].assign(source="flashscore")], ignore_index=True)
    h["tdate"] = h["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    return h


def frame_targets() -> pd.DataFrame:
    f = EC.model_frame()
    pre = EC.stage0(EC.S0_PRE, cols=["match_id", "level", "qualifying", "round_order", "tournament_id",
                                     "tournament_name", "tournament_date", "player_a_id", "player_b_id"])
    f = f.merge(pre.drop(columns=["tournament_date"]), on="match_id", how="left")
    remap = EC.id_map()
    f["nid"] = f["match_id"].map(lambda x: remap.get(x, x))
    tm = pd.read_parquet(EC.TIMING, columns=["match_id", "obs"]).rename(columns={"match_id": "nid"})
    f = f.merge(tm, on="nid", how="left")
    f["year"] = f["season"]
    return f


def stage0_targets() -> pd.DataFrame:
    m = EC.stage0(cols=["match_id", "tour", "year", "level", "qualifying", "round_order", "tournament_id",
                        "tournament_name", "tournament_date", "player_a_id", "player_b_id"])
    m = m[m["level"].isin(("GS",) + EC.TOUR_LEVELS) & ~m["qualifying"].astype(bool) & m["year"].between(2015, 2026)]
    tm = pd.read_parquet(EC.TIMING, columns=["match_id", "obs"])
    return m.merge(tm, on="match_id", how="left")


def presence(t: pd.DataFrame, h: pd.DataFrame) -> pd.DataFrame:
    """Per target side: has a 14-day / 364-day timed history; 14-day presence from main-tour main draws only; and the
    14-day window's matches by level group."""
    sides = pd.concat([t.assign(side="A", player_id=t["player_a_id"]), t.assign(side="B", player_id=t["player_b_id"])],
                      ignore_index=True)
    sides["tdate"] = sides["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    hk = h["tour"] + "|" + h["player_id"].astype(str)
    groups = {k: g for k, g in h.groupby(hk.to_numpy())}
    sk = (sides["tour"] + "|" + sides["player_id"].astype(str)).to_numpy()
    n = len(sides)
    out = {"n14": np.zeros(n), "n364": np.zeros(n), "n14_main": np.zeros(n), "n364_main": np.zeros(n)}
    lev = {g: np.zeros(n) for g in LGROUPS}
    td, tid, ro, ob = (sides["tdate"].to_numpy(), sides["tournament_id"].to_numpy(), sides["round_order"].to_numpy(),
                       sides["obs"].to_numpy(float))
    for i in range(n):
        g = groups.get(sk[i])
        if g is None:
            continue
        earlier = (g["tdate"].to_numpy() < td[i]) | ((g["tournament_id"].to_numpy() == tid[i])
                                                     & (g["round_order"].to_numpy() < ro[i]))
        age = ob[i] - g["obs"].to_numpy(float)
        w14 = earlier & (age <= SHORT)
        w364 = earlier & (age <= LONG)
        main = np.isin(g["lgroup"].to_numpy(), list(MAIN_TOUR))
        out["n14"][i], out["n364"][i] = w14.sum(), w364.sum()
        out["n14_main"][i], out["n364_main"][i] = (w14 & main).sum(), (w364 & main).sum()
        if w14.any():
            lg = g["lgroup"].to_numpy()[w14]
            for k in LGROUPS:
                lev[k][i] = (lg == k).sum()
    for k, v in out.items():
        sides[k] = v
    for k, v in lev.items():
        sides[f"lv_{k}"] = v
    return sides


def match_level(sides: pd.DataFrame) -> pd.DataFrame:
    a = sides[sides["side"].eq("A")].set_index("match_id")
    b = sides[sides["side"].eq("B")].set_index("match_id")
    m = a[["tour", "year", "level"]].copy()
    m["slam"] = m["level"].eq("GS")
    m["both14"] = (a["n14"] > 0) & (b["n14"] > 0)
    m["both364"] = (a["n364"] > 0) & (b["n364"] > 0)
    m["one14"] = (a["n14"] > 0) | (b["n14"] > 0)
    m["exactly_one14"] = (a["n14"] > 0) ^ (b["n14"] > 0)
    m["neither364"] = (a["n364"] == 0) & (b["n364"] == 0)
    m["both14_main_only"] = (a["n14_main"] > 0) & (b["n14_main"] > 0)
    m["both364_any_both14_not"] = m["both364"] & ~m["both14"]
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--flashscore", action="store_true")
    args = ap.parse_args()
    h = history(args.flashscore)
    res = {"reads_results": False, "history_rows": int(len(h)), "flashscore": args.flashscore}
    EC.log("frame targets")
    ft = frame_targets()
    fs = presence(ft, h)
    fm = match_level(fs)
    cov = (fm.groupby(["tour", "year", "slam"]).agg(frame=("both14", "size"), both14=("both14", "sum"),
                                                    both364=("both364", "sum"), one14=("one14", "sum"),
                                                    exactly_one14=("exactly_one14", "sum"),
                                                    neither364=("neither364", "sum"),
                                                    both14_main_only=("both14_main_only", "sum"))
           .reset_index())
    suffix = "_fs" if args.flashscore else ""
    cov.to_csv(EC.OUT / f"engineer_coverage_frame{suffix}.csv", index=False)
    res["frame_by_tour_window"] = (fm.assign(window=np.select([fm["year"] <= 2021, fm["year"] <= 2024],
                                                              ["2013-21", "2022-24"], "2025-26"))
                                   .groupby(["tour", "window", "slam"])
                                   .agg(frame=("both14", "size"), both14=("both14", "sum"), both364=("both364", "sum"),
                                        one14=("one14", "sum"), neither364=("neither364", "sum"),
                                        both14_main_only=("both14_main_only", "sum"))
                                   .reset_index().to_dict(orient="records"))
    # the 14-day windows' composition by level, men 2022-2026 frame sides
    men = fs[(fs["tour"] == "atp") & fs["year"].between(2022, 2026) & (fs["n14"] > 0)]
    comp = men.groupby("year")[[f"lv_{k}" for k in LGROUPS]].sum()
    comp["sides_with_14d"] = men.groupby("year").size()
    comp["sides_only_via_non_main"] = men[men["n14_main"] == 0].groupby("year").size()
    comp["sides_with_any_qual_in_14d"] = men[(men["lv_tour_qual"] + men["lv_slam_qual"] + men["lv_ch_qual"]) > 0] \
        .groupby("year").size()
    comp.reset_index().to_csv(EC.OUT / f"engineer_window_levels{suffix}.csv", index=False)
    res["men_14d_window_levels_2022_26"] = comp.reset_index().to_dict(orient="records")
    # what non-main levels add to men's frame matches with both14
    mm = fm[(fm["tour"] == "atp") & fm["year"].between(2022, 2026)]
    res["men_frame_2022_26_both14_all_levels"] = mm.groupby("year")["both14"].sum().astype(int).to_dict()
    res["men_frame_2022_26_both14_main_only"] = mm.groupby("year")["both14_main_only"].sum().astype(int).to_dict()
    # cumulative: main-tour main draws, + tour qualifying, + Slam qualifying, + Challengers, + team events / ITF
    steps = [("main", ["slam_main", "tour_main"]), ("+tour_qual", ["tour_qual"]), ("+slam_qual", ["slam_qual"]),
             ("+challenger", ["ch_main", "ch_qual"]), ("+team_itf", ["team", "itf"])]
    sm_ = fs[(fs["tour"] == "atp") & fs["year"].between(2022, 2026)].copy()
    used, inc = [], []
    for name, levs in steps:
        used += levs
        sm_["has"] = sm_[[f"lv_{k}" for k in used]].sum(axis=1) > 0
        a = sm_[sm_["side"].eq("A")].set_index("match_id")["has"]
        b = sm_[sm_["side"].eq("B")].set_index("match_id")["has"]
        yr = sm_[sm_["side"].eq("A")].set_index("match_id")["year"]
        both = (a & b).groupby(yr).sum()
        inc.append({"step": name, **{int(k): int(v) for k, v in both.items()}})
    res["men_both14_cumulative_by_level"] = inc
    if not args.flashscore:
        fs.drop(columns=["player_a_id", "player_b_id"], errors="ignore").to_parquet(EC.OUT / "engineer_frame_sides.parquet",
                                                                                    index=False)
    # validation on Stage 0's main-tour main draws (the acquisition's frame and rule)
    EC.log("Stage 0 main-tour main-draw targets (validation)")
    st = stage0_targets()
    ss = presence(st, h)
    sm = match_level(ss)
    val = sm.groupby(["tour", "year", "slam"]).agg(frame=("both14", "size"), both14=("both14", "sum")).reset_index()
    acq = pd.read_csv(EC.ROOT / "data" / "studies" / "serve_speed_acquisition" / "coverage_feature_by_year.csv")
    val = val.merge(acq[["tour", "year", "slam", "frame", "N2_slams"]].rename(columns={"frame": "acq_frame"}),
                    on=["tour", "year", "slam"], how="left")
    res["validation_vs_acquisition_N2"] = val.to_dict(orient="records")
    (EC.OUT / f"engineer_coverage{suffix}.json").write_text(json.dumps(res, indent=1, default=str) + "\n",
                                                           encoding="utf-8")
    EC.log("frame coverage:\n" + cov.to_string(index=False))
    EC.log("validation:\n" + val.to_string(index=False))
    EC.log("men's 14-day windows by level:\n" + comp.to_string())


if __name__ == "__main__":
    main()

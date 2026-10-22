"""Aggregate tables of the third-party readers (part "box", prefix tp_) for box/REPORT_third.md: coverage (Q1),
SofaScore's box against its own point recount (Q2), and Flashscore and the ATP-site scrape on the main tour before
2019 (Q3). Reads only the readers' own outputs (box/readers/tp_*.parquet), the study's Stage 0 snapshot and its link
files. Aggregates only (counts, shares, means): no per-match rows, no prices.

Writes (data/studies/source_reconciliation/box/):
    tp_coverage.csv                 Q1: Stage 0 matches each reader covers, by tour, level group and season
    tp_sofascore_q2_counts.csv      Q2: SofaScore's box (ALL and set sums) against its recount, per count
    tp_sofascore_q2_months.csv      Q2: by month: ALL = sum of sets, and each against the recount, per count
    tp_sofascore_q2_aces.csv        Q2: aces and double faults: the box against the recount's bounds
    tp_sofascore_q2_first_serves.csv Q2: first serves in against Stage 0, by level; the moved serves' win rate
    tp_sofascore_q2_bp.csv          Q2: break points by period: equal shares, impossible conversions
    tp_q3_pre2019.csv               Q3: men's main tour (Slams and tour main draws) 2010-2018: matches covered
    tp_q3_agreement.csv             Q3: per-count agreement with Stage 0 there, 2010-2012 and 2013-2018
    tp_q3_second_opinion.csv        Q3: where Flashscore or the scrape differs from Stage 0, does the other agree?
In every equality table mean_diff = the second-named source minus the first (for "X vs recount": X minus the recount;
for "ALL box vs set-sum box": ALL minus the set sums).
    tp_tables.json                  the headline numbers quoted in the report
Run: ./python.sh src/eda/source_reconciliation/tp_tables.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import tp_common as T  # noqa: E402

READERS = ["tp_sofascore_box", "tp_sofascore_setbox", "tp_sofascore_recount", "tp_tennislive_stats", "tp_atp_scraped",
           "tp_flashscore_stats", "tp_mcp_recount"]
RC = ["svpt", "sv_won", "sv_gms", "bp_faced", "bp_saved"]


def read(name: str) -> pd.DataFrame:
    return pd.read_parquet(T.READERS / f"{name}.parquet")


def eq_table(left: pd.DataFrame, right: pd.DataFrame, fields: list[str], by: list[str], label: str) -> pd.DataFrame:
    """Per field and group: rows where both have the count, equal, equal share, mean difference (right - left)."""
    rows = []
    for f in fields:
        a, b = left[f], right[f]
        both = a.notna() & b.notna()
        d = (b - a).where(both)
        g = pd.DataFrame({**{c: left[c] for c in by}, "both": both, "eq": (d == 0) & both, "d": d})
        g = g[g["both"]].groupby(by, dropna=False).agg(n=("both", "size"), equal=("eq", "sum"), mean_diff=("d", "mean"))
        g = g.reset_index()
        g.insert(len(by), "field", f)
        rows.append(g)
    out = pd.concat(rows, ignore_index=True)
    out["equal_share"] = (out["equal"] / out["n"]).round(4)
    out["mean_diff"] = out["mean_diff"].round(3)
    out.insert(0, "comparison", label)
    return out


def q1() -> tuple[pd.DataFrame, dict]:
    frames, head = [], {}
    for r in READERS:
        d = read(r)
        cv = T.coverage(d, r)
        frames.append(cv)
        head[r] = {"matches": int(d["match_id"].nunique()), "complete": int(d.loc[d["complete"], "match_id"].nunique()),
                   "by_tour": {t: int(n) for t, n in cv.groupby("tour")["covered"].sum().items()}}
    return pd.concat(frames, ignore_index=True), head


def q2() -> tuple[dict, dict]:
    b, s, r = read("tp_sofascore_box"), read("tp_sofascore_setbox"), read("tp_sofascore_recount")
    S = T.s0_frame()[["match_id", "tour", "year", "level_group"]]
    lk = C.links("sofascore", ["source_key", "date_local"]).set_index("source_key")
    keys = ["match_id", "player_id"]
    rc = r[r["complete"]]
    out, head = {}, {}
    # counts: ALL box vs recount, set-sum box vs recount, ALL vs set-sum
    jb = b.merge(rc[keys + RC + ["x_ace_listed", "x_ace_max", "x_df_listed", "x_df_max"]], on=keys, suffixes=("", "_r"))
    js = s.merge(rc[keys + RC], on=keys, suffixes=("", "_r"))
    jbs = b.merge(s[keys + C.FIELDS], on=keys, suffixes=("", "_s"))
    tabs = []
    for j, lab, suf in ((jb, "ALL box vs recount", "_r"), (js, "set-sum box vs recount", "_r")):
        j = j.merge(S, on="match_id", how="left")
        left = j[[f"{f}{suf}" for f in RC]].set_axis(RC, axis=1)
        for c in ("tour", "x_collection", "x_season"):
            left[c] = j[c]
        tabs.append(eq_table(left, j[RC], RC, ["tour", "x_collection", "x_season"], lab))
        head[lab] = {f: round(float(((j[f] == j[f"{f}{suf}"]) & j[f].notna())[j[f].notna() & j[f"{f}{suf}"].notna()]
                                    .mean()), 4) for f in RC}
    jbs = jbs.merge(S, on="match_id", how="left")
    left = jbs[[f"{f}_s" for f in C.FIELDS]].set_axis(C.FIELDS, axis=1)
    for c in ("tour", "x_collection", "x_season"):
        left[c] = jbs[c]
    tabs.append(eq_table(left, jbs[C.FIELDS], C.FIELDS, ["tour", "x_collection", "x_season"],
                         "ALL box vs set-sum box (right = ALL)"))
    out["counts"] = pd.concat(tabs, ignore_index=True)
    # months
    month = lambda d: pd.to_datetime(d["source_key"].map(lk["date_local"])).dt.to_period("M").astype(str)  # noqa: E731
    jb["month"], js["month"], jbs["month"] = month(jb), month(js), month(jbs)
    mrows = []
    for j, lab, pairs in ((jb, "ALL box vs recount", [(f, f"{f}_r") for f in RC]),
                          (js, "set-sum box vs recount", [(f, f"{f}_r") for f in RC]),
                          (jbs, "ALL box vs set-sum box", [(f, f"{f}_s") for f in C.FIELDS])):
        for f, g in pairs:
            ok = j[f].notna() & j[g].notna()
            t = j[ok].assign(eq=(j[f] == j[g])[ok]).groupby("month").agg(n=("eq", "size"), equal_share=("eq", "mean"))
            t = t.reset_index().assign(comparison=lab, field=f)
            mrows.append(t)
    out["months"] = pd.concat(mrows, ignore_index=True)[["comparison", "field", "month", "n", "equal_share"]]
    out["months"]["equal_share"] = out["months"]["equal_share"].round(4)
    # aces and double faults against the recount's bounds
    a_rows = []
    for f in ("ace", "df"):
        ok = jb[f].notna()
        x = jb[ok]
        lo, hi = x[f"x_{f}_listed"], x[f"x_{f}_max"]
        a_rows.append({"field": f, "rows": int(len(x)), "box_equals_listed": round(float((x[f] == lo).mean()), 4),
                       "box_within_bounds": round(float(((x[f] >= lo) & (x[f] <= hi)).mean()), 4),
                       "box_below_listed": round(float((x[f] < lo).mean()), 4),
                       "box_above_max": round(float((x[f] > hi).mean()), 4),
                       "mean_box_minus_listed": round(float((x[f] - lo).mean()), 3)})
        jsx = js[js[f].notna()].merge(rc[keys + [f"x_{f}_listed", f"x_{f}_max"]], on=keys, suffixes=("", "_rr"))
        lo2, hi2 = jsx[f"x_{f}_listed"], jsx[f"x_{f}_max"]
        a_rows.append({"field": f + " (set-sum box)", "rows": int(len(jsx)),
                       "box_equals_listed": round(float((jsx[f] == lo2).mean()), 4),
                       "box_within_bounds": round(float(((jsx[f] >= lo2) & (jsx[f] <= hi2)).mean()), 4),
                       "box_below_listed": round(float((jsx[f] < lo2).mean()), 4),
                       "box_above_max": round(float((jsx[f] > hi2).mean()), 4),
                       "mean_box_minus_listed": round(float((jsx[f] - lo2).mean()), 3)})
    out["aces"] = pd.DataFrame(a_rows)
    head["aces_and_double_faults"] = a_rows
    # first serves in against Stage 0, by level; the moved serves' win rate where serve points agree
    P = T.s0_players()
    f_rows = []
    for d, lab in ((b, "ALL box"), (s, "set-sum box")):
        j = d.merge(P, on=keys, suffixes=("", "_s0")).merge(S, on="match_id")
        j = j[j["svpt"].notna() & j["svpt_s0"].notna() & j["first_in"].notna() & j["first_in_s0"].notna()]
        for (tour, lg), g in j.groupby(["tour", "level_group"]):
            same = g[g["svpt"] == g["svpt_s0"]]
            moved = same[same["first_in"] != same["first_in_s0"]]
            dfi, dfw = moved["first_in"] - moved["first_in_s0"], moved["first_won"] - moved["first_won_s0"]
            f_rows.append({"box": lab, "tour": tour, "level_group": lg, "rows": int(len(g)),
                           "first_in_equal_share": round(float((g["first_in"] == g["first_in_s0"]).mean()), 4),
                           "first_in_mean_diff": round(float((g["first_in"] - g["first_in_s0"]).mean()), 3),
                           "rows_svpt_equal": int(len(same)), "rows_svpt_equal_first_in_differs": int(len(moved)),
                           "sum_first_in_diff": int(dfi.sum()), "sum_first_won_diff": int(dfw.sum()),
                           "moved_serves_win_rate": round(float(dfw.sum() / dfi.sum()), 3) if dfi.sum() else None,
                           "stage0_first_serve_win_rate": round(float(g["first_won_s0"].sum() / g["first_in_s0"].sum()), 3),
                           "stage0_second_serve_win_rate": round(float(g["second_won_s0"].sum() /
                                                                       (g["svpt_s0"] - g["first_in_s0"]).sum()), 3)})
        tot = j[(j["svpt"] == j["svpt_s0"]) & (j["first_in"] != j["first_in_s0"])]
        for tour, g in tot.groupby("tour"):
            head.setdefault("moved_first_serves", {})[f"{lab} {tour}"] = {
                "rows": int(len(g)), "sum_first_in_diff": int((g["first_in"] - g["first_in_s0"]).sum()),
                "win_rate_of_moved": round(float((g["first_won"] - g["first_won_s0"]).sum() /
                                                 (g["first_in"] - g["first_in_s0"]).sum()), 3)}
    out["first_serves"] = pd.DataFrame(f_rows)
    # break points by period
    def period(m):
        if "2024-12" <= m <= "2025-08":
            return "2024-12..2025-08"
        if "2025-09" <= m <= "2026-01":
            return "2025-09..2026-01"
        if "2026-02" <= m <= "2026-06":
            return "2026-02..2026-06"
        return "other"
    jb["period"] = jb["month"].map(period)
    js["period"] = js["month"].map(period)
    bp_rows = []
    for (per, tour), g in jb.merge(S[["match_id", "tour"]], on="match_id").groupby(["period", "tour"]):
        g = g[g["bp_faced"].notna()]
        conv = g["bp_faced"] - g["bp_saved"]
        broken = g["bp_faced_r"] - g["bp_saved_r"]               # the recount's breaks = games broken
        bp_rows.append({"box": "ALL", "period": per, "tour": tour, "rows": int(len(g)),
                        "bp_faced_equal_recount": round(float((g["bp_faced"] == g["bp_faced_r"]).mean()), 4),
                        "bp_saved_equal_recount": round(float((g["bp_saved"] == g["bp_saved_r"]).mean()), 4),
                        "box_faced_below_recount": round(float((g["bp_faced"] < g["bp_faced_r"]).mean()), 4),
                        "box_conversions_below_games_broken": round(float((conv < broken).mean()), 4),
                        "svpt_equal_recount": round(float((g["svpt"] == g["svpt_r"])[g["svpt"].notna()].mean()), 4)})
    for (per, tour), g in js.merge(S[["match_id", "tour"]], on="match_id").groupby(["period", "tour"]):
        g = g[g["bp_faced"].notna()]
        bp_rows.append({"box": "set-sum", "period": per, "tour": tour, "rows": int(len(g)),
                        "bp_faced_equal_recount": round(float((g["bp_faced"] == g["bp_faced_r"]).mean()), 4),
                        "bp_saved_equal_recount": round(float((g["bp_saved"] == g["bp_saved_r"]).mean()), 4),
                        "box_faced_below_recount": round(float((g["bp_faced"] < g["bp_faced_r"]).mean()), 4),
                        "box_conversions_below_games_broken": round(float(((g["bp_faced"] - g["bp_saved"]) <
                                                                           (g["bp_faced_r"] - g["bp_saved_r"])).mean()), 4),
                        "svpt_equal_recount": round(float((g["svpt"] == g["svpt_r"])[g["svpt"].notna()].mean()), 4)})
    out["bp"] = pd.DataFrame(bp_rows)
    head["bp"] = bp_rows
    return out, head


def q3() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    S = T.s0_frame()
    main = S[S["tour"].eq("atp") & S["level_group"].isin(["slam", "tour_main"]) & S["year"].between(2010, 2018)]
    P = T.s0_players()
    rows, so_rows, head = [], [], {}
    fs, ap = read("tp_flashscore_stats"), read("tp_atp_scraped")
    fs, ap = fs[fs["complete"]], ap[ap["complete"]]
    for year, g in main.groupby("year"):
        mids = set(g["match_id"])
        r = {"tour": "atp", "level": "slam + tour main draw", "year": int(year), "stage0_matches": len(mids),
             "stage0_with_box": int(g["has_box"].sum()),
             "flashscore_complete": int(fs["match_id"].isin(mids).groupby(fs["match_id"]).first().sum()),
             "atp_scrape_complete": int(ap["match_id"].isin(mids).groupby(ap["match_id"]).first().sum())}
        both = set(fs["match_id"]) & set(ap["match_id"]) & mids
        r["both"] = len(both)
        rows.append(r)
    cov = pd.DataFrame(rows)
    # per-count agreement with Stage 0 on 2013-2018 (and 2010-2012), each source
    agree = []
    for name, d in (("flashscore", fs), ("atp_scrape", ap)):
        j = d.merge(P, on=["match_id", "player_id"], suffixes=("", "_s0")).merge(
            main[["match_id", "year"]], on="match_id")
        for span, sub in (("2010-2012", j[j["year"] <= 2012]), ("2013-2018", j[j["year"] >= 2013])):
            for f in C.COUNTS:
                ok = sub[f].notna() & sub[f"{f}_s0"].notna()
                agree.append({"source": name, "years": span, "field": f, "player_rows": int(ok.sum()),
                              "equal_share": round(float((sub[f] == sub[f"{f}_s0"])[ok].mean()), 4) if ok.any() else None,
                              "mean_diff": round(float((sub[f] - sub[f"{f}_s0"])[ok].mean()), 3) if ok.any() else None})
    agree = pd.DataFrame(agree)
    # second opinion, 2013-2018: where one source differs from Stage 0, does the other side with it?
    j = fs.merge(ap[["match_id", "player_id"] + C.COUNTS], on=["match_id", "player_id"], suffixes=("_fs", "_ap"))
    j = j.merge(P[["match_id", "player_id"] + C.COUNTS], on=["match_id", "player_id"]).merge(
        main[["match_id", "year"]], on="match_id")
    j = j[j["year"] >= 2013]
    for f in C.COUNTS:
        ok = j[f"{f}_fs"].notna() & j[f"{f}_ap"].notna() & j[f].notna()
        x = j[ok]
        fs_eq, ap_eq, fa_eq = x[f"{f}_fs"] == x[f], x[f"{f}_ap"] == x[f], x[f"{f}_fs"] == x[f"{f}_ap"]
        so_rows.append({"field": f, "player_rows_all_three": int(len(x)), "all_equal": int((fs_eq & ap_eq).sum()),
                        "flashscore_differs_scrape_equals_stage0": int((~fs_eq & ap_eq).sum()),
                        "scrape_differs_flashscore_equals_stage0": int((fs_eq & ~ap_eq).sum()),
                        "both_differ_and_agree_with_each_other": int((~fs_eq & ~ap_eq & fa_eq).sum()),
                        "all_three_differ": int((~fs_eq & ~ap_eq & ~fa_eq).sum())})
    so = pd.DataFrame(so_rows)
    head["coverage_2013_2018"] = {
        "stage0_matches": int(cov.loc[cov["year"] >= 2013, "stage0_matches"].sum()),
        "flashscore_complete": int(cov.loc[cov["year"] >= 2013, "flashscore_complete"].sum()),
        "atp_scrape_complete": int(cov.loc[cov["year"] >= 2013, "atp_scrape_complete"].sum()),
        "both": int(cov.loc[cov["year"] >= 2013, "both"].sum())}
    return cov, agree, so, head


def main() -> int:
    head = {}
    cov, head["q1"] = q1()
    cov.to_csv(T.BOX / "tp_coverage.csv", index=False)
    q2t, head["q2"] = q2()
    q2t["counts"].to_csv(T.BOX / "tp_sofascore_q2_counts.csv", index=False)
    q2t["months"].to_csv(T.BOX / "tp_sofascore_q2_months.csv", index=False)
    q2t["aces"].to_csv(T.BOX / "tp_sofascore_q2_aces.csv", index=False)
    q2t["first_serves"].to_csv(T.BOX / "tp_sofascore_q2_first_serves.csv", index=False)
    q2t["bp"].to_csv(T.BOX / "tp_sofascore_q2_bp.csv", index=False)
    cov3, agree3, so3, head["q3"] = q3()
    cov3.to_csv(T.BOX / "tp_q3_pre2019.csv", index=False)
    agree3.to_csv(T.BOX / "tp_q3_agreement.csv", index=False)
    so3.to_csv(T.BOX / "tp_q3_second_opinion.csv", index=False)
    head["q3"]["agreement"] = T.records(agree3)
    head["q3"]["second_opinion"] = T.records(so3)
    C.write_json(T.BOX / "tp_tables.json", head)
    T.log("tables written")
    return 0


if __name__ == "__main__":
    sys.exit(main())

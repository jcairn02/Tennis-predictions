"""The WTA part's questions (Q1-Q5 of the brief), as aggregate tables from the readers' parquet files. Writes only
aggregates (counts, shares, means) and a few ids: box/wta_*.csv and box/wta_questions.json.

    wta_coverage.csv            Q1: Stage 0's women's matches 2019-2026 at the levels the API lists, by level group and
                                season: how many each reader links, and how many it gives complete
    wta_api_not_in_stage0.csv   Q1: singles the API lists (played) that link to no Stage 0 match, by tier, draw, year
    wta_recount_vs_box.csv      Q2: the event-log recount (complete matches) against the API's box, per count and
                                season: rows, exact share, within-one share, mean difference (recount minus box); also
                                the first-serve flag reading and the tiebreak-filled recount
    wta_three_way.csv           Q2-Q4: on rows where the complete recount, the box and Stage 0 all have a count: all
                                equal, or which one is the odd one out, per count and season
    wta_short_records.csv       Q3: per season, box against Stage 0 on serve points with the Slam boxes (all zeros in
                                2024-2025) read as counts and without them; and the tour boxes that differ from both
                                the recount and Stage 0
    wta_service_games.csv       Q4: which definition each count follows (games completed, + the game in progress at a
                                retirement, service games won), per source pair and season
    wta_event_disagreement.csv  Q5: per edition, the complete recount against the box, per count; editions where any
                                count agrees in under 95% of at least 10 rows
    wta_serve_number_missing.csv Q5: logs that record no serve numbers, by edition

Run (after the readers): ./python.sh src/eda/source_reconciliation/wta_questions.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import wta_common as WC  # noqa: E402

F = C.FIELDS
READER_NAMES = ["wta_api_box", "wta_api_slam_box", "wta_events_recount", "wta_events_tbfill_recount",
                "wta_pbp_recount"]


def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(WC.READERS / f"{name}.parquet")


def stage0_counts() -> tuple[pd.DataFrame, pd.DataFrame]:
    s0m, s0p = WC.stage0_women()
    s0p = s0p.copy()
    s0p["sv_won"] = s0p["first_won"] + s0p["second_won"]
    return s0m, s0p


def share(a, b):
    return round(float(a) / float(b), 4) if b else None


def coverage(s0m: pd.DataFrame, readers: dict) -> pd.DataFrame:
    base = s0m[s0m["level_group"].notna()]
    rows = []
    for name, f in readers.items():
        per = f.drop_duplicates("match_id")[["match_id", "complete"]]
        if name == "wta_events_tbfill_recount":
            per = f[f["x_tb_filled"]].drop_duplicates("match_id")[["match_id", "complete"]]
        j = base[["match_id", "level_group", "year"]].merge(per, on="match_id", how="left")
        j["linked"] = j["complete"].notna()
        j["complete"] = j["complete"].fillna(False).astype(bool)
        g = j.groupby(["level_group", "year"]).agg(s0_matches=("match_id", "size"), linked=("linked", "sum"),
                                                   complete=("complete", "sum")).reset_index()
        g.insert(0, "reader", name if name != "wta_events_tbfill_recount" else name + " (filled matches only)")
        rows.append(g)
    out = pd.concat(rows, ignore_index=True)
    out["group4"] = out["level_group"].map(WC.GROUP4)
    out["linked_share"] = (out["linked"] / out["s0_matches"]).round(4)
    out["complete_share"] = (out["complete"] / out["s0_matches"]).round(4)
    return out.rename(columns={"year": "season"})


def not_in_stage0(readers: dict) -> pd.DataFrame:
    lst = WC.listing()
    lst = lst[lst["draw"].isin(["main_singles", "qual_singles"]) & lst["MatchState"].eq("F")
              & ~lst["how"].eq("walkover")]
    linked = set(WC.C.links("wta_api", ["source_key"])["source_key"])
    lst = lst.assign(linked=lst["source_key"].isin(linked))
    box_keys = set(readers["wta_api_box"]["source_key"]) | set(readers["wta_api_slam_box"]["source_key"])
    g = lst.groupby(["tier", "draw", "year"]).agg(api_played_singles=("source_key", "size"),
                                                  linked_to_stage0=("linked", "sum")).reset_index()
    g["not_in_stage0"] = g["api_played_singles"] - g["linked_to_stage0"]
    return g


def three_way(rc: pd.DataFrame, box: pd.DataFrame, s0p: pd.DataFrame, by: str = "x_s0_year") -> pd.DataFrame:
    j = rc[rc["complete"]].merge(box[["match_id", "player_id"] + F], on=["match_id", "player_id"],
                                  suffixes=("", "_box"))
    j = j.merge(s0p[["match_id", "player_id"] + F].rename(columns={c: c + "_s0" for c in F}),
                on=["match_id", "player_id"])
    rows = []
    for c in F:
        r, b, s = j[c], j[c + "_box"], j[c + "_s0"]
        ok = r.notna() & b.notna() & s.notna()
        cat = np.select([(r == b) & (b == s), (r == s) & (r != b), (b == s) & (r != b), (r == b) & (r != s)],
                        ["all_equal", "box_odd", "recount_odd", "stage0_odd"], "all_differ")
        t = pd.DataFrame({"season": j[by], "cat": cat})[ok]
        ct = pd.crosstab(t["season"], t["cat"])
        for col in ("all_equal", "box_odd", "recount_odd", "stage0_odd", "all_differ"):
            if col not in ct:
                ct[col] = 0
        ct = ct.reset_index()
        ct.insert(0, "field", c)
        rows.append(ct)
    out = pd.concat(rows, ignore_index=True)
    out["rows"] = out[["all_equal", "box_odd", "recount_odd", "stage0_odd", "all_differ"]].sum(axis=1)
    out["all_equal_share"] = (out["all_equal"] / out["rows"]).round(4)
    return out[["field", "season", "rows", "all_equal", "all_equal_share", "box_odd", "recount_odd", "stage0_odd",
                "all_differ"]]


def recount_vs_box(rc: pd.DataFrame, fill: pd.DataFrame, box: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for label, f in (("events_recount", rc), ("events_tbfill_recount", fill)):
        j = f[f["complete"]].merge(box[["match_id", "player_id"] + F], on=["match_id", "player_id"],
                                   suffixes=("", "_box"))
        left = j[[c + "_box" for c in F] + ["x_s0_year"]].rename(columns={c + "_box": c for c in F})
        right = j[F]
        a = C.agreement(left, right, by=["x_s0_year"])
        a.insert(0, "recount", label)
        parts.append(a)
        if label == "events_recount":
            # the first-serve flag reading (the device's own flag), for comparison
            fl = j[["x_first_in_flag", "x_first_won_flag"]].rename(columns={"x_first_in_flag": "first_in",
                                                                              "x_first_won_flag": "first_won"})
            a2 = C.agreement(left, fl, by=["x_s0_year"], fields=["first_in", "first_won"])
            a2.insert(0, "recount", "events_recount, first-serve flag reading")
            parts.append(a2)
            # by whether the match had a correction
            left2 = left.assign(corr=np.where(j["x_corrections"] > 0, "with correction", "no correction"))
            a3 = C.agreement(left2[[c for c in F] + ["corr"]], right, by=["corr"])
            a3 = a3.rename(columns={"corr": "x_s0_year"})
            a3.insert(0, "recount", "events_recount, by correction")
            parts.append(a3)
    out = pd.concat(parts, ignore_index=True).rename(columns={"x_s0_year": "season_or_group"})
    out["mean_diff_recount_minus_box"] = out.pop("mean_diff").round(4)
    out = out.drop(columns=["mean_abs_diff"])
    for c in ("equal_share", "within1_share"):
        out[c] = out[c].round(4)
    return out


def short_records(box: pd.DataFrame, slam: pd.DataFrame, rc: pd.DataFrame, s0p: pd.DataFrame,
                  s0m: pd.DataFrame) -> pd.DataFrame:
    allb = pd.concat([box, slam], ignore_index=True)
    j = allb.merge(s0p[["match_id", "player_id"] + F], on=["match_id", "player_id"], suffixes=("", "_s0"))
    rows = []
    for yr, g in j.groupby("x_s0_year"):
        zeros = g["x_box_all_zero"]
        sv_as_counts = g["svpt"].where(~zeros, 0)
        ok = sv_as_counts.notna() & g["svpt_s0"].notna()
        d = (sv_as_counts - g["svpt_s0"])[ok]
        tour = g[g["x_tier"] != "slam"]
        okt = tour["svpt"].notna() & tour["svpt_s0"].notna()
        dt = (tour["svpt"] - tour["svpt_s0"])[okt]
        rows.append({"season": yr, "rows_with_box_and_stage0": int(ok.sum()),
                     "slam_box_rows_all_zero": int(zeros.sum()),
                     "svpt_equal_share_zero_boxes_as_counts": share((d == 0).sum(), len(d)),
                     "svpt_mean_diff_zero_boxes_as_counts": round(float(d.mean()), 2) if len(d) else None,
                     "svpt_mean_diff_where_differ_zero_boxes_as_counts": round(float(d[d != 0].mean()), 2)
                     if (d != 0).any() else None,
                     "tour_rows": int(okt.sum()), "tour_svpt_equal_share": share((dt == 0).sum(), len(dt)),
                     "tour_svpt_mean_diff_where_differ": round(float(dt[dt != 0].mean()), 2) if (dt != 0).any() else None})
    out = pd.DataFrame(rows)
    # tour boxes against the complete recount and Stage 0 when those two agree
    e = rc[rc["complete"]].merge(box[["match_id", "player_id", "svpt", "x_svpt_sets_agree", "x_sets_in_box"]],
                                 on=["match_id", "player_id"], suffixes=("", "_box"))
    e = e.merge(s0p[["match_id", "player_id", "svpt"]].rename(columns={"svpt": "svpt_s0"}), on=["match_id", "player_id"])
    odd = e[(e["svpt"] == e["svpt_s0"]) & e["svpt_box"].notna() & (e["svpt_box"] != e["svpt"])]
    t = odd.groupby("x_s0_year").agg(tour_box_differs_from_recount_and_stage0_rows=("match_id", "size"),
                                     of_them_matches=("match_id", "nunique"),
                                     box_short_rows=("svpt_box", lambda s: int((s < odd.loc[s.index, "svpt"]).sum())),
                                     box_match_row_not_sum_of_its_sets_rows=("x_svpt_sets_agree",
                                                                             lambda s: int((s == False).sum())),  # noqa: E712
                                     mean_box_minus_recount=("svpt_box", lambda s: round(float(
                                         (s - odd.loc[s.index, "svpt"]).mean()), 2))).reset_index()
    t = t.rename(columns={"x_s0_year": "season"})
    return out.merge(t, on="season", how="left").fillna({"tour_box_differs_from_recount_and_stage0_rows": 0})


def service_games(box, slam, rc, s0p, s0m) -> pd.DataFrame:
    rows = []
    # the tour: box, Stage 0 and the recount's two definitions
    e = rc[rc["complete"]].merge(box[["match_id", "player_id", "sv_gms"]], on=["match_id", "player_id"],
                                 suffixes=("", "_box"))
    e = e.merge(s0p[["match_id", "player_id", "sv_gms", "bp_faced", "bp_saved"]].rename(
        columns={"sv_gms": "sv_gms_s0", "bp_faced": "bp_faced_s0", "bp_saved": "bp_saved_s0"}),
        on=["match_id", "player_id"])
    e = e[e["sv_gms_box"].notna() & e["sv_gms_s0"].notna()]
    for yr, g in list(e.groupby("x_s0_year")) + [("all", e)]:
        ret = g["x_s0_status"].eq("retired")
        rows.append({"population": "tour (complete event-log recounts)", "season": yr, "rows": len(g),
                     "retirement_rows": int(ret.sum()),
                     "box_eq_stage0": share((g["sv_gms_box"] == g["sv_gms_s0"]).sum(), len(g)),
                     "box_eq_recount_completed_games": share((g["sv_gms_box"] == g["x_sv_gms_completed"]).sum(), len(g)),
                     "box_eq_recount_completed_plus_game_in_progress": share((g["sv_gms_box"] == g["sv_gms"]).sum(), len(g)),
                     "stage0_eq_recount_completed_games": share((g["sv_gms_s0"] == g["x_sv_gms_completed"]).sum(), len(g)),
                     "stage0_eq_recount_completed_plus_game_in_progress": share((g["sv_gms_s0"] == g["sv_gms"]).sum(), len(g)),
                     "retirement_rows_with_game_in_progress": int((ret & (g["x_sv_gms_unfinished"] > 0)).sum()),
                     "of_them_box_counts_it": int((ret & (g["x_sv_gms_unfinished"] > 0)
                                                   & (g["sv_gms_box"] == g["sv_gms"])).sum()),
                     "of_them_stage0_counts_it": int((ret & (g["x_sv_gms_unfinished"] > 0)
                                                      & (g["sv_gms_s0"] == g["sv_gms"])).sum()),
                     "box_eq_recount_plus_tiebreaks_served_first": share(
                         (g["sv_gms_box"] == g["sv_gms"] + g["x_tb_served_first"]).sum(), len(g))})
    # the Slams (no event logs): the box against Stage 0's games played and games won
    s = slam.merge(s0p[["match_id", "player_id", "sv_gms", "bp_faced", "bp_saved"]], on=["match_id", "player_id"],
                   suffixes=("", "_s0"))
    s = s[s["sv_gms"].notna() & s["sv_gms_s0"].notna()]
    for yr, g in s.groupby("x_s0_year"):
        holds = g["sv_gms_s0"] - (g["bp_faced_s0"] - g["bp_saved_s0"])
        rows.append({"population": "Slams (API box B9, no event log)", "season": yr, "rows": len(g),
                     "box_eq_stage0": share((g["sv_gms"] == g["sv_gms_s0"]).sum(), len(g)),
                     "slam_box_eq_stage0_service_games_won": share((g["sv_gms"] == holds).sum(), len(g)),
                     "slam_box_eq_its_own_service_games_won": share(
                         (g["sv_gms"] == g["sv_gms_s0"] - (g["bp_faced"] - g["bp_saved"])).sum(), len(g))})
    # data-continuity's 2026 reading: Stage 0 rows by source against every API box, Slams in or out
    allb = pd.concat([box, slam], ignore_index=True).merge(
        s0p[["match_id", "player_id", "sv_gms"]], on=["match_id", "player_id"], suffixes=("", "_s0")).merge(
        s0m[["match_id", "source"]], on="match_id")
    a = allb[(allb["x_s0_year"] == 2026) & allb["sv_gms"].notna() & allb["sv_gms_s0"].notna()]
    for src, g in a.groupby("source"):
        for lab, sub in (("every API box", g), ("tour boxes only", g[g["x_tier"] != "slam"]),
                         ("Slam boxes only", g[g["x_tier"] == "slam"])):
            rows.append({"population": f"2026, Stage 0 rows from {src}, against {lab}", "season": 2026,
                         "rows": len(sub), "box_eq_stage0": share((sub["sv_gms"] == sub["sv_gms_s0"]).sum(), len(sub))})
    return pd.DataFrame(rows)


def event_disagreement(rc: pd.DataFrame, box: pd.DataFrame) -> pd.DataFrame:
    j = rc[rc["complete"]].merge(box[["match_id", "player_id"] + F], on=["match_id", "player_id"],
                                 suffixes=("", "_box"))
    j["edition"] = j["source_key"].str.extract(r"wta:(\d+/\d+)/")[0]
    rows = []
    for ed, g in j.groupby("edition"):
        row = {"edition": ed, "tier": g["x_tier"].iloc[0], "rows": len(g),
               "serve_number_recorded_share": round(float(g["x_serve_number_recorded"].mean()), 4)}
        worst = 1.0
        for c in F:
            ok = g[c].notna() & g[c + "_box"].notna()
            sh = share((g.loc[ok, c] == g.loc[ok, c + "_box"]).sum(), ok.sum())
            row[f"{c}_equal"] = sh
            if sh is not None and ok.sum() >= 10:
                worst = min(worst, sh)
        row["worst_count_equal"] = worst
        rows.append(row)
    out = pd.DataFrame(rows)
    out["flag_under_95"] = (out["worst_count_equal"] < 0.95) & (out["rows"] >= 10)
    return out.sort_values(["flag_under_95", "worst_count_equal"], ascending=[False, True])


def serve_number_missing(rc: pd.DataFrame) -> pd.DataFrame:
    d = rc.drop_duplicates("source_key")
    d = d.assign(edition=d["source_key"].str.extract(r"wta:(\d+/\d+)/")[0])
    g = d.groupby(["edition", "x_tier"]).agg(logs=("source_key", "size"),
                                             no_serve_number=("x_serve_number_recorded", lambda s: int((~s).sum())))
    g = g.reset_index()
    return g[g["no_serve_number"] > 0].sort_values("no_serve_number", ascending=False)


def main() -> int:
    s0m, s0p = stage0_counts()
    readers = {n: load(n) for n in READER_NAMES}
    box, slam = readers["wta_api_box"], readers["wta_api_slam_box"]
    rc, fill = readers["wta_events_recount"], readers["wta_events_tbfill_recount"]
    cov = coverage(s0m, readers)
    cov.to_csv(WC.BOX / "wta_coverage.csv", index=False)
    nis = not_in_stage0(readers)
    nis.to_csv(WC.BOX / "wta_api_not_in_stage0.csv", index=False)
    rvb = recount_vs_box(rc, fill, box)
    rvb.to_csv(WC.BOX / "wta_recount_vs_box.csv", index=False)
    tw = three_way(rc, box, s0p)
    tw.to_csv(WC.BOX / "wta_three_way.csv", index=False)
    sr = short_records(box, slam, rc, s0p, s0m)
    sr.to_csv(WC.BOX / "wta_short_records.csv", index=False)
    sg = service_games(box, slam, rc, s0p, s0m)
    sg.to_csv(WC.BOX / "wta_service_games.csv", index=False)
    ed = event_disagreement(rc, box)
    ed.to_csv(WC.BOX / "wta_event_disagreement.csv", index=False)
    snm = serve_number_missing(rc)
    snm.to_csv(WC.BOX / "wta_serve_number_missing.csv", index=False)
    # headline numbers
    g4 = cov.groupby(["reader", "group4"])[["s0_matches", "linked", "complete"]].sum().reset_index()
    tw_all = tw.groupby("field")[["rows", "all_equal", "box_odd", "recount_odd", "stage0_odd", "all_differ"]].sum()
    tw_all["all_equal_share"] = (tw_all["all_equal"] / tw_all["rows"]).round(4)
    rvb_all = C.agreement(*(lambda j: (j[[c + "_box" for c in F]].rename(columns={c + "_box": c for c in F}), j[F]))(
        rc[rc["complete"]].merge(box[["match_id", "player_id"] + F], on=["match_id", "player_id"], suffixes=("", "_box"))))
    slam_fi = slam.merge(s0p[["match_id", "player_id", "svpt", "first_in"]], on=["match_id", "player_id"],
                         suffixes=("", "_s0"))
    slam_fi = slam_fi[slam_fi["first_in"].notna() & slam_fi["first_in_s0"].notna()]
    headline = {
        "q1_coverage_by_group4": json_records(g4),
        "q2_recount_vs_box_all_complete_rows": json_records(rvb_all[["field", "n", "equal", "equal_share",
                                                                      "within1_share", "mean_diff"]].round(4)),
        "q2_three_way_all_seasons": json_records(tw_all.reset_index()),
        "q3_short_records": json_records(sr),
        "q4_service_games": json_records(sg),
        "q5_editions_flagged": int(ed["flag_under_95"].sum()),
        "q5_editions_checked": int(len(ed)),
        "q5_logs_without_serve_numbers": int(snm["no_serve_number"].sum()),
        "q5_slam_2026_first_in_rate": {"box": round(100 * slam_fi["first_in"].sum() / slam_fi["svpt"].sum(), 2),
                                       "stage0": round(100 * slam_fi["first_in_s0"].sum() / slam_fi["svpt_s0"].sum(), 2),
                                       "rows": int(len(slam_fi))},
    }
    C.write_json(WC.BOX / "wta_questions.json", headline)
    print(g4.to_string())
    print(tw_all.to_string())
    print(sr.to_string())
    print(sg.to_string())
    print(ed.head(25).to_string())
    print(snm.head(20).to_string())
    return 0


def json_records(df: pd.DataFrame) -> list[dict]:
    import json
    return json.loads(df.to_json(orient="records"))


if __name__ == "__main__":
    sys.exit(main())

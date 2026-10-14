"""B2-skeptic: write the exact scope of every confirmed fix (read-only on the repo; writes only under
data/studies/input_data_audit/fixes/B2-skeptic/). Run after f7_*, f8_ages, f11_odds_scan, f12_rank_orientation, f14_speed.

Scope files (one row per operation):
    scope_F7.csv    Stage 0 player rows of the 13 new ids: match_id, side, player_id (new) -> established_id
    scope_F8.csv    the 12 garbage-age rows: match_id, side, player_id, age now, F8 (blank) and F8b (recomputed) values
    scope_F9.csv    the 182 ATP Challenger rows of 17 Aug 2020: match_id, player_id, age now, dob, recomputed age
    scope_F11.csv   Stage 1 rows whose average (and, where marked, maximum) is exchanged between the players
    scope_F12.csv   the Nottingham 2017 final: every price exchanged between the players
    scope_F13.csv   the Canada 2022 R64 row: average and maximum blanked (contested exclusion)
    scope_F14.csv   key-statistic records that stop being candidates (narrowed)
    scope_F15.csv   men's records >= 240 km/h that stop being candidates
Also f9_dob_support.csv (each F9 player's other 2020 rows against the birth date) and f17_second_serve.csv.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B2-skeptic"
S0 = ROOT / "data/studies/predictability_diagnostic"


def dobs() -> pd.Series:
    ap = pd.read_parquet(ROOT / "data/dump/players/sackmann_archive/atp/atp_players.parquet")
    wp = pd.read_parquet(ROOT / "data/dump/players/sackmann_archive/wta/wta_players.parquet")
    d = pd.concat([ap.assign(t="atp"), wp.assign(t="wta")])
    d["pid"] = d["t"] + ":" + d["player_id"].astype(str)
    s = d.set_index("pid")["dob"].astype(str)
    return pd.to_datetime(s.where(s.str.fullmatch(r"\d{8}")), format="%Y%m%d", errors="coerce")


def main() -> None:
    p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "side", "player_id", "player_name", "age"])
    m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "tournament_name", "tournament_date", "level",
                                                                "round", "source", "source_file", "source_row"])
    d = p.merge(m, on="match_id")
    d["tournament_date"] = pd.to_datetime(d["tournament_date"])
    dob = dobs()

    # F7
    pairs = pd.read_csv(ROOT / "data/studies/input_data_audit/frame_split_ids_oct07.csv")
    alias = dict(zip(pairs["new_id"], pairs["established_id"]))
    f7 = d[d["player_id"].isin(alias)].copy()
    f7["established_id"] = f7["player_id"].map(alias)
    f7 = f7[["match_id", "side", "player_id", "established_id", "player_name", "tournament_name", "tournament_date",
             "round", "source", "source_file", "source_row"]].rename(columns={"player_id": "player_id_new"})
    f7.sort_values(["established_id", "tournament_date", "match_id"]).to_csv(OUT / "scope_F7.csv", index=False)
    print("F7 rows:", len(f7), "| ids:", f7["player_id_new"].nunique())

    # F8 / F8b
    f8 = d[d["age"].gt(100)].copy()
    f8["established_id"] = f8["player_id"].map(alias)
    f8["dob"] = f8["established_id"].map(dob)
    f8["age_F8"] = np.nan
    f8["age_F8b"] = ((f8["tournament_date"] - f8["dob"]).dt.days / 365.25).round(3)
    f8["age_decoded_from_garbage"] = (f8["age"] // 100) + (f8["age"] % 100) / 1000
    f8["decode_equals_F8b"] = (f8["age_decoded_from_garbage"] - f8["age_F8b"]).abs() < 0.0005
    f8 = f8[["match_id", "side", "player_id", "established_id", "player_name", "tournament_name", "tournament_date", "round",
             "source_file", "source_row", "age", "dob", "age_F8", "age_F8b", "age_decoded_from_garbage", "decode_equals_F8b"]]
    f8.to_csv(OUT / "scope_F8.csv", index=False)
    print("F8 rows:", len(f8), "| decode == F8b on all:", bool(f8["decode_equals_F8b"].all()))

    # F9
    week = d[d["tournament_date"].eq("2020-08-17") & d["level"].eq("CH") & d["player_id"].str.startswith("atp:")].copy()
    week["dob"] = week["player_id"].map(dob)
    week["age_exact"] = (week["tournament_date"] - week["dob"]).dt.days / 365.25
    week["age_F9"] = np.floor(week["age_exact"] * 10 + 1e-9) / 10           # Sackmann's convention: truncated to 0.1
    week["shift_days"] = (week["age_exact"] - week["age"]) * 365.25
    # support: each player's other Sackmann rows of 2020 agree with the dob under the truncation convention
    other = d[d["player_id"].isin(week["player_id"]) & d["tournament_date"].dt.year.eq(2020)
              & d["tournament_date"].ne("2020-08-17") & d["source"].eq("sackmann") & d["age"].notna()].copy()
    other["dob"] = other["player_id"].map(dob)
    other["trunc"] = np.floor((other["tournament_date"] - other["dob"]).dt.days / 365.25 * 10 + 1e-9) / 10
    other["agrees"] = (other["trunc"] - other["age"]).abs() < 0.051
    sup = other.groupby("player_id").agg(other_rows=("match_id", "size"), agree_share=("agrees", "mean"))
    week = week.join(sup, on="player_id")
    week[["match_id", "side", "player_id", "player_name", "tournament_name", "tournament_date", "round", "source_file",
          "source_row", "age", "dob", "age_exact", "age_F9", "shift_days", "other_rows", "agree_share"]].to_csv(
        OUT / "scope_F9.csv", index=False)
    print("F9 rows:", len(week), "| dob known:", int(week["dob"].notna().sum()), "| shift days quantiles:",
          week["shift_days"].quantile([0, .5, 1]).round(1).to_dict(), "| players:", week["player_id"].nunique(),
          "| players with other 2020 rows:", int(sup.shape[0]), "| other rows agreeing with dob:",
          round(float(other["agrees"].mean()), 4), "of", len(other))
    other.to_csv(OUT / "f9_dob_support.csv", index=False)

    # F11 / F12 / F13 from the raw-book table
    x = pd.read_parquet(OUT / "f11_raw_books.parquet")
    o = pd.read_parquet(S0 / "stage1_odds.parquet")
    o = o.set_index("match_id")
    f11_ids = {"atp|2016-540|F|atp:104918|atp:105683": True, "atp|2013-891|SF|atp:104386|atp:105379": True,
               "wta|2025-822|F|wta:210722|wta:211817": False, "wta|2022-2030|R32|wta:201603|wta:216146": False}
    rows = []
    for mid, with_max in f11_ids.items():
        r = x[x["match_id"].eq(mid)].iloc[0]
        s = o.loc[mid]
        rows.append({"match_id": mid, "td_file": r.td_file, "td_row": int(r.td_row), "src_file": r.src_file,
                     "src_row": int(r.src_row), "td_winner": r.Winner, "td_loser": r.Loser,
                     "exchange": "avg+max" if with_max else "avg",
                     "AvgW": r.AvgW, "AvgL": r.AvgL, "MaxW": r.MaxW, "MaxL": r.MaxL, "B365W": r.B365W, "B365L": r.B365L,
                     "PSW": r.PSW, "PSL": r.PSL, "WRank": r.WRank, "LRank": r.LRank,
                     "stage1_avg_a_now": s.avg_a, "stage1_avg_b_now": s.avg_b, "stage1_max_a_now": s.max_a,
                     "stage1_max_b_now": s.max_b, "p_avg_a_now": s.p_avg_a,
                     "avg_a_new": s.avg_b, "avg_b_new": s.avg_a,
                     "max_a_new": s.max_b if with_max else s.max_a, "max_b_new": s.max_a if with_max else s.max_b,
                     "p_avg_a_new": 1 - s.p_avg_a, "p_books_median_for_a": None})
    f11 = pd.DataFrame(rows)
    # the books' view of A, for the record
    for i, r in f11.iterrows():
        b = x[x["match_id"].eq(r.match_id)].iloc[0]
        a_is_w = o.loc[r.match_id, "avg_a"] == b.AvgW
        f11.loc[i, "p_books_median_for_a"] = b.p_books_med if a_is_w else 1 - b.p_books_med
    f11.to_csv(OUT / "scope_F11.csv", index=False)
    print(f11[["match_id", "exchange", "p_avg_a_now", "p_avg_a_new", "p_books_median_for_a"]].to_string())

    mid = "wta|2017-1080|F|wta:202427|wta:202499"
    r = x[x["match_id"].eq(mid)].iloc[0]
    s = o.loc[mid]
    f12 = pd.DataFrame([{"match_id": mid, "td_file": r.td_file, "td_row": int(r.td_row), "src_file": r.src_file,
                         "src_row": int(r.src_row), "td_winner_as_named": r.Winner, "td_loser_as_named": r.Loser,
                         "WRank": r.WRank, "LRank": r.LRank, "link": s.link, "exchange": "every price: avg, ps, max, b365",
                         **{f"{c}_now": s[c] for c in ["avg_a", "avg_b", "ps_a", "ps_b", "max_a", "max_b", "b365_a",
                                                       "b365_b", "p_avg_a", "p_ps_a"]},
                         "avg_a_new": s.avg_b, "avg_b_new": s.avg_a, "ps_a_new": s.ps_b, "ps_b_new": s.ps_a,
                         "max_a_new": s.max_b, "max_b_new": s.max_a, "b365_a_new": s.b365_b, "b365_b_new": s.b365_a,
                         "p_avg_a_new": 1 - s.p_avg_a, "p_ps_a_new": 1 - s.p_ps_a}])
    f12.to_csv(OUT / "scope_F12.csv", index=False)
    print(f12.T.to_string())

    mid = "atp|2022-421|R64|atp:105138|atp:106218"
    r = x[x["match_id"].eq(mid)].iloc[0]
    s = o.loc[mid]
    f13 = pd.DataFrame([{"match_id": mid, "td_file": r.td_file, "td_row": int(r.td_row), "src_file": r.src_file,
                         "src_row": int(r.src_row), "operation": "blank avg_a, avg_b, max_a, max_b (p_avg_a missing)",
                         "AvgW": r.AvgW, "AvgL": r.AvgL, "MaxW": r.MaxW, "MaxL": r.MaxL, "B365W": r.B365W,
                         "B365L": r.B365L, "PSW": r.PSW, "PSL": r.PSL, "p_avg_a_now": s.p_avg_a, "p_ps_a": s.p_ps_a}])
    f13.to_csv(OUT / "scope_F13.csv", index=False)

    # F14 / F15 (narrowed)
    t = pd.read_csv(OUT / "f14_flagged.csv")
    rec = pd.read_parquet(ROOT / "data/studies/serve_speed_tabpfn/speed_records.parquet")
    pm = rec[rec["kind"].eq("point_mean") & rec["valid"]].groupby(["match_id", "side"])["y"].min()
    t["point_mean_same_match"] = [pm.get((a, b), np.nan) for a, b in zip(t["match_id"], t["side"])]
    t["y"] = t["y_raw"] - 0.5
    # the published mean itself is wrong (too high or too low), not only the max: >= 8 km/h from the player's own
    # +-365-day median (at least 3 other records), or >= 5 km/h from a valid point mean of the same player-match
    shown_by_norm = t["resid_vs_norm"].abs().ge(8) & t["norm_n"].ge(3)
    shown_by_pts = (t["y"] - t["point_mean_same_match"]).abs().ge(5)
    t["mean_shown_wrong"] = shown_by_norm | shown_by_pts
    # one decision per player-match: every flagged record of a player-match goes together (else the panel falls back
    # from one copy to the other)
    pmw = t.groupby(["match_id", "side"])["mean_shown_wrong"].transform("max")
    t["in_scope_F14"] = t["f14"] & pmw
    t.to_csv(OUT / "f14_flagged_with_decision.csv", index=False)
    keep = ["match_id", "side", "source", "source_key", "player_id", "year", "y_raw", "spd_max", "gap", "n", "player_norm",
            "norm_n", "resid_vs_norm", "point_mean_same_match", "chosen_now", "fallback_source", "fallback_y",
            "fallback_resid", "f15"]
    t[t["in_scope_F14"]][keep].to_csv(OUT / "scope_F14.csv", index=False)
    out14 = t[t["f14"] & ~t["in_scope_F14"]]
    print("F14 flagged:", int(t["f14"].sum()), "| in scope:", int(t["in_scope_F14"].sum()), "| chosen in scope:",
          int((t["in_scope_F14"] & t["chosen_now"]).sum()), "| left out:", len(out14))
    print(out14[["match_id", "side", "source", "y_raw", "spd_max", "player_norm", "norm_n", "resid_vs_norm",
                 "point_mean_same_match"]].round(1).to_string())
    t[t["f15"]][keep].to_csv(OUT / "scope_F15.csv", index=False)
    print("F15 records:", int(t["f15"].sum()), "| all in F14 scope:", bool(t.loc[t["f15"], "in_scope_F14"].all()))

    # F17: second-serve mean >= first: is the first-serve mean (the only value the panel uses) the wrong field?
    pan = pd.read_parquet(ROOT / "data/studies/serve_speed_tabpfn/speed_panel.parquet")
    u = pan[pan["use"]].copy()
    u["tdate"] = pd.to_datetime(u["tournament_date"])
    mix = u[u["spd2"].notna() & u["n2"].fillna(0).ge(5) & (u["spd2"] >= u["y"])].copy()
    by = {k: g for k, g in u.groupby("player_id")}
    res = []
    for r in mix.itertuples():
        g = by[r.player_id]
        g = g[(g["match_id"] != r.match_id) & ((g["tdate"] - r.tdate).abs() <= pd.Timedelta(days=365))]
        res.append(r.y - g["y"].median() if len(g) >= 5 else np.nan)
    mix["resid_first"] = res
    mix[["match_id", "side", "source", "year", "y", "spd2", "n2", "spd_max", "resid_first"]].to_csv(
        OUT / "f17_second_serve.csv", index=False)
    print("F17 second >= first (use rows):", len(mix), "| first-serve mean within 5 km/h of the player's norm:",
          int(mix["resid_first"].abs().le(5).sum()), "| below norm by > 8:", int(mix["resid_first"].lt(-8).sum()),
          "| no norm:", int(mix["resid_first"].isna().sum()))


if __name__ == "__main__":
    main()

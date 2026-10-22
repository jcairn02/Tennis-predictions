"""Readers wta_api_box and wta_api_slam_box: the WTA API's per-match box score on Stage 0's ids.

Source: batch B3 (every WTA 1000/500/250/125 and Finals edition of 2019-2026, every draw) and batch B9 (the Slams of
2024-2026), staged as data/dump/points/wta/stats/<year>.parquet, one row per set and setnum "0" for the whole match.
The Slam box scores are told apart by the match list's tier ("slam"), and written as their own reader, because
data-continuity section 3.2 found their first serves in 2-3 points higher than Sackmann's and the Slams' own feeds.

Mapping onto the contract (as data_continuity/sources.wta_api, checked there against Sackmann):
    ace aces · df dblflt · svpt totservplayed · first_in ptsplayed1stserv · first_won ptswon1stserv ·
    sv_won ptstotwonserv · second_won = sv_won - first_won · sv_gms servgamesplayed ·
    bp_faced = the OPPONENT's breakptsplayed, bp_saved = that minus the opponent's breakptsconv (the API records break
    points on the returner's side). x_bp_faced_alt / x_bp_saved_alt keep the other reading (the player's own columns).
complete = the listing marks the match played (MatchState F) and not a walkover, and the box has a setnum 0 row that
is not all zeros. Observed: every Slam box of 2024 and 2025 in B9 is a match row of zeros with no set rows; those counts
are blanked (NaN) and x_box_all_zero marks them.

Extra columns (x_): tier, draw, the listing's year, how it ended, the per-set rows of the same box (their number and,
per count, whether the sets sum to the match row), total points won (the box's own), the API's winner against Stage 0's,
the listing's score, Stage 0's level group and season.

Run: ./python.sh src/eda/source_reconciliation/wta_api_box.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import wta_common as WC  # noqa: E402
from src.eda.data_continuity import common as K  # noqa: E402

STAT_NUM = ["acesa", "acesb", "dblflta", "dblfltb", "ptswon1stserva", "ptswon1stservb", "ptsplayed1stserva",
            "ptsplayed1stservb", "ptstotwonserva", "ptstotwonservb", "totservplayeda", "totservplayedb",
            "breakptsconva", "breakptsconvb", "breakptsplayeda", "breakptsplayedb", "servgamesplayeda",
            "servgamesplayedb", "totptswona", "totptswonb", "scorea", "scoreb", "scoretb"]


def read_stats(years=WC.YEARS) -> pd.DataFrame:
    parts = []
    for y in years:
        s = K.read_parquet_dedup(WC.WTA / "stats" / f"{y}.parquet",
                                 ["tournament_id", "year", "match_id", "setnum"] + STAT_NUM)
        parts.append(s)
    s = pd.concat(parts, ignore_index=True)
    s["source_key"] = "wta:" + s["tournament_id"].astype(str) + "/" + s["year"].astype(str) + "/" + s["match_id"]
    for c in STAT_NUM:
        s[c] = K.num(s[c])
    s["setnum"] = pd.to_numeric(s["setnum"], errors="coerce")
    return s


def per_side(total: pd.DataFrame, sets: pd.DataFrame) -> pd.DataFrame:
    """One row per (match, API side) with the contract's counts, the alternative break-point reading, and the per-set
    rows' sums."""
    sums = sets.groupby("source_key")[STAT_NUM].sum(min_count=1)
    nsets = sets.groupby("source_key").size().rename("x_sets_in_box")
    rows = []
    for side, other in (("a", "b"), ("b", "a")):
        f = total
        d = pd.DataFrame({"source_key": f["source_key"], "api_side": side.upper()})
        d["ace"] = f[f"aces{side}"].to_numpy()
        d["df"] = f[f"dblflt{side}"].to_numpy()
        d["svpt"] = f[f"totservplayed{side}"].to_numpy()
        d["first_in"] = f[f"ptsplayed1stserv{side}"].to_numpy()
        d["first_won"] = f[f"ptswon1stserv{side}"].to_numpy()
        d["sv_won"] = f[f"ptstotwonserv{side}"].to_numpy()
        d["second_won"] = d["sv_won"] - d["first_won"]
        d["sv_gms"] = f[f"servgamesplayed{side}"].to_numpy()
        d["bp_faced"] = f[f"breakptsplayed{other}"].to_numpy()
        d["bp_saved"] = (f[f"breakptsplayed{other}"] - f[f"breakptsconv{other}"]).to_numpy()
        d["x_bp_faced_alt"] = f[f"breakptsplayed{side}"].to_numpy()
        d["x_bp_saved_alt"] = (f[f"breakptsplayed{side}"] - f[f"breakptsconv{side}"]).to_numpy()
        d["x_tot_pts_won"] = f[f"totptswon{side}"].to_numpy()
        # per-set rows of the same box: their sums, per count, against the match row
        sm = sums.reindex(f["source_key"])
        d["x_svpt_sets_sum"] = sm[f"totservplayed{side}"].to_numpy()
        d["x_sv_won_sets_sum"] = sm[f"ptstotwonserv{side}"].to_numpy()
        d["x_first_in_sets_sum"] = sm[f"ptsplayed1stserv{side}"].to_numpy()
        d["x_sv_gms_sets_sum"] = sm[f"servgamesplayed{side}"].to_numpy()
        d["x_ace_sets_sum"] = sm[f"aces{side}"].to_numpy()
        d["x_df_sets_sum"] = sm[f"dblflt{side}"].to_numpy()
        d["x_sets_in_box"] = nsets.reindex(f["source_key"]).to_numpy()
        rows.append(d)
    return pd.concat(rows, ignore_index=True)


def main() -> int:
    lst = WC.listing()
    s0m, s0p = WC.stage0_women()
    st = read_stats()
    n_rows = len(st)
    total = st[st["setnum"] == 0].drop_duplicates("source_key")
    sets = st[st["setnum"] > 0].drop_duplicates(["source_key", "setnum"])
    info_read = {"stats_rows": int(n_rows), "matches_with_box": int(total["source_key"].nunique()),
                 "by_year": total.groupby("year").size().to_dict()}
    lst_s = lst[lst["draw"].isin(["main_singles", "qual_singles"])]
    info_read["singles_with_box"] = int(total["source_key"].isin(set(lst_s["source_key"])).sum())
    lk, info_link = WC.link(lst_s, s0m, s0p)
    box = per_side(total, sets)
    pl = WC.players_of(lk, s0p)
    out = pl.merge(box, on=["source_key", "api_side"], how="left", indicator=True)
    no_box = out.loc[out["_merge"] == "left_only", "source_key"].nunique()
    out = out[out["_merge"] == "both"].drop(columns="_merge")
    meta = lk[["source_key", "tier", "draw", "year", "how", "MatchState", "ScoreString", "x_winner_agrees",
               "x_ids_agree", "x_orient_one_name", "link_method", "level_group", "s0_year", "map_level", "status"]]
    out = out.merge(meta, on="source_key", how="left")
    out["complete"] = out["MatchState"].eq("F") & out["how"].isin(["completed", "retired"])
    out = out.rename(columns={"tier": "x_tier", "draw": "x_draw", "year": "x_api_year", "how": "x_how",
                              "ScoreString": "x_api_score", "level_group": "x_level_group", "s0_year": "x_s0_year",
                              "map_level": "x_map_level", "status": "x_s0_status", "api_side": "x_api_side",
                              "s0_side": "x_s0_side", "won": "x_s0_won"})
    out = out.drop(columns=["MatchState"])
    # a box whose match row is all zeros for a played match is no box (the Slams of 2024-2025 in B9, observed): its
    # counts are blanked and it is not complete; the flag is kept per match (both sides zero)
    zero_side = out[C.FIELDS].fillna(0).eq(0).all(axis=1)
    out["x_box_all_zero"] = zero_side.groupby(out["source_key"]).transform("all")
    out.loc[out["x_box_all_zero"], C.FIELDS] = np.nan
    out.loc[out["x_box_all_zero"], ["x_bp_faced_alt", "x_bp_saved_alt", "x_tot_pts_won"]] = np.nan
    out["complete"] = out["complete"] & ~out["x_box_all_zero"]
    for c in ("x_svpt_sets_sum", "x_sv_won_sets_sum", "x_first_in_sets_sum", "x_sv_gms_sets_sum"):
        base = c.replace("x_", "").replace("_sets_sum", "")
        out[f"x_{base}_sets_agree"] = (out[c] == out[base]).where(out[c].notna() & out[base].notna())
    slam = out["x_tier"].eq("slam")
    results = {}
    for reader, part in (("wta_api_box", out[~slam]), ("wta_api_slam_box", out[slam])):
        frame = WC.finish_reader(part.drop(columns=[]), reader, "box")
        keys = set(frame["source_key"])
        eq_all = WC.equality_with_stage0(frame, s0p)
        eq_year = WC.equality_with_stage0(frame, s0p, by=["x_s0_year"])
        summary = {
            "source": "WTA API box score (stats endpoint, setnum 0); batches B3 (tour, WTA 125, Finals, every draw) "
                      "and B9 (Slams 2024-2026); data/dump/points/wta/stats/<year>.parquet",
            "split": "tier == 'slam' -> wta_api_slam_box; every other tier -> wta_api_box",
            "records_read": {**info_read, "this_reader_matches_linked": len(keys)},
            "link": {**info_link, "note": "link and orientation are computed over every singles listing row; this "
                                          "reader keeps its own tier"},
            "dropped": {"linked_but_no_box_row (both readers)": int(no_box)},
            "complete": {"rows": int(frame["complete"].sum()), "of": int(len(frame))},
            "by_level_group": frame.groupby("x_level_group")["match_id"].nunique().to_dict(),
            "by_s0_year": frame.groupby("x_s0_year")["match_id"].nunique().to_dict(),
            "box_all_zero_rows (counts blanked, not complete)": int(frame["x_box_all_zero"].sum()),
            "box_all_zero_by_tournament_year": frame[frame["x_box_all_zero"]].assign(
                t=frame["source_key"].str.extract(r"wta:(\d+)/(\d+)/").agg("/".join, axis=1))
                .groupby("t")["match_id"].nunique().to_dict(),
            "winner_disagrees_after_orienting_matches": int(frame.loc[frame["x_winner_agrees"] == False,  # noqa: E712
                                                                      "match_id"].nunique()),
            "sanity_equality_with_stage0_all_rows": WC.agreement_records(eq_all),
            "sanity_equality_with_stage0_by_year": WC.agreement_records(eq_year),
            "hand_checks": "see wta_handcheck.json",
        }
        WC.write_reader(frame, reader, summary)
        results[reader] = len(frame)
    print(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())

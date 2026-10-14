"""R1-rederive (round 2): my numbers against the lead's proposal, read only now that mine exist.

Compares (data/studies/rg_first_serve_recount/followup/):
  proposed_overrides.csv   matches and the eighteen values, by feed key and Stage 0 match id; the lookup key
  whole_box_rows.csv       every player row: class, raw_*, off_*, mb_*, ks_*, cv_*, mcp_*, service games
  proposed_exchanges.csv   the four exchanges (source file and row, guards)
  exchange_rows.csv        the exchange evidence
against my my_overrides.csv, matches.csv, sides.csv, rgx.csv.

Writes compare_overrides.csv (every value that differs, if any), compare_rows.csv (per player row and column, the
differences) and compare.json; prints the tallies.
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/compare.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
VALS = [f"{s}_{c}" for s in "wl" for c in ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved",
                                             "bpFaced")]


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.strip().replace({"": np.nan, "nan": np.nan}), errors="coerce")


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.max_rows", 300)
    res: dict = {}
    lead = pd.read_csv(LEAD / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    mine = pd.read_csv(HERE / "my_overrides.csv", dtype=str, keep_default_na=False)
    mine = mine[mine["group"].isin(["W22", "W26"])].copy()
    mine["feed_key"] = "rolandgarros:" + mine["feed_key"].str.replace(r"^RG(\d{4})\|", r"\1/", regex=True)
    res["overrides"] = {"lead": int(len(lead)), "mine": int(len(mine))}
    lk, mk = set(lead["feed_key"]), set(mine["feed_key"])
    res["overrides"]["same_feed_keys"] = int(len(lk & mk))
    res["overrides"]["lead_only"] = sorted(lk - mk)
    res["overrides"]["mine_only"] = sorted(mk - lk)
    j = lead.merge(mine, on="feed_key", suffixes=("_lead", "_mine"))
    res["overrides"]["same_stage0_match_id"] = int((j["stage0_match_id_lead"] == j["stage0_match_id_mine"]).sum())
    for c in ("source", "tour", "tid", "round", "winner_key", "loser_key"):
        res["overrides"][f"same_{c}"] = int((j[f"{c}_lead"] == j[f"{c}_mine"]).sum())
    diffs = []
    for c in VALS:
        a, b = num(j[f"{c}_lead"]), num(j[f"{c}_mine"])
        bad = ~((a == b) | (a.isna() & b.isna()))
        for i in np.flatnonzero(bad.to_numpy()):
            r = j.iloc[i]
            diffs.append({"feed_key": r["feed_key"], "stage0_match_id": r["stage0_match_id_lead"], "column": c,
                          "lead": r[f"{c}_lead"], "mine": r[f"{c}_mine"], "my_sv_gms_from": r["sv_gms_from"],
                          "winner": r["winner_name"], "loser": r["loser_name"], "row_score": r["tml_score"]})
    dd = pd.DataFrame(diffs)
    dd.to_csv(HERE / "compare_overrides.csv", index=False)
    res["overrides"]["values_compared"] = int(len(j) * len(VALS))
    res["overrides"]["values_differing"] = int(len(dd))
    res["overrides"]["matches_with_a_difference"] = int(dd["feed_key"].nunique()) if len(dd) else 0
    res["overrides"]["differences_by_column"] = dd["column"].value_counts().to_dict() if len(dd) else {}
    print(json.dumps(res["overrides"], indent=1))
    if len(dd):
        print(dd.to_string())

    # ---------------- whole_box_rows: classes and every source value, per player row
    wb = pd.read_csv(LEAD / "whole_box_rows.csv", low_memory=False)
    sd = pd.read_csv(HERE / "sides.csv", low_memory=False)
    mm = pd.read_csv(HERE / "matches.csv", low_memory=False)
    sd = sd.merge(mm[["rid", "cls"]], on="rid")
    sd = sd[sd["year"].ge(2022)]
    sd["match_id"] = sd["s0_match_id"]
    x = wb.merge(sd, left_on=["match_id", "raw_side"], right_on=["match_id", "side"], how="outer",
                 suffixes=("_lead", "_mine"), indicator=True)
    res["rows"] = {"lead": int(len(wb)), "mine": int(len(sd)), "joined": int((x["_merge"] == "both").sum()),
                   "lead_only": int((x["_merge"] == "left_only").sum()),
                   "mine_only": int((x["_merge"] == "right_only").sum())}
    b = x[x["_merge"] == "both"].copy()
    cmap = {"no_link": "identity"}
    b["cls_lead_m"] = b["cls_lead"].replace(cmap)
    res["rows"]["class_equal"] = int((b["cls_lead_m"] == b["cls_mine"]).sum())
    res["rows"]["class_crosstab_where_different"] = pd.crosstab(b.loc[b["cls_lead_m"] != b["cls_mine"], "cls_lead"],
                                                                b.loc[b["cls_lead_m"] != b["cls_mine"], "cls_mine"]
                                                                ).to_dict() if (b["cls_lead_m"] != b["cls_mine"]).any() else {}
    pairs = [("raw_ace", "raw_ace"), ("raw_df", "raw_df"), ("raw_svpt", "raw_svpt"), ("raw_first_in", "raw_first_in"),
             ("raw_first_won", "raw_first_won"), ("raw_second_won", "raw_second_won"), ("raw_sv_gms", "raw_sv_gms"),
             ("raw_bp_saved", "raw_bp_saved"), ("raw_bp_faced", "raw_bp_faced")] + \
        [(f"off_{k}", f"off_{k}") for k in ("ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_saved",
                                             "bp_faced", "sv_gms")] + \
        [(f"mb_{k}", f"mb_{k}") for k in ("svpt", "first_in", "first_won", "second_won", "ace", "df")] + \
        [("mb_sv_gms_regular", "mb_sv_gms_reg_done")] + \
        [(f"ks_{k}", f"ks_{k}") for k in ("svpt", "first_in", "first_won", "second_won", "ace", "df")] + \
        [(f"cv_{k}", f"cv_{k}") for k in ("svpt", "first_in", "first_won", "second_won", "ace", "df")] + \
        [(f"mcp_{k}", f"mcp_{k}") for k in ("svpt", "first_in", "first_won", "second_won", "ace", "df")]
    col_diff = {}
    rows_diff = []
    for lc, mc in pairs:
        lv = num(b[f"{lc}_lead"] if f"{lc}_lead" in b else b[lc])
        mv = num(b[f"{mc}_mine"] if f"{mc}_mine" in b else b[mc])
        bad = ~((lv == mv) | (lv.isna() & mv.isna()))
        col_diff[lc] = {"differ": int(bad.sum()), "lead_blank_mine_not": int((lv.isna() & mv.notna()).sum()),
                        "mine_blank_lead_not": int((mv.isna() & lv.notna()).sum())}
        for i in np.flatnonzero(bad.to_numpy()):
            r = b.iloc[i]
            rows_diff.append({"match_id": r["match_id"], "side": r["raw_side"], "name": r["player_name"],
                              "year": r["year_lead"], "code": r["rg_code"], "column": lc, "lead": lv.iloc[i],
                              "mine": mv.iloc[i], "cls_lead": r["cls_lead"], "cls_mine": r["cls_mine"]})
    rd = pd.DataFrame(rows_diff)
    rd.to_csv(HERE / "compare_rows.csv", index=False)
    res["rows"]["column_differences"] = {k: v for k, v in col_diff.items() if v["differ"]}
    print(json.dumps(res["rows"], indent=1, default=str))
    # the service-games source: the lead's sv_gms_from against mine, on proposed rows
    pr = b[b["cls_lead"].eq("proposed")]
    res["rows"]["sv_from_crosstab_proposed"] = pd.crosstab(pr["sv_gms_from"].fillna("none"), pr["sv_from"]).to_dict()
    print("service games source (lead rows x mine columns):\n", pd.crosstab(pr["sv_gms_from"].fillna("none"),
                                                                          pr["sv_from"]).to_string())
    # where the lead's off_sv_gms differs from mine, show the evidence
    sv = pr[~((num(pr["off_sv_gms_lead"]) == num(pr["off_sv_gms_mine"])) |
              (num(pr["off_sv_gms_lead"]).isna() & num(pr["off_sv_gms_mine"]).isna()))]
    print("proposed rows whose service games differ (lead vs mine):")
    print(sv[["match_id", "raw_side", "player_name", "score", "sv_gms_from", "sv_from", "raw_sv_gms_lead",
              "off_sv_gms_lead", "off_sv_gms_mine", "mb_sv_gms_regular", "mb_sv_gms_reg_done", "der_sv",
              "mb_svpt_lead", "off_svpt_lead"]].to_string())

    # ---------------- exchanges
    pe = pd.read_csv(LEAD / "proposed_exchanges.csv", dtype=str, keep_default_na=False)
    rgx = pd.read_csv(HERE / "rgx.csv", dtype=str, keep_default_na=False)
    ke = set(zip(pe["source_file"], pe["source_row"]))
    km = set(zip(rgx["source_file"], rgx["source_row"]))
    res["exchanges"] = {"lead": len(ke), "mine": len(km), "same": len(ke & km)}
    er = pd.read_csv(LEAD / "exchange_rows.csv")
    ok = 0
    for r in er.itertuples():
        mr = rgx[(rgx["code"] == r.rg_code)].iloc[0]
        s = r.raw_side
        same = all(float(getattr(r, f"off_{k}")) == float(mr[f"rg_{s}_{k}"]) and
                   float(getattr(r, f"raw_{k}")) == float(mr[f"raw_{s}_{k}"])
                   for k in ("ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"))
        same &= float(r.off_sv_gms) == float(mr[f"der_{s}_sv_gms"]) and float(r.raw_sv_gms) == float(mr[f"raw_{s}_sv_gms"])
        ok += same
    res["exchanges"]["exchange_rows_equal_to_mine"] = f"{ok} of {len(er)}"
    print(json.dumps(res["exchanges"]))
    (HERE / "compare.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()

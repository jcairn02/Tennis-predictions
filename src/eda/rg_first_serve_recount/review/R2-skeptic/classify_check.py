"""R2-skeptic: my own classes from my own raw parse (sides.parquet), then a side-by-side check of the lead's proposal:
links, sides, classes, and every proposed value against the raw records.

Writes in data/studies/rg_first_serve_recount/review/R2-skeptic/:
    my_sides.parquet         sides.parquet + consistency flags, classes, second-channel status
    value_check.csv          every proposed side: the lead's values, the raw official record's, MatchBeats/pbp, match
    value_check_summary.json counts of agreement and every disagreement
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R2-skeptic/classify_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"
STUDY = ROOT / "data" / "studies" / "rg_first_serve_recount"
SPLIT = ["first_in", "first_won", "second_won"]
REST = ["svpt", "ace", "df", "bp_faced", "bp_saved"]


def official(s: pd.DataFrame) -> pd.DataFrame:
    rg = s["event"].eq("RG")
    s["off_svpt"] = np.where(rg, s["api_svpt"], s["og_svpt"])
    s["off_first_in"] = np.where(rg, s["api_first_in"], s["og_first_in"])
    s["off_first_won"] = np.where(rg, s["api_first_won"], s["og_first_won"])
    s["off_second_won"] = np.where(rg, s["api_second_won"], s["og_second_won"])
    s["off_ace"] = np.where(rg, s["api_ace"], s["og_ace"])
    s["off_df"] = np.where(rg, s["api_df"], s["og_df"])
    s["off_bp_faced"] = np.where(rg, s["api_opp_bp_opps"], s["og_opp_bp_opps"])
    s["off_bp_saved"] = np.where(rg, s["api_opp_bp_opps"] - s["api_opp_bp_won"],
                                 s["og_opp_bp_opps"] - s["og_opp_bp_won"])
    for c in ["off_svpt", "off_first_in", "off_first_won", "off_second_won", "off_ace", "off_df", "off_bp_faced",
              "off_bp_saved"]:
        s[c] = pd.to_numeric(s[c], errors="coerce")
    api_ok = (s["api_first_won_den"].eq(s["api_first_in"])
              & s["api_second_won_den"].eq(s["api_svpt"] - s["api_first_in"])
              & s["api_ret_den"].eq(s["api_opp_svpt"])
              & s["api_total_won"].eq(s["api_first_won"] + s["api_second_won"] + s["api_ret_won"]))
    og_ok = (s["og_status"].eq("OFFICIAL") & s["og_spw"].eq(s["og_first_won"] + s["og_second_won"])
             & s["og_second_att"].eq(s["og_svpt"] - s["og_first_in"]))
    s["off_ok_side"] = np.where(rg, api_ok, og_ok) & s["off_svpt"].notna()
    key = s["source_file"] + "#" + s["source_row"].astype(str)
    s["off_ok"] = s.groupby(key)["off_ok_side"].transform("all")
    # extra internal checks of mine: the set statistics sum to the match's (RG); per-set sums (OG)
    s["set_sum_ok"] = np.where(rg, s["api_set_first_in"].eq(s["api_first_in"]) & s["api_set_svpt"].eq(s["api_svpt"])
                               & s["api_set_first_won"].eq(s["api_first_won"])
                               & s["api_set_second_won"].eq(s["api_second_won"]),
                               s["ogset_first_in"].eq(s["og_first_in"]) & s["ogset_svpt"].eq(s["og_svpt"])
                               & s["ogset_first_won"].eq(s["og_first_won"])
                               & s["ogset_second_won"].eq(s["og_second_won"]))
    return s


def classify(s: pd.DataFrame) -> pd.DataFrame:
    s["raw_first_in"], s["raw_first_won"], s["raw_second_won"] = s["raw_1stIn"], s["raw_1stWon"], s["raw_2ndWon"]
    s["raw_bp_faced"], s["raw_bp_saved"] = s["raw_bpFaced"], s["raw_bpSaved"]
    frame = s["raw_svpt"].eq(s["off_svpt"]) & (s["raw_first_won"] + s["raw_second_won"]).eq(
        s["off_first_won"] + s["off_second_won"])
    rest_eq = np.all([s[f"raw_{c}"].eq(s[f"off_{c}"]) for c in REST], axis=0) & frame
    split_eq = np.all([s[f"raw_{c}"].eq(s[f"off_{c}"]) for c in SPLIT], axis=0)
    has = s["off_ok"] & s["raw_svpt"].notna()
    s["my_cls"] = np.select([~has, rest_eq & split_eq, split_eq, rest_eq, frame],
                            ["no_record", "equal", "other", "split", "split_other"], "points")
    s["d_first_in"] = s["raw_first_in"] - s["off_first_in"]
    s["d_first_won"] = s["raw_first_won"] - s["off_first_won"]
    # second record: MatchBeats (RG) / the play-by-play (OG)
    rg = s["event"].eq("RG")
    for c in ["svpt", "first_in", "first_won", "second_won", "ace", "df"]:
        s[f"sec_{c}"] = np.where(rg, s.get(f"mb_{c}"), s.get(f"ogp_{c}"))
        s[f"sec_{c}"] = pd.to_numeric(s[f"sec_{c}"], errors="coerce")
    held = s["sec_svpt"].notna()
    complete = held & s["sec_svpt"].eq(s["off_svpt"])
    same = complete & np.all([s[f"sec_{c}"].eq(s[f"off_{c}"]) for c in SPLIT], axis=0)
    s["my_second"] = np.select([~held, ~complete, same], ["absent", "incomplete", "agrees"], "contradicts")
    return s


def main() -> int:
    s = pd.read_parquet(OUT / "sides.parquet")
    s = classify(official(s))
    s.to_parquet(OUT / "my_sides.parquet", index=False)

    # ---------------------------------------------------------------- the lead's proposal against mine
    pr = pd.read_csv(STUDY / "proposed_rows.csv")
    pc = pd.read_csv(STUDY / "proposed_corrections.csv")
    pr = pr[pr["raw_side"].isin(["w", "l"])]
    k = ["source_file", "source_row", "side"]
    pr = pr.rename(columns={"raw_side": "side"})
    m = s.merge(pr[k + ["cls", "proposal_class", "proposed", "rg_code", "unit", "second_channel", "off_first_in",
                        "off_first_won", "off_second_won", "event"]].rename(
        columns={"off_first_in": "lead_off_first_in", "off_first_won": "lead_off_first_won",
                 "off_second_won": "lead_off_second_won", "unit": "lead_unit", "event": "lead_event"}),
        on=k, how="outer", indicator=True)
    scope = m["lead_event"].notna()
    summary = {"merge": m.loc[scope, "_merge"].value_counts().to_dict()}
    mm = m[scope & m["_merge"].eq("both")].copy()
    # links: same RG code / unit
    rgm = mm["event"].eq("RG")
    summary["rg_code_differs"] = mm[rgm & mm["code"].ne(mm["rg_code"]) & mm["rg_code"].notna()][
        k + ["code", "rg_code"]].to_dict("records")
    summary["og_unit_differs"] = mm[~rgm & mm["unit"].ne(mm["lead_unit"]) & mm["lead_unit"].notna()][
        k + ["unit", "lead_unit"]].to_dict("records")
    summary["class_crosstab"] = pd.crosstab(mm["cls"].fillna("NA"), mm["my_cls"]).to_dict()
    # every proposed side's values from the corrections table
    rows = []
    for r in pc.itertuples(index=False):
        for side in ("w", "l"):
            fi = getattr(r, f"{side}_1stIn")
            if pd.isna(fi):
                continue
            rows.append({"fix": r.fix, "source_file": r.source_file, "source_row": r.source_row, "side": side,
                         "p_first_in": fi, "p_first_won": getattr(r, f"{side}_1stWon"),
                         "p_second_won": getattr(r, f"{side}_2ndWon"), "p_svpt": getattr(r, f"{side}_svpt"),
                         "p_ace": getattr(r, f"{side}_ace"), "p_df": getattr(r, f"{side}_df"),
                         "g_tourney_id": r.tourney_id, "g_round": r.round, "g_winner": r.winner_name,
                         "g_loser": r.loser_name})
    p = pd.DataFrame(rows)
    v = p.merge(s, on=k, how="left")
    v["val_eq_official"] = (v["p_first_in"].eq(v["off_first_in"]) & v["p_first_won"].eq(v["off_first_won"])
                            & v["p_second_won"].eq(v["off_second_won"]))
    v["val_eq_second"] = (v["p_first_in"].eq(v["sec_first_in"]) & v["p_first_won"].eq(v["sec_first_won"])
                          & v["p_second_won"].eq(v["sec_second_won"]))
    v["guard_eq_raw"] = (v["p_svpt"].eq(v["raw_svpt"]) & (v["p_ace"].isna() | v["p_ace"].eq(v["raw_ace"]))
                         & (v["p_df"].isna() | v["p_df"].eq(v["raw_df"])))
    v["names_eq_raw"] = v["g_winner"].eq(v["raw_winner_name"]) & v["g_loser"].eq(v["raw_loser_name"])
    v["spw_kept"] = (v["p_first_won"] + v["p_second_won"]).eq(v["raw_first_won"] + v["raw_second_won"])
    v.to_csv(OUT / "value_check.csv", index=False)
    summary["proposed_sides"] = int(len(v))
    summary["proposed_sides_by_fix"] = v["fix"].value_counts().to_dict()
    summary["values_equal_my_official_parse"] = int(v["val_eq_official"].sum())
    summary["values_equal_my_second_record"] = int(v["val_eq_second"].sum())
    summary["second_record_status_of_proposed"] = v["my_second"].value_counts().to_dict()
    summary["guards_equal_raw"] = int(v["guard_eq_raw"].sum())
    summary["serve_points_won_kept"] = int(v["spw_kept"].sum())
    summary["my_class_of_proposed"] = v.groupby("fix")["my_cls"].value_counts().unstack(fill_value=0).to_dict("index")
    summary["value_mismatches"] = v[~v["val_eq_official"]][k + ["p_first_in", "p_first_won", "p_second_won",
                                                               "off_first_in", "off_first_won",
                                                               "off_second_won"]].to_dict("records")
    # what my rules would propose that the lead does not, and vice versa
    in_scope = s[(s["event"].eq("RG") & s["year"].between(2022, 2025)) | s["event"].eq("OG")]
    mine = in_scope[in_scope["my_cls"].isin(["split", "split_other"]) & ~in_scope["my_second"].eq("contradicts")]
    mk = set(zip(mine["source_file"], mine["source_row"], mine["side"]))
    lk = set(zip(v["source_file"], v["source_row"], v["side"]))
    summary["mine_not_lead"] = sorted(mk - lk)
    summary["lead_not_mine"] = sorted(lk - mk)
    summary["my_classes_in_scope"] = in_scope.groupby(["event"])["my_cls"].value_counts().unstack(fill_value=0) \
        .to_dict("index")
    ctrl = s[s["event"].eq("RG") & s["year"].between(2019, 2021)]
    summary["control_classes"] = ctrl["my_cls"].value_counts().to_dict()
    summary["control_not_equal"] = ctrl[~ctrl["my_cls"].eq("equal")][
        ["year", "tour", "draw", "round", "code", "side", "player", "my_cls", "off_ok"]].to_dict("records")
    summary["set_sum_ok_of_proposed"] = v["set_sum_ok"].value_counts(dropna=False).to_dict()
    (OUT / "value_check_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n",
                                                   encoding="utf-8")
    short = {kk: (vv if not isinstance(vv, list) else f"{len(vv)} items") for kk, vv in summary.items()}
    print(json.dumps(short, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

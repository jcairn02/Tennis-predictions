"""R1-rederive: compare my own values and scope with the lead's proposal (read only after mine were built).

Reads data/studies/rg_first_serve_recount/proposed_corrections.csv and proposed_rows.csv, and my scope.csv,
scope_all.csv and sides.csv. Writes compare_sides.csv (every side in either set, with both values) and prints every
difference: sides in one set only, values, fix ids, and per player row the classes, Sackmann's and the official counts.
Run: ./python.sh src/eda/rg_first_serve_recount/review/R1-rederive/compare_proposal.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R1-rederive"
STUDY = ROOT / "data" / "studies" / "rg_first_serve_recount"


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.max_colwidth", 60)
    prop = pd.read_csv(STUDY / "proposed_corrections.csv", keep_default_na=False, na_values=[""])
    rows = []
    for r in prop.itertuples():
        for side in ("w", "l"):
            fi = getattr(r, f"{side}_1stIn")
            if pd.notna(fi):
                rows.append({"source_file": r.source_file, "source_row": int(r.source_row), "side": side,
                             "p_fix": r.fix, "p_first_in": fi, "p_first_won": getattr(r, f"{side}_1stWon"),
                             "p_second_won": getattr(r, f"{side}_2ndWon"), "p_svpt": getattr(r, f"{side}_svpt"),
                             "p_ace": getattr(r, f"{side}_ace"), "p_df": getattr(r, f"{side}_df")})
    p = pd.DataFrame(rows)
    mine = pd.read_csv(HERE / "scope.csv")
    print("proposal: match rows", len(prop), "sides", len(p), "| mine: match rows",
          mine.drop_duplicates(["source_file", "source_row"]).shape[0], "sides", len(mine))
    j = p.merge(mine, on=["source_file", "source_row", "side"], how="outer", indicator=True)
    print(j["_merge"].value_counts().to_dict())
    allx = pd.read_csv(HERE / "scope_all.csv", keep_default_na=False, na_values=[""])
    info = allx.set_index(["source_file", "source_row", "side"])[["event", "year", "key", "name", "side_class",
                                                                   "m_state", "k_state", "T1", "T2", "T3", "T4", "T5"]]
    j = j.join(info, on=["source_file", "source_row", "side"])
    only_p = j[j["_merge"].eq("left_only")]
    only_m = j[j["_merge"].eq("right_only")]
    print("\nsides in the proposal only:")
    print(only_p[["event", "year", "key", "side", "name", "p_fix", "side_class", "m_state", "k_state", "T4", "T5",
                  "p_first_in", "p_first_won", "p_second_won"]].to_string())
    print("\nsides in my scope only:")
    print(only_m[["event", "year", "key", "side", "name", "fix", "side_class", "m_state", "first_in", "first_won",
                  "second_won"]].to_string())
    both = j[j["_merge"].eq("both")]
    vdiff = both[(both["p_first_in"] != both["first_in"]) | (both["p_first_won"] != both["first_won"]) |
                 (both["p_second_won"] != both["second_won"])]
    print("\nsides in both with different values:", len(vdiff))
    print(vdiff[["event", "year", "key", "side", "name", "p_first_in", "first_in", "p_first_won", "first_won",
                 "p_second_won", "second_won"]].to_string())
    fdiff = both[both["p_fix"] != both["fix"]]
    print("sides in both with a different fix id:", len(fdiff))
    print(fdiff[["event", "year", "key", "side", "name", "p_fix", "fix", "side_class"]].to_string())
    j.drop(columns="_merge").to_csv(HERE / "compare_sides.csv", index=False)

    # ---- the per-player-row table: classes and counts against my sides table
    pr = pd.read_csv(STUDY / "proposed_rows.csv", keep_default_na=False, na_values=[""])
    pr["side"] = pr["raw_side"]
    d = pd.read_csv(HERE / "sides.csv", keep_default_na=False, na_values=[""])
    d = d[(d["event"].eq("RG") & d["year"].between(2019, 2025)) | d["event"].eq("OG")]
    k = pr.merge(d, on=["source_file", "source_row", "side"], how="outer", indicator=True, suffixes=("_p", ""))
    print("\nproposed_rows vs my sides:", k["_merge"].value_counts().to_dict())
    print(k[k["_merge"].ne("both")][["event_p", "year_p", "source_file", "source_row", "side", "player_name", "name",
                                       "cls_p", "cls"]].head(30).to_string())
    kb = k[k["_merge"].eq("both")]
    cmp = {"raw_svpt": "s_svpt", "raw_ace": "s_ace", "raw_df": "s_df", "raw_first_in": "s_first_in",
           "raw_first_won": "s_first_won", "raw_second_won": "s_second_won", "raw_bp_faced": "s_bp_faced",
           "raw_bp_saved": "s_bp_saved", "off_svpt": "o_svpt", "off_ace": "o_ace", "off_df": "o_df",
           "off_first_in": "o_first_in", "off_first_won": "o_first_won", "off_second_won": "o_second_won",
           "off_bp_faced": "o_bp_faced", "off_bp_saved": "o_bp_saved", "mb_svpt": "m_svpt",
           "mb_first_in": "m_first_in", "mb_first_won": "m_first_won", "mb_second_won": "m_second_won"}
    for a, b in cmp.items():
        x, y = pd.to_numeric(kb[a], errors="coerce"), pd.to_numeric(kb[b], errors="coerce")
        bad = ~((x == y) | (x.isna() & y.isna()))
        if bad.any():
            print(f"  {a} vs my {b}: {int(bad.sum())} differ")
            print(kb.loc[bad, ["event", "year", "key", "side", "name", a, b]].head(12).to_string())
    # classes
    my = np.where(kb["cls"].isin(["split", "split_other"]), kb["cls"], kb["cls"])
    ct = pd.crosstab(kb["cls_p"], pd.Series(my, index=kb.index, name="mine"))
    print("\nclass (lead) x class (mine):")
    print(ct)
    sg = kb[kb["cls"].isin(["split", "split_other"])]
    print("sign agreement on split sides:", int((sg["sign_p"].astype(str) == sg["sign"].astype(str)).sum()), "of",
          len(sg))
    print(sg[sg["sign_p"].astype(str) != sg["sign"].astype(str)][["key", "side", "name", "sign_p", "sign"]].head())
    print("\nlead's proposed flag x my confirmed:")
    conf = set(zip(mine["source_file"], mine["source_row"], mine["side"]))
    kb = kb.assign(mine_conf=[(f, r, s) in conf for f, r, s in zip(kb["source_file"], kb["source_row"], kb["side"])])
    print(pd.crosstab(kb["proposed"], kb["mine_conf"]))
    print(kb.groupby(["proposal_class", "second_channel"], dropna=False).size().to_string())


if __name__ == "__main__":
    main()

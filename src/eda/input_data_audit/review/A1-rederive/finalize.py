"""Reviewer A1-rederive: write the confirmed scope files and the extensions found along the way (outside the candidates'
scopes, listed for a later round, never part of this vote's scope).

Scope files (data/studies/input_data_audit/fixes/A1-rederive/):
  F1_scope.csv   player rows: svpt := svpt + df
  f2_scope.csv   player rows of the confirmed matches (written by f2_verdict.py): exchange all nine counts between the two players
  F2_verdicts_all88.csv
  F3a_scope.csv  player rows: blank the box
  F3b_scope.csv  player rows: replace from the WTA API (counts given) or blank
  f4_scope.csv   player rows of the copy rows decided within the candidate's pairs: blank the box
Extensions: ext_F1_doha.csv, ext_F2_api_exchanges_outside_88.csv, ext_F4_other_pairs.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

O = R.OUT
m, p = R.stage0()

# ---------------- F1
f1 = pd.read_csv(O / "f1_scope_rows.csv")
f1 = f1[f1["s0_has_box"].eq(True)]
F1 = f1[["match_id", "player_id", "player_name", "_source_file", "_row", "raw_side", "tourney_name", "tourney_date",
         "round", "raw_svpt", "raw_df", "new_svpt"]].rename(columns={"raw_svpt": "svpt_now", "raw_df": "df", "new_svpt": "svpt_fixed"})
F1.to_csv(O / "F1_scope.csv", index=False)
print("F1:", len(F1), "player rows,", F1["match_id"].nunique(), "matches; df = 0 (no-op):", int(F1["df"].eq(0).sum()))

# Doha 2015 SF Safarova-Suarez Navarro and F Azarenka-Safarova: exclusive per MCP (extension, not in scope)
mcp = pd.read_csv(O / "f1_mcp_pairs.csv", parse_dates=["tdate"])
d = mcp[mcp["tourney_name"].eq("Doha") & mcp["tdate"].dt.year.eq(2015) & mcp["round"].isin(["SF", "F"])]
d.to_csv(O / "ext_F1_doha.csv", index=False)

# ---------------- F2
v = pd.read_csv(O / "f2_verdicts.csv")
v.to_csv(O / "F2_verdicts_all88.csv", index=False)
F2 = pd.read_csv(O / "f2_scope.csv")   # written by f2_verdict.py; the F2 scope file itself
print("F2:", F2["match_id"].nunique(), "matches,", len(F2), "player rows")
ag = pd.read_csv(O / "wta_api_agree_2019_2020_2021_2022_2023_2024_2025_2026_matches.csv")
ex = ag[ag["cls"].eq("exchanged")].copy()
key = m.assign(k=m["source_file"] + "#" + m["source_row"].astype(str)).set_index("k")["match_id"]
ex["match_id"] = (ex["_source_file"] + "#" + ex["_row"].astype(str)).map(key)
ex["in_candidate_88"] = ex["match_id"].isin(v["match_id"])
ex = ex[~ex["in_candidate_88"]]
ex[["match_id", "_source_file", "_row", "tourney_name", "tdate", "round", "winner_name", "loser_name", "score"]].to_csv(
    O / "ext_F2_api_exchanges_outside_88.csv", index=False)
print("F2 extension: WTA API-verified exchanges outside the 88:", len(ex))

# ---------------- F3
f3 = pd.read_csv(O / "f3_scope.csv")
F3a = f3[["match_id", "player_id", "player_name", "_source_file", "_row", "raw_side", "round", "score", "copied_from_2021",
          "s0_has_box"]]
F3a.to_csv(O / "F3a_scope.csv", index=False)
F3b = f3[["match_id", "player_id", "player_name", "_source_file", "_row", "raw_side", "round", "score", "copied_from_2021",
          "s0_has_box", "f3b_action", "api_wmid"] + [f"api_{b}" for b in R.BOX]]
F3b.to_csv(O / "F3b_scope.csv", index=False)
print("F3:", f3["match_id"].nunique(), "matches,", len(f3), "player rows; F3b actions:", f3["f3b_action"].value_counts().to_dict())

# ---------------- F4
f4 = pd.read_csv(O / "f4_copies_all.csv")
F4 = f4[f4["in_candidate_pairs"]].copy()
ap = pd.read_csv(O / "f4_audit_pairs.csv")
F4.to_csv(O / "f4_scope.csv", index=False)
print("F4:", F4["_row"].nunique(), "copy rows (", F4["match_id"].nunique(), "Stage 0 matches),", len(F4), "player rows;",
      "with a Stage 0 box:", F4.loc[F4["s0_has_box"].eq(True), "match_id"].nunique())
print("   audit pairs:", ap["my_verdict"].value_counts().to_dict())
f4x = f4[~f4["in_candidate_pairs"]]
pairs = pd.read_csv(O / "f4_pairs.csv")
both_bad = pairs[pairs["reason"].str.contains("implausible for every row", na=False)]
pd.concat([f4x.assign(note="copy decided by record, same score so not in the audit's list"),
           both_bad.assign(note="box implausible for both rows (fits neither score)")], ignore_index=True).to_csv(
    O / "ext_F4_other_pairs.csv", index=False)

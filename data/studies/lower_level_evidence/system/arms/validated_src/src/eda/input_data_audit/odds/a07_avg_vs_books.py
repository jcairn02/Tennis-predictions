"""Task 3/4: is the average-odds pair reversed or garbled relative to the individual bookmakers on the same raw row?

The average and the maximum both come from OddsPortal, so a reversal in that feed moves both; the referees here are
the individual books tennis-data prints beside them (B365, PS, and EX, LB, SJ while they exist). A frame row is
    reversed  when the average's favourite is the other player for every referee and the referees agree with each
              other (spread <= 0.15) and sit more than 0.20 from the average,
    garbled   when the average sits more than 0.15 from the referees' median without being reversed.
Also: links made by round alone (no identical set scores) whose tennis-data event differs from Stage 0's.

Outputs (out/): a07_avg_vs_books.csv (flagged frame rows), a07_avg_vs_books.json, a07_round_alone.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from _common import OUTD, num

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 60)
D = pd.read_parquet(OUTD / "a03_joined.parquet")
td30 = pd.read_parquet(OUTD / "a05_td30.parquet")
raw = td30.set_index(["td_file", "td_row"])
R = raw.reindex(pd.MultiIndex.from_arrays([D["td_file"].astype(str), D["td_row"].astype("int64")]))
a_is_w = np.where(D["link"].eq("winner_swapped"), ~D["a_won"].astype(bool), D["a_won"].astype(bool))


def p_a(book: str) -> np.ndarray:
    if f"{book}W" not in R.columns:
        return np.full(len(D), np.nan)
    w, l_ = num(pd.Series(R[f"{book}W"].to_numpy())), num(pd.Series(R[f"{book}L"].to_numpy()))
    pw = ((1 / w) / (1 / w + 1 / l_)).to_numpy()
    return np.where(a_is_w, pw, 1 - pw)


refs = ["B365", "PS", "EX", "LB", "SJ"]
P = pd.DataFrame({b: p_a(b) for b in refs + ["Max", "Avg"]}, index=D.index)
assert np.allclose(P["Avg"], D["p_mkt"], equal_nan=True), "Avg from the raw rows must equal p_mkt"
ref = P[refs]
n_ref = ref.notna().sum(axis=1)
med = ref.median(axis=1)
spread = ref.max(axis=1) - ref.min(axis=1)
opp_all = ((ref.sub(0.5).mul(D["p_mkt"] - 0.5, axis=0) < 0) | ref.isna()).all(axis=1) & (n_ref >= 1)
far = (ref.sub(D["p_mkt"], axis=0).abs() > 0.20) | ref.isna()
reversed_ = opp_all & far.all(axis=1) & (spread.fillna(0) <= 0.15)
dev = (D["p_mkt"] - med).abs()
garbled = ~reversed_ & (n_ref >= 1) & (dev > 0.15)
D["p_ref_median"] = med
D["n_ref"] = n_ref
D["ref_spread"] = spread
D["dev_from_refs"] = dev
D["max_agrees_with_avg"] = (P["Max"] - D["p_mkt"]).abs() < (P["Max"] - med).abs()
D["flag"] = np.select([reversed_, garbled], ["reversed", "garbled"], "")
fl = D[D["flag"] != ""].copy()
for b in refs + ["Max"]:
    fl[f"p_{b}"] = P.loc[fl.index, b]
cols = ["match_id", "tabpfn_split", "tour", "season", "tournament_name", "round", "td_date", "td_winner", "td_loser", "a_won",
        "name_a", "name_b", "rank_a", "rank_b", "avg_a", "avg_b", "max_a", "max_b", "p_mkt", "p_ref_median", "n_ref", "ref_spread",
        "p_B365", "p_PS", "p_EX", "p_LB", "p_SJ", "p_Max", "p_elo", "max_agrees_with_avg", "flag", "link", "td_comment"]
fl[cols + ["dev_from_refs"]].sort_values(["flag", "dev_from_refs"], ascending=False).to_csv(OUTD / "a07_avg_vs_books.csv", index=False)
y = D["a_won"].astype(float).to_numpy()
out = {"frame_rows": int(len(D)), "rows_with_a_referee": int((n_ref >= 1).sum()),
       "reversed": int(reversed_.sum()), "reversed_by_split": D[reversed_].groupby("tabpfn_split").size().to_dict(),
       "garbled": int(garbled.sum()), "garbled_by_split": D[garbled].groupby("tabpfn_split").size().to_dict(),
       "dev_from_refs_quantiles": dev.quantile([.5, .9, .99, .999, 1]).round(4).to_dict()}
# log-loss cost of the flagged rows (the market's own, vs the referees' median)
for lab, m in (("reversed", reversed_), ("garbled", garbled)):
    if m.any():
        pm, pr = D.loc[m, "p_mkt"].to_numpy(), med[m].to_numpy()
        yy = y[m.to_numpy()]
        out[f"{lab}_logloss_avg"] = round(float(-(yy * np.log(pm) + (1 - yy) * np.log(1 - pm)).mean()), 4)
        out[f"{lab}_logloss_refs"] = round(float(-(yy * np.log(pr) + (1 - yy) * np.log(1 - pr)).mean()), 4)
        out[f"{lab}_winner_favoured_by_avg"] = int(((pm > .5) == (yy == 1)).sum())
        out[f"{lab}_winner_favoured_by_refs"] = int(((pr > .5) == (yy == 1)).sum())
(OUTD / "a07_avg_vs_books.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str))
show = ["match_id", "tabpfn_split", "tournament_name", "round", "td_winner", "td_loser", "a_won", "rank_a", "rank_b", "avg_a", "avg_b",
        "max_a", "max_b", "p_mkt", "p_ref_median", "n_ref", "p_B365", "p_PS", "p_Max", "p_elo", "flag"]
print(fl.sort_values(["flag", "dev_from_refs"], ascending=[False, False])[show].round(3).to_string())

# links by round alone
ra = D[D["same_set_scores"] == False].copy()  # noqa: E712
ra["name_match"] = [str(a).lower()[:4] in str(b).lower() or str(b).lower()[:4] in str(a).lower()
                    for a, b in zip(ra["tournament_name"], ra["td_tournament"])]
ra[["match_id", "tabpfn_split", "tournament_name", "td_tournament", "round", "td_round", "tournament_date", "td_date",
    "days_from_monday", "score", "td_winner", "td_loser", "link", "td_comment", "p_mkt", "p_elo", "name_match"]].to_csv(
    OUTD / "a07_round_alone.csv", index=False)
print("\nlinks without identical set scores in the frame:", len(ra), "| by split", ra.groupby("tabpfn_split").size().to_dict(),
      "| td comment", ra["td_comment"].value_counts(dropna=False).to_dict(), "| Stage 0 status", ra["status"].value_counts().to_dict())
print("round-alone links whose tennis-data event name shares no 4-letter prefix with Stage 0's:", int((~ra["name_match"]).sum()))
print(ra[~ra["name_match"]][["match_id", "tournament_name", "td_tournament", "round", "td_round", "tournament_date", "td_date",
                             "score", "td_winner", "td_loser"]].head(60).to_string())

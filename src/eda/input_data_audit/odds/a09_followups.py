"""Follow-ups:
    (a) frame rows whose average-odds overround is unusual (< 1.02 or > 1.10), with the referees
    (b) unlinked tennis-data rows that are eligible matches left without odds (strict: same season, both surnames,
        round agrees or the td date is a typo of the event's month)
    (c) the rows the 7 Oct Stage 1 adds (ATP 2018, Aug-Sep 2026): the same reversal scan against B365 and Pinnacle

Outputs (out/): a09_overround_outliers.csv, a09_unlinked_eligible.csv, a09_new_rows_scan.json, a09_new_rows_flagged.csv
"""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

from _common import NEW, OLD, OUTD, ROOT

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 60)
D = pd.read_parquet(OUTD / "a03_joined.parquet")


def devig(a, b):
    return (1 / a) / (1 / a + 1 / b)


# (a)
D["ovr"] = 1 / D["avg_a"] + 1 / D["avg_b"]
D["p_ps"], D["p_b365"], D["p_max"] = devig(D["ps_a"], D["ps_b"]), devig(D["b365_a"], D["b365_b"]), devig(D["max_a"], D["max_b"])
oo = D[(D["ovr"] < 1.02) | (D["ovr"] > 1.10)]
cols = ["match_id", "tabpfn_split", "tournament_name", "round", "td_winner", "td_loser", "a_won", "avg_a", "avg_b", "max_a", "max_b",
        "ps_a", "ps_b", "b365_a", "b365_b", "ovr", "p_mkt", "p_ps", "p_b365", "p_max", "p_elo"]
oo[cols].to_csv(OUTD / "a09_overround_outliers.csv", index=False)
print("frame rows with overround < 1.02 or > 1.10:", len(oo), oo.groupby("tabpfn_split").size().to_dict())
print(oo[cols].round(3).to_string())
dd = (oo["p_mkt"] - oo[["p_ps", "p_b365"]].median(axis=1)).abs()
print("their |p_mkt - median(PS, B365)|:", dd.round(3).tolist())

# (b)
fr = pd.read_parquet(ROOT / "data/studies/tabpfn_thinking/frame.parquet",
                     columns=["match_id", "tour", "year", "split", "tabpfn_split", "tournament_name", "tournament_date"])
s0 = pd.read_parquet(OLD / "stage0_matches.parquet", columns=["match_id", "round"])
miss = fr[(fr["split"] != "") & (fr["tabpfn_split"] == "")].merge(s0, on="match_id")
mp = pd.read_parquet(OLD / "stage0_match_players.parquet", columns=["match_id", "player_name"])
mp = mp[mp["match_id"].isin(miss["match_id"])]
names = mp.groupby("match_id")["player_name"].apply(lambda s: " | ".join(s).lower())
miss["players"] = miss["match_id"].map(names)
un = pd.read_parquet(OLD / "stage1_odds_unlinked.parquet")
TDR = {"1st Round": None, "2nd Round": None, "3rd Round": None, "4th Round": None, "Quarterfinals": "QF", "Semifinals": "SF",
       "The Final": "F", "Round Robin": "RR"}


def key_tokens(td_name: str) -> list[str]:
    sur = re.sub(r"\s+[A-Z]\.(\s*[A-Z]\.)*$", "", str(td_name)).strip().lower()
    return [t for t in re.split(r"[\s\-']+", sur) if len(t) >= 3] or [sur]


hits = []
for _, u in un.iterrows():
    cand = miss[(miss["tour"] == u["tour"]) & (miss["year"] == u["td_season"])]
    wt, lt = key_tokens(u["td_winner"]), key_tokens(u["td_loser"])
    if cand.empty:
        continue
    m = cand[cand["players"].fillna("").apply(lambda s: any(t in s for t in wt) and any(t in s for t in lt)).astype(bool).to_numpy()]
    r = TDR.get(u["td_round"])
    if r is not None:
        m = m[m["round"] == r]
    for _, c in m.iterrows():
        gap = (pd.Timestamp(u["td_date"]) - c["tournament_date"]).days if pd.notna(u["td_date"]) else None
        hits.append({"td_file": u["td_file"], "td_row": u["td_row"], "td_date": u["td_date"], "td_tournament": u["td_tournament"],
                     "td_round": u["td_round"], "td_winner": u["td_winner"], "td_loser": u["td_loser"], "AvgW": u["AvgW"],
                     "AvgL": u["AvgL"], "match_id": c["match_id"], "players": c["players"], "tournament_name": c["tournament_name"],
                     "tournament_date": c["tournament_date"], "days_td_minus_monday": gap})
hits = pd.DataFrame(hits)
hits = hits[hits["days_td_minus_monday"].abs() <= 120] if len(hits) else hits
hits.to_csv(OUTD / "a09_unlinked_eligible.csv", index=False)
print("\nunlinked tennis-data rows that are eligible matches without odds:", len(hits),
      "| distinct matches", hits["match_id"].nunique() if len(hits) else 0)
print(hits[["td_date", "td_tournament", "td_round", "td_winner", "td_loser", "AvgW", "AvgL", "match_id", "tournament_date",
            "days_td_minus_monday"]].to_string() if len(hits) else "")

# (c) the rows the 7 Oct Stage 1 adds
o7 = pd.read_parquet(NEW / "stage1_odds.parquet")
s7 = pd.read_parquet(NEW / "stage0_matches.parquet", columns=["match_id", "a_won"])
add = o7[((o7["tour"] == "atp") & (o7["year"] == 2018)) | (o7["td_date"] >= "2026-08-03")]
add = add[add["p_avg_a"].notna()].merge(s7, on="match_id")
add["p_ps"], add["p_b365"], add["p_max"] = devig(add["ps_a"], add["ps_b"]), devig(add["b365_a"], add["b365_b"]), devig(add["max_a"], add["max_b"])
ref = add[["p_ps", "p_b365"]]
nref = ref.notna().sum(axis=1)
opp = ((ref.sub(0.5).mul(add["p_avg_a"] - 0.5, axis=0) < 0) & (ref.sub(add["p_avg_a"], axis=0).abs() > 0.2)) | ref.isna()
rev = (nref >= 1) & opp.all(axis=1)
dev = (add["p_avg_a"] - ref.median(axis=1)).abs()
y = add["a_won"].astype(float)
p = add["p_avg_a"]
out = {}
for lab, m in (("atp2018", (add["tour"] == "atp") & (add["year"] == 2018)), ("from_2026-08-03", add["td_date"] >= "2026-08-03")):
    g = add[m]
    out[lab] = {"rows_with_p": int(len(g)), "reversed_vs_refs": int(rev[m].sum()), "dev_gt_0.15": int((dev[m] > .15).sum()),
                "links": g["link"].value_counts().to_dict(),
                "logloss": round(float(-(y[m] * np.log(p[m]) + (1 - y[m]) * np.log(1 - p[m])).mean()), 4),
                "fav_win_rate": round(float(((p[m] > .5) == (y[m] == 1)).mean()), 4),
                "mean_p_fav": round(float(np.maximum(p[m], 1 - p[m]).mean()), 4)}
(OUTD / "a09_new_rows_scan.json").write_text(json.dumps(out, indent=1))
print("\n", json.dumps(out, indent=1))
fl = add[rev | (dev > .15)]
fl[["match_id", "td_tournament", "td_round", "td_winner", "td_loser", "a_won", "avg_a", "avg_b", "max_a", "max_b", "ps_a", "ps_b",
    "b365_a", "b365_b", "p_avg_a", "p_ps", "p_b365", "link"]].to_csv(OUTD / "a09_new_rows_flagged.csv", index=False)
print(fl[["match_id", "td_tournament", "td_round", "td_winner", "td_loser", "a_won", "avg_a", "avg_b", "max_a", "max_b", "ps_a", "ps_b",
          "b365_a", "b365_b", "p_avg_a", "p_ps", "p_b365"]].round(3).to_string())

"""Tasks 3-5 on the model frame (30 Sep links):
    (a) the winner_swapped links: do the odds follow tennis-data's names (as Stage 1 assumes) or the result?
    (b) placeholder rows (no score / 'Sched') and walkovers among the frame rows
    (c) is the average biased toward the actual winner relative to Pinnacle (late, in-play captures)?
    (d) exact 0.5 and other value clusters, extreme prices
    (e) why frame-eligible matches have no odds; the unlinked tennis-data rows
    (f) one-player-anchor links: is the other player the same person?

Outputs (out/): a06_winner_swapped.csv, a06_placeholders.csv, a06_inplay.json, a06_values.json,
                a06_missing_odds.csv, a06_missing_odds_summary.json, a06_unlinked_vs_missing.csv, a06_anchor_names.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from _common import OLD, OUTD, ROOT, logit, num

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 60)
D = pd.read_parquet(OUTD / "a03_joined.parquet")
td30 = pd.read_parquet(OUTD / "a05_td30.parquet")
raw = td30.set_index(["td_file", "td_row"])
D["td_row"] = D["td_row"].astype("Int64")
R = raw.reindex(pd.MultiIndex.from_arrays([D["td_file"].astype(str), D["td_row"].astype("int64")]))
for c in ["W1", "L1", "W2", "L2", "W3", "L3", "Wsets", "Lsets", "WRank", "LRank", "Comment", "Date"]:
    D[f"raw_{c}"] = R[c].to_numpy()
res = {}

# (a) winner_swapped
ws = D[D["link"] == "winner_swapped"].copy()
ws["p_elo_a"] = ws["p_elo"]
ws["p_as_stored"] = ws["p_mkt"]
ws["p_if_odds_follow_result"] = 1 - ws["p_mkt"]
lg = lambda x: logit(np.clip(np.asarray(x, dtype=float), 1e-6, 1 - 1e-6))  # noqa: E731
ws["dist_stored"] = np.abs(lg(ws["p_as_stored"]) - lg(ws["p_elo_a"]))
ws["dist_flipped"] = np.abs(lg(ws["p_if_odds_follow_result"]) - lg(ws["p_elo_a"]))
ws["rank_fav_is_a"] = ws["rank_a"] < ws["rank_b"]
ws["stored_fav_is_a"] = ws["p_mkt"] > 0.5
cols = ["match_id", "tabpfn_split", "tournament_name", "round", "name_a", "name_b", "rank_a", "rank_b", "a_won", "score",
        "td_winner", "td_loser", "raw_W1", "raw_L1", "raw_W2", "raw_L2", "raw_W3", "raw_L3", "raw_Wsets", "raw_Lsets", "raw_Comment",
        "avg_a", "avg_b", "ps_a", "ps_b", "b365_a", "b365_b", "p_mkt", "p_elo", "dist_stored", "dist_flipped", "same_set_scores"]
ws[cols].to_csv(OUTD / "a06_winner_swapped.csv", index=False)
print("winner_swapped links in the frame:", len(ws))
print(ws[cols].round(3).to_string())
res["winner_swapped_n"] = int(len(ws))
res["winner_swapped_closer_to_elo_when_flipped"] = int((ws["dist_flipped"] < ws["dist_stored"]).sum())

# (b) placeholders and walkovers
ph = D[D["td_comment"].isna() | D["td_comment"].isin(["Sched", "Walkover", "Rrtired"]) |
       (D["td_comment"].eq("Completed") & D["status"].eq("retired")) | (D["td_comment"].eq("Retired") & D["status"].eq("completed"))]
ph[[c for c in cols if c in ph.columns] + ["status", "td_comment"]].to_csv(OUTD / "a06_placeholders.csv", index=False)
print("\nplaceholder / walkover / status-comment mismatch rows in the frame:", len(ph))
print(ph[["match_id", "tabpfn_split", "tournament_name", "round", "status", "td_comment", "score", "td_winner", "td_loser",
          "raw_W1", "raw_L1", "raw_W2", "raw_L2", "raw_W3", "raw_L3", "link", "p_mkt", "p_elo"]].round(3).to_string())

# (c) the average vs Pinnacle, toward the winner?
def devig(a, b):
    return (1 / a) / (1 / a + 1 / b)


D["p_ps"] = devig(D["ps_a"], D["ps_b"])
D["p_b365"] = devig(D["b365_a"], D["b365_b"])
y = D["a_won"].astype(float)
pw_avg = np.where(y == 1, D["p_mkt"], 1 - D["p_mkt"])
pw_ps = np.where(y == 1, D["p_ps"], 1 - D["p_ps"])
pw_b = np.where(y == 1, D["p_b365"], 1 - D["p_b365"])
d = pd.Series(pw_avg - pw_ps)
db = pd.Series(pw_avg - pw_b)
ip = {}
for lab, dd in (("avg_minus_ps", d), ("avg_minus_b365", db)):
    ok = dd.notna()
    rec = {"n": int(ok.sum()), "mean": round(float(dd[ok].mean()), 5), "share_toward_winner": round(float((dd[ok] > 0).mean()), 4)}
    for thr in (0.05, 0.1, 0.2):
        big = ok & (dd.abs() > thr)
        rec[f"n_abs_gt_{thr}"] = int(big.sum())
        rec[f"share_toward_winner_abs_gt_{thr}"] = round(float((dd[big] > 0).mean()), 4) if big.any() else None
    ip[lab] = rec
# by split, by season
ip["avg_minus_ps_by_split"] = {s: {"mean": round(float(d[(D["tabpfn_split"] == s) & d.notna()].mean()), 5),
                                   "n_gt_0.1": int(((d.abs() > .1) & (D["tabpfn_split"] == s)).sum()),
                                   "toward_winner_gt_0.1": int(((d > .1) & (D["tabpfn_split"] == s)).sum())}
                               for s in ("train", "test")}
# log loss of each source on the same rows
both = d.notna() & db.notna()
for nm, pw in (("avg", pw_avg), ("ps", pw_ps), ("b365", pw_b)):
    ip[f"logloss_{nm}_rows_with_all_three"] = round(float(-np.log(np.asarray(pw, dtype=float)[both.to_numpy()]).mean()), 5)
(OUTD / "a06_inplay.json").write_text(json.dumps(ip, indent=1))
print("\nin-play / late-capture check:", json.dumps(ip, indent=1))

# (d) values
v = {}
p = D["p_mkt"].to_numpy(dtype=float)
v["p_exactly_0.5"] = int((p == 0.5).sum())
v["p_exactly_0.5_by_split"] = D[p == 0.5].groupby("tabpfn_split").size().to_dict()
v["p_exactly_0.5_share_by_season"] = (D.assign(h=p == 0.5).groupby(["tour", "season"])["h"].mean().round(4)
                                      .reset_index().pivot(index="season", columns="tour", values="h").to_dict())
v["p_exactly_0.5_odds_values"] = D.loc[p == 0.5, "avg_a"].value_counts().head(10).to_dict()
# the same pair of odds repeated many times within an event (copy-down)
D["pair"] = D["avg_a"].round(2).astype(str) + "/" + D["avg_b"].round(2).astype(str)
rep = D.groupby(["tour", "season", "tournament_id", "pair"]).size()
v["same_odds_pair_ge4_in_one_event"] = rep[rep >= 4].reset_index().rename(columns={0: "n"}).to_dict("records")
v["p_lt_0.02_or_gt_0.98"] = int(((p < .02) | (p > .98)).sum())
v["p_lt_0.05_or_gt_0.95"] = int(((p < .05) | (p > .95)).sum())
v["p_quantiles"] = pd.Series(p).quantile([0, .001, .01, .5, .99, .999, 1]).round(5).to_dict()
mx = np.maximum(D["avg_a"], D["avg_b"])
v["max_avg_odds_quantiles"] = mx.quantile([.5, .99, .999, 1]).to_dict()
v["avg_odds_ge_20"] = int((mx >= 20).sum())
ext = D[(p < .03) | (p > .97)]
v["extreme_rows"] = ext[["match_id", "tabpfn_split", "tournament_name", "round", "name_a", "name_b", "rank_a", "rank_b", "a_won",
                         "avg_a", "avg_b", "ps_a", "ps_b", "b365_a", "b365_b", "p_mkt", "p_elo"]].round(3).to_dict("records")
v["extreme_rows_upsets"] = int(((ext["p_mkt"] > .5) != ext["a_won"]).sum())
ov = 1 / D["avg_a"] + 1 / D["avg_b"]
v["frame_overround_quantiles"] = ov.quantile([0, .001, .01, .5, .99, .999, 1]).round(4).to_dict()
v["frame_overround_lt_1.02"] = int((ov < 1.02).sum())
v["frame_overround_gt_1.10"] = int((ov > 1.10).sum())
(OUTD / "a06_values.json").write_text(json.dumps(v, indent=1, default=str))
print("\nvalues:", json.dumps({k: x for k, x in v.items() if k not in ("extreme_rows",)}, indent=1, default=str)[:5000])
print(pd.DataFrame(v["extreme_rows"]).to_string())

# (e) eligible matches without odds
fr = pd.read_parquet(ROOT / "data/studies/tabpfn_thinking/frame.parquet",
                     columns=["match_id", "tour", "year", "group", "status", "split", "tabpfn_split", "tournament_name", "tournament_date"])
o30 = pd.read_parquet(OLD / "stage1_odds.parquet")
miss = fr[(fr["split"] != "") & (fr["tabpfn_split"] == "")].merge(
    o30[["match_id", "link", "td_file", "td_row", "avg_a", "avg_b", "overround_avg", "avg_coherent", "td_comment"]], on="match_id", how="left")
miss["reason"] = np.select(
    [miss["link"].isna(), miss["link"].eq("none") & (miss["tour"].eq("atp") & miss["year"].eq(2018)),
     miss["link"].eq("none") & (miss["tournament_date"] >= "2026-07-27"), miss["link"].eq("none"),
     miss["avg_a"].isna() | miss["avg_b"].isna(), ~miss["avg_coherent"].astype(bool)],
    ["not a Stage 1 candidate", "no ATP 2018 workbook", "after the 3 Aug 2026 capture", "not linked",
     "linked, average odds missing", "linked, overround outside 1.00-1.20"], "other")
miss.to_csv(OUTD / "a06_missing_odds.csv", index=False)
ms = {"eligible_without_odds": int(len(miss)), "by_reason": miss["reason"].value_counts().to_dict(),
      "by_reason_tour_year": miss.groupby(["reason", "tour", "year"]).size().reset_index(name="n").to_dict("records")}
nl = miss[miss["reason"] == "not linked"]
ms["not_linked_by_event"] = nl.groupby(["tour", "year", "tournament_name"]).size().sort_values(ascending=False).head(40).reset_index(name="n").to_dict("records")
(OUTD / "a06_missing_odds_summary.json").write_text(json.dumps(ms, indent=1, default=str))
print("\nmissing odds:", json.dumps({k: x for k, x in ms.items() if k != "by_reason_tour_year"}, indent=1, default=str))
print(pd.DataFrame(ms["by_reason_tour_year"]).pivot_table(index=["tour", "year"], columns="reason", values="n", fill_value=0).to_string())
# unlinked tennis-data rows vs the missing matches
un = pd.read_parquet(OLD / "stage1_odds_unlinked.parquet")
print("\nunlinked td rows (30 Sep):", len(un), un["reason"].value_counts().to_dict())
mp = pd.read_parquet(OLD / "stage0_match_players.parquet", columns=["match_id", "player_name"])
mp = mp[mp["match_id"].isin(nl["match_id"])]
names = mp.groupby("match_id")["player_name"].apply(lambda s: " | ".join(s))
nl = nl.assign(players=nl["match_id"].map(names))
hits = []
for _, u in un.iterrows():
    w = str(u["td_winner"]).split(" ")[0].lower()
    l_ = str(u["td_loser"]).split(" ")[0].lower()
    cand = nl[(nl["tour"] == u["tour"]) & nl["players"].str.lower().str.contains(w, regex=False, na=False) &
              nl["players"].str.lower().str.contains(l_, regex=False, na=False)]
    for _, c in cand.iterrows():
        hits.append({"td_file": u["td_file"], "td_row": u["td_row"], "td_date": u["td_date"], "td_tournament": u["td_tournament"],
                     "td_round": u["td_round"], "td_winner": u["td_winner"], "td_loser": u["td_loser"], "reason": u["reason"],
                     "AvgW": u["AvgW"], "AvgL": u["AvgL"], "match_id": c["match_id"], "players": c["players"],
                     "tournament_name": c["tournament_name"], "tournament_date": c["tournament_date"]})
hits = pd.DataFrame(hits)
hits.to_csv(OUTD / "a06_unlinked_vs_missing.csv", index=False)
print("unlinked td rows that name both players of an eligible match without odds:", len(hits))
if len(hits):
    print(hits.to_string())
print(un[["tour", "td_season", "td_date", "td_tournament", "td_round", "td_winner", "td_loser", "reason", "AvgW", "AvgL"]].to_string())

# (f) anchors: is the other player the same person?
an = D[D["link"] == "one_player_anchor"].copy()
a_is_w = an["a_won"].astype(bool)
an["td_name_a"] = np.where(a_is_w, an["td_winner"], an["td_loser"])
an["td_name_b"] = np.where(a_is_w, an["td_loser"], an["td_winner"])


def surname_hit(full, td):
    full, td = str(full).lower(), str(td).lower()
    sur = td.rsplit(" ", 1)[0] if " " in td else td
    toks = [t for t in sur.replace("-", " ").split() if len(t) > 2]
    return any(t in full for t in toks)


an["a_name_hit"] = [surname_hit(f, t) for f, t in zip(an["name_a"], an["td_name_a"])]
an["b_name_hit"] = [surname_hit(f, t) for f, t in zip(an["name_b"], an["td_name_b"])]
bad = an[~(an["a_name_hit"] & an["b_name_hit"])]
bad[["match_id", "tabpfn_split", "tournament_name", "round", "name_a", "td_name_a", "name_b", "td_name_b", "rank_a", "rank_b",
     "rank_agrees_a", "rank_agrees_b", "p_mkt", "p_elo"]].to_csv(OUTD / "a06_anchor_names.csv", index=False)
print("\nanchor links in the frame:", len(an), "| the other name shares no surname token:", len(bad),
      "| of which a rank disagrees:", int(((bad["rank_agrees_a"] == False) | (bad["rank_agrees_b"] == False)).sum()))  # noqa: E712
print(bad[["match_id", "tabpfn_split", "name_a", "td_name_a", "name_b", "td_name_b", "rank_a", "rank_b", "rank_agrees_a",
           "rank_agrees_b", "p_mkt", "p_elo"]].head(60).to_string())

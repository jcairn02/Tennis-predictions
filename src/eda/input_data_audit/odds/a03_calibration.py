"""Task 3: the market's calibration per season, level and event, and suspect (reversed / mislinked) matches,
on the model frame's 63,737 matches with the 30 Sep Stage 1 links behind them.

Outputs (out/):
    a03_joined.parquet          model frame + 30 Sep Stage 1 link columns + Stage 0 names/ranks + Elo probability
    a03_season.csv              per tour x season (and split): n, log loss, Brier, fav win rate vs implied, slope/intercept
    a03_season_level.csv        per tour x season x level
    a03_month_2024_on.csv       per tour x month from 2024 (the book-mix change)
    a03_events.csv              per event: n, favourite wins vs expected (z), log loss vs its expectation (z)
    a03_events_flagged.csv      events with |z| >= 3 on either test
    a03_suspects.csv            matches flagged by rank reversal, Elo reversal, cross-book disagreement, rank mismatch
    a03_links.json              link types, verification flags and per-link-type calibration on frame rows
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from _common import MF, OLD, OUTD, ROOT, logit

mf = pd.read_parquet(MF, columns=["match_id", "tour", "season", "tournament_date", "a_won", "p_mkt", "tabpfn_split"])
o30 = pd.read_parquet(OLD / "stage1_odds.parquet")
s30 = pd.read_parquet(OLD / "stage0_matches.parquet",
                      columns=["match_id", "tournament_id", "tournament_name", "score", "status", "player_a_id", "player_b_id",
                               "level", "round", "source"])
mp = pd.read_parquet(OLD / "stage0_match_players.parquet", columns=["match_id", "side", "player_name", "rank"])
mp = mp[mp["match_id"].isin(mf["match_id"])]
fr = pd.read_parquet(ROOT / "data/studies/tabpfn_thinking/frame.parquet", columns=["match_id", "p_elo"])

D = mf.merge(o30.drop(columns=["tour", "tournament_date", "status", "level", "round"]), on="match_id", how="left")
D = D.merge(s30, on="match_id", how="left").merge(fr, on="match_id", how="left")
for sd in ("A", "B"):
    x = mp[mp["side"] == sd].set_index("match_id")
    D[f"name_{sd.lower()}"] = D["match_id"].map(x["player_name"])
    D[f"rank_{sd.lower()}"] = D["match_id"].map(x["rank"])
y = D["a_won"].astype(float).to_numpy()
p = D["p_mkt"].to_numpy(dtype=float)
D["p_winner"] = np.where(y == 1, p, 1 - p)
D["ll"] = -np.log(D["p_winner"])
D["fav_won"] = np.where(p == 0.5, np.nan, ((p > 0.5) == (y == 1)).astype(float))
D["p_fav"] = np.maximum(p, 1 - p)
D["ll_exp"] = -(p * np.log(p) + (1 - p) * np.log(1 - p))
D["ll_var"] = p * (1 - p) * np.log(p / (1 - p)) ** 2
D["month"] = pd.to_datetime(D["td_date"]).dt.strftime("%Y-%m")
D.to_parquet(OUTD / "a03_joined.parquet", index=False)


def fit_logit(z, yy, iters=50):
    """Logistic regression y ~ a + b*z by Newton's method; returns (a, b)."""
    X = np.column_stack([np.ones_like(z), z])
    w = np.zeros(2)
    for _ in range(iters):
        eta = X @ w
        mu = 1 / (1 + np.exp(-eta))
        g = X.T @ (yy - mu)
        H = (X * (mu * (1 - mu))[:, None]).T @ X
        step = np.linalg.solve(H, g)
        w += step
        if np.abs(step).max() < 1e-10:
            break
    return w


def summarise(g: pd.DataFrame) -> pd.Series:
    z = logit(g["p_mkt"].to_numpy(dtype=float))
    yy = g["a_won"].astype(float).to_numpy()
    a, b = fit_logit(z, yy) if len(g) > 50 else (np.nan, np.nan)
    pf = g["p_fav"].to_numpy()
    fw = g["fav_won"].dropna().astype(float)
    exp_fw = g.loc[g["fav_won"].notna(), "p_fav"]
    zf = (fw.sum() - exp_fw.sum()) / np.sqrt((exp_fw * (1 - exp_fw)).sum()) if len(fw) else np.nan
    zl = (g["ll"].sum() - g["ll_exp"].sum()) / np.sqrt(g["ll_var"].sum())
    return pd.Series({"n": len(g), "logloss": g["ll"].mean(), "logloss_expected": g["ll_exp"].mean(),
                      "z_logloss": zl, "brier": ((g["p_mkt"] - yy) ** 2).mean(),
                      "fav_win_rate": fw.mean(), "mean_p_fav": exp_fw.mean(), "z_fav": zf,
                      "mean_p_winner": g["p_winner"].mean(), "cal_intercept": a, "cal_slope": b})


season = D.groupby(["tour", "season"]).apply(summarise).reset_index()
season.to_csv(OUTD / "a03_season.csv", index=False)
pd.set_option("display.width", 250)
print(season.round(4).to_string())
lev = D.groupby(["tour", "season", "level"]).apply(summarise).reset_index()
lev.to_csv(OUTD / "a03_season_level.csv", index=False)
mon = D[D["tournament_date"] >= "2024-01-01"].groupby(["tour", "month"]).apply(summarise).reset_index()
mon.to_csv(OUTD / "a03_month_2024_on.csv", index=False)
print(mon.round(4).to_string())
sp = D.groupby(["tabpfn_split"]).apply(summarise).reset_index()
print(sp.round(4).to_string())

# events
ev = D.groupby(["tour", "season", "tournament_id", "tournament_name", "level"]).apply(summarise).reset_index()
ev["split"] = np.where(ev["season"] >= 2022, "test", "train")
ev.to_csv(OUTD / "a03_events.csv", index=False)
fl = ev[(ev["z_fav"].abs() >= 3) | (ev["z_logloss"].abs() >= 3)].sort_values("z_logloss", ascending=False)
fl.to_csv(OUTD / "a03_events_flagged.csv", index=False)
print("events:", len(ev), "flagged |z|>=3:", len(fl))
print(fl.round(3).to_string())
# how many flags would chance give? (two one-sided tests at |z|>=3 ~ 0.27% each, correlated)
print("expected by chance at |z|>=3 on one test: ~", round(len(ev) * 0.0027, 1))

# suspects
S = D.copy()
fav_is_a = S["p_mkt"] > 0.5
S["rank_fav"] = np.where(fav_is_a, S["rank_a"], S["rank_b"])
S["rank_dog"] = np.where(fav_is_a, S["rank_b"], S["rank_a"])
S["rank_reversal"] = (S["p_fav"] >= 0.8) & (S["rank_fav"] >= 150) & (S["rank_dog"] <= 30)
pe = S["p_elo"].to_numpy(dtype=float)
S["elo_reversal"] = np.isfinite(pe) & (np.abs(logit(np.clip(pe, 1e-6, 1 - 1e-6)) - logit(p)) >= 3) & ((pe - 0.5) * (p - 0.5) < 0)


def devig(a, b):
    return (1 / a) / (1 / a + 1 / b)


S["p_ps"] = devig(S["ps_a"], S["ps_b"])
S["p_b365"] = devig(S["b365_a"], S["b365_b"])
S["p_max"] = devig(S["max_a"], S["max_b"])
others = S[["p_ps", "p_b365", "p_max"]]
n_other = others.notna().sum(axis=1)
opp = ((others.sub(0.5).mul(S["p_mkt"] - 0.5, axis=0) < 0) & (others.sub(S["p_mkt"], axis=0).abs() > 0.2)).sum(axis=1)
S["n_books_other"] = n_other
S["n_books_opposite"] = opp
S["cross_book_reversal"] = (n_other >= 1) & (opp == n_other)
S["max_abs_dev_other"] = others.sub(S["p_mkt"], axis=0).abs().max(axis=1)
S["rank_mismatch_both"] = (S["rank_agrees_a"] == False) & (S["rank_agrees_b"] == False)  # noqa: E712
flags = ["rank_reversal", "elo_reversal", "cross_book_reversal", "rank_mismatch_both"]
sus = S[S[flags].any(axis=1)]
cols = ["match_id", "tour", "season", "tabpfn_split", "tournament_name", "round", "td_date", "link", "td_winner", "td_loser",
        "name_a", "name_b", "rank_a", "rank_b", "a_won", "score", "td_comment", "avg_a", "avg_b", "ps_a", "ps_b", "b365_a",
        "b365_b", "max_a", "max_b", "p_mkt", "p_ps", "p_b365", "p_max", "p_elo", "same_set_scores", "round_agrees",
        "rank_agrees_a", "rank_agrees_b"] + flags + ["n_books_other", "n_books_opposite", "max_abs_dev_other"]
sus[cols].to_csv(OUTD / "a03_suspects.csv", index=False)
print({f: int(S[f].sum()) for f in flags})
print("by split:", {f: S[S[f]].groupby("tabpfn_split").size().to_dict() for f in flags})
print("cross-book reversals:")
print(sus[sus["cross_book_reversal"]][cols[:30]].to_string())
# the deviation of the average from Pinnacle on frame rows
dev = (S["p_mkt"] - S["p_ps"]).abs()
print("p_mkt vs Pinnacle (both present):", int(S["p_ps"].notna().sum()), "| |diff| quantiles",
      dev.quantile([.5, .9, .99, .999, 1]).round(4).to_dict(), "| >0.10:", int((dev > .1).sum()), ">0.20:", int((dev > .2).sum()))

# links
L = {"link_counts": D["link"].value_counts().to_dict(),
     "same_set_scores_false": int((D["same_set_scores"] == False).sum()),  # noqa: E712
     "round_agrees": D["round_agrees"].value_counts().to_dict(),
     "rank_agrees_a_false": int((D["rank_agrees_a"] == False).sum()),  # noqa: E712
     "rank_agrees_b_false": int((D["rank_agrees_b"] == False).sum()),  # noqa: E712
     "rank_mismatch_both": int(S["rank_mismatch_both"].sum()),
     "days_from_monday_quantiles": D["days_from_monday"].quantile([0, .001, .01, .5, .99, .999, 1]).to_dict(),
     "days_from_monday_lt_-1": int((D["days_from_monday"] < -1).sum()),
     "days_from_monday_gt_15": int((D["days_from_monday"] > 15).sum()),
     "td_redated_rows_in_frame": int(D["td_redated"].sum()),
     "td_comment_counts": D["td_comment"].value_counts().to_dict(),
     "status_vs_td_comment": pd.crosstab(D["status"], D["td_comment"]).to_dict()}
per = D.groupby("link").apply(summarise)
L["calibration_by_link"] = per.round(4).to_dict("index")
(OUTD / "a03_links.json").write_text(json.dumps(L, indent=1, default=str))
print(json.dumps(L, indent=1, default=str))

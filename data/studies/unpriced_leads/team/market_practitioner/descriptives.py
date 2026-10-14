"""Outcome-free descriptives for the market practitioner's memo (unpriced_leads, round 1, B3).

Reads NO match outcome of any season: the columns a_won, won, score, status and anything derived from results are never
loaded. Prices, their times, entry codes, countries, ranks and the clock are pre-match facts.
Market-response readings (book-vs-book shading, open-to-close moves) are restricted to seasons <= 2024, so the
2025-26 confirmation window stays clean for every new statistic. Counts and price timing of 2025-26 are coverage only.

Run: ./python.sh data/studies/unpriced_leads/team/market_practitioner/descriptives.py
Writes descriptives.json beside this file.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
T = ROOT / "data/studies/current_best_model/template_2026-10-10"
S0 = ROOT / "data/studies/predictability_diagnostic"


def lg(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def devig(oa, ob):
    ia, ib = 1.0 / np.asarray(oa, float), 1.0 / np.asarray(ob, float)
    s = ia + ib
    ok = np.isfinite(s) & (s >= 1.0) & (s <= 1.20)
    return np.where(ok, ia / s, np.nan)


def ols_cluster(X, y, g):
    """OLS with cluster-robust (CR0) standard errors over clusters g."""
    m = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    X, y, g = X[m], y[m], g[m]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    xtx_inv = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for k in np.unique(g):
        s = (X[g == k] * r[g == k, None]).sum(axis=0)
        meat += np.outer(s, s)
    v = xtx_inv @ meat @ xtx_inv
    return b, np.sqrt(np.diag(v)), int(m.sum()), int(len(np.unique(g)))


res: dict = {"note": "outcome-free; market-response readings on seasons <= 2024 only"}

# ---------------------------------------------------------------- frame, no outcome column
mf = pd.read_parquet(T / "model_frame.parquet",
                     columns=["match_id", "tour", "season", "tournament_date", "debut_season", "in_level", "in_round",
                              "in_best_of", "in_indoor", "in_age", "odds_input", "in_odds_logit"])
mf["match_id"] = mf["match_id"].astype(str)
res["frame_counts"] = mf.groupby(["tour", "season"]).size().unstack(0).fillna(0).astype(int).to_dict()
res["odds_input_by_season"] = mf.groupby(["season", "odds_input"]).size().unstack(1).fillna(0).astype(int).to_dict()

s0 = pd.read_parquet(S0 / "stage0_matches.parquet",
                     columns=["match_id", "player_a_id", "player_b_id", "tournament_id", "tournament_name", "level"])
s0["match_id"] = s0["match_id"].astype(str)
mp = pd.read_parquet(S0 / "stage0_match_players.parquet",
                     columns=["match_id", "player_id", "entry", "country", "age", "rank"])
mp["match_id"] = mp["match_id"].astype(str)

f = mf.merge(s0, on="match_id", how="left")
pa = mp.rename(columns={c: f"{c}_a" for c in ["entry", "country", "age", "rank"]}).rename(
    columns={"player_id": "player_a_id"})
pb = mp.rename(columns={c: f"{c}_b" for c in ["entry", "country", "age", "rank"]}).rename(
    columns={"player_id": "player_b_id"})
f = f.merge(pa, on=["match_id", "player_a_id"], how="left").merge(pb, on=["match_id", "player_b_id"], how="left")

# orientation: is the frame's A Stage 0's player_a? (age difference against in_age)
d_age = f["age_a"] - f["age_b"]
ok = np.isfinite(d_age) & np.isfinite(f["in_age"])
res["orientation_check"] = {
    "rows_compared": int(ok.sum()),
    "corr_in_age_vs_age_a_minus_b": float(np.corrcoef(f.loc[ok, "in_age"], d_age[ok])[0, 1]),
    "share_same_sign": float((np.sign(f.loc[ok, "in_age"]) == np.sign(d_age[ok])).mean()),
}

# entry codes (pre-match facts) in frame matches
ent = {}
for code in ["Q", "LL", "WC", "PR", "SE", "ALT"]:
    has = (f["entry_a"] == code) | (f["entry_b"] == code)
    ent[code] = f.assign(h=has).groupby("season")["h"].mean().round(4).to_dict()
res["entry_share_by_season"] = ent

# US players
f["us_a"] = (f["country_a"] == "USA").astype(int)
f["us_b"] = (f["country_b"] == "USA").astype(int)
one_us = (f["us_a"] + f["us_b"]) == 1
res["one_us_player_share"] = f.assign(o=one_us).groupby(["tour", "season"])["o"].mean().round(3).unstack(0).to_dict()
res["country_missing_share"] = float(f["country_a"].isna().mean())

# ---------------------------------------------------------------- book prices (pre-match), BetOnline vs Pinnacle
bp = pd.read_parquet(T / "book_prices.parquet")
bp["match_id"] = bp["match_id"].astype(str)
f = f.merge(bp, on="match_id", how="left")
f["p_pin"] = devig(f["pin_a"], f["pin_b"])
f["p_bol"] = devig(f["bol_a"], f["bol_b"])
res["book_prices_note"] = "pin_*/bol_* read as decimal odds; sample values below"
res["book_prices_sample"] = f.loc[f["season"] == 2024, ["pin_a", "pin_b", "bol_a", "bol_b"]].dropna().head(3).to_dict(
    "records")

# stale benchmark: minutes between BetOnline's last line and the listed start, by season (coverage/timing only)
st = f[np.isfinite(f["bol_after_listed_min"])]
res["bol_close_minutes_after_listed_start"] = st.groupby("season")["bol_after_listed_min"].describe(
    percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]).round(1).to_dict("index")
res["bol_close_more_than_60min_before_start_share"] = st.assign(s=st["bol_after_listed_min"] < -60).groupby(
    ["tour", "season"])["s"].mean().round(3).unstack(0).to_dict()

# week cluster
f["week"] = pd.to_datetime(f["tournament_date"]).dt.to_period("W").astype(str)

# ---------------------------------------------------------------- outcome-free gate 1: BetOnline shading toward US players, <= 2024
def shading(df, x_col, label, y="d"):
    """y (oriented to A) on x (A minus B indicator) + odd polynomial of Pinnacle's log-odds (the books' margin shapes)."""
    L = lg(df["p_pin"])
    X = np.column_stack([df[x_col].to_numpy(float), L, L ** 3, L * np.abs(L)])
    b, se, n, k = ols_cluster(X, df[y].to_numpy(float), df["week"].to_numpy())
    return {"label": label, "coef_logodds": round(float(b[0]), 5), "se": round(float(se[0]), 5),
            "z": round(float(b[0] / se[0]), 2), "n": n, "clusters": k}


g = f[(f["season"] <= 2024) & np.isfinite(f["p_pin"]) & np.isfinite(f["p_bol"]) & (f["bol_after_listed_min"] <= 30)].copy()
g["d"] = lg(g["p_bol"]) - lg(g["p_pin"])  # + = BetOnline prices A shorter than Pinnacle does
g["us_diff"] = g["us_a"] - g["us_b"]
out = []
for tour in ["atp", "wta", None]:
    h = g if tour is None else g[g["tour"] == tour]
    out.append(shading(h, "us_diff", f"BetOnline close - Pinnacle close on US(A)-US(B), {tour or 'both'}, <=2024"))
# fame proxy: top-10 by rank at the match
g["top10_diff"] = (g["rank_a"] <= 10).astype(int) - (g["rank_b"] <= 10).astype(int)
for tour in ["atp", "wta"]:
    out.append(shading(g[g["tour"] == tour], "top10_diff", f"... on top10(A)-top10(B), {tour}, <=2024"))
res["gate_bol_vs_pin_shading"] = out

# ---------------------------------------------------------------- outcome-free gate 2: BetOnline's open->close move for US players, <= 2024
bt = pd.read_parquet(ROOT / "data/studies/bet_timing/frame.parquet",
                     columns=["match_id", "p_bol_open", "p_bol_close", "ok_bol_open", "ok_bol_close", "h_bol_open",
                              "h_bol_close"])
bt["match_id"] = bt["match_id"].astype(str)
f2 = f.merge(bt, on="match_id", how="inner")
res["bet_timing_orientation_check"] = {
    "corr_logit_pbolclose_frame_vs_bettiming": float(np.corrcoef(
        lg(f2.loc[np.isfinite(f2["p_bol"]) & np.isfinite(f2["p_bol_close"]), "p_bol"]),
        lg(f2.loc[np.isfinite(f2["p_bol"]) & np.isfinite(f2["p_bol_close"]), "p_bol_close"]))[0, 1])}
h = f2[(f2["season"] <= 2024) & f2["ok_bol_open"].astype(bool) & f2["ok_bol_close"].astype(bool)].copy()
h["p_pin"] = h["p_bol_open"]  # control for the opening price level here
h["mv"] = lg(h["p_bol_close"]) - lg(h["p_bol_open"])  # + = A shortened into the close
h["us_diff"] = h["us_a"] - h["us_b"]
mv = []
for tour in ["atp", "wta", None]:
    hh = h if tour is None else h[h["tour"] == tour]
    mv.append(shading(hh, "us_diff", f"BetOnline open->close move on US(A)-US(B), {tour or 'both'}, <=2024", y="mv"))
h["top10_diff"] = (h["rank_a"] <= 10).astype(int) - (h["rank_b"] <= 10).astype(int)
for tour in ["atp", "wta"]:
    mv.append(shading(h[h["tour"] == tour], "top10_diff", f"... on top10(A)-top10(B), {tour}, <=2024", y="mv"))
res["gate_bol_move"] = mv
res["bol_open_hours_before_start"] = f2.groupby("season")["h_bol_open"].median().round(1).to_dict()
res["bol_close_hours_before_start"] = f2.groupby("season")["h_bol_close"].median().round(2).to_dict()
res["bol_move_abs_logodds_median_by_season"] = f2.assign(
    m=np.abs(lg(f2["p_bol_close"]) - lg(f2["p_bol_open"]))).groupby("season")["m"].median().round(3).to_dict()

# ---------------------------------------------------------------- BetOnline total games, linked through OddsTrader eids (<= 2024 shape; coverage all)
os_ = pd.read_parquet(T / "odds_sources.parquet", columns=["match_id", "eid"])
os_["match_id"] = os_["match_id"].astype(str)
tg = pd.read_parquet(ROOT / "data/dump/odds/oddstrader/betonline_matches.parquet",
                     columns=["eid", "tg_open_line", "tg_close_line", "tg_close_uncertain", "tg_close_after_listed_min"])
f3 = f.merge(os_, on="match_id", how="left").merge(tg, on="eid", how="left")
f3["has_tg"] = np.isfinite(f3["tg_close_line"]) & ~f3["tg_close_uncertain"].fillna(True).astype(bool)
res["tg_close_coverage_by_season"] = f3.groupby("season")["has_tg"].mean().round(3).to_dict()
q = f3[(f3["season"] <= 2024) & f3["has_tg"] & np.isfinite(f3["p_bol"])].copy()
L = lg(q["p_bol"])
for bo in [3, 5]:
    qq = q[q["in_best_of"] == bo]
    LL = lg(qq["p_bol"])
    X = np.column_stack([np.ones(len(qq)), np.abs(LL), LL ** 2, (qq["tour"] == "wta").astype(float)])
    y = qq["tg_close_line"].to_numpy(float)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    res[f"tg_close_line_best_of_{bo}"] = {
        "n": int(len(qq)), "mean": round(float(y.mean()), 2), "sd": round(float(y.std()), 2),
        "r2_on_price_shape_and_tour": round(float(1 - r.var() / y.var()), 3),
        "residual_sd_games": round(float(r.std()), 2)}
q["tg_move"] = q["tg_close_line"] - q["tg_open_line"]
res["tg_move_abs_share_ge_1_game_le2024"] = float((np.abs(q["tg_move"]) >= 1).mean())

# ---------------------------------------------------------------- the clock: exact start coverage on frame matches
tm = pd.read_parquet(ROOT / "data/studies/match_timing/timing.parquet", columns=["match_id", "start", "exact"])
tm["match_id"] = tm["match_id"].astype(str)
f4 = mf[["match_id", "season"]].merge(tm, on="match_id", how="left")
res["exact_start_share_by_season"] = f4.assign(e=f4["start"].notna()).groupby("season")["e"].mean().round(3).to_dict()

# ---------------------------------------------------------------- attention proxy: OddsTrader books pricing the match (pre-start lines)
import pyarrow.parquet as pq  # schema only: the a_won column of this table is never loaded
cols = [c for c in pq.read_schema(T / "odds_sources.parquet").names if c.startswith("after_ot")]
osx = pd.read_parquet(T / "odds_sources.parquet", columns=["match_id", "season"] + cols)
nb = (osx[cols].le(30) & osx[cols].notna()).sum(axis=1)
res["oddstrader_books_pre_start_median_by_season"] = osx.assign(nb=nb).groupby("season")["nb"].median().to_dict()

(OUT / "descriptives.json").write_text(json.dumps(res, indent=1, default=str))
print(json.dumps({k: res[k] for k in ["orientation_check", "gate_bol_vs_pin_shading", "gate_bol_move",
                                      "tg_close_coverage_by_season", "tg_close_line_best_of_3",
                                      "tg_close_line_best_of_5", "exact_start_share_by_season"]}, indent=1,
                 default=str))

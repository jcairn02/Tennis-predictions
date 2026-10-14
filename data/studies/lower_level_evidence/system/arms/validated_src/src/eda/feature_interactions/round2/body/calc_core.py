"""Round 2, body brainstormer: each player's own sequence (seasons <= 2024, filtered at read time) and result-free kernels.

Never reads `won` or `a_won`. Uses the PRE-REBUILD Stage 0 and clock (panel.SOURCES), consistent with the model frame.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.eda.feature_interactions.history import parse_score  # noqa: E402
from src.eda.feature_interactions.panel import SOURCES  # noqa: E402

MCOLS = ["match_id", "tour", "year", "level", "qualifying", "round_order", "match_num", "surface", "indoor", "best_of",
         "tournament_id", "tournament_name", "tournament_date", "status", "score", "minutes"]
ITF_CODE = re.compile(r"^\d{4}-[MW]-[A-Z0-9]+-([A-Z]{3})-")


def load_long(max_year: int = 2024) -> pd.DataFrame:
    m = pq.read_table(str(SOURCES["stage0_matches"]), columns=MCOLS, filters=[("year", "<=", max_year)]).to_pandas()
    m["match_id"] = m["match_id"].astype(str)
    ids = m["match_id"].tolist()
    t = pq.read_table(str(SOURCES["timing"]), columns=["match_id", "es", "lf", "obs"],
                      filters=[("match_id", "in", ids)]).to_pandas()
    p = pq.read_table(str(SOURCES["stage0_players"]), columns=["match_id", "player_id", "side", "age", "country"],
                      filters=[("match_id", "in", ids)]).to_pandas()
    for d in (t, p):
        d["match_id"] = d["match_id"].astype(str)
    parsed = np.array([parse_score(s) for s in m["score"].to_numpy()], dtype=float)
    m["sets"], m["games"] = parsed[:, 0], parsed[:, 1]
    m = m.drop(columns=["score"]).merge(t, on="match_id", how="left")
    L = p.merge(m, on="match_id", how="inner")
    L["tday"] = (pd.to_datetime(L["tournament_date"]) - pd.Timestamp("1970-01-01")).dt.days.astype(float)
    L = L[L["status"].isin(["completed", "retired"])]          # played matches only
    L = L.sort_values(["player_id", "obs", "es", "tday", "round_order", "match_num"], kind="stable")
    return L.reset_index(drop=True)


def add_load(L: pd.DataFrame) -> pd.DataFrame:
    """Minutes where present, else games x the tour's median minutes per game (2010-2018, frozen)."""
    ok = (L["minutes"] > 0) & (L["games"] > 0) & (L["year"] <= 2018)
    mpg = (L.loc[ok, "minutes"] / L.loc[ok, "games"]).groupby(L.loc[ok, "tour"]).median()
    imp = L["games"] * L["tour"].map(mpg)
    L["load"] = L["minutes"].where(L["minutes"] > 0, imp).fillna(imp.median())
    return L


def kernels(L: pd.DataFrame, tau: float = 3.0, window: float = 14.0) -> pd.DataFrame:
    """Pre-match kernels from strictly earlier played matches of the same player:
    fat = log1p(sum L e^-d/tau); off = the off-site part; on_n = earlier matches at this tournament id;
    rest = days since the previous played match; prev_x = the previous on-site match's set excess (0 if none within
    3 days; NaN if it was a retirement); pastfat = mean pre-match fat over the player's matches of the last `window` days."""
    pid = L["player_id"].tolist(); t = L["obs"].tolist(); ld = L["load"].tolist()
    tid = L["tournament_id"].tolist(); bo = L["best_of"].tolist(); st = L["status"].tolist()
    sets = L["sets"].tolist()
    n = len(L)
    F = [0.0] * n; Fon = [0.0] * n; onn = [0] * n; rest = [math.nan] * n; px = [0.0] * n
    for i in range(1, n):
        if pid[i] != pid[i - 1]:
            continue
        d = max(t[i] - t[i - 1], 0.0)
        e = math.exp(-d / tau)
        F[i] = e * (F[i - 1] + ld[i - 1])
        rest[i] = d
        if tid[i] == tid[i - 1]:
            Fon[i] = e * (Fon[i - 1] + ld[i - 1])
            onn[i] = onn[i - 1] + 1
            if d <= 3:
                if st[i - 1] == "retired":
                    px[i] = math.nan
                else:
                    lo = (bo[i - 1] + 1) / 2
                    px[i] = min(max((sets[i - 1] - lo) / (bo[i - 1] - lo), 0.0), 1.0) if sets[i - 1] == sets[i - 1] else math.nan
    L["fat"] = np.log1p(np.array(F)); L["off"] = np.log1p(np.maximum(np.array(F) - np.array(Fon), 0.0))
    L["on_n"] = np.log1p(np.array(onn)); L["rest"] = np.array(rest); L["prev_x"] = np.array(px)
    # mean pre-match fat over the last `window` days (strictly earlier matches)
    pf = np.full(n, np.nan)
    fat = L["fat"].to_numpy(); obs = L["obs"].to_numpy()
    for idx in L.groupby("player_id", sort=False).indices.values():
        o = obs[idx]; c = np.concatenate([[0.0], np.cumsum(fat[idx])])
        lo = np.searchsorted(o, o - window, side="left"); ar = np.arange(len(idx))
        cnt = ar - lo
        with np.errstate(invalid="ignore", divide="ignore"):
            pf[idx] = np.where(cnt > 0, (c[ar] - c[lo]) / np.maximum(cnt, 1), np.nan)
    L["pastfat"] = pf
    return L


def itf_country(tid: pd.Series) -> pd.Series:
    return tid.astype(str).str.extract(ITF_CODE, expand=False)

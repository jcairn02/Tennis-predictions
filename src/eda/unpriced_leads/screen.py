"""Discovery harness of the unpriced-leads study (docs/studies/unpriced_leads/, 13 Oct 2026).

One candidate statistic at a time, against the close, era by era, on seasons <= 2024 only. The study reads **no outcome
from 1 Jan 2025 on**: every read of a result column goes through load_frame() or model_lens(), which filter
tournament_date < 2025-01-01 inside the parquet read and then assert it. Everything else here is outcome-free.

The close lens mirrors edge_anatomy's scan (src/eda/edge_anatomy/scan.py), so its readings of the model's own inputs
reproduce that study's 2013-24 numbers (selftest): a logistic regression without an intercept,
    logit P(A wins) = s_atp L 1[men] + s_wta L 1[women] + beta x
with L = logit of the frame's odds input (Pinnacle first, margin-free) and x the candidate, scaled by its root mean
square in the window (0 = no difference between the players; missing = 0, coverage reported). z is cluster-robust over
four-week blocks. + = the player higher on the statistic (A - B > 0) beats the close.
A symmetric (context) candidate s cannot move a symmetric forecast alone: it enters as a modifier of the price's slope,
x = L * (s - mean) / sd (+ = the price should be steeper where s is high).

Lenses (screen() runs all four; summarize() makes one row per candidate and tour):
    close       per era (2013-16, 2017-19, 2020-22, 2023-24) and tour (both, atp, wta); then the four eras pooled by
                inverse variance (z_pool, as edge_anatomy's z_2013_24) and the count of eras whose sign matches the pool
    model       the same fit with the current instance's own both-stages forecast (edge_anatomy's analysis.parquet,
                q_full) in place of the close, seasons 2020-2024: is the information already in the model?
    move        BetOnline's open-to-close move on the bet-timing frame, seasons 2018-2024, least squares
                logit(close) - logit(open) = a_tour logit(open) + b x: outcome-free; + = the line moves toward the
                player higher on the statistic before the close
    redundancy  R^2 of x on the model's 48 non-price, non-context inputs (pairs as A - B), 2013-2024, outcome-free

Player-level candidates are built from each player's own earlier matches with long_table() (the logic of
src/eda/feature_interactions/history.py, applied to the current Stage 0 and match clock, the tables the current instance
was built on) and aligned to the frame's sides with at_frame(). Safe by construction only if a value comes from strictly
earlier rows of the same player.

Run: ./python.sh src/eda/unpriced_leads/screen.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10"
FRAME = INSTANCE / "model_frame.parquet"
ANALYSIS = ROOT / "data" / "studies" / "edge_anatomy" / "analysis.parquet"
BET_TIMING = ROOT / "data" / "studies" / "bet_timing" / "frame.parquet"
STAGE0_M = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
STAGE0_P = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_match_players.parquet"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
OUT = ROOT / "data" / "studies" / "unpriced_leads"

DISCOVERY_END = pd.Timestamp("2025-01-01")      # no outcome from this day on is read by the study
ERAS = {"2013-16": (2013, 2016), "2017-19": (2017, 2019), "2020-22": (2020, 2022), "2023-24": (2023, 2024)}
TOURS = ("both", "atp", "wta")
BLOCK_ORIGIN = np.datetime64("2010-01-04")      # the corrected harness's Monday origin (tabpfn_thinking.common)
EPS = 1e-6
CONTEXT = ("tour", "surface", "level", "indoor", "best_of", "round")
PAIRS = {"surf_season": ("surf_season_a", "surf_season_b"), "surf_layoff": ("surf_layoff_a", "surf_layoff_b")}


# --------------------------------------------------------------------------------------------------------- basics

def lg(p) -> np.ndarray:
    return logit(np.clip(np.asarray(p, float), EPS, 1 - EPS))


def blocks(dates, width_days: int = 28) -> np.ndarray:
    days = (np.asarray(dates, dtype="datetime64[D]") - BLOCK_ORIGIN).astype(int)
    return days // width_days


def fit_offset(X: np.ndarray, y: np.ndarray, offset: np.ndarray, ridge: float = 1e-8,
               max_iter: int = 100, tol: float = 1e-10) -> tuple[np.ndarray, np.ndarray]:
    """Logistic regression without an intercept and with a fixed offset (edge_anatomy.stats.fit_offset)."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    k = X.shape[1]
    lam = np.full(k, ridge)
    b = np.zeros(k)
    for _ in range(max_iter):
        p = expit(offset + X @ b)
        g = X.T @ (y - p) - lam * b
        H = (X.T * (p * (1 - p))) @ X + np.diag(lam)
        step = np.linalg.solve(H, g)
        big = np.abs(step).max()
        if big > 4:
            step *= 4 / big
        b += step
        if np.abs(step).max() < tol:
            break
    p = expit(offset + X @ b)
    return b, (X.T * (p * (1 - p))) @ X + np.diag(lam)


def cluster_cov(X: np.ndarray, y: np.ndarray, offset: np.ndarray, b: np.ndarray, H: np.ndarray,
                clusters: np.ndarray) -> np.ndarray:
    p = expit(offset + X @ b)
    s = X * (np.asarray(y, float) - p)[:, None]
    labels, ix = np.unique(clusters, return_inverse=True)
    S = np.zeros((len(labels), X.shape[1]))
    np.add.at(S, ix, s)
    G = len(labels)
    if G < 2:
        return np.full((X.shape[1], X.shape[1]), np.nan)
    Hi = np.linalg.inv(H)
    return G / (G - 1) * Hi @ (S.T @ S) @ Hi


def ols_cluster(X: np.ndarray, y: np.ndarray, blk: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    XtXi = np.linalg.inv(X.T @ X)
    labels, ix = np.unique(blk, return_inverse=True)
    Sg = np.zeros((len(labels), X.shape[1]))
    np.add.at(Sg, ix, X * r[:, None])
    G = len(labels)
    V = G / (G - 1) * XtXi @ (Sg.T @ Sg) @ XtXi
    return b, np.sqrt(np.clip(np.diag(V), 0, None))


def bh(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float)
    out = np.full(len(p), np.nan)
    ok = np.isfinite(p)
    n = int(ok.sum())
    if n == 0:
        return out
    pv = p[ok]
    order = np.argsort(pv)
    q = pv[order] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    tmp = np.empty(n)
    tmp[order] = np.minimum(q, 1.0)
    out[ok] = tmp
    return out


def tour_slope_cols(tour: np.ndarray, L: np.ndarray) -> np.ndarray:
    atp = tour == "atp"
    cols = []
    if atp.any():
        cols.append(np.where(atp, L, 0.0))
    if (~atp).any():
        cols.append(np.where(~atp, L, 0.0))
    return np.column_stack(cols)


def rms_scale(x: np.ndarray) -> np.ndarray:
    x = np.where(np.isfinite(x), x, 0.0)
    r = float(np.sqrt(np.mean(x ** 2)))
    return x / r if r > 0 else x


# ------------------------------------------------------------------------------------------------------ the frame

def load_frame() -> pd.DataFrame:
    """The current instance's frame, seasons <= 2024 only (filtered in the read, then asserted), debut seasons out,
    with the result y, the close's log-odds L, four-week blocks, the model's inputs and the players' ids."""
    names = [d["name"] for d in json.loads((INSTANCE / "model_inputs.json").read_text(encoding="utf-8"))["inputs"]]
    cols = ["match_id", "tour", "season", "tournament_date", "debut_season", "p_mkt", "odds_input", "a_won"] + \
        [f"in_{n}" for n in names]
    # both filters inside the read: a match of season 2025 dated in late Dec 2024 (136 rows) belongs to Look A, so its
    # result is not loaded (added 13 Oct 2026 on S1's note; before, those rows were loaded but no lens used them)
    f = pd.read_parquet(FRAME, columns=cols, filters=[("tournament_date", "<", DISCOVERY_END), ("season", "<=", 2024)])
    if len(f) == 0 or f["tournament_date"].max() >= DISCOVERY_END or f["season"].max() > 2024:
        raise RuntimeError("an outcome from 2025 on was read")
    f["match_id"] = f["match_id"].astype(str)
    f = f[~f["debut_season"].astype(bool)].copy()
    for k, (a, b) in PAIRS.items():
        f[f"in_{k}"] = f[f"in_{a}"] - f[f"in_{b}"]
    f["y"] = f["a_won"].astype(float)
    f = f.drop(columns=["a_won"])
    f["L"] = lg(f["p_mkt"])
    f["block"] = blocks(f["tournament_date"].to_numpy(), 28)
    ids = pd.read_parquet(STAGE0_M, columns=["match_id", "player_a_id", "player_b_id"]).astype({"match_id": str})
    f = f.merge(ids, on="match_id", how="left", validate="one_to_one")
    return f.reset_index(drop=True)


def frame_outcome_free(min_season: int = 2013) -> pd.DataFrame:
    """Every season's frame rows without any result column (for coverage counts in 2025-26)."""
    f = pd.read_parquet(FRAME, columns=["match_id", "tour", "season", "tournament_date", "debut_season"])
    f["match_id"] = f["match_id"].astype(str)
    ids = pd.read_parquet(STAGE0_M, columns=["match_id", "player_a_id", "player_b_id"]).astype({"match_id": str})
    f = f.merge(ids, on="match_id", how="left", validate="one_to_one")
    return f[f["season"] >= min_season].reset_index(drop=True)


def diff_input_names() -> list[str]:
    """The model's 48 non-price, non-context inputs as tested (pairs as A - B; ios_points_short is not an input)."""
    names = [d["name"] for d in json.loads((INSTANCE / "model_inputs.json").read_text(encoding="utf-8"))["inputs"]]
    out = []
    for n in names:
        if n == "odds_logit" or n in CONTEXT:
            continue
        stem = n[:-2] if n.endswith(("_a", "_b")) and n[:-2] in PAIRS else n
        if stem not in out:
            out.append(stem)
    return out


# ------------------------------------------------------------------------------------------- the player history

SET_RE = re.compile(r"(\d+)-(\d+)(\(\d+\))?")


def parse_score(score) -> tuple[float, float, float, float]:
    """(sets, games, tiebreaks, sets won by the winner) from a winner-first score (feature_interactions.history)."""
    if not isinstance(score, str) or not score.strip():
        return (np.nan, np.nan, np.nan, np.nan)
    sets = games = tbs = won = 0
    for a, b, tb in SET_RE.findall(score):
        a, b = int(a), int(b)
        sets += 1
        games += a + b
        tbs += int(bool(tb) or {a, b} == {7, 6})
        won += int(a > b)
    if sets == 0:
        return (np.nan, np.nan, np.nan, np.nan)
    return (float(sets), float(games), float(tbs), float(won))


MATCH_COLS = ["match_id", "tour", "level", "qualifying", "round", "round_order", "match_num", "surface", "indoor",
              "best_of", "draw_size", "tournament_id", "tournament_name", "tournament_date", "status", "status_detail",
              "score", "minutes", "has_box"]


def long_table(player_cols: list[str] | None = None) -> pd.DataFrame:
    """Each player's own matches at every level, 2010-2026, one row per (match, player), in the player's own order:
    feature_interactions.history.long_table's logic on the current Stage 0 and match clock. Order: each event by its
    earliest best-estimate day `obs`, then the tournament date and id, then the round order and match number.
    Adds k (the player's match count so far), rest_days (best-estimate days since the previous match, >= 0) and
    rest_min (this match's earliest start minus the previous match's latest finish, a conservative lower bound).
    The current row's own facts (score, minutes, box score, won) are the result: a builder uses STRICTLY EARLIER rows
    of the same player (groupby player_id + shift(1) along k), never the current row's."""
    pcols = ["match_id", "player_id", "opponent_id", "side", "won", "rank", "rank_points", "seed", "entry", "age",
             "height", "hand", "country"]
    if player_cols:
        pcols += [c for c in player_cols if c not in pcols]
    m = pd.read_parquet(STAGE0_M, columns=MATCH_COLS)
    t = pd.read_parquet(TIMING, columns=["match_id", "es", "lf", "obs", "exact", "start"])
    p = pd.read_parquet(STAGE0_P, columns=pcols)
    for d in (m, t, p):
        d["match_id"] = d["match_id"].astype(str)
    parsed = np.array([parse_score(s) for s in m["score"].to_numpy()], dtype=float)
    m["sets"], m["games"], m["tiebreaks"], m["sets_won_by_winner"] = parsed.T
    m = m.merge(t, on="match_id", how="left", validate="one_to_one")
    L = p.merge(m, on="match_id", how="left", validate="many_to_one")
    L["won"] = L["won"].astype(bool)
    L["retired_self"] = (L["status"] == "retired") & ~L["won"]
    L["walkover"] = L["status"] == "walkover"
    L["played"] = ~L["walkover"]
    L["tday"] = (pd.to_datetime(L["tournament_date"]) - pd.Timestamp("1970-01-01")).dt.days.astype(float)
    L["ev_obs"] = L.groupby(["player_id", "tournament_id", "tday"])["obs"].transform("min")
    L = L.sort_values(["player_id", "ev_obs", "tday", "tournament_id", "round_order", "match_num"], kind="stable")
    L["k"] = L.groupby("player_id").cumcount()
    L["obs_mono"] = L.groupby("player_id")["obs"].cummax()
    g = L.groupby("player_id")
    L["rest_days"] = L["obs_mono"] - g["obs_mono"].shift(1)
    L["rest_min"] = L["es"] - g["lf"].shift(1)
    return L.reset_index(drop=True)


def at_frame(values: pd.DataFrame, col: str, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """A per-(match, player) column aligned to the frame's rows: (value for player A, value for player B), NaN where
    absent. values needs match_id, player_id and col."""
    v = values[["match_id", "player_id", col]].drop_duplicates(["match_id", "player_id"])
    v = v.astype({"match_id": str})
    key = v.set_index(["match_id", "player_id"])[col]
    a = key.reindex(pd.MultiIndex.from_arrays([frame["match_id"].astype(str), frame["player_a_id"]])).to_numpy(float)
    b = key.reindex(pd.MultiIndex.from_arrays([frame["match_id"].astype(str), frame["player_b_id"]])).to_numpy(float)
    return a, b


RESULT_COLS = ("won", "score", "sets", "games", "tiebreaks", "sets_won_by_winner", "minutes", "status",
               "status_detail", "retired_self", "walkover", "played")


def timing_probe(build_fn, L: pd.DataFrame, value_cols: list[str], cuts=("2016-06-01", "2019-03-01", "2022-09-01"),
                 seed: int = 20261013) -> dict:
    """Black-box timing check of a builder (CLAUDE.md "Feature timing"): build_fn(L) -> DataFrame with match_id,
    player_id and value_cols. For each cut day, every result and box-score field of the matches that may start on or
    after the cut (es >= cut) is scrambled (won flipped at random; scores, minutes, statuses and every numeric box-score
    column permuted among those rows), the builder is re-run, and the values at matches that surely finished before the
    cut (lf + 1 <= cut) are compared with the unscrambled build (a future leak changes them). So are the values at each
    player's first match on or after the cut whose every earlier row is untouched: its own facts are scrambled, so a
    builder that reads the current match's own result changes them (an own-match leak). A builder that uses only
    strictly earlier matches changes none of either. Returns, per cut, the rows compared and changed (must be 0)."""
    rng = np.random.default_rng(seed)
    base = build_fn(L).set_index(["match_id", "player_id"])[value_cols]
    box = [c for c in L.columns if c not in ("match_id", "player_id", "opponent_id", "side", "k", "tday", "es", "lf",
                                              "obs", "obs_mono", "ev_obs", "exact", "start", "rest_days", "rest_min",
                                              "rank", "rank_points", "seed", "entry", "age", "height", "hand",
                                              "country", "tour", "level", "qualifying", "round", "round_order",
                                              "match_num", "surface", "indoor", "best_of", "draw_size",
                                              "tournament_id", "tournament_name", "tournament_date", "has_box")
           and (c in RESULT_COLS or pd.api.types.is_numeric_dtype(L[c]))]
    out = {}
    for cut in cuts:
        c_day = (pd.Timestamp(cut) - pd.Timestamp("1970-01-01")).days
        after = (L["es"].to_numpy(float) >= c_day) | ~np.isfinite(L["es"].to_numpy(float))
        S = L.copy()
        idx = np.flatnonzero(after)
        for c in box:
            if c == "won":
                S.loc[S.index[idx], c] = rng.random(len(idx)) < 0.5
            else:
                S.loc[S.index[idx], c] = S[c].to_numpy()[rng.permutation(idx)]
        new = build_fn(S).set_index(["match_id", "player_id"])[value_cols]

        def changed(rows: pd.DataFrame) -> tuple[int, int]:
            keys = pd.MultiIndex.from_frame(rows[["match_id", "player_id"]].astype({"match_id": str}))
            a = base.reindex(keys).to_numpy(float)
            b = new.reindex(keys).to_numpy(float)
            same = (a == b) | (np.isnan(a) & np.isnan(b))
            return int(len(keys)), int((~same.all(axis=1)).sum())

        n_fut, c_fut = changed(L.loc[(L["lf"].to_numpy(float) + 1 <= c_day)])
        # each player's first scrambled row whose earlier rows (smaller k) are all unscrambled
        A = pd.DataFrame({"player_id": L["player_id"].to_numpy(), "k": L["k"].to_numpy(), "after": after})
        first_after = A[A["after"]].groupby("player_id")["k"].min()
        last_before_max = A[~A["after"]].groupby("player_id")["k"].max()
        ok_players = first_after.index[(first_after > last_before_max.reindex(first_after.index).fillna(-1)).to_numpy()]
        fa = first_after.loc[ok_players]
        sel = L.set_index(["player_id", "k"]).index.isin(pd.MultiIndex.from_arrays([fa.index, fa.to_numpy()]))
        n_own, c_own = changed(L.loc[sel])
        out[cut] = {"future_rows_compared": n_fut, "future_rows_changed": c_fut,
                    "own_rows_compared": n_own, "own_rows_changed": c_own, "columns_scrambled": len(box)}
    return out


# --------------------------------------------------------------------------------------------------- the lenses

def _fit_one(g: pd.DataFrame, x: np.ndarray, base: str, curv: bool = False) -> dict:
    """One fit beyond the base price: per-tour slopes on the base's log-odds, plus (curv) per-tour curvature terms
    on L * |L|, so a candidate cannot borrow the price's favourite-longshot shape (added 13 Oct 2026, after the market
    builder's curvature reading; the default keeps the edge_anatomy-identical base)."""
    y, blk = g["y"].to_numpy(float), g["block"].to_numpy()
    Lb = g[base].to_numpy(float)
    B = tour_slope_cols(g["tour"].to_numpy(), Lb)
    if curv:
        B = np.column_stack([B, tour_slope_cols(g["tour"].to_numpy(), Lb * np.abs(Lb))])
    xs = rms_scale(x)
    Z = np.column_stack([B, xs])
    zero = np.zeros(len(y))
    b1, H1 = fit_offset(Z, y, zero)
    V = cluster_cov(Z, y, zero, b1, H1, blk)
    se = float(np.sqrt(V[-1, -1])) if np.isfinite(V[-1, -1]) and V[-1, -1] > 0 else np.nan
    return {"beta": float(b1[-1]), "se": se, "z": float(b1[-1] / se) if se and np.isfinite(se) else np.nan,
            "n": int(len(y)), "present": float(np.mean(np.isfinite(x)))}


def candidate_x(frame: pd.DataFrame, x, kind: str, base: str = "L") -> np.ndarray:
    """The tested column: x itself for a difference (A - B), L * standardised s for a context candidate."""
    x = np.asarray(x, float)
    if kind == "diff":
        return x
    if kind == "context":
        ok = np.isfinite(x)
        mu, sd = (np.nanmean(x[ok]), np.nanstd(x[ok])) if ok.any() else (0.0, 1.0)
        s = np.where(ok, (x - mu) / (sd if sd > 0 else 1.0), np.nan)
        return frame[base].to_numpy(float) * s
    raise ValueError(f"unknown kind {kind}")


def close_lens(frame: pd.DataFrame, x, name: str, kind: str = "diff", base: str = "L",
               curv: bool = False) -> pd.DataFrame:
    """The close lens. `base` names another log-odds column of `frame` to test against instead of the odds input
    (e.g. BetOnline's own close, for a statistic built from BetOnline's line); rows where it is missing are left out,
    and the era rows report how many remain (n). `curv` adds per-tour curvature terms (L * |L|) to the base; the lens
    label then ends in "+curv"."""
    xx = candidate_x(frame, x, kind, base=base)
    okb = np.isfinite(frame[base].to_numpy(float))
    rows = []
    for era, (a, b) in ERAS.items():
        for tour in TOURS:
            m = frame["season"].between(a, b).to_numpy() & okb
            if tour != "both":
                m = m & (frame["tour"] == tour).to_numpy()
            if m.sum() < 200:
                continue
            g = frame[m]
            r = _fit_one(g, xx[m], base, curv=curv)
            lab = ("close" if base == "L" else f"close[{base}]") + ("+curv" if curv else "")
            rows.append({"name": name, "kind": kind, "lens": lab, "era": era, "tour": tour, **r})
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    pooled = []
    for tour, h in out.groupby("tour"):
        h = h[np.isfinite(h["se"]) & (h["se"] > 0)]
        if h.empty:
            continue
        w = 1 / h["se"] ** 2
        bp = float((w * h["beta"]).sum() / w.sum())
        sp = float(np.sqrt(1 / w.sum()))
        pooled.append({"name": name, "kind": kind, "lens": out["lens"].iloc[0], "era": "2013-24 pooled", "tour": tour,
                       "beta": bp, "se": sp, "z": bp / sp, "n": int(h["n"].sum()),
                       "eras_same_sign": int((np.sign(h["beta"]) == np.sign(bp)).sum()),
                       "eras_abs_z_ge_2": int((h["z"].abs() >= 2).sum()),
                       "present": float((h["present"] * h["n"]).sum() / h["n"].sum())})
    return pd.concat([out, pd.DataFrame(pooled)], ignore_index=True)


_MODEL_CACHE: dict = {}


def _model_frame() -> pd.DataFrame:
    if "m" not in _MODEL_CACHE:
        a = pd.read_parquet(ANALYSIS, columns=["match_id", "tour", "season", "tournament_date", "debut", "y", "q_full"],
                            filters=[("tournament_date", "<", DISCOVERY_END), ("season", "<=", 2024)])
        if len(a) and (a["tournament_date"].max() >= DISCOVERY_END or a["season"].max() > 2024):
            raise RuntimeError("an outcome from 2025 on was read (model lens)")
        a = a[(a["season"].between(2020, 2024)) & ~a["debut"].astype(bool) & np.isfinite(a["q_full"])].copy()
        a["match_id"] = a["match_id"].astype(str)
        a["Lm"] = lg(a["q_full"])
        a["block"] = blocks(a["tournament_date"].to_numpy(), 28)
        _MODEL_CACHE["m"] = a.reset_index(drop=True)
    return _MODEL_CACHE["m"]


def model_lens(frame: pd.DataFrame, x, name: str, kind: str = "diff") -> pd.DataFrame:
    """Beyond the current instance's own both-stages forecast, 2020-2024 (its out-of-sample seasons <= 2024)."""
    a = _model_frame()
    s = pd.Series(np.asarray(x, float), index=frame["match_id"].astype(str).to_numpy())
    s = s[~s.index.duplicated()]
    xa = s.reindex(a["match_id"]).to_numpy(float)
    if kind == "context":
        ok = np.isfinite(xa)
        mu, sd = (np.nanmean(xa[ok]), np.nanstd(xa[ok])) if ok.any() else (0.0, 1.0)
        xa = a["Lm"].to_numpy(float) * np.where(ok, (xa - mu) / (sd if sd > 0 else 1.0), np.nan)
    rows = []
    for tour in TOURS:
        m = np.ones(len(a), bool) if tour == "both" else (a["tour"] == tour).to_numpy()
        r = _fit_one(a[m], xa[m], "Lm")
        rows.append({"name": name, "kind": kind, "lens": "model", "era": "2020-24", "tour": tour, **r})
    return pd.DataFrame(rows)


_MOVE_CACHE: dict = {}


def _move_frame() -> pd.DataFrame:
    if "m" not in _MOVE_CACHE:
        bt = pd.read_parquet(BET_TIMING, columns=["match_id", "tour", "season", "tournament_date", "debut_season",
                                                  "p_bol_open", "p_bol_close", "ok_bol_open", "ok_bol_close",
                                                  "known_bol_open"])
        bt = bt[(bt["season"] <= 2024) & ~bt["debut_season"].astype(bool)].copy()
        keep = bt["ok_bol_open"].astype(bool) & bt["ok_bol_close"].astype(bool) & \
            bt["known_bol_open"].astype(bool) & np.isfinite(bt["p_bol_open"]) & np.isfinite(bt["p_bol_close"])
        bt = bt[keep.to_numpy()].copy()
        bt["match_id"] = bt["match_id"].astype(str)
        bt["Lo"] = lg(bt["p_bol_open"])
        bt["move"] = lg(bt["p_bol_close"]) - bt["Lo"]
        bt["block"] = blocks(bt["tournament_date"].to_numpy(), 28)
        _MOVE_CACHE["m"] = bt.reset_index(drop=True)
    return _MOVE_CACHE["m"]


def move_lens(frame: pd.DataFrame, x, name: str, kind: str = "diff") -> pd.DataFrame:
    """BetOnline's open-to-close move on the statistic, 2018-2024 (outcome-free)."""
    bt = _move_frame()
    s = pd.Series(np.asarray(x, float), index=frame["match_id"].astype(str).to_numpy())
    s = s[~s.index.duplicated()]
    xb = s.reindex(bt["match_id"]).to_numpy(float)
    if kind == "context":
        ok = np.isfinite(xb)
        mu, sd = (np.nanmean(xb[ok]), np.nanstd(xb[ok])) if ok.any() else (0.0, 1.0)
        xb = bt["Lo"].to_numpy(float) * np.where(ok, (xb - mu) / (sd if sd > 0 else 1.0), np.nan)
    rows = []
    for tour in TOURS:
        m = np.ones(len(bt), bool) if tour == "both" else (bt["tour"] == tour).to_numpy()
        g = bt[m]
        xs = rms_scale(xb[m])
        if not np.any(xs != 0):          # the candidate is absent for this tour: no reading (S1's note)
            rows.append({"name": name, "kind": kind, "lens": "move", "era": "2018-24", "tour": tour,
                         "beta": np.nan, "se": np.nan, "z": np.nan, "n": int(len(g)), "present": 0.0})
            continue
        X = np.column_stack([tour_slope_cols(g["tour"].to_numpy(), g["Lo"].to_numpy(float)), xs])
        b, se = ols_cluster(X, g["move"].to_numpy(float), g["block"].to_numpy())
        rows.append({"name": name, "kind": kind, "lens": "move", "era": "2018-24", "tour": tour,
                     "beta": float(b[-1]), "se": float(se[-1]), "z": float(b[-1] / se[-1]) if se[-1] > 0 else np.nan,
                     "n": int(len(g)), "present": float(np.mean(np.isfinite(xb[m])))})
    return pd.DataFrame(rows)


def redundancy(frame: pd.DataFrame, x, kind: str = "diff") -> dict:
    """R^2 of the candidate on the model's 48 non-price, non-context inputs (A - B), rows where it is present, by
    tour (outcome-free; context candidates are tested as L * s against the inputs times L, so the same R^2 reads how
    much of the slope modifier the inputs' own slope modifiers span)."""
    names = diff_input_names()
    out = {}
    xx = np.asarray(x, float)
    for tour in TOURS:
        m = np.isfinite(xx)
        if tour != "both":
            m = m & (frame["tour"] == tour).to_numpy()
        if m.sum() < 200:
            out[tour] = np.nan
            continue
        X = frame.loc[m, [f"in_{n}" for n in names]].to_numpy(float)
        X = np.where(np.isfinite(X), X, 0.0)
        if kind == "context":
            X = X * frame.loc[m, "L"].to_numpy(float)[:, None]
            yv = candidate_x(frame, xx, "context")[m]
        else:
            yv = xx[m]
        X = np.column_stack([np.ones(len(yv)), X])
        b, *_ = np.linalg.lstsq(X, yv, rcond=None)
        r = yv - X @ b
        out[tour] = float(1 - r.var() / yv.var()) if yv.var() > 0 else np.nan
    return out


def orthogonal_part(frame: pd.DataFrame, x, coef: dict | None = None) -> tuple[np.ndarray, dict]:
    """The part of a difference candidate the model's own inputs do not span: x minus its least-squares projection on
    the 48 non-price, non-context inputs (A - B; missing inputs 0), without an intercept (so it stays antisymmetric:
    it flips sign when A and B swap), fitted by tour on the rows where x is present. Outcome-free. Pass `coef` (as
    returned) to apply a frozen projection to other rows, e.g. 2025-26 at registration time. Returns (residual aligned
    to frame, NaN where x is NaN; coefficients by tour)."""
    names = diff_input_names()
    xx = np.asarray(x, float)
    res = np.full(len(xx), np.nan)
    fitted = {} if coef is None else coef
    for tour in ("atp", "wta"):
        m = (frame["tour"] == tour).to_numpy() & np.isfinite(xx)
        if m.sum() == 0:
            continue
        X = frame.loc[m, [f"in_{n}" for n in names]].to_numpy(float)
        X = np.where(np.isfinite(X), X, 0.0)
        if coef is None:
            b, *_ = np.linalg.lstsq(X, xx[m], rcond=None)
            fitted[tour] = {"inputs": names, "b": b.tolist()}
        else:
            if list(coef[tour]["inputs"]) != list(names):     # the red team's M1: frozen coefficients, same inputs
                raise RuntimeError("the frozen projection's inputs differ from the template's input list")
            b = np.asarray(coef[tour]["b"], float)
        res[m] = xx[m] - X @ b
    return res, fitted


def screen(frame: pd.DataFrame, x, name: str, kind: str = "diff", lenses=("close", "model", "move"),
           base: str = "L", curv: bool = False) -> pd.DataFrame:
    """Every lens for one candidate (x aligned to frame's rows). Returns the long table of readings. `base` changes
    the close lens's price column (default: the frame's odds input), `curv` adds the curvature terms to its base;
    summarize(long, lens=...) reads the other labels ("close+curv", "close[<base>]")."""
    parts = []
    if "close" in lenses:
        parts.append(close_lens(frame, x, name, kind, base=base, curv=curv))
    if "model" in lenses:
        parts.append(model_lens(frame, x, name, kind))
    if "move" in lenses:
        parts.append(move_lens(frame, x, name, kind))
    out = pd.concat(parts, ignore_index=True)
    r2 = redundancy(frame, x, kind)
    out["r2_inputs"] = out["tour"].map(r2)
    return out


def summarize(long: pd.DataFrame, lens: str = "close") -> pd.DataFrame:
    """One row per candidate and tour: the pooled close reading (lens label `lens`), its eras, the model and move
    readings, the R^2; BH q over all rows of the table on the pooled close z (two-sided normal p)."""
    from scipy.stats import norm
    rows = []
    for (name, tour), h in long.groupby(["name", "tour"], sort=False):
        r = {"name": name, "tour": tour, "kind": h["kind"].iloc[0]}
        pool = h[(h["lens"] == lens) & (h["era"] == "2013-24 pooled")]
        if len(pool):
            p = pool.iloc[0]
            r.update({"beta_pool": p["beta"], "z_pool": p["z"], "eras_same_sign": p.get("eras_same_sign"),
                      "eras_abs_z_ge_2": p.get("eras_abs_z_ge_2"), "present_2013_24": p.get("present")})
        for era in ERAS:
            e = h[(h["lens"] == lens) & (h["era"] == era)]
            r[f"z_{era}"] = float(e["z"].iloc[0]) if len(e) else np.nan
        mo = h[h["lens"] == "model"]
        r["z_model_2020_24"] = float(mo["z"].iloc[0]) if len(mo) else np.nan
        mv = h[h["lens"] == "move"]
        r["z_move_2018_24"] = float(mv["z"].iloc[0]) if len(mv) else np.nan
        r["r2_inputs"] = float(h["r2_inputs"].iloc[0])
        rows.append(r)
    s = pd.DataFrame(rows)
    if "z_pool" in s:
        s["p_pool"] = 2 * norm.sf(np.abs(s["z_pool"]))
        s["q_pool"] = bh(s["p_pool"].to_numpy())
    return s


def coverage_2025_26(frame_all: pd.DataFrame, x_all) -> dict:
    """Outcome-free: the share of 2025-26 frame rows (and of 2013-24) where the candidate is present, by tour."""
    x = np.asarray(x_all, float)
    out = {}
    for tour in ("atp", "wta"):
        for lab, (a, b) in (("2013_24", (2013, 2024)), ("2025_26", (2025, 2026))):
            m = (frame_all["tour"] == tour).to_numpy() & frame_all["season"].between(a, b).to_numpy()
            out[f"{tour}_{lab}"] = float(np.mean(np.isfinite(x[m]))) if m.any() else np.nan
    return out


# ----------------------------------------------------------------------------------------------------- selftest

def selftest() -> dict:
    """(1) sides: the frame's age input equals Stage 0's age of player A minus player B; (2) the close lens reproduces
    edge_anatomy's pooled 2013-24 z for the model's own inputs (its scan_learning.csv, column z_2013_24 only);
    (3) a placebo: 200 random columns give z close to N(0, 1)."""
    f = load_frame()
    res = {"frame_rows_le_2024": int(len(f)), "last_date": str(f["tournament_date"].max().date())}
    p = pd.read_parquet(STAGE0_P, columns=["match_id", "player_id", "age"]).astype({"match_id": str})
    a, b = at_frame(p, "age", f)
    d = a - b
    ok = np.isfinite(d) & np.isfinite(f["in_age"].to_numpy(float))
    res["sides_age_corr"] = float(np.corrcoef(d[ok], f["in_age"].to_numpy(float)[ok])[0, 1])
    res["sides_age_max_abs_diff"] = float(np.nanmax(np.abs(d[ok] - f["in_age"].to_numpy(float)[ok])))
    res["sides_rows_checked"] = int(ok.sum())
    ref = pd.read_csv(ROOT / "data" / "studies" / "edge_anatomy" / "scan_learning.csv",
                      usecols=["tour", "input", "z_2013_24"])
    checks = []
    for inp in ("sets_14d", "age", "iosO_hold", "form_bp_saved", "surf_layoff", "elo_overall"):
        x = f[f"in_{inp}"].to_numpy(float)
        cl = close_lens(f, x, inp)
        for tour in TOURS:
            mine = float(cl[(cl["tour"] == tour) & (cl["era"] == "2013-24 pooled")]["z"].iloc[0])
            theirs = ref[(ref["tour"] == tour) & (ref["input"] == inp)]["z_2013_24"]
            checks.append({"input": inp, "tour": tour, "z_here": mine,
                           "z_edge_anatomy": float(theirs.iloc[0]) if len(theirs) else np.nan})
    c = pd.DataFrame(checks)
    res["repro_max_abs_diff_z"] = float((c["z_here"] - c["z_edge_anatomy"]).abs().max())
    res["repro_table"] = c.round(4).to_dict(orient="records")
    rng = np.random.default_rng(20261013)
    zs = []
    for _ in range(200):
        x = rng.standard_normal(len(f))
        cl = close_lens(f, x, "placebo")
        zs.append(float(cl[(cl["tour"] == "both") & (cl["era"] == "2013-24 pooled")]["z"].iloc[0]))
    zs = np.array(zs)
    res["placebo_z_mean"] = float(zs.mean())
    res["placebo_z_sd"] = float(zs.std())
    res["placebo_share_abs_z_ge_2"] = float(np.mean(np.abs(zs) >= 2))
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        res = selftest()
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "harness_selftest.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(json.dumps({k: v for k, v in res.items() if k != "repro_table"}, indent=1))
        print(pd.DataFrame(res["repro_table"]).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

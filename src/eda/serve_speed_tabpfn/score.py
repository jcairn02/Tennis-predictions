"""The scorer of the serve-speed study (audit C6): the expanding-window test on 2024, 2025 and 2026.

Every forecast scored for season Y comes from a fit trained on the model frame's matches of 2013 .. Y - 1 (local_fits.py).

Modes:
    --check       result-free: the populations and their SHA-256, the counts, the input and code hashes, the probe
                  records, which fits exist, the reuse checks. Writes data/studies/serve_speed_tabpfn/check.json.
                  Never reads a match result.
    --synthetic   the verifier's mode: outcomes are DRAWN from a planted model (the calibrated base plus beta * spd_f),
                  never read; P2, S0, S10 and P2's interval variants are computed as in --run, over replicates.
                  Writes data/studies/serve_speed_tabpfn/synthetic/<tag>.json. Never selects a_won.
    --run         ONCE, after the pre-registration is hashed (docs/studies/serve_speed_tabpfn/preregistration.md and
                  its .sha256, CRLF normalised to LF; the recorded code, input and population hashes must equal the
                  current ones). The only path that reads a_won. Before it reads any result it refuses: a missing or
                  failed reuse check, a stale speed-arm fit, ANY missing needed fit, and fits that differ from a
                  recorded FORECASTS_SHA256. Writes results.json and results.csv; refuses to overwrite them.
    --hash-prereg writes preregistration.sha256 (SHA-256 with CRLF normalised to LF), the lead's freeze step.

Forecasts. Symmetrised P(A wins), averaged over the stated seeds; eta = logit of the seed mean.
Calibration (decided). One slope per tour on eta, no intercept, fitted for season Y on the arm's own out-of-sample
    seasons 2019 .. Y - 1 from the seeds 0-3 mean (debut seasons out), applied to the season-Y seed mean. The same for
    every arm and the base.
P2 (primary). G = 1000 * mean[LL(q_base) - LL(q_A1)] over men's model-frame matches of 2024-2026, debut seasons out.
    POSITIVE = A1 (spd) HAS THE LOWER LOG LOSS (BETTER). SE^2 = SE_block^2 + v_A1 + v_base: SE_block clustered on four-week
    blocks of tournament dates (tabpfn_thinking.common.paired_interval's formula), v_arm = the variance over seeds k of
    the mean log loss of seed k's forecast (calibrated with the arm's seed-mean slope), divided by K (the surface-IOS
    seed_var convention). t on G - 1 degrees of freedom, 95% two-sided. Seeds 0-15 on both sides.
Secondaries S0-S14 (descriptive), the decision table and the multiplicity count: see SECONDARIES below and
docs/studies/serve_speed_tabpfn/preregistration.md.
Stale fits. Every speed-arm fit (spd, spd_raw, spd_all, spd_noodds) must store the SHA-256 of the current feature file;
--check lists mismatches, the loader refuses them and --run refuses to start (the file itself must equal the frozen
FEATURE_SHA256).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.special import expit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402

SEEDS16, SEEDS8 = tuple(range(16)), tuple(range(8))
TEST = C.TEST_SEASONS
HIST = tuple(range(C.CALIB_FROM, 2027))       # seasons whose forecasts the scorer reads: 2019-2026
MIN_CAL_ROWS = 1000
LABEL = {"model": "the base (58 inputs)", "spd": "A1 spd", "spd_raw": "A2 spd_raw", "spd_all": "A3 spd_all",
         "spd_noodds": "A1's no-odds twin spd_noodds", "model_noodds": "the no-odds base model_noodds"}
DIAGNOSTICS = ("k28_a", "k28_b", "last_age_a", "last_age_b", "id_conflict")
PREREG_KEYS = ("SCORER_CODE_SHA256", "MODEL_FRAME_SHA256", "FEATURE_SHA256", "REGISTRY_SHA256", "EARLY_SHA256",
               "POPULATION_SHA256")


@dataclass(frozen=True)
class Comparison:
    """One paired log-loss comparison. ONE seed set, used on both sides (audit Q5: identical seed sets)."""
    cid: str
    base: str
    arm: str
    seeds: tuple
    population: str
    seasons: tuple
    metric: str = "calibrated"           # or "raw"
    block: str = "td"                    # "early": both fed Polymarket's 24-hour price, calibrated with the td slopes
    loss: str = "ll"                     # "ll" (log loss, mLL) or "brier" (1000 x Brier score)

    @property
    def direction(self) -> str:
        what = "log loss" if self.loss == "ll" else "Brier score"
        return f"positive = {LABEL[self.arm]} has the lower {what} (better) than {LABEL[self.base]}"

    @property
    def unit(self) -> str:
        return UNIT[self.loss]


UNIT = {"ll": "mLL", "brier": "1000 x Brier"}
PRIMARY = Comparison("P2", "model", "spd", SEEDS16, "men", TEST)
S14 = Comparison("S14", "model", "spd", SEEDS16, "men", TEST, loss="brier")     # P2 on the Brier score
COMPARISONS = [PRIMARY]
COMPARISONS += [Comparison(f"S1_{y}", "model", "spd", SEEDS16, "men", (y,)) for y in TEST]
COMPARISONS += [Comparison("S2", "model", "spd", SEEDS16, "men", (2025, 2026))]
COMPARISONS += [Comparison(f"S3_{g}", "model", "spd", SEEDS16, f"men_recency_{g}", TEST) for g in ("both", "one",
                                                                                                   "neither")]
COMPARISONS += [Comparison("S4_A1_women", "model", "spd", SEEDS16, "women", TEST),
                Comparison("S4_A1_both", "model", "spd", SEEDS16, "both", TEST),
                Comparison("S4_A3_women", "model", "spd_all", SEEDS8, "women", TEST),
                Comparison("S4_A3_women_no_conflict", "model", "spd_all", SEEDS8, "women_no_conflict", TEST)]
COMPARISONS += [Comparison("S5", "model_noodds", "spd_noodds", SEEDS8, "men", TEST)]
COMPARISONS += [Comparison("S6_early_all", "model", "spd", SEEDS16, "men_early_all", (2025, 2026), block="early"),
                Comparison("S6_early_clean", "model", "spd", SEEDS16, "men_early_clean", (2025, 2026), block="early")]
COMPARISONS += [Comparison("S7", "model", "spd", SEEDS16, "men", TEST, metric="raw")]
COMPARISONS += [Comparison("S8_A2", "model", "spd_raw", SEEDS8, "men", TEST),
                Comparison("S8_A3", "model", "spd_all", SEEDS8, "men", TEST),
                Comparison("S8_A1_vs_A2", "spd_raw", "spd", SEEDS8, "men", TEST),
                Comparison("S8_A3_vs_A1", "spd", "spd_all", SEEDS8, "men", TEST)]

SECONDARIES = {
    "S0": "information: logit P = sum_season a eta_B + c eta_B^3 + b spd_f, men 2024-2026, eta_B the base's raw 16-seed "
          "log-odds; b in log-odds per unit of spd_f (one s_f = 2.224 km/h); positive = the man whose speed state is "
          "higher wins more often than the base says (union-clustered variance, t on G - 1)",
    "S1": "P2 by season", "S2": "P2 on 2025-2026 (blind for the new coverage)",
    "S3": "P2 by recency: both / one / neither side with a timed row within 28 days (neither: a harm check, ~0)",
    "S4": "A1 against the base on women and on both tours; A3 against the base on women, with and without the "
          "id_conflict matches",
    "S5": "spd_noodds against model_noodds, seeds 0-7, men 2024-2026, each calibrated on its own 2019 .. Y - 1",
    "S6": "Polymarket 24 hours out, men 2025-2026: (a) A1 against the base, both fed the early price and calibrated with "
          "their close slopes; (b) the 24 h -> 30 min price move: with the odds, M on [eta_B[0-7],early - logit p24, "
          "eta_B[0-7],early, eta_A1[0-15],early - eta_B[8-15],early], the last slope (verifier V1); without, M on "
          "[eta_Bno, eta_Ano - eta_Bno], the second slope; positive = the price moved toward A1's view",
    "S7": "P2 on raw (uncalibrated) forecasts",
    "S8": "A2 and A3 against the base; A1 against A2; A3 against A1 on men (dilution); seeds 0-7; positive = the "
          "first-named arm (A2 / A3 / A1 / A3) better",
    "S9": "the walk-forward nudge q = s eta_B + b_Y spd_f (fitted on 2019 .. Y - 1), shrunk (tau 0.05) and not, "
          "against the calibrated base",
    "S10": "capture a = sum(dev z) / sum(z^2), dev = eta_A1 - eta_B (raw 16-seed means), log-odds per unit of spd_f; "
           "also a_cal (each season's dev times s_Y, A1's men's calibration slope); a / b_S0 and a_cal / b_S0 when S0's "
           "interval excludes 0",
    "S11": "P2 with a block-only interval and with a calendar-week interval",
    "S12": "the registered statistic's replication: S0's model with z = spd_raw (NaN -> 0), men 2025-2026; b in "
           "log-odds per unit of spd_raw (5.998 km/h of x_raw, the published beta's unit)",
    "S13": "CONTEXT, not a test of the speed column and not counted in the multiplicity: the calibrated base (seeds "
           "0-15) against the closing price p_mkt recalibrated the decided way (one slope per tour on logit p_mkt, no "
           "intercept, fitted for Y on 2019 .. Y - 1, debut out), P2's population, mLL, positive = the base better, "
           "block-only interval; plus P2 / S13, a descriptive point value (the speed gain as a share of the base's "
           "edge over the close)",
    "S14": "P2 on the Brier score: 1000 x mean[Brier_base - Brier_A1], positive = A1 better, P2's interval convention "
           "(block SE plus the empirical seed variance on Brier)",
}


# ------------------------------------------------------------------------------------------------
# Inputs (no outcome)

def frame_index(P: C.Paths) -> F.FrameIndex:
    f = pd.read_parquet(P.model_frame, columns=["match_id", "season"])
    f["match_id"] = f["match_id"].astype(str)
    return F.FrameIndex(f)


def feature_columns(P: C.Paths) -> list[str]:
    names = set(pq.read_schema(P.feature_file).names)
    want = ["match_id", "spd_f", "spd_f_all", "spd_raw"]
    missing = [c for c in want if c not in names]
    if missing:
        raise RuntimeError(f"feature file lacks {missing}")
    return want + [c for c in DIAGNOSTICS if c in names]


def population(P: C.Paths = C.DEFAULT) -> pd.DataFrame:
    """Every model-frame match of 2019-2026 by match id, with what the scorer needs except the result."""
    f = pd.read_parquet(P.model_frame, columns=["match_id", "tour", "season", "tournament_date", "debut_season",
                                                "p_mkt"])
    f["match_id"] = f["match_id"].astype(str)
    f = f[f["season"].between(C.CALIB_FROM, 2026)].reset_index(drop=True)
    f["debut"] = f["debut_season"].astype(bool)
    f["block"] = C.blocks(f["tournament_date"].to_numpy(), 28)
    f["week"] = C.blocks(f["tournament_date"].to_numpy(), 7)
    s0 = pd.read_parquet(P.stage0_pre, columns=["match_id", "player_a_id", "player_b_id"])
    s0["match_id"] = s0["match_id"].astype(str)
    f = f.merge(s0, on="match_id", how="left", validate="one_to_one")
    ft = pd.read_parquet(P.feature_file, columns=feature_columns(P))
    ft["match_id"] = ft["match_id"].astype(str)
    f = f.merge(ft, on="match_id", how="left", validate="one_to_one")
    if f["spd_f"].isna().any() or f["spd_f_all"].isna().any():
        raise RuntimeError("spd_f / spd_f_all must exist (never NaN) for every frame match")
    ep = pd.read_parquet(P.early, columns=["match_id", "has_early", "clean", "all_early", "p_early_a", "p_close_a"])
    ep["match_id"] = ep["match_id"].astype(str)
    f = f.merge(ep, on="match_id", how="left", validate="one_to_one")
    for c in ("has_early", "clean", "all_early"):
        f[c] = f[c].fillna(False).astype(bool)
    f["recency"] = recency(f)
    f["id_conflict"] = f["id_conflict"].fillna(False).astype(bool) if "id_conflict" in f else False
    return f.set_index("match_id")


def recency(f: pd.DataFrame) -> pd.Series:
    """both / one / neither side with a timed row within 28 days of the match (the build's diagnostics: k28 counts, or
    the age of the last row); NaN when the feature file carries neither."""
    if {"k28_a", "k28_b"} <= set(f.columns):
        a, b = f["k28_a"].fillna(0).to_numpy() > 0, f["k28_b"].fillna(0).to_numpy() > 0
    elif {"last_age_a", "last_age_b"} <= set(f.columns):
        a, b = f["last_age_a"].to_numpy(float) <= 28, f["last_age_b"].to_numpy(float) <= 28
    else:
        return pd.Series(np.nan, index=f.index, dtype=object)
    return pd.Series(np.select([a & b, a ^ b], ["both", "one"], "neither"), index=f.index)


def labels(P: C.Paths = C.DEFAULT) -> pd.Series:
    """THE ONLY READER OF MATCH RESULTS (a_won), used by --run alone."""
    f = pd.read_parquet(P.model_frame, columns=["match_id", "season", "a_won"])
    f = f[f["season"].between(C.CALIB_FROM, 2026)]
    return pd.Series(f["a_won"].astype(float).to_numpy(), index=f["match_id"].astype(str).to_numpy())


def ids_hash(ids) -> str:
    return hashlib.sha256("\n".join(sorted(map(str, ids))).encode()).hexdigest()


def population_ids(info: pd.DataFrame, pop: str, seasons) -> pd.Index:
    m = info["season"].isin(list(seasons)).to_numpy() & ~info["debut"].to_numpy(bool)
    tour = info["tour"].to_numpy()
    if pop.startswith("men"):
        m &= tour == "atp"
    elif pop.startswith("women"):
        m &= tour == "wta"
    elif pop != "both":
        raise KeyError(pop)
    if pop.startswith("men_recency_"):
        m &= (info["recency"] == pop.rsplit("_", 1)[1]).to_numpy()
    if pop == "women_no_conflict":
        m &= ~info["id_conflict"].to_numpy(bool)
    if pop.startswith("men_early_"):
        priced = np.isfinite(info["p_early_a"].to_numpy(float)) & np.isfinite(info["p_close_a"].to_numpy(float))
        m &= info["has_early"].to_numpy(bool) & priced & info["clean" if pop.endswith("clean") else "all_early"].to_numpy(bool)
    return info.index[m]


# ------------------------------------------------------------------------------------------------
# Forecasts

class Bank:
    """Saved forecasts by (arm, season, seed), loaded once; synthetic tables can be injected (--synthetic)."""

    def __init__(self, P: C.Paths, fx: F.FrameIndex, require_checks: bool = True):
        self.P, self.fx, self.require_checks = P, fx, require_checks
        self.cache: dict = {}
        self.injected: dict = {}
        self.provenance: list = []

    def blocks(self, arm: str, season: int, seed: int) -> dict:
        key = (arm, season, seed)
        if key in self.injected:
            return self.injected[key]
        if key not in self.cache:
            out, prov = F.load_fit(arm, season, seed, self.fx, self.P, self.require_checks)
            self.cache[key] = out
            self.provenance.append(prov)
        return self.cache[key]

    def per_seed(self, arm: str, seeds, seasons, block: str = "td") -> pd.DataFrame:
        parts = []
        for s in seasons:
            per = {}
            for k in seeds:
                b = self.blocks(arm, s, k)
                if block not in b:
                    raise RuntimeError(f"{arm} {s} seed {k}: no {block} block")
                per[k] = b[block]
            parts.append(pd.DataFrame(per))
        out = pd.concat(parts)
        if list(out.columns) != list(seeds):
            raise RuntimeError("seed columns out of order")
        return out

    def eta(self, arm: str, seeds, seasons, block: str = "td") -> pd.Series:
        p = self.per_seed(arm, seeds, seasons, block)
        if p.isna().to_numpy().any():                                     # verifier V13: never a NaN-skipping mean
            raise RuntimeError(f"{arm} {block}: forecasts missing for {int(p.isna().any(axis=1).sum())} rows")
        return pd.Series(C.lg(p.mean(axis=1).to_numpy()), index=p.index)


class Scorer:
    """Everything that needs outcomes y (a Series by match id: real in --run, drawn in --synthetic)."""

    def __init__(self, bank: Bank, info: pd.DataFrame, y: pd.Series):
        self.bank, self.info, self.y = bank, info, y
        self._slopes: dict = {}

    # the decided calibration: seasons 2019 .. Y - 1 only, seeds 0-3, per tour, no intercept
    def slopes(self, arm: str, season: int) -> dict:
        key = (arm, season)
        if key not in self._slopes:
            hist = tuple(range(C.CALIB_FROM, season))
            eta = self.bank.eta(arm, C.CAL_SEEDS, hist, "td")
            inf = self.info.reindex(eta.index)
            if inf["season"].max() >= season:
                raise RuntimeError("calibration read a season >= Y")
            keep = ~inf["debut"].to_numpy(bool)
            out = {}
            for t in C.TOURS:
                m = keep & (inf["tour"].to_numpy() == t)
                if m.sum() < MIN_CAL_ROWS:
                    raise RuntimeError(f"calibration of {arm} for {season}, {t}: {int(m.sum())} rows")
                yy = self.y.reindex(eta.index[m]).to_numpy(float)
                if np.isnan(yy).any():
                    raise RuntimeError("outcomes missing in the calibration window")
                beta, _ = C.fit_logistic(eta.to_numpy()[m][:, None], yy)
                out[t] = float(beta[0])
            self._slopes[key] = out
        return self._slopes[key]

    def row_slopes(self, arm: str, ids) -> np.ndarray:
        inf = self.info.loc[ids]
        return np.array([self.slopes(arm, int(s))[t] for s, t in zip(inf["season"], inf["tour"])])

    # S13: the closing price recalibrated the decided way: one slope per tour on logit p_mkt, no intercept, fitted for
    # season Y on 2019 .. Y - 1, debut seasons out
    def price_slopes(self, season: int) -> dict:
        key = ("__close__", season)
        if key not in self._slopes:
            inf = self.info
            s_ = inf["season"].to_numpy()
            p = inf["p_mkt"].to_numpy(float)
            base = (s_ >= C.CALIB_FROM) & (s_ < season) & ~inf["debut"].to_numpy(bool) & np.isfinite(p)
            out = {}
            for t in C.TOURS:
                m = base & (inf["tour"].to_numpy() == t)
                if m.sum() < MIN_CAL_ROWS:
                    raise RuntimeError(f"price calibration for {season}, {t}: {int(m.sum())} rows")
                yy = self.y.reindex(inf.index[m]).to_numpy(float)
                if np.isnan(yy).any():
                    raise RuntimeError("outcomes missing in the price calibration window")
                beta, _ = C.fit_logistic(C.lg(p[m])[:, None], yy)
                out[t] = float(beta[0])
            self._slopes[key] = out
        return self._slopes[key]

    def price_forecast(self, ids) -> np.ndarray:
        inf = self.info.loc[ids]
        p = inf["p_mkt"].to_numpy(float)
        if not np.isfinite(p).all():
            raise RuntimeError("closing price missing on scored rows")
        s = np.array([self.price_slopes(int(se))[t] for se, t in zip(inf["season"], inf["tour"])])
        return expit(s * C.lg(p))

    def forecast(self, arm: str, seeds, seasons, block: str, metric: str, ids) -> tuple[np.ndarray, np.ndarray]:
        """(the seed-mean forecast, the per-seed forecasts), calibrated or raw, on rows ids."""
        p = self.bank.per_seed(arm, seeds, seasons, block).reindex(ids)
        if p.isna().to_numpy().any():
            raise RuntimeError(f"{arm} {block}: forecasts missing for {int(p.isna().any(axis=1).sum())} rows")
        if metric == "raw":
            return p.mean(axis=1).to_numpy(), p.to_numpy()
        s = self.row_slopes(arm, ids)
        return expit(s * C.lg(p.mean(axis=1).to_numpy())), expit(s[:, None] * C.lg(p.to_numpy()))

    def paired(self, cmp: Comparison, ids=None) -> dict:
        ids = population_ids(self.info, cmp.population, cmp.seasons) if ids is None else ids
        if len(ids) == 0:
            return {"cid": cmp.cid, "matches": 0, "available": False}
        qb, qbk = self.forecast(cmp.base, cmp.seeds, cmp.seasons, cmp.block, cmp.metric, ids)
        qa, qak = self.forecast(cmp.arm, cmp.seeds, cmp.seasons, cmp.block, cmp.metric, ids)
        if qbk.shape[1] != qak.shape[1]:
            raise RuntimeError("unequal seed sets")
        y = self.y.reindex(ids).to_numpy(float)
        if np.isnan(y).any():
            raise RuntimeError("outcomes missing")
        inf = self.info.loc[ids]
        loss = LOSSES[cmp.loss]
        r = paired_stats(loss(qb, y), loss(qa, y), seed_loss(qbk, y, loss), seed_loss(qak, y, loss),
                         inf["block"].to_numpy(), inf["week"].to_numpy())
        return {"cid": cmp.cid, "base": cmp.base, "arm": cmp.arm, "seeds": [min(cmp.seeds), max(cmp.seeds)],
                "population": cmp.population, "seasons": list(cmp.seasons), "metric": cmp.metric, "block": cmp.block,
                "loss": cmp.loss, "direction": cmp.direction, "unit": cmp.unit, **r}


def brier(q, y) -> np.ndarray:
    """Per-match Brier score of a forecast that A wins."""
    return (np.asarray(q, float) - np.asarray(y, float)) ** 2


LOSSES = {"ll": C.ll, "brier": brier}


def seed_loss(qk: np.ndarray, y: np.ndarray, loss=C.ll) -> np.ndarray:
    """1000 x the mean loss of each seed's forecast on these rows (one value per seed): the empirical seed variance's
    input (surface-IOS seed_var convention)."""
    return 1000 * loss(qk, y[:, None]).mean(axis=0)


def cluster_se(values: np.ndarray, clusters: np.ndarray) -> tuple[float, int]:
    """SE of the mean with a cluster sandwich and the G / (G - 1) factor: tabpfn_thinking.common.paired_interval's
    formula, returned as an SE (same units as values)."""
    values = np.asarray(values, float)
    labels_, ix = np.unique(clusters, return_inverse=True)
    G, n = len(labels_), len(values)
    infl = np.bincount(ix, weights=values - values.mean())
    return float(np.sqrt(G / (G - 1) * np.dot(infl, infl)) / n), G


def paired_stats(ll_base, ll_arm, seed_ll_base, seed_ll_arm, block, week) -> dict:
    """1000 x mean(loss_base - loss_arm), positive = the arm better, with the block interval plus the seeds' variance
    (lo, hi), the block-only interval and the calendar-week interval plus the seeds' variance. Any per-match loss (log
    loss or Brier); the seed arrays are 1000 x each seed's mean loss on the same rows."""
    d = 1000 * (np.asarray(ll_base) - np.asarray(ll_arm))
    g = float(d.mean())
    v_base = float(np.var(seed_ll_base, ddof=1) / len(seed_ll_base)) if len(seed_ll_base) > 1 else 0.0
    v_arm = float(np.var(seed_ll_arm, ddof=1) / len(seed_ll_arm)) if len(seed_ll_arm) > 1 else 0.0
    se_b, Gb = cluster_se(d, block)
    se_w, Gw = cluster_se(d, week)
    tb, tw = student_t.ppf(0.975, Gb - 1), student_t.ppf(0.975, Gw - 1)
    se = np.sqrt(se_b ** 2 + v_base + v_arm)
    sew = np.sqrt(se_w ** 2 + v_base + v_arm)
    return {"matches": int(len(d)), "estimate": g, "lo": g - tb * se, "hi": g + tb * se, "se": float(se),
            "se_block": se_b, "v_seed_base": v_base, "v_seed_arm": v_arm, "blocks": Gb,
            "lo_block_only": g - tb * se_b, "hi_block_only": g + tb * se_b,
            "lo_week": g - tw * sew, "hi_week": g + tw * sew, "weeks": Gw}


# ------------------------------------------------------------------------------------------------
# S0 / S12: the information test (feature interactions' tabpfn_tests.encompassing, copied with screen.fit and
# screen.clustered_variances, so the frozen code is this study's own)

def _fit(Z: np.ndarray, y: np.ndarray, max_iter: int = 80, tol: float = 1e-10):
    k = Z.shape[1]
    pen = np.full(k, 1e-8)
    beta = np.zeros(k)
    for _ in range(max_iter):
        p = expit(Z @ beta)
        g = Z.T @ (y - p) - pen * beta
        H = (Z.T * (p * (1 - p))) @ Z + np.diag(pen)
        step = np.linalg.solve(H, g)
        big = np.abs(step).max()
        if big > 4:
            step *= 4 / big
        beta += step
        if np.abs(step).max() < tol:
            break
    p = expit(Z @ beta)
    return beta, p, (Z.T * (p * (1 - p))) @ Z + np.diag(pen)


def _sum_sq_by(u: np.ndarray, keys: np.ndarray) -> float:
    _, ix = np.unique(keys, return_inverse=True)
    s = np.bincount(ix, weights=u)
    return float(np.dot(s, s))


def clustered_variances(u: np.ndarray, block: np.ndarray, pa: np.ndarray, pb: np.ndarray) -> dict:
    G = len(np.unique(block))
    corr = G / (G - 1) if G > 1 else np.nan
    v_block = _sum_sq_by(u, block)
    pa, pb = np.asarray(pa, str), np.asarray(pb, str)
    players = np.r_[pa, pb]
    uu = np.r_[u, u]
    pair = np.where(pa < pb, np.char.add(np.char.add(pa, "|"), pb), np.char.add(np.char.add(pb, "|"), pa))
    v_player = _sum_sq_by(uu, players) - _sum_sq_by(u, pair)
    bk = np.r_[block, block].astype(str)
    v_both = _sum_sq_by(uu, np.char.add(np.char.add(players.astype(str), "#"), bk)) - \
        _sum_sq_by(u, np.char.add(np.char.add(pair.astype(str), "#"), block.astype(str)))
    return {"block": corr * v_block, "player": corr * v_player, "union": corr * (v_block + v_player - v_both)}


def encompassing(inf: pd.DataFrame, y: np.ndarray, eta_b: np.ndarray, dev: np.ndarray,
                 unit: str = "log-odds per unit of the column") -> dict:
    """b is per UNIT of dev (dev is scaled by its SD inside and b scaled back; sd_z is reported)."""
    eta_b, dev = np.asarray(eta_b, float), np.asarray(dev, float)
    tour, season = inf["tour"].to_numpy(), inf["season"].to_numpy()
    cols = [np.where((tour == t_) & (season == s_), eta_b, 0.0) for t_, s_ in sorted(set(zip(tour, season)))]
    for t_ in C.TOURS:
        if not (tour == t_).any():
            continue
        e3 = np.where(tour == t_, eta_b ** 3, 0.0)
        cols.append(e3 / (np.std(e3[tour == t_]) or 1.0))
    sd_dev = float(np.std(dev)) or 1.0
    Z = np.column_stack(cols + [dev / sd_dev])
    beta, p, H = _fit(Z, y)
    j = Z.shape[1] - 1
    a_j = np.linalg.solve(H, np.eye(Z.shape[1])[j])
    u = (y - p) * (Z @ a_j)
    v = clustered_variances(u, inf["block"].to_numpy(), inf["player_a_id"].to_numpy(str),
                            inf["player_b_id"].to_numpy(str))
    G = len(np.unique(inf["block"]))
    b, se = float(beta[j]) / sd_dev, float(np.sqrt(max(v.values()))) / sd_dev
    tq = student_t.ppf(0.975, G - 1)
    return {"matches": int(len(y)), "estimate": b, "se": se, "lo": b - tq * se, "hi": b + tq * se, "df": G - 1,
            "p_two_sided": float(2 * student_t.sf(abs(b / se), G - 1)), "blocks": G, "sd_z": sd_dev, "unit": unit}


def s_f_kmh(P: C.Paths) -> float | None:
    """The feature file's frozen scale s_f (km/h per unit of spd_f), from speed_meta.json."""
    try:
        v = C.read_json(P.feature_meta).get("s_f")
        return float(v) if v is not None else None
    except (OSError, ValueError):
        return None


def column_unit(z_col: str, P: C.Paths) -> str:
    """Verifier V6: S0's and S12's b are per UNIT of the column, not per SD."""
    if z_col == "spd_raw":
        return "log-odds per unit of spd_raw (one unit = 5.998 km/h of the registered x_raw)"
    s_f = s_f_kmh(P)
    return f"log-odds per unit of {z_col} (one s_f = {s_f:.3f} km/h)" if s_f else f"log-odds per unit of {z_col} (one s_f)"


def information(sc: Scorer, z_col: str, seasons) -> dict:
    ids = population_ids(sc.info, "men", seasons)
    eta_b = sc.bank.eta("model", SEEDS16, seasons, "td").reindex(ids).to_numpy()
    z = sc.info.loc[ids, z_col].fillna(0.0).to_numpy(float)
    y = sc.y.reindex(ids).to_numpy(float)
    return encompassing(sc.info.loc[ids], y, eta_b, z, column_unit(z_col, sc.bank.P))


# ------------------------------------------------------------------------------------------------
# S6 moves, S9 nudge, S10 capture

def ols_cluster(y: np.ndarray, X: np.ndarray, clusters: np.ndarray) -> dict:
    """OLS without intercept, CR1 cluster-robust covariance, t on G - 1 (surface_elo_pieces.early_price_score)."""
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    labels_, ix = np.unique(clusters, return_inverse=True)
    g = len(labels_)
    S = np.zeros((g, k))
    np.add.at(S, ix, X * e[:, None])
    V = XtX_inv @ (S.T @ S) @ XtX_inv * (g / (g - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(V))
    tq = student_t.ppf(0.975, g - 1)
    return {"beta": beta.tolist(), "se": se.tolist(), "lo": (beta - tq * se).tolist(), "hi": (beta + tq * se).tolist(),
            "clusters": int(g), "n": int(n)}


BASE_EARLY_CONTROL, BASE_EARLY_DEV = tuple(range(8)), tuple(range(8, 16))


def moves(sc: Scorer) -> list[dict]:
    """The Polymarket price's move from 24 hours to 30 minutes, M = logit p(30 min) - logit p(24 h), regressed with no
    intercept and four-week clusters; positive = the price moved toward the speed arm's view.
    With the odds (verifier V1): M on [eta_B[0-7],early - logit p(24 h), eta_B[0-7],early, eta_A1[0-15],early -
    eta_B[8-15],early], the LAST slope read. The base's seeds are disjoint between the controls and the deviation, and
    eta_B itself is a control, so neither the base's seed noise nor a confidence difference between the arms can fake a
    move (the first version rejected a true null in 24-43% of the verifier's replicates).
    Without the odds: M on [eta_Bno, eta_Ano - eta_Bno] (the no-odds twins, seeds 0-7, the rating race's convention),
    the second slope."""
    out = []
    for pop in ("men_early_all", "men_early_clean"):
        ids = population_ids(sc.info, pop, (2025, 2026))
        if len(ids) < 20:
            continue
        inf = sc.info.loc[ids]
        M = C.lg(inf["p_close_a"]) - C.lg(inf["p_early_a"])
        eb_c = sc.bank.eta("model", BASE_EARLY_CONTROL, (2025, 2026), "early").reindex(ids).to_numpy()
        eb_d = sc.bank.eta("model", BASE_EARLY_DEV, (2025, 2026), "early").reindex(ids).to_numpy()
        ea = sc.bank.eta("spd", SEEDS16, (2025, 2026), "early").reindex(ids).to_numpy()
        X = np.column_stack([eb_c - C.lg(inf["p_early_a"]), eb_c, ea - eb_d])
        r = ols_cluster(M, X, inf["block"].to_numpy())
        out.append({"cid": f"S6_move_odds_{pop.rsplit('_', 1)[1]}", "population": pop, "matches": r["n"],
                    "estimate": r["beta"][2], "lo": r["lo"][2], "hi": r["hi"][2], "unit": "slope",
                    "direction": "positive = the price moved toward A1's view beyond the base's (early-fed; the base's "
                                 "seeds 0-7 as controls, 8-15 in the deviation)"})
        nb = sc.bank.eta("model_noodds", SEEDS8, (2025, 2026), "td").reindex(ids).to_numpy()
        na = sc.bank.eta("spd_noodds", SEEDS8, (2025, 2026), "td").reindex(ids).to_numpy()
        r = ols_cluster(M, np.column_stack([nb, na - nb]), inf["block"].to_numpy())
        out.append({"cid": f"S6_move_noodds_{pop.rsplit('_', 1)[1]}", "population": pop, "matches": r["n"],
                    "estimate": r["beta"][1], "lo": r["lo"][1], "hi": r["hi"][1], "unit": "slope",
                    "direction": "positive = the price moved toward the no-odds A1's view beyond the no-odds base's"})
    return out


def nudge_parameters(sc: Scorer, season: int) -> dict:
    """S9: logit q = s_tour eta + b z fitted on 2019 .. season - 1 (both tours, debut out), eta = the base's seeds 0-3
    mean, z = spd_f; returns s, b (maximum likelihood), its SE and the shrunk b (prior N(0, TAU^2))."""
    hist = tuple(range(C.CALIB_FROM, season))
    eta = sc.bank.eta("model", C.CAL_SEEDS, hist, "td")
    inf = sc.info.reindex(eta.index)
    if inf["season"].max() >= season:
        raise RuntimeError("nudge read a season >= Y")
    keep = ~inf["debut"].to_numpy(bool)
    e, atp = eta.to_numpy()[keep], (inf["tour"].to_numpy() == "atp")[keep]
    z = inf["spd_f"].to_numpy(float)[keep]
    yy = sc.y.reindex(eta.index[keep]).to_numpy(float)
    beta, se = C.fit_logistic(np.column_stack([np.where(atp, e, 0.0), np.where(~atp, e, 0.0), z]), yy)
    b, s = float(beta[2]), float(se[2])
    return {"s_atp": float(beta[0]), "s_wta": float(beta[1]), "b_mle": b, "se_b": s,
            "b_shrunk": b * C.TAU_NUDGE ** 2 / (C.TAU_NUDGE ** 2 + s ** 2), "rows": int(keep.sum())}


def nudge(sc: Scorer) -> tuple[list[dict], dict]:
    ids = population_ids(sc.info, "men", TEST)
    qb, _ = sc.forecast("model", SEEDS16, TEST, "td", "calibrated", ids)
    eta16 = sc.bank.eta("model", SEEDS16, TEST, "td").reindex(ids).to_numpy()
    inf = sc.info.loc[ids]
    y = sc.y.reindex(ids).to_numpy(float)
    params = {s: nudge_parameters(sc, s) for s in TEST}
    rows = []
    for variant in ("b_shrunk", "b_mle"):
        logit_q = np.empty(len(ids))
        for s, p in params.items():
            k = (inf["season"] == s).to_numpy()
            sl = np.where(inf["tour"].to_numpy() == "atp", p["s_atp"], p["s_wta"])
            logit_q[k] = sl[k] * eta16[k] + p[variant] * inf["spd_f"].to_numpy(float)[k]
        d_ll_f = C.ll(expit(logit_q), y)
        r = paired_stats(C.ll(qb, y), d_ll_f, np.zeros(1), np.zeros(1), inf["block"].to_numpy(), inf["week"].to_numpy())
        rows.append({"cid": f"S9_{'shrunk' if variant == 'b_shrunk' else 'mle'}", "population": "men",
                     "seasons": list(TEST), "unit": "mLL",
                     "direction": "positive = the nudge has the lower log loss (better) than the calibrated base",
                     **{k: r[k] for k in ("matches", "estimate", "lo_block_only", "hi_block_only")},
                     "lo": r["lo_block_only"], "hi": r["hi_block_only"]})
    return rows, {str(k): v for k, v in params.items()}


def capture(sc: Scorer, s0: dict) -> dict:
    """S10. a = sum(dev z) / sum(z^2) on raw log-odds (dev = eta_A1 - eta_B, 16-seed means). Verifier V9: S0's b is on
    the calibrated (outcome) scale, so also a_cal = sum(s_Y dev z) / sum(z^2), each season's deviation multiplied by
    s_Y, A1's men's calibration slope for that season (per season, pooled by the z^2 weights), and a_cal / b_S0."""
    ids = population_ids(sc.info, "men", TEST)
    dev = (sc.bank.eta("spd", SEEDS16, TEST, "td") - sc.bank.eta("model", SEEDS16, TEST, "td")).reindex(ids).to_numpy()
    z = sc.info.loc[ids, "spd_f"].to_numpy(float)
    a = float(np.dot(dev, z) / np.dot(z, z))
    s_y = {int(s): sc.slopes("spd", int(s))["atp"] for s in TEST}
    s_row = np.array([s_y[int(s)] for s in sc.info.loc[ids, "season"]])
    a_cal = float(np.dot(s_row * dev, z) / np.dot(z, z))
    excl = s0["lo"] > 0 or s0["hi"] < 0
    ok = excl and s0["estimate"] != 0
    return {"cid": "S10", "matches": int(len(ids)), "applied_slope_a": a, "applied_slope_calibrated": a_cal,
            "s_Y_men_A1": {str(k): v for k, v in s_y.items()},
            "unit": f"{column_unit('spd_f', sc.bank.P)}; a on raw log-odds, a_cal on the calibrated scale",
            "ratio_to_S0": a / s0["estimate"] if ok else None,
            "calibrated_ratio_to_S0": a_cal / s0["estimate"] if ok else None,
            "direction": "a > 0 = TabPFN moved its forecast toward the player whose speed state is higher"}


def close_edge(sc: Scorer, p2: dict) -> dict:
    """S13, context for "by how much": the calibrated base (seeds 0-15) against the calibrated closing price on P2's
    population; block-only interval (the price has no seeds). The ratio P2 / S13 is a descriptive point value."""
    ids = population_ids(sc.info, PRIMARY.population, PRIMARY.seasons)
    qb, _ = sc.forecast("model", SEEDS16, TEST, "td", "calibrated", ids)
    qm = sc.price_forecast(ids)
    y = sc.y.reindex(ids).to_numpy(float)
    inf = sc.info.loc[ids]
    r = paired_stats(C.ll(qm, y), C.ll(qb, y), np.zeros(1), np.zeros(1), inf["block"].to_numpy(),
                     inf["week"].to_numpy())
    est = r["estimate"]
    return {"cid": "S13", "base": "close", "arm": "model", "population": PRIMARY.population,
            "seasons": list(TEST), "seeds": [0, 15], "matches": r["matches"], "estimate": est,
            "lo": r["lo_block_only"], "hi": r["hi_block_only"], "blocks": r["blocks"], "unit": "mLL",
            "direction": "positive = the calibrated base (58 inputs, seeds 0-15) has the lower log loss (better) than "
                         "the calibrated closing price",
            "ratio_P2_to_S13": (p2["estimate"] / est) if est != 0 else None,
            "ratio_note": "descriptive point value only (no interval): P2 as a share of the base's edge over the close"}


# ------------------------------------------------------------------------------------------------
# The decision table and the evaluation

def verdict(lo: float, hi: float, pos: str = "better", neg: str = "worse") -> str:
    return pos if lo > 0 else (neg if hi < 0 else "tie")


def decision(p2: dict, s0: dict) -> dict:
    g = f"{p2['estimate']:+.2f} [{p2['lo']:+.2f}, {p2['hi']:+.2f}] mLL"
    if p2["lo"] > 0:
        row, text = 1, f"Adding the speed state improves the men's log loss by {g} (positive = A1 better)"
    elif p2["hi"] < 0:
        row, text = 2, f"Harm: adding the speed state worsens the men's log loss ({g}, positive = A1 better); do not deploy"
    elif s0["lo"] > 0:
        row, text = 3, (f"S0 detects information beyond the base (b {s0['estimate']:+.3f} [{s0['lo']:+.3f}, "
                        f"{s0['hi']:+.3f}] {s0['unit']}); P2 ties ({g}). P2 has less power than S0 at small effects and "
                        "loses power as capture rises, so the tie does not show the column fails; S10 (capture) and S9 "
                        "(nudge) say whether it delivers")
    elif s0["hi"] < 0:
        row, text = 5, (f"P2 ties ({g}); S0 reverses the published direction (b {s0['estimate']:+.3f} "
                        f"[{s0['lo']:+.3f}, {s0['hi']:+.3f}] {s0['unit']})")
    else:
        row, text = 4, (f"No detectable speed information beyond the model in 2024-2026: P2 {g} bounds the gain, S0 b "
                        f"{s0['estimate']:+.3f} [{s0['lo']:+.3f}, {s0['hi']:+.3f}] {s0['unit']} bounds beta")
    return {"row": row, "reading": text}


def evaluate(sc: Scorer, core_only: bool = False) -> dict:
    p2 = sc.paired(PRIMARY)
    s0 = information(sc, "spd_f", TEST)
    s0.update({"cid": "S0", "direction": "positive = the man whose speed state is higher wins more often than the "
                                         "base says"})
    out = {"P2": p2, "S0": s0, "S10": capture(sc, s0),
           "S11": [{"cid": "S11_block_only", "estimate": p2["estimate"], "lo": p2["lo_block_only"],
                    "hi": p2["hi_block_only"], "unit": "mLL", "direction": PRIMARY.direction},
                   {"cid": "S11_week", "estimate": p2["estimate"], "lo": p2["lo_week"], "hi": p2["hi_week"],
                    "unit": "mLL", "direction": PRIMARY.direction}],
           "S13": close_edge(sc, p2), "S14": sc.paired(S14),
           "decision": decision(p2, s0)}
    if core_only:
        out["multiplicity"] = multiplicity(out)
        return out
    secondary = []
    for cmp in COMPARISONS[1:]:
        try:
            secondary.append(sc.paired(cmp))
        except (FileNotFoundError, RuntimeError, np.linalg.LinAlgError, ValueError) as e:   # never silences the rest
            secondary.append({"cid": cmp.cid, "available": False, "error": str(e), "direction": cmp.direction})
    out["paired_secondaries"] = secondary
    try:
        out["S6_moves"] = moves(sc)
    except (FileNotFoundError, RuntimeError, np.linalg.LinAlgError, ValueError) as e:
        out["S6_moves"] = [{"cid": "S6_move", "available": False, "error": str(e)}]
    try:
        out["S9"], out["S9_parameters"] = nudge(sc)
    except (FileNotFoundError, RuntimeError, np.linalg.LinAlgError, ValueError) as e:
        out["S9"], out["S9_parameters"] = [{"cid": "S9", "available": False, "error": str(e)}], {}
    try:
        s12 = information(sc, "spd_raw", (2025, 2026))
        s12.update({"cid": "S12", "direction": "positive = the man whose registered speed change is higher wins more "
                                               "often than the base says"})
        out["S12"] = s12
    except (FileNotFoundError, RuntimeError, np.linalg.LinAlgError, ValueError) as e:
        out["S12"] = {"cid": "S12", "available": False, "error": str(e)}
    out["multiplicity"] = multiplicity(out)
    return out


CONTEXT = ("S13",)        # context, not a test of the speed column: reported, never counted


def secondary_rows(res: dict, counted: bool = False) -> list[dict]:
    """Every secondary estimate with an interval (S0-S14; S10 and the S13 ratio are point values and are not here).
    counted=True drops the context row S13 (the base against the close), which tests no speed column."""
    rows = [res["S0"]] + res.get("paired_secondaries", []) + res.get("S6_moves", []) + res.get("S9", []) + \
        res["S11"] + ([res["S12"]] if "S12" in res else []) + [res["S13"], res["S14"]]
    rows = [r for r in rows if r.get("available", True) and "lo" in r]
    return [r for r in rows if r["cid"] not in CONTEXT] if counted else rows


def multiplicity(res: dict) -> dict:
    rows = secondary_rows(res, counted=True)
    excl = [r["cid"] for r in rows if r["lo"] > 0 or r["hi"] < 0]
    return {"secondary_intervals": len(rows), "excluding_0": len(excl), "which": excl,
            "not_counted": list(CONTEXT) + ["S10 (point value)", "the P2 / S13 ratio (point value)"],
            "null_reference": "the verifier's null re-run after V1 (pre-registration section 9), not 5% x K"}


def table(res: dict) -> pd.DataFrame:
    rows = [{**res["P2"], "role": "primary"}] + \
        [{**r, "role": "context (not counted)" if r["cid"] in CONTEXT else "secondary"} for r in secondary_rows(res)]
    t = pd.DataFrame(rows)
    t["verdict"] = [verdict(lo, hi) if u in UNIT.values() else verdict(lo, hi, "positive", "negative")
                    for lo, hi, u in zip(t["lo"], t["hi"], t["unit"])]
    keep = ["role", "cid", "base", "arm", "population", "seasons", "metric", "block", "seeds", "matches", "estimate",
            "lo", "hi", "unit", "direction", "verdict", "lo_block_only", "hi_block_only", "lo_week", "hi_week",
            "v_seed_base", "v_seed_arm", "se_block", "blocks"]
    return t[[c for c in keep if c in t.columns]]


# ------------------------------------------------------------------------------------------------
# Hashes, --check

def hashes(P: C.Paths = C.DEFAULT, info: pd.DataFrame | None = None) -> dict:
    info = population(P) if info is None else info
    return {"SCORER_CODE_SHA256": C.code_hash(), "MODEL_FRAME_SHA256": C.sha256_file(P.model_frame),
            "FEATURE_SHA256": C.sha256_file(P.feature_file), "REGISTRY_SHA256": C.sha256_file(P.registry),
            "EARLY_SHA256": C.sha256_file(P.early),
            "POPULATION_SHA256": ids_hash(population_ids(info, "men", TEST))}


def needed_fits() -> dict:
    """(arm -> {(season, seed)}) every fit the scorer reads: each comparison's scored seasons and seeds, every
    calibration window 2019 .. 2025 with seeds 0-3."""
    need: dict = {}
    for cmp in COMPARISONS:
        for arm in (cmp.base, cmp.arm):
            need.setdefault(arm, set()).update((s, k) for s in cmp.seasons for k in cmp.seeds)
            if cmp.metric == "calibrated":
                need[arm].update((s, k) for s in range(C.CALIB_FROM, max(cmp.seasons)) for k in C.CAL_SEEDS)
    need.setdefault("model", set()).update((s, k) for s in HIST for k in SEEDS16)      # S0, S9, S10 on the base
    return need


def forecasts_hash(P: C.Paths = C.DEFAULT) -> dict:
    """SHA-256 over every fit file the scorer reads that exists now (sorted by arm, season, seed); informational: the
    pre-registration records it when the fits exist at the freeze."""
    h = hashlib.sha256(b"serve_speed_tabpfn/forecasts/v1")
    present = missing = 0
    for arm, need in sorted(needed_fits().items()):
        for season, seed in sorted(need):
            try:
                label, path = F.find_fit(arm, season, seed, P)
            except FileNotFoundError:
                missing += 1
                continue
            h.update(f"{arm}|{season}|{seed}|{label}".encode())
            h.update(path.read_bytes())
            present += 1
    return {"FORECASTS_SHA256": h.hexdigest(), "fits_present": present, "fits_missing": missing}


def check(P: C.Paths = C.DEFAULT) -> dict:
    """Result-free: populations, counts, hashes, probes, fits present, reuse checks. Writes check.json."""
    info = population(P)
    pops = {}
    for pop, seasons in (("men", TEST), ("women", TEST), ("both", TEST), ("men", (2025, 2026)),
                         ("men_recency_both", TEST), ("men_recency_one", TEST), ("men_recency_neither", TEST),
                         ("women_no_conflict", TEST), ("men_early_all", (2025, 2026)), ("men_early_clean", (2025, 2026))):
        ids = population_ids(info, pop, seasons)
        inf = info.loc[ids]
        pops[f"{pop} {seasons[0]}-{seasons[-1]}"] = {
            "matches": int(len(ids)), "sha256": ids_hash(ids),
            "by_season": {str(k): int(v) for k, v in inf["season"].value_counts().sort_index().items()},
            "spd_f_nonzero": int((inf["spd_f"] != 0).sum()), "spd_f_all_nonzero": int((inf["spd_f_all"] != 0).sum()),
            "spd_raw_present": int(inf["spd_raw"].notna().sum()), "blocks": int(inf["block"].nunique())}
    men = info.loc[population_ids(info, "men", TEST)]
    fits = {}
    for arm, need in sorted(needed_fits().items()):
        missing = []
        for season, seed in sorted(need):
            try:
                F.find_fit(arm, season, seed, P)
            except FileNotFoundError:
                missing.append([season, seed])
        fits[arm] = {"needed": len(need), "present": len(need) - len(missing), "missing": missing}
    out = {"what": "result-free check of the scorer's inputs (no match result read)",
           "hashes": hashes(P, info), "feature_status": A.feature_status(P), "registry": A.registry(P),
           "populations": pops, "recency_available": bool(info["recency"].notna().any()),
           "men_2024_2026_recency": {str(k): int(v) for k, v in men["recency"].value_counts(dropna=False).items()},
           "women_id_conflict_2024_2026": int(info.loc[population_ids(info, "women", TEST), "id_conflict"].sum()),
           "fits": fits, "forecasts": forecasts_hash(P), "reuse_checks": F.checks_passed(P),
           "stale_speed_fits": F.stale_speed_fits(P, needed_fits()),
           "comparisons": [asdict(c) for c in COMPARISONS + [S14]], "calibration_seeds": list(C.CAL_SEEDS)}
    C.write_json(P.out / "check.json", out)
    return out


# ------------------------------------------------------------------------------------------------
# --synthetic (the verifier's mode)

def synthetic(P: C.Paths = C.DEFAULT, beta: float = 0.0, capture_share: float = 0.5, reps: int = 200, seed: int = 0,
              arms: str = "synthetic", s_true: float = 0.9, seed_sd: float = 0.019, tag: str | None = None) -> dict:
    """Outcomes y ~ Bernoulli(expit(s_true * eta_B + beta * spd_f)) for every 2019-2026 frame match (eta_B the base's
    16-seed log-odds; spd_f is 0 for women), never read. arms="synthetic": A1's seed k = eta_B + capture *
    (beta / s_true) * spd_f + N(0, seed_sd^2) per match; arms="real": A1's saved fits (the feature-hash guard applies).
    Reports P2, S0, S10, S11, S13 (the base against the recalibrated close) and S14 (P2 on the Brier score) per replicate
    and their rejection rates; `expected_gain` is P2's exact expectation given the forecasts."""
    info = population(P)
    if arms == "real":
        # verifier V5: the real A1 forecasts carry a speed coefficient TabPFN learned from results (2024-25 included
        # for the 2025-26 fits); relating them to spd_f is allowed only after the pre-registration is hashed
        verify_prereg(P, hashes(P, info))
    fx = frame_index(P)
    bank = Bank(P, fx, require_checks=(arms == "real"))
    eta_b = bank.eta("model", SEEDS16, HIST, "td").reindex(info.index)
    if eta_b.isna().any():
        raise RuntimeError("base forecasts missing for some 2019-2026 frame matches")
    z = info["spd_f"].to_numpy(float)
    truth = s_true * eta_b.to_numpy() + beta * z
    rng = np.random.default_rng(seed)
    ids_p2 = population_ids(info, "men", TEST)
    pos = pd.Series(np.arange(len(info)), index=info.index)
    rows = []
    for r in range(reps):
        y = pd.Series((rng.random(len(info)) < expit(truth)).astype(float), index=info.index)
        if arms == "synthetic":
            bank.injected = {}
            base = eta_b.to_numpy() + capture_share * (beta / s_true) * z
            for s in HIST:
                k_rows = (info["season"] == s).to_numpy()
                idx = info.index[k_rows]
                for k in SEEDS16:
                    p = expit(base[k_rows] + rng.normal(0, seed_sd, k_rows.sum()))
                    bank.injected[("spd", s, k)] = {"td": pd.Series(p, index=idx)}
        sc = Scorer(bank, info, y)
        res = evaluate(sc, core_only=True)
        qb, _ = sc.forecast("model", SEEDS16, TEST, "td", "calibrated", ids_p2)
        qa, _ = sc.forecast("spd", SEEDS16, TEST, "td", "calibrated", ids_p2)
        pt = expit(truth[pos.reindex(ids_p2).to_numpy()])
        exp_gain = 1000 * float(np.mean(pt * (np.log(qa) - np.log(qb)) + (1 - pt) * (np.log1p(-qa) - np.log1p(-qb))))
        p2, s0, s13, s14 = res["P2"], res["S0"], res["S13"], res["S14"]
        rows.append({"rep": r, "P2": p2["estimate"], "P2_lo": p2["lo"], "P2_hi": p2["hi"],
                     "P2_lo_block_only": p2["lo_block_only"], "P2_hi_block_only": p2["hi_block_only"],
                     "expected_gain": exp_gain, "S0_b": s0["estimate"], "S0_lo": s0["lo"], "S0_hi": s0["hi"],
                     "S10_a": res["S10"]["applied_slope_a"], "S13": s13["estimate"], "S13_lo": s13["lo"],
                     "S13_hi": s13["hi"], "S13_ratio": s13["ratio_P2_to_S13"], "S14": s14["estimate"],
                     "S14_lo": s14["lo"], "S14_hi": s14["hi"], "excluding_0": res["multiplicity"]["excluding_0"],
                     "decision_row": res["decision"]["row"]})
    t = pd.DataFrame(rows)
    summary = {"reps": reps, "beta": beta, "capture": capture_share, "arms": arms, "s_true": s_true, "seed": seed,
               "P2_mean": float(t["P2"].mean()), "expected_gain_mean": float(t["expected_gain"].mean()),
               "P2_reject_positive": float((t["P2_lo"] > 0).mean()), "P2_reject_negative": float((t["P2_hi"] < 0).mean()),
               "P2_block_only_reject_positive": float((t["P2_lo_block_only"] > 0).mean()),
               "P2_covers_expected_gain": float(((t["P2_lo"] <= t["expected_gain"]) & (t["expected_gain"] <= t["P2_hi"])).mean()),
               "S0_b_mean": float(t["S0_b"].mean()), "S0_b_sd": float(t["S0_b"].std()),
               "S0_reject_two_sided": float(((t["S0_lo"] > 0) | (t["S0_hi"] < 0)).mean()),
               "S0_covers_beta": float(((t["S0_lo"] <= beta) & (beta <= t["S0_hi"])).mean()),
               "S10_a_mean": float(t["S10_a"].mean()),
               "S13_mean": float(t["S13"].mean()), "S13_reject_positive": float((t["S13_lo"] > 0).mean()),
               "S14_mean": float(t["S14"].mean()), "S14_reject_positive": float((t["S14_lo"] > 0).mean()),
               "S14_reject_negative": float((t["S14_hi"] < 0).mean()),
               "core_secondaries_excluding_0_mean": float(t["excluding_0"].mean()),
               "decision_rows": {str(k): int(v) for k, v in t["decision_row"].value_counts().sort_index().items()}}
    out = {"what": "synthetic outcomes drawn from a planted model; no match result read", "summary": summary,
           "replicates": t.to_dict(orient="records")}
    tag = tag or f"b{beta:g}_c{capture_share:g}_{arms}_r{reps}_s{seed}"
    C.write_json(P.out / "synthetic" / f"{tag}.json", out)
    return out


# ------------------------------------------------------------------------------------------------
# --run (once, after the hash)

def recorded(prereg_text: str, keys=PREREG_KEYS) -> dict:
    out = {}
    for key in keys:
        m = re.search(rf"{key}\W+([0-9a-f]{{64}})", prereg_text)
        out[key] = m.group(1) if m else None
    return out


def prereg_sha256(P: C.Paths = C.DEFAULT) -> str:
    """Verifier V8: the pre-registration's SHA-256 with CRLF normalised to LF (a checkout under core.autocrlf must not
    change it)."""
    return hashlib.sha256(P.prereg.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def hash_prereg(P: C.Paths = C.DEFAULT) -> str:
    """`score.py --hash-prereg`: write preregistration.sha256 (the lead, at the freeze)."""
    h = prereg_sha256(P)
    P.prereg_sha.write_text(f"{h}  {P.prereg.name} (SHA-256, CRLF normalised to LF)\n", encoding="utf-8")
    return h


def verify_prereg(P: C.Paths, current: dict) -> None:
    if not P.prereg.exists() or not P.prereg_sha.exists():
        raise RuntimeError("no hashed pre-registration")
    if prereg_sha256(P) != P.prereg_sha.read_text(encoding="utf-8").split()[0].strip():
        raise RuntimeError("preregistration.md does not match its recorded SHA-256")
    rec = recorded(P.prereg.read_text(encoding="utf-8"))
    bad = {k: (rec[k], current[k]) for k in PREREG_KEYS if rec[k] != current[k]}
    if bad:
        raise RuntimeError(f"recorded hashes differ from the current inputs or code: {list(bad)}")


def missing_fits(P: C.Paths = C.DEFAULT) -> list:
    out = []
    for arm, need in sorted(needed_fits().items()):
        for season, seed in sorted(need):
            try:
                F.find_fit(arm, season, seed, P)
            except FileNotFoundError:
                out.append((arm, season, seed))
    return out


def run(P: C.Paths = C.DEFAULT) -> dict:
    if (P.out / "results.json").exists():
        raise RuntimeError("results.json exists: the test runs once")
    info = population(P)
    current = hashes(P, info)
    verify_prereg(P, current)
    A.require_features(P)
    st = F.checks_passed(P)
    if not all(st.values()):
        raise RuntimeError(f"reuse checks not passed: {st}")
    stale = F.stale_speed_fits(P, needed_fits())         # the feature file equals FEATURE_SHA256 (verify_prereg)
    if stale["mismatches"]:
        raise RuntimeError(f"{len(stale['mismatches'])} speed-arm fits were made on another feature file: "
                           f"{[m['file'] for m in stale['mismatches']][:10]}")
    gone = missing_fits(P)                               # verifier V2: never spend the one run with fits missing
    if gone:
        raise RuntimeError(f"{len(gone)} needed fits are missing, e.g. {gone[:5]}")
    pinned = recorded(P.prereg.read_text(encoding="utf-8"), ("FORECASTS_SHA256",))["FORECASTS_SHA256"]
    if pinned and pinned != forecasts_hash(P)["FORECASTS_SHA256"]:                    # verifier V7
        raise RuntimeError("the fits differ from the FORECASTS_SHA256 the pre-registration records")
    bank = Bank(P, frame_index(P), require_checks=True)
    sc = Scorer(bank, info, labels(P))
    res = evaluate(sc)
    res.update({"key": "mLL gains: positive = the named arm has the lower log loss (better); coefficients in log-odds "
                       "per unit of the column (spd_f: one s_f = 2.224 km/h; spd_raw: 5.998 km/h); a 95% interval "
                       "spanning 0 is a tie",
                "hashes": current, "calibration_seeds": list(C.CAL_SEEDS),
                "expanding_window": "each season Y scored by fits trained on 2013 .. Y - 1",
                "provenance": bank.provenance})
    C.write_json(P.out / "results.json", res)
    table(res).to_csv(P.out / "results.csv", index=False)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--synthetic", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--hash-prereg", action="store_true", help="write preregistration.sha256 (CRLF normalised)")
    ap.add_argument("--beta", type=float, default=0.0)
    ap.add_argument("--capture", type=float, default=0.5)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--arms", choices=("synthetic", "real"), default="synthetic")
    a = ap.parse_args()
    if a.check:
        out = check()
        print(json.dumps({k: out[k] for k in ("hashes", "feature_status", "reuse_checks")}, indent=1, default=str))
        print(json.dumps(out["populations"], indent=1)[:3000])
        return 0
    if a.synthetic:
        out = synthetic(beta=a.beta, capture_share=a.capture, reps=a.reps, seed=a.seed, arms=a.arms)
        print(json.dumps(out["summary"], indent=1))
        return 0
    if a.hash_prereg:
        print(f"{hash_prereg()}  -> {C.DEFAULT.prereg_sha}")
        return 0
    res = run()
    print(res["decision"]["reading"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

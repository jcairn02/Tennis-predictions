"""Step 3: would the model gain from it? Walk-forward calibration layers on the current best's raw out-of-sample
log-odds, development seasons only (2015-2024; 2025-2026 never loaded).

For each target season Y, every layer is fitted by maximum likelihood (no intercept) on seasons 2014 .. Y-1 and applied
to Y. Every modulator uses only quantities known before the match and constants from the training seasons (raw Elo sum
in thousands, quantile edges from the training rows), so nothing is read from Y.

    B14         a slope per tour on eta (the decided calibration's form, on the same window as every layer below)
    B19         the decided calibration itself: a slope per tour fitted on 2019 .. Y-1 (from 2020)
    lin         B14 + b_tour (elo_sum x eta)                 the reversed I-084, per tour
    lin_pooled  B14 + b (elo_sum x eta)                       one b for both tours
    q1          B14 + b_tour (1[weakest fifth by elo_sum] x eta)
    quad        B14 + b1_tour (elo_sum x eta) + b2_tour (elo_sum^2 x eta)
    level       a slope per tour x level (GS+Finals, 1000, 500, 250)
    level_lin   level + b_tour (elo_sum x eta)
    lrank       B14 + b_tour (log-rank sum x eta)
    ttt         B14 + b_tour (TTT sum x eta)
    mset        B14 + cubic and eta|eta| per tour (the screen's nuisance shape)
    mset_lin    mset + b_tour (elo_sum x eta)

Scores: paired log loss against B14 (and B19 from 2020), milli-log-loss per match, positive = the layer has the lower
log loss (better); 95% intervals over four-week blocks.

    ./python.sh src/eda/pair_strength/deploy.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.eda.pair_strength import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402

FIT_FROM = 2014
LEVEL_GROUPS = {"GS": ("GS", "FIN"), "T1000": ("T1000",), "T500": ("T500",), "T250": ("T250",)}


def raw_columns(F: pd.DataFrame) -> dict[str, np.ndarray]:
    return {"elo_sum": F["pr_elo_sum"].to_numpy(float) / 1000.0 - 4.4,
            "lrank_sum": F["pr_lrank_sum"].to_numpy(float),
            "ttt_sum": F["pr_ttt_sum"].to_numpy(float)}


def design(F: pd.DataFrame, rows: np.ndarray, eta: np.ndarray, spec: str, train: np.ndarray) -> np.ndarray:
    """The layer's columns for the given rows; constants (quantile edges) from the training rows only."""
    e = eta[rows]
    tour = F["tour"].to_numpy()[rows]
    lv = F["level"].astype(str).to_numpy()[rows]
    raw = {k: np.nan_to_num(v[rows], nan=np.nanmedian(v[train])) for k, v in raw_columns(F).items()}
    per_tour = lambda v: [np.where(tour == t, v, 0.0) for t in C.TOURS]  # noqa: E731
    cols = []
    if spec.startswith("level"):
        for t in C.TOURS:
            for g, members in LEVEL_GROUPS.items():
                cols.append(np.where((tour == t) & np.isin(lv, members), e, 0.0))
    else:
        cols += per_tour(e)
    if spec in ("lin", "level_lin", "mset_lin", "quad"):
        cols += per_tour(raw["elo_sum"] * e)
    if spec == "quad":
        cols += per_tour(raw["elo_sum"] ** 2 * e)
    if spec == "lin_pooled":
        cols.append(raw["elo_sum"] * e)
    if spec == "q1":
        s_all = F["pr_elo_sum"].to_numpy(float)
        t_all = F["tour"].to_numpy()
        q = np.zeros(rows.sum())
        for t in C.TOURS:
            edge = np.nanquantile(s_all[train & (t_all == t)], 0.2)
            q = np.where((tour == t) & (F["pr_elo_sum"].to_numpy(float)[rows] <= edge), 1.0, q)
        cols += per_tour(q * e)
    if spec == "lrank":
        cols += per_tour(raw["lrank_sum"] * e)
    if spec == "ttt":
        cols += per_tour(raw["ttt_sum"] * e)
    if spec.startswith("mset"):
        cols += per_tour(e ** 3 / 10.0) + per_tour(e * np.abs(e))
    return np.column_stack(cols)


def walk_forward(F: pd.DataFrame, eta: np.ndarray, spec: str, first: int = 2015, last: int = 2024,
                 fit_from: int = FIT_FROM) -> tuple[np.ndarray, dict]:
    season = F["season"].to_numpy()
    y = F["a_won"].to_numpy(float)
    p = np.full(len(F), np.nan)
    coefs = {}
    for Y in range(first, last + 1):
        train = (season >= fit_from) & (season < Y)
        test = season == Y
        if not test.any():
            continue
        beta, _, _ = S.fit(design(F, train, eta, spec, train), y[train])
        p[test] = expit(design(F, test, eta, spec, train) @ beta)
        coefs[Y] = [float(b) for b in beta]
    return p, coefs


def gains(F: pd.DataFrame, pa: np.ndarray, pb: np.ndarray, rows: np.ndarray) -> dict:
    ok = rows & np.isfinite(pa) & np.isfinite(pb)
    yb = F["a_won"].to_numpy(bool)[ok]
    c = C.compare(C.ll(pa[ok], yb), C.ll(pb[ok], yb), F.loc[ok, "tournament_date"].to_numpy())
    return {"n": int(c["n"]), "gain": float(c["gain"]), "lo": float(c["lo"]), "hi": float(c["hi"])}


SPECS = ("lin", "lin_pooled", "q1", "quad", "level", "level_lin", "lrank", "ttt", "mset", "mset_lin")


def main() -> int:
    warnings.simplefilter("ignore")
    F = C.dev_frame()
    season, tour = F["season"].to_numpy(), F["tour"].to_numpy()
    out = {}
    for base, col in (("model", "z_model"), ("market", "z_market")):
        eta = F[col].to_numpy(float)
        p14, c14 = walk_forward(F, eta, "B14")
        p19, _ = walk_forward(F, eta, "B14", first=2020, fit_from=2019)
        res = {"B14_coefs": c14, "B19_vs_B14": {}}
        subsets = {"2015-2024": season >= 2015, "2015-2021": (season >= 2015) & (season <= 2021),
                   "2022-2024": season >= 2022, "2020-2024": season >= 2020,
                   "atp 2015-2024": (season >= 2015) & (tour == "atp"),
                   "wta 2015-2024": (season >= 2015) & (tour == "wta")}
        res["B19_vs_B14"] = gains(F, p19, p14, season >= 2020)
        for spec in SPECS:
            p, coefs = walk_forward(F, eta, spec)
            res[spec] = {"vs_B14": {k: gains(F, p14, p, m) for k, m in subsets.items()},
                         "vs_B19_2020_2024": gains(F, p19, p, season >= 2020),
                         "coefs_last": coefs.get(2024)}
            C.log(f"{base} {spec}: vs B14 2015-2024 {res[spec]['vs_B14']['2015-2024']['gain']:+.3f} "
                  f"[{res[spec]['vs_B14']['2015-2024']['lo']:+.3f}, {res[spec]['vs_B14']['2015-2024']['hi']:+.3f}]; "
                  f"2022-2024 {res[spec]['vs_B14']['2022-2024']['gain']:+.3f}")
        out[base] = res
    out["key"] = ("gains in mLL per match, positive = the named layer has the lower log loss than B14 (or B19); 95% "
                  "intervals over four-week blocks; spanning 0 = tie")
    C.write_json(C.OUT / "deploy.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

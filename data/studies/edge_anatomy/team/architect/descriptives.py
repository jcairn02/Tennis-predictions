"""Architect memo (edge_anatomy, round 1): outcome-free descriptives of the current instance.

Reads NO result column (a_won is never loaded) and nothing dated from 29 Jul 2026 (the proposed sealed holdout):
    * matches per tour and season (all, non-debut), the odds input's source;
    * w = p(1 - p) of the margin-free odds input (the weight that turns log-odds moves into log loss);
    * the stage-1 forecast (16-seed mean, symmetrised, uncalibrated) against the odds input, by tour and season:
        - d = logit(model) - logit(price): its SD (how far the model moves away from the price);
        - the OLS slope of logit(model) on logit(price) and the SD of the part not linear in the price;
    * seed jitter: the SD across the 16 seeds of a match's log-odds (RMS over matches), and what remains in a
      4-seed and a 16-seed mean.
Run: ./python.sh data/studies/edge_anatomy/team/architect/descriptives.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[5]
INST = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10"
OUT = Path(__file__).resolve().parent / "descriptives.txt"
CUT = pd.Timestamp("2026-07-28")
EPS = 1e-6


def lg(p):
    return logit(np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS))


def main() -> None:
    cols = ["match_id", "tour", "season", "tournament_date", "p_mkt", "debut_season", "odds_input"]
    f = pd.read_parquet(INST / "model_frame.parquet", columns=cols)
    assert "a_won" not in f.columns
    f = f[f["tournament_date"] <= CUT].copy()
    f["match_id"] = f["match_id"].astype(str)
    lines = []
    lines.append("Matches per tour and season (frame rows, tournament date <= 28 Jul 2026; non-debut in brackets)")
    cnt = f.groupby(["season", "tour"]).agg(n=("match_id", "size"), nd=("debut_season", lambda s: int((~s).sum())))
    tab = cnt.unstack("tour")
    lines.append(tab.to_string())
    lines.append("")
    lines.append("Odds input source by season (share of rows)")
    src = pd.crosstab(f["season"], f["odds_input"], normalize="index").round(3)
    lines.append(src.loc[2019:].to_string())
    lines.append("")
    f["w"] = f["p_mkt"] * (1 - f["p_mkt"])
    lines.append("Mean w = p(1-p) of the odds input, by tour, 2020 - 28 Jul 2026: "
                 + ", ".join(f"{t} {f.loc[(f['tour'] == t) & (f['season'] >= 2020), 'w'].mean():.4f}"
                             for t in ("atp", "wta")))
    lines.append("")
    # stage-1 forecasts, seeds 0-15
    per_season = []
    for season in range(2019, 2027):
        mats = []
        ids0 = None
        for k in range(16):
            path = INST / "fits" / f"model__{season}__seed{k}.npz"
            with np.load(path, allow_pickle=False) as z:
                p, ids = z["p_td"], z["ids_td"].astype(str)
            n = len(ids)
            ps = 0.5 * (p[:n] + 1.0 - p[n:])
            if ids0 is None:
                ids0 = ids
            elif not np.array_equal(ids0, ids):
                raise RuntimeError(f"{season} seed {k}: ids differ")
            mats.append(ps)
        P = pd.DataFrame(np.column_stack(mats), index=ids0)
        per_season.append(P)
    P = pd.concat(per_season)
    P = P[~P.index.duplicated()]
    g = f.set_index("match_id").loc[lambda d: d["season"] >= 2019]
    g = g.join(P, how="inner")
    seedcols = list(range(16))
    eta_k = lg(g[seedcols].to_numpy())
    eta = lg(g[seedcols].mean(axis=1).to_numpy())
    c = lg(g["p_mkt"].to_numpy())
    g["d"] = eta - c
    g["eta"] = eta
    g["c"] = c
    g["jit"] = eta_k.std(axis=1, ddof=1)
    rows = []
    for (season, tour), h in g.groupby(["season", "tour"]):
        h = h[~h["debut_season"]]
        if len(h) < 50:
            continue
        X = np.column_stack([np.ones(len(h)), h["c"]])
        beta = np.linalg.lstsq(X, h["eta"].to_numpy(), rcond=None)[0]
        resid = h["eta"].to_numpy() - X @ beta
        rms_jit = float(np.sqrt(np.mean(h["jit"] ** 2)))
        rows.append({"season": season, "tour": tour, "n": len(h), "sd_d": h["d"].std(),
                     "mean_abs_d": h["d"].abs().mean(), "slope_eta_on_c": beta[1], "sd_perp": resid.std(),
                     "seed_sd_1": rms_jit, "seed_sd_4": rms_jit / 2, "seed_sd_16": rms_jit / 4,
                     "sd_c": h["c"].std(), "w": h["w"].mean()})
    R = pd.DataFrame(rows)
    lines.append("Stage-1 forecast (16-seed mean, uncalibrated) against the odds input, non-debut, by season and tour")
    lines.append("sd_d = SD of logit(model) - logit(price); slope = OLS slope of logit(model) on logit(price); "
                 "sd_perp = SD of the part of logit(model) not linear in logit(price); seed_sd_k = RMS seed noise "
                 "left in a k-seed mean (log-odds)")
    lines.append(R.round(4).to_string(index=False))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

"""R1 design look of the integration strategist: the power of the expanding-window test on 2024-2026, by Monte Carlo
on SYNTHETIC outcomes. No match result is read anywhere.

What is real here (counts and structure only, allowed by brief 2.1): the men's model-frame matches of 2024-2026 per
season (debut seasons out) and their four-week blocks; the empirical distribution of the base's men's log-odds
(16-seed means, 2019-2023 forecasts); the base's seed noise (strategist_noise.json). Everything else is assumed and
stated in ASSUMED below.

The synthetic world. Each match has true log-odds eta + beta * (xA - xB), with xA, xB ~ N(0, VAR_X / 2) (so the
registered two-sided x_std has variance VAR_X), observed per side with the season's coverage. The forecasts compared:
    B    the base: eta + seed noise of a K_SEEDS mean
    A    a TabPFN column arm that applies a share c ("capture") of the observed term: eta + c beta x_obs + seed noise
         (+ structural noise on rows with a value)
    F    the walk-forward nudge: eta + b_Y x_obs, b_Y ~ N(beta, SE_Y^2), SE_Y from the training seasons' coverage
    x_obs    "bayes": xA - xB with a missing side counted at its prior mean 0 (both, or one side, observed);
             "registered": xA - xB only where both sides are observed (the point-sequence statistic), else nothing
Tests (95%, two-sided; "power" = the interval lies above 0):
    primary    paired mLL gain of A over B, four-week-block t interval (G - 1 df), with the project's seed variance
               added (surface-IOS convention) and without it
    nudge      paired mLL gain of F over B (same base forecasts: no seed term)
    info       the coefficient b of x_obs given the base (offset), block-clustered: the information test

Writes data/studies/serve_speed_tabpfn/design/strategist_power.csv and .json.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/strategist_power.py
"""
from __future__ import annotations

import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import common as T  # noqa: E402

OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "design"
MODEL_FRAME = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"
FI = ROOT / "data" / "studies" / "feature_interactions" / "local"
RACE = ROOT / "data" / "studies" / "surface_rating_race" / "local"

# ASSUMED (inferred; stated in the design note)
VAR_X = 0.92                 # variance of the registered x_std on men <= 2023 (strategist_redundancy.json: 0.9216)
SEED_SD_1 = 0.0192           # per-match SD of one seed's log-odds around the seed mean (strategist_noise.json)
K_SEEDS = 16                 # seeds per arm in the scored seasons
COVER = {                    # P(both sides observed), P(exactly one side observed), per test season (men)
    2024: (0.61, 0.24),      # both: acquisition N2 1,656 / 2,718; one-only: held 2024 data, 2,206 vs 1,429 (x 1.54)
    2025: (0.50, 0.28),      # both: N2 1,324 / 2,659; one-only assumed at the 2022-2024 ratio
    2026: (0.56, 0.26),      # both: N2 1,266 / 2,266
}
SE_TRAIN = {                 # walk-forward nudge: SE of b_Y from 2019 .. Y-1, 1 / sqrt(P1MP * VAR_X * n_eff), n_eff =
    # matches with both sides + half of those with one side (N2 counts 2021-2025, held one-side counts 2019-2023)
    "bayes": {2024: 0.036, 2025: 0.030, 2026: 0.027},          # n_eff 4,216 / 6,193 / 7,884
    "registered": {2024: 0.043, 2025: 0.034, 2026: 0.030},     # n 3,102 / 4,758 / 6,082
}
P1MP = 0.194                 # mean p(1 - p) of the men's base forecast (strategist_noise.json)
REPS = 2000
RNG = np.random.default_rng(20261007)


def template() -> pd.DataFrame:
    f = pd.read_parquet(MODEL_FRAME, columns=["match_id", "tour", "season", "tournament_date", "debut_season"],
                        filters=[("season", ">=", 2024)])
    assert "a_won" not in f.columns
    f = f[(f["tour"] == "atp") & ~f["debut_season"].astype(bool)].copy()
    f["block"] = T.blocks(f["tournament_date"].to_numpy(), 28)
    return f.sort_values("block").reset_index(drop=True)


def base_eta_pool() -> np.ndarray:
    """Men's base log-odds (16-seed means of the symmetrised forecasts, 2019-2023): forecasts only."""
    out = []
    for s in range(2019, 2024):
        per = []
        for k in range(16):
            p = FI / f"model__{s}__seed{k}.npz"
            p = p if p.exists() else RACE / f"model__{s}__seed{k}.npz"
            with np.load(p, allow_pickle=False) as z:
                pr, ids = z["p_td"], z["ids_td"].astype(str)
            n = len(ids)
            per.append(pd.Series(0.5 * (pr[:n] + 1 - pr[n:]), index=ids))
        m = pd.concat(per, axis=1).mean(axis=1)
        m = m[m.index.str.startswith("atp")]
        out.append(np.log(m / (1 - m)).to_numpy())
    return np.concatenate(out)


def block_se(D: np.ndarray, starts: np.ndarray) -> np.ndarray:
    """Cluster-sandwich SE of the row mean of D (reps x n, rows sorted by block), as T.paired_interval."""
    n, G = D.shape[1], len(starts)
    mean = D.mean(axis=1, keepdims=True)
    infl = np.add.reduceat(D - mean, starts, axis=1)
    return np.sqrt(G / (G - 1) * (infl ** 2).sum(axis=1)) / n


def ll(eta: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.logaddexp(0.0, eta) - y * eta          # -log p(y) for logit eta


def simulate(tpl: pd.DataFrame, pool: np.ndarray, beta: float, cap: float, struct: float, xmode: str,
             seasons=(2024, 2025, 2026), reps: int = REPS, chunk: int = 250) -> dict:
    g = tpl[tpl["season"].isin(seasons)].reset_index(drop=True)
    n = len(g)
    starts = np.flatnonzero(np.r_[True, g["block"].to_numpy()[1:] != g["block"].to_numpy()[:-1]])
    G = len(starts)
    tq = student_t.ppf(0.975, G - 1)
    season = g["season"].to_numpy()
    pb = np.array([COVER[s][0] for s in season])
    p1 = np.array([COVER[s][1] for s in season])
    se_seed = np.sqrt(2 / K_SEEDS * P1MP * SEED_SD_1 ** 2 / n)        # the convention's seed term, nats
    res = {k: [] for k in ("gain_A", "lo_A", "lo_A_noseed", "gain_F", "lo_F", "b", "lo_b", "hi_b", "gain_oracle")}
    done = 0
    while done < reps:
        r = min(chunk, reps - done)
        eta = RNG.choice(pool, size=(r, n))
        xa = RNG.normal(0, np.sqrt(VAR_X / 2), (r, n))
        xb = RNG.normal(0, np.sqrt(VAR_X / 2), (r, n))
        u = RNG.random((r, n))
        both, one = u < pb, (u >= pb) & (u < pb + p1)
        side_a = RNG.random((r, n)) < 0.5
        if xmode == "bayes":
            xo = np.where(both, xa - xb, np.where(one, np.where(side_a, xa, -xb), 0.0))
        else:
            xo = np.where(both, xa - xb, 0.0)
        y = (RNG.random((r, n)) < expit(eta + beta * (xa - xb))).astype(float)
        has = xo != 0
        eb = eta + RNG.normal(0, SEED_SD_1 / np.sqrt(K_SEEDS), (r, n))
        ea = (eta + cap * beta * xo + RNG.normal(0, SEED_SD_1 / np.sqrt(K_SEEDS), (r, n))
              + struct * RNG.normal(0, 1, (r, n)) * has)
        bY = np.array([[RNG.normal(beta, SE_TRAIN[xmode][s]) for s in seasons] for _ in range(r)])
        bmap = {s: i for i, s in enumerate(seasons)}
        ef = eb + bY[:, [bmap[s] for s in season]] * xo
        lb = ll(eb, y)
        for name, e in (("A", ea), ("F", ef)):
            D = lb - ll(e, y)
            m = D.mean(axis=1)
            se = block_se(D, starts)
            res[f"gain_{name}"].append(1000 * m)
            if name == "A":
                res["lo_A"].append(1000 * (m - tq * np.sqrt(se ** 2 + se_seed ** 2)))
                res["lo_A_noseed"].append(1000 * (m - tq * se))
            else:
                res["lo_F"].append(1000 * (m - tq * se))
        res["gain_oracle"].append(1000 * (lb - ll(eb + beta * xo, y)).mean(axis=1))
        b = np.zeros(r)                                          # info test: offset logistic, one slope
        for _ in range(5):
            p = expit(eb + b[:, None] * xo)
            b += ((y - p) * xo).sum(1) / np.maximum((p * (1 - p) * xo ** 2).sum(1), 1e-12)
        p = expit(eb + b[:, None] * xo)
        info = (p * (1 - p) * xo ** 2).sum(1)
        S = np.add.reduceat((y - p) * xo, starts, axis=1)
        seb = np.sqrt(G / (G - 1) * (S ** 2).sum(1)) / info
        res["b"].append(b)
        res["lo_b"].append(b - tq * seb)
        res["hi_b"].append(b + tq * seb)
        done += r
    R = {k: np.concatenate(v) for k, v in res.items()}
    return {"beta": beta, "capture": cap, "struct": struct, "x": xmode, "seasons": f"{seasons[0]}-{seasons[-1]}",
            "matches": n, "blocks": G, "share_with_value": float(np.mean([COVER[s][0] + (COVER[s][1] if xmode == "bayes" else 0) for s in season])),
            "oracle_gain_mll": float(R["gain_oracle"].mean()),
            "A_gain_mean": float(R["gain_A"].mean()), "A_gain_sd": float(R["gain_A"].std()),
            "power_A_seedvar": float((R["lo_A"] > 0).mean()), "power_A_blockonly": float((R["lo_A_noseed"] > 0).mean()),
            "F_gain_mean": float(R["gain_F"].mean()), "F_gain_sd": float(R["gain_F"].std()),
            "power_F": float((R["lo_F"] > 0).mean()),
            "b_mean": float(R["b"].mean()), "b_sd": float(R["b"].std()),
            "power_info_two_sided": float(((R["lo_b"] > 0) | (R["hi_b"] < 0)).mean()),
            "power_info_positive": float((R["lo_b"] > 0).mean()),
            "se_seed_term_mll": float(1000 * se_seed)}


def main() -> int:
    tpl = template()
    pool = base_eta_pool()
    rows = []
    grid = list(product((0.0, 0.03, 0.05, 0.077, 0.09), (0.25, 0.5, 1.0), (0.0, 0.02), ("bayes", "registered")))
    for beta, cap, struct, xmode in grid:
        if beta == 0.0 and cap != 0.5:
            continue
        rows.append(simulate(tpl, pool, beta, cap, struct, xmode))
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
    for beta, cap in ((0.05, 0.5), (0.077, 0.5), (0.09, 0.5)):          # the blind seasons alone
        rows.append(simulate(tpl, pool, beta, cap, 0.0, "bayes", seasons=(2025, 2026)))
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
    R = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    R.to_csv(OUT / "strategist_power.csv", index=False)
    meta = {"rules": "synthetic outcomes only; real data: 2024-2026 men's match counts and four-week blocks, the base's "
                     "2019-2023 men's forecast distribution (forecasts only)", "reps": REPS,
            "assumed": {"VAR_X": VAR_X, "SEED_SD_1": SEED_SD_1, "K_SEEDS": K_SEEDS, "COVER": COVER,
                        "SE_TRAIN": SE_TRAIN, "P1MP": P1MP},
            "template": {"matches": int(len(tpl)), "by_season": tpl["season"].value_counts().sort_index().to_dict(),
                         "blocks": int(tpl["block"].nunique())},
            "eta_pool": {"n": int(len(pool)), "sd": float(pool.std())}}
    (OUT / "strategist_power.json").write_text(json.dumps(meta, indent=1, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

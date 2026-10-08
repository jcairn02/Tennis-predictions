"""Audit scratch: dry-run score.py's loading and comparison logic on SYNTHETIC predictions written to a scratch receipt
folder (guard.canonical_root is monkeypatched; nothing is written under data/studies/surface_elo_pieces/tabpfn and
score.main, which writes results files, is not called).

Checks:
  1. a missing seed job silently removes that season from the arm's seed-averaged forecast, and the pooled primary
     comparison is then computed on fewer seasons without any warning;
  2. the pilot's pooled 'primary vs base' compares one primary seed with the mean of two base seeds;
  3. market_recalibrated matches an independent per-tour, per-fold slope fit;
  4. symmetrisation orientation.

Run: ./python.sh data/studies/surface_elo_pieces/audit_scratch/score_dryrun.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.surface_elo_pieces import guard as G  # noqa: E402
from src.eda.surface_elo_pieces import score as S  # noqa: E402

OUT = Path(__file__).resolve().parent
FAKE = OUT / "fake_tabpfn"
FAKE.mkdir(exist_ok=True)
G.canonical_root = lambda: FAKE           # score.load reads G.canonical_root()
rng = np.random.default_rng(5)
frame = pd.read_parquet(C.OUT / "frame.parquet")
jobs = json.loads((C.OUT / "jobs.json").read_text(encoding="utf-8"))
res = {}


def write_fake(j, drop=False):
    d = FAKE / j["job"]
    d.mkdir(exist_ok=True)
    path = d / "predictions.npz"
    if path.exists():
        path.unlink()                      # scratch only
    if drop:
        return
    g = frame[frame["season"] == j["season"]]
    o = g["x_odds_logit"].to_numpy()
    z = 1.09 * o + rng.normal(0, 0.05, len(o))              # orientation as stored
    z_flip = -1.09 * o + rng.normal(0, 0.05, len(o))        # P(A wins | swapped) = P(original B wins)
    pa = expit(np.r_[z, z_flip])
    proba = np.column_stack([1 - pa, pa])
    binding = G.binding_for(j, G.job_config(j["seed"]))
    np.savez(path, probabilities=proba, classes=np.array([0, 1]), metadata=np.asarray(json.dumps({})),
             binding=np.asarray(G._json(binding)))


# 1. confirm stage with ONE missing job (primary 2024 seed 2)
for j in jobs:
    if j["stage"] == "confirm":
        write_fake(j, drop=(j["job"] == "confirm__primary__2024__seed2"))
f, arms, seasons = S.load("confirm")
miss = f[f["season"] == 2024]
res["missing_seed_job"] = {
    "arms": arms, "seasons": seasons,
    "rows_2024": int(len(miss)),
    "p_primary_nan_in_2024": int(miss["p_primary"].isna().sum()),
    "p_primary_s0_present_in_2024": int(miss["p_primary_s0"].notna().sum()),
    "pooled_primary_vs_base_matches": int(S.compare(f, "base", "primary")["n"]),
    "all_confirm_matches": int(len(f)),
}
# 4. symmetrisation: p = mean(P(A|x), 1 - P(A|swapped x)); with the synthetic model above both halves agree in sign
res["symmetrised_vs_market_raw_corr"] = float(np.corrcoef(f["p_base_s0"], f["p_market_raw"])[0, 1])

# 3. market recalibration against an independent fit
ok = True
for season in seasons:
    g = frame[frame["season"] == season].reset_index(drop=True)
    mine = np.full(len(g), np.nan)
    for tour in ("atp", "wta"):
        tr = frame["season"].between(2013, season - 1) & frame["tour"].eq(tour)
        lr = LogisticRegression(C=np.inf, fit_intercept=False, tol=1e-12, max_iter=1000)
        lr.fit(frame.loc[tr, ["x_odds_logit"]].to_numpy(), frame.loc[tr, "a_won"].astype(int).to_numpy())
        t = g["tour"].eq(tour).to_numpy()
        mine[t] = expit(lr.coef_[0, 0] * g.loc[t, "x_odds_logit"].to_numpy())
    theirs = f.loc[f["season"] == season, "p_market"].to_numpy()
    ok &= bool(np.allclose(mine, theirs, atol=1e-7))
res["market_recalibration_matches_independent_fit"] = ok

# 2. the pilot: arm forecasts and pairs
for j in jobs:
    if j["stage"] == "pilot":
        write_fake(j)
fp, arms_p, seasons_p = S.load("pilot")
seed_cols = sorted((mm.group(1), int(mm.group(2))) for c in fp.columns if (mm := S.SEED_COL.match(c)))
res["pilot"] = {"arms": arms_p, "seed_columns": seed_cols,
                "p_base_is_mean_of": [c for c in fp.columns if c.startswith("p_base_s")],
                "p_primary_is_mean_of": [c for c in fp.columns if c.startswith("p_primary_s")]}
print(json.dumps(res, indent=1))
(OUT / "score_dryrun.json").write_text(json.dumps(res, indent=1))

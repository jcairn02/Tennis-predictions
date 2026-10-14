"""Design scratch (agent 2): is the speed state already in the model's inputs or in the closing price? Seasons
2022-2023 only (a price look, logged). Feature-on-feature regressions; no result column is read (a_won is not loaded).

For each candidate column (spd_f, spd_dev, x_raw where present), on men's model-frame matches of 2022-2023:
    R2 on the 58 model inputs (diffs and pairs as they are, context inputs one-hot), OLS
    R2 on in_odds_logit alone (the closing price), and on the inputs without the odds
A low R2 says the column is information the model (and the price) does not already carry linearly.

Run: ./python.sh src/eda/serve_speed_tabpfn/design/modeller_redundancy.py
Writes data/studies/serve_speed_tabpfn/design/modeller_redundancy.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import modeller_common as M  # noqa: E402

CONTEXT = ["in_tour", "in_surface", "in_level", "in_indoor", "in_best_of", "in_round"]


def r2(X: np.ndarray, y: np.ndarray) -> float:
    X = np.column_stack([np.ones(len(y)), X])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(1 - ((y - X @ b) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def main() -> None:
    cols = [c for c in pd.read_parquet(M.FRAME).columns if c.startswith("in_")]
    f = pd.read_parquet(M.FRAME, columns=["match_id", "tour", "season"] + cols, filters=[("season", ">=", 2022),
                                                                                       ("season", "<=", 2023)])
    feats = pd.read_parquet(M.OUT / "modeller_features_ks_first.parquet", columns=["match_id", "spd_f", "spd_dev", "x_raw"])
    f = f.merge(feats, on="match_id", how="inner")
    out = {"seasons": [2022, 2023], "inputs": len(cols)}
    for tour, g in f.groupby("tour"):
        num = [c for c in cols if c not in CONTEXT]
        X = g[num].fillna(0.0).to_numpy(float)
        D = pd.get_dummies(g[[c for c in CONTEXT if c != "in_tour"]].astype(str), drop_first=True).to_numpy(float)
        Xa = np.column_stack([X, D])
        no_odds = [c for c in num if c != "in_odds_logit"]
        Xn = np.column_stack([g[no_odds].fillna(0.0).to_numpy(float), D])
        res = {}
        for name in ("spd_f", "spd_dev", "x_raw"):
            m = g[name].notna().to_numpy()
            y = g[name].to_numpy(float)[m]
            res[name] = {"rows": int(m.sum()), "r2_all_inputs": r2(Xa[m], y), "r2_inputs_without_odds": r2(Xn[m], y),
                         "r2_odds_only": r2(g["in_odds_logit"].to_numpy(float)[m][:, None], y),
                         "corr_odds": float(np.corrcoef(g["in_odds_logit"].to_numpy(float)[m], y)[0, 1])}
        out[tour] = res
        M.log(f"{tour}: {res}")
    (M.OUT / "modeller_redundancy.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

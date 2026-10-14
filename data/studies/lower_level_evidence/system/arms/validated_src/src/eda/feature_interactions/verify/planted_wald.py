"""Harness verifier, task 2 (Wald path): planted effects on real column blocks with SYNTHETIC outcomes, through
screen.run_wald; at beta = 0 also the Wald statistic under each clustered covariance (the harness picks one by trace).

    KN-SDEV   the known-null set's 8-column block (surface deviations); no controls (as the batch's P3 runs it)
    S2        [S-IOS, S-AGE] with controls in_iosD_hold, in_sets_14d and miss x eta
The planted direction is the equal-weight sum of the standardised columns. Real results are never used.

Run: ./python.sh src/eda/feature_interactions/verify/planted_wald.py --deltas 0,0.2 --draws 100 [--tag name]
Writes data/studies/feature_interactions/verify/wald_<tag>.parquet
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.feature_interactions.verify import simlib as V  # noqa: E402
from src.eda.feature_interactions.verify.cols import load_cols  # noqa: E402


def blocks(F, K):
    X8 = K[[f"KN-SDEV#{j}" for j in range(8)]].to_numpy(float)
    X2 = K[["S-IOS", "S-AGE"]].to_numpy(float)
    miss = ~np.isfinite(X2).all(axis=1)
    C2 = np.column_stack([F["in_iosD_hold"], F["in_sets_14d"], miss * F["z_model"].to_numpy(float)])
    return {"KN-SDEV": (X8, None), "S2": (X2, C2)}


def preprocess(F, X, controls):
    """As run_wald: each column through prepare; the controls' scaling with the first column."""
    Xs = np.empty_like(X)
    for j in range(X.shape[1]):
        Xs[:, j], _, prep = S.prepare(F, S.Hypothesis("w", X[:, j], None), "model")
    _, Cs, prep = S.prepare(F, S.Hypothesis("w", X[:, 0], controls), "model")
    return Xs, Cs, prep


def wald_three(F, rows, Xs, Cs, prep) -> dict:
    """b' V^-1 b under the model-based, block, player and union covariances (coef_test_multi's own algebra)."""
    N = S.nuisance(F, rows, "model", True, prep)
    Z = np.column_stack([N] + ([Cs[rows]] if Cs is not None else []) + [Xs[rows]])
    y = F["a_won"].to_numpy(float)[rows]
    beta, p, H = S.fit(Z, y)
    k = Xs.shape[1]
    J = np.arange(Z.shape[1] - k, Z.shape[1])
    A = np.linalg.solve(H, np.eye(Z.shape[1])[:, J])
    U = (y - p)[:, None] * (Z @ A)
    covs = S.clustered_cov(U, F["block"].to_numpy()[rows], F["player_a_id"].to_numpy(str)[rows],
                           F["player_b_id"].to_numpy(str)[rows])
    b = beta[J]
    out = {f"W_{n}": float(b @ np.linalg.solve(Vm, b)) for n, Vm in covs.items()}
    out["W_model"] = float(b @ np.linalg.solve(A[J], b))
    out["trace_pick"] = max(covs, key=lambda n: np.trace(covs[n]))
    out["union_min_eig"] = float(np.linalg.eigvalsh(covs["union"]).min())
    return out


def main() -> int:
    warnings.simplefilter("ignore")
    arg = lambda n, d: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d  # noqa: E731
    deltas = [float(d) for d in arg("--deltas", "0,0.1,0.2,0.3").split(",")]
    draws, tag = int(arg("--draws", 100)), arg("--tag", "main")
    F = S.load(with_model=True)
    F["a_won"] = False                                     # the real results are never used below
    K = load_cols()
    base = V.base_logit(F)
    rng = np.random.default_rng(31)
    rows, path = [], C.OUT / "verify" / f"wald_{tag}.parquet"
    allw = np.ones(len(F), bool)
    for name, (X, controls) in blocks(F, K).items():
        Xs, Cs, prep = preprocess(F, X, controls)
        x0 = V.std_disc(F, sum(V.std_disc(F, X[:, j]) for j in range(X.shape[1])))
        for delta in deltas:
            beta, g = (V.calibrate(F, x0, delta, Cs, prep) if delta > 0 else
                       (0.0, {"discovery": 0.0, "replication": 0.0, "pooled": 0.0}))
            C.log(f"{name} delta {delta}: beta {beta:.4f}, pooled gain {1000 * g['pooled']:.3f} mLL")
            for d in range(draws):
                F["a_won"] = V.draw(F, base + beta * x0, rng)
                r = S.run_wald(F, name, X, controls, n_p1=0)
                rec = {"block": name, "k": X.shape[1], "delta": delta, "beta": beta, "draw": d,
                       "gain_disc": 1000 * g["discovery"], "gain_rep": 1000 * g["replication"],
                       "gain_pooled": 1000 * g["pooled"], **{k: r[k] for k in ("W1", "p1", "W_joint", "p_joint",
                                                                           "z_rep_along_disc", "filter_pass",
                                                                           "replicates", "n1", "n2")}}
                rec.update(wald_three(F, allw, Xs, Cs, prep))          # every delta: the fix's power too
                rows.append(rec)
            pd.DataFrame(rows).to_parquet(path, index=False)
    C.log(f"written {path.name}: {len(rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())

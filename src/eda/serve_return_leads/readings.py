"""The serve/return-leads study's one way to read a candidate against results: seen matches only.

Every outcome this study's diagnostics read passes through `seen_frame()` (common.seen: tournament date before
29 Jul 2026, the registered loader's guards on). A candidate is an A - B value aligned to the frame's rows (NaN = no
information, counted 0).

    read(frame, x, name, sign)   per window (eras 2013-16, 2017-19, 2020-22, 2023-24; 2013-24; 2020-24; 2025-26 =
                                 1 Jan 2025 - 28 Jul 2026), per form (raw; orth = minus its least-squares projection on
                                 the model's 48 non-price, non-context inputs, fitted on the window's own rows, by tour,
                                 no intercept) and per base (L = the close's log-odds; L_model = the current model's
                                 both-stages forecast, 2020 - 28 Jul 2026 only): beta per RMS of the oriented value,
                                 its SE, z, one-sided p (t on G - 1), P(beta > 0). + = the oriented direction holds.
    fit_joint(frame, S, base)    several oriented scores at once beyond the base (the decomposition), the same base
                                 terms and clusters as unpriced leads' look.fit
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_return_leads import common as C  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

WINDOWS = {"2013-16": (2013, 2016), "2017-19": (2017, 2019), "2020-22": (2020, 2022), "2023-24": (2023, 2024),
           "2013-24": (2013, 2024), "2020-24": (2020, 2024), "2025-26": (2025, 2026)}
_FRAME: dict = {}


def seen_frame(tour: str = "atp") -> pd.DataFrame:
    if tour not in _FRAME:
        f = C.seen(tour)
        st = pd.read_parquet(H.STAGE0_M, columns=["match_id", "player_a_id", "player_b_id"]).astype({"match_id": str})
        f = f.merge(st.drop_duplicates("match_id"), on="match_id", how="left", validate="one_to_one")
        _FRAME[tour] = f
    return _FRAME[tour]


def _clean(x) -> np.ndarray:
    x = np.asarray(x, float)
    return np.where(np.isfinite(x), x, 0.0)


def read(frame: pd.DataFrame, x, name: str, sign: int = +1, forms=("raw", "orth"), bases=("L", "L_model"),
         windows=None) -> pd.DataFrame:
    x = np.asarray(x, float) * sign
    rows = []
    for w, (a, b) in (windows or WINDOWS).items():
        m = frame["season"].between(a, b).to_numpy()
        g = frame[m].reset_index(drop=True)
        xm = x[m]
        present = float(np.mean(np.isfinite(xm) & (xm != 0)))
        for form in forms:
            if form == "orth":
                xo, _ = H.orthogonal_part(g, xm)
                xs = _clean(xo)
            else:
                xs = _clean(xm)
            for base in bases:
                if not np.isfinite(g[base].to_numpy(float)).any():
                    continue
                r = C.fit(g, xs, base=base)
                rows.append({"candidate": name, "sign": sign, "window": w, "form": form, "base": base,
                             "beta": r["beta"], "se": r["se"], "z": r["z"], "p_one_sided": r["p_one_sided"],
                             "p_beta_positive": r["p_beta_positive"], "n": r["n"], "blocks": r["blocks"],
                             "present": present})
    return pd.DataFrame(rows)


def fit_joint(frame: pd.DataFrame, S: np.ndarray, base: str = "L", names: list[str] | None = None) -> pd.DataFrame:
    """Oriented scores (columns of S, each scaled to unit RMS in the rows fitted) jointly beyond the base."""
    ok = np.isfinite(frame[base].to_numpy(float))
    g = frame[ok]
    S = np.column_stack([_clean(c) for c in np.asarray(S, float).T])[ok]
    rms = np.sqrt(np.mean(S ** 2, axis=0))
    S = S / np.where(rms > 0, rms, 1.0)
    y, blk, tour = g["y"].to_numpy(float), g["block"].to_numpy(), g["tour"].to_numpy()
    Lb = g[base].to_numpy(float)
    B = np.column_stack([H.tour_slope_cols(tour, Lb), H.tour_slope_cols(tour, Lb * np.abs(Lb))])
    B = B[:, np.abs(B).sum(axis=0) > 0]
    Z = np.column_stack([B, S])
    zero = np.zeros(len(y))
    b1, H1 = H.fit_offset(Z, y, zero, ridge=1e-6)
    V = H.cluster_cov(Z, y, zero, b1, H1, blk)
    G = int(len(np.unique(blk)))
    k = S.shape[1]
    out = []
    for j in range(k):
        i = B.shape[1] + j
        se = float(np.sqrt(V[i, i]))
        z = float(b1[i] / se)
        out.append({"score": (names or [f"s{j}" for j in range(k)])[j], "beta": float(b1[i]), "se": se, "z": z,
                    "p_one_sided": float(student_t.sf(z, G - 1)), "p_beta_positive": float(student_t.cdf(z, G - 1)),
                    "n": int(len(y)), "blocks": G})
    return pd.DataFrame(out)

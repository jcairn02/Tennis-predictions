"""B-LEVER, the price's leverage by match structure (final family, round-2 rulings MAT-R3): I-001, I-006's format slope
and the surface-mean leverage kappa_surf, a Wald 3-df block of price slopes (x_times_eta: the batch forms each s_k * eta),
two-sided, weight 0.5, trait slow. Supersedes the round-1 stand-alones I-001 and I-006.

    s1  kappa_pair = beta_L(m_pair; format, rule) / beta_L(mu_cell; format, rule) - 1, centred within tour x surface on
        2014-2021 rows (within-cell dominance): m_pair = mu_spw + (O_A + O_B - D_A - D_B)/2 from the surface IOS
        (srf_O_eff_spw, srf_D_eff_spw; leak-proof, inherited), mu_cell the tour x surface spw average (stage4_constants,
        2010-2018), beta_L = d logit P(match) / d Delta at Delta = 0 under the iid model with the match's best-of and
        deciding-set rule (stage2_iid)
    s2  1[best of five] (men's Grand Slams here), centred within tour
    s3  kappa_surf = beta_L(mu_cell; format, rule) / beta_L(mu_tour; format, rule) - 1, mu_tour the tour's all-surface
        average, centred within tour: the between-cell part that I-001's former cell controls removed
Controls: the M-set (eta|eta| per tour), eta * 1[Grand Slam], the nearest inputs to each s_k * eta, and, fitted jointly
(final family), the other rows' modulators times eta, imported from the market analyst's f10_price_slopes so they are
exactly that module's columns: I-036's obscurity O and unranked flag, B-FLB's L = 1[not the event's first main-draw
round] and HP = 1[Grand Slam or Tour Finals] (joint_modulators). f10 in turn imports lever_columns' three modulators.
Deployment: nudge; TabPFN context form kappa_pair (S2's IOS sums span m_pair).
Constants: none tuned (h = 1e-3, a numerical step). Pre-declared sensitivities (not hypotheses): I-002's comp, I-011,
MEC-K2. Reads no result. Run (diagnostics): ./python.sh src/eda/feature_interactions/features/f02_leverage.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.features import f01_structure_lib as S  # noqa: E402

# nearest inputs to each s_k * eta_model on 2014-2021 rows (diagnostics; odds_logit excluded as the price base's offset):
# kappa_pair prod_bp_saved -0.116, iosD_second_won +0.115, prod_first_won -0.098; 1[bo5] ratings_iid +0.260,
# ios_points_short +0.204, points_52w +0.186; kappa_surf form_ace -0.085, iosO_first_won -0.074 (RMS kappa_surf 3.0%
# men, 1.1% women; kappa_pair 6.5% and 2.5%)
STD_LEVER = ("prod_bp_saved", "iosD_second_won", "prod_first_won", "ratings_iid", "ios_points_short", "points_52w")
STD_SURF = ("form_ace", "iosO_first_won")


def m_pair(P: pd.DataFrame) -> np.ndarray:
    return S.mu(P, "spw") + 0.5 * (S.ios(P, "srfO", "spw", "a") + S.ios(P, "srfO", "spw", "b")
                                   - S.ios(P, "srfD", "spw", "a") - S.ios(P, "srfD", "spw", "b"))


def kappa_pair(P: pd.DataFrame) -> np.ndarray:
    bo, r = S.num(P, "best_of"), S.rule(P)
    return S.leverage(m_pair(P), bo, r) / S.leverage(S.mu(P, "spw"), bo, r) - 1.0


def kappa_surf(P: pd.DataFrame) -> np.ndarray:
    bo, r = S.num(P, "best_of"), S.rule(P)
    mu_tour = S.mu(P, "spw", surface=np.full(len(P), "all", dtype=object))
    return S.leverage(S.mu(P, "spw"), bo, r) / S.leverage(mu_tour, bo, r) - 1.0


def bo5(P: pd.DataFrame) -> np.ndarray:
    return (S.num(P, "best_of") == 5).astype(float)


def joint_modulators(P: pd.DataFrame) -> np.ndarray:
    """The jointly fitted rows' modulators (final family: B-LEVER with B-FLB and I-036), taken from the market analyst's
    own functions in f10_price_slopes so the controls are exactly their columns: I-036's obscurity O and unranked flag,
    B-FLB's L (later round) and HP (Slam or Tour Finals), each as f10 centres or standardises them."""
    from src.eda.feature_interactions.features import f10_price_slopes as F10
    L_, HP = F10.flb_parts(P)
    return np.column_stack([F10.obscurity(P), F10.unranked_flag(P), L_, HP])


def lever_columns(P: pd.DataFrame) -> np.ndarray:
    return np.column_stack([S.centre_disc(P, kappa_pair(P), ("tour", "surface")), S.centre_disc(P, bo5(P), ("tour",)),
                            S.centre_disc(P, kappa_surf(P), ("tour",))])


def combine_lever(P: pd.DataFrame) -> dict:
    X = lever_columns(P)
    slam = S.centre_disc(P, (P["level"].astype(str) == "GS").to_numpy(float), ("tour",))
    E = np.nan_to_num(np.column_stack([slam[:, None], joint_modulators(P)]))
    Cm, names = S.pack([(f"in_{n}", S.num(P, f"in_{n}")) for n in STD_LEVER + STD_SURF])
    return {"x": X, "x_times_eta": True, "m_set": True, "eta_mod_controls": E, "controls": Cm, "control_names": names,
            "tabpfn": {"f02_kappa_pair": (X[:, 0], "context", None)}}


HYPOTHESES = [
    {"hid": "B-LEVER", "master": "I-001+I-006+kappa_surf", "kind": "M", "sign": "two", "weight": 0.5, "trait": "slow",
     "wald": True, "deployment": "nudge", "family": "01", "prepare": None, "combine": combine_lever},
]


def diagnostics(P: pd.DataFrame) -> dict:
    """Result-free: each modulator's RMS on 2014-2021 rows, the novelty of s * eta and s * z on the 58 inputs, the
    nearest inputs, the correlations among the three columns and with the joint-fit modulators."""
    X, d, atp = lever_columns(P), S.disc(P), S.is_atp(P)
    eta, z = S.num(P, "eta_model"), S.num(P, "in_odds_logit")
    out = {}
    for j, nm in enumerate(("kappa_pair", "bo5", "kappa_surf")):
        s = X[:, j]
        out[nm] = {"rms_disc": {"atp": float(np.sqrt(np.nanmean(s[d & atp] ** 2))),
                                "wta": float(np.sqrt(np.nanmean(s[d & ~atp] ** 2)))},
                   "novelty_r2_s_eta": S.r2_on_58(P, s * eta), "novelty_r2_s_z": S.r2_on_58(P, s * z),
                   "nearest_s_eta": S.nearest(P, s * eta, 4)}
    out["corr_columns"] = np.round(np.corrcoef(np.nan_to_num(X[d]).T), 3).tolist()
    J = joint_modulators(P)
    out["corr_with_joint_modulators(O, unranked, L, HP)"] = np.round(
        np.corrcoef(np.nan_to_num(np.column_stack([X, J])[d]).T)[:3, 3:], 3).tolist()
    return out


if __name__ == "__main__":
    import json
    import warnings
    warnings.simplefilter("ignore")
    from src.eda.feature_interactions.panel import panel
    res = diagnostics(panel(max_season=2024))
    print(S.write_diag("f02_leverage", res))
    print(json.dumps(res, indent=1, default=str))

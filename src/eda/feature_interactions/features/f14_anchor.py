"""B-ANCHOR, artefacts of the average close [A] (math audit block; composite, weight 0.5, capped as [A]).

    I-037 dispersion (-)  a = 1 - (1/max_A + 1/max_B), the best prices' arbitrage margin (symmetric), centred per tour;
                          the member is a * eta (a price-slope term: its eta is the current best's, the model base)
    I-038 skew (+)        k = logit p_max(A) - odds_logit, p_max(A) = (1/max_A) / (1/max_A + 1/max_B); fam = 1[sign(k) =
                          -sign(dF)] (the skew points at the more famous player), the contrast k (2 fam - 1) as the
                          family writes it (equal fame gives fam = 0, so -k there; the tie-to-0 variant, -|k| sign(dF)
                          with 0 at equal fame, is a sensitivity)

Fame F = log(1 + main-tour titles + Slam quarter-finals or better), I-083's, from strictly earlier matches since 2010.
Outlier and incoherence rules (MKT-14 asks for them; fixed without results): a pair with a maximum below the average on
either side is incoherent (both members, so x, missing there: the batch adds the indicator x eta); a is winsorised at its 0.5% and
99.5% quantiles and k at +-(the 99.5% quantile of |k|), both on the 2014-2021 rows (symmetric clipping keeps k
antisymmetric). I-037's member depends on the base's eta: the block is returned as x_of_eta (the batch
evaluates it per base; each member standardised on the given rows' 2014-2021 part); x is its eta_model version.
Controls: k and dF (I-038's), the M-set, Std. Needs bookmaker quotes at bet time (max and average: OddsPortal via
tennis-data.co.uk, 100% of 2013-2024 rows; whether the maximum includes exchanges is unknown).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions.features import mkt_common as M


def prepare_fame(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = M.hist(L, P)
    fa, fb = M.at_model(H, P, M.fame(H))
    return {"fame_a": fa, "fame_b": fb}


def odds_parts(P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(a winsorised, k winsorised, incoherent flag)."""
    mxa, mxb, ava, avb = (M.num(P, c) for c in ("max_a", "max_b", "avg_a", "avg_b"))
    bad = ~(np.isfinite(mxa) & np.isfinite(mxb) & np.isfinite(ava) & np.isfinite(avb)) | (mxa < ava) | (mxb < avb)
    a = 1.0 - (1.0 / mxa + 1.0 / mxb)
    pmax = (1.0 / mxa) / (1.0 / mxa + 1.0 / mxb)
    k = np.log(pmax) - np.log1p(-pmax) - M.zmkt(P)
    a[bad], k[bad] = np.nan, np.nan
    d = M.disc(P)
    lo, hi = np.nanquantile(a[d], [0.005, 0.995])
    q = np.nanquantile(np.abs(k[d]), 0.995)
    return np.clip(a, lo, hi), np.clip(k, -q, q), bad.astype(float)


def contrast(P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(I-038's k (2 fam - 1), k, dF): fam = 1[sign(k) = -sign(dF)] literally (equal fame gives fam = 0)."""
    _, k, _ = odds_parts(P)
    dF = M.num(P, "fame_a") - M.num(P, "fame_b")
    fam = (np.sign(k) == -np.sign(dF)).astype(float)
    m38 = k * (2.0 * fam - 1.0)
    m38[~np.isfinite(dF)] = np.nan
    return m38, k, dF


def combine_banchor(P: pd.DataFrame) -> dict:
    a, _, _ = odds_parts(P)
    ac = M.centre(a, P)
    m38, k, dF = contrast(P)
    d = M.disc(P)

    def x_of_eta(e, rows):
        """The block for a base's eta: eta * a (-) and the contrast (+), each standardised on these rows' 2014-2021 part."""
        return M.signed_sum_masked([(ac[rows] * np.asarray(e, float), "-"), (m38[rows], "+")], d[rows], symmetric=False)
    allr = np.arange(len(P))
    x = x_of_eta(M.eta(P), allr)
    Cs, names = M.std_controls(P, x)
    ctrl, cn = M.stack([(np.nan_to_num(k), "k (best-price skew)"), (dF, "Delta fame")] + ([(Cs, names)] if names else []))
    # incoherent quotes leave both members (so x) missing: the batch's missing-indicator x eta is that control
    return {"x": x, "x_of_eta": x_of_eta, "x_market": x_of_eta(M.zmkt(P), allr), "m_set": True, "controls": ctrl,
            "control_names": cn, "members": {"I-037": ac * M.eta(P), "I-038": m38}, "tabpfn": {}}


HYPOTHESES = [
    {"hid": "B-ANCHOR", "master": "I-037+I-038", "kind": "M", "sign": "+", "weight": 0.5, "trait": "none",
     "deployment": "nudge", "anchor": "A", "prepare": prepare_fame, "combine": combine_banchor},
]

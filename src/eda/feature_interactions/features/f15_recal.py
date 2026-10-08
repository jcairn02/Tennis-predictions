"""B-RECAL, recalibrating the current best's own adjustment (math audit block; Wald, 2 df, weight 0.5).

adj = eta_model - odds_logit, the current best's out-of-sample adjustment to the price (antisymmetric; 2014 on).

    I-040 (+)  r_bar x adj: the context fixed by the math audit is I-032's evidence weight r_bar, the harmonic mean over
               the two players of n/(n + 20), n = surface matches rated (centred per tour on the 2014-2021 rows); the
               format context is dropped (W-12) and "adjustment size" is I-041
    I-041 (+-) adj^3: non-linear shrinkage (b3 < 0) or heavy tails (b3 > 0) of the adjustment

The block's x has the two columns (Wald, 2 df: I-041 is two-sided). Controls: adj (its own slope, the b0 term), the M-set
(eta, eta^3 and eta|eta| per tour; the screen's cubic is in eta, not in the adjustment, so adj^3 is not collinear) and
Std. A recalibration layer outside TabPFN (nudge); it corrects the model, not the market. The prequential kill test of
the originator reads results and belongs after M1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions.features import mkt_common as M


def combine_brecal(P: pd.DataFrame) -> dict:
    a = M.adj(P)
    c = M.centre(M.evidence_rbar(P), P)
    X = np.column_stack([c * a, a ** 3])
    C1, n1 = M.std_controls(P, c * a)
    C2, n2 = M.std_controls(P, a ** 3, exclude=tuple(n[3:] for n in n1))
    ctrl, cn = M.stack([(a, "adj (eta_model - odds_logit)")] + ([(C1, n1)] if n1 else []) + ([(C2, n2)] if n2 else []))
    return {"x": X, "m_set": True, "controls": ctrl, "control_names": cn,
            "members": {"I-040": c * a, "I-041": a ** 3}, "tabpfn": {}}


HYPOTHESES = [
    {"hid": "B-RECAL", "master": "I-040+I-041", "kind": "M", "sign": "two", "weight": 0.5, "trait": "none",
     "deployment": "nudge", "anchor": "", "wald": True, "prepare": None, "combine": combine_brecal},
]

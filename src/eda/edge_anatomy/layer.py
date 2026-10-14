"""The architect's first recommendation, tested walk-forward (edge-anatomy study, 12 Oct 2026; added after the first
results showed men's 2025-26 realisation 1.80): re-size each family's part of the model's disagreement with the close.

For each season Y in 2020-2026 and tour (no outcome read): the season's disagreement d = logit(stage 1, calibrated)
- logit(recalibrated close) is split by a least-squares surrogate on the input families (anatomy.design: price shape,
context, ratings, schedule, form, IOS; the rest unexplained); for men stage 2's speed offset is one more part.
Then (outcomes of earlier seasons only) the layer
    logit q' = logit q_final + sum_f delta_f d_f,   delta ~ N(0, 0.5^2) a priori (ridge 4: fixed before any result)
is fitted per tour on 2020 .. Y - 1 and applied to Y (from 2021). delta_f = k_f - 1: k_f is how far the family's part
should be scaled. Also the one-scale version (every part scaled together: the two-part recalibration of earlier studies).
Scored against the current model (q_final) and the recalibrated close; mLL, + = the layer better; four-week blocks;
debut seasons out.

Writes data/studies/edge_anatomy/layer_scores.csv and layer_coefficients.csv.
Run: ./python.sh src/eda/edge_anatomy/layer.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.edge_anatomy import anatomy as AN  # noqa: E402
from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.edge_anatomy import stats as S  # noqa: E402

PRIOR_SD = 0.5
SEASONS = tuple(range(2020, 2027))


def parts_by_season(df: pd.DataFrame) -> pd.DataFrame:
    """Per match: each family's part of the disagreement, from a surrogate fitted on its own season and tour."""
    out = []
    for (Y, tour), g in df.groupby(["season", "tour"]):
        g = g.reset_index(drop=True)
        Lc = S.lg(g["q_close"].to_numpy())
        d1 = S.lg(g["q_full_s1"].to_numpy()) - Lc
        des = AN.design(g)
        X = np.column_stack([des[k] for k in AN.GROUPS])
        b, _ = AN.ols(X, d1)
        rec = {"match_id": g["match_id"].to_numpy()}
        start = 0
        for k in AN.GROUPS:
            w = des[k].shape[1]
            rec[k] = des[k] @ b[start:start + w]
            start += w
        rec["rest"] = d1 - X @ b
        rec["speed"] = S.lg(g["q_full"].to_numpy()) - S.lg(g["q_full_s1"].to_numpy())
        out.append(pd.DataFrame(rec))
    return pd.concat(out).set_index("match_id")


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(E.OUT / "analysis.parquet")
    df = df[(df["season"] >= 2020) & ~df["debut"]].copy()
    parts = parts_by_season(df)
    df = df.set_index("match_id").join(parts)
    names = list(AN.GROUPS) + ["rest", "speed"]
    preds, coefs = [], []
    for tour in ("atp", "wta"):
        t = df[df["tour"] == tour]
        cols = names if tour == "atp" else [n for n in names if n != "speed"]
        for Y in SEASONS[1:]:
            tr, te = t[t["season"] < Y], t[t["season"] == Y]
            off_tr, off_te = S.lg(tr["q_full"].to_numpy()), S.lg(te["q_full"].to_numpy())
            y = tr["y"].to_numpy(float)
            Xf = tr[cols].to_numpy()
            dlt, _ = S.fit_offset(Xf, y, off_tr, ridge=1 / PRIOR_SD ** 2)
            Xone = tr[cols].sum(axis=1).to_numpy()[:, None]
            one, _ = S.fit_offset(Xone, y, off_tr, ridge=1 / PRIOR_SD ** 2)
            q_fam = expit(off_te + te[cols].to_numpy() @ dlt)
            q_one = expit(off_te + one[0] * te[cols].sum(axis=1).to_numpy())
            preds.append(pd.DataFrame({"match_id": te.index, "q_family_layer": q_fam, "q_one_scale": q_one}))
            coefs.append({"tour": tour, "season": Y, **{f"k_{c}": 1 + float(v) for c, v in zip(cols, dlt)},
                          "k_one_scale": 1 + float(one[0])})
    P = pd.concat(preds).set_index("match_id")
    df = df.join(P, how="inner")
    rows = []
    for label, seasons in (("2025-26", (2025, 2026)), ("2021-24", (2021, 2022, 2023, 2024)),
                           *((str(Y), (Y,)) for Y in SEASONS[1:])):
        for tour in ("both", "atp", "wta"):
            g = df[df["season"].isin(seasons)]
            if tour != "both":
                g = g[g["tour"] == tour]
            y, blk = g["y"].to_numpy(), g["block"].to_numpy()
            for arm in ("q_family_layer", "q_one_scale"):
                v = S.gain(g["q_full"], g[arm], y, blk)
                w = S.gain(g["q_close"], g[arm], y, blk)
                rows.append({"seasons": label, "tour": tour, "arm": arm, "n": int(len(g)),
                             **{f"vs_model_{k}": v[k] for k in ("est", "lo", "hi", "p_better")},
                             "vs_model_verdict": S.verdict(v),
                             **{f"vs_close_{k}": w[k] for k in ("est", "lo", "hi", "p_better")}})
    return pd.DataFrame(rows), pd.DataFrame(coefs)


def main() -> int:
    scores, coefs = run()
    scores.to_csv(E.OUT / "layer_scores.csv", index=False)
    coefs.to_csv(E.OUT / "layer_coefficients.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 100)
    print(scores.round(2).to_string(index=False))
    print(coefs.round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

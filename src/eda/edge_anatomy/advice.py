"""The professional's process, run walk-forward (the edge-anatomy study, added 12 Oct 2026 after the first results):
"identify what statistics predict the outcome that the most recent closing line is not pricing in; build a model
around that idea".

Selection never reads 2025-26. Each rule picks, per tour, the model's non-price inputs (and men's speed) whose
coefficient beyond the close (scan.py: one input at a time, the close with a free slope per tour, cluster-robust z) is
at least 2 in absolute value in its discovery window:
    decade     2013-2024 pooled (scan_learning.csv's inverse-variance pooled z over the four earlier eras)
    recent     2023-2024 alone (the era the "most recent closing line" reading points to)
    both       |z| >= 2 in the decade window and the same sign in 2023-24
Then the anchored residual model of residual.py (the close with free per-tour slopes + ridge nudges, lambda chosen inside
the window) on the selected inputs only, trained on 2013 .. Y - 1 (or on the last four seasons: "recent fit"), for
Y = 2025, 2026 (2026 to 28 Jul). Scored against the recalibrated close, the full-input anchored model and the current
model (mLL, + = the named model better; four-week-block intervals). Debut seasons out.

Writes data/studies/edge_anatomy/advice_selection.csv and advice_scores.csv.
Run: ./python.sh src/eda/edge_anatomy/advice.py
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

from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.edge_anatomy import residual as RS  # noqa: E402
from src.eda.edge_anatomy import scan as SN  # noqa: E402
from src.eda.edge_anatomy import stats as S  # noqa: E402

TEST = (2025, 2026)


def selections() -> pd.DataFrame:
    learn = pd.read_csv(E.OUT / "scan_learning.csv")
    ins = pd.read_csv(E.OUT / "scan_inputs.csv")
    rec = ins[ins["era"] == "2023-24"][["tour", "input", "z"]].rename(columns={"z": "z_2023_24"})
    t = learn.merge(rec, on=["tour", "input"], how="left")
    t = t[t["tour"].isin(["atp", "wta"])]
    t["decade"] = t["z_2013_24"].abs() >= 2
    t["recent"] = t["z_2023_24"].abs() >= 2
    t["both"] = t["decade"] & (np.sign(t["z_2013_24"]) == np.sign(t["z_2023_24"]))
    return t[["tour", "input", "family", "z_2013_24", "z_2023_24", "decade", "recent", "both"]]


def fit_predict(f: pd.DataFrame, Y: int, cols: list[str], window: str) -> pd.Series:
    te = f[f["season"] == Y]
    if not cols:
        b, rms, _ = RS.fit_window(f, Y, window, [])
        return pd.Series(expit(RS.base(te) @ b), index=te["match_id"].to_numpy())
    b, rms, _ = RS.fit_window(f, Y, window, cols)
    q = expit(np.column_stack([RS.base(te), RS.matrix(te, cols, rms)]) @ b)
    return pd.Series(q, index=te["match_id"].to_numpy())


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    sel = selections()
    f = SN.load()
    a = pd.read_parquet(E.OUT / "analysis.parquet").set_index("match_id")
    full = pd.read_parquet(E.OUT / "residual_forecasts.parquet").set_index("match_id")["expanding"]
    preds = {}
    for rule in ("decade", "recent", "both"):
        for window, wlabel in (("expanding", "fit on 2013 .. Y-1"), ("last4", "fit on the last 4 seasons")):
            parts = []
            for tour in ("atp", "wta"):
                cols = sel[(sel["tour"] == tour) & sel[rule]]["input"].tolist()
                ft = f[f["tour"] == tour]
                for Y in TEST:
                    parts.append(fit_predict(ft, Y, cols, window))
            preds[f"{rule} | {wlabel}"] = pd.concat(parts)
            E.log(f"{rule} {window} done")
    P = pd.DataFrame(preds)
    P = P.join(a[["season", "tour", "y", "block", "debut", "q_close", "q_full"]], how="inner")
    P["full-input anchored (expanding)"] = full.reindex(P.index)
    P = P[~P["debut"] & P["season"].isin(TEST)]
    rows = []
    for tour in ("both", "atp", "wta"):
        g = P if tour == "both" else P[P["tour"] == tour]
        y, blk = g["y"].to_numpy(), g["block"].to_numpy()
        for name in list(preds) + ["full-input anchored (expanding)"]:
            for base, bname in (("q_close", "the recalibrated close"), ("q_full", "the current model"),
                                ("full-input anchored (expanding)", "the full-input anchored model")):
                if name == base:
                    continue
                v = S.gain(g[base], g[name], y, blk)
                rows.append({"tour": tour, "model": name, "against": bname, "n": int(len(g)), **v,
                             "verdict": S.verdict(v)})
    return sel, pd.DataFrame(rows)


def main() -> int:
    sel, scores = run()
    sel.to_csv(E.OUT / "advice_selection.csv", index=False)
    scores.to_csv(E.OUT / "advice_scores.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    for rule in ("decade", "recent", "both"):
        for tour in ("atp", "wta"):
            print(rule, tour, sel[(sel["tour"] == tour) & sel[rule]]["input"].tolist())
    print(scores[["tour", "model", "against", "est", "lo", "hi", "p_better", "verdict"]].round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

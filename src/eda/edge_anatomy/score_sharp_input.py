"""Scores sharp_input.py: the current model fed the exchange consensus as its odds input, 2026 to 28 Jul.

Per match: the seed mean (seeds 0-3) of each block, symmetrised, through the instance's 2026 walk-forward recipe
(data_facts.json: the per-tour slope and the men's speed coefficient b, fitted on 2019-2025 with the instance's own
input; reused unchanged for the new input). Matches where the consensus exists (Betfair's close and/or Polymarket's
30-minute price), debut seasons out, results to 28 Jul 2026 only. Readings (mLL, + = the second named better;
four-week-block intervals):
    the model fed the consensus vs the consensus itself (raw)   does the model add to the sharpest price?
    the model fed the consensus vs the model fed its own input   which input serves the model better?
    the model fed its own input (4 seeds) vs the consensus      the earlier check, on these matches
Writes data/studies/edge_anatomy/sharp_input_scores.csv.
Run: ./python.sh src/eda/edge_anatomy/score_sharp_input.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.edge_anatomy import stats as S  # noqa: E402

IN = E.OUT / "sharp_input"


def main() -> int:
    parts, checks = {"orig": [], "sharp": []}, []
    for k in E.SEEDS:
        with np.load(IN / f"seed{k}.npz", allow_pickle=False) as z:
            ids = z["ids"].astype(str)
            n = len(ids)
            parts["orig"].append(E.sym(z["p_orig"], n))
            parts["sharp"].append(E.sym(z["p_sharp"], n))
            checks.append(json.loads(str(z["meta"])))
    p_orig, p_sharp = np.mean(parts["orig"], axis=0), np.mean(parts["sharp"], axis=0)
    src = pd.read_csv(IN / "sources.csv").astype({"match_id": str}).set_index("match_id")["source"]
    a = pd.read_parquet(E.OUT / "analysis.parquet").set_index("match_id")
    a = a[(a["season"] == 2026) & ~a["debut"]]
    fc = pd.DataFrame({"p_orig": p_orig, "p_sharp": p_sharp}, index=ids).reindex(a.index)
    facts = json.loads((E.OUT / "data_facts.json").read_text(encoding="utf-8"))
    s_atp, s_wta, b = facts["coefficients_both_stages"]["2026"][:3]
    s = np.where(a["tour"] == "atp", s_atp, s_wta)
    zz = np.where(a["tour"] == "atp", a["spd"].to_numpy(float), 0.0)
    a["q_orig4"] = expit(s * S.lg(fc["p_orig"].to_numpy()) + b * zz)
    a["q_sharp_model"] = expit(s * S.lg(fc["p_sharp"].to_numpy()) + b * zz)
    o = pd.read_parquet(E.INSTANCE / "odds_sources.parquet", columns=["match_id", "p_bfe", "p_pm_m30"])
    o = o.astype({"match_id": str}).set_index("match_id").reindex(a.index)
    lb, lp = S.lg(o["p_bfe"].to_numpy(float)), S.lg(o["p_pm_m30"].to_numpy(float))
    fb, fp = np.isfinite(o["p_bfe"].to_numpy(float)), np.isfinite(o["p_pm_m30"].to_numpy(float))
    a["p_consensus"] = np.where(fb & fp, expit((lb + lp) / 2), np.where(fb, expit(lb), np.where(fp, expit(lp), np.nan)))
    a["source"] = src.reindex(a.index).to_numpy()
    a = a[np.isfinite(a["p_consensus"])]
    rows = []
    for tour in ("both", "atp", "wta"):
        g = a if tour == "both" else a[a["tour"] == tour]
        y, blk = g["y"].to_numpy(), g["block"].to_numpy()
        for name, base, arm in (("model fed the consensus over the consensus", "p_consensus", "q_sharp_model"),
                                ("model fed the consensus over the model fed its own input", "q_orig4",
                                 "q_sharp_model"),
                                ("model fed its own input over the consensus", "p_consensus", "q_orig4")):
            v = S.gain(g[base], g[arm], y, blk)
            rows.append({"tour": tour, "reading": name, "n": int(len(g)), **v, "verdict": S.verdict(v)})
    out = pd.DataFrame(rows)
    out.to_csv(E.OUT / "sharp_input_scores.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.round(2).to_string(index=False))
    print("checks:", [(c["seed"], c["check_max_abs_diff_orig"]) for c in checks])
    print("4-seed orig vs 16-seed final, mean |diff|:", float(np.nanmean(np.abs(a["q_orig4"] - a["q_full"]))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

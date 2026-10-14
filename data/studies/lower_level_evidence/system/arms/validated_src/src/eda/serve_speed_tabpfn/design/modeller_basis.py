"""Design scratch (agent 2): the two bases of a match average, men, seasons <= 2023 only (speeds only; no result).

On ATP tour-level player-matches carrying both the held Infosys point mean (pm) and ManTennisData's key statistic (ks):
    the distribution of ks - pm (median, robust SD, tails), its relation to the count difference, rounding;
    for the discordant rows (|ks - pm| > 3 km/h), which value lies farther from the player's local reference (the
    median of his other tour-level matches within +-60 days, other events only).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/modeller_basis.py
Writes data/studies/serve_speed_tabpfn/design/modeller_basis.json
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


def main() -> None:
    p = M.panel("ks_first")
    p = p[(p["tour"] == "atp") & (p["year"] <= 2023)].copy()
    b = p[p["pm_mean"].notna() & p["ks_mean"].notna()].copy()
    b["d"] = b["ks_mean"] - b["pm_mean"]
    mad = 1.4826 * float((b["d"] - b["d"].median()).abs().median())
    out = {"rows_both": int(len(b)), "by_year": b["year"].value_counts().sort_index().to_dict(),
           "median": float(b["d"].median()), "mean": float(b["d"].mean()), "robust_sd": mad,
           "quantiles": {str(q): float(b["d"].quantile(q)) for q in (0.01, 0.05, 0.25, 0.75, 0.95, 0.99)},
           "share_abs_gt3": float((b["d"].abs() > 3).mean()),
           "ks_equals_ceil_pm": float((b["ks_mean"] == np.ceil(b["pm_mean"])).mean()),
           "ks_equals_round_pm": float((b["ks_mean"] == b["pm_mean"].round()).mean())}
    b["adn"] = pd.cut((b["ks_n"] - b["pm_n"]).abs(), [-1, 0, 2, 5, 10, 1000])
    out["by_count_gap"] = {str(k): {"rows": int(len(g)), "share_abs_gt3": float((g["d"].abs() > 3).mean())}
                           for k, g in b.groupby("adn", observed=True)}
    # local reference: median of the player's other-event tour-level values within +-60 days
    t = p[p["family"] == "tour"][["player_id", "obs", "tournament_id", "pm_mean", "ks_mean"]].copy()
    t["ref"] = t[["pm_mean", "ks_mean"]].mean(axis=1)
    loc = np.full(len(t), np.nan)
    for _, idx in t.groupby("player_id").indices.items():
        o, tid, r = t["obs"].to_numpy()[idx], t["tournament_id"].to_numpy()[idx], t["ref"].to_numpy()[idx]
        for k in range(len(idx)):
            m = (np.abs(o - o[k]) <= 60) & (tid != tid[k]) & ~np.isnan(r)
            if m.sum() >= 3:
                loc[idx[k]] = np.median(r[m])
    t["local"] = loc
    x = t[t["pm_mean"].notna() & t["ks_mean"].notna() & t["local"].notna()].copy()
    big = x[(x["ks_mean"] - x["pm_mean"]).abs() > 3]
    out["discordant_with_reference"] = int(len(big))
    out["discordant_ks_farther_share"] = float(((big["ks_mean"] - big["local"]).abs()
                                                > (big["pm_mean"] - big["local"]).abs()).mean())
    out["robust_sd_vs_local"] = {c: float(1.4826 * (x[c] - x["local"] - (x[c] - x["local"]).median()).abs().median())
                                 for c in ("ks_mean", "pm_mean")}
    (M.OUT / "modeller_basis.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

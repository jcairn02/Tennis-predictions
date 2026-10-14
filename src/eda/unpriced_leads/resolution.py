"""Outcome-free resolution of the registered looks (unpriced-leads study, 13 Oct 2026).

For a candidate x scaled to unit RMS, the information about its coefficient beyond the close is about sum p(1 - p) x^2,
so SE(beta) ~ 1 / sqrt(sum p (1 - p)) per unit of x, times a design effect for clustering (the harness's placebo SD,
1.08, measured on 2013-24). Reads match ids, dates, tours and the close only (no result column): Look A = 1 Jan 2025 -
28 Jul 2026, Look B = the sealed matches from 29 Jul 2026 (counted to the frame's last date and projected to 31 Jan 2027
from the 2025 calendar's matches per day over the same months).
Writes data/studies/unpriced_leads/resolution.json.
Run: ./python.sh src/eda/unpriced_leads/resolution.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
FRAME = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10" / "model_frame.parquet"
OUT = ROOT / "data" / "studies" / "unpriced_leads" / "resolution.json"
DEFF = 1.08            # the harness's placebo SD of the cluster-robust z (selftest, 13 Oct 2026)
Z80 = 1.96 + 0.8416    # two-sided 5%, 80% power
Z80_ONE = 1.645 + 0.8416


def main() -> int:
    f = pd.read_parquet(FRAME, columns=["match_id", "tour", "season", "tournament_date", "debut_season", "p_mkt"])
    if "a_won" in f.columns:
        raise RuntimeError("no result column may be read here")
    f = f[~f["debut_season"].astype(bool)].copy()
    p = f["p_mkt"].clip(1e-6, 1 - 1e-6)
    f["info"] = p * (1 - p)
    A = f[(f["tournament_date"] >= "2025-01-01") & (f["tournament_date"] < "2026-07-29")]
    B = f[f["tournament_date"] >= "2026-07-29"]
    ref = f[(f["tournament_date"] >= "2025-07-29") & (f["tournament_date"] < "2026-01-31")]   # same months, a year earlier
    out = {"design_effect": DEFF, "frame_last_date": str(f["tournament_date"].max().date())}
    for lab, g in (("lookA_2025_to_2026-07-28", A), ("lookB_sealed_so_far", B), ("calendar_2025-07-29_to_2026-01-30", ref),
                   ("disc_2013_2024", f[f["season"] <= 2024])):
        d = {}
        for tour in ("both", "atp", "wta"):
            h = g if tour == "both" else g[g["tour"] == tour]
            I = float(h["info"].sum())
            se = DEFF / np.sqrt(I) if I > 0 else np.nan
            d[tour] = {"matches": int(len(h)), "mean_p1mp": float(h["info"].mean()) if len(h) else np.nan,
                       "se_beta_per_rms": se, "mde80_two_sided": Z80 * se, "mde80_one_sided": Z80_ONE * se}
        out[lab] = d
    # Look B projected to 31 Jan 2027: the sealed matches so far plus the 2025 calendar's matches from the frame's last
    # date + 1 to 30 Jan (shifted one year), by tour
    last = f["tournament_date"].max()
    proj = {}
    for tour in ("both", "atp", "wta"):
        b = B if tour == "both" else B[B["tour"] == tour]
        r = f[(f["tournament_date"] > last - pd.DateOffset(years=1)) & (f["tournament_date"] < pd.Timestamp("2026-01-31"))]
        r = r if tour == "both" else r[r["tour"] == tour]
        I = float(b["info"].sum() + r["info"].sum())
        n = int(len(b) + len(r))
        se = DEFF / np.sqrt(I)
        proj[tour] = {"matches": n, "se_beta_per_rms": se, "mde80_two_sided": Z80 * se, "mde80_one_sided": Z80_ONE * se}
        a = A if tour == "both" else A[A["tour"] == tour]
        I2 = I + float(a["info"].sum())
        se2 = DEFF / np.sqrt(I2)
        proj[tour]["A_plus_B_matches"] = n + int(len(a))
        proj[tour]["A_plus_B_se"] = se2
        proj[tour]["A_plus_B_mde80_one_sided"] = Z80_ONE * se2
    out["lookB_projected_to_2027-01-31"] = proj
    # what a coefficient of size beta (log-odds per RMS unit) is worth in mLL: about 1000 * beta^2 * mean p(1-p) / 2
    mp = float(A["info"].mean())
    out["mll_per_beta"] = {f"{b:.2f}": 1000 * b * b * mp / 2 for b in (0.02, 0.03, 0.05, 0.07, 0.10)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

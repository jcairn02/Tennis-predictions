"""R2 exposure checks, outcome-free (no result column is loaded).

1. Do the registered scores stay orthogonal to the model's 48 inputs on Look A's rows (frozen projections)? If they do,
   a score's Look A estimate is nearly independent of the in-model inputs' Look A estimates that edge_anatomy read.
2. How close is G1 to the luck statistic market_anchoring read on 2019-2026 outcomes (men's hold and break luck with a
   365-day half-life)? The nearest held version: the luck builder's PS03 hold/break/net with h = 365.
3. Polymarket coverage in the bet-timing frame by month (for H8's 3,000-match trigger).
Writes exposure_checks.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import rt_common as R  # noqa: E402


def main() -> int:
    reg = R.registry()
    f = R.outcome_free_frame()
    td = pd.to_datetime(f["tournament_date"])
    disc = f["season"].between(2013, 2024).to_numpy()
    lookA = (f["season"].between(2025, 2026) & (td < pd.Timestamp("2026-07-29"))).to_numpy()
    mem, grp, omni, _ = R.scores(f, reg)
    names = R.diff_inputs()
    X = np.nan_to_num(f[[f"in_{n}" for n in names]].to_numpy(float))
    out = {"max_abs_corr_with_inputs": {}}
    for k, s in {"omnibus": omni, **grp}.items():
        e = {}
        for lab, m in (("disc", disc), ("lookA", lookA)):
            c = np.array([np.corrcoef(s[m], X[m, j])[0, 1] if np.std(X[m, j]) > 0 else 0.0 for j in range(X.shape[1])])
            j = int(np.nanargmax(np.abs(c)))
            # the share of the score's variance the 48 inputs span linearly on these rows (no intercept)
            b = np.linalg.lstsq(X[m], s[m], rcond=None)[0]
            r2 = 1 - np.sum((s[m] - X[m] @ b) ** 2) / np.sum(s[m] ** 2)
            e[lab] = {"max_abs_corr": float(np.abs(c[j])), "input": names[j], "r2_on_inputs": float(r2)}
        out["max_abs_corr_with_inputs"][k] = e
    # 2. G1 against the 365-day luck relatives
    lv = pd.read_parquet(R.ROOT / "data/studies/unpriced_leads/candidates/luck/values.parquet",
                         columns=["match_id", "PS03_hold_h365", "PS03_break_h365", "PS03_net_h365", "PS03_net"])
    lv = lv.astype({"match_id": str}).set_index("match_id").reindex(f["match_id"])
    rel = {}
    men = (f["tour"] == "atp").to_numpy()
    for lab, m in (("disc_men", disc & men), ("lookA_men", lookA & men), ("lookA_all", lookA)):
        r = {}
        for c in ("PS03_hold_h365", "PS03_break_h365", "PS03_net_h365"):
            x = lv[c].to_numpy(float)
            ok = m & np.isfinite(x)
            r[f"G1_vs_{c}"] = float(np.corrcoef(grp["G1"][ok], -x[ok])[0, 1])
            r[f"PS03_net_member_vs_{c}"] = float(np.corrcoef(mem["G1:PS03_net"][ok], -x[ok])[0, 1])
        x = lv["PS03_net"].to_numpy(float)
        ok = m & np.isfinite(x)
        r["PS03_net_member_vs_raw_PS03_net_h91"] = float(np.corrcoef(mem["G1:PS03_net"][ok], -x[ok])[0, 1])
        rel[lab] = r
    out["G1_vs_365day_luck"] = rel
    # 3. Polymarket coverage (bet-timing frame), matches with a Polymarket price 48 h or 6 h out, by month
    bt = pd.read_parquet(R.ROOT / "data/studies/bet_timing/frame.parquet",
                         columns=["match_id", "tournament_date", "condition_id", "p_pm_h48", "p_pm_h6"])
    bt["ym"] = pd.to_datetime(bt["tournament_date"]).dt.to_period("M").astype(str)
    cov = bt.groupby("ym").agg(matches=("match_id", "size"), with_condition=("condition_id", lambda s: int(s.notna().sum())),
                               with_pm_h48=("p_pm_h48", lambda s: int(s.notna().sum())),
                               with_pm_h6=("p_pm_h6", lambda s: int(s.notna().sum())))
    out["polymarket_by_month"] = cov[cov.index >= "2024-07"].to_dict(orient="index")
    (R.OUT / "exposure_checks.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

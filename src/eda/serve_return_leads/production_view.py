"""Should production use the two steady signals? (serve/return-leads study, the owner's question of 22 Oct 2026.)

For the luck score (C1) and the second-serve speed form (C3) of addendum 1, men, seen matches only (through
readings.seen_frame: tournament dates before 29 Jul 2026):
    beyond the model's both-stages forecast (the production model's TabPFN plus its first-serve speed stage), 2020-24
    and 2025-26: beta per SD, se, z, and the in-window gain in mLL per match (in-sample, so optimistic);
    beyond the close, 2013-24: the discovery beta per SD;
    a size by the five-pattern template (check_now_rules.md): prior N(m0, m0^2), m0 = 0.45 x the 2013-24 beta beyond
    the close, updated with the 2025-26 beta beyond the model; never below 0;
    what that size does to a match: the shift in percentage points at even odds for the median and the 95th
    percentile |score|, and the plausible log-loss gain 1000 x 0.5 b^2 E[p(1-p)] mLL per match.
Writes data/studies/serve_return_leads/production_view.json.
Run: ./python.sh src/eda/serve_return_leads/production_view.py
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

from src.eda.serve_return_leads import addendum_scales as A  # noqa: E402
from src.eda.serve_return_leads import common as C  # noqa: E402
from src.eda.serve_return_leads import readings as R  # noqa: E402


def main() -> int:
    f = R.seen_frame("atp")
    v = A.raw_values(f)
    sc = A.scales(f, v)
    s = A.scores(v, sc)
    out = {}
    for k, name in (("C1", "luck in the big points"), ("C3", "second-serve speed change")):
        x = np.asarray(s[k], float)
        res = {"name": name}
        for w, (a, b) in {"2013-24": (2013, 2024), "2020-24": (2020, 2024), "2025-26": (2025, 2026)}.items():
            m = f["season"].between(a, b).to_numpy()
            g = f[m].reset_index(drop=True)
            for base in ("L", "L_model"):
                if not np.isfinite(g[base].to_numpy(float)).any():
                    continue
                r = C.fit(g, x[m], base=base)
                res[f"{w} {base}"] = {kk: r[kk] for kk in ("beta", "se", "z", "n", "blocks", "gain_mll_in_window")}
        m0 = 0.45 * res["2013-24 L"]["beta"]
        b_d, se_d = res["2025-26 L_model"]["beta"], res["2025-26 L_model"]["se"]
        prec0, prec1 = 1 / m0 ** 2, 1 / se_d ** 2
        post = max(0.0, (prec0 * m0 + prec1 * b_d) / (prec0 + prec1))
        m = f["season"].between(2025, 2026).to_numpy()
        z = x[m] / np.sqrt(np.mean(x[m] ** 2))
        az = np.abs(z[z != 0])
        p = expit(f.loc[m, "L"].to_numpy(float))
        res["size_per_sd"] = post
        res["prior_mean"] = m0
        res["shift_points_median"] = 100 * (expit(post * np.median(az)) - 0.5)
        res["shift_points_p95"] = 100 * (expit(post * np.quantile(az, 0.95)) - 0.5)
        res["plausible_gain_mll"] = 1000 * 0.5 * post ** 2 * float(np.mean(p * (1 - p)))
        res["share_with_value_2025_26"] = float(np.mean(z != 0))
        out[k] = res
    C.write_json(C.OUT / "production_view.json", out)
    for k, r in out.items():
        print(k, r["name"])
        for kk in ("2020-24 L_model", "2025-26 L_model", "2013-24 L", "2025-26 L"):
            q = r[kk]
            print(f"   {kk:16s} beta {q['beta']:+.4f} se {q['se']:.4f} z {q['z']:+.2f} gain {q['gain_mll_in_window']:+.3f} mLL")
        print(f"   size per SD {r['size_per_sd']:.4f} (prior mean {r['prior_mean']:.4f}); shift median "
              f"{r['shift_points_median']:.2f} pts, p95 {r['shift_points_p95']:.2f} pts; plausible gain "
              f"{r['plausible_gain_mll']:.3f} mLL/match; present {r['share_with_value_2025_26']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

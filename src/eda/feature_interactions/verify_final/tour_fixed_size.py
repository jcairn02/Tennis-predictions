"""Final-test verifier: the per-tour primary with bug 1's fix (encompassing restricted to the tours present), size at
beta = 0 and power at the 0.5 mLL setting, synthetic outcomes (harness DGP).

    ./python.sh src/eda/feature_interactions/verify_final/tour_fixed_size.py --reps 1000
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.verify_final import harness as HN  # noqa: E402
from src.eda.feature_interactions.verify_final.synth_power import beta_for, population_gain  # noqa: E402
from src.eda.feature_interactions.verify_final.tour_subset_bug import encompassing_fixed  # noqa: E402

FT, TT = HN.FT, HN.TT


def main() -> int:
    warnings.simplefilter("ignore")
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 1000
    syn = HN.Synth()
    TT.encompassing = encompassing_fixed
    masks = {t: (syn.f["tour"] == t).to_numpy() for t in ("atp", "wta")}
    out = []
    for i, target in enumerate((0.0, 0.5)):
        beta = beta_for(syn, target)
        rng = np.random.default_rng(7000 + i)
        rej = {t: [] for t in masks}
        above = {t: [] for t in masks}
        for _ in range(reps):
            syn.draw(beta, rng)
            params = FT.parameters(syn.xs)
            for t, m in masks.items():
                q = FT.primary(syn.f[m].reset_index(drop=True), syn.xs, params)
                rej[t].append((q["lo"] > 0) or (q["hi"] < 0))
                above[t].append(q["lo"] > 0)
        s = {"target_mll": target, "beta": beta, "pooled_population_gain": population_gain(syn, beta), "reps": reps}
        for t in masks:
            s[f"{t}_two_sided_rejection"] = float(np.mean(rej[t]))
            s[f"{t}_interval_above_0"] = float(np.mean(above[t]))
        out.append(s)
        print(json.dumps(s), flush=True)
    (HN.OUT / "tour_fixed_size.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

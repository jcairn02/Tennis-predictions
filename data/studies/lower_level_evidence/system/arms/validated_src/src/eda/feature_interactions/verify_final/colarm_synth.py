"""Final-test verifier: the column-arm secondary (final_test.column_arm) on SYNTHETIC outcomes at a near-zero difference.

DGP, every season 2019-2026: y ~ Bernoulli(expit(a_tour * (eta_binj + eta_model) / 2)), each eta the seed mean of the
seeds held (binj 0-2 in 2019-2024 and 0-7 in 2025-2026; model 0-15), so neither arm is the truth and their expected
gap is about 0. tabpfn_tests.frame is replaced by a result-free cached frame whose a_won is the current synthetic draw
(column_arm reads its calibration history through it). gain* per replicate = the expected paired gain of the forecasts
column_arm actually deployed (captured from its paired_gain calls) under the true probabilities.

    ./python.sh src/eda/feature_interactions/verify_final/colarm_synth.py --reps 1000
"""
from __future__ import annotations

import functools
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.verify_final import harness as HN  # noqa: E402

FT, TT, C = HN.FT, HN.TT, HN.C
ORIG_ETA_ARM, ORIG_PG = FT.eta_arm, TT.paired_gain


@functools.lru_cache(maxsize=None)
def _eta_arm(arm, seeds, seasons, block):
    return ORIG_ETA_ARM(arm, seeds, seasons, block)


class ColSynth:
    def __init__(self):
        self.cache, self.y, self.calls = {}, None, []
        TT.frame = self.frame
        FT.eta_arm = lambda arm, seeds, seasons, block="td": _eta_arm(arm, tuple(seeds), tuple(seasons), block).copy()
        TT.paired_gain = self.pg
        self.f = FT.population()
        base = HN.frame_free(range(2019, 2027), with_players=False)
        eb = pd.concat([FT.eta_arm("binj", range(16), [s]) for s in range(2019, 2027)])
        em = pd.concat([FT.eta_arm("model", range(16), [s]) for s in range(2019, 2027)])
        mix = 0.5 * (base["match_id"].map(eb).to_numpy(float) + base["match_id"].map(em).to_numpy(float))
        a = base["tour"].map(HN.A_TRUE).to_numpy(float)
        if not np.isfinite(mix).all():
            raise RuntimeError("missing forecasts")
        self.p = pd.Series(expit(a * mix), index=base["match_id"].to_numpy())

    def frame(self, seasons, with_players: bool = True) -> pd.DataFrame:
        key = (tuple(seasons), with_players)
        if key not in self.cache:
            self.cache[key] = HN.frame_free(seasons, with_players)
        f = self.cache[key].copy()
        f["a_won"] = f["match_id"].map(self.y).to_numpy(float) if self.y is not None else np.nan
        return f

    def pg(self, f, pa, pb, rows=None):
        self.calls.append((f["match_id"].to_numpy(), np.asarray(pa, float), np.asarray(pb, float), rows))
        return ORIG_PG(f, pa, pb, rows)

    def draw(self, rng):
        self.y = pd.Series((rng.random(len(self.p)) < self.p.to_numpy()).astype(float), index=self.p.index)
        self.f["a_won"] = self.f["match_id"].map(self.y).to_numpy(float)


def main() -> int:
    warnings.simplefilter("ignore")
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 1000
    cs = ColSynth()
    rng = np.random.default_rng(424242)
    rec = []
    for _ in range(reps):
        cs.draw(rng)
        cs.calls = []
        rows = FT.column_arm(cs.f)
        for r, (ids, pa, pb, mask) in zip(rows, cs.calls):
            pt = cs.p.reindex(ids).to_numpy(float)
            k = mask & np.isfinite(pa) & np.isfinite(pb)
            g_star = float(1000 * np.mean(HN.ce(pt[k], pa[k]) - HN.ce(pt[k], pb[k])))
            rec.append({"tour": r["tour"], "gain": r["gain"], "lo": r["lo"], "hi": r["hi"], "g_star": g_star,
                        "n": r["matches"]})
    d = pd.DataFrame(rec)
    out = []
    for t, g in d.groupby("tour", sort=False):
        bias = g["gain"] - g["g_star"]
        out.append({"tour": t, "reps": len(g), "matches": int(g["n"].iloc[0]), "gain_star_mean": g["g_star"].mean(),
                    "gain_mean": g["gain"].mean(), "bias_mean": bias.mean(), "bias_mc_se": bias.std() / np.sqrt(len(g)),
                    "gain_sd": g["gain"].std(),
                    "interval_covers_gain_star": float(((g["lo"] <= g["g_star"]) & (g["g_star"] <= g["hi"])).mean()),
                    "interval_excludes_0": float(((g["lo"] > 0) | (g["hi"] < 0)).mean())})
    d.to_csv(HN.OUT / "colarm_replicates.csv", index=False)
    (HN.OUT / "colarm_results.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

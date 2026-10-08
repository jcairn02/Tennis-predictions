"""Final-test verifier, step 1 (result-free or synthetic only):
  1. frame_free equals tabpfn_tests.frame without a_won (checked on 2014-2024, a_won dropped before comparing);
  2. final_test.x_scaled equals the screen's own preprocessing (screen.prepare) on the screen's 2014-2024 rows;
  3. one synthetic replicate through final_test.parameters / primary / effect, timed.

    ./python.sh src/eda/feature_interactions/verify_final/sanity.py
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.verify_final import harness as HN  # noqa: E402

S, FT, TT = HN.S, HN.FT, HN.TT


def main() -> int:
    warnings.simplefilter("ignore")
    out = {}
    a = HN.ORIG_FRAME(range(2014, 2025)).drop(columns=["a_won"])
    b = HN.frame_free(range(2014, 2025)).drop(columns=["a_won"])
    out["frame_free_equal_2014_2024"] = bool(a.equals(b[a.columns])) and list(a.columns) == list(b.columns)
    del a
    Fs = S.load(with_model=False)
    x = pd.read_parquet(FT.X_FILE).set_index("match_id")["x"]
    h = S.Hypothesis("B-INJ", x.reindex(Fs["match_id"]).to_numpy(float))
    xs_screen, _, prep = S.prepare(Fs, h, "market")
    xs_final = FT.x_scaled(x).reindex(Fs["match_id"]).to_numpy(float)
    out["x_scaled_vs_screen_max_abs_diff"] = float(np.max(np.abs(xs_screen - xs_final)))
    out["screen_clip"], out["screen_sd"] = prep.x_clip, prep.x_sd
    out["x_missing_share_2014_2024"] = float(np.isnan(h.x).mean())
    syn = HN.Synth()
    out["population"] = int(len(syn.f))
    out["history_rows"] = int(len(syn.H))
    out["x_missing_share_test"] = float(syn.x.reindex(syn.f["match_id"]).isna().mean())
    out["x_sd_test_scaled"] = float(np.std(syn.xs.reindex(syn.f["match_id"])))
    out["corr_x_eta_test"] = float(np.corrcoef(syn.xs.reindex(syn.f["match_id"]), syn.z16)[0, 1])
    out["seed_noise_sd_z0_minus_z8"] = float(np.std(syn.z0 - syn.z8))
    rng = np.random.default_rng(1)
    t0 = time.time()
    syn.draw(0.0, rng)
    params = FT.parameters(syn.xs)
    t1 = time.time()
    prim = FT.primary(syn.f, syn.xs, params)
    t2 = time.time()
    eff = FT.effect(syn.f, syn.xs, params)
    t3 = time.time()
    out["timing_s"] = {"parameters": t1 - t0, "primary": t2 - t1, "effect": t3 - t2}
    out["params"] = params
    out["primary"], out["effect"] = prim, eff
    HN.OUT.mkdir(parents=True, exist_ok=True)
    (HN.OUT / "sanity.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, default=float)[:2500])
    return 0


if __name__ == "__main__":
    sys.exit(main())

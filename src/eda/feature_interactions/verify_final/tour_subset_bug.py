"""Final-test verifier: tabpfn_tests.encompassing on a one-tour subset (synthetic outcomes). The absent tour's cubic
column is 0 / np.std([]) = 0 / NaN, because `np.std(empty) or 1.0` keeps NaN (NaN is truthy), so b is NaN.
encompassing_fixed skips tours absent from the rows; on both tours it must equal the original exactly.

    ./python.sh src/eda/feature_interactions/verify_final/tour_subset_bug.py
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

FT, TT, C, S = HN.FT, HN.TT, HN.C, HN.S
ORIG = TT.encompassing


def encompassing_fixed(f, eta_b, dev):
    """The proposed fix: the cubic (and slope) columns only for tours present in f; otherwise unchanged."""
    import types
    tour = f["tour"].to_numpy()
    present = tuple(t for t in C.TOURS if (tour == t).any())
    real = C.TOURS
    try:
        C.TOURS = present
        return ORIG(f, eta_b, dev)
    finally:
        C.TOURS = real


def main() -> int:
    warnings.simplefilter("ignore")
    syn = HN.Synth()
    syn.draw(0.042955620639999706, np.random.default_rng(11))
    params = FT.parameters(syn.xs)
    out = {"np.std([]) or 1.0": repr(np.std(np.array([])) or 1.0)}
    for name, mask in (("all", np.ones(len(syn.f), bool)), ("atp", (syn.f["tour"] == "atp").to_numpy()),
                       ("wta", (syn.f["tour"] == "wta").to_numpy())):
        g = syn.f[mask].reset_index(drop=True)
        a = FT.primary(g, syn.xs, params)
        TT.encompassing = encompassing_fixed
        b = FT.primary(g, syn.xs, params)
        TT.encompassing = ORIG
        out[name] = {"current_b": a["b"], "current_lo": a["lo"], "fixed_b": b["b"], "fixed_lo": b["lo"],
                     "fixed_hi": b["hi"], "fixed_df": b["df"], "identical": a == b}
    (HN.OUT / "tour_subset_bug.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

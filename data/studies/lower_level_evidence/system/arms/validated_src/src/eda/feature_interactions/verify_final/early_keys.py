"""Final-test verifier: do the 2025-2026 base forecast files carry the "early" block (the base fed the 24-hour price)
that final_test.polymarket reads, and which match ids does it cover? Forecasts and availability flags only.

    ./python.sh src/eda/feature_interactions/verify_final/early_keys.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402


def main() -> int:
    ep = pd.read_parquet(C.EARLY, columns=["match_id", "has_early", "p_early_a", "p_close_a", "clean", "all_early"])
    ep["match_id"] = ep["match_id"].astype(str)
    for s in (2025, 2026):
        for k in range(16):
            name = f"model__{s}__seed{k}.npz"
            path = C.LOCAL / name if (C.LOCAL / name).exists() else C.RACE_LOCAL / name
            with np.load(path, allow_pickle=False) as z:
                has = "p_early" in z.files
                n = len(z["ids_early"]) if has else None
                ids = set(z["ids_early"].astype(str)) if has else set()
            if k in (0, 2, 3, 8, 15):
                print(s, k, path.parent.parent.name, "p_early" if has else "NO p_early", n)
        if has:
            e = ep[ep["match_id"].isin(ids)]
            print(s, "early ids in EARLY frame:", len(e), "all_early", int(e["all_early"].fillna(False).sum()),
                  "clean", int(e["clean"].fillna(False).sum()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Final-test verifier: the column-arm secondary's inputs. Which binj forecast files exist, and does every match the
secondary needs (calibration history 2019-2025, test 2025-2026) have a binj and a model forecast? Forecast ids only.

    ./python.sh src/eda/feature_interactions/verify_final/binj_coverage.py
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

FT, C = HN.FT, HN.C


def main() -> int:
    warnings.simplefilter("ignore")
    out = {"files": {}, "coverage": {}}
    for s in range(2014, 2027):
        out["files"][s] = [k for k in range(16) if (C.LOCAL / f"binj__{s}__seed{k}.npz").exists()]
    for s in range(2019, 2027):
        fr = HN.frame_free([s], with_players=False)
        row = {"matches": int(len(fr))}
        for arm, seeds in (("binj", range(16)), ("model", range(16))):
            have = [k for k in seeds if (C.LOCAL / f"{arm}__{s}__seed{k}.npz").exists()
                    or (arm == "model" and (C.RACE_LOCAL / f"model__{s}__seed{k}.npz").exists())]
            if not have:
                row[arm] = "no files"
                continue
            e = FT.eta_arm(arm, have, [s])
            v = fr["match_id"].map(e).to_numpy(float)
            row[arm] = {"seeds": len(have), "covered": float(np.isfinite(v).mean()),
                        "duplicate_ids": int(e.index.duplicated().sum())}
        out["coverage"][s] = row
    (HN.OUT / "binj_coverage.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())

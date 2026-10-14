"""Lead's check (13 Oct 2026): is the draw shadow's reverse term R (rank > 50 while a dominant other is alive) more than
the status axis (rank > 50 alone)? Seasons <= 2024 through the harness; writes lead_checks/shadow_check.json.
Run: ./python.sh src/eda/unpriced_leads/shadow_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import screen as H  # noqa: E402


def fit_joint(f: pd.DataFrame, cols: list[np.ndarray], tour: str) -> list[tuple[float, float]]:
    m = np.ones(len(f), bool) if tour == "both" else (f["tour"] == tour).to_numpy()
    g = f[m]
    y, blk = g["y"].to_numpy(float), g["block"].to_numpy()
    B = H.tour_slope_cols(g["tour"].to_numpy(), g["L"].to_numpy(float))
    X = np.column_stack([H.rms_scale(c[m]) for c in cols])
    Z = np.column_stack([B, X])
    zero = np.zeros(len(y))
    b, Hs = H.fit_offset(Z, y, zero)
    V = H.cluster_cov(Z, y, zero, b, Hs, blk)
    k = X.shape[1]
    return [(float(b[-k + i]), float(b[-k + i] / np.sqrt(V[-k + i, -k + i]))) for i in range(k)]


def main() -> int:
    f = H.load_frame()
    v = pd.read_parquet(H.OUT / "candidates" / "extras" / "values.parquet").astype({"match_id": str})
    v = v.drop_duplicates("match_id").set_index("match_id").reindex(f["match_id"])
    p = pd.read_parquet(H.STAGE0_P, columns=["match_id", "player_id", "rank"]).astype({"match_id": str})
    ra, rb = H.at_frame(p, "rank", f)
    low = ((ra > 50).astype(float) - (rb > 50).astype(float))
    has = v["rs09_R_event_has_dominant"].to_numpy(float) > 0
    R = v["rs09_R"].to_numpy(float)
    out = {}
    for tour in ("both", "atp", "wta"):
        out[tour] = {
            "low_alone": fit_joint(f, [low], tour)[0],
            "R_alone": fit_joint(f, [R], tour)[0],
            "R_and_low_jointly": fit_joint(f, [R, low], tour),
            "low_in_events_with_dominant": fit_joint(f, [np.where(has, low, 0.0)], tour)[0],
            "low_in_events_without_dominant": fit_joint(f, [np.where(~has, low, 0.0)], tour)[0],
        }
    (H.OUT / "lead_checks").mkdir(parents=True, exist_ok=True)
    (H.OUT / "lead_checks" / "shadow_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

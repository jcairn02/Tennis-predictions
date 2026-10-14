"""How far the rebuilt frame's 58 inputs moved from the current frame's, on the matches both frames hold.

Per input and part (training 2013-2021, test 2022-2026): rows changed (|difference| > 1e-9), correlation, and the
median and 99th-percentile absolute change in units of the current input's standard deviation; per input and season the
share of rows changed. Inputs and labels only; no forecast or result is related to anything.

Writes data/studies/model_rebuild/input_changes.csv and input_changes_by_season.csv.
Run: ./python.sh src/eda/model_rebuild/input_changes.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "studies" / "model_rebuild"
CURRENT = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"


def main() -> int:
    cur = pd.read_parquet(CURRENT).set_index("match_id")
    new = pd.read_parquet(OUT / "model_frame.parquet").set_index("match_id")
    ids = cur.index.intersection(new.index)
    cur, new = cur.loc[ids], new.loc[ids]
    inputs = [c for c in cur.columns if c.startswith("in_")]
    part = np.where(cur["season"] <= 2021, "train", "test")
    rows, by_season = [], []
    for c in inputs:
        a, b = cur[c].to_numpy(float), new[c].to_numpy(float)
        both = np.isfinite(a) & np.isfinite(b)
        changed = (np.isfinite(a) != np.isfinite(b)) | (both & (np.abs(a - b) > 1e-9))
        sd = float(np.nanstd(a)) or 1.0
        for p in ("train", "test"):
            m = part == p
            k = m & both
            d = np.abs(a[k] - b[k]) / sd
            rows.append({"input": c[3:], "part": p, "rows": int(m.sum()), "changed": int(changed[m].sum()),
                         "changed_share": round(float(changed[m].mean()), 4),
                         "correlation": round(float(np.corrcoef(a[k], b[k])[0, 1]), 5) if k.sum() > 2 and
                         np.std(a[k]) > 0 and np.std(b[k]) > 0 else None,
                         "median_abs_change_sd": round(float(np.median(d)), 5) if len(d) else None,
                         "p99_abs_change_sd": round(float(np.quantile(d, 0.99)), 5) if len(d) else None,
                         "missing_current": int((~np.isfinite(a[m])).sum()),
                         "missing_rebuilt": int((~np.isfinite(b[m])).sum())})
        s = pd.Series(changed).groupby(cur["season"].to_numpy()).mean()
        by_season.append({"input": c[3:], **{str(k): round(float(v), 4) for k, v in s.items()}})
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "input_changes.csv", index=False)
    pd.DataFrame(by_season).to_csv(OUT / "input_changes_by_season.csv", index=False)
    print(f"common matches {len(ids):,}; labels equal: {bool((cur['a_won'] == new['a_won']).all())}")
    print(t.sort_values(["part", "changed_share"], ascending=[True, False]).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

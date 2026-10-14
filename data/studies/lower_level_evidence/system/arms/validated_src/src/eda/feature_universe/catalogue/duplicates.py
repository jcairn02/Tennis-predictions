"""Exact and near duplicates among the store's columns (values only; no result is read). A selection process should keep
one column of each exact group. Exact = identical float64 values with NaN in the same rows. Near = the pairs checked by
hand in the universe (correlation > 0.999 on rows where both exist).
Writes data/studies/feature_universe/build/duplicates.json. (store_registry.csv's canonical / near_dup_of columns, from
build_store.py's hygiene step, are the complete version of this check: every pair, with negated copies.)
Run: ./python.sh src/eda/feature_universe/catalogue/duplicates.py
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parents[4] / "data" / "studies" / "feature_universe" / "build"
STORE = HERE.parent / "store.parquet"
NEAR = [("pp__rest_days_a", "fp__f20_fatigue__bd_rest_a"), ("fp__f13_uncertainty__l52_a", "fp__f07_evidence_age__f07_ell_a"),
        ("fi__B11__bd11_on", "ds__B11_member_On"), ("pp__adjperf_tpw_2w_a", "fp__f07_evidence_age__f07_form_rebuilt_a"),
        ("pp__age_a", "pp__age_pl_a")]


def main() -> int:
    names = [c for c in pq.read_schema(STORE).names if "__" in c]
    groups = defaultdict(list)
    for i in range(0, len(names), 100):
        d = pd.read_parquet(STORE, columns=names[i:i + 100])
        for c in d.columns:
            v = pd.to_numeric(d[c], errors="coerce").to_numpy(dtype="float64")
            v = np.where(np.isnan(v), np.nan, v + 0.0)          # -0.0 -> 0.0, one NaN pattern
            groups[hashlib.sha256(np.nan_to_num(v, nan=1.2345e300).tobytes()).hexdigest()].append(c)
    exact = sorted([g for g in groups.values() if len(g) > 1], key=lambda g: g[0])
    near = []
    d = pd.read_parquet(STORE, columns=sorted({c for p in NEAR for c in p}))
    for a, b in NEAR:
        x, y = d[a].astype(float), d[b].astype(float)
        m = x.notna() & y.notna()
        near.append({"a": a, "b": b, "corr": round(float(np.corrcoef(x[m], y[m])[0, 1]), 5),
                     "max_abs_diff": round(float((x[m] - y[m]).abs().max()), 4),
                     "nan_mismatch_share": round(float((x.isna() != y.isna()).mean()), 4)})
    out = {"exact_groups": exact, "n_exact_groups": len(exact),
           "redundant_columns": int(sum(len(g) - 1 for g in exact)), "near": near}
    (HERE / "duplicates.json").write_text(json.dumps(out, indent=1))
    print(f"{len(exact)} exact groups, {out['redundant_columns']} redundant columns")
    for g in exact:
        print("  " + " = ".join(g))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

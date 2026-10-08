"""Result-free G2 metrics for every candidate column that can be built from the augmented panel (round 1).

For each builder (builders_a, _b, _c) and each column it returns: coverage (both players, 2014-2021 and 2022-2024, per
tour), the swap test under the full swap (base.swap_full), and the R-squared on the 58 inputs over 2014-2021 rows (plain
OLS; and on the symmetry-aware augmented basis). `a_won` is never read. Writes
data/studies/feature_interactions/round1/feasibility_metrics.csv.
Run: ./python.sh src/eda/feature_interactions/round1/feasibility/audit.py [I-001,I-002,...]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.eda.feature_interactions.round1.feasibility import base as B  # noqa: E402
from src.eda.feature_interactions.round1.feasibility import builders_a, builders_b, builders_c  # noqa: E402

BUILDERS = {**builders_a.BUILDERS, **builders_b.BUILDERS, **builders_c.BUILDERS}


def main() -> int:
    only = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
    P = pd.read_parquet(B.OUT / "_panel_aug.parquet")
    P_sw = B.swap_full(P)
    rows = []
    for hid in sorted(BUILDERS):
        if only and hid not in only:
            continue
        t0 = time.time()
        cols, cols_sw = BUILDERS[hid](P), BUILDERS[hid](P_sw)
        for j, (name, (x, kind)) in enumerate(cols.items()):
            x = np.asarray(x, float)
            y = np.asarray(cols_sw[name][0], float)
            ok = np.isfinite(x) & np.isfinite(y)
            same_missing = bool((np.isfinite(x) == np.isfinite(y)).all())
            if kind == "diff":
                swap = same_missing and bool(np.allclose(x[ok], -y[ok], atol=1e-7, rtol=1e-5))
            else:
                swap = same_missing and bool(np.allclose(x[ok], y[ok], atol=1e-7, rtol=1e-5))
            r = {"hid": hid, "column": name, "primary": j == 0, "kind": kind, "swap_ok": swap}
            r.update(B.coverage(P, x))
            r.update(B.r2_on_inputs(P, x, kind))
            m = np.isfinite(x) & P["season"].between(*B.DISC).to_numpy()
            r["share_nonzero_disc"] = round(float((x[m] != 0).mean()), 4) if m.any() else np.nan
            rows.append(r)
        B.C.log(f"{hid}: {len(cols)} column(s), {time.time() - t0:.1f}s")
    out = pd.DataFrame(rows)
    path = B.OUT / "feasibility_metrics.csv"
    if only and path.exists():
        old = pd.read_csv(path)
        out = pd.concat([old[~old["hid"].isin(only)], out], ignore_index=True).sort_values(["hid", "column"])
    out.to_csv(path, index=False)
    with pd.option_context("display.width", 220, "display.max_rows", 300):
        print(out.drop(columns=["r2_rows"]).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

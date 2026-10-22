"""Diagnostic of the M0 check (22 Oct 2026, 08:00): M0's 2019 seed-0 fit reproduced the instance's stored fit only to
1.2e-4. Three fits with M0's 2019 training rows and seed 0 separate the causes:
    a   the query exactly as the instance asked it (the main block alone)
    b   the query as fits.py asked it (main, then qualifying) - a repeat of the checked fit
    c   b again (run-to-run determinism)
Each is compared with the stored fit (instance) and with fits.py's file (M0__2019__seed0.npz), on the main block.
Also compared: the stored fit's metadata (training shape, versions, checkpoint, config) with fits.py's.
Writes data/studies/qualifying_targets/diag_m0.json.
Run: ./python_tabpfn_local.sh src/eda/qualifying_targets/diag_m0.py
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

from src.eda.qualifying_targets import common as C  # noqa: E402
from src.eda.qualifying_targets import fits as F  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402


def main() -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    P, cols, main_frame, q = F.load()
    X_train, y_train, _, blocks = F.job("M0", 2019, P, cols, main_frame, q)
    with np.load(C.INSTANCE / "fits" / "model__2019__seed0.npz", allow_pickle=False) as z:
        stored, stored_meta = z["p_td"], json.loads(str(z["meta"]))
    with np.load(C.LOCAL / "M0__2019__seed0.npz", allow_pickle=False) as z:
        mine, mine_meta = z["p_main"], json.loads(str(z["meta"]))
    queries = {"a_main_only": blocks["main"][0],
               "b_main_then_qual": pd.concat([blocks["main"][0], blocks["qual"][0]], ignore_index=True),
               "c_repeat_of_b": pd.concat([blocks["main"][0], blocks["qual"][0]], ignore_index=True)}
    n = len(blocks["main"][0])
    out = {"stored_meta": {k: stored_meta.get(k) for k in ("train_shape", "versions", "checkpoint", "config", "device",
                                                           "fingerprint", "query_rows")},
           "fits_py_meta": {k: mine_meta.get(k) for k in ("train_shape", "versions", "checkpoint", "config", "device",
                                                           "fingerprint", "query_rows")},
           "train_X_equal_to_the_instance_job": None, "runs": {}}
    # the instance's own job data (serve_speed_tabpfn/arms.job_data on its frame) against F.job's
    from src.eda.serve_speed_tabpfn import arms as A
    Xi, yi, Xti, idi = A.job_data(main_frame, cols, 2019)
    out["train_X_equal_to_the_instance_job"] = bool(np.array_equal(Xi.to_numpy(), X_train.to_numpy(), equal_nan=True)
                                                    and np.array_equal(yi, y_train))
    for name, Xq in queries.items():
        clf = runtime.classifier(**SC.CONFIG, random_state=0)
        clf.fit(X_train, y_train)
        p = clf.predict_proba(Xq)[:, 1][:n]
        out["runs"][name] = {"max_abs_vs_stored": float(np.abs(p - stored).max()),
                             "max_abs_vs_fits_py": float(np.abs(p - mine).max()),
                             "equal_stored": bool(np.array_equal(p, stored)), "equal_fits_py": bool(np.array_equal(p, mine))}
        out["runs"][name]["p_head"] = [float(x) for x in p[:3]]
        del clf
        torch.cuda.empty_cache()
    out["stored_head"] = [float(x) for x in stored[:3]]
    out["fits_py_head"] = [float(x) for x in mine[:3]]
    C.write_json(C.OUT / "diag_m0.json", out)
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

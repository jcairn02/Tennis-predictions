"""Red team (S3), step 0: run the FROZEN B-INJ builder (f26 via screen_batch.evaluate, g5_build's approach) on the
2013-2024 panel and save what it returns, so the independent re-implementation (binj_redo.py) can be compared with it.

Reads no result: the panel's a_won is dropped before the builder sees it, and max_season = 2024. Writes only
data/studies/feature_interactions/redteam/frozen_binj_2024.parquet (+ .json with the dict keys and the hash check).

Run: ./python.sh src/eda/feature_interactions/redteam/frozen_dump.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen_batch as B  # noqa: E402
from src.eda.feature_interactions.g5_build import spec_of  # noqa: E402
from src.eda.feature_interactions.history import long_table  # noqa: E402
from src.eda.feature_interactions.panel import panel  # noqa: E402

OUT = C.OUT / "redteam"


def main() -> int:
    warnings.simplefilter("ignore")
    spec = spec_of("B-INJ")
    L = long_table()
    P = panel(max_season=2024).drop(columns=["a_won"])
    new = spec["prepare"](P, L) if spec.get("prepare") else {}
    r = B.evaluate(spec, P.assign(**new))
    frame = pd.DataFrame({"match_id": P["match_id"].astype(str).to_numpy(), "season": P["season"].to_numpy(),
                          "tour": P["tour"].astype(str).to_numpy()})
    info = {"spec_keys": sorted(spec), "prepare_keys": sorted(new), "result_keys": sorted(r)}
    for k, v in new.items():
        frame[f"prep__{k}"] = np.asarray(v, float)
    frame["x"] = np.asarray(r["x"], float)
    for k, v in r.items():
        if k == "tabpfn":
            for name, (arr, kind, partner) in v.items():
                frame[f"tab__{name}"] = np.asarray(arr, float)
        elif isinstance(v, np.ndarray) and v.ndim == 1 and len(v) == len(P) and k != "x":
            frame[f"res__{k}"] = v.astype(float)
        elif isinstance(v, np.ndarray) and v.ndim == 2 and len(v) == len(P):
            info[f"shape__{k}"] = list(v.shape)
            for j in range(v.shape[1]):
                frame[f"res__{k}__{j}"] = v[:, j].astype(float)
        elif isinstance(v, (list, tuple, str, int, float)):
            info[f"val__{k}"] = v if not isinstance(v, tuple) else list(v)
    frozen = pd.read_csv(B.HYP / "hypothesis_table.csv").set_index("hid").loc["B-INJ", "x_sha256"]
    info["x_matches_frozen_hash"] = B.sha_array(r["x"]) == frozen
    frame.to_parquet(OUT / "frozen_binj_2024.parquet", index=False)
    C.write_json(OUT / "frozen_binj_2024.json", info)
    C.log(f"saved {frame.shape}; {info}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

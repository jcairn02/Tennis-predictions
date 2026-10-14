"""The base frame for the surface-IOS TabPFN test: the best 2026 model's 54 inputs on every main-tour match with closing
odds, 2013-2026, with the leak-proof IOS inputs (the 5 Oct 2026 refit's upload, src/eda/tabpfn_leakproof/).

Starts from the original study's frame (src/eda/tabpfn_thinking/: its training rows 2013-2021 and test rows 2022-2026,
in its order), swaps the 22 IOS inputs for their leak-proof versions exactly as tabpfn_leakproof/build_frame.py did, and
checks the result against that study's verified upload value for value (its X_train for 2013-2021, the first half of its
X_query for 2022-2026). Everything else (the odds, the other 31 inputs, the match context) is unchanged.

Writes data/studies/surface_ios/base_frame.parquet: match_id, tour, year, tournament_date, a_won, the level group,
the surface code, p_mkt (the de-vigged average closing probability), split (train / test as in the original study) and
the 54 inputs as in_<model name>.
Run: ./python.sh src/eda/surface_ios/frames.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.tabpfn_leakproof import common as L  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

BASE = C.OUT / "base_frame.parquet"
NAMES = T.TABPFN_NAMES                      # the odds' log-odds, then the 53 inputs, in the model's order


def same(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    return a.shape == b.shape and np.array_equal(a.to_numpy(dtype="float64"), b.to_numpy(dtype="float64"),
                                                 equal_nan=True)


def build() -> pd.DataFrame:
    f = pd.read_parquet(T.OUT / "frame.parquet")
    f = f[f["tabpfn_split"].isin(["train", "test"])].reset_index(drop=True)
    X = pd.DataFrame({n: f[f"in_{n}"].to_numpy(dtype="float64") for n in NAMES})
    lp = pd.read_parquet(L.LEAKPROOF, columns=["match_id"] + list(L.REPLACED.values()))
    lp = f[["match_id"]].merge(lp, on="match_id", how="left", validate="one_to_one")
    for name, col in L.REPLACED.items():
        X[name] = lp[col].to_numpy(dtype="float64")
    X_train0, _, X_query0, _, _ = L.load_upload()       # the leak-proof refit's verified upload
    tr, te = (f["tabpfn_split"] == "train").to_numpy(), (f["tabpfn_split"] == "test").to_numpy()
    n = int(te.sum())
    if not same(X[tr].reset_index(drop=True), X_train0) or not same(X[te].reset_index(drop=True),
                                                                     X_query0.iloc[:n].reset_index(drop=True)):
        raise RuntimeError("the base frame does not reproduce the leak-proof refit's upload")
    meta = pd.DataFrame({"match_id": f["match_id"].to_numpy(), "tour": f["tour"].to_numpy(),
                         "year": f["year"].to_numpy().astype(int), "tournament_date": f["tournament_date"].to_numpy(),
                         "a_won": f["a_won"].astype(int).to_numpy(), "group": f["group"].to_numpy(),
                         "surface_code": f["in_surface"].to_numpy(), "p_mkt": f["p_mkt"].to_numpy(dtype="float64"),
                         "split": f["tabpfn_split"].to_numpy()})
    out = pd.concat([meta, X.add_prefix("in_")], axis=1)
    if out[[f"in_{n}" for n in NAMES]].isna().all(axis=0).any():
        raise RuntimeError("an input is missing on every row")
    return out


def main() -> int:
    C.OUT.mkdir(parents=True, exist_ok=True)
    out = build()
    out.to_parquet(BASE, index=False)
    C.log(f"wrote {BASE.name}: {len(out):,} matches; train {int((out['split'] == 'train').sum()):,}, test "
          f"{int((out['split'] == 'test').sum()):,}; reproduces the leak-proof upload exactly")
    print(pd.crosstab(out["year"], out["tour"]).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())

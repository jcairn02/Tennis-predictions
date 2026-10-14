"""Build the exact upload for the leak-proof refit (src/eda/tabpfn_leakproof/).

Starts from the original study's verified upload (src/eda/tabpfn_thinking/: X_train, y_train, X_query, query_ids) and
its frame (which fixes the row order of the training and test matches), and swaps the inputs in common.REPLACED for
their leak-proof versions. Before anything is written it checks that:

    * the frame's inputs reproduce the original upload exactly (so the row mapping is right);
    * every column outside REPLACED is identical to the original upload, value for value;
    * the labels and the query's identifiers are the original ones;
    * the query's second half is its first half with A and B swapped;
    * the leak-proof table covers every row the original covered.

Writes data/studies/tabpfn_leakproof/upload/ (X_train.parquet, y_train.npy, X_query.parquet, query_ids.parquet),
manifest.json (hashes, both uploads' fingerprints, the replaced inputs) and input_changes.csv (how far each replaced
input moved).
Run: ./python.sh src/eda/tabpfn_leakproof/build_frame.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_leakproof import common as C  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402
from src.eda.tabpfn_thinking import dispatch as OD  # noqa: E402   (its load_upload verifies the original upload)


def same(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    return a.shape == b.shape and np.array_equal(a.to_numpy(dtype="float64"), b.to_numpy(dtype="float64"),
                                                 equal_nan=True)


def changes(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, col in C.REPLACED.items():
        a, b = old[name].to_numpy(dtype="float64"), new[name].to_numpy(dtype="float64")
        both = np.isfinite(a) & np.isfinite(b)
        sd = float(np.std(a[both]))
        rows.append({"input": name, "leakproof_column": col, "rows": int(len(a)),
                     "covered_original": int(np.isfinite(a).sum()), "covered_leakproof": int(np.isfinite(b).sum()),
                     "changed_rows": int((both & (a != b)).sum()), "correlation": float(np.corrcoef(a[both], b[both])[0, 1]),
                     "median_abs_change_in_sd": float(np.median(np.abs(a[both] - b[both])) / sd),
                     "p99_abs_change_in_sd": float(np.quantile(np.abs(a[both] - b[both]), 0.99) / sd)})
    return pd.DataFrame(rows)


def main() -> int:
    from src.eda.lower_level_evidence import level_layer_ios as _LLEIOS  # lower_level_evidence C2 (sandbox only)
    _LLEIOS.require_consistent(ROOT, "ios_part")  # lower_level_evidence C2 (sandbox only)
    X0_train, y0_train, X0_query, manifest0 = OD.load_upload()
    ids0 = pd.read_parquet(T.UPLOAD / "query_ids.parquet")
    f = pd.read_parquet(T.OUT / "frame.parquet")
    tr, te = (f["tabpfn_split"] == "train").to_numpy(), (f["tabpfn_split"] == "test").to_numpy()
    X_frame = pd.DataFrame({n: f[f"in_{n}"].to_numpy(dtype="float64") for n in C.NAMES})
    n = int(te.sum())
    if not (same(X_frame[tr].reset_index(drop=True), X0_train)
            and same(X_frame[te].reset_index(drop=True), X0_query.iloc[:n].reset_index(drop=True))):
        raise RuntimeError("the original frame does not reproduce the original upload")
    if not (np.array_equal(f.loc[tr, "a_won"].astype("int64").to_numpy(), y0_train)
            and np.array_equal(f.loc[te, "match_id"].to_numpy(), ids0["match_id"].to_numpy()[:n])):
        raise RuntimeError("labels or query identifiers differ from the original upload")

    lp = pd.read_parquet(C.LEAKPROOF, columns=["match_id"] + list(C.REPLACED.values()))
    lp = f[["match_id"]].merge(lp, on="match_id", how="left", validate="one_to_one")
    X_new = X_frame.copy()
    for name, col in C.REPLACED.items():
        X_new[name] = lp[col].to_numpy(dtype="float64")
        lost = np.isfinite(X_frame[name].to_numpy()) & ~np.isfinite(X_new[name].to_numpy()) & (tr | te)
        if lost.any():
            raise RuntimeError(f"{name}: the leak-proof table lacks {int(lost.sum())} rows the original covered")

    X_train = X_new[tr].reset_index(drop=True)
    X_test = X_new[te].reset_index(drop=True)
    X_query = pd.concat([X_test, T.flip(X_test)], ignore_index=True)
    kept = [c for c in C.NAMES if c not in C.REPLACED]
    if not (same(X_train[kept], X0_train[kept]) and same(X_query[kept], X0_query[kept])):
        raise RuntimeError("a column outside REPLACED differs from the original upload")
    if not np.allclose(T.flip(X_query.iloc[n:]).to_numpy(), X_query.iloc[:n].to_numpy(), equal_nan=True):
        raise RuntimeError("the query's second half is not the first half with A and B swapped")

    C.UPLOAD.mkdir(parents=True, exist_ok=True)
    X_train.to_parquet(C.UPLOAD / "X_train.parquet", index=False)
    np.save(C.UPLOAD / "y_train.npy", y0_train)
    X_query.to_parquet(C.UPLOAD / "X_query.parquet", index=False)
    ids0.to_parquet(C.UPLOAD / "query_ids.parquet", index=False)
    ch = pd.concat([changes(X0_train, X_train).assign(part="train"),
                    changes(X0_query.iloc[:n].reset_index(drop=True), X_test).assign(part="test")])
    ch.to_csv(C.OUT / "input_changes.csv", index=False)
    fp = C.fingerprint(X_train, y0_train, X_query)
    manifest = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "original_study": "src/eda/tabpfn_thinking", "original_input_fingerprint": manifest0["input_fingerprint"],
        "sources": {name: {"path": str(p.relative_to(ROOT)), "sha256": C.sha256_file(p)}
                    for name, p in (("original_frame", T.OUT / "frame.parquet"), ("leakproof_features", C.LEAKPROOF),
                                    ("timing", ROOT / "data/studies/match_timing/timing.parquet"))},
        "names": C.NAMES, "replaced": C.REPLACED, "unchanged": kept,
        "categorical": manifest0["categorical"], "categorical_indices": manifest0["categorical_indices"],
        "shapes": {"X_train": list(X_train.shape), "X_query": list(X_query.shape)},
        "fit_description": manifest0["fit_description"],
        "upload_sha256": {p.name: C.sha256_file(p) for p in sorted(C.UPLOAD.glob("*")) if p.is_file()},
        "input_fingerprint": fp,
    }
    C.write_json(C.OUT / "manifest.json", manifest)
    C.log(f"upload: X_train {X_train.shape}, X_query {X_query.shape}; {len(C.REPLACED)} inputs replaced, "
          f"{len(kept)} identical to the original; fingerprint {fp[:16]}...")
    C.log(ch.groupby("part")[["correlation", "median_abs_change_in_sd"]].describe().round(4).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())

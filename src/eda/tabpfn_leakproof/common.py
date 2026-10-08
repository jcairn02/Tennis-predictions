"""Shared definitions for the leak-proof refit of the best 2026 model (src/eda/tabpfn_leakproof/).

The owner's request of 5 Oct 2026: rebuild the solved-together (IOS) inputs of the TabPFN-3.5-Thinking model of
src/eda/tabpfn_thinking/ (the closing odds plus 53 pre-match inputs, main tour, trained on 2013-2021 and scored on
2022-2026) on the leak-proof match timeline of src/eda/match_timing/, make ONE paid fit on exactly the same matches,
and see whether the predictive value changes.

The design (fixed before the paid call):

    same rows     the original upload's training rows and query rows (the test matches, then the same matches with A
                  and B swapped), in the same order
    same inputs   the original upload's 54 columns in the same order. The inputs in REPLACED are swapped for their
                  leak-proof versions (data/studies/match_timing/leakproof_features.parquet); every other column is
                  checked to be identical to the original upload, value for value
    same config   guard.CONFIG equals the original guard's (8 estimators, softmax temperature 0.9, seed 0, thinking
                  effort high, log-loss metric)
    scoring       the original study's: per tour, 2022-2026 and 2026 alone, against the closing odds recalibrated on
                  the training matches and against the original fit, paired 95% intervals over four-week blocks

Every number in the write-up is read from data/studies/tabpfn_leakproof/ (written by this study's scripts).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import common as T  # noqa: E402

OUT = ROOT / "data" / "studies" / "tabpfn_leakproof"
UPLOAD = OUT / "upload"
THINKING = OUT / "thinking"
LEAKPROOF = ROOT / "data" / "studies" / "match_timing" / "leakproof_features.parquet"

# model input -> column of the leak-proof table. The solved-together inputs: IOS offence and defence on seven
# statistics, their matchup products, and the short-memory IOS points matchup (4 weeks men, 13 women)
REPLACED = {f"ios{k}_{s}": f"ios_{k}_{s}|single" for s in T.IOS_STATS for k in ("O", "D")}
REPLACED.update({f"prod_{s}": f"prod_{s}|single" for s in T.IOS_STATS})
REPLACED["ios_points_short"] = "ios_short"

NAMES = T.TABPFN_NAMES                      # the original order: the odds' log-odds, then the 53 inputs
log, write_json, fingerprint, sha256_file = T.log, T.write_json, T.fingerprint, T.sha256_file


def load_upload() -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame, pd.DataFrame, dict]:
    """The prepared upload, checked against its manifest (file hashes and the value fingerprint)."""
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    for name, sha in manifest["upload_sha256"].items():
        if sha256_file(UPLOAD / name) != sha:
            raise RuntimeError(f"upload/{name} differs from the manifest; rebuild with build_frame.py")
    X_train = pd.read_parquet(UPLOAD / "X_train.parquet")
    y_train = np.load(UPLOAD / "y_train.npy", allow_pickle=False)
    X_query = pd.read_parquet(UPLOAD / "X_query.parquet")
    ids = pd.read_parquet(UPLOAD / "query_ids.parquet")
    if list(X_train.columns) != NAMES or list(X_query.columns) != NAMES or manifest["names"] != NAMES:
        raise RuntimeError("upload columns differ from the original model's inputs")
    if fingerprint(X_train, y_train, X_query) != manifest["input_fingerprint"]:
        raise RuntimeError("the value fingerprint differs from the manifest")
    n = len(X_query) // 2
    if len(ids) != len(X_query) or not np.array_equal(ids["orientation"].to_numpy(), np.r_[np.zeros(n), np.ones(n)]):
        raise RuntimeError("query identifiers do not match the doubled query")
    return X_train, y_train, X_query, ids, manifest

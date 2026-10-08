"""Frozen inputs and safe file loading for one new frontier TabPFN experiment."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.eda.tabpfn_thinking.common import fingerprint, sha256_file
from src.eda.predictive_frontier.score import STRONG
from src.eda.predictive_frontier.features import FEATURE_COLUMNS

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/studies/predictive_frontier_tabpfn"
UPLOAD = OUT / "upload"
THINKING = OUT / "thinking"
SPORTS = STRONG + FEATURE_COLUMNS
RENAMES = dict(zip(STRONG, ["elo_logit", "serve_return_matchup_logit", "recent_adjusted_total_points",
    "short_memory_serve_return_matchup", "games_weighted_elo_logit", "observed_14d_sets_log_difference",
    "surface_familiarity_difference", "age_difference", "age_centered_squared_difference"]))
NAMES = [RENAMES.get(c, c) for c in SPORTS]


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def flip(frame):
    """Every one of the 36 sports inputs reverses when players are swapped."""
    changed = frame.copy()
    changed[NAMES] *= -1
    return changed


def load_upload():
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    for relative, expected in manifest["artifact_sha256"].items():
        if sha256_file(OUT / relative) != expected:
            raise ValueError(f"Prepared artifact changed: {relative}")
    train = pd.read_parquet(UPLOAD / "X_train.parquet")
    labels = np.load(UPLOAD / "y_train.npy", allow_pickle=False)
    query = pd.read_parquet(UPLOAD / "X_query.parquet")
    ids = pd.read_parquet(UPLOAD / "query_ids.parquet")
    if list(train) != NAMES or list(query) != NAMES or manifest["names"] != NAMES:
        raise ValueError("Model columns do not match the frozen 36 sports specification")
    if fingerprint(train, labels, query) != manifest["input_sha256"]:
        raise ValueError("Input values do not match the frozen manifest")
    if len(query) != len(ids) or len(query) % 2:
        raise ValueError("Query identifiers do not match the doubled prediction input")
    n = len(query)//2
    if not np.array_equal(ids.match_id.iloc[:n].to_numpy(), ids.match_id.iloc[n:].to_numpy()):
        raise ValueError("The two query orientations use different match IDs")
    if not np.array_equal(ids.orientation.to_numpy(), np.r_[np.zeros(n), np.ones(n)]):
        raise ValueError("Wrong query orientation order")
    if not np.array_equal(flip(query.iloc[:n]).to_numpy(), query.iloc[n:].to_numpy()):
        raise ValueError("Query sides were not flipped correctly")
    return train, labels, query, ids, manifest

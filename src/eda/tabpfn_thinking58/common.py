"""Shared definitions for ONE TabPFN-3.5-Thinking fit on the current best model's 58 inputs (src/eda/tabpfn_thinking58/).

The owner's request of 8 Oct 2026: "Do ONE paid fit to close the gap on the 58 columns and compare tabpfn3.5
nonthinking calibrated to tabpfn 3.5 thinking noncalibrated. When doing so also compose ROI against betonline/pinnacle
close." The only Thinking fits so far (src/eda/tabpfn_thinking/, src/eda/tabpfn_leakproof/) used the 54 inputs from
before the owner's decisions of 6 Oct 2026; every result on the 58 inputs came from the local non-thinking model.

The design (fixed before the paid call):

    rows      the 58-input model frame (data/studies/surface_rating_race/model/model_frame.parquet): the leak-proof
              refit's 39,918 training matches (main tour with closing odds, 2013-2021) and 23,819 test matches
              (2022-2026), in the frame's order; labels and test ids checked equal to the leak-proof upload's
    inputs    the 58 inputs in model_inputs.json's order; the 31 kept from the leak-proof refit checked value for value
    query     block "td": the test matches as stored, then with A and B swapped (flip below);
              block "early": the 2025-2026 test matches with a Polymarket price 24 hours before the listed start, with
              odds_logit replaced by that price (the rating race's early block, the same matches), stored then swapped
    config    the leak-proof refit's guard configuration (8 estimators, softmax temperature 0.9, seed 0, thinking effort
              high, log-loss metric): ONE fit and ONE prediction batch (guard.py)
    the twin  the local open checkpoint on exactly this upload and these settings, without thinking: seeds 0-3
              (local_twin.py), free
    scoring   score.py, written and run on the free forecasts before the paid call: the comparisons, then the return
              at the BetOnline and Pinnacle closes (books.py) under the owner's staking rule (stake below)

Every number in the write-up is read from data/studies/tabpfn_thinking58/ (written by this study's scripts).
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

OUT = ROOT / "data" / "studies" / "tabpfn_thinking58"
DOCS = ROOT / "docs" / "studies" / "tabpfn_thinking58"
UPLOAD = OUT / "upload"
THINKING = OUT / "thinking"                   # the paid fit's receipts and returned probabilities (guard.py)
LOCAL = OUT / "local"                         # the twin's fits, one file per seed (local_twin.py)
MODEL = ROOT / "data" / "studies" / "surface_rating_race" / "model"
MODEL_FRAME = MODEL / "model_frame.parquet"
MODEL_INPUTS = MODEL / "model_inputs.json"
EARLY = ROOT / "data" / "studies" / "surface_elo_pieces" / "early_price_frame.parquet"
LEAKPROOF = ROOT / "data" / "studies" / "tabpfn_leakproof"

TOURS = ("atp", "wta")
TEST_YEARS = tuple(range(2022, 2027))
PRICE_SEASONS = (2025, 2026)                  # the seasons with Polymarket prices (the rating race's early block)
PRICE_EPS = 1e-6                              # the race's clip of the 24-hour price before its logit
TWIN_SEEDS = (0, 1, 2, 3)                     # seed 0 mirrors the paid fit's random_state
BLOCKS = ("td", "early")

log, write_json, fingerprint, sha256_file = T.log, T.write_json, T.fingerprint, T.sha256_file


# ------------------------------------------------------------------------------------------------
# The inputs and the swap of A and B

def model_inputs() -> list[dict]:
    """The 58 inputs of the owner's decisions of 6 Oct 2026, in the model's order, each with its kind."""
    return json.loads(MODEL_INPUTS.read_text(encoding="utf-8"))["inputs"]


def partner(name: str) -> str:
    """The other player's column of an (A, B) pair: surf_season_a <-> surf_season_b."""
    if name.endswith("_a"):
        return name[:-2] + "_b"
    if name.endswith("_b"):
        return name[:-2] + "_a"
    raise ValueError(f"{name} is not an (A, B) pair column")


def flip(X: pd.DataFrame, kinds: dict[str, str]) -> pd.DataFrame:
    """The same matches with A and B swapped: every A - B difference (the odds' log-odds included) negated, each (A, B)
    pair exchanged, the match context unchanged."""
    unknown = [c for c in X.columns if kinds.get(c) not in ("diff", "pair", "context")]
    if unknown:
        raise ValueError(f"no kind for {unknown}")
    out = X.copy()
    diff = [c for c in X.columns if kinds[c] == "diff"]
    out[diff] = -X[diff]
    for c in [c for c in X.columns if kinds[c] == "pair"]:
        out[c] = X[partner(c)].to_numpy()
    return out


# ------------------------------------------------------------------------------------------------
# The owner's staking rule (8 Oct 2026)

def stake(d) -> np.ndarray:
    """Units staked on a side at decimal odds d. The owner's words: "Bet 1 unit at even, bet X units to win 1 on favorites
    and slightly <1 unit on underdogs proportional to how much of an underdog they are, partially informed by what you
    think kelly would want (win more than 1 unit, but not an exact 1to1)."

        d <= 2  (favourite, or even money)   1 / (d - 1) units: wins exactly 1 unit; 1 unit at d = 2
        d >  2  (underdog)                   d / (2 (d - 1)) units: wins d / 2 units (more than 1)

    The underdog stake is Kelly's shape. Kelly stakes f = (p d - 1) / (d - 1) of the bankroll; with an edge of the same
    size in probability at every price, p = 1/d + delta, that is delta d / (d - 1), proportional to d / (d - 1). Scaled
    to 1 unit at even money it is d / (2 (d - 1)): 0.83 units at 2.50, 0.75 at 3.00, 0.63 at 5.00, tending to 0.5. On
    favourites the owner's to-win-1 rule stakes 2/d times that Kelly shape (2.0 units at 1.50, where the shape gives
    1.5). The two branches meet at 1 unit at d = 2."""
    d = np.asarray(d, dtype=float)
    if np.any(~np.isfinite(d) | (d <= 1.0)):
        raise ValueError("decimal odds must be finite and above 1")
    return np.where(d <= 2.0, 1.0 / (d - 1.0), d / (2.0 * (d - 1.0)))


# ------------------------------------------------------------------------------------------------
# The upload

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
    names = manifest["names"]
    if list(X_train.columns) != names or list(X_query.columns) != names or len(names) != 58:
        raise RuntimeError("upload columns differ from the manifest's 58 inputs")
    if fingerprint(X_train, y_train, X_query) != manifest["input_fingerprint"]:
        raise RuntimeError("the value fingerprint differs from the manifest")
    if len(ids) != len(X_query) or set(ids["block"]) != set(BLOCKS):
        raise RuntimeError("query identifiers do not match the query")
    return X_train, y_train, X_query, ids, manifest


def load_twin_seed(seed: int, fingerprint: str, n_rows: int) -> np.ndarray:
    """P(A wins) for every query row from a saved twin fit (local_twin.py), checked against the upload's fingerprint."""
    with np.load(LOCAL / f"seed{seed}.npz", allow_pickle=False) as z:
        meta = json.loads(str(z["meta"]))
        p = z["p_a"].astype(float)
    if meta["input_fingerprint"] != fingerprint or len(p) != n_rows or not np.isfinite(p).all():
        raise RuntimeError(f"seed{seed}.npz does not belong to this upload")
    return p


def symmetrised(p_a: np.ndarray, ids: pd.DataFrame) -> dict[str, pd.Series]:
    """{block: P(A wins) by match id}, the mean of P(A | x) and 1 - P(A | x swapped), from one fit's query output."""
    p_a = np.asarray(p_a, dtype=float)
    if len(p_a) != len(ids):
        raise ValueError("one probability per query row is needed")
    out = {}
    for b in BLOCKS:
        k = (ids["block"] == b).to_numpy()
        stored, swapped = k & (ids["orientation"] == 0).to_numpy(), k & (ids["orientation"] == 1).to_numpy()
        a, s = ids.loc[stored, "match_id"].to_numpy(), ids.loc[swapped, "match_id"].to_numpy()
        if not np.array_equal(a, s):
            raise RuntimeError(f"block {b}: the swapped rows are not the stored rows' matches in order")
        out[b] = pd.Series(T.symmetrize(p_a[stored], p_a[swapped]), index=a.astype(str))
    return out

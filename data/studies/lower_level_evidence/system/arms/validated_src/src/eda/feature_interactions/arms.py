"""The arms (input sets) of the TabPFN fits, the frame they read and how a match is flipped.

Every arm starts from the model's 58 inputs (MODEL_FRAME, columns in_<name>, in the model's order) and appends new
inputs registered in data/studies/feature_interactions/features/registry.json:

    {"<name>": {"family": "<file stem>", "kind": "diff" | "context" | "pair", "partner": "<name>" (pairs only),
                "desc": "..."}}

with values in features/<family>.parquet (match_id + one column per input). Kinds, as the model frame's:
    diff     A - B (or any antisymmetric value): negated when A and B swap
    context  describes the match (symmetric): unchanged when they swap
    pair     an (A, B) couple: exchanged with its partner when they swap

ARMS maps an arm to its extra inputs; "model" is the 58 inputs alone. An arm "<arm>_noodds" drops odds_logit.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C

ARMS: dict[str, list[str]] = {"model": []}      # extra inputs per arm; filled as finalists are chosen
# H-S2 (plan.md): the players' sums of the model's own player inputs, 17 context columns
ARMS["levels"] = ([f"lv_{k}_{s}" for k in ("iosO", "iosD") for s in ("ace", "df", "first_in", "first_won", "second_won",
                                                                     "hold", "bp_saved")]
                  + ["lv_elo", "lv_age", "lv_sets14"])
# M2 (plan.md, "Fixed at M1"): the one bundle-eligible member's G5 arm, B-INJ's three frozen deployment columns
ARMS["binj"] = ["bdinj_I043", "bdinj_I044", "bdinj_I045"]


def base_inputs() -> tuple[list[str], dict[str, str], dict[str, str]]:
    """(the 58 input names in order, kind per input, pair partner per pair input)."""
    meta = json.loads(C.MODEL_INPUTS.read_text(encoding="utf-8"))
    names = [d["name"] for d in meta["inputs"]]
    kinds = {d["name"]: d["kind"] for d in meta["inputs"]}
    partners = {}
    for n, k in kinds.items():
        if k == "pair":
            stem, side = n.rsplit("_", 1)
            partners[n] = f"{stem}_{'b' if side == 'a' else 'a'}"
    return names, kinds, partners


def registry() -> dict:
    path = C.FEATURES / "registry.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def arm_inputs(arm: str) -> list[str]:
    names, _, _ = base_inputs()
    stem = arm[:-len("_noodds")] if arm.endswith("_noodds") else arm
    cols = names + [c for c in ARMS[stem] if c not in names]
    return [c for c in cols if c != "odds_logit"] if arm.endswith("_noodds") else cols


def kinds_and_partners(cols: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    _, kinds, partners = base_inputs()
    reg = registry()
    for c in cols:
        if c in kinds:
            continue
        if c not in reg:
            raise KeyError(f"input {c} is neither a model input nor registered in features/registry.json")
        kinds[c] = reg[c]["kind"]
        if reg[c]["kind"] == "pair":
            partners[c] = reg[c]["partner"]
    return kinds, partners


def load_frame(extra: list[str]) -> pd.DataFrame:
    """The model frame (every season) with the requested registered inputs joined by match id (in_<name>)."""
    f = pd.read_parquet(C.MODEL_FRAME)
    reg = registry()
    for fam in sorted({reg[c]["family"] for c in extra}):
        cols = [c for c in extra if reg[c]["family"] == fam]
        t = pd.read_parquet(C.FEATURES / f"{fam}.parquet", columns=["match_id"] + cols)
        t = f[["match_id"]].merge(t, on="match_id", how="left", validate="one_to_one")
        for c in cols:
            f[f"in_{c}"] = t[c].to_numpy(dtype="float64")
    return f


def matrix(frame: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return pd.DataFrame({c: frame[f"in_{c}"].to_numpy(dtype="float64") for c in cols})


def flip(X: pd.DataFrame) -> pd.DataFrame:
    """The same matches with A and B swapped: diffs negated, pairs exchanged, context unchanged."""
    kinds, partners = kinds_and_partners(list(X.columns))
    out = X.copy()
    anti = [c for c in X.columns if kinds[c] == "diff"]
    out[anti] = -X[anti]
    for c in X.columns:
        if kinds[c] == "pair":
            out[c] = X[partners[c]].to_numpy()
    return out


def job_data(frame: pd.DataFrame, cols: list[str], season: int):
    """(X_train, y_train, X_test, test match ids): training 2013 .. season - 1, test = the season's matches."""
    tr = frame["season"].between(C.TRAIN_FROM, season - 1).to_numpy()
    te = (frame["season"] == season).to_numpy()
    X = matrix(frame, cols)
    return (X[tr].reset_index(drop=True), frame.loc[tr, "a_won"].astype("int64").to_numpy(),
            X[te].reset_index(drop=True), frame.loc[te, "match_id"].to_numpy())


def check_flip(frame: pd.DataFrame, cols: list[str]) -> bool:
    X = matrix(frame, cols)
    return bool(np.allclose(flip(flip(X)).to_numpy(), X.to_numpy(), equal_nan=True))

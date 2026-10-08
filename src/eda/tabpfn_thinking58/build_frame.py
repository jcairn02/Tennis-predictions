"""Build the exact upload for the one Thinking fit on the 58 inputs (src/eda/tabpfn_thinking58/).

Starts from the 58-input model frame (src/eda/surface_rating_race/model_frame.py) and, before anything is written,
checks that:

    * there are 58 inputs: 48 differences (the odds included), 4 (A, B) pair columns, 6 context columns;
    * the training rows, their labels and the test matches are the leak-proof refit's upload's, in its order;
    * the 31 inputs the 58-input model kept from the leak-proof refit equal its upload value for value;
    * swapping A and B twice gives the query back, and the swapped half is the stored half swapped;
    * the early block's matches are the rating race's early-block matches for the 58-input model ("model" arm), and
      its price is the race's: odds_logit = logit of the Polymarket price 24 hours before the start, clipped at 1e-6.

Writes data/studies/tabpfn_thinking58/upload/ (X_train.parquet, y_train.npy, X_query.parquet, query_ids.parquet) and
manifest.json (hashes, kinds, the fingerprint, the description sent with the fit).
Run: ./python.sh src/eda/tabpfn_thinking58/build_frame.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_leakproof import common as LP  # noqa: E402
from src.eda.tabpfn_thinking58 import common as C  # noqa: E402

RACE_LOCAL = ROOT / "data" / "studies" / "surface_rating_race" / "local"

# The leak-proof refit's description, adapted to the 58 inputs (sent with the fit; informational for the server).
DESCRIPTION = (
    "Professional tennis singles, ATP and WTA main tour (Grand Slams, Tour Finals, 1000, 500, 250 events), seasons "
    "2013-2021; one row per match; player A is assigned at random, so the task is symmetric: swapping A and B negates "
    "the odds column and every difference column, exchanges each _a/_b pair column and flips the label. Target: 1 if "
    "player A won. Inputs are pre-match only: odds_logit, the bookmakers' closing log-odds that A wins (de-vigged "
    "average of the books), which is by far the strongest input; differences (A minus B) of rating systems (overall "
    "Elo log-odds and the two players' surface offsets, serve/return strength ratings, games-weighted Elo), "
    "opponent-adjusted serve/return statistics over a two-week memory, long-memory offence/defence ratings per "
    "statistic on the match's surface, recent load and age; each player's matches on the surface earlier this season "
    "and days since his or her last match on it (_a/_b pairs); plus match context (tour, surface, indoor, level, "
    "best-of, round). The question is whether these inputs improve on the odds. Predictions will be for the later "
    "seasons 2022-2026 and are scored by log loss, so calibration matters.")


def same(a, b) -> bool:
    return bool(np.array_equal(np.asarray(a, dtype="float64"), np.asarray(b, dtype="float64"), equal_nan=True))


def race_early_ids() -> np.ndarray:
    """The rating race's early-block match ids for the 58-input model, 2025 then 2026 (seed 0's files)."""
    out = []
    for season in C.PRICE_SEASONS:
        with np.load(RACE_LOCAL / f"model__{season}__seed0.npz", allow_pickle=False) as z:
            out.append(z["ids_early"].astype(str))
    return np.concatenate(out)


def main() -> int:
    inputs = C.model_inputs()
    names = [i["name"] for i in inputs]
    kinds = {i["name"]: i["kind"] for i in inputs}
    counts = Counter(kinds.values())
    if len(names) != 58 or counts != Counter({"diff": 48, "pair": 4, "context": 6}) or names[0] != "odds_logit":
        raise RuntimeError(f"unexpected inputs: {len(names)} names, kinds {dict(counts)}")
    for c in [c for c in names if kinds[c] == "pair"]:
        if kinds.get(C.partner(c)) != "pair":
            raise RuntimeError(f"{c}: its partner {C.partner(c)} is not a pair column")

    f = pd.read_parquet(C.MODEL_FRAME)
    f["match_id"] = f["match_id"].astype(str)
    tr, te = (f["tabpfn_split"] == "train").to_numpy(), (f["tabpfn_split"] == "test").to_numpy()
    X = pd.DataFrame({n: f[f"in_{n}"].to_numpy(dtype="float64") for n in names})
    X_train, X_test = X[tr].reset_index(drop=True), X[te].reset_index(drop=True)
    y_train = f.loc[tr, "a_won"].astype("int64").to_numpy()
    test_ids = f.loc[te, "match_id"].to_numpy()

    # the leak-proof refit's rows, labels, test matches and the 31 inputs kept from it
    L_train, L_y, L_query, L_ids, _ = LP.load_upload()
    n = len(test_ids)
    kept = [i["name"] for i in inputs if i["source"].endswith("unchanged")]   # the surface profile keeps old names
    checks = {
        "train_rows": len(X_train) == len(L_train) == 39918,
        "test_matches": n == len(L_ids) // 2 == 23819,
        "labels_equal_leakproof": bool(np.array_equal(y_train, L_y)),
        "test_ids_equal_leakproof": bool(np.array_equal(test_ids, L_ids["match_id"].astype(str).to_numpy()[:n])),
        "kept_inputs": len(kept) == 31,
        "kept_equal_leakproof_train": all(same(X_train[c], L_train[c]) for c in kept),
        "kept_equal_leakproof_test": all(same(X_test[c], L_query[c].iloc[:n]) for c in kept),
        "flip_is_an_involution": same(C.flip(C.flip(X_test, kinds), kinds), X_test),
    }

    # the early block: the race's matches and price
    ep = pd.read_parquet(C.EARLY, columns=["match_id", "season", "has_early", "p_early_a"])
    ep["match_id"] = ep["match_id"].astype(str)
    e = ep.set_index("match_id").reindex(test_ids)
    seasons = f.loc[te, "season"].to_numpy()
    ok = e["has_early"].fillna(False).to_numpy(bool) & np.isin(seasons, C.PRICE_SEASONS)
    X_early = X_test[ok].reset_index(drop=True).copy()
    X_early["odds_logit"] = logit(np.clip(e["p_early_a"].to_numpy(dtype=float)[ok], C.PRICE_EPS, 1 - C.PRICE_EPS))
    early_ids = test_ids[ok]
    checks["early_ids_equal_race"] = bool(np.array_equal(early_ids, race_early_ids()))
    checks["early_prices_finite"] = bool(np.isfinite(X_early["odds_logit"]).all())

    X_query = pd.concat([X_test, C.flip(X_test, kinds), X_early, C.flip(X_early, kinds)], ignore_index=True)
    ids = pd.DataFrame({
        "match_id": np.concatenate([test_ids, test_ids, early_ids, early_ids]),
        "block": ["td"] * (2 * n) + ["early"] * (2 * len(early_ids)),
        "orientation": np.concatenate([np.zeros(n), np.ones(n), np.zeros(len(early_ids)), np.ones(len(early_ids))])
        .astype("int64")})
    checks["swapped_halves"] = (same(C.flip(X_query.iloc[n:2 * n].reset_index(drop=True), kinds), X_test)
                                and same(C.flip(X_query.iloc[2 * n + len(early_ids):].reset_index(drop=True), kinds),
                                         X_early))
    bad = [k for k, v in checks.items() if v is not True]
    if bad:
        raise RuntimeError(f"checks failed: {bad}")

    C.UPLOAD.mkdir(parents=True, exist_ok=True)
    X_train.to_parquet(C.UPLOAD / "X_train.parquet", index=False)
    np.save(C.UPLOAD / "y_train.npy", y_train)
    X_query.to_parquet(C.UPLOAD / "X_query.parquet", index=False)
    ids.to_parquet(C.UPLOAD / "query_ids.parquet", index=False)
    fp = C.fingerprint(X_train, y_train, X_query)
    manifest = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "names": names, "kinds": kinds,
        "sources": {name: {"path": str(p.relative_to(ROOT)), "sha256": C.sha256_file(p)}
                    for name, p in (("model_frame", C.MODEL_FRAME), ("model_inputs", C.MODEL_INPUTS),
                                    ("early_price_frame", C.EARLY))},
        "leakproof_input_fingerprint": LP.load_upload()[4]["input_fingerprint"],
        "checks": checks,
        "shapes": {"X_train": list(X_train.shape), "X_query": list(X_query.shape)},
        "query_blocks": {"td_matches": int(n), "early_matches": int(len(early_ids)),
                         "early_by_season": {str(s): int((ok & (seasons == s)).sum()) for s in C.PRICE_SEASONS}},
        "fit_description": DESCRIPTION,
        "upload_sha256": {p.name: C.sha256_file(p) for p in sorted(C.UPLOAD.glob("*")) if p.is_file()},
        "input_fingerprint": fp,
    }
    C.write_json(C.OUT / "manifest.json", manifest)
    C.log(f"upload: X_train {X_train.shape}, X_query {X_query.shape} ({n} test matches x 2, {len(early_ids)} early x 2); "
          f"checks {checks}; fingerprint {fp[:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())

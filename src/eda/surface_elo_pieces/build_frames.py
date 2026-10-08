"""Build the walk-forward frame for the TabPFN-3.5-Plus test and register every paid job.

The frame holds every main-tour match with closing odds of 2013-2026 that the best 2026 model could use (its population:
Grand Slams, Tour Finals, 1000s, 500s, 250s; completed or retired; a supported pre-match format; tabpfn_split set),
with the 54 inputs of the leak-proof refit and the new inputs of arms.py.

Checks before anything is written:
    * the 54 base inputs reproduce the leak-proof refit's upload value for value (its 39,918 training rows and 23,819
      test rows), so the base arm is the current best model's representation exactly;
    * the new inputs exist wherever the surface is known; the flip is an involution and maps every arm's columns
      correctly.

Jobs: one per (stage, arm, season, seed). A job trains on 2013 .. season - 1 and predicts the season's matches as
stored and with A and B swapped (2 x rows), the rows in the frame's order.

    pilot      seasons 2019-2021 (design years): base with seeds 0 and 1, primary and literal with seed 0
    confirm    seasons 2022-2026 (the test): base, primary, literal, elo_only, switch_only, seeds 0, 1, 2
    diagnostic seasons 2022-2026: base and primary without the odds, seed 0 (is a null "priced in" or "unusable"?)

Writes data/studies/surface_elo_pieces/frame.parquet, jobs.json (each job's fingerprint and shapes), frame_manifest.json.
Run: ./python.sh src/eda/surface_elo_pieces/build_frames.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces import arms as A  # noqa: E402
from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.tabpfn_leakproof import common as LP  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

STAGES = {
    "pilot": {"seasons": [2019, 2020, 2021], "runs": [("base", 0), ("base", 1), ("primary", 0), ("literal", 0)]},
    "confirm": {"seasons": [2022, 2023, 2024, 2025, 2026],
                "runs": [(arm, seed) for arm in ("base", "primary", "literal", "elo_only", "switch_only")
                         for seed in (0, 1, 2)]},
    "diagnostic": {"seasons": [2022, 2023, 2024, 2025, 2026], "runs": [("base_noodds", 0), ("primary_noodds", 0)]},
}
KEEP = ["match_id", "tour", "year", "group", "a_won", "p_mkt", "tournament_date", "tournament_name", "tabpfn_split",
        "split"]


def base_inputs(f: pd.DataFrame) -> pd.DataFrame:
    """The 54 inputs of the leak-proof refit for every frame row: the original frame's inputs with the 22 IOS ones
    taken from the leak-proof table."""
    X = pd.DataFrame({n: f[f"in_{n}"].to_numpy(dtype="float64") for n in A.BASE})
    lp = pd.read_parquet(C.LEAKPROOF, columns=["match_id"] + list(LP.REPLACED.values()))
    lp = f[["match_id"]].merge(lp, on="match_id", how="left", validate="one_to_one")
    for name, col in LP.REPLACED.items():
        X[name] = lp[col].to_numpy(dtype="float64")
    return X


def debut_season(frame: pd.DataFrame) -> np.ndarray:
    """True where a player's first match in Stage 0 (any level, since 2010) falls in this match's season: a player
    with no history before this season. Pre-registered after the audit (B1) to leave out of every scored comparison
    the 2026 WTA players who re-appear under new IDs from June 2026 with no history (73 test matches), by a rule that
    is the same in every season (it flags 0-5 matches a season in 2013-2025). Known before the match."""
    m = pd.read_parquet(C.STAGE0, columns=["match_id", "tour", "year", "player_a_id", "player_b_id"])
    first = pd.concat([m[["tour", "player_a_id", "year"]].rename(columns={"player_a_id": "pid"}),
                       m[["tour", "player_b_id", "year"]].rename(columns={"player_b_id": "pid"})]) \
        .groupby(["tour", "pid"])["year"].min()
    ids = frame[["match_id", "tour", "season"]].merge(m[["match_id", "player_a_id", "player_b_id"]], on="match_id",
                                                      how="left", validate="one_to_one")
    fa = first.reindex(pd.MultiIndex.from_arrays([ids["tour"], ids["player_a_id"]])).to_numpy()
    fb = first.reindex(pd.MultiIndex.from_arrays([ids["tour"], ids["player_b_id"]])).to_numpy()
    s = ids["season"].to_numpy()
    return (fa == s) | (fb == s)


def check_against_leakproof_upload(f: pd.DataFrame, X: pd.DataFrame) -> dict:
    X_train, y_train, X_query, ids, _ = LP.load_upload()
    tr = (f["tabpfn_split"] == "train").to_numpy()
    te = (f["tabpfn_split"] == "test").to_numpy()
    n = int(te.sum())
    ok_train = np.array_equal(X[tr].to_numpy(), X_train.to_numpy(dtype="float64"), equal_nan=True)
    ok_test = np.array_equal(X[te].to_numpy(), X_query.iloc[:n].to_numpy(dtype="float64"), equal_nan=True)
    ok_y = np.array_equal(f.loc[tr, "a_won"].astype("int64").to_numpy(), y_train)
    ok_ids = np.array_equal(f.loc[te, "match_id"].to_numpy(), ids["match_id"].to_numpy()[:n])
    if not (ok_train and ok_test and ok_y and ok_ids):
        raise RuntimeError(f"base inputs differ from the leak-proof upload: train {ok_train}, test {ok_test}, "
                           f"labels {ok_y}, ids {ok_ids}")
    return {"training_rows": int(tr.sum()), "test_rows": n, "identical": True}


def build() -> tuple[pd.DataFrame, dict]:
    f = pd.read_parquet(C.FRAME)
    f = f[f["tabpfn_split"].isin(["train", "test"])].reset_index(drop=True)      # main tour, with odds, supported
    X = base_inputs(f)
    check = check_against_leakproof_upload(f, X)
    pieces = pd.read_parquet(C.PIECES)
    pieces = f[["match_id"]].merge(pieces, on="match_id", how="left", validate="one_to_one")
    new = A.new_inputs(pieces)
    out = pd.concat([f[KEEP].reset_index(drop=True), X.add_prefix("x_"), new.add_prefix("x_")], axis=1)
    out["season"] = out["year"].astype(int)
    # raw values the scorer's subsets read (not model inputs)
    out["season_n_a"], out["season_n_b"] = pieces["season_n_a"].to_numpy(), pieces["season_n_b"].to_numpy()
    out["debut_season"] = debut_season(out)
    meta = {"leakproof_upload_check": check,
            "coverage": {c: float(np.isfinite(out[f"x_{c}"].to_numpy()).mean())
                         for c in list(A.NEW_DIFF) + A.PAIR_COLS},
            "debut_season_matches": out.groupby(["season", "tour"])["debut_season"].sum().rename("matches")
                                       .reset_index().to_dict("records"),
            "rows_by_season_tour": out.groupby(["season", "tour"]).size().rename("matches").reset_index()
                                      .to_dict("records")}
    return out, meta


def matrix(frame: pd.DataFrame, arm: str) -> pd.DataFrame:
    return pd.DataFrame({n: frame[f"x_{n}"].to_numpy(dtype="float64") for n in A.ARMS[arm]})


def job_data(frame: pd.DataFrame, arm: str, season: int):
    """(X_train, y_train, X_query, query_ids) for one job: training 2013 .. season - 1, query the season (stored, then
    swapped)."""
    tr = frame["season"].between(C.TRAIN_FROM, season - 1).to_numpy()
    te = (frame["season"] == season).to_numpy()
    X = matrix(frame, arm)
    X_train = X[tr].reset_index(drop=True)
    y_train = frame.loc[tr, "a_won"].astype("int64").to_numpy()
    X_test = X[te].reset_index(drop=True)
    X_query = pd.concat([X_test, A.flip(X_test)], ignore_index=True)
    ids = pd.DataFrame({"match_id": np.r_[frame.loc[te, "match_id"].to_numpy(), frame.loc[te, "match_id"].to_numpy()],
                        "orientation": np.r_[np.zeros(te.sum(), int), np.ones(te.sum(), int)]})
    return X_train, y_train, X_query, ids


def job_id(stage: str, arm: str, season: int, seed: int) -> str:
    return f"{stage}__{arm}__{season}__seed{seed}"


def jobs(frame: pd.DataFrame) -> list[dict]:
    out = []
    for stage, spec in STAGES.items():
        for arm, seed in spec["runs"]:
            for season in spec["seasons"]:
                X_train, y_train, X_query, ids = job_data(frame, arm, season)
                out.append({"job": job_id(stage, arm, season, seed), "stage": stage, "arm": arm, "season": season,
                            "seed": seed, "train_rows": int(len(X_train)), "query_rows": int(len(X_query)),
                            "columns": list(X_train.columns),
                            "fingerprint": T.fingerprint(X_train, y_train, X_query)})
    return out


def main() -> int:
    C.OUT.mkdir(parents=True, exist_ok=True)
    frame, meta = build()
    for arm, names in A.ARMS.items():
        X = matrix(frame, arm)
        if not np.allclose(A.flip(A.flip(X)).to_numpy(), X.to_numpy(), equal_nan=True):
            raise RuntimeError(f"{arm}: the flip is not an involution")
        missing = [c for c in names if not np.isfinite(X[c].to_numpy()).any()]
        if missing:
            raise RuntimeError(f"{arm}: inputs without any value: {missing}")
    frame.to_parquet(C.OUT / "frame.parquet", index=False)
    js = jobs(frame)
    C.write_json(C.OUT / "jobs.json", js)
    meta.update({"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "arms": A.describe(),
                 "stages": STAGES, "jobs": len(js),
                 "sources": {k: {"path": str(p.relative_to(ROOT)), "sha256": C.sha256_file(p)}
                             for k, p in (("frame", C.FRAME), ("leakproof", C.LEAKPROOF), ("pieces", C.PIECES))}})
    C.write_json(C.OUT / "frame_manifest.json", meta)
    C.log(f"frame: {len(frame):,} matches; {len(js)} jobs; coverage of new inputs: "
          f"{ {k: round(v, 4) for k, v in meta['coverage'].items()} }")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Shared helpers for the study "rating systems against Elo" (src/eda/rating_systems/).

The study replaces the predictability diagnostic's surface Elo (Stage 1) with Glicko-2, Glicko-1 and TrueSkill, tuned the
way Stage 1 tuned Elo, and scores them on the same matches and with the same tests as the two earlier studies, so every
number is on their scale:

    history         every singles match of Stage 0 from 2010, every level (ITF and team events included), per tour, in
                    the table's order; walkovers and "other" never move ratings, retirements do (the owner's rule)
    tuning          the evaluation matches of 2013-2018 only (2010-2012 warm up), then frozen
    the harness     src/eda/ufc_ideas/common.py (the Stage 4 pool and its walk-forward rundown, any base column)
    the ladder      src/eda/feature_alpha_audit/elo_retest.py (annual expanding fits, intervals clustered by calendar week)

Use: m = load_table(); h = history(m[m["tour"].eq("atp")].reset_index(drop=True)); res = ratings.run(h, "glicko2", cfg)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "rating_systems"
DOCS = ROOT / "docs" / "studies" / "rating_systems"
UPDATES = ("completed", "retired")               # statuses whose result moves ratings (Stage 1's "ret" rule)
TUNE_YEARS = range(2013, 2019)
SYSTEMS = ("glicko2", "glicko1", "trueskill")
SYSTEM_NAMES = {"elo": "Surface Elo (Stage 1)", "glicko2": "Glicko-2", "glicko1": "Glicko-1 (fixed volatility)",
                "trueskill": "TrueSkill"}
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def load_table(last_year: int | None = None) -> pd.DataFrame:
    """Stage 0's matches in the table's order, with what the passes and the scoring read."""
    m = C.load_matches(["match_id", "tour", "year", "level", "qualifying", "evaluation", "status", "surface",
                        "tournament_id", "tournament_date", "round", "round_order", "player_a_id", "player_b_id",
                        "a_won"])
    if last_year is not None:
        m = m[m["year"].le(last_year)].reset_index(drop=True)
    return m


def history(t: pd.DataFrame) -> dict:
    """The inputs of a pass for one tour's matches, already in the table's order: stage1_baselines.history_arrays
    (week = tournament date in days, event, round order, player codes, result, surface code) plus which rows move
    ratings (upd), the masks of the two components (every row; rows with a known surface) and, for scoring, the
    evaluation flag and season as arrays."""
    h = B.history_arrays(t)
    h["upd"] = t["status"].isin(UPDATES).tolist()
    if "round" in t:
        # events played over about two weeks under one start date: those with a round of 128 (the Grand Slams and the
        # 96-draw 1000s), for TrueSkill Through Time's hold (ratings.ttt_pass)
        key = t["tournament_date"].astype(str) + "|" + t["tournament_id"].astype(str)
        h["fortnight"] = t["round"].eq("R128").groupby(key).transform("any").tolist()
    h["all"] = [True] * len(t)
    h["surf_known"] = [s >= 0 for s in h["surf"]]
    h["eval"] = t["evaluation"].to_numpy(dtype=bool)
    h["year"] = t["year"].to_numpy()
    h["y"] = t["a_won"].to_numpy(dtype=bool)
    return h


def tune_mask(h: dict) -> np.ndarray:
    return h["eval"] & np.isin(h["year"], list(TUNE_YEARS))


def log_loss(p, y) -> float:
    return B.log_loss(p, y)


# The earlier studies' and the audit's code this study imports. It is being revised by other work (the shared harness
# changed on 2 Oct 2026 at 16:48), so every summary records the hash of what it ran with.
SHARED_CODE = ["src/eda/predictability_diagnostic/common.py", "src/eda/predictability_diagnostic/stage1_baselines.py",
               "src/eda/predictability_diagnostic/stage4_rundown.py", "src/eda/ufc_ideas/common.py",
               "src/eda/ufc_ideas/stageA_rundown.py", "src/eda/feature_alpha_audit/elo_retest.py",
               "src/eda/feature_alpha_audit/profile_retest.py"]
INPUT_TABLES = ["data/studies/predictability_diagnostic/stage0_matches.parquet",
                "data/studies/predictability_diagnostic/stage0_match_players.parquet",
                "data/studies/predictability_diagnostic/stage1_baselines.parquet",
                "data/studies/predictability_diagnostic/stage1_odds.parquet",
                "data/studies/predictability_diagnostic/stage4_features.parquet",
                "data/studies/ufc_ideas/stageB_adj_features.parquet", "data/studies/ufc_ideas/stageB_ios_features.parquet",
                "data/studies/ufc_ideas/stageD_profile_features.parquet"]


def dependency_hashes() -> dict:
    """SHA-256 of the shared code, and size and modification time of the input tables, as this run found them."""
    import hashlib
    code = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SHARED_CODE if (ROOT / p).exists()}
    tables = {}
    for p in INPUT_TABLES:
        f = ROOT / p
        if f.exists():
            st = f.stat()
            tables[p] = {"bytes": st.st_size,
                         "modified": pd.Timestamp(st.st_mtime, unit="s", tz="UTC").isoformat(timespec="seconds")}
    return {"code_sha256": code, "input_tables": tables}


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """zstd with byte-stream-split for the float columns (as the UFC-ideas study writes its rating tables)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    fl = [c for c in df.columns if df[c].dtype.kind == "f"]
    strs = [c for c in df.columns if df[c].dtype.kind not in "fiub"]
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), path, compression="zstd", compression_level=12,
                   use_dictionary=strs, use_byte_stream_split=fl)

"""The history-composition feature, for the feature universe's store (the owner's request of 8 Oct 2026: add it to the
universe a future feature-selection phase draws from).

For every match of the store's population (the frozen model frame's 63,737 matches, 2013-2026), each player's share of
their played matches in the previous 365 days that were below the main tour: tour and Slam qualifying, Challenger and
WTA 125 main draws and qualifying, ITF main draws and qualifying. Team events count in the total only. It is
blend.history on the model frame's snapshot (the 30 Sep 2026 Stage 0, common.SOURCES): the player's own earlier matches
in Stage 0's order with a tournament date within 365 days, so it is safe by construction under the match clock. No
result of the match itself is read, and nothing here relates the feature to an outcome. Missing when the player has no
played match in the window.

Writes data/studies/event_levels/universe_columns.parquet, in the store's row order: match_id, player_a_id,
player_b_id, low_share_a, low_share_b, low_share_diff (A - B; the input experiment C1 tested); and
universe_columns.json (sources, checks).
Checks: every store match is found once with both sides; the values of 2013-2024 equal the study's history.parquet.
Run: ./python.sh src/eda/event_levels/universe_columns.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.event_levels import blend as BL  # noqa: E402
from src.eda.event_levels import common as C  # noqa: E402

STORE = C.STUDIES / "feature_universe" / "store.parquet"
OUT_FILE = C.OUT / "universe_columns.parquet"


def main() -> int:
    sources = C.check_sources()
    keys = pd.read_parquet(STORE, columns=["match_id", "season"])
    keys["match_id"] = keys["match_id"].astype(str)
    if keys["match_id"].duplicated().any():
        raise RuntimeError("the store's match ids are not unique")
    m, p = BL.load()
    h = BL.history(m, p, years=(C.TRAIN_FROM, 2026), levels=C.MAIN, match_ids=keys["match_id"])
    a = h[h["side"] == "A"].set_index("match_id")
    b = h[h["side"] == "B"].set_index("match_id")
    found = keys["match_id"].isin(a.index) & keys["match_id"].isin(b.index)
    if not found.all() or a.index.duplicated().any() or b.index.duplicated().any():
        raise RuntimeError(f"{int((~found).sum())} store matches lack a side in the snapshot")
    ids = pd.Index(keys["match_id"])
    sides = m.set_index("match_id").reindex(ids)[["player_a_id", "player_b_id"]]
    out = pd.DataFrame({"match_id": ids, "player_a_id": sides["player_a_id"].to_numpy(),
                        "player_b_id": sides["player_b_id"].to_numpy(),
                        "low_share_a": a["low_share"].reindex(ids).to_numpy(float),
                        "low_share_b": b["low_share"].reindex(ids).to_numpy(float)})
    out["low_share_diff"] = out["low_share_a"] - out["low_share_b"]
    checks = {"store_rows": int(len(keys)), "found_both_sides": int(found.sum()),
              "player_a_is_the_side_a_row": bool((a["player_id"].reindex(ids).to_numpy() ==
                                                   out["player_a_id"].to_numpy()).all()),
              "share_in_0_1": bool(np.nanmin(out[["low_share_a", "low_share_b"]].to_numpy()) >= 0
                                   and np.nanmax(out[["low_share_a", "low_share_b"]].to_numpy()) <= 1)}
    # the study's own table (2013-2024, the experiments' input) must agree on every common row
    hp = pd.read_parquet(C.OUT / "history.parquet", columns=["match_id", "side", "low_share"])
    ha = hp[hp["side"] == "A"].set_index("match_id")["low_share"]
    hb = hp[hp["side"] == "B"].set_index("match_id")["low_share"]
    common = ids.intersection(ha.index)
    o = out.set_index("match_id")
    checks["rows_in_history_parquet"] = int(len(common))
    checks["equal_history_parquet"] = bool(
        np.array_equal(o.loc[common, "low_share_a"].to_numpy(float), ha.loc[common].to_numpy(float), equal_nan=True)
        and np.array_equal(o.loc[common, "low_share_b"].to_numpy(float), hb.loc[common].to_numpy(float),
                           equal_nan=True))
    season = keys["season"].to_numpy()
    checks["coverage_both_sides"] = {
        f"{lo}-{hi}": float(np.isfinite(out["low_share_diff"].to_numpy())[(season >= lo) & (season <= hi)].mean())
        for lo, hi in ((2013, 2021), (2022, 2024), (2025, 2026))}
    bad = [k for k in ("player_a_is_the_side_a_row", "share_in_0_1", "equal_history_parquet") if not checks[k]]
    if bad or checks["found_both_sides"] != checks["store_rows"]:
        raise RuntimeError(f"checks failed: {bad} {checks}")
    out.to_parquet(OUT_FILE, index=False)
    C.write_json(C.OUT / "universe_columns.json", {
        "what": "each player's share of the previous 365 days' played matches below the main tour, for the feature "
                "universe's store (63,737 matches, 2013-2026); no result read",
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "sources": sources, "store_sha256": C.sha256_file(STORE), "checks": checks,
        "file_sha256": C.sha256_file(OUT_FILE)})
    C.log(f"universe_columns.parquet: {len(out):,} rows; {checks}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

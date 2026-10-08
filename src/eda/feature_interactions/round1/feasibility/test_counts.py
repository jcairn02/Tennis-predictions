"""Row counts only, for the closed 2025-2026 seasons and the point-sequence table (round-1 feasibility, gate G2).

Counts the model frame's 2025-2026 matches by tour, and how many of them have the data a partial-coverage candidate
needs: a Pinnacle close, both players' heights, both players' serve-speed history (shot-level flags), a shot-level
point record. No result, price value or feature value is read: only presence. Also summarises the point-sequence
table's own coverage file for 2014-2021 and 2022-2024 and records whether that table changed since 18:24.
Writes data/studies/feature_interactions/round1/test_counts.json.
Run: ./python.sh src/eda/feature_interactions/round1/feasibility/test_counts.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.eda.feature_interactions.round1.feasibility import base as B  # noqa: E402

S = B.ROOT / "data" / "studies"
OLD = S / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"


def main() -> int:
    mf = pd.read_parquet(B.C.MODEL_FRAME, columns=["match_id", "season", "tour"])
    t = mf[mf["season"] >= 2025].reset_index(drop=True)
    res = {"model_rows_2025_2026": t.groupby("tour").size().to_dict()}
    ids = set(t["match_id"])

    def count(mask_ids: set) -> dict:
        return t[t["match_id"].isin(mask_ids)].groupby("tour").size().reindex(["atp", "wta"]).fillna(0).astype(int).to_dict()
    o = pd.read_parquet(OLD / "predictability_diagnostic" / "stage1_odds.parquet", columns=["match_id", "ps_a", "ps_b"])
    res["pinnacle_present"] = count(set(o.loc[o["match_id"].isin(ids) & o["ps_a"].notna() & o["ps_b"].notna(), "match_id"]))
    p = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_match_players.parquet", columns=["match_id", "height"])
    p = p[p["match_id"].isin(ids)]
    both_h = p.groupby("match_id")["height"].apply(lambda s: bool(s.notna().all() and len(s) == 2))
    res["height_both_present"] = count(set(both_h[both_h].index))
    sides = pq.read_table(S / "shot_level" / "stage3_sides.parquet",
                          columns=["match_id", "A|spd1_change|off|dec2-w52|has", "B|spd1_change|off|dec2-w52|has"]).to_pandas()
    sides = sides[sides["match_id"].isin(ids)]
    ok = (sides["A|spd1_change|off|dec2-w52|has"] > 0.5) & (sides["B|spd1_change|off|dec2-w52|has"] > 0.5)
    res["speed_history_both"] = count(set(sides.loc[ok, "match_id"]))
    sm = pd.read_parquet(S / "shot_level" / "stage0_source_matches.parquet", columns=["match_id", "n_points"])
    res["shot_level_points_present"] = count(set(sm.loc[sm["match_id"].isin(ids) & (sm["n_points"] > 0), "match_id"]))
    # the point-sequence table (another session's study): its own coverage file, and whether it is stable
    ps_dir = S / "point_sequence"
    cov = pd.read_csv(ps_dir / "coverage_model.csv")
    cov = cov[cov["year"] != "all"].astype({"year": int})
    summ = {}
    for tag, (lo, hi) in (("2014_2021", (2014, 2021)), ("2022_2024", (2022, 2024)), ("2025_2026", (2025, 2026))):
        c = cov[cov["year"].between(lo, hi)]
        for tour, g in c.groupby("tour"):
            w = g["matches"].to_numpy(float)
            summ[f"{tour}_{tag}"] = {k: round(float((g[k] * w).sum() / w.sum()), 4)
                                     for k in ("own_sequence", "own_complete", "both_ge5", "both_ge20")}
    res["point_sequence_coverage"] = summ
    res["point_sequence_files"] = {f.name: datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="minutes")
                                   for f in sorted(ps_dir.glob("*.parquet")) + [ps_dir / "coverage_model.csv"]
                                   if f.name in ("sequences.parquet", "seq_matches.parquet", "coverage_model.csv")}
    res["checked_at"] = datetime.now().isoformat(timespec="minutes")
    (B.OUT / "test_counts.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

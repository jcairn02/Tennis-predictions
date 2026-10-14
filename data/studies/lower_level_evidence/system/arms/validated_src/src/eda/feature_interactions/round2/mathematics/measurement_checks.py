"""Round 2, mathematics (measurement-reliability lens): result-free checks of box-score quality, 2013-2024.

1. Count identities per player-match box score (7 inequalities) and a plausibility band for the first-serve share.
2. Event-level recording-fault detector for first serves in: each event's mean residual of the first-serve share against
   the players' own 2013-2024 means, with its z; flagged at > +3 pp and z > 4 (events with >= 40 player-matches).
Reads Stage 0 (pre-rebuild copies): box-score counts, tour, year, level, qualifying, tournament name, source. Never the
result, the score or the status. Run: ./python.sh src/eda/feature_interactions/round2/mathematics/measurement_checks.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OLD = ROOT / "data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/data/studies/predictability_diagnostic"
OUT = ROOT / "data/studies/feature_interactions/round2/mathematics"


def main() -> int:
    m = pd.read_parquet(OLD / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "level", "qualifying", "tournament_name", "source"])
    m = m[(m.year >= 2013) & (m.year <= 2024)]
    p = pd.read_parquet(OLD / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "ace", "df", "svpt", "first_in", "first_won", "second_won",
                                 "sv_gms", "bp_saved", "bp_faced", "has_box"])
    x = p.merge(m, on="match_id", how="inner")
    x = x[x.has_box.fillna(False)]
    second = x.svpt - x.first_in
    v = pd.DataFrame({"first_in>svpt": x.first_in > x.svpt, "first_won>first_in": x.first_won > x.first_in,
                      "second_won>second": x.second_won > second, "df>second": x.df > second,
                      "ace>points_won": x.ace > x.first_won + x.second_won, "bp_saved>bp_faced": x.bp_saved > x.bp_faced,
                      "breaks>sv_gms": (x.bp_faced - x.bp_saved) > x.sv_gms,
                      "first_share_outside_0.4_0.8": ((x.first_in / x.svpt) < 0.4) | ((x.first_in / x.svpt) > 0.8)})
    out = {"player_match_box_scores": int(len(x)), "violation_rate_pct": {k: float(100 * v[k].mean()) for k in v}}
    y = x[x.svpt >= 30].copy()
    y["fi"] = y.first_in / y.svpt
    y["res"] = y.fi - y.groupby(["tour", "player_id"]).fi.transform("mean")
    e = y.groupby(["tour", "year", "tournament_name", "qualifying"]).res.agg(["size", "mean", "std"]).reset_index()
    e = e[e["size"] >= 40]
    e["z"] = e["mean"] / (e["std"] / np.sqrt(e["size"]))
    flag = (e["mean"] > 0.03) & (e.z > 4)
    out["events"] = int(len(e))
    out["flagged_share_pct"] = float(100 * flag.mean())
    out["flagged_top"] = e[flag].sort_values("mean", ascending=False).head(15).to_dict(orient="records")
    bra = e[e.tournament_name.str.contains("Bratislava", na=False)].sort_values("year")
    out["bratislava"] = bra.to_dict(orient="records")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "measurement_checks.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("player_match_box_scores", "violation_rate_pct", "events", "flagged_share_pct")},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Outcome-free: how many of the model's main-tour matches the feed's first snapshot touches. A match is touched when a
player of it has a match added by the snapshot (or a box score it completed) in the 365 days before the match's
tournament date. Reads the current instance's frame (no result column) and the snapshot.
Writes data/studies/data_gaps_2026/coverage/exposure_<snapshot>.json.
Run: ./python.sh src/eda/data_gaps_2026/exposure.py --snapshot <feed>/<snapshot>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import additions as AD  # noqa: E402

FRAME = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10" / "model_frame.parquet"
OUT = ROOT / "data" / "studies" / "data_gaps_2026" / "coverage"


def run(target: str) -> dict:
    snap = AD.ACCEPTED / target
    am = pd.read_parquet(snap / "matches.parquet", columns=["match_id", "tour", "tournament_date", "map_level"])
    amp = pd.read_parquet(snap / "match_players.parquet", columns=["match_id", "player_id"])
    comp = pd.read_parquet(snap / "completions.parquet", columns=["match_id", "player_id"])
    added = amp.merge(am, on="match_id")
    added["d"] = pd.to_datetime(added["tournament_date"])
    from src.eda.lower_level_evidence import common as LC
    f = pd.read_parquet(FRAME, columns=["match_id", "tour", "season", "tournament_date"])     # no result column read
    ids = pd.read_parquet(LC.STAGE0_DIR / "stage0_matches.parquet", columns=["match_id", "player_a_id", "player_b_id"])
    f = f[f["season"].between(2025, 2026)].merge(ids, on="match_id", how="left")
    f["d"] = pd.to_datetime(f["tournament_date"])
    by_player = added.groupby("player_id")["d"].apply(lambda s: np.sort(s.to_numpy()))

    def touched(pid, d) -> bool:
        a = by_player.get(pid)
        if a is None:
            return False
        lo = np.searchsorted(a, d - np.timedelta64(365, "D"))
        hi = np.searchsorted(a, d)
        return hi > lo

    f["touched"] = [touched(a, d) or touched(b, d) for a, b, d in zip(f["player_a_id"], f["player_b_id"],
                                                                       f["d"].to_numpy())]
    f["month"] = f["d"].dt.to_period("M").astype(str)
    out = {"snapshot": target, "frame": str(FRAME.relative_to(ROOT)), "added_matches": int(len(am)),
           "completions": int(comp["match_id"].nunique()),
           "touched_share_by_tour_season": {f"{t}|{s}": round(float(g["touched"].mean()), 3)
                                            for (t, s), g in f.groupby(["tour", "season"])},
           "touched_share_by_tour_month_2026": {f"{t}|{m}": round(float(g["touched"].mean()), 3)
                                                for (t, m), g in f[f["season"] == 2026].groupby(["tour", "month"])}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"exposure_{target.replace('/', '_')}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", required=True)
    a = ap.parse_args()
    print(json.dumps(run(a.snapshot), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

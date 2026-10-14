"""The gate: a live match's inputs may be used only when they read what the frame's matches read
(docs/decisions/2026-10-08-prediction-run-box-scores.md, point 3).

40 of the model's 57 inputs are built from box scores (41 of 58 until ios_points_short was dropped on 9 Oct 2026), and
all of them read the same event's earlier rounds; a missing box
score is skipped silently, and the two-week averages shrink toward 0. In the frame's seasons of 2019-2025, 98.4-99.7%
of the same event's earlier-round player-matches had one. So for each live match and each of its players, every
completed match before it, at the same event or within WINDOW_DAYS of its day, must have a box score in the Stage 0 the
inputs were built on. Retired matches and walkovers are not required: no box-score input reads them. A player who
entered through the qualifying (Q, or LL) with no qualifying match in that span of Stage 0 fails too: Tennis My Life
has lacked the WTA's qualifying since June 2026, which the frame's earlier seasons held.

A live match that fails is recorded with what is missing and marked not to bet. The days are the timeline's: a match
counts as within the window when its latest possible finish falls within it.

Run: ./python.sh src/eda/prediction_run/gate.py --run <folder> [--stage0 <folder>] [--timing <timing.parquet>]
     (default: the sandbox's tables, which hold the live rows)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.prediction_run import common as P  # noqa: E402

REQUIRED = ("completed",)
QUALIFIED = ("Q", "LL")                            # entries that played the qualifying (a lucky loser lost its last round)
MISSING_COLUMNS = ["live_match_id", "player_id", "player_name", "match_id", "tournament_name", "round", "same_event"]


def check(stage0: Path, timing: Path, meta: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per live match: complete or not, and the earlier matches that lack a box score (one row per player-match)."""
    m = pd.read_parquet(stage0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "tournament_id", "tournament_name", "round", "round_order",
                                 "status", "has_box", "qualifying", "tournament_date"])
    p = pd.read_parquet(stage0 / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "player_name", "entry"])
    for t in (m, p):
        t["match_id"] = t["match_id"].astype(str)
    t = pd.read_parquet(timing, columns=["match_id", "lf"]).astype({"match_id": str}).set_index("match_id")["lf"]
    m["lf"] = m["match_id"].map(t)
    hist = p.merge(m, on="match_id")
    live_ids = set(meta["match_id"])
    rows, missing = [], []
    for _, lm in meta.iterrows():
        me = m[m["match_id"].eq(lm["match_id"])]
        if me.empty:
            rows.append({"match_id": lm["match_id"], "complete": False, "reason": "not in Stage 0"})
            continue
        me = me.iloc[0]
        day = P.day_of(lm["day"])
        players = p[p["match_id"].eq(lm["match_id"])]
        checked = lacking = 0
        reasons = []
        for _, pl in players.iterrows():
            h = hist[hist["player_id"].eq(pl["player_id"]) & ~hist["match_id"].isin(live_ids)]
            same_event = h["tournament_id"].eq(me["tournament_id"]) & (h["round_order"] < me["round_order"])
            recent = h["lf"].notna() & (h["lf"] >= day - P.WINDOW_DAYS) & (h["lf"] < day)
            before = h[(same_event | recent) & h["status"].isin(REQUIRED)]
            checked += len(before)
            gap = before[~before["has_box"].astype(bool)]
            lacking += len(gap)
            for _, g in gap.iterrows():
                missing.append({"live_match_id": lm["match_id"], "player_id": pl["player_id"],
                                "player_name": pl["player_name"], "match_id": g["match_id"],
                                "tournament_name": g["tournament_name"], "round": g["round"],
                                "same_event": bool(g["tournament_id"] == me["tournament_id"])})
            # TML files some events' qualifying under an id of its own (Shanghai 2026: -20261005, the main draw
            # -20261007), so the qualifying matches are looked for in the window, not by the event's id
            if str(pl.get("entry") or "").upper() in QUALIFIED and not h.loc[same_event | recent, "qualifying"].any():
                reasons.append(f"{pl['player_name']}: entered through qualifying, but no qualifying match in Stage 0")
        if lacking:
            reasons.insert(0, f"{lacking} earlier match(es) without a box score")
        rows.append({"match_id": lm["match_id"], "tournament_name": me["tournament_name"], "round": me["round"],
                     "players": " v ".join(players["player_name"].astype(str)), "earlier_matches_checked": checked,
                     "without_box": lacking, "complete": not reasons, "reason": "; ".join(reasons)})
    return pd.DataFrame(rows), pd.DataFrame(missing, columns=MISSING_COLUMNS)


def run(folder: Path, stage0: Path, timing: Path) -> dict:
    meta = pd.read_parquet(folder / "live_meta.parquet").astype({"match_id": str})
    table, missing = check(stage0, timing, meta)
    table["bet"] = np.where(table["complete"], "may be bet", "do not bet: inputs incomplete")
    table.to_csv(folder / "gate.csv", index=False)
    missing.to_csv(folder / "gate_missing.csv", index=False)
    out = {"checked_at": P.stamp(), "stage0": str(stage0), "live_matches": int(len(table)),
           "complete": int(table["complete"].sum()), "incomplete": table.loc[~table["complete"], ["match_id", "reason"]]
           .to_dict("records")}
    P.write_json(folder / "gate.json", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="the run's folder (live_meta.parquet)")
    ap.add_argument("--stage0", default=str(P.SANDBOX / P.PD))
    ap.add_argument("--timing", default=str(P.SANDBOX / P.MT / "timing.parquet"))
    a = ap.parse_args()
    folder = Path(a.run) if Path(a.run).is_absolute() else ROOT / a.run
    res = run(folder, Path(a.stage0), Path(a.timing))
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

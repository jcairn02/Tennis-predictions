"""The prediction run's gate (src/eda/prediction_run/gate.py) applied to every past main-tour singles match, as if each
were predicted live, on today's tables (docs/studies/box_score_gate_review/).

For each target match and each player, the gate's rule: every completed match of the player at the same event in an
earlier round, or with a latest possible finish in the WINDOW_DAYS before the match's day, must have a box score; a
player whose entry is Q or LL needs a qualifying match among them. The tables are the data check's Stage 0 (today's
downloads, the repaired builder) with the accepted packages and the lower-level feed merged in, as a prediction run's
tables step merges them (src/pipeline/readiness.tables); the window from the shared timeline (the packages' own rows for
their matches). A target's day is the timeline's best start (`start`), else its anchor.

This counts only the gaps that are still there today (permanent ones, or ones our checks made). A bet-day run also meets
the gaps of publication delay (Tennis My Life's box score not out yet), which this cannot see: a lower bound on how often
the gate fires.

Run: ./python.sh src/eda/box_score_gate_review/simulate_gate.py [--first 2024] [--last-day 2026-10-07]
Writes data/studies/box_score_gate_review/gate_simulation_{targets,gaps}.parquet and gate_simulation.json.
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
from src.eda.prediction_run import gate as G  # noqa: E402
from src.pipeline import readiness as RD  # noqa: E402

OUT = ROOT / "data" / "studies" / "box_score_gate_review"
TARGET_LEVELS = ("GS", "FIN", "T1000", "T500", "T250")      # what a bet day predicts (no team events, no qualifying)
EPOCH = pd.Timestamp("1970-01-01")


def level_group(level: pd.Series, qualifying: pd.Series) -> pd.Series:
    """The kind of a match. ITF and team events come before qualifying (corrected 14 Oct 2026: the first version put
    every qualifying match first, so the women's ITF qualifying, with no box score in training, was pooled with the
    tour-level and Challenger qualifying, which training nearly always holds)."""
    lv = level.astype(str)
    out = np.select([lv.eq("ITF"), lv.eq("TEAM"), qualifying.astype(bool), lv.isin(TARGET_LEVELS), lv.eq("CH")],
                    ["ITF", "team event", "qualifying", "main tour", "Challenger / WTA 125"], "other")
    return pd.Series(out, index=level.index)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--first", type=int, default=2024)
    ap.add_argument("--last-day", default="2026-10-07")
    ap.add_argument("--stage0", default=str(RD.CACHE))
    ap.add_argument("--tag", default="", help="a suffix for the output files (e.g. _2013)")
    a = ap.parse_args()
    m, p, lf, merged = RD.tables(Path(a.stage0), ROOT / "data" / "studies" / "match_timing" / "timing.parquet")
    cols = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id",
            "tournament_name", "tournament_date", "status", "has_box", "box_status", "source"]
    h = p[["match_id", "player_id", "player_name", "entry"]].merge(m[cols], on="match_id")
    h["lf"] = h["match_id"].map(lf).astype(float)
    t = pd.read_parquet(ROOT / "data" / "studies" / "match_timing" / "timing.parquet",
                        columns=["match_id", "start", "anchor", "exact"]).astype({"match_id": str}).set_index("match_id")
    h["start"] = h["match_id"].map(t["start"]).fillna(h["match_id"].map(t["anchor"])).astype(float)
    h["group"] = level_group(h["level"], h["qualifying"])
    del m, p
    last = (pd.Timestamp(a.last_day) - EPOCH).days
    tg = h[h["level"].isin(TARGET_LEVELS) & ~h["qualifying"].astype(bool) & h["status"].eq("completed")
           & (h["year"] >= a.first) & h["start"].notna() & (h["start"] <= last)].copy()
    hist = h[h["status"].isin(G.REQUIRED)][["player_id", "match_id", "tournament_id", "tournament_name", "round",
                                            "round_order", "lf", "has_box", "box_status", "source", "group",
                                            "qualifying", "tournament_date", "tour", "year"]]
    pairs = tg[["player_id", "match_id", "tournament_id", "round_order", "start", "entry"]].merge(
        hist, on="player_id", suffixes=("", "_h"))
    pairs = pairs[pairs["match_id_h"].ne(pairs["match_id"])]
    same = pairs["tournament_id_h"].eq(pairs["tournament_id"]) & (pairs["round_order_h"] < pairs["round_order"])
    recent = pairs["lf"].notna() & (pairs["lf"] >= pairs["start"] - P.WINDOW_DAYS) & (pairs["lf"] < pairs["start"])
    pairs = pairs[same | recent].assign(same_event=same[same | recent])
    gaps = pairs[~pairs["has_box"].astype(bool)]
    key = ["match_id", "player_id"]
    per = tg.set_index(key)[["tour", "year", "tournament_name", "round", "entry", "start"]]
    per["checked"] = pairs.groupby(key).size().reindex(per.index).fillna(0).astype(int)
    per["gaps"] = gaps.groupby(key).size().reindex(per.index).fillna(0).astype(int)
    per["gap_same_event"] = gaps[gaps["same_event"]].groupby(key).size().reindex(per.index).fillna(0).astype(int)
    qual = pairs.groupby(key)["qualifying"].any().reindex(per.index).fillna(False)
    per["qualifier_without_q"] = per["entry"].astype(str).str.upper().isin(G.QUALIFIED) & ~qual.astype(bool)
    per["fails"] = (per["gaps"] > 0) | per["qualifier_without_q"]
    per = per.reset_index()
    match = per.groupby("match_id").agg(tour=("tour", "first"), year=("year", "first"), fails=("fails", "any"),
                                        same=("gap_same_event", "sum"), gaps=("gaps", "sum"),
                                        qual=("qualifier_without_q", "any"), start=("start", "first"))
    gaps = gaps.assign(target_tour=gaps["match_id"].map(match["tour"]), target_year=gaps["match_id"].map(match["year"]))
    OUT.mkdir(parents=True, exist_ok=True)
    per.to_parquet(OUT / f"gate_simulation_targets{a.tag}.parquet", index=False)
    gaps.to_parquet(OUT / f"gate_simulation_gaps{a.tag}.parquet", index=False)
    by = match.groupby(["tour", "year"]).agg(matches=("fails", "size"), blocked=("fails", "sum"),
                                             same_event_gap=("same", lambda s: int((s > 0).sum())),
                                             qualifier_rule=("qual", "sum"))
    by["blocked_pct"] = (100 * by["blocked"] / by["matches"]).round(1)
    cause = gaps.groupby(["target_tour", "group"])["match_id"].nunique().rename("blocked_matches").reset_index()
    events = (gaps.groupby(["target_tour", "tournament_name", "year", "group", "box_status"])["match_id"]
              .nunique().rename("blocked_matches").reset_index().sort_values("blocked_matches", ascending=False))
    out = {"tables": {"stage0": a.stage0, "packages_merged": merged}, "first_season": a.first, "last_day": a.last_day,
           "window_days": P.WINDOW_DAYS, "targets": int(len(match)), "blocked": int(match["fails"].sum()),
           "by_tour_year": by.reset_index().to_dict("records"),
           "gap_cause_by_level_of_missing_match": cause.to_dict("records"),
           "top_missing_events": events.head(25).to_dict("records")}
    (OUT / f"gate_simulation{a.tag}.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    pd.set_option("display.width", 220)
    print(by.to_string())
    print(cause.to_string(index=False))
    print(events.head(25).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

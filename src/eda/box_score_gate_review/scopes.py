"""How often narrower versions of the gate would withhold a bet: the gate simulation's gaps (simulate_gate.py, the
tables named by --tag) re-counted under each scope (docs/studies/box_score_gate_review/).

Scopes (a missing box score blocks only when its match is of these kinds; the qualifier rule kept or not):
    current             every kind (the gate of 8 Oct)
    near_complete       the kinds whose box scores training rows nearly always hold (coverage.py, 2016-2025):
                        main tour, Challenger / WTA 125 and the tour-level and Challenger qualifying, both tours
                        (corrected 14 Oct 2026: first read as the men's qualifying only, from a grouping that pooled
                        the women's ITF qualifying with the rest)
    main_tour           main-tour matches only
    same_event_main     the same event's earlier main-draw rounds only
Run: ./python.sh src/eda/box_score_gate_review/scopes.py [--tag _now] [--first 2024]
Writes data/studies/box_score_gate_review/scopes{tag}.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "studies" / "box_score_gate_review"


def in_scope(g: pd.DataFrame, scope: str) -> pd.Series:
    kind, tour = g["group"].astype(str), g["tour"].astype(str)
    if scope == "current":
        return pd.Series(True, index=g.index)
    if scope == "near_complete":
        return kind.isin(["main tour", "Challenger / WTA 125", "qualifying"])
    if scope == "main_tour":
        return kind.eq("main tour")
    if scope == "same_event_main":
        return kind.eq("main tour") & g["same_event"].astype(bool)
    raise ValueError(scope)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default="_now")
    ap.add_argument("--first", type=int, default=2024)
    a = ap.parse_args()
    per = pd.read_parquet(OUT / f"gate_simulation_targets{a.tag}.parquet")
    gaps = pd.read_parquet(OUT / f"gate_simulation_gaps{a.tag}.parquet")
    per = per[per["year"] >= a.first]
    gaps = gaps[gaps["target_year"] >= a.first]
    match = per.groupby("match_id").agg(tour=("tour", "first"), year=("year", "first"),
                                        qual=("qualifier_without_q", "any"))
    rows = []
    for scope in ("current", "near_complete", "main_tour", "same_event_main"):
        hit = set(gaps.loc[in_scope(gaps, scope), "match_id"])
        for with_q in (True, False):
            fails = match.index.isin(hit) | (match["qual"].to_numpy() if with_q else False)
            d = match.assign(fails=fails)
            for (t, y), g in list(d.groupby(["tour", "year"])) + [((t, "all"), g) for t, g in d.groupby("tour")]:
                rows.append({"scope": scope, "qualifier_rule": with_q, "tour": t, "year": y, "matches": len(g),
                             "blocked": int(g["fails"].sum()), "pct": round(100 * g["fails"].mean(), 1)})
    r = pd.DataFrame(rows)
    r.to_csv(OUT / f"scopes{a.tag}.csv", index=False)
    w = r.pivot_table(index=["scope", "qualifier_rule"], columns=["tour", "year"], values="pct")
    pd.set_option("display.width", 250)
    print(w.to_string())
    # what the near-complete scope still blocks on, by kind of the missing match
    g = gaps[in_scope(gaps, "near_complete")]
    print(g.groupby(["target_tour", "group", "tour"])["match_id"].nunique().rename("blocked_matches").to_string())
    print(g.groupby(["target_tour", "tournament_name", "year", "group"])["match_id"].nunique()
          .sort_values(ascending=False).head(15).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())

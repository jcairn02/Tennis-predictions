"""Ideas agent, P9 point-details study: descriptive coverage of rally length (no results read).

Reads only P9's staged tables (data/dump/points/infosys_atp_recent/). Never loads a winner
column (match_winner, winner_from_points, scorer): every number here is a count of how often
something occurs, which brief 02 allows.

What it reports (printed only: brief 02 lets this agent write nothing but its memo, its CSV and
ideas_*.py scripts, so the numbers live in the printout and are copied into team/ideas.md):
  1. per event: the share of matches with a known rally length on >= half their points
     ("covered"), by level, and how bimodal that is (all-or-nothing events vs partial ones);
  2. inside partial events: coverage by court (do show courts carry the rally data?);
  3. the rally-length mix of known points, from the rally files' `category` (the shot the
     point ended on), by level;
  4. per covered match: points with a known rally length, and the spread of the match mean
     of the old rally count (tm1Rally + tm2Rally), for shrinkage scales;
  5. for each player's match at an event after his first, whether his previous round there
     is covered too (the coverage of a "load from the previous round" state), by level;
  6. the net flags: matches per player at the 24 flagged events.

Usage (from the repository root, Git Bash):  ./python.sh src/eda/p9_point_details/ideas_coverage.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
P9 = ROOT / "data" / "dump" / "points" / "infosys_atp_recent"

LEVEL_GROUP = {
    "1000": "1000s", "atpFinal": "Finals", "nextGen": "NextGen",
    "atp500": "500s", "atp250": "250s",
    "ch100": "Challengers", "ch50": "Challengers",
}


def load_matches() -> pd.DataFrame:
    cols = ["year", "event_id", "match_id", "draw", "round_from_code", "level",
            "court_id", "court_name", "p1_id", "p2_id", "points", "rally_entries"]
    m = pd.read_parquet(P9 / "matches.parquet", columns=cols)
    m["key"] = m["year"].astype(str) + "/" + m["event_id"].astype(str) + "/" + m["match_id"].astype(str)
    m["level_group"] = m["level"].map(LEVEL_GROUP).fillna(m["level"].astype(str))
    return m


def load_points() -> pd.DataFrame:
    """One row per point. `known` is the source's flag; `real` is the flag AND a newer shot count
    (tm1Shot + tm2Shot) of 1 to 60. The flag alone is junk outside tracked matches: at Challengers
    53-56% of flagged points carry a count of 0 (first run of this script, 28 Oct 2026)."""
    cols = ["year", "event_id", "match_id", "tm1Rally", "tm2Rally", "tm1Shot", "tm2Shot",
            "rallyLengthMissing", "tm1AtNet", "tm2AtNet"]
    p = pd.read_parquet(P9 / "points.parquet", columns=cols)
    p["key"] = p["year"].astype(str) + "/" + p["event_id"].astype(str) + "/" + p["match_id"].astype(str)
    flag = p["rallyLengthMissing"].astype(str).str.upper().eq("FALSE")
    shots = pd.to_numeric(p["tm1Shot"], errors="coerce") + pd.to_numeric(p["tm2Shot"], errors="coerce")
    p["known"] = flag & shots.between(1, 60)
    r1 = pd.to_numeric(p["tm1Rally"], errors="coerce")
    r2 = pd.to_numeric(p["tm2Rally"], errors="coerce")
    p["rally_old"] = r1 + r2
    p.loc[~p["known"] | (p["rally_old"] < 0) | (p["rally_old"] > 60), "rally_old"] = np.nan
    p["net"] = p["tm1AtNet"].astype(str).str.upper().eq("TRUE") | p["tm2AtNet"].astype(str).str.upper().eq("TRUE")
    return p[["key", "known", "rally_old", "net"]]


def main() -> None:
    m = load_matches()
    p = load_points()

    per_match = p.groupby("key").agg(pts=("known", "size"), known=("known", "sum"),
                                     rally_mean=("rally_old", "mean"), net_pts=("net", "sum"))
    m = m.merge(per_match, left_on="key", right_index=True, how="left")
    m["known_share"] = m["known"] / m["pts"]
    m["covered"] = m["known_share"] >= 0.5
    res: dict = {"matches": int(len(m)), "matches_with_points": int(m["pts"].notna().sum())}

    # 1. event-level coverage
    ev = (m.dropna(subset=["pts"]).groupby(["year", "event_id", "level_group"])
          .agg(n=("key", "size"), cov=("covered", "mean")).reset_index())
    ev["kind"] = pd.cut(ev["cov"], [-0.01, 0.05, 0.95, 1.01], labels=["none (<=5%)", "partial", "full (>=95%)"])
    t1 = (ev.groupby(["level_group", "kind"], observed=False)
          .agg(events=("n", "size"), matches=("n", "sum")).reset_index())
    res["events_by_kind"] = t1.to_dict(orient="records")
    print("\n1. Events by coverage kind (share of matches with rally length on >= half their points)")
    print(t1.to_string(index=False))
    t1b = m.dropna(subset=["pts"]).groupby(["level_group", "draw"]).agg(
        matches=("key", "size"), covered=("covered", "mean")).reset_index()
    res["covered_by_level_draw"] = t1b.to_dict(orient="records")
    print(t1b.to_string(index=False))

    # 2. partial events: coverage by court
    part_keys = set(ev.loc[ev["kind"] == "partial", ["year", "event_id"]].astype(str).agg("/".join, axis=1))
    mp = m[(m["year"].astype(str) + "/" + m["event_id"].astype(str)).isin(part_keys)].dropna(subset=["pts"]).copy()
    # rank courts inside each event by how many matches they host (court 1 = busiest)
    # court_name is empty in this copy, so courts are ranked by how many matches they host
    mp["court_matches"] = mp.groupby(["year", "event_id", "court_id"])["key"].transform("size")
    mp["court_kind"] = (mp.groupby(["year", "event_id"])["court_matches"]
                        .rank(method="dense", ascending=False).clip(upper=4).astype(int)
                        .map({1: "busiest court", 2: "2nd", 3: "3rd", 4: "4th or later"}))
    t2 = mp.groupby(["level_group", "court_kind"]).agg(matches=("key", "size"), covered=("covered", "mean")).reset_index()
    # per partial event: does coverage split cleanly by court (each court all or nothing)?
    pc = mp.groupby(["year", "event_id", "court_id"])["covered"].mean()
    clean = float(((pc <= 0.05) | (pc >= 0.95)).mean()) if len(pc) else float("nan")
    res["partial_events"] = {"events": len(part_keys), "matches": int(len(mp)),
                             "by_court_kind": t2.to_dict(orient="records"),
                             "share_of_event_courts_all_or_nothing": clean}
    print("\n2. Partial events: coverage by court")
    print(t2.to_string(index=False))
    print("share of (event, court) cells that are all-or-nothing:", round(clean, 3))

    # 3. rally-length mix from the rally files' category
    rc = pd.read_parquet(P9 / "rally.parquet", columns=["year", "event_id", "match_id", "category"])
    rc["key"] = rc["year"].astype(str) + "/" + rc["event_id"].astype(str) + "/" + rc["match_id"].astype(str)
    rc = rc.merge(m[["key", "level_group"]], on="key", how="left")
    cat = rc["category"].astype(str)
    res["category_values"] = cat.value_counts().head(30).to_dict()
    print("\n3. Rally files' categories (top 30):")
    print(cat.value_counts().head(30).to_string())

    def band(c: str) -> str:
        c = c.lower()
        if c.startswith("serve"):
            return "1 serve"
        if c.startswith("return"):
            return "2 return"
        if c.startswith("3rd") or c.startswith("4th"):
            return "3-4"
        if c[:1] in "5678":
            return "5-8"
        if c.startswith("9") or c.startswith("10"):
            return "9+"
        return "other"
    rc["band"] = cat.map(band)
    t3 = pd.crosstab(rc["level_group"], rc["band"], normalize="index").round(3)
    res["band_mix_by_level"] = t3.reset_index().to_dict(orient="records")
    print("\nBand mix of rally-file points by level (share of points):")
    print(t3.to_string())

    # 4. per covered match: known points, match-mean rally (old count) spread
    cm = m[m["covered"] == True]  # noqa: E712
    q = cm.groupby("level_group").agg(matches=("key", "size"), known_pts_median=("known", "median"),
                                      rally_mean_median=("rally_mean", "median"),
                                      rally_mean_sd=("rally_mean", "std")).reset_index()
    res["covered_match_summary"] = q.to_dict(orient="records")
    print("\n4. Covered matches: known points per match; match mean of tm1Rally+tm2Rally (raw old count)")
    print(q.to_string(index=False))

    # 5. previous round at the same event covered?
    rows = []
    for side in ("p1_id", "p2_id"):
        x = m[["year", "event_id", "draw", "round_from_code", "level_group", "covered", "key"]].copy()
        x["player"] = m[side]
        rows.append(x)
    pm = pd.concat(rows, ignore_index=True).dropna(subset=["player"])
    pm = pm[pm["player"].astype(str).str.len() > 0]
    # order rounds within the event by the draw then by the event's own round order (string codes)
    rc_order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4, "R128": 10, "R64": 11, "R32": 12, "R16": 13,
                "QF": 14, "SF": 15, "F": 16, "RR": 12}
    pm["r"] = pm["round_from_code"].astype(str).str.upper().map(rc_order)
    res["round_codes"] = pm["round_from_code"].astype(str).value_counts().to_dict()
    pm = pm.dropna(subset=["r"]).sort_values(["player", "year", "event_id", "r"])
    pm["prev_cov"] = pm.groupby(["player", "year", "event_id"])["covered"].shift(1)
    later = pm[pm["prev_cov"].notna()]
    t5 = later.groupby("level_group").agg(
        later_round_rows=("key", "size"),
        this_covered=("covered", "mean"),
        prev_covered=("prev_cov", lambda s: float(pd.Series(s, dtype=float).mean())),
        both_covered=("covered", lambda s: float((s.astype(bool) & later.loc[s.index, "prev_cov"].astype(bool)).mean())),
    ).reset_index()
    res["previous_round_coverage"] = t5.to_dict(orient="records")
    print("\n5. Player-rows after the first round at an event: is the previous round covered?")
    print(t5.to_string(index=False))

    # 6. net flags
    netm = m[m["net_pts"].fillna(0) > 0]
    per_player = pd.concat([netm["p1_id"], netm["p2_id"]]).value_counts()
    res["net"] = {"matches_with_net_flags": int(len(netm)),
                  "players": int(per_player.size),
                  "players_with_ge3": int((per_player >= 3).sum()),
                  "players_with_ge5": int((per_player >= 5).sum()),
                  "median_matches_per_player": float(per_player.median()),
                  "by_level": netm["level_group"].value_counts().to_dict()}
    print("\n6. Net flags:", res["net"])
    print("\nJSON of every table above:")
    print(json.dumps(res, default=str))


if __name__ == "__main__":
    main()

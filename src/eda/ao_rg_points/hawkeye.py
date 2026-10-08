"""The Hawk-Eye Court Vision copy against the gap slam_points_ao_rg: what the staged copy holds for each gap match.

Reads:
* data/dump/points/slam_ball_tracking/ (src/ingest/public_dump/slam_ball_tracking.py): matches.parquet with each
  match's counts, and the points/, json_points/ and shots/ tables for the cross-checks.
* data/studies/gap_sources/hawkilol_matches.csv: lane A's replay of every match of the same commit against
  Sackmann's official score (``pbp_status``) and its link to the data map (``map_uid``, build of 25 Sep 2026);
  src/eda/gap_sources/hawkilol_matches.py, with 40 of 40 sampled "complete" gap matches confirmed by
  src/eda/gap_sources/hawkilol_spotcheck.py.
* data/studies/ao_rg_points/gap_matches.csv (gap.py): the gap's 1,636 matches, with the uid of the same build.

Checks, over the staged tables:
1. Staged against lane A: every match's points (the final row of each point) and tracked share agree with lane A's
   reading of the research copy.
2. CSV against JSON (2022-2024): one CSV row per JSON point record, the same point keys, and ``is_track_avail``
   true exactly when the record's ``trajectoryData`` is not empty (the repository makes the CSV from the JSON).
3. Strokes: the positions of a tracked rally come as hit / peak / net / bounce groups.

Writes data/studies/ao_rg_points/hawkeye_gap.csv (one row per gap match: what the copy holds) and
hawkeye_summary.json.

Run: ./python.sh src/eda/ao_rg_points/hawkeye.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[3]
STAGED = PROJECT_ROOT / "data" / "dump" / "points" / "slam_ball_tracking"
LANE_A = PROJECT_ROOT / "data" / "studies" / "gap_sources" / "hawkilol_matches.csv"
OUT = PROJECT_ROOT / "data" / "studies" / "ao_rg_points"
TRACKED = 0.9
COMPLETE = "complete"
TNAME = {"AO": "Australian Open", "RG": "Roland Garros"}


def staged_matches() -> pd.DataFrame:
    m = pd.read_parquet(STAGED / "matches.parquet")
    m["code"] = m["match_id"].str.split("_").str[-1]
    m["year"] = m["year"].astype(int)
    for c in ("n_csv_rows", "n_csv_points", "csv_track_share", "n_json_points", "n_json_points_tracked",
              "n_json_positions"):
        m[c] = pd.to_numeric(m[c], errors="coerce")
    m["json_on_disk"] = m["json_on_disk"].eq("TRUE")
    m["tracked"] = m["tracked"].eq("TRUE")
    return m


def check_against_lane_a(m: pd.DataFrame, lane: pd.DataFrame) -> dict:
    j = m.merge(lane, left_on=["year", "slam", "tour", "code"], right_on=["year", "slam", "tour", "match_id"],
                how="outer", suffixes=("", "_a"), indicator=True)
    both = j[j["_merge"].eq("both")]
    return {"staged_matches": int(len(m)), "lane_a_matches": int(len(lane)),
            "joined": int(len(both)), "only_staged": int(j["_merge"].eq("left_only").sum()),
            "only_lane_a": int(j["_merge"].eq("right_only").sum()),
            "points_differ": int((both["n_csv_points"] != both["n_points"]).sum()),
            "tracked_share_differs_by_more_than_0.0001": int(
                ((both["csv_track_share"] - both["track_share_points"]).abs() > 1e-4).sum()),
            "tracked_flag_differs": int((both["csv_track_share"].ge(TRACKED) != both["tracked_a"]).sum())
            if "tracked_a" in both else None}


def check_csv_against_json(m: pd.DataFrame) -> dict:
    """Record by record for every match whose JSON is staged. The CSV's ``point_ID`` is the record's own ``pointId``
    field; the JSON's dict key equals it except in placeholder records (``pointId`` "NA", no scorer), which the CSV
    carries as point_ID "NA". So the check pairs records by match and ``pointId`` counts."""
    out = Counter()
    for tag in sorted(p.stem for p in (STAGED / "json_points").glob("*.parquet")):
        csv = pd.read_parquet(STAGED / "points" / f"{tag}.parquet",
                              columns=["match_id", "tour", "point_ID", "is_track_avail"])
        js = pd.read_parquet(STAGED / "json_points" / f"{tag}.parquet", columns=["match_id", "tour", "point_key", "pointId"])
        shots = pq.read_table(STAGED / "shots" / f"{tag}.parquet", columns=["match_id", "tour", "point_key", "position"]).to_pandas()
        out["csv_rows"] += len(csv)
        out["json_records"] += len(js)
        out["json_placeholder_records"] += int(js["pointId"].eq("NA").sum())
        out["json_key_differs_from_pointId"] += int((js["point_key"] != js["pointId"]).sum())
        a = csv.groupby(["tour", "match_id", "point_ID"]).size()
        b = js.groupby(["tour", "match_id", "pointId"]).size()
        both = pd.concat([a.rename("csv"), b.rename("json")], axis=1).fillna(0)
        out["pointId_counts_differ"] += int((both["csv"] != both["json"]).sum())
        # tracking: CSV rows flagged tracked against JSON records with a trajectory, per match
        traj = shots.drop_duplicates(["tour", "match_id", "point_key"]).groupby(["tour", "match_id"]).size()
        flag = csv[csv["is_track_avail"].eq("True")].groupby(["tour", "match_id"]).size()
        both = pd.concat([flag.rename("csv"), traj.rename("json")], axis=1).fillna(0)
        out["matches_where_tracked_counts_differ"] += int((both["csv"] != both["json"]).sum())
        out["records_with_trajectory"] += int(traj.sum())
        out["trajectory_positions"] += len(shots)
        # a stroke's positions: hit, peak, net, bounce; 'last' closes a rally
        out.update({f"position:{k}": int(v) for k, v in shots["position"].value_counts().items()})
    return dict(out)


def gap_rows(gap: pd.DataFrame, m: pd.DataFrame, lane: pd.DataFrame) -> pd.DataFrame:
    lane = lane.dropna(subset=["map_uid"]).copy()
    lane["map_uid"] = lane["map_uid"].astype(int)
    lane = lane.merge(m[["year", "slam", "tour", "code", "match_id", "json_on_disk", "n_json_points",
                         "n_json_points_tracked", "n_json_positions", "tracked"]].rename(columns={"match_id": "copy_match_id"}),
                      left_on=["year", "slam", "tour", "match_id"], right_on=["year", "slam", "tour", "code"], how="left")
    keep = ["map_uid", "copy_match_id", "file", "status", "pbp_status", "n_points", "track_share_points",
            "json_on_disk", "n_json_points", "n_json_points_tracked", "n_json_positions", "tracked"]
    g = gap.merge(lane[keep], on="map_uid", how="left")
    g["in_copy"] = g["copy_match_id"].notna()
    g["complete"] = g["pbp_status"].eq(COMPLETE)
    g["tracked"] = g["tracked"].eq(True)
    g["fills_point"] = g["complete"]
    g["fills_shot"] = g["complete"] & g["tracked"] & g["json_on_disk"].eq(True)
    return g


def main() -> int:
    m = staged_matches()
    lane = pd.read_csv(LANE_A, low_memory=False)
    lane = lane.rename(columns={"tracked": "tracked_a"})
    summary = {"source": "hawkilol/tennisSlamBallTracking @ f97a9b3, staged by src/ingest/public_dump/slam_ball_tracking.py",
               "check_staged_against_lane_a": check_against_lane_a(m, lane),
               "check_csv_against_json": check_csv_against_json(m)}
    lane = lane.rename(columns={"tracked_a": "tracked_lane_a"})
    gap = pd.read_csv(OUT / "gap_matches.csv")
    g = gap_rows(gap, m, lane)
    cols = ["map_uid", "edition", "tour", "tname", "year", "d", "name1", "name2", "in_copy", "copy_match_id", "file",
            "status", "pbp_status", "complete", "n_points", "track_share_points", "json_on_disk", "n_json_points",
            "n_json_points_tracked", "n_json_positions", "tracked", "fills_point", "fills_shot"]
    g[cols].to_csv(OUT / "hawkeye_gap.csv", index=False)
    by = g.groupby(["tname", "tour", "year"]).agg(gap=("map_uid", "size"), in_copy=("in_copy", "sum"),
                                                 complete=("complete", "sum"), complete_and_tracked=("fills_shot", "sum"))
    summary["gap"] = {"matches": int(len(g)), "in_copy": int(g["in_copy"].sum()),
                      "complete_point_records": int(g["fills_point"].sum()),
                      "complete_and_every_stroke_tracked": int(g["fills_shot"].sum()),
                      "pbp_status_in_copy": {k: int(v) for k, v in g.loc[g["in_copy"], "pbp_status"].value_counts().items()},
                      "by_tname_tour_year": [{"tname": t, "tour": tr, "year": int(y), **{k: int(v) for k, v in r.items()}}
                                             for (t, tr, y), r in by.iterrows()],
                      "left_without_a_complete_record": int((~g["fills_point"]).sum()),
                      "left_by_year": {int(k): int(v) for k, v in g.loc[~g["fills_point"]].groupby("year").size().items()}}
    (OUT / "hawkeye_summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("check_staged_against_lane_a", "check_csv_against_json")}, indent=1))
    print(json.dumps({k: v for k, v in summary["gap"].items() if k != "by_tname_tour_year"}, indent=1))
    print(by.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""SofaScore's records for the gap slam_points_ao_rg: what was fetched, how complete it is, and whether it agrees with
the official result and with the Hawk-Eye copy.

Reads:
* data/studies/ao_rg_points/sofascore_links.csv (link_sofascore.py): each gap match's SofaScore event.
* data/raw/point_sources/sofascore_tournaments/ and data/dump/points/sofascore_tournaments/events.parquet
  (src/ingest/point_sources/sofascore_tournaments.py): the records and the events' own scores.
* data/dump/matches/tennis_my_life/{atp_main,wta_main}/: the official score of every Slam main-draw match.
* data/studies/gap_sources/hawkilol_matches.csv: the Hawk-Eye copy's replayed score of each match it holds (lane A),
  with the map uid of the same build as the frozen gap list.

Per gap match:
* asked: the answers to /point-by-point and /statistics (200, 404, or not asked yet).
* complete: every set of the record has as many games as SofaScore's own score of it; a retirement may also list
  the game in progress (the gap research's rule, src/eda/gap_sources/sofascore_probe.py).
* full box: aces, double faults, first serves in and won, second serves won and break points saved.
* official: SofaScore's set scores, turned to the winner's side, against Tennis My Life's (tie-break points aside).
* hawkeye: where the copy's record is complete, SofaScore's set scores against the copy's replay.

Writes data/studies/ao_rg_points/sofascore_check.csv (one row per gap match) and sofascore_check.json.

Run: ./python.sh src/eda/ao_rg_points/sofascore_check.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P                    # noqa: E402
from src.ingest.point_sources import sofascore as S                  # noqa: E402
from src.ingest.point_sources import sofascore_tournaments as T      # noqa: E402

OUT = PROJECT_ROOT / "data" / "studies" / "ao_rg_points"
TML = PROJECT_ROOT / "data" / "dump" / "matches" / "tennis_my_life"
LANE_A = PROJECT_ROOT / "data" / "studies" / "gap_sources" / "hawkilol_matches.csv"
FULL_BOX = {"aces", "doubleFaults", "firstServeAccuracy", "firstServePointsAccuracy", "secondServePointsAccuracy",
            "breakPointsSaved"}
SLAMS = ["Australian Open", "Roland Garros", "Wimbledon", "US Open"]


def set_scores(score) -> list[tuple[int, int]]:
    """'7-6(5) 3-6 6-4 RET' -> [(7, 6), (3, 6), (6, 4)]: the games of each set, first player first. A last set of
    0-0 ('6-2 0-0 RET', a retirement between sets) is dropped, as in sofascore_sets."""
    out = []
    for tok in str(score or "").split():
        m = re.fullmatch(r"(\d+)-(\d+)(?:\(\d+\))?", tok)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
    while out and out[-1] == (0, 0):
        out.pop()
    return out


def sofascore_sets(event: pd.Series, winner_side: str) -> list[tuple[int, int]]:
    """SofaScore's set scores from the winner's side ('home' or 'away'). A retirement between sets is listed as a
    last set of 0-0, which the official score does not have; it is dropped."""
    out = []
    for n in range(1, 6):
        h, a = pd.to_numeric(event.get(f"home_set{n}"), errors="coerce"), pd.to_numeric(event.get(f"away_set{n}"), errors="coerce")
        if pd.isna(h) or pd.isna(a):
            break
        out.append((int(h), int(a)) if winner_side == "home" else (int(a), int(h)))
    while out and out[-1] == (0, 0):
        out.pop()
    return out


def record_verdict(pbp: list, event: pd.Series) -> dict:
    """The research's completeness rule: games per set of the record against SofaScore's own set scores."""
    shape = S.pbp_shape(pbp)
    want = [g for g in (pd.to_numeric(event.get(f"home_set{n}"), errors="coerce")
                        + pd.to_numeric(event.get(f"away_set{n}"), errors="coerce") for n in range(1, 6)) if pd.notna(g)]
    have = shape["games_per_set"]
    retired = "retired" in str(event.get("status_description") or "").lower()
    extra = sum(have) - sum(want)
    if not want:
        verdict = "no score to compare"
    elif len(have) == len(want) and all(h == w for h, w in zip(have, want)):
        verdict = "complete"
    elif retired and len(have) == len(want) and 0 <= extra <= 1 and all(h >= w for h, w in zip(have, want)):
        verdict = "complete to retirement"
    elif len(have) <= len(want) and all(h <= w for h, w in zip(have, want)):
        verdict = "short"
    else:
        verdict = "other"
    return {"pbp_sets": shape["sets"], "pbp_games": shape["games"], "pbp_points": shape["points"],
            "score_games": int(sum(want)), "pbp_verdict": verdict}


def official_scores() -> pd.DataFrame:
    frames = []
    for tour, folder in (("M", "atp_main"), ("W", "wta_main")):
        for path in sorted((TML / folder).glob("20*.parquet")):
            year = int(path.name[:4])
            if 2022 <= year <= 2026:
                t = pd.read_parquet(path, columns=["tourney_name", "tourney_level", "round", "winner_name", "loser_name", "score"])
                t = t[t["tourney_level"].eq("G") & t["tourney_name"].isin(SLAMS)]
                frames.append(t.assign(tour=tour, year=year))
    return pd.concat(frames, ignore_index=True).rename(columns={"tourney_name": "tname"})


def main() -> int:
    links = pd.read_csv(OUT / "sofascore_links.csv")
    receipts = P.receipts_for(T.SOURCE)
    events = pd.read_parquet(P.dump_path(T.SOURCE, "events.parquet")).set_index("event_id")
    off = official_scores()
    off_key = off.set_index(["tour", "year", "tname", "winner_name", "loser_name"])["score"]
    off_key = off_key[~off_key.index.duplicated()]
    lane = pd.read_csv(LANE_A, usecols=["map_uid", "pbp_status", "replay_score"]).dropna(subset=["map_uid"])
    lane = lane.assign(map_uid=lane["map_uid"].astype(int)).drop_duplicates("map_uid").set_index("map_uid")
    rows = []
    for _, g in links.iterrows():
        row = g[["map_uid", "edition", "tour", "tname", "year", "d", "name1", "name2", "event_id"]].to_dict()
        eid = g["event_id"]
        if pd.isna(eid):
            rows.append({**row, "pbp_asked": "unlinked", "stats_asked": "unlinked"})
            continue
        eid = int(eid)
        row["event_id"] = eid
        ev = events.loc[str(eid)] if str(eid) in events.index else None
        for part, col in (("point-by-point", "pbp_asked"), ("statistics", "stats_asked")):
            rec = receipts.get(f"events/{eid}/{part}") or {}
            row[col] = rec.get("error") or rec.get("status") or "not asked"
        side = g["name1_side"]
        if ev is not None:
            row["ss_status"] = ev["status_description"]
            row["ss_sets_from_winner"] = " ".join(f"{a}-{b}" for a, b in sofascore_sets(ev, side))
            if row["pbp_asked"] == 200:
                row.update(record_verdict(P.read_json(T.event_doc_path(eid, "point-by-point")).get("pointByPoint") or [], ev))
            if row["stats_asked"] == 200:
                stats = P.read_json(T.event_doc_path(eid, "statistics")).get("statistics") or []
                keys = {it.get("key") for p in stats if p.get("period") == "ALL"
                        for grp in p.get("groups") or [] for it in grp.get("statisticsItems") or []}
                row["full_box"] = FULL_BOX <= keys
            official = off_key.get((g["tour"], int(g["year"]), g["tname"], g["name1"], g["name2"]))
            row["official_score"] = official
            if str(ev["status_description"]).lower() == "walkover" or "W/O" in str(official or ""):
                row["official_agrees"] = "walkover"
            elif official is not None:
                row["official_agrees"] = sofascore_sets(ev, side) == set_scores(official)
            if g["map_uid"] in lane.index and lane.loc[g["map_uid"], "pbp_status"] == "complete":
                hk = set_scores(lane.loc[g["map_uid"], "replay_score"])
                row["hawkeye_score"] = lane.loc[g["map_uid"], "replay_score"]
                row["hawkeye_agrees"] = sofascore_sets(ev, side) == hk
        rows.append(row)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "sofascore_check.csv", index=False)
    asked = t[t["pbp_asked"].isin([200, 404])]
    ok = asked["pbp_verdict"].isin(["complete", "complete to retirement"]) if "pbp_verdict" in asked else pd.Series(dtype=bool)
    summary = {
        "gap_matches": int(len(t)), "linked": int(t["event_id"].notna().sum()),
        "point_by_point": {str(k): int(v) for k, v in t["pbp_asked"].value_counts().items()},
        "statistics": {str(k): int(v) for k, v in t["stats_asked"].value_counts().items()},
        "record_verdicts": {str(k): int(v) for k, v in t.get("pbp_verdict", pd.Series(dtype=str)).value_counts().items()},
        "complete_records": int(ok.sum()),
        "full_box_scores": int(t.get("full_box", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()),
        "official_agrees": {str(k): int(v) for k, v in t.get("official_agrees", pd.Series(dtype=object)).value_counts(dropna=False).items()},
        "hawkeye_agrees": {str(k): int(v) for k, v in t.get("hawkeye_agrees", pd.Series(dtype=object)).value_counts(dropna=False).items()},
        "by_edition": {e: {"gap": int(len(x)), "records": int(x["pbp_asked"].eq(200).sum()),
                           "complete": int(x.get("pbp_verdict", pd.Series(dtype=str)).isin(["complete", "complete to retirement"]).sum())}
                       for e, x in t.groupby("edition")},
    }
    (OUT / "sofascore_check.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "by_edition"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

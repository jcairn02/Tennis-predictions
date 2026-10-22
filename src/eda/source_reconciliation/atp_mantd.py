"""Reader atp_mantennisdata: ManTennisData's box scores (the ATP Stats Centre's match statistics as atptour.com shows
them, kept as CSV by a third party; staged in data/dump/matches/mantennisdata/atp_matches_<year>.parquet).

Scope: the staged seasons 2015-2026 (the part's window is 2018-2026; 2015-2017 are the same reader and are kept,
labelled by x_season, because they overlap the model's training seasons). ATP tour level, Challengers, Slams, team
events; main draw and qualifying.

Mapping onto the contract (winner columns win_*, loser columns los_*; Sackmann's definitions):
    ace aces · df double_faults · svpt first_serves_total (every point served: the first-serve attempts) ·
    first_in first_serves_in · first_won first_serve_points_won · second_won second_serve_points_won ·
    sv_gms service_games_played · bp_faced break_points_serve_total · bp_saved break_points_saved ·
    sv_won service_points_won.
    Its own redundant totals are kept as x_ columns for the internal-consistency check: x_first_pts_total
    (first_serve_points_total, should equal first_in), x_second_pts_total (second_serve_points_total, should equal
    svpt - first_in), x_service_pts_total (service_points_total, should equal svpt).
Orientation: by the winner's and loser's ATP codes and names (the linker), never by who won; x_won is the source's
    own winner flag (player 1 = winner_*), checked against Stage 0's `won`.
complete: the source marks the match finished (match_ret empty); retired ('(RET)') and walkovers ('(W/O)') are False,
    with x_status giving which.
Link: the event linker (atp_common.EventLinker) on (season, ATP event id from tournament_id 'YYYY-<id>'), the draw
    (Q1-Q3 = qualifying), the round (stadie_id, a tie-breaker) and both players (crosswalk id, full name, abbreviated
    name). x_atp_key = '<year>_<event>_<CODE>' from the stats link: the Infosys key, for joining to the key statistics.

Run: ./python.sh src/eda/source_reconciliation/atp_mantd.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import atp_common as A  # noqa: E402

READER = "atp_mantennisdata"
YEARS = range(2015, 2027)
STATS_KEY = re.compile(r"/(\d{4})/(\d+)/([mq]s\d{3})", re.I)
MAP = {"ace": "aces", "df": "double_faults", "svpt": "first_serves_total", "first_in": "first_serves_in",
       "first_won": "first_serve_points_won", "second_won": "second_serve_points_won",
       "sv_gms": "service_games_played", "bp_faced": "break_points_serve_total", "bp_saved": "break_points_saved",
       "sv_won": "service_points_won", "x_first_pts_total": "first_serve_points_total",
       "x_second_pts_total": "second_serve_points_total", "x_service_pts_total": "service_points_total",
       "x_spd1": "average_first_serves_kmh"}


def load(years=YEARS) -> pd.DataFrame:
    """One row per ManTennisData match: identity, link fields and both players' stats (_1 winner, _2 loser)."""
    parts = []
    for y in years:
        f = A.MANTD / f"atp_matches_{y}.parquet"
        if f.exists():
            parts.append(pd.read_parquet(f).assign(x_file_year=y))
    m = pd.concat(parts, ignore_index=True)
    key = m["stats_url"].fillna("").str.extract(STATS_KEY)
    m["x_atp_key"] = np.where(key[0].notna(), key[0] + "_" + key[1] + "_" + key[2].str.upper(), None)
    ev = m["tournament_id"].astype(str).str.extract(r"^(\d{4})-0*(\d+)$")
    m["season"] = pd.to_numeric(ev[0], errors="coerce").fillna(-1).astype(int)
    m["ev"] = pd.to_numeric(ev[1], errors="coerce").fillna(-1).astype(int)
    rnd = m["stadie_id"].fillna("").astype(str).str.upper()
    m["round"] = rnd
    m["qual"] = rnd.str.match(r"^Q\d$")
    m["c1"], m["c2"] = m["winner_code"].map(A.atp_code), m["loser_code"].map(A.atp_code)
    m["f1"], m["f2"] = m["winner_name"].fillna(""), m["loser_name"].fillna("")
    m["source_key"] = "mantd:" + m["id"].astype(str)
    out = m[["source_key", "x_atp_key", "season", "ev", "round", "qual", "c1", "c2", "f1", "f2", "match_ret",
             "match_score", "tournament_id", "x_file_year"]].copy()
    for no, pre in (("1", "win_"), ("2", "los_")):
        for f, col in MAP.items():
            out[f"{f}_{no}"] = pd.to_numeric(m[pre + col].astype("string").str.strip().replace("", pd.NA),
                                             errors="coerce").astype("float64")
    return out


def build(xw: pd.Series | None = None, linker: A.EventLinker | None = None) -> tuple[pd.DataFrame, dict]:
    m = load()
    info = {"reader": READER, "source": "data/dump/matches/mantennisdata/atp_matches_<year>.parquet",
            "seasons_read": [int(y) for y in YEARS], "records_read": int(len(m)),
            "records_by_file_year": m["x_file_year"].value_counts().sort_index().to_dict()}
    dropped = {}
    has_stats = m[[f"svpt_1", "svpt_2"]].notna().all(axis=1) | m[["ace_1", "ace_2"]].notna().all(axis=1)
    dropped["no_box_statistics"] = int((~has_stats).sum())
    dupe = m.duplicated("source_key", keep="first")
    dropped["duplicate_source_key"] = int(dupe.sum())
    m = m[has_stats & ~dupe].copy()
    linker = linker or A.EventLinker()
    lk = linker.link(m, xw)
    m = m.join(lk)
    reasons = m.loc[m["match_id"].isna(), "unlinked_reason"].value_counts().to_dict()
    dropped.update({f"unlinked:{k}": int(v) for k, v in reasons.items()})
    info["dropped"] = dropped
    info["linked"] = int(m["match_id"].notna().sum())
    info["link_methods"] = m["link_method"].value_counts().to_dict()
    lm = m[m["match_id"].notna()].copy()
    status = lm["match_ret"].fillna("").str.strip()
    lm["x_status"] = status.replace({"": "completed", "(RET)": "retired", "(W/O)": "walkover"})
    lm["complete"] = status.eq("")
    lm["x_season"] = lm["season"]
    fields = A.FIELDS + ["x_first_pts_total", "x_second_pts_total", "x_service_pts_total", "x_spd1"]
    rows = A.long_rows(lm, fields, extra=["complete", "link_method", "x_atp_key", "x_status", "x_season",
                                          "match_score"])
    rows["x_won"] = rows["x_player_no"].eq(1)
    # long_rows stacks the player-1 rows, then the player-2 rows, in lm's order
    rows["x_code"] = pd.concat([lm["c1"], lm["c2"]], ignore_index=True).to_numpy()
    rows = rows.rename(columns={"match_score": "x_score"})
    info["winner_vs_stage0"] = A.winner_check(rows)
    # its own redundant totals
    sub = rows[rows["svpt"].notna()]
    info["internal_consistency"] = {
        "first_pts_total_equals_first_in": _share(sub["x_first_pts_total"], sub["first_in"]),
        "second_pts_total_equals_svpt_minus_first_in": _share(sub["x_second_pts_total"], sub["svpt"] - sub["first_in"]),
        "service_pts_total_equals_svpt": _share(sub["x_service_pts_total"], sub["svpt"]),
        "sv_won_equals_first_won_plus_second_won": _share(sub["sv_won"], sub["first_won"] + sub["second_won"])}
    return A.to_contract(rows, READER, "box"), info


def _share(a: pd.Series, b: pd.Series) -> dict:
    both = a.notna() & b.notna()
    return {"n": int(both.sum()), "equal": round(float((a[both] == b[both]).mean()), 5) if both.any() else None}


def main() -> int:
    rows, info = build(A.crosswalk())
    info["crosswalk_codes"] = int(len(A.crosswalk()))
    A.write_reader(READER, rows, info)
    return 0


if __name__ == "__main__":
    sys.exit(main())

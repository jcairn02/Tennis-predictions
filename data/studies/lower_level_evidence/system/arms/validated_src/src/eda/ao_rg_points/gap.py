"""The data map's gap slam_points_ao_rg: its matches, their editions, and each edition's SofaScore season.

The gap is every Grand Slam main-draw singles match of 2022-2026 whose best grain on the map is below point
(data/data_map.yaml, `gaps:`): 1,636 matches in the measurement of 25 Sep 2026, 1,631 of them at the Australian
Open and Roland Garros. The map's per-match table is rebuilt (and its uids renumbered) by every build, so the list
is frozen here with the names, dates and uid of that measurement.

Reads:
* data/studies/data_map/matches.parquet: the map's per-match table (built 25 Sep 2026).
* data/studies/gap_sources/sofascore_editions.csv: the SofaScore seasons the gap probe located on 29 Sep 2026
  (20 of the gap's 22 editions; women's Roland Garros 2026 and the women's US Open 2024 were not reached).

Writes data/studies/ao_rg_points/:
* gap_matches.csv: one row per gap match.
* sofascore_seasons.csv: one row per edition, with the season's ids where known, and for the others what
  src/ingest/point_sources/sofascore_tournaments.py needs to find them (category, name pattern, days to read).

Run: ./python.sh src/eda/ao_rg_points/gap.py            (keeps gap_matches.csv once written; --refresh derives it again)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAP = PROJECT_ROOT / "data" / "studies" / "data_map" / "matches.parquet"
PROBE = PROJECT_ROOT / "data" / "studies" / "gap_sources" / "sofascore_editions.csv"
OUT = PROJECT_ROOT / "data" / "studies" / "ao_rg_points"

GAP = {"tours": ["M", "W"], "levels": ["GS"], "years": [2022, 2023, 2024, 2025, 2026], "below": ["result", "stats"]}
CATEGORY = {"M": 3, "W": 6}                        # SofaScore's ATP and WTA categories
EVENT = {"M": "Men", "W": "Women"}
SS_NAME = {"Australian Open": "Australian Open", "Roland Garros": "Roland Garros", "Wimbledon": "Wimbledon",
           "US Open": "US Open"}
LOCATE_OFFSETS = [2, 5, 8]                         # days after the first gap match's date to read listings on
CREATOR_TNAME = {"ausopen": "Australian Open", "ausopen_wayback": "Australian Open", "slam_draws": "Australian Open"}


def gap_matches(matches: pd.DataFrame) -> pd.DataFrame:
    m = matches[matches["tour"].isin(GAP["tours"]) & matches["level"].isin(GAP["levels"])
                & matches["year"].isin(GAP["years"]) & matches["best"].isin(GAP["below"])].copy()
    m = m.rename(columns={"uid": "map_uid"})
    # Five gap matches were added to the map by the Australian Open's own files without a tournament name
    # (four from the archived 2022 draws, one from the 2026 feed); their source names the tournament.
    m["tname_from"] = np.where(m["tname"].isna(), "creator", "map")
    m["tname"] = m["tname"].fillna(m["creator"].map(CREATOR_TNAME))
    m["edition"] = m["tour"] + "|" + m["tname"] + "|" + m["year"].astype(str)
    m["d"] = pd.to_datetime(m["d"]).dt.date
    cols = ["map_uid", "edition", "tour", "tname", "tname_from", "year", "d", "name1", "name2", "creator", "best",
            "sources"]
    return m[cols].sort_values(["tname", "year", "tour", "d", "name1"]).reset_index(drop=True)


def held_seasons() -> dict[str, dict]:
    """'tour|tname|year' -> the season of a Slam singles listing the SofaScore adapter holds (so a season it found
    itself is recorded here too)."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from src.ingest.point_sources import common as P
    from src.ingest.point_sources import sofascore_tournaments as T
    out = {}
    for key in T.held_seasons():
        pages = T.season_pages(key)
        for e in (P.read_json(pages[0][1]).get("events") or []) if pages else []:
            ut, season = (e.get("tournament") or {}).get("uniqueTournament") or {}, e.get("season") or {}
            m = re.fullmatch(r"(Australian Open|Roland Garros|Wimbledon|US Open), (Men|Women)", ut.get("name") or "")
            if m:
                tour = "M" if m.group(2) == "Men" else "W"
                out[f"{tour}|{m.group(1)}|{season.get('year')}"] = {
                    "utid": ut.get("id"), "sid": season.get("id"), "ss_tournament": ut.get("name"),
                    "ss_season": season.get("name")}
                break
    return out


def seasons(gap: pd.DataFrame, probe: pd.DataFrame) -> pd.DataFrame:
    probe = probe[probe["gap"].eq("slam_points_ao_rg")].set_index("edition")
    held = held_seasons()
    rows = []
    for edition, g in gap.groupby("edition", sort=True):
        tour, tname, year = edition.split("|")
        d0 = pd.Timestamp(min(g["d"]))
        row = {"edition": edition, "tour": tour, "tname": tname, "year": int(year), "gap_matches": len(g),
               "d_min": d0.date(), "category": CATEGORY[tour],
               "name_pattern": f"^{SS_NAME[tname]}, {EVENT[tour]}$",
               "locate_days": ";".join((d0 + pd.Timedelta(days=o)).strftime("%Y-%m-%d") for o in LOCATE_OFFSETS),
               "utid": None, "sid": None, "ss_tournament": None, "ss_season": None, "how": "to be located"}
        if edition in probe.index and pd.notna(probe.loc[edition, "utid"]):
            p = probe.loc[edition]
            row.update(utid=int(p["utid"]), sid=int(p["sid"]), ss_tournament=p["ss_tournament"],
                       ss_season=p["ss_season"], how=f"gap probe, 29 Sep 2026 ({p['located_by']})")
        elif edition in held:
            row.update(**held[edition], how="located by sofascore_tournaments.py from its day listings "
                                            "(listing held under data/raw/point_sources/sofascore_tournaments/seasons/)")
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true",
                        help="derive the list again from the map's current matches.parquet (a later build has filled "
                             "part of the gap, so the list would shrink); by default the frozen list is kept")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    frozen = OUT / "gap_matches.csv"
    if frozen.exists() and not args.refresh:
        gap = pd.read_csv(frozen)
        print(f"kept the frozen list {frozen.relative_to(PROJECT_ROOT).as_posix()} (--refresh derives it again)")
    else:
        gap = gap_matches(pd.read_parquet(MAP))
        gap.to_csv(frozen, index=False)
    ss = seasons(gap, pd.read_csv(PROBE))
    ss.astype({"utid": "Int64", "sid": "Int64"}).to_csv(OUT / "sofascore_seasons.csv", index=False)
    print(f"{len(gap)} gap matches in {len(ss)} editions; {ss['utid'].notna().sum()} seasons known, "
          f"{ss['utid'].isna().sum()} to locate")
    print(gap.groupby(["tname", "tour"])["year"].value_counts().unstack(fill_value=0).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())

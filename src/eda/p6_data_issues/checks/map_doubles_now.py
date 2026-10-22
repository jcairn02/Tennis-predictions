"""The data map's doubles from Tennis My Life's misdated editions, on the map as it stands (read-only).

A double: a match of a misdated edition that the map holds as Tennis My Life's copy at Tennis My Life's wrong date
(creator "tml", its tournament name and date) and again as another source's copy near the true start (any other
creator, the same two surnames, within -7 .. +14 days of the edition's true start). The editions and their rows are
the P6 study's (tml_misdates/misdated_matches.csv.gz, the "misdated" categories); whether Tennis My Life still dates
them so is the weekly check's (src/eda/tml_revisions/edition_dates.py).

Prints the doubles by season, by the twin's creator, and the best grain of each copy (what the map credits to each).
Run: ./python.sh src/eda/p6_data_issues/checks/map_doubles_now.py
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]


def surname(name) -> str:
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    w = [x for x in s.replace("-", " ").replace(".", " ").split() if len(x) > 1]
    return w[-1] if w else ""


def pair(a, b) -> str:
    return "|".join(sorted([surname(a), surname(b)]))


def main() -> int:
    mm = pd.read_csv(ROOT / "data/studies/p6_data_issues/tml_misdates/misdated_matches.csv.gz", low_memory=False,
                     usecols=["category", "tourney_id", "tourney_name", "tourney_date", "winner_name", "loser_name",
                              "true_start", "season"])
    mm = mm[mm["category"].astype(str).str.startswith("misdated")].copy()
    mm["d"] = pd.to_datetime(mm["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
    mm["true"] = pd.to_datetime(mm["true_start"], errors="coerce")
    mm["pair"] = [pair(a, b) for a, b in zip(mm["winner_name"], mm["loser_name"])]
    m = pd.read_parquet(ROOT / "data/studies/data_map/matches.parquet",
                        columns=["uid", "tour", "level", "draw", "year", "d", "name1", "name2", "tname", "creator", "best"])
    m = m[m["tour"].eq("M")].copy()
    m["d"] = pd.to_datetime(m["d"]).dt.normalize()
    m["pair"] = [pair(a, b) for a, b in zip(m["name1"], m["name2"])]
    tml = m[m["creator"].eq("tml")]
    other = m[~m["creator"].eq("tml")]
    a = mm.merge(tml[["uid", "tname", "d", "pair", "best"]], left_on=["tourney_name", "d", "pair"],
                 right_on=["tname", "d", "pair"], how="left")
    a = a.rename(columns={"uid": "tml_uid", "best": "tml_best"}).drop(columns=["tname"])
    b = a.merge(other[["uid", "pair", "d", "creator", "best"]].rename(columns={"d": "d_other"}), on="pair", how="left")
    near = (b["d_other"] - b["true"]).dt.days.between(-7, 14)
    b = b[near].sort_values("d_other").drop_duplicates(["tml_uid", "tourney_id", "pair"])
    dbl = b[b["tml_uid"].notna()]
    print(f"map built {pd.Timestamp((ROOT / 'data/studies/data_map/matches.parquet').stat().st_mtime, unit='s')} UTC; "
          f"misdated-edition rows {len(mm):,}; their Tennis My Life copy on the map at the wrong date "
          f"{int(a['tml_uid'].notna().sum()):,}; held twice {len(dbl):,}")
    print("by season:", dbl.groupby("season").size().to_dict())
    print("the twin's creator:", dbl["creator"].value_counts().to_dict())
    print("grain credited: the misdated copy", dbl["tml_best"].value_counts().to_dict(), "| the twin",
          dbl["best"].value_counts().to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""How much of the 2024-2026 main tour The Odds API's tennis history can reach.

The Odds API keys each tennis tournament separately, and each key's history starts on its own date
(https://the-odds-api.com/sports/tennis-odds.html, fetched 6 Oct 2026). A match counts as reachable
when its tennis-data.co.uk date is on or after its key's first snapshot. This is a ceiling for any
bookmaker on that route: it does not show that BetOnline priced the match.

Run: ./python.sh src/eda/betonline_lines/odds_api_coverage.py
Used by docs/research/betonline-lines/README.md.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3] / "data" / "dump" / "odds" / "tennis_data_couk"

# (tour, tennis-data Location, Tournament substring or None, key, first snapshot date)
KEYS = [
    ("atp", "Melbourne", None, "tennis_atp_aus_open_singles", "2021-02-06"),
    ("atp", "Paris", "French Open", "tennis_atp_french_open", "2020-09-24"),
    ("atp", "London", "Wimbledon", "tennis_atp_wimbledon", "2021-06-25"),
    ("atp", "New York", None, "tennis_atp_us_open", "2020-08-28"),
    ("atp", "Barcelona", None, "tennis_atp_barcelona_open", "2026-04-13"),
    ("atp", "Montreal", "Canadian", "tennis_atp_canadian_open", "2024-08-06"),
    ("atp", "Toronto", "Canadian", "tennis_atp_canadian_open", "2024-08-06"),
    ("atp", "Beijing", None, "tennis_atp_china_open", "2024-09-24"),
    ("atp", "Cincinnati", None, "tennis_atp_cincinnati_open", "2024-08-12"),
    ("atp", "Dubai", None, "tennis_atp_dubai", "2025-02-24"),
    ("atp", "Hamburg", None, "tennis_atp_hamburg_open", "2026-05-17"),
    ("atp", "Halle", None, "tennis_atp_halle_open", "2026-06-15"),
    ("atp", "Indian Wells", None, "tennis_atp_indian_wells", "2025-03-04"),
    ("atp", "Rome", None, "tennis_atp_italian_open", "2025-05-06"),
    ("atp", "Tokyo", None, "tennis_atp_japan_open", "2026-09-29"),
    ("atp", "Madrid", None, "tennis_atp_madrid_open", "2025-04-22"),
    ("atp", "Miami", None, "tennis_atp_miami_open", "2025-03-17"),
    ("atp", "Monte Carlo", None, "tennis_atp_monte_carlo_masters", "2025-04-06"),
    ("atp", "Munich", None, "tennis_atp_munich", "2026-04-13"),
    ("atp", "Paris", "Masters", "tennis_atp_paris_masters", "2024-10-28"),
    ("atp", "Doha", None, "tennis_atp_qatar_open", "2025-02-16"),
    ("atp", "Queens Club", None, "tennis_atp_queens_club_champ", "2026-06-15"),
    ("atp", "Shanghai", None, "tennis_atp_shanghai_masters", "2024-10-05"),
    ("atp", "Washington", None, "tennis_atp_washington_open", "2026-07-27"),
    ("wta", "Melbourne", None, "tennis_wta_aus_open_singles", "2021-02-06"),
    ("wta", "Bad Homburg", None, "tennis_wta_bad_homburg_open", "2026-06-21"),
    ("wta", "Montreal", "Canadian", "tennis_wta_canadian_open", "2024-08-06"),
    ("wta", "Toronto", "Canadian", "tennis_wta_canadian_open", "2024-08-06"),
    ("wta", "Charleston", None, "tennis_wta_charleston_open", "2026-03-30"),
    ("wta", "Beijing", None, "tennis_wta_china_open", "2024-09-24"),
    ("wta", "Cincinnati", None, "tennis_wta_cincinnati_open", "2024-08-12"),
    ("wta", "Dubai", None, "tennis_wta_dubai", "2025-02-16"),
    ("wta", "Paris", "French Open", "tennis_wta_french_open", "2020-09-24"),
    ("wta", "Berlin", None, "tennis_wta_german_open", "2026-06-15"),
    ("wta", "Guadalajara", None, "tennis_wta_guadalajara_open", "2026-09-13"),
    ("wta", "Indian Wells", None, "tennis_wta_indian_wells", "2025-03-04"),
    ("wta", "Rome", None, "tennis_wta_italian_open", "2025-05-06"),
    ("wta", "Madrid", None, "tennis_wta_madrid_open", "2025-04-22"),
    ("wta", "Miami", None, "tennis_wta_miami_open", "2025-03-17"),
    ("wta", "Monterrey", None, "tennis_wta_monterrey_open", "2026-08-23"),
    ("wta", "Doha", None, "tennis_wta_qatar_open", "2025-02-10"),
    ("wta", "Singapore", None, "tennis_wta_singapore_open", "2026-09-20"),
    ("wta", "Queens Club", None, "tennis_wta_queens_club_champ", "2026-06-08"),
    ("wta", "Strasbourg", None, "tennis_wta_strasbourg", "2026-05-17"),
    ("wta", "Stuttgart", None, "tennis_wta_stuttgart_open", "2026-04-13"),
    ("wta", "New York", None, "tennis_wta_us_open", "2020-08-28"),
    ("wta", "Washington", None, "tennis_wta_washington_open", "2026-07-27"),
    ("wta", "London", "Wimbledon", "tennis_wta_wimbledon", "2021-06-25"),
    ("wta", "Wuhan", None, "tennis_wta_wuhan_open", "2024-10-06"),
]


def load_matches() -> pd.DataFrame:
    frames = []
    for path in sorted(ROOT.glob("*/*/202[4-6].parquet")):
        d = pd.read_parquet(path, columns=["Location", "Tournament", "Date"])
        d["tour"], d["year"] = path.parts[-3], int(path.stem)
        frames.append(d)
    m = pd.concat(frames, ignore_index=True)
    m["Date"] = pd.to_datetime(m["Date"])
    return m


def mark_covered(m: pd.DataFrame) -> pd.DataFrame:
    m = m.assign(key=None, covered=False)
    for tour, loc, name_part, key, start in KEYS:
        sel = (m["tour"] == tour) & (m["Location"] == loc)
        if name_part:
            sel &= m["Tournament"].str.contains(name_part, case=False, regex=False)
        m.loc[sel, "key"] = key
        m.loc[sel & (m["Date"] >= pd.Timestamp(start)), "covered"] = True
    return m


def main() -> None:
    m = mark_covered(load_matches())
    by_year = m.groupby(["year", "tour"]).agg(matches=("covered", "size"), reachable=("covered", "sum"))
    both = m.groupby("year").agg(matches=("covered", "size"), reachable=("covered", "sum"))
    for table in (by_year, both):
        table["share"] = (table["reachable"] / table["matches"]).map("{:.0%}".format)
        print(table.to_string(), end="\n\n")
    print(f"2024-2026: {int(m['covered'].sum())} of {len(m)} matches ({m['covered'].mean():.0%})")
    key_days = m[m["covered"]].groupby(["key", "year"])["Date"].nunique().sum()
    print(f"key-days with a reachable match: {key_days}")
    print(f"last match date in the dump: {m['Date'].max().date()}")


if __name__ == "__main__":
    main()

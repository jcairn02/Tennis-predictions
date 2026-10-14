"""Wimbledon's IBM SlamTracker feeds, 2019 and 2021-2026: the Site settings for slamtracker.py.

Hosts (observed 24 Sep 2026): 2019 and 2021-2025 are served only by the archive host 2025.wimbledon.com, whose
robots.txt disallows every robot (the www host answers HTTP 403 for those years; 2018 and 2020 are not served).
2026 is on www.wimbledon.com, where the MS and LS draw files redirect automated clients to /robots.txt: they are
listed as blocked and never requested, and those two events are listed from the completed-match days instead.

Extras: IBM likelihood-to-win after every point (singles main draws, 2025 on the archive host, 2026 on www; it
lags the point, so join it on point_number, not time) and TennisViz per-set metrics (singles main draws, 2024-2025,
archive host).

Usage:
    ./python.sh -m src.ingest.point_sources.wimbledon --years 2025 --limit 5     # pilot
    ./python.sh -m src.ingest.point_sources.wimbledon --years 2019,2021,2022,2023,2024,2025
    ./python.sh -m src.ingest.point_sources.wimbledon --stage-only
"""
from __future__ import annotations

import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import slamtracker as T

ARCHIVE = "https://2025.wimbledon.com"
WWW = "https://www.wimbledon.com"
SINGLES_MAIN = frozenset({"MS", "LS"})
ROBOTS_2026 = "302 to /robots.txt for automated clients (research pass, 24 Sep 2026 15:44 UTC); not requested"

WIMBLEDON = T.Site(
    key="wimbledon",
    source="wimbledon",
    slam="wimbledon",
    lang="en_GB",
    hosts={2019: ARCHIVE, 2021: ARCHIVE, 2022: ARCHIVE, 2023: ARCHIVE, 2024: ARCHIVE, 2025: ARCHIVE, 2026: WWW},
    events=("MS", "LS", "QS", "RS", "MD", "LD"),
    feeds=(
        T.history_feed(),
        T.stats_feed(),
        T.Feed("livel2w", "/clouddata/livel2w/{year}/{id}C.json", years=frozenset({2025, 2026}), events=SINGLES_MAIN),
        T.Feed("tz", "/clouddata/tz/{year}/{id}.json", years=frozenset({2024, 2025}), events=SINGLES_MAIN),
    ),
    blocked={"draws/2026/MS": ROBOTS_2026, "draws/2026/LS": ROBOTS_2026},
    day_lists=frozenset({2026}),
)
SITE = WIMBLEDON  # the name src/eda/official_point_feeds/slamtracker_checks.py looks for

if __name__ == "__main__":
    sys.exit(T.main(WIMBLEDON))

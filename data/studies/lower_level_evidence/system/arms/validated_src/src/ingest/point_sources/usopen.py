"""The US Open's IBM SlamTracker feeds, 2022-2026: the Site settings for slamtracker.py.

Host (observed 24 Sep 2026): www.usopen.org serves 2022-2026; 2019-2021 answer HTTP 404 there and on
2024.usopen.org, the only year host that resolves (it mirrors 2024 and is not used here). The site resets the
connection of plain clients; curl_cffi's chrome profile gets the files. A missing feed file answers HTTP 404; a
missing /clouddata/ file answers HTTP 302 to https://www.usopen.org/notfound. Both are recorded as absent.

Feeds for all six events (MS, WS, MQ, WQ, MD, WD), every match: the draws, point histories and match statistics.
A match whose draw entry is not "H" (qualifying on courts without full scoring, walkovers) answers a history with
only the two marker rows; so do 43 "H" qualifying matches of 2023 and 2025, and eight 2025 qualifying histories
number their points without giving most of them a winner (docs/studies/official_point_feeds/README.md).

The other feeds, requested for the draw levels below. Coverage found by the collection of 24-25 Sep 2026:
    distance      slamtracker/distance/<id>.dist.json: metres run by each player, cumulative per set ("H"). Main-draw
                  singles in every year; qualifying where its courts had tracking (2022 few, 2023 nearly all, 2024
                  none, 2025-2026 most); HTTP 404 for doubles
    livel2w       IBM likelihood-to-win after every point ("H", 2025-2026). Singles main draws, and about half of 2025
                  qualifying; it lags the point, so join it on point_number, not time. The 2025 main-draw files are
                  replays written in July 2026
    limbtracking  serve biomechanics from limb tracking ("H", 2026). Singles main draw
    keymoments    IBM key moments ("H", 2026). Singles main draw
    prematch_l2w  pre-match likelihood to win (every level, 2025-2026). Singles main draws and most of 2025 qualifying
Every extra is asked for every event: the engine abandons a feed for a year and event after five absences in a
row, so coverage is measured, not assumed, at a cost of a few requests per empty group. Where a feed is sporadic
the rest of the group has to be asked with --streak 0 (--years, --events and --feeds to select it).

Out of scope: 3d.usopen.org (SlamTracker 3D), which needs a Firebase sign-in; the mixed doubles draw.

Usage:
    ./python.sh -m src.ingest.point_sources.usopen --years 2026 --limit 3      # pilot
    ./python.sh -m src.ingest.point_sources.usopen --max-requests 11000
    ./python.sh -m src.ingest.point_sources.usopen --stage-only
    ./python.sh src/eda/official_point_feeds/slamtracker_checks.py --site usopen
"""
from __future__ import annotations

import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import slamtracker as T

WWW = "https://www.usopen.org"
FULL = frozenset({"H"})

SITE = T.Site(
    key="usopen",
    source="usopen",
    slam="usopen",
    lang="en_US",
    hosts={2022: WWW, 2023: WWW, 2024: WWW, 2025: WWW, 2026: WWW},
    events=("MS", "WS", "MQ", "WQ", "MD", "WD"),
    feeds=(
        T.history_feed(),
        T.stats_feed(),
        T.Feed("distance", T.SCORES + "/slamtracker/distance/{id}.dist.json", levels=FULL),
        T.Feed("livel2w", "/clouddata/livel2w/{year}/{id}C.json", years=frozenset({2025, 2026}), levels=FULL),
        T.Feed("limbtracking", "/clouddata/limbtracking/{year}/match/{id}.json", years=frozenset({2026}), levels=FULL),
        T.Feed("keymoments", "/clouddata/keymoments/key_moment/{year}/{id}.json", years=frozenset({2026}), levels=FULL),
        T.Feed("prematch_l2w", "/clouddata/likelihood-to-win/{year}/{id}.json", years=frozenset({2025, 2026})),
    ),
    impersonate="chrome",
)

if __name__ == "__main__":
    sys.exit(T.main(SITE))

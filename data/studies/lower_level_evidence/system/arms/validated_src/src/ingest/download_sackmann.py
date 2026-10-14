"""Download Jeff Sackmann's open tennis results CSVs from GitHub.

Sources (license CC BY-NC-SA 4.0 — attribution, non-commercial):
    https://github.com/JeffSackmann/tennis_atp
    https://github.com/JeffSackmann/tennis_wta

Per tour-year this fetches ``{tour}_matches_{year}.csv`` (main-tour matches:
results, surface, round, rank/points, and serve stats like aces, double faults,
serve points won — the raw material for serve/return features).

Usage:
    ./python.sh src/ingest/download_sackmann.py --tour atp --start 2015 --end 2026
    ./python.sh src/ingest/download_sackmann.py --tour both --start 1990 --end 2026 --players
    ./python.sh src/ingest/download_sackmann.py --tour atp --start 2020 --end 2026 --qual

Failure policy: every failed/suspect download is collected and reported, and the
script exits non-zero if anything failed. No silent skips.
"""

import argparse
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_BASE = "https://raw.githubusercontent.com/JeffSackmann/tennis_{tour}/master/{filename}"

# Qualifying / lower-tier match files use different names per tour.
QUAL_PATTERN = {
    "atp": "atp_matches_qual_chall_{year}.csv",   # qualifying + Challenger tour
    "wta": "wta_matches_qual_itf_{year}.csv",     # qualifying + ITF circuit
}

REQUEST_TIMEOUT = 30
RETRIES = 2
RETRY_SLEEP = 2


def fetch(url: str) -> bytes:
    """GET with small retry. Raises requests.HTTPError on final failure."""
    last_err = None
    for attempt in range(RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as err:  # includes HTTPError, timeouts
            last_err = err
            if attempt < RETRIES:
                time.sleep(RETRY_SLEEP)
    raise last_err


def looks_like_match_csv(content: bytes) -> bool:
    """Guard against HTML error pages saved as .csv."""
    head = content[:200].decode("utf-8", errors="replace")
    return "tourney_id" in head


def download_file(filename: str, tour: str, dest_dir: Path, force: bool,
                  expect_match_header: bool, failures: list) -> None:
    dest = dest_dir / filename
    if dest.exists() and not force:
        print(f"SKIP (exists): {dest}")
        return
    url = RAW_BASE.format(tour=tour, filename=filename)
    try:
        content = fetch(url)
    except requests.RequestException as err:
        failures.append(f"{url} -> {err}")
        print(f"FAIL: {url} ({err})")
        return
    if expect_match_header and not looks_like_match_csv(content):
        failures.append(f"{url} -> content does not look like a Sackmann match CSV")
        print(f"FAIL (bad content): {url}")
        return
    dest.write_bytes(content)
    print(f"OK:   {dest} ({len(content):,} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tour", choices=["atp", "wta", "both"], required=True)
    parser.add_argument("--start", type=int, required=True, help="first season year")
    parser.add_argument("--end", type=int, required=True, help="last season year (inclusive)")
    parser.add_argument("--players", action="store_true", help="also fetch {tour}_players.csv")
    parser.add_argument("--qual", action="store_true",
                        help="also fetch qualifying/lower-tier match files per year")
    parser.add_argument("--dest", type=Path, default=None,
                        help="override destination root (default data/raw/sackmann/)")
    parser.add_argument("--force", action="store_true", help="re-download existing files")
    args = parser.parse_args()

    if args.start > args.end:
        parser.error(f"--start {args.start} > --end {args.end}")

    tours = ["atp", "wta"] if args.tour == "both" else [args.tour]
    failures: list = []

    for tour in tours:
        dest_dir = (args.dest or PROJECT_ROOT / "data" / "raw" / "sackmann") / tour
        dest_dir.mkdir(parents=True, exist_ok=True)

        for year in range(args.start, args.end + 1):
            download_file(f"{tour}_matches_{year}.csv", tour, dest_dir, args.force,
                          expect_match_header=True, failures=failures)
            if args.qual:
                download_file(QUAL_PATTERN[tour].format(year=year), tour, dest_dir,
                              args.force, expect_match_header=True, failures=failures)
        if args.players:
            download_file(f"{tour}_players.csv", tour, dest_dir, args.force,
                          expect_match_header=False, failures=failures)

    if failures:
        print(f"\n{len(failures)} download(s) FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        print("Note: the current season's file may not exist yet in Sackmann's repo "
              "(updates can lag weeks during the season).", file=sys.stderr)
        return 1
    print("\nAll downloads OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

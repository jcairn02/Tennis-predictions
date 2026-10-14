"""Download historical results + closing odds workbooks from tennis-data.co.uk.

Each tour-year is a single Excel workbook (newer years .xlsx, older .xls) with
one row per completed match: tournament, date, players, ranks, score, and
decimal odds columns (B365*, PS* = Pinnacle, Max*, Avg*). Men's files live at
``/{year}/{year}.x...``, women's at ``/{year}w/{year}.x...``.

Usage:
    ./python.sh src/ingest/download_tennis_data_couk.py --tour atp --start 2010 --end 2026
    ./python.sh src/ingest/download_tennis_data_couk.py --tour both --start 2005 --end 2026

For each year, candidate URLs are tried in order (xlsx, then xls, then zip);
which one succeeded is printed. Anything that fails entirely is reported and the
script exits non-zero. No silent skips.
"""

import argparse
import io
import sys
import time
import zipfile
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]

XLSX_MAGIC = b"PK\x03\x04"          # xlsx is a zip container
XLS_MAGIC = b"\xd0\xcf\x11\xe0"     # legacy OLE compound document

REQUEST_TIMEOUT = 30
RETRIES = 1
RETRY_SLEEP = 2


def candidates(year: int, tour: str):
    seg = f"{year}w" if tour == "wta" else f"{year}"
    for scheme in ("http", "https"):  # site is plain http; https tried as backup
        for ext in ("xlsx", "xls", "zip"):
            yield f"{scheme}://www.tennis-data.co.uk/{seg}/{year}.{ext}", ext


def fetch(url: str) -> bytes:
    last_err = None
    for attempt in range(RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as err:
            last_err = err
            if attempt < RETRIES:
                time.sleep(RETRY_SLEEP)
    raise last_err


def plausible_workbook(content: bytes) -> bool:
    return content[:4] in (XLSX_MAGIC, XLS_MAGIC) and len(content) > 10_000


def save_year(year: int, tour: str, dest_dir: Path, force: bool, failures: list) -> None:
    existing = list(dest_dir.glob(f"{year}.*"))
    if existing and not force:
        print(f"SKIP (exists): {existing[0]}")
        return

    errors = []
    for url, ext in candidates(year, tour):
        try:
            content = fetch(url)
        except requests.RequestException as err:
            errors.append(f"{url} -> {err}")
            continue

        if ext == "zip":
            try:
                zf = zipfile.ZipFile(io.BytesIO(content))
            except zipfile.BadZipFile:
                errors.append(f"{url} -> not a zip")
                continue
            members = [m for m in zf.namelist() if m.lower().endswith((".xls", ".xlsx", ".csv"))]
            if not members:
                errors.append(f"{url} -> zip has no workbook/csv members: {zf.namelist()}")
                continue
            member = members[0]
            data = zf.read(member)
            out = dest_dir / f"{year}{Path(member).suffix.lower()}"
            out.write_bytes(data)
            print(f"OK:   {out} (from zip {url}, member {member}, {len(data):,} bytes)")
            return

        if not plausible_workbook(content):
            errors.append(f"{url} -> response is not an Excel workbook "
                          f"(magic={content[:4]!r}, {len(content)} bytes)")
            continue
        out = dest_dir / f"{year}.{ext}"
        out.write_bytes(content)
        print(f"OK:   {out} (from {url}, {len(content):,} bytes)")
        return

    failures.append(f"{tour} {year}: all candidates failed:\n    " + "\n    ".join(errors))
    print(f"FAIL: {tour} {year} (all candidate URLs failed)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tour", choices=["atp", "wta", "both"], required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--dest", type=Path, default=None,
                        help="override destination root (default data/raw/tennis_data_couk/)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.start > args.end:
        parser.error(f"--start {args.start} > --end {args.end}")

    tours = ["atp", "wta"] if args.tour == "both" else [args.tour]
    failures: list = []
    for tour in tours:
        dest_dir = (args.dest or PROJECT_ROOT / "data" / "raw" / "tennis_data_couk") / tour
        dest_dir.mkdir(parents=True, exist_ok=True)
        for year in range(args.start, args.end + 1):
            save_year(year, tour, dest_dir, args.force, failures)

    if failures:
        print(f"\n{len(failures)} year(s) FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print("\nAll downloads OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Download every tennis-data.co.uk season workbook again, beside the shared dump, and measure what changed.

Why beside it. The shared dump (data/dump/odds/tennis_data_couk/) feeds Stage 1's odds link (stage1_odds.py). On 9 Oct
2026 other sessions' candidate builds were running that link through junctions to data/dump/, and restaging the dump
in place would have changed their inputs mid-run. So this script keeps its own copies, with receipts, under
data/raw/indoor_fill/tennis_data_couk/, and compares each workbook with the one the dump was staged from:
    unchanged      the same bytes (SHA-256) as the dump's source
    appended       every row of the dump's source unchanged and in place, and rows added after them: restaging keeps
                   each old row at its position in its partition, so Stage 1's links (td_file, td_row) stay valid
    same rows      other bytes, the same rows
    changed        some of the dump's rows differ or moved: Stage 1 must be rebuilt after restaging
    not in dump    a season the dump does not hold
The routine refresh (src/ingest/refresh_odds.py, its tennis_data step; or the adapter with --refresh) restages the dump;
run it when no build reads the dump.

Acquisition as the adapter does it (src/ingest/public_dump/tennis_data_couk.py, route "live"): the listing page
data.php names each season's workbook under the relaunched site's directory; a season it does not link is tried at its
old path. About 2.5 s between requests plus up to 1 s of jitter, a receipt for every answer, and a stop on a block
(HTTP 401, 403 or 429), as the scraping decision asks (docs/decisions/2026-10-08-scraping-approved.md).

Writes, in data/studies/indoor_fill/:
    snapshot.json       per tour and season: the receipt, the comparison, and the Court values of rows the dump lacks
    snapshot_rows.csv   every row the dump lacks or holds differently (tour, season, row, event, date, Court)
Run: ./python.sh -I src/eda/indoor_fill/snapshot.py [--fetch-only | --compare-only]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump import tennis_data_couk as TD  # noqa: E402

OUT = ROOT / "data" / "studies" / "indoor_fill"
RAW = ROOT / "data" / "raw" / "indoor_fill"
DUMP = C.dump_path("odds", TD.SOURCE)
LAST_YEAR = 2026
MIN_INTERVAL, JITTER = 2.5, 1.0
BLOCK_STATUS = (401, 403, 429)
ROW_COLS = ["Location", "Tournament", "Date", "Court", "Surface", "Round", "Winner", "Loser"]


class Stopped(RuntimeError):
    pass


class Pace:
    """At least MIN_INTERVAL seconds, plus jitter, between the starts of two requests."""

    def __init__(self) -> None:
        self.last = 0.0

    def wait(self) -> None:
        gap = MIN_INTERVAL + random.uniform(0.0, JITTER) - (time.monotonic() - self.last)
        if gap > 0:
            time.sleep(gap)
        self.last = time.monotonic()


def receipts() -> C.Receipts:
    return C.Receipts(TD.SOURCE, root=RAW)


def fetch() -> list[dict]:
    """The listing pages, then every season's workbook (ATP 2000-, WTA 2007-). Raises Stopped on a block."""
    rec, pace, out = receipts(), Pace(), []
    for page, filename in TD.INDEX_PAGES.items():
        pace.wait()
        r = C.download(f"{TD.SITE}/{page}", RAW / TD.SOURCE / "docs" / filename, rec, name=f"docs/{page}",
                       refresh=True, validator=C.not_html if page.endswith(".txt") else None)
        if r.get("status") in BLOCK_STATUS:
            raise Stopped(f"{page}: HTTP {r['status']}")
    listing = TD.read_listing(rec)
    C.log(f"[indoor_fill] {len(listing)} workbook links on {TD.LISTING_PAGE}")
    for tour in ("atp", "wta"):
        for year in range(TD.FIRST_YEAR[tour], LAST_YEAR + 1):
            url = listing.get((tour, year)) or TD.legacy_url(tour, year)
            dest = RAW / TD.SOURCE / tour / f"{year}{Path(urlparse(url).path).suffix.lower()}"
            pace.wait()
            r = C.download(url, dest, rec, name=f"{tour}/{year}", refresh=True, validator=C.workbook_magic,
                           keep_superseded=True, extra={"route": "listed" if (tour, year) in listing else "old_path"})
            C.log(f"[indoor_fill] {tour} {year}: " + (f"ERROR {r['error']}" if r.get("error") else
                                                     f"{r['bytes']:,} bytes, last modified {r.get('last_modified')}"))
            if r.get("status") in BLOCK_STATUS:
                raise Stopped(f"{tour} {year}: HTTP {r['status']}")
            out.append(r)
    return out


def dump_rows(tour: str, year: int) -> tuple[pd.DataFrame | None, list[str]]:
    """The dump's rows of one season, in workbook order (_row), and the SHA-256s of the workbooks they came from."""
    parts = sorted(DUMP.glob(f"{tour}/*/{year}.parquet"))
    if not parts:
        return None, []
    d = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    d["_row"] = pd.to_numeric(d["_row"])
    return d.sort_values("_row").reset_index(drop=True), sorted(d["_sha256"].dropna().unique().tolist())


def workbook_rows(path: Path) -> pd.DataFrame:
    """The workbook's rows as the adapter stages them: the header's columns, values as text, row numbers from 1."""
    _, header, rows, _ = C.read_workbook(path)
    cols = C.dedupe_header(header)
    body = [[None if v is None else str(v) for v in (r[:len(cols)] + [None] * (len(cols) - len(r)))] for r in rows]
    d = pd.DataFrame(body, columns=cols, dtype=object)
    d["_row"] = range(1, len(d) + 1)
    return d


def court_counts(d: pd.DataFrame) -> dict:
    return d["Court"].fillna("<blank>").astype(str).value_counts().to_dict() if "Court" in d.columns else {}


def compare(tour: str, year: int, receipt: dict) -> tuple[dict, pd.DataFrame]:
    """One season: the downloaded workbook against the dump's source."""
    rec = {"tour": tour, "season": year, "url": receipt.get("url"), "retrieved_at": receipt.get("retrieved_at"),
           "last_modified": receipt.get("last_modified"), "sha256": receipt.get("sha256")}
    if receipt.get("error"):
        return {**rec, "status": "not downloaded", "error": receipt["error"]}, pd.DataFrame()
    new = workbook_rows(ROOT / receipt["dest"])
    old, shas = dump_rows(tour, year)
    rec.update(rows_new=int(len(new)), court_new=court_counts(new))
    if old is None:
        extra = new.assign(tour=tour, season=year, why="season not in the dump")
        return {**rec, "status": "not in dump"}, extra
    rec.update(rows_dump=int(len(old)), dump_source_sha256=shas, court_dump=court_counts(old))
    if shas == [receipt.get("sha256")]:
        return {**rec, "status": "unchanged"}, pd.DataFrame()
    cols = [c for c in new.columns if c != "_row"]
    old_cols = [c for c in old.columns if not c.startswith("_")]
    if cols != old_cols:
        rec.update(status="changed", header_differs=True, header_new=cols, header_dump=old_cols)
        return rec, new.assign(tour=tour, season=year, why="header differs")
    k = min(len(old), len(new))
    a, b = old[cols].iloc[:k].fillna("<NA>").to_numpy(), new[cols].iloc[:k].fillna("<NA>").to_numpy()
    differs = (a != b).any(axis=1)
    court = cols.index("Court") if "Court" in cols else None
    rec.update(rows_differing=int(differs.sum()),
               court_differing=int((a[:, court] != b[:, court]).sum()) if court is not None else None,
               rows_removed=int(max(len(old) - len(new), 0)), rows_appended=int(max(len(new) - len(old), 0)))
    if differs.any() or len(new) < len(old):
        status = "changed"
    else:
        status = "appended" if len(new) > len(old) else "same rows"
    parts = [new.iloc[:k][differs].assign(why="row differs from the dump's"),
             new.iloc[k:].assign(why="row appended")]
    extra = pd.concat(parts, ignore_index=True).assign(tour=tour, season=year)
    if len(extra):
        rec["appended_events"] = (extra[extra["why"].eq("row appended")]
                                  .groupby(["Location", "Tournament"], dropna=False)
                                  .agg(rows=("_row", "size"), first=("Date", "min"), last=("Date", "max"),
                                       court=("Court", lambda s: "/".join(sorted(s.dropna().astype(str).unique()))))
                                  .reset_index().to_dict("records"))
    return {**rec, "status": status}, extra


def compare_all() -> dict:
    rec = receipts()
    seasons, rows = [], []
    for tour in ("atp", "wta"):
        for year in range(TD.FIRST_YEAR[tour], LAST_YEAR + 1):
            r = rec.get(f"{tour}/{year}")
            if r is None:
                continue
            s, extra = compare(tour, year, r)
            seasons.append(s)
            if len(extra):
                rows.append(extra)
    table = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    OUT.mkdir(parents=True, exist_ok=True)
    keep = ["tour", "season", "_row", "why"] + [c for c in ROW_COLS + ["Series", "Tier"] if c in table.columns]
    (table[keep] if len(table) else table).to_csv(OUT / "snapshot_rows.csv", index=False)
    by_status = pd.Series([s["status"] for s in seasons]).value_counts().to_dict()
    summary = {"generated_at": C.utc_now_iso(), "raw_folder": C.rel(RAW / TD.SOURCE), "dump_modified": False,
               "status_counts": by_status, "seasons": seasons,
               "stage1_links_valid_after_restaging": all(s["status"] in ("unchanged", "appended", "same rows",
                                                                         "not downloaded", "not in dump")
                                                         for s in seasons)}
    (OUT / "snapshot.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    C.log(f"[indoor_fill] compared {len(seasons)} seasons: {by_status}; Stage 1's links valid after restaging: "
          f"{summary['stage1_links_valid_after_restaging']}")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fetch-only", action="store_true")
    g.add_argument("--compare-only", action="store_true")
    a = ap.parse_args()
    if not a.compare_only:
        try:
            fetch()
        except Stopped as stop:
            C.log(f"[indoor_fill] STOPPED on a block: {stop}")
            return 2
    if not a.fetch_only:
        compare_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())

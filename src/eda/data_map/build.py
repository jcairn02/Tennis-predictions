"""Build the data map: data/data_map.html, from data/data_map.yaml and the measured coverage.

Steps:
1. Read and check the catalog (data/data_map.yaml): ids unique, statuses and grains known, every
   `measured_as` id one the measurement produces, every linked file present.
2. Measure coverage (src/eda/data_map/measure.py), or reuse the last measurement (--no-measure).
3. Size every dataset's folders, and list folders under data/raw/ and data/dump/ that no catalog
   entry claims, so new data cannot slip in unmapped.
4. Read live progress of the downloads marked `downloading` from the files they are writing, and count
   the encrypted ATP Stats Centre files by season and level from their names (nothing is decrypted).
5. Count the market data (closing odds, BetOnline lines, Polymarket prices and trades) from the staged
   tables.
6. Write the page: the template with all of the above embedded as JSON, so the file opens on its
   own in any browser. The page sets what is held against the catalog's `universe` of outside sources.

Usage:
    ./python.sh src/eda/data_map/build.py                    # measure, then build (about a minute)
    ./python.sh src/eda/data_map/build.py --no-measure       # rebuild the page from the last measurement
    ./python.sh src/eda/data_map/build.py --fragment <path>  # also write the page without <html>/<head>

Writes data/data_map.html (tracked) and data/studies/data_map/build_report.json (tracked).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map import measure as M  # noqa: E402

DATA = PROJECT_ROOT / "data"
CATALOG = DATA / "data_map.yaml"
TEMPLATE = Path(__file__).with_name("template.html")
PAGE = DATA / "data_map.html"
REPORT = M.OUT / "build_report.json"

STATUSES = {"on_disk", "downloading", "assumed"}
GRAINS = {"shot", "point", "stats", "result", "market", "reference"}
MEASURED_IDS = {"tml", "sackmann", "wta_lists", "wimbledon", "usopen", "ausopen", "ausopen_wayback", "slam_draws",
                "api_tennis", "tdi", "tdi_listing", "slam_pbp", "infosys", "court_vision", "mcp", "ta_charts",
                "sofascore", "sofascore_editions", "sirgenkii", "tennislive", "lta_sample", "wta_events",
                "wta_box", "slam_ball_tracking", "sofascore_tournaments", "infosys_slams", "infosys_atp", "marcosjn2",
                "wta_site",
                "itf_live", "tennislive_listed", "tennislive_samples", "tennislive_gaps", "flashscore_points"}


# --------------------------------------------------------------------------------------------
# Catalog

def load_catalog() -> dict:
    return yaml.safe_load(CATALOG.read_text(encoding="utf-8"))


def _paths(value) -> list[str]:
    if not value:
        return []
    items = value if isinstance(value, list) else [value]
    out = []
    for item in items:
        out += [p.strip() for p in str(item).split(",") if p.strip()]
    return out


def _doc_path(ref: str) -> Path:
    return PROJECT_ROOT / ref.split("#")[0].split(" (")[0].strip()


def check_catalog(cat: dict) -> list[str]:
    """Problems with the catalog; an empty list means it is sound."""
    problems = []
    ids = [d.get("id") for d in cat.get("datasets") or []]
    for dup in {i for i in ids if ids.count(i) > 1}:
        problems.append(f"dataset id used twice: {dup}")
    measured = []
    for ds in cat.get("datasets") or []:
        name = ds.get("id", "?")
        for key in ("id", "name", "what", "grain", "tours", "years", "status"):
            if not ds.get(key):
                problems.append(f"{name}: missing '{key}'")
        if ds.get("status") not in STATUSES:
            problems.append(f"{name}: unknown status {ds.get('status')!r}")
        if ds.get("grain") not in GRAINS:
            problems.append(f"{name}: unknown grain {ds.get('grain')!r}")
        for item in ds.get("measured_as") or []:
            mid = item["id"] if isinstance(item, dict) else item
            measured.append(mid)
            if mid not in MEASURED_IDS:
                problems.append(f"{name}: measured_as '{mid}' is not a source the measurement produces")
            if isinstance(item, dict) and item.get("status") not in STATUSES:
                problems.append(f"{name}: measured_as '{mid}' has unknown status {item.get('status')!r}")
        for batch in ds.get("batches") or []:
            if batch.get("status") not in STATUSES:
                problems.append(f"{name}: batch {batch.get('id')} has unknown status {batch.get('status')!r}")
        for key in ("report", "decision", "evidence"):
            for ref in _paths(ds.get(key)):
                if not _doc_path(ref).exists():
                    problems.append(f"{name}: {key} {ref} does not exist")
        for ref in _paths(ds.get("adapter")):
            if not _doc_path(ref).exists():
                problems.append(f"{name}: adapter {ref} does not exist")
    for mid in sorted(MEASURED_IDS - set(measured)):
        problems.append(f"no dataset claims the measured source '{mid}'")
    methods = {m.get("id") for m in cat.get("methods") or []}
    for ds in cat.get("datasets") or []:
        if ds.get("how") not in methods:
            problems.append(f"{ds.get('id', '?')}: 'how' {ds.get('how')!r} is not one of the catalog's methods")
    for gap in cat.get("gaps") or []:
        for ref in _paths(gap.get("lead")):
            if not _doc_path(ref).exists():
                problems.append(f"gap {gap.get('id')}: lead {ref} does not exist")
    uni = cat.get("universe") or {}
    routes = {r.get("id") for r in uni.get("routes") or []}
    for src in uni.get("sources") or []:
        name = f"universe source {src.get('id')}"
        if src.get("route") not in routes:
            problems.append(f"{name}: unknown route {src.get('route')!r}")
        sel = src.get("select") or {}
        if not (sel.get("tours") and sel.get("levels") and sel.get("years")):
            problems.append(f"{name}: select needs tours, levels and years")
        for grain in list((src.get("shares") or {}).keys()) + list((src.get("counts_by_year") or {}).keys()):
            if grain not in ("shot", "point", "stats", "result"):
                problems.append(f"{name}: unknown grain {grain!r}")
        for ref in _paths(src.get("lead")):
            if not _doc_path(ref).exists():
                problems.append(f"{name}: lead {ref} does not exist")
    return problems


# --------------------------------------------------------------------------------------------
# Folders

def folder_size(path: Path) -> tuple[int, int]:
    """(bytes, files) under ``path``; a file path counts itself."""
    if path.is_file():
        return path.stat().st_size, 1
    total = files = 0
    stack = [path]
    while stack:
        try:
            entries = list(os.scandir(stack.pop()))
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                stack.append(entry.path)
            elif entry.is_file(follow_symlinks=False):
                files += 1
                try:
                    total += entry.stat(follow_symlinks=False).st_size
                except OSError:
                    pass
    return total, files


def folder_units() -> list[Path]:
    """The folders every catalog entry must account for: data/raw/<group>/<source> (one level deeper
    inside the Hugging Face dump) and data/dump/<branch>/<source>."""
    units = []
    raw = DATA / "raw"
    for group in sorted(p for p in raw.iterdir() if p.is_dir()):
        if group.name in ("sackmann", "tennis_data_couk"):
            units.append(group)
            continue
        for source in sorted(p for p in group.iterdir() if p.is_dir()):
            if source.name == "atp_pipeline_handoff":
                units += sorted(p for p in source.iterdir() if p.is_dir())
            else:
                units.append(source)
    dump = DATA / "dump"
    for branch in sorted(p for p in dump.iterdir() if p.is_dir()):
        units += sorted(p for p in branch.iterdir() if p.is_dir())
    return units


def sizes_and_unmapped(cat: dict) -> tuple[dict, list[dict], list[str]]:
    claimed: dict[str, str] = {}
    per_dataset = {}
    for ds in cat.get("datasets") or []:
        entry = {}
        for key in ("raw", "staged"):
            size = files = 0
            for ref in _paths(ds.get(key)):
                path = PROJECT_ROOT / ref
                claimed[str(path.resolve()).rstrip("\\/").lower()] = ds["id"]
                if path.exists():
                    b, f = folder_size(path)
                    size, files = size + b, files + f
            entry[f"{key}_bytes"], entry[f"{key}_files"] = size, files
        per_dataset[ds["id"]] = entry
    unmapped, tree = [], []
    for unit in folder_units():
        key = str(unit.resolve()).lower()
        owner = next((ds for path, ds in claimed.items() if key == path or key.startswith(path + os.sep)
                      or path.startswith(key + os.sep)), None)
        b, f = folder_size(unit)
        rel = unit.relative_to(PROJECT_ROOT).as_posix()
        tree.append({"path": rel + "/", "bytes": b, "files": f, "dataset": owner})
        if owner is None:
            unmapped.append(rel + "/")
    return per_dataset, tree, unmapped


def stage_sizes() -> list[dict]:
    out = []
    for name, rel in (("raw", "data/raw"), ("staged", "data/dump"), ("evidence", "data/studies"),
                      ("bets", "data/betting_history")):
        b, f = folder_size(PROJECT_ROOT / rel)
        out.append({"stage": name, "path": rel + "/", "bytes": b, "files": f})
    studies = []
    for p in sorted((DATA / "studies").iterdir()):
        if p.is_dir():
            b, f = folder_size(p)
            studies.append({"path": p.relative_to(PROJECT_ROOT).as_posix() + "/", "bytes": b, "files": f})
    return out + [{"stage": "studies", "folders": studies}]


# --------------------------------------------------------------------------------------------
# Live progress of running downloads, from the files they write

def _mtime(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="minutes")


def _latest_write(path: Path) -> str | None:
    """Newest modification time of any file under ``path`` (receipts first, as a cheap answer)."""
    receipts = path / "_receipts.jsonl"
    if receipts.exists():
        return _mtime(receipts)
    newest = 0.0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                newest = max(newest, os.stat(os.path.join(root, name)).st_mtime)
            except OSError:
                pass
    return datetime.fromtimestamp(newest, timezone.utc).isoformat(timespec="minutes") if newest else None


def live_progress(cat: dict) -> dict:
    """Files on disk and the last write of every dataset the catalog marks as downloading."""
    out = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="minutes"), "datasets": {}}
    for ds in cat.get("datasets") or []:
        if ds.get("status") != "downloading":
            continue
        files, last = 0, None
        for ref in _paths(ds.get("raw")):
            path = PROJECT_ROOT / ref
            if path.exists():
                files += folder_size(path)[1]
                when = _latest_write(path)
                last = max(filter(None, [last, when]), default=None)
        out["datasets"][ds["id"]] = {"files_on_disk": files, "last_write": last}
    return out


def _tml_levels() -> dict:
    """(season, ATP tournament id) -> map level, from Tennis My Life's main-draw files."""
    out = {}
    for path in sorted((DATA / "dump" / "matches" / "tennis_my_life" / "atp_main").glob("*.parquet")):
        year = M._year_of(path)
        if year is None or year < M.FIRST_YEAR:
            continue
        f = pd.read_parquet(path, columns=["tourney_id", "tourney_level", "tourney_name"]).drop_duplicates()
        for tid, code, name in zip(f["tourney_id"], f["tourney_level"], f["tourney_name"]):
            out[(year, str(tid).partition("-")[2])] = M.tour_level_atp(str(code), str(name))
    return out


def locked_counts() -> list[dict]:
    """Matches whose encrypted ATP Stats Centre files are on disk (data/raw/point_sources/infosys_atp/), by season,
    map level and kind of file: MatchBeats (every point) or Court Vision (every shot). Nothing is decrypted: only
    the file names are read (<season>/<event>/<route>/<match code>.json.gz)."""
    root = DATA / "raw" / "point_sources" / "infosys_atp"
    if not root.exists():
        return []
    levels, seen = _tml_levels(), set()
    for path in root.glob("*/*/*/*.json.gz"):
        season, event, route = path.parts[-4], path.parts[-3], path.parts[-2]
        if route not in ("match-beats", "court-vision") or not season.isdigit():
            continue
        code = path.name[:-len(".json.gz")]
        level = levels.get((int(season), event))
        if level is None:
            continue
        if code.upper().startswith("Q"):
            level = M.to_qual(level)
        seen.add((int(season), level, route, event, code.upper()))
    counts = pd.DataFrame(sorted(seen), columns=["year", "level", "route", "event", "code"])
    if counts.empty:
        return []
    counts["grain"] = counts["route"].map({"match-beats": "point", "court-vision": "shot"})
    out = counts.groupby(["year", "level", "grain"]).size().rename("matches").reset_index()
    out["tour"] = "M"
    return out.to_dict(orient="records")


# --------------------------------------------------------------------------------------------
# Market data, from the staged tables' metadata (no rows are read)

ODDS_LEVEL = {"Grand Slam": "GS", "Masters 1000": "T1000", "Masters": "T1000", "ATP500": "T500", "ATP250": "T250",
              "International": "T250", "International Gold": "T500", "Masters Cup": "FIN", "Tour Championships": "FIN",
              "WTA1000": "T1000", "WTA500": "T500", "WTA250": "T250", "Premier": "T1000/T500"}


def market_counts(first_year: int) -> dict:
    odds = []
    base = DATA / "dump" / "odds" / "tennis_data_couk"
    for path in sorted(base.glob("*/*/*.parquet")):
        tour, label, year = path.parts[-3], path.parts[-2], path.stem
        if not year.isdigit() or int(year) < first_year:
            continue
        level = ODDS_LEVEL.get(label, "T250" if label.startswith("WTA25") else label)
        odds.append({"tour": "M" if tour == "atp" else "W", "label": label, "level": level, "year": int(year),
                     "matches": pq.ParquetFile(path).metadata.num_rows})
    prices = []
    for path in sorted((DATA / "dump" / "odds" / "polymarket" / "price_history").glob("*/*.parquet")):
        prices.append({"bucket": path.parent.name, "month": path.stem, "rows": pq.ParquetFile(path).metadata.num_rows})
    # wallets.parquet beside the buckets is the table of traders, not a level of markets
    trades = [{"bucket": p.stem, "rows": pq.ParquetFile(p).metadata.num_rows}
              for p in sorted((DATA / "dump" / "odds" / "polymarket" / "trades").glob("*.parquet")) if p.stem != "wallets"]
    betonline = []
    path = DATA / "dump" / "odds" / "oddstrader" / "betonline_matches.parquet"
    if path.exists():
        b = pd.read_parquet(path, columns=["tour", "dt_utc", "mw_open_home", "mw_close_home", "tg_close_line"])
        b["year"] = pd.to_datetime(b["dt_utc"], errors="coerce", utc=True).dt.year
        for (tour, year), g in b.dropna(subset=["year"]).groupby(["tour", "year"]):
            betonline.append({"tour": "M" if tour == "ATP" else "W", "year": int(year), "matches": int(len(g)),
                              "with_open": int(g["mw_open_home"].notna().sum()),
                              "with_last": int(g["mw_close_home"].notna().sum()),
                              "with_total_games": int(g["tg_close_line"].notna().sum())})
    return {"closing_odds": odds, "polymarket_prices": prices, "polymarket_trades": trades, "betonline": betonline}


def held_by_dataset(cat: dict) -> pd.DataFrame:
    """One row per (map match, catalog dataset holding it), with the dataset's acquisition method.

    Read from data/studies/data_map/matches.parquet (local, rebuilt by the measurement); empty if absent.
    """
    path = M.OUT / "matches.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["uid", "tour", "year", "dataset", "how"])
    src_to_ds = {}
    for ds in cat.get("datasets") or []:
        for item in ds.get("measured_as") or []:
            src_to_ds[item["id"] if isinstance(item, dict) else item] = ds["id"]
    how = {ds["id"]: ds.get("how") for ds in cat.get("datasets") or []}
    m = pd.read_parquet(path, columns=["uid", "tour", "level", "year", "sources"])
    m = m[m["level"].isin(M.GRID_LEVELS)]
    m = m.assign(src=m["sources"].fillna("").str.split(";")).explode("src")
    m["dataset"] = m["src"].map(src_to_ds)
    m = m.dropna(subset=["dataset"]).drop_duplicates(["uid", "dataset"])
    m["how"] = m["dataset"].map(how)
    return m[["uid", "tour", "year", "dataset", "how"]]


def dataset_years(held: pd.DataFrame) -> list[dict]:
    """Matches in the map each dataset holds, by tour and year, each match counted once per dataset."""
    out = held.groupby(["dataset", "tour", "year"]).size().rename("matches").reset_index()
    return out.to_dict(orient="records")


def method_matches(held: pd.DataFrame) -> list[dict]:
    """Matches in the map the datasets of each acquisition method hold, each match counted once per method."""
    out = held.dropna(subset=["how"]).drop_duplicates(["uid", "how"]).groupby("how").size()
    return [{"how": how, "matches": int(n)} for how, n in out.items()]


# --------------------------------------------------------------------------------------------
# Page

def render(payload: dict) -> tuple[str, str]:
    """(full document, fragment). The template's head part ends at <!--BODY-->."""
    text = TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(payload, separators=(",", ":"), default=str).replace("</", "<\\/")
    text = text.replace("/*__DATA__*/null", blob)
    head, _, body = text.partition("<!--BODY-->")
    full = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            + head.strip() + "\n</head>\n<body>\n" + body.strip() + "\n</body>\n</html>\n")
    return full, head.strip() + "\n" + body.strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build data/data_map.html.")
    parser.add_argument("--no-measure", action="store_true", help="reuse data/studies/data_map/coverage.json")
    parser.add_argument("--end", help="last day counted (default: the last complete Sunday)")
    parser.add_argument("--refresh", action="store_true", help="re-read the slow sources instead of the cache")
    parser.add_argument("--fragment", help="also write the page as a fragment (no <html>/<head>) to this path")
    parser.add_argument("--strict", action="store_true", help="fail on catalog problems or unmapped folders")
    args = parser.parse_args()

    cat = load_catalog()
    problems = check_catalog(cat)
    for p in problems:
        print("catalog:", p)

    coverage_path = M.OUT / "coverage.json"
    if args.no_measure and coverage_path.exists():
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    else:
        end = pd.Timestamp(args.end) if args.end else M.last_complete_sunday(datetime.now())
        coverage = M.run(end, refresh=args.refresh)

    per_dataset, tree, unmapped = sizes_and_unmapped(cat)
    for u in unmapped:
        print("unmapped folder (add it to data/data_map.yaml):", u)
    held = held_by_dataset(cat)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "catalog": cat,
        "coverage": coverage,
        "sizes": {"datasets": per_dataset, "folders": tree, "stages": stage_sizes()},
        "unmapped": unmapped,
        "catalog_problems": problems,
        "live": live_progress(cat),
        "market": market_counts(M.FIRST_YEAR),
        "dataset_years": dataset_years(held),
        "method_matches": method_matches(held),
        "locked": locked_counts(),
    }
    full, fragment = render(payload)
    PAGE.write_text(full, encoding="utf-8")
    if args.fragment:
        Path(args.fragment).write_text(fragment, encoding="utf-8")
    report = {"generated_at": payload["generated_at"], "page": PAGE.relative_to(PROJECT_ROOT).as_posix(),
              "page_bytes": len(full.encode("utf-8")), "catalog_problems": problems, "unmapped_folders": unmapped,
              "live": payload["live"], "window": coverage.get("window"), "totals": coverage.get("totals")}
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))
    if args.strict and (problems or unmapped):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

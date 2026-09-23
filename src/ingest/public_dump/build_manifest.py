"""Build the tracked manifest and coverage summaries for the public data dump.

Scans data/dump/**/*.parquet with their .meta.json sidecars, reads every source's receipts under
data/raw/public_dump, and writes to data/studies/public_data_dump/:

    manifest.json        one record per staged Parquet file: provenance plus measured coverage
    coverage.json        per branch/source aggregates
    coverage_tables.md   the same as Markdown tables, for the report
    download_log.json    latest receipt per downloaded object, including failures and routes

Coverage is measured from the verbatim string columns (lexicographic min/max of date-like columns,
value counts of tournament-type columns). It is a description of what was staged, not validation.

Usage:
    ./python.sh -m src.ingest.public_dump.build_manifest
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

DATE_COLUMNS = ["tourney_date", "Date", "date", "scheduled_time_utc", "ranking_date", "timestamp_utc",
                "sport_date", "start_date", "gameStartTime", "t"]
TIER_COLUMNS = ["_partition_value", "tourney_level", "Series", "Tier", "tier_key", "level", "bucket",
                "bucket_slug", "sportsMarketType"]


def nonempty(column):
    values = column.drop_null()
    if pa.types.is_string(values.type) or pa.types.is_large_string(values.type):
        values = values.filter(pc.not_equal(values, ""))
    return values


def date_bounds(path: Path, columns: list[str]) -> tuple[str | None, str | None, str | None]:
    schema = pq.ParquetFile(path).schema_arrow
    candidates = [c for c in DATE_COLUMNS if c in columns]
    # "t" is only a date column when it holds integer Unix seconds (Polymarket price files)
    candidates = [c for c in candidates if c != "t" or pa.types.is_integer(schema.field("t").type)]
    column = candidates[0] if candidates else None
    if column:
        values = nonempty(pq.read_table(path, columns=[column]).column(0))
        if len(values) == 0:
            return column, None, None
        if column == "t":
            lo, hi = pc.min(values).as_py(), pc.max(values).as_py()
            to_iso = lambda s: dt.datetime.fromtimestamp(s, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            return column, to_iso(lo), to_iso(hi)
        # verbatim strings: only date-like values (YYYYMMDD or ISO) count; malformed rows such as a
        # round code shifted into the date column are ignored here and flagged by _width_ok instead
        date_like = values.filter(pc.match_substring_regex(values, r"^\d{4}-?\d{2}-?\d{2}"))
        if len(date_like) == 0:
            return column, None, None
        return column, pc.min(date_like).as_py(), pc.max(date_like).as_py()
    if "match_id" in columns:
        values = nonempty(pq.read_table(path, columns=["match_id"]).column(0)).to_pylist()
        dates = sorted({v[:8] for v in values if re.match(r"^\d{8}", v)})
        if dates:
            return "match_id[:8]", dates[0], dates[-1]
        years = sorted({v[:4] for v in values if re.match(r"^\d{4}-", v)})
        if years:
            return "match_id[:4]", years[0], years[-1]
    return None, None, None


def tier_counts(path: Path, columns: list[str], top: int = 30) -> tuple[str | None, dict]:
    column = next((c for c in TIER_COLUMNS if c in columns), None)
    if not column:
        return None, {}
    values = pq.read_table(path, columns=[column]).column(0)
    counts = pc.value_counts(values)
    pairs = sorted(((str(item["values"]), item["counts"]) for item in counts.to_pylist()), key=lambda p: -p[1])
    return column, {k: v for k, v in pairs[:top]}


def scan_dump() -> list[dict]:
    records = []
    for path in sorted(C.DUMP_ROOT.rglob("*.parquet")):
        meta_path = path.parent / (path.name + ".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        parquet = pq.ParquetFile(path)
        columns = parquet.schema_arrow.names
        rel_path = C.rel(path)
        parts = rel_path.split("/")
        record = {"branch": parts[2] if len(parts) > 2 else None, "source": parts[3] if len(parts) > 3 else None,
                  "dest": rel_path, "rows": parquet.metadata.num_rows, "columns_n": len(columns),
                  "file_bytes": path.stat().st_size}
        for key in ("source_path", "url", "final_url", "sha256", "retrieved_at", "last_modified", "route",
                    "wayback_timestamp", "local_path", "commit", "release_tag", "zenodo_version", "checksum_ok",
                    "partition_column", "partition_value", "short_rows", "long_rows", "encoding", "bucket", "month", "note"):
            if key in meta:
                record[key] = meta[key]
        date_col, lo, hi = date_bounds(path, columns)
        record.update(date_column=date_col, date_min=lo, date_max=hi)
        tier_col, counts = tier_counts(path, columns)
        record.update(tier_column=tier_col, tier_counts=counts)
        record["provenance_columns"] = [c for c in columns if c.startswith("_")]
        record["source_columns"] = [c for c in columns if not c.startswith("_")]
        records.append(record)
    return records


def aggregate(records: list[dict]) -> dict:
    groups: dict = defaultdict(lambda: {"files": 0, "rows": 0, "bytes": 0, "date_min": None, "date_max": None,
                                         "routes": Counter(), "tier_rows": Counter()})
    for r in records:
        g = groups[(r["branch"], r["source"])]
        g["files"] += 1
        g["rows"] += r["rows"]
        g["bytes"] += r["file_bytes"]
        if r["date_min"] and (g["date_min"] is None or r["date_min"] < g["date_min"]):
            g["date_min"] = r["date_min"]
        if r["date_max"] and (g["date_max"] is None or r["date_max"] > g["date_max"]):
            g["date_max"] = r["date_max"]
        if r.get("route"):
            g["routes"][r["route"]] += 1
        for value, count in r["tier_counts"].items():
            g["tier_rows"][value] += count
    out = {}
    for (branch, source), g in sorted(groups.items()):
        out[f"{branch}/{source}"] = {"branch": branch, "source": source, "files": g["files"], "rows": g["rows"],
                                     "bytes": g["bytes"], "date_min": g["date_min"], "date_max": g["date_max"],
                                     "routes": dict(g["routes"]), "tier_rows": dict(g["tier_rows"].most_common(40))}
    return out


def read_download_log() -> dict:
    log = {}
    if not C.RAW_ROOT.exists():
        return log
    for receipts_path in sorted(C.RAW_ROOT.glob("*/_receipts.jsonl")):
        source = receipts_path.parent.name
        latest: dict[str, dict] = {}
        history = 0
        with receipts_path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    receipt = json.loads(line)
                    latest[receipt["name"]] = receipt
                    history += 1
        errors = [r for r in latest.values() if r.get("error")]
        routes = Counter(r.get("route") for r in latest.values() if r.get("route"))
        entry = {"objects": len(latest), "receipt_lines": history, "errors": len(errors),
                 "routes": dict(routes), "error_details": [{"name": r["name"], "url": r.get("url"), "error": r["error"]}
                                                           for r in errors[:200]]}
        if source == "polymarket_prices":
            entry["points"] = sum(r.get("points") or 0 for r in latest.values())
            entry["empty_histories"] = sum(1 for r in latest.values() if r.get("points") == 0)
            entry["buckets"] = dict(Counter(r.get("bucket") for r in latest.values() if not r.get("error")))
        else:
            entry["receipts"] = sorted(({k: v for k, v in r.items() if k not in ("attempts",)} for r in latest.values()),
                                       key=lambda r: r["name"])
        log[source] = entry
    return log


def markdown_tables(records: list[dict], coverage: dict) -> str:
    lines = ["# Public data dump coverage tables", "",
             f"Generated {C.utc_now_iso()} by src/ingest/public_dump/build_manifest.py from the staged Parquet files. "
             "Dates are the verbatim min/max of the named column (tournament-week dates for Sackmann/TML, "
             "match dates for tennis-data.co.uk, scheduled UTC for the Live Tennis API index); row counts are physical rows.", "",
             "## By branch and source", "", "| Branch | Source | Files | Rows | MB | Earliest | Latest | Routes |", "|---|---|---:|---:|---:|---|---|---|"]
    for key, g in coverage.items():
        lines.append(f"| {g['branch']} | {g['source']} | {g['files']} | {g['rows']:,} | {g['bytes'] / 1e6:.1f} | "
                     f"{g['date_min'] or ''} | {g['date_max'] or ''} | {', '.join(f'{k}={v}' for k, v in g['routes'].items())} |")
    lines += ["", "## Rows by tournament-type value (verbatim source labels)", ""]
    for key, g in coverage.items():
        if not g["tier_rows"]:
            continue
        lines += [f"### {key}", "", "| Value | Rows |", "|---|---:|"]
        lines += [f"| {value} | {count:,} |" for value, count in g["tier_rows"].items()]
        lines.append("")
    lines += ["## Every staged file", "", "| File | Rows | Date column | Earliest | Latest | Short/long rows | Route |",
              "|---|---:|---|---|---|---|---|"]
    for r in records:
        odd = f"{r.get('short_rows', 0) or 0}/{r.get('long_rows', 0) or 0}"
        lines.append(f"| {r['dest']} | {r['rows']:,} | {r['date_column'] or ''} | {r['date_min'] or ''} | "
                     f"{r['date_max'] or ''} | {odd} | {r.get('route') or ''} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    C.STUDY_ROOT.mkdir(parents=True, exist_ok=True)
    records = scan_dump()
    coverage = aggregate(records)
    log = read_download_log()
    (C.STUDY_ROOT / "manifest.json").write_text(json.dumps({"generated_at": C.utc_now_iso(), "files": records},
                                                          indent=1, ensure_ascii=False), encoding="utf-8")
    (C.STUDY_ROOT / "coverage.json").write_text(json.dumps({"generated_at": C.utc_now_iso(), "by_source": coverage},
                                                          indent=1, ensure_ascii=False), encoding="utf-8")
    (C.STUDY_ROOT / "download_log.json").write_text(json.dumps({"generated_at": C.utc_now_iso(), "sources": log},
                                                              indent=1, ensure_ascii=False), encoding="utf-8")
    (C.STUDY_ROOT / "coverage_tables.md").write_text(markdown_tables(records, coverage), encoding="utf-8")
    total_rows = sum(r["rows"] for r in records)
    C.log(f"[manifest] {len(records)} staged files, {total_rows:,} rows, {len(coverage)} branch/source groups; "
          f"download errors: { {s: e['errors'] for s, e in log.items() if e['errors']} }")
    return 0


if __name__ == "__main__":
    sys.exit(main())

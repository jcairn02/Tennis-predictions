"""Fetch and audit named public tennis snapshots without changing ingestion code.

Research interpreter explicitly used: C:/Users/zerom/miniforge3/envs/ufc-monitor/python.exe.
Only Python stdlib is required. Reruns reuse raw files; use --refresh to refetch.
"""
import argparse
import concurrent.futures
import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import re
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/studies/tennis_data_audit/public"
START, END = "20250910", "20260910"
SOURCES = {
    "archive_tree.json": "https://api.github.com/repos/Aneeshers/tennis-sackmann-archive/git/trees/main?recursive=1",
    "mcp_tree.json": "https://api.github.com/repos/JeffSackmann/tennis_MatchChartingProject/git/trees/master?recursive=1",
    "open_tennis_releases.json": "https://api.github.com/repos/ryantjx/tennis-match-data/releases?per_page=5",
    "archive_readme.md": "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/README.md",
    "archive_atp_readme.md": "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/atp/UPSTREAM_README.md",
    "archive_wta_readme.md": "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/wta/UPSTREAM_README.md",
    "mcp_m_matches.csv": "https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-m-matches.csv",
    "mcp_w_matches.csv": "https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/charting-w-matches.csv",
    "tennisdata_downloads.html": "https://tennisdata.app/downloads/",
    "zenodo_record.json": "https://zenodo.org/api/records/22048731",
}
for tour in ("atp", "wta"):
    for year in (2024, 2025, 2026):
        for suffix in ("matches", "matches_qual_chall", "matches_futures"):
            name = f"{tour}_{suffix}_{year}.csv"
            SOURCES[name] = f"https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/{tour}/{name}"
    for kind in ("players", "rankings_current"):
        name = f"{tour}_{kind}.csv"
        SOURCES[name] = f"https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/{tour}/{name}"
for year in (2024, 2025, 2026):
    name = f"wta_matches_qual_itf_{year}.csv"
    SOURCES[name] = f"https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/wta/{name}"
SOURCES["sackmann_data_dictionary.txt"] = "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/atp/matches_data_dictionary.txt"
SOURCES["slam_readme.md"] = "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/slam_pointbypoint/UPSTREAM_README.md"
for name in ("2024-usopen-matches.csv", "2024-usopen-matches-doubles.csv", "2024-usopen-matches-mixed.csv"):
    SOURCES[name] = f"https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/slam_pointbypoint/{name}"
for name in ("DATA.md", "DATA_LICENSE.md", "docs/SCHEMA.md", "docs/SOURCES.md"):
    SOURCES["open_tennis_" + name.replace("/", "_")] = f"https://raw.githubusercontent.com/ryantjx/tennis-match-data/main/{name}"
for tour in ("atp", "wta"):
    for year in (2025, 2026):
        segment = str(year) + ("w" if tour == "wta" else "")
        SOURCES[f"tennis_data_{tour}_{year}.xlsx"] = f"https://www.tennis-data.co.uk/{segment}/{year}.xlsx"
SOURCES["tennis_data_notes.txt"] = "https://www.tennis-data.co.uk/notes.txt"
SOURCES["tennis_data_notesw.txt"] = "https://www.tennis-data.co.uk/notesw.txt"


def fetch(item, refresh):
    name, url = item
    target = OUT / "raw" / name
    receipt_path = target.with_suffix(target.suffix + ".receipt.json")
    if target.exists() and receipt_path.exists() and not refresh:
        return json.loads(receipt_path.read_text())
    receipt = {"name": name, "url": url, "accessed_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "tennis-data-research/1.0"})
        with urllib.request.urlopen(req, timeout=45) as res:
            body = res.read()
            receipt.update(status=res.status, final_url=res.url, content_type=res.headers.get("Content-Type"),
                           last_modified=res.headers.get("Last-Modified"), bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        target.write_bytes(body)
    except Exception as exc:
        receipt["error"] = str(exc)
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def csv_audit(path):
    try:
        body = gzip.decompress(path.read_bytes()).decode("utf-8-sig") if path.suffix == ".gz" else path.read_text(encoding="utf-8-sig")
        reader = csv.DictReader(io.StringIO(body))
        rows = list(reader)
        fields = reader.fieldnames or []
    except Exception as exc:
        return {"file": path.name, "error": str(exc)}
    result = {"file": path.name, "rows": len(rows), "fields": fields,
              "missing": {f: sum(r.get(f, "") in ("", None) for r in rows) for f in fields}}
    widths = list(csv.reader(io.StringIO(body)))
    result["invalid_width_rows"] = sum(len(r) != len(fields) for r in widths[1:])
    result["duplicate_full_rows"] = len(widths[1:]) - len({tuple(r) for r in widths[1:]})
    for field in ("tourney_date", "date", "ranking_date", "Date"):
        if field in fields:
            dates = [str(r[field]) for r in rows if re.match(r"^\d{4}-?\d{2}-?\d{2}", str(r[field]))]
            result[field + "_invalid_nonempty"] = sum(bool(r[field]) and not re.match(r"^\d{4}-?\d{2}-?\d{2}", str(r[field])) for r in rows)
            result[field] = {"min": min(dates, default=None), "max": max(dates, default=None)}
            compact = lambda d: d.replace("-", "")[:8]
            result["requested_window_rows"] = sum(START <= compact(d) <= END for d in dates)
    for field in ("tourney_level", "round", "surface", "best_of"):
        if field in fields:
            result[field] = dict(collections.Counter(r[field] for r in rows))
    if "score" in fields:
        result["score_status"] = dict(collections.Counter("RET" if "RET" in r["score"].upper() else "W/O" if "W/O" in r["score"].upper() else "DEF" if "DEF" in r["score"].upper() else "ABN" if "ABN" in r["score"].upper() else "blank" if not r["score"] else "other" for r in rows))
    if all(f in fields for f in ("tourney_id", "match_num")):
        keys = [(r["tourney_id"], r["match_num"]) for r in rows]
        result["duplicate_tourney_match_keys"] = len(keys) - len(set(keys))
        duplicated_keys = {key for key,count in collections.Counter(keys).items() if count > 1}
        result["duplicate_key_examples"] = [{f:r.get(f) for f in ("tourney_id","tourney_name","match_num","winner_name","loser_name")} for r in rows if (r["tourney_id"],r["match_num"]) in duplicated_keys][:8]
        result["tournaments"] = len({r["tourney_id"] for r in rows})
    if "winner_id" in fields and "loser_id" in fields:
        result["distinct_players"] = len({r[f] for r in rows for f in ("winner_id", "loser_id") if r[f]})
        result["self_matches"] = sum(r["winner_id"] == r["loser_id"] for r in rows)
    if "match_id" in fields:
        result["duplicate_match_ids"] = len(rows) - len({r["match_id"] for r in rows})
        if path.name.startswith(("mcp", "2024-usopen")):
            years = collections.Counter(r["match_id"][:4] for r in rows)
            result["match_id_year_counts"] = dict(sorted(years.items()))
            result["requested_window_by_match_id"] = sum(START <= r["match_id"][:8] <= END for r in rows)
        if path.name.startswith("mcp"):
            result["match_id_date_max"] = max(r["match_id"][:8] for r in rows)
    if "tourney_name" in fields and "tourney_level" in fields:
        result["tournament_examples_by_level"] = {level: sorted({r["tourney_name"] for r in rows if r["tourney_level"] == level})[:8] for level in result["tourney_level"]}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    zenodo = OUT / "raw/zenodo_record.json"
    if zenodo.exists():
        for item in json.loads(zenodo.read_text())["files"]:
            SOURCES["zenodo_" + item["key"]] = item["links"]["self"]
    releases = OUT / "raw/open_tennis_releases.json"
    if releases.exists():
        for item in json.loads(releases.read_text())[0]["assets"]:
            SOURCES["open_tennis_" + item["name"]] = item["browser_download_url"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        receipts = list(pool.map(lambda item: fetch(item, args.refresh), SOURCES.items()))
    (OUT / "fetch_receipts.json").write_text(json.dumps(receipts, indent=2), encoding="utf-8")
    audits = [csv_audit(p) for p in sorted((OUT / "raw").iterdir()) if p.name.endswith((".csv", ".csv.gz"))]
    (OUT / "csv_audit.json").write_text(json.dumps(audits, indent=2), encoding="utf-8")
    print(json.dumps({"fetched": sum("error" not in r for r in receipts), "errors": [r for r in receipts if "error" in r],
                      "audits": [{k: v for k, v in a.items() if k in ("file", "rows", "error", "tourney_date", "requested_window_rows", "invalid_width_rows")} for a in audits]}, indent=2))


if __name__ == "__main__":
    main()

"""Gap sources, lane A: download the hawkilol Court Vision copy's catalogue and per-point CSVs.

Source: GitHub hawkilol/tennisSlamBallTracking, pinned to commit f97a9b31e64eab8485474398414dd26523871f64
(2025-04-08, the latest on 29 Sep 2026). Files come from raw.githubusercontent.com at that commit; the tree
listing comes from the GitHub API through the owner's `gh` CLI.

Downloads into data/raw/gap_sources/hawkilol/ (gitignored), keeping the repository's paths:
* _tree_<sha7>.json: the recursive git tree (paths, sizes, blob SHA-1s).
* README.md, LICENSE, src/process.py, src/search_utils.py, players_matches_catalogue/*.csv.
* every pbp_data_csvs/**/*.csv (2,027 files, about 163 MB).
* three raw per-match JSON samples (one each from 2022, 2023 and 2024); the other 2,024 raw JSON files
  (3.3 GB in all) are not downloaded.
* _receipt_<sha7>.json: per file, bytes and whether its git blob SHA-1 matches the tree.

A file already on disk whose git blob hash matches the tree is not fetched again.
Run: ./python.sh src/eda/gap_sources/fetch_hawkilol.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "raw" / "gap_sources" / "hawkilol"
REPO = "hawkilol/tennisSlamBallTracking"
SHA = "f97a9b31e64eab8485474398414dd26523871f64"
RAW = f"https://raw.githubusercontent.com/{REPO}/{SHA}/{{}}"
META = ["README.md", "LICENSE", "src/process.py", "src/search_utils.py"]
JSON_SAMPLES = [
    "all_json/australian_open/wta/wta_AO_Open_year_2022_WS101_tracking_data.json",
    "all_json/roland_garros/atp/atp_RG_year_2023_SM001_tracking_data.json",
    "all_json/australian_open/atp/atp_AO_Open_year_2024_MS701_tracking_data.json",
]


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def load_tree() -> list[dict]:
    path = OUT / f"_tree_{SHA[:7]}.json"
    if not path.exists():
        raw = subprocess.run(
            ["gh", "api", f"repos/{REPO}/git/trees/{SHA}?recursive=1"],
            check=True, capture_output=True, text=True,
        ).stdout
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw, encoding="utf-8")
    tree = json.loads(path.read_text(encoding="utf-8"))
    if tree.get("truncated"):
        sys.exit("tree listing truncated")
    return [e for e in tree["tree"] if e["type"] == "blob"]


def fetch(entry: dict, session: requests.Session) -> dict:
    dest = OUT / entry["path"]
    if dest.exists() and git_blob_sha1(dest.read_bytes()) == entry["sha"]:
        return {"path": entry["path"], "bytes": entry["size"], "blob_ok": True, "fetched": False}
    r = session.get(RAW.format(entry["path"]), timeout=120)
    r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return {"path": entry["path"], "bytes": len(r.content),
            "blob_ok": git_blob_sha1(r.content) == entry["sha"], "fetched": True}


def main() -> None:
    blobs = load_tree()
    wanted = [e for e in blobs if e["path"] in META or e["path"] in JSON_SAMPLES
              or e["path"].startswith("players_matches_catalogue/")
              or (e["path"].startswith("pbp_data_csvs/") and e["path"].endswith(".csv"))]
    missing = set(JSON_SAMPLES) - {e["path"] for e in wanted}
    if missing:
        sys.exit(f"sample paths not in tree: {missing}")
    session = requests.Session()
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda e: fetch(e, session), wanted))
    bad = [r["path"] for r in rows if not r["blob_ok"]]
    receipt = {
        "repo": REPO, "commit": SHA,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": len(rows), "bytes": sum(r["bytes"] for r in rows),
        "fetched_this_run": sum(r["fetched"] for r in rows), "blob_sha_mismatch": bad,
        "per_file": rows,
    }
    (OUT / f"_receipt_{SHA[:7]}.json").write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    print(f"{len(rows)} files, {receipt['bytes']:,} bytes, fetched {receipt['fetched_this_run']}, "
          f"blob mismatches {len(bad)}")


if __name__ == "__main__":
    main()

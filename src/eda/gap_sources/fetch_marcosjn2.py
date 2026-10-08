"""Gap sources, lane B1: download the Kaggle marcosjn2 point-by-point dataset without an account.

Source: Kaggle dataset `marcosjn2/tennis-point-by-point-match-dataset-20152025` ("Tennis Point-by-Point
Match Dataset (2015-2026)", Marcos Johnson Noya; version 2 of 29 Aug 2025 on 29 Sep 2026). Kaggle's public
endpoint `/api/v1/datasets/download/<owner>/<slug>/<file>` answers an anonymous request with HTTP 302 to a
signed Google Cloud Storage URL (valid 3 days); the file is streamed from there. No login, cookie or token
is sent.

Writes into data/raw/gap_sources/marcosjn2/ (gitignored):
* `_view.json` and `_files.json`: the dataset metadata and file list as served by the public API.
* `atp-matches.jsonl`, `wta-matches.jsonl`: the two files, byte-exact.
* `_receipts.jsonl`: per file the unsigned storage path, dataset/version ids, bytes, SHA-256 and time.

A file already on disk with the listed size is not fetched again. Requests to kaggle.com are spaced by at
least 2 seconds. Run: ./python.sh src/eda/gap_sources/fetch_marcosjn2.py
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "raw" / "gap_sources" / "marcosjn2"
REF = "marcosjn2/tennis-point-by-point-match-dataset-20152025"
API = "https://www.kaggle.com/api/v1"
HEADERS = {"User-Agent": "tennis-predictions-research/1.0 (no account)"}
GAP_S = 2.2
_last = [0.0]


def _kaggle(url: str, **kw) -> requests.Response:
    wait = GAP_S - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    return requests.get(url, headers=HEADERS, timeout=60, **kw)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    view = _kaggle(f"{API}/datasets/view/{REF}")
    view.raise_for_status()
    (OUT / "_view.json").write_text(view.text, encoding="utf-8")
    files = _kaggle(f"{API}/datasets/list/{REF}")
    files.raise_for_status()
    (OUT / "_files.json").write_text(files.text, encoding="utf-8")
    meta = view.json()
    for f in files.json()["datasetFiles"]:
        name, size = f["name"], int(f["totalBytes"])
        dest = OUT / name
        if dest.exists() and dest.stat().st_size == size:
            print(f"{name}: already on disk ({size:,} bytes)")
            continue
        r = _kaggle(f"{API}/datasets/download/{REF}/{name}", allow_redirects=False)
        if r.status_code != 302:
            raise SystemExit(f"{name}: expected a 302 redirect, got {r.status_code}")
        signed = r.headers["location"]
        parts = urlsplit(signed)
        h = hashlib.sha256()
        n = 0
        tmp = dest.with_suffix(dest.suffix + ".part")
        with requests.get(signed, stream=True, timeout=120) as s, tmp.open("wb") as fh:
            s.raise_for_status()
            for chunk in s.iter_content(1 << 20):
                fh.write(chunk)
                h.update(chunk)
                n += len(chunk)
        if n != size:
            raise SystemExit(f"{name}: got {n} bytes, list says {size}")
        tmp.replace(dest)
        path_bits = parts.path.strip("/").split("/")  # kagglesdsdata/datasets/<dataset_id>/<version_id>/<file>
        rec = {
            "name": name, "dest": str(dest.relative_to(ROOT)).replace("\\", "/"),
            "dataset_ref": REF, "dataset_id": meta.get("id"), "version_number": meta.get("currentVersionNumber"),
            "storage_version_id": path_bits[3] if len(path_bits) > 4 else None,
            "storage_path": f"{parts.scheme}://{parts.hostname}{parts.path}",
            "signed_url_expires_s": 259200, "bytes": n, "sha256": h.hexdigest(),
            "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_updated": meta.get("lastUpdated"), "license": meta.get("licenseName"),
        }
        with (OUT / "_receipts.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"{name}: {n:,} bytes, sha256 {rec['sha256'][:16]}...")


if __name__ == "__main__":
    main()

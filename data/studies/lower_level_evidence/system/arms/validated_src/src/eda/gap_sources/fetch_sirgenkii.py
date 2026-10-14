"""Gap sources, lane B2: download the SirGenkii/infotennis fork's SQL dumps and reference files.

Source: GitHub SirGenkii/infotennis (fork of glad94/infotennis), pinned to its head commit
ec1b188f30e9bccc6923ed084b0db99e0e472917 (2025-04-11, still the head on 29 Sep 2026). The `backup_sql/`
dumps were added in commit 1bb7527dda3845fc2cbe4c3d4391042f5cf97aa1 (2025-04-07) and not changed since.
Files come from raw.githubusercontent.com at the pinned commit; the tree comes from the GitHub API through
the owner's `gh` CLI (read-only; it only raises rate limits).

Writes into data/raw/gap_sources/sirgenkii/ (gitignored), keeping the repository's paths:
* _tree_<sha7>.json: the recursive git tree.
* backup_sql/*.sql (6 files, about 34 MB), README.md, LICENSE, config.yaml, data/players_ATP.csv,
  references/api-info/*.json, infotennis/scrapers/*.py, infotennis/routines/sql_functions.py.
* _receipt_<sha7>.json: per file, bytes and whether its git blob SHA-1 matches the tree.

Run: ./python.sh src/eda/gap_sources/fetch_sirgenkii.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "raw" / "gap_sources" / "sirgenkii"
REPO = "SirGenkii/infotennis"
SHA = "ec1b188f30e9bccc6923ed084b0db99e0e472917"
RAW = f"https://raw.githubusercontent.com/{REPO}/{SHA}/{{}}"
EXTRA = ["README.md", "LICENSE", "config.yaml", "data/players_ATP.csv",
         "infotennis/scrapers/scrape_match_data.py", "infotennis/scrapers/scraping_functions_atp.py",
         "infotennis/routines/sql_functions.py", "infotennis/routines/update_calendar_results.py"]


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tree_txt = subprocess.run(["gh", "api", f"repos/{REPO}/git/trees/{SHA}?recursive=1"],
                              check=True, capture_output=True, text=True).stdout
    (OUT / f"_tree_{SHA[:7]}.json").write_text(tree_txt, encoding="utf-8")
    tree = {e["path"]: e for e in json.loads(tree_txt)["tree"] if e["type"] == "blob"}
    want = [p for p in tree if p.startswith("backup_sql/") or p.startswith("references/api-info/")] + EXTRA
    receipt = []
    for path in want:
        dest = OUT / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and git_blob_sha(dest.read_bytes()) == tree[path]["sha"]:
            data = dest.read_bytes()
        else:
            r = requests.get(RAW.format(path), timeout=120)
            r.raise_for_status()
            data = r.content
            dest.write_bytes(data)
        ok = git_blob_sha(data) == tree[path]["sha"]
        receipt.append({"path": path, "url": RAW.format(path), "bytes": len(data), "git_blob_sha1": tree[path]["sha"],
                        "blob_matches": ok, "sha256": hashlib.sha256(data).hexdigest(),
                        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
        print(f"{path}: {len(data):,} bytes, blob {'ok' if ok else 'MISMATCH'}")
    (OUT / f"_receipt_{SHA[:7]}.json").write_text(json.dumps({"repo": REPO, "commit": SHA, "files": receipt}, indent=1),
                                                 encoding="utf-8")


if __name__ == "__main__":
    main()

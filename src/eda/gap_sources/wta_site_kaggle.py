"""A Kaggle copy of the WTA website's match records against the women's ITF gaps of the data map.

Kaggle `bwandowando/womens-tennis-association-matches-1975-present` says it is built from wtatennis.com,
player by player (its description; the WTA site lists each player's ITF matches too, qualifying included).
If so it would list what no file in the project does: women's ITF qualifying in 2025-26 (gap
`women_itf_qualifying`) and women's ITF results after June 2026 (half of gap `itf_after_june_2026`).

It is checked three ways:
* **Against Sackmann where both exist:** women's ITF qualifying 2019-2024 and ITF main draws January-May
  2026, year by year: rows in each, and the share of Sackmann's matches found in the file (both surnames,
  tournament start within 7 days).
* **The gap years:** its women's ITF qualifying of 2025 and 2026, and its ITF main draws by ISO week of 2026.
* **Content:** scores, retirements and walkovers (`reason_code`), dates.

Download as src/eda/gap_sources/fetch_marcosjn2.py does: Kaggle's public endpoint answers an anonymous
request with a redirect to a signed storage URL; no login, cookie or token. Files already on disk with the
listed size are not fetched again.

Versions are kept side by side (work package P2 of docs/studies/gap_downloads/collection-plan.md): version 29,
the first downloaded (29 Sep 2026), stays at the folder's root, where the data map and the lower-level evidence
study read it; any later version goes into its own folder `v<N>/`, never over another. A check that finds the
version already on disk saves Kaggle's two answers under `_checks/` and fetches nothing.

Usage:
    ./python.sh src/eda/gap_sources/wta_site_kaggle.py [--no-fetch]
    ./python.sh src/eda/gap_sources/wta_site_kaggle.py --fetch-only     # P2: the current version, beside v29

Writes data/raw/gap_sources/bwandowando/ (files, _view.json, _files.json, _receipts.jsonl; gitignored) and
data/studies/gap_sources/wta_site_kaggle.json (not with --fetch-only).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map.measure import pair_key, surname_key   # noqa: E402

REF = "bwandowando/womens-tennis-association-matches-1975-present"
RAW = PROJECT_ROOT / "data" / "raw" / "gap_sources" / "bwandowando"
OUT = PROJECT_ROOT / "data" / "studies" / "gap_sources" / "wta_site_kaggle.json"
API = "https://www.kaggle.com/api/v1"
HEADERS = {"User-Agent": "tennis-predictions-research/1.0 (no account)"}
_last = [0.0]


def kaggle(url: str, **kw) -> requests.Response:
    wait = 2.2 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    return requests.get(url, headers=HEADERS, timeout=60, **kw)


def root_version() -> int | None:
    """The version held at the folder's root (29), from its saved dataset page; None before any download."""
    view = RAW / "_view.json"
    return json.loads(view.read_text(encoding="utf-8")).get("currentVersionNumber") if view.exists() else None


def version_dir(version: int, root: int | None) -> Path:
    """Where a version's files go: the root for the version already there (or the very first), else v<N>/."""
    return RAW if root is None or version == root else RAW / f"v{version}"


def newest_dir() -> Path:
    """The folder of the newest version on disk (a v<N>/ folder holding matches.csv, else the root)."""
    held = [(int(p.name[1:]), p) for p in RAW.glob("v*") if p.name[1:].isdigit() and (p / "matches.csv").exists()]
    return max(held)[1] if held else RAW


def fetch() -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    root = root_version()
    view = kaggle(f"{API}/datasets/view/{REF}")
    view.raise_for_status()
    files = kaggle(f"{API}/datasets/list/{REF}")
    files.raise_for_status()
    meta = view.json()
    version = meta.get("currentVersionNumber")
    folder = version_dir(version, root)
    if folder == RAW and root is not None:
        # the version on disk: keep Kaggle's answers as a dated check, never over the root's own copies
        checks = RAW / "_checks"
        checks.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (checks / f"{stamp}_view.json").write_text(view.text, encoding="utf-8")
        (checks / f"{stamp}_files.json").write_text(files.text, encoding="utf-8")
    else:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "_view.json").write_text(view.text, encoding="utf-8")
        (folder / "_files.json").write_text(files.text, encoding="utf-8")
    print(f"Kaggle's current version: {version} ({meta.get('lastUpdated')}); on disk at the root: {root}; "
          f"folder: {folder.relative_to(PROJECT_ROOT)}")
    held = folder == RAW and root is not None   # the root's version: nothing is downloaded, nothing overwritten
    for f in files.json()["datasetFiles"]:
        name, size = f["name"], int(f["totalBytes"])
        dest = folder / name
        if held or (dest.exists() and dest.stat().st_size == size):
            continue
        r = kaggle(f"{API}/datasets/download/{REF}/{name}", allow_redirects=False)
        if r.status_code != 302:
            raise SystemExit(f"{name}: expected a 302 redirect, got {r.status_code}")
        parts = urlsplit(r.headers["location"])
        h, n, tmp = hashlib.sha256(), 0, dest.with_suffix(dest.suffix + ".part")
        with requests.get(r.headers["location"], stream=True, timeout=120) as s, tmp.open("wb") as fh:
            s.raise_for_status()
            for chunk in s.iter_content(1 << 20):
                fh.write(chunk)
                h.update(chunk)
                n += len(chunk)
        if n != size:
            raise SystemExit(f"{name}: got {n} bytes, the list says {size}")
        tmp.replace(dest)
        rec = {"name": name, "dest": str(dest.relative_to(PROJECT_ROOT)).replace("\\", "/"), "dataset_ref": REF,
               "dataset_id": meta.get("id"), "version_number": meta.get("currentVersionNumber"),
               "storage_path": f"{parts.scheme}://{parts.hostname}{parts.path}", "bytes": n, "sha256": h.hexdigest(),
               "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "last_updated": meta.get("lastUpdated"), "license": meta.get("licenseName")}
        with (folder / "_receipts.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"{name}: {n:,} bytes")
    return {"version": meta.get("currentVersionNumber"), "last_updated": meta.get("lastUpdated"),
            "license": meta.get("licenseName"), "title": meta.get("title"), "folder": str(folder.relative_to(PROJECT_ROOT)),
            "files": {f["name"]: int(f["totalBytes"]) for f in files.json()["datasetFiles"]}}


def display_name(s) -> str:
    """'SURNAME, FIRST CTY' (the file's form) -> 'First Surname'."""
    s = str(s or "")
    if "," not in s:
        return s
    last, rest = s.split(",", 1)
    parts = rest.split()
    if parts and len(parts[-1]) == 3 and parts[-1].isupper():
        parts = parts[:-1]
    return " ".join(parts + [last.strip()])


def found_share(ours: pd.DataFrame, theirs: pd.DataFrame) -> dict:
    """Share of our matches found in theirs: both surname keys, tournament start within 7 days."""
    ours = ours.assign(pair=pair_key(ours["name1"].map(surname_key), ours["name2"].map(surname_key)))
    j = ours[["uid", "pair", "d"]].merge(theirs[["pair", "start"]], on="pair", how="left")
    hit = j[(j["start"] - j["d"]).dt.days.abs() <= 7]["uid"].nunique()
    return {"ours": int(len(ours)), "found": int(hit), "share": round(hit / max(len(ours), 1), 3)}


def analyse(meta: dict) -> dict:
    t = pd.read_csv(RAW / "tournaments.csv", low_memory=False)
    t["start"] = pd.to_datetime(t["startDate"], errors="coerce")
    cols = ["pseudo_match_id", "pseudo_tournament_id", "reason_code", "round_name", "scores", "qpm_flag",
            "team_name_1", "team_name_2"]
    m = pd.read_csv(RAW / "matches.csv", low_memory=False, usecols=cols)
    rows_all = int(len(m))
    m = m.drop_duplicates("pseudo_match_id").merge(t[["pseudo_tournament_id", "title", "start", "level"]],
                                                   on="pseudo_tournament_id", how="left")
    out = {"dataset": meta, "rows": rows_all, "distinct_matches": int(len(m)),
           "reason_codes": {str(k): int(v) for k, v in m["reason_code"].fillna("(none)").value_counts().items()},
           "levels": {str(k): int(v) for k, v in m["level"].fillna("(none)").value_counts().head(15).items()}}
    m = m[~m["reason_code"].isin(["B"])]                              # byes
    played = m[~m["reason_code"].isin(["D", "UNP", "V"])].copy()      # walkovers and unplayed, read from the data
    itf = played[played["level"].eq("ITF") & played["start"].notna()].copy()
    itf["year"] = itf["start"].dt.year
    itf["n1"], itf["n2"] = itf["team_name_1"].map(display_name), itf["team_name_2"].map(display_name)
    itf["pair"] = pair_key(itf["n1"].map(surname_key), itf["n2"].map(surname_key))
    itf["has_score"] = itf["scores"].fillna("").astype(str).str.strip().ne("")
    # One match can appear twice under different pseudo ids (seen when one player's record lacks the
    # opponent's id): same tournament, draw, round and players. Keep one. Pairs of namesakes (sisters)
    # have no pair key and are kept as they are.
    key = ["pseudo_tournament_id", "qpm_flag", "round_name", "pair"]
    dup = itf["pair"].notna() & itf.duplicated(key)
    out["itf_rows_before_dedup"], out["itf_duplicate_rows_dropped"] = int(len(itf)), int(dup.sum())
    itf = itf[~dup].copy()
    uni = pd.read_parquet(PROJECT_ROOT / "data" / "studies" / "data_map" / "matches.parquet")
    by_year = {}
    for year in range(2018, 2027):
        q = itf[itf["year"].eq(year) & itf["qpm_flag"].eq("Q")]
        mainv = itf[itf["year"].eq(year) & itf["qpm_flag"].eq("M")]
        ours_q = uni[uni["tour"].eq("W") & uni["level"].eq("ITFQ") & uni["year"].eq(year)]
        ours_m = uni[uni["tour"].eq("W") & uni["level"].eq("ITF") & uni["year"].eq(year)]
        by_year[year] = {"kaggle_qual": int(len(q)), "kaggle_main": int(len(mainv)),
                         "kaggle_qual_with_score": int(q["has_score"].sum()),
                         "map_qual": int(len(ours_q)), "map_main": int(len(ours_m)),
                         "map_qual_found": found_share(ours_q, q) if len(ours_q) else None,
                         "map_main_found": found_share(ours_m, mainv) if len(ours_m) else None}
    out["women_itf_by_year"] = by_year
    y26 = itf[itf["start"].dt.isocalendar().year.eq(2026)].copy()
    y26["week"] = y26["start"].dt.isocalendar().week.astype(int)
    wk = y26.groupby(["week", "qpm_flag"]).size().unstack(fill_value=0)
    out["women_itf_2026_by_iso_week"] = {int(w): {str(k): int(v) for k, v in r.items()} for w, r in wk.iterrows()}
    win = y26[y26["week"].between(27, 38)]
    out["women_itf_2026_weeks_27_38"] = {"main": int(win["qpm_flag"].eq("M").sum()), "qual": int(win["qpm_flag"].eq("Q").sum()),
                                         "main_with_score": int((win["qpm_flag"].eq("M") & win["has_score"]).sum())}
    q25 = itf[itf["year"].eq(2025) & itf["qpm_flag"].eq("Q")]
    q26 = itf[itf["year"].eq(2026) & itf["qpm_flag"].eq("Q")]    # calendar years, as for 2025
    out["women_itf_qualifying_gap"] = {"map_estimate_2025": 16277, "map_estimate_2026_to_week_38": 12278,
                                       "kaggle_2025": int(len(q25)), "kaggle_2026": int(len(q26)),
                                       "kaggle_2026_by_month": {str(k): int(v) for k, v in
                                                                q26.groupby(q26["start"].dt.month).size().items()}}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-fetch", action="store_true", help="use the files already on disk")
    parser.add_argument("--fetch-only", action="store_true",
                        help="ask for the current version and download it beside the others; no analysis")
    args = parser.parse_args()
    if args.fetch_only:
        print(json.dumps(fetch(), indent=1))
        return 0
    meta = json.loads((RAW / "_view.json").read_text(encoding="utf-8")) if args.no_fetch else None
    meta = {"version": meta.get("currentVersionNumber"), "last_updated": meta.get("lastUpdated"),
            "license": meta.get("licenseName"), "title": meta.get("title")} if meta else fetch()
    out = analyse(meta)
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

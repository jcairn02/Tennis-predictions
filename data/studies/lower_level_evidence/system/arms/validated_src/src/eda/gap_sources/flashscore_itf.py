"""Flashscore records already on disk (Hugging Face handoff) against the ITF gaps of the data map.

The handoff's Flashscore files (data/raw/public_dump/atp_pipeline_handoff/flashscore_full/, 127 GB of JSON
gzipped to 14 GB) are not read into the data map's counts. This scan keeps every record whose tournament
name marks it as an ITF event ("M15 ...", "W35 ..."), one row per Flashscore match id, with whether it
carries the statistics block, and then links the rows to the data map's matches to answer:

* itf_detail: how many ITF main-draw matches of 2018-2024 without a box score does Flashscore give one?
* women_itf_qualifying: does Flashscore hold women's ITF qualifying? Its records carry no round, so this
  is read from 2024, where Sackmann lists the qualifying: Flashscore rows linking to Sackmann's 2024
  women's ITF qualifying matches, and Flashscore 2025-26 rows of ITF women's events linking to no known
  main-draw match.

Usage:
    ./python.sh src/eda/gap_sources/flashscore_itf.py [--workers 6] [--rescan]

Writes data/raw/gap_sources/flashscore_itf.parquet (the extracted rows; gitignored) and
data/studies/gap_sources/flashscore_itf_summary.json.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

FLASH = PROJECT_ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff" / "flashscore_full"
EXTRACT = PROJECT_ROOT / "data" / "raw" / "gap_sources" / "flashscore_itf.parquet"
OUT = PROJECT_ROOT / "data" / "studies" / "gap_sources" / "flashscore_itf_summary.json"
MATCHES = PROJECT_ROOT / "data" / "studies" / "data_map" / "matches.parquet"
ITF_NAME = re.compile(r'"tournament_name":\s*"([MW])\d{2,3}\b')
FIELDS = ["match_id", "match_date", "tournament_name", "home_player", "away_player", "home_player_name",
          "away_player_name", "home_player_slug", "away_player_slug", "set_scores", "status"]


def filled(value) -> bool:
    return value not in (None, "", [], {})


def scan(path_text: str) -> list[dict]:
    path = Path(path_text)
    opener = gzip.open if path.suffix == ".gz" else open
    rows = []
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not ITF_NAME.search(line[:4000] if len(line) > 4000 else line):
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            row = {k: r.get(k) for k in FIELDS}
            row["has_stats"] = filled(r.get("home_aces"))
            row["has_serve_points"] = filled(r.get("home_first_serve_points_won")) or filled(r.get("home_service_points_won"))
            row["file"] = path.name
            rows.append(row)
    return rows


def extract(workers: int) -> pd.DataFrame:
    files = sorted(str(p) for p in FLASH.glob("flashscore_full_*.jsonl*") if "checkpoint" not in p.name)
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for n, part in enumerate(pool.map(scan, files), 1):
            rows.extend(part)
            print(f"{n}/{len(files)} files, {len(rows):,} ITF rows", flush=True)
    frame = pd.DataFrame(rows)
    frame["has_stats"] = frame["has_stats"].astype(bool)
    frame = (frame.sort_values("has_stats", ascending=False).drop_duplicates("match_id").reset_index(drop=True))
    EXTRACT.parent.mkdir(parents=True, exist_ok=True)
    frame.astype({c: str for c in frame.columns if c not in ("has_stats", "has_serve_points")}).to_parquet(EXTRACT, index=False)
    return frame


def surname_first(name: str) -> str:
    """Flashscore writes 'Navarro E.': the surname words before the initial."""
    words = [w for w in re.split(r"\s+", str(name or "").strip()) if w and not re.fullmatch(r"[A-Z]\.(-[A-Z]\.)?", w)]
    return " ".join(words)


def link(fs: pd.DataFrame, m: pd.DataFrame) -> pd.Series:
    """uid of the data map match each Flashscore row is (same tour, both surnames, date -10..+21 days), or NaN."""
    from src.eda.data_map.measure import surname_key, pair_key
    fs = fs.copy()
    fs["tour"] = fs["tournament_name"].str[0].map({"M": "M", "W": "W"})
    fs["d"] = pd.to_datetime(fs["match_date"], format="%Y%m%d", errors="coerce")
    fs["k1"] = fs["home_player"].map(surname_first).map(surname_key)
    fs["k2"] = fs["away_player"].map(surname_first).map(surname_key)
    fs["pair"] = pair_key(fs["k1"], fs["k2"])
    u = m[["uid", "tour", "d", "name1", "name2", "level"]].copy()
    u["pair"] = pair_key(u["name1"].map(surname_key), u["name2"].map(surname_key))
    cand = fs.reset_index()[["index", "tour", "pair", "d"]].merge(u.rename(columns={"d": "d_u"}), on=["tour", "pair"])
    delta = (cand["d"] - cand["d_u"]).dt.days
    cand = cand[(delta >= -21) & (delta <= 10)]           # a match is played on or after its tournament's start
    cand = cand.assign(score=(cand["d"] - cand["d_u"]).dt.days.abs()).sort_values(["index", "score"])
    best = cand.drop_duplicates("index").set_index("index")["uid"]
    return fs.index.to_series().map(best)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--rescan", action="store_true")
    args = parser.parse_args()
    fs = pd.read_parquet(EXTRACT) if EXTRACT.exists() and not args.rescan else extract(args.workers)
    fs["has_stats"] = fs["has_stats"].astype(str).str.lower().eq("true")
    fs["year"] = pd.to_numeric(fs["match_date"].astype(str).str[:4], errors="coerce")
    m = pd.read_parquet(MATCHES)
    fs["uid"] = link(fs, m)
    lv = m.set_index("uid")
    fs["linked_level"] = fs["uid"].map(lv["level"])
    fs["linked_best"] = fs["uid"].map(lv["best"])
    fs["tour"] = fs["tournament_name"].str[0]
    out = {"rows": int(len(fs)), "by_tour_year": {}, "itf_detail_fill": {}, "women_qualifying": {}}
    for (tour, year), g in fs.groupby(["tour", "year"]):
        if 2018 <= year <= 2026:
            out["by_tour_year"][f"{tour}|{int(year)}"] = {
                "matches": int(len(g)), "with_stats": int(g["has_stats"].sum()),
                "linked": int(g["uid"].notna().sum()),
                "linked_levels": {str(k): int(v) for k, v in g["linked_level"].value_counts().items()}}
    # itf_detail: gap = ITF main draw 2018-2024 whose best grain is 'result'
    gap = m[m["level"].eq("ITF") & m["year"].between(2018, 2024) & m["best"].eq("result")]
    filled_uids = set(fs.loc[fs["has_stats"] & fs["uid"].isin(gap["uid"]), "uid"])
    for (tour, year), g in gap.groupby(["tour", "year"]):
        out["itf_detail_fill"][f"{tour}|{int(year)}"] = {
            "gap": int(len(g)), "flashscore_listed": int(g["uid"].isin(set(fs["uid"].dropna())).sum()),
            "flashscore_with_stats": int(g["uid"].isin(filled_uids).sum())}
    out["itf_detail_fill"]["total"] = {"gap": int(len(gap)), "flashscore_with_stats": len(filled_uids)}
    # women's qualifying: 2024 Sackmann ITFQ rows found in Flashscore; 2025-26 rows of W events linking nowhere
    wq24 = m[m["tour"].eq("W") & m["level"].eq("ITFQ") & m["year"].eq(2024)]
    out["women_qualifying"]["sackmann_2024_itfq"] = int(len(wq24))
    out["women_qualifying"]["of_them_in_flashscore"] = int(wq24["uid"].isin(set(fs["uid"].dropna())).sum())
    w = fs[fs["tour"].eq("W")]
    for year in (2024, 2025, 2026):
        g = w[w["year"].eq(year)]
        out["women_qualifying"][f"w_{year}"] = {"rows": int(len(g)), "linked_main": int(g["linked_level"].eq("ITF").sum()),
                                               "linked_qual": int(g["linked_level"].eq("ITFQ").sum()),
                                               "unlinked": int(g["uid"].isna().sum())}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Flashscore's "Average 1st serve speed" in the Hugging Face handoff's Flashscore crawl: which events carry it, and
whether it equals the official speeds the project holds. Reads no match result.

Source: data/raw/public_dump/atp_pipeline_handoff/flashscore_{full,gql_stats}/ (atlas-polybot/atp-pipeline-handoff,
commit ea3d94d7, downloaded 25 Sep 2026). Year files and the statistics files name the event by slug; head-to-head
records by tournament name. Links to Stage 0: data/studies/match_timing/links/flashscore.parquet.

Agreement: for linked matches that the shot-level study also times (stage1_match_stats spd1_n / spd1_d), the two
players' Flashscore averages are compared with the held means of first serves in, without orienting the players:
the match mean's difference, and the per-player error of the better of the two pairings.

Run: ./python.sh src/eda/serve_speed_sources/flashscore_crawl.py
Writes data/studies/serve_speed_sources/flashscore_crawl_events.csv and flashscore_agreement.json
"""
from __future__ import annotations

import gzip
import json
import multiprocessing as mp
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
HANDOFF = ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff"
OUT = ROOT / "data" / "studies" / "serve_speed_sources"
FS_LINK = ROOT / "data" / "studies" / "match_timing" / "links" / "flashscore.parquet"
SHOT = ROOT / "data" / "studies" / "shot_level"
DATE = re.compile(r'"match_date":\s*"(\d{8})"')
FIRST = 2024_01_01


def kmh(v) -> float:
    """A speed in km/h; Flashscore's "0 km/h" placeholders (most 2024 records) and values outside the shot-level
    adapters' 40-270 km/h range are missing."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*km/h", str(v or ""))
    x = float(m.group(1)) if m else np.nan
    return x if 40.0 < x <= 270.0 else np.nan


def speeds(r: dict) -> tuple[float, float]:
    h, a = kmh(r.get("home_average_1st_serve_speed")), kmh(r.get("away_average_1st_serve_speed"))
    if np.isfinite(h) and np.isfinite(a):
        return h, a
    sj = r.get("stats_detail_json") or ""
    if "Average 1st serve speed" not in sj:
        return np.nan, np.nan
    try:
        items = json.loads(sj)
    except ValueError:
        return np.nan, np.nan
    period = None
    for it in items:
        period = it.get("SE", period)
        if period == "Match" and str(it.get("SG", "")).lower() == "average 1st serve speed":
            return kmh(it.get("SH")), kmh(it.get("SI"))
    return np.nan, np.nan


def scan(path: str) -> list[tuple]:
    rows = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = DATE.search(line)
            if not m or int(m.group(1)) < FIRST:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            sj = r.get("stats_detail_json") or ""
            has_stats = (bool(sj) and sj not in ("[]", "null")) or bool(r.get("home_aces"))
            h, a = speeds(r) if "erve speed" in line else (np.nan, np.nan)
            rows.append((r.get("match_id"), r.get("match_date"), r.get("tournament_name") or r.get("tournament_slug"),
                         has_stats, h, a))
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(str(p) for d in ("flashscore_full", "flashscore_gql_stats") for p in (HANDOFF / d).glob("*.jsonl.gz"))
    with mp.Pool(6) as pool:
        parts = pool.map(scan, files, chunksize=1)
    d = pd.DataFrame([r for p in parts for r in p], columns=["fs_id", "date", "event", "has_stats", "h1", "a1"])
    d["timed"] = d["h1"].notna() & d["a1"].notna()
    d = d.sort_values("timed").drop_duplicates("fs_id", keep="last")
    d["year"] = d["date"].str[:4].astype(int)
    ev = (d.groupby(["year", "event"]).agg(matches=("fs_id", "size"), with_stats=("has_stats", "sum"),
                                           with_speed=("timed", "sum")).reset_index())
    ev["speed_share_of_stats"] = (ev["with_speed"] / ev["with_stats"].where(ev["with_stats"] > 0)).round(3)
    ev.sort_values(["year", "with_speed", "matches"], ascending=[True, False, False]).to_csv(
        OUT / "flashscore_crawl_events.csv", index=False)

    link = pd.read_parquet(FS_LINK, columns=["match_id", "source_key"]).rename(columns={"source_key": "fs_id"})
    t = d[d["timed"]].merge(link, on="fs_id", how="inner")
    st = pd.read_parquet(SHOT / "stage1_match_stats.parquet", columns=["match_id", "side", "spd1_n", "spd1_d",
                                                                        "spd1_src"])
    st = st[st["spd1_d"] > 0].assign(v=lambda x: x["spd1_n"] / x["spd1_d"])
    w = st.pivot_table(index="match_id", columns="side", values="v").dropna()
    w = w.join(st.groupby("match_id")["spd1_src"].first())
    k = t.merge(w, left_on="match_id", right_index=True, how="inner")
    k["diff_match_mean"] = (k["h1"] + k["a1"]) / 2 - (k["A"] + k["B"]) / 2
    k["pair_err"] = np.minimum(abs(k["h1"] - k["A"]) + abs(k["a1"] - k["B"]),
                               abs(k["h1"] - k["B"]) + abs(k["a1"] - k["A"])) / 2
    agree = (k.groupby("spd1_src").agg(matches=("diff_match_mean", "size"),
                                       mean_diff_kmh=("diff_match_mean", "mean"),
                                       sd_diff_kmh=("diff_match_mean", "std"),
                                       median_player_err_kmh=("pair_err", "median"),
                                       p90_player_err_kmh=("pair_err", lambda x: x.quantile(0.9)))
             .round(3).reset_index())
    summary = {"records_from_2024": int(len(d)), "with_stats": int(d["has_stats"].sum()),
               "with_speed": int(d["timed"].sum()), "with_speed_linked_to_stage0": int(len(t)),
               "with_speed_by_year": d[d["timed"]].groupby("year").size().to_dict(),
               "agreement_with_held": agree.to_dict(orient="records"),
               "note": "positive diff = Flashscore faster; the crawl reached matches through head-to-head pages, so "
                       "its counts are a lower bound on what Flashscore serves"}
    (OUT / "flashscore_agreement.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    sys.exit(main())

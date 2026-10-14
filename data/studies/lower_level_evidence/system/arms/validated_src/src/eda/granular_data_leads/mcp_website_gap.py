"""Granular data leads: which Match Charting Project charts the dump does not hold.

Tennis Abstract's chart index (https://www.tennisabstract.com/charting/meta.html, downloaded byte-exact on
23 Sep 2026 by src/eda/point_shot_sources/link_public_sources.py, receipt in
data/studies/point_shot_sources/public_source_receipts.json) links every published chart. The dump holds the
GitHub export of the Match Charting Project (data/dump/points/match_charting_project/), which is not the same
set: the export leaves out charts that the website publishes, and the dump staged only the 2010s and 2020s
point files, so export matches from before 2010 have metadata but no points.

Each chart page on the website embeds a `pointlog` table that describes every shot of every point in words
(serve direction, fault type, each stroke's side, direction and depth, error type, outcome, rally length),
so a website-only chart is a shot-by-shot record the dump lacks.

Writes to data/studies/granular_data_leads/:
* tennis_abstract_chart_gap.csv: one row per chart id on the index or in the export, with where it is held.
* tennis_abstract_chart_gap.json: counts by year and tour.
Run: ./python.sh src/eda/granular_data_leads/mcp_website_gap.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
INDEX = ROOT / "data" / "raw" / "point_shot_sources" / "tennis_abstract" / "meta.html"
MCP = ROOT / "data" / "dump" / "points" / "match_charting_project"
OUT = ROOT / "data" / "studies" / "granular_data_leads"
CHART_URL = "https://www.tennisabstract.com/charting/{}.html"
# 20260921-W-Sao_Paulo-F-Kaitlin_Quevedo-Nadia_Podoroska: date, tour, event, round, player 1, player 2
CHART_ID = re.compile(r'href="(\d{8}-[MW]-[^"/]+?)\.html"')


def export_ids(folder: str) -> set[str]:
    ids: set[str] = set()
    for f in (MCP / folder).glob("*.parquet"):
        ids |= set(pq.read_table(f, columns=["match_id"]).column("match_id").to_pylist())
    return ids


def main() -> None:
    html = INDEX.read_text(encoding="utf-8", errors="replace")
    totals = re.search(r"<b>([\d,]+)</b> matches!.*?<b>([\d,]+)</b> points!.*?<b>([\d,]+)</b> shots!", html, re.S)
    site = set(CHART_ID.findall(html))
    meta, points = export_ids("metadata"), export_ids("points")

    rows = []
    for cid in sorted(site | meta):
        date, tour, *rest = cid.split("-")
        rows.append({
            "chart_id": cid,
            "date": f"{date[:4]}-{date[4:6]}-{date[6:]}",
            "tour": "men" if tour == "M" else "women",
            "on_website": cid in site,
            "in_export": cid in meta,
            "points_in_dump": cid in points,
            "url": CHART_URL.format(cid) if cid in site else "",
        })
    df = pd.DataFrame(rows)
    df["year"] = df["date"].str[:4].astype(int)
    OUT.mkdir(parents=True, exist_ok=True)
    df.drop(columns="year").to_csv(OUT / "tennis_abstract_chart_gap.csv", index=False)

    website_only = df[df.on_website & ~df.in_export]
    no_points = df[df.in_export & ~df.points_in_dump]
    summary = {
        "index_file": str(INDEX.relative_to(ROOT)).replace("\\", "/"),
        "index_totals_claimed": dict(zip(["matches", "points", "shots"], totals.groups())) if totals else None,
        "chart_ids_on_website": len(site),
        "chart_ids_in_export_metadata": len(meta),
        "chart_ids_with_points_in_dump": len(points),
        "website_only": len(website_only),
        "export_only": int((df.in_export & ~df.on_website).sum()),
        "in_export_without_points_in_dump": len(no_points),
        "website_only_by_year_and_tour": {
            str(y): g.groupby("tour").size().to_dict() for y, g in website_only.groupby("year")
        },
        "export_without_points_by_decade": no_points.groupby(no_points.year // 10 * 10).size()
        .rename(lambda d: f"{d}s").to_dict(),
    }
    (OUT / "tennis_abstract_chart_gap.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if not k.endswith("year_and_tour")}, indent=1))


if __name__ == "__main__":
    main()

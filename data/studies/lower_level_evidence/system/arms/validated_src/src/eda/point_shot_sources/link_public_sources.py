"""Point/shot sources study, step 3: link the free downloadable point/shot sources the dump does not hold.

Three public sources, each downloaded byte-exact with a receipt (URL, time, bytes, SHA-256) to
data/raw/point_shot_sources/ (gitignored) and searched for the ten sampled players:

* Sackmann's `tennis_pointbypoint` (server/returner point strings, all men's levels down to Futures).
  The original repository returns 404; two third-party copies survive on GitHub:
  ppaulojr/tennis_pointbypoint (April 2015, matches 2011 to early 2015) and
  sportsdatascience/setuppoints, folder data/ (January 2018, matches 2011-2015 and January 2017).
* Tennis Abstract's Match Charting Project index (https://www.tennisabstract.com/charting/meta.html; robots.txt
  allows /charting/). It lists every published chart; the dump holds the GitHub export, which lags it.

A row links to an official match of the same player when the opponent's name agrees
(career_coverage.build_coverage.name_score >= 1) and its date lies 12 days before to 20 days after the
official tournament date; round agreement and the smaller gap break ties.

Writes public_source_rows.csv (the ten players' rows found, with link) and public_source_receipts.json
to data/studies/point_shot_sources/.
Run: ./python.sh src/eda/point_shot_sources/link_public_sources.py
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "point_shot_sources"
OUT = ROOT / "data" / "studies" / "point_shot_sources"
REFERENCE = ROOT / "data" / "studies" / "career_coverage" / "reference_record.csv"
sys.path.insert(0, str(ROOT / "src" / "eda" / "career_coverage"))
from build_coverage import name_score  # noqa: E402

MEN_FILES = [f"pbp_matches_{lv}_{dr}_{part}.csv" for lv in ("atp", "ch", "fu") for dr in ("main", "qual")
             for part in ("archive", "current")]
COPIES = {
    "pbp_copy_2015": ("https://raw.githubusercontent.com/ppaulojr/tennis_pointbypoint/"
                      "3d3bfc602ed0551352f9e984c1f51240811c8db6/{f}"),
    "pbp_copy_2018": ("https://raw.githubusercontent.com/sportsdatascience/setuppoints/"
                      "e2ad89cb0f795fac85155f866831b753a3968a48/data/{f}"),
}
CHART_INDEX = "https://www.tennisabstract.com/charting/meta.html"
USER_AGENT = "tennis-predictions-research/1.0 (point/shot source study; python-requests)"
LINK_WINDOW = (-12, 20)
LEVEL = {("ATP", "Main"): "Tour main draw", ("ATP", "Qual"): "Tour qualifying",
         ("CH", "Main"): "Challenger main draw", ("CH", "Qual"): "Challenger qualifying",
         ("FU", "Main"): "ITF main draw", ("FU", "Qual"): "ITF qualifying"}


def fetch(url: str, dest: Path, receipts: list) -> Path | None:
    """Download once; later runs reuse the file and its first receipt."""
    if not dest.exists():
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
        if r.status_code != 200:
            receipts.append({"url": url, "status": r.status_code, "retrieved_at": _now()})
            return None
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
    data = dest.read_bytes()
    receipts.append({"url": url, "status": 200, "file": dest.relative_to(ROOT).as_posix(), "bytes": len(data),
                     "sha256": hashlib.sha256(data).hexdigest(),
                     "file_time": dt.datetime.fromtimestamp(dest.stat().st_mtime, dt.timezone.utc).isoformat()})
    return dest


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def pbp_rows(copy: str, path: Path, players: dict) -> list[dict]:
    """The sampled players' matches in one point-string file."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    rows = []
    for _, r in df.iterrows():
        for code, name in players.items():
            first, _, last = name.partition(" ")
            for me, opp in (("server1", "server2"), ("server2", "server1")):
                if name_score(first, last, r[me]) == 3:
                    points = len(re.sub(r"[^SRAD]", "", r["pbp"]))
                    rows.append({"source": copy, "code": code, "player": name,
                                 "date": dt.datetime.strptime(r["date"], "%d %b %y").strftime("%Y-%m-%d"),
                                 "event": r["tny_name"], "level": LEVEL.get((r["tour"], r["draw"]), ""),
                                 "round": "", "opponent": r[opp], "score": r["score"], "points": points,
                                 "file": path.name, "row_id": r.get("pbp_id", "")})
    return rows


def chart_rows(path: Path, players: dict, export_ids: set) -> list[dict]:
    html = path.read_text(encoding="utf-8", errors="replace")
    rows = []
    for link in sorted(set(re.findall(r'href="(\d{8}-M-[^"]+)\.html"', html))):
        parts = link.split("-")
        for code, name in players.items():
            tag = name.replace(" ", "_")
            if tag in parts[4:]:
                opp = next(p for p in parts[4:] if p != tag).replace("_", " ")
                rows.append({"source": "tennis_abstract_chart", "code": code, "player": name,
                             "date": f"{link[:4]}-{link[4:6]}-{link[6:8]}", "event": parts[2].replace("_", " "),
                             "level": "", "round": parts[3], "opponent": opp, "score": "", "points": "",
                             "file": "meta.html", "row_id": link,
                             "in_dump_export": link in export_ids})
    return rows


def link(rows: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, r in rows.iterrows():
        d = pd.Timestamp(r["date"])
        cand = ref[(ref["code"] == r["code"]) & (ref["event_date"] >= d - pd.Timedelta(days=LINK_WINDOW[1])) &
                   (ref["event_date"] <= d - pd.Timedelta(days=LINK_WINDOW[0]))].copy()
        cand["s"] = [name_score(f, l, r["opponent"]) for f, l in zip(cand["opp_first"], cand["opp_last"])]
        cand = cand[cand["s"] >= 1]
        cand["r"] = (cand["round"] == r["round"]).astype(int)
        cand["gap"] = (d - cand["event_date"]).dt.days.abs()
        cand = cand.sort_values(["s", "r", "gap"], ascending=[False, False, True])
        hit = cand.iloc[0] if len(cand) else None
        out.append({**r.to_dict(), "ref_id": hit["ref_id"] if hit is not None else "",
                    "ref_level": hit["level"] if hit is not None else "",
                    "ref_event": hit["event_name"] if hit is not None else "",
                    "link": "linked" if hit is not None else "not on the official record"})
    return pd.DataFrame(out)


def main():
    ref = pd.read_csv(REFERENCE, dtype=str, keep_default_na=False)
    ref = ref[ref["is_bye"] != "True"].copy()
    ref["event_date"] = pd.to_datetime(ref["event_date"])
    players = ref.drop_duplicates("code").set_index("code")["player"].to_dict()
    receipts, rows = [], []
    for copy, pattern in COPIES.items():
        for f in MEN_FILES:
            path = fetch(pattern.format(f=f), RAW / copy / f, receipts)
            if path is not None:
                rows += pbp_rows(copy, path, players)
    meta = pd.concat([pd.read_parquet(f, columns=["match_id"]) for f in
                      glob.glob(str(ROOT / "data/dump/points/match_charting_project/metadata/*.parquet"))])
    index = fetch(CHART_INDEX, RAW / "tennis_abstract" / "meta.html", receipts)
    rows += chart_rows(index, players, set(meta["match_id"].astype(str)))
    linked = link(pd.DataFrame(rows), ref)
    # a match found in both point-string copies is one match
    linked["duplicate_of_other_copy"] = (linked["source"].str.startswith("pbp_copy") &
                                         linked.duplicated(subset=["code", "date", "opponent"], keep="last"))
    OUT.mkdir(parents=True, exist_ok=True)
    linked.to_csv(OUT / "public_source_rows.csv", index=False)
    (OUT / "public_source_receipts.json").write_text(json.dumps(receipts, indent=1), encoding="utf-8")
    print(linked.groupby(["source", "link"]).size())
    print(linked[linked["source"] == "tennis_abstract_chart"][["row_id", "in_dump_export", "link"]].to_string())


if __name__ == "__main__":
    main()

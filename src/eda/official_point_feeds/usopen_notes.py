"""US Open checks beyond the shared SlamTracker checks (slamtracker_checks.py --site usopen).

Reads the staged tables in data/dump/points/usopen/ and the dump's Polymarket catalogue and price histories; writes
to data/studies/official_point_feeds/:

    usopen_notes.json               the totals below
    usopen_clock_vs_polymarket.csv  every 2026 singles and qualifying match matched to a Polymarket market: the
                                    history's first and last point, the listing's time, the market's scheduled
                                    start, the first time a side's price reached 0.98, and the market's close

What it measures:
    * Hollow point rows: numbered history rows without a PointWinner (and, in practice, without a score, time or
      sentence). The shared checks count them as points; here they are counted per match, and a history whose points
      are mostly hollow is named.
    * The draw's statsLevel against the match statistics file's own statsLevel, for the "H" matches whose history
      holds no point.
    * Which clock is right in 2026. The draw's `epoch` (the listing's time) is the match end in 2022-2025, but in
      2026 it sits five hours before the last point in most matches. Polymarket's markets are an independent clock:
      each has a scheduled start and a close time, and its price history shows when a side first reached 0.98
      (often near the end, but earlier in one-sided matches). Markets are matched to matches by both players' last
      names in the event title, US Open events of 18 Aug-15 Sep 2026 only; a match whose names fit more than one
      market, or none, is left out. The quartiles of each measure are compared between the matches whose listing
      is five hours early and those whose listing agrees with the history.

Usage:
    ./python.sh src/eda/official_point_feeds/usopen_notes.py
"""
from __future__ import annotations

import glob
import json
import sys
import unicodedata
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import feeds as F  # noqa: E402

SOURCE = "usopen"
POLYMARKET = P.DUMP_ROOT.parent / "odds" / "polymarket"
DECIDED = 0.98                     # a side's price at or above this: the market has decided the match
FIVE_HOURS = (4.9 * 3600, 5.1 * 3600)


def table(name: str, columns=None) -> pd.DataFrame:
    return pq.read_table(P.dump_path(SOURCE, f"{name}.parquet"), columns=columns).to_pandas()


def ascii_lower(text) -> str:
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()


def hollow_points(points: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Numbered history rows without a PointWinner of 1 or 2, per match."""
    pts = points[points["PointNumber"].astype(str).str.isdigit()].copy()
    pts["has_winner"] = pts["PointWinner"].isin(["1", "2"])
    by = (pts.groupby(["year", "event", "match_id"])
          .agg(points=("has_winner", "size"), with_winner=("has_winner", "sum")).reset_index())
    by["hollow"] = by["points"] - by["with_winner"]
    hollow = by[by["hollow"] > 0].sort_values(["hollow", "year", "match_id"], ascending=[False, True, True])
    mostly = hollow[hollow["hollow"] > hollow["points"] / 2]
    return {"points": int(len(pts)), "points_with_a_winner": int(pts["has_winner"].sum()),
            "hollow_rows": int((~pts["has_winner"]).sum()), "matches_with_hollow_rows": int(len(hollow)),
            "histories_mostly_hollow": [f"{y} {e} {m}: {w} of {n} points with a winner"
                                        for y, e, m, n, w in zip(mostly["year"], mostly["event"], mostly["match_id"],
                                                                 mostly["points"], mostly["with_winner"])],
            "hollow_by_match": {f"{y} {e} {m}": int(h) for y, e, m, h in
                                zip(hollow["year"], hollow["event"], hollow["match_id"], hollow["hollow"])}}, by


def stats_levels(matches: pd.DataFrame, by_match: pd.DataFrame) -> dict:
    """The draw's statsLevel against the statistics file's, overall and for "H" matches without a point."""
    st = table("statistics", ["year", "match_id", "section", "key", "value"])
    level = (st[(st["section"] == "meta") & (st["key"] == "statsLevel")][["year", "match_id", "value"]]
             .rename(columns={"value": "file_level"}))
    m = matches.merge(level, on=["year", "match_id"], how="left")
    m["file_level"] = m["file_level"].fillna("(no statistics)")
    points = by_match.set_index(["year", "match_id"])["points"]
    m["points"] = [int(points.get((y, i), 0)) for y, i in zip(m["year"], m["match_id"])]
    empty_h = m[(m["stats_level"] == "H") & (m["points"] == 0)]
    return {"draw_by_file_level": {f"{d}|{f}": int(n) for (d, f), n in m.groupby(["stats_level", "file_level"]).size().items()},
            "H_without_points": int(len(empty_h)),
            "H_without_points_by_year_event_file_level": {f"{y} {e}|{f}": int(n) for (y, e, f), n in
                                                          empty_h.groupby(["year", "event", "file_level"]).size().items()},
            "H_without_points_courts": dict(empty_h["entry.courtName"].value_counts()),
            "H_without_points_other_feeds": {f: dict(empty_h[f"{f}_outcome"].value_counts())
                                             for f in ("stats", "distance", "livel2w", "prematch_l2w")}}


def clock_check(matches: pd.DataFrame, points: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    pts = points[points["PointNumber"].astype(str).str.isdigit()].copy()
    pts["end"] = pd.to_numeric(pts["EpochTimeEnd"], errors="coerce")
    pts = pts[pts["end"] > 0]
    span = pts.groupby(["year", "match_id"])["end"].agg(first_end="min", last_end="max").reset_index()
    m = matches.merge(span, on=["year", "match_id"])
    m["listing"] = pd.to_numeric(m["entry.epoch"], errors="coerce") / 1000
    m["last_minus_listing_h"] = (m["last_end"] - m["listing"]) / 3600

    def band(h):
        if pd.isna(h):
            return "no listing time"
        if abs(h) <= 1 / 6:
            return "within 10 minutes"
        if FIVE_HOURS[0] <= h * 3600 <= FIVE_HOURS[1]:
            return "last point 5 h after the listing"
        return "listing later" if h < 0 else "last point later otherwise"

    m["listing_band"] = m["last_minus_listing_h"].map(band)
    by_year = {f"{y}|{b}": int(n) for (y, b), n in m.groupby(["year", "listing_band"]).size().items()}

    events = pq.read_table(POLYMARKET / "event_index.parquet",
                           columns=["id", "title", "sport_date", "bucket_slug", "closedTime_derived"]).to_pandas()
    events = events[events["sport_date"].between("2026-08-18", "2026-09-15")
                    & events["title"].str.contains("US Open", na=False)
                    & events["bucket_slug"].isin(["slam_main", "slam_qualifying"])].copy()
    events["title_key"] = events["title"].map(ascii_lower)
    singles = m[(m["year"] == "2026") & m["event"].isin(["MS", "WS", "MQ", "WQ"])]
    rows, ambiguous = [], 0
    for _, r in singles.iterrows():
        a, b = ascii_lower(r["entry.team1.lastNameA"]), ascii_lower(r["entry.team2.lastNameA"])
        hit = events[events["title_key"].str.contains(a, regex=False) & events["title_key"].str.contains(b, regex=False)]
        if len(hit) != 1:
            ambiguous += len(hit) > 1
            continue
        h = hit.iloc[0]
        rows.append({"event": r["event"], "match_id": r["match_id"], "polymarket_event": h["id"], "title": h["title"],
                     "first_point_end": int(r["first_end"]), "last_point_end": int(r["last_end"]),
                     "listing": r["listing"], "listing_band": r["listing_band"],
                     "market_start": pd.Timestamp(h["sport_date"]).timestamp(),
                     "market_closed": (pd.Timestamp(h["closedTime_derived"]).timestamp()
                                       if pd.notna(h["closedTime_derived"]) else None)})
    joined = pd.DataFrame(rows)
    files = sorted(glob.glob(str(POLYMARKET / "price_history" / "slam_*" / "2026-0[89].parquet")))
    prices = pd.concat([pq.read_table(f, columns=["event_id", "t", "p"]).to_pandas() for f in files])
    prices["t"], prices["p"] = pd.to_numeric(prices["t"]), pd.to_numeric(prices["p"])
    decided = prices[prices["p"] >= DECIDED].groupby("event_id")["t"].min().rename("market_decided")
    joined = joined.merge(decided, left_on="polymarket_event", right_index=True, how="left")
    for col in ("market_decided", "market_closed"):
        joined[f"{col}_minus_last_point_min"] = (joined[col] - joined["last_point_end"]) / 60
        joined[f"{col}_minus_listing_min"] = (joined[col] - joined["listing"]) / 60
    joined["first_point_minus_market_start_min"] = (joined["first_point_end"] - joined["market_start"]) / 60
    summary = {"listing_vs_last_point_by_year": by_year,
               "polymarket_2026": {"matches_with_points": int(len(singles)), "matched": int(len(joined)),
                                   "matches_fitting_several_markets": int(ambiguous), "by_listing_band": {}}}
    measures = ["market_decided_minus_last_point_min", "market_decided_minus_listing_min",
                "market_closed_minus_last_point_min", "market_closed_minus_listing_min",
                "first_point_minus_market_start_min"]
    for band_name, group in joined.groupby("listing_band"):
        decided_n = group["market_decided"].notna()
        summary["polymarket_2026"]["by_listing_band"][band_name] = {
            "matches": int(len(group)), "with_a_decided_price": int(decided_n.sum()),
            **{k: {q: round(float(group[k].quantile(v)), 1) for q, v in (("p25", .25), ("median", .5), ("p75", .75))}
               for k in measures},
            "share_of_decided_markets_decided_within_30_min_before_the_last_point": round(float(
                group.loc[decided_n, "market_decided_minus_last_point_min"].between(-30, 0).mean()), 3)
            if decided_n.any() else None}
    return summary, joined


def run() -> dict:
    P.configure_stdout()
    matches = table("matches")
    points = table("points", ["year", "event", "match_id", "row", "PointNumber", "PointWinner", "EpochTimeEnd"])
    out = {"source": SOURCE, "checked_at": P.utc_now_iso()}
    out["hollow"], by_match = hollow_points(points)
    out["stats_levels"] = stats_levels(matches, by_match)
    out["clock"], joined = clock_check(matches, points)
    F.STUDY_ROOT.mkdir(parents=True, exist_ok=True)
    path = F.STUDY_ROOT / f"{SOURCE}_clock_vs_polymarket.csv"
    joined.to_csv(path, index=False, encoding="utf-8")
    P.log(f"[{SOURCE}] wrote {P.rel(path)} ({len(joined)} rows)")
    path = F.STUDY_ROOT / f"{SOURCE}_notes.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    P.log(f"[{SOURCE}] wrote {P.rel(path)}")
    return out


if __name__ == "__main__":
    run()

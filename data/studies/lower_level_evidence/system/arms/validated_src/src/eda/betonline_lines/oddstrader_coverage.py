"""Coverage and checks of the OddsTrader BetOnline lines. Writes counts only: no price leaves data/dump/.

Reads the staged tables of src/ingest/oddstrader.py and the tennis-data.co.uk dump, and writes to
data/studies/betonline_lines/:
    oddstrader_coverage.csv  completed singles, and those with an opening line, a last line and both, by tour,
                             year, book and market
    oddstrader_checks.json   the run's receipts; when opening and last lines were recorded against the listed
                             start; price sanity (overround, one-sided lines); SportsBetting.ag against BetOnline;
                             and how many tennis-data main-tour matches 2024-2026 were found, with BetOnline lines

Run: ./python.sh src/eda/betonline_lines/oddstrader_coverage.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DUMP = ROOT / "data" / "dump" / "odds" / "oddstrader"
RECEIPTS = ROOT / "data" / "raw" / "oddstrader" / "_receipts.jsonl"
TENNIS_DATA = ROOT / "data" / "dump" / "odds" / "tennis_data_couk"
OUT = ROOT / "data" / "studies" / "betonline_lines"
BOOKS = ("BetOnline", "SportsBetting.ag")
MARKETS = ("match_winner", "total_games")


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    events = pd.read_parquet(DUMP / "events.parquet")
    lines = pd.read_parquet(DUMP / "lines.parquet")
    events["dt"] = pd.to_datetime(events["dt_ms"], unit="ms", utc=True)
    events["year"] = events["dt"].dt.year
    lines["tim"] = pd.to_datetime(lines["tim_ms"], unit="ms", utc=True)
    return events, lines


def played_singles(events: pd.DataFrame) -> pd.DataFrame:
    """Singles that were played: status 'complete' or 'retired' (not canceled, scheduled or in progress)."""
    return events[events["singles"] & events["es"].isin(["complete", "retired"])]


def has(lines: pd.DataFrame, book: str, market: str, kind: str) -> set:
    sel = lines[(lines["book"] == book) & (lines["market"] == market) & (lines["kind"] == kind)]
    return set(sel["eid"])


def coverage(events: pd.DataFrame, lines: pd.DataFrame) -> pd.DataFrame:
    singles = played_singles(events)
    rows = []
    for (tour, year), group in singles.groupby(["tour", "year"]):
        eids = set(group["eid"])
        for book in BOOKS:
            for market in MARKETS:
                opened, last = has(lines, book, market, "open") & eids, has(lines, book, market, "last") & eids
                rows.append({"tour": tour, "year": year, "book": book, "market": market,
                             "played_singles": len(eids), "with_open": len(opened), "with_last": len(last),
                             "with_both": len(opened & last), "share_both": round(len(opened & last) / len(eids), 4)})
    return pd.DataFrame(rows)


def side_pairs(lines: pd.DataFrame, book: str, market: str, kind: str) -> pd.DataFrame:
    """One row per event: the line time and the implied-probability sum of its two sides (NaN if one-sided)."""
    sel = lines[(lines["book"] == book) & (lines["market"] == market) & (lines["kind"] == kind)]
    grouped = sel.groupby("eid").agg(sides=("partid", "nunique"), tim=("tim", "max"),
                                     overround=("pri", lambda p: float((1 / p).sum())), iof=("iof", "max"))
    grouped.loc[grouped["sides"] != 2, "overround"] = np.nan
    return grouped


def quantiles(series: pd.Series, qs=(0.01, 0.1, 0.5, 0.9, 0.99)) -> dict:
    series = series.dropna()
    return {f"p{int(q * 100)}": round(float(series.quantile(q)), 4) for q in qs} if len(series) else {}


def timing_and_sanity(events: pd.DataFrame, lines: pd.DataFrame) -> dict:
    singles = played_singles(events).set_index("eid")
    out = {}
    for market in MARKETS:
        opened = side_pairs(lines, "BetOnline", market, "open").join(singles["dt"], how="inner")
        last = side_pairs(lines, "BetOnline", market, "last").join(singles["dt"], how="inner")
        lead_h = (opened["dt"] - opened["tim"]).dt.total_seconds() / 3600
        after_min = (last["tim"] - last["dt"]).dt.total_seconds() / 60
        bins = pd.cut(after_min, [-np.inf, 0, 30, 180, 720, np.inf],
                      labels=["at or before listed start", "0-30 min after", "30 min-3 h after", "3-12 h after",
                              "over 12 h after"])
        out[market] = {
            "opening_hours_before_listed_start": quantiles(lead_h),
            "openings_after_listed_start": int((lead_h < 0).sum()),
            "last_line_vs_listed_start": {k: int(v) for k, v in bins.value_counts().sort_index().items()},
            "last_lines_marked_off_board": int(last["iof"].fillna(False).astype(bool).sum()),
            "last_lines": len(last),
            "overround_open": quantiles(opened["overround"]),
            "overround_last": quantiles(last["overround"]),
            "one_sided_open": int((opened["sides"] != 2).sum()),
            "one_sided_last": int((last["sides"] != 2).sum()),
            "overround_outside_1_to_1.15": int(((last["overround"] < 1) | (last["overround"] > 1.15)).sum()
                                               + ((opened["overround"] < 1) | (opened["overround"] > 1.15)).sum()),
        }
    return out


def sister_brand(lines: pd.DataFrame) -> dict:
    """Same event, market, side and kind: does SportsBetting.ag quote BetOnline's price, line and time?"""
    keys = ["eid", "market", "partid", "kind"]
    bol = lines[lines["book"] == "BetOnline"].set_index(keys)
    sb = lines[lines["book"] == "SportsBetting.ag"].set_index(keys)
    both = bol[["ap", "adj", "tim_ms"]].join(sb[["ap", "adj", "tim_ms"]], how="inner", rsuffix="_sb")
    out = {}
    for kind in ("open", "last"):
        part = both[both.index.get_level_values("kind") == kind]
        out[kind] = {"pairs": len(part),
                     "same_price_and_line": int(((part["ap"] == part["ap_sb"]) & (part["adj"] == part["adj_sb"])).sum()),
                     "same_time": int((part["tim_ms"] == part["tim_ms_sb"]).sum())}
    return out


# --------------------------------------------------------------------------------------
# tennis-data.co.uk main-tour matches found on OddsTrader
# --------------------------------------------------------------------------------------
def norm(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", text.lower())


def tennis_data_surname(name: str) -> str:
    """'Bautista Agut R.' -> 'bautistaagut', 'Struff J.L.' -> 'struff': drop the trailing initials."""
    tokens = str(name or "").split()
    while len(tokens) > 1 and ("." in tokens[-1] or len(tokens[-1]) <= 2):
        tokens.pop()
    return norm(" ".join(tokens))


def same_player(a: str, b: str) -> bool:
    return bool(a) and bool(b) and (a == b or (min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a))))


def tennis_data_matches() -> pd.DataFrame:
    frames = []
    for path in sorted(TENNIS_DATA.glob("*/*/202[4-6].parquet")):
        d = pd.read_parquet(path, columns=["Date", "Winner", "Loser", "Tournament"])
        d["tour"], d["tier"] = path.parts[-3].upper(), path.parts[-2]
        frames.append(d)
    m = pd.concat(frames, ignore_index=True)
    m["date"] = pd.to_datetime(m["Date"]).dt.normalize()
    m["w"], m["l"] = m["Winner"].map(tennis_data_surname), m["Loser"].map(tennis_data_surname)
    return m


def link_tennis_data(events: pd.DataFrame, lines: pd.DataFrame) -> dict:
    singles = events[events["singles"]].copy()
    singles["day"] = singles["dt"].dt.tz_convert(None).dt.normalize()
    singles["a"], singles["h"] = singles["away_last"].map(norm), singles["home_last"].map(norm)
    by_day = defaultdict(list)
    for row in singles[["tour", "day", "eid", "a", "h"]].itertuples(index=False):
        by_day[(row.tour, row.day)].append(row)
    both = has(lines, "BetOnline", "match_winner", "open") & has(lines, "BetOnline", "match_winner", "last")
    td = tennis_data_matches()
    found, ambiguous = [], 0
    for row in td.itertuples(index=False):
        hits = set()
        for shift in (-1, 0, 1, 2):  # listed start in UTC can fall a day either side of tennis-data's date
            for ev in by_day.get((row.tour, row.date + pd.Timedelta(days=shift)), []):
                if ((same_player(row.w, ev.a) and same_player(row.l, ev.h))
                        or (same_player(row.w, ev.h) and same_player(row.l, ev.a))):
                    hits.add(ev.eid)
        ambiguous += len(hits) > 1
        found.append(min(hits) if hits else None)
    td["eid"] = found
    td["year"] = td["date"].dt.year
    td["betonline_both"] = td["eid"].isin(both)
    summary = (td.groupby(["tour", "year"])
                 .agg(matches=("eid", "size"), found=("eid", lambda s: int(s.notna().sum())),
                      betonline_open_and_last=("betonline_both", "sum")))
    total = td.agg({"eid": lambda s: int(s.notna().sum())})
    return {"by_tour_year": {f"{t} {y}": {k: int(v) for k, v in r.items()} for (t, y), r in summary.iterrows()},
            "matches": len(td), "found": int(total["eid"]), "betonline_open_and_last": int(td["betonline_both"].sum()),
            "ambiguous": int(ambiguous),
            "not_found_by_tier": {k: int(v) for k, v in td[td["eid"].isna()]["tier"].value_counts().items()}}


def close_flags() -> dict:
    """From the per-match table: played singles with an opening and a close, and how many closes are uncertain."""
    m = pd.read_parquet(DUMP / "betonline_matches.parquet")
    played = m[m["es"].isin(["complete", "retired"])]
    out = {}
    for prefix, market in (("mw", "match_winner"), ("tg", "total_games")):
        has_open, has_close = played[f"{prefix}_open_utc"].notna(), played[f"{prefix}_close_utc"].notna()
        uncertain = played[f"{prefix}_close_uncertain"].astype(bool)
        out[market] = {"played_singles": len(played), "with_close": int(has_close.sum()),
                       "close_uncertain": int(uncertain.sum()),
                       "open_uncertain": int(played[f"{prefix}_open_uncertain"].astype(bool).sum()),
                       "clean_open_and_close": int((has_open & has_close & ~uncertain
                                                    & ~played[f"{prefix}_open_uncertain"].astype(bool)).sum())}
    return out


def receipts_summary() -> dict:
    receipts = [json.loads(line) for line in RECEIPTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    times = sorted(r["retrieved_at"] for r in receipts)
    return {"requests": len(receipts), "errors": sum(1 for r in receipts if r.get("error")),
            "events_responses": sum(1 for r in receipts if r["name"].startswith("events/")),
            "lines_responses": sum(1 for r in receipts if r["name"].startswith("lines/")),
            "bytes": sum(r.get("bytes") or 0 for r in receipts), "first": times[0], "last": times[-1]}


def main() -> None:
    events, lines = load()
    OUT.mkdir(parents=True, exist_ok=True)
    cov = coverage(events, lines)
    cov.to_csv(OUT / "oddstrader_coverage.csv", index=False)
    checks = {"receipts": receipts_summary(),
              "events": {"listed": len(events), "singles": int(events["singles"].sum()),
                         "status_of_singles": {k: int(v) for k, v in events[events["singles"]]["es"].value_counts().items()}},
              "timing_and_sanity_betonline": timing_and_sanity(events, lines),
              "betonline_close_flags": close_flags(),
              "sportsbetting_vs_betonline": sister_brand(lines),
              "tennis_data_main_tour_2024_2026": link_tennis_data(events, lines)}
    (OUT / "oddstrader_checks.json").write_text(json.dumps(checks, indent=1), encoding="utf-8")
    view = cov[(cov["book"] == "BetOnline")].pivot_table(index=["tour", "year"], columns="market",
                                                          values=["played_singles", "with_both"], aggfunc="sum")
    print(view.to_string())
    print(json.dumps({k: v for k, v in checks.items() if k != "tennis_data_main_tour_2024_2026"}, indent=1)[:4000])
    link = checks["tennis_data_main_tour_2024_2026"]
    print({k: link[k] for k in ("matches", "found", "betonline_open_and_last", "ambiguous")})


if __name__ == "__main__":
    main()

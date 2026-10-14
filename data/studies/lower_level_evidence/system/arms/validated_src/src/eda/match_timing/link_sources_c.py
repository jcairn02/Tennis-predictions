"""Match timing, sources C: exact match days (and start times where present) attached to Stage 0's matches from six
sources earlier studies downloaded and partly linked, so that the leak-proof timeline (timing.py) can use real days
instead of tournament weeks.

Sources (one module each, src/eda/match_timing/srcc_*.py; srcc_common.py holds the linker and schema, srcc_tz.py the
venue time zones):
    tennis_data   Stage 1's tennis-data.co.uk links (stage1_odds.parquet), days as published
    wta_api       WTA API match lists 2019-2026 and the umpire's event logs (first point, venue zone)
    sofascore     SofaScore events of three collections (careers, ATP editions 2025-26, AO/RG 2022-26), listed start
    slam_feeds    Australian Open match centre and archived draws, Wimbledon and US Open SlamTracker (first point)
    tdi           TDI Tennis Results, ATP and Challenger, June-September 2026 and Wayback ids (first point)
    sirgenkii     SirGenkii/infotennis dumps, ATP January-April 2025: no day or time held, file left empty

Writes data/studies/match_timing/links/:
    <source>.parquet             one row per linked Stage 0 match: match_id, source, source_key, date_local,
                                 start_utc, date_basis ('local' | 'utc_date'), link_method, score_agrees, round_agrees
    <source>.csv                 every in-scope source row left unlinked, with why (and ambiguous candidates)
    sources_c_link_counts.csv    coverage by source x tour x level x qualifying x year, against Stage 0's matches
    sources_c_summary.json       per source: rows read, linked, ambiguous, unlinked, methods and checks; agreement with
                                 tennis-data's days and between the sources; days outside a plausible window
Reads only files on disk; no network.

Run: ./python.sh src/eda/match_timing/link_sources_c.py [--sources wta_api,sofascore] [--workers 3]
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.eda.match_timing import srcc_common as K  # noqa: E402

MODULES = {"tennis_data": "srcc_tennis_data", "wta_api": "srcc_wta", "sofascore": "srcc_sofascore",
           "slam_feeds": "srcc_slams", "tdi": "srcc_tdi", "sirgenkii": "srcc_sirgenkii"}
SUMMARY = K.LINKS / "sources_c_summary.json"
COUNTS = K.LINKS / "sources_c_link_counts.csv"
MAX_WORKERS = 3


def run_source(name: str) -> dict:
    t = time.time()
    mod = importlib.import_module(f"src.eda.match_timing.{MODULES[name]}")
    out = mod.run()
    out["seconds"] = round(time.time() - t, 1)
    K.log(f"[{name}] done: {out.get('linked', 0):,} linked in {out['seconds']} s")
    return out


def load_links(names) -> pd.DataFrame:
    frames = []
    for n in names:
        f = K.LINKS / f"{n}.parquet"
        if f.exists():
            frames.append(pd.read_parquet(f))
    lk = pd.concat(frames, ignore_index=True)
    lk["date_local"] = pd.to_datetime(lk["date_local"])
    lk["start_utc"] = pd.to_datetime(lk["start_utc"], utc=True)
    return lk


def coverage(lk: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    dims = ["tour", "level", "qualifying", "year"]
    den = m.groupby(dims).size().rename("stage0_matches")
    rows = []
    groups = [(s, g) for s, g in lk.groupby("source")]
    groups.append(("any_source_c", lk.drop_duplicates("match_id")))
    groups.append(("any_except_tennis_data", lk[lk["source"] != "tennis_data"].drop_duplicates("match_id")))
    for s, g in groups:
        c = g[["match_id"]].merge(m[["match_id"] + dims], on="match_id").groupby(dims).size().rename("linked")
        t = pd.concat([den, c], axis=1).fillna(0).reset_index()
        t = t[t["linked"] > 0] if s not in ("any_source_c", "any_except_tennis_data") else t
        t.insert(0, "source", s)
        rows.append(t)
    out = pd.concat(rows, ignore_index=True)
    out["stage0_matches"] = out["stage0_matches"].astype(int)
    out["linked"] = out["linked"].astype(int)
    out["linked_pct"] = (100 * out["linked"] / out["stage0_matches"].where(out["stage0_matches"] > 0)).round(1)
    return out


def share(d: pd.Series) -> dict:
    n = int(len(d))
    if not n:
        return {"matches": 0}
    a = d.abs()
    return {"matches": n, "same_day": int((a == 0).sum()), "same_day_pct": round(100 * float((a == 0).mean()), 2),
            "one_day_apart": int((a == 1).sum()), "within_one_day_pct": round(100 * float((a <= 1).mean()), 2),
            "more_than_one_day": int((a > 1).sum()),
            "differences_days": {str(int(k)): int(v) for k, v in d.value_counts().sort_index().items()}}


def agreement_with_td(lk: pd.DataFrame) -> dict:
    td = lk[lk["source"] == "tennis_data"][["match_id", "date_local"]].rename(columns={"date_local": "td_date"})
    out, worst = {}, []
    for s, g in lk[lk["source"] != "tennis_data"].groupby("source"):
        j = g.merge(td, on="match_id")
        j["diff"] = (j["date_local"] - j["td_date"]).dt.days
        out[s] = {"overall": share(j["diff"]),
                  "by_date_basis": {b: share(x["diff"]) for b, x in j.groupby("date_basis")}}
        worst.append(j)
    w = pd.concat(worst, ignore_index=True) if worst else pd.DataFrame()
    if len(w):
        w = w.assign(a=w["diff"].abs()).sort_values(["a", "source", "match_id"], ascending=[False, True, True])
        w = w.head(20)[["source", "match_id", "source_key", "date_local", "td_date", "diff", "date_basis", "start_utc",
                        "link_method"]]
        w["date_local"] = w["date_local"].dt.strftime("%Y-%m-%d")
        w["td_date"] = w["td_date"].dt.strftime("%Y-%m-%d")
        w["start_utc"] = w["start_utc"].dt.strftime("%Y-%m-%d %H:%M").fillna("")
    return {"by_source": out, "worst_20": w.to_dict("records") if len(w) else []}


def td_clock(lk: pd.DataFrame) -> dict:
    """Which clock tennis-data's day follows: against matches whose start is known, its day compared with the venue's
    day, the UTC day and the London day of the start, overall and where the venue's day differs from London's."""
    td = lk[lk["source"] == "tennis_data"][["match_id", "date_local"]].rename(columns={"date_local": "td_date"})
    x = lk[(lk["source"] != "tennis_data") & lk["start_utc"].notna() & lk["date_basis"].eq("local")]
    x = x.sort_values("source").drop_duplicates("match_id").merge(td, on="match_id")
    if x.empty:
        return {}
    x["utc_day"] = x["start_utc"].dt.tz_convert(None).dt.normalize()
    x["london_day"] = x["start_utc"].dt.tz_convert("Europe/London").dt.tz_localize(None).dt.normalize()
    differ = x[x["date_local"] != x["london_day"]]

    def rates(d):
        return {"matches": int(len(d)),
                "td_equals_venue_day_pct": round(100 * float((d["td_date"] == d["date_local"]).mean()), 2) if len(d) else None,
                "td_equals_utc_day_pct": round(100 * float((d["td_date"] == d["utc_day"]).mean()), 2) if len(d) else None,
                "td_equals_london_day_pct": round(100 * float((d["td_date"] == d["london_day"]).mean()), 2) if len(d) else None}
    west = differ[differ["london_day"] > differ["date_local"]]
    east = differ[differ["london_day"] < differ["date_local"]]
    return {"note": "matches with a known start (first point or listed start) and a venue day from a known zone; "
                    "tennis-data's day compared with three calendars",
            "all": rates(x), "venue_day_differs_from_london_day": rates(differ),
            "of_which_london_day_later (Americas evening)": rates(west),
            "of_which_london_day_earlier (Asia-Pacific morning)": rates(east)}


def pairwise(lk: pd.DataFrame) -> list:
    """Agreement of days between every two sources on the matches both link."""
    names = sorted(lk["source"].unique())
    out = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            x = lk[lk["source"] == a][["match_id", "date_local", "date_basis"]].merge(
                lk[lk["source"] == b][["match_id", "date_local", "date_basis"]], on="match_id", suffixes=("_a", "_b"))
            if x.empty:
                continue
            d = (x["date_local_a"] - x["date_local_b"]).dt.days
            both_local = x["date_basis_a"].eq("local") & x["date_basis_b"].eq("local")
            r = {"a": a, "b": b, **{k: v for k, v in share(d).items() if k != "differences_days"},
                 "both_local": share(d[both_local]).get("same_day_pct")}
            out.append(r)
    return out


def flags(lk: pd.DataFrame, m: pd.DataFrame) -> dict:
    x = lk.merge(m[["match_id", "tour", "level", "qualifying", "tournament_date", "round"]], on="match_id")
    x["off"] = (x["date_local"] - pd.to_datetime(x["tournament_date"])).dt.days
    w = [K.flag_window(lv, q) for lv, q in zip(x["level"], x["qualifying"])]
    x["lo"], x["hi"] = [a for a, _ in w], [b for _, b in w]
    x["early"] = x["off"] < x["lo"]
    x["late"] = x["off"] > x["hi"]
    x["by"] = np.where(x["early"], x["lo"] - x["off"], np.where(x["late"], x["off"] - x["hi"], 0))
    f = x[x["early"] | x["late"]]
    worst = f.sort_values(["by", "source", "match_id"], ascending=[False, True, True]).head(20)
    worst = worst.assign(date_local=worst["date_local"].dt.strftime("%Y-%m-%d"),
                         tournament_date=pd.to_datetime(worst["tournament_date"]).dt.strftime("%Y-%m-%d"))
    return {"rule": "a day earlier than the tournament date - 1 (qualifying: - 10 at a Slam, - 4 elsewhere), or later "
                    "than + 15 (Slam main draw), + 13 (1000s and team events), + 8 (Finals), + 9 (other main draws), "
                    "+ 1 (qualifying); srcc_common.flag_window",
            "by_source": {s: {"links": int(len(g)), "early": int(g["early"].sum()), "late": int(g["late"].sum())}
                          for s, g in x.groupby("source")},
            "by_source_level": f.groupby(["source", "level", "qualifying"]).agg(
                early=("early", "sum"), late=("late", "sum")).reset_index().to_dict("records"),
            "worst_20": worst[["source", "match_id", "source_key", "level", "qualifying", "round", "tournament_date",
                               "date_local", "off", "date_basis", "link_method"]].to_dict("records")}


def multi_day(lk: pd.DataFrame) -> dict:
    t = lk["link_method"].str.extract(r"last_point_day\+(\d+)")[0]
    return {s: {"matches_finishing_on_a_later_local_day": int(g.notna().sum()),
                "by_days": g.dropna().astype(int).value_counts().sort_index().to_dict()}
            for s, g in t.groupby(lk["source"])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", default=",".join(MODULES))
    ap.add_argument("--workers", type=int, default=MAX_WORKERS)
    args = ap.parse_args()
    names = [s.strip() for s in args.sources.split(",") if s.strip()]
    bad = [n for n in names if n not in MODULES]
    if bad:
        raise SystemExit(f"unknown sources: {bad}")
    workers = max(1, min(MAX_WORKERS, args.workers))
    K.LINKS.mkdir(parents=True, exist_ok=True)
    K.log(f"running {names} with {workers} worker process(es)")
    results = {}
    if workers == 1:
        for n in names:
            results[n] = run_source(n)
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            fut = {n: ex.submit(run_source, n) for n in names}
            for n, f in fut.items():
                results[n] = f.result()
    # the combined view always covers every source file on disk
    all_names = [n for n in MODULES if (K.LINKS / f"{n}.parquet").exists()]
    lk = load_links(all_names)
    m = pd.read_parquet(K.C.MATCHES, columns=["match_id", "tour", "year", "level", "qualifying", "tournament_date",
                                               "round"])
    cov = coverage(lk, m)
    cov.to_csv(COUNTS, index=False)
    old = {}
    if SUMMARY.exists():
        try:
            old = json.loads(SUMMARY.read_text(encoding="utf-8")).get("sources", {})
        except (ValueError, OSError):
            old = {}
    sources = {n: results.get(n, old.get(n)) for n in all_names}
    summary = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "script": "src/eda/match_timing/link_sources_c.py",
        "schema": K.LINK_COLUMNS,
        "linking_rule": " ".join(K.__doc__.split("The identity rule")[1].split()),
        "sources": sources,
        "links_per_source": lk.groupby("source").size().to_dict(),
        "matches_with_any_source_c_day": int(lk["match_id"].nunique()),
        "coverage_file": str(COUNTS.relative_to(K.ROOT)),
        "coverage_by_source_tour_level_qualifying": cov.groupby(["source", "tour", "level", "qualifying"]).agg(
            stage0_matches=("stage0_matches", "sum"), linked=("linked", "sum")).reset_index().to_dict("records"),
        "coverage_by_source_tour_level_qualifying_year": cov[cov["linked"] > 0].to_dict("records"),
        "agreement_with_tennis_data": agreement_with_td(lk),
        "tennis_data_clock": td_clock(lk),
        "agreement_between_sources": pairwise(lk),
        "days_outside_plausible_window": flags(lk, m),
        "matches_spanning_days": multi_day(lk),
    }
    K.jdump(summary, SUMMARY)
    K.log(f"wrote {SUMMARY.relative_to(K.ROOT)} and {COUNTS.relative_to(K.ROOT)}")
    for n in all_names:
        s = sources.get(n) or {}
        print(f"  {n:12s} read {s.get('rows_read', '?'):>8} linked {s.get('linked', '?'):>7} "
              f"ambiguous {s.get('ambiguous', '?'):>4} unlinked {s.get('unlinked', '?'):>7}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The P7 trigger check (role G's plan, docs/studies/lower_level_evidence/system/P7_plan.md, section 1): has a SofaScore
gap landed, completely? Counting only: targets, links, fetch outcomes, box scores per tour and year, the link check's
verdicts and the gap's last run. No outcome is used (the link check compares the winner and set scores with the
official result only to confirm that two records are one match, as the timeline's linker does).

Reads (written by the collector and verify_links.py; data/studies/gap_downloads/):
    sofascore_<gap>_matches.csv[.gz]      one row per frozen target: event_id (linked), stats_status (200 / 404 / empty
                                          = not fetched yet), stats_full_box, pbp_verdict
    sofascore_<gap>_link_check.json       verify_links.py's verdicts
    sofascore_<gap>_summary.json          the gap's last run (finished_at; runs.jsonl's lines do not name their gap)
Writes data/studies/lower_level_evidence/system/p7_plan/trigger_<gap>.json and prints the verdict.

Run: ./python.sh data/studies/lower_level_evidence/system/p7_plan/scripts/p7_trigger_check.py --gap itf_detail
     (also --gap itf_points_2025_2026; any other SofaScore gap for a rehearsal)
Pass (the plan's thresholds, fixed before P7 lands):
    complete      every linked target has a statistics outcome (200 or 404): pending == 0, and the gap's summary shows
                  a finished last run, not "stopped" (a block, a budget)
    yield         box scores (stats_full_box) on >= 90% of the targets of each year 2019-2024 and >= 75% in 2018
                  (the plan's expectation: ~98% overall, 2018 the weakest year); for itf_points_2025_2026 >= 80%
                  (the collection plan's stop rule)
    links         verify_links "agrees" >= 98% of linked targets; "winner differs" <= 0.1%
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("C:/Users/zerom/Documents/Tennis-predictions")
GAPS = ROOT / "data" / "studies" / "gap_downloads"
OUT = ROOT / "data" / "studies" / "lower_level_evidence" / "system" / "p7_plan"
YIELD_MIN = {"default": 0.90, 2018: 0.75}
YIELD_2025_26 = 0.80
AGREE_MIN, WINNER_DIFF_MAX = 0.98, 0.001


def read_targets(gap: str) -> pd.DataFrame:
    for name in (f"sofascore_{gap}_matches.csv.gz", f"sofascore_{gap}_matches.csv"):
        p = GAPS / name
        if p.exists():
            return pd.read_csv(p, low_memory=False)
    raise SystemExit(f"no frozen target list for gap {gap} in {GAPS} (the collector freezes it at its first run)")


def last_run(gap: str) -> dict | None:
    """The gap's last run, from the collector's per-gap summary (runs.jsonl's lines do not name their gap)."""
    p = GAPS / f"sofascore_{gap}_summary.json"
    if not p.exists():
        return None
    s = json.loads(p.read_text(encoding="utf-8"))
    return {"started_at": s.get("started_at"), "finished_at": s.get("finished_at"), "stopped": s.get("stopped"),
            "matches_selected": s.get("matches_selected"), "receipts_with_errors": s.get("receipts_with_errors")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gap", required=True)
    a = ap.parse_args()
    t = read_targets(a.gap)
    t["linked"] = t["event_id"].notna()
    st = pd.to_numeric(t.get("stats_status"), errors="coerce")
    t["fetched"] = st.isin([200.0, 404.0])
    t["box"] = t.get("stats_full_box", pd.Series(False, index=t.index)).astype(str).str.lower().eq("true")
    t["pending"] = t["linked"] & ~t["fetched"]
    by = (t.groupby(["tour", "year"]).agg(targets=("uid", "size"), linked=("linked", "sum"),
                                          fetched=("fetched", "sum"), box=("box", "sum"),
                                          pending=("pending", "sum")).reset_index())
    by["box_share"] = (by["box"] / by["targets"]).round(4)
    lc_path = GAPS / f"sofascore_{a.gap}_link_check.json"
    lc = json.loads(lc_path.read_text(encoding="utf-8")) if lc_path.exists() else None
    verdicts = (lc or {}).get("verdicts", {})
    n_link = sum(v for k, v in verdicts.items() if k != "not linked") or 1
    agree = verdicts.get("agrees", 0) / n_link
    wdiff = verdicts.get("winner differs", 0) / n_link
    run = last_run(a.gap)
    yearly = {}
    for (tour, year), g in by.groupby(["tour", "year"]):
        need = YIELD_2025_26 if a.gap == "itf_points_2025_2026" else YIELD_MIN.get(int(year), YIELD_MIN["default"])
        yearly[f"{tour}|{int(year)}"] = {"box_share": float(g["box_share"].iloc[0]), "need": need,
                                         "ok": bool(g["box_share"].iloc[0] >= need)}
    res = {"gap": a.gap, "targets": int(len(t)), "linked": int(t["linked"].sum()), "fetched": int(t["fetched"].sum()),
           "box_scores": int(t["box"].sum()), "pending": int(t["pending"].sum()),
           "by_tour_year": by.to_dict("records"), "yield_by_tour_year": yearly,
           "link_check": {"file_exists": lc is not None, "verdicts": verdicts, "agrees_share": round(agree, 4),
                          "winner_differs_share": round(wdiff, 5)},
           "last_run": run}
    res["complete"] = bool(res["pending"] == 0 and run is not None and run.get("finished_at")
                           and not run.get("stopped"))
    res["yield_ok"] = bool(all(v["ok"] for v in yearly.values()))
    res["links_ok"] = bool(lc is not None and agree >= AGREE_MIN and wdiff <= WINNER_DIFF_MAX)
    res["landed"] = bool(res["complete"] and res["yield_ok"] and res["links_ok"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"trigger_{a.gap}.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(by.to_string(index=False))
    print(json.dumps({k: res[k] for k in ("gap", "targets", "linked", "fetched", "box_scores", "pending", "complete",
                                          "yield_ok", "links_ok", "landed")}, indent=1))
    return 0 if res["landed"] else 1


if __name__ == "__main__":
    sys.exit(main())

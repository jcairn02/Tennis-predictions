"""The summary's numbers for the study "ideas borrowed from UFC-predictions": every feature tried, in both studies,
and how it did, on one scale.

For every scored row of each stage (stageX_ranking.csv, joined to stageX_catalog.json for its family and description)
and for every row of the earlier study (data/studies/predictability_diagnostic/stage4_ranking.csv, grouped into the
families of that study's summary_results.py), the same re-expression as the earlier summary used:

    main_tour_gain   the given-Elo improvement on the main-tour level groups (Grand Slams, Finals, 1000s, 500s, 250s),
                     the per-match average over the walk-forward's level groups (exact, as those are the same model
                     restricted to the group)
    share_of_gap     main_tour_gain over Elo's gap to the closing odds over the row's scored seasons (Stage 1's "room":
                     2013-2026 for rows scored from 2013, 2019-2026 for the women's box-score rows)
    market_share     the given-market improvement over the distance from a coin to the closing odds, the same seasons

A family's verdict per tour is the earlier summary's rule: "helps" if a finding (clears the family-wide line given Elo
and gains in three or more eras) exists, its best version being the finding with the largest main-tour gain; else "no".
Reversed findings (a finding whose sign contradicts the statistic's own direction) are flagged where the earlier study
flagged them; the new rows carry no prior direction, so none is flagged there.

Reads data/studies/ufc_ideas/stage*_ranking.csv, stage*_results.csv, stage*_catalog.json, stage*_summary.json and the
earlier study's summary_results.json and stage4_ranking.csv / stage4_results.csv.
Writes data/studies/ufc_ideas/summary_results.json.
Run: ./python.sh src/eda/ufc_ideas/summary_results.py
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import summary_results as OLD  # noqa: E402
from src.eda.ufc_ideas import common as U  # noqa: E402

OUT = U.OUT / "summary_results.json"
STAGES = ("A", "B", "C", "D", "D_profile")       # stageD_profile_*: Stage D's second part, the statistics profiles
MAIN_TOUR = OLD.MAIN_TOUR
STAGE_TITLES = {"A": "Bradley–Terry and market ratings", "B": "Opponent-adjusted statistics",
                "C": "Schedule, credit and fatigue", "D": "Together", "D_profile": "The statistics profiles together"}


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def level_gains(results_csv: Path, score: str = "elo") -> dict:
    """(tour, id, form) -> the per-match average improvement over the main-tour level groups, given ``score``."""
    r = pd.read_csv(results_csv, low_memory=False)
    if "score" in r.columns:                      # this study's long layout: one row per score
        r = r[(r["score"] == score) & (r["group_kind"] == "level") & r["group_name"].isin(MAIN_TOUR)]
        n_col, imp_col = "n", "imp"
    else:                                         # the earlier study's wide layout: <score>_n, <score>_imp
        r = r[(r["group_kind"] == "level") & r["group_name"].isin(MAIN_TOUR)]
        n_col, imp_col = f"{score}_n", f"{score}_imp"
    r = r[pd.to_numeric(r[imp_col], errors="coerce").notna() & pd.to_numeric(r[n_col], errors="coerce").notna()]
    out = {}
    for (t, i, f), g in r.groupby(["tour", "id", "form"]):
        n = pd.to_numeric(g[n_col]).sum()
        out[(t, i, f)] = float((pd.to_numeric(g[n_col]) * pd.to_numeric(g[imp_col])).sum() / n) if n else None
    return out


def row_record(r: pd.Series, mt: float | None, room: dict, to_market: dict, extra_scores: list[str]) -> dict:
    t = r["tour"]
    w = "2013-2026" if int(r["scored_from"]) == 2013 else "2019-2026"
    rec = {"id": r["id"], "form": r["form"], "name": r["name"], "tour": t, "reading": r["reading"],
           "scored_from": int(r["scored_from"]), "window": w,
           "overall_gain": num(r.get("elo_imp")), "overall_lo": num(r.get("elo_lo")), "overall_hi": num(r.get("elo_hi")),
           "gain_2022_2026": num(r.get("elo_2022-2026")), "gain_2019_2026": num(r.get("elo_2019-2026")),
           "main_tour_gain": mt, "share_of_gap": None if mt is None else mt / room[f"{t}|{w}"],
           "elo_clears_line": bool(r.get("elo_clears_line", False)), "elo_above_band": bool(r.get("elo_above_band", False)),
           "eras_positive": int(r.get("eras_positive", 0) or 0),
           "alone_gain": num(r.get("alone_imp")), "alone_observed": r.get("alone_observed"),
           "market_gain": num(r.get("market_imp")), "market_lo": num(r.get("market_lo")), "market_hi": num(r.get("market_hi")),
           "market_line": bool(r.get("market_clears_line", False)), "market_above_band": bool(r.get("market_above_band", False)),
           "market_share": None if num(r.get("market_imp")) is None else num(r.get("market_imp")) / to_market[f"{t}|{w}"],
           "market_2022_2026": num(r.get("market_2022-2026")),
           "sign": r.get("sign_observed") if isinstance(r.get("sign_observed"), str) else None,
           "coverage": num(r.get("elo_coverage"))}
    for s in extra_scores:
        if f"{s}_imp" in r.index:
            rec[f"{s}_gain"] = num(r.get(f"{s}_imp"))
            rec[f"{s}_clears_line"] = bool(r.get(f"{s}_clears_line", False))
            rec[f"{s}_above_band"] = bool(r.get(f"{s}_above_band", False))
    return rec


def family_summary(rows: list[dict], reversed_ids: set | None = None) -> dict:
    """Per tour: the verdict and the best version, as the earlier summary read a family."""
    out = {}
    for t in C.TOURS:
        rs = [r for r in rows if r["tour"] == t]
        if not rs:
            continue
        for r in rs:
            r["reversed"] = bool(reversed_ids and (r["id"], r["form"]) in reversed_ids)
        # "helps": a finding that also gains on the main tour, where the bookmakers price matches (a finding whose gain
        # comes only from the lower levels is listed, not counted)
        helps = [r for r in rs if r["reading"] == "finding" and not r["reversed"] and r["main_tour_gain"] is not None
                 and r["main_tour_gain"] > 0]
        best = max(helps, key=lambda o: o["main_tour_gain"]) if helps else None
        best_any = max((r for r in rs if r["overall_gain"] is not None), key=lambda o: o["overall_gain"], default=None)
        on_market = [r for r in rs if r["market_line"]]
        out[t] = {"verdict": "helps" if helps else ("reversed" if any(r["reversed"] for r in rs) else "no"),
                  "findings": sum(1 for r in rs if r["reading"] == "finding"), "versions": len(rs),
                  "worse": sum(1 for r in rs if r["reading"] == "worse"),
                  "best": best, "best_any": best_any,
                  "market": max(on_market, key=lambda o: o["market_gain"]) if on_market else None,
                  "market_best_any": max((r for r in rs if r["market_gain"] is not None), key=lambda o: o["market_gain"], default=None)}
    return out


def earlier_families(old: dict, room: dict, to_market: dict) -> list[dict]:
    """The earlier study's 13 families, every version listed, from stage4_ranking.csv and stage4_results.csv."""
    rank = pd.read_csv(U.STAGE4_RANKING)
    lv = level_gains(C.OUT / "stage4_results.csv")
    reversed_ids = set()
    for f in old["plain"]["families"]:
        for t in C.TOURS:
            x = f["tours"].get(t)
            if x:
                reversed_ids |= {(o["id"], o["form"]) for o in x.get("reversed", [])}
    fams = []
    for key, title, what, ids in OLD.FAMILIES:
        rows = [row_record(r, lv.get((r["tour"], r["id"], r["form"])), room, to_market, [])
                for _, r in rank[rank["id"].isin(ids)].iterrows()]
        fams.append({"key": f"earlier:{key}", "title": title, "what": what, "ids": ids, "source": "earlier", "stage": "4",
                     "rows": rows, "tours": family_summary(rows, reversed_ids)})
    return fams


def new_families(room: dict, to_market: dict) -> tuple[list[dict], dict]:
    """The new study's families from each stage's catalog, every version listed."""
    fams, stages = [], {}
    for s in STAGES:
        rank_csv, res_csv, cat_json = U.OUT / f"stage{s}_ranking.csv", U.OUT / f"stage{s}_results.csv", U.OUT / f"stage{s}_catalog.json"
        if not (rank_csv.exists() and cat_json.exists()):
            continue
        rank = pd.read_csv(rank_csv)
        cat = json.loads(cat_json.read_text(encoding="utf-8"))
        entries = cat if isinstance(cat, list) else cat.get("rows", cat.get("catalog", list(cat.values())))
        cat = {}
        for c in entries:                              # a catalog may key its entries by "id" or by "id|form"
            cat.setdefault(c["id"], c)
            if "form" in c:
                cat.setdefault(f'{c["id"]}|{c["form"]}', c)

        def entry(i, form):
            return cat.get(f"{i}|{form}") or cat.get(i) or cat.get(f"{i}|single") or {}
        lv = level_gains(res_csv) if res_csv.exists() else {}
        extra = sorted({c[:-4] for c in rank.columns if c.endswith("_imp") and c[:-4] not in ("alone", "elo", "market")})
        stages[s] = {"title": STAGE_TITLES.get(s, s), "rows": int(len(rank)), "ids": int(rank["id"].nunique()),
                     "extra_scores": extra,
                     "families": sorted({entry(i, f).get("family", "?") for i, f in zip(rank["id"], rank["form"])})}
        by_family: dict = {}
        for _, r in rank.iterrows():
            c = entry(r["id"], r["form"])
            fam = c.get("family", "other")
            rec = row_record(r, lv.get((r["tour"], r["id"], r["form"])), room, to_market, extra)
            rec["description"] = c.get("description", "")
            rec["tuned"] = c.get("tuned", "")
            by_family.setdefault(fam, []).append(rec)
        for fam, rows in by_family.items():
            ids = sorted({r["id"] for r in rows})
            descs = sorted({r["description"] for r in rows if r["description"]})
            # rows of the earlier study re-scored beside a stage's own are references, not new features
            source = "reference" if (fam.lower().startswith("earlier") or fam.lower() in ("elo", "reference")) else "new"
            fams.append({"key": f"{s}:{fam}", "title": fam, "what": "; ".join(descs[:3]), "ids": ids, "source": source,
                         "stage": s, "rows": rows, "tours": family_summary(rows)})
    return fams, stages


def stage_summaries() -> dict:
    """Whatever each stage put in its stageX_summary.json (constants, probes, comparisons), copied for the page."""
    out = {}
    for s in STAGES:
        p = U.OUT / f"stage{s}_summary.json"
        if p.exists():
            try:
                out[s] = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                out[s] = {"error": "unreadable"}
    return out


def main() -> int:
    old = json.loads((C.OUT / "summary_results.json").read_text(encoding="utf-8"))
    room, to_market = old["plain"]["room"], old["plain"]["coin_to_market"]
    earlier = earlier_families(old, room, to_market)
    new_all, stages = new_families(room, to_market)
    new = [f for f in new_all if f["source"] == "new"]
    refs = [f for f in new_all if f["source"] == "reference"]
    fams = new + refs + earlier
    counts = {"new_rows": sum(len(f["rows"]) for f in new), "new_ids": len({i for f in new for i in f["ids"]}),
              "new_families": len(new), "reference_rows": sum(len(f["rows"]) for f in refs),
              "earlier_rows": sum(len(f["rows"]) for f in earlier),
              "earlier_ids": len({i for f in earlier for i in f["ids"]}), "earlier_families": len(earlier),
              "pool": old["quoted"]["stage4"]["pool_evaluation"]}
    # the leaders: the best new versions given Elo (findings) and given the market, per tour
    leaders = {}
    for t in C.TOURS:
        rows = [r for f in new for r in f["rows"] if r["tour"] == t]
        find = sorted([r for r in rows if r["reading"] == "finding"], key=lambda r: -(r["overall_gain"] or -1e9))
        mk = sorted([r for r in rows if r["market_gain"] is not None], key=lambda r: -r["market_gain"])
        leaders[t] = {"given_elo": find[:10], "given_market": mk[:10], "market_line": [r for r in rows if r["market_line"]],
                      "clear_given_elo": [r for r in find if (r["overall_gain"] or 0) >= 1]}
    ladder = json.loads(json.dumps(old["plain"]["ladder"]))
    d_sum = U.OUT / "stageD_summary.json"
    if d_sum.exists():                               # Stage D's rungs: the raw Bradley-Terry and Elo + everything
        dl = json.loads(d_sum.read_text(encoding="utf-8")).get("ladder", {})
        for t in C.TOURS:
            if t in dl:
                if "bt_raw" in dl[t]:
                    ladder[t]["bt"] = dl[t]["bt_raw"]
                if "elo_plus_everything" in dl[t]:
                    ladder[t]["elo_plus_all"] = dl[t]["elo_plus_everything"]
    res = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "families": fams, "stages": stages, "counts": counts, "leaders": leaders,
           "ladder": ladder, "room": room, "coin_to_market": to_market,
           "earlier": {"ladder": old["plain"]["ladder"], "best_market": old["plain"]["best_market"],
                       "candidates": old["plain"]["candidates"], "versions": old["plain"]["versions"],
                       "lines": old["quoted"]["stage4"]["lines"]},
           "stage_summaries": stage_summaries()}
    OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(f"wrote {OUT}: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

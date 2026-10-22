"""The 14 Oct gap-fill rule's coverage condition (C2) for NEW matches, read on a derived candidate of the level-evidence
builder (docs/decisions/2026-10-14-lower-level-gap-fills.md: per tour, level and season it touches, on today's tables,
the history already holds "at least as many matches as it adds" for new matches, or the fill brings the season closer to
its level's median over the other seasons from 2013). src/eda/tennislive_box_fill/conditions.py reads C1 and C2 for
box-score completions; this reads C2 for added matches in that script's terms: the level is the level-evidence study's
bucket (CH, CHQ, ITF ...) and a cell's count is its played matches (completed or retired). C1 (counts the same way)
concerns box scores only: a results-only package has none to compare.

The adds are what the merge would add. The candidate is written as a trial package (additions.package, into
<out>/trial_package/, never the accepted folder). Today's tables as builds see them are the repository's Stage 0 (every
decided repair) merged by additions.merge with every accepted package, then the feed's current snapshot; the same merge
with the trial package listed last among the packages (where --register puts it, before the feed) gives the tables
after. The adds are the matches after and not before: a match the tables already hold under the same id, as the same
meeting, or as the same pair and round within three days is not counted, as the merge skips it. Matches before and not
after (a feed row the package would displace) are counted and reported.
Per tour, level and season the package touches:
    held      the cell's played matches today
    adds      the played matches the merge adds to the cell
    median    the level's median of played matches over the other seasons from 2013 (seasons with at least 30)
    pass      held >= adds, or |held + adds - median| < |held - median|
Counts only: no outcome of any match is read for any choice.

Beside it, the duplicate risk the merge's guard leaves: an added match whose two players (by ids, or by both name keys)
already meet in today's tables within NEAR_DAYS of its tournament date, at any round, level or tournament. The merge
skips only the same id, the same meeting, and the same pair and round within three days; a source that labels a round
or dates an event differently passes it. Listed in <out>/near_pairs.csv for a look by hand.
Writes <out>/c2_new_matches.csv, <out>/near_pairs.csv and <out>/c2_new_matches.json.
Run: ./python.sh src/eda/men_lower_level_fill/conditions_new.py --candidate <derived READY folder> --out <folder>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import additions as AD  # noqa: E402
from src.eda.lower_level_evidence import common as LC  # noqa: E402

TODAY = ROOT / "data" / "studies" / "predictability_diagnostic"          # the repository's Stage 0
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
FIRST, MIN_PLAYED = 2013, 30
PLAYED = ("completed", "retired")
NEAR_DAYS = 14
DECISION = "docs/decisions/2026-10-14-lower-level-gap-fills.md"
SHOW = ["match_id", "tour", "map_level", "tournament_id", "tournament_name", "tournament_date", "round", "score",
        "status"]


def near_pairs(added: pd.DataFrame, added_p: pd.DataFrame, m: pd.DataFrame, mp: pd.DataFrame) -> pd.DataFrame:
    """Each added match beside every match of the tables (m, mp) with the same two players (sorted ids, or both name
    keys) whose tournament date is at most NEAR_DAYS away, at any round, level or tournament."""
    if not len(added):
        return pd.DataFrame()
    d = pd.to_datetime(m["tournament_date"])
    lo = pd.to_datetime(added["tournament_date"]).min() - pd.Timedelta(days=NEAR_DAYS)
    hi = pd.to_datetime(added["tournament_date"]).max() + pd.Timedelta(days=NEAR_DAYS)
    near = m[(d >= lo) & (d <= hi)].reset_index(drop=True)
    a = added.reset_index(drop=True)
    A = AD.pairs(a, added_p[added_p["match_id"].isin(set(a["match_id"]))])
    N = AD.pairs(near, mp[mp["match_id"].isin(set(near["match_id"]))])
    hits = []
    for col in ("ids", "names"):
        j = A.dropna(subset=[col]).merge(N.dropna(subset=[col]), on=col, suffixes=("", "_n"))
        j = j[(j["d"] - j["d_n"]).abs() <= pd.Timedelta(days=NEAR_DAYS)]
        hits.append(j[["i", "i_n"]].assign(by=col))
    h = pd.concat(hits).groupby(["i", "i_n"])["by"].agg(lambda s: "+".join(sorted(set(s)))).reset_index()
    left = a.loc[h["i"], SHOW].reset_index(drop=True).add_prefix("added_")
    right = near.loc[h["i_n"], SHOW].reset_index(drop=True).add_prefix("held_")
    out = pd.concat([left, right], axis=1)
    out["paired_by"] = h["by"].to_numpy()
    return out


def played_cells(m: pd.DataFrame) -> pd.Series:
    """Played matches per tour, level (bucket) and season."""
    p = m[m["status"].isin(PLAYED)]
    k = pd.DataFrame({"tour": p["tour"].astype(str).to_numpy(), "level": LC.bucket(p["map_level"]).astype(str).to_numpy(),
                      "season": p["year"].astype(int).to_numpy()})
    return k.groupby(["tour", "level", "season"]).size()


def c2_cells(held: pd.Series, adds: pd.Series) -> pd.DataFrame:
    """C2 per tour, level and season with adds (both series indexed by tour, level, season: played matches)."""
    tab = pd.concat([held.rename("held"), adds.rename("adds")], axis=1).fillna(0).astype(int)
    tab.index.names = ["tour", "level", "season"]
    tab = tab.reset_index()
    rows = []
    for (tour, lvl), g in tab.groupby(["tour", "level"]):
        for _, r in g[g["adds"] > 0].iterrows():
            other = g[(g["season"] != r["season"]) & (g["season"] >= FIRST) & (g["held"] >= MIN_PLAYED)]["held"]
            med = float(other.median()) if len(other) else float("nan")
            a = bool(r["held"] >= r["adds"])
            b = bool(not np.isnan(med) and abs(r["held"] + r["adds"] - med) < abs(r["held"] - med))
            rows.append({"tour": tour, "level": lvl, "season": int(r["season"]), "held": int(r["held"]),
                         "adds": int(r["adds"]), "median_other_seasons": round(med, 1),
                         "holds_at_least_as_many": a, "closer_to_median": b, "pass": a or b})
    cols = ["tour", "level", "season", "held", "adds", "median_other_seasons", "holds_at_least_as_many",
            "closer_to_median", "pass"]
    return pd.DataFrame(rows, columns=cols).sort_values(["tour", "level", "season"]).reset_index(drop=True)


def trial_package(candidate: Path, out: Path) -> Path:
    """The candidate as a package in <out>/trial_package/ (kept as the reading's evidence; reused when it was written
    from this candidate's manifest)."""
    acc = out / "trial_package"
    p = acc / "trial"
    if (p / "manifest.json").exists():
        man = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
        if man["candidate_manifest_sha256"] != AD.sha256(candidate / "manifest.json"):
            raise SystemExit(f"{p} was written from another candidate; read into another --out")
        return p
    acc.mkdir(parents=True, exist_ok=True)
    return AD.package(candidate, "trial", DECISION, accepted=acc)


def run(candidate: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    pkg = trial_package(candidate, out)
    m = pd.read_parquet(TODAY / "stage0_matches.parquet")
    mp = pd.read_parquet(TODAY / "stage0_match_players.parquet")
    t = pd.read_parquet(TIMING)
    listed = AD.listed()
    n_pk = len(AD.index()["packages"])                   # listed(): the packages, then each feed's snapshot
    m1, mp1, _, rec1 = AD.merge(m, mp, t, listed)
    m2, mp2, _, rec2 = AD.merge(m, mp, t, listed[:n_pk] + [pkg] + listed[n_pk:])
    ids1, ids2 = set(m1["match_id"].astype(str)), set(m2["match_id"].astype(str))
    added = m2[~m2["match_id"].astype(str).isin(ids1)]
    displaced = m1[~m1["match_id"].astype(str).isin(ids2)]
    near = near_pairs(added, mp2, m1, mp1)
    near.to_csv(out / "near_pairs.csv", index=False)
    res = c2_cells(played_cells(m1), played_cells(added))
    res.to_csv(out / "c2_new_matches.csv", index=False)
    pk = pd.read_parquet(pkg / "matches.parquet", columns=["match_id", "tour", "map_level", "status"])
    summary = {"candidate": str(candidate), "trial_package": str(pkg), "decision": DECISION,
               "package_matches": int(len(pk)),
               "package_by_tour_level": pk.assign(level=LC.bucket(pk["map_level"]).astype(str))
               .groupby(["tour", "level"]).size().rename("matches").reset_index().to_dict("records"),
               "merge_onto_today": rec2["packages"][n_pk],
               "added_by_the_merge": int(len(added)),
               "displaced_by_the_merge": int(len(displaced)),
               "near_pairs": {"added_matches_with_one": int(near["added_match_id"].nunique()) if len(near) else 0,
                              "rows": int(len(near)), "within_days": NEAR_DAYS},
               "added_played": int(added["status"].isin(PLAYED).sum()),
               "added_by_tour_level": added.assign(level=LC.bucket(added["map_level"]).astype(str))
               .groupby(["tour", "level"]).size().rename("matches").reset_index().to_dict("records"),
               "today_tables_packages": [r["package"] for r in rec1["packages"]],
               "cells": int(len(res)),
               "cells_failing": res.loc[~res["pass"], ["tour", "level", "season", "held", "adds",
                                                        "median_other_seasons"]].to_dict("records"),
               "adds_in_passing_cells": int(res.loc[res["pass"], "adds"].sum()),
               "adds_in_failing_cells": int(res.loc[~res["pass"], "adds"].sum()),
               "pass": bool(res["pass"].all())}
    (out / "c2_new_matches.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "package_by_tour_level"}, indent=1, default=str))
    print(res.to_string(index=False))
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    return 0 if run(Path(a.candidate), Path(a.out))["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

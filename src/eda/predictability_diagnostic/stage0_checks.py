"""Stage 0 checks: the analysis table against the project's earlier measurements.

1. Match counts by tour x level x year, 2018 on, against data/studies/data_map/coverage_cells.csv.
   The data map counts every source (the WTA's match lists, api-tennis, TDI and others add matches the
   result files lack), so the like-for-like figure is the map's matches first listed by a result file
   (Sackmann or Tennis My Life), from its matches.parquet. Walkovers and blank scores are left out on
   both sides, as the map does.
2. Box-score coverage against serve_stats_available_pct in data/studies/merge_feasibility/summary.json,
   on that study's grouping (tier and qualifying) and years. Its figure is a box score with serve
   points for both players, before any check; Stage 0's before-check and after-check shares are both given.
3. The share of matches side A won (sides come from a hash of the match id): overall, by tour, level,
   year and among evaluation matches, each with a 95% range.
4. The as-of helper on real data: the leakage probe on one season, for the helper and for a
   deliberately leaky feature.

Reads the Stage 0 tables and the two earlier studies' files; writes stage0_checks.json,
stage0_check_counts.csv and stage0_check_box.csv.
Run: ./python.sh src/eda/predictability_diagnostic/stage0_checks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402

MAP_CELLS = ROOT / "data" / "studies" / "data_map" / "coverage_cells.csv"
MAP_MATCHES = ROOT / "data" / "studies" / "data_map" / "matches.parquet"
MERGE_SUMMARY = ROOT / "data" / "studies" / "merge_feasibility" / "summary.json"
RESULT_FILES = {"sackmann", "tml"}


def records(frame: pd.DataFrame) -> list:
    return json.loads(frame.to_json(orient="records"))


def share(k, n) -> dict:
    """A share with its 95% range (normal approximation)."""
    p = k / n if n else float("nan")
    half = 1.96 * np.sqrt(p * (1 - p) / n) if n else float("nan")
    return {"n": int(n), "a_won": int(k), "share": round(p, 4), "lo": round(p - half, 4), "hi": round(p + half, 4)}


def check_counts(m: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cells = pd.read_csv(MAP_CELLS)
    mm = pd.read_parquet(MAP_MATCHES, columns=["tour", "level", "year", "creator"])
    first = cm = mm[mm["creator"].isin(RESULT_FILES)]
    first = cm.groupby(["tour", "level", "year"]).size().rename("map_result_files")
    played = m[~m["status"].eq("walkover") & ~(m["score"].eq("") & m["status_detail"].eq("unknown"))]
    ours = played.assign(tour=played["tour"].map(C.MAP_TOUR), level=played["map_level"]).groupby(
        ["tour", "level", "year"]).size().rename("stage0")
    out = cells[["tour", "level", "year", "matches", "missing_estimate", "filled_by_batch"]].rename(
        columns={"matches": "map_all_sources"}).set_index(["tour", "level", "year"])
    out = out.join(first, how="left").join(ours, how="outer").fillna(0).astype(int).reset_index()
    out = out[out["year"] >= 2018]
    out["diff_vs_result_files"] = out["stage0"] - out["map_result_files"]
    out["diff_pct"] = (100 * out["diff_vs_result_files"] / out["map_result_files"].where(out["map_result_files"] > 0)).round(2)
    out["diff_vs_all_sources"] = out["stage0"] - out["map_all_sources"]
    totals = out.groupby("tour")[["stage0", "map_result_files", "map_all_sources"]].sum()
    big = out[out["diff_pct"].abs().gt(1) & out["diff_vs_result_files"].abs().ge(10)]
    summary = {
        "years": "2018 on", "cells": int(len(out)),
        "explained": explain_counts(played, cm, big),
        "totals_by_tour": records(totals.reset_index()),
        "cells_within_1pct_of_result_files": int(out["diff_pct"].abs().le(1).sum()),
        "cells_with_result_files": int(out["map_result_files"].gt(0).sum()),
        "cells_off_by_more_than_1pct_and_10_matches": records(big.sort_values("diff_vs_result_files")),
        "map_matches_from_other_sources_by_tour": records(
            mm[~mm["creator"].isin(RESULT_FILES)].groupby(["tour", "creator"]).size().rename("matches").reset_index()),
    }
    return out, summary


def explain_counts(played: pd.DataFrame, cm: pd.DataFrame, big: pd.DataFrame) -> dict:
    """Where the larger differences with the data map come from, measured three ways."""
    from src.eda.data_map import measure as M
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "player_name", "side"])
    names = mp.pivot(index="match_id", columns="side", values="player_name")
    x = played.join(names, on="match_id")
    # 1. the map's own de-duplication: the same surname pair in the same round within five days is one match
    x["pair"] = M.pair_key(x["A"].map(M.surname_key), x["B"].map(M.surname_key))
    x = x.sort_values(["tour", "pair", "round", "tournament_date"])
    gap = x.groupby(["tour", "pair", "round"])["tournament_date"].diff().dt.days
    merged = x[x["pair"].notna() & gap.le(5) & (x["year"] >= 2018)]
    by_level = merged.assign(level=merged["map_level"], tour=merged["tour"].map(C.MAP_TOUR)).groupby(
        ["tour", "level"]).size().rename("matches").reset_index()
    # 2. levels: the map calls 'M' events without 'Masters' in the name 250s
    mm = pd.read_parquet(MAP_MATCHES, columns=["tour", "level", "year", "tname", "creator"])
    masters = mm[mm["tname"].str.contains(r"^(?:Monte Carlo|Shanghai)$", regex=True) & mm["level"].eq("T250")]
    # 3. week by week, for the cells off by more than 1% and 10 matches
    ours = played.assign(tour=played["tour"].map(C.MAP_TOUR), level=played["map_level"])
    weeks = []
    mm_d = pd.read_parquet(MAP_MATCHES, columns=["tour", "level", "year", "d", "creator"])
    mm_d = mm_d[mm_d["creator"].isin(RESULT_FILES)]
    mm_d["week"] = mm_d["d"].dt.to_period("W-SUN").dt.start_time
    ours["week"] = ours["tournament_date"].dt.to_period("W-SUN").dt.start_time
    for r in big.itertuples():
        a = ours[(ours["tour"] == r.tour) & (ours["level"] == r.level) & (ours["year"] == r.year)].groupby("week").size()
        b = mm_d[(mm_d["tour"] == r.tour) & (mm_d["level"] == r.level) & (mm_d["year"] == r.year)].groupby("week").size()
        d = a.sub(b, fill_value=0).astype(int)
        d = d[d.ne(0)].reindex(d[d.ne(0)].abs().sort_values(ascending=False).index).head(4)
        weeks.append({"tour": r.tour, "level": r.level, "year": int(r.year),
                      "weeks": {str(k.date()): int(v) for k, v in d.items()}})
    # 4. ITF rows the map's link passes would fold into a match it listed first from Tennis My Life: the same
    #    surname pair within -10..+21 days (its first pass), or one shared surname in the same round within
    #    three days (its third pass). TML lists ATP main draws, their qualifying and Challenger main draws, and
    #    WTA main draws; ITF is never in it.
    x["k1"], x["k2"] = x["A"].map(M.surname_key), x["B"].map(M.surname_key)
    tml_like = x[((x["tour"] == "atp") & x["level"].isin(["GS", "FIN", "T1000", "T500", "T250", "TEAM"]))
                 | ((x["tour"] == "atp") & x["level"].eq("CH") & ~x["qualifying"])
                 | ((x["tour"] == "wta") & x["level"].isin(["GS", "FIN", "T1000", "T500", "T250", "TEAM"]) & ~x["qualifying"])]
    itf = x[x["level"].eq("ITF") & (x["year"] >= 2018)].copy()
    itf["rid"] = np.arange(len(itf))
    pairs = itf[["rid", "tour", "pair", "tournament_date"]].merge(
        tml_like[["tour", "pair", "tournament_date"]].rename(columns={"tournament_date": "d_u"}), on=["tour", "pair"])
    gap = (pairs["tournament_date"] - pairs["d_u"]).dt.days
    first = set(pairs.loc[gap.between(-10, 21), "rid"])
    one = pd.concat([itf[["rid", "tour", "round", "tournament_date"]].assign(key=itf[k]) for k in ("k1", "k2")])
    uni = pd.concat([tml_like[["tour", "round", "tournament_date"]].assign(key=tml_like[k]) for k in ("k1", "k2")])
    cand = one.merge(uni.rename(columns={"tournament_date": "d_u"}), on=["tour", "round", "key"])
    third = set(cand.loc[(cand["tournament_date"] - cand["d_u"]).dt.days.abs().le(3), "rid"])
    caught = itf["rid"].isin(first | third)
    folded = itf[caught].assign(tour=itf.loc[caught, "tour"].map(C.MAP_TOUR)).groupby(["tour", "year"]).size()
    return {"itf_matches_the_map_would_fold_into_a_tml_match_2018_on": records(folded.rename("matches").reset_index()),
            "stage0_matches_the_map_would_merge_by_surname_pair_2018_on": records(by_level),
            "map_monte_carlo_and_shanghai_as_250s": records(
                masters.groupby(["tour", "year", "tname"]).size().rename("matches").reset_index()),
            "largest_weekly_differences_stage0_minus_map": weeks}


TIER = {"GS": "slam", "FIN": "tour", "T1000": "tour", "T500": "tour", "T250": "tour", "CH": "challenger",
        "ITF": "itf", "TEAM": "team"}


def check_box(m: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    ref = json.loads(MERGE_SUMMARY.read_text(encoding="utf-8"))["serve_stats_available_pct"]
    ref = pd.DataFrame(ref).melt(id_vars=["tour", "tier", "is_qual"], var_name="year", value_name="merge_feasibility_pct")
    ref["year"] = ref["year"].astype(int)
    x = m.assign(tier=m["level"].map(TIER), is_qual=m["qualifying"],
                 in_source=~m["box_status"].isin(["blank", "all_zero", "one_side", "partial"]))
    g = x.groupby(["tour", "tier", "is_qual", "year"]).agg(matches=("match_id", "size"), in_source=("in_source", "mean"),
                                                           after_checks=("has_box", "mean")).reset_index()
    g["stage0_in_source_pct"] = (100 * g.pop("in_source")).round(1)
    g["stage0_after_checks_pct"] = (100 * g.pop("after_checks")).round(1)
    out = ref.merge(g, on=["tour", "tier", "is_qual", "year"], how="left")
    out["diff_in_source"] = (out["stage0_in_source_pct"] - out["merge_feasibility_pct"]).round(1)
    comparable = out.dropna(subset=["merge_feasibility_pct", "stage0_in_source_pct"])
    off = comparable[comparable["diff_in_source"].abs().gt(1)]
    summary = {"cells": int(len(comparable)),
               "within_1_point": int(comparable["diff_in_source"].abs().le(1).sum()),
               "off_by_more_than_1_point_by_tier": off["tier"].value_counts().to_dict(),
               "largest_differences": records(comparable.reindex(comparable["diff_in_source"].abs()
                                                                 .sort_values(ascending=False).index).head(10))}
    return out, summary


def check_points_per_game(m: pd.DataFrame) -> dict:
    """Serve points per game in the score, over the box scores kept: where the 4.5 floor of check B9 sits."""
    from src.eda.predictability_diagnostic.stage0_build import score_counts
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "svpt"])
    pts = mp.groupby("match_id")["svpt"].sum(min_count=2)
    ok = m[m["has_box"] & m["status"].eq("completed")]
    games = pd.Series([score_counts(sc, fmt == "short_sets") for sc, fmt in zip(ok["score"], ok["format"])],
                      index=ok["match_id"]).map(lambda c: c[2] + c[3] - c[6])
    ppg = (pts.reindex(games.index) / games.where(games > 0)).dropna()
    q = ppg.quantile([0.001, 0.01, 0.05, 0.5])
    return {"box_scores": int(len(ppg)), "quantiles": {str(k): round(float(v), 2) for k, v in q.items()},
            "below_4_5": int((ppg < 4.5).sum())}


def check_sides(m: pd.DataFrame) -> dict:
    out = {"all": share(int(m["a_won"].sum()), len(m))}
    for col in ("tour", "level", "year"):
        out[f"by_{col}"] = {str(k): share(int(g["a_won"].sum()), len(g)) for k, g in m.groupby(col)}
    ev = m[m["evaluation"]]
    out["evaluation"] = {t: share(int(g["a_won"].sum()), len(g)) for t, g in ev.groupby("tour")}
    out["cells_outside_95pct_range_by_tour_level_year"] = int(sum(
        1 for _, g in m.groupby(["tour", "level", "year"])
        if not (share(int(g["a_won"].sum()), len(g))["lo"] <= 0.5 <= share(int(g["a_won"].sum()), len(g))["hi"])))
    out["cells_by_tour_level_year"] = int(m.groupby(["tour", "level", "year"]).ngroups)
    return out


def check_asof() -> dict:
    mp = C.load_match_players(["match_id", "player_id", "won"])
    season = mp[mp["tournament_date"].between("2024-01-01", "2024-12-31")].copy()
    season["won"] = season["won"].astype(float)

    def leaky(rows):
        r = rows.sort_values(["order", "player_id"])
        return r.groupby("player_id")[["won"]].cumsum().reindex(rows.index)

    return {"slice": "player rows of 2024 tournament weeks", "rows": int(len(season)),
            "asof_helper": C.leak_probe(season, lambda r: C.asof_sums(r, ["won"]), ["won"], n_cuts=20),
            "leaky_running_total_including_the_match": C.leak_probe(season, leaky, ["won"], n_cuts=20)}


def main() -> int:
    m = C.load_matches()
    counts, counts_summary = check_counts(m)
    counts.to_csv(C.OUT / "stage0_check_counts.csv", index=False)
    box, box_summary = check_box(m)
    box.to_csv(C.OUT / "stage0_check_box.csv", index=False)
    result = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
              "counts_vs_data_map": counts_summary, "box_vs_merge_feasibility": box_summary,
              "side_a_won": check_sides(m), "asof_leak_probe": check_asof(),
              "points_per_game_in_kept_box_scores": check_points_per_game(m)}
    (C.OUT / "stage0_checks.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"counts": counts_summary["totals_by_tour"], "a_won": result["side_a_won"]["all"],
                      "asof": result["asof_leak_probe"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

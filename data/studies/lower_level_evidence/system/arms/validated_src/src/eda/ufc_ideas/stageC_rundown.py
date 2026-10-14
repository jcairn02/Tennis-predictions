"""Stage C of the study "ideas borrowed from UFC-predictions", part 3: the rundown. Every Stage C feature, and four
reference rows of the earlier study's Stage 4 re-scored in the same run, through the shared harness
(common.rundown: walk-forward by season, logistic regression without an intercept, alone / given surface Elo / given
the closing odds, 20 shuffled copies per row, the family-wide line, the reading).

    families        strength of schedule (stageC_sos.py), retrospective credit (stageC_sos.py), fatigue
                    (stageC_fatigue.py), earlier study (Stage 4's elo_change_52w, recent_level, played_52w, sets_14d)
    WTA seasons     the Elo-based rows (SoS on Elo, the credit, the references) are scored from 2013; the rows built on
                    box scores, point-by-point records or the Stage 3 ratings (sos_rating, the fatigue rows) from 2019,
                    as the Brief and Stage 4 score the women's box-score rows
    given ratings   afterwards, the two rows with the largest gain given Elo in each of the strength-of-schedule and
                    credit families, per tour, are scored again added to the Stage 3 serve and return ratings through
                    the iid model (p_ratings = expit(rating_matchup|single), the earlier study's strongest feature),
                    against the ratings alone: a second rundown with its own null band and line (the women's from 2019,
                    where Stage 4 scored the ratings). Surface Elo's own log-odds is scored the same way beside them, as
                    the reference for what any results-based strength adds to the point-based ratings

Writes, in data/studies/ufc_ideas/:
    stageC_features.parquet                 the pool, every Stage C column, the reference columns and p_ratings
    stageC_ranking.csv, stageC_results.csv, stageC_null_copies.csv, stageC_results.json     the harness's rundown
    stageC_ratings_ranking.csv, _results.csv, _null_copies.csv, _results.json               the given-ratings rundown
    stageC_catalog.json                     one entry per scored column: id, name, family, description, tuned
    stageC_summary.json                     stageC_sos_part.json and stageC_fatigue_part.json folded together, the
                                            rows chosen for the given-ratings scores, the reference rows against
                                            Stage 4's ranking, the headline rows, timings

Run after stageC_sos.py and stageC_fatigue.py: ./python.sh src/eda/ufc_ideas/stageC_rundown.py   (about 2 minutes
with 5 workers, 78 to 121 seconds on 2 Oct 2026 depending on the machine's load; measured runtime in stageC_summary.json).
--summary-only rebuilds stageC_catalog.json and stageC_summary.json from the rundown's files without rescoring.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.ufc_ideas import common as U  # noqa: E402
from src.eda.ufc_ideas import stageC_fatigue as FT  # noqa: E402
from src.eda.ufc_ideas import stageC_sos as S  # noqa: E402

FEATURES = U.OUT / "stageC_features.parquet"
PREFIX = U.OUT / "stageC"
PREFIX_RATINGS = U.OUT / "stageC_ratings"
CATALOG = U.OUT / "stageC_catalog.json"
SUMMARY = U.OUT / "stageC_summary.json"
WORKERS = 5
REFERENCE = {"elo_change_52w|single": "Elo's change over 12 months",
             "recent_level|single": "Level played over the last 52 weeks",
             "played_52w|single": "Matches played (last 52 weeks)",
             "sets_14d|single": "Sets over the last 14 days"}
FAMILY = {"sos": "strength of schedule", "credit": "retrospective credit", "fatigue": "fatigue", "ref": "earlier study"}
BEST_GIVEN_RATINGS = 2
ELO_AS_FEATURE = "elo_surface|single"       # the given-ratings rundown's reference row: Elo itself added to the ratings
T0 = time.time()

DESCRIPTIONS = {   # one line each, in words only (no numbers): the catalog's descriptions
    "sos_elo|52 weeks": "Mean pre-match surface Elo (log-odds scale) of the opponents a player met over the last year, shrunk toward the tour's typical opponent with phantom opponents; A minus B.",
    "sos_elo|decayed": "The same mean of opponents' surface Elo with every earlier match weighted by a one-year half-life; A minus B.",
    "sos_rating|52 weeks": "Mean pre-match serve-plus-return rating (the earlier study's ratings) of the last year's opponents, shrunk with phantom opponents; A minus B.",
    "sos_bt|52 weeks": "Mean pre-match Bradley-Terry rating (this study's first stage) of the last year's opponents, shrunk with phantom opponents; A minus B.",
    "sos_won_elo|52 weeks": "Quality of wins: mean surface Elo of the opponents a player beat over the last year, shrunk; A minus B.",
    "sos_lost_elo|52 weeks": "Mean surface Elo of the opponents a player lost to over the last year, shrunk; A minus B.",
    "over_elo|52 weeks": "Results above surface Elo's expectation over the last year: won minus Elo's pre-match probability, summed over matches plus phantom matches; A minus B.",
    "over_elo_strong|52 weeks": "Results above surface Elo's expectation against opponents above the tour's main-tour median Elo, over the last year, shrunk; A minus B.",
    "revalue|52 weeks": "Retrospective credit: for the last year's opponents, their latest pre-match surface Elo from an earlier week minus their Elo at the meeting, later rematches taken out, averaged and shrunk; A minus B.",
    "revalue_won|52 weeks": "The retrospective credit over the opponents a player beat; A minus B.",
    "revalue_lost|52 weeks": "The retrospective credit over the opponents a player lost to; A minus B.",
    "revalue_later|52 weeks": "The retrospective credit from the opponents' later matches only: the meeting's own Elo update and later rematches taken out (the UFC rule); A minus B.",
    "revalue_won_later|52 weeks": "The later-matches-only credit over the opponents a player beat; A minus B.",
    "revalue_lost_later|52 weeks": "The later-matches-only credit over the opponents a player lost to; A minus B.",
    "late_decline|career": "A player's change in serve-point win rate from the first two sets to the third set onward, relative to the opponent's, over earlier Grand Slam point-by-point matches, shrunk; A minus B.",
    "late_decline_x_bo5|single": "The late-decline difference multiplied by whether the match is best of five (the source's record); men only.",
    "late_decline_x_long|single": "The late-decline difference multiplied by the match's expected closeness from the earlier study's ratings through the iid model.",
    "grinder|career": "A player's total points won above the earlier study's ratings' expectation in long matches (minutes per set above the tour's upper quartile) minus in short ones, career, shrunk; A minus B.",
    "grinder|52 weeks": "The grinder contrast over the last year, shrunk; A minus B.",
    "grinder_x_bo5|single": "The career grinder difference multiplied by whether the match is best of five; men only.",
    "sets_14d_x_decline|single": "Each player's sets over the last two weeks (log of one plus) times their late-decline trait; A's product minus B's.",
    "minutes_14d_x_decline|single": "Each player's minutes over the last two weeks (log of one plus) times their late-decline trait; A's product minus B's.",
    "elo_change_52w|single": "The earlier study's rundown row: overall Elo now minus at the first match on or after a year before; A minus B.",
    "recent_level|single": "The earlier study's rundown row: share of the last year's matches played in main-tour main draws; A minus B.",
    "played_52w|single": "The earlier study's rundown row: log of one plus the matches played over the last year; A minus B.",
    "sets_14d|single": "The earlier study's rundown row: log of one plus the sets played over the last two weeks; A minus B.",
    ELO_AS_FEATURE: "Surface Elo's own log-odds that A wins, scored only as an input added to the earlier study's serve and return ratings: the reference for what results-based strength adds to them.",
}


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def column_family(col: str) -> str:
    if col in REFERENCE:
        return "ref"
    if col.startswith(("sos_", "over_elo")):
        return "sos"
    if col.startswith("revalue"):
        return "credit"
    return "fatigue"


def box_based(col: str) -> bool:
    """Rows scored for the women from 2019: built on box scores, point-by-point records or the Stage 3 ratings."""
    return col.startswith(("sos_rating", "late_decline", "grinder", "sets_14d_x", "minutes_14d_x"))


def build_frame() -> tuple[pd.DataFrame, list, dict, dict]:
    frame = U.load_pool(list(REFERENCE) + ["rating_matchup|single"])
    sos = pd.read_parquet(S.PART)
    fat = pd.read_parquet(FT.PART)
    for part in (sos, fat):
        assert (part["match_id"].to_numpy() == frame["match_id"].to_numpy()).all(), "part not in the pool's order"
    cols = [c for c in sos.columns if c != "match_id"] + [c for c in fat.columns if c != "match_id"]
    for c in cols:
        frame[c] = (sos if c in sos else fat)[c].to_numpy(dtype="float64")
    frame["p_ratings"] = expit(frame["rating_matchup|single"].to_numpy(dtype="float64"))
    # a reference for the given-ratings scores: surface Elo's own log-odds as a feature added to the ratings
    frame[ELO_AS_FEATURE] = logit(np.clip(frame["p_elo"].to_numpy(dtype="float64"), 1e-9, 1 - 1e-9))
    sj = json.loads(S.PART_JSON.read_text(encoding="utf-8"))
    fj = json.loads(FT.PART_JSON.read_text(encoding="utf-8"))
    return frame, cols, sj, fj


def name_of(col: str, sj: dict, fj: dict) -> str:
    return sj["columns"].get(col) or fj["columns"].get(col) or REFERENCE.get(col) or col


def tasks_for(cols: list, sj: dict, fj: dict) -> list:
    out = []
    for col in cols + list(REFERENCE):
        cid, form = col.split("|")
        fam = column_family(col)
        for tour in C.TOURS:
            if col.endswith("_x_bo5|single") and tour == "wta":
                continue                                     # best of five never occurs in the women's pool
            out.append(U.task(tour, cid, form, name_of(col, sj, fj), FAMILY[fam], [col], wta_box_from_2019=box_based(col)))
    return out


def tuned_text(col: str, sj: dict, fj: dict) -> str | None:
    if col in sj.get("K", {}):
        k = sj["K"][col]
        what = "phantom opponents" if column_family(col) == "sos" else "phantom encounters"
        return (f"K ({what}) from {{0, 2, 5, 10, 20}}, per tour, by the in-sample log-loss gain given Elo on 2013-2018: "
                f"men {k['atp']:g}, women {k['wta']:g}")
    if col.startswith(("late_decline", "sets_14d_x", "minutes_14d_x")):
        k = fj["K_used"]["decline"]
        src = fj["K_used"]["source"]
        return (f"late-decline shrinkage K (effective points): men {k['atp']:.0f} ({src['decline atp']}), "
                f"women {k['wta']:.0f} ({src['decline wta']})")
    if col.startswith("grinder"):
        k = fj["K_used"]["grinder"]
        src = fj["K_used"]["source"]
        ln = fj["long_line_minutes_per_set"]
        return (f"grinder shrinkage K (effective points): men {k['atp']:.0f} ({src['grinder atp']}), women {k['wta']:.0f} "
                f"({src['grinder wta']}); long-match line {ln['atp']:g} (men) and {ln['wta']:g} (women) minutes per set, "
                f"the 2010-2018 upper quartile")
    return None


def main() -> int:
    """With --summary-only, the harness is not rerun: the catalog and stageC_summary.json are rebuilt from the
    rundown's existing files (after a change to the parts' JSON that leaves every feature column as it was)."""
    t_start = time.time()
    summary_only = "--summary-only" in sys.argv
    frame, cols, sj, fj = build_frame()
    tasks = tasks_for(cols, sj, fj)
    if summary_only:
        old = pd.read_parquet(FEATURES)
        for c in cols:
            assert np.array_equal(old[c].to_numpy(dtype="float64"), frame[c].to_numpy(dtype="float64"), equal_nan=True), c
        rank = pd.read_csv(f"{PREFIX}_ranking.csv")
        res = {"lines": json.loads(Path(f"{PREFIX}_results.json").read_text(encoding="utf-8"))["lines"]}
        prev = json.loads(SUMMARY.read_text(encoding="utf-8"))["timings"]
        t_main = prev["rundown_s"]
        log("summary only: the rundown's files are read, the features unchanged")
    else:
        frame.to_parquet(FEATURES, index=False, compression="zstd")
        log(f"wrote {FEATURES.name}: {frame.shape}")
        res = U.rundown(FEATURES, tasks, PREFIX, workers=WORKERS)
        t_main = round(time.time() - t_start, 1)
        rank = res["ranking"]
    # the two best rows given Elo per family and tour (strength of schedule; retrospective credit), given the ratings
    chosen = []
    for tour in C.TOURS:
        for fam in ("sos", "credit"):
            r = rank[(rank["tour"] == tour) & (rank["group"] == FAMILY[fam])].sort_values("elo_imp", ascending=False)
            for _, x in r.head(BEST_GIVEN_RATINGS).iterrows():
                chosen.append({"tour": tour, "family": FAMILY[fam], "id": x["id"], "form": x["form"],
                               "column": f"{x['id']}|{x['form']}", "elo_imp": float(x["elo_imp"])})
    rtasks = [U.task(c["tour"], c["id"], c["form"], name_of(c["column"], sj, fj), c["family"], [c["column"]],
                     scores=("ratings",), wta_box_from_2019=True, bases={"ratings": "p_ratings"}) for c in chosen]
    rtasks += [U.task(t, "elo_surface", "single", "Surface Elo (Stage 1) as a feature", FAMILY["ref"], [ELO_AS_FEATURE],
                      scores=("ratings",), wta_box_from_2019=True, bases={"ratings": "p_ratings"}) for t in C.TOURS]
    t2 = time.time()
    if summary_only:
        rres = {"ranking": pd.read_csv(f"{PREFIX_RATINGS}_ranking.csv"),
                "lines": json.loads(Path(f"{PREFIX_RATINGS}_results.json").read_text(encoding="utf-8"))["lines"]}
        t_ratings = prev["rundown_given_ratings_s"]
    else:
        rres = U.rundown(FEATURES, rtasks, PREFIX_RATINGS, workers=WORKERS, reading_base="ratings")
        t_ratings = round(time.time() - t2, 1)
    # the reference rows against Stage 4's own ranking (same columns, same fits: the improvements must agree); with
    # --summary-only the full run's check is kept (re-read from CSV, both sides would agree trivially)
    ref4 = U.stage4_reference([c.split("|")[0] for c in REFERENCE])
    ref_check = []
    for col in ([] if summary_only else REFERENCE):
        cid, form = col.split("|")
        for tour in C.TOURS:
            a = rank[(rank["tour"] == tour) & (rank["id"] == cid) & (rank["form"] == form)].iloc[0]
            b = ref4[(ref4["tour"] == tour) & (ref4["id"] == cid) & (ref4["form"] == form)].iloc[0]
            ref_check.append({"tour": tour, "column": col, "elo_imp_here": float(a["elo_imp"]),
                              "elo_imp_stage4": float(b["elo_imp"]), "market_imp_here": float(a["market_imp"]),
                              "market_imp_stage4": float(b["market_imp"]),
                              "largest_difference": float(max(abs(a["elo_imp"] - b["elo_imp"]), abs(a["market_imp"] - b["market_imp"]),
                                                              abs(a["alone_imp"] - b["alone_imp"])))})
    if summary_only:
        ref_check = json.loads(SUMMARY.read_text(encoding="utf-8"))["reference_check"]
    log(f"reference rows against Stage 4: largest difference {max(x['largest_difference'] for x in ref_check):.2e}")
    # the catalog
    cat = []
    for col in cols + list(REFERENCE):
        cid, form = col.split("|")
        tours = sorted(set(rank.loc[(rank["id"] == cid) & (rank["form"] == form), "tour"]))
        cat.append({"id": col, "name": name_of(col, sj, fj), "family": FAMILY[column_family(col)],
                    "description": DESCRIPTIONS[col], "tuned": tuned_text(col, sj, fj), "tours": tours,
                    "women_scored_from": C.WTA_BOX_FROM if box_based(col) else C.EVAL_YEARS[0],
                    "also_given_ratings": sorted({c["tour"] for c in chosen if c["column"] == col})})
    cat.append({"id": ELO_AS_FEATURE, "name": "Surface Elo (Stage 1) as a feature", "family": FAMILY["ref"],
                "description": DESCRIPTIONS[ELO_AS_FEATURE], "tuned": None, "tours": list(C.TOURS),
                "women_scored_from": C.WTA_BOX_FROM, "also_given_ratings": list(C.TOURS), "only_given_ratings": True})
    CATALOG.write_text(json.dumps(cat, indent=1), encoding="utf-8")
    log(f"wrote {CATALOG.name}: {len(cat)} entries")
    # the summary
    keep = ["tour", "id", "form", "name", "group", "alone_imp", "alone_above_band", "elo_imp", "elo_lo", "elo_hi",
            "elo_band_max", "elo_band_min", "elo_z", "elo_above_band", "elo_below_band", "elo_clears_line", "elo_observed",
            "elo_2019-2026", "elo_2022-2026", "elo_scored", "elo_coverage", "market_imp", "market_lo", "market_hi",
            "market_band_max", "market_band_min", "market_above_band", "market_below_band", "market_clears_line",
            "market_observed", "market_2019-2026", "market_2022-2026", "market_scored", "eras_positive", "eras_scored",
            "elo_coef", "elo_coef_lo", "elo_coef_hi", "sign_observed", "reading", "scored_from", "constant"]
    rows = json.loads(rank[[c for c in keep if c in rank]].to_json(orient="records"))
    rr = rres["ranking"]
    keep_r = ["tour", "id", "form", "name", "group", "ratings_imp", "ratings_lo", "ratings_hi", "ratings_band_max",
              "ratings_band_min", "ratings_z", "ratings_above_band", "ratings_clears_line", "ratings_2019-2026",
              "ratings_2022-2026", "ratings_scored", "ratings_coef", "eras_positive", "eras_scored", "reading", "scored_from"]
    rows_r = json.loads(rr[[c for c in keep_r if c in rr]].to_json(orient="records"))
    # counts the write-up quotes
    new = rank[rank["group"] != FAMILY["ref"]]
    kvals = [v for col in sj["K"].values() for v in col.values()]

    def best_of(df, key):
        if df.empty or df[key].isna().all():
            return None
        x = df.loc[df[key].idxmax()]
        pre = key.split("_")[0]
        return {"column": f"{x['id']}|{x['form']}", "name": x["name"], key: float(x[key]),
                "lo": float(x[f"{pre}_lo"]), "hi": float(x[f"{pre}_hi"]), "reading": x["reading"]}
    derived = {"new_rows": {t: int((new["tour"] == t).sum()) for t in C.TOURS},
               "reference_rows": {t: int(((rank["tour"] == t) & (rank["group"] == FAMILY["ref"])).sum()) for t in C.TOURS},
               "readings_new_rows": {t: {k: int(v) for k, v in new.loc[new["tour"] == t, "reading"].value_counts().items()}
                                     for t in C.TOURS},
               "K_choices": {"total": len(kvals), "at_grid_top": int(sum(v == max(S.K_GRID) for v in kvals)),
                             "at_grid_bottom": int(sum(v == min(S.K_GRID) for v in kvals))},
               "best_given_elo": {t: {fam: best_of(new[(new["tour"] == t) & (new["group"] == fam)], "elo_imp")
                                      for fam in (FAMILY["sos"], FAMILY["credit"], FAMILY["fatigue"])} for t in C.TOURS},
               "best_given_market": {t: {fam: best_of(new[(new["tour"] == t) & (new["group"] == fam)], "market_imp")
                                         for fam in (FAMILY["sos"], FAMILY["credit"], FAMILY["fatigue"])} for t in C.TOURS},
               "new_rows_clearing_the_line_given_market": {t: new.loc[(new["tour"] == t) & new["market_clears_line"].astype(bool),
                                                                      "id"].tolist() for t in C.TOURS},
               "new_rows_above_band_given_market": {t: int(((new["tour"] == t) & new["market_above_band"].astype(bool)).sum())
                                                    for t in C.TOURS},
               "new_rows_at_or_above_1_given_market": int((new["market_imp"] >= 1).sum()),
               "largest_new_market_gain": float(new["market_imp"].max()),
               "pool_total": int(len(frame)),
               "probes": {k: int(sj["probe"][k] + fj["probe"][k]) for k in ("protected_checked", "protected_changed",
                                                                           "control_protected_changed")},
               "pbp_matches": int(sum(v["player_matches"] for v in fj["pbp_coverage"].values()) // 2),
               "fatigue_players": int(len(pd.read_csv(FT.PLAYERS_CSV, usecols=["tour"])))}
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "pool": {t: int((frame["tour"] == t).sum()) for t in C.TOURS},
               "pool_evaluation": {t: int(((frame["tour"] == t) & frame["evaluation"]).sum()) for t in C.TOURS},
               "lines": res["lines"], "lines_given_ratings": rres["lines"],
               "ranking": rows, "ranking_given_ratings": rows_r, "chosen_given_ratings": chosen, "derived": derived,
               "reference_check": ref_check, "sos": sj, "fatigue": fj,
               "timings": {"sos_script_s": sj["timings"]["total_s"], "fatigue_script_s": fj["timings"]["total_s"],
                           "rundown_s": t_main, "rundown_given_ratings_s": t_ratings,
                           "rundown_script_s": prev["rundown_script_s"] if summary_only else round(time.time() - t_start, 1),
                           "workers": WORKERS,
                           **({"summary_rebuilt_s": round(time.time() - t_start, 1)} if summary_only else {})},
               "tasks": len(tasks), "tasks_given_ratings": len(rtasks)}
    SUMMARY.write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    log(f"wrote {SUMMARY.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The summary of "rating systems against Elo": every number summary.md and the report's summary quote, gathered from the
stages' outputs into one file (data/studies/rating_systems/summary_results.json).

    systems         the frozen constants and the tuning years' log loss of every system (stageA_summary.json)
    raw             each system against surface Elo on every evaluation match and on the matches with odds, by window:
                    log loss, Elo minus the system (milli-log-loss) with the per-match and the calendar-week and
                    four-week-block cluster 95% intervals, the share of the Elo-to-market gap closed, and each forecast's
                    distance from a coin to the market (stageB_summary.json)
    leader          the leading candidate (TrueSkill Through Time, designated by the owner on 3 Oct 2026): the tuning
                    years' ranking, and TTT head to head against Elo and every other system by window
    ladder          the coin-to-market scale on the matches with odds, 2022-2026
    harness         each system given Elo and given the market; Elo given each leading system; the earlier leaders given
                    Elo and given each leading system (stageB_ranking.csv; the revised harness's four-week intervals)
    orthogonality   the feature-alpha audit's ladder with each base: the base against calibrated Elo, the full model
                    against Elo's full model, both ratings together, the full model against the closing average
                    (stageC_ladder_results.csv)
    market          each rating, the 16-input profile and the profile with each rating, against the calibrated closing
                    average and Pinnacle (stageC_market_results.csv; men)
    checks          probes, prefix checks, the earlier ranking reproduced, the shared code's hashes

Run after the stages: ./python.sh src/eda/rating_systems/summary_results.py   (seconds)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.feature_alpha_audit.elo_retest import clustered_gain  # noqa: E402
from src.eda.rating_systems import common as RC  # noqa: E402

OUT = RC.OUT
SUMMARY = OUT / "summary_results.json"
TOURS = ("atp", "wta")
ORDER = ["glicko_cs", "ttt", "ttt_hold", "glicko2m", "trueskill", "trueskill_cs", "glicko1m", "glicko2", "glicko1"]
LEADING = ["glicko_cs", "ttt", "glicko2m", "trueskill"]
LEADERS = ["profile_adjperf", "rating_matchup", "ios_short", "adjperf_tpw", "elo_games", "mu_points", "sets_14d",
           "surface_first", "age"]
T0 = time.time()


def fnum(x):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else x


def block_clusters(f: pd.DataFrame, mask: np.ndarray, d: np.ndarray) -> dict:
    """The four-week-block cluster interval of a paired difference (milli-log-loss), Monday origin 4 Jan 2010, as the
    revised harness computes it."""
    days = (pd.to_datetime(f["tournament_date"]).to_numpy().astype("datetime64[D]") - np.datetime64("2010-01-04")).astype(int)
    r = clustered_gain(d[mask], (days // 28)[mask])
    return {"lo": r["lo_mll"], "hi": r["hi_mll"], "blocks": r["weeks"]}


def main() -> int:
    A = json.loads((OUT / "stageA_summary.json").read_text(encoding="utf-8"))
    B = json.loads((OUT / "stageB_summary.json").read_text(encoding="utf-8"))
    C = json.loads((OUT / "stageC_summary.json").read_text(encoding="utf-8"))
    systems = [s for s in ORDER if s in B["systems"]]
    hold_path = OUT / "stageA_ttt_hold_summary.json"
    hold = json.loads(hold_path.read_text(encoding="utf-8")) if hold_path.exists() else None
    out = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "systems": systems,
           "names": B["names"], "coin": B["coin"]}

    # ---- the systems: constants and the tuning years
    out["constants"] = {f"{s}|{t}": (A["chosen"][f"{s}|{t}"] if s != "ttt_hold" else hold["constants"][t])
                        for s in systems for t in TOURS}
    out["ttt_hold"] = hold
    # the correlated-surface Glicko's surface deviation implied by its newcomer prior: RD0 x sqrt(1 - rho), rating points
    out["surface_deviation_points"] = {t: A["chosen"][f"glicko_cs|{t}"]["rd0"] * float(np.sqrt(1 - A["chosen"][f"glicko_cs|{t}"]["rho"]))
                                       for t in TOURS if f"glicko_cs|{t}" in A["chosen"]}
    out["surface_blend_gain_milli"] = {k: 1000 * (v["log_loss_w0"] - v["log_loss_best"]) for k, v in A["surface_weight"].items()
                                       if v.get("blend", True)}
    out["tuning_log_loss"] = {}
    for t in TOURS:
        tune = B["raw"][t]["2013-2018 (tuning)"]["all"]
        out["tuning_log_loss"][t] = {"elo": tune["ll"]["elo"], **{s: tune["ll"][s] for s in systems}}

    # ---- raw comparisons, with the four-week-block interval added from the scored frame
    f = pd.read_parquet(OUT / "stageB_features.parquet", columns=["match_id", "tour", "year", "evaluation", "a_won", "p_elo",
                                                                  "p_mkt"] + [f"p_{s}" for s in systems])
    m = RC.C.load_matches(["match_id", "tournament_date"]).set_index("match_id")
    f["tournament_date"] = m.reindex(f["match_id"])["tournament_date"].to_numpy()
    y = f["a_won"].to_numpy(dtype=bool)

    def ll(p):
        p = np.clip(np.nan_to_num(np.asarray(p, dtype="float64"), nan=0.5), 1e-12, 1 - 1e-12)
        return -np.where(y, np.log(p), np.log(1 - p))
    L = {"elo": ll(f["p_elo"]), **{s: ll(f[f"p_{s}"]) for s in systems}}
    odds = np.isfinite(f["p_mkt"].to_numpy(dtype="float64"))
    out["raw"] = {}
    for t in TOURS:
        out["raw"][t] = {}
        for w, c in B["raw"][t].items():
            a, o = c["all"], c["odds"]
            a0, a1 = B["windows"][w]
            base = (f["tour"].to_numpy() == t) & f["evaluation"].to_numpy(dtype=bool) & (f["year"].to_numpy() >= a0) \
                & (f["year"].to_numpy() <= a1)
            rec = {"n_all": a["n"], "n_odds": o["n"], "elo_ll": a["ll"]["elo"], "elo_ll_odds": o["ll"]["elo"],
                   "market_ll": o["ll"]["market"], "room_milli": o["room_milli"],
                   "coin_to_market_elo": o["coin_to_market"]["elo"], "systems": {}}
            for s in systems:
                da, do = a["elo_minus"][s], o["elo_minus"][s]
                ba = block_clusters(f, base, L["elo"] - L[s])
                bo = block_clusters(f, base & odds, L["elo"] - L[s])
                rec["systems"][s] = {
                    "ll": a["ll"][s], "ll_odds": o["ll"][s],
                    "better_than_elo": da["milli"], "iid_lo": da["lo"], "iid_hi": da["hi"],
                    "week_lo": da["week_lo"], "week_hi": da["week_hi"], "block_lo": ba["lo"], "block_hi": ba["hi"],
                    "better_than_elo_odds": do["milli"], "odds_week_lo": do["week_lo"], "odds_week_hi": do["week_hi"],
                    "odds_block_lo": bo["lo"], "odds_block_hi": bo["hi"],
                    "gap_closed": o["gap_closed"][s], "coin_to_market": o["coin_to_market"][s]}
                assert abs(1000 * float(np.mean((L["elo"] - L[s])[base])) - da["milli"]) < 1e-9, (t, w, s)
            out["raw"][t][w] = rec

    # ---- the leading candidate (the owner's designation of 3 Oct 2026): TrueSkill Through Time against Elo and every
    # other system head to head, positive when TTT is better, with four-week-block intervals. The selection rule is the
    # tuning years' log loss; the hold variant is a sensitivity of TTT with TTT's constants, so it is not ranked.
    out["leader"] = {"system": "ttt", "designated": "2026-10-03",
                     "rule": "lowest log loss on the 2013-2018 evaluation matches (the tuning years), then frozen",
                     "tuning_rank": {t: sorted((s for s in out["tuning_log_loss"][t] if s != "ttt_hold"),
                                               key=out["tuning_log_loss"][t].get) for t in TOURS},
                     "head_to_head": {}}
    for t in TOURS:
        out["leader"]["head_to_head"][t] = {}
        for w in B["raw"][t]:
            a0, a1 = B["windows"][w]
            base = (f["tour"].to_numpy() == t) & f["evaluation"].to_numpy(dtype=bool) & (f["year"].to_numpy() >= a0) \
                & (f["year"].to_numpy() <= a1)
            rec = {}
            for s in ["elo"] + [s for s in systems if s != "ttt"]:
                d = L[s] - L["ttt"]
                ba, bo = block_clusters(f, base, d), block_clusters(f, base & odds, d)
                rec[s] = {"ttt_better": 1000 * float(np.mean(d[base])), "lo": ba["lo"], "hi": ba["hi"],
                          "ttt_better_odds": 1000 * float(np.mean(d[base & odds])), "odds_lo": bo["lo"],
                          "odds_hi": bo["hi"]}
            out["leader"]["head_to_head"][t][w] = rec
    out["by_level"] = {t: {g: {s: B["by_level"][t][g]["all"]["elo_minus"][s]["milli"] for s in LEADING}
                           | {"n": B["by_level"][t][g]["all"]["n"]}
                           for g in B["level_groups"] if B["by_level"][t][g]["all"]["n"]} for t in TOURS}
    out["by_era"] = {t: {e: {s: B["by_era"][t][e]["all"]["elo_minus"][s]["milli"] for s in LEADING}
                         | {"n": B["by_era"][t][e]["all"]["n"]} for e in B["eras"]} for t in TOURS}
    out["calibration_slope_2019_2026"] = {t: {k: B["calibration_2019_2026"][t][k]["slope"] for k in ["elo"] + systems}
                                          for t in TOURS}
    out["weekly_overshoot"] = B.get("weekly_overshoot")
    out["diagnostics"] = {t: {s: {k: {b: {"milli": v["milli"], "n": v["n"]} for b, v in B["diagnostics"][t][s][k].items()}
                                  for k in ("fewest_prior_matches", "longest_layoff_days")}
                              for s in LEADING} for t in TOURS}

    # ---- the coin-to-market ladder, matches with odds, 2022-2026
    out["ladder_2022_2026"] = {t: {"elo": out["raw"][t]["2022-2026 (headline)"]["coin_to_market_elo"],
                                   **{s: out["raw"][t]["2022-2026 (headline)"]["systems"][s]["coin_to_market"]
                                      for s in systems}, "market": 1.0} for t in TOURS}

    # ---- the harness
    rk = pd.read_csv(OUT / "stageB_ranking.csv")

    def hrow(t, cid, s):
        r = rk[(rk["tour"] == t) & (rk["id"] == cid)]
        if r.empty or f"{s}_imp" not in r or pd.isna(r.iloc[0][f"{s}_imp"]):
            return None
        r = r.iloc[0]
        return {"imp": fnum(r[f"{s}_imp"]), "lo": fnum(r[f"{s}_lo"]), "hi": fnum(r[f"{s}_hi"]),
                "2022-2026": fnum(r.get(f"{s}_2022-2026"))}
    out["harness"] = {t: {"systems": {s: {"given_elo": hrow(t, s, "elo"), "given_market": hrow(t, s, "market"),
                                          "alone": hrow(t, s, "alone")} for s in systems},
                          "elo_given": {s: hrow(t, "elo", s) for s in LEADING},
                          "elo_given_market": hrow(t, "elo", "market"),
                          "leaders": {cid: {b: hrow(t, cid, b) for b in ["elo"] + LEADING + ["market"]} for cid in LEADERS},
                          "pairs": {cid: {"alone": hrow(t, cid, "alone"), "market": hrow(t, cid, "market")}
                                    for cid in ("pair_glicko_cs", "pair_ttt", "ratings_three")}} for t in TOURS}
    out["harness_reading"] = {t: {r["id"]: r["reading"] for _, r in rk[rk["tour"] == t].iterrows()} for t in TOURS}

    # ---- the ladder of the audit with each base
    lad = pd.read_csv(OUT / "stageC_ladder_results.csv")

    def lrow(t, since, pop, model, ref):
        r = lad[(lad["tour"] == t) & (lad["since"] == since) & (lad["population"] == pop) & (lad["model"] == model)
                & (lad["reference"] == ref)]
        if r.empty:
            return None
        r = r.iloc[0]
        return {"gain": fnum(r["gain_mll"]), "lo": fnum(r["lo_mll"]), "hi": fnum(r["hi_mll"]), "n": int(r["n"])}
    bases = [b for b in ("glicko_cs", "ttt", "glicko2m", "trueskill", "glicko2") if f"{b}_full" in C["ladder"]["specs"]]
    out["orthogonality"] = {}
    for t in TOURS:
        out["orthogonality"][t] = {}
        for since in (2019, 2022):
            rec = {"elo_full_vs_calibrated": lrow(t, since, "all_common", "elo_full", "elo_calibrated"),
                   "elo_full_vs_market": lrow(t, since, "market_common", "elo_full", "market_raw"), "bases": {}}
            for b in bases:
                rec["bases"][b] = {
                    "calibrated_vs_elo_calibrated": lrow(t, since, "all_common", f"{b}_calibrated", "elo_calibrated"),
                    "sr_vs_elo_sr": lrow(t, since, "all_common", f"{b}_sr", "elo_sr"),
                    "full_vs_elo_full": lrow(t, since, "all_common", f"{b}_full", "elo_full"),
                    "full_vs_own_calibrated": lrow(t, since, "all_common", f"{b}_full", f"{b}_calibrated"),
                    "both_full_vs_elo_full": lrow(t, since, "all_common", f"elo+{b}_full", "elo_full"),
                    "both_calibrated_vs_elo_calibrated": lrow(t, since, "all_common", f"elo+{b}_calibrated", "elo_calibrated"),
                    "full_vs_market": lrow(t, since, "market_common", f"{b}_full", "market_raw"),
                    "both_full_vs_market": lrow(t, since, "market_common", f"elo+{b}_full", "market_raw"),
                    "steps_given_base": {st: lrow(t, since, "all_common", f"{b}_{st}", f"{b}_{prev}")
                                         for prev, st in zip(["calibrated", "sr", "sr_adjperf", "sr_adjperf_ios",
                                                              "sr_adjperf_ios_games"],
                                                             ["sr", "sr_adjperf", "sr_adjperf_ios", "sr_adjperf_ios_games", "full"])}}
            rec["steps_given_elo"] = {st: lrow(t, since, "all_common", f"elo_{st}", f"elo_{prev}")
                                      for prev, st in zip(["calibrated", "sr", "sr_adjperf", "sr_adjperf_ios",
                                                           "sr_adjperf_ios_games"],
                                                          ["sr", "sr_adjperf", "sr_adjperf_ios", "sr_adjperf_ios_games", "full"])}
            out["orthogonality"][t][str(since)] = rec
    out["orthogonality_coverage"] = C["ladder"]["coverage"]

    # ---- the closing line, men
    mk = pd.read_csv(OUT / "stageC_market_results.csv")
    out["market"] = {}
    for _, r in mk.iterrows():
        out["market"].setdefault(r["market"], {}).setdefault(r["window"], {}).setdefault(r["model"], {})[r["comparator"]] = {
            "gain": fnum(r["week_gain_mll"]), "lo": fnum(r["week_lo_mll"]), "hi": fnum(r["week_hi_mll"]), "n": int(r["n"])}

    # ---- the repaired cohort (the audit's repairs: main-tour matches with trusted match dates, features rebuilt)
    rep_path = OUT / "stageC_repaired_results.csv"
    if rep_path.exists():
        rep = pd.read_csv(rep_path)

        def rrow(study, tour, model, comp, window, market="none"):
            r = rep[(rep["study"] == study) & (rep["tour"] == tour) & (rep["model"] == model) & (rep["comparator"] == comp)
                    & (rep["window"] == window) & (rep["market"] == market)]
            if r.empty:
                return None
            r = r.iloc[0]
            return {"gain": fnum(r["gain_mll"]), "lo": fnum(r["lo_mll"]), "hi": fnum(r["hi_mll"]), "n": int(r["n"]),
                    "week_lo": fnum(r["week_lo_mll"]), "week_hi": fnum(r["week_hi_mll"])}
        windows = {"2019": "post_tuning_2019_2026", "2022": "recent_2022_2026"}
        out["repaired"] = {"ladder": {}, "market": {}, "meta": C.get("repaired", {}).get("coverage")}
        for t in TOURS:
            out["repaired"]["ladder"][t] = {}
            for k, w in windows.items():
                rec = {"elo_repaired_vs_elo_calibrated": rrow("ladder", t, "elo_repaired_calibrated", "elo_calibrated", w),
                       "elo_repaired_full_vs_elo_full": rrow("ladder", t, "elo_repaired_full", "elo_full", w)}
                for b in ("glicko_cs", "ttt", "glicko2m", "trueskill"):
                    rec[b] = {"calibrated_vs_elo_calibrated": rrow("ladder", t, f"{b}_calibrated", "elo_calibrated", w),
                              "full_vs_elo_full": rrow("ladder", t, f"{b}_full", "elo_full", w),
                              "both_full_vs_elo_full": rrow("ladder", t, f"elo+{b}_full", "elo_full", w)}
                out["repaired"]["ladder"][t][k] = rec
        for market in ("p_avg_a", "p_ps_a"):
            out["repaired"]["market"][market] = {}
            for k, w in windows.items():
                rec = {"profile": rrow("market", "atp", "profile", "calibrated_market", w, market)}
                for b in ("elo", "glicko_cs", "ttt", "glicko2m", "trueskill"):
                    rec[f"rating_{b}"] = rrow("market", "atp", f"rating_{b}", "calibrated_market", w, market)
                    rec[f"profile_rating_{b}_vs_profile"] = rrow("market", "atp", f"profile_rating_{b}", "profile", w, market)
                out["repaired"]["market"][market][k] = rec

    # ---- checks
    pr = A["probes"]
    out["checks"] = {
        "probes": {"real_cuts": int(sum(p["cuts"] for p in pr if not p["leaky"])),
                   "protected_checked": int(sum(p["protected_matches_checked"] for p in pr if not p["leaky"])),
                   "protected_changed": int(sum(p["protected_matches_changed"] for p in pr if not p["leaky"])),
                   "leaky_changed": int(sum(p["protected_matches_changed"] for p in pr if p["leaky"])),
                   "systems_probed": sorted({p["system"] for p in pr if not p["leaky"]})},
        "prefix_checks_max_abs": max(v["tuning_pass_vs_full_prefix_max_abs"] for v in A["checks"].values()),
        "stage4_reference_reproduced_max_abs": B["stage4_reference_reproduced"]["max_abs_difference"],
        "stage4_reference_note": "point estimates, bands and counts reproduce the earlier ranking; the ranges differ "
                                 "because the shared harness now gives four-week cluster intervals",
        "top10_end": A.get("top10_end"),
        "shared_code": {"stageA": A.get("shared_code"), "stageB": B.get("shared_code"), "stageC": C.get("shared_code")}}
    out["seconds"] = round(time.time() - T0, 1)
    SUMMARY.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    print(f"wrote {SUMMARY} in {out['seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

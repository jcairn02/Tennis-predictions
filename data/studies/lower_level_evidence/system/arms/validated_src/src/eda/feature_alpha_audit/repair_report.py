"""Render the corrected selected-feature evidence, without recycling old claims."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.feature_alpha_audit.render_report import inline

DATA = ROOT / "data/studies/feature_alpha_audit/repairs"
DOCS = ROOT / "docs/studies/feature_alpha_audit"


def main():
    history = json.loads((DATA / "repair_history_summary.json").read_text(encoding="utf-8"))
    feature = json.loads((DATA / "repair_features_summary.json").read_text(encoding="utf-8"))
    scores = pd.read_csv(DATA / "repair_results.csv")
    verification = json.loads((DATA / "verification.json").read_text(encoding="utf-8"))
    fmt = json.loads((DATA.parent / "format_repair_counts.json").read_text(encoding="utf-8"))
    md, body = [], []

    def heading(s, level=2):
        md.append("#" * level + " " + s)
        body.append(f"<h{level}>{inline(s)}</h{level}>")

    def p(s):
        md.append(s)
        body.append(f"<p>{inline(s)}</p>")

    def table(headers, rows):
        md.append("\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
                            + ["| " + " | ".join(map(str, row)) + " |" for row in rows]))
        body.append('<div class="table"><table><thead><tr>' + "".join(f"<th>{inline(h)}</th>" for h in headers)
                    + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>" for row in rows)
                    + "</tbody></table></div>")

    def one(**criteria):
        sel = pd.Series(True, index=scores.index)
        for key, value in criteria.items():
            sel &= scores[key].eq(value)
        r = scores.loc[sel]
        assert len(r) == 1, (criteria, len(r))
        return r.iloc[0]

    def effect(r):
        return f"{r.gain_mll:+.3f} [{r.lo_mll:+.3f}, {r.hi_mll:+.3f}]"

    main_window = "post_tuning_2019_2026"
    profile = one(study="profile", tour="atp", market="p_ps_a", model="profile_ridge",
                  comparator="calibrated_market", window=main_window)
    conditional = one(study="profile", tour="atp", market="p_ps_a", model="profile_context",
                      comparator="context", window=main_window)
    heading("Repaired tennis feature study", 1)
    p("2 October 2026. Implemented corrections and a fresh feature rebuild following the [original audit](README.md). "
      "Research evidence, not a model or betting decision. [HTML version](repairs.html); "
      "[measured comparisons](../../../data/studies/feature_alpha_audit/repairs/repair_results.csv).")
    if profile.lo_mll > 0:
        conclusion = "The men's recent statistics profile retains a positive market-conditional signal on the repaired dated cohort."
    elif profile.gain_mll > 0:
        conclusion = "The men's recent statistics profile retains a positive point estimate, but its repaired uncertainty interval includes zero."
    else:
        conclusion = "The men's recent statistics profile no longer improves the calibrated Pinnacle line on the repaired dated cohort."
    p(f"**The defects are fixed in code and the shortlisted features have been rebuilt. {conclusion}** "
      f"Its gain beyond calibrated Pinnacle is {effect(profile)} milli-log-loss on {int(profile.n):,} matches. "
      f"Beyond Pinnacle plus ratings, load, age and surface context, the profile contributes {effect(conditional)}. "
      "These are exploratory, historically selected comparisons; the intervals do not correct for the earlier feature search.")
    p("A positive gain means better predictions. +1 milli-log-loss means reducing mean natural-log loss by 0.001; "
      "it is not a percentage-point increase in accuracy or a betting return. Brackets below are paired 95% intervals "
      "clustered into four-week calendar blocks, with week-cluster sensitivity retained in the CSV.")

    heading("What was fixed")
    repair = history["data_repairs"]
    table(["Defect", "Implemented correction", "Verification / scope"], [
        ["Overlapping tournaments could expose future results", "Both history and targets now require accepted provider match dates. Every selected rating and statistic is rebuilt from raw rows in match-day order.", "A future-result mutation in an overlapping tournament cannot change protected earlier Elo, serve/return, adjperf or IOS values; later forecasts must respond."],
        ["Current scores determined forecast format", "Forecast format and box-history eligibility come from event, tour, year and scheduled round. Unsupported editions are excluded from box history and iid probability conversion; future scores cannot classify earlier history.", f"{fmt['raw_best_of_disagreement_supported']:,} recorded best-of disagreements; {fmt['evaluation_played'] - fmt['supported_evaluation_played']:,} unsupported evaluation matches excluded by event metadata across the original pool. [Rule sources](format_rules.md)."],
        ["Split player identities", "Canonicalize unambiguous normalized full names against Sackmann identity records, with demographic and opposing-player collision checks.", f"{repair['identity_player_rows_changed']:,} player rows corrected in the full input table; unresolved conflicts are recorded."],
        ["Match tiebreaks counted as games", "Reconstruct certain historical deciding match tiebreaks separately from ordinary games. Preserve ambiguous two-game-margin advantage sets.", f"{repair['historical_plain_match_tiebreaks_corrected']:,} historical score records corrected; this does not determine forecast format."],
        ["Invalid box counts and durations", "Negative primitive counts invalidate both players' box statistics; impossible derived ratios and implausible durations are missing.", f"{repair['negative_primitive_box_matches_masked']:,} paired boxes invalidated; {repair['implausible_minutes_masked']:,} durations masked."],
        ["Full-sample scaling and overstated evidence", "Fit scaling within training seasons; compare raw and recalibrated baselines separately; use paired calendar clusters. A negative gain cannot clear the evidence threshold.", "Shuffled thresholds are labelled descriptive heuristics, not conditional null tests or family-wise error control. Shared scorers are repaired."],
        ["Simulation interpreted as a forecasting ceiling", "Removed the claims that perfect pre-match information has a demonstrated low ceiling or that failed tested features close the pre-match route.", "The original simulation remains conditional on its iid and denoising assumptions."],
    ])

    heading("The chronology repair has a coverage cost")
    total, accepted = history["history_matches_original"], history["history_matches_accepted"]
    p(f"The rebuild accepts {accepted:,} of {total:,} original matches ({accepted / total:.1%}). "
      "A date is accepted only with a trusted identity join, matching set scores and round, no reassigned provider date, "
      "and a plausible gap from the event start. Undated matches are omitted from both history and targets; no artificial finish dates are assigned. "
      "The surviving history is main-tour matches. Challenger, qualifying and ITF coverage has not been repaired by inventing timestamps.")
    table(["Date check", "Matches"], [[k.replace("_", " "), f"{v:,}"] for k, v in history["date_reasons"].items()])
    p("Only earlier days and strictly earlier rounds of the same event on the same day may contribute. "
      "A previous day's result is assumed available by the next day; exact match-end and quote timestamps remain unavailable. "
      "Retrospective source concordance establishes record identity, not a timestamped pre-match join process. "
      "This corrects the demonstrated event-start ordering leak within the accepted cohort, not all historical data availability questions. "
      "Reduced history also changes workload, surface familiarity and player warm-up. Changes in model performance cannot be attributed solely to removal of leakage.")

    heading("Closing-line comparisons after rebuilding")
    rows = []
    for market in ("p_avg_a", "p_ps_a"):
        for model, comparator, label in [
            ("profile_ridge", "calibrated_market", "Profile beyond recalibrated line"),
            ("profile_ridge", "raw_market", "Profile forecast versus raw line"),
            ("profile_fixed_market", "raw_market", "Profile with raw line as fixed offset"),
            ("context", "calibrated_market", "Ratings + load + age + surface"),
            ("profile_context", "context", "Profile beyond line + context"),
            ("profile_context", "calibrated_market", "Profile + context together"),
        ]:
            r = one(study="profile", tour="atp", market=market, model=model, comparator=comparator, window=main_window)
            rows.append(["Pinnacle" if market == "p_ps_a" else "Average", label, f"{int(r.n):,}", effect(r)])
    table(["Market", "Men, 2019 onward", "Matches", "Gain [95% interval]"], rows)
    recent = one(study="profile", tour="atp", market="p_ps_a", model="profile_ridge", comparator="calibrated_market", window="recent_2022_2026")
    p(f"The same profile versus calibrated Pinnacle in 2022 onward: {effect(recent)} on {int(recent.n):,} matches. "
      f"The scored main comparison runs from {profile.first_match_day} to {profile.last_match_day}. "
      "Average and Pinnacle comparisons use identical complete-case matches. Ridge selection uses predictions from the prior two calendar seasons only; "
      "each validation regression is itself trained on earlier seasons. The 16 statistics and feature constants are frozen from the prior studies, "
      "so this is a corrected replication, not a newly tuned model search.")
    p("The original pre-2019 feature constants, population priors and exposure scales remain frozen. Their tuning was not "
      "rerun on corrected histories; all scored seasons here follow that tuning period. The repairs rebuild observations, "
      "rating states, features and forecast fits. Inner penalty validation before 2019 therefore inherits feature constants estimated "
      "through 2018; it is not a fully nested retuning of the feature generator. They do not claim that the old constants are optimal "
      "for the reduced history universe.")

    heading("What adds beyond Elo on the repaired cohort")
    ladder = [
        ("Serve/return strength", "elo_sr", "elo_calibrated"),
        ("Add recent adjusted points", "elo_sr_adjperf", "elo_sr"),
        ("Add short-memory IOS", "elo_sr_adjperf_ios_short", "elo_sr_adjperf"),
        ("Add games-weighted Elo", "elo_sr_adjperf_ios_short_games", "elo_sr_adjperf_ios_short"),
        ("Add load, age and surface context", "elo_sr_adjperf_ios_short_games_context", "elo_sr_adjperf_ios_short_games"),
        ("Full combination versus Elo", "elo_sr_adjperf_ios_short_games_context", "elo_calibrated"),
    ]
    rows = []
    for label, model, comparator in ladder:
        vals = [one(study="elo", tour=t, population="all_common", model=model, comparator=comparator, window=main_window) for t in ("atp", "wta")]
        rows.append([label] + [effect(r) for r in vals])
    table(["Sequential comparison, 2019 onward", "Men", "Women"], rows)
    full_name = "elo_sr_adjperf_ios_short_games_context"
    comparison = [one(study="elo", tour=t, market="p_ps_a", population="market_common", model=full_name,
                      comparator="raw_market", window=main_window) for t in ("atp", "wta")]
    p("The full Elo-based combination versus raw Pinnacle on its available market subset is "
      + "; ".join(f"{r.tour.upper()} {effect(r)} ({int(r.n):,} matches)" for r in comparison)
      + ". This is distinct from fitting the market itself as an input.")
    p("Every ladder row uses the same eligible matches within each tour and expanding season-by-season training. "
      "A sequential gain measures only the addition to the row immediately before it; it is not the feature's standalone value. "
      "The recent-window ladder, absolute losses, market-subset comparisons and exact row counts are in the measured CSV. "
      "The promising next research remains a player's performance relative to their own expected serve/return level, "
      "and partially pooled player-by-surface ratings. Those changes have not been silently mixed into this bug-fix replication.")
    p("A larger serve/return gain than in the original study is not evidence that its alpha increased. Removing undated "
      "lower-level history changes the Elo comparator and the other ratings as well. The conditional feature additions "
      "above are interpretable within this restricted cohort; cross-study differences are not controlled timing experiments.")
    cached = pd.read_csv(DATA / "cached_same_match_comparisons.csv")
    checks = []
    for study, tour, model, label in [
        ("profile", "atp", "p_ps_a|profile_ridge", "Men: Pinnacle + profile"),
        ("elo", "atp", full_name, "Men: full Elo combination"),
        ("elo", "wta", full_name, "Women: full Elo combination"),
    ]:
        selected = cached[cached.study.eq(study) & cached.tour.eq(tour) & cached.feature_model.eq(model)
                          & cached.window.eq(main_window)]
        if len(selected) == 1:
            r = selected.iloc[0]
            checks.append([label, f"{int(r.n):,}", effect(r)])
    table(["Rebuilt forecast versus cached original on identical match IDs", "Matches", "Change [95% interval]"], checks)
    p("Negative values in this last table mean the rebuilt forecast performs worse than the archived forecast on the same "
      "targets. The comparison combines corrected chronology, format, identities, reduced history and changed fitting cohorts. "
      "It cannot quantify how much of the original score came from leakage.")

    heading("Verification and reproduction")
    tests = verification["tests"]
    p(f"{tests['tests'] - tests['skipped']:,} tests passed; {tests['skipped']:,} skipped; no failures or errors. "
      "Regressions cover outcome-independent format, future-overlap isolation with responsive later controls, "
      "identity collisions, invalid data, training-only scaling, side symmetry and paired clustered uncertainty. "
      f"All {verification['original_evidence_files_unchanged']:,} original numerical evidence files remain unchanged. "
      f"The {verification['pre_repair_archive_files_verified']:,}-file pre-repair source/report archive matches its original hashes. "
      "[Verification evidence](../../../data/studies/feature_alpha_audit/repairs/verification.json).")
    commands = """./python.sh src/eda/feature_alpha_audit/repair_history.py
./python.sh src/eda/feature_alpha_audit/repair_features.py
./python.sh src/eda/feature_alpha_audit/repair_score.py
./python.sh -m pytest test/predictability_diagnostic test/ufc_ideas test/feature_alpha_audit -p no:cacheprovider --basetemp=data/studies/feature_alpha_audit/repairs/pytest_rebuild --junitxml=data/studies/feature_alpha_audit/repairs/test_results.xml
./python.sh src/eda/predictability_diagnostic/render_report.py
./python.sh src/eda/ufc_ideas/render_report.py
./python.sh src/eda/feature_alpha_audit/verify_repairs.py
./python.sh src/eda/feature_alpha_audit/repair_report.py
./python.sh src/eda/feature_alpha_audit/render_report.py
./python.sh src/eda/feature_alpha_audit/check_report.py --document docs/studies/feature_alpha_audit/repairs.html --output-dir data/studies/feature_alpha_audit/repairs"""
    md.append("```bash\n" + commands + "\n```")
    body.append("<pre>" + inline(commands) + "</pre>")
    p("Run from the repository root using the project's tennis environment through Git Bash. On this Windows machine, "
      "prepend C:/Users/zerom/miniforge3/envs/tennis/Library/bin to PATH for the numerical DLLs. Use a new writable pytest temporary "
      "directory if the shown one already exists. The shim and environment files were not changed. "
      "Original study outputs are historical; running their older full-pool builders does not supply missing match dates. "
      "Use the repair sequence above for the corrected shortlist. Weak feature families were not rerun.")
    p("The remaining limit is data coverage and publication timing, not an unimplemented test. No untouched holdout, "
      "executable closing-price history or measured after-cost betting edge is created by these repairs. "
      "[Source register and usage restrictions](sources.md).")
    (DOCS / "repairs.md").write_text("\n\n".join(md) + "\n", encoding="utf-8")
    css = "body{font:16px/1.65 system-ui,sans-serif;color:#182834;background:#f7f8f5;margin:0}main{max-width:1100px;margin:auto;padding:36px 26px 70px}h1,h2{color:#103b3d;line-height:1.25}h1{font-size:36px}h2{margin-top:40px}a{color:#126865}p{overflow-wrap:anywhere}.table{overflow-x:auto;background:white;border:1px solid #cddbd5;border-radius:6px;margin:20px 0;max-width:100%}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:12px;vertical-align:top;text-align:left;border-bottom:1px solid #dce5e0}th{background:#e4efea}pre{overflow-x:auto;padding:18px;background:#e7eeea;font-size:13px}@media(max-width:600px){main{padding:22px 14px}h1{font-size:28px}th,td{min-width:140px}}"
    (DOCS / "repairs.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Repaired tennis feature study</title><style>' + css + '</style><main>' + "\n".join(body) + '</main></html>', encoding="utf-8")
    print("Wrote repairs.md and repairs.html from repaired evidence")


if __name__ == "__main__":
    main()

"""Build the audit's Markdown and HTML from measured results and explicit readings."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/studies/feature_alpha_audit"
DOCS = ROOT / "docs/studies/feature_alpha_audit"


def inline(text):
    text = html.escape(str(text))
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    profile = pd.read_csv(DATA / "profile_results.csv")
    original = pd.read_csv(DATA / "profile_reproduction.csv")
    elo = pd.read_csv(DATA / "elo_results.csv")
    md, body = [], []

    def heading(s, level=2):
        md.append("#" * level + " " + s)
        body.append(f"<h{level}>{inline(s)}</h{level}>")

    def p(s):
        md.append(s)
        body.append(f"<p>{inline(s)}</p>")

    def bullets(items):
        md.append("\n".join("- " + x for x in items))
        body.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")

    def table(headers, rows):
        md.append("\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
                            + ["| " + " | ".join(map(str, r)) + " |" for r in rows]))
        body.append('<div class="table"><table><thead><tr>' + "".join(f"<th>{inline(h)}</th>" for h in headers)
                    + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
                    + "</tbody></table></div>")

    def one(frame, **criteria):
        mask = pd.Series(True, index=frame.index)
        for col, val in criteria.items():
            mask &= frame[col].eq(val)
        rows = frame.loc[mask]
        assert len(rows) == 1, (criteria, len(rows))
        return rows.iloc[0]

    def fmt(row, prefix="week_"):
        return f"{row[prefix+'gain_mll']:+.2f} [{row[prefix+'lo_mll']:+.2f}, {row[prefix+'hi_mll']:+.2f}]"

    heading("Feature alpha audit: what deserves more work", 1)
    p("**Update: the identified defects have now been repaired and the shortlist rebuilt.** Read the [repairs and corrected results](repairs.md) or [corrected HTML report](repairs.html). The original audit below records the evidence available before those repairs; its numerical conclusions are historical.")
    p("2 October 2026. Research, not a model or trading decision. Audit of the [predictability diagnostic](../predictability_diagnostic/README.md) and [UFC ideas](../ufc_ideas/README.md), with new bounded experiments. [HTML version](report.html); [code](../../../src/eda/feature_alpha_audit/); [evidence](../../../data/studies/feature_alpha_audit/).")
    p("**Keep the men's recent opponent-adjusted statistics profile as the main closing-line lead. Keep serve/return strength plus recent form as the strongest prediction features beyond Elo. Keep age, surface familiarity and recent load in that prediction baseline.** The market lead survives a stronger bookmaker comparator; its unique contribution becomes uncertain after the fullest context controls. There is no demonstrated executable betting edge.")
    p("I audited code, reports, saved outputs and tests, then ran three targeted checks: a regularized market-profile reanalysis; a joint Elo feature ladder; and a frozen-feature calendar-week timing sensitivity. The original studies were preserved. Every gain below is milli-log-loss: +1 means reducing average natural-log loss by 0.001, not increasing accuracy or return by 1%.")

    heading("The closing-line lead survived a useful challenge")
    r = one(original, model="profile_unpenalized", comparator="calibrated_market", window="all_2013_2026")
    p(f"**Observed.** The original men's profile reproduces exactly on {int(r.n):,} matches: {fmt(r)} against the calibrated average line. Brackets are now 95% intervals clustered by tournament-start calendar week; the original interval treated matches as independent. The profile is **16 inputs**, comprising twelve adjperf statistics and four non-duplicate adjdef statistics, not simply twelve independent skills.")
    rows = []
    comparisons = [
        ("Average line, recalibrated", "p_avg_a", "profile_ridge", "calibrated_market"),
        ("Pinnacle, recalibrated", "p_ps_a", "profile_ridge", "calibrated_market"),
        ("Pinnacle, raw probability", "p_ps_a", "profile_ridge", "raw_market"),
        ("Pinnacle fixed as an offset", "p_ps_a", "profile_fixed_market", "raw_market"),
        ("Pinnacle + serve/return + 14-day load", "p_ps_a", "profile_ratings_load", "ratings_load"),
    ]
    for label, market, model, comparator in comparisons:
        r = one(profile, market=market, model=model, comparator=comparator, window="post_tuning_2019_2026")
        rows.append([label, f"{int(r.n):,}", fmt(r)])
    table(["Baseline / check", "Matched matches, 2019 onward", "Profile improvement [95% week interval]"], rows)
    p("Both market measures are compared on exactly the same matches. The ridge penalty is chosen only from available predictions in the preceding two calendar seasons, each itself fitted on earlier seasons. There are no 2018 rows in the shared cohort, so 2019 selection uses the available 2017 predictions. Scaling also uses training data only. The market slope is unpenalized; the fixed-offset check keeps that slope at one. These comparisons separate feature contribution from simple market recalibration. Regularization did not materially improve the full profile's point estimate over an unpenalized fit.")
    r = one(profile, market="p_ps_a", model="profile_ratings_load", comparator="ratings_load", window="recent_2022_2026")
    p(f"**Inference.** Some profile information survives ratings and workload, rather than merely reproducing them. But the corresponding conditional result in 2022 onward is {fmt(r)}, so consistency is not settled. Pinnacle coverage in the archived data largely stops in January 2026; only 71 matched 2026 matches enter this comparison. Do not describe it as validation through the whole 2026 season.")
    p("All these intervals are pointwise. Neither the earlier search across hundreds of rows nor choosing this profile after seeing its historical performance is erased by nested ridge selection. 2019 onward avoids the original feature-constant tuning years; it is **not an untouched holdout**. The profile's weak standalone score also does not prove orthogonality: its improvement conditional on the line is the relevant evidence.")
    context = pd.read_csv(DATA / "profile_context_results.csv")
    r = one(profile, market="p_ps_a", model="profile_ridge", comparator="calibrated_market", window="post_tuning_2019_2026")
    rc = one(context, market="p_ps_a", model="profile_context", comparator="context", window="post_tuning_2019_2026")
    combined = one(context, market="p_ps_a", model="profile_context", comparator="calibrated_market", window="post_tuning_2019_2026")
    p(f"**The stronger qualification:** grouping uncertainty into four-week calendar blocks gives {fmt(r, 'block4week_')} for the profile beyond calibrated Pinnacle. After adding age, age squared and surface familiarity to the ratings/load controls, the profile's marginal contribution is {fmt(rc, 'block4week_')}. The combined profile + context forecast gains {fmt(combined, 'block4week_')} over calibrated Pinnacle. That supports a small joint lead, while leaving the profile's uniquely independent contribution unresolved. The expanded controls were a follow-up stress test, not a preregistered confirmation.")
    control = one(context, market="p_ps_a", model="context", comparator="calibrated_market", window="post_tuning_2019_2026")
    p(f"The ratings/load/age/surface control block itself gains {fmt(control, 'block4week_')} over calibrated Pinnacle. It deserves to be part of the comparator for further profile research, rather than attributing every recent-form gain to the sixteen statistics.")
    recent = one(profile, market="p_ps_a", model="profile_ridge", comparator="calibrated_market", window="recent_2022_2026")
    p(f"The profile-only 2022-onward result against calibrated Pinnacle is {fmt(recent, 'block4week_')} under four-week blocks. Its interval also crosses zero, so the broader-period result should not be read as consistently confirmed across recent windows.")
    p("The group ablations do not identify a proven individual statistic: removing serve-style statistics, break/game statistics or the extra adjdef terms each weakens the point estimate, but each paired uncertainty interval includes zero. The larger historical gain at Masters 1000 events is a selected subgroup and particularly exposed to fortnight-event chronology. It does not justify choosing a betting filter. [Full market-profile notes and stress tests](profile_notes.md).")

    heading("What really adds beyond Elo")
    definitions = [
        ("Serve/return strength", "elo_sr", "elo_calibrated"),
        ("Add two-week adjusted total-points form", "elo_sr_adjperf", "elo_sr"),
        ("Then add short-memory IOS", "elo_sr_adjperf_ios_short", "elo_sr_adjperf"),
        ("Then add games-weighted Elo", "elo_sr_adjperf_ios_short_games", "elo_sr_adjperf_ios_short"),
        ("Then add age, surface familiarity and load", "elo_sr_adjperf_ios_short_games_context", "elo_sr_adjperf_ios_short_games"),
        ("Full combination versus calibrated Elo", "elo_sr_adjperf_ios_short_games_context", "elo_calibrated"),
    ]
    rows = []
    for label, model, reference in definitions:
        entries = [one(elo, tour=t, since=2022, population="all_common", model=model, reference=reference) for t in ("atp", "wta")]
        rows.append([label] + [fmt(r, "") for r in entries])
    table(["Sequential comparison, 2022 onward", "Men: gain [95% week interval]", "Women: gain [95% week interval]"], rows)
    p("These fits use a common complete-case sample for every row within each tour, with annual expanding training from 2013 and scoring from 2019. The 2022-onward samples contain 63,336 men's and 23,379 women's matches. They include qualifying and Challenger/125 levels; this table is not a closing-line comparison. IOS solves opponent-adjusted offensive and defensive strengths jointly; its short memory is the original selected four weeks for men and thirteen for women.")
    p("**Inference.** Recent adjusted points are worth keeping even after serve/return ratings. Short IOS has much less incremental value once that recent form is present; the two gains should not be added as if independent. The context block is materially useful beyond Elo. The separate load/surface/age ablations were added after seeing its combined result, so their attribution is explicitly exploratory; their gains do not add up.")
    p("On the matched-odds subset, the full forecast still trails the raw normalized average line by 9.11 milli-log-loss for men and 6.92 for women. These Elo gains support a stronger independent prediction baseline; they do not themselves establish information beyond the line. Restoring regression training from 2010 and excluding whole editions with format problems leave the context gains broadly intact.")
    p("Stored serve/return and IOS match probabilities inherit the original score-derived format and tournament-date issues. See [Elo experiment details](elo_notes.md) for the warm-up and format-sensitivity checks. This audit has not silently converted those columns into production-safe features.")

    heading("Where the promising methods leave information unused")
    table(["Priority", "Concrete follow-up", "Why it is justified / what would count"], [
        ["1. Recent statistics profile", "Recent performance surprises versus the player's own expected serve/return performance; shrink by effective exposure and predictive uncertainty. Fit a small short/long-memory combination against a market offset.", "Existing market-conditional signal. Current one-hop opponent norms still carry opponent-strength bias; the very short memory can mix form with tournament survival. Require improvement beyond line + ratings + context on a later frozen evaluation."],
        ["2. Serve/return model", "Partially pool player-by-surface serve and return deviations, with separate adaptation rates and count-aware uncertainty.", "The strongest Elo addition currently has one serve and one return rating per player; surface changes only the population intercept. Do not confuse a surface average with player-specific surface ability."],
        ["3. Recent form / IOS", "Evaluate binomial or overdispersed count likelihoods and short/long innovations against the same strong baseline; select constants inside historical training folds.", "IOS was tuned to the next statistic, while the target here is match or market residual log loss. Its promising short aggregate memory does not establish a profitable individual-statistic profile."],
        ["4. Context", "Keep age and surface familiarity; distinguish recent form from fatigue using actual rest hours, prior minutes/points and within-event versus prior-event exposure.", "Joint Elo gain is measured. Workload's positive coefficient can mean survival or form, not that fatigue is beneficial. Test state-dependent recovery, not another stable 'toughness' trait."],
    ])
    p("**Suggestions, not measured new alpha.** Surface-specific dynamic strength and shrinkage/opponent adjustment have support in [primary tennis forecasting research](sources.md). Physical studies support context-dependent recovery effects, but do not demonstrate that bookmakers miss them. A clean next experiment must freeze the feature definition, timing cutoff, market comparator and scoring rule before observing later outcomes.")
    p("A narrow extension is justified; a new sweep of hundreds of variants is not. In particular, long-memory individual-statistic IOS failing does not rule out a short-memory innovation profile—the original short IOS experiment tested aggregate serve points, not every individual statistic. Detailed implementation findings are in [method notes](method_notes.md).")

    heading("Audit findings that change how to read the old results")
    bullets([
        "**The shuffled-copy threshold is not proof of positive market value.** Permuting across a season destroys the feature's relationships with baseline strength, players and events. It is not a conditional, dependence-preserving null for 'adds nothing beyond the line'. Two men's IOS profiles clear the old market threshold while their actual market gains are negative (-0.058 and -0.206). Require a positive paired gain, dependence-aware uncertainty and later validation.",
        "**The search was not fully held out.** Constants use 2010–2018 data while headlines include 2013–2018; short IOS settings and combined models were chosen after inspecting the broader results. The adaptive family-line calculations within stages do not correct selection across both studies and all subsequent variants.",
        "**Baseline gains often mean gains over a recalibrated baseline.** The old harness refits the coefficient on Elo or market log-odds. That is a legitimate comparison, but distinct from beating the published raw probability. The new market tables give both.",
        "**Timing probes validate the proxy rule, not real availability.** Features use event start dates and rounds. A joint IOS snapshot can ingest late rounds from a fortnight-long event before another overlapping event actually starts. Passing the original mutation probes does not resolve that. Calendar normalization alone cannot fix it.",
        "**Current-match format must be prematch metadata.** The iid match-probability helpers infer format from the final score by default. Historical rules or recorded pre-match format must replace that path; dropping affected cells is only a sensitivity analysis.",
        "**Data defects still matter.** Split 2026 player identities, lower-tier match-tiebreak parsing, implausible durations and retirement treatment remain inherited. The calendar experiment rebuilds the profile only, not every Elo or opponent rating. No full source-data cleanup is claimed.",
        "**Full-sample scaling is a hygiene issue, not the main explanation.** The old unpenalized fits scale features using the whole dataset. Unpenalized predictions are essentially invariant to nonzero linear scaling, and the original profile reproduces with training-only scaling. Training-only scaling is essential once meaningful regularization is introduced.",
        "**Stage 2 did not establish an information-theoretic ceiling.** Its 'scoring luck' split comes from an iid replay and denoising assumptions applied to realized match statistics. It does not prove that all day-level variation is unknowable before play, or that failed current features close the pre-match route.",
    ])

    if (DATA / "chronology_scores.csv").exists():
        heading("Calendar timing sensitivity")
        ch = pd.read_csv(DATA / "chronology_scores.csv")
        rows = []
        for start in (2019, 2022):
            pair = [one(ch, tour="atp", variant=v, window_start=start, base="market") for v in ("original", "calendar_week")]
            rows.append([f"{start} onward", f"{int(pair[0].n):,}", f"{pair[0].imp:+.3f}", f"{pair[1].imp:+.3f}"])
        table(["Men, average line", "Same matches", "Original dates", "Calendar-week dates"], rows)
        p("Frozen adjperf constants were retained while every tournament date, including Sunday, was moved to its preceding Monday. This changes both which prior events are visible and decay ages. It is a stress test, not a justified replacement for actual match timestamps; fortnight overlap remains. The numbers above use the original unpenalized scorer to isolate feature changes. [Feature deltas and full results](../../../data/studies/feature_alpha_audit/chronology_summary.json).")
        if (DATA / "profile_chronology_results.csv").exists():
            cp = pd.read_csv(DATA / "profile_chronology_results.csv")
            rows = []
            for model, comparator, label in [("profile_ridge", "calibrated_market", "Profile versus calibrated Pinnacle"),
                                              ("profile_fixed_market", "raw_market", "Profile with fixed raw-Pinnacle offset"),
                                              ("profile_ratings_load", "ratings_load", "Profile beyond Pinnacle + ratings + load")]:
                pair = [one(cp, sample=s, market="p_ps_a", model=model, comparator=comparator,
                            window="post_tuning_2019_2026") for s in ("original_dates", "calendar_week_dates")]
                rows.append([label, fmt(pair[0], "block4week_"), fmt(pair[1], "block4week_")])
            table(["Matched Pinnacle sample, 2019 onward", "Original [95% four-week interval]", "Calendar-week [95% four-week interval]"], rows)
            p("The small standalone profile lead remains under this date perturbation, while its contribution beyond ratings and load becomes uncertain. The comparison removes one additional 2010 training row to align original and rebuilt feature availability; the 16,776 scored post-2018 rows are unchanged. This explains tiny differences from the main fit. Neither date convention is verified against complete actual-match availability.")

    heading("What I would stop spending time on")
    p("Do not prioritize replacing Elo with the tested batch Bradley–Terry model, market-embedded ratings on top of the current line, raw head-to-head or clutch records, standalone schedule/revaluation features, the strong-versus-weak opponent trait, or the tested late-decline/grinder traits. Their observed gains are absent, fragile or too small relative to the stronger candidates. This is a research-priority judgment about the tested constructions, not a universal impossibility claim.")
    p("Serving style having little incremental value for the match winner does not establish that it is useless for totals, tiebreak or in-play markets. Those targets were not evaluated, so this audit assigns them no measured alpha.")

    heading("Reproduce and inspect")
    p("The original audit used ./python.sh through Git Bash with the tennis environment's Library/bin prepended to PATH for NumPy/SciPy DLLs. Its sequence was audit_inputs.py, profile_retest.py, profile_retest.py --context, elo_retest.py, chronology.py and render_report.py. The input manifest and original_unchanged.json describe that pre-repair snapshot; they must not be replaced with hashes of the repaired code. The current [repair reproduction commands](repairs.md) supersede that sequence for corrected results. Tests live in [test/feature_alpha_audit](../../../test/feature_alpha_audit/).")
    p("The [input manifest](../../../data/studies/feature_alpha_audit/input_manifest.csv) records 261 original files and hashes. [Original score inventory](../../../data/studies/feature_alpha_audit/original_scores.csv), [profile results](../../../data/studies/feature_alpha_audit/profile_results.csv), [Elo results](../../../data/studies/feature_alpha_audit/elo_results.csv), and prediction Parquet files retain the auditable evidence. The HTML is generated from the same measured rows as this write-up.")
    p("Verification: 290 original-study tests passed across the main run and a retry of the tests initially blocked by the default temporary-directory permissions; 10 audit tests passed. Audit tests cover future-data isolation, actual side-swapped fits, cluster behavior under duplicated within-cluster observations, calendar mapping, and equivalence of the restricted profile builder to the original on a hand-made history. Numerical DLL and temporary-path issues were resolved per invocation.")
    p("Bookmaker odds are archived provider-described pre-play snapshots, not verified executable timestamps or Polymarket quotes. Better log loss does not quantify an after-cost return. Data/source access and usage limitations are recorded in the [source register](sources.md).")
    (DOCS / "README.md").write_text("\n\n".join(md) + "\n", encoding="utf-8")
    css = "body{font:17px/1.65 system-ui,sans-serif;color:#182834;background:#f7f8f5;margin:0}main{max-width:1080px;margin:auto;padding:40px 28px 80px}h1{font-size:36px;line-height:1.2;color:#103b3d}h2{font-size:24px;margin-top:42px;line-height:1.3}a{color:#126865;text-underline-offset:3px}p,li{max-width:100ch}.table{overflow-x:auto;border:1px solid #d3dcda;border-radius:8px;background:white;margin:22px 0}table{border-collapse:collapse;width:100%;font-size:15px}th,td{text-align:left;padding:13px 15px;vertical-align:top;border-bottom:1px solid #e0e6e4}th{background:#e5efeb;color:#164943}tr:last-child td{border-bottom:none}li{margin-bottom:14px}@media(max-width:600px){main{padding:24px 16px}h1{font-size:29px}th,td{min-width:150px}}"
    css += "p,li{overflow-wrap:anywhere}.table{max-width:100%}"
    (DOCS / "report.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Feature alpha audit</title><style>' + css + '</style><main>' + "\n".join(body) + '</main></html>', encoding="utf-8")
    print("Wrote README.md and report.html from measured CSV rows")


if __name__ == "__main__":
    main()

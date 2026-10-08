# Feature alpha audit: what deserves more work

**Update: the identified defects have now been repaired and the shortlist rebuilt.** Read the [repairs and corrected results](repairs.md) or [corrected HTML report](repairs.html). The original audit below records the evidence available before those repairs; its numerical conclusions are historical.

2 October 2026. Research, not a model or trading decision. Audit of the [predictability diagnostic](../predictability_diagnostic/README.md) and [UFC ideas](../ufc_ideas/README.md), with new bounded experiments. [HTML version](report.html); [code](../../../src/eda/feature_alpha_audit/); [evidence](../../../data/studies/feature_alpha_audit/).

**Keep the men's recent opponent-adjusted statistics profile as the main closing-line lead. Keep serve/return strength plus recent form as the strongest prediction features beyond Elo. Keep age, surface familiarity and recent load in that prediction baseline.** The market lead survives a stronger bookmaker comparator; its unique contribution becomes uncertain after the fullest context controls. There is no demonstrated executable betting edge.

I audited code, reports, saved outputs and tests, then ran three targeted checks: a regularized market-profile reanalysis; a joint Elo feature ladder; and a frozen-feature calendar-week timing sensitivity. The original studies were preserved. Every gain below is milli-log-loss: +1 means reducing average natural-log loss by 0.001, not increasing accuracy or return by 1%.

## The closing-line lead survived a useful challenge

**Observed.** The original men's profile reproduces exactly on 31,661 matches: +0.51 [-0.11, +1.13] against the calibrated average line. Brackets are now 95% intervals clustered by tournament-start calendar week; the original interval treated matches as independent. The profile is **16 inputs**, comprising twelve adjperf statistics and four non-duplicate adjdef statistics, not simply twelve independent skills.

| Baseline / check | Matched matches, 2019 onward | Profile improvement [95% week interval] |
| --- | --- | --- |
| Average line, recalibrated | 16,776 | +0.86 [+0.21, +1.52] |
| Pinnacle, recalibrated | 16,776 | +0.79 [+0.17, +1.42] |
| Pinnacle, raw probability | 16,776 | +0.87 [+0.20, +1.53] |
| Pinnacle fixed as an offset | 16,776 | +0.90 [+0.24, +1.56] |
| Pinnacle + serve/return + 14-day load | 16,776 | +0.57 [+0.04, +1.09] |

Both market measures are compared on exactly the same matches. The ridge penalty is chosen only from available predictions in the preceding two calendar seasons, each itself fitted on earlier seasons. There are no 2018 rows in the shared cohort, so 2019 selection uses the available 2017 predictions. Scaling also uses training data only. The market slope is unpenalized; the fixed-offset check keeps that slope at one. These comparisons separate feature contribution from simple market recalibration. Regularization did not materially improve the full profile's point estimate over an unpenalized fit.

**Inference.** Some profile information survives ratings and workload, rather than merely reproducing them. But the corresponding conditional result in 2022 onward is +0.54 [-0.08, +1.17], so consistency is not settled. Pinnacle coverage in the archived data largely stops in January 2026; only 71 matched 2026 matches enter this comparison. Do not describe it as validation through the whole 2026 season.

All these intervals are pointwise. Neither the earlier search across hundreds of rows nor choosing this profile after seeing its historical performance is erased by nested ridge selection. 2019 onward avoids the original feature-constant tuning years; it is **not an untouched holdout**. The profile's weak standalone score also does not prove orthogonality: its improvement conditional on the line is the relevant evidence.

**The stronger qualification:** grouping uncertainty into four-week calendar blocks gives +0.79 [+0.13, +1.46] for the profile beyond calibrated Pinnacle. After adding age, age squared and surface familiarity to the ratings/load controls, the profile's marginal contribution is +0.51 [-0.08, +1.10]. The combined profile + context forecast gains +1.05 [+0.28, +1.82] over calibrated Pinnacle. That supports a small joint lead, while leaving the profile's uniquely independent contribution unresolved. The expanded controls were a follow-up stress test, not a preregistered confirmation.

The ratings/load/age/surface control block itself gains +0.54 [+0.10, +0.97] over calibrated Pinnacle. It deserves to be part of the comparator for further profile research, rather than attributing every recent-form gain to the sixteen statistics.

The profile-only 2022-onward result against calibrated Pinnacle is +0.85 [-0.07, +1.76] under four-week blocks. Its interval also crosses zero, so the broader-period result should not be read as consistently confirmed across recent windows.

The group ablations do not identify a proven individual statistic: removing serve-style statistics, break/game statistics or the extra adjdef terms each weakens the point estimate, but each paired uncertainty interval includes zero. The larger historical gain at Masters 1000 events is a selected subgroup and particularly exposed to fortnight-event chronology. It does not justify choosing a betting filter. [Full market-profile notes and stress tests](profile_notes.md).

## What really adds beyond Elo

| Sequential comparison, 2022 onward | Men: gain [95% week interval] | Women: gain [95% week interval] |
| --- | --- | --- |
| Serve/return strength | +4.74 [+4.01, +5.48] | +3.12 [+2.21, +4.02] |
| Add two-week adjusted total-points form | +1.03 [+0.59, +1.47] | +1.26 [+0.37, +2.15] |
| Then add short-memory IOS | +0.13 [+0.05, +0.20] | +0.25 [+0.13, +0.36] |
| Then add games-weighted Elo | +0.31 [-0.01, +0.62] | +0.93 [+0.41, +1.45] |
| Then add age, surface familiarity and load | +4.90 [+4.16, +5.64] | +3.93 [+2.75, +5.12] |
| Full combination versus calibrated Elo | +11.10 [+9.94, +12.27] | +9.49 [+7.68, +11.29] |

These fits use a common complete-case sample for every row within each tour, with annual expanding training from 2013 and scoring from 2019. The 2022-onward samples contain 63,336 men's and 23,379 women's matches. They include qualifying and Challenger/125 levels; this table is not a closing-line comparison. IOS solves opponent-adjusted offensive and defensive strengths jointly; its short memory is the original selected four weeks for men and thirteen for women.

**Inference.** Recent adjusted points are worth keeping even after serve/return ratings. Short IOS has much less incremental value once that recent form is present; the two gains should not be added as if independent. The context block is materially useful beyond Elo. The separate load/surface/age ablations were added after seeing its combined result, so their attribution is explicitly exploratory; their gains do not add up.

On the matched-odds subset, the full forecast still trails the raw normalized average line by 9.11 milli-log-loss for men and 6.92 for women. These Elo gains support a stronger independent prediction baseline; they do not themselves establish information beyond the line. Restoring regression training from 2010 and excluding whole editions with format problems leave the context gains broadly intact.

Stored serve/return and IOS match probabilities inherit the original score-derived format and tournament-date issues. See [Elo experiment details](elo_notes.md) for the warm-up and format-sensitivity checks. This audit has not silently converted those columns into production-safe features.

## Where the promising methods leave information unused

| Priority | Concrete follow-up | Why it is justified / what would count |
| --- | --- | --- |
| 1. Recent statistics profile | Recent performance surprises versus the player's own expected serve/return performance; shrink by effective exposure and predictive uncertainty. Fit a small short/long-memory combination against a market offset. | Existing market-conditional signal. Current one-hop opponent norms still carry opponent-strength bias; the very short memory can mix form with tournament survival. Require improvement beyond line + ratings + context on a later frozen evaluation. |
| 2. Serve/return model | Partially pool player-by-surface serve and return deviations, with separate adaptation rates and count-aware uncertainty. | The strongest Elo addition currently has one serve and one return rating per player; surface changes only the population intercept. Do not confuse a surface average with player-specific surface ability. |
| 3. Recent form / IOS | Evaluate binomial or overdispersed count likelihoods and short/long innovations against the same strong baseline; select constants inside historical training folds. | IOS was tuned to the next statistic, while the target here is match or market residual log loss. Its promising short aggregate memory does not establish a profitable individual-statistic profile. |
| 4. Context | Keep age and surface familiarity; distinguish recent form from fatigue using actual rest hours, prior minutes/points and within-event versus prior-event exposure. | Joint Elo gain is measured. Workload's positive coefficient can mean survival or form, not that fatigue is beneficial. Test state-dependent recovery, not another stable 'toughness' trait. |

**Suggestions, not measured new alpha.** Surface-specific dynamic strength and shrinkage/opponent adjustment have support in [primary tennis forecasting research](sources.md). Physical studies support context-dependent recovery effects, but do not demonstrate that bookmakers miss them. A clean next experiment must freeze the feature definition, timing cutoff, market comparator and scoring rule before observing later outcomes.

A narrow extension is justified; a new sweep of hundreds of variants is not. In particular, long-memory individual-statistic IOS failing does not rule out a short-memory innovation profile—the original short IOS experiment tested aggregate serve points, not every individual statistic. Detailed implementation findings are in [method notes](method_notes.md).

## Audit findings that change how to read the old results

- **The shuffled-copy threshold is not proof of positive market value.** Permuting across a season destroys the feature's relationships with baseline strength, players and events. It is not a conditional, dependence-preserving null for 'adds nothing beyond the line'. Two men's IOS profiles clear the old market threshold while their actual market gains are negative (-0.058 and -0.206). Require a positive paired gain, dependence-aware uncertainty and later validation.
- **The search was not fully held out.** Constants use 2010–2018 data while headlines include 2013–2018; short IOS settings and combined models were chosen after inspecting the broader results. The adaptive family-line calculations within stages do not correct selection across both studies and all subsequent variants.
- **Baseline gains often mean gains over a recalibrated baseline.** The old harness refits the coefficient on Elo or market log-odds. That is a legitimate comparison, but distinct from beating the published raw probability. The new market tables give both.
- **Timing probes validate the proxy rule, not real availability.** Features use event start dates and rounds. A joint IOS snapshot can ingest late rounds from a fortnight-long event before another overlapping event actually starts. Passing the original mutation probes does not resolve that. Calendar normalization alone cannot fix it.
- **Current-match format must be prematch metadata.** The iid match-probability helpers infer format from the final score by default. Historical rules or recorded pre-match format must replace that path; dropping affected cells is only a sensitivity analysis.
- **Data defects still matter.** Split 2026 player identities, lower-tier match-tiebreak parsing, implausible durations and retirement treatment remain inherited. The calendar experiment rebuilds the profile only, not every Elo or opponent rating. No full source-data cleanup is claimed.
- **Full-sample scaling is a hygiene issue, not the main explanation.** The old unpenalized fits scale features using the whole dataset. Unpenalized predictions are essentially invariant to nonzero linear scaling, and the original profile reproduces with training-only scaling. Training-only scaling is essential once meaningful regularization is introduced.
- **Stage 2 did not establish an information-theoretic ceiling.** Its 'scoring luck' split comes from an iid replay and denoising assumptions applied to realized match statistics. It does not prove that all day-level variation is unknowable before play, or that failed current features close the pre-match route.

## Calendar timing sensitivity

| Men, average line | Same matches | Original dates | Calendar-week dates |
| --- | --- | --- | --- |
| 2019 onward | 18,651 | +0.932 | +0.862 |
| 2022 onward | 12,344 | +0.922 | +0.888 |

Frozen adjperf constants were retained while every tournament date, including Sunday, was moved to its preceding Monday. This changes both which prior events are visible and decay ages. It is a stress test, not a justified replacement for actual match timestamps; fortnight overlap remains. The numbers above use the original unpenalized scorer to isolate feature changes. [Feature deltas and full results](../../../data/studies/feature_alpha_audit/chronology_summary.json).

| Matched Pinnacle sample, 2019 onward | Original [95% four-week interval] | Calendar-week [95% four-week interval] |
| --- | --- | --- |
| Profile versus calibrated Pinnacle | +0.79 [+0.13, +1.46] | +0.71 [+0.03, +1.38] |
| Profile with fixed raw-Pinnacle offset | +0.90 [+0.19, +1.61] | +0.81 [+0.09, +1.53] |
| Profile beyond Pinnacle + ratings + load | +0.57 [+0.00, +1.13] | +0.52 [-0.05, +1.09] |

The small standalone profile lead remains under this date perturbation, while its contribution beyond ratings and load becomes uncertain. The comparison removes one additional 2010 training row to align original and rebuilt feature availability; the 16,776 scored post-2018 rows are unchanged. This explains tiny differences from the main fit. Neither date convention is verified against complete actual-match availability.

## What I would stop spending time on

Do not prioritize replacing Elo with the tested batch Bradley–Terry model, market-embedded ratings on top of the current line, raw head-to-head or clutch records, standalone schedule/revaluation features, the strong-versus-weak opponent trait, or the tested late-decline/grinder traits. Their observed gains are absent, fragile or too small relative to the stronger candidates. This is a research-priority judgment about the tested constructions, not a universal impossibility claim.

Serving style having little incremental value for the match winner does not establish that it is useless for totals, tiebreak or in-play markets. Those targets were not evaluated, so this audit assigns them no measured alpha.

## Reproduce and inspect

The original audit used ./python.sh through Git Bash with the tennis environment's Library/bin prepended to PATH for NumPy/SciPy DLLs. Its sequence was audit_inputs.py, profile_retest.py, profile_retest.py --context, elo_retest.py, chronology.py and render_report.py. The input manifest and original_unchanged.json describe that pre-repair snapshot; they must not be replaced with hashes of the repaired code. The current [repair reproduction commands](repairs.md) supersede that sequence for corrected results. Tests live in [test/feature_alpha_audit](../../../test/feature_alpha_audit/).

The [input manifest](../../../data/studies/feature_alpha_audit/input_manifest.csv) records 261 original files and hashes. [Original score inventory](../../../data/studies/feature_alpha_audit/original_scores.csv), [profile results](../../../data/studies/feature_alpha_audit/profile_results.csv), [Elo results](../../../data/studies/feature_alpha_audit/elo_results.csv), and prediction Parquet files retain the auditable evidence. The HTML is generated from the same measured rows as this write-up.

Verification: 290 original-study tests passed across the main run and a retry of the tests initially blocked by the default temporary-directory permissions; 10 audit tests passed. Audit tests cover future-data isolation, actual side-swapped fits, cluster behavior under duplicated within-cluster observations, calendar mapping, and equivalence of the restricted profile builder to the original on a hand-made history. Numerical DLL and temporary-path issues were resolved per invocation.

Bookmaker odds are archived provider-described pre-play snapshots, not verified executable timestamps or Polymarket quotes. Better log loss does not quantify an after-cost return. Data/source access and usage limitations are recorded in the [source register](sources.md).

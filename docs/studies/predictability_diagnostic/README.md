# Predictability diagnostic

> **Correction, 2 October 2026:** These are historical results. The audit found chronology, forecast-format and evaluation defects. The shared code and shortlisted features have been repaired; see the [repair report](../feature_alpha_audit/repairs.md). Original numerical results below have not been relabelled as corrected results.

**Status: study, not a decision.** An exploratory pass run one stage per session, each stopping for the owner's review. Nothing here chooses features, models, markets or a roadmap. All five stages and the summary are written (2 Oct 2026); each waits for the owner's review, and the open decisions are listed at the end of [summary.md](summary.md).

## In short

Plain-language detail is in [summary.md](summary.md) and at the top of the [report](report.html).

* **Observed. The bookmakers stay ahead.** No feature improves on their closing prices by more than 0.3% of the way from a coin flip to their prices.
* **Observed. A few features beat Elo, modestly.** Serve-and-return strength ratings do best, closing about 28% (men) and 29% (women) of the gap between Elo and the bookmakers. Recent points won, recent workload and a new surface add less. "Clutch" records, serving style, head to head and player background add little or nothing.
* **Inferred. Pre-match records look priced in.** An edge, if any, is more likely in live (in-play) data or in markets less sharp than the bookmakers' closing prices.
* **Observed. The numbers were checked.** A script checked every number in the report against the data files, and none was wrong.

## Write-ups

* [summary.md](summary.md): the summary, in plain language. What helps beyond Elo and the bookmakers, what to do next, and every open decision.
* [report.html](report.html): the HTML report. The summary opens the page, and the five stages follow as reference.
* [stage0.md](stage0.md), the analysis table, and [audit_stage0.md](audit_stage0.md), its audit.
* [stage1.md](stage1.md): how predictable (the baselines).
* [stage2.md](stage2.md): the anatomy of a win.
* [stage3.md](stage3.md): which statistics repeat.
* [candidates.md](candidates.md): the Stage 4 candidate list, approved on 1 Oct 2026.
* [stage4.md](stage4.md), the rundown, and [audit_stage4.md](audit_stage4.md), its audit.

## Brief

Study: predictability_diagnostic. A first exploratory pass over this repository's tennis data: how predictable matches are, and which historical statistics predict the winner beyond a rating and beyond the closing odds. The owner builds UFC prediction models and knows sports modelling, but is new to tennis: define each tennis term once and explain every number plainly. This is exploration; it chooses no features, models, markets or roadmap. Label results as observed, inferred or suggestion.

Stages, one session each: 0 analysis table; 1 how predictable (baselines); 2 anatomy of a win and 3 traits (may run side by side); the Stage 4 candidate list, approved by the owner before anything is computed; 4 the rundown; the summary.

Scope (owner defaults; the README's Owner decisions override them):
- Singles only. ATP and WTA analysed separately, always shown side by side.
- Evaluation matches: Grand Slams, Tour Finals, 1000s, 500s, 250s, their qualifying, and Challenger / WTA 125 main draws and qualifying. Completed and retired matches count, retirements flagged; the player who advanced won. Walkovers are excluded.
- Evaluation years 2013–2026; 2010–2012 warm up the ratings. Headline window 2022–2026. Eras: 2013–16, 2017–19, 2020–21, 2022–26.
- WTA box scores before 2019 have holes (whole levels missing in some years): use them as history, but evaluate WTA box-score features from 2019 on.
- History for ratings and features: every singles level from 2010, ITF and team events included.
- Never included: doubles, exhibitions, juniors. Out of scope: betting simulation, and any model beyond logistic regression on a few inputs.

Rules:
- Follow CLAUDE.md (./python.sh, filing, no Git commands that change state).
- Code in src/eda/predictability_diagnostic/, shared helpers in common.py; tests in test/predictability_diagnostic/; outputs in data/studies/predictability_diagnostic/, named stageN_...; write-ups in docs/studies/predictability_diagnostic/ (README.md, one stageN.md per stage, report.html).
- Derived tables as Parquet (the repo ignores Parquet; scripts rebuild it). Summaries as JSON or CSV. Hand-made tables, such as a code mapping, as CSV so git tracks them. Any other file over 50 MB goes in data/LARGE_FILES.md.
- The report is built by a script from the stages' JSON. Each stage adds its section as its own file; the builder assembles whatever sections exist, in stage order. Load the dataviz skill, if available, before writing any chart.
- Compute every number before stating it; no write-up holds a number a script did not produce.
- Log loss only, never AUC. Differences in milli-log-loss, with the word better or worse. Groups under about 300 matches are directional only.
- A feature for a match may use only earlier events and earlier rounds of the same event. Compute features in one chronological pass; a per-row look-back takes hours per column at this size.
- Use the tennis environment's packages (pandas, pyarrow, scikit-learn, matplotlib); ask before adding any. Use only data on disk; leave running downloads alone.
- Earlier stages were reviewed by the owner: use their outputs as they are. If you find a problem in one, report it; don't fix it silently.
- Do only your stage, then stop for the owner's review.

## Owner decisions

Dated entries go here; they override the Brief's scope defaults.

* **30 Sep 2026, before Stage 1:** none since the last review. Stage 0's seven decisions and the Stage 0 audit's suggestions ([audit_stage0.md](audit_stage0.md)) remain open; Stage 1 uses the Stage 0 table as built.
* **30 Sep 2026, after Stage 1:** Elo is a rough, exploratory baseline that may not be used in a final model; its details are not to be worked further. Stage 1's three Elo items are closed at the defaults it suggested: retirements counted, surface Elo as the rating, the tuned constants frozen. The owner's aim is an edge on the market from point-by-point data; results-only (win/loss) information is taken to be priced in.
* **30 Sep 2026, before Stage 2:** none since the last review.
* **1 Oct 2026, before Stage 3:** none since the last review.
* **1 Oct 2026, before the Stage 4 candidate list:** none since the last review.
* **1 Oct 2026, on the Stage 4 candidate list:** the exponentially decayed form uses a 52-week half-life (the plan had proposed 13 weeks). The rest of the list still awaits approval.
* **1 Oct 2026, before Stage 4:** [candidates.md](candidates.md) approved as written. Stage 4 reads this as approving every choice the plan marks "as planned" in its section 9: history from every level for results-based statistics, with the opponent-adjusted form as the fix; retirements left out of box-score histories; the record against the opponent's hand kept; the reading rule and the expectation scale as set; the tournament's country from a hand-made table built at the start of Stage 4; fatigue windows counted between event start dates; each entry type scored only where its code appears, the women's protected ranking kept; the earlier stages' tables used as built.
* **2 Oct 2026, before the summary:** none since the last review.

## Stages

| Stage | Status | Write-up |
|---|---|---|
| 0. Analysis table | Built 30 Sep 2026; waiting for the owner's review, with decisions listed | [stage0.md](stage0.md) · [report](report.html) (section "Data used") |
| 1. How predictable (baselines) | Built 30 Sep 2026; waiting for the owner's review, with decisions listed | [stage1.md](stage1.md) · [report](report.html) (section "How predictable is tennis?") |
| 2. Anatomy of a win | Built 30 Sep 2026; waiting for the owner's review, with decisions listed | [stage2.md](stage2.md) · [report](report.html) (section "Anatomy of a win") |
| 3. Traits | Built 1 Oct 2026; waiting for the owner's review, with decisions listed | [stage3.md](stage3.md) · [report](report.html) (section "Which statistics repeat") |
| Stage 4 candidate list | Written 1 Oct 2026; half-life decided (52 weeks); approved as written 1 Oct 2026 | [candidates.md](candidates.md) |
| 4. The rundown | Built 1 Oct 2026; waiting for the owner's review, with decisions listed | [stage4.md](stage4.md) · [report](report.html) (section "The rundown") |
| Audits | Stage 0 audited 30 Sep 2026, Stage 4 on 2 Oct 2026: reviews, not decisions | [audit_stage0.md](audit_stage0.md) · [audit_stage4.md](audit_stage4.md) |
| Summary | Written 2 Oct 2026; waiting for the owner's review, with decisions listed | [summary.md](summary.md) · [report](report.html) (section "What we found", at the top of the page) |

## Files

| What | Where |
|---|---|
| Shared helpers: scope, loaders, the chronological order, the as-of helper and its leakage probe | `src/eda/predictability_diagnostic/common.py` |
| Stage 0 build and checks | `src/eda/predictability_diagnostic/stage0_build.py`, `stage0_checks.py` |
| Stage 1: closing odds linked to the matches; the baselines (coin, ranking, Elo, surface Elo, market); their scores | `src/eda/predictability_diagnostic/stage1_odds.py`, `stage1_baselines.py`, `stage1_results.py` |
| Stage 2: the iid point model, the Grand Slam deciding-set rules and a point-by-point simulator; what decides a match, with the pure-luck replay; big points in the Grand Slam point-by-point files (optional part) | `src/eda/predictability_diagnostic/stage2_iid.py`, `stage2_anatomy.py`, `stage2_pbp.py`; the hand-made rules table `data/studies/predictability_diagnostic/stage2_slam_final_set_rules.csv` |
| Stage 3: the serve and return ratings (pre-match values for every match); reliability, shrinkage, carry-over, next-match forecasts and verdicts of every per-match rate | `src/eda/predictability_diagnostic/stage3_ratings.py`, `stage3_traits.py` |
| Stage 4 plan: the candidate list (hand-made) and its coverage and comparison counts | `data/studies/predictability_diagnostic/stage4_candidates.csv`; `src/eda/predictability_diagnostic/stage4_candidates.py` |
| Stage 4: each event's country (hand-made table) and its check against tennis-data.co.uk and the WTA's records | `data/studies/predictability_diagnostic/stage4_event_country.csv`; `src/eda/predictability_diagnostic/stage4_country.py` |
| Stage 4: every candidate's features in one chronological pass, the constants set in Stage 4, the probe cut by date, event and round; the rundown (walk-forward scores, null bands, the family-wide line, direction by era and level, leak checks) | `src/eda/predictability_diagnostic/stage4_features.py`, `stage4_rundown.py` |
| Summary: every number it quotes (the coin-to-bookmakers scale, each feature family's share of Elo's gap to the bookmakers, the skill-or-luck chart) | `src/eda/predictability_diagnostic/summary_results.py` |
| Summary: the number check of report.html against the JSON outputs, with its self-test of planted errors | `src/eda/predictability_diagnostic/summary_number_check.py` (needs the Chromium that Playwright installed) |
| Report builder (the summary first, then the stages folded as reference), page shell and one section module per stage and for the summary | `src/eda/predictability_diagnostic/render_report.py`, `report_shell.html`, `report_stage0.py`, `report_stage1.py`, `report_stage2.py`, `report_stage3.py`, `report_stage4.py`, `report_summary.py` |
| Tests | `test/predictability_diagnostic/` |
| Tables (Parquet, rebuilt by the scripts) and evidence (CSV, JSON) | `data/studies/predictability_diagnostic/` |

Rebuild, from the repository root: `./python.sh src/eda/predictability_diagnostic/stage0_build.py`, then `stage0_checks.py` (about a minute for the build and a quarter of a minute for the checks); then `stage1_odds.py`, `stage1_baselines.py` and `stage1_results.py` (6 seconds, 5½ minutes and 8 seconds); then `stage2_anatomy.py` and `stage2_pbp.py` (about 1½ minutes each); then `stage3_ratings.py` and `stage3_traits.py` (about 2 and 2½ minutes); then `stage4_candidates.py` (under a minute; the plan's coverage counts); then `stage4_country.py`, `stage4_features.py` and `stage4_rundown.py` (about 15 seconds, 9 minutes and 13 minutes); then `summary_results.py` (seconds); then `render_report.py`; then `summary_number_check.py` (about 1½ minutes; `--self-test` about 5). Tests with `./python.sh -m pytest test/predictability_diagnostic`.

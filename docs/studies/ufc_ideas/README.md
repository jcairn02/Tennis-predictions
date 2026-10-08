# Ideas borrowed from UFC-predictions

> **Update, 5 October 2026.** Three of this study's methods released every result of an event whose start date preceded the solve: Stage B's IOS ratings, and Stage A's Bradley–Terry and MESR. Results of events still running therefore leaked into other matches played before them.
>
> * IOS has been rebuilt leak-proof in the [match-timing study](../match_timing/README.md).
> * Bradley–Terry and MESR must be rebuilt the same way before any use.
>
> The rule is in [CLAUDE.md](../../../CLAUDE.md), section "Feature timing".
>
> **Correction, 2 October 2026:** These are historical results. The audit found chronology, forecast-format and evaluation defects. The shared code and shortlisted features have been repaired; see the [repair report](../feature_alpha_audit/repairs.md). Original numerical results below have not been relabelled as corrected results.

**Status: study, not a decision.** A second exploratory pass over the same data as the [predictability diagnostic](../predictability_diagnostic/README.md), started 2 Oct 2026. It tries the rating and feature machinery of the owner's UFC project in tennis, to narrow the gap between what a model predicts and the bookmakers' closing line, or to find information the closing line does not price. Nothing here chooses features, models, markets or a roadmap.

## The question

The earlier study found that serve-and-return strength ratings close about 28% (men) and 29% (women) of the gap between Elo and the bookmakers, and that nothing beats the closing line by more than 0.3% of the way from a coin flip to it. The UFC pipeline has tools that the earlier study did not try:

* **A tuned Bradley–Terry rating (BT)** in place of Elo: every result re-solved at once with a time decay and a ridge toward an anchor, so every win is credited at what the opponent turned out to be worth. In UFC it beats Elo clearly.
* **Opponent-adjusted statistics (adjperf / adjdef) and IOS ridge ratings.** adjperf scores a player's statistic against what that opponent usually allows; adjdef scores how far a player held opponents below their own norm; IOS solves an offense and a defense rating per statistic as a ridge regression over the whole history. In UFC the samples are small and fights end early; in tennis every match is the same length and the samples are large, so these should converge better. The key is **who the statistics were produced against**: a player who comes up just short against strong opponents and crushes weak ones looks the same to Elo as a steady one.
* **Strength of schedule (SoS)** and the UFC's retrospective credit for old opponents.
* **Market-embedded skill ratings (MESR)**: a rating solved from closing odds rather than results.
* **Fatigue**: whether a player degrades as matches get long.

What does not carry over: the UFC exposure exponents (beta, tau) that weight a fight by its length, since tennis matches are the same length to a first approximation; a decay rate and a shrinkage constant still matter.

## Stages

| Stage | What | Status | Write-up |
|---|---|---|---|
| A | Bradley–Terry rating tuned for tennis, against Elo; MESR from closing odds | Built 2 Oct 2026 (about 4 hours of compute, mostly the widened grids; 21 tests pass; 48 probe cuts clean). The tuned BT is worse than surface Elo by 1.60 (men) and 4.45 (women) milli-log-loss, and closes −8% and −32% of the Elo-to-market gap; a surface BT is 0.58 better than Elo for the men only; MESR adds nothing given the odds (−0.03, −0.02) | [stageA.md](stageA.md) |
| B | adjperf / adjdef, IOS ridge ratings per statistic, and performance split by opponent strength | Built 2 Oct 2026 (about 55 minutes of compute; 10 tests pass; three probes clean). adjperf of total points won with a 2-week half-life +3.19 (men) and +3.32 (women) given Elo, beside the earlier ratings' +3.61 and +4.58; IOS with a short memory +3.72 and +5.02 (diagnostic rows added after the first rundown, disclosed); adjdef is adjperf's mirror; the opponent-strength split loses information; nothing clear on the market | [stageB.md](stageB.md) |
| C | Strength of schedule, retrospective credit for old opponents, fatigue | Built 2 Oct 2026 (about 9 minutes of compute; 15 tests pass; both probes clean). Schedule: worse for the men, the women's quality of wins +0.95 given Elo; credit through opponents lost to +0.16 (men) and +0.41 (women); fatigue no sign; nothing on the market | [stageC.md](stageC.md) |
| D | The best of everything together; the individual-statistic profiles together against the odds; the report | Built 2 Oct 2026 (about 5 minutes). Everything together adds 9.35 (men) and 9.86 (women) given Elo and 0.31 and 0.32 given the odds; the men's 2-week adjperf profile of twelve individual statistics adds 0.51 given the odds (0.92 in 2022–2026), the largest gain on the closing line in either study, the women's nothing | [stageD.md](stageD.md) · [report.html](report.html) |

## Brief (every stage follows this)

**Scope.** Exactly the earlier study's: singles only; ATP and WTA separately, side by side; evaluation matches are the Grand Slams, Tour Finals, 1000s, 500s, 250s, their qualifying, and Challenger / WTA 125 main draws and qualifying (completed or retired; walkovers excluded); evaluation years 2013–2026 with 2010–2012 as warm-up; headline window 2022–2026; eras 2013–16, 2017–19, 2020–21, 2022–26; history for ratings and features is every singles level from 2010. WTA box-score features are scored from 2019. Doubles, exhibitions and juniors never. No betting simulation, and no model beyond logistic regression on a few inputs.

**One pool, one protocol.** Every feature is built for the pool of `data/studies/predictability_diagnostic/stage4_features.parquet` (every evaluation-level match of 2010–2026, completed or retired; 255,123 matches; side A random) and scored with the shared harness `src/eda/ufc_ideas/common.py`, which is the earlier study's Stage 4 rundown with any baseline column allowed: walk-forward by season, a logistic regression without an intercept, three scores (alone; given surface Elo; given the closing odds), 20 shuffled copies as the null band, the family-wide line, the reading rule (finding / possible / no sign / worse) and the size scale (small under 1 milli-log-loss, clear from 1). The harness reproduces the earlier study's numbers to the last digit (checked 2 Oct 2026 on the ratings-through-the-iid-model and games-weighted-Elo rows).

**Rules.**

* Follow [CLAUDE.md](../../../CLAUDE.md): `./python.sh`, the filing table, no Git command that changes state, no deletion of temporary files mid-session.
* The earlier study's code and tables are read-only. Import them (`src.eda.predictability_diagnostic.common`, `stage1_baselines`, `stage2_iid`, `stage3_ratings`, `stage3_traits`, `stage4_features`, `stage4_rundown`); never edit them or their outputs.
* Code in `src/eda/ufc_ideas/`, named `stageX_*.py`; tests in `test/ufc_ideas/test_stageX.py`; outputs in `data/studies/ufc_ideas/`, named `stageX_*` (Parquet for big tables, which git ignores; CSV and JSON for evidence); the write-up `docs/studies/ufc_ideas/stageX.md`; the report section `src/eda/ufc_ideas/report_stageX.py`.
* A feature for a match may use only earlier events and earlier rounds of the same event: never the match itself, another match of the same round, or another event of the same week. A batch rating solved at a snapshot uses only earlier weeks' matches (and may add the same event's earlier rounds through an incremental update if it does so leak-free). Every new rating or feature family gets a black-box probe cut by date, event and round (as `stage3_ratings.probe_by_round` and `stage4_features.probe` do), and its result is reported.
* Constants are tuned on 2013–2018 only (2010–2012 warm up), then frozen; every score is also given for 2019–2026 and 2022–2026.
* Compute every number before stating it: no write-up holds a number a script did not produce, and the report section reads its numbers from the stage's JSON. Log loss only, never AUC; differences in milli-log-loss, with the word better or worse; groups under 300 matches are directional only.
* Label results **observed** (measured), **inferred** (a reading) or **suggestion** (a proposal). Define each tennis or UFC term once. The owner builds UFC models and knows sports modelling, but is new to tennis.
* Compute: 16 cores and plenty of memory, but stages run side by side: at most 5 worker processes per stage, and plan each script to finish within about 45 minutes (coarser tuning grids or snapshots are fine if the choice is stated).
* Problems found in the earlier study's data or code are reported in the write-up, not fixed.

**What each stage delivers.**

1. `stageX_features.parquet`: the pool columns plus one column per feature (A − B, missing where the feature does not exist for both players), through `common.load_pool()`.
2. `stageX_ranking.csv`, `stageX_results.csv`, `stageX_null_copies.csv`, `stageX_results.json`: the harness's rundown.
3. `stageX_catalog.json`: one entry per scored row id: `id`, `name`, `family`, a one-line description of the feature, and (where it applies) which constants were tuned and chosen, so that the final page can list every feature tried and how it did.
4. `stageX_results.json` may also hold anything else the write-up quotes (tuning grids, probes, comparisons).
5. `stageX.md` and `report_stageX.py` (contract: `SECTION = {"stage": "X", "id": ..., "title": ...}` and `render(study_dir) -> {"html": str, "data": dict, "script": str}`, built from the stage's JSON only; the page shell's CSS classes are in `src/eda/predictability_diagnostic/report_shell.html`).
6. Tests: hand-made histories against a row-by-row reading of each rule; the time rule; the solver against a reference (for example a dense solve on a toy problem).

## Files

| What | Where |
|---|---|
| Shared harness: the pool, tasks, the rundown with any baseline column, the earlier ranking for comparisons | `src/eda/ufc_ideas/common.py` |
| The stages' code, tests, outputs and write-ups | as the Brief names them |
| The report (the new summary, the stages, and the earlier study's summary folded as reference) | `docs/studies/ufc_ideas/report.html`, built by `src/eda/ufc_ideas/render_report.py` |

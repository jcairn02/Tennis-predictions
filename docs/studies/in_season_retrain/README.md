# Retrains you call: this season's matches in training, stage 2 grown with them

20–21 Oct 2026 · For the owner · Status: **built and checked; the first retrain waits for your word on the day** ·
[Process log](process_log.md) · Decision: [the amendment of 20 Oct](../../decisions/2026-10-09-adoption-by-change-class.md)

## What you asked

> "it is a massive error that we are not using any 2026 for training the tabpfn3.5 production models ... As of now ,
> Id like to only re-train manually , when I say its time to retrain. (a timer can exist that watches time since last
> retrain so im informed off it on the masters script)"

Then: record the rule, build the setup and the check, and let stage 2 grow too, with the check made fast ("24 hours is
an unreasonble cost time wise").

## The first retrain: done 21 Oct 2026, live from 10:59 PDT

* **The new model** (`template_2026-10-21`) trains on **67,531 matches**, 2013 to 19 Oct 2026, against 62,869
  (2013–2025) before: every 2026 match of its frame (4,662). 75 main-tour matches of 2026 are not training rows yet
  (mostly the last few days, waiting for their closing odds).
* **Stage 2 grown:** men's slope 0.901 → 0.906, women's 0.923 → 0.933, the speed number 0.033 → 0.038 (daily feed);
  the annual set logged beside it on every run.
* **The harm check against the 16 Oct model** (2020–2026, both tours, both stages, + = new better): −0.012
  [−0.027, +0.003] mLL, unresolved: no harm. 2020–2024 identical (0.000); the difference is 2025–26, mostly women
  (−0.078 [−0.18, +0.03], unresolved), from Tennis My Life's women's corrections accepted that morning.
* **The replay proof passed** (23 matches; IOS inputs exact; every input within 4.4e-6). The TabPFN caches on the new
  rows are already built; Thinking's paid fit on them comes with the first A4 that has Thinking on (about 180k tokens).
* **Before it, that morning:** every download run by hand (results, the three held files reviewed and accepted, a
  21-day speed backfill, match days, odds, the lower-level feed); the shared tables rebuilt; 163 GB of the replaced
  builds' caches deleted at the owner's sign-off. Two launch failures were fixed on the way (a launch tied to the
  session, then a shell without conda's paths); the notebook's C0 now launches the working way.
* **The rollback,** should it be wanted: `tp.use_instance("template_2026-10-16", tree="C:/Users/zerom/tnr_tpl1016")`.
* **A flaw found after it (21 Oct, afternoon): its newest matches were priced at the books' average.** Every new row
  has a closing line (none blank; no exchange prices: the rule is Pinnacle, then BetOnline, then the average), but the
  scripted builds since 13 Oct ran a copy of the finishing steps without OddsTrader's refresh, so from late September
  the average stood in for BetOnline's closes that were on disk (September 164 of 323 matches, October 149 of 149,
  against 3-9% before). Fixed in the code the same day: the odds step refreshes OddsTrader's tables itself and refuses
  stale ones; one copy of the finishing steps; the download asks only for new matches; an OddsTrader price that is the
  mirror image of the other books (the sides swapped in its matching: 4 matches, e.g. Bergs v Alcaraz) is left out
  (*turned round the same evening*: all four were tennis-data rows with the prices swapped, and from the next retrain
  OddsTrader's price wins; [decision amendment](../../decisions/2026-10-09-pinnacle-first-odds-input.md)). On a
  copy of this instance, 291 of 67,531 rows change (288 recent matches to BetOnline). **Corrected the same day, at the
  owner's word** ("Yes, start now (Recommended)"): `template_2026-10-21b`, the same build finished with the repaired odds
  step, **live since 16:39 PDT**. Harm check against the morning's instance: +0.018 [−0.074, +0.110] mLL (+ = the
  corrected better), unresolved, no harm; the replay passed (23 matches, IOS exact, every input within 4.4e-6); stage 2
  grown: men's slope 0.9056 → 0.9051, women's 0.9326 unchanged. Its evaluation-only fits (seeds 4-15, 2019-2025) were
  paused after the switch, since a bet day started during them would wait on them for the card, and resume at 03:00 on
  22 Oct ([process log](process_log.md), § 4c). The rollback to the morning's instance:
  `tp.use_instance("template_2026-10-21", tree="C:/Users/zerom/tnr_tpl1021")`.

## The rule (recorded as an amendment to the 9 Oct decision)

* **A retrain you call** builds the model on the day's tables and trains its live fit on 2013 through the retrain's
  cut-off, so this season's finished matches become training rows. Thinking trains on the same rows.
* **Stage 2 grows with it:** its calibration slopes and speed number are refitted on 2019 through the cut-off. For this
  season's matches it reads the forecasts the season-start model made of them, which are out of sample.
* **Nothing grows between retrains,** and nothing at a prediction run.
* **Everything that measures keeps the season rule:** backtests, harm checks and the checks waiting on unseen matches
  read the walk-forward fits, never the retrained one.

## The check, made fast: about 3 minutes of GPU

The plan had 36 fits; it ran with 6, plus a part with none. The cut: no test of whether the extra TabPFN rows help.
Their plausible effect (0.001–0.01 milli-log-loss per match) is 10–100 times below anything a feasible check can see,
and your 9 Oct policy had already decided it. What was kept is what could actually go wrong. Rules fixed before any
result. Seasons 2020–2024 only, so 2025–26 stay unread.

| What | Result (mLL per match, + = the new way better) | Reading |
|---|---|---|
| **Stage 2 grown monthly** within the season, against stage 2 fixed for the season (2020–2024, 20,040 matches) | **+0.16 [+0.05, +0.27]** | **better**: no harm, your condition 2 met |
| the same, men | +0.25 [+0.07, +0.42] | better |
| the same, women | +0.06 [−0.02, +0.14] | unresolved (P(better) 0.94) |
| **A retrain at 1 July** plus grown stage 2, against the season-start model (2022–24, 6,337 matches after 1 July) | **+0.34 [−0.00, +0.67]** | unresolved (P(better) 0.97): the guard passes |
| the extra TabPFN rows alone | +0.04 [−0.11, +0.19] | unresolved, tiny, as the learning curve said; far from the +1.0 that would mean a leak |

* **Most of the gain is stage 2, not TabPFN.** The speed number changes from season to season, and refitting it within
  the season tracks that. In 2022 it started at 0.013 and rose to about 0.07; in 2023 it started at 0.073 (inherited
  from 2022) and fell to about 0.035.
* **The calibration still fits a retrained model:** recalibration slopes after 1 July of 0.97 (men) and 0.94 (women)
  against 0.98 and 0.93 for the season-start model (1 = right-sized). The retrained model is only 1–3% bolder.
* **Not edge credit.** These are log-loss readings on the walk-forward seasons, not money.

## What a retrain does now: notebook cell C0

`tp.retrain()` shows the plan and its checks; `tp.retrain(confirm=True)` starts it, detached, so it survives the kernel
and VS Code. About 5–6 hours, no input needed:
1. the build on the shared tables as last rebuilt, without copying the daily engine's 220 GB of caches (the old C2
   would have filled the disk: fixed);
2. the cut-off recorded, and stage 2's speed table extended to every men's match of the season (checked: it reproduces
   the existing table exactly on all 1,774 matches both hold, and fills the other 416; your condition 1);
3. the walk-forward fits, then the harm check against the model in use (rule: worse by more than 0.10 with the whole
   interval below 0);
4. with no harm, the switch, after the replay proof; on a failure, the previous model comes back.

**Before it:** B5, B2 and B4, then B6 with `confirm=True`, after the week's lower-level feed snapshot (Wednesdays,
12:00). The shared tables were last rebuilt on 14 Oct, so without B6 a retrain still trains on this season's matches
and grows stage 2, but brings nothing newer than 14 Oct.

**Revisions decided for the next retrain** (since 22 Oct 2026; the owner: "aware of these intended revisions to the
model, not simply adding the latest data"):
* **The register:** `data/studies/current_best_model/pending_at_retrain.json` lists them, with their checks.
* **The plan:** `tp.retrain()` lists them and refuses to start while one is missing from the shared tables, so B6 is
  required while one is pending.
* **The build:** `retrain.sh` checks the built instance before its fits (`<instance>/revisions_at_build.json`), stops
  if one is missing, and marks them applied after the switch.
* **The first one:** the [source reconciliation's repairs](../../decisions/2026-10-22-source-reconciliation-repairs.md),
  which are box scores, levels, surfaces, statuses and the serve-speed history.

**After it:** the first A4 builds the new TabPFN caches (about 15 minutes, once) and, with Thinking on, Thinking's paid
fit on the same rows (about 180k tokens). Both stage-2 versions are logged on every run (`q_a_stage2_annual` beside the
prediction used; your condition 3).

## The timer

One line at A1, at A4, in Status and on the bet sheet (its header and Run tab). Today:

> MODEL AGE: trained through 31 Dec 2025 (the season rule: no retrain recorded for this season): 294 days ago; 4,641
> main-tour matches since are not training rows (results table of 2026-10-14). RETRAIN DUE (setting: 30 days)

The 30 days is my default, a setting (`RETRAIN_DUE_DAYS`); you call each retrain.

## Expected effect of the first retrain

On the active model's own 2026 matches, stage 2 would move from the annual numbers to the grown ones: men's slope
0.901 → 0.905, women's 0.923 → 0.936, the speed number 0.033 → 0.037 (the daily feed). Small, as the check predicts.

## Limits, and what 21 Oct fixed

* **The speed history is no longer frozen for a retrain** (21 Oct). The extended table reads the frozen history plus
  the live feed's later rows (the daily collector's from 8 Oct, and a 21-day backfill), each counted only from the day
  the feed collected it; on the active model's matches every value is unchanged (36,793 of 36,793).
* **The three held Tennis My Life files were reviewed and accepted** (21 Oct): matches moved to their own events, box
  scores filled for 98 women's matches, 166 ages corrected, about 290 new results; nothing lost. Accepting them needed
  a fix: Tennis My Life reordered its 2026 WTA file, and the 8 Oct corrections now find a moved row by its match
  (identical output on unmoved files; noted in that decision).
* **The switch no longer waits for an unchanged data list** (21 Oct): replays use each build's own list since 16 Oct,
  so a feed snapshot during the build only reaches the next one.
* **Still real:** tennis-data.co.uk's closing odds arrive about a week late, and a training row needs one, so the last
  days before a retrain enter at the next one.
* **Disk:** the four instances' daily caches hold 220 GB; each retrain adds a build tree (~16 GB) and caches (~55 GB).
  Clearing the oldest builds' caches is your call.
* **The engine's self-tests** now follow the model you bet with (they had kept checking the 10 Oct one).

## Code

| What | Where |
|---|---|
| The training-row rule and the cut-off record | `src/eda/current_best_model/training_rows.py` |
| The rule in the daily fit, Thinking's fit, stage 2 | `src/eda/daily_prediction/dp_fit.py`, `dp_predict.py`; `src/pipeline/thinking.py`, `predict.py` |
| The extended speed table | `src/eda/in_season_retrain/speed_extend.py` |
| The harm check against the model in use | `src/eda/in_season_retrain/harm.py` |
| The retrain | `src/eda/in_season_retrain/retrain.sh`; `tp.retrain` in `src/pipeline/train.py`; notebook C0 |
| The timer | `tp.model_age`, `tp.show_model_age` (`src/pipeline/train.py`); A1, A4, Status, the bet sheet |
| The check | `src/eda/in_season_retrain/check.py`; rules `data/studies/in_season_retrain/check_rules.md`; results `data/studies/in_season_retrain/check/` |
| Tests | `test/in_season_retrain/`; `test/daily_prediction/` (conftest follows the selected model) |

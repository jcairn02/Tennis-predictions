# In-season retrains, the owner's way: process log

20 Oct 2026 – · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) · Session
`dd0f8ec7-2146-47b2-9c8c-75b9d421eea0` · For a future reviewer · Report: [README.md](README.md)

## 1. The request

* **The owner's words, verbatim** (20 Oct 2026, the first message of the session):
  > "We havent decided on the frequency of retrains yet, but it is a massive error that we are not using any 2026 for
  > training the tabpfn3.5 production models that are used to inform our betting. For production betting our latest
  > trains should IDEALLY be using the latest matches. This is weighed against the cost of frequently retraining. Not
  > practical to do it every day for example. As of now , Id like to only re-train manually , when I say its time to
  > retrain. (a timer can exist that watches time since last retrain so im informed off it on the masters script) each
  > time I run the A1-A5, but being 10 months out of sync is not good. For a proper retraining of the model that adds
  > this new training data and considers our latest plans for a model rebuild, how would that look? what do you
  > recommend also be included in the latest train? what would change between the current iteration and the next train
  > (the one we are about to do).? or is it simply the new data?"
* **Then, after the plan was put in chat** (stage 2 discussed, the Thinking speed term fixed: master pipeline process
  log Part 7):
  > "I'm on board with the following 3 items. Execute them. "Record your rule as an amendment to the 9 Oct decision?
  > Training rows and stage 2 would grow only at retrains you call; backtests and checks on unseen matches keep the
  > season rule. I recommend yes. Go-ahead for the setup and the check, on the fast plan above? I recommend yes. Should
  > stage 2 grow at every retrain, on the three conditions from before (speed table extended and checked, no harm in the
  > check, both versions logged)? I recommend yes." Then explain how we can make the "The 2022–2024 check: a dress
  > rehearsal on past seasons" faster while still being informative. Your plan takes too long. Common sense shows
  > frequent retraining is very unlikely to be harmful, so testing for it is a bit overkill imo, but im open to it if
  > you think its worth it to test. 24 hours is an unreasonble cost time wise though."
* **How it was read:**
  * Execute three items: the amendment (done first, `docs/decisions/2026-10-09-adoption-by-change-class.md`); the setup
    (the in-season training-row rule for the local model and Thinking, the cut-off record, stage 2's growth with its
    speed table, the timer, the retrain command, the engine's self-tests on the active build, the build cell's cache
    skip); the check, cut down.
  * **The check cut to what can fail cheaply.** The owner's "24 hours" counts the whole setup; the check itself was
    planned at 36 fits (~30 min of GPU). It is cut to six fits and a no-fit part (§ 3), and the accretion question is
    dropped (below its resolution by 10–100 times, and decided by policy).
  * **Not done without a further word:** the retrain itself (its day was not among the three items); accepting the
    three held Tennis My Life files (item 8 of the chat list, not among the three); the timer's threshold (item 4: a
    setting, default 30 days).
* **The target:** live bets at Pinnacle's price of the moment, after a retrain. The check scores past seasons at the
  close (the backtest convention), seasons 2020–2024 only (2025–2026, the proposed holdout, unread). Fixed in § 3 before
  any result of this study.

## 2. Starting point

* **Code:** commit `1d8f53e` (14 Oct 2026) plus the uncommitted working tree (the owner commits by hand), including this
  session's Thinking change (master pipeline process log Part 7).
* **Data:** the active instance `template_2026-10-16` (frame sha256 in its `odds_input.json`; 67,226 matches, 4,357 of
  2026, the newest finishing by 29 Sep 2026); its fits 2019–2026, seeds 0–15; the match clock
  `data/studies/match_timing/timing.parquet`; the speed column `data/studies/infosys_atp_backfill/speed_columns_augmented.parquet`
  (covers 1,774 of the frame's 2,190 men's 2026 matches).
* **Earlier looks:** the training-window study (seasons ≤ 2024: windows and recency, no in-season arm); the 9 Oct
  learning-curve estimate of in-season rows (0.001–0.01 mLL by late season); the speed-backfill study's season-by-season
  speed effect (I² ≈ 50%).
* **The idea and how it arose:** more of a kind of data already used (accretion, decided as a policy on 9 Oct), and a
  refit of stage 2 on more matches (accretion). Not mined from scored seasons.

## 3. Plan (fixed before any result; the rules also in `data/studies/in_season_retrain/check_rules.md`)

**Part A: does growing stage 2 harm?** No new TabPFN fit.
* Instance `template_2026-10-16`, its walk-forward fits (seeds 0–3), the speed column `spd_L_B` (the backtest
  convention), women's column 0.
* Seasons 2020–2024. Monthly retrains simulated: cut-offs on the 1st of February to November; segment k = the season's
  matches with es in [c_k, c_k+1) (the last runs to the season's end). January is the same in both arms and is left out.
* Annual arm: s_atp, s_wta, b on 2019 .. Y − 1 (debut seasons out, b shrunk, τ 0.05), the decided rule.
* Grown arm: the same fit on 2019 .. Y − 1 plus the season's matches with lf + 1 ≤ c_k (their walk-forward forecasts).
* Both arms: η = the seeds 0–3 mean.
* **Primary:** both tours, 2020–2024 pooled, paired log loss in mLL per match, + = grown better; 4-week blocks and the
  paired seed term (compare.paired).
* **Harm:** worse by more than 0.10 mLL with the whole 95% interval below 0.
* Report only: men, women, each season; the coefficients at each cut-off.

**Part B: the guard of 9 Oct.** Six TabPFN fits.
* Seasons 2022, 2023, 2024; cut-off 1 July; seeds 0 and 1; the decided settings.
* The in-season fit: 2013 .. Y − 1 plus the season's matches with lf + 1 ≤ 1 July; it predicts the season's matches
  with es ≥ 1 July, stored and swapped, symmetrised. Matches in flight at the cut-off are in neither.
* **Primary:** the live configuration (the in-season fit with the grown stage 2 through 1 July) against the decided one
  (the walk-forward fit with the annual stage 2), seeds 0–1 matched, both tours, the three seasons pooled.
* **The guard fails** if (i) the primary is worse by more than 0.10 mLL with the whole 95% interval below 0, or (ii) the
  TabPFN part alone (both with the annual stage 2) gains more than +1.0 mLL: about 100 times the learning curve's
  estimate, so a suspected leak of rows after the cut-off, to be found before any use.
* **Mechanical checks** (no result read): no training row with lf + 1 after the cut-off; no predicted match with es
  before it; the training rows equal the season rule's plus the admitted ones.
* Report only: the recalibration slope of each configuration's log-odds on the predicted matches (1 = right-sized), per
  tour; the spread of each fit's log-odds about the close.

**Dropped:** a test of whether retraining within the season improves forecasts. Its plausible size (0.001–0.01 mLL)
is 10–100 times below what a feasible check resolves (about ±0.3 mLL here), so it could not decide anything, and the
policy decided it on 9 Oct. The owner's view: "testing for it is a bit overkill".

## 4. Chronology

Local time PDT (UTC−7). "Results" means any outcome-based score of any candidate.

| When | Step | Why | Results seen by then | Output |
|---|---|---|---|---|
| 18:40–18:50 | The amendment recorded: the 9 Oct decision (point 7 note, new section), the 8 Oct decision (three notes), CLAUDE.md (Fit, Coefficients), the decisions index | item 1 | none of this study | the files named |
| 18:50 | This log opened; § 3 written | the rule: before the first substantive step | none of this study | this file |
| 18:52 | `check_rules.md` written and hashed (SHA-256 `2d92b5d3…`; its header says 18:55, written from memory; the file time is 18:52) | rules before any result | none | `data/studies/in_season_retrain/check_rules.md` |
| 18:52–18:54 | `current_best_model/training_rows.py` (the rule, shared); `in_season_retrain/check.py`; `--plan`: 2022 45,515 rows (42,538 + 2,977 admitted), predicts 1,966; 2023 50,399 (47,483 + 2,916), 2,219; 2024 55,596 (52,623 + 2,973), 2,168; mechanical checks passed | the plan's counts, no result | none | console |
| 18:55–18:58 | `--fits` (background): six fits, 26–36 s each, exit 0 | Part B | none | `check/fits/`, `check_fits.log` |
| 18:55–18:58 | Beside it: the rule wired into `dp_fit.season_jobs` (and `fit.json` records the cut-off) and Thinking's `prepare` (its record names the cut-off; `fit_state` gains "other rows"; `predict._thinking_fits` refuses it) | setup piece 1 | none | the files named |
| 18:58 | `--score` failed before printing: the fits stored the ids as an object array; loader allows it for these six own files, the writer now stores text | a bug, no result read | none | — |
| 18:58 | **The first look (rules fixed):** Part A grown vs annual stage 2, 2020–2024, both tours: **+0.160 [+0.054, +0.266] better**, P 0.998 (men +0.245 better; women +0.063, P 0.94; 2022 +0.499 better, 2023 +0.248 P 0.96, others ~0). Harm: no. Part B live config vs decided: **+0.336 [−0.002, +0.674] unresolved**, P 0.974; TabPFN part +0.039 [−0.114, +0.193], P 0.70 (leak flag +1.0: no). Guard: passes. Recalibration slopes after 1 July: live men 0.97 (SE 0.045), women 0.94; decided 0.98, 0.93. Spread about the close: in-season +1–3%. b̃ paths: 2022 from 0.013 (annual) to 0.05–0.07; 2023 from 0.073 to 0.034–0.039 | the check | this row | `check/results.json`, `results.csv` |
| 18:59 (row of 18:58, corrected) | The rules file's time, read from the clock: 18:51, not 18:52 as the row above says | the template's rule 3 | — | — |
| 19:00–19:04 | Condition 1, the speed table. (a) The live 28-day form (live/form.py) at each match's es: equal to the decided column on 1,012 of 1,774 2026 men's matches (B), max 0.56: **set aside** (the live panel is not the frozen history). (b) The decided builder (adaptive/columns.build_scenario on the augmented history, its release table) on targets made from today's tables (the frame's side A = Stage 0's: a_won equal on 9,462 of 9,462 matches of 2025-26): `speed_extend.py`, **equal on 1,774 of 1,774 (B and D, max difference 0.0)**, 416 filled, 6 s | condition 1 | the check's (row above) | `data/studies/in_season_retrain/speed_extend_test/` |
| 19:05 | Found: the frozen history ends (latest observation 3 Oct, finish 7 Oct 2026); the tool counts extended matches starting after it (`extended_beyond_history`) | a limit for the next retrain's October matches | — | `speed_extend.py` |
| 19:05–19:07 | `compare.walk_forward_on` (the decided fit on named rows); `dp_predict.coefficients` grown set (2019 .. Y − 1 + admitted, season Y's walk-forward forecasts, the instance's extended table; refused without it), the annual set beside it in `predictions.csv` (`q_a_stage2_annual`, `stage2_set`) and `provenance.json`. One existing test's stand-in key function took three arguments, so the fourth is passed only for a grown set. `test_thinking.py` + `test_stage2_sync.py` 13 of 13; `test/in_season_retrain` 4 of 4 (the annual set on a copy of the instance equals the engine's held record bit for bit; walk_forward_on = walk_forward exactly) | setup piece 4 | the check's | the files named |
| 19:08 | Preview on a scratch copy of the active instance, cut-off 1 Oct 2026 (admits its 4,357 2026 matches): daily feed s_atp 0.9010 → 0.9054, s_wta 0.9234 → 0.9357, b̃ 0.0334 → 0.0373 (weekly 0.0366 → 0.0401) | what the first retrain moves | the check's | scratchpad `grown_coef.py` |
| 19:08 → 05:15 (21 Oct) | **The work stopped**: the session's turn ended after the preview without a report, and resumed at the owner's message, verbatim: "did the process get interrupted?" The first reply said it had not; the file times show the 10-hour gap (corrected in the reply that followed). No job was running; nothing was lost | — | — | file times |
| 05:15–05:20 | The timer: `train.model_age` / `show_model_age` (the season rule's 31 Dec, or the instance's cut-off; main-tour main-draw evaluation rows of the shared Stage 0 counting after it; due at `CFG.RETRAIN_DUE_DAYS` = 30, a setting); printed by A1, A4, Status; on the bet sheet's header and Run tab. Today: 294 days, 4,641 matches, due | setup piece 3 | — | `src/pipeline/` |
| 05:20–05:25 | The retrain: `in_season_retrain/harm.py` (the 16 Oct check with ON a parameter, default the instance in use), `retrain.sh` (the 16 Oct script's steps plus the cut-off, the speed table, the replay registry entry), `tp.retrain` (plan and checks; `confirm=True` starts it detached under Git Bash); the build cell's copy now leaves out the daily engine's caches (`RUN_CHAIN_SKIP_DIRS`, `BUILD_DISK_GB` 90); notebook C0 added, C2's comment corrected. `tp.retrain()` plan: tables of 14 Oct 21:19 UTC, older than the instance in use, so flagged (B6 first); nothing started | setup piece 2 | — | the files named |
| 05:25 | The engine's self-tests follow the selected instance (conftest sets DP_INSTANCE and DP_BASE_TREE from `selected_instance.json` when unset; the price-grid test reads the replay's own instance) | setup piece 5 | — | `test/daily_prediction/` |
| 05:26 | The final regression launched (background): `test/in_season_retrain`, `test/daily_prediction` (with the replay on the active instance), `test/master_pipeline`, `test/current_best_model` | verification | — | scratchpad `final_tests.log` |

## 6. Judgment calls and deviations

1. **The check cut to six fits and a no-fit part** (before any result): the accretion question dropped as below
   resolution and decided by policy; Part A uses no new fit because stage 2's growth reads only stored walk-forward
   forecasts; Part B keeps the guard of 9 Oct at its smallest informative size (three seasons, one cut-off, two seeds).
   The other branch (36 fits) would have tightened Part B's interval by about a third.
2. **The speed table from the decided builder, not the live form** (after seeing the live form's 1,012 of 1,774): only
   the builder reproduces the column exactly, which condition 1 asks.
3. **Matches beyond the frozen history kept in the grown fit,** counted, not dropped: their forms are stale, not leaky.
4. **The harm check's seasons are 2020 .. the last,** as the 16 Oct check (it reads 2025-26, the holdout's exposed
   part); the guard and Part A read 2020-2024 only.
5. **The retrain switches by itself on no harm,** as the 16 Oct rebuild did; the owner's word starts it.
6. **Not done:** the retrain; the held Tennis My Life files; a threshold the owner chose.

## 7. Claims and their evidence

| Claim (README) | Evidence | Status |
|---|---|---|
| Grown stage 2 better, +0.16 [+0.05, +0.27] | `data/studies/in_season_retrain/check/results.json`, part_a | observed |
| The guard passes, +0.34 [−0.00, +0.67]; TabPFN part +0.04 | same, part_b | observed |
| Calibration still fits (0.97 and 0.94 against 0.98 and 0.93) | same, part_b.recalibration | observed |
| The speed table reproduced exactly on 1,774 of 1,774 | `speed_extend_test/stage2_speed_columns.json` | observed |
| The annual set unchanged bit for bit | `test/in_season_retrain/test_training_rows.py::test_the_grown_stage2_set` | observed |
| Grown numbers on the active instance's 2026 matches | the 19:08 row | observed (scratch) |
| The old build cell would have filled the disk | 220 GB of caches in `data/studies/daily_prediction/state`, 258 GB free, no skip in `build_instance` | observed, not run |

## 8. Weak points

* **Part B's power:** ±0.34 at 95%; a harm smaller than that would pass. The plausible harm (the calibration mismatch
  from 7% more rows) is far smaller, and the recalibration slopes show none.
* **Part A's seasons include the speed number's worst years** (2022, 2023) for the annual rule; growth helps most when
  a season breaks from the last. In a calm season expect about 0.
* **One instance, one frame:** the check ran on `template_2026-10-16`; a retrain's own build is checked only by its harm
  check and replay proof.
* **The speed table beyond 3 Oct 2026** (README, limits).
* **The retrain script is untested end to end.** Its build and switch steps are the 16 Oct script's, which ran; its new
  steps ran here on a copy. Its first run is the first live use.

## 9. What a re-design would do

Test grown stage 2 at more cut-offs per season and a weekly cadence (it costs seconds); merge the live panel's rows into
the speed builder for matches after the frozen history; a season-aware speed coefficient as a candidate.

## 10. Reviewer checklist and reproduction

* Rules hash before results: `sha256sum data/studies/in_season_retrain/check_rules.md` gives `2d92b5d3…`.
* `./python.sh src/eda/in_season_retrain/check.py --plan` (counts and mechanical checks, no result);
  `./python_tabpfn_local.sh src/eda/in_season_retrain/check.py --fits` (about 3 minutes);
  `./python.sh src/eda/in_season_retrain/check.py --score`.
* `./python.sh src/eda/in_season_retrain/speed_extend.py --instance data/studies/current_best_model/template_2026-10-16 --season 2026 --out <folder>`.
* `./python.sh -m pytest test/in_season_retrain -q`.


## 4b. Chronology, 21 Oct 2026: the data brought up to date, then the retrain

The owner's message (about 05:30), verbatim: "What i struggle to understand is if these limits on timing have something
to do with when the data will be available or adhering to process rules for the sake of following process rules. Like
if we have a process that we do once per week, that COULD be do once per day , but we dont because of some trade offs.
However, for a retrain it makes sense we update these first (more frequently than the rule suggests) we should NOT
stick to the rules because we have to consider what the intention of the rules were. Like The frozen speed history
ends october 3, why are we freezing the speed history? that seems silly to me all this data freezing. "after the 12:00
lower level feed. Why not just manually do that now BEFORE the retrain and bump up the timing so its convenient to do
the retrain?" I guess you are telling me to do all these steps in the master script, but maybe you should just do it
now?"

**Read as:** the go for today's retrain, with every data step run now rather than on its schedule; each limit judged
by its purpose. **Sorted:** the 12:00 feed and the routine cadences are cost trade-offs (run now); B2-B6 are real data
steps (run now); the frozen speed history is the serve-speed study's reproducibility copy (the live feed is not frozen:
add its rows); the switch's "accepted.json unchanged" guard lost its reason on 16 Oct (replays merge the build's own
list: relaxed); the held-file review is a real check (run it); tennis-data's odds lag is a real limit (kept).

| When | Step | Why | Results seen by then | Output |
|---|---|---|---|---|
| 05:35 | B2 (Tennis My Life): six held versions (2025 WTA two, 2026 WTA three, 2026 Challenger one) | data | — | master pipeline log |
| 05:36-05:39 | The review (`tml_revisions/held_check.py`): it needs one held version per file, so `held_files` now takes the newest (by the CSV's write time) and names the older; build B stopped on a row correction (row 1328 of 2026_wta.csv: Tennis My Life reordered the file) | the review | — | `held_check.py` |
| 05:40 | B3 speeds (21 days back), B5 odds, B4 timeline then B8 feed, launched (background) | data | — | `data/studies/in_season_retrain/refresh_2026-10-21/` |
| 05:40-05:44 | `input_data_audit/corrections.py`: a row correction whose row moved is applied to the one row of its file with the same four guards (none or two: stop). The review's build A with the new code equals the old code's build A on all five outputs (SHA-256) | the row order | — | the 8 Oct decision's note |
| 05:44-05:51 | The review: B builds; 60 dropped (32 paired: 31 Challenger matches to their own event, 1 key), 290 new (220 Challenger and 55 WTA 1000 results, 15 others), 283 revised (box scores for 98 matches that had none, 166 ages, 191 indoor flags, 47 match lengths, 8 rank points, 1 score), 28 team-event rows unpaired; history check: the template may be built | the review | — | `data/studies/tml_revisions/held_check/summary.json` |
| 05:52-05:54 | **Accepted** the three newest versions (2025_wta a99bb69b647c, 2026_wta 8f6fb09ef0b0, 2026_challenger 290817794982): no change is data loss. The rule's letter (main-tour changes go to the owner) was set aside on the owner's word of 05:30 and the 9 Oct narrowing (main-tour repairs decided on the data evidence); the owner is told; the replaced copies are kept in `superseded/` | the data | — | the downloader's log |
| 05:54 | `data.held_tml_files` no longer lists held versions older than the current copy | a misleading list | — | — |
| 05:53-05:56 | `speed_extend.py`: the frozen history plus the live panel's rows it lacks (438, observed to 20 Oct), each released by its scenario's rule but never before its collection day; on the active instance the overlap is still 1,774 of 1,774 exact (both feeds) and every value equals the frozen-only build (36,793 of 36,793) | the frozen-history limit | — | `speed_extend_test_live/` |
| 05:57 | `retrain.sh`: the switch no longer refuses when accepted.json changed during the build (a note instead) | its reason gone since 16 Oct | — | — |
| 05:26-06:40 | **The final regression** (`test/in_season_retrain`, `test/daily_prediction` on the selected instance, `test/master_pipeline`, `test/current_best_model`): **205 passed, 2 failed, 6 errors.** The 6 errors: the replay fixture's `run_day` stopped at its pattern step, reading TennisLive's `listed.parquet` while this session's manual feed run (B8, from 06:03:51) rewrote it ("Parquet magic bytes not found"; the file was readable again from 06:05:56, 878,293 rows). Failed: `test_linker_on_the_probe` (the known data drift) and `test_changed_past_row_recomputes_through_the_steps` (the short-term forms recompute beside the 7 IOS solves on the 16 Oct instance's 22 Jun checkpoint; under the old 10 Oct default it failed with Elo too; none of today's changes reads that path) | verification | — | scratchpad `final_tests.log` |
| 06:42 | The six replay tests re-run alone (background), with nothing writing TennisLive's listing | the collision | — | scratchpad `replay_rerun.log` |
| 06:47 | B8 done (2,594 s): the lower-level feed advanced to snapshot 20261021. B6 (the shared tables) launched (background) | data | — | `refresh_2026-10-21/` |
| 06:48-06:50 | The owner's sign-off asked (a phone push, then the question): delete the daily engine's state of the three superseded instances (10, 13, 14 Oct; 54.3 GB each; no reparse points). The owner's answer: "Yes, delete them (Recommended)". Deleted at once (links re-checked first: none); free disk 382 GB; `state/template_2026-10-16` kept (in use; the rollback after the retrain) | the owner's request of 06:0x: "if there's a backup on disk of an old train to clear some disk space, propose if we should clear it" | — | — |
| 07:00 | The six replay tests re-run alone: **5 passed** (the price grid now against the 16 Oct instance's stored fits; the fit cache; the history check; the side names; the three processes). **1 failed:** `test_replay_reproduces_the_57_inputs` asks 36 of 36 non-IOS inputs bitwise; 21 are, the rest are Stage B's forms on 5 of 23 matches, at most 4.4e-6 (float32 rounding: the same reading the 16 Oct switch recorded, daily prediction process log Part 5; the switch guard, every input within 1e-4 and IOS within 1e-6, passes). The test's bitwise bar was set on the 10 Oct instance; a recommendation, not a change made here: hold it to the switch guard | verification | — | scratchpad `replay_rerun.log` |
| 07:18 | B6 done (1,860 s): Stage 0 873,681 → 873,964 matches; rebuild `2026-10-21T1347Z`. `tp.retrain()` plan: all four checks ok (tables of 13:47 UTC, after the instance in use; 423 GB free; cut-off 2026-10-21); the timer: 4,737 main-tour matches since its rows end | — | — | — |
| 07:18-07:20 | `tp.retrain(confirm=True)` started it (pid 39228, Popen, no console of its own); the dump view frozen (`tnr_dump_freeze_10211347`: 104 files, none re-staged); the sandbox set up. **Stopped and relaunched:** a build started from a session's shell died with its console on 14 Oct (data_gaps_2026 process log 00:24), and the proven launch is PowerShell's Start-Process in a hidden window; the processes stopped at the additions step (`taskkill /T`), the sandbox removed with `run_chain.py --cleanup` (junctions first; data/raw and data/dump intact), the log kept | the launch's survival | — | the retrain's log |
| 07:20 | **The retrain relaunched** (Start-Process, Git Bash, hidden; pid 22652), appending to `data/studies/in_season_retrain/retrains/template_2026-10-21.log`; `tp.retrain` now launches the same way; a watcher (this session's) waits for the pid | — | — | — |
| 07:29 | **The retrain stopped at lane 0** (14:28:35Z): `match_timing/rebuild.py`'s IOS pool, BrokenProcessPool, no traceback from the worker. The 07:20 launch ran `bash -c`: a non-login Git Bash does not read its profile, so conda's folders were not on PATH and the workers died in MKL (the long-jobs memory's crash). The setup and the additions had passed (the feed 20261021 merged: 50,028 added, 43 skipped by id) | — | — | `template_2026-10-21/build.out`, the sandbox's `logs/timing_features.log` |
| 07:29-07:31 | Sandbox removed (`run_chain.py --cleanup`); a probe of both launches (a 3-worker pool solving with numpy): `bash -c` BrokenProcessPool, `bash -l -c` conda on PATH and the solves done; `tp.retrain` now launches with `-l`; the long-jobs memory updated in place | the cause, checked | — | scratchpad `mkl_probe*` |
| 07:31 | **The retrain relaunched as a login shell** (Start-Process, hidden; pid 42072); a new watcher | — | — | the retrain's log |
| 07:31-11:57 | **The retrain ran through** [observed, its log]: build 07:31-09:38; post-build; the cut-off (4,662 of 4,662 2026 frame matches admitted; 67,531 training rows against 62,869) and the speed table (overlap 1,774 exact on both feeds; 571 extended, 47 of them after the frozen history, reading 468 live rows); fits seeds 0-3 09:39-09:55; **harm check against template_2026-10-16: −0.012 [−0.027, +0.003] unresolved, P 0.06, no harm** (2020-2024 identical: 0.000; 2025-26 women −0.078 [−0.182, +0.026], P 0.06); compare.py: 22 inputs uneven, the 16 Oct list plus one-season form flags; seeds 4-15 2026; the replay registry's entry; **switch** (checkpoint 22 Jun; replay of 13 Jul R16: 23 matches, 42 inputs bitwise, max 4.4e-6, IOS exact; live checkpoint 23 Sep) **done 10:59**; seeds 4-15 2019-2025; DONE 11:57 | the retrain | the harm check's | the retrain's log; `template_2026-10-21/` |
| 11:58-12:10 | Verified after it: the template check OK (5 of 5); the replay had built the 16 TabPFN caches on 67,531 rows; stage 2 computed (daily s_atp 0.9010 → 0.9060, s_wta 0.9234 → 0.9326, b̃ 0.0334 → 0.0382; 32,414 → 37,070 matches); the timer corrected to the newest admitted match (19 Oct) and the season's matches it does not admit (75); the price-grid test skips its stored-fits comparison for a retrain's instance (they are not its live fit); `test/in_season_retrain` + `test/master_pipeline` 73 passed (the probe test deselected); the instance index updated | verification | — | — |

## 4c. 21 Oct 2026, afternoon: the newest matches priced at the books' average

Session dd0f8ec7-2146-47b2-9c8c-75b9d421eea0 (resumed after a context summary; this log re-read). The owner's
question, verbatim: "The new rows added had closing lines right? They weren't left blank? They used betonline or
betonline + exchanges?" Then, mid-turn: "I'm concerned how many moving peices there are in this pipeline that depends on
arbitrary rules and such. There's a lot of ways for minor bugs to show up like, we have all these closing lines and we
aren't using them because of some policy that hasn't updated. I think this may need some sort of higher level
organizational update to reduce the chance of these bugs / Pretty silly this was missed imo"

**Read as:** a factual check of the retrain's new training rows' odds input; then a request for a structural answer to
a class of bug, not only this one. The live model is not changed without the owner's word (it is a change to the
model bet with; the GPU may be needed by a bet day).

| When (PDT) | Step | Results seen by then | Output |
|---|---|---|---|
| ~13:50-14:10 | The instance's 2026 training rows: none blank (in_odds_logit and p_mkt finite on 4,662 of 4,662); sources betonline 4,095, average 567, no exchange (the rule's order is Pinnacle, BetOnline, average; tennis-data's Betfair column is read only by the odds-sources study). By month (tournament date): the average 16-53 a month January-August (3-9%), September 164 of 323, October 149 of 149 | — | — |
| ~14:05 | **Cause:** OddsTrader's link (tennis-data row to OddsTrader event) and the every-book pull (which holds BetOnline's line, book 8) were last built on 9 Oct (the link's newest linked match 29 Sep). The notebook's `finish_instance` ran both before the odds step; `data/studies/level_layer_adoption/post_build.sh`, which every scripted build since 13 Oct ran (data_gaps_2026's builds, the 14 and 16 Oct instances, this retrain), had its own copy of the steps without them. The odds step's fallback (the average where neither book prices a match) hid it. The monthly listing was current (B5, 05:42): 661 BetOnline closes for 23 Sep-20 Oct singles on disk | the counts above | — |
| 14:15-14:40 | **A second gap of the same kind, in the download:** the every-book pull names its batches by position (books/<tour>/<month>/<nn>) and reuses any batch it holds, so run again on a month that gained events it would have returned the 9 Oct batch for the month's last position (ATP September's batch 01 held 33 events) and the new events in it would have had no lines | the code | — |
| 14:40-15:00 | **Fixes** (no live change): (1) `src.ingest.oddstrader`: the every-book pull asks only for events no good earlier receipt holds, in batches named by a hash of their events (old raw copies kept; staging already keeps the newest copy of a line); `pull_books`, `pull_months` shared by the command line and the odds step. (2) `odds_sources/table.py`: the link records the tennis-data rows' last day it saw; `coverage()` refuses a frame with a match newer than that, a linked event with no every-book pull, or a month listed before its newest match's line was final (two days after the match day, UTC); `build()` stops on any. (3) `current_best_model/odds_input.py --apply` brings the three tables up to date itself first (stale months listed again, the link, the pull; `--no-refresh` for a reproduction), refuses an already rewritten frame before any network, and records the average's share month by month from August 2025. (4) `finish_instance` is the one list of the finish steps (it keeps the chain's frame and list, as post_build.sh did); post_build.sh now runs it, so retrain.sh and the old study scripts run the same steps as the notebook. Tests: `test/odds_sources` 12 passed (3 new: coverage passes a covered frame and names each stale table; the pull asks only for new events, named by them) | — | — |
| 15:00 | The repaired odds step run on a scratch copy of the live instance's chain frame (scratchpad `odds_fix/`), to see which rows change before anything is proposed | — | scratchpad `odds_fix/apply.log` |
| 14:25 | First run (scratchpad `odds_fix/`): the staleness check listed **2017-12** as never listed (the 2018 season's matches of late December 2017, outside OddsTrader's listing, which starts 2018-01) and re-listed it (5 requests; it changed no row, below). Fixed: months before 2018-01 are not checked (`table.FIRST_LISTED`; a test) | — | `odds_fix/apply.log` |
| 14:27 | The link: 39,978 of 42,685 tennis-data rows (39,666 of 42,378 on 9 Oct); the every-book pull: 312 new events of 39,978, 8 requests (39,666 pulled before); staged | — | `odds_fix/apply.log` |
| 14:29 | **Against the live instance: 289 rows changed, all 2026 training rows, all average → BetOnline** (September 148, October 141); nothing else moved; the average's share of September and October back to about 5% (January-August 3-9%). Log-odds change median 0.040, 95th percentile 0.13, **one at 4.22** | the repaired frame | — |
| 14:31-14:45 | The outlier, with names (open_tennis_data players): **Bergs v Alcaraz, Shanghai 2026 third round**: every OddsTrader book (BetOnline 0.888, 10 others median 0.898) at 89% for Bergs, tennis-data's average 0.104, Bet365 0.096 and Betfair 0.083: a mirror image, the OddsTrader event linked with its sides exchanged. Among all 5,282 BetOnline rows of the repaired frame, 7 are gross against the average (the odds study's GROSS 1.0 log-odds and 10 points): 2 mirrors (Bergs v Alcaraz; Zverev v Fery, Wimbledon 2026 semi-final, BetOnline 0.152 against tennis-data's 0.838-0.845, in the live frame since the Pinnacle-first instance), 5 not mirrors (Zverev v Auger-Aliassime, Finals 2025; Pliskova v Sasnovich; Osaka v Kalinina, tennis-data's average 0.035 against 11 OddsTrader books at 0.42, where tennis-data looks the wrong one; Bublik v Tsitsipas; Zverev v Cobolli). The odds study measured "swapped" lines (quality.py) but the production rule never applied it | — | — |
| 14:45-14:58 | **The mirror guard** (`odds_input.construct`): an OddsTrader price (BetOnline's, or its recording of Pinnacle) that is the study's "swapped" against tennis-data's average is left out; a mirrored OddsTrader Pinnacle hands the match back to tennis-data's Pinnacle where that one is Pinnacle's (before August 2025), else the next source; a gross gap that is not a mirror is kept and listed (`betonline_gross_listed`), since either record may be wrong. The first version fell to the average for the two older mirrors; corrected before any result was used. Tests: 21 passed (2 new) | the 7 rows | — |
| 14:58-15:05 | **The repaired odds input against the live instance** (scratchpad `odds_fix2/`, `--no-refresh` on the refreshed tables): 291 rows: 2026 average → BetOnline 288; 2026 BetOnline → average 1 (Zverev v Fery); 2023 and 2025 Pinnacle (OddsTrader, mirrored) → Pinnacle (tennis-data) 1 each (the 2025 one: Roland Garros women's final). By source: Pinnacle (tennis-data) 60,739, Pinnacle (OddsTrader) 957, BetOnline 5,280, average 555 | — | `odds_fix2/odds_input.json` |
| 15:05 | Not done without the owner's word: a corrected instance and its switch (the 2023 and 2025 rows mean every season from 2023 is refitted, which the retrain's path does anyway in a new folder) | — | — |
| 15:10 | 97 tests passed (`test/master_pipeline` without the known probe test, `test/pinnacle_first`, `test/odds_sources`, `test/current_best_model/test_odds_input.py`, `test/in_season_retrain`); the report's note added | — | — |
| 15:15-15:25 | **The owner's answers** (a phone push, then two questions). "Correct the live model now? A corrected copy of today's retrain with the repaired odds (288 recent matches to BetOnline, 3 mirrored prices replaced, the new mirror rule), the same checks as this morning, and a switch only if they pass. About an hour; no bet day meanwhile." → **"Yes, start now (Recommended)"**. "Go ahead with the bigger fix: a results check on every built model before it can go live, then one copy of each procedure, with a one-page rule list drafted for you to prune?" → **"Discuss first"**: nothing of it is built until it is discussed | the comparison above | — |
| 15:26-15:28 | `template_2026-10-21b/`: the 21 Oct build's chain frame and list and its records copied (no rebuild), a README of its origin; **launched** (Start-Process, Git Bash `-l -c`, pid 10152): `SKIP_BUILD=1 bash src/eda/in_season_retrain/retrain.sh template_2026-10-21b C:/Users/zerom/tnr_tpl1021 2026-10-21`. Post-build 22:28:24-22:29:09Z: by source as the scratch run (60,739 / 957 / 5,280 / 555); 4 mirrors left out; no month listed again; the cut-off 4,662 admitted, 67,531 rows; fits from 22:29:16Z | — | `retrains/template_2026-10-21b.log` |
| 15:30 | Recorded: the Pinnacle-first decision's amendment of 21 Oct (the repair; the mirror rule with the owner's answer verbatim), its index entry, CLAUDE.md's odds bullet | — | — |
| 15:29-15:45 | Fits seeds 0-3, 2019-2026 (16 s a seed for 2019, 52 s for 2026) | — | `template_2026-10-21b/fits.log` |
| 15:45 | **Harm check against template_2026-10-21** (2020-2026, both tours, both stages, + = the corrected better): **+0.018 [−0.074, +0.110] mLL, unresolved, P(better) 0.65: no harm.** Wider than the morning's (±0.015) because the two older mirrors (2023, 2025) change the training rows of every later season, so 2024-2026's fits all differ a little. compare.py against the frozen reference: +0.045 [−0.297, +0.386], unresolved (the odds change's ±0.3); the same 22 inputs flagged uneven as the morning's build | the harm check's | `retrains/template_2026-10-21b/harm.out`; `template_2026-10-21b/vs_reference_2026-10-08/` |
| 15:46 | Told the owner the switch lands about 17:00 PDT, not in "about an hour" (the morning's checkpoint, replay and live checkpoint took 53 minutes after the fits) | — | — |
| 15:55-16:29 | READY 22:55:44Z; a note that accepted.json changed since the build: checked, the noon feed task re-ran and logged the same snapshot (20261021 → 20261021), no content change; checkpoint 22 Jun; **the replay passed** (13 Jul R16, 23 matches: none missing, IOS exact and NaN pattern equal, 42 of 57 inputs bitwise, max 4.4e-6; the replay built the 16 TabPFN caches on the corrected rows) | — | `daily_prediction/runs/replay_2026-07-13_R16_20261021T160541/` |
| 16:39 | **SWITCH DONE** (live checkpoint 23 Sep): the daily runs use template_2026-10-21b. Template check 5 of 5; the timer: trained through 19 Oct, 75 main-tour matches of the season not training rows; stage 2 grown (replay feed): s_atp 0.9056 → 0.9051, s_wta 0.9326 unchanged | — | — |
| 16:40-16:47 | **The evaluation fits paused.** The script went on to seeds 4-15 of 2019-2025 (about an hour, evaluation only). A bet day's fit step checks for other local-env processes before its first fit and fits.py checks before every fit, so a bet day started meanwhile would wait on them (up to 6 h): the long-jobs rule (evaluation-only fits at a quiet time). The script stopped first, then fits.py right after a fit was saved (2019 seed 9); all 50 fit files open; the note in the retrain's log; `resume_eval_fits.sh` launched detached (pid 8788), waiting to 03:00 on 22 Oct | — | `retrains/template_2026-10-21b.log` |
| 16:50 | Recorded: the instance index (21b current, 21 the rollback), the report | — | — |

**Still open from this part (owner's call):** the "bigger fix". The owner chose "Discuss first"; the discussion was put
to them (five kinds of bug seen in this project, options A-E from a results check to a declared pipeline, Claude's
recommendation A then B, C as steps are touched, D drafted; E not now) with four questions: stop or warn on a failed
check; builds first or bet days too; how much pruning; where to show it. Nothing of it is built.

**Claims and evidence (§ 4c).** No new 2026 row was blank, no exchange price used: the frame's columns (14:00 counts).
The average stood in for BetOnline from late September because the link and the every-book pull were the 9 Oct ones:
link_counts (newest linked match 29 Sep), the scripts' step lists, the repaired run's 289 changed rows. The mirrors are
link orientation errors: every OddsTrader book on one side, tennis-data's average, Bet365 and Betfair on the other, at
mirror-image chances (two by players' names and plausibility: Bergs v Alcaraz, Zverev v Fery). The correction did no
harm: the harm check. **Where a flaw would hide:** the 5 gross non-mirror disagreements are kept on BetOnline and only
listed (either record may be wrong; Osaka's suggests tennis-data's); the mirror rule uses the odds study's constants,
not ones tuned here; the link's own orientation logic (the sharp benchmark's linker) was not audited, only its output
checked against tennis-data's books, so an error that moves both records together would pass.

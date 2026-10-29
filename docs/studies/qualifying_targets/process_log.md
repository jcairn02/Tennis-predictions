# Tour-level qualifying as prediction targets: process log

22 Oct 2026, 07:37 – 09:40 PDT · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) · Session:
40624dcb-dd11-4b33-9758-215a45a8677e (it also holds the 16 Oct exchange that led here) · For a future reviewer ·
Report: [README.md](README.md) (written at the end) · Pre-registration: [preregistration.md](preregistration.md)

## 1. The request

* **The owner's words, verbatim** (22 Oct 2026), quoting part of my reply of 16 Oct:
  > "My recommendation: test qualifying as a separate study / This adds a new kind of match, so it needs its own
  > evidence of an edge before any money goes on it. Testing it changes nothing in today's model. / After tonight's
  > retrain finishes: download Pinnacle's qualifying lines from the same odds site, if it has them (2018 to September
  > 2025, where its Pinnacle history ends). That's about 200 paced requests, roughly 10 minutes. / Check how accurate
  > the closing prices are on qualifying, and whether BetOnline's match Pinnacle's there as they do on main draws. /
  > Build the model's inputs for qualifying and test on seasons it hasn't seen: / Does it beat the closing price on
  > qualifying, at the bookmaker's own odds? / Do the main-draw predictions stay as good? In the earlier study, adding
  > Challenger matches to training leaned toward making them worse, though not conclusively. So qualifying may need a
  > model of its own."
  >
  > "I like this idea. Execute the test properly and with care, then report your findings."
* **Where it came from** (same session, 16 Oct 2026):
  * The owner sent BetOnline screenshots of eight Almaty matches and asked: "Run todays predictions."
  * All eight were qualifying round 1, which the pipeline leaves out ("qualifying"). The model's 67,226 training matches
    hold none.
  * The owner asked: "Is our data complete for qualifyers? why did we choose to omit them from our model?"
  * My answer, from a search of the records, verified by me:
    * nobody decided it;
    * it followed from training on tennis-data.co.uk's closing prices, which cover main draws only (30 Sep – 2 Oct);
    * BetOnline's lines downloaded on 7–8 Oct cover qualifying but were never linked.
* **How it was read:**
  * **The interpretation acted on:** steps 1–3 of the quoted recommendation. These are the Pinnacle download, the
    market's accuracy on qualifying, and the model on qualifying (edge against the close, main-draw harm).
  * **Set aside: step 4**, wiring the bet-day pipeline for qualifying. My recommendation made it conditional ("only if
    it shows an edge"), and the owner quoted steps 1–3 only.
  * **Set aside: Challenger and ITF qualifying.** The question and the Almaty case are tour-level qualifying.
  * **Not touched:** the deferred odds-rule test build ("DO NOT DO THE TEST YET", 21 Oct). This study changes no
    instance, no shared table except the OddsTrader dump (new lines added, see § 4), and no live setting.
  * No question was put to the owner: the request is explicit.
* **The target** (adoption framework § 1), fixed before any outcome-based result of any model on qualifying:
  * **The price:** the closing line, the only historical price held: Pinnacle's where OddsTrader recorded it (to
    7 Sep 2025), else BetOnline's. Live it would be Pinnacle's current line before the match (not tested).
  * **The matches:** tour-level qualifying (Slams, 1000s, 500s, 250s), ATP and WTA, completed or retired, standard
    format, priced.
  * **The seasons scored:** 2020–2026, walk-forward; 2019 calibrates only.
  * **The declared primary:** M1 (pooled), both stages, both tours, against the calibrated close (pre-registration).

## 2. Starting point

* **Code:**
  * The last commit is 1d8f53e (14 Oct 2026).
  * Uncommitted changes exist in files this study runs or imports: `current_best_model/compare.py`,
    `odds_input.py`, `odds_sources/table.py`, `src/ingest/oddstrader.py`; untracked: `current_best_model/training_rows.py`
    and `in_season_retrain/`.
  * The inputs are rebuilt with the build tree's own copy of `src/` (`C:/Users/zerom/tnr_tpl1021/src`), the code that
    built the instance.
* **Data** (SHA-256, 22 Oct 07:40 PDT):
  * The instance `template_2026-10-21b`:
    * `model_frame.parquet` e99212c9…;
    * `model_frame_chain.parquet` 73bb430c…;
    * `model_inputs.json` a3dcbf35….
    * It merged the packages `tennislive_box_fill`, `tennislive_box_fill_men_gsq` and `men_lower_level_fill`, and the
      feed snapshot 20261021.
  * The tree's `stage0_matches.parquet` eeb73c0a… and `timing.parquet` 8a388bee….
  * OddsTrader's dump before this study's pull:
    * `events.parquet` 6127c47e…;
    * `books_lines.parquet` bf99dae0…;
    * `lines.parquet` 830bef40….
* **Earlier looks at qualifying results:**
  * Stage 1 of the predictability diagnostic (30 Sep) scored Elo-type baselines on qualifying, without a price.
  * The sharp benchmark scored Polymarket's qualifying markets by horizon (352 markets).
  * The Polymarket sharp-money study measured money by level, qualifying included.
  * The event-levels study (8 Oct) built the inputs for qualifying matches but scored only main-tour and Challenger
    targets.
  * **No study has scored this model, or any TabPFN model, on a qualifying match.**
  * My 16 Oct checks read counts, coverage and margins only, no results: coverage of results, box scores, OddsTrader's
    listing, BetOnline's and Pinnacle's closes and Polymarket; BetOnline's margin on qualifying vs the main draw.
* **Environment:**
  * the `tennis` env (`./python.sh`) and the local TabPFN env (`./python_tabpfn_local.sh`);
  * an RTX 5090, idle at 07:30 PDT;
  * running: data collectors only (Pinnacle capture, Sofascore, TennisExplorer lower levels, Infosys ATP).
* **The idea and how it arose** (framework § 2):
  * **The mechanism, stated before the test:** the model's information beyond the close may carry over to qualifying.
    The markets there look less settled: the sharp benchmark found Polymarket's qualifying prices sharpen far more in
    the last day than the Slams' do.
  * **Not mined from scored seasons:** no qualifying season has been scored with a model.
  * **The kind:** an expansion as training rows; a new population as betting targets.

## 3. Plan

The design as first written is [preregistration.md](preregistration.md). It is frozen before the first fit, with its
SHA-256 recorded in the chronology. The order of work:
1. **Link** our qualifying matches to OddsTrader's events (no result read); the stop rule on the link rate.
2. **The every-book pull** for the linked events: Pinnacle's and BetOnline's lines, paced, receipts kept.
3. **Check the pull changes no main-draw price:** the instance's OddsTrader sources rebuilt for its frame before and after
   must be equal.
4. **The prices** of qualifying matches (Pinnacle first, BetOnline second); the market readings (question 1).
5. **The extended frame** with the instance's own code on the tree; the input gate.
6. **The speed column** for qualifying matches.
7. **Freeze the pre-registration**, then the fits (M0, M1, M2; 2019–2026; seeds 0–3), detached, one GPU job.
8. **Scoring:** the primary, the secondary readings, betting, the main-draw harm check.
9. **The report** for the owner, and this log's §§ 7–10.

**Resolution, against plausible effects** (inference, before any result):
* The window should hold about 12,000 scored qualifying matches (2020–2026, debut seasons out).
* With a per-match log-loss difference SD of about 0.05 nats against the close, the 95% half-width is about 1–1.5 mLL.
* The model's measured edge on the main tour is about 1–2.5 mLL by level (event-levels study). An edge of that size on
  qualifying would be borderline; a larger one would show.
* All seasons are historical, so the answer is available today (no waiting for new matches).

## 4. Chronology

Local time PDT (UTC−7). "Results" means any outcome-based score of any model on qualifying.

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| 16 Oct, 15:55–17:30 | Almaty linking (`tp.todays_matches`); training-frame composition; Stage 0, box-score, OddsTrader, Polymarket and margin coverage of qualifying (scratchpad `qual_odds_coverage.py`) | The owner's questions of 16 Oct | none (counts and margins only) | chat answers of 16 Oct |
| 22 Oct, 07:20–07:45 | Machine state; the active instance (21b, tree tnr_tpl1021); read the event-levels frame builder, the chain, `build_frame.py`, the odds step and its linker, the fit runner, `compare.py`, the in-season harm check, the speed extender; the match clock's windows for qualifying (97% exact; Slam qualifying 4–8 days and tour qualifying 1–3 days before the main draw's Monday) | Design | none | — |
| 22 Oct, 07:50 | Pre-registration written | Fix the design before any result | none | `preregistration.md` |
| 22 Oct, 07:40 (correction) | The row above gives 07:50 from memory; the file's own time is 07:36:56 PDT, and this log was opened at 07:37:34. Times below come from the clock | Rule 3 of the template | none | — |
| 22 Oct, 07:39 | `./python.sh src/eda/qualifying_targets/link.py` | Step 1: link Stage 0's qualifying matches to OddsTrader's events (no result read) | none | `oddstrader_link.parquet`, `oddstrader_eids.csv`, `link_counts.json`: 21,462 of 22,790 linked (2019–2025: 95.4%, over the 80% stop line); 0 events in both orientations, 4 matches with two events at the nearest day (resolved: BetOnline's close, then the lower id), 0 events nearest to two matches; gap 0 days for 21,017, 1 day for 445 |
| 22 Oct, 07:39 | Read the 40 sampled links and 40 unlinked matches by hand (`link_counts.json`) | Link quality | none | 25 of 25 read links right (names, sides, qualifying days). Unlinked: matches OddsTrader did not list, or spellings the variant forms miss (e.g. "Christopher Oconnell" against O'Connell) |
| 22 Oct, 07:39 | `pull_check.py --before` | Step 3's baseline: the instance's OddsTrader sources for its 39,507 linked frame matches | none | `pull_check_before.parquet` (books_lines bf99dae0…) |
| 22 Oct, 07:40 | `pull_books.sh` launched detached (Git Bash, hidden window): `src.ingest.oddstrader --books-eids oddstrader_eids.csv --max-requests 800` | Step 2: every book's lines for the qualifying events | none | 21,461 events to pull (1 pulled before), 302 batches; log `pull_books.log` |
| 22 Oct, 07:42 | `cmp` of the tree's `src/` against the repository's for the 15 modules the inputs, fits and scores use | Which code built the instance | none | all 15 identical |
| 22 Oct, 07:43 | `./python.sh src/eda/qualifying_targets/frame.py` | Step 5: the inputs of the qualifying rows, with the tree's code on the tree's tables; the gate | none | **gate passed:** 67,531 chain rows × 58 inputs equal (missing cells included), labels and debut flags equal, flip an involution. 22,790 qualifying rows (`frame.parquet`): level codes TQ 6 / GSQ 7, rounds 1–3, best of 3 (men's Slam qualifying recorded 5: 64 rows); coverage 95–97% on the statistics inputs (main draw 99–100%); indoor: men Stage 0's flag (11,003), women the WTA calendar (11,562), event (113), none (112); debut share 0.6% |
| 22 Oct, 07:45 | `./python.sh src/eda/qualifying_targets/speed.py` | Step 6: stage 2's speed column for men's qualifying | none | 11,003 men's rows filled (8,892 non-zero). The check on 2,000 sampled main-draw matches: 1,994 equal to 1e-9, 6 differ (max 0.017): exit 5 by the pre-registered criterion |
| 22 Oct, 07:46 | The 6 differences read against the serve-speed study's frame keys | Why the check failed | none | All 6 are "changed targets": the decided column was built on clock windows since moved by one day (es / lf / obs); the instance keeps the old values, the builder reads today's clock. `speed_extend`'s own check counts exactly this as allowed (0 unexplained). The call is right; deviation 5 below |
| 22 Oct, 07:49 | `./python.sh -m pytest test/qualifying_targets -q` | The arithmetic: margin removal, coherence, side orientation, bets and ROI, the arms' training rows | none | 6 passed |
| 22 Oct, 07:50 | **Pre-registration frozen:** `preregistration.md` SHA-256 b166f59bbc069483ffc3b552e4fa65d52e33b3d5834c4de1bcf6007bb0634370 | Before any outcome-based reading (the market reading and the fits come after) | none | — |
| 22 Oct, 07:59 | The pull ended (`pull_books.log`) | — | none | 302 requests, no block, exit 0. `events.parquet` and `lines.parquet` byte-identical to before; `books_lines.parquet` 2.16M → 3,023,210 lines (dfb6489a…) |
| 22 Oct, 07:59 | `pull_check.py --after` | Step 3: no main-draw price may move | none | **equal cell for cell** on all 39,507 frame matches (`pull_check.json`) |
| 22 Oct, 07:59 | `./python.sh src/eda/qualifying_targets/prices.py` | Step 4: the qualifying closes | none | Of 21,462 linked: Pinnacle's close kept for 17,647 (coherent 17,754; 107 stamped over 30 min after the start left out), BetOnline's for 19,137 (57 late left out). Pinnacle prices 73–100% of linked matches per tour, kind and season 2018–2025, none in 2026 (OddsTrader's Pinnacle ends 7 Sep 2025). BetOnline's line equal in both pulls on all 19,137. Priced (the odds input): 20,704 |
| 22 Oct, 07:59 | `run_fits.sh` launched detached | Step 7 | none | **M0 check failed:** M0 2019 seed 0 against the instance's stored fit: same ids, max abs diff 1.15e-4 (criterion 1e-6); the batch did not start (exit 6), as designed |
| 22 Oct, 08:01 | `./python_tabpfn_local.sh src/eda/qualifying_targets/diag_m0.py` | Why M0 differs | none (forecasts compared with forecasts, no outcome) | Training rows identical to the instance's job (`train_X_equal_to_the_instance_job` true). Asked the main block alone, the fit reproduces the stored one **bit for bit**; asked main then qualifying in one call, the main forecasts move by up to 1.15e-4, identically on a repeat (deterministic). So TabPFN's forecast of a row depends slightly on the other rows of its call (`diag_m0.json`) |
| 22 Oct, 08:02 | `fits.py` changed: one `predict_proba` call per block; the combined-query file renamed `M0__2019__seed0.combined_query_superseded.npz.bak` (kept), its check record likewise | So M0 is the instance exactly and no block perturbs another | none | Deviation 6 below |
| 22 Oct, 08:03 | `run_fits.sh` relaunched detached | Step 7 | none | **M0 check passed: max abs diff 0.0, equal exactly** (2019, seed 0). The batch started: M0, M1, M2 × 2019–2026 × seeds 0–3 |
| 22 Oct, 08:04 | `score.market()` → `market.json` (**first outcome-based look**: the closes' accuracy, pre-registered question 1; no model) | Question 1 | the market reading only |
| 22 Oct, 08:05 | A wait on `fits.log` ended at once: its pattern matched the first run's "check failed" line. Re-armed on new lines only | Monitoring | market reading | the fits kept running |
| 22 Oct, 09:24 | The batch ended (`fits.log`): 96 fits, exit 0 | Step 7 | market reading | M0 against the instance: **exact** in every fit of 2019–2025 (28 of 28); 2026 within 1.3e-4 (seeds 0–3), where the instance's call held 9,100 Polymarket-price rows beside its main block (2025: 1,592, and still exact) — deviation 6's mechanism (`m0_checks.json`) |
| 22 Oct, 09:25 | `score.py`: crashed before writing or printing anything (`row()` got its label `arm` twice). Renamed the function's parameters; rerun | Bug | market reading | none from the models |
| 22 Oct, 09:25 | `./python.sh src/eda/qualifying_targets/score.py` (**the model readings, pre-registered**) | Step 8 | — | **Primary: M1, both stages, both tours, vs the calibrated close: +0.97 mLL [+0.10, +1.83], 15,834 matches, P(better) 0.986: better.** Harm (main draw, M1 vs M0, both stages, 2020–2026, 32,027 matches): +0.028 [−0.087, +0.143], unresolved: **no harm**. `scores.csv`, `betting.csv`, `harm.json`, `forecasts.parquet`, `summary.json` |
| 22 Oct, 09:26 | Read the secondary readings (`scores.csv`, `betting.csv`, `harm.json`) | Step 8 | primary, harm | M0 vs calibrated close +1.09 [+0.23, +1.95]; M2 −0.01 [−0.88, +0.86]. M1 − M0 −0.12 [−0.44, +0.20] (P 0.22), M1 − M2 +0.98 [+0.25, +1.71]. M1 by kind: GSQ +1.50 [+0.16, +2.85], TQ +0.68 [−0.47, +1.83]; by period: 2020–24 +0.69 [−0.48, +1.86], 2025–26 +1.62 [+0.65, +2.60]; men +1.18 [+0.10, +2.26], women +0.76 [−0.38, +1.90]; positive in 6 of 7 seasons (2021 −0.72 [−4.88, +3.44]). Against the raw close: M1 +1.51 [+0.34, +2.67]. **Betting, EV > 0, 1 unit:** M1 at BetOnline's close +2.5% [+0.5, +4.7] on 7,009 bets (P(ROI > 0) 0.99), at Pinnacle's +1.0% [−1.5, +3.5] on 4,685 (0.78); M0 +4.0% [+1.8, +6.1] / +1.7% [−0.5, +4.1]; M2 +0.3% / −2.4%. EV ≥ 0.02: M1 +4.5% [+1.5, +7.6] / +3.5% [−1.2, +8.3]. M1's stage-1 slopes on qualifying 0.89–1.01 (men), 0.92–1.02 (women); b grows to 0.07 by 2026 |
| 22 Oct, 09:27 | `explore_decomposition.py` (**exploratory, not pre-registered**, written after the readings above) | How much of the betting reading is the price itself | all of the above | ROI with no model, same bets rule and matches: the raw close (pure line-shopping at BetOnline) −2.7% [−8.6, +2.8] on 2,734 bets; the calibrated close (recalibration + line-shopping) +2.0% [−0.5, +4.4] at BetOnline (3,763 bets), −4.3% [−7.2, −1.7] at Pinnacle (1,291). `exploratory_decomposition.json` |
| 22 Oct, 09:28 | `explore_recalibration.py` (**exploratory, not pre-registered**) | Is the gain only a curved recalibration of the close (the one-slope baseline cannot bend)? | all of the above | A flexible recalibration (z, z³, z·\|z\|, per tour, walk-forward) is no better than the one-slope one: curved − calibrated −0.40 [−0.85, +0.05] (P 0.04). Against it: M1 +1.36 [+0.50, +2.23], M0 +1.49 [+0.65, +2.32]. The gain is not the close bent; it comes from the other inputs. `exploratory_recalibration.json` |
| 22 Oct, 09:30 | README written; every figure checked against `scores.csv`, `betting.csv`, `market.json`, `harm.json` and the two exploratory files; four wordings corrected (which book's calibration, "every one of its inputs", the second reason Almaty could not run, the women's qualifying source) | Step 9 | all | `README.md` |
| 22 Oct, 09:40 | §§ 7–9 written; the study added to `docs/studies/README.md` | Step 9 | all | — | 14,592 qualifying and 28,361 main-draw matches of 2019–2025 with both closes. **Log loss (lower is better), BetOnline − Pinnacle:** qualifying +0.62 mLL [+0.14, +1.10], so Pinnacle is sharper (power method +0.92 [+0.36, +1.47]; men +0.78 [+0.03, +1.52], women +0.47 [−0.27, +1.20] unresolved); main draw −0.54 [−2.33, +1.24], unresolved. **Calibration slopes** (1 = calibrated; above 1 = too timid, favourites win more than priced): qualifying Pinnacle men 1.108 [1.047, 1.170], women 1.132 [1.061, 1.204], BetOnline 1.090 / 1.118; main draw Pinnacle 1.023 [0.983, 1.064] / 1.039 [1.000, 1.079], BetOnline 1.051 / 1.059. **Margins (mean):** Pinnacle 4.42% on qualifying vs 2.69% on the main draw; BetOnline 3.79% vs 3.62% |

## 5. Sources

* **OddsTrader:**
  * the odds service, through `src/ingest/oddstrader.py` (decision of 6 Oct 2026; scraping approval of 8 Oct 2026);
  * the listing of 2018-01 to 2026-10 already on disk;
  * the every-book lines pulled here for the qualifying events (§ 4).

## 6. Judgment calls and deviations

1. **The primary arm is M1 (pooled), not M0 or M2.**
   * The reason held at the time: it is the natural extension of the current model, and it answers both of the
     owner's questions (qualifying edge, main-draw harm) with one model.
   * M0 sees level and round values it never trained on (level 6/7, rounds 1–3). M2 has few rows in its early
     seasons.
   * Chosen before any result.
2. **The same query rows in every arm** (level 6/7, rounds 1–3), so that M0, M1 and M2 differ only in their training
   rows.
   * The other option for M0 was the parent event's level code with a main-draw round. It would test a different
     encoding, not only different rows.
   * Chosen before any result.
3. **Scored against the calibrated close** (one slope per tour, walk-forward), as `compare.py` scores a model against
   its close; the raw close is reported too.
   * Chosen before any result.
4. **Seeds 0–3,** as the harm checks and `compare.py` use them; the live model averages 16.
   * Chosen before any result.
5. **Deviation: the speed check's criterion.**
   * The pre-registered check asked the builder to reproduce the instance's column "to 1e-9" on 2,000 main-draw
     matches. 6 differ, all because the decided column was built on clock windows since moved by a day.
   * I applied the instance's own criterion instead (`in_season_retrain/speed_extend.py`: differences only where the
     targets changed). By that criterion 0 differences are unexplained.
   * The qualifying values come from today's clock, as the instance's "extended" rows do. No result had been read.
6. **Deviation: one TabPFN call per query block.**
   * Found at the M0 check, 08:00: in one `predict_proba` call a row's forecast moves by up to 1.2e-4 with the other
     rows of the call. Asked alone, the main block reproduces the instance bit for bit.
   * Changed `fits.py` to ask each block (main, qualifying) in its own call.
   * The instance's own 2025–2026 fits asked their main block together with Polymarket-price blocks, so M0's
     2025–2026 main forecasts may differ from the instance's by about 1e-4. The harm check compares M1 with M0, both
     asked alike, so it is unaffected.
   * The pre-registration did not specify how the blocks are asked. No result had been read.

## 7. Claims and their evidence

Every number below is observed (run here) unless marked. None rests on a choice made after seeing results, except the
two readings marked exploratory.

| README claim | Evidence | Status |
|---|---|---|
| The pooled model beats the calibrated close on qualifying: +0.97 [+0.10, +1.83], 15,834 matches, P 0.99 | `scores.csv` (M1 vs calibrated close, both stages, primary); `summary.json` | observed; pre-registered primary |
| Today's model +1.09 [+0.23, +1.95]; qualifying-only −0.01 [−0.88, +0.86]; pooled − today's −0.12 [−0.44, +0.20] | `scores.csv` | observed; secondary (flags) |
| Slices: men, women, Slam vs tour qualifying, periods, 6 of 7 seasons positive | `scores.csv` (groups tour, kind, period, season) | observed; secondary |
| Betting at BetOnline's close +2.5% [+0.5, +4.7] (7,009 bets), at Pinnacle's +1.0% [−1.5, +3.5]; today's model +4.0% / +1.7%; EV ≥ 2%: +4.5% / +3.5%; 4,799 bets on favourites | `betting.csv` | observed; secondary (the decision reading) |
| No-model rows: calibrated close +2.0% / −4.3%; raw close at BetOnline −2.7% | `exploratory_decomposition.json` | observed; **exploratory, after the results** |
| A curved recalibration is no better (−0.40 [−0.85, +0.05]); the model beats it by +1.36 | `exploratory_recalibration.json` | observed; **exploratory, after the results** |
| Main draw: pooled vs today's +0.03 [−0.09, +0.14] on 32,027; no harm | `harm.json` | observed; pre-registered harm check |
| Market: BetOnline − Pinnacle +0.62 [+0.14, +1.10] on qualifying, −0.54 [−2.33, +1.24] on the main draw; margins 4.4% / 3.8% (qualifying), 2.7% / 3.6% (main draw); slopes 1.11 / 1.13 | `market.json` | observed; pre-registered question 1 |
| Pinnacle's close held for 17,647 qualifying matches, BetOnline's for 19,137; no main-draw price moved | `prices_counts.json`, `pull_check.json` | observed |
| The inputs reproduce the instance's exactly on all 67,531 rows | `frame_manifest.json` (gate) | observed |
| Today's model reproduces the instance's fits exactly (2019–2025) | `m0_checks.json`, `diag_m0.json` | observed |
| The three bet-day changes; "about a day of work" | `src/pipeline/live.py` (the qualifying filter, `_round`, `_events`), CLAUDE.md (feeds) | the changes: observed in the code; the time: an estimate |
| Why qualifying was left out (16 Oct) | the search agent's report, re-checked quotes (Appendix) | observed (re-checked) |

## 8. Weak points

* **Threats to validity, most important first:**
  * **Closing prices, not bet-time prices.** The whole test is at the close, which is the model's input and the price
    bet at. Live bets are placed earlier, at prices the model was not trained on. The edge at bet time is unmeasured;
    the trial measures it.
  * **Wrong links.** A qualifying match given another match's price would make the close look worse than it was, and
    the model's gain larger. Against it:
    * 25 of 25 hand-read links were right;
    * matching needs both players' names, the tour and the clock's window, one to one;
    * the close's accuracy on qualifying (log loss 0.587 at Pinnacle) is as good as on the main draw (0.591), which
      many wrong prices would spoil.
  * **Late lines.** A line stamped up to 30 minutes after the listed start counts as the close, as in the live model's
    own rule. An in-play price would sit in both the input and the baseline.
  * **Power.** The primary's 95% half-width is about ±0.87 mLL against an estimate of +0.97; it clears 0 with little to
    spare. The slices' readings are flags only.
  * **Multiplicity.** One primary, fixed and hashed before any result. The secondary tables hold many cells, and none
    is used as a verdict.
    * Recommending today's model over the pooled one is a choice among three. It rests on their difference being
      small and unresolved (−0.12 ± 0.32) and on operational simplicity, not on a better score, and the trial is its
      confirmation.
  * **Leakage.**
    * Training rows are seasons before the scored one (tested: `test_training_masks_of_the_arms`).
    * Calibration and stage 2 are walk-forward.
    * The inputs follow the leak-proof clock, whose qualifying windows sit before the main draw (§ 4, 07:20 row).
    * The speed column uses the release rules.
    * No feature or setting was tuned on qualifying.
  * **The incumbent:** none. No qualifying model existed.
* **Where a flaw would most likely hide:**
  * the link of matches to OddsTrader events (orientation, a few wrong pairs);
  * the 30-minute late-line rule on qualifying, whose real start times drift more than main-draw ones.
* **What a re-design would do:**
  * score at earlier prices: OddsTrader's opening lines (Pinnacle's opening line is held for 17,805 matches), and
    Polymarket's price history for 2025–2026;
  * use sixteen seeds, and test the Thinking half of the live blend.
* **The experiment most likely to overturn the conclusion:** the live trial at bet-time prices.

## 9. Reviewer checklist

* [ ] Re-derive the primary: `./python.sh src/eda/qualifying_targets/score.py`, then read `summary.json`'s
  `primary` (+0.968 [+0.105, +1.831]).
* [ ] Confirm the pre-registration is unchanged: `sha256sum docs/studies/qualifying_targets/preregistration.md` gives
  b166f59b….
* [ ] Confirm no main-draw price moved: `pull_check.json`, `equal_cell_for_cell: true`.
* [ ] Confirm the input gate: `frame_manifest.json`, `gate.passed: true`, 67,531 rows × 58 inputs.
* [ ] Confirm M0 = the instance: `m0_checks.json` (exact 2019–2025).
* [ ] Read 20 more links by hand: `oddstrader_link.parquet` against `events.parquet` (names, sides, dates).
* [ ] Check the verdict words against the intervals in the README's tables.
* [ ] `./python.sh -m pytest test/qualifying_targets -q` (6 tests).

## 10. Reproduction

From the repository root, in order (written before the scores were read; the commands are the ones run):

```
./python.sh src/eda/qualifying_targets/link.py                      # step 1: link (seconds); oddstrader_link.parquet, oddstrader_eids.csv
./python.sh src/eda/qualifying_targets/pull_check.py --before       # step 3's baseline
bash data/studies/qualifying_targets/pull_books.sh                  # step 2: the every-book pull, ~20 min, paced; network
./python.sh src/eda/qualifying_targets/pull_check.py --after        # step 3: must print "equal cell for cell: True"
./python.sh src/eda/qualifying_targets/prices.py                    # step 4: prices.parquet
./python.sh src/eda/qualifying_targets/frame.py                     # step 5: the inputs, with the gate (~1 min; needs the tree C:/Users/zerom/tnr_tpl1021)
./python.sh src/eda/qualifying_targets/speed.py                     # step 6: speed.parquet (~15 s)
bash data/studies/qualifying_targets/run_fits.sh                    # step 7: GPU, ~1 h; the M0 check first, then 96 fits (seeds 0-3)
./python.sh src/eda/qualifying_targets/score.py                     # step 8: scores.csv, betting.csv, market.json, harm.json
./python.sh -m pytest test/qualifying_targets -q                    # the arithmetic's tests (offline)
./python_tabpfn_local.sh src/eda/qualifying_targets/diag_m0.py      # the M0 diagnostic of 08:01 (GPU, ~2 min)
```

Seeds 0–3; the bootstrap of the betting reading uses seed 20261022 and 2,000 draws; the samples read by hand in
`link_counts.json` use random_state 20261022. The superseded fit of 08:00 is kept as
`local/M0__2019__seed0.combined_query_superseded.npz.bak`.

## Appendix: briefs

* **The search of 16 Oct 2026** (an Explore agent, read-only; it saw no result of any qualifying model, none existing).
  Its report was the basis of the 16 Oct answer "why did we choose to omit them"; I re-checked its key quotes against
  the files (the predictability diagnostic's scope, stage 1's lines 39 and 94, candidates.md line 45, the current-best-
  model decision's line 127, the event-levels study's findings and the Polymarket studies' qualifying rows). Its brief,
  verbatim:

  > Repository: C:\Users\zerom\Documents\Tennis-predictions (a tennis match-prediction project). Read-only search; very thorough.
  >
  > Background: the current model (a TabPFN fit on 57 inputs, closing odds among them) trains and predicts only on main-draw matches. Its population is defined in code as MAIN_GROUPS = ("GS", "FIN", "T1000", "T500", "T250") in src/eda/tabpfn_thinking/common.py, and Stage 0's `qualifying` flag is False on all 67,226 training rows. The operator layer src/pipeline/live.py leaves out "qualifying" matches, and the bet sheet blocks "not a main-tour match (outside the model's population)". Qualifying matches ARE held in Stage 0 (data/studies/predictability_diagnostic/stage0_matches.parquet has a `qualifying` column and an `evaluation` column) and lower-level observations (Challengers, qualifying, ITF) enter the model's INPUTS through "the level layer" (docs/decisions/2026-10-10-level-evidence-layer.md), but never as prediction targets.
  >
  > The owner asks: "why did we choose to omit [qualifying] from our model?" I need the actual recorded reasoning, not a guess. Find:
  >
  > 1. WHERE and WHEN the prediction/evaluation population was first restricted to main-draw / main-tour matches, and any stated REASON. Likely places: docs/studies/predictability_diagnostic/ (Stage 0 / Stage 4 design; what the `evaluation` column means), docs/studies/tabpfn_thinking/, docs/studies/tabpfn_leakproof/, docs/decisions/*.md, docs/research/ (data inventory, Polymarket coverage research), docs/research/legacy-one-shot/ (inherited suggestions from a prior LLM — note these are unapproved), docs/00_overview.md, docs/pipeline.md, README.md, and src/eda/predictability_diagnostic/stage0*.py docstrings. Search terms: "qualifying", "qualif", "main tour", "main-tour", "main draw", "population", "evaluation", "MAIN_GROUPS", "tour-level", "lower-level", "lower level".
  > 2. Whether the OWNER ever explicitly decided it (a docs/decisions/ file or a quoted owner instruction), versus it being inherited from the prior LLM's scaffold or a default nobody revisited. Quote the owner's words if any.
  > 3. Any recorded reasons tied to data: e.g. no historical closing odds for qualifying (tennis-data.co.uk covers main draws only?), OddsTrader coverage of qualifying, box-score coverage of qualifying, Tennis My Life's coverage of qualifying (it lacks WTA qualifying since June 2026; men's Challenger qualifying), timing data, Polymarket listing qualifying or not.
  > 4. Any study, rejected-ideas ledger entry, or feature-universe note that considered adding qualifying (or lower levels generally) as prediction TARGETS, and what happened. Check for a rejected-ideas ledger (grep "rejected" in docs/).
  > 5. Any measured evidence about how well markets price qualifying matches (e.g. closing-odds calibration on qualifying vs main draw) anywhere in docs/studies or data/studies reports.
  >
  > Report: for each item, the finding with exact file paths (and line numbers where useful), dates, and short verbatim quotes. Clearly separate (a) owner decisions, (b) prior-LLM inherited suggestions, (c) study findings, (d) your inference. If something is not found, say so explicitly. Keep the report under ~900 words.

* No subagent was used for the study itself (22 Oct): every step was run and read by the lead.

---

# Part 2: the top 40% of predicted edges (22 Oct 2026, from 10:32 PDT)

Opened at 10:32, before this part's first step. Same session.

## P2.1 The request

* **The owner's words, verbatim** (22 Oct 2026, after reading Part 1's report):
  > "Perform a test to see how we'd do at pinnacle close and betonline close if we only bet on the best top 40%
  > predicted edges for the qualifying matches with the current best model (and offset)"
* **How it was read:**
  * **"The current best model"** is today's model unchanged: Part 1's arm M0, whose fits equal the live instance's
    (exactly for 2019–2025). It is not the pooled arm M1, which the owner has not adopted.
  * **"(and offset)"** is the serve-speed offset added to the model's log-odds: stage 2. In this project's words, the
    Thinking decision of 20 Oct calls Thinking plus that term "Thinking + offset", and the edge-anatomy notes call it
    "the speed offset". So the forecast is Part 1's "both stages": the calibration slope per tour plus b̃ · spd_L,
    fitted walk-forward on qualifying (2019 .. Y − 1), as in Part 1.
  * **"Predicted edge"** is the expected profit per unit at that book's closing odds, margin included:
    EV = q · d − 1 for the side bet.
  * **"The best top 40%"** means: of the bets the model would make at that book (every side with EV > 0, as in
    Part 1), keep the 40% with the highest EV.
    * The cut is the 60th percentile of EV among those bets over 2020–2026.
    * It uses forecasts and odds only, no result, but it sees the whole window's distribution of edges.
* **Set aside, and why:**
  * **The five-pattern adjustment** (also a log-odds offset in the live predictions): the owner wrote "offset",
    singular, which this project uses for the speed term. Its score is not built for qualifying matches.
  * **Sixteen seeds,** as the live model averages: Part 1's fits have seeds 0–3 for qualifying. Fitting 4–15 would
    take about 2 hours of GPU; offered instead.
  * **"Top 40% of all matches"** instead of "of the bets": the model bets on about 44% of BetOnline-priced matches, so
    that version would keep almost every bet and would not answer a question about selectivity. Reported as a single
    line.
* **The checks added** (each one line, labelled):
  * the cut set in advance: each season's cut from the earlier seasons' bets only (2021–2026);
  * ranking by the edge in probability points instead (q − 1/d);
  * the live instance's own stage-2 coefficients (fitted on main draws) applied to qualifying, as the model would run
    if simply pointed at them;
  * the other 60% of the bets, for contrast.

## P2.2 Plan

1. `src/eda/qualifying_targets/top_edges.py`: today's model's stage-2 forecasts on Part 1's scored qualifying matches
   (2020–2026, debut seasons out); bets at Pinnacle's and BetOnline's closes; the top 40% by EV; ROI with Part 1's
   bootstrap (2,000 draws of 4-week blocks); breakdowns by period, tour and kind; the checks above.
2. Read, log, and add a section to the README.

**Status of the reading:** owner-requested, on seasons Part 1 already scored. It is not a fresh confirmation. The 40%
is the owner's choice, not fitted here.

## P2.3 Chronology

| When | Step | Why | Results seen by then | Output |
|---|---|---|---|---|
| 22 Oct, 10:32 | Part 2 opened (this section) | Before the first step | Part 1's readings | — |
| 22 Oct, 10:33 | `./python.sh src/eda/qualifying_targets/top_edges.py` (forecast: M0 + stage 2 fitted on qualifying; the check rows for the live instance's own stage 2) | The owner's test | Part 1's readings | **Top 40% by EV (qualifying-fitted stage 2):** BetOnline +5.4% [+1.7, +8.8] on 2,691 bets (cut EV ≥ 2.5%), Pinnacle +2.3% [−1.6, +6.2] on 1,730 (cut ≥ 1.6%); all +EV bets +4.0% / +1.7%; other 60% +3.1% / +1.4%; cut set in advance (2021–26) +6.7% [+3.0, +10.4] / +2.2% [−1.8, +6.4]; by points +5.4% / +2.4%. **The check, the live instance's stage 2 (fitted on main draws):** all +EV +4.5% [+1.1, +7.7] (5,572) / +4.7% [+0.7, +8.7] (2,857); top 40% +8.3% [+3.1, +13.5] (2,229) / +9.8% [+3.7, +16.1] (1,143) |
| 22 Oct, 10:34 | The two stage-2 versions' coefficients read (`top_edges.json`) | Why the live version returns more | the above | Main-draw stage 2 shrinks the model's log-odds more (men 0.88–0.91, women 0.92–0.98) than qualifying-fitted (men 0.94–1.05, women 0.98–1.07); speed b similar in size |
| 22 Oct, 10:34 | `explore_stage2_variants.py` (**exploratory**, after the readings) | Is the live version's lead plausible or luck? | the above | Accuracy against the calibrated close: live version +1.22 [+0.36, +2.09], qualifying-fitted +1.09 [+0.23, +1.95]; live − qualifying-fitted +0.13 [−0.32, +0.59], unresolved. Bets: shared (same side) BetOnline +6.2% [+3.4, +8.9] (4,389), Pinnacle +3.5% [−0.1, +7.2] (2,181); the qualifying-fitted version's own extra bets (≈2,100–2,300, nearly all favourites) −0.2% / 0.0%; the live version's own extra bets (nearly all underdogs) −2.2% [−12.0, +7.1] (1,183) / +8.8% [−2.4, +20.6] (676); no match bet on opposite sides. `exploratory_stage2_variants.json` |
| 22 Oct, 10:35 | `top_edges.py` rerun with the full checks for the live version too (deviation P2-1) | The live instance's stage 2 is the literal "current best model (and offset)" | the above | **Live version, top 40%:** cut set in advance (2021–26) +8.6% [+3.0, +13.9] (1,909) / +10.9% [+4.6, +17.8] (1,158); other 60% +1.9% / +1.4%; by points +7.3% / +8.9%; 2020–24 +9.4% / +9.7%; 2025–26 +4.3% [−6.8, +14.8] (490) / +9.8% [−8.2, +31.5] (207); men +10.3% / +15.2%; women +5.3% / +1.1%; Slam qualifying +15.8% / +0.8%, tour qualifying +4.7% / +14.4% (slices disagree across the books: noise) |

## P2.4 Judgment calls and deviations

* **P2-1. Both stage-2 versions reported side by side, after their readings were seen.**
  * The plan made the qualifying-fitted stage 2 the main reading (Part 1's recipe) and the live instance's own stage 2
    a check.
  * On reading the results, the live instance's own stage 2 is the literal "current best model (and offset)": the
    model as it runs today, its offset's coefficients fitted on main draws, pointed at qualifying.
  * So the report gives both, with the order of events stated. Neither is called better: their forecasts are equally
    accurate (+0.13, unresolved), and the betting gap rests partly on ~680–1,180 extra underdog bets with very wide
    ranges.
* **P2-2. Recommending the live version for the trial** rests on its being the unchanged live model (no refit to
  maintain), not on its higher backtest return. Any edge used to size stakes should come from the trial, shrunk.

## P2.5 Weak points

* **The same seasons as Part 1.** This is a betting rule chosen (by the owner) after Part 1's betting reading was seen.
  It is not a confirmation, and nothing here was pre-registered.
* **Wide ranges.** The top-40% sets hold about 1,100–2,700 bets. The ranges are ±4–6 points, and the slices disagree
  across the books.
* **Two versions tried.** Reporting the better one alone would overstate it; both are reported.
* **Recent seasons are weaker for betting:** 2025–26 is unresolved in every version (n ≈ 200–630).
* **Four seeds** (the live model averages sixteen), closing prices only, and the five-pattern adjustment left out.

## P2.6 Claims, reproduction

* **README's follow-up table:** `top_edges.csv`, rows "top 40% by EV" / "all +EV bets" / "other 60%" / "cut set in
  advance" for both forecasts. The cut values (EV): live version BetOnline 0.0280, Pinnacle 0.0187; refitted version
  0.0252 / 0.0161 (`top_edges.json`). Observed; not pre-registered.
* **"Equally accurate" and the extra bets:** `exploratory_stage2_variants.json`. Observed; exploratory.
* **Reproduction:**
  ```
  ./python.sh src/eda/qualifying_targets/top_edges.py
  ./python.sh src/eda/qualifying_targets/explore_stage2_variants.py
  ```
  Both read Part 1's fits (`local/`) and frames; a few seconds each, CPU only. The bootstrap seed is 20261022.
* **22 Oct, 10:40:** the README's follow-up section written; two rounded counts corrected to their ranges.

## P2.7 The owner's confusion, and a wording correction (22 Oct 2026)

* **The owner's words, verbatim:**
  > "What's the difference between the live version and the "refitted" version, im confused. Whats the refitting?"
  >
  > "I'm so confused. When did the refitted version even get proposed? This is all news to me. if I run A1-A5, does it
  > ever use the "refitted" version? Does the "live" version the version without calibration? why would we use that at
  > all? our process includes calibration? im soooo confused"
* **What went wrong** (mine):
  * Part 1's pre-registration fitted stage 2 per population, so the qualifying scores used calibration learned on
    qualifying matches. This followed `compare.py`'s practice of fitting the calibration on the matches it scores.
  * The first report called this "the same two stages as the live model" without saying that the calibration's
    numbers came from qualifying, not from the main draw as live.
  * Part 2 then named the two "the live version" and "the refitted version". That read as if one were uncalibrated,
    and as if a new model had been proposed.
* **The facts given to the owner:**
  * Both versions are calibrated.
  * A1–A5 uses only the live model's calibration, learned on main-draw matches, and today does not predict qualifying
    at all.
  * The qualifying calibration exists only in this study's scoring code. It was never proposed as a change.
* **The correction (by adding, the numbers unchanged):**
  * README "What I did" step 4 now states the difference.
  * The two versions are renamed "the live model (calibrated on main draws, as A1–A5)" and "calibrated on qualifying
    (test only)" in the summary and the follow-up.

---

# Part 3: the five-pattern adjustment on qualifying (22 Oct 2026, from 13:04 PDT)

Same session (`40624dcb-dd11-4b33-9758-215a45a8677e`). Between Parts 2 and 3 the owner decided to bet qualifying with
the live model (`docs/decisions/2026-10-22-qualifying-bets.md`) and it was built into A1–A5 (master pipeline process
log, Part 8), with the five-pattern adjustment on for qualifying as for the main draw, untested there.

## P3.1 The request (verbatim)

> "I recommend I score it on past qualifying matches before Saturday, at no cost. "
> Test this.
>
> Stakes should be the same as main.

The quote is from my report of Part 8: "Five-pattern adjustment: it's on for qualifying because it's part of the live
model, but the study didn't test it there, and one of its parts reads seeding, which in qualifying means the
qualifying seed. I recommend I score it on past qualifying matches before Saturday, at no cost." The stakes sentence
is a decision, recorded in the decision file; it changes no code (the sheet already staked qualifying as main).

## P3.2 Interpretation, and what is fixed before any result

* **The question:** does the adjustment, as the live engine applies it, help or harm the live model's qualifying
  forecasts?
* **z as the engine computes it,** for the study's scored qualifying matches (2020–2026, debut seasons out, priced: the
  population of Part 1's primary and Part 2), on the instance's build tree (the tables the study's forecasts were built
  on):
  * the registered members (`unpriced_leads/live_members.py`, the tree's copy, identical to the repository's), its
    not-built members missing as live;
  * the live gate by each match's month (`patterns_live.live_gates`, on the tree);
  * the frozen parameters (`check_now/now/params.json`, its SHA-256 checked), z capped at ±3.5;
  * logit q += b z, b = 0.0616 (`adjustment.json`).
* **The forecast it is added to:** the live model's (Part 2: today's fits with the instance's stage 2 fitted on main
  draws), seeds 0–3.
* **Kind (framework § 0):** an expansion, an adopted adjustment with frozen parameters applied to a new population. Its
  effect where adopted: +0.41 mLL in the check's window (9,457 main-draw matches, 2025–Sep 2026). Plausible here: from
  about −0.5 to +0.5.
* **Primary:** paired log loss, patterns on against off (positive = on better, 1000 × mean difference), every scored
  match, both tours, 4-week blocks with seed variance (`compare.paired`, matched seeds), as Part 1.
* **Decision rule (the framework's default harm check), fixed now:**
  * turn the patterns off for qualifying if on is worse by more than 0.10 mLL with the whole 95% interval below 0;
  * otherwise keep them on, as the owner's live model.
  * The reading is labelled better, worse or unresolved, with P(better).
* **Secondary, descriptive only:**
  * each version against the calibrated close;
  * betting at BetOnline's and Pinnacle's closes (every +EV side; the top 40% of edges), both versions;
  * slices: men and women, tour and Slam qualifying, 2020–24 and 2025–26.
* **Seen before this:** z and the two forecasts of the 16 round-1 matches replayed for Part 8 (Almaty and Brussels, 17
  Oct 2026), 16 of the scored matches. No aggregate of the patterns on qualifying.

## P3.3 Plan, each with its check

1. **Members** for the scored ids, the tree's `live_members.py` run in the tree, outputs outside it. Checks:
   * its ace gap equals the study frame's `in_iosO_ace` (its own `--frame` check);
   * nothing written into the tree (its extracts exist, their records match: checked 13:00).
2. **Gates and z** in this repository's process, the tree's tables for the gate counts. Check: the 16 replayed matches'
   z equal the replay's own live z (`live_patterns.parquet` of the Part 8 replay).
3. **Scores:** the primary, the secondaries, the slices. Then the report and the owner's answer.


## P3.4 Chronology (PDT)

| Time | What |
|---|---|
| 13:04 | Part 3 opened (P3.1–P3.3), before any member or score was computed. The stakes decision recorded (`docs/decisions/2026-10-22-qualifying-bets.md`, the master pipeline README, CLAUDE.md) |
| 13:05–13:12 | Read the engine's pattern path (`patterns_live.build_for_run`, `check_now.score_from_params`, `live_members`); the tree's copies of the seven pattern modules are byte-identical to the repository's; the tree holds the builder's two input extracts with matching records (no write needed); the projection reads the 48 non-price, non-context inputs, so the odds input does not enter z. `src/eda/qualifying_targets/patterns_check.py` written |
| 13:13 | `--members` started: the tree's `live_members.py`, run in the tree, for the scored ids (outputs in `data/studies/qualifying_targets/patterns/`, the IOS table's copy in the session's scratch folder) |
| 13:06 | (Correction to the two rows above: their times were written ahead of the clock. The reading ran about 12:55–13:04 and `--members` started at 13:05.) |
| 13:06–13:13 | **Members** for the 15,834 scored matches (7,835 men's, 7,999 women's; 10,265 tour, 5,569 Slam qualifying): the builder's own frame check passed on all 15,834 (its ace gap equals the study frame's `in_iosO_ace`, largest difference 0.0); present: post-Slam, venue pace, seeded, fame and rhythm d7 15,834 each, rest under 20 h 14,956, past fatigue 11,489; the five not-built members 0, as live. Nothing written into the tree but Python's bytecode caches (`__pycache__`): no data file changed there since 13:05 |
| 13:14–13:16 | **Scored** (`--score`). **Parity: the 16 replayed matches' z equal the engine's own live z exactly** (16 of 16, largest difference 0.0). z: sd 0.81, 12 matches at the cap; shift mean 0.038 log-odds, at most 0.216; the live gate switched members off in some months (G1's three in 20, G4's pair in 14, rhythm d7 in 5, past fatigue in 2) |
| 13:16 | **Primary: on against off +0.28 mLL [−0.07, +0.63], P(better) 0.945, unresolved. The harm check does not fail: the patterns stay on for qualifying (the rule of P3.2).** Off against the calibrated close +1.22 [+0.36, +2.09] better; on +1.51 [+0.65, +2.37] better. Slices (flags, not verdicts): men +0.39 (P 0.93), women +0.18 (0.74), tour qualifying +0.50 [+0.02, +0.98] better, Slam qualifying −0.12 (0.31), 2020–24 +0.32, 2025–26 +0.19. **Betting at the close, patterns on against off:** BetOnline every +EV side +5.8% [+3.1, +8.4] (6,164 bets) against +4.5% [+1.1, +7.7] (5,572); its top 40% +10.4% [+5.1, +15.7] against +8.3%; Pinnacle every +EV side +5.3% [+1.6, +8.7] (3,444) against +4.7%; its top 40% +14.3% [+7.8, +21.0] against +9.8% |
| 13:18–13:22 | Reported: this study's README (follow-up 2, and a line in "In short"), the decision file (the test, and "stays on"), the decisions index row, the master pipeline README's qualifying section, CLAUDE.md's qualifying block, the studies index row. Peer tennis-predictions-f8, editing some of the same files for the live-model naming fix, told which lines first |

## P3.5 Judgment calls and deviations

* None from P3.2's design. Seen before the scores: nothing beyond P3.2's note (16 replayed matches).
* **Run inside the instance's tree, not a work tree:** its tables are the forecasts' own, and it holds the builder's two
  extracts with matching records, so the builder reads and writes nothing there (checked after: only bytecode
  caches). A work tree would have needed a replay's tables step.
* **The month of each match:** its observed day in the tree's timeline (live: the run's day), for the gate.

## P3.6 Claims and their evidence

| Claim | Evidence |
|---|---|
| z here is the engine's z | `patterns/patterns.json` "parity": 16 of 16 equal to `replay_2026-10-19_Q1_qualifying_maindate/live_patterns.parquet` |
| The members read the same surface IOS as the model's input | `patterns/members.json` frame check, 15,834 of 15,834 equal |
| No harm on qualifying; +0.28 mLL, unresolved | `patterns/patterns.json` "accuracy", row 1; `harm_check_fails` false |
| Returns at the close are higher with the patterns | `patterns/patterns.json` "betting"; `patterns/rows.csv` |

## P3.7 Weak points

* **Unresolved:** the gain could be zero (P(better) 0.945). The decision rests on the harm check, as fixed.
* **The Slam slice leans the other way** (−0.12, P 0.31). A flag, not a verdict; one of the members reads seeding,
  which in Slam qualifying is a qualifying seed.
* **The betting gains reuse the same matches as the accuracy reading.** They are descriptive, at closing prices, and
  the top-40% cut was set on the matches it is scored on (Part 2's caveat).
* **Four seeds**, as every comparison; the live model averages sixteen.
* **The not-built members** are missing here as live; if they are ever built, z changes.

## P3.8 Reproduction

`./python.sh src/eda/qualifying_targets/patterns_check.py --members` (about 7 minutes; set QT_SCRATCH for the IOS
table's copy), then `--score` (about 2 minutes). Outputs: `data/studies/qualifying_targets/patterns/`.

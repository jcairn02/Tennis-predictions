# Changes suggested under the adoption framework: a checklist

9 October 2026 · For the owner, who runs each item as its own prompt · Sorted by how confident I am that the change is right. Importance says what is at stake if it is. The numbers stay fixed: #7 is now the softer version the owner chose, rated higher, and #10 was added for the run order.

**How to use it.**
* **Each item has a ready-to-paste prompt** written for a fresh session. A new session loads `CLAUDE.md` by itself, so the prompts don't repeat its rules (`./python.sh`, no git commits, the frozen reference).
* **Run order:** see "Run order" below. Each prompt checks what is already done.
* **Your decision is written into the prompt.** Prompts that change a decided thing say "this prompt is my decision". Delete that line if you would rather the session stop and report.
* **Each prompt ends by ticking its box here,** with a one-line outcome.

| # | Change | Confidence | Importance | Run after |
|---|---|---|---|---|
| 1 | Fix `compare.py`'s seed term; drop "tie" from its labels | Very high (~95%) | **High** | — |
| 2 | Start the ledger of adoptions made on a lean | High (~90%) | Medium | — |
| 3 | Women's matches: zero or token stakes until an untouched edge shows | High (~80%) | **High** once betting starts | — |
| 4 | Build the bet-time price like the training input | Fairly high (~75%) | **High** | — |
| 5 | Centre the IOS ratings before the matchup products | Moderate–high (~70%) | Low now, medium later | 1 |
| 6 | Fix Roland Garros 2022–25 first serves, if a per-match recount holds | Moderate (~65%) | Low–medium | — |
| 7 | Keep stage 2 (the speed adjustment) live as a logged lean: no edge credit, a cut-off | Fairly high (~75%) | Medium–high | 2 |
| 8 | Pooled instead of per-surface IOS profile | Low–moderate (~55%) | Low | 1 |
| 9 | The lower-level share as a 59th input (**re-filed 9 Oct: a pool admission, not an adoption**) | Low–moderate (~50%) | Low | 1 |
| 10 | Check the adopted changes together (**since 9 Oct: the first holdback comparison**) | High (~90%) | Medium | 5, 6, 8 (9 re-filed) |
| 11 | The lean review's tests: drop the IOS chain's parts? Keep stage 2 live? (added 9 Oct) | High (~85%) that they are worth running | Medium–high | 1 |
| 12 | Tripwire: the Roland Garros box-score repair at the Slams, on new matches (added 10 Oct, the owner's condition for adopting #6) | High (~90%) that it stays quiet | Low–medium | 6 applied; after the 2027 US Open |

Figures below are mLL per match, + = the change better, unless noted.

## Run order

* **Wave 1, in parallel, now:** #1, #2, #3, #4, and steps 1–2 of #6 (the recount and the reviewers' check). None of them builds a model or uses the GPU.
* **Wave 2, once #1 and #2 are done:** #7. It changes only documents, so it can run alongside the build queue.
* **The build queue, one at a time, once #1 is done:** #8 → #5 → steps 3–4 of #6 (if its recount held) → #9 → #10.
  * **Proposed by the [lean review](../lean_review/README.md) (9 Oct; the owner's call): run #11 before #8.** Its T2 can make #8 and #5 moot. It needs no sandbox, only the card.
  * **Why one at a time:** `run_chain.py` builds every candidate in one sandbox (`C:/Users/zerom/tnr_sb`). It copies the repository at `--setup`, so another candidate's half-made code edits would leak into it. The GPU fits also share one card, with no lock.
  * **Why #8 before #5:** #8 settles whether the products to centre are the pooled or the per-surface ones, so the centring is built only once.
  * **Why #1 before the queue:** every comparison in the queue uses the corrected interval, and no sandbox should copy `score.py` mid-edit.
  * **Why #10 last:** it checks the adopted changes together.
* **Parallel sessions share files** (`CLAUDE.md`, the decisions, this checklist). A session that finds a file changed under it should re-read the file and retry.

---

## [x] 1. Fix `compare.py`'s seed term, and drop "tie" from its labels

**Done 9 Oct 2026:** paired seed term on in `compare.py`, `model_rebuild/compare.py` (and so the backfill study's script) and `training_window/score.py`; left off in the pre-registered serve-speed and centring scorers (item 5 passes `matched_seeds=True`); backfill both tours +0.014 [−0.006, +0.035], men +0.027 [−0.012, +0.066], stage 1 exactly 0 (`data/studies/adoption_framework/seed_fix_check/`); tests pass.

* **Confidence: very high (~95%).**
  * The interval adds both arms' seed noise as if it were independent, so a model compared with itself gets ±0.087 instead of 0.
  * Pairing by seed is the standard estimator when the arms share seed numbers.
  * I'd be wrong only for a caller whose arms don't share seeds, and the prompt leaves those unpaired.
* **Importance: high.**
  * Every small comparison has looked less certain than it is. The backfill went from P(better) 0.63 to 0.92.
  * The framework's arithmetic needs the right standard error.

```text
Task: fix the seed term in the project's paired comparison, and replace compare.py's "tie" label.

Read first: docs/studies/adoption_framework/README.md ("Known problems"), docs/studies/adoption_framework/review_statistics.md (finding 1), and src/eda/adoption_framework/seed_term_check.py with its output in data/studies/adoption_framework/seed_term_check.out.

The problem: paired_stats() in src/eda/serve_speed_tabpfn/score.py (around line 396) adds both arms' seed variances as if independent (v_base + v_arm). Arms that use the same seed numbers share that noise, so the interval is too wide: a model compared with itself gets ±0.087 mLL instead of 0.

Do:
1. Give paired_stats an argument for matched seeds, off by default so other callers keep their behaviour until checked. When on, the seed term is the variance over seeds of (seed_ll_base − seed_ll_arm), ddof 1, divided by the number of seeds; this applies to both the block and the week intervals. Keep returning the old values under new names (e.g. se_unpaired, lo_unpaired, hi_unpaired), so old readings can be reproduced.
2. Turn it on in src/eda/current_best_model/compare.py (both arms use seeds 0–3). Check the other callers (src/eda/model_rebuild/compare.py, src/eda/ios_product_centring/score.py, src/eda/training_window/score.py, src/eda/serve_speed_tabpfn/score.py, src/eda/serve_speed_tabpfn/adaptive/score_adaptive.py, src/eda/serve_speed_tabpfn/latency/score_latency.py). Turn it on only where both arms use the same seed indices, and list which you changed and why.
3. In compare.py, reading() returns "better", "worse" or "unresolved", never "tie". Add p_better (the t distribution's CDF of estimate / se, with blocks − 1 degrees of freedom) to scores.csv and summary.json. Update the docstring and the summary's "unit" text.
4. Tests in test/current_best_model/:
   - identical arms give an estimate of 0 and a zero-width interval;
   - on a toy example, the paired seed term equals var(d)/K;
   - with the argument off, the old interval is reproduced exactly.
5. Verify on real data, writing only to a new folder:
   ./python.sh src/eda/current_best_model/compare.py --candidate reference --speed data/studies/infosys_atp_backfill/speed_columns_augmented.parquet --out data/studies/adoption_framework/seed_fix_check
   Expect, with + = with the backfill better:
   - both tours about +0.014 [−0.006, +0.035];
   - men about +0.027 [−0.012, +0.066];
   - stage 1 exactly 0, with a zero-width interval.
6. Docs:
   - mark the problem fixed, with the date, in the framework's "Known problems" and in the "Open" list of docs/decisions/2026-10-09-adoption-framework.md;
   - remove the "Known problem" bullet from CLAUDE.md's adoption section;
   - don't rewrite numbers already published in other studies.

Done when the tests pass, the real-data check matches and every changed caller is listed. Then tick item 1 in docs/studies/adoption_framework/checklist.md, with a one-line outcome.
```

## [x] 2. Start the ledger of adoptions made on a lean

**Done 9 Oct 2026:** [lean_ledger.md](lean_ledger.md), linked from the framework's § 9 and Files table: 10 leans (the 7 named, stage 2 as item 7's logged lean, plus the walk-forward calibration slopes and the odds fed as an input), none with stakes credit; itemized luck in the close edge ≈ 0.2 for stage 1 against the forecast's 0.35, and ≈ 0.2 per men's match for stage 2 against 0.25; no look at the matches from 29 Jul 2026 on record; every number linked to its source.

* **Confidence: high (~90%).** It is the framework's own instruction, and it needs no fits. I'd be wrong only if it turned into busywork.
* **Importance: medium.**
  * It is how leans get revisited.
  * It is how the claimed edge gets corrected for luck: the 2025–26 reading of the edge (~1.4) is forecast to be inflated by about 0.35.

```text
Task: start the ledger of adoptions made on a lean, as the adoption framework asks (§ 9).

Read first:
- docs/studies/adoption_framework/README.md (§§ 2, 4, 6, 9);
- data/studies/feature_provenance/provenance_58.csv and provenance_stage2.csv, with docs/studies/feature_provenance/README.md;
- the decisions of 6–8 Oct in docs/decisions/.

Write docs/studies/adoption_framework/lean_ledger.md: one row per adopted choice in the current best model whose support at its target is unresolved, or whose support comes from seasons that also chose it. At least: the surface IOS profile; the offset Elo; stage 2 (the speed adjustment) and its 28-day memory; the two-week profile; the short IOS memory; age; the speed backfill.

For each row give:
- the target it was adopted for (price, hour, tour);
- its reading at that target: interval, direction key and P(better); the seasons used, and whether they include 2025–26;
- how it arose (the framework's provenance classes), and the number of variants behind it (K);
- the expected luck to subtract (about s·m_K; 0 for a single declared test);
- whether its gain may count toward the edge used for stakes (default: no, for every lean);
- what would reverse it, and when it is next read (e.g. the first checkpoint of sealed matches).

Then total the expected luck and compare it with the clean-holdout forecast (docs/studies/clean_holdout_rebuild/02_contamination_and_forecast.md: about 0.35 mLL for the current model on 2025–26).

Read no new results: every number comes from the docs. Link the ledger from the framework's § 9 and from its Files table.

Done when every number in the ledger has a source link. Then tick item 2 in docs/studies/adoption_framework/checklist.md.
```

## [ ] 3. Women's matches: zero or token stakes until an untouched edge shows

* **Confidence: high (~80%).**
  * Every women's reading at a venue is unresolved: +0.73 against Pinnacle's close (2020–24); returns of +0.73% at Pinnacle and +1.23% at BetOnline (+ = profit). Men carry the edge.
  * Staking on an unproven edge is the expensive error.
  * I'd be wrong if the women's edge is real at early Polymarket prices. Token stakes keep collecting that evidence.
* **Importance: high once betting starts.** The studies' staking rule (bet any positive expected return) treats women's matches the same as men's.

```text
Task: record that women's matches get zero or token stakes until untouched matches show their edge at the venue, and make the future bet step follow it.

Read first:
- docs/studies/adoption_framework/README.md (§ 6, the stakes lane);
- docs/studies/close_drift/README.md (lines ~28–39: women +0.73 against Pinnacle's close, unresolved);
- docs/studies/tabpfn_thinking58/README.md (lines ~31–45: women's returns at Pinnacle and BetOnline, unresolved);
- docs/studies/bet_timing/README.md;
- docs/decisions/2026-10-08-prediction-run-box-scores.md.

Do:
1. Look for any newer women's reading at a venue (Pinnacle, BetOnline, Polymarket at 24–48 hours) in docs/studies/ written after 8 Oct. Read no new results.
2. Write a decision record, docs/decisions/<today>-women-stakes.md, with this prompt as my words, and add a row to docs/decisions/README.md. It says:
   - women's matches get no stake, or a token stake (the venue's minimum, or at most 10% of what the men's rule would stake), to learn prices, fills and closing-line value;
   - this holds until untouched matches (sealed from 29 Jul 2026, then live) show the women's edge at the venue's bet-time price, after costs;
   - what lifts it: propose a pre-declared reading (primary, venue, hour, minimum number of matches) and mark it as my call;
   - men are unaffected.
3. If any code already chooses or sizes bets, make women's matches default to the token stake there, with a test. If none exists yet, write the rule into the prediction-run docs where the bet step will be built, so it isn't missed.
4. Add one line under "Prediction runs" in CLAUDE.md pointing to the decision.

Done when the decision, its index row and the CLAUDE.md line exist. Then tick item 3 in docs/studies/adoption_framework/checklist.md.
```

## [ ] 4. Build the bet-time price like the training input

* **Confidence: fairly high (~75%).**
  * Feeding a model inputs built differently from its training inputs is a known failure.
  * The bet-timing study found the books' average, the way the training input is built, to be the best price to feed: +0.34 to +0.42.
  * The uncertain part is whether those books' prices can be had at bet time.
* **Importance: high.** It is bigger than any single input change.

```text
Task: make the price fed to the model at bet time match the way its training odds input was built.

Read first:
- docs/studies/bet_timing/README.md: its two follow-ups found the books' average the best input (+0.34 to +0.42 mLL), and a single book's line about level with the current model;
- docs/research/early-lines/README.md: which early lines can be had;
- the Stage 1 code that builds the training odds input (the books' average close, proportionally de-vigged); find it from docs/pipeline.md and the model frame's builder;
- src/eda/prediction_run/.

Do:
1. Write down exactly how the training input is built: which books, the de-vig, the averaging, and what happens when books are missing. Give file and line references.
2. List which of those books' prices can be collected at bet time: at which hours, for which tours and levels, and from where (the 8 Oct scraping approval covers public pages). Measure availability on recent matches. Read no results.
3. Build a function the prediction run calls to form the bet-time input the same way from the prices available at that moment, with a fallback order when books are missing. Prove it is the same construction: fed each past match's closing prices, it must reproduce the training input exactly.
4. Report the expected accuracy for each availability case, from the bet-timing study's cells, and what is missing to reach the best case.

Done when the reproduction test passes and the availability table exists. Then tick item 4 in docs/studies/adoption_framework/checklist.md.
```

## [ ] 5. Centre the IOS ratings before the 7 matchup products

**Note (9 Oct 2026): item 8 concluded "stay per surface", with no switch** ([lean review](../lean_review/README.md#results-9-oct-2026), T3). So centre the **per-surface** products, as the model has them now. Item 8 being ticked does not mean pooled.

* **Confidence: moderate–high (~70%).**
  * It fixes a known drift: new ITF box scores widened the products in 2025–26 only (finding #6).
  * It protects against the next change in data coverage.
  * The readings show no harm, −0.05 [−0.21, +0.11] (+ = centred better), but they lean a hair worse. I'd be wrong if the paired re-read shows a real cost.
* **Importance: low now, medium later.** The model barely notices today. The drift grows as lower-level data arrives.

```text
Task: adopt centring of the IOS ratings before the 7 matchup products, unless a corrected re-read shows clear harm.

Read first:
- docs/studies/ios_product_centring/README.md, especially "If the owner adopts it";
- docs/studies/adoption_framework/README.md (§ 2: a fix of a known artifact is adopted on its mechanism, and the outcome test is a harm check);
- finding #6 in docs/studies/input_data_audit/README.md.

Before you start, check docs/studies/adoption_framework/checklist.md:
- if item 1 (the seed-term fix) is done, use the paired seed term;
- if item 8 (pooled IOS) is done, centre the pooled products instead of the surface ones.

Do:
1. Re-read the study's 2022–2024 comparison with the paired seed term, from its stored fits (seasons ≤ 2024 only). Pre-declared harm rule: stop and report if centred is worse by more than 0.1 mLL with the whole 95% interval below 0.
2. Otherwise implement it as the study describes: the reference level in the IOS build, and products formed from centred ratings.
   - Rebuild the template as a candidate: run_chain.py --setup --candidate, the lanes, then --collect, with its own --out under data/studies/current_best_model/.
   - Fit seeds 0–3: ./python_tabpfn_local.sh src/eda/model_rebuild/fits.py.
   - Run compare.py against the reference.
3. Read the input part first: the 7 products should no longer be flagged "uneven", and nothing else should move.
4. If the input check is clean and the harm rule is not met, record the adoption as an amendment to docs/decisions/2026-10-08-current-best-model.md (this prompt is my decision), and update CLAUDE.md's model section if it names the products.

Done when the comparison, the input check and the amendment exist. Then tick item 5 in docs/studies/adoption_framework/checklist.md.
```

## [x] 6. Fix Roland Garros 2022–25 first serves, if a per-match recount holds

**Done 10 Oct 2026: no harm, so the candidate is adopted under the declared rule; the swap waits for a coordinated Stage 0 rebuild.** Steps 1–2 on 9 Oct; steps 3–4 on 9–10 Oct.
* **Officially adopted by the owner, 10 Oct 2026:** "Official decision: adopt, with the tripwire on the Slam number."
  * The tripwire is item 12.
  * The application waits until the level-layer work, running in another session, reports done. Its replay check builds Stage 0 from the decided tables ([decision](../../decisions/2026-10-09-roland-garros-box-scores.md), "Adopted by the owner").
* **The outcome** (report § 10.3, steps 11–13; [decision](../../decisions/2026-10-09-roland-garros-box-scores.md), "The harm check"). `compare.py`, both stages, both tours, 2020–2024; + = the candidate better.
  * −0.026 [−0.076, +0.023] mLL per match, unresolved, P(better) 0.145. Men −0.023, women −0.030, both unresolved.
  * The rule's harm (worse than −0.1, with the whole interval below 0) is not met.
  * The comparison resolves ±0.049 (`adoption_read.py --kind repair`: "adopt, pending the input check"). The seven input flags are read against the dose: they are the fix's own (step 9 of § 10.3).
* **Not yet applied** (report § 10.4).
  * The two decided tables take the candidate's (`adopt.py --check`, then `--apply`) in the next coordinated run of `rebuild_stage0.py`, after the lower-level-evidence study's arm builds. That study's gates fail on any main-tour Stage 0 change.
  * Until then, Stage 0 and the model are unchanged.
* **The recount validates.** RG's own statistics (rolandgarros.com) and point-by-point (Infosys MatchBeats) were collected for every edition of 2019–2025. They recount exactly wherever a point file is complete, and in 2019–2021 they equal Sackmann's rows on every count. The Paris Olympics have their own official results files.
* **Three independent reviewers confirmed 1,447 of the 1,718 proposed sides,** on 933 Sackmann rows: first serves in and points won on each serve, from the official record.
* **Confirmed corrections:** `data/studies/rg_first_serve_recount/confirmed/confirmed_corrections.csv`.
* **For step 3, the Stage 0 corrections folder:** `data/studies/rg_first_serve_recount/confirmed/candidate_corrections/` (the decided tables plus these rows; `stage0_build.py --corrections-dir`).
* **Report, and how to run steps 3–4:** [rg_first_serve_recount](../rg_first_serve_recount/README.md) § 7.
* **Follow-ups, 9 Oct 2026** (owner: "Do all of these that you think is a good idea, review it first, then execute if you do"; report § 8). A second three-reviewer round confirmed:
  * RG's own whole box score, under the Slam rule of 6 Oct, for 1,304 matches: 953 of 2022–2025, and all 351 of 2026;
  * the **four RG 2021 exchanged boxes**.
* **Decided by the owner, 9 Oct 2026** ("Execute and fix", on Claude's recommendations; [decision](../../decisions/2026-10-09-roland-garros-box-scores.md)):
  * **RG's own record is the box-score source for Roland Garros 2022–2026.** With the rule extended, all three reviewers confirm **all 1,541 proposed matches**.
  * **The swapped service games at the Australian Open and Roland Garros are exchanged back** wherever the Slam's point record proves who served first. All three reviewers confirmed **809 of 810**: AO 2019–2026 and RG 2015–2021 (report § 9).
  * **The remaining service-game errors are set from the score** (the owner, the same evening). All three reviewers confirmed **558**: 460 blanks filled and 98 wrong counts (report § 10.1).
  * **Adoption rule for steps 3–4** (declared before any reading): adopt the candidate unless `compare.py` (both stages, both tours, seasons ≤ 2024) reads it worse than the frozen reference by more than 0.1 mLL with the whole 95% interval below 0, or an input is flagged "uneven". The 2025–2026 part is adopted with it on the data evidence. If the rule stops it, report what drove the reading.
* **For step 3, the candidate:** `data/studies/rg_first_serve_recount/followup/confirmed/candidate/`. It holds:
  * RG's box for the 1,541 matches;
  * step 2's split for 58 others;
  * the 4 exchanges;
  * the 809 service-game swaps and the 558 service-game sets.

  It needs both `--box-overrides` and `--corrections-dir` (report § 7). Its dry run is clean: 4,664 rows change, none outside the tables.
  * **Steps 3–4 started 9 Oct 2026, evening** (the owner: "Execute these 3 fixes"). The build is in `C:/Users/zerom/tnr_sb`, recorded in `data/studies/current_best_model/2026-10-09_rg_box_scores/`; report § 10.3.
  * **Input check, 10 Oct 2026 (read before any fit):** 41 of 58 inputs move, all built from box scores. Seven hold inputs are flagged "uneven", in WTA 2013–2014 only.
    * Their dose explains them: the candidate's RG 2013–2014 sets are the WTA's first service-game counts in those seasons, and nothing moves before RG 2013 (report § 10.3, step 9; `input_dose.py`).
    * Under the adoption-by-kind decision (point 4), a repair's flag is harm only when its dose does not explain it.
  * **Built on the reference's recipe, not today's template:** 58 inputs, the books' average, the old indoor input (report § 10.3, step 10).
    * The reading is this repair's bug check, against the frozen reference.
    * A comparison across the Pinnacle-first odds change resolves only about ±0.3 mLL (errata E1), too wide for a 0.1 tolerance.
    * The decided changes are read together by item 10.
  * The folder above is the narrower split-only alternative, now superseded.
  * Build the candidate on the template as it stands at build time. Item 8 kept the per-surface profile, so it changed nothing; check items 5 and 11 before building. *(Departed from, 10 Oct: built on the reference's recipe, for the reason above.)*

* **Confidence: moderate (~65%).**
  * If a per-match recount validates, fixing the data is right on the evidence alone.
  * The uncertain part is whether the point data supports a clean recount. Roland Garros's own 2025 statistics count differently even where nothing is wrong.
* **Importance: low–medium.** It affects the serve statistics of Roland Garros matches, and the players' recent form after the event.

```text
Task: find out whether the first-serve counts of Roland Garros 2022–2025 (and the Paris Olympics 2024) can now be corrected match by match. If so, put the fix through the usual review.

Read first:
- docs/studies/input_data_audit/README.md: the finding that second serves were booked as first;
- docs/decisions/2026-10-08-corrupt-data-fixes.md: F5 and F6 were rejected because RG 2025's own statistics count differently, and because for 2022–24 "no per-match record is held";
- docs/decisions/2026-10-08-scraping-approved.md: every RG edition's own files may now be collected and decrypted;
- docs/studies/ao_rg_points/README.md: the Court Vision (2019–24) and SofaScore point data already held;
- docs/studies/adoption_framework/README.md (§ 2: a data fix is decided on data evidence).

Do:
1. Feasibility, reading no results: can first serves in, and total first serves, be recounted per match from the point data (Court Vision, SofaScore, RG's Infosys files)? Validate the recount where the truth is known: the same sources at other Slams against their official box scores, and RG's own per-edition totals.
2. If a recount validates, write the proposed per-match corrections. Have three independent reviewers (subagents) check them, as on 8 Oct, and keep only what all three confirm. Save the confirmed corrections in a new study folder, and write its path under item 6 in this checklist, so steps 3–4 can run in a later session.
3. A changed past match is a candidate under the frozen-reference rule. Build it with run_chain.py --setup --candidate and its own --out, and compare it with compare.py (seasons ≤ 2024). The outcome reading is only a harm check.
4. Report the result for my acceptance. If the recount does not validate, say why and stop.

Then tick item 6 in docs/studies/adoption_framework/checklist.md, with the outcome.
```

## [ ] 7. Keep stage 2 (the speed adjustment) live, as a logged lean

*This is the softer version the owner chose on 9 Oct 2026. It replaces "move it into shadow".*

**Note (9 Oct 2026, the [lean review](../lean_review/README.md) § 1): proposals for this item, the owner's call.**
* **Keep stage 2 as a logged lean** (both debaters, 55–60%), with three changes:
  * (a) a coefficient that allows for season-to-season disagreement: b ≈ 0.030 for 2027 instead of 0.0444;
  * (b) Challenger speeds kept out of `spd_L`;
  * (c) the first checkpoint at ≥ 2,000 men's matches, with only the alarms before that.
* **Two checks first:** T0 (a speed replay) and T1 (the Pinnacle-first base absorbs at most half of the speed information); T1 is in item 11.
* **The read moves to the new live input:** the model is now fed Pinnacle's current line.

* **Confidence: fairly high (~75%).**
  * It keeps whatever stage 2 is really worth, and removes the expensive error: sizing stakes on a gain that may be luck.
  * **Its support comes from seasons that also chose it:** men 2024–26, +0.41 [+0.04, +0.78]. Selection could explain up to 0.3 of that gain.
  * **On 2020–24 it leans worse:** −0.26 [−0.60, +0.07], P(better) 0.06. So it shouldn't earn edge credit yet.
  * **I'd be wrong if it loses a season before the cut-off catches it.** The backfill study puts the chance of a losing season at about one in three.
* **Importance: medium–high.** It is half of "the current best model". The cut-off bounds what it can cost, and keeping its gain out of the edge estimate keeps stakes honest.

```text
Task: keep stage 2 (the walk-forward serve-speed adjustment) in the betting forecast, but as a logged lean. Claim none of its backtest gain when sizing stakes or deciding whether to bet, set a cut-off for dropping it, and pre-declare when it is next read.

Why; read these first:
- docs/studies/adoption_framework/README.md (§§ 2–4, 6, 9);
- docs/decisions/2026-10-07-speed-nudge.md: its support is men 2024–26, +0.41 [+0.04, +0.78] mLL, a pre-registered secondary;
- data/studies/adoption_framework/seed_term_check.out: stage 2 against stage 1, men 2020–24, −0.26 [−0.60, +0.07] (+ = the adjustment helps);
- docs/studies/infosys_atp_backfill/README.md § 5: the seasons disagree. Next season's expected gain is about +0.2 to +0.3 per men's match, with roughly a one-in-three chance of a losing season. From 2019–24 evidence alone: +0.10, with a 40% chance of a loss;
- docs/studies/feature_provenance/README.md: selection could explain up to 0.3 of its gain.

Do:
1. Amend docs/decisions/2026-10-07-speed-nudge.md and docs/decisions/2026-10-08-current-best-model.md (this prompt is my decision):
   - stage 2 stays in the betting forecast, unchanged;
   - it is a logged lean: none of its backtest gain counts toward the edge estimate that sets stake sizes or decides whether to bet. That estimate comes from untouched matches;
   - the daily speed collector keeps running.
2. Pre-declare, before any sealed result is read:
   - the read: the paired gain of both stages over stage 1, for men, at the venue's bet-time price, on sealed matches with speeds (from 29 Jul 2026). Propose the first checkpoint, with enough matches for a useful interval;
   - the cut-off: stage 2 leaves the betting forecast if that read lands at P(better) ≤ 0.2. It also leaves earlier, as an alarm, if a season's reading on those matches is clearly worse: for example below −1.0 mLL with P(better) ≤ 0.1, the size of 2023's −1.26;
   - full adoption, with edge credit: P(better) ≥ 0.8, with the shrunk gain above the feed's cost;
   - propose the exact numbers and mark them as my call.
3. Add its row to the lean ledger (docs/studies/adoption_framework/lean_ledger.md). If that ledger doesn't exist yet, note under item 2 in this checklist that it must include stage 2.
4. Add one line to CLAUDE.md's "The current best model" section: stage 2 is a logged lean, linking the amendment.
5. If staking code exists, make sure its overall edge estimate (the Kelly fraction, the go/no-go) excludes stage 2's backtest gain, with a test. If none exists, write the rule where the bet step will be built.

Done when both amendments, the pre-declared read and cut-off, and the CLAUDE.md line exist. Then tick item 7 in docs/studies/adoption_framework/checklist.md.
```

## [x] 8. Pooled instead of per-surface IOS profile

**Done 9 Oct 2026 by the lean review's T3, at the owner's word: stay per surface, no switch** ([results](../lean_review/README.md#results-9-oct-2026)).
* The setting: the Pinnacle-first base, without `ios_points_short` (T2's proposal); 2020–24; + = per surface better.
* Per surface against pooled: +0.055 [−0.054, +0.163] at Pinnacle's opening line, P(better) 0.84; +0.045 [−0.058, +0.149] at the close, P 0.81.
* The amended rule keeps per surface (B·est 0.025 > 0.01). This prompt's own rule agrees: at the close, pooled is worse with P(better) 0.19 ≤ 0.2.
* Nothing to amend.

**Note (9 Oct 2026, the [lean review](../lean_review/README.md) § 2): proposals for this item, the owner's call.**
* **Run it after item 11's T2.** If T2 drops the long-memory profile and the owner accepts, this item is moot.
* **Otherwise this item becomes the review's T3:**
  * primary at Pinnacle's opening line, 2020–24, the close as the secondary;
  * switch to pooled on both tours unless the per-surface build clears est > +0.024 (B·est > 0.01 at τ 0.05);
  * split by tour only if one tour clears and the other is worse with P(better) ≤ 0.2;
  * keep this prompt's veto (pooled worse at the close by more than 0.1).

* **Confidence: low–moderate (~55%).**
  * It was kept for early bets, yet at the 24-hour price it reads −0.02 [−0.42, +0.38] on its own.
  * It adds nothing at any price once offset Elo is in, and ties go to the simpler member.
  * That interval is wide, though, so the case is mostly about simplicity.
* **Importance: low.** A simpler build, with the same forecasts.

```text
Task: test returning the model's 21 IOS profile inputs from the per-surface build to the pooled one, and switch unless pooled is clearly worse.

Read first:
- docs/decisions/2026-10-06-surface-ios-profile.md: it was kept for early bets;
- docs/studies/surface_rating_race/README.md § 5 (lines ~199–222): once offset Elo is in, the surface profile adds nothing; at the 24-hour price it reads −0.02 [−0.42, +0.38] on its own (+ = surface better);
- docs/studies/adoption_framework/README.md: ties go to the simpler member.

Before you start, check docs/studies/adoption_framework/checklist.md:
- if item 1 (the seed-term fix) is done, comparisons use the paired seed term;
- if item 5 (centring) is done, carry the centring over to the pooled products.

Do:
1. Find how the pooled profile was built before 6 Oct (the leak-proof refit's inputs), and add an option to the template chain that builds it in place of the surface one.
2. Build the candidate (run_chain.py --setup --candidate, with its own --out), fit seeds 0–3, and run compare.py against the reference on seasons ≤ 2024. Read no 2025–26 results, so take no new 24-hour reading.
3. Pre-declared reading:
   - switch to pooled unless it is worse by more than 0.1 mLL, or worse with P(better) ≤ 0.2;
   - if it is, keep the surface build and report.
4. If you switch:
   - amend docs/decisions/2026-10-06-surface-ios-profile.md and docs/decisions/2026-10-08-current-best-model.md (this prompt is my decision);
   - keep the surface IOS build for forecasting individual statistics;
   - update CLAUDE.md's model section.

Then tick item 8 in docs/studies/adoption_framework/checklist.md, with the outcome.
```

## [ ] 9. The lower-level share as a 59th input

**Re-filed on 9 Oct 2026 by the owner's decision on [adoption by kind of change](../../decisions/2026-10-09-adoption-by-change-class.md):** a new feature is no longer adopted on its own reading.
* **U-330 is admitted to the pool as a lead** ([feature universe](../feature_universe/README.md) § 9). Its readings used 2013–2024 results.
* **A selection round decides** whether it enters (framework § 11). The prompt below is kept for the record and is not to be run as an adoption test.
* Its 2025–26 look (step 2) is better spent in a selection round's single look.

* **Confidence: low–moderate (~50%).**
  * The mispricing is real: the close under-rates players arriving from Challengers and qualifying. It was found on 2020–24 (+0.18 [+0.09, +0.27]) and repeated on 2013–19 (+0.09 [+0.02, +0.16]); + = the price under-rates them.
  * As an input it is worth about 0.1 at most, and the verdict turns on the prior.
* **Importance: low.**

```text
Task: decide whether the lower-level share (U-330 in the feature universe) enters the model as a 59th input.

Read first:
- docs/studies/event_levels/README.md § 8 (lines ~277–306):
  - the close under-rates players arriving from lower levels: β +0.18 [+0.09, +0.27] on 2020–24, repeated on 2013–19 at +0.09 [+0.02, +0.16];
  - as a 59th input (C1) it read +0.06 [−0.10, +0.23] mLL (+ = with the share better);
- docs/studies/feature_universe/README.md (the U-330 columns);
- docs/studies/adoption_framework/README.md (§§ 2, 4).

Before you start: if item 1 (the seed-term fix) is done, use the paired seed term.

Do:
1. Re-read C1 on 2020–24 (seasons ≤ 2024) with the paired seed term. Reuse the study's stored fits (data/studies/event_levels/, experiment C) if they hold per-seed forecasts.
2. Take one logged look at 2025–26, declared before reading: C1 against the current model, both stages, both tours, every 2025–26 match the frame holds. This feature has never been read there. Log the look in the study's report, the way earlier look ledgers do (e.g. docs/studies/serve_speed_tabpfn/look_ledger.md). [Delete this step to keep 2025–26 untouched.]
3. Apply the framework with τ = 0.05 (a mispricing repeated outside the seasons that found it) and c = 0.01 (one more input). Pre-declared rule:
   - adopt it on a logged lean if B·est > c on 2020–24, and the 2025–26 look does not lean worse (P(better) ≥ 0.3);
   - otherwise keep it as a candidate and report.
4. If it is adopted:
   - build it as a template candidate (run_chain.py --setup --candidate, with its own --out) and confirm the input check;
   - amend docs/decisions/2026-10-08-current-best-model.md (this prompt is my decision);
   - add a row to the lean ledger, if item 2 is done.

Then tick item 9 in docs/studies/adoption_framework/checklist.md, with the outcome.
```

## [ ] 10. Check the adopted changes together

**Since 9 Oct 2026, this is the first holdback comparison** ([decision](../../decisions/2026-10-09-adoption-by-change-class.md), point 5; framework § 10).
* **The control** (corrected the same night, [errata](../../decisions/2026-10-09-adoption-by-change-class-errata.md) E1): the latest stored instance carrying every structural change since the frozen reference.
  * Today that is the Pinnacle-first instance of 9 Oct (`data/studies/current_best_model/pinnacle_first_2026-10-09/`), not the reference.
  * Across the odds change a comparison resolves only about ±0.3.
* **When:** after each batch of adoptions, and at least monthly while changes are adopted.
* **No ready tool yet.**
  * `compare.py` compares only against the frozen reference.
  * Score the template against the control with a paired scorer on `compare.py`'s recipe: adapt `src/eda/indoor_fill/score.py`, which scored a candidate against another instance (the lean review's arm A2).
* The step "if fewer than two were adopted, stop" no longer applies: a single batch is read too.
* A holdback that shows harm (worse by more than 0.10 mLL with the whole interval below 0) is bisected, adoption by adoption.
* Read it with `src/eda/current_best_model/adoption_read.py --kind holdback`: it keeps the adopted changes unless the harm rule fails, and otherwise says to bisect them. Report its estimate as the adopted changes' cumulative effect.

* **Confidence: high (~90%).**
  * Effects don't always add up. Once offset Elo was in, the surface profile added nothing.
  * Each item above is compared with the reference on its own.
* **Importance: medium.** It is the model you would actually use.

```text
Task: build the current best model's template once, with every change this checklist adopted, and compare it with the holdback's control: the latest stored instance carrying every structural change since the frozen reference (today the Pinnacle-first instance of 9 Oct; see the note above the prompt). [Amended 9 Oct 2026; it first said "the frozen reference".]

Read first: docs/studies/adoption_framework/checklist.md (which items are ticked, and their outcomes), the amendments since 9 Oct in docs/decisions/2026-10-08-current-best-model.md, and docs/studies/adoption_framework/README.md.

Do:
1. List the adopted changes that alter the model's inputs or training data (items 5, 6, 8 and 9 if adopted), with each one's decision amendment. Read the batch even if only one change was adopted. [Amended 9 Oct 2026; it first said "If fewer than two were adopted, say so and stop."]
2. Build the template with all of them:
   - first check that the sandbox (C:/Users/zerom/tnr_sb) doesn't exist and that no other job is using the GPU;
   - build with run_chain.py --setup --candidate and its own --out under data/studies/current_best_model/;
   - fit seeds 0–3;
   - score it against the control on compare.py's recipe (seasons ≤ 2024), with a paired scorer adapted from src/eda/indoor_fill/score.py, since compare.py compares only against the frozen reference; also run compare.py against the reference, as the structural yardstick;
   - read the control comparison with ./python.sh src/eda/current_best_model/adoption_read.py --kind holdback;
   - run --cleanup on the sandbox once the build is collected.
3. Compare the combined reading with the single-change readings. Flag any change whose gain disappears in combination.
4. Report the combined reading (+ = the combined template better), the input check, and any change worth revisiting. Don't amend decisions: that is my call.

Then tick item 10 in docs/studies/adoption_framework/checklist.md.
```

## [ ] 11. The lean review's tests: drop the IOS chain's parts? Keep stage 2 live?

**Partly done 9 Oct 2026** (T2 and T3, at the owner's word; [results](../lean_review/README.md#results-9-oct-2026)). 2020–24, on the Pinnacle-first base; + = without the dropped part better.
* **The long-memory profile stays,** per surface (item 8 ticked). Dropping it reads −0.18 at the opening line and −0.29 [−0.63, +0.04] at the close, P(better) 0.04; the rule's veto applies.
* **`ios_points_short` was dropped by the owner on 9 Oct** ([amendment](../../decisions/2026-10-08-current-best-model.md)), after reading −0.03 at the opening line (P 0.25) and −0.00 at the close. The model has 57 inputs; `template_inputs.py --apply` writes the list after the chain.
* **Still to run: T0 and T1, stage 2's checks.**

*Added on 9 Oct 2026 by the [lean review](../lean_review/README.md): a debate, at the owner's request, on three leans the [ledger](lean_ledger.md) flags.*

* **Confidence: high (~85%) that the tests are worth running.** The plan was fixed before any of it runs.
  * The outcomes are open: per surface → pooled 65–70%; removing `ios_points_short` 55–60%; stage 2 kept live 55–60%.
  * I'd be wrong if the opening-line reads are too noisy to move any decision. Even then, the close readings serve as harm checks.
* **Importance: medium–high.** If the long-memory profile and `ios_points_short` both go, the IOS chain leaves the model, and with it:
  * items 5 and 8;
  * the exposure to finding #6;
  * one of the two main entry points of the ITF data due about 31 Oct.

```text
Task: run the lean review's pre-declared tests T2 and T1 (and T0 unless item 7 has done it), and report proposals.

Read first:
- docs/studies/lean_review/README.md, "The test plan": it was fixed on 9 Oct 2026 before any of it ran. Follow it exactly, amendments A–C included;
- its debate/ rounds 2 and 3;
- docs/decisions/2026-10-09-pinnacle-first-odds-input.md;
- src/eda/bet_timing/fits_cons_trained.py (the runner to adapt) and src/eda/current_best_model/compare.py (walk_forward, forecasts, the seed-paired interval).

Before you start: check that no other job is using the GPU, and that the Pinnacle-first instance's fits for 2019–2024, seeds 0–3, exist (data/studies/current_best_model/pinnacle_first_2026-10-09/fits/).

Do:
1. T2, the IOS 2×2, on the Pinnacle-first instance. Column drops only; no chain rebuild.
   - Arms: A0 (58 inputs), A1 without the 21-input long-memory profile, A2 without ios_points_short, A3 without both.
   - Seeds 0–3, seasons 2019–2024 fitted.
   - Each fit predicts the close-fed rows first. Then, in a separate predict call on the same fitted model, it predicts the rows fed Pinnacle's margin-free opening line: p_ot20o in data/studies/odds_sources/sources.parquet, complete cases, no 2021 US Open, lines stamped after the listed start left out.
   - Reproduction check first: A0's close-fed predictions must equal the instance's existing fits to machine precision. If they do not, stop and report.
   - Score with a paired scorer: new code in src/eda/lean_review/, tests in test/lean_review/. Both stages with the decided stage-2 recipe; walk-forward calibration per yardstick; 2020–24; debut seasons out; seed term paired.
   - Apply the plan's rule as written: B·est + c > 0 at the opening line, the veto at the close, and the order rule. Report the realisation slope at the opening line.
2. T1, scoring only: d = β_pf − β_ref, men 2019–24, with a block bootstrap. Add the secondaries as written.
3. T0, unless item 7 has done it: the speed replay, with the Challenger filter on both sides.
4. Write the results:
   - a "Results" section in docs/studies/lean_review/README.md, with outputs in data/studies/lean_review/;
   - each reading under the ledger's rows 1, 3 and 6 (docs/studies/adoption_framework/lean_ledger.md).
   Read no 2025–26 result.

Don't amend decisions. Every outcome is a proposal; accepting it is my call. Then tick item 11 in docs/studies/adoption_framework/checklist.md, with a one-line outcome.
```

## [ ] 12. Tripwire: the Roland Garros box-score repair at the Slams, on new matches

**Added 10 Oct 2026, the owner's condition for adopting item 6:** "Official decision: adopt, with the tripwire on the Slam number."
* **Why.** At the harm check the repair read worse at the Slams: −0.065 [−0.162, +0.033] mLL per match, P(better) 0.09, unresolved (+ = the repair better).
  * Five end-to-end checks found it applied as confirmed (report § 10.3, steps 13–14).
  * The tripwire reads it again on Slam matches it has never been read on.
* **The rule, fixed before any of these matches was played:** [decision](../../decisions/2026-10-09-roland-garros-box-scores.md), "Adopted by the owner, 10 October 2026, with a tripwire".
* **When:** after the 2027 US Open, so all four 2027 Slams are in, then after each later Slam. It needs item 6 applied first (`data/studies/rg_first_serve_recount/adoption/<stamp>/adoption.json`).
* **What it can see:** about ±0.2–0.3 mLL at the Slams after the first year. It catches a large harm; today's lean would take years to resolve.

```text
Task: run the tripwire on the Roland Garros box-score repair (checklist item 12), on Slam matches it has never been read on.

Read first:
- docs/decisions/2026-10-09-roland-garros-box-scores.md, section "Adopted by the owner, 10 October 2026, with a tripwire": the rule was fixed before any of these matches was played. Follow it exactly.
- docs/studies/rg_first_serve_recount/README.md, § 10.3 (the harm check) and § 10.4 (the adoption).

Before you start: check that the repair has been applied (an adoption.json under data/studies/rg_first_serve_recount/adoption/), and that no other job is using the GPU or rebuilding the shared tables.

Do:
1. Build the template as it stands twice, with the same code, each in its own sandbox (run_chain.py --setup --candidate, its own --out, MODEL_REBUILD_SANDBOX set): once on the decided tables (with the repair), once with the two pre-adoption tables (adopt.py's kept copies under adoption/<stamp>/replaced/) put into that sandbox's Stage 0 build.
2. Fit season 2027 (and later seasons, if their Slams are in) on 2013 .. Y-1 for both builds: seeds 0-3, the template's fit settings, stage 2 as decided.
3. Score both stages, both tours, on the four Slams' matches played from the 2027 Australian Open on (compare.py's "Slams" level), paired by seed, with the week-block interval. Use a paired scorer between the two builds (compare.py's functions, or the pairing in src/eda/lower_level_evidence/system_pairs.py). Report all new matches, both tours, beside the Slam figure. Read no 2025-2026 result.
4. Apply the trigger as written. If the repair reads worse at the Slams with the whole 95% interval below 0, recommend reverting (adopt.py --restore <stamp>, then a coordinated rebuild_stage0.py) and look for the cause. Otherwise, keep it.
5. Record the reading under the tripwire in the decision record, and in data/studies/adoption_framework/class_record.csv.

Recommend; reverting is my call. Then tick item 12 with a one-line outcome, or leave it open with the date of the next reading.
```

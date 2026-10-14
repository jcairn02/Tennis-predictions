# The daily prediction script, phase 1

10–11 October 2026 · For the owner · Process log: [process_log.md](process_log.md) (part 2: the speed-ups) · The plan
it builds: [prediction_pipeline/PLAN.md](../prediction_pipeline/PLAN.md) § 7 · **Not a decision:** nothing here changes
the current best model; the script reproduces it.

## Stage 0's builders and a name fix (11 Oct 2026, afternoon)

You approved editing `stage0_build.py` and `feature_alpha_audit/repair_data.py` for speed, "with proof that the new
Stage 0 is byte-identical to today's", and asked me to delete the leftover folder (done: the caches are now 54 GB).

* **Stage 0: 129–141 s → 75–84 s, and its output is byte-identical.**
  * **What changed:** where the two builders loop over text columns in Python, each column is now read once as a
    plain array. A helper converts only the column types checked to give the very same values (text, object, bool,
    whole numbers) and loops over any other type as before. Three Python group-bys in `repair_data.py` became single
    loops that build the same sets. Nothing else changed; neither file is one of the level layer's hooked builders.
  * **The proof:** Stage 0 built in a sandbox (Tennis My Life held at the freeze). Today's code was built twice, to
    show the build is deterministic (byte-identical). Then the new code, in both ways the pipeline calls it (the
    repository's default build, and the daily pipeline's build with live rows):
    * **All five data files are byte-identical to today's.**
    * The summary is byte-identical apart from its clock line, with no other field differing; its record of every
      input file's hash shows both builds read the same inputs.
  * **Also checked:**
    * The 136 tests of the six test files that use these builders pass, before and after.
    * The replay through `run_day` gives all 57 inputs bit for bit, and every seed's fit identical.
    * Records: `data/studies/daily_prediction/stage0_speed/` (each build's files, hashes and comparisons; the
      originals as `original/*.orig`).
* **A day is now about 5.5 minutes with a warm disk cache.** The replay took 392 s with a cold work-tree copy:
  tables 129 s, of which Stage 0 is 84.
* **A bug found by the master-notebook session (`tennis-predictions-fc`), now fixed: `predictions.csv` could put a
  player's name beside the other player's price and forecast.**
  * **Cause:** whenever the matchups CSV listed the players opposite to Stage 0's side A, the price was turned to
    side A but the CSV's names were not.
  * **Exposure:** live runs only (replays carry no names), and none has been made yet.
  * **Fix:** the names now come from Stage 0's own player rows by side, and a run is refused if they disagree.
  * **Tests:** `test_side_names_follow_stage0_sides`, and `test_prediction_names_are_stage0_sides`, which checks each
    name against the template's Stage 0.
* **A second bug from the same session's review, also fixed: a run refused because another run's work tree existed
  deleted that tree.** A run now deletes only a work tree whose marker names it. The new test failed on the old code
  (checked on a scratch copy) and passes on the new.
* **Added for your master notebook (agreed with that session):**
  * `DP_INSTANCE`: the name of an instance's folder, to run the daily path on a newly built instance. Set it together
    with `DP_BASE_TREE` (that instance's build tree), and make a checkpoint on it first.
  * An optional `quoted_at` column in the matchups CSV: the quote's own time, written to `predictions.csv` as
    `price_quoted_at`.
* **A limit that session found (not changed: it is prediction_run's linking, part of § 7 item 1's alias table):** a
  live run stops on a player name that matches two Stage 0 ids. Fourteen current players are affected (12 ATP, 2 WTA;
  Jakub Mensik, for example, has `atp:210150` and an old duplicate `atp:210084`). The notebook's linker leaves such
  matches out for now.
* **Tests:** the full suite, now 15 tests: **15 passed in 56 minutes** (`checks/pytest_part3.txt`). After the last
  changes, every test that touches them ran again on a fresh replay: **11 of 11 pass** (`checks/pytest_part3b.txt`).
  One first failed because of those changes: the fit's self-test made its comparison folder without `run.json`,
  which the fit step now reads. I fixed the self-test, then reran it.

**Decision for you (raised by the same session): which speed feed stage 2 uses.**
* The decision reads: coefficients refitted "on the speed history that matches the live feed: spd_L_B for the weekly
  feed, spd_L_D once the daily collector runs".
* The collector has run every day since 8 Oct, but the pipeline still uses the weekly set.
* **I recommend:** live runs use the daily set (2026's coefficients refitted on `spd_L_D`, applied as the daily
  feed). Replays of days before 8 Oct keep the weekly set.
* This moves live predictions slightly, by design, so it's your call. Shall I make it?

## Speed-ups (11 Oct 2026)

You asked: "see if you can find speed ups with no cost to prediction quality or potential bugs. Saving states etc."

* **A day now takes under 7 minutes instead of 20, and every number is the same, bit for bit.** The timed replay of
  15 Jul 2026: **403 s against 1,190 s**, and 345 s (5.8 minutes) in the test run, where the disk cache was warm. Its
  57 inputs, its 16 seeds' price grids and its prediction file are identical to part 1's.
* **The fit: 811 s → 82 s.** TabPFN's cached mode now gives exactly the decided path's numbers.
  * **The 0.18 gap was a bug in tabpfn 9.1.0.** When the 8 estimators share one cache, memory saving (on, as decided)
    splits them into chunks but hands each chunk the whole cache, and the attention takes estimator 0's rows for
    every estimator.
  * **The fix: one cache per estimator.** At this training size the decided path already runs the estimators one at
    a time, so the cached predictions equal it **bit for bit** (all 16 seeds; caches built fresh and caches read back
    from disk).
  * **Saved state:** each seed's cache is built once per instance and season (41 s) and kept on disk (3.6 GB). A day
    reads it (1.7 s) and predicts (2.9 s). A cache is used only if everything it was built from is unchanged (the
    training rows, seed, settings, library versions, model weights and graphics card); otherwise it is rebuilt.
* **The states step: 162 s → 85 s.** The surface IOS and Stage B's forms now run in processes of their own beside the
  other families. Each runs the same code on the same data.
* **The tables step: 198 s → 157 s.** The history check runs beside the states step; nothing reads it to build an
  input, and its result is recorded where it was.
* **Not done, yours to decide: Stage 0, now the largest step (117 s).** About half of it is pandas reading text
  columns one element at a time, inside `stage0_build.py` and `feature_alpha_audit/repair_data.py`. Fixing that means
  editing two builders, which your rule leaves to you (the daily_update_speed session planned it too). Likely
  saving: about a minute. **(Done that afternoon, at your word: see the section above.)**

**Your list, item by item:**

| Your item (its estimate) | Done? | Why |
|---|---|---|
| Rebuild Stage 0 incrementally (~2 min) | **No** | It is a builder edit, so it needs your approval. The profile also points to a simpler fix: about half of Stage 0's time is the text-column loops above; removing them needs no incremental logic |
| One long-running process with the tables and states in memory, one shared row loader (~1.5–2 min) | **No**; parallel processes instead | Every run rebuilds today's tables, so a long-lived process would still have to re-read them. It would also add stale-state risk. Running the families side by side saved 77 s with neither problem |
| Whole-table work limited to new rows; the families in parallel (~1.5–2 min) | **Parallel: yes** (−77 s). **New rows only: no** | Each restriction would need its own proof of equality, mostly in other studies' code. After the parallel change, the slowest family (the IOS, 75 s) sets the pace, so restricting the other families' loading alone saves about 10 s |
| Fix TabPFN's cached mode (GPU ~16 min → under 1 min) | **Yes**: 13.5 min → 1.4 min | The bug above; bit for bit. Not under a minute, because each seed's 3.6 GB cache is read from disk |

**What it costs:**
* **56 GB of disk** for the caches (16 × 3.6 GB, under the state folder, outside git).
* **About 12 minutes once per instance and season** to build them (a run builds any missing seed by itself).
* A new instance gets new caches; the old instance's stay until deleted.
* **Left on disk:** `data/studies/daily_prediction/state/template_2026-10-10/tabpfn/season2026/seed13.part` (3.6 GB),
  the copy from an attempt Windows refused to rename. I fixed the save and did not delete the folder, per your rule
  on temporary files. Deleting it is safe.

**Checks:** `./python.sh -m pytest test/daily_prediction` gave **13 passed in 53 minutes**
(`data/studies/daily_prediction/checks/pytest_part2.txt`). Part 1's nine checks all pass again, now through the faster
paths: the test replay reproduced the 57 inputs bit for bit, in **345 s** (5.8 minutes, warm disk cache). Part 2's
four:

| Test | Result |
|---|---|
| `test_fit_cache_equals_decided_path`: the replay's fit (from the caches) against the decided path itself (seeds 0–1, with their separate own-price calls), and a cache built from scratch (seed 2) against the replay's cache read from disk | **Pass.** Every array bit for bit (largest difference 0.0); the decided path took 44 s a seed, the cache's build 41 s |
| `test_fit_cache_key_sees_every_change`: a cache is refused if a training value (one last bit), a label, a column, the seed, the versions or the card changes, or if a file is missing | **Pass** |
| `test_history_check_recorded`: the history check, run beside the states step, still reaches `tables.json` | **Pass** |
| `test_states_ran_in_three_processes`: test 2's inputs came through the three processes | **Pass** |
| Development checks: all 16 seeds' cached fits against part 1's decided-path fit; the tree check (1,565 matches) through the three processes | **16 of 16 seeds bit for bit** (13 read from disk, 3 built); **57 of 57 inputs bit for bit** |

## Phase 1 (10 Oct): in short

* **Built:** `src/eda/daily_prediction/`, one command per pipeline step and `run_day`, which chains them
  (`./python.sh src/eda/daily_prediction/dp.py <step> --run <folder>`). Every input family resumes from a saved checkpoint
  instead of rebuilding 873,000 matches of history; a part whose history changed is recomputed in full, and says so.
* **"Phase 1" as I read it:** § 7's items 2 and 3 (the state path and the daily fit with the price grid, stage 2 and
  the prediction file), because those are what your four checks test. Item 1 (the Pinnacle recorder, linking, first
  rounds) is the next build: until then matchups and prices come from a CSV, as `prediction_run` takes them. Say if you
  meant otherwise.
* **Your four checks all pass:** `./python.sh -m pytest test/daily_prediction` gave **9 passed in 1 h 21 min**, building everything from scratch (`data/studies/daily_prediction/checks/pytest_final.txt`):
  1. **Resumed state = full recompute:** every family bit for bit on every row after the checkpoint, **the surface IOS
     included (largest difference 0.0, inside your 1e-6)**.
  2. **The replay through run_day reproduces all 57 inputs** of `template_2026-10-10/model_frame.parquet` **bit for
     bit** on all 23 matches of the round of 16's first day in the week of 13 Jul 2026 (15 Jul).
  3. **A changed past row invalidates its checkpoint:** 22 of 22 cases as required. Through the real steps too: one
     past match moved a day made exactly the 7 parts that read it recompute, and the inputs still equal a from-scratch
     build's.
  4. **Price grid against a direct prediction:** within **0.00050** (mean 0.00022; 16 seeds, 23 matches); the fit's direct
     predictions are within 1e-5 of the template's own stored fits.
* **What a day cost on 10 Oct** (the final run's replay, nothing else running; **since 11 Oct under 7 minutes in all**,
  see the speed-ups above): **about 6 minutes to the inputs** (work tree 9 s, matchups 3 s, tables 3.3 min, states
  2.7 min), then **13.5 minutes of GPU** for 16 seeds, then predictions in under a second. Building a checkpoint takes
  about 11 minutes (weekly, or after a fallback).
* **Found on the way:** the repository's copies of three constants files are older builds' (Stage 3's women's drift
  1e-4 against the template's 5e-5; Stage 4's constants CSV). A plain sandbox copy would have built different inputs,
  so each checkpoint now carries the instance's constants and installs them in the work tree.

## How to run it

```
# a day (matchups and margin-free prices of side A in a CSV, prediction_run's columns)
./python.sh src/eda/daily_prediction/dp.py run_day --run data/studies/daily_prediction/runs/<day> --matchups <csv> [--refresh]
# a replay of a past day (the proof): the first day's round of 16 of the week of 13 Jul 2026
./python.sh src/eda/daily_prediction/dp.py run_day --run <folder> --replay-week 2026-07-13 --replay-round R16 --checkpoint 2026-06-22
./python.sh src/eda/daily_prediction/dp.py replay-compare --run <folder>
# a new price later in the day: read off the stored curve, no refit
./python.sh src/eda/daily_prediction/dp.py reprice --run <folder> --prices <csv of match_id, p_a>
# a checkpoint (every family's state before a day) on a tree's tables
./python.sh src/eda/daily_prediction/dp.py checkpoint --tree <tree> --day <YYYY-MM-DD>
# the tests (slow: they build a checkpoint, a replay and its fit)
./python.sh -m pytest test/daily_prediction -q
```

Settings by environment variable: `DP_INSTANCE` (the instance folder's name, default `template_2026-10-10`) with
`DP_BASE_TREE` (its build tree); `DP_WORK_TREE` (one per run running at the same time); `DP_STATE` (where checkpoints
and TabPFN's caches live). The matchups CSV takes prediction_run's columns (`tour, tourney_id, round, player_a,
player_b, day, p_a`; optional `tourney_name, best_of, start_utc`, and since 11 Oct `quoted_at`). In
`predictions.csv`, `player_a` is Stage 0's side A, and every `_a` figure is that player's, whichever player the CSV
listed first.

The steps, in run_day's order: `refresh` (box scores first: prediction_run's), `matchups`, `prices`, `worktree` (a
fresh sandbox copy, the instance's constants installed), `tables` (Stage 0 with the live rows, the accepted packages,
the level layer resolved, Stage 1's odds, the timeline), `states` (the 57 inputs from the checkpoint, and the gate),
`patterns` (since 13 Oct 2026, while the five-pattern adjustment is on: its live score, from
`src/eda/unpriced_leads/live_members.py` inside the work tree; [decision](../../decisions/2026-10-13-five-pattern-adjustment.md)),
`fit` (16 seeds, every live match at 91 prices and its own), `predict` (stage 2 with the pattern term;
`predictions.csv` keeps `q_a`, the prediction used, and adds `q_a_patterns_off` and `q_a_patterns_on`; `curves.parquet`,
`provenance.json`; a live run also archives to `predictions/<day>/records/`, since 13 Oct beside the master
pipeline's bet-sheet records), then the work tree is deleted. `grade` (after
results) and `reprice` run on their own.

## The checks, in detail

All on the template's own build (its tables in `C:/Users/zerom/tnr_lyr_new`, read only; nothing there was written).

| # | Test | What it compares | Result |
|---|---|---|---|
| 1 | `test_elo_passes_resume_bit_for_bit`, `test_forms_resume_bit_for_bit`, `test_ios_resume_within_tolerance`, `test_stateless_families_equal_the_build` | A checkpoint at 31 Aug 2026 made by the script, then each family resumed from it against the same family recomputed from scratch, on **every** row after the day: the offset, games/points-weighted and Stage 3 passes (1,892 men's and 219 women's matches); Stage B's z (2,848 box rows, 17 pairs) and inputs (1,986 matches); the 14 IOS solves (3,826 men's and 656 women's rows). Stage 4 and the Elo pieces have no state: recomputed for the day's players against the build's stored tables | **Pass.** Everything bit for bit, the IOS too (0.0). IOS resume 2.6–5.2 s per solve against 1–6 min from scratch |
| 2 | `test_replay_reproduces_the_57_inputs` | `run_day` on the morning of 15 Jul 2026 (the round of 16's first day that week: Bastad, Gstaad, Umag, Athens, Iasi), each match a live row with its result removed, the later rounds left out, priced at the instance's own price; then its 57 inputs against the template frame | **Pass.** 57 of 57 inputs, 23 of 23 matches, bit for bit (largest difference 0.0); all 21 state parts resumed from the 22 Jun checkpoint |
| 3 | `test_changed_past_row_invalidates` | Each family's hash on the tables, then with one row changed: a result, a player, an inserted match, serve points, games, a box-score count, a timeline window | **Pass.** 22 of 22: each change before the day moves exactly the hashes of the parts that read it; after the day, none; an ITF box score the layer weights to zero, none |
| 3 | `test_changed_past_row_recomputes_through_the_steps` | A replay's work tree with one April 2026 men's final moved a day in the timeline; the states step from the checkpoint against the states step with every part from scratch | **Pass.** Exactly the 7 men's IOS solves recomputed, the other 14 parts resumed; all 57 inputs equal the from-scratch build's, bit for bit |
| 4 | `test_price_grid_matches_direct_prediction` | The replay's 16-seed price grid read at each match's own price, against the same model's prediction at that price in the same call, and against the template's stored fits of these matches | **Pass.** 0.00050 at most (mean 0.00022) against the same-call prediction; 0.00051 against the template's stored fits, from which this fit's own-price predictions differ by 9.8e-6 at most; the own-price rows predicted alone in a separate call differ by 5.6e-5 at most (the batch's effect) |
| — | `test_slice_hash_sees_every_change` | The hash itself: a last bit, order, a filled missing value, a row added; one NaN pattern; float32 read as float64 | **Pass** |

A smoke test of the live path's own timeline steps (a replay dated as live, not held at the template's timeline) also
ran through `states`: every step ran; the rebuilt timeline differs on older matches (sources restaged after the freeze),
so all 14 IOS parts were rightly recomputed; its 36 inputs outside the joint solves equal the template's, its IOS
inputs differ by up to 0.009, which is what live dating changes.

## What a day costs

The same replay, timed twice: part 1's final pytest run (`runs/pytest_replay_2026-07-13_R16_*/run_day.json`) and
part 2's run with the speed-ups (`runs/replay_2026-07-13_R16_speed/run_day.json`), nothing else of mine running:

| Step | 10 Oct (s) | 11 Oct (s) | Inside it (11 Oct) |
|---|---:|---:|---|
| refresh | not run | not run | a replay holds the dump; prediction_run's 9 Oct live refresh: download 3, Stage 0 on it 145 |
| worktree | 9 | 72 | the sandbox copy: 9 s on a warm disk cache, 51–72 s cold (just after 56 GB of cache files were written and read) |
| matchups | 3 | 3 | |
| prices | 0.0 | 0.0 | |
| tables | 198 | 157 | Stage 0 with the live rows 117, packages 15, check 0.6, level layer 12, Stage 1's odds 6, live prices 0.7. A live run adds links, timeline and the live window: about 75 s (the smoke test) |
| history | (in tables: 48) | 0 | 51 s, run beside the states step |
| states | 162 | 85 | three processes: main (Stage 4's rows 41, the passes and Stage 3 19, the rest 18), forms 65, IOS 75 (cache 63, solves 12) |
| fit | 811 | 82 | 16 seeds × 4.6 s from their caches (read 1.7, predict 2.9; 5.6 GB peak); a seed whose cache must be built: about 46 s |
| predict | 0.6 | 0.8 | (stage 2's coefficients: fitted once per season, about 10 s) |
| cleanup | 6 | 3 | |
| **total** | **1,190** | **403** | **from about 20 minutes to under 7, 1.4 of them on the GPU.** The test run's replay, warm: 345 s (work tree 10, tables 158, states 84, fit 87, cleanup 3) |

A checkpoint takes about 11 minutes (the 14 IOS solves from 2010 are 7 of them, on 7 workers). A state part that falls
back costs its full recompute: an IOS solve 1–6 minutes, the forms about 2, the passes seconds.

## How it works

**The work tree.** Each run builds today's tables in a fresh sandbox copy of the repository (about a minute; the
builders write into their own folders, so they never run in the repository), with the prediction run's licence for
live rows. The checkpoint's copies of the instance's constants files are installed into it first. A replay holds
Tennis My Life's dump at the 8 Oct freeze and the timeline at the template's, as the 10 Oct layer replay did.

**Tables.** `prediction_run`'s own preparation, run unchanged, without the three steps that reach no input (Stage 0's
and the timeline's report-only checks, and `match_timing/rebuild.py`, whose columns the surface IOS replaces).

**States.** Each input family resumes from the checkpoint (the state before a tournament week three weeks back):

| Family (inputs) | What the checkpoint keeps | Daily work |
|---|---|---|
| Elo-type passes (offset Elo 2 + pieces, games Elo, Stage 3's ratings) | each pass's per-player lists and the week's pending updates, per tour (1–2 MB each); Stage 3's outputs before the day (its table is read whole) | the matches since, seconds |
| Surface IOS (21) | each of the 14 solves' running sums, last solution and in-flight rows (1–3 MB each) | the snapshot days since, about 1 s a solve |
| Stage B forms (17) | every past box-score row's z, float64 (85 MB) | the new rows' z and each day's player's form |
| Stage 4 (6) and the Elo pieces' surface counts (4) | nothing: per-player sums | recomputed for the day's players |
| Context (6), odds (1) | nothing | row values; the odds input is log(p/(1−p)) of the price |

A part resumes only if a hash of every array its state read before the checkpoint day (its "slice") is unchanged on
today's tables; otherwise that part is recomputed from scratch and the run says so. The hash covers exactly what the
pass reads: a past result, box score, player, date or inserted match invalidates the parts that read it; a change the
pass never reads (an ITF box score the level layer weights to zero) does not. A live run whose parts fell back leaves a
fresh checkpoint on its own tables for the next day.

**Fit and predict.** For each of seeds 0–15, one TabPFN call holds every live match at 91 log-odds prices
(logit 0.05 to logit 0.95) and at its own price, both orientations (the decided configuration, trained on the instance
frame's 2013 .. Y−1). Since 11 Oct the call reads the seed's training cache from disk (`dp_tabcache.py`; built the
first time, rebuilt when anything it depends on changes; `--fit-cache off` runs the decided path itself, with the same
numbers). The seed mean gives η at every price; stage 2 adds the men's 28-day serve-speed difference with
the season's coefficients (fitted once per season by the decided `walk_forward` on the instance's seeds 0–3, on the
backfill-augmented speed history; for 2026: s_atp 0.9004, s_wta 0.9223, b̃ 0.0369). A later price is a lookup on the
stored curve (`reprice`: at the run's own prices within 0.00045 of its q); a price outside the grid is refused, its
own-price forecast stands. `grade` joins each prediction to its result once Stage 0 holds it (exercised on the replay;
its numbers decide nothing).

## Limits

* **No live day has been run.** Phase 1 has no source of upcoming matches and prices beyond a CSV (§ 7 item 1: the
  Pinnacle recorder, ATP matchups, an alias table, first-round event columns). The live path's own timeline steps
  (links, the live window) ran once, in the live-dated smoke test; the exact replay held the timeline instead.
* **The first live run is expected to recompute most parts in full** (about 10–15 minutes of states instead of 3):
  Tennis My Life revised past rows on 10 Oct (players' ids among them), so no checkpoint made on the 8 Oct tables should
  match today's (inferred, not run). It then leaves a checkpoint on its own tables, and the next day resumes.
* **The in-season fit is not built** (decided but waiting for its calibration guard): season Y's live fit is the annual
  2013 .. Y−1 fit.
* **`grade` is minimal** (log loss against the price used); the monitors are § 7 item 4.
* **Stage 0 is rebuilt in full every day** (about 2 minutes), now the largest step: see the speed-ups above.

## Decisions for the owner

| # | Question | My recommendation |
|---|---|---|
| 1 | Is "phase 1" items 2–3 of § 7, as built? | Yes; build the Pinnacle recorder next (it serves the decided live price and the matchups) |
| 2 | Past revisions: "exact" (validate every part, recompute what changed) or "fixed" (hold history between weekly rebuilds, the daily_update_speed study's option b) | **Exact**, as built: a fallback costs minutes, and the inputs always equal a full rebuild's |
| 3 | Where states live | Kept in `data/studies/daily_prediction/state/` (gitignored by its own file) for now; PLAN.md's `data/state/<instance>/` once this runs daily (`DP_STATE` switches it) |
| 4 | Stage 2's 2026 coefficients, computed here by the decided fit (they read 2019–2025 results) | Keep them: the decided recipe needs them for any 2026 forecast |
| 5 (11 Oct) | May I edit `stage0_build.py` and `feature_alpha_audit/repair_data.py` to read their text columns as plain arrays (or tell the daily_update_speed session to)? | **Yes**: likely about a minute a day, proven byte-equal against today's Stage 0 before use. *(Approved and done 11 Oct: byte-identical, 45–65 s saved)* |
| 7 (11 Oct) | Stage 2's speed feed: the daily set (`spd_L_D`) for live runs, as the decision says once the daily collector runs (it has since 8 Oct)? | **Yes**, the weekly set kept for replays of days before 8 Oct |
| 8 (11 Oct) | Lower-level history in live runs. The first live day (12 Oct's Shanghai R32, run by the notebook session) found Tennis My Life's post-freeze revisions in its tables: 30 old tour-qualifying matches under revised ids, 20 Challengers revised. A template build on those tables would be refused, but live runs take the day's dump and only report it. Hold the lower-level history at the 8 Oct freeze in live runs, accept the revisions, or refuse such runs? | **Hold it at the freeze**, so that live inputs follow the recipe the template was trained on. Main-tour rows keep flowing in, and new lower-level data keeps entering only as accepted packages<br>**Decided 13 Oct by the owner: accept the revisions** (the other option; [decision](../../decisions/2026-10-13-tml-lower-level-revisions.md)). Tennis My Life's own lower-level corrections enter live runs at once, as the live path already does, and training at the next rebuild. `history.py` lists them as `tml_lower`. Other sources' lower-level data still enters only as accepted packages or through the lower-level feed |
| 6 (11 Oct) | 56 GB of disk for TabPFN's caches (int8 caches would halve it but change the numbers) | **Keep the exact caches**: the disk is available (160 GB free), and int8 would move predictions |

## Files

| What | Where |
|---|---|
| The script (commands, steps) | `src/eda/daily_prediction/dp.py`, `dp_steps.py` |
| The work tree; tables; matchups and prices | `dp_worktree.py`, `dp_tables.py`, `dp_matchups.py` |
| The state path and the store | `dp_state.py`, `dp_store.py`, `dp_hash.py` |
| The families | `dp_elo.py`, `dp_ios.py`, `dp_forms.py`, `dp_stage4.py`, `dp_pieces.py`, `dp_context.py` (the plan's prototypes `src/eda/prediction_pipeline/{ios,forms,elo}_state.py`, imported unchanged) |
| Fit, predict | `dp_fit.py`, `dp_predict.py`; TabPFN's training caches `dp_tabcache.py` (the gap's diagnosis: `dp_cachediag.py`) |
| TabPFN's caches (gitignored, 54 GB) | `data/studies/daily_prediction/state/template_2026-10-10/tabpfn/season<Y>/seed<k>/` |
| Stage 0's byte-identity proof (11 Oct) | `src/eda/daily_prediction/dp_stage0_equiv.py`; records `data/studies/daily_prediction/stage0_speed/` |
| The checks behind the tests | `dp_selftest.py`; tests `test/daily_prediction/` |
| Checkpoints (gitignored) | `data/studies/daily_prediction/state/template_2026-10-10/<day>/` |
| Runs, checks, logs | `data/studies/daily_prediction/{runs,checks,logs}/`; stage 2's coefficients `stage2/` |

Nothing outside `src/eda/daily_prediction/`, `test/daily_prediction/`, `data/studies/daily_prediction/` and this folder was created or edited (checked), but one row at the top of the studies index (`docs/studies/README.md`), as the plan's session did: the builders, `prediction_run/` and the prototypes are imported as they are. The work trees live outside the repository (`C:/Users/zerom/tnr_daily*`) and are deleted at the end of each run.

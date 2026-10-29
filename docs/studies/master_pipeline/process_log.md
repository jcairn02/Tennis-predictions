# The master pipeline notebook: process log

11 October 2026 (PDT), started 09:15 · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) ·
Session: `e1afd0c6-b679-41fa-97ad-552d02e03282` (peer name `tennis-predictions-fc`) · For a future reviewer ·
Report: [README.md](README.md) (written at the end) · Subagent briefs: [subagent_briefs.md](subagent_briefs.md)

This is engineering work (an operator notebook and the thin `src/` layer it calls), not a study that scores a model.
The log is scaled to that: it records the request, the design choices and what each rested on, and the checks.
No model result is read to choose anything here.

## 1. The request

* **The owner's words, verbatim** (11 Oct 2026, 09:15 PDT):
  > "The goal of this prompt is to create a master script ipynb that mirrors the structure of the ../ufc-predictions/
  > Pipeline
  >
  > -Sections that call scraping functions that get newest data that is required for our functions and the newest
  > tennis data available
  >
  > - sections that build the training and predictions databases for the info we have available
  >
  > - sections that call scrapers of the prediction time info needed to feed as input to our best model. Anything
  > about the current event we are betting on and the players about to compete on that event that could eligible for
  > a bet
  >
  > - a section that generates the output csv that gives diagnostics about the upcoming prediction , similar to what
  > exists in the ufc pipeline for making predictions. These functions were mostly recently built but likely need
  > refinement to give us the needed info at bet time.
  >
  > Various cells  in this notebook  allows me to manually call the needed functions to retrain the model and generate
  > the predictions and get the data without asking an LLM each time.
  > I want the option of using the tabpfn 3.5 non thinking calibrated and tabpfn3.5 thinking depending on a hyper
  > parameter in the function call. Everything else about the features for these models will be the same.
  > One difference from the ufc pipeline is there's quite a bit more data so how the data is stored is different and
  > how it's pulled will be more automatic.
  >
  > Work with a small team of agents to discuss the appropriate way to approach this and arrive on your best estimates
  > and execute.
  >
  > Note the functions are in seperate src/ .py files. Most of the inner working should be hidden from the notebook"
* **Added by the owner mid-turn, verbatim** (about 09:24 PDT):
  > "Note: another process is in the midst of improving the prediction process and pipeline in .py form . Collaborate
  > with it if necessary on how the final prediction pipeline will work and the functions to be called. Potentially
  > build that part last so the other process can finish"
* **How it was read (before any agent report):**
  * **Deliverable:** one notebook in `scripts/` (the project's home for notebooks) whose cells are short calls into
    `src/` functions, in the UFC notebook's arrangement: imports first, the most frequent cells (predictions) at the
    top, the data-update and rebuild steps beneath, each cell headed by a comment saying what it does and when to run it.
  * **"Scraping functions that get newest data":** the existing refresh entry points (results, box scores, odds,
    speeds, timelines, calendars), wrapped so one call per source family runs them in the right order. Not new
    scrapers, unless a gap blocks the pipeline.
  * **"Build the training and predictions databases":** Stage 0/1 and the timeline, the model frame by the documented
    chain (the current best model's recipe), the season fits, stage 2's coefficients, and the daily pipeline's
    checkpoint state.
  * **"Prediction time info":** today's matchups at the events being bet, the players, and the bet-time prices (the
    owner's rule: Pinnacle's current line, margin removed; BetOnline's while Pinnacle has none). The daily_prediction
    README says this source does not exist yet (matchups and prices come from a CSV).
  * **"Output csv that gives diagnostics":** a per-match bet-time file, modelled on the UFC prediction CSV, built over
    the daily pipeline's outputs (forecast, price, gate flags, fallbacks, provenance).
  * **"tabpfn 3.5 non thinking calibrated" vs "tabpfn3.5 thinking":** a `model=` parameter. Read as: the local
    TabPFN-3.5 with stage 2 (whose s_tour slope is a calibration) against TabPFN-3.5-Thinking on the same 57 inputs.
    To be confirmed against the code by the recon (brief R3 item 3, R4).
  * **"Collaborate with it":** the active daily_prediction session (`d2d2331e-…`, peer `tennis-predictions-98`),
    which owns `src/eda/daily_prediction/` and is editing the Stage 0 builders now. Its folders are not edited here;
    the prediction cells call its entry points, and are built last.
* **Other readings set aside:**
  * *A notebook that holds the pipeline's logic in cells* (the UFC notebook partly does): set aside; the owner says
    the inner workings should be hidden in `src/`.
  * *A new, separate prediction engine:* set aside; it would fork the decided recipe that daily_prediction reproduces
    bit for bit.
* **The target:** not applicable in the adoption framework's sense: nothing here scores or adopts a model. The
  notebook must reproduce the decided recipe's outputs, not change them.

## 2. Starting point

* **Code:** commit `677a63f` with many uncommitted changes from other sessions (`git status` at session start).
  Active peer: the daily_prediction session, part 3 (since 09:10 PDT), editing
  `src/eda/predictability_diagnostic/stage0_build.py` and `src/eda/feature_alpha_audit/repair_data.py` for speed.
* **UFC reference:** `C:/Users/zerom/Documents/UFC-Predictions/scripts/master_script.ipynb`, 24 cells (observed,
  read 09:17): a markdown map; Step 1 imports (torch first, a Windows DLL quirk); the prediction steps 13–16b at the
  top (most frequent), each a single call with keyword switches such as `use_tabpfn_thinking=True`,
  `reuse_leg_probs=True`, `smoke_test=False`; then the data-update Steps 1–12 (scrapers, merges, history builds,
  frames, the upcoming card).
* **Tennis pieces found before the recon (observed):** the daily pipeline `src/eda/daily_prediction/dp.py`
  (refresh → matchups → prices → worktree → tables → states → fit → predict; reprice, grade, checkpoint), the
  rebuild chain `src/eda/model_rebuild/run_chain.py` with `fits.py`, the template steps
  `src/eda/current_best_model/{odds_input,template_inputs}.py`, ingest adapters in `src/ingest/`, and no notebook in
  `scripts/`.

## 3. Plan

1. **Recon, four read-only agents in parallel** (briefs R1–R4): the UFC notebook and its output CSV; the tennis
   data-refresh entry points; the rebuild and daily paths; the Thinking variant.
2. **Coordinate** with the daily_prediction session on its stable entry points, the matchups schema, the Thinking
   seam and the files the diagnostics CSV may read.
3. **Design discussion:** synthesise the reports into a design; two agents propose and critique it independently;
   settle it.
4. **Build, in this order:** the `src/` layer for the data refresh and the rebuild/retrain; the notebook's data and
   rebuild sections; then the prediction-time inputs, the Thinking switch and the diagnostics CSV, last, after the
   peer session's answer.
5. **Verify:** the package imports; every wrapped command's flags against the real CLIs (`--help` or a dry run);
   unit tests of the layer with the expensive calls stubbed; the notebook executed top to bottom in a safe mode
   (status and dry-run cells only); one end-to-end replay of a past day through the notebook's prediction cell if the
   GPU and the peer's work allow, its outputs compared with the daily pipeline's own run.

## 4. Chronology

Local time (PDT, UTC−7). No model result is read in this work.

| When | Step | Why | Results seen by then | Output |
|---|---|---|---|---|
| 09:15 | Read README, `docs/pipeline.md`, the UFC notebook's cell outline, `docs/studies/daily_prediction/README.md`, the current-best-model decision, PLAN.md § 7 | Orientation | none | § 2 |
| 09:22 | Launched four read-only recon agents R1–R4 | Plan step 1 | none | briefs in [subagent_briefs.md](subagent_briefs.md) |
| 09:24 | Owner's mid-turn note (verbatim in § 1) | — | none | plan step 2 added; prediction part built last |
| 09:26 | `ListAgents`; the daily_prediction process log names its session `d2d2331e-…` (started 10 Oct 20:15, part 3 from 09:10 today); matched to peer `tennis-predictions-98` (busy, started 13 h ago). Sent it five questions (entry points, prediction-time inputs, the Thinking seam, stable output files, timing), with a promise not to edit its folders or the Stage 0 builders | Plan step 2 | none | message `e58ea4ba…`; idle notice requested |
| 09:28 | Environment check (observed): the `tennis` env has nbformat 5.11.1, nbconvert 7.17.1, ipykernel 7.3.0, no torch/TabPFN; `tennis-tabpfn-local` has tabpfn 9.1.0 + torch 2.11.0+cu128; `tennis-tabpfn` has tabpfn_client 0.6.0. No `src/__init__.py`: the repo imports by `sys.path` insertion or `python -m src.…` (namespace package) | The notebook kernel must be `tennis`; GPU fits and API calls must run as subprocesses in their own envs | none | design constraint |
| 09:31 | R1 (UFC analyst) reported (taken as reported; spot-checks below where used). Main points: UFC cells are one keyword call each, defaults as module constants; the output CSV (77 columns) has no match keys beyond the two names; a provenance sidecar lets a re-bet reuse cached leg probabilities; UFC's hosted Thinking call is synchronous and in-process, which tennis's own `tabpfn_thinking58/guard.py` rejects (a timed-out fit is retried and paid twice). R1 advises against cell order differing from run order | Plan step 1 | none | this row |
| 09:38 | R2 (data refresh) reported (taken as reported; the commands it names are re-checked against each CLI's `--help` before use). Main points: a Windows scheduled task already runs `-m src.ingest.scheduled` daily at 07:30 (tml → speeds → itf → canary Mon → slams reminder → tdi Mon); today's run exited 1 on held TML Challenger files; odds refreshes (`refresh_odds`, `oddstrader`) are not scheduled, and a held OddsTrader month needs `--refresh-month`; `rebuild_stage0.py` rewrites shared tables (~50 min, coordinate first); the daily pipeline is pinned to `template_2026-10-10` and the tree `C:/Users/zerom/tnr_lyr_new` (`dp_common.py:27-31`); prediction-time gaps: no Pinnacle adapter (a 9 Oct probe only), no ATP order of play, no alias table, and a first-round match cannot be built until TML lists a played match of its event. Flags for the owner: stage 2 reads `spd_L_B` though the daily collector runs (decision says `spd_L_D` then); `odds_sources/common.py` stops at season 2026 | Plan step 1 | none | this row |
| 09:45 | R3 (rebuild and daily path) reported (taken as reported except where re-checked). Main points: latest instance `template_2026-10-10` (fits 2019–2026 × seeds 0–15); the rebuild is CLI-only at the fit (`fits.py`), callable functions in `run_chain.py`; `dp_steps.run_day(...)` and each step are callable but the fit re-launches itself in `tennis-tabpfn-local`; matchups CSV columns `tour, tourney_id, round, player_a, player_b, day, p_a` (+ `tourney_name, best_of, start_utc`); `predictions.csv` has 22 columns (no edge, no EV, no side-B price); "calibrated" = stage 2's per-tour slope s_tour (the Thinking study's rule is η + b·spd_L with no slope: research, not decided); a Thinking backend would write the same `fit/season<Y>_seed<k>.npz` files; a reused run folder silently keeps stale fits | Plan step 1 | none | this row |
| 09:47 | **Re-checked R3's claimed name swap (observed):** `prediction_run/run.py` `live_from_matchups` flips `p_a` to Stage 0's side A but stores the CSV's `player_a`/`player_b` unflipped; `dp_predict.py` writes them beside side A's ids, price and q. Real. Not fixed here (another study's file, promised untouched); reported to the peer with a suggested fix; the diagnostics reader will take names from the ids | A money-relevant label error | none | message `656206f0…` |
| 09:50 | Read the Pinnacle probe of 9 Oct (`data/raw/pinnacle/probe/`, observed): guest API `/0.1/sports/33/matchups` (league names carry the round: "ATP Shanghai - R2"; parent matchups carry the real names; "(Games)" children are alternates) and `/markets/straight?primaryOnly=true` (moneyline period 0, American prices, `maxRiskStake`); the key sits in the public `config/app.json` (`api.haywire.apiKey`; value not printed) | Prediction-time source for matchups and the decided live price | none | design § 1 |
| 09:55 | R4 (Thinking) reported (taken as reported; `dp_fit.py`/`dp_predict.py` re-read by the lead). Main points: guarded async pattern of `tabpfn_thinking58/guard.py` (the SDK's sync path can bill twice); settings pinned (`v3.5_default`, 8 est., 0.9, seed 0, effort high, metric log_loss); no Thinking fit on the 57-input template, none walk-forward; bills were 25% of the free quote; estimates (inference) ≈180k tokens billed per season fit, ≈30k per daily call; quota 5M/day; the 8 Oct Thinking rule is η + b̃_local·spd_L with no slope (research); fits re-attach by id, retention undocumented | Plan step 1 | none | design § 5 |
| 09:58 | Wrote `design_v1.md` (frozen as sent to the critics); launched D1 (operator) and D2 (correctness/money safety) | Plan step 3 | none | briefs appended to [subagent_briefs.md](subagent_briefs.md) |
| 10:05 | Captured `--help` of the 19 CLIs the layer will wrap (scratchpad `help/`; read-only; `table.py` prints its doc and exits 2 without a mode; `live/form.py` fails on `--help`, not wrapped). Flags match R2/R3's commands | Success criterion 5a | none | flags verified |
| 10:10 | Wrote `src/pipeline/config.py` (interpreters read from the shims; overrides `TENNIS_PYTHON`, `TENNIS_TABPFN_PYTHON`, `TENNIS_TABPFN_API_PYTHON`), `runner.py` (streamed subprocess steps, logs, receipts, dry runs, tree-kill on interrupt, parallel steps), `data.py` (section B) | Plan step 4 | none | code |
| 10:25–10:55 | Wrote `train.py`, `thinking.py`, `thinking_api.py` (season fits: free quote by default, the guard's fit-only flow, `fit.json` with the peer's `train_sha256` recipe), `status.py`, `__init__.py` (lazy names), `src/ingest/pinnacle.py` (the recorder), `live.py` (the linker). Offline tests on the 9 Oct probe (observed): 58 match moneylines staged, 46 usable (9 in-play and 3 doubles excluded); the linker mapped Shanghai → TML `2026-5014`, Pinnacle R2/R3 → R64/R32, WTA Beijing → `2026-1020`, flagged every match TML already holds, and found **"Jakub Mensik" names two Stage 0 ids** (atp:210150, atp:210084) | Plan step 4 | none | code; probe test |
| 10:58 | Measured (observed): among players with a 2025–26 main-tour match, 12 ATP and 2 WTA name keys name two Stage 0 ids (Mensik, Landaluce, Gigante, …); `run.py` refuses such a key, which would stop a whole run. The linker leaves those matches out with the reason; reported to the peer (message `09afdf51…`) with D2's concurrency and Thinking points | Live-day blocker | none | report |
| 11:00 | **D2 (correctness) reported** (taken as reported; its curve-root count re-checked when the diagnostics were written). Adopted: exact main-level event matching and round verification; `cutoffAt`/start after the pull; resolved ids carried in the CSV and checked after the run; scrubbed child environment (`DP_*`, `LLE_*`, `MODEL_REBUILD_SANDBOX`); `template_check` before prediction; seeds 0–15 and `--refresh` forced for bet runs; a lock and a work-tree check; p* reported as every root (0–3 roots seen on the replay); EV at a new price read off the curve; fair odds 1/q; no Kelly column (the owner's 8 Oct research stake rule offered instead, labelled); `link_odds=False` removed; per-pull staged files. Not adopted: "always run the local model beside Thinking" (the peer owns the Thinking seam) | Plan step 3 | none | revisions below |
| 10:20 | **The peer's answers** (verbatim in § 4a below). Agreed division: the notebook calls `dp.py` only through its CLI; this session builds the matchups module (Pinnacle recorder + linker, the peer's `MATCHUP_COLUMNS`, plus `quoted_at`); **the peer owns the Thinking seam** (`--model {local,thinking}` inside `dp_fit`/`dp_predict`) after owner decisions, and asks that the notebook raise `NotImplementedError` for Thinking until then; the name bug is fixed in the peer's files (`dp_steps.side_names`); prediction section from about 11:00. Replied: agreed; shared R4's Thinking facts; offered to build the paid season fits in the retrain section (asked yes/no) | Owner's mid-turn note: collaborate | none | message `f583dbfa…` |
| — | **Correction (added 10:24 PDT, clock read with `date`):** the rows timed "10:10" to "11:00" above were timed by estimate, not by the clock, and run ahead of real time (D1 noticed: the clock read 10:05 when rows said 10:10+). The order of the steps is right; their real times are earlier, between about 09:45 and 10:12. The rows from "10:25–10:55" and "10:58"/"11:00" were also inserted above the "10:20" row by mistake. From here on every time is read from the clock | Rule 4 (correct by adding) | none | this row |
| 10:05–10:12 | **D1 (operator) reported** (its two load-bearing claims re-checked by the lead, observed): `run_chain.setup` copies `data/studies` excluding only `full_runs`, `pytest_*`, `__pycache__`, so a rebuild sandbox would copy the daily pipeline's 55 GB of TabPFN caches (119 GB free at 10:11): real; and the log-time drift: real. Adopted: a disk check in `build_instance` (refuses below 130 GB with the options) and `sandboxes()`; `live_prices` orients by the resolved id (it compared Pinnacle's raw spelling: an alias would have flipped the price); TDI/ITF refused while paused after a block (`override_pause=True`); `morning_refresh` refetches results/speeds older than 6 h; the notebook's own work tree `tnr_daily_nb` and a GPU-users warning; running-step markers and `running()`; fair odds both sides, serve-speed coverage, the run's download warning and the left-out matches in the diagnostics; a kernel check, season-rollover note and maintenance cell in the notebook. Not adopted: splitting A1 into "refresh into the run folder, then link" (it would drive dp.py's steps one by one, against the peer's "the CLI's run_day is the contract"; the residual risk, a player new since 8 Oct, is handled by finding them in TML's rows); moving the checkpoint after betting (the peer's design; `leave_checkpoint` is exposed instead) | Plan step 3 | none | revisions |
| 10:13 | Renamed `src/pipeline/status.py` → `overview.py` (the package exports a function `status`; a submodule of the same name can shadow it); `tp.config` etc. resolve as modules | A latent bug | none | code |
| 10:15 | **Real checks (observed):** `tp.status()` and `tp.template_check()` on the live repository: template OK (57 inputs, Pinnacle-first odds on this frame, layer built, seeds 0–15 for 2026, the daily tree's layer config identical). **First real Pinnacle pull** (3 GETs, 6 s, receipts and raw copies kept): 75 match moneylines, 61 usable; the linker found 8 ATP Shanghai R32 matches for 12 Oct linkable; 23 WTA Wuhan R1 matches left out (no played match at the event yet: first rounds wait); Pinnacle also names rounds by draw ("ATP Shanghai - R16"), which the parser missed: fixed; then 10 linkable (8 R32 + 2 R16), 1 left out (Jakub Mensik's two ids) | Success criterion 5e | none | `data/raw/pinnacle/2026-10-11/`, `data/dump/odds/pinnacle/pulls/2026-10-11/` |
| 10:16–10:17 | `test/master_pipeline/test_master_pipeline.py`: 19 tests (every issued command against its CLI's `--help`; odds, margin, rounds, curve roots; probe staging and linking; diagnostics on the replay incl. D2's root count {1: 9, 3: 7, 0: 6, 2: 1}; the runner; Thinking refused without `--spend-tokens`; `train_sha256` equal to `dp_tabcache.train_sha256`; the notebook clean). First run 18/19: the failing case was the test's own arithmetic (R4 of a 32 draw is SF); fixed; **19 passed in 15 s** | Success criteria 5a, 5b | none | tests |
| 10:18 | **The notebook executed top to bottom with `DRY_RUN = True`** (nbclient, the tennis env's kernel): 5 s, no error; A1–A4 ran their real checks (template, 8 matches pass), every other step printed its command. Its outputs kept in the scratchpad, the notebook itself saved without outputs | Success criterion 5c | none | scratchpad `master_pipeline_dryrun_executed.ipynb` |
| 10:21 | Told the peer about a planned live `run_day` test (8 Shanghai R32 matches, own work tree, after its tests end ~10:50); asked it to say "hold" if it objects | Success criterion 5d (live variant) | none | message `8ae0efc3…` |
| 10:22 | **The peer: "HOLD the live run … until I message you that my changes have landed (expected about 11:20 PDT)"** (its edits to `dp_steps`/`dp_matchups`/`dp_predict`/`dp_common`: the cleanup guard, `quoted_at`, `DP_INSTANCE`). Held; asked for `DP_INSTANCE`'s exact semantics | Collaboration | none | message `16a1110a…` |
| 10:23–10:25 | README written; index rows in `docs/studies/README.md` and `scripts/README.md`; an orientation test added (home on side A and on side B, corrupted price, swapped player, stale quote): 20 passed | Plan step 5 | none | docs, test |
| 10:26 | Launched V1 (independent code review, read-only; brief in [subagent_briefs.md](subagent_briefs.md)) | Plan step 5 | none | — |
| 10:45 | **V1 reported** 6 money and 6 robustness findings, several reproduced offline (taken as reported, each fix re-tested). Fixed: (1) **manual matchups dropped the bookmaker's margin** (the diagnostics read other column names; 14 of 20 shown picks lost money at the typed odds in V1's test): one odds column name for both sources, and missing odds now block the pick; (2) a paid Thinking call possible without a spend flag once the peer adds `--model`: `predict_day(spend_tokens=True)` required, exact flag detection; (3) checks and run could see different instances/trees (kernel `DP_*` read by the checks, scrubbed from the child): one resolution (`dp_defaults`, a saved `use_instance` choice), handed to every dp step (`dp_env`), and the predicted instance asserted equal to the checked one; (4) Pinnacle's best-of would override Tennis My Life's (a model input): no longer written; (5) a new-since-Stage-0 away player blocked as a read-back failure: only present ids compared; (6) a first round could link to the previous event of the same city: an event whose final is played, or whose latest match is over a week old, is refused (a stricter "later round already played" rule was written, then withdrawn before any run: after rain one half of a draw can be a round behind); (7) Ctrl-C left an 18 GB work tree with "delete it" advice, dangerous with its junctions: the daily pipeline's own `cleanup --work-tree` now runs on any stop, and `cleanup_work_tree()` exists; (8) **steps died with the kernel** (their output piped to it): output now goes straight to the log file, which the cell follows; (9) `reprice(dry_run=True)` pulled and wrote: now a true dry run; (10) `latest_run` by mtime: by name; (11) diagnostics overwritten: one timestamped file per call; (12) smaller: naive quote times, failed scheduled jobs counted fresh, a failed parallel lane left the other running, the no-curve note, speed checks on replays, the archive day, `only=`/`drop=` matches vanishing from the file | Plan step 5 | none | code |
| 10:50 | Tests: **26 passed** (6 new: dry-run reprice, run order by name, the spend flag, the event rule, time zones, `dp_env`); the notebook re-executed in dry-run mode: 4 s, 0 errors | Success criteria 5a–c | none | tests |
| 11:00 | **The peer: changes landed and tested** (its suite 15/15 at 10:43; 11/11 targeted at 11:00): `quoted_at` (any ISO 8601, matched by row, to `prices.parquet` and `predictions.csv` as `price_quoted_at`; run_day keeps the CSV as `<run>/matchups.csv`); `DP_INSTANCE` = the instance folder's name, recorded in `run.json` at init; the work-tree cleanup deletes only the tree its marker names. Checked (observed, 11:01): the layer reads the new `dp_common` (defaults `template_2026-10-10`, `tnr_lyr_new`; `dp_env` now passes `DP_INSTANCE`); dp's `run_day` offers no `--model` yet (Thinking raises NotImplementedError) | Collaboration | none | — |
| 11:01 | Fresh Pinnacle pull (6 s): the same 8 Shanghai R32 matches of 12 Oct link, prices moved since 10:15 (e.g. Lehecka −134 → −144); 73 listed matches left out with reasons; all 8 pass `check_matchups` | Success criterion 5d | none | `matchups_2026-10-11_110135.csv` |
| 11:02 | **Launched the first live end-to-end run** from the layer: `tp.predict_day(MATCHUPS, model="tabpfn35")` then `tp.bet_diagnostics(RUN)` (scratchpad `live_run.py`, output `live_run.out`), in the background | Success criterion 5d | none | running |
| 11:25 | **The live run finished (observed):** exit 0 in 1,393 s (`run_day.json`: refresh 89, tables 230, states 390 with 11 parts recomputed and 3 resumed, checkpoint 609, fit 57, predict 0.2, cleanup 2.5; work tree deleted); all 8 matches predicted with `template_2026-10-10` (asserted equal to the checked instance); gate: 5 may be bet, 3 do not (a missing box score); `price_quoted_at` = 18:01:29Z; diagnostics: no read-back block, Pinnacle's away player on side A flipped correctly (Bergs v Alcaraz: 0.905379 = 1 − 0.0946), 4 matches with a +EV side at Pinnacle's own odds (a diagnostic; nothing was bet), warnings: the run's history check (template_ok false on 11 Oct's tables) and the held-file exit of the TML download. A new checkpoint `state/template_2026-10-10/2026-09-21/` was left by the daily pipeline's own design. These model outputs were read only to check the plumbing; no choice was made on them | Success criterion 5d | the run's predictions (plumbing only) | `data/studies/daily_prediction/runs/live_2026-10-11_110150/`, `predictions/2026-10-12/` |
| 11:35 | The peer confirmed the live run and is putting the history check (template_ok false on 11 Oct's tables: 2011 tour-qualifying matches under revised TML player ids; some 2026 Challengers revised) to the owner as a decision with three options (hold lower-level history at the 8 Oct freeze in live runs, its recommendation; accept; refuse). Added as decision 9 of the README with the lead's agreement to option 1; the diagnostics keep it a warning until the owner decides. The peer expects later days at about 6–7 min (states ~2 min, no checkpoint step) | Collaboration | as above | README |
| 11:45 | **The owner asked:** "What is the difference between the 'revisions' and the lower level history as frozen on 8 Oct?" Answered from a read-only comparison of the frozen Stage 0 (`reference_2026-10-08/frozen/…`) and the live run's (`runs/live_2026-10-11_110150/stage0/`; scratchpad `history_diff.py`), observed: 30 lower-level matches re-identified (shown as 30 dropped + 30 new because a match id holds its players' ids; 28 paired one-to-one by event, round and score, 2 share a score): 21 Rome 2011 and 3 Umag 2011 qualifying matches (the frozen copy has 24 unnamed placeholder ids there and several named players today's data replaces), 1 Winston-Salem 2015 qualifying, Andre Ilagan's 2017 Challenger moved to his main id, 4 2026 qualifying matches re-attributed; 20 revised in place: 18 ages (Ilagan 56.5 → 25.6 in 15 Challengers; Miguel Tobon 58.2 → 20.2 in 3) and Ilagan's 2 Washington qualifying matches moved to his main id. Accepting would merge Ilagan's two ids (Mensik keeps two). None of the 8 predicted players is touched. README decision 9 made precise; the recommendation refined: hold now, route the corrections as a repair candidate | Owner's question | the run's history record | README |
| 11:55 | **The owner, verbatim:** "There was a freeze that was told to freeze and not include new challenger data until we run an experiment that checks how we should effectively integrate challenger data. We however completed the study and found how to effectively integrate challenger data by changing weight of that info and adjusting it by opponent skill. This is not that right? Why aren't we just using the newest data? Is it to save time from training a big model constantly?" Checked the 10 Oct decisions (observed): the level layer settled HOW (men; ITF box scores excluded until P7; women untouched) and the men's 2026 Challenger backlog entered as an accepted package; the freeze rule in CLAUDE.md was narrowed, not lifted (past lower-level history still gated per batch). New matches since 8 Oct do flow (today's run: 96, 42 of them men's Challengers). Recommendation revised: a standing policy accepting lower-level data from the layer-validated feeds automatically (live now, training at rebuild, harm check per rebuild), the candidate step kept for new kinds; README decision 9 updated | Owner's question | — | README |
| 12:05 | **The owner, verbatim:** "Do you recommend also retraining post 50 corrections? I'm away from my computer accessing remotely so it won't be competing for Gpu usage". Measured (observed): the corrections touch 97 player ids, who appear in 6,402 of the 62,869 rows the 2026 fit trains on (10.2%; by season 737 in 2013 falling to 190 in 2025), through one to three old (mostly 2011) qualifying results each. Recommended: not now (effect expected below resolution, an inference; live runs already use the corrections; cost is a build, a shared-table rebuild or candidate Stage 0, a ~75 GB sandbox on ~100 GB free, and a new checkpoint/caches, plus the policy or candidate approval); batch with the next worthwhile rebuild. README decision 9 extended | Owner's question | — | README |
| 11:26 | The "not predicted" rows trimmed to main-tour singles by default (`left_out="main"`: 73 → 23, the Wuhan first round); **A6 for real:** a Pinnacle pull at 18:26:15Z, `dp.py reprice` read each new price off the curve (e.g. Fils 0.789 → 0.796, q 0.811 → 0.817), the diagnostics recomputed at the new prices (quote age 0.1 min). Tests: 26 passed. Sent the peer its requested `run_day.json` and the checks (message `39d1d1c6…`) | Success criteria 5d, 5b | as above | `reprice_*.csv` in the run |

## 4a. Messages with the peer session (the daily_prediction session, `tennis-predictions-98`)

The lead's messages are in the session transcript (sent 09:26, 09:47 and 10:20); their content is summarised in the
chronology. The peer's reply that shaped the design, verbatim (received about 10:18 PDT):

> daily_prediction session: answers to your 5 questions, and the name bug you found is real and now fixed in my code.
>
> NAME BUG: confirmed. prediction_run.live_from_matchups turns p_a to Stage 0's side A but keeps the CSV's names, and dp_predict wrote those names beside side A's ids, prices and q. Replays carry no names, so no test caught it. Fixed in my files only (prediction_run untouched):
> - dp_steps.side_names reads each side's name from Stage 0's own player rows by side, and refuses a match whose rows disagree with its A/B ids.
> - live_stage0.parquet gains player_a_name and player_b_name.
> - dp_predict writes those and never the CSV's names. A run folder made before the fix is refused; rerun its states step.
> - Tests: test_side_names_follow_stage0_sides, and test_prediction_names_are_stage0_sides (each name must be the template's Stage 0 name for that side's id).
> In predictions.csv every "_a" figure, and reprice's p_a, is Stage 0's side A, whose id is player_a_id and whose name is player_a. live_meta.parquet still holds the CSV's names: don't read names from it.
>
> 1 ENTRY POINTS: call dp.py as subprocesses; the CLI is the stable contract. dp_steps.run_day and other Python functions are internal; their signatures changed today and may change again.
>   ./python.sh src/eda/daily_prediction/dp.py run_day --run <folder> --matchups <csv> [--refresh] [--fit-cache use|rebuild|off] [--seeds 0-15] [--checkpoint auto|YYYY-MM-DD]
>   reprice --run <folder> --prices <csv: match_id,p_a, side A's>
>   grade --run <folder>
>   checkpoint --tree <tree> --day <YYYY-MM-DD>
> - New today: --fit-cache (default use), plus a history step that run_day runs beside the states step. No flags were removed.
> - A failure exits non-zero. Each step's time is in <run>/run_day.json.
> - One run at a time per work tree (DP_WORK_TREE, default C:/Users/zerom/tnr_daily); set it if you run two at once.
> - The fit waits while any other tennis-tabpfn-local process uses the card.
>
> 2 MATCHUPS, § 7 item 1: I am not building the Pinnacle recorder, linking, aliases or first-round columns; the owner hasn't asked me. Please build the module that writes the matchups CSV. The schema is prediction_run/run.py's MATCHUP_COLUMNS, which I pass on unchanged, and I'll keep it stable:
> - tour: atp or wta.
> - tourney_id: Tennis My Life's id. The event must already have TML rows, so first rounds can't be predicted yet.
> - round: R128..F or Q1..Q4.
> - player_a, player_b: names as Stage 0 knows them, matched by exact name key; an ambiguous name stops the run.
> - day: the match's date.
> - p_a: margin-free chance that the CSV's player_a wins. The pipeline turns it to side A.
> - Optional: tourney_name, best_of, start_utc.
> Quote time: agreed. I'll add an optional quoted_at column (UTC ISO 8601), carried to prices.parquet and to predictions.csv as price_quoted_at. price_recorded_at stays as the time the prices step ran. I'll tell you when it's in.
>
> 3 THINKING SWITCH: I'll own it inside my code, as --model {local,thinking} in dp_fit and dp_predict; please don't wrap it. The price grid, per-seed caches, seeds and symmetrising all live in dp_fit. It needs owner decisions first:
> - Thinking is the paid API, so every daily fit costs money.
> - Its training-size limits.
> - Its seeds.
> - Stage 2's coefficients are fitted on the local model's own seeds 0-3 forecasts of 2019-2025. Thinking would need its own fit, or stage 2 off.
> Until then, expose the parameter in the notebook and raise NotImplementedError for "thinking".
>
> 4 STABLE OUTPUTS (all in the run folder; columns may be added, not removed or renamed):
> - predictions.csv: match_id, tour, tournament, round, player_a_id, player_b_id, player_a, player_b, day, price_source, price_recorded_at, p_market_a, p_base_a, eta, p_grid_read_back_a, spd_L, q_a, gate, gate_reason, instance, seeds, checkpoint. Today's change: player_a and player_b are now side A's and B's names. Coming: price_quoted_at.
> - curves.parquet: match_id, odds_logit, p_market_a, p_base_a, eta, q_a (91 prices a match).
> - gate.csv: prediction_run's gate, unchanged.
> - provenance.json: keys may grow, so read only the ones you need.
> - run_day.json, states.json, fit.json.
>
> 5 TIMING: today's work, Stage 0 about 40% faster with byte-identical output plus your bug fix, is in. The full test suite is running and should end about 10:45 PDT; then the docs. The quoted_at column comes after that, today. So the prediction section can be built from about 11:00 today.
>
> SPEED FEED (spd_L_D): I agree with your reading. The decision says "spd_L_D once the daily collector runs", and the collector has run daily since 8 Oct. So live runs should use the daily coefficient set, and replays of days before 8 Oct the weekly one. That changes predictions, so I'm asking the owner before changing it. Do list it on your side too.

Later messages from the peer (summarised; verbatim in the session transcript):
* About 10:20: agreed with the division; exact spellings: an optional matchups column `quoted_at` (UTC ISO 8601) reaching
  `predictions.csv` as `price_quoted_at`; `--model local|thinking` on `fit` and `run_day` later; "yes to the division, if
  the owner approves the Thinking plan … Please don't spend tokens until the owner says so"; the `train_sha256` recipe.
* About 10:20 (second): "HOLD the live run, please, until I message you that my changes have landed (expected about 11:20
  PDT)": its edits to `dp_steps`, `dp_matchups`, `dp_predict`, `dp_common` (the work-tree cleanup guard, `quoted_at`,
  `DP_INSTANCE`) would be imported partway through a run started earlier.

## 5. Sources (external, reached in this work)

* **Pinnacle's public guest API** (accessed 11 Oct 2026, 10:15 PDT; three GETs, paced; receipts in
  `data/raw/pinnacle/_receipts.jsonl`; raw copies in `data/raw/pinnacle/2026-10-11/`): `https://www.pinnacle.com/config/app.json`
  (the public config holding the guest key), `…/0.1/sports/33/matchups?withSpecials=false`,
  `…/0.1/sports/33/markets/straight?primaryOnly=true`. Covered by the scraping decision of 8 Oct (publicly served; no login,
  paywall or CAPTCHA). It supports the listed matchups, start times and current moneylines (observed). Its round labels
  are Pinnacle's own ("R3", "R16"), mapped through Tennis My Life's draw size (inference, checked against TML's rounds).
* **Prior Labs' hosted TabPFN API:** not called. The quote and fit paths were tested offline only (no token used); their
  behaviour rests on the project's guard (`tabpfn_thinking58/guard.py`) and R4's reading of the SDK (not re-run).
* Nothing else outside the repository was reached.

## 6. Judgment calls and deviations

1. **Where the layer lives:** `src/pipeline/` (new), not `src/eda/`. CLAUDE.md's table puts study code in `src/eda/`; this
   is an operator layer, not a study, and the owner asked for "functions in separate src/ .py files". D1 agreed. Owner
   decision 6 asks for the CLAUDE.md row. No result exists in this work, so nothing was seen before choosing.
2. **Subprocesses, not imports:** every heavy step runs as its own process in its own environment; the kernel imports only
   light readers. Reasons: three environments, the peer's "the CLI is the stable contract", crash isolation. The other
   branch (importing `dp_steps`) would break whenever the peer changes an internal signature (it did today).
3. **Section order:** bet day first (UFC's convention, the owner's "mirrors the structure"), each section in run order. R1
   advised run order throughout; D1 agreed with frequency-first because the bet-day section refreshes its own data.
4. **The Thinking split** (agreed with the peer): this side holds the paid season fits (quote by default; one slot per
   instance and season; the peer's `train_sha256`); the peer owns `--model thinking` in its fit and predict. The design's
   "thin predict" fallback was dropped (D1, D2: it would fork `dp_predict`). Until the peer's flag exists, the predict cell
   raises NotImplementedError naming what waits. The owner asked for the switch; it is exposed but not yet runnable for
   daily predictions: the largest gap between the request and the delivery.
5. **No staking rule:** D2 asked to drop Kelly; the owner's own 8 Oct research rule is offered opt-in, labelled research.
6. **Gate-like rules in the diagnostics:** a stale quote (30 min), a started match, read-back mismatches, not-main and an
   unsupported format block the pick; the history check is a warning, not a block. D2 asked to block on
   `template_ok = false`; not adopted: the peer's daily path treats it as a report, and a bet gate is the owner's policy.
   The 30-minute threshold is an assumption (a parameter), not a decided rule.
7. **The linker's eligibility:** main-tour singles (TML levels G, M, A, F, P, PM, I, 1000, 500, 250), no qualifying, no
   "Cup" leagues; events matched among main-tour TML events of the last 16 days, exact name tokens first. Chosen from the
   model's population (the decision's "Matches") and D2's collision examples ("Shanghai CH"), before the live pull.
8. **Ambiguous names left out, not fixed:** run.py would stop the whole run on them; fixing duplicated ids is a data repair
   for the owner and the peer (decision 3).
9. **The live end-to-end run** was planned for success criterion 5d and held at the peer's request; its outcome is in the
   chronology.

## 7. Claims and their evidence

| Claim (README) | Evidence | Status |
|---|---|---|
| The tests pass (19, then 20 with the orientation test) | `./python.sh -m pytest test/master_pipeline -q` (10:16; 10:22) | observed |
| Every issued command parses | `test_every_issued_command_parses`: 32 commands, 19 targets, each flag in its `--help` | observed |
| The notebook runs top to bottom in dry-run mode | nbclient execution, 10:18 (scratchpad `master_pipeline_dryrun_executed.ipynb`) | observed |
| Today's pull: 75 moneylines, 61 usable, 8 Shanghai R32 linked; Wuhan R1 left out | the 10:15 pull (`data/dump/odds/pinnacle/pulls/2026-10-11/`), `todays_matches()` | observed |
| 14 active players with two Stage 0 ids | query on the repository's Stage 0 (8 Oct build), about 09:55 | observed |
| The name swap existed; it is fixed | `run.py` read by the lead (09:47); the fix as reported by the peer | observed (bug); peer's claim (fix) |
| The rebuild sandbox copies 55 GB of caches | `run_chain.py:171` read; `du` of the state folder (10:11) | observed |
| Curve crossings 0–3 per match (6/9/1/7 matches) | `test_diagnostics_on_a_replay` | observed |
| The first live day ran end to end from the layer (1,393 s; 8 predicted; prices read back) | `runs/live_2026-10-11_110150/` (`run_day.json`, `predictions.csv`), `predictions/2026-10-12/…_diagnostics_*.csv`, scratchpad `live_run.out` | observed |
| Thinking cost estimates (≈180k per season fit, ≈30k per day) | R4's inference from four past receipts | subagent inference, not re-derived |
| Past bills were 25% of the quote | R4, from the Thinking studies' receipts | subagent finding, not re-checked |

## 8. Weak points

* **The live path has run end to end once** (11 Oct, 8 matches, one event, one tour). Women's matches, a Slam (best of
  5), a day with several events, Pinnacle naming a round differently, and a different instance (`use_instance`) have not
  run live yet; each has a unit test or a guard, not a live run.
* **The linker's rules are new code over a changing listing:** Pinnacle's league and round naming (seen on two days only)
  and TML's event names. A wrong round would change an input and the side-A hash; the guard is the check of each player's
  last win at the event. Where a flaw would hide: a player's first match after a bye, which that check cannot verify.
* **Names are checked against the 8 Oct Stage 0:** a player new since then passes on TML's rows, and the run's refreshed
  Stage 0 is the final check (it stops the run if wrong); A5's id read-back catches a wrong link.
* **The diagnostics' pick ignores staking, venue costs and the uncertainty of q** beyond the seed spread: a diagnostic,
  labelled so.
* **Concurrency with other sessions:** the notebook's own work tree and lock prevent clashes with the peer's runs; other
  sessions' scrapers can run at the same time as the B cells (their own locks apply).

## 9. Reviewer checklist

* [ ] `./python.sh -m pytest test/master_pipeline -q` passes.
* [ ] Open `scripts/master_pipeline.ipynb` with the `tennis` kernel; set `DRY_RUN = True`; run all: no error.
* [ ] `tp.template_check()` is OK for the season.
* [ ] After a live run: no predicted row of the diagnostics carries a "read-back" block, and `pinnacle_odds_a` matches the
      Pinnacle pull for side A (by id).
* [ ] `git status`: only `src/pipeline/`, `src/ingest/pinnacle.py`, `scripts/`, `test/master_pipeline/`,
      `docs/studies/master_pipeline/`, `data/studies/master_pipeline/`, the Pinnacle data folders and the two index rows are
      new or changed by this work.

## 10. Reproduction

```
./python.sh -m pytest test/master_pipeline -q            # 20 tests, about 20 s, offline
./python.sh -m src.ingest.pinnacle                       # one Pinnacle pull (network, 3 GETs)
# the notebook, dry run: DRY_RUN = True in its first code cell, then run all (kernel: the tennis env)
```

---

# Part 2 (13 Oct 2026): the bet sheet

13 October 2026 (PDT), started 15:40 · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) · Session:
`f66b9e99-f90d-40a5-b5fe-c347536062c5` (peer name `tennis-predictions-b2`) · Engineering work on section A's output; no
model is scored and no model result chooses anything. Part 1 above is not edited.

## P2.1 The request

* **The owner's words, verbatim** (13 Oct 2026, about 15:30 PDT):
  > "im looking at the master_pipeline.ipynb, and looked at the predictions output .csv's a lot of improvements needs to
  > be done. These are almost illegible.
  > The most important qualities are buried. and lots of stats that have confusing information are apart of these
  > csvs's.
  > Think, "if I were a businessman looking at this information to find information about the matchup and to find which
  > side to bet, and by how much? think how hard it would be dig through all this data you have no idea what it was. The
  > output organization needs to be greatly improved."
* **What was seen first (observed, `predictions/2026-10-12/`):** three CSVs. The diagnostics file has 53 columns; the
  decision (`pick`, `pick_player`, `ev_pinnacle_pick`) sits in columns 40–46, behind break-even roots; every number
  carries 4–16 decimals; the players are Stage 0's sides A/B, not Pinnacle's order; the same three run-level warnings are
  repeated in every row; 23 "not predicted" rows with ~45 empty cells each outnumber the 8 predictions; start times are
  UTC (a 04:00Z match of "12 Oct" starts at 21:00 on 11 Oct, the owner's time); no stake appears (`STAKE_RULE = None`);
  nothing says what `eta`, `spd_L`, `p_base_a`, `q_a` or `seed_sd` mean. The daily engine's archive copy
  (`live_<run>.csv`) beside it has the same jargon.
* **How it was read:**
  * **The deliverable:** section A's output (A5, and A6's reprice), as files and as the notebook's display, organised
    for a reader deciding *which side, at what price, how much*, with the matchup's context and the detail one step away.
  * **Unchanged:** every calculation and safety rule of the diagnostics (EV at Pinnacle's own odds, margin included; a
    blocked match has no pick; a stale quote, a started match, a read-back mismatch block; one new file per call; the
    provenance sidecar). The record `bet_diagnostics()` returns keeps its columns (the tests pin them); columns may be
    added.
  * **"By how much":** no staking rule is decided. The owner's own 8 Oct research rule (`tabpfn_thinking58/common.stake`:
    favourites staked to win 1 unit, 1 unit at even money, underdogs d/(2(d−1)) units) is the only one in the owner's
    words; it is shown by default, labelled, and switched off with `STAKE_RULE = None`. Part 1's decision 7 recommended
    leaving it off; the owner's question now asks for the amount, so the default is reversed and said so.
* **Readings set aside:**
  * *Changing what counts as a bet* (a minimum EV, Kelly sizing): betting policy, not organisation; left as a
    recommendation for the owner.
  * *A "matchup facts" panel from the model's inputs* (Elo, form, surface record): the frame holds them as log-ratios and
    logit differences (observed, `live_frame.parquet`); decoding them without the feature definitions could mislead, and
    ratings are priced-in controls. Offered as a follow-up.
  * *An HTML report:* considered. Excel chosen as the file (installed on this machine, observed; sortable; the reader's
    business tool), with the same tables shown in the notebook.

## P2.2 Plan

1. Keep `bet_diagnostics()`'s record; add `src/pipeline/bet_sheet.py`, which only reads the record (it computes no
   probability, EV or block) and builds: a **Bets** table (the matches to bet), a **No bet** table (PASS: no side +EV at
   Pinnacle's odds; BLOCKED: a safety rule fired, with the reason in plain words), the run's notes said once, and a
   workbook (Bets, Matches, Not predicted, Run, How to read).
2. Files: the workbook at the top of `predictions/<day>/`; the machine record (CSV) and provenance in
   `predictions/<day>/records/`; the daily engine's archive moved there too (one path in `dp_steps.step_predict`).
3. The notebook: A5 shows the sheet; `STAKE_RULE = "owner_8oct"`; comments and the map updated.
4. Verify: the 26 tests plus new ones; the two 11 Oct sheets regenerated at their original times, every number compared
   with the old diagnostics CSVs; the workbook opened and rendered.
5. Docs: `predictions/README.md`, the README's section on the output, this log.

## P2.3 Chronology

Local time (PDT, UTC−7). No model result is read to choose anything.

| When | Step | Why | Results seen by then | Output |
|---|---|---|---|---|
| 15:30–15:40 | Read the notebook, `src/pipeline/diagnostics.py`, `predict.py`, Part 1 of this log, the README, the tests, the 11 Oct run folder, the three CSVs in `predictions/2026-10-12/`, the UFC prediction CSVs (`UFC-Predictions/predictions/`, read only; their front columns lead with the bet and a plain `Sigma_Bet_Note`) | Orientation | the 11 Oct run's predictions (format only) | § P2.1 |
| 15:40 | Checked the environment (observed): Excel at `C:/Program Files/Microsoft Office/root/Office16/EXCEL.EXE`; `tennis` env has openpyxl 3.1.5, jinja2 3.1.6, IPython 9.17; no xlsxwriter. Local zone PDT. `ListAgents`: the daily_prediction session (`tennis-predictions-98`) idle; `dp_steps.py` last written 11 Oct 10:44; no test or reader depends on the archive's path (grep) | Feasibility; who else writes `predictions/` | none | design § P2.2 |
| 16:00–16:25 | Wrote `src/pipeline/bet_sheet.py`; in `diagnostics.py`: the run's notes (history check, recomputed state, unclean download) taken out of every row's `warnings` into `_run_notes` (provenance and the sheet's header); added record columns `decision`, `home_side` (Pinnacle's first-listed side), `gate_detail` (from the gate's `gate_missing.csv`); the files: workbook on top, record and provenance in `records/`; `_show` replaced by the sheet's view | Plan steps 1–2 | the 11 Oct run (format only) | code |
| 16:25 | **Reproduction check (observed):** both 11 Oct diagnostics files rebuilt from the same run at their own times (18:25:03Z, run prices, `left_out="all"`; 18:26:22Z, the reprice): 81 and 31 rows, **52 of 52 shared columns identical** after one fix below; `warnings` now empty for every row (the three run notes moved out, as designed). Scratchpad `compare_old.py` | Only the presentation may change | the run's numbers, to compare only | — |
| 16:25 | **A pre-existing flaw found and fixed:** `_speed_coverage` chose the serve-speed form file by the match day, so a sheet remade later read files collected after it (here 12 Oct's file: the reading counts 5→6, 7→9, …). Display only: the model's own `spd_L` is the run's. Now the file is capped at the sheet's own date (`min(match day, local date of now)`); with it the counts equal 11 Oct's | Reproducibility of a shown figure | as above | `diagnostics.py` |
| — | **Correction (added 16:04 PDT, clock read with `date`):** the three rows timed "16:00–16:25" and "16:25" above were timed by estimate and run ahead of the clock (it read 16:03 when this was noticed). Their order is right; their real times were about 15:42–15:52. From here every time is read from the clock or from a file's own timestamp | Rule 4 (correct by adding) | — | this row |
| 15:53 | `pytest test/master_pipeline`: **26 passed** (the existing suite, after the record changes) | Plan step 4 | none | — |
| 15:54–15:59 | Trial workbook in the scratchpad, **rendered by Excel itself** (COM, hidden, read-only, `ExportAsFixedFormat` to PDF; scratchpad `trial_sheet*.pdf`, `trial2_sheet*.pdf`) and read. Seen and fixed: a long PASS note ran past the table and shrank the printed page (notes now wrapped at 72 characters, rows sized); the seed spread carried a +/− sign (now unsigned); a blocked match's reason appeared three times on Matches (one Notes column now); nine frozen columns on Matches (now three: start and both players); the history line twice on Run; label cells not top-aligned. Checked by hand on the render: Carreno Busta 20.6% (TabPFN) → 22.4% (+1.8 stage 2); serve-speed gap −0.730 × 1.9496 = −1.4 km/h; Lehecka (player 1, side B) no-edge price 1 − 0.0742 = 92.6% | Plan step 4 | the run's numbers, to check the display | `bet_sheet.py` |
| 15:58–16:00 | The notebook's HTML view rendered with headless Edge (scratchpad `trial_html*.pdf`): the Notes column fell off the right edge at a normal width; the view now shortens the event and lists each match's note under the table (the workbook keeps them in the table) | Plan step 3 | as above | `bet_sheet.py` |
| 16:00 | `dp_steps.step_predict` archives to `predictions/<day>/records/` (one path; content unchanged); its README line, `config.py`'s comment. The notebook: the map's bet-day row and "where the outputs land", `STAKE_RULE = "owner_8oct"` in Setup, A5's and A6's comments | Plan steps 2–3 | none | code, notebook |
| 16:00 | Tests: the orientation test's synthetic priced run factored into `_priced_run` (its asserts unchanged); 3 new tests (the sheet re-says the record: BET = the record's pick at its odds, EV and 8 Oct stake, PASS never +EV, BLOCKED offers no player/stake/odds, BET→PASS→BLOCKED, player 1 = Pinnacle's home; the plain reasons; the files: sheet on top, record and provenance in `records/`, a second call writes `_2`). **29 passed** | Plan step 4 | none | tests |
| 16:00 | **In a real Jupyter kernel** (nbclient, the `tennis` env; scratchpad `kernel_check.py`): A5's call on the 11 Oct run gives one `text/html` display (the table, the notes list), no error | Plan step 4 | as above | — |
| 16:01 | A sheet rebuilt later than its "as of" time now says so ("Rebuilt … from the run's saved files, as of …"), and the provenance gains `written_at`. 29 passed. **The 11 Oct run's two sheets written** at their own times (18:25:03Z on the run's prices, 18:26:22Z on the reprice): `predictions/2026-10-12/bet_sheet_2026-10-11_1125.xlsx`, `…_1126.xlsx`, records in `records/`. The 11:26 sheet rendered by Excel and read: 4 to bet (Auger-Aliassime 3.18 u at 1.315, Lehecka 1.44 at 1.694, Fils 4.40 at 1.227 flagged thin at +0.3%, Vacherot 0.88 at 2.320), 1 pass (Medvedev: "worth a bet at 1.182 or more"), 3 blocked (Laver Cup box scores), 23 not predicted (Wuhan first round); 9.90 units staked to win 4.16, model's expected profit +0.16 | Plan step 4 | the run's numbers (format check; nothing chosen on them) | `predictions/2026-10-12/` |
| 16:02–16:05 | Docs: `predictions/README.md` rewritten (it still said "no forecast is written here yet"); the README's output section, A5/A6 rows, decision 7, files and test count; the study index row. The four old files of 11 Oct at the top of `predictions/2026-10-12/` left in place (moving them is the owner's call) | Plan step 5 | — | docs |

| 17:30 | **The owner, verbatim** (after the report): "Why would there be no box score? if we were running predictions, wouldnt it make sense to wire up obtaining the necessary data to getting the predictions? or at least the previous steps should be run to get them? such that theres a logical flow in the master script" | Owner's question | — | investigation below |
| 17:32–17:45 | **Why the three blocks (observed):** the gate (`prediction_run/gate.py`) requires a box score for every completed match of either player at the event or with a latest possible finish in the 14 days before the match, at any level. Ruud's and Fritz–Alcaraz's **Laver Cup 2026 matches have box scores in Tennis My Life** (`data/raw/public_dump/tennis_my_life/2026.csv`, rows 2391 and 2403). **Stage 0 rejected them** (`box_status = failed_check`, also in the run's own `stage0/`): their match tiebreaks `10-8` and `13-11` are legal advantage-set scores, so `repair_data.plain_match_tiebreak` leaves them as sets by design ("without independent rule evidence it is never rewritten"). The event-level rule (`mtb_event`, `stage0_build.py:1235`) should supply that evidence, but it measures bracketed deciders in the raw score, and TML never brackets, so it sees 0 of 4 (the two certain `10-7`s are bracketed only later, in `score_columns`). Read as sets, the scores hold 41 and 43 games; 159 and 143 serve points fall under check B9's 4.5 per game, and the box scores are dropped. The Cup's two `10-7` matches pass. Laver Cup box scores were complete in 2024 and 2025 (9 of 9 each). Second cause: the timeline has no exact Laver Cup dates (`window_basis` named_rule, 7 days), so its latest possible finish is 29 Sep although it ended 27 Sep, one day inside the window of 12 Oct's matches (from 28 Sep). Either cause alone blocks; fixing either unblocks these three | Owner's question | the run's gate records | scratchpad `laver_box.py`, `laver_timing.py`, `laver_checks.py` |
| 17:45 | **Footprint of the misreading (observed, shared Stage 0):** ambiguous deciders (a 2-point final "set" of 10 or more, read as a set) at events whose other deciders are certain match tiebreaks: 3,670, of which 3,668 ITF (lower level, frozen; ITF box scores are out of the inputs) and **2 at main level: exactly these two Laver Cup matches**. All 3,924 ambiguous standard deciders by level: ITF 3,767, Slams 146 (advantage final sets, correctly sets), TEAM 11 | Scope of a repair | — | scratchpad `mtb_footprint.py` |
| 17:47 | The sheet said "no box score yet": wrong for these three. `diagnostics._gate_gaps` now reads each gap's `box_status` from the run's own Stage 0 and names the cause ("Tennis My Life has it, but our consistency check rejected it" / "has none" / "is incomplete"); the sheet says "no usable box score for …". 29 passed. The two 11 Oct sheets already written keep the old wording (not rewritten: a sheet is never replaced) | Correct my own report | as above | `diagnostics.py`, `bet_sheet.py`, test |
| 17:55 | **The owner, verbatim:** "yes do this", replying to (pasted) "1. Fix the score reading. At an event where other deciding sets were certainly 10-point tiebreaks, read an ambiguous 10-8 or 13-11 as a tiebreak too. Within the main tour it changes only these two matches, and it fixes every future Laver Cup. It changes the shared data builder, so under your adoption rules it's a repair and your call. I recommend yes. 2. Add a data check to the bet day, before the 10-minute prediction run. It would list every recent match without a usable box score, with the cause and the remedy: not published yet: refresh later (women's gaps are filled automatically); published but rejected by our checks: needs a fix like the one in 1; never published. You'd see "3 matches will be blocked, and why" before running A4, not after." | Owner's go-ahead | — | — |
| 18:00–18:02 | Stage 0 built with the code before the repair into the scratchpad (`stage0_build.py --out-dir`, 75 s; the shared tables untouched: an `--out-dir` build writes only there) | Before/after comparison | none | scratchpad `s0_before/` |
| 18:02–18:04 | The repair: `repair_data.plain_match_tiebreak(event_rule=False)`; `stage0_build.match_tiebreak_events` (main tour only, never qualifying: `history.MAIN_TOUR`; an event qualifies when one completed decider is certainly a match tiebreak and every decider's last "set" reaches 10), the `mtb_rule` column read by `score_columns`, cleaning note C42. Checked by reading: `repair_tables` (run inside the build and by downstream builders) re-reads the raw score without the rule, which leaves the repaired rows alone; `candidate_stage0`'s copy of the format logic serves new lower-level rows only | Owner's go-ahead (1) | — | code |
| 18:04–18:12 | Stage 0 built after (104 s) and compared with before on every row of all six outputs (scratchpad `s0_compare3.py`): **2 matches change** (the two Laver Cup 2026 matches: format → `match_tiebreak`, box score `failed_check` → `full`), their 4 player rows (box counts back; games 19 and 23 instead of 43 and 41), the cleaning log, cells and summary by exactly those counts; `stage0_level_applied.csv` byte-identical. **A false alarm first:** the first comparison reported 869,546 rows changed. It was an artifact: pandas 3's `astype(str)` keeps missing values as NaN, and NaN ≠ NaN. Redone with missing equal to missing | Footprint | none | — |
| 18:12 | Seen: another session edited `dp_steps.py` (18:11), and the lower-level feed reached the pipeline today (notebook cell B8, `data.py`). The repair reaches the daily engine through the repository's builder (`dp_stage0_equiv.py`: the tree runs the repository's `stage0_build.py`) | Coordination | — | — |
| about 18:15–18:24 | `src/pipeline/data_check.py` (renamed `readiness.py` at about 20:55, below). Stage 0 cached under a key: `input_record()`, the decided tables, the builders' code. The gate's rule per linked match and player. Latest possible finish: the shared timeline's, else the timeline's own rule window, else the event's start + 14 days. Causes from `box_status`; fixes from `fills.gaps`'s classes | Owner's go-ahead (2) | — | code |
| about 18:20 | **Validation against the real gate (observed):** on the 11 Oct run's own Stage 0 and matchups, the check blocks Tien–Ruud, Tsitsipas–Fritz and Bergs–Alcaraz, as `gate.csv` does, saying "Tennis My Life has it, but our consistency check rejected it". The earlier-matches counts equal the gate's, match by match. On the repaired Stage 0, all 8 are ready | Faithfulness | the run's gate records | scratchpad `dc_validate.py` |
| about 18:30 | Every build and run merges the accepted packages and each feed's snapshot after Stage 0 (`additions.merge`; the feed decision of 13 Oct). A qualifier's qualifying match or a Challenger can exist only there, so the check now merges them the same way (~15 s, ~1.3 GB held briefly, then only the checked players' rows kept) | Faithfulness | — | `readiness.py` |
| about 18:35 | Tests: two for the repair (the builder's and the repairs' files: 98 pass), two for the check (synthetic causes and fixes; agreement with the 11 Oct gate). Notebook: cell A3b inserted between A3 and A4; the section A header (the flow, timings) and the map updated; the other session's cell B8 (`46c67b30`) kept | Plan | — | tests, notebook |
| 19:00 | Peer `tennis-predictions-f6` (its messages verbatim in the session transcript): the owner decided Tennis My Life's lower-level corrections enter by themselves (`docs/decisions/2026-10-13-tml-lower-level-revisions.md`). It edited `diagnostics.py` (`_run_notes`; held files named) and `data.py` (`held_tml_files`, `accept_held_tml`), added `test_tml_notes.py`, and appended "Done/Decided 13 Oct" lines to the README's decisions 8 and 9. Re-read: its changes and mine coexist | Coordination | — | — |
| about 20:55 | **A bug of mine:** `tp.data_check` resolved to the module `src/pipeline/data_check.py`. Importing a submodule sets it on the package and shadows the function: the trap `status` hit on 11 Oct. Renamed to `readiness.py`; a test now checks that no module shares an exported name. 38 passed (with the peer's 6) | Bug | — | code, test |
| 21:03 | **End to end (observed):** a dry run prints the build. A first call builds Stage 0 in its cache (77 s; 97 s in all, step log `logs/2026-10-13/210310_data_check_stage0.log`), merges the feed's snapshot `20261013c`, and finds all 8 of the 11 Oct matches ready. A second call reuses the cache (18 s) | Plan step 4 | — | `data/studies/master_pipeline/data_check/` |
| 21:04 | Told the peer about the shared-code changes and the files still being edited. Its answer: no interaction (the repair's 2 rows are allowed main-tour revisions, not `tml_lower`) | Coordination | — | — |
| 21:05–21:10 | Decision record `docs/decisions/2026-10-13-match-tiebreak-reading.md` and its index row; README: the data check's section, the A3b row, files, tests. The other session's Part 3 below this part was not touched | Records | — | docs |

## P2.4 Judgment calls and deviations

No model result was read to choose anything below; the 11 Oct run's numbers were read to check the display only.

1. **Excel as the file, plus the notebook's view** (options: a clean CSV, HTML, Excel). A CSV cannot hold a header, colours, notes or a glossary; HTML cannot be sorted or filtered. Excel is installed here, and it is the reader's business tool. The other branch would have kept one more format universal; the record CSV stays for machines.
2. **The stake shown by default** (`STAKE_RULE = "owner_8oct"`). Part 1's decision 7 recommended leaving it off; the owner now asks "by how much". The rule is the owner's own words and sizes by the price only, so it gives no edge credit to the model's estimate. Labelled as research on every sheet; `None` hides it.
3. **One table, sorted BET → PASS → BLOCKED, then by start,** rather than two tables or a chronological list. The bets answer the question first; the decision column keeps the rest legible.
4. **Pinnacle's order on the sheets, sides A/B in the record.** The reader cross-checks against Pinnacle's listing; the record keeps the daily pipeline's contract.
5. **A blocked match shows no model numbers on the Bet sheet** (they are on Matches). A data gap makes them unreliable, and a number beside a match invites a bet.
6. **"Thin" below 1% expected profit:** a label only, with its threshold stated. It was set after the 11 Oct file had been read, where Fils' +0.26% was visible. It changes no decision.
7. **The run's notes said once** (header, Run sheet, provenance) instead of on every row: the owner's "stats that have confusing information".
8. **The daily engine's archive moved into `records/`:** `dp_steps.py` is the daily_prediction session's file (idle at the time, last written 11 Oct). One path, content unchanged, and no reader of the old path (grep). Without it, two technical files would stay beside the sheets.
9. **The speed-coverage fix** changes a shown count on sheets rebuilt later, never a probability or EV.
10. **The machine's local zone** for times (PDT here). On another machine the times follow that machine's zone; the label says which.
11. **Not done:** a matchup-facts panel; a minimum-EV hurdle; Kelly sizing (Part 1, D2). The first is offered as a follow-up, the second is put to the owner (README decision 7).
12. **(Added after the owner's go-ahead of 17:55) The repair's scope: main tour only.** The other branch, every level, would also read 3,668 ITF deciders anew. That is lower-level history, frozen, and would go through the candidate route. The event rule (one certain match tiebreak and every decider reaching 10) is stricter than the footprint query's (one certain match tiebreak). On the main tour both select the same two matches. The stricter rule was chosen so that an advantage-set event with one mistyped 10-7 does not qualify.
13. **No harm check for the repair** (a departure from the framework's default, stated in the decision). 2 matches of 875,000 are far below any comparison's resolution, and a candidate build costs about four hours; the next template build's harm check covers it with the other repairs.
14. **The data check builds its own Stage 0 (~100 s, cached)** rather than reading the shared tables (built 8 Oct, so they miss the last days) or stopping the run after its gate (`run_day --no-fit` comes after the refresh, tables and states, most of the run's time). Exact box statuses were chosen over speed.
15. **The window for matches the shared timeline lacks:** the timeline's own rule window, else the event's start + 14 days. These are cautious estimates, so the check may block a match the run lets through; for box statuses it reads what the run reads (inference: the same builder and merge on the same downloads, until the run's own download).
16. **The check's fixes are read from the run's own classes** (`fills.gaps`: held, fillable, unserved), so "the run fills it" is said only where the run's refresh would try.

## P2.5 Claims and their evidence

| Claim | Evidence | Status |
|---|---|---|
| Only the presentation changed: 52 of 52 shared columns identical, 81 and 31 rows | scratchpad `compare_old.py` against `predictions/2026-10-12/live_2026-10-11_110150_diagnostics_*.csv` | observed |
| The sheet never computes: every BET is the record's pick at its odds, EV and stake | `test_bet_sheet_says_what_the_record_says` | observed (synthetic priced replay) |
| 29 tests pass | `./python.sh -m pytest test/master_pipeline -q`, 16:01 | observed |
| The workbook renders in Excel as designed | Excel exports, scratchpad `trial2_sheet*.pdf`, `real_1126_sheet1.pdf` | observed |
| The notebook shows it in a real kernel | scratchpad `kernel_check.py` (nbclient) | observed |
| A call never replaces an earlier sheet | `test_bet_sheet_files` | observed |
| Glossary definitions match the code (seed flag 3 pts, spd_L standardiser 1.9496 km/h capped ±4, stage 2's slope < 1) | `diagnostics.SEED_SD_WARN`; `serve_speed_tabpfn/adaptive/adjust.py` docstring; the run's provenance (`s_atp` 0.90) | observed |
| The 11 Oct blocks came from Stage 0 rejecting box scores Tennis My Life had | `tennis_my_life/2026.csv` rows 2391, 2403; `box_status = failed_check` in the shared and the run's Stage 0; scratchpad `laver_checks.py` | observed |
| The repair changes exactly 2 matches (4 player rows) of Stage 0 | before/after builds, every row of six outputs (scratchpad `s0_compare3.py`) | observed |
| The data check reaches the run's gate's verdicts | `test_data_check_agrees_with_the_runs_own_gate` (11 Oct: same 3 blocked, same counts per match) | observed (one run) |
| The data check takes ~100 s, ~20 s cached | the end-to-end calls of 21:03 (97 s, 18 s) | observed |
| 38 tests pass in `test/master_pipeline`, 98 in the builder's and repairs' files | pytest, about 20:55 and 18:35 | observed |

## P2.6 Weak points

* **The plain sentences rest on patterns over the record's reason texts.** A reason worded differently by a later daily-pipeline change falls back to its own text, sentence-cased: still shown, less plain. `test_plain_reasons` pins today's wording.
* **"Lowest odds to take" holds while Pinnacle's own price stands still.** The model's input is Pinnacle's current price at every venue (9 Oct decision); if Pinnacle moves, reprice. At another venue it ignores that venue's fees unless `venue_prices`/`venue_fee` are given.
* **Row heights of wrapped notes are estimated** (Excel does not size them on opening). A long note in a narrow window can clip until the row is widened.
* **One live day exercised** (11 Oct, one ATP event). WTA rows (no serve-speed feed), best of 5, several events and another venue's prices run through code paths and tests, not a live day.
* **Where a flaw would most likely hide:** the orientation of "1"/"2" on the Matches sheet when Pinnacle's home player is side B (tested on the synthetic run and checked by hand for Lehecka and Bergs), and a stake rule other than `owner_8oct` (none exists).
* **(Added at 21:10) The data check's limits:**
  * It cannot see the indoor input, which the run's gate also checks; the run reports it.
  * It cannot know a qualifier's entry before their first main-draw match: entry is read from the player's earlier rows at the event.
  * A result Tennis My Life has not recorded at all is invisible to it and to the gate alike. At the same event, the linker's round check (A2) guards against that.
  * Its agreement with the gate is shown on one run (11 Oct).
* **The repair's live/training gap:** today's instance (`template_2026-10-13`) was built with the old reading, so live runs now read two box scores that training lacks. That affects four players' inputs for about three weeks, until the next template build.

## P2.7 Reviewer checklist

* [ ] `./python.sh -m pytest test/master_pipeline -q`: 29 pass.
* [ ] Open `predictions/2026-10-12/bet_sheet_2026-10-11_1126.xlsx`: 4 BET, 1 PASS, 3 BLOCKED; each BET's odds and expected profit equal `records/bet_sheet_2026-10-11_1126.csv`'s `pinnacle_odds_pick` and `ev_pinnacle_pick`.
* [ ] Rerun scratchpad `compare_old.py` (or its logic): 52 of 52 columns equal the old files.
* [ ] `git status`: this part touched `src/pipeline/{bet_sheet,diagnostics,config}.py`, `src/eda/daily_prediction/dp_steps.py` (one path), `scripts/master_pipeline.ipynb`, `test/master_pipeline/`, `predictions/README.md`, `predictions/2026-10-12/` (new files only), `docs/studies/master_pipeline/{README,process_log}.md`, `docs/studies/daily_prediction/README.md` (one line), `docs/studies/README.md` (one row).
* [ ] (After 17:55) The repair: rebuild Stage 0 twice with `--out-dir`, with and without `event_rule` passed in `score_columns`, and compare (scratchpad `s0_compare3.py`): only the two Laver Cup 2026 matches differ.
* [ ] The data check: `tp.data_check(<a matchups CSV>)` twice (the second reuses the cache); `test_data_check_agrees_with_the_runs_own_gate`.
* [ ] Also touched after 17:55: `src/eda/predictability_diagnostic/stage0_build.py`, `src/eda/feature_alpha_audit/repair_data.py`, `src/pipeline/{readiness,__init__}.py`, `test/predictability_diagnostic/test_stage0_build.py`, `docs/decisions/2026-10-13-match-tiebreak-reading.md` and the decisions index.

## P2.8 Reproduction

```
./python.sh -m pytest test/master_pipeline -q                       # 29 tests, ~20 s, offline
# the 11 Oct sheets, rebuilt at their own times (writes a new set each call, _2 if the minute's name exists):
./python.sh -c "import datetime as dt, sys; sys.path.insert(0, '.'); import src.pipeline as tp; from pathlib import Path; \
run = Path('data/studies/daily_prediction/runs/live_2026-10-11_110150'); \
tp.bet_diagnostics(run, reprice_file=run / 'reprice_2026-10-11T182622Z.csv', stake_rule='owner_8oct', \
now=dt.datetime(2026, 10, 11, 18, 26, 22, tzinfo=dt.timezone.utc))"
# (after 17:55) the repair's footprint: Stage 0 before (code without event_rule) and after, into two folders, compared
./python.sh src/eda/predictability_diagnostic/stage0_build.py --out-dir <scratch>/s0_after          # ~100 s each
./python.sh -m pytest test/predictability_diagnostic/test_stage0_build.py test/feature_alpha_audit/test_data_repairs.py -q
# the data check on the 11 Oct matchups (builds or reuses data/studies/master_pipeline/data_check/stage0)
./python.sh -c "import sys; sys.path.insert(0, '.'); import src.pipeline as tp; \
tp.data_check('data/studies/master_pipeline/matchups/matchups_2026-10-11_110135.csv')"
```

---

# Part 3 (13 Oct 2026): the first live day of 14 Oct, and TabPFN-3.5-Thinking's 2026 season fit

Kept by Claude Opus 5.5 (`claude-opus-5-5`), Claude Code in VS Code, peer name `tennis-predictions-b7`. Local time PDT
(UTC−7), read from the clock.

## P3.1 The requests

* **First (about 16:30 PDT),** with a screenshot of a sportsbook's ATP Shanghai lines (Jodar v van de Zandschulp,
  Auger-Aliassime v Ruud, Tsitsipas v Medvedev, Bergs v Paul, De Minaur v Zverev):
  > "Are we ready and able to predict on the attached images? the upcoming ATP mens matches?"
* **Second (about 17:50 PDT):**
  > "Train tabpfn3.5 thinking on the same model as the tabpfn3.5 non thinking model. Dont calibrate the thinking one
  > and see the predictions on these 5 fights"
* **How the second was read:** "the same model" = the active instance `template_2026-10-10`: its 57 inputs and
  exactly the local fit's training rows for season 2026 (2013–2025, 62,869 rows); the guard's fixed settings (8
  estimators, softmax temperature 0.9, pretraining limits ignored, random_state 0, thinking effort high, metric log
  loss). "Train" = this layer's one paid season fit (`thinking.fit_season(..., spend_tokens=True)`), read as the
  owner's approval of that spend (README decision 1). "Don't calibrate" = no stage 2 slope; the reported number is
  Thinking's own probability, symmetrised over the two orientations as the local fit is (and as the 8 Oct Thinking
  study reported it, "Not calibrated"). The serve-speed term (stage 2's other half) is shown beside it, labelled, not
  headlined. "These 5 fights" = the five matches of today's two live runs (`live_2026-10-13_163937`, R16 of 14 Oct;
  `live_2026-10-13_165316`, the QF of 16 Oct): the same live rows the local model predicted.
* **Readings set aside:** a walk-forward of Thinking over past seasons (not asked; ~1.3M tokens); several seeds
  (the guard's config is seed 0; each seed is a new paid fit); calibrating Thinking (the owner said not to).

## P3.2 Chronology (Part 3)

| When | Step | Why | Results seen by then | Output |
|---|---|---|---|---|
| 16:33–16:53 | Readiness: `status()`, a Pinnacle pull (16:37), the five matches linked (four R16 of 14 Oct, the QF of 16 Oct); peers checked (`data_gaps_2026` editing `additions.py`; `unpriced_leads` wiring a switched-off adjustment into `dp_predict.py`) | The owner's first question | none | — |
| 16:39–16:53 | `predict_day` on the four R16 matches (run `live_2026-10-13_163937`, 809 s; 7 men's IOS parts recomputed in full, every other part resumed; gate: 4 of 4 may be bet). The QF kept for its own run (a later day: placeholder rows were feared to reach its inputs; on reading `live_rows.outcome_removed`, live rows carry no box score, so the shared run would most likely have been safe) | Bet day | none | `predictions/2026-10-14/` |
| 16:53–17:07 | `predict_day` on the QF (`live_2026-10-13_165316`, 811 s; gate 1 of 1); reprice of both runs from a 17:07 pull; bet sheets with the screenshot's prices as a venue | Bet day | the runs' predictions | `predictions/2026-10-14/`, `predictions/2026-10-16/` |
| 16:53 | Checks on the R16 run: accepted additions 1,725 as on 11 Oct (`additions.py` last written 16:28, before the run's merge at 16:43); no adjustment keys or columns from `unpriced_leads` in provenance or predictions; `adjustment.json` "off" | Peers' edits | the runs | — |
| 17:55 | `thinking.fit_season(instance, 2026, daily_matches=5)`, the free quote: **refused before any model call**: HTTP 401 "Invalid authentication credentials" | Step 1 | none | `prepared.json`, `train.npz` (62,869 × 57, `train_sha256` 5caded0a…) |
| 17:56–17:58 | Diagnosis: the VS Code process's `TABPFN_TOKEN` equals the client's cached login (2 Oct) and is rejected (401); the Windows user-scope `TABPFN_TOKEN` differs and is accepted (HTTP 200), as the 8 Oct Thinking study found. **Failure (mine):** a PowerShell helper named `H` resolved to the built-in alias for `Get-History`, so both keys' values were echoed into this session's tool output. Reported to the owner at once, with the advice to revoke both and issue a new key | Unblock the quote | none | — |
| 17:58 | The quote again, the user-scope key passed to that process only: fit 727,604 quoted; a prediction of 5 matches × 92 prices × 2 orientations (920 rows) 126,286 quoted; remaining 5,000,000 today, 16,238,035 this month. Past bills were 25% of the quote (8 Oct study: 169,141 billed against 676,563, 338 s) | Step 1 | none | `quote_*.json` |
| 17:59–18:07 | **The paid fit** (`thinking.fit_season(..., spend_tokens=True)`, the user-scope key passed to that process only): submitted 00:59:26Z, complete 01:07:44Z (504 s); fitted train set `01a137eb-db7f-7cb3-adad-9e5ad9a2feb0`; **181,901 tokens** (25% of the quote); month 3,943,866 of 20,000,000 used | The owner's request | none | `fit.json` and receipts in `thinking/template_2026-10-10/season2026/` |
| 18:00–18:02 | Wrote `src/eda/thinking_live_compare/` (`query.py`, `predict_api.py`, `compare.py`): a one-off comparison, not a prediction path. The query is `dp_fit.season_jobs` on the two runs (each match at the 91 grid prices and its own, stored then swapped), with the season's training rows checked against the fit's `train_sha256` and its columns against the fit's | So Thinking sees exactly the local model's live rows | none | code |
| 18:01 | `query.py`: 920 rows (R16 run 736 from row 0; QF run 184 from row 736); training rows equal to the fit's for both runs; `query_sha256` 46f56d8c… | — | none | `season2026/live_2026-10-13/query.*` |
| 18:08 | `predict_api.py --spend-tokens`: one POST (slot 01:07:59Z, complete 01:08:29Z); **31,572 tokens**; served package 9.0.0, billing model v3.5, execution mode "thinking" | — | none | `predictions.npz`, `predict_complete.json` |
| 18:09 | `compare.py`: Thinking symmetrised (seed 0), at each run's latest bet-sheet price (the 17:07 Pinnacle pull, unchanged from the runs' own prices), beside the local model; expected profit at Pinnacle's odds and at the screenshot's | — | **first look at Thinking's numbers** | `comparison.csv` |
| 18:10 | Read the 8 Oct Thinking study's headline (58 inputs): Thinking uncalibrated ties the calibrated local model (−0.01 [−0.30, +0.27] mLL, 2022–26) and in money at Pinnacle's close (+1.55% against +1.50%); its slope 0.987, the local twin's 0.909 | Context for the report | the comparison | — |

## P3.3 Judgment calls

1. **Uncalibrated = no stage 2 slope; the headline is Thinking's own symmetrised probability.** The serve-speed term
   (stage 2's other half, the 8 Oct research rule's offset) is computed beside it (`thinking_speed_a`) and reported as a
   side line only. Chosen before the results (§ P3.1).
2. **The full price grid in the one prediction** (920 rows, 126,286 quoted, 31,572 billed) rather than the own prices
   alone (10 rows): a later price is read off the stored curve without another paid call, as the local runs do.
3. **The user-scope key passed per process** (the 8 Oct study's practice), never written to a file or the shared
   environment. The exposure at 17:57 was mine (§ P3.2); the owner was told at once.
4. **Seed 0 only** (the guard's fixed configuration; each seed is a new paid fit). The local model's 16 seeds spread
   0.4–0.5 points on these matches; Thinking's single-seed noise is not measured here.

## P3.4 Claims and their evidence

| Claim | Evidence | Status |
|---|---|---|
| Thinking was trained on exactly the local model's 2026 training rows and inputs | `prepared.json` / `fit.json` `train_sha256` 5caded0a… equal to the rows `dp_fit.season_jobs` builds for both runs (`query.py`'s check) | observed |
| The query is the local model's live rows of the two runs | `query.py` builds it with `dp_fit.season_jobs`; segments in `query.json` | observed |
| Thinking's five forecasts and their expected profit | `comparison.csv` | observed (one seed; a forecast, not a result) |
| Thinking and the local model are not known to differ in quality | `docs/studies/tabpfn_thinking58/README.md` (58 inputs, 8 Oct) | another study's evidence, not re-measured on the 57 inputs |
| The local model's Bergs edge comes mostly from its calibration slope | p_base 0.3422 → logit −0.6535; × 0.9004 + 0.0369 × 0.419 → 0.3606; without the slope 0.3457 | computed from `predictions.csv` and the stage-2 coefficients |
| Cost: 181,901 + 31,572 = 213,473 tokens | `fit.json`, `predict_complete.json` | observed (the account's daily counter) |

## P3.5 Weak points

* One Thinking seed against sixteen local seeds.
* The 8 Oct tie was measured on the 58 inputs; this fit is on the 57 (ios_points_short dropped). Its quality on the 57
  inputs is not measured: a walk-forward over past seasons would need a paid fit per season (~1.3M quoted tokens).
* The Thinking forecasts sit beside a decided model; they earn no edge credit and decide nothing.

## P3.6 Reproduction

```
OUT=data/studies/master_pipeline/thinking/template_2026-10-10/season2026/live_2026-10-13
RUNS="data/studies/daily_prediction/runs/live_2026-10-13_163937 data/studies/daily_prediction/runs/live_2026-10-13_165316"
./python.sh src/eda/thinking_live_compare/query.py --out $OUT $RUNS           # free; refuses other training rows
./python_tabpfn.sh src/eda/thinking_live_compare/predict_api.py --out $OUT     # reads the saved probabilities back
./python.sh src/eda/thinking_live_compare/compare.py --out $OUT $RUNS         # the comparison, offline
```

---

# Part 4 (14 Oct 2026): a bet day from a screenshot, three failed runs, and the runner's environment fix

Kept by Claude Opus 5.5 (`claude-opus-5-5`), Claude Code in VS Code, session `fde0b675-7704-4ccc-8a96-9aa9cb886955`.
Local time PDT (UTC−7). No context summary occurred.

## P4.1 The requests

* **First (about 12:15),** with a screenshot of a US book's ATP Shanghai QF lines (Paul +170 / Medvedev −195, Ruud +116
  / Jodar −136, Davidovich Fokina −120 / Gea +100, De Minaur +174 / Zverev −200; all "Tomorrow, 6–7 PM"):
  > "generate predictions using the same code that the master pipeline would for the matches ive taken a picture for,
  > they are upcoming. Any issues with doing so?"
* **Later:** "why is this taking so long?"; "Was there not a minimum EV bar we applied to bet? or has that not been
  applied?"; "thes screenshot I showed you had medvedev not at -195, where did you get -195 from?"; "So the price
  moved on me in the time it took you to do this analysis. Why did we have so many failed runs?"; then, to my offer
  to fix the runner, "Make it".
* **How the first was read:** the notebook's cells A1–A6 through `src/pipeline/`, called from scratchpad scripts
  (`a3.py`: A3 + A3b; `a4.py`: A4; `a6.py`: A6 with the screenshot as a venue, as on 13 Oct), not a second path.
  The model is fed Pinnacle's margin-free price (the decided rule); the screenshot's prices only give EV at that book.

## P4.2 Chronology (PDT)

| Time | What | Results seen at the time |
|---|---|---|
| 12:22–12:27 | Template check (template_2026-10-14 OK); A1 (fetched at 07:30, nothing ran); A2; B2 (TML again) | Pinnacle lists all four QFs; Gea v Davidovich Fokina starts 23:30 PDT tonight and Zverev v De Minaur 03:00, not "tomorrow" (Thursday in Shanghai; the ATP's Wednesday order of play confirms the R16 split). Medvedev v Paul left out: TML's ATP file last changed 08:30Z, before Medvedev–Tsitsipas and Paul–Bergs |
| 12:29 | A3 + A3b for the 15 Oct pair | both ready |
| 12:33 | Run 1 (`live_2026-10-14_123349`), launched with PowerShell `Start-Process` of the tennis env's python.exe | died at 12:46 in the states step; the engine's cleanup left one file held by two orphaned workers |
| 12:52–12:58 | Repository data checked intact; orphans stopped; leftover moved into the run folder, empty folders removed; **retried unchanged** (the death coincided with a session unlock) | a judgment error: no diagnosis first |
| 12:58 | Run 2 (`…_125827`) | the same death, same place: systematic |
| 13:11–13:53 | No traceback; no Windows crash record; memory ample (≥ 35 GB commit free, `memlog`) | the leftover-file lock is a consequence, not the cause |
| 13:53 | Run 3 (`…_135305`) with `PYTHONFAULTHANDLER=1` and an exit-code watcher | exit **0xC06D007F** (delay-load: procedure not found); the tracer: an IOS worker in `numpy.linalg.norm`, then the main in `numpy.linalg.solve` (`stage4_features.fit_slope`) |
| ~15:00 | 5-second test: the tennis python with PowerShell's PATH crashes on `np.linalg.solve`; with the env's folders first (or conda base's, as Git Bash has) it passes | cause: the launch, not the pipeline or the data. Git Bash's profile activates conda base; the 13 Oct runs and the morning replay were launched from it |
| 15:12 | Run 4 (`…_151255`), conda base's folders prepended | ok, 1,057 s; both 15 Oct matches PASS |
| 15:13 | TML's ATP file changed at 21:18Z: Medvedev and Paul's R16 rows present; A2 again links all four | — |
| 15:31 | Run 5 (`…_153110`, 16 Oct: Jodar v Ruud, Medvedev v Paul) | ok; A6 at 15:48: BET Medvedev (+0.6% at Pinnacle), BET Jodar (+0.5%), both under the sheet's 1% "thin" label |
| 16:20–16:37 | The fix (below): tests first, failing on the old runner; then the fix; 46 of 46 pass | — |
| 16:42 | Run 6 (`…_164201`) launched exactly as runs 1–3 (PowerShell's own PATH, no conda) with the fixed runner | ok, 1,140 s: states 442 s, the local-env fit 54 s. Jodar v Ruud at the same price as run 5: p_base and q equal to 10 decimals |

## P4.3 The fix and its judgment calls

* **`runner._activated_path`:** each step's PATH gets its own environment's folders first (`<env>`,
  `Library\mingw-w64\bin`, `Library\usr\bin`, `Library\bin`, `Scripts`, `bin`), as `conda activate` sets them;
  Windows only; nothing else in the environment changes.
* **The child in another environment** (dp.py's fit in tennis-tabpfn-local inherits the tennis step's PATH) was tested
  before choosing this: with the fit's import order (numpy and pandas, then tabpfn and torch) the local environment
  loads under the tennis environment's folders, its own, or base's, and fails under a bare PATH.
* **Rejected:** conda's `CONDA_DLL_SEARCH_MODIFICATION_ENABLE` (no effect in this conda-forge build: all three
  environments still crashed under a bare PATH).
* **Found, not fixed:** in the local environment, torch's CPU maths and numpy's linear algebra in one process abort
  with OMP Error #15 under every PATH, activated or not (two OpenMP runtimes). The fit computes on the GPU and does not
  hit it; the test leaves torch's CPU maths out and says why.
* **Separate runs per day** (the 13 Oct precedent: a later day's inputs never see a placeholder result).

## P4.4 Claims and their evidence

| Claim | Evidence | Status |
|---|---|---|
| The three failures were the launch's missing conda folders | exit 0xC06D007F in numpy.linalg (fault tracer, run 3); the 5-second A/B test; run 4 passing with base's folders | observed |
| The fix stops it from any shell | `test_runner_env.py`: 7 pass with the fix, 7 fail with `_activated_path` switched off in memory; run 6 end to end from a bare PowerShell | observed |
| The fix changes no prediction | run 6 = run 5 for Jodar v Ruud at the same price (10 decimals) | observed |
| The other tests still pass | `pytest test/master_pipeline`: 46 passed | observed |

## P4.5 Weak points

* The exact library behind 0xC06D007F was not named; the diagnosis rests on behaviour (PATH with or without the
  environment's folders), reproduced both ways.
* Only the notebook layer is fixed. `dp.py` started by hand from a shell without conda still crashes; the engine
  belongs to the daily_prediction session (a recommendation for it, not done here).
* Left for the owner: the three failed run folders (6.1 GB, no predictions) await a yes before deletion.

## P4.6 Reproduction

```
./python.sh -m pytest test/master_pipeline/test_runner_env.py -q      # 7 tests; ~10 s
# the end-to-end check: from PowerShell, with no conda environment active,
#   Start-Process <envs\tennis\python.exe> <a script calling tp.predict_day(MATCHUPS, model="tabpfn35")>
```

## P5. GPU guard: Jupyter interrupt helper (18 Oct 2026)

Owner's request, verbatim:
> **Fix the GPU guard to exclude the Jupyter interrupt helper**, while retaining checks for actual competing training processes and available GPU memory. Avoid killing the helper or disabling the guard entirely.

Interpretation: change the daily fit's shared `training_window.fits` guard and the notebook's preflight warning;
do not stop any process, relaunch predictions, or change model/data behavior. This session has no exposed session ID.
Evidence already seen: `live_2026-10-18_105406/fit.log` waits for PID 53492 with 30.3 GB free; the notebook identifies
that PID as VS Code's `vscode_datascience_helpers/kernel_interrupt_daemon.py --ppid 27060`. The fit guard counts
all local-env Python processes; the notebook separately enumerates the local interpreter with psutil.

Plan: first reproduce the helper false positive in regression tests, then share a narrow helper-command predicate
between the two scans. Keep ordinary kernels/training scripts blocked, current-process exclusion in the fit guard,
and the existing free-memory threshold and timeout. Verify these cases with simulated processes/memory, without
starting a fit or using the GPU; record results below. No feature timing or prediction rules change.

Implementation and checks so far:
* Before the fix, both helper-path regression variants failed: `other_local_processes()` returned `[53492]`.
* Added one shared predicate for the exact helper-script invocation plus `--ppid <positive PID>`; it handles quoted
  Windows paths, path separators and casing. Merely mentioning the helper as a training argument does not exclude
  that job; unknown invocations and ordinary ipykernels remain blocking.
* Kept the fit guard's existing CIM environment filter and own-PID exclusion. CIM now returns command lines with
  PIDs as JSON so the predicate can filter the helper. The notebook's psutil scan uses the same predicate. The
  `wait_for_card` loop, memory threshold, retry cadence and timeout are unchanged.
* Initial focused run: 14 passed. Expanded run (20 guard cases plus existing master-pipeline and training-window
  tests): 114 passed, 13 fixture errors from access denied to the default pytest temp directory, and one linker
  assertion failure (`test_linker_on_the_probe`: expected at least 20 reasons containing "already played", got 0;
  rows now report that the event's final is played). Retrying the failing/error cases in a fresh workspace temp
  directory; no product change made for these unrelated test issues.

Final verification: **20 focused guard tests passed** (`./python.sh -m pytest
test/master_pipeline/test_gpu_guard.py -q -p no:cacheprovider`). Tests cover the observed unquoted command,
quoted paths with spaces, Windows casing/separators, mixed helper/training processes, ordinary kernels, own PID,
empty/single-object CIM output, unknown commands, insufficient memory, the 12 GB boundary, timeout, and waiting
until a real job exits while the helper remains alive. GPU memory is simulated; no CUDA allocation or fit ran.
The broader retry still had 13 temp-directory permission errors even with a fresh workspace base path, and the
same linker assertion failure (19 passed). `git diff --check` passed on changed tracked source and this log.

Review/reproduction: inspect the narrow shared command predicate and both callers; run the focused command above.
The existing environment-selection rules and memory gate are preserved. A future helper launch signature may need
another explicit case: unknown signatures remain blocking. The guards still have their existing separate scan
mechanisms (CIM versus psutil), and process enumeration failure behavior was not redesigned here. This change was
not verified by an end-to-end prediction run. No helper or running prediction was killed, restarted or modified;
already-loaded Python code must be started afresh to use the fix. Existing unrelated worktree edits were preserved.

---

# Part 6 (20 Oct 2026): TabPFN-3.5-Thinking beside the local model, their 50/50 ensemble, US odds only

Kept by Claude Opus 5.5 (`claude-opus-5-5`), Claude Code in VS Code, session `8deb79df-d266-484f-86d1-bc08542c9e4f`
(peer name `tennis-predictions-97`). Local time PDT (UTC−7). Opened 06:05, before any code was changed.

## P6.1 The request (verbatim)

> Via steps A1-A5 in the master_pipeline.ipynb I attempted to run a tabpfn3.5 thinking run for the newest model.
> The intention is to have a tabpfn 3.5 paid thinking version I can run IN ADDITION to the tabpfn3.5 nonthinking
> version, so I can see their results side by side in the tennis bet sheet.
>
> So its EITHER the nonthinking-calibrated version OR ( the thinking-noncalibrated version AND nonthinking-calibrated
> version) that's output in the display.
> You can remove the european/decimal odds from the run notes that are output from step A5.
> We only need US odds. Convert lowest odds to take into american as well.
>
> We'll use basically a 50/50 ensemble to calculate edge/expected profit.
> So nonthinking chance without patterns,
> thinking chance without patterns,
> ensemble chance without patterns,
> Would add two columns and reduce one after we get rid of the decimal odds column.
> Then the other columns are recalculated to consider the ensemble.
>
> The pipeline is not set up properly to handle tabpfn3.5 thinking at the moment either. The only difference between
> that model and the nonthinking is how its called (the API) and that we do not calibrate those probabilites, we use
> the probabilities given to us from the API. The pipeline is not set up properly to use this.
>
> Fix that.

The owner pasted another LLM's answer (A4 refused with `NotImplementedError(THINKING_WAITS)` before any API call;
make a 2026 Thinking fit for the active instance; set `spend_tokens=True`), with: "use the info only if you think its
accurate". Checked against the code: accurate. A4's guard (`predict.py`, `dp_takes_thinking()`) refused because the
daily engine had no Thinking option; the only Thinking season fit is `template_2026-10-10`'s, and the active instance is
`template_2026-10-16` (`selected_instance.json`), whose training rows differ, so a new paid season fit is needed.

## P6.2 Interpretation acted on

* **Two displays.** `MODEL = "tabpfn35"`: the current best model alone, unchanged. `MODEL = "tabpfn35_thinking"`: the
  same local run **plus** one paid TabPFN-3.5-Thinking prediction of the same live rows; never Thinking alone. The
  existing name is kept (the owner's kernel already uses it); its meaning becomes "both".
* **Thinking uncalibrated** (the owner, again as on 13 Oct): its chance is the API's probability, with no stage 2 at
  all, neither the calibration slope nor the serve-speed term. It is symmetrised over the two orientations, as the
  local fit is and as the 13 Oct comparison did: that is how the model is queried (the decided fit's
  "symmetrised"), not a calibration.
* **The same model otherwise:** the active instance's 57 inputs and exactly the local model's training rows for the
  season (2013 .. Y−1; `train_sha256` checked against the season fit's), the same query rows (each match at the 91
  grid prices and its own, stored then swapped), the guard's fixed settings (8 estimators, temperature 0.9).
* **Seed 0 only** (my assumption, to be confirmed): the season fit is one paid fit with `random_state` 0. Sixteen
  seeds would be sixteen paid fits and sixteen times each day's call.
* **The ensemble** = the plain average of the two chances without patterns: 0.5 × local stage-2 chance + 0.5 ×
  Thinking's chance (a linear pool; "basically a 50/50 ensemble"). The five-pattern adjustment, while on, is added to
  the ensemble's log-odds as it is to the local model's today (logit q += b·z). "Model chance", edge, expected profit,
  the pick, the lowest odds to take, the break-even prices and a reprice all use the ensemble.
* **The sheet's columns** (Bet sheet, a Thinking run): the decimal "Odds" column removed; "US odds" kept; "Lowest odds
  to take" in US odds; three chances without patterns (non-thinking, thinking, ensemble) where one stood. Net +1
  column, as the owner counted. "Only US odds" is applied everywhere the sheet shows odds (Notes, the Matches and Not
  predicted sheets, a venue's price), not only in that table. The machine record keeps its decimal columns (EV is
  computed from them; the record's columns are never removed).
* **Where it is built:** inside the daily engine, as a `--thinking` step of `run_day` (the engine is the one prediction
  path: CLAUDE.md "Do not build a second prediction path"; the 11 Oct agreement put Thinking's daily call there). The
  paid season fit stays in `src/pipeline/thinking*.py`; A4 makes it first when the active instance has none for the
  season (with `spend_tokens=True`).

**Readings set aside:** Thinking alone in the sheet (the owner: "EITHER … OR (… AND …)"); calibrating Thinking (the
owner: not to); an average in log-odds (the owner said 50/50; a linear pool is the plain reading); the patterns applied
to each model before averaging (the owner lists the chances "without patterns" and one model chance after them);
several Thinking seeds (cost).

## P6.3 Plan, each with its check

1. Engine (`src/eda/daily_prediction/`): `dp_thinking.py` (query from `dp_fit.season_jobs` with the fit's
   `train_sha256` checked; the one paid POST through the project's guard in the tennis-tabpfn env, slot written before
   it, never repeated; the answers symmetrised into a grid and an own price); `dp.py run_day --thinking --spend-tokens`
   and a `thinking` step; `dp_predict` writes the ensemble as `q_a` with the local and Thinking chances beside it, in
   `predictions.csv` and `curves.parquet`; `reprice` and `grade` read the new curves. A failed Thinking call leaves the
   local model's predictions, said loudly. Check: tests with a fake backend; the 13 Oct paid answers replayed through
   the new step offline (no token): its query must equal 13 Oct's rows bit for bit and its chances `comparison.csv`'s.
2. Layer (`src/pipeline/`): `predict_day` passes `--thinking --spend-tokens`, makes the missing season fit first;
   the record and the sheet show the three chances and US odds only. Check: the bet-sheet tests, rewritten for US
   odds, plus a Thinking run's sheet.
3. Notebook: `SPEND_TOKENS` in Setup, A4 passes it, comments say what each switch does. Check: the notebook test
   (valid, no outputs, every `tp.` call exists) and a dry run.
4. A free quote for the active instance's 2026 fit (no token spent: it checks the key works here and gives the cost).
5. No paid call from this session: the owner runs A4.

**Results seen before these choices:** the 13 Oct comparison (`thinking/template_2026-10-10/season2026/live_2026-10-13/
comparison.csv`: five matches, Thinking within 0.4–1.9 points of the local model's final chance); the 8 Oct Thinking
study's headline as quoted in Part 3 (uncalibrated Thinking level with the calibrated local model, 2022–26, 58 inputs).
No new Thinking number was produced before the plan was fixed.

## P6.4 Chronology (PDT)

| Time | Step | Results seen by then | Output |
|---|---|---|---|
| 06:00–06:05 | Read the notebook, `src/pipeline/`, the engine's fit and predict steps, the 13 Oct one-off (`src/eda/thinking_live_compare/`), the guard. Token check (hashes compared, nothing printed): the process's `TABPFN_TOKEN` equals the user-scope one (Part 3's 401 is gone) | the 13 Oct comparison | — |
| 06:05 | This part opened, the plan fixed (above) | same | — |
| 06:06–06:14 | Engine: `dp_thinking.py` (new); `dp.py`, `dp_steps.py` (`--thinking`, `--spend-tokens`, the `thinking` step, `thinking-send`, a failed call kept apart), `dp_predict.py` (the ensemble), `reprice`, `grade`; `dp_common.py` (`PY_API`, `THINKING_FITS`). Layer: `predict.py`, `thinking.fit_state`, `config.py`, `diagnostics.py`, `bet_sheet.py` (US odds, the three chances) | none new | code |
| 06:15 | Offline check on a scratchpad copy of `live_2026-10-19_173201` (`template_2026-10-16`; its stage-2 record current, so nothing shared was written). The local re-run equals the run's own `predictions.csv` bit for bit, every numeric column, `spd_L` included. With made-up Thinking answers: ensemble = plain average, patterns after, the curves likewise. The reprice's ensemble against the average of the two models read off their own curves: 6.8e-7. The sheet's three columns, ensemble = average to the record's 6-decimal rounding. One assertion of mine was too tight for that rounding | made-up Thinking numbers only | scratchpad |
| 06:17 | The 13 Oct paid answers replayed through the new step (scratchpad copy of `live_2026-10-13_163937`): the query equals 13 Oct's 736 rows bit for bit; the guard's flow with a stand-in answering the saved probabilities made one call, then read back; the read-back chances equal `comparison.csv`'s `thinking_own_price_a` exactly (max abs 0.0) | the 13 Oct numbers, already known | scratchpad |
| 06:18 | The step's subprocess into the tennis-tabpfn env: saved answers read back (exit 0); no answers and no `--spend-tokens`: refused, nothing written | — | — |
| 06:20 | **The free quote** (`tp.fit_seasons(model="tabpfn35_thinking", seasons="2026")`) for `template_2026-10-16`: authenticated. The training rows prepared: 62,869, `train_sha256` 3782beec…, not `template_2026-10-10`'s 5caded0a…. Fit quoted 727,604. A 30-match day quoted 136,939, against 126,286 for 5 matches on 13 Oct: the cost barely depends on the matches. 15,423,502 of 20M left this month | quote | `thinking/template_2026-10-16/season2026/` (prepared.json, train.npz, quote) |
| 06:22–06:30 | Tests. The engine's 6: three first failed on Windows' 260-character path limit under this session's deep scratchpad temp folder (a real run's receipt path is about 200 characters); they passed with pytest's default temp folder. The layer's file: 36 then 37 pass, and 1 fails, `test_linker_on_the_probe`, the failure Part 5 recorded (data drift: "final is played" where "already played" was expected) | — | — |
| 06:30–06:33 | Notebook: the intro, Setup (`SPEND_TOKENS`), A4, A5, C4, C9. Dry runs on the latest real matchups file (35 matches). The local setting's command is unchanged. Thinking without `spend_tokens` is refused. With it: template check OK, then the season fit planned (prepare, fit), then `run_day … --thinking --spend-tokens` | — | notebook |
| 06:33–06:39 | Decision record and its index row, both READMEs, the engine's log pointer, CLAUDE.md. Then all tests again on the final code (94 pass, the same 1 known failure). Both offline checks again. `read` reordered (the record before `thinking.npz`); its 6 tests pass. The written workbook opened: US odds signed (`+0;-0;0`), chances in %, the Run tab's Thinking line | — | docs |

## P6.5 Judgment calls (results seen when each was made: none new, unless said)

1. **In the engine, not the layer.** The engine is the one prediction path, and reprice and grade then see both models. The 11 Oct agreement put Thinking's daily call there. Ownership: the owner asked for it.
2. **A failed Thinking call gives the local model's predictions, said loudly, not a failed run.** The local model is the decided one, and a run costs 10–20 minutes. A4 prints the failure in capitals, and the sheet's first run note says it. The alternative, failing the run, was set aside: it leaves no sheet.
3. **A4 makes a missing season fit itself** (with `spend_tokens=True`, after the free checks, before the run), and prints it as PAID. Without the fit no Thinking run is possible; it is made once per instance and season. A departure from "C9 by hand"; C9 stays for a quote or a fit ahead of a bet day.
4. **Thinking's call comes after the local fit.** No token is spent on a run whose local fit failed.
5. **`SPEND_TOKENS` is a Setup switch, False by default**, and `MODEL`'s default stays `"tabpfn35"`. The flag is the existing spend guard made visible.
6. **US odds everywhere the sheet shows a price**: the table, Notes, Matches, Not predicted, a venue's price, the stake rule's wording. The record keeps decimal odds: expected profit is computed from them, and its columns are never removed.
7. **Defaults for the owner to confirm**, in the decision record: seed 0, the linear pool, the patterns after the average. The latter two are measured there: 0.17 points apart near 50%, 0.71 at 10/20%; 0.05.
8. **The permanent test does not assert the 19 Oct file bit for bit.** A later correction of the shared speed panel may legitimately move `spd_L`. That equality is recorded here as today's one-time check; the test checks the local run's schema and that the ensemble reproduces the same code's local numbers.

## P6.6 Claims and their evidence

| Claim | Evidence | Status |
|---|---|---|
| A run without Thinking is unchanged | the 19 Oct copy re-predicted bit for bit (06:15, again 06:36); the schema test | observed |
| Thinking predicts exactly the local model's rows, trained on exactly its rows | `build_query` = 13 Oct rows bit for bit; `train_sha256` checked against the fit (a mismatch refused: test) | observed |
| The read-back equals the paid answers' symmetrised chances | 13 Oct replay, max abs 0.0 | observed |
| The prediction used is the plain average, the patterns after it | `test_the_prediction_used_is_the_average_of_the_two_models` (1e-15, 1e-12) | observed, on made-up Thinking numbers |
| The paid call is guarded (refused without the flag, slot before the call, never resent, an unknown outcome refused) | `test_the_paid_call_is_guarded`; the API-env subprocess checks | observed with a stand-in backend |
| The key works from this environment | the 06:20 quote | observed |
| A paid run end to end | not made: the owner runs A4 | **not observed** |

## P6.7 Weak points; where a flaw would hide

* **No paid call was made here.** The API's answer to a run's real query is not observed (35 matches: 6,440 rows; 13 Oct's 920 took 28 s), nor its time.
* **The ensemble is unmeasured on past seasons**, and the pattern adjustment's size was measured on the local model alone.
* **Seed 0 only:** Thinking's seed noise is unknown.
* **The fallback** keeps a sheet when Thinking fails. A reader who misses the warning would bet on the local model alone, which is the decided model, not a wrong one.
* **Paths:** a receipt's path is about 200 characters. Moving the repository deeper would cross Windows' 260 limit, as the scratchpad tests did.
* **Where a flaw would hide:**
  * the orientation of Thinking's answers (checked only against 13 Oct, where both sides used the same code);
  * the reprice's independent interpolation of each curve (6.8e-7 apart here).

## P6.8 What a re-design would do

* Measure the ensemble first: paid walk-forward Thinking fits of 2022–2025. Or, for free, read the 8 Oct study's saved Thinking forecasts (58 inputs) beside its local twin.
* Run the Thinking call beside the local fit, not after it: it saves about a minute, but spends tokens on a run whose local fit may fail.

## P6.9 Reviewer checklist

* [ ] `dp_thinking.send`: the slot is written before the POST, never resent, refused without `--spend-tokens`.
* [ ] `dp_predict.run` with `thinking=False` takes exactly the old path.
* [ ] The sheet shows no decimal odds: the table, Notes, Matches, Not predicted, the header.
* [ ] `predict_day`: every free check before the paid fit, the fit before the run.
* [ ] The decision record's defaults stated as defaults.

## P6.10 Reproduction

```
./python.sh -m pytest test/daily_prediction/test_thinking.py -q          # 6 tests, offline (the 13 Oct replay, the 19 Oct copy)
./python.sh -m pytest test/master_pipeline -q                            # the sheet, the switch's dry runs
# the dry run of a Thinking day, nothing paid:
./python.sh -c "import src.pipeline as tp; tp.predict_day('<matchups csv>', model='tabpfn35_thinking', spend_tokens=True, dry_run=True)"
```

## P6.11 The owner's answers, the log-odds average, and "why train through 2025?" (08:35–08:45)

**The owner (verbatim):**
> "one seed for thinking, averaging in log odds not a plain average, pattern adjusted after averaging is correct.
> What's this !? [the A4 output: the season fit's `prepare` JSON, `"train_through": 2025`] Train through 2025?? wheres
> all the 2026 matches and why arent they part of the training?"

**State found at 08:35.**
* The owner's A4 had made the season fit of `template_2026-10-16` at 08:16–08:23: fitted train set `01a159e2…`, 181,901 tokens, the same as 13 Oct's bill.
* Its run `live_2026-10-20_081558` (23 matches, `--thinking --spend-tokens`) was in its tables step. Its predict step runs in the repository's process and imports `dp_predict` when it starts, so a change made before then is the one the run uses.

**The change (08:35–08:38), before that step.**
* `dp_predict.log_odds_mean`: logit q = ½ logit(local stage 2) + ½ logit(Thinking), then the patterns.
* Compiled in both environments. The engine's 6 tests pass, rewritten for the log-odds average:
  * a check that it is not the plain average;
  * the reprice's ensemble now equal to the log-odds average of the two re-read curves to 1e-12, since interpolation in log-odds is linear.
* The layer's 14 sheet and Thinking tests pass.
* The wording "plain average" was replaced in the sheet's header and glossary, the code's docstrings and help text, the decision record (its defaults table now records the three answers), the index row, CLAUDE.md and both READMEs.
* **Not edited:** the notebook. It was open in VS Code with A4 running, and a change on disk could collide with the open copy at its next save. Its intro still says "the plain 50/50 average"; to fix once the owner is done with it.

**The question.**
* `train_through: 2025` is the current best model's annual protocol: season Y trained on 2013 .. Y − 1 (CLAUDE.md, "Fit"). The local model's 2026 fits are trained the same way, and Thinking mirrors them, as the owner specified.
* The 4,357 frame matches of 2026 (`season_matches`) are predicted, not learned from. Their results still reach every prediction through the inputs, which each run recomputes on the day's tables.
* **The owner had decided otherwise on 9 Oct:** "Live fits grow within the season" (`2026-10-08-current-best-model.md`, the adoption-by-change-class point 7). That is 2013 .. Y − 1 plus every season-Y match whose result counts by the run's cut-off; a guard before first use (a replay showing stage 2's calibration still fits such fits' forecasts); backtests and the frozen reference keep the annual protocol.
* It was never built (the daily prediction README, Limits).
* **What it would be worth:** about 0.001–0.01 mLL by late season. That is the adoption framework's learning curve through the training-window study's random-draw arms (`resolution_check.out`): an inference from three noisy points, robust in order of magnitude. The training-window study also found recent rows worth no more than old ones.

**Recommendation put to the owner:** build the in-season fit at the cadence of instance rebuilds, guard first.
* Each rebuild already makes new local fits and a new paid Thinking fit, so adding the season's played matches costs about 7% more rows.
* Daily refits would cost about 180k tokens a day for Thinking and minutes of GPU a day, for a gain no comparison can see.

## P6.12 The first paid Thinking run, checked (08:47–08:52)

`live_2026-10-20_081558` (the owner's A4) ended at 08:47:33, exit 0, 1,447 s in all:

| Step | Seconds |
|---|---|
| tables | 795 |
| states | 183 |
| fit | 160 |
| patterns | 99 |
| thinking | 48 |
| predict | 0.6 |

Read from its files, nothing written:
* **The ensemble.** All 23 matches `ensemble` "on", the patterns on.
  * `q_a_patterns_off` equals the log-odds average of `q_a_local_patterns_off` and `q_a_thinking` to 6e-17; the plain average would have differed by 0.014 points at most here.
  * `q_a` is that average shifted by `pattern_shift` (1e-16).
* **The paid call.** 4,232 rows (23 × 92 × 2) on fit `01a159e2…`, 33,475 tokens on the daily counter.
  * Served: package 9.0.0, weights `tabpfn-v3.5-20260909.safetensors`, execution mode "thinking".
* **The two models.** Thinking minus the local model, side A: mean +0.31 points, sd 0.92, largest 2.0. The same player favoured in 22 of 23 matches. One day: a description, not a measurement.
* **The sheet, built in memory** (`write=False`): model `tabpfn35_thinking`, the designed columns.
  * All 23 matches BLOCKED at 08:50: 20 for a quote 37 minutes old (Pinnacle's pull of 08:11; the season fit and the run took 36 minutes); 2 started; 1 by the gate (inputs incomplete).
  * The decided 30-minute rule: A6's reprice pulls Pinnacle again and reads both models' stored curves at no cost.

# Part 7 (20 Oct 2026, evening): Thinking takes stage 2's serve-speed term, never the calibration

Kept by Claude Opus 5.5 (`claude-opus-5-5`), Claude Code in VS Code, session `dd0f8ec7-2146-47b2-9c8c-75b9d421eea0`
(a session planning the in-season retrain; this part is the one code change it made).

## P7.1 The owner's words, and the reading acted on

> "Tabpfn3.5 thinking should still move with the serve speed numbers wtf? just not the calibration."

Said on reading the session's remark that, with Thinking on, stage 2 shapes only the local model's half of the average.
* **Read as:** logit(Thinking's chance) = logit(the API's own) + b̃_Y · `spd_L`, the local model's b̃ for the match's
  season and speed feed, the same `spd_L`, 0 for women, slope 1. The ensemble then carries ½ s·η + ½ logit(API) + b̃·`spd_L`.
* **Why this reading:** it is the 8 Oct study's "Thinking + offset" and this README's own recommendation of 11–13 Oct
  ("η + the local b̃·spd_L, no slope"); Part 6 had recorded "no serve-speed term" from "we use the probabilities given
  to us from the API", which the owner now corrects.
* **Set aside:** a speed coefficient fitted on Thinking's own forecasts (needs a paid fit per past season); re-issuing
  the morning's runs (their records stand as made).

## P7.2 What changed

| Where | Change |
|---|---|
| `dp_predict.py` | `speed_only(coef)`: the coefficient sets with s_atp = s_wta = 1; Thinking's own and grid chances go through `apply_stage2` with it before `log_odds_mean`. `predictions.csv`: `q_a_thinking` is now Thinking with the term, `q_a_thinking_api` the API's own; the curves carry both; the provenance rule text and a `thinking_stage2` line |
| `dp_steps.reprice` | carries `q_a_thinking_api` too |
| `dp_thinking.py`, `src/pipeline/thinking.py`, `diagnostics.py`, `bet_sheet.py` (How to read) | descriptions |
| `test/daily_prediction/test_thinking.py` | the ensemble test computes Thinking's used chance itself from the run's recorded b̃ by feed and checks: the API's own kept, the men moved by b̃·`spd_L`, the women unmoved, the ensemble the log-odds average of the local chance and that one, the reprice consistent |
| Records | the decision's amendment, its index row, CLAUDE.md's rule line, this README's "What Thinking is", the daily prediction README, the notebook's introduction (also "the plain 50/50 average" corrected to the decided log-odds average) |

## P7.3 Checks

* `test/daily_prediction/test_thinking.py`: 6 of 6 pass, the ensemble test run, not skipped (its 19 Oct run: 22 men, all
  with `spd_L` ≠ 0).
* `test/master_pipeline`: 69 pass, 1 fails, `test_linker_on_the_probe`, the data-drift failure Parts 5–6 recorded; none
  of its code was touched.
* The notebook's introduction cell equals its old text exactly once the two phrases are put back (SHA-256 prefix
  `35b099a1cae49a15` both ways).
* No prediction run was in progress (process list); the other two tennis sessions were idle.

## P7.4 What it moves (read from files, nothing written to the runs)

* `live_2026-10-20_081558` and `live_2026-10-20_090046` (b̃ 0.03337, daily feed): the amended rule would move the men's
  ensemble chances by 0.29–0.30 points on average, 0.6 at most.
* The 09:14 sheet's decisions, recomputed as the sheet makes them (it reproduced all 19 BET/PASS rows): one changes,
  Darderi–Duckworth (starting 05:00 UTC on 21 Oct), from PASS to BET on Duckworth at +102: his chance 49.5% → 50.1%,
  expected profit −0.0002 → +0.011 a unit at the 09:14 price. The other 18 stand.
* An A6 reprice of the morning's runs reads their stored curves, so it keeps the morning's rule; a new A4 run uses the
  amended one.

## P7.5 Weak points

* b̃ was fitted jointly with the local model's slope on the local model's forecasts. Applied to Thinking's log-odds it
  assumes the speed effect beyond Thinking's forecast is the same; `spd_L` is in neither model's inputs, so the
  assumption is mild, but it is not measured.
* The ensemble with the term, like the ensemble without it, is not measured on past seasons and earns no edge credit.

## P7.6 Addendum: the engine's full test suite (finished 23:31 UTC)

* **First attempt, no result:** run with a 28-minute limit and its output piped through `tail`; the limit stopped it
  before anything printed (exit 143). Re-run with every result logged, no limit: 1 h 28 min.
* **37 passed, 3 failed.** The failures are the three that compare a replay of 13 Jul 2026 with the **10 Oct build**,
  the suite's default (its default tree `tnr_lyr_new` and `dp_common`'s default instance; the price-grid test names
  `template_2026-10-10/fits` itself):
  * `test_replay_reproduces_the_57_inputs`: 14 of 36 non-IOS inputs bitwise (36 asked); e.g. `ratings_iid` up to 0.57,
    `points_52w` up to 0.26;
  * `test_price_grid_matches_direct_prediction`: the replay's fit against that build's stored fits, up to 0.0081 (0.001
    asked); its three self-consistency asserts passed;
  * `test_changed_past_row_recomputes_through_the_steps`: Elo and forms recompute beside the IOS solves.
* **Read as:** the effect of repairs decided after that build (the Roland Garros box scores applied 13 Oct, the
  Tenerife dates, Tennis My Life's corrections; daily prediction process log Part 5: "Repairs decided after a build are
  not undone"). None of the three reads this part's code: they test the tables, states and fit steps, while this part
  changed only the predict step's Thinking branch and the reprice's column list. The fixture's own `run_day`, predict
  step included, finished with exit 0.
* **Not done:** pointing the suite at the build in use (`template_2026-10-16`, whose dump view the replay registry
  holds). The tests then guard an instance nobody predicts with; put to the owner as a recommendation.

---

# Part 8 (22 Oct 2026): tour-level qualifying into A1–A5

Kept by Claude Opus 5.5 (`claude-opus-5-5`), Claude Code in VS Code, session `40624dcb-dd11-4b33-9758-215a45a8677e`
(the session that ran the qualifying study, `docs/studies/qualifying_targets/`; this part continues after a context
summary, and its log was re-read first). Local time PDT (UTC−7). Opened 11:15, before any code was changed; the
reading of the code (about an hour) came first and is summarised in P8.3.

## P8.1 The request (verbatim)

> We've done enough tests to conclude we should be betting the qualifying rounds of 250+ tournaments.
> Build the acceptance of this into A1-A5 so we can predict on them using the live model

The conversation just before: the owner asked what the study's "refitted" version was; the answer was that both
versions are calibrated, that A1–A5 uses only the live model's calibration (learned on main draws), that the
qualifying-calibrated version existed only in the study's scoring code, and that A1–A5 also applies the five-pattern
adjustment, which neither test version included.

## P8.2 Interpretation acted on

* **"Qualifying rounds of 250+ tournaments"** = the study's population: the qualifying of the ATP and WTA 250s, 500s and
  1000s and of the four Slams (Stage 0's levels T250, T500, T1000 and GS with `qualifying`; Stage 4's groups TQ and
  GSQ), both tours. Challenger, WTA 125 and ITF qualifying stay out.
* **"The live model"** = the model A1–A5 runs today, unchanged: the active instance (training rows main-draw only), its
  16 seeds, stage 2 with the slope and speed coefficient fitted on main draws. Not the study's qualifying-calibrated
  variant, not the pooled arm M1, no retrain. A qualifying match's inputs are built as the study built them: level
  code TQ 6 / GSQ 7, round order Q1 1 / Q2 2 / Q3 3, best of 3 (5 where Stage 0 records 5 for a men's Slam
  qualifying match), the indoor rule.
* **The parts of the live model the study did not test on qualifying:** the five-pattern adjustment and the Thinking
  ensemble. "Using the live model" is read as: they apply to qualifying as they apply to the main draw (the owner was
  told in the previous answer that neither was tested). Reported, with the option of turning the patterns off for
  qualifying, not decided by me.
* **"Build the acceptance into A1–A5"**: the bet-day cells predict and bet these matches: the linker lets them through
  and finds their event and round (round 1 included), the engine builds their inputs as the study did, the gate and the
  data check say what is missing, the bet sheet treats them as bettable. Recorded as a decision.

**Readings set aside:** a small-stake trial or a stake scale for qualifying (recommended on 22 Oct, not asked for now;
the sheet's stake rule applies as for the main draw); betting only the top 40% of edges (asked about, not asked for);
the qualifying-calibrated stage 2.

## P8.3 What the code showed (11:15, before any change)

Seven things keep a qualifying match out today, or would make its inputs differ from the study's:
1. `src/pipeline/live.py` `todays_matches`: `qualifying` → left out.
2. The event: the linker, `live_rows.upcoming_rows` and `run.live_from_matchups` need the event's own Tennis My Life
   rows (and their Stage 0 tournament id). A round-1 qualifying match has none: neither qualifying nor main-draw rows
   exist yet. **Women's qualifying never has any:** Tennis My Life has carried no women's qualifying since June 2026;
   the lower-level feed brings it weekly (Wednesdays), so on the day even round 2's earlier results are missing.
3. The round: Pinnacle's league says only "Qualifiers" (16–18 Oct pulls: Almaty, Brussels, Lyon, Ningbo, Osaka).
   Tennis My Life's own dates of 2026 qualifying rows are not the day played (Almaty and Brussels round 1 was played
   17 Oct by Pinnacle's start times, dated 18 Oct) and its file lags the day by hours, so its rows alone cannot tell a
   round 2 whose round 1 is not yet published from a round 1.
4. `dp_context.inputs`: the level code maps only GS..T250 (TQ/GSQ give NaN, the study's 6/7 expected); the men's GSQ
   best-of-5 rule is absent; `main` marks the frame population.
5. `inject.odds`: a live match needs a Stage 1 row (tennis-data's levels); qualifying has none, so the tables step
   would stop. The engine's odds input does not read it (`dp_state.inputs` takes the run's prices).
6. The gate (`prediction_run/gate.py`) and the data check (`readiness.py`): no rule for a qualifying match's own
   earlier rounds; the data check's "same event" excludes qualifying rows.
7. `diagnostics.py`: "not a main-tour match" blocks a row whose frame row is not `main`; its "not predicted" list drops
   every qualifying league.

The stage-2 step (`dp_predict`) has no population filter: qualifying gets the live coefficients per tour.

## P8.4 Plan, each with its check

1. **The decision**, `docs/decisions/2026-10-22-qualifying-bets.md`, and CLAUDE.md's line. Check: the owner's words
   verbatim; nothing beyond them claimed as decided.
2. **Inputs** (`dp_context`): TQ 6 / GSQ 7, the men's GSQ best-of-5 rule, a `bettable` flag (main draw or tour-level
   qualifying). Check: `dp.py tree-check --full` on the instance's build tree for past qualifying matches: the state
   path's 57 inputs against the study's frame (`data/studies/qualifying_targets/frame.parquet`), bit for bit.
3. **Live rows** (`live_rows`, `run.live_from_matchups`, `inject.odds`): an event with no Tennis My Life rows takes its
   columns from the matchups CSV; a qualifying live match is priced through the run's prices only. Check: a replay of
   past qualifying matches as live rows (training dating) against the study's frame; a live-dated replay as a smoke
   test of the timeline steps.
4. **Gate and data check**: a qualifying match in round k ≥ 2 needs each player's round k−1 match at the event in
   Stage 0, else it is blocked (results missing, not only box scores). Check: unit tests; the replay's gate.
5. **The linker**: tour-level qualifying passes; the event from Tennis My Life's rows of the edition, else built from
   the previous edition; the round from a same-day listing, cross-checked with Tennis My Life. Check: offline tests on
   the saved 16–18 Oct pulls; a dry run of A2–A3 on today's listing.
6. **Bet sheet and diagnostics**: a qualifying row is bettable; "Not predicted" lists tour-level qualifying. Check: the
   master pipeline's tests.
7. **Docs**: the master pipeline README, the study's README status, CLAUDE.md.

## P8.5 Chronology (PDT)

| Time | What |
|---|---|
| 10:10–11:15 | Read the bet-day path end to end (P8.3); Pinnacle's qualifying leagues listed from every saved pull; Tennis My Life's 2026 qualifying file and its download history; the tree's Stage 0 for qualifying levels, ids, Slam best-of and the women's 2026 sources |
| 11:15 | This part opened |
| 11:15 | (Correction to the row above: the request's arrival time was not recorded; "10:10" is an estimate.) |
| 11:16 | `docs/decisions/2026-10-22-qualifying-bets.md` written (the owner's words, scope, evidence, what is not decided) |
| 11:17 | `dp_context.inputs`: `QUALIFYING_LEVELS` TQ 6 / GSQ 7 in the level code; best of 5 where Stage 0 records 5 for a men's GSQ match; `qualifying` and `bettable` beside `main` in the info |
| 11:18–11:24 | **Check 1** (`dp.py tree-check`, DP_INSTANCE `template_2026-10-21b`, the build tree `C:/Users/zerom/tnr_tpl1021`, the checkpoint of 23 Sep made on that tree): the study's qualifying rows from 23 Sep (a scratch copy of `frame.parquet` with `p_mkt` = the study's close, else 0.5, and `in_odds_logit` its logit): **200 matches, 57 of 57 inputs bit for bit, largest difference 0.0** (`data/studies/daily_prediction/checks/tree_check_2026-09-23_qualifying.json`). Both tours; the women's are the feed's rows (Ningbo, Osaka, Wuhan under their `W-WTAID` ids), Shanghai's split ids included. All TQ: no GSQ or best-of-5 row |
| 11:25–11:31 | **Check 2**, the same from the checkpoint of 22 Jun on rows of 22 Jun – 31 Aug: **756 matches, 57 of 57 bit for bit, 0.0** (`tree_check_2026-06-22_qualifying.json`): Wimbledon's and the US Open's qualifying of both tours (GSQ), Wimbledon's men's Q3 at best of 5, and the summer's tour-level qualifying. Without the edit the level input of every one of them would have been missing (TQ and GSQ are not in `T.CODES`), so the check can fail |
| 11:20–11:40 | Code written, before any replay result was seen: `live_rows` (an event TML holds no row of takes `event_*` columns from the CSV, `csv_event`; a player without a TML row falls back to their latest Stage 0 row with a blank id, `stage0_players`), `run.live_from_matchups` (a built event's id predicted as Stage 0 normalises TML's), `inject.odds` (a qualifying live match has no Stage 1 row: skipped and counted; any other missing row still stops), `dp_matchups.replay_select`/`replay` (a Q round: the first day's matches at the week's T1000/T500/T250, later qualifying rounds and the events' main draws left out; the day from the instance timeline's `obs`, the venue as a live run finds it), `--replay-frame` (`dp.py`, `dp_steps.replay_frame`: a frame holding rows the instance frame lacks), the gate's previous-round rule (`gate.previous_round_missing`, `PREVIOUS_ROUND_DAYS` 4) and the data check's (`readiness.py`) |
| 11:23–11:40 | Peers asked about file overlap (another session had edited `dp_steps.py` at 11:23 PDT, before my edits to it): tennis-predictions-b5 (session f3930e64) made the 22 Oct source-reconciliation repairs (`dp_steps.step_worktree`, `dp_worktree.setup(fixes=)`, `dp_predict`'s speed-column constants, `train.retrain`; outside my list `stage0_build.py`, `corrections.py`, `history.py`, …), finished; it is running a replay in `C:/Users/zerom/tnr_daily_srfix`. -f6 and -90 edit none of these files. Since 18:15 UTC Stage 0 builds apply 201 more row corrections and `event_corrections.csv`; replays read the instance's build-tree copy |
| 11:27–11:37 | **Replay Q1** (`replay_2026-10-19_Q1_qualifying`, DP_WORK_TREE `C:/Users/zerom/tnr_daily_qual`, checkpoint 23 Sep, `--no-fit`, training dating, frame `data/studies/master_pipeline/qualifying_replay/replay_frame.parquet` = the study's 2026 rows with its close as the price): 16 targets (Almaty 8, Brussels 8, the Q1 of 17 Oct); left out as later: their Q2, Lyon's Q1 of 18 Oct and Q2, both main draws. Every step ran: Stage 0 with the live rows (the inject check passed: the ids predicted), `live_odds` skipping 16 qualifying matches, states, **the patterns step (66 s; no failure on qualifying rows)** |
| 11:38 | **Replay Q1 compared: 38 of 57 inputs bit for bit; 0 of 16 matches equal on every input.** Equal: every rating input (Elo, offset Elo, `ratings_iid`, `elo_games`), the 21 surface-IOS inputs, the context. Different: `sets_14d` (12 of 16 rows, up to 2.39), `points_52w` (12 of 16, up to 0.14), `adjperf_tpw_2w` (16, up to 0.022), 13 `form_*` and 3 `formdef_*` (16, up to 0.035). All read a time window by the match's tournament date. **Cause:** with the main draws left out, Stage 0 dates these events by their earliest row (Tennis My Life's Q1 date, 18 Oct), while the instance dated their qualifying with the main draw's first date (20 Oct): its rule C05, "one date per TML event: the main draw's first date". A live qualifying match always meets this, since its main draw is not played yet |
| 11:40 | Training's convention measured on the tree's 2025–26 qualifying (every T250–GS edition, both tours, every source): the date is the main draw's start, a Monday for most, the Wednesday or Sunday where the main draw starts then, the Slams' main-draw Sunday or Monday (6–7 days after Q1). **Fix chosen:** the linker estimates the main draw's start (`event_main_date`) and Stage 0 uses it for an event that has no main-draw row yet; nothing else changes. Peer b5 told before `stage0_build.py` is edited |
| 11:42 | `stage0_build.py` edited (peer b5 agreed; its own edits of today are elsewhere in the file): `add_live_rows` carries an optional `event_main_date` as `live_main_date`; rule C05's `main_day` takes it where an event has no main-draw row (`main_day.combine_first(hint)`). Without the column nothing changes. `live_rows.upcoming_rows` passes the CSV's `event_main_date` on; the qualifying replay gives each live row the instance's own date of its event (the exact test of the code path; a live run's date is the linker's estimate) |
| 11:43 | **Replay Q1 rerun** started (`replay_2026-10-19_Q1_qualifying_maindate`); its Stage 0 dates both events' live rows 2026-10-20, the instance's date (read from the work tree) |
| 11:44–11:47 | `qualifying.main_draw_start` written; **date check** (`src/eda/master_pipeline/qualifying_dates.py`): on the tree's 5,145 tour-level and Slam qualifying matches of 2025–26 (207 editions, both tours), the estimate from each match's observed day and its previous edition's date is exact for 79.8%, within a day for 95.0%, at most 3 days off. The misses were Friday matches of Sunday starts (Doha, Dubai, Brisbane); rule changed (Friday to Sunday → the next week): **exact 80.6%, within a day 96.7%, within 2 days 100%** (`main_date_check.json`). The 2-day misses: the 2025 Masters, whose 2024 editions Stage 0 dates a Monday and 2025's a Wednesday (2026's are exact), and Shanghai 2026, whose qualifying TML files apart (dated 5 Oct, estimate 7 Oct). Seen before any forecast was compared |
| 11:45–11:50 | `test/master_pipeline/test_qualifying.py` (8 tests, offline). The linker on Pinnacle's pull of 16 Oct 22:58 UTC with Tennis My Life cut to 16 Oct: **first 11 of 33 linked**, the 22 women's left out because Tennis My Life's women's rows carry no indoor flag (the built event required it). The women's indoor input comes from the WTA's calendar (`indoor_fill`), so the flag is now optional (`built_event`, `csv_event`): **32 of 33 linked**, every one Q1 (the stand-in TennisLive has no result yet), events built from 2025-9410, 2025-7485, 2025-2092, 2025-405, main-draw start 19 Oct. The one left out: Pinnacle's "Joel Josef Schwaerzler" is Tennis My Life's "Joel Schwaerzler"; the linker's documented fix is an alias in `config/player_aliases.csv`, not created (config/README: no operational configuration is approved). 8 of 8 pass |
| 11:50–11:52 | **Built-row check** (`src/eda/master_pipeline/qualifying_rows_check.py`): every men's 2026 Q1 in Tennis My Life's qualifying file (778 matches, 54 editions), built as on its morning (TML cut to before the edition) against the row TML published: previous edition found 94.9% (the misses are TML's own 2026 spellings, "Buenoa Aires", "Rio de Jainero", and new or moved events: Estoril, Lyon, Marrakesh; Pinnacle's spellings would match 2025's); where found, indoor 100%, level class (Slam or tour qualifying) 100%, best of 100%, surface 98.9% (Santiago), draw size 97.3%; players found 97.8%, hand/height/country ≥ 99.3%, age within 0.37 days for 90% (at most 8.4 days); rank 13% (not an input) |
| 11:53 | **Replay Q1 rerun compared: 57 of 57 inputs bit for bit, 16 of 16 matches equal on every input, largest difference 0.0** (`replay_2026-10-19_Q1_qualifying_maindate/replay_compare.json`). With the main-draw date given, the live path for a qualifying round 1 reproduces the training frame exactly; the patterns step ran (z for 16 of 16; two members not built for live matches, as on the main draw). What a live run adds beyond this exact path: the date estimate (11:44) and a round 1's built event and player columns (11:50) |
| 11:53 | `--replay-main-date` (`dp.py`, `dp_steps.step_matchups`, `dp_matchups.replay`): a qualifying replay's live rows name a given main-draw start instead of the instance's (edited `dp_matchups` first, so a work tree copied between the two edits stays consistent; the round-2 replay's copy has both) |
| 11:53– | **Replay Q2** started (`replay_2026-10-19_Q2_qualifying`, the instance's dates): the round-2 path, its event taken from Tennis My Life's Q1 rows, the gate's previous-round rule |
| 11:54–12:04 | **Replay Q2** (`replay_2026-10-19_Q2_qualifying`): 8 targets (Almaty 4, Brussels 4, the Q2 of 18 Oct), their events taken from Tennis My Life's Q1 rows (dated 18 Oct there, given the instance's 20 Oct by the hint). **57 of 57 inputs bit for bit, 8 of 8 matches equal on every input.** The gate: all 8 "may be bet", 5–10 earlier matches checked each, none missing (the previous-round rule found every player's Q1) |
| 11:56–12:02 | The master pipeline suite (`test/master_pipeline`, 78 tests with the 8 new): **76 passed, 2 failed, neither from this work.** (1) `test_every_issued_command_parses`: `src/eda/current_best_model/odds_input.py --help` crashes (`TypeError: %o format`): its new help text `{TE_MIN_SHARE:.0%} of` renders "75% of", which argparse reads as a format (the file was edited at 01:32 today by another session; `--apply` runs are unaffected). Not edited here; reported. (2) `test_linker_on_the_probe`: the 9 Oct probe read with today's Tennis My Life, which now holds Shanghai's final (18 Oct), so every listed Shanghai round reads "a new event of the same name" (`_event_current`) instead of "already played". Fixed in the test only: Tennis My Life cut to 14 Oct, as it stood when the test was written; it passes |
| 12:04– | **Replay Q1 with the estimate** started (`replay_2026-10-19_Q1_qualifying_estimate`, `--replay-main-date 2026-10-19`: the linker's estimate for both events, the instance's being 20 Oct, Tennis My Life's own date of their main draw's first day) |
| 12:05 | No tour-level qualifying in today's Pinnacle pulls (the latest on disk, 04:18 UTC: ITF, Challengers, Lyon/Almaty/Brussels/Ningbo main draws). Basel's and Vienna's qualifying starts Saturday 24 Oct. **A live A1–A5 run on a real qualifying match is not possible today** |
| 12:06 | **TennisLive on real events** (`qualifying.TennisLive`, Almaty and Ningbo 2026): both found, their qualifying read (Q1 8 + Q2 4; Q1 12 + Q2 6), played pairs "already played". **But no request was made:** the adapter's `fetch_section` refetches only an answer that lists an unfinished match, and the results section lists finished matches only, so a morning answer reads as final and is never asked again. That would misread a later round. Fixed: `tennislive_events.fetch_section(force=)` and `fetch_day(refresh=)`, both defaulting to the old behaviour (the daily task and the feed are unchanged); the linker asks each event's section afresh once per linking and today's or later date pages afresh. Rerun: 3 requests (a session, two sections), status 200, both answers current (today's quarter-finals listed) |
| 12:06–12:15 | **Replay Q1 with the estimate** (main draw 19 Oct, the instance's 20 Oct: Tennis My Life dated Almaty's and Brussels's main draws a day late, as their qualifying): 38 of 57 inputs bit for bit, the same 19 differing as with the unfixed date (18 Oct): `sets_14d` and `points_52w` as much (a match falls just inside or outside the window either way), the forms about half as much (up to 0.017 against 0.035) |
| 12:10–12:20 | **Fits** (GPU, seeds 0–15, the instance's fits; `dp.py fit`, then `predict`) of the three round-1 replays, against the exact one (`date_effect.json`): **one day off moves the model's own chance (before stage 2) by 0.42 points on average, at most 1.9; after stage 2 0.39, at most 1.7; the chance used (with the patterns) 0.13, at most 0.35.** The unfixed date (2 days off): 0.43, 1.95; 0.40, 1.79; 0.14, 0.42. The patterns' score moved too (its past-fatigue member reads the dates), here against the model's move; not read as a rule. The side the model favours against the market changed for 1 of 16 either way. Read: the date matters at about these sizes wherever it is wrong; the estimate is exact for 81% of matches (11:44), so the expected effect over all qualifying matches is about a fifth of these |
| 12:21 | The bet-sheet record (`diagnostics.bet_diagnostics`, not written) on the exact round-1 replay: 16 predicted, rounds Q1, events "ATP Brussels Q1 · Hard, indoor · best of 3"; the only block is the replay's own "no bookmaker odds" (no matchups CSV); none "not a main-tour match" |
| 12:22 | Docs: `docs/decisions/2026-10-22-qualifying-bets.md` (how it is carried out), the decisions index row, CLAUDE.md (the master notebook section and the gate's rules), this README's section, the qualifying study's status line and the studies index rows, the notebook's section A text and the A2, A3b and A5 comments (`test_notebook_is_clean…` passes after the edits) |
| 12:25 | The owner committed at 12:09 ("latest rebuild and extra data"), mid-work: the code and most outputs are in it; the docs and logs edited after are not. Correction to what I told peer b5 at 11:41: the builder's plain path was checked by code path (both edits sit behind conditions only live rows meet), not by a separate before/after build; b5 told |
| 12:30 | Peer b5 (not that file's author either) agreed the `odds_input.py --help` fix is safe. Made, outside this part's scope: its `--min-share`-style help text now renders "75% of" (`{TE_MIN_SHARE:.0%}%`, so argparse sees "%%"); only `--help` formats it, so `--apply` runs are unchanged. `odds_input.py --help` prints, and `test_every_issued_command_parses` passes. With the probe test's fix, the master pipeline suite's two failures of 11:56 are both resolved |
| 12:31 | (Precision on the row above: the option is `--allow-low-te-coverage`.) |

## P8.6 Judgment calls (results seen when each was made)

* **Patterns and Thinking stay on for qualifying** (before any result; the owner's "using the live model", told the previous answer that neither was tested). Option offered, not taken: patterns off for qualifying.
* **TennisLive as the round's source, not Tennis My Life's silence** (after seeing, 10:30–11:10, that TML dates some 2026 qualifying a day late and its file lags the day; no forecast seen). Both players' TML wins still give the next round when TennisLive does not answer; a round 1 never comes from TML alone.
* **The main draw's start as a hint to Stage 0's C05, not a re-dating step after the build** (after the first replay showed the date effect, before any forecast): the builder then orders and ids the rows itself; a build without the hint is unchanged.
* **The estimate's weekday from the previous edition's Stage 0 date; the Friday rule** (after the first date check, 79.8% exact): changed once, to 80.6%; no further tuning. Tuned on 2025–26 matches only, which are also its check (a weak point, P8.8).
* **The replay gives the instance's own date** (the exact test of the code path), and a second replay the linker's estimate (its error); chosen before either compare.
* **The indoor flag optional** in a built event (after the 16 Oct linking left all 22 women's matches out): Tennis My Life's women's rows never carry it; the women's input comes from the WTA's calendar, a men's blank flag is blocked by the gate.
* **Not done:** a same-day source for women's earlier qualifying rounds (the WTA API lists them, the lower-level feed already takes its box scores; a new live data path, its own proof); the patterns' check on past qualifying; the alias for "Joel Josef Schwaerzler" (config/README: no operational configuration approved); the `odds_input.py --help` fix (another session's file).

## P8.7 Claims and their evidence

| Claim | Evidence |
|---|---|
| The engine builds a qualifying match's 57 inputs as the study did | `tree_check_2026-09-23_qualifying.json` (200 matches), `tree_check_2026-06-22_qualifying.json` (756): 57 of 57 bit for bit |
| A qualifying round's live rows reproduce the training inputs, given the main draw's start | `replay_2026-10-19_Q1_qualifying_maindate` (16) and `replay_2026-10-19_Q2_qualifying` (8): `replay_compare.json`, 57 of 57, every match equal |
| Without that date, 19 inputs move | `replay_2026-10-19_Q1_qualifying/replay_compare.json` |
| The estimate's accuracy | `data/studies/master_pipeline/qualifying_replay/main_date_check.json` |
| A day's error moves the forecast 0.42 points on average (16 matches) | `date_effect.json`; the three runs' `predictions.csv` |
| A built round-1 event matches the published one | `rows_check.json` (778 men's 2026 Q1 matches) |
| A2 places 32 of 33 qualifying matches of 16 Oct | `test_qualifying.py::test_the_linker_on_the_16_oct_qualifying` |
| The gate and the data check block a round whose round before is missing | `test_qualifying.py` (two tests); the Q2 replay's `gate.csv` (none blocked when present) |
| TennisLive's results are read current | 12:06 rerun: 3 requests, answers of 19:07 UTC |
| Nothing else changed | main-draw paths behind every new branch (P8.10); `test/master_pipeline`: 76 of 78, the probe test then fixed; the two failures predate this work |

## P8.8 Weak points; where a flaw would hide

* **No live run on a real qualifying match yet:** the first is Basel's and Vienna's qualifying (24 Oct). The parts a replay cannot reach: Pinnacle's listing, TennisLive on an event under way, the built event in a real run (tested offline and field by field only), the women's player fallback in a real Stage 0 build, the WTA calendar's indoor value for a built women's event.
* **Women's qualifying has no replay.** Tennis My Life carries none, so women's live rows were never compared with a training row. The tree check covers their inputs given the rows; the built event is checked for men only.
* **The date estimate was tuned and checked on the same 2025–26 matches** (one change); a calendar change (a new start day) is missed until the next edition.
* **TennisLive is a third-party live-score site:** a name it spells differently from Stage 0 and Pinnacle could read a round 2 as a round 1. Guarded by the round-1-complete and later-round checks and by Tennis My Life's rows where they exist, not proven.
* **The five-pattern adjustment on qualifying is untested**, and its seeding member means a qualifying seed there.
* **Edge credit:** the study's edge is at closing prices; the bet sheet's prices are earlier ones.

## P8.9 What a re-design would do

* Take women's earlier rounds the same day from the WTA API (results and box scores), as live-only rows the feed's replace at its next snapshot; then women's rounds 2 and 3 become bettable.
* Score the five-pattern adjustment on the study's qualifying matches before keeping it on there.
* Read the main draw's start from an official calendar (the ATP's, the WTA's) instead of estimating it.
* Use the built-event path for main-draw first rounds too (still left out).

## P8.10 Reviewer checklist

* Is every main-draw path untouched? `dp_context` (TQ/GSQ only), `inject.odds` (qualifying only), `stage0_build` (only with the hint), `live_rows` (only an event without TML rows; the player fallback only without a TML row), `replay_select` (Q rounds only), the gate (qualifying only), `diagnostics` (`bettable`, with `main` as the fallback).
* Can the hint override a played main draw? `main_day.combine_first(hint)`: no.
* Could the linker read a round 2 as a round 1? Only if TennisLive misses both players' round-1 results while showing no later round and fewer round-1 results than the previous edition had.
* Are the replays' frames the study's? `replay_frame.parquet` = the study's 2026 rows, `in_odds_logit` from its close.

## P8.11 Reproduction

* The inputs on the instance's tables: `dp.py tree-check --tree C:/Users/zerom/tnr_tpl1021 --day 2026-09-23 --frame <a copy of the study's frame.parquet with p_mkt and in_odds_logit> --tag _qualifying` (DP_INSTANCE `template_2026-10-21b`, DP_BASE_TREE the tree); likewise `--day 2026-06-22`.
* A qualifying replay: `dp.py run_day --run data/studies/daily_prediction/runs/<name> --replay-week 2026-10-19 --replay-round Q1 --replay-frame data/studies/master_pipeline/qualifying_replay/replay_frame.parquet --checkpoint 2026-09-23 --no-fit` (DP_WORK_TREE `C:/Users/zerom/tnr_daily_qual`; add `--replay-main-date 2026-10-19` for the estimate's version), then `dp.py replay-compare --run <the same>`; `dp.py fit` and `dp.py predict` for the forecasts.
* `./python.sh src/eda/master_pipeline/qualifying_dates.py`, `./python.sh src/eda/master_pipeline/qualifying_rows_check.py`, `./python.sh -m pytest test/master_pipeline/test_qualifying.py -q`.

---

# Part 9 (22 Oct 2026): one place names the live model; no default instance anywhere

Kept by Claude Opus 5.5 (`claude-opus-5-5`), Claude Code in VS Code, session `f471b5ba-df28-4941-8f4b-8f5bca704b45`.
Local time PDT (UTC−7). **Opened at about 13:45, after the change and its tests** (made 13:00–13:40 under the owner's
"high priority"), not before the first step as the log rule asks; it is written from the session's own commands and
outputs, in order, and says where it relies on them.

## P9.1 The request (verbatim)

Earlier in the session the owner asked for an assessment of the pipeline's organisation (a chat answer, no log). Three
read-only sweeps (subagents: silent fallbacks on the bet-day path; copies of the build procedure; documents stating
production state, to-do lists and study banners) found, among other things, that the live model is named four ways.
The owner then quoted that finding back:

> "The live model is named four different ways. Your notebook's selection says 21 Oct. The prediction engine's
> built-in default is still the 10 Oct model. One guide says 16 Oct, and three old models' notes each call themselves
> "the current" one. The notebook passes the right model today. Anything that runs the engine without that selection
> would predict with the 10 Oct model. Its name would appear on the sheet, but nothing would flag it as wrong."
>
> These needs to be rectified at a high priority

The same message asks for an independent audit of a proposed organisation plan "after that"; it is not part of this
part.

Re-verified by this session before the finding was reported: `dp_common.py:27`
`os.environ.get("DP_INSTANCE", "template_2026-10-10")` (tree default `C:/Users/zerom/tnr_lyr_new`); this README's
"The active instance, `template_2026-10-16`"; `template_2026-10-14/README.md` line 3 "The current instance of the
template" (the sweep also named 10-10 and 10-13, confirmed when banners were added); `selected_instance.json` =
`template_2026-10-21b` on `tnr_tpl1021`; the two newest live runs' `predictions.csv` carry `template_2026-10-21b`.

## P9.2 Interpretation acted on

* "Rectified" = **one place decides which model is live, everything reads it, nothing falls back to another model
  silently, and no document asserts which one is live now.**
* The one place: the notebook's selection file. It already existed (written by `use_instance()` and the retrain's
  switch; read by the notebook layer and the engine's test conftest), so nothing new was introduced: the "production
  record" of the plan under audit may later absorb it, and this part pre-empts nothing of that plan.
* No default anywhere: with no selection, refuse loudly.
* The explicit override stays, as a pair: `DP_INSTANCE` with `DP_BASE_TREE` (`retrain.sh` and candidate replays set
  both). `DP_INSTANCE` alone naming another instance than the selection is refused: it would pair that instance with
  the selection's build tree.
* Because the finding said "nothing would flag it as wrong", the bet sheet now blocks every match of a live run made
  with another model than the selected one.

Set aside: making `template_2026-10-21b` the new default (a copy that goes stale at the next retrain); moving the
selection file to a new production folder (the retrain script, the notebook and the tests read it where it is).

## P9.3 What changed

Code:
* `src/eda/daily_prediction/dp_common.py`: `resolve_instance()` (the pair of variables, else the selection, else
  none, with the reason), `INSTANCE_OK`, `INSTANCE_SOURCE`, `require_instance()` (refuses; else pins `DP_INSTANCE` and
  `DP_BASE_TREE` in the environment so every step the run starts reads the same instance even if the selection
  changes mid-run). Unresolved, the module still imports (a `NO_INSTANCE_SELECTED` placeholder) for tests and helpers.
* `dp.py` `main()`: `require_instance()` for every command except `cleanup`; one stderr line "instance X on T: from
  <source>". `dp_steps.init()`: `run.json` records `instance_source`.
* `src/pipeline/train.py`: `dp_defaults()` removed (it read the default out of `dp_common.py`'s text with a regex);
  `selected_instance_name()`; `active_instance()`, `base_tree()`, `dp_env()` refuse with no selection;
  `use_instance(None)` refuses (no default to go back to); `instance_status`, `sandboxes`, `template_check` no longer
  raise when nothing is selected.
* `src/pipeline/diagnostics.py`: `_selected_instance()`, `_model_block()`. A `live_` run made with another model, with
  none selected, or not recording its model: every match BLOCKED, and one note heads the sheet. Replays and other
  non-live runs are not checked.
* `src/pipeline/overview.py`: STATUS's Model section opens with "LIVE MODEL: <name> on <tree> (the notebook's
  selection, set <time>)", or "NONE SELECTED: …".
* `src/eda/in_season_retrain/retrain.sh`: refuses before creating anything when no model is selected.
* `test/daily_prediction/conftest.py`: no 10 Oct fallback; tests needing an instance skip without one.

Documents: this README (the Thinking-fit sentence; the "DP_INSTANCE" limit marked done, with the rule); the daily
pipeline's README (the `DP_INSTANCE` lines; folder examples as `<instance>`); `data/studies/current_best_model/README.md`
(the selection decides; the table records when each instance went live; the stale "history up to 13 Oct" line);
banners on `template_2026-10-10`, `-13` and `-14`'s READMEs; one paragraph in `CLAUDE.md`'s master-notebook section;
the notebook's C6 cell (it still said the switch "needs the daily pipeline's DP_INSTANCE, requested from its session"
and offered `use_instance(None): back to the default`).

New tests: `test/daily_prediction/test_instance_selection.py` (8; a fake repository through `DP_REPO`, the real
selection never read) and seven in `test/master_pipeline/test_master_pipeline.py`, with an autouse fixture making the
replay's own model (`template_2026-10-10`) the selected one for the existing priced-run tests, which dress the replay
as a live run.

## P9.4 Checks, and what was seen

* **The bug reproduced first:** all 8 new engine tests failed on the old code. The key one: `dp.py init` with no
  selection exited 0, `run.json` named `…/template_2026-10-10` on `C:\Users\zerom\tnr_lyr_new`, stderr empty.
* After the change: those 8 pass (3.0 s); `test_master_pipeline.py` 44 pass (37 earlier + 7 new; 260 s); the engine's
  fast tests 36 pass (instance selection, stage-2 sync, replay tables, Thinking, ace rows, and five fast tests of
  `test_daily_prediction.py`).
* **On the real selection with the `DP_*` variables unset** (as an agent running the engine from a shell would): in
  all three interpreters the engine uses (tennis 3.11.16, tennis-tabpfn-local 3.11.17, tennis-tabpfn 3.11.16), the
  instance resolves to `template_2026-10-21b` on `C:\Users\zerom\tnr_tpl1021`, "from the notebook's selection
  (selected 2026-10-21T15:55:44)". Before the change the same call gave `template_2026-10-10` on `tnr_lyr_new`.
* `dp.py init` on the real selection, into the session's scratchpad: exit 0, the stderr line names the instance and
  its source, and `run.json` records it.
* **The notebook path is unchanged:** `dp_env()` = `{DP_INSTANCE: template_2026-10-21b, DP_BASE_TREE:
  C:\Users\zerom\tnr_tpl1021}`, the same values as before; `template_check()` OK on all five checks;
  `use_instance(None)` refuses; the notebook test passes after the C6 edit.
* **Not run:** the replay proof (C8; GPU, about 7 minutes), the heavy engine tests (families, replay through run_day;
  hours) and a live run. The change decides which instance is chosen, not how it predicts, and on the notebook's path
  the chosen instance and tree are the same strings as before.

## P9.5 Coordination with the sessions running at the same time

Two other sessions were busy: `tennis-predictions-0a` (qualifying into A1–A5, Part 8) and `tennis-predictions-92` (the
cleanup inventory). Both were sent the list of files and lines this part edits before the documents were touched.
* 0a: not adding a Part 9; its remaining edits are elsewhere (a bullet in this README's qualifying section, one in
  CLAUDE.md's qualifying block); its earlier qualifying edits in `dp.py`, `dp_steps.py` and `diagnostics.py` are
  intact after these (it checked). `diagnostics.py` had changed since this session first read it (0a's qualifying
  docstring); the edits here matched the current text.
* 92: no overlap. At the owner's word it deleted `template_2026-10-21`'s TabPFN caches and five scratch work trees
  (13:05–13:12); `template_2026-10-21b`'s state and the tree `tnr_tpl1021` are untouched.

## P9.6 Threats to validity, and where a flaw would hide

* **An explicit pair still runs a non-selected instance**, live or not. The engine says so (its source names the
  selection's instance), and the bet sheet blocks the run; a caller that ignores both is not stopped.
* **A sheet re-made from an old live run after a switch is blocked by design:** run A4 again.
* **Study code still calls an old instance "the current" one** in its own docstrings or constants, as evidence of its
  time (none of it is on the live path; checked by a search of `src/pipeline`, the daily engine, the prediction run
  and the retrain): `edge_anatomy/{common,data,fits,scan}.py`, `unpriced_leads/{screen,resolution,rebuild_pool}.py`,
  `data_gaps_2026/{harm,exposure}.py`, `daily_update_speed/bet_time_pricing.py`, `level_layer_adoption/harm.py`,
  `daily_prediction/dp_cachediag.py`, `in_season_retrain/check.py` (the one-off check before the first retrain, pinned
  to the 16 Oct instance it checked), `qualifying_targets/common.py` (the 21 Oct tree). For the study-status work.
* **`tml_revisions/held_check.py`** measures a held Tennis My Life file's reach on `template_2026-10-10`'s frame with
  training seasons 2013–2025, stale since the in-season retrain (the live fit also trains on 2026). A report, not a
  gate; not changed here.
* The checks not run (P9.4).

## P9.7 What a re-design would do

Hold every live fact (this selection included) in one production record, with a check that the record and the disk
agree at bet time and at each agent session's start: then a document or a constant naming the live model goes red
instead of going stale.

## P9.8 Reviewer checklist

* With no selection, can anything still choose an instance? `grep -rn "template_2026" src/pipeline
  src/eda/daily_prediction src/eda/prediction_run src/eda/in_season_retrain`: an example in an error message and a
  diagnostic's history note only.
* Is the explicit pair still honoured for the retrain (`retrain.sh` sets both for its checkpoints and replays)? Yes.
* Do the steps a run starts inherit its instance? `require_instance()` sets both variables before any child starts.
* Is the bet-sheet block only on live runs? `_model_block` returns None otherwise
  (`test_replays_are_not_checked_against_the_selection`).

## P9.9 Reproduction

* `./python.sh -m pytest test/daily_prediction/test_instance_selection.py test/master_pipeline/test_master_pipeline.py -q`
* The real selection, variables unset (Git Bash, repository root):
  `env -u DP_INSTANCE -u DP_BASE_TREE ./python.sh -c "import sys; sys.path.insert(0, 'src/eda/daily_prediction'); import dp_common as DC; print(DC.require_instance(), DC.INSTANCE_ID, DC.BASE_TREE)"`

---

# Part 10 (22 Oct 2026, from 16:15 PDT): executing the production-integrity plan

Kept by Claude Opus 5.5 (`claude-opus-5-5`), Claude Code in VS Code, session `f471b5ba-df28-4941-8f4b-8f5bca704b45` (the
session of Part 9). Opened before the first substantive step of this part. The plan of record is the decision
`docs/decisions/2026-10-22-production-integrity-plan.md`; this part is how it was carried out.

## P10.1 The request (verbatim)

The owner quoted the last block of the session's plan, as revised after an independent audit:

> Revised order (my recommendation):
> Fix the four false or blind signals above. A few hours.
> Bet-sheet integrity. About 1–2 days. This targets the incidents that actually touched bets; today's live-model fix is
> the first piece of it.
> full model identity, against the receipt from the last passing replay;
> the every-part-present check;
> the missing-results check;
> what each bet rests on.
> Outcome tracking.
> Record placed bets.
> Grade every predicted match nightly.
> Run the strength-of-lean check above.
> The reviewer found closing prices already saved for 186 of 191 recent main-draw matches, so this can start from 10 Oct.
> One to-do list that routes, with "who decided" marked. You pick which open items from the 25+ scattered places are
> still wanted.
> The generated state printout. Last, because it's mostly a printout of steps 2–4.
> Then: checking each day's predictions against the backtest, countdowns before data is lost for good, and per-file
> claims.

> Execute on this plan, and have it documented that this is the plan so other future agents will know what happened.
> Integrate it into the master_pipeline and the scripts that run for predictions and production

How the plan came about (this session, before this part): the owner's question on the pipeline's organisation; three
read-only sweeps (silent fallbacks; copies of the build procedure; documents of state and to-do lists); the assessment
and first plan (a chat answer); the live-model fix (Part 9); then an independent audit of the first plan by three
subagents (20 past incidents; an adversarial design review on another model family; the bet-time warnings), each
"agree with changes", with the claims this session relied on re-checked in files (summarised in the decision).

## P10.2 Interpretation acted on

* **"Execute on this plan"** = build steps 1–6 in order, each verified before the next, with the details the revised
  plan named ("the four false or blind signals", "the strength-of-lean check") as the session's last answer defined
  them.
* **"Documented that this is the plan"** = a decision record (the owner's words, the plan, the principles the audit
  set, a status per step), its row in the decisions index, and a short pointer in CLAUDE.md so every agent session sees
  it; this log for the how.
* **"Integrate it into the master_pipeline and the scripts that run for predictions and production"** = the checks run
  inside the notebook's existing cells (STATUS, A4, A5) and the engine and scheduled task, not as a separate tool to
  remember; new notebook cells only where a new action is needed (recording a placed bet, the outcomes).
* **What the owner still decides** (not taken by this session): which of the scattered open items stay on the to-do
  list (step 4 builds the list and fills it with candidates marked "proposed"); whether the session-start hook in the
  owner's own settings should expect effort "high" or "xhigh" (asked; left untouched until answered); any new rule that
  blocks bets is marked "agent's choice" for the owner to confirm.

Set aside: a hand-written production record (the audit's main correction); claims on to-do items (claims go on shared
files and resources); closing-line value as the model's health alarm (kept only as a check on prices).

## P10.3 The plan, with the check for each step

1. **The four false or blind signals.** STATUS shows every scheduled run of the last day and the last days' alerts
   (not only the latest run); serve-speed freshness from the newest real reading, on STATUS, the bet sheet and the
   daily job's alert, and missed days fetched again; the canary's known flags acknowledged with an expiry; the hook
   (owner's answer). Check: unit tests on fixture records; STATUS run on the real records.
2. **Bet-sheet integrity.** Model identity (every code file a run imports, the weights' contents, Thinking's served
   version) against a receipt written by the last passing replay proof; every part of the forecast present (inputs,
   pattern parts, speed term, Thinking); a main-draw player's previous round present (a bye excepted); what each bet
   rests on; a verdict per match, a run-level red only for run-level failures, a typed acceptance saved with the sheet.
   Check: tests reproduce each failure; the real 21 Oct live run re-sheeted; a replay proof writes the first receipt.
3. **Outcome tracking.** A placed-bet record (with any acceptance); every predicted match graded nightly by the
   scheduled task from a freshly built Stage 0; the strength-of-lean (realisation slope) per model; closing-line value
   for bets as a price check; backfilled from 10 Oct. Check: the backfill's numbers by hand on a sample.
4. **One to-do list that routes.** One machine-readable list (decider, who decided, status, claim, check), shown on
   STATUS and the sheet while an item touches the live path; candidates from the scattered places marked "proposed".
5. **The generated state printout.** From disk and run records; a short owner-edited intent section, each line with
   its check or "unchecked"; a one-line verdict for a project session-start hook.
6. **Then.** Each day's predictions against the backtest; countdowns before data is lost for good; claims on shared
   files and resources, and a live run that notices code changed under it.

## P10.4 Working log

**16:15–16:40, documentation first.** The decision record
(`docs/decisions/2026-10-22-production-integrity-plan.md`: the owner's words, why, eight principles, the six steps with a
status column), its row in the decisions index, and a short "Production integrity" section in CLAUDE.md (after the
master-notebook section). Coordination: the two sessions that had touched the same files today were sent the list of
files this part edits. tennis-predictions-0a (qualifying) asked, verbatim in substance: don't widen
`gate.previous_round_missing` / `previous_round_reason` in place (a main-draw check needs its own rule: main round orders
10–17, qualifiers and byes); `bet_sheet._gate_block` parses the qualifying reason text with a regex; diagnostics decides
blocks by `live_frame`'s "bettable" column; rerun `test/master_pipeline/test_qualifying.py` after edits.
tennis-predictions-92 (cleanup) touched none of the listed files; at the owner's word it deleted the build trees
`tnr_gaps` and `tnr_tpl1014` (16:16–16:17) and noted it in the 10-13 and 10-14 READMEs.

**16:40–17:45, step 1 (the four signals).**
* New `src/ingest/health.py`: the feed-health rules in one place. Serve-speed state from the speed job's own record
  (newest reading, planned and staged matches): ok / stale (newest reading older than 4 days while rounds were there to
  collect; an agent's choice) / empty / off / unknown. Canary flags split into open, acknowledged (until a date) and
  lapsed; the acknowledgments in `data/studies/data_continuity/canary_acknowledged.json` (7 flags: Sackmann's three gone
  repositories and their archive flags, Tennis My Life's GitHub archive flag; until 31 Jan 2027 / 31 Dec 2026; marked
  as an agent's choice). `tml_manifest:REVISED` is left open: it reports real revisions.
* `src/ingest/scheduled.py`: the speed job asks for the last 7 days' rounds (was 1; matches held complete are never
  asked again, `atp_daily.plan_days`, and an earlier "absent" is asked again, `fetch_daily` with refresh); alerts on
  "planned but nothing staged" the second time in a row, on a stale newest reading (again every 3 days), and on a
  switched-off collector. The canary job alerts on open flags and once on a lapsed acknowledgment.
* `src/pipeline/overview.py` (STATUS): every scheduled run of the last 24 hours with each job's result, the other jobs'
  latest result, every alert of the last 3 days (one line per alert text, with how many runs repeated it), serve speeds
  by the newest reading, the source watch's flags by group; the latest prediction runs ordered by their run.json's
  `created_at` (a folder's time moves when a cleanup touches it: today's cleanup had put the 14 Oct runs first).
* **What was seen on the real records:** the old STATUS read only the last run (13:22, `event_country`, no alerts), so
  four Tennis My Life "held two runs in a row" alerts of 19–21 Oct were not on it; the new one shows them, and four held
  files (2015_wta, 2024, 2025, 2025_wta). Serve speeds: newest reading 22 Oct, 9 of 24 planned matches staged at the
  07:30 run. Source watch: open `tml_manifest:REVISED`, 7 acknowledged.
* Tests: `test/master_pipeline/test_health_signals.py` (7, offline); `test/master_pipeline/` 92 passed (the qualifying
  session's 8 included). The scheduler imports and plans (`--dry-run`).
* **The hook (the fourth signal) is not changed:** it is in the owner's own settings, and which value is intended
  ("high" or "xhigh") is the owner's answer.

**22 Oct, 17:45 to the disconnect, step 2 begun (engine side only).**
* `dp_common.py`: code fingerprints (`code_rel`, `code_fingerprints`, `write_code_used`, `code_used`), a source snapshot,
  `replay_passed` (the replay proof's own standard) and `write_receipt` (receipts under
  `data/studies/daily_prediction/receipts/`; refused when the code changed during or since the replay).
* `dp.py`: every command with a run folder writes `code_used/<step>_<pid>.json` at exit; a passing `replay-compare`
  writes the receipt.
* `dp_predict.py`: provenance gains `code_used`, `code_conflicts` (a file seen with two contents during the run) and
  `tabpfn_weights_sha256` (by content, cached); `predictions.csv` gains `speed_k28_a/b`, `speed_last_reading_a/b` (the
  form the adjustment used) and `speed_term` (b × spd_L in log-odds; women 0); the speed record gains `newest_reading`.
* **Not verified before the session was cut off** (the check below was running; its tool call failed).

**Resumed 27 Oct 2026, about 06:30 PDT, same session, after a disconnect of four days.** Other sessions had worked
meanwhile (Parts 11–18), and the decision's status table carried their updates: step 1's speed look-back of 7 days had
made every collector run hit its 200-request budget and a second run on one day erase the first's staged matches;
fixed on 25 Oct at the owner's word (Part 16). Step 3's closing-line ledger was built on 25 Oct (Part 18). Step 6's
stale-kernel refusal was built on 23 Oct (Part 11).
* **The unverified step-2 engine code had run in every live run since:** 23 Oct 11:59, 24 Oct 07:42, 19:50, 21:25,
  25 Oct 09:21; all on `template_2026-10-21b`, each with predictions, 119–120 fingerprinted files, no code conflict,
  the weights' fingerprint and the speed evidence columns.
* **The check, done now:** `dp.py predict` on a scratch copy of `live_2026-10-21_203628` (made by the old code).
  Against the original: 23 rows in the same order; `p_base_a`, `eta` and every other column bit for bit, except
  `spd_L` and the chances derived from it on the 14 men's matches. Cause: the live speed history changed since 21 Oct
  (its fingerprint differs: the 22 Oct repair and the 25 Oct collector fix). For every men's match the shift in
  log-odds equals b × the change in spd_L to 3e-15 (b 0.038388), women unchanged; the largest shift in a chance 0.305
  points. **So the new code changed no prediction;** a predict step re-run reads today's speed history, by design.
* **An incident of this check, put right:** a live-mode predict step archives its outputs into
  `predictions/<day>/records/` (`dp_steps.step_predict`, since 13 Oct). The scratch re-run therefore overwrote
  `predictions/2026-10-22/records/live_2026-10-21_203628.csv` and `.provenance.json` at 06:32. Restored at once from
  the run folder (the archive's source; `cp -p`): byte-identical, original times. Lesson for any later check of this
  kind: re-run a predict step only on a copy whose `run.json` mode is not "live", or with the archive step bypassed.
* **Step 1 finished, 27 Oct:** the owner asked what the hook was ("I dont understand why it would expect any effort
  level?"), was shown it, and answered "expect xhigh". The owner's own `~/.claude/settings.json`: the SessionStart
  hook's expected effort changed from "high" to "xhigh" (pattern and message only). Checked: the file parses, and the
  hook's command run by hand exits 0 and prints nothing.

**27 Oct, about 07:40 PDT: the owner's reply to step 2's plain explanation, and what the run records showed.** Verbatim:

> I think this is a good idea in theory, but im concerned its going to add a lot of overhead. 7 minute process randomly
> during the middle of the night or whatever every day where I may shut down my computer or have other gpu processes
> randomly. I could imagine that it could block bets incorrectly. These two things are useful "Missing results. In a
> main-draw round 2 or later, if a player's previous-round result isn't in the data yet, the model doesn't know about
> yesterday's match. Today only qualifying is checked for this. What each bet rests on. For example, "this bet exists
> only because of the serve-speed nudge, and the speed data is 9 days old."" But what would be way more useful is if
> there was some sort of intelligence that identifies the missing information AND RETRIVES IT with a warning that A) its
> happening (may slow things down) B) it happened or failed Is this possible to built practically? is there a way to
> reduce the time significantly for the check?

Read from the run folders to answer it; no code changed, nothing written but this entry.
* **The replay's time, corrected.** From each run's `steps.json`: the replay proofs since 13 Oct took 9–27 minutes in
  all, and the part that builds and compares the 57 inputs (work tree, tables, states, patterns) 5–15, the table build
  alone 2–8. The comparison does not need the fit (the GPU step); `run_day --no-fit`, which already exists, stops after
  the inputs and the gate. The "about 7 minutes" told to the owner earlier on 27 Oct comes from the 10–11 Oct measurement
  (daily prediction README) and is out of date. Bet-day runs since 18 Oct took 13–25 minutes (50–61 when they leave a
  checkpoint), not the "~7 min warm" of the master pipeline README; the fit is 1–3 of them.
* **What was missing on bet days, 13–25 Oct** (`gate.csv`, `gate_missing.csv`, `refresh.json` of every live run):
  * The gate blocked 6 of 13 matches on 24 Oct at 07:42 and 17 of 22 at 19:50: a qualifying round 2 with no round 1 in
    the data. None were blocked at 21:25, after Part 14's TennisLive fill.
  * On 24 Oct at 21:25, 8 matches took the 1-point edge (16 qualifying matches without a box score).
  * On 20 Oct, 1 qualifier had no qualifying match (filled since Part 17). On 19 Oct, 1 team event was noted.
  * The refresh's own box-score fills filled 0 in every run.
  * The Tennis My Life download was held (exit 1) in 14 of 22 runs since 11 Oct; the run then continues on the copy
    it has. (Said as "17 of 22" to the owner while checking; 14 is the count.)
* **Main-draw previous rounds, 18–25 Oct.** For every live main-draw match after an event's first round, I looked up
  each player's previous round in the run's own Stage 0 copy. 15 players had none, in 4 runs, all at events whose first
  round was complete in the data: byes for the top seeds. Ningbo's Stage 0 draw size is 32 for a 28 draw. None
  missing.
* **Found: a whole week missing from four bet-day runs, with no warning.**
  * **Which runs:** 19 Oct 07:57 and 17:32, 20 Oct 08:15 and 09:00, all on `template_2026-10-16` with the same base
    tree and work tree as 18 Oct's runs.
  * **What was missing:** every match of the events of the week of 12 Oct, searched by name at any date. That is Wuhan
    (WTA 1000, 55 matches) and the six men's Challengers (Jinan, Catania, Maia, Olbia, Santa Cruz 2, Roanne; 180–186
    matches).
  * **Before and after:** the run of 18 Oct 13:59 holds them, and the run of 21 Oct 18:49 holds them again.
  * **Matches affected:** by the 21 Oct copy, qualifying included, 13–20 matches of each run had a player who played
    that week.
  * **The bet sheets made from these runs:** 19 Oct 08:11, 19 Oct 17:46, 20 Oct 08:47 (all 23 blocked, for a stale
    quote) and 20 Oct 09:14. On them, 13 of 20 "BET" lines (10 distinct matches) were such matches.
  * **The history check saw it and passed it.** It recorded the fall in its "future" count: 375 on 18 Oct, 174 on 19 Oct,
    272 on 20 Oct, 591 on 21 Oct (WTA T1000: 60, 5, 5, 60). It still said "allowed", because it compares with the frozen
    reference of 8 Oct and counts every later match as "future". Nothing compares a run with the run before.
  * **The cause is not established.** The lead is the held Tennis My Life files (`2026_challenger.csv` and
    `2026_wta.csv` were held on 19–20 Oct), unproven.
  * **Not known:** whether the picks would have differed with the week present (those days were not re-run), and
    whether the 25 Oct hold of the men's `2026.csv` lost anything (no later table to compare with).
* **Offered to the owner, not decided:**
  1. A guard that compares each run's results with the previous run's and restores vanished rows from that copy, with
     a loud message.
  2. One step that fetches what is missing, announcing each fetch before it starts and its result after. Its parts:
     retry a download held as "being rewritten"; extend the TennisLive fill to main-draw previous rounds and to
     qualifying box scores; serve speeds on demand.
  3. The replay demoted: run with `--no-fit` by the agent who changes the engine's code, no nightly job, a note on the
     sheet and never a block.
  4. The cause of the 19–20 Oct hole found, and those days re-run to see whether the picks change.

**27 Oct, about 09:00 PDT: the owner's next instruction, and an audit started.** The owner pasted the five steps of the
reply (a check that nothing vanished; the cause and a re-run of 19–20 Oct; the fetch-what's-missing step; what each
bet rests on; the replay as described) and wrote, verbatim: "Audit these steps are the best ones with another agent.
Then if that agent signs off on it as is, execute it". Read as: an independent agent audits the five steps; executed
only on a sign-off "as is"; any change it asks for goes back to the owner first.
* **Other sessions, read first:** Part 19 (`tennis-predictions-d1`, today) built A7's grading and graded the 19–20 Oct
  runs. P17.12 (`tennis-predictions-ad`, today) found Tennis My Life's file of events under way and its archived copies
  (`data/raw/public_dump/tennis_my_life/superseded/`), and the canary of 26 Oct flags Tennis My Life's manifest SHRANK
  and REVISED (put to the owner by -ad). Both sessions edited the live path between 08:07 and 08:43.
* **The auditor:** a read-only planning agent. Brief (summarised, the full text is in this session's transcript): the
  owner's goals verbatim; the five steps with their meaning; the evidence as claims E1–E7 to verify, each with where
  to look; the unverified lead on the cause (a held yearly Tennis My Life file while the file of events under way has
  dropped the finished week); six questions (the steps and their order; step 1's baseline, false alarms and action;
  the re-run's validity; step 3's practicality; steps 4–5; the evidence); a first line `VERDICT: SIGN OFF AS IS` or
  `VERDICT: CHANGES NEEDED`. No file edits, no GPU, no network.
* **Meanwhile, a fault of mine fixed** (Part 10's step 1, not one of the five steps): `test_health_signals.py::
  test_the_acknowledged_flags_are_real_canary_flags` failed since the canary of 26 Oct (reported by -d1 and -ad). It
  required each acknowledgment to be a flag the latest canary gives, so `sackmann_tennis_atp:ARCHIVE` failed once
  Software Heritage answered again and the flag cleared. Now it checks the intent: each acknowledgment names a watched
  item and one of the canary's flag words (`canary.WATCH`; GONE, STALE, SHRANK, REVISED, TERMS, ARCHIVE, UNARCHIVED),
  with two typos of its own that must fail. 7 of 7 pass. No acknowledgment or data changed; -d1 and -ad told.
* **A second fault of mine, found then (22 Oct's step 1):** `test/data_continuity/test_rebuild_and_schedule.py`, 2 of
  24 failing: `test_canary_flags_compare_first_word` and `test_offline_canary_raises_nothing`. Both patch
  `scheduled.CANARY_LATEST`, but since Part 10 `scheduled.canary_flags()` delegates to `health.canary_flags()`, which
  reads `health.CANARY_LATEST`, so they read the real canary file. Failing since 22 Oct: I ran `test/master_pipeline/`
  then, not `test/data_continuity/`. `tennis-predictions-d8` had claimed both test files at the owner's request
  (until about 16:00 PDT), so I left the fix to it and sent it the cause (patch `H.CANARY_LATEST` and point
  `H.CANARY_KNOWN` at an empty file). **Lesson:** a change to a shared module is followed by every test folder that
  imports it, not only the study's own.
* **The cause, from a peer's reading of the download log** (`tennis-predictions-ad`, message of about 09:30 PDT, read
  from disk by that session, not yet checked here):
  * No accepted `2026_challenger.csv` between 12 Oct 14:30 and 21 Oct 12:52 UTC, and no accepted `2026_wta.csv`
    between 15 Oct 14:30 and 21 Oct 12:52 UTC. At 21 Oct 12:52 UTC, 2025_wta, 2026_wta and 2026_challenger were
    accepted after review.
  * That fits the hole: present on 18 Oct, missing on 19–20 Oct, back on 21 Oct. The unchecked link is that Tennis My
    Life's file of events under way dropped the finished week on 19 Oct, while the yearly files that took it in were
    held.
  * The canary's alarm of 26 Oct (Tennis My Life's manifest SHRANK and REVISED) is, by the same reading, unrelated:
    SHRANK is mostly a line-ending artefact (`canary.py` takes the allowance from the copy already replaced), and
    REVISED is genuine cell corrections the download accepts.
  * Its suggestion: a "lagging" check at the source, alarming on a current-season file whose manifest is newer than
    our copy for more than a day, or a held version still pending.
  * Forwarded to the auditor, to weigh against step 1.
  * **The unchecked link, checked by the same peer** (second message, from the archived copies under `superseded/`,
    stamped by retrieval time, UTC):
    * `wta_ongoing_tourneys` holds Wuhan (52–55 rows) in every copy from 16 Oct 14:30 to 18 Oct 14:30, and no Wuhan
      from 19 Oct 14:30.
    * `challenger_ongoing_tourneys` holds the six Challengers in every copy to 18 Oct 20:57, and from 19 Oct 14:30 only
      the new week's events.
    * So the hold did no harm until Tennis My Life moved the finished week into the held season files.
  * **Its second suggestion:** a check at the download that every event in the previous file of events under way is in
    the new one or in the accepted season file. It would have fired at 14:30 UTC on 19 Oct, before any run. Also
    forwarded to the auditor. Not yet re-read here.

**27 Oct, about 10:25 PDT: the audit's verdict, CHANGES NEEDED.** The full report is in this session's transcript (86
tool calls, about 19 minutes). Per the owner's instruction, nothing is built until the owner decides.
* **Evidence:**
  * E2–E7 confirmed.
  * E1 partly right: the brief's "all six runs used the same model, base tree and work tree" was wrong. The 21 Oct run
    used `template_2026-10-21b` on `tnr_tpl1021`. The four holed runs and 18 Oct's did use `template_2026-10-16` on
    `tnr_tpl1016`, as this log's 07:40 entry says. The week's return on 21 Oct follows the acceptance at 12:52 UTC,
    not the model switch.
* **The cause is confirmed, and the hold itself was a false alarm.** The "gone" rows that held the files were
  corrections:
  * 2026_challenger's 31: San Diego 2 re-keyed, 2026-2971 → 2026-3175;
  * 2026_wta's 29: 14 winners reversed (Rouen 12, Dubai, Merida), 14 BJK Cup Finals rows relabelled QF → RR, 1 other.
  * The download keys rows by event id and winner and loser ids (`tennis_my_life.py:72–73`). Files of events under way
    are never checked for dropped rows.
* **Step 1 as designed fails on the record.**
  * Run to run by match id, it flags the hole at 19 Oct 07:57 and is silent by 17:32: the holed run becomes the baseline.
  * Later comparisons are false alarms, and restoring by id would duplicate matches.
  * Re-checked here (completed rows, by match id, then by tour, event, year and unordered player pair):
    * 18 → 19 Oct: 235 gone, 235 truly;
    * 19 Oct 07:57 → 17:32: 0;
    * 20 Oct 09:00 → 21 Oct 18:49: 60 gone, all present by identity;
    * 21 Oct 20:36 → 23 Oct: 136 gone, 130 present by identity, 6 WTA rows whose player ids changed.
  * The auditor's counts (45, 20) differ by filter; the conclusion is the same.
  * The held copies, re-read here: `held/2026_wta.8f6fb09ef0b0.csv` (19 Oct 07:30) holds Wuhan's 55 rows, and
    `held/2026_challenger.290817794982.csv` (19 Oct 07:30) holds the six Challengers, 31 each.
* **The revised plan the auditor would sign off on, in order:**
  1. **At the download:** pair "gone" rows with their corrected rows by event and unordered player pair (any round or
     winner), so corrections no longer hold a file. A continuity check, with carry-forward, on the files of events
     under way: every event of the previous copy must be in the new one or in the accepted season copy. If not, it
     says so and keeps the event's rows, from the held season copy when one exists. A test: the archived 19 Oct copies
     give back the 241 rows. A "lagging" line (a file held more than a day) on STATUS, A1 and the sheet. The held-file
     check run automatically, its verdict shown; auto-accepting is the owner's call.
  2. **Step 1 rebuilt as a detector only:** a ledger of completed matches over about 8 weeks, from the work tree's
     Stage 0 after the additions. Identity: event and unordered pair, or event, round, score and one player. It never
     restores or blocks: a loud line in A4 and an amber note on the affected matches. Placed beside the history step
     (`dp_steps.py:223–235`).
  3. **Step 4, with two additions:** "without speed" applied to both models in a Thinking run; each player's newest
     result date, and any held or carried file. The speed term reaches 0.154 log-odds.
  4. **The rest of step 3.** Dropped: "retry a minute later" (the manifest lags by hours: on 25 Oct it listed 546,316
     bytes at 07:30 and 09:21 while 546,322 and 546,416 came down) and bulk TennisLive fills (Challengers are not among
     its event types; a 150-request budget). The fill order: TML's own copies, main-draw previous rounds from the
     TennisLive results A2 already fetches, qualifying box scores, then speeds only where a player's last reading is
     older than his last match.
  5. **Step 5, with four fixes:** the first replay first (no `receipts/` folder exists yet); compare only the
     input-path files, and name them; principle 2 of the 22 Oct decision amended by the owner's word (a note, never a
     block); and say that a replay cannot see a data hole.
  6. **Step 2 last and optional.** If run: a control that reproduces each original `live_frame` with today's code
     (`template_2026-10-16` on `tnr_tpl1016`, checkpoint pinned, `LIVE_MAIN_DRAW_DATE=0`), data as of each run's time
     from `superseded/`, then the same with the seven events' rows from the held copies. Matchups, prices, `spd_L` and
     Thinking's chances held fixed. A7's grades decide nothing (model and Pinnacle within 0.006 log loss on 21–36
     matches).
* **The state now, checked here:** this morning's download accepted `2026_wta.csv`; `2026.csv` and
  `2026_challenger.csv` were accepted on 26 Oct. Last week's finished events are in them (Almaty, Brussels, Lyon 27
  each; Ningbo 27; Osaka 31; the week's Challengers 30–31), and this week's are in the files of events under way. No
  hole for the next bet day.
* **A correction of mine to the owner:** the download-level check "would have fired about an hour before" the first
  19 Oct run. 14:30 UTC is 07:30 PDT and that run started 07:57 PDT: about half an hour.

**27 Oct, after 10:25: the report to the owner.** The verdict, the cause, the revised plan in six steps and three
decisions, with my recommendations: (1) Tennis My Life's corrections go through automatically when every "vanished" row
has a corrected twin, "same event, same two players" (recommended yes); (2) the replay check a note, never a block
(recommended yes); (3) the 19–20 Oct re-run, last (recommended yes: it sizes how loud the bet-time detector should be).

**28 Oct 2026, from about 08:30 PDT (session resumed after a context summary; this log re-read first): the owner's
answer, and the execution.** Verbatim:

> I approve the plan and
> Decision 1 and 2 I approve.
> However, right now a few hours of computer time and 20 minutes of graphics card is not what I want.
> After you execute the plan, considering 1 & 2.
> Mention to me you are done and suggest the 19-20 oct re-run again

* **Read as:** build the revised plan's steps 1–5 in the auditor's order, with decision 1 (corrections pass) and
  decision 2 (the replay a note, never a block) as the owner's words; **not** step 6 (the 19–20 Oct re-run), to be
  suggested again at the end. The first replay of step 5 (inputs only, `--no-fit`, no graphics card, 8–15 minutes) is
  part of step 5, not of the declined re-run; run only when no bet day is on.
* **What decision 1 covers, and what it does not** (my reading of "same event, same two players", checked on the held
  copies before any code; scratchpad `pairing_probe.py`, read-only): a vanished row pairs with a new row of the same
  event, by id or, when Tennis My Life renumbered the event, by the same name and date, with the same two player ids in
  any order, any round, date or score. **Not covered:** a row in which a player's id changed (a different player, or
  the same one re-identified); those still count as vanished, and more than 5 still hold the file for review. What the
  held copies show:
  * 19 Oct, `2026_wta`: 28 of 29 pair (10 winners reversed with a score change, 4 winners reversed, 14 rounds
    relabelled); 1 left (Rouen R32: a player id and the winner both changed), within the 5 allowed: **accepted**.
  * 19 Oct, `2026_challenger`: 31 of 31 pair by name and date (San Diego 2 renumbered): **accepted**.
  * 28 Oct (this morning's holds): `2022_wta` 62 of 62 and `2023_wta` 29 of 29 renumbered events: **accepted**;
    `2025_wta` 0 of 40 (35 a player's id changed, e.g. "Xiyu Wang" 216016 to "Xin Yu Wang" 216133; 5 an id and the
    score or both ids): **still held**.
* **Found while reading, not this work's fault:** the "size differs from the manifest" hold (a manifest that lags by
  hours) held 14 versions between 22 and 27 Oct; each went in a day later. Left as it is (the plan keeps it); the
  carry-forward below covers the harm it could do.
* **Peers, 08:35–08:50:** `tennis-predictions-73` (Part 21) edits `stage0_build.py` (TML's re-spelled names);
  `tennis-predictions-ad` claimed `canary.py`, `id_aliases.csv`, `src/pipeline/live.py` (`_stage0_keys` only) and
  Part 22. My claim sent to -ad, -d2 and -d8 (message `01aeedef…` to -ad): `tennis_my_life.py`, `health.py`,
  `scheduled.py` (`job_tml`), `overview.py`, `readiness.py`, `diagnostics.py`, `bet_sheet.py`, `data.py`, `dp_steps.py`,
  `dp.py`, `dp_common.py`; later, after asking, `qualifying.py` and `earlier_rounds.py`; new tests; the decision
  amendment, a new decision for (1), CLAUDE.md. I stay out of `live.py` until -ad is done.
* **The plan, with the check for each step:**
  1. **At the download** (`tennis_my_life.py`): the pairing of decision 1 (check: the held copies above give the
     counts above); a continuity check on the three files of events under way with carry-forward (check: the archived
     copies of 18–19 Oct give back the 241 rows, 55 Wuhan and 186 Challengers); the corrections and the rows TML
     removed listed in `_changes.jsonl`; a Tennis My Life status (held over a day, carried, corrected) in `health.py`,
     on STATUS, A1 and the bet sheet, and in the scheduled task's alert; the held-file check run by the scheduled task
     on a file held over a day, its verdict shown, never accepting.
  2. **The bet-time detector**, beside the history step: a ledger of the finished matches of about 8 weeks from the
     work tree's Stage 0 after the additions, found again by identity (event week and the two players, else event week,
     round, score and one player); never restores or blocks: a loud A4 line and an amber note per affected match.
     Check: the 18–21 Oct run folders replayed through it (the hole flagged in both 19 Oct runs and both 20 Oct runs;
     the renumbered 60 and 136 not flagged).
  3. **What each bet rests on**, on the bet sheet: the bet without the serve-speed term (both models in a Thinking
     run), without the patterns, each player's newest result and speed reading, held or carried files. Check: the
     sheets of 19–25 Oct remade from their runs' files.
  4. **The fetching, announced:** "fetching / filled / failed" lines for every fill; TennisLive's results for a
     main-draw previous round and qualifying box scores; speeds only where a player's newest reading is older than his
     last match. Check: per fill, a test and one live-day dry run.
  5. **The replay**: the first replay (`--no-fit`) writes the first receipt; the sheet compares only the input-path
     files, names them, and says that a replay cannot see a data hole; a note, never a block (decision 2).

---

# Part 11 (23 Oct 2026): a notebook kernel running older code than the files on disk

Kept by Claude Opus 5.5 (`claude-opus-5-5`), Claude Code in VS Code, session `3ae5ac26-1afa-4543-8d6b-0bd0d2eea280`
(`tennis-predictions-28`). Local time PDT (UTC−7). **Opened at about 08:38, after the diagnosis, the change and its
tests** (08:27–08:37), not before the first step as the log rule asks; written from the session's own commands and
outputs, in order.

## P11.1 The request (verbatim)

The owner pasted the A4 cell and its output, with: "Fix this issue". The output ends

> RuntimeError: dp_common.py: cannot read its default INSTANCE_ID / DP_BASE_TREE

raised in `train.py:54, in dp_defaults()`, called from `train.py:81, in dp_env()`, called from `predict.py:152`
(`env = {**dp_env(), ...}`); the last frame shows "Error retrieving source code with stack_data".

## P11.2 What the files showed, before any change

* **The file on disk has no `dp_defaults()`.** Part 9 removed it (`train.py` saved 22 Oct 13:13), and the engine's
  default instance with it (`dp_common.py` saved 16:34). The committed `train.py` (HEAD, 22 Oct 12:09) still has it:
  defined at line 47, the message at line 54, called by `dp_env()` at line 81. These are exactly the traceback's frames.
  The old function read the default out of `dp_common.py`'s text on every call, so old code failed on the new file.
* **The kernel:** the only `tennis` kernel running (pid 35664) started 21 Oct 18:40:42, before every 22 Oct edit. The
  notebook imports the layer once (SETUP), and nothing reloads it. It built matchups at 18:43 and 20:31 on 21 Oct and at
  08:05 and 08:26 today.
* **Changed since that kernel started:**
  * in `src/pipeline/`, on 22 Oct: `readiness.py` 11:28, `bet_sheet.py` 11:37, `live.py` 11:43, `qualifying.py` 12:06,
    `train.py` and `diagnostics.py` 13:13, `overview.py` 16:21;
  * the engine's `dp_common.py` and `dp.py`, 16:34.

  Which of these the kernel held old copies of depends on when it first imported each. It certainly held the old
  `live.py` (A2 ran at 18:43 on 21 Oct): today's linking file lacks the `qualifying` column that the current
  `todays_matches` writes.
* **What the old code reached:**
  * no live run since 21 Oct 20:36;
  * the three bet sheets in `predictions/2026-10-22/` were made on 21 Oct (19:50, 21:18), before the changes;
  * today's Pinnacle pull (15:26 UTC) ran as its own process, so on current code. It lists 43 matches, none of them
    qualifying, so the old `live.py` lost nothing today;
  * A4 stopped before its lock and work tree, so neither was left behind.

## P11.3 Interpretation acted on

* "Fix this issue" = A4 runs again; and the next kernel that outlives a code change says so plainly, instead of
  failing this way or silently running a replaced rule.
* **Today's fix needs no code: restart the kernel.** Nothing in the files is wrong (P11.5).
* **The lasting part is an agent's choice.** It applies principle 7 of the integrity plan ("a run notices if its code
  changed under it") to the notebook's kernel; step 6 is otherwise untouched. A call through `tp.` refuses when a file
  of `src/` the kernel imported has changed on disk since; the refusal names the files and says to restart.

Set aside:
* reloading changed modules by themselves (`%autoreload`-style): a partial reload mixes versions again, and files the
  kernel made with the old code (a matchups CSV) would stay in use. A restart makes the bet-day cells run again;
* editing the notebook's SETUP cell: the owner has the notebook open, and VS Code would keep a stale copy of the file.

## P11.4 What changed

* `src/pipeline/__init__.py`:
  * **an import hook** that finds nothing. For each module read from `src/`, by package name or by bare name (a folder
    of `src/` on `sys.path`), it notes the file's time, size and SHA-1 as the import read it;
  * **`_changed()`**: a file whose time or size moved and whose hash differs. A rewrite with the same text counts as
    current;
  * **`StaleKernel`**, raised by every `tp.<function>` before it runs. A name's first look-up is checked before its
    module is imported, because a new module importing an old one can fail there;
  * **on only in an IPython session** (`get_ipython()` not None). A script imports, calls and exits, and each of
    `retrain.sh`'s `python -c` steps makes one call. `TP_CODE_GUARD=1` or `0` forces it (the tests);
  * the records survive a reload of the package.
* `test/master_pipeline/test_code_guard.py`, 10 tests:
  * eight run the real `__init__.py`, copied into a temporary repository beside stand-in modules, in a fresh
    interpreter;
  * two check the real package: a record made to differ (no file touched), and the wrapped calls keeping their
    signature and help.

## P11.5 Checks, and what was seen

* **The failure reproduced.** With the committed `train.py` loaded in its place, `tp.predict_day(<08:26 matchups>,
  dry_run=True)` ended with the same three frames and message (scratchpad `repro_a4.py stale`).
* **On the files as they are (a restarted kernel), A4's dry run passes:**
  * the model-age line;
  * the template check OK on all five items (`template_2026-10-21b`: 57 inputs, Pinnacle first on this frame, the
    layer, seeds 0–15 for 2026, the tree's layer config);
  * "7 matches pass the daily pipeline's checks";
  * `run_day` with `DP_INSTANCE=template_2026-10-21b DP_BASE_TREE=C:\Users\zerom\tnr_tpl1021`.

  With `"tabpfn35_thinking"` (dry): `template_2026-10-21b` has no Thinking fit for 2026 (both 21 Oct runs were local),
  so its first Thinking run makes the paid season fit, as the cell says. The dry-run receipts went to the scratchpad,
  not `runs.jsonl`.
* **The guard.** Its 10 tests pass (0.8 s). On the same case, the package before the change ran the old function after
  its file changed: "v1" while the file said "v2". With the guard, this morning's A4 (`train.py`'s record set to the
  committed text) stops with the message before anything runs.
* **`test/master_pipeline/` in full: 102 passed** (252 s: the 92 of 22 Oct and the 10 new). The suite ran before one
  later line (the hook gives up quietly if its own search raises). After that line:
  * the 10 guard tests pass again;
  * an IPython session with the guard on ran, on the real repository: SETUP's import, the template check, the matchups
    check and A4's dry run. There was no false stop; 19 modules of `src/` were noted, none changed (scratchpad
    `ipython_session.py`).

## P11.6 Threats to validity, and where a flaw would hide

* **Modules imported before `src.pipeline`** are noted as their files stand at the package's import, so a change
  between their import and that moment is missed. In the notebook nothing of `src/` is imported before SETUP.
* **Only calls through `tp.` are checked.** A cell that imports a module of `src/pipeline/` itself is not. The
  notebook's cells all go through `tp.`, apart from `tp.config.interpreter` in SETUP.
* **Any change to a loaded file refuses, a comment included.** The cost is a restart (minutes), against running a
  replaced rule. If agents edit `src/` often on bet days, the owner will restart often.
* **A change during a call is not checked.** The engine's steps run as fresh processes and read the files as they are.
  Principle 7's "a live run notices" stays with step 6.
* The guard decides nothing in a forecast: no pick changes.

## P11.7 Reviewer checklist

* Is every name the notebook calls checked? `__getattr__` wraps every callable of `_NAMES`, and
  `test_no_module_shadows_an_exported_function` still holds each to callable and not a module.
* Could the hook change what is imported? It always returns None, and the usual finders import.
* Is it off outside IPython? See `test_a_script_runs_as_before` and `test_the_guard_is_on_in_an_ipython_session`.

## P11.8 Reproduction

* `./python.sh -m pytest test/master_pipeline/test_code_guard.py -q`
* In the notebook: after an edit to a file of `src/` that the kernel has imported, the next cell refuses with "STOP:
  ... was not run". Restart the kernel and run SETUP, and it runs.

---

# Part 12 (23 Oct 2026, 11:40–11:55 PDT): A2 stopped on a qualifying event with no finished match

Same session as Part 11. Opened after the fix and its checks (written from their outputs, in order).

## P12.1 The request (verbatim)

After restarting the kernel (Part 11), the owner pasted the A2 cell and its output, with: "Fix this". The output ends
with `KeyError: 'draw'`, raised from `live.py:298` (`_link_qualifying`, the call of `Q.round_from_results`) at pandas'
`range.py:535`. The first frame is the new guard's wrapper, so the kernel ran the current code.

## P12.2 What the files showed

* The listing of 11:39 (82 rows) holds Saturday's qualifying of WTA Tokyo (a 500) and WTA Guangzhou (a 250). This
  morning's listing had none, and this was the first live listing of a round 1 since Part 8.
* TennisLive's answer for Tokyo, fetched at 11:39, is well formed: status "ok", its usual keys, `totalCounts.singles`
  12, `groups: []`. Twelve matches are listed and none is finished, so the results hold no match.
* `TennisLive.results` makes `pd.DataFrame(section_rows(...))`. An empty list gives a frame with no columns (a
  `RangeIndex`), and `round_from_results` filters on `rows["draw"]` before its own "no qualifying result yet: round 1"
  branch. Hence `KeyError: 'draw'`.
* **Why the tests missed it:** `test_qualifying.py`'s TennisLive stand-in returned an empty frame *with* columns, which
  the real reader never gives.

## P12.3 What changed

* `src/pipeline/qualifying.py`:
  * `round_from_results`: a table with no row reads as round 1, the same reading and words as a table with no
    qualifying row. This is the rule as Part 8 built it, not a new one.
  * `TennisLive.results`: an "ok" answer without its list of matches (`data.groups` not a list, as after a change of
    the site) stops TennisLive for the linking, as the reader already does for an answer with an error. The linker
    then reads Tennis My Life's rows alone, which never give a round 1, and says why. **An agent's choice:** without it,
    such an answer would read every listed qualifying match as round 1.
* `test/master_pipeline/test_qualifying.py`: two tests on the real reader, run on Tokyo's answer saved as its fetch
  saves one (no request); the stand-in now returns what the real reader returns (no rows, no columns).

## P12.4 Checks, and what was seen

* **Reproduced first:** on the code before the change, both new tests fail, the first with `KeyError: 'draw'` at
  `range.py:535`, the owner's line.
* After the change: `test_qualifying.py` 10 passed, the 16 Oct linker test included (with the faithful stand-in).
* **A2 and A3 on the listing of 11:39, with the real TennisLive** (scratchpad `a2_check.py`; the matchups CSV written
  to the scratchpad):
  * 78 listed in the window, 27 linked;
  * all 21 qualifying matches (Tokyo 10, Guangzhou 11) placed as Q1, each event built from its 2025 edition (Tokyo
    500, draw 28; Guangzhou 250, draw 32; hard courts), with the main draw's start 26 Oct;
  * 6 main-draw matches;
  * `check_matchups`: 27 of 27 pass the daily pipeline's checks.
* **`test/master_pipeline/` in full: 103 passed, 1 failed** (262 s). The failure is
  `test_notebook_is_clean_and_calls_only_existing_functions`'s first assertion: the notebook holds no saved outputs.
  The owner's VS Code saved it at 11:38 with the morning's outputs (7 cells with an execution count, 6 with outputs),
  and the run of 08:37 passed the same test on the clean file. Its other checks, run by hand on the saved notebook,
  pass: every cell compiles, all 47 `tp.` names it calls exist, and SETUP sets `MODEL` and `DRY_RUN`. The outputs were
  left in place (the owner's open file); clearing them before a commit makes the test pass.
* **No replay proof run.** The change decides only whether a round is read when TennisLive lists no finished match;
  the rows it then writes are the round-1 rows built from a previous edition that Part 8's replay reproduced bit for
  bit. The engine is not touched.

## P12.5 Weak points

* **An "ok" answer with an empty list while matches are finished** (a fault of the site) would read a round 2 as
  round 1. For men, Tennis My Life's rows check it (`tml_agrees`); for women nothing does on the day.
* **Editing `qualifying.py` while the owner's kernel holds it** makes Part 11's guard refuse the owner's next cell:
  restart once more.

# Part 13 (24 Oct 2026, about 08:10–08:45 and 19:35–20:30 PDT): a listed start no longer blocks

Session 2a717397-1bea-4c10-867c-714bb6b4c4b0. The decision:
[2026-10-24-start-time-never-blocks.md](../../decisions/2026-10-24-start-time-never-blocks.md).

## P13.1 The requests (verbatim)

First, with cell A5 selected (the sheet of 08:08 had blocked three matches as "The match has started."):

> Why would this code block fights that already have started according to the model? Clearly I cant bet on the fight if
> its in the past, so why not output a prediction? what harm is there in that? If the models timing is wrong and I CAN
> bet on it still, it just wasted my opportunity

Claude answered with the evidence below. It recommended keeping a block only for a match Pinnacle shows in play, read
from Pinnacle's own market at the reprice, and asked whether to make that change now. The owner replied:

> Yo, it just doesnt matter if its started in the eyes of the model. If it started I cant bet it. If it uses a "live
> line" then I wont be able to bet it. Their live bet section is different than pre-bet. So there's literally zero
> risk. just give me the prediction

**Read as:** no block for a start time at all, not the state-based block Claude had proposed. Claude also applied the
owner's rule at A2 and the reprice, which dropped or skipped a match whose listed start had passed even while Pinnacle
still listed its pre-match price. That extension is marked as Claude's reading. In-play markets stay out: a live price
is never the model's input.

## P13.2 What the files showed (before any change)

* **The rule's origin.** `diagnostics.py` blocked when the listed start from the run's matchups CSV (A2's pull) had
  passed. It was choice 6 of Part 2, an agent's choice, never tested.
* **A reprice never refreshes the start.** `live_prices` writes no start time, so a match Pinnacle had pushed back
  stayed blocked even at a fresh price.
* **Pinnacle's own listing every 10 minutes**, 22 Oct 04:50 to 23 Oct 16:40 UTC (P11's capture, 216 reads, raw
  copies). Scratchpad `start_vs_live.py`; its table is `start_vs_live.csv`.
  * Tour level: 32 singles matches were seen pre-match before their first listed start, then in play.
  * 27 of 34 had their listed start moved while pre-match, every time later (median 120 minutes, up to 510).
  * 26 of 32 could still be bet pre-match after the start first listed, a median 80 minutes past it (11 for over
    2 hours; the longest 7 h 10 min: Altmaier v Fritz, Lyon QF, first listed 08:00, open at 15:10, in play at 15:20).
  * 15 of 32 went in play more than 10 minutes before the start listed at their last pre-match reading (median
    43 minutes early). Rybakina v Kawa (Ningbo QF) went in play while listed about 14 hours later.
* **Pinnacle's market states**, from the staged reasons. The cutoff equals the listed start on 99.4% of pre-match
  readings. Across every level, doubles included, 83 of the 246 matchups whose cutoff passed reopened with a later
  time. In 243 saved pulls, the same pair was never listed twice pre-match, so no new ambiguity guard was needed.
* **Today's sheet (08:08 PDT)** blocked three matches as started:
  * Duckworth v Kovacevic, Basel Q1, listed 14:36:01 UTC, 13 s after the price was read: a bet on Duckworth at +132;
  * Bertola v Paul, Basel Q1: a pass;
  * Moutet v Machac, Vienna Q1, listed 15:00: a pass.

  Only one Pinnacle pull was made that day (14:35 UTC), so whether each had started cannot be read from disk.

## P13.3 What changed

* `src/pipeline/diagnostics.py`: the block "the match has started" is removed (the owner's words, quoted in the code);
  the module's rules text says so. `minutes_to_start` stays in the record.
* `src/pipeline/live.py` (Claude's reading):
  * `PAST_LISTED_START` holds the staging's two reasons for a pre-match price still listed after its listed start or
    cutoff;
  * `todays_matches` keeps such a match in the window and links it (before, the window `start > now` dropped it
    without a word);
  * `live_prices` reprices it.
  * In-play markets stay out of both.
* `src/pipeline/bet_sheet.py`: the plain reason "The match has started." is kept for records made before 24 Oct.
* Not changed: the notebook's A5 comment still lists "a started match". The notebook was open in the owner's editor,
  so it was not edited. `src/ingest/pinnacle.py`'s staging is not changed either.

## P13.4 Checks, and what was seen

* New tests in `test/master_pipeline/test_master_pipeline.py`:
  * `test_a_passed_listed_start_never_blocks`;
  * `test_a_match_still_listed_pre_match_after_its_listed_start_stays_a_candidate`, with a synthetic pull: one match
    ahead, one past its start and cutoff, one past its start, one in play;
  * `test_reprice_keeps_a_match_still_listed_pre_match`.

  First run: 1 failed, from the test's own `is None` on a pandas NaN, which was fixed in the test. Then 3 passed.
* **Reproduced on the old code** (scratchpad `old_vs_new.py`: scratch copies with the old lines restored):
  * the priced replay's 23 matches with their listed start an hour past: old code 23 BLOCKED ("started"); new code
    8 BET, 12 PASS and 3 BLOCKED (the replay's gate);
  * the synthetic pull: old window keeps match 1 only; new window keeps 1, 2 and 3, and not the in-play match 4.
* **Today's sheet rebuilt as of 08:08:07 PDT** (write=False; its own stale limit and stake rule). 3 of 13 rows change:
  * Duckworth v Kovacevic: BLOCKED to BET, Duckworth +132, lowest +126, expected profit +2.9%, 0.879 units;
  * Bertola v Paul: BLOCKED to PASS;
  * Moutet v Machac: BLOCKED to PASS;
  * the other 10 are unchanged (2 BET, 2 PASS, 6 BLOCKED by the gate).

  The comparison script also counted 8 identical rows as changed, an artefact of comparing an empty pick with NaN.
* **The rebuilt sheet's own table:** BET on Duckworth (0.879 units, +132, lowest +126); PASS on Bertola (−264, worth
  −252) and on Machac (−156, worth −148), each with its player, chances and note.
* **The bet-day pulls of 20–24 Oct held one tour-level match the old A2 dropped:** Bonzi v Norrie (Lyon R1), at
  20 Oct 15:55 UTC, listed for 15:50 and still priced pre-match.
* **`test/master_pipeline/` in full: 106 passed, 1 failed** (350 s). The failure is
  `test_notebook_is_clean_and_calls_only_existing_functions`, the same as in P12.4: the owner's open notebook holds
  saved outputs (the STATUS cell, execution count 10). It is unrelated to this change.
* No replay proof: no input of the model changes.

## P13.5 Weak points

* **An in-play match keeps the run's pre-match price** on the sheet until the stale limit (60 minutes in the notebook)
  blocks it. A BET shown for it cannot be placed pre-match; the owner accepts this ("zero risk").
* **Polymarket trades during play.** A Polymarket price typed in for a started match is a live one, and the sheet cannot
  tell. Said once to the owner.
* **Past its cutoff, Pinnacle refuses pre-match bets until it sets a later time.** A2 now predicts such a match too: a
  BET on it waits for Pinnacle to reopen.
* **Editing `src/pipeline/` while the owner's kernel holds it** makes Part 11's guard refuse the owner's next cell:
  restart the kernel, run SETUP, then `RUN = tp.latest_run()` if needed.

# Part 14 (24 Oct 2026, from 20:18 PDT): the earlier qualifying rounds, from TennisLive

Session dd93a4a6-3a6e-47c1-838e-3ebf11a5cb9d. Opened at about 21:45, after the code and before the proof's result;
the entries up to P14.3 were written from the session's own outputs, in order.

## P14.1 The request (verbatim)

The owner pasted the bet sheet of the 19:50 run (5 BET or PASS rows, 16 BLOCKED, all qualifying round 2) with:

> Why so many blocked?
>
> "BLOCKED Fabian Marozsan v Tomas Machac: Data check: Tomas Machac's Q1 result at this qualifying is not in the data
> yet, so their inputs are incomplete (Tennis My Life has not published it yet). Fabian Marozsan's Q1 result at this
> qualifying is not in the data yet, so their inputs are incomplete (Tennis My Life has not published it yet).
> Qualifying Q2: both players won Q1 on TennisLive. Event built from its previous edition 2025-337 (2025-10-20)."
>
> This is annoying why cant I get this data? we need to get this data.

**Read as:** explain the block, then get the round-1 results into the live tables, from where they already are
(TennisLive, read at A2 to place the round). **Set aside:** loosening the gate (a missing result is not a missing box
score: decision 2026-10-14 keeps it a block); running the weekly feed early (women only, and it would change the
training tables). The design below is an agent's choice; the instruction to get the data is the owner's.

## P14.2 What the files showed (before any change)

* **The block** is the gate's rule of 22 Oct (`gate.previous_round_missing`): a qualifying round 2 or 3 whose player has
  no match of the round before in Stage 0. 17 of the run's 22 matches (8 ATP: Vienna and Basel; 9 WTA: Tokyo and
  Guangzhou), every one for this reason (`runs/live_2026-10-24_195045/gate.json`).
* **Tennis My Life:** the run's download (19:50) staged only the three ongoing files (last week's main draws). Its
  2026 men's qualifying file last changed on 23 Oct 07:30 and ends with last week's events (Almaty, Brussels, Lyon:
  qualifying played 17-18 Oct), so it lags by days, not hours. It carries no women's qualifying at all.
* **The lower-level feed** carries women's tour qualifying (`wta:TQ`) but builds on Wednesdays only; men's tour
  qualifying is outside its scope.
* **TennisLive already held every round-1 result on disk:** the results sections A2 fetched at 19:44 for the four
  events list all 40 round-1 matches (Vienna 8, Basel 8, Tokyo 12, Guangzhou 12) with winner, score and match-page URL.
  A2 read them to place the round and dropped them.
* **TennisLive's box scores:** equal to the history's on 99.6-100% of the qualifying levels measured (Slam and
  Challenger qualifying, every women's level; `docs/studies/tennislive_box_fill/`). Men's tour qualifying was not
  measured there.
* **The engine** already adds today's matches as Tennis My Life rows (`--live-rows`); Stage 0 does not force their
  placeholder result. No model input reads service games (which TennisLive does not give) or minutes.

## P14.3 Plan, and the source check

1. A2 (`src/pipeline/live.py`, `qualifying.py`): for a match after round 1, each player's finished wins at the event
   before it, from the results rows A2 already fetched, unless Tennis My Life holds them; the score from the listing,
   the box score from the match page (paced, receipts, raw copies). Written to `<matchups>_earlier.csv`.
2. The engine (`prediction_run/run.py`, new `prediction_run/earlier_rounds.py`): the sidecar's matches as live rows
   with their results (`live_role` "played"); `played_meta.parquet` dates them; `inject.py` pins each to its tour's
   current window around its day, as a live match is pinned.
3. Stage 0 (`stage0_build.add_live_rows`, `drop_replaced`): accepts "played"; the source's own row of the same match,
   when it stands, wins and the fill is dropped (LV3). Builds without live rows are untouched.
4. A3 (`readiness.py`): a round whose earlier round is in the sidecar is not reported blocked.
5. The proof: the 22 Oct replay of Almaty and Brussels round 2 (8 matches, 57 of 57 inputs bit for bit with Tennis My
   Life's round-1 rows), run again with those 16 rows dropped and filled from TennisLive
   (`dp.py run_day --replay-earlier tennislive`).

**Source check (before the proof; scratchpad `tl_vs_tml.py`, its table `tl_vs_tml_atp_tq.csv`):** TennisLive's pages
of last week's men's tour qualifying (Almaty, Brussels, Lyon: 36 matches, 36 pages fetched, receipts kept) against
Tennis My Life's published rows:
* scores equal on 36 of 36;
* all eight counts equal on 33 of 36 (Almaty and Lyon 24 of 24). The three differences, all Brussels round 1, are
  single points: Bertola v Mpetshi Perricard (loser's first-serve points won 64 v 65), Chidekh v Bailly (16 v 17),
  Dougaz v Gentzsch (serve points and first serves in, each 1).
* At match level that is 92%, below the 98% the gap-fill rule asks of training data. **An agent's choice:** use them
  live anyway. The alternative is a missing result (a block) or a result without a box score; a one-point difference
  in one match of twelve moves the 52-week and form inputs far less than the median 0.35 points the box-score gate
  review measured for a whole missing round.

## P14.4 What changed (files claimed by this session from about 21:10 PDT)

* **New** `src/eda/prediction_run/earlier_rounds.py`: `tl_score`, `tl_box` (the candidate builder's mapping of a
  TennisLive page, with its 45% swap guard), `finish_utc`, `uk_day`, `played_rows` (the sidecar's matches as live rows
  with their results, and their meta), `sidecar` (the path `<matchups>_earlier.csv`).
* `src/pipeline/qualifying.py`: `earlier_wins` (a player's finished qualifying wins at the event before a round);
  `TennisLive.page` (a match page, read from disk when held, else fetched on the linking's client: paced, receipt, raw
  copy, a refusal stops TennisLive for the linking); `MAX_REQUESTS` 20 -> 100 (a page per earlier round).
* `src/pipeline/live.py`: `_earlier` (one sidecar row per earlier round Tennis My Life's rows of the edition do not
  hold; the opponent named as Stage 0 knows them, by `_player`, or the round is left out with a note);
  `_link_qualifying` calls it for any round after Q1 read from TennisLive; `build_matchups` writes the sidecar (an
  empty one over a stale file at the same path) and keeps the list out of the `_linking` CSV.
* `src/pipeline/readiness.py` (A3b): a player whose round before is in the sidecar is "ready" with its box score, or
  counts toward the 1-point edge without one; otherwise the block as before.
* `src/eda/daily_prediction/dp_steps.py`: the matchups step copies the sidecar into the run's folder;
  `dp_matchups.live` passes it to `prediction_run/run.live_from_matchups`, which appends the played rows to
  `live_rows.parquet` and writes `played_meta.parquet`; `dp_tables.prep` copies that into the work tree's `run/`.
* `src/eda/prediction_run/inject.py`: `check` reports the earlier rounds held (never refuses); `pin` also pins each
  earlier round Stage 0 holds under the id predicted, with its tour's window around its day, the window measured
  before the live matches' first day as before (so the live matches' own windows do not move).
* `src/eda/predictability_diagnostic/stage0_build.py`: `add_live_rows` accepts `live_role` "played";
  `drop_replaced`: a played row replaces nothing and goes when a source row of the same match stands (rule LV3, logged
  only when a build holds played rows); a replay's "drop" row still removes the source's row first. Builds without live
  rows are untouched; builds with live rows but no played rows give the same tables and summary as before.
* The replay proof's option: `dp.py init/run_day --replay-earlier tennislive`, `dp_matchups.replay_earlier` (each
  target's players' earlier rounds: their TML rows "drop", the same matches "played" from TennisLive's raw copies in
  the repository) and `_tl_section`.
* **New tests** `test/master_pipeline/test_earlier_rounds.py` (7): the score, the box columns (and the swap guard), a
  real Vienna page, `earlier_wins`, Stage 0's `drop_replaced` with played rows (alone; the source published; a replay's
  drop; and the old behaviour without played rows), and A3b with a sidecar. One failed first, on the test's own data:
  TennisLive's set strings hold each player's own tiebreak points (a 7-6 winner's at least 7), which the code already
  read that way (36 of 36 real scores equal to Tennis My Life's). After fixing the test: with `test_qualifying.py` and
  `test/prediction_run/`, 36 passed.

## P14.5 Checks, and what was seen

* **A2 and A3 on the 19:44 listing** (scratchpad `a2_earlier.py`; the CSV and sidecar written to the scratchpad, no
  Pinnacle request, TennisLive pages fetched): 81 listed, 22 linked; all 17 qualifying round-2 matches carry their two
  round-1 matches, 34 rows, 34 with a box score, every opponent named by exactly one Stage 0 player (e.g. TennisLive's
  "Pablo Carreno-Busta" as "Pablo Carreno Busta"); every score in Tennis My Life's form.
* **The replay proof** (`runs/replay_2026-10-19_Q2_earlier_tennislive`, work tree `C:/Users/zerom/tnr_daily_earlier`,
  kept; checkpoint 2026-09-23 and frame as the 22 Oct replay): matchups record 16 earlier rounds, 16 TML rows dropped,
  16 filled, 16 with a box score, 16 under the same match id as Tennis My Life's, 16 scores equal. Stage 0's summary:
  `earlier_rounds_filled` 16, `earlier_rounds_superseded` 0; Almaty and Brussels round 1 are all `earlier_rounds` rows
  with box scores.
* **The proof FAILED the first time** (`runs/replay_2026-10-19_Q2_earlier_tennislive/replay_compare.json`, 20:50):
  27 of 57 inputs bit for bit, every match off somewhere. Two causes, read from which inputs moved:
  * **service games** (the large part): `form_hold` (0 of 8 equal, up to 0.21), `form_bp_faced_pg` (up to 0.28),
    `form_brk`, `formdef_bp_faced_pg`, and the hold inputs of the surface IOS. TennisLive lists no service games, and
    P14.2's "no model input reads service games" was wrong: the search ran for `sv_gms`/`SvGms` in a list of files that
    missed where the forms compute hold and break rates. The surface IOS, solved jointly, then moved slightly on every
    input (up to 0.04 on hold, about 1e-4 to 1e-3 elsewhere);
  * **the three one-point differences** of Brussels round 1 (P14.3): `ratings_iid`, `adjperf_tpw_2w`, `points_52w`
    differ on 3 of 8 matches, the serve forms on 1.
* **Service games derived** (`earlier_rounds.service_games`; scratchpad `svgms2.py`): from the score and the match's
  first server (TennisLive's `first_server_index`), games alternating through the match, a tiebreak taking its turn
  without being a service game: **equal to Tennis My Life's on 36 of 36** of last week's matches (counting the
  tiebreak as a service game: 15 of 36). TennisLive's game lists omit the tiebreak and some servers, so they are not
  counted directly. A page without a game-by-game record (1 of tonight's 34: Ibragimova v Saigo) has no first server;
  then its "Service games won" line's games played are used, only when they are the score's games as one of the two
  first servers would give them (14 + 13 for 3-6 6-2 6-4). That line comes from the live points and can be partial
  (Machac v Moutet: 7 + 6 for 6-4 6-4), hence the check. Tonight's sidecar: 34 of 34 with service games.
* Tests: 9 in `test_earlier_rounds.py` (service games, the fallback and its refusal added); with `test_qualifying.py`
  and `test/prediction_run/`: 38 passed.
* **The proof again** (`runs/replay_2026-10-19_Q2_earlier_tennislive_v2`, work tree `tnr_daily_earlier2`), with
  service games: see below.
* **The proof, second run** (21:00; `runs/replay_2026-10-19_Q2_earlier_tennislive_v2/replay_compare.json`): 34 of 57
  inputs bit for bit; the hold and break inputs now equal (the service games). **Non-IOS inputs: 5 of 8 matches bit
  for bit on all 36.** The other 3 are exactly the Brussels matches whose players' round 1 differs by one point
  between TennisLive and Tennis My Life (P14.3): `ratings_iid`, `adjperf_tpw_2w`, `points_52w`, `form_rpw_first`
  (and, for one of them, the serve forms), up to 0.020. The surface IOS, solved jointly, absorbs those three points on
  every match: at most 0.004 (`iosD_first_won`), about 1e-4 to 1e-3 elsewhere. So the code path reproduces training
  where the sources agree; what is left is the sources' own three points. **Not "verified" in the bit-for-bit sense of
  the replay proofs:** the residual is a data difference, measured next.
* **The forecast effect** (scratchpad `baseline_folder.py`, `compare_fits.py`): the same 8 matches fitted twice on the
  GPU (16 seeds, the full price grid, then stage 2 and the patterns), once on the replay's inputs and once on a copy
  whose inputs are the training frame's (`runs/replay_2026-10-19_Q2_training_inputs`). Largest difference per match
  over the whole grid: 0.05 to 0.24 points (final chance; 0.06 to 0.24 before stage 2), median about 0.1; the largest
  is a Brussels match with the one-point difference. Against: a missing earlier round's box score moved forecasts by a
  median 0.35 points in the gate review, and the gate asks a 1-point edge for one; a missing result is a block. The two
  fits' own grid read-back errors are 0.0004 and 0.0002, so GPU noise is not the difference.
* **Shown to the owner at 21:03 before going live:** without the fill, the 19:50 sheet (16 BLOCKED); with it, the
  next run's sheet. The owner was told to restart the kernel and run A1 to A5.
* **Owner's second message (verbatim, 20:47):** "Also if you are only patching this as "right now thing" also patch it
  so this doesnt happen again, and I can succesfully and accurately bet these qualifiers a day out when a similar issue
  happens." **Read as:** the fill must be a standing part of A2 and the run (it is: every linking fills every round
  after Q1), and the same gap elsewhere must be closed. **Found:** the same gap hits the main draw a day later
  (qualifiers' and lucky losers' qualifying matches: silently missing from round-1 inputs, a block from round 2).
  **Deferred to the next session, not tonight:** extending the fill to the main draw edits `src/pipeline/live.py`
  again, which would stop the owner's notebook (A5, A6 reprices) mid-evening. Its design is in the scratchpad
  (`main_draw_patch.md`); the replay candidates are Shanghai's first day (5 Oct week, 14 matches, 6 qualifiers;
  Shanghai filed its 2026 qualifying under an id of its own, the one such edition of 206 in 2025-26) and Beijing's (28
  Sep week, 16 matches, 9 qualifiers or lucky losers). Last week's first rounds are past the instance's cut-off.
* Documents: decision `docs/decisions/2026-10-24-earlier-rounds-from-tennislive.md` (the owner's words, the design
  marked Claude's), its line in the decisions index, and CLAUDE.md's qualifying and gate bullets.

## P14.6 Threats to validity, and where a flaw would hide

* **The proof is men's only**, as the 22 Oct one was. Women's tour qualifying reaches training through the feed (WTA
  API box scores first, then TennisLive's), with the feed's own event ids on its newest editions; no replay has ever
  compared a women's qualifying match's live inputs with training's. Tonight's women's round 2s are bet on that basis.
* **Three single-point differences in twelve Brussels matches** may be TennisLive's or Tennis My Life's error; either
  way the live input differs from the training input by them. Measured at 0.05-0.24 points of forecast on 8 matches:
  one week, one tour, small.
* **The live dating** (inject.pin on filled rows) is tested by a unit test, not by a replay: an exact replay holds the
  instance's timeline and never runs the pin. A wrong window would hide in the surface IOS inputs only (the forms and
  ratings follow each player's own order).
* **An opponent known to the feed only** (a women's player with no Stage 0 history before the feed) cannot be named, so
  that round stays blocked; tonight none.
* **A page fetched before its statistics were final** is held and not asked again; a page with incomplete statistics
  gives no box score (the 1-point bar), never a wrong one, unless TennisLive posts partial numbers as complete.

## P14.7 Reviewer checklist

* `replay_compare.json` of `_v2`: 34 of 57; non-IOS differences only on the three Brussels matches named in P14.3.
* `compare_fits.py` on `_v2` and `_training_inputs`: largest 0.2217 points (final).
* `tl_vs_tml_atp_tq.csv`: 36 scores equal; 33 of 36 boxes; `svgms2.py`: 36 of 36 service games.
* The next live run's `gate.json`: no "no Q1 match before this Q2" for a match whose sidecar holds the round;
  `inject.json`'s `check.earlier_rounds` and `live_window.earlier_rounds_pinned`; Stage 0's `live_rows` summary.

## P14.8 Reproduction

```
./python.sh <scratchpad>/tl_vs_tml.py <out.csv>          # TennisLive v Tennis My Life, men's tour qualifying 17-19 Oct
./python.sh <scratchpad>/svgms2.py <out.csv>             # the service-games rule
DP_WORK_TREE=C:/Users/zerom/tnr_daily_earlier2 ./python.sh src/eda/daily_prediction/dp.py run_day \
  --run data/studies/daily_prediction/runs/replay_2026-10-19_Q2_earlier_tennislive_v2 --replay-week 2026-10-19 \
  --replay-round Q2 --replay-frame data/studies/master_pipeline/qualifying_replay/replay_frame.parquet \
  --replay-earlier tennislive --checkpoint 2026-09-23 --no-fit --keep-worktree
./python.sh src/eda/daily_prediction/dp.py replay-compare --run <that run>
./python.sh -m pytest -q test/master_pipeline/test_earlier_rounds.py test/master_pipeline/test_qualifying.py test/prediction_run/
```
Kept for review, not deleted (cleanup is the owner's call): work trees `C:/Users/zerom/tnr_daily_earlier` and
`tnr_daily_earlier2`; run folders `replay_2026-10-19_Q2_earlier_tennislive`, `_v2` and `replay_2026-10-19_Q2_training_inputs`.
* **Final tests (21:12):** every changed module compiles; `test_earlier_rounds.py`, `test_qualifying.py`,
  `test/prediction_run/` and `test_master_pipeline.py`: 84 passed, 1 failed. The failure is
  `test_notebook_is_clean_and_calls_only_existing_functions`, the owner's open notebook holding saved outputs (as in
  P12.4 and P13.4), unrelated to this change.

## P14.9 The owner's run of 21:25, and Tennis My Life publishing results without box scores

* **The owner (verbatim, about 21:20):** "can I run it again and get the predictions for these matches now? this is
  so frustrating im missing tons of betting opportunties". Told to restart the kernel and run SETUP, A2, A3, A4, A5
  (A1 and A3b skipped to save time). Run `live_2026-10-24_212506`, finished 21:47; sheet
  `predictions/2026-10-25/bet_sheet_2026-10-24_2147.xlsx`.
* **What the run did:** the sidecar held all 28 round-1 matches of the 14 qualifying round-2 matches still listed (the
  20:10 ones and two of Tokyo's had started); `live_from_matchups` filled 28, all with box scores. The pin dated all 28
  (`earlier_rounds_pinned` 28; the tours' current windows: 0 days either side). Gate: 19 of 19 complete, none blocked;
  **8 with the 1-point edge** (the men's).
* **Why the men's had the bar:** the run's refresh (21:25) downloaded a new 2026 men's qualifying file from Tennis My
  Life holding Vienna's and Basel's round 1 **as results only** (box_status blank). Stage 0 superseded the 16 fills by
  those rows (rule LV3: `earlier_rounds_superseded` 16), so the TennisLive box scores were dropped and the gate saw 16
  earlier rounds without a box score. P14.4's "the source wins" was wrong for a source row without a box score.
* **Fix, engine half** (`prediction_run/run.py`: `tml_box_fills`, called by `live_from_matchups`; not imported by the
  owner's kernel, so no restart): a sidecar round the run's fresh Stage 0 already holds keeps its row; when that row has
  no box score and is Tennis My Life's, the two agree on the winner and every set's games, and its key names exactly
  one staged row, TennisLive's counts go into the run's `overrides.csv` (box source `tennislive_live`), as the WTA
  API's and the ATP's live fills do; an official fill of the same row, listed first, wins.
  * Offline on the 21:25 run's own matchups, sidecar and fresh Stage 0 (scratchpad `boxfill_test.py`): 16 override
    rows, 12 played rows (the women's).
  * A scratch Stage 0 build with them (`stage0_build.py --out-dir <scratch> --live-rows ... --box-overrides ...`):
    2,288 overrides applied (the decided 2,272 and the 16); Vienna's and Basel's round 1 are Tennis My Life's rows
    with full box scores; the women's round 1 the fills'.
* **Fix, linker half** (`src/pipeline/live.py._earlier`, applied after 22:00 so as not to stop the owner's notebook
  before the 22:00 matches): a round Tennis My Life holds is skipped only when its row has a box score, so a
  results-only row still gets its TennisLive box score at the next linking. `readiness.py` counts such a round as
  filled by the run.
* **Linker half applied at 22:00** (after the owner's 21:47 sheet and the 22:00 matches): `_earlier` skips a round
  Tennis My Life holds only when its row has a box score (`w_svpt`); `readiness.py` counts a missing box score that the
  sidecar holds from TennisLive as filled by the run ("ready once filled"). Tests: 2 more in `test_earlier_rounds.py`
  (the engine's override: given for a results-only row, refused when the two disagree on the winner, skipped when
  Tennis My Life has a box score; the linker keeping a results-only round); with `test_qualifying.py` and
  `test/prediction_run/`: 40 passed.
* **End to end at 22:01 on the latest listing (21:24) and the new Tennis My Life file** (scratchpad `a2_2200/`,
  `e2e_2200.py`): 19 linked; the sidecar holds all 28 round-1 matches (Vienna 8 and Basel 8 kept although Tennis My
  Life holds them as results); `live_from_matchups` on the 21:25 run's fresh Stage 0: 16 box scores given to Tennis
  My Life's rows, 12 played rows. The owner was told to restart the kernel and run SETUP, A2, A3, A4, A5.

---

# Part 15 (24 Oct 2026, from about 22:04 PDT): the bet sheet's market chance is the posted price's, vig included

Kept by Claude Opus 5.5 (`claude-opus-5-5`), Claude Code in VS Code, session `94e81d21-a59d-4e2a-9275-0ec426cc647a`
(`tennis-predictions-e1`). Local time PDT (UTC−7). Opened at about 22:12, after reading the code and before the first
edit; the before-snapshot (P15.4) was taken at 22:08.

## P15.1 The request (verbatim)

The owner pasted a row of the 21:47 sheet (`predictions/2026-10-25/bet_sheet_2026-10-24_2147.xlsx`):

> Sun 25 Oct 08:40	ATP Brussels F	Jan-Lennard Struff v Tallon Griekspoor	BET	Tallon Griekspoor	1.21	-121	-123	55.1%
> 54.7%	53.2%	+1.9	+0.7%
>
> ? if model change is 55.1% and market says 53.2% isn't that like almost 3.8% ROI? whats the 0.7%? is it 0.7% over a
> 3% threshold or something?

After the explanation (EV = 0.5512 × 1.8264 − 1 = +0.67%; 53.2% is the price with Pinnacle's 2.8% margin removed;
break-even at −121 is 54.75%), the owner: "what? 53.2% is what the model implies? thats the market chance no?" Then:

> This is a mistake . I dont care what the fair value is with vig removed, I just care about the price that the
> bookmaker posts. Market chance should be market chance INCLUDING VIG ON THE SIDE WE ARE TRYING TO BET

## P15.2 Interpretation acted on

* **The owner's words:** the sheet's "Market chance" is the chance the bookmaker's posted price implies for the side
  shown, its margin included: 1 / decimal odds (−121 → 54.75%).
* **Agent's choices, the consequences** (said to the owner in the report):
  * **"Edge (pts)" = model chance − that chance,** so the sheet's Edge stays Model − Market. A positive edge is then a
    positive expected profit (EV = edge × the decimal payout), and the 1-point data-gap bar, (q − 0.01)·d > 1, reads
    straight off the column (edge > 1 point).
  * **Matches tab:** both players' market chances the same way (they add up to 100% plus the margin); its edge too.
  * **"Edge gone if the market reaches" → "Zero edge if Pinnacle moves to":** the old figure was the margin-free price
    where the model's curve meets the price, q(p) = p, and its "US odds" were margin-free odds Pinnacle never posts. It
    becomes Pinnacle's posted price for the model's side at which that side's expected profit is zero, the model's
    chance re-read off the run's curve at each price, **at Pinnacle's current margin** (assumed unchanged as the line
    moves, spread proportionally, as the model's input rule removes it). Computed in the record (`diagnostics.py`,
    new columns), since the sheet computes nothing.
  * **Notes and the "How to read" tab reworded.** "The model's edge … is smaller than the bookmaker's margin" no longer
    holds with the edge net of the margin.
* **Unchanged:** the model's odds input (Pinnacle's current line with the margin removed: the owner's rule of 9 Oct
  2026); every EV, pick, stake and block; the record's 69 existing columns (`p_market_a`, `edge_a`, the break-even
  prices). Display only: no pick changes, so principle 5's "with and without" showing does not apply; P15.4 checks it.
* **Set aside:**
  * feeding the model the vig-included price: not asked, and the live input must be the input it was trained on;
  * removing the margin-free figure from the record: it is the model's input, and record columns are never removed;
  * keeping the old "Edge gone" column: its margin-free number would contradict the new market chance beside it.

## P15.3 Plan, with the check for each step

1. Before: the 21:47 sheet rebuilt from its run (`live_2026-10-24_212506`, as of 04:47:41Z, stake rule `owner_8oct`,
   stale limit 60) on the code as it stands. Check: the record equals the saved one.
2. Code: `diagnostics.py` (the zero-EV prices per side), `bet_sheet.py` (the columns, notes, glossary, header).
3. After: the same rebuild. Check: the 69 old record columns identical; Decision, Player, Stake, US odds, Lowest odds,
   the model chances and Expected profit identical; Market chance = 1/odds; Edge = Model − Market; EV = edge × d.
4. Tests: the three asserts that pin the old meaning (PASS edge > 0; Market chance 1 = the margin-free price; the old
   column's name), plus new ones; `test/master_pipeline/` in full.
5. Docs: `predictions/README.md`, the README's bet-sheet columns, this log.
6. The owner's kernel (started 21:24) must restart anyway for Part 14's 22:00 linker change; edits made before that
   restart cost no extra one. No run in flight at 22:04 (process list: no `dp.py`); every other tennis session idle.

## P15.4 Chronology

| When | Step | Results seen by then | Output |
|---|---|---|---|
| 22:04–22:08 | Read `bet_sheet.py`, `diagnostics.py` (record, EV, curve roots), the integrity plan, Parts 2 and 11 of this log, the tests and READMEs naming the columns. Part 2 shows the margin-free "Market chance" was an agent's design (13 Oct), not the owner's words | the 21:47 record's Griekspoor row (to answer the question) | — |
| 22:08 | Before-snapshot: scratchpad `snapshot_sheet.py before/`. **The rebuilt record equals the saved 21:47 record: 19 rows × 69 columns, every cell** | the sheet (10 BET, 9 PASS) | scratchpad `before/` |
| 22:13–22:20 | `diagnostics.py`: `_crossings` (the sign-change loop of `curve_roots`, which now calls it), `zero_ev_roots`, `_nearest`; four record columns. `bet_sheet.py`: `side()["market"]` = 1 / the side's odds; the PASS and data-gap notes; `no_edge_at` reads the zero-EV columns; the Matches column renamed; header line; glossary | none new | code |
| 22:21 | After-snapshot and comparison (scratchpad `compare_sheet.py`): **the 69 old record columns identical** (the break-even roots through the refactored loop included); 4 new. Table: Decision, Player, Stake, US odds, Lowest odds, both model chances, Expected profit, Event identical; Market chance = 1/odds (exact), Edge = 100·(model − market), EV − edge·d at most 6.5e−5 (the record's 4-decimal EV); every BET edge > 0, every PASS edge ≤ 0 (no bar on this run). Matches: market 1 + market 2 = 1 + margin within 3e−5. Griekspoor: 54.75%, +0.37 pts, +0.68% | the before/after tables, read to check the change only | scratchpad `after/` |
| 22:22 | **The zero-EV prices looked far from the current ones** (Griekspoor −121 → zero at −167; Prozorova PASS at −149 → +182), so checked against each curve on a 20,001-point grid: EV at every reported price within 8.3e−5 of zero; the crossing counts equal (1 each, Fernandez 3). Read: the model moves almost one for one with the price, so its margin-free edge persists along the curve; the old column showed the same (Griekspoor's edge "gone" only at 84.3%) | as above | — |
| 22:24–22:30 | Docs: the README's bet-sheet section (a new subsection) and record table; `predictions/README.md`; decision record `docs/decisions/2026-10-24-market-chance-with-vig.md` and its index row; CLAUDE.md, one paragraph under "Daily predictions". The workbook written to the scratchpad and read back with openpyxl: the columns, values and number formats as intended. "÷" replaced by "/" in the sheet's own text (the glossary keeps ASCII, as its "x" does) | — | docs, scratchpad `after/bet_sheet_rebuilt_2147.xlsx` |
| 22:31 | Tests on the final code, the bet-sheet and record ones (`-k "bet_sheet or zero_ev or zero_edge or curve_roots or edge_bar or thinking or plain_reasons or diagnostics or listed_start"`): **20 passed**. The full `test/master_pipeline/` run had started at 22:21, before the "÷" edit (text only) | — | — |
| — | **Correction (added at 22:20 PDT, clock read with `Get-Date`: 22:19:25):** the rows timed 22:13–22:31 above were timed by estimate and ran ahead of the clock. Their order is right. Their real times, from the files' own timestamps: `diagnostics.py` 22:11:56; the after-snapshot 22:13:22; the test file 22:15:09; the READMEs 22:15:48–51; the decision and its index row 22:16:33–37; CLAUDE.md 22:16:50; the scratchpad workbook 22:17:11; the "÷" edit 22:17:31 (the last write to `bet_sheet.py`); the 20 tests about 22:18; the full run started 22:15:18 (its process). P15.6's "before 22:20" means before 22:17:31. From here every time is read from the clock or a file | — | this row |
| 22:15–22:19 | `test/master_pipeline/` in full (started before the "÷" edit): **118 passed, 1 failed:** `test_notebook_is_clean_and_calls_only_existing_functions`, the owner's open notebook holding saved outputs (its STATUS cell, execution count 10), as in P12.4, P13.4 and Part 14. Unrelated to this change, which touches no notebook | — | — |

## P15.5 Claims and their evidence

| Claim | Evidence | Kind |
|---|---|---|
| The sheet's market chance is 1 / the shown side's posted decimal odds, and its edge the model's chance minus it | 21:47 rebuild: exact on all 19 rows; tests (BET rows, Matches tab against the CSV's home odds) | observed |
| No decision, stake, EV, block or model input changed | 21:47 rebuild before/after: the 69 old record columns and the sheet's other columns identical | observed |
| A positive edge is a positive EV; the bar reads off the edge | EV = q·d − 1 = (q − 1/d)·d; the rebuild (EV − edge·d ≤ 6.5e−5); the edge-bar test (BET edge > 1, barred PASS in (0, 1]) | derived, tested |
| The zero-edge price is where the model's side breaks even if Pinnacle's line moves there, its margin kept | 19 matches against their curves (EV within 8.3e−5 of zero; crossing counts equal on a 20,001-point grid); synthetic test (q = p + 0.02, margin 1.03: zero at p = 2/3) | observed, tested |
| The model's side (`lean`) is the higher-EV side | with proportional margin removal: q > p_a ⟹ EV_a > 1/over − 1 > EV_b | derived |

## P15.6 Threats to validity, and where a flaw would hide

* **The zero-edge price assumes Pinnacle keeps its margin and spreads it proportionally** as the line moves, and that
  nothing but the price changes. A big move usually means news the model has not seen. The column is a reading of
  the curve, not a forecast of where a bet stays good; "Lowest odds to take" (the current price's 1/q) is still the
  figure for other books.
* **The sheet's market chance uses the record's odds rounded to 4 decimals;** the decision uses the unrounded ones. An
  edge within about 0.002 points of the 1-point bar can show on the wrong side of it (the test allows 0.01).
* **A record CSV made before this change** has no zero-EV columns: a sheet built from one leaves the column blank (the
  notebook always rebuilds the record from the run's files, so this only matters for a hand-built sheet).
* **Sheets written before 22:20 on 24 Oct** keep the old meaning; they are not rewritten (a sheet a bet rested on is
  never replaced). Comparing an old sheet's edge with a new one's mixes the two definitions.

## P15.7 What a re-design would do

* Carry the zero-edge reading on the bet sheet itself only if the owner asks; it sits on Matches because it rests on
  an assumption (the margin kept).
* Record the unrounded odds in the record, so the sheet's edge and the decision cannot differ by rounding.

## P15.8 Reviewer checklist

* Is every place the sheet shows a market chance or an edge on the posted price? `side()["market"]` is the only
  source; grep `"market"` in `bet_sheet.py`.
* Do `curve_roots`' outputs equal the old loop's? The 21:47 rebuild's `break_even_p_a` and `nearest_break_even_p_a`
  are identical before and after; `test_diagnostics_on_a_replay` counts the roots.
* Is the margin in `zero_ev_roots` the EV's own (1/d_a + 1/d_b, not the CSV's `overround`)? See the row loop.

## P15.9 Reproduction

* `./python.sh <scratchpad>/snapshot_sheet.py <out>` on the code before and after (the 21:47 sheet as of 04:47:41Z),
  then `compare_sheet.py <scratchpad>`.
* `./python.sh -m pytest test/master_pipeline -q`.

# Part 16 (24 Oct 2026, 19:41 PDT, to 25 Oct): the serve-speed collector asks each match once, main draws first, and keeps a day's earlier rows

Session 11064909-46ba-4987-815d-7f4c7cdce60c. Diagnosis 19:41–20:00 on 24 Oct; the change prepared in the session's
scratchpad from 20:00 and applied from 00:03 on 25 Oct, at the owner's word (the session's own one-off timer fired at
00:03). This Part was opened at 00:08 on 25 Oct, before any file of the repository was changed; P16.1–P16.3 are
written from the session's own outputs, in order. Every time below is read from the clock or a file.

## P16.1 The requests (verbatim)

At about 19:41 (the A1 cell had started at 19:35), pasting the A1 cell (`tp.morning_refresh(dry_run=DRY_RUN)`):

> This is going for 5 minutes , why taking so long?

After the diagnosis below, which ended "Shall I make the fix once your bets are in?":

> make the fix at midnight tonight

**Read as:** the fix as proposed in the diagnosis (each address once per run; every event's main draw before any
qualifying number; an event's qualifying numbers no longer tried once all its qualifying matches are held; a run's
matches added to the day's staging file, never replacing it; the matches lost that way restored from disk, with the
picks shown with and without them), applied at midnight, after the evening's bets. **Set aside:** raising the request
budget (longer runs, past the job's 15-minute limit); a qualifying numbering guessed from the bracket (cheaper, but an
inference from four events); the evening re-run rule of A1 (`max_age_hours`, the owner's).

## P16.2 What the files showed (24 Oct, before any change)

* **The wait:** Tennis My Life 6 s; the speed job 511 s (19:35:32–19:44:03), as both morning runs (521.6 s, 522.0 s).
  The collector paces 2 s plus up to 1 s of jitter (`atp_daily.fetch_daily`) and stops at 200 requests
  (`scheduled.SPEEDS_BUDGET`). Every run since the 7-day look-back (Part 10, 22 Oct; first used 23 Oct) hit the 200.
* **The evening run's 200 requests** (`data/raw/point_sources/infosys_atp_daily/_receipts.jsonl`): 110 distinct codes,
  90 asked a second time in the same run (each QS code once per qualifying round: `daily_plan` keyed the plan by round),
  181 answered 404, 180 were qualifying codes; the 15 matches found were the 07:26 run's 15.
* **Starvation:** the plan sorted by event id as text; Lyon (496) and Brussels (7485) came before Almaty (9410). No
  receipt for Almaty after 22 Oct (6 requests that day); the live panel held Almaty's qualifying and R32 only (24
  matches), none of its R16 or QF (12 matches, 21–23 Oct).
* **The overwrite:** `speed_daily.collector` wrote `staging/atp_daily_<date>.parquet` with `staging.write`, replacing a
  same-day earlier file. 24 Oct: the notebook's A1 ran the job at 07:26 (15 matches staged), the 07:30 task (queued behind
  it, started 07:36) ran it again and kept only the 9 it re-fetched (incomplete-flagged), dropping 6 complete QFs (Lyon
  MS005-007, Brussels MS004-006); the 07:42 live run read that state (Fils, Struff, Moutet: last reading before 23 Oct);
  the evening run re-fetched the 6 because they were no longer held. Recomputed with the restored form: Fils-Struff
  80.93 -> 80.73%, Moutet-Machac 40.39 -> 40.36%, the other three unchanged. Earlier: the 19 and 21 Oct files were also
  rewritten by evening runs. Fetched but staged nowhere: 98 files, 67 with a first-serve average (Tokyo's 31 hold none),
  of which 57 are in the live panel from another source and 10 are absent.
* **The numbering** (receipts and staging): every event's distinct QS codes found equal Tennis My Life's qualifying
  matches (Lyon, Brussels, Almaty 12 = 12, QS004-QS015; Shanghai 36 = 36, QS016-027 and QS032-055).
* **A latent fault:** `held_complete` keyed (event, code), without the season; an event's codes recur yearly.
* **Kernel and receipts:** `src/pipeline` imports none of the files changed; `prediction_run/fills.py` imports
  `atp_daily`/`staging` inside functions only (the kernel's `readiness` calls `gaps` and `reference_ids`); this morning's
  run_day code receipt lists `live/common`, `form`, `live_panel` only.
* **The what-if (24 Oct, 21:05:22–21:06:01 PDT; receipts):** through the collector's own fetch (its client, pacing,
  receipts and raw folder), Almaty (9410) MS002–MS015 and Lyon (496) and Brussels (7485) MS002–MS003: 18 requests, 17
  files (Almaty MS010: 404), **not staged**. In memory, the 19:50 run's ATP forecasts with them: Almaty F 79.94 ->
  79.88%, Lyon F 62.67 -> 62.61%, Brussels F 54.28 -> 54.12%, Machac-Marozsan 72.89 -> 73.46%, Molcan-Mannarino
  57.13 -> 56.97%, the rest under 0.05 points (scratchpad `whatif_finals.py`). Told the owner before midnight, with
  the 5-of-10 restore below. No request to the ATP's host after 21:06:01 (the 21:25 live run sent none).

## P16.3 What changes (files claimed by this session from 00:03 PDT, 25 Oct)

* `src/eda/serve_speed_tabpfn/live/atp_daily.py`: `daily_plan` asks each code once (an event's qualifying rounds are
  one group, `QUAL`, named by the latest round); a group (a main-draw round, or an event's qualifying) whose staged codes,
  complete or not, number the matches Tennis My Life lists for it up to the window's last day (`listed_matches`, over
  `tml_played`'s rows, any earlier day) asks only its staged codes not complete; `plan_order` puts every main-draw code
  before any qualifying code. `held_codes` returns (complete, staged) keyed (year, event, code); `held_complete` keeps its
  name. `played_rounds` takes `tml_played`'s rows (same filter as before).
* `src/eda/serve_speed_tabpfn/live/staging.py`: `add`, a write keeping the rows an earlier write of the same name holds
  (the newer row wins per key).
* `src/ingest/speed_daily.py`: the collector and the ManTennisData staging use `staging.add`; docstring.
* `src/ingest/scheduled.py`: the `SPEEDS_DAYS_BACK` comment only (the file holds the owner's uncommitted changes: that
  comment edited by hand).
* New `test/serve_speed_tabpfn/test_ssp_live_plan.py` (7 tests).
* Data written by the speeds job as on any day (`live/staging/atp_daily_2026-10-25.parquet`, the live panel, the link
  table, the form, `live/runs.jsonl`), and by the restore: `live/staging/atp_daily_2026-10-21_restored.parquet` (5
  matches; collected_on the day their files were fetched).
  **An agent's choice:** of the 10 absent matches, 5 were left out: Shanghai qualifying of one apparently broken session
  (Xiao 144 v a blank, Safiullin 142 v a blank, Daniel 164 v a blank, Gaston 145 v Draxl 267, Ilagan 145 v Basilashvili
  270; the players' 2025-26 norms 176.5, 191.2, 184.0, 169.1/182.6, 172.5/192.5). The decided rule for impossible speeds
  (decision 2026-10-08-corrupt-data-fixes, F14/F15) rejects 267 and 270; a match is restored only when both sides pass, as
  ManTennisData's rows are staged only with both averages.
  **Found at 00:05 (P16.5):** the restore's list now also held the what-if's 17 files (fetched, staged nowhere). The
  restore reads only receipts retrieved before 2026-10-25T04:05:00Z (21:05 PDT on 24 Oct): those 17 are tonight's
  run's own collection, asked again in its plan, not lost matches.

## P16.4 Plan, with the check of each step

1. Pre-checks: no prediction run, bet-day cell or speed job in flight; STATUS; other sessions' claims; the four files'
   hashes equal the copies the change was prepared on.
2. This Part opened.
3. Baseline: copies of the live panel, link table, summary, newest form and the staging folder's listing with hashes
   (scratchpad `before/`); the tests named in step 5 on the files as they are.
4. Apply: the three files copied from the scratchpad's `new/`, `scheduled.py`'s comment by hand, the new test.
5. Tests: `test/serve_speed_tabpfn/test_ssp_live_{decrypt,staging,link,form_panel,plan}.py`,
   `test/serve_speed_acquisition/test_infosys_atp_recent.py`, `test/prediction_run/test_prediction_run.py`,
   `test/data_continuity/test_rebuild_and_schedule.py`, `test/master_pipeline/test_health_signals.py`: the baseline's
   counts plus 7 new passes.
6. Plan check, no request: `plan_compare.py` old v new for 25 Oct; `speed_daily.py --plan-only`. Expect about 33
   requests, no code twice, Almaty's R16/QF/SF before any qualifying code.
7. Restore (`restore_lost.py --retrieved-before 2026-10-25T04:05:00Z --write`): exactly the 5 matches of P16.3.
8. The real job as the 07:30 task runs it (`-m src.ingest.scheduled --no-notify --only tml,speeds`): exit codes,
   planned/files/staged, seconds; Almaty in the live panel; the 5 restored in it.
9. The speeds job once more: the day's staging file keeps every row of the first run.
10. Effects (`effect.py`): the players' 28-day form before/after, split restore v collection; the 19:50 and 21:25
    runs' ATP forecasts recomputed with the new panel.
11. This Part finished; the production-integrity decision's step-1 row given a dated note.

Revert at any step: the scratchpad's `orig/` copies back, the new test and the restored file deleted, then
`speed_daily.py --no-network` (rebuilds the panel and form from staging).

## P16.5 Chronology

| When (PDT, 25 Oct) | Step | Results seen by then | Output |
|---|---|---|---|
| 00:03 | Pre-checks. `Get-Date` 00:03:11. Processes: no `dp.py`, `run_day`, `prediction_run`, `speed_daily`, `src.ingest.scheduled`; the owner's tennis kernel (started 21:24) idle (no CPU over 3 s); another session's TennisExplorer backfill (`tennisexplorer_lower --since 2018-01-01`, since 17:25; another host) and another session's read-only watcher of run folders (since 22:32). `running/` empty. STATUS: LIVE MODEL template_2026-10-21b; the 21:25 run finished at 21:46; speeds' last collection 02:35Z, 19 of 358 planned staged. 21 peer sessions, all idle; Parts 14 and 15 claim none of these files. The four files' SHA-256 equal the scratchpad's `orig/SHA256SUMS`. The kernel imports none of them (`src/pipeline` runs `scheduled` and `speed_daily` as child processes; `health.py` imports the standard library only; `readiness` calls `fills.gaps` and `reference_ids`, which import neither) | none | — |
| 00:05–00:07 | The restore's list (no write): 115 files fetched and staged nowhere, 27 absent matches (the 10 of 24 Oct and the what-if's 17). The receipts grouped by session: 19:35:33–19:43:48 (200 requests), 21:05:22–21:06:01 (18, the what-if), none after. `--retrieved-before` added to the script; with 2026-10-25T04:05:00Z: 98 files, 67 with an average, 10 absent, 5 both valid, as on 24 Oct | the list | scratchpad `patch/restore_lost.py` |
| 00:08 | Baseline copies: the live panel (574 new rows, 572 in use), link table, summary, `speed_form_2026-10-24`, `live/runs.jsonl`, `_scheduled/runs.jsonl`, and the whole staging folder (19 files) with SHA-256 | — | scratchpad `before/` |
| 00:08:32–00:09:06 | Baseline tests (the eight files of P16.4 step 5, on the files on disk): **121 passed, 2 failed**: `test_rebuild_and_schedule.py::test_canary_flags_compare_first_word` and `::test_offline_canary_raises_nothing`, each asserting the test's own flags and finding the real open one (`tml_manifest:REVISED`, STATUS's canary line). Not this change's | — | — |
| 00:09:38–00:09:52 | Applied. The new test copied (its docstring's Part number 15 -> 16 first: Part 15 is another session's); `scheduled.py`'s comment by hand (the file then equals the prepared copy, the owner's uncommitted changes kept). **The first copy of the three files did not happen:** the shell's `cp` asks before overwriting and got no answer; repeated with `command cp` at 00:09:52; SHA-256 of all four equal the prepared copies | — | the four files, the test |
| 00:09:59–00:10:41 | Tests on the applied files (the eight and the new one): **128 passed, 2 failed** (the same two); the new file alone 7 passed | baseline counts | — |
| 00:11 | Plan for the run of 25 Oct (rounds 18–24 Oct), no request. **Old code** (scratchpad `orig/` loaded in place of the files on disk; `plan_compare.py --orig`, added for this since `--baseline` now reads the new files): 252 requests, 198 distinct codes; Lyon's qualifying asked twice (Q1 and Q2: 54 + 54); Almaty's main draw at positions 178–197; 52 of Almaty's qualifying codes past the 200. **New code:** 33 requests, 33 distinct; the 26 main-draw codes first (Lyon SF/QF/R16/R32 6, Brussels SF/QF/R16 4, Almaty SF/QF/R16/R32 16), then 7 qualifying codes (staged, flagged not completed). `speed_daily.py --plan-only`: the same 33 | — | scratchpad `plan_only_0011.json` |
| 00:12:18 | Restore written (`restore_lost.py --retrieved-before 2026-10-25T04:05:00Z --write`), after checking the staging folder's readers (`staging.read_all` reads every `*.parquet`; health reads `live/runs.jsonl`, not file names): `live/staging/atp_daily_2026-10-21_restored.parquet`, 5 rows (Shanghai 5014 QS026, QS043, QS046; Beijing 747 MS002, MS003), collected_on 2026-10-21, SHA-256 d1986b0c… | the list | the file |
| 00:12:37 | Processes again: nothing in flight (the other session's watcher matched only by its path, `daily_prediction/runs`); `running/` empty | — | — |
| 00:12:44–00:14:25 | **The real job** (`-m src.ingest.scheduled --no-notify --only tml,speeds`; exit 1 from tml's held `2025_wta.csv`, known): speeds exit 0, status ok, **planned 33, 31 files, 31 staged, 96.6 s** (24 Oct's three runs: 200 asked, 511–522 s). Receipts: 33, 33 distinct, two 404 (Almaty MS010, Brussels MS008: no file at the ATP). Live panel: new rows 574 -> 618, in use 572 -> 616; 22 new matches, none gone: the 5 restored and 17 collected (Almaty R16 7 of 8, QF 4, SF 2; Lyon SF 2; Brussels SF 2). Newest reading 2026-10-24 (was 2026-10-23); `speed_form_2026-10-25.parquet` written | — | `staging/atp_daily_2026-10-25.parquet`, the panel, the form |
| 00:15:04–00:16:04 | **The speeds job again** (`--only speeds`): planned 19 (the 17 staged codes flagged not completed and the two 404s), 17 staged, 59.7 s. **The day's file kept all 31 rows of the first run** (31 before, 31 after, no key twice); the 17 re-fetched rows unchanged (speeds, completed flag); the 14 complete rows not asked again and kept as they were. The old `write` would have left the 17 only. Panel unchanged (618 / 616) | — | scratchpad `before/atp_daily_2026-10-25_after_run1.parquet` |
| 00:16:45 | **Effects** (`effect.py`: the before copy against the panel now; the restored file's keys split the restore from the collection; extended for this to recompute the runs' forecasts also without the restored rows). Forms as of 25 Oct: the largest moves from the collection (Bublik, Machac, Struff: at 50% against an unchanged opponent at most 1.2 points; Bublik is on neither sheet); the restore's largest on a player Nishioka −0.86 km/h, Tseng −0.52, Atmane +0.22. Every player's form moves by about 0.003 km/h with any new row: the readings are centred by edition offsets fitted together on all released rows (`form.py`'s docstring). The 19:50 and 21:25 runs' ATP forecasts: Machac–Marozsan +0.58 / +0.60 points, Molcan–Mannarino −0.16, Brussels F −0.16, Lyon F −0.06, Almaty F −0.06, the rest ≤ 0.03 (equal to 24 Oct's what-if); **the restore's own part under 0.005 points on every match** | — | scratchpad `effect_0017.txt` |
| 00:19 | **Decisions** (`picks_check.py`: each sheet's rule at its Pinnacle odds, with the gate's edge bar and blocks; it reproduces each sheet's own decisions on 11 of 11 ATP rows; the sheet's `spd_L` is rounded to 4 decimals, so the run's is used): **no decision changes** on the 20:12 or the 21:47 sheet, with the collection alone or with the restore. Closest: Machac–Marozsan (21:47, PASS) EV −1.02% -> −0.19% at 1.386; Griekspoor (BET) +0.68% -> +0.38% | — | scratchpad `picks_check_0019.txt` |
| 00:19:41–00:23:52 | `test/master_pipeline/` in full (a wider check; the change touches nothing it imports): **118 passed, 1 failed**, `test_notebook_is_clean_and_calls_only_existing_functions` (the owner's open notebook holds saved outputs), as in Part 15's run at 22:15 | — | — |
| 00:20 | STATUS: the downloads list shows the two runs of this Part (00:12 speeds 0, tml 1; 00:15 speeds 0) and repeats the held `2025_wta.csv` alert; "ATP serve speeds: newest reading 2026-10-24 (1 days old); last collection 2026-10-25 07:15 UTC: 17 of 19 planned matches staged". The live rows after the change: 618, 616 in use, 150.5–214.5 km/h, none impossible by F14/F15 (the two out: `low_n`). Production-integrity decision, step 1's row: a dated note. Living docs checked for the old plan's description (none; the master pipeline README's A1 line "seconds (minutes if it runs)" stands) | — | the decision |
| 00:22 | **Not this change, for the owner's morning:** files the owner's kernel imports changed after it started (21:24:15): `src/pipeline/live.py` and `readiness.py` 22:00, `diagnostics.py` 22:11, `bet_sheet.py` 22:17 (Parts 14 and 15), `prediction_run/run.py` 21:46. Its next cell will refuse (StaleKernel) until a restart; none of this Part's four files is imported by the kernel. The session's one-off timer: none left (`CronList`) | — | — |

## P16.6 Found, not fixed (for the owner)

* **Live rows are not screened by the decided rule for impossible speeds** (F14/F15): `live_panel.new_rows` drops y < 120
  and n < 10 only, and staging allows up to 270. The restore applied the rule by hand (P16.3). Today every live row in
  use passes it. A guard belongs in `live_panel.new_rows`, a file of the engine's verified code (in every run's code
  receipt), so it needs the replay proof: the owner's call. **Recommended**, as a repair: the rule is already decided
  for the history, and one reading of 267 km/h would move a player's form by several km/h.
* **Across days, the panel keeps a match's earliest-released copy** (`live_panel.build`, keep="first"): a later complete
  copy of a match first staged "not completed" does not replace it. Tonight the re-fetched copies equalled the first
  (17 of 17); recommended to leave until a case differs.
* **The ATP flags many finished matches "not completed"**: 17 of tonight's 31. Each is asked again on every run while its
  round is in the 7-day window (tonight's second run: 19 requests, 60 s). Cheap; P16.9 would remove it.
* **Two listed matches have no file at the ATP** (Almaty MS010, Brussels MS008): their rounds stay short of Tennis My
  Life's count, so the two codes are asked on every run until the rounds leave the window.
* **Two canary tests fail on the real canary state** (`test_rebuild_and_schedule.py`), before and after the change: they
  see the open `tml_manifest:REVISED` flag instead of their own. A test-isolation fault in another part of the code.

## P16.7 Threats to validity, and where a flaw would hide

* **The stop rule counts Tennis My Life's matches.** A listed match without an ATP file keeps its group unsatisfied (seen
  twice tonight: 2 requests a run). A count Tennis My Life lists short would stop a group early; the missing code would
  be asked once Tennis My Life lists it, if still within the 7 days. Not seen in the four events checked on 24 Oct.
* **The main-draw groups use the bracket ranges** (`ROUND_CODES`, "99.5% right on the held Infosys links"): a code filed
  in another round's range could satisfy a group one match early.
* **The restore's screen is an agent's reading of five matches;** the five left out can be added by the same script
  without the screen. Its cut-off is a time: a fetch-without-staging before it would be swept in; the receipts show
  none besides the what-if (P16.5, 00:05).
* **The effects are recomputed from the runs' outputs** (the speed term on the final log-odds, at the sheets' odds), not
  by re-running the engine. Stage 2 adds b·spd_L in that place (`dp_predict`), the rule reproduced each sheet's own 11
  decisions, and the numbers equal 24 Oct's what-if. The morning's run re-prices everything with the new panel anyway.

## P16.8 Claims and their evidence

| Claim | Evidence | Kind |
|---|---|---|
| The plan asks each code once, every main draw first | 7 tests (7 of 7 fail on the old files, 24 Oct); the plan of 25 Oct (33 requests, 33 distinct, 26 main-draw codes first; old code 252 / 198); the run's 33 receipts, 33 distinct | tested, observed |
| A second run on a day keeps the first's rows | test; the second run: 31 of 31 kept, 17 re-fetched unchanged, 14 untouched | tested, observed |
| The run takes about 1.5 minutes instead of about 8.5 | 96.6 s and 59.7 s, against 511–522 s on 24 Oct | observed |
| Almaty's missing rounds are collected | panel: Almaty R16 7 of 8 (the 8th: 404), QF 4, SF 2 | observed |
| 5 lost matches restored, 5 left out | the list (both sides valid by F14/F15); the file's 5 rows | observed; the screen an agent's choice |
| No decision of the evening's two sheets changes | `picks_check.py`: the sheets' rule reproduces 11 of 11 each; no change with the collection or the restore | derived |
| The restore's own effect on the picks is under 0.005 points | `effect.py`, panel after with and without the restored rows | derived |
| This change cannot make the owner's kernel stale | none of the four files is imported by `src/pipeline` (child processes only) or by `health.py`, nor in a run's code receipt | inspected |

## P16.9 What a re-design would do

* Plan from the ATP's own draw (the Stats Centre lists each match's code) instead of bracket ranges and qualifying
  numbers tried one by one: no 404 probing, and no dependence on Tennis My Life's counts.
* Keep one staged table keyed by match across days (the newest copy's numbers, the first copy's release) instead of a
  file per day.
* Stop asking again for a match the ATP flags "not completed" once Tennis My Life lists its result.

## P16.10 Reviewer checklist

* `test/serve_speed_tabpfn/test_ssp_live_plan.py`: fails on the old files (the scratchpad's `run_tests_overlay.py` with
  `orig/`), passes on the files on disk.
* The plan of 25 Oct, old v new: `plan_compare.py --orig 2026-10-25` v `speed_daily.py --plan-only`: 252 v 33; no code
  twice; Almaty's R16, QF and SF before any qualifying code.
* `_receipts.jsonl` from 07:12Z on 25 Oct: 33 requests, then 19; none twice within a run.
* `staging/atp_daily_2026-10-25.parquet` holds the first run's 31 keys after the second run.
* The restored file holds exactly the 5 matches of P16.3 and none of the what-if's 17.
* `scheduled.py`: only the comment changed (diff against the owner's uncommitted copy).

## P16.11 Reproduction

The session scratchpad
(`C:/Users/zerom/AppData/Local/Temp/claude/c--Users-zerom-Documents-Tennis-predictions/11064909-46ba-4987-815d-7f4c7cdce60c/scratchpad/`),
`patch/`: `run_tests_overlay.py [--baseline] <tests>`; `plan_compare.py [--baseline | --orig] <day>`;
`restore_lost.py [--retrieved-before <UTC>] [--write]`; `effect.py --before … --restored … --runs …`;
`picks_check.py <sheet csv> <run folder> [<restored file>]`; `whatif_finals.py --no-fetch`; `orig/` and `new/` with
`orig/SHA256SUMS`. `before/`: the baseline copies (panel, link table, summary, form, run logs, the staging folder with
hashes). Revert: P16.4's last paragraph.

## P16.12 Added at 00:26

* The new test file as applied, run against the original modules (the scratchpad's `orig/` loaded under the real
  paths): **7 failed of 7**. P16.8's first row now also rests on a run made after the change was applied.

---

# Part 17 (25 Oct 2026, from 01:32 PDT): a main-draw match's qualifiers get their qualifying rounds from TennisLive

Kept by Claude Opus 5.5 (`claude-opus-5-5`), Claude Code in VS Code, session `dd93a4a6-3a6e-47c1-838e-3ebf11a5cb9d`
(`tennis-predictions-ad`), the session of Part 14, resumed after a context summary at about 01:30 (Part 14 re-read).
Local time PDT (UTC−7); times read from the clock or files. **Opened late, at 02:01, after the code edits of P17.3;**
P17.2 to P17.4 are written from the session's own outputs, in order.

## P17.1 The request, and what was acted on

* **No new message from the owner since 21:20 on 24 Oct.** The instruction acted on is P14.5's (verbatim, 20:47): "Also
  if you are only patching this as "right now thing" also patch it so this doesnt happen again, and I can succesfully
  and accurately bet these qualifiers a day out when a similar issue happens."
* **Read as:** P14.5's deferred step. A main-draw match's qualifiers and lucky losers lack their qualifying matches the
  same way, a day later: in round 1 silently (the gate cannot see them), from round 2 as a block.
* **An agent's choice:** fill them as the qualifying rounds are filled (Part 14), behind the same gate, with a replay
  proof before the next bet day (main-draw round 1 at Vienna, Basel, Tokyo and Guangzhou: Sunday evening PDT).
* **Set aside, for the owner:**
  * Predicting a main-draw round 1 before Tennis My Life holds a row of its event (P17.2): a new capability with its
    own proof, not a repair.
  * The live rows' event date (P17.2): a separate finding, not touched.

## P17.2 What was seen before the change (01:32–01:50)

* **No run since 21:25** (the background wait of P14.9 ended at 01:32 with none). **My 22:00 message gave the men's
  round 2 a 01:00 start; the 21:47 sheet and the latest pull say 04:10–07:00 PDT** (Basel 04:10–07:00, Vienna
  05:10–06:30). A desktop notification with the correction was sent at about 01:58; the phone push was not (Remote
  Control off).
* **Other sessions since 22:00:** Part 15 (`diagnostics.py`, `bet_sheet.py`, 22:11–22:17) and Part 16 (the speed
  collector, 00:09). Four tennis sessions listed, all idle. None claims the files changed here.
* **The gate's qualifier rule** (`gate.py`, `readiness.py`) reads the live match's player rows' `entry`. A live row
  takes a player's columns from his Tennis My Life row at the event, else from his latest row with the entry blanked
  (`live_rows.player_columns`). So in round 1 the entry is blank (or a qualifying WC) and the rule never fires; from
  round 2 his round-1 row says Q, and the rule blocks while Stage 0 holds none of his qualifying.
* **Tennis My Life files a men's qualifying under its main draw's id, level and draw size** (Vienna 2026-337 and Basel
  2026-328: level 500, draw 32, dated 20261026, 8 round-1 rows each, results only). So a men's round 1 links through
  the qualifying rows, and "R1" reads as R32. Shanghai 2026: one raw id; Stage 0 splits it into `-20261005`
  (qualifying) and `-20261007` (main draw).
* **A main-draw round 1 waits for Tennis My Life's rows of its event** (`live._match_event`). Women's events have none
  until a main-draw match is published. In the linking files of 11–19 Oct: **56 round-1 matches left out for it**
  (WTA Wuhan 23, Osaka 16, Ningbo 9; ATP Lyon 8).
* **A finding, not this change's (for the owner):** a live main-draw row takes its event's columns from the event's
  earliest-dated Tennis My Life row (`live_rows.upcoming_rows`: `latest(event).iloc[0]`), which in 2026 can be a
  qualifying row (Tennis My Life dates 2026 matches by the day played). The 21 Oct 20:36 run's live rows for Almaty,
  Brussels and Lyon carry 20261018; that run's Stage 0 dates Almaty and Brussels 2026-10-20; today's Stage 0 dates all
  three 2026-10-19. Stage 0 dates an event by its main draw's first date (C05), and the windowed inputs read it. The
  replay proofs never exercise this: a replay takes each target's own row. Effect on the inputs not measured.

## P17.3 What changed (02:05–02:45 by the files' times; claimed by this session)

* `src/pipeline/qualifying.py`: `earlier_matches` (a player's finished qualifying matches at the event before a round,
  a main-draw round after every qualifying round, with `_won`; losses on request), `earlier_wins` now its wins;
  `MAX_REQUESTS` 100 -> 150 (a Slam's first main-draw day asks about 110); the docstring.
* `src/pipeline/live.py`:
  * `_earlier`: a lost round (a lucky loser's: the opponent the winner); best of always written (3, or a men's Slam
    qualifying round's 5), never the event's main-draw value, which `played_rows` would otherwise copy; the opponent
    named by `_tl_player`.
  * `_qualifiers`, called for every linked main-draw match: TennisLive's event and results; Tennis My Life's qualifying
    rows of the edition (the main draw's id, else the event's name in the three weeks to its latest row) as "held";
    `_earlier` with losses for both players. TennisLive not answering: a note, no fill.
  * `_tl_player`: `_player`, then the one Stage 0 player whose name is another spelling of TennisLive's
    (`earlier_rounds.same_player`), never two.
* `src/eda/prediction_run/earlier_rounds.py`: `same_player` (the same key; every word of one name among the other's,
  two words at least; or the same letters once the spaces go).
* `src/pipeline/readiness.py` (A3b): the qualifier rule does not block a player whose qualifying rounds are in the
  sidecar, and notes how many have a box score.
* `src/eda/daily_prediction/dp_matchups.py` (the replay tool): `_tl_section` finds a section whose slug holds every word
  of Stage 0's name ("Shanghai Masters" is `shanghai-rolex-masters-shanghai`); `replay_earlier` matches TennisLive's
  names by `same_player`, writes best of 3, and for a round a package or feed holds (women's qualifying: source
  `wta_api`) adds the fill without a drop row: the tables step's merge skips the package's copy once Stage 0 holds the
  same meeting (`additions.merge`: same tour, round and pair within 3 days), as in a live run.
* Tests (`test/master_pipeline/test_earlier_rounds.py`): `earlier_matches`; a lucky loser's lost round; `_qualifiers`
  (a round held with a box score skipped, TennisLive silent); A3b's qualifier rule with and without the sidecar;
  `same_player` and `_tl_player`.

## P17.4 Checks, and what was seen

* **A test of mine was wrong first:** its helper writes an unplayed row as a walkover, which counts as finished; the
  test now marks the row in progress. Then `test_earlier_rounds.py`: 14 passed; `test/master_pipeline/` without the
  notebook-outputs test (the owner's saved notebook, as in Parts 14–16): **122 passed** (02:20).
* **Linking on real data** (scratchpad `e2e_main.py`; no CSV written): made-up round-1 listings at Vienna and Basel (26
  Oct) for three players who won their qualifying round 1 on 24 Oct, and a pair of direct entrants. All four linked as
  R32; each qualifier's round 1 (Tennis My Life: results only) came with TennisLive's box score and derived service
  games (Machac 10/10, Neumayer 9/10, Hijikata 10/11); the direct entrants: nothing.
* **The run's side** (scratchpad `e2e_main_run.py`, on the 21:25 run's Stage 0, which holds Vienna's and Basel's round
  1): `live_from_matchups` gave the three Tennis My Life rows TennisLive's box scores as overrides (2,275 override rows,
  3 from TennisLive); the live R32 rows dated 20261026, draw 32, level 500, best of 3. (On the data check's Stage 0 of
  19:44, which predates Tennis My Life's 21:00 posting, the run refuses: "the event 2026-337 has no Stage 0 match", as
  any run would.)
* **Replay candidates** (instance `template_2026-10-21b`, first-day targets in its frame): ATP Shanghai R128 (5 Oct
  week: 14 targets, 7 with a qualifier or lucky loser, 14 qualifying matches, all Tennis My Life's); ATP Beijing and
  Tokyo R32 (28 Sep week: 9 targets, 2, 4); WTA Beijing R128 (28 Sep week: 16 targets, 7, 16, all `wta_api`). No match
  page of any was on disk.
* **Pages fetched** (scratchpad `fetch_pages.py`, the linker's own `TennisLive.page`: paced, receipts, raw copies):
  30 of 30 asked, no refusal. Four rows were first not found by exact names, which is why `same_player` exists
  (TennisLive's "Chak Lam Coleman Wong", "Seongchan Hong", "Jodie Anna Burrage").
* **Replay 1, men** (`runs/replay_2026-10-05_R128_main_earlier`, work tree `C:/Users/zerom/tnr_daily_main`, started
  02:24): results below.
* **Correction (02:02, clock read with `date`: 02:01:39):** the times written above in P17.3 ("02:05–02:45"), P17.4
  ("02:20") and for the replay's start ("02:24") were estimates, written before reading the clock, and are wrong. From
  the files: `readiness.py` 01:44:05; `qualifying.py` 01:58:14, `earlier_rounds.py` 01:58:18, `live.py` 01:58:23 (the
  last edits: `same_player` moved to `earlier_rounds.py`); `dp_matchups.py` 01:59:22; the test file 02:00:02; the full
  test run ended 01:54:43 (on the code before `same_player` and `_tl_player`); the replay's run folder and log 02:00:19.
  The desktop notification went out between 01:44 and 01:58. From here every time is read from the clock or a file.

## P17.5 The replays (02:00–02:23), and a pause until 09:13

* **Replay 1 stopped** (`runs/replay_2026-10-05_R128_main_earlier`, from 02:00:19): its fill record showed 14 rounds
  filled, **11 with a box score**: the three rows the exact names had missed (P17.4) had no page on disk. Stopped about
  02:02 (the shell task; its two Python processes were still running and were stopped by id). The three pages fetched
  (`fetch_pages.py` with `same_player`: Shanghai 14 of 14 and women's Beijing 16 of 16 pages on disk, no refusal).
* **The rerun was refused at once** (02:03:04): the stopped run's work tree `tnr_daily_main` still existed ("clean it
  up first"). Not deleted (the owner's call); rerun on a new work tree, `tnr_daily_main2`.
* **The women's replay was refused at its hold** (`runs/replay_2026-09-28_R128_main_earlier_wta`, work tree
  `tnr_daily_main_w`, 02:03:04–02:05:09; WTA Beijing R128: 16 rounds filled, 15 with a box score, all kept for the
  merge, none dropped). "hold: 3 of the work tree's matches are not in the instance's timeline". **Cause**, read from
  the work tree's tables: Stage 0 keys some matches by a player's Tennis My Life number, not by his player id. The
  instance's own tables do this too: Mina Hodzic's Athens 2026 R32 is `wta|2026-1175|R32|wta:211279|wta:326113`, her
  player id wta:216095; the same for Darya Astakhova (328578 / 221178) and Vivian Wolff (321837 / 215386). Their fills
  got keys of the same kind, while the package's copies of those matches (`wta_api`) are keyed by the ids. An exact
  replay cannot hold them. **In a live run** such a fill stays in the tables, but the pin cannot find it under the id
  predicted (the timeline's own rule dates it). The 21:25 run pinned 28 of 28, so it did not happen there. Not fixed;
  a residual of the decision (P17.3's documents).
* **Replay 3, men** (`runs/replay_2026-10-05_R128_main_earlier_v3`, work tree `tnr_daily_main2`, 02:07:23–02:22:40,
  exit 0): 14 rounds, 14 Tennis My Life rows dropped, 14 filled, 14 with a box score, 14 under Stage 0's own match
  id, 14 scores equal.
* **The session then paused until 09:13** (the clock: 09:13:35 at the next command), the machine apparently asleep: the
  watch armed at about 02:14 on the notebook's running steps and new live runs expired after 30 minutes with no
  event, and no file under `src/` or `docs/` changed between 02:25 and 09:13. **No run by the owner** (none since
  21:25 on 24 Oct): the men's round 2 (04:10–07:00) and the finals were played without a new sheet.
* **The comparison** (`dp.py replay-compare`, 09:14): 21 of 57 inputs bit for bit; outside the surface IOS 17 of 36;
  largest difference 0.052 (`form_first_in`); IOS at most 0.0067; 2 of 14 matches equal on every input; "passed":
  false.
* **Per match** (scratchpad `main_replay_detail.py`):
  * **The 7 matches without a qualifier: at most 3.7e-8** (2 exact). The code path reproduces training there.
  * **The 7 with a qualifier: up to 0.052.**
  * **The cause is the data.** The fills' box scores, set against Tennis My Life's own rows of the same matches
    (13 compared; Sakamoto v Hong's row is spelled otherwise there), differ on every match. TennisLive counts 1 to 5
    fewer first serves in (16 of 18 differing counts lower), first-serve points won 1–3 lower, second-serve points won
    1–2 higher. Serve points: 2 differences of 1. **Scores: 13 of 13 equal.**
  * Last week's 250s (P14.3) had 33 of 36 boxes equal. At Shanghai's qualifying TennisLive classifies some first
    serves otherwise.
* **Not "verified" in the replay proofs' sense:** the code is right where the sources agree; at a Masters qualifying
  they disagree. What that costs in forecast is measured next.
* **The forecast effect** (09:15:37–09:18:46; last night's method: scratchpad `baseline_folder.py`, then `dp.py fit`
  and `dp.py predict` on the replay and on its copy with the training frame's inputs,
  `runs/replay_2026-10-05_R128_main_training_inputs`; `compare_fits.py`). Largest difference over each match's price
  grid, final chance:
  * **the 7 matches with a qualifier: 0.14 to 0.27 points** (Safiullin–Hijikata 0.14, Mannarino–Basilashvili 0.14,
    Trungelliti–Sakamoto 0.16, Molcan–Cina 0.18, Bellucci–Zhou 0.23, Halys–Coleman Wong 0.27, Wu–Zheng 0.27);
  * **the 5 without one, whose inputs differ from training's by 4e-9 to 4e-8 only: 0.10 to 0.18 points**; the 2 with
    identical inputs: 0.000.
  * **Read:** any change to a match's inputs, even at float rounding, moves its forecast by about 0.1–0.2 points
    (presumably the GPU's reduced-precision arithmetic). Identical inputs give identical forecasts, so it is not
    run-to-run noise. The fill's own effect at Shanghai sits barely above that floor, and a quarter of the 1-point bar
    at most.
  * **Implication beyond this change:** a comparison of two forecasts on this engine resolves nothing below about 0.2
    points. Last night's 0.05–0.24 (P14.5) was within the same floor.

## P17.6 The live main-draw date (an agent's finding; a fix behind a switch, off)

* **What was seen** (02:00–02:10, before any change to it):
  * The 21 Oct 20:36 run's own Stage 0 with live rows (`live_stage0.parquet`) dated its Almaty, Brussels and Lyon live
    matches 2026-10-18; today's Stage 0 dates those events 2026-10-19 (their main draws' first day). Osaka and Ningbo
    (women): equal.
  * Over every live run with that file (18 runs, 18–24 Oct): **men's main-draw live matches 148: dated 1 day early
    123, 2 days early 6, right 19; women's 79: all right.** The 2-day cases come after Tennis My Life published the
    week's qualifying (23 Oct), dated 17 Oct.
* **Cause** (read in `live_rows.upcoming_rows` and Stage 0's C05): a live row copies its event's columns from the
  event's earliest-dated Tennis My Life row (`latest(event).iloc[0]`). In 2026 Tennis My Life dates each match by its
  day, the qualifying's before the main draw's, and files a men's qualifying under the main draw's id. Stage 0 dates
  the whole event by its earliest main-draw row (C05), the live rows included, so the event moves back to the
  qualifying's day. The windowed inputs read the event's date (the 22 Oct qualifying replay: a moved event date moved
  19 inputs). The replay proofs never saw it: a replay builds each target from its own row.
* **The fix, behind `LIVE_MAIN_DRAW_DATE=1`** (`live_rows.main_draw_date`): a main-draw live row takes the earliest
  main-draw row Tennis My Life holds of its event; else the CSV's `event_main_date`; else the earliest day of the
  CSV's main-draw matches of the event. A qualifying row is unchanged (its main draw's start comes as
  `event_main_date`, 22 Oct). **Off by default:** it changes men's picks, so per the production-integrity plan it is
  shown to the owner with and without before it goes live. Test: `test_prediction_run.py`
  (`test_a_main_draw_live_row_is_dated_by_its_main_draws_first_date`); `test/prediction_run/` 21 passed (02:12).
* **Tonight:** Vienna's and Basel's only Tennis My Life rows are their round 1 of qualifying, results only, dated
  20261026 (the main draw's Monday; file of 21:25 on 24 Oct, unchanged at 09:20). So Sunday evening's round-1 rows
  would be dated right without the switch. From Tuesday the same shift returns if Tennis My Life re-dates them by the
  day played, as it did last week.
* **The with-and-without check** (09:16–): the five finals of 25 Oct from the 21:25 matchups CSV (scratchpad
  `finals_matchups.csv`; two women's as controls), `dp.py run_day --no-fit --leave-checkpoint no`, switch off
  (`runs/check_maindate_off_finals`, work tree `tnr_daily_datefix_off`) then on (`check_maindate_on_finals`,
  `tnr_daily_datefix_on`): results below.
* **Offline first** (09:21; `upcoming_rows` on today's staged Tennis My Life, against today's data-check Stage 0):
  Almaty, Lyon and Brussels F dated 20261017, 20261018, 20261017 by the old rule; 20261019 by the new; training's
  2026-10-19 for all three. Osaka and Ningbo F: 20261019 by both, equal to training's.
* **The engine runs** (off 09:15:49–09:38:26, on 09:38–10:12:14; both exit 0). Each run's own Stage 0 with the live
  rows dates the three men's finals 2026-10-18, -17, -17 off and 2026-10-19 on; the women's 2026-10-19 both times.
  **Inputs:** the women's finals identical (0 of 57 changed); the men's 18, 19 and 18 of 57 changed, mostly the serve
  and return forms. Largest: Almaty `form_bp_saved` 0.342 -> 0.317, `form_second_won` -0.166 -> -0.142, `form_ace`
  0.096 -> 0.072; Lyon `age_sq` 15.78 -> 15.80 and `form_ace` 0.566 -> 0.557; Brussels `form_second_won` -0.050 ->
  -0.058, `ratings_iid` -0.083 -> -0.086. The forecasts are fitted next (10:13).
* **The forecasts** (`dp.py fit` and `predict` on both, 10:12:36–10:14:40), at each match's own price: Fritz–Musetti
  +0.005 points, Griekspoor–Struff −0.025, Medvedev–Basilashvili +0.025; the women's 0.000. Over the 91-price grid:
  typical (median) 0.02–0.07, largest 0.11–0.25.
* **Correction to P17.5's reading of the forecast effect (10:20):**
  * **P17.5 measured the wrong thing.** It took each match's largest difference over the 91-price grid, which picks
    up the curve's own wobble (81–87 of 1,260 steps fall where they should rise, `fit.log`).
  * **Its explanation ("presumably the GPU's reduced-precision arithmetic") was a guess, and wrong.** The installed
    TabPFN (`tennis-tabpfn-local`, `inference_config.FINGERPRINT_FEATURE = True`) adds a feature computed as a hash of
    each row's values rounded to 12 decimals (`preprocessing/steps/add_fingerprint_features_step.py`). Any input
    change larger than 1e-12 therefore gives the row a new pseudo-random value of that feature, and moves its
    prediction in no set direction. Identical inputs give identical forecasts (the 0.000 matches).
  * **At each match's own price**, the Shanghai replay against training's inputs:
    * the 7 with a qualifier: mean 0.19 points, at most 0.34 (signs mixed: −0.34 to +0.29);
    * the 5 whose inputs differ only at rounding: 0.04–0.21; the 2 identical: 0.000.
  * **So the fill's own effect is about 0.1–0.2 points**, the excess over the fingerprint's. Neither check resolves
    anything finer.
  * **For any later comparison on this engine:** a forecast moves by up to about 0.2–0.3 points whenever a match's
    inputs change at all. Compare at the match's own price, and against that floor.
* **A test reached the network (found 09:24, fixed):** `test_linker_on_the_probe` links main-draw matches with no
  stand-in for TennisLive, so since `_qualifiers` it asked TennisLive (the 01:54 full run did). It now passes a
  stand-in (`_NoTennisLive`): 1.4 s, no new receipt.
* **Final tests** (10:12:48–10:17:09, the code as it stands): `test/master_pipeline/` and `test/prediction_run/`,
  **144 passed**, the owner's notebook-outputs test deselected (its saved outputs, as before). TennisLive's receipts
  from the linker: 68 before and after.

## P17.7 Claims and their evidence

| Claim | Evidence | Kind |
|---|---|---|
| A main-draw match's qualifiers and lucky losers get their qualifying rounds, Tennis My Life's held ones excepted | tests (`earlier_matches`, the lucky loser's round, `_qualifiers`); linking on real data: 3 of 3 qualifiers' round 1 filled with box scores, the direct entrants none | tested, observed |
| The run places them as it places last night's fills | the 21:25 Stage 0 run-side check: 3 box scores given to Tennis My Life's results-only rows; Shanghai replay: 14 of 14 filled under Stage 0's own ids | observed |
| Where the sources agree, the fill reproduces training | Shanghai replay: the 7 matches without a qualifier within 4e-8, 2 exact | observed |
| At Shanghai 2026's qualifying the sources disagree on the box scores, not the results | 13 of 13 boxes differ (1–5 first serves in), 13 of 13 scores equal | observed |
| Their forecast effect is about 0.1–0.3 points, at the engine's own floor | the replay fitted on its inputs and on training's: qualifier matches 0.14–0.27, rounding-level matches 0.10–0.18, identical inputs 0.000 | observed |
| The data check (A3b) no longer blocks a qualifier whose rounds the sidecar holds | test | tested |
| TennisLive's spellings are read as the one player they fit, never two | tests (`same_player`, `_tl_player`), the 4 Shanghai/Beijing names | tested |
| 129 of 148 men's main-draw live matches of 18–24 Oct were dated 1–2 days early | the runs' `live_stage0.parquet` against today's Stage 0 | observed |
| The switch dates a main-draw live row as training does | test; the five finals offline (P17.6) | tested, observed |

## P17.8 Threats to validity, and where a flaw would hide

* **The proof is one Masters' first round, men's.** A 250 or 500 (tonight's Vienna and Basel) has its own scorers;
  last week's 250s agreed with Tennis My Life on 33 of 36 boxes, Shanghai's qualifying on none.
* **Women's main-draw fills are not proven** (the exact replay refused them: P17.5). Their code path is the men's;
  the id quirk can leave a fill dated by the timeline's rule instead of the pin.
* **A round-1 qualifier whose round is not filled** (TennisLive silent, an opponent no Stage 0 player fits) is still
  predicted without it, flagged only in the notes.
* **The noise floor (P17.5)** limits every forecast comparison here to about 0.2 points; the fill's effect cannot be
  resolved below it.
* **The date switch is off**: until the owner turns it on, men's main-draw rows keep the old date (benign tonight).

## P17.9 What a re-design would do

* Measure TennisLive against the official numbers by level once (as the box-fill study did for the lower levels)
  and give a fill from a level where they disagree the 1-point bar instead of "complete".
* Build each fill's match id the way the feed's packages do (from the players' ids), so the women's quirk cannot
  arise; and let an exact replay hold a fill by its meeting, not its id.
* Date a live main-draw row by its main draw's first date unconditionally (the switch, made default).

## P17.10 Reviewer checklist

* `runs/replay_2026-10-05_R128_main_earlier_v3/replay_compare.json` and scratchpad `main_replay_detail.py`: the 7
  matches without a qualifier within 4e-8.
* `compare_fits.py` on `_v3` and `_training_inputs`: 0.2725 points at most.
* `live._qualifiers` is called only for linked main-draw matches; `_earlier` skips a round Tennis My Life holds with a
  box score.
* `live_rows.main_draw_date` returns None for a qualifying round; the switch is read from the environment at each call.

## P17.11 Reproduction

```
DP_WORK_TREE=C:/Users/zerom/tnr_daily_main2 ./python.sh src/eda/daily_prediction/dp.py run_day \
  --run data/studies/daily_prediction/runs/replay_2026-10-05_R128_main_earlier_v3 --replay-week 2026-10-05 \
  --replay-round R128 --replay-earlier tennislive --checkpoint auto --no-fit --keep-worktree
./python.sh src/eda/daily_prediction/dp.py replay-compare --run data/studies/daily_prediction/runs/replay_2026-10-05_R128_main_earlier_v3
./python.sh <scratchpad>/main_replay_detail.py replay_2026-10-05_R128_main_earlier_v3
./python.sh <scratchpad>/baseline_folder.py <v3 run> <training-inputs copy> <instance>/model_frame.parquet
./python.sh src/eda/daily_prediction/dp.py fit --run <each>; ./python.sh src/eda/daily_prediction/dp.py predict --run <each>
./python.sh <scratchpad>/compare_fits.py <v3 run> <training-inputs copy>
./python.sh -m pytest -q test/master_pipeline/test_earlier_rounds.py test/master_pipeline/test_qualifying.py test/prediction_run/
```
Scratchpad: `C:/Users/zerom/AppData/Local/Temp/claude/c--Users-zerom-Documents-Tennis-predictions/dd93a4a6-3a6e-47c1-838e-3ebf11a5cb9d/scratchpad/`.
Kept, not deleted (cleanup is the owner's call): work trees `C:/Users/zerom/tnr_daily_main` (the stopped replay),
`tnr_daily_main2`, `tnr_daily_main_w`, `tnr_daily_datefix_off`, `tnr_daily_datefix_on`; run folders
`replay_2026-10-05_R128_main_earlier` (stopped), `_v2` (refused), `_v3`, `replay_2026-10-05_R128_main_training_inputs`,
`replay_2026-09-28_R128_main_earlier_wta` (refused), `check_maindate_off_finals`, `check_maindate_on_finals`.

## P17.12 (27 Oct 2026, from 08:03 PDT): the owner's decisions; the date switch on, after a correction

Inserted inside Part 17 (not at the end) by agreement with the peer session `tennis-predictions-d1`, which was
appending its Part 19 at the time. The same session, `dd93a4a6-…`, resumed after a context summary. Part 17 was
re-read first. Times are from the clock (first command 08:03:39) or from files.

* **The owner's message (verbatim):** "switch the date fix on, dont built predictions for womens rounds 1, we arent
  betting women yet"
* **Read as:** make the main-draw date rule the default, and leave the women's first-day round 1 unbuilt, recording
  why. Set aside: taking women off the bet sheet (not asked).
* **Before changing the live path:** no live run in flight (no `dp.py` process; the newest run folder is from 25 Oct
  10:14). The plan's to-do list and claims are not built yet (steps 4 and 6). The peer session claimed
  `src/pipeline/live.py`, the notebook and this log for two hours. Asked, it answered "Go ahead with both now" to my
  four lines in `live._qualifiers` and to this section.
* **A correction to P17.6 and P17.7, found before switching:**
  * P17.6 and P17.7 said the switch "dates a main-draw live row as training does". That was shown on the finals, on
    25 Oct's Tennis My Life file, which had corrected its dates by then.
  * The archived copies of Tennis My Life's file of events under way (`data/raw/public_dump/tennis_my_life/
    superseded/ongoing_tourneys.*.csv`) dated Almaty's and Brussels' Monday (19 Oct) R32 rows 20261020 from the copy
    of 19 Oct 14:30 UTC through the copy of 22 Oct 14:30 UTC, and 20261019 from 23 Oct 14:30 UTC (e.g.
    Duckworth–Kecmanovic, Munar–Cina). Lyon's were right throughout.
  * Every live run of 11–25 Oct rebuilt (scratchpad `date_rule_runs.py`, then `date_rule_runs2.py`): the 25 Oct rule
    (Tennis My Life's main-draw rows first) dates 86 of the 148 men's main-draw matches right and 62 a day late. The
    old rule dates 19 right, 123 a day early, 6 two days early.
  * P17.6's with-and-without forecasts stand: they were made on 25 Oct's file.
* **The design added (an agent's choice):**
  * TennisLive's results, which the linker already reads for every main-draw match, list each finished match with its
    start. Almaty's, Brussels' and Lyon's first main-draw starts all fall on 19 Oct (the held files).
  * `qualifying.main_draw_first_day`: the earliest start among the event's main-draw singles matches on TennisLive and
    the listed match's own. It is read in the venue's zone (`venue_zone`: TennisLive's country of the event and the
    city after " - " in its name, through the timing study's `srcc_tz` tables), else as the UK day. The zone matters
    because Tennis My Life dates by local day: its 2026 file puts Auckland's first main-draw day on Monday 12 Jan,
    and an 11:00 start there is 22:00 UTC the day before.
  * `live._qualifiers` writes it as `event_main_date` on the main-draw row, once TennisLive's results arrive; nothing
    when TennisLive does not answer.
  * `live_rows.main_draw_date` takes the earliest of Tennis My Life's earliest main-draw row of the event and each of
    the CSV's main-draw rows of the event, by its `event_main_date` where the linker gave one, else its own `day`.
    Qualifying rows are unchanged. `upcoming_rows` copies `event_main_date` into a live row only for a qualifying round,
    as Stage 0's docstring describes that hint.
  * The switch: on unless `LIVE_MAIN_DRAW_DATE=0`.
  * A first version took the earliest of Tennis My Life's row, the linker's day and the CSV's UK days of every row. It
    was replaced after the first full test run below by the per-row reading above, so that a far-east UK day cannot
    undercut the linker's local day; the full suites were run again on the final version.
* **Checks, with what had been seen:**
  * `test_earlier_rounds.py`, `test_qualifying.py` and `test/prediction_run/`: 47 passed (08:24:42–08:24:53, the first
    version), and 47 again on the final version.
  * `test/master_pipeline/` and `test/prediction_run/` (08:27:24–08:35:54, the first version): 166 passed, 1 failed:
    `test_health_signals.py::test_the_acknowledged_flags_are_real_canary_flags`. That is a data-state test. The canary
    of 26 Oct 15:02 UTC no longer gives the acknowledged `sackmann_tennis_atp:ARCHIVE`; it gives `GONE` for Sackmann's
    ATP, WTA and slam point-by-point repositories, and `SHRANK` and `REVISED` for Tennis My Life's manifest. Not from
    this change; the peer found it alone too. Reported to the owner, not acknowledged: the acknowledgments are Part
    10's (session `f471b5ba`).
  * The same suites on the final version (08:42:18–08:47:48): 166 passed, the same 1 failed.
  * **Every live run of 11–25 Oct, rebuilt from what each could see** (`date_rule_runs2.py`; output
    `date_rule_runs2.out`): the archived Tennis My Life copy in effect at the run's start (10 minutes allowed for its
    own refresh), TennisLive's held results limited to matches finished by then (finished_at, else start + 3 h), and
    the run's matchups CSV, against today's data-check Stage 0. **The decided rule: 148 of 148 on training's date**
    (08:38:50). A first try found TennisLive's files by name and matched Challenger files too, finding none for
    Brussels, Lyon and Shanghai: a bug in the script, fixed by taking the event as the linker does (TennisLive's tour
    kinds).
  * Limits of that check: TennisLive's held files are each event's last fetch (Brussels' and Lyon's 20 Oct,
    Almaty's 22 Oct, Shanghai's 25 Oct), filtered by finish time. Vienna's and Basel's run of 25 Oct has no training
    date yet; Tennis My Life now dates both main draws 20261026, the rule's date.
  * **A live link** (08:39:21–08:39:25, scratchpad `e2e_date.py`; two TennisLive requests with receipts: the 28 Oct
    date page and Basel's results). A made-up Basel R16 listing linked with `event_main_date` 20261026 (Basel's zone),
    and `upcoming_rows` dated it 20261026 with and without the switch. Not a discriminating case: Tennis My Life dates
    Basel's rows 20261026 this week. The made-up Vienna listing was left out: "'Jakub Mensik' names 2 Stage 0 players
    (atp:210150, atp:210084)".
* **Found on the way, not acted on (reported to the owner with a recommendation):** Stage 0 holds 11 of Jakub
  Mensik's Challenger matches of January–May 2023 (Sackmann's `atp_matches_qual_chall_2023.csv`) under a second id,
  atp:210084. Same name, country and age at each date, in weeks when his main id, atp:210150, has no match. The linker
  and the run refuse an ambiguous name, so any Mensik listing is left out. One row of the decided `id_aliases.csv`
  would merge them.
* **The owner's second instruction:** recorded in the 24 Oct decision's "Not covered" and in CLAUDE.md; nothing built.
* **Documents:** the decision `docs/decisions/2026-10-27-main-draw-live-date.md` and its README row; CLAUDE.md (the
  date bullet under Prediction runs; women's round 1 under the qualifying section); the 24 Oct decision; the module
  docstrings of `live_rows.py` and `qualifying.py`.
* **Threats to validity:**
  * The far-east reading rests on the timing study's hand-made zone tables and on TennisLive naming the country. A
    multi-zone country whose city the tables lack falls back to the UK day.
  * The rule assumes no source dates a main-draw match before the main draw's first day. That held for the 148
    matches here; no far-east or American event was among them.
* **Reproduction:** `./python.sh <scratchpad>/date_rule_runs2.py`; `./python.sh <scratchpad>/e2e_date.py` (asks
  TennisLive); `./python.sh -m pytest -q test/master_pipeline/test_earlier_rounds.py test/prediction_run/`.

# Part 18 (25 Oct 2026, from 14:59 PDT): the closing-line ledger, every bet sheet's predictions against Pinnacle's close

Kept by Claude Opus 5.5 (`claude-opus-5-5`), Claude Code in VS Code, session `37a84738-65ac-4624-b38a-fbe769e0e53e`
(`tennis-predictions-d1`). Local time PDT (UTC−7); times read from the clock or files. Opened at 15:00, after reading
only (about 14:30–14:59: no file written but scratchpad readers), before the first edit.

## P18.1 The request (verbatim)

> The master_pipeline, do any of the A1-A5 functions save the predictions somewhere?
> At some point in the future, comparing the "best model predictionsat the time of the run" to the closing line (as
> well as see how much the line drifted since then to calculate CLV) will be useful.
>
> If we dont have that id like to build that.
> the ../ufc-predictions/  pipeline has a similar mechanism, but tennis will be a bit more complicated

## P18.2 What the files showed, before any change

* **The predictions are saved.** Each A5 sheet, and each one after an A6 reprice, writes
  `predictions/<day>/records/bet_sheet_<made>.csv` (73 columns: the quote time, Pinnacle's odds with the margin, the
  margin-free price the model was fed, the model's chance, the pick, the decision, `match_id`, `run`) and its
  provenance (`made_at`, model, instance). A sheet is never replaced. A4's engine archives `live_<run>.csv` beside
  them. The run folder keeps `curves.parquet` (the model's chance at 91 prices per match) and `matchups_input.csv`
  (with Pinnacle's `pinnacle_matchup_id`). 22 live run folders from 11 Oct; 4 hold no predictions (stopped runs).
* **Nothing records the close, the drift or CLV.** A7 (`grade`) scores one run's log loss once the repository's Stage
  0 holds its results. The production-integrity plan (the owner's, 22 Oct) lists "closing-line value for bets;
  backfilled from 10 Oct" in step 3, planned. Its principle 8: the outcome alarm is the strength of the model's lean,
  not CLV; CLV "is kept for the bets placed, as a check on prices", since the market does not move toward this model
  before the close (bet timing: slope +0.01 [−0.02, +0.04]).
* **UFC's mechanism** (`../UFC-Predictions/src/post_prediction_modifiers/snapshot_real_world_predictions.py`): one CSV
  per card and sex, the last run before the card overwriting earlier ones. Studies
  (`src/eda/close_edge_diagnosis/live/01_build_archive_table.py`) join it to the open, 10-day, 4-day and closing lines
  of the scraped database. UFC's close comes in one scraped table; tennis has none.
* **Where a tennis close can come from:**
  * **TennisExplorer's tour adapter** (the daily `pinnacle_closes` job; `data/dump/odds/tennisexplorer/`): each finished
    main-draw match, every book's prices with their times, Pinnacle's among them (from 10 Oct: 242 matches, 236 with
    Pinnacle).
    * **Main draws only:** the rounds of its 9,978 matches are "1. round" to "final", none qualifying. The lower-level
      adapter leaves out "main" events, so tour qualifying (bet since 22 Oct) has no page in either.
    * **Its last Pinnacle change comes before the start:** over 4,668 matches of 2026, a median 47.5 minutes before the
      listed start, a quarter more than 110, a tenth more than 219 (minimum −4).
    * The Pinnacle-gap research found it equal to Pinnacle's own price to the cent on 93% of tour-level readings.
  * **Pinnacle's own pulls**, by `matchup_id`: the bet-day pulls (`data/dump/odds/pinnacle/pulls/`, 30 pulls on 12
    days from 11 Oct) and P11's 10-minute capture (`data/dump/odds/pinnacle_capture/pulls/`, 216 pulls, 22–23 Oct).
    A standing capture is the owner's open decision (CLAUDE.md, P11).
* **Results:** a played match keeps the live row's id in Stage 0 (`dp_steps.step_grade`). The repository's Stage 0 is
  of 21 Oct; the newest run's own Stage 0 and the data check's are of today.
* **STATUS at 14:58:**
  * `pinnacle_closes` exit 0 at 07:30 today;
  * an ALERT not this work's: Tennis My Life's 2025_wta.csv held two runs in a row;
  * live model `template_2026-10-21b`.
* **Sessions and the kernel:** every tennis session idle (ListAgents, 14:57). The owner's kernel is stale since Parts
  14–17 (the notebook's saved STATUS cell shows StaleKernel), so editing `src/pipeline/__init__.py` here costs no
  extra restart.

## P18.3 Interpretation acted on

* **The answer:** yes, A5 and A6 save every prediction with its price and time. What is missing is the close.
* **Built:** a closing-line ledger, rebuilt in full from the records each time it runs (never hand-kept: the
  integrity plan's lesson), with a notebook cell A8:
  * one row per sheet and predicted match (every prediction kept), with two views: the match's first sheet, and its
    last sheet before the start;
  * Pinnacle's close per match, its source, and how long before the start it was observed;
  * the drift from the sheet's price to the close, and whether it moved toward the model;
  * the CLV of each sheet's pick, at the sheet's Pinnacle price;
  * the model's chance re-read off the run's curve at the closing price (tennis keeps the curve; UFC has none);
  * the result and log losses, once a Stage 0 holds it.
* **Agent's choices (so marked in the code and docs):**
  * **The close:** the latest pre-start observation of Pinnacle's price among its own pulls (bet-day and capture: the
    last usable, not in-play) and TennisExplorer's last Pinnacle price (observed at its last change).
    * "True close" only when Pinnacle's own next pull no longer lists the match pre-match within 15 minutes (P11's
      measure).
    * TennisExplorer's price is left out when untimed or far from its other books (the odds input's own test).
  * **CLV:** the pick's expected profit per unit if the close's margin-free chance is right, p_close × d_taken − 1,
    beside the price ratio d_taken / d_close − 1.
  * **The summary's default view:** the last sheet before the start, BET rows. Every row stays in the file.
* **Set aside, for the owner:**
  * **P11's 10-minute capture as a standing job:** the only true closes, and the only closes of qualifying. The owner's
    open decision; recommended in the report.
  * **A placed-bet record** (step 3): the bets actually placed, their venue and price. The CLV here is the sheets'
    picks at Pinnacle's price.
  * **Nightly grading and the strength-of-lean alarm** (step 3): the outcome alarm is not CLV (principle 8).
  * **Qualifying from TennisExplorer's day pages:** new collection, not asked.

## P18.4 Plan, with the check for each step

1. **Code:** `src/pipeline/closing_line.py` (new: the ledger and its summary) and one name in
   `src/pipeline/__init__.py`. Check: tests on synthetic sheets, pulls, site tables, curves and results
   (`test/master_pipeline/test_closing_line.py`).
2. **The backfill:** every sheet from 11 Oct. Checks:
   * counts by source;
   * the sheet's own price against TennisExplorer's Pinnacle at the quote time (a wrong link or side shows as
     disagreement);
   * the curve read at the sheet's own price against the sheet's model chance;
   * a hand check of a sample against the raw pulls and the site's moves (the plan's "the backfill's numbers by hand on
     a sample").
3. **The notebook:** cell A8 after A7. Check: `test_master_pipeline.py`'s notebook test (the functions exist).
4. **Docs:** `predictions/README.md`, the master pipeline README, the integrity plan's step-3 row, this log.

## P18.5 Files claimed by this session (from 15:00 PDT)

* **New:** `src/pipeline/closing_line.py`, `test/master_pipeline/test_closing_line.py`, `predictions/clv/`.
* **Edited:** `src/pipeline/__init__.py` (one name), `scripts/master_pipeline.ipynb` (one cell), `predictions/README.md`,
  `docs/studies/master_pipeline/README.md`, `docs/decisions/2026-10-22-production-integrity-plan.md` (step 3's
  status), this log.

## P18.6 Chronology

| When | Step | Results seen by then | Output |
|---|---|---|---|
| 14:30–14:59 | Read the notebook, `diagnostics.py`, `predict.py`, `bet_sheet.py`, `config.py`, `__init__.py`, the integrity plan, the TennisExplorer adapters, `pinnacle_capture.py`, `odds_input.py`, `dp_steps.step_grade`, UFC's snapshotter and archive table; STATUS; ListAgents | P18.2's counts (scratchpad `facts.py`, `facts2.py`: no prices printed beyond two sample rows) | — |
| 15:00–15:08 | `src/pipeline/closing_line.py`, first version: close = the later observation of our own pulls and the site; CLV headline = expected profit at the margin-free close; results by id, else by pair and date | — | code |
| 15:08 | **First run on the real files** (`--no-write`, 71 s). Two problems seen: (1) **Basel R32 matches not yet played showed "won"/"lost"**: the result fallback (same pair within 21 days) took an earlier meeting at another event (Fritz v Tsitsipas, van de Zandschulp v Michelsen); (2) the headline CLV read −2.5% [−3.3, −1.6] "below 0" while the price beat the close by +0.6%: the expected-profit measure scores a bet at the close itself at minus Pinnacle's margin (about −2.8%), so 0 is the wrong reference | the summary lines, 15 table rows | — |
| 15:10 | Diagnostics (scratchpad `clv_diag.py`). **Checks:** the site's record of Pinnacle at each sheet's quote time equals the sheet's own price on 162 of 191 readings, 0 with the sides swapped (the link and sides are right); the curve re-read at the sheet's price is within 0.09 points of the sheet's chance (interpolation between the 91 prices and the curve's wobble, P17.6). **64 "last seen" prices were our own early pulls, a median ~4 hours before the start** | the checks; counts by source; 15 rows where our last pull and the site's last record differ (taken hours apart) | — |
| 15:12–15:16 | Fixes, each before a re-run: the result fallback needs the same tour, pair, **round and event name** (window 14 days before to 4 after); Stage 0 filtered to the ledger's players first (the build: 70 s → 6 s; the old key over 874k rows); **the close rule reordered:** our own confirmed close, else the site's last record (the training data's close), unless a later pull of ours saw another price; else our earlier pull, "last seen", left out of the headline; the headline CLV became the price measure (odds taken against the closing odds), the expected profit shown beside it with the score of a bet at the close itself | the 15:08 and 15:10 readings | code |
| 15:17 | Re-run: 90 closes (17 our own, 73 the site's), 53 earlier-only (47 qualifying); picks' CLV +0.9% [−0.4, +2.2], n = 35, unresolved. Seen next: 6 main-draw matches with only an earlier price; 6 matches whose every sheet came after the listed start | the summary | — |
| 15:18–15:22 | Looked at those (scratchpad `clv_diag2.py`, `pull_states.py`): Shimabukuro v Medvedev and Rybakina v Kudermetova were read 3–5 minutes before the real start (Pinnacle rewrites the start to it, 12:45:26), the next pull listing them with **"market cutoff not after the pull"**; the staging gives **"start not after the pull"** only while the cutoff is still ahead (a match running late, its pre-match price open), and P11's `closes()` skips those rows; Pinnacle lists the in-play market under a new matchup id, so the pre-match one goes "gone"; **3 predicted pairings never happened** (Collignon v Rune, Wang v Bejlek, Day v Birrell: the site shows the player against someone else) | the pulls' reasons and two matchups' series | — |
| 15:22–15:25 | Fixes: "cutoff passed" counts as closed; rows of a match running late count as pre-match; every match keeps one bet-time row (its last sheet, flagged `made_after_start`, when all came after the listed start); a pairing Stage 0 shows replaced is "not played as listed", and void matches (that, walkovers) leave the summary; an earlier price never fills the close's odds (so no CLV is computed on it) | 15:18's readings | code |
| 15:25–15:27 | Tests `test/master_pipeline/test_closing_line.py`: 13 passed at the first run, so each key rule was broken in turn (scratchpad `mutate.py`): 3 of 5 caught. **Not caught:** the late-match rows (the test built its rows from the module's own constant) and the event-name condition (the decoy meeting was in another round). Tests fixed (the staging's literal reasons, and a test that they appear in `src/ingest/pinnacle.py`; the decoy in the same round at another event): **5 of 5 caught, 14 passed.** The mutation script's first restore wrote CRLF line endings (text mode on Windows); restored byte-for-byte from the scratchpad backup and checked with `cmp` | the test and mutation outputs | tests |
| 15:28 | `src/pipeline/__init__.py`: the name `clv_ledger`, the module `closing_line`. The notebook (last saved 09:14, before my read): cell A8 inserted after A7; in the first markdown cell, one bullet ("Where the outputs land") and one table cell | — | code, notebook |
| 15:29–15:34 | `test/master_pipeline/` without the owner's saved-outputs notebook test (as in Parts 14–17): **137 passed.** The notebook valid; every `tp.<name>` its cells call exists; its 7 saved outputs kept | — | — |
| 15:34 | **The backfill written** (`predictions/clv/`). A wording slip seen: "175 matches, 69 of them picks" counted picks after the void were removed; fixed (72) | the summary | ledger |
| 15:35 | **Hand check** (scratchpad `hand_check.py`): 4 picks, each from the raw files (the sheet's record row, the run's matchup row, every raw pull of the matchup, the site's page and Pinnacle moves, Stage 0's row), CLV recomputed by hand: **equal to 5 decimals; the sides right**, Pinnacle's home on side B and the site listing side B first included. **Found two faults:** (1) Carreno Busta v Auger-Aliassime took a site "close" whose record ended 18 hours before the start, and the site keeps only some of Pinnacle's changes (it missed Vacherot's 2.28 → 2.30 → 2.32); (2) Siniakova v Linette: Pinnacle relisted the start at 07:30 while the pre-match market was gone by 06:50, so "49.8 minutes before the start" was wrong (the close itself right) | the 4 picks' raw evidence | — |
| 15:36 | **A look at results before a choice:** the site's lead (median 47 minutes, 75th percentile 117, 90th 270) and, in the same command, the bets' price CLV kept and dropped at caps of 120 and 180 minutes (120: kept 19 of 25, mean +1.6%; dropped −0.45%). **Chose 120 minutes** (two hours, about the 75th percentile); the CLV split had been seen (P18.8) | the leads; the CLV split by cap | — |
| 15:36–15:37 | Code: the 2-hour cap on the site's close (`CLOSE_LEAD_MAX_MIN`); a later pull of ours with the same price shows the site's price held until then; the start capped at the moment our pulls saw the market shut; **the pulls sorted by time** (found writing a test: `pinnacle_capture.closes` reads a matchup's final listed start as its last row in frame order, and the bet-day folder came first). Tests: 17 passed | — | code, tests |
| 15:37 | Rebuilt and hand-checked again: the long-lead case is now "earlier price only"; Siniakova v Linette 10 minutes before the market shut; the other two unchanged and equal by hand | the summary (P18.7) | ledger |
| 15:38–15:40 | Docs: the master pipeline README (A7 and A8 rows, a section "The closing line (A8)", decision 5's note, the files); `predictions/README.md` (`clv/`); the integrity plan's step-3 row; CLAUDE.md (one table row). A count checked before it was written: of 55 qualifying matches, 5 have a close (the capture's, 23 Oct), 50 only an earlier price | the counts | docs |
| 15:40–15:41 | **A8 in a real kernel on the tennis interpreter** (scratchpad `run_a8_kernel.py` through nbclient: the base install's `python3` kernelspec lacks pyarrow; nothing installed or changed): the HTML summary and table shown, 332 rows. Thinking sheets (2 of 22, 45 rows): their curves hold the ensemble's chance (within 0.0006 of the sheet's; 0.0102 off the local model's), so the re-read at the close is the chance bet on | — | — |
| 15:40–15:45 | `test/master_pipeline/` on the final code, without the owner's saved-outputs notebook test: **140 passed** (123 before this Part, 17 new) | — | — |

## P18.7 The first reading (25 Oct, 15:37; sheets of 11–25 Oct)

Each match on its last sheet before the start; the void left out:
* **Coverage:** 22 sheets, 332 predictions of 175 matches, 72 picks.
  * A close for 78: 21 true closes of our own, 57 the site's (a median 24 minutes before the start).
  * No close for the rest: 66 with only an earlier price (a median 7.2 hours before), 21 not started, 5 awaiting the next download, 5 void.
  * Qualifying: a close for 5 of 55, all read by the capture on 23 Oct.
* **The picks' CLV** (n = 30), against the closing odds:
  * by price: +1.1% [−0.4%, +2.6%], unresolved, P(above 0) 0.92;
  * the line's move toward the pick: +0.58 points [−0.17, +1.33];
  * expected profit if the close, margin removed, is fair: −1.6% [−3.1%, −0.2%], where a bet at the close itself scores −2.7%.
* **The move toward the model:** −0.06 [−0.21, +0.09] of its disagreement, n = 78 (the backtest: +0.01 [−0.02, +0.04]).
* **At the close:** 29 of 30 picks still +EV by the model's curve.
* **Graded (78), log loss, above 0 = the model better:**
  * against the close: −6.6 mLL [−22.5, +9.3], unresolved, P(above 0) 0.21;
  * against the price it was fed: −5.7 mLL [−19.9, +8.5], unresolved, P(above 0) 0.21.
* **Checks:** the site's Pinnacle at the sheets' quote times equal to the sheets' own prices on 162 of 191 readings, 0 swapped; the curves within 0.09 points of the sheets' chances.
* These numbers decide nothing: a reading of prices, at a sample size that resolves little (principle 8; the adoption framework).

## P18.8 Claims and their evidence

| Claim | Evidence | Kind |
|---|---|---|
| A5 and A6 already saved every prediction with its price and time; nothing recorded the close | the records' 73 columns; the integrity plan's step 3 "planned"; no CLV code in `src/pipeline/` | observed |
| The ledger joins each sheet's prediction to the right match and sides at Pinnacle and at the site | 0 swapped of 191 readings at the quote times; 4 picks by hand from the raw files, both side-B cases included; tests | observed, tested |
| The closing-line value and drift are computed as stated | the hand check, equal to 5 decimals; tests with numbers worked by hand | observed, tested |
| A true close needs our own pull within 15 minutes of the market shutting; a match running late keeps its open price | the pulls' reasons (`src/ingest/pinnacle.py`'s order: the cutoff before the start); Cobolli v Wawrinka's market reopened at 17:10:12 and was taken; tests | observed, tested |
| A result is never taken from another meeting at another event | the 15:08 fault and its fix; the decoy test (same pair, same round, another event) | observed, tested |
| Each key rule is guarded by a test | 5 rules broken in turn, 5 caught | tested |
| A8 runs in a kernel and shows its summary | the nbclient run on the tennis interpreter | observed |

## P18.9 Threats to validity, and where a flaw would hide

* **The 2-hour cap was chosen after the CLV split by cap had been printed** (15:36: at 120 minutes the kept bets read +1.6%, the dropped −0.45%). A reviewer should read the headline at other caps; the ledger keeps every reading (`close_min_before_start`, `te_odds_a/_b`), so it costs one filter.
* **The site's record of Pinnacle is partial.** It equals our own pull at the same moment on 162 of 191 readings, so a site "close" can miss a late move. That pulls the CLV toward 0 by an unknown amount.
* **A "true close" rests on the next pull.** "Gone" could be a withdrawal rather than the start. And a market can shut and reopen: Cobolli v Wawrinka's shut at 17:00 and reopened at 17:10 with a new price. The capture was still pulling, so the 17:10 price was taken; had the pulls stopped at 17:00, the 16:50 price would have counted as the close.
* **The start is approximate.** It is the latest listed time, capped at the observed shut, and the site's start may be the scheduled time. So the leads are approximate.
* **The picks are the sheets', not the bets placed.** A match on several sheets is read on its last sheet before the start. A bet placed from an earlier sheet, or at another venue, has another CLV; the ledger holds every sheet, but no record of the bets exists.
* **Results come from the freshest Stage 0 by file time.** The fallback by event name fails quietly for a renamed event (counted as no result).
* **Void matches are known only through Stage 0's draw.** Before the results, a withdrawn pairing shows as "awaiting" or "last seen".
* **Small n and simple intervals:** 30 picks; normal approximations, no clustering by day (a day's picks share news).
* **The model at the close is a re-read of its curve,** not a refit. It inherits the curve's wobble (P17.6: about 0.1–0.3 points).

## P18.10 What a re-design would do

* Record Pinnacle's own listing every 10 minutes as a standing job (P11's capture): every close true, qualifying included. The site would then be a cross-check, not a source.
* Pre-register the close's lead cap before any CLV is seen.
* Add a placed-bet record (venue, price, time, stake, the sheet it came from), and compute the CLV of the bets placed at their own price.
* Write Pinnacle's matchup id into the sheet's record itself, instead of reading it from the run's matchups.
* Give intervals by match-day bootstrap.

## P18.11 Reviewer checklist

* **`own_closes`:** "start not after the pull" rows count as open and "market cutoff not after the pull" as shut, by the staging's order (`src/ingest/pinnacle.py`; `test_the_reasons_read_are_the_stagings_own` pins the words).
* **`match_closes`, in this order:** a true close of our own; pending; the site within 2 hours unless a later pull of ours saw another price; awaiting (main draw only); last seen; none. An earlier price never fills the close's odds.
* **`results`:** an id match, else the same tour, pair, round and event name in the window; never another event's meeting (the decoy test).
* **The sides:** Pinnacle's home by the record's `home_side` (else the names); the site's by its name test; `checks()` reports swapped readings (0).
* **`summarize`:** the void out; CLV only on `close_kind == "close"`; the reporting rule ("unresolved" with P(above 0), never "tie").

## P18.12 Reproduction

```
./python.sh -m src.pipeline.closing_line                       # writes predictions/clv/ and prints the summary
./python.sh -m pytest -q test/master_pipeline/test_closing_line.py
PYTHONPATH=. ./python.sh <scratchpad>/clv_diag.py              # likewise clv_diag2.py, pull_states.py, clv_profile.py
./python.sh <scratchpad>/hand_check.py                         # after the ledger is written
./python.sh <scratchpad>/mutate.py                             # each rule broken once; restores the source byte for byte
./python.sh <scratchpad>/make_a8_check.py <scratchpad>/a8_check.ipynb
./python.sh <scratchpad>/run_a8_kernel.py <scratchpad>/a8_check.ipynb <scratchpad>/a8_check_out.ipynb
```
Scratchpad: `C:/Users/zerom/AppData/Local/Temp/claude/c--Users-zerom-Documents-Tennis-predictions/37a84738-65ac-4624-b38a-fbe769e0e53e/scratchpad/`.
Nothing deleted. The owner's kernel must be restarted before A8 (it is stale since Parts 14–17 anyway).

---

# Part 19 (27 Oct 2026, from 07:50 PDT): the bet-day cells run top to bottom; A7 grades every run that is due; A6 becomes A5b

Session `37a84738-65ac-4624-b38a-fbe769e0e53e` (tennis-predictions-d1), the one that wrote Part 18. Its context was
summarised once between Part 18 and this Part; Part 18 and this log's end were re-read before this Part was opened.

## P19.1 The owner's request, verbatim

The question (27 Oct, after Part 18):

> I want to confirm something.
> My process is generally WHEN ITS CONVIENET and I have a good sense of when matches are finishing, I run A1-A5.
> This ends up about once a day or once every few days if its slow.
> Should I just sequentially run A1-A8 when im checking for new prices instead?

Answered in chat (A8 at the end of each run; A6 only for later the same day; A7 left out; closes depend on recording,
not on how often a cell runs). The owner's reply, the request acted on here:

> this requires me to memorize and understand whats happening along the way.
> A workflow that more matches my habits is ideal.
> I know running cells more often wont get me more closing prices?
> Its more, I have many other priorities in life and I decide to bet tennis BEFORE close at some point in a range of
> time. Im not following whats going on with when tennis matches are posting, so I do it when convienient. I also dont
> know when prices are posted, so my habits are to just run this casually every day or so when I feel like it.
> If i could just sequentially run A1-A8 (except A6) it would make my life easier. But Id want the aproximate same net
> effect of I did A7 more selectively.
> A6 could maybe renamed A5b, as I see b steps as more optional

## P19.2 What the files showed, before any change

* **A7** (`# tp.grade(RUN)`, commented out) runs the engine's `dp.py grade`: each prediction of one run joined by match
  id to **the repository's Stage 0** only (`dp_steps.step_grade` reads `C.MATCHES`), written to the run's
  `graded.csv` and `grade.json`. That Stage 0 changes only at B6, last run 21 Oct 06:48. **No live run has ever been
  graded:** 22 live run folders, 18 with predictions, none with `grade.json`. Nothing reads `graded.csv` or `grade.json`.
* **Run in sequence, A7 as written would grade the run A4 just made,** whose matches are not played: nothing.
* **The freshest results on disk** are the newest live run's own Stage 0 (25 Oct 09:23) and the data check's
  (25 Oct 09:16). A run's own `stage0/stage0_matches.parquet` holds **none of its upcoming matches** (0 of 22, 19 and
  21 in the last three runs): the live rows sit apart, in `live_stage0.parquet`. So it is safe to grade from.
* **A8's joins on the real ledger:** of 112 matches with a result, 107 by match id, 2 by players, round and event,
  3 "not played as listed" (the engine's id-only join would find 107 of the 109 played).
* **A probe of the engine's grade** on a scratch copy of `live_2026-10-19_173201` (its `predictions.csv` only): 37 of
  38 graded from the repository's Stage 0, about 1 s; it writes `graded.csv`, `grade.json`, `steps.json` and
  `code_used/grade_<pid>.json` (every dp.py process does; the predict step's provenance is not rewritten, and a
  reprice already adds its own file the same way).
* **A3 on a day with nothing predictable raises** (`build_matchups`: "no match left to write"), and the kernel keeps
  the previous `MATCHUPS` and `RUN`. Pressing on in a kernel left open since an earlier day, A3b and A4 would check
  and predict the old matchups (their prices then blocked as stale on the sheet, after a 10-minute run).
* **A4 leaves `RUN` as it was when it fails,** so A5 would show the earlier run's sheet.
* **"A6" is named** in the notebook (cells, Setup's `STALE_MINUTES` comment, both markdown cells), `bet_sheet.py`'s
  three plain-word texts ("reprice with cell A6"), one test assertion, the master pipeline README, `predictions/README.md`,
  two decision records and this log's earlier Parts.
* **Other sessions:** tennis-predictions-ad and -b3 busy; -ad resumed Part 10 at 06:30 today (step 2, the bet sheet's
  side, still to build). None of the files below changed today. Both were sent this Part's claim (P19.5).

## P19.3 Interpretation acted on

* **The routine:** the bet-day cells run top to bottom whenever the owner likes; the b cells are optional and skipped
  in a run-through (A3b, and A5b, the former A6).
* **A7, "the approximate same net effect" as run selectively:** each earlier run is graded once its results are on
  disk, again only when more of them arrive, never the run just made, and quickly when nothing is new.
* **Agent's choices (marked so in code and docs):**
  1. A7 reads the freshest Stage 0 on disk, A8's rule (the repository's, the data check's, the newest live run's own),
     not only the repository's: a selective A7 waited for B6, which the owner's routine never runs.
  2. A run is due when that Stage 0 holds a result (completed or retired, the engine's rule) for more of its
     predictions than its last `grade.json` counted.
  3. No predictable match: A3 says so without an error, A3b to A5b skip, A7 and A8 run.
  4. A4 clears `RUN` first, so a failed run never leaves an earlier one for A5.
  5. A7 and A8 keep their numbers; there is no A6 now.
* **Set aside:**
  * renumbering A7 and A8 (they are named in CLAUDE.md, the integrity plan, the README, code): offered to the owner;
  * making A5b skip itself right after A5: the owner skips b cells, and a deliberate early reprice should still work;
  * dropping a match that would stop the run (`check_matchups`' error) by itself: a different question, not asked;
  * the engine's join by id only (A8's fallback finds 2 more of 109): unchanged; noted;
  * editing the two decision records that say "A6": records of their day; the README notes the rename.

## P19.4 Plan, with the check for each step

1. **The engine:** `dp.py grade --stage0 <file>` (optional; default the repository's, unchanged); `grade.json`
   records the Stage 0 read and its time. Check: a test on a temporary run and Stage 0; the CLI test that every
   issued command parses.
2. **The layer:** `grade(run, stage0=)`; `grade_due()` (the due runs, one compact table; the engine's output to its
   log); `build_matchups` returns None with a plain line when nothing is predictable; `check_matchups`, `data_check`
   and `predict_day` skip None. Check: tests of the due rule (due, up to date, not played, no predictions), of the
   empty day, and of the skips.
3. **The notebook:** A3, A3b, A4, A5b (the former A6), A7, the A8 and B6 comments, Setup's comment, the two markdown
   cells; no saved output touched. Check: the notebook valid; every `tp.<name>` exists; the A-cells, run in a kernel
   on a scratch copy against a day with nothing to predict, skip and run as described.
4. **A7 on the real runs,** once, after the tests: the catch-up of 18 runs, its table checked against A8's results.
5. **Docs:** the master pipeline README, `predictions/README.md`, the daily pipeline README (one line), the integrity
   plan's step-3 cell, this log.

## P19.5 Files claimed by this session (from 08:20 PDT; messages `980c5b65…` to -ad, `c73debd3…` to -b3)

* **New:** `test/master_pipeline/test_grade_due.py`.
* **Edited:** `scripts/master_pipeline.ipynb`; `src/pipeline/predict.py`, `live.py`, `readiness.py`, `__init__.py`,
  `bet_sheet.py` (three strings); `src/eda/daily_prediction/dp.py`, `dp_steps.py`;
  `test/master_pipeline/test_master_pipeline.py`; `docs/studies/master_pipeline/README.md`, this log;
  `predictions/README.md`; `docs/studies/daily_prediction/README.md`; the integrity plan's step-3 cell.
* **Written by A7's first run:** each graded run's `graded.csv`, `grade.json`, `steps.json` entry and
  `code_used/grade_<pid>.json`.

## P19.6 Chronology

| When | Step | Results seen by then | Output |
|---|---|---|---|
| 07:50–08:05 | Answered the first question in chat from the notebook's cells and `predict.py`, `dp_steps.reprice` (no age limit; refused only when the run's inputs changed) | — | chat |
| 08:05–08:20 | Read the notebook, `step_grade`, `dp.py`, `runner.py`, `live.build_matchups`/`check_matchups`, `readiness.data_check`, `predict.predict_day`, `closing_line.stage0_path`/`results`, the tests; the facts of P19.2 (scratchpad `grade_probe/`); ListAgents; the files' times | the 37-of-38 probe; A8's join counts | — |
| 08:20 | Claims sent; this Part opened | — | log |
| 08:20–08:25 | Replies: -b3 "No overlap"; -ad (switching the live main-draw date on, the owner's word of today) asked to edit `live._qualifiers` (4 lines) and to insert P17.12 inside Part 17. My `live.py` edits made first (`build_matchups` returns None, `check_matchups(None)`), then -ad told to go ahead (message `9717f7b4…`); `live.py` is theirs from then on | — | code |
| 08:20–08:28 | The engine: `step_grade(run_dir, stage0=None)`, Stage 0 deduplicated by match id, `grade.json` gains `stage0` and `stage0_written`; `dp.py grade --stage0`. The layer: `grade(stage0=)`, `grade_due()`, `predict_day(None)` and `data_check(None)` skip; `__init__` exports `grade_due`; `bet_sheet.py`'s three "cell A6" texts say A5b; the test asserting "A6" now asserts "A5b"; the dry-run command list gains `grade --stage0` | — | code |
| 08:28 | A fault of mine found before any run: `_results_source` tested `path.parent.parent == runs`, but a run's Stage 0 sits at `<runs>/<run>/stage0/`, so it never matched; now `runs in path.parents`. The wording "results from the results …" rewritten | — | code |
| 08:29 | `test/master_pipeline/test_grade_due.py`: **5 passed** at the first run (the due rule on five runs with literal statuses, a walkover among them; the run just made never graded; the engine end to end through `tp.grade(stage0=)` with log losses worked by hand; a day with nothing to predict; the plain-words source). Not mutation-checked: each rule is pinned by an exact call list or count from literal fixtures, and breaking the engine's files in place would expose other sessions to broken code | — | tests |
| 08:30–08:31 | The notebook through a script (scratchpad `edit_notebook_p19.py`): each old text must occur once; outputs, counts and metadata kept; written only if unchanged on disk. Tried on a copy first: my line-length guard caught an existing over-long Setup line (the guard narrowed to added lines), then A8's comment at 121 characters ("A5, and A5b's reprices"). The copy's diff read, then the real file written; it equals the checked copy. Valid; every `tp.<name>` exists; the A-cells read A1, A2, A3, A3b, A4, A5, A5b, A7, A8 | — | notebook |
| 08:31–08:33 | Docs: the master pipeline README (a "run top to bottom" block quoting the owner, the A5b and A7 rows, two A6 mentions), the daily pipeline README (`grade --stage0`), `predictions/README.md` (A5b) | — | docs |
| 08:32 | **A7 dry run on the real runs:** 17 of 18 runs due, 203 results, read from the 25 Oct 09:21 run's own Stage 0 (the freshest); that run itself waits (its own copy predates its matches). It took over 2 minutes while the test suite ran beside it; its parts time at under a second each alone | the due list | — |
| 08:31–08:39 | `test/master_pipeline/` on the changed code, without the owner's saved-outputs notebook test (as in Parts 14–18): **145 passed** (140 before + 5 new), **1 failed**: `test_health_signals.py::test_the_acknowledged_flags_are_real_canary_flags`, also alone (0.07 s). The active acknowledgment `sackmann_tennis_atp:ARCHIVE` is no longer among the canary's flags (Monday's canary, 26 Oct 08:07, gives that source only `GONE`). Not this change's (`src/ingest/health.py` untouched since 22 Oct); reported to -ad, whose step-1 work it is (message `33180359…`) | — | — |
| 08:35–08:37 | **The kernel check** (scratchpad `make_p19_kernel_check.py`, `run_p19_kernel.py`): the notebook's own SETUP, A3, A3b, A4, A5, A7 and A8 in a kernel on the tennis interpreter, after a stand-in for A2 (three listed matches, all left out) in a kernel holding another day's `MATCHUPS` and `RUN`; A8 not writing. A3 "Nothing to predict now…", A3b and A4 skip, A5 shows nothing, **A7 graded 17 runs (203 results) and left the 25 Oct run waiting**, A8 showed its summary; after the pass `MATCHUPS` and `RUN` were None. Seen: A3 also displayed an empty table (`check_matchups`' empty frame) | — | the real runs' `graded.csv`, `grade.json` |
| 08:40 | **A7 against A8 on the real runs** (scratchpad `p19_cross_check.py`, A8 rebuilt on the same Stage 0): A7 graded 203, A8 holds 207 results (4 by its players-and-event fallback, as P19.2 foresaw), none only in A7; **the same result on all 203** both hold | — | — |
| 08:41 | **A second A7 pass with nothing new took 85 s**, so the dry run's slowness had not been the test suite. cProfile: `Series.isin` of each run's ~20 ids against the set of 870k ids, about 4.5 s a run (pandas' pyarrow strings turn the set into a list at each call). Now one set lookup per id: **1.0 s**. And `check_matchups(None)` returns None (no empty table in A3), its test with it; -ad told first (message `2889865e…`) | the profile | code |
| 08:42 | -ad on the canary test: not theirs either (Part 10, session f471b5ba), and they will not acknowledge it away: the canary of 26 Oct reports Sackmann's ATP, WTA and Slam point-by-point repositories GONE and Tennis My Life's manifest SHRANK and REVISED, a data-continuity alarm they are putting to the owner | — | — |
| 08:43 | The integrity plan's step-3 cell: A7's grading, its checks, what remains | — | docs |
| 08:41–08:47 | **The kernel check again** on the final code: the whole pass in 6 s; A3 shows only its line now; **A7 "Nothing new to grade … 17 up to date, 1 waiting"**; A8 its summary; `MATCHUPS` and `RUN` None after. **`test/master_pipeline/`: 145 passed, the same canary test failed** (not this change's), 1 deselected (the owner's saved-outputs notebook test) | — | — |
| 14:00 | **The canary test, settled.** -e4's message: the test was theirs (Part 10, step 1; their entry "a fault of mine fixed"), now fixed in the test file only: it checks that each acknowledgment names a watched item and one of the canary's flag words, no longer that the flag is still raised; no data or acknowledgment changed. Re-run here: `test_health_signals.py` **7 passed**. So the 08:31–08:39 row has the cause right and the owner wrong (-ad's, it said; -ad at 08:42: not theirs). My report to the owner had also called the failure the data-continuity alarm of 08:42: wrong. That alarm is separate and stays open (Tennis My Life's manifest SHRANK and REVISED; -ad's report to the owner). Corrected to the owner in this session's reply | the test's 7 results | — |

## P19.7 The first grading (27 Oct, results as the 25 Oct 09:21 run downloaded them)

17 of 18 live runs graded, 203 predictions (the 25 Oct run waits for its matches). Log loss, lower is better; Pinnacle's
price with its margin removed, the price each run was fed:

| Run | Matches | With results | Model | Pinnacle |
|---|---|---|---|---|
| Sun 11 Oct 11:01 | 8 | 8 | 0.992 | 0.946 |
| Tue 13 Oct 16:39 | 4 | 4 | 0.548 | 0.533 |
| Tue 13 Oct 16:53 | 1 | 1 | 0.399 | 0.413 |
| Wed 14 Oct 15:12 | 2 | 2 | 0.542 | 0.542 |
| Wed 14 Oct 15:31 | 2 | 2 | 0.476 | 0.511 |
| Wed 14 Oct 16:42 | 2 | 2 | 0.475 | 0.509 |
| Sun 18 Oct 13:59 | 16 | 15 | 0.647 | 0.646 |
| Mon 19 Oct 07:57 | 27 | 25 | 0.646 | 0.641 |
| Mon 19 Oct 17:32 | 38 | 36 | 0.660 | 0.665 |
| Tue 20 Oct 08:15 | 23 | 22 | 0.565 | 0.571 |
| Tue 20 Oct 09:00 | 22 | 21 | 0.557 | 0.563 |
| Wed 21 Oct 18:49 | 25 | 23 | 0.512 | 0.516 |
| Wed 21 Oct 20:36 | 23 | 21 | 0.516 | 0.518 |
| Fri 23 Oct 11:59 | 27 | 6 | 0.689 | 0.696 |
| Sat 24 Oct 07:42 | 13 | 7 | 0.718 | 0.691 |
| Sat 24 Oct 19:50 | 22 | 4 | 0.537 | 0.534 |
| Sat 24 Oct 21:25 | 19 | 4 | 0.537 | 0.534 |

Not pooled here: a match predicted in several runs counts once in each. A8 reads each match once; neither decides
anything (principle 8; the adoption framework's resolution).

## P19.8 Claims and their evidence

| Claim | Evidence | Kind |
|---|---|---|
| The bet-day cells pass a day with nothing to predict, and a kernel left open since another day predicts nothing old | the kernel check (twice); `test_a_day_with_nothing_to_predict_passes_the_cells` | observed, tested |
| A7 grades a run only when more of its results are on disk, and never the run just made | tests with exact call lists from literal statuses; the real first pass (the 25 Oct run waited) and second ("nothing new") | tested, observed |
| The engine reads the Stage 0 it is given | the end-to-end test, log losses worked by hand; `grade.json`'s `stage0` on the 17 runs | tested, observed |
| A7's results equal A8's | 203 of 203; A8's 4 more come from its fallback by players and event | observed |
| A7 costs about a second with nothing new | 1.0 s timed after the fix (85 s before it) | observed |
| The rename holds wherever a name is followed as an instruction | the notebook's cells, `bet_sheet.py`'s texts, the READMEs; the decision records and earlier Parts keep "A6" as of their day | observed (grep) |
| Nothing else changed in a run's predictions or sheet | the engine's change is in `step_grade` only (default unchanged); the layer's predicting paths gained only a None check before their first line of work | by construction |

## P19.9 Threats to validity, and where a flaw would hide

* **A7 joins by match id only** (the engine's rule). A8's fallback finds 4 more of 207 (an event built from its
  previous edition, a women's id that differs). Those never enter a run's `graded.csv`.
* **"Due" counts results, not their content.** A result corrected later with the same count is not regraded;
  `tp.grade(run, stage0=...)` does it by hand.
* **The freshest Stage 0 is chosen by file time.** A Stage 0 touched without being rebuilt would win.
* **Grading adds `code_used/grade_<pid>.json` to each graded run.** Harmless today: only the predict step merges those
  files, at its own time, and a reprice already adds one the same way. Step 2's receipt check, still to build, must
  read the predict step's provenance, not the folder (-ad told).
* **A5b with no run in the kernel reprices the newest run,** which may have been made on an earlier day. Its inputs
  are then a day old; the cell says a new day needs A1 to A5.
* **A3 now clears `RUN`.** A5b after A3 alone falls back to the newest run, which is the same run.
* **A match that would stop the run still stops a run-through at A3** (`check_matchups`' error, with the fix to make).
  Rare since A2's linking leaves such matches out; not changed (P19.3).

## P19.10 What a re-design would do

* Grade on a schedule (the 07:30 task), not with the notebook, and read the grades per match with the strength-of-lean
  alarm (principle 8): the integrity plan's step 3, still to build.
* Give the engine's grade A8's results join (the fallback by players and event), so one rule decides both.
* One call for the whole pass (`tp.bet_day()`), so no cell needs to be chosen at all. Not built: the owner asked for
  the cells, run in order.

## P19.11 Reviewer checklist

* **`predict.grade_due`:** due when `n > before`; results counted as `closing_line.DONE` counts them (completed,
  retired); the engine's output silenced only around a successful step (a failure raises with the log's tail); the
  set lookup per id (P19.6, 08:41).
* **`dp_steps.step_grade`:** the `stage0` argument, the Stage 0 deduplicated by match id, `grade.json`'s `stage0` and
  `stage0_written`; `dp.py grade --stage0` resolved against the repository like `--run`.
* **The None paths:** `build_matchups`, `check_matchups`, `data_check` and `predict_day` return before any check, read
  or paid call.
* **The notebook:** Setup defines `RUN` and `MATCHUPS`; A3 clears both; A5b falls back to the newest run; A7 calls
  `grade_due`; the saved outputs untouched.

## P19.12 Reproduction

```
./python.sh -m pytest -q test/master_pipeline/test_grade_due.py
./python.sh -m pytest -q test/master_pipeline/ --deselect test/master_pipeline/test_master_pipeline.py::test_notebook_is_clean_and_calls_only_existing_functions
./python.sh <scratchpad>/edit_notebook_p19.py <notebook>                  # refuses unless each old text occurs once
./python.sh <scratchpad>/make_p19_kernel_check.py scripts/master_pipeline.ipynb <scratchpad>/p19_check.ipynb
./python.sh <scratchpad>/run_p19_kernel.py <scratchpad>/p19_check.ipynb <scratchpad>/p19_check_out.ipynb
./python.sh <scratchpad>/p19_cross_check.py                               # after A7 has graded
```
Scratchpad: `C:/Users/zerom/AppData/Local/Temp/claude/c--Users-zerom-Documents-Tennis-predictions/37a84738-65ac-4624-b38a-fbe769e0e53e/scratchpad/`
(the notebook before this Part: `nb_before_p19.ipynb`; the probe of P19.2: `grade_probe/`). Nothing deleted. The
owner's kernel needs one restart (this Part's code and -ad's date fix).

# Part 20 (27 Oct 2026, from about 13:50 PDT): the three failing canary tests, fixed in the tests

Session `1ef1b0d0-468f-4a15-bd88-58e5dc5f3a37` (tennis-predictions-d8).

## P20.1 The owner's request, verbatim

> "These are three tests of the daily task's data health check. They have been broken since 22 October, when another
> session moved that check's rules into a new file without updating the tests. I left them alone."
>
> Identify this issue, review your thoughts with a reviewer and fix it.

The quoted lines are the serve-speed acquisition session's report (its process log, the 27 Oct 08:17 row).

## P20.2 What the files showed, before any change (read-only, to 14:00)

* **The three:** `test/data_continuity/test_rebuild_and_schedule.py::test_canary_flags_compare_first_word` and
  `::test_offline_canary_raises_nothing`; `test/master_pipeline/test_health_signals.py::test_the_acknowledged_flags_are_real_canary_flags`.
  The eight test files that import the scheduled task: 139 passed, these 3 failed. Part 16 (25 Oct, 00:08) logged the
  first two as "a test-isolation fault", Part 19 (today, 08:39) the third; none was fixed.
* **The first two broke with Part 10's move (22 Oct, 16:40–17:45).** In the committed code (`9228b26`, 22 Oct 12:09)
  `scheduled.canary_flags()` read `scheduled.CANARY_LATEST`, which both tests redirect; both pass on that code
  (`git archive HEAD` into the scratchpad: 2 passed). Since the move it calls `health.canary_flags()`, which reads
  `health.CANARY_LATEST` (a second constant naming the same file), and `job_canary` also reads `health.CANARY_KNOWN`
  (the acknowledgments). Neither is redirected, so both tests read the real files; their assertions show
  `tml_manifest:REVISED` and `SHRANK`. `scheduled.canary_offline()` still reads `scheduled.CANARY_LATEST`, so the second
  test's offline half passed. Neither test writes a real file (`child` is replaced).
* **The third is a different fault: not the move, and broken since 26 Oct.** Written with `health.py` on 22 Oct, it
  compares the acknowledgments with the latest canary run only. `sackmann_tennis_atp:ARCHIVE` is the first word of
  "ARCHIVE UNKNOWN (Software Heritage did not answer: ConnectTimeout)". Of the canary's four runs (6, 12, 19, 26 Oct)
  only 19 Oct's has it, and that run was the latest when the acknowledgments were written (22 Oct, 16:20), so the test
  passed then. Monday's run (26 Oct, 08:02) lacks it. All 7 acknowledgments are in some run.
* **An acknowledgment of an absent flag is valid by design:** `health.canary_split` reads only the flags present, and
  the acknowledgment file's own text says an acknowledged flag "does not alert while its date lasts". For a flag that
  comes and goes, the acknowledgment is what stops an alert each time it returns.
* **What an edit would disturb:** `src/pipeline/overview.py` (STATUS) imports `health.py`, so an edit to it stops the
  owner's kernel (Part 11's guard). `scheduled.py` runs only as a child process; another session added a job to it
  today, 08:13–08:17.

## P20.3 Interpretation acted on

* "Fix it": the three tests pass by testing what their names and docstrings claim, read no real file they should not,
  and nothing the scheduled task or STATUS does changes.
* **The data is right; the tests are wrong.** No acknowledgment is added or removed; the open `tml_manifest` flags stay
  open (-ad is putting that alarm to the owner, Part 19, 08:42).
* **Set aside, pending the reviewer:** removing `scheduled.CANARY_LATEST` so one constant serves both readings (a
  change to the live scheduled task); checking acknowledgments against a list of the canary's flag words (none exists in
  code; its docstring's list lacks ARCHIVE).

## P20.4 Plan, with the check for each step

1. **A reviewer**, read-only (a Plan agent, which cannot edit; brief verbatim in [subagent_briefs.md](subagent_briefs.md),
   "Part 20"). Check: each finding answered here.
2. **The tests.** First: redirect `health.CANARY_LATEST`. Second: redirect `scheduled.CANARY_LATEST`,
   `health.CANARY_LATEST` and `health.CANARY_KNOWN`. Third: every run in `canary.jsonl`, not the latest only. Check: the
   three pass; so do the eight files of P20.2.
3. **Mutation checks in a scratch copy:** each test fails when the rule it guards is broken, and the old third test
   fails where the new one passes.
4. **The reviewer reads the final diff.**

## P20.5 Files claimed (from 14:00 PDT; message `faed012c…` to -ad)

`test/data_continuity/test_rebuild_and_schedule.py`, `test/master_pipeline/test_health_signals.py`, this Part, a
section of `subagent_briefs.md`. No file under `src/` or `data/`.

## P20.6 Chronology

| When | Step | Results seen by then | Output |
|---|---|---|---|
| about 13:50–14:00 | Read-only: the tests run; the code, the canary's four runs, the committed code run in the scratchpad; Parts 10, 16 and 19, the serve-speed log; ListAgents | the facts of P20.2 | — |
| 14:00–14:05 | Reviewer launched; claim sent to -ad; this Part opened | P20.2 | log |
| 14:03–14:05 | **The third test had been rewritten by e4** (-ad's message; e4's own message). The file's time on disk is 13:59:27, after this session's first run of it (about 13:57, the old assertion failing); e4 dates the change "about 09:00 PDT" in Part 10. Its check: each acknowledgment's item is one the canary watches (`canary.WATCH`), and its word one of the canary's first words (a set written in the test, ARCHIVE included), with two typo cases that must fail; it passes, here and in the scratch mirror (copied after 13:59). **Kept as it is**; the history check of P20.4 dropped. The reviewer told to review e4's version instead; the claim on `test_health_signals.py` dropped | the mirror's run | messages |
| 14:05–14:07 | **e4: the first two are its regression from Part 10** ("I never ran test/data_continuity"), recorded by e4 in Part 10. e4 confirms the cause and the fix, will not touch `test/data_continuity/`, `test_health_signals.py` or `health.py`, and keeps `scheduled.CANARY_LATEST` (`canary_offline` and the job still read it). -ad: not editing either test file. **This Part's edit is now `test_rebuild_and_schedule.py` only** | — | — |
| 14:09 | **The reviewer's report** (about 9 minutes; it ran e4's version of the third test, 7 of 7). The diagnosis right for the first two; e4's third test sound, nothing justifies replacing it; tests only, the right scope; no CLAUDE.md rule broken. **Two corrections:** (1) test 1's failure showed all 8 real flags of the latest run, not only `tml_manifest:REVISED` and `SHRANK` (P20.2): test 1 does not go through `canary_split`; test 2's showed those two. (2) Part 19's 08:42 row is -ad declining to acknowledge away the data alarm (the open `tml_manifest` flags), not about the ARCHIVE acknowledgment, as my brief implied; the third test's own history is e4's Part 10 entry ("a fault of mine fixed") and d1's Part 19 row of 14:00. **Two suggestions, adopted (agent's choices):** test 2 gives `job_canary` an acknowledgment file holding b:GONE and a flag seen at the last run (x:GONE), so it covers the acknowledgment rule the 22 Oct change added, untested at the job level (the reviewer's mutation "acknowledgments ignored" passed the planned test); and an assert that the two names of the latest run are one file, since pointing both at one temporary file would hide a drift between them. **Also:** alternative (a) in `scheduled.py` alone would not trip the kernel guard (only `health.py` would); e4's check accepts impossible pairs (`tml_manifest:UNARCHIVED`; low stakes: a misplaced acknowledgment leaves the real flag open); the ATP repository's last full Software Heritage snapshot (8 May 2026) passes 180 days on 5 Nov, so **the canary of Mon 9 Nov will raise `sackmann_tennis_atp:UNARCHIVED`, not acknowledged: one "new flag" alert** | — | — |
| 14:12 | The file unchanged since 22 Oct 13:22 (LF; its uncommitted 22 Oct edits elsewhere, untouched); a copy kept (scratchpad `test_rebuild_and_schedule.before.py`). Edited: `from src.ingest import health as H`; a helper `canary_files()` (the assert, then the three paths to the test's files); test 1 through it; test 2 through it, its second half with flags a, b and x and the acknowledgment of b | the review | code |
| 14:13 | **The three pass. 158 passed:** `test/data_continuity/` and the 7 other files that import the scheduled task, `test_health_signals.py` among them. New lines within 117 characters | — | — |
| 14:13–14:14 | **Mutation checks** (scratchpad `mutation_check.py`, in a mirror, never the repository; validated first on the unfixed tests, where it flagged both failures and their reading of the real files): **11 of 11 as expected.** First-word rule broken: test 1 fails. Offline rule broken, never alerting, acknowledgments ignored, a flag of the last run alerted again: test 2 fails. Health's path moved: tests 1 and 2 fail on the assert. The tests' own flags planted in the "real" acknowledgments or latest run: tests 1 and 2 still pass. A typo'd item or word in the real acknowledgments: the third fails | — | — |
| 14:15 | The final diff sent to the reviewer | — | — |
| 14:16 | **The reviewer: no defect** (the 22 Oct edits untouched; the second half traced by hand; the assert runs before any patch, so it compares the real paths). Two optional gaps: the job's saving of this run's flags is unchecked (deleting `state["canary_flags"] = sorted(flags)` passed all three; in production every open flag would alert again each Monday); the lapsed-acknowledgment alert has no job-level test. **The first closed** (one clause: `state["canary_flags"]` holds a, b and x); the second left (P20.9) | the diff, the checks | — |
| 14:17 | 158 passed again; **mutation checks 12 of 12** (the new case, the state not saved: test 2 fails) | — | code |
| 14:20 | **e4's reply.** The reviewer's docstring note fixed by e4 at 14:16:41 (the file's docstring now says one test reads the real acknowledgment file): **checked here, the only change** against the 13:59 copy in the mirror; `test_health_signals.py` and `test/data_continuity/`, 47 passed. The per-kind word check declined by e4: it would copy `canary.flags`' rules for each kind of item into a test that must follow every change to the canary; agreed. The 9 Nov flag left to the owner; e4 would also recommend acknowledging it now, like its WTA and Slam twins (the repository is gone; the copy held locally is newer) | — | — |
| 28 Oct, about 09:00 | **The canary changed under these tests** (-ad, Part 22: SHRANK compares the matches in the project's copies of both versions where it holds them, the size rule otherwise; the first word unchanged, so the third test's word list holds; one live run at 15:54 UTC: no SHRANK, REVISED on 26 files, TERMS on `tml_readme_terms` and `tml_site_terms`). **Re-run here: `test_rebuild_and_schedule.py` and `test_health_signals.py`, 31 passed**; -ad's run of `test/data_continuity/` with `test_health_signals.py`, 49 passed (two new tests of -ad's). e4 claims `health.py` today (Part 10): told that the two tests name `health.CANARY_LATEST` and `CANARY_KNOWN`, and that e4 may update them if it renames either. **Seen in the canary's code (`previous()`, each item's last record in `canary.jsonl`):** a run by hand is the next scheduled run's baseline, so the TERMS flags of -ad's run (Tennis My Life's new non-commercial terms) never reach the scheduled job's "new flag" alerts; STATUS shows them until Monday's run. Told to -ad, for its report to the owner | -ad's report; the re-run | — |

## P20.7 Claims and their evidence

| Claim | Evidence | Kind |
|---|---|---|
| The first two broke with Part 10's move on 22 Oct; they redirected a path the moved rule no longer reads | both pass on the committed code (`git archive HEAD`); since, their assertions held the real flags; e4's own account (Part 10) | observed |
| The third broke on 26 Oct, not 22 Oct: an acknowledged flag that comes and goes was absent from the latest run | `canary.jsonl`: ARCHIVE in the 19 Oct run only; the acknowledgments written 22 Oct 16:20; all 7 in some run | observed |
| The acknowledgments and the data are right; only the tests were wrong | `canary_split` reads only the flags present; the acknowledgment file's own rule; nothing in `data/` or `src/` changed | by construction |
| The three pass and read no real canary file | 3 passed; 158 passed in the related files; the isolation cases (the tests' own flags planted in the real files change nothing) | tested |
| Each test fails when the rule it guards breaks | 12 of 12 mutation cases, in a mirror | tested |
| Nothing live changed; the owner's kernel is untouched | only `test/data_continuity/test_rebuild_and_schedule.py` edited (and this log) | by construction |

## P20.8 Threats to validity, and where a flaw would hide

* **The mutations are the ones thought of.** The lapsed-acknowledgment alert is still untested at the job level; a
  fault there would pass.
* **The third test (e4's) reads the real acknowledgment file** and allows any watched item with any flag word, so a
  misplaced acknowledgment (`tml_manifest:UNARCHIVED`) passes. Low stakes: the real flag stays open and alerts.
* **The assert pins today's design** (two names for one file). A deliberate move of the canary's file must change both
  names, or the canary tests fail; that is the intent.

## P20.9 What a re-design would do

* One name for the canary's latest run (`canary_offline` reading `health.CANARY_LATEST`; `scheduled.py` only, no kernel
  restart). Not done: a change to the live task for no behaviour change, and e4 keeps the name; the assert now guards
  the drift.
* A job-level test of the lapsed-acknowledgment alert (said once, then not again while the flag stays).
* After moving code out of a module, run every test folder that imports it (e4's lesson, Part 10).

## P20.10 Reviewer checklist

* `canary_files()`: the assert before any patch; all three paths redirected.
* Test 2's second half: a new (alerts), b acknowledged (no alert), x of the last run (no alert); one alert; the state
  holds all three.
* e4's third test untouched; `canary_acknowledged.json` and the open `tml_manifest` flags untouched.

## P20.11 Reproduction

```
./python.sh -m pytest -q -p no:cacheprovider test/data_continuity test/master_pipeline/test_health_signals.py
python -I <scratchpad>/mutation_check.py <repository> <scratchpad>/mirror      # the tennis interpreter; a mirror only
```
Scratchpad: `C:/Users/zerom/AppData/Local/Temp/claude/c--Users-zerom-Documents-Tennis-predictions/1ef1b0d0-468f-4a15-bd88-58e5dc5f3a37/scratchpad/`
(the file before the edit: `test_rebuild_and_schedule.before.py`; the diff: `canary_tests_fix.diff`; the mirror:
`mirror/`; the committed code: `head_before_move/`). Nothing deleted. No kernel restart needed.

**For the owner:** the canary of **Mon 9 Nov** will raise `sackmann_tennis_atp:UNARCHIVED` (the gone ATP repository's
last full Software Heritage snapshot, 8 May 2026, passes 180 days on 5 Nov), not acknowledged: one "new flag" alert.
Expected and harmless, like the WTA repository's acknowledged flag; e4 told.

# Part 21 (28 Oct 2026, from about 07:40 PDT): A3b stopped by Tennis My Life's re-spelled names; the override lookup made to survive a re-spelling

Session `80331616-a199-46aa-a9c2-9ce921cc7012` (tennis-predictions-73).

## P21.1 The owner's request, verbatim

> There's a bug in step A3b

with A3b's output pasted (the data check's Stage 0, `data_check_stage0`, 07:04:40, exit 1):

> box overrides: 6 of 2272 rows do not name exactly one row of their source (first: ['tml|wta|2026-905|R128|wang xinyu|arango emiliana', 'tml|wta|2026-905|R128|eva lys|gabriela knutson', 'tml|wta|2026-905|R64|anna kalinskaya|wang xinyu']); rebuild data/studies/data_continuity/slam_box_overrides.csv from the current staged files

and, while this session was reading: "fix it once you understand it".

## P21.2 What the files showed, before any change (read-only, to about 08:25)

* **The cause: Tennis My Life re-spelled three players' names** (scratchpad `probe_overrides.py`: today's staged files
  loaded and normalised as `stage0_build` does, the override check repeated). The six rows, each finding 0 rows: WTA
  US Open R128 and R64 and Wimbledon R128 and R64, "Xinyu Wang" now "Xin Yu Wang" (key `wang xinyu` -> `wang xin yu`);
  US Open R128, "Gabriela Knutson" now "Gabriela Andrea Knutson"; ATP Wimbledon R128, "Alexander Shevchenko" now
  "Aleksandr Shevchenko". Same TML ids (216133, 213873, S0H2), same events, rounds, opponents and scores. ATP `2026.csv`
  downloaded 26 Oct 07:30 (TML's 26 Oct 06:12 GMT), WTA `2026_wta.csv` 27 Oct 07:30. The table is unchanged since 9 Oct.
* **The download gate cannot catch it:** it holds a file in which rows are gone; a re-spelling removes none.
* **The builder's advice would lose data:** `data_continuity/slam_overrides.py` writes the Wimbledon and US Open rows
  only (731); the table holds 2,272, with 1,541 Roland-Garros rows appended on 9 Oct by `rg_first_serve_recount`.
* **Re-keying the table to the new spellings would break replays.** The live instance (`template_2026-10-21b`, built
  21 Oct) and every instance before 26 Oct were built on the old spellings; a replay builds on the instance's frozen
  Tennis My Life view but copies the repository's override table (`dp_worktree.setup` replaces only the correction
  tables). One table must serve both spellings.
* **Who else stops:** the bet-day run itself (its work tree builds Stage 0 with the same builder and table; the last
  live run was 25 Oct, so today is the first since), the scheduled coverage job (`scheduled.job_coverage`) and any
  template build or held check on today's files.
* **What an edit would disturb:** `stage0_build.py` is imported by the owner's kernel (`readiness._key`), so an edit
  stops the next cell until a restart (Part 11). It carries another session's uncommitted edits of 24 Oct 20:33
  (26 insertions, 11 deletions: the TennisLive earlier rounds), kept untouched. No step is running
  (`data/studies/master_pipeline/running/` empty).
* **Separate, not this fault:** today's TML job held `2022_wta.csv`, `2023_wta.csv`, `2025_wta.csv` two runs in a row
  (the scheduled task's alert: review the held copies); the canary's open `tml_manifest` REVISED/SHRANK flags.

## P21.3 Interpretation acted on

* "Fix it": A3b and the bet-day run build Stage 0 on today's files, with the same box scores on the same matches as
  before the re-spelling, and a replay on an older frozen view builds exactly as before.
* **The lookup, not the table, changes:** an override whose name keys find no row takes the one row of its source,
  tour, event and round with the score the table recorded (`tml_score`), one player's key unchanged on the same side,
  and the other player's name a re-spelling of the recorded one (the last word of either name a word of the other).
  Anything else still stops: both names changed, a changed score or round, a dropped row, two candidates, two overrides
  on one row. **An agent's choice** (production integrity, principle 5): it changes no pick against the build before
  the re-spelling; it is shown to the owner in the reply.
* The stop message's advice corrected (re-key the named rows; `slam_overrides.py` rebuilds two events only).
* **Set aside:** re-keying the six rows (breaks replays); matching by TML's player ids (the table holds Stage 0 ids,
  and ATP TML ids map to them only after linking; TML also changes ids, 22 Oct); a fuzzy name score (harder to state).

## P21.4 Plan, with the check for each step

1. The new lookup run on today's files by monkeypatching, the repository untouched (scratchpad
   `run_patched_build.py`, `new_overrides_code.py`). Check: the build completes; the 6 found as re-spellings.
2. Compared with the data check's last good build (25 Oct 09:16, old spellings): every override's match present with
   the same box score. Check: 0 differences on the overridden matches.
3. The edit in `stage0_build.py` (this function and two helpers, docstrings), tests in
   `test/rg_first_serve_recount/test_overrides.py`. Check: the old and new tests pass.
4. A3b's own command, into the scratchpad. Check: exit 0, outputs equal to step 1's.

## P21.5 Files claimed (from about 08:30 PDT)

`src/eda/predictability_diagnostic/stage0_build.py` (the override lookup only), `test/rg_first_serve_recount/test_overrides.py`,
this Part. Nothing under `data/` changed. Message `846cd3ce…` to -ad. Later added: a dated note in
`docs/decisions/2026-10-06-slam-box-scores.md` (where it is implemented).

## P21.6 Chronology

| When | Step | Results seen by then | Output |
|---|---|---|---|
| about 07:40–08:25 | Read-only: A3b's log; the builder; the table, its builder and the Roland-Garros rows; today's staged files through the builder's own load (scratchpad `probe_overrides.py`); the download gate; the replay's work tree; the live instance; the tests; Parts 19–20; ListAgents | the facts of P21.2 | probe output |
| 08:28–08:31 | This Part opened; the claim sent to -ad | P21.2 | log, message |
| 08:28–08:31 | **Step 1** with the first version of the rule (one player's key unchanged on the same side, the other name a re-spelling): the full build on today's files with the lookup monkeypatched in (scratchpad `run_patched_build.py`, `new_overrides_code.py`; the repository's file untouched). Exit 0 in 79 s; 2,272 overrides applied, 6 found as re-spellings; every later step passed (the row corrections' own rule found 11 rows "by their match, their source having moved them", as before) | — | scratchpad `stage0_patched/` |
| about 08:33 | **Step 2** (scratchpad `compare_builds.py`), against the data check's build of 25 Oct 09:16 (the old spellings): the overridden matches 2,269 in both, 4,538 player rows, **0 with any box count different**; the 6, and 3 renamed with an unchanged key (case, hyphen), carry the table's counts exactly. Elsewhere: 156 new matches, 0 dropped; 17 matches with a box count changed, 16 of them Basel and Vienna Q1 (blank to full: Tennis My Life's numbers arrived) and 1 Davis Cup tie (Tennis My Life's revision); 13 players' names changed on common matches, all Tennis My Life's re-spellings | step 1 | compare output |
| about 08:34 | **-ad's reply:** not editing the claimed files. The batch re-spelled 19 players, not 3: 7 men (Shevchenko; de Jong, de Minaur, van de Zandschulp and Pucinelli de Almeida by case; Nuñez Vera, accent; Fares Zakaria) and 12 women (Begu, Ruse, Sherif, Burillo Escorihuela, Knutson, Bulgaru, Ma, Wang, Ku, Kessler, Romero Gormaz, Rakotomanga Rajaonah). Suggests a look at A2's linking and `earlier_rounds.same_player`. Only Wang, Knutson and Shevchenko change a key in the table's rows | — | message |
| about 08:36 | **The rule generalised before the repository edit:** each player's name the recorded one or a re-spelling of it, so both may have changed. Re-spellings accumulate; under the first rule, a later re-spelling of the other player (Kalinskaya, say) would stop the Kalinskaya–Wang row again. The same 6 rows today; winner and loser exchanged still fail (the names are checked per side). Results seen: steps 1–2 only; the final code checked end to end in step 4 | steps 1–2 | — |
| about 08:37 | **Step 3, the edit:** the module docstring; `respelled`, `respelled_rows`; in `apply_box_overrides` the lookup, the stop message (re-key the named rows; `slam_overrides.py` rebuilds two events only), the summary's `respelled` list, one log line; its docstring's stale "the decided table has no such column" corrected (the Roland-Garros rows carry it since 9 Oct). The other session's hunks (`add_live_rows`, `drop_replaced`) untouched | — | code |
| about 08:38 | 13 new tests (6 cases of `respelled`; a re-spelled winner, loser and both; a row found by its names not listed; a changed score, a player sharing only a first name, winner and loser exchanged, two candidates and one row named twice still stop): **22 passed**. The 8 other test files that import the builder: **217 passed** | — | tests |
| about 08:40 | -ad's pointer, for today's slate only: A2 linked "Alex De Minaur" (re-spelled by case only) to `atp:200282`, his usual id; no other re-spelled man among the 19 linked matches; women's round 1 is not built | — | — |
| about 08:41 | The decision's note (where it is implemented), marked as an agent's choice | — | doc |
| 08:34–08:36 | **Step 4: A3b's own command** (`stage0_build.py --out-dir`, the final code, from the repository): **exit 0** in 110 s; "6 found with a player's name re-spelled"; **every output equal to step 1's** (both parquet frames equal, the three CSVs byte for byte, the summary but for its build time: scratchpad `same_outputs.py`) | steps 1–3 | scratchpad `stage0_cli/` |
| 08:36 | Reply to -ad (`f4de2cc3…`); the 25 Oct build copied to the scratchpad (A3b's next run overwrites the cache) | — | message, copy |

## P21.7 Claims and their evidence

| Claim | Evidence | Kind |
|---|---|---|
| A3b stopped because Tennis My Life re-spelled three players whose names key 6 of the table's rows | the probe: the 6 overrides find 0 rows each; the rows under the new spellings carry the same ids, rounds, opponents and scores | observed |
| Re-keying the table would break replays of the instances built before 26 Oct, the live one among them | `dp_worktree.setup` copies the repository's override table and replaces only the correction tables; `template_2026-10-21b` built 21 Oct | read in code, not run |
| The new lookup finds exactly those 6 and changes no box score | step 1: 6 found; step 2: 0 box differences on the 2,269 overridden matches against the 25 Oct build; the 6 equal the table's counts | tested on today's files |
| A3b's command completes on today's files, and the bet-day run's Stage 0 with it (same builder, same table, copied into its work tree) | step 4: exit 0, outputs equal step 1's | tested (the work tree's build not run) |
| Builds on the old spellings, replays included, are unchanged | every override found by its names: the same row labels as before, the new search not entered; only the summary gains an empty `respelled` list | by construction |
| The stop still guards the wrong-match cases | the 7 behaviour tests | tested |
| Today's slate is clear of the other re-spellings at A2 | "Alex De Minaur" linked to `atp:200282`; no other re-spelled man among the 19 linked matches | observed, today only |

## P21.8 Threats to validity, and where a flaw would hide

* **A wrong match accepted** needs the recorded row gone and another row of the same round with the same score whose
  players share both family names with the recorded ones. Not seen; on real data the rule has met these 6 rows only.
* **A family name re-spelled** ("Kalinskaya" as "Kalinskaia") still stops the build. Re-keying that row would then stop
  replays on older views, which this rule would not bridge either.
* **The replay path was not run:** its safety rests on the construction argument above.
* **Other steps that match by name** (A2's linking in general, `earlier_rounds.same_player`, the odds joins at the
  next rebuild) were not checked against the 19 re-spellings, except A2 on today's slate.

## P21.9 What a re-design would do

* Carry Tennis My Life's own player ids in the table and accept a row found by ids or by names (Tennis My Life changes
  ids too, 22 Oct), which would also bridge a re-spelled family name.
* Replays take the instance's own copy of the override table, as they take the correction tables since 22 Oct.
* The download's change log flags a re-spelling (same id, new name) as its own class, so the owner sees it before a
  build stops.

## P21.10 Reviewer checklist

* With every override found by its names, `rows` holds the labels the old `.loc` lookup gave, in table order, and
  `respelled_rows` returns before reading a name.
* The search is entered only for a key with no row (a key with two rows still stops), needs the recorded score (not
  blank) and both sides' names to agree, takes one candidate only, and no row may be named twice.
* The other session's hunks in `add_live_rows` and `drop_replaced` are as before.
* The owner's kernel must restart before its next cell (Part 11's guard).

## P21.11 Reproduction

```
./python.sh -m pytest -q -p no:cacheprovider test/rg_first_serve_recount/test_overrides.py
./python.sh src/eda/predictability_diagnostic/stage0_build.py --out-dir <scratch>/stage0_cli
python <scratchpad>/compare_builds.py <scratchpad>/stage0_datacheck_2026-10-25 <scratch>/stage0_cli
python <scratchpad>/same_outputs.py <scratchpad>/stage0_patched <scratch>/stage0_cli
```
Scratchpad: `C:/Users/zerom/AppData/Local/Temp/claude/c--Users-zerom-Documents-Tennis-predictions/80331616-a199-46aa-a9c2-9ce921cc7012/scratchpad/`
(the probe, the patched build and its code, both builds, the 25 Oct baseline, the diff `stage0_build_after.diff`).
Nothing deleted. The comparison needs today's staged files; a later download moves it.

**For the owner:** restart the notebook's kernel, then run SETUP and A1 to A3b again (A3b rebuilds its Stage 0, about
2 minutes). Separate and still open: Tennis My Life's 2022, 2023 and 2025 women's files, held two runs in a row
(B2's held list).

# Part 22 (28 Oct 2026, from about 08:30 PDT): the data alarm counts matches; Jakub Mensik's second id merged

Session `dd93a4a6-3a6e-47c1-838e-3ebf11a5cb9d` (tennis-predictions-ad), continued after a context summary. Its earlier
work is Part 17, P17.12, where the Mensik duplicate was found.

## P22.1 The owner's request, verbatim

> fix the alarm and fix mensik

This answered the session's report of 27 Oct. The alarm: "Fix the alarm so it counts matches instead of bytes; the
download already records how many matches each revision removes ... say 'fix the alarm'". Mensik: "One row in the
table that merges duplicate ids fixes it: bet days pick it up at once, training at the next retrain ... Say 'fix
Mensik'."

## P22.2 What was known before any change

* **The alarm**, from the check of 27 Oct (chat only, and sent to -e4):
  * the canary run of 26 Oct raised SHRANK on 34 files. Each held the same rows before and after: the old copies had
    CRLF on every line, the new ones LF.
  * The line-ending allowance had been counted in `TML_HELD`, which the daily download had replaced on 22-23 Oct.
  * REVISED was Tennis My Life's corrections of 22-27 Oct (the download's `_changes.jsonl`). None removed a row from an
    old season.
* **Mensik**, from P17.12, re-checked on the shared Stage 0 at about 08:30:
  * `atp:210084` has 11 rows, all from Sackmann's archive `atp_matches_qual_chall_2023.csv`, Jan-May 2023;
    `atp:210150` has 291.
  * Same name, both CZE, both born Sep 2005 by their ages, no week with a match under both.
* **The finding that changed the plan** (about 08:35, reading `live.py`): A2's name check reads the shared Stage 0
  (`CFG.STAGE0`, built 21 Oct 06:48), not the run's.
  * A row in the alias table alone would reach A2 only at the shared tables' next rebuild (B6), and A2 would keep
    leaving Mensik out.
  * My report of 27 Oct ("bet days pick it up at once") had assumed otherwise.
* -73's override fix (Part 21) cleared Stage 0 builds on today's files at about 08:36.

## P22.3 Interpretation acted on, and the plan

1. **Mensik.**
   * Work:
     * the alias row;
     * A2's `_stage0_keys` applies the decided alias table (an agent's choice: with it, A2 and the run agree on one
       player; without it, the row reaches A2 only at B6);
     * the retrain register's entry, with a check script.
   * Check:
     * a Stage 0 build on today's files in a scratch folder: exit 0, one id;
     * A2 links him on the real shared tables.
2. **The alarm.** SHRANK by the matches of both versions, counted in the project's own copies.
   * Set aside:
     * the download's change log: it has no counts for the versions accepted after review, and it never records a
       version held back;
     * a count recorded at each run: it would need a run of history before it could compare.
   * Check: the recorded runs rebuilt with the new rule; tests.
3. **One live canary run**, so the 26 Oct flags are replaced by a reading of the new rule.

Claims were sent at about 08:40 to -e4, -d2, -73 and -d8. No reply overlapped. -e4 waited for `live.py`, released at
about 08:43 (the claimed files are in the messages).

## P22.4 Chronology (PDT)

| When | Step | Results seen by then | Output |
|---|---|---|---|
| about 08:30 | ListAgents. Mensik's ids re-checked; the alias code read: every row of the second id must carry the table's name key, and both ids must have rows | P22.2 | — |
| about 08:35 | A2's name check read: the shared Stage 0, built 21 Oct. The run's own check (`prediction_run/run.py`) reads the run's Stage 0 | — | plan step 1 widened |
| about 08:40 | Claims sent | — | messages |
| about 08:42 | `live.py`: `_stage0_keys` and a new `_id_aliases`. `id_aliases.csv`: the Mensik row, its CRLF line endings kept. Landed first because -73 had asked the owner to restart the kernel, so one restart covers both | — | code, table |
| about 08:43 | A2 on the real shared Stage 0: `('Jakub Mensik', 'atp:210150', 'stage0')`; Sinner unchanged. `live.py` released to -e4 | — | — |
| 08:43-08:45 | A Stage 0 build on today's files with the decided tables (`stage0_build.py --out-dir`, scratchpad `stage0_mensik/`): exit 0 in 84 s. "3 second ids mapped" (Mensik's 11 rows); 9 aliases written as the established id by the source itself | — | scratch build |
| about 08:44 | `src/eda/input_data_audit/verify_aliases.py` and 4 tests, all pass. On the shared tables it exits 1 (`atp:210084` present), as it should until B6 | — | code, tests |
| about 08:44 | Register entry `2026-10-28-mensik-id-alias`. `pending.py --show` lists both pending revisions; `--check` on the shared tables: both not in the tables, as expected before B6 | — | register |
| about 08:45 | `verify_aliases.py` on the scratch build: 12 of 12. Mensik is one id with 303 matches | the scratch build | — |
| about 08:46 | The engine read. A live run's work tree copies the repository's `data/studies` (the decided tables), so the row applies. A replay copies the instance's build-tree tables, unchanged. History before the checkpoint changed by the row is recomputed in full, as the live run of 25 Oct did for six families (states step 478 s) | — | — |
| about 08:46-08:51 | `test_id_aliases_link.py` (2 new), `test/input_data_audit/`, `test_master_pipeline.py`: 92 passed, 2 failed. (a) `test_linker_on_the_probe` asserted the Mensik ambiguity on the 9 Oct sample. Updated: his row passes the name check and is left out only as already played. (b) `test_notebook_is_clean...`: the owner's notebook was saved with the kernel guard's stop in a cell. That is the owner's open notebook, not touched | — | one test edited |
| about 08:52 | `canary.py`, first version: SHRANK by matches where both versions' copies are found by size | — | code |
| about 08:52 | The 26 Oct run rebuilt: 70 files smaller. 48 had both versions kept, 0 with fewer matches; 22 were not kept and within 2%. `2015_wta.csv` was still flagged: the version listed (528,277 bytes) was written 26 Oct 14:38 UTC, after that day's download, and replaced before the next. The byte rule took its allowance from the current, re-saved copy: the original flaw, on the fallback path | the first version | — |
| about 08:53 | Second version: with only the earlier version kept, its line endings are the allowance. The three recorded runs rebuilt: 26 Oct, the false SHRANK gone and REVISED 80 kept; 19 Oct unchanged; 12 Oct, 8 Challenger season files (2018-2025) with fewer matches (-3, -1, -1, -4, -7, -5, -127, -12), where the byte rule had flagged 1 | the second version | — |
| about 08:54 | 2 new canary tests. `test/data_continuity` and `test_health_signals.py`: 49 passed (47 before, -d8's count). (The times from 08:46 to 08:54 are reconstructed after the fact, fitted to the two times the commands printed: the scratch build's end, 08:45:04, and the canary run's start, 15:54:34 UTC.) | — | tests |
| 08:54-08:58 | **The live canary run** (15:54-15:58 UTC, against 26 Oct): 15 men's files smaller again, both versions kept for all 15, every match kept: no SHRANK (the old rule would have flagged all 15). REVISED: 26. **TERMS on both of Tennis My Life's statements:** the site's MIT statement replaced by non-commercial terms that name prediction models (the page's own `dateModified` 2026-10-28T15:40:06Z), and the README's lines rewritten in the same sense | the second version | `canary.jsonl`, `canary_latest.json` |
| about 08:59 | Copies of both terms pages with times and hashes (`data/studies/data_continuity/terms_receipts/`); data continuity README 4.8, a dated note | — | receipts, doc |
| about 09:20 | **A side effect of the hand run, pointed out by -d8 and confirmed in `scheduled.job_canary`.** The Monday job alerts on flags new against its own last run. Its canary compares with the last record in `canary.jsonl`, which is now this run. So Monday's run will not see the terms change and will send no alert for it. STATUS shows the TERMS flags until Monday's run rewrites `canary_latest.json`. This session's report is therefore the owner's only notice of the licence change, and it says so | — | report |
| 09:02-09:10 | Two decisions, two rows in their index, the data-continuity README's SHRANK line, the master pipeline README's name-check line | — | docs |
| 09:04-09:10 | `test/master_pipeline`, `prediction_run`, `data_continuity`, `input_data_audit`, `current_best_model`, `rg_first_serve_recount`: **407 passed**, 1 deselected (the owner's saved-outputs notebook test, which reads the notebook as saved with the kernel guard's stop). A repo-wide run (08:57-09:03) stopped at collection on 189 files with "import file mismatch": test modules of one name in two folders (`test_common.py` in `tour_pooling` and `ufc_ideas`), unrelated to this change | everything above | — |

## P22.5 Claims and their evidence

| Claim | Evidence | Kind |
|---|---|---|
| Mensik's two ids are one person | same name and key, CZE, birth Sep 2005 by both ids' ages, no shared week | observed |
| Every Stage 0 build now gives him one id | the scratch build on today's files: 11 rows mapped, one id with 303 matches; `verify_aliases.py` 12 of 12 | tested |
| A2 names him once now, before B6 | `_player` on the real shared tables: `atp:210150`; the 9 Oct sample's row passes the name check | tested |
| A live run applies the row, and a replay does not | `dp_worktree.setup` copies the repository's `data/studies`; a replay replaces the correction tables with the instance's build tree's | read in code, not run |
| The next retrain cannot start without it | the register's entry; `pending.py --check` on the shared tables fails on it | tested |
| The 26 Oct SHRANK was false, and the new rule clears it | the rebuilt run: 48 of 48 files with both copies kept every match; `2015_wta.csv` explained by its earlier copy's line endings | tested on the recorded runs |
| The new rule sees losses the byte rule missed | the 12 Oct run rebuilt: 8 Challenger files with fewer matches, against 1 flagged | tested on the recorded runs |

## P22.6 Threats to validity, and where a flaw would hide

* **Versions matched by byte size.** Two versions of one file with the same size are taken as one. A loss would hide
  only behind a version with fewer matches and exactly the listed size.
* **A held-back version may be a half-written file** (the download holds those). Its count would then raise SHRANK,
  which still points at something wrong with the version listed.
* **Files the project does not keep** are judged by size within 2%. A smaller loss there is unseen.
* **A2's alias map reads today's table.** A replay of A2 (none exists) would read today's table, not the instance's.
* **Mensik's live inputs gain 11 matches of early 2023** that the live instance's training rows count as another
  player's, until the next retrain. That is the register's kind of revision. Those 11 of his 303 matches are three and
  a half years old.

## P22.7 What a re-design would do

* The download records each version's match count (it pairs rows already). The alarm would read the counts, with no
  size matching.
* One identity table for every name check (A2, the run, TennisLive's spellings) and the builder: the alias table is
  that table now for ids, not for spellings.

## P22.8 Reviewer checklist

* `flags()` without `rows` or `crlf_then` behaves as before: the old test is unchanged and passes.
* `shrink_evidence()` looks only at files smaller in bytes, leaves out the ongoing files, and finds the qualifying
  subfolder's copies.
* The alias row's name key equals Stage 0's key, and both ids have rows in a build on today's files.
* `_stage0_keys` maps ids within the tour only.
* The owner's kernel restarts before its next cell (`live.py`; Part 11's guard).

## P22.9 Reproduction

```
./python.sh -m pytest -q test/data_continuity test/master_pipeline/test_health_signals.py test/input_data_audit test/master_pipeline/test_id_aliases_link.py
./python.sh src/eda/predictability_diagnostic/stage0_build.py --out-dir <scratch>/stage0_mensik
./python.sh src/eda/input_data_audit/verify_aliases.py --stage0 <scratch>/stage0_mensik
./python.sh src/eda/current_best_model/pending.py --check
./python.sh src/eda/data_continuity/canary.py
```

The recorded runs rebuilt: `canary.shrink_evidence(cur, old)`, then `canary.flags("tml_manifest", 10, checked_at, {**cur,
**evidence}, old)` over consecutive `tml_manifest` records of `canary.jsonl`. Scratchpad:
`C:/Users/zerom/AppData/Local/Temp/claude/c--Users-zerom-Documents-Tennis-predictions/dd93a4a6-3a6e-47c1-838e-3ebf11a5cb9d/scratchpad/`
(the scratch build `stage0_mensik/`). Nothing deleted.

# Part 23 (28 Oct 2026, from about 15:05 PDT): A4 stopped by two re-keyed players; a live match's id predicted as Stage 0 builds it

Session `30b2af43-833a-42bc-a224-4ad7b577420d` (tennis-predictions-24).

## P23.1 The owner's request, verbatim

> Fix this issue and diagnose why this happens and what is the best way to minimize the chance of it happening again

It came with the A4 cell and its traceback pasted. The check's line:
`check: live matches missing from Stage 0 or not built as expected: {'live_matches': 21, 'in_stage0': 19, 'missing':
['wta|2026-1023|R16|wta:214388|wta:259733', 'wta|2026-1023|R16|wta:221237|wta:270082'], 'not_as_expected': [], ...}`.
Later, while I worked:

> When you are finished, run step A4 and A5 for me.
> Disregard if its been past 60-70 minutes since the data refresh. Run it anyway

## P23.2 What the files showed, before any change (read-only, to about 15:20)

* **The stop.**
  * Run `live_2026-10-28_145820` (A4 at 14:58) stopped in the tables step, at `inject.py --step check`.
  * 2 of its 21 live matches were not in the sandbox's Stage 0 under the id expected. Both are Guangzhou round-of-16
    matches: Anna Bondar v Kaitlin Quevedo, and Maria Timofeeva v Xinran Sun.
  * The failure's cleanup removed the work tree.
* **The ids.**
  * The run's live rows (`live_rows.parquet`) carry the ids Tennis My Life writes at the event: Quevedo 269267, Sun
    335958.
  * The expected ids carry the established ones: wta:259733 and wta:270082.
* **Quevedo in the run's refresh Stage 0.**
  * Every row of hers carries player id wta:259733.
  * Her matches up to Sao Paulo (15 Sep) are named with 259733.
  * From Osaka (19 Oct) on, they are named with wta:269267: `wta|2026-405|R32|wta:222290|wta:269267` and
    `wta|2026-1023|R32|wta:213550|wta:269267`.
* **Sun in the run's refresh Stage 0.**
  * Her player id is wta:270082, from Sackmann's ITF and WTA 125 rows.
  * Her matches are named wta:266647 at Beijing (30 Sep) and wta:335958 at Guangzhou.
* **The cause in code.**
  * Stage 0 names a match by its players' ids as the source row resolves them (`stage0_build.resolve_ids`): the
    Sackmann id the crosswalk learned from linked matches, else the source's own id.
  * Only then does it map a second id to the established one: `repair_data.repair_tables` by exact name, then
    `apply_id_aliases`. Both keep the match id and the sides ("Original stable handles retained; canonical player IDs
    corrected separately").
  * The run predicts the live match's id from Stage 0's player ids, the established ones
    (`prediction_run/run.live_from_matchups`, lines 189-196). The two agree only while the source's id resolves to the
    established one.
  * An id Tennis My Life first used after Sackmann's files ended (June 2026) was learned from no link.
* **The same prediction in two more places.**
  * `earlier_rounds.played_rows` predicts the TennisLive fills' ids. A miss there is only reported: the fill's window
    is not pinned, and its gate block stays.
  * `run.tml_box_fills` looks up a published round by a rebuilt id. A miss treats the round as unpublished, so it
    does not get TennisLive's box score.
* **Side A is a hash of the match id** (`common.side_is_low`), so the predicted id also orients the price (p_a).
* **What reads the live match's players:** predictions.csv, the gate, the speed columns and the bet sheet's join.
  They take them from Stage 0's match rows (the established ids), not from the match id, so they are unaffected.
* **The alias table** (Part 22's route for Mensik) maps player ids only. It would not change these match ids.

## P23.3 Interpretation acted on

* **"Fix this issue":** the run predicts each live match's id, and each earlier round's, as Stage 0 builds it.
  * Today's 21 matches then pass the check.
  * Their inputs are those training will build once the source publishes the match: the same id and the same players.
  * Not chosen: making Stage 0 rename the match. That changes the decided builder, and provenance joins rely on its
    stable handles.
  * Not chosen: letting the check accept another id. The meta's id is the key of the prices, the frame, the fit and
    the bet sheet.
* **"minimize the chance":** one helper for the three places, a check whose message names the cause, and a regression
  test.
* **"Run it anyway":** run A4 and A5 with A3's matchups of 14:53 and their prices (quoted 21:52 UTC). No new A3, even
  past the hour.
* **Readings set aside.**
  * Writing the established id into the live row: the row would then differ from the one Tennis My Life will
    publish, and an ATP code cannot be written that way.
  * A second Stage 0 build in the matchups step, to learn the ids: about 80 s on every run.

## P23.4 Plan, with the check for each step

1. **`live_rows.id_handles`:** (tour, a player id as the source writes it) → the id Stage 0's match ids give it, read
   off the run's Stage 0 matches sourced from Tennis My Life.
   * Check: on the failed run's refresh Stage 0, today's 21 predicted ids. 19 unchanged; the 2 now carry 269267 and
     335958.
2. **Use it** in `live_from_matchups` and `played_rows`. `tml_box_fills` finds the match by the established pair instead.
   * Check: `test/prediction_run`, and a new regression test.
3. **The check's message** lists the live ids Stage 0 gave that were not expected.
   * Check: a test.
4. **A4 and A5.**
   * Check: the run passes the check and predicts 21 matches, and the bet sheet reads them back.

## P23.5 Files claimed (from about 15:20 PDT; message to -34, which replied: no overlap)

* Code: `src/eda/prediction_run/live_rows.py`, `run.py`, `earlier_rounds.py`, `inject.py`, and
  `src/eda/daily_prediction/dp_matchups.py`.
* A new test in `test/prediction_run/`, and this Part.
* The work tree and the GPU, for A4.

## P23.6 Chronology (PDT)

| When | Step | Results seen by then | Output |
|---|---|---|---|
| 15:05-15:20 | Diagnosis, read-only (P23.2) | the run's log, `steps.json`, `live_rows.parquet`, the refresh Stage 0 | — |
| about 15:20 | Claim to -34; it replied: no overlap | — | message |
| about 15:21 | This Part opened (P23.1-P23.6) | P23.2 | log |
| 15:22-15:26 | Code. `live_rows.id_handles` and `handle_of`. `run.live_from_matchups` names each live match with them. `earlier_rounds.played_rows` takes them (`handles`; without it, as before), and so do the run and the replay's `dp_matchups.replay_earlier`. `run.tml_box_fills` finds a published round by its event, round and the two players' Stage 0 ids. `inject.check`'s failure lists the live ids Stage 0 gave that the meta does not name | P23.2 | code |
| about 15:26 | `live_from_matchups` on the failed run's refresh Stage 0 and A3's CSV, into the scratchpad (`live_check/`, 23 s). 19 ids unchanged; 2 changed, to `wta\|2026-1023\|R16\|wta:221237\|wta:335958` and `wta\|2026-1023\|R16\|wta:214388\|wta:269267`. Every p_a equal. The 12 earlier rounds' ids equal. The live rows equal byte for byte | the code | scratch meta |
| 15:26-15:28 | A Stage 0 build on today's files with those live rows (`stage0_build.py --out-dir --live-rows`, 80 s, exit 0). 21 of 21 meta ids in it, and no live id the meta does not name. 12 of 12 earlier-round ids. All completed, evaluation matches, no box score. In both matches side A is the re-keyed player under her established id (wta:270082, wta:259733), and p_a is her chance | the scratch meta | scratch build |
| about 15:27 | 5 tests (`test/prediction_run/test_match_id_handles.py`). `test/prediction_run`: 26 passed | — | tests |
| about 15:29 | Lines reflowed (formatting only). 26 passed again | — | — |
| 15:30:09 | **A4 started** (scratchpad `run_a4_a5.py`: `tp.predict_day` with tabpfn35, the failed run's model, and A3's matchups of 14:53; then `tp.bet_diagnostics` with stale_minutes 70 and the owner_8oct stake rule, the notebook's defaults). Run `live_2026-10-28_153009` | everything above | run |
| about 15:31 | STATUS read: the live model is template_2026-10-21b; A4 running; Tennis My Life's 2025 WTA file held since 22 Oct; event renumberings accepted this week. **A departure:** the rule says read STATUS before changing the live path; I read it after the edits, before the run | — | — |
| 15:31-15:33 | How common, on the failed run's refresh Stage 0 (read-only). 220 of 1,748,576 player rows sit in a match whose id names them with another id. Since 1 Jun 2026 that is 87 players (77 men, mostly Challenger players named by an ATP code the crosswalk never learned, though their rows carry Sackmann's id; 10 women). 15 of the 558 players with a match from 1 Oct. First named otherwise in Jun 11, Jul 19, Aug 11, Sep 36, Oct 10. At Osaka (19 Oct) Tennis My Life gave at least two women new ids: wta:259733 became 269267 and wta:223168 became 269265 | — | — |
| about 15:35 | `test/master_pipeline/test_earlier_rounds.py` (-73's or -ad's file of 24-25 Oct, untracked): 1 failed. Its synthetic Stage 0 lacked `tournament_id` and `round`, which every real Stage 0 has and the published-round lookup now reads. Those two columns added to its three rows (the test's assertions unchanged). With `test_qualifying.py` and `test/prediction_run`: 52 passed | — | one test edited |
| 15:39:06 | **A4's check passed** (`inject.json`): 21 of 21 live matches in the sandbox's Stage 0, none missing or not as expected; 12 of 12 earlier rounds in it, completed, with box scores | the run | the run's sandbox |
| about 15:38 | `test/current_best_model/test_level_layer_template.py`, `test/indoor_fill`: 28 passed (GPU-free; `test/daily_prediction` left until the run ends: it may fit TabPFN) | — | — |
| 15:53:48 | **A4 finished**: exit 0, 1,422 s (tables 565 s, states 547 s with 21 saved-state parts recomputed after data revisions, fit 90 s). 21 of 21 matches predicted with template_2026-10-21b; the gate allows all 21 | the run | run `live_2026-10-28_153009` |
| 15:53 | **A5**, made 15:53 on prices quoted 14:52 (61 min old): 10 bets, 11 passes, 0 blocked. 1 listed match not predicted: Altmaier, already out at Basel. The two repaired matches: Sun a bet at +174; Bondar v Quevedo a pass. Their predictions carry the established ids (wta:259733, wta:270082); the bet sheet's read-back of players and prices blocked neither | the run | `predictions/2026-10-29/bet_sheet_2026-10-28_1553.xlsx` |
| about 15:56 | The two matches' inputs. Bondar v Quevedo: none empty. Timofeeva v Sun: 2 empty, age and age squared (Tennis My Life's row for Sun at Guangzhou has no age). That is the most any match has: Osaka v Pohankova has the same 2 empty | the run | — |
| about 15:56 | `test/daily_prediction` started (it may fit TabPFN, so it waited for the run). The owner moved it to the background; it had not finished when this Part closed | — | — |
| 15:57-16:05 | **The owner, mid-turn:** "If you have the mens results please print them off please, while you fix a single row it shouldnt hold up the whole pipeline. Time matters here"; then "IF WHAT YOU ARE DOING IS NOT RELATED TO GETTING ME THE MENS PREDICTIONS , STOP FOCUSING ON IT FOR NOW AND GIVE ME THE PREDICTIONS!!!!"; then "ATTENTION!!!!". The men's predictions given from the sheet | the sheet | chat |
| after 16:00 | The owner: "did this include the calibration step?" Yes, read from `predictions.csv` and `provenance.json`: the 16 seeds' chance (`p_base_a`); then stage 2, set "grown", with s_atp 0.905, s_wta 0.933 and b̃ 0.038; then the five-pattern adjustment (on). The owner: "Note: these are not all the columns, theres columns you didnt tell me". All 14 of the sheet's columns given for the men's matches, notes included | the run | chat |
| about 16:08 | -b6's claim: women switched off in A1-A8, in `src/pipeline/` files, with its Part 24 after this one. No overlap; it was asked to append Part 24 after this Part closes | — | message |

## P23.7 Claims and their evidence

| Claim | Evidence | Kind |
|---|---|---|
| The stop was the run's id prediction, not missing data | the two live rows were in the build (`stage0_live_rows.rows` 21); Stage 0 names those players' matches with Tennis My Life's new ids (P23.2); the fixed prediction finds 21 of 21 in a build with the same live rows | observed, tested |
| The fix changes nothing else on today's matches | 19 of 21 ids and every p_a equal; the live rows byte-equal; the 12 earlier rounds' ids equal | tested on the failed run's own Stage 0 |
| The predicted ids are the ones Stage 0 builds | the scratch build with the live rows: 21 of 21, 12 of 12, no live id unexpected | tested |
| The price is oriented as Stage 0 orients the match | p_a follows the hash of Stage 0's id; side A in the build is Sun or Quevedo, and p_a is her chance (0.353, 0.447) | tested |
| These matches' inputs are the ones training will build once the result is published | the live row is Tennis My Life's own (unchanged), so the published row carries the same id and gets the same match id and the same player ids; every input reads the players' ids, never the match id's parts | read in code. Not run: a replay of a re-keyed player's played match (replays do not use the changed code) |
| It would have recurred | 87 players named otherwise since June, 15 of the 558 active from 1 Oct; at least 2 women re-keyed at Osaka | observed |
| The other sites had the same flaw | `played_rows` and `tml_box_fills` built the id the same way (read in code). The `played_rows` test shows the old id without the lookup (`...wta:259733...`). The `tml_box_fills` test was not run against the old code | read in code; tested in part |

## P23.8 Threats to validity, and where a flaw would hide

* **An id no Stage 0 match from a TML row carries** keeps the player's Stage 0 id. That happens when the id appears only
  in rows linked to Sackmann's, which the crosswalk maps to Sackmann's id, the Stage 0 id. It is wrong only if the
  crosswalk learned another id for it. The check then stops the run as before, and names Stage 0's id now.
* **A blank id** (a player whose rows are all Sackmann's or the feed's) keeps the Stage 0 id. Stage 0 resolves a blank
  by the unambiguous name; a name with two ids would resolve to a name-based id, and the run would stop as before.
* **Sides paired by name inside a match.** Two players with one name key in a match are skipped.
* **The lookup reads the refresh's Stage 0.** The sandbox's adds the live rows and the lower-level additions. Their
  crosswalk could differ only if a live row linked to a Sackmann row; Sackmann's files end in June 2026.
* **A source that re-keys a player between the bet and the result** gives the played match another id than the live
  one. Grading and the closing-line ledger find a result by its players when the id differs (`closing_line.results`).

## P23.9 What a re-design would do

* **The owner's words, mid-turn (28 Oct 2026, about 16:00): "while you fix a single row it shouldnt hold up the whole pipeline".** The check stops all 21 matches over one it cannot place. That is the next change, my recommendation and for the owner to decide. A live match the check cannot place would be left out with its reason, as the gate blocks a match, and the rest predicted. The meta, the prices and the earlier rounds would drop it together, before anything reads them.
* **Stop predicting the id.** The sandbox's Stage 0 knows each live row's match id, by its position (`source_file`
  "live_rows", `source_row`). The run would take those ids (meta, prices) before anything reads them: one construction
  of the key instead of two, so they cannot disagree.
* **Stage 0 writes its id resolution** (each source id's id in match names) beside its tables. The run would read it,
  and not infer it from the matches.
* **The source's re-keying on STATUS:** a line when a player's matches start to carry a new id. With the fix it no
  longer stops a run; it would say why a player's matches changed names.

## P23.10 Reviewer checklist

* `id_handles` pairs a match with its own staged row (source file and row) and the sides by name. It takes side A's id
  as `stage0_build` does: the lower id when `side_is_low` holds, else the higher.
* `handle_of` falls back to the player's Stage 0 id, the old behaviour, wherever nothing is known.
* `tml_box_fills` finds a match by event, round and the two Stage 0 ids. Qualifying has no round robins.
* `inject.check`'s new key appears only in a failure's message: a passing run's `inject.json` is unchanged.
* The owner's kernel must restart before its next cell (Part 11's guard): five files of `src/` changed.

## P23.11 Reproduction

```
./python.sh -m pytest -q test/prediction_run test/master_pipeline/test_earlier_rounds.py test/master_pipeline/test_qualifying.py
# the real-data check (scratchpad live_check/): run.live_from_matchups(<A3's CSV>, <failed run>/stage0, <scratch>, <sidecar>)
./python.sh src/eda/predictability_diagnostic/stage0_build.py --out-dir <scratch>/stage0_live_check --live-rows <scratch>/live_check/live_rows.parquet
```

Scratchpad: `C:/Users/zerom/AppData/Local/Temp/claude/c--Users-zerom-Documents-Tennis-predictions/30b2af43-833a-42bc-a224-4ad7b577420d/scratchpad/`
(`live_check/`, `stage0_live_check/`, `run_a4_a5.py` and its log). Nothing deleted.

## P23.12 Added at the close: the outcome

| Claim | Evidence | Kind |
|---|---|---|
| A4 passes with the fix, and predicts every match | run `live_2026-10-28_153009`: the check 21 of 21 and 12 of 12; 21 predicted; the gate allows 21; the sheet's read-backs blocked none | observed |
| `test/daily_prediction` with the fix | started after the run and moved to the background by the owner; not finished at the close, so no result is claimed | — |

# Part 24 (28 Oct 2026, from about 15:57 PDT): women's matches switched off for the bet day (A1–A8)

Session `286e9fb7-6414-4398-8d27-470c7f4cdc8d` (tennis-predictions-b6).

## P24.1 The owner's request, verbatim

> For the master_pipeline.ipynb steps A1-A8 temporarily disable womens matches
> We havent demonstrated they are profitable yet, im not betting on them, and their matches constantly cause errors
> because the pipeline isnt robust enough yet. It just slows everything down massively

(The owner's editor had the A4 cell selected.)

## P24.2 What the files showed, before any change (read-only, to about 16:05)

* **Where a match's tour matters on the bet day:**
  * **A2** (`live.todays_matches`) already takes `tours=("atp", "wta")`. A tour outside it is left out before any
    linking: no Tennis My Life event, Stage 0 name or TennisLive request.
  * **A3, A3b, A4 and A5b** work only on the matches A3 writes:
    * A3b's data check reads the matchups' own matches;
    * A4's engine (`dp.py run_day --refresh`) builds live rows for the matchups' matches. It fetches the WTA's calendar
      only for women's live seasons (`prediction_run/run.wta_calendar`).
  * **The engine's refresh** fills every recent box-score gap of both tours, whatever the matchups hold
    (`fills.fill_all`; women's from the WTA API). In the last 8 live runs it filled none: 0 fillable gaps
    (`refresh.json`). Its 85–115 s is the Stage 0 build.
  * **A5** (`diagnostics.bet_diagnostics`) reads the run's predictions, and A3's linking file for "Not predicted"
    (leagues "ATP ..." or "WTA ...").
  * **A7** (`predict.grade_due`) grades every live run. Each grade takes under a second (34 receipts, median 0.9 s),
    and none has failed.
  * **A8** (`closing_line.clv_ledger`) rebuilds the ledger from every sheet's record (local files only) and reads both
    tours together.
  * **A1** (`data.morning_refresh`) re-runs the shared download jobs (Tennis My Life, ATP speeds) when stale. No
    per-match work.
* **The model is trained on both tours.** The live instance's frame (`template_2026-10-21b`) holds 34,874 men's and
  32,657 women's rows, with `in_tour` an input. So women's downloads and builds must go on: a retrain reads them.
* **What women's matches cost:**
  * Today's 14:53 slate: 21 predictable, 12 of them women's (A3's linking file).
  * A4 at 14:58 stopped on two women's Guangzhou matches (Part 23): 420 s, then a second run.
  * Inside A4, the 7 women's IOS jobs of the states step take 66–150 s each, against the men's 250–400 s. With 14 jobs
    on 7 workers they add about 90 s to a full recompute (run `live_2026-10-28_153009`, `states.json`). The tables
    step builds both tours regardless.
  * A4 failures recorded through the notebook (`runs.jsonl`): 14 Oct ×3 (a Windows `rmdir`), 18 Oct (no message),
    28 Oct 14:58 (the women's Guangzhou rows). So 1 of 5. The rest of "constantly" is A2 and A3b trouble that is not
    recorded as a failed step (Parts 17–23).
* **Other sessions:**
  * -24 (Part 23, engine files) had finished. The owner's sheet of the 15:30 run
    (`predictions/2026-10-29/bet_sheet_2026-10-28_1553.xlsx`) keeps its 12 women's matches.
  * -15 (P7, the SofaScore ITF download) asked that its detached download and watchdog be left running.

## P24.3 Interpretation acted on

* **One switch, the owner's words:** `config.BET_TOURS = ("atp",)`. Setting it to `("atp", "wta")` switches women back
  on. Nothing on disk is deleted, so switching back brings back every step's women's output from the files.
* **How each step applies it (an agent's choice, production integrity principle 5):**
  * **A1:** unchanged. Its jobs are shared, and the model trains on both tours.
  * **A2:** women's matches are left out before linking, with the reason. The listing gives their count in one line
    instead of a row each.
  * **A3:** only men's matches are written, by construction. `check_matchups` refuses a women's row typed by hand (the
    fallback).
  * **A3b, A4:** men's matches only, by construction. The engine is unchanged.
  * **A5:** a run made before the switch keeps its women's predictions in its files. The sheet leaves them out, and its
    "Not predicted" tab leaves out the women's listed matches. Each is said once in the notes.
  * **A5b:** reprices only the run's men's matches.
  * **A7:** grades as before (the engine grades every prediction of a run: the record). The runs' figures shown are the
    men's matches'.
  * **A8:** the ledger file keeps every prediction. Its reading (the summary and the table) is the men's matches', with
    one line saying how many women's are left out.
  * **STATUS:** one line naming the switch.
* **No men's pick moves**, by construction: the engine and its inputs are unchanged, a men's match's inputs are built
  per player and tour, and TabPFN's test rows attend only to training rows.
* **Set aside:**
  * Skipping women's tables and states inside the engine: about 90 s of a full recompute, and an engine change that
    needs the replay proof.
  * Stopping women's downloads or builds: the model trains on both tours, so a retrain would read stale women's rows.
  * Editing the notebook: the owner has it open, and a change on disk can clash with its unsaved state. The switch
    lives in `config.py`, and STATUS shows it.
  * Removing women's predictions from the ledger file or the runs' grades: they are the record, and are needed again
    when women are switched back on.
  * The owner's "while you fix a single row it shouldnt hold up the whole pipeline" (Part 23, P23.9): a separate change,
    proposed there for the owner to decide.

## P24.4 Plan, with the check for each step

1. **Baseline:** `test/master_pipeline` before any edit. Check: after the change, the same results plus the new tests.
2. **The switch** in `config.py`. Check: the new tests.
3. **A2, A3 and A5b** in `live.py`. Check: a synthetic pull of one men's and one women's match (the woman left out with
   the reason, and no women's Stage 0 lookup); the existing linker tests.
4. **A5** in `diagnostics.py`. Check: a run with a women's prediction and a women's linking row.
5. **A7** in `predict.py`. Check: `test_grade_due` and a new test.
6. **A8** in `closing_line.py`. Check: `test_closing_line` and a new test.
7. **STATUS.** Check: `status()` prints the line.
8. **Real data, read only:** A2 on today's latest pull; A5 on the 15:30 run (`write=False`); A7 and A8 without
   writing. Check: no women's rows, and the men's rows equal to before.
9. **Docs:** the decision, its index row, CLAUDE.md, the master pipeline README.

## P24.5 Files claimed (from about 16:05 PDT; messages to -24 and -15, both replied: no overlap)

`src/pipeline/config.py`, `live.py`, `diagnostics.py`, `predict.py`, `closing_line.py`, `overview.py`;
`test/master_pipeline/test_women_switched_off.py` (new); `docs/decisions/2026-10-28-women-switched-off.md` (new),
`docs/decisions/README.md`, `CLAUDE.md`, `docs/studies/master_pipeline/README.md`; this Part.

## P24.6 Chronology (PDT)

| When | Step | Results seen by then | Output |
|---|---|---|---|
| 15:57–16:05 | Read-only: the notebook's A cells; the A functions of `src/pipeline/`; the engine's refresh and fills; 8 recent runs' `refresh.json` and `steps.json`; A3's linking files; the 15:30 run's `states.json`; the training frame's tours; `runs.jsonl`'s failures; Parts 21–23; ListAgents | the facts of P24.2 | — |
| about 16:05 | Claims sent to -24 and -15 | — | messages |
| 16:06–16:09 | -15: no overlap. -24: no overlap; the owner's A4/A5 done (sheet of 15:53, women kept); later, Part 23 complete | — | messages |
| about 16:08 | Baseline `test/master_pipeline` started (background) | — | — |
| 16:10 | This Part opened | P24.2 | log |
| 16:11–16:18 | **The code.** `config.py`: `BET_TOURS`, `tour_off`, `off_mask` (tour column, else the match id's first part), `off_names`, `bet_tours_line`. `live.py`: `todays_matches` takes `tours=None` (the switch), and a switched-off tour's listing gets the switch's reason first, before Pinnacle's own reasons, so every women's row says the same thing (ITF rows keep theirs); `show` counts those rows in one line; A3's two messages count them; `check_matchups` refuses a women's row; `live_prices` skips the run's women's matches. `diagnostics.py`, `predict.py`, `closing_line.py`, `overview.py` as P24.3 | — | code |
| 16:13 | **Baseline result:** 112 passed, then `-x` stopped at `test_notebook_is_clean_and_calls_only_existing_functions`. The owner's open notebook is saved with STATUS's output, the same failure Part 22 recorded and deselected. The modules were imported at collection (16:09), before the first edit (about 16:11) | — | scratchpad `baseline_tests.txt` |
| about 16:19 | Read `_priced_run`: the replay (15 men's, 8 women's matches) copied as `live_test_run`. **The A5 rule narrowed to live runs**, as the live-model check is (`_model_block`): a C8 replay's diagnostics keep both tours. Seen before any test result | the fixture's code | code |
| about 16:21 | `test_women_switched_off.py`, 15 tests: **15 passed** (4 s) | — | tests |
| about 16:21 | The two linker tests of the women's code (the 9 Oct probe with Wuhan; the 16 Oct qualifying with Ningbo and Osaka) pass `tours=("atp", "wta")` by name, before the suite was run: they test the code that links women once switched back on | the tests' assertions | tests |
| 16:22–16:27 | **The whole suite** (the notebook test deselected): **160 passed, 3 failed**, all three on `_priced_run` (`test_bet_sheet_says_what_the_record_says`, `test_the_bet_sheet_shows_both_models_and_decides_on_their_average`, `test_a_failed_thinking_call_gives_the_local_sheet_and_says_so`): the sheet now holds 15 rows against the run's 23 predictions. The intended behaviour on a live run; these tests check the sheet's figures, not the switch | — | scratchpad `after_tests.txt` |
| about 16:27 | **Fixed in the tests:** an autouse fixture in `test_master_pipeline.py` pins both tours (beside the module's existing autouse `replay_model_selected`, the same pattern); the probe test's explicit `tours=` reverted as redundant. `test_qualifying.py` keeps its explicit `tours=` | the 3 failures | tests |
| 16:23–16:26 | **Plan step 8, real files, read only** (scratchpad `real_data_check.py`; the engine's grade stood in by a recorder, since a dry run writes a receipt to `runs.jsonl`). **A2** on the 14:52 pull, TennisLive stood in: 22 women's listings all with the switch's reason; the 29 men's rows of A3's 14:53 file with the same status, the same 9 predictable. **A5** on the 15:30 run at the 15:53 sheet's time: 9 BLOCKED, every one "quote 61 min old (over 30)". My check used the function's default `stale_minutes` (30); the sheet was made with 70 (its provenance). Again with the sheet's parameters: 5 BET and 4 PASS, as the owner's sheet; compared as the record file holds them, **equal in all 80 columns on the 9 men's rows** (one text column first read differently: pandas' string type keeps a missing value missing, and `"nan"` ≠ missing; equal pair by pair). **A7:** every run's state the same either way; the 3 runs due show men's figures, 19 women's predictions left out; runs without women's predictions the same figures. **A8:** 211 of the ledger's 353 predictions read (111 of 196 matches) | steps 2–7 | console output |
| 16:26–16:30 | The decision and its index row; CLAUDE.md; the master pipeline README | step 8 | docs |
| 16:26–16:30 | `test_master_pipeline.py`, `test_qualifying.py`, the new file and `test/daily_prediction/test_stage2_sync.py` (the one test outside the folder that imports `src/pipeline`): **80 passed**, 1 deselected | the fix above | — |
| about 16:32 | Landing message to -24; claims released | — | message |
| 16:32–16:37 | **The whole suite once more** (`test/master_pipeline` and `test_stage2_sync.py`, the owner's saved-notebook test deselected): **170 passed**. The real STATUS prints "BET DAY (A1-A8): men's matches; women's switched off since 28 Oct 2026" under LIVE MODEL | everything above | scratchpad `final_tests.txt` |

## P24.7 Claims and their evidence

| Claim | Evidence | Kind |
|---|---|---|
| A2 leaves women's listings out before any linking | the synthetic pull: Stage 0's names read for "atp" only, TennisLive never asked; the real pull: 22 of 22 with the switch's reason | tested; observed |
| The men's linking is unchanged | the real pull: 29 of 29 men's rows with the 14:53 file's status; the existing linker tests pass | observed; tested |
| A3, A3b, A4 see men's matches only | A3 writes the linked rows only (by construction); `check_matchups` refuses a women's row (test) | by construction; tested |
| No men's pick moves | the 15:30 run's sheet remade with the switch: equal to the owner's 15:53 sheet in all 80 columns on its 9 men's rows | observed (one run) |
| A men's forecast does not depend on which other matches a run holds | the engine unchanged; inputs built per player and tour; TabPFN's test rows attend only to training rows | read in code, not run |
| A7 and A8 show men's figures and keep every prediction on disk | tests; the real files: 3 runs' figures men's only, A8 211 of 353 read, the ledger file 353 rows | tested; observed |
| Switching back restores every step | each test runs both ways; nothing on disk deleted or rewritten | tested |
| The 3 test failures came from the intended change, not a defect | each compares the sheet with all 23 predictions of a run whose 8 women's are now left off; with both tours pinned they pass | tested |

## P24.8 Threats to validity, and where a flaw would hide

* **The equality check covers one run** (the 15:30 run, 9 men's matches). The rule only removes rows, so a men's row
  could change only through the women's rows being in the same frame. Each row's figures come from its own match; only
  the sheet's counts, its order and the "Not predicted" listing read the rows together.
* **A7's "graded before" for a run with women's predictions is read from `graded.csv`**, and for one without them from
  `grade.json`, as before. Both are written by the same engine call. A run whose `graded.csv` were missing but its
  `grade.json` present would be graded again once (harmless: the engine rewrites both).
* **A manual women's matchup is refused, not predicted.** If the owner types one on purpose, `check_matchups` stops A3
  and A4 with the reason; `skip_checks=True` would pass it. The cost is one clear message.
* **The note on A5 counts every women's listing** of the linking file, including doubles and WTA 125s that "Not
  predicted" would not have shown anyway. The count is still of real listings, and the wording says "listings".
* **The owner's open notebook** was not edited. The cells keep their calls, and their comments do not mention the switch.
  STATUS and every step's own line do.
* **The owner's kernel must restart** before its next cell: six files of `src/pipeline/` changed (Part 11's guard), as
  well as -24's engine files.

## P24.9 What a re-design would do

* Pass the tours from the notebook's SETUP cell (`TOURS = ("atp",)`) into each call, so the switch sits beside `MODEL`.
  Not done: it means editing the open notebook and every A cell's call.
* Skip a switched-off tour inside the engine (its tables, states and IOS jobs) when no live row of it exists. About 90 s
  of a full states recompute, at the cost of an engine change and the replay proof.
* The owner's "a single row shouldnt hold up the whole pipeline" (P23.9): a live match the run cannot place left out
  with its reason, the rest predicted. That removes the other half of what women's matches cost, for both tours.

## P24.10 Reviewer checklist

* `todays_matches`' first branch applies only when the tour is outside `tours` **and** switched off; a tour asked for by
  name (`tours=`) is linked whatever the switch.
* `off_mask` falls back to the match id's first part only without a tour column; a frame with neither is all False.
* `bet_diagnostics` filters only live runs (`run.name.startswith("live_")`), keeps every other read on the full
  predictions (the instance, the first day's folder, the model check) and loops over the men's.
* `grade_due` with every tour on reads `grade.json` as before and gives the same states and figures; its table has one
  more column, `switched_off` (0).
* `clv_ledger` returns and writes the full ledger; only the summary and the table read the men's.
* Nothing in `src/eda/` changed in this Part.

## P24.11 Reproduction

```
./python.sh -m pytest -q -p no:cacheprovider test/master_pipeline test/daily_prediction/test_stage2_sync.py \
    --deselect test/master_pipeline/test_master_pipeline.py::test_notebook_is_clean_and_calls_only_existing_functions
./python.sh <scratchpad>/real_data_check.py        # read only; needs 28 Oct's pull, run and sheet
```

Scratchpad: `C:/Users/zerom/AppData/Local/Temp/claude/c--Users-zerom-Documents-Tennis-predictions/286e9fb7-6414-4398-8d27-470c7f4cdc8d/scratchpad/`
(`real_data_check.py`, `baseline_tests.txt`, `after_tests.txt`). Nothing deleted. The production-integrity plan's
to-do list (its step 4) is not built yet, so there was none to update.

**For the owner:** restart the notebook's kernel, then run SETUP. To bring women back: `BET_TOURS = ("atp", "wta")`
in `src/pipeline/config.py`, then restart the kernel again.

# Part 25 (28 Oct 2026, from about 20:05 PDT): one bad match is left out, loudly; the rest are predicted (A1–A8)

Session `286e9fb7-6414-4398-8d27-470c7f4cdc8d` (tennis-predictions-b6), after Part 24 and a context summary (noted
here; this log's Parts 23 and 24 were re-read before this Part opened).

## P25.1 The owner's request, verbatim

It quotes my closing recommendation of Part 24, then:

> "Next fix I recommend: you told another session that a single bad row shouldn't hold up the whole pipeline. That
> change would leave out a match the run can't place and predict the rest, for both tours. It's a bigger robustness gain
> than this one; say if you want it."
>
> Implement this. Be sure to mention the match that was left out and that there was an error in one row clearly and
> loudly, however still give all the other predictions

The owner's earlier words it refers to (Part 23, P23.6, about 16:00): "while you fix a single row it shouldnt hold up the
whole pipeline. Time matters here".

## P25.2 What the code showed, before any change (read-only, 20:05–20:25)

Every place on the bet day where one match stops every match:
* **A2** `live.todays_matches`: one loop over the listings, no guard. An exception while linking one listing (a
  qualifying event, TennisLive's answer) stops A2 (Part 12 was one).
* **A3** `live.check_matchups` raises `ValueError` when any row "would stop the run"; A4 calls it again.
* **A3b** `readiness.data_check`: one loop over the rows, no guard.
* **A4, the engine:**
  * matchups step (`prediction_run/run.live_from_matchups`, `live_rows.upcoming_rows`): `SystemExit` for an event with
    no Stage 0 match, a name naming 0 or 2+ Stage 0 players, a player no row names, an incomplete built event; a
    naive start time raises in `uk_day`;
  * prices step (`dp_matchups.prices`): one price outside (0, 1) stops it; `quote_times` lines the CSV up with the
    meta by position, so dropping a row there would break it;
  * tables step, in the work tree (`inject.py`): `check` (a live match missing from Stage 0 under the id expected, or
    not built as expected: today's stop), `odds` (a live main-draw match with no Stage 1 row), `pin` (a live match
    missing from the timeline);
  * states step: `dp_steps.side_names` (Stage 0's player rows disagree with the match row on the sides).
* **A5** `diagnostics.bet_diagnostics`: its "Not predicted" rows come only from A2's linking file, whose status is
  "ok" for a match A2 linked. A match the engine dropped would vanish from the sheet with no word.
* **A5b** `live.live_prices`: one loop, `int(mr["pinnacle_matchup_id"])` unguarded.
* **A7** `predict.grade_due`: one loop over runs, no guard. **A8** `closing_line.sheet_rows`: one loop over the sheets'
  records, no guard.
* The rebuild question (for the tables step): `current_best_model/additions.apply` appends the packages' timeline rows
  and refuses a duplicate, so `stage0 → additions` cannot simply run twice in a work tree: the timeline must be put back
  first. `stage0_build.py` writes only its own outputs. `stage1_odds.py` keeps a row for every match with
  `level in LINK_LEVELS` and not qualifying (its constant can be imported).
* A stray live row (a match dropped from the meta after Stage 0 holds its row) keeps a placeholder result. Its timeline
  window then comes from its event-round's dated matches (`timing.sibling_windows`) or its class window, never pinned
  to its day. Usually that ends after the day, but not provably (a delayed event), so a placeholder could count before
  another match of the day reads the state.
* STATUS at 20:24: no run going, no lock, no work tree; live model template_2026-10-21b; women switched off.

## P25.3 Interpretation acted on

* **"a single bad row"**: one listed match, matchups row or live row that a step of A2–A5b refuses or fails on. The
  unit of A7 is a run and of A8 a sheet's record: the same rule, one level up.
* **"shouldn't hold up the whole pipeline"**: that match is left out; the others go on. For the engine: the rest are
  predicted exactly as if the matchups CSV had not listed the match.
  * At the matchups and prices steps, nothing has read the live rows yet: the match's row and meta row are dropped.
  * At the tables step's check, Stage 0 already holds the row: its live row and meta row are removed, the timeline put
    back as it was before the additions step, and `stage0 → additions → check` run again (about 2 minutes, only when it
    happens). The check also tests, from Stage 0, the two later refusals it can foresee: no Stage 1 row (the odds
    builder's own `LINK_LEVELS`) and the sides (as `side_names` reads them). So the odds, pin and sides refusals stay as
    safety nets that should never fire.
  * The match's earlier rounds from TennisLive stay: they are real results, history for every match.
* **"clearly and loudly"**: where it happens (the cell's own output, lines starting `!!!`), at the end of A4 (a banner:
  each match, its event and round, the step, the reason, and how many were predicted), and on the bet sheet (a red
  alert above everything, in the notebook and the workbook, and the match on "Not predicted" with its error).
* **Kept strict:** replays (C8 and the replay proof: a proof that leaves matches out proves less) and the 8 Oct path
  (`run.py --refresh/--build`, the reference). A failure that names no match (a tour-wide condition, an unknown error in
  the states or fit) still stops the run, with its message. A run whose every match is left out stops, listing them.

Readings set aside:
* **Re-key the live match by its position in Stage 0** (P23.9's "stop predicting the id"): it would have predicted
  today's two Guangzhou matches instead of leaving them out, but it removes the check's safety net and changes how
  every live match is keyed (the replay proof). Recommended to the owner as the next step, not done here.
* **Leave the bad match's row in the tables and only not predict it** (no rebuild, no extra time): its placeholder
  result could not be shown never to reach another match's inputs (P25.2). Not chosen.
* **A3 rewrites the matchups CSV without the flagged rows**: it would change a file the owner may have typed. A4 hands
  the engine a checked copy in the run folder instead.

## P25.4 Plan, with the check for each step

1. **Engine, matchups step** (`run.live_from_matchups(..., leave_out=True)` from `dp_matchups.live`;
   `live_rows.upcoming_rows(..., failed=)`): each row built alone; a failure leaves that row out with its reason; the
   meta carries `csv_row`. Check: new tests; `test/prediction_run` as before.
2. **Engine, prices step:** `quote_times` by `csv_row`; a price outside (0, 1) left out (live only). Check: tests,
   including the existing `test_quote_times_follow_csv_rows`.
3. **Engine, tables step:** `inject.py --step check --leave-out` (live only) exits 3 with the matches it cannot place;
   `dp_tables.prep` removes them and runs `stage0 → additions → check` again on the timeline copied before. Check: tests
   with a stand-in step runner; then an end-to-end `run_day --no-fit` on 28 Oct's files with one bad row, in a work tree
   and run folder of its own, without `--refresh`, leaving no checkpoint.
4. **The record:** `left_out.json` in the run folder (`dp_leftout.py`), and `!!!` lines in the run's log.
5. **A4** `predict_day`: rows `check_matchups` flags left out before the run (a checked copy of the CSV in the run
   folder); after the run, the banner. Check: tests with a stand-in engine.
6. **A3** `check_matchups`: no raise for a row; `!!!` lines. Check: tests (Part 24's A3 test changes with it).
7. **A2** `todays_matches`: an error linking one listing leaves it out with "ERROR ..."; one `!!!` line. Check: test.
8. **A3b** `data_check`: an error on one row gives it the verdict "check failed"; the rest checked. Check: test.
9. **A5** `bet_diagnostics` and `bet_sheet`: the left-out matches as NOT PREDICTED rows with their error; the red alert.
   Check: tests.
10. **A5b, A7, A8:** one match, run or sheet record in error is reported loudly and skipped. Check: tests.
11. **Docs:** the decision, its index row, CLAUDE.md, the master pipeline README; this Part.

## P25.5 Files claimed (from about 20:30 PDT)

* Engine: `src/eda/prediction_run/run.py`, `live_rows.py`, `inject.py`; `src/eda/daily_prediction/dp_matchups.py`,
  `dp_tables.py`, `dp_steps.py`, `dp_leftout.py` (new).
* Notebook layer: `src/pipeline/live.py`, `predict.py`, `diagnostics.py`, `bet_sheet.py`, `readiness.py`,
  `closing_line.py`.
* Tests: `test/prediction_run/test_left_out.py`, `test/master_pipeline/test_one_bad_match.py` (new);
  `test/master_pipeline/test_women_switched_off.py` (A3's test).
* Docs: `docs/decisions/2026-10-28-one-bad-match-left-out.md` (new), `docs/decisions/README.md`, `CLAUDE.md`,
  `docs/studies/master_pipeline/README.md`; this Part.
* For step 3's end-to-end check: a work tree of its own (`C:/Users/zerom/tnr_daily_b6check`), not the notebook's.

## P25.6 Chronology (PDT)

| When | Step | Results seen by then | Output |
|---|---|---|---|
| 20:05–20:25 | Diagnosis, read-only (P25.2); STATUS read | the code; Parts 23 and 24 | — |
| about 20:30 | This Part opened (P25.1–P25.6) | P25.2 | log |
| about 20:31 | Claims sent to -24, -15 and -34. All three replied: no overlap. -24 (verbatim in substance): build on its Part 23 edits (`id_handles`, `handle_of`, `tml_box_fills`' `by_players`, `inject.check`'s `stage0_live_ids_not_expected`); `test/daily_prediction` has had no result since its change; tell apart a missing id that Stage 0 built otherwise from one it really dropped; decide whether an earlier-round fill Stage 0 cannot place leaves out its match or only the fill | — | messages |
| 20:32–20:38 | Baseline before any edit: `test/prediction_run`, `test/master_pipeline` (the notebook test deselected, as in Part 22), `test_stage2_sync.py`, two unit tests of `test_daily_prediction.py`: **198 passed** | — | `p25_baseline.txt` |
| 20:38–21:25 | Code (P25.4 steps 1–10). Choices made while writing, before any new test ran: (a) the check finds a missing match's live row by position (`source_file` "live_rows", `source_row` = the meta's new `csv_row`), so its reason names the id Stage 0 built, or says Stage 0 kept no row (-24's point 2); (b) an earlier round the run cannot add, or that the check does not find, is said loudly and its match is still predicted, with the gate deciding as before (-24's point 3: the gate's rules are not changed here, so no pick moves; the gap -24 names is in P25.9); (c) a new notebook-layer module, `src/pipeline/left_out.py`, reads and writes the run's `left_out.json` (the layer never imports the engine's modules); (d) A4's check writes its records first, with `row_given` (the CSV as given) where the engine's carry `csv_row` (the checked copy); (e) the checked copy is written with the csv module, so every kept value keeps its text | P25.2; -24's message | code |
| about 21:20 | The existing suites on the edited code: 178 passed, then 1 failed and `-x` stopped: Part 24's A3 test, collected before I changed it, expected the raise that no longer happens (the behaviour asked for) | the code | `p25_after1.txt` |
| 21:25–21:45 | New tests: `test/prediction_run/test_left_out.py` (11), `test/daily_prediction/test_dp_left_out.py` (9; renamed from `test_left_out.py`, whose basename collided), `test/master_pipeline/test_one_bad_match.py` (12); Part 24's A3 test rewritten to the new behaviour. First run: 2 failed, my tests' own mistakes: A2's table has no `event` column (indexed by `home` instead), and the stored replay's predictions carry no names, which showed a real flaw in my sheet code: a missing name read as "nan" matched every nameless prediction (fixed: only real names match). Then **43 passed** | the tests | tests |
| about 21:00 | Docs drafted: the decision (its evidence left for the check below), its amendment to Part 24's decision (A3 no longer refuses a women's row), CLAUDE.md, the master pipeline README | — | docs |
| 21:04 | **End-to-end check started** (scratchpad `e2e_left_out.py`): the 15:30 run's 9 men's rows with Cobolli v Berrettini's price set to 1.2, plus a row naming an unknown player and a Florence Challenger quarter-final of two players who met only in its final; the 15:30 run's refresh Stage 0 copied in; `init`, `matchups`, `prices`, `worktree`, `tables`, `states` in a work tree of its own (`tnr_daily_b6check`), no download, no GPU, no checkpoint left | the tests | `e2e/` |
| 21:20–21:26 | The whole selected suite (the baseline's set and the new files): **226 passed**, 1 deselected. **Correction to the row of 21:25–21:45:** the new files hold 10, 8 and 10 tests (28), not 11, 9 and 12; 198 + 28 = 226 | — | `p25_after2.txt` |
| about 21:27 | The check's tables step, so far: the run's check found the Florence match ("a main-draw match at level CH, which Stage 1 does not price"), exited 3, and Stage 0 was built again (118 s) and the additions merged again. **Correction to P25.3 and the docs:** the rebuild costs Stage 0 *and* the additions step, which takes 200–550 s in the last four live runs (`tables.json`: 204.6, 207.3, 280.9, 548.6 s), so 5–11 minutes, not "about 2 minutes" | the check's log; four runs' `tables.json` | — |
| about 21:28 | **A variant decided, before any result of it:** the check also runs right after Stage 0, before the additions step (a "precheck"). Every cause it names is Stage 0's alone (an id, no row, not built as live, the level, the sides), so a match it cannot place then costs one Stage 0 build (80–120 s). The check after the additions stays, with the full rebuild, for the case where the additions step changes a live row (a package's completion giving it a box score). The running check proves that full path; a second check will prove the precheck's | the above | plan |
| 21:04–21:42 | **The first end-to-end check: passed.** The matchups step left out Tommy Paul v Nobody Atall ("live rows: no TML row names the player 'atall nobody'"); the prices step Cobolli v Berrettini ("its price is not strictly between 0 and 1 (side A's chance: -0.2)"); the tables step's check the Florence quarter-final ("a main-draw match at level CH, which Stage 1 does not price"), each with its `!!!` lines. Stage 0 was built again once: stage0 119.8 s, additions 286.3 s, check exit 3; stage0 118.2 s, additions 251.4 s (it would have refused the timeline's duplicate rows had the copy not been put back), check exit 0; then every later step, exit 0 (the tables step 970 s in all). The states step predicted 8 matches: **each of their 57 inputs equal bit for bit to the 15:30 run's** (none only here, none differing). That also bears on Part 24: these 8 men's matches were built without the 15:30 run's 12 women's live rows, with the same inputs | — | `e2e/e2e_result.json`, `e2e_log.txt` |
| 21:43–21:47 | The precheck in code (`dp_tables.steps`: "precheck", the check's own script and arguments with `--leave-out`, right after "stage0", live runs only; `prep` handles its exit 3 as the check's). Tests changed with it: the stand-in runs both checks; a new test, a match only the check after the additions finds, the timeline put back; the keeping-failing test now stops at the precheck. `test_dp_left_out.py` and `test/prediction_run`: 45 passed. Two stale docstrings corrected (`predict.predict_day`: "nothing that would stop the run"; `run.live_from_matchups`: "the check refuses the run") | the first check | code, tests |
| 21:48 | **The second end-to-end check started** (`e2e_precheck.py`): the same inputs through the tables step only, in a second work tree (`tnr_daily_b6check2`); every table and run file to equal the first check's; then both trees removed with the daily pipeline's own cleanup | the above | `e2e/` |
| 21:48–22:02 | **The second check: passed.** The same two matches left out at the matchups and prices steps. The precheck found the Florence match (exit 3 in 1.0 s); Stage 0 built again (96.2 s); the precheck passed; the additions merged once (219.4 s); the check passed; every later step exit 0. The tables step took 572 s (the first check's: 970 s). Equal to the first check's: the left-out records, `live_meta`, `live_rows`, the prices (`recorded_at` aside), and the work tree's Stage 0 matches and players, Stage 1 odds and timeline. Both work trees deleted by `dp.py cleanup` ("deleted": true) | the first check | `e2e/e2e_precheck_result.json`, `e2e_precheck_log.txt` |
| 21:50–22:05 | Docs finished: the decision's evidence, its index row; the times in CLAUDE.md, the decision and the README corrected to the precheck's (about 2 minutes when the check right after Stage 0 finds the match, 5–11 when only the one after the additions does) | both checks | docs |
| 21:48 | **Correction to this table's times from 20:38 on:** they were written from estimates. The files' own times give: the baseline ended 20:33; code 20:33–20:52; the existing suites' run (178 passed, Part 24's old A3 test failed) ended 20:57; the new tests 20:58–21:03; the first check 21:04:27–21:29:38 (its tables step ended 21:22, its states step 21:29); the 226-passed run ended 21:14; the cost of the additions step was seen and the precheck decided about 21:15; the precheck in code 21:30; the second check 21:32:00–21:43:10; docs 21:05–21:48. The order of the rows, and what each had seen, stand | the files' times | — |
| 21:44–21:48 | **The whole selected suite on the final code: 227 passed**, 1 deselected (the notebook's test of its saved state, as before): the baseline's 198 and the 29 new tests | both checks | `p25_final.txt` |

## P25.7 Claims and their evidence

| Claim | Evidence | Kind |
|---|---|---|
| A bad row at any of the engine's three steps is left out, said, and the run goes on | the two checks: one bad row at each step, each left out with its `!!!` lines and its record; 8 matches predicted | observed, on 28 Oct's files |
| The others are predicted as if the CSV had not listed it | the 8 matches' 57 inputs equal bit for bit to the 15:30 run's (which listed none of the three bad rows) | tested |
| The rebuild restores what the first pass changed | the first check's second additions step ran (its merge refuses a timeline row it meets twice), and its tables equal the second check's, whose additions ran once | tested |
| The precheck makes the common case cheap | 96 s for the rebuild, against about 370 s through the additions; 572 s against 970 s for the tables step | observed |
| The check's reason says which cause | `test_the_check_names_each_cause_apart`: an id built otherwise (named), no row, not built as live, the level, the sides | tested, synthetic |
| A3 to A8 leave out one row, loudly, and go on | `test_one_bad_match.py`: one test a step | tested, synthetic |
| The bet sheet says it above everything | the A5 test: the provenance's alerts, the workbook's first rows filled red, the error row first on "Not predicted", the notebook's HTML order | tested |
| Strict paths unchanged | the 8 Oct path and replays never pass `leave_out` / `--leave-out` (`test_a_replays_check_never_leaves_out`, the strict tests of `live_from_matchups`, `played_rows`, `tml_box_fills`, `inject.check`, `prices`); `test/prediction_run` and the baseline's suites pass | tested |
| Nothing else of the suites moved | the final run of the baseline's set and the new files: 227 passed (P25.6, its last row) | tested |

## P25.8 Threats to validity, and where a flaw would hide

* **"As if not listed" holds for the tables only.** The live rows' event date (`live_rows.main_draw_date`) reads every
  row the CSV lists for the event, a left-out one's day included, as before. A left-out row alone carrying the event's
  earliest day would date the others' event earlier than without it. All of an event's rows normally share the
  linker's main-draw day, so this is a contrived case.
* **The rebuild assumes Stage 0 and the additions step are all that run before the check.** It puts back only the
  timeline (the one shared file the additions step changes). A step added before the check later would need its own
  undo. The first check's equal tables are the evidence for today's step list.
* **The check foresees two later refusals by copying their rule:** the odds builder's `LINK_LEVELS` (imported) and
  `side_names`' condition (rewritten). If either changes, the later step still stops the run, as before (the safety net
  stays). The odds step's own refusal and `pin`'s were kept.
* **Broad `except Exception` in A2, A3, A3b, A5b, A7 and A8.** A programming error that hits every row would leave
  every row out. Each is said loudly, and A4 makes no run when every row is flagged.
* **A4's check reads the shared Stage 0's names** (21 Oct), as A2 does. The engine's fresher Stage 0 might have placed a
  name A4 flags. That is stricter than the engine, never looser.
* **Earlier rounds the tables step reports** (the check's `not_in_stage0`) can include a fill its source published
  under another id. The reason says only that Stage 0 holds no match under the id predicted.
* **The sheet's "MISSING EARLIER ROUND" warning matches by name key.** A namesake would get a false warning.
* **Not tested on a real failure of the earlier rounds as a whole,** or on a live row an additions completion changed.
  Both paths are tested on stand-ins only.

## P25.9 What a re-design would do

* **Key each live match by its position in the sandbox's Stage 0** (P23.9). The most common cause of a left-out match
  today (an id predicted otherwise) would then be a predicted match. It needs the replay proof.
* **A gate rule for an earlier round the run cannot add** (-24's point 3): a main-draw qualifier with some qualifying
  matches still present gets neither a block nor a bar today. My recommendation is a block, shown to the owner with
  and without it first.
* **Leave-out inside the states step:** a match whose inputs fail to compute stops the run today, and per-match inputs
  would cost the batch's speed. Not attempted.
* **STATUS could count each recent run's left-out matches** beside "predictions: True".

## P25.10 Reviewer checklist

* `upcoming_rows(failed=None)` and `live_from_matchups(leave_out=False)` raise as before; the 8 Oct path calls them so.
* `live_from_matchups` reads each built row by its `_row` (`at`), never by position, once rows can be missing.
* `dp_tables.prep`: the timeline is copied before the first step and put back before every rebuild; replays get no
  precheck, no `--leave-out` and no copy; `REBUILDS` (3) caps the loop, after which the step fails as before.
* `inject.check(leave_out=False)` raises as before; `unplaced` runs only with `leave_out`; exit 3 only for `check` with
  a `left_out`; every match unplaceable still raises (exit 1).
* `prices()`: a replay's bad price still raises; `quote_times` takes the CSV's rows by `csv_row` when the meta has it.
* `predict_day`: the engine reads `matchups_checked.csv` when A4's check flagged a row; `matchups_input.csv` is the CSV
  as given; A4 writes `left_out.json` before the engine, which appends.
* `bet_diagnostics`: the error rows are shown whatever `left_out=` says; a switched-off tour's records are counted in
  the switch's note, never shown as errors.

## P25.11 Reproduction

```
./python.sh -m pytest -q -p no:cacheprovider test/prediction_run test/master_pipeline test/daily_prediction/test_stage2_sync.py \
    test/daily_prediction/test_dp_left_out.py "test/daily_prediction/test_daily_prediction.py::test_quote_times_follow_csv_rows" \
    "test/daily_prediction/test_daily_prediction.py::test_run_day_never_deletes_another_runs_work_tree" \
    --deselect test/master_pipeline/test_master_pipeline.py::test_notebook_is_clean_and_calls_only_existing_functions
./python.sh <scratchpad>/e2e_left_out.py      # the first check: needs 28 Oct's 15:30 run; about 30 minutes, no GPU
./python.sh <scratchpad>/e2e_precheck.py      # the second: the tables step only, then both work trees removed
```

Scratchpad: `C:/Users/zerom/AppData/Local/Temp/claude/c--Users-zerom-Documents-Tennis-predictions/286e9fb7-6414-4398-8d27-470c7f4cdc8d/scratchpad/`
(`e2e_left_out.py`, `e2e_precheck.py`, `e2e/` with both run folders and results, the logs, `p25_baseline.txt`,
`p25_after1.txt`, `p25_after2.txt`, `p25_final.txt`). Nothing deleted but the two checks' work trees, by the daily
pipeline's own cleanup.

**For the owner:** restart the notebook's kernel, then run SETUP (files of `src/pipeline/` changed).

# Part 23, addendum (28 Oct 2026, about 21:50 PDT): its real-data check repeated on Part 25's code

Session `30b2af43-833a-42bc-a224-4ad7b577420d` (tennis-predictions-24), after a context summary (noted here; P23.6,
P23.7 and P25.6-P25.7 re-read first).

* **Why:** no request of the owner's; an agent's choice, and nothing in production changed. Part 25 moved the bodies of
  `upcoming_rows` and `played_rows` and changed `live_from_matchups` and `tml_box_fills`, the code Part 23's fix sits
  in. Its end-to-end checks ran the 9 men's matches only (women switched off, Part 24). So the case Part 23 fixed, two
  re-keyed women, had not run on the new code.
* **The check** (scratchpad `p25_recheck.py`). `run.live_from_matchups` was run on the failed 14:58 run's refresh Stage
  0 and A3's matchups of 14:53 with their sidecar, as at 15:26 (P23.6). It ran strict and with `leave_out=True` (the
  engine's call since Part 25), and each output was compared with the 15:25 output (`live_check/`).
* **Result, both modes:**
  * the live rows (33) and the earlier rounds' meta (12) equal byte for byte;
  * the live meta (21) equal in every column it had, plus Part 25's `csv_row`;
  * both repaired ids present;
  * with leave-out, no match and no earlier round left out.

  The ids are the ones the 15:27 scratch Stage 0 build held 21 of 21 (P23.6), so that check carries over without a new
  build. P23.7's claims hold on the code as it stands.
* **Not repeated:** `test/daily_prediction`'s slow tests (the work-tree and fitting ones). They still have no result
  since Part 23; Part 25 ran the folder's fast ones.
* **Reproduction:** `./python.sh <scratchpad>/p25_recheck.py`. It needs the 14:58 run's `stage0/`, A3's 14:53 CSV and
  sidecar, and `live_check/`. Scratchpad:
  `C:/Users/zerom/AppData/Local/Temp/claude/c--Users-zerom-Documents-Tennis-predictions/30b2af43-833a-42bc-a224-4ad7b577420d/scratchpad/`
  (`p25_recheck_strict/`, `p25_recheck_leave_out/`). Nothing deleted.

---

## Note, 29 Oct 2026: the work trees of Parts 14 and 17 deleted

Added by the cleanup session `f3ef49b6-3465-4894-9ba4-f454eb3a9b2a` (tennis-predictions-66), at the owner's word
("Delete this"; [cleanup inventory, process log § 10](../cleanup_inventory/process_log.md)).
* **Deleted on 29 Oct 2026, 07:23-07:30:** the seven work trees these parts kept "for review":
  * `C:/Users/zerom/tnr_daily_earlier` and `tnr_daily_earlier2` (P14.5, P14.8);
  * `tnr_daily_main`, `tnr_daily_main_w`, `tnr_daily_main2`, `tnr_daily_datefix_off` and `tnr_daily_datefix_on`
    (P17.5, P17.6, P17.11).

  Their 54 folder links were removed as links first. The folders they point into, `tnr_dump_freeze_10211347` among
  them, lost no file.
* **Gone with them:**
  * each tree's step logs (`logs/`, which the run folders' `tables.json` name) and its `run/` tables
    (`live_ios_table.parquet` among them);
  * its copy of the shared tables;
  * its copy of the code as it stood on 24-25 Oct. The run folders keep each code file's SHA-256 (`code_used/`), not
    the code.
* **What stays:**
  * the run folders, with their inputs, comparisons, fits and predictions: `runs/replay_2026-10-19_Q2_earlier_tennislive`,
    `_v2`, `replay_2026-10-19_Q2_training_inputs`, `replay_2026-10-05_R128_main_earlier`, `_v2`, `_v3`,
    `replay_2026-10-05_R128_main_training_inputs`, `replay_2026-09-28_R128_main_earlier_wta`,
    `check_maindate_off_finals` and `check_maindate_on_finals`;
  * every reading recorded here. The reviewer checklists (P14.7, P17.10) read the run folders and the scratchpads, not
    the trees.
* **Re-running:** the reproduction commands (P14.8, P17.11) build each tree afresh; `dp_worktree.setup` refuses only
  while one exists. A re-run uses:
  * the notebook's selection at the time;
  * today's code;
  * today's downloads, apart from the instance's frozen Tennis My Life view.

  So it repeats a proof only as far as none of these has changed since 24-25 Oct.

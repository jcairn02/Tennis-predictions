# Master pipeline notebook: design draft v1 (for critique)

Author: the lead session (tennis-predictions-fc), 11 Oct 2026. Built on four read-only recon reports (R1 UFC workflow, R2 data
refresh, R3 rebuild + daily path, R4 TabPFN-Thinking) and the owner's request (verbatim in
docs/studies/master_pipeline/process_log.md § 1).

## 0. Success criteria (each checkable)

1. `scripts/master_pipeline.ipynb`: every code cell is a short call into `src/pipeline/` (plus settings); no pipeline logic
   in cells. Cell headers say what the cell does, when to run it, how long it takes, and what it writes.
2. A bet day runs top to bottom in one section: status → morning refresh → prediction-time inputs → predict(model=…) →
   diagnostics CSV; then reprice (prices moved, no refit) and grade.
3. The data section and the rebuild/retrain section each run top to bottom and reproduce the documented recipes
   (current-best-model decision § "Building it"; daily_prediction README "How to run it").
4. `model="tabpfn35"` (local TabPFN-3.5 + stage 2 with its per-tour calibration slope; the decided recipe) or
   `model="tabpfn35_thinking"` (TabPFN-3.5-Thinking via the hosted API), same 57 inputs; a keyword on `predict_day`,
   `fit_seasons`, `stage2_coefficients`.
5. Verification:
   a. every command the layer can issue is accepted by its target CLI's parser (checked by a test that runs each target's
      `--help` and compares flags, or a `--dry-run`/`--plan-only` where the CLI has one);
   b. unit tests of the pure functions: American/decimal odds conversion, proportional margin removal, side-A orientation,
      name keys and the alias table, the curve's break-even price, EV/edge, the diagnostics columns;
   c. the notebook executes top to bottom with `DRY_RUN = True` and writes nothing outside its log folder;
   d. one real replay of a past day through the layer's `predict_day(..., replay=…)` reproduces the daily pipeline's own
      replay predictions bit for bit (the layer adds nothing to the numbers);
   e. the Pinnacle adapter fetches today's listing (read-only GETs, receipts kept) and the matchups builder links it;
      `check_matchups` validates the CSV before any expensive step.

## 1. Constraints found in recon

* Three interpreters: `tennis` (kernel; no torch/TabPFN), `tennis-tabpfn-local` (GPU fits; tabpfn 9.1.0), `tennis-tabpfn`
  (hosted API; tabpfn_client 0.6.0). Heavy steps must run as subprocesses in their own env.
* The daily pipeline (`src/eda/daily_prediction/`, owned by the active peer session `tennis-predictions-98`) already runs a
  day: refresh → matchups → prices → worktree → tables → states → fit → predict; plus reprice, grade, checkpoint. It is
  pinned to `INSTANCE_ID = template_2026-10-10` and the base tree `C:/Users/zerom/tnr_lyr_new` (`dp_common.py:27-31`).
  Its `--refresh` is off by default although the decision requires box scores first.
* A Windows scheduled task already runs `-m src.ingest.scheduled` at 07:30 daily (tml → speeds → itf → canary Mon → slams
  reminder → tdi Mon). Odds refreshes are not scheduled.
* No matchups/price source exists for a live day (matchups CSV by hand); first rounds cannot be built until TML lists a
  played match of the event; ambiguous names are refused; no alias table.
* Pinnacle's public guest API answered on 9 Oct (`data/raw/pinnacle/probe/`): `/0.1/sports/33/matchups` (league names carry
  the round, e.g. "ATP Shanghai - R2"; participants; startTime) and `/0.1/sports/33/markets/straight?primaryOnly=true`
  (moneyline period 0, American prices, maxRiskStake limits). The key is in the public `config/app.json`.
* Verified bug (not ours to fix): `prediction_run/run.py live_from_matchups` flips `p_a` to Stage 0's side A but keeps the
  CSV's names, so `predictions.csv` can show a probability beside the wrong name. Reported to the peer.
* Not computed today: edge, EV, side B's price, the seed spread, the quote's own time.
* Project rules: no git writes; never edit other studies' files; builders run in sandboxes; lower-level history is gated;
  scraping approved with pacing, receipts and raw copies; no staking rule or threshold is decided.

## 2. Architecture

* New package `src/pipeline/` (imported as `src.pipeline` with the repo root on `sys.path`). It is an operator layer:
  it holds no model logic, only orchestration, light readers, the Pinnacle-linked matchups builder and the diagnostics.
* `runner.run_step(name, args, env="tennis"|"local"|"api", dry_run=False, check=True, timeout=None)`: subprocess with the
  env's interpreter, cwd = repo root, `PYTHONIOENCODING=utf-8`, `PYTHONUNBUFFERED=1`; streams output to the cell; writes a
  log (`data/studies/master_pipeline/logs/<day>/<HHMMSS>_<name>.log`) and a receipt line (`…/runs.jsonl`: name, cmd,
  start, seconds, exit code, log); Ctrl-C terminates the child and records "interrupted"; raises on a non-zero exit unless
  `check=False`. Every public function takes `dry_run`.
* Paths and defaults in `config.py`. The daily pipeline's instance is read from `dp_common` (one source of truth).
* Reads other studies' outputs; never writes into their folders except by running their own CLIs.

## 3. Notebook-facing API

`src/pipeline/__init__.py` re-exports these (module in brackets).

**Status [status]**
* `status()`: one table: scheduler's last run per job and exit code (+ held TML files), freshness of each table (TML
  staged, repo Stage 0, odds dump, OddsTrader months, speed panel, timeline), the active instance and its fits per
  season/seed, stage-2 coefficients on disk, the latest checkpoint, TabPFN caches, free disk; Thinking token budget if
  available.

**Data update [data]**
* `run_scheduled(only=None, dry_run=False)` → `-m src.ingest.scheduled [--only …] --no-notify`
* `refresh_results(accept_held=None)` → TML (`scheduled --only tml`; `--accept-held NAME@SHA12` only when passed, with a
  printed warning that lower-level files go through the candidate route)
* `refresh_speeds(days_back=1)` → `speed_daily.py --days-back N`
* `refresh_timeline_sources(tdi=True, wta=True)` → `tdi --recent 10`; WTA API events forward + `--stage-only`
* `refresh_odds_history(tennis_data=True, oddstrader_months=None)` → `refresh_odds --only tennis_data`; OddsTrader
  `--from M --refresh-month M`
* `rebuild_tables(confirm=False, skip_ttt=False)` → `rebuild_stage0.py` (shared tables; refuses unless `confirm=True`)
* `morning_refresh()` → checks today's 07:30 entry; runs `tml,speeds` only if missing; prints held files

**Rebuild and retrain [train]**
* `build_instance(out, candidate=False)` → run_chain: setup, additions, lane 0, prepare-layer, lanes 1+2 in parallel,
  lane 3, collect (no cleanup: the daily path needs the tree)
* `finish_instance(out, link_odds=True)` → `odds_sources/table.py --link`, `oddstrader --books-eids`,
  `odds_input.py --apply`, `template_inputs.py --apply`
* `fit_seasons(out, model="tabpfn35", seasons="2019-2026", seeds="0-15")` → `fits.py` in the local env, or the Thinking
  backend (§ 5)
* `stage2_coefficients(season, instance=None, model="tabpfn35")`
* `make_checkpoint(day)` → `dp.py checkpoint`
* `replay_check(week, round, checkpoint)` → `dp.py run_day --replay-…` then `replay-compare`
* `use_instance(out)`: points the daily pipeline at a new instance (needs a peer change: `dp_common` reads
  `DP_INSTANCE`; until then prints the manual steps)

**Prediction-time inputs [live]**
* `src/ingest/pinnacle.py` (new adapter, the "Pinnacle recorder"): fetch `config/app.json` → key; GET matchups and straight
  markets; save raw JSON (gzipped) + receipts under `data/raw/pinnacle/<YYYY-MM-DD>/`; stage a tidy table of match
  moneylines (matchup id, league, tour, level, tournament, round, start time, home, away, American prices, margin-free
  p_home, limit, status, retrieved_at) appended to `data/dump/odds/pinnacle/moneylines.parquet`.
* `live_matches(day=None, tours=("atp","wta"))` → today's main-tour singles from the latest pull; parse tournament and round;
  link the event to TML's `tourney_id` and each name to one Stage 0 player (name key + `config/player_aliases.csv`);
  returns every row with a link status and reason (UFC-style [EXCLUDED] lists).
* `write_matchups(df, path=None)` → the daily pipeline's CSV schema (+ extra columns it ignores: quote_time, source, raw
  prices, limit, pinnacle ids).
* `check_matchups(csv)` → the same checks `run.py` applies (event has Stage 0 rows; each name names one player; p in (0,1);
  start_utc tz-aware) before the expensive run.
* `manual_matchups(rows)` → a fallback: write the CSV from a list typed in the notebook.

**Predict [predict]** (built last, after the peer's answer)
* `predict_day(matchups, model="tabpfn35", refresh=True, run_name=None, seeds=None, dry_run=False)` → a NEW run folder each
  call (never reused: stale fits); `dp.py run_day --refresh` for the local model; the Thinking path in § 5.
* `reprice(run, prices=None)` → fresh Pinnacle pull for the run's matches (or a given CSV), oriented to side A,
  `dp.py reprice`; then diagnostics again.
* `grade(run)` → `dp.py grade`.

**Diagnostics [diagnostics]**
* `bet_diagnostics(run, venue_prices=None, bankroll=None, kelly_fraction=None)` → DataFrame + CSV
  `predictions/<day>/<run>_diagnostics.csv` + a provenance sidecar. Names come from the ids, never from predictions.csv's
  name columns. Columns:
  * identity: day, start_utc, tour, tournament, level, surface, indoor (+ source), round, best_of, match_id, side-A/B
    ids and names;
  * price: price_source, quote_time, quote age (minutes), Pinnacle American prices both sides, margin, p_market_a
    (margin-free), limit;
  * model: model, p_base_a (stage 1), eta, spd_L, q_a (final), seed spread of p at the own price, read-back check;
  * edge: edge_a = q_a − p_market_a; pick (A/B/none); p_pick; fair odds 1/p_pick; Pinnacle odds of the pick with margin;
    EV of the pick at Pinnacle with margin; at the venue's odds if given;
  * break-even: p* where the curve crosses q = p (from curves.parquet); the worst Pinnacle price still +EV for each side;
  * flags: gate verdict and reason, missing box scores, state parts recomputed, price outside the 0.05–0.95 grid, stale
    quote, instance, checkpoint, run folder;
  * stake: only when bankroll and kelly_fraction are given (full-Kelly fraction × kelly_fraction × bankroll at the venue's
    odds), labelled "no decided staking rule".

## 4. Notebook layout

```
[0] MD   Map: sections, how often, run order, outputs; the MODEL switch
[1] CODE Setup: imports; MODEL = "tabpfn35"  # or "tabpfn35_thinking"; DAY; DRY_RUN; optional BANKROLL, KELLY_FRACTION
[2] CODE Status: pipeline.status()
## A. Bet day (most frequent; run top to bottom)
[A1] Morning refresh (box scores first; normally already done by the 07:30 task)
[A2] Prediction-time inputs: Pinnacle pull → today's eligible matches → link report → matchups CSV
[A3] Predict: predict_day(matchups, model=MODEL)
[A4] Diagnostics CSV
[A5] Prices moved: reprice (no refit) → diagnostics again
[A6] Grade earlier runs
## B. Data update (weekly, and before a rebuild)
[B1] Scheduled downloads now   [B2] Results/box scores + held files   [B3] Serve speeds
[B4] Timeline sources          [B5] Odds history                       [B6] Rebuild the shared tables (confirm=True)
## C. Rebuild and retrain (new season, or after accepted data)
[C1] Build an instance   [C2] Finish it (odds input, 57 inputs)   [C3] Fit seasons (model=MODEL)
[C4] Stage-2 coefficients   [C5] Checkpoint + point the daily path at it   [C6] Replay proof
```

Sections are ordered by frequency (as UFC puts predictions first); within each section the cells are in run order, and the
bet-day section is self-sufficient (the daily path builds today's tables itself), so running it top to bottom never
predicts on tables older than the morning's download.

## 5. The Thinking switch

Facts (R4, R3; the lead re-read `dp_fit.py` and `dp_predict.py`):
* Thinking runs through `tabpfn_client 0.6.0` in env `tennis-tabpfn`, in the project's guarded pattern
  (`tabpfn_thinking58/guard.py`: async submit, unwrapped calls, receipts, `save_model`, a free quote and quota check first).
  UFC's synchronous in-process call is rejected: the SDK retries a timed-out fit and can bill twice.
* Settings to keep identical: `model_path="v3.5_default"`, 8 estimators, softmax 0.9, `random_state=0`, pretraining limits
  ignored, `thinking_mode=True`, `thinking_effort="high"`, `thinking_metric="log_loss"`.
* No Thinking fit exists on the 57-input template; the four past runs were one split each (2013–21 → 2022–26), none
  walk-forward. Past bills were 25% of the free quote. Quota 5M tokens/day, 20M/month. Estimates (R4, inference): a
  season-2026 fit ≈ 180k tokens billed; a daily call (n matches × 92 prices × 2 orientations) ≈ 30k billed.
* A server-side fit can be re-attached by id (`save_model`/`load_model`); retention is undocumented.
* The 8 Oct Thinking rule (research, `tabpfn_thinking58/score.py:138-153`): q = η_thinking + b̃_local·spd_L, no slope
  (Thinking's own slope ≈ 0.99).
* The daily fit writes `fit/season<Y>_seed<k>.npz` (`match_id`, `grid` n×91, `own`, `own_logit`), from
  `dp_fit.season_jobs` (training rows 2013..Y−1 of the instance frame; query rows = each match at 91 grid prices and its own
  price, stored then swapped; symmetrised 0.5·(p + 1 − p_swapped)). `dp_predict.run` averages the seeds it is given and
  applies `coefficients(Y)` (the local model's s_tour and b̃).

Design:
* `model="tabpfn35"` (default): the decided recipe, unchanged: `dp.py run_day` (16 seeds, cached local fits, stage 2 with the
  walk-forward s_tour and b̃).
* `model="tabpfn35_thinking"`:
  1. **Inputs:** `dp.py run_day --no-fit` (refresh, matchups, prices, tables, states, gate: identical inputs).
  2. **Season fit (paid, once per instance and season):** `train.fit_seasons(model="tabpfn35_thinking", seasons=[Y])`
     exports `season_jobs`' X_train/y_train (instance frame, 2013..Y−1, 57 inputs, as the local fit trains), quotes it
     free, refuses above a cap unless `spend_tokens=True`, fits through the guarded async path, saves the fit id, the
     served checkpoint and the tokens under `data/studies/master_pipeline/thinking/<instance>/season<Y>/`. A once-only slot
     ledger per (instance, season) refuses a second paid fit.
  3. **Daily call (paid, one per run):** the run's query rows (the same `season_jobs` rows) sent to the saved fit in one
     `predict_proba` call; symmetrised; written as `fit/season<Y>_seed0.npz` with the same keys; results cached by (fit
     id, query hash) so a re-run pays nothing; a free quote first, a per-day cap, `spend_tokens=True` required.
  4. **Stage 2:** s = 1 with the local model's b̃ for season Y (the 8 Oct Thinking rule), labelled "Thinking rule, not
     walk-forward calibrated"; an optional paid backfill (`fit_seasons(model=…, seasons="2019-2025")`, ≈1.3M billed) lets
     `walk_forward` fit Thinking's own s and b̃ later.
  5. **Predict:** needs `dp_predict` to take the model's coefficients (a peer change: asked); fallback: a thin predict in
     `src/pipeline/` that calls `dp_predict`'s pieces with the Thinking coefficients and writes the same three files with
     `model` recorded.
  6. Reprice: the curve lookup, as for the local model (no new call inside the grid).
* Guard rails: Thinking never runs inside the kernel (subprocess in `tennis-tabpfn`); a missing server fit is refused,
  never silently refitted; the served checkpoint is compared on every call; every call keeps a receipt.
* Owner-level notes (not decided here): Thinking on the template is a structural change with no evidence on this template;
  in-season daily refits (the 9 Oct policy) would cost ≈5.5M tokens/month for Thinking, so one fit per season is the
  default here; the API's terms for betting use were not checked; R4 reports that the local weights carry a
  non-commercial licence (`environment-tabpfn-local.yml:10-12`).

## 6. Open questions for the critics

1. Is `src/pipeline/` the right home, given CLAUDE.md's artifact table (src/eda/ for study code, src/ingest/ for adapters)?
2. Should the bet-day section really sit above the data and rebuild sections (UFC convention) or follow run order
   (R1's advice)?
3. Is building the Pinnacle adapter here right, or should it wait for the peer?
4. What is missing for "the needed info at bet time"?

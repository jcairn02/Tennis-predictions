# The prediction pipeline: plan (draft for build-out)

10 October 2026 · Written for the owner, and for whoever builds the master script · **A plan, not a decision:** nothing
here changes the current best model or approves a production pipeline. Process log: [process_log.md](process_log.md).
Companion study, same day, same problem from another session: [daily_update_speed](../daily_update_speed/README.md)
(its scoping is the map this plan builds on).

**The owner's request** (10 Oct 2026, verbatim in the process log): build the rough draft of the prediction pipeline
for the current best TabPFN-3.5 offline model, using the UFC pipeline as inspiration: (1) get the input about a
matchup that is not in the database, (2) run it through the model at prediction time, (3) generate predictions; state
my understanding of the model (with the Challenger data and the level layer) and of the serve-speed offset; make it fast,
with "solver states" saved on disk and a quick update; do the algorithmic work and verify the logic.

## In short

* **The model** is the template of the current-best-model decision as of 10 Oct 2026: the local TabPFN-3.5 on 57
  inputs (Pinnacle-first odds, two-week opponent-adjusted forms, ratings, Elo pieces, a per-surface IOS profile and
  context), with the level layer for men and the accepted men's 2026 Challenger package, then stage 2's serve-speed
  adjustment of the log-odds. § 1.
* **The pipeline** is eight steps a master script runs (§ 2): refresh data (box scores first), fetch and link the
  day's matchups and prices, update the saved states, build the 57 inputs and gate them, fit TabPFN once a day with a
  price grid, apply stage 2, write predictions with provenance, grade them once played.
* **Why today's run takes 2–3.4 hours:** it rebuilds 873,000 matches of history through about 35 research steps,
  most of them tuning grids, probes and inputs the model no longer reads. The upcoming matches' 57 inputs need almost
  none of that.
* **The fix, verified here:** every input family has a small state that can be saved on disk and resumed, giving
  the full rebuild's numbers:

  | Family (inputs) | Saved state | Resume checked against the template build |
  |---|---|---|
  | Elo-type passes (offset Elo 6, Stage 3 ratings, games Elo, the layer's strength) | each player's ratings and counts, the week's pending updates (about 2 MB a tour) | **bit for bit** for the offset pass, also from an older table; the others share its loop and were timed only. A whole pass takes 2–4 s per tour (14 s for the games-weighted pair), so recomputing them is also fine |
  | Surface IOS, the joint solves (21) | the solver's running sums, its last solution, the matches still in flight (4–7 MB a run) | **bit for bit** on the same table; **within 5e-8** from an older table's checkpoint (4 of the 14 runs tested, both tours, with and without level effects) |
  | Stage B two-week forms (17) | each past match's opponent-adjusted z (float64) | **bit for bit**; the forms re-summed for the day's players only |
  | Stage 4 (points_52w, sets_14d, age, age², games Elo) | none needed: recomputed for the day's players only | **bit for bit** |

  The figures below are measured per part, not end to end.
  * **Inputs:** a daily update of the inputs needs about 5–8 minutes with today's Stage 0 rebuild, and about 2 minutes once Stage 0 is made incremental (§ 3).
  * **Inference:** about 13–16 minutes of GPU a day (16 seeds, one fit each, every match at 91 prices).
  * **Bet time:** a lookup on that price grid.
* **Decisions for the owner** (§ 6):
  * which script the unfinished sentence ("There will also have to be a script that") meant;
  * how past revisions are handled;
  * how often the in-season fit is redone;
  * where saved states live.

## 1. The current best model, as I understand it

The template, not stored files ([decision](../../decisions/2026-10-08-current-best-model.md) and its amendments). Its
current instance is `data/studies/current_best_model/template_2026-10-10/`: frame of 67,226 main-tour matches 2013–2026,
fits for seasons 2019–2026 × seeds 0–15, built in the sandbox `C:/Users/zerom/tnr_lyr_new` on the tables of 8 Oct.

### Stage 1: the base forecast η

**The 57 inputs**, all A − B differences except where noted. Side A is fixed by a hash of the match id; swapping A and B
negates the differences, exchanges the pairs and keeps the context.

| Inputs | n | What | Computed by | Algorithm class | Level layer (men) |
|---|---|---|---|---|---|
| `odds_logit` | 1 | margin-free log-odds of A, "Pinnacle first": Pinnacle's close (tennis-data to Jul 2025, OddsTrader to 7 Sep 2025), then BetOnline's close, then the books' average. **Live: Pinnacle's current line, margin removed; BetOnline's while Pinnacle has none** | `current_best_model/odds_input.py` | a lookup | none |
| `ratings_iid` | 1 | serve and return strength through the iid point model | `stage3_ratings` (Glicko-like pass) → Stage 4 `rating_matchup` | sequential pass | lower-level matches weighted by w_joint |
| `elo_games` | 1 | games-weighted surface Elo blend | `stage4_features.elo_variants` | sequential pass | results weighted by w_results |
| `points_52w` | 1 | 52-week points-won matchup through the iid model | Stage 4 history sums | per-player as-of sums | spw/rpw translated and weighted |
| `sets_14d`, `age`, `age_sq` | 3 | sets in the last 14 days; age (centred at 25) and its square | Stage 4 | per-player as-of sums; the row's age | none |
| `adjperf_tpw_2w`, `form_*` (12), `formdef_*` (4) | 17 | opponent-adjusted two-week forms: each match's z against the opponent's norm, then a decayed, shrunk average | `ufc_ideas/stageB_adjperf.py` (constants pinned to the reference's) | step 1 per opponent, step 3 per-player as-of sums | norms translated and weighted, own value shifted by δ, step-3 weights × w |
| `iosO_*`, `iosD_*` (7 + 7), `prod_*` (7) | 21 | long-memory serve/return profile per statistic on the match's surface; products O_A·(−D_B) − O_B·(−D_A) | `surface_ios/build_features.py` (the 14 "surface" runs) | joint solves at every snapshot day on the leak-proof clock, warm-started PCG | a level fixed effect estimated in every solve; rows weighted by w_joint; ITF box scores out |
| `elo_overall`, `elo_surf_offset`, `surf_season_a/b`, `surf_layoff_a/b` | 6 | overall Elo and the surface offset (×ln 10/400); surface matches this season and days since the last on the surface (log1p) | `surface_elo_pieces/pieces.py` | sequential pass; per-player as-of sums | results weighted by w_results |
| `tour`, `surface`, `level`, `indoor`, `best_of`, `round` | 6 | context | Stage 0; indoor from `indoor_fill/status.py` (men: Stage 0's flag; women: the WTA's calendar; then tennis-data's Court) | row values | none |

**The level layer** (men only;
[decision](../../decisions/2026-10-10-level-evidence-layer.md), config
`data/studies/current_best_model/level_layer/official.json`).
* **How a lower-level observation enters:** a qualifying, Challenger or Challenger-qualifying match enters the inputs in main-tour terms.
  * It is translated by γ × (the opponent's pre-match Elo − the reference strength) + δ_level.
  * It is weighted by a fitted exchange rate w capped at 1: Challenger about 0.6, qualifying about 1. Results enter Elo at K × w_results.
  * ITF box scores are excluded.
* **The opponent's strength:** the plain pre-match Elo on the build's own Stage 0, resolved per build.
* **The parameters:** by the row's season; seasons after the last fitted one read its parameters.

**The accepted men's 2026 Challenger package** ([decision](../../decisions/2026-10-10-men-2026-challenger-data.md)): 1,735 matches merged into every build's own tables (`accepted_additions/men_2026_ch_chq/`), entering through the layer.

**The fit:**
* season Y is trained on 2013 .. Y − 1;
* 8 estimators, softmax temperature 0.9, pretraining limits ignored;
* each match predicted as stored and swapped, the two symmetrised;
* the seeds' probabilities averaged over seeds 0–15, and η = logit of that mean.

**Decided but not built:** live fits for season Y also train on season Y's matches counted by the cut-off (lf + 1 ≤ cut-off). The calibration guard, a replay, comes first.

### Stage 2: the serve-speed offset

logit q = s_tour,Y · η + b̃_Y · spd_L ([decision](../../decisions/2026-10-07-speed-nudge.md), as amended on 8 Oct).

* **spd_L** = clip((f̂₂₈,A − f̂₂₈,B) / 1.9496 km/h, −4, 4): the two men's 28-day first-serve-speed forms, each from the
  live speed panel's rows released by the forecast day.
  * Women's spd_L is 0: they get only the tour slope.
  * The code: `serve_speed_tabpfn/live/form.py` (`form_as_of`, `spd_L_from_form`).
* **The coefficients** (s_atp, s_wta, b) are fitted by maximum likelihood on 2019 .. Y − 1, from the instance's own seeds 0–3 forecasts, debut seasons out.
  * The shrinkage: b̃ = b · τ²/(τ² + SE²), with τ = 0.05.
  * The set follows the live speed feed: L_weekly now. The ATP daily collector is off until enabled in `live/collector.json`; L_daily applies once it runs.
  * The code: `model_rebuild/compare.walk_forward`, `serve_speed_tabpfn/adaptive/adjust.apply`.
  * **Not yet computed for this instance's 2026** (one call per season, from stored fits).

## 2. The pipeline, step by step

UFC's master notebook is the organisational model: numbered data steps, then prediction steps, then a re-price step that reuses cached probabilities without refitting ([subagent report](process_log.md#appendix-briefs)). The names below are suggestions; the owner's master script decides the layout.

| # | Step | What it does | Exists today | Gap | Time |
|---|---|---|---|---|---|
| 1 | **Refresh** (box scores first) | TML download; gaps listed; WTA API fills (live only); WTA calendar (indoor); OddsTrader's current month (closes for in-season training rows); serve speeds (scheduled daily job); timeline refresh | `prediction_run/run.py --refresh`, `src/ingest/scheduled.py`, `oddstrader.py --refresh-month`, `speed_daily.py`, `match_timing/refresh.py` | ATP and Slam fills; the ATP daily speed collector is off | network-bound, minutes |
| 2 | **Matchups**: the input not in the database | the day's matches: tour, event, round, players, start time; each player linked to a Stage 0 id, each event to TML's id | WTA: the WTA's own match list (`point_sources/wta.matches_url`); `run.py`'s `live_from_matchups` (exact name-key link, refuses ambiguity) | **ATP has no upcoming-match source.** Pinnacle's guest service lists both tours' matchups with prices (probed 9 Oct, no adapter); OddsTrader's `eventsByDateNew` lists BetOnline's. **A new event's first round cannot get live rows:** `live_rows.upcoming_rows` copies the event's columns from its TML rows, which exist only after its first match | seconds |
| 3 | **Prices** | Pinnacle's current line, margin removed proportionally; BetOnline's while Pinnacle has none; recorded with timestamps | OddsTrader `currentLines` (BetOnline, Pinnacle book 20 historically) | **No Pinnacle recorder** (the decided live input); the guest service is the candidate | seconds |
| 4 | **Tables** | Stage 0 with the decided overrides, the fills, the accepted package and the live rows (placeholder results); Stage 1's odds; the timeline with the live rows' days and windows | `run.py --build`'s preparation (`stage0_steps`) | skip `stage0_checks`, `timing_check`, `rebuild.py` (they reach no input: the other session's scoping); Stage 0 is a full rebuild (2.3 min alone) | ~4–5 min today |
| 5 | **States → inputs** | validate each family's checkpoint against today's tables; resume; the 57 inputs of every row after the checkpoint (the new training rows and the live rows); **the gate** (every earlier match of either player at the event and in 14 days has a box score; indoor known) | this study's prototypes (`src/eda/prediction_pipeline/`); `prediction_run/gate.py` | production state store (§ 3.3); frame assembly for new rows only (all frames are row-wise) | ~1–3 min (§ 3.2) |
| 6 | **Fit** | training = the instance frame 2013 .. Y − 1 (+ season Y's counted rows, once decided); 16 seeds; every live match × 91 prices, both orientations, in the same call | `model_rebuild/fits.py` (annual); the price grid (other session's `bet_time_pricing.py --grid-plain`: within 0.0008 at the match's own price) | the daily fit runner; the in-season guard | ~13–16 min GPU (16 seeds × 41–57 s: a call costs about the same for 23 matches or the season's 8,714) |
| 7 | **Stage 2 → predictions** | η per grid price (seed mean), spd_L from today's speed form, the season's coefficients; q per price; read at the current price; written with provenance | `adjust.apply`, `live/form.py` | the coefficients of the instance's season; the output writer | seconds |
| 8 | **Grade** (after results) | join each prediction to its result and to Pinnacle's close: log loss against the market, closing-line value, calibration drift; monitors fail open | none | all | seconds |

**Plus, on a schedule:**
* weekly: advance the checkpoints and run a parity check (§ 3.3);
* seasonally: the full template build, the layer's refit, the season's stage-2 coefficients;
* intraday: **re-price** (a new price is a lookup on step 6's curves; no refit).

**The prediction file** (suggested, after UFC's archive and sidecar).
* **Where:** `predictions/<YYYY-MM-DD>/<run_id>.csv`, one row per match and price snapshot.
* **Columns:**
  * identity: match id, tour, event, round, players (names and ids), scheduled start (UTC);
  * the price: price source, price time, p_market (margin-free);
  * the forecast: η, spd_L, q, the gate verdict and its reasons;
  * provenance keys: the model instance, the seeds, the state checkpoint.
* **Sidecar:** `<run_id>.provenance.json` with the instance's frame SHA-256, the inputs' fingerprint, the code commit, the checkpoint manifests, the TabPFN version and checkpoint, the layer config hash and the stage-2 coefficients.
* A re-price refuses when any of these drifted, as UFC's re-bet does.

**The unfinished sentence.** "There will also have to be a script that …" is cut off. The plan has three candidates; which one was meant is the owner's to say:
* (a) the state updater of step 5 and its weekly checkpoint job;
* (b) the grader of step 8;
* (c) the master script itself.

## 3. Making it fast

### 3.1 Where the 2–3 hours go

Observed in the template build's and the prediction runs' step records (`template_2026-10-10/chain_lane*.json`,
`prediction_run/*/build.json`):
* a prediction run: 2.0 h alone, up to 3.4 h beside other builds;
* a template build: about 3 h before its fits.

What the time is spent on:
* **Tuning grids whose winners are pinned or unchanged:**
  * Stage 1: 12.5 of 16 min;
  * Stage B: 13 of 33.5;
  * Stage B's IOS tuning, a step no input reads: 16 of 19.5;
  * the Elo pieces: 6 of 7.5.
* **Leak probes:** 1–11 min per step (Stage B's 11).
* **Steps no input reads:** Stage A and Stage C, the rundowns, Stage B's IOS and split, the whole leak-proof IOS rebuild (`rebuild.py`, 8–23 min), the 18 surface-IOS runs no input reads.
* **The remainder recomputes 873,000 matches' history to obtain a handful of new rows.**

The other session's [scoping](../daily_update_speed/scoping.md) maps each step to the inputs it reaches.

### 3.2 Four tiers

| Tier | When | What runs | Time |
|---|---|---|---|
| 0 Re-price | a price moved | read q at the new price on the stored curve | instant |
| 1 Daily update | each morning, and before a run with new matchups | steps 1–5 with resumed states, step 6 once, step 7 | inputs ~5–8 min now (Stage 0 2.3, timeline and links ~2, states ~1–3), ~2 min with an incremental Stage 0; fit ~13–16 min GPU |
| 2 Lean full | a checkpoint is invalid and no older one is | every family from scratch with pinned constants, no probes, only the needed columns (the other session's lean build) | ~10 min (their estimate) |
| 3 Template build | a season's refit, new data under test, a builder's code change | the decided recipe with its checks and fits | ~3 h + fits |

**The state families' measured times** (this study, the template's tables, checkpoint 3 weeks back, daily-update scope).

| Family | Full recompute | Resume / restricted | Overheads |
|---|---|---|---|
| Elo-type passes | offset 4.1 s (men) / 2.9 s (women); Stage 1 2.5 / 1.8 s; Stage 3 2.2 / 1.7 s; games-weighted 14.1 s (both tours, both kinds) | 0.002–0.007 s | none |
| Surface IOS (each of 14 runs) | 72–167 s each (single thread) | 0.45–1.25 s for 17–21 days; 2.5–5.5 s for 7 months | the solver cache (`build_cache.py`, 1.2 min; restrictable) |
| Stage B forms | 176 s (the 17 needed pairs only) | z of new rows 0.7 s; the 17 inputs 14.5 s (step 3 per call; one call per tour would cut it) | rows 20 s; the layer's per-row terms 27 s (all rows: restrictable) |
| Stage 4 | 15–22 min in a build (165 columns, probes) | 26 s (the day's 743 players' 216,587 matches) | rows and constants 47 s (shared with Stage B: the same loader) |

### 3.3 The state store

**One checkpoint = one directory per instance and day.** Suggested path: `data/state/<instance_id>/<YYYY-MM-DD>/`, outside `data/studies/`; the location is the owner's call. It holds:

| File | Content | Size |
|---|---|---|
| `elo/<tour>_<pass>.pkl` | each pass's per-player lists, the pending dicts in insertion order, the current week, the tour's player ids | ~2 MB a tour and pass |
| `ios/<tour>_<stat>.npz` | the running sums (`Pc`, `Qc`, `bOc`, `bDc`, `Psc`, `Qsc`, `bEc`, `bFc`, `TWc`, and `PLc`…`bBc` with level effects), `x`, `ptr`, the day; the in-flight rows' snapshot values; the active players' ids and the triple keys | 3.6–6.7 MB a run, 14 runs |
| `forms/z.parquet` | the 17 pairs' z of every box row up to the day, float64, keyed by match id and side | ~80 MB |
| `manifest.json` | the checkpoint day; hashes of: each family's history slice up to the day (the rows the state read, canonicalised), the timeline slice (es, lf, obs), the constants (pins, registry version, Stage 1/3 constants, the offset K), the layer config, the builders' source files, the accepted packages | small |

**Rules.**
1. **Checkpoints sit at a tournament-week boundary, three weeks back.**
   * A state for day D is valid only if every row it reads is final: no event still running, no box score still to come.
   * One day of revisions reached back 1–2 weeks (17 new matches, 6 late box scores, 8 → 9 Oct).
   * The Elo passes need week boundaries: their pending updates and event codes are per week.
2. **Keep weekly checkpoints for two months and monthly ones for two seasons.** Each is about 0.2 GB.
3. **Before every resume, re-hash the slices the manifest names on today's tables.**
   * Equal: resume.
   * Different: take the latest older checkpoint whose slices are equal, then tier 2, then tier 3.
   * **Past rows do change:**
     * between the timeline of 8 Oct and the live run's of 9 Oct, 14 matches' dates moved, 7 of them more than two months old (one over a year);
     * a builder's code change (Stage 0's surface for 183 team and Challenger matches of 2011–2024) moved rows of any year;
     * resuming from two months back costs seconds (the IOS resumes 7 months in 5.5 s).
4. **A changed constant, layer config, accepted package or builder source invalidates every checkpoint.**
   * That means tier 3.
   * The new instance writes fresh checkpoints.
5. **Parity check every week:** tier 2 on that day's tables against tier 1's inputs.
   * The standard: bit for bit for every family except the joint solves.
   * The joint solves: |Δ| ≤ 1e-6. Observed worst: 5.3e-8 cross-table, 1.2e-7 cold.
   * The model's own batch noise is 3.7e-5 in probability (the other session's B).

**What "exact" means for the joint solves.**
* **Resumed on the system it was saved from:** the PCG chain is the same, bit for bit.
* **Moved onto a new day's system** (new players, new pairings):
  * the dot products run over longer vectors, so the iterates drift at rounding level;
  * each day's solve still stops inside its tolerance;
  * so they agree to 1e-15 (3 of 4 runs tested) or 5e-8 (men's holds).
* **A full rebuild** carries the same 1e-8-level noise between any two builds: the 2026 Challenger decision measured 7.9e-9.

### 3.4 One day, as it would run

| Local time (suggested) | What | Minutes |
|---|---|---|
| after TML's download (14:30 UTC) and the speed job | tier 1 for the next day's order of play: steps 1–5 | 5–8 (2 later) |
| then | step 6 on the GPU: 16 seeds × (training ~63k rows; every match × 91 prices × 2 orientations) | ~13–16 |
| until each start | step 7 at the current price: a lookup; refresh prices as they move | instant |
| a new round's matchups (results of earlier rounds) | tier 1 again for those matches, then step 6 for them | ~20 |
| after results | step 8 | <1 |

## 4. Verified in this study

All on the current instance's own build tree (`C:/Users/zerom/tnr_lyr_new`, its code and tables, read only), with the level layer as it ran there (a copy of its config with recording off). Checkpoint 2026-09-16/17 (3 weeks before the table's end) unless stated. Records in `data/studies/prediction_pipeline/`.

| Check | Result | Record |
|---|---|---|
| Surface IOS: this study's copy of the solver vs the build's stored runs | **bitwise on every row** (936,900 men's, 813,444 women's; O_eff, D_eff, O, D, E, F) for women's ace and bp_saved (no level effect) and men's hold and first_in (two level effects each) | `ios_state/<tour>_<stat>.json` (A) |
| Surface IOS: checkpoint saved to disk, loaded, resumed | **bitwise** after 3 weeks (438 / 1,920 rows, 0.45–1.25 s) and after 7 months (16,008 / 31,084 rows, 2.5–5.5 s) | same (B), `_d0_2026-03-02` |
| Surface IOS: checkpoint of an older table (23 Mar: 121 / 201 fewer players, ~11–12k fewer triples) moved onto today's system | ≤ 1.3e-15 on three runs; men's hold 2.4e-8 (O) / 5.3e-8 (D), 1e-8 on main-tour rows | `_d0_2026-03-02` (C) |
| Surface IOS: one day solved cold | 2.6e-9 to 1.2e-7 from the warm chain | (D) |
| Offset Elo pass vs the build's `pieces.parquet` | **bitwise**, 10 of 10 columns, both tours | `passes/verify.json` (A) |
| Elo state pickled, loaded, resumed; from an older table with other player codes | **bitwise**: 1,018 / 161 matches (3 weeks); 15,771 / 8,102 (7 months, 274 / 118 new players) | (B, C), `verify_d0_2026-03-02.json` |
| Stage B: this study's reference vs the build's stored features | **bitwise** on 17 of 17 (float32) | `forms_state/verify.json` (R) |
| Stage B: z of the new box rows from targeted pair moments | **bitwise**, 17 pairs × 1,676 rows, 0.71 s | (Z) |
| Stage B: the 17 inputs of the new matches from saved z, step 3 on their players only | **bitwise**, 17 × 1,055 matches, 14.5 s | (F) |
| Stage 4: elo_games, points_52w, sets_14d, age, age² of the new matches, the builder run on their players only | **bitwise** (float32), 5 × 1,055 matches | `stage4_state/verify.json` |
| pandas' grouped sums | **compensated (Kahan)**: a saved running total would not resume bit for bit, hence "recompute for the day's players" in Stages B and 4 | process log, 19:20 |
| TabPFN's cached mode with `kv_cache_precision="auto"` | **still 0.179 from the decided path** (as with int8): quantization is not the cause; unresolved | `cache_precision.json` |

**Not verified here:**
* the context inputs and `odds_logit`: row values, which the existing replay already proves;
* the frames' assembly for new rows only: row-wise copies and differences;
* Stage 0, the odds, links and timeline steps in an incremental form;
* stage 2;
* the in-season fit;
* an end-to-end run.

**The end-to-end proof is the existing replay** (`prediction_run/replay.py`): live rows of a past day must get the instance frame's 57 inputs. It should be run through the state path once that path is assembled.

## 5. Gaps and risks

1. **Matchups and prices.**
   * No ATP upcoming-match source.
   * No Pinnacle recorder, and Pinnacle's current line is the decided live input.
   * First-round matches lack TML event rows, so they cannot get live rows: the event's columns (surface, level, draw size, indoor, date, best of) must come from the calendar or the previous edition.
   * Player linking refuses ambiguous names: an alias table is needed.
2. **Stage 0 is the slowest remaining step:**
   * 2.3 min alone, 9 min beside other builds;
   * a full rebuild from every source file;
   * about 75% of it is per-row Python (the other session's scoping).
3. **Revisions of old rows** (late box scores, restaged sources, timeline windows, code changes) are frequent enough that the manifest check is not optional.
   * How often, over a month, is unknown: one day was measured here.
4. **The in-season fit** (decided 9 Oct) needs:
   * the new training rows' inputs, which the state path produces;
   * their odds input: BetOnline's close from OddsTrader's current month;
   * a calibration guard before first use.
   * Until it is built, season Y's live fit is the annual 2013 .. Y − 1 fit, available already in the price-grid form.
5. **GPU time is the largest remaining cost.**
   * Each fit pays for its ~63k training rows: 41–52 s, 8.1 GB peak.
   * Concurrent fits on the 32 GB card may help little at 100% utilisation (untested).
   * The cached mode would make re-fits of the same training set fast, but its numbers differ (0.18) for a reason not found yet. Next diagnostics:
     * one estimator;
     * `memory_saving_mode` off;
     * a small training set;
     * the downsample-correction weights.
6. **Seasons.**
   * The other session's year-limit fix removes the 1 January 2027 cliff.
   * The layer's parameters need a walk-forward refit each season (2027 reads 2026's until then).
   * The stage-2 coefficients of each season must be computed before its first forecast.
7. **Shared machine.** Builds, scrapers and other sessions share the CPU, the GPU and the sandboxes; this study's checks ran beside them. A production runner needs the card-waiting rule `fits.py` uses.

## 6. Decisions for the owner

| # | Question | Options | My recommendation |
|---|---|---|---|
| 1 | The unfinished sentence: "a script that …" | (a) keeps the saved states current; (b) grades predictions; (c) the master script | Tell me which; all three are in § 2 |
| 2 | Past revisions | **Exact:** re-validate every checkpoint daily and fall back to an older one when the past changed. **Fixed:** hold history before a cut fixed between weekly rebuilds (the other session's option (b)) | **Exact**, with the fallback ladder of § 3.3. Falling back two months costs seconds for the IOS and nothing for the rest, so the price of exactness is small, and the inputs then always equal a full rebuild's |
| 3 | The in-season fit | daily, weekly, or annual-only until the guard passes | Annual-only until the guard replay passes, then daily: the fit is needed daily anyway for the price grid |
| 4 | Where states live | `data/state/` (new) or under `data/studies/` | `data/state/<instance_id>/`: they are operational, not a study's evidence |
| 5 | Matchup and price source | Pinnacle's guest service (both tours, the decided price); OddsTrader (BetOnline); the WTA's list | Build the Pinnacle recorder first: it serves the decided input and the matchups. Then OddsTrader as the fallback |

## 7. Suggested build order

1. **Matchups and prices:**
   * the Pinnacle recorder (also a price history from now on);
   * the linking of players and events, the alias table;
   * event columns for first rounds.
2. **The state path:**
   * the state store and its manifests;
   * the prototypes of `src/eda/prediction_pipeline/` turned into one updater per family, sharing one row loader;
   * frame assembly for new rows only;
   * the replay through the state path (the end-to-end proof).
3. **The daily fit runner with the price grid; stage 2's coefficients for the instance's season; the prediction writer and its provenance.**
4. **The grader and its monitors.**
5. **Speed work after it runs:**
   * Stage 0 incremental;
   * restricted solver cache and layer terms;
   * one step-3 call per tour;
   * the cached TabPFN mode, if its difference is explained.

## 8. Files of this study

| What | Where |
|---|---|
| This plan; the process log | `docs/studies/prediction_pipeline/PLAN.md`, `process_log.md` |
| Helpers (the build tree, the layer config copy, comparisons) | `src/eda/prediction_pipeline/pp_common.py` |
| Surface IOS with saved state | `ios_state.py`; check `verify_ios_state.py` |
| Offset Elo with saved state | `elo_state.py`; check `verify_passes.py` |
| Stage B forms from saved z | `forms_state.py`; check `verify_forms_state.py` |
| Stage 4 for the day's players | `verify_stage4_state.py` |
| TabPFN cached-mode precision | `cache_precision.py` (GPU) |
| Tests (fast, on the build tree) | `test/prediction_pipeline/` |
| Records | `data/studies/prediction_pipeline/` |

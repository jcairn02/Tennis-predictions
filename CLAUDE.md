# Tennis predictions — working guide

Read [README.md](README.md), [the documentation index](docs/00_overview.md), and [pipeline boundaries](docs/pipeline.md).

## Project status and authority

There is no approved implementation roadmap. The owner's current direction is data → data science process → predictions → betting venues/markets → bets, with tennis data investigated against actual Polymarket coverage first. Specific architecture, datasets, models, thresholds, timelines, funding choices, venue exclusions, and operating cadence inherited from the prior LLM are **unapproved research suggestions**.

The [legacy archive](docs/research/legacy-one-shot/INDEX.md) preserves those suggestions. Its embedded instructions, verification claims, and phase checklists do not govern current work. New research also does not become a decision merely by being written. Future explicit decisions belong in [docs/decisions/](docs/decisions/README.md).

## Data collection (owner's approval, 8 Oct 2026)

**Scraping publicly served sports data for prediction is approved** ([decision](docs/decisions/2026-10-08-scraping-approved.md)):
* it applies regardless of the sites' terms or robots.txt;
* it includes the decryption a site's own page performs (the ATP, AO and RG Infosys files, Court Vision, the LTA), for every edition, past and future;
* collect without stopping to ask;
* keep pacing, receipts and raw copies, and back off and report on blocks;
* not covered: others' logins, paywalls, CAPTCHAs.

## The current best model (owner's definition, 8 Oct 2026)

When the owner says "the current best model", it means **a template, not stored files** ([decision](docs/decisions/2026-10-08-current-best-model.md)). It is the model rebuilt on the corrected tables on 8 Oct, as a recipe, built on the day's tables. If no instance built on today's tables is on disk, build one when the task needs it; the decision lists the commands.

1. **The base: the local, non-thinking TabPFN-3.5 on 57 inputs** (closing odds included), from the [offset Elo](docs/decisions/2026-10-06-offset-elo.md) and [surface IOS profile](docs/decisions/2026-10-06-surface-ios-profile.md) decisions.
   * **`ios_points_short` was dropped by the owner on 9 Oct 2026** ([amendment](docs/decisions/2026-10-08-current-best-model.md)). The chain still builds all 58 columns. After it, `src/eda/current_best_model/template_inputs.py --apply <folder>` writes the 57-input list. The frozen reference and the Pinnacle-first instance of 9 Oct are 58-input builds, as built.
   * **Data:** Stage 0 and Stage 1 as their builders write them by default, with the [Slam overrides](docs/decisions/2026-10-06-slam-box-scores.md) and the [corrections of 8 Oct](docs/decisions/2026-10-08-corrupt-data-fixes.md).
   * **Inputs:** built by the documented chain. `src/eda/model_rebuild/run_chain.py` runs it in a sandbox copy, so no study's folder is overwritten.
   * **The odds input is "Pinnacle first", the production rule** (owner, 9 Oct 2026, [decision](docs/decisions/2026-10-09-pinnacle-first-odds-input.md)). After the chain, `src/eda/current_best_model/odds_input.py --apply` replaces the books' average with:
     * Pinnacle's close: tennis-data's to July 2025, cross-checked against OddsTrader's timed copy, then OddsTrader's to 7 Sep 2025;
     * then BetOnline's closing line;
     * the average only where neither book prices a match.

     **Live, at every venue and bet time:** Pinnacle's current line with the margin removed (BetOnline's while Pinnacle has none). **If the missing Pinnacle closes (August 2025 on) are obtained, retrain the model on Pinnacle throughout.**
   * **The indoor input covers every match** (owner's request, 9 Oct 2026, [decision](docs/decisions/2026-10-09-indoor-input.md)): `src/eda/indoor_fill/status.py`, run by `tabpfn_thinking/build_frame.py`.
     * Men: Stage 0's flag, then tennis-data's Court (the 2026 US Open).
     * Women: the WTA's calendar, then tennis-data's Court. The calendar-first order is Claude's recommendation, for the owner to confirm.
     * `--indoor-men-only` rebuilds the old input. The frozen reference and the 9 Oct instances keep it (women missing).
   * **Fit:** season Y trained on 2013..Y−1; 8 estimators, softmax temperature 0.9, pretraining limits ignored; symmetrised; seeds 0–15 averaged (`src/eda/model_rebuild/fits.py`).
   * **The level layer, for men** (owner, 10 Oct 2026, [decision](docs/decisions/2026-10-10-level-evidence-layer.md)): lower-level observations enter the inputs translated and weighted (the level-evidence study's SYS; ITF box scores out; women untouched). Config `data/studies/current_best_model/level_layer/official.json`; every build runs `run_chain.py --prepare-layer` (the opponent strength on its own Stage 0), then each lane with `--layer`; prediction runs resolve it on their own Stage 0. With `LLE_LAYER` unset the hooked builders build the template of before. **Refit each season** walk-forward into a new folder (`relationship.py --method F4`), re-issue the config with the new path and hash, re-run the identity and strength checks; until then later seasons read the last fitted season's parameters. **Accepted lower-level packages** (owner, 10 Oct 2026: the men's 2026 Challenger data, [decision](docs/decisions/2026-10-10-men-2026-challenger-data.md)) are merged into every build's own tables, never the repository's: `run_chain.py --additions` after `--setup`, then lane 0, then `--prepare-layer` (`build_template.sh <sandbox> <out> 1 accepted`); prediction runs merge them themselves.
   * **The lower-level feed** (owner, 13 Oct 2026, [decision](docs/decisions/2026-10-13-lower-level-feed.md)) is merged the same way, after the packages. It holds the levels the history lost in 2026: Sackmann's files ended in June, and Tennis My Life has no ITF, WTA 125 or women's qualifying. Its current snapshot is named in `accepted.json`'s "feeds", and it replaced the men's package.
     * **It updates by itself:** the "lower-level feed" Windows task runs `src/eda/data_gaps_2026/feed.py --run --auto --advance` on Wednesdays, and a snapshot becomes current only when every check passes.
     * **Box scores** enter only from sources that count as Stage 0 does.
     * **The coverage alarm** (`src/eda/data_gaps_2026/coverage.py`) compares every tour and level with one and two years earlier. A newly lost level is added to the feed's scope only after a harm check.
2. **The walk-forward serve-speed adjustment** on its log-odds, with the **28-day speed memory**: logit q = s_tour·η + b̃·`spd_L`.
   * **Coefficients:** refitted each season on 2019..Y−1 from this model's own seeds 0–3, on the speed history that matches the live feed; b̃ shrunk (τ = 0.05).
   * **Speeds:** the live feed's history without the 130 impossible records (`data/studies/serve_speed_tabpfn/live/speed_panel_frozen_corrected.parquet`), plus the ATP's decrypted Stats Centre files of 2018 to Oct 2021 (`…/live/speed_panel_backfilled.parquet`, added 8 Oct at the owner's word); `live_panel.frozen_panel()` returns it.
   * **Code:** `src/eda/serve_speed_tabpfn/adaptive/adjust.py`, every match in mode L.
3. **The five-pattern adjustment, in the daily predictions** (owner, 13 Oct 2026, [decision](docs/decisions/2026-10-13-five-pattern-adjustment.md)): logit q += b·z.
   * **z** is the unpriced-leads study's combined score, with frozen parameters, capped at ±3.5.
   * **b** = 0.0616.
   * **The switch** is `data/studies/unpriced_leads/check_now/adjustment.json`.
   * **Computation:** the engine computes z inside its work tree (`src/eda/unpriced_leads/live_members.py`, `patterns_live.py`).
   * **Output:** in `predictions.csv`, `q_a` is the prediction used, with `q_a_patterns_off` and `q_a_patterns_on` beside it.
   * **Not in `compare.py`'s both stages.**

New features and studies are compared against both stages, never the TabPFN fit alone. The model built on the tables of 30 Sep (`data/studies/surface_rating_race/model/`) is the previous model, kept as evidence.

**The frozen reference** (owner, 8 Oct 2026, [amendment](docs/decisions/2026-10-08-current-best-model.md)). The build of 8 Oct and the tables it was built on are frozen in `data/studies/current_best_model/reference_2026-10-08/`: copied, hashed, read-only, with a [README](data/studies/current_best_model/reference_2026-10-08/README.md) of every data location. It keeps the books' average as its odds input (built before the Pinnacle-first decision); the Pinnacle-first instance of 9 Oct is `data/studies/current_best_model/pinnacle_first_2026-10-09/`.
* **The training data:** the reference's matches plus the matches played since, from the feeds that fed it.
  * **The freeze is about lower-level data** (narrowed by the owner on 9 Oct 2026: "the oct 8 freeze I suggested was more about the data from the challenger series/ITF tour").
    * New, revised or dropped lower-level history never enters by itself, even of past dates: qualifying (tour and Slam), Challengers, ITF, or an unknown level.
    * **Except Tennis My Life's own corrections, drops and backfills** at the levels it fed the reference (men's Challengers, ATP tour and Slam qualifying). The owner decided on 13 Oct 2026 ([decision](docs/decisions/2026-10-13-tml-lower-level-revisions.md)) that they enter by themselves: on bet days at once, and in training at the next rebuild, with no retrain for them alone. `history.py` lists them as `tml_lower`. A held Tennis My Life file is accepted after `src/eda/tml_revisions/held_check.py` lists every change it makes.
    * Main-tour corrections and new official main-tour sources are repairs, decided on the data evidence.
  * `src/eda/current_best_model/history.py` checks any Stage 0 against the reference's and lists every difference.
  * `run_chain.py --setup` refuses a template build only when the lower-level history differs beyond Tennis My Life's own changes.
* **New lower-level data, new inputs and rebuilds are tested as candidates:** a `run_chain.py --setup --candidate` build with its own `--out`, then `./python.sh src/eda/current_best_model/compare.py --candidate <built folder>`. New features go to the pool (the adoption section below).
* **Read the input check first.** An input flagged "uneven" (its scale or level moves in some seasons only) is the warning sign of finding #6.
* **If a candidate harms the model,** its data is ignored, down-weighted or transformed, and compared again. Accepting it is the owner's call.
* **A candidate that shows no harm is recommended** when it is a repair, or new data entering by the route its evidence supports. "Unresolved" is not harm ([adoption by kind of change](docs/decisions/2026-10-09-adoption-by-change-class.md)).
* `reference.py --verify` checks the copies.

## Suggesting that a change be adopted (owner, 9 Oct 2026)

Reason with the [adoption framework](docs/studies/adoption_framework/README.md) ([decision](docs/decisions/2026-10-09-adoption-framework.md); amended the same day by [adoption by kind of change](docs/decisions/2026-10-09-adoption-by-change-class.md)). It gives **guiding principles, not rules**: use them to structure the judgment, and say where you depart from them and why. Accepting a change stays the owner's call. Recommend; don't delegate.
* **Classify the change before reading any result** (framework § 0).
  * The kinds: accretion, repair, expansion, new feature, structural, tuning.
  * The kind sets the direction expected, what decides, and what a before/after comparison is for.
* **Check what the comparison can see.**
  * State the plausible effect against the comparison's resolution (its 95% half-width); `src/eda/current_best_model/adoption_read.py` reads `compare.py`'s output this way.
  * A reading far wider than the effect is "below resolution": it decides nothing and serves as a harm check (default: worse by more than 0.10 mLL with the whole interval below 0).
  * A pre-registered decision rule states how often it adopts a change that works.
* **Below resolution, the kind's direction decides.**
  * More data of a kind already used, a verified fix, or live inputs built as in training: adopt unless the harm check fails.
  * Never "keeping it out costs nothing": name what the status quo forgoes.
* **New features go to the pool, not into the model** (framework § 11).
  * A feature study ends with an admission verdict for the [feature universe](docs/studies/feature_universe/README.md); selection rounds decide by cluster.
  * Only a feature whose effect is big enough to see alone is tested alone.
* **Combine** (framework § 10).
  * Decide recurring kinds once, as policies.
  * After each batch of adoptions, compare the template with the holdback's control: the latest stored instance carrying every structural change, today the Pinnacle-first instance ([errata](docs/decisions/2026-10-09-adoption-by-change-class-errata.md) E1). Across the odds change a comparison resolves only ±0.3.
  * Pool readings by kind in `data/studies/adoption_framework/class_record.csv`.
  * Test complements together.
  * Slices of one comparison are one reading.
* **Name the target first:** the price and hour we would bet at, the matches, the seasons.
  * A reading with the close as an input answers only "does it help beyond the close?".
  * An idea mined from the scored seasons, or the best of many, needs data outside its discovery.
  * A new live feed has to pay for itself.
* **Reporting, not deciding.** Say better or worse when the 95% interval clears 0; otherwise say "unresolved" and give P(better). Never "tie". Verdicts on the declared primary only. The label describes a reading; the bullets above decide.
* **Keep parts apart from stakes.** The edge that sizes bets comes only from matches no choice has seen, at the venue's price, after costs, shrunk. Adoptions made on a kind's direction earn no edge credit.

## Daily predictions: the master notebook (since 11 Oct 2026)

**Run predictions only from `scripts/master_pipeline.ipynb`** ([how it works](docs/studies/master_pipeline/README.md)). Each cell is one call into `src/pipeline/`; the bet-day cells run the daily engine `src/eda/daily_prediction/` ([report](docs/studies/daily_prediction/README.md)): today's tables in a sandbox, the 57 inputs resumed from a saved checkpoint, 16 seeds at 91 prices, stage 2. About 10 minutes a bet day; a new price is read off the stored curve in seconds. Do not build a second prediction path.

| Path | What it is |
|---|---|
| `scripts/master_pipeline.ipynb` | The front door: bet day, data update, rebuild and retrain |
| `src/pipeline/` | The notebook's layer: runs the project's commands and reads their outputs |
| `src/eda/daily_prediction/` | The daily engine (`dp.py`; the notebook calls its `run_day`) |
| `src/eda/prediction_pipeline/` | The engine's plan and the prototypes it imports; not run directly |
| `src/eda/prediction_run/` | The 8 Oct live path: its refresh, live rows and gate are the engine's parts; its full sandbox rebuild (`run.py --build`, about 2 hours) is the reference for proofs, not a way to predict |
| `docs/studies/daily_update_speed/` | A closed study (the speed scoping, the bet-time pricing measurements, the 2027 fix); no code to run |

## Prediction runs (decided 8 Oct 2026)

These rules hold for every prediction, and the daily engine above implements them; the commands below are the 8 Oct path, kept as the reference.

Live inputs must be the inputs the model was trained on ([decision](docs/decisions/2026-10-08-prediction-run-box-scores.md)). 40 of the 57 inputs read the same event's earlier rounds' box scores, and a missing one is skipped silently.

* **Box scores first.** A prediction run starts with `./python.sh src/eda/prediction_run/run.py --refresh --matchups <csv>`. It downloads Tennis My Life, lists the gaps and fills post-freeze WTA gaps from the WTA API. Fills are live only: they never enter the training history, and TML's numbers replace them once TML publishes.
* **Built in the run's sandbox, never in `data/studies/`:** `run.py --setup`, then `run.py --build <folder>`.
  * Upcoming matches enter Stage 0 as rows with a placeholder result (`stage0_build.py --live-rows`, refused outside a sandbox).
  * They go through the unchanged chain.
* **The gate** (`gate.csv`): a live match is marked not to bet when an earlier match of either player, at the event or in the last 14 days, lacks a box score, or when its indoor input is unknown (`--refresh --matchups` refetches the WTA's calendar the women's input reads).
* **The proof:** `src/eda/prediction_run/replay.py` replays one past day's matches as live rows; their inputs must equal the template frame's (9 Oct 2026: 23 of 23, to machine precision; 10 Oct 2026, with the level layer and the accepted package: 23 of 23, bit for bit, compared with `--template <instance> --frame model_frame_chain.parquet`).
* **The history check** lets a match possibly played from 5 Oct on, from the reference's feeds, be completed, corrected or dropped.

## Environment

Use `./python.sh` for the project's `tennis` Conda environment. It fails if absent; do not silently fall back or change the shim. If another interpreter is deliberately used for a self-contained research utility, identify it explicitly. Setup is specified in `environment.yml`.

## Git and working files

No state-mutating Git command unless explicitly requested in the current conversation. The owner commits manually; read-only inspection is allowed. Preserve unrelated changes. Do not delete temporary files mid-session; discuss cleanup before deletion.

| Artifact | Location |
|---|---|
| Source acquisition adapters | `src/ingest/` |
| Study / EDA / scratch Python | `src/eda/` |
| Study tests | `test/<study_name>/` |
| Study reports | `docs/studies/` |
| Study / research process logs | `process_log.md` beside the report ([template](docs/studies/process_log_template.md)) |
| Study evidence / outputs | `data/studies/<study_name>/` |
| External-source research | `docs/research/` |
| Historical inherited suggestions | `docs/research/legacy-one-shot/` |
| Explicit project decisions | `docs/decisions/` |
| Notebooks only | `scripts/` |
| Predictions / actual bets | `predictions/` / `data/betting_history/` |

## Research discipline

Separate observed data, provider claims, inference, unknowns, and suggestions. Record source URLs, access dates, dataset versions, and relevant licensing limitations. Tournament start dates are not match timestamps; reconstructable match outcomes are not historical executable market prices. Preserve missing and ambiguous joins. For private or paywalled sources, distinguish documented access from payloads actually audited.

Inherited code is an experimental scaffold. Its existence or passing tests does not approve the system. Use the sibling UFC project for organizational and technical references, assessing tennis applicability without importing production decisions by default.

## Process logs (owner, 9 Oct 2026)

Every study and research note keeps a **process log** by default ([decision](docs/decisions/2026-10-09-study-process-logs.md); [template](docs/studies/process_log_template.md); worked example: [tour pooling's audit trail](docs/studies/tour_pooling/audit_trail.md)). It is written for a future reviewer, perhaps a more capable model, who may find a flaw in the reasoning or the process and re-design the study.
* **Where:** `process_log.md` beside the README, in `docs/studies/<study>/` or `docs/research/<topic>/`.
  * The README stays the owner's report.
  * Chat-only answers need none.
* **Open it before the first substantive step:** the owner's request verbatim, the interpretation acted on, the readings set aside, and the plan.
* **Write it while working, not at the end.**
  * Correct by adding, never by rewriting.
  * After a context summary, note it and re-read the log.
* **For each choice that could move a conclusion, record what results had been seen.** Also log:
  * every look at results, failure, dead end and variant tried;
  * the owner's instructions and subagent briefs, verbatim;
  * the session id(s).
* **Finish it before reporting:**
  * the claims mapped to their evidence;
  * threats to validity, and where a flaw would hide;
  * what a re-design would do;
  * a reviewer checklist and reproduction.
* **Scale it to the work:** a few lines per section for a short lookup.
* **Existing studies are not retrofitted.** A resumed study starts its log at the resumption.

## Feature timing (decided 5 Oct 2026)

A result may reach another match's features only if it surely finished before that match could start ([decision](docs/decisions/2026-10-05-match-timing.md)).

* **Safe by construction:** features that follow each player's own matches in order (Elo, Glicko, the opponent-adjusted profiles, workload, age).
* **Must use the leak-proof clock, never the tournament start date:** anything that combines different players' results, such as ratings solved together (IOS), smoothed ratings (TrueSkill Through Time), batch fits and statistics of a field.

How to apply it:

* **Clock:** `data/studies/match_timing/timing.parquet`, built by `src/eda/match_timing/timing.py`.
  * A result counts from `lf + 1`, the day after its latest possible finish.
  * A match reads the state as of `es`, its earliest possible start.
  * An undated match gets a cautious window, never a guessed day.
* **Leak-proof versions:** IOS is `src/eda/match_timing/ios_time.py` (`run_timed`, built by `rebuild.py`); TrueSkill Through Time is `ttt_pass_timed`.
* **Leaking, not to be used as they are:** the weekly `src/eda/ufc_ideas/stageB_ios.py`, `ttt_pass`, Bradley–Terry, MESR and the SOS revaluation.
* **Checking new work:** run `src/eda/match_timing/probe.py` on any new cross-player feature. It flips every result after a cut day; nothing about a match that finished before the cut may move.
* **The Thinking fit of 5 Oct 2026** (TabPFN-3.5-Thinking, closing odds + 53 inputs; the best model before the 6–7 Oct decisions) has used leak-proof IOS since 5 Oct 2026, and its edge is unchanged ([report](docs/studies/tabpfn_leakproof/README.md)). Build on its leak-proof inputs (`data/studies/tabpfn_leakproof/upload/`), not on the IOS columns of `tabpfn_thinking`.
* **New data:** scrapers keep every match-time field their source sends. After new results or dates arrive, run `./python.sh src/eda/match_timing/refresh.py`.

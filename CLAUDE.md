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

**Bookmakers' odds below the tour level** (Challenger, WTA 125, ITF; Pinnacle's among them where listed) **download daily from TennisExplorer** (owner, 22 Oct 2026; job `lower_odds`, [cadence amendment](docs/decisions/2026-10-06-download-cadence.md); work package P11, [report](docs/studies/gap_downloads/README.md#bookmaker-odds-below-the-250s-work-package-p11)). Not a model input.
* **Its Pinnacle prices are late pre-match prices, not closes** (P11's forward-capture test, done 24 Oct 2026). On 22-23 Oct the site's last Pinnacle price equalled Pinnacle's own close on 148 of the 197 lower-level matches where it showed one. Its record stops a median 3.6 hours before the start, so it misses late moves.
* **Open, the owner's decision:** whether to record Pinnacle's own site every 10 minutes as a standing job, the only route to every true lower-level close. Claude recommends it if lower-level markets may be bet; a close not recorded on the day is lost.

## The current best model (owner's definition, 8 Oct 2026)

When the owner says "the current best model", it means **a template, not stored files** ([decision](docs/decisions/2026-10-08-current-best-model.md)). It is the model rebuilt on the corrected tables on 8 Oct, as a recipe, built on the day's tables. If no instance built on today's tables is on disk, build one when the task needs it; the decision lists the commands.

1. **The base: the local, non-thinking TabPFN-3.5 on 57 inputs** (closing odds included), from the [offset Elo](docs/decisions/2026-10-06-offset-elo.md) and [surface IOS profile](docs/decisions/2026-10-06-surface-ios-profile.md) decisions.
   * **`ios_points_short` was dropped by the owner on 9 Oct 2026** ([amendment](docs/decisions/2026-10-08-current-best-model.md)). The chain still builds all 58 columns. After it, `src/eda/current_best_model/template_inputs.py --apply <folder>` writes the 57-input list. The frozen reference and the Pinnacle-first instance of 9 Oct are 58-input builds, as built.
   * **Data:** Stage 0 and Stage 1 as their builders write them by default, with the [Slam overrides](docs/decisions/2026-10-06-slam-box-scores.md) and the [corrections of 8 Oct](docs/decisions/2026-10-08-corrupt-data-fixes.md), and since 22 Oct the [source reconciliation's repairs](docs/decisions/2026-10-22-source-reconciliation-repairs.md). Those are 201 more rows in `row_corrections.csv`, and `event_corrections.csv`: one edition's level or surface, which Stage 0's builder applies.
   * **Revisions decided for the next retrain** (owner, 22 Oct 2026: a retrain must be "aware of these intended revisions to the model, not simply adding the latest data"). `data/studies/current_best_model/pending_at_retrain.json` lists each one with its check (`src/eda/current_best_model/pending.py --show`).
     * They are already in the decided tables, so prediction runs read them at once; training takes them at the next retrain, built on the shared tables after B6.
     * `tp.retrain()` refuses to start while one is missing from the shared tables. `retrain.sh` checks the built instance before its fits and marks them applied after the switch.
     * A retrain run by hand must run `pending.py --check` on its Stage 0 first.
     * Add any future revision of this kind to the register.
   * **Inputs:** built by the documented chain. `src/eda/model_rebuild/run_chain.py` runs it in a sandbox copy, so no study's folder is overwritten.
   * **The odds input is "Pinnacle first", the production rule** (owner, 9 Oct 2026, [decision](docs/decisions/2026-10-09-pinnacle-first-odds-input.md)). After the chain, `src/eda/current_best_model/odds_input.py --apply` replaces the books' average with:
     * Pinnacle's close: tennis-data's to July 2025, cross-checked against OddsTrader's timed copy, then OddsTrader's to 7 Sep 2025;
     * **from 1 Nov 2025, TennisExplorer's time-stamped Pinnacle close**, its last price before the match. Not used:
       * untimed prices;
       * a price far from the site's other books;
       * a price contradicted by both BetOnline and the average when those two agree (the site's own errors: 4 in 2026);
     * then BetOnline's closing line;
     * the average only where neither book prices a match;
     * **when OddsTrader and tennis-data are mirror images, OddsTrader wins**: tennis-data's row is the one with the players' prices swapped.

     The step keeps OddsTrader's and TennisExplorer's tables current itself. It refuses a frame OddsTrader's do not cover, and a month from Nov 2025 that TennisExplorer prices under 75%.

     **Live, at every venue and bet time:** Pinnacle's current line with the margin removed (BetOnline's while Pinnacle has none).
   * **The closing line from 2025 on changes at the next retrain** (owner, 21 Oct 2026, [amendment](docs/decisions/2026-10-09-pinnacle-first-odds-input.md)). The two bold rules above are that change: rule `2026-10-21`, the step's default, so the next retrain or template build applies them by itself.
     * **The instances built before 21 Oct 2026, the live one included, keep the rule they were built with** (`--rule 2026-10-09` reproduces it). They carry BetOnline from August 2025 and the mirrored prices on 4 matches.
     * **The owner asked for a test build compared with the current model, then deferred it** ("DO NOT DO THE TEST YET", 21 Oct 2026). Don't run it until the owner asks.
     * **August – October 2025 stay as they were** (OddsTrader's Pinnacle to 7 Sep, then BetOnline). TennisExplorer's Pinnacle there has no times and equals tennis-data's, which stopped being Pinnacle's close on 24 Jul 2025 ([research](docs/research/pinnacle-gap/README.md)).
     * **TennisExplorer's pages download daily** (`src/ingest/scheduled.py`, job `pinnacle_closes`; adapter `src/ingest/tennisexplorer.py`).
   * **The indoor input covers every match** (owner's request, 9 Oct 2026, [decision](docs/decisions/2026-10-09-indoor-input.md)): `src/eda/indoor_fill/status.py`, run by `tabpfn_thinking/build_frame.py`.
     * Men: Stage 0's flag, then tennis-data's Court (the 2026 US Open).
     * Women: the WTA's calendar, then tennis-data's Court. The calendar-first order is Claude's recommendation, for the owner to confirm.
     * `--indoor-men-only` rebuilds the old input. The frozen reference and the 9 Oct instances keep it (women missing).
   * **Fit:** season Y trained on 2013..Y−1; 8 estimators, softmax temperature 0.9, pretraining limits ignored; symmetrised; seeds 0–15 averaged (`src/eda/model_rebuild/fits.py`).
     * **Live, the rows grow at retrains the owner calls** (owner, 20 Oct 2026, [amendment](docs/decisions/2026-10-09-adoption-by-change-class.md)): a retrain's instance trains its live season-Y fit on 2013..Y−1 plus every season-Y frame match whose result counts by its cut-off (lf + 1 ≤ the cut-off), recorded in the instance; Thinking takes the same rows. Never at a prediction run. Backtests, harm checks and every check on unseen matches keep season Y on 2013..Y−1. A timer at A1, A4 and on the bet sheet shows the time since the cut-off.
   * **The level layer, for men** (owner, 10 Oct 2026, [decision](docs/decisions/2026-10-10-level-evidence-layer.md)): lower-level observations enter the inputs translated and weighted (the level-evidence study's SYS; ITF box scores out; women untouched). Config `data/studies/current_best_model/level_layer/official.json`; every build runs `run_chain.py --prepare-layer` (the opponent strength on its own Stage 0), then each lane with `--layer`; prediction runs resolve it on their own Stage 0. With `LLE_LAYER` unset the hooked builders build the template of before. **Refit each season** walk-forward into a new folder (`relationship.py --method F4`), re-issue the config with the new path and hash, re-run the identity and strength checks; until then later seasons read the last fitted season's parameters. **Accepted lower-level packages** (owner, 10 Oct 2026: the men's 2026 Challenger data, [decision](docs/decisions/2026-10-10-men-2026-challenger-data.md)) are merged into every build's own tables, never the repository's: `run_chain.py --additions` after `--setup`, then lane 0, then `--prepare-layer` (`build_template.sh <sandbox> <out> 1 accepted`); prediction runs merge them themselves.
   * **The lower-level feed** (owner, 13 Oct 2026, [decision](docs/decisions/2026-10-13-lower-level-feed.md)) is merged the same way, after the packages. It holds the levels the history lost in 2026: Sackmann's files ended in June, and Tennis My Life has no ITF, WTA 125 or women's qualifying. Its current snapshot is named in `accepted.json`'s "feeds", and it replaced the men's package.
     * **It updates by itself:** the "lower-level feed" Windows task runs `src/eda/data_gaps_2026/feed.py --run --auto --advance` on Wednesdays, and a snapshot becomes current only when every check passes.
     * **Box scores** enter only from sources that count as Stage 0 does.
     * **The coverage alarm** (`src/eda/data_gaps_2026/coverage.py`) compares every tour and level with one and two years earlier. A newly lost level is added to the feed's scope only after a harm check.
2. **The walk-forward serve-speed adjustment** on its log-odds, with the **28-day speed memory**: logit q = s_tour·η + b̃·`spd_L`.
   * **Coefficients:** refitted each season on 2019..Y−1 from this model's own seeds 0–3, on the speed history that matches the live feed; b̃ shrunk (τ = 0.05).
     * **Live, they grow with each retrain** (owner, 20 Oct 2026, same amendment): 2019..Y−1 plus the season-Y matches the retrain admits, from the walk-forward forecasts (the season-Y fit on 2013..Y−1). Conditions: the speed table extended to every season-Y men's match and checked equal where it overlaps; no harm in the check; both versions logged on the first runs.
     * **The live feed is the daily collector's from 8 Oct 2026:** matches from that day use `spd_L_D`, earlier ones (replays) `spd_L_B` (owner, 14 Oct 2026, [amendment](docs/decisions/2026-10-08-current-best-model.md)).
     * **In sync with the model:** the daily engine refits them whenever the frame, the input list, the seeds 0–3 fits, their TabPFN or the speed history change, and refuses a live fit made with another TabPFN, weights, settings or input list (`src/eda/daily_prediction/dp_predict.py`).
   * **Speeds:** the live feed's history without the 130 impossible records (`data/studies/serve_speed_tabpfn/live/speed_panel_frozen_corrected.parquet`), plus the ATP's decrypted Stats Centre files of 2018 to Oct 2021 (`…/live/speed_panel_backfilled.parquet`, added 8 Oct at the owner's word); `live_panel.frozen_panel()` returns it.
     * **Since 22 Oct 2026** ([decision](docs/decisions/2026-10-22-source-reconciliation-repairs.md)), it returns the repaired copy (`…/live/speed_panel_repaired.parquet`). There, 576 published averages that the match's point record contradicts by more than 5 km/h take the point mean.
     * Stage 2's column on it is `data/studies/source_reconciliation/applied/speed_columns_repaired.parquet` (`live_panel.decided_column()`).
     * A retrain writes it into the new instance's own speed table (`stage2_speed_columns.parquet`). The instance in use keeps its own table until then.
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
  * **Lower-level data: only data that changes coverage waits for a test** (the 8 Oct freeze, narrowed to lower-level data by the owner on 9 Oct 2026; since 14 Oct 2026, [decision](docs/decisions/2026-10-14-lower-level-gap-fills.md), data that fills holes enters by itself). Lower-level means qualifying (tour and Slam), Challengers, ITF, or an unknown level.
    * **Enters by itself:** on bet days at once, in training at the next rebuild, with no retrain for it alone; the next rebuild's harm check covers it.
      * **Tennis My Life's own corrections, drops and backfills** at the levels it fed the reference (men's Challengers, ATP tour and Slam qualifying; owner, 13 Oct 2026, [decision](docs/decisions/2026-10-13-tml-lower-level-revisions.md)). `history.py` lists them as `tml_lower`. A held Tennis My Life file is accepted after `src/eda/tml_revisions/held_check.py` lists every change it makes.
      * **Other sources' gap fills** (owner, 14 Oct 2026): built by the candidate builder (`src/eda/lower_level_evidence/candidate_stage0.py`) into an accepted package (`additions.py`) and registered without asking, when both hold:
        * per tour and level, the source's box scores equal the history's on at least 98% of the matches both score (at least 30 of them). Today's tables, with every decided repair, decide; the frozen copy's reading is recorded beside them;
        * per tour, level and season it touches (today's tables), the history already holds a box score for at least half of the played matches (for new matches: at least as many matches as it adds), **or** the fill brings the season's box-score share closer to its level's median over the other seasons from 2013 (a season catching up with its neighbours; a level empty in most seasons, such as ITF before 2025, still fails).

        `src/eda/tennislive_box_fill/conditions.py` reads both for box scores; `src/eda/men_lower_level_fill/conditions_new.py` reads the second for added matches (what the merge would add, plus a list of same-pair meetings within 14 days to look at for duplicates). Record the numbers in the package's report, and tell the owner. The packages so far: `tennislive_box_fill` (233), `tennislive_box_fill_men_gsq` (184, men's 2018 Slam qualifying) and `men_lower_level_fill` (4,376 men's Challenger, Challenger-qualifying and ITF results to the feed's start, results only; 16 Oct 2026).
      * **The weekly lower-level feed** (13 Oct 2026, above).
    * **Still tested first, as a candidate:** lower-level data that fails either condition; a level or seasons the history does not cover (ITF box scores before 2025, the risk of finding #6); a level Stage 0 never held; another source's revision of a box score the history already holds.
    * Main-tour corrections and new official main-tour sources are repairs, decided on the data evidence.
  * `src/eda/current_best_model/history.py` checks any Stage 0 against the reference's and lists every difference; a registered package's matches count as "accepted".
  * `run_chain.py --setup` refuses a template build only when the lower-level history differs beyond what is accepted: Tennis My Life's own changes, the registered packages and the feed.
* **Lower-level data that changes coverage, new inputs and rebuilds are tested as candidates:** a `run_chain.py --setup --candidate` build with its own `--out`, then `./python.sh src/eda/current_best_model/compare.py --candidate <built folder>`. New features go to the pool (the adoption section below).
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

## Held-out matches and the look ledger (owner, 29 Oct 2026)

**The untouched test of the live model's edge counts the matches played from 19 Oct 2026** ([decision](docs/decisions/2026-10-29-holdout-soft-rule.md)).
* It and the other protected periods are in [the register](docs/holdouts/README.md). Each one protects a single question.
* **They are soft rules, the owner's to override** ("Not a hard lock"). The design is Claude's.

What agents do:
* **Before measuring what a period protects on its matches, offer the owner the choice, with your recommendation.**
  * The choice: stop the window the day before the period, or use the recent matches and spend part of it.
  * Skip the question when the instruction already names the matches.
  * For a new model (women's, props, ITF), also ask whether it should get a clean period of its own, and from when.
  * `./python.sh src/eda/holdouts/ledger.py check --from <day> --to <day> --tours <atp|wta|both> --levels <tour|lower|all>` lists the periods a window touches.
* **Log every read of recent results in the ledger, without being asked**, whether or not anything changes (`ledger.py add`).
  * A decision that rests on logged reads is logged too (`ledger.py decide`).
  * A read is anything computed from the results (who won, the score, the box score) of matches since the earliest open period's start, today 29 Jul 2026.
  * It counts when set against a model, a feature, a rule, a price or an idea, whichever model the work is for.
* **Not a read:**
  * training and prediction runs under the decided recipe;
  * data checks between sources, and counts;
  * prices without results;
  * watching bet-day results.
* **Logged anyway:**
  * a change made because of bet-day results, as a decision;
  * a retrain's harm check, by whoever runs or reports the retrain.
* **Side models (Claude's recommendation, for the owner to confirm):**
  * The women's model counts under H1, since it predicts the same winners. Its reads of H1 are asked first.
  * Props and ITF work reads recent matches without asking, logged, on two conditions: it never grades the live model's forecasts on H1, and nothing it chooses enters the live model untested.
* `ledger.py status` shows how much each period has been used.

## Daily predictions: the master notebook (since 11 Oct 2026)

**Run predictions only from `scripts/master_pipeline.ipynb`** ([how it works](docs/studies/master_pipeline/README.md)). Each cell is one call into `src/pipeline/`; the bet-day cells run the daily engine `src/eda/daily_prediction/` ([report](docs/studies/daily_prediction/README.md)): today's tables in a sandbox, the 57 inputs resumed from a saved checkpoint, 16 seeds at 91 prices, stage 2. About 10 minutes a bet day; a new price is read off the stored curve in seconds. Do not build a second prediction path.

**The live model is named in one place: the notebook's selection** (`data/studies/master_pipeline/selected_instance.json`, written by `use_instance()` or a retrain's switch; STATUS shows it as "LIVE MODEL"). The daily engine and the notebook read it and have no default (owner's request, 22 Oct 2026): with no selection they refuse to predict, and a bet sheet blocks every match of a live run made with another model. Documents may record when a model went live, never which one is live now.

**Women's matches are switched off for the bet day** (owner, 28 Oct 2026, [decision](docs/decisions/2026-10-28-women-switched-off.md): "temporarily disable womens matches ... im not betting on them, and their matches constantly cause errors"; the design is Claude's). The switch is `BET_TOURS = ("atp",)` in `src/pipeline/config.py`; `("atp", "wta")` brings them back. STATUS shows it as "BET DAY (A1-A8)".
* A2 leaves a women's listing out before any linking.
* A3 to A5b see men's matches only. A sheet of a live run made before the switch leaves out its women's predictions and says so.
* A7 and A8 show the men's figures, and their files keep every prediction.
* Downloads, builds, the replay proof and training keep both tours: the model trains on both.

**One bad match never holds up the others** (owner, 28 Oct 2026, [decision](docs/decisions/2026-10-28-one-bad-match-left-out.md): "while you fix a single row it shouldnt hold up the whole pipeline" and "Be sure to mention the match that was left out and that there was an error in one row clearly and loudly, however still give all the other predictions"; the design is Claude's).
* A match whose own row a step cannot handle is left out with its reason, and the step goes on with the others: A2 (one listing), A3's check (it no longer raises; A4 leaves the flagged rows out), A3b, the daily engine's matchups, prices and tables steps, A5b. A7 (one run) and A8 (one sheet's record) do the same.
* At A4's tables step the run builds its data again without the match, so the others are predicted as if the CSV had not listed it. The run's check runs right after Stage 0 and again after the additions step. If the first check finds the match, the rebuild is one Stage 0 build (about 2 minutes). If only the second does, the additions' merge is redone too (5–11 minutes). Its players' earlier rounds stay.
* Loud: `!!!` lines where it happens and at the end of A4; on the bet sheet, red lines above everything and a NOT PREDICTED row whose reason starts "ERROR in its row". The run's record is `left_out.json` in its folder.
* Still stopping: a run with every match left out, a failure that names no match, and replays and the 8 Oct path, which keep every refusal.

**The bet sheet's market chance is the posted price's, its margin included** (owner, 24 Oct 2026, [decision](docs/decisions/2026-10-24-market-chance-with-vig.md): "Market chance should be market chance INCLUDING VIG ON THE SIDE WE ARE TRYING TO BET"): 1 ÷ the decimal odds of the player shown. Its edge is the model's chance minus it, so a positive edge is a positive expected profit. The model's input stays margin-free.

**TabPFN-3.5-Thinking beside the local model** (owner, 20 Oct 2026, [decision](docs/decisions/2026-10-20-thinking-beside-local.md)).
* **The switch:** `MODEL = "tabpfn35_thinking"` with `SPEND_TOKENS = True`. It adds one paid Thinking call per run (`run_day --thinking --spend-tokens`, `dp_thinking.py`). A new instance's first such run also makes its paid season fit.
* **The rule:** Thinking's chance is the API's own (seed 0) plus stage 2's serve-speed term, never its calibration slope (owner, the evening of 20 Oct 2026: "should still move with the serve speed numbers ... just not the calibration"). The prediction used is the two models' chances averaged 50/50 in log-odds, with the five-pattern adjustment added after.
* **The bet sheet:** US odds only.

**The qualifying of the 250s and above is bet, with the live model unchanged** (owner, 22 Oct 2026, [decision](docs/decisions/2026-10-22-qualifying-bets.md)): ATP and WTA 250s, 500s, 1000s and Slams (Stage 0's T250–GS with `qualifying`; Stage 4's TQ and GSQ). Challenger, WTA 125 and ITF qualifying stay out.
* **Inputs as the qualifying study built them** (`dp_context`): level TQ 6 / GSQ 7, round order Q1–Q3, best of 5 where a men's Slam qualifying round records 5.
* **A2 places each match** (`src/pipeline/qualifying.py`):
  * the event from Tennis My Life's rows of the edition, else built from its previous edition (every round 1; all women's qualifying, which Tennis My Life lacks);
  * the round from TennisLive's results, checked against Tennis My Life's, never read from Tennis My Life's silence;
  * the main draw's start (`event_main_date`). Stage 0 dates an event by its main draw's first date (rule C05); before the main draw is played, it would otherwise take the first qualifying day and move 19 inputs.
* **The proof:** a qualifying replay (`dp.py run_day --replay-round Q1 --replay-frame …`) reproduces the training inputs bit for bit, given that date.
* **The five-pattern adjustment on qualifying:** tested on 22 Oct 2026 at the owner's request ([report](docs/studies/qualifying_targets/README.md), follow-up 2): +0.28 mLL [−0.07, +0.63], unresolved; the harm check passes, so it stays on. **Thinking is untested on qualifying**; it applies as on the main draw.
* **Stakes are the main draw's** (owner, later on 22 Oct 2026: "Stakes should be the same as main").
* **A qualifier's earlier rounds come from TennisLive until their source publishes them** (owner, 24 Oct 2026: "we need to get this data" and "patch it so this doesnt happen again"; [decision](docs/decisions/2026-10-24-earlier-rounds-from-tennislive.md); the design is Claude's).
  * **Why:** on the day, a round 2 or 3's round 1 was never in the data, so the gate blocked it. Tennis My Life's qualifying file lags by days; women's qualifying waits for the weekly feed.
  * **How:** A2 writes each player's earlier wins at the event to `<matchups>_earlier.csv`. Each row has its score and its match page's box score, with service games derived from the score and the first server (36 of 36 equal to Tennis My Life's). The run adds them as live rows with their results (`src/eda/prediction_run/earlier_rounds.py`), dated like a live match.
  * **Live only:** Tennis My Life's or the feed's row replaces a fill once published. A round that cannot be filled stays blocked, with its reason; one without a box score needs the 1-point edge.
  * **The proof:** `dp.py run_day --replay-earlier tennislive` (master pipeline process log, Part 14): 5 of 8 matches bit for bit outside the surface IOS; the rest is three single points where the sources differ; the forecast within 0.24 points.
  * **Since 25 Oct 2026, the main draw too:** a main-draw match's qualifiers and lucky losers get every qualifying match of theirs at the event the same way (`live._qualifiers`; process log, Part 17). Without it, a round 1 silently lacked them and a round 2 was blocked. TennisLive's spellings of a name ("Chak Lam Coleman Wong") are read as the one Stage 0 player they fit (`earlier_rounds.same_player`).
  * **A women's main-draw round 1 on its first day stays unpredicted** (Tennis My Life holds no row of the event yet; owner, 27 Oct 2026: "dont built predictions for womens rounds 1, we arent betting women yet").

| Path | What it is |
|---|---|
| `scripts/master_pipeline.ipynb` | The front door: bet day, data update, rebuild and retrain |
| `src/pipeline/` | The notebook's layer: runs the project's commands and reads their outputs |
| `predictions/clv/` | The closing-line ledger (A8, `tp.clv_ledger`; an agent's design, 25 Oct 2026): every bet sheet's predictions against Pinnacle's close, rebuilt from the records; a check on prices, not the model |
| `src/eda/daily_prediction/` | The daily engine (`dp.py`; the notebook calls its `run_day`) |
| `src/eda/prediction_pipeline/` | The engine's plan and the prototypes it imports; not run directly |
| `src/eda/prediction_run/` | The 8 Oct live path: its refresh, live rows and gate are the engine's parts; its full sandbox rebuild (`run.py --build`, about 2 hours) is the reference for proofs, not a way to predict |
| `docs/studies/daily_update_speed/` | A closed study (the speed scoping, the bet-time pricing measurements, the 2027 fix); no code to run |

## Production integrity (owner, 22 Oct 2026)

**The plan of record for keeping production in sync** ([decision](docs/decisions/2026-10-22-production-integrity-plan.md); how it is carried out: the master pipeline's process log, Part 10; each step's status is in the decision).
* **What is live is read from disk, never from a document.** A document may record when something went live, not which one is live now; a study describes its own time, never production.
* **Before changing the live path** (the notebook layer, the daily engine, the scheduled downloads, the decided tables): read STATUS's verdict and the to-do list, and claim the shared files you will write. **After:** run the check the change needs (a change to the engine's inputs: the replay proof, whose receipt is what "verified" means) and update the to-do list.
* **Mark every new rule as the owner's words or an agent's choice.** An agent's reading that changes picks is shown to the owner, with and without it, before it goes live.
* **The notebook's kernel refuses to run code older than the files on disk** (an agent's choice, 23 Oct 2026; `src/pipeline/__init__.py`, the process log's Part 11). An edit to any file of `src/` the owner's kernel has imported stops the owner's next cell until the kernel is restarted.

## Prediction runs (decided 8 Oct 2026)

These rules hold for every prediction, and the daily engine above implements them; the commands below are the 8 Oct path, kept as the reference.

Live inputs must be the inputs the model was trained on ([decision](docs/decisions/2026-10-08-prediction-run-box-scores.md)). 40 of the 57 inputs read the same event's earlier rounds' box scores, and a missing one is skipped silently.

* **Box scores first.** A prediction run starts with `./python.sh src/eda/prediction_run/run.py --refresh --matchups <csv>`. It downloads Tennis My Life, lists the gaps and fills post-freeze gaps: women's tour matches from the WTA API, and since 14 Oct 2026 men's tour-level main-draw matches from the ATP Stats Centre's keystats (`fills.fill_atp`, read through the daily speed collector's files and client; equal to TML's counts on 164 of 164 Shanghai 2026 player rows; not the qualifying, where the ATP's first serves differ from TML's). Fills are live only: they never enter the training history, and TML's numbers replace them once TML publishes.
* **Built in the run's sandbox, never in `data/studies/`:** `run.py --setup`, then `run.py --build <folder>`.
  * Upcoming matches enter Stage 0 as rows with a placeholder result (`stage0_build.py --live-rows`, refused outside a sandbox).
  * They go through the unchanged chain.
  * **A main-draw live row is dated by its main draw's first day**, as Stage 0 dates a played event (owner, 27 Oct 2026: "switch the date fix on"; [decision](docs/decisions/2026-10-27-main-draw-live-date.md); the design is Claude's). It takes the earliest day known: Tennis My Life's main-draw rows, and each listed match by A2's day (TennisLive's main-draw starts and the listing's, in the venue's time zone), else its own UK day (`live_rows.main_draw_date`). The event's earliest Tennis My Life row, a qualifying one, had dated 129 of 148 men's matches early; Tennis My Life's main-draw rows alone would have dated 62 late. `LIVE_MAIN_DRAW_DATE=0` reproduces the runs before.
* **The gate** (`gate.csv`; replaced by the owner on 14 Oct 2026, [decision](docs/decisions/2026-10-14-box-score-gate.md)): every earlier match of either player, at the event or in the last 14 days, is checked for a box score, and a missing one never blocks.
  * A gap of a kind the training rows nearly always hold (main tour, Challenger / WTA 125, qualifying above ITF level) makes a bet need a 1-point edge: the forecast moved 1 point against the side must still be +EV at the odds (`gate.EDGE_BAR`, applied in `src/pipeline/diagnostics.py`).
  * A gap of a kind they mostly lack (team events, ITF) is only noted.
  * Still marked not to bet: a qualifier with no qualifying match in the data, or an unknown indoor input (`--refresh --matchups` refetches the WTA's calendar the women's input reads).
  * Since 22 Oct 2026, also a qualifying round 2 or 3 whose player has no match of the round before in the data: the result is missing, not only the box score. A woman's waits for the weekly lower-level feed. Since 24 Oct 2026, A2 fills such rounds from TennisLive (above); the block stays only for a round it could not fill.
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
| Protected periods and the look ledger | `docs/holdouts/` (`register.csv`, `looks.csv`) |
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

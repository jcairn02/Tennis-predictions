# Tour-level qualifying as prediction targets: pre-registration

Written 22 Oct 2026, 07:50 PDT, before any fit of any arm below and before any outcome-based score of any model on a
qualifying match. Frozen with its SHA-256 recorded in the process log (§ 3) before the first fit. Later changes go in the
process log as deviations; this file is not edited.

## The questions (the owner's words of 22 Oct 2026, on the recommendation of 16 Oct)

1. **Market:** how accurate are the closing prices on tour-level qualifying, and does BetOnline's close match Pinnacle's
   there as it does on main draws?
2. **Model:** does the model beat the closing price on qualifying, at the bookmaker's own odds?
3. **Main draw:** do the main-draw predictions stay as good when qualifying matches join the training rows?

## The kind of change (adoption framework § 0), fixed before any result

* Qualifying matches as **training rows** of the current model: an **expansion** (a new level). For the main draw the
  before/after comparison is a harm check; adopted unless the harm rule fires; accepting is the owner's call.
* Qualifying matches as **betting targets**: a new population. Its edge must be measured on matches no choice has seen,
  at the venue's price; nothing is adopted on a kind's direction.

## Data

* **Tables:** the active instance `template_2026-10-21b` (selected 21 Oct 2026, 15:55) and its build tree
  `C:/Users/zerom/tnr_tpl1021`: its Stage 0 (the accepted packages and the feed snapshot 20261021 merged), Stage 4, the
  Stage D tables, the leak-proof table, the Elo pieces, the surface IOS features and the match clock. The instance's
  frame (`model_frame.parquet`: Pinnacle-first odds input, 57 inputs) is used unchanged for its main-draw rows.
* **Qualifying rows:** the tree's Stage 0 matches with `qualifying` true and `level` in GS, T1000, T500, T250 (Stage 4's
  groups TQ and GSQ), ATP and WTA, status completed or retired, not flagged non-standard format, seasons 2018–2026.
* **Inputs:** the instance's 57 inputs, built with the instance's own code (the tree's `src/`) on the tree's tables.
  **Gate:** on every main-draw row of the instance's chain frame, each of its 58 inputs must equal the rebuilt value
  (missing cells included); otherwise stop before any fit.
  * Context of qualifying rows: level code TQ 6, GSQ 7 (the event-levels study's codes; the model's are GS 0 to T250 4);
    round = Stage 0's round order (Q1 1, Q2 2, Q3 3); best of 3, or 5 where Stage 0 records 5 for men's Slam
    qualifying; indoor by the indoor rule (`indoor_fill/status.py`); tour and surface as recorded.
* **The price** (the odds input, and the close scored against):
  * OddsTrader's Pinnacle last line (book 20); else BetOnline's (book 8); else no price, and the match is left out
    (as main-draw matches without a price are).
  * Each line must be coherent (overround 1.00–1.20) and stamped no later than 30 minutes after the listed start (the
    odds-sources rules). Margin removed proportionally.
  * **Linking:** OddsTrader's played singles events to Stage 0's qualifying matches, on the same tour, by the
    "surname span + first initial" forms of both players (the sharp benchmark's `td_variants`), with OddsTrader's listed
    start day from the match clock's earliest start minus 1 day to its latest finish plus 1 day. Nearest day first, one
    event per match and one match per event; a tie leaves both out.
  * **The Pinnacle download:** every book's lines for the linked qualifying events (`src.ingest.oddstrader
    --books-eids`), paced, with receipts and raw copies.

## Arms

TabPFN-3.5 local with the instance's settings (8 estimators, softmax temperature 0.9, pretraining limits ignored),
symmetrised, seeds 0–3. Season Y in 2019–2026 is fitted on seasons up to Y − 1 only.

* **M1, pooled (primary):** the instance's main-draw rows of 2013 .. Y − 1 plus the priced qualifying rows of
  2018 .. Y − 1.
* **M0, today's model (secondary):** the instance's main-draw rows of 2013 .. Y − 1 only, i.e. its own fits' training
  rows. **Check:** its main-draw predictions reproduce the instance's stored seed 0–3 fits.
* **M2, separate (secondary):** the priced qualifying rows of 2018 .. Y − 1 only.

Every arm queries every season-Y priced qualifying row; M0 and M1 also query every season-Y main-draw row. Each query
row is asked as stored and with A and B swapped.

## Stages (the decided recipe, fitted per population)

* **Stage 1:** the seed mean's log-odds with one calibration slope per tour, fitted walk-forward on the same
  population's matches of 2019 .. Y − 1, debut seasons out (`compare.walk_forward`).
* **Stage 2:** stage 1 plus b · spd_L (men; women 0), with b fitted alongside the slopes and shrunk (τ = 0.05).
  * spd_L = the 28-day speed memory from the instance's speed builder (`in_season_retrain/speed_extend.py`, spd_L_B)
    for each match.
  * A match without a reading gets 0 (the "zero" rule).
* **Not applied:** the five-pattern adjustment (not in `compare.py`'s two stages).

## Readings

Seasons scored 2020–2026 (2019 only calibrates), debut seasons out, qualifying results as the tree's Stage 0 holds them.

**Primary.** M1, both stages, both tours, on the priced qualifying matches:
* the measure: 1000 × mean(LL(calibrated close) − LL(M1)), milli-log-loss per match; positive = M1 better than the
  close;
* the calibrated close: the close with one slope per tour fitted walk-forward on the same population
  (`compare.close_forecast`);
* the interval: 95%, from 4-week blocks plus the seeds' variance (`compare.paired`, unmatched);
* the verdict: "better" if the interval lies above 0, "worse" if below, else "unresolved" with P(better).

**Secondary** (flags, no verdict words):
* M1 by tour, stage 1 alone, Slam vs tour qualifying, 2020–2024 vs 2025–2026, each season, and against the raw close.
* M0 and M2: the same readings, plus M1 − M0 and M1 − M2 paired.
* **Betting** (the decision reading): each arm's stage-2 forecast against the closing odds with the margin.
  * The bet: the side with EV = q · d − 1 > 0, if any; 1 unit flat.
  * At Pinnacle's close (the matches Pinnacle priced) and at BetOnline's close (the matches BetOnline priced),
    separately.
  * Reported: bets, ROI = profit / stake, and a 95% interval from 2,000 bootstrap draws of 4-week blocks.
  * Sensitivity: EV ≥ 0.02.
  * This is a measured return on unseen matches, before any shrinkage.
* **Market** (question 1), on the qualifying and main-draw matches of 2019–2025 that have both closes:
  * the log loss of each close (proportional margin removal; the power method as a check);
  * BetOnline − Pinnacle, paired, with 4-week block intervals;
  * each book's margin (overround − 1);
  * each close's calibration slope per tour (the result regressed on the close's log-odds);
  * qualifying against main draw throughout.

**Main-draw harm check (M1).** M1's main-draw forecasts against the instance's own:
* the recipe: seeds 0–3, stage 2 refitted on each model's own forecasts, the "zero" speed rule;
* the scorer: the in-season retrain's harm check's;
* test seasons 2020–2026;
* harm = worse by more than 0.10 mLL with the whole 95% interval below 0.

## What decides (the recommendation rule, stated in advance)

* **Betting qualifying:**
  * **The primary reading is "better" and the ROI at BetOnline's close is above 0:** recommend wiring the bet-day
    pipeline for qualifying, then a small-stake live trial with the edge shrunk.
  * **Unresolved with P(better) ≥ 0.8:** a lead. Recommend paper predictions on qualifying from now on before any money.
  * **Otherwise:** no betting on qualifying with this model; report the process suspects.
* **Choosing M0 or M2 over M1** on these seasons would be the best of three. Such a choice needs confirmation on matches
  played after this freeze.
* **M1 as the model for the main draw:** decided by the harm rule (an expansion, adopted unless harm); the owner's call.

## Stop rules

* The input gate fails: stop and fix before any fit.
* M0 does not reproduce the instance's fits beyond floating-point noise: find out why before scoring.
* Fewer than 80% of the 2019–2025 qualifying matches link to an OddsTrader event: find out why before going on.

## What this cannot show

* **Bet-time prices:** only the close is held; live bets would be at earlier prices.
* **Women's 2026 qualifying from the feed:** about half have box scores, so the inputs that read box scores are often
  missing there.
* **Polymarket:** prices there are not tested.

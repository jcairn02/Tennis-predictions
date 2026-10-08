# Feature interactions: brief for the agent team

6 October 2026. Every agent in this study reads this file first. It is the shared description of the model, the data, the rules and what is already known. Research evidence, not a decision.

## The owner's request

Flesh out reasonable **interactions** between features of the feature universe of the best-performing local, non-thinking TabPFN-3.5 model, including features the model does not use yet. Reason about which **match-level statistics interact**, not only which are predictive by themselves. Research what other modellers have published in the past few years. Build the universe of reasonable interactions, narrow it like a cone to the best candidates, explore them with EDA, then test them in the model. **2025–2026 is the test data: no EDA or design choice may look at it.**

## The current best model

| | |
|---|---|
| Model | Local TabPFN-3.5 (open checkpoint `tabpfn-v3.5-20260909`, the API's non-thinking weights) on this PC's RTX 5090: 8 estimators, softmax temperature 0.9, `ignore_pretraining_limits`, seeds 0–2. Runner: `src/eda/surface_rating_race/local_fits.py`; settings: `src/eda/tabpfn_local/runtime.py` |
| Population | ATP and WTA main-tour singles (Grand Slams, Tour Finals, 1000s, 500s, 250s), completed or retired, with closing odds, 2013–2026: 63,737 matches (39,918 in 2013–2021, 23,819 in 2022–2026). The men's 2018 season has no odds file |
| Design | Walk-forward: season Y is trained on 2013 … Y−1 and predicted in both orientations (A and B swapped), the two symmetrised, the seeds averaged. Then **one logistic slope per tour on the log-odds** (calibration; the raw local model is over-confident, slopes ≈ 0.89 men, 0.96 women), refitted each season on all earlier out-of-sample seasons from 2019 |
| Scoring | Log loss; gains in milli-log-loss (mLL), paired, 95% intervals clustered over four-week blocks of tournament dates (`src/eda/tabpfn_thinking/common.py`: `ll`, `compare`, `blocks`); seed variance added for arm-vs-arm tests. Matches in a player's debut season are left out of scored comparisons |
| Edge | The 54-input predecessor beats the recalibrated closing price by +1.30 [+0.65, +1.94] mLL, both tours, 2022–2026 (men +1.57 [+0.82, +2.33], women +1.00, a tie). Higher = better. The two 6 Oct swaps that made the 58-input model each tie at the close |

**The 58 inputs** (`data/studies/surface_rating_race/model/model_frame.parquet`, columns `in_<name>`; list in `model_inputs.json`):

* `odds_logit`: the de-vigged average closing odds' log-odds that A wins (tennis-data.co.uk).
* Ratings and points aggregates: `ratings_iid` (serve/return ratings through the iid point model), `elo_games`, `elo_overall`, `elo_surf_offset` (offset Elo), `adjperf_tpw_2w`, `ios_points_short`, `points_52w`.
* Load and age: `sets_14d`, `age`, `age_sq`; surface switching pairs `surf_season_a/b`, `surf_layoff_a/b`.
* Two-week opponent-adjusted statistics profile (`form_<s>` for ace, df, first_in, first_won, second_won, hold, bp_saved, bp_faced_pg, brk, bp_conv, rpw_first, rpw_second; `formdef_<s>` for ace, df, first_in, bp_faced_pg).
* Long-memory IOS profile **built per surface**: offence `iosO_<s>`, defence `iosD_<s>` and matchup product `prod_<s>` (A's offence × B's lack of defence minus the reverse) for ace, df, first_in, first_won, second_won, hold, bp_saved.
* Context: `tour`, `surface`, `level`, `indoor` (men only), `best_of`, `round`.

**The representation matters for interactions.** Side A is random. Every player input is an **A − B difference** (negated when A and B swap), except the two surface-switch pairs (exchanged when they swap) and the six context columns (unchanged). Consequences:

* The model never sees either player's **level** separately, so it cannot form anything that depends on A's and B's values other than through their difference: the sum of both players' serve strength, A's serve against B's return separately from B's serve against A's return, one player's age times the same player's load, and so on. The `prod_<s>` columns are the only cross-player products it has.
* Symmetry algebra. P(A wins) − ½ must change sign when A and B swap. A product of an antisymmetric input (a difference) and a symmetric one (context, or a sum over both players) is antisymmetric and can enter directly: it **modulates** a difference by the match's character. A product of two differences is symmetric and can only act as context. A per-player term f(A's own inputs) − f(B's own inputs) is antisymmetric for any f.

## What is already known (do not rediscover; build on it)

* **TabPFN's learned adjustment to the price is almost additive.** On the paid Thinking fit, about 65% of the adjustment's variance is linear in the inputs, 96% additive, and interactions explain about 2%. Match context (surface, level, best of, round) carries nothing. The adjustment leans most on the long-memory IOS profile, then load/age/surface familiarity, then the two-week profile ([report](../tabpfn_thinking/README.md)).
* Free flexible models do not reproduce TabPFN's men's gain: boosting with interactions, a spline GAM, ridge and TabICL all score +0.1 to +0.3 over the price against TabPFN's +1.57.
* **Ratings and win/loss information are priced in.** Elo variants, TrueSkill Through Time, Glicko, surface Elo, surface IOS: real information without the odds, nothing detectable given the close ([surface IOS](../surface_ios/README.md), [Elo pieces](../surface_elo_pieces/README.md), [rating race](../surface_rating_race/README.md), [market anchoring](../market_anchoring/README.md)).
* **Shot-level statistics** (rally length, how points end, serve speed, net play, ball tracking) add nothing to the close; the men's recent serve speed (+0.24 mLL, 2022–2026) is the one direction to watch ([shot level](../shot_level/README.md)).
* Stacking a market-free forecast onto the price fails; the price must stay inside the model ([meta stack](../meta_stack/README.md)). Calibration was worth more than any input tested.
* The owner's thesis: the edge lives in **per-statistic offence/defence profiles and point-level data**, not in win/loss ratings, which are controls. Rank results by the gain on the odds, never by the gain on Elo. A null against the close is a process flaw to hunt, never proof the market cannot be beaten.

## Data available (pointers; the data cartographer maps it in detail)

* Stage 0 (`data/studies/predictability_diagnostic/stage0_matches.parquet`, `stage0_match_players.parquet`): every match at every level since the 1990s/2010, with per-player box scores (aces, double faults, serve points, first serves in and won, second serves won, service games, break points saved and faced, tiebreaks), rank and points, seed, entry, age, **height, hand, country**, minutes, score, round, best of, indoor, surface, draw size. **Rebuilt at 17:07 on 6 Oct 2026; some match ids changed** (`data/studies/data_continuity/rebuilds/2026-10-07T0005Z/id_map.csv`; the pre-rebuild copies, consistent with the model frame, are under `.../replaced/`).
* Per-player surface IOS ratings, A and B separately (`data/studies/surface_ios/surface_features.parquet`: `cur_O_<s>_a`, `srf_O_eff_<s>_a`, …).
* Leak-proof per-player and IOS inputs (`data/studies/match_timing/perplayer_features.parquet`, `ios_features.parquet`, `leakproof_features.parquet`), the match clock (`timing.parquet`), TrueSkill Through Time, Glicko, Bradley–Terry and other study outputs under `data/studies/`.
* Point-by-point records (6.2 million points from eight sources, `data/studies/shot_level/`), official Slam and WTA feeds, Hawk-Eye tracking for some Slams, serve speeds: partial coverage.
* Odds: tennis-data.co.uk closing averages (and Pinnacle, Betfair for some years); Polymarket price paths for 2025–2026.

## Rules every agent follows

1. **No 2025–2026 data** in exploration, EDA, tuning or any choice. Discovery uses seasons up to 2021; 2022–2024 replicates. 2025–2026 is opened once, for the final pre-registered test.
2. **The match clock** ([decision](../../decisions/2026-10-05-match-timing.md)). Features that follow each player's own matches in order are safe by construction. Anything that combines different players' results (ratings solved together, smoothed ratings, field statistics, court-speed estimates from other matches) must use the leak-proof clock in `data/studies/match_timing/timing.parquet` (a result counts from the day after its latest possible finish; a match reads the state as of its earliest possible start) and pass `src/eda/match_timing/probe.py`.
3. **No paid API calls.** Only the orchestrator runs TabPFN fits, on the local GPU, which other sessions share.
4. **No Git commands that change state; delete nothing.** Write only inside this study's folders: `docs/studies/feature_interactions/`, `src/eda/feature_interactions/`, `data/studies/feature_interactions/`, `test/feature_interactions/`. Run Python through `./python.sh`. Other sessions are rebuilding shared tables today: read them, never write them.
5. **Separate** observed (measured here), provider or author claims, inference, and suggestion. Cite sources with URLs and access dates.
6. **Every score carries its direction**: "log loss, lower is better" or "gain, higher is better", who wins, and "tie" when the 95% interval spans zero.

## Idea template (brainstormers, and anyone proposing a candidate)

| Field | Content |
|---|---|
| ID, name | short and specific |
| Mechanism | the tennis or market story, in a few sentences |
| Why the price might miss it | the market-orthogonality argument; the test is against the closing odds |
| Type | **S** symmetric match character × a difference (modulation); **W** within-player nonlinear, f(A) − f(B); **X** cross-player matchup, g(A offence, B defence) − g(B offence, A defence); **C** composition through a structural model (point → game → set → match); **U** uncertainty or reliability weighting; **M** market-state interaction (odds level, favourite/longshot) |
| Formula | explicit, with its swap behaviour checked |
| Data | tables and columns; timing class (safe by construction, or needs the leak-proof clock) |
| Why the model cannot already do it | which of the 58 inputs come close and why they are not enough (differences hide levels, missing input, etc.) |
| Expected effect | sign, rough size, where (tour, surface, level, format) |
| Kill test | the EDA result that would discard it |

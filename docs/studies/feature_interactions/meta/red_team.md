# Red team (S3): B-INJ, hidden physical impairment

7 October 2026, before the final pre-registration is hashed. The finalist was re-implemented from its written specification and attacked. This is research evidence, not a decision. No 2025–2026 result was read. The one look at results (2014–2024) is ledger row 28.

## Verdict: pass with caveats

B-INJ survives.
* Independent code reproduces the frozen column exactly.
* It has no leak, and its orientation is right.
* It is not a proxy for the price, the model's inputs or player identity.
* Its screen signal does not depend on the pandemic seasons.

**It fails as a description.** The column does not measure an *unplanned* layoff. Its "longer than the field's norm" condition never binds, so the winter off-season is the main "layoff" it sees. The test of the frozen column stays valid, but the claim must be reworded (section 4).

## 1. Independent re-implementation

**Code.**
* `src/eda/feature_interactions/redteam/binj_redo.py` and `redo_run.py` were written from f26's docstring and f20's shared definitions, without f26's functions.
  * After the first comparison failed, I read f26's code once, at lines 44–80 (the week/band helper and `layoffs`), to find E's unstated fallback.
  * The inj44 and I-045 readings below were found by testing variants against the frozen values, without reading f26's I-044 or I-045 code.
* They reuse only `history.long_table()`: the raw facts and each player's order.
* Sides A and B are assigned **by player id** (Stage 0's player_a_id), not by the history's side label.
* The frozen values come from `frozen_dump.py`, which runs f26's prepare and `screen_batch.evaluate` as `g5_build` does. Its x reproduces the frozen hash.

**Result on all 55,144 model-frame rows of 2013–2024.**
* x matches to a maximum |difference| of **8.6e-12**: no row above 1e-9 and no NaN mismatch.
* The raw member differences match: I-043 to 1.8e-15, I-044 exactly, I-045 to 1.2e-13.
* U, inj and the Elo at the return match exactly.

Three readings had to be taken from the frozen code, because the docstring is silent or says something else. None of them changes the screened column. Each must be written into the pre-registration.

| Point | Docstring | Frozen builder | Literal reading would give | Who is wrong |
|---|---|---|---|---|
| E's cells | "same tour, week of the year and ranking band in the three previous seasons" | falls back from tour × week × band to tour × week, then to tour; a cell needs ≥ 60 player-rows; no prior (a missing E means no return is possible, so no 2010 row can ever be a return) | E missing in many cells; U differs on 11,316 rows | the docstring, which is incomplete; the builder is reasonable |
| inj44 (I-044) | "inj or entry PR" | inj, or entry PR **or SR** | 6 model rows differ (WTA 2022–2023, SR entries) | the docstring. The WTA codes its protected ranking SR, and I-043's own formula says "PR or SR"; the builder's reading is the substantive one |
| I-045's "match sequence" | "slope by least squares on the match sequence, shrunk by τ²/(τ² + 12/(n³ − n))" | position = the row's index in the player's whole sequence (walkovers and matches without a box score keep their slots); n = the number of residuals | positions 0 … n−1 of the residuals: 3,042 model rows differ, raw ΔDec by ≤ 0.028 | neither (the text is ambiguous). With gaps, 12/(n³ − n) overstates the slope's variance, so those windows are slightly over-shrunk |

Two more conventions are not in f26's docstring but are documented in f20 (shared), and my code matched them as written:
* each member is clipped at the 99th percentile of |member| and divided by its population SD, both on 2014–2021 model rows, and a missing member counts 0 in the sum;
* e_pre's tour mean pools sides A and B over the 2014–2021 panel rows.

## 2. Attacks, result-free

### 2.1 Leaks: none found

* **Cut probe on the frozen builder** (`redteam/binj_probe.py`, following `match_timing/probe.py`).
  * For each cut day D, every history match that surely started after D (es > D) is either reversed (the winner flag and both box scores exchanged, retired_self recomputed) or removed.
  * Every model match that surely finished by D (lf ≤ D) must then keep all 14 per-player prepare columns and the 3 raw member differences (tolerance 1e-9).
  * Six cuts (6 Jul 2016, 23 Jan 2019, 29 Jan 2020, 9 Sep 2020, 6 Jul 2022, 24 Jan 2024), both modes: **0 earlier rows moved**, in every column, over 18,353 to 50,496 earlier model matches.
  * The test has power: later rows moved (I-045 on 4,346 to 34,241 rows under reversal; every later row under removal).
* **Own match.** The busiest model-match day of 2014, 2017, 2020, 2021, 2023 and 2024 (425 matches; players with two matches that day left out) had its own results reversed: **0 own values moved**, while 1,074 to 12,040 later I-045 values did.
* **The field table's clock.** For every season Y from 2011 to 2024, the latest source finish lf + 1 ≤ T_Y ≤ the earliest start of any row of Y, and no es is missing. So a row's E reads only results with lf + 1 ≤ its own start.
* **The current row's own facts.** In the independent code, no member reads row i's score, minutes, box score, status or winner:
  * gap and E use the clock;
  * inj uses the row before the return;
  * I-045 uses the rows before i.
  That code reproduces the frozen values exactly.
* **The 2026 build** reproduces 2013–2024 exactly (ledger row 24). That amounts to a removal probe at 20 Dec 2024.
* **Not covered.** The upstream tables (the surface-Elo pieces behind e_pre, and the clock's obs, es and lf) are read, not rebuilt. Elo is pre-match and in the decision's safe class.

### 2.2 Orientation: correct

* The history's side labels equal Stage 0's player_a_id and player_b_id on all 55,144 rows.
  * The batch's swap test exchanges the prepare outputs, so it could not catch a wrong assignment inside prepare.
  * Assigning by player id closes that gap.
* The model frame's A is Stage 0's A:
  * `in_age` correlates 1.0000 with age_A − age_B;
  * `in_elo_overall` = (R_A − R_B) × 0.0058 (ln 10/400), correlation 1.0000.
* Swapping A and B negates x exactly (the largest |x_swapped + x| is 0).

### 2.3 Proxies: not a proxy (2014–2024 model rows)

* **The inputs.** The largest |r| with the 58 inputs are sets_14d +0.21, elo_games −0.14, elo_overall −0.14 and surf_layoff_a −0.13.
  * R² on all 58 inputs: 0.103 (2014–2021) and 0.120 (2022–2024).
  * I-043 alone: 0.24 and 0.23.
* **The forecasts.** r with the current best's log-odds is −0.06, with the price −0.07, and with the model's adjustment (η − price) −0.04.
* **Player identity.** 1,546 players carry rust. The top 10 hold 7% of the rust mass and the top 50 hold 25%.
* **Where rust is high** (mean per player-row):
  * players ranked below 250 or unranked: 0.93, against 0.22–0.28 in the ranked bands;
  * PR or SR entries: 1.15 against 0.27 (built in through ψ);
  * by level: 250s 0.35 and Slams 0.33, against 1000s 0.13 and the Finals 0.05;
  * by tour: alike (0.27 and 0.28).
* **By season.**
  * The SD of x is 1.49–1.60 in 2014–2018, 1.76–1.88 in 2019 and in 2021–2024, and 2.29 in 2020.
  * The members' SDs stay at 0.84–1.14, except in 2020 (I-043 1.50, I-044 1.33).
  * So x's rise from 2019 is the sum of three roughly independent members, not a break in one of them.

### 2.4 The pandemic break

* **E does not see the break.**
  * In 2021–2023, the weeks of the 2020 restart (weeks 31–37) have an E only 0.4–1.2 days above the rest of the year.
  * The reason: the field mean is dominated by within-event gaps of a day or two.
  * So every player at the 2020 restart is a "return" with U ≈ log(1 + 150 − 12) ≈ 4.9.
* **Rows touched.**

  | Season | Model rows where either player's latest return was the 2020 break | Share of that season's Σx² |
  |---|---|---|
  | 2020 | 54% | 58% |
  | 2021 | 14% | 10% |
  | 2022 | 5% | 2% |

* 2020–2021 hold 14.1% of the 2014–2024 rows and 18.8% of the Σx².
* The look in section 3 settles it: the signal stands without these seasons.

### 2.5 Coverage and artefacts

**The return definition is "a gap of 42 days or more". The "unplanned" part is inert.**
* E is a mean over every player-row, so within-event gaps dominate it: its 1st percentile is 3.9 days, its median 12.2 and its 99th percentile 25.5. In weeks 0–1 it averages 22.3 days.
* "gap > E" therefore blocks only 7 of the 106,296 returns of 2013–2024.
* The ranking bands do nothing either (E is 6.7–7.8 days in the ranked bands and 13.3 in "other").

**So the off-season is the main layoff.** For the 2014–2024 model player-rows, the latest return falls into these classes:

| Latest return | Player-rows | Rust mass | Σx² (the side with more rust) |
|---|---|---|---|
| off-season (last match Sep–Dec, return Dec–Feb, gap ≤ 120 days) | 79.6% | 60.0% | 53.7% |
| other breaks of ≤ 180 days | 14.3% | 22.3% | 29.1% |
| long breaks (> 180 days) | 3.0% | 8.2% | 12.6% |
| the 2020 break | 3.1% | 9.5% | 4.6% |

* **Reading (inference).** The screen mostly found "rust after a break of six weeks or more, chiefly the winter break, fading over the first matches". The declared direction holds: the rustier player does worse than the forecast. It is not established as an injury signal:
  * inj applies to only 6% of returns (5,338 retirements and 1,015 walkovers given just before the break);
  * I-044 is null on its own.
* **Why.** The math audit asked for "E[gap] from the calendar alone". The builder's walk-forward E is leak-free, but it measures the gap of an average player-row, not the gap at the start of an event, so it cannot reach 42 days. This is a property of the frozen specification, not a builder error, and it cannot change now.

**I-044 is a sparse spike of ±9.7.**
* It is non-zero on 1.2% of rows, so the 99th-percentile clip falls inside its non-zero values: 81% of them are clipped to one magnitude (z44 = ±9.67).
* The screen's own clip of x (at |x| = 6.04) cuts 70% of those rows again.
* These rows (1.2%) carry **17% of the screen-scaled Σx²**, that is, of the test's leverage. The member is null on its own (z +0.48, ledger row 23).
* With b̂ = 0.0421, the nudge on those rows averages 0.15 logits, against 0.03 elsewhere.
* If I-044 carries no effect, the expected cost is about 0.03 mLL of log loss (second-order approximation; p from the current best), out of the nudge's whole quadratic size of 0.17 mLL.
* It dilutes power. It does not bias the test.

**2026 coverage (features only).**
* I-043 is missing exactly where a player's age is missing in the pre-rebuild Stage 0: 101 of 3,488 rows in 2026 (94 WTA, 7 ATP), 2 in 2025, 2 in 2024 and 3 in 2013–2024.
* A missing member counts 0, so on those rows x drops the rust term of both players.

**Walkovers and retirements before a break.**
* inj reads the row just before the return.
* 219 returns follow a walkover the player received; inj is then 0.
* 475 returns are walkover rows themselves, but no model row's latest return is one.

**Lower-level coverage.**
* History rows rise in two steps:
  * WTA ITF: about 30–36k per season to 2018, then 55–71k from 2019;
  * ATP Challengers: about 9k to 2015, then 15–20k from 2016.
* Matches missing from the history would create fake layoffs before those years.
* An indicator: among weighted model rows (n ≤ 2), the share whose rank improved by more than 10% during the "layoff" is 9–12% (ATP) and 12–17% (WTA). It did not fall after the expansions.
* Fake layoffs cannot be ruled out, but nothing suggests that they drive the column.

**I-045's support moves with box-score coverage.**
* Slam box scores cover 55–89% of rows in 2014–2018 and 99% from 2019; 2015's main-tour rows only 62–71%.
* I-045 is non-zero on 77–94% of rows, depending on the season.

**The test years, features only** (no outcome read; checkpoint 1 §6.3 item 7).
* Member SDs relative to 2014–2021: I-043 0.99 (2025) and 1.16 (2026); I-044 0.69 and 1.09; I-045 1.10 and 0.98.
* Non-zero shares are as in 2022–2024. There is no large shift.

## 3. The one look (ledger row 28): the signal without 2020–2021

The look used the screen's own machinery: `screen_batch.screen_one`, then `screen.run`, on the model base with n_p1 = 0. (The batch's widening for B-INJ was 1.0, so n_p1 = 0 changes nothing.) The script is `redteam/binj_look.py`.

**Keys.**
* z is positive in the declared direction: the less rusty side does better than the current best expects.
* Gains are out-of-sample milli-log-loss; positive means the column lowers the log loss (better). A tie means the 95% interval spans 0.

| Rows | z₁ (discovery) | z₂ (2022–2024) | joint z | Gain, discovery | Gain, 2022–2024 |
|---|---|---|---|---|---|
| 2014–2024 as screened (reproduces the published row) | +3.51 (2014–2021) | +1.93 | +3.99 | +0.19 [−0.03, +0.42], tie | +0.02 [−0.31, +0.36], tie |
| **2020 and 2021 removed** | **+2.90** (2014–2019) | +1.93 | **+3.48** | +0.15 [−0.10, +0.40], tie | +0.04 [−0.29, +0.36], tie |

* **The finding stands without the pandemic seasons.** The filter (z₁ > 1) and the replication (z₂ > 0.67) still pass.
* A uniform effect would have cut z₁ to about 3.1 when a fifth of the discovery rows went. The observed 2.90 means 2020–2021 were somewhat stronger than average, but not necessary.
* This is exploratory and cannot change a claim or the bundle.

## 4. What the final pre-registration must state

1. **B-INJ exactly as frozen**, including the three readings of section 1:
   * E's fallback chain, its 60-row cells and its missing prior;
   * inj44 = inj or entry PR or SR;
   * I-045's positions in the player's whole sequence, with n = the residuals counted;
   * f20's standardisation: the 99th-percentile clip and the population SD on 2014–2021, with a missing member counting 0.

   Also cite the independent reproduction (8.6e-12 on 2013–2024). Correct the docstring's wording in the report, not in the frozen builder.
2. **The claim's wording.**
   * Name: "rust after a break of six weeks or more (mostly the winter off-season), fading over the matches since the return", in the declared direction.
   * Not: "unplanned layoff" or "hidden physical impairment". The "gap > E" condition blocks 7 of 106,296 returns, and inj and I-044 carry little.
   * A positive final test supports the rust reading only.
3. **The data version and the missing ages.**
   * On the pre-rebuild Stage 0, I-043 is missing on 101 of the 3,488 rows of 2026 (94 WTA), where an age is missing. On those rows x drops the rust term for both players.
   * If the live rebuilt Stage 0 is used instead (via `id_map.csv`), rerun the 2013–2024 reproduction check on it and report the change in coverage.
4. **Power.**
   * I-044's rows are 1.2% of matches but carry 17% of the screen-scaled leverage, and that member is null on its own.
   * The expectation and power statement should say that this dilutes the test (about 0.03 mLL of expected cost if I-044 is null).
   * Nudges on those rows reach 0.17 logits: b̂ = 0.0421 times the largest screen-scaled |x|, 4.08 (the clip of 6.04 divided by the SD of 1.48).
5. **The pandemic.** Report that the screen signal stands without 2020–2021 (z₁ +2.90, joint +3.48; ledger row 28).
6. **Frozen constants.** These must stay frozen:
   * the member clips and SDs;
   * the 2014–2021 Elo tour mean;
   * I-045's τ² (0.0039);
   * E's table rules.

   The 2026 build's reproduction check covers them.
7. **Suggested descriptive secondaries** (not gates; the orchestrator's choice, made before the hash):
   * x's coefficient on matches whose larger rust comes from an off-season return, and on the rest;
   * I-043 alone. The plan's "each finalist alone" does not separate the members.

## Files

* Scripts in `src/eda/feature_interactions/redteam/`:
  * `binj_redo.py` and `redo_run.py`: the re-implementation and the comparison;
  * `frozen_dump.py`: the frozen values;
  * `binj_probe.py`: the leak probes;
  * `binj_attack.py`: orientation, timing, proxies, the pandemic break, artefacts, classes and coverage;
  * `binj_look.py`: the one look.
* Outputs in `data/studies/feature_interactions/redteam/`:
  * `frozen_binj_2024.*` and `redo_binj_2024.parquet`;
  * `probe.json`;
  * `attack_*.json`;
  * `look_ex2020_2021.json`.

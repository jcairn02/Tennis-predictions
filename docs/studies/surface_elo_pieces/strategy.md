# Elo by surface: strategy for representing the pieces (draft for audit)

6 October 2026 · Research plan and design-years evidence; not a model, production or betting decision.

**Key for every score below.** Log loss: lower is better. Gains are in milli-log-loss (mLL): +1 means the named model's
average log loss is 0.001 lower than its base, so **positive = the named model is better**. Brackets are paired 95%
intervals clustered in four-week blocks of tournament dates. A range that spans 0 is a **tie**.

## 1. The suggestion under test

The owner's two items, verbatim:

> 5. Give the model the pieces, not the 30% blend. That means the overall rating, the surface-only rating, and each
> player's match count on the surface; a surface rating built on 5 matches is noise. Tennis Abstract blends 50/50, our
> tuning chose 30% and TrueSkill Through Time 35%. The right weight depends on how much evidence each player has, and
> only the pieces let the model learn that.
>
> 6. Fix how surface switches are represented. "First matches on this surface" goes in as player A minus player B, so
> it vanishes when both players are new to the surface, as in the first grass week. Add both players' counts, days
> since each last played on the surface, and last season's form on that surface. Early season is where the no-odds
> model trails the market most: 31–34 milli-log-loss on early clay and hard courts, against 10 later in the hard-court
> season.

The model to improve is the best 2026 model: the closing odds' log-odds plus 53 pre-match inputs, the 22 IOS ones
leak-proof ([tabpfn_leakproof](../tabpfn_leakproof/README.md)). Its Elo input `elo_logit` is Stage 1's surface-blended
Elo, 0.7 × overall + 0.3 × surface for men and 0.75 / 0.25 for women; each surface rating starts at 1500 and moves only
on that surface. Its `surface_first` input is A's flag minus B's, where the flag means fewer than 3 played matches on
the surface this calendar season.

## 2. Design discipline

* Every representation choice below uses **seasons 2010–2021 only**. Constants are tuned on 2013–2018 and checked on
  2019–2021. The test seasons 2022–2026 stay unseen for the new inputs.
* The baseline's 53 inputs were chosen by earlier studies after their 2022–2026 results were seen. That caveat belongs
  to the baseline and applies equally to every arm.
* Code: `src/eda/surface_elo_pieces/`. Outputs: `data/studies/surface_elo_pieces/`. Tests:
  `test/surface_elo_pieces/` (10 pass).

## 3. The claims, checked

| Claim | Verdict | Evidence (design years) |
|---|---|---|
| "A surface rating built on 5 matches is noise" | **Wrong in kind.** It is biased, and the bias is informative | The surface rating sits 445–459 Elo points *below* the overall rating at ≤ 5 surface matches (men), 252 below at 20–40 and 18 below at 160+ (`evidence_bias.csv`). Players with ≤ 5 career matches on a surface win 6.9 points (men) and 2.4 (women) less often than overall Elo expects; against the market they are +0.5 and +0.4, so the market prices it (`evidence_priced.csv`) |
| "Tennis Abstract 50/50, our tuning 30%, TTT 35%" | **Correct for men.** Women: ours 25%, TTT 30% | `stage1_baselines_summary.json`; [rating systems](../rating_systems/README.md) |
| "The right weight depends on how much evidence each player has" | **Direction right, effect absent for this rating.** | Where both players have many surface matches, the best single weight is higher: men 0.25 at 11–20 matches rising to 0.45 above 80, women 0.25 to 0.35. Above 20 matches the gain over the fixed weight is only 0.1–0.8 mLL (`evidence_weight_by_bin.csv`). But a per-player weight w·n/(n + k) on Stage 1's surface rating tunes to k = 0; every k > 0 is worse by 0.6–1.8 mLL (men) and 0.4–1.0 (women) on 2013–2018 (`evidence_k_cost.csv`). Shrinking the low-count rating throws away the inexperience penalty. Re-anchoring the surface rating at the overall rating also loses: men −0.51 [−0.82, −0.20] on all evaluation levels, 2019–2021, worse |
| "Only the pieces let the model learn that" | **Not in a linear model.** A rating that weights evidence itself does better | Without the odds, forward-chained 2016–2021, main tour, against the fixed blend: overall + surface-only rating **+0.10 [−0.23, +0.42] men, tie**; adding career counts −0.83 [−1.76, +0.11], tie. The surface-offset Elo (section 4): **+2.16 [+0.58, +3.73] men, +1.44 [+0.10, +2.77] women, both better** (`evidence_no_odds.csv`) |
| "First matches on this surface vanishes when both are new, as in the first grass week" | **Confirmed.** | In the opening week of each tour's grass season, both players are flagged in 61% (men) and 62% (women) of main-tour matches, so A − B = 0. Over all design-year matches the flag difference is zero in 92% of men's hard, 80% of clay and 65% of grass matches (`evidence_switch_*.csv`). The stored flag is reproduced exactly (agreement 1.000) |
| "Add both counts, days since, last season's form" | **Informative without the odds; tie with them** | Without the odds, beyond the offset Elo: this season's counts add about 2.1 mLL (men) and 3.7 (women); layoff about 1.7 and 1.9; last season's form about 0.2 and −0.1. With the odds, linear, forward-chained 2016–2021: men −0.05 [−0.21, +0.11], women +0.40 [−0.07, +0.87], **ties** (`evidence_with_odds.csv`) |
| "No-odds model trails the market by 31–34 mLL early in clay and hard seasons, 10 later" | **Quoted correctly** from [market anchoring](../market_anchoring/README.md) §6.4 (hard early −34.0, clay early −31.2, hard rest −9.8; 36-input market-free model against the average price) | It describes a **no-odds** model. The model under test holds the odds, so this gap is not one it has |

## 4. What the evidence says about Elo by surface

**Bias, not noise** (men, main tour, player-rows, 2013–2021; Elo points, surface rating minus overall):

| Surface matches | ≤ 0 | 1–2 | 3–5 | 6–10 | 11–20 | 21–40 | 41–80 | 81–160 | 160+ |
|---|---|---|---|---|---|---|---|---|---|
| Stage 1 surface rating (starts at 1500) | −445 | −455 | −459 | −424 | −346 | −252 | −138 | −50 | −18 |
| Re-anchored at the overall rating | 0 | −145 | −196 | −188 | −133 | −73 | −50 | −36 | −19 |
| Surface offset (section below) | 0 | −2 | −5 | −7 | −2 | +11 | +21 | +43 | +65 |

Players with fewer than 20 surface matches are 31% (men) and 34% (women) of grass player-rows, 1% of clay and 0.4% of
hard. Women's carpet (54 matches) is all low-evidence.

**The surface-offset Elo** (`pieces.py`, mode `offset`). The overall rating is Stage 1's, unchanged. Each player has a
surface offset that:

* starts at 0;
* moves only on that surface, by the surprise of the combined forecast expected(R_A + D_A, R_B + D_B);
* uses K(n) = kd0 / (n + kd_off)^kd_shape on the surface count, tuned on 2013–2018 evaluation matches: men 80, 10, 0.6;
  women 80, 20, 0.6.

The tuning valley is flat and its best lies inside the grid. With no evidence the offset is 0, so it is unbiased; with
evidence it grows, so it weighs evidence by construction.

**Elo-only forecasts, 2019–2021** (each variant recalibrated by one slope fitted on 2013–2018; gain over Stage 1's
blend; positive = better). From `evidence_elo_only.csv`:

| Variant | Men, main tour | Men, all evaluation levels | Women, main tour | Women, all evaluation levels |
|---|---|---|---|---|
| Overall alone | −4.84 [−7.24, −2.44] worse | −4.49 worse | −2.74 [−4.60, −0.88] worse | −3.47 worse |
| Evidence-weighted blend | tunes to the fixed blend (0) | 0 | 0 | 0 |
| Re-anchored blend | −0.00, tie | −0.51 [−0.82, −0.20] worse | −0.55 [−1.08, −0.02] worse | −0.24, tie |
| **Surface offset** | **+4.50 [+2.06, +6.94] better** | **+1.57 [+0.31, +2.83] better** | +1.81 [−0.99, +4.61] tie | +1.44 [−0.27, +3.16] tie |

**Given the odds** (logistic, forward-chained 2016–2021, main tour, gain over the recalibrated odds; positive = better;
`evidence_with_odds.csv`):

| Added to the odds | Men | Women |
|---|---|---|
| Stage 1 blend | −0.06 [−0.15, +0.03] tie | −0.04 [−0.12, +0.04] tie |
| The literal pieces (overall, surface-only, counts) | **−0.27 [−0.46, −0.08] worse** | −0.04 [−0.35, +0.27] tie |
| Offset pieces (overall, offset) | −0.09 [−0.25, +0.08] tie | +0.06 [−0.20, +0.33] tie |
| Odds × both-new (a symmetric slope change) | −0.03 [−0.12, +0.06] tie | −0.03 [−0.13, +0.06] tie |
| Switch differences (season counts, layoffs, last season's form) | −0.05 [−0.21, +0.11] tie | +0.40 [−0.07, +0.87] tie |

**Is the surface-switch information priced?** The share of matches won minus the expected share, player-rows, main tour
(`evidence_priced.csv`; negative = the player won less than expected):

| Days since the player's last match on the surface | Men vs overall Elo | Men vs market | Women vs overall Elo | Women vs market |
|---|---|---|---|---|
| ≤ 3 | +1.0 pts | +0.0 | +1.0 | +0.3 |
| 31–90 | −1.8 | +0.7 | −3.1 | −1.0 |
| 201–400 | −7.5 | −1.0 | −6.1 | −2.1 |
| over 400 (or never since 2010) | −14.1 (254 rows with odds) | −5.0 | −8.2 (324) | −2.1 |

*Inferred.* The market prices almost all of the surface-switch effect that Elo misses. The one residual hint is
players returning to a surface after more than 200 days, who win 1–5 points less than the price says; the samples are
small.

## 5. The strategy

**Principles, each from the evidence above:**

1. **Do not feed the 1500-started surface rating as a piece.** Its level mixes "how good on this surface" with "how many
   matches on it". Feed the **surface-offset Elo**: unbiased at no evidence, evidence-weighted by its own K, and the
   best Elo-only variant on the check years.
2. **Keep the overall Elo as a separate piece** next to it, so the model can set the weight of the surface term itself.
3. **Feed the evidence as both players' career surface counts.** The model can then learn the inexperience penalty that
   the offset Elo leaves out by construction. Without the odds that penalty is 3–7 points of win probability.
4. **Replace the A − B flag by both players' values.** Each of the following is a per-player pair that is exchanged when
   A and B swap, so "both new" and "one new" stay distinct:
   * this season's surface matches;
   * days since the last surface match, capped at 3 years;
   * last season's surface form: wins above overall Elo's expectation on that surface last season, over (matches + 5).
5. **Unchanged:** the odds, the other 51 inputs, both orientations predicted and averaged, the population and the
   configuration.

**Expectation, stated before the test.** Given the odds, the linear evidence puts any gain within ±0.4 mLL. TabPFN found
+1.5 mLL where linear models found +0.1 on the same inputs (the [thinking study](../tabpfn_thinking/README.md)), mostly
through reweighting and curvature rather than interactions. The open question is whether it does so here.

### The arms

All five with-odds arms are trained and scored on identical matches.

| Arm | Inputs | Columns |
|---|---|---|
| `base` | The current best model's 54 inputs, unchanged; checked value for value against the leak-proof upload | 54 |
| **`primary`** | base − `elo_logit` − `surface_first` + `elo_overall` + `elo_offset` + 4 pairs (`surf_career`, `surf_season`, `surf_layoff`, `surf_form_prev`, each `_a`/`_b`) | 62 |
| `literal` | As primary, with `elo_surface` (the 1500-started surface-only rating) in place of `elo_offset`: the suggestion as written | 62 |
| `elo_only` | base with `elo_logit` replaced by `elo_offset` | 54 |
| `switch_only` | base with `surface_first` replaced by the 4 pairs | 61 |
| `base_noodds`, `primary_noodds` | base and primary without `odds_logit` (diagnostic) | 53, 61 |

Encodings: `elo_*` are log-odds (Elo points × ln 10 / 400) and negate on swap. Counts and days are log(1 + x). Days
default to 3 years when the player has no earlier match on the surface since 2010. Form is a shrunk mean; with no
matches last season it is 0.

## 6. The test

**Model.** TabPFN-3.5 with thinking off: the API's plain v3.5 (`model_path = v3.5_default`), the hosted "3.5-Plus".
* Settings: 8 estimators, softmax temperature 0.9, `ignore_pretraining_limits` on. These are the best model's settings
  without thinking.
* No fit description; no categorical declaration, as in the best model.
* Seeds 0, 1 and 2.

**Walk-forward, one season per sample.** For season Y in 2022–2026, train on the main-tour matches with odds of 2013 to
Y − 1, and predict Y's matches as stored and with A and B swapped.
* The 2022 fold's training set is exactly the best model's 39,918 matches.
* The men's 2018 season has no odds and is absent, as before.

**Stages and budget.** All three stages are registered in `jobs.json` and each runs once (`guard.py`). Quotes are the
server's (`quotes_*.json`); bills have run below quotes before.

| Stage | Seasons | Runs | Jobs | Quoted tokens |
|---|---|---|---|---|
| Pilot (design years) | 2019–2021 | base seeds 0 and 1, primary seed 0, literal seed 0 | 12 | 138,724 |
| Confirmation | 2022–2026 | 5 arms × seeds 0, 1, 2 | 75 | 1,268,961 |
| Diagnostic | 2022–2026 | base_noodds, primary_noodds, seed 0 | 10 | about 170,000 |

**What the pilot is for:**
* run the pipeline end to end;
* measure seed noise (base seed 1 against base seed 0);
* confirm the non-thinking fit is not billed.

**Pre-registered:** the pilot does not change the arms or the primary endpoint. A broken input would be fixed and the
pilot re-run.

**Scoring** (`score.py`, written before any call).
* **A match's forecast** is the mean of its two orientations. **An arm's forecast** is the mean of its three seeds.
* **The market reference** is the closing odds recalibrated per tour by one slope (no intercept), fitted on each fold's
  own training matches.

**Primary endpoint.** `primary` against `base`, both tours pooled, 2022–2026 pooled: the gain in mLL with its
four-week-block interval. "The idea is better" only if the interval lies above 0.

**Secondary results, reported in full but not used to claim the idea:**
* per tour;
* each season as one sample: five seasonal gains, their mean with a t interval on 4 df, and how many are positive;
* `literal`, `elo_only` and `switch_only` against `base`;
* every arm against the recalibrated odds (the ranking that matters for betting);
* subsets: early surface season, both players new, grass, the rest of the season;
* the noise floor: base seeds against each other, and each arm against base seed by seed.

**The diagnostic** (no odds) separates two readings of a null with the odds:
* primary_noodds beats base_noodds, but primary ties base: the information is priced in;
* both tie: TabPFN cannot use the representation.

**Multiplicity.** One primary comparison. The 3 other arms, 2 tours, 5 seasons and 4 subsets are exploratory and
unadjusted, and are labelled so.

## 7. Risks and limits known before the audit

* **History starts in 2010.** Every player starts at 1500 then. Surface counts and layoffs are truncated for players
  active before 2010, which matters most in the early training seasons.
* **The 2026 duplicate player IDs.** The [TTT decision](../../decisions/2026-10-03-leading-rating-candidate.md) records
  2026 players split across two identities. That resets their Elo and their counts in every arm, base included.
* **Time rule.** Elo and the per-player quantities follow each player's own order, as the
  [timing decision](../../decisions/2026-10-05-match-timing.md) allows for per-player features. Layoffs use the timing
  study's best-estimate days. Last season's form uses only the previous calendar season. A probe that flips later
  results moved no earlier value.
* **Not an untouched holdout.** The baseline inputs were selected on 2022–2026. Only the new representation is
  pre-registered here.
* **Closing prices.** They are tennis-data's average, archived and not executable. A log-loss gain is not a betting
  return.

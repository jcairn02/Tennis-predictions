# Plan: does the new representation carry information the early price lacks?

6 October 2026 · Fixed before any forecast was compared with any price or result. Requested by the owner the same day
("run it"), after the confirmation found the new representation ties the best model's inputs given the **closing** odds
([README](README.md) §5–6).

**Key.**
* Log loss: lower is better. Gains are milli-log-loss (mLL), and positive means the second-named forecast is better.
* Slopes are reported with their sign meaning stated.
* 95% intervals are cluster-robust over four-week blocks of tournament dates, with t on (blocks − 1) degrees of
  freedom; calendar weeks are a sensitivity. A range that spans 0 is a tie.

## Data

* **The sample.** `early_price_frame.py` → `early_price_frame.parquet`. It takes the confirmation's 2025–2026 test
  matches and links each to its Polymarket market through the sharp-benchmark study's match table.
* **Early price:** the Polymarket price 24 hours before the listed start.
* **Close:** the price 30 minutes before the listed start, the sharp-benchmark study's closing benchmark. The last half
  hour holds in-play prices.
* **Clean sample (primary population).** 1,067 matches (582 men, 485 women; 184 in 2025, 883 in 2026). Each satisfies
  all of the following:
  * both players are playing their first match of the event;
  * both players' previous match surely ended at least 3 days before the listed start's UTC day, so every input of the
    forecast existed 24 hours before the start;
  * both prices exist;
  * no identity-split debut.
* **Sensitivity population.** 2,648 matches with both prices, later rounds included. There the forecast may know a
  previous round that ended within the last 24 hours, so it can "predict" the move by knowing news the early price did
  not.

## Forecasts (none sees any price of the match)

* **No-odds forecasts:** `base_noodds` and `primary_noodds`, the confirmation's two arms without `odds_logit`. They are
  refitted on the local GPU with TabPFN-3.5, seeds 0, 1 and 2, with each season's walk-forward training (2013 to Y − 1),
  and averaged over seeds. The API's seed-0 forecasts from the diagnostic stage are an agreement check and a sensitivity.
* **Deployment forecasts** (test 3): `base` and `primary` with the odds, trained on the closing odds exactly as in the
  confirmation, local, seeds 0–2. At prediction time each match's `odds_logit` is replaced by the Polymarket price 24
  hours out, which is what a model trained on closing prices would be fed at bet time. Queried also with the 30-minute
  price, and with the tennis-data close as an agreement check against the API forecasts.

## Tests

**Test 1, the headline: does the new representation predict the move to the close?**
* For each match:
  * M = logit P(A) at 30 minutes − logit P(A) at 24 hours;
  * D = logit `base_noodds` − logit P(A) at 24 hours: how far the old model disagrees with the early price;
  * Δ = logit `primary_noodds` − logit `base_noodds`: what the new representation changes.
* OLS of M on D and Δ, no intercept, so the forecast is antisymmetric in A and B.
* **β_Δ above 0:** the price moves toward the new representation's change, so it carries information the early price
  lacks.
* **β_D** is the positive control: does the market move toward the old sporting model at all? If it does not, the test
  cannot see such information.
* Each slope's interval reads as above 0, below 0, or a tie.

**Test 2: given the early price, which sporting forecast predicts the result better?** Logistic stacks without an
intercept, cross-fitted by leaving one four-week block out:

| Stack | Logit p |
|---|---|
| S0 | b · logit(early) |
| S1 | b · logit(early) + c · logit(`base_noodds`) |
| S2 | b · logit(early) + c · logit(`primary_noodds`) |

* S2 against S1 is the new representation's value given the early price.
* S1 against S0 and S2 against S0 measure each sporting model's value beside the early price.
* The same three are run with the 30-minute price as a reference; the expectation is about 0, as with the closing
  odds.

**Test 3: deployment.** Log loss on the sample, all of TabPFN's deployment forecasts:
* `primary` queried with the early price against `base` queried with the early price;
* both against S0, the early price recalibrated.

**Reading.**
* Test 1 is the headline.
* Tests 2 and 3 are the betting-relevant follow-ups. On 1,067 matches they have little power: scaled from the
  confirmation, their minimum detectable effect is about 1.5 mLL, against a no-odds gain of +1.36 for both tours. A tie
  there is "inconclusive", not "no value".
* Every population, tour and horizon other than the headline is exploratory and unadjusted.

## Run

```bash
./python.sh src/eda/surface_elo_pieces/early_price_frame.py          # the sample (no forecasts, no results)
./python_tabpfn_local.sh src/eda/surface_elo_pieces/early_price_local.py   # 24 local GPU fits, no API tokens
./python.sh src/eda/surface_elo_pieces/early_price_score.py          # tests 1-3
```

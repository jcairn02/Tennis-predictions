# The best 2026 model with leak-proof IOS: one TabPFN-3.5-Thinking refit

5 October 2026 · Research evidence, not a production, model or betting decision.

**Status: run on 5 October 2026.** The owner authorised one paid fit that day ([decision](../../decisions/2026-10-05-match-timing.md)).

* **The first attempt** was refused before anything was sent: Prior Labs rejected the login token the project's pipelines had shared since September (HTTP 401). Prior Labs' docs now issue keys at platform.priorlabs.ai.
* **The fit itself** ran after the owner saved a new key there. It took 335 seconds and was billed 162,211 tokens, the same as the original fit.

## Result

**Rebuilding the IOS inputs leak-proof does not change the model's predictive value.** The edge over the closing price is the same within a few hundredths of a milli-log-loss, and the two fits' forecasts are almost identical.

Against the closing price recalibrated on the training matches (positive = better than the price):

| Tour | Window | Matches | Original fit | Leak-proof refit | Refit against original |
|---|---|---|---|---|---|
| Men | 2022–2026 | 12,352 | +1.57 [+0.82, +2.32] better | +1.52 [+0.76, +2.27] better | −0.06 [−0.13, +0.02] tie |
| Men | 2026 | 1,774 | +2.70 [+0.01, +5.38] better | +2.70 [−0.11, +5.51] tie | 0.00 [−0.28, +0.28] tie |
| Women | 2022–2026 | 11,467 | +0.74 [−0.14, +1.63] tie | +0.81 [−0.05, +1.67] tie | +0.07 [−0.07, +0.21] tie |
| Women | 2026 | 1,714 | −0.83 [−4.45, +2.80] tie | −0.31 [−3.57, +2.95] tie | +0.52 [−0.43, +1.46] tie |
| Both tours | 2022–2026 | 23,819 | +1.17 [+0.54, +1.80] better | +1.18 [+0.56, +1.79] better | 0.00 [−0.08, +0.08] tie |

* **Men, season by season** (refit against the price): 2022 +1.29, 2023 +0.62, 2024 +1.22, 2025 +2.16 [+0.22, +4.09] and 2026 +2.70. That is positive every season, as the original was.
* **The men's 2026 lower bound** moved from +0.01 to −0.11 with an unchanged point estimate. On 1,774 matches that season's result was borderline before and is borderline now.
* **Agreement.** The two fits' forecasts correlate 0.9999 in log-odds. A forecast moves by 0.16 percentage points on average and by 0.33 at the 90th percentile. 44 of the 23,819 matches change favourite.
* **Run-to-run variation.** With forecasts this close, the fit's own variation is small. The caveat below matters little here.

## The question

The best 2026 model is the [TabPFN-3.5-Thinking fit](../tabpfn_thinking/README.md) on the closing odds plus 53 pre-match inputs. Against the recalibrated closing price it scored, for men, +2.70 [+0.01, +5.38] milli-log-loss on 2026 and +1.57 [+0.82, +2.32] on 2022–2026. Positive means better; brackets are paired 95% intervals over four-week blocks.

Twenty-two of its inputs come from IOS, ratings solved for all players together, and those [leaked](../match_timing/README.md) across overlapping events. Does rebuilding them on the leak-proof clock change the model's predictive value?

## The design, fixed before the call

* **Same matches.** The original upload's 39,918 training matches (main tour 2013–2021 with closing odds), and its 23,819 test matches (2022–2026), each queried as stored and with A and B swapped (47,638 rows), in the same order.
* **Same inputs, 22 replaced.**
  * The 54 columns keep their original order.
  * Replaced: the IOS offence and defence on seven statistics (14), their matchup products (7), and the short-memory IOS points matchup (1). They now come from the leak-proof rebuild (`data/studies/match_timing/leakproof_features.parquet`).
  * Unchanged: the other 32 columns, the odds included, checked value for value against the original upload.
* **Same configuration.** The original guard's: 8 estimators, softmax temperature 0.9, seed 0, thinking effort high, log-loss metric, and the original fit description.
* **Same scoring.** The original study's: per tour, 2022–2026 and each season, against the closing price recalibrated on the training matches and against the original fit. `score.py` reproduces the original numbers exactly from the saved predictions.
* **Its own budget.** A once-only guard with its own schema and receipt folder (`data/studies/tabpfn_leakproof/thinking/`); the earlier studies' receipts are never read or changed.

## How much the inputs moved

Observed (`input_changes.csv`):

| Rows | Correlation, leak-proof vs original IOS input | Median change |
|---|---|---|
| Training | mean 0.9995, lowest 0.9962 | 0.21% of a standard deviation |
| Test | mean 0.9978, lowest 0.9930 | 0.33% of a standard deviation |

They moved more in the test seasons, consistent with the overlap growing once Madrid, Rome and Shanghai became 12-day events in 2023. In the free logistic models, the same swap ties the original on every comparison, within ±0.1 milli-log-loss for the men.

## Caveat for reading the result

A thinking fit may not be exactly reproducible even on identical inputs. Only one fit was authorised, so its difference from the original fit cannot be split into the input change and the fit's own run-to-run variation. Both are small: the two fits' forecasts agree to 0.9999.

## Run

```
./python.sh src/eda/tabpfn_leakproof/build_frame.py                    # the upload and its checks (free)
./python_tabpfn.sh src/eda/tabpfn_leakproof/dispatch.py --quote         # quote and remaining quota (free)
./python_tabpfn.sh src/eda/tabpfn_leakproof/dispatch.py --run --spend-tokens   # the one fit and one prediction
./python.sh src/eda/tabpfn_leakproof/score.py                           # the comparisons (free)
```

Both fits were quoted at 648,845 tokens (463,704 for the fit, 185,141 for the prediction) and billed 162,211. The receipts are in `data/studies/tabpfn_leakproof/thinking/`; the scores are in `results.json`, `results.csv` and `test_predictions.parquet`.

**The key.** `TABPFN_TOKEN` must hold a key from platform.priorlabs.ai. A process started before the key was saved still has the old one. On Windows, read the saved value with `[Environment]::GetEnvironmentVariable('TABPFN_TOKEN','User')`.

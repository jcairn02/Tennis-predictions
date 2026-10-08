# One men's TabPFN 3.5 Thinking fit: test on 2026

Completed 2 October 2026 (Vancouver time). [Plain-language HTML report](report.html).

One hosted Thinking fit in the `tennis-tabpfn` environment used **13,952 men's matches from 2020–2025** and the repaired model's **36 sporting inputs**: the established nine, including Elo, plus the 27 frontier features. No women's matches, closing prices, dates, player identities or test outcomes were model inputs. The final test contains **1,712 men's matches from 4 January to 2 August 2026**.

| Forecast | Test matches | Log loss (lower is better) |
|---|---:|---:|
| TabPFN 3.5 Thinking, 36 inputs | 1,712 | 0.607825 |
| Logistic regression, same 36 inputs and training rows | 1,712 | 0.609853 |
| Previous annual logistic model, 36 inputs | 1,712 | 0.610329 |
| Logistic regression, original nine inputs | 1,712 | 0.617108 |
| Average closing probability | 1,712 | 0.594790 |
| Training-calibrated average closing probability | 1,712 | 0.594452 |

TabPFN improves the direct logistic comparator by **2.028 milli-log-loss**, with a paired 95% interval of **−1.110 to +5.166**. This modest improvement is not clearly separated from zero. Both sporting models lose to the average closing benchmark. Pinnacle has only **70** comparable matches, all in January: TabPFN 0.627282, logistic 0.626780, Pinnacle 0.608138. That small subset cannot establish season-wide performance against Pinnacle.

## Training selection and evaluation

Before the final fit, the code compared all available history from 2013, the latest six calendar years, and the latest four. Each strategy and each of four ridge penalties was scored on forward predictions for 2023, 2024 and 2025 (7,784 validation matches), with scaling and model fitting restricted to earlier seasons. The best six-year configuration scored 0.612339, versus 0.613228 for the best full-history configuration and 0.612774 for the best four-year configuration. It selected 2020–2025 and ridge 0.01 for the final comparison. This logistic-based selection is a practical proxy, not proof of TabPFN's optimal history length.

Logistic regression uses training-only RMS scaling, no intercept, unpenalized established inputs and ridge on the new 27. Both models keep the same fitted state throughout the test; the historical sporting features update from allowable earlier matches as 2026 progresses. TabPFN's single prediction request includes original and swapped player orders (3,424 query rows); averaging complementary predictions yields one forecast per match. Test labels are never uploaded.

Paired intervals use fixed 28-day calendar blocks and cluster-t uncertainty. The 2026 outcomes and the feature design had already been inspected in earlier research, so this is not an untouched research holdout. Exact historical publication and quote times remain unverified. Retirement labels follow the repaired study's winner/advancement convention, which need not match bookmaker settlement. The API's internal Thinking validation is not guaranteed chronological; the external pre-2026/2026 split is enforced locally.

## Actual run and artifacts

The immutable receipts record **one fit and one prediction request**, `execution_mode=thinking`, billing version `v3.5`, and returned checkpoint `tabpfn-v3.5-20260909.safetensors`. Requested settings were high Thinking effort, log-loss objective, seed 0 and eight estimators. The provider reported two prediction estimators. Total dispatch-to-completion time was 110 seconds. The token counter increased by **78,020**, against a free preflight quote of 312,081; this is not a dollar-cost receipt.

- [Frozen manifest and training-selection record](../../../data/studies/predictive_frontier_tabpfn/manifest.json)
- [Exact results and metadata](../../../data/studies/predictive_frontier_tabpfn/results.json)
- [Paired comparisons](../../../data/studies/predictive_frontier_tabpfn/comparisons.csv)
- [Completion receipt](../../../data/studies/predictive_frontier_tabpfn/thinking/COMPLETE.json)
- [Run usage and timing](../../../data/studies/predictive_frontier_tabpfn/thinking_run.json)
- [Preparation, dispatch guard and scoring code](../../../src/eda/predictive_frontier_tabpfn/)
- [41 passing tests in the tennis-tabpfn environment](../../../data/studies/predictive_frontier_tabpfn/tests_roundoff_audit.xml)

Rebuild the report from saved predictions without calling the API:

```bash
./python.sh src/eda/predictive_frontier_tabpfn/score.py
```

The guard prevents another fit under this study's authorization. The rejected pooled preparation was never dispatched and is preserved in `data/studies/predictive_frontier_tabpfn/superseded_pooled_preparation.zip`. This result is research evidence, not a production or betting decision.

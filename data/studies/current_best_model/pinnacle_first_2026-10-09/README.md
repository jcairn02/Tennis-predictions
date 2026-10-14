# The current best model with the Pinnacle-first odds input, 9 October 2026

**What it is.** An instance of the current best model's template ([decision](../../../../docs/decisions/2026-10-08-current-best-model.md)) with the odds input the owner decided on 9 Oct 2026: "Pinnacle first" ([decision](../../../../docs/decisions/2026-10-09-pinnacle-first-odds-input.md)).
* **The frame is the frozen reference's** (`../reference_2026-10-08/frozen/instance/model_frame.parquet`): the same 67,226 matches of 2013–2026 and the same 57 other inputs.
* **Only the odds input changes,** together with `p_mkt`, the frame's closing price for scoring. Checked by `test/current_best_model/test_odds_input.py`.

> **Note (the owner, 9 Oct 2026). Pinnacle's own closes are missing from August 2025:**
> * tennis-data's column stops being Pinnacle's close that month;
> * OddsTrader's recording stops on 7 Sep 2025.
>
> Those rows use BetOnline's closing line as a stand-in. **If the missing Pinnacle closes are obtained, the model is retrained on Pinnacle's closes throughout.** Live, at every venue and bet time, the model is fed Pinnacle's current line with the margin removed (BetOnline's while Pinnacle has none).

## The odds input, by source (`odds_input.json`)

| Source | Matches | Seasons |
|---|---:|---|
| Pinnacle's close, tennis-data's (to 31 Jul 2025) | 60,737 | 2013–2025 |
| Pinnacle's close, OddsTrader's timed recording (where tennis-data has none, or the other books side with it; to 7 Sep 2025) | 959 | 2018–2025 |
| BetOnline's closing line (where Pinnacle has none) | 4,993 | 889 in 2025, 4,095 in 2026, 9 earlier |
| The books' average (where neither book prices the match) | 537 | 9–64 a season to 2025, 262 in 2026 |

OddsTrader's lines stamped more than 30 minutes after the listed start are left out (some are in-play prices). The rules are in `src/eda/current_best_model/odds_input.py`, which uses the odds-sources study's implementation.

## Files

| File | What |
|---|---|
| `model_frame.parquet` | The frame: the reference's, with `in_odds_logit` and `p_mkt` from the Pinnacle-first price. Added columns: `p_mkt_avg` (the books' average, the earlier input) and `odds_input` (the source) |
| `model_inputs.json` | The reference's input list, unchanged |
| `odds_input.json` | The rule, the counts by tour, season and source, and the frame's SHA-256 |
| `book_prices.parquet` (gitignored) | Per match, the decimal odds of the Pinnacle close used and of BetOnline's close (OddsTrader's prices are not committed) |
| `fits/model__<Y>__seed<k>.npz` | Local TabPFN-3.5 fits, seasons 2019–2026, seeds 0–15 (`src/eda/model_rebuild/fits.py`); `fits.log` |
| `vs_reference_2026-10-08/` | The decided comparison with the frozen reference (`src/eda/current_best_model/compare.py`, 2020–2024) |

The men's backtest by season, log loss and the return at Pinnacle's and BetOnline's closes: [docs/studies/pinnacle_first/](../../../../docs/studies/pinnacle_first/README.md).

## Rebuild

```
./python.sh src/eda/current_best_model/odds_input.py --from-reference data/studies/current_best_model/pinnacle_first_2026-10-09
bash src/eda/bet_timing/run_when_free.sh src/eda/model_rebuild/fits.py --out data/studies/current_best_model/pinnacle_first_2026-10-09 --seeds 0-15 --seasons 2019-2026
./python.sh src/eda/current_best_model/compare.py --candidate data/studies/current_best_model/pinnacle_first_2026-10-09
./python.sh src/eda/pinnacle_first/backtest.py
```

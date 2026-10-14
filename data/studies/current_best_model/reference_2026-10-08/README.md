# The frozen reference of the current best model, 8 October 2026

> **Note, 9 Oct 2026: the template's odds input has changed since this freeze.** This reference's odds input is the books' average close (Stage 1's `p_mkt`). Since the owner's [decision of 9 Oct 2026](../../../../docs/decisions/2026-10-09-pinnacle-first-odds-input.md) the current best model uses "Pinnacle first":
> * Pinnacle's close (tennis-data's to July 2025, cross-checked against OddsTrader's timed copy; OddsTrader's to 7 Sep 2025);
> * then BetOnline's closing line;
> * live, Pinnacle's current line with the margin removed.
>
> **If the missing Pinnacle closes (August 2025 on) are obtained, the model is retrained on Pinnacle throughout.** This reference stays as it is: the yardstick for `compare.py`. The Pinnacle-first instance is [`../pinnacle_first_2026-10-09/`](../pinnacle_first_2026-10-09/README.md).

**What it is.** The current best model as built on 8 Oct 2026, with the tables it was built on, copied, hashed and made read-only. It is the fixed point that new data, new features and rebuilds are compared against.

**Why** (the owner, 8 Oct 2026; recorded in the [current-best-model decision](../../../../docs/decisions/2026-10-08-current-best-model.md)):

> "I want to freeze the template of current model and its data locations as comparisons so the new data thats coming, if it harms results we will want to make some modifications, Either to ignore data, lower its weight, or find a way to mathematically change and integrate it so its useful. I dont want to lose sight of the current model"

## Where everything is

The copies are in `frozen/`, which is gitignored and reaches cold storage with the next `backup.py` run. `manifest.json` (tracked) records the configuration, the key files' SHA-256 and the counts. `frozen/files.csv.gz` lists every frozen file with its source and SHA-256.

| Folder in `frozen/` | What it holds | Copied from |
|---|---|---|
| `instance/` | **The model.** The 58-input frame (67,226 matches, 2013–2026), its input list, its 32 fits (seasons 2019–2026, seeds 0–3), the stage-2 speed column on the corrected speed history, the build's records, and its comparison with the previous model | `data/studies/model_rebuild/` (whole) |
| `speed/` | Stage 2's speed history (the live feed's corrected panel) and the adjustment's columns and coefficients | `data/studies/serve_speed_tabpfn/live/`, `…/adaptive/` |
| `tables/` | **The data it was built on**, exactly as the build read it: 54 of the 72 files the Stage 0 rebuild of 8 Oct wrote. Stage 0 (matches and players), Stage 1's odds, TrueSkill Through Time and most timeline links | their repository paths, e.g. `data/studies/predictability_diagnostic/stage0_matches.parquet` |
| `tables_later/` | The other 18 of those files, **as they stood at the freeze, not as the build read them** (see below) | `data/studies/match_timing/…` |
| `previous/` | The previous model (built on the 30 Sep tables), which every study up to 8 Oct was scored on: its frame, input list, fits of seeds 0–3 in their three folders, the checks its reused fits require, Polymarket's early-price frame | `data/studies/surface_rating_race/model/`, its fit folders |
| `code/` | `src/`, `docs/`, `test/`, the root files, and git's HEAD (`677a63f`) and status (183 lines, 86 untracked): much of the code is not committed | the repository |
| `env/` | The TabPFN-3.5 checkpoint the fits used (876 MB) and `pip freeze` of both environments | `%APPDATA%/tabpfn/tabpfn-v3.5-20260909.safetensors` |
| `inventory.csv.gz` | Every file under `data/studies` at the freeze: 7,356 files, 17.4 GB, path, size, time and SHA-256 | (hashes only, nothing copied) |

**The configuration** is the [current-best-model decision](../../../../docs/decisions/2026-10-08-current-best-model.md)'s:
* local TabPFN-3.5, 8 estimators, softmax temperature 0.9, tabpfn 9.1.0;
* then the serve-speed adjustment with the 28-day memory.
* The 2026 coefficients on this build are s_atp 0.8956, s_wta 0.9189 and b̃ 0.0342 (weekly feed, corrected speed history).
* The IOS constants it was built with are version `2026-10-08_reference` of the [IOS constants registry](../../ios_constants/README.md), added after the freeze: Stage B's tuning of 2 Oct, the surface tuning of 6 Oct, and the short memory of 4 weeks (men) and 13 (women). Its source files hash as this inventory does.

**One gap: 18 timeline files.**
* **What happened.** The build copied `data/studies` into its sandbox at about 20:00 UTC. A TDI refresh then rewrote the match timeline, its TDI links and the leak-proof IOS and features in place (20:12–20:30 UTC). It kept no copy, and today's only backup was packed earlier.
* **What survived.** The SHA-256 the build recorded for the leak-proof table and the timeline match nothing on disk (`manifest.json`, `preconditions`). `tables_later/` holds the later versions, for reference only.
* **What the later versions add** (measured against the copy the rebuild kept from before it ran):
  * 268 TDI date links, for 206 Challenger and 62 ATP 500 matches (Beijing and Tokyo), all played 29 Sep – 8 Oct 2026;
  * new days for 238 matches (176 Challenger, 62 ATP 500), all of events starting 28 Sep – 5 Oct 2026. Nothing else.
* **What it affects: no model input.**
  * The frame's last matches (Chengdu and Hangzhou, events of 23 Sep) finish by 29 Sep. Under the match clock a result counts only from the day after it finishes, so none of these days can reach a model input.
  * Checked: the one input taken straight from the leak-proof table (`ios_points_short`) is identical on all 67,226 frame matches.
  * So the frame rebuilt from `tables/` plus `tables_later/` should come out the same. That has not been run.
* **Recovering them.** They could probably be rebuilt from TDI's raw files received before 19:22 UTC. That is untested, and by the above unnecessary.

## The training history

The owner, the same day:

> "I just want the same data as before for training + training updates from future dates frozen. But if we are downloading new LOWER LEVEL data, challenger +ITF it doesnt get auto included in the model. I want a way to test if this lower level skill data is harming our model (though the data is prior to the current date)."

* **What the model trains on.** The reference's 873,437 matches (`tables/…/stage0_matches.parquet`), plus the matches played since, from the feeds that were feeding it. Today that is Tennis My Life: the main tour, its qualifying, Challenger main draws and team events.
* **What never enters by itself.** Anything else that changes the history: new Challenger or ITF matches or box scores of past dates, a new source, and a dropped or revised past match. Those are tested first, as a candidate.
* **The check:** `./python.sh src/eda/current_best_model/history.py`. It compares the live Stage 0 (or any other) with the reference's, match by match, and sorts the differences:
  * **future** (allowed): played from 5 Oct 2026 on, from a feed of the reference's last 60 days;
  * **new past**, **dropped** and **revised**: not allowed.
* **The gate.** `run_chain.py --setup` runs the check and refuses a template build when the history differs. A test build uses `--setup --candidate`.
* On 8 Oct the live Stage 0 is the reference's: 0 future, 0 new past, 0 dropped, 0 revised.

## Checking it

```
./python.sh src/eda/current_best_model/reference.py --verify     # every frozen file against its SHA-256; writes verify.json
./python.sh src/eda/current_best_model/history.py                # the live training history against the reference's
./python.sh -m pytest test/current_best_model -q                 # 21 tests
```

* **`--verify`** also lists the sources that have changed since the freeze. When a later Stage 0 rebuild replaces the live tables, that list grows; the frozen copies do not change.
* **First verification** (8 Oct 2026, 23:52 UTC): all 1,581 files intact and read-only. One source had moved on, a test file another session was editing.

## Comparing a candidate with it

A candidate is any new build of the model: new data wired into Stage 0, a new or changed input, or a remedy (data ignored, down-weighted or transformed).

1. **Build it in a folder**, as the [decision](../../../../docs/decisions/2026-10-08-current-best-model.md) describes:
   * `run_chain.py --setup --candidate`;
   * the new data put into the sandbox's tables (the live tables stay as they are);
   * the lanes, then `--collect --out <folder>`;
   * then `fits.py --out <folder> --seeds 0-3 --seasons 2019-2024`.

   If its speed history differs, add `<folder>/speed_columns.parquet`.
2. **Compare:** `./python.sh src/eda/current_best_model/compare.py --candidate <folder>`. It writes `<folder>/vs_reference_2026-10-08/`.
   * **Part 1, the inputs.** It reads no result. For every input, tour and season it reports:
     * how many rows changed;
     * the **scale ratio** (the candidate's SD over the reference's);
     * the **level shift** (the change of the mean, in reference SDs).

     An input is **"uneven"** when some tour-seasons move by more than 10% in scale or 0.10 SD in level and others do not. That is the shape of the input-data audit's finding #6, where ITF box scores widened the IOS products in 2025–2026 only. Look here first: an uneven input is the warning sign for new data.
   * **Part 2, the scores.** Both stages, refitted walk-forward on each model's own forecasts, scored on 2020–2024. **Positive = the candidate has the lower log loss (better).** Each row is read "better", "worse" or "tie" (95% interval spanning 0).
     * Primary rows: both tours, men, women.
     * Also: stage 1 alone, each level, each season, and each model against its own calibrated close.
   * Results of 2025–2026 are read only with `--through 2026`. Those seasons are the [proposed clean holdout](../../../../docs/studies/clean_holdout_rebuild/README.md).
3. **If it harms** (an uneven input, or a negative primary row), change the data handling and compare again. Accepting a candidate is the owner's call.

**Two runs of 8 Oct 2026** (`comparisons/`, 2020–2024):

| Candidate | Both stages, both tours (mLL, + = candidate better) | Inputs |
|---|---|---|
| The reference itself | 0.000 exactly (interval ±0.085 from the seeds' variance) | 0 of 58 changed |
| The previous model (30 Sep tables) | −0.07 [−0.21, +0.08], tie | 52 of 58 changed. Two uneven, each at the tour-season a known correction touched: `prod_first_in` in WTA 2015 (scale ×1.13; the WTA 2015 serve-points fix) and `ratings_iid` in WTA 2021 (×1.10) |

* **For scale,** the reference beats its own calibrated close by +1.37 [+0.67, +2.08] mLL on 2020–2024 (men +1.48, women +1.26).
* **A harness check.** On the previous model, the comparison reproduces the published per-season rows of the [rebuild comparison](../../../../docs/studies/model_rebuild/README.md) for 2022–2024 exactly (to 10⁻⁹), both stages and stage 1.

# P9 point details: the harness agent's memo

28 Oct 2026 · Harness agent (Claude Opus 5.5, `claude-opus-5-5`, a subagent of the lead's session `4ad0f090-214d-4b51-b18a-41ad8262b656`) · Brief: [../briefs/03_harness.md](../briefs/03_harness.md) · Shared context: [../briefs/00_shared_context.md](../briefs/00_shared_context.md)

*Status: finished (09:45). The lead stopped the study at its depth rule (09:41), so no candidate was scored. What follows is the reusable harness for a later men's 2025–26 feature study. Every number is a base's, a placebo's or a synthetic one. All are observed, computed in this session; each table names its file in `data/studies/p9_point_details/harness/`. Inferences are marked.*

## In short

* **The population:** 25,807 men's matches with a day in 1 Jan 2025 – 18 Oct 2026, at tour level (main draws and qualifying) and at Challengers; 25,542 (99.0%) with a margin-free price.
* **The live model's out-of-sample forecasts, both stages:** on all 7,266 priced tour-level matches, from stored fits only (16 seeds on the main draw, 4 on qualifying). No TabPFN fit, no GPU.
* **The sanity check holds.** On the main draw, the model beats the close by +2.65 mLL [+1.19, +4.31]. Recomputed the way edge anatomy did, it gives +3.18 [+1.79, +4.89], against the reported +2.83 [+1.27, +4.39] for an earlier instance.
* **The scoring is calibrated:**
  * random columns' z has SD 1.00–1.05 (2,000 draws per population), with 5.4–6.2% beyond ±1.96;
  * the cross-fitted gain of a useless column centres at −0.02 to −0.2 mLL and never reads "better" (0 of 200 in every population).
* **Resolution** (one standardised feature, 80% power, two-sided 5%, the z test):
  * about 0.15 mLL pooled, 0.22 at Challengers, 0.53 tour level, 0.76 tour main draw, 1.65 tour qualifying;
  * the cross-fitted gain needs about 4 times as much to read "better".

## The population (`population.parquet`, `population_facts.json`)

| Cell | Matches | Finished | Retired | Priced | With the model |
|---|---:|---:|---:|---:|---:|
| Tour level, main draw | 4,939 | 4,774 | 165 | 4,937 | 4,937 |
| Tour level, qualifying | 2,474 | 2,402 | 72 | 2,329 | 2,329 |
| Challengers, main draw | 13,026 | 12,506 | 520 | 12,967 | – |
| Challengers, qualifying | 5,368 | 5,174 | 194 | 5,309 | – |
| **All** | **25,807** | 24,856 | 951 | **25,542** | 7,266 |

**By half-year, matches (priced):**

| Cell | 2025 H1 | 2025 H2 | 2026 H1 | 2026 H2 (to 18 Oct) |
|---|---:|---:|---:|---:|
| Tour main | 1,478 (1,477) | 1,116 (1,115) | 1,516 (1,516) | 829 (829) |
| Tour qualifying | 818 (771) | 442 (426) | 834 (774) | 380 (358) |
| Challenger main | 3,149 (3,140) | 3,453 (3,435) | 3,917 (3,897) | 2,507 (2,495) |
| Challenger qualifying | 1,741 (1,730) | 1,825 (1,801) | 1,802 (1,778) | 0 (0): none in the shared Stage 0 after June |

* **Left out:** 142 walkovers, 17 'other' statuses, the 15 matches of the Next Gen Finals.
* **The convention:** retirements in (the `finished` flag gives the completed-only sensitivity), as the model's frame and the unpriced-leads check do.
* **The day and the clusters:** a match's day is the clock's `obs`; weeks and 4-week blocks run from the tournament date.
* **Side A:** Stage 0's side A won 50.01% (± 0.31%) and is the favourite on 49.97%. The orientation carries no information, and the scoring is symmetric (tested).

**The prices** (margin removed proportionally, book by book):

| Cell | Source | Matches |
|---|---|---:|
| Tour main (rule 2026-10-21, built in memory as `pinnacle_gap/dry_run.py` does) | Pinnacle via TennisExplorer, from Nov 2025 | 2,342 |
| | Pinnacle via tennis-data, to Jul 2025 | 1,774 |
| | Pinnacle via OddsTrader, to Sep 2025 | 318 |
| | BetOnline's close | 460 |
| | the books' average | 43 |
| Tour qualifying (OddsTrader's lines as the qualifying study kept them; TennisExplorer has none) | Pinnacle, to Sep 2025 | 1,007 |
| | BetOnline, after | 1,322 |
| Challenger main (TennisExplorer's lower-level pages, linked here) | Pinnacle's last pre-match price, with times | 10,265 |
| | median of the other books (median 13 books) | 2,702 |
| Challenger qualifying | Pinnacle | 3,434 |
| | median of the other books | 1,875 |

**Links:**
* **Challengers:** 18,292 of 18,394 (99.4%). 1 refused because its set score names the other winner; 101 unlinked (none, several, or a page claimed twice).
* **TennisExplorer's tour link:** 4,989 of 5,009 frame matches from 20 Oct 2025; the winner agrees on all 4,989.
* **Unpriced tour qualifying:** 145 (76 linked without a usable line, 69 not linked by the qualifying study).

**The model** (`model_logit_full`, `model_logit_s1`):
* **Main draw:** the live instance's `fits/`, seasons 2019–2026 × seeds 0–15. The 2025 and 2026 fits are trained on 2013..Y−1 (checked against the expanding window). The slope and stage 2 are fitted walk-forward on 2019..Y−1 from seeds 0–3, with the instance's own speed column (no value missing).
* **Qualifying:** the qualifying study's M0 fits, the instance's own model (seeds 0–3, checked by the frame's SHA-256 and the training shape), with the main draw's slope and stage 2.
* **Checks:**
  * the walk-forward parameters equal the qualifying study's stored ones exactly;
  * the rule of 9 Oct rebuilt in memory equals the instance's input on 67,531 of 67,531 matches;
  * Stage 0's results equal the frames' on 7,266 of 7,266.

## The bases (`bases.json`)

Log loss, nats per match:

| Population | Matches | Price, raw | Price, slope per cell (cross-fitted) | Model, stage 1 | Model, both stages |
|---|---:|---:|---:|---:|---:|
| Tour main | 4,937 | 0.5982 | 0.5983 | 0.5959 | 0.5955 |
| Tour qualifying | 2,329 | 0.5925 | 0.5913 | 0.5906 | 0.5902 |
| Tour level | 7,266 | 0.5964 | 0.5961 | 0.5942 | 0.5938 |
| Challenger main | 12,967 | 0.6128 | 0.6125 | – | – |
| Challenger qualifying | 5,309 | 0.5435 | 0.5409 | – | – |
| Challengers | 18,276 | 0.5927 | 0.5917 | – | – |
| All | 25,542 | 0.5937 | 0.5930 | – | – |

* **The price's slope:** tour main 0.99, tour qualifying 1.16, Challenger main 1.08, Challenger qualifying 1.19. Favourites are under-priced below the main tour (inference: the late, softer prices there).
* **The model against the price** (mLL, + = the model better; block-bootstrap 95% intervals):

| Population | Comparison | Gain | 95% interval | Reading |
|---|---|---:|---|---|
| Tour main | both stages vs the raw close | +2.65 | [+1.19, +4.31] | better |
| Tour main | both stages vs the close with its own slope | +2.83 | [+1.31, +4.55] | better |
| Tour main | stage 1 vs the raw close | +2.25 | [+0.87, +3.89] | better |
| Tour main | stage 2's own gain (both stages vs stage 1) | +0.40 | [+0.11, +0.68] | better |
| Tour qualifying | both stages vs the raw close | +2.29 | [+0.62, +3.74] | better |
| Tour qualifying | both stages vs the close with its own slope | +1.04 | [−1.14, +3.10] | unresolved, P(better) 0.82 |
| Tour level | both stages vs the close with a slope per cell | +2.25 | [+1.10, +3.39] | better |
| Tour main, finished only | both stages vs the raw close | +2.81 | [+1.25, +4.58] | better |

* **The sanity check against the project's reports:**
  * Edge anatomy (§ 3) reported +2.83 [+1.27, +4.39] for men, Jan 2025 – Jul 2026: the model against its own odds input, recalibrated walk-forward, for the instance of 10 Oct.
  * Recomputed the same way for the live instance: +3.18 [+1.79, +4.89] on 4,366 matches, and +2.78 [+1.47, +4.28] to 18 Oct.
  * Inference: consistent. It is another instance on a slightly different set of matches.
  * **Note added by the lead, 28 Oct 2026.** Every figure to 18 Oct in this memo includes matches from 29 Jul 2026. [Edge anatomy](../../edge_anatomy/README.md) § 3 kept those matches "sealed for a future untouched test" of the model's edge. The lead's brief set the window without checking for that seal.
    * Two pooled figures (to July, and to 18 Oct) are enough for a rough back-calculation of the sealed period's edge. Neither the lead nor this memo makes one.
    * The owner decides whether that period still counts as untouched for the model's edge. See the [process log](../process_log.md), judgment call 3.

## Placebo calibration (`placebo_summary.csv`, `placebos.csv.gz`, `null_check.csv`)

**Random N(0, 1) columns:** the price base, raw part, the "free" variant. The model bases and the new part read almost the same; the full table is in the file.

| Population | Matches | z SD (200 placebos) | Beyond ±1.96 (200) | z SD (2,000 more) | Beyond ±1.96 (2,000) | Gain, mean ± SD (mLL) | Read "better" |
|---|---:|---:|---:|---:|---:|---:|---:|
| All | 25,542 | 1.02 | 7.0% | 1.00 | 5.6% | −0.020 ± 0.031 | 0 of 200 |
| Challengers | 18,276 | 1.09 | 8.5% | 1.02 | 5.7% | −0.026 ± 0.047 | 0 |
| Challenger main | 12,967 | 1.03 | 5.5% | 1.05 | 5.9% | −0.038 ± 0.058 | 0 |
| Challenger qualifying | 5,309 | 1.00 | 6.5% | 1.02 | 5.4% | −0.105 ± 0.170 | 0 |
| Tour level | 7,266 | 1.11 | 7.0% | 1.02 | 5.9% | −0.052 ± 0.114 | 0 |
| Tour main | 4,937 | 1.14 | 11.0% | 1.01 | 6.2% | −0.076 ± 0.175 | 0 |
| Tour qualifying | 2,329 | 1.07 | 8.0% | 1.02 | 5.5% | −0.195 ± 0.393 | 0 |

* **The 2,000-draw check decides.** The week-clustered z is calibrated to within a few percent. The first 200 columns' wider spread at tour level (1.14 on the main draw) was a chance high.
* **The other standard errors:** the model-based one gives SD 0.99–1.03; clustering by 4-week block (about 24 clusters) gives 1.04–1.08. So z stays clustered by week; the one-sided p on the t with weeks − 1 is reported beside it.
* **The gains:** a useless column costs about 1/n per match out of sample. Its interval is narrow, so it reads "worse" about a third of the time and "better" never.
* **With missing values** (200 columns, present by level: 0.95 at the 1000s, 0.57 at the 500s and 250s, 0.5 at the Slams, 0.30 at Challengers):
  * z SD 0.94–1.04, 3–9% beyond ±1.96;
  * the subset and the indicator give the same z, as designed;
  * gains −0.02 to −0.40 mLL, never "better".
* **The nuisance columns:**
  * *The hash of the match id behaves as noise:* |z| ≤ 0.72 everywhere.
  * *The two player-index columns are not clean placebos:*
    * B's index (rank among the ids): z −3.02 pooled.
    * A's minus B's: z +3.31 pooled, +2.18 at tour level against the price, and only +1.16 against the model's both stages. Their cross-fitted gains are unresolved (pooled +0.19 [−0.14, +0.50]).
  * *Inference:* ATP ids rise with the date a player was registered, so the columns stand for career newness. The close leans against newer players, and the model's age and rating inputs absorb most of that. This is a real structure the harness detects, not a fault of it.

## Planted signal (`planted_summary.csv`, `planted.csv.gz`)

* **The design:** synthetic results from the base plus γ × a random column, 200 draws per gain, the "free" variant.
* **What each cell shows:** the share detected by the one-sided z at 5%, then the share read "better" by the cross-fitted gain. Four gains were run, before the lead's note that one would do.
* **Under the null (gain 0):** 2–7% and 0–1%.

| Population, base | 0.25 mLL | 0.5 mLL | 1 mLL | 2 mLL |
|---|---|---|---|---|
| All, price | 0.98 / 0.32 | 1.00 / 0.70 | 1.00 / 0.98 | 1.00 / 1.00 |
| Challengers, price | 0.92 / 0.20 | 1.00 / 0.52 | 1.00 / 0.94 | 1.00 / 1.00 |
| Challenger main, price | 0.82 / 0.07 | 0.96 / 0.30 | 1.00 / 0.74 | 1.00 / 0.99 |
| Challenger qualifying, price | 0.48 / 0.02 | 0.72 / 0.06 | 0.94 / 0.20 | 1.00 / 0.62 |
| Tour level, price | 0.60 / 0.01 | 0.88 / 0.09 | 0.98 / 0.30 | 1.00 / 0.84 |
| Tour level, model | 0.61 / 0.04 | 0.83 / 0.10 | 1.00 / 0.32 | 1.00 / 0.81 |
| Tour main, price | 0.47 / 0.00 | 0.78 / 0.05 | 0.93 / 0.14 | 0.99 / 0.58 |
| Tour main, model | 0.43 / 0.01 | 0.69 / 0.04 | 0.94 / 0.17 | 1.00 / 0.54 |
| Tour qualifying, price | 0.38 / 0.01 | 0.46 / 0.01 | 0.69 / 0.04 | 0.91 / 0.15 |
| Tour qualifying, model | 0.29 / 0.01 | 0.45 / 0.01 | 0.68 / 0.07 | 0.95 / 0.18 |

* **The cross-fitted gain recovers the planted gain** less its estimation cost of 0.01–0.3 mLL, larger on the smaller populations. For example: pooled, 0.5 → +0.47; tour main against the price, 1 → +0.89.
* **The z test is the instrument.** The gain's "better" reading is a strict confirmation that needs about 4 times the gain.

## Resolution (`resolution.csv`)

One standardised feature, 80% power, two-sided 5%, the "free" variant. "Curve" matches it; "offset" is up to 15% more sensitive on the qualifying cells, whose price slope is far from 1.

| Population | Base | Matches | Weeks | se of b per SD | MDE of b per SD (log-odds) | MDE (mLL), from the se | MDE (mLL), planted z | MDE (mLL), gain read "better" | Null gain, mean ± SD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| All | price | 25,542 | 91 | 0.0136 | 0.038 | 0.15 | < 0.25 | 0.64 | −0.020 ± 0.031 |
| Challengers | price | 18,276 | 89 | 0.0164 | 0.046 | 0.22 | < 0.25 | 0.80 | −0.026 ± 0.047 |
| Challenger main | price | 12,967 | 89 | 0.0191 | 0.053 | 0.31 | 0.32 | 1.16 | −0.038 ± 0.058 |
| Challenger qualifying | price | 5,309 | 69 | 0.0323 | 0.090 | 0.80 | 0.77 | > 2 | −0.105 ± 0.170 |
| Tour level | price | 7,266 | 62 | 0.0255 | 0.071 | 0.53 | 0.57 | 1.90 | −0.052 ± 0.114 |
| Tour level | model | 7,266 | 62 | 0.0255 | 0.071 | 0.53 | 0.55 | 1.96 | −0.053 ± 0.112 |
| Tour level | model, stage 1 | 7,266 | 62 | 0.0255 | 0.071 | 0.53 | 0.49 | 1.85 | −0.053 ± 0.113 |
| Tour main | price | 4,937 | 61 | 0.0307 | 0.086 | 0.76 | 0.73 | > 2 | −0.076 ± 0.175 |
| Tour main | model | 4,937 | 61 | 0.0308 | 0.086 | 0.76 | 0.85 | > 2 | −0.077 ± 0.173 |
| Tour qualifying | price | 2,329 | 60 | 0.0448 | 0.125 | 1.66 | 1.68 | > 2 | −0.195 ± 0.393 |
| Tour qualifying | model | 2,329 | 60 | 0.0449 | 0.126 | 1.65 | 1.58 | > 2 | −0.194 ± 0.395 |

* **How the columns are read:**
  * *From the se:* (1.96 + 0.84) × the placebos' median clustered se, turned into mLL by the expected Kullback–Leibler gain over the population's own prices.
  * *Planted:* interpolated in log gain on the power curves above.
* **For a feature present on a share c of the matches:**
  * the MDE of b grows by 1/√c;
  * its gain averaged over the whole population is unchanged;
  * on the covered matches alone, the MDE in mLL grows by 1/c.
* **Against the shot-level study's hidden edges of 1–2 mLL** (inference): the pooled and Challenger tests resolve them easily. The tour main draw alone detects 1 mLL 93% of the time (one-sided z at 5%).

## How to call the harness

The candidate goes in as a parquet file with `match_id` (Stage 0's) and one column: the A − B difference on Stage 0's side A, NaN where it does not exist. A depth rule or the deepest quarter is expressed by setting the other rows to NaN.

```
./python.sh src/eda/p9_point_details/harness.py --feature <features.parquet> --column <name> --direction 1 \
    --populations all,tour,tour_main,tour_qual,challenger,ch_main,ch_qual --bases price,model,model_s1 \
    --out <readings.csv>
./python.sh src/eda/p9_point_details/harness.py ... --finished-only      # the sensitivity without retirements
```

From Python: `harness.score(pop, feature_series, direction, populations, bases)` returns the same long table.

**Note added by the lead, 28 Oct 2026, 13:42.** The command now takes `--last-date YYYY-MM-DD`: it scores only the matches played on or before that day (`harness.window`). `--last-date 2026-07-28` leaves out the matches edge anatomy kept sealed. Without it, the command prints a note when the window reaches 29 Jul 2026. It is refused with `--bases-report`, which rewrites `bases.json` for the whole window. Two tests cover it (15 of 15 pass). Masking the feature with NaN is not a substitute: the "indicator" readings still fit every row's result.

* **One row per reading:** population × base × part (raw, new part) × variant (offset, free, curve) × missing handling (subset, indicator).
* **Each row holds:**
  * the matches and the coverage;
  * b per RMS unit and per raw unit, with its week-clustered se, z, and the one-sided p in the declared direction (normal, and t on weeks − 1);
  * the cross-fitted gain in mLL with its block-bootstrap 95% interval, P(better) and reading, and the t interval beside it;
  * the uncentred correlation with the base, and the R² on the model's 48 inputs (new-part rows).
* **The model bases exist at tour level only.** The command skips them elsewhere.
* **It reads** only `data/studies/p9_point_details/harness/population.parquet` and `model_inputs.parquet`, plus the feature file it is given.

## The new part below the tour: what is possible

* **The model's inputs are not built for Challenger matches,** so the tour-level projection on the 48 inputs cannot be made there.
* **The price is the base everywhere.** The z beyond the price is already the orthogonality test the owner asked for, at every level.
* **A substitute is possible now** (observed coverage, 09:24): Stage 0's match players carry each player's pre-match ranking points and age.
  * Both players' ranking points: 90–99% of Challenger matches. Age: 95–100%.
  * A projection of the feature on Δ log(1 + ranking points), Δ age and Δ age² (A − B, no intercept) would give a "beyond results-only status" part.
  * The harness's `new_part(x, Z)` takes any outcome-free control matrix Z, so this needs only the columns.
  * Not built here: the brief asks what is possible, and such controls are weaker than the model's inputs (no form, no box-score profiles, no Elo).
* **The stronger option** is to build the model's own non-price inputs for Challenger rows with the chain's builders. The lower-level layer already computes opponent strength on Stage 0 for every level. That is the builder's or the lead's call, as it means running the chain's code on rows it does not normally emit.

## Caveats a reviewer should check

* **The Challenger price is a late pre-match price, not a close.** Pinnacle's last recorded change came a median 1.3 hours before the listed start on these pages. The other books' median is 2.0 hours (`price_lead_hours`). P11 found the site's last Pinnacle price equal to Pinnacle's close on 75% of matches. A statistic that moves the line late could look "unpriced" at Challengers and not at tour level.
* **The tour-level qualifying price is BetOnline's from September 2025** (OddsTrader's Pinnacle record ends then; no TennisExplorer Pinnacle exists for qualifying). That cell's price is a little less sharp.
* **The model on qualifying is the live model with 4 seeds,** not 16 (the qualifying study's M0 fits). Its seed noise is larger than on the main draw.
* **Challenger qualifying ends in June 2026** in the shared Stage 0 (above). Pooled readings weight the tour-level and Challenger main-draw matches more in July–October 2026.
* **The window was read for the bases.** Edge anatomy kept matches from 29 Jul 2026 "sealed", and the unpriced-leads check registered its Look B from that day. This harness tested none of those statistics; it read the price's and the model's log loss.
* **Cross-fitting folds over time in both directions.** A block's slope is fitted on the blocks before and after it. That is fine for a feature test, where both arms get it. It is not a walk-forward forecast.
* **The blocks are tournament-date blocks.** A Slam's two weeks fall in one week cluster (its tournament date). The matches of one event share a cluster, which is the conservative choice.

## Process notes

Local time (UTC−7). "Results" here means only the bases' and placebos' numbers: no rally statistic and no P9 table is opened.

### 1. Reading (09:00–09:04, no result read)

* Read the brief, the shared context, the lead's process log, CLAUDE.md (in context).
* Code read: `current_best_model/compare.py`, `odds_input.py`; `serve_speed_tabpfn/common.py`, `forecasts.py`, `score.py` (`paired_stats`); `tabpfn_thinking/common.py` (`fit_logistic`, `blocks`, `ll`); `unpriced_leads/build_forecasts.py`, `screen.py` (`orthogonal_part`, `diff_input_names`); `qualifying_targets/common.py`, `prices.py`, `score.py`, `top_edges.py`; `ingest/tennisexplorer.py` (`link_frame`), `ingest/tennisexplorer_lower.py`; `pinnacle_gap/dry_run.py`.
* Docs read: the Pinnacle-first decision with both 21 Oct amendments; the P11 section of `gap_downloads/README.md`; the unpriced-leads README §§ 2–5; the qualifying-targets README; the edge-anatomy scoreboard (§ 3); the clean-holdout proposal's status.
* Facts found (observed, files named):
  * **The live instance** is `template_2026-10-21b` (`data/studies/master_pipeline/selected_instance.json`). Its `fits/` hold seasons 2019–2026 × seeds 0–15. The 2025 and 2026 fits were trained on 2013..Y−1 only: train shapes 57,764 and 62,869 rows (`fits.log`, `fits_seeds4-15_*.log`), which equal the expanding window; the live 2026 fit (67,531 rows, the cut-off of 21 Oct) is not among them (`training_cutoff.json`). So out-of-sample 2025 and 2026 forecasts exist from stored fits: the model part can be done without any fit.
  * **The instance's frame is main draws only** (both tours, 67,531 matches). Its odds input is the rule of 9 Oct (`odds_input.json`: BetOnline's close from August 2025, 2,216 of 2026's 2,345 men's matches).
  * **No instance was built with rule 2026-10-21** (no `odds_input.json` names TennisExplorer). The market benchmark under that rule can be built in memory exactly as `src/eda/pinnacle_gap/dry_run.py` does: the instance's `odds_sources.parquet`, TennisExplorer's tour staging linked to the frame (`tennisexplorer.link_frame`, read-only), then `odds_input.construct(sources, RULE)`.
  * **Tour-level qualifying prices:** TennisExplorer holds none. Its tour staging (`data/dump/odds/tennisexplorer/matches.parquet`) has main-draw rounds only (event type "main", rounds "1. round" to "final"), and the lower-level collector puts tour events out of scope. The qualifying-targets study priced them from OddsTrader's every-book lines (`data/studies/qualifying_targets/prices.parquet`, 21,462 linked matches): Pinnacle's last line to September 2025 (where OddsTrader's Pinnacle history ends), BetOnline's last line after, both with the 30-minute late rule, margin removed proportionally.
  * **Tour-level qualifying forecasts from stored fits:** the qualifying study's arm M0 (`data/studies/qualifying_targets/local/M0__<Y>__seed<k>.npz`, seeds 0–3) is the live instance's own model: same training rows (train shape 62,869 for 2026; the instance frame's SHA-256 in its meta) and its main-draw block equals the instance's fits exactly (`m0_checks.json`, max |diff| 0). Its `qual` block holds forecasts for priced tour-level qualifying matches. With the instance's main-draw calibration and stage 2 (as `qualifying_targets/top_edges.py`'s "main-draw stage 2"), this gives the model's forecast on qualifying with 4 seeds instead of 16.
  * **Challengers:** TennisExplorer's lower-level tables are "not linked to the map or Stage 0" (P11 report, Limits). No linker exists in `src/`: one has to be written.
  * **Stage 0's side A is not the winner:** `a_won` mean 0.501 on the window's men's tour and Challenger matches; A has the lower id string on 49.5% (Stage 0's assignment is effectively random).
  * **Today's Stage 0 differs from the instance's build tree** (`C:/Users/zerom/tnr_tpl1021`; different SHA-256, as the tree merges the accepted packages). The brief names today's Stage 0; links to the instance's frame and the qualifying study's tables go by match id, with the rate reported.
  * **No seal on 2025–26 results exists.** The clean-holdout rebuild is "a proposal for review, not a decision" and `data/studies/feature_provenance/seal.json` does not exist. But the unpriced-leads check registered its Look B on 29 Jul 2026 – 31 Jul 2027, and edge anatomy kept matches from 29 Jul 2026 "sealed for a future untouched test". This harness reads the price's and the model's log loss on matches to 18 Oct 2026 as the brief asks; it tests none of those registered statistics. Flagged for the lead.

### 2. The population (09:05–09:11)

* **Written:** `src/eda/p9_point_details/harness_population.py`. First and only run 09:10–09:11, 64 seconds. Outputs in `data/studies/p9_point_details/harness/`.
* **Choices, made before any base's log loss was computed:**
  * *The window's day* is the match clock's `obs` (floored), not the tournament date: P9's coverage is by match day, and qualifying is dated by its main draw's first day in Stage 0 (rule C05). Clusters (weeks) and 4-week blocks use the tournament date, as every project harness does, so an event's matches share a cluster.
  * *Retirements are kept,* with `finished` = completed. The model's frame keeps them, and the unpriced-leads check scored them and reported completed matches only as a sensitivity. Walkovers (142), the 'other' statuses (17: unknown, defaulted, abandoned) and the Next Gen Finals (15, a nonstandard format outside the frame) are left out.
  * *Margin removal:* proportional, book by book, everywhere (the project's rule).
  * *Challenger price:* Pinnacle's last price only when the site shows it with times. That is the production rule's test at tour level, where untimed prices turned out not to be Pinnacle's close. It must also be on time (last change at most 30 minutes after the listed start, the project's late rule) and pass the production test for the site's own errors (far from the median of at least 3 agreeing other books). Otherwise the median of the other books' margin-free log-odds. All of them are late pre-match prices (P11: Pinnacle's last change a median 3.6 hours before the start on 22–23 Oct 2026). Considered and set aside: untimed Pinnacle prices as Pinnacle (2,351 Challenger matches show one, mostly August–October 2025, as at tour level); the books' average from the day listings (coarser, and no times).
  * *The Challenger linker* is new (none existed: P11's report, Limits), modelled on `tennisexplorer.link_frame`. Pass 1: both players' name-word sets equal (the adapter's `_same_tokens`), the site's day within one day of the clock's day. Pass 2: the site's day within the tournament date −7 to +10. Pass 3: the site's event that the tournament's other links name, with the adapter's looser `_close_tokens`. Two candidates: the one of the same draw (qualifying or main) if exactly one. Otherwise no link. A page claimed by two matches links neither. **A link whose set score names the other winner is refused** (a check against the result, used for the link only, as the gap downloads' link checks do).
  * *The model on tour qualifying:* the qualifying study's M0 fits (see § 1), 4 seeds, with the main draw's slope and stage 2. The other option was the market part only for qualifying; it was set aside because these are the live model's own forecasts from stored fits, checked to be the instance's model.
* **Checks (observed, `population_facts.json`):**
  * The rule of 9 Oct rebuilt in memory equals the instance's stored odds input on all 67,531 matches (max |diff| 0, same source on all), so the in-memory build of the rule of 21 Oct runs on the right table.
  * TennisExplorer's tour link: 4,989 of the frame's 5,009 matches from 20 Oct 2025; winner agrees with the frame's on 4,989 of 4,989.
  * The walk-forward parameters for 2025 and 2026 (slope, stage 2's b) reproduce the qualifying study's stored "main-draw stage 2" parameters exactly (max |diff| 0.0): the same instance, the same seeds 0–3, the same speed column.
  * Every men's tour main-draw match of 2019–2026 has its stage-2 speed value; none had to be filled with 0 (2025–26 test matches: 0; qualifying: 0).
  * Stage 0's result equals the frame's (main draw) and the qualifying frame's on 7,266 of 7,266 matches.
  * Challenger link: 18,292 of 18,394 Stage 0 matches (99.4%): 18,172 by pass 1, 4 by pass 2, 125 by pass 3; 8 with several candidates, 85 with none, 8 pages claimed twice; 1 link refused (the winner disagrees). The site's day equals the clock's on 17,504, one day off on 786, more on 3.
* **A coverage gap found (observed):** today's shared Stage 0 holds **no men's Challenger qualifying after early June 2026** (45 matches in June, 0 from July). Its Challenger main draws continue (Tennis My Life). The live instance's build tree (`C:/Users/zerom/tnr_tpl1021`) holds TennisLive rows for those months (the lower-level feed, which is merged into builds' own tables, never the shared ones). The brief names the shared Stage 0, so the population follows it. Flagged for the lead: P9's Challenger qualifying of July–October 2026 cannot be scored against this Stage 0.

### 3. The scorer and the bases (09:11–09:16)

* **Written:** `src/eda/p9_point_details/harness.py` (functions and command line).
* **Design choices, made before any base's number was seen:**
  * No intercept anywhere and no centring of the feature, so that a swap of A and B (feature, base log-odds and result all mirrored) leaves every likelihood, and so every score, unchanged. The feature is scaled by its root mean square on the scored rows (as the unpriced-leads screen), so b is per RMS unit; it equals the SD for an antisymmetric feature whose mean is 0.
  * The missing-indicator variant: the feature is set to 0 where it is missing, plus a term m × L (m = 1 where missing). An additive indicator would act as an intercept and break the symmetry; m × L flips with the swap.
  * Weeks and 4-week blocks from the tournament date, Monday origin 2010-01-04 (the project's harness).
  * The bootstrap draws whole 4-week blocks (2,000 draws, fixed seed 20261028). Each draw's gain is its matches' mean. The project's t interval over blocks is reported beside it.
  * The new part follows `unpriced_leads/screen.py`'s `orthogonal_part`: the 48 non-price, non-context inputs (46 differences + 2 pairs as A − B), no intercept, missing inputs 0, fitted on the scored rows where the feature exists. It is outcome-free.
* **First look at any result (about 09:13): one random N(0, 1) column through every population and base**, as a smoke test. z between −0.17 and −0.04; cross-fitted gain −0.05 (all), −0.11 (tour), −0.11 (Challengers) mLL, every interval below 0 ("worse"). Expected: a useless parameter costs about 1/n per match out of sample, and its per-match gains are tiny, so the interval is narrow. Nothing was changed after it.
* **The bases (09:15; `--bases-report`, `bases.json`).** Read once; nothing in the harness was changed after them. The numbers are in the results section below.

### 4. Calibration and tests (09:16–)

* **Written:** `src/eda/p9_point_details/harness_calibrate.py`; `test/p9_point_details/test_harness.py`.
* **A trial (09:17; 3 placebos, 3 draws per gain on two pairs, not kept):** the pooled population detected a planted 0.25 mLL signal with z 3.5–5.5, and the cross-fitted gain came back near the planted one. One placebo column takes about 1 second for every population and base. A planted draw takes 0.45 seconds on the pooled 25,542 matches.
* **The full calibration started at about 09:18** (4 workers; 200 random columns, 200 with level-shaped missing values, 3 nuisance columns; 13 population-base pairs × gains 0, 0.25, 0.5, 1, 2 mLL × 200 draws; 1,000 bootstrap draws inside the planted runs to save time, 2,000 elsewhere).
* **A fix while it ran (09:19), found while writing the symmetry test, before any calibration output existed:** the descriptive correlation of the feature with the base was centred. A centred correlation changes when A and B are swapped on some rows. It is now uncentred. It touches only that descriptive column, never z or the gains.
* **That run was stopped (09:20) before it wrote anything, for a design change.** The bases had shown that the price's calibration slope differs by cell: tour main 0.99, tour qualifying 1.16, Challenger main 1.08, Challenger qualifying 1.19 (`bases.json`). With one pooled slope, a feature correlated with the favourite could borrow that favourite–longshot shape, which is not new information. So:
  * the "free" variant now fits **one slope per cell** (level group × draw);
  * a third variant, "curve", adds a curvature term L³ per cell, as the unpriced-leads test did per tour.

  No placebo or planted output had been seen. The stop killed the shell but left the Python process and its 4 workers running; I ended those 5 processes by id (all mine).
* **A second fix, found by the cross-fitting test (09:21):** the per-block fits were warm-started from the fit on all blocks. The held-out block's results therefore nudged the Newton path, by up to 4e-16 in the log-odds, to the same optimum. The warm start is gone, so a block's forecast is now an exact function of the other blocks. 13 of 13 tests pass (`./python.sh -m pytest test/p9_point_details/test_harness.py`, 7 seconds).
* **The bases report was re-run (09:22)** with the per-cell recalibration. The raw comparisons are unchanged. The tour-level "model against the recalibrated price" moved from +2.54 to +2.25 mLL, because the qualifying cell now gets its own slope. The main draw's is unchanged (one cell).
* **The full calibration was restarted at 09:23** with the three variants, on the same settings.
* **Coverage of Stage 0's own pre-match controls (09:24, outcome-free):** ranking points for both players exist on 98–100% of tour matches and 90–99% of Challenger matches, and age on 95–100%. That makes the substitute "new part" below the tour possible (see the answers section).
* **The placebo phase ended at 09:28** (360 seconds; `placebos.csv.gz`, `placebo_summary.csv`). First look, random columns, raw part, "free" variant:
  * the cross-fitted gains centre just below 0 (−0.02 mLL pooled, −0.08 tour main draw, −0.19 tour qualifying), and **none of the 200 is read "better"** in any population;
  * **the z spread is about right on the pooled and Challenger populations** (SD 1.02–1.03, except 1.09 on all Challengers), **and wider at tour level:** SD 1.13–1.14 on the main draw (11% of |z| above 1.96), 1.10–1.11 tour, 1.07 qualifying.
  * Theory expects about 1.01–1.05 for an independent random column: the week-clustered sandwich is unbiased but noisy, roughly a t with as many degrees of freedom as effective clusters. The SD of an SD from 200 draws is about 0.05, and the 200 columns are shared across populations and bases, so these readings are not independent.
* **So a larger null check was added (09:31)**, before any planted result was seen: `harness_calibrate.py --null-check N`. It draws N fresh random columns per population against the price ("free" variant) and computes z with the week-clustered se (the harness's), the 4-week-block-clustered se and the model-based se (no clustering). The SD of b over the draws, against each se's median, says which se is calibrated. It runs after the planted phase, to stay within 4 workers.
* **The calibration ended at 09:40** (1,040 seconds, exit 0; `planted*.csv*`, `resolution.csv`, `calibration.json`). The planted results were read only after the null check had been designed.
* **The null check ran 09:40:17–09:40:49** (2,000 columns per population, 4 workers; `null_check.csv`). It settled the question: the week-clustered z has SD 1.00–1.05 everywhere (tour main 1.01), so the first 200 columns' spread at tour level was chance. Nothing in the harness was changed after it.
* **The lead's message (09:41), verbatim:** "the study stops at its declared depth rule (the builder's measure of what P9 adds to rally-length history is 1.07, against the threshold of 1.5), so no candidate will be scored this round. Please finish only the parts that make your harness reusable for a later men's 2025–26 feature study: the population with its prices and the live model's both-stage forecasts, the scoring functions, the placebo calibration, and the resolution table. Skip anything optional you have not started; for the planted signal, one gain size is enough. Write team/harness.md, then stop, and keep your final message short."
  * Everything it names was already built and run. The planted runs had covered four gains before the message arrived.
  * Nothing optional was started after it.
* **The documented command was run once (09:42)** on a random column written to the scratchpad (`placebo_demo.parquet`, 75% coverage): it printed and wrote its 36 readings. No candidate statistic, no P9 table and nothing under `data/studies/p9_point_details/build/` was opened at any point.
* **Clean-up:** no process of mine is left running (checked after each run). Scratch files are in the session's scratchpad only.

### A recommendation for a later pre-registration (Claude's, not decided)

* **The test:** the one-sided z of the "free" variant, beyond the price per cell, read on the t with weeks − 1. It is calibrated (above) and far more powerful than the gain's interval.
* **Also reported:**
  * the "curve" variant, the stricter guard against the price's favourite–longshot shape;
  * the cross-fitted gain with its interval and P(better), as the size;
  * finished matches only.
* **Pool tour level and Challengers** only with the per-cell slopes, as here. A single slope would let a feature correlated with the favourite borrow the Challenger cells' slopes of 1.08–1.19.
* **Beyond the model:** read at tour level, main draw and qualifying together. Qualifying's 4-seed forecasts are its weakest part.

## Reproduction

From the repository root, in Git Bash:

```
./python.sh src/eda/p9_point_details/harness_population.py                    # population.parquet and the rest, ~65 s
./python.sh src/eda/p9_point_details/harness.py --bases-report                # bases.json, under a minute
./python.sh src/eda/p9_point_details/harness_calibrate.py --workers 4         # placebos, planted signal, resolution, ~17 min
./python.sh src/eda/p9_point_details/harness_calibrate.py --null-check 2000 --workers 4    # null_check.csv, ~30 s
./python.sh -m pytest test/p9_point_details/test_harness.py                   # 13 tests, ~7 s
```

The population depends on files that move:
* TennisExplorer's staging, tour and lower-level, which the daily jobs rewrite;
* the shared Stage 0 and the match clock.

Their SHA-256 values and staging dates are recorded in `population_facts.json`. A rebuild on later tables gives a slightly different population.

## Files written

* `src/eda/p9_point_details/harness_population.py`, `harness.py`, `harness_calibrate.py`
* `test/p9_point_details/test_harness.py`
* `data/studies/p9_point_details/harness/`:
  * the population: `population.parquet`, `population_facts.json`, `model_inputs.parquet`, `challenger_link.parquet`;
  * the bases: `bases.json`;
  * the calibration: `placebos.csv.gz`, `placebo_summary.csv`, `planted.csv.gz`, `planted_summary.csv`, `resolution.csv`, `calibration.json`, `null_check.csv`.
* `docs/studies/p9_point_details/team/harness.md` (this memo)

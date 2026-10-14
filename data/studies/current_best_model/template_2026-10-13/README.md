# The current best model, 13 October 2026: the lower-level feed

**What it is.** The current instance of the template ([decision](../../../../docs/decisions/2026-10-08-current-best-model.md)) as of 13 Oct 2026. It is the 10 Oct template, on the tables of 8 Oct, with **the lower-level feed's first snapshot** in place of the men's 2026 Challenger package ([decision](../../../../docs/decisions/2026-10-13-lower-level-feed.md), [report](../../../../docs/studies/data_gaps_2026/README.md)):
* the Pinnacle-first odds input, 57 inputs, the indoor input for every match (decisions of 9 Oct);
* **the level layer for men** ([decision](../../../../docs/decisions/2026-10-10-level-evidence-layer.md)). Its opponent strength is resolved on this build's Stage 0 and **re-centred** (the decided rule, "option c"): the women's additions moved the 2026 main-tour mean by 3.75 Elo (`chain_layer.json`);
* **the snapshot `../accepted_additions/lower_level_feed/20261013c/`**: 48,572 matches the history lacked, 5,743 with box scores. They are men's ITF from June 2026, men's Challenger qualifying of 2026 and Challenger main draws to 5 Oct; women's ITF, WTA 125 and its qualifying from June; tour qualifying from 18 May; Slam qualifying from 19 Jan (results only); and ITF qualifying from 16 Dec 2024 (results only).

**How it was built.** As the harm check's arm FEED (`data/studies/data_gaps_2026/harm/feed_instance/`, sandbox `C:/Users/zerom/tnr_gaps`):
1. The derived candidate `F20261013c_gaps` was installed as the sandbox's Stage 0 and timeline, then lane 0 ran.
2. The layer was resolved on that Stage 0, then lanes 1–3 ran with `--layer` (`build_template.sh C:/Users/zerom/tnr_gaps <folder> 1 <F20261013c_gaps>`), then `post_build.sh`.
3. Merging the snapshot into the frozen tables gives the same Stage 0 and timeline (`additions.py --check-against`), so this is a build of the decided recipe.

The folder was copied here after the harm check, with its seeds 0–3 fits. Seeds 4–15 were then fitted here: for season 2026 only, the season the daily pipeline predicts (`fits_seeds4-15_2026.log`). The other seasons have seeds 0–3, which is what the comparisons and stage 2 read. This instance is the bridge to the build on the day's tables with the Roland Garros repair (process log, § 3 addendum 2).

**The harm check** (process log § 3 addendum, fixed before any build): FEED (this build) against ON (`template_2026-10-10`), both tours, both stages, 2025–2026, 9,457 matches: **+0.044 mLL per match [−0.097, +0.185], P(better) 0.74, unresolved** (+ = this build better). So there is no harm, and it was adopted under the owner's rule. The gate passed first: on the 60,412 matches the additions cannot reach, every input equals ON's bit for bit, except the joint solves' (at most 1.4e-11 apart). Men +0.016 [−0.005, +0.038]; women +0.073 [−0.214, +0.359]. It is a harm check, not evidence of a gain, so no edge credit (`data/studies/data_gaps_2026/harm/feed.json`, `gate.json`).

## Files

| File | What |
|---|---|
| `model_frame.parquet`, `model_inputs.json` | The frame (Pinnacle-first odds input) and the 57-input list |
| `model_frame_chain.parquet`, `model_inputs_chain.json` | The chain's own frame (the books' average odds input) and its 58-column list |
| `chain_lane*.json`, `chain_layer.json`, `chain_logs/`, `chain_outputs/` | The build's records (lane 0 included) |
| `level_layer/` | The resolved config, the strength and its check, the hooks' records |
| `odds_input.json`, `odds_sources*`, `book_prices.parquet` (gitignored) | The odds input's record |
| `fits/model__<Y>__seed<k>.npz`, `fits.log`, `fits_seeds4-15*.log` | Local TabPFN-3.5 fits |

## Rebuild

```
bash data/studies/data_gaps_2026/harm/build_feed_arm.sh data/studies/data_gaps_2026/feed/candidates/F20261013c_gaps
./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out data/studies/current_best_model/template_2026-10-13 --seeds 4-15 --seasons 2026
```

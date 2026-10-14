# The current best model, 10 October 2026: the level layer and the accepted men's 2026 Challenger data

**What it is.** The current instance of the template ([decision](../../../../docs/decisions/2026-10-08-current-best-model.md)) as decided on 10 Oct 2026, on the tables of 8 Oct (today's live tables equal the frozen reference's):
* the Pinnacle-first odds input, 57 inputs, the indoor input for every match (decisions of 9 Oct);
* **the level layer for men** ([decision](../../../../docs/decisions/2026-10-10-level-evidence-layer.md)): config `../level_layer/official.json`, resolved for this build in `level_layer/build_config.json` (the opponent strength on this build's Stage 0: `level_layer/strength_check.json`);
* **the accepted men's 2026 Challenger and Challenger-qualifying matches** ([decision](../../../../docs/decisions/2026-10-10-men-2026-challenger-data.md)): 1,735 matches and one box score, the package `../accepted_additions/men_2026_ch_chq/`.

**How it was built.** As the 2026 data's candidate: role F's additions installed as the sandbox's Stage 0 (`data/studies/level_layer_adoption/stage0/C0_men26/`), lane 0, the layer resolved on that Stage 0, lanes 1–3 with `--layer` (`build_template.sh C:/Users/zerom/tnr_lyr_new <folder> 1 <C0_men26>`), then `post_build.sh`. Merging the accepted package into the frozen tables (`run_chain.py --additions`, the decided route) gives that Stage 0 and timeline exactly (`additions.py --check-against`), so this is a build of the decided recipe. The folder was copied from `data/studies/level_layer_adoption/candidate_men26/` after the harm check, with its seeds 0–3 fits; seeds 4–15 were fitted here.

## Files

| File | What |
|---|---|
| `model_frame.parquet`, `model_inputs.json` | The frame (Pinnacle-first odds input) and the 57-input list |
| `model_frame_chain.parquet`, `model_inputs_chain.json` | The chain's own frame (the books' average odds input) and its 58-column list |
| `chain_lane*.json`, `chain_layer.json`, `chain_logs/`, `chain_outputs/` | The build's records (lane 0 included) |
| `level_layer/` | The resolved config, the strength and its check, the hooks' records |
| `odds_input.json`, `odds_sources*`, `book_prices.parquet` (gitignored) | The odds input's record |
| `fits/model__<Y>__seed<k>.npz`, `fits.log`, `fits_seeds4-15.log` | Local TabPFN-3.5 fits, seasons 2019–2026, seeds 0–15 |

## Rebuild

```
bash data/studies/level_layer_adoption/build_template.sh <sandbox> data/studies/current_best_model/<date> 1 accepted
bash data/studies/level_layer_adoption/post_build.sh data/studies/current_best_model/<date>
./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out data/studies/current_best_model/<date> --seeds 0-15 --seasons 2019-2026
```

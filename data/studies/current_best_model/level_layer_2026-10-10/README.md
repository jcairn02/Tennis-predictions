# The current best model with the level layer, 10 October 2026

**What it is.** A build of the current best model's template ([decision](../../../../docs/decisions/2026-10-08-current-best-model.md)) with the level layer for men ([decision](../../../../docs/decisions/2026-10-10-level-evidence-layer.md)), on the tables of 8 Oct 2026 (today's live tables equal the frozen reference's). It is the "with the layer" arm of the layer's harm check, and the base of the 2026 data's candidate ([decision](../../../../docs/decisions/2026-10-10-men-2026-challenger-data.md)).
* **Built** by `data/studies/level_layer_adoption/build_template.sh C:/Users/zerom/tnr_lyr_on <this folder> 1` (sandbox kept): `run_chain.py --setup`, `--prepare-layer`, lanes 1–3 with `--layer`, `--collect`; then `post_build.sh` (the chain's frame kept as `model_frame_chain.parquet`; `odds_input.py --apply`; `template_inputs.py --apply`).
* **The sandbox was deleted on 14 Oct 2026** (the owner's go-ahead). The files code still read from it are copied,
  byte for byte, in `data/studies/level_layer_adoption/sandbox_extracts/tnr_lyr_on/` (its README). `level_layer/build_config.json`
  below still names the sandbox's strength table: that is the record of this build, and the copy holds the same file.
* **The layer's config:** `level_layer/build_config.json`, resolved from `data/studies/current_best_model/level_layer/official.json` with the opponent strength on this build's Stage 0 (`level_layer/strength_check.json`: equal to the frozen strength bit for bit on all 873,437 matches). The hooks' records: `level_layer/layer_calls/`.
* **Its inputs equal the study's SYS arm's bit for bit** on every input the decision keeps (`indoor` carries the decided fill; `ios_points_short`, switched off, equals the reference's): `data/studies/level_layer_adoption/checks/fidelity.json`.

## Files

| File | What |
|---|---|
| `model_frame.parquet`, `model_inputs.json` | The frame with the Pinnacle-first odds input and the 57-input list |
| `model_frame_chain.parquet`, `model_inputs_chain.json` | The chain's own frame (the books' average odds input) and its 58-column list |
| `chain_lane*.json`, `chain_layer.json`, `chain_logs/`, `chain_outputs/` | The build's records |
| `level_layer/` | The resolved config, the strength and its check, the hooks' records |
| `odds_input.json`, `odds_sources*.`, `book_prices.parquet` (gitignored) | The odds input's record |
| `fits/model__<Y>__seed<k>.npz`, `fits.log` | Local TabPFN-3.5 fits, seasons 2019–2026, seeds 0–3 (`src/eda/model_rebuild/fits.py`) |
| `vs_reference_2026-10-08/` | `compare.py` against the frozen reference (2020–2024) |

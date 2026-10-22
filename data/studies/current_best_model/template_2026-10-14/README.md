# The current best model, 14 October 2026: the day's tables, the lower-level feed and the Roland Garros repair

**What it is.** The current instance of the template ([decision](../../../../docs/decisions/2026-10-08-current-best-model.md)), built on **the day's tables**: the live tables rebuilt on 13 Oct 2026 (21:12–21:48 PDT), with every decided change in:
* **the Roland Garros repair** ([decision](../../../../docs/decisions/2026-10-09-roland-garros-box-scores.md), adopted 10 Oct, applied 13 Oct 21:12): RG's own box scores for 2022–2026, including the 254 main-draw matches of 2026 that had none, and the corrected service games of the Australian Open and Roland Garros;
* **Tennis My Life's own lower-level corrections** ([decision](../../../../docs/decisions/2026-10-13-tml-lower-level-revisions.md), 13 Oct), including the four 2022–2025 Challenger files accepted that day;
* **the lower-level feed's first snapshot** `../accepted_additions/lower_level_feed/20261013c/` ([decision](../../../../docs/decisions/2026-10-13-lower-level-feed.md)), merged into the build's own tables (48,529 added, 43 already present);
* the Pinnacle-first odds input, 57 inputs, the indoor input for every match, and the level layer for men. The layer's opponent strength is re-centred (option c): the women's additions moved the 2026 main-tour mean by 3.75 Elo.

**How it was built.** `data/studies/data_gaps_2026/build_final.sh`, which runs `build_template.sh C:/Users/zerom/tnr_tpl1014 <this folder> 1 accepted` and then `post_build.sh`.
* The session running it ended at 00:30 on 14 Oct, which stopped lane 1 at `elo_pieces`. `data/studies/data_gaps_2026/resume_final.sh` resumed it from that step at 07:01 (`run_chain.py --lane 1 --from elo_pieces --layer`; the lane's record is appended).
* Fits are local TabPFN-3.5: seeds 0–3 for 2019–2026, seeds 4–15 for 2026, then the other seasons' seeds 4–15.

**Checks.**
* **History against the frozen reference** (the build's own setup): 2,964 decided repairs and 104 of Tennis My Life's own lower-level changes, both allowed; 9 main-tour changes (Davis Cup and Laver Cup records, one Båstad match); nothing gated.
* **`compare.py` against the reference** (`vs_reference_2026-10-08/`; seasons 2020–2024, both stages; + = this build better): +0.014 [−0.336, +0.365] mLL per match, unresolved, P(better) 0.53. Across the odds change it resolves only about ±0.35.
  * **Its input check:** 19 inputs flagged uneven, each from a decided change's own dose:
    * 11 were already in the 10 Oct instance;
    * the feed adds the women's 2026 surface layoffs;
    * the repair adds the women's 2013–2014 hold and break inputs (the filled service games its 10 Oct check recorded) and the women's 2026 forms (Roland Garros 2026's box scores).
  * The report's process log, `docs/studies/data_gaps_2026/process_log.md`, has the attribution.
* **The replay check** (2026-07-13 R16, with Tennis My Life held as this build read it: the frozen view `C:/Users/zerom/tnr_dump_freeze_1014`, freeze 2026-10-14T04:12:16Z, set through `DP_FREEZE_DUMP`): 23 matches, none missing from the frame; every IOS input equal; **18 of 23 matches equal on every input; 5 men's (Umag ×3, Båstad ×2) differ on the level layer's 15 Stage B forms by at most 4.5e-6**; the 8 women's equal bit for bit (`daily_prediction/runs/replay_2026-07-13_R16_20261014T075546/replay_compare.json`). The cause, as for the 13 Oct bridge (4 men's matches): option (c)'s shift is a mean over each season, and a replay drops the replayed events' later rounds (the process log's judgment call 8).

## Files

| File | What |
|---|---|
| `model_frame.parquet`, `model_inputs.json` | The frame (Pinnacle-first odds input) and the 57-input list |
| `model_frame_chain.parquet`, `model_inputs_chain.json` | The chain's own frame (the books' average odds input) and its 58-column list |
| `chain_additions.json`, `chain_lane*.json`, `chain_layer.json`, `chain_logs/`, `chain_outputs/` | The build's records |
| `level_layer/` | The resolved config, the strength and its check, the hooks' records |
| `odds_input.json`, `odds_sources*`, `book_prices.parquet` (gitignored) | The odds input's record |
| `fits/model__<Y>__seed<k>.npz`, `fits*.log` | Local TabPFN-3.5 fits |
| `vs_reference_2026-10-08/` | `compare.py`'s output |
| `build_final.log`, `build.out`, `lane*.out`, `post_build.out`, `compare.out` | The run's logs |

## Rebuild

```
./python.sh src/eda/rg_first_serve_recount/adopt.py --apply     # once: the decided tables (done 13 Oct 21:12)
./python.sh src/eda/data_continuity/rebuild_stage0.py            # the live tables on the day's files
bash data/studies/data_gaps_2026/build_final.sh <sandbox> data/studies/current_best_model/<date>
```

You are the return-elasticity builder for the serve/return-leads study in the Tennis predictions repository (C:\Users\zerom\Documents\Tennis-predictions). The lead is Claude, session 6483c720-30a3-46ff-9519-287690b6f9d8. Read CLAUDE.md first (environment, timing and process rules).

**Context.**
* **The finding.** The edge-anatomy study (docs/studies/edge_anatomy/README.md) found that from January 2025 to 28 July 2026, the close over-rated men's long-memory serving records and under-rated their returning strength.
* **The model's return ratings are additive.** They are IOS D (`src/eda/match_timing/ios_time.py`: y = logit((x + ½)/(d + 1)) − logit(μ) ~ O_server − D_returner). So they already measure each returner against each server's normal level.
* **What is not in the model.** The owner asked for "return quality measured against each server's normal level". The version the model lacks is the non-additive one: does a strong returner gain more, or less, against big servers than the additive rating predicts?
* This is the unpriced-leads long list's PS10, never built (`data/studies/unpriced_leads/longlist.csv`). The note there reads "needs the clock and a reliability gate; similar splits failed".
* This work is diagnostic and exploratory; nothing in production changes.

**Hard rules.**
1. **No unseen results.** No match result with a tournament date of 29 Jul 2026 or later may be read, printed, or loaded alongside values.
   * Read match outcomes only through `src/eda/serve_return_leads/readings.py` (`seen_frame()`, `read()`, `fit_joint()`), which enforces this.
   * Box-score facts (points won) of matches that finished before a target match are inputs, and are allowed for building values. Never use a box score dated 29 Jul 2026 or later in any reading of results.
2. **Do not edit any existing file.** Import existing modules.
   * Another session is editing the live prediction code today.
   * Touch nothing under `src/eda/daily_prediction`, `src/pipeline`, `data/studies/unpriced_leads/check_now`, or the `data/studies/current_best_model/` folders.
3. **Commands.** Use `./python.sh` (Git Bash). Run no git command that changes state. Delete no file.
4. **Where things go.**
   * Code: `src/eda/serve_return_leads/elasticity.py`.
   * Outputs: `data/studies/serve_return_leads/elasticity/`.
   * A memo: `docs/studies/serve_return_leads/team/elasticity_builder.md`.

**The task: build PS10.**
1. **The residuals.** For each returner j, use his earlier matches: any level with a box score, strictly before the target match could start (`lf + 1 ≤ es` on `data/studies/match_timing/timing.parquet`). The residual is his return points won against the IOS prediction from the server's pre-match O_spw and his own pre-match D_spw.
   * The ratings: `data/studies/surface_ios/surface_features.parquet`. Its `srf_O_eff_spw_a/b` and `srf_D_eff_spw_a/b` are each match's pre-match values, and their A − B differences correlate 0.996–0.999 with the model's own IOS inputs.
   * Check how they map to the IOS prediction (the solver's μ and logit), and to the box score's serve and return points.
   * Stage 0 has the box scores; see `screen.long_table()` in `src/eda/unpriced_leads/screen.py`.
2. **The slope.** Regress the residuals on the server's O (centred). Choose a decay half-life before reading (e.g. 365 days), and shrink toward 0 by empirical Bayes, from the split-half reliability of the slopes. This uses points from earlier matches, never match results.
3. **The matchup term** at match m, A − B: b_A·(O_B − Ō) − b_B·(O_A − Ō).
4. **Report the reliability:** the split-half correlation of b_j across a player's alternate matches.
5. **Timing probe:** as in `src/eda/unpriced_leads/screen.py`'s `timing_probe`.

**Readings.**
* Only through `readings.read(seen_frame('atp'), x, 'PS10', sign=+1)`. The direction, registered before reading, is +: a returner who gains more against big servers beats the close when he faces a big server.
* Report the windows `read` gives: raw and orth, beyond the close and beyond the model.
* Also give women's readings with `seen_frame('wta')`, as a contrast.

**Report back** in your final message:
* the construction, coverage, reliability and probe results;
* the readings;
* what you read and when, with times, for the lead's process log;
* your recommendation: is PS10 worth registering for the check on unseen matches?

Keep the memo factual, and separate what you observed from what you infer.

You are the speed builder for the serve/return-leads study in the Tennis predictions repository (C:\Users\zerom\Documents\Tennis-predictions). The lead is Claude, session 6483c720-30a3-46ff-9519-287690b6f9d8. Read CLAUDE.md first (environment, timing and process rules).

**Context.** The edge-anatomy study (docs/studies/edge_anatomy/README.md) found that from January 2025 to 28 July 2026, men whose first-serve speed had recently risen above their own normal beat the closing line more often than it priced them. The column is the serve-speed stage's 28-day speed memory, `spd_L_B` (data/studies/infosys_atp_backfill/speed_columns_augmented.parquet): z +3.8 beyond the close there, about +1.5 in 2020–24, and it cost in 2023. The owner wants cleaner speed data: second serves, and how speed fades during a match. This work is diagnostic and exploratory; nothing in production changes.

**Hard rules.**
1. **No unseen results.** No match result with a tournament date of 29 Jul 2026 or later may be read, printed, or loaded alongside values.
   * Read outcomes only through `src/eda/serve_return_leads/readings.py` (`seen_frame()`, `read()`, `fit_joint()`), which enforces this.
   * Do not load `a_won`, `won`, scores or any other result column from any other file. Building values needs no result.
2. **Do not edit any existing file.** Import existing modules (`src/eda/serve_speed_tabpfn/...`, and the `build_on` pattern of `src/eda/infosys_atp_backfill/columns.py`). If needed, patch module attributes inside your own process only, as `build_on` does.
   * Another session is editing the live prediction code today.
   * Touch nothing under `src/eda/daily_prediction`, `src/pipeline`, `data/studies/unpriced_leads/check_now`, the speed panels in `data/studies/serve_speed_tabpfn/live/`, or the `data/studies/current_best_model/` folders.
3. **Commands.** Use `./python.sh` (Git Bash) for Python. Run no git command that changes state. Delete no file.
4. **Where things go.**
   * New code: `src/eda/serve_return_leads/` (e.g. `speed_ext.py`).
   * Outputs: `data/studies/serve_return_leads/speed/`.
   * A memo: `docs/studies/serve_return_leads/team/speed_builder.md`.

**Tasks.**

A. **Second-serve speed form.** Build the analogue of `spd_L_B` for the second serve.
   * Use the same builder: `serve_speed_tabpfn/adaptive/columns.py`'s `build`, run on the augmented history (`live_panel.BACKFILLED`) as `infosys_atp_backfill/columns.py`'s `build_on` does.
   * Replace the history's first-serve speed value with the second-serve speed (`spd2`, its count `n2`). Check how `y`, `y_raw`, `n`, `basis`, `use` and the edition offsets enter the filter, and replace them consistently. Rows without `spd2` are not used.
   * First confirm that `build_on` on the augmented history reproduces `speed_columns_augmented.parquet`'s `spd_L_B` exactly.
   * Name the result `spd2_L_B` (and `spd2_T_B` if it is cheap).
   * Re-estimate nothing that needs results. If the filter's constants (q, s2f, the noise terms, the standardiser) are specific to the first serve, state how you set them for the second serve: outcome-free choices only, e.g. the second-serve series' own variances.

B. **First-minus-second gap.** Either the form of (first − second) speed, or the difference of the two forms. Say which and why, before reading.

C. **Fault speed.** `fault1` (the mean speed of first-serve faults) exists only for 2025–26.
   * Assess what can be built (e.g. fault speed minus first-serve-in speed, against the player's own 2025–26 normal), and its coverage.
   * There is no history before 2025 to discover on, so any 2025–26 reading is descriptive only.

D. **The fade within a match.**
   * Find whether point-level speeds with point order exist on disk: the panel's point-level sources are slam_pbp, slamtracker, slam_tracking, infosys_slams and ausopen_mc; find their raw files.
   * The statistic: for each player's previous match within 14 days, last-third minus first-third first-serve speed, against his own normal fade.
   * Report coverage by year and level.
   * Build it if at least the Slams from 2015 can be covered. Otherwise report what would be needed: the ATP Stats Centre per-point files (collection package P9, approved but not collected).

E. **Timing.**
   * Every value uses only matches that surely finished before the target match could start: the builder's release rules for A–C. For D, use `data/studies/match_timing/timing.parquet`: a match's information is usable from `lf + 1`, and the target reads at `es`.
   * Run a cut-scramble probe for each new column: replace the speeds of rows released after a cut day with random values, rebuild, and confirm that no value of a target with es ≤ cut moves (as `features.py`'s Probe B does).

F. **Readings.**
   * For each new column, register its direction, and the reason for it, in the memo **before** reading.
   * Then call `readings.read(seen_frame('atp'), x, name, sign)`.
   * Report the z's by era (2013–16, 2017–19, 2020–22, 2023–24), then 2013–24, 2020–24 and 2025–26: raw and orth, beyond the close (`L`) and beyond the model (`L_model`).
   * Read `spd_L_B` itself the same way for comparison.
   * Add a joint fit (`readings.fit_joint`) of `spd_L_B` with your second-serve column beyond the close, in 2025–26 and in 2013–24.
   * Men only: the women's speed columns are 0 in the model.

**Report back** in your final message:
* what you built, its coverage and the probe results;
* the readings table;
* what you read and when, with times, for the lead's process log;
* your recommendation: which speed extension, if any, is worth registering for the check on unseen matches.

Keep the memo factual, and separate what you observed from what you infer.

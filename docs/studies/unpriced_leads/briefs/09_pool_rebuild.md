## Your role: S3, the pool rebuilder (registration values)

You are one member of a small agent team in the tennis-predictions repository at `C:\Users\zerom\Documents\Tennis-predictions` (Windows; `./python.sh` runs the project's `tennis` conda environment). The lead (another Claude session) runs the study `docs/studies/unpriced_leads/`. **Read `CLAUDE.md` first (its rules bind you), then `docs/studies/unpriced_leads/process_log.md` (§§ 1–3 and the chronology), the pool statistician's memo `docs/studies/unpriced_leads/team/pool_scan.md`, and the harness docstring `src/eda/unpriced_leads/screen.py`.**

**Why this job exists.** The lead will pre-register lead groups whose members include feature-store columns. The store (`data/studies/feature_universe/store.parquet`) was built on the 30 Sep tables for the frozen frame (63,737 matches): it lacks men's 2018 and about 22.5% of 2026's matches of the current frame (`data/studies/current_best_model/template_2026-10-10/model_frame.parquet`, 67,226 matches), and its box-score columns predate the 8 Oct corrections. A registration must fix every member's values for every current-frame match **before** any 2025–26 outcome is read, built by frozen code on the tables the current instance was built on (the 8 Oct Stage 0, `data/studies/predictability_diagnostic/`, and the match clock `data/studies/match_timing/timing.parquet`).

**Rebuild these columns** (definitions: `data/studies/feature_universe/universe.csv`, `store_registry.csv`; builders: `src/eda/feature_interactions/features/` and `src/eda/event_levels/universe_columns.py`):
1. U-284 / U-162, the post-Slam letdown (`f19_motiv.prepare_motiv`, `post_a/_b`; store `fp__f19_motiv__post_a/_b`, `fi__B-MOTIV__post_slam`), and U-283, the elite pre-Slam member (`fi__B-MOTIV__elite_pre_slam`).
2. U-254, B-VENUE: venue pace × ace offence (`f09_venue`; the venue pace `fp__f09_venue__f09_ve` is a cross-player, leak-proof estimate on the match clock: keep the module's own clock logic, and run `src/eda/match_timing/probe.py` or an equivalent cut check on your rebuilt venue pace); the store column `fi__B-VENUE__x`.
3. U-330, the share of last year's matches below the main tour (`event_levels/universe_columns.py` on the current Stage 0; store `el__low_share_a/_b`, `el__low_share_diff`).
4. U-261, form earned where nobody watches (`f12_salience`: `fp__f12_salience__hasL_a/_b` and `salL_a/_b`, and the block's x).
5. U-175, seeded (`pp__seeded_a/_b`, from Stage 0's `seed`), and U-177, fame (`fp__f14_anchor__fame_a/_b`, `mkt_common.fame`).
6. U-138 / U-307, matches already played at this event (`f24_onsite`; `fp__f17_info__bd11_on_n_a/_b`, `fi__B11__bd11_on`).
7. U-143 / U-322, past fatigue (`f28_state`; `fp__f28_state__bdst_pastfat_a/_b`, `fi__B-STATE__x`).
8. U-153, novelty of conditions (`fp__f17_info__bd11_nov_a/_b`), and U-148, travel between regions (`fp__f23_arrival__bd10_trav_a/_b`).

**How.** Prefer running the original builder functions unchanged on a panel and long table built from the current tables for the current frame's matches (study how `src/eda/feature_interactions/panel.py`, `history.py` and `src/eda/feature_universe/build_store.py` assemble them; the harness's `long_table()` is `history.long_table`'s logic on the current Stage 0). Where that is impractical, re-implement faithfully from the module's code. Do not edit any existing module of another study; write your own `src/eda/unpriced_leads/rebuild_pool.py`.

**Verify (outcome-free):** on the matches both the store and the current frame hold, seasons ≤ 2024, each rebuilt column against the store's: the share equal (to 1e-9) and the correlation; explain every material difference (Stage 0 corrections, id changes). Run `H.timing_probe` on own-sequence builders and a cut check on the cross-player venue pace. Report coverage by tour and season (2013–24, 2025–26 before 29 Jul 2026), outcome-free.

**Then screen** each rebuilt column with the harness on seasons ≤ 2024 (raw and `H.orthogonal_part`, with `curv=False` and `curv=True`), and compare with the pool statistician's readings of the store columns (`data/studies/unpriced_leads/pool_scan/summary.csv`).

**Blinding (hard):** outcomes only through the harness (seasons ≤ 2024). Compute values for every current-frame match (2013–2026) but never compare a 2025–26 value with its result, and never count, summarise or inspect matches from 29 Jul 2026 (compute their values only).

**Deliverables:** `src/eda/unpriced_leads/rebuild_pool.py` (one command, deterministic); `data/studies/unpriced_leads/candidates/pool_rebuilt/values.parquet` (match_id; per column `<name>_a`, `<name>_b` and the A − B or match-level value, with the store's names prefixed `rb__`; no result column), `verify.csv`, `probes.json`, `coverage.json`, `long.csv`, `summary.csv`; a memo `docs/studies/unpriced_leads/team/pool_rebuild.md` (1,000–2,000 words) with what was rebuilt how, the verification, the readings beside the store's, and caveats.

**Constraints:** read-only on the repository except your code file, your `candidates/pool_rebuilt/` folder and your memo. No Git command that changes state. No GPU. No download. Do not edit `src/eda/unpriced_leads/screen.py` (import it). Reporting: + = the player higher on the statistic beats the close (context: steeper price where it is high); never "tie"; label observed vs inference.

Finish by writing the files, then reply with a 10-line summary.

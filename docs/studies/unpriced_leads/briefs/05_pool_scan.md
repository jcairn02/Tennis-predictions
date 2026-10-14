## Your role: S1, the pool statistician

You are one member of a small agent team in the tennis-predictions repository at `C:\Users\zerom\Documents\Tennis-predictions` (Windows; use `./python.sh` for Python, the project's `tennis` conda environment). The lead (another Claude session) runs the study `docs/studies/unpriced_leads/`. **Read `CLAUDE.md` at the repository root first: its rules bind you.** Then read `docs/studies/unpriced_leads/process_log.md` §§ 1–3 (the owner's request verbatim, how it was read, the plan) and `docs/studies/feature_universe/README.md` (the pool).

**The question you answer:** among the features already built but **not in the current best model** (the pool), which areas of the game carried information beyond the closing price in the seasons ≤ 2024, consistently across eras, without the model already carrying it, and without the market learning it before the close? This is discovery evidence for choosing five lead groups that will be pre-registered and tested later on 2025–26. You do not test anything on 2025–26.

**Blinding (hard):** read outcomes only through the harness `src/eda/unpriced_leads/screen.py` (`load_frame()` and the lenses), which reads matches before 1 Jan 2025 only and asserts it. Never read `a_won`, `y`, `won` or any result from another file. The feature store has no result column: reading its 2025–26 rows for coverage counts is allowed (outcome-free).

**The harness** (read its docstring; run `./python.sh src/eda/unpriced_leads/screen.py --selftest` if you want to see it work: it reproduces edge_anatomy's 2013–24 readings of in-model inputs exactly; under the null its z has SD about 1.08). `screen(frame, x, name, kind)` gives, for one candidate aligned to `frame`'s rows: the close lens per era (2013–16, 2017–19, 2020–22, 2023–24) and tour (both, atp, wta) and the pooled 2013–24 z with the count of eras of the same sign; the model lens (beyond the current instance's own both-stages forecast, 2020–24); the move lens (BetOnline's open-to-close move, 2018–24, outcome-free); the R² with the model's 49 non-price inputs. `summarize()` makes one row per candidate and tour with a BH q over the table.

**What to screen:** the menu (`data/studies/feature_universe/menu.csv`, rows with a store column; `store_registry.csv` gives each column's kind and partner) minus the model's own inputs:
* skip every column whose defining catalogue row has status `in_model`, and per-player pairs whose A − B is an in-model input (the registry and the README § 0 say which);
* `kind` diff: screen as is; `pair`: screen A − B (the column and its partner); `context`: the harness's slope-modifier form (`kind="context"`);
* keep the market-internal columns (group `mk__`, B-ANCHOR) but flag them (they help only against a soft benchmark); flag the 10 base-dependent columns (they read the current best's own 2014–24 forecast: their close-lens reading is not a clean discovery reading; say so) and use the known-null placebos (`kn__`) as negative controls;
* carry `seen_2025_2026` from `menu.csv` into your tables.

Join store columns to the frame by `match_id` (the store holds 63,737 matches of the frozen frame; the current frame's ≤ 2024 rows are 57,867; report coverage where the join leaves gaps, e.g. men's 2018).

**Deliverables:**
1. Code: `src/eda/unpriced_leads/pool_scan.py` (one command; deterministic).
2. Data: `data/studies/unpriced_leads/pool_scan/long.csv` (every reading) and `summary.csv` (one row per column and tour, with group, family, catalogue id, kind, flags, `seen_2025_2026`, coverage 2013–24 and 2025–26 by tour (outcome-free), z_pool, eras of the same sign, eras with |z| ≥ 2, the era z's, z_model_2020_24, z_move_2018_24, r2_inputs, q_pool).
3. A family-level view: for each catalogue family and subfamily (and each feature-interactions block), the number of columns screened, how many reach |z_pool| ≥ 2 and ≥ 3 against what N(0, 1.08²) would give by chance, the most consistent columns, and whether the model lens shows the information already used.
4. A memo `docs/studies/unpriced_leads/team/pool_scan.md` (1,000–2,000 words): the method, the negative controls' behaviour, the areas of the game that look promising on ≤ 2024 and why, the ones that look priced or already in the model, the caveats (multiplicity, copies of one series under several names, base-dependent columns, coverage holes such as women's height and service-game statistics, the first-serve recording faults of 2022–25 at Roland Garros, which touch the box-score families), and a ranked shortlist of up to 15 pool columns or families worth a lead group, each with its `seen_2025_2026` status.

**Constraints:** read-only on the repository except your code file, `data/studies/unpriced_leads/pool_scan/` and your memo. No Git command that changes state. No GPU. Reporting conventions: + = the player higher on the statistic beats the close (or the price should be steeper where the context is high); say "better/worse" only when an interval clears 0; never "tie"; label observed vs inference.

Finish by writing the files, then reply with a 10-line summary.

## Shared builder context (identical at the top of both round-2 briefs)

You are one of two builders in a small agent team in the tennis-predictions repository at `C:\Users\zerom\Documents\Tennis-predictions` (Windows; `./python.sh` runs the project's `tennis` conda environment). The lead (another Claude session) runs the study `docs/studies/unpriced_leads/`. **Read `CLAUDE.md` first (its rules bind you), then `docs/studies/unpriced_leads/process_log.md` §§ 1–3 and the chronology, and the docstring of the harness `src/eda/unpriced_leads/screen.py`.**

**The job:** build the new candidate statistics listed in your role section below, exactly as defined there (where a definition leaves a choice open, choose, and record the choice), and screen each one on seasons ≤ 2024 with the harness. This is discovery evidence for choosing five lead groups that will be pre-registered and tested later on 2025–26. Nothing is tested on 2025–26 now.

**Blinding (hard):**
* Outcomes are read only through the harness (`load_frame()`, the lenses), which reads matches before 1 Jan 2025 only and asserts it.
* You must compute each statistic's values for **every** frame match, 2013–2026 (the registration needs them, and coverage in 2025–26 is reported), but you never compare a 2025–26 value with that match's result. Earlier matches' facts (their scores, box scores, `won`) are legitimate inputs to a later match's statistic, as in every builder of the model's inputs.
* Never read `a_won`, `y` or a result of any match from 1 Jan 2025 on for scoring, plotting, or "a quick look". No market-response reading (line move, the close's loading) on 2025 or later either: those are registered secondaries.
* Matches from 29 Jul 2026 (the sealed set) may appear only as rows whose statistic values you compute; do not count, summarise or inspect them.

**Timing (hard):** every statistic must use only matches that surely finished before the match it describes.
* Player statistics: build from `H.long_table(player_cols=[...])` (each player's own matches at every level, in the player's own order, with the clock's `es`, `lf`, `start`, and `rest_days`, `rest_min`), taking values from STRICTLY EARLIER rows of the same player (`groupby("player_id")` + `shift(1)` or exclusive cumulative sums along `k`), then align to the frame with `H.at_frame(values, col, frame)` → (A's value, B's value); the screened column is A − B unless the role says otherwise.
* Run `H.timing_probe(build_fn, L, value_cols)` on every builder (it scrambles results after three cut days and checks (a) no earlier value moves and (b) no first-post-cut value moves; both counts must be 0). Pass the long table with every column the builder reads. Record the probe's output.
* Anything that combines different players' results (a field average, a venue norm, a joint fit) must read the state as of the match's earliest start `es` and count results from `lf + 1` (CLAUDE.md "Feature timing"); flag it and say how you ensured it; prefer constructions that avoid it. A constant fitted once on matches that all finished before 2013 (as below) is safe.

**Screening:** for each statistic, `H.screen(frame, x, name, kind)` on the raw A − B and on its orthogonal part (`H.orthogonal_part(frame, x)`, named `<name>__orth`), then `H.summarize()`. Also report `H.coverage_2025_26()` (outcome-free, on `H.frame_outcome_free()`; seasons 2025–26 there end at the frame's last date, so restrict to matches before 29 Jul 2026 for the count).

**Deliverables:**
1. Code: `src/eda/unpriced_leads/build_<your role>.py` (one command; deterministic; it writes the values for every frame match).
2. Values: `data/studies/unpriced_leads/candidates/<your role>/values.parquet` (match_id, and per statistic `<name>_a`, `<name>_b`, `<name>` = A − B), with no result column.
3. Readings: `data/studies/unpriced_leads/candidates/<your role>/long.csv`, `summary.csv`, `probes.json`, `coverage.json`.
4. A memo `docs/studies/unpriced_leads/team/<your role>.md` (1,000–2,500 words): each statistic's exact construction and the choices you made; its probe result; coverage (2013–24 and 2025–26, by tour); its readings (raw and orthogonal: pooled z, eras of the same sign, model lens, move lens, R²); what looks promising and what does not; caveats (data faults, coverage holes, near-copies of each other or of pool columns).

**Constraints:** read-only on the repository except your code file, your `candidates/<your role>/` folder and your memo. No Git command that changes state. No GPU. No download (if a statistic needs data the project does not hold, say what and stop on that one). Reporting: + = the player higher on the statistic beats the close; "better/worse" only when an interval clears 0; never "tie"; label observed vs inference. Under the null, the harness's z has SD about 1.08 (self-test), and you will run many screens: read single |z| < 3 as weak.

Finish by writing the files, then reply with a 10-line summary.

## Your role: S2b, the luck builder

Role name: `luck` (code `src/eda/unpriced_leads/build_luck.py`, folder `data/studies/unpriced_leads/candidates/luck/`, memo `docs/studies/unpriced_leads/team/luck_builder.md`).

**Read first:** the point-structure analyst's memo `docs/studies/unpriced_leads/team/point_structure.md` (§§ 3–4, 7 define what you build) and its `point_structure_ideas.csv`; `src/eda/predictability_diagnostic/stage2_iid.py` (the iid point model: `game`, `tiebreak`, `set_win`, `match_win_by`, `deciding_set_rule`, `tiebreak_target`); `data/studies/predictability_diagnostic/stage2_matches.parquet` (it already holds `tb_exp_a`, `tb_over_a`, naive `bp_save_over_a/_b`; check its coverage and conventions before reusing anything); the pool's conversion luck I-025 (`src/eda/feature_interactions/` builder `f18_overreact.py`; store column via `data/studies/feature_universe/store_registry.csv`) and `src/eda/market_anchoring/luck.py`, so you can say how yours differ.

**The hypothesis (registered direction):** results carry scoring luck; rankings, results-based ratings and the crowd read it as skill; so a player whose recent results ran ahead of his points is over-rated by the close (negative coefficient for the lucky player). Persistence near zero is the premise, not a flaw.

**Build, per match and player, from the current Stage 0 box scores** (`H.long_table(player_cols=[...])` with `spw_n/_d`, `rpw_n/_d`, `tpw_n/_d`, `hold_n/_d`, `brk_n/_d`, `bp_saved_n/_d`, `bp_conv_n/_d`, `tb_won_n/_d`, `sets_won_n/_d`, `games_won_n/_d`; completed matches with a box score; non-standard formats out). Expectation curves are fitted **once on completed box-score matches of 2010–2012 at every level, by tour** (and best-of where needed), frozen, and applied unchanged to every later match. Each per-match residual e is then aggregated over the player's STRICTLY EARLIER box-score matches at every level as a decayed sum S = Σ 2^(−Δdays/h)·e with h = 91 days (secondaries: h = 365; a flat 52-week sum), with the decayed count as a companion and 0 (plus a flag) when there is no history. Screen A − B.

1. **PS01 tiebreak luck:** tiebreaks won minus Σ over tiebreaks played of π_TB(p_i, p_j, target), with p the match's serve-point rates and the target from the deciding-set rule (10 for Slam deciding tiebreaks where the rule says so, else 7). Check the bias the analyst flags (the match rates include the tiebreak points) by p-bins on 2010–12.
2. **PS06 close-set and deciding-set luck:** sets won from 5–5 (or tiebreak sets plus 7–5 sets, if 5–5 is not identifiable from the score: say which) minus their iid expectation; deciding sets won minus π_set at the match's rates. Two separate statistics.
3. **PS03 break-point luck, four pieces:** save luck S − F·s̄(p_i) (registered sign −); faced luck F − G·φ̄(p_i) (registered sign +: a player who faced more break points than his serve rate implies had bad luck, so he should beat the close); conversion luck C − Ch·(1 − s̄(p_j)) (sign −); chance luck Ch − G_opp·φ̄(p_j) (sign −). s̄ and φ̄ frozen on 2010–12 as the analyst defines (§ 3.3 of the memo). Also report the pieces combined in the hold-luck direction.
4. **PS04 event-run luck and flattery:** run luck = Σ (y_k − Λ_P,k) over the player's earlier matches at this event (qualifying included), with Λ_P the points-implied win probability (logit Λ_P = β(T_i − T_j)/√(T_i + T_j), β fitted on 2010–12 by tour × best-of); flattery = the previous match's logit(games share) − κ·logit(points share), κ the 2010–12 slope. Missing → 0 with a flag. Note: run luck uses the earlier rounds' results at this event, which are known before this match.
5. **PS02 results-rating luck gap** (build only if time allows after 1–4): an Elo run on results minus the same Elo run with Λ_P in place of the result wherever a box score exists (`src/eda/predictability_diagnostic/stage1_baselines.py`'s Elo), pre-match, in log-odds; the split into set and game luck is optional.
6. **PS11 visible luck count:** over the last 10 matches, points-dominant losses minus fewer-points wins.
7. **The pool's I-025** (store column) screened beside yours with the same harness, for comparison.

**Also report, for each statistic (outcome-free or ≤ 2024 only):**
* split-half persistence (odd vs even matches of a player-season) or the season-to-season correlation: luck should be near 0;
* **the close's loading c** (the analyst's § 4 gate), seasons ≤ 2024 only: per tour and era, least squares of the close's log-odds L on point-based skill Z (the IOS inputs, `form_*`, `formdef_*`, `adjperf_tpw_2w`, `ratings_iid`, `sets_14d`, `age`, the surface pairs; not `elo_*` or `points_52w`) plus x, clustered by four-week block; report c, its z, and the outcome coefficient β from the harness side by side (the analyst predicts β ≈ −c);
* the correlations among your statistics and with `sets_14d` and U-138 (matches here; store column `fp__...on_n` or the B11 member: find it in the registry).

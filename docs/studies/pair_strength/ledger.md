# Look ledger

Every run of this study that read match results (`a_won`), in time order (7 October 2026, local time). No row before the pre-registration's hash reads a 2025–2026 result.

| # | When | Script | Seasons read | What was related to results |
|---|---|---|---|---|
| 1 | about 12:50 | `reproduce.py` | 2014–2024 | The feature-interactions screen's I-084 row through its own machinery (`screen.run`): z₁ −2.6566, z₂ −2.0326, joint −2.9846 (model base), −3.1155 (price base). A machinery check; no new information |
| 2 | about 12:55, rerun 13:10 | `explore.py` | 2014–2024 | The pair-strength slope alone and in decompositions (favourite and underdog Elo, maximum and minimum, rank, TrueSkill Through Time, overround, mismatch, experience, age, level, round, best of five), quintile slopes, Pinnacle and power de-vig bases, the price-plus-adjustment split, by tour, level and season, a quadratic. The rerun changed only the favourite's tie-break at even prices |
| 3 | about 13:00 | `deploy.py` | 2014–2024 | Ten walk-forward calibration layers against a slope per tour (model and price bases), 2015–2024 |
| 4 | about 13:02 (scratchpad), 13:20 (`levels_check.py`) | `levels_check.py` | 2016–2024 | The feature-interactions levels arm (17 sums, seeds 0–5): its pair-strength slope and its calibrated gain over the model (2017–2024) |
| 5 | 13:03–13:25 | `local_fits.py` (GPU) | forecasts only | The arm `elosum` (58 inputs + R_A + R_B): 2014–2024 seeds 0–2, 2025–2026 seeds 0–7 (each season trained on earlier seasons' results only). No 2025–2026 forecast scored |
| 6 | about 13:13 | `score_arm.py` | 2014–2024 | The arm against the model: its pair-strength slope, calibrated gains (2020–2024 decided calibration; 2015–2024 from 2014), raw gain, the encompassing test with disjoint seeds (2016–2024) |
| 7 | about 13:17 | `where_gain.py` | 2015–2024 | The arm's gain by tour, level, pair-strength fifth, price band, format and surface; the seed check (model seeds 3–5) |
| 8 | 13:12 onward | tests, `final_test.py --check`, `--dry-run` | no 2025–2026 result | Tests: synthetic outcomes only. `--check`: counts, coverage, constants, hashes. `--dry-run`: every code path of the run with **synthetic** 2025–2026 outcomes (drawn from the model's own forecast) and real 2014–2024 results; the real 2025–2026 `a_won` is never loaded (`frame(..., with_results=False)` for test seasons) |
| 9 | 13:26–13:35 | `local_fits.py --arm elosum_perm` (GPU) | forecasts only | The placebo arm: the Elo-sum column permuted within tour × season, 2014–2024 seeds 0–2 |
| 10 | about 13:35 | `where_gain.py` | 2015–2024 | The placebo against the model and against the arm (calibrated from 2014; 2020–2024 with the decided calibration) and its pair-strength slope |
| 11 | 13:36 | none | none | **The pre-registration frozen**: `preregistration.md` SHA-256 b75ab3a87422b965a9683fc668f391d94463d869b5a5489e2bdcd1190dd55757 |
| 12 | 13:36 | `final_test.py --run` | **2025–2026, once** | The two pre-registered primaries (H1, H2 with Holm), the effect sizes and the secondaries. Every hash matched; the primaries were written before anything else (`final/final_primary.json`, `final/final_results.json`) |
| 13 | about 13:45 | `explore_test.py` | 2025–2026 (**exploratory**, after the run) | One process suspect for H2: the Elo sum's drift above the training range (result-free shares), and H2's gain by pair-strength fifth and above/below the training 95th percentile (`final/explore_test.json`). Cannot change any reading |

# Lock-in, addendum 1: three cleaner versions

**Frozen 16 Oct 2026, 15:15 PDT**, before any result from 29 Jul 2026 on was read for these statistics.
* It **adds** hypotheses. It changes nothing in the [lock-in](lock_in.md).
* This file's SHA-256 and those of its inputs are in the [process log](process_log.md).
* Changes before the first look follow the lock-in's § 8.

## 1. What was seen

**These versions are discovery, not confirmation.** They were built and read on seen matches only (2013 – 28 Jul 2026), and chosen with those readings in view (process log, 14:15–15:13). Only the unseen check can confirm them.

**Built and not registered** (readings in the [process log](process_log.md) and the helpers' [memos](team/)):
* **The returner's elasticity to the server's strength:** the close prices it.
* **The speed gap between first and second serve, the fade within a match, and fault speed:** unresolved, or too little data.

**C1's members** were built by the unpriced-leads study on 2013–24 and were first read on 2025+ today. Their net cousin (net break-point luck) was read once on 13 Oct, inside that study's luck group.

## 2. The cleaner versions

Men's main tour, A − B. "+" means the registered direction holds.

| | What | Built from | Direction | Seen: 2013–16 / 17–19 / 20–22 / 23–24; 2025–26 (z beyond the close) |
|---|---|---|---|---|
| **C1** | Luck in the big points | The mean of save luck and hold luck (break points saved, and service games held, beyond what the match's serve points imply; 91-day half-life): unpriced leads' `build_luck.py`, columns PS03_save and PS03_hold | The luckier man loses to the close | +1.95 / +1.01 / +3.05 / +1.05; +2.66 |
| **C2** | Serve over return, at equal overall strength | (O_spw − D_spw) of A minus that of B: the surface-effective IOS ratings on serve points won | The serve-heavy man loses to the close | −1.01 / +1.77 / +0.48 / +0.53; +3.44 |
| **C3** | Second-serve speed change | `spd2_L`: the serve-speed stage's 28-day builder run on second serves (`speed_ext.py`) | The man whose second serve sped up beats the close | +1.86 / +2.03 / +2.12 / +0.75; +1.90 |

**Scores** are frozen in `data/studies/serve_return_leads/addendum_scales.json`, computed outcome-free on the lock-in's window: the men's matches of 1 Jan 2025 – 28 Jul 2026.
* **C1:** save and hold luck, each over its RMS; their mean over its RMS.
* **C2:** over its RMS.
* **C3:** over the RMS of its non-zero values.
* A missing value counts 0.

## 3. Hypotheses and error

* **HC1–HC3: β > 0 beyond the close.**
* **One family.** Holm across the three at each look's level, on the lock-in's schedule (lock-in § 6), once you choose it.
* **If nothing is real,** the chance of at least one false "confirmed" across the lock-in's H0–H3 and HS and these three is about 0.14.

## 4. The matches and the test

The lock-in's § 5, unchanged:
* every men's main-tour match from 29 Jul 2026;
* the frame's odds input;
* unpriced leads' registered fit;
* four-week blocks, with t on G − 1.

## 5. The values at the look

**Each is rebuilt with the registered code on the instance current at the look.** Before any unseen result is read, the rebuild must reproduce this registration's values on seen matches, or its differences must be listed and explained by data repairs.
* **C1:** `build_luck.py`, unchanged (SHA-256 below), on that instance's tables.
* **C2:** that instance's own surface IOS features (`srf_O_eff_spw`, `srf_D_eff_spw`).
* **C3:** `speed_ext.py`, unchanged, on the speed panel current at the look. Use the weekly feed's release days for matches before 8 Oct 2026, and the daily collector's from 8 Oct, as the production rule does for the first serve. The live panel records second-serve speeds for the daily collector's rows (182 of 182 in October 2026).

## 6. Reported beside the verdicts, without verdict words

* each of C1's two members alone;
* beyond the model's forecast;
* the first and second serve together (T4 with C3);
* against Pinnacle's own close, where it exists (if those closes are bought);
* completed matches only;
* the Slams left out;
* the 416 matches already read by the five-pattern check, apart.

## 7. What the check can see

Power of one look at one-sided 0.05: `addendum_power.csv`.

| | If the 2025–26 strength is real | At the 2013–24 strength |
|---|---|---|
| C1, by 31 Aug 2027 | 0.66 | 0.25 |
| C2, by 31 Aug 2027 | 0.84 | 0.11 |
| C3, by 31 Aug 2027 | 0.43 | 0.15 |

**C1 and C3 are small and steady.** A check on unseen matches will most likely read "unresolved" through 2027. Their main evidence is their record since 2013, which a check this size cannot overturn or confirm. **C2 is new,** and the check is its only route.

## 8. Hashes of the inputs (SHA-256)

| File | SHA-256 |
|---|---|
| `data/studies/serve_return_leads/addendum_scales.json` | `b402e4e6e646a0c67bf1352fad57d5e830d41f3f4914d3da50a0d23c328f7b2d` |
| `src/eda/serve_return_leads/addendum_scales.py` | `201016c805029b9d07f8933b8c4761cd818b44f8fe91e37dde320c10aa2673ce` |
| `src/eda/serve_return_leads/speed_ext.py` | `285507302b5d80b6bf94bb3b18291272e09a48f0c3a1e885569b508fa81974c2` |
| `src/eda/serve_return_leads/decompose.py` | `fb89b427824bd00285eae6d20a4d93b63986d717b28d3fb4d28538adcbc4c60c` |
| `src/eda/unpriced_leads/build_luck.py` (equal to unpriced leads' registered hash) | `1286a62e25ca5db0ca51be92ddbb4c80a2e751c42b63a6c9fc6b609da4e74fd7` |
| `data/studies/unpriced_leads/candidates/luck/values.parquet` (equal to its registry's) | `092d423ccca35474252bd749c5ef27c16b78d250c7566533cb5ca9f2b2b04466` |
| `data/studies/serve_return_leads/speed/builder_columns.parquet` | `5bafccfb1bcea70cfe59ab470e0c6cca4e2c51e8e57f09b6825396a8f12e2f75` |
| `data/studies/surface_ios/surface_features.parquet` | `ba8514e8e514f95881275f192a340f0a3ee5954d61b24b6976e63e1c10f66365` |

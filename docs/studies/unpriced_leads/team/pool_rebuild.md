# Pool rebuild (S3): the pool's lead columns on the current tables

13 Oct 2026 · S3, the pool rebuilder (Claude Opus 5.5, session `e1ffc84e-fa2d-42f9-9d17-7c936a046c45`) · Registration values, not a decision · Code: [`src/eda/unpriced_leads/rebuild_pool.py`](../../../../src/eda/unpriced_leads/rebuild_pool.py) (one command, deterministic) · Data: `data/studies/unpriced_leads/candidates/pool_rebuilt/`

No outcome from 1 Jan 2025 on was read; outcomes only through the harness (seasons ≤ 2024). Labels: *observed*, *inference*, *suggestion*. Signs: + = the player higher on the statistic beats the close; for the venue pace (a context), + = a steeper price where the pace is high.

## Summary

* **Values for every current-frame match** (67,226; 2013–2026) of the 30 store columns behind U-284/U-162, U-283, U-254, U-330, U-261, U-175, U-177, U-138/U-307, U-143/U-322, U-153 and U-148: `values.parquet`, `rb__` + the store's name, pairs as `_a`, `_b`, `_a-b`; no result column. Men's 2018 and all of 2026 are now covered.
* **Code fidelity** (observed): fed the store's own inputs, the same code reproduces the store exactly: 30 of 30 columns, all 55,144 store rows ≤ 2024, to 1e-9.
* **On the current tables** (observed, the same 55,144 rows): 6 of the 15 screened candidates are identical to the store and 6 correlate ≥ 0.9995 with it; the venue pace and B-VENUE r 0.994–0.996; **salience (I-082) r 0.88, men 0.77**, moved by the level layer inside the instance's Stage B and by nothing else.
* **Timing** (observed): no future row moves under the harness's probe, for any own-sequence builder at any cut; own rows move only by rounding (≤ 4e-14) or by leaving the population; f01's probe-equivalent leaves the venue pace of every earlier frame match unchanged; every leaky control is caught.
* **Readings** (observed, both tours, ≤ 2024): where values did not change, the pool's numbers come back exactly on the store's rows. Men's 2018 weakens the post-Slam letdown (raw −4.71 → −4.04, orthogonal −4.23 → −3.53; men only) and strengthens the status axis (U-330 +5.72, has-low-visibility-form +5.53, seeded −4.96). Salience reads +2.60 raw, +1.38 orthogonal (+3.99 and +2.48 without the layer).
* **Two table facts** for the registration: the clock on disk was rewritten on 12 Oct, after the instance's 10 Oct build, and the repository's Stage 0 lacks the accepted men's 2026 Challenger package. Building on the instance's own tables changes little (r ≥ 0.999 on 2013–24, ≥ 0.996 on 2026's rows).

## 1. What was rebuilt, and how (observed)

* **Builders, unchanged.** Every value comes from the original module functions, imported, never edited: `f19_motiv.prepare_motiv` / `combine_bmotiv`, `f09_venue.prepare_venue` / `x_i072` with `f01_structure_lib.signed_block`, `event_levels.blend.history` (as `universe_columns.py` calls it), `f12_salience.prepare_i082`, `f14_anchor.prepare_fame`, `f24_onsite.prepare_b11` / `b11_members`, `f28_state.past_fat` on `f20_fatigue.history` with `f20_fatigue.block`, `f23_arrival.prepare_b10`, and `build_store`'s seeded rule.
* **Their hard-wired sources point at the current tables** for the duration of a build (`Patched`, restored after): the harness's `long_table()` on the 8 Oct Stage 0 and the clock on disk; Stage 1's odds for tennis-data's Court; `blend.load`'s Stage 0; f01's surface-IOS path; f12's Stage B z, merged into the long table so the probes can scramble it.
* **Two tables exist only in the instance's build sandbox** (`C:/Users/zerom/tnr_lyr_new`): its surface IOS (the venue pace's expected ace rate, the target's ace offence) and its Stage B (salience's per-match z). The sandbox's IOS reproduces the frame's `iosO_ace` exactly on every match; its Stage 0 hashes as the instance's `chain_layer.json` records. Both are pinned by SHA-256 and frozen as extracts in `inputs/`.
* **The panel** is `feature_interactions.panel`'s join for the columns these builders read (the frame's keys, Stage 0's pre-match fields and sides, the clock's es/lf), never a result.
* **Variants** (outcome-free, never registered): V0 the store's inputs; Vk V0 with today's clock; Vs V1 with the repository's 30-Sep surface IOS and Stage B; Vz V1 with Stage B rebuilt on the same 8 Oct Stage 0 without the layer (the level-layer adoption study's layer-off build); V2 the instance's own Stage 0 and clock.

## 2. Verification against the store (observed; `verify.csv`, `verify_by_season.csv`)

Rows both hold, seasons ≤ 2024: 55,144 (the store has no men's 2018). Each difference is attributed along store → V0 → Vk → Vs → Vz → V1.

| Column (store name) | Share equal (1e-9) | r | What moves the differing rows |
|---|---:|---:|---|
| `post_a/_b`, `post_slam`; elite pre-Slam; seeded; fame; `bd11_on_n`, `bd11_on` | 1.000 | 1.000 | nothing |
| `nslam_days` (inside elite pre-Slam) | 0.994 | 0.9996 | the clock: 310 rows, women 2018–20 (the elite flag itself is unchanged) |
| `el__low_share_*` | 0.999 | 1.0000 | Stage 0's id fixes: 58 men's rows of 2015–16 (a 2015 Winston-Salem qualifying match moved from atp:106329 to atp:106298) |
| `hasL_a/_b` | 0.9999 | 0.9998 | 10 rows: the clock 6, Stage B's rebuild 4 |
| `bd11_nov`, `bd10_trav` | 1.000 | 1.000 | one men's row of 2021 (an id fix) |
| `bdst_pastfat_a/_b` | 0.68 | 0.9996 | Stage 0 15k rows (women 2013–15: missing minutes are imputed from points played, which the 8 Oct box-score fixes change), the clock 3.3k |
| `fi__B-STATE__x` | 0.20 | 0.9995 | the same, plus its scale: 2014–21 now includes men's 2018 |
| `f09_ve`, `f09_venue_pace_x_ace`, `fi__B-VENUE__x` | 0.009 | 0.994–0.996 | every row: the instance's surface IOS; the clock and the box-score fixes 14k rows each |
| `salL_a/_b`, `fi__I-082__x` | 0.16–0.36 | 0.84–0.88 | the level layer in Stage B (men r 0.74–0.77; women 0.996–0.998, from Stage B's rebuild alone); with the layer off (Vz) r 0.998–0.999, men 0.9999 |

* **The clock** (`match_timing/timing.parquet`, rewritten 12 Oct 07:24, about 9,200 more exact days): against the store's 30 Sep clock, 8,043 earliest starts, 11,200 latest finishes and 13,067 best-estimate days differ before 29 Jul 2026, almost all in 2016–21, 550–840 of them main-tour. The instance's 10 Oct clock differs from today's by about as much.
* **Stage 0, 8 Oct against 30 Sep:** no level, round, status or date changed before 2026; 76 player ids were fixed before 2025 (56 unresolved `atpcode:` ids, mostly 2011 qualifying); minutes changed on 138 matches; box scores carry the 8 Oct corrections.
* **Sides:** none changed on the common rows. 71 women's matches of 2026 have remapped player ids and 40 store rows of 2026 are not in the frame, outside the ≤ 2024 check.

## 3. Timing (observed; `probes.json`)

* **Own-sequence builders** (`screen.timing_probe` at 1 Jun 2016, 1 Mar 2019 and 1 Sep 2022, on a panel of every match of the history before 29 Jul 2026, so every history row carries a value; Stage B's z is scrambled with the results): **no future row moved** at any cut, of 626k, 916k and 1.25M (post-Slam, elite pre-Slam, fame, salience, has-low-visibility-form, matches here, novelty; travel, past fatigue and the lower-level share where they exist).
* **Own rows** (each player's first scrambled match; 21,691 / 17,660 / 12,778): none moved for seven builders. Salience moved on 367–477 and past fatigue on one, by at most 3.3e-16 and 3.8e-14, none beyond 1e-9: rounding, because both exclude the current match as a cumulative sum minus its own term. The lower-level share lost or gained its value on 3–5 rows the scramble turned into walkovers or back (they leave or enter the query population); no value changed.
* **Leaky controls move** (the harness's counts): the current match's points or load on 9,999–21,678 own rows, the next match's on 2,577–6,028 future rows.
* **Venue pace** (cross-player, the module's own clock): f01's probe-equivalent (results after each of five cuts, 2016–24, reversed between the players) leaves every frame match starting by the cut exactly unchanged, while a control counting results nine days early moves at four cuts. The scramble probe moves no future row; its own rows move legitimately (a match that finished before the target started belongs to the pace even if it started after the cut).
* Seeded reads Stage 0's seed of the match itself, a pre-match field the probe cannot perturb.

## 4. Coverage (observed; `coverage.json`)

Debut seasons out, by tour and season, 2026 only before 29 Jul. Every match carries post-Slam, elite pre-Slam, B-VENUE and its pace, salience, has-low-visibility-form, seeded, fame, matches here and novelty; the lower-level share 99.9% (missing without a played match in the year), travel 96–98% (a region unknown), past fatigue 75–83% (missing without a match in the previous 14 days). Men's 2018 (2,620 matches) is complete, and 2025 and 2026 run at 2013–24's rates.

## 5. Readings beside the store's (observed; `summary.csv`, `long.csv`)

Both tours, 2013–24 pooled z (eras of the pool's sign). *Store rows*: the rebuilt values on the matches the store holds. Model: beyond the instance's forecast, 2020–24; move: BetOnline's open-to-close, 2018–24 (a direction, not a null test).

| Candidate | Pool: raw / orth | Store rows | Raw (eras) | Raw + curv | Orth (eras) | Orth + curv | Model | Move |
|---|---|---:|---|---:|---|---:|---:|---:|
| Post-Slam letdown (U-284/U-162) | −4.71 / −4.23 | −4.71 | −4.04 (4/4) | −4.01 | −3.53 (4/4) | −3.51 | −2.38 | −0.59 |
| Elite pre-Slam (U-283) | −2.06 / −1.51 | −2.06 | −2.29 (2/4) | −1.99 | −1.77 (2/4) | −1.50 | +1.15 | −1.35 |
| B-VENUE (U-254) | +3.69 / +3.87 | +3.84 | +3.61 (4/4) | +3.61 | +3.74 (4/4) | +3.76 | +2.75 | +2.41 |
| Venue pace, context | +0.72 / — | +0.63 | +0.39 (3/4) | +0.49 | — | — | +0.29 | +0.07 |
| Lower-level share (U-330) | +5.30 / +2.88 | +5.30 | +5.72 (4/4) | +5.35 | +3.15 (4/4) | +2.71 | +2.43 | −2.26 |
| Salience x (U-261) | +3.62 / +2.10 | +2.35 | +2.60 (4/4) | +2.63 | +1.38 (3/4) | +1.52 | +0.87 | +8.91 |
| … Stage B without the layer (Vz; not registered) | | +3.56 | +3.99 (4/4) | +3.93 | +2.48 (4/4) | +2.52 | +1.90 | +7.40 |
| Has low-visibility form (U-261) | +5.08 / +3.29 | +5.10 | +5.53 (4/4) | +5.15 | +3.67 (4/4) | +3.22 | +3.23 | −1.06 |
| Seeded (U-175) | −4.32 / −3.61 | −4.32 | −4.96 (4/4) | −4.56 | −3.95 (4/4) | −3.46 | −2.47 | +3.68 |
| Fame (U-177) | −3.90 / −2.73 | −3.90 | −4.20 (4/4) | −4.19 | −2.82 (4/4) | −2.76 | −1.30 | −2.25 |
| Matches here (U-138) | +4.18 / +2.18 | +4.18 | +4.34 (4/4) | +3.94 | +2.40 (4/4) | +2.07 | +2.05 | +5.82 |
| On, log (U-307) | +4.28 / +2.27 | +4.28 | +4.41 (4/4) | +4.00 | +2.45 (4/4) | +2.13 | +2.03 | +6.98 |
| Past fatigue (U-143) | +5.19 / +2.11 | +5.21 | +5.31 (4/4) | +5.25 | +1.99 (3/4) | +1.97 | +1.89 | +5.60 |
| B-STATE (U-322) | +5.20 / +2.11 | +5.22 | +5.33 (4/4) | +5.27 | +1.98 (3/4) | +1.97 | +1.92 | +5.65 |
| Novelty (U-153) | −4.01 / −1.88 | −4.00 | −3.86 (4/4) | −3.78 | −1.73 (4/4) | −1.72 | −1.19 | −2.88 |
| Travel (U-148) | −3.52 / −1.68 | −3.52 | −3.39 (4/4) | −3.32 | −1.54 (4/4) | −1.51 | −0.85 | −2.76 |

## 6. By tour (observed), and what the changes do (inference)

* **Letdown:** women −3.60 raw, −3.29 orthogonal, as in the store; men −1.56 and −1.28 (store −2.16 and −1.83). Men's 2018 reads against it: the men's 2017–19 era goes from −1.52 to −0.39.
* **B-VENUE:** women +4.47 / +4.51, men +1.47 / +1.24 (store +1.61 / +1.41).
* **Status axis:** lower-level share men +3.45 / +2.12 (store +2.97 / +1.75), women +3.02 / +2.46; seeded men −3.75 / −3.39 (store −3.24 / −3.03), women −2.70 / −2.07. Men's 2018 strengthens it (2017–19 era: lower-level share +1.08 → +1.99, has-low-visibility-form +1.86 → +3.48, seeded −2.38 → −3.43).
* **Salience:** men +1.87 / +0.98 with the layer, +3.57 / +2.43 without (store +2.92 / +1.36 on its rows); women +1.34 / +0.48 either way. *Inference:* the layer's translation of lower-level performance removes most of the men's signal, so what the unlayered version carried for men was largely the level of the evidence, the status axis again.
* *Inference:* the curvature terms take 0.3–0.4 z from the members that grow with the price's lopsidedness (seeded, the lower-level share, has-low-visibility-form, matches here) and leave the letdown, B-VENUE, salience and fatigue as they were.

## 7. Caveats

1. **The clock.** The registration reads the clock on disk, as the brief, the harness and the other builders do; it is not the clock the instance was built on (rewritten 12 Oct). V2 moves values little (`sensitivity.csv`), but a registry should name the clock it froze: `build.json` keeps every input's SHA-256.
2. **The accepted men's 2026 Challenger package** is merged into the instance's tables, never the repository's. Without it, men's 2026 rows before 29 Jul differ in four columns: lower-level share 21 rows, past fatigue 24, novelty 3, travel 2.
3. **Salience is not the statistic the pool scan read.** Its discovery reading (+3.62) used Stage B without the layer; the registered value uses the instance's Stage B, with it. *Suggestion:* if a group takes U-261, take its has-low-visibility-form indicator (the layer does not move it: r 0.9998 with the store; +5.53 / +3.67), or register the layered salience with its own, weaker, evidence; do not register the unlayered version, which the live template does not build.
4. **Scaled block columns.** `fi__B-VENUE__x` and `fi__B-STATE__x` take their scale (B-STATE also its 99th-percentile clip) from the current frame's 2014–21 rows, now with men's 2018. The harness rescales anyway; the unscaled members are in the values.
5. **The instance's tables live in a sandbox** the owner may delete; the extracts in `inputs/` hold exactly the columns read, and the code checks both hashes.
6. **The store's data caveats remain:** women's minutes before 2016 are imputed (past fatigue, B-STATE); past fatigue is missing without a match in the previous 14 days; travel is missing where a region is unknown.
7. **Multiplicity.** These re-measure the pool's best-of-many candidates on the same seasons: not new evidence; shrink them as the pool memo says.
8. **For the registration** (*suggestion*): freeze `values.parquet` with `build.json`'s hashes; `orth_coef.json` holds each candidate's orthogonal-part coefficients, fitted by tour on the screened frame (≤ 2024), ready to apply to 2025–26 rows.

## 8. Process notes (for the lead's log)

* **Brief** (`briefs/09_pool_rebuild.md`, verbatim) received 10:03; read CLAUDE.md, the process log §§ 1–4, the pool memo, the harness, the builders, `build_store.py`; 10:05–10:35 outcome-free source checks (above).
* **Fixed before any result:** the V1 tables (the brief's Stage 0 and clock for the long table; the instance's surface IOS and Stage B, the only versions built on the 8 Oct tables), the variant chain V0, Vk, Vs, V2, the extracts, the 15 screened candidates (the pool scan's names) and the screens.
* **Deviation, disclosed:** the first V1 build (10:36) printed summary statistics of every values column over all 67,226 matches, the 866 from 29 Jul 2026 included: feature values, no result, nothing decided from them.
* **10:39:** V0 reproduced the store exactly. **About 10:55–11:00:** first look at screen readings (a full run without probes, after the outcome-free checks).
* **After that look:** added Vz and the layer-off salience screen, to explain salience's move (descriptive; the registered values did not change); added the probe breakdown's tolerance and largest change, after the hist group's exact own-row count. No statistic definition changed after a screen.
* **Blinding tightened (11:10):** the development probe run used the whole history, so the harness's own-row set could include a new player's first match from 29 Jul 2026 on (aggregate counts of changed feature values; no result), and the venue check counted later frame matches that moved. The official probes run on the history before 29 Jul 2026, and every count in the build records stops there. The first official launch (11:07) was stopped for this and relaunched (11:12).
* **Official run:** 11:12–11:44 (1,931 s), from scratch; its files are the ones here. Determinism: three independent builds of V1 (10:36, 11:08 in the stopped launch, and the official run) are bit-identical.

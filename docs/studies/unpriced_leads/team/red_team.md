# Red team (R2): the draft registration, attacked before the freeze

13 Oct 2026 · Role R2 ([brief](../briefs/10_red_team.md), binding) · Claude Opus 5.5 (`claude-opus-5-5`), a subagent of session `e1ffc84e-fa2d-42f9-9d17-7c936a046c45` · Attacked: the draft [preregistration.md](../preregistration.md) and `registry.json` (SHA-256 `7177d60d…`, the run of 11:52) · Scratch code and outputs: `data/studies/unpriced_leads/team/red_team/` (one script per check, § 6)

* **Outcomes read: seasons ≤ 2024 only.** They came through my own loader (`rt_common.disc_frame`: filter inside the parquet read, then asserted) and the registered dry run (seasons 2023–24), which I ran through `look.run()` with its output written to my folder.
* **Outcome-free reads of 2025–26:** member values, coverage, block counts, correlations, Stage 0 match counts by month, feed end dates. One disclosure is in § 7, item 6.
* **Labels:** *observed* = computed here, or read from a named file; *inference* = my reading; *suggestion* = a fix for the lead. Discovery z's are the registered fit unless stated: per-tour slope and curvature on the close, the score at unit RMS, cluster-robust over four-week blocks, both tours, 2013–24.

## Summary, ranked

| # | Rank | Finding | Fix |
|---|---|---|---|
| B1 | **Blocker** | Looks A and B and their combination can each "confirm" at one-sided 0.05. Under the null, that is a 9.8–11.0% false-confirmation rate for H0. The verdict rule for Look B and for A + B is not written down. | Register a two-look boundary: A at z ≥ 2.50, final A + B at z ≥ 1.66 (overall 0.05). Gatekeep H1–H5 behind H0 |
| B2 | **Blocker** | § 9: a confirmed omnibus (or Holm group) admits *every* member "as a lead confirmed on 2025–26", even one whose group reads contrary | "Confirmed" belongs to the score tested. Members enter as leads carrying their own and their group's reading |
| B3 | **Blocker** (Look B) | Look B's inputs are not on disk, and the registration has no completeness rule. After May/June 2026, Stage 0 has no ITF, no women's WTA 125 and no women's qualifying, and 8% of men's Challenger qualifying. Flashscore times end 17 Apr 2026. G4's women's members would collapse toward 0, and their orthogonal score would then become a combination of in-model inputs | An outcome-free completeness gate per member and tour, with a fixed fallback. Tell the owner that restoring the 2026 lower-level data needs his acceptance under the freeze rules |
| M1 | Major | `look.py` never checks the registry's frame or values hashes. Its frame, book prices and input list are wired to the 10 Oct instance, so Look B as coded reads 866 matches. `rebuild_pool.py` is pinned to the 10 Oct sandbox | Parameterise the instance, verify every hash, assert the projection's input order. A dry run must reproduce today's numbers |
| M2 | Major | The frozen projections drift on Look A's rows: fame ~ age −0.21, past fatigue ~ `sets_14d` −0.14, bye seed ~ `surf_layoff` −0.16 (all 0 in discovery). These inputs' 2025–26 mispricing is published. G4's correlation with the model's own adjustment more than doubles in 2025 (0.105, against 0.045 in 2020–24) | Register "beyond the close and the 48 inputs, fitted in the window" (or an in-window re-projection, which reads no outcome) as primary or as a decisive secondary |
| M3 | Major | Unstated exposure. market_anchoring scored a G1 relative (men's 365-day hold and break luck; r 0.39 with G1 on Look A) on 2019–2025 and on 2026 outcomes, including 36 matches dated 29 Jul–2 Aug 2026. S2c's MP-10 read the results of the 136 season-2025 Look A matches dated Dec 2024 | Add both to § 2 and to G1's exposure line. State whether those 136 matches stay in Look A |
| M4 | Major | The bye-seed member (`rb14_cold28`) reads z 0.12 on 2020–24 (−0.64 in 2023–24; women −1.64). The line moves toward it (+6.8). It is 54% predictable from inputs, context and price. A third of its z is G4's `seeded` (r 0.29–0.34), and its women's population doubles in Look A | Drop it from G5 (G5 without it: z 3.99) or demote it to a member-level secondary. Log this as a post-result change prompted here |
| M5 | Major | Retirements (2.9% of matches) carry part of the signal: omnibus 8.52 → 8.08 without them, G1 3.85 → 3.34, net break-point luck 1.93 → 1.33. Books settle retirements differently, and 2025's rate was reported as a record | Register a completed-matches secondary (the settlement reading) |
| m1–m8 | Minor | Power stated with z rather than t(20), at optimistic realisations. Realisation ratio per window RMS. H7 not in the registry. Small code bugs. Uneven inputs. Text inconsistencies. Look B secondaries not deliverable. No registration-wide error rate | § 3 |

**Sound** (§ 4): the blinding of every code path and values file; register.py's numbers (re-derived exactly); the dry run (reproduced exactly); the base (no price-shape or context artefact, no source-switch bias); timing of the venue pace and the own-sequence members; group distinctness; the honest statement of shrinkage.

## 1. Blockers

### B1. Three chances to "confirm" one hypothesis, and no rule for two of them

* **Evidence** (observed, `preregistration.md`):
  * § 5 gives the verdict words with no window qualifier (lines 132–136).
  * § 8 (line 168): Look B runs "the same tests; plus the combination of Looks A and B by a weighted z".
  * § 9 (line 176): "Look B reads them again".
* **The cost** (observed, `power_check.json`; simulation under the null, independent looks, weights ∝ 1/SE):

  | Looks that can confirm H0 at one-sided 0.05 | False-confirmation rate |
  |---|---:|
  | A only | 0.050 |
  | A or B | 0.098 |
  | A, B or A + B | 0.110 |

  H1–H5 inherit the same inflation, on top of Holm.
  * Nothing gates H1–H5 behind H0.
  * H6–H8 carry their own 0.05.
  * The chance of at least one false "confirmed" in the registration, if nothing is real, is about 0.2. That is never stated.
* **Why it matters:** the owner will read "confirmed" as a 5% risk. The README's own advice ("Look B and the combination of A and B then decide") is exactly where the uncontrolled looks happen.
* **Fix** (suggestion). A two-look group-sequential boundary for H0 (`sequential_power.json`):
  * **Look A** confirms if z ≥ 2.50 (one-sided p ≤ 0.0062).
  * **Otherwise the final test is A + B**, the weighted z, confirmed if z ≥ 1.66 (p ≤ 0.049). Overall α is 0.05.
  * **Look B alone** is reported without verdict words.
  * **H1–H5** are tested only after H0 is confirmed at the same look (serial gatekeeping), with Holm at the same boundaries.

  At the realisation the screened universe predicts (k = 0.45, § 3 m1), this design confirms H0 with probability 0.61 by August 2027 (0.17 already at Look A). Look A alone at 0.05 gives 0.46. The current text's 0.66 exceeds this design's 0.61 only through its inflated α.
  * **Simpler alternative:** Look A is the only confirmatory look, and Look B and A + B are replication readings without verdict words.

### B2. A confirmed score "confirms" members it never tested

* **Evidence** (observed, § 9, lines 174–175):
  * "H0 confirmed: … Every member enters the feature pool as a lead confirmed on 2025–26."
  * "A group confirmed (Holm): the same for that group's members."
* **Why it matters:**
  * The omnibus averages five nearly uncorrelated groups. It can clear 0.05 while one group reads contrary. On the dry run (2023–24, in-sample), the omnibus read z +2.44 while G1 read +0.52.
  * Under these rules, a contrary group's members would enter the pool labelled "confirmed on 2025–26". Future selection rounds would then weigh a label the data never gave.
* **Fix** (suggestion):
  * "Confirmed" applies only to the score tested (H0: the five areas together; Hg: group g).
  * Every member enters the pool as a lead, with its own member reading and its group's verdict attached.
  * A group reading contrary is not admitted on the strength of the omnibus.

### B3. Look B depends on data the repository stopped holding, and nothing says what happens then

* **Evidence** (observed):
  * **Stage 0 match counts by month** (`stage0_matches.parquet`, tournament date):
    * ITF: zero for both tours from July 2026 (June 2026: 393 men's, 427 women's; June 2025: 2,362 and 2,281).
    * Women's WTA 125: zero from July 2026.
    * Women's qualifying at every level: zero from Roland Garros 2026. Its qualifying, in May, has 0 women's matches, against 112 in May 2025.
    * Men's Challenger qualifying: 102 in June 2026 (345 in June 2025), then zero.
    * The data_continuity study's splice table agrees: 0–13% of these draws kept after 1 June 2026.
  * **Feeds** (`match_timing/links/`):
    * Flashscore's starts and ends stop on 17 Apr 2026. Flashscore is the only source of actual end times and the first-choice start source.
    * Live Tennis API, its copy, stops on 13 Aug 2026.
    * After that, starts are SofaScore's schedules, about 10 minutes before the first point (the rhythm builder's measurement).
  * **TennisLive doubles do continue** (to 8 Oct 2026).
* **What it does to the members** (observed in Look A, inference for Look B):
  * **In Look A** the gap touches 634 of 4,197 women's matches (from 18 May 2026) and 319 of 4,394 men's (from 29 Jun 2026).
    * Women's past fatigue is present in 66% of July 2026 player-rows, against 82–88% in July 2024 and 2025.
    * Qualifiers' short rest is undercounted when their last qualifying match is missing.
  * **In Look B**, a woman's 52-week window loses its lower-level matches month by month. `low_share` and `hasL` then tend to 0, and the orthogonal part of a near-constant member is just −Xb: **a linear combination of the model's own inputs**. G4's women's half would then re-read in-model inputs whose 2025–26 behaviour is known.
  * The rest member silently switches from actual starts to schedules within Look B.
* **Why it is a blocker:**
  * § 8 freezes "every member's values recomputed by the registered code on that instance's tables" and § 10 forbids changing a member later.
  * The handling must therefore be registered now.
  * Restoring the data is not automatic. Under CLAUDE.md's freeze rules, lower-level history enters only as a candidate the owner accepts.
* **Fix** (suggestion):
  * **A completeness gate.** Before each look, for each member, tour and month, compare the outcome-free input counts with the same months a year earlier: lower-level and qualifying matches, start-time coverage, doubles rows, box scores. Fix a threshold now (for example 80%). A member that fails for a tour is set to missing (0) for that tour in that window, and its group's score is the mean of the others. This is fixed now and reported.
  * **A Look A secondary** before the gap: women before 18 May 2026, men before 29 Jun 2026.
  * **In README § 8, "What we need from you":** accept a lower-level 2026 package (the held WTA API, Slam feeds and TDI; no ITF source is held), and keep the start-time and doubles feeds running through July 2027.

## 2. Majors

### M1. The frozen analysis code does not check what it reads, and cannot run Look B

* **No hash check** (observed):
  * `look.py` reads each values file (`member_values`, line 109) and the frame (`load_window`, line 77, `H.FRAME`) without comparing them with `values_sha256` / `frame_sha256`, which the registry carries.
  * A rebuilt values file would be read silently. The result records only the registry's own hash.
* **Look B as coded** (observed):
  * `run()` (line 251) reads `H.FRAME`, which `screen.py` lines 49–50 fix to `template_2026-10-10`. That frame ends on 23 Sep 2026 (866 sealed matches), not at the August 2027 end Look B needs.
  * `add_book_bases` (`BOOKS`, line 55) and the input list (`model_inputs.json`) are wired to the same instance.
  * § 12's Look B procedure changes only the values paths, their hashes and `look_b_end`, so it would run on the wrong frame.
* **Projection order** (observed): with frozen coefficients, `screen.orthogonal_part` (lines 527, 541) takes the input list from today's `model_inputs.json`. It never compares it with `coef[tour]["inputs"]`. A template change would misalign the coefficients silently.
* **Values for Look B** (observed): `rebuild_pool.py` hard-codes the 10 Oct sandbox (`C:/Users/zerom/tnr_lyr_new`, line 117) and pins its IOS and Stage B by SHA-256 (lines 134, 138). It cannot rebuild Look B's values "on that instance's tables" without edits that § 10 does not clearly allow.
* **Fix** (suggestion):
  * Take the instance folder, frame, book prices, inputs and sandbox tables from the registry or the command line.
  * Assert every hash, and assert `coef[tour]["inputs"] == names`.
  * Let the registry name the frame used per look.
  * Show by a dry run on 2023–24 that today's parameters reproduce today's numbers bit for bit (they do today: § 4).

### M2. A channel from the published 2025–26 ledger into Look A's G4 and G5 readings

* **The design premise:** projecting out the 48 inputs keeps Look A from re-finding edge_anatomy's known 2025–26 results (process log, 08:35 row). With frozen coefficients, this holds only if the inputs relate to the members in 2025–26 as they did before.
* **Evidence** (observed, outcome-free, `exposure_checks.json` and the console checks of § 7):
  * **Group scores:** on Look A's rows the 48 inputs span 1–6% of each group score's variance (G4 5.7%, G1 4.9%, omnibus 3.1%; 0 in discovery by construction).
  * **Members drift more** (correlations of the oriented member score with an input on Look A):

    | Member | Input | r on Look A | The input's 2025–26 reading (edge_anatomy `ledger.csv`) | Direction of the leak (inference) |
    |---|---|---:|---|---|
    | fame | `age` | −0.21 | men β −0.074 (z −2.05) | toward the registered sign |
    | fame | `iosO_hold` | −0.17 | men −0.122 (z −4.44) | toward the registered sign |
    | fame | `elo_overall` | −0.12 | men −0.086, women −0.147 | toward the registered sign |
    | bye seed | `surf_layoff` | −0.16 | men −0.063, women −0.085 | toward the registered sign |
    | bye seed | `elo_overall` | −0.10 | as above | toward the registered sign |
    | bye seed | `sets_14d` | +0.10 | men +0.065, women +0.069 | toward the registered sign |
    | past fatigue | `sets_14d` | −0.14 | as above | against the registered sign |

  * **Alignment with the instance's own adjustment** (q_full minus the close, outcome-free; season 2025, where the model was trained on ≤ 2024):
    * G4's correlation is 0.105, against 0.059 in 2024 and 0.045 over 2020–24.
    * The omnibus: 0.068.
    * The adjustment's SD is 0.151 log-odds.
* **Why it matters** (inference):
  * Even if the instance's whole adjustment were true signal, the inflation would be at most about 0.105 × 0.151 ≈ 0.016 per unit of G4, or 0.6 of Look A's SE. Realistically it is a fraction of that, so it is not large.
  * But it points mostly in the registered direction for fame and the bye seed. A G4 or G5 "confirmed" could then be partly the published in-model result again, which the design meant to rule out.
* **Fix** (suggestion):
  * Add the 48 inputs, per tour, to the base, fitted in the window ("beyond the close and the model's inputs").
  * Or re-project each member on the window's own rows. The projection reads no outcome and is deterministic, so it adds no forking path.
  * Make it the primary, or a registered secondary with a stated role (a confirmation that vanishes under it is reported as "re-finding in-model information").
  * Before the look, publish each score's R² on the inputs and its correlation with the instance's adjustment.

### M3. Exposure that § 2 and G1's line leave out

* **market_anchoring** (5 Oct 2026, before the seal; observed, `src/eda/market_anchoring/luck.py`, `luck_results.csv`, `anchor_predictions.parquet` dates only):
  * It tested "each player's decayed holds and breaks above the iid expectation from their points won" (men, 365-day half-life). It read −0.01 [−0.10, +0.09] mLL on 2019–2025 and +0.28 [−0.07, +0.62] on 2026, plus coefficients on 2013–2025.
  * Its 2026 window holds 1,712 men's matches to tournament date 2 Aug 2026. **36 are dated 29 Jul–2 Aug 2026, inside Look B.**
  * On Look A's men's rows, the registered G1 score correlates 0.39 with the luck builder's 365-day net break-point luck, the nearest held version; the net member alone correlates 0.56.
  * The point-structure memo knew this reading (its § 3.2, line 153); the prereg does not mention it.
* **predictability_diagnostic's Stage 4** sentence on the tiebreak record given Elo pools 2013–2026 (point-structure memo, line 133). Close-set luck correlates 0.83 with tiebreak luck (luck builder § 7).
* **The 136 season-2025 matches dated late December 2024 belong to Look A** (§ 8). Their results were read in two places:
  * S2c's MP-10 pool used "frame matches before 2025" (it equals `load_frame`'s 57,867 pre-fix rows).
  * The harness, before its 09:42 fix, loaded them, unused.
  * No registered statistic was read against them (observed in the code).
* **Fix** (suggestion):
  * Add both studies to § 2 "Known before" and to G1's exposure line, with the 0.39 correlation.
  * Say that Look B's first 36 men's matches were scored by market_anchoring for in-model inputs and this relative.
  * Either drop the 136 matches from Look A or disclose them (1.6% of it).

### M4. The bye-seed member is the weak link of G5

* **Evidence** (observed):
  * **Eras** with the registered base: +1.15, +4.03, +0.60, −0.64.
  * **On 2020–24:** z 0.12 against the close and 0.11 beyond the instance's forecast (`robustness.csv`, part E).
  * **By tour:** men +3.22 and women +0.47 in discovery; women −1.64 in 2023–24 (`discovery_registered.csv`).
  * **The line learns it:** BetOnline moves toward it before the close, move z +6.8 (rhythm builder § 5).
  * **A context proxy:** a gradient-boosted model of its orthogonal score on the inputs, the six context inputs and the price reaches cross-validated R² 0.54 (by season; every other member ≤ 0.11; `proxies.json`). It is essentially "a seed's first match after a bye", a context the model sees through round, level and the odds.
  * **Shared with G4:** it correlates 0.29 (discovery) and 0.34 (Look A) with G4's `seeded`. Fitted jointly, `seeded` keeps z 2.86 and the bye seed falls to 1.73.
  * **Population shift:** its women's non-zero share doubles in Look A (7.0% in 2013–24 to 13.0% in 2025–26, rhythm builder § 4), where its discovery signal is null. Its orthogonal RMS on Look A is 1.17 times discovery's.
* **Why it matters** (inference): its expected contribution to G5 and the omnibus on Look A is about 0, while it carries an M2 leak toward the registered sign. It dilutes G5 (5.21 with it, 3.99 without) and double-counts G4's signal.
* **Fix** (suggestion): register G5 as doubles elsewhere, rest under 20 h and past fatigue. Keep the bye seed as a registered member-level secondary. Log the change as made after results, on this evidence.

### M5. Retirements

* **Evidence** (observed, `robustness.csv` part C; Stage 0 status, seasons ≤ 2024): 1,695 of 57,731 discovery matches (2.9%) ended in a retirement. Without them:

  | Score | All matches | Without retirements |
  |---|---:|---:|
  | Omnibus | 8.52 | 8.08 |
  | G1 | 3.85 | 3.34 |
  | Net break-point luck | 1.93 | 1.33 |
  | G2 | 3.61 | 3.33 |
  | Has low-visibility form | 3.08 | 2.56 |

  G3, G4 and G5 are unchanged.
* **Why it matters:**
  * Books settle retirements by their own rules (the market practitioner flagged this), so an edge carried by retirements may not be bettable.
  * The researcher cites a record ATP retirement and withdrawal rate in 2025 (4.8%; a news source), so Look A may lean on this channel more than discovery did.
* **Fix** (suggestion): register a "completed matches only" secondary (the settlement reading), and name the benchmark books' retirement rules in the README.

## 3. Minors

* **m1. Power is stated more favourably than the coded test and the evidence support** (observed, `power_check.json`, `shrinkage.json`, `se_windows.csv`):
  * **The coded test is t on G − 1 = 20 degrees of freedom.** Look A has 21 four-week blocks, so the one-sided critical value is 1.725, not 1.645.
  * **The realisation the data predict.** Across 380 screened orthogonal parts, a 2013–19 z correlates 0.28 with the 2020–24 z. Candidates with |z| ≥ 2 early kept 0.37–0.41 of their β. The reliability of a full-discovery z is k = 0.43–0.48. Under k = 0.41–0.48:

    | Score | Power at Look A (t(20)) | Power for A + B by August 2027 |
    |---|---:|---:|
    | Omnibus | 0.39–0.49 | 0.55–0.66 |
    | Each group | 0.13–0.24 | |

  * This is consistent with the prereg's "a quarter to a half". But the README leads with "96% if all of it is there". Lead instead with about 45% for Look A and about 60% by August 2027 (with B1's design).
  * The SE formula itself holds: in 21 nineteen-month windows of discovery, the omnibus's cluster SE averaged 1.00 times the formula's (SD 0.14); G4's averaged 1.13.
* **m2. The realisation ratio mixes units.** `look.fit` (line 152) rescales each score to the window's RMS. G5's RMS is 1.10 times higher on Look A (the doubles member exists for every Look A match), so a constant effect would read a realisation of 1.10. Report β per frozen unit, or divide by the RMS ratio.
* **m3. H6–H8 are protocols the code does not implement.**
  * H7 has no registry entry: no values, frozen projection, scale or `look.py` code. Freeze them now from the store's column on ≤ 2024.
  * H6 leaves the hour, the wind variable and the WBGT formula open. Fix them before anyone sees Look A's G3 reading.
  * H8 needs its poller started at the freeze, and someone named to start it. Coverage allows the 3,000-match trigger: 350–570 main-tour matches a month carry a Polymarket market in 2026 (`exposure_checks.json`).
* **m4. Small code faults** (observed):
  * `look.holm` (line 209): `max(run, nan)` returns `run`, so a failed fit's NaN p would receive an adjusted p.
  * The group "contrary" verdict (line 219) is not Holm-adjusted while "confirmed" is: an asymmetric rule.
  * `screen._model_frame` (line 417) filters on date only, so the 136 season-2025 results are loaded (unused). Add `season ≤ 2024` to the read, as `load_frame` now does.
* **m5. Uneven inputs** (CLAUDE.md's warning sign; observed, `score_rms_by_season.csv`). The orthogonal RMS by season:
  * **Fame** rises steadily: 0.93–0.98 in 2013–17, 1.10 in 2025, 1.19 in 2026. Fame counts titles from 2010, and its raw A − B RMS goes from 1.27 in 2013 to 1.58 in 2026.
  * **Past fatigue** jumps to 1.07 in 2025–26 (0.80–0.97 before).
  * **Doubles elsewhere** falls to 0.76–0.86 as men's doubles play drops.
  * Put the input check in the prereg, and consider a rolling-window fame (stationary from 2015).
* **m6. Text** (observed):
  * § 4 (line 116) says values are built "on the tables of the instance the look uses". Look A's frozen values were built on the repository's 8 Oct Stage 0, the 12 Oct clock and the sandbox's IOS and Stage B (S3's caveat 1).
  * § 7 (line 144) gives Look A as 8,455 matches (by date); it is 8,591 (by season).
  * § 12 (line 240) "rebuilds … or reports the raw-score secondary" is a choice made at look time. Make it a rule.
  * README line 14 says "about 100" new statistics; the prereg says about 140.
  * README line 18 "unrelated to each other" omits the seed signal shared by G4 and G5.
* **m7. Look B cannot deliver two of its secondaries as coded.**
  * "Beyond the model" reads `edge_anatomy/analysis.parquet`, which ends on 28 Jul 2026.
  * There is no Pinnacle base after 7 Sep 2025.
  * Say so, or register the forecast table to build.
* **m8. Registration-wide error rate.** If B1's gatekeeping is not adopted, state the chance of at least one false "confirmed" across H0–H8 (about 0.2 if nothing is real).

## 4. What I checked and found sound

* **Blinding** (observed):
  * **The harness:** `load_frame` filters season ≤ 2024 and date < 2025 inside the read and asserts it. The model lens reads dates < 2025 (m4). The move lens uses seasons ≤ 2024.
  * **The builders:**
    * Luck: calibration on 2010–12; persistence and drift on matches with lf + 1 ≤ 1 Jan 2025; the loading c through `load_frame`.
    * Rhythm: stale-line and time-source facts on ≤ 2024.
    * Pool rebuild: screens through `load_frame`; counts stop at 28 Jul 2026.
    * Market: MP-10, with the M3 note.
  * **`look.py`** refuses any season > 2024 without `--look` and `--owner-go`.
  * **The three values files:** 67,226 rows each, hashes equal to the registry's, no result-like column.
  * **Every agent's disclosure** concerns outcome-free counts or prices. No 2025+ outcome or line move of a registered statistic was read by this study.
* **Look A is still a valid one-shot test** of the registered scores, subject to M2 (a modest leak channel) and M3 (disclosure).
* **register.py's numbers, re-derived independently** (observed, `rederive.csv`, `rederive_checks.json`):
  * My own loader, input list, scipy least squares, sklearn's logistic fit and my own cluster sandwich.
  * The projections and scales are identical (difference 0).
  * Omnibus β 0.0877, z 8.52 (eras 4.31 / 5.81 / 4.77 / 2.44). All five groups and all 13 members agree with `discovery_registered.csv` to |Δz| ≤ 9e-6 and |Δβ| ≤ 9e-8.
  * Per-era β of the omnibus: 0.070, 0.104, 0.106, 0.073. Of G1: 0.020, 0.049, 0.054, 0.011 (a decay to watch, as the README says).
* **The dry run** (observed, `dry_run_result.json`): 839 fields equal to the lead's `looks/dry-run/result.json`. Only the recorded registry path string differs. The omnibus reads +0.0733, z +2.44, G 24.
* **The base** (observed, `robustness.csv`):
  * **No price-shape or context artefact.** A per-tour restricted cubic spline in L plus per-tour price slopes by level, round, surface and indoor moves the omnibus from 8.52 to 8.63; G3 goes to 3.31, G4 to 4.72, G5 to 5.01.
  * **No source-switch bias.** On 28,523 matches of 2018–24 priced by both books, the omnibus reads:

    | Base | z | β |
    |---|---:|---:|
    | Pinnacle's close | 6.49 | 0.0968 |
    | BetOnline's close | 6.55 | 0.0974 |
    | A switch from Pinnacle to BetOnline in mid-window, pooled base (as Look A) | 6.51 | 0.0969 |
    | The same switch, base by period | 6.52 | 0.0967 |

  * **No stale-line artefact for the omnibus.** β is 0.102 on fresh BetOnline last lines and 0.088 on stale ones. G3 leans stale (0.045 against 0.020), G4 leans fresh (0.069 against 0.034).
  * `bol_after_listed_min` is never missing where BetOnline's close exists, so the fresh/stale split is well defined.
* **Timing** (observed, code read and checks):
  * **The venue pace** sums serves released at lf + 1 ≤ es by venue (`f09_venue.venue_state` with `clock_sum`): leak-proof by construction.
  * **Own-sequence members** use strictly earlier rows: the luck sums (shift-by-one prefix sums), flattery (the previous played row), rest (the previous played match's end), past fatigue (strictly earlier rows in 14 days) and the letdown (the last Slam QF-or-later match's lf ≤ es).
  * **The doubles window** is relative to `obs`, not `es`. But only 9 of 7,467 non-zero player-rows have an other-event doubles day on or after `es`: immaterial.
  * **The rest end rule:** Flashscore-first and minutes-first agree in ≥ 99.6% of player-rows in every tour-season, so the men's 2025–26 source shift does not move `rb03_lt20`.
  * **Short rest uses the actual first point.** At the close it is effectively known; at an earlier bet time only the schedule is.
* **Distinct groups** (observed, `proxies.json`, `robustness.json`):
  * With the registered values (not the store stand-ins), the group scores correlate at most 0.084 in discovery and 0.12 on Look A (G4 ~ G5).
  * Fitted jointly, the groups keep z 4.07, 3.61, 3.46, 3.87 and 4.93.
  * Non-linear proxy R² (inputs, context, price): G1 0.003, G2 0.004, G3 0.04, G4 0.16, G5 0.12 (mostly the bye seed).
* **"The model leaves it unused"** (observed, 2020–24): beyond the instance's forecast the groups read 2.30, 2.19, 2.65, 2.85 and 2.66, against 2.30, 2.01, 2.70, 3.29 and 2.71 beyond the close.
* **The bases are oriented correctly.** BetOnline's close, Pinnacle's close and the forecast correlate 0.995–1.000 with the odds input, in discovery and on Look A.
* **Shrinkage is stated honestly.** "A quarter to a half" matches the screened universe's 0.37–0.48 (m1). Raw forms replicate far more (0.83–0.85), because they carry in-model relatives.

## 5. On the design (brief item 5)

* **The omnibus is the right primary** for small effects spread over areas. Alternatives:
  * A sign-consistency rule discards magnitudes and has little power with five groups.
  * Weighting by discovery z would chase noise (k ≈ 0.45).
  * A held-out era is no longer available, because every era chose the groups. The cross-era replication in m1 is its substitute and should be cited as the basis of the shrinkage.
* **What would make it clearly better:**
  * B1's two-look boundary and gatekeeping.
  * A registered empirical-Bayes secondary: P(β_g > 0) under a prior centred on k × the discovery β, with k = 0.45 from the screened universe. It gives the owner a probability per group instead of "unresolved".
  * A wild-cluster-bootstrap p beside the t test. With 21 clusters the cluster SE scatters by ±14% from window to window.

## 6. Reproduction

All scripts are in `data/studies/unpriced_leads/team/red_team/`. Run each with `PYTHONDONTWRITEBYTECODE=1 ./python.sh <script>` (BLAS pinned to one thread inside); a minute or two each, except `proxies.py` (4 minutes).

| Script | What | Output |
|---|---|---|
| `rt_common.py` | Independent loaders, projection, fit (outcome loader ≤ 2024 only) | — |
| `rederive.py` | Re-derivation of every registered discovery reading | `rederive.csv`, `rederive_checks.json` |
| `dry_run_here.py` | The registered dry run, written here, compared with the lead's | `dry_run_result.json` |
| `outcome_free_checks.py` | Look A's size, blocks, sources, freshness; RMS by season | `outcome_free_checks.json`, `score_rms_by_season.csv` |
| `robustness.py` | Base variants, source switch, fresh/stale, retirements, joint fits, beyond the model (≤ 2024) | `robustness.csv`, `robustness.json` |
| `shrinkage.py` | Cross-era replication over the screened universe | `shrinkage.json`, `shrinkage_universe.csv` |
| `proxies.py` | Group and member correlations; non-linear proxy R²; raw members' R² | `proxies.json`, `member_corr_*.csv` |
| `data_checks.py` | Fame drift; doubles window against `es`; rest rule (i) against (ii) | `data_checks.json` |
| `exposure_checks.py` | Orthogonality on Look A; G1 against the 365-day luck; Polymarket coverage | `exposure_checks.json` |
| `power_check.py` | t(20) power; realisation from `shrinkage.json`; false confirmations across looks | `power_check.json` |
| (console) | Correlation with the instance's adjustment; SE in 19-month windows; two-look power | `model_adjustment_corr.json`, `se_windows.csv`, `sequential_power.json` |

## 7. Process notes (for the lead's log)

1. **Read** (no result of mine yet): the brief, CLAUDE.md, the process log, the draft prereg, the registry, the README draft, the builders' and pool memos in full, and the brainstorm memos for anything touching 2025+. Then the code: `screen.py`, `look.py`, `register.py`, `resolution.py`, `member_coverage.py`, `group_corr.py`; the docstrings and timing paths of `build_luck.py`, `build_rhythm.py`, `rebuild_pool.py`; `f09_venue.py`, `f19_motiv.py`, `f28_state.past_fat`; market_anchoring's README and `luck.py`.
2. **Before any fit**, outcome-free:
   * The values files' schemas and hashes.
   * The frame's seasons and odds sources.
   * market_anchoring's 2026 dates (the date column only).
   * Stage 0 counts by month.
3. **Fits on ≤ 2024, in order** (results seen at each step):
   * Re-derivation (exact).
   * Dry run (exact).
   * Outcome-free Look A checks.
   * Robustness (part A crashed twice on my own collinear columns, a duplicated linear spline term and men's best of 5 equal to men's Slams; fixed, nothing else changed).
   * Shrinkage, proxies, data checks, exposure checks, power.
   * B1–B3 and M1 were identified from the code and documents before any fit. M2, M4 and M5 rest on the fits.
4. **No threshold or variant was chosen after seeing a result to strengthen a finding.** The 19-month SE windows and the two-look boundaries were computed after the power check, to size the fixes.
5. **Deviation:** none from the brief. I did not run `look.py --dry-run` from the command line, because it writes into `looks/dry-run/`, outside my allowed folder. I ran the same `look.run()` and wrote its output here. No Git command was used.
6. **Disclosure.** My first correlation of the scores with the instance's adjustment (q_full minus the close) pooled Look A's rows. For 2026 rows, q_full was trained walk-forward on seasons up to 2025, so that figure (G4 0.122) embeds 2025 outcomes through training. I then restricted the check to season 2025 (trained on ≤ 2024) and report only that version. No outcome was read directly.
7. **BLAS** was pinned to one thread for every fit. No GPU was used.

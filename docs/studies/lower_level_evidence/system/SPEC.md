# The level-evidence system: the team's specification

9 October 2026, 20:00 UTC · Written by the lead (the main session) · Binding on every role of this run. Only the lead
changes it, dated, in §12. The frozen pre-registration (§7–§8 with its hash) is
`data/studies/lower_level_evidence/system/preregistration.md`.

## 1. The goal

**The owner (9 Oct, condensed).** Find the proper relationship between lower-level evidence (Challenger, qualifying,
later ITF) and main-tour (250+) evidence, and build it. Verify that it is the best way to build the men's model. For
data that does not exist yet (ITF box scores of 2018–2024, collection plan P7, about 31 Oct – 2 Nov), leave a test ready
to run. Deliver actionable insight and one cohesive system, not more exploration.

**The owner's answers.**
* Hand over the verified version for approval. Do **not** integrate it into the current-best-model template, and do not
  edit any decided file.
* **Spend the 2025–2026 holdout** on the final check: once, after every choice is frozen on 2020–2024.

**The owner's note on statistics** (verbatim): "identify wheter a statistic is independent of its opponent or dependent
to figure out if it qualifies for an offset depending on level of skill. For example how many points given up on their
break is dependent of the opponent. Age is not dependent on the opponent. 1st Serve speed is not really dependent on the
opponents skill. Most stats will be dependent on the opponent I believe?"

**The owner's precedent** (UFC): a new fighter is treated as an average *new* fighter, skewed toward his record outside
the UFC, not as an average fighter.

## 2. What the first run established, and what it left open

Sources: `docs/studies/lower_level_evidence/README.md` and `team/01`–`08`.
* **Today.** 49 of the 58 inputs read lower-level matches with no level awareness.
  * The one-step forms keep about 78% of the level shift. They read each match against the opponent's own norm, built
    from his own opponents at whatever level.
  * `points_52w` pools raw rates.
  * The joint solves (IOS, `ratings_iid`) have no level term. The products' zero point moves with the pool's level mix.
* **The first remedy** (role 08, FP): constant per-level offsets in the 17 forms and `points_52w`.
  * Men: +0.083 mLL [+0.002, +0.164] against the reference, better; all of it from `points_52w`.
  * But the share control R_S2 did as well (FP against R_S2: −0.003, P(better) 0.49).
  * *Inferred:* with one constant offset per level, translating is close to re-centring each input by the player's
    lower-level share, which TabPFN can learn from a share input.
* **Statistic level** (role 03): translated and weighted beat pooled, and main-only lost to pooled.
  * The men's Challenger weight read 0.5–0.8.
  * That estimator had no opponent term, no recency and one prior mean for everyone, so the weight is confounded.
* **Results.** Removing lower-level results from Elo costs 6.8 / 6.4 mLL at the statistic level; ×0.75 is unresolved.
* **ITF box scores** exist only from January 2025 to May 2026. They reach 42% of women's and 7% of men's 2025–26 model
  matches. The reference's 2025–26 inputs therefore carry evidence its training seasons never had.

**Open:** the proper relationship (opponent-aware, weighted, with a newcomer prior, fitted walk-forward), applied the
same way in every input family, and its model-level value against the alternatives.

## 3. The relationship (the hypothesis this run builds, measures and tests)

**The principle.** Every lower-level observation enters an input exactly where a main-tour observation would, after
three things:
* it is translated into main-tour terms, to the extent that the statistic depends on who is across the net;
* it is counted at an exchange rate;
* a player with little main-tour evidence starts from the average main-tour newcomer of his tier, not from the average
  main-tour player.

**Three components,** per statistic s, tour g and level L (TQ, GSQ, CH, CHQ; ITF and ITFQ once P7 lands), all fitted
walk-forward:

1. **Translation.** A lower-level observation about player X is shifted by
   **T = γ_{s,g} · (X's opponent's strength − the main-tour reference opponent's strength) + δ_{s,g,L}**.
   * **γ is the statistic's opponent dependence:** how far the statistic moves per unit of opponent strength, measured
     inside the main tour (role A). This is the owner's note made operational. γ ≈ 0 means the statistic does not
     qualify for a skill offset.
   * **Strength is read on one scale across levels:** by default the opponent's pre-match Elo from results at every
     level, as the frozen reference built it, in every arm. Role A may show that a statistic-specific counter-skill
     explains more.
   * **δ is the residual level effect** the opponent's strength does not explain: conditions, balls, the rating pools'
     calibration. It is used only where role A's class allows it (§4).
   * **The translation is per match, not per level.** A Challenger final against a top-100 player is translated less
     than a first round against the 600th. A constant offset cannot do this, and a share input cannot carry it.
2. **The exchange rate w.** A translated observation's weight in an aggregation is w_{s,g,L} times a main-tour
   observation's weight there. A lower-level match is worth w main-tour matches.
3. **The newcomer prior.** Where an input shrinks toward a population value, a player's target is the average main-tour
   newcomer of his home tier. It is kept only if role B shows it predicts better at the statistic level.

**Fitting.**
* The parameters used for season Y are fitted on results available before season Y's first match on the match clock
  (`lf + 1 ≤ es`), never later.
* Seasons 2025 and 2026 use parameters fitted on ≤ 2024 and ≤ 2025. They are produced mechanically by frozen code, and
  nobody reads their diagnostics before the holdout readout.
* The builders' tuned constants stay the reference's (`IOS_CONSTANTS_VERSION=2026-10-08_reference`; Stage B's constants
  as the reference build chose them).

**Per input family** (the same principle in each family's own units; the engineers confirm each insertion point from
`team/01_lineage.md`):

| Family | Inputs | How lower-level evidence enters under the system |
|---|---|---|
| Raw rates | `points_52w` | Each lower-level match's serve and return points won are translated by T (the opponent's strength gap, plus δ) and weighted by w |
| One-step forms | `adjperf_tpw_2w`, `form_*` (12), `formdef_*` (4) | The opponents' norms are re-referenced to the main tour: each lower-level row in a norm is shifted by the strength gap of the player who produced it, plus δ. Lower-level matches are weighted by w in the decay-and-shrink. The newcomer prior is the shrink target if kept |
| Joint solves | `iosO_*`, `iosD_*` (14), `ios_points_short`; `prod_*` (7) follow | A level term (δ in the solve's own units) and observation weights w; the solve itself handles the opponent. The newcomer prior is the ridge target if kept |
| Online point ratings | `ratings_iid` | As the joint solves: a level offset, and K × w |
| Results ratings | `elo_overall`, `elo_surf_offset`, `elo_games` | Opponent-adjusted by construction: K × w_results only |
| Workload, intrinsic | `sets_14d`, `surf_season_*`, `surf_layoff_*`, `age`, `age_sq` | Untouched: a set is a set, and age is age |
| Market, context | `odds_logit`, `tour`, `surface`, `level`, `indoor`, `best_of`, `round` | Untouched |
| Stage 2 | `spd_L` | Untouched unless role A finds a level problem. Serve speed does not depend on the opponent, but edition centring is relative to the field |

**ITF and ITFQ box scores are excluded (w = 0) from every box-score family** until their parameters can be fitted on
training seasons, which needs P7.
* The principle: lower-level evidence enters only after its relationship has been estimated on the training period.
* ITF results stay in Elo as today.

## 4. Statistic classes (role A decides; the layer obeys)

| Class | Meaning | Treatment |
|---|---|---|
| OPP | Depends materially on the opponent's skill | Translation (the γ term, plus δ where the residual is real) and w |
| ENV | Not opponent-dependent, but shifted by level conditions or by field-relative centring | δ only where it is measured; w |
| INTR | Intrinsic (age) | Untouched |
| WORK | Workload or experience counts | Untouched |
| RES | Results rating | w_results only |
| CTX | Market or context | Untouched |

Role A justifies its materiality thresholds and fixes them before role B fits.

## 5. The team

| Role | Owns the question | Delivers | Starts | Depends on |
|---|---|---|---|---|
| **A Classifier** | Which statistics depend on the opponent, and by how much (γ)? Is the level effect an opponent effect? | `classify.py`; `system/classes/`; `A_classes.md` | now | nothing |
| **B Relationship** | Which translation, exchange rate and prior predict main-tour performance best, walk-forward? Is 0.5–0.7 right? | `relationship.py`; `system/relationship/` (parameters by season, validation, dose curve); `B_relationship.md` | now | A's γ function (a stub until then) |
| **C1 Layer engineer** (lead engineer) | One layer in every lane-1 family (forms, `points_52w`, `ratings_iid`, Elo), and the arms pipeline | `level_layer.py`, `system_sandbox.py`, `system_arms.py`, `system_gates.py`; `system/arms/`; `C_layer.md` | now | B's parameters (identity until then); C2's hooks |
| **C2 Joint-solve engineer** | The layer in the joint solves (surface IOS, `ios_points_short`, products) | `level_layer_ios.py`, its patch and gates; a section of `C_layer.md` | now | B's specification of the level term |
| **D Evaluator** | Is the system the best way, at the model level? | `system_pairs.py`, the fits, the readings; `D_verification.md` | now (infrastructure) | arms from C1 |
| **E Red team** | Is anything leaking, over-claimed or mis-specified? | `E_red_team.md`, at three checkpoints | checkpoint 1 | everything |
| **Lead** | The spec, the pre-registration, the checkpoints, the one document, the P7 plan | `SPEC.md`, `preregistration.md`, the final `README.md` | | all |

**Paths:**
* code: `src/eda/lower_level_evidence/`;
* tests: `test/lower_level_evidence/`;
* data: `data/studies/lower_level_evidence/system/` (written `system/` below);
* reports: `docs/studies/lower_level_evidence/system/`.

**Each role writes only its own files** and may read anything.
* Existing files of the first run are read-only, including `translate_hooks.py`, `candidates/` and `team/`. Copy from
  them; do not edit them.

## 6. Interfaces

### 6.1 Classes (A → B, C1, C2, D)

* **`system/classes/classes.csv`:** one row per (input or base statistic, tour). Columns:
  `name, kind (input|stat), base_stat, side (serve|return|defence|none), family, class, gamma, gamma_lo, gamma_hi,
  gamma_unit, level_shift_<L>, explained_share_<L>, residual_<L>, rule`. Plus a sha256 file.
* **`classify.gamma(...)`:** returns γ per base statistic and tour from the data available through a given date. It is
  the walk-forward version B calls; A documents the signature.

### 6.2 Parameters (B → C1, C2)

* **`system/relationship/params.parquet`:** one row per (season_used, tour, stat, level). Columns:
  `gamma, delta, w, w_lo, w_hi, delta_lo, delta_hi, n_players, strength_ref, prior_mu, prior_k, fit_through (the last
  result date used), method_version`.
* Rows with stat = `results` carry w_results.
* Units: the logit of the statistic's rate per opportunity, unless a column says otherwise.
* A sha256 file sits beside it.

### 6.3 Layer config (C1 owns the loader; every arm uses it)

* **The switch:** JSON named by the environment variable `LLE_LAYER=<path>`. Unset, every hook returns its input object
  unchanged.
* **The shape:**
  ```
  {"name": "SYS", "tours": ["atp"], "params": "<params.parquet>", "params_sha256": "...",
   "classes": "<classes.csv>" | null, "translate": true, "weight": "fitted" | <0..1.5>,
   "weight_results": "fitted" | <0..1.5>, "prior": "newcomer" | "pool", "itf_box": "exclude" | "as_is",
   "families": {"points_52w": true, "forms": true, "ios": true, "ios_points_short": true, "ratings_iid": true, "elo": true}}
  ```
* **The identity config** must reproduce the reference's 58 inputs exactly on all 67,226 matches: translate false,
  weights 1, prior pool, `itf_box` as_is.
* **The patches:** each engineer exposes `apply_patch(sandbox)` and `check_patch(sandbox)`. C1's `system_sandbox.py`
  applies both engineers' patches to a sandbox copy. They are never applied to the repository.

### 6.4 Arms (C1 builds; D fits and scores)

* **`system/arms/<ARM>/`** holds `model_frame.parquet`, `model_inputs.json`, `layer_config.json`, `gates/` and the
  build's logs.
* D writes `fits/` and `vs_reference_2026-10-08/` inside it.

## 7. The arms (fixed before any score; copied into the pre-registration)

The layer applies to **men only** unless stated; women's inputs stay the reference's.

| Arm | Config | Question |
|---|---|---|
| **REF** | the frozen reference | Today: equivalent pooling |
| **SYS** | translate on; w fitted; w_results fitted; prior per role B; ITF box scores excluded | **The proposed relationship (primary)** |
| SYS_w0 | as SYS, w = 0 | Main-tour evidence only, for statistics |
| SYS_w50 | as SYS, w = 0.5 | Dose |
| SYS_w100 | as SYS, w = 1 | Translation only, no discount |
| SEP_ALL | no translation; w = 0; w_results = 0; prior pool | Complete separation |
| SYS_NOCLASS | as SYS, classes ignored: every statistic translated by its own γ and δ | The owner's taxonomy, at the model level |
| SYS_S2 | SYS plus R_S2's two share inputs | Does the share add anything beyond the system? |
| R_S2 | exists (role 08): the reference plus the two share inputs | The share control |
| SYS_PLACEBO | SYS's per-match change (all changed inputs together), permuted within tour × season | The mechanism against any perturbation of that size |
| SYS_BOTH | SYS on both tours, with women's parameters | Women, for information |
| REF_noITF | the reference with ITF box scores excluded (w = 0) from every box-score family; nothing else | The ITF regime in the reference's 2025–26 inputs (holdout only) |

**Optional, if time allows,** fitted after the others: SYS_w25 and SYS_w75.

## 8. The verification protocol (copied into the pre-registration)

**Scoring.** Both stages through `compare.py`; seeds 0–3; mLL per match.
* + means the first-named model has the lower log loss.
* Intervals: four-week blocks plus the paired seed variance.
* "Better" or "worse" when the 95% interval clears 0; otherwise "unresolved" with P(better).

**Dev: 2020–2024** (fits 2019–2024), every arm except REF_noITF.

**The selection rule.**
* **SYS is the proposal.** It stays selected unless a challenger beats SYS on dev, men, with P(better than SYS) ≥ 0.90.
  * The challengers: SYS_w0, SYS_w50, SYS_w100, SEP_ALL, SYS_NOCLASS, SYS_S2 and R_S2.
  * If more than one qualifies, the selected arm is the one with the largest point gain over SYS.
* If the selected arm's dev reading against REF (men) has P(better) < 0.50, **REF is selected** (no change).
* **Women: no selection.** The women's treatment waits for P7.

**The holdout: 2025–2026.** Every arm is fitted on 2025 and 2026; stage 2 refits walk-forward on 2019 .. Y − 1. The
holdout is opened once, after three things:
1. the dev readings and the selection are written down;
2. the red team's checkpoint 2 passes;
3. the lead writes `system/holdout_unlock.json` with the pre-registration's hash.

The scorer refuses to read seasons after 2024 without that file.

**The holdout readings.**
* **Primary:** SELECTED against REF, men.
* **Decomposition, both tours:**
  * SELECTED against REF_noITF: the Challenger and qualifying part;
  * REF_noITF against REF: the ITF part.
* **Secondary, read with no separate decision:**
  * every arm against REF;
  * the dose curve: SYS_w0, SYS_w50, SYS, SYS_w100;
  * SYS against SYS_NOCLASS, SYS_PLACEBO and R_S2; SYS_S2 against SYS;
  * SYS_BOTH, women;
  * the strata: the less-exposed side has fewer than 10 main-tour results in 365 days; the share gap is 0.5 or more;
    falsification (both sides 20+ main-tour results and both shares under 0.10);
  * each season;
  * dev and holdout pooled (2020–2026), for the primary and the dose curve.

**The recommendation** (guiding, under the adoption framework; the owner decides):
* **Recommend SELECTED** for the men's final model if either holds:
  * the holdout primary is better;
  * or it is unresolved with P(better) ≥ 0.80, and the pooled 2020–2026 reading is better, and no secondary is worse.
* **Holdout primary worse:** recommend REF (no change), with the readings.
* **Otherwise unresolved:** report P(better). Add nothing beyond "reversible, and it points the right way" where it does.

**The input check.**
* Run compare.py's part 1 on every arm before its scores.
* Read a flag against the tour-season's own change in evidence mix (the first run's lesson).
* Write the expected broad change down before reading.

## 9. Ground rules (every role)

1. **Read `CLAUDE.md` first.**
   * Python through `./python.sh`; GPU fits through `./python_tabpfn_local.sh`.
   * No state-changing git. Delete nothing: sandboxes stay, and cleanup is the owner's call. No downloads or scrapers.
2. **Decided files are read-only.** Builders are patched only in sandbox copies:
   `MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_sys<n>`, all new. Leave the first run's `tnr_lle` alone.
3. **The data is the frozen reference's** (`src/eda/lower_level_evidence/common.py`).
   * **Not read until the holdout is unlocked:** the outcomes of 2025–2026 matches (results, and box scores as
     evidence of performance) for any estimate, selection or diagnostic.
   * **Allowed:** counting those matches and building inputs from them.
   * **Also allowed:** mechanical walk-forward parameter fits for 2025 and 2026, by frozen code, with their
     diagnostics unread.
4. **The match clock** applies to anything that combines players: a result is in at `lf + 1` and read at `es`. Run
   `src/eda/match_timing/probe.py` on every cross-player change.
5. **Label every claim** Observed, Inferred or Suggestion, and cite path:line or the file.
6. **Scores are never a bare sign.** Say "better" or "worse" when the 95% interval clears 0, otherwise "unresolved"
   with P(better). Never "tie".
7. **The owner's thesis:** per-statistic point-level profiles first. Elo and win-rate aggregates are priced-in
   controls.
8. **Plain writing.**
   * Give numbers with units.
   * Start every report with "In short" (8 bullets at most) and end it with "What it does not show".
9. **Checkpoints.** Report to the lead at the checkpoints in §10. Ask the lead rather than guess on anything that
   changes another role's work.
10. **Share the machine.** 8 cores / 16 threads, 126 GB of RAM, 391 GB of free disk, and one RTX 5090 that another
    session's fits (`lean_review/fits.py`) are also using. Run CPU builds at most 3 at a time. Only role D runs GPU
    fits.

## 10. Checkpoints

| | When | Who | Gate |
|---|---|---|---|
| CP0 | A's classes and γ function are ready | A → lead | B and the engineers adopt the class table |
| CP1 | B's method is frozen (parameters and their sha256); the C1 and C2 identity gates pass | lead + E | E audits the leaks, the clock, the estimator (planted recovery) and the hooks. The lead hashes a dated addition that fixes SYS's internals. Only then are SYS-family arms built |
| CP2 | The dev readings and the selection | D → lead + E | E audits. The lead writes the unlock |
| CP3 | The holdout readings | D → lead + E | E re-derives the headline numbers. The lead writes the document |

**Arms that need no parameters** (SEP_ALL, REF_noITF) may be built and fitted as soon as the identity gates pass. Their
scores are not read before the pre-registration addition at CP1.

## 11. The final document (the lead writes it from the roles' reports)

`docs/studies/lower_level_evidence/system/README.md`:
1. **The decision proposed:** one paragraph, and a table of what changes.
2. **The relationship:** the three components; the class table; the men's parameters with intervals.
3. **The proof:**
   * at the statistic level, B's comparison;
   * at the model level, the dev and holdout readings;
   * the dose curve.
4. **How it is built:** the layer, the commands, the gates.
5. **Women and ITF:** the P7 plan, with its arms, commands and pass/fail criteria.
6. **Renewal:** when and how to refit.
7. **What it does not show.**

## 12. Changes

(Dated entries, by the lead only.)

* **9 Oct, 20:50 UTC: the owner asks for a test of the rule of 8 October.** Pre-registered as
  `system/preregistration_addition_1.md` (sha256 `c718e6d0…`), before any score of this run.
  * **New arms:**
    * SYS_ITFASIS and SYS_BOTH_ITFASIS: ITF box scores as the reference treats them; holdout only;
    * NEW_ASIS and NEW_SYS_BOTH: on a candidate Stage 0, C0_now.
  * **New role F, data wiring.** F builds C0_now with `candidate_stage0.py`, into `system/stage0/<label>/`, and reports
    in `F_rule_data.md`. C0_now is the frozen Stage 0 plus the excluded data on disk that can be linked with validated
    identity. The same code builds C0_P7 when P7 lands.
  * **New hand-off:** `system/stage0/<label>/READY.txt` (F → C1).
* **9 Oct, 20:50 UTC: the schema of role A's `classes.csv` is binding.** The permission for a level term is one column,
  `delta_levels` (for example "CH,CHQ" or "none"). It replaces the per-level columns sketched in §6.1.
* **10 Oct, 01:49 UTC: checkpoint 1.** Addition 3 (`f2063433…`) freezes SYS's internals, the scorer and the build
  code. It also:
  * caps fitted w, w_joint and w_results at 1;
  * adds the arm RES_ONLY;
  * registers NEW_ASIS_PRE;
  * pins the NEW arms to the reference's constants.
* **10 Oct, 03:00 UTC: the owner's decision of 9 Oct replaces the decision layer.** Decision:
  `docs/decisions/2026-10-09-adoption-by-change-class.md`; applied in `system/owner_decision_2026-10-09.md`; adopted
  in addition 4 (`754e055c…`). No score existed. §8's selection rule, recommendation and addition 1's interpretation
  now read as follows:
  * a challenger must read "better" than SYS to be selected;
  * REF is chosen only on harm (worse by more than 0.10 mLL, with the whole interval below 0);
  * SELECTED is recommended unless the holdout primary or a Holm reading shows harm;
  * new data enters by the system's route unless NEW_SYS_BOTH shows harm.
* **9 Oct, 20:50 UTC: C2's step for the joint solves.** With the IOS families on, a build runs
  `level_layer_ios.run_ios_part(sandbox, out)` before lane 1's `leakproof_frame`. `ios_points_short` and the pooled
  IOS are read from stored tables that no lane rebuilds.

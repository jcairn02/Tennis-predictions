# Lower-level evidence in the 250+ model: the system, the proof and the plan

10 October 2026 · For the owner · Written by the lead from the reports of roles A–G. **This is a proposal; adoption is
the owner's call.** Nothing in the template or in the decided files has changed. Everything was built in sandboxes and
tested against the frozen reference of 8 October.

**Keys.**
* **Model-level scores** are mLL (milli-log-loss per match). + means the first-named model is better.
  * Intervals are 95%. "Better" or "worse" when the interval clears 0; otherwise "unresolved", with P(better).
  * Both stages: TabPFN, then the serve-speed adjustment.
  * Seeds 0–3.
* **Statistic-level scores** are milli-log-likelihood per opportunity, from predicting a player's next main-tour match
  statistics.
* **Labels.** *Observed* means computed and on file. *Inferred* means reasoning. *Suggestion* means a proposal.

## The answer in short

1. **The relationship.**
   * **The rule.** A lower-level match is evidence about a player's main-tour level once it is translated into main-tour
     terms.
   * **How much a statistic moves** depends on how strongly it depends on the opponent, times how much weaker this
     particular opponent was than a main-tour opponent. Then it is counted at an exchange rate.
   * **Opponent dependence.**
     * 17 of 19 men's statistics depend on the opponent; first serves in and double faults do not.
     * Serve speed needs no translation.
     * Age is never touched.
   * **The exchange rate (men).**
     * A Challenger point is worth about 0.6 of a main-tour point (0.63), or about 0.55 of a match. The level's mean is
       lifted by about 0.035 by the estimator-prior artefact below.
     * A qualifying match is worth about 1 once translated.

     (*Observed*, roles A and B.)
2. **At the statistic level, the relationship is clearly better than pooling as equivalent,** in role B's predictor.
   It predicts players' next main-tour statistics much better than treating lower-level matches as equivalent:
   * men +0.41 [+0.34, +0.47]; women +0.19 [+0.15, +0.23];
   * about twice that for players with little main-tour history.

   Using only main-tour evidence is worse for those players on both tours. (*Observed*, role B.)
3. **At the model level, on 2020–2024, the system neither helps nor harms.**
   * Men: −0.008 [−0.162, +0.145], unresolved, P 0.46.
   * Dropping the lower-level evidence instead is clearly worse (−0.59).
   * The model-level test cannot tell equivalent pooling from translated inputs: ±0.15 on dev, ±0.43 on the holdout.
   * The two share inputs ("how much of this player's evidence is lower-level") lean better for men (+0.15, P 0.93).
     They are a lead for the feature pool, not part of this decision. (*Observed*, role D.)
4. **The holdout (2025–2026), read once, shows no difference and no harm.**
   * The system against today's model, men: +0.011 [−0.425, +0.447], unresolved, P 0.52.
   * 2020–2026 pooled: −0.003 [−0.164, +0.159], unresolved.
   * None of the eight subgroup checks reads worse.
   * Dropping the lower-level box scores is worse over 2020–26 pooled: −0.50 [−0.87, −0.13], negative in every season
     and every seed. On the holdout alone it is unresolved (−0.30).
   * A single period's readings cannot resolve changes of this size. A shuffled placebo of the system's size moved the
     holdout by +0.35 for men, and +0.215 [+0.031, +0.398] on both tours. (*Observed*, role D; the red team's CP3.)
5. **The proposal, for men:** adopt the system as the route by which lower-level evidence enters the model.
   * **Why.** The owner's decision of 9 October judges a repair by its data evidence and uses the model comparison as a
     harm check. This system is a repair: data already in the model, entering in main-tour terms. Its statistic-level
     evidence is strong, and no model-level reading shows harm.
   * **No edge credit.** Expect no measurable accuracy gain now. The gain is a correct route for the lower-level data
     that is arriving.
   * **Four qualifications** (red team, CP3):
     * The harm check is weak. It flags a true −0.20 mLL harm only about 13% of the time.
     * No model-level reading supports the system: dev −0.008, holdout +0.011, pooled −0.003.
     * The Elo-weighting part alone (RES_ONLY) leans better than today's model on the holdout: +0.055, P 0.81. The full
       system reads −0.045 against it. Both readings are unresolved.
     * The original pre-registered rules would have chosen SYS_S2 (the system plus the two share inputs) on dev. They
       would then have made no recommendation: SYS_S2 against today's model on the holdout reads P 0.64.
6. **Women** follow the ITF test (P7, about 22 Oct – 2 Nov). The plan is ready to run: [P7_plan.md](P7_plan.md).
7. **The rule of 8 October** (new lower-level data enters only as a tested candidate). For this batch, the rule
   protected against nothing measurable.
   * **The test.** The data it keeps out was wired into a candidate Stage 0: 298,008 matches, mostly ITF qualifying.
     Entering through the system's route (men, NEW_SYS_BOTH against SYS_BOTH), it reads:
     * −0.029 [−0.055, −0.003] on dev for the 2018–24 additions: slightly worse, but within the harm tolerance;
     * +0.031 [−0.035, +0.097] on the holdout for the 2025–26 additions: unresolved, P 0.84.
   * **Without the rule** (as-is, NEW_ASIS), it reads −0.021 on dev and +0.055 on the holdout, both unresolved.
   * **Under the owner's rules, the men's additions are recommended for entry by the system's route.**
   * **Women** wait for P7.
   * **The batch that really tests the rule** is P7's ITF box scores, which move women's inputs unevenly. Its plan is
     ready.

## 1. The proposed decision (for the owner's approval)

**What changes, men** (the arm SYS; parameters refitted each season, walk-forward):

| Input family | Today | Under the system |
|---|---|---|
| `points_52w` (raw serve and return points won) | Lower-level points pooled as main-tour points | Each lower-level match's rates translated by its opponent's strength gap (γ) and a level offset (δ), then weighted by w |
| One-step forms (`adjperf_tpw_2w`, `form_*`, `formdef_*`) | Each match read against the opponent's own-opponents norm, at whatever level | The opponents' norms re-referenced to the main tour, row by row. Lower-level matches weighted by w. First serves in and double faults take δ only (not opponent-dependent) |
| Joint solves (`iosO_*`, `iosD_*`, `ios_points_short`; the products follow) | One pool, no level term | A level effect estimated inside each solve, at the levels where the classifier allows one. Lower-level rows weighted by B's joint weight (w_joint, capped at 1) |
| `ratings_iid` | No level term | Lower-level rows weighted by the joint weight (w_joint). No level term |
| Elo (`elo_overall`, `elo_surf_offset`, `elo_games`) | Every result counts fully | Results weighted by w_results: about 1 at Challengers, 0.25–0.5 for men's ITF, **0 (dropped) for ITF qualifying** |
| ITF and ITFQ box scores | Enter as equivalent (2025–26 only) | Excluded until P7 lets their translation be fitted on training seasons |
| Age, workload counts, context, odds, serve speed | — | Untouched |

**The numbers** (men, season 2024; full tables in [B_relationship.md](B_relationship.md)):

| Level | w (exchange rate) | δ, the residual offset (logit) |
|---|---|---|
| Challenger | 0.63 [0.54, 0.79] | serve points −0.081, holds −0.149 |
| Challenger qualifying | 0.77 [0.50, 1.19] | serve points −0.032, unresolved |
| Tour qualifying | 1.03 [0.87, 1.22] → capped at 1 | return points −0.046, total points −0.039 |
| Slam qualifying | 0.99 [0.73, 1.30] | total points −0.044 |

* **Every weight is capped at 1.** A lower-level match never counts for more than a main-tour one.
  * The largest fitted values, up to 2.8 for men's break points forced at Challengers, came from the estimator's prior
    (red team).
  * Qualifying's 1.03 is not shown to be an artefact.
* **δ is a forecasting offset,** not a measured "conditions" effect.

**Adopting it would take:**
1. The hooks into the decided builders: `level_layer.py` and `level_layer_ios.py`, applied today by
   `system_sandbox.py`'s patch.
2. A rebuild of the current template (57 inputs, Pinnacle-first odds).
3. One confirming `compare.py` run against the frozen reference.
4. The yearly refit of the parameters (§6).

## 2. The relationship

### 2.1 Which statistics depend on the opponent (role A)

The owner's question was whether each statistic qualifies for a level offset by depending on the opponent's skill.
Measured inside the main tour, within player, against the opponent's pre-match Elo (*Observed*,
[A_classes.md](A_classes.md)):

| Class | Statistics | Treatment |
|---|---|---|
| **Depends on the opponent** (17 of 19 men's, 16 of 19 women's) | Total, serve and return points won; first- and second-serve points won; return points won against first and second serves; holds; breaks; break points saved, converted and faced per game; aces; the defence forms | Translated by γ × the opponent's strength gap (+ δ where real), weighted by w |
| **Not opponent-dependent** | First serves in (γ ≈ 0.000); double faults (−0.012, borderline) | δ only |
| **Intrinsic or workload** | Age; sets in 14 days; surface counts and layoffs | Untouched |
| **Results** | Elo inputs | Weight only |
| **Serve speed** (stage 2) | Rises slightly against stronger opponents (+0.29 km/h per 100 Elo) | No translation. Edition centring already removes the level; the same player's Challenger speed reads +1.0 [−1.0, +3.0] km/h, unresolved |

* **γ, the strength of the dependence** (men / women, logit per 100 Elo):
  * breaks −0.186 / −0.214;
  * holds −0.146 / −0.155;
  * return v first serve −0.087 / −0.099;
  * aces −0.075 / −0.054;
  * total points −0.056 / −0.069;
  * break points saved −0.055 / −0.061.
* **The Challenger "boost" is an opponent effect.** The weaker opposition explains about 100% of men's Challenger shift
  in total points won, 80–89% of qualifying's, and 77–92% of women's. What remains is a serve–return balance: serve
  statistics sit lower at Challengers and return statistics higher, and the two cancel in total points.

### 2.2 How much a lower-level match is worth (role B)

Walk-forward, predicting both players' statistics in every main-tour match of 2019–2024 from their history as of that
match (*Observed*, [B_relationship.md](B_relationship.md)). Gain over pooling as equivalent, the mean over 19
statistics:

| Formulation | Men, all | Men, low exposure | Women, all | Women, low exposure |
|---|---|---|---|---|
| Main tour only (separation) | +0.065, unresolved | **−0.355, worse** | **−0.066, worse** | **−0.310, worse** |
| Constant offset per level | +0.335 | +0.690 | +0.112 | +0.301 |
| Per-match translation (γ) + δ | +0.371 | +0.761 | +0.162 | +0.393 |
| + exchange rate w | +0.380 | +0.773 | +0.168 | +0.401 |
| + newcomer prior (the UFC idea) | +0.295 | +0.878 | +0.100 | +0.453 |
| **The method** (w, recency tuned, no prior) | **+0.409 [+0.344, +0.474]** | **+0.814 [+0.567, +1.062]** | **+0.190 [+0.152, +0.227]** | **+0.399 [+0.251, +0.548]** |

* **Translating per match beats a constant offset:** men +0.036 [+0.023, +0.049], better. A constant offset is nearly a
  function of the player's lower-level share; the per-match form is not.
* **Is "a Challenger match is worth 0.5–0.7" right?**
  * For Challenger main draws, yes: 0.63.
  * Qualifying is worth about 1 once translated.
  * A single 0.5 for every lower level is worse than 1 (men −0.013 [−0.022, −0.004]).
  * Once the translation is in place, the weight adds little (+0.009): the translation is what matters.
* **The newcomer prior, in the form tested,** helps players with little history but is worse overall (men −0.085). It
  was left out by a rule logged before the comparison. The UFC idea itself, in other forms, is untested.
* **These gains are for B's estimator,** which lets w reach 3. The system caps w at 1; B's dose curve puts the
  difference at about +0.006.
* **Results (Elo).**
  * Discounting men's ITF results to 0.25–0.5 improves Elo's own forecasts (+1.05 [+0.47, +1.63] mLL).
  * Challenger results are worth about 1.
  * ITF qualifying results are fitted at 0, so they are dropped. That matters for the new data: C0_now adds 159,191
    men's ITF-qualifying results.

### 2.3 What was rejected, and why

| Option | Evidence | Verdict |
|---|---|---|
| Equivalent pooling (today) | Statistic level: worse than the system by +0.41 (men). Model level, 2020–24: indistinguishable from the system | The statistic-level case is decisive for the route; the model is indifferent |
| Complete separation (250+ only) | Statistic level: worse for low-exposure players on both tours. Model level: SYS_w0 −0.586 [−1.055, −0.118], **worse**; SEP_ALL −0.592, P 0.02 | Rejected: the lower-level evidence carries real information |
| Constant offsets (the first attempt) | Beaten by per-match translation (+0.036, better) | Superseded |
| Newcomer prior (in the form tested) | Worse overall at the statistic level | Not used |

## 3. The proof at the model level

### 3.1 How it was tested

* **The team** worked to one specification ([SPEC.md](SPEC.md)):
  * A, the classifier;
  * B, the relationship;
  * C1 and C2, the layer in every input family;
  * D, the fits and scoring;
  * E, the red team, at three checkpoints;
  * F, data wiring for the 8 October test;
  * G, the P7 plan.
* **Everything was pre-registered and hashed before any score:**
  * the arms, the scoring and the holdout protocol (`data/studies/lower_level_evidence/system/preregistration.md`);
  * the system's internals, frozen at checkpoint 1 (addition 3);
  * the owner's decision layer (additions 4–4c);
  * the code (addition 5);
  * the checkpoint-2 conditions (addition 6).
* **The holdout lock.** The scorer refuses 2025–26 without the unlock, which holds every one of those hashes.
* **The gates passed before any fit:**
  * with every hook on at neutral settings (the identity configuration), the build reproduces all 58 inputs exactly on
    all 67,226 matches;
  * inputs that no lower-level evidence can reach do not move;
  * inputs move in the expected direction;
  * they move monotonically with the weight;
  * leak probes moved no earlier match.

  The gates caught one outside change: another session's `indoor` fill reached one sandbox. That arm was rebuilt on a
  validated code snapshot.
* **The owner's decision of 9 October** (adoption by kind of change) replaced the decision layer before any score. Who
  wrote what:
  * the owner said "I accept your adoptation logic, implement it";
  * session `tennis-predictions-cc` wrote its application to this study (02:55 UTC) and an erratum (03:54 UTC);
  * the lead adopted both in additions 4–4c, all before the first score (08:09 UTC).

  The rules:
  * a challenger must read "better" than SYS to be selected;
  * REF is preferred only on harm (worse by more than 0.10 mLL, with the whole interval below 0);
  * the recommendation stands unless the holdout shows harm.

### 3.2 Dev readings, 2020–2024 (men, both stages)

| Arm | vs REF (today) | vs SYS |
|---|---|---|
| **SYS** (the system; fitted w) | −0.008 [−0.162, +0.145], unresolved, P 0.46 | — |
| SYS_w100 (translation, no discount) | +0.034, unresolved, P 0.72 | +0.042 [−0.072, +0.156], unresolved |
| SYS_w50 | −0.126, unresolved, P 0.09 | −0.118, unresolved |
| SYS_NOCLASS (the classes ignored) | — | −0.015, unresolved |
| SYS_w0 (lower-level box scores dropped) | **−0.586 [−1.055, −0.118], worse** | **−0.578, SYS better** |
| SEP_ALL (complete separation) | −0.592 [−1.187, +0.002], unresolved, P 0.02 | **−0.584, SYS better** |
| R_S2 (REF plus the two share inputs; report-only) | +0.152, unresolved, P 0.93 | unresolved, P 0.90 |
| SYS_S2 (SYS plus the share inputs; report-only) | +0.159, unresolved, P 0.90 | unresolved, P 0.95 |
| SYS_PLACEBO (SYS's change, shuffled) | −0.161 | SYS +0.153, P 0.94 |

* **Women** (SYS applied to men only, so this is a side effect): −0.037, unresolved. Both tours: −0.022, unresolved.
* **Strata (men):**
  * where the two players' lower-level shares differ by 0.5 or more: +0.150, P 0.83;
  * falsification (both main-tour regulars): −0.041, unresolved.
* **The selection: SYS.**
  * Under the owner's rules, no challenger reads "better", and SYS shows no harm.
  * The registered rules would have picked SYS_S2 (P 0.95 of beating SYS) and kept it: its P against REF, 0.90, passes
    their step 2. SYS itself (P 0.46 against REF) would have failed that step.
  * The switch came from the owner's new threshold ("better" at 95%), set before any score of this run, though with the
    first run's R_S2 reading known. The red team's account is in [E_red_team.md](E_red_team.md).

### 3.3 The holdout, 2025–2026 (unlocked 10 Oct 08:36 UTC, read once)

Men, both stages, 4,810 matches unless stated (*Observed*, [D_verification.md](D_verification.md);
`data/studies/lower_level_evidence/system/results/holdout/`):

| Reading | mLL [95%] | Label |
|---|---|---|
| **Primary: SYS against REF, 2025–26** | **+0.011 [−0.425, +0.447]** | **unresolved, P 0.52** |
| The same, without the 909 matches that have no serve-speed memory | +0.043 | unresolved, P 0.57 |
| SYS against REF, 2020–2026 pooled | −0.003 [−0.164, +0.159] | unresolved, P 0.49 |
| Addition 2's eight checks (each season; exposure; share gap; falsification; stage 1 alone) | −0.28 to +0.14 | none worse, raw or after Holm |
| SYS_w0 (lower-level box scores dropped) against REF, pooled 2020–26 | −0.502 [−0.872, −0.131] | **worse**: negative in every season and seed; the holdout alone −0.30, unresolved, P 0.16 |
| RES_ONLY (only the Elo results weighting) against REF | +0.055 | unresolved, P 0.81 |
| SYS against RES_ONLY / SYS_NOCLASS / R_S2 | −0.045 / −0.021 / −0.010 | unresolved |
| SYS_S2 against SYS | +0.088 | unresolved |
| SYS_PLACEBO (SYS's change, shuffled) against REF, both tours | +0.215 [+0.031, +0.398] (men +0.350, P 0.97) | "better": a noise flag |

**The recommendation.**
* **Under the owner's rules (addition 4):** SYS for men. The primary shows no harm, and no Holm reading is worse.
* **Under the original rules:** none. Their selection would have been SYS_S2, and its holdout reading against REF (P
  0.64) does not meet their bar: P ≥ 0.80 and a better pooled reading.

**The caution** (the red team's CP3, [E_red_team.md](E_red_team.md)).
* **The holdout is wide.** Its standard error is 0.21 mLL, not the 0.12 expected. SYS's per-match differences are
  larger on 2025–26, and there are fewer four-week blocks, so "no harm" rules out only a harm of roughly 0.45 mLL or more.
  At that SE, a true −0.20 harm is flagged only about 13% of the time. (*Observed*.)
* **The placebo's "better" belongs to the period.** It is not seed noise (the four seeds agree), and it is not
  regularisation (the placebo does not shrink forecasts; REF's calibration slope is 0.97). By season, the men's placebo
  reads −0.42 to 0.00 on dev and +0.36, +0.34 on the holdout, and −0.012 pooled. (*Observed*.)
* **So one period's reading cannot tell SYS from a shuffle of its own changes.** The intervals are right for these
  matches, not for "any change of this size". (*Inferred*.)
* **The model-level test cannot judge this change.** The statistic-level evidence (§2) is what supports it.

### 3.3b The arms read after the main run (supplementary scorer; each first reading is the reading of record)

*Observed*: `results/supplementary/` and `status.log`, from 14:02 UTC on 10 Oct.

| Arm | Dev 2020–24 | Holdout 2025–26 |
|---|---|---|
| RES_ONLY (only the Elo results weighting) against REF, men | −0.038 [−0.112, +0.036], unresolved, P 0.15 | +0.055, unresolved, P 0.81 |
| RES_ONLY, men whose less-exposed side has fewer than 10 main-tour results | **−0.180 [−0.313, −0.046], worse** (reported, no decision) | — |
| SYS against RES_ONLY (the box-score layer beyond the Elo weighting), men | +0.030, unresolved, P 0.67 | −0.045, unresolved |
| SYS against SYS_ITFASIS (ITF box scores excluded against as-is), men | −0.000 (rounding only) | −0.028 [−0.211, +0.155], unresolved, P 0.37 |
| SYS_BOTH (the system on both tours) against REF, women | −0.048 [−0.248, +0.152], unresolved, P 0.32 | +0.039 [−0.390, +0.468], unresolved, P 0.57 |
| SYS_BOTH against REF, men | +0.012, unresolved | +0.005, unresolved |

* **Inferred: the Elo results discount is the weakest part of the system.** The discount alone (RES_ONLY) reads worse on dev for men whose opponents have little main-tour history. Their ratings rest on lower-level results, so discounting those results removes information. The full system shows no harm in that stratum on the holdout.
* **Suggestion:** test a variant with Elo results left as they are (w_results = 1) and the box-score layer unchanged, as a later candidate. Choosing it from this report-only reading would be choosing on seen data, so it is not done here.

### 3.4 What the model-level test can and cannot see

* **The resolution.** On dev the interval for SYS against REF (men) is ±0.15 mLL, wider than the power note's 0.08,
  because SYS moves forecasts about twice as much as the first attempt did. On the holdout the standard error is 0.21,
  where addition 6 expected 0.12.
* **What the harm check can catch.** It can catch only a harm of roughly 0.45 mLL or more. At an SE of 0.12 it would
  already flag a true −0.10 harm only about 11% of the time (addition 6).
* **What follows.** The model-level readings are a harm check, and the route rests on the statistic-level evidence, as
  the owner's decision prescribes for a repair. Between w = 0.5 and 1 the model cannot tell the arms apart; the exchange
  rate comes from §2.2.

## 4. The rule of 8 October: helpful or harmful?

* **What it keeps out today** (role F; [F_rule_data.md](F_rule_data.md)):
  * **The candidate Stage 0 C0_now** adds 298,008 lower-level matches. Most are ITF qualifying: men 159,191, women
    111,647. The rest: ITF 21,529; WTA 125 and women's qualifying 2,902; Challenger qualifying 2,676; and others.
  * **It completes 1,644 box scores.** Only 18,334 of the new matches touch a player with a main-tour match within a
    year.
  * **Identity checks:** 120 of 120 links right; players 237 of 248 right.
  * **The pre-2025 twin, C0_pre,** holds 205,760 new matches.
* **The natural experiment.** ITF box scores of 2025–26 entered the reference before the rule existed. Removing them
  (REF_noITF):
  * brings the products' inflated 2025–26 spread back to 2024's (input level);
  * reads ±0.002 on dev, nothing, as expected.
  * **Holdout, 2025–26:**
    * men −0.073 [−0.282, +0.136], unresolved, P 0.24: removing them leans worse;
    * women +0.166 [−0.272, +0.604], unresolved, P 0.78: removing them leans better.

    For women, ITF box scores reach 42% of the matches; for men, 7%.
* **The wired test.** The supplementary scorer, 14:02–16:00 UTC on 10 Oct; each first reading is the reading of record
  (*Observed*, [D_verification.md](D_verification.md)).

  | Comparison | Men, dev 2020–24 | Men, holdout 2025–26 | Women (information only) |
  |---|---|---|---|
  | **NEW_SYS_BOTH against SYS_BOTH**: the data through the system (decides entry) | **−0.029 [−0.055, −0.003]**, worse but not harm (inside 0.10) | **+0.031 [−0.035, +0.097]**, unresolved, P 0.84 | dev −0.010; holdout −0.086, P 0.31 |
  | NEW_ASIS against REF: the data as equivalent, no rule | −0.021 [−0.064, +0.022], P 0.16 | +0.055 [−0.029, +0.139], P 0.91 | dev +0.019; holdout −0.029 |
  | NEW_ASIS_PRE against REF: the 2018–24 backfill only | −0.021 (same inputs through 2024) | +0.049, P 0.89 | holdout +0.006 |
  | NEW_ASIS against NEW_ASIS_PRE: the 2025–26 additions | — | +0.006, P 0.64 | −0.035 |
  | SYS_BOTH against SYS_BOTH_ITFASIS: ITF box scores excluded against as-is, inside the system | women +0.017, P 0.85 | men −0.037; women −0.021 | — |

  * The opponent strength of NEW_SYS_BOTH sits on the reference's Elo scale: the new data shifts that scale by about
    +80 Elo (addition 7, option c).
  * The option-(a) build was never scored.
* **The verdicts** (the owner's rules, addition 4):
  * **Men's additions of 2018–24: recommended for entry by the system's route.** The dev reading is resolved worse,
    but by 0.029, well inside the 0.10 tolerance.
  * **Men's additions of 2025–26: recommended.** The holdout reading is unresolved and leans better.
  * **Women:** decided at P7.
* **The reading so far** (*Inferred*):
  * The rule's premise holds at the input level. Data arriving unevenly moves the inputs in some seasons only (finding
    #6).
  * The system is the route that lets such data in safely: translated, weighted, and held out until its translation
    can be fitted.
  * Under the owner's decision of 9 October, new lower-level data enters by that route unless its harm check fails.
  * **For this batch, the rule protected against nothing measurable.** The data is mostly ITF-qualifying results, which
    rarely touch a main-tour player. Let in as-is or through the system, it reads within ±0.06 of today's model.
  * **The one resolved reading is a small dev worsening (−0.029) through the system.** Its likely sources are the new
    results in Elo and the workload counts. The workload counts take every match untouched ("a set is a set"), so 159k
    ITF-qualifying matches enter them. That is worth watching when larger batches land. (*Inferred*.)
  * **Suggestion for the rule.** Replace the blanket hold with the owner's route: new lower-level data enters through
    the system's translation and weights unless its harm check fails, with an expected-unevenness file written first.
    P7 is the real test of this route.
  * **Caution.** The harm check at this resolution can see only large harms (§3.4).

## 5. Women and ITF: the P7 plan

* **The data.** ITF box scores land in two parts: 2025–26 around 17–18 Oct, and 2018–24 around 22 Oct – 2 Nov.
  [P7_plan.md](P7_plan.md) is the executable plan:
  * the trigger;
  * the wiring (C0_P7 and a control);
  * B's refit with ITF parameters, fitted from season 2020;
  * four arms (as-is, excluded, translated, control);
  * the gates;
  * the readings on 2020–2026, labelled non-clean;
  * a forward test from the decision date;
  * the decision rule under the owner's 9 October decision.
* **Its forward test is a harm guard only.** One season resolves only effects of about 0.3 mLL.
* **The code changes it needs** (§10 of the plan) wait until this run is closed.

## 6. Keeping it current

* **Each season,** refit B's parameters walk-forward (`relationship.py`; the frozen method F4, both tours, the cap at 1).
  Re-check the classes with A's frozen thresholds.
* **When new lower-level data lands,** wire it into a candidate Stage 0 with `candidate_stage0.py`. Write the expected
  unevenness before any arm. Build the system's arm on it, and harm-check it against the system on the old data (the
  owner's rule for an expansion).
* **The first run's re-review tool,** `src/eda/lower_level_evidence/refresh.py`, still snapshots the dose and the
  translation for each new Stage 0.

## 7. Decisions for the owner

1. **Adopt the system for men?** The recommendation above, on the conditions in §1.
2. **The rule of 8 October:** keep it as it is, or change it to "new lower-level data enters by the system's route
   unless its harm check fails". See §4.
   * For this batch, the men's additions are recommended for entry. They would enter through a candidate Stage 0
     rebuilt with `candidate_stage0.py`, not as-is.
   * The P7 batch is decided by its own test.
3. **The harm tolerance:** 0.10 mLL. It was chosen by Claude in the form of the Roland Garros rule; the owner may set
   another.
4. **The share inputs:** to the feature pool as a lead (+0.15 for men, −0.11 for women, on their discovery seasons).
5. **Women:** decided at P7.
6. **Cleanup.** The build sandboxes `C:/Users/zerom/tnr_sys1`–`tnr_sys5`, `tnr_sys_ios` and the first run's `tnr_lle`,
   about 21 GB each.

## What it does not show

* **A model-level gain.** The system's value at the model level is unresolved on dev, and the comparison cannot see
  effects below about 0.15 mLL.
* **Clean seasons for future tests.** 2020–2024 has been read by many studies, and this run spent the 2025–26 holdout.
  No untouched seasons remain until the forward period.
* **ITF translation.** It is untested: excluded until P7.
* **Women.** B fitted women's parameters. SYS_BOTH was read after the main run, by the supplementary scorer: women's
  dev −0.048, holdout +0.039, both unresolved (§3.3b). Their decision waits for P7.
* **Which part of the new data moved the dev reading.** NEW_SYS_BOTH's small dev worsening (−0.029) is not decomposed
  between the new results in Elo, the workload counts and the box completions.
* **Other odds inputs.** Everything was measured on the frozen reference: 58 inputs, books'-average odds. The current
  template (57 inputs, Pinnacle-first) needs one confirming rebuild.

## Files

| What | Where |
|---|---|
| Specification, pre-registration, additions, unlock | `SPEC.md`; `data/studies/lower_level_evidence/system/preregistration*.md`, `holdout_unlock.json` |
| Role reports | [A_classes.md](A_classes.md), [B_relationship.md](B_relationship.md), [C_layer.md](C_layer.md), [C_layer_ios.md](C_layer_ios.md), [D_verification.md](D_verification.md), [E_red_team.md](E_red_team.md), [F_rule_data.md](F_rule_data.md), [P7_plan.md](P7_plan.md) |
| Code | `src/eda/lower_level_evidence/`: `classify.py`, `relationship.py`, `level_layer.py`, `level_layer_ios.py`, `system_sandbox.py`, `system_arms.py`, `system_gates.py`, `system_fits.py`, `system_pairs.py`, `system_decide.py`, `system_supplementary.py`, `candidate_stage0.py` |
| Evidence | `data/studies/lower_level_evidence/system/`: `classes/`, `relationship/`, `arms/`, `ios_layer/`, `stage0/`, `results/`, `audit/` |
| The first run (exploration) | [../README.md](../README.md) |

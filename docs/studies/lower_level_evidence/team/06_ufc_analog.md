# How the UFC pipeline uses a fighter's record outside the UFC, and what tennis should take from it

9 October 2026 · Specialist 06 (UFC analog) of the lower-level-evidence team · Research evidence, not a decision.

**Note added by the lead (9 Oct 2026).** This report was written before the owner's [decision of 9 Oct](../../../decisions/2026-10-09-adoption-framework.md) that no comparison is called a "tie". Read "tie" here as "unresolved": the 95% interval spans 0.

**The question this report answers.** The owner's UFC pipeline uses a fighter's record outside the UFC to inform his starting point. How exactly? What has worked there, what has failed, and why? What should the tennis remedy for Challenger / ITF data copy, adapt or avoid?

**Ground rules.**
* The UFC repository and its memory folder were read only. No UFC code was run, nothing there was changed, and no Git command was used.
* Labels: **Observed** = read in a file (path:line given); **Inferred** = my reasoning; **Suggestion** = a proposal for the owner.
* Memory notes are point-in-time. Every load-bearing memory claim below was checked against the UFC code or the study report it summarises; the report is cited, not the memory.
* Units: **mLL** = thousandths of log loss per fight (UFC) or per match (tennis). The UFC reports use opposite sign conventions in different studies; every number here is translated into words ("better" = lower log loss for the named version). A range that spans 0 is called a **tie**.
* **Support** (UFC) = the share of event-date bootstrap resamples in which the candidate is better ([UFC AGENTS.md:45-50](#sources)). 70% is the UFC house bar for a provisional ship (AGENTS.md:28-38).

## Vocabulary (UFC terms used below)

| Term | Plain meaning |
|---|---|
| **MESR** | "Market-embedded skill rating": one number per fighter, solved by ridge least squares from the de-vigged **closing lines of his past fights** (never their results). The model reads A's minus B's. |
| **BT** | A Bradley–Terry rating solved from fight **results**. |
| **Informed prior** | A fighter's starting value in the MESR and BT solvers, predicted from his record before the UFC. |
| **S(x), SoS** | S(x) is a logistic "skill score" fitted on a list of fighter inputs (which include MESR and BT before the fight). SoS (strength of schedule) is the recency-weighted average of a fighter's past **opponents'** S, pulled toward a below-average "phantom opponent" when the schedule is thin. |
| **adjperf / adjdef** | Opponent-adjusted averages of one statistic: how far a fighter out-does what his opponents usually allow (adjperf), or holds opponents below their usual output (adjdef). The UFC cousin of tennis IOS and adjusted form. |
| **K** | The pseudo-count in a Bayesian average, (sum of observations + K·population mean) / (count + K). Bigger K = more pull toward the population mean. |
| **min_tf** | The smaller of the two fighters' prior UFC fight counts. "Rookie fight" = min_tf ≤ 3. |
| **Ramp gate** | A multiplier on one model column's A − B difference: m_low when min_tf ≤ 2, rising linearly to 1 at min_tf ≥ 4. |
| **Channel** | One route by which a shared input reaches the model. |
| **Placebo twin** | A change of the same size and shape as the candidate's, with its mechanism destroyed (shuffled or random noise). |
| **TabICL** | The in-context tabular learner the UFC studies use; a near-twin of TabPFN. |
| **τ (transfer ratio)** | How much one non-UFC result is worth, relative to one UFC result, for predicting UFC fights. |

## The answer in short

* **Observed. UFC uses the outside record in three places, all thin.** (1) An *informed prior* for two ratings (MESR and BT): a ridge from nine counts of the pre-UFC record, whose pull fades to zero over six effective UFC fights. (2) A *career win rate* that pools every organisation at equal weight, damped by a *ramp gate* when a pair has only 2–3 UFC fights. (3) An *any-organisation activity clock* in a post-model ageing shift. The outside data are **results only**: there are no outside fight statistics.
* **Observed. The informed prior is worth nothing measurable in the model, and its direct channel reads slightly harmful.** It carries zero information beyond the debut betting line. On the primary 2022+ window, every change that added information or spread to the prior's direct (MESR) channel made the model worse, including a richer, genuinely better prior; removing the prior from that channel read 0.16 mLL better. The same richer prior fed only to the strength-of-schedule channel read 0.10 mLL better (support 91%) — at the noise wall, parked, not shipped.
* **Observed. The one shipped "informative, not equivalent" device is the ramp gate**, an in-place damping of the pooled win rate's difference on rookie fights (first on the win-rate ÷ age ratio, since 15 Sep on the plain win rate). Measured alone in July it read 0.30 mLL better (15 of 15 seeds). It has since faded: on 2019–21 it is 0.69 mLL better (98%), on 2022+ a tie. The reason is the UFC's sharpest finding: **the value of an outside result changed between eras** (τ ≈ 0.02 in 2013–21, ≈ 0.71 in 2022+). A fixed downward "padded record" correction lost on every seed once the regime changed.
* **Observed. What died:** adding experience or uncertainty columns, re-scaling the prior to its "calibrated" spread, down-weighting thin opponents inside the schedule average, experience-conditioned population defaults, a rookie calibration multiplier.
* **Inferred. Tennis is structurally different in ways that matter.** Players move between levels every few weeks; the cross-level opponent graph is dense; Challengers have full box scores; lower levels are about ten times the main tour's volume; the tennis model takes the match's closing price as an input; and the tennis market **under-rates** players arriving from lower levels, where the UFC market had priced the outside record. A pre-debut prior that fades does not fit a player who keeps returning to Challengers.
* **Suggestion. Copy the method; adapt the mechanism.** Copy: channel-by-channel tests with channel-matched placebo twins, in-place changes instead of added columns, splits by main-tour exposure, pre-registration, cheap prescreens. Adapt: replace "a prior that fades" with **a level offset plus a transfer weight τ < 1 inside the joint solves, fitted walk-forward per statistic**, so that main-tour matches take over naturally as they accumulate and top players (no lower-level matches) are untouched. Avoid: fixed discounts fitted on old seasons, re-scaling, added "exposure" columns, and lower-level training rows without a price.

---

## 1. How the UFC pipeline uses the outside record

### 1.1 The data

* **Observed.** The outside record is ESPN's fight history: 52,511 rows for 2,703 fighters, of which 34,919 are non-UFC rows across 3,594 organisations; 17,592 are UFC rows. A UFC debutant has a median of 10 pre-UFC fights (10th–90th percentile 4–21) (NRP:72-79).
* **Observed. Results only.** Each outside row carries result, method, date, organisation and an organisation size flag (big / small). No judges' margins and no fight statistics exist outside the UFC (NRP:106-108). The experience study named "scrape non-UFC fight statistics so rookie averages start informed" as the root-cause fix; it was never done (EUG:272-276).
* **Observed. The UFC's own feeder show with betting lines (Dana White's Contender Series, DWCS) is excluded** from the UFC history by project convention (BACKGROUND.md:25; create_training_prediction_data_v3.py:425-426, comment "It seems DWCS events lowers the prediction scores"; closing-odds spec 2026-04-26:203 "Excluded per project convention"). I found no study of including it (every `DWCS` mention under `UFC/docs` is a passing note of the exclusion).

### 1.2 The informed prior (the ratings channel)

* **Observed. What it predicts.** For each fighter, a starting value for MESR and for BT (IPA:27-29).
* **Observed. The model.** A ridge regression (α 1.0) on nine standardised counts of the pre-UFC record: wins and losses in big and in small organisations, win share, current streak, win and loss finish rates, total pre-UFC fights (informed_priors.py:26-31, 34-106).
* **Observed. The target.** The fighter's own rating at his 4th UFC fight (or his last, if fewer), solved *without* any informed prior, so the prior never contaminates its own target (informed_priors.py:300-337; IPA:27).
* **Observed. Shrinkage and centring.** informed = flat anchor + 0.9 × (ridge prediction − the training set's mean prediction) (informed_priors.py:236-241, 493-495). The anchors are −0.244 (MESR) and −0.35 (BT) (informed_priors.py:566, 587). Subtracting the training mean removes survivorship: fighters who reach a 4th fight are above average (informed_priors.py:178-183).
* **Observed. Time validity.** Five expanding-window refits a year from 2012; each window holds debuts from [cutoff − 6 years, clamped to 2006–2009] to the cutoff, with at least 20 fighters; each fighter takes the model current at his debut. Pre-2012 debutants get the flat anchor (informed_priors.py:265-297, 340-437, 440-507).
* **Observed. How its weight falls.** In the rating solve, each fighter's ridge penalty pulls him toward m = prior × max(0, 1 − n_eff / 6), where n_eff is his count of UFC fights, each discounted by age on a clock four times slower than the rating's own half-life (elo_utils.py:2604, 2617, 2683-2692, 2722). So the pull fades linearly to zero after six effective fights, and returns if his fights go stale. The penalty strength λ stays constant (0.75 for the men's MESR; MEM/project_mesr_hp_grid_study.md:13). At a true debut the rating *is* the prior (elo_utils.py:2787-2794).
* **Observed. Who consumes it — two channels.**
  * **(a) Direct:** `MESR_difference`, a model column (pre_process_v3_model_from_base.py:526).
  * **(b) Strength of schedule:** `MESR_prior` and `BT_Rating_prior` are inputs of S(x) (pre_process_v3_model_from_base.py:1352-1356). A fighter's SoS averages his opponents' S, shrunk toward a phantom at −0.5 with weight K 2 (fight_data_utils_production.py:7740-7747; MEM/project_v3_sos_production_state.md:13). So the prior decides how much credit *other* fighters earn for having fought a near-debutant. `SoS_difference` is a model column (pre_process_v3_model_from_base.py:528).
  * The v4 model uses the same frozen dictionary (features/v4/history.py:288-295).
* **Observed. Its dose is tiny where the model acts.** At 2–3 prior UFC fights, the whole informed prior moves `MESR_prior` by 0.03 on a spread of 0.76 (4%), and SoS by 0.004 on 0.26 (NRP:341-351, 376-377).
* **Observed. The thinnest fights are never predicted.** Each fighter needs at least two prior UFC fights in training (UFC CLAUDE.md:293-294); prediction needs A ≥ 2, B ≥ 2 and A + B ≥ 5 (dial audit:186). Debuts and second fights are outside the model.
* **Observed. One closing line outweighs the whole record.** The spread of `MESR_prior` jumps from 0.153 before the debut to 0.690 after it: one market line takes a debutant to the full spread of established fighters (IPA:65).

### 1.3 The career win rate (the one "equivalent" input) and the ramp gate

* **Observed. Equal pooling.** `career_winrate` counts every pre-bout fight on ESPN — amateur, other organisations and UFC — at equal weight; draws excluded (fight_data_utils_production.py:2125-2131). With no usable ESPN record, a population pseudo-record (the mean outside record of earlier UFC entrants, ≈ 11.0 wins and 2.95 losses, 78.9%) plus the fighter's known UFC record (fight_data_utils_production.py:2133-2137, 2200-2213; espn_coverage_prior_repair.md:33-49).
* **Observed. The model reads its A − B difference** (`career_winrate_difference`, pre_process_v3_model_from_base.py:602), **damped by the ramp gate** (experience_gate.py:73-83):
  * multiplier = m_low + clip((min_tf − 2) / 2, 0, 1) × (1 − m_low) (experience_gate.py:9-13, 177-180);
  * m_low = the column's logistic slope on rookie fights divided by its slope on veteran fights, fitted on the whole training frame at build time, clipped to [0.3, 1], stored, and **reused, never refitted, at prediction** (experience_gate.py:146-171, 203-229);
  * m_low was 0.7276 at the 15 Sep ship (experience_gate.py:24-25): a 2-fight pair counts ×0.73, a 3-fight pair ×0.86, 4+ ×1.
* **Observed. What the gate does and does not do.** It changes the *slope* (how much a record gap counts on a thin pair). It does not change the *level* (whether a padded record is too high) (WEP:19, 143).

### 1.4 Activity elsewhere: an any-organisation clock, post-model only

* **Observed. In the model, counting outside fights in the layoff column was worse in every form, on 15 of 15 seeds** (LEA:5, 14-17). The long tail of the UFC-only gap already marked "cut, fought elsewhere, came back", and the model had learned to read it (LEA:25-37).
* **Observed. As a post-model shift it shipped** (29 Sep, a bounded experiment): logit −0.10 × (unseen-ageing years of A − of B), with the layoff measured from the last fight in **any** organisation (MEM/project_unseen_aging_shift_shipped.md:11-16). The trigger: of 73 "stale" veterans, the 9 who had been fighting elsewhere won 67% against a model 30% (LAO:23); every correction on the UFC-only clock hurt (LAO:26).

### 1.5 Experience shrinkage of UFC statistics (the K overrides)

* **Observed.** UFC fight statistics are Bayesian averages shrunk toward the weight class's population mean with a per-class K of 1, 2 or 4 (EUG:142-146, 430-433).
* **Observed.** One override shipped: adjdef head-strike accuracy, K 1 → 4 (MEM/project_experience_uncertainty_gating_study.md:13). The study measured K 8 as the optimum and shipped a conservative half-step (EUG:439-456).

---

## 2. What worked, what failed, and why

All UFC results are men's v3, TabICL, paired on identical fights, 15 seeds, 2022+ primary unless noted.

| Idea | What was done | Result | Why (as the study reads it) |
|---|---|---|---|
| The informed prior itself | Audit of the shipped prior | **Zero information beyond the debut line** (log-likelihood gain exactly 0.00) (IPA:15, 55). Refitting it per era changed nothing (MEM/project_v3_walkforward_retune_study.md:21) | The debut line already knows the record, and spreads debutants 3.4× wider (IPA:55) |
| Re-scale the prior to its "calibrated" spread (×2.1) | Paired swap, 3 seeds | **Worse in 6 of 6 reads**, 0.17–0.30 mLL worse pooled, 0.5–0.9 worse on the fights it touched (IPA:17, 87-93) | Wider spread = variance correlated with the price; the solver's dials were tuned *with* this prior, so "fixing" one re-litigates both (IPA:93) |
| Elite imports | Audit | Count features cannot see "was a champion elsewhere": Melendez's prior ≈ flat, the market said far above (IPA:64) | A ceiling of count features, not of the machinery |
| **A richer prior: a BT rating on the outside-fight graph** | 38 arms incl. 24 placebo twins, pre-registered (NRP) | Improves the prior's own forecast (r² 0.114 → 0.131 on debuts ≤ 2021; 0.143 → 0.155 on 2022+) and adds a little debut information beyond the line (~0.5 mLL per debut, not significant) (NRP:277-286, 309-318) | The first pre-UFC feature ever to do either |
| … through the **MESR channel only** | `cand1_mesr` | **0.06 mLL worse** (support 11%); on thin fights 0.40 worse, interval excluding 0; the fuller version 0.12 worse, thin 0.51 worse. The older 2019–21 window read the other way (0.10 and 0.05 better), the ×2.1 spread control did not (0.24 worse on 2022+, 0.11 worse on 2019–21) (NRP:404, 407, 410, 443, 456-461) | "The market has already priced the record": extra debut spread is price-correlated noise (NRP:458-461) |
| … through the **SoS channel only** | `cand1_sos` | **0.10 mLL better** (91%, 15/15 seeds), 0.14 better on 2019–21 (92%); above all eight SoS-only twins (max 0.05 better) but **not** above the pre-registered both-channel twin max (0.106 better); thin fights 0.06 better (63%), veterans 0.12 better (95%) = spillover, not the mechanism (NRP:406, 419-427, 441, 451-455, 476-485) | Real but at the noise wall; parked with a fresh-season trigger (NTB:239-244) |
| Remove the shipped prior from the MESR channel | `flat_mesr` | **0.16 mLL better** (92%, 15/15, better in all 8 years); on a size-matched null ≈ 1.5 sd, "suggestive" (NRP:401, 462-467, 492-493) | The production prior's direct channel reads mildly harmful; removal study recommended, not done |
| Companion graph features | Opponent mean rating, wins/losses vs ex-UFC opponents, activity, organisation prominence | Dead: each lowers the prior's own forecast or adds nothing (NRP:289-292, 531-534) | The outside graph is 70% one-fight opponents (NRP:237-238) |
| **Lever 1: score a near-debut opponent from his own debut line** | In S(x), replace `MESR_prior` by the post-fight market rating for opponents with ≤ 1 UFC fight | **0.62 mLL better on 2022+, 1.05 worse on 2019–21** — a regime bet, parked (NTB:204, 207) | The market line knows more than any record; the gain lives on thin schedules |
| Down-weight thin opponents inside the SoS average | Every dose | Dead at every dose (NRP:64) | "Shrink the uncertain score, not its vote" (MEM/project_v3_sos_production_state.md:26) |
| Damp SoS on rookie fights | ×0.30 / muted | **0.72 / 2.55 mLL worse** (EUG:343) | SoS is load-bearing even for rookies |
| **ADD an experience / uncertainty column** | Six forms (experience context, gate × rating products, effective-count difference, fight-length difference) | **None better**; the gate × BT product was worse than all 8 of its noise copies (EUG:198-206) | The averages are already experience-shrunk; the whole rookie problem is worth ≈ 1 mLL even with hindsight (EUG:224-233) |
| **REPLACE in place: the ramp gate** | Damp the win-rate ÷ age column's difference on rookie fights (July; moved to the plain win rate on 15 Sep) | **0.30 mLL better**, 15/15 (step form 0.19); with adjdef K 8, **0.63 better**, every seed at least 0.39 better (EUG:417-419, 467) | Partial damping beats both full strength and removal (rookie fights: 0 / 0.63 better / 1.07 worse) (EUG:359-362) |
| The gate's value, re-measured 15 Sep | Gated vs ungated plain win rate | **2019–21: 0.69 mLL better** [+0.05, +1.34], 98%; **2022+: tie**, 0.08 worse [−0.56, +0.39], 38% (WAS:621-622) | Consistent with the transfer ratio's rise (next row) |
| **Downward "padded record" prior (a level fix)** | Pull rookies' win rates down 6–9 points, fading 2 → 4 fights | **Worse on every seed** at every dose: 0.23–0.52 mLL worse; replacing the gate with it was worst (WEP:94-101) | The 2013–21 bias was real (rookie side over-rated by ≈ 6 win-rate points after the gate, growing with how padded the record was) and is **zero on 2022+**; τ̂ rose from 0.02 to 0.71 (WEP:55-74, 78-86) |
| Rookie calibration multiplier | Walk-forward trust multiplier on rookie fights | Fits ≈ 1.00 in every era; with hindsight worth 0.009 mLL (WEP:117) | The model was already calibrated on rookies |
| K per statistic | Sweep K, split rookies / veterans | adjdef head K 8: 0.50 better (rookies 1.44, veterans 0.09 better); top-position aggression K 12: rookies 0.38 better (15/15) but veterans 0.20 worse (0/15), a wash; two others dead or a hair (EUG:439-456, 524-547) | K shrinks everyone; it helps only where veterans' signal survives shrinkage. **Appetite is per (statistic, channel)** (EUG:549-558) |
| Experience-conditioned population defaults (v4) | Newer fighters borrow from newer fighters | **1.70 mLL worse** on the leg (support 2%); copies with the experience counts shuffled cost about the same (EPV:11-12) | The experience alignment itself carried nothing; the change was a same-size disturbance |
| A thin population borrowing another as context | Women's model trained with men's fights as rows | Women-only context **24–25 mLL worse**; duplicating women's rows flat (WCS:47, 50, 88-89) | Pooling is load-bearing — but the men's rows carry every input, prices included |

**Observed. The cross-cutting laws the UFC studies wrote down** (MEM/project_study_method_lessons.md, verified against the reports above):
* **Channel decomposition is mandatory for a shared input.** The informed prior's two channels moved in opposite directions under every change; a pooled "both channels" arm averaged a gain and a harm into nothing, and a both-channel placebo twin over-priced the SoS-only null by 2× (max 0.106 vs 0.050 better) (NRP:471-484; MEM/project_study_method_lessons.md:30).
* **Information the market already prices is anti-signal when copied into the model** (MEM/project_study_method_lessons.md:45). Check "beyond the line" first.
* **Prior quality is not model value.** A 15% better prior did nothing in the model (NRP); priors that forecast next-fight statistics 6–11 points better did not help the model either (EPV:13-17).
* **Imposed reshapes bet on a past regime** (MEM/project_study_method_lessons.md:41): the padded-record correction is the clearest case.
* **A population-level shift leaks into every A − B column** by (share of prior in B − share in A) × the shift, so a "better prior" can win as an experience-gap signal in disguise; run an explicit exposure-gap control (MEM/project_study_method_lessons.md:43, item 3).
* **Training-context spillover:** changing many training rows moves untouched test rows; read touched and untouched fights separately (MEM/project_study_method_lessons.md:40).
* **"15 of 15 seeds" is not evidence.** A mechanism-free twin read 0.11 mLL better on every seed (NRP:419-423).

---

## 3. The method that produced those answers (worth copying)

* **Observed. Pre-registration.** The design, the candidate lists and a four-part bar were written before any solve; additions were dated and disclosed (NRP:9-13, 197-208, 548-566). The bar: better with ≥ 70% support; above the largest placebo twin; the gain where the mechanism acts (thin / touched fights); the older window not materially worse (NRP:199-206).
* **Observed. A replica baseline.** Every arm is paired against the production recipe re-run through the study's own pipeline (`prodrep`), so a candidate differs from its baseline in one thing only (NRP:166, 258-263).
* **Observed. Cheap prescreens first, on the CPU** (NRP §3; WEP:147, 157): the prior's own out-of-sample quality; a "beyond the line" logistic; channel size in rating space; the τ̂ transfer regression; the bias split by how padded the record is. They decided the record-prior study before any model fit (WEP:145).
* **Observed. Placebo twins built two ways:** the candidate's per-fighter increments shuffled within debut year (era profile kept, alignment destroyed), and Gaussian noise of the same spread (lib_nrp.py:595-614); then the same twins per channel (lib_nrp.py:563-571).
* **Observed. Splits:** thin segment (min_tf ≤ 3), touched vs untouched, per year, top 5% of fights removed (NRP:437-493).
* **Observed. Judging:** the pooled paired difference against matched nulls and against the feature's own value; never era spread, seed counts or cells under ~300 (AGENTS.md:52-105; MEM/feedback_evidence_judging_rules.md:15-18). Market claims only from rolling 12–24-month windows, never long pools (MEM/feedback_market_claims_recency_scoped.md:10-19).

---

## 4. Mapping to tennis

### 4.1 What corresponds

| UFC | Tennis | Label |
|---|---|---|
| A rookie (2–3 UFC fights) | A player with little main-tour history; typically ranked about 100–200 | Inferred |
| Regional promotions, ESPN record | Challengers, ITF, qualifying | Inferred |
| The informed prior, fading over 6 UFC fights | The weight of lower-level evidence in a player's main-tour estimate, falling as main-tour matches accumulate | Inferred |
| The direct channel (`MESR_difference`) | Ratings the model reads directly: offset Elo, games-weighted Elo, serve / return ratings | Inferred |
| The SoS channel (how opponents are scored) | The joint solves whose opponent adjustment depends on how lower-level opponents are rated: the surface IOS profile, adjusted two-week form, IOS points | Inferred |
| The pooled career win rate, gated | `points_52w` (raw rates pooled over all levels; EL:121); the history-share measure `low_share_diff` (EL:295-306) | Inferred |
| The any-organisation activity clock | `sets_14d` and the surface layoffs, which count every level | Inferred |
| Prior-pool contamination (another population's rows entering a prior; a prior estimated on a different population than the one it shrinks) | Input-audit finding #6: ITF box scores, 45–80% of all box-score rows in 2025–26, shift the IOS level and widen the 7 product inputs by 25–56% (input_data_audit/README.md:38, 221, 260-270) | Observed (tennis) / Inferred (link) |
| A frozen interaction constant de-centred by a level shift (−1.9 to −2.0 mLL on the v4 leg unless re-centred; EPV:63) | The IOS products `prod_* = O_B·D_A − O_A·D_B` change scale when every rating shifts (input_data_audit/README.md:261) | Observed (both) / Inferred (link) |

### 4.2 What differs, and why it matters

| | UFC | Tennis | Consequence (Inferred) |
|---|---|---|---|
| Movement between levels | One way, before the debut (cut-and-return veterans aside) | Both ways, every few weeks: after a Challenger, men ranked 51–100 next play the main tour 54% of the time; after a main-tour event, men ranked 101–150 go back to a Challenger 37% (EL:78-86) | Lower-level evidence keeps arriving throughout a career. A pre-debut prior that fades over N matches does not fit. |
| The opponent graph | 70% of outside opponents fight once; a 2023–26 debutant's pre-UFC opponents include a future-UFC fighter on 7.6% of edges (NRP:237-251) | 92% of men's 250 matches have a player who played a Challenger the year before (EL:87) | A joint solve can actually identify the level gap in tennis. In UFC the outside "graph rating" was mostly a win-rate cousin (NRP:268-269). |
| Data below the top level | Results only | Men's Challengers 100% box scores, WTA 125 74–97%, ITF box scores from 2025, Challenger point-by-point 41% (EL:47-52, 127-130) | Tennis can transfer statistic by statistic. UFC never could, so it has **no evidence** on per-statistic transfer. |
| Volume | Outside rows ≈ 2× UFC rows (NRP:73-74) | ITF main draws alone ≈ 7× the model's 55,144 rows (EL:30-52) | Lower levels can dominate pooled population constants (finding #6). |
| The market | Priced the outside record: zero information beyond the debut line (IPA:15) | **Under-rates** players arriving from lower levels: β +0.13 [+0.07, +0.19] on the close, replicated on 2013–19, growing 0.06 → 0.13 → 0.18 by era; the model takes up about a third (EL:279-292) | In tennis a direct channel is not anti-signal by construction. But so far the measure ties as an input (+0.06 [−0.10, +0.23]) and as a stage-2 term (+0.08 [−0.35, +0.50]) (EL:297-305). |
| The current price in the model | No: MESR is built from past lines; the current opening line acts only through a post-model correction (pre_process_v3_model_from_base.py:515-619, no odds column; MEM/project_mesr_open_correction_shipped.md:15) | Yes: the closing log-odds is an input | Anything the close prices is already in the tennis model; the room is what the close misses. |
| Who is predicted | Fighters with ≥ 2 prior UFC fights; A + B ≥ 5 | Every main-tour match with a price, first main-tour matches included | In tennis, lower-level evidence carries a large dose exactly where it acts. The UFC prior's dose was 4% where it acted (NRP:341-351). The UFC lore says so itself: a tennis-style gain that lives on newcomers "cannot reach a frame that excludes debuts" (MEM/project_study_method_lessons.md:49, item e). |
| Regime change | τ̂ 0.02 → 0.71 (WEP:55, 84) | The market's β grew across eras (EL:288) | A fixed discount is a bet on the seasons it was fitted on. |
| Top players | Elite imports invisible to count features (IPA:64) | Top players play no lower-level matches | Any remedy must reduce to "main tour only" for them by construction. |
| Integrity and noise below | Not studied | Challenger alerts concentrate at Challenger 50 and 75; retirements 3.59% at Futures vs 1.61% on the tour (EL:270, 318-319, 326) | Supports τ < 1 for some levels on top of any level shift. |

### 4.3 The owner's UFC description, checked

* **Observed.** "Instead of treating a new fighter as an average new fighter, I treat them as an average new fighter skewed towards their prior to UFC performances" is exactly the informed prior: flat anchor + 0.9 × (centred ridge prediction from the outside record) (informed_priors.py:236-241).
* **Observed. Two qualifications the UFC evidence adds.** (1) In the model, that skew has measured zero value, and through the direct channel slightly negative value (IPA:15; NRP:462-467). (2) The one place the UFC pools outside results *at equal weight* is the career win rate, and its correction (the gate) earned its keep only while outside records were inflated (WAS:621-622).
* **Inferred.** So the UFC pipeline does not yet hold a proven recipe for "informative, not equivalent". It holds a proven *testing method*, a proven *shape* for the fix (in place, channel by channel, weight fitted walk-forward), and a set of documented failures.

---

## 5. Lessons for the tennis design and its tests

### 5.1 Copy

1. **Suggestion. Decompose by channel and give each channel its own placebo twins.** The tennis channels that read lower-level matches, per the shared brief and EL:43, 121, 136:
   * ratings: offset Elo, games-weighted Elo, serve / return ratings;
   * per-statistic profiles: the surface IOS (14 ratings + 7 products), two-week form (12) and defence form (4), adjusted points won over two weeks, IOS points;
   * raw rates: `points_52w`;
   * workload: `sets_14d`, surface layoffs.

   One arm per channel, plus an all-channels arm. Twins of the same size per channel. The UFC prior's two channels moved in opposite directions; a pooled arm hid both (NRP:471-484).
2. **Suggestion. Measure the transfer before building anything.** The UFC's parked "Mechanism A" is the owner's idea in its simplest general form: record = (main wins + τ × lower wins + K0 × p0) / (main matches + τ × lower matches + K0), with τ fitted walk-forward rather than assumed (WEP:147; NTB:138). In tennis, fit τ (and a level shift) **per statistic and per level** on players who play both levels in the same season, as a CPU prescreen (the UFC's `08_memo_diagnostics.py` pattern, WEP:157). If τ̂ ≈ 1 once the level shift is removed, equal weighting is already right for that statistic and the remedy is a no-op there.
3. **Suggestion. Change values in place; do not add "exposure" or "uncertainty" columns.** The UFC ADD family died (EUG:198-206); the in-place ramp shipped (EUG:417-419). Tennis's `low_share_diff` is already in the feature universe (U-330) and ties as an input (EL:297-306).
4. **Suggestion. Split every read by main-tour exposure** (for example, the share of last year's matches below the main tour, or main-tour matches in the last 52 weeks) and require the gain to land on the players the change touches; read touched and untouched matches separately for spillover (NRP:451-455).
5. **Suggestion. Run an explicit exposure-gap control.** Down-weighting lower-level evidence moves each player toward the population in proportion to his lower-level share, so the A − B inputs change by about (share B − share A) × the shift (MEM/project_study_method_lessons.md:43, item 3). In tennis that difference is exactly what the market under-rates (EL:279-292). A down-weighting arm can therefore win as `low_share_diff` in disguise. The control: the same arm against the reference **plus** `low_share_diff` (experiment C1's column).
6. **Suggestion. Pre-register, and use the tennis candidate machinery as the UFC's "replica baseline".** A `run_chain.py --setup --candidate` build compared with `compare.py` against the frozen reference, both stages, 2020–2024, never 2025–26 (docs/decisions/2026-10-08-current-best-model.md:13-30, 85). Read the input check first: an "uneven" flag is finding #6's warning sign.
7. **Suggestion. Keep population constants on the main-tour population.** Centre the IOS ratings on a fixed main-tour reference group before forming products (input_data_audit/README.md:341), the tennis form of the UFC's re-centring of frozen interaction constants (EPV:63).

### 5.2 Adapt

1. **Suggestion. Replace "a prior that fades" with a level offset and a transfer weight inside the joint solves.** Every match keeps contributing. A lower-level match's expected statistic carries a level term (the same players win 2.9 more points in 100 at Challengers, EL:107-119; Tennis Abstract still finds a 1.09–1.10 ratio after its own competition adjustment, EL:323), and it counts with weight τ ≤ 1. Main-tour matches count fully. Precision weighting then reproduces the UFC fade without a fixed six-match clock: as main-tour matches accumulate, they dominate. Players who never play below the tour are untouched.
2. **Suggestion. If a gate is used, fit it the UFC way.** m_low as a slope ratio on training seasons only, stored and reused at prediction (experience_gate.py:146-171, 203-229). Use it only where the over-trust is in the *slope* on low-exposure players; the UFC level fix failed while the slope fix held.
3. **Suggestion. Route by the UFC routing diagnostic** (EUG:572-581): sweep the down-weight of lower-level evidence for one statistic; read the low-exposure and high-exposure splits. Both improve → change that statistic's native weight. Low-exposure improves while high-exposure worsens → a gate. Neither → leave it. Expect different answers per statistic, as K did in the UFC (EUG:549-558).
4. **Suggestion. Keep workload and layoffs on an every-level clock.** The UFC's any-organisation clock was right and its single-organisation clock hurt (LAO:26); a player's Challenger week is real tennis played.
5. **Inferred. Re-tune what was tuned on the pooled data.** The UFC prior and its solver dials were co-adapted (IPA:93). In tennis, the offset Elo's surface-offset K and the surface IOS constants were tuned on 2013–2018 (docs/decisions/2026-10-06-offset-elo.md:14; docs/decisions/2026-10-06-surface-ios-profile.md:9), on histories in which every level counts equally (EL:43, 136). A level-weighted arm should re-tune them on 2013–2018 only, or it is judged against an optimum it never had.

### 5.3 Avoid

1. **Re-scaling a rating or a prior on statistical-calibration grounds** (UFC: worse 6 of 6; IPA:17).
2. **A fixed discount fitted on old seasons.** The UFC padded-record correction was right for 2013–21 and wrong after (WEP:78-101). Fit τ walk-forward and watch it per season.
3. **Down-weighting lower-level opponents inside an opponent-quality average.** Fix how such an opponent is scored, not how much his game counts (NRP:64).
4. **Lower-level training rows without a price.** Tennis already found they lean harmful (−0.48 [−1.09, +0.14], a tie, and the edge over the close falls to a tie; EL:212-221). The UFC's successful pooling of men's fights into the women's model used rows with every input, prices included (WCS:50).
5. **Population defaults conditioned on a level tier, without shuffled-label twins.** The UFC's experience-conditioned defaults lost 1.70 mLL, and shuffled copies lost the same (EPV:11-12).
6. **Judging a component in isolation.** A better prior or a better statistic forecast is not a better model (NRP:286; EPV:13-17).
7. **Seed agreement, single seasons and small cells as evidence** (MEM/feedback_evidence_judging_rules.md:17-18).
8. **Market claims from long pooled windows.** The tennis β has grown by era; report it on rolling windows with a date (MEM/feedback_market_claims_recency_scoped.md:14-19).

---

## 6. What this report does not show

* **No UFC number was recomputed.** Every UFC figure is as its report states it, checked against the report and, for mechanisms, the code.
* **The UFC evidence is on a small sample and another learner.** The UFC verdict window is about 1,313 fights (NRP:392); the tennis 2020–24 window is about 22,265 matches (EL:188). TabICL and TabPFN are near-twins (MEM/MEMORY.md:56), so in-context lessons (column tax, spillover) plausibly carry over; that is an inference, not a test.
* **No UFC evidence exists on per-statistic transfer from a lower level,** because the UFC has no outside fight statistics. Tennis is in new territory there.
* **Lever 1 and the SoS-only richer prior are unresolved** in the UFC (parked to a fresh-season read ~2027-02; NTB:211-215, 244). Neither is a UFC verdict to import.
* **The diagnosis of which tennis inputs are contaminated** is outside this role; section 4.1 maps families only.

## Sources

Short names used above. `UFC/` = `C:\Users\zerom\Documents\UFC-Predictions\`; `MEM/` = `C:\Users\zerom\.claude\projects\c--Users-zerom-Documents-UFC-Predictions\memory\`. Tennis paths are relative to this repository.

| Short name | File |
|---|---|
| NRP | `UFC/docs/studies/nonufc_record_prior_study.md` (2026-09-19) |
| IPA | `UFC/docs/studies/informed_prior_audit_study.md` (2026-07-21) |
| WEP | `UFC/docs/studies/winrate_experience_prior_study.md` (2026-07-24) |
| EUG | `UFC/docs/studies/experience_uncertainty_gating_study.md` (2026-07-05) |
| WAS | `UFC/docs/studies/winrate_age_split_study.md` (2026-09-15) |
| EPV | `UFC/docs/studies/experience_prior_v4_vscode.md` (2026-09-30) |
| LEA | `UFC/docs/studies/layoff_espn_activity_study.md` (2026-09-08) |
| LAO | `UFC/docs/studies/layoff_aging_opus55.md` (2026-09-29) |
| WCS | `UFC/docs/studies/womens_v3_config_study_study.md` (2026-07-01) |
| NTB | `UFC/docs/near_the_bar_revisit_list.md` |
| AGENTS.md | `UFC/AGENTS.md` (the UFC evaluation policy) |
| UFC CLAUDE.md | `UFC/CLAUDE.md` |
| BACKGROUND.md | `UFC/docs/BACKGROUND.md` |
| dial audit | `UFC/docs/studies/v3_mens_dial_reverification_audit/v3_mens_dial_reverification_audit.md` |
| closing-odds spec 2026-04-26 | `UFC/docs/superpowers/specs/2026-04-26-closing-odds-residual-feature-design.md` |
| espn_coverage_prior_repair.md | `UFC/docs/studies/espn_coverage_prior_repair.md` |
| informed_priors.py | `UFC/src/features/informed_priors.py` |
| experience_gate.py | `UFC/src/features/experience_gate.py` |
| elo_utils.py | `UFC/src/elo_utils.py` |
| fight_data_utils_production.py | `UFC/src/fight_data_utils_production.py` |
| pre_process_v3_model_from_base.py | `UFC/src/pre_process_v3_model_from_base.py` |
| create_training_prediction_data_v3.py | `UFC/src/create_training_prediction_data_v3.py` |
| features/v4/history.py | `UFC/src/features/v4/history.py` |
| lib_nrp.py | `UFC/src/eda/nonufc_record_prior/lib_nrp.py` |
| EL | `docs/studies/event_levels/README.md` (tennis, 8 Oct 2026) |
| input_data_audit/README.md | `docs/studies/input_data_audit/README.md` (tennis) |

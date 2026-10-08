# Round 2 · Mechanics: rebuttals, one literature addition, two contrarian ideas

6 October 2026 · Brainstormer MECHANICS (Opus 5.5) · Research evidence, not a decision.

**Read:**
* [plan.md](../plan.md) and the [master list](../master_list.md), with the family tables of my 21 rows (I-001, I-004, I-008, I-012, I-014, I-016, I-018 to I-023, I-025 to I-028, I-046, I-066, I-068, I-072, I-073);
* the [mathematical audit](../round1/math_audit.md), its family cards and [withdrawn_and_blocks.md](../round1/math_audit/withdrawn_and_blocks.md);
* the [feasibility audit](../round1/feasibility.md) and its CSV;
* the [literature review](../round0/literature.md).

**No results.**
* No match result (`a_won`) was read, and no price was related to an outcome.
* Only seasons up to 2021 were used, read with a parquet filter.
* The current best's forecasts were read for 2014–2021, as forecasts.
* **Disclosure:** `stage0_match_players` has no season column. Parts E, G and G2 read up to four of its box-score columns (no result column) for every row, then kept only model-frame matches up to 2021. Nothing later was used.

Two kinds of look, both result-free, are reported for the look ledger:
* **The close's log-odds, or η, as a regressand against pre-match features** (parts B, C, D, F). This is the class of the mathematical auditor's I-006 check.
* **Serve-point statistics against pre-match IOS** (parts E, G, G2). These are statistic-level gates.
  * **Parts G and G2 computed I-012's precheck in two forms before its form was fixed** (see R2).

| Part | What | Script in `src/eda/feature_interactions/round2/mechanics/` | Output in `data/studies/feature_interactions/round2/mechanics/` |
|---|---|---|---|
| A, B | remainders on the 58 inputs; I-001's premise | `checks.py` (with `common.py`) | `checks.json` |
| C | I-001's premise for η | `part_c.py` | `part_c.json` |
| D | leverage between cells | `part_d.py` | `part_d.json` |
| E | court change within an event | `part_e.py` | `part_e.json` |
| F | the surface part of dominance | `part_f.py` | `part_f.json` |
| G, G2 | the serve–return link and the shield, from serve points | `part_g.py`, `part_g2.py` | `part_g.json`, `part_g2.json` |
| H | novelty of the serve-point link term | `part_h.py` | `part_h.json` |

## 1. Rebuttals (one round)

### R1 · I-008 · feasibility "defer" (novelty R² 0.980)

**Reformulation, using the feasibility auditor's own remedy.** The primary column becomes the remainder of z_C1 after an OLS projection on the 58 inputs. The projection is fitted per tour on 2013–2018, without outcomes, and applied unchanged to every later season.

**Computed (part A):**
* R² in the fit: 0.979 (men), 0.993 (women).
* Remainder SD in match log-odds: 0.217 and 0.104 in 2013–2018.
* Out of the fit, 2019–2021: **0.205 and 0.089**. That is seven and three times the ≈ 0.03 a 0.09 mLL term needs.

By Frisch–Waugh, the remainder's coefficient equals z_C1's beside the 58 inputs. The mathematical audit's weight (2) and sign (+) stand.

### R2 · I-012 · feasibility "defer" (g undeclared; R² 0.954 with a linear g), and block B2's precheck

**Declaration.** MEC-04 fixes g; nothing is free: c = logit[a + (1 − a)σ(logit r₀ − kD)] − logit p.
* a comes from IOS aces, r₀ from IOS serve points.
* k = p̄(1 − p̄)/((1 − ā)r̄(1 − r̄)), from Stage 4's cell averages.

**Novelty (part A).** R² on the 58 is 0.922 (men) and 0.929 (women), under 0.95. The 2019–2021 remainder SD is 0.075 and 0.039 match log-odds.

**Precheck.** The shield (+) and the probability-scale link (−) correlate at 0.70 and cancel when tested alone.
* Shield alone (men): −0.006 ± 0.031, a false kill.
* Joint fit, r ~ O + D + O^ace + O·D + O^ace·D (part G2):
  * shield **+0.053 ± 0.044**, where the structure predicts +0.050;
  * link −0.27 ± 0.14.

**So the gate must be the joint fit.** I computed both forms before choosing: a ledger look. Women: uninformative.

## 2. Result-free numbers for verdicts I accept (no contest)

**I-001 (pass, weight 1): the premise holds in part.**
* **The close applies less than half of the iid's dominance scaling.** Within tour × surface × indoor × best-of cells, at matched IOS strength, the close's log-odds scale with the pair's leverage at b/a = 0.52 (men) and 0.42 (women). The iid's own log-odds, on the same rows, give 1.21 and 1.24 (part B). So the close applies about **43% (men) and 34% (women)** of the iid scaling.
* **The current best applies no more.** Its η applies 36% (men, 2014–2021; part C). Its adjustment does not scale with κ: its coefficient on z·κ is +0.01.
* **Attenuation is not the cause.** Var(Δ) is flat across κ terciles (0.068–0.073).
* **Reading.**
  * Unlike I-006, the premise survives; the card's "≈ 0.03 if half priced" is the right planning number, and the + sign is supported.
  * The women's numbers are noisy (RMS κ 0.026).
* **A sensitivity, suggested.** Add the venue's earlier-edition serve residual (I-072) to m; its stable SD is about 0.04 log-odds.

**I-020 (kill, reason c): I agree, as its originator.**
* Feasibility's 70% is the share of matches with any speed history.
* A recent-change column needs speeds in the matches themselves, which cover 12%. That is my own 30% floor again.

**Accepted as ruled:** I-004, I-014, I-016, I-018, I-019, I-021, I-022, I-023, I-025, I-026, I-027, I-028, I-046, I-066, I-068, I-072, I-073; and W-01 to W-09.

**Two candidates dropped before proposing them:**
* **Court wear by round** (part E, men): late-minus-early ace residuals lie between −0.02 and +0.02, with no carry-over between editions (r −0.13 to +0.10).
* **The surface part of dominance** (part F, men): it is priced at 29%, against 44% for the all-surface part, but its RMS is 0.015, worth under 0.01 mLL.

Part D (leverage between cells) is confounded by cell-specific attenuation of Δ, and is not used.

## 3. Literature addition (one)

**The other mechanical items in the review are already master-list rows:**
* price shape by context: I-036;
* best of five: I-006, I-007;
* volatility: B5;
* event speed: I-072;
* home: B-HOME;
* height and handedness: I-021 to I-024;
* head-to-head: I-019, I-091;
* clutch: B-CLUTCH;
* load: family 11.

**Pollard, Cross and Meyer's set dependence** [R13] is a format-level effect, which is I-006's territory.
* Its player-specific version ("better at best of five", [R13b]) is worth about 0.002 mLL by iid arithmetic, so it is not proposed.
* The arithmetic: a first-set handicap costs 2s(1 − s) of match probability in best of three, and 25% less in best of five.

### MEC-L1 · The serve–return link: a probability-scale correction to IOS

| Field | Content |
|---|---|
| ID, name | MEC-L1 · The serve–return link (literature §5: "No paper tests a point-level server × returner interaction") |
| Mechanism | **The two scales differ by a bilinear term.**<br>• IOS adds serve and return on the log-odds scale (O − D). Barnett–Clarke adds them on the probability scale [R39].<br>• The difference is σ(μ + O − D) − [σ(μ + O) + σ(μ − D) − σ(μ)] ≈ −σ″(μ)·O·D. In serve-point log-odds that is γ·O·D, with γ = 1 − 2p̄ = −0.24 at p̄ = 0.62.<br>**Observed** (part G2; men's serve points, 2013–2021, no winners): γ̂ = −0.27 ± 0.14, fitted jointly with the shield (−0.17 ± 0.10 alone). Women: +0.07 ± 0.23, uninformative.<br>A strong server facing a strong returner wins fewer serve points than IOS says. |
| Why the price might miss it | Practitioners use one scale or the other. Untested in the literature. |
| Type | X (and a correction inside the C columns) |
| Formula | τ = O^spw_A·D^spw_B − O^spw_B·D^spw_A = ½[ΔO·ΣD − ΣO·ΔD] = −prod_spw.<br>A's serve-point correction minus B's is γ·τ; the match form is L(m)·γ·τ.<br>**Swap:** anti ✓. **Sign:** − on τ.<br>**Pre-declared variant:** a surface-specific γ_s = 1 − 2p̄_s (men: clay −0.21, grass −0.31). |
| Data | Surface IOS spw for A and B. **Timing:** leak-proof IOS, inherited. Coverage 100%. |
| Why the model cannot already do it | It needs levels, and the seven `prod_<s>` exclude spw.<br>The component products carry most of it: R² on the 58 is 0.987 (men) and 0.961 (women).<br>Remainder SD 0.010 and 0.008, implying 0.013 and 0.011 match log-odds (part H). |
| Expected effect (S6) | **Prior:** Δ ≈ +0.02 mLL (men) and +0.01 (women), sign − on τ, coverage 100%. Below every MDE as a stand-alone column |
| Main-effect decomposition (M2) | X: d = τ. Controls: ΔO^spw, ΔD^spw, ΣO^spw·η, ΣD^spw·η, the seven prods, Std |
| Deployment | **No hypothesis slot.** Use it in two places:<br>(i) a link-corrected I-008, building each part as σ(μ + O − D + γ_s·O·D), as a pre-declared sensitivity;<br>(ii) O·D as a mandatory control in B2's precheck (R2). |
| Evidence seen 2025–26 | No. The statistics here are 2013–2021; the literature's tests are ATP 2014 and earlier |
| Kill test | Result-free: kill if the joint-fit γ̂ on 2013–2021 serve points is ≥ 0. Today −0.27 ± 0.14 (men) |

## 4. Contrarian ideas (critique S5)

### MEC-K1 · Information-weighted Elo (against "ratings and win/loss information are priced in")

| Field | Content |
|---|---|
| ID, name | MEC-K1 · Elo updated by each result's information |
| Mechanism | **Results are not equally informative.** Under the iid, a result's information about the strength gap is ∝ λ²·p(1 − p).<br>• Two big servers (λ ≈ 0.81, the men's hard-court 5th percentile) give (0.81/1.04)² = 0.61 of the information of two returners (λ ≈ 1.04, the 95th).<br>• A best-of-five result gives 1.25² = 1.56 times a best-of-three one.<br>• **What goes wrong.** Elo, rankings and the results-based views behind the price weight every result alike, with E = σ(ΔR/s) for every pair. So tiebreak-heavy careers carry noisier ratings, and Slam results are under-weighted. |
| Why the price might miss it | **The market is leverage-blind.** It applies about 43% of the iid's dominance scaling (part B), and its ratings inherit the same blindness in estimation |
| Type | W (a new per-player rating difference; U character) |
| Formula | **Update:** R_A ← R_A + K·λ_AB·(y − σ(λ_AB·(R_A − R_B)/s)).<br>**Leverage:** λ_AB = L(m_AB)/L̄ × (1.25 at best of five), with m_AB from leak-proof IOS at each earlier match.<br>**Constants:** K and s as Stage 1's surface Elo, frozen, no tuning.<br>**Column:** x = ΔR_lev. **Swap:** anti ✓ |
| Data | **Updates:** Stage 0 results in each player's own order (safe by construction). **λ:** leak-proof IOS at each earlier match. Coverage 100% |
| Why the model cannot already do it | `elo_overall`, `elo_games` and `elo_surf_offset` are leverage-blind; the points-based inputs are not results-based |
| Expected effect (S6) | **Prior:** Δ ≈ 0–0.03 mLL, sign + on ΔR_lev beyond the Elo inputs, coverage 100%. Men mostly: λ's within-cell SD is 0.067 against 0.026.<br>Near (e): rating variants tied at the close (W-19), so weight 0.5 |
| Main-effect decomposition (M2) | W: d = ΔR_lev. Controls: the three unweighted Elo inputs, Std |
| Deployment | TabPFN difference column if capture ≥ 0.5, else a nudge |
| Evidence seen 2025–26 | No |
| Kill test | Result-free gate: on 2014–2021 main-tour matches, kill if the SD of ΔR_lev − ΔR_std is under 15 Elo points, or if ΔR_lev's R² on the 58 exceeds 0.95 |

### MEC-K2 · The pair's realized character from earlier meetings (against "head-to-head adds nothing beyond ratings")

| Field | Content |
|---|---|
| ID, name | MEC-K2 · Head-to-head as match character, not as who won |
| Mechanism | **Earlier meetings record more than who won.** Head-to-head results are strength plus luck (tied or worse at the close in five forms). But the meetings also record the pair's realized serve dominance: both players' serve points won.<br>The link (MEC-L1) and the shield (I-012) operate at the level of the pair. If some pairings play systematically more or less serve-dominated than the two IOS profiles predict, the realized dominance refines κ_pair, I-001's modulator. The close applies only about 43% of the predicted scaling there |
| Why the price might miss it | The market reads head-to-head as who won, not as how serve-dominated the meetings were |
| Type | M × S (refines I-001's modulator) |
| Formula | **Residual per meeting:** e_k = logit(serve points won by both in meeting k) − m̂_AB,k, the IOS-predicted dominance at the time.<br>**Shrunk mean:** ê_AB = Σ n_k·e_k / (Σ n_k + 600 serve points).<br>**Modulator:** κ_H2H = L(m_AB + ê_AB)/L(m_AB) − 1.<br>**Column:** x = η·κ_H2H. **Swap:** ê is symmetric and η anti, so x is anti ✓. **Sign:** + |
| Data | Box scores of earlier meetings (the pair's own matches: safe by construction), and leak-proof IOS for m̂. About 60% of main-tour matches follow a meeting; elsewhere ê = 0 |
| Why the model cannot already do it | There is no pair input, and a symmetric pair quantity cannot be formed from differences |
| Expected effect (S6) | **Prior:** Δ ≤ 0.01 mLL, sign +, coverage about 60%; only if the pair-level dominance residual persists |
| Main-effect decomposition (M2) | M × S: s = κ_H2H, d = η. Controls: the M-set; I-001's κ·η, so that only the head-to-head refinement identifies b; the missing-meeting indicator × η; Std |
| Deployment | Nudge |
| Evidence seen 2025–26 | No |
| Kill test | Result-free gate: for pairs with at least 3 meetings, the correlation between ê from meetings 1 to k − 1 and e_k. Kill if it is under 0.1, or not above the same correlation with partners shuffled within tour × season |

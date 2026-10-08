# Round 2 · Body and schedule: rebuttals, literature additions, contrarian ideas

6 October 2026 · Brainstormer "body and schedule" · Research evidence, not a decision.

**Read:** [plan.md](../plan.md), [master_list.md](../master_list.md) (BOD-01 … BOD-30 are now I-024, I-042, I-043, I-045, I-047, I-048, I-050–I-065, I-067, I-069, I-070, I-074, I-075, I-077, I-078, I-090), the [math audit](../round1/math_audit.md) (families 09–14 and 16, [blocks](../round1/math_audit/withdrawn_and_blocks.md)), the [feasibility audit](../round1/feasibility.md) (families 11 and 14) and the [literature](../round0/literature.md).

**No result read.** Nothing here relates a column to `a_won` or compares a price with an outcome. I loaded only seasons up to 2024, filtered when the files were read.

* Code: `src/eda/feature_interactions/round2/body/calc_core.py` and `calc_report.py`. Output: `data/studies/feature_interactions/round2/body/calc_report.json`.
* Rows: the 34,890 model rows of 2014–2021. Each player's own played matches come from the pre-rebuild Stage 0 and clock.
* R² is plain OLS on the 58 inputs, plus missingness indicators.
* Load is minutes where known, else games × the tour's 2010–2018 median minutes per game, which gives 100% coverage. Fat uses τ = 3 days, as the math audit fixed it.

**Accepted.** These verdicts on my ideas stand: every block placement (B6, B9a, B9b, B10, B11, B-INJ, B-SWITCH, B-HOME, B-AGE, B-REPUTE, B-MOTIV); I-052 and I-053 at weight 1 with τ fixed in advance; I-056's single Scare definition; I-057, I-062 and I-069 as sensitivities; I-077 folded into venue pace; I-064 deferred to its statistic-level precheck; I-067 killed (no weather on disk). I contest one demotion and three deferrals.

## 1. Rebuttals

### R1 · I-051's Off is not a sensitivity of I-052 (math audit, family 11)

* **Contested.** "Off becomes a sensitivity of I-052", on the reason "Off is Fat restricted to off-site load".
* **Result-free computation.**
  * R² on the 58 inputs: ΔFat 0.811, ΔOff 0.543.
  * Adding ΔFat to the 58 lifts ΔOff only to 0.546. Adding ΔOff lifts ΔFat only to 0.813.
  * So ΔOff's novel variance (46%) is 2.4 times ΔFat's (19%), and the two are almost orthogonal.
* **Algebra.** I-051's mechanism has on-site load positive and off-site load negative. ΔFat adds the two, so its test beyond `sets_14d` reads a different residual. And a sensitivity cannot carry a claim.
* **Fix.** Make ΔOff a stand-alone hypothesis at weight 0.5 (sign −; controls `sets_14d`, ΔFat, Std). Or make I-052 a two-column Wald test {ΔFat, ΔOff}. The On and Off parts vary almost independently: corr(ΔOn, ΔOff) = −0.11.

### R2 · I-060 can pass G2 now (feasibility, family 11: "event country exists only for evaluation events; a continent map is to build")

* **Rebuilt from data on disk.**
  * Event countries come from `stage4_event_country.csv` for evaluation events. Every ITF tournament id also carries the host's IOC code (`^\d{4}-[MW]-[A-Z0-9]+-([A-Z]{3})-`).
  * Continents come from the 81-code map in `round0/body/counts.py`, plus 46 codes that appear only in ITF ids. This is built, and it runs in seconds.
* **Computation.**
  * 1.8% of all-level played player-match rows up to 2024 stay unmapped. 61% of those are team ties, whose ids name two nations; 20% are ITF and 16% Challenger.
  * On the 2014–2021 model rows, every event in both players' previous 42 days has a known continent in 79.1% of men's and 82.1% of women's matches. The rest takes the single missingness rule (S11).
* **Ask.** Pass. The build takes about an hour and is done. The same map supplies I-059's travel factor.

### R3 · I-074 (jet lag) needs no city table (feasibility: "time-zone table not held"; math audit: "only if a city → UTC-offset table is built")

* **Reformulation.** Use a continent-level offset from R2's map, taking the circular difference: EU and AF +1, ME +4, AS +8, OC +10, NA −6, SA −3 hours.
  * A city table would refine only moves within one continent: at most 3–4 hours (US coasts, Australia, Mexico), which rarely reach the ≥ 5-zone trigger.
  * Two country overrides, India +5.5 and Kazakhstan +6, fix the main misclassifications.
* **Computation.**
  * The proxy is defined for both players at 92.8% of men's and 94.6% of women's first-match rows.
  * The trigger (≥ 5 hours, ≤ 5 days since the last match) touches 1.28% of men's and 0.76% of women's 2014–2021 model rows.
* **Ask.** Build I-074 with the proxy inside B10 now, and drop the six-hour table. That prevalence also caps its value. A surviving shift of 0.1–0.2 logit on 1% of rows is worth 0.01–0.04 mLL (gain, higher is better) by the value rule, so it should stay a block member.

### R4 · I-075's novelty term does not wait for three tables (feasibility, family 14: "depends on three tables not yet built")

* **The auditors disagree.** The math audit already ruled "Nov from the parts on disk; altitude dropped".
* **With R2's map, every part is on disk.** Shares are of 2014–2021 model rows, men / women:
  * a surface switch for either player: 13.5% / 11.9%;
  * a continent change: 20.5% / 20.9%, defined for both players at 93–95% of first-match rows;
  * the indoor switch: men from Stage 0; women from tennis-data's Court field, as the math audit proposes.
* **Ask.** Pass G2 now, with Nov = 1[surface switch] + 1[indoor/outdoor switch] + 1[continent change]. Its R² is measured with block B11.

## 2. Literature additions

I checked the master list for both before proposing them. The previous match's sets relative to the opponent appears only as I-056's *control* (ΔScare); age × strength does not appear at all.

### BOD-L1 · The previous match's extra sets, relative to the opponent's, by tour and format

| Field | Content |
|---|---|
| ID, name | BOD-L1 · Previous on-site match: set excess against the opponent's |
| Mechanism | An extra set in the previous round costs energy and recovery time. **Reported** ([literature](../round0/literature.md) idea 4), each controlling only for rank or Elo: <br>• Goossens et al., Slams 1992–2011: women with one set more than the opponent, logit −0.286 (s.e. 0.052); men +1 set −0.076 (not significant), +2 sets −0.184 (s.e. 0.039) [R14]. <br>• O'Donoghue 2006: women affected, men not [R15]. <br>• Sackmann, men's Slams: next-round win ratio against surface Elo falls from 1.07 to 0.76 as the previous match lengthens [R61] |
| Why the price might miss it | Scores are visible, and practitioners say this is "usually" priced, but no study tests it against odds (literature §5). No input carries it: "only `sets_14d`; no last-match sets relative to the opponent" (literature, idea 4). The master list uses it only as I-056's control, so nothing tests it as a hypothesis |
| Type | W (S secondary by tour and format) |
| Formula | PrevX_X = (sets in X's previous match − the format's minimum) / (maximum − minimum). This applies if that match was at this event and ≤ 3 days ago; otherwise PrevX = 0, and it is missing if that match ended in a retirement. d = PrevX_A − PrevX_B. Swap: negates ✓. Secondary: 1[women]·d and 1[bo5]·d (context × difference). Sensitivities: the previous two on-site matches (O'Donoghue) and minutes above the format's median (Sackmann) |
| Data | Stage 0 previous match (score → sets, `best_of`, `status`); the clock's `obs`. Safe by construction. Built in `calc_core.py` |
| Why the model cannot already do it | `sets_14d` is a 14-day box-car. d correlates 0.30 with ΔFat and −0.03 with ΔOff |
| Expected effect (S6 prior) | Sign −. Coverage: d ≠ 0 in 28.8% of men's and 26.0% of women's 2014–2021 model rows; missing in 3.2%. E[d²] = 0.27. Upper bound by the value rule 99·β²·E[d²], if the rank-only coefficient survived the close whole: 2.2 mLL (women), not plausible. If 15–25% of it survives: 0.05–0.14 mLL for women and ≤ 0.05 for men. All gains, higher is better |
| M2 decomposition | d is itself the main effect: I-056's ΔScare for best of three, graded for best of five. I-056's rest contrast is its modulation. Controls: `sets_14d`, ΔFat, I-056's contrast column, Std (missingness difference and missing·η) |
| Novel variance | R² 0.121 on the 58 inputs (88% new) |
| Deployment | TabPFN difference column |
| Evidence seen 2025–2026? | No. The literature covers 1992–2017; this computation stops at 2021 |
| Kill test | Beyond η and its controls, d's interval spans 0 or the sign is positive, on the screen's 2014–2021 filter |

### BOD-L2 · Career stage: the price should be flatter far from the stable ages

| Field | Content |
|---|---|
| ID, name | BOD-L2 · The pair's distance from the stable ages × the price |
| Mechanism | **Reported.** In random-forest dependence plots, Elo's weight is largest near ages 28–32 (men's Slams 2011–22, 5,013 matches [R46]). Ageing curves peak near 25 for men (flat 24–27) and 23–24 for women [R75]. **Inferred.** A teenager's or a 34-year-old's level is still moving, so a strength gap built from past results is less reliable, and the forecast should be flatter |
| Why the price might miss it | The market prices names and ratings; how reliable a gap is at each career stage is not a quoted adjustment. Not in the master list (age enters only as levels: I-053, I-068, I-070, I-071) |
| Type | M × S |
| Formula | s = abs(age_A − 28.5) + abs(age_B − 28.5) − its mean (symmetric); column s·η, with the price version s·z. Swap: s unchanged, η negates ✓. Sensitivities: hinges (24 − age)+ + (age − 32)+; centre 27 for women |
| Data | Stage 0 `age` (97.5%) and η. Safe |
| Why the model cannot already do it | The model has Δage and Δage², not Σabs(age − c). The S2 arm's Σage cannot form it linearly |
| Expected effect (S6 prior) | Sign − (flatten). Coverage 100% of model rows. By the price-slope rule (79κ² men, 68κ² women): a ±5% slope swing would be worth 0.2 mLL if unpriced. Prior 0.02–0.08 mLL; evidence grade C (no odds) |
| M2 decomposition | A symmetric s has no main effect in the antisymmetric screen. The candidate is s·η, with controls the M-set and Std (cross-cutting finding 1) |
| Novel variance | R² 0.068 (93% new). It correlates 0.09 with BOD-C2 and 0.01 with I-049, so it is distinct |
| Deployment | s as a context column for TabPFN, else a nudge |
| Evidence seen 2025–2026? | No (sources stop in 2022; computed to 2021) |
| Kill test | b ≥ 0, or b's interval spans 0 |

## 3. Contrarian ideas (critique S5)

### BOD-C1 · The two-week profile reads tiredness as decline

| Field | Content |
|---|---|
| ID, name | BOD-C1 · Fatigue-contaminated form |
| Claim contradicted | The brief's thesis that the per-statistic profiles carry *skill*. Here the two-week profile partly measures the fatigue state under which its statistics were produced |
| Mechanism | `form_*` and `adjperf_tpw_2w` average the last two weeks' opponent-adjusted statistics. Statistics produced while tired (late rounds, back-to-back weeks) are depressed. Once rested, the player is better than the profile says, and the model reads the dip as decline |
| Why the price might miss it | The error is in the model's own input, which the price does not use. The gain is measured against the current best, as with I-068 |
| Type | W |
| Formula | PastFat_X = the mean of Fat_X(τ = 3 days) over X's own matches in the 14 days before; d = PastFat_A − PastFat_B. Swap: negates ✓ |
| Data | The players' own histories and I-052's kernel. Safe by construction. Built in `calc_core.py` |
| Why the model cannot already do it | The profile carries no record of the state in which each past match was played. **Observed:** d correlates +0.34 with Δ`adjperf_tpw_2w` (busy players are also winning) and +0.29 with ΔFat. Current fatigue (sign −) must therefore be held, or it masks the effect |
| Expected effect (S6 prior) | Sign + given the 58 and ΔFat; 0.02–0.08 mLL (gain). Coverage 80.3% of 2014–2021 model rows (both players played in the last 14 days) |
| M2 decomposition | d is the main effect. Controls: ΔFat, `sets_14d` and the profile (inside η); Std |
| Novel variance | R² 0.67 (33% new) |
| Deployment | TabPFN difference column |
| Evidence seen 2025–2026? | No |
| Kill test | d's interval spans 0, or the sign is negative, beyond η, ΔFat and Std |

### BOD-C2 · One calibration slope per tour is wrong: staleness should flatten the forecast

| Field | Content |
|---|---|
| ID, name | BOD-C2 · The pair's staleness × the forecast |
| Claim contradicted | The brief's calibration design, one logistic slope per tour refitted each season, and "calibration was worth more than any input". Calibration itself may depend on the schedule. Also against I-049's premise (the price is under-confident early in a surface season, so steepen) |
| Mechanism | After long gaps (the off-season, injuries, skipped weeks) every input, the price's included, describes an older player. The true strength gap is then less certain than the inputs say, so the forecast should be flatter |
| Why the price might miss it | Sharp prices react to injury news, not to the generic staleness of form information |
| Type | M × S |
| Formula | s = log1p(rest_A) + log1p(rest_B) − its mean, where rest = days since the player's previous played match at any level (best-estimate days); column s·η, with the price version s·z. Swap: s unchanged, η negates ✓ |
| Data | Each player's own sequence (`rest_days` as in `history.py`) and η. Safe by construction |
| Why the model cannot already do it | Rest is not an input. The `surf_layoff` pairs are surface-specific, and a single slope cannot vary with staleness |
| Expected effect (S6 prior) | Sign − (flatten). Coverage 100%; either player rested ≥ 21 days in 11.0% of men's and 12.5% of women's 2014–2021 model rows. By the price-slope rule, a slope RMS of 0.04 would be worth 0.13 mLL if unpriced. Prior 0.02–0.1 mLL (gain) |
| M2 decomposition | A symmetric s has no main effect. The candidate is s·η, with controls the M-set and Std. I-049's column is a declared rival, fitted jointly (corr +0.29, so the two can be told apart) |
| Novel variance | R² 0.088 (91% new) |
| Deployment | Calibration nudge, or s as a context column for TabPFN |
| Evidence seen 2025–2026? | No |
| Kill test | b ≥ 0, or b's interval spans 0, in the joint fit with I-049 |

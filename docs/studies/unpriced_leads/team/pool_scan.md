# Pool scan (S1): the built pool against the close, seasons ≤ 2024

13 Oct 2026 · S1, the pool statistician (Claude Opus 5.5, session `e1ffc84e-fa2d-42f9-9d17-7c936a046c45`) · Discovery evidence, not a decision · Code: [`src/eda/unpriced_leads/pool_scan.py`](../../../../src/eda/unpriced_leads/pool_scan.py) · Data: `data/studies/unpriced_leads/pool_scan/`

No outcome from 1 Jan 2025 on was read. Outcomes were read only through the harness, and the 2025–26 coverage counts the feature store's own rows, which hold no result. Labels: *observed* (from the files above), *inference*, *suggestion*. Signs: + means the player higher on the statistic beats the close; for a context column, + means a steeper price where the context is high.

## 1. Method (observed)

* **Candidates.** 340 in all: every `menu.csv` column not catalogued `in_model`, plus `m__ios_points_short`, which the owner dropped from the model on 9 Oct.
  * 163 diffs, screened as they are.
  * 135 pairs, screened as A − B.
  * 42 contexts, screened as the harness's slope modifier.
  * 298 orthogonal parts, all lenses: each diff and pair minus its projection on the model's **48** non-price inputs. The docstrings say 49: the 57-input template has no `ios_points_short`, and each surface pair enters as one A − B.
* **Rows.**
  * The frame's 57,731 non-debut matches of seasons ≤ 2024; 55,111 of them join the store.
  * **The store has no men's 2018** (2,620 matches), so the men's 2017–19 era is 2017 plus 2019.
  * The store ends on 28 Jul 2026, so 2025–26 coverage means Look A.
* **Flags.** Flagged columns are screened and reported but never shortlisted:
  * 8 base-dependent (the other two of the ten are copies);
  * 8 market-internal;
  * 13 known nulls;
  * 1 now in the model: the both-tours indoor flag equals the current indoor input on 100% of men's and 98.7% of women's rows;
  * 3 near a context input: B-LEVER `s1` against best of, r 0.94;
  * 43 copies of an input at |r| ≥ 0.95: the pooled IOS and every other rating system;
  * 4 unstable (§ 2).

  262 candidates remain eligible.
* **The shortlist rule, fixed before the full run.** A row passes if:
  * it is eligible;
  * |z_pool| ≥ 2, with at least 3 of the 4 eras of its sign;
  * for a diff or pair, the orthogonal part meets the same test with the same sign.

  43 both-tour rows pass, 16 men's and 35 women's. `shortlist_rule.csv` keeps one member per outcome-free correlation cluster (complete linkage at |r| ≥ 0.8; 182 + 37 clusters): 33, 14 and 25 rows.
* **Post hoc.** 18 representatives read jointly, beside each other and then also beside the 48 inputs (`joint.csv`). I chose them after the scan, so the joint reading only sorts distinct signals from shared ones.
* **Deterministic** (one BLAS thread): two runs, byte-identical.

## 2. Negative controls

* **Sign-flip placebos** (observed). Each tested column was multiplied by a random sign per four-week block, 3 draws per candidate and encoding.
  * Without the 4 unstable columns: z SD 1.04–1.10; |z| ≥ 2 in 5.6–7.1% of draws and ≥ 3 in 0.3–1.2%; all four eras of one sign in 11–13%.
  * The N(0, 1.08²) references are 6.4%, 0.5% and 12.5%. **The harness is calibrated for these columns.**
* **Four unstable columns** (observed). Women's protected-ranking and alternate entries, the men's switch-missing indicator, and the orthogonal part of `alt__prod_cur_df`. Their placebo RMS z is 3–41, so their own z's (up to 41) mean nothing. They are excluded from every count.
* **Known nulls** (observed). 3 of 39 close-lens readings reach |z| ≥ 2, against 2.5 expected: `alt__ttt_logit` (both tours −2.06, men −2.19), the known over-weighting of ratings, and `alt__sdevO_first_won` +2.15. No model-lens reading exceeds 1.9.
* **The move lens is not a null test** (observed). Open-to-close moves track every strength proxy: the median |z| is 2.7 raw and 1.7 orthogonal, and known nulls reach 16. I read it only as a direction:
  * *toward*: the line moves the way the effect points, so the market learns part of it;
  * *against*: the line moves the other way;
  * *flat*: no move.
* **Context columns:** the harness's R² is about 0 by construction, so their correlation with the six context inputs is used instead.

## 3. What the pool carries beyond the close

**Overall** (observed; both tours; 328 candidates without unstable or base-dependent columns):

| Encoding | \|z_pool\| ≥ 2 | Expected | \|z_pool\| ≥ 3 | Expected |
|---|---:|---:|---:|---:|
| Raw (328) | 98 | 21 | 53 | 1.8 |
| Orthogonal (286) | 46 | 18.3 | 11 | 1.6 |

Men and women give 65 and 71 raw readings at |z| ≥ 2, and 25 and 46 orthogonal ones. Seven eligible both-tour orthogonal readings have BH q < 0.05, six distinct columns: the letdown, B-MOTIV, B-VENUE, seeded, ranking points, low-visibility form.

**The pool carries information the close lacks, but more than half of the raw signal is the model's own inputs again** (inference). It is mostly relatives of `sets_14d`, age and the surface pairs: the schedule family edge_anatomy found unpriced and already in the model.

| Family (both tours) | n | Raw ≥ 2 (expected) | Raw ≥ 3 | Orth ≥ 2 (expected) | 2020–24 replication: close / model |
|---|---:|---:|---:|---:|---:|
| feature-interactions blocks | 98 | 36 (6.3) | 22 | 15 (5.4) | 0.85 / 0.48 |
| load and schedule | 38 | 20 (2.4) | 14 | 9 (2.4) | 1.03 / 0.64 |
| level sums (context) | 18 | 9 (1.2) | 4 | — | 0.93 / 0.91 |
| player background | 16 | 5 (1.0) | 3 | 3 (1.0) | 0.73 / 0.42 |
| ratings | 31 | 13 (2.0) | 5 | 6 (2.0) | 1.09 / 0.37 |
| long-memory profile | 98 | 9 (6.3) | 1 | 9 (6.3) | 0.23 / −0.08 |
| shot and point level | 10 | 0 (0.6) | 0 | 0 (0.6) | −0.43 / −0.64 |
| event levels (U-330) | 2 | 2 (0.1) | 2 | 2 (0.1) | 5.26 / 2.43 |

*Replication* is the family's mean 2020–24 z, each column oriented by its own 2013–19 sign (independent outcomes, 0 under the null). A model figure near the close figure means the model leaves the information unused; near 0, the model has it.

**Promising** (§ 5; readings observed, mechanisms inference):
* **Calendar effort:** the post-Slam letdown.
* **Venue × serve,** for women.
* **A status axis.** The close over-prices names (seeded, famous, ranking points) and under-prices arrivals from lower levels or from low-visibility form. The two sides correlate at r −0.4 to −0.6 and share one signal jointly. The line moves *away* from the arrivals before the close, a bias the close keeps.
* **Recent load beyond `sets_14d`:** busy players beat the close.
* **Conversion luck:** wins beyond what the points share implies.
* **Rust** (seen).
* **Pair serve strength as a slope modifier:** the price should be flatter when both players serve big.

**Priced, or already in the model** (observed):
* **Long-memory profile variants:** at chance.
* **Other rating systems:** orthogonalised, the replication falls from 1.09 to 0.17. What they carry is the close's over-weighting of ratings, which Elo already gives the model.
* **Shot and point level** (with serve speed): 0 of 10.
* **Load kernels:** fatigue, off-site load and the 21-day fitness kernel are relatives of `sets_14d`.
* **Arrival features:** they fade to about 0 by 2023–24.
* **Calendar context, body and history:** week, month, Slam proximity; height, handedness, head to head.
* **Market-internal columns,** measured against a Pinnacle-first close.
* **The dropped `ios_points_short`:** +0.53 orthogonal.

## 4. Caveats

* **Multiplicity.** About 2,000 readings; 67 of 219 clusters reach a raw |z| ≥ 2. Every shortlisted item is a best-of-many: expect shrinkage, and confirm on unseen seasons.
* **Copies.** Read clusters, not columns: `fi__B-MOTIV__post_slam` is `fp__f19_motiv__post`, and B-STATE is `pastfat`.
* **Base-dependent columns** carry the 7 Oct model's own edge (`fi__I-042__x` +4.38): not discovery evidence.
* **Coverage holes:**
  * men's 2018;
  * women's height, 39% of 2025–26;
  * women's service-game statistics, 74% of 2013–21;
  * women's minutes imputed before 2016, which touches the load columns;
  * serve speed thin before 2022;
  * past fatigue missing without a match in the last 14 days.
* **Data version.**
  * The store was built on the 30 Sep Stage 0; the inputs and the model lens on the corrected 8 Oct tables with the level layer.
  * Box-score columns keep faults fixed since: Roland Garros first serves 2022–25, the Australian Open and Roland Garros service-game swaps, the WTA's 2015 double faults.
  * An orthogonal residual can partly be this gap (row 15). *Suggestion:* rebuild a chosen column on the current tables before registering it.
* **Drift.** The letdown is weakest in 2023–24 (raw −1.22; the 12-day Masters?); the lower-level share and women's B-VENUE are strongest then.
* **The model lens** covers only 2020–24: its |z| runs about 0.6 times the close lens's even for an unused column.

## 5. Ranked shortlist

The joint z is the post-hoc reading beside the other representatives and the 48 inputs. The model and move (raw) columns are both-tour readings unless a tour is named.

| # | Area: columns (catalogue id) | Seen 2025–26 | Raw z (eras) | Orth z (eras) | Joint z | Model | Move | Note |
|---|---|---|---|---|---|---|---|---|
| 1 | Post-Slam letdown: `fp__f19_motiv__post_a-b` (U-162, U-284) | no | −4.71 (4/4) | −4.23 (4/4) | −3.97 (4/4) | −2.38 | flat | Women −3.29, men −1.83 (orth) |
| 2 | Venue pace × aces: `fi__B-VENUE__x` (U-254) | no | +3.69 (4/4) | +3.87 (4/4) | +3.75 (4/4) | +2.62 | toward | Women +4.45, men +1.41 (orth) |
| 3 | Status, under-rated side: `el__low_share_diff` (U-330), `fp__f12_salience__hasL_a-b` (I-082) | no | +5.30 / +5.08 | +2.88 / +3.29 | +2.43 / +0.38 | +2.43 / +3.22 | against | One signal; U-330 is already a lead |
| 4 | Status, over-rated side: `pp__seeded_a-b` (U-175), `fp__f14_anchor__fame_a-b` (U-177), `pp__rank_points_a-b` (U-172) | no / no / yes | −4.32 / −3.90 / −4.57 | −3.61 / −2.73 / −4.53 | −1.75 / +0.38 / −1.17 | −2.47 / −1.30 / −2.91 | mixed | Shares row 3's signal |
| 5 | Recent load: `fi__B-STATE__x` (U-322) | no | +5.20 (4/4) | +2.11 (3/4) | +2.61 (4/4) | +1.92 | toward | r 0.75 with `sets_14d` |
| 6 | Conversion luck: `fi__B-OVERREACT__luck_13w` (U-278) | no | −2.11 (4/4) | −1.58 (4/4) | −2.50 (4/4) | −2.32 | toward | Below the rule's orthogonal bar; kept for the joint reading |
| 7 | Rust: `fp__f26_impairment__bdinj_rust0_a-b` (U-135), I-043 | **yes** | −4.88 (4/4) | −3.05 (4/4) | −3.45 (4/4) | −2.48 | toward | B-INJ tied on 2025–26 |
| 8 | On-site rhythm: `fi__B11__bd11_on` (U-307) | no | +4.28 (4/4) | +2.27 (4/4) | +1.11 (3/4) | +2.03 | toward | Shares rows 3 and 5 |
| 9 | Pair serve strength: `lv__iosO_first_won` and three relatives (H-S2) | no | −3.44 (4/4) | context | −1.52 (4/4) | −1.37 | flat | r 0.55 with the Elo sum, which failed on 2025–26 |
| 10 | Women's travel: `fp__f23_arrival__bd10_trav_a-b` (U-148) | no | −3.38 (4/4) | −2.19 (4/4) | −2.59 (4/4) | −1.62 | toward | Men about 0 |
| 11 | Career matches: `pp__elo_N_a-b` (U-022) | yes | −5.08 (4/4) | −2.39 (4/4) | −1.90 (2/4) | −1.46 | toward | Mostly age |
| 12 | `alt__surface_first` (U-131, replaced) | yes | −4.77 (4/4) | −2.20 (3/4) | −1.51 | −2.77 | toward | A repair question |
| 13 | Women's qualifier form: `fi__B-INFO__info2_qform` (U-276) | no | +2.65 (4/4) | +2.13 (4/4) | — | +1.44 | toward | Rare |
| 14 | Men's height prior: `fi__B7__f07_height_prior` (U-247) | no | +2.54 (4/4) | +3.11 (4/4) | — | +1.04 | against | Men only |
| 15 | Two-week serve points won: `ad__adjperf_spw_decayed` (U-097) | yes | +4.17 (4/4) | +2.94 (4/4) | +0.34 (3/4) | +3.03 | toward | R² 0.93; rebuild first |

*Suggestion:* use the first five areas as the lead groups: calendar effort, venue × serve, the status axis (one bipolar group from its unseen columns), recent load, and conversion luck.
* All five are unseen on 2025–26, all are distinct in the joint reading, and the model does not use any of them.
* Rust (row 7) is the strongest alternative if the confirmation is on Look B only.

## 6. For the lead (observed in the harness)

* `load_frame()` filters on the tournament date, so it returns 136 season-2025 matches with their result, some played in January 2025. No lens uses them and this scan drops them, but filtering on `season` would make the blinding exact.
* The input count is 48, not 49.
* `redundancy()` reads about 0 for context columns by construction.
* `move_lens` raises where a column is absent from one tour; `pool_scan.py` falls back to the move lens tour by tour.

**Process record.** I fixed the design, rule and controls before the full run. Three things came after seeing results: the unstable threshold, set after the placebos; the near-context flag, set after seeing B-LEVER `s1`; and the joint list.

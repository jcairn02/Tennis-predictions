# Near misses: candidates for a future feature-selection study

7 October 2026 · Written after the study ([README](README.md)) on the owner's request: the members that came close (|z| ≥ 1) and might do better in a model built from scratch than as additions to today's 58 inputs. Every number is read from the screen's saved outputs (`data/studies/feature_interactions/hypotheses/screen_results.csv`, `descriptive_results.csv`, `known_null_results.csv`, `exploratory_binj_members.csv`). No new result was computed.

**Keys.**
* **z** is the screen's joint z on 2014–2024, **oriented: positive = the member's declared direction**.
* "Model" means tested beyond the current best's own forecast, which was the gating test. "Price" means tested beyond the closing price only (the owner's ranking lens). The price lens is the closer guide to how a feature would fare in a model built from scratch on the price.
* z₁ is 2014–2021, z₂ 2022–2024.
* For Wald blocks the z is the one-sided equivalent of the joint p.

**Read this list with its base rate.** Under no effect at all, about a third of 34 tests would reach |z| ≥ 1 by chance, about 11 members (a little more with two bases). Fifteen did on at least one base (a Wald block that showed −1.16 on the price, B-RECAL, is a strong null, not a near miss), so the list is a pool to select from, not evidence. Only members with |z| ≳ 2.5 or a coherent mechanism stand out.

**What is still clean.** Only B-INJ was opened on 2025–2026. Nothing else here has been scored on those seasons, so 2025–2026 stays a valid test set for any of them, under a new pre-registration chosen on 2014–2024 alone. *Update, 7 Oct 2026: I-084 (with the Elo sum as a TabPFN input) has since been opened there too, by the [pair-strength study](../pair_strength/README.md); not confirmed.*

## Tier A: strong signal, |z| ≥ 2.5

| Candidate | What it is | z model / price | z₁ / z₂ (model) | Why it did not get there | Built from scratch |
|---|---|---|---|---|---|
| **I-043 rust** (B-INJ's core) | a break of six weeks or more (mostly the off-season), fading over the matches since the return (half-weight after about 1.4 matches); stronger past age 28, after a retirement or walkover given just before the break, or with a protected ranking | +4.05 / +3.91 | +3.89 / +1.44 | it passed the screen (as B-INJ, +3.99). On 2025–2026 it tied, leaning worse; TabPFN used only 39% of it as a column | a raw input: days since the last match and matches since the return, separately, with age, so a model can find its own shape. B-INJ's other two members diluted it |
| **I-084 pair prominence × forecast**, **reversed** | how much stronger or weaker the pair is overall (A's Elo + B's), as a modulator of the forecast's steepness | **−2.98 / −3.12** (against the declared +) | −2.38 / −1.82 | registered one-sided in the other direction | a symmetric input (A + B Elo) beside the price, or a calibration slope by pair strength: the forecast is too steep for strong pairs and too flat for weak ones (inferred). See below. **Since tested:** the [pair-strength study](../pair_strength/README.md)'s one-shot 2025–2026 test confirmed neither form (ties), and the holdout is now used |
| **B11's On member** | matches the player has already played at this event (on-site rhythm), A − B | +3.29 / +3.03 (descriptive) | +2.63 / +1.99 | it was registered only inside B11 (+1.97), whose two interaction members are null, so the block diluted it | a raw input. It is a main effect, not an interaction, and is not among the 58 inputs (`sets_14d` counts sets, not rounds at this event) |
| **B-VENUE venue pace × serve** (I-072) | the venue's pace, estimated leak-free from its earlier editions' aces, times the server's ace offence: fast courts amplify the bigger server's edge | +2.50 / **+2.72** | +2.13 / +1.32 | BH q 0.15 on the model; **eligible on the price lens** (q 0.075), which was reported, not gated | venue pace as a symmetric context input beside the per-player ace and serve ratings, letting TabPFN form the product |
| **C-1 Pinnacle minus average** (descriptive) | Pinnacle's de-vigged log-odds minus the average close's | +2.98 / +3.05 | +2.41 / +1.76 | not a member: a pre-declared diagnostic | **caution**: market-internal, an artefact of the average close. It would help a model benchmarked on the average, not one betting at Polymarket, which is as sharp as Pinnacle. Use it only as an uncertainty input, not a direction |
| **KN-TTTLOGIT** (a known-null placebo) | the decided TrueSkill Through Time log-odds, beyond the model | −2.53 (two-sided) | −1.32 / −2.60 | a placebo by design, outside the family | a from-scratch model may weight the ratings differently. The negative sign says the 58 inputs already over-carry rating information (inferred). Test which rating to keep, not to add |

## Tier B: 2 ≤ |z| < 2.5

| Candidate | What it is | z model / price | z₁ / z₂ | Why not | Built from scratch |
|---|---|---|---|---|---|
| **B-MOTIV calendar effort** (I-089, I-090) | top-20 players at 250 and 500 events in the week before a Slam main draw (effort saving), and a post-Slam letdown: a Slam quarter-final or better in the previous 21 days (`Δpost`) | +2.27 / +2.31 | +2.39 / +0.49 | failed replication (z₂ below 0.67) | the two members as separate indicators; the effect may have changed with the 2023 Masters calendar |
| **B-OVERREACT over-reaction to recent results** (I-025, I-085, I-086, I-091) | conversion luck (results beyond the points earned); the favourite's price drift; flattering last-round scorelines; raw head-to-head of three or more meetings | +2.13 / +2.27 | +1.64 / +1.38 | passed filter and replication; q 0.23, too weak for the family | four different mechanisms in one sum; test them one by one (none was decomposed) |

## Tier C: 1 ≤ |z| < 2

| Candidate | What it is | z model / price | z₁ / z₂ | Why not | Built from scratch |
|---|---|---|---|---|---|
| **B11 on-site rhythm** (block) | On, plus acclimatisation × how new the conditions are (I-075), plus event rhythm against a cold start (I-076) | +1.97 / +1.78 | +1.35 / +1.54 | q 0.23; the signal is the On member (Tier A); I-075 +0.10 and I-076 +0.99 | keep On; I-076 (+0.99) is borderline |
| **B-STATE past fatigue** (BOD-C1) | the two-week form read through recent fatigue: tired players' last two weeks look like decline | +1.79 / +1.52 | +0.87 / +1.93 | failed the filter (z₁ below 1) | a fatigue-adjusted two-week form, replacing the raw `form_*` inputs rather than adding to them |
| **H-S2 the levels arm** (TabPFN) | both players' sums (A + B) of 17 inputs as context: 14 surface-IOS offence/defence, Elo, age, sets in 14 days | +1.73 (model) | +1.37 / +1.05 | q 0.23 | the most direct "built from scratch" test: give TabPFN levels as well as differences. Worth repeating with fewer, chosen sums (the serve-points-won sums, Elo) |
| **I-036 obscurity × forecast**, **reversed** | the pair's worse ranking (max log rank) as a modulator of steepness | −1.65 / −1.37 (against +) | −1.36 / −0.92 | fitted jointly with I-084 (correlation −0.70), so the two compete | one pair-strength modulator, not two |
| **B9a constitution × load** (I-024, I-058, I-061) | height × fatigue and height × age; recovery as a player trait; the season's odometer × age late in the year | +1.48 / +1.15 | +0.10 / +2.52 | failed the filter: nothing in 2014–2021, strong in 2022–2024 | look for a change after 2021 (calendar, balls); the late-season odometer is the likeliest member |
| **I-053 age × recovery debt** | fatigue over the last days times age above 26, within one player | +1.29 / +1.39 | +1.71 / −0.26 | failed replication | the brief's own example; as raw per-player age and load (pairs) it could be formed by TabPFN itself |
| **B-ANCHOR artefacts of the average**, **reversed** (I-037, I-038) | book dispersion as uncertainty; best-price skew (steam or shading) | −1.34 / −1.39 (against +) | −1.40 / −0.31 | registered direction wrong; [A]-type | market-internal; only for a model benchmarked on the average |
| **B-AGE age-dependent trust in recent form** (I-070) | whether a young player's recent form should outweigh the long-memory profile: (short − long) × an age curve | +1.09 / +1.24 | +1.32 / −0.01 | failed replication | the form-minus-profile gap and age as separate inputs |
| **B3 second-serve style** (Wald; I-016, I-022) | risky second servers against strong second-serve returners; kick second serves against short returners | 0.52 / **1.24** (one-sided equivalents) | – | not significant on the model; close on the price lens | per-player second-serve risk and return, plus height, as raw pairs |
| **B6 transient uncertainty** (I-033, BOD-L2, U_rest) | short against long memory disagreement (flux); the pair's distance from stable career ages; a U-shape of rest and fatigue | +1.13 / +1.13 | +1.33 / +0.03 | failed replication | symmetric uncertainty inputs (flux, age distance) as context |
| **I-045 within-event serve decay** (a B-INJ member) | the player's first-serve numbers falling across this event's matches | +1.56 / +1.60 (exploratory) | +1.21 / +0.99 | inside B-INJ, which was not confirmed | exposed to the 2025–2026 first-serve recording fault; test only on clean data |

## Tier D: one strong window only, joint |z| below 1

| Candidate | What it is | z₁ / z₂ (model) | Note |
|---|---|---|---|
| **B7 evidence and staleness weighting** (I-023, I-031, I-032, I-048) | height as the serve prior for thin histories; re-anchoring two-week form on the long-memory level; serve-point IOS by its evidence; a stale surface profile | **−0.97 / +2.85** | strong only in 2022–2024: a change after 2021, or chance |
| **B-CLUTCH non-iid scoring skill** (I-026) | big-point return skill × how scarce break points are in the pair | +1.48 / −0.72 | did not replicate |
| **B-FLB the price's favourite–longshot slope** (Lahvička) | steeper prices after the first round, and at Slams and the Finals | +1.37 / −0.37 | did not replicate; I-084 (pair strength) may be the better form of the same idea |
| **B-REPUTE reputation anchoring** (I-071, I-083, I-055) | rank lag × career trajectory; the fallen-star premium; the favourite's hidden fatigue | −1.28 / +1.78 (oriented) | the two windows disagree in sign |
| **I-008 the composed serve-point profile** | the surface IOS composed through the point model, its part not spanned by the 58 inputs | +1.07 / −0.41 | the highest-weighted idea; did not replicate |

## What "pair prominence × the forecast, reversed" means (I-084)

> **Corrected later on 7 Oct 2026.** The size quoted below is overstated, and the lead has since been tested once on 2025–2026 without confirmation. See the last bullet and the [pair-strength study](../pair_strength/README.md). The rest is the original note, kept as written.

* **The feature.** The pair's combined strength (A's overall Elo plus B's, standardised; it is the same whichever player is A) multiplied by the current best's forecast in log-odds. Its coefficient says whether the forecast should be steeper or flatter for stronger or weaker pairs.
* **What was registered.** The mathematics lens predicted that prominent pairs are better known, so the forecast should be steeper for them. It was tested one-sided in that direction.
* **What came out.**
  * The opposite, and clearly: z −2.38 on 2014–2021 and −1.82 on 2022–2024.
  * Beyond the closing price alone it is the same, z −3.12, so the price shows it too.
  * Per standard deviation of pair strength, the best multiplier on the model's log-odds falls by about 0.073 (from about 0.90). For a match the model calibrates to 70% for the favourite:
    * two strong players (+1.5 SD) are better forecast at about **67.8%**;
    * two weak players (−1.5 SD) at about **72.1%**.
  * Favourites among strong pairs win a little less often than forecast, and among weak pairs a little more.
* **Why it is a lead, not a finding.**
  * A reversed direction was never registered, so the multiplicity control does not cover it.
  * Among 34 tests, the chance that at least one shows |z| ≥ 2.98 in some direction by chance is about 9%.
  * Two things raise its prior. It agrees in both windows and on both bases. It is the mirror image of the best-measured market bias in the literature, Lahvička's favourite–longshot bias, strongest when both players are outside the top 50 (favourites underpriced in weak pairs).
* **The clean test.** Pre-register "the forecast's slope falls with pair strength" (the reversed I-084, one symmetric pair-strength modulator, I-036 folded in) on 2014–2024's evidence alone, and test it once on 2025–2026. Nothing about it has been looked at there.
* **Done, 7 Oct 2026 ([pair-strength study](../pair_strength/README.md)).** Tested once on 2025–2026 with the Elo sum alone, together with a TabPFN arm given that sum as an input (Holm over the two). Neither is confirmed: b +0.022 [−0.030, +0.074]; the arm −0.07 [−0.29, +0.16] mLL (positive = the arm better). Measured alone on 2014–2024, the pattern is about a third of the size quoted above, and it sits mostly in the weakest pairs. The 67.8% / 72.1% example came from the screen's fit, which also held I-036 (correlation −0.70), and that inflated both; alone, a 70% forecast is better at about 69.4% for strong pairs and 70.9% for weak ones. **2025–2026 is no longer clean for I-084 or the Elo sum.**

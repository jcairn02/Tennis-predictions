# Withdrawn, set aside or not proposed by their own originators

Part of the [master list](../master_list.md). These 20 ideas were closed by the brainstormer who raised them, not by an auditor. Each keeps the originator's stated reason, condensed, so the auditors can confirm the closure or revive the idea (any brainstormer may also rebut, critique C6). IDs W-01 … W-20 are bookkeeping labels only. The body-and-schedule lens closed none of its own ideas.

## Mechanics: "considered and set aside" ([source](../round0/ideas_mechanics.md#considered-and-set-aside))

| ID | Idea | Originator's reason (condensed) | Related live rows |
|---|---|---|---|
| W-01 | A left-hander's ad-court slice as a big-point bonus | Killed by the iid identity (observed): deuce and ad courts each carry exactly half of a game's sensitivity; a ±2-point court split moves the hold rate by at most 0.0003. What remains is an average effect | I-021 |
| W-02 | Attrition driven by serve dominance | Killed (observed): expected points depend on closeness, not dominance (an even best-of-three match lasts 164–166 points at serve rates 0.56–0.70) | I-066 |
| W-03 | First serves under pressure × second-serve return | Bounded: a 3-point drop in first serves landed on pressure points moves the hold rate by about 0.3 points at most | I-014 |
| W-04 | Style contrast at equal strength and dominance | Exactly zero under the additive iid model; real style effects need MEC-04, -06, -07, -09 or -10 | I-017 tests this same null as a structural check against the price |
| W-05 | Height × height ("tall against short") | Identically zero after antisymmetrisation; only the asymmetric version can carry a sign | I-022 |
| W-06 | Rally-length matchups (first strike against grinder) | Tested in the shot-level study, nothing given the odds; no new mechanism | I-065, I-066 |
| W-07 | Serving first in a set or match | Unknown before the toss; under iid the set probability does not depend on it (Stage 2) | – |
| W-08 | Weather, heat, wind, day or night sessions | No archived forecasts or start times are held | I-067 proposes heat, parked if the data are unavailable |
| W-09 | Returners adapting to big servers over best of five | The late-match decline is not a player trait (UFC-ideas Stage C): no stable quantity to cross | – |

## Mathematics: "kill by calculation" (seven of its 27 ideas)

| ID | Idea | Originator's reason (condensed, computed) | Related live rows |
|---|---|---|---|
| W-10 | [MAT-C6](../round0/ideas_mathematics.md#mat-c6--the-deciding-set-rule-as-an-input-kill-by-calculation) · the Slams' deciding-set rule as context | Against a 7-point tiebreak at 6-6, P(match) moves 0.04–0.32 pp (≤ 0.019 logit), only in matches reaching a deciding set: bound < 0.01 mLL | I-006 |
| W-11 | [MAT-C7](../round0/ideas_mathematics.md#mat-c7--hold-versus-points-scale-interaction-kill-by-calculation) · hold-versus-points scale interaction | d logit hold / d logit p is 2.50–2.99 and within ±5% of 2.65 over the men's range: a linear combination suffices | I-009 |
| W-12 | [MAT-S3](../round0/ideas_mathematics.md#mat-s3--format--the-models-adjustment-kill-by-calculation) · best of five × the profile's adjustment | κ = 0.10–0.25 on the 20% of men's rows at Bo5 gives ≈ 0.002–0.013 mLL; and best_of is already an input | I-006, I-063, I-007 |
| W-13 | [MAT-U3](../round0/ideas_mathematics.md#mat-u3--posterior-variance-attenuation-of-the-price-kill-by-calculation) · posterior-variance attenuation of the price | Gap posterior variance median 0.0135 (men), 0.0116 (women), nearly uniform and small beside day noise (0.075): slope modulation RMS 0.7–1.2%, ≤ 0.01 mLL (≤ 0.025 without day noise) | I-032 (evidence counts, checked the same way first) |
| W-14 | [MAT-U5](../round0/ideas_mathematics.md#mat-u5--measurement-noise-in-the-average-close-kill-by-calculation) · measurement noise in the average close | Average and Pinnacle log-odds differ by SD 0.114 / 0.089; even if half were noise, the average's reliability is ≥ 0.994: < 0.001 mLL. Pinnacle as a second price is a main effect, left to the market lens | I-039, I-037 |
| W-15 | [MAT-M4](../round0/ideas_mathematics.md#mat-m4--odds--overround-kill-by-calculation-as-an-interaction) · odds × overround | The overround is nearly uniform (SD ≈ 0.5 pp), so its part of the slope varies by RMS 0.6–0.9%: ≤ 0.007 mLL. Killed as an interaction; suggestion kept: a power or Shin de-vig as a more faithful odds input | I-035 (same modulator, convex rather than linear function of the price) |
| W-16 | [MAT-M6](../round0/ideas_mathematics.md#mat-m6--adjustment--lopsidedness-kill-by-calculation) · adjustment × lopsidedness | It only rescales the model's adjustment (worth ≈ κ² mLL, κ ≤ 0.3) on ≈ 6% of men's matches: < 0.01 mLL; and `odds_logit` is an input | I-081 (same form with N in place of the adjustment) |

## Market: "not proposed, and why" ([source](../round0/ideas_market.md#not-proposed-and-why))

| ID | Idea | Originator's reason (condensed) | Related live rows |
|---|---|---|---|
| W-17 | Features from Polymarket or Betfair (early prices, volume as attention, account flow) | They exist only for 2025–2026, so rule 1 makes them impossible to discover; revisit once seasons beyond the test exist | I-080, I-087 |
| W-18 | Cross-book standard deviation over five books (B365, EX, LB, PS, SJ) | Only 2010–2018 have them, so the 2025–2026 test could not use it; MKT-14's arbitrage measure works in every season | I-037 |
| W-19 | Main effects already tested against the close (surface Elo, surface IOS, TTT, load, conversion luck, home country and entry types alone) | Only their interactions appear in the list | I-025 proposes a broader short-memory luck index as a main effect; I-051, I-052 split load |
| W-20 | Dead rubbers at the Tour Finals | About 2–4 matches a season: too few | – |

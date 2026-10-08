# Stage A: the rating systems, tuned and frozen

**Status: built 2 Oct 2026.** A study stage, not a decision. The Brief is in the [README](README.md); the report section is Stage A in [report.html](report.html). Every number comes from `data/studies/rating_systems/stageA_summary.json` and `stageA_tuning.csv` unless another file is named.

Labels: **observed** is measured on the data, **inferred** is a reading of measurements, **suggestion** is a proposal.

## In short

* **Observed. In the tuning years (2013–2018), TrueSkill Through Time is the best rating, by about 2.6 milli-log-loss over surface Elo on both tours.** Log loss on the evaluation matches of 2013–2018, the matches every system's constants were chosen on (surface Elo 0.58686 for the men, 0.59912 for the women):

  | System | Men | vs Elo | Women | vs Elo |
  |---|---:|---:|---:|---:|
  | TrueSkill Through Time | 0.58421 | +2.65 | 0.59659 | +2.53 |
  | Glicko with correlated surfaces | 0.58620 | +0.67 | 0.59727 | +1.85 |
  | TrueSkill with correlated surfaces | 0.58779 | −0.93 | 0.59758 | +1.54 |
  | Glicko-2, match by match | 0.58696 | −0.09 | 0.59861 | +0.52 |
  | Glicko-1, match by match | 0.58697 | −0.10 | 0.59860 | +0.52 |
  | TrueSkill | 0.58845 | −1.59 | 0.59842 | +0.70 |
  | Glicko-2, weekly rating periods | 0.59282 | −5.96 | 0.60127 | −2.15 |
  | Glicko-1, weekly rating periods | 0.59287 | −6.01 | 0.60127 | −2.15 |

  "vs Elo" is milli-log-loss better (+) or worse (−) than surface Elo. Out-of-sample results are in [Stage B](stageB.md); they hold.
* **Observed. Glicko-2's volatility adds nothing.** Glicko-2 and Glicko-1 differ by at most 0.05 milli-log-loss in every pairing above. The "2" of Glicko-2 is not what matters here.
* **Observed. Glicko-2 run as Glickman specifies it is worse than Elo,** with a tournament week as the rating period: by 5.96 (men) and 2.15 (women) in these years. Run match by match, it ties Elo. Why: [Stage B](stageB.md#why-glicko-2-with-weekly-rating-periods-loses).
* **Observed. Every constant ended inside the range tried, but one.** TTT's smoothing window for the men reached the largest value tried, 416 weeks, after three widenings. The step from 208 weeks gained 0.12 milli-log-loss, so a longer window would add little. 1,160 settings were scored in all (`stageA_tuning.csv`).
* **Observed. Every probe is clean.** Across 96 cuts over the eight systems, 0 of 4,979,008 protected pre-match values moved; the leaky control moved 969. Every tuning pass equals its full pass's first rows exactly.
* **Observed. The sanity check reads right.** The ten highest-rated players at the end of the table (those with at least 30 rated matches) are, for every system kept: Sinner, Alcaraz, Zverev, Djokovic, Fils…; and Sabalenka, Rybakina, Gauff, Pegula, Swiatek…

## The frozen constants

| System | Men | Women |
|---|---|---|
| TrueSkill Through Time | σ0 1.125, γ 0.4 per √year, window 416 weeks; surface weight 0.35 | σ0 1.5, γ 0.5, window 104 weeks; surface weight 0.30 |
| Glicko with correlated surfaces | RD0 600, σ 0.07 per week, ρ 0.99 | RD0 700, σ 0.08, ρ 0.995 |
| TrueSkill with correlated surfaces | σ0 2.0, γ 0.5, ρ 0.98 | σ0 2.5, γ 0.5, ρ 0.99 |
| Glicko-2, match by match | RD0 600, σ0 0.07, τ 1.0; surface weight 0.30 | RD0 700, σ0 0.07, τ 1.0; surface weight 0.20 |
| Glicko-1, match by match | RD0 600, σ 0.07; surface weight 0.30 | RD0 700, σ 0.07; surface weight 0.20 |
| TrueSkill | σ0 2.0, τ 0.01, γ 0.4; surface weight 0.30 | σ0 3.0, τ 0.02, γ 0.4; surface weight 0.25 |
| Glicko-2, weekly periods | RD0 700, σ0 0.07, τ 1.67; surface weight 0.25 | RD0 700, σ0 0.07, τ 1.0; surface weight 0.20 |
| Glicko-1, weekly periods | RD0 700, σ 0.07; surface weight 0.25 | RD0 700, σ 0.07; surface weight 0.20 |

**Observed. What the constants say.**

* **The drift is time's, not the match's.** TrueSkill's per-match drift τ is near zero (0.01–0.02 against β = 1), and its per-year drift γ does the work. Every system wants a player's uncertainty to grow with time away, not with matches played.
* **Surface blends are worth about as much as for Elo.** For the systems with a separate surface rating, the blend gains 2.3 to 3.7 milli-log-loss for the men and 1.5 to 3.4 for the women in the tuning years (`summary_results.json`, `surface_blend_gain_milli`). Stage 1 found 3.6 and 2.8 for Elo.
* **Correlated surfaces.**
  * **Observed.** The constants keep a newcomer's surface skills highly correlated (ρ 0.98–0.995).
  * **Inferred.** Because a newcomer's overall uncertainty is large, that still leaves room for a real surface deviation: RD0 × √(1 − ρ) is 60 rating points for the men's Glicko and 49 for the women's (`surface_deviation_points`).

**The tuning surfaces** (`stageA_summary.json`, `flatness`; milli-log-loss above each system's best, the other constants free):

* **TTT, men.** The window: 26 weeks +2.26, 52 weeks +1.34, 104 weeks +0.54, 208 weeks +0.12. γ: 0.3 +1.25, 0.625 +1.06.
* **TTT, women.** The window: 26 weeks +0.32, 208 weeks +0.03.
* **Glicko with correlated surfaces.** ρ: 0.97 is +0.57 (men) and +1.34 (women); 0.995 is +0.24 (men).

## The two-week events (the overlap sensitivity)

**The concern.** The time rule reads a tournament's start date as its week. A Grand Slam's second week therefore counts as known once the start date's week is over, although it is played during the next week's events. The feature-alpha audit's repairs (2 Oct 2026) removed this overlap from the features.

* **Filtering ratings are not exposed.** Elo, Glicko, TrueSkill and the correlated ratings move only with the player's own matches, so they cannot pass those later rounds to another player.
* **TrueSkill Through Time is.** Its smoothing re-scores opponents, so it can.

**The check.** `stageA_ttt_hold.py` reruns TTT at its frozen constants (not retuned) with every event that has a round of 128 held back:

* The held events are 114 per tour: the Grand Slams and the 96-draw 1000s, 21,812 men's and 20,491 women's rating-moving matches.
* Each joins the smoothed model only at the first date at least 14 days after its start date.
* This is conservative, because it also withholds the event's first week.

**Observed.** In the tuning years the held version scores 0.58435 (men) and 0.59659 (women), against 0.58421 and 0.59659 for TTT. Its out-of-sample record is in [Stage B](stageB.md). **Inferred:** the overlap is not where TTT's gain comes from.

## The systems

All eight are built from wins and losses alone, over every singles match from 2010 at every level (466,115 men's and 406,589 women's matches; ITF, team events and qualifying included), so players arriving from the lower levels bring ratings. Walkovers never move ratings; retirements do (the owner's rule for Elo). Newcomers start at the scale's mean (1500), as Elo's do.

| System | What it is |
|---|---|
| **Glicko-2, weekly periods** (`glicko2`) | Glickman's algorithm as he specifies it (glicko2.pdf, 2022 revision), with a tournament date as the rating period. Each player has a rating μ, a deviation φ (RD / 173.7178) and a volatility σ. A player's games of a week are scored together, each against the opponent's rating at the start of the week: v, Δ, the new volatility by the Illinois iteration, then φ′ and μ′. A week without a match adds σ² to φ² (Glickman's rule); φ never exceeds the newcomer's φ0. Within an event, a player's rating for round r is the period update from their earlier rounds only. |
| **Glicko-1, weekly** (`glicko1`) | The same with the volatility held at σ0 (σ0 then plays the part of Glicko-1's c). |
| **Glicko-2, match by match** (`glicko2m`) | Each round a player plays is its own rating period, and the drift is by elapsed time. The first period of a week carries kσ², with k the days since the player's last period divided by 7; later rounds of the event carry none. Glickman's step 5 generalises directly: the drift term eˣ of his f(x) becomes k·eˣ (k = 1 is his). |
| **Glicko-1, match by match** (`glicko1m`) | The same with the volatility fixed. |
| **TrueSkill** (`trueskill`) | Herbrich, Minka and Graepel's two-player update, no draws, performance noise β = 1 (it fixes the scale). The variance grows by τ² per match and by γ² per year since the player's last period. The forecast is the probit P = Φ((μA − μB) / √(2 + σA² + σB²)). |
| **Correlated surfaces, Glicko** (`glicko_cs`) | One skill per surface (hard, clay, grass, carpet), jointly Gaussian. A newcomer's surfaces are correlated ρ, and the drift has the same form. A match observes the two players' skills on its surface; Glicko's (Kalman) step updates them, and the other surfaces move through the covariance by exact Gaussian conditioning. With ρ = 1 it is Glicko-1 match by match (tested). The Bayesian form of the surface blend, and the literature's most consistent extension (Ingram 2021; Gorgi et al. 2019). |
| **Correlated surfaces, TrueSkill** (`trueskill_cs`) | The same with TrueSkill's update; with ρ = 1 it is TrueSkill with τ = 0 (tested). |
| **TrueSkill Through Time** (`ttt`) | Dangauthier et al. 2008, as implemented by Landfried and Mocskos 2025, run causally. A skill node per player and week, linked by a Gaussian drift of γ² per year, solved by expectation propagation. After each finished week its matches join the model as a batch, then one backward and one forward sweep over the trailing window re-scores every game in it against the current estimates. An old win is thereby credited at what the opponent later proved to be worth. Within a week, TrueSkill's update round by round. |

Every system except the correlated ones also keeps one rating per surface, moved only by matches on it, with the same constants. The forecast blends the two as Stage 1's surface Elo does: the means (1 − w) overall + w surface, and the uncertainty the same way on the variance scale.

## The time rule

A player's rating for a match is their rating at the start of its week (tournament date) plus what their earlier rounds of the same event added. A round's results are held back until the player's next round of that event, so a round robin's matches never see each other. They reach the player's other events only when the week is over, so two events of one week never see each other. This is `stage1_baselines.elo_pass`'s rule.

* **Combining.** Round robins and several events of one week are combined as each system's mathematics says. For Glicko with weekly periods, one period holds all of a player's games of the week. For the Gaussian systems, the matches' messages are multiplied (natural parameters added).
* **TTT.** It adds a week to the model only once the week is over.

## Tuning

As Stage 1 tuned Elo:

* **Constants.** Chosen on the log loss of the **overall** rating's forecast over the evaluation matches of 2013–2018. 2010–2012 warm up, and the history read stops at the end of 2018.
* **Surface weight.** Chosen next, 0 to 1 in steps of 0.05, with the constants fixed.
* **Then frozen.**

**The grids** were centred on a first exploration of the same years (`stageA_summary.json`, `grids`). Where a best value lay on an edge of the values tried, the grid was widened past it in up to three rounds:

* geometrically for most constants;
* in 1 − ρ for the correlation, so it never reaches 1;
* never past a natural bound (TrueSkill's τ or γ at 0).

`stageA_tuning.csv` records every setting with the round that added it. The five original systems' settings were scored in a first run and read back (`--reuse-grid`), since a pass is deterministic.

## Checks and tests

* **Tests** (`test/rating_systems/test_ratings.py`):
  * Glicko-2 reproduces Glickman's worked example: r′ 1464.06, RD′ 151.52, σ′ 0.05999. The intermediate v and Δ match his printed values, which come from rounded intermediates.
  * Glicko-1 reproduces his Glicko example: r′ 1464, RD′ 151.4.
  * The volatility iteration finds the root of its equation (against Brent's method), for k = 1 and for any k.
  * TrueSkill's update equals the moments of the exact posterior integrated numerically. Default TrueSkill gives 29.205 / 7.195 for a win without a draw margin.
  * TTT reproduces Landfried and Mocskos's published one-on-one example: the filtered N(3.339, 4.985), N(0.059, 4.218) and N(−2.688, 3.779), then N(0, 2.395) for everyone after convergence.
  * The correlated model at ρ = 1 equals TrueSkill and Glicko-1 match by match, to 1e-10. A result on one surface moves another by ρ times as much.
  * With one match per player per week, the passes equal plain sequential Glicko-2 and TrueSkill.
  * Every pre-match value of random histories (round robins, overlapping events, retirements, walkovers, unknown surfaces) equals a fresh pass over only what the rule lets the match see, for every system and both components.
* **Stage logic tests** (`test/rating_systems/test_stages.py`): the widening, the grid's read-back, the comparison block, the ladder's references.
* **The probe cut by date, event and round** (`stage1_baselines.probe_by_round`), on the matches from 2024 with the history inside the slice, every system. At each cut every result the cut may not see is redrawn, and the pass re-run; the pre-match values of the matches it may see must not move. A control that runs each week backwards (so early rounds see later ones) must move them.
* **The tuning pass equals the full pass's first rows**, to the last bit.

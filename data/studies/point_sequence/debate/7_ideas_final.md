# Brainstormer: final take (6 Oct 2026)

**Labels.** Observed = from the gate results or checked read-only. Inferred = my arithmetic.

## 1. Surviving leads, ranked

1. **Medical events → next-match non-completion.** *Novel combination; get more data.*
   * A treatment in the previous logged match raises the risk of retiring or withdrawing next match (observed):
     * risk ratio 2.39 [1.48, 3.84] in discovery, 2.27 [1.69, 3.06] in replication;
     * 2.7–3.4 when the next match is 1–2 days later.
   * Combine it with a settlement-aware P(advance). The men need a medical-event source; none is held.
2. **Within-match dynamics at population level** (set-to-set swing, game dispersion beyond the replay). *In-play / other market.*
   * They are not player traits, so they are useless pre-match.
   * They are what an iid in-play price would miss. Provisional until the replay is fixed (point 3).
3. **Men's S4** (within-set serve dispersion). *In-play / other market* (volatility for totals and handicaps), only if it survives a corrected replay. Otherwise close.
4. **Close:**
   * the S1–S3 and S5 momentum traits;
   * the women's anomaly (box-score error);
   * the women's fade markers;
   * my I1b test (the edge is uniform, so it is moot), and my states-over-traits thesis;
   * finishing-form carry-over. It fails its registration. Even if real, about 1 point of win chance per SD, in in-tournament matches only, is about 0.1 mLL (inferred; positive = with the feature better), below anything detectable or bettable.

## 2. Best recommendation: lead 1

**Cheapest next step, about an hour:**
* Read Polymarket's and the odds source's settlement rules for retirements and walkovers.
* Mind the frame: it includes retirements (observed: 1,897 of 63,737 rows, 3.0%) but no walkovers.

**Then:**
* Pre-register one settlement-aware adjustment for the shared 2025–26 final test, with its size stated in advance.
* Expected size (inferred): about −0.03 to −0.09 log-odds per treated player (negative = less likely to advance), about 1–2 points of win chance.
* That is an adjustment to the model's bets, not a standalone bet: at even odds it is below costs of about 3¢.
* Scope a men's medical-event source in parallel.

## 3. Possible mis-readings

* **The medical screen's ties are not a negative.** Its 95% interval half-widths of 0.18–0.24 log-odds are 3–8 times the effect the risk ratio implies. The screen could not tell that effect from zero.
* **S4 and the population-level dynamics rest on a replay the gates found mis-calibrated.**
  * The replay draws the two players independently, plays too many tie-breaks, and makes sets too alike.
  * S4 passes only at variance × 0.5, and it correlates −0.28 with hold rate. That looks like an artifact of how the replay models serve rates.
  * Rerun both with a frozen joint prior, or a permutation null within the match, before reading either.
* **The replication positive for carry-over is an unregistered second look.** Keep it closed.
* **The most actionable finding is a data fix:** mirrored WTA box scores feed the model's form inputs.

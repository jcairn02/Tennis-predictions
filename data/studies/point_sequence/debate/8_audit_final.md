# Final audit: the four gates

Positive = the feature or the model is better; "tie" when the 95% interval spans 0.

## 1. Are the verdicts right under their registrations?

* **Traits (item 1), 10 of 10 FAIL: correct.**
  * The deviations are logged. S4's exploration is labelled post hoc.
  * Over-claim: "within-match dynamics exist". Every replay variant makes sets too alike: set-1 against late-set correlation, real 0.27 against replays 0.34–0.46 (men, best of three); women 0.21 against 0.29–0.41. Real-minus-replay contrasts are therefore replay-dependent. Say "non-stationarity, unattributed".
* **Women's anomaly (item 4), FAIL: correct.**
  * Trait deviation D1 (a one-sided reading, after structure numbers were seen) **changed nothing**. The women's gap is −38.6 mLL [−45.3, −31.9], the opposite direction, and the men's control fails to cover 0 under V1, so the original rule fails too.
  * Do not read magnitudes: the WTA-log sample has lost its tie-break matches (0.09 tie-breaks per match).
* **Medical (item 2), mechanism PASS: correct as registered.** The pass rule was the cluster-Wald p with Holm; the permutation p was a reported placebo.
  * Discovery evidence is weaker than "Holm 0.0014" suggests: the permutation p is 0.048. The **replication** carries it: risk ratio 2.27 [1.69, 3.06].
  * Under-claim risk: a tied residual screen (−0.22 [−0.46, +0.02] then +0.07 log-odds per treated side, positive = treated side wins more than the model says) cannot refute mispricing. The implied effect is about −0.05 to −0.11 log-odds, below its resolution. Write "unresolved", not "priced in".
  * Walkovers usually void bets; only retirements matter for money.
* **Carry-over (item 3), FAIL: correct.** The file's re-creation leaves its body unverifiable, since no hash was recorded; its analysis log reports no deviation. Hash every registration before estimating from now on.

## 2. The men's S4 dispersion lead

**Do not pre-register it as a winner feature.** It is:
* below the margin at the primary depth: +0.074 [+0.010, +0.137], positive = real more reliable than replay, against a 0.10 margin;
* replay-dependent (it passes only at variance × 0.5), with a replay shown to be mis-calibrated;
* tied to serve strength (r −0.28 with hold rate).

It is most likely an artefact of de-noised rates interacting with the game-stopping rule. One cheap, outcome-free retest: an **exact null** that shuffles each server's points within the set and re-scores the games (no rate model). If it survives, it is a variance trait for totals and handicaps, not for the winner.

## 3. Carry-over

* **Honest label: inconclusive.** Discovery is a tie (+0.0038); replication is marginal (+0.0109 [+0.0003, +0.0216]); the pooled figure is unregistered. There is **no fade with rest**, which undercuts a form-state mechanism.
* If real, it is about 0.2 pp of serve points, about 1 pp of match chance: at most about 0.2 mLL. A 2025–26 arm is a guaranteed tie. **Do not spend the shared holdout on it.** At most, one serve-point Δ endpoint in the final battery.

## 4. Ranking for the owner

1. **Fix the data defects feeding the model.**
   * The mirrored WTA box scores (scan every match for side flips against the sequences, rebuild the form and IOS inputs).
   * The replay prior: joint draws, frozen.
   * The Infosys/SirGenkii table holes.
   * Recovery of WTA tie-break points.
   * Any use of `start` as a match day.

   Then **measure the 58-input model's edge**, which no fit has yet scored.
2. **Venue and price.** The edge is real and uniform: +0.55 [+0.05, +1.05] in 2015–21, +1.39 [+0.71, +2.06] in 2022–24, positive = model better. But early-versus-close betting was $0.00 per 100 matches, and it ties Polymarket's close. Where and how to bet now matters more than features.
3. **In-play and other markets.** The G2 price-only pilot, order-book recording, and a census of totals and handicaps.
4. **Novel combinations** (the feature-interactions study).
5. **More point data for pre-match winner features: last.** At full depth, the momentum and streak traits fail.

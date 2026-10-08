# Gate results (main session summary, 6 Oct 2026). Full tester reports in data/studies/point_sequence/*_prereg.md and *_results.*

Discovery ≤2021, replication 2022–24; 2025–26 untouched.

## I1 edge location (main session; fixed with `obs` match days)
Model (54-input walk-forward, prequentially recalibrated) vs recalibrated close, mLL, positive = model better:
discovery 2015–21 +0.55 [+0.05, +1.05]; replication 2022–24 +1.39 [+0.71, +2.06]. Six subgroup contrasts (first-at-event,
rest >7d vs ≤1d, previous deciding set, early vs late rounds, Slams vs others, men vs women): all ties after Holm in both
windows; 2022–24 "cold start" directions flip in discovery. Edge roughly uniform across previous-match states.

## Item 1 — momentum/streak traits at full depth: 10/10 FAIL (real − replay split-half r; Holm over 10)
Men 754 players, women 347 at ≥20 matches/half. S1 hold-after-break, S2 break-back, S3 point-to-point dependence,
S5 set-to-set swing: ties, ~0 in both tours. Placebo (hold after holding) on the replay.
Only lead: MEN's S4 (game-level serve-point dispersion within a set): Δ +0.074 [+0.010, +0.137] at ≥20/half (below the
0.10 margin), +0.225 [+0.135, +0.310] at ≥50/half (secondary); post hoc robust (strict, by source, by event, main tour
+0.30); r −0.28 with hold rate; within-set game-to-game, not set swings or court ends. Replay-dependent at ≥20 (passes
only with true-rate variance ×0.5). Women's S4 tie.
Population level: real > replay for set-to-set swing (men +0.053, women +0.036), game dispersion, hold after breaking
(+0.0065 holds/game): within-match dynamics exist, but players don't differ in them.
Calibration: no replay variant reproduces real between-set correlation (replays: sets too alike; the inherited
de-noising draws the two players independently, losing skill-gap covariance; too many tie-breaks).

## Item 4 — women's points-share anomaly: FAIL; it was box-score error
Women's box-score points share decides worse than the sequence's on the same matches (+30.4 mLL); mirrored Stage 0
women's box scores in events 2021-2028, 2021-2027 (and 2022-2030). Refit of Stage 2's women's table without the two 2021
events: log loss 0.1182 → 0.1049 vs replay 0.103. Predictability Stage 2's open question 7 is answered.

## Item 2 — WTA medical events: mechanism PASSES on one cell; result screen FAILS
TREATED (physio/medical treatment in previous logged match, ~6% of pairs) → next-match retirement or walkover-out:
risk ratio 2.39 [1.48, 3.84] discovery, 2.27 [1.69, 3.06] replication (4.3–4.5% vs 1.9%); Holm p 0.0014 (permutation
0.048); toilet-break control null; placebo centred on 1; concentrated in fresh pairs (won, next round 1–2 days later:
3.40 and 2.67). Next-match serve-point shift: tie (−0.48 / −0.04 pp). INJURY reason untestable (only on suspension
records). Women's fade markers (first-serve-in, DF, tempo): all ties.
Residual screen (main session, registered in its docstring): log-odds per treated side given the model: discovery −0.22
[−0.46, +0.02], replication +0.07 [−0.11, +0.25]; given the close: −0.21 / +0.09; all ties.

## Item 3 — finishing-form carry-over: FAIL (discovery ties)
Δ (forward minus reverse late-minus-early set residual effect on next-match serve points, log-odds per 10 pp):
discovery +0.0038 [−0.0030, +0.0107] tie; replication +0.0109 [+0.0003, +0.0216]; unregistered pool +0.0059
[+0.0002, +0.0117]. Replay and label-swap placebos fine. No fade with rest. Women's replication +0.0145 [+0.0006,
+0.028]. Size if real ≈ 0.2 pp serve points per SD ≈ 1 point of match-win chance at even odds.
Side: winners of t serve 0.4–0.5 pts better late than in set 1 vs ~0 in winner-conditioned replays (within-match).

## Data defects found
* Stage 0 mirrored box scores (WTA 2021-2027, 2021-2028, 2022-2030; 55 matches confirmed by two sources): feed the
  model's form inputs.
* shot_level AO table drops each game's last point; Sackmann strings skip 2016; Infosys/SirGenkii reused tables have
  holes (46%/28%) — men's Challengers 2021–24 nearly absent from the usable table; WTA logs: tie-break points "0-0"
  (68% of logged matches with a tie-break unusable → WTA-log population skewed to decisive matches).
* timing.parquet `start` is the tournament day; the match day is `obs` (the brief's instruction was wrong; fixed).
* stage2 `denoised_rates` prior is not frozen and draws players independently (replays mis-calibrated).

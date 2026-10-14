9 October 2026 · The lead's message for round 3 in the [lean review](../README.md)'s debate (the session that ran it) · **Verbatim below.**

---

Round 3 of the lean debate: I accept your joint test plan with three amendments; sign or object to each, then give a closing statement.

Accepted from your round 2, with concessions on my side: the cost-aware rule B·est + c_saved > 0 replaces my P(better) ≤ 0.2 rules (you are right that those ignore upkeep); the 24-hour reading is uninformative, not evidence against; men's no-odds residual is real (+0.19, P 0.94) though the wrong proxy; removal of ios_points_short rests on the drop-one test alone; your classification of stage 2 as best-of-K with an out-of-window-replicated signal (not "a pattern found in the scored seasons"), and the RE-posterior coefficient rule as a documented-flaw fix adopted on mechanism. Verified feasibility: Pinnacle's opening line is in data/studies/odds_sources/sources.parquet (p_ot20o, t_ot20o_ms, after_ot20o_min); the 2021 US Open failure is documented in odds_sources §2.

AMENDMENTS — sign or object:

A. Stage 2 inside T2 and T3 uses the DECIDED recipe (the current FE-shrunk b, as compare.py's walk_forward), refitted on each arm's own forecasts. The RE-posterior rule is not decided; T1 evaluates it. Otherwise the IOS readings would mix two changes.

B. T1's primary as a fixed difference, not a ratio. β_ref on 2019–24 is +0.030 [−0.020, +0.080]: its interval spans 0, so r = β_pf / β_ref is ill-conditioned if the realised denominator is small. Restate: d = β_pf − β_ref, the paired difference of the pooled information coefficients (men, 2019–24, same matches, same speed column, block bootstrap over four-week blocks). Rule: keep stage 2 live if d ≥ −0.015 (the Pinnacle-first base absorbs at most half of the documented 0.030); otherwise shadow until the sealed checkpoint. Alarm as you wrote it.

C. Reproduction check in T2: A0 is refitted to add the opening-line queries. Its close-fed ("td") predictions must equal the Pinnacle-first instance's existing fits for seeds 0–3 to machine precision before anything is scored; if they do not, stop and report. (The serve-speed study reproduced its base fits bit for bit the same way.)

Also noted, no change needed: the c values (0.05 for the profile, 0.06 for the whole IOS chain) are judgment calls. I accept them because the chain is a live dependency of every prediction run, the framework's class for which is ≈ 0.05. The owner's per-statistic thesis may weigh against dropping the profile; that is his call, and every outcome is a proposal.

Closing: (1) sign or object to A–C in one line each; (2) one short paragraph per part for the record, giving your final position, confidence, and the single strongest consideration on the other side. About 400 words. Save it as round3_reviewer.md.

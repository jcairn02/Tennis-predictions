# Training-window study: reading rules

Written 8 Oct 2026 at 12:20 PDT, while the fits ran and before `score.py` had produced any score. Only exp's stage-2 coefficients had been computed, to check them against the published ones; they matched exactly.

* **Primary.** Each lastN's two-stage forecast against the current model's (exp), both tours, 2020–2024, in mLL with the four-week-block interval plus the seeds' variance. A window **helps** only if:
  * its interval lies above 0;
  * it is not worse in 2024, the protocol's confirmation season;
  * it is not worse in either choosing era (2020–21, 2022–23).
* **Multiplicity.** Three windows are primary, so one interval clearing 0 by a hair is weak. It is reported as such.
* **The mechanism.**
  * lastN against randN at the same size answers "is recent data worth more than old data, row for row?"
  * randN against exp answers "what does the lost size cost?"
  * The realisation c against the recalibrated close tests the owner's account. If the learned move goes stale, a recent window should move c towards 1. Today it is about 1.3 against the average close (the close-drift study, stage 1).
* **The cheap alternative** (2p_all, 2p_recent: re-sizing exp's move away from the close without refitting) is secondary. It is read by the same rule as the primary.
* **Not changed after seeing the scores:** the arms, the seasons, the seeds, the calibration window, the stage-2 rule.

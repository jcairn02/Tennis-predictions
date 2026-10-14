# Agents weigh adoption suggestions with the adoption framework: guiding principles, not rules

**Decided by the owner on 9 October 2026.** Recorded the same day.

**The context.**
* **8 October.** The owner questioned labelling every comparison whose 95% interval spans 0 a "tie": "Im betting to make money here, not proving a vaccine works."
* **9 October.** The owner asked two independent agents to review the answer. The owner's guess: the evidence needed to call a change implementable "depends on how the change was hypothesized. EDA based on the past? domain intuiton? What is the cost of being wrong?" The reviews and the framework built from them are in [docs/studies/adoption_framework/](../studies/adoption_framework/README.md).

The owner's words on adopting it:

> "yes adopt the framework, but emphasize its a framework for guiding principles not a RULE."

## Decision

1. **Agents reason with the [adoption framework](../studies/adoption_framework/README.md)** when they suggest adopting or declining a change: new data, new inputs, variants, rebuilds. Its questions:
   * the target price, hour and matches;
   * how the idea arose;
   * what being wrong costs;
   * the shrunk, selection-corrected gain against that cost.

   It also sets checks to run before a suggestion, keeps three lanes apart (data fixes, parts, stakes), and asks for a ledger of adoptions made on a lean.
2. **It is a framework of guiding principles, not a rule.**
   * Its numbers are starting values for judgment: the spread of true effects τ, the cost bars, the default thresholds.
   * An agent may depart from it when a case calls for it, and says where and why.
   * Nothing in it decides by itself. Accepting a change stays the owner's call, as the [current-best-model decision](2026-10-08-current-best-model.md) already says.
3. **No comparison is called a "tie."**
   * Report the estimate, the interval and the direction key.
   * Say "better" or "worse" when the 95% interval clears 0; otherwise say "unresolved" and give P(better).
   * Give verdicts on the declared primary only. The framework's § 7 has the details.

## What it does not change

* **The procedures already decided:**
  * the [match clock](2026-10-05-match-timing.md) and its leak probe;
  * the frozen reference, its history check and the candidate comparison;
  * the [prediction runs](2026-10-08-prediction-run-box-scores.md).

  The framework guides how their results are read and turned into suggestions.
* **Earlier decisions stand** until the owner revisits them. Where the framework reads one differently, agents say so as a suggestion.

## Open

* **Fixed on 9 Oct 2026: `compare.py` counted seed noise twice.** A model compared with itself got ±0.087 mLL instead of 0. Its seed term is now paired by seed (`score.paired_stats`, `matched_seeds`), so a model compared with itself gets exactly 0 with a zero-width interval ([framework](../studies/adoption_framework/README.md), "Known problems"; [checklist](../studies/adoption_framework/checklist.md), item 1).
* **Fixed on 9 Oct 2026: `compare.py` printed "tie"** in its `reading` column. It now says "better", "worse" or "unresolved", and gives `p_better`.

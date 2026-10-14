## Your role: the statistics and machine-learning architect (round 1)

(The shared context in `00_shared_context.md` comes first in your prompt.)

The owner asks whether he is "doing it wrong by throwing [the close] in a complex non-linear model with a line that is built across over a decade", and whether "more sophisticated techniques" exist. Your job is the design space, judged against the repository's own evidence.

Cover:
1. **What the current design does, mechanically.** TabPFN learns in context, from 2013..Y−1 rows, a mapping from (close, 56 other inputs) to the result. Explain what that implies for how much it trusts the close, how it can (or cannot) represent "the close plus a small residual", how era changes in the market's efficiency enter it, and what the earlier studies measured about it (`training_window`, `close_drift`, `meta_stack`, `market_anchoring`, `tabpfn_thinking`, `surface_ios` on calibration). Say plainly where the owner's worry is already answered and where it is not.
2. **The alternatives, as a ranked design space**, each judged on what it changes, its expected effect on 2025–26 accuracy against the close, its cost, and its risk:
   * the close as a fixed offset or free-slope anchor, with shrunk nudges (GLM, GAM, hierarchical shrinkage per statistic family);
   * residual boosting (trees started from the close's log-odds as a base margin; note that no boosting library is installed in the `tennis` environment, so say what would be needed);
   * TabPFN aimed at the residual (e.g. the close as an offset through a two-stage or stacked form, or the residual as a regression target), versus TabPFN with the close as an input;
   * coefficients that move over time (dynamic logistic / state-space nudges, exponential discounting, era interactions), as a direct implementation of "the most recent close";
   * a separate walk-forward scale for the model's disagreement with the close (two-part recalibration), and recalibration of the close by context;
   * models whose target is the line's move from open to close (what the market will learn), beside the result model;
   * anything else you judge better.
3. **How to test "not priced by the most recent close" properly.** Power: with about 4,000–4,500 main-tour matches per tour per season, what effect (mLL) can one season or a rolling 12 months resolve? Discovery and confirmation windows, sequential monitoring, alpha-decay detection (the realisation coefficient tracked season by season), multiple testing across many candidate statistics, and how not to fool ourselves with seasons already used to choose the inputs (`feature_provenance`, `clean_holdout_rebuild`).
4. **A recommended architecture** for "a model built around what the recent close misses", in enough detail that it could be built next: its stages, what is fitted on what window, how a new statistic is admitted, how it would be compared with the current model (the project's `compare.py` and adoption framework), and what result would make you abandon it.

Write your memo to `docs/studies/edge_anatomy/team/architect.md`. Formulas are welcome where they make a point precise.

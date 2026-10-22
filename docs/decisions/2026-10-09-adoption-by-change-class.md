# Adoption by kind of change: the kind decides what counts as evidence, a comparison decides only what it can see, and new features go to the pool

**Decided by the owner on 9 October 2026, on Claude's recommendation:** "I accept your adoptation logic, implement it."
Recorded the same day. It amends the [adoption framework](../studies/adoption_framework/README.md) adopted earlier that
day ([decision](2026-10-09-adoption-framework.md)), which stays a set of guiding principles, not rules.

**The context.**
* **The owner's challenge** (9 Oct): "NOT ALL DECISIONS SHOULD BE DONE IN THIS COMPARITIVE BEFORE + AFTER WAY! As thats
  the case the model will never grow incrementally. There are decisions that dont matter individually but matter
  COMBINED together."
* **Claude's diagnosis** (reasoning in the framework, § 0 and § 4; arithmetic in
  [resolution_check.out](../../data/studies/adoption_framework/resolution_check.out)):
  * **The comparison can't see small effects.** The yardstick, a 2020–2024 backtest with the close as an input,
    resolves about 0.02–0.12 mLL (the 95% half-width), depending on what changes. Most changes are expected to be
    far smaller: 100 more training rows are worth about 0.0001 mLL, and a typical new input at the close about 0.01.
  * **Both decision rules fail at that scale.** A rule that needs the interval to clear 0 rejects nearly everything
    real. A rule that follows the sign is close to a coin flip: a true +0.01 at SE 0.04 points the right way 60% of
    the time.
  * **The arithmetic had no direction.** The framework shrank every estimate toward 0, although many kinds of change
    have a known direction.
  * **The reporting convention had become the decision rule.** "Better / worse / unresolved" describes a reading,
    not a decision.
  * **The live case.** The level-evidence study's registered rules would have:
    * recommended a system worth +0.083 mLL for men only 56% of the time;
    * kept 298,008 new lower-level matches out about 96% of the time, whatever they are worth
      ([level_evidence_rules.out](../../data/studies/adoption_framework/level_evidence_rules.out)).
* **The owner's follow-up** (9 Oct): "Maybe I should never do individual feature studies on a 'should I add this to
  the model' capacity? its more I should wonder if it makes any sense to add it to a future feature selection process?
  as features are almost only ever helpful together unless they are the very very best features." Claude agreed, with
  the refinements in point 6.

## Decision

1. **Classify a change before reading any result.** The kind of change sets three things: the direction expected,
   what decides, and what a before/after comparison is for.

   | Kind | Examples | Expected direction | What decides | The before/after comparison |
   |---|---|---|---|---|
   | **Accretion** | new matches from the reference's feeds; refits | + (the learning curve) | a policy, decided once | none per instance: data checks and the holdback |
   | **Repair** | data fixes; restoring lost coverage; live inputs built as in training | + | data evidence | a bug alarm |
   | **Expansion** | a new source or level; a backfill | set by the route the data enters | mechanism and statistic-level tests; the input check | a harm check |
   | **New feature** | a new input or transform | about 0, or slightly − | a selection round (point 6) | only when big enough to see |
   | **Structural** | the learner, training rows, calibration | unknown; effects large | the comparison and the realisation check | decisive |
   | **Tuning** | the best of K memories or settings | 0, plus the winner's luck | the corrected comparison; ties go to the default | decisive after correction |

   Stakes keep their strict lane, unchanged.
2. **Check what the comparison can see before reading it.**
   * State the change's plausible effect and the comparison's resolution (its 95% half-width).
   * A reading much wider than the plausible effect is **"below resolution"**: it decides nothing, and serves only as a
     harm check.
   * A pre-registered decision rule states its rates: how often it adopts a change that works, and how often one that
     harms.
   * `src/eda/current_best_model/adoption_read.py` reads `compare.py`'s output this way. `compare.py` itself is left
     unchanged while the level-evidence study, whose scorer imports it, is running.
3. **The expected direction enters the arithmetic.**
   * The framework's B·(est − sel) > c becomes **B·(est − sel) + (1 − B)·μ₀ > c**, where μ₀ is the kind's expected
     effect.
   * μ₀ comes from theory, learning curves, statistic-level tests and the pooled record (point 5).
   * When the comparison can see the effect (B near 1), the reading decides. When it cannot (B near 0), μ₀ decides.
4. **Below resolution, a harm check with a stated tolerance.**
   * **Default harm:** worse by more than 0.10 mLL with the whole 95% interval below 0, the form of the
     [Roland Garros rule](2026-10-09-roland-garros-box-scores.md); or an input flagged "uneven" in a way its dose does
     not explain.
   * **"Unresolved" passes a harm check.**
   * **"Keeping it out costs nothing" is never a reason.** Say what keeping the status quo forgoes.
5. **Combine changes and evidence.**
   * **Policies, not instances.** A recurring kind of change is decided once, by a study built to see its effect (large
     perturbations, learning curves, dose-response). Its instances then pass data checks only.
   * **The holdback.** The frozen reference is the cumulative control. After each batch of adoptions, and at least
     monthly while changes are adopted, the current template is compared with it (`compare.py`). Many small changes
     then become one reading the comparison can see. Checklist item 10 is the first.
   * **The pooled record.** Every reading of a kind of change goes into
     [class_record.csv](../../data/studies/adoption_framework/class_record.csv). Pooled, they set that kind's μ₀ and
     spread.
   * **Complements**, changes that only work together, are tested together.
   * **Slices of one comparison** (seasons, tours, prices, stages) count as one reading.
6. **New features go to the pool, and selection rounds decide.**
   * **A feature study ends with an admission verdict** for the pool, the
     [feature universe](../studies/feature_universe/README.md). It no longer asks "should this go into the model?"
     * **Admitted.**
     * **Admitted as a lead:** it has read results, and the seasons it read are recorded.
     * **Not admitted,** with the reason.
     * **A repair:** it fixes an input already in the model, so point 1's repair lane applies.
   * **Admission rests mostly on what needs no result:**
     * a stable measurement;
     * leak-proof (the clock and the probe);
     * available at bet time;
     * not a near-copy;
     * a mechanism;
     * a place in the cluster tree.
   * **A selection round decides what enters, by cluster:**
     * a cluster tree fixed before any result;
     * top-down testing, descending only while effects are big enough to see;
     * removal from the full set rather than forward addition;
     * stability across resamples;
     * large clusters compressed;
     * one look per round at untouched matches, for the whole selected model.

     The [clean-holdout rebuild](../studies/clean_holdout_rebuild/README.md)'s selection is redrafted on these lines
     (its Q8).
   * **Rounds are rare,** about once a season, since each spends untouched matches.
   * **The exception:** a feature whose plausible effect is big enough to see on its own may still be tested alone.
7. **Two accretion policies.**
   * **Live fits grow within the season.** This applies once the forecast step is built.
     * A prediction run's fit for season Y trains on 2013 .. Y − 1, plus every season-Y match from the reference's
       feeds whose result counts by the run's cut-off under the match clock (lf + 1 ≤ the cut-off).
     * Backtests and the frozen reference keep the annual protocol.
     * The guard, before first live use: a replay showing that the walk-forward calibration still fits.
     * ***Amended by the owner on 20 Oct 2026** (section at the end): the rows grow at retrains the owner calls, not at
       every run ("the retrain's cut-off" in place of "the run's"), and stage 2 grows with them.*
   * **The holdback** (point 5) runs monthly while adoptions are being made.
8. **Reporting is unchanged, and is only reporting.**
   * Say "better" or "worse" when the 95% interval clears 0; otherwise "unresolved", with P(better). Never "tie".
   * This describes a reading. Whether a change is adopted follows points 1–7.
9. **The level-evidence study,** in progress: its decision rules were replaced before any model-level score existed,
   by [owner_decision_2026-10-09.md](../../data/studies/lower_level_evidence/system/owner_decision_2026-10-09.md).
   * **SYS:** recommended for men unless a reading shows harm.
   * **The selection:** it switches away from SYS only on a "better" reading.
   * **REF:** kept only if the selected arm shows harm.
   * **The new data:** it enters by the system's route unless a reading shows harm.

   Its measurements are unchanged.

## Re-filed by this decision

* **[Checklist](../studies/adoption_framework/checklist.md) item 9** (the lower-level share as a 59th input): no longer
  an adoption decision. U-330 is in the pool as a lead (its readings used 2013–2024 results).
* **The share-signal candidate** (the two box-score shares, [lower-level evidence](../studies/lower_level_evidence/README.md)
  § 8.2): a pool admission as a lead, not a pre-registered adoption.
* **Checklist item 10** becomes the first holdback comparison.

## What it does not change

* **The procedures already decided:** the match clock and its probe; the frozen reference, its history check and
  candidate builds (now read by kind of change); the prediction runs.
* **The stakes lane:** an adoption made on a prior earns no edge credit.
* **Earlier decisions stand.** Agents recommend; accepting a change stays the owner's call.

## Amendment of 20 October 2026: the live fit grows at retrains the owner calls, and stage 2 with it

**The owner's words.** On learning that every 2026 prediction trained on 2013–2025 only (the policy of point 7 was
never built):

> "We havent decided on the frequency of retrains yet, but it is a massive error that we are not using any 2026 for
> training the tabpfn3.5 production models that are used to inform our betting. For production betting our latest
> trains should IDEALLY be using the latest matches. This is weighed against the cost of frequently retraining. Not
> practical to do it every day for example. As of now , Id like to only re-train manually , when I say its time to
> retrain. (a timer can exist that watches time since last retrain so im informed off it on the masters script) each
> time I run the A1-A5, but being 10 months out of sync is not good."

Then, to Claude's three recommendations (the same day): "I'm on board with the following 3 items. Execute them."
* "Record your rule as an amendment to the 9 Oct decision? Training rows and stage 2 would grow only at retrains you
  call; backtests and checks on unseen matches keep the season rule."
* "Go-ahead for the setup and the check, on the fast plan above?"
* "Should stage 2 grow at every retrain, on the three conditions from before (speed table extended and checked, no harm
  in the check, both versions logged)?"

And on the check: "Common sense shows frequent retraining is very unlikely to be harmful, so testing for it is a bit
overkill imo, but im open to it if you think its worth it to test. 24 hours is an unreasonble cost time wise though."

**The rule.**
1. **The live fit's training rows grow at retrains the owner calls, never at a prediction run.** A retrain builds an
   instance on the day's tables. Its live fit for season Y trains on 2013 .. Y − 1 plus every season-Y match of its
   frame whose result counts by the retrain's cut-off under the match clock (lf + 1 ≤ the cut-off). The instance
   records the cut-off and the season-Y matches it admits. Between retrains the rows stay as they are.
2. **Stage 2 grows with them.** s_atp, s_wta and b are refitted at each retrain on 2019 .. Y − 1 plus the same season-Y
   matches, by the decided fit (debut seasons out, b shrunk with τ = 0.05). For those matches it reads the walk-forward
   forecasts: the instance's season-Y fit, trained on 2013 .. Y − 1. The owner's three conditions:
   * the speed table extended to every season-Y men's match of the build, and checked equal to the existing table
     where they overlap;
   * no harm in the check (below);
   * both versions, grown and annual, logged on the first runs.
3. **The season rule stays for everything that measures.** Backtests, harm checks, the holdback, the frozen reference
   and every check on unseen matches read the walk-forward fits (season Y on 2013 .. Y − 1) and the annual stage 2
   (2019 .. Y − 1). The production fit never replaces them, and its forecasts of its own training matches are never
   scored.
4. **Thinking's season fit trains on exactly the local fit's rows** (one paid fit per retrain).
5. **A timer** shows the days and main-tour matches since the active instance's cut-off at A1, A4 and on the bet sheet.
   Its "retrain due" threshold is a setting, 30 days by default (Claude's suggestion; the owner has not chosen one).
6. **The guard** of point 7, cut to what can fail cheaply (the owner's "24 hours is an unreasonble cost"): the check of
   `docs/studies/in_season_retrain/`, with its rules fixed before it runs.
7. **How often:** undecided. The owner calls each retrain.

**Records:** [the in-season retrain report](../studies/in_season_retrain/README.md) and its process log; the
[current best model](2026-10-08-current-best-model.md) (its amendment notes); `CLAUDE.md`.

## Open

* **The default constants** (the harm tolerance of 0.10 and each kind's μ₀ and spread) are starting values; the pooled
  record refines them.
* **The redrafted selection protocol** needs its review rounds ([04_review.md](../studies/clean_holdout_rebuild/04_review.md))
  before it runs.
* **Women's lower-level treatment** waits for the ITF box scores (P7), as the level-evidence study registered.

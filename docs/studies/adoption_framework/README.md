# Adopting a change: how agents weigh the evidence

9 October 2026 · For the agents who suggest adopting or declining a change, and for the owner, who decides · **Adopted by the owner on 9 Oct 2026 as guiding principles, not rules** ([decision](../../decisions/2026-10-09-adoption-framework.md)). **Amended the same day** ([decision](../../decisions/2026-10-09-adoption-by-change-class.md); [errata](../../decisions/2026-10-09-adoption-by-change-class-errata.md)):
* the kind of change comes first (§ 0);
* a comparison decides only what it can see;
* small changes and their evidence are combined (§ 10);
* new features go to the pool (§ 11).

**How to use it.**
* **Start with § 0.** The kind of change decides what counts as evidence, before any reading.
* **Structure the judgment with it.** Its numbers are starting values, not thresholds to pass. When a case calls for something else, depart from it and say where and why.
* **It decides nothing by itself.** Accepting a change stays the owner's call.
* **It does not replace the procedures already decided** (the leak probe, the frozen reference and its comparison). It guides how their results are read and turned into suggestions.

**The question (owner, 9 Oct 2026).** How much evidence should a change need before an agent calls it implementable? The owner's guess: it depends on how the change was hypothesized (EDA on past results? domain intuition?) and on what being wrong costs.

Two independent reviews ([statistics](review_statistics.md), [betting practice](review_betting.md)) examined an earlier answer ([brief](review_brief.md)). They agree with the guess and add a third factor: the price the change is judged against.

**The second question (owner, 9 Oct 2026, evening).** "NOT ALL DECISIONS SHOULD BE DONE IN THIS COMPARITIVE BEFORE + AFTER WAY! As thats the case the model will never grow incrementally." Changes that are invisible one at a time can matter together. §§ 0, 10 and 11 are the answer ([process log](process_log.md)).

**What it replaces.**
* **Labelling every comparison whose 95% interval spans 0 a "tie",** and treating "the interval clears 0" as the bar for adoption. That bar is a publishing convention: it limits false claims. It does not maximise money, and it is too strict for free changes and too lax for costly ones.
* **Since the amendment, also: deciding every change by one before/after comparison.** Most changes are far smaller than such a comparison can see (§ 0), so the reading cannot be what decides them.

## In short

1. **Classify the change before reading any result** (§ 0): accretion, repair, expansion, new feature, structural or tuning. The kind sets three things: the direction expected, what decides, and what a before/after comparison is for.
2. **Check what the comparison can see.** State the plausible effect against the comparison's resolution. A reading far wider than the effect is "below resolution": it decides nothing and serves only as a harm check.
3. **Name the target before reading a result.**
   * Say which venue and hour we would bet at, which price is fed to the model, which matches would be bet, and which seasons are scored.
   * Also check that the input will exist at bet time, in the same form.
4. **Ask how the idea arose.** That sets how far to shrink its estimate, and whether the seasons that suggested it may also confirm it.
5. **Ask what being wrong costs.** Upkeep, reversibility, whether we would ever notice, and whether it changes stakes all count. Together they set the bar.
6. **Weigh the reading with the kind's expected direction** (§ 4): B·(est − sel) + (1 − B)·μ₀ against the cost.
   * When the comparison can see the effect, the reading decides.
   * When it cannot, the kind decides:
     * repair, expansion and accretion are adopted unless the harm check fails (worse by more than 0.10 mLL with the whole interval below 0);
     * a new feature goes to the pool;
     * tuning keeps the default;
     * a structural change is undecided, and goes to mechanism, cost and the realisation gate.
   * A costly change pays for itself, and can need more than a 95% interval.
7. **Combine** (§ 10):
   * decide recurring kinds once, as policies;
   * compare the template with the frozen reference after each batch of adoptions;
   * pool readings by kind;
   * test complements together.
8. **New features go to the pool** (§ 11). A feature study ends with an admission verdict, and selection rounds decide by cluster.
9. **Check the basics first** (§ 5). A change that leaks, can't exist at bet time or makes the model over-react is rarely worth suggesting, whatever its numbers.
10. **Be pragmatic about parts and strict about the edge.** The edge that decides whether to bet, and how much, comes only from matches no choice has seen. It is measured at the venue's price, after costs, and shrunk.

Agents suggest. The owner decides what enters the current best model.

## 0. What kind of change is this?

*Added on 9 Oct 2026 by the [amendment](../../decisions/2026-10-09-adoption-by-change-class.md).*

**Classify the change before reading any result.** The kind sets what counts as evidence.

| Kind | Examples | Expected direction (μ₀) | What decides | The before/after comparison | Plausible effect (mLL, starting value) |
|---|---|---|---|---|---|
| **Accretion** | new matches from the reference's feeds; new seasons; refits | + (the learning curve) | a policy, decided once (§ 10) | none per instance: data checks, and the holdback (§ 10) | a season's rows: about 0.001–0.01 |
| **Repair** | a verified data fix; restoring lost coverage; live inputs built as in training; a fix of a measured bias in an input already in the model (a new input aimed at a market bias is a new feature) | + by mechanism | data evidence | a bug alarm: the harm check (§ 4) | about 0.02 |
| **Expansion** | a new source or level; a backfill | set by the route the data enters | mechanism, statistic-level tests, the input check | a harm check | about 0.03 |
| **New feature** | a new input, a transform, a new cluster | about −0.03 for a single input at the close | a selection round (§ 11) | decisive only if the effect is big enough to see alone | about 0.01 |
| **Structural** | the learner, training rows, calibration, how the price enters | 0; effects large either way | the comparison, plus the realisation gate (§ 5) | decisive | about 0.2 |
| **Tuning** | the best of K memories, windows or settings | 0, plus the winner's luck | the corrected comparison; ties go to the default | decisive after the correction | about 0.03 |

* **Where the numbers come from.** They are starting values, refined by the pooled record (§ 10).
  * **Accretion:** the training-window study's random draws give a learning curve. 100 more training rows at about 60,000 are worth about 0.0001 mLL, and a season's rows about 0.001–0.01 ([resolution_check.out](../../../data/studies/adoption_framework/resolution_check.out)).
  * **New feature:** the screens' 28 single additions averaged −0.028 (+ = the addition better), with true effects spread about 0.012 around that ([statistics review](review_statistics.md), finding 3).
  * **Repair and expansion:** the readings on file, mostly within ±0.05 ([class_record.csv](../../../data/studies/adoption_framework/class_record.csv)).
  * **Structural:** Challenger matches as training rows read −0.48, and the last three seasons as the training window −0.38 (+ = the change better; § 4; [training window](../training_window/README.md)).
* **Stakes are not a kind.** They keep their strict lane (§ 6).
* **Declare the kind before any reading,** and say why. Reclassifying a change after reading it is a forking path.

### What the comparison can see

* **The resolution** of a comparison is its 95% half-width, 1.96 × SE. A true effect that size is detected about half the time; one 1.4 times larger (2.8 × SE), 80% of the time.
* **The project's comparisons resolve about 0.02–0.3 mLL,** depending on what changes (95% half-widths; + = the change better throughout):
  * a change to stage 2's speed column alone: ±0.02 (the speed backfill, [seed check](../../../data/studies/adoption_framework/seed_fix_check/scores.csv));
  * an input change on 2020–2024: about ±0.07–0.09. The lower-level translation read ±0.07; the lean review's removal of one input, ±0.09;
  * the level-evidence study's men's holdout: ±0.12 (its power note);
  * a structural change: about ±0.3 (Pinnacle first against the reference).
* **So most changes are below resolution.** A reading much wider than the plausible effect decides nothing.
  * Say "below resolution", not just "unresolved".
  * "Unresolved" suggests more data would settle it; "below resolution" says this comparison will not.
* **Following the sign of such a reading is close to a coin flip.** A true +0.01 at SE 0.04 points the right way 60% of the time, and an equal harm passes 40% of the time.
* **A pre-registered decision rule states its rates:** how often it adopts a change that works, and how often one that harms, at the comparison's own standard errors. The level-evidence study's first rules would have recommended a system worth +0.083 mLL for men 56% of the time ([level_evidence_rules.out](../../../data/studies/adoption_framework/level_evidence_rules.out)).
* **The reader.** `./python.sh src/eda/current_best_model/adoption_read.py --scores <compare.py's scores.csv> --kind <kind>` prints three things: the resolution, whether the kind's plausible effect is below it, and the kind's decision (§ 4).
  * An expansion also needs `--route-supported`, once the route's statistic-level evidence is stated.
  * Tuning needs `--k`, the number of variants.
  * `--kind holdback` reads a holdback (§ 10).
  * It lists the inputs `compare.py` flagged, and an adoption waits on reading them against the dose.
* **Too small to matter.** When neither the estimate nor its interval could change a bet, say "immaterial" and decide on simplicity, consistency or upkeep. Don't carry the arithmetic to four decimals: the `ios_points_short` removal was decided "by +0.0004 on a bar of 0" (§ 4).
* **Slices of one comparison are one reading.** Seasons, tours, prices and stages of the same comparison share its noise. "It leans worse in every reading" is one reading.

## 1. The target

* **A change can help at one price and not at another.**
  * Offset Elo for women read −0.21 [−0.48, +0.07] with the close as an input, and +1.11 [+0.04, +2.18] when the model was fed the price 24 hours out (+ = offset Elo better; [decision](../../decisions/2026-10-06-offset-elo.md)).
  * It was adopted for early bets, so the second reading is the one that counts.
* **The yardstick moves the edge itself.**
  * In 2020–24 the model beat the books' average close by +1.46 [+0.84, +2.08] mLL per match, and Pinnacle's by +1.16 [+0.52, +1.79] (+ = model better; [close drift](../close_drift/README.md)).
  * Fed Polymarket's price 48 hours out, it beat that price by +5.03 [+0.49, +9.56] ([bet timing](../bet_timing/README.md)).
* **`compare.py` scores with the closing odds as an input.** Its readings answer "does this help beyond the close?". That is the right question only for bets at the close.
* **Early-price history exists only for 2025–26,** the proposed clean holdout. A change aimed at early prices can be read at its target only by spending holdout looks, or on sealed and live matches. Say so; don't quietly substitute the close.
* **Bet-time existence.** An input that is late, missing or built differently live is not implementable. Check its publication lag against the bet hour, and check that the live chain reproduces it ([prediction runs](../../decisions/2026-10-08-prediction-run-box-scores.md)).

## 2. How the idea arose

*Since the amendment of 9 Oct 2026, § 0's kind comes first; provenance then sets the shrinkage and the confirmation within the kind. The table's first two rows are § 0's repair and expansion.*

Provenance changes three things:
* the prior: how large true effects of this kind tend to be;
* the search behind the estimate;
* whether the evidence that suggested the idea can also confirm it.

| How it arose | What the outcome test is for | Default |
|---|---|---|
| **A verified data fix** | A bug check only | Adopt on the data evidence. A noisy outcome reading never vetoes a correct fix: choosing data by outcomes is itself overfitting |
| **More of a kind of data already used** (a backfill, wider coverage) | A harm check. The input check is the real gate: a new source can shift an input's scale in some seasons only, as the input-data audit's finding #6 did | Adopt if the input check is clean and the harm check passes (§ 4). A smaller visible harm sends it back to its route. Claim no edge for it. *Aligned with § 4 on 9 Oct 2026; it first read "the estimate is not clearly negative".* |
| **A mechanism stated before one declared test** | Decisive, after shrinking | Adopt if the shrunk gain beats the cost (§ 4) |
| **The best of K variants** (memories, windows, settings) | Decisive after removing the winner's luck | As above, after the correction. Ties go to the default, which is the simplest member unless stated (§ 0, tuning). A reading that cannot see the effect keeps the default |
| **Many ideas screened, or a pattern found in the scored seasons** | A lead only | Confirm outside the data that found it (2015–19, the other tour, sealed matches) before suggesting adoption |
| **Structural** (training rows, the learner, calibration) | Decisive, plus the realisation gate | Shrink less, since effects can be large either way, but check for over-reaction |

**Domain intuition is a weak prior at the close.** It predicts results, and the close already holds most of what it knows. Examples (+ = the change better):
* **The surface IOS profile:** men +0.83 [+0.39, +1.27] without the odds, +0.07 [−0.11, +0.26] with the close.
* **The feature-interactions study:** 116 ideas from four brainstormers became 35 pre-registered hypotheses. One passed the screen, and 2025–26 did not confirm it: −0.27 [−0.64, +0.10] ([study](../feature_interactions/README.md)).
* **The size of true effects:** the project's screens put the spread of true effects of a new input at the close at about 0.01 mLL or less ([statistics review](review_statistics.md), finding 3).

**Ask the market question:** why would the market misprice this, and who is on the other side? A story is more credible at a thin early book than at a sharp close.

## 3. What being wrong costs

| Class | Examples | Starting cost bar c (mLL per match) |
|---|---|---|
| Free and reversible | A data fix; a backfill with no new feed; anything that falls back to the reference | 0 |
| More complexity or compute | One more input; more fits | ≈ 0.01 |
| A new live dependency | A new scraper, feed or decryption needed at bet time | ≈ 0.05, plus the lag check |
| Changes stakes | How far the model strays from the price; the edge used for sizing | Not a part decision: see § 6 |
| Hard to undo | Spending sealed matches; changing the training history | The owner's call |

Errors are not alike:
* **Cheap and reversible:** a part with no new feed that can fall back to the reference.
* **Cheap but never detected:** a dud. Live data will not expose it. Its cost is the inflation it adds to the claimed edge.
* **Expensive:**
  * over-staking on an inflated edge;
  * a feed that vanishes at bet time;
  * a leak's phantom edge;
  * account limits at soft books;
  * spent sealed matches.
* **Missing a real edge:** cheap if it is small, because it can be found again. A large one would show.

## 4. Weighing it: shrunk gain against cost

**A default to reason with: adoption pays when B · (est − sel) + (1 − B) · μ₀ > c.** It is arithmetic for structuring the judgment, not a test to pass. *Amended 9 Oct 2026: the μ₀ term was added. Before, every estimate was shrunk toward 0.*
* **est, s:** the declared primary's estimate (mLL per match, + = the candidate better) and its standard error.
* **B = τ² / (τ² + s²)** shrinks the estimate toward 0. τ is the typical size of a true effect of that kind.
  * For a new input at the close, start at 0.03. That is generous: the screens say about 0.01.
  * For structural changes, 0.1–0.3.
  * Re-estimate τ for other targets, since effects at early prices have been larger.
* **sel** removes the winner's luck when the candidate is the best of K variants. It is about s · m_K, with m_K = 0.56, 0.85, 1.03, 1.27 and 1.54 for K = 2, 3, 4, 6 and 10 (less when the variants' noise overlaps). It is 0 for one declared test.
* **c:** the cost bar from § 3.
* **μ₀:** the kind's expected effect (§ 0).
  * B · (est − sel) is the reading's share; (1 − B) · μ₀ is the prior's.
  * When the comparison can see the effect (B near 1), the reading decides. When it cannot (B near 0), μ₀ does.

What it implies:
* **With μ₀ = 0 and c = 0 only the sign matters, and below resolution the sign is close to a coin flip** (§ 0). So a free change below resolution is decided by its kind:
  * repair, expansion or accretion: adopted on the kind's direction unless the harm check fails;
  * a new feature: admitted to the pool;
  * tuning: left at the default;
  * a structural change: undecided. It goes to mechanism, cost and the realisation gate; the sign of its reading decides nothing.

  *Corrected 9 Oct 2026: this bullet first read "Free changes need only point the right way".*
* **The harm check,** for kinds decided on their direction.
  * Harm is a reading worse by more than **0.10 mLL** with its whole 95% interval below 0, the form of the owner's [Roland Garros rule](../../decisions/2026-10-09-roland-garros-box-scores.md). It is also an input flagged "uneven" in a way its dose does not explain. The value 0.10 is Claude's choice in that form; the owner may set another.
  * "Unresolved" passes.
  * **A small harm** is a reading worse with its interval below 0, but inside the tolerance.
    * A repair is still adopted: a correct fix is not vetoed by its outcome (§ 2).
    * An expansion or accretion goes back to its route first: ignore, down-weight or transform the data, and compare again. In the owner's words of 8 Oct: "if it harms results we will want to make some modifications".
  * A harm check catches large harms (bugs, scale shifts), not small ones. Say so when quoting it.
  * **A costly change pays for itself.** "Adopt unless harm" is for free changes. An expansion that needs a new live feed carries § 3's bar (about 0.05) and is weighed by the arithmetic ([errata](../../decisions/2026-10-09-adoption-by-change-class-errata.md), E6).
* **"Keeping it out costs nothing" is never a reason.** Name what the status quo forgoes: data, coverage, live/training parity, a fix of a known bias.
* **With costs, no single P bar fits.** Depending on τ and s, the bar in flat-P terms runs from about 0.5 to above 0.98.
* **A change can be 99% likely to help and still be worth nothing.** Its size against its cost decides, not the probability of its sign.

A suggestion usually takes one of six forms:
* **adopt;**
* **adopt on a logged lean** (§ 9);
* **admit to the pool:** a new feature (§ 11);
* **shadow:** run it beside the model on live matches;
* **decline, but keep it as a candidate;**
* **reject.**

Declining a part is not a verdict on the idea. Say what would change the call: another target, more data, more power.

**Worked examples** (+ = the change better):
* **The ATP speed backfill** ([study](../infosys_atp_backfill/README.md)): an expansion with more of the same data and no new feed, so c = 0.
  * Men: +0.027 [−0.073, +0.128] as reported, and +0.027 [−0.012, +0.066] with the seed term paired ("Known problems").
  * There is no harm, the input check is clean, and the data enters in its own format → adopt, and claim no edge for it.
  * *Amended 9 Oct 2026:* it would have been adopted had it leaned slightly the other way. It was first written as "It points the right way → adopt".
* **`ios_points_short`** ([lean review](../lean_review/README.md#results-9-oct-2026)): removing it read −0.03 [−0.11, +0.06] at Pinnacle's opening line (+ = without it better).
  * The rule fixed in advance removed it "by +0.0004 on a bar of 0".
  * Under § 0 it is immaterial either way. The honest reason to drop it is simplicity; the arithmetic adds nothing.
* **The surface IOS profile:** a mechanism.
  * At the close it reads +0.01 [−0.10, +0.13], unresolved (P(better) 0.57).
  * It was kept for early bets, a target not yet tested → adopt on a logged lean, to be read at the target once clean early-price matches exist.
* **Challenger matches as training rows:** structural.
  * At the close it reads −0.48 [−1.09, +0.14], and the model's realisation fell from 0.91 to 0.63: it over-reacts.
  * → Reject on the gate alone ([study](../event_levels/README.md)).
* **Rust after a long break (B-INJ):** the one survivor of 35 screened hypotheses. As a lead it needed confirmation outside the screen's seasons, and 2025–26 did not confirm it.

## 5. Checks before suggesting adoption

These are strong defaults: a failure is a reason not to suggest the change, or to name the failure plainly. The leak probe is required anyway, by the [match-clock decision](../../decisions/2026-10-05-match-timing.md).

* **Kind and resolution,** declared before any reading (§ 0).
* **Leak probe** for any feature that combines different players' results (`src/eda/match_timing/probe.py`).
* **Input check** (`compare.py` part 1): no input flagged "uneven".
* **Shuffled twin:** the same columns permuted within each era must not score as well. It also measures what extra columns cost.
* **Bet-time existence:** the publication lag fits before the bet hour, and the live chain reproduces the training inputs.
* **Fallback:** a missing live input returns the model to the reference, not to a guess.
* **Realisation:** the change must not make the model over-react to its disagreement with the price, shown by a realisation slope well below 1.

## 6. Three lanes

| Lane | What it decides | How strict |
|---|---|---|
| **Data fixes** | Whether a correction is right | Data evidence only; outcomes serve as a bug check |
| **Parts** | What goes into the model | Pragmatic: § 4 |
| **Stakes, and whether to bet at all** | Whether to bet, where, and how much | Strict: matches no choice has read (sealed, then live), at the venue's bet-time price, after the margin and fees, shrunk, at fractional Kelly |

Why the stakes lane is strict:
* **Kelly punishes over-estimates more.** Staking on twice the true edge earns about nothing. Staking on half keeps about 75% of the growth.
* **Margins magnify the error.** A bet's net edge is its gross edge minus the margin, so an overstated gross edge is a far more overstated net one.
  * At Pinnacle (2022 to Jan 2026, the seasons that chose the inputs), the bets claimed 2.9% on average and returned +1.50% [+0.38, +2.73] per unit staked ([study](../tabpfn_thinking58/README.md)).
  * The bets that claimed edges above 5% returned about their claim, so the shortfall sits in the small edges.
* **Every choice made on the backtest's seasons inflates its edge.**
  * The current model's 2025–26 reading is forecast to overstate the edge by about 0.35 mLL ([clean holdout](../clean_holdout_rebuild/README.md)).
  * So far the edge exists only in the seasons that chose the inputs: +0.18 [−0.28, +0.64] in 2015–19 against +1.46 [+0.84, +2.08] in 2020–24 (+ = model better than the recalibrated average close; [provenance](../feature_provenance/README.md)).
* **Shrink the edge with the realisation slope,** measured on untouched matches at the venue. Bet only where the shrunk edge beats the spread and the fees.

## 7. Reporting

* **This section is how to report a reading.** It does not decide adoption; § 0 and § 4 do. A reading's label (better, worse, unresolved) is not a verdict on the change.
* **No "tie".**
  * Give the estimate, the 95% interval and the direction key.
  * Say "better" or "worse" if the interval clears 0. Otherwise say "unresolved" and give P(better).
* **P(better) = Φ(est / SE)** is the flat-prior reading of that one test. It is not the chance that the change helps next season.
* **Say "equivalent" only when a 90% interval lies inside ±δ.** δ is the smallest effect that would change the decision; for a costly change, that is its cost.
* **Give verdicts on the declared primary only.** Other cells (tours, levels, seasons) are flags: a 13-cell table shows a cell at P ≈ 0.95 or 0.05 about once by chance.
* **State the search:** how many variants were tried, and on which seasons.
* **Give the money context** when the target is a venue: the return and closing-line value after the margin, and the depth available.
* **End with the suggestion line:** kind · target · provenance · cost class · plausible effect against resolution · B·(est − sel) + (1 − B)·μ₀ against c, or the harm check · gates · outcome · what would change it.

## 8. What live data can and cannot settle

* **The whole model, slowly.**
  * About 5,000 main-tour matches arrive a year. Detecting +1.3 mLL with 80% power takes about 7,700 ([provenance](../feature_provenance/README.md)).
  * A true edge nearer 0.5 takes years.
* **Not small parts.**
  * A part worth ±0.1 needs a decade or more of live matches.
  * Shadow-running a challenger proves it runs live and banks untouched evidence. It will not settle a small part.
* **Faster signals for early bets.**
  * Closing-line value: does the price move our way after we bet?
  * The price's drift toward the model's view: after the offset Elo swap, +0.23 [+0.04, +0.43] beyond the old model's (+ = toward the new model).
  * Bets at the close have no such signal. With the close as an input, their closing-line value is just minus the costs, so only outcomes can judge them.
* **Alarms.**
  * No bet on a stale or out-of-range input.
  * Watch for drift in the model's disagreement with the market, and in the bet count.
  * Also watch for rolling closing-line value below 0, realisation below about 0.8, and a drawdown beyond what the shrunk edge allows.

## 9. The ledger

* **The ledger is [lean_ledger.md](lean_ledger.md),** started 9 Oct 2026. It holds each lean's target, reading, luck and next read, totals the luck against the clean-holdout forecast, and counts the looks at sealed matches.
* **Log every adoption made on a lean,** with its estimate, sel, provenance and target. Subtract their expected luck from any claimed edge.
* **Review adopted parts that lean worse at their own target.**
  * Today stage 2, the speed adjustment, reads −0.26 [−0.60, +0.07] on men 2020–24 (+ = the adjustment helps; [statistics review](review_statistics.md), finding 8).
  * Its support comes from 2024–26, which overlaps the proposed holdout.
* **Count the looks** at sealed data, and log each one.
* **The pooled record is separate** (§ 10). It holds every reading of every change by kind, adopted or not, to set each kind's μ₀.

## 10. Combining small changes and their evidence

*Added on 9 Oct 2026 by the [amendment](../../decisions/2026-10-09-adoption-by-change-class.md).* Changes that cannot be seen one at a time can be seen together, and so can their evidence.

* **Policies, not instances.**
  * A recurring kind of change is decided once, by a study built to see its effect: large perturbations, a learning curve, a dose-response.
  * Its instances then pass data checks only: identity, duplicates, the match clock, the leak probe, the input check.
* **Live fits grow within the season** (a policy decided with the amendment; it applies once the forecast step is built).
  * A prediction run's fit for season Y trains on 2013 .. Y − 1, plus every season-Y match from the reference's feeds whose result counts by the run's cut-off under the match clock (lf + 1 ≤ the cut-off).
  * Backtests and the frozen reference keep the annual protocol.
  * The guard, before first live use: a replay showing that the walk-forward calibration still fits.
  * The learning curve puts the gain at about 0.001–0.01 mLL by late season. That is small, but its sign is known and it costs minutes of GPU.
  * Its cost is taken as 0, not § 3's 0.01 for "more fits". It adds minutes to a run that already rebuilds the frame (about 2 hours), and adds no input, no upkeep and no live dependency (errata E7).
* **The holdback** (a policy decided with the amendment; its control corrected the same night, [errata](../../decisions/2026-10-09-adoption-by-change-class-errata.md) E1).
  * **The control is the most recent stored instance that carries every structural change made since the reference.** Today that is the Pinnacle-first instance of 9 Oct (`data/studies/current_best_model/pinnacle_first_2026-10-09/`).
  * After each batch of adoptions, and at least monthly while changes are being adopted, the current template is compared with it (`compare.py`).
  * **Why not the frozen reference itself.**
    * The reference predates the Pinnacle-first odds input, which moves every forecast.
    * A comparison across that change resolves only about ±0.3. The indoor fill against the reference read +0.007 [−0.306, +0.320] (+ = the fill better).
    * The reference stays the yardstick for structural changes and for the model as a whole.
  * **With a control that shares the structural changes,** a batch reads at about ±0.07–0.1. Twenty changes of +0.01 each make one +0.2 reading, which that comparison can see. Leans that add up to harm show too.
  * **On harm, bisect.** A holdback reading that shows harm is bisected, adoption by adoption. `adoption_read.py --kind holdback` reads it that way, and says when its control cannot see the batch.
  * **A new control.** When a structural change is adopted, an instance carrying it becomes the next control.
  * The first holdback is [checklist](checklist.md) item 10.
* **The pooled record** ([class_record.csv](../../../data/studies/adoption_framework/class_record.csv)).
  * Every reading of a change goes in, adopted or not, with its kind, its seasons and whether its seed term was paired.
  * `./python.sh src/eda/adoption_framework/class_record.py` pools each kind over its readings of seasons ≤ 2024: inverse-variance, with the DerSimonian–Laird spread ([class_record.out](../../../data/studies/adoption_framework/class_record.out)).
  * As the pooled means and spreads firm up, they replace § 0's starting values.
  * **Leads stay out of the pools.** So do readings chosen as the best of several. Both carry selection, and would bias μ₀ upward. Today the two lower-level share readings are leads, so the new-feature kind keeps its screened starting value (−0.028).
  * Add a row whenever a change is read.
* **Complements are tested together.**
  * Changes that only work together are one candidate: a layer and the data it is built for; centring and the coverage shift it protects against.
  * One-at-a-time testing cannot see them.
* **Order matters.** A change's reading depends on what is already in the model: once offset Elo was in, the surface profile added nothing. The holdback reads the whole set.

## 11. New features: the pool and selection rounds

*Added on 9 Oct 2026 by the [amendment](../../decisions/2026-10-09-adoption-by-change-class.md), on the owner's question: "Maybe I should never do individual feature studies on a "should I add this to the model" capacity? … features are almost only ever helpful together unless they are the very very best features."*

**Why.** A feature's value beside the close is mostly joint:
* **Substitutes.** Correlated features share information, so each one's value given the others is about 0, even when the group matters.
  * Dropping the whole long-memory IOS profile read −0.29 [−0.63, +0.04] at the close (+ = without it better): about a quarter of the model's lead over the price.
  * Its member `ios_points_short`, on the same scale, read −0.00.
* **Complements.** An offence rating needs the opponent's defence; a modifier needs what it modifies.
* **Spread-out signal.** Many statistics each add a sliver. The two-week profile's lead was the twelve together.
* **One at a time,** most single additions read about 0 or slightly worse: the screens' 28 averaged −0.028.

**A feature study ends with an admission verdict** for the pool, the [feature universe](../feature_universe/README.md) (§ 9 there):
* **admitted;**
* **admitted as a lead:** it has read results. The seasons it read are recorded, so a selection round confirms it on others;
* **not admitted,** with the reason;
* **a repair:** it fixes an input already in the model, so § 0's repair lane applies.

**Admission rests mostly on what needs no result:**
* a stable measurement, defined the same way every season;
* leak-proof: the match clock and the probe;
* available at bet time;
* not a near-copy of a pool member;
* a mechanism: why would the market misprice it?
* a place in the cluster tree.

Signal tests of one relationship are still worth running: they shape the clusters, but they adopt nothing. For example, the close under-rates players arriving from lower levels: β +0.18 [+0.09, +0.27], + = the price under-rates them.

**A selection round decides what enters, by cluster.** The principle: decide at the coarsest level a comparison can see; below that, decide by structure and simplicity, not by readings.
1. **A cluster tree, fixed before any result.**
   * It starts from the per-statistic taxonomy: serve, return, pressure and style; offence and defence; short and long memory; differences and matchup products.
   * It is refined by the features' correlations on the development seasons, which read no result.
   * It also splits statistics the player drives from those the opponent drives (the lower-level study's role A).
2. **Top-down testing.**
   * First all per-statistic profiles against none; then serve, return and pressure.
   * Descend only while effects are big enough to see; this is hierarchical testing of variable importance (Meinshausen, 2008).
   * Below that level, a branch is kept or dropped whole.
3. **Removal from the full set,** not forward addition, so complements start together.
   * A branch goes only when the comparison shows it is not worth its columns: the upper end of its gain's interval is below its column price.
   * An unresolved branch stays whole.
4. **Stability.** A cluster is dropped only if dropping it holds in most resamples of the development seasons (stability selection). Otherwise it stays.
5. **Compression.** A large cluster enters as a few summary columns, since TabPFN pays a price per column.
6. **One look per round,** at untouched matches, for the whole selected model.
   * A whole-model change is big enough to see, so this is where a before/after comparison belongs.
   * It also gives the untouched edge for stakes.

* **The rebuild's selection is redrafted on these lines** ([03_rebuild_stages.md](../clean_holdout_rebuild/03_rebuild_stages.md) § 5; its Q8).
  * Its first draft added families forward, each against a one-standard-error bar. That is one-at-a-time testing at the family level.
  * It keeps complements out, and it drops a small real family half the time or more.
  * Yet among about 20 families with no real effect, the best one clears that bar 97% of the time ([statistics review](review_statistics.md), finding 9).
* **Rounds are rare,** about once a season, since each spends untouched matches. Between rounds, the model changes only through repairs, expansions and accretion.
* **The exception:** a feature whose plausible effect is big enough to see on its own may still be tested alone. Offset Elo at the 24-hour price read +0.78 [+0.03, +1.54] (+ = offset Elo better).
* **Re-filed:** checklist item 9 (the lower-level share, U-330) and the share-signal pair are pool admissions as leads.

## Known problems in the tools (9 Oct 2026)

* **Fixed on 9 Oct 2026: `compare.py` counted seed noise twice** ([checklist](checklist.md), item 1).
  * `score.paired_stats` added both arms' seed variances as if they were independent. Arms that share seed numbers share that noise: per-seed losses correlate +0.97 to +0.99, even between different fits.
  * A model compared with itself got ±0.087 instead of 0.
  * **The fix:** `paired_stats(..., matched_seeds=True)` takes the seed term as the variance over seeds of the per-seed difference, divided by the number of seeds. It is off by default.
    * `compare.py` turns it on for model against model. Rows against the close stay unpaired, since a price has no seeds.
    * Its `reading` says "unresolved" instead of "tie", with `p_better` beside it.
    * Also on in `model_rebuild/compare.py` (and so in the backfill study's script) and `training_window/score.py`. Left off in the pre-registered serve-speed and centring scorers, whose registered runs used the unpaired term.
  * **Checked on the backfill** (`data/studies/adoption_framework/seed_fix_check/`; + = with the backfill better): both tours +0.014 [−0.006, +0.035] instead of [−0.073, +0.102], men +0.027 [−0.012, +0.066], P(better) 0.92 for each. Stage 1 is exactly 0, with a zero-width interval.
  * **Readings published before the fix keep their wider intervals.** `compare.py` keeps the old interval as `lo_unpaired` / `hi_unpaired`, and reproduces the old readings exactly.
* **`compare.py` scores only with the close as an input.** Changes aimed at early bets need a second yardstick.
* **`compare.py` reports no resolution and no kind** (9 Oct 2026, evening).
  * `src/eda/current_best_model/adoption_read.py` reads its `scores.csv` that way (§ 0).
  * `compare.py` itself is left unchanged while the level-evidence study runs, because that study's scorer imports its recipe and checks its rows.
* **No generic tool compares the template with an instance other than the frozen reference** (9 Oct 2026, evening).
  * The holdback needs one (§ 10). Until it exists, adapt `src/eda/indoor_fill/score.py`, which scored a candidate against the lean review's arm A2.
  * Once the level-evidence study ends, a `--base` option for `compare.py` would serve.

## Files

| File | Content |
|---|---|
| [checklist.md](checklist.md) | The changes suggested under the framework, sorted by confidence, each with a ready-to-run prompt |
| [lean_ledger.md](lean_ledger.md) | The adoptions made on a lean (§ 9): each one's target, reading, luck and next read; their luck against the clean-holdout forecast; the looks at sealed matches |
| [review_brief.md](review_brief.md) | What both reviewers were given: the owner's challenge, the earlier answer under review, the follow-up |
| [review_statistics.md](review_statistics.md) | The statistics and decision-theory review, verbatim |
| [review_betting.md](review_betting.md) | The betting-practice review, verbatim, with its sources |
| [process_log.md](process_log.md) | How the amendment of 9 Oct 2026 was reached, for a future reviewer |
| `src/eda/adoption_framework/` | The calculations behind them: the threshold model, the seed-term checks, the decision review; since the amendment, the resolution check (`resolution_check.py`), the level-evidence rules' rates (`level_evidence_rules.py`) and the pooled record (`class_record.py`) |
| `data/studies/adoption_framework/` | Their printed outputs; `seed_fix_check/`, the seed-term fix checked on the backfill; `class_record.csv`, the pooled record (§ 10) |
| `src/eda/current_best_model/adoption_read.py` | Reads `compare.py`'s output by kind: the resolution, the harm check, or the arithmetic with μ₀ (§§ 0, 4) |

# Review brief: when should a tested change be adopted? (9 Oct 2026)

*Kept as both reviewers received it, with two notes added afterwards:*
* **A correction (from the [betting review](review_betting.md), finding 7):** "$0.00 per 100 matches" below was the difference between betting at the early market and at the close, not a return.
  * Both moments returned about +4% per $1 in 2026, against an expected −1.6% with Polymarket's close as the truth.
  * The model's log loss tied that close (+0.21, + = model better), so the profit is probably luck ([line sharpening](../line_sharpening/README.md)).
* **The scratch script** in § 4 is now `src/eda/adoption_framework/tie_reeval.py`, with its output in `data/studies/adoption_framework/tie_reeval.out`.

## The project in three lines

A tennis match-winner forecasting project aimed at betting (repo: `C:\Users\zerom\Documents\Tennis-predictions`; read its `CLAUDE.md` first). "The current best model" is a TabPFN-3.5 forecast on 58 inputs (closing odds included) plus a walk-forward men's serve-speed adjustment. Candidate changes (new data, inputs, rebuilds) are compared with a frozen reference by `src/eda/current_best_model/compare.py`: paired log loss in milli-log-loss per match (mLL; **positive = the candidate is better**), scored walk-forward on 2020–2024, with a 95% interval from a 4-week-block cluster SE plus seed variance (`src/eda/serve_speed_tabpfn/score.py`, `paired_stats`, line ~396). 2025–2026 is a proposed clean holdout (`docs/studies/clean_holdout_rebuild/`, not approved). The model's edge over the recalibrated average closing price is about +1.4 mLL per match on 2020–2024 (+1.46 [+0.84, +2.08]; + = model better). No betting has been done; a line-sharpening study found $0.00 per 100 matches realised at an early market.

## 1. The owner's challenge (8 Oct 2026, verbatim)

> Throughout all the work we've been doing now youve labeled any comparison where 0 exists in the 95%ile as a "tie". I question if thats a good strategy.
> There's things we do at random that may need this level of scrutinty, but if we add more data of type we already suspect is helpful and we ask "did this data help" and the test shows there's an 80% chance, dismissing it as a tie seems kind of silly?
> Maybe im missing a risk though if we make a bunch of changes based on suggestive 60-75% tests that cross zero, they may compound into some sort of overfitting?
> Like if I have a model that is 80% to make money, and the prior is that we have to beat a tough closing line maybe that's no good, but if we suspect a stat is helpful based on some domain consideration or in the case of the serve data simply supplying more data to data that we know was already helpful, 80% likely to improve is a very strong indicator we have something good yeah?
> Im betting to make money here, not proving a vaccine works. Its ok for small scale losses to then revisit my idea as more information develops live.
> Im not instructing you to change your threshold, but im instructing you to re-evalute critically. Double down on how you've been approaching this problem, or add nuance/caveats to what im saying or agree.

## 2. The assistant's answer (8 Oct 2026, verbatim) — THE LOGIC UNDER REVIEW

**Verdict: you're mostly right, and I'd change what I've been doing.** "Tie" was the wrong word, and a 95% interval is the wrong bar for adopting a cheap, well-motivated change. The overfitting you suspect is real, though. It mostly inflates our estimate of the edge rather than damaging the model, and a strict bar doesn't prevent it.

### Where you're right

**"Tie" threw away information in both directions.** An interval that spans 0 means "not proven", not "equal". Some readings the docs call ties (mLL per match, + = the change is better; P(better) is the chance it helps, read off the same interval as if it were the only test run):

| Labelled "tie" | Estimate [95%] | P(better) |
|---|---|---|
| Serve-speed backfill, men 2020–24 | +0.027 [−0.073, +0.128] | 0.70 |
| Surface IOS profile with the close, both tours | +0.01 [−0.10, +0.13] | 0.57 |
| Men's odds + 16-input profile vs the close, 2022–26 | +0.93 [−0.00, +1.86] | 0.98 |
| Offset Elo with the close, women (we adopted it) | −0.21 [−0.48, +0.07] | 0.06 |
| Adding Challenger rows, men | −0.91 [−1.89, +0.08] | 0.03 |

One word covered our best lead against the close, a coin flip, and a 94% lean toward harm in a change we adopted.

**The 95% bar is a rule for publishing, not for betting.** It limits how often you claim something false, while a bettor wants the most expected money. I modelled 20 ideas at this project's typical noise (an SE of about 0.08 mLL per comparison), with 30% of them real but small:
- **The 95% rule** adopts 1.3 of them and gains +0.08 mLL for real.
- **Adopting at P > 0.8** adopts 5.8, of which 2.4 are duds, and gains +0.27: over three times as much.
- **Duds cost almost nothing** if they need no new feed. Charging each one 0.02 mLL still leaves P > 0.8 about three times ahead.

### The caveats

1. **The overfitting lands on the edge estimate.** In the same model, at P > 0.8 the backtest shows +0.74 for changes really worth +0.27. The 95% rule overstates just as badly: it shows +0.26 for +0.08 real. Anything that clears a bar on noisy data clears it partly by luck, so only untouched matches fix this.
   - The clean-holdout proposal already forecasts that the current model's reading on 2025–26 overstates its ~1.4 edge by about 0.35, after about 20 looks at those seasons.
   - **This is where your money is at risk.** If you size Kelly stakes on an edge twice the true one, you earn nothing, and beyond that you lose. Staking on half the true edge still keeps 75% of the growth.
   - So be lenient about what goes into the model, and strict about the edge number you size stakes with. That number has to come from matches no choice has seen.
2. **80% is about direction, not size.** The backfill was P ≈ 0.70, but its whole interval lies between −5% and +9% of the model's edge over the close (+1.37). Adopting it was right because it was free and the prior was good. The test only said "nothing big either way". What decides is expected gain against cost, and a change can be 99% likely to help and still be worth nothing.
3. **The prior that counts is "helps beyond the closing odds".** Domain sense mostly predicts gains *without* the odds:
   - Surface IOS: +0.83 for men without the odds, +0.07 with the close.
   - Offset Elo: +2.24 without a price, +0.13 with the close.

   With the close in, most increments in the docs land within ±0.1. When most ideas are duds (10% real in my model), P > 0.8 gains only +0.085 against +0.027 for the 95% rule. If each dud costs 0.02, adopting whatever points the right way loses money.

   "Known helpful" also oversells the speed data. The adjustment's seasons from 2020 to 2024 read −0.03, −0.04, +0.16, −1.26 and 0.00. The backfill study puts the chance of any one season losing at about 1 in 3.
4. **"Revisit live" works for the whole model, not its parts.** A year of live matches (about 5,000) pins the overall edge to roughly ±1.3, so a year or two answers whether to bet at all. Betting small in the meantime is exactly what fractional Kelly prescribes. But a part the size of the backfill would take decades to resolve live. Part choices are effectively permanent, so make them on expected value and log which ones rode on a lean.

**Where I'd double down:**
- **Tables of many cells.** A table of 9–13 cells will show a P ≈ 0.95 cell by chance about once.
- **Best-of-several readings.** A reading that won among variants is inflated by the selection. The men's profile beat its 52-week and long-memory variants, so its real P is below 0.98.

Decisions should rest on the reading declared in advance. Treat individual cells as flags, and correct selected readings for the selection.

### What I'd change

- **Reporting (mine to fix):** drop "tie". Give the estimate, the interval and P(better), then one of:
  - **better / worse:** the interval clears 0;
  - **leans better / worse:** P ≥ 0.8 or ≤ 0.2;
  - **equivalent:** the whole interval sits inside ±δ, for example ±0.15 mLL (about a tenth of the edge). δ is your call;
  - **unresolved:** anything else.
- **The decision rule (your call), tiered by prior and cost:**
  1. **More of a kind of data already used, with no new live feed:** adopt unless it leans worse or the input check flags it "uneven".
  2. **A new feature with a mechanism behind it:** adopt at P ≳ 0.8, plus the shuffled-twin check. If it needs a new live feed, its gain must also pay for the upkeep. The rebuild proposal's one-SE bar already works out to about P > 0.84, so compare.py's `reading()` is the odd one out.
  3. **The best of many variants:** judge it on the selection-corrected estimate. Ties go to the simplest.
  4. **Both directions:** flag adopted parts that lean worse, such as offset Elo for women at the close.
  5. **Whether to bet, and how much:** decide only from untouched matches, with the edge shrunk.

## 3. The owner's follow-up (9 Oct 2026, verbatim)

> have 2 agents review this logic and the proposal of how we should frame success in a sports betting analytics context.
> My guess is the degree necessary to decalre "implementable" depends on how the change was hypothesized. EDA based on the past? domain intuiton? What is the cost of being wrong?
> A frame work of thinking that neednt be too rigid or all encompassing but will help agents reason about adoption vs non-adoption suggestions going forward

## 4. How the numbers were made

Scratch script: `C:\Users\zerom\AppData\Local\Temp\claude\c--Users-zerom-Documents-Tennis-predictions\1de31848-973c-4af8-87da-129379e1984b\scratchpad\tie_reeval.py` (run with `./python.sh <path>` from the repo root).
* **P(better)** = Φ(estimate / SE), SE = interval half-width / 2.0 (the docs' t intervals have about 50–60 four-week blocks). Flat prior; ignores how many comparisons were run on the same seasons.
* **The threshold model** is analytic (checked by Monte Carlo): each candidate's true gain is a two-point/three-point mixture in SE units; adopt when z_obs > c; c = 1.96, 1.28, 0.84, 0.67, 0. SE = 0.08 mLL. Scenario A: 6 real at +1 SE, 12 null, 2 harmful at −1 SE. Scenario B: real at +2 SE. Scenario C ("fishing"): 2 real, 16 null, 2 harmful. Optional cost of 0.02 mLL per adopted null. Outputs: expected adoptions, nulls adopted, true gain, backtest (measured) gain, inflation, exaggeration of adopted real effects.

Key outputs (expected totals over 20 decisions, mLL):

| Scenario, rule | adopted | nulls in | true gain | backtest gain |
|---|---|---|---|---|
| A, 95% (P>0.975) | 1.3 | 0.3 | +0.081 | +0.258 |
| A, P>0.80 | 5.8 | 2.4 | +0.265 | +0.735 |
| A, P>0.50 | 11.4 | 6.0 | +0.378 | +0.916 |
| B, 95% | 3.4 | 0.3 | +0.495 | +0.743 |
| B, P>0.80 | 7.7 | 2.4 | +0.836 | +1.215 |
| C, 95% | 0.7 | 0.4 | +0.027 | +0.143 |
| C, P>0.80 | 4.4 | 3.2 | +0.085 | +0.518 |
| C, P>0.50, cost 0.02/null | 10.0 | 8.0 | −0.051 | +0.697 |

## 5. Where the cited evidence lives (verify against these)

* Comparison machinery: `src/eda/current_best_model/compare.py` (`reading()` ~line 280, docstring lines 1–40); `src/eda/serve_speed_tabpfn/score.py` (`paired_stats`, `cluster_se`, ~lines 386–412).
* The current-best-model decision, incl. the backfill amendment: `docs/decisions/2026-10-08-current-best-model.md` (line ~36).
* The backfill study, incl. the per-season speed record and the "1 in 3 losing seasons" forecast: `docs/studies/infosys_atp_backfill/README.md` §4–5 (lines ~121–200).
* Surface IOS decision: `docs/decisions/2026-10-06-surface-ios-profile.md` (lines 15–37).
* Offset Elo decision: `docs/decisions/2026-10-06-offset-elo.md` (lines 28–55).
* Speed adjustment decision: `docs/decisions/2026-10-07-speed-nudge.md` (evidence table lines ~49–62).
* Challenger rows: `docs/studies/event_levels/README.md` (lines ~212–222).
* Men's profile vs the close: `docs/studies/match_timing/README.md` (lines ~296–305); its origin `docs/studies/ufc_ideas/stageD.md` (lines ~9–16).
* Speed adjustment 2020–24 (before the 8 Oct corrections): `docs/studies/training_window/README.md` (lines ~134–152).
* Clean-holdout proposal: `docs/studies/clean_holdout_rebuild/README.md`; selection-bias arithmetic `02_contamination_and_forecast.md` (§1, §3); the proposed selection protocol (1-SE add rule, shuffled twins, winner's-curse correction, neutral members) `03_rebuild_stages.md` (lines ~100–150).
* Project working rules: `CLAUDE.md` (repo root); feature timing / leak probe: `docs/decisions/2026-10-05-match-timing.md`.

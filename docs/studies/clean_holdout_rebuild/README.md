# Rebuilding the model with 2025–2026 as an "as clean as possible" holdout

8 October 2026 · Written for the owner and for the language models that will review, improve and execute it · **A proposal for review, not a decision.** Nothing here has been run.

The owner's request (8 Oct 2026): construct a rebuild and fresh feature selection whose holdout is 2025–2026, as clean as it can be made; estimate how clean that is, as a forecast of how much of the holdout edge will be optimistic; and write up what has to be rebuilt and how, leaving room for several other models to improve and criticise the process.

**This folder contains no 2025–2026 result, and must keep it that way.** It can therefore be handed to a reviewer or an executor as a blinded brief. The audit it builds on ([feature provenance](../feature_provenance/README.md)) does quote 2025–2026 results. Only the reviewers whose role needs it read that audit ([04_review.md](04_review.md)).

## The design in one paragraph

**The holdout.** H is every match of the 2025 and 2026 seasons (from the events of 30 Dec 2024), in two parts:
* **H-exposed:** 2025 to 28 Jul 2026, 8,593 main-tour matches. Earlier studies have read it about 20 times.
* **H-sealed:** events from 29 Jul 2026 onward, which no model choice has read and which keeps growing.

**The development data.** D is every season up to 2024. Men's 2018 joins it now that its odds exist.

**The rebuild.**
* **Numbers.** Every number that touches the model is fitted on D or set by a written rule.
* **Choices.** Every choice is made on D by a codified selection that no current-model value can steer. Executor agents work in a clean room without H outcomes or H-derived reports.
* **The menu.** The selection draws on the whole menu of 603 built columns. The current model's choices enter as alternatives on an axis, not as the default.
* **One look.** The design is frozen and hashed, its H forecasts are written, and H is scored once.

**What re-selection cannot clean.** An earlier choice made on windows containing 2025–2026 leaves an imprint on H whenever the rebuild repeats it. So the report gives three numbers side by side:
* the raw H edge;
* the edge corrected by a sealed estimate of each repeated choice's selection bias;
* the edge on H-sealed alone.

**Relation to the feature-provenance plan.**
* Its phase 0 (sealing the post-frame matches) and phase 3 (the decision bootstrap) are prerequisites here.
* Its phase 7 assumed 2025–2026 would become development data. This protocol is the alternative the owner asked for: 2025–2026 as the holdout. The owner chooses one; both cannot hold.

## How clean can it be? The forecast

All figures are mLL (milli-log-loss per match). The forecast is the expected upward bias of the H edge (+ = the holdout flatters the model), both tours, against the recalibrated average close. The reasoning and every input are in [02_contamination_and_forecast.md](02_contamination_and_forecast.md).

| | Stage 1 (both tours) | Stage 2 (men's speed gain) |
|---|---|---|
| Rebuild, raw H edge | **≈ 0.2** (plausible 0.05–0.45) | ≈ 0.15 (0.05–0.3) |
| Rebuild, after the bias correction | **≈ 0.1** (0–0.25) | ≈ 0.05 (0–0.15) |
| For comparison: the current model read on H-exposed as it stands (inferred) | ≈ 0.35 (0.2–0.6) | ≈ 0.25 (0.1–0.4) |
| Sampling noise of the H estimate (1 SE; not a bias) | ≈ 0.5, so ±1.0 at 95% | ≈ 0.25 (a paired gain on 4,394 men's matches) |

* **As a share of the edge.** The current design's edge over the close in 2020–2024 (D data) was +1.46 [+0.84, +2.08]. If the rebuilt model's true edge is near that level, its H edge is optimistic by about **15% raw (4–30%) and about 5–10% after correction (0–17%)**.
* **Leakage will not be the main error for stage 1.** With about 8,600 matches the holdout's own noise is ±1.0 mLL at 95%, five to ten times the forecast bias. Making H cleaner than this has diminishing returns; adding sealed matches does not.
* **For stage 2 the bias matters more.** The raw bias (≈ 0.15) is over half of one SE (≈ 0.25). The correction brings it down to about a fifth, so the stage-2 reading depends more on the correction.
* **The residual has one main source:** the choices the rebuild repeats because D agrees with them. The forecast assumes several:
  * the offset Elo;
  * the odds as an input;
  * the speed adjustment's form and memory;
  * the TabPFN learner.

  Re-selecting cannot remove an imprint already left on H. Subtracting a bootstrap estimate of it can.
* **Not in these numbers: a change of era.** The edge lives in 2020+ seasons. Whether it lasts beyond 2026 is not leakage, and only H-sealed and later matches can show it.

## What has to be rebuilt

The full inventory, with each component's current provenance and the action, is in [03_rebuild_stages.md](03_rebuild_stages.md). The stages:

| Stage | What | Gate before the next |
|---|---|---|
| 0 | Freeze, seal H-sealed, set up the clean room and the access log | owner approval; hashes logged |
| 1 | Data, outcome-agnostic: the known box-score fixes applied to every season, odds refreshed, men's 2018 added, match clock and speed panel refreshed | each fix justified by data evidence only; changelog |
| 2 | Features: rebuild every as-of feature over 2010–2026 at frozen D constants, plus the axis variants (memories, representations); leak probes | probes pass; store hash |
| 3 | Quarantine: split the store into D (seasons ≤ 2024) and H (sealed); build the clean room | the executors' folder has no H row |
| 4 | Pre-registration of the selection (menu hash, axes, rules, eras, seeds, costs); review rounds R0–R2; freeze | decision log entries approved |
| 5 | Rehearsal: the whole protocol on D' (≤ 2022) with 2023–2024 as a pseudo-holdout | process transfers, or the protocol changes now |
| 6 | Selection campaign on D, by blind executors | per-round logs; nulls and twins |
| 7 | Finalists, the winner's-curse-corrected D estimate, per-tour reads, the stage-2 decision (men, 2022–2024) | one frozen, hashed design |
| 8 | H forecasts, walk-forward (2025 from ≤ 2024, 2026 from ≤ 2025); the one look; the sealed bias correction opened after the look | look logged |
| 9 | Report: raw, corrected and sealed-only edges; contamination diagnostics; the current model as a report-only anchor | — |
| 10 | Prospective continuation on H-sealed checkpoints | pre-registered |

* **Estimated effort.**
  * Data and features: about 2–4 days, mostly compute.
  * Review: calendar time.
  * Rehearsal and selection: about 15–40 GPU hours (a full-size local TabPFN fit takes about 33 s).
  * Scoring and report: a day.

## How to review and improve this

[04_review.md](04_review.md) holds the process:
* **The roles:** holdout auditor, statistician, data engineer, tennis-and-market critic, red team, and optionally an independent protocol author.
* **The rounds:** independent critiques, then rulings, then a focused re-review, then the freeze.
* **The finding template.**
* **The rules:** a suggestion must rest on mechanism or D-only evidence; anything that cites 2025–2026 results is declined.
* **The index** of numbered open questions, Q1–Q29, which the documents raise where they arise. Q28–Q29 come from the [close-drift study](../close_drift/README.md), which reads seasons ≤ 2024 only.

Rulings go into [decision_log.md](decision_log.md). The owner decides anything contested.

## Files

| File | Content |
|---|---|
| [01_contract.md](01_contract.md) | Windows, what may touch H, the rules with no current-model value in them, estimands, pre-registered responses |
| [02_contamination_and_forecast.md](02_contamination_and_forecast.md) | Every channel by which 2025–2026 is already known, its mitigation, its residual, and the forecast's arithmetic |
| [03_rebuild_stages.md](03_rebuild_stages.md) | The rebuild inventory and stages 0–10, including the selection protocol |
| [04_review.md](04_review.md) | The multi-model review process, templates and open questions |
| [decision_log.md](decision_log.md) | Proposed entries awaiting rulings |

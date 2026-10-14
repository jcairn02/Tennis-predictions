# 04: Review by several models

The protocol is meant to be improved and attacked before it is frozen. This document sets out who reviews, what each reviewer may read, how findings are written, how they are ruled on, and which questions are open.

## 1. What reviewers may read

* **This folder is a blinded brief.** It contains no 2025–2026 result, and every reviewer reads all of it. A reviewer who finds a 2025–2026 result in it reports that as a blocker.
* **The feature-provenance audit** (`docs/studies/feature_provenance/`) quotes 2025–2026 results. Only the **holdout auditor** and the **red team** read it, because finding leak paths needs it. Their suggestions must still rest on mechanism or D-only evidence.
* **Off limits to everyone:** the rest of `docs/studies/`, the studies index and the decision records. The protocol does not need them, and they quote 2025–2026 results. A reviewer who has read them anyway says so in the front matter.

## 2. Roles

Use at least three roles, from different model families where possible. One model may take two roles in separate sessions, not in the same one.

| Role | Task |
|---|---|
| **Holdout auditor** | Find every path by which 2025–2026 information can enter a fitted number, a choice, a default, an axis, the menu, the scoring or the report. Extend the channel table in `02_contamination_and_forecast.md` §2. Challenge every p, ρ and k there |
| **Statistician** | Check the selection algebra and the bias correction (Q13); the nulls and twins; the winner's-curse correction; era fits against per-season fits (Q9); intervals and power; whether the forecast's ranges are honest |
| **Data and pipeline engineer** | Check feasibility, the timing of every feature, the match clock, the data-fix list (Q19), the quarantine and the clean room (Q14), compute cost, reproducibility and hashes |
| **Tennis and market critic** | Check the family definitions, axes and neutral members; per-tour issues (Q11); the benchmark (Q15); stage 2's speed data (Q12, Q21); whether any default encodes knowledge of what worked recently |
| **Red team** | Try to produce a fake edge on H under this protocol: describe the scenario, the step it exploits and the fix. Attack the forecast's numbers. Look for defaults that favour H |
| *Optional:* independent protocol author | Read only `README.md` and `01_contract.md`. Write your own stage-4 selection design *before* reading `03_rebuild_stages.md`. The differences are reviewed in R1 |

## 3. Rounds

| Round | What happens | Output |
|---|---|---|
| **R0** | Independent critiques; reviewers do not see each other's | `reviews/R0_<role>_<model>.md` |
| **R1** | Each finding is ruled on: accepted, modified or declined, with the reason. Contested findings go to the owner. Accepted changes are made to the protocol | entries in `decision_log.md`; edited protocol files, changes listed |
| **R2** | Focused re-review of the changed sections, plus the red team's second pass | `reviews/R2_<role>_<model>.md` |
| **Freeze** | The protocol folder is hashed and logged. From here only deviations are logged, and no protocol edit is made before the look | hash in `decision_log.md` |
| **After the look** | A verifier reproduces every H number from the frozen hash and checks the look ledger and the executors' read logs | `reviews/post_look_verifier_<model>.md` |

## 4. Finding template

```
---
reviewer: <model, version>
role: <role>
round: R0
date: <yyyy-mm-dd>
documents_read: [README.md, 01_contract.md, 02_contamination_and_forecast.md, 03_rebuild_stages.md, 04_review.md]
read_2025_2026_results: no | yes: <which files>
---

| ID | File, section | Finding | Severity | Category | Proposed change (exact text if possible) | Effect on H's cleanliness | Evidence: mechanism or D-only |
|---|---|---|---|---|---|---|---|
| A1 | 03 §5.4 | ... | blocker / major / minor | leak / statistics / data / cost / domain / clarity | ... | cleaner / neutral / less clean | ... |
```

* **blocker:** H can leak, or the result would be invalid.
* **major:** a material bias, power loss or cost.
* **minor:** clarity or a small improvement.

## 5. Rules for reviewers

1. **No 2025–2026 result as evidence**, for or against anything. Rest each suggestion on a mechanism or on D-only evidence (seasons ≤ 2024).
2. **Do not propose** reading H early, re-tuning anything on H, or choosing among protocol variants by their H result.
3. **Prefer changes that make H cleaner.** Say plainly when a change would make it less clean, and why it is worth it.
4. **Be specific:** file, section and the replacement text.
5. **Give every number** its direction (e.g. "mLL, + = model better"), and call it a tie when its interval spans 0.
6. **Treat other reviewers' findings as claims to verify,** not as conclusions.

## 6. How findings are ruled on

* **Findings that make H cleaner** are accepted unless the owner rules the cost too high.
* **Findings resting on 2025–2026 results** are declined, whatever they suggest.
* **Ties** between reasonable options go to the neutral default.
* **Every ruling** is recorded with its reason. Declined findings stay in the log.

## 7. Briefs for each role (ready to paste)

**Shared preamble.** You are reviewing a protocol for rebuilding a tennis match-winner model and re-selecting its features, so that the 2025–2026 seasons can serve as a holdout that is as clean as possible. Read every file in `docs/studies/clean_holdout_rebuild/`. Write your findings with the template in `04_review.md` §4 to `docs/studies/clean_holdout_rebuild/reviews/R0_<role>_<model>.md`, and edit no other file. Follow the rules in §5. Above all, never use a 2025–2026 result as evidence.

* **Holdout auditor.** You may also read `docs/studies/feature_provenance/README.md`, `plan.md` and `data/studies/feature_provenance/provenance_58.csv`. Find every route by which knowledge of 2025–2026 outcomes reaches a number, choice, default, axis, menu entry, scoring step or report. For each, say whether the protocol removes it, and estimate what remains in mLL with the reasoning of `02` §1.
* **Statistician.** Check `02` §1 and §4 (the imprint algebra and the bootstrap correction), the add rule and twins of `03` §5, the finalist correction, the power figures and the forecast's ranges. Where you disagree, give your own estimate.
* **Data and pipeline engineer.** Walk through `03` §1–§4 as if you had to run them. List what is missing, what would break, what will take longer than stated, and how to prove the clean room holds no H row and no H-derived report.
* **Tennis and market critic.** Read the axes and neutral members in `03` §1 and §5. Say which families or alternatives are missing, which neutral members are not neutral, and where tennis structure (tours, surfaces, levels, best of five, retirements, speed data by tour) breaks an assumption.
* **Red team.** Assume an adversary wants this protocol to report a large edge on 2025–2026 that will not hold afterwards. Describe the attacks it could mount within the rules, and the change that stops each one. Then attack the forecast in `02` §3.

## 8. Open questions

| Q | Question | Proposed default |
|---|---|---|
| Q1 | H by season (from the events of 30 Dec 2024) or by date (from 1 Jan 2025)? | by season, as the frame |
| Q2 | H-sealed inside the primary estimand, or reported apart? | inside, with the parts reported |
| Q3 | Walk-forward inside H, or D-only fits for all of H, as the primary? | walk-forward primary; D-only secondary |
| Q4 | Era layout: choose on 2020–21 and 2022–23, confirm on 2024, fragile 2016–19? | as proposed; reviewers may argue for others |
| Q5 | Keep the constants tuned on 2013–2018, or re-tune them on recent D eras? | keep; re-choose only H-exposed ones |
| Q6 | Learner fixed by mechanism, or chosen on D? | fixed; D check reported |
| Q7 | Temperature: 1.0, or chosen from {0.8, 0.9, 1.0} on D? | chosen on D, interior tie-break |
| Q8 | Forward family selection, a backward walk, or both? | **Ruled in principle by the owner on 9 Oct 2026** (a decision record, off limits under §1; its content is in `03` §5, item 4): neither as first drafted. Top-down removal over a cluster tree fixed before any score, with stability (`03` §5, items 4–7, redrafted). The first draft's proposed default was "forward, then a backward clean-up" |
| Q9 | Era fits or per-season fits for selection scores? | era fits (cost); per-season for the final |
| Q10 | Exclude market-internal columns? | exclude |
| Q11 | The per-tour gating rule | as in `03` §5.8 |
| Q12 | Stage-2 axes; τ fixed at 0.05 or an axis? | τ fixed (set before 2024–26 was read) |
| Q13 | Is the bootstrap bias correction valid when carried from the current model's context to the rebuild's? | yes, as an approximation, with its caveats stated |
| Q14 | Is folder scope plus logged reads enough to blind executor agents? | yes, with the auditor checking logs; stronger isolation welcome |
| Q15 | Primary benchmark: the recalibrated average close, or Betfair Exchange? | the average (continuity; it can be recalibrated on D) |
| Q16 | The response thresholds (`01` §5) | as proposed |
| Q17 | Is the rehearsal worth its cost? | yes |
| Q18 | Men's 2018 in D? | yes |
| Q19 | Which data fixes, and how to show each was decided without outcomes? | the list in `03` §1, each with source-against-source evidence |
| Q20 | Looks: one at the freeze, then H-sealed checkpoints? | yes |
| Q21 | Stage 2 for men without speed data | adjustment 0, as today |
| Q22 | The scored population | main-tour main draws with odds, completed or retired, debut seasons excluded |
| Q23 | Seeds: 3 in selection, 8 in the final? | yes |
| Q24 | The finalist correction σ · m_F | yes |
| Q25 | If the rebuild reproduces the current model almost exactly, anything beyond the correction and H-sealed? | no; disclose |
| Q26 | Run the a-priori-menu sensitivity (a second campaign with only ideas proposed before any 2022+ result)? | optional, after the main |
| Q27 | Who rules on contested findings? | the owner; ties to the neutral default |
| Q28 | The close is an input, so the model learns how far to move away from it, and that value drifts. On D, the realisation of the model's disagreement with the close was 0.60 in 2015–2019 (over-reacting) and 1.29 in 2020–2024 (under-reacting); see `docs/studies/close_drift/`. Should the training window be an axis? **D-only evidence, 8 Oct 2026** (`docs/studies/training_window/`, scored on 2020–2024): no window beat expanding, whether the last 7, 5 or 3 seasons, recency-weighting or a size-matched random draw. Every estimate was below 0 and every interval spanned 0. The short windows moved further from the close and over-shot: TabPFN's realisation against Pinnacle was 0.80 and 0.67 for the last 5 and 3 seasons, against 0.98 for expanding. | yes: expanding (neutral), the last N seasons, or recency-weighted, chosen on D and confirmed on 2024 |
| Q29 | A two-part recalibration: a slope for the close and a separate, walk-forward scale for the model's disagreement? And a Pinnacle-scored sensitivity, given that the books' average was softer than Pinnacle by +0.82 in 2020–2024 (+ = the average softer)? **D-only evidence, 8 Oct 2026** (`docs/studies/training_window/`): the walk-forward two-part form tied the one-slope rule. Fitted on 2019 .. Y − 1: −0.07 [−0.32, +0.17]. Fitted on the last two seasons: −0.25 [−0.56, +0.06], and worse in 2022–23. + = the two-part form better. | an axis on D; Pinnacle as a D-side sensitivity only (Pinnacle on file ends in Jan 2026) |
| Q30 | The redraft's constants (`03` §5, items 4–5): the column price from three twin draws; the merge at mean \|r\| ≥ 0.8; each node's column budget and its compression; the per-block power check before any score; 200 resamples and the two-thirds rule for dropping a node. Added 9 Oct 2026 | as written; reviewers may argue for others |

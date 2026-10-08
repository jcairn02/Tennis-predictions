# The team

Fixed by the lead on 7 October 2026, before any agent ran. Five Opus 5.5 agents and the lead (the main session). The owner allowed 3–10.

## Why this shape

The task has three hard parts, and each needs its own expert:
* the **data**: six speed sources on two bases (key statistic and point mean) and five measuring systems, with the coverage holes;
* the **statistics**: a noisy, irregularly observed state for players with little data;
* the **model**: TabPFN's use of a weak, mostly missing input, with the market as the benchmark.

Two kinds of failure have hurt this project before. Independent checkers guard against each:
* leaks and bugs in a build. The feature-interactions study's harness verifier found 14 bugs before its screen;
* tests that read the holdout before they were fixed.

## Roles

| # | Agent | Rounds | Owns | Must not |
|---|---|---|---|---|
| 1 | **Speed-data engineer** | R1 proposal, R3 build | One leak-proof per-player-match speed panel from every source: source choice per match, basis and system offsets, plausibility, linking to the model's Stage 0, the clock days (`es`, `lf`, `obs`), and coverage maps | relate speed to any result |
| 2 | **Bayesian state modeller** | R1 proposal, R3 build | The speed-state model and its priors: shrinkage for thin histories, a missing-data policy, constants tuned on result-free targets ≤ 2023, the candidate columns | tune on match results |
| 3 | **Integration strategist** (TabPFN and market) | R1 proposal, R3 build | How the columns enter TabPFN; the arms; the fit runner and the expanding-window scorer (with/without odds, 24-hour price); power and the draft pre-registration | run GPU fits (the lead runs them) |
| 4 | **Auditor and red team** | R2 ruling, R4 red team, R5 report check | Rulings on the three proposals (errors, leaks, power, multiplicity); then an independent re-implementation of the primary feature and a leak probe on the build; finally the report against the outputs | build what it audits |
| 5 | **Test verifier** | R4 | `score.py` on synthetic outcomes (planted effect recovered, null not rejected too often); the pre-registration against the code | read any real 2024–2026 result |

**The lead (main session):**
* writes the brief;
* relays between agents and checks their claims on disk;
* keeps the look ledger;
* freezes the pre-registration;
* runs every TabPFN fit and the one scoring run;
* writes the report.

## How they work together

* **A shared workspace.** Every agent reads the brief and every earlier round's files in `data/studies/serve_speed_tabpfn/design/`. The proposals are independent: R1 agents do not read each other's R1 files.
* **Messages go through the lead.** The lead relays rebuttals, data facts and the auditor's rulings, and continues each agent with its context kept.
* **The auditor's ruling settles disputes,** after at most one rebuttal round. The lead can overrule only with a written reason in `design/lead_notes.md`.
* **Builders own their modules; verifiers own their checks.** No one verifies their own build.

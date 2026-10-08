# Feature interactions: the agent team and how it works

6 October 2026. The owner asked for a multi-agent deep dive, with roles from brainstormer to auditor to meta-auditor, working back and forth, all on Opus. This is the configuration, fixed before the first agent ran, and why. Shared context for every agent: [brief.md](brief.md).

## Design principles

1. **Diverge independently, then converge.** Ideas from agents that have seen each other's lists, or the literature, correlate. Brainstormers work in parallel and blind to each other and to the literature in round 0; the literature joins in round 2.
2. **Different lenses, not copies.** Four brainstormers each get one lens, so their errors and blind spots differ.
3. **Generation and judgement are separate agents.** An auditor has no stake in an idea. A brainstormer may rebut a verdict once, with an argument or a fix; the auditor rules on the rebuttal.
4. **Data settles disputes.** Arguments that cannot be resolved go to EDA on 2013–2021 (discovery) and 2022–2024 (replication). 2025–2026 stays closed until the pre-registered test.
5. **A meta-auditor watches the process, not the ideas**: forking paths, multiple testing, leakage, gates applied unevenly, claims beyond the evidence.
6. **One blackboard.** Every list, critique, rebuttal and result is a file in this folder, so every agent reads the same state and the trail can be audited.

## Roles (all Opus)

| Role | Agents | Job | Writes |
|---|---|---|---|
| Orchestrator | the main session | context, merges, gates, the EDA harness, every TabPFN fit, the report | `README.md`, `master_list.md`, `plan.md` |
| Data cartographer, then feasibility auditor | 1, continued | maps the feature universe: every input built so far, raw per-player data, coverage by year and tour, timing class; a register of what earlier studies tested and how it fared against the close. Later rules on each idea's data needs and leak risk | `round0/inventory.md`, `round1/feasibility.md` |
| Literature scout | 1 | what other modellers published (2015–2026, academic and practitioner) on matchups and interactions in tennis prediction and betting, especially against bookmakers | `round0/literature.md` |
| Brainstormers | 4 | interaction hypotheses in the brief's template, one lens each: **mechanics** (point structure, serve and return, style, surface, conditions); **mathematics** (Markov composition, symmetry, variance, uncertainty, what differences hide); **market** (where prices err, by context); **body and schedule** (load, recovery, age, travel, format) | `round0/ideas_<lens>.md`, then `round2/rebuttal_<lens>.md` |
| Mathematical auditor | 1, continued | per idea: symmetry, identifiability, redundancy with the 58 inputs, a quick derivation or bound on the effect, power, the right EDA test. Rules on rebuttals | `round1/math_audit.md`, `round2/rulings.md` |
| EDA analysts | 2 | build the shortlisted features leak-proof and run the shared screen; one on serve-return structure, one on context, body and market | `src/eda/feature_interactions/`, `round3/` |
| Meta-auditor | 1, continued | checkpoint 1: the shortlist and the EDA plan before any outcome is computed. Checkpoint 2: EDA results and the TabPFN plan. Checkpoint 3: the final test and the report | `meta/checkpoint_<n>.md` |
| Configuration critic | 1 | critiques this configuration at the start; its useful points are adopted in later rounds | `round0/team_critique.md` |

## The cone

| Round | Who | In | Out | Gate |
|---|---|---|---|---|
| 0 | cartographer, scout, 4 brainstormers, critic (parallel) | brief | inventory, literature, four idea lists | – |
| 1 | orchestrator, then mathematical and feasibility auditors (parallel) | idea lists, inventory | master list; verdicts: pass, refine, kill | **G1** a mechanism, and a reason the 58 inputs and the price cannot already hold it. **G2** buildable from data held, leak-safe, enough coverage before 2022 |
| 2 | brainstormers (rebut, refine, add from the literature), auditors (rule) | verdicts, literature | EDA shortlist with each candidate's pre-declared test | survivors of G1–G2 after rebuttal |
| M1 | meta-auditor | shortlist, EDA plan | amendments | the plan is fixed before any outcome is computed |
| 3 | EDA analysts on the orchestrator's harness | shortlist | out-of-sample gains, 2013–2021 and 2022–2024 | **G3** a gain beyond the price and beyond the current best model's own forecast in discovery, with the interaction adding beyond its main effects. **G4** replicates in 2022–2024, after multiplicity control |
| 4 | mathematical auditor, meta-auditor | EDA results | at most about six finalists; pre-registration | **G5** TabPFN gain on the 2019–2024 walk-forward windows |
| 5 | orchestrator | finalists | local TabPFN fits; the pre-registered test on 2025–2026 | primary endpoint |
| M3 | meta-auditor | results, draft report | corrections | claims match the evidence |

## Why this shape

* **Four brainstormers rather than one long one.** One agent's list is one sample from one prior. Four lenses give coverage of the space; merging them costs one deduplication pass.
* **Two auditors with different jobs.** Mathematical soundness and data feasibility fail in different ways, and an agent asked to check both tends to check the one it is better at.
* **The cartographer becomes the feasibility auditor** (continued, not restarted), so the inventory's context is reused.
* **The EDA screen is the orchestrator's code**, shared by both analysts, so every candidate is judged by the same test, on the same matches and the same folds.
* **The screen tests against the current best model's own out-of-sample forecast**, not only against the price. An interaction TabPFN already learns from its 58 inputs adds nothing to it, however strong it looks against the price alone.
* **The meta-auditor comes in at three fixed checkpoints**, before outcomes, after EDA and before the final claim, because that is where forking paths open.

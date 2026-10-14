# The adoption framework, extended to adoption by kind of change: process log

9 Oct 2026, about 19:00 – 21:10 (local, UTC−7) · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) · Session:
`c0f7c8d9-cc78-498f-9409-72258b59a7dd` · For a future reviewer · Report: [README.md](README.md) and the
[decision](../../decisions/2026-10-09-adoption-by-change-class.md)

**Scope of this log.** The work of 9 Oct 2026, evening, that extended the framework adopted earlier that day: adoption by
kind of change, the pool and selection rounds for new features, and the amendment to the level-evidence study's
decision rules. The framework's first version (9 Oct, earlier sessions) is not logged here. Per the
[process-log decision](../../decisions/2026-10-09-study-process-logs.md), anything about it is reconstructed, not
contemporaneous.

**Opened late.** The log was opened at 20:05, after the steps of § 4's first nine rows. Those rows were written then,
from this session's own record: the transcript and the files' times. Later rows were written as the work happened.

## 1. The request

* **The owner's words, verbatim** (9 Oct 2026, about 19:00):
  > "I have a problem with the way the agents adopt features, data or changes.
  > The over emphasis on statistical significance will make clear mistakes when not taken into consideration the scope of the change.
  >
  > For example, the strategy is to add new data as it arrives obviously so it can be used in the model. More fresh data is clearly better statistically for future predictions.
  >
  > However, if you evaluated this via "statistical significance"
  >
  > In a model that has 10,000 rows compared to the new model that has 10,100 (100 new rows of the newest data), they will be nearly identical and no statistical signifiance will show.
  >
  > NOT ALL DECISIONS SHOULD BE DONE IN THIS COMPARITIVE BEFORE + AFTER WAY!
  > As thats the case the model will never grow incrementally.
  >
  > There are decisions that dont matter individually but matter COMBINED together. For examples 20 sets of 100 new rows, individually arent predictive, but together they are.
  >
  > The vocabulary and thought that has to go into how we can improve the model needs to deeply consider information like this. How its currently wired is too one dimensional. We have SOME rules that we recently implemented that widen the way of thinking these problems, but I fear they arent being used or they are reasoned out poorly.
  >
  > Think deeper about this problem"
* **The follow-up, verbatim** (about 19:30):
  > "Before you implement anything I have a question.
  >
  > Maybe I should never do individual feature studies on a "should I add this to the model" capacity? its more I should wonder if it makes any sense to add it to a future feature selection process? as features are almost only ever helpful together unless they are the very very best features. So its like no it shouldnt be adopted, but it should be included in a process that finds clusters of statistics?"
* **The instruction, verbatim** (about 19:45): "I accept your adoptation logic, implement it"
* **How it was read:**
  * **Acted on:** "implement it" covers every item the two chat answers promised "on a yes":
    * the level-evidence study's decision rules, first, because its arms were being built;
    * the framework amendment and a decision record;
    * CLAUDE.md;
    * a resolution read of `compare.py`'s output;
    * the two policies (in-season live fits, the holdback);
    * the pooled record;
    * the rebuild's selection redrafted around clusters;
    * checklist item 9 re-filed.
  * **Set aside:**
    * a narrower reading, the framework text only, because the answers had listed concrete items under "on a yes";
    * editing `compare.py` itself, for the reason in § 6, call 3.
  * **No question was put to the owner.** The instruction was explicit.
* **The target:** none of a model study. This work scores no model and reads no outcome-based result. It changes how
  other studies' readings become recommendations.

## 2. Starting point

* **Code:** commit `677a63f`, with many uncommitted changes from other sessions (git status at the session's start).
  The only code this work ran is the two new calculation scripts (§ 10); they read no data file.
* **Data:** none read. Every number used was copied from a document, with its source cited where it is used.
* **Earlier looks:** none by this work. The scripts' inputs are standard errors and estimates already published:
  * the training-window study (seasons ≤ 2024);
  * the level-evidence study's power note (written before any of its scores).
* **Environment:** `./python.sh` (the `tennis` conda environment): numpy, scipy.
* **The idea and how it arose:** a change to how decisions are made, from the owner's challenge. Claude's diagnosis
  rests on mechanism (what a comparison of a given size can resolve) and on the project's own documents.

## 3. Plan

As first written, in the two chat answers, before the instruction:
1. Before SYS and the new-data arms are scored: a dated amendment to the level-evidence study's decision rules, with
   its measurements untouched, handed to the session that owns the study.
2. Amend the framework and CLAUDE.md:
   * a § 0 table of kinds of change;
   * the resolution check and the rules' rates;
   * μ₀ in the arithmetic;
   * policies, the holdback and the pooled record;
   * "too small to matter → decide on simplicity" and "slices of one comparison are one reading";
   * better/worse/unresolved labelled as reporting only.
3. `compare.py`: print each reading's resolution and, given a kind, the kind's decision mode.
4. Two policies to decide once:
   * live fits include the season's completed matches;
   * a monthly holdback comparison.
5. A pooled record, started from readings already on file.
6. From the second answer:
   * new features go to the pool by default;
   * checklist item 9 and the share-signal candidate become pool admissions;
   * the rebuild's selection (its Q8) is redrafted as top-down cluster testing, removal within clusters and stability
     selection.

## 4. Chronology

Local time (UTC−7). "Results" means any outcome-based score of any candidate. This work saw none beyond published
numbers.

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| ≈19:00 | Read the framework, its decision, checklist, ledger, the statistics review, the current-best-model decision, the lower-level dossier, training-window and centring studies, the lean review's rule lines, the memories | Find where the one-dimensional reasoning lives | Published readings only | – |
| ≈19:12 | Found the level-evidence study writing a rule for new data (`F_rule_data.md`, 19:10); read its SPEC rules, addition 1's interpretation, D's power note; listed which arms had fits and score folders (names only) | The likely trigger, and the live case | D's power note (written before any score) | – |
| 19:18 | `rule_oc.py` (scratch): the SPEC rule's rates; the new data's chance to read "better"; the sign rule's hit rate; a learning curve through the training-window study's three random-draw arms | Make the diagnosis quantitative | Training-window estimates (2020–24, published) | Became `resolution_check.py` (§ 10) |
| 19:21 | Memory: `score-direction-labels` marked reporting-only (its stale "compare.py prints tie" line removed); `adoption-beyond-before-after` saved | The owner's direction, for later sessions | – | Memory files |
| ≈19:22 | First chat answer: the diagnosis, the kinds table, five missing ideas, recommendations | The owner asked to think deeper | – | Chat |
| ≈19:30 | Read the feature universe (§ 6) and the clean-holdout rebuild (README; § 5 of `03_rebuild_stages.md`) | The owner's pool question; the pieces already existed | – | – |
| ≈19:35 | Second chat answer: pool + selection rounds, the rebuild's forward rule critiqued, the cluster-tree design | The owner's question | – | Chat |
| ≈19:45 | The instruction. Re-listed the study's arms: SEP_ALL and REF_noITF had fits and part-1 folders; SYS_w0 being built. Read `preregistration.md` and additions 1–3 in full | Implement, the time-critical item first | – | – |
| 19:46 | Checked the two "scored" folders by file name: part-1 files only, no `scores.csv` | Whether the amendment could still be blind | None: no model-level score existed | – |
| 19:52 | `amend_oc.py` (scratch): the registered and amended rules' rates from the study's own SEs | The decision asks rules to state their rates | – | Became `level_evidence_rules.py` |
| 19:53 | Hashed the study's pre-registration files; all equal their recorded hashes | Record the state | – | – |
| 19:54 | Both scripts copied into `src/eda/adoption_framework/`; outputs written | Keep the calculations in the repo | – | `level_evidence_rules.out`, `resolution_check.out` |
| 19:55 | Wrote and hashed `data/studies/lower_level_evidence/system/owner_decision_2026-10-09.md` | Replace the study's decision layer before any score | None | The amendment + `.sha256` |
| ≈19:56 | Read `system_pairs.py`: its guard globs `preregistration*.md` and `*addition*.md`; it imports `compare.py`'s recipe | Would the file or a `compare.py` edit break the running study? | – | Decision: leave `compare.py` untouched (§ 6, call 3) |
| 19:58 | Wrote the decision record; added its index row (another session had added a row meanwhile) | The owner's acceptance is a decision | – | `docs/decisions/2026-10-09-adoption-by-change-class.md` |
| ≈20:00 | Messages to `tennis-predictions-f5` and `tennis-predictions-0e`, the two busy sessions; the study's lead could not be identified | Hand over the amendment | – | Delivered to both inboxes; not yet read |
| 20:03 | Read the new process-log decision (added by another session at 19:58) and its template | It covers this extended study | – | This log, opened 20:05 |
| 20:08 | Message from `tennis-predictions-f5`: the study's lead adopted the amendment in full as `preregistration_addition_4.md` (19:59:56; sha256 `754e055c…`, equal to its record), before any score. Read it: sections 1–5 restated faithfully; "the owner's file governs" where texts differ; code changes to be hashed in an addition 4b | Confirm the handover | None | Addition 4 records the decision record's hash `e72e9ae2…` (checked equal). **So the decision record is kept byte-stable from here;** later notes go in the framework and this log |
| 20:10–20:25 | Amended the framework README: header, § 0 (new), "In short", §§ 2, 4, 5, 7 and 9 amended in place, §§ 10–11 (new), Known problems, Files. Section titles kept, since other docs link to §§ 2, 4, 6, 7, 8 and 9 | The amendment's home | – | `README.md` |
| 20:25–20:35 | Wrote `src/eda/current_best_model/adoption_read.py` and its tests; fixed one gap before running: a new feature big enough to see alone but failing the arithmetic now goes to the pool, not "do not adopt" | The decision's point 2, without touching `compare.py` | The published backfill's `scores.csv` (seed check), read by a test | 11 new tests pass; the folder's 57 pass |
| 20:35–20:45 | Wrote `class_record.csv` (22 readings copied from documents) and `class_record.py`; ran it | The decision's point 5 | Published readings only | `class_record.out` |
| 20:40 | **Corrections to the record before its first use:** five `read_on` dates had been filled from memory; replaced by the source studies' own dates. Two training-window arms (last3, rand5) un-pooled, since three arms of one comparison would count as three readings | Rule 4: correct by adding (logged here) | – | The pooled repairs read +0.007 [−0.013, +0.028] over 3 (+ = the repair better) |
| **Correction, 20:36** | **The four rows above give estimated times, written at 20:10 ahead of part of the work, and they are wrong.** The file times show: the framework edits, the reader and its tests, and the record were all done between about 20:00 and 20:10 (`class_record.csv` first written 20:09:20, `class_record.out` 20:10:09; the log rows themselves 20:10:20). The order of the steps is as listed. Rows from here on take their times from the files. **The same applies to the "opened 20:05" note at the top and to the 20:03 and 20:08 rows.** The lead's addition 4 is stamped 19:59:56. Its message was shown to this session right after the log's first write, so the log was opened between about 20:00 and 20:03, and the reply came then too | Rule 4 | – | – |
| 20:10:43 | CLAUDE.md: the adoption section rewritten (kinds, resolution, the pool, combining; the reporting labels marked as reporting); one line added under the frozen reference: a candidate showing no harm is recommended when it is a repair or new data entering by its supported route | Every session reads CLAUDE.md first; the old bullets carried the sign rule | – | `CLAUDE.md` |
| 20:12–20:13 | The rebuild: `03_rebuild_stages.md` § 5 items 4–7 redrafted as the cluster tree with top-down removal and stability (the first draft kept verbatim at the section's end); Q8 ruled in principle and Q30 added (`04_review.md`); entry 0.9 (`decision_log.md`) | The decision's point 6 | – | The three files |
| 20:13 | Feature universe § 9 (the pool's admissions); checklist items 9 (re-filed) and 10 (the first holdback) | The decision's re-filings | – | Two files |
| 20:13:38 | **Fix:** checklist item 10 first said to read the holdback with `--kind structural`, whose adopt-or-not arithmetic is the wrong frame for changes already adopted. Added a `holdback` kind to the reader ("keep the adopted changes" or "bisect"), a test, and the checklist and framework lines | Caught on rereading item 10 | – | 12 tests pass |
| 20:14 | Live fits within the season: an amendment to the current-best-model decision (and a pointer in its "Fit" bullet); a note in the prediction-run study's next steps | The decision's point 7 | – | Two files |
| ≈20:30–20:32 | Memory: the memory saved at 19:21 deleted, since the decision record and CLAUDE.md now hold it; `score-direction-labels` re-pointed to the decision; `edge-thesis-point-by-point` updated so a built feature is admitted to the pool rather than adopted on its score | Memory discipline: one place per fact | – | Memory files |
| 20:33 | Checks: every relative link in the 13 edited files resolves; the framework's §§ 1–9 titles (anchors used by the ledger and checklist) unchanged; both hashed files unchanged (`e72e9ae2…`, `7e7f35da…`). **Fix:** a link added from the rebuild folder pointed at the statistics review, which quotes 2025–2026 results; replaced by a plain citation with the arithmetic (1 − Φ(1)^20) | The rebuild folder must hold no 2025–2026 result | – | `03_rebuild_stages.md` |
| ≈20:36–20:51 | **Independent review:** one read-only subagent (brief verbatim in the appendix) | The owner does not check the work himself; catch errors before they spread | – | 15 findings (3 high, 6 medium, 6 low). About 35 numbers checked: all matched their sources except two context claims in the decision record |
| 20:51–20:54 | **Checked the review's two high claims before acting:**<br>• the indoor fill against the reference read +0.007 [−0.306, +0.320] (`indoor_fill/README.md`:153), so a holdback against the reference cannot see a batch of small changes;<br>• the level-evidence study had no `scores.csv`, no selection file and no SYS-family fits, and addition 4b codes the layer in `system_decide.py` with R_S2 and SYS_S2 among the challengers.<br>Both confirmed | A subagent's findings are taken only after checking | – | – |
| 20:54 | `level_evidence_rules.py` extended to five challengers; its first tables reproduce exactly. Study erratum 1 written and hashed (`edb9b377…`; no score or selection file at 03:54 UTC); message to the lead | **Finding 2:** R_S2 and SYS_S2 as challengers would adopt a lead on its discovery seasons. **Finding 15:** the tolerance is Claude's choice | None | `owner_decision_2026-10-09_erratum_1.md` |
| 20:54:38 | Errata file for the decision record (E1–E8); its index row points to them. The decision record itself is left byte-stable, since addition 4 cites its hash | Findings 1, 3–7, 9 and 10 | – | `2026-10-09-adoption-by-change-class-errata.md` |
| 20:55–20:58 | **The reader rewritten:**<br>• a blind reading no longer falls back to its sign: tuning keeps the default, a structural change is undecided;<br>• tuning needs k ≥ 2; expansion needs `--route-supported`;<br>• a costly harm-checked change is weighed by the arithmetic;<br>• a small harm sends expansion or accretion back to its route, and does not veto a repair;<br>• features are "admitted to the pool as a lead", and a harm first means a bug or leak check;<br>• input flags are read from `summary.json`; NaN rows are refused.<br>Its tests were rewritten (16). **One test of mine was wrong:** the luck of 10 variants (1.54 SE) does not eat a 2.04-SE estimate; the test was corrected to 50 variants | Findings 3, 4 and 12 | – | 62 tests pass |
| ≈20:58 | Message from the lead: erratum 1 adopted before any score; addition 4c will hash the code change | – | None | – |
| 20:59–21:02 | **Framework:**<br>• "In short" item 6 limited by kind; a repair is a fix to an input already in the model;<br>• § 2's rows aligned with § 4; § 4 gains the small-harm and costly-change rules;<br>• § 10: the holdback's control, the refit's cost, leads kept out of the pools;<br>• § 11's stability; the reader's flags; a Known problem: no generic two-instance scorer.<br>**Pooled record:** the two share leads un-pooled, so the feature kind keeps −0.028.<br>**Rebuild:**<br>• links to the decision record replaced by words (decision records are off limits to its reviewers, `04` §1);<br>• the level-1 rule drops a block only when it is shown not worth its columns, with a power check and no luck correction;<br>• stability drops a node only on stable evidence; Q30 updated.<br>**Checklist item 10:** the control, the missing tool, and the prompt's stop condition removed.<br>**CLAUDE.md:** the holdback line | Findings 1, 5–8, 11, 13 and 14 | – | The files |
| 21:38 | **The owner on the holdback's control,** verbatim: "yes that makes sense and is approved. the oct 8 freeze I suggested was more about the data from the challenger series/ITF tour and I think the agent I was talking to read into it deeper than I was intending". Recorded the approval of E1 (errata, decisions index). Read `history.py`: it refused a template build on any past change at any level | An owner message that changed the course | – | The errata and index; a recommendation to narrow the gate, keeping qualifying gated |
| 21:42–21:47 | **The owner,** on the pasted three-point recommendation: "Ok, do this". Then:<br>• `history.py` narrowed: the all-level counts are kept; each is split into `gated` (lower-level, including qualifying and unknown levels) and `allowed_main_tour`; `template_ok` reads the gated part only;<br>• `run_chain.py`'s refusal message and docstring;<br>• `test_history.py`: three tests given the new expectation, eight added; 24 pass;<br>• the live gate run: no difference;<br>• the current-best-model decision amended with the owner's words; CLAUDE.md; the decisions index; a dated note in the Roland Garros report;<br>• an FYI to the level-evidence lead | The owner's instruction | – | The files |

## 6. Judgment calls and deviations

1. **The harm tolerance: 0.10 mLL**, with the whole 95% interval below 0.
   * **Options:** 0.05, or a cost-based bar.
   * **Why:** it is the form the owner already decided for the Roland Garros candidate, so one rule serves every lane.
   * **The cost of the choice:** it accepts a true 0.05 harm about 70% of the time in the level-evidence study
     (the rates are in its amendment). A 0.05 tolerance would raise false alarms on a harmless change to about 7%.
   * **When:** chosen before any of the study's scores existed.
2. **The selection switch: "better"** (the 95% interval clears 0).
   * **Options:**
     * the EV-optimal sign-after-luck rule: lax, since noise switches between equal arms cost nothing in expectation;
     * a luck-corrected strict rule (estimate − SE × 1.35 > 1.96 SE).
   * **Why "better":**
     * it keeps the choice from being noise-driven, with a noise-switch rate of 6–16% against the registered 19–52%;
     * it keeps the switch power at about 0.82 for a challenger truly better by 0.10;
     * SYS is the arm the statistic-level evidence supports, and it is needed when the ITF data arrives.
3. **`compare.py` was left byte-identical;** a companion reader does the resolution and kind read instead.
   * **Why:** `system_pairs.py` imports `compare.py`'s recipe, and its `--run-compare` checks `compare.py`'s rows
     against its own. Changing `compare.py` while that study runs could alter or break its scoring.
   * **What the other branch would change:** nothing in results; only where the code sits.
4. **The amendment is a separate file, outside the scorer's addition glob,** rather than an edit of the lead's
   pre-registration.
   * **Why:** another session owns the study and its hashed files. The cost is that the scorer does not enforce the
     amendment, so the lead must restate it.
5. **Both busy sessions were messaged.**
   * **Why:** the study's lead could not be identified; `status.log` was not read, to stay blind.
   * **The cost:** one session receives a message that is not for it.
6. **Women's treatment stays deferred to P7, as registered.**
   * **The option:** extend the harm-framed rule to SYS_BOTH for women now.
   * **Why not:** women's lower-level evidence is dominated by ITF, whose parameters wait for P7, and the study
     registered men first.
7. **The new data's "supported route" is the system's treatment as a whole (NEW_SYS_BOTH),** not channel by channel.
   * **Why:** role B's fits are the statistic-level evidence for every channel, and only registered arms can be read
     without new builds.
   * **The fallback,** if REF is recommended for men: RES_ONLY on C0_now.
8. **In-season live fits were decided as a policy, with no code now.**
   * **Why:** the forecast step that would use them is not built.
   * **The guard:** a replay check of the calibration before first live use.
9. **The decision record was left byte-stable,** and its corrections went into an errata file.
   * **The option:** edit it.
   * **Why not:** addition 4 cites its hash as the source, so an edit would leave that provenance stale. The errata govern where they differ.
   * **When:** after the review, before any score of the level-evidence run.
10. **The holdback's control** (errata E1).
    * **The options:** the frozen reference, as decided; the Pinnacle-first instance; or "the latest stored instance carrying every structural change".
    * **The choice:** the last, which today is the Pinnacle-first instance.
    * **Why:** across the odds change, a comparison resolves only ±0.3.
    * **This changes how the owner's point 5 is run,** so it is flagged to the owner.
11. **The reader's "blind":** the plausible effect is below resolution *and* the reading is unresolved.
    * **Why:** a resolved reading saw something, whatever the prior said, so the arithmetic may decide it. Otherwise a clearly better structural change would read "undecided".
12. **The rebuild's level-1 default: keep a block unless it is shown not worth its columns.**
    * **The option:** the first redraft's "drop unless the arithmetic clears".
    * **Why:** under that rule an unresolved block was dropped on noise, and the tree's blocks are fixed by mechanism.
    * **What the other branch would change:** fewer blocks and columns, at the risk of losing a block like the long-memory profile (−0.29 [−0.63, +0.04] when removed, unresolved).
13. **Qualifying kept under the narrowed gate.**
    * **What the owner said:** "challenger + ITF", and his approval quoted "(Challenger and ITF)".
    * **Why:** the preceding message had asked him to say if he meant Challenger and ITF only, and he did not. The lower-level study found qualifying box scores inflate form like Challengers' (77–83% of the level boost kept).
    * **Recorded** in the decision as removable by the owner.
14. **Unknown levels are gated,** the cautious default: a level the check does not know is examined before it enters.
15. **`history.py`'s all-level keys kept their meaning.** The split was added beside them, so the lower-level study's `run_history` and its recorded counts stay valid.

## 7. Claims and their evidence

Mapped from the [decision](../../decisions/2026-10-09-adoption-by-change-class.md) and the framework's §§ 0, 4, 10 and
11. No number here rests on a choice made after seeing a result; every outcome-based number was read from a document.

| Claim | Evidence | Status |
|---|---|---|
| Comparisons resolve about 0.02–0.12 mLL (about 0.3 for a structural change) | seed check `scores.csv` (±0.02); lower-level § 7 (±0.07); lean review T2 (±0.09); D's power note (±0.12); Pinnacle first (±0.30) | Observed (copied) |
| 100 more training rows ≈ 0.0001 mLL; a season's rows ≈ 0.001–0.01 | `resolution_check.out`: a curve fitted through the training-window study's three random-draw arms | **Inference.** Three noisy points (SE about 0.1–0.15 each, seeds unpaired); the order of magnitude is robust across the four curve shapes tried, the exact values are not |
| A true +0.01 at SE 0.04 points the right way 60% of the time | Φ(0.25); `resolution_check.out` | Arithmetic |
| The level-evidence rules: 56% (registered) against 100% (amended) for a SYS worth +0.083; the amended rules accept a 0.05 harm about 70% of the time | `level_evidence_rules.out` | **Inference.** A simulation on the study's own SEs; the eight Holm strata's SEs are approximations; a homogeneous effect across strata is assumed |
| The new lower-level data would stay out about 96% of the time | P(reads "better") 3–5% for a true gain of 0.005–0.01 at SE 0.03–0.04 (`resolution_check.out`) | **Inference.** The men's true gain is assumed, not measured; F's dose table makes a small one likely |
| Repairs pool to +0.007 [−0.013, +0.028] (+ = the repair better) | `class_record.out`, 3 readings | Observed arithmetic on copied readings; mixed targets and scorers |
| Dropping the long-memory profile −0.29 at the close; `ios_points_short` −0.00 | lean review T2 | Observed (copied) |
| The screens' single additions averaged −0.028, true-effect spread 0.012 | statistics review, finding 3 | Copied; **taken as reported**, not re-checked here |
| The best of about 20 useless families clears one SE about 97% of the time | 1 − Φ(1)^20 = 0.968 | Re-derived here |
| Hierarchical testing (Meinshausen, 2008) and stability selection are established methods | Cited from knowledge | **Not looked up this session**; a reviewer should confirm the citations |
| No model-level score of the level-evidence run existed when its rules were amended | File names of `arms/*/vs_reference_2026-10-08/` (part-1 files only); confirmed by the lead's addition 4 | Observed |
| The same held when erratum 1 was hashed (03:54 UTC) | No `scores.csv` or selection file in the study; confirmed by the lead's message | Observed |
| A holdback against the frozen reference resolves only about ±0.3 | The indoor fill against the reference: +0.007 [−0.306, +0.320] (`indoor_fill/README.md`:153); Pinnacle first alone ±0.30 | Observed (copied) |

## 8. Weak points

* **Threats to validity, most important first.**
  1. **The kinds' plausible effects are thin starting values:** repair rests on 3 readings, accretion on a 3-point curve. If true effects are larger than assumed, "below resolution" labels err toward adopting on the kind's direction.
  2. **The harm tolerance (0.10) lets small harms through:** about 70% at −0.05 in the level-evidence study. This matters most where statistic-level and model-level value can diverge. The lower-level dossier names that case: correcting an input can remove an accidental signal that offset the market's error. The guards are the holdback and the ledger, not the harm check.
  3. **Forking paths.** "Declare the kind before reading" is a norm; `adoption_read.py` takes the kind at read time and cannot enforce it. A reviewer should check that each study's kind predates its scores.
  4. **The pooled record** mixes targets (the close, the opening line), paired and unpaired seed terms, and scorers. Its pooled means are rough.
  5. **The redrafted selection's constants** (τ 0.1, the 0.8 merge, the two-thirds stability, 200 resamples) have had no power analysis. The rehearsal (stage 5) is where they would be tested.
  6. **Blinding.** The rebuild folder now links only to the decision record, which holds no 2025–2026 result. That record links onward to documents that do. The clean room relies on folder scope and logged reads (Q14), as before.
  7. **`compare.py` does not print the resolution itself.** Agents must run the reader until `compare.py` takes it in, after the level-evidence study.
  8. **No generic tool scores the template against the holdback's control.** `compare.py` compares only against the frozen reference. The first holdback has to adapt a study's scorer.
  9. **The independent review found 15 issues;** all were addressed the same night (§ 4). A second review of the fixes was not run.
* **Where a flaw would most likely hide:** in the claim that repairs and expansions are positive by mechanism. If adoptions made on a kind's direction are, on average, slightly harmful at the model level, the policy accumulates harm too small for any single harm check to see.
* **What a re-design would do:**
  * measure the accretion curve properly, with paired seeds: drop 1%, 5% and 20% of rows, with several draws each, which also measures the refit noise floor;
  * calibrate the harm tolerance against the holdback;
  * rehearse the redrafted selection on D′.
* **The one experiment most likely to overturn the conclusion:** the holdback (checklist item 10). It reads the sum of the changes adopted on their kind's direction. A clearly worse reading would say the kinds' priors are wrong.

## 9. Reviewer checklist

* [ ] Re-derive the level-evidence rates: `./python.sh src/eda/adoption_framework/level_evidence_rules.py` against `data/studies/adoption_framework/level_evidence_rules.out`.
* [ ] Re-derive the learning-curve values: `./python.sh src/eda/adoption_framework/resolution_check.py` against `resolution_check.out`.
* [ ] Confirm that no model-level score of the level-evidence run existed at 02:55 UTC:
  * the part-1-only folders;
  * `status.log` before 02:55 UTC;
  * the lead's addition 4.
* [ ] Confirm the hashes: `owner_decision_2026-10-09.sha256` (`7e7f35da…`); the decision record (`e72e9ae2…`, recorded in addition 4).
* [ ] Check each `class_record.csv` row against its cited source, and the pooling rule (one row per change; seasons ≤ 2024).
* [ ] Rerun the tests: `./python.sh -m pytest test/current_best_model -q` (62 at writing, 16 of them the reader's).
* [ ] Check erratum 1's hash (`edb9b377…`), and that the lead's addition 4c removes R_S2 and SYS_S2 from `system_decide.py`'s challengers before the first dev score.
* [ ] Check that the framework's §§ 1–9 titles still match the anchors used in `lean_ledger.md` and the checklist.
* [ ] Check that the additions to `docs/studies/clean_holdout_rebuild/` hold no 2025–2026 result.
* [ ] Check the verdict words in the amendment against its rates table.

## 10. Reproduction

```
# calculations (CPU, seconds; no data read)
./python.sh src/eda/adoption_framework/resolution_check.py      > data/studies/adoption_framework/resolution_check.out
./python.sh src/eda/adoption_framework/level_evidence_rules.py  > data/studies/adoption_framework/level_evidence_rules.out
./python.sh src/eda/adoption_framework/class_record.py          > data/studies/adoption_framework/class_record.out
# the reader, on a compare.py output (example: the speed backfill's seed check)
./python.sh src/eda/current_best_model/adoption_read.py --scores data/studies/adoption_framework/seed_fix_check/scores.csv --kind expansion --out <scratch>.json
# tests
./python.sh -m pytest test/current_best_model -q
```

Seeds: `resolution_check.py` 0; `level_evidence_rules.py` 20261009 (200,000 draws per cell, so its rates are stable to
about ±0.002).

## Appendix: briefs and messages

* **One subagent: the independent reviewer** (general-purpose, read-only; launched about 20:36, done about 20:51).
  * It was allowed to read the whole repository and to run the reader's tests. It wrote nothing.
  * Its report is in the session transcript. § 4 lists what it found and what was done.
  * Its brief, verbatim:

  > You are reviewing documentation and code changes made tonight in the repository C:\Users\zerom\Documents\Tennis-predictions (a tennis betting-model research project). Read-only: do not edit, create or delete any file, and do not run anything that writes files (running the tests with `./python.sh -m pytest test/current_best_model/test_adoption_read.py -q` from the repo root is allowed).
  >
  > Context: the owner decided on 9 Oct 2026 that adoption of model changes is judged by "kind of change" (decision: docs/decisions/2026-10-09-adoption-by-change-class.md). A comparison decides only where it can see a change's plausible effect; below that, the kind's expected direction decides and the reading is a harm check (worse by more than 0.10 mLL with the whole 95% interval below 0). New features go to a pool (the feature universe) and selection rounds decide by cluster. The changes implementing it are in:
  > 1. docs/decisions/2026-10-09-adoption-by-change-class.md (new)
  > 2. docs/studies/adoption_framework/README.md (amended: § 0 new, "In short", §§ 2, 4, 5, 7, 9 amended, §§ 10–11 new, Known problems, Files)
  > 3. CLAUDE.md (the section "Suggesting that a change be adopted", and one bullet under the frozen reference: "A candidate that shows no harm is recommended ...")
  > 4. data/studies/lower_level_evidence/system/owner_decision_2026-10-09.md (new; amends another study's decision rules; that study's own files are in the same folder and docs/studies/lower_level_evidence/system/)
  > 5. docs/studies/clean_holdout_rebuild/03_rebuild_stages.md § 5 items 4–7 and 9 (redrafted), 04_review.md (Q8, Q30), decision_log.md (entry 0.9)
  > 6. docs/studies/feature_universe/README.md § 9 (new)
  > 7. docs/studies/adoption_framework/checklist.md items 9 and 10 (notes added at their tops)
  > 8. docs/decisions/2026-10-08-current-best-model.md (one amendment bullet "Live fits grow within the season", and the "Fit" bullet)
  > 9. src/eda/current_best_model/adoption_read.py and test/current_best_model/test_adoption_read.py (new)
  > 10. data/studies/adoption_framework/class_record.csv and src/eda/adoption_framework/class_record.py (new), output data/studies/adoption_framework/class_record.out
  > 11. docs/studies/adoption_framework/process_log.md (new)
  > Supporting calculations: src/eda/adoption_framework/resolution_check.py and level_evidence_rules.py, with outputs in data/studies/adoption_framework/*.out.
  >
  > Check, and report findings:
  > (a) Contradictions between these documents, or between a new statement and an unchanged part of the framework README (for example § 2's table against § 0; § 3's cost classes against § 0; §§ 6 and 8).
  > (b) Numbers that do not match their cited source. Spot-check at least 12, including every number in the decision record's context section, the framework's § 0 bullets under "What the comparison can see", and at least 6 class_record.csv rows against the document in their "source" column.
  > (c) Any 2025–2026 result (an outcome-based score of seasons 2025 or 2026) added to docs/studies/clean_holdout_rebuild/. That folder must contain none; dates such as "9 Oct 2026" are fine.
  > (d) Logic errors in adoption_read.py (a wrong decision for an edge case; the harm rule; the "pool" mode; the holdback kind) and whether the tests cover them.
  > (e) Places where the new rules could be read as "adopt anything" (loopholes), or where any of these documents still defaults to keeping the status quo because a reading is unresolved.
  > (f) Statements that overclaim: an inference presented as observed, or a proposal presented as decided.
  >
  > Report as a numbered list, most severe first. For each: file:line, severity (high / medium / low), the problem in one or two sentences, and a suggested fix. Do not report style preferences or wording you merely would have chosen differently. If you find nothing in a category, say so in one line. Keep the report under 900 words.
* **The message to the study's lead,** sent at about 20:00 to `tennis-predictions-f5` and `tennis-predictions-0e`.
  * The same text went to both, except the second's "it was also sent to tennis-predictions-f5".
  * Verbatim, in the session transcript (`c0f7c8d9-cc78-498f-9409-72258b59a7dd.jsonl`).
  * Its content: § 4's 20:00 row, and the amendment's sections 1–5.
* **The lead's reply** (from `tennis-predictions-f5`), verbatim:
  > "The level-evidence study's lead has adopted the amended decision rules, in full, before any score.
  > - Adopted in data/studies/lower_level_evidence/system/preregistration_addition_4.md (sha256 754e055c…, 02:59:59 UTC). It restates sections 1–5 of owner_decision_2026-10-09.md (7e7f35da…) and says that file governs if the two texts differ.
  > - No model-level score of this run existed at that time: SEP_ALL and REF_noITF had part-1 input checks only.
  > - Role D is implementing the layer without changing what the frozen scorer measures. The registered rules' outcome is still computed and reported beside it.
  > - Any code hashes go in an addition 4b before the first dev score.
  > - The final report will quote the rules' rates (your section 6) beside the readings.
  > - No rule looks inapplicable to the arms as built. If one turns out to be, I will record the reading closest to its intent before scoring, as your section 7 asks."
* **The erratum 1 message** went to `tennis-predictions-f5` only, at about 20:54. It is in the transcript; its content is the erratum's sections 1–3.
* **The lead's second reply,** verbatim:
  > "The level-evidence lead has adopted erratum 1, before any score. Its file and hash were checked (edb9b377…), and no scores.csv or selection file existed at 03:54 UTC.
  > - Role D is changing system_decide.py: the challengers become SYS_w0, SYS_w50, SYS_w100, SEP_ALL and SYS_NOCLASS. R_S2 and SYS_S2 are reported as lead evidence for the pool, with their seasons recorded.
  > - Addition 4c will hash the change before the first dev score.
  > - The 0.10 tolerance is recorded as your choice, in the form of the owner's Roland Garros rule. The owner may set another value, but it cannot be loosened once a governed score exists."

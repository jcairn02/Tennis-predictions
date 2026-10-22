# Process logs: how a study records the way its conclusions were reached

9 October 2026 · For the agents who run studies and research, and for the future reviewer who reads their logs · **The owner's default from 9 Oct 2026** ([decision](../decisions/2026-10-09-study-process-logs.md)).

**Why.** A study's README says what was found. Its process log says how it was found:
* what was done, and in what order;
* what was known when each choice was made;
* why each choice went the way it did.

It is written for a future reviewer, perhaps a more capable model. That reviewer may see a flaw in the reasoning or the process and re-design the study.

Without such a log, the [feature-provenance study](feature_provenance/README.md) had to reverse-engineer which seasons the model's inputs were chosen on. That took four independent audits of every report, decision and look ledger.

**Worked example:** [tour pooling's methods and audit trail](tour_pooling/audit_trail.md) (9 Oct 2026). It predates this template. It paraphrases the request and summarises the subagents' briefs; the template keeps both verbatim.

## Rules

1. **Every study and research note keeps one,** whether new, resumed or extended. It is `process_log.md` beside the README, in `docs/studies/<study>/` or `docs/research/<topic>/`.
   * Long companions sit beside it and are linked: a look ledger, the subagents' briefs.
   * A question answered only in chat needs none.
2. **Open it before the first substantive step,** with the request (§ 1) and the plan (§ 3).
3. **Write it while working, not at the end.**
   * Add a chronology row after each step that produces a result, a decision, a failure or a change of plan. Do it before moving on, and before launching a long job.
   * A log rebuilt at the end is filtered by hindsight.
   * A long session's context gets summarised, and detail is lost. After a summary, note it in the chronology and re-read the log before continuing.
   * **Take each row's time from the clock** (`date`, or a timestamp the step itself printed), never from memory. Times written from memory ran 1 to 20 minutes off in three logs of 13–16 Oct 2026 (data gaps, TennisLive box fill, men's lower-level fill), each needing correction rows.
4. **Correct by adding, never by rewriting.**
   * Leave a wrong entry in place and add a dated correction under it.
   * If a bug or leak touched results already read, say which numbers it touched and whether they were replaced.
5. **For every choice that could move a conclusion, record what had been seen.**
   * Such choices include the target, the primary, windows, filters, variants, thresholds and when to stop.
   * Say whether the choice came before or after any outcome-based result, and which result.
6. **Keep the words that matter verbatim:** the owner's request and later instructions, and each subagent's brief. Interpretation errors hide in paraphrase.
7. **Log what failed too:** errors, bugs and their fixes, abandoned approaches, variants tried and dropped, searches that found nothing. The number of variants tried is evidence in itself (the winner's luck).
8. **Label every statement's status** ([research discipline](../../CLAUDE.md#research-discipline)).
   * The labels: observed (run or read here, with the path), provider claim, inference, assumption, unknown.
   * Say which subagent findings the lead re-checked and which were taken as reported.
9. **Give reasons as they were held at the time,** including ones later proved wrong. The log is evidence, not advocacy.
10. **Finish it before reporting.** §§ 7–10 are written at the end, and the README links the log.
11. **Scale it to the work.**
    * A short lookup needs §§ 1, 4, 5, 6 and 8, a few lines each.
    * Work that scores a model, chooses data or inputs, or reads results needs every section.
12. **Existing studies are not retrofitted.**
    * A study resumed or extended from 9 Oct 2026 opens its log at that point.
    * It labels anything earlier "reconstructed, not contemporaneous".

**The session id** is the name of the transcript file under `~/.claude/projects/<project folder>/` (`<id>.jsonl`). It is also the name of the session's scratchpad folder. A reviewer can read the raw session there while the transcript is kept.

## The template

Copy the block into `process_log.md` and replace each placeholder and each italic note. The links assume a study in `docs/studies/<study>/`. From `docs/research/<topic>/`, prefix them with `../../studies/`.

````markdown
# <Study title>: process log

<started> – <finished> · Kept by <model and harness, e.g. Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code> · Sessions: <id, id> · For a future reviewer · Report: [README.md](README.md)

## 1. The request

* **The owner's words, verbatim** (<date>):
  > "…"
* **How it was read:**
  * the interpretation acted on;
  * the other readings, and why they were set aside;
  * any question put to the owner, and the answer.
* **The target** ([adoption framework](../adoption_framework/README.md) § 1):
  * the price and hour a bet would be placed at;
  * the matches;
  * the seasons scored;
  * the declared primary.

  Say when each was fixed, relative to the first result read.

## 2. Starting point

* **Code:** the commit, and any uncommitted changes in files the study runs.
* **Data:** each table read, with its path, SHA-256 or row count, and build date; the reference or instance it rests on.
* **Earlier looks:** studies that already read these seasons with this idea or a related one.
* **Environment:** the interpreter, the packages that matter (the TabPFN checkpoint, numpy) and the hardware.
* **The idea and how it arose** (adoption framework § 2). It is one of:
  * a verified fix;
  * more of a kind of data already used;
  * a mechanism stated before the test;
  * the best of several variants;
  * a pattern found in the scored seasons;
  * a structural change.

## 3. Plan

*The design as first written: arms, controls, primary and secondary readings, gates and the stopping rule. If pre-registered, give the file, its SHA-256 and when it was frozen. This section is not edited later; changes go in §§ 4 and 6.*

## 4. Chronology

Local time (UTC<offset>). "Results" means any outcome-based score of any candidate.

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| | | | | |

*One row per step. Always add a row for each of these:*
* *each look at results (when there are many, keep a separate `look_ledger.md` and link it);*
* *each owner message that changed the course, verbatim;*
* *each subagent launched (its brief goes in the appendix);*
* *each failure, bug, fix and rerun;*
* *each change of plan;*
* *each new session or context summary.*

## 5. Sources (research only)

*For each source:*
* *the search query or route tried;*
* *for a source used: its URL, the access date, what it supports, and whether it is a provider claim or verified here;*
* *for a source rejected: why;*
* *what could not be reached (a paywall, a login, a block).*

*Then say where the search is likely blind.*

## 6. Judgment calls and deviations

*Numbered. For each judgment call:*
* *the options;*
* *the choice;*
* *the reason given at the time;*
* *whether it came before or after which results;*
* *what the other branch would plausibly have changed.*

*Include every deviation from § 3 and every shortcut (fewer seeds, a subsample, a skipped check), with its reason.*

## 7. Claims and their evidence

*Map each claim in the README to the file, table or command behind it, and give its status (observed or inference). Flag the numbers that rest on a choice made after seeing results. Flag the subagent findings the lead did not re-check.*

## 8. Weak points

* **Threats to validity, most important first:**
  * the untested assumption the conclusion leans on most;
  * leakage routes;
  * power: the comparison's resolution against the plausible effects;
  * repeated looks and multiplicity;
  * the incumbent's advantage.
* **Where a flaw would most likely hide.**
* **What a re-design would do** with more time, data or compute, and the one experiment most likely to overturn the conclusion.

## 9. Reviewer checklist

*Concrete checks, each with its command or file. For example:*
* [ ] *re-derive a headline number;*
* [ ] *confirm that no sealed or out-of-window result was read;*
* [ ] *rerun the tests;*
* [ ] *check the verdict words against the intervals.*

## 10. Reproduction

```
<commands in order, with their environments; mark the ones that need the GPU>
```

*Give the seeds, what each step writes, rough run times, and any superseded outputs kept as the record.*

## Appendix: briefs

*For each subagent:*
* *its role;*
* *its brief, verbatim (or the path where it is saved);*
* *what it was allowed to read, in particular whether it saw results;*
* *the path of its report.*
````

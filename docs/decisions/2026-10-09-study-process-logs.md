# Every study and research note keeps a process log for a future reviewer

**Decided by the owner on 9 October 2026.** Recorded the same day.

**The context.**
* **What a README records.** The question, data, method, results, limitations and decision status ([studies index](../studies/README.md)). It says what was found, not how the conclusion was reached.
* **What was kept before, ad hoc:**
  * pre-registrations;
  * look ledgers (serve speed, pair strength, feature interactions);
  * the clean-holdout rebuild's decision log;
  * one full methods-and-audit-trail file, written for "a future reviewer (a more capable model or a statistician)" ([tour pooling](../studies/tour_pooling/audit_trail.md), 9 Oct 2026).
* **The cost of not keeping them.** The [feature-provenance study](../studies/feature_provenance/README.md) (8 Oct 2026) had to reverse-engineer how the model's 58 inputs were chosen. That took four independent audits of every report, decision and look ledger.

The owner's words:

> "I want as a default when I ask to research or create a study for a file to log the process for how it was obtained so that if a smarter LLM in the future looks at the study it may see flaws in the reasoning or the process of the conclusions and re-design the study."

## Decision

1. **Every study and research note keeps a process log by default,** without being asked.
   * It is `process_log.md` beside the README, in `docs/studies/<study>/` or `docs/research/<topic>/`, following the [template](../studies/process_log_template.md).
   * It covers new work, and work resumed or extended from 9 Oct 2026.
   * A question answered only in chat needs none.
2. **Its reader is a future reviewer,** perhaps a more capable model, looking for flaws in the reasoning or the process in order to re-design the study. The README stays the owner's report.
3. **It is kept while the work happens, not rebuilt at the end.** It holds:
   * the owner's request verbatim, the interpretation acted on, and the readings set aside;
   * the starting point (code, data versions, earlier looks at the same seasons) and the plan as first written;
   * a chronology that records what results had been seen when each choice was made;
   * every look at results, failure, dead end and variant tried;
   * the owner's instructions and the subagents' briefs, verbatim;
   * the judgment calls, with the reasons given at the time;
   * the report's claims, each mapped to its evidence;
   * the study's weak points, where a flaw would most likely hide, and what a re-design would do;
   * a reviewer checklist and the reproduction steps.
4. **It scales with the work.**
   * A short lookup needs a few lines per section.
   * A study that scores models, chooses data or inputs, or reads results needs every section.

## What it does not change

* **What a README reports,** and the studies and research indexes.
* **The procedures already decided:** pre-registration, look ledgers, the [match clock](2026-10-05-match-timing.md) and its leak probe, the frozen reference and its comparison, and the [adoption framework](2026-10-09-adoption-framework.md). The log records how they were applied.
* **Existing studies are not retrofitted.**
  * A log rebuilt after the fact would be the hindsight-filtered account this decision is meant to avoid.
  * A study resumed or extended from 9 Oct 2026 opens its log at that point and labels anything earlier as reconstructed.

## Open

* **Raw session transcripts.**
  * Each log records its Claude Code session ids.
  * The transcripts themselves hold every message, tool call and tool result. They are `~/.claude/projects/<project folder>/<session id>.jsonl`: 88 files and 501 MB for this project on 9 Oct 2026, the oldest from 22 Sep.
  * They are kept only on this machine, and are deleted 30 days after they were last used unless the `cleanupPeriodDays` setting is raised (default 30, minimum 1; [Claude Code docs](https://code.claude.com/docs/en/claude-directory.md), read 9 Oct 2026).
  * **Claude's recommendation, awaiting the owner's answer:** raise the setting, so a reviewer can read the raw session behind a log.

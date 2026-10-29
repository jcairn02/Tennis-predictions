# Studies keep a recipe, not a copy: the data-version rule (draft)

22 October 2026 · **A draft for the owner, not a decision.** It moves to `docs/decisions/` only with the owner's word.
· [Process log](process_log.md) · [The index](index.md) (which data each table was built on, generated)

## Why

On 22 Oct two tests failed because a set of the repository's tables was three weeks behind its history. Those tables
turned out to be one consistent older snapshot (the history saved at the 7 Oct rebuild), read on purpose by about 39
code files. The real faults were narrower:
* two places joined that snapshot with today's history, so a few matches silently dropped or went blank;
* no table records which history it was built from;
* the code that built a table or a model is not kept anywhere but inside the model's folder, so an old version cannot
  be rebuilt exactly once its files are gone.

The owner's aim: studies keep pointing at the data they were run on, without keeping every old version on disk, as
long as an old version can be recreated if it is ever needed; and agents keep this up to date by themselves.

## The rule

Each line says who chose it and which check enforces it (the production-integrity decision of 22 Oct: "checks over
prose"; "who chose each rule").

1. **A study names the data version it used, and never silently follows the current model.**
   * *Who:* the owner ("We dont want the studies to point to "new versions""); the reviewer of 22 Oct ("pin, never
     current").
   * *Check:* code that combines tables refuses tables built from different histories, unless the study names the
     version it wants (plan step 4). The daily engine already refuses this way.
2. **To re-create a study is to re-run it on newer data. The re-run is a new, dated reading; the original numbers stay
   as the record of what was found then.**
   * *Who:* the owner ("to re-create the study we have to retest it on the new data … the study says so in itself").
   * *Check:* the study's data-version block says how to re-run it and that the numbers will be a new reading; the
     process-log rule "correct by adding, never by rewriting".
3. **Every study, model build and shared rebuild records its data version as a recipe:**
   * the history's fingerprint, and the package and feed snapshot when it used a model's merged history;
   * the version of each raw download it read (the download receipts already record them);
   * the code version, captured automatically: one compressed copy per distinct state of the code, a few MB each,
     shared by every study run on it;
   * the correction tables it used;
   * the commands that ran it.

   *Who:* the owner ("an addendum and a pointer"; "the process of HOW to recreate the old version"). What the recipe
   holds is an agent's choice (Claude, from the 22 Oct audit, which found the code to be the missing piece).
   *Check:* each table builder stamps its output with the history it read; model builds and the study helper write the
   record; a weekly check lists any study or table without one and sends a notification (plan step 3).
4. **Old versions need not be kept.** A snapshot may be deleted when:
   * no study still in progress needs it on disk;
   * its recipe is proven: a cheap part of it, such as its history, is rebuilt from the recipe and its fingerprint
     matches;
   * a backup exists.

   A snapshot whose recipe cannot be proven is kept unless the owner decides otherwise. The early-October snapshot is
   one: the code that built it no longer exists.
   *Who:* the owner ("may not want to keep all the old versions"); the proof and the backup are an agent's choice (the
   reviewer: "back up before any deletion").
   *Check:* the recreation test writes a receipt; every deletion list goes to the owner first (plan step 5; the
   project rule "discuss cleanup before deletion").
5. **Always kept:** the frozen reference of 8 Oct; the model in use and its build folder; its documented rollback; the
   holdback comparison model; and any saved history a kept model's replay needs.
   * *Who:* earlier decisions (the frozen reference, 8 Oct; the holdback control, 9 Oct); listing them here is an
     agent's choice.
   * *Check:* the cleanup script's list of what it keeps.
6. **Agents do not have to remember; the tools do it.**
   * builders, model builds and the study helper record versions automatically;
   * the index regenerates itself weekly and after each build;
   * the weekly check notifies about anything missing;
   * code that mixes versions refuses to run.

   *Who:* the owner ("a process to ensure future agents automatically update this … without my manual execution").
   How it is done is an agent's choice.
   *Check:* the weekly job and the end-of-build check (plan step 3).
7. **One short paragraph in the project instructions** (CLAUDE.md), which every agent reads at the start:
   * use the helper;
   * never point a study at "the current model";
   * never delete a snapshot without a proven recipe and the owner's approval.

   *Who:* an agent's choice (how to carry the owner's request to every agent). *Check:* none of its own: the checks
   above enforce it.

## What it changes for existing studies

* **Nothing is re-pointed.** Closed studies keep reading the snapshot they were run on.
* **The two places that mix versions** get a pin to one version: the unpriced-leads study's extra features and the
  serve/return study.
* **A dated note in each affected study**, generated from the index, says which history it was run on and whether that
  history can be recreated.
* **Re-runs** only for studies the owner chooses, after the next shared rebuild (today's decided corrections are not in
  the shared history yet).

## For the owner to decide

1. **Adopt the rule** as written, or with changes.
2. **The code copy:** keep one compressed copy per distinct code state (a few MB each), or commit more often so that a
   commit can serve as the code version. The copy needs no habit change; I recommend it.
3. **Retired model folders:** once a folder's recipe is proven and backed up, delete it at once, or keep the last two.
   I recommend at once (each is about 17 GB), except the ones rule 5 keeps.

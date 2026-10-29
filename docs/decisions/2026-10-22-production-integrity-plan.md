# Production integrity: one authority for what is live, checks on every bet sheet, outcomes graded, one to-do list

**Decided by the owner on 22 October 2026.** The owner asked how to keep a pipeline with many data sources and many
parallel AI agent sessions in sync, and how to trust that the model being bet has no bugs or unintended behaviour
("some sort of clear process and ledger that each future agent will be able to reference as a ground truth"; "LOUD
WARNINGS when I run at bet-time"). Claude's assessment proposed a plan; three independent reviewers audited it (past
incidents, an adversarial design review, the bet-time warnings); the plan was revised. The owner's words, verbatim,
quoting the revised plan's order:

> Revised order (my recommendation): Fix the four false or blind signals above. A few hours. Bet-sheet integrity. About
> 1–2 days. [...] full model identity, against the receipt from the last passing replay; the every-part-present check;
> the missing-results check; what each bet rests on. Outcome tracking. Record placed bets. Grade every predicted match
> nightly. Run the strength-of-lean check above. [...] One to-do list that routes, with "who decided" marked. You pick
> which open items from the 25+ scattered places are still wanted. The generated state printout. Last, because it's
> mostly a printout of steps 2–4. Then: checking each day's predictions against the backtest, countdowns before data is
> lost for good, and per-file claims.
>
> Execute on this plan, and have it documented that this is the plan so other future agents will know what happened.
> Integrate it into the master_pipeline and the scripts that run for predictions and production

Carried out by Claude from 22 Oct 2026 ([master pipeline process log](../studies/master_pipeline/process_log.md),
Part 10). The live-model fix that preceded it is Part 9 of the same log.

## Why: what the sweeps and the audit found (each re-checked in the files)

* **The live model was named four ways**, and the daily engine silently defaulted to the 10 Oct build. Fixed on
  22 Oct (Part 9): the notebook's selection is the one place, and nothing has a default.
* **Documents contradict each other about what is live:** the studies index said the five-pattern adjustment was
  "switched off pending the owner" after it went on; the retrain study said the first retrain "waits for your word"
  after it ran; open items sit in 25+ documents.
* **Hand-kept ledgers go stale within about a week:** the shared adoption checklist, the class record (no entry after
  16 Oct), the odds rule kept by hand in three places. A hand-written "production record" would be one more.
* **The one bug that put a wrong bet on a sheet** was a part of the forecast missing on every live match: the
  fast-courts pattern, 13–16 Oct ([five-pattern decision](2026-10-13-five-pattern-adjustment.md), "Found on 16 Oct").
* **Live inputs are never blank** (21 Oct: 0 missing values in 57 inputs × 23 matches; a gap is filled by leaning
  toward the player's prior), so a "share missing" check cannot see a broken feed.
* **The market does not move toward this model before the close** ([bet timing](../studies/bet_timing/README.md):
  slope +0.01 [−0.02, +0.04]), so closing-line value cannot tell a broken model from a working one; it only checks
  prices.
* **Known problems wait:** 7 of 20 past incidents (10–22 Oct) were written down days before anyone acted.
* **Nothing grades the live predictions or records the bets placed:** no live run has been graded;
  `data/betting_history/` holds only its README.

## Decision

### Principles

1. **One authority for what is live, generated from disk and run records.** Documents may record when something went
   live and why, never which one is live now. A study describes what was measured at its time, never production. A
   short owner-edited statement of intent may sit beside the generated state; each of its lines names the check that
   verifies it, or says "unchecked".
2. **Checks over prose.** A rule comes with the check that enforces it. Each match gets its own verdict: green, amber
   (shown, bet allowed) or red (blocked). The whole run goes red only for run-level failures: the wrong model, code that
   differs from the last verified run, prices that cannot be trusted. Red only where it would change a decision.
3. **An acceptance is typed, named and kept.** Overriding a red needs a typed reason, saved with the bet sheet and any
   bet placed from it, and it opens a to-do item. Known standing conditions are acknowledged with an expiry date.
4. **"Verified" means the last passing replay proof**, which writes a receipt of the code and model files it ran. Code
   or model files that differ from the receipt are "unverified".
5. **Who chose each rule.** A production rule is marked as the owner's words or an agent's choice. An agent's reading
   that changes picks is shown to the owner on the day's sheet, with and without it, before it goes live.
6. **Known problems route to a decision.** Every "found, not fixed" note and every decided-but-unbuilt item is one entry
   in one to-do list, with who decides and a date. While it touches the live path it shows on STATUS and the bet sheet.
7. **Claims go on shared things** (files, the GPU, the shared tables), with an expiry, honoured by the steps that write
   them. No edits to the engine's code while a live run is in flight; a run notices if its code changed under it.
8. **The outcome alarm is the strength of the model's lean**, not closing-line value: across every predicted match,
   whether the model's departure from the price predicts results as strongly as in the backtest (the realisation
   slope, per model). Closing-line value is kept for the bets placed, as a check on prices.

### The steps, in order

| Step | What | Status |
|---|---|---|
| 1 | **Four false or blind signals:** STATUS showed only the latest scheduled run; serve-speed freshness was read from a file rewritten daily and the job's exit code, and missed days were never fetched again; the canary's known "gone" flags could not be acknowledged; the owner's session-start hook warns at every session (it expects effort "high", the settings say "xhigh") | done 27 Oct. The hook now expects effort "xhigh", at the owner's word ("expect xhigh"); checked: the settings file still valid, the hook prints no warning. 25 Oct, the speed job's catch-up, at the owner's word ("make the fix at midnight tonight"): its 7-day look-back made every run hit the 200-request budget (each qualifying number asked once per round; events in text order, so Almaty's last 16 and quarter-finals were never asked), and a second run on one day erased the first's staged matches. Now each code is asked once, main draws first, a round staged in full asks only its incomplete codes, and a run adds to the day's file; 5 lost matches restored. Checked: 7 new tests; the run of 25 Oct asked 33 (96.6 s, against 200 and about 520 s) and a second run kept the first's rows (master pipeline process log, Part 16) |
| 2 | **Bet-sheet integrity:** model identity against the replay receipt; every part of the forecast present (inputs, pattern parts, speed term, Thinking); a main-draw player's previous round present; what each bet rests on; per-match verdicts and typed acceptances | in progress. The engine's side built on 22 Oct: every run records the source files it ran (fingerprints) and flags a file that changed during it, the weights by content, each men's match's speed evidence and the speed term's size; a passing replay proof writes the receipt. Checked on 27 Oct: a predict step re-run on a copy of the 21 Oct run changed no prediction (the only differences, on men's matches, are the speed history's own changes since: each shift equals b × the change in the speed gap to 3e-15); every live run since 23 Oct ran it cleanly (master pipeline process log, Part 10). **Still to build:** the bet sheet's side (the receipt comparison, every part present, the main-draw missing-results check, what each bet rests on, the verdicts), and a first receipt (a replay proof run) |
| 3 | **Outcome tracking:** a placed-bet record; every predicted match graded nightly; the strength-of-lean alarm per model; closing-line value for bets; backfilled from 10 Oct | in part. 25 Oct, at the owner's request ("comparing the "best model predictionsat the time of the run" to the closing line ... to calculate CLV"), the design an agent's choice: **closing-line value built**, the notebook's A8 (`tp.clv_ledger`, `predictions/clv/`). It covers every bet sheet's picks at the sheet's price, against Pinnacle's own pull within 15 minutes of the market shutting, else TennisExplorer's record of Pinnacle held within 2 hours of the start. It is rebuilt from the records at each call, backfilled from the first sheets (11 Oct), and grades the matches a Stage 0 holds. Checked: 17 tests (each key rule broken once, all caught); 4 picks by hand against the raw pulls and pages, equal to 5 decimals; the site's Pinnacle at each quote time equal to the sheet's own price on 162 of 191 readings, none with the sides swapped (master pipeline process log, Part 18). 27 Oct, at the owner's request ("If i could just sequentially run A1-A8 (except A6) ... Id want the aproximate same net effect of I did A7 more selectively"), the design an agent's choice: **every predicted match graded as its result arrives**, the notebook's A7 (`tp.grade_due`): each live run graded again whenever the freshest Stage 0 on disk holds more of its results, never before, each time the bet-day cells run. Checked: 5 tests; its first run graded 17 of 18 runs (203 predictions), the same results as A8's on all 203 (master pipeline process log, Part 19). **Still to build:** the placed-bet record, grading on a schedule without the notebook, the strength-of-lean alarm |
| 4 | **One to-do list that routes,** "who decided" marked; the scattered open items as candidates for the owner to pick | planned |
| 5 | **The generated state printout,** and a one-line verdict at every agent session's start | planned |
| 6 | **Then:** each day's predictions against the backtest; countdowns before data is lost for good; claims on shared files and resources | planned. One piece of principle 7 built on 23 Oct, an agent's choice: the notebook's kernel refuses to run code older than the files on disk (`src/pipeline/__init__.py`; master pipeline process log, Part 11). A live run noticing a change during the run is still to build |

Each row is updated when its step is done, with the date and the check that verified it.

## Left to the owner

* Which of the scattered open items stay on the to-do list (step 4 lists them as "proposed").
* The session-start hook: whether effort "high" or "xhigh" is intended (the owner's own settings; not changed by an
  agent).
* Any new blocking rule is marked as an agent's choice until the owner confirms it.

## Where things are

* How it was done, step by step: [master pipeline process log](../studies/master_pipeline/process_log.md), Part 10.
* The working guide's pointer: CLAUDE.md, "Production integrity".

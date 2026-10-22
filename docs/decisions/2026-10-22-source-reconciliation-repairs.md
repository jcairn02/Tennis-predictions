# The source reconciliation's repairs: in the decided tables now, in training from the next retrain

**Decided by the owner on 22 October 2026,** on the recommendation of the [source reconciliation study](../studies/source_reconciliation/README.md) ([process log](../studies/source_reconciliation/process_log.md)). The owner quoted the recommendation back:

> "Approve the fixes now, and I'll write them into the decided correction tables.
> I'd dry-run them first: build the match table twice and confirm only the named rows change.
> They would then take effect at your next retrain, whose harm check covers them, so no separate test build is needed.
> Two pieces need a little more:
> The level and surface fixes need a small change to the table builder, which today can't correct a single year of an event.
> The speed fix should go in with that retrain. Putting it in earlier would make the daily engine refit the speed stage between retrains."

and wrote: **"I want you to execute this. Ensure that when we implement the next re-train either through the master script or via another LLM agent, that it's aware of these intended revisions to the model, not simply adding the latest data. Also ensure you do this The level and surface fixes need a small change to the table builder, which today can't correct a single year of an event now, before the retrain (unless you disagree)"**

Recorded and carried out by Claude. Where carrying it out changed a point, it says so below.

## Decision

**The kind of change:** repairs ([adoption by kind of change](2026-10-09-adoption-by-change-class.md)). They are adopted on the data evidence; a model run serves only as a harm check, and they earn no edge credit.

1. **Five repairs go into the decided tables** (`data/studies/input_data_audit/fixes/`). Every Stage 0 build applies these tables (`stage0_build.py`):

   | Fix | What | Rows | Table, action |
   |---|---|---:|---|
   | SRS1 | Slam matches whose two service-game counts are the point record's exchanged (AO and US Open 2016–17, Wimbledon 2016–17 and 2024, Roland Garros 2016): exchanged back | 122 | `row_corrections.csv`, `exchange_svgms` |
   | SRO1 | Matches whose tour's own box and point record agree with each other and not with Stage 0: the tour's whole box (WTA 56, ATP 9, the ATP's two site copies 5, an ATP Challenger 1). The 3 that differ only on the first-serve split are left out, as recommended | 71 | `row_corrections.csv`, `replace_box` |
   | SRRET | Frame matches filed as completed that every source and the WTA's own record call retirements: " RET" appended to the score, so Stage 0 reads them as retired | 8 | `row_corrections.csv`, `mark_retired` (new) |
   | SRLVL | Editions at the wrong level: Valencia and Vienna 2014 (swapped); WTA Zhuhai 2015 (season finale); Brisbane, Moscow and Sydney 2017, Moscow and Osaka 2019, Strasbourg 2024 (500s); Guadalajara 2023 (1000); Cleveland 2025 (250); Bol 2016–17, Zhengzhou 2017, Limoges 2019 (WTA 125s) | 15 editions | `event_corrections.csv` (new), `set_level` |
   | SRSRF | WTA Paris 2010–14 filed as carpet, hard by the WTA, tennis-data and Flashscore | 5 editions | `event_corrections.csv`, `set_surface` |

   * **The evidence** is the study's: README §§ 2.3 and 3, the tables named there, and `data/studies/source_reconciliation/applied/repairs.csv` (each repair with its pointer).
   * **The builder change** (wanted before the retrain; done):
     * `corrections.apply_event_corrections` corrects one field of every row of a named edition. The edition is named by source, tour, Stage 0's tournament id, name and season, and guarded by the value it replaces. An edition already at the new value is reported and left alone; any other mismatch stops the build.
     * Stage 0 applies it after its level rules and their refinement from Tennis My Life (levels), and after its surface fill (surfaces).
     * `mark_retired` is a new row action, guarded by the score it marks.
2. **When they reach what.**
   * **Prediction runs: at once.** Each run builds its own Stage 0 from the decided tables, as with Tennis My Life's own corrections (13 Oct). The first run after 22 Oct recomputes, once, the parts of its saved state whose history changed.
   * **The shared tables:** at their next rebuild (notebook B6).
   * **The model's training rows: from the next retrain.** The retrain builds on the shared tables, so B6 must run first, as the retrain's plan already asks.
   * **No separate test build.** The retrain's own harm check (the new instance against the one in use, both stages) covers these repairs with everything else that entered.
3. **The serve-speed repair** (576 history rows: a published first-serve average more than 5 km/h off the match's complete point record takes the point mean; README § 6):
   * **The repaired history:** `data/studies/serve_speed_tabpfn/live/speed_panel_repaired.parquet`, a layer above the backfilled history, read by `live_panel.frozen_panel()` while its record holds.
   * **Its stage-2 column:** `data/studies/source_reconciliation/applied/speed_columns_repaired.parquet` (`live_panel.decided_column()`).
   * **Built by** `src/eda/source_reconciliation/apply_speed.py --build`.
   * **How it reaches the model.** A retrain's `in_season_retrain/speed_extend.py` writes the new instance's own speed table from this pair. The daily engine reads the pair for an instance without its own table.
   * *Changed when carrying it out.* The recommendation said the speed fix must wait for the retrain because putting it in earlier would make the daily engine refit the speed stage between retrains. **That was wrong for the instance in use.**
     * Since the 20–21 Oct retrains, an instance carries its own speed table (`stage2_speed_columns.parquet`), and its stage-2 coefficients are keyed on that file.
     * So the shared history could be repaired at once without touching the live model. The live instance keeps its own table, and the repair reaches stage 2 through the next retrain's table, as the owner wanted.
     * An older instance without its own table (built before 20 Oct) would refit on the repaired column if it were used again.
   * **Today's live speed form does not move:** 0 of 1,101 players, since every repaired row is older than the form's 364-day history.
   * **Its own harm check,** since the retrain's harm check holds both instances on the frozen reference's speed column and cannot see it:
     * the result is in the Status section;
     * the rule: harm = worse by more than 0.10 mLL with the whole 95% interval below 0.
4. **The next retrain must carry them** (the owner's "aware of these intended revisions ..., not simply adding the latest data").
   * **The register:** `data/studies/current_best_model/pending_at_retrain.json` lists every revision decided for the next retrain, with its checks (`src/eda/current_best_model/pending.py`; this decision's check is `src/eda/source_reconciliation/verify_applied.py`).
   * **`tp.retrain()`** (the notebook's C0) lists the pending revisions in its plan and **refuses to start while one is missing from the shared tables.** Today that means: run B6 first.
   * **`retrain.sh`** checks the built instance before its fits: its Stage 0 and its own speed table. It writes `<instance>/revisions_at_build.json` and stops when a check fails (no fits, no switch). After a switch it marks the revisions applied.
   * **CLAUDE.md** names the register and this decision, for an agent running the retrain by hand.
5. **Not included:**
   * **The 20th Tennis My Life row** (a men's 2015 qualifying match only Tennis My Life holds). It is lower-level, and the source order after the splice is a separate open question (README § 8, item 3).
   * **The lower-level winners, scores and statuses** (2 winners, 113 scores and statuses): the candidate route (item 5).
   * **The 101 Slam break-point differences:** for review only.
   * **The odds stand-in:** the 21 Oct amendment brings Pinnacle's closes from November 2025 at the next retrain; the three-price blend for the earlier rows was not part of this approval.
   * **ManTennisData's qualifying boxes:** the gap-fill policy's route (item 9).
   * **The women's indoor order:** still the owner's confirmation (item 6).
   * **The three-reviewer check** the recommendation offered for S1 and O1: left out of the owner's quote, so not run.
6. **Where this departs from the rules, and why.**
   * **Lower-level rows.**
     * The one ATP Challenger match in O1, and the four WTA 125 editions that move from 250 to 125, are lower-level. The 14 Oct rule sends another source's revision of a lower-level box score through a candidate build.
     * They enter here as part of a decided repair, as the 8 Oct fixes' Slam-qualifying rows did (`history.py` accepts every match the decided tables name; since this decision, every match of an edition the event table names).
     * The reason: the rule guards against sources that count differently, and these follow the tour's own records.
   * **WTA Paris 2010–12.** The approval named 2013–14, the editions in the model's frame. The study found the same fault and the same evidence on all five editions 2010–14, so all five are corrected: correcting two would leave one event on two surfaces. 2010–12 are history only (no training row); they feed later matches' surface inputs.

## Fixes made on the way (needed for any Stage 0 build today)

* **The id-alias check.** Tennis My Life's 2026 WTA file of 22 Oct (07:30) writes nine players under their established ids. Their aliases then had no rows, and Stage 0 stopped ("have no rows and were not merged ... rebuild the table"). That would have stopped the next bet-day run and every rebuild.
  * **The fix:** an alias whose second id has no rows, while every row under its player's name carries the established id, is satisfied by the source itself. It is reported, not stopped. Any other alias without rows still stops the build.
  * A replay of an older dump still holds the second ids, which the alias maps as before.
* **Replays read the instance's own correction tables** (`dp_steps.step_worktree`, `dp_worktree.setup`).
  * A replay copies the decided tables of the instance's build tree into its work tree. So a correction decided after an instance was built does not reach that instance's replay, and the proof stays exact.
  * Live runs read the repository's tables.

## Status

**Carried out on 22 October 2026, from about 10:50 PDT.**
* **The tables:** written at 11:15 PDT (18:15 UTC), each repair first re-checked against today's raw rows (`src/eda/source_reconciliation/apply_repairs.py`; `data/studies/source_reconciliation/applied/applied.json`).
  * `row_corrections.csv`: 2,951 → 3,152 rows.
  * `event_corrections.csv`: 20 rows (new).
  * The tables they replace are kept beside the record (`row_corrections_before.csv`).
* **The dry run** (Stage 0 built twice from today's dump, the decided tables before and after; every column compared, match by match):
  * **1,166 matches differ, exactly the ones the repairs name;** every named match changed.
  * Service games now match the point record in 122 of 122.
  * The 71 boxes now match the tour's (the 28 whose service games Stage 0 had blanked are complete again).
  * The 8 matches read retired.
  * 689 matches are at their edition's corrected level, and 277 Paris matches are on hard.
  * Nothing else moved.
  * `history.py` on the repaired build: the template may be built (decided repairs 2,995 → 4,161; gated lower-level changes 0).
* **The speed repair:**
  * built and checked;
  * its harm check, 2020–2024, both tours, both stages, positive = the repaired history better: **+0.008 [−0.026, +0.042] mLL per match, unresolved, P(better) 0.68: no harm.** Men: +0.015 [−0.050, +0.081]. One season's slice (2022) reads worse by 0.046, far inside the harm line; slices of one comparison are one reading.
* **The live instance's proof still holds:**
  * The replay of 13 Jul 2026 was run with the repaired tables already in the repository, up to the inputs (no fit).
  * It read the build tree's tables, and its 57 inputs equal `template_2026-10-21b`'s frame as on 21 Oct: 23 matches, the IOS inputs exact, every input within 4.4e-6, which passes the switch's rule.
* **In the model:** none of it yet. The live instance (`template_2026-10-21b`) was built before. The register lists the revisions as pending, and `tp.retrain()` reports them "NOT in the tables" until the shared tables are rebuilt (B6).

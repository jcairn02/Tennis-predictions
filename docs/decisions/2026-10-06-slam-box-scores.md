# Wimbledon and US Open 2026 box scores come from the official feeds

**Delegated by the owner on 6 October 2026.** Asked "How should Wimbledon 2026 be fixed: take the counts from the official feed, or leave them blank?", the owner answered: "I want you and a highly intelligent opus 5.5 extra high agent to discuss this and arrive at a solution."

Decided the same day by Claude after one round of review with an independent Opus agent. Recorded on 6 October 2026.

The US Open part went beyond the question's wording, so it was put to the owner. Later that day the owner gave two conditional answers:
* on the US Open: "Yes if you think its most likely to be predictive". Claude judged that met (point 4).
* on the rebuild: "Yes if you think its most likely to be what the end state of our model will want". It ran that night (point 5).

## Decision

1. **Every Stage 0 match of Wimbledon 2026 takes its whole box score from the official Wimbledon feed.** That is all nine counts, for both players, from one source per match, never mixed inside a match. It covers 366 matches: the men's main draw and qualifying, and the women's main draw. Stage 0 has no women's qualifying after 25 May 2026; that is a separate coverage question.
2. **Two Wimbledon 2026 matches also take the feed's score and duration**, because Tennis My Life's (TML) score of the deciding set is wrong:

   | Match | TML's score | Feed's score | Feed's duration |
   |---|---|---|---|
   | Djokovic d. Safiullin, R16 | 7-6(6) 6-3 3-6 6-2 | 7-6(6) 6-3 3-6 6-3 | 206 minutes |
   | Zverev d. Lehecka, R16 | 6-4 7-5 3-6 6-3 | 6-4 7-5 3-6 7-6(6) | 202 minutes |

   The feed's own point stream confirms both scores. TML's serve points cover only part of those matches' points.
3. **This is an exception to the match-clock decision's "results reach Stage 0 only from Tennis My Life".** The exception covers these matches' box scores and the two scores, and nothing else. The [match clock](2026-10-05-match-timing.md) itself is unchanged: no date moves, and the Slam feeds are already timing sources.
4. **The US Open 2026 under the same rule, confirmed.** The rule: at a Slam whose official feed is held and has matched Sackmann's history, the feed is the box-score source.
   * **Scope.** That covers 365 matches. The 366th is a walkover with no box score and keeps TML's row.
   * **Where TML is wrong.** TML's US Open 2026 agrees with the feed in 97–100% of player rows. But ten player rows of the final qualifying round (Q3) have the Wimbledon fault. In one, TML has 98 first serves in from 109 serve points, against the feed's 58.
   * **Judged most likely to be predictive.** The model was trained on Sackmann's counts. In 2022–2025 the US Open feed equalled them in 98.3–100% of player rows on every count, and in 100% in 2024 and 2025 ([referee_vs_stage0.csv](../../data/studies/data_continuity/referee_vs_stage0.csv)). So the feed measures what the training data measured. TML differs only where its own counts are impossible: second serves counted as first.
   * **Effect.** The change is small: the men's qualifying rate moves from 58.9% to 58.1% first serves in. It is a correction, and no mechanism makes the faulty values more predictive.
5. **Applied at the coordinated rebuild of 6 October 2026** (7 Oct, 00:05 UTC). Before it, the three studies running at the time confirmed they did not read the tables it rewrote.
   * **Every Stage 0 build now applies the table by default.** `stage0_build.py` reads `data/studies/data_continuity/slam_box_overrides.csv` unless given `--no-box-overrides`, so no later rebuild drops the fix. Another table needs `--confirm-live-overrides`.
   * **The rebuild ran in one command,** `src/eda/data_continuity/rebuild_stage0.py --expect <the dry run's build>`. Its record is [rebuild.json](../../data/studies/data_continuity/rebuilds/2026-10-07T0005Z/rebuild.json). In order:
     1. It kept everything it would replace, 366 MB with a SHA-256 manifest, in `rebuilds/2026-10-07T0005Z/replaced/`. Stage 0's code had changed, so the tables of 30 Sep could not be rebuilt later.
     2. It built Stage 0. The new tables equal the second dry run's override build, row for row.
     3. It re-linked the closing odds.
     4. It rewrote 42 changed match ids in the frozen match-timing link files.
     5. It refreshed and checked the timeline.
     6. It rebuilt the per-player, IOS and leak-proof inputs and the TrueSkill table.
   * **The rebuild also brought Tennis My Life's results to 5 October.** They were downloaded that evening under the [file-versions decision](2026-10-06-tml-file-versions.md): 873,364 matches, up from 872,704. A second dry run on those files passed like the first ([stage0_dry_run_tml1006.json](../../data/studies/data_continuity/stage0_dry_run_tml1006.json)):
     * the same 251 matches and 735 player rows changed;
     * nothing changed outside the overrides;
     * every count equalled the feed's.
   * **It also brought code changes unrelated to this decision.** `stage0_build.py` and `src/eda/feature_alpha_audit/repair_data.py` changed on 2 October, after the tables of 30 Sep were written. On the same inputs, 8,040 matches changed:
     * 7,650 matches, 7,643 of them ITF and 98% of them from 2020–2024, change their `format` from standard to match tiebreak. Their deciding match tiebreak is no longer counted as games.
     * 305 player rows move to the player's own Sackmann id. Every one was checked against the name that id carries in Sackmann's rows; 301 match exactly, and 4 differ only by a hyphen.
       * The old ids were wrong. Some were a Tennis My Life code split from the player's history. Others were another player's id: Andreas Haider-Maurer's 2011 match sat under Blaz Kavcic's.
       * An earlier version of this record called these "a different player on side A or B". It is the same player under the right id, and 21 matches only swapped sides.
     * 42 June-2026 WTA match ids change with them.
     * 137 implausible durations are blanked.
   * **Judged to be what the end state of the model wants.** Every change is a correction:
     * the official counts at the two Slams;
     * games counted as games;
     * each player's history under one id;
     * the newest results.

     The studies already published keep their own frozen inputs, and their input hashes tie them to the tables of 30 Sep.
   * **Not yet rebuilt: the model's own inputs.** `model_frame.parquet`, the offset-Elo frame and the surface IOS arms are still on the tables of 30 Sep. The [offset-Elo decision](2026-10-06-offset-elo.md) lists the steps that bring them onto this rebuild, starting with Stage 1's baselines.

## Why

* **The feed is right and TML is wrong.**
  * The feed matched Sackmann's counts in 99.6–100% of player rows at every Wimbledon from 2021 to 2025, and in 98.7–100% in 2019, on every count.
  * In 2026 its statistics equal its own point stream in every main-draw row.
  * TML moved about six serves per man from second serve to first. Those points were won at second-serve rates, not first-serve rates:
    * men's qualifying: the 1,742 extra first serves were won 51.7% of the time, against the feed's 50.8% on second serves and 73.1% on first;
    * men's main draw: the 1,106 extra were won 42.4%, against 50.6% and 74.2%.
  * Pooled first serves in, men's main draw: TML 67.7%, the feed 63.8%. The feed's figure is within every earlier year's range (62.5–63.8%).
  * Evidence: the [data continuity study](../studies/data_continuity/README.md), sections 3.2 and 4.5.
* **Replacing beats blanking.** A blank count loses information but adds no bias: Stage 0 already blanks counts that fail its checks, and the features skip them. A wrong count biases every later feature built on it for that player. A trustworthy replacement exists, so it is used.
* **The dry run** ([stage0_dry_run.json](../../data/studies/data_continuity/stage0_dry_run.json)) passed. It built Stage 0 twice into a scratch folder, without and with the overrides:
  * the live tables did not change;
  * no match changed outside the 731 override matches;
  * after the overrides, all nine counts equal the feed's in every one of them;
  * Wimbledon's men's first-serve-in rate returns to 63.8% (main draw) and 61.6% (qualifying), from 67.7% and 70.9%;
  * 246 matches whose service games Stage 0 had blanked get the feed's, and all 731 have a full box score.

## Where it is implemented

* **`src/eda/data_continuity/slam_overrides.py`** writes `data/studies/data_continuity/slam_box_overrides.csv`.
  * Each row names its TML row by tour, tournament id, round and both players' name keys, and gives the feed's counts for TML's winner and loser.
  * Each row carries the feed document's SHA-256 and retrieval time.
  * The file is written only when every match resolves exactly once, no surname disagrees, and every feed box score passes Stage 0's checks under the feed's score.
* **`src/eda/predictability_diagnostic/stage0_build.py`**:
  * `apply_box_overrides` runs right after the rows are read, before any score is parsed or box score checked, and logs rules O1 and O2 in the cleaning log.
  * `--out-dir` builds elsewhere.
  * Into the live folder it applies overrides only with `--confirm-live-overrides`.
  * With no new arguments the build is unchanged.
* **`src/eda/data_continuity/stage0_dry_run.py`** is the dry run.

## Not decided

* ~~Collecting each Slam feed as it is played.~~ Settled the same day in the [download-cadence decision](2026-10-06-download-cadence.md). Each feed is collected after its event, with a weekly reminder until it is. Collecting during the event is built with the betting pipeline.
* **Making the Slam feeds the routine box-score source** for later Slams. The override table covers 2026's two events. A later event's feed needs its own table rows, from `slam_overrides.py`, once that feed is collected.
* **Roland Garros 2026.** No official feed is held.
  * Stage 0's 127 men's main-draw matches have no box score, because Sackmann's blank rows take precedence over TML's.
  * TML's men's qualifying fails Stage 0's checks in 98 of 112 matches: 84 lose their service games and 14 their whole box score.
  * Left as it is.
  * **Corrected 9 Oct 2026 (the facts only; nothing here is decided again):**
    * **RG 2026's official feed has been held since 7 Oct:** the Infosys key statistics and point-by-point, in `data/raw/point_sources/infosys_slams/RG/2026/`. RG's own match statistics (rolandgarros.com) were added on 9 Oct, by `src/ingest/point_sources/rolandgarros.py`.
    * **The women's 127 main-draw matches have no box score either,** for the same reason as the men's.
    * **A candidate applies point 4's rule to Roland Garros** ([report § 8](../studies/rg_first_serve_recount/README.md)). Three reviewers confirmed RG's own box for:
      * all 351 Stage 0 matches of RG 2026;
      * 953 of 2022–2025.

      It enters only as a candidate under the frozen-reference rule. Adopting it, and extending the rule to Sackmann's own 2022–2025 rows, are the owner's call.
    * **Decided since:** the owner extended point 4 to Sackmann's Roland Garros 2022–2025 rows, with adoption on a harm check ([decision of 9 Oct](2026-10-09-roland-garros-box-scores.md)).
* **Sackmann's Roland Garros men's qualifying of 2022–2025.** It has the same fault: 65.2–68.6% first serves in where TML has 61.2–63.3%, and the extra ones were won at 47.7–52.2%, second-serve rates. It is in the training data. It is flagged and left unchanged until a study measures its effect.
  * **Update, 9 Oct 2026:** the study is item 6 of the [adoption checklist](../studies/adoption_framework/checklist.md). Its report is the [Roland Garros first-serve recount](../studies/rg_first_serve_recount/README.md).
    * RG's own per-match records are now held for every edition.
    * The fault is in every draw of 2022–2025, not only the men's qualifying.
    * Its corrections enter only as candidates.
* **Roland Garros 2022's men's main draw**, which reads about 66% first serves in in both sources against 62–64% in the other years. With no feed to check it, it goes with the item above.
  * **Update, 9 Oct 2026:** RG's own statistics put it at 63.4%. Sackmann's 66.1% is the same fault (same report).
* **The source order for other events** (the WTA API, TDI). Their disagreements with TML are not yet settled, so it waits.
* **Women's qualifying and WTA 125 after the splice**, which TML does not publish and the WTA API and Slam feeds hold. That is a coverage decision.

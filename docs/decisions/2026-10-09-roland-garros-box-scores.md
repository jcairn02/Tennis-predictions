# Roland Garros box scores from RG's own record, and the Infosys Slams' swapped service games corrected

**Decided by the owner on 9 October 2026.** The owner asked for recommendations, not open choices ("SUGGEST to me, don't delegate to me. I am only the final arbiter of YOUR suggestions"). Claude recommended the three points below, each with its checks ([report § 8.7](../studies/rg_first_serve_recount/README.md)). The owner answered: "Execute and fix".

Recorded the same day by Claude, who carries it out.

## Decision

1. **Roland Garros's own record is the box-score source for Roland Garros 2022–2026.**
   * **The extension.** This extends point 4 of the [Slam decision of 6 Oct](2026-10-06-slam-box-scores.md) to Sackmann's own rows of 2022–2025 ("at a Slam whose official feed is held and has matched Sackmann's history, the feed is the box-score source"). Point 4 had covered only rows after Sackmann's data ends.
   * **What a match takes:** both players' nine counts from RG's statistics, with service games from its point-by-point.
   * **Which matches:** those the three reviewers confirm with the same values under this rule.
   * **Scope:** Roland Garros only. Other Slams and events are not covered.
2. **The changes enter as one candidate under the frozen-reference rule, and are adopted on a harm check declared now.**
   * **The rule:** adopt unless the candidate is worse than the frozen reference by more than 0.1 mLL per match with the whole 95% interval below 0, or an input is flagged "uneven".
     * The comparison: `compare.py`, both stages, both tours, seasons ≤ 2024.
     * The harm rule is item 5's.
   * **The 2025–2026 part** is adopted with it on the data evidence. It is not read on the 2025–2026 seasons, so as not to spend the clean holdout on a data fix.
   * **If the rule stops the adoption,** the candidate is not adopted, and the stop is reported with what drove it.
3. **The swapped service games of the Infosys Slams are corrected.**
   * **The fault:** at the Australian Open and Roland Garros, Sackmann's rows often give the two players each other's service games, mostly as the score gives them if the winner had served first.
   * **The fix:** the two counts exchanged back (`exchange_svgms`, decided on 8 Oct as F2y). It applies wherever the Slam's own point record proves who served first, and each match is confirmed by three reviewers. It joins the same candidate.

## Why

1. **The evidence favours RG's record even on the small differences left out under unanimity.**
   * Where an independent record holds every point, it reads RG's value: 18 to 0 on the 237 matches, and about 94% on the whole class.
   * 44 player rows in those matches are off by three first serves or more.
   * **The dissenting reviewer's grounds,** as it corrected this record: the rule's scope, and, under the stricter 8 Oct bar, changes that no record could settle (Court Vision catches RG wrong about once in 23 on such sides). Under the extended rule it confirmed all 237 with the same values, finding no record against RG on any of them.
2. **A data fix is decided on data evidence** (adoption framework § 2). The model reading is insurance against harm, not the case for the change.
3. **The service-game fault is systematic.** It was checked on 9 Oct, counting completed matches:
   * RG 2019–2021: 241 of 1,343 matches;
   * AO 2025: 77 of 455 matches;
   * Wimbledon and the US Open are clean.

   The proposal itself counts retirements too: 242 and 81 swaps. All three reviewers confirmed those 323.

   Service games feed 6 of the model's 58 inputs, the hold rates and break points faced per service game. The error credits the winner with an extra service game.
   * *Corrected 10 Oct 2026:* 7 inputs. The candidate's input check shows a seventh moving with them: prod_hold, the matchup product of the IOS hold ratings.

## Where it is implemented

* `src/eda/rg_first_serve_recount/`:
  * `whole_box.py` and `consensus_followup.py` for point 1;
  * `service_games.py` and its consensus for point 3.
* `stage0_build.apply_box_overrides` names a Sackmann row through a `source` column.
* The candidate, its build commands and its dry run: [report §§ 7–9](../studies/rg_first_serve_recount/README.md).
* Item 6 of the [adoption checklist](../studies/adoption_framework/checklist.md) carries the harm rule. Its steps 3–4 build and check the candidate.

## Carried out the same day

* **Point 1:** with the rule extended, all three reviewers confirm all 1,541 proposed Roland Garros matches of 2022–2026 with the same values.
* **Point 3:** the Slams' own point files were fetched back to AO 2018 and RG 2013 (raw only).
  * The fault is in every Australian Open from 2019 to 2026 and at Roland Garros 2015–2021. AO 2018 and RG 2013–2014 are clean.
  * All three reviewers confirmed 809 of 810 swaps. They left out Stosur d. Halep (RG 2016), whose row also has its break points wrong.
* **Point 3, extended the same evening at the owner's word** ("Fix the remaining service-game errors that aren't simple swaps … plus 123 Roland Garros 2017 matches recorded as 0 and 0").
  * Where the point record proves who served first, service games that are blank, zero or wrong without being an exchange are set from the score's alternation of serve. This uses a new correction type, `set_svgms` (rule E8).
  * Each must agree with the row's own break points and score; 2 that don't are left out.
  * All three reviewers confirmed all 558, each with its own values: 460 blanks filled (RG 2013–2014, RG 2017 and others) and 98 wrong counts.
* **Point 2:** the candidate (`data/studies/rg_first_serve_recount/followup/confirmed/candidate/`) dry-runs clean with all of it: 4,664 rows change, none outside its tables.
  * Its build and harm check run in the build queue after item 5 of the checklist. *(They ran next instead, at the owner's word of the same evening: "Run the candidate build and harm check next in the build queue".)*
  * Until it is adopted, Stage 0 and the model are unchanged. *(Adopted 10 Oct; applied with the next coordinated rebuild: see below.)*

## The harm check, 10 Oct 2026: no harm, so the candidate is adopted

* **The reading** (`compare.py`, both stages, both tours, 2020–2024, 22,265 matches; + = the candidate better): −0.026 [−0.076, +0.023] mLL per match, unresolved, P(better) 0.145. Men −0.023 [−0.084, +0.038]; women −0.030 [−0.103, +0.043].
* **Under the rule of point 2: not harm.** The estimate is above −0.1, and the interval includes 0.
* **The input check** flags seven hold inputs in WTA 2013–2014 only.
  * They are the fix's own dose. The candidate's sets are the WTA's first service-game counts of those seasons, and nothing moves before RG 2013.
  * The adoption-by-kind decision of the same evening counts a flag as harm only "in a way its dose does not explain" ([decision](2026-10-09-adoption-by-change-class.md), point 4). Point 2's wording predates it, and is read with it ([report § 10.3](../studies/rg_first_serve_recount/README.md), step 9; [process log](../studies/rg_first_serve_recount/process_log.md), judgment call 2).
* **What the comparison can see:** ±0.049 mLL, against a repair's plausible effect of about 0.02. It serves as the harm check, not as evidence of a gain, and the adoption earns no edge credit.
* **The candidate was built on the reference's recipe** (58 inputs, the books' average, the old indoor input), so the reading isolates the repair.
* **Applying it:** the two decided tables take the candidate's (`src/eda/rg_first_serve_recount/adopt.py`), in the same coordinated run as the live Stage 0 rebuild.
  * It waits for the lower-level-evidence study's arm builds, whose gates fail on any main-tour change.
  * Until it runs, Stage 0 and the model are unchanged.
  * The steps: [report § 10.4](../studies/rg_first_serve_recount/README.md).

## Adopted by the owner, 10 October 2026, with a tripwire

**The owner's words:** "Official decision: adopt, with the tripwire on the Slam number."

The owner questioned the reading first: the Slam slice read worse (−0.065, P(better) 0.09). Claude answered three questions in turn: why the fix was made, whether a prior was carrying it, and whether it was applied correctly. The last was answered by five end-to-end checks (`verify_applied.py`; [report § 10.3](../studies/rg_first_serve_recount/README.md), steps 13–14).

**The tripwire.** Declared 10 Oct 2026, before any match it will read.
* **The question:** does the repair harm forecasts at the Slams, on matches it was never read on?
* **The matches:** the four Slams' matches, as `compare.py`'s "Slams" level, played after the freeze, from the Australian Open 2027 on. The 2025–2026 holdout stays unread.
* **The comparison:** the template as it then stands, against the same template built on the pre-adoption tables (`adopt.py`'s kept copies), with the code the same and only these tables toggled.
  * Both stages, both tours, seeds 0–3 paired.
  * Season 2027 is trained on 2013–2026, as the template trains.
* **When:** first after all four 2027 Slams (about 1,000 matches, with the week-block interval), then after each later Slam, cumulating the new matches.
* **The trigger:** the repair reads worse at the Slams with the whole 95% interval below 0. Claude then recommends reverting (`adopt.py --restore`, then a coordinated Stage 0 rebuild) and looks for the cause.
  * An unresolved reading, of either sign, triggers nothing.
  * All new matches, both tours, are reported beside the Slam figure, but do not trigger.
* **What it can see:** after the first year, an interval of roughly ±0.2–0.3 mLL per match at the Slams. It guards against a large harm, which the checks of 10 Oct make unlikely. A lean the size of today's (−0.065) would take many years of Slams to resolve.
* **Where it is tracked:** checklist item 12 of the [adoption checklist](../studies/adoption_framework/checklist.md), with its prompt.

**Applying it: after the level-layer work, not now.**
* Another session is making the level-evidence layer part of the template ([its prompt](../studies/lower_level_evidence/system/IMPLEMENTATION_PROMPT.md)).
  * It edits the chain's builders and builds the template.
  * Its replay check builds Stage 0 from the decided tables.
* Swapping the tables, or rebuilding Stage 0, while that work runs would change its inputs mid-build, and could make its replay fail for a reason not its own. The owner asked that nothing conflict with it.
* **The steps, once that work reports done** (its template build collected, its replay passed):
  1. `./python.sh src/eda/rg_first_serve_recount/adopt.py --check`, then `--apply`;
  2. `./python.sh src/eda/data_continuity/rebuild_stage0.py`, the coordinated rebuild;
  3. `./python.sh src/eda/current_best_model/history.py`;
  4. a template build, which then carries the layer and this repair, and `prediction_run/replay.py`.
* **One interaction to know.** The repair changes Roland Garros qualifying box scores of 2022–2026. The level layer treats Slam qualifying as lower-level evidence, with parameters fitted on the tables of 8 Oct, so those parameters saw the faulty rows. The layer's yearly refit takes the corrected rows.
* **Until the steps run,** Stage 0 and the model are unchanged.

## Not decided

* **Whole boxes from the other official records:** the Olympics (not a Slam, and no clean edition to check against) and the Australian Open (not proposed).
* ~~**Service-game mismatches that are not exact swaps**~~ **Decided the same evening** ("Execute these 3 fixes"): set from the score and the proven first server, under the same review. See "Carried out the same day" above.
* ~~**Future Australian Opens and Roland Garros**~~ **Decided the same evening:** [future Australian Opens and Roland Garros take their box scores from the Slams' own records](2026-10-09-ao-rg-box-scores-from-feeds.md).

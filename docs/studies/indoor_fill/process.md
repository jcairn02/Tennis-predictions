# How the indoor-fill study was done: a record for audit

9 October 2026 (the session ran from 00:20 UTC on 10 October; the study's results were read at 01:49, and this record was written at about 02:55) · For a later reviewer, human or model, who wants to judge whether the study was set up soundly and whether its conclusions follow from its evidence.

The [README](README.md) states the conclusions; the [decision record](../../decisions/2026-10-09-indoor-input.md) states what changed. This file records the process:
* what was known when each choice was made;
* the alternatives set aside, and why;
* how strongly each claim was checked;
* where the work is weakest.

It was written after the results, at the owner's request, from the session's transcript and the evidence files. Its account of the session's reasoning is the session's own and cannot be checked independently.

## 1. The request, and how it was read

The owner's words:

> "In my current best performing model the indoor/outdoor input is missing for every women's match. It could be filled from tennis-data.co.uk's Court column. Get this data and integrate it into our models training data sources after you've downloaded it all"

> "The 127 men's matches of the 2026 US Open are also missing it, obtain them if you can find them"

| Phrase | Read as | Other readings set aside | Why |
|---|---|---|---|
| "Get this data … after you've downloaded it all" | Fetch every tennis-data season workbook again, all seasons the site lists | Only the missing seasons; only 2026 | Cheap (49 requests), and it shows whether anything on disk was stale |
| "integrate it into our models training data sources" | Make the filled input the default of every future build of the current best model (the chain's frame builder). Test it as `CLAUDE.md` requires for new data; keep the frozen reference and the stored instances as built | Write it into Stage 0; rebuild the stored instances; only test it and leave the default unchanged | See § 3.1. The owner asked for integration, so it was integrated, with a harm check fixed in advance as the project's rules require |
| "It could be filled from tennis-data.co.uk's Court column" | A suggested means, not a required source | Court as the only source | **The study's one departure from the request** (§ 3.2). It is flagged for the owner to confirm, and a one-line change reverses it |
| "obtain them if you can find them" (the US Open) | Find a source for the 127 men's matches | — | tennis-data's own rows for those matches say "Outdoor" |

## 2. Chronology

Times are UTC on 10 October 2026 (local time 9 October, UTC−7). Tool-call times are from the session's transcript (`C:\Users\zerom\.claude\projects\c--Users-zerom-Documents-Tennis-predictions\b9449a90-ef05-4cbd-83dd-6a33f1fa8140.jsonl`, on the owner's machine only). Output times are from the evidence files' `generated_at` fields.

| Time | Step |
|---|---|
| 00:20–00:42 | Read the project's guides, the current-best-model decision, the earlier notes on the women's indoor gap (tour pooling, feature interactions), the chain, `compare.py`, the lean review and the prediction run. Measured on disk: every model match has a tennis-data row with a Court value; Court and TML's flag agree on 99.2% of men's matches; no event mixes values; the 127 US Open matches are in tennis-data's 2026 workbook. Found other sessions' candidate builds reading the shared dump through junctions |
| 00:42:42 | `snapshot.py` launched: the download beside the dump |
| 00:42:43 | WTA calendar for 2013–2015 and 2017 (4 requests) |
| 00:43:54 | Cross-check, first version: women's events matched to WTA editions by tennis-data's Location and first date |
| 00:46:17 | Snapshot done: 43 workbooks unchanged; ATP 2026 has 62 rows appended; 3 seasons the dump never held |
| 00:46:22 | `status.py`, first version: the literal reading. For the women, tennis-data's Court came first, the calendar only as a fallback |
| about 00:47 | First cross-check run: 26 disagreements (16 women's events, 10 men's); 14 women's events unmatched (Eastbourne and Queen's) |
| 00:48:58–00:49:21 | Seven venue searches (§ 4) |
| 00:51:05 | WTA calendar for 2010–2012 (3 requests) |
| **00:52:41** | **`status.py`, final version: the women's order changed to the WTA's calendar first. The departure was decided here, on data alone; no fit existed** |
| 00:53–00:56 | Cross-check on the final rule (`crosscheck.json`; rerun at 01:36 with only a path-format change); `live_check.py` |
| **01:00:43–01:01:05** | **`tabpfn_thinking/build_frame.py` edited: from here, every chain build set up from the repository carries the new input** (§ 5, point 1) |
| 01:02–01:06 | `arm.py --chain-check`: the candidate frame and its checks (`arm.json`) |
| 01:07–01:09 | `fits.py --check`: the candidate's jobs differ from A2's in the indoor column alone (`check.json`) |
| **01:09:45** | **The test plan written into the README** |
| **01:09:47** | **The 24 fits launched** (`fits.log`) |
| 01:14:26 | `build_frame.py` edited again: it also records each row's source. The candidate frame, written at 01:05, is not affected |
| 01:15:45 | First fit written |
| 01:20:28 | `score.py` written. It implements the plan's rule; no result existed |
| 01:40:51 | One more search (the 2023 Elite Trophy) |
| 01:42:24 | Scoring queued behind the last fit |
| 01:49:13 / 01:50:13 | `score_summary.json`, then `compare.py` against the frozen reference: the first results read |
| 01:51:50 onward | Results written up; decision record, indexes and `CLAUDE.md` updated |

**Seen before the plan was fixed:** every data check (download, cross-check, venue searches, live check, the candidate frame's checks, the jobs' equality). The A2 arm's fit files were opened for their metadata only (fingerprints, column lists), in `fits.py --check`. Their predictions were first read by `score.py` at 01:49.
* At the start the session read the lean review's published T2 result, quoted in the current-best-model decision. It concerns another input (`ios_points_short`).

**Changed after the results:** nothing in the rule, the candidate frame, the fits or the scorer.
* Documents only, plus one refactor in `prediction_run/run.py` (the WTA receipts are read once).
* The corrections of § 8.

## 3. The choices, and the alternatives set aside

### 3.1 Where the fill lives

* **Chosen:** in the chain's frame builder (`tabpfn_thinking/build_frame.py`), which calls `src/eda/indoor_fill/status.py`. Stage 0's own `indoor` column stays as it was.
* **Set aside:**
  * **Stage 0.** `current_best_model/history.py` compares Stage 0's match facts, `indoor` among them, with the frozen reference's, and `run_chain.py --setup` refuses a template build when they differ. Stage 0 is also built before Stage 1 links tennis-data's rows.
  * **A step after the chain** (patching `model_frame.parquet`). The live path builds frames through the same chain, so a patch would have to be repeated there.
  * **A new chain lane.** More moving parts for a single column.
* **Cost of the choice:** the rule reads Stage 1 and the tennis-data partitions from inside the frame builder. That is why the builder now hashes Stage 1 before and after reading it.

### 3.2 Which source, per tour

* **Chosen:**
  * men: TML's flag first (unchanged), then tennis-data's Court;
  * women: the WTA's calendar first, then Court.
* **Set aside:**
  * **Court alone, the literal request.** It is wrong on 26 of the 1,609 model events (§ 4); for women it would differ on 371 matches.
  * **Court first for both tours.** That would change 273 men's values that TML has right.
  * **TML first for the women.** TML gives a flag for only 384 women's model matches, all in 2026, and is wrong on one of those events (Singapore 2026, where the WTA and tennis-data both say indoor).
* **The basis:** data only, before any fit. In every disagreement checked, the source chosen first was right.
* **What would reverse it:** finding that the WTA's `inOutdoor` means something other than "played indoors" (§ 5, point 4); or the owner preferring the literal reading. In that case put "own" and "event" before "calendar" in `STEPS["wta"]`.

### 3.3 Event level or row level

* Court never differs within an event (0 of 1,609 model events), so the own-row and event-level values are the same in training.
* The event level and the earlier edition are what a live match can have, so the rule falls back to them.

### 3.4 The live fallbacks and their order

* **Men:** TML's flag (live rows carry it), then the match's own row, then the event's rows, then the latest earlier edition.
* **Women:** the calendar, then own row, then event, then earlier edition, then TML's flag.
* **Why TML is last for the women:** it is sparse and was wrong on Singapore 2026.
* **Why "previous" uses the earlier edition's final value:** it is computed from earlier years only, so a later edition never informs an earlier one (a unit test checks this).
* The venue is an event attribute, not a result, so the match-clock rule does not apply. Using earlier editions only is a precaution.

### 3.5 Matching WTA editions to Stage 0 events

* **The method:**
  * candidates: the editions whose start − 3 days to end + 2 days holds the event's date in Stage 0;
  * first, an id match, where TML's id is "<year>-<the WTA's id>";
  * else name similarity of 0.6 or more against city or title, using Stage 0's name or tennis-data's Location;
  * ties go to the best match on Stage 0's name, then the nearest start.
* **The constants (window, 0.6, the 4-letter containment rule) were set by judgment and not tuned.** By eye the session read only the 16 disagreeing events and the unmatched ones: in all of them the matched title was the right edition.
* **The result:** 737 women's events matched, 12 not (Eastbourne 2013–2025, absent from the WTA's calendar until 2026).
* **By method, per season** (`crosscheck_events.csv`, column `wta_how`): 2013–2015 all by name (Sackmann's ids). From 2016 most by id. In 2026, 43 by id and 2 by name: the Australian Open and Roland Garros, which Stage 0 files under ATP-style ids (580, 520).

### 3.6 Not restaging the shared dump

* Other sessions' candidate builds read `data/dump/` through junctions.
* Restaging rewrites a season's partitions in place, so it could have failed a read mid-run, or slipped new 2026 rows into another session's comparison.
* So the download went to `data/raw/indoor_fill/`. Its comparison shows restaging later keeps every Stage 1 link valid: rows were only appended.

### 3.7 The test

* **A patched frame, not a chain build.**
  * The candidate is the Pinnacle-first instance's frame (the tables of 8 Oct) with only `in_indoor` replaced.
  * A `run_chain.py --setup --candidate` build would also have picked up whatever changed in the tables since 8 Oct, and taken hours.
  * The cost: the candidate frame comes from `status.py`, not from a chain run. § 4 says what was checked instead.
* **Base: the lean review's arm A2,** the decided 57 inputs. Its fits (seeds 0–3, 2019–2024, close-fed and opening-fed) already existed, with the same code, checkpoint, library versions and GPU.
  * The lean review's reproduction check found these fits deterministic: a refit equals the stored fit bitwise (`data/studies/lean_review/repro.json`: max difference 0.0).
  * So the paired difference reflects the input change, not GPU noise.
* **Seasons 2019–2024 fitted, 2020–2024 scored.** 2025–2026 are the proposed clean holdout and were not read.
* **Yardsticks:**
  * Pinnacle's opening line (O), the lean review's declared primary;
  * the close (C).
* **Populations:** both tours (primary), women, men.

### 3.8 The rule

* Adopt unless:
  * both tours or women, at O or at C, have the 95% interval below 0;
  * or the realisation at O falls below 0.9 while A2's is not.
* It is a harm check, chosen because the adoption framework treats a data fix, or wider coverage of an existing input, as free and reversible (cost 0). The outcome test is there to catch a bug, not to prove an edge.
* A reviewer may find it too lenient (§ 5, point 3).
* **Read later under the owner's decision of the same night** ([adoption by kind of change](../../decisions/2026-10-09-adoption-by-change-class.md), recorded after these results):
  * the fill is a Repair (restoring lost coverage): data evidence decides, the comparison is a bug alarm;
  * its default harm tolerance, worse by more than 0.10 mLL with the whole interval below 0, is looser than this rule;
  * the readings pass both. The study's design did not change.

### 3.9 Checks not run

* **The shuffled twin** (adoption framework § 5). It measures whether added columns score well by chance. Here nothing was added; one column's missing values were filled. Not run.
* **The leak probe** (`match_timing/probe.py`). It is for features that combine different players' results; a venue attribute does not. Not run.
* **16 seeds.** The comparison used seeds 0–3, as the lean review did. The template forecasts with 16.
* **An independent review** (a red team, as several studies had). Not done.
* **An end-to-end chain build and a real prediction run.** Not done (§ 5, point 2).

## 4. How strongly each claim was checked

| Claim | Check | Strength | Evidence |
|---|---|---|---|
| Every model match has a tennis-data Court value | Read through Stage 1's links, by position, with the row's two names matched to Stage 1's | Strong | `crosscheck.json`; `status.td_fields` |
| The fresh download changes nothing for the model | SHA-256 against the dump's sources; row by row for the one changed workbook | Strong | `snapshot.json`, `snapshot_rows.csv` |
| Court and the second sources agree on 99.2% (men) and 98.8% (women) of matches | Event by event | Strong for the arithmetic. The women's figure rests on the edition matching (§ 3.5) | `crosscheck.json`, `crosscheck_events.csv` |
| tennis-data is wrong on the 26 disagreeing events | **Seven events by web search:** São Paulo 2016–17, Santiago (2023 only; the other seasons assume the same venue), Antalya 2021, Zhuhai 2015–19, Taipei 2017–18, Tokyo 2018, Tallinn 2022. **Three by general knowledge, not searched:** Stuttgart 2013–17, Dubai 2016, Guadalajara 2021 | Medium. The searches went through a tool that returns a model's summary of the results, not the pages; the pages are linked in the README | The README's table |
| The final values are right where the two sources agree | Not checked. Both sources could be wrong together | Unknown. One borderline case: the 2023 Elite Trophy, on a covered outdoor court, is "indoor" in both | — |
| The rule leaves no model match unknown and changes no value the model had | `arm.py`'s checks | Strong | `arm.json` |
| The chain builder gives the same column | `build_frame.indoor_codes` on the frame's 67,226 matches equals the candidate's column; with `--indoor-men-only` it equals the instance's | Medium. The full `build()` could not run on the repository's tables, whose Stage 4 pool predates the Stage 0 of 8 Oct. **No chain build has yet run with the change** | `arm.json` → `chain_builder` |
| The candidate's jobs differ from A2's in the indoor column alone | `fits.py --check`, season by season: labels, ids and every other column equal; A2's fingerprints match | Strong | `check.json` |
| The harm check's readings | `score.py`, through `compare.py`'s recipe | Strong for what it measures; its power is limited (§ 5, point 3) | `score_summary.json`, `scores.csv` |
| A prediction run reproduces the value | Simulated: each season with every tennis-data link removed | Medium. No real prediction run has used the change; the calendar pages were read as published on 9 Oct 2026 | `live_check.json` |
| The code does what the README says | 13 unit tests on made-up tables; the prediction run's 11 tests pass; smoke tests of the run helpers | Medium | `test/indoor_fill/` |

## 5. Weak points, most serious first

1. **The change reached other sessions' builds.** The frame builder is shared code. Any chain sandbox set up after 01:01 UTC copies it. Two sandboxes carry the new input, as found at about 02:30 UTC:
   * **`C:/Users/zerom/tnr_sb`**, created 01:35 UTC. It runs the Roland Garros box-score candidate (`run_chain.py --out data/studies/current_best_model/2026-10-09_rg_box_scores`; its lane 1 started at 02:26 UTC).
     * That candidate's harm check against the frozen reference will include the indoor fill as well as the RG box scores.
     * Its input check will flag `indoor` in the women's seasons.
     * The fill's measured effect (about 0.01 mLL, § 5, point 3) is far below that decision's threshold (worse by more than 0.1 mLL with the interval below 0), so its outcome should not move. The flag could still be read as a sign of the RG change.
   * **`tnr_sys5`**, created 02:08 UTC, with no build running yet. By its name it is the lower-level-evidence study's next sandbox. Its builds would differ from the same study's `tnr_sys1`–`tnr_sys4` builds, which predate the change, in the indoor input as well.

   **The remedies:**
   * build those frames with `tabpfn_thinking/build_frame.py --indoor-men-only`;
   * or compare them against a base that carries the fill;
   * or keep the indoor change in mind when reading their comparisons.

   Older studies' frames rebuilt in the repository now get the new input by default as well.
2. **Integration is checked at the level of the code path, not end to end.**
   * No `run_chain.py` build and no prediction run has executed with the change.
   * The first template build is the real integration test: its `in_indoor` should equal `status.table()` on its tables, and its manifest records the sources (`indoor`).
3. **The harm check can see only large harm.**
   * Its standard errors are 0.011 mLL (O, both tours), 0.018 (O, women), 0.007 (C, both tours) and 0.014 (C, women).
   * At 95% and 80% power it detects a true effect of about 2.8 × SE: 0.030, 0.051, 0.020 and 0.040 mLL.
   * The adoption framework puts the typical true effect of a new input at the close near 0.01 mLL. **A true harm of that size would pass unseen.**
   * "P(better) 0.75" is the flat-prior reading of this one test, not the chance that the fill helps.
   * The adoption therefore rests on the data evidence and the framework's default for free, reversible fixes, not on the outcome reading.
4. **What "indoor" means.**
   * Both sources label events, not matches.
   * Events with roofs (Slams, the 2023 Elite Trophy's covered court) are labelled by convention, and the WTA's convention may differ from tennis-data's.
   * The WTA's calendar is read as it stands in October 2026. Its value for a past edition could have been edited after the event. That is no leak of a result, but the training values are retrospective labels.
5. **The departure from the request.** The owner named tennis-data's Court; the study made the WTA's calendar the women's first source.
   * The reasons are in § 3.2, and the choice is flagged for confirmation.
   * A reviewer should judge whether the session should have asked before making it the default rather than after.
6. **The 127 men's US Open values are outside the outcome test.** 2026 is neither fitted nor scored here. They rest on tennis-data's row alone; that the US Open is played outdoors is not in doubt.
7. **The edition matching was read by eye only where it mattered visibly** (§ 3.5). A wrong match that happens to agree with tennis-data would not show; a reviewer can read `wta_title` for every event in `crosscheck_events.csv`.
8. **The scale of the comparison.**
   * Four seeds where the template uses 16.
   * The opening-line population is the complete cases with OddsTrader's timed Pinnacle line (2018 to Sep 2025, the 2021 US Open left out), 20,979 matches against 22,265 at the close.
   * Other targets the owner bets at (Polymarket 24–48 hours out) were not tested.
9. **The input check's flag was explained, not removed.** `compare.py` calls `indoor` "uneven": flagged in the 14 women's seasons, in none of the men's. The study reads that as the fill itself, since the women's column goes from missing to known, and shows the season profile moving with the calendar. A reviewer should check that reading against `arm/vs_reference_2026-10-08/season_profile.csv`.
10. **Evidence that the plan came first** is the transcript alone. The README's file times were reset by later edits, and no hash of the plan was taken before the fits.
11. **The download's receipts live in `data/raw/`, which is not under version control.** So do the WTA calendar pages. `snapshot.json` and the cross-check files in `data/studies/indoor_fill/` summarise them.

## 6. Reproducing it

* **Environment:**
  * `./python.sh` (the `tennis` Conda environment) for everything but the fits;
  * the fits use `./python_tabpfn_local.sh` through `src/eda/bet_timing/run_when_free.sh`, with TabPFN 9.1.0, torch 2.11.0+cu128, checkpoint `tabpfn-v3.5-20260909.safetensors` and an RTX 5090.
* **Repository:** HEAD `677a63f` (8 Oct 2026), with uncommitted work of this and other sessions.
* **Inputs** (SHA-256, first 16 characters), unchanged during the study:

| File | SHA-256 |
|---|---|
| `data/studies/predictability_diagnostic/stage0_matches.parquet` | `07bc2d34f6655fdb` |
| `data/studies/predictability_diagnostic/stage1_odds.parquet` | `4a802e173ea87284` |
| `data/studies/current_best_model/pinnacle_first_2026-10-09/model_frame.parquet` | `6996d41e67dd7ac5` |
| `data/studies/lean_review/arms/A2/model_inputs.json` | `8d79d876cbde15f4` |
| The candidate frame, `data/studies/indoor_fill/arm/model_frame.parquet` | `b3777d6ac4328818` |

**Commands, in order** (runtimes on this machine):

```
./python.sh -I src/eda/indoor_fill/snapshot.py                                      # 49 requests, ~4 min
./python.sh -m src.ingest.point_sources.wta --calendar-only --years 2013-2015,2017 --max-requests 16
./python.sh -m src.ingest.point_sources.wta --calendar-only --years 2010-2012 --max-requests 12
./python.sh src/eda/indoor_fill/crosscheck.py                                       # ~15 s
./python.sh src/eda/indoor_fill/live_check.py                                       # ~2 min
./python.sh src/eda/indoor_fill/arm.py --chain-check                                # ~2 min; rewrites arm/: not while fits run
./python.sh src/eda/indoor_fill/fits.py --check                                     # ~1.5 min, CPU
bash src/eda/bet_timing/run_when_free.sh src/eda/indoor_fill/fits.py --run          # 24 fits, ~36 min
./python.sh src/eda/indoor_fill/score.py                                            # ~2 min
./python.sh src/eda/current_best_model/compare.py --candidate data/studies/indoor_fill/arm
./python.sh -m pytest test/indoor_fill -q
```

* A rerun on later tables (after a Stage 0 or Stage 1 rebuild) changes the counts, not the method.
* The fits are deterministic, so `fits.py --run` on the same frame should reproduce the stored files bitwise. Delete them first, or run into another folder.

## 7. Evidence index (`data/studies/indoor_fill/`)

| File | What it holds |
|---|---|
| `snapshot.json`, `snapshot_rows.csv`, `snapshot.log` | The download: each workbook's receipt fields and its comparison with the dump; the rows the dump lacks |
| `crosscheck.json`, `crosscheck_events.csv` | Every model event: tennis-data's Court, the second source, the WTA edition matched and how, the rule's value and source; agreement by tour and season; the disagreements |
| `live_check.json`, `live_check.csv` | The live simulation by tour, season and source |
| `arm.json` | The candidate frame's checks, the sources' counts, the chain-builder check, the indoor share by tour and season |
| `arm/model_frame.parquet`, `arm/model_inputs.json` | The candidate (gitignored parquet; the list is A2's) |
| `check.json` | The jobs' equality with A2's, season by season |
| `arm/fits/*.npz`, `fits.log` | The 24 fits: close-fed (`td`) and opening-fed (`open`) predictions, with metadata (fingerprints, versions, timings) |
| `scores.csv`, `score_summary.json`, `score.log` | The harm check: every population and yardstick, the realisation slopes, the rule's outcome |
| `arm/vs_reference_2026-10-08/`, `compare.log` | `compare.py` against the frozen reference: the input check (`inputs.csv`, `inputs_by_season.csv`, `season_profile.csv`) and both stages |

Outside this folder:
* `data/raw/indoor_fill/tennis_data_couk/` (the 47 workbooks and `_receipts.jsonl`);
* `data/raw/point_sources/wta/calendar/` (the calendar pages; the adapter's receipts);
* `data/studies/official_point_feeds/wta_calendar_summary.json` (the last calendar run).

## 8. Corrections made after the first write-up

Found while writing this record and corrected in the README and the decision record:
* "Every 2026 event is matched to its edition by id" → 43 of 45; the Australian Open and Roland Garros match by name.
* "The rows without a link are long-standing venues" → three were not searched. Guadalajara hosted the Finals once (2021).
* "Each checked against the venue" → seven events by search, three from general knowledge.
* "Cluj-Napoca twice" in 2021 → the second Cluj-Napoca only (the first was outdoors).

## 9. Questions a reviewer could take up

1. Does a full chain build on the tables of 8 Oct give exactly `arm/model_frame.parquet`'s `in_indoor`? (`run_chain.py --setup --candidate` in its own sandbox, then compare.)
2. Sample 30 events where the two sources agree and check their venues: what is the error rate of the final input?
3. Is the WTA's `inOutdoor` the right concept for conditions of play, given roofs and covered courts? Should a roofed match count as indoor?
4. Is a harm check the right bar here, given § 5, point 3? Would the framework's other defaults (shrinkage with τ near 0.01) have changed the call?
5. Does the fill matter at the earlier prices the owner may bet at (24–48 hours out), which this test did not cover?
6. Were the Roland Garros box-score candidate (built in `tnr_sb`) and any lower-level-evidence build from `tnr_sys5` read with the indoor change in mind (§ 5, point 1)?

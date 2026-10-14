# Corrupt source rows confirmed by three independent reviewers are corrected at source

**Asked by the owner on 8 October 2026,** after the [input-data audit](../studies/input_data_audit/README.md): "find all the corrupt data that is UNDOUBTABLY corrupt where the fix is CLEAR. Have review agents confirm the logic so we have consensus that the problem is clear and the fix is unanimous. Execute it after." Recorded the same day by Claude, who ran the review and applied its result.

## Decision

1. **The rule.** A row is corrected only where all three independent reviewers of its group confirmed both points:
   * it is corrupt beyond reasonable doubt;
   * the fix is clear, unique and correct.

   All three had to name the same rows, the same operation and the same values. Everything else stays as it is.
   * **Who reviewed.** Six Opus 5.5 reviewers worked independently. One group took the box scores; the other took identities, ages, odds and speed records. Each group had three lenses:
     * recompute every claim from the raw files;
     * attack every claim, looking for another explanation;
     * check against independent records and simulate the fix.
   * **How they voted.** In round 1 each reviewer voted on the [candidate list](../../data/studies/input_data_audit/fixes/candidates.md). In round 2 they voted on rows that some of them found outside it.
   * **The record.** Votes and scope files are in `data/studies/input_data_audit/fixes/<reviewer>/`. `src/eda/input_data_audit/consensus.py` intersects them into [consensus.json](../../data/studies/input_data_audit/fixes/consensus.json) and the correction tables.
2. **What is corrected:**

   | Fix | Rows | The fault | The fix | Confirmed by |
   |---|---:|---|---|---|
   | F1, F1x, F1y | 1,196 matches | Serve points leave out double faults: 30 WTA tour events of 23 Feb – 24 Aug 2015, plus the Doha 2015 semi-final and final | Serve points + double faults, both players. 3 boxes Stage 0 dropped come back | Charted rows with double faults: serve points + double faults equal the chart in 141, serve points alone in 2 (chart errors). The definition test fails in no row afterwards |
   | F2, F2x | 78 matches | The winner's and the loser's box scores exchanged, 63 of them at WTA Abu Dhabi and Phillip Island 2021 | The nine counts exchanged back | The WTA's own statistics (equal on all 18 counts only once exchanged), the US Open and Wimbledon feeds, the ATP's key statistics, or the score |
   | F2y | 1 match | AO 2022 Paire–Monteiro: only the service-game counts exchanged | The two service-game counts exchanged back | AO ball tracking and SofaScore |
   | F3 | 35 matches | WTA Adelaide 2 2022 carries Adelaide 2021's box scores, on other players | 34 replaced by the WTA's own statistics of the match; 1 walkover blanked | The WTA's statistics equal Sackmann's on 99.7% of 12,354 clean 2021–22 player rows, and on the event's 4 genuine boxes |
   | F4, F4x | 18 matches | A box score copied from the same pair's other meeting (and two Düsseldorf 2012 rubbers) | Blanked | The box is impossible for this match's own score, or a chart or point-by-point record contradicts it |
   | F7 | 11 players | One player under two ids (9 women from June 2026; Marques, Tran) | The second id mapped to the established one | The WTA's own player ids; birth dates to the day |
   | F8b | 12 player rows | Tennis My Life's 2026 WTA ages written without their decimal point (2808 for 28.008) | The age from the birth date, which equals the decoded value | Sackmann's player file |
   | F9 | 182 player rows | ATP Prague and Todi Challengers (17 Aug 2020) aged at 16 March 2020, the ranking freeze | The age from the birth date, one decimal (Sackmann's convention) | Sackmann's player file; Tennis My Life's own ages |
   | F11 | 6 odds rows | The average (and in four rows the maximum) reversed against every individual book: Wimbledon 2016 F, Chennai 2013 SF, US Open 2010 SF, Roland Garros 2011 F, Adelaide 2 2022 R32, 's-Hertogenbosch 2025 F | The named books' two prices exchanged | Every book on the row; the maximum below every book's price, which a maximum cannot be |
   | F12 | 1 odds row | Nottingham 2017 F: tennis-data swapped the names; Konta carried Vekic's price | All four books' prices exchanged | Ranks, set scores and prices on the row are Vekic's |

3. **Where it is implemented.** `src/eda/input_data_audit/corrections.py` applies the tables in `data/studies/input_data_audit/fixes/`. Each row names its source file and row, guarded by the names, tournament and round (odds: names and date). A source that moves or rewrites a row stops the build instead of correcting the wrong match.
   * **`stage0_build.py`:**
     * applies `row_corrections.csv` right after the rows are read, after the Slam overrides. These are logged in the cleaning log as rules E1–E6;
     * applies `id_aliases.csv` after the repairs;
     * every build does this by default. `--no-corrections` builds without them; `--corrections-dir` takes other tables, into the live folder only with `--confirm-live-overrides`.
   * **`stage1_odds.py`** applies `odds_corrections.csv` right after the rows are read. It also gains `--out-dir` and `--no-corrections`.
   * **Tests:** `test/input_data_audit/test_corrections.py`.
4. **Dry run** (`src/eda/input_data_audit/fixes_dry_run.py`, [dry_run.json](../../data/studies/input_data_audit/fixes/dry_run.json)). It built Stage 0 twice into a scratch folder, with and without the corrections:
   * the live tables did not change;
   * no match changed outside the corrected ones;
   * every corrected match changed exactly as its table says;
   * the second ids are gone;
   * only the seven named odds rows changed.

5. **Applied at the coordinated rebuild of 8 Oct 2026, 18:53 UTC** (`src/eda/data_continuity/rebuild_stage0.py --expect <the dry run's corrected build>`; record: [rebuild.json](../../data/studies/data_continuity/rebuilds/2026-10-08T1853Z/rebuild.json)).
   * **Before it ran,** the two sessions busy at the time were asked. One confirmed that no job of its own read these tables; the other did not answer. No running job read them.
   * **Kept first:** every file it replaced, 384 MB with a SHA-256 manifest, in `rebuilds/2026-10-08T1853Z/replaced/`. `rebuild_stage0.py --restore 2026-10-08T1853Z` puts them back.
   * **Rebuilt, in order:**
     * Stage 0: equal to the dry run's corrected build, byte for byte;
     * its checks;
     * the closing odds;
     * the timeline;
     * the per-player, IOS and leak-proof inputs;
     * TrueSkill.
   * **It also brought Tennis My Life's results of this morning:** 73 more matches (873,364 → 873,437).
     * 36 Shanghai 2026 qualifying matches changed id, because Tennis My Life names the event "Shanghai Masters" in one file and "Shanghai" in another. Stage 0 now treats them as two events.
     * No link file referred to the old ids.
   * **Checked after it** (`src/eda/input_data_audit/verify_after.py`, [after_rebuild.json](../../data/studies/input_data_audit/fixes/after_rebuild.json)):

     | The audit's detector | Before | After |
     |---|---:|---:|
     | Matches that fit their score only with the boxes exchanged | 88 | 29 (the unconfirmed ones) |
     | WTA 2015 rows failing the double-fault definition test | 100 | 0 |
     | WTA 2015 window, second-serve points won | 51.9% | 44.8% |
     | Adelaide 2 2022 rows equal to an Adelaide 2021 box | 20 | 0 |
     | Players under a second id (the audit's rule) | 13 | 2 |
     | Ages of 100 or more | 12 | 0 |

## Not corrected

* **Rejected or excluded by all three reviewers:**
  * **Roland Garros 2025 from RG's own statistics (F5).** They count differently from Sackmann even where nothing is wrong: all nine counts agree in only about half of main-draw rows. The 6 Oct decision also deferred it.
  * **Roland Garros 2022–24 and the Paris Olympics (F6).** The fault shows only edition by edition, and no per-match record is held.
  * **Update, 9 Oct 2026 (facts since; the rejections stand as they were made):**
    * Per-match records are now held for every edition: RG's own statistics and point-by-point, and the Olympic results files.
    * In 2019–2021 RG's statistics equal Sackmann's rows on every count they share, apart from four boxes Sackmann exchanged. So the 2022–2025 differences are the fault, not a convention.
    * The fix went through this decision's three-reviewer rule as checklist item 6. Its corrections are candidates under the frozen-reference rule: [Roland Garros first-serve recount](../studies/rg_first_serve_recount/README.md).
  * **Ages that look impossible but are real (F10).** Gail Falkenberg, born 1947, played in her seventies.
  * **Court offsets and the speed filter's design (F17).**
* **Split votes**, left as they are:
  * three odds averages blanked as in-play prices (F13; 2 to 1);
  * copied speed blocks (F16; 1 to 2);
  * San Jose 2011 F (2 to 1; its books come from one collection step);
  * 30 of the 88 candidate exchanges;
  * same-pair copies whose direction the reviewers did not agree on.
* **Nine "exchanged" boxes found in round 1 are correct.** All three reviewers rejected them in round 2. Each is a match between two players with the same surname (the Pliskovas, the Kudermetovas, the Wangs and others). Linking by surname made the box look exchanged; by full name the WTA's statistics equal the box as recorded.
* **Noted by reviewers, not voted:**
  * four set scores at Abu Dhabi and Phillip Island 2021 that differ from the WTA's;
  * two players filed under an older player's id (Elizabeth Jones, Raul Sanchez).

## Serve-speed records: applied to the live feed

All three reviewers confirmed 130 serve-speed records as impossible: a first-serve average at or above the record's own fastest serve, or 240 km/h and more. They are listed in `speed_exclusions.csv`.

**Applied to the live speed feed at the owner's word, 8 Oct 2026.** Asked "Should I apply them to the live speed feed?", the owner answered "Yes apply them".
* **The study's frozen panel is unchanged.** It is a frozen input of the pre-registered serve-speed study, and its scorers refuse changed inputs.
* **The live feed reads a corrected copy instead** (`src/eda/serve_speed_tabpfn/live/live_panel.py`): `live/speed_panel_frozen_corrected.parquet`, built by `src/eda/input_data_audit/speed_live_panel.py`. It is read only while the frozen panel's SHA-256 equals the one it was built from.
* **What changed.** The study's own choice, rerun without the 130 records, gives each affected player-match its next valid record. Of the 107 player-matches, 77 take the Slam or Infosys point-by-point average and 30 are left without a usable value. The live run of 8 Oct was rerun.

## The model rebuilt on the corrected tables (8 Oct 2026)

**Run at the owner's word.** Asked whether to rebuild the model's inputs, refit and compare, the owner answered "Then run this".
* **How.** The whole input chain was rebuilt on the corrected tables in a sandbox copy of the repository, then refitted locally: seasons 2019–2026, seeds 0–3. The study is [model_rebuild](../studies/model_rebuild/README.md).
* **The result: a tie** (milli-log-loss per match, positive = the rebuilt model better):
  * both stages, both tours 2022–2026, with the corrected speed history: +0.03 [−0.13, +0.20];
  * men 2024–2026: −0.09 [−0.33, +0.14];
  * stage 1 at the price 24 hours out, 2025–2026: −0.26 [−0.56, +0.03];
  * none of the 29 model-against-model comparisons excludes 0.
* **Unchanged.** The current model's files are as they were. `model_frame.parquet` is still on the tables of 30 Sep.

## Decided since

* **The rebuilt model is the current best model,** as a template built on the day's tables, not as stored files. The owner decided this on 8 Oct 2026 ([decision](2026-10-08-current-best-model.md)).

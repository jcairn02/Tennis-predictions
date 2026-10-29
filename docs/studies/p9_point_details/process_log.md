# The P9 point details as new predictive statistics: process log

28 Oct 2026, 08:37–13:50 local · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code extension) · Session: `4ad0f090-214d-4b51-b18a-41ad8262b656` (one session; its context was summarised once, between about 09:57 and 13:36, and this log was re-read after it) · For a future reviewer · Report: [README.md](README.md)

## 1. The request

* **The owner's words, verbatim** (28 Oct 2026, the session's first message):
  > "24,997 of the 25,003 matches that have every point now carry the eight extra details per point, such as point duration and net approaches. Due to the P9 ATP infosys files
  >
  > IF AND ONLY IF, these were statistics not explored before properly for predictiveness (either from insufficient data, it not being relevant to the prodution model but now is, or we simply didnt have these stats before).
  > Do a deep dive with a team of agents to see if any of these extra details could be promising as a new predictive statistics for either men or women (or both).
  > The most important quality is orthogonality to the market information. Having it help the model predict better also helps."
* **How it was read:**
  * **A gate first, detail by detail.** Does the field carry information the project did not already hold? Was the statistic it names explored properly before? Each of the owner's three clauses is checked: insufficient data before; newly relevant to the production model; a statistic not held before.
  * **The deep dive runs only for what passes,** with a team of agents, as asked.
  * **"Orthogonality to the market information"** is read as information about the result that the closing price lacks: the statistic's gain over the close. How much of the statistic the price and the model's inputs already explain is reported beside it as a description. A statistic can be uncorrelated with the price and still useless (noise is orthogonal), so the description alone decides nothing.
  * **"Help the model"** is read as the gain over both stages of the current best model (CLAUDE.md: never the TabPFN fit alone).
  * **"Men or women":** P9 is the ATP's files, men only. Women have no P9 counterpart. Their analogues (the Slam feeds, the WTA's advanced statistics, the volunteer charts) are what the earlier studies read.
  * **Readings set aside:**
    * taking "eight extra details" as eight new statistics without checking the fields (the gate found most of them empty or duplicates);
    * re-opening the closed families wholesale (momentum, tempo, style rates): only where one of the owner's clauses applies;
    * a field-level reading that would drop rally length because the new shot counts repeat the older copy's rally counts. The owner's condition is about whether the statistic was explored properly, and the older P9 copy's rally counts were never read for prediction either.
  * **No question was put to the owner.** The condition is the owner's decision rule; applying it is the lead's job ("recommend, don't delegate").
* **The target** is declared in § 3, before any match result was read.

## 2. Starting point

* **Code:** commit `9228b26` (22 Oct 2026) with many uncommitted changes elsewhere in the tree. This study's code is new (`src/eda/p9_point_details/`); other studies' code is imported read-only.
* **Data** (all read-only):
  * P9's staged tables, `data/dump/points/infosys_atp_recent/` (restaged 28 Oct, 04:23 UTC): `points.parquet` 3,590,495 rows; `rally.parquet` 3,545,656; `matches.parquet` 25,115.
  * Stage 0, `data/studies/predictability_diagnostic/stage0_matches.parquet` (873,964 rows, written 21 Oct 06:48 local); the match clock, `data/studies/match_timing/timing.parquet` (873,964 rows, 21 Oct 06:51).
  * Below-tour prices, `data/dump/odds/tennisexplorer_lower/` (monthly files, 2019-02 and 2024-02 to 2026-10).
  * The live model: `template_2026-10-21b` (`data/studies/master_pipeline/selected_instance.json`, read 28 Oct).
* **Earlier looks at these statistics** (the gate's evidence, § 4 rows 2–3):
  * [Shot level](../shot_level/README.md), 2 Oct 2026: rally length, net play, endings, serve speed and placement, against the close and Elo on 2013–2026, 2025–26 included. Stage 3: the noisy statistics (quick points, long rallies, net points) pass only 15–34% of a player's true value into the pre-match feature, and edges up to 1–2 mLL could hide in them. Stage 0 names "the men's tour-level gap of April 2025 to June 2026, between SirGenkii's files and TDI's window".
  * [Point sequence](../point_sequence/README.md), 6 Oct 2026: momentum, streaks, leverage, tempo and within-match fade closed at full depth (19 million points); "shot-level rates … closed for winner markets", more data "no". 2025–26 untouched by its tests.
  * [Serve and return leads](../serve_return_leads/README.md): the within-match speed fade and fault speed "the ATP's per-point files would test … properly", rated low priority.
  * [Unpriced leads](../unpriced_leads/README.md): shot-level statistics "already priced".
  * [Feature universe](../feature_universe/README.md) U-200–U-215.
* **Environment:** `./python.sh` (the `tennis` Conda environment), Windows 11. No GPU is used by this study.
* **The idea and how it arose** (framework § 2): more of a kind of data already used, at greater depth, for a statistic whose earlier null its own study attributed partly to thin data. Kind (framework § 0): new feature, for the pool.

## 3. Plan

*As first written, 28 Oct 2026, 08:55 local, after the gate (rows 1–12) and before any match result was read.*

**Phase 0, the gate (done, rows 1–12).** Per detail: its fill, its equality with fields already held, its behaviour event by event; then the record of the statistic it names; then the owner's three clauses. The verdict is judgment call 1 (§ 6).

**Phase 1, round 1: three agents in parallel.** None reads the result of a match it scores.
1. **Builder.** A men's rally table for 2018–2026 under one convention, from P9 and the earlier sources. Linked to today's Stage 0 (match id, both players' ids, date, round order). Per player and match, the rally "atoms": points by rally-length band and their winner, on serve and on return; shots hit; net points where flagged. Per-player depth before and with P9; the split-half reliability of candidate rates.
2. **Ideas.** At most ten statistics built from rally length and net play. Each has a mechanism for why the 2025–26 close would misprice it, is distinct from the closed families, and comes with an exact definition and a declared direction. A literature scan.
3. **Harness.** The men's 2025–26 matches with a price:
   * the prices: the Pinnacle-first close at tour level; TennisExplorer's last pre-match price below it;
   * the live instance's out-of-sample forecasts, both stages;
   * the "new part" projection on the model's non-price inputs;
   * the scoring: z beyond the price, cross-fitted mLL with 4-week block intervals, P(better);
   * the resolution of each test;
   * placebo runs.

   No rally statistic is read.

**Stopping rule after Phase 1** (declared now). The pass for rally length rests on P9 raising men's per-player rally depth in 2025–26. If the builder finds that, on the priced matches, the median player-match's 52-week count of points with a known rally length is less than 1.5 times what the same matches had without P9, stop. The gate then fails for rally length too, and this is reported.

**Phase 2, pre-registration (lead).** From round 1's memos: at most eight statistics and one combined score, with definitions, directions, populations, the primary and the decision words. Frozen as `preregistration.md`, with its SHA-256, before any scoring. The builder then builds the registered features as of each match, and the timing probe is run.

**Phase 3, one scoring pass.**
* **Primary:** the combined score's gain beyond the closing price, on men's 2025–26 matches where both players meet the registered depth rule. Tour level and Challengers are pooled. Measured as z and cross-fitted mLL, with intervals over 4-week blocks.
* **Secondary:**
  * each statistic alone;
  * at tour level, the gain beyond both stages of the live instance (out-of-sample seasons 2025 and 2026);
  * the deepest quarter of history depth;
  * tour level and Challengers apart.
* **Words:** "better" or "worse" when the 95% interval clears 0, otherwise "unresolved" with P(better). Never "tie".

**Phase 4, red team** (one agent): re-derive the headline numbers and the gate's numbers with its own code; check the timing, the links and the multiplicity.

**Phase 5, the report:** an admission verdict per statistic for the feature universe, and the README for the owner.

## 4. Chronology

Local time (UTC−7). "Results" means any outcome-based score of any candidate. None has been read so far.

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| before 08:37 (no clock read) | Read `serve_speed_acquisition/README.md` § 9 (P9) | Learn what the eight details are | none | The eight are `firstServer`, `lastHitter`, `serveClassId`, `tm1Shot`, `tm2Shot`, `pointDuration`, `tm1AtNet`, `tm2AtNet`, plus `game_momentum_*` (§ 9.7) |
| before 08:37 | Read the feature universe; the shot-level README and Stage 3; the point-sequence README (summary, verdict table); grep of the unpriced-leads README; the memory "edge thesis" | The prior record of each statistic, for the gate | none (other studies' reported results, read as the gate's evidence) | § 2's list of earlier looks |
| before 08:37 | Inline profile of the new fields (`./python.sh -c`, not saved) | First look at what the fields hold | none | `lastHitter` empty; `serveClassId` 1/2/4; shot counts ≈ rally counts; `pointDuration` odd units, extremes ±86,400; net TRUE on 0.5% of points; momentum sums to 10 |
| before 08:37 | Inline checks by level and event (not saved) | Is `pointDuration` a duration anywhere? Where do net flags exist? | none | `pointDuration`: no link to the match clock, weak with rally length except at about a dozen events; net flags at 24 of 535 events, the same 24 as the rally files' `t1NetPoint`/`t2NetPoint` |
| before 08:37 | Inline: first server; shot/rally differences; momentum steps (not saved) | Duplicate or new? | none | First server = the first point's server; shot counts a recount; momentum +1 hold, +2 break |
| before 08:37 | Read `shot_level/stage0_sources.csv` (men, 2022–26); P9 matches with rally lengths by level | Depth gain for rally length | none | Before P9: men's rally length linked on about 2,075 (2025) and 3,556 (2026) source matches, overlapping. P9: 6,507 matches with rally lengths on at least half their points |
| before 08:37 | Inline: `pointDuration` of rally-ended against serve-ended points, by event | Second test of the duration field | none | Median event ratio 0.99 (no difference); 7 events above 2 |
| 08:37 | `date`; `git log -1`; the session id | Log header | none | Session `4ad0f090-…` (the scratchpad folder) |
| ~08:40 | Peer sessions `tennis-predictions-ad` and `-e4` claimed pipeline and ingest files; replied that this study writes none of them and named its own folders | Production integrity: claim shared files | none | Messages sent; no overlap |
| ~08:42 | Located the lower-level prices (`tennisexplorer_lower/`, monthly to 2026-10) and stored forecasts (`unpriced_leads/check_now/forecasts.parquet`; the live instance's `fits/`) | Can Challengers be scored, and against which model? | none | Challenger prices exist for 2025–26; the live instance holds per-season, per-seed fits |
| 08:47:32–08:47:49 | `./python.sh src/eda/p9_point_details/field_profile.py` | Make every gate number reproducible from one script | none | `data/studies/p9_point_details/field_profile.json`, `field_profile_events.csv` |
| ~08:49 | Inline: the momentum score's deviations from the hold/break rule (not saved) | Is it only a function of the score? | none | 16% of games deviate: every set's first game (it resets) and about 11% of others, in half-steps near level scores |
| ~08:50 | Inline: Court Vision columns | Can point duration be measured from the tracking files? | none | Positions and speeds per stroke; no stroke times seen |
| 08:55 | Gate verdict (judgment call 1); plan (§ 3) written | | none | This log |
| ~08:56 | Briefs written: [00_shared_context](briefs/00_shared_context.md), [01_builder](briefs/01_builder.md), [02_ideas](briefs/02_ideas.md), [03_harness](briefs/03_harness.md) | Round 1 | none | `briefs/` |
| 08:56 | Round 1 launched: builder, ideas, harness (three background agents, general-purpose type) | Phase 1 | none | Their memos go to `team/` |
| 08:57 | Added a dated note under the "eight extra details" claim in `serve_speed_acquisition/README.md` § 9.7, pointing here | The claim overstated what the fields hold; it shaped this request | none | One note, by addition |
| (while round 1 ran) | Peer `tennis-predictions-ad` released its claims. It had added one row to `input_data_audit/fixes/id_aliases.csv` (Mensik, `atp:210084` → `atp:210150`); the shared Stage 0 was not rebuilt | Inputs the builder reads | none | No action |
| ~09:36 | **The builder reported** ([memo](team/builder.md)). Stopping-rule number **1.069**: the median, over 35,812 player-matches (men's tour-level and Challenger main draws, 2025-01-01 to 2026-10-18), of the 52-week count of points with a known rally length with P9 ÷ without P9. Ratio of medians 1.45; against the shot-level study's 2 Oct tables, 1.68. P9's "rally length known" flag marks aces, double faults and junk 0/1 counts outside tracked matches: real rally lengths exist in 4,330 of its 25,004 matches | Phase 1 | none (depth and reliability only; no match result) | `build/depth.json`, `depth.csv`, `depth_rows.parquet`, `convention.json`, `reliability.csv`, `probe.json` and the rest of `build/` |
| ~09:38 | **Lead's re-check 1** (inline, not saved): P9 points flagged as having a known rally length, by level group. Challengers: counts 0 (54%), 1 (24%), negative junk and six-figure values; winners' median count 1. Tour level: a plausible spread | Is the builder's decisive claim right? | none | Confirms it. A second test I tried (≥ 90% of rally-ended points with a count ≥ 2) was wrong: a return error has a count of 1 under the convention. Discarded |
| ~09:39 | **Lead's re-check 2** (inline): recomputed the headline from `depth_rows.parquet` with my own code | Is the aggregation right? | none | 1.069 median of ratios and 1.452 ratio of medians, as reported. By half-year: 250s to Finals 1.00 / 1.32 / 2.18 / 1.81; Slams 1.06 / 1.28 / 2.10 / 1.76; Challengers 1.00 / 1.00 / 1.40 / 1.15 (2025H1 … 2026H2). The per-player counts themselves are the builder's, not re-derived |
| 09:40 | Messages to the ideas and harness agents: the study stops; wrap up (texts in the appendix) | Stopping rule | none | – |
| 09:42 | Stop decision recorded (judgment call 2); gate corrections recorded (corrections to judgment call 1) | | none | This log |
| ~09:45 | **The harness agent reported** ([memo](team/harness.md)). 25,807 men's matches (1 Jan 2025 – 18 Oct 2026), 25,542 priced: Challengers through TennisExplorer, linked 99.4%. The live model's both-stage out-of-sample forecasts on all 7,266 priced tour-level matches, from stored fits. Placebos calibrated (z SD 1.00–1.05). Resolution of one standardised feature by the z test: about 0.15 mLL pooled, 0.22 Challengers, 0.53 tour level, 0.76 tour main draw | Phase 1 | **The bases' numbers only:** model (both stages) against the raw close on the tour main draw, +2.65 mLL [+1.19, +4.31]; the price's slope per cell. No candidate statistic | `harness/`, `src/eda/p9_point_details/harness*.py`, 13 tests |
| 09:46 | **Found: the harness's window crosses the sealed matches.** Edge anatomy § 3 kept matches from 29 Jul 2026 "sealed for a future untouched test" of the model's edge. My brief set the window to 18 Oct without checking. The harness's pooled bases include that period, and its memo gives two pooled figures (to July and to 18 Oct) from which a rough figure for the sealed period can be back-calculated | Seal discipline | The two pooled figures. The lead made a rough mental back-calculation before deciding not to pursue it; no figure is written anywhere | Note added to the harness memo; judgment call 3 |
| 09:50 | Correction to judgment call 2 (resolution) | The harness's resolution table arrived | The resolution table (placebos and planted signals only) | This log |
| ~09:55 | Told the owner in chat that a Challenger test would resolve "roughly 0.3 mLL" | Status update | as above | Chat only; corrected at 09:57 |
| 09:57 | Inline count (not saved): main draws outside the seal where both players have ≥ 300 rally points (`build/depth_rows.parquet`). Context added to judgment call 3; correction to the correction of judgment call 2 | My claim that Challenger rally history sits mostly in the sealed period needed checking | none new (depth counts only) | Challengers 3,655 of 11,232; 250s to Finals 3,362 of 3,471; Slams 857 of 882; about 0.5 mLL |
| 09:57–13:36 | Waited for the ideas agent. The session's context was summarised in this interval; this log was re-read afterwards | – | – | – |
| 13:36 | **The ideas agent reported** ([memo](team/ideas.md), [csv](team/ideas.csv)). Eight ideas; the three to register (R1 serve first-strike change, R2 return-neutralisation change, R3 long-rally luck, combined as z(R1) + z(R2) − z(R3)); none resolvable now (R1–R3 on roughly 1,500–2,000 tour matches, inferred; a speed-sized effect would read about z 1.8). Literature: 14 sources. Its own coverage script agrees with the builder (real rally counts on 99% of 1000s main draws, 44–49% of 250s and 500s, 6–7% of Challengers, under a looser criterion) | Phase 1 | none (no statistic related to results; checked in its process notes) | `team/ideas.md`, `team/ideas.csv`, `src/eda/p9_point_details/ideas_coverage.py` |
| 13:37 | Extracted the three launch prompts and the two wrap-up messages from the session transcript (`./python.sh` reading the transcript's JSON lines) | Verbatim record for the appendix | – | Appendix. **Correction:** the wrap-up messages were sent at 09:41:06 and 09:41:08 local (transcript timestamps), not 09:40 as the row above says |
| 13:38 | Read `harness.py`'s command line: no date option. The instruction in judgment call 3 ("pass a date filter") could not be followed from the command line, and masking a feature with NaN still lets the "indicator" readings fit every row's result | Make the harness safe to reuse | – | – |
| 13:39–13:42 | Added `--last-date` and `harness.window()`, a note when a window reaches 29 Jul 2026, and a refusal with `--bases-report` (judgment call 4); two tests. `pytest test/p9_point_details`: 21 passed. One end-to-end run on a random column (`--populations tour_main --bases price --no-new-part --last-date 2026-07-28`, scratchpad files `placebo_lastdate*.`): 4,335 matches, z +1.54, unresolved; no note. `--orientation` without the option printed the note; `--bases-report --last-date` was refused. The note's "§" printed garbled in Git Bash, so it now says "section"; 15 of 15 harness tests pass | Judgment call 4 | A random column's reading, on matches to 28 Jul only | `harness.py`, `test_harness.py`; a note in the harness memo |
| 13:43 | Recomputed the stopping-rule number on priced matches only (`depth_rows.parquet` joined to the harness population's `priced` flag; no result read) | The rule says "on the priced matches"; the builder's open problem 2 | none | 35,660 player-matches: median of ratios **1.070**, ratio of medians **1.451** (1,100 / 758); the 152 rows outside the priced population: 1.000 / 1.140. The stop stands |
| 13:44 | Checked two report figures: the last-hitter count (3,589,532 = `points_with_newer_copy` in `field_profile.json`; 0 non-empty) and edge anatomy's men's +2.83 (its scoreboard row; an earlier instance, so the report's wording was corrected) | Report accuracy | – | – |
| 13:44–13:50 | Wrote the [README](README.md); finished this log; added the study's row to the studies index | Phase 5 | – | – |
| 13:48 | Re-read my 08:57 note in the P9 report (§ 9.7). It called the shot counts a repeat, and the report nowhere says that the "rally length known" flag is junk outside tracked matches. Added both, by addition, with a link to the builder's memo | The note was written before the builder's findings | – | `serve_speed_acquisition/README.md` § 9.7 |

## 5. Sources

* **The repository's own reports and tables** (§ 2), read 28 Oct 2026.
* **The ideas agent's literature scan:** 14 sources, all accessed 28 Oct 2026, each marked as read in full, from its abstract, or from a search snippet ([ideas memo § 6](team/ideas.md#6-literature-all-accessed-28-oct-2026)). No claim in the README rests on a snippet-only source. Unread: the SUU working paper "One more shot" (2018), whose PDF text could not be extracted; Kovalchik (2016), seen as a record only.
* **No web source was used by the lead.**

## 6. Judgment calls and deviations

1. **The gate (28 Oct, 08:55; before any result).** Evidence: `field_profile.json` (rows 1–12).

   | Detail | What it holds (observed) | New information? | Explored before? | Verdict |
   |---|---|---|---|---|
   | Who served first (`firstServer`) | the server of the match's first point, on 24,998 of 24,998 matches | no | not a statistic of skill | **fails** |
   | Last hitter (`lastHitter`) | empty on every one of 3,589,532 points | no | – | **fails** (no data) |
   | Serve class (`serveClassId`) | 1 = ace, 2 = in play, 4 = double fault: agrees with the ending field on 99.99% | no | aces and double faults are model inputs | **fails** |
   | Shot counts (`tm1Shot`, `tm2Shot`) | the older copy's rally counts, recounted: equal on 95.6% of points; 23,382 points (0.65%) filled where the old count was 0 | the field, no; **the statistic it names, rally length, at P9's depth: never read** | rally length: shot level, on data its own Stage 3 called too thin for the noisy rates; men's tour-level gap April 2025–June 2026 | **passes, men only** (the owner's "insufficient data"), subject to § 3's stopping rule |
   | Point duration (`pointDuration`) | behaves as a duration at 17 of 535 events (768 matches); elsewhere rally-ended points get the value aces get (median event ratio 0.99), no link to the match clock (median ρ −0.004) | a statistic not held before, but not measured by this field outside 17 events | ball-in-play time never tested; tempo between points closed (point sequence) | **fails** (too little real data to explore) |
   | Net approaches (`tm1AtNet`, `tm2AtNet`) | flagged at 24 of 535 events (1,133 matches), the same 24 as the rally files' net-point flags held since 24 Oct | no (a duplicate) | net play: shot level, data-limited | **fails as a new field**; net play rides along as a secondary of the rally deep dive where flagged |
   | Momentum score per game | a running tally, +1 per hold and +2 per break, reset each set, with half-steps near level scores (84% of games follow the plain rule; the rest are set starts and near-level games) | no (a function of the score) | momentum and streaks closed at full depth (point sequence) | **fails** |

   * **Options:** stop at the gate (every field fails as a field); or run the deep dive on the one statistic the owner's "insufficient data" clause covers.
   * **Choice:** the deep dive, narrowed to men's rally length, with net play where flagged. The owner's condition is about statistics explored properly, and the shot-level study itself named thin data and the April 2025–June 2026 men's gap that P9 fills.
   * **What the other branch changes:** no team; a report of the gate alone.
   * The "newly relevant to the production model" clause was considered. Qualifying of the 250s and above is bet since 22 Oct, and P9 covers tour qualifying, but that makes no statistic newly relevant: the earlier tests' main-draw population is the same model. It decides nothing here.
   * **Corrections, added 09:42 after the builder's report (no result read):**
     * **The gate's rally coverage was wrong.** "Rally length known on 38.7% of points … 25–35% at Challengers" read P9's `rallyLengthMissing` flag as a measurement. Outside tracked matches the flag marks aces, double faults and junk counts of 0 or 1. Real rally lengths exist in 4,330 of P9's 25,004 matches: 1000s main draws 1,402 of 1,422, 250s main draws 707 of 1,479, 500s main draws 397 of 906, Finals 15 of 15, Challenger main draws 566 of 12,494 (mostly 2026). The same error sits in the gate's estimate that P9 roughly doubles men's rally data (process log row "before 08:37", 6,507 matches).
     * **The new shot counts are worse than a duplicate.** `tm1Shot`/`tm2Shot` add the erring shot on only about half the error points: they equal the rally files' category on 71% of errors, against 99% for the old counts. Their 23,382 "fills" are 22,031 double faults counted as 1 and about 1,000 others. The builder did not use them.
     * The pass for rally length stood, provisionally, on the stopping rule. Judgment call 2 applies it.
   * **Note, added 13:46.** The per-level counts in the first correction above are the builder's first inline look. The README quotes its final table, `convention.json` A4 (the gate with each event's counting rule): 1000s main 1,398 of 1,427, 500s main 394 of 913, 250s main 708 of 1,548, Finals 15 of 15, Challenger main 566 of 12,494, and qualifying 458, 159, 319 and 313. These sum to 4,330. The two differ by a few matches per level and change nothing.
2. **The stop (09:42; after the builder's depth numbers, before any match result).**
   * **The rule** (§ 3, written 08:55): stop if "the median player-match's 52-week count of points with a known rally length is less than 1.5 times what the same matches had without P9".
   * **Its wording allows two readings.** One is the median of each player's ratio, which is what the builder's brief asked for as "the median ratio". The other, read literally, is the ratio of the two medians. The baseline is "without P9", meaning every other source held today: the builder's brief said "with every source, and without P9".
   * **The numbers:**

     | Reading | Against today's other sources | Against the shot-level study's 2 Oct tables |
     |---|---:|---:|
     | Median of each player's ratio | **1.069** | 1.191 |
     | Ratio of the medians | **1.452** | 1.679 |
     | Tour main draws only, median of ratios | 1.39 | 1.56 |
     | Tour main draws only, ratio of medians | 1.56 | – |

   * **Choice: stop.** Both readings fall below 1.5 on the rule's population, against the rule's baseline. Only two corners cross it: the 2 Oct baseline, which measures what has arrived since the shot-level study rather than what P9 adds, and tour level alone, which is not the rule's population. The rule's population is priced matches, and Challengers are priced through TennisExplorer.
   * **The decision is close under one reading (1.45).** It was taken after the depth numbers were seen, which a reviewer should weigh. Two further readings, not outcomes, point the same way:
     * **Reliability barely moves.** In 2026, with P9 against without, who wins the points of each rally length scores 0.10–0.38 against 0.08–0.39, and net points won 0.105 against 0.110 (`build/reliability.csv`). Those are the noisy statistics the shot-level study said thin data held back.
     * **Tour-level players were not short of depth to begin with.** Their median 52-week count without P9 is about 3,400 points (Slam feeds, charts, the AO and RG Infosys files, SirGenkii). That already sits in the shot-level study's deepest quarter (`build/depth.csv`).
   * **The other branch:** register up to eight rally statistics and score them once on 2025–26. Its likely reading would be "unresolved", on statistics whose measurement P9 barely improves.
   * **What would reopen it:** real rally lengths at the Challengers (P9 has them for 566 main-draw matches), or a confirmation season (2027) for a tour-level statistic.
   * **Correction, added 09:50 after the harness's resolution table (no candidate result).** "Its likely reading would be 'unresolved'" was an assumption made before the harness existed. The z test resolves about 0.15 mLL pooled, 0.5 at tour level and 0.8 on the tour main draw for one fully covered feature (`harness/resolution.csv`).
     * A rally statistic is not fully covered, though. Where both players have at least 300 points of rally history: tour main draws 97%, Challenger main draws 39% (`build/depth.csv`).
     * Most Challenger rally history comes from TDI's capture of June–September 2026, which largely falls in the sealed period (judgment call 3).
     * So, with sealed matches left out, such a test would rest mostly on tour-level matches. That resolution is near what the earlier studies already had on tour matches, so the stop stands. The reason is now the depth rule and the reliability readings, not resolution.
     * **The resolution itself is news for other questions,** and the README reports it.
3. **The sealed matches (09:46; a failure of the lead's brief).**
   * **What happened:** edge anatomy (§ 3) kept matches played since 29 Jul 2026 "sealed for a future untouched test" of the model's edge. The unpriced-leads check registered its Look B on the same period. The harness brief set the window to 2026-10-18 without checking either. The harness read the price's and the model's log loss on the whole window, sealed matches included, and published pooled figures to July and to 18 Oct.
   * **What it touched:**
     * the model's edge on the sealed period can be roughly back-calculated from the two pooled figures;
     * the placebo, planted-signal and resolution runs used the results too, but they carry no information about any statistic or the model.
   * **What it did not touch:**
     * the unpriced-leads Look B statistic, the five-pattern score, which was never computed here;
     * any candidate statistic.
   * **Effect on this study:** none. The stop (09:42) came before the harness reported (about 09:45).
   * **What was done:**
     * a note beside the pooled figures in the harness memo;
     * this entry;
     * no figure for the sealed period was computed or written. The lead made a rough mental back-calculation on first reading the two figures, then stopped. Its value is not recorded, so as not to spread a sealed-period estimate.
   * **Left to the owner:** whether the sealed period still counts as untouched for the model's edge; if not, a new seal date.
   * **For later work with this harness:** pass a date filter that leaves out matches from 29 Jul 2026.
   * **Context, added 09:57.** The period was not untouched before this study. The owner-approved unpriced-leads check (13 Oct, `unpriced_leads/check_now_rules.md`) read every match from 2025 to 23 Sep 2026, with the model's both-stage forecast as its base. That includes 29 Jul – 23 Sep. What is new here is a published model-against-close figure on the period, through 18 Oct.
   * **Correction to the correction of judgment call 2, added 09:57.** The sentence "Most Challenger rally history comes from TDI's capture of June–September 2026, which largely falls in the sealed period" is wrong (`build/depth_rows.parquet`, main draws, both players with at least 300 rally points):

     | Level | Outside the sealed period | Inside it |
     |---|---:|---:|
     | Challengers | 3,655 of 11,232 (32.5%) | 1,453 of 1,750 |
     | 250s to Finals | 3,362 of 3,471 | – |
     | Slams | 857 of 882 | – |

     * That makes about 7,900 covered main-draw matches outside the seal. A z test on them would resolve roughly 0.5 mLL: the harness's pooled 0.15 scaled by 25,542 / 7,900, about the tour level's own 0.53.
     * The stop stands on the depth rule and the reliability readings. The Challenger part would, however, be a population on which no rally statistic has been tested. The README reports that as an option, not as part of this request.
     * (In chat at about 09:55, the lead had said "roughly 0.3 mLL"; 0.5 is the computed scaling.)
   * **Addition to judgment call 2, 13:43: the rule's population exactly.** The rule says "on the priced matches"; the builder counted every completed or retired main-draw match (its open problem 2). On the 35,660 player-matches of priced matches (the harness population's `priced` flag): median of ratios 1.070, ratio of medians 1.451. The stop stands as decided.
4. **A date option added to the harness after the study stopped (13:39; the lead's change to an agent's code).**
   * **Why:** judgment call 3 told later users to "pass a date filter", but the command line had none. Masking the feature with NaN is no substitute: the "indicator" readings still fit every row's result.
   * **What:** `--last-date YYYY-MM-DD` (function `window`), a note on stderr whenever a window reaches 29 Jul 2026, and a refusal with `--bases-report` (which rewrites `bases.json` for the whole window). The default is unchanged: no date filter, so the memo's documented numbers still describe the default run.
   * **Option set aside:** a default of 28 Jul 2026. It would protect the seal by default, but it changes what the documented numbers describe, and the owner may move the seal. It is the owner's call (judgment call 5).
   * **Checks:** two new tests; 21 of 21 pass; one end-to-end run on a random column, and the refusal and the note seen to fire.
5. **The recommendation on the seal, and a side finding read over sealed weeks (13:44).**
   * **The recommendation: count the untouched test of the model's edge from 19 Oct 2026.** The owner decides.
     * The five-pattern adjustment, now in the live model, was adopted on the owner's check of 13 Oct, which read every match to 23 Sep 2026 with the model as its base.
     * This study published a pooled model-against-close figure to 18 Oct.
     * The cost: about 600 men's main-draw matches (4,937 − 4,335 in the harness population), plus the women's.
     * The other option was weighed: keep 29 Jul, since no decision was made from this figure. It rests on nobody back-calculating.
     * Either way, the README asks that the ruling be recorded in `docs/decisions/`. The harness agent found no central record of the seal (no `seal.json`; the clean-holdout rebuild is a proposal), which is how the brief missed it.
   * **The side finding on newer players** (README § 5, item 4) comes from the harness's nuisance columns, pooled over the whole window, sealed weeks included.
     * It is reported because it is already in the harness memo, and it echoes U-330, a lead already in the pool.
     * Its sealed share was not separated. It is not one of the statistics registered for the sealed matches (the serve-and-return leads' lock-in; the five-pattern score), though it is related in spirit to the five-pattern score's group 4 ("status over-priced").
     * A reviewer may judge that it should have stayed in the memo only.

## 7. Claims and their evidence

| README claim | Evidence | Computed by; checked by |
|---|---|---|
| Who served first = the first point's server, 24,998 of 24,998 matches | `field_profile.json` (`firstServer`) | lead's script |
| Last hitter empty on all 3,589,532 points that carry the newer fields | `field_profile.json` (`lastHitter`, `points_with_newer_copy`) | lead's script; checked again 13:44 |
| Serve class agrees with the point's ending on 99.99% | `field_profile.json` (`serveClassId`) | lead's script |
| Shot counts equal the older counts on 95.6% of points; 71% against 99% agreement on errors | `field_profile.json` (`shot_counts`); `build/convention.json` A2 | lead; the builder independently, with its own code |
| Point duration a duration at 17 of 535 events (768 matches); median ratio 0.99; no link to the clock | `field_profile.json` (`pointDuration`), `field_profile_events.csv` | lead's script; no second agent |
| Net flags at the same 24 events (1,133 matches) as the rally files | `field_profile.json` (`net`) | lead's script; the builder's `net_cov` agrees on the 24 events |
| Momentum is a tally of holds and breaks | `field_profile.json` (`momentum`); row ~08:49 | lead |
| Real rally lengths in 4,330 of 25,004 P9 matches | `build/convention.json` A4 | builder; the lead's re-check 1 (09:38) confirmed the junk flag at Challengers |
| Stopping-rule number 1.07 (1.45); tour main 1.39 (1.56); Challenger main 1.00 (1.41) | `build/depth.json`, `depth.csv`, `depth_rows.parquet` | builder; the lead recomputed the headline (09:39) and the priced version (13:43) |
| Reliability 0.10–0.38 against 0.08–0.39; net points won 0.105 against 0.110 | `build/reliability.csv` | builder; not re-derived |
| The scoring tool: 25,807 matches, 25,542 priced, Challenger link 99.4%, model on 7,266 | `harness/population_facts.json` | harness agent; its own checks; not re-derived by the lead |
| Calibration: z spread 1.00–1.05; resolution 0.15 / 0.22 / 0.53 / 0.76 / 1.65 mLL | `harness/null_check.csv`, `resolution.csv` | harness agent; 13 (now 15) tests; not re-derived |
| Price slopes 1.08, 1.19, 1.16, 0.99 | `harness/bases.json` | harness agent |
| No men's Challenger qualifying after June 2026 in the shared Stage 0 | harness memo § 2; builder memo, link failures | both agents, independently |
| Roland Garros 2026 files count the erring shot | `build/convention.json` (`event_rules`) | builder |
| Newer players under-rated: z +3.31 pooled, +2.18 tour, +1.16 beyond the model | harness memo, placebo section (`placebos.csv.gz`) | harness agent |
| The eight ideas, their priors and coverage | `team/ideas.md`, `ideas.csv` | ideas agent; priors subjective, the 1,500–2,000 not counted |
| Outside the seal: 3,655 of 11,232 Challenger, 3,362 of 3,471 250s–Finals, 857 of 882 Slam main draws covered; about 0.5 mLL | `build/depth_rows.parquet`, inline count at 09:57 (not saved) | lead |
| About 600 men's main-draw matches from 29 Jul to 18 Oct | harness population: 4,937 tour main priced, 4,335 to 28 Jul (row 13:39–13:42) | lead |

## 8. Weak points

* **The stop came after the depth numbers were seen** (judgment call 2). The rule's wording allowed two readings. One of them, the ratio of the medians, gives 1.45, near the bar of 1.5. A reviewer who reads the rule that way, with the 2 Oct baseline (1.68), would have continued.
* **Depth counts points, not information.** P9 does double tour-level data in 2026's first half (2.1–2.2 times). A 2026-only tour test is the strongest case against the stop. It would rest on about 2,300 tour main-draw matches of 2026, fewer outside the seal. That resolves about 1.5–2 mLL for a fully covered feature, against plausible effects of a fraction of 1.
* **Four of the gate's field verdicts rest on the lead's script alone:** who served first, serve class, point duration and momentum. Only the shot counts and the flag were re-derived by another agent. Each verdict is a large-margin reading (100%, 99.99%, a ratio of 0.99), so a small error would not flip it.
* **No red team ran.** Phase 4 was planned for the scored results, and nothing was scored. The harness's numbers are its own, backed by its tests and its placebo runs.
* **The seal lapse** (judgment call 3). The harness's figures to 18 Oct include the sealed weeks. No sealed-period figure was computed or written. The lead made one rough mental estimate.
* **Women were not examined.** P9 holds no women's matches. No women's source with these details was searched for, because the request was about P9's details.
* **The "newly relevant to the production model" clause** was weighed in one paragraph (judgment call 1). Betting qualifying since 22 Oct changes the population, not the statistic.
* **Where a flaw would hide:**
  * in the builder's match gate (90% of points with a valid rally count). If it wrongly dropped real Challenger tracking, the depth would be understated. Against it: the lead saw the Challenger counts (0 on 54%, 1 on 24%), and gate 0.5 gives 1.12;
  * in the without-P9 arm, which includes sources added after the shot-level study. Against the 2 Oct tables the median ratio is 1.19, still below 1.5.

## 9. Reviewer checklist

* [ ] Re-run `field_profile.py` and compare it with judgment call 1's table.
* [ ] Open five Challenger matches of P9 flagged "rally length known" and look at the counts.
* [ ] Recompute 1.069 / 1.452 (all) and 1.070 / 1.451 (priced) from `build/depth_rows.parquet` and the harness population.
* [ ] Decide which reading of the stopping rule was meant, and whether 1.45 against 1.5 should have stopped the study.
* [ ] Re-run the harness tests and its null check (`--null-check 2000`). Confirm the z spread of 1.00–1.05.
* [ ] Confirm that no rally statistic was joined to a match result: no output under `build/` or `harness/` holds both. The builder used point winners inside matches only as raw material and for its probe.
* [ ] Read judgment calls 3 and 5. Weigh the disclosure and the recommendation on the seal.
* [ ] Check the README's side findings against the memos.

## 10. Reproduction

From the repository root, in Git Bash:

```
./python.sh src/eda/p9_point_details/field_profile.py                         # the gate's numbers, ~20 s
./python.sh src/eda/p9_point_details/build_link.py                            # then build_points, build_atoms,
                                                                              # build_depth, build_depth_checks,
                                                                              # build_convention, build_reliability,
                                                                              # build_probe (~10 min in all)
./python.sh src/eda/p9_point_details/harness_population.py                    # ~65 s
./python.sh src/eda/p9_point_details/harness.py --bases-report                # under a minute; reads the sealed weeks
./python.sh src/eda/p9_point_details/harness_calibrate.py --workers 4         # ~17 min
./python.sh src/eda/p9_point_details/harness_calibrate.py --null-check 2000 --workers 4
./python.sh src/eda/p9_point_details/ideas_coverage.py                        # prints only, ~5 s
./python.sh -m pytest test/p9_point_details -q                                # 21 tests
```

The inputs move: P9's staging (restaged 28 Oct, 04:23 UTC), the shared Stage 0 and the match clock (21 Oct), and TennisExplorer's staging (daily). Their hashes and dates are in `population_facts.json` and the builder's reports. A rebuild on later tables gives slightly different numbers.

## Appendix: briefs, launch prompts and messages

* **The briefs**, saved verbatim before launch: [00 shared context](briefs/00_shared_context.md), [01 builder](briefs/01_builder.md), [02 ideas](briefs/02_ideas.md), [03 harness](briefs/03_harness.md). **The memos:** [team/](team/).
* **The launch prompts, verbatim** (Agent tool, type general-purpose, the session's model; 08:56:13, 08:56:18 and 08:56:22 local):
  * Builder, "Builder: rally data and depth":
    > You are the builder of the P9 point-details study in the Tennis-predictions repository (C:\Users\zerom\Documents\Tennis-predictions; run Python only through ./python.sh from the repository root in Git Bash).
    >
    > Your brief is saved verbatim in docs/studies/p9_point_details/briefs/01_builder.md. Read it and the shared context it points to (docs/studies/p9_point_details/briefs/00_shared_context.md) first, then follow the brief exactly: its goal, its task order, its rules on outcomes, where you may write, your memo, and your final message.
    >
    > The single most important output is task 4's number. Take the median ratio of each player's 52-week count of points with a known rally length, with P9 against without P9, on men's 2025–26 tour-level main draws and Challenger main draws. The study stops if it is below 1.5. Get that number done and checked before spending time on reliability.
    >
    > The machine is shared with other Claude sessions that are editing pipeline and ingest files today: keep to your own paths, use at most 4 worker processes, and leave nothing running when you finish.
  * Ideas, "Ideas: rally statistics and mechanisms":
    > You are the ideas agent of the P9 point-details study in the Tennis-predictions repository (C:\Users\zerom\Documents\Tennis-predictions; if you run any Python, use ./python.sh from the repository root in Git Bash).
    >
    > Your brief is saved verbatim in docs/studies/p9_point_details/briefs/02_ideas.md. Read it and the shared context it points to (docs/studies/p9_point_details/briefs/00_shared_context.md) first, then follow the brief exactly: read the earlier studies' closures before proposing anything, propose at most ten men's pre-match statistics from rally length (and net play where flagged), each with a definition, encoding, declared direction, mechanism, why it is not already closed, state or trait, coverage, how it could be wrong, and literature with URLs and access dates. Rank them and name the three you would register.
    >
    > You must not relate any statistic to match results. Write only docs/studies/p9_point_details/team/ideas.md, team/ideas.csv and, if needed, scratch code under src/eda/p9_point_details/ideas_*.py. The WebSearch and WebFetch tools are deferred: load them with ToolSearch ("select:WebSearch,WebFetch") before your first search.
  * Harness, "Harness: market and model scoring":
    > You are the harness agent of the P9 point-details study in the Tennis-predictions repository (C:\Users\zerom\Documents\Tennis-predictions; run Python only through ./python.sh from the repository root in Git Bash).
    >
    > Your brief is saved verbatim in docs/studies/p9_point_details/briefs/03_harness.md. Read it and the shared context it points to (docs/studies/p9_point_details/briefs/00_shared_context.md) first, then follow the brief exactly. Build the population of men's 2025-01-01 to 2026-10-18 matches with prices: the Pinnacle-first close at tour level, and TennisExplorer's last pre-match price for Challengers and qualifying, linked to Stage 0. Add the live instance's out-of-sample forecasts for both stages, from stored fits only, with no TabPFN fit and no GPU. Then write the scoring functions (symmetric, z clustered by week, cross-fitted mLL with 4-week block intervals and P(better), the new part, missing values), the placebo calibration, a planted-signal check and the resolution table.
    >
    > You never open the P9 tables or the study's build folder, and you score no real candidate feature: report only the bases' and placebos' numbers. Write only where the brief allows. The machine is shared with other Claude sessions editing pipeline files today: at most 4 worker processes, and nothing left running when you finish.
* **The wrap-up messages, verbatim** (SendMessage; 09:41:06 and 09:41:08 local):
  * To the ideas agent:
    > Lead here: the study stops at its declared depth rule, so nothing will be pre-registered or scored this round. The builder found that P9 raises the median player-match's 52-week rally-length history only 1.07 times (tour-level main draws 1.39). The reason is that P9's "rally length known" flag is junk outside tracked matches. Real rally lengths exist in only 4,330 of its 25,004 matches: nearly all 1000s, about half of the 250s and 500s, and 566 Challenger main draws, mostly 2026. Real net flags are at 24 events. Please wrap up now: finish team/ideas.md and team/ideas.csv with the ideas you have, with no new searches. Add to each idea its realistic coverage given these facts, and say which (if any) would still be testable at tour level. Then stop, and keep your final message short.
  * To the harness agent:
    > Lead here: the study stops at its declared depth rule (the builder's measure of what P9 adds to rally-length history is 1.07, against the threshold of 1.5), so no candidate will be scored this round. Please finish only the parts that make your harness reusable for a later men's 2025–26 feature study: the population with its prices and the live model's both-stage forecasts, the scoring functions, the placebo calibration, and the resolution table. Skip anything optional you have not started; for the planted signal, one gain size is enough. Write team/harness.md, then stop, and keep your final message short.
* **The builder** had already finished (about 09:36) and received no wrap-up message.
* **Peer messages** (other Claude sessions on the machine, not the owner): summarised in § 4 (rows ~08:40 and "while round 1 ran"). No request from them changed this study.

## Addendum, 29 Oct 2026 (about 06:40–07:35): the owner's ruling on the sealed matches

Session `4ad0f090-214d-4b51-b18a-41ad8262b656`, resumed after a context summary.

* **The owner's words, verbatim** (29 Oct, after Claude's plain-words explanation of § 6):
  > Note: I am good to start the fair test from 19 october 2026, but I want it to be a user decision to potentially
  > over-ride it. Not a hard lock. Like a "soft-rule" so when I give vague instructions to an LLM to test it out on
  > recent data, it may return to me the option of when to test it, and should we have the clean hold out.
  >
  > Im building out womens models, prop models , ITF models, and lets say in 3 months, not using that data to inform
  > decisions is a significant cost. Its loosely related to the current model I have.
  > Im not sure how to navigate that trade off. How psiloed to keep the prop and ITF models from the main model.
  >
  > What do you think of a ledger of keeping track of each time we touched sets of data going forward so that we can
  > backwards reason HOW contaminatead certain data is.
  > A file that stores all of this that the claude/agents.md file is aware about, and directs agents doing work to the
  > existence of it, so when it looks at the "hold outs" to inform a decision that makes its way to the model it updates
  > this ledger automatically without me explicitly telling it.
* **How it was read:**
  * the ruling on § 6's open question: 19 Oct 2026;
  * soft: the owner may override it, and agents offer the choice when an instruction leaves it open;
  * a project-wide ledger, pointed to from CLAUDE.md and kept by agents without being asked;
  * a request for advice on how far to keep the side models apart.
* **Done.** The design is in the
  [decision record](../../decisions/2026-10-29-holdout-soft-rule.md).
  * `docs/holdouts/`: the README, `register.csv` (H1–H3) and `looks.csv`, with L0001–L0003 and D0001–D0002 backfilled
    through the tool.
  * `src/eda/holdouts/ledger.py` and `test/holdouts/test_ledger.py` (12 tests).
  * `harness.py`'s warning now reads the register: `SEALED_FROM` is removed, and one test was added. 34 of 34 pass.
  * Edits elsewhere:
    * CLAUDE.md: a new section and a row in the locations table;
    * the decisions index: a new row;
    * README § 4 (`--last-date 2026-10-18`) and § 6: dated notes;
    * edge anatomy § 3: a dated note.
* **Dates checked; no result was read:**
  * The qualifying study's follow-up 2 (22 Oct) held 129 October matches. 4 of them were played on 19 Oct (`obs` and `es`
    in its tree's timing table).
  * The 21 Oct instance's frame ends with events of 12 Oct.
  * So H1 has one prior read: 4 matches pooled with 15,830 others, under a harm check (L0002, D0002).
* **Judgment calls:**
  1. **A period per question,** not one seal. H2 and H3 keep their registered windows, following the serve-and-return
     study's reasoning.
  2. **The women's model counts under H1,** as a recommendation for the owner to confirm: it predicts the same winners.
  3. **A CSV ledger with a tool,** because the contamination arithmetic needs structured windows, k and se.
  4. **The backfill holds only the reads known to touch today's periods.** Earlier harm checks stay in
     `class_record.csv`.
* **Peers:**
  * Claims sent to tennis-predictions-66 and -a1; neither overlapped.
  * tennis-predictions-66 is deleting this study's `build/` and `harness/` parquet tables with the owner's go-ahead.
    They can be rebuilt (§ 10).

---

## Note, 29 Oct 2026: the working tables deleted

Added by the cleanup session `f3ef49b6-3465-4894-9ba4-f454eb3a9b2a` (tennis-predictions-66), at the owner's word
("Delete this"; [cleanup inventory, process log § 10](../cleanup_inventory/process_log.md)).
* **Deleted at 07:31:35:** the nine git-ignored `.parquet` tables, 26,080,455 bytes:
  * in `build/`: `atoms`, `crosswalk`, `depth_rows`, `links`, `match_sources` and `rally_points`;
  * in `harness/`: `challenger_link`, `model_inputs` and `population`.
* **How it was checked:** each table's size was re-checked against the size found at the check. The folder's other 24
  files were listed before and after; none was lost.
* **What stays:**
  * every JSON and CSV output, among them `population_facts.json`, the builder's reports, and the placebo and
    planted-signal rows;
  * the memos, the briefs, and every reading recorded here.
* **To get them back:** run the builder's scripts, then the harness's (§ 10; README § 8: about 10 and 20 minutes).
  * The inputs have moved since 28 Oct, so the numbers come out slightly different.
  * `population_facts.json` and the builder's reports hold the hashes and dates of the inputs the study read.

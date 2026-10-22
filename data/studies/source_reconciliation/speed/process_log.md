# Source reconciliation, Part G (serve speed): process log

16 Oct 2026 – 16 Oct 2026 · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code, as a subagent of the study's
lead session · Session: f3930e64-e3c4-49f0-8e93-a4637aebdbcf · For the lead and a future reviewer · Report: delivered
to the lead in the subagent's final reply (the harness does not let a subagent write REPORT.md)

This part's log lives beside its outputs (the brief limits this part's writes to `src/eda/source_reconciliation/spd_*.py`
and `data/studies/source_reconciliation/speed/`); the lead may fold it into the study's `docs/studies/` log.

## 1. The request

* **The lead's brief for this part, verbatim (16 Oct 2026; the shared hard rules and context are in the lead's own log):**
  > YOUR PART: Part G, serve speed. Prefix: spd_. Part folder: data/studies/source_reconciliation/speed/. Report:
  > speed/REPORT.md.
  > Background (read first): docs/studies/input_data_audit/README.md section 2 (all of it), docs/studies/
  > serve_speed_acquisition/README.md, docs/studies/serve_speed_tabpfn/README.md (the panel and the live feed), and
  > docs/decisions/2026-10-07-speed-nudge.md. The model's stage 2 reads each men's player's first-serve average speed per
  > match from a panel (src/eda/serve_speed_tabpfn/panel.py; live: src/eda/serve_speed_tabpfn/live/live_panel.py,
  > frozen_panel(): data/studies/serve_speed_tabpfn/live/speed_panel_frozen_corrected.parquet plus
  > speed_panel_backfilled.parquet), which takes one source per player-match by an order. The audit found the handoff's key
  > statistics 26% more than 10 km/h off the player's norm, broken ManTennisData rows and court offsets, and suggested:
  > prefer the point mean where a key statistic differs from it by more than 5 km/h; drop rows whose average is at or above
  > the maximum, or whose second-serve average is at or above the first; bands of 150-235 km/h (men) and 125-205 (women).
  > Only the 130 impossible records were excluded (8 Oct).
  > The question: per player-match, which source of first-serve average speed is the most accurate, taking as referee the
  > mean of the same match's timed first serves in point records (Infosys MatchBeats and rally analysis, the Slam feeds'
  > points, Sackmann's Slam point-by-point speeds, the Hawk-Eye copy) where one exists; and does a consensus rule (e.g. the
  > median of the available sources; the point mean first; a key statistic only when within X km/h of another source) beat
  > the panel's current choice? Measure: (1) each source's agreement with the point mean (bias, SD, share within 1, 3 and 5
  > km/h), by source and season, men and women; (2) how many panel rows (by season) differ from the point mean by more than
  > 3, 5 and 10 km/h, and from the consensus; (3) how far the consensus would move spd_L: recompute the 28-day speed form on
  > the corrected history with the project's own code (src/eda/serve_speed_tabpfn/features.py, adaptive/adjust.py), at the
  > data level only (do NOT score against results), and count the matches moved by at least 0.25, 0.5 and 1 unit, as the
  > audit's propagation table did. Never modify the frozen or live panels; build your alternatives under your folder.
* **How it was read (16 Oct, before any result):**
  * "The panel's current choice" = the history the live feed and the coefficient fits read: `live_panel.frozen_panel()`,
    i.e. `speed_panel_backfilled.parquet` (the corrected copy plus the ATP backfill), checked by its own SHA-256 chain.
  * "Point mean" = mean speed of the points a player served on his or her first serve that were in (serve 1, not a double
    fault), timed. A first-serve fault is not in that mean; a definitional variant (all first-serve attempts, faults
    included) is reported where a source holds fault speeds, to say which definition each key statistic follows.
  * The referee must not be the record being judged: a point copy is judged against another copy; an aggregate statistic
    against the best point copy.
  * "Does a consensus rule beat the current choice" is answered at the data level only: (a) against an independent
    point referee where one exists; (b) by validating key-statistic validity rules on 2021-24 rows (where a referee
    exists) before applying them to 2025-26 rows (where none does). Nothing reads a match result.
  * spd_L is recomputed for the men's frame matches of 2024-26 under scenarios A (instant) and B (the weekly feed, the
    replays' history), plus D (daily) for completeness, with `features_latency` / `panel.EditionOffsets` exactly as the
    audit's propagation step (`input_data_audit/speed/a14_propagation.py`) did; the base must reproduce the stored
    `infosys_atp_backfill/speed_columns_augmented.parquet` exactly before any alternative is read.
* **Readings set aside:** scoring any rule against match results (forbidden by the brief and the sealed holdout);
  refitting the stage-2 coefficients (that reads results).

## 2. Starting point

* Stage 0 = the study's frozen snapshot (`_snapshot/`, manifest of 16 Oct 2026 20:53 UTC; Stage 0 files of 14 Oct).
* Speed history = `data/studies/serve_speed_tabpfn/live/speed_panel_backfilled.parquet` (43,315 rows).
* Records = `data/studies/serve_speed_tabpfn/speed_records.parquet` (70,805 records, the study's frozen build).

## 3. Plan (16 Oct, before any result)

1. Own readers (`spd_readers.py`) for every on-disk source of a per-player-match first-serve average: point copies
   (Infosys MatchBeats of the AO/RG and ATP hosts; Infosys rally analysis of the handoff, the ATP host and SirGenkii;
   IBM SlamTracker points of Wimbledon and the US Open; Sackmann's Slam point-by-point; the Hawk-Eye copy of AO/RG) and
   aggregates (ManTennisData; the handoff's, the ATP host's, SirGenkii's and RG's Infosys key statistics; RG's plain
   statistics; the IBM feeds' match statistics; the AO match centre). Verify each on >= 5 random linked matches by hand.
2. Link every record to the snapshot's (match_id, side), check orientation by names.
3. Referee and agreement tables (task 1); panel rows against the referee and the consensus (task 2).
4. Consensus histories under this folder; spd_L recomputed with the project's code; movement counts (task 3).
5. REPORT.md.

## 4. Chronology

| When (UTC) | Step | Result / decision | What had been seen |
|---|---|---|---|
| 16 Oct | Read the background (audit §2, acquisition, TabPFN study, nudge decision) and the code (panel, live_panel, features, features_latency, adaptive columns/adjust, form, dp_predict, history/backfill builders, a14_propagation) | The current history is `frozen_panel()` = the backfilled panel; coefficient fits read `infosys_atp_backfill/speed_columns_augmented.parquet` (spd_L_B / spd_L_D) | No result |
| 16 Oct | Survey of the staged speed tables | MatchBeats speeds are whole km/h on all three Infosys hosts; the AO 2026 match-centre points carry no speed; the Infosys Challenger files time only 930 points (left out) | Values only |
| 16 Oct | Point-by-point join of MatchBeats and rally analysis (same pointId) | ATP host: rally = MatchBeats - 1 on 50.3% of 25,108 timed points, equal on the rest (mean -0.503 km/h): the rally analysis truncates, MatchBeats rounds. RG host (RG 2025): identical on 56,860 of 56,860. So the handoff's rally-analysis point means (the panel's `infosys`) sit about 0.5 km/h below a MatchBeats mean by definition | Values only (`s05` scratch check; reproduced in `spd_checks.py`) |
| 16 Oct | Rally reader: first version took the server per point from the ending shot's parity (as shot_level.points, which built the panel's `infosys` point means) | Against MatchBeats servers on the ATP host: 97.7% of classified points right (87.2% at the 2018 Finals); the 2018 final's Djokovic mean came out +4.9 km/h. Replaced by a set-level parity vote (double faults left out of the vote: one 2021 event lists them under the winner): 99.99% right, 98.9% of points assigned. RG host: 99.97% / 100% | Values only |
| 16 Oct | ATP key statistic vs MatchBeats (2018, 2021; 366 player-matches) | KS = round(MatchBeats mean) in 90.4% (= ceil of the rally mean, 89.6%); a tail up to ±62 km/h. Per-set key statistics show the tail is the FIRST SET's average: set 1 reads 360, 59, 208, 162 km/h where MatchBeats reads 186-201, later sets agree to <1 km/h; in two cases MatchBeats also lacks most of set 1 | Values only |
| 16 Oct | RG's plain statistics (rolandgarros_stats) | `speed_averageFirstServe` is 0-14 (nonsense) in 2019-22 and absent 2023-26: unusable, left out | Values only |
| 16 Oct | spd_build.py --fresh | 148,060 records, 144,559 linked; names never reverse a link's orientation (0 of 61,000+ testable); ManTennisData 46 round mislinks (23 matches), as the acquisition study found | Values only |
| 16 Oct | spd_checks.py: 5 random records per reader (75), recounted by plain loops from the staged rows (the handoff from its raw JSON lines) | 40/40 point records equal in counts and means; 35/35 aggregates equal the staged values; every name on its side. Keys in reader_checks.json | Values only |
| 16 Oct | Pairwise agreement of every source (scratch t06), then spd_agree.py | Slam sources agree to ~1 km/h (IBM statistic = its points' rounded mean, 99.8% within 1; RG key statistic = MatchBeats' rounded mean, 99.9%; Hawk-Eye copy vs Sackmann 96-98% within 1, 100% within 5). ATP key statistic vs point mean: 89% within 1, 94% within 5, 1.6-2.2% beyond 10; the four copies of the ATP statistic are identical (ManTennisData = handoff on 11,782 of 11,783) | Values only |
| 16 Oct | Decision (before any spd_L): a point copy is "complete" only if timed share >= 0.9 AND its first serves in are within 10% of the box score's | Added after seeing that copies missing a set inflate the key statistic's apparent error (coverage < 0.95: 70-85% "errors"); with the gate the key-statistic error rate is 6.2% beyond 5 km/h | The agreement tables only (no spd_L, no result) |
| 16 Oct | Event-level vs match-level errors; arbitration by the player's norm | No event's median key-statistic error exceeds 0.25 km/h: the errors are match-level, so edition centring cannot absorb them. When key statistic and point mean disagree by > 5 km/h, the point mean is closer to the player's norm in 74% (5-10), 85% (10-20), 93% (> 20) | Values only |
| 16 Oct | Validity rules for key statistics (t1_ks_flags.csv), judged on 10,028 rows of 2021-25 with a referee, 634 errors > 5 km/h | avg >= max: precision 100%, recall 8%; 2nd >= 1st: 19% / 3%; bands 29% / 1%; the three together 43% / 12%; player-norm >= 10 km/h 28% / 34%; set-1 vs later sets >= 10 km/h 34% / 68% (needs per-set values, absent from ManTennisData). A first ks_flags run took the per-set values from the wrong copy (ManTennisData has none): fixed and re-run, the numbers above are the fixed ones | Values only |
| 16 Oct | Task 2 (t2_*.csv) | Men's panel rows with a referee: 20,849; beyond 3/5/10 km/h: 950/577/135, of which ManTennisData rows 924/559/128. Women: 0 beyond 3 | Values only |
| 16 Oct | spd_consensus.py, first run | The key-statistic swap fired on 718 rows: it accepted partial point copies (some lack a set). Decision before any spd_L was computed: only a complete copy (the referee's gate) may overrule a full-match statistic. Re-run: 576 rows (= task 2's count beyond 5 km/h) | Only the rule's own row counts |
| 16 Oct | spd_spdl.py base | The current history reproduces infosys_atp_backfill/speed_columns_augmented.parquet exactly (every column), so the alternatives run the production builder | Values only |
| 16 Oct | Flaw found in the "median" rule while it ran: its key-statistic family included the impossible records (e.g. 267 km/h) that the live feed already excludes; its first run (A >= 1 unit: 27, max 4.61) is superseded. Fixed in spd_agree.panel_rows (aggregates rejected by the audit's impossible rule or the panel's floors do not vote); the median rule is re-run after the other rules finish | Seen: the first median run's move counts (data level) |
| 16 Oct | Side finding: the panel's own `infosys` point means (speed_records.parquet, shot_level's per-point parity) against this part's rally reader on 9,697 player-matches | Differ by > 1 km/h in 10.8%, > 3 in 1.4%, > 5 in 0.5% (servers misassigned, unclassified points dropped). 90 history rows use them; the audit's 5 km/h key-statistic check and the study's "ceiling in 81.5%" read them | Values only |
| 16 Oct | spd_spdl.py, all rules (log: session scratchpad spdl1.log) | Moves at >= 0.25/0.5/1 unit, men 2024-26, scenario B: ks_within5 437/163/29; ks_within3 579/226/40; points_first 621/244/41; ks_within5_audit 602/243/80; ks_within5_literal 3,562/2,289/1,075. Live form on 16 Oct 2026: 0 of 590 men move >= 0.1 unit under the replacement rules (every changed row is older than 364 days) | Data level only; no result read, no coefficient refitted |
| 16 Oct | spd_agree.py, spd_consensus.py, spd_spdl.py --rules median after the fix | The ks_within5 history is byte-for-byte unchanged by the fix (assert_frame_equal). Median rule: 18,491 rows changed; B: 249/46/4, max 1.52. Task 2 against the consensus becomes 532/216/58 (was 604/289/108) | As above |
| 16 Oct | Rule 3 | The live Stage 0's three files equal the snapshot manifest's SHA-256 (no helper read them) | - |
| 16 Oct | The REPORT.md asked for by the brief could not be written: the harness blocks report files from subagents. Its content went to the lead in the final reply | - | - |

## 5. Claims and their evidence

| Claim | Evidence |
|---|---|
| The readers are right | reader_checks.json: 75 hand checks (40 point and 35 aggregate), all equal; names on the side in all 75; build_summary.json: 0 orientation reversals |
| The rally analysis is -0.51 km/h by definition (ATP host) | reader_checks.json "definitional" (25,108 points); t1_pairs.csv mb_atp-ra_atp |
| Per-point parity misnames 2.3% of servers | reader_checks.json definitional `server_per_point_rule_*` |
| Slam sources agree within ~1 km/h | t1_agreement.csv, t1_pairs.csv |
| The ATP key statistic: 6.2% beyond 5, 1.6% beyond 10 km/h | t1_agreement.csv (ks_mantd all), checks in scratch t08 (coverage gate) |
| The errors are match-level | scratch t08 (event medians within 0.25 km/h); reproducible from records.parquet |
| The point mean is the better value when they disagree | t1_arbitration.csv |
| The audit's rules catch 12% | t1_ks_flags.csv |
| spd_L moves | t3_spdl_moves.csv, t3_live_form.csv; base reproduction asserted in spd_spdl.py |

## 6. Threats to validity

* **The referee shares the key statistic's system.** Both come from Infosys, so the comparison sees aggregation
  faults, not radar faults. A radar error common to both would be invisible.
* **The norm test** uses the history's own rows, mostly key statistics, and the 91-day window includes real form
  changes.
* **The coverage gate** uses Stage 0's box score, which comes from the same ATP statistics. A box score wrong in the
  same way would pass.
* **The scale offsets of the Slam copies against MatchBeats** (at most 0.5 km/h) were not measured.
* **"Complete" thresholds** (0.9 timed share, coverage within 10%) were set before any spd_L was computed, but after
  the agreement tables were read.
* **The 5 and 3 km/h thresholds** come from the brief and the audit; they were not tuned.

## 7. What a re-design would do

* Score the repaired history's spd_L on a result-free speed target: the next match's referee point mean, from
  earlier rows only.
* Measure b-tilde's change in a pre-registered refit (the owner's call).
* Collect the ATP host's MatchBeats / rally files for 2025-26 to give the tour level a referee.
* Decode Court Vision for a measurement-level referee.

## 8. Reviewer checklist and reproduction

* Re-run the five scripts in the order spd_build (--fresh), spd_checks, spd_agree, spd_consensus, spd_spdl.
* spd_spdl.py must assert the reproduction of `speed_columns_augmented.parquet`.
* Spot-check three reader_checks.json keys against the staged tables by hand.
* Confirm t3_rules.csv's ks_within5 count (576) equals t2_panel_vs_referee.csv's beyond-5 count over the three
  key-statistic sources (559 + 9 + 8).

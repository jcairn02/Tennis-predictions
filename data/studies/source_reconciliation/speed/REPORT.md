# Part G, serve speed (subagent 6's report)

16 Oct 2026 · Written by subagent 6 for the lead; saved here by the lead because the harness refused the subagent's own write of this file. The text below is the subagent's report as returned, unedited apart from this header. The subagent's own process log is `process_log.md` beside it. The lead's re-checks are in the study's process log and README.

## 1. Answers

**Q1. Which source is the most accurate?**

- **At the Slams it doesn't matter.** Every source agrees with the point mean to about 1 km/h (`t1_agreement.csv`, `t1_pairs.csv`):

  | Source | Referee | Player-matches | Within 1 km/h | Within 5 |
  |---|---|---:|---:|---:|
  | IBM feeds' statistic | its own SlamTracker points | 6,254 | 99.8% | 100% |
  | RG's key statistic | RG MatchBeats | 1,277 | 99.9% | 100% |
  | Hawk-Eye copy | Sackmann's files | 1,391 | 96–98% | 100% |
  | AO match centre | Hawk-Eye / MatchBeats | 82 | 79–92% | 98–100% |

  No women's history row differs from the referee by more than 3 km/h.

- **At tour level the point mean beats the ATP key statistic.**
  - The four copies of the key statistic are one number. ManTennisData equals the handoff's on 11,782 of 11,783 player-matches.
  - Against a complete point copy that covers the whole match (9,543 player-matches), the key statistic is within 5 km/h in 94%, but 6.2% are more than 5 km/h off and 1.6% more than 10.
  - The worst season is 2023, with 8.4% more than 5 km/h off. Early rounds are worse: 11% in the first round against 4% in finals.
  - **The errors are match-level.** No event's median error exceeds 0.25 km/h, so the per-event offsets cannot absorb them.
  - **When the two disagree, the point mean is usually right.** It is closer to the player's own norm (his other matches within 91 days) in 67% of 3–5 km/h gaps, 74% of 5–10, 85% of 10–20 and 93% above 20 (`t1_arbitration.csv`). Those norm rows are mostly key statistics themselves, so the test if anything favours the key statistic.
  - **The cause is a corrupt per-set average** that the match value inherits. Examples: Eubanks, Indian Wells 2021, set 1 reads 360 km/h, giving a match value of 257 against 200.0 from the points. Gomez, same event, set 1 reads 59, giving 125 against 187.2. A gap of more than 20 km/h between set 1 and the later sets means 76% of match values are more than 5 km/h off; a gap of 3 km/h or less means 1.2%.

- **Differences by definition, not errors** (`reader_checks.json`):
  - The ATP host's rally analysis cuts speeds to whole km/h while MatchBeats rounds, so a rally mean reads 0.51 km/h low (25,108 points compared one by one). RG's two renderings are identical.
  - The ATP key statistic is the rounded MatchBeats mean in 90.4% of player-matches.
  - The panel's adjustment (key statistic minus 0.5 km/h) is therefore right in direction.

**Q2. Does a consensus rule beat the panel's current choice?** (data level)

- **Yes, where a complete point copy exists:** take the point mean when the key statistic is more than 5 km/h off it (`ks_within5`).
  - That repairs 576 history rows from 2018 and 2021–25: 559 ManTennisData, 9 handoff, 8 from the ATP backfill.
  - Using the point mean everywhere (`points_first`) adds about 10,000 changes, mostly rounding-sized; only one more row moves by more than 5 km/h.
- **The median of the sources is worse.** With only two independent sources per match it becomes their mean, which halves an error instead of removing it.
- **10,223 rows have only a key statistic** (7,099 in 2025–26), so no consensus is possible there. At the measured rate, roughly 600 of them are more than 5 km/h off.
- **Validity rules catch few of those errors** (`t1_ks_flags.csv`, judged on 634 errors among 10,028 rows):

  | Rule | Precision | Recall |
  |---|---:|---:|
  | average ≥ maximum | 100% | 8% |
  | all three audit rules | 43% | 12% |
  | 10+ km/h from the player's norm | 28% | 34% |
  | set 1 vs later sets 10+ km/h apart | 34% | 68% |

  The set rule needs per-set values, which ManTennisData does not have.
- **Read literally**, "a key statistic only when within X km/h of another source" would drop all 10,223 rows.

**Q3. How far would it move spd_L?**

The project's own column builder reproduces `speed_columns_augmented.parquet` exactly on the current history, so all alternatives run the production code. Counts are men's matches moved by at least 0.25 / 0.5 / 1 unit (`t3_spdl_moves.csv`):

| Rule (rows changed / dropped) | B (weekly feed), 2024–26, 7,070 matches | B, 2019–23, 11,594 matches | A (instant), 2024–26 |
|---|---|---|---|
| `ks_within5` (576 / 0) | 437 / 163 / 29, max 2.13 | 551 / 222 / 33 | 547 / 245 / 66 |
| `ks_within3` (947 / 0) | 579 / 226 / 40 | 701 / 253 / 36 | 715 / 324 / 80 |
| `points_first` (10,840 / 0) | 621 / 244 / 41 | 742 / 261 / 38 | 782 / 342 / 83 |
| `median` (18,491 / 0) | 249 / 46 / 4 | 223 / 34 / 2 | 342 / 84 / 12 |
| `ks_within5_audit` (576 / 145) | 602 / 243 / 80, max 4.82 | 697 / 316 / 85 | 759 / 357 / 126 |
| `ks_within5_literal` (576 / 10,223) | 3,562 / 2,289 / 1,075 | 2,141 / 1,048 / 334 | 4,086 / 2,755 / 1,446 |

- Scenario D is in the file.
- **Today's live form is untouched:** on 16 Oct 2026, 0 of 590 men move by 0.1 unit under the replacement rules, because every changed row is older than the 364-day window. The rules act on replays and on the 2019–25 seasons the stage-2 coefficients are fitted on.
- How the fitted coefficient would move is unknown; that needs a refit that reads results.

**Recommendation (adoption is the owner's call):**
- Treat `ks_within5` (or `ks_within3`) as a repair of the history.
- Don't adopt the median rule, the audit's drop rules (43% precision; they add 51 moves of 1 unit or more), or the literal reading.
- A consequence to state if adopted: the training history becomes cleaner than the 2025–26 live inputs, which keep the ~6% tail.

## 2. Built

- `spd_readers.py`: 15 readers.
  - Point copies: MatchBeats (AO/RG; ATP host), rally analysis (ATP host, handoff, SirGenkii), SlamTracker, Sackmann, the Hawk-Eye copy.
  - Aggregates: ManTennisData, the handoff's, ATP host's, SirGenkii's and RG's key statistics, the IBM statistic, the AO match centre.
  - Linking puts every record on the snapshot's match and side, with orientation checked by names.
- `spd_build.py`: runs and caches the readers, links, and marks mislinks (wrong round, wrong level, duplicates).
- `spd_checks.py`: hand checks and the point-by-point definition checks.
- `spd_agree.py`: tasks 1 and 2.
- `spd_consensus.py`: the alternative histories, as copies.
- `spd_spdl.py`: task 3, with the reproduction check and the live form.

## 3. Outputs and columns (`speed/`; parquet is per-match and git-ignored)

- **`cache/<reader>.parquet`**: per record and player slot.
  - Identity: `src`, `kind`, `sys`, `key`, `pno`, `pname`, `year`.
  - Point counts: `npts`, `f1`, `n1`, `s1`, `sd1`, `f2`, `n2`, `s2`, `nf`, `sf`, `pmax`, `rep`.
  - Published values: `v1`, `v2`, `vmax`, `vfin`, `vftot`, `v1_set1`, `fin_set1`, `v1_rest`, `fin_rest`.
- **`records.parquet`**: the cache columns plus the link columns, the snapshot context, `invalid_reason` and `valid`.
  - Link: `match_id`, `side_link`, `side_names`, `side`, `link`, `link_flip`, `name_ok`, `dup_link`, `round_src`.
  - Context: `tour`, `year_s0`, `level`, `qualifying`, `round`, `tournament_id`, `tournament_name`, `tournament_date`, `player_id`.
- **`build_summary.json`**, **`reader_checks.json`**.
- **`t1_agreement.csv`**: `src`, `tour`, `year`, `referees`, `n`, `bias`, `median`, `sd`, `sd_robust`, `mae`, `within_1/3/5`, `beyond_5/10`.
- **`t1_pairs.csv`**: `x`, `y`, `tour`, and the same statistics.
- **`t1_ks_mechanism.csv`**: by set-1 gap band, `n`, `match_ks_beyond_5/10`, `match_ks_mae`, `later_sets_ks_beyond_5`, `later_sets_ks_mae`.
- **`t1_ks_flags.csv`**: `rule`, `scope`, `rows`, `errors`, `flagged`, `flagged_errors`, `precision`, `recall`.
- **`t1_arbitration.csv`**: `gap_kmh`, `rows`, `point_mean_closer_to_norm`, and the two median distances to the norm.
- **`panel_rows.parquet`**: every history row plus the value on the MatchBeats scale, the referee, the consensus families (`fam_*`) and `norm_dev`.
- **`t2_panel_vs_referee.csv` / `t2_panel_vs_consensus.csv`**: `tour`, `year`, `panel_source`, `panel_rows`, `with_ref_mb` / `with_cons_mb`, `same_copy`, `beyond_3/5/10`, `share_beyond_5`, `median_abs`.
- **`agree_summary.json`**.
- **`histories/<rule>.parquet`**: the history with each rule's values.
- **`t3_rules.csv`**: rows changed / dropped per rule, tour, season and source.
- **`spdl/<rule>.parquet`**: every `spd_*`, `late_*` and `mode_*` column for scenarios A, B, D and E.
- **`t3_spdl_moves.csv`**, **`t3_live_form.csv`**, **`spdl_summary.json`**.

**Task 2 headline:** of 43,098 history rows in use, 30,819 have a referee. 950 / 577 / 135 differ from it by more than 3 / 5 / 10 km/h, and 532 / 216 / 58 from the consensus. ManTennisData rows account for 924 / 559 / 128.

## 4. Checks

- **Rule 8:** 75 random records (5 per reader) were recounted from the staged rows (the handoff from its raw JSON lines) by separate plain loops. All 40 point and 35 aggregate records match, and in all 75 the name is the snapshot's player on the assigned side. I read the printout myself.
- **Orientation:** wherever both a link's side and the names' verdict exist, they agree, with 0 reversals.
- **Reproduction:** exact, every column, in both runs.
- **Rule 3:** the live Stage 0's three files still equal the snapshot manifest's SHA-256. None of my code read them.

## 5. Couldn't do

- **No referee for 2025–26 tour level:** TDI's points have no speed, and the daily collector's files hold key statistics only.
- **Court Vision:** not decoded (obfuscated keys).
- **Flashscore:** not read; its timed matches are unoriented and mostly Slams.
- **RG's plain statistics:** the average reads 0–14 in 2019–22 and is absent in 2023–26.
- **AO 2026:** no referee; its points carry no speed.
- **Independence:** the referee and the key statistic come from the same Infosys system, so these comparisons see aggregation errors, not radar errors.
- **Not measured:** the effect on the coefficient and on log loss.

## 6. Surprising, or to report

1. **Bug, not fixed:** the panel's rally reader (`shot_level/points.infosys`) assigns the server point by point and gets 2.3% wrong (12.8% at the 2018 ATP Finals). Its point means differ from a set-level reader by more than 1 km/h in 10.8% of 9,697 player-matches. The audit's 5 km/h check used them; only 90 history rows do. My reader agrees with MatchBeats' servers on 99.99% of points.
2. **Wrong link:** a `shot_level` link puts the 2018 ATP Finals final on the same pair's round-robin match.
3. **The audit's "26% more than 10 km/h off" for the handoff's key statistics** described the panel before the 8 Oct exclusions. Today's 292 handoff rows sit at 6.8% against the player's norm, and 2 of 259 are more than 10 km/h off the referee.

To rerun, from the repo root:
```
./python.sh src/eda/source_reconciliation/spd_build.py --fresh
./python.sh src/eda/source_reconciliation/spd_checks.py
./python.sh src/eda/source_reconciliation/spd_agree.py
./python.sh src/eda/source_reconciliation/spd_consensus.py
./python.sh src/eda/source_reconciliation/spd_spdl.py
```

# Shot-level statistics

**Status: study, not a decision.** Started 2 Oct 2026 on the owner's question of that day. The statistics used so far are match totals: could statistics built from shot-by-shot and annotated point-by-point data be independent of the closing odds and of Elo, and would that justify finding or paying for more such data? Those data cover rally length, how points end, serve speed and placement, net play, return depth, stroke mix and ball tracking. Nothing here chooses features, models, markets, data purchases or a roadmap.

## In short

* **Observed.** 25 new per-player match statistics, built from 6.2 million points of eight sources (Stage 1). They are stable traits of a player, and almost entirely independent of the odds and Elo.
* **Observed.** As 141 pre-match features scored with the earlier studies' harness (Stage 2), none adds to the closing odds, alone or in profiles, nor to the odds plus the box-score profile. A few add a little to Elo, all under one milli-log-loss.
* **Observed. One direction to watch:** the men's serve speed, chiefly its recent change. It adds 0.24 milli-log-loss to the odds in 2022–2026 (range 0.07 to 0.41), positive in each of those seasons and absent before. One row among about 300.
* **Inferred.** Style measured from shots is real and new to the market, but it does not say who wins. These results give no case for buying more shot-level data for pre-match markets.
* **Observed. Method or data (Stage 3).** Little of the null result is method.
  * Scored on serve points, the shot features add a third of box-score form's information for men in 2022–2026, and nothing elsewhere.
  * Flexible learners find the box-score signal on the same matches and not the shot signal.
  * The one flaw found was the unpenalised profile fit, which costs about 0.5 milli-log-loss per 10 inputs. It hid nothing: with a ridge fit, every shot profile lands at zero given the odds.

  Planted edges show the data's limit. For serve speed, errors and winners, the real results rule out edges of 0.25–0.5 milli-log-loss (men) in the players' true career values. In the five noisy statistics, edges up to 1–2 could hide.

## The question

The two earlier studies ([predictability diagnostic](../predictability_diagnostic/README.md), [ideas borrowed from UFC-predictions](../ufc_ideas/README.md)) built every feature from box scores: each match's totals of aces, double faults, first serves in, points won on the first and second serve, service games and break points, plus the score. Their one lead against the closing odds is the men's two-week profile of twelve individual box-score statistics. It measured 0.51 milli-log-loss over all scored seasons and 0.92 in 2022–2026 ([Stage D](../ufc_ideas/stageD.md)). After the [feature-alpha audit's repairs](../feature_alpha_audit/repairs.md) it is 0.36 beyond Pinnacle's line, with an interval from −0.25 to 0.96.

This study asks the same question one level down: do statistics that only shot-level data can produce add anything to the closing odds, and to the box-score profile, on the same matches?

## Owner decisions

* **2 Oct 2026, after Stage 0:** build the features from the shot-by-shot and point-by-point data and test them against Elo and the closing odds directly ("build more features ... trainable at a match level that we currently don't have but can be assembled up from the more granular data ... to potentially add to the list of features that improve on ELO or the closing line"). That replaced the approval step the candidate list had proposed. Stages 1 and 2 were built the same day.
* **2 Oct 2026, after Stage 2:** the owner asked "how much of this is you dont know how to amalgamate the data in a predictive way vs theres simply no edge to be found there?" Stage 3 answers it.

## Stages

| Stage | What | Status | Write-up |
|---|---|---|---|
| 0 | What the data on disk holds, linked to the earlier studies' match table; on how many matches with closing odds a shot-level feature could be scored; the smallest gain such a test would detect | Built 2 Oct 2026 (about 3 minutes of compute); tables regenerated after Stage 1 corrected one source's keys. Nothing compared with who won | [stage0.md](stage0.md) |
| Candidate list | The proposal that preceded the owner's decision | Superseded on 2 Oct 2026 by the owner's decision; kept as the record of the proposal | [candidates.md](candidates.md) |
| 1 | The common point table from eight sources under one convention, checked source against source; 25 statistics per player and match; which of them are traits | Built 2 Oct 2026 (about 2 minutes) | [stage1.md](stage1.md) |
| 2 | 141 pre-match features in the earlier studies' forms; the rundown against Elo, the closing odds and the box-score profile; the place of every row in the list of features tried | Built 2 Oct 2026 (about 10 minutes) | [stage2.md](stage2.md) |
| 3 | Method or data? The shot features scored on serve points; flexible learners on both players' values; edges planted in the players' true values to measure what the pipeline recovers; the profiles refitted with a penalty | Built 2 Oct 2026 (about 10 minutes) | [stage3.md](stage3.md) |

## Brief

**Scope.** The earlier studies' pool and harness: singles, ATP and WTA side by side, evaluation matches and seasons as in the [predictability diagnostic's Brief](../predictability_diagnostic/README.md#brief), scored with `src/eda/ufc_ideas/common.py`. History for shot-level features: every linked source match from 2010 at any level. Closing odds exist only for main-tour main draws (Grand Slams to 250s), so the market comparisons are on those matches.

**Rules.**

* Follow [CLAUDE.md](../../../CLAUDE.md): `./python.sh`, the filing table, no Git command that changes state, no deletion of temporary files mid-session.
* The earlier studies' code and tables are read-only: imported, never edited. This study read the original tables (versions and hashes in `stage0_summary.json`, `inputs`). The feature-alpha audit was repairing that code on the same day and writes its repaired tables to its own folder.
* Code in `src/eda/shot_level/`, named `stageN_*.py` (shared modules `common.py`, `points.py`, `stats.py`); tests in `test/shot_level/`; outputs in `data/studies/shot_level/`, named `stageN_*` (Parquet for big tables, which git ignores; CSV and JSON for evidence); write-ups here.
* Raw and staged data are read, never written. Downloads running in other sessions are left alone.
* A feature for a match may use only earlier events and earlier rounds of the same event (`common.asof_sums` of the predictability diagnostic). Every feature family passes a leak probe.
* No constant is tuned on results: memories are fixed in advance, and shrinkage comes from the statistics' own spread.
* Compute every number before stating it; the write-ups' tables are generated from the stages' files. Log loss only, never AUC; differences in milli-log-loss, with the word better or worse; groups under 300 matches are directional only.
* Label results **observed** (measured), **inferred** (a reading) or **suggestion** (a proposal). The owner builds UFC models and knows sports modelling, but is new to tennis: each tennis term is defined once.

## Files

| What | Where |
|---|---|
| Shared helpers: the families of shot-level fields, the source register, the link to Stage 0, the detectable-gain formula | `src/eda/shot_level/common.py` |
| The common point table's adapters; the per-match statistics | `src/eda/shot_level/points.py`, `stats.py` |
| Stage 0: every source read match by match and linked; coverage and detectable gains; the write-up's numbers and tables | `stage0_sources.py`, `stage0_coverage.py`, `stage0_summary.py` |
| Stage 1: the point tables, the source agreement, the statistics, their reliability | `stage1_points.py`, `stage1_agreement.py`, `stage1_stats.py`, `stage1_reliability.py` |
| Stage 2: the features, the rundown, the clustered ranges and redundancy, the full list, the write-ups' tables | `stage2_features.py`, `stage2_rundown.py`, `stage2_summary.py`, `stage2_list.py`, `stage2_tables.py` |
| Stage 3: both players' values side by side, the serve-point test (and its split into serve and rally inputs), the flexible learners, the ridge refit of the profiles, the planted edges, the write-up's tables | `stage3_sides.py`, `stage3_points.py`, `stage3_points_split.py`, `stage3_flexible.py`, `stage3_profiles.py`, `stage3_planted.py`, `stage3_tables.py` |
| Outputs | `data/studies/shot_level/stage0_*`, `stage1_*`, `stage2_*`, `stage3_*` (listed in each stage's write-up; the three large Parquet files in [data/LARGE_FILES.md](../../../data/LARGE_FILES.md)) |
| Tests | `test/shot_level/test_stage0.py`, `test_stage1.py`, `test_stage2.py`, `test_stage3.py` (42 tests) |

Rebuild, from the repository root, all with `./python.sh`:

1. Stage 0: `src/eda/shot_level/stage0_sources.py` (under 2 minutes with 5 workers), `stage0_coverage.py` (about a minute), `stage0_summary.py` (seconds; `write_tables` for the write-up's tables).
2. Stage 1: `stage1_points.py` (about 1½ minutes), `stage1_agreement.py`, `stage1_stats.py`, `stage1_reliability.py` (seconds each).
3. Stage 2: `stage2_features.py` (about 6 minutes with the probe), `stage2_rundown.py` (about 4 minutes), then `stage2_summary.py`, `stage2_list.py` and `stage2_tables.py` (seconds).
4. Stage 3: `stage3_sides.py` (a few minutes), then `stage3_points.py` (under half a minute), `stage3_points_split.py` (about 20 seconds), `stage3_flexible.py` (about 2½ minutes), `stage3_profiles.py` (under a minute), `stage3_planted.py` (about 4 minutes; it imports `stage3_profiles`), and `stage3_tables.py` (seconds).

Tests: `./python.sh -m pytest test/shot_level`.

# The ATP Stats Centre backfill (2018 to October 2021): what the decrypted files hold, and what they do for the model

8 October 2026 · Research evidence and data integration. The integration follows the owner's instruction (below). No model setting changed; stage 2's speed history gained the files after a tie against the frozen reference.

**The request** (the owner, 8 Oct 2026):

> "I took another route to decrypt the 2015-2020 data, its all tennis data, exactly like the other data. Nothing strange, take a look to see. Do a study if this data integrated into the serve data helps the offline tabpfn models. Integrate it as well into our pipeline like all the analogous data to this data unless there's a clear bug you identify. See if it gives us more insight into the future predictability of the feature we designed"

**Keys.**
* **Gains** are milli-log-loss (mLL) per match, paired. **Positive = the arm with the backfill is better** (lower log loss), unless a row says otherwise. A 95% interval that spans 0 is a **tie**.
* **Speed coefficients** are log-odds per unit of `spd_L_B`, the 28-day speed-form column of the decided adjustment (one unit = 1.95 km/h). **Positive = the man whose serve speed rose more than his opponent's wins more often than the model says.**
* **Labels:** *observed* (computed here, with its file) and *inferred* (reasoning).

**Note for reviewers (9 Oct 2026): a flaw in this study's intervals, found after it ran. The study was not re-run.**
* **The flaw.** The mLL intervals here add both arms' seed-to-seed variance as if their seed noise were independent. Every arm is the same fits (seeds 0–3), with only the speed column changed, so nearly all of that noise is shared and cancels in the difference. Adding both counts it twice. It matters most where the two forecasts differ least, as with the backfill.
  * Found by the adoption framework's statistics review ([finding 1](../adoption_framework/review_statistics.md)). In §4.1's own `scores.csv`, stage 1 compared with itself got ±0.087 mLL instead of 0.
* **§4.1 has since been re-read with the seed term paired,** as the check of the fix ([checklist](../adoption_framework/checklist.md), item 1; `data/studies/adoption_framework/seed_fix_check/`; results through 2024 only; + = with the backfill better):
  * both tours +0.014 [−0.006, +0.035] instead of [−0.073, +0.102]; men +0.027 [−0.012, +0.066] instead of [−0.073, +0.128]. P(better) is 0.92 for each: still unresolved;
  * stage 1, and the women: exactly 0, with a zero-width interval;
  * by season: 2022 still better, +0.10 [+0.05, +0.15]; **2023 now reads worse, −0.04 [−0.07, −0.01]**, a secondary cell (a flag, not a verdict); the rest still span 0.
* **§5's last column** (the adjustment against the calibrated base, by season) is affected too, but little: there the four-week blocks dominate. On the reference model, men 2020–2024, the review found the SE fell only from 0.169 to 0.162 when paired. §5's coefficient tests (the effects per unit, Cochran's Q, the predictive range) are not affected.
* **Not re-run, on purpose.** This study's `compare.py` now pairs the seed term, through `model_rebuild/compare.py`, and keeps the old intervals as `lo_unpaired` / `hi_unpaired`. The numbers below stay as they were computed.

## In short

1. **It is genuine ATP tennis data, decrypted exactly, but there is far less of it than "2015–2020" suggests** *(observed)*.
   * **2015–2017: nothing.** The ATP's host served no file for any event.
   * **2018–2020: 209 matches.** The 2018 and 2019 ATP Finals, the 2019 Next Gen Finals, and Vienna, Paris, Sofia and the ATP Finals of 2020. Every point is there, but only the 2018 Finals carry serve speeds.
   * **2021: a file for every match, but little inside.**
     * Points at only 9 of 52 events (365 matches). The other 43 events' point files name the players and hold no point.
     * **Serve speeds at three events:** Washington, San Diego and Indian Wells (169 matches).
   * **184 timed matches in all.** About 110 of them were not already in the speed history (the Hugging Face copy held the rest).
2. **No bug blocks it.**
   * **Decryption:** the files equal the Hugging Face handoff's independent decrypted copy on every value both hold (4,848 key statistics and 16,462 points).
   * **Identity:** they name the same two players as the ATP's plain records on all 2,048 linkable matches, and the same winner on all 566 with points.
   * **Quirks, all handled:**
     * a double fault is coded `P` (or `DF`);
     * the rally analysis cuts speeds to whole km/h, while MatchBeats rounds them;
     * about 5% of point files miss a point or are cut short.
3. **Integrated like the AO/RG files.**
   * Staged tables; the per-player speed table; the speed panel's builder; the data map.
   * **The live speed history:** +225 usable player-matches of 2018 and 2021, and one mislink fixed.
   * **No live forecast input moves:** all 1,093 players' speed forms of 8 Oct are unchanged.
4. **It does not help the offline TabPFN model measurably: a tie.**
   * **The official comparison with the frozen reference** (both stages, 2020–2024): both tours +0.01 [−0.07, +0.10], men +0.03 [−0.07, +0.13].
   * **Next season's coefficient:** b̃ for 2027 moves from 0.0432 to 0.0444.
   * **TabPFN's training rows** with both players timed in the last 28 days rise from 23.7% to 24.1%. That is far too little to change how little TabPFN uses the speed column, so no GPU refit was run.
5. **Future predictability of the speed feature: real on average, unstable from season to season** *(observed; the backfill moves these by a few percent)*.
   * **Pooled 2019–2026:** +0.050 [+0.013, +0.086] log-odds per unit. On 2019–2024 alone the pooled effect ties: +0.030 [−0.020, +0.080].
   * **The seasons disagree more than chance allows** (I² ≈ 50%, p ≈ 0.05).
     * 2022: +0.15.
     * 2023: −0.05. The walk-forward adjustment lost 1.3 mLL per men's match that year.
     * 2026: +0.10.
   * **What it means for next season:**
     * the 2027 adjustment's expected gain is about **+0.2 to +0.3 mLL per men's match**;
     * roughly **a one-in-three chance of a losing season**.
   * **The backfill cannot settle this.** Only seasons with dense tour speeds (2022 onward) can, and each new season adds one.

## 1. What the files hold

*Observed:* `data/studies/serve_speed_acquisition/infosys_atp_stage_summary.json`, `data/dump/points/infosys_atp/`. The download is section 8 of the [acquisition study](../serve_speed_acquisition/README.md); the decryption audit is `data/studies/serve_speed_acquisition/infosys_atp_decryption/` (4,906 files, every one opened, originals unchanged).

| Season | Events with files | Matches with points | Timed matches (MatchBeats) | Key statistics with speed | Court Vision |
|---|---|---:|---:|---:|---:|
| 2015–2017 | none of 188 | 0 | 0 | 0 | 0 |
| 2018 | ATP Finals | 15 | 15 | 15 | 14 |
| 2019 | ATP and Next Gen Finals | 30 | 0 | 0 | 0 |
| 2020 | Vienna, Paris, Sofia, ATP Finals | 163 | 0 | 0 | 0 |
| 2021 (to 17 Oct) | all 52 | 365, at 9 events | 169: Washington 37, San Diego 27, Indian Wells 105 | 169 | 176 files |

* **What a point holds.**
  * **MatchBeats:** the server, the serve number, the serve's speed, the scorer, the rally counts and break-point flags.
    * At the 2018 and 2019 ATP Finals and in 2021 it also gives how the point ended.
    * At the 2019 Next Gen Finals and every 2020 event only aces and double faults are classified (the rest read `N`).
  * **Rally analysis:** the same points by the shot that ended them, with serve direction and court side.
  * **Court Vision:** Hawk-Eye tracking with decimal speeds.
* **The 2021 files of 43 events are shells.** They name both players and hold no point and no speed, from Delray Beach and Antalya in January to Winston-Salem in late August.
* **Staged** (`src/ingest/point_sources/infosys_atp_stage.py`, AO/RG's parsers): 2,072 match codes, 83,155 MatchBeats points (25,108 timed), 34,811 key statistics, 83,335 rally entries and 37,785 Court Vision points.

## 2. Is it right? Checks against independent copies

*Observed:* `data/studies/infosys_atp_backfill/checks.json`; every disagreeing value is in `check_mismatches.csv` (`src/eda/infosys_atp_backfill/checks.py`).

| # | Against | Result |
|---|---|---|
| A | ManTennisData's plain row for the same match code (the ATP's own pages) | **Same two players: 2,048 of 2,048.** Same winner: 566 of 566. Same games in every set: 558 of 563 |
| B | The key statistics' box score against ManTennisData's | 15,512 of 16,072 player values equal (96.5%). The rest are mostly ±1 (an ace, a first serve in) at the 2018–2019 Finals and Metz 2021 qualifying: the ATP's two publications differ, not the decryption |
| C | A box score counted from MatchBeats' points against the key statistics and ManTennisData | 93–99% equal per statistic (double faults 99%, service points 94%). Most misses are one point missing from MatchBeats; a few files are cut short (Washington QS020 holds 36 of 96 service points) |
| D | MatchBeats against the rally analysis of the same match | 83,137 points in both, 18 in MatchBeats only. **Serve number identical on every point; ending identical on all 32,628 classified in both.** Speeds: identical on 12,489 timed points, MatchBeats 1 km/h higher on 12,619 |
| E | Speeds against each other | **MatchBeats = Court Vision's decimal speed rounded** (23,374 of 23,469); **rally analysis = it cut down** (23,366). The key statistic's first-serve average is the rounded point mean (339 of 368) and its maximum the fastest point (367 of 368) |
| F | **The Hugging Face handoff's own decrypted copy** (261 matches in both: 2018–2019 Finals, Washington, Indian Wells and five other 2021 events) | **Key statistics identical: 4,848 of 4,848 values. Rally points identical: 16,462 of 16,462.** These files hold 21,696 more points than the handoff for the same matches, and the handoff none they lack |
| G | Impossible speeds | 29 MatchBeats speeds outside (40, 270] km/h (from 4 to 1,088) and 52 Court Vision speeds under 50: the project's 40–270 rule drops them. Two key-statistic averages fail the input-data audit's rule (257 km/h with a fastest serve of 211; 217 with 211) and are excluded |
| H | Stage 0 (Sackmann and Tennis My Life) | 2,048 of 2,070 matches link (2,024 by the exact id and round, 24 by names; the 22 left are empty Indian Wells qualifying files). Same winner 566 of 566. Box scores equal on 94–99.5% per statistic |

**Reading** *(inferred)*. A wrong key would give garbage, not data that equals a third party's copy to the last value. The disagreements are of the ordinary kind between two feeds (a point missing, a ±1 count), and no check found a decryption fault.

**Quirks to know, all handled in the new code** *(observed)*:
1. **Double faults are `P` or `DF`.** `P` counts equal the key statistics' double faults exactly in 2018–2020 (30/30, 60/60, 326/326 player-matches); in 2021 `P` + `DF` together match 703 of 730. Code that treats only `DF` as a double fault counts `P` points as second serves.
2. **Speeds differ by route by rounding:** Court Vision has decimals, MatchBeats rounds and the rally analysis truncates. *Inferred:* the Hugging Face copy's point speeds, which come from rally analysis, are therefore about 0.5 km/h below a MatchBeats mean. The speed panel prefers key statistics at tour level, so few rows are affected.
3. **The 2018–2021 key statistic is the rounded point mean,** not its ceiling (the research found the ceiling for later seasons, 81.5%). The panel's −0.5 km/h key-statistic shift is then 0.5 km/h too low for these rows and for the handoff's 2021 copies already in the history. *Inferred:* harmless, because each event edition gets its own offset.
4. **One mislink fixed.** At the 2018 ATP Finals, Zverev and Djokovic met twice: in the round robin and in the final. The handoff's name-based link had put both of their key-statistic records on the round-robin match, which made it unusable. The new code-and-round link puts each where it belongs.

## 3. Integration: where the data now flows

The template was the AO/RG Infosys files of 7 Oct (staged, per-player speeds, speed panel, live history) and the Hugging Face copy of the same feed (the data map, the panel).

| Step | What changed | File |
|---|---|---|
| Staging | Five tables from the decrypted JSON, as AO/RG's | `src/ingest/point_sources/infosys_atp_stage.py` → `data/dump/points/infosys_atp/*.parquet` |
| Per-player speeds | Source `infosys_atp`: 4,140 player rows, 368 timed, linked by the live linker (ATP codes, the exact id with ManTennisData's round) | `src/eda/serve_speed_acquisition/speeds.py` → `speeds.parquet` (rerun; the 7 Oct copy is kept in `replaced/`. 10 ManTennisData links moved, all from the 8 Oct player-id corrections, e.g. O'Connell) |
| Speed panel builder | Sources `infosys_atp` (MatchBeats point means) and `infosys_atp_ks` (key statistics), with the same rules. `build_records(sources=...)` builds any subset; on the old sources it reproduces the committed build exactly (70,805 records) | `src/eda/serve_speed_tabpfn/panel.py` (the study's frozen `speed_panel.parquet` is not rebuilt) |
| The live speed history | The corrected history plus the new records, chosen by the panel's own precedence | `src/eda/infosys_atp_backfill/history.py` → `serve_speed_tabpfn/live/speed_panel_backfilled.parquet` (+ `.json`). The live panel reads it only while its record matches the corrected copy (`live/live_panel.py`) |
| Data map | The entry now reads decrypted, staged and measured (placed by ATP ids). The "on disk but encrypted" gap is gone | `data/data_map.yaml`, `src/eda/data_map/measure.py`, `build.py` |

**The history in numbers** (`data/studies/infosys_atp_backfill/history.json`) *(observed)*:
* The frozen records alone reproduce the corrected history exactly, so the method is the one that built it.
* **Added: 226 player-matches, 225 usable.** 2018 ATP Finals 12; Washington 74, San Diego 53 and Indian Wells 86 in 2021. ATP usable rows rise from 507 to 520 in 2018 and from 1,439 to 1,652 in 2021.
* **Changed values: 3 player-matches.**
  * The 2018 Finals mislink above, which becomes usable (214.5 km/h on its own record).
  * Two Indian Wells qualifying matches move from the handoff's truncated point mean to the rounded MatchBeats mean (+0.6 km/h).
  * 139 more rows change only the list of alternative sources.
* **Live forecasts** (`live_check.json`): the live panel and the 28-day form of 8 Oct, rebuilt both ways, are identical for all 1,093 players. *Inferred:* the newest backfilled row is from 15 Oct 2021, outside every window a 2026 form reads.

**What was left out, and why:**
* **The shot-level point tables** (`stage0_source_matches`, `stage1_points_*`), where the Hugging Face copy of this feed sits.
  * No model input reads them.
  * Their linker matches by name, the cause of the 2018 Finals mislink.
  * Adding the source is one loader and `--only infosys_atp` (an option below).
* **The match clock:** the files carry no date or time of play.

## 4. Does it help the offline TabPFN model?

### 4.1 The official comparison with the frozen reference

*Observed:* `src/eda/current_best_model/compare.py --candidate reference --speed <the augmented column>` → `data/studies/infosys_atp_backfill/vs_reference_2026-10-08/`. This is the comparison the [current-best-model decision](../../decisions/2026-10-08-current-best-model.md) requires for new data:
* the reference's own fits (seeds 0–3), with only stage 2's speed column changed;
* stage 2 refitted walk-forward on 2019 .. Y − 1;
* scored on 2020–2024, so no 2025–2026 result is read.

| Population | Both stages (positive = with the backfill better) | Reading |
|---|---|---|
| Both tours (22,265 matches) | **+0.014 [−0.073, +0.102]** | **Tie** |
| Men (11,672) | +0.027 [−0.073, +0.128] | Tie |
| Women (10,593) | 0.000 | Unchanged (women's column is 0) |
| Stage 1 alone | 0.000 | Unchanged: 0 of 58 inputs differ |
| By season | 2020 −0.00, 2021 +0.01, **2022 +0.10 [+0.03, +0.17]**, 2023 −0.04, 2024 −0.01 | Ties except 2022: one of 13 rows, about what chance gives |
| For scale: the reference against its calibrated close | +1.37 [+0.67, +2.08] | Better |

**Coefficients** (b̃, shrunk; current → with the backfill): 2025 0.0241 → 0.0261 · 2026 0.0342 → 0.0357 · 2027 0.0432 → 0.0444.

### 4.2 The speed as a TabPFN column

* **The serve-speed study's diagnosis.** It found TabPFN uses only about 8% of the speed column's information. Its likely reason: few training rows carry recent speeds. It proposed decrypting these files to add some.
* **Measured** (`coverage.json`; men's frame matches with both players timed in the 28 days before) *(observed)*:

| Training rows of | Corrected history | With the backfill |
|---|---:|---:|
| the 2024 fit (2013–2023, 24,613 matches) | 23.7% both, 41.4% one | 24.1% both, 42.1% one |
| the 2026 fit (2013–2025, 29,909) | 32.8% both, 50.4% one | 33.1% both, 51.0% one |

* **The gain is 87 matches with both sides timed, all in 2021.** *Inferred:* a 0.35-point shift in coverage cannot move a 8% capture. A refit would measure seed noise.
* **So no GPU refit was run.** The card was also busy with another session's fits.

## 5. The feature's future predictability

*Observed:* `comparison.json` (2019–2024; nothing of the proposed holdout) and `comparison_through_2026.json` (also 2025 to 28 Jul 2026, the holdout's already-exposed part; see §6).
* **The model:** the rebuilt current best model (`data/studies/model_rebuild/fits`).
* **The test:** the serve-speed study's information test, men, one season at a time. It regresses the result on the base's log-odds (a slope per season and a cubic) plus `spd_L_B`.
* **Labels:** "now" = the corrected history; "backfill" = with the new files.

| Season | Effect per unit, now | With the backfill | Walk-forward adjustment's gain, men (mLL; positive = the adjustment helps) |
|---|---|---|---|
| 2019 | +0.20 [−0.22, +0.61] | +0.20 | (fit year) |
| 2020 | −0.01 [−0.46, +0.44] | −0.01 | −0.03 [−0.50, +0.44] |
| 2021 | −0.05 [−0.22, +0.12] | −0.01 [−0.18, +0.16] | −0.04 [−0.40, +0.31] |
| 2022 | **+0.15 [+0.03, +0.27]** | +0.15 [+0.04, +0.27] | +0.16 [−0.01, +0.33] |
| 2023 | −0.05 [−0.14, +0.04] | −0.05 | **−1.26 [−2.63, +0.10]** |
| 2024 | +0.02 [−0.06, +0.09] | +0.02 | +0.00 [−0.48, +0.49] |
| 2025 (holdout, exposed) | +0.08 [−0.04, +0.19] | +0.08 | +0.32 [−0.14, +0.78] |
| 2026 to 28 Jul (holdout, exposed) | **+0.10 [+0.00, +0.20]** | +0.10 | **+0.73 [+0.09, +1.38]** |
| **Pooled 2019–2024** | +0.030 [−0.020, +0.080], tie | +0.032 [−0.017, +0.081], tie | |
| **Pooled 2019–2026** | **+0.050 [+0.013, +0.086]** | **+0.051 [+0.015, +0.086]** | |

**Do the seasons share one effect?** Not quite.

| | Through 2024 | Through 2026 |
|---|---|---|
| Cochran's Q | 10.6, 5 df, p = 0.06 | 14.2, 7 df, p = 0.047 |
| I² | 53% | 51% |
| Between-season SD (τ) | 0.063 | 0.055 |
| Random-effects mean | +0.024 | +0.044 (backfill +0.049) |
| A new season's effect, 95% predictive range | [−0.17, +0.21] | [−0.10, +0.19] |
| Share of seasons below 0 | 38% (backfill 34%) | 25% (backfill 22%) |

**What that predicts for the next season** *(inferred: a second-order expansion of log loss, normal approximation, men)*:
* **The rule.** Adding b̃·z gains when the season's true effect exceeds b̃/2. Its size is about 1000·k·(b̃β − b̃²/2), with k = mean p(1 − p)z² = 0.24.
* **2027, with b̃ 0.0444 and the 2019–2026 evidence:**
  * expected **+0.28 mLL per men's match** (+0.23 without the backfill);
  * −1.2 to +1.8 at the predictive range's ends;
  * **probability of a losing season about 33%** (36% without).
* **2025, from 2019–2024 evidence alone:** +0.10 (+0.06), probability of a loss 40% (44%).

**Reading** *(inferred)*.
* **The signal looks real but small and unsteady.** Pooled over eight seasons, the faster-trending man wins more than the model says. Season to season, the effect swings by as much as its mean.
* **The adjustment's value comes from many seasons, not any one.** In a single season the chance of a loss is about one in three.
* **2023 is the warning.** The coefficient fitted on 2019–2022 (b̂ 0.11, shrunk to 0.07) met a season whose effect was negative, and lost 1.3 mLL per men's match. From 2024 the fit uses more seasons and settles near 0.03–0.04.
  * Process suspects for the swings: the measuring-system breaks inside seasons (AO 2024 reads about 3 km/h fast, Wimbledon 2025 +8.5 km/h), which the as-of offsets absorb only partly; and the speed sources' coverage changing over the years.
* **What the backfill adds to this.** It nudges every estimate a few percent in the feature's favour. 2021 moves from −0.05 to −0.01, and the 2027 loss probability from 36% to 33%. With speeds at only three events of 2021, it cannot settle the question.
* **What can settle it.** Seasons with dense tour-level speeds: 2022 onward, and each prospective season.

## 6. Looks at the proposed clean holdout

The [clean-holdout proposal](../clean_holdout_rebuild/README.md) (not approved) keeps 2025–2026 out of model choices.
* **The decision-relevant comparison (§4.1) read results through 2024 only.**
* **This study's exploratory comparison read 2025 to 28 Jul 2026 twice:**
  * a first version of `compare.py` that scored 2022–2026, before the protocol was found;
  * the labelled `--through 2026` run behind §5.
* **That is H-exposed,** which earlier studies have read about 20 times.
* **No H-sealed match was read.** The speed columns end with the events of 28 Jul 2026.
* **No choice here was made on those seasons:** the integration follows the owner's instruction and the 2020–2024 comparison.

## 7. Limits

* **Small by nature.**
  * 184 timed matches of 2018–2021, about 110 new to the history.
  * The point data of 2019–2020 carry no speed.
  * 43 of the 52 events of 2021 hold no point.
* **The decrypted 2018–2020 files were rewritten by the host in 2026** (their plain `lastModified`). They are what it served on 8 Oct 2026, and their values match the Hugging Face copy taken years earlier.
* **Tests.** Of the five affected suites (this study, both serve-speed studies, the data map, the current best model), 291 tests pass, the 35 new ones among them.
  * **Three fail for reasons older than this work.** The Stage 0 rebuild of 8 Oct changed what they compare: the match count, a corrected box score used by a nowcast, and the 2026 timeline.
  * **One live-panel test was adapted.** It assumed the live history equals the corrected copy row for row. It now checks both histories for the audit's exclusions, and checks that the backfill keeps every corrected player-match.
* **Women:** no ATP file concerns them.

## 8. Options (not decisions)

1. **Add the source to the shot-level point tables** (`stage0_sources.py`, `points.py --only infosys_atp`) for point-level studies of 2019–2021 tour matches.
   * Gain: about 340 matches with every point that no other source holds.
   * Use the code-and-round links, not names.
2. **The TabPFN speed-column refit** on the rebuilt frame (seeds 0–3, 2022–2024, about 15 GPU minutes). Run it only to confirm the tie §4.2 predicts.
3. **Remove the duplicate** `data/studies/infosys_atp_backfill/speed_panel_augmented.parquet`. It is byte-identical to the live file, and was kept only because files are not deleted mid-session.
4. **The question this study cannot answer** is whether the speed adjustment's gain holds. The prospective test registered for matches after 7 Oct 2026 can, with the daily collector's speeds.

## 9. Files and reruns

| What | Where |
|---|---|
| Code | `src/ingest/point_sources/infosys_atp_stage.py`; `src/eda/infosys_atp_backfill/`: `checks.py`, `history.py`, `columns.py`, `coverage.py`, `live_check.py`, `compare.py` |
| Changed elsewhere | `src/eda/serve_speed_acquisition/speeds.py`, `src/eda/serve_speed_tabpfn/panel.py`, `src/eda/serve_speed_tabpfn/live/live_panel.py`, `src/eda/data_map/measure.py`, `build.py`, `data/data_map.yaml` (and the rebuilt `data/data_map.html`); docstrings in `src/eda/model_rebuild/speed_columns.py` and `live/common.py`; one test in `test/serve_speed_tabpfn/test_ssp_live_form_panel.py`; notes in the current-best-model and scraping decisions, their index, the acquisition study and `CLAUDE.md` |
| Tests (35) | `test/infosys_atp_backfill/` |
| Evidence | [data/studies/infosys_atp_backfill/](../../../data/studies/infosys_atp_backfill/README.md) |

```
./python.sh -m src.ingest.point_sources.infosys_atp_stage           # staged tables (about 30 s)
./python.sh src/eda/serve_speed_acquisition/speeds.py               # per-player speeds and the acquisition's checks (about 3 min)
./python.sh src/eda/infosys_atp_backfill/checks.py                  # checks A-H
./python.sh src/eda/infosys_atp_backfill/history.py                 # the live history with the backfill
./python.sh src/eda/infosys_atp_backfill/columns.py                 # the adjustment's columns on it (about 1 min)
./python.sh src/eda/infosys_atp_backfill/coverage.py
./python.sh src/eda/infosys_atp_backfill/live_check.py
./python.sh src/eda/current_best_model/compare.py --candidate reference --speed data/studies/infosys_atp_backfill/speed_columns_augmented.parquet --out data/studies/infosys_atp_backfill/vs_reference_2026-10-08
./python.sh src/eda/infosys_atp_backfill/compare.py [--through 2026]
./python.sh -m pytest test/infosys_atp_backfill -q
```

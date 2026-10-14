# P7: the ITF box-score test, and how women's lower-level evidence is treated — an executable plan

10 October 2026 · Role G (P7 test planner) of the level-evidence system · **A plan, not a decision.** The lead turns
it into P7's own dated pre-registration (draft in Appendix A) before any P7 arm is built; the owner decides what the
readings recommend.

**The owner's request** (9 Oct): "If the data doesnt exist, to build a plan to do this test when it does."

**What lands** (`docs/studies/gap_downloads/collection-plan.md:310-341`; `team/04_incoming.md` §2–3): SofaScore's ITF
main-draw box scores (package P7), first 2025–26 (about 17–18 Oct), then 2018–2024 (about 31 Oct – 2 Nov; about 22 Oct
at the faster pace), then TennisLive's ITF pages (P8, early–mid November). About 197,000 box scores for ITF matches
Stage 0 holds as results only. 69% of women's model matches have such a match in a player's previous year, against 9%
of men's.

**Keys.** *Observed* = read in code (`path:line`) or computed here (file cited; G's scratch outputs are in
`data/studies/lower_level_evidence/system/p7_plan/`, written `p7_plan/`). *Inferred* = reasoning. *Suggestion* = a
proposal: every step below is a Suggestion until the lead adopts it. `system/` = `data/studies/lower_level_evidence/system/`.
Scores are mLL per match; **+ = the first-named model has the lower log loss (better)**; "better" or "worse" only when
the 95% interval clears 0, otherwise "unresolved" with P(better) = Φ(estimate / SE). Never "tie". Commands run from the
repository root with `./python.sh` (GPU fits with `./python_tabpfn_local.sh`, role D only).

---

## The checklist (one page)

Dates are estimates at the logged pace and slip if the PC sleeps or SofaScore blocks. "Day 0" = the day P7's 2018–24
gap passes the trigger check. Every command is in the section named.

| Step | When | What | Pass, or the decision | Whose call |
|---|---|---|---|---|
| **C0** | before P7 lands | This run finishes CP2 and CP3 (SELECTED written; holdout read once). The code changes of §10 are made, tested and hashed | §10 tests pass; IDENTITY_ALL G1 still passes if the layer changed (§5) | the lead |
| **T1** | ≈ 17–18 Oct | P7's 2025–26 gap lands: trigger check (§1.2); **counting calibration** of SofaScore's ITF counts against the official ones (§2.3); rehearsal build `C0_P7a`, no arm (§1.3) | calibration table written; decision D-CAL | **the lead** (D-CAL) |
| **T2** | ≈ 22 Oct – 2 Nov | P7's 2018–24 gap lands: `p7_trigger_check.py --gap itf_detail` | exit 0 (complete, yield, links) | the lead if it fails |
| **W1** | day 0, 0–2.5 h | F builds `C0_P7` and `C0_P7ctl` and runs `--checks` (§2.1, §2.4, §2.5) | both `checks.json` pass; history: dropped 0, future 0 | — |
| **W2** | day 0, 2.5–4 h | Hand checks (§2.2); **expected unevenness written and hashed** (§2.6); E re-audits (§2.7); `--ready` ×2 | thresholds of §2.2; hash posted before any arm | — |
| **P0** | day 0, ≈ 4 h | **P7 pre-registration** hashed by the lead (Appendix A): arms, configs, readings, decision guidance, D-δ and D-CAL settled | `preregistration_P7.md` + `.sha256` exist | **the lead**; the owner if the arm set changes |
| **A1** | day 0, 4–8 h | Build P7_ASIS and P7CTL_ASIS (two sandboxes) (§4) | gates of §5 | — |
| **R1** | day 0, ≈ 5–8 h | P7_ASIS's Stage 1 → strength file; γ check; A's ITF δ levels (D-δ); B's refit on C0_P7 (§3) | ITF fitted from season_used 2020; γ inside its interval; fit_through ≤ cutoff | the lead if ITF is not fitted |
| **R2** | day 0, ≈ 8 h | B's P7 freeze and 2025–26 rows; P7 addition 1 hashes `params_P7` (§3.5) | hashes recorded | the lead |
| **A2** | day 0, 8–12 h | Build P7_SYS_EXCL and P7_SYS_ITF (and SEL_BOTH if CP2 did not keep SYS) | gates of §5, leak probes included | — |
| **F1** | as each arm is READY | D: frame check, input check (part 1) against §2.6, then 32 fits per arm | frame and provenance checks | — |
| **S1** | day 0, ≈ 14 h | The pre-registered readings on 2020–2026, labelled non-clean (§6.1); B's statistic-level pair (§3.6) | — | — |
| **E3** | day 1 | E re-derives the headline numbers | — | — |
| **D1** | day 1–2 | Women's and men's treatment (§7), written; the forward test frozen on that day (§6.2) | — | **the owner** |
| **P8** | early–mid Nov | P8 lands: rebuild the chosen configuration on `C0_P8` as a candidate, input check; the full arm set again only if the lead asks (§1.4) | no unexpected "uneven" input | the lead |
| **FW** | from D1 (first forward match: the 2027 season) | Forward test: harm looks after 800 and 1,600 scored women's matches; the first clean reading after 2,400 (≈ the 2027 season) (§6.2–6.3) | harm (worse by > 0.10 mLL, whole 95% interval below 0) reverts W*; the reading at 2,400 | **the owner** |

---

## In short

* **The test** (Suggestion). Four new arms on the two P7 Stage 0s, read against REF and the system on both tours: the
  template with the new data as equivalent (P7_ASIS, "no rule of 8 October"), the same without SofaScore's ITF
  (P7CTL_ASIS), the system with ITF box scores excluded (P7_SYS_EXCL, today's system rule) and the system with them
  translated and weighted by their own walk-forward parameters (P7_SYS_ITF). A share control (P7_S2) is optional: the
  owner's decision re-files the share inputs as a feature-pool lead (§4.3).
* **Readiness** (Observed, §9). F's builder, its control flag, the strength writer and B's ITF-ready rule exist and run.
  A code check of B's estimator on C0_now (the ten SofaScore careers' men's ITF box scores) turned men's ITF "fitted"
  at season_used 2022 and not 2021, exactly as the two-season rule says, and left γ equal to the frozen γ. **Six code
  paths are missing** before P7_SYS_ITF can be built and scored: the layer has no "fitted" ITF mode, C2's solves bar an
  ITF level term, B's freeze and 2025–26 rows are tied to the frozen run's files, A's decomposition has no ITF level,
  C1's arm list knows no P7 arm, and the run's scorer refuses after the unlock (§10; guarded by six xfail tests).
* **Seasons** (Observed in B's code; Inferred for P7's counts). With ITF box scores from 2018, ITF is fitted from season_used 2020; ITF rows dated
  2018–2019 keep w = 0 under the own-season convention, so the ITF entry acts from 2020 and fully from 2021. ITFQ is
  never fitted (P7 skips qualifying).
* **A new integrity risk** (Observed). SofaScore splits first and second serves differently from the official feed:
  46–83% exact agreement for first serves in on ATP rows (`docs/studies/data_continuity/README.md:247-258`), and 78.9%
  (SofaScore higher by 0.88 per player-match) on 514 lower-level matches before 2025 in G's dry run. P7's 2018–24 ITF
  box scores are SofaScore's, most 2025–26 ones Sackmann's (official): uncalibrated, a counting step at 2025 in the
  first-serve statistics. Measured on the 2025–26 ITF overlap before any arm; decision D-CAL (§2.3).
* **No holdout is left; the decision layer is the owner's** (Inferred; addition 4). This run's CP3 spends 2025–2026.
  Under the owner's decision of 9 October the women's route is set by B's statistic-level evidence, and P7's
  model-level readings on 2020–2026 (pre-registered, non-clean) are the harm check: worse by more than 0.10 mLL with
  the whole interval below 0. A forward test from the decision day is the holdback (§7).
* **Forward-test sizing** (Inferred from E's and D's resolution numbers, §6.3). A women's match carries σ ≈ 4.4–5.8 mLL
  of paired noise; a season holds about 2,400 women's matches. Resolving ±0.10 mLL with 80% power needs ≈
  15,000–26,000 of them (6–11 seasons); a 0.30 mLL harm ≈ 1,700–2,900 (0.7–1.2 seasons). **Minimum: one full season
  (2027, about 2,400 matches), which resolves only |δ| ≳ 0.25–0.33 mLL.** The forward test is a harm guard, not a proof
  of a small gain.
* **Compute** (Inferred, §8). Four chain builds (two sandboxes reused, ≤ 3 builds at a time), B's refit ≈ 2 h, 128
  fits ≈ 1.5–3.5 h of GPU. Critical path ≈ 13–16 h from P7's landing to the readings, most of it F's build and hand
  check, B's refit and one chain build.

---

## 1. The trigger: has P7 landed, completely?

### 1.1 What lands, where, and the counts to expect

*Observed* (`collection-plan.md:310-341`, `team/04_incoming.md` §2–3, the P6 runs' files in
`data/studies/gap_downloads/`):

| Gap | Content | Targets | Requests | Expected |
|---|---|---|---|---|
| `itf_points_2025_2026` (first) | ITF main draws 2025–26, both tours, points and box scores | ~55,416 on 8 Oct (men 24,234, women 31,182), more once P4's listings since June 2026 are targets | ~150,000 | unmeasured (the block stopped the count); 96% of the 49,180 Stage 0 matches it reaches already hold Sackmann's box score; 13,862 targets Stage 0 lacks |
| `itf_detail` (second) | ITF main draws 2018–2024 | 205,872 frozen (Stage 0 matches results-only: men 100,311, women 101,896) | ~440,000 | box scores ≈ 98% (84 sampled), complete points ≈ 93%; 2018 the weakest year (Hungary F1 2018: 23 of 31) |

Where it lands:
* staged tables `data/dump/points/sofascore_editions/{events,statistics,points}.parquet` (+ `.meta.json`); ITF events
  carry `category_name` "ITF Men" / "ITF Women" (`candidate_stage0.py:839`);
* per gap, in `data/studies/gap_downloads/`: the frozen targets `sofascore_<gap>_matches.csv.gz` (one row per target:
  `event_id`, `stats_status`, `stats_full_box`, `pbp_verdict`), the link check `sofascore_<gap>_link_check.json` and
  `.csv` (verify_links.py), the summary `sofascore_<gap>_summary.json`;
* the run log `data/studies/gap_downloads/runs.jsonl` (one line per run: `stopped`, fetch outcomes) and
  `data/raw/point_sources/sofascore_editions/_logs/run_<UTC>_<gap>.log`, receipts `_receipts.jsonl`.

The collector's own closing steps (`collection-plan.md:332`) are verify_links, staging, the map rebuild and
`match_timing/refresh.py --sources sofascore`. The candidate Stage 0 does not read the live timeline (F §8), so the test
does not wait for that refresh; but F's builder must not read the staged files while the collector or a staging run is
writing them.

### 1.2 The check

1. **No collector is writing** (`collection-plan.md:57`), in PowerShell:
   `Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Select-Object ProcessId, CommandLine` shows no
   `sofascore_editions`.
2. **Complete, with the expected yield** (G's script, written now so the thresholds predate the data):
   ```
   ./python.sh data/studies/lower_level_evidence/system/p7_plan/scripts/p7_trigger_check.py --gap itf_detail
   ./python.sh data/studies/lower_level_evidence/system/p7_plan/scripts/p7_trigger_check.py --gap itf_points_2025_2026
   ```
   Exit 0 = landed. It writes `p7_plan/trigger_<gap>.json` and requires:
   * **complete:** every linked target has a statistics outcome (200 or 404), and the gap's summary
     (`sofascore_<gap>_summary.json`) shows a finished last run, not `stopped` (the lines of `runs.jsonl` do not name
     their gap);
   * **yield:** box scores on ≥ 90% of the targets of every tour-year 2019–2024, ≥ 75% in 2018; ≥ 80% for the 2025–26
     gap (the collection plan's stop rule);
   * **links:** verify_links "agrees" on ≥ 98% of linked targets; "winner differs" ≤ 0.1%.
   Rehearsed on the finished P6 gap `challenger_points_2025` (§9): 14,675 targets, 14,608 linked, every one fetched,
   14,541 box scores (98.9% in 2025, 99.5% in 2026), links ok: "landed", exit 0 (`p7_plan/trigger_challenger_points_2025.json`).
3. **If the yield fails** (Suggestion): stop and report to the lead. A tour-year far below the others is a coverage
   step the input check will read as "uneven"; the lead decides whether to wait for P8 or drop that year's SofaScore
   ITF box scores (a builder option, §10).

### 1.3 If only 2025–26 has landed

*Inferred.* No ITF parameter can be fitted: women hold ITF box scores only in 2022 (29) and 2025–26, men only the ten
SofaScore careers' 55–285 a season (2016–24) and 2025–26 (`p7_plan/c0now_itf_box_counts.csv`). B's rule needs two
seasons of 100+ in the fit window, so women's ITF is never fitted for a season ≤ 2026, and men's only from 2022 on a
sample selected by player (E S9), which is no basis for a decision. So no P7 arm is built for scoring. Do three things:
1. **The counting calibration** (§2.3) on the 2025–26 overlap, after this run's CP3 (the 2025–26 box scores are then
   spent). It is the only place to measure SofaScore's ITF counting against the official ITF box scores before its
   2018–24 box scores are trusted (`collection-plan.md:329-331`).
2. **A rehearsal**: F builds `C0_P7a` with the same commands as §2.1 (label `C0_P7a`), runs `--checks`, and stops:
   no hand check, no READY, nothing downstream. It times the build on SofaScore's ITF volume and finds linking problems
   two weeks early.
3. **Wait** for the 2018–24 gap. Nothing in this test is decided on 2025–26 ITF box scores alone.

### 1.4 P8 (TennisLive's ITF pages)

*Observed.* P8 fetches pages for the ITF main draws 2019–26 SofaScore lacks (~7%, ~19,000), with 8 of the 9 counts
(no service-game count, Stage 0's `no_svgms`; F §2), and ITF qualifying only if P4's sample says most pages carry
points (`collection-plan.md:345-357`).
* *Suggestion:* do not wait for P8. Run the test on `C0_P7`. When P8 lands, build the chosen women's configuration on
  `C0_P8` (= C0_P7's sources plus P8) as a candidate and read its input check and its scores against the same
  configuration on C0_P7; re-run the full arm set only if a new input reads "uneven" outside the written expectation or
  the lead asks.
* *Observed caveat for any P8-era control:* `--sofascore-skip` removes SofaScore's ITF events only
  (`candidate_stage0.py:871`). TennisLive's pages come later in the box priority (`:121`), so in a control built after
  P8 they would complete the very ITF matches SofaScore was skipped for. A P8-era control needs a box-layer level skip
  (§10, F).

---

## 2. Wiring: C0_P7 and its control C0_P7ctl

### 2.1 The builds

```
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7 --checks
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7ctl --sofascore-skip "ITF Men,ITF Women"
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7ctl --checks
```
* One heavy process at a time (F §9): about 35–60 minutes per build and 25–40 per check on the shared machine (F's
  estimate for P7's ~270,000 SofaScore events to link). Outputs in `system/stage0/<label>/`. The round union runs inside
  the build (F §5). The builder refuses a label already marked READY (`candidate_stage0.py:2595-2596`).
* **What the control is** (*Observed*, `candidate_stage0.py:841-873`): `--sofascore-skip` drops every SofaScore event of
  those categories from all three SofaScore collections, so `C0_P7ctl` also lacks the ten careers' 1,450 men's ITF
  completions that C0_now holds. `C0_P7` minus `C0_P7ctl` = all SofaScore ITF box scores (P7's and the ten careers'),
  plus the few ITF matches only SofaScore lists. The count left out is `left_out_by_category_option` in
  `build_record.json`.

**What `checks.json` must show, for each** (`candidate_stage0.py:2387-2419`; F §5):

| Check | Pass |
|---|---|
| `structure.pass` | true: every reference match present, facts unchanged; `has_box` changed only where a completion was applied; new-match ids of the other tour 0; season/holdout disagreements 0; `new_windows_disjoint_from_the_frozen_round` 0; the frozen timeline's rows identical |
| `duplicates` | same pair twice in a tournament 0; same pair within 3 days in two tournaments 0; a player twice in a round 0 |
| `history` (§2.4) | dropped 0 and future 0 (`history_ok`, `:2412`); updated 0; revised = the applied completions on reference matches |
| `repair_tables` | would remap 0 new-match player rows |
| counts (Inferred, to compare, not gates) | C0_P7: completions ≈ C0_now's 1,644 plus ≈ 190,000–197,000 SofaScore ITF 2018–24; C0_P7ctl: completions ≈ 1,644 − 1,450 ≈ 200 plus whatever P1, P5, P6 added; new matches ≈ C0_now's 298,008 plus P1 and P4 growth since 9 Oct |

### 2.2 The identity hand checks

The builder draws the samples (`identity_samples`, `candidate_stage0.py:2258`, 20 per source and route, seed
20261009; `repair_moves_sample` `:2342`): `identity_sample_{links,players,new_ids,repair_moves}.csv` in each folder. A
person (or a session) writes `identity_verdicts.csv` (columns `kind, source, route, row, verdict, note`; verdict
`right`, `wrong` or `unsure`) after F's procedure (F §5); `--ready` refuses without it (`:2448`) and writes
`identity_precision.csv` (Clopper–Pearson bounds, `:2421-2438`).

**What matters for P7** (*Inferred*): P7's bulk are completions of reference matches, so a wrong **link** puts another
match's box score on a reference match; player resolution is the reference's. Thresholds fixed now (Suggestion):
* SofaScore links: 0 wrong of 20 (any wrong link stops READY until F finds the cause);
* players: at most 1 wrong per (source, route) sample, and none in the crosswalk route;
* new ids: splits allowed (F's namesake rule), merges not;
* **swapped sides** (new for P7): among SofaScore ITF completions, the share whose winner won under 45% of the points
  must be ≤ 0.1% (F's TennisLive rule, F §4). Seasons ≤ 2024 are allowed; 2025–26 only after CP3.

### 2.3 SofaScore's counting against the official ITF box scores (decision point D-CAL)

* *Observed* (`docs/studies/data_continuity/README.md:247-258`): on ATP rows, SofaScore's first serves in agree exactly
  with Sackmann's in 83% (2024), 46% (2025) and 61% (2026) of player rows, higher by 0.4–0.7 per player; break points
  faced 99%, 70%, 50%; aces, double faults and service games 80–100%. "It cannot stand in for first serves in or break
  points without a calibration."
* *Observed* (F §2, the box layers): where Stage 0 already holds a box score, a SofaScore box score is a **revision**,
  counted, not applied; where Stage 0 has none, a **completion**, applied. So C0_P7's ITF box scores are SofaScore's for
  2018–2024 and mostly Sackmann's (official umpire data) for 2025–26.
* *Inferred:* uncalibrated, a counting difference puts a step at 2025 into every input that reads first serves in or
  break points from ITF rows (first_in, first_won, second_won, bp_saved, bp_faced_pg, bp_conv and their defence
  mirrors) — the "uneven" shape — and into B's ITF parameters, fitted on SofaScore counts and applied to official ones.

**The measurement** (G's script, written now; counting only, two sources of one match compared):
```
./python.sh data/studies/lower_level_evidence/system/p7_plan/scripts/sofascore_calibration.py \
    --candidate data/studies/lower_level_evidence/system/stage0/C0_P7 --levels ITF --max-year 2026 \
    --out data/studies/lower_level_evidence/system/p7_plan/calibration_C0_P7_itf.csv
```
It reads `box_layers.parquet` (kind `identical` or `revision`, source `sofascore`) and gives, per count, tour, level and
year, the share exactly equal and the mean and SD of SofaScore minus official. Run it on `C0_P7a` at T1 (after CP3),
again on `C0_P7`.

**The dry run already points at the problem** (*Observed*, `p7_plan/calibration_C0_now_pre2025.csv`; C0_now's SofaScore
box scores of matches Stage 0 also holds, seasons 2019–2024, 514 matches, 1,028 player rows, almost all Challengers and
their qualifying; no ITF row is comparable before 2025):

| Count | Exact agreement | SofaScore minus official, per player-match | The plan's rule |
|---|---|---|---|
| first serves in | 78.9% (Challengers 81.7%, their qualifying 76.9%, Slam qualifying 40.5%) | +0.88 | fails |
| first-serve points won | 82.2% | +0.45 | fails |
| second-serve points won | 83.9% | −0.41 | fails |
| serve points | 93.4% | +0.11 | passes |
| aces, double faults, service games, break points faced and saved | 96.1–98.2% | −0.06 to −0.01 | pass |

*Inferred:* SofaScore moves serve points from the second serve to the first (first-serve won +0.45, second-serve won
−0.41: their sum, serve points won, barely moves). If ITF behaves the same, the statistics built on the first-serve
split (first_in, first_won, second_won, rpw_first, rpw_second, def_first_in) need D-CAL; serve and return points won,
holds, breaks, aces and double faults do not. SofaScore's ITF statistics may come from the ITF's own umpire feed
(`team/04_incoming.md` §5) and agree better.

**Two eras, two overlaps** (*Inferred*). SofaScore's counting changed with time: break points faced agreed in 2024 and
not from 2025 (data continuity §3.3), while the dry run's pre-2025 rows pass. So the 2025–26 ITF overlap may misdescribe
SofaScore's 2018–24 ITF records, which have no official counterpart (Stage 0 holds 29 women's ITF box scores of 2022 and
none for men). Read both before D-CAL: the ITF overlap by year (the command above), and the pre-2025 lower-level overlap
on the same build (`--levels TQ,GSQ,CH,CHQ,ITF --max-year 2024`). A count counts as calibrated only where both pass.

**The rule, fixed now** (Suggestion): a count passes when, over the ITF rows compared, exact agreement ≥ 90% and
|mean difference| ≤ 0.25 per player-match. **D-CAL, the lead, before P7's pre-registration**, if a count fails:
1. *(recommended)* **the system arms leave out the ITF rows of the statistics built on a failing count**: an exclusion
   list in the layer config under `itf_box` "fitted" (part of change #1 in §10), for example first_in, first_won,
   second_won, rpw_first, rpw_second and def_first_in, with the joint solves of those statistics dropping their ITF
   rows (m = 0). Serve and return points won keep their ITF rows (the sum passes). The template arms take the data as
   it is: that is the no-rule counterfactual, flaw included.
2. F's builder sets the failing counts of SofaScore completions missing (a per-count mask, §10): every arm sees only
   usable counts, but a missing first_won or second_won also loses serve points won, which passes.
3. As it is everywhere, the step named in the expected unevenness.
P7_ASIS and the system arms are built on the same Stage 0 whatever is chosen, so the rule-of-8-October readings
compare like with like.

### 2.4 `history.py`

Run inside `--checks` (`candidate_stage0.py:2117`); by hand:
```
./python.sh src/eda/current_best_model/history.py --stage0 data/studies/lower_level_evidence/system/stage0/C0_P7 \
    --timing data/studies/lower_level_evidence/system/stage0/C0_P7/timing.parquet
```
(flags at `history.py:169-170`). **Pass:** future 0, updated 0, dropped 0; new past = the build's new matches; revised =
the applied completions exactly (C0_now: 1,644 = 1,644); "template refused" (it must be, for a candidate). *Observed
caveat* (`team/04_incoming.md` §2): history.py compares Stage 0 facts and box scores, not the timeline, so §2.5 checks
the clock separately.

### 2.5 The clock

* C0_P7's `timing.parquet` holds the frozen timeline's row for every reference match, unchanged, and a window for every
  new match (F §3: the source's own day widened by its measured clock error, else the frozen class window; the union
  rule for a row joining a Stage 0 tournament). Completions move no window.
* **Pass** (in `--checks`): every new window finite with `lf ≥ es`; `new_windows_disjoint_from_the_frozen_round` 0; the
  frozen rows identical in all columns; no new event's matches starting a week or more after its date.
* Never run `match_timing/refresh.py` in a P7 sandbox (F §8: it re-links live raw folders and could move reference
  matches' days).
* The cross-player features' leak probes run on the built P7 arms (§5, G5).

### 2.6 The expected unevenness: written and hashed before any P7 arm exists

The writer (F, or the session running P7) copies the draft below into `system/stage0/C0_P7/expected_unevenness.txt`,
replaces the bracketed numbers with C0_P7's own `dose.csv` (written by `--checks`, `candidate_stage0.py:2210`), hashes
it into `expected_unevenness.sha256` and posts a status line, **before any P7 arm is built**; it is never revised once an
arm exists (F §7's procedure). *Inferred*, from the composition study's P7 scenario (`team/02_composition.md` §6:
women's lower-level share of box-score evidence +11 to +14 points at 365 days in 2019–2024, +6 in 2018 and 2025, +0 in
2013–2017 and 2026; up to +16 at the 52-week IOS memory; men +0.4 to +1.0, up to +2.5) and from F's C0_now
expectation:

| Arm against | Men | Women |
|---|---|---|
| **P7_ASIS vs P7CTL_ASIS** (SofaScore's ITF box scores as equivalent) | box-score inputs move a little from 2016 (the ten careers) and 2018 (P7): share +0.4 to +1.0 points; nothing flagged, perhaps the IOS products in 2019–2024 | **"uneven" by construction:** `points_52w`, `ios_points_short`, the 14 IOS ratings, the 7 products and `ratings_iid` flagged in 2019–2024, partly 2018 and 2025, not 2013–2017 or 2026; the products' scale up 5–15% from 2019 (finding #6's mechanism, moved back to 2018); the two-week forms' level up to ~0.10 SD in some seasons. The results family, odds, context and age: identical except where SofaScore-only ITF matches reach ([count]) |
| **P7_ASIS vs REF** | as NEW_ASIS vs REF (F §7) plus the row above | as NEW_ASIS vs REF (2026 workload counts flagged) plus the row above |
| **P7_SYS_ITF vs P7_SYS_EXCL** | from 2020 only (ITF rows of 2018–19 keep w = 0), smaller than the as-is change (translated, w ≤ 1); not flagged | box-score inputs flagged from 2020–2021 to 2025, not 2013–2019: the shape is the reading's subject, not a defect |
| **P7_SYS_EXCL vs SEL_BOTH** | as NEW_SYS_BOTH vs SYS_BOTH, plus the refit's parameters and the candidate's strength: every season moves a little (not uneven) | the same |
| Any D-CAL mask (§2.3) | the masked statistics' ITF-reading inputs: a step at 2025 for P7_ASIS if option 3 | named here if chosen |

Writing and hashing it (Git Bash, from the repository root; F's format: `<sha256> *expected_unevenness.txt`):
```
D=data/studies/lower_level_evidence/system/stage0/C0_P7
(cd $D && sha256sum --binary expected_unevenness.txt > expected_unevenness.sha256)
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) F expected unevenness written before any P7 arm: stage0/C0_P7/expected_unevenness.txt, sha256 $(cut -c1-12 $D/expected_unevenness.sha256)..." \
    >> data/studies/lower_level_evidence/system/status.log
```
C0_P7ctl's folder gets the same file and hash (it is read for P7CTL_ASIS's input check).

### 2.7 E's re-audit, then READY

E re-audits each folder before any arm (the lead's gate; `candidate_stage0.py:2480` writes it into READY.txt):
cross-tour ids 0; the windows; the residual identity classes against the frame (E's CP1b scripts
`system/audit/scripts/e_cp1b_checks.py` and `e_cp1b_residuals.py`, pointed at the new folder); the SofaScore link sample.
Then:
```
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7 --ready
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7ctl --ready
./python.sh -m pytest test/lower_level_evidence/test_candidate_stage0.py -q
```
`--ready` refuses unless `checks.json` passes and `identity_verdicts.csv` exists (`:2446-2448`), then writes
`manifest.json` (every file's SHA-256) and `READY.txt`. The chain refuses a folder without READY
(`system_sandbox.py:347-348`).

### 2.8 The pre-2025 twin: not built

*Inferred.* (1) The 2020–2024 readings of a C0_P7 arm equal those of its pre-2025 twin by construction: inputs of a
season-Y match read only earlier history, season Y's fit trains on 2013..Y−1, B's parameters are walk-forward, the
constants are pinned. (2) The twin's purpose in this run, a clean 2025–26 holdout separated from the publication-lag
fill, is gone once CP3 spends 2025–26. (3) C0_P7 against C0_P7ctl already separates P7 from every other addition. A
derived twin costs ten minutes (`candidate_stage0.py --label C0_P7_pre --derive-from C0_P7 --until 2024-12-29`, F §9)
and is useful only for counting; no arm is built on it. (Suggestion)

---

## 3. Re-estimating the relationship with ITF

### 3.1 Which seasons become eligible

*Observed* (`relationship.py:381-383`, `:427-454`; constants `:93-99`). Season_used Y's fit uses main-tour targets of
max(2011, Y − 6) .. Y − 1 with results in by Y's cutoff. A lower level is fitted when (a) at least 2 seasons in
Y − 8 .. Y − 1 hold ≥ 100 box-score matches at the level (counted per statistic, rows surely finished by the cutoff),
and (b) at least 30 fit targets have a row at the level in their 730-day history. Otherwise its row says `fitted` false,
w = 0. One rule for every level (B §8).

With P7's ITF box scores (≈ 14,000 men's and ≈ 14,500 women's ITF main-draw matches a season):

| season_used | ITF seasons with ≥ 100 box scores in the window | ITF fitted? |
|---|---|---|
| 2018 | none | no |
| 2019 | 2018 | no (one season) |
| **2020** | 2018, 2019 | **yes** (rule (b): women surely; men likely: 104 same-season ITF and main-tour anchors in 2018–24, `team/04_incoming.md` §4) |
| 2021–2024 | 3–6 seasons | yes |
| 2025, 2026 (the mechanical rows) | 2018–2024, plus 2025's official ITF box scores for 2026 | yes |

* **ITFQ:** never fitted. P7 skips qualifying; C0_now holds 4–23 men's and 2–8 women's ITFQ box scores a season before
  2026 (`p7_plan/c0now_itf_box_counts.csv`); P1 adds ITFQ only from September 2026. ITFQ rows keep w = 0 in every arm
  that reads B's weights.
* **The own-season convention** (*Inferred* from `level_layer.py`'s rule, C_layer §3): a row is translated and weighted
  with its own season's parameters, so ITF rows dated 2018 and 2019 carry unfitted rows (w = 0), as men's Challenger
  qualifying of 2016–17 does (E N3). P7_SYS_ITF admits ITF rows from 2020; a 2020 model match reads its 2020 ITF rows
  only; the full 365-day dose arrives in 2021. A floor rule for ITF (2020's parameters for 2018–19 rows) would hand a
  2019 model match parameters fitted on its own season's results: not allowed.
* **The dry run** (§9) showed the rule firing on real data. On C0_now, men's ITF holds 98, 199, 91, 170 and 285
  box-score matches in 2018–2022 (the ten SofaScore careers), so the count part first passes at season_used 2022 (2019
  and 2021). B's estimator then marked men's ITF `fitted` for 2022 and not for 2021; women's ITF stayed unfitted. Its
  free w for serve points won sat at the lower bound 0 (65 players, δ barred at ITF, one statistic so no shrinkage):
  a code check, not evidence, but a reminder that the fitted w can itself shut ITF out, and that a w at a bound enters
  B's shrinkage with its SE floored at 0.02 (`relationship.py:989-1010`), where it pulls the level mean hard. Report the
  ITF cells at a bound in the P7 refit.

### 3.2 The strength file

* *Observed:* B's `load` reads each side's pre-match Elo from `--strength` (`relationship.py:214-221`); a row without one
  is dropped from every statistic without a word (`:315`); only the dev step logs the count (`:1252-1253`).
* So the P7 strength must cover every C0_P7 match: C0_P7's own Stage 1 under the reference's K, which is P7_ASIS's
  Stage 1 (constants pinned), exactly as C1 makes NEW_SYS_BOTH's (`system_arms.py:263`, `system_new_arms.py:202-235`).
* **When:** P7_ASIS's lane 1 starts with Stage 1 (≈ 21 minutes, C_layer §5), after its lane 0 (≈ 30–60 minutes on the
  larger Stage 0). Then, while P7_ASIS's build continues:
  ```
  ./python.sh src/eda/lower_level_evidence/system_new_arms.py --strength --from C:/Users/zerom/tnr_sys<k> --name P7_C0_P7_elo
  ```
  **Pass:** the writer's checks (`system_new_arms.py:222-228`): no missing rating, every match before C0_P7's first new
  match equal to `strength_elo.parquet`; `arms/strength/P7_C0_P7_elo.parquet` and its `.sha256`.
* For B's optional statistic-level pair (§3.6), the same from P7CTL_ASIS's sandbox: `--name P7_C0_P7ctl_elo`.

### 3.3 What A's classes need

* **γ** comes from main-tour rows (`classify.py` `_main_rows`) and should not change; but it is read against the
  strength file, and C0_P7's Elo holds more lower-level results. B's estimator recomputes γ on the candidate
  (`relationship.py:789-805`: `gamma_by_season` passes the candidate's Stage 0 and strength to `classify.gamma`).
  **Check:** every (season 2013–2024, tour, statistic) γ in `params_P7` lies inside the frozen row's
  [`gamma_lo`, `gamma_hi`]; report the largest |Δγ| in SE units. If one is outside: report it and keep the recomputed
  γ (the candidate's own, consistent with its strength); the pre-registration fixes this now. In the dry run (C0_now,
  the frozen strength) γ came out equal to the frozen rows to every printed digit (serve points won: men −0.060323 and
  −0.060557, women −0.062520 and −0.062757 for 2021 and 2022): the candidate's main-tour rows are the reference's, so in
  the real run only the candidate's strength can move γ.
* **The classes (OPP, ENV)** come from the main tour: unchanged.
* **δ at ITF: decision point D-δ.** *Observed:* A's decomposition covers TQ, GSQ, CH and CHQ only
  (`classify.py:59`), so `delta_levels` never lists ITF. Then B holds δ_ITF at 0 (`relationship.py:776-787`), the layer
  applies none, and C2's form (b) never estimates an ITF level term (`level_layer_ios.py:286-300`). ITF rows would be
  translated by γ · gap alone — γ fitted inside the main tour and extrapolated across the largest gaps (B's caveat).
  **The lead decides, before P7's pre-registration** (Suggestion: option 1):
  1. *(recommended)* extend A's decomposition to ITF and ITFQ with A's frozen rule unchanged (`classes/thresholds.json`:
     ≥ 100 qualifying player-seasons, the residual clears 0 and reaches 0.10 SD_signal), on C0_P7's rows before 2025;
     write `system/classes_P7/classes.csv` (+ `.sha256`) in which only `delta_levels` may gain ITF or ITFQ, every other
     column equal to A's frozen table (checked). Needs A's code change (§10). *Inferred:* women's ITF residuals are
     identified (851 same-season ITF and main-tour anchors after P7, `team/04_incoming.md` §4); men's probably not (104).
  2. keep A's frozen table: δ_ITF = 0 everywhere. No change on A's side; the fallback if option 1 is not ready.

### 3.4 The commands

Run into a new folder; **never into `system/relationship/`** (B's frozen files).
```
P7=data/studies/lower_level_evidence/system/stage0/C0_P7
S=data/studies/lower_level_evidence/system/arms/strength/P7_C0_P7_elo.parquet
R=data/studies/lower_level_evidence/system/relationship_P7
./python.sh src/eda/lower_level_evidence/relationship.py --steps elo --stage0-dir $P7 --timing $P7/timing.parquet \
    --strength $S --out $R --work $R/work
./python.sh src/eda/lower_level_evidence/relationship.py --steps params --method F4 --boot 60 --workers 3 \
    --stage0-dir $P7 --timing $P7/timing.parquet --strength $S --out $R --work $R/work  [--classes <D-δ option 1's table>]
```
* `--method F4 --boot 60` **must be given**: the CLI defaults are F5 and 100 (`relationship.py:2071`, `:2068`); B froze
  F4 with 60 draws (`B_relationship.md` §7). The half-life grid stays the default 26, 52, 104, 208 weeks; a reduced
  grid must contain 52 (`:1631` reads the 52-week fit; the dry run's first attempt failed on `--h-grid 26`, §9).
* `--steps elo` writes `elo_w_results.csv` (w_results by the Elo grid, walk-forward) into `--out`; `--steps params`
  appends those rows (`:1875-1877`). Run elo first.
* Time: B's params step took 76 minutes with 3 workers on the loaded machine (B §7); ITF rows add work to every fit:
  allow 90–120 minutes.
* `--classes` does not exist yet: without it the frozen classes are read (`:1204`, §10).
* **The freeze and the 2025–26 rows: not as the code stands.** `--freeze` writes the module constant
  `system/relationship/method_freeze.json` (`relationship.py:90`, `:1924`) — B's frozen record — and `--mechanical`
  reads that file and then refuses because P7's `params_dev.parquet` differs (`:1932`, `:1948`). `frozen_inputs` also
  hashes the frozen strength and classes, not the ones the run used (`:1890-1896`). With the change of §10 (the freeze
  record under `--out`; the hashed inputs the ones actually read):
  ```
  ./python.sh src/eda/lower_level_evidence/relationship.py --freeze --method F4 --boot 60 \
      --stage0-dir $P7 --timing $P7/timing.parquet --strength $S --out $R
  ./python.sh src/eda/lower_level_evidence/relationship.py --mechanical \
      --stage0-dir $P7 --timing $P7/timing.parquet --strength $S --out $R     # writes $R/params.parquet, params.sha256
  ./python.sh -m pytest test/lower_level_evidence/test_relationship.py -q
  ```
  The mechanical path is still the only one that loads seasons after 2024 (`relationship.py:182-183`), and it keeps
  the walk-forward (2025 on results in by 29 Dec 2024, 2026 on results in by 3 Jan 2026). After CP3 "unread" protects
  no holdout any more, but the rows still come from frozen code.
* The cap: B's table stays uncapped; the configs cap fitted w, w_joint and w_results at 1 (`fitted_cap`, as in this run).

**What the output must show** (pass criteria, `relationship_P7/params_dev.parquet`, then `params.parquet`):
1. ITF rows `fitted` true for season_used ≥ 2020 for most statistics on both tours (a statistic short of 30 targets
   starts later: recorded, not changed); false for 2018–2019; ITFQ false everywhere.
2. Every row's `fit_through + 1 ≤` its season's cutoff (`season_first_es`), as E checked for B (E, "Checked and found
   correct").
3. The γ check of §3.3.
4. Every fit converged; every point estimate inside its bootstrap interval (B's `checks_params.json` checks, repeated).
5. A drift note, not a gate: per tour and non-ITF level, the median w over statistics against B's frozen 2019–2024
   bootstrap ranges (the new strength and data move them a little).

### 3.5 The freeze and the hashes

**P7 addition 1** (the lead; after §3.4, before P7_SYS_EXCL and P7_SYS_ITF are built) records the full SHA-256 of:
`relationship_P7/params.parquet` and its `method_freeze.json`; `arms/strength/P7_C0_P7_elo.parquet`; the class table used
(A's frozen `classes.csv` or `classes_P7/classes.csv`); `relationship.py`, `classify.py`, `level_layer.py`,
`level_layer_ios.py`, `system_sandbox.py`, `system_arms.py`, `system_new_arms.py`, `level_pins.py`, `system_gates.py`,
the P7 scorer and fit module (§10); C0_P7's and C0_P7ctl's `manifest.json`; `expected_unevenness.sha256`; the P7 arm
configs (`arms/configs_P7/MANIFEST.json`).

### 3.6 B's statistic-level reading: the route evidence for ITF

*Suggestion; required under the owner's decision* (§7: for an expansion, the statistic-level evidence sets the route;
the model-level readings are harm checks). The model-level readings are coarse (§6); B's predictor resolves far smaller
differences. Run B's dev step on both Stage 0s with the frozen method, then pair them per target:
```
./python.sh src/eda/lower_level_evidence/relationship.py --steps dev,tables --stage0-dir $P7 --timing $P7/timing.parquet \
    --strength $S --out $R/dev --work $R/dev/work
./python.sh src/eda/lower_level_evidence/relationship.py --steps dev,tables --stage0-dir <C0_P7ctl> --timing <C0_P7ctl>/timing.parquet \
    --strength <P7_C0_P7ctl_elo> --out <relationship_P7ctl>/dev --work <relationship_P7ctl>/dev/work
```
(≈ 25–35 minutes each, 3 workers.) Reading: the frozen method's per-target log-likelihood (`F6_F4`) on C0_P7 against on
C0_P7ctl, 2019–2024 targets, per tour and statistic group, player-clustered (B's `summarise`): "do ITF box scores,
translated and weighted, predict main-tour statistics better than none?" The pairing script is new (§10, B). Reads
2019–2024 outcomes only. **The route criterion** (§7, fixed now): per tour, the mean over the 19 statistics does not read
"worse" (its 95% player-clustered interval is not wholly below 0); each statistic group is reported beside it.

---

## 4. The arms

### 4.1 The arm set (pre-registered in Appendix A)

Every P7 arm on a candidate Stage 0 pins every tuned constant to the reference's, as NEW_ASIS does (addition 3 §4):
Stage 1's K and surface weight, the offset Elo's kd and Stage 3's constants (`level_pins.py`, from
`arms/constants/reference_constants.json`, sha256 `57bc4382…`); Stage B's by the layer's pin
(`stageB_adj_summary_reference.json`, `43429744…`); `IOS_CONSTANTS_VERSION=2026-10-08_reference`.

| Arm | Stage 0 | Config | Question |
|---|---|---|---|
| **REF** | frozen | `reference_2026-10-08/frozen/instance` (fits exist) | today |
| **SEL_BOTH** | frozen | SELECTED's config on both tours: **SYS_BOTH** if CP2 keeps SYS (built and fitted in this run); otherwise SELECTED's config with `tours ["atp","wta"]`, built like SYS_BOTH | the system for women, without P7 |
| **P7CTL_ASIS** | C0_P7ctl | the identity config + pins (= NEW_ASIS's, `system_arms.py:272-277`) | the day's data without SofaScore's ITF, template |
| **P7_ASIS** | C0_P7 | the identity config + pins | the day's data as equivalent: what happens without the rule of 8 October |
| **P7_SYS_EXCL** | C0_P7 | SYSCFG on both tours with `params_P7`, the P7 strength, `itf_box` "exclude" | today's system rule on the new data, parameters refitted by the frozen method |
| **P7_SYS_ITF** | C0_P7 | as P7_SYS_EXCL with `itf_box` "fitted" (§10) | ITF box scores translated and weighted by their own walk-forward parameters |
| P7_S2 (optional diagnostic, §4.3) | C0_P7 | P7_ASIS's frame + the two share inputs recomputed on C0_P7 | the share control |

* **SYSCFG** is SELECTED's frozen config when CP2 selected a SYS-family arm, and SYS's when CP2 selected REF or a share
  arm (the women's question is about the system; the share question is P7_S2's). If SELECTED is a dose arm, its number
  replaces "fitted" (and then applies to ITF rows too under "fitted" ITF); if SYS_NOCLASS, `classes` null and a
  no-class view of `params_P7` (B's `relationship_report.noclass_view`, which needs an `--out`, §10).
* **The parameter table** is `params_P7` for both system arms, so they differ only in `itf_box` (*Inferred*: the
  non-ITF parameters of the refit were fitted with ITF rows in the targets' histories from 2020; the shift is second
  order, and a separate refit without ITF would add a second difference to the pair).
* **Why the refit and not B's frozen table** (*Inferred*): the system is a method fitted walk-forward; on a new Stage 0
  its parameters are what the frozen code produces there (the renewal procedure, SPEC §11.6). The frozen table has no
  ITF rows to use.

### 4.2 The exact configs (level_layer schema, SPEC 6.3 plus C1's extensions; `level_layer.py:12-58`)

Paths below are relative to `system/`; the files are written with absolute paths by C1's config writer, as now.

**P7_ASIS** (P7CTL_ASIS: the same with its name):
```json
{"name": "P7_ASIS", "tours": ["atp", "wta"], "params": null, "params_sha256": null, "classes": null, "prior": "pool",
 "translate": false, "weight": 1.0, "weight_results": 1.0, "itf_box": "as_is",
 "families": {"points_52w": true, "forms": true, "ios": true, "ios_points_short": true, "ratings_iid": true, "elo": true},
 "strength": {"path": "classes/strength_elo.parquet", "sha256": "4fa9a573e7d0fbc34ab95f5f6c5efc97b835471a0f676bb5f14c182321c34d0d"},
 "pins": {"stageB_adjperf": {"path": "arms/constants/stageB_adj_summary_reference.json",
                             "sha256": "43429744425a89c43a1a119bc0e7620405d82ffd913a9f31c95bce3342ced271"}},
 "pin_constants": {"path": "arms/constants/reference_constants.json",
                   "sha256": "57bc438239160980723227d42a28ae152dd1fd83eecb8dc56efebdcd29adae6e"},
 "elo_count": "weighted", "record_dir": "arms/P7_ASIS/layer_calls"}
```

**P7_SYS_EXCL** (SYSCFG = SYS_BOTH's frozen config, `arms/configs/SYS_BOTH.json`, with three paths changed):
```json
{"name": "P7_SYS_EXCL", "tours": ["atp", "wta"],
 "params": "relationship_P7/params.parquet", "params_sha256": "<P7 addition 1>",
 "classes": "classes/classes.csv  (or classes_P7/classes.csv under D-δ option 1)", "classes_sha256": "<the table's>",
 "strength": {"path": "arms/strength/P7_C0_P7_elo.parquet", "sha256": "<its .sha256>"},
 "translate": true, "weight": "fitted", "weight_results": "fitted", "prior": "pool", "itf_box": "exclude",
 "families": {"points_52w": true, "forms": true, "ios": true, "ios_points_short": true, "ratings_iid": true, "elo": true},
 "params_season_floor": 2013, "missing_params": "untouched", "solve_w": "w_joint", "ratings_level_term": "none",
 "fitted_cap": 1.0, "fitted_cap_results": 1.0, "ios_level_term": "fixed_effect", "elo_count": "weighted",
 "pins": {"stageB_adjperf": {"path": "arms/constants/stageB_adj_summary_reference.json", "sha256": "43429744…"}},
 "pin_constants": {"path": "arms/constants/reference_constants.json", "sha256": "57bc4382…"},
 "record_dir": "arms/P7_SYS_EXCL/layer_calls"}
```

**P7_SYS_ITF**: P7_SYS_EXCL's with `"name": "P7_SYS_ITF"`, `"itf_box": "fitted"` and its own `record_dir`. Under
"fitted" (§10) ITF and ITFQ box rows are treated as every other lower level: translated by T = γ · gap + δ (δ only at
the levels the class table allows), weighted by B's fitted w (`w_joint` in the joint solves) of the row's own season,
capped at 1; an unfitted season or level reads w = 0 from B's row.

**Every tuned constant pinned to the reference's** (above), and the identity config for the template arms, so the data
and the layer are the only differences.

### 4.3 The share control: does the first run's lesson apply?

* **The lesson** (*Observed*, SPEC §2; the harness, `D_verification.md`): the first run's constant per-level offsets
  (FP) gained +0.083 mLL for men, and the share control R_S2 (the reference plus two lower-level share inputs) did as
  well (FP against R_S2 −0.003, P(better) 0.49). *Inferred there:* a constant offset per level is close to re-centring
  each input by the player's lower-level share, which TabPFN can learn from a share input.
* **Why it applies to P7, in part** (*Inferred*). ITF's dose is concentrated in identifiable players (women ranked
  101+, `team/02_composition.md` §6) and switches on by season (2018). A share input that counts ITF box scores tells
  TabPFN exactly whose inputs carry ITF evidence. If P7_SYS_ITF's gain over P7_ASIS were only "know who is ITF-heavy",
  P7_ASIS plus the shares would do as well, with no translation to maintain.
* **Why it may not** (*Inferred*). (1) The system's translation is per match (γ · the opponent's gap), not a constant
  offset; B measured per-match against constant offsets as better at the statistic level for women (+0.050
  [+0.038, +0.062]). (2) The share input is itself uneven by construction: before 2018 no ITF box score exists, so
  its meaning moves with the season, the same defect it would control for.
* **And the owner has since re-filed the share inputs** (*Observed*, `docs/decisions/2026-10-09-adoption-by-change-class.md`,
  "Re-filed by this decision"): the two box-score shares are a feature-pool admission as a lead (U-330), decided in a
  selection round, not by a pre-registered adoption. So P7_S2 decides nothing about the women's treatment.
* **Rule** (Suggestion): P7_S2 is **optional**, a diagnostic of the mechanism only (does the system's ITF translation
  do more than telling TabPFN who is ITF-heavy?). If the lead wants it: its pairs, women first, P7_SYS_ITF vs P7_S2 and
  P7_S2 vs P7_ASIS, expected unresolved (an arm that adds inputs reads with SE ≈ 0.10 mLL, E's table). The shares
  would be recomputed on C0_P7 with ITF box scores counted; `candidate_arms.share_inputs` reads the frozen Stage 0
  (`candidate_arms.py:101-107`, `:373-384`), so a P7 copy with a Stage 0 argument is needed (§10). 32 fits through D's
  60-input runner (`system_fits.py --fit60`); no chain build.

---

## 5. Gates

Each P7 arm passes these before D fits it (C1's `system_gates.py` with the P7 additions of §10):

| Gate | Arms | Pass criterion |
|---|---|---|
| **Layer identity** (before any P7 build) | the changed `level_layer.py` and `level_layer_ios.py` | C1's and C2's test suites pass; a new test shows `itf_box` "exclude" and "as_is" give bit-for-bit the frozen modules' outputs (26e21291, 3fa5f69e) on a real slice; **IDENTITY_ALL** rebuilt with the changed modules passes G1 (all 58 inputs exact on 67,226 matches) if a sandbox is free — else the slice test and the hashes are recorded and the rebuild follows |
| **Lane 0** | every C0 arm | `system_new_arms.py --lane0-check --sandbox D`: Stage 1's odds equal the frozen file in every column; the 67,226 frame matches unchanged in the candidate Stage 0 (run inside the build, `system_arms.py:707-713`) |
| **Identifiers and untouched** | every C0 arm | the NEW-arm gates (`system_gates.py:526-527`, `:589-611`): the same frame matches in order; identifiers and results through 2024 equal; the inputs no Stage 0 row feeds exactly the reference's |
| **Constants** | every arm | Stage 1, offset Elo, Stage 3 and Stage B constants the reference's (`constants_gate`) |
| **Invariance (G2-like)** | P7_SYS_ITF vs P7_SYS_EXCL | the Elo family, workload, odds, context and age **exactly equal on all matches** (ITF box scores touch no result); every input of a match before 2020 exactly equal (ITF rows of 2018–19 keep w = 0); box-score inputs exactly equal where no ITF box row of 2020 on is in reach (G2's reach sets with the ITF levels; the 21 surface-solver inputs within 1e-12, G2's one tolerance) |
| **Invariance** | P7_ASIS vs P7CTL_ASIS | the results family exactly equal except on matches a SofaScore-only ITF match reaches (counted); box-score inputs exactly equal before each tour's first SofaScore ITF box row |
| **Direction (G3-like)** | P7_SYS_ITF vs P7_ASIS | ITF rows are pulled toward main-tour terms: weaker opponents give T > 0, so a side's `points_52w` falls where its 365-day ITF box share rises. Required, per tour, 2021–2024: Spearman ρ between the change of `in_points_52w` (A − B) and the ITF box-share gap (A − B) below 0, its 95% interval below 0 |
| **Dose (G4-like)** | P7_SYS_ITF vs P7_SYS_EXCL | the share of matches changed and the mean absolute change rank with the tour-season's ITF box share (Spearman > 0) |
| **Leaks (G5)** | P7_SYS_ITF; P7_ASIS | from the arm's sandbox with `LLE_LAYER` = its config: `match_timing/probe.py` and `surface_ios/probe.py` (C2's procedure, `C_layer_ios.md` §7) and C1's real-date probe (`system_g5.py`, with a config and output option, §10): **0 protected matches moved at all four cuts**, the leaky control caught. The probe slice 2023–2024 holds ITF box rows, so the ITF path is exercised |
| **Lane 3 mapping** | P7_SYS_EXCL, P7_SYS_ITF | the pooled and surface IOS agree within 1e-12 (`surface_ios/arms.py:90`), with an ITF level term in form (b) under D-δ option 1 |
| **B's clock** | `params_P7` | `fit_through + 1 ≤` cutoff on every row; `test_relationship.py` passes |
| **Input check (part 1)** | every arm | compare.py's part 1 against REF and the arm's pair partner, read against §2.6 only after the expectation's hash exists; a flag outside the written expectation holds the arm until explained (D's frame check `unexpected_moves`, `system_fits.py:386-413`) |

Commands, per arm (after the build, from the repository root):
```
./python.sh src/eda/lower_level_evidence/system_gates.py --arm <ARM> --sandbox C:/Users/zerom/tnr_sys<k>
./python.sh src/eda/lower_level_evidence/system_gates.py --arm <ARM> --ready
(cd C:/Users/zerom/tnr_sys<k> && export LLE_LAYER=C:/Users/zerom/Documents/Tennis-predictions/data/studies/lower_level_evidence/system/arms/P7_SYS_ITF/layer_config.json \
    IOS_CONSTANTS_VERSION=2026-10-08_reference && \
    C:/Users/zerom/Documents/Tennis-predictions/python.sh src/eda/match_timing/probe.py && \
    C:/Users/zerom/Documents/Tennis-predictions/python.sh src/eda/surface_ios/probe.py)
```
(in a subshell, so no shell stays in the sandbox; the scripts are the sandbox's patched copies reading the sandbox's
tables, as C2 ran them, `C_layer_ios.md` §7; ≈ 13 and 22 minutes; `python.sh` only selects the project's interpreter).

---

## 6. Scoring, and the holdout problem

### 6.1 The readings on 2020–2026, labelled non-clean

*Why non-clean* (*Inferred*): 2020–2024 shaped B's method and this run's selection (E N1, N2); 2025–2026 are opened at
this run's CP3, before P7 lands. The P7 arms are written down before any P7 score, so the readings are not mined, but
the system they test was chosen on these seasons. Every P7 reading carries the label **"non-clean (pre-registered;
seasons seen by the system's design)"**.

* **Fits:** each P7 arm, seasons 2019–2026, seeds 0–3 (32 fits; season Y trains on 2013..Y−1): `model_rebuild/fits.py
  --out <arm folder> --seeds 0-3 --seasons 2019-2026 --wait-memory-only` through `./python_tabpfn_local.sh`, one fit at a
  time, after D's frame check and input check (D's queue logic, extended to P7 arms, §10). REF's and SYS_BOTH's exist.
* **Recipe:** compare.py's, both stages (stage 2's b̃ walk-forward on 2019..Y−1, men; women have no stage 2);
  addition 2 §1's 2026 rule (no nudge where the speed memory is missing; the 909-match drop as a sensitivity); P(better)
  = Φ(estimate / SE), the t value beside it.
* **Matches:** the 67,226 frame matches every compared frame holds; extra matches of a C0 frame counted, never scored.
* **Periods:** 2020–2026 pooled (the reading's period), each season, and 2020–2024 and 2025–2026 apart.
* **The pre-registered pairs** (Appendix A §3), each for women, men and both tours, both stages and stage 1 alone:
  1. **P7_SYS_ITF vs P7_SYS_EXCL** — the women's primary: does ITF evidence, through the system, help?
  2. **P7_ASIS vs P7CTL_ASIS** — the rule of 8 October on P7's data: SofaScore's ITF box scores as equivalent.
  3. P7_SYS_ITF vs P7_ASIS — the system's ITF entry against no rule.
  4. P7_SYS_EXCL vs P7_ASIS — the system (ITF out) against no rule, on the same data.
  5. SEL_BOTH vs REF and P7_SYS_ITF vs REF — the system for women, without and with P7.
  6. P7_SYS_EXCL vs SEL_BOTH — the day's other data and the refit, under the system.
  7. P7_S2's pairs (§4.3), if it is built as a diagnostic.
  8. **Strata** (pre-match counts from C0_P7; no outcome): *ITF-exposed* — a side's 365-day box-score history in C0_P7
     is ≥ 20% ITF; *ITF-free* — both sides under 5% (the falsification stratum for pairs 1–3: they should read near
     0 there); *low exposure* — the less-exposed side has fewer than 10 main-tour results in 365 days.
* **Holm**, for each harm-check pair of §7 (SEL_BOTH vs REF, P7_SYS_ITF vs P7_SYS_EXCL, P7_SYS_EXCL vs SEL_BOTH; per
  tour): the family of its seven seasons and the four strata cells (ITF-exposed / not, low exposure / not), family-wise
  5%, two-sided normal p (D's `holm_family` rule); raw labels beside.
* **Statistic level:** B's pair of §3.6.

*Resolution* (*Inferred*): women's frame matches 2020–2026 number 15,255 (F's dose table). With σ ≈ 4.4–5.8 mLL per
match (§6.3), SE ≈ 0.036–0.047 mLL: the pooled reading calls a difference of ≈ 0.07–0.09 mLL, and has 80% power at
≈ 0.10–0.13. Pair 1 acts from 2020 (fully from 2021), so its effective sample is smaller. The scorer: §10 (the run's
`system_pairs.py` refuses dev after the unlock and the holdout twice, by design).

### 6.2 The forward test

*Suggestion.* On the decision day D (step D1):
* **Freeze and hash** a dated addition ("P7 forward"): the chosen women's configuration W* and its comparator (the
  arm W* was chosen over; by default P7_SYS_ITF against P7_SYS_EXCL if W* is the system with ITF, else W* against REF),
  every code file, the class table, `params_P7` with the rule that makes its season-2027 rows (the frozen code's
  mechanical mode on results in by the 2027 cutoff), the strength rule, the scorer, the looks and the thresholds below.
* **Matches scored:** main-tour main draws (250+) whose earliest possible start `es` ≥ D + 1 (the match clock), women
  first, men secondary; nothing about them is read before D.
* **At each look** (the leak-free way, *Inferred*): F's frozen builder makes `C0_FWD` from C0_P7's sources as they stand
  that day; a history check proves every match possibly played before D identical to C0_P7's (a base-folder option,
  §10); both arms are built on C0_FWD with the frozen configs (2 chain builds); fits only for the seasons the window
  touches (season 2026's fits are C0_P7's, copied only if the training inputs are identical, D's copy rule; season 2027:
  2 × 4 fits); scored with the frozen recipe on the window's matches.
* **Looks**, counted in scored women's matches (robust to the calendar): **L1 at 800** (≈ the 2027 hard-court spring),
  **L2 at 1,600** (≈ after Wimbledon), **L3 at 2,400** (≈ the end of the 2027 season). At every look the **harm check of §7**: W* is
  reverted if the women's reading is worse by more than 0.10 mLL with its whole 95% interval below 0 (early, the
  interval binds: at L1 the estimate must be below about −0.31 to −0.40 mLL). At L3 also the **first clean reading**,
  labelled better / worse / unresolved with P(better); later seasons are pooled with it at each season's end. With a
  true effect of 0, each look flags harm 2.5% of the time at most; with a true −0.30, L3 flags it 72–92% of the time.

### 6.3 How many weeks the forward test needs (women)

**Assumptions** (*Inferred*, from D's and E's numbers):
* The paired difference's noise per match, σ = SE · √N: the men's holdout primary, SE ≈ 0.063 on ≈ 4,810 matches
  (E's power note, `D_verification.md`) gives **σ ≈ 4.4 mLL**; the first run's FP against REF for women on dev, interval
  [−0.154, +0.073] on 10,593 matches (SE ≈ 0.057, the harness), gives **σ ≈ 5.8 mLL**. Arms that differ less than an
  input-changing arm against REF (P7_SYS_ITF against P7_SYS_EXCL) may sit lower; P7 doubles some women's box-score
  evidence, so it may sit higher.
* SE ≈ σ / √N with four-week blocks and four seeds (as compare.py scores); two-sided 5%.
* "Resolve": the 95% interval clears 0 with 80% probability when the true effect is δ: **N = (2.80 σ / δ)²**. The
  adoption framework's weaker "unresolved, but P(better) ≥ 0.80" bar with 80% probability (reporting only since
  the owner's decision of 9 October): N = (1.68 σ / δ)².
* Women's main-tour matches (*Observed*, `p7_plan/frame_weeks.json`, counts only): 2,408 a season (2021–2025 mean),
  in 34.2 tournament-start weeks, 70.4 matches per such week; about 30 between mid-November and the end of December.
  A decision in mid-November 2026 therefore waits for the 2027 season before its first forward match.

| Effect δ (mLL) | Why plausible | N, σ = 4.4 | N, σ = 5.8 | Tournament weeks | Seasons |
|---|---|---|---|---|---|
| 0.10 | the size of every model-level effect this study has seen (FP for men +0.083) | 15,200 | 26,400 | 216–375 | 6.3–11 |
| 0.15 | | 6,700 | 11,700 | 96–167 | 2.8–4.9 |
| 0.20 | | 3,800 | 6,600 | 54–94 | 1.6–2.7 |
| 0.30 | a large harm: a counting step at full dose; about three times the first run's placebo cost (0.11) | 1,700 | 2,900 | 24–42 | 0.7–1.2 |
| 0.10, the weaker bar (P(better) ≥ 0.80 with 80% probability) | | 5,500 | 9,500 | 78–135 | 2.3–3.9 |

With one season (≈ 2,400 matches) the forward reading has 80% power at |δ| ≈ 2.8 σ / √2,400 = 0.25 (σ = 4.4) to 0.33
(σ = 5.8).

**Reading it** (*Inferred*). A plausible effect of ITF evidence for women (±0.1 mLL, the size of every model-level
effect this study has seen) needs ≈ 6–11 seasons of forward matches to resolve. Only a large harm (≈ 0.3 mLL, for example
a broken calibration at full dose) shows within a season. **The minimum forward window is therefore
one season of women's play (≈ 2,400 matches, 34 tournament weeks: 2027)** for a first clean reading that can catch a
large harm; it cannot confirm a plausible gain. Under the owner's decision this is no obstacle: the route is
set by the statistic-level evidence, the non-clean readings are harm checks, and the forward test is the holdback that
catches a large harm.

---

## 7. The decision rule (the owner's decision of 9 October, as addition 4 applies it; the owner decides)

**The layer** (*Observed*): the owner's decision `docs/decisions/2026-10-09-adoption-by-change-class.md`, its application
to this study `system/owner_decision_2026-10-09.md` (sha256 `7e7f35da…`), adopted by the lead's
`preregistration_addition_4.md` (sha256 `754e055c…`, 10 Oct 03:00 UTC). It replaced this run's "better / P(better)"
rules before any model-level score existed. Three steps: **classify the change before any result; the route the
statistic-level evidence supports decides; the model-level comparison is a harm check with a stated tolerance.**
"Keeping it out costs nothing" is never a reason. The labels (better / worse / unresolved, P(better)) are reporting only.

**Name the target first** (`docs/studies/adoption_framework/README.md`): the price and hour we bet at is the market near
its close, and the model holds the close as an input, so every reading answers "does it help beyond the close?"; the
matches are WTA (women) and ATP (men) main draws of 250 and up; the seasons are 2020–2026 (non-clean) and the forward
window. No edge credit follows from any adoption here: the edge that sizes stakes comes only from untouched matches at
the venue's price, after costs, shrunk.

**1. The kinds of change, classified now, before any P7 result** (Suggestion, in the decision's table):

| Change | Kind | Expected direction | What decides | The model-level comparison |
|---|---|---|---|---|
| The system for women (translation, w, w_results; **W1**) | repair: it changes how data already in the model enters its inputs (the owner's file, "Why") | + (B: women +0.190 [+0.152, +0.227] milli per unit against pooling, +0.256 against main-tour only) | the statistic-level evidence, which exists | harm check |
| P7's ITF box scores, through the system (**W2**): the 2018–24 backfill and the 2025–26 ones already in the reference | expansion | set by the route | B's refit (ITF fitted, w > 0, γ check, §3.4), B's statistic-level pair (§3.6), the D-CAL calibration (§2.3), the input check | harm check |
| P7's data as equivalent (**W3**, P7_ASIS) | not a supported route: pooled as equivalent, opponent-dependent lower-level statistics predict worse than ignoring them (`docs/studies/lower_level_evidence/README.md` §3.2) | − | — | read and reported: what the rule of 8 October protects against |

**2. Harm** (the owner's file §1; not loosened once a score it governs exists): a reading shows harm when the named model
is **worse by more than 0.10 mLL with its whole 95% interval below 0**; an input flag shows harm only when the hashed
expected unevenness (§2.6), read against the tour-season's dose, does not explain it. "Unresolved" passes. A subgroup
harm counts too: a reading of the Holm family of §6.1 that reads "worse" after Holm (the role addition 2's eight play
for men).

**3. Women** (W0 = REF's recipe for women, P7 out: today):

| Step | Route evidence | Harm evidence | If no harm | If harm |
|---|---|---|---|---|
| **W1, the system for women** | B's women's statistic-level gains (above) | SEL_BOTH vs REF, women, both stages, 2020–2026, and its Holm family | the system is recommended for women | W0, with what drove the harm |
| **The other new lower-level data for women** (C0_now's additions and the day's: results, non-ITF box scores), by the system's route (addition 4) | B's w_results and translation, as for men | NEW_SYS_BOTH vs SYS_BOTH, women (this run), and P7_SYS_EXCL vs SEL_BOTH, women (pair 6) | they enter by the system's route | they stay out, with what drove the harm |
| **W2, ITF through the system** (on top of W1) | B's refit fits women's ITF from season_used 2020 with w > 0 in most statistics, and B's statistic-level pair (C0_P7 against C0_P7ctl, women, 2019–2024) is not worse; D-CAL settled | P7_SYS_ITF vs P7_SYS_EXCL, women, both stages, 2020–2026 (pair 1) and its Holm family; the input check against §2.6 | ITF box scores enter translated and weighted by their own fitted parameters; the 2025–26 ITF box scores already in the reference follow (addition 4: REF_noITF vs REF on the holdout and pair 1's 2025–2026 reading are their harm evidence) | the route keeps them out (w = 0, as today) and the report names what that forgoes |
| **W3, as equivalent** | none | P7_ASIS vs P7CTL_ASIS and P7_ASIS vs REF, reported | never decides entry | — |

If the route evidence fails (B fits women's ITF at w ≈ 0, or the statistic-level pair reads worse), the route itself
excludes ITF and pair 1 is reported only. If W1 shows harm, W2 is moot (it sits on the system).

**The rates of the women's harm check** (the decision asks every rule to state them; *Inferred*, normal approximation,
SE 0.036–0.047 for women's 2020–2026 pooled, §6.1; the flag is "estimate below −0.10 and the whole interval below 0"):

| True effect of the change (mLL) | 0 | −0.05 | −0.10 | −0.15 | −0.20 |
|---|---|---|---|---|---|
| P(harm flagged) | 0.003–0.017 | 0.08–0.14 | 0.50 | 0.86–0.92 | 0.98–0.997 |

So a harmless W2 is adopted 98–99.7% of the time, and a true 0.10 mLL harm passes half the time: the decision's trade,
accepted because the statistic-level evidence, not the model-level reading, sets the route.

**4. Men.** The same steps on men's readings. Men's treatment is CP3's outcome under addition 4 (SELECTED unless harm;
REF otherwise, with RES_ONLY on C0_now registered next). Men's ITF: the route is B's men's ITF fit (the dry run's
thin data put serve points won's free w at 0, §9) and pair 1 for men is the harm check. P7 reaches ≈ 9% of men's matches
and ≈ 1 point of box-score share, so men's readings are expected unresolved, and unresolved passes.

**5. The rule of 8 October.** The rule stands as procedure: P7 is a candidate, tested here before it enters. P7_ASIS
against P7CTL_ASIS shows what it protects against: harm there means the rule kept a harmful as-is entry out; no harm
means an as-is entry would have been harmless here (it is still not the supported route). Struck, by the owner's
decision: "the rule costs nothing to keep". The report names what keeping P7 out forgoes: 14–18% of a woman's
previous-year box-score history (`team/04_incoming.md` §3.2), and, for live use, the women's histories missing lower
levels since June 2026 (finding #7).

**6. The forward test under this layer** (§6.2) is this change's holdback (the decision's point 5): W* against its
comparator, read with the same harm tolerance at each look; harm reverts W* and is reported. It earns no edge credit.

---

## 8. Compute and time

*Inferred*, from the run's timings (C_layer §5: lane 1 ≈ 98 minutes in the first run, 143–226 minutes for this run's
loaded builds; C_layer_ios §4; D: 40–55 s a fit on a free card, about twice that shared; B §7: 76 minutes for the
params step; F §9: 35–60 + 25–40 minutes per candidate).

| Item | Count | Each | Total |
|---|---|---|---|
| F: C0_P7, C0_P7ctl (build + checks), one at a time | 2 | 1–1.7 h | 2–3.4 h |
| Hand checks + E's re-audit | 2 folders | 0.5–0.75 h | 1–1.5 h |
| Chain builds: P7_ASIS, P7CTL_ASIS, P7_SYS_EXCL, P7_SYS_ITF (lane 0 on ≈ 1.47 M matches adds the full leak-proof rebuild, F §8) | 4 (+1 SEL_BOTH if SELECTED ≠ SYS; +1 IDENTITY_ALL re-check) | 2.5–4 h | 10–16 h of builds, ≈ 6–8 h wall at 2 in parallel |
| Gates + leak probes (P7_SYS_ITF, P7_ASIS) | 2 | 0.75–1 h | 1.5–2 h |
| Strength files | 1–2 | 5 min | — |
| A's ITF δ levels (option 1) | 1 | 5–10 min | — |
| B: elo + params (19 statistics, both tours, 2013–2024, 60 draws) + freeze + mechanical | 1 | 2–2.5 h | 2–2.5 h |
| B's statistic-level pair (route evidence for W2, §3.6; beside A2) | 2 dev runs | 0.5 h | 1 h |
| Fits: 32 per arm × 4 arms (+32 P7_S2, +32 SEL_BOTH) | 128–192 | 40–90 s | 1.4–4.8 h of GPU |
| Scoring + E's re-derivation | 1 | 1–1.5 h | 1–1.5 h |

**In all** (*Inferred*): ≈ 10–16 hours of chain builds (≈ 6–8 hours of wall time at two in parallel), ≈ 2–3.5 hours of F's
builds and checks, ≈ 2–2.5 hours of B, ≈ 1.5–5 hours of GPU fits and ≈ 3 hours of human checks (hand check, E twice),
spread over about two working days.

**Sandboxes and disk** (about 21 GB each): two sandboxes, reused. `tnr_sysA` patched with C0_P7 builds P7_ASIS, then
P7_SYS_ITF; `tnr_sysB` patched with C0_P7ctl builds P7CTL_ASIS, then is re-patched with C0_P7
(`system_new_arms.py --patch --sandbox … --stage0 …/C0_P7`) for P7_SYS_EXCL. A NEW-type sandbox refuses other arms and
vice versa (`system_arms.py:645-655`); lane 2 keeps one runs folder per arm name, so no name is built twice in one
sandbox (C2's caution, `system_arms.py:676-679`). A third sandbox only for SEL_BOTH or IDENTITY_ALL.

**The critical path** (≈ 13–16 hours from T2 to the readings):
F's C0_P7 build and checks (1–1.7 h) → hand check and E (≈ 1.5 h) → READY → P0 the pre-registration (≈ 0.25 h) → P7_ASIS
lane 0 and Stage 1 (≈ 1–1.5 h) → strength file → A's δ levels → B's elo and params (≈ 2 h) → freeze and mechanical
(≈ 0.3 h) → P7 addition 1 (≈ 0.25 h) → **P7_SYS_ITF's build (≈ 3–4 h)** → gates and probes (≈ 1 h) → input check and 32
fits (≈ 0.5–1 h) → scoring (≈ 0.5 h) → E (≈ 1 h). Everything else runs beside it: C0_P7ctl after C0_P7 (F's one-at-a-time
rule), P7CTL_ASIS and the rest of P7_ASIS beside B, P7_SYS_EXCL beside P7_SYS_ITF. **The code changes of §10 are off the
path only if they are made and tested before P7 lands.**

---

## 9. The dry run (10 Oct, CPU-light, one process at a time, no GPU, no chain build)

*Observed* unless stated. Evidence in `p7_plan/` (`help/`, `scripts/`, the outputs named).

**What was run** (02:13–02:55 UTC, while C1 built SYS-family arms; the machine shared):

| # | Command | Result |
|---|---|---|
| 1 | `--help` of 21 cited scripts, one at a time (`p7_plan/scripts/help_all.sh`; outputs and exit codes in `p7_plan/help/`) | 19 exit 0 (1–80 s each, mostly import time). `level_layer_ios_checks.py` has no `--help` branch: it prints its usage and exits 1 (`:483-484`), by design. **`model_rebuild/fits.py --help` fails under `./python.sh`**: it imports torch before parsing (`fits.py:63`); it runs only under `./python_tabpfn_local.sh`, which was not started (no GPU environment touched); its flags are read from the code (`:66-72`) |
| 2 | (not run) `match_timing/probe.py`, `surface_ios/probe.py`, `relationship_report.py` with `--help` | no argument parser: "--help" would run the probe (13–22 minutes on the live tables) or rewrite B's tables (`relationship_report.py:119-130`). Listed as traps in §10 |
| 3 | Every flag the plan cites: `./python.sh -m pytest test/lower_level_evidence/test_p7_plan_commands.py -q` | **17 passed, 6 xfailed.** 14 scripts' cited flags all declared (e.g. `--sofascore-skip` `candidate_stage0.py:2566`, `--derive-from` `:2571`, `--strength` and `--name` `system_new_arms.py:243,247`, `--stage0` `system_sandbox.py:409`, `--through` `compare.py:443`, `--stage0`/`--timing` `history.py:169-170`). The six xfails are §10's missing paths (#1, #2, #3, #4, #5, #9), each failing for the stated reason |
| 4 | `p7_trigger_check.py --gap challenger_points_2025` (a finished P6 gap as the stand-in) | exit 0, "landed": 14,675 targets, 14,608 linked, all fetched, 14,541 box scores (98.9%, 99.5%); verify_links agrees |
| 5 | `count_itf_box.py` on C0_now (`p7_plan/c0now_itf_box_counts.csv`, `_season_rule.csv`) | men's ITF box-score matches 55, 80, 98, 199, 91, 170, 285, 216, 248 (2016–2024), all but a few on reference matches the frozen strength covers; women's 29 (2022), 1 (2023); ITFQ ≤ 23 a season before 2026. The count part of B's rule first passes for men at season_used 2022 |
| 6 | B's estimator, the ITF-ready path, on C0_now: `relationship.py --steps params --method F4 --stage0-dir …/C0_now --timing …/C0_now/timing.parquet --strength …/classes/strength_elo.parquet --through 2021 --first-season 2021 --last-season 2022 --stats spw --h-grid 26,52 --boot 2 --workers 1 --out p7_plan/dryrun_b_c0now` | **One tour was asked for; no `--tours` flag exists** (`relationship.py:2056-2073`), so both tours ran for the one statistic (cheap; §10 #3 adds the flag as optional). **First try failed**: with `--h-grid 26`, `KeyError: 52.0` in `job_params_p2` (`relationship.py:1631` reads the 52-week fit for the no-class view). **Fix:** a reduced grid must contain 52. **Second try: exit 0 in 6.0 minutes**, 28 rows (`params_dev.parquet`; `inspect.json`). Men's ITF `fitted` false for 2021, **true for 2022**; women's ITF false; ITFQ false. ITF's free w for serve points won at the bound 0 (se 0; 65 players; δ barred at ITF), so w = 0. γ equal to the frozen rows. Non-ITF w differ from B's frozen rows (one statistic, so no shrinkage across statistics; a two-value half-life grid; C0_now's extra box scores): expected. `fit_through` 2020-11-22 and 2021-11-21, before each season's cutoff. **A code check on one statistic and two seasons, with the frozen strength (C0_now's new matches carry no rating and drop out): not evidence** |
| 7 | `sofascore_calibration.py --candidate …/C0_now` (seasons ≤ 2024; `p7_plan/calibration_C0_now_pre2025.csv`) | 514 matches, 1,028 player rows: first serves in 78.9% exact (+0.88), first-serve won 82.2% (+0.45), second-serve won 83.9% (−0.41) fail the 90% rule; serve points 93.4%, the other five 96–98% pass (§2.3) |
| 8 | `frame_weeks.py` (counts of the frozen frame; no input or result column read) | women 2,408 matches a season (2021–2025), 34.2 tournament weeks, 70.4 a week; men 2,609, 35.6, 73.3 (`p7_plan/frame_weeks.json`) |

**What was not run, and why** (each would write another role's files or needs a missing path):
* `relationship.py --freeze` / `--mechanical` with a P7 `--out`: `--freeze` would overwrite B's frozen
  `system/relationship/method_freeze.json` (`:90`, `:1924`). Fix: §10 #3.
* `classify.py --analysis` on a candidate: no Stage 0 option; it writes `system/classes/` (`:1121-1123`). Fix: §10 #4.
* `system_arms.py --config P7_ASIS`: `arm_config` raises "unknown arm" (`:258`). Fix: §10 #5.
* `system_g5.py --tree …`: writes `arms/g5/real_date_probe.json` with synthetic configs. Fix: §10 #7.
* `system_new_arms.py --strength --from <sandbox>`: needs a sandbox whose Stage 1 ran on a candidate; NEW_ASIS's
  is not built yet (`arms/strength/` holds only the reference's file). Its checks are read from the code (`:202-235`).
* Any chain build, fit or score.

---

## 10. Changes needed in other roles' code

None was made by G. Each is a Suggestion for the owning role; every one that touches a frozen file needs a new dated
addition before any score it touches (addition 3 §1).

| # | File (owner) | Change | Why |
|---|---|---|---|
| 1 | `level_layer.py` (C1) | `validate` (`:225-226`): allow `itf_box` "fitted". `weights` (`:567-571`): under "fitted", ITF and ITFQ rows take the fitted (or numeric) path like any lower level, capped; an unfitted row reads w = 0 from B's row. `translation` (`:615`): drop `& ~np.isin(bucket, ITF_LEVELS)` under "fitted" (δ only where the class table lists ITF). Optional with it: a list of statistics whose ITF rows stay at w = 0 under "fitted" (D-CAL option 1). Tests: "exclude" and "as_is" bit-for-bit unchanged; "fitted" reads B's ITF rows by own season | P7_SYS_ITF cannot be expressed today |
| 2 | `level_layer_ios.py` (C2) | `fe_levels` (`:289-300`): under `itf_box` "fitted", do not drop ITF/ITFQ (`NO_LEVEL_TERM`, `:286`) when the class table lists them (and with classes null). `level_arrays` already reads m through C1's `weights` (`:319-320`) | ITF level term in form (b); m for ITF rows |
| 3 | `relationship.py` (B) | `--freeze` and `--mechanical` use `Path(a.out) / "method_freeze.json"` instead of the module's `FREEZE` (`:90`, `:1924`, `:1932`); `frozen_inputs` (`:1890-1896`) hashes the `--strength` and class table actually used; a `--classes` flag passed to `build_ctx` (`:1204`, `:1829`); log `elo_missing_rows` in `run_params` (only the dev step does, `:1252`); optional `--tours` | the P7 refit must never touch B's frozen files and must record what it read |
| 4 | `classify.py` (A) | the decomposition's `LEVELS` (`:59`) extended to ITF and ITFQ for a P7 run; CLI options `--stage0-dir`, `--timing`, `--strength-path`, `--out` (today only `--strength`, `--demo`, `--analysis`, `:1121-1123`, all writing `system/classes/`) so the analysis on C0_P7 writes `system/classes_P7/` and changes only `delta_levels` | D-δ option 1 |
| 5 | `system_arms.py` (C1) | P7 arm names (and SEL_BOTH, if CP2 did not keep SYS): a `P7_STAGE0` map like `NEW_STAGE0` (`:262`), configs as §4.2 (`new_config`-style, `:266-297`), the build's candidate-Stage-0 check (`:645-655`) extended to them, a `configs_P7/` folder with its MANIFEST; `arm_config` raises on unknown names (`:258`) | no P7 arm can be built today |
| 6 | `system_gates.py` (C1) | P7 arms in the NEW-arm gate list (`:526-527`, `:589`); the P7 invariance gate (P7_SYS_ITF vs P7_SYS_EXCL) and the direction gate of §5 | §5 |
| 7 | `system_g5.py` (C1) | `--config <layer config>` and `--out` (it writes `arms/g5/real_date_probe.json` and uses synthetic configs, `system_g5.py:1-21`) | the real-date probe on P7_SYS_ITF without overwriting C1's evidence |
| 8 | `system_fits.py` (D; frozen) | P7 arm lists (`C1_ARMS`, `FIT_ORDER`, `EXTRA_MATCHES_OK`, `EXPECT`: `:96-108`, `:140`) — better a new `p7_fits.py` importing its functions, with P7's expectations from §2.6 | D's queue knows only this run's arms |
| 9 | a new P7 scorer (D) | `p7_pairs.py`, importing `system_pairs.py`'s `load_models`, `paired`, `populations`, `holm_adjust`; its own lock: the P7 pre-registration's hash; the periods of §6.1 and the forward windows of §6.2 | `system_pairs.py` refuses dev once the unlock exists and the holdout once `readings.json` exists (its docstring, `:11-21`) |
| 10 | `candidate_stage0.py` (F) | (a) a box-layer level skip (e.g. `--box-skip-levels ITF,ITFQ`) for a P8-era control; (b) a per-count mask for SofaScore completions (D-CAL option 2); (c) the calibration table of §2.3 written by `--checks`; (d) F's own given-name rule for the `name_subset` route (F §5) | §1.4, §2.3 |
| 11 | a forward-test history check (lead) | `history.py` compares only against the frozen reference (`history.py:49-53`; a decided file); a P7 copy that takes a base folder (C0_P7) | §6.2 |
| 12 | `candidate_arms.py` (first run, read-only) | `share_inputs` / `side_shares` read the frozen Stage 0 (`:101-107`, `:175`, `:373-384`): a P7 copy with a Stage 0 argument | P7_S2 |
| 13 | `relationship_report.py` (B) | an `--out`: it takes no argument and rewrites `system/relationship/`'s tables (`:119-130`) | a no-class view of `params_P7` if SELECTED is SYS_NOCLASS |
| 14 | a pairing script (B) | per-target pair of two dev runs (§3.6) | B's statistic-level reading |

Not changes, but traps found (*Observed*): `match_timing/probe.py`, `surface_ios/probe.py` and `relationship_report.py`
have no argument parser, so `--help` would run the job (and the last would rewrite B's tables);
`model_rebuild/fits.py --help` imports torch before parsing (`fits.py:63`), so it fails under `./python.sh` and must go
through the GPU environment.

---

## 11. Open questions for the lead

1. **D-δ:** extend A's classes to ITF (option 1, needs A's change) or freeze δ_ITF = 0?
2. **D-CAL:** if SofaScore's first-serve split (or its break points) fails the calibration on ITF, leave those
   statistics' ITF rows out of the system arms (option 1), mask the counts in the data (option 2), or accept the step
   (option 3)?
3. **Who owns the new modules** (the P7 scorer, the P7 fit queue, the forward history check), and is a dated addition
   to this run's pre-registration the right home for the code changes to frozen files, or does P7's own pre-registration
   cover them?
4. **The share control:** drop P7_S2 (the owner's decision files the share inputs as a pool lead, U-330), or build it
   as a diagnostic of the mechanism?
5. **P8:** accept "rebuild the chosen configuration only"?
6. **The forward test as a harm guard:** accept that it cannot confirm a plausible gain within a season, and that the
   women's decision rests on the non-clean readings?
7. **SEL_BOTH when CP2 selects a non-SYS arm:** one more build on the frozen Stage 0, or read SYS_BOTH instead?
8. **The decision layer:** §7 follows addition 4 (written at 03:00 UTC, while this plan was being drafted). Confirm that
   P7's pre-registration adopts it for women, with W1 and W2 classified as in §7.1 before any P7 result.

### 11.1 The lead's rulings (10 Oct 2026, about 03:40 UTC)

These bind the session that runs this plan. They can be changed only by a dated note in P7's own pre-registration,
written before any P7 result.

1. **D-δ: option 1, by the frozen rule.**
   * Extend A's analysis to ITF (§10's change to `classify.py`) and run it on C0_P7's training seasons only.
   * ITF joins a statistic's `delta_levels` only where its residual passes A's frozen thresholds (`thresholds.json`,
     `d8eb62d2…`). No choice is made by hand.
   * Until that change exists, δ_ITF = 0.
2. **D-CAL: option 1.**
   * A statistic whose SofaScore counting fails the calibration on ITF is left out of the system arms: w = 0 for that
     statistic's ITF rows from that source. The counts left out are reported.
   * P7_ASIS and P7CTL_ASIS take the data as wired, because they stand for what would happen without the rule.
   * Masking the data (option 2) would change that counterfactual. Accepting a failed check (option 3) contradicts the
     check.
3. **Ownership and frozen files.**
   * The session that runs this plan is P7's lead. It owns the new modules (the P7 scorer, the P7 fit queue, the forward
     history check), written as new files where possible.
   * The changes §10 lists to this run's frozen files are made only after this run's checkpoint 3 closes:
     `relationship.py`, `level_layer.py`, `level_layer_ios.py`, `classify.py`, `system_arms.py`, `system_gates.py`.
   * Each change comes with tests, and P7's own pre-registration records it with its old and new hashes. This run's
     pre-registration takes no further additions after checkpoint 3.
4. **The share control.**
   * P7_S2 is a diagnostic of the mechanism only, built last if time allows, and never decisive.
   * Under the owner's decision of 9 October, share inputs are a lead for the feature pool (U-330), not part of this
     test.
5. **P8: accepted.** P8 completes the same route, so it is a repair or accretion under the owner's decision:
   * a rebuild of the chosen configuration only;
   * data checks;
   * the input check against a hashed expected unevenness;
   * a harm check against the configuration P7 chose.
6. **The forward test: accepted as a harm guard.**
   * The women's route is decided by B's statistic-level pair (P7 against its control) and the non-clean model-level
     harm checks, as the owner's decision prescribes for an expansion.
   * One season (2027) flags only harms of about 0.3 mLL or more, and the report says so.
7. **SEL_BOTH.** Build it on the frozen Stage 0 only if this run's checkpoint 2 selects, and checkpoint 3 then
   recommends, a configuration other than SYS. Otherwise read SYS_BOTH. The P7 arms always use the configuration this
   run recommends for men, applied to both tours.
8. **The decision layer: confirmed.** P7's pre-registration adopts addition 4 (the owner's decision of 9 October) for
   both tours, with W1 and W2 classified as in §7.1 before any P7 result.
9. **`history.py` was narrowed on 9 October** (the owner's amendment in `docs/decisions/2026-10-08-current-best-model.md`).
   * Only lower-level differences now refuse a template build. They are listed under `gated`.
   * Main-tour differences are listed under `allowed_main_tour`.
   * The all-level keys (`new_past`, `dropped`, `revised`) are unchanged, so the C0 checks in §2.4 read as written.
   * Every P7 addition is lower-level, so P7 remains a candidate.

---

## Appendix A. Draft of P7's pre-registration (the lead hashes it at step P0)

```
# Pre-registration P7: ITF box scores (package P7) and the women's treatment of lower-level evidence

Written <date, UTC> by the lead, before any P7 arm was built and before any P7 score. SHA-256 in
preregistration_P7.sha256. Earlier files unchanged: preregistration.md (cc65bcd5…), additions 1 (c718e6d0…),
2 (3f536796…), 3 (f2063433…)<, later additions>. This run's selection: SELECTED = <arm> (results/selection.json <sha>);
CP3 done (holdout_unlock.json <sha>; results/holdout/readings.json <sha>).

## 1. The data
* C0_P7: system/stage0/C0_P7, manifest <sha>; C0_P7ctl (--sofascore-skip "ITF Men,ITF Women"), manifest <sha>.
* Expected unevenness: system/stage0/C0_P7/expected_unevenness.txt, <sha>, written <time>, before any P7 arm.
* D-CAL: <the rule chosen, with the calibration table's sha>.
* D-δ: <option 1: classes_P7/classes.csv <sha> | option 2: classes/classes.csv 58e78622…>.

## 2. The arms
REF; SEL_BOTH (<SYS_BOTH | SELECTED's config on both tours>); P7CTL_ASIS; P7_ASIS; P7_SYS_EXCL; P7_SYS_ITF;
<P7_S2 as a diagnostic | not built>. Configs: arms/configs_P7/MANIFEST.json <sha>.
Every tuned constant pinned to the reference's (reference_constants.json 57bc4382…; Stage B pin 43429744…;
IOS_CONSTANTS_VERSION=2026-10-08_reference). The parameters: relationship_P7/params.parquet, fitted by the frozen method
(F4, 60 draws, half-lives 26/52/104/208 weeks, the cap at 1 in the configs), recorded in P7 addition 1 before the system
arms are built.

## 3. The readings (non-clean: pre-registered; seasons seen by the system's design)
Scoring: compare.py's recipe through the P7 scorer; both stages; seeds 0-3; 2020-2026 pooled, each season, 2020-2024
and 2025-2026; addition 2 §1's speed rule; P(better) = Φ(est/SE).
* Women's primary harm check for ITF: P7_SYS_ITF vs P7_SYS_EXCL, women, both stages, 2020-2026; for the system:
  SEL_BOTH vs REF, women. Route evidence: B's refit and statistic-level pair (P7_plan.md §3).
* The rule of 8 October: P7_ASIS vs P7CTL_ASIS (women, men, both).
* Secondary: P7_SYS_ITF vs P7_ASIS; P7_SYS_EXCL vs P7_ASIS; SEL_BOTH vs REF; P7_SYS_ITF vs REF; P7_SYS_EXCL vs
  SEL_BOTH; P7_S2 pairs; every arm vs REF; the strata (ITF-exposed >= 20%, ITF-free < 5% both sides, low exposure
  < 10 main-tour results); each season; men's versions of all.
* Holm on each harm-check pair (SEL_BOTH vs REF, P7_SYS_ITF vs P7_SYS_EXCL, P7_SYS_EXCL vs SEL_BOTH; per tour): its 7
  seasons and 4 strata cells, family-wise 5%, two-sided normal p.
* Statistic level: B's frozen method on C0_P7 against on C0_P7ctl, 2019-2024 targets, per tour and group.

## 4. The decision layer (the owner decides)
The owner's decision of 9 Oct 2026 (adoption by change class), as addition 4 applies it: P7_plan.md §7's
classification, route evidence and harm checks (harm: worse by more than 0.10 mLL with the whole 95% interval below 0;
an unexplained input flag), as written there on <date>.

## 5. The forward test
Frozen on the decision day in a dated addition: W*, its comparator, the code, the parameters' rule for 2027, the
looks (800, 1,600 and 2,400 scored women's matches), the harm check at each look (§7's tolerance), the reading at 2,400.
```

## Appendix B. Every command, in order

```
# Git Bash, from the repository root; the shorthands of section 3.4
P7=data/studies/lower_level_evidence/system/stage0/C0_P7
S=data/studies/lower_level_evidence/system/arms/strength/P7_C0_P7_elo.parquet
R=data/studies/lower_level_evidence/system/relationship_P7

# T1/T2: the trigger (PowerShell for the process list)
Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Select-Object ProcessId, CommandLine
./python.sh data/studies/lower_level_evidence/system/p7_plan/scripts/p7_trigger_check.py --gap itf_points_2025_2026
./python.sh data/studies/lower_level_evidence/system/p7_plan/scripts/p7_trigger_check.py --gap itf_detail

# W1-W2: the Stage 0s (one heavy process at a time)
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7 --checks
./python.sh data/studies/lower_level_evidence/system/p7_plan/scripts/sofascore_calibration.py \
    --candidate data/studies/lower_level_evidence/system/stage0/C0_P7 --levels ITF --max-year 2026 \
    --out data/studies/lower_level_evidence/system/p7_plan/calibration_C0_P7_itf.csv
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7ctl --sofascore-skip "ITF Men,ITF Women"
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7ctl --checks
#   hand check -> identity_verdicts.csv in each folder; expected_unevenness.txt + .sha256 + status line; E's re-audit
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7 --ready
./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_P7ctl --ready

# P0: preregistration_P7.md + .sha256 (the lead)

# A1: the template arms (after §10's system_arms change; two sandboxes)
./python.sh src/eda/lower_level_evidence/system_sandbox.py --setup --n <A>
./python.sh src/eda/lower_level_evidence/system_new_arms.py --patch --sandbox C:/Users/zerom/tnr_sys<A> \
    --stage0 data/studies/lower_level_evidence/system/stage0/C0_P7
./python.sh src/eda/lower_level_evidence/system_arms.py --build P7_ASIS --sandbox C:/Users/zerom/tnr_sys<A>
./python.sh src/eda/lower_level_evidence/system_sandbox.py --setup --n <B>
./python.sh src/eda/lower_level_evidence/system_new_arms.py --patch --sandbox C:/Users/zerom/tnr_sys<B> \
    --stage0 data/studies/lower_level_evidence/system/stage0/C0_P7ctl
./python.sh src/eda/lower_level_evidence/system_arms.py --build P7CTL_ASIS --sandbox C:/Users/zerom/tnr_sys<B>

# R1: once P7_ASIS's Stage 1 is written
./python.sh src/eda/lower_level_evidence/system_new_arms.py --strength --from C:/Users/zerom/tnr_sys<A> --name P7_C0_P7_elo
#   D-δ option 1: A's analysis on C0_P7 -> system/classes_P7/ (after §10 #4)
./python.sh src/eda/lower_level_evidence/relationship.py --steps elo --stage0-dir $P7 --timing $P7/timing.parquet --strength $S --out $R --work $R/work
./python.sh src/eda/lower_level_evidence/relationship.py --steps params --method F4 --boot 60 --workers 3 --stage0-dir $P7 --timing $P7/timing.parquet --strength $S --out $R --work $R/work
# R2 (after §10 #3)
./python.sh src/eda/lower_level_evidence/relationship.py --freeze --method F4 --boot 60 --stage0-dir $P7 --timing $P7/timing.parquet --strength $S --out $R
./python.sh src/eda/lower_level_evidence/relationship.py --mechanical --stage0-dir $P7 --timing $P7/timing.parquet --strength $S --out $R
#   P7 addition 1 (the lead) hashes params_P7 and the configs

# A2: the system arms. Run each arm's gates and probes (below) BEFORE its sandbox is reused: the next build
#     rewrites the sandbox's intermediate tables (the arm's own outputs are already collected in arms/<ARM>/)
./python.sh src/eda/lower_level_evidence/system_arms.py --build P7_SYS_ITF --sandbox C:/Users/zerom/tnr_sys<A>
./python.sh src/eda/lower_level_evidence/system_new_arms.py --patch --sandbox C:/Users/zerom/tnr_sys<B> \
    --stage0 data/studies/lower_level_evidence/system/stage0/C0_P7
./python.sh src/eda/lower_level_evidence/system_arms.py --build P7_SYS_EXCL --sandbox C:/Users/zerom/tnr_sys<B>
# only if CP2 did not keep SYS: SEL_BOTH on the frozen Stage 0 in a third sandbox (system_sandbox.py --setup --n <C>;
#     --patch --sandbox C:/Users/zerom/tnr_sys<C>; system_arms.py --build SEL_BOTH ...; after §10 #5)
# B's statistic-level pair (§3.6; the route evidence for W2), beside A2: relationship.py --steps dev,tables on C0_P7 and on C0_P7ctl, then the
#     pairing script (§10 #14)

# gates, per arm; probes for P7_SYS_ITF and P7_ASIS (§5)
./python.sh src/eda/lower_level_evidence/system_gates.py --arm <ARM> --sandbox C:/Users/zerom/tnr_sys<k>
./python.sh src/eda/lower_level_evidence/system_gates.py --arm <ARM> --ready

# F1: fits (role D, after §10 #8): the frame check and the input check (compare.py's part 1, read against §2.6) through
#     the P7 fit module, then
./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out data/studies/lower_level_evidence/system/arms/<ARM> \
    --seeds 0-3 --seasons 2019-2026 --wait-memory-only

# P7_S2 (optional diagnostic, §4.3): D builds it from P7_ASIS's frame plus the two shares recomputed on C0_P7 (§10 #12),
#     then 32 fits through the 60-input runner (system_fits.py --fit60's path)
# S1: the readings (after §10 #9)
./python.sh src/eda/lower_level_evidence/p7_pairs.py --score          # the new scorer
```

## What it does not show

* **Any reading.** Nothing here scores P7; no P7 data exists yet. The thresholds, sizes and expectations are written
  before the data so that they cannot follow it.
* **That P7 will land as planned.** The dates, the 98% yield and the link rates are the collection plan's research
  claims (84 sampled matches); the 2025–26 yield is unmeasured.
* **SofaScore's ITF counting.** The calibration is designed, not run on ITF: the dry run read pre-2025 SofaScore rows,
  mostly men's Challengers.
* **The code changes.** §10 lists them; none exists, and each will need its own tests and gates. The plan's commands
  for P7 arms, the freeze, the scorer and the probes on P7 configs run only after them.
* **The forward test's power** rests on two σ values from earlier readings; P7's arms may be noisier or quieter.
* **Men.** P7 reaches few men's matches; the men's readings are expected unresolved by construction.
* **P8** is planned only as a refresh of the chosen configuration.

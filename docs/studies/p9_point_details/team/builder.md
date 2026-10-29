# P9 point details: the builder's memo

28 Oct 2026 · Builder agent (Claude Opus 5.5, `claude-opus-5-5`), launched by the lead (session `4ad0f090-214d-4b51-b18a-41ad8262b656`) · Brief: [../briefs/01_builder.md](../briefs/01_builder.md) · Shared context: [../briefs/00_shared_context.md](../briefs/00_shared_context.md)

Labels: **observed** (computed or read here; the file is named), **inferred** (a reading of observed numbers), **unknown**. Every output is in `data/studies/p9_point_details/build/`; every script is in `src/eda/p9_point_details/`. No match result was read: point winners inside matches were used only as raw material (task 3) and to align two sources' point sequences (task 1).

## In short

* **The stopping-rule number: 1.069** *(observed; `depth.json`, `depth.csv`)*. This is the median, over the 35,812 player-matches of men's tour-level main draws (Slams included) and Challenger main draws of 2025-01-01 to 2026-10-18, of each player's 52-week count of points with a known rally length with P9, divided by the same count without P9. **It is below 1.5, so by the declared rule the study stops.**
* **Every variant of the per-player median ratio stays below 1.5** *(observed; `depth.json`, `depth_checks.json`)*:
  * leaving out the player-matches with no such point either way: 1.20;
  * gate at 0.5 instead of 0.9: 1.12;
  * P9's unlinked rally matches added to the with-P9 arm only (an upper bound): 1.08;
  * each match taking its largest count: 1.07;
  * "without P9" = the shot-level study's own tables as of 2 Oct: 1.19.
* **The one reading above 1.5:** the ratio of the two medians (1,093 / 752.5 = 1.45 today) becomes 1.68 against the 2 Oct baseline. That reading takes the shared context's wording ("the median player-match's count … less than 1.5 times what the same matches had") literally and uses the older baseline. Flagged for the lead in "Depth".
* **Why so low** *(observed; `convention.json`, `depth.csv`)*:
  1. **P9's "rally length known" flag mostly marks aces, double faults and junk 0/1 counts in matches the tracker never covered.** Real rally lengths exist in 4,330 of P9's 25,004 matches with points:
     * 1000s: 1,398 of 1,427 main-draw matches;
     * 250s and 500s: about half;
     * Challengers: 566 of 12,494 main-draw matches, nearly all of them 2026's tracked events.
  2. **2025H1 targets cannot gain:** P9 starts in January 2025.
  3. **The non-P9 sources already give top players deep histories:** the volunteer charts, the Slam feeds, TDI from mid-2026.
* **Where P9 does add depth** *(observed; `depth.csv`)*: tour-level main draws pooled, 1.39; targets in 2026H1, 2.18 at the 250s-to-Finals and 2.10 at the Slams. That is the April 2025–June 2026 tour-level gap the shot-level study named. Challenger main draws: 1.00, and 1.40 in 2026H1.
* **The convention** *(observed; `convention.json`, `convention_agreement.csv`)*. `tm1Rally + tm2Rally` counts the shots that landed in, the serve included; an ace and a double fault are 0. So in the shot-level convention: ace 1, double fault 0, winner = the count, error = the count + 1.
  * Against the rally files' categories: aces and double faults 100%, winners 98.8%, forced errors 99.3%, unforced errors 98.9%.
  * Against other sources on aligned matches (equal rally lengths): SirGenkii 99.2%, TDI 98.2%, the Hugging Face Infosys copy 99.3% (5 matches), the volunteer charts 96.7%.
  * The newer recount (`tm1Shot`/`tm2Shot`) is not used: it equals the category on 71% of errors.
* **Links** *(observed; `link_report.json`)*: P9 links to today's Stage 0 for 23,024 of 25,115 matches (91.7%), and for 4,085 of 4,330 rally-carrying matches (94.3%). Every unlinked rally-carrying match is 2026 Challenger qualifying that Stage 0 does not hold. No link was guessed.
* **Reliability** *(observed; `reliability.csv`)*:
  * Style rates repeat well: share of serve points ending by shot 2, by shot 4 and at 9+, 0.70–0.82; mean rally length on serve 0.81–0.85.
  * Points won by band are noisy: 0.03–0.43; won at 9+ 0.03–0.21.
  * Net points won sit near chance: inside the chance band in 2025 (0.01–0.03), just above it in 2026 (0.11 against a band edge of 0.09–0.10).
  * P9 changes these little: it adds players (232 against 199 in the 2025 window) and points per half (921 against 668).
* **The timing probe is clean** *(observed; `probe.json`)*. Nothing dated on or before a cut moved on Stage 0's clock (20 cuts), or on the real dates (9 cuts where events overlap). A match's own points never moved its own aggregate (200 probes).

## What was built

| File | What it holds | Rows (observed) |
|---|---|---|
| `links.parquet` | One row per source match (ATP-format files and the shot-level sources): the Stage 0 match, `a1` (source player 1 is side A), the method, the gate's share and whether the match carries rally length | 30,277 ATP-format + 55,975 shot-level |
| `crosswalk.parquet` | ATP code → Stage 0 player id, with votes, share and origin | 2,441 codes |
| `link_report.json`, `link_failures.csv` | Methods, rates by source, level, draw and season (all and rally-carrying), the crosswalk's checks, the ace check, round disagreements, every unlinked ATP-format match with its reason | |
| `rally_points.parquet` | **Task 2.** One row per point with a known rally length, men 2018–2026, one source per Stage 0 match (P9 first). Columns: `match_id`, `source`, `src_key`, `seq`, `set_no`, `game_seq`, `point_in_game`, `server_id`, `winner_id`, `rally`, `rally_c` (capped 9/10), `band`, `end`, `ender_is_server`, `net_server`, `net_returner`, `how` | 3,055,901 points, 19,090 matches |
| `match_sources.parquet` | One row per (Stage 0 match, source): gate numbers, known points, raw-flag points, `chosen_all`, `chosen_without_p9` | |
| `atoms.parquet` | **Task 3.** One row per (Stage 0 match, player): serve and return points by band and won, rally sums, shots hit, net counts with coverage, `pts_known`, and Stage 0's date, round order, level, draw, surface | 38,180 |
| `depth.csv`, `depth.json`, `depth_rows.parquet` | **Task 4.** Every cell (variant × level group × draw × half); the headline; one row per target player-match with both counts | 51,432 target rows |
| `depth_checks.json`, `depth_composition.csv` | Task 4's checks: what each arm is made of, by source; the 2 Oct baseline; the upper bound; the largest count per match; spot checks | |
| `convention.json`, `convention_agreement.csv` | **Task 1.** Inside P9, and against the other sources | |
| `reliability.csv`, `reliability.json` | **Task 5** | 60 rows |
| `probe.json` | **Task 6** | |
| `rally_points_summary.json`, `atoms_summary.json` | Counts by source and year | |

**Code** (`src/eda/p9_point_details/`):

| Script | What it does | Run time |
|---|---|---|
| `build_common.py` | Shared pieces: the MatchBeats reader, the convention and per-event rule, bands, gate, Stage 0 loaders, the 52-week sums | – |
| `build_link.py` | The links and the crosswalk | ~1.5 min |
| `build_points.py` | The point table | ~50 s |
| `build_atoms.py` | The atoms | ~5 s |
| `build_depth.py` | The depth table | ~5 s |
| `build_depth_checks.py` | Task 4's checks | ~40 s |
| `build_convention.py` | Task 1's checks | ~1.5 min |
| `build_reliability.py` | Task 5 | ~15 s |
| `build_probe.py` | Task 6 | ~3 min |

**Tests:** `test/p9_point_details/test_build.py`, 6 tests, all passing.

**Reproduction**, in order:

```
./python.sh src/eda/p9_point_details/build_link.py
./python.sh src/eda/p9_point_details/build_points.py
./python.sh src/eda/p9_point_details/build_atoms.py
./python.sh src/eda/p9_point_details/build_depth.py
./python.sh src/eda/p9_point_details/build_depth_checks.py
./python.sh src/eda/p9_point_details/build_convention.py
./python.sh src/eda/p9_point_details/build_reliability.py
./python.sh src/eda/p9_point_details/build_probe.py
./python.sh -m pytest test/p9_point_details -q
```

**The bands** (`band`: 0 double fault, 1 = 1–2 shots, 2 = 3–4, 3 = 5–8, 4 = 9+):
* **1–2:** the points the serve and the return decide (aces, unreturned serves, return errors, return winners).
* **3–4:** the serve-plus-one and return-plus-one. Their upper edge at 4 is the shot-level study's "quick points" (won within 4 shots).
* **5–8:** that study's "rally points" from 5 shots.
* **9+:** its "long rallies". It is also the cap of Infosys's groups ("9+ odd", "10+ even"), so every source can be banded alike.

Shares in the table *(observed; `rally_points_summary.json`)*: double faults 3.6%, 1–2 30.1%, 3–4 30.0%, 5–8 23.6%, 9+ 12.6%.

## The convention and its checks (task 1)

**What `tm1Rally + tm2Rally` counts** *(observed, point by point on a 2026 Masters final, then on all P9; `convention.json` A1)*:
* Each team's shots that landed in, the serve included.
* An ace is 0 + 0 and a double fault 0 + 0.
* A winner's count includes the winning shot; an error's count excludes the erring shot.

| Ending (MatchBeats `result`) | Rule into the shot-level convention | Points compared with the rally file's category | Equal |
|---|---|---:|---:|
| Ace (`A`) | 1 | 217,263 | 100% |
| Double fault (`DF`) | 0 (category "Serve") | 119,425 | 100% |
| Winner (`W`) | the count | 140,350 | 98.8% |
| Forced error (`FE`) | the count + 1 | 176,755 | 99.3% |
| Unforced error (`UE`) | the count + 1 | 202,551 | 98.9% |
| Unclassified (`N`), resolved by the rally file's list (`t1win`/`t1err` …) | won: the count; erred: + 1 | 12,362 | 99.9% |

Comparisons are made after the categories' cap (9 = "9+ odd", 10 = "10+ even"). The two players' counts are consistent with this rule: the last ball in belongs to the point's winner.

**Special cases** *(observed; `build_common.mb_convention`, `test_build.py`)*:
* A count of 1 won by the server is shot 2, whether it is coded a winner or left unclassified. It is a serve won without an ace, which the shot-level convention codes as the returner's forced error.
* An unclassified ending of 2+ shots that the rally file does not name stays unknown (`n_unresolved`: 3,416 P9 points).
* Where the count is unusable but the rally file names the category, the category is used, as the Hugging Face copy's adapter does (`how = ra`: 13,559 P9 points).

**The newer recount (`tm1Shot`/`tm2Shot`) is not used** *(observed; `convention.json` A2)*:
* It equals the category on 77.2% of rally-ended points, against 99.0% for the old count with the ending: 70.8% of forced errors, 71.0% of unforced, 94.1% of winners. It adds the erring shot on only part of the errors.
* Where the old count is missing (2,267,284 points other than aces and double faults), the recount is positive on 3,938. The gate's "23,382 fills" are mostly the 22,031 double faults it counts as 1. A double fault's rally length is 0 by the ending anyway.
* *Inferred:* it brings no rally length the old count lacks, and it is less consistent.

**What the "known" flag covers** *(observed; `convention.json` A4)*. In matches where the flag covers at most half the points other than aces and double faults:
* the flagged rally points have counts of 0 (46%) or 1 (53%);
* only 61.5% of the counts of 1 or more pass the parity check, where the server wins about 62% of points anyway.

In matches flagged on more than 90%:
* 1.4% of counts are 0;
* parity holds on 97.6%.

*Inferred:* in the first group the flag marks the aces and double faults (always "known") plus defaults, not measured rallies. The study therefore counts a match's rally lengths only when the match **carries** them: at least 90% of its points other than aces and double faults have a valid rally length (the shot-level study's gate, `build_common.GATE`).

| P9 (`convention.json` A4) | Matches | Carrying rally length |
|---|---:|---:|
| 1000s main / qualifying | 1,427 / 511 | 1,398 / 458 |
| 500s main / qualifying | 913 / 380 | 394 / 159 |
| 250s main / qualifying | 1,548 / 673 | 708 / 319 |
| Finals | 15 | 15 |
| Challengers main / qualifying | 12,494 / 7,139 | 566 / 313 |

* By season, after linking *(observed; `links.parquet`)*: Challenger main draws carry rally length in **25** P9 matches of 2025 and **541** of 2026. *Inferred:* the 2026 ones are the Challengers with radar and ball tracking (P9 report § 9.3: 790 such matches).

**Two counting rules** *(observed; `convention.json` `event_rules`; `build_common.event_rules`)*. Each event's rule is read from parity on its tracked errors:
* "standard" when ≥ 80% fit P9's rule;
* "inclusive" (the erring shot counted) when ≤ 20% fit;
* else "unclear", read as standard.

Results:
* P9: 87 events standard, 1 inclusive (`2026|3121`), 283 unclear. The unclear ones are dominated by junk counts, and their matches fail the gate.
* **Roland Garros 2026's Infosys files (`infosys_slams`) are inclusive**: 9% of their errors fit the standard rule, 91% the inclusive one. AO and RG 2025 are standard. *Unknown:* why the files differ; this was found from the data, not documented by the source.

**Against the earlier sources** *(observed; `convention_agreement.csv`)*. Points are aligned by their order in the match. A match is kept when the two sources agree on the server and the point winner of ≥ 98% of its points, as the shot-level study's Stage 1 did. Where one side is capped, both are capped.

| Pair | Matches both carry | Aligned | Points | Rally equal | Within 1 | Band equal | Same side of 5 / 9 | Equal, aces and double faults excluded |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P9 / SirGenkii (same ATP files, capped) | 339 | 238 | 34,892 | 99.2% | 100.0% | 99.9% | 99.9% / 100.0% | 99.1% |
| P9 / TDI | 1,117 | 1,034 | 148,853 | 98.2% | 99.6% | 99.5% | 99.8% / 99.9% | 98.0% |
| P9 / Hugging Face Infosys copy (capped) | 8 | 5 | 693 | 99.3% | 99.9% | 99.9% | 100% / 100% | 99.2% |
| P9 / volunteer charts | 325 | 303 | 42,549 | 96.7% | 99.9% | 98.8% | 99.6% / 99.8% | 96.5% |
| AO/RG Infosys files / charts | 97 | 94 | 20,696 | 98.4% | 99.3% | 99.4% | 99.7% / 99.9% | 98.3% |
| TDI / charts | 24 | 23 | 3,126 | 98.7% | 99.9% | 99.8% | 99.8% / 100% | 98.6% |
| SirGenkii / charts (capped) | 147 | 110 | 16,058 | 98.5% | 99.9% | 99.7% | 99.8% / 100% | 98.4% |

* *Inferred:* the mapping puts P9 in the shot-level convention. P9 and the charts agree better than the shot-level study's Hugging Face Infosys copy and the charts did (81% equal, `stage1_agreement.csv`).
* The mean difference is under 0.03 shots in every pair, so no source counts systematically longer.

## Links (task 2)

**The crosswalk** *(observed; `link_report.json` `crosswalk`)*:
* Votes come from strict name links: both surnames and both first names, unique in the event and draw.
* 2,351 codes received votes; 2,347 kept (share ≥ 0.8); 4 below.
* Agreement with the live speed linker's cache: 99.7% of 1,768 shared codes. With the source reconciliation's crosswalk: 99.7% of 2,012.
* 2,441 of the 2,774 codes the ATP-format files use are mapped.
* 308 Stage 0 ids carry two codes.
  * 303 pair a numeric old-style ATP id from the 2018–24 files (e.g. `11674`) with a four-character code.
  * 5 pair two four-character codes: `A0NB`/`A0OO`, `C0QV`/`C0UZ`, `F0H6`/`M1A0` from name votes; `J0A4`/`J0EO` and `A0IQ`/`D0ID`, where one code comes from the live speed crosswalk's fallback.
  * *Unknown:* whether these are one player under two codes (as the P9 report found for one Bahrain Challenger player) or slips. An id link still needs both players' ids on one match of the same event and draw, so a slip can hardly produce a wrong link (open problem 11).

**P9's link methods** *(observed)*:

| Method | Matches |
|---|---:|
| ids and names agree | 22,835 |
| ids only | 165 |
| names only (strict) | 18 |
| names only (loose) | 6 |
| ids by the date window (event not in Stage 0) | 2 (counted in "ids") |
| **Unlinked:** conflict between names and ids | 2 |
| **Unlinked:** duplicate of another copy | 3 |
| **Unlinked:** event not in Stage 0 (Fujairah 2026, Wuning Open 3 2026, Basel 2026) | 72 |
| **Unlinked:** no candidate in the event and draw | 2,014 |

**Rates** *(observed; `links.parquet`, `link_report.json` `rates`)*:

| Season | Level | Draw | P9 matches | Linked | Rally-carrying | Of those linked |
|---|---|---|---:|---:|---:|---:|
| 2025 | Tour | Main | 2,038 | 100.0% | 1,236 | 100% |
| 2025 | Tour | Qualifying | 805 | 100.0% | 422 | 100% |
| 2025 | Challenger | Main | 6,366 | 99.7% | 25 | 100% |
| 2025 | Challenger | Qualifying | 3,576 | 95.6% | 14 | 100% |
| 2026 | Tour | Main | 1,880 | 97.8% | 1,279 | 100% |
| 2026 | Tour | Qualifying | 759 | 98.9% | 514 | 100% |
| 2026 | Challenger | Main | 6,128 | 99.4% | 541 | 100% |
| 2026 | Challenger | Qualifying | 3,563 | **48.6%** | 299 | **18.1%** |

**The failures** *(observed; `link_failures.csv`)*:
* 1,955 of the 2,014 "no candidate" are Challenger qualifying: 1,799 in 2026, 156 in 2025. *Inferred:* the repository's Stage 0 lacks most of 2026's Challenger qualifying, since Sackmann's files ended in June and the lower-level feed is merged only into builds (CLAUDE.md). It is not a linker miss: the same players link elsewhere.
* The other 59 are 35 tour and 24 Challenger main-draw matches, none carrying rally length.
* The 245 unlinked rally-carrying matches are all 2026 Challenger qualifying. Their effect on task 4 is bounded below (upper bound 1.08).

**Checks without results** *(observed; `link_report.json`)*:
* **Orientation.** Each player's aces in the P9 points against Stage 0's box score: equal in the link's orientation for 21,896 of 22,475 matches (97.4%). Of the 20,213 informative matches (where swapping would change the comparison), 20,207 are closer in the link's orientation and 6 when swapped. *Unknown:* the 6 were not examined one by one.
* **Rounds.** 10 main-draw links have a round label different from the match code's: infosys_atp's 2021 event 8888, whose codes do not follow the bracket.
* **Other ATP-format files:** infosys_atp 2,046 of 2,070 linked, infosys_challengers 2,354 of 2,375, infosys_slams 704 of 717. All their rally-carrying matches are linked.

**The shot-level sources** *(observed; `link_report.json` `shot_level`)*:
* 48,871 of 49,954 men's 2017+ source matches were carried from the 2 Oct links by the rebuilds' id maps.
* Of the 1,083 left, 31 re-linked to today's Stage 0.
* TDI read from today's dump: 6,021 men's matches, 4,181 linked (the 2 Oct table: 4,698 read, 3,146 linked).

## The point table and the atoms (tasks 2 and 3)

*Observed; `rally_points_summary.json`, `atoms_summary.json`.*

* **The table:** 3,055,901 points in 19,090 Stage 0 matches, 2018–2026, with 868,758 points in 2026 and 502,233 in 2025.
* **The source that gives each match:**

| Source | Matches | Points |
|---|---:|---:|
| Hugging Face Infosys copy | 4,898 | 684,444 |
| P9 | 4,085 | 595,728 |
| TDI | 2,946 | 417,410 |
| Slam feeds (slamtracker) | 1,912 | 385,866 |
| Sackmann's Slam files | 1,588 | 358,023 |
| Volunteer charts | 1,924 | 288,345 |
| AO/RG Hawk-Eye copy | 590 | 133,875 |
| AO/RG Infosys files | 477 | 95,362 |
| SirGenkii | 533 | 78,188 |
| infosys_atp | 132 | 17,758 |
| infosys_challengers | 5 | 902 |

* **Overlaps:** 1,702 matches are carried by P9 and another source: TDI 1,117, SirGenkii 339, the charts 325, the Hugging Face copy 8. P9's count there equals the other's on average (140.5 against 140.7 points).
* **Net flags:** P9 records net points at its 24 flagged events, 24.9% of its points in the table. The Slam feeds, TDI and the charts record them on nearly all of theirs. `net_cov` in the atoms marks the matches.
* **The atoms:** 38,180 rows, two per match. Asserted:
  * every point is counted once on serve and once on return;
  * points won on serve plus points won on return equal the points.

## Depth: the stopping rule's number (task 4)

**Definition** (`build_depth.py`):
* **The clock:** Stage 0's `tournament_date` and `round_order`. A target counts the player's own matches at events with an earlier tournament date within 364 days (dates in [date − 363, date − 1]), plus earlier rounds of the same event. Never the match itself, its round or another event of the same date.
* **The count:** a history match's points with a known rally length, double faults excluded, from the first source in the preference order (P9, the ATP's other files, the Slams' feeds, TDI, the charts) among those that carry the match.
* **The arms:** "with P9" uses every source; "without P9" every other source on disk today, including the AO/RG Infosys files and TDI's refreshed dump.
* **The population:** men's Stage 0 matches, tournament date 2025-01-01 to 2026-10-18, completed or retired, at the Slams, Finals, 1000s, 500s, 250s and Challengers. Not restricted to matches with a price on file (see open problems).
* **The ratio** per player-match is with / without: 1 when both are 0 (no gain), infinite when only "with" is positive.

**The table** *(observed; `depth.csv`, variant `gate_0.9`, all halves)*:

| Level group | Draw | Player-matches | With P9: q25 / median / q75 | Without P9: q25 / median / q75 | Median ratio | Ratio of medians | Both ≥ 300, with / without | Both ≥ 1,000, with / without |
|---|---|---:|---|---|---:|---:|---|---|
| Slams | Main | 2,018 | 3,690 / 5,321 / 6,810 | 1,853 / 3,431 / 5,318 | 1.35 | 1.55 | 97.5% / 95.5% | 92.3% / 79.2% |
| Slams | Qualifying | 1,786 | 572 / 1,315 / 2,469 | 338 / 804 / 1,659 | 1.22 | 1.64 | 71.9% / 59.8% | 36.5% / 24.0% |
| 250s to Finals | Main | 7,830 | 3,871 / 5,332 / 6,750 | 1,923 / 3,414 / 5,234 | 1.40 | 1.56 | 97.2% / 94.6% | 91.3% / 81.0% |
| 250s to Finals | Qualifying | 3,098 | 770 / 2,046 / 3,802 | 495 / 1,251 / 2,394 | 1.26 | 1.64 | 71.5% / 64.4% | 49.3% / 34.5% |
| Challengers | Main | 25,964 | 99 / 485 / 1,558 | 0 / 343 / 1,127 | **1.00** | 1.41 | 39.3% / 33.0% | 18.0% / 13.1% |
| Challengers | Qualifying | 10,736 | 0 / 0 / 150 | 0 / 0 / 110 | 1.00 | – | 2.9% / 1.8% | 0.6% / 0.3% |
| **Headline: tour + Challenger main draws** | Main | **35,812** | 196 / 1,093 / 3,820 | 125 / 753 / 2,317 | **1.069** | 1.45 | 55.3% / 50.0% | 38.2% / 31.7% |
| Tour main only (Slams + 250s to Finals) | Main | 9,848 | 3,834 / 5,329 / 6,757 | 1,903 / 3,416 / 5,252 | 1.39 | 1.56 | 97.3% / 94.8% | 91.5% / 80.6% |

**By half-year of the target** *(observed; `depth.csv`)*:

| Main draws | 2025H1 | 2025H2 | 2026H1 | 2026H2 (to 18 Oct) |
|---|---:|---:|---:|---:|
| Headline population: median ratio | 1.00 | 1.00 | 1.75 | 1.27 |
| Headline: ratio of medians | 1.02 | 1.36 | 1.90 | 1.39 |
| Slams | 1.06 | 1.28 | 2.10 | 1.76 |
| 250s to Finals | 1.00 | 1.32 | 2.18 | 1.81 |
| Challengers | 1.00 | 1.00 | 1.40 | 1.15 |

**Variants of the headline** *(observed; `depth.json`, `depth_checks.json`)*:

| Variant | Median ratio | Excluding 0/0 rows | Ratio of medians | Tour main | Challenger main |
|---|---:|---:|---:|---:|---:|
| **As declared** (gate 0.9, every other source today) | **1.069** | 1.202 | 1.452 | 1.391 | 1.000 |
| Gate 0.5 | 1.118 | 1.247 | 1.468 | | |
| Each match's largest count among its sources | 1.069 | 1.202 | 1.452 | 1.391 | 1.000 |
| Upper bound: P9's 245 unlinked rally matches added to "with" only | 1.082 | 1.220 | 1.472 | 1.391 | 1.000 |
| "Without" = the shot-level study's own tables (2 Oct: no AO/RG Infosys files, TDI as it was then) | 1.191 | 1.361 | **1.679** | 1.564 | 1.000 |
| Raw flags, no gate: P9's "known" flag including aces, double faults and 0/1 junk (**not a valid count**; shown to explain the gate's coverage claim) | 2.184 | 2.207 | 2.185 | | |

**What each arm is made of** *(observed; `depth_composition.csv`; mean 52-week points per player-match)*:
* **Tour main, 2026H1:** with P9, P9 3,265 + Slam feeds 799 + AO/RG Infosys files 382 + charts 311 + SirGenkii 172 + TDI 65. Without P9: Slam feeds 799, charts 742, AO/RG Infosys 382, SirGenkii 361, TDI 177.
* **Challenger main, 2026H2:** with P9, TDI 963 + P9 721. Without P9: TDI 1,191.

**Spot checks** *(observed; `depth_checks.json`)*:
* Zverev at Rome 2026 R16: with P9 9,146 (P9 6,128), without 4,803.
* Sinner at Rome 2026: with 11,154, without 9,237. The charts alone give him 4,876 points in 52 weeks.

**Reading it** *(inferred)*:
* The pooled number is low for three reasons:
  1. 2025H1 targets cannot gain, since P9 starts in January 2025.
  2. Challenger main draws, 73% of the headline population, gain little: P9's Challenger files carry real rally lengths for 25 main-draw matches in 2025 and 541 in 2026, and TDI already covers Challengers from mid-2026.
  3. 16% of the headline player-matches have no rally history either way.
* Where P9 adds depth, it adds a lot: 2.1–2.2× for tour-level targets of 2026H1, the gap the shot-level study named.
* **For the lead** (not my decision):
  * As instructed (the median of per-player ratios), every variant is below 1.5.
  * The shared context's wording ("the median player-match's count … 1.5 times what the same matches had") could be read as the ratio of medians. That is 1.45 against today's other sources, and **1.68** against the shot-level study's 2 Oct tables.
  * Restricted to tour-level main draws, the median ratio is 1.39 (1.56 against the 2 Oct tables), and the ratio of medians 1.56.

## Reliability (task 5)

*Description only; `build_reliability.py`, `reliability.csv`.*

**Method:**
* Windows: the 52 weeks ending 31 Dec 2025 (2025-01-02 to 2025-12-31) and those ending 18 Oct 2026 (2025-10-21 to 2026-10-18).
* Players with ≥ 6 matches with rally data in the window.
* 50 random splits of each player's matches into halves. A half's rate is the sum of numerators over the sum of denominators. Pearson's r across players, averaged over the splits.
* Chance: the 97.5% point of r with halves shuffled across players.
* Without P9, P9's matches take the next carrying source's points, or drop out.

| Rate | 2025, with P9 | 2025, without | 2026, with P9 | 2026, without | Shot-level study's nearest (men, all years, 30+ matches) |
|---|---:|---:|---:|---:|---|
| Serve points ending by shot 2 (double faults excluded) | 0.705 | 0.655 | 0.762 | 0.754 | – |
| … by shot 4 | 0.762 | 0.730 | 0.817 | 0.797 | quick points won on serve 0.77 (a different definition) |
| … at 9+ | 0.752 | 0.734 | 0.795 | 0.782 | share of long points (5+) 0.85 |
| Serve points won, 1–2 / 3–4 / 5–8 / 9+ | 0.39 / 0.19 / 0.10 / 0.21 | 0.43 / 0.20 / 0.13 / 0.18 | 0.38 / 0.25 / 0.18 / 0.10 | 0.39 / 0.21 / 0.16 / 0.08 | 5+ won 0.68; 9+ won 0.55 |
| Return points won, 1–2 / 3–4 / 5–8 / 9+ | 0.35 / 0.27 / 0.23 / 0.03 | 0.34 / 0.29 / 0.31 / 0.03 | 0.36 / 0.21 / 0.20 / 0.11 | 0.33 / 0.18 / 0.18 / 0.09 | quick points won on return 0.72 |
| Mean rally length on serve (capped 9/10) | 0.814 | 0.786 | 0.854 | 0.842 | – |
| Mean rally length on return | 0.480 | 0.522 | 0.617 | 0.618 | – |
| Net approach rate | 0.499 | 0.423 | 0.606 | 0.654 | 0.94 |
| Net points won | 0.013 | 0.027 | 0.105 | 0.110 | 0.55 |
| Players | 232 (net 216) | 199 (184) | 492 (483) | 474 (474) | |
| Serve points per half, double faults excluded (mean) | 921 | 668 | 800 | 643 | |

Chance bands (97.5%) are 0.07–0.18 across rows.

**Observed:**
* Points won on 9+ rallies on return (2025, 0.03) and net points won (2025, 0.01–0.03) are at or below the chance band.
* r varies by 0.01–0.10 (SD) over the 50 splits.

**Inferred:**
* The style shares (how a player's serve points end) are stable traits within one season.
* Who wins the points of each length is mostly noise at one season's depth: ~110 points of 9+ per half.
* P9 adds players and points but does not change the picture.
* The shot-level study's higher values come from all years and 30+ matches per player, not from better data.

## The timing probe (task 6)

*Observed; `build_probe.py`, `probe.json`.*

**The aggregate:** every atoms row's 52-week sums of points won (on serve, on return, by band) and points played, on Stage 0's clock.

**The probes:**
1. **Stage 0's clock.** 20 random cut days, 2019-02-11 to 2026-08-30. Every point winner of matches dated after the cut was scrambled (each point given at random to one of the two players), the atoms rebuilt and the sums recomputed.
   * 0 of 226,596 row-comparisons dated on or before a cut moved.
   * 508,897 of 537,004 after the cuts moved.
2. **Real dates** (the match clock). 9 cuts where events overlap: the second Wednesday of the eight 2025–26 Slams, and 9 Aug 2025 during Cincinnati. Every match that surely started after D (`es > D`) was scrambled.
   * 0 rows of matches that surely finished by D (`lf ≤ D`) moved, out of 20,728–35,472 per cut.
   * 2,141–16,412 per cut of the surely-later rows moved.
3. **The match itself.** For 200 random rows, the match, the same event's same and later rounds, and every later date were scrambled.
   * 0 of the 200 rows moved.
   * In 192 probes, the player's later rows did move.

*Inferred:* the aggregator reads only strictly earlier matches, and the Stage 0 clock agrees with the real dates for a player's own history.

## Open problems

1. **Stage 0 lacks about half of 2026's Challenger qualifying** *(observed: P9 links 48.6% of it)*. 245 P9 rally-carrying matches cannot enter the atoms. Their effect on task 4 is bounded (1.07 → 1.08). TDI's 1,840 unlinked matches, mostly the same kind, are left out of the without-P9 arm, so the bound is generous to P9.
2. **The prices.** The population is every completed or retired main-draw match, not only those with a price on file; the harness agent holds the prices. *Unknown:* the headline on priced matches only. *Inferred:* unlikely to cross 1.5, since tour-level main draws alone give 1.39.
3. **The reading of the stopping rule** (median of ratios against ratio of medians; today's other sources against the shot-level study's): only one corner crosses 1.5 (ratio of medians against the 2 Oct tables, 1.68). For the lead.
4. **Six P9 matches' aces fit the swapped orientation better** (of 20,213 informative). Not examined one by one.
5. **The 2018–21 ATP files (`infosys_atp`)** leave most endings unclassified and their rally files unnamed: 132 of 574 matches carry rally length. Irrelevant to 2025–26, but the 2018–21 history is thinner than the files' size suggests.
6. **Roland Garros 2026's files count the erring shot** (found from parity). *Unknown:* whether other years or sources do. The per-event rule guards the ATP-format files only; the shot-level tables keep that study's conventions, which its agreement checks validated.
7. **The charts and the Slam feeds are as the shot-level study read them on 2 Oct** (their dumps: 22–24 Sep). Only TDI was refreshed.
8. **Mean rally length** uses lengths capped at 9/10, as Infosys's groups are, so sources compare. P9's exact counts are in `rally` (up to 60) for any later use.
9. **Net play** in P9 exists at 24 events only (`net_cov`). Its reliability above leans on the Slam feeds, TDI and the charts.
10. **Unit tests** cover the convention, the gate, bands and the window. The linker is checked by the ace and round checks, not by a hand-made test.
11. **Five Stage 0 ids carry two four-character ATP codes** in the crosswalk (see "Links"). Not resolved; the id pass needs both players on one match of the event and draw, which limits the harm.

## Process notes

Written while working, in order. Corrections are added, never rewritten.

* **08:58 local, start.** Commit `9228b26` with many uncommitted changes elsewhere. Read the brief, the shared context, the study's process log, `field_profile.json` and `field_profile.py`, the shot-level study's `stage0.md`, `stage1.md`, `points.py`, `stats.py`, `common.py`, `stage1_reliability.py`, the serve-speed acquisition README § 9 (P9), the data map's `load_infosys_atp_recent` and `build()`, Stage 0's builder's TML-to-Sackmann crosswalk, and the live speed linker `src/eda/serve_speed_tabpfn/live/link.py`. No match result read.
* **The lead's instruction to me, verbatim** (the launch message): "The single most important output is task 4's number. Take the median ratio of each player's 52-week count of points with a known rally length, with P9 against without P9, on men's 2025–26 tour-level main draws and Challenger main draws. The study stops if it is below 1.5. Get that number done and checked before spending time on reliability. The machine is shared with other Claude sessions that are editing pipeline and ingest files today: keep to your own paths, use at most 4 worker processes, and leave nothing running when you finish."
* **Crosswalk options found (08:58).**
  * Stage 0's own TML-to-Sackmann crosswalk is computed inside `stage0_build.py` and not saved.
  * `src/eda/serve_speed_tabpfn/live/link.py` learns ATP code → project id from ManTennisData links, the Infosys handoff's shot-level links and Tennis My Life's 2024–26 rows (80% vote share). Its `crosswalk()` **writes** a cache (`data/studies/serve_speed_tabpfn/live/crosswalk.parquet`) when Stage 0 changed, so I must not call it: I import its read-only helpers instead and write my own copy.
  * `src/eda/source_reconciliation/atp_crosswalk.py` wrote `data/studies/source_reconciliation/box/atp_crosswalk.parquet` from ManTennisData on a frozen snapshot of Stage 0.
* **09:00–09:25, first looks at the convention (inline scratch scripts, not kept in the repo; their results are re-derived by `build_convention.py`).** No match result read.
  * On a 2026 Masters match (event 807, MS001), point by point: `tm1Rally + tm2Rally` counts **the shots that landed in, the serve included; an ace is 0, a double fault 0**. A winner's count equals the shot-level rally length; an error's count is one less (the erring shot is not counted). So the shot-level convention is: ace 1, double fault 0, winner = count, error = count + 1.
  * Against the rally files' `category` (all P9, 875,591 tracked points joined): aces and double faults 100%; winners equal 98.8%, forced errors 99.3%, unforced errors 98.9% (comparing after the rally files' cap at "9+ odd" / "10+ even").
  * **The newer recount (`tm1Shot`/`tm2Shot`) is inconsistent:** it adds the erring shot on about half the error points only (equal to the rally files' category on 71% of errors against 99% for the old count + ending rule). Where the old count is missing, the recount is 0 on nearly every point; its 23,382 "fills" are 22,031 double faults counted as 1 and about 1,000 others. **Decision: the recount is not used.**
  * **Unclassified endings (`N`)** leave a ±1 ambiguity (winner: count; error: count + 1). The rally files' `list` (`t1win`/`t1err`…) resolves it where they name the point (99.5% equal to the category); a count of 1 won by the server is shot 2 either way.
  * **The big one: the `rallyLengthMissing == 'FALSE'` flag is not "rally length measured".** In matches where under half the points are flagged, the flagged points are the aces and double faults (99.9% flagged) and about 11% of the other points, whose counts are 0 or 1 (a winner with 0 shots in is impossible). Parity check (the last ball in must be the point winner's): 61% for count 1 in those matches, against 98% in matches tracked on more than 90% of points.
  * **Real tracking, by match** (share of points other than aces and double faults with a plausible count, ≥ 0.9): 1000s main 1,402 of 1,422, qualifying 461 of 510; 500s main 397 of 906; 250s main 707 of 1,479; Finals 15 of 15; **Challenger main 522 of 12,488, qualifying 285 of 7,136.** The rally files name their categories in the same matches (Challenger main 572). The gate's "25–35% of points at Challengers" was aces, double faults and junk. This is expected to weigh heavily on task 4.
  * **Other ATP-format files staged since the shot-level study** that carry rally counts (same MatchBeats format): `data/dump/points/infosys_slams/` (AO 2025 partly, RG 2025 and 2026, men's main and qualifying), `infosys_challengers/` (2021–24), `infosys_atp/` (2018–22). They are not P9, so they belong to both arms of task 4. TDI's dump was refreshed on 26 Oct, after the shot-level table (2 Oct): it is rebuilt from today's dump with the shot-level adapter and re-linked.
* **Correction (added at 09:25):** the times in the note above were estimates. The clock read 09:25 after the depth checks below, so everything up to here took about 27 minutes.
* **Code written** (`src/eda/p9_point_details/`): `build_common.py` (paths, the MatchBeats reader with each point's rally-file row beside it, the convention, bands, the match gate, Stage 0 loaders, the 52-week as-of sums), `build_link.py`, `build_points.py`, `build_atoms.py`, `build_depth.py`, `build_depth_checks.py`; tests `test/p9_point_details/test_build.py` (6, passing: the convention on hand-made points, an inclusive event, bands and cap, the gate, the windowed sums against a direct look-back on 400 random rows, and a hand-worked window).
* **A second counting rule found while smoke-testing:** Roland Garros 2026's Infosys files (`infosys_slams`) count the erring shot (the last counted ball is the loser's on 91% of its errors; RG 2025 and AO 2025 follow P9's rule). `build_common.event_rules` now reads each event's rule from parity: standard at ≥ 80% of tracked errors fitting P9's rule, inclusive at ≤ 20%, else "unclear" (read as standard; junk-dominated events, whose matches then fail the gate). P9: 87 events standard, 1 inclusive (`2026|3121`), 283 unclear (all junk-dominated). With the rule, RG 2026 carries rally length on 477 of 698 AO/RG men's matches instead of 287.
* **Failure and fix:** `build_link.py` first stopped in the data map's Slam linker (`KeyError: 'year'`): the shot-level linker needs a `year` column for Grand Slam rows. Added it to both re-link calls.
* **Link variants considered.** (a) The live speed linker's crosswalk alone: rejected, 2,480 codes, mostly tour level. (b) The source reconciliation's crosswalk: built on a frozen snapshot of Stage 0. (c) **Chosen:** a crosswalk learned from P9 and the other ATP-format files themselves (strict name links inside each event and draw vote code → Stage 0 id, ≥ 80% share), with (a) and (b) as fallbacks only for codes with no vote. It agrees with (a) on 99.7% of the 1,768 codes both hold and with (b) on 99.7% of 2,012. Links need the name pass and the id pass to agree, or one alone; 2 P9 conflicts are left unlinked.
* **The 2 Oct shot-level links** carry to today's ids through the rebuilds' id maps (48,871 of 49,954 men's 2017+ source matches; the rest re-linked to today's Stage 0: 31 more). TDI read again from today's dump: 6,021 men's matches, 4,181 linked (the 2 Oct table held 4,698, 3,146 linked).
* **09:10–09:25, task 4 (no result read).** First run: headline 1.069. Then the checks in `build_depth_checks.py`: what each arm is made of, the 2 Oct baseline, P9's unlinked matches, the largest count per match. Every per-player median ratio stays below 1.5; one reading crosses it (the ratio of medians against the 2 Oct baseline, 1.68). Details in "Depth" above.
* **Choices in task 4, and why** (made before the first depth number was seen, except where marked):
  * **The clock:** Stage 0's tournament date and round order (the brief's first option). It is safe for a player's own history, and the probe later confirmed it against the real dates.
  * **The window:** dates in [date − 363, date − 1] plus earlier rounds of the same event, i.e. the 51 weeks before plus the current week's earlier rounds. With Monday dates, the previous year's edition (364 days before) falls out, so the window covers 52 weeks of play.
  * **The count excludes double faults.** They are known from the ending in every source, measured or not. Aces are counted inside matches that carry rally length.
  * **The gate is the shot-level study's** (90% of points other than aces and double faults). Chosen because P9's flag proved to mark junk; the 0.5 variant was added after the first number was seen, as a check.
  * **"Without P9" is every other source on disk today,** the brief's "count with every source, and without P9". The 2 Oct baseline was added after the first number, as a check.
  * **Zero rows:** a ratio of 1 for 0/0 and infinite for x/0, set before the run. The "excluding 0/0" variant was added after.
  * **The population:** tournament dates 2025-01-01 to 2026-10-18, completed or retired. Not restricted to priced matches, since the prices are the harness agent's.
* **09:26–09:30, task 1** (`build_convention.py`). **Failure and fix:** my first draft aligned the raw recount columns to the sorted point frame by position, which would have misaligned them. It was caught before running; the recount is now merged by match and point id.
* **09:29–09:31, task 5** (`build_reliability.py`).
  * **Failure and fix:** the without-P9 atoms' rebuild hit a duplicate `player_a_id` column, because `orient()` had already joined Stage 0's sides; those columns are now dropped before `atoms()`.
  * **Variants considered for the minimum per player:** 6 matches (3 per half) chosen, to keep a few hundred players in a one-season window; the shot-level study's 30 matches would leave too few within 52 weeks. Not varied.
  * **The 2026 window** ends at the data's end (18 Oct), so it overlaps the 2025 window from 21 Oct to 31 Dec 2025.
* **09:31–09:34, task 6** (`build_probe.py`). Three probes, all clean on the first run.
* **09:35, memo.** Two claims were corrected against the files before the final version: 1,799 (not 1,830) "no candidate" 2026 Challenger qualifying matches (1,830 was the count of all unlinked ones); and the 308 two-code ids, which are not all numeric pairs (5 are two four-character codes).
* **Session housekeeping.** Scratch scripts are in the scratchpad (`…/scratchpad/p9b/`), outside the repository. No process is left running. Nothing was written outside the brief's paths. No Git command that changes state was run.

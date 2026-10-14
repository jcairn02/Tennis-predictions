# Roland Garros 2022–2025 and the Paris Olympics: recounting the first serves

9 October 2026 · Item 6 of the [adoption checklist](../adoption_framework/checklist.md), steps 1–2 only: the recount and the reviewers' check. Later the same day, the follow-ups the report suggested (§ 8): RG's whole box score under the Slam rule of 6 Oct, and four exchanged boxes. Then, at the owner's word, the rule extended to Sackmann's own rows and the swapped service games of both Infosys Slams corrected (§ 9). ~~**Steps 3–4 (the candidate build and the harm check) are left for a later session, as asked. Nothing here changes Stage 0 or the model.**~~ **Updated 10 Oct 2026:** steps 3–4 ran at the owner's word ("Execute these 3 fixes"). The harm check found no harm, and the candidate is adopted under the declared rule (§ 10.3). Its tables enter Stage 0 at the next coordinated rebuild (§ 10.4); until then Stage 0 and the model are unchanged. Process log: [process_log.md](process_log.md).

**The request** (owner, 9 Oct 2026): "Carry out only steps 1–2 of item 6 … (the recount and the reviewers' check). Stop before the candidate build: save the confirmed corrections and write their path under item 6, as step 2 says. Don't tick the item yet."

**Labels.** **Observed** = computed here, with its file; *inferred* = reasoning.

## In short

**Step 1: yes, first serves in and serve points can be recounted match by match, and the recount validates** (observed).
* **Roland Garros's own records exist for every edition.** Both were collected today under the 8 Oct scraping approval:
  * RG's own match statistics, 2019–2025, qualifying included (rolandgarros.com);
  * RG's own point-by-point (the Infosys MatchBeats files), 2019–2024.

  The 8 Oct reviewers excluded 2022–24 because "no per-match record is held". It is held now. The Paris Olympics have their own official results files, with a play-by-play.
* **The recount is exact wherever a point file is complete:**
  * at the Australian Open 2025 against Stage 0's AO rows: 731 of 731;
  * at the Olympics against their own statistics: 243 of 243;
  * at RG against its own statistics, in every edition 2019–2025.

  The rows that differ are point files missing points.
* **Before the fault, RG's statistics are Sackmann's.** In 2019–2021 they equal Sackmann's rows on all eight counts in 2,732 of 2,740 player rows. The other 8 are four 2021 matches whose two boxes Sackmann exchanged between winner and loser; exchanged back, they are equal too. The 8 Oct reviewers could not show this; it was why RG's statistics were not trusted as a replacement.
* **From 2022 they part.** In 2022–2025, Sackmann's first serves in equal RG's in only 29–82% of rows, depending on the draw. Where they differ, the independent records side with RG's (whole split, proposed sides):
  * Court Vision 2022: 226 sides against 1;
  * the hand charts: 125 against 4.
* **What cannot recount:**
  * SofaScore: its points carry no serve number, and its box scores are Sackmann's.
  * The Court Vision copy: approximate at the AO, and its 2023–24 RG files lack many faulted first serves.

**Step 2: three independent reviewers confirmed 1,447 of the 1,718 proposed sides, on 933 Sackmann rows** (observed).
* **The confirmed corrections:** `data/studies/rg_first_serve_recount/confirmed/confirmed_corrections.csv`.
* **What was proposed** (§3). On 1,069 rows, the official first serves in and points won on each serve, wherever Sackmann's split differs:
  * class A, 1,485 sides: only the split differs;
  * class B, 233 sides: an ace, double-fault or break-point count differs too, and is left as it is.
* **How it was checked** (§4). Each reviewer worked alone, from the raw files, with its own lens (rederive, skeptic, referee).
  * They confirmed 1,713, 1,449 and 1,679 sides, every one with the proposed values.
  * Kept: the 1,447 sides all three confirmed.
* **What the confirmed sides are:**
  * 1,426 of the 1,460 sides where Sackmann has more first serves in: the audit's fault.
  * 21 of the 258 where Sackmann has fewer or the same. On a few of these the reviewers found RG's own record wrong, so they kept only those a point record settles.
* **Where an independent record holds a confirmed side, it reads the official split:**
  * Court Vision 2022: 225 of 225 decided sides (5 read neither split);
  * the hand charts: 109 of 109 (13 neither).
* **The radar.** From 2023, RG's point files record the speed of each faulted first serve. On about 566 of 900 "+" sides there are more measured faults than Sackmann has second serves, so Sackmann's split is impossible (two reviewers' counts).
* **Applicability.** The confirmed table applies to the raw rows with the build's own code, together with the decided corrections of 8 Oct. It changes only the named counts, and Stage 0's checks pass.

**What the confirmed fix does to the editions** (observed): first serves in return to near the official level, for example:
* men's qualifying 2022: 68.6% → 63.3% (official 62.5%);
* men's qualifying 2025: 68.6% → 64.0% (official 63.3%);
* the Olympics: men 70.4% → 66.0% (official 64.8%), women 68.3% → 63.7% (official 62.2%).

The rest of the gap is in rows not corrected: their other counts differ too (§5), or the reviewers did not all confirm them.

**The follow-ups (§ 8).** At the owner's word ("Do all of these that you think is a good idea, review it first, then execute if you do"), all three suggestions of § 5 were done, as candidates (observed):
* **RG's whole box score, under the Slam rule of 6 Oct.** All three reviewers of a second round confirmed RG's own box for **1,304 matches**:
  * **953 of Roland Garros 2022–2025.** These include the aces, double faults, serve points and service games that the split fix leaves wrong.
  * **351 of 2026.** That covers all 251 main-draw matches, which have no box score today, and 100 of TML's 112 men's qualifying matches. TML writes no service games in most of them, and its other counts are near RG's but not equal.
  * **237 more matches of 2022–2025 had two votes of three.** The third reviewer held that extending the rule to Sackmann's own history is the owner's call. Those 237 are listed separately.
* **The four exchanged boxes of RG 2021:** confirmed by all three (`exchange_box`, the fix F2 of 8 Oct).
* **The decisions' stale facts:** the 6 Oct decision now notes that RG 2026's feed is held, and the 8 Oct decision's F5 and F6 note that per-match records now exist.
* **The candidate for steps 3–4** now takes RG's box where confirmed, step 2's split elsewhere, and the four exchanges. After it, every edition's pooled first serves in, aces and double faults lie within 0.4 points of RG's own.

**Executed at the owner's word (§ 9;** [decision](../../decisions/2026-10-09-roland-garros-box-scores.md)**):**
* **RG's own record for Roland Garros 2022–2026,** extended to Sackmann's own rows. All three reviewers now confirm **all 1,541 matches**.
* **809 swapped service games corrected.** At the Australian Open 2019–2026 and Roland Garros 2015–2021, Sackmann's rows give the two players each other's service games, mostly as if the winner had served first. The Slams' own point files, fetched back to AO 2018 and RG 2013, prove who served first. All three reviewers confirmed 809 of 810.
  * Service games feed 6 of the model's 58 inputs. *(Corrected 10 Oct: 7, with prod_hold; § 10.3, step 9.)*
* **One candidate,** adopted on a harm check declared beforehand (item 6). Its dry run is clean.

**The three fixes of the evening (§ 10), at the owner's word:**
* **558 more service-game errors set from the score** (blanks, zeros and wrong splits), all confirmed by the three reviewers (§ 10.1).
* **Future Australian Opens and Roland Garros take their box scores from the Slams' own records** (§ 10.2).
* **The harm check: no harm, so the candidate is adopted** (§ 10.3, observed). Both stages, both tours, 2020–2024, + = the candidate better: −0.026 [−0.076, +0.023] mLL per match, unresolved, P(better) 0.145.
  * The rule's harm needs worse than −0.1 with the whole interval below 0. Neither part holds.
  * The comparison resolves ±0.049. A repair's plausible effect is about 0.02, so it serves only as the harm check.
  * The seven inputs the check flags are the fix's own dose: the WTA's first 2013–2014 service-game counts.
* **The swap waits for a coordinated Stage 0 rebuild** (§ 10.4). The lower-level-evidence study is building on today's Stage 0, and its gates would fail on any main-tour change.

## 1. The records

| Record | Editions held | How it is read | Collected |
|---|---|---|---|
| **RG's own statistics**: rolandgarros.com's plain match API, per match and set: aces, double faults, first serve in/served, win on 1st serve won/in, win on 2nd serve won/(served − in), break points won, receiving points, total points won | 2019–2025, main draw and qualifying | First serves in and serve points from "first serve"; points won on each serve from "win on 1st/2nd serve"; break points faced and saved from the opponent's "break points won" | Today: 3,340 requests and 6 probes, no error or refusal; 3,290 matches, 56 codes absent (the 96-player women's qualifying of 2019–2020). `src/ingest/point_sources/rolandgarros.py` |
| **RG's own point-by-point**: Infosys MatchBeats, every point with its server, `serve` 1 (in on the first serve) or 2 (after a first-serve fault), scorer and result | 2019–2024 (new today), 2025–2026 (held since 7 Oct) | Recounted per server: points, points with serve 1, and those won; aces (result A) and double faults (DF) | Today: 2,862 requests and 20 probes, no error or refusal; 2,795 matches. Raw only (§6) |
| **RG's Infosys key statistics** | 2025–2026 (held) | As the 8 Oct reviewers read them | 7 Oct |
| **The Paris 2024 results files** (olympics.com): per player 1ST_SERVE in/attempts with points won, 2ND_SERVE, ACES, DBL_FAULT, BREAK_PTS; a play-by-play whose results name the serve (PS1, PS2, PR1, PR2, A1, A2, DF) | 125 of the 128 singles matches (the site no longer serves them; the Wayback Machine's latest captures, every one "OFFICIAL") | As printed; the play-by-play recounted like MatchBeats | Today: 127 requests, `src/ingest/point_sources/olympics.py` |
| The Hawk-Eye Court Vision copy | RG 2019–24 main draw (part), AO 2020–24 | One row per serve; a faulted first serve is its own row | 29 Sep |
| SofaScore | AO and RG 2022–26 (the gap's matches) | Points with plain/ace/double-fault codes, no serve number | 30 Sep |
| The Match Charting Project | A sample of each draw | Hand-charted totals | Held |

## 2. Step 1: can the first serves be recounted?

### 2.1 Where the truth is known: other events, the same kinds of record

*Observed* (`ao_check.csv`, `ao_rows.csv`, `agree_olp_vs_ol.csv`).

| Record recounted | Against | Rows | Serve points equal | First serves in equal, where the serve points are |
|---|---|---:|---:|---:|
| AO 2025 MatchBeats (the AO's own point files; same provider as RG) | Stage 0's AO rows (Sackmann's; they match the hand charts) | 936 | 60–95% by draw | **731 of 731** |
| The Olympic play-by-play | The Olympic statistics | 248 | 98% | **243 of 243** |
| Court Vision, AO 2020–24 | Stage 0's AO rows | 2,506 | 63–100% | 80–99% |

* **When a point file is complete, a recount from the event's own point record reproduces the box score exactly.** At the AO, points won on each serve agree as well: 730 of 731 rows (first serve), 731 of 731 (second).
* **Where it is not complete,** the box has more serve points than the file (1–14 at the AO): the file misses points. Completeness is checkable, so an incomplete file is never mistaken for a different count.
* **Court Vision is approximate.** It equals Stage 0's AO rows on first serves in in only 80–99% of complete rows, so it serves as a referee, not a record.

### 2.2 RG's own two records agree, every edition

*Observed* (`agree_mb_vs_api.csv`, `rows.parquet`). RG's MatchBeats recount against RG's statistics, on the 6,488 player rows whose point file is complete (the same serve points):
* first serves in and second-serve points won: 100%, in every edition and draw of 2019–2025;
* first-serve points won: 100% but one row (2024).

The other rows (0–4% by draw) are files missing points.

### 2.3 RG's record against Sackmann's

*Observed* (`agree_api_vs_raw.csv`; Sackmann's rows as read, before Stage 0's checks):

| Editions | Player rows | All eight counts equal | First serves in equal |
|---|---:|---:|---:|
| **2019–2021** (before the fault) | 2,740 | **99.7%**: 100% but four 2021 matches whose boxes Sackmann exchanged, equal once exchanged back | **99.7%** (the same four) |
| 2022 | 952 | 29–44% by draw | 35–49% |
| 2023 | 950 | 42–71% | 48–74% |
| 2024 | 952 | 26–79% | 29–82% |
| 2025 | 942 | 26–68% | 34–75% |

* **Before 2022, Sackmann's Roland Garros rows are RG's statistics,** count for count. So RG's record measures what the training data measured. The 8 Oct reviewers rejected RG 2025's statistics for want of exactly this overlap (*inferred*: their "count differently even where nothing is wrong" was the 2022–25 rows' own fault and noise, not a convention).
* **From 2022, Sackmann's rows come from another record.**
  * Mostly the first serves differ: where serve points agree, Sackmann reads higher in 9–62% of rows (most in qualifying), lower in 1–11%.
  * In a few percent of rows the aces, double faults or serve points differ as well (§3, §5).
  * SofaScore's box scores equal Sackmann's at RG 2022–25 (8 Oct review: 95.5–100%), so the two share that record (*inferred*).

### 2.4 RG's own per-edition totals

*Observed* (`proposal_editions.csv`, `editions.csv`). Pooled first serves in by edition:

| Draw | RG's statistics (= Sackmann) 2019 / 2020 / 2021 | Sackmann 2022 / 2023 / 2024 / 2025 | RG's statistics 2022 / 2023 / 2024 / 2025 |
|---|---|---|---|
| Men, main | 63.1 / 63.5 / 62.1 | 66.1 / 62.3 / 63.1 / 62.8 | 63.4 / 61.2 / 62.3 / 62.3 |
| Men, qualifying | 62.3 / 61.3 / 62.7 | 68.6 / 65.3 / 65.2 / 68.6 | 62.5 / 61.5 / 61.2 / 63.3 |
| Women, main | 63.7 / 63.9 / 61.5 | 65.6 / 62.6 / 64.8 / 63.3 | 63.6 / 61.5 / 62.9 / 62.7 |
| Women, qualifying | 64.2 / 65.2 / 65.0 | 70.0 / 68.1 / 67.6 / 68.6 | 65.1 / 64.7 / 63.6 / 63.6 |

RG's own totals are level across the editions. The fault's edition-level signature (2022's high main draw, qualifying five points high) is Sackmann's alone.

### 2.5 What cannot referee the split

* **SofaScore:** its point records code plain points, aces and double faults only, with no serve number. Its box scores are Sackmann's at RG.
* **The Court Vision copy, RG 2023–24:** its rows for faulted first serves cover only 74% (2023) and about 47% (2024) of its second-serve points, against one each in 2019–22. It equals RG's first serves in on only 21–66% of rows where RG and Sackmann agree (reviewer R3). It is a referee for 2019, 2020 and 2022 only.
  * An earlier version of this report said the copy's share of points played on a second serve fell to 27% and 16%. Those were the shares of points that carry a fault row (R3's correction).
* **The Match Charting Project:** hand-charted, so noisy. Even in 2019–21 it equals Sackmann's first serves in in only 42–83% of rows. It is useful as a side-taker on disputed rows, not as a record.

## 3. Step 2: the proposed corrections

*Observed* (`propose.py`; `proposed_rows.csv`, `proposed_corrections.csv`, `proposal_summary.json`).

**Scope.** Sackmann's player rows of RG 2022–2025 (both tours, main draw and qualifying; 3,824 rows) and the Paris Olympics 2024 (256 rows).

**The official record:**
* RG's statistics for RG rows, the Olympic results for Olympic rows.
* Each must pass its own consistency checks for both players: denominators, receiving points against the opponent's serve points, totals.

**Its second record may veto.** Where RG's MatchBeats (or RG's key statistics, 2025) or the Olympic play-by-play holds every point of a row, it must give the same split:
* 1,696 sides agree;
* 22 have no complete second record;
* 1 contradicts and is dropped.

**Classes of a player row** (Sackmann's against the official record):

| Class | Definition | RG rows | Olympic rows | Proposed |
|---|---|---:|---:|---|
| equal | Every count equal | 1,822 | 97 | — |
| **A, split** | Only first serves in and points won on each serve differ | 1,432 | 54 | **Yes** (1,485 sides) |
| **B, split + other** | The split differs; serve points and serve points won agree; an ace, double-fault or break-point count differs too | 190 | 43 | **Yes**, the split only (233 sides) |
| points | Serve points or serve points won differ | 254 | 41 | No (§5) |
| other | The split agrees; something else differs | 106 | 9 | No |
| no record | No official record, or one failing its checks | 20 | 12 | No |

* **The mechanism.** Of the proposed sides, Sackmann has more first serves in on 1,460 (median +3, up to +53). He has fewer on 194, by 1 (163), 2 (29) or 3 (2). On 64 the number is the same, with points won moved between the serves.
  * Pooled, the extra first serves were won 49.4% of the time, a second-serve rate.
  * Reviewer R2 showed this is not diagnostic row by row: the error depends on the point's outcome. In RG 2024's main draw, 54% of "+" sides moved only lost points.
  * The row-level evidence is the radar (§4) and the referees.
* **The operation, `replace_split`.**
  * It is a new action of `src/eda/input_data_audit/corrections.py`, with tests; no decided table uses it.
  * It gives each named side the official first serves in and points won on each serve.
  * It applies only if the source row still reads the table's serve points, aces and double faults, and its serve points won do not change. Otherwise the build stops.
* **The dry run.** The table, applied to the raw rows with the build's own code:
  * changes 1,069 rows;
  * every one of the 1,718 sides reads the official split afterwards;
  * no other count changes;
  * Stage 0's split checks (B1–B3, B6, B7) pass on every row.
* **The independent referees on the proposed sides,** where they hold every point (the whole split):
  * Court Vision: 2022, 226 sides official, 1 Sackmann's; 2023–24, 35 against 10 (its own defect, §2.5);
  * the hand charts: 125 official, 4 Sackmann's.
  * Every side a hand chart or Court Vision 2022 puts with Sackmann was dropped by the reviewers (§4).
* **Examples:**
  * Nakashima, 2022 R32 on Suzanne-Lenglen: Sackmann 110 first serves in of 128; RG's statistics, its MatchBeats and Court Vision 78.
  * Fritz, 2023 R32: Sackmann 94; RG, MatchBeats, Court Vision and the hand chart 70.
  * Ofner, Olympics R32: Sackmann 57 of 58; the official results and the hand chart 31.

## 4. The reviewers' check

*Observed* (`review/brief.md`, `review/<reviewer>/verdict.json` and `scope.csv`, `confirmed/consensus.json`).

**How.** As on 8 Oct:
* three independent reviewers (Opus 5.5 subagents), each with its own lens;
* each worked alone from the raw files, on the same brief;
* a correction stands only where all three confirm the same side with the same values (`consensus.py`).

| Reviewer | Lens | Recount validates | RGFSA (1,340) | RGFSB (282) | OGFSA (39) | OGFSB (57) | Sides |
|---|---|---|---|---|---|---|---:|
| R1 | Rederive every count with its own code | Yes | narrow: 1,337 | confirm: 282 | narrow: 37 | confirm: 57 | 1,713 |
| R2 | Attack every claim | Yes | narrow: 1,114 | narrow: 261 | narrow: 21 | narrow: 53 | 1,449 |
| R3 | Independent records; simulate the fix | Yes | narrow: 1,316 | narrow: 280 | narrow: 27 | narrow: 56 | 1,679 |
| **All three** | | | **1,112** | **261** | **21** | **53** | **1,447 (933 rows)** |

The fix ids' sides count both sides of a row labelled B as B. No reviewer derived a different value on any side it confirmed. R1 also listed one match the proposal lacks (§5); the consensus counts proposed sides only.

**What each narrowed, and why:**
* **R1** kept a "−" or "0" side only where the venue's own point record shows Sackmann's split impossible. It left out 5 sides:
  * three 2025 sides with no point record against Sackmann;
  * Fernandez and Gauff at the Olympics: the play-by-play is partial, or contradicts the statistics on the other serve.
* **R2** kept a "−" or "0" side only where Court Vision 2022 reads RG's exact values (22 of 236), because there RG's own record is sometimes the wrong one. It also dropped:
  * 30 sides whose RG point file is incomplete or missing (key statistics alone are not a point record);
  * 12 where the hand chart reads Sackmann's value and nothing physical settles it.
* **R3** dropped:
  * "both-minus" matches, where both players read fewer first serves in from Sackmann: the referees split there, 4 for RG and 3 for Sackmann;
  * all 13 Olympic "−" sides: no clean Olympic edition exists to check the record against;
  * Pigossi's side of Pigossi–Kawa: the only box the fix would bring back, with Kawa's side still corrupt.

**What was dropped** (271 sides):
* 173 of the 188 class-A "−" sides and 55 of its 61 "0" sides;
* all 9 of class B's "−" and "0" sides;
* 34 "+" sides: incomplete or missing second records, a hand chart reading Sackmann's value, Pigossi.

Every proposed side that a hand chart or Court Vision 2022 puts with Sackmann is among them.

**What the reviewers added to the evidence:**
* **The radar.** From 2023, RG's point files carry each faulted first serve's speed (`faultSrvSpd`).
  * On 566 (R2) to 568 (R1) of about 900 "+" sides of 2023–25, there are more measured faults than Sackmann has second serves. That makes his split impossible.
  * The radar never contradicts the official split.
* **The values and links,** re-derived from the raw files by all three. Every proposed value equals RG's raw documents and the Olympic files. R2 checked 121 inexact name pairs by hand.
* **The simulation** (R3):
  * the proposal changes only its 4,188 split cells;
  * it combines with the decided table without overlap;
  * checks B0–B8 pass afterwards;
  * R3's own reproduction of Stage 0's box checks equals Stage 0's status on all 3,418 RG and Olympic rows of 2019–25.
* **Class B.** Where an independent record holds them, the aces and double faults class B leaves in place are Sackmann's errors too: 28 of 28 equal the official value (R3). Correcting them would be a separate operation, and a separate decision.
* **SofaScore** equals Sackmann on all four split counts in 99.5% of 1,508 linked RG 2022–25 rows, including every proposed one (R3). It shares his record.
* **A bug in the lead's referee link** (R3). Quarter-finals were read as qualifying, so the hand charts of 64 quarter-final rows went unlinked.
  * Fixed and rerun.
  * The proposal does not use the charts, and it is byte-identical after the rerun (SHA-256 `7e976039…`). The tallies above are from the rerun.

## 5. Found along the way (not proposed)

* **Rows with more wrong than the split** (classes "points" and B). 295 rows differ in serve points or serve points won.
  * Some are partial boxes: Sackmann has 19 serve points where RG has 91 (Kovalik, 2022 Q1).
  * Stage 0 already drops 18 of the 20 rows that are 13 or more serve points short (its check B9).
  * The rest, mostly within a few serve points, reach the model.
  * Class B rows keep a differing ace or double-fault count. Sackmann's is mostly lower, most often by one (double faults: 161 of 178 differing sides lower).
  * *Inferred:* the record behind Sackmann's 2022–25 rows misses some faults and aces altogether.
* **RG's record could replace the whole box.** RG's statistics equal Sackmann's on every count before 2022 (§2.3). By the 6 Oct rule for Wimbledon and the US Open ("a Slam whose official feed is held and has matched Sackmann's history"), RG's feed could be the box-score source for 2022–26. That would also fix the rows above. It is a decision beyond this item, and the owner's call. **Taken up the same day at the owner's word: § 8.**
  * Service games are not in RG's statistics. The 8 Oct reviewers' derivation from "Break Points Converted Games" matched only 68–84%. MatchBeats counts them.
* **RG 2026.** The Slam decision of 6 Oct says "no official feed is held" for RG 2026. RG's key statistics and MatchBeats for 2026 have been held since 7 Oct. **The decision now notes it (§ 8.1).**
* **The Olympic rows are worse than RG's.** 41 of 256 differ in serve points or serve points won, and 43 more in aces or double faults. Sackmann has Zhang Zhizhen at 81 first serves in of 84 with 1 ace; the official record says 62 and 10.
* **Four exchanged boxes at RG 2021** (women's main draw: Muchova–Petkovic, Peterson–Rogers, Siniakova–Zidansek, Bogdan–Badosa).
  * The winner carries the loser's whole box, the input-data audit's fault #3. RG's statistics confirm each exchange count for count.
  * They are the only differences in 2019–2021, and none of 2022–2025 fits the exchange.
  * A candidate for the exchanged-box fix (F2 of 8 Oct), which needs its own review. **Reviewed and confirmed by all three: § 8.**
* **Identity slips in Sackmann's rows** (not linked or not proposed here):
  * RG 2024 Q1 Kolar d. Faurel (RG's code QM126): Sackmann names the loser "T. Farquhar" (`atp:212408`). R1 shows it is Thomas Faurel, and that the row has the same fault.
  * RG 2023: "Eduardo Nava" (`atp:124013`, four rows) is Emilio Nava per RG (R1).
* **The Olympic Struff–Moutet walkover is reversed in Sackmann's row:** the Olympic file and Sackmann's own next round have Moutet through (R1).
* **The most extreme rows stay dropped.** Every serve point is booked as a first serve in: Barrios Vera–Kovalik 25/25 and 19/19, Uchijima–Yuan 28/28 and 23/23. Stage 0 drops them (B3/B6), and their serve points differ too, so a split fix cannot apply (R3).
* **RG's statistics are not infallible.**
  * On 8 sides of 2024 qualifying they lack one serve point, apparently the match's last, that MatchBeats and Sackmann both hold (R1). None is proposed.
  * On some "−" and "0" sides, an independent record puts RG's own split in the wrong (R2, R3). Those sides were dropped.
* **The second record's 2025 key statistics.** The lead counted RG's 2025 key statistics as a second record where MatchBeats was incomplete (8 sides). R2 counted only point records, and those sides were dropped.
* **The data map does not list the two new sources yet.** It is a shared file that other sessions are editing.

## 6. Files and reruns

| What | Where |
|---|---|
| Adapters | `src/ingest/point_sources/rolandgarros.py` (new; 2026 added on 9 Oct, every held year staged by every run, `--summary-dir`), `olympics.py` (new), `infosys_slams.py` (editions RG 2013–2024 and AO 2013–2024 and 2026 added, raw only: the serve-speed panel reads its staged points, so they are never staged there; `--routes`) |
| Raw (gitignored) | `data/raw/point_sources/rolandgarros/`, `olympics/`, `infosys_slams/RG/2019`–`2024/`, each with `_receipts.jsonl` |
| Staged (gitignored) | `data/dump/points/rolandgarros/` (2019–2026), `data/dump/points/olympics/` |
| Study code | `src/eda/rg_first_serve_recount/`: `sources.py` (loaders and recounts), `link.py`, `recount.py` (step 1), `propose.py` (step 2), `consensus.py`; the follow-ups (§§ 8–10) `whole_box.py`, `followup_delta.py`, `consensus_followup.py`, `service_game_swaps.py`, `service_games.py`, `candidate_trim.py`, `input_dose.py`, `reading_split.py`, `verify_applied.py` and `adopt.py`; the future editions' builder `src/eda/data_continuity/slam_infosys_overrides.py`; the reviewers' scripts in `review/<reviewer>/` and `review_followup/<reviewer>/` |
| The operations | `src/eda/input_data_audit/corrections.py` (`replace_split`); `src/eda/predictability_diagnostic/stage0_build.py` (rule E7, where an action no row uses is no longer logged, so the decided build's log is unchanged; and, for § 8, an override row may name a Sackmann row through a `source` column, which the decided table lacks, so it applies as before) |
| Tests | `test/rg_first_serve_recount/` (25: the recount, the links, the classes, service games and the proof of who served first, the override's `source` column, `whole_box.py`'s checks and service-game sources), `test/input_data_audit/test_corrections.py` (8 new) |
| Evidence | `data/studies/rg_first_serve_recount/`: `rows.parquet`, `agree_*.csv`, `editions.csv`, `ao_*.csv`, `disputed_referees.csv`, `proposed_*.csv`, `proposal_*`, `control_2019_2021.csv`; the collection's summaries and logs in `collection/`; the reviewers' brief and verdicts in `review/`; the confirmed corrections in `confirmed/`; the follow-ups in `followup/` ([its file list](../../../data/studies/rg_first_serve_recount/README.md)) |

```
./python.sh -m src.ingest.point_sources.rolandgarros --years 2019-2026        # RG's statistics (cached; --stage-only)
./python.sh -m src.ingest.point_sources.infosys_slams --editions RG2019,RG2020,RG2021,RG2022,RG2023,RG2024 \
    --no-stage --summary-dir data/studies/rg_first_serve_recount/collection     # RG's MatchBeats, raw
./python.sh -m src.ingest.point_sources.olympics                              # the Olympic results files
./python.sh src/eda/rg_first_serve_recount/recount.py                         # step 1, about a minute
./python.sh src/eda/rg_first_serve_recount/propose.py                         # step 2's proposals and dry run
./python.sh src/eda/rg_first_serve_recount/consensus.py                       # after the three reviews
./python.sh src/eda/rg_first_serve_recount/whole_box.py                       # § 8's proposal and dry run, minutes
./python.sh src/eda/rg_first_serve_recount/followup_delta.py                  # what the amendments changed against v1
./python.sh -m src.ingest.point_sources.infosys_slams --editions AO2018,AO2019,AO2020,AO2021,AO2022,AO2023,AO2024,AO2026 \
    --routes match-beats --no-stage --summary-dir <folder>                     # older AO point files, raw (RG: match-beats-api)
./python.sh src/eda/rg_first_serve_recount/service_games.py                    # § 9's swap proposal (all editions held)
./python.sh src/eda/rg_first_serve_recount/consensus_followup.py              # after the reviews, minutes
./python.sh -m pytest test/rg_first_serve_recount test/input_data_audit -q
```

## 7. For steps 3–4 (a later session)

Not run here, as asked. The checklist's step 3 makes the changed past matches a candidate under the frozen-reference rule.

* **The input: the candidate the owner decided** (§ 9.3; [decision](../../decisions/2026-10-09-roland-garros-box-scores.md)), `data/studies/rg_first_serve_recount/followup/confirmed/candidate/`. It contains:
  * RG's whole box for all 1,541 matches;
  * step 2's split rows for the matches that take no override (12 at RG, 46 at the Olympics);
  * the four RG 2021 exchanges;
  * the 809 swapped service games of AO 2019–2026 and RG 2015–2021.

  It needs two arguments, `--box-overrides` and `--corrections-dir`. The decided tables' SHA-256 values are in `followup/confirmed/consensus.json`. If those tables have changed by then, rebuild the candidate with `whole_box.py`, `service_games.py` and `consensus_followup.py`.
  * **The adoption rule,** declared before any reading (item 6): adopt unless `compare.py` (both stages, both tours, seasons ≤ 2024) reads the candidate worse by more than 0.1 mLL with the whole interval below 0, or an input is flagged "uneven".
  * **The earlier split-only folder** (`confirmed/candidate_corrections/`) is superseded.
* **The build, in outline** (`src/eda/model_rebuild/run_chain.py`'s candidate path; its lane 0 is "not yet exercised", so read its docstring first):
  1. Check that the sandbox (`C:/Users/zerom/tnr_sb`) does not exist and no other job uses it or the GPU. The build queue runs one candidate at a time.
  2. `./python.sh src/eda/model_rebuild/run_chain.py --setup --candidate --out data/studies/current_best_model/<date>_rg_first_serves`. The sandbox copies `src/` and `data/studies/`, so the candidate's files, and Stage 0's support for an override naming a Sackmann row, are there.
  3. In the sandbox, rebuild its Stage 0 with the candidate. Run this from the sandbox's root so that it writes the sandbox's copy:
     `stage0_build.py --box-overrides data/studies/rg_first_serve_recount/followup/confirmed/candidate/slam_box_overrides.csv --corrections-dir data/studies/rg_first_serve_recount/followup/confirmed/candidate/corrections --confirm-live-overrides`
  4. Then `--lane 0` (Stage 1's odds link, the timeline, the leak-proof inputs), lanes 1–3 and `--collect`.
  5. Fit seeds 0–3 and compare with `src/eda/current_best_model/compare.py` on seasons ≤ 2024. The outcome reading is only a harm check (adoption framework § 2: a data fix is decided on data evidence).
* **What to expect in the input check** (*inferred*).
  * **Only box-score inputs move,** for players with a Roland Garros or Olympic match of 2022–2026 in their memory: two-week form, the IOS ratings and products, and the points aggregates.
  * **2022–2025:** first-serve and second-serve rates move most; aces, double faults and service-game rates move a little.
  * **2026:** 251 main-draw matches gain a box, and 100 qualifying matches gain their service games.
  * **AO 2019–2026 and RG 2015–2021:** the hold-rate and break-points-per-service-game inputs move a little for players with those matches in memory (809 swapped service-game pairs).
  * **The harm check sees only part of it.** A reading on seasons ≤ 2024 shows the 2022–2024 changes. The 2025–2026 changes reach only the untouched seasons, so for them the data evidence alone decides (adoption framework § 2).

## 8. The follow-ups of 9 Oct

**The request** (owner, 9 Oct 2026, on the three suggestions that ended steps 1–2): "Do all of these that you think is a good idea, review it first, then execute if you do."

As in steps 1–2, nothing here changes Stage 0 or the model:
* every confirmed change is a candidate under the frozen-reference rule;
* `run_chain.py` and the GPU were not used, and no git command was run.

### 8.1 The three suggestions, reviewed

| Suggestion | Verdict | Why | Outcome |
|---|---|---|---|
| **RG's record as the whole box score of Roland Garros 2022–2026,** under the 6 Oct Slam rule | Worth doing, as a candidate, after three reviewers | See below | 1,304 of 1,541 proposed matches confirmed by all three (§ 8.4) |
| **The four exchanged boxes of RG 2021** | Worth doing | RG's own statistics read Sackmann's two boxes exchanged, count for count; the operation is F2 of 8 Oct (`exchange_box`) | 4 of 4 confirmed |
| **The 6 Oct decision's "no official feed is held" for RG 2026** | Worth doing | A stale fact in a decision record misleads later sessions | Dated notes, marked as facts with nothing decided again, in the 6 Oct decision (RG 2026 and its two RG 2022–2025 items) and the 8 Oct decision (F5 and F6) |

**Why the whole box was worth doing.** The 6 Oct rule reads: "at a Slam whose official feed is held and has matched Sackmann's history, the feed is the box-score source".
* **RG meets both conditions.** Its feed is held, and its statistics equal Sackmann's 2019–2021 rows on all eight counts they share, apart from four exchanged boxes.
* **The independent records side with RG on every count that changes** (§ 8.3).
* **It fixes what step 2's split leaves:**
  * aces and double faults that Sackmann's rows undercount;
  * serve points, break points, and service games the score disproves.
* **It fills RG 2026,** whose 251 main-draw matches have no box at all.

**Where the proposal departs from the rule as written, and why:**
* **The rule was applied only to rows after Sackmann's data ends** (Wimbledon and the US Open 2026). Here it also reaches Sackmann's own 2022–2025 rows, the training history. So the proposal went through the 8 Oct three-reviewer rule as well, and only unanimous matches are kept.
* **RG's statistics give no service games.** They come from the first of these that fits the score:
  * RG's MatchBeats, counting completed games with tiebreaks left out (Sackmann's convention);
  * the score's alternation of serve, from the player MatchBeats has serving first;
  * the row's own count.
* **Matches left out:**
  * where RG's statistics miss points that MatchBeats holds (13);
  * where MatchBeats contradicts RG's statistics (1);
  * where an independent record reads the row's value (13);
  * walkovers (12);
  * Kolar d. Faurel (Sackmann's "T. Farquhar").
* **Not included:**
  * **the Olympics:** not a Slam, and no clean edition exists to check its record against;
  * **RG 2026 women's qualifying:** not in Stage 0, a coverage question.

### 8.2 Roland Garros 2026

* **Collected today:** RG's own 2026 statistics. 478 requests, every match answered, with no error, retry or refusal (`followup/collection/`). RG's Infosys key statistics and MatchBeats have been held since 7 Oct.
  * The adapter now stages every held year on every run. Before, a run for one year replaced the staged tables with that year alone.
* **Stage 0 today** (observed):
  * **Main draws:** 127 men's and 127 women's matches, from Sackmann's rows, every one without a box score. The 6 Oct decision names only the men's.
  * **Men's qualifying, from TML:**
    * 0 service games in 194 of 224 player rows, so Stage 0 keeps service games for 26;
    * 15 matches without a box;
    * its other counts are near RG's but not equal: serve points in 69% of rows, first serves in 60%;
    * its pooled first serves in are level with RG's (63.2% against 63.1%), so this is not the first-serve fault.
  * **Women's qualifying:** no rows.
* **TML's 2026 main-draw rows have the men's first-serve fault** (64.7% first serves in against RG's 62.2%; R1, R3). Stage 0 does not use them, and they must not replace Sackmann's blank rows.

### 8.3 The proposal

`src/eda/rg_first_serve_recount/whole_box.py`; tables in `data/studies/rg_first_serve_recount/followup/`.

* **The operation.** One override row per match, in stage0_build's `--box-overrides` table: both players' nine counts from RG's record. The row is named by its source, tour, tournament, round and the two names.
  * `apply_box_overrides` now accepts a `source` column, so an override can name a Sackmann row.
  * The decided table has no such column and applies as before (tests in `test/rg_first_serve_recount/test_overrides.py`).
* **The 2,278 matches of 2022–2026:**

  | Class | Matches |
  |---|---:|
  | Proposed | 1,541 (2022: 356, 2023: 272, 2024: 273, 2025: 289, 2026: 351) |
  | Already equal | 697 |
  | RG's statistics miss points | 13 |
  | Referee contradicts | 13 |
  | Walkovers | 12 |
  | MatchBeats contradicts | 1 |
  | No link | 1 |

* **What changes in the 1,541,** in player rows:
  * the split: first serves in 1,833; points won on the first serve 1,390, on the second 1,378;
  * serve points 357;
  * double faults 207; aces 83;
  * break points saved 94, faced 48;
  * service games 255;
  * 504 rows with no box get one: the 2026 main draws, and Karatsev–Moreno de Alboran 2023.
* **The independent records on the counts that change.** Proposed rows only, where the record holds every point; "held" includes rows where the record reads neither value:

  | Count | Rows changing | Court Vision 2022: RG / the row / held | Hand charts: RG / the row / held |
  |---|---:|---|---|
  | serve points | 357 | 15 / 0 / 15 | 39 / 0 / 39 |
  | aces | 83 | 10 / 0 / 10 | 2 / 0 / 2 |
  | double faults | 207 | 21 / 0 / 21 | 5 / 0 / 5 |
  | first serves in | 1,833 | 232 / 0 / 236 | 130 / 0 / 140 |

  * The zeros are partly by construction: the 13 matches where a record read the row's value are left out.
  * Counting those back in, R3 finds the split 368 to 5 for RG (149 to 4 where first serves in differ by at most one).
  * Where aces and double faults change, the row is lower than RG's in 81 of 83 and 182 of 207: a record that misses some (*inferred*).
* **Amended after the review** (§ 8.4), with the reviewed version kept as the `*_v1` files and the difference in `review/addendum_matches.csv`:
  * **Retirements:** the unfinished game no longer counts as a service game. Sackmann never counts it (R2: 68 of 68 retired rows of 2022–2025). This changed 11 matches.
  * **Service games from the score's alternation,** where MatchBeats misses points. This filled Maestrelli–Noguchi 2026 with 14 and 15.
  * **32 more matches** whose eight counts were already RG's but whose service games were:
    * missing: TML's zeros in 19 matches of 2026 qualifying, Sackmann's blanks in 3 of 2023;
    * impossible for the score: 10 matches of 2023–2024. Muchova–Podoroska has 13 and 11 in 24 games without a tiebreak, which no order of serve allows.

### 8.4 The reviewers' check (round 2)

Three independent Opus 5.5 reviewers, the same three lenses as round 1, the brief in `followup/review/brief.md`. Then an addendum round on the 44 amended or added matches. A match is kept only where all three name it with the same eighteen values (`consensus_followup.py`).

| Reviewer | Lens | RGX | W22 (2022–2025) | W26 (2026) | Matches named, all with the amended values |
|---|---|---|---|---|---:|
| R1 | rederive | confirm, 4 | source rule: all 1,190 | source rule: all 351 | 1,541 |
| R2 | skeptic | confirm, 4 | **8 Oct bar: 953** | source rule: all 351 | 1,304 |
| R3 | referee | confirm, 4 | source rule: all 1,190 | source rule: all 351 | 1,541 |
| **All three** | | **4** | **953** | **351** | **1,304** |

**Why R2 held 2022–2025 to the 8 Oct bar.** RG qualifies under the rule; R2 confirmed that 2,732 of 2,740 rows are equal. But the 6 Oct decision applied the rule only to 2026's rows, and left Sackmann's RG 2022–2025 to a study under the 8 Oct rule. So, in R2's judgment, extending the rule to Sackmann's history is the owner's call.

Under the 8 Oct bar R2 left out 237 matches (reasons overlap):
* **199:** a side where Sackmann has fewer first serves in than RG, or the same with points won moved, and no Court Vision 2022 reading. There, Court Vision shows RG's own record wrong about once in 23.
* **18:** an ace or double fault higher in Sackmann's row, against that record's usual undercount, with no referee.
* **20:** RG's point record incomplete or incoherent.
* **4:** serve points that cannot be settled.
* **4 blank rows:** a blank is missing, not corrupt.

**The 237 are listed with each reviewer's word** in `followup/confirmed/not_unanimous_overrides.csv`. All 237 were confirmed by R1 and R3 with the same values. If the owner extends the 6 Oct rule to Sackmann's history, they can join the candidate. Otherwise they keep their rows, and 100 of them keep step 2's confirmed split.

**What the review changed:**
* the retirements (R1, R2);
* the service-game gaps (R2, R3);
* Maestrelli–Noguchi (R1);
* a latent bug, now fixed: `apply_box_overrides` failed on a table without `score` or `minutes` columns (R1).

**The four exchanges** are confirmed by all three:
* RG's statistics and its point record read the boxes exchanged.
* Two hand charts and one Court Vision file read them exchanged too.
* The score, RG's winner and the next round all name the recorded winner, so the names are right and the boxes are what's swapped.
* Service games are level in each match, so exchanging all nine counts is exact.

### 8.5 The candidate for steps 3–4

`data/studies/rg_first_serve_recount/followup/confirmed/candidate/`:
* `slam_box_overrides.csv`: the decided table of 6 Oct (731 rows) with the 1,304 confirmed RG rows;
* `corrections/row_corrections.csv`: the decided table of 8 Oct (1,522 rows), with these appended:
  * step 2's confirmed split rows for the matches without an override (112 at RG, 46 at the Olympics);
  * the 4 exchanges.

  Step 2's other 775 split rows are covered by overrides that give the same split.
* `corrections/id_aliases.csv`: the decided table.

**The dry run** (`consensus.json`): both tables applied to the raw rows with the build's own code.
* All 1,304 RG rows and 731 decided rows read their tables afterwards.
* No row is both overridden and corrected.
* The exchanges read exchanged.
* 3,160 rows change, 0 outside the tables.
* 251 matches without a box get one.
* Reviewers' simulations of the full proposal (R3): full boxes rise and no row loses one. R2's simulation of exactly this scope reads its values on all 1,304 rows.

**What it does to the editions** (`followup/confirmed/editions_after.csv`, observed). After the candidate, pooled first serves in, aces and double faults lie within 0.4 points of RG's own in every edition and draw. For example:

| Draw | First serves in: the rows as read → after the candidate (RG's own) |
|---|---|
| Men's qualifying 2022 | 68.6% → 62.5% (62.5%) |
| Men's qualifying 2025 | 68.6% → 63.7% (63.3%) |
| Men's main draw 2022 | 66.1% → 63.3% (63.4%) |
| Women's qualifying 2022 | 70.0% → 65.0% (65.1%) |
| 2026 main draws | no box → 62.2% (men) and 63.0% (women), 248 and 254 player rows |

### 8.6 Found by the reviewers, not acted on

* **Sackmann's 2019–2021 RG service games are swapped between the players in 241 of 1,343 matches** (R2), mostly as if the winner had served first. This is an uncorrected fault in the training history that Stage 0's B5 cannot see. It is outside this proposal.
  * **Checked by the lead the same day** (`service_game_swaps.py`, `followup/service_game_swaps.csv`). The truth is the score's alternation of serve from the first server in the Slam's own point record.
    * At RG 2019–2021, exactly 241 completed matches are swapped, 197 of them as the score gives if the winner served first. In 2022–2025 there is 1.
    * **The same fault is in Sackmann's Australian Open 2025 rows:** 77 of 455 completed matches are swapped, 70 of them as if the winner served first.
    * Both are Slams whose own statistics give no service games (*inferred*: Sackmann's source filled them in). Wimbledon and the US Open matched Sackmann on every count (6 Oct decision).
  * **Service games feed 6 of the model's 58 inputs:** the hold rates (`form_hold`, `iosO_hold`, `iosD_hold`, `prod_hold`) and break points faced per service game (`form_bp_faced_pg`, `formdef_bp_faced_pg`).
* **Sackmann's 2022–2025 rows over-count serve points in 167 rows** (127 matches; R2), not only under-count. The confirmed overrides fix the ones they cover.
* **RG's 2026 service games leave tiebreaks out, while the decided Wimbledon and US Open 2026 rows count them** (R2). B5 accepts both.
* **Baez d. Heide, 2024 R128, could come in on its service games** (R1, R3). The contradiction that kept it out rests on one MatchBeats point with no scorer. Not proposed, so not reviewed.
* **Monfils, 2025 R128:** RG's statistics seem more complete than its point record (R2). Not proposed.
* **The Court Vision copy:**
  * its 2023–2024 RG files can referee serve points, aces, service games and break points, but not double faults or the split (R3);
  * many faulted-serve rows carry no player id, so a recount must take the server from the point's other row (R1).
* **TML is not an independent referee at RG** (R3): in 2022–2025 its main-draw rows copy Sackmann's values, and its qualifying rows copy RG's.
* **Identity:** RG 2024 QM126 "T. Farquhar" is Thomas Faurel and needs an identity fix before any box (R1, R2).

### 8.7 Recommendations to the owner (9 Oct 2026; proposals awaiting a yes)

1. **Extend RG's own record as the box-score source to Sackmann's Roland Garros 2022–2025 rows, so that the 237 matches join the candidate. Recommended.**
   * **The evidence favours RG on exactly these rows.**
     * Where an independent record holds every point of a changing first-serve count, it reads RG's value: Court Vision 3–0, hand charts 15–0.
     * On the whole class of small disputed differences, RG is right about 94% of the time (R3: 33–2 and 12–0; R2: Court Vision finds RG wrong about once in 23).
   * **They are not all noise.** 44 of their player rows are off by three first serves or more, and stay wrong if left out.
   * **The dissent was mostly about authority.** R2 checked the values of all 1,509 matches, and said the blanks "would pass the source rule if the owner extends it". It later added that its narrowing was also about changes no record could settle, under the stricter 8 Oct bar.
   * **The cost if wrong:** about one first serve on a few percent of some 300 player rows.
   * **The scope:** Roland Garros 2022–2025 only, not a rule for other events.
2. **Adopt the candidate after the harm check, under a rule declared now. Recommended.**
   * **The rule:** adopt unless the candidate is worse by more than 0.1 mLL with the whole 95% interval below 0 (both stages, both tours, seasons ≤ 2024; the harm rule of item 5). Also, no input may be flagged "uneven".
   * **The 2025–2026 part** goes in with it, on the data evidence: the same rule and source, and mostly boxes that are missing today. Testing it on 2025–2026 would spend the clean holdout on a data fix.
3. **Fix the swapped service games of the Infosys Slams. Recommended.**
   * **Scope:** every Australian Open and Roland Garros match where the Slam's own point record proves the first server.
     * Held now: RG 2019–2021 (241 matches) and AO 2025 (77).
     * Obtainable: AO 2020–2024 from the Court Vision copy held, and earlier point files under the scraping approval where they exist.
   * **The operation:** `exchange_svgms`, decided on 8 Oct (F2y), with three reviewers as usual.
   * **Fold it into the same candidate,** so one harm check covers everything.

**The owner's answer:** "Execute and fix" (§ 9).

## 9. Executed at the owner's word (9 Oct 2026)

**The decision:** [Roland Garros box scores from RG's own record, and the Infosys Slams' swapped service games corrected](../../decisions/2026-10-09-roland-garros-box-scores.md). It has three points:
1. RG's own record is the box-score source for Roland Garros 2022–2026, extending the 6 Oct rule to Sackmann's own rows.
2. Everything enters as one candidate, adopted on a harm check declared beforehand.
3. The swapped service games of the Australian Open and Roland Garros are exchanged back wherever the Slam's own point record proves who served first.

Nothing here changed Stage 0 or the model. The decided tables are byte-identical (hashes in `followup/confirmed/consensus.json`); `run_chain.py` and the GPU were not used.

### 9.1 RG's own box for Roland Garros 2022–2026: all 1,541 matches

Under the extended rule, the dissenting reviewer R2 re-ruled on the 237 matches it had left out, and confirmed all 237 with the same values.
* **No record contradicts RG on them.** Where Court Vision or a hand chart holds every point, it reads RG's value: 44 readings in 17 matches, none for the row.
* **R2's open cases came out for RG:**
  * **Monfils, 2025 R128:** RG's statistics hold the match point that RG's own point file cuts off (148 serve points against 147).
  * **Etcheverry–Rinderknech, 2024:** Court Vision holds RG's serve points, not Sackmann's.
  * **The 4 blank fills** take RG's record, with service games derived from the score.
* **R2's grounds, corrected in the record:** its earlier narrowing was also about changes no record could settle under the stricter 8 Oct bar, not only about authority.

**So all three reviewers confirm all 1,541 matches, with the same eighteen values.**

### 9.2 The swapped service games: 809 matches

**The point files.** Fetched today under the scraping approval, raw only (`followup/collection/`), with the old editions probed first (each final). Point files are served from AO 2018 and RG 2013; AO 2013–2017 have none.

| Fetch | Requests | Outcome |
|---|---:|---|
| AO 2018–2024 and 2026, static route | 2,976 | No error or refusal. Qualifying files do not exist for 2018, 2019, 2020 or 2022 |
| RG 2013–2018, API route | 2,907 | 17 HTTP 500 answers. On retry, RG 2015's came through. RG 2016's 16 failed again on both routes, so those matches have no file |

**The method** (`service_games.py`; `sources._mb_counts`):
* **Who served first:** the file's first point opens set 1, and every game the file holds follows the alternation of serve from that player.
* **The truth:** the score's alternation from that player, with tiebreaks uncounted and a retirement's unfinished game left out.
* **A swap:** the row's two counts are the truth's, exchanged.
* **Not proposed:**
  * any other mismatch;
  * a row the decided corrections already change (AO 2022 Paire–Monteiro, whose service-game swap the 8 Oct reviewers confirmed independently, and which the method finds unprompted);
  * an RG match with an override (RG 2023 Diaz Acosta–Agamenone).

**Where the fault is** (completed and retired matches with a proven first server):

| Slam | Swapped matches, by edition | Clean |
|---|---|---|
| Australian Open | 2019: 36 · 2020: 32 · 2021: 48 · 2022: 47 · 2023: 83 · 2024: 70 · 2025: 81 · 2026: 66 | 2018 (0) |
| Roland Garros | 2015: 1 · 2016: 43 · 2017: 10 · 2018: 52 · 2019: 71 · 2020: 79 · 2021: 92 | 2013–2014, and 2022–2025, whose rows came from another record (1 swap, left to its override) |

* **The pattern:** 678 of the 809 confirmed swaps are exactly the counts the score gives if the winner had served first.
* **Tennis My Life's rows share the fault.** In the matches R2 compared, they equal Sackmann's swapped counts in most and the truth in few.

**The review.** Three rounds, with the same three reviewers and the 8 Oct bar:
* RG 2019–2026 and AO 2025: 323 swaps;
* AO 2018–2024, 2026 and RG 2013–2015: 382;
* RG 2016–2018: 105.

| Reviewer | Round 1 | Addendum 1 | Addendum 2 |
|---|---:|---:|---:|
| R1 (rederive) | 323 | 382 | 105 |
| R2 (skeptic) | 323 | 382 | 104 |
| R3 (referee) | 323 | 382 | 105 |
| **All three** | **323** | **382** | **104** |

**The evidence the reviewers brought:**
* **Who served first.** Independent records never disagree with the point files:
  * hand charts: 457 + 566 + 46 matches (R2);
  * Court Vision: 1,262 matches at AO 2020–2024 (R3), and 735 at RG (R2).
* **The swaps themselves.** Where a record holds one, it reads the truth: 69 of 69 in round 1, 273 of 274 readings in addendum 1, and 3 of 3 in addendum 2. It never reads the row.
* **A test with no point files** (R1, R2) picks the truth over Sackmann's row in all 705 swaps of the first two rounds, and in 104 of 105 in the third. The test: games won on serve must equal service games, minus service games lost, plus the opponent's lost.
* **Six boxes come back.** Each concedes more breaks than it has service games as recorded (Stage 0's B8 drops it) and passes once exchanged:
  * Halep d. Tsurenko and Halep d. Swiatek, RG 2019;
  * Dimitrov d. Carreno Busta, AO 2021;
  * Muchova d. Tsurenko, AO 2023;
  * Noskova d. Svitolina, AO 2024;
  * Bartunkova d. Osuigwe, AO 2026 qualifying.

**The one left out: Stosur d. Halep, RG 2016 R16.** R1 and R3 confirmed it; R2 did not.
* **The swap is real,** but Sackmann's row also has Halep's break points wrong (7 faced and 2 lost, against the file's 12 and 3).
* **Exchanging the service games alone** would move her hold rate from 80.0% to 81.8%, further from the true 72.7%.
* So it is not a clear and complete fix, and stays as it is.

**Two confirmed swaps fail only a stricter proof** (`alternation_strict`, added at R3's suggestion):
* **Griekspoor d. Safiullin, AO 2024:** its file repeats a game. All three confirmed it on Court Vision and a hand chart.
* **AO 2019 MS140:** its file splits set 3 across three set records, with the alternation unbroken.

### 9.3 The candidate

`data/studies/rg_first_serve_recount/followup/confirmed/candidate/`:
* **`slam_box_overrides.csv`:** the decided table of 6 Oct (731 rows) and the 1,541 RG rows.
* **`corrections/row_corrections.csv`:** the decided table of 8 Oct (1,522 rows), with these appended:
  * step 2's split rows for the matches without an override: 12 at RG, 46 at the Olympics;
  * the 4 exchanges;
  * the 809 service-game swaps.
* **`corrections/id_aliases.csv`:** the decided table.

**The dry run**, through the build's own code on the raw rows:
* every override row reads its table: 1,541 RG and 731 decided;
* no row is both overridden and corrected;
* the exchanges read exchanged;
* every swap reads exchanged, with nothing else changed;
* 4,106 rows change, 0 outside the tables;
* 252 matches without a box get one.

**R3's simulation** across 12,762 AO, RG and Olympic rows: B5 failures unchanged, B8 failures from 6 to 0, and no row loses a box.

**Adoption** (decision, point 2; under item 6):
* **The rule:** adopt unless `compare.py` (both stages, both tours, seasons ≤ 2024) reads the candidate worse than the frozen reference by more than 0.1 mLL with the whole interval below 0, or an input is flagged "uneven".
* **The 2025–2026 part** is adopted with it on the data evidence.
* **When:** the build and its reading run in the build queue, after item 5 (the checklist's run order). The commands are in § 7.

### 9.4 Left as it is, with a recommendation

1. **Service-game mismatches that are not exact swaps** (about 1–3% of AO and RG matches; plus RG 2017's 123 matches recorded as 0 and 0, which Stage 0 treats as missing).
   * Where a record holds them, it reads the truth: 22 of 22 (R3); the no-point-file test 132 of 167 (R2).
   * **Recommended: yes, as a small follow-up.** Set both counts from the score and the proven first server, with a new correction action and the same three-reviewer check.
   * Low value, but the machinery exists.
2. **Stosur d. Halep** (RG 2016): one match, which needs its break points as well as its service games. **Recommended: leave it.**
3. **Future Australian Opens and Roland Garros** (the live pipeline).
   * Tennis My Life's rows of these Slams carry the same faults: its RG 2026 main draw has the first-serve fault, and its AO and RG service games copy Sackmann's derivation.
   * **Recommended: yes.** Take each new edition's box scores from the Slam's own feed through the override table once the feed is collected, as the 6 Oct decision does for Wimbledon and the US Open. That settles, for these two Slams, its open item "Making the Slam feeds the routine box-score source for later Slams".

**The owner's answer** (9 Oct 2026, on items 1 and 3 above and on running the harm check): "Execute these 3 fixes … if it requires the GPU wait if other CLAUDE processes are clearly using it" (§ 10).

## 10. The three fixes of the evening of 9 Oct

### 10.1 The remaining service-game errors: 558 matches set from the score

* **The operation:** `set_svgms`, new in `src/eda/input_data_audit/corrections.py`, with rule E8 in `stage0_build.py` and tests in `test/input_data_audit/test_corrections.py`.
  * It writes both players' service games.
  * It first checks that the source row still reads the table's serve points and the counts it replaces. Any mismatch stops the build.
  * No decided table uses it.
* **Which matches** (`service_games.py`; `followup/service_games/proposed_sets.csv`): AO and RG matches with a proven first server (the proof of § 9.2), whose service games are one of:
  * **blank** ("fill"), or 0 with serve points played, which Stage 0 already treats as missing: 460;
  * **wrong without being an exchange** ("other"): 98.
* **The consistency test.** The true counts must agree with the row's own break points and score: each player's games won, tiebreaks apart, equal service games, minus breaks conceded, plus the opponent's breaks conceded.
  * A row whose break points are wrong too fails it, as Stosur d. Halep did, and is left out (2 here).
  * The test independently backs the swaps of § 9: the truth passes it in 809 of 810, and the row in 1.
* **Where they are:**
  * AO 2019–2026: 55;
  * RG 2013 and 2014: 167 each (Sackmann's rows with serve points but no service games);
  * RG 2017: 132 (mostly 0 and 0);
  * a few in RG 2015–2024.
  * Left out: 141 matches with an RG override, which already take RG's service games, and 1 row the decided corrections name.
* **The review** (the same three reviewers, the 8 Oct bar; brief `followup/review/brief_service_game_sets.md`): **all three confirmed all 558, each with the values it derived itself.**
  * The row's own break points rule out the other possible first server in all 300 matches where it would matter (R3).
  * Court Vision (33 matches) and the hand charts (39) read the true counts every time (R3).
  * Of the 98 "other" rows, 96 have the right total but a split the score rules out, mostly a tiebreak not given its turn in the order of serve (R2). Every one fails the test with the row's own break points.
  * **455 boxes become full** (RG 2013: 164, RG 2014: 164, RG 2017: 126, RG 2023: 1).
  * Six RG 2013–2014 fills stay partial because those rows also lack double faults (R2, R3). The fill is right but changes nothing there for now.
* **Stosur d. Halep** stays out of everything: R3 withdrew its earlier vote for it, so all three now agree on 809 swaps.

### 10.2 Future Australian Opens and Roland Garros from the Slams' own records

**The decision:** [Future Australian Opens and Roland Garros take their box scores from the Slams' own records](../../decisions/2026-10-09-ao-rg-box-scores-from-feeds.md). From AO 2027 and RG 2027 on, each edition's matches take their whole box score from the Slam's statistics and point files once collected after the event, through the override table.

* **Collection.** The daily scheduler (`src/ingest/scheduled.py`) now reminds weekly until each record is collected: both Slams' Infosys statistics and point files, and rolandgarros.com's statistics (tests in `test/data_continuity/`). The adapters take the new years: `infosys_slams.py` AO and RG 2027–2030, raw only, and `rolandgarros.py --years`.
* **The Australian Open's key statistics are served,** like Roland Garros's. The 2026 edition was fetched (`data/studies/data_continuity/slam_infosys_overrides/collection/`).
* **The builder:** `src/eda/data_continuity/slam_infosys_overrides.py --edition AO2027`. It produces an edition's override rows:
  * the eight counts from the key statistics, and service games from the point file;
  * with the checks of the RG candidate: links by both names, the statistics' own consistency, statistics not short of the point file, agreement with the point file where it holds every point, and Stage 0's checks.
* **Validated on Roland Garros 2026.** From the key statistics alone it reproduces exactly the 351 reviewed overrides, with all eighteen values equal in 349. The other two show the known small gap between RG's two statistics feeds (99.7% agreement in 2025).
* **Validated on the Australian Open 2026.** The AO's key statistics name their statistics differently ("1st Serve In", "Win 1st Serve"); the builder reads both naming schemes.
  * Against Sackmann's AO 2026 rows they agree on every count: double faults 100%, serve points 99.8%, first serves in 99.6%, points won on each serve 99.8–99.9%, break points 99.9%, aces 98.4%.
  * Service games agree in only 84.5%, which is the swap fault of § 9.
  * So the AO's feed measures what the training data measured: the 6 Oct rule's condition.
  * Its 86 AO 2026 rows are a validation only. They are pre-freeze Sackmann rows, whose service games the candidate's swaps and sets already fix.
* **Recorded as open:** Wimbledon and the US Open after 2026, with Claude recommending the same routine. My earlier recommendation said they "already work this way"; that holds for 2026 only.
* **Live, during an event:** built with the betting pipeline, before the first AO or RG the project bets on.

### 10.3 The candidate build and the harm check (steps 3–4 of item 6)

**The candidate:**
* the 1,541 RG overrides;
* step 2's split for 58 other matches;
* the 4 exchanges;
* the 809 service-game swaps and the 558 sets.

Final tables: `followup/confirmed/candidate/` (overrides SHA-256 `505336f6…`, corrections `25e48366…`). Records are in `data/studies/current_best_model/2026-10-09_rg_box_scores/`.

**The GPU** was free when the build started (1% use, no Python process on the card). Other sessions were building their own candidates in other sandboxes, so the fits wait their turn: `model_rebuild/fits.py` holds each fit until no other local-environment process runs and 12 GB of the card are free.

**The build so far:**
1. **Setup:** `run_chain.py --setup --candidate`. The history gate passed: the live Stage 0 equals the frozen reference's history.
2. **Stage 0, in the sandbox,** with the candidate tables.
   * The first attempt was stopped. The shell's `cp` asks before overwriting, so the copy of the final corrections silently declined, and the sandbox still held the table without the 558 sets. The build's log showed 2,393 corrections where the final table has 2,951.
   * The tables were copied again, forced, with their SHA-256 checked against the repository's. The rebuild then logged 2,272 override rows and all 2,951 corrections.
3. **The trim** (`candidate_trim.py`; `candidate_trim.json`). The sandbox build reads today's source files, so it also brought 35 matches played since the live build and newer rows for 160 recent ones. All are 2026 events of 30 Sep – 7 Oct: row positions in the newer Tennis My Life files, and 6 new Beijing box scores.
   * The trim dropped the 35, and restored the 160 from the live tables.
   * Afterwards the candidate differs from the live Stage 0 in exactly the 2,964 matches its tables name, and nowhere else.
   * Against the live tables: no box is lost and 578 player rows gain one.
4. **Stage 1's odds:** rebuilt in the sandbox and identical to the live table (93,031 rows), as expected with the same matches.
5. **The timeline:** not rebuilt. It would re-link match days from source folders that changed since the freeze (the lower-level-evidence study's warning), and the candidate changes no match or date.
6. **The leak-proof features** (`match_timing/rebuild.py`, lane 0's last step): exit 0 in 32 minutes.
7. **Lanes 1–3:** every step exit 0. Lane 1 took 220 minutes on the shared machine, lane 2 28.
   * The model frame has 67,226 matches × 58 inputs, the reference's match count.
   * All its own checks pass. (Their "31 unchanged inputs" counts the inputs the frame copies verbatim from the frame upstream. This line first misread it as inputs unchanged against the reference; step 9 has that count.)
   * Collected into the records folder.
8. **The fits** (seeds 0–3, seasons 2019–2024, the reference's 58-input list, so the comparison isolates the data). At collection the card was busy with another session's fits (99% use, 16 GB).
   * As the owner asked, these wait: a watcher outside the GPU environment starts `fits.py` only after no local-environment process has run for three minutes (`fits_wait.log`).
   * `fits.py` then takes its own turns as usual.
   * The watcher was stopped before any fit started, and restarted after step 10.
9. **The input check** (`compare.py`'s first part, read before any fit; 10 Oct, 06:15 UTC).
   * **41 of the 58 inputs move, all built from box scores.** The other 17 are identical to the reference's:
     * the odds;
     * the three Elo inputs;
     * age and its square;
     * sets in the last 14 days;
     * tour, surface, level, round, best of and indoor;
     * the four surface season and layoff inputs.
   * **Seven are flagged "uneven", in WTA 2013 and 2014 only:** form_hold, form_brk, form_bp_faced_pg, formdef_bp_faced_pg, iosO_hold, iosD_hold, and prod_hold, the matchup product built from the IOS hold ratings.
   * **Their dose explains them** (`input_dose.py`, which reads no result; its tables are in the records folder's `input_dose/`). In the reference, the WTA has almost no service-game counts in those two seasons: 20 player rows in 2013 and none in 2014, all levels. The candidate's sets at RG 2013 and 2014 add 328 player rows each, the first women's hold data of those seasons (§ 10.1).
     * No WTA match before RG 2013 moves: 1,130 matches, at a threshold of 0.001 SD.
     * From RG 2013 on, the four form inputs go from missing to known: 884 matches in 2013, 1,786 in 2014. The IOS hold ratings, which had almost nothing to rate from, spread out (scale ratio 9.3 in 2013, 2.1 in 2014).
     * The form inputs' scale ratios compare against only 3 (2013) and 19 (2014) known reference values.
     * From 2015 the WTA has thousands of hold records from other events. The same kind of sets, such as RG 2017's 126 newly full boxes, move nothing enough to be flagged.
     * The ATP's 2013–2015 hold inputs move by about a millionth of an SD (99th percentile under 0.0001 SD): a constant pooled across both tours. The ATP's own service games change only from RG 2016.
   * **Not harm, by the owner's later rule.** The adoption-by-kind decision of the same evening reads candidate builds by kind of change. For a repair, an input flag counts as harm only "in a way its dose does not explain" ([decision](../../decisions/2026-10-09-adoption-by-change-class.md), point 4).
     * The RG decision's own wording ("or an input is flagged 'uneven'") came first. I read it with that refinement, which the owner adopted later the same day.
     * These flags are the fix doing what it is meant to: the women's 2013–2014 hold inputs now carry the RG records they lacked.
   * **The first collection also flagged `indoor`,** in exactly the 14 women's seasons: 32,634 rows, the 32,507 women's matches and the 127 of the men's 2026 US Open.
     * That is the indoor fill decided the same day ([decision](../../decisions/2026-10-09-indoor-input.md)), which `tabpfn_thinking/build_frame.py` now applies in every build.
     * It is not this candidate's change.
10. **Rebuilt without the indoor fill** (10 Oct, 06:20 UTC), so that the candidate differs from the reference by this repair alone.
    * The steps:
      * `build_frame.py --indoor-men-only`, the indoor decision's own undo;
      * then the leak-proof frame, the Elo frames and lane 3, by run_chain's runner (`chain_lane1i.json`, `chain_lane3.json`).
      * Every step exited 0, in 74 seconds in all.
    * The new frame differs from the first only in `in_indoor`, and `indoor` is identical to the reference's. The input check then flags only the seven of step 9.
    * The first collection is kept in `first_collect_indoor_filled/` (frame SHA-256 `af51f912…`). The frame to be fitted is `8549316e…`.
    * **Why not keep the fill.** The reading is this repair's bug check: with the fill inside, it could not say which change moved it. The template combines the decided changes, and checklist item 10, the holdback, reads them together.
11. **The fits** (10 Oct, 06:39–06:53 UTC). The card was free for three minutes after the lower-level-evidence session's batch. All 24 fits exited 0, every one on frame `8549316e…`.
12. **The reading** (`compare.py --candidate`; seasons 2020–2024, 22,265 matches; `vs_reference_2026-10-08/`). Both stages, mLL per match, + = the candidate better:

    | Population | Candidate vs reference | P(better) | Reading |
    |---|---|---|---|
    | **Both tours (the declared primary)** | **−0.026 [−0.076, +0.023]** | **0.145** | **unresolved** |
    | Men | −0.023 [−0.084, +0.038] | 0.229 | unresolved |
    | Women | −0.030 [−0.103, +0.043] | 0.206 | unresolved |

    * Stage 1 alone reads the same: −0.026 [−0.076, +0.023].
    * For scale: the reference beats its calibrated close by 1.374 [0.668, 2.081], the candidate by 1.348 [0.648, 2.048].
    * **What the comparison can see** (`adoption_read.py --kind repair`, `adoption_read.json`). Its resolution is ±0.049 mLL, with 80% power at 0.069. A repair's plausible effect is about 0.02, so the comparison is blind to it: the reading decides nothing and serves as the harm check.
13. **The verdict under the declared rule: no harm, so the candidate is adopted.**
    * **The harm test:** worse by more than 0.1 mLL, with the whole 95% interval below 0. The estimate is −0.026 and the interval reaches +0.023, so neither part holds. Nor does the adoption-by-kind decision's "small harm", an interval wholly below 0.
    * **The input flags** are the fix's own dose (step 9).
    * **`adoption_read.py`:** "adopt, pending the input check", and the input check is read (step 9).
    * **The lean.** The estimate sits about one standard error below 0. A reading that low or lower comes about one time in seven when the true effect is 0.
      * The slices (tours, stages) are slices of one reading. They were not searched for a cause.
      * A repair is decided on the data evidence and is not vetoed by its outcome (errata E4).
    * Recorded in the pooled class record (`data/studies/adoption_framework/class_record.csv`, `rg_box_scores`).
    * **The lean, examined at the owner's question** (10 Oct; slices of the same run, read as description; `reading_split.py` → `reading_split.csv`):
      * **By level:** Slams −0.065 [−0.162, +0.033] (P(better) 0.09; all four seeds negative); 500s −0.057 (0.12); 1000s −0.001; 250s −0.003. The lean sits where the fix acts first: at the two Slams and in the events just after them. Every slice is unresolved, and the Slams are the most negative of five levels.
      * **Men and women lean alike** (−0.023 and −0.030), so the women's 2013–2014 flags are not indicated as the driver.
      * **No feasible re-run settles it.** The seeds carry 28% of the variance, so 16 seeds would narrow the SE only from 0.0246 to 0.0218. Only more matches would.
      * **Context:** the pooled record's other repairs read +0.007, +0.024, +0.03 and −0.05, all unresolved, with mixed signs.
      * **The recommendation does not rest on a prior that the fix scores better on the backtest** (the owner asked whether it did). In a backtest the wrong numbers are used consistently in training and testing, so a prior for the backtest effect should be small. The reading combined with normal priors (per match, + = the fix better):
        * no prior (flat): P(better) 0.14, expected −0.026;
        * 0 ± 0.02: 0.25, −0.010;
        * +0.01 ± 0.02: 0.39, −0.004;
        * +0.02 ± 0.02: 0.54, +0.002;
        * +0.02 ± 0.01, a confident gain, not held: 0.93, +0.013.

        A sensible prior leaves the fix about 60–75% likely to score a hair worse on the backtest, by under 1% of the model's edge over the close. Read purely as a backtest bet, the arithmetic would lean slightly against it. That is why data fixes are decided on the data, with the backtest as a bug alarm (framework § 2; errata E4).
      * **Why the recommendation stands.** The backtest compares wrong statistics everywhere with right statistics everywhere. Live, the Australian Open and Roland Garros will feed the Slams' official statistics (decided 9 Oct, § 10.2).
        * Not adopting therefore means a model trained on the wrong statistics and fed the right ones at exactly those events: a train-live mismatch the backtest cannot see, and which the prediction-run rule forbids.
        * A consistent "no" would also feed Tennis My Life's faulty Slam statistics live (its Roland Garros 2026 main draw carries the first-serve fault, § 9.4). That builds on a third party's known error, which changes if they fix it.
14. **Was it applied as confirmed?** (the owner: "The next possiblity is that you fixed it incorrectly? how likely is that?"; `verify_applied.py`, which reads no result; tables in the records folder's `verify_applied/`.) Five end-to-end checks of the built candidate against the reference:
    * **V1, the values.** Every confirmed value reads in the built Stage 0 as its table gives it, on the right player: 27,738 override values, 534 split values, 72 exchanged-box values, and the swaps and sets.
      * 12 rows differ from that simple expectation, and all are explained.
      * 6 swapped matches had been dropped by Stage 0's own box check in the reference ("breaks conceded exceed service games"): the wrong service games made them fail. They now pass, so the fix rescues them.
      * 6 RG 2013–2014 sets sit in boxes that also lack double faults, which Stage 0 still drops (§ 10.1).
    * **V2, the orientation**, by two tests that use none of this study's derivations.
      * **Service games against the score** (games won, tiebreaks apart = service games − breaks conceded + breaks made):
        * the swapped matches go from 0% to 100% consistent, and the set ones from 0% to 100%;
        * the overrides go from 97% to 100%, and the exchanged boxes from 1 of 4 to 4 of 4;
        * the Australian Open's and Roland Garros's uncorrected matches are unchanged (96%), as are Wimbledon's and the US Open's.
      * **The winner won more points:** 93.7% of the overridden matches after the fix, beside 95% at the uncorrected Slams. A box on the wrong player would read about 6%.
        * After the four exchanged boxes, 1 of 4 winners won more points (3 of 4 before).
        * All four are close three-setters.
          * In two, the loser won more regular games; in one, as many.
          * In the fourth (Peterson d. Rogers), the winner won 18 regular games to 14 but 115 points to 117.
        * The score test passes all four after the exchange, against one before: Muchova's, whose two boxes pass either way.
    * **V3, the timing.** No input changes before the first correction that can reach it.
      * The hold inputs move from RG 2013 (women) and RG 2016 (men).
      * The point inputs move from RG 2022 for the men.
      * For the women, the point inputs move from RG 2019: two of the rescued boxes are RG 2019 matches.
        * Every women's row changed before RG 2021 lies on a route those two boxes allow: inside their light cone for per-player inputs, or, for IOS, starting after their results count (2 June 2019). None lies outside.
      * The men's IOS inputs first move in the later rounds at Geneva and Lyon, the week of RG 2022's qualifying. No row starts before the first corrected result counts (17 May 2022).
    * **V4, the direction.** First serves in fall in most overridden rows, and each edition's pooled rate falls to near RG's own level (men 2022: 67.9% → 62.7%; women 2022: 68.7% → 64.3%).
    * **V5, Stage 0's own checks.** 42 fewer boxes fail a sanity check (second-serve points, break points saved, breaks conceded, serve points per game), and no check fails more often.
      * Each correction appears in Stage 0's log with exactly its count.
      * Three other counts moved (by 16, 1 and 1). They come from newer source files that the build read before the trim (`candidate_trim.json`).
    * **Two slips while checking**, both in the checks, not in the fix: the timeline's days are day numbers since 1970, first read as dates, and a path was off by one folder. Each was fixed and rerun.
    * **Assessment:** an application error large enough to matter is now unlikely, about 1–2% (it was about 5% before these checks).
      * What remains unchecked would have to keep every count consistent with the score, with RG's official totals and with Stage 0's checks.
      * The likeliest place for it is the first-serve split, which the score test does not cover. That split is RG's own record, confirmed by Court Vision and the hand charts (§ 2.3).

**Note added 9 Oct 2026 (late evening), by another session: the gate this build passed through was narrowed.**
* The owner narrowed the 8 Oct freeze to lower-level data ([current-best-model decision](../../decisions/2026-10-08-current-best-model.md), amendment of 9 Oct). Main-tour corrections and new official sources are now repairs, decided on the data evidence. `history.py` lists them, but no longer refuses a template build.
* **This build is unaffected.** It is a candidate build, which the gate never stopped.
* **Its harm check still serves as the bug check** of the data-fix lane, and its declared rule stands.
* **Once the owner accepts the candidate,** its tables can enter the live Stage 0 without refusing later template builds.

### 10.4 Adoption: decided, with the swap waiting for a coordinated rebuild

**Officially adopted by the owner on 10 Oct 2026:** "Official decision: adopt, with the tripwire on the Slam number." The owner also asked that nothing conflict with the level-layer work running in another session.
* **The tripwire** is fixed in the [decision record](../../decisions/2026-10-09-roland-garros-box-scores.md), before any match it reads, and tracked as checklist item 12.
  * It reads the repair against the pre-adoption tables on Slam matches from the 2027 Australian Open on, first after the 2027 US Open.
  * If it reads worse with the whole 95% interval below 0, Claude recommends reverting.
* **The application now waits for the level-layer work** (its prompt: `docs/studies/lower_level_evidence/system/IMPLEMENTATION_PROMPT.md`), no longer for the lower-level study's arm builds, which have finished.
  * That work edits the chain's builders and builds the template.
  * Its replay check builds Stage 0 from the decided tables, so a swap now could make it fail for a reason not its own.
  * The steps below run once it reports done, followed by a template build that carries both changes.
* **The build sandbox was renamed, not deleted,** to `C:/Users/zerom/tnr_sb_rg_candidate`.
  * The level-layer work's template build runs `run_chain.py --setup` on the default path, `C:/Users/zerom/tnr_sb`, which this build occupied.
  * The candidate's Stage 0 stays there for `input_dose.py` and `verify_applied.py`: pass `--candidate-stage0 C:/Users/zerom/tnr_sb_rg_candidate/data/studies/predictability_diagnostic`.
  * Remove it with `MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_sb_rg_candidate ./python.sh src/eda/model_rebuild/run_chain.py --cleanup` once the owner agrees.

The plan as first written on 10 Oct, before the official decision:

* **Adopted on 10 Oct 2026** under the RG decision's rule (point 2). The 2025–2026 part is adopted with it on the data evidence, unread.
* **What adoption changes.** Two decided tables take the candidate's; the aliases are unchanged. Stage 0 changes when it is next built.
  * the Slam overrides: 731 rows, plus 1,541;
  * the row corrections: 1,522 rows, plus 1,429 (4 exchanges, 58 split rows, 809 swaps, 558 sets).
* **Not yet applied, on purpose.** The live Stage 0 is rebuilt in one coordinated run (`rebuild_stage0.py`), at a time no study is building on it. The swap goes in the same run.
  * **The lower-level-evidence study is building its arms on today's tables.** Its gate G2 requires every input outside its own change to equal the reference's.
    * At 06:52 UTC that gate failed on the indoor fill, which reached a sandbox set up after the fill entered the repository.
    * A Stage 0 carrying this repair would fail it the same way.
  * **Swapping the tables ahead of the rebuild would split the data.**
    * Prediction runs build their own Stage 0 from the decided tables, while template builds copy the live Stage 0.
    * The replay proof compares the two.
* **The steps, once the lower-level study's arm builds are done:**
  1. `./python.sh src/eda/rg_first_serve_recount/adopt.py --check`. On 10 Oct it reports "ready": every decided row is in the candidate unchanged.
  2. `adopt.py --apply`. It keeps the replaced tables, with their SHA-256, in `data/studies/rg_first_serve_recount/adoption/<stamp>/`; `--restore <stamp>` puts them back.
  3. `./python.sh src/eda/data_continuity/rebuild_stage0.py`, the coordinated rebuild; its own `--restore` undoes it.
     * It also brings what any rebuild brings: the matches played since, and the timeline re-linked from the current source folders.
  4. `./python.sh src/eda/current_best_model/history.py`. The main-tour differences from the reference must be the candidate's 2,964 matches and those the rebuild brings.
  * The next template build then carries the repair. Checklist item 10, the holdback, reads it with the other adopted changes.
* **The build sandbox** `C:/Users/zerom/tnr_sb` is no longer needed.
  * The records are collected, and the rebuild does not use it.
  * It occupies `run_chain.py`'s default sandbox path.
  * Its removal (`run_chain.py --cleanup`) is recommended to the owner, not done.

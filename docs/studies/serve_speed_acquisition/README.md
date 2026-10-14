# Serve-speed acquisition: ManTennisData and the AO and RG Infosys files

**Status: data collection under the [owner's decision of 7 October 2026](../../decisions/2026-10-07-serve-speed-acquisition.md), not a selection.** No feature, model or holdout was touched. On 8 October the ATP's own files of 2015 to October 2021 were added, downloaded and **not decrypted**, on the owner's instruction (section 8).

**Update, 8 Oct 2026 (evening):** the owner then had those files decrypted (`src/ingest/point_sources/infosys_atp_decrypt.py`). They are staged, checked and integrated in the [ATP backfill study](../infosys_atp_backfill/README.md): serve speeds exist only at the 2018 ATP Finals and Washington, San Diego and Indian Wells 2021 (184 matches); 2019–2020 hold points without speeds. `speeds.parquet` now includes them (source `infosys_atp`).

Labels: **observed** (seen in the files or measured here), **documented** (the provider's own code or schema), **inference**.

**The request** (owner, 7 Oct 2026):

> "We are trying to acquire more serve speed data. In another prompt session I was recommended to Download ManTennisData (about 32 MB) msolonskyi/ManTennisData on GitHub and Decrypt the AO and RG files for the 2025–26 Slam gaps."

These were options 1 and 3 of the [serve-speed sources research](../../research/serve-speed-sources/README.md#5-what-could-be-done-first-options-not-decisions).

* **The two are separate sources.** ManTennisData is plain CSV and holds no Slam speeds. The "AO and RG files" are the two Slams' own Infosys match-centre feeds.
* **What the speeds are for:** the [point-sequence study's](../point_sequence/README.md) serve-speed-change statistic, whose only clean test left is the closed 2025–26 holdout.

## In short

**Both acquisitions are done** *(observed)*:
* **ManTennisData** (section 1):
  * 10 files, 31.6 MB, at commit `4e2d39f` (4 Oct 2026).
  * 10,055 matches carry both players' first-serve average, from October 2021 to October 2026: ATP tour level and some Challengers.
  * 9,288 of its 9,291 tour-level matches link to Stage 0.
* **AO 2025, RG 2025 and RG 2026** (section 2):
  * 1,910 requests brought 1,891 files for 1,417 of the 1,434 match codes, and every file decrypted.
  * 1,410 matches have points, and every one has timed serves: 232,965 timed points of 235,725, main draws and qualifying, men and women.
  * RG's key statistics cover 941 matches.

**It is right** *(observed; section 3)*:
* **Against another copy:** the AO 2025 points equal SirGenkii's independent decrypted copy point for point, 3,368 of 3,368.
* **Against official and third-party numbers:** each agrees with the decrypted points:
  * Tennis Australia's own plain match averages, 10 of 10;
  * RG's own key statistic, 1,443 of 1,452;
  * Flashscore, on 256 matches, within its whole-number rounding.
* **ManTennisData** equals the ATP's decrypted key statistics on every match checked: 5,847 of 2021–24 and 333 player-matches of 2025.
* **No measuring break** shows where the decrypted files begin.

**What it adds** *(observed; section 4)*:
* **Men, 2025–26 holdout:** the feature rises from 622 matches to **2,590**, from 13% to 53%. Power for the replication's effect rises from 17% to **54%**.
* **Polymarket window:** men's main-tour coverage rises from 8% to **58%**.
* **Women:** 9% to 12%. No WTA tour-level source exists.

**The ATP's own files, 2015 to 17 October 2021** *(observed; section 8; 8 Oct 2026)*:
* 9,162 requests brought 4,902 files for 2,070 matches (234 MB). They are kept as served and **not decrypted**, on the owner's instruction.
* **2015–2017:** no event has a file.
* **2018–2020:** only the 2018 and 2019 ATP Finals, the 2019 Next Gen Finals, and Vienna, Paris, Sofia and the ATP Finals of 2020: 209 matches.
* **2021:** all 52 events, every main-draw match (1,751) and 110 qualifying matches.
* **Whether any of them carries a serve speed is unknown** until they are decrypted. *Answered the same evening:* 184 matches do (the 2018 ATP Finals; Washington, San Diego and Indian Wells 2021), and 43 of the 2021 events' point files are empty ([backfill study](../infosys_atp_backfill/README.md)).

**Found on the way** *(observed)*:
* **A lead for ATP 2015–20:** the ATP's own files carry speeds before its pages showed them (the 2018 ATP Finals; Washington, August 2021). Followed up on 8 Oct: section 8.
* **AO 2024 reads fast:** in the held Hawk-Eye copy it reads about 3 km/h fast for the same players, against both 2023 and 2025.
* **Stage 0 gaps:** it lacks RG 2026's women's qualifying (112 matches, all now timed). It also lacks 216 of the 308 Challenger qualifying matches of 2026 that ManTennisData times.
* **A research note was wrong:** lane A2's example "MS101 Sinner, 194.1 km/h (n = 79)" was the first-serve points that Jarry ended. Corrected in place.

**Still missing:**
* WTA tour-level speeds (vendors only);
* the ATP tour-level events that recorded no speed (Barcelona, Munich and Houston every year, and others);
* ATP 2015–20: the ATP's host has no file for 2015–17 and few for 2018–20 (section 8). Decrypted on 8 Oct, the 2019–20 files hold points but no speed; only the 2018 ATP Finals are timed ([backfill study](../infosys_atp_backfill/README.md)).

## 1. ManTennisData

**What was downloaded** *(observed)*:
* **Version:** commit `4e2d39f99e` of [`msolonskyi/ManTennisData`](https://github.com/msolonskyi/ManTennisData), dated 4 Oct 2026 ("atp update 2026-10-04"). It was still the head when downloaded on 7 Oct 2026.
* **Files:** `atp/matches_2021.csv` … `matches_2026.csv`, `tournaments.csv`, `players.csv`, the README and the licence. That is 10 files and 31.6 MB, each checked against the repository tree's git blob hash.
* **Errors:** none.
* **Seasons 1999–2020** are in the repository but carry no speed, so they were not fetched (`--years all` adds them).

**What it holds** *(observed)*:
* **Rows:** 78,453 match rows for 2021–26: tour level, Challengers and Slams, with the box score.
* **Speeds:** 10,057 rows have both players' first-serve average above zero. By season: 235, 1,521, 1,815, 2,440, 1,710 and 2,336.
* **No Slam row has a speed.**
* **Implausible values:** of 20,252 player values above zero, four are 40 km/h or below (the minimum is 14) and count as missing. Another 27 lie between 40 and 120 km/h. They stay in under the project's 40–270 km/h rule; for men they are almost certainly errors.

**Linking** *(observed; `links.json`)*:
* 9,986 of the 10,206 matches with any speed link to a Stage 0 match and its side.
* **Tour level** (Masters, 250s, 500s, Finals and team events): 9,288 of 9,291.
* **Challengers:** all 382 main-draw matches of 2026 link. 216 of the 308 qualifying matches of 2026 do not, because Stage 0 holds only part of 2026's Challenger qualifying.
* **Corrected on 7 Oct 2026:**
  * `speeds.py` had labelled all 713 timed quarter-finals as qualifying, because their round code `QF` starts with "Q".
  * The linker penalises a draw that disagrees with Stage 0's. So 4 of them had gone to a qualifying match between the same two players instead of their own quarter-final: Orleans and Brest 2022, Eastbourne 2024 and Nottingham 2026.
  * The label now uses the data map's qualifying-round test, and all 4 link to their own quarter-finals.
  * No count in this report changes. In `coverage_matches.csv`, four cells move by one match.

**It equals the ATP's own decrypted numbers** *(observed; check 5, section 3)*:
* **2021–24, Hugging Face handoff:** on all 5,847 matches that both time, both players' first-serve averages are identical.
* **2025, SirGenkii's key statistics:** all 333 player-matches are identical, as lane B found.
* **What decrypting the ATP Stats Centre files would add, 2021–24:**
  * 194 timed matches ManTennisData lacks. 98 of them are from Washington (August) and Indian Wells (October) 2021, before ManTennisData's speeds begin. The others are scattered, at most 17 per event.
  * **So the ATP's files carry speeds earlier than its pages showed them.** The handoff has them for Washington 2021 (August), and for all 10 records it holds from 2018 (the ATP Finals). Lane A1 had found no per-match speed before October 2021.
  * That is a lead for the ATP's 2015–20 gap. It concerns the ATP's own files, which the decision did not cover. They were downloaded on 8 Oct 2026, still encrypted (section 8).
  * The reverse also happens: 164 matches are timed in ManTennisData only.
  * So for match-level averages, the ATP files would add about 3%. Their remaining value is per-point speeds.

## 2. The AO and RG Infosys files

### 2.1 How the files are encrypted, and how they are opened

* **What the pages load** *(observed)*: each Slam's match-centre page loads its data per match from an Infosys host, `itp-ao-sls.infosys-platforms.com` or `itp-rg-sls.infosys-platforms.com`. No login is needed.
* **The format** *(observed)*: every file is an envelope `{lastModified, response, data: null}`, or at RG 2025 six such envelopes in one file. `response` is base64 AES-128-CBC ciphertext.
* **The key** *(documented in the public implementation, observed to work)*:
  * It is derived from `lastModified` alone: `#`, then 14 characters, then `$`. The IV is the key in upper case.
  * The 14 characters are `lastModified`'s digits read as hexadecimal and written in base 36, followed by (year + reversed year) × (day + reversed two-digit day) of its UTC date in base 24. The result is padded with zeros or cut to 14.
  * This is the step the page's own script runs in every visitor's browser. The project's code follows [`nipunagarwalla/courtside`](https://github.com/nipunagarwalla/courtside) (`backend/scrapers/infosys/decrypt.py`, taken from atptour.com's `main.js`); the tests pin it to that code's keys.
* **It opened everything** *(observed)*: every one of the 4,104 blocks with content opened, with no failures, on both hosts and in both years.
* **What is kept:** the served envelopes, still encrypted, are the raw files. Decryption happens at staging, so the bytes the sites sent are what is preserved.

### 2.2 The collection

* **Before the run** *(observed)*: four probe requests tested the scheme on the men's finals: RG 2025's match-centre file, AO 2025's MatchBeats file, and both of RG 2026's API routes. A two-match dry run of the adapter followed (AO 2025 MS701 and MS101).
* **The run:** 7 Oct 2026, 15:43–17:04 UTC. 1,910 requests, at least 2 seconds apart plus up to 1 second of jitter.
  * No retry was needed.
  * There was no error, block, challenge or redirect, and no family was given up.
* **Routes** (the only ones serving these editions; lane A2's probes and the earlier passes):

| Edition | Route | What it holds |
|---|---|---|
| AO 2025 | `static/prod/match-beats/2025/580/<MID>/data.json` | MatchBeats: every point |
| RG 2025 | `static/prod/match-centre/2025/520/<MID>/data.json` | Six blocks: MatchBeats, key statistics per set, rally analysis, match status (with the match date), insights, quiz |
| RG 2026 | `prod/api/match-beats/data/year/2026/eventId/520/matchId/<MID>` | MatchBeats |
| RG 2026 | `prod/api/stats-plus/v1/keystats/year/2026/eventId/520/matchId/<MID>` | Key statistics per set |

* **Match codes:** every singles code of both draws and both qualifying events, the final round first.
  * AO: `MS/WS 701 … 101-164` and `MQ/WQ 301 … 101-164`.
  * RG: `SM/SD 001-127` and `QM/QD 016-127`.
* **Absent files:**
  * **17 codes had no file.** S3 answered "AccessDenied", which the run read as "no such object" only on a route that had already served a file to the same headers.
  * Stage 0 records none of the 17 as a walkover, so they are played matches whose files are not served *(observed)*:
    * AO 2025: WS101, MQ222, MQ228, MQ314, MQ316, WQ222, WQ226, WQ301 and WQ314;
    * RG 2025: eight men's qualifying codes.
  * **Four RG 2026 key-statistics codes were answered 404.** They are walkovers, and their MatchBeats files hold no points.

### 2.3 What the files hold

*Observed. "Timed" = at least one point with a serve speed; "≥ 90%" = at least 90% of the match's points timed.*

| Edition | Draw | Codes | With a file | Matches with points | Timed | ≥ 90% timed | Points | Points timed | With key statistics |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AO 2025 | Men's main | 127 | 127 | 127 | 127 | 127 | 29,072 | 28,915 | – |
| | Men's qualifying | 112 | 108 | 108 | 108 | 105 | 15,613 | 15,238 | – |
| | Women's main | 127 | 126 | 126 | 126 | 124 | 18,264 | 18,098 | – |
| | Women's qualifying | 112 | 108 | 108 | 108 | 103 | 15,896 | 15,494 | – |
| RG 2025 | Men's main | 127 | 127 | 125 | 125 | 125 | 28,143 | 27,890 | 125 |
| | Men's qualifying | 112 | 104 | 103 | 103 | 102 | 15,213 | 14,969 | 103 |
| | Women's main | 127 | 127 | 127 | 127 | 124 | 17,997 | 17,814 | 127 |
| | Women's qualifying | 112 | 112 | 112 | 112 | 109 | 15,633 | 15,380 | 112 |
| RG 2026 | Men's main | 127 | 127 | 124 | 124 | 124 | 29,139 | 28,926 | 124 |
| | Men's qualifying | 112 | 112 | 111 | 111 | 111 | 16,611 | 16,387 | 111 |
| | Women's main | 127 | 127 | 127 | 127 | 127 | 17,791 | 17,669 | 127 |
| | Women's qualifying | 112 | 112 | 112 | 112 | 112 | 16,353 | 16,185 | 112 |
| **All** | | **1,434** | **1,417** | **1,410** | **1,410** | **1,393** | **235,725** | **232,965** | **941** |

* **Every match with points has timed serves,** outer courts and qualifying included. 98.8% of all points carry a speed.
  * So the outer courts the research expected to be missing at RG are timed in 2025–26.
  * The seven files without points are walkovers: Stage 0 records all seven as such, among them RG 2026's semifinal SM002.
* **A MatchBeats point** holds:
  * the server and the serve number (1 or 2);
  * the speed of the serve that started the point, and a first-serve fault's speed;
  * the point's ending (winner, error, ace and so on), the stroke and hand;
  * both players' rally counts, break and crucial-point flags, the score and the match clock in seconds. On the RG 2025 final's last point it reads 19,767 seconds, or 5 h 29 min.
* **RG's key statistics** give, per set and for the match, the maximum, the first- and second-serve average speeds and the box score.
* **RG 2025's rally analysis** covers 345 matches and 57,483 entries. It files every point under the shot that ended it (return, 3rd shot … 10+ shots), with the serve's speed, direction (wide, centre, body, net) and court side.
* **Linking** *(observed; `links.json`)*: every match with a file links to Stage 0 and is oriented, except RG 2026 women's qualifying (112 matches). Stage 0 holds no RG 2026 women's qualifying, so they will link once it does.

## 3. Checks

*All observed; `checks.json`, from `speeds.py`. "Mean of first serves in" = the mean speed of the points a player played on his or her first serve, from the decrypted points.*

| # | Against | Result |
|---|---|---|
| 1 | **SirGenkii's rally analysis**: its own decrypted copy, through the ATP's host, of the 14 AO 2025 men's first-round matches it holds | Joined on the point id, **3,368 of 3,368 points** are in both, with the **same speed and the same serve number** on every one (largest difference 0.0 km/h) |
| 2 | **The AO match centre's plain "1st Serve Average"**: Tennis Australia's own unencrypted API, in the held Wayback captures | All **10 of 10** player-matches (5 matches) equal the rounded MatchBeats mean of first serves in. The differences run from −0.02 to −0.48 km/h |
| 3 | **RG's own key statistic**, "1st Serve Average Speed", against the same file's points | **1,443 of 1,452** player-matches equal the rounded mean of first serves in, and 1,448 are within 1 km/h. The median difference is 0.0 km/h, and the count of first serves in equals the timed first-serve points (median difference 0). So RG's statistic is the rounded mean of first serves in |
| 4 | **Flashscore's "Average 1st serve speed"** (held handoff crawl, unoriented) | **256 matches**: AO 2025, 32 matches, mean difference +0.004 km/h; RG 2025, 224 matches, −0.11 km/h. Each player's median error is 0.25 km/h, Flashscore's whole-number rounding. RG 2026 is after the crawl ended (17 Apr 2026) |
| 5 | **ManTennisData against the decrypted ATP key statistics** | **5,847 of 5,847** matches of 2021–24 (handoff) and **333 of 333** player-matches of 2025 (SirGenkii) are identical. Coverage differences are in section 1 |
| 6 | **Continuity**: each player's mean of first serves in at the same Slam a year or two apart, for players with at least 20 first serves in each time | **No break at the new files** (below) |

**Check 6 in detail.** Median change for the same players, km/h; positive = faster in the later year:

| | 2022→23 | 2023→24 | **2024→25** | **2025→26** | **2023→25** |
|---|---:|---:|---:|---:|---:|
| AO, men | +0.2 | +3.5 | **−3.4** (111 players) | – | **+0.3** (92) |
| AO, women | +0.5 | +2.4 | **−2.9** (103) | – | **−0.9** (95) |
| RG, men | +2.7 | −0.8 | **+0.3** (62) | **+0.8** (158) | **+1.6** (49) |
| RG, women | +2.5 | −0.6 | **+0.3** (59) | **−0.6** (106) | **+1.9** (45) |

* **AO 2025 reads at AO 2023's level** for the same players. The outlier is AO 2024, in the held Hawk-Eye copy, which reads about 3 km/h fast for both tours *(observed)*.
* **RG 2025–26 continues smoothly** from 2024.
* **Year-to-year medians since 2015 range from −5.3 km/h** (RG men 2019→20, the edition played in October) **to +4.3**. So this check cannot see a shift smaller than about 3 km/h.
* **The AO 2024 jump matters for the feature** wherever a player's 52-week window holds AO 2024 *(inference)*.

## 4. What the two sources add to the serve-speed feature

*Observed: `coverage_after.py`, `coverage_summary.json`. It reads no match result.*

**The feature and frame** are the research's ([section 2.2](../../research/serve-speed-sources/README.md#22-the-feature-itself-on-the-main-tour-main-draws)):
* The frame is Stage 0's main-tour main draws.
* A match carries the feature when both players have a timed match in the previous 14 days.
* The research's scenarios S0 (held) and S1 (files on disk) are reused unchanged. The new ones are what was acquired, counted per player:
  * **N1:** plus ManTennisData;
  * **N2:** plus the decrypted AO and RG files.
* **Ceiling** (hypothetical): every ATP tour-level match of 2025–26 timed, on top of N2.

| | Frame | S0 held | S1 + files on disk | **N1 + ManTennisData** | **N2 + AO/RG files** | Ceiling |
|---|---:|---:|---:|---:|---:|---:|
| **Men, 2025–26 holdout** | 4,925 | 454 (9.2%) | 622 (12.6%) | **2,392 (48.6%)** | **2,590 (52.6%)** | 3,772 (76.6%) |
| Power, β = 0.09 | | 14% | 17% | **51%** | **54%** | 70% |
| non-Slam | 3,909 | 192 | 266 | 1,916 | 1,936 | 2,958 |
| Slam | 1,016 | 262 | 356 | 476 | 654 | 814 |
| **Women, 2025–26 holdout** | 4,778 | 272 (5.7%) | 432 (9.0%) | 432 | **575 (12.0%)** | 3,407 (71.3%) if every WTA tour match were timed |
| **Polymarket window,** men's main tour (10 Sep 2025 – 10 Sep 2026) | 2,640 | 137 (5.2%) | 212 (8.0%) | **1,467 (55.6%)** | **1,540 (58.3%)** | 2,044 (77.4%) |
| **Polymarket window,** women's main tour | 2,505 | 130 (5.2%) | 212 (8.5%) | 212 | **282 (11.3%)** | 1,775 (70.9%) if every WTA tour match were timed |

* **The research's forecasts held.** It predicted 2,390 men's holdout matches with ManTennisData; 2,392 were measured. Its women's figure with the AO and RG gaps filled was 575, exactly as measured.
* **The Slam files' gain is mostly at the Slams themselves:** 476 → 654 men's Slam matches.
  * The feature needs the previous 14 days timed, and a Slam's first round looks back at weeks of tour events.
  * So most of the distance left to the ceiling is ATP tour-level matches whose events recorded no speed (section 5).
* **Power** uses the research's method: a two-sided 5% test of β = 0.09 log-odds per SD, the 2022–24 replication's estimate and probably inflated, with the registration's standard error.
* **Men 2022–24** (8,083 matches): 3,592 held, 4,019 with files on disk, 4,127 with ManTennisData.

## 5. Limits

* **Two kinds of average.**
  * The Slam rows are means computed from points.
  * ManTennisData's are the Stats Centre's key statistic. On ATP points it runs a median 0.5–0.6 km/h above the point mean, with a long tail ([research](../../research/serve-speed-sources/README.md#1-what-the-statistic-needs-from-a-source), section 1).
  * RG's own key statistic is the rounded point mean (check 3).
  * The research's advice stands: keep ManTennisData as its own source, with its own offset, rather than mixing it with point means in one player's windows.
* **Measuring systems.**
  * The study's frozen offsets (AO +0.37, RG −2.49 km/h against the tour mean) were set on matches to 2021.
  * Check 6 finds no break where the decrypted files begin: AO 2025 reads at AO 2023's level, and RG 2025–26 follows on from 2024. It cannot see a shift smaller than about 3 km/h.
  * It does find that AO 2024, in the held Hawk-Eye copy, reads about 3 km/h fast for the same players. One offset per Slam would turn that into false speed changes for players whose windows span it.
* **Not every match or point is there.**
  * 17 played matches have no file: nine at AO 2025, eight in RG 2025's men's qualifying (section 2.2).
  * 17 of the 1,410 matches with points have fewer than 90% of their points timed, and 1.2% of all points carry no speed.
* **ManTennisData has no match dates.** Rows are placed by the tournament's start date and the round, as every other source is placed before the match clock.
  * Some event-years lack speed: Barcelona, Munich and Houston in every year, and Halle, Hamburg, Rotterdam, Dubai, Doha, Acapulco and Brisbane in 2025.
  * The 2025 speeds arrived in a backfill in autumn 2025, and later seasons arrive within about a week. A refresh is needed to keep 2026 current.
  * **Some links go to the wrong match** *(observed, 7 Oct 2026)*. 23 linked matches carry a round other than Stage 0's:
    * **15 sit on another event.** In 14 of them, the same pair met at an event that began 6 days earlier: Madrid for Rome 2022, Halle and Queen's for Mallorca 2022, Canada for Cincinnati 2022–23, Cary for Winston-Salem 2024, Washington for Canada 2025–26, and Beijing for Shanghai 2025.
      * The linker prefers a Stage 0 date 3 days before the source's, as for sources dated by the day of play, and does not compare rounds in its first pass.
      * ManTennisData's dates are tournament starts. So the event 6 days earlier scores no worse than the right one.
      * The 15th is a 2026 Cassis qualifying match that Stage 0 lacks. It went to the same pair's Rennes match a week later.
    * **5 finals sit on the same pair's round-robin match:** the ATP Finals of 2021, 2023 and 2024, and the Next Gen Finals of 2022 and 2024.
    * **3 are the same match,** under another round label: Miami 2022, Rotterdam 2023 and Madrid 2026.
  * So 20 matches (40 player rows) carry another match's speeds. A user of `speeds.parquet` should drop ManTennisData rows whose round differs from the linked match's, as the [serve-speed TabPFN panel](../serve_speed_tabpfn/README.md) does.
* **The raw Infosys folder is the only copy.** RG 2026's static files are already gone, though its API still answers. The AO host serves earlier editions only while it keeps them. No copy exists outside this PC. The same holds for the ATP's files of section 8, which the host keeps rewriting.
* **Terms.** Tennis Australia's and the FFT's sites prohibit automated extraction, and the files are encrypted to deter it. The owner's decision accepts that for these files. atptour.com's terms cover the numbers ManTennisData republishes.
* **Women outside the Slams: still nothing.** No source carries WTA tour-level speed. The vendor route in the research (section 4) is the only one.

## 6. Options from here (not decisions)

1. **Feed the new rows to the serve-speed feature.**
   * `speeds.parquet` has per player and match: the mean of first serves in, their number, second serves and the maximum, with Stage 0's match and side.
   * Each source keeps its own offset, and ManTennisData stays apart from point means.
   * Then register the speed-family test on the closed 2025–26 holdout, as the point-sequence study proposed.
2. **Refresh ManTennisData weekly:** `--commit latest`, a run of seconds. It could join the [scheduled downloads](../../decisions/2026-10-06-download-cadence.md), which would be the owner's call.
3. **Back up `data/raw/point_sources/infosys_slams/` and `infosys_atp/`** to the project's cloud bucket, as for the other only copies.
4. **Later Slam editions.** The decision covers AO 2025, RG 2025 and RG 2026. The adapter would collect AO 2027 and RG 2027 the same way if the decision were extended. AO 2026 is already held in the clear.
5. **The ATP's files of 2015 to October 2021 are on disk** (section 8). *Done on 8 Oct:* decrypted on the owner's instruction, staged and integrated ([backfill study](../infosys_atp_backfill/README.md)).
6. **Women's tour level:** only the vendors (the research's section 4 and its draft inquiry).

## 7. Method, files and reruns

* **Adapters:**
  * `src/ingest/public_dump/mantennisdata.py`: a pinned commit, files checked against the git tree, verbatim string staging.
  * `src/ingest/point_sources/infosys_slams.py`: the request plan, calibration, decryption (`key_iv`, `decrypt`) and staging. It uses the official feeds' client (`feeds.FeedClient`), which stops on any block.
  * `src/ingest/point_sources/infosys_atp.py`: the ATP's files of section 8. It fetches only: no decryption and no staging.
* **Study scripts** in `src/eda/serve_speed_acquisition/`:
  * `speeds.py`: per-player match speeds from both sources, linked to Stage 0, and checks 1–6;
  * `coverage_after.py`: the feature's coverage, reusing the research's `serve_speed_sources/coverage.py`.
* **Tests:** `test/serve_speed_acquisition/` (offline).
  * The key derivation is pinned to keys computed with the public implementation.
  * Decryption is tested by round trip and with a wrong key.
  * Also tested: the plan's match codes and rounds, the calibration rule, staging, the per-server speeds, RG's key statistics, the sides and ManTennisData's draw label.
* **Evidence:** [data/studies/serve_speed_acquisition/](../../../data/studies/serve_speed_acquisition/README.md), which also lists the reruns.
* **Environment:** `pycryptodome` was added to `environment.yml` and installed in the `tennis` environment for the AES step.
* **Nothing was bought, no account was used, and no vendor was contacted.**
* **GitHub:**
  * two read-only `gh api` calls through the owner's login (the commit list and the tree);
  * the adapter's one tree call without a token;
  * 10 file downloads from raw.githubusercontent.com, plus the public decryption code read once into the session scratchpad.
* **Other requests:** one Wayback Machine index query listed RG's match codes, and four probe requests (section 2) tested decryption before the run.

## 8. The ATP's own files of 2015 to October 2021: downloaded, not decrypted (8 Oct 2026)

**The request** (owner, 8 Oct 2026), quoting the lead of section 1:

> "Acquire this speed data and download it. DO NOT DECRYPT IT. I just want the encrypted files on my computer."

* **Authority:** the [8 October decision](../../decisions/2026-10-08-scraping-approved.md) approves the collection. Its "Clarified" section keeps these files encrypted until the owner says otherwise.
* **Nothing was decrypted.** The adapter has no decryption code, and a test checks for it. The inventory reads only each envelope's plain fields: `lastModified` and the ciphertext's length.

### 8.1 What was asked

* **Host:** `itp-atp-sls.infosys-platforms.com`, the Stats Centre host. Four static routes were asked, the ones whose contents carry serve speed *(documented in Infosys's client code and the decrypted 2021–24 copies; not seen here)*:

| Route | Path | Documented contents |
|---|---|---|
| Key statistics | `static/prod/stats-plus/<year>/<event>/<MID>/keystats.json` | Per set: Max Speed, 1st and 2nd Serve Average Speed, the box score |
| MatchBeats | `static/prod/match-beats/<year>/<event>/<MID>/data.json` | Every point, with the serve's speed |
| Rally analysis | `static/prod/rally-analysis/<year>/<event>/<MID>/data.json` | Every point by rally length, with the serve's speed and direction |
| Court Vision | `static/prod/court-vision/<year>/<event>/<MID>/data.json` | Hawk-Eye tracking per point |

* **The plan:** every ATP tour-level singles match in ManTennisData's plain 2015–21 seasons whose event began from 1 Jan 2015 to 17 Oct 2021. On 18 Oct 2021 atptour.com's pages began to show speeds.
  * That is 400 events and 18,693 match codes. Each code comes from the match's atptour.com stats link (MS001 is the final; QS codes are the qualifying).
  * **Left out:** the Slams (not on the ATP's host), the Olympics, Davis Cup and Challengers. The Hugging Face crawl had asked for every Challenger of 2015–19 and kept none.
  * **Not asked:** 750 rows without a stats link, mostly walkovers. They include the whole 2020 ATP Cup and the 2017–19 Laver Cups.
* **Order:**
  * Each event's final was asked on all four routes. Where none had it, the next match was asked on key statistics and Court Vision.
  * An event with a file was then asked match by match.
  * On a route without a file, a family (main draw or qualifying) was given up once its first 8 codes were all absent.
* **Practice:**
  * About 2 s between requests plus up to 1 s of jitter, every answer kept with a receipt, and nothing asked twice.
  * S3's 403 "AccessDenied" counted as "no such file" only on a route that had already served a file to the same headers. Four calibration files outside the window showed that each route did: the 2022 ATP Finals final and the Paris 2025 final.
* **The run** *(observed)*: 8 Oct 2026, 15:32–23:09 UTC, 9,162 requests. There was no error, refusal or challenge.
  * Claude had set a cap of 6,000 requests for each season. 2021 reached it at its last event, Indian Wells, and a rerun asked the remaining 422.

### 8.2 What the host has

*Observed. Matches are match codes with at least one file. Events asked are those with codes.*

| Season | Events with files | Matches (main / qualifying) | Key statistics | MatchBeats | Rally analysis | Court Vision |
|---|---|---|---:|---:|---:|---:|
| 2015 | 0 of 62 | 0 | 0 | 0 | 0 | 0 |
| 2016 | 0 of 62 | 0 | 0 | 0 | 0 | 0 |
| 2017 | 0 of 64 | 0 | 0 | 0 | 0 | 0 |
| 2018 | 1 of 64: the ATP Finals | 15 / 0 | 15 | 15 | 15 | 14 |
| 2019 | 2 of 63: the ATP and Next Gen Finals | 30 / 0 | 30 | 30 | 30 | 0 |
| 2020 | 4 of 29: Vienna, Paris, Sofia, the ATP Finals | 121 / 43 | 164 | 163 | 164 | 0 |
| 2021 (to 17 Oct) | 52 of 52 | 1,751 / 110 | 365 | 1,860 | 1,861 | 176 |
| **All** | **59** | **2,070** | **574** | **2,068** | **2,070** | **190** |

* **2015–2017: nothing,** at every event and on every route. The Hugging Face crawl agrees: it asked for every event of 2015–19 and kept only the 2018–19 Finals and the 2019 Next Gen Finals.
* **2018–2020: the Finals and the end of 2020 only.**
  * The 2018 Next Gen Finals have no file.
  * No 2020 event before Vienna (late October) has one. That includes Cincinnati, Rome and Hamburg after the restart.
* **2021: every event,** from Delray Beach in January.
  * MatchBeats and rally analysis cover every main-draw match.
  * Key statistics exist at 9 events: Mallorca in June (one match), then Newport, Washington, Metz, Nur-Sultan, the Laver Cup, Sofia, San Diego and Indian Wells.
  * Court Vision exists only at Washington, San Diego and Indian Wells.
  * The Hugging Face copy's 2021 tour-level matches start with that Mallorca match and Newport. The host now also serves January to June 2021.
* **The host rewrites its files** (their plain `lastModified`):
  * The 2018–20 files were written in 2026: key statistics on 6–8 Oct, MatchBeats in May–June, rally analysis in September–October.
  * The 2021 files date from March 2022 to 8 Oct 2026.
  * So this is a copy of what the host served on 8 Oct 2026. The host may change or drop files later.
* **Every file is a well-formed envelope:** base64 ciphertext that is a whole number of AES blocks.

### 8.3 What is not known

* **Whether these files carry serve speeds.**
  * Their documented contents have speed fields.
  * Many events have none: in the decrypted copies, 70 of 189 tour events of 2022–24 have no speed on any match ([research](../../research/serve-speed-sources/README.md), lane A1).
  * Only decryption would tell, and the owner has kept it off for these files.
  * **Answered later on 8 Oct 2026,** after the owner had them decrypted: the 2018 ATP Finals and Washington, San Diego and Indian Wells 2021 carry speeds (184 matches); the 2019–2020 files hold every point without a speed; 43 of the 52 events of 2021 have point files with no point ([backfill study](../infosys_atp_backfill/README.md)).
* **Why 2015–17 has nothing.**
  * The host serves no file for those years now. Whether files existed and were dropped is unknown.
  * The Wayback Machine holds no ATP Infosys file from before November 2021 (lane A1).
* **The 2020 ATP Cup and the 2017–19 Laver Cups** were not asked for, because ManTennisData gives no match codes for them. The 2020 ATP Cup was played in January, when no other event has a file *(inference)*.

### 8.4 Files and reruns

* **Raw (gitignored), the only copy:** `data/raw/point_sources/infosys_atp/<season>/<event>/<route>/<MID>.json.gz`, each envelope as served and gzipped.
  * 4,906 files, including the four calibration files: 177 MB stored, 234 MB as served.
  * `_receipts.jsonl` holds 9,162 receipts.
* **Evidence** in [data/studies/serve_speed_acquisition/](../../../data/studies/serve_speed_acquisition/README.md):
  * `infosys_atp_summary.json`;
  * `infosys_atp_events.csv`: one row per event, with its codes, outcome, and files and absences per route;
  * `infosys_atp_files.csv`: one row per file, with its bytes, SHA-256, plain `lastModified` and ciphertext length.
* **Adapter:** `src/ingest/point_sources/infosys_atp.py`.
* **Tests:** `test/serve_speed_acquisition/test_infosys_atp.py`, offline. They cover the plan from the stats links, the calibration rule, discovery and expansion against a fake host, byte-for-byte storage, and the absence of decryption code.
* **Reruns:**
  * `./python.sh -m src.ingest.point_sources.infosys_atp` asks only for what is not held.
  * `--inventory-only` rewrites the evidence without any request.

# Serve speed: how much the project holds, and where the rest could come from

**Status: research, not a decision.** Checked on 7 October 2026; every URL was accessed that day.
* **Acted on later that day:** the owner chose options 1 and 3 of section 5 ([decision](../../decisions/2026-10-07-serve-speed-acquisition.md)). ManTennisData was downloaded, and the AO and RG Infosys files were decrypted. What they hold and add is in the [serve-speed acquisition study](../../studies/serve_speed_acquisition/README.md). The rest of this page is unchanged.
* **Nothing acquired or sent:** nothing was bought, no account was opened, no vendor was contacted and nothing was decrypted.
* **ManTennisData** (section 3) was read from a scratch copy only to measure it. It is not staged in the project.

Labels: **observed** (a payload or file actually seen), **documented** (the provider's own documentation, schema or rulebook), **claimed** (marketing or sales text), **inference**, **unknown**.

**The request** (owner, 7 Oct 2026), about the men's serve-speed change:

> "a) how much of this stat do we have access to currently (what level of data completion) … b) where else can we potentially find this data to fill in the gap … paid or preferably non paid. If there are a few paid API that are popular and likely have propropierty point by point information but what they offer is opaque (may or may not have this stat), find for me how to get in contact with them or find out what they have."

**The statistic** ([point-sequence study](../../studies/point_sequence/README.md), section 5.6; [registration](../../../data/studies/point_sequence/speed_prereg.md)): a player's mean first-serve speed over his matches in the last 14 days, minus the same over the last 364 days.
* **Replication 2022–24:** +0.090 [+0.017, +0.162] log-odds per SD given the model. Positive = a player whose recent speed rose wins more often than the model says.
* **Discovery** (only 860 matches) ties, so the statistic failed its registered rule.
* **The only clean confirmation left** is the closed 2025–26 holdout.

## In short

**(a) How much the project holds** *(observed)*:
* **Men's tour level outside the Slams:**
  * 2022–24: speeds for 44–65% of matches; the gaps are whole events that recorded none;
  * 2025: January–April only;
  * nothing from May 2025;
  * nothing before late 2021.
* **Women outside the Slams: nothing, in any year.**
* **Slams:**
  * 2020–24: 73–81% of main-draw matches (Wimbledon on its show courts only);
  * Wimbledon and the US Open complete in 2025–26;
  * nothing for AO 2025, RG 2025 or RG 2026.
* **Challengers and ITF:** effectively nothing.
* **The feature** needs both players timed in the previous 14 days.
  * **Today:** it exists for 454 of the 4,925 men's main-tour matches of the 2025–26 holdout (9%). That gives about 14% power for an effect of the replication's size.
  * **With unused files already on disk:** 622 (13%).

**(b) Where the rest is:**
1. **ATP tour level from May 2025: free, public, ready** *(observed)*.
   * **What it is.** The GitHub dataset [`msolonskyi/ManTennisData`](https://github.com/msolonskyi/ManTennisData), updated every Sunday, publishes as plain CSV the per-match speeds the ATP's own Stats Centre pages show:
     * first-serve average, max and second-serve average;
     * the first serves in behind them;
     * ATP tour level from October 2021, and some Challengers.
   * **Checked.** It equals the project's decrypted Infosys copy on all 333 player-matches checked.
   * **What it adds.** The men's 2025–26 feature rises from 622 to **2,390 matches (49%; about 51% power)**. Inside the Polymarket window, men's main-tour coverage rises from 8% to **56%**.
   * **What it takes:** one download of about 32 MB.
2. **The ATP's encrypted Stats Centre files probably add little beyond it.**
   * ManTennisData reads those same files through the ATP's pages, and whole events have no speed in them: Barcelona, Munich and Houston every year; Halle, Hamburg, Rotterdam and Dubai in 2025.
   * Decryption stays the owner's decision. It would add per-point speeds, and the ceiling, if every 2025–26 match were timed, is 73%.
3. **AO 2025, RG 2025 and RG 2026 exist only in the Slams' encrypted Infosys files**, which are still served.
   * rolandgarros.com's plain API holds nulls. ESPN has no tennis statistics at all.
   * A few dozen AO 2025 matches exist in open copies.
4. **WTA outside the Slams: no free source exists** *(observed absence across the WTA API and site, Flashscore, 20 tournament sites, 14 aggregators, 7 broadcasters, GitHub, Kaggle and Hugging Face)*.
   * Before 2026 the WTA required tracking only on the centre courts of its 1000 and 500 hard and grass events. All courts are tracked only from 2026 *(documented)*.
   * Holders: the WTA and Stats Perform (official data to about 2030), the radar firm SMT, and Hawk-Eye.
5. **ATP 2015–2020: no free source.** The ATP site never showed per-match speeds before October 2021.
   * SMT claims "the most complete" serve-speed database, kept since 1989. Hawk-Eye and TDI hold the tracking.
6. **Paid: no vendor publicly sells a non-Slam serve-speed archive.**
   * The data sits with TDI (the ATP's data company), SMT/IDS, Hawk-Eye, the WTA with Stats Perform, and the Slams.
   * Contacts, questions and a draft email are in [section 4](#4-paid-vendors-who-holds-it-and-how-to-ask).
   * Matchstat's API documents per-match speed averages, but its examples fill them only at the Slams; its free tier can measure that cheaply.

## 1. What the statistic needs from a source

* **A box-score number is enough** *(inference, from the definition)*.
  * Per match and player, the feature uses the mean speed of first serves in, weighted by how many there were.
  * A match-level "average 1st serve speed", with the first serves in from the box score, gives the same number.
  * Point-by-point data is not required.
* **"Fastest serve" is not a substitute.** It is a maximum, and much noisier.
* **One measuring system per player, or a known offset.**
  * Systems read at different levels. The study froze these offsets from the tour mean on matches to 2021 (men, km/h; positive = reads faster): Infosys tour events +5.34, Wimbledon +3.13, AO +0.37, US Open −1.21, RG −2.49.
  * A 2-week window from one system against a 52-week window from another creates a false change.
* **Three agreement checks made here** *(observed)*:
  * **Flashscore republishes the official Slam numbers.**
    * On 182 matches that both Flashscore and the Wimbledon or US Open feeds time, the match mean differs by −0.18 km/h (Flashscore slower). Each player's average differs by a median of 0.27 km/h (90th percentile 0.61): integer rounding.
    * Against Infosys, 12 of 14 matches agree within about 1 km/h. Two Next Gen Finals 2024 matches are Flashscore errors, one with averages of 125 and 110 km/h.
    * Most 2024 records print "0 km/h" for both players where nothing was measured; lane A1 caught this. Every count here treats values outside 40–270 km/h as missing.
  * **ManTennisData equals Infosys's own key statistics.** All 333 player-matches checked match. It sits a median 0.57 km/h above the mean of first serves in computed from points (lane B).
  * **Infosys's key statistic runs faster than its points.**
    * On 4,853 ATP matches, "1st Serve Average Speed" is 2.18 km/h faster on average than the mean of the timed first serves in. The median absolute gap is 0.67 km/h and the 90th percentile 4.0, so a few large gaps drive the mean.
    * Lane B's signed median for the same comparison is +0.5–0.6 km/h.
    * So key-statistic averages, and ManTennisData, which copies them, are best kept as their own source rather than mixed with point-based means in one player's windows.

## 2. How much the project holds (part a)

`src/eda/serve_speed_sources/coverage.py` measures it; nothing it reads is a match result.

**"Held"** is what the study used: the shot-level study's per-match speeds (`stage1_match_stats.parquet`), from five sources:
* the decrypted ATP Stats Centre copy on Hugging Face (Infosys; ATP 2021–24);
* the SirGenkii fork (ATP, January–April 2025);
* Sackmann's Slam files (to 2024);
* the Wimbledon and US Open feeds;
* the Hawk-Eye copies of AO and RG.

**"With files on disk"** adds three sources the project already holds but the study never read:
* **Infosys key statistics.** Match averages for 1,133 matches of 2021–24 whose points fail the study's half-timed gate.
* **The Australian Open match centre's per-set averages.** 483 matches: AO 2026 and some Wayback captures.
* **Flashscore's "Average 1st serve speed".** The handoff's Flashscore crawl has 1,012 matches with real readings: 17 of 2024, 602 of 2025 and 393 of 2026 to 17 April. 392 of them are linked and not already held. The crawl reached matches through head-to-head pages, so it is a lower bound on what Flashscore serves.

### 2.1 Matches with both players' first serves timed

*Observed.* Share of all matches in the project's match table (Stage 0); held → with files on disk. 2026 runs to events starting 30 September.

| Men | 2015–17 | 2018–19 | 2020–21 | 2022–24 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| Slam main draw | 64–68% | 48–54% | 74–81% | 74–77% | 50% → 56% | 50% → 75% |
| Slam qualifying | 0 | 0 | 0 | 8–10% | 34% → 45% | 49% → 74% |
| Tour main draw (250, 500, 1000, Finals) | 0 | 0 | 0 / 4% → 10% | 44–65% → 53–77% | 11% → 16% | **0** |
| Tour qualifying | 0 | 0 | 0 / 3% → 5% | 24–58% → 28–77% | 14% | 0 |
| Challenger | 0 | 0 | 0 | 0–1% | 0 | 0 |
| ITF | 0 | 0 | 0 | 0 | 0 | 0 |

| Women | 2015–17 | 2018–19 | 2020–21 | 2022–24 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| Slam main draw | 49–68% | 50–56% | 75–81% | 73–76% | 50% → 78% | 50% → 75% |
| Slam qualifying | 0 | 0 | 0 | 8–10% | 34% → 43% | 0 → 100% (AO only in the table) |
| Tour main draw | **0** | **0** | **0** | **0** | **0** | **0** |
| WTA 125 | 0 | 0 | 0 | 0 | 0 | 0 |
| ITF | 0 | 0 | 0 | 0 | 0 | 0 |

Full tables: [coverage_matches.csv](../../../data/studies/serve_speed_sources/coverage_matches.csv) (tour × level × year) and [coverage_slam_editions.csv](../../../data/studies/serve_speed_sources/coverage_slam_editions.csv).

### 2.2 The feature itself, on the main-tour main draws

**Why it is rarer than timed matches.** The feature exists for a match only when **both** players have a timed match in the previous 14 days. A Slam first round, for example, needs the week before to be timed.

**The frame** is the match table's main-tour main draws. It stands in for the model's frame of matches with closing odds, which the script does not open beyond 2024. On the study's own frame for 2015–24, the held column reproduces `speed_build.py`'s counts exactly in all eight tour × window × Slam cells.

| | Frame | Held | With files on disk |
|---|---:|---:|---:|
| **Men, 2015–21**, non-Slam | 13,525 | 181 (1.3%) | 267 (2.0%) |
| Slam | 3,429 | 853 (25%) | 853 (25%) |
| **Men, 2022–24**, non-Slam | 6,559 | 2,809 (43%) | 3,189 (49%) |
| Slam | 1,524 | 783 (51%) | 830 (54%) |
| **Men, 2025–26**, non-Slam | 3,909 | 192 (4.9%) | 266 (6.8%) |
| Slam | 1,016 | 262 (26%) | 356 (35%) |
| **Women, 2025–26**, non-Slam | 3,762 | 19 (0.5%) | 46 (1.2%) |
| Slam | 1,016 | 253 (25%) | 386 (38%) |

* **The men's 2025–26 holdout:** 454 matches today (9%). Power is about 14% for the replication-sized effect, close to the study's own "about 15%".
* **How the power is computed** *(inference)*:
  * β = 0.09 per SD, which is probably inflated;
  * a two-sided 5% test;
  * the registration's standard error, 1/√(n × 0.19 × 1.06).
* By year: [coverage_feature_by_year.csv](../../../data/studies/serve_speed_sources/coverage_feature_by_year.csv). Per match: `coverage_feature_matches.parquet` (gitignored).

### 2.3 Why the gaps are where they are

* **Men's tour level after April 2025.** The decrypted copies the project holds stop there: the Hugging Face handoff at 2024, the SirGenkii fork at April 2025.
* **Men's tour level in 2022–24: whole events without speed, not outside courts** *(observed)*.
  * 70 of the 189 tour-level events have Infosys records but no speed on any match. They are mostly clay events and smaller 250s, plus some 500s and grass events: Barcelona every year, Hamburg 2022–23, Halle 2024, Munich, Estoril, Houston, Buenos Aires, Rio, Santiago, Marrakech, Bastad, Gstaad, Kitzbühel, Umag, Geneva, Lyon, Stuttgart, 's-Hertogenbosch and others.
  * Inside the other events, speed is present on 92–99% of matches on every court number.
  * *Lane A1's reading (inference, partly search):*
    * the Stats Centre takes speed only from Hawk-Eye installations;
    * clay events had no electronic line calling before 2025;
    * several events used FoxTenn rather than Hawk-Eye.
  * So these events are probably unfillable from any public source.
* **Men's tour level before late 2021.** The ATP's site and the Infosys files show no per-match speed before the Stats Centre pages of October 2021; the Wayback Machine holds no ATP Infosys file before November 2021 (lane A1).
* **Women's tour level.** No women's source on disk has a speed field:
  * the WTA API (box scores, 222 advanced-statistics paths, point-by-point);
  * SofaScore, TennisLive and the Match Charting Project;
  * Flashscore's crawl, whose few 2024 WTA "speeds" are "0 km/h" placeholders.
* **Slams.**
  * **None for AO 2025, RG 2025 or RG 2026.** AO and RG moved to encrypted Infosys feeds in 2022, and the AO match centre serves only the current edition.
  * **Wimbledon 2019–24:** speed only on the six show courts (Centre, No.1, No.2, No.3, 12, 18), at 100%. The other courts and qualifying have none: never measured (lane A2). Electronic line calling covered every court from 2025.
  * **RG 2022:** no speed on Courts 4, 5 or 8–12. RG's own API agrees.
  * **US Open qualifying 2022–24:** only about 80 matches a year have full data.
* **Holes in Sackmann's Slam files** *(observed)*:
  * **RG 2018 is recoverable now.** Its speeds sit in `Speed_MPH` only, with the serve number filled (lane A2).
  * **AO 2014 and all four Slams of 2012–13** carry speeds but no first- or second-serve marker, so first serves cannot be separated. RG 2019 has no speeds in the file; the Hawk-Eye copy covers part of it.
  * **Wimbledon 2016 women's points** are missing from the archive.
* **Challengers.** Infosys Challenger points are 0.9% timed. The 2026 ATP Rulebook only *authorises* electronic review at Challengers *(documented)*; a few events use Bolt6 or FoxTenn.

### 2.4 Against Polymarket

*Observed:* Polymarket's own tier buckets in its event index, for the audit's window of 10 Sep 2025 – 10 Sep 2026: 40,507 events and $3.48 billion of listed volume.

| Tier (main draw and qualifying) | Share of volume | Can carry serve speed? |
|---|---:|---|
| ATP tour level and Slams | 42% | Yes, where measured |
| WTA tour level and Slams | 26% | Yes, where measured; nothing public outside the Slams |
| Challenger and WTA 125 | 24% | Rarely |
| ITF | 4% | No |
| Doubles, juniors, team events, props | 4% | Not applicable |

**Inside that window the feature exists today for 5% of the men's and 5% of the women's main-tour main-draw matches.**
* Men: 137 of 2,640; 212 with the files on disk.
* Women: 130 of 2,505; 212 with the files on disk.
* What each new source would add is in section 3.3.

## 3. Where else the data could come from (part b)

### 3.1 By gap

| Gap | Best free route | Paid, or ask | Probably unfillable |
|---|---|---|---|
| **1. ATP tour level, May 2025 on** | **ManTennisData** (public CSV, weekly): 58% of 2025 and 68% of 2026 tour-level main-draw matches | TDI; the ATP's encrypted files mostly duplicate ManTennisData | Events whose Stats Centre has no speed: Barcelona, Munich and Houston every year, and Halle, Hamburg, Rotterdam, Dubai, Doha, Acapulco and Brisbane in 2025. Probably no Hawk-Eye there |
| **2. WTA tour level, any year** | **None** | The WTA and WTA Ventures, Stats Perform (official data, about 2021–30), SMT (radar), Hawk-Eye | 2022–25 courts without tracking: the WTA required electronic line calling only on centre courts of 1000 and 500 hard and grass events. All courts only from 2026 |
| **3. AO 2025, RG 2025, RG 2026** | **None plain.** The Slams' encrypted Infosys files are still served: the owner's decryption decision. Scraps: 26 + 7 AO 2025 men's matches in open copies; 14 in the held SirGenkii fork. The files on disk (Flashscore's crawl, Wayback captures) time 2 men's and 34 women's AO 2025 main-draw matches, and 27 men's and 111 women's RG 2025 | Tennis Australia, Bolt6, SMT (AO); the FFT, via rolandgarros.com or Sportradar (RG) | RG outer courts |
| **4. ATP tour level, 2015–20** | **None.** The ATP site never showed per-match speed before October 2021 | SMT ("the most complete" database, from 1989); Hawk-Eye; TDI (Hawk-Eye at Masters and Finals from 2017, select 500/250 events from 2019) | Events without Hawk-Eye or a recorded radar |
| **5. Challenger, WTA 125** | ManTennisData: 438 Challenger main-draw matches of 2026 (7%), mostly from 16 events | TDI; Bolt6 | Most events: no tracking |

### 3.2 The free sources in detail

**1. `msolonskyi/ManTennisData`: the main find** (lane B; [notes](../../../data/studies/serve_speed_sources/research_notes/B_open_datasets.md), section F1).
* **What it is** *(observed)*:
  * GitHub, created June 2021, MIT label on the repository, head `4e2d39f99e` (4 Oct 2026), a commit every Sunday.
  * Its collector (`msolonskyi/tennisAnalyzer`) opens atptour.com Stats Centre pages in Chrome and stores the numbers the ATP's own page script shows. The ATP's script does the decrypting in the browser; the repository's owner decrypts nothing.
* **Fields, per match and player:**
  * "Max Speed", "1st Serve Average Speed" and "2nd Serve Average Speed" (km/h);
  * first serves in and the rest of the box score;
  * ATP player codes, tournament id and round (no match date; a join to Stage 0 or Tennis My Life supplies it).
* **Coverage, matches with a speed** (lane B's count; rows include qualifying):

  | Year | Masters 1000 | 250, 500, Finals | Challenger | Slams |
  |---|---|---|---|---|
  | 2014–20 | 0 | 0 | 0 | 0 |
  | 2021 (from October) | 74 / 707 | 169 / 2,167 | 0 | 0 |
  | 2022 | 585 / 718 | 878 / 2,353 | 83 / 8,895 | 0 |
  | 2023 | 910 / 959 | 914 / 2,137 | 47 / 9,484 | 0 |
  | 2024 | 922 / 959 | 1,495 / 2,179 | 47 / 10,053 | 0 |
  | 2025 | 954 / 1,049 | 730 / 1,980 | 45 / 10,508 | 0 |
  | 2026 (to Beijing/Tokyo) | 811 / 842 | 841 / 1,641 | 690 / 9,629 | 0 |

* **Linked here** *(observed)*:
  * 9,837 of its 10,055 matches timed for both players link to Stage 0 (98%), by the shot-level linker: names, tournament start date, round.
  * With it, the match table's tour-level main draws are timed for **58% of 2025 and 68% of 2026 matches**, and qualifying for 51% and 62%.
* **Caveats** *(observed)*:
  * no Slams;
  * 31 values below 120 km/h to drop;
  * the 2025 speeds arrived in a backfill in autumn 2025, while 2026 speeds appear within a week;
  * some event-year gaps may be the scraper's rather than the ATP's (lane B's reading).
* **Rights:** the numbers are the ATP's; atptour.com's terms forbid systematic retrieval. The owner's [decision of 25 September](../../decisions/2026-09-25-atp-pipeline-handoff.md) accepted third-party copies of this kind.

**2. Files already on disk, not yet used** (section 2):
* Infosys key statistics (1,133 matches, with the +2.2 km/h offset);
* AO 2026 per-set averages (483);
* Flashscore's crawl (392, plausibility-filtered).

Lane A2 found three more:
* RG 2018's mph speeds;
* 14 AO 2025 men's first-round matches with per-point speeds in the held SirGenkii fork;
* about 30 US Open 2025 qualifying matches whose match statistics have averages that their points lack.

**3. Flashscore's live site** (lane A1).
* **What it carries** *(observed)*:
  * Per-match first- and second-serve averages on the Slams.
  * Off the Slams, only on some matches: of 16 non-Slam matches of May–October 2026 sampled, the field appeared only on the Madrid and Rome finals, not on Rome's round of 32.
* **Access:**
  * The desktop feed is signed (401 without its header, which was not sent).
  * The mobile site shows the same statistics as plain HTML, but its robots.txt disallows `/match/`.
* **Verdict:** a supplement for the Slams, not a tour source.

**4. The encrypted official files** (the owner's decision; lanes A1 and A2):
* **ATP Stats Centre (Infosys), 2021–26** *(documented in Infosys's own page code; 2026 files observed)*.
  * It holds per-point speed and per-match averages.
  * Beyond ManTennisData it would add per-point speeds (the within-match speed fade the study proposed), and the matches the pages failed to render.
  * It would probably not add whole events. The 2026 rulebook approves FoxTenn and FlightScope as well as Hawk-Eye, and the Stats Centre appears to carry speed only from Hawk-Eye installations (lane A1's inference).
* **AO and RG match centres (Infosys), 2022–26.** Still served for AO 2025 (the final checked), RG 2025 and RG 2026. The Wayback Machine holds encrypted copies of only 13 RG 2025 main-draw and 58 qualifying matches, and 10 of RG 2026.
* **The LTA's match centre** for Queen's and Eastbourne 2026, men and women.
  * Its code defines fastest, first- and second-serve averages, but every reply is encrypted.
  * Both WTA finals came back exactly 18,372 bytes, which hints that the payload holds no speed *(inference)*.
* **Public decryption code exists:** `nipunagarwalla/courtside`, `hawkilol/TennisCC` and the earlier infotennis scrapers (lane B). It was not used.

**5. Checked and empty** *(observed, unless stated)*:
* **ESPN:** no tennis statistics at any level; 0 of 6,508 listed matches, and its statistics endpoint answers 404.
* **rolandgarros.com's plain match API:** the speed fields are null for 2023–26, and the 2019 and 2022 averages read 0–6.
* **Official sites and apps:** atptour.com's plain JSON, the ATP app gateway, the WTA API and site, ProTennisLive.
* **Tournament sites:** about 20.
* **Aggregators** (14): including SofaScore, Tennis Explorer, 365Scores, AiScore and LiveScore.
* **Broadcasters** (7): including Tennis TV, Sky and Eurosport (TNT's statistics, which load from a GraphQL API, were not determined).
* **Datasets:** Kaggle, Hugging Face, Zenodo, Figshare, Dataverse and OSF.
* **Partial copies:** `serve-and-volley` (a 2021–22 subset of ManTennisData); `henrynye/M4R` and `KacWNK` (26 and 7 AO 2025 men's matches).

### 3.3 What each source adds

*Observed counts; the last two rows are hypothetical upper bounds.* Cumulative, top to bottom.

| | Men 2025–26 holdout (4,925 matches) | Power, β = 0.09 | Polymarket window, men's main tour (2,640) |
|---|---:|---:|---:|
| Held | 454 (9%) | 14% | 137 (5%) |
| + files on disk | 622 (13%) | 17% | 212 (8%) |
| **+ ManTennisData** | **2,390 (49%)** | **51%** | **1,466 (56%)** |
| + every ATP tour match of 2025–26 timed (the ceiling for the encrypted files) | 3,592 (73%) | 68% | 1,970 (75%) |
| + AO 2025, RG 2025–26 in full | 3,772 (77%) | 70% | 2,044 (77%) |

* **Women's 2025–26 holdout** (4,778 matches): held 272 (6%); with files on disk 432 (9%); with the AO and RG gaps filled 575 (12%). Only if every WTA tour match were timed would it reach 3,407 (71%). No source for that is known.
* **The men's 2022–24 window** (8,083 matches): 3,592 held, 4,019 with the files on disk, 4,124 with ManTennisData.

## 4. Paid vendors: who holds it, and how to ask

**No vendor publicly documents a non-Slam serve-speed archive for sale** (lane C; [notes](../../../data/studies/serve_speed_sources/research_notes/C_paid_vendors.md)). The speeds sit with three kinds of holder:
* the bodies that own the events: the ATP through TDI, the WTA, the Slams;
* the firms that measure them: Hawk-Eye, SMT/IDS, and historically FlightScope/EDH and FoxTenn;
* their distributors: Sportradar for the ATP, Stats Perform for the WTA.

Every route is a custom licence or a question. The vendors are ordered by how likely they are to hold non-Slam history:

| Vendor | What it holds, and the evidence | Contact | Ask first |
|---|---|---|---|
| **TDI** (Tennis Data Innovations, ATP and ATP Media's data company) | **Very probably every ATP Tour serve speed.** Tracking on every court from 2025; Hawk-Eye events before that. Sportradar's overlays show serve speed from "the deep data collected via TDI from all ATP events" *(third-party)*. Its "Tennis Data Platform" claims an archive and a sandbox *(claimed)*. No speed field documented | `contact@tennisdata.com`; the form at [tennisdata.com](https://www.tennisdata.com/). Named: Jonathon Thorpe (Head of Commercial), Anthony Taylor (Head of Product) | Is per-serve speed in the official ATP data or the platform's archive, from which year, and in per-match summaries? Sandbox eligibility? Research licence terms? |
| **SMT** (SportsMEDIA Technology) and its radar unit **IDS** | **Radar speeds at "40+ ATP/WTA Tour events" and all four Slams** *(third-party, Aug 2025)*. Serve-speed systems for the tours since 1989 *(claimed)*. "The most complete data belongs to SportsMEDIA Technology" *(claimed, 2020)*. Its platform stores "historical ATP and WTA Tour data … serve speeds" *(claimed)*. All 16 AO courts in 2024 *(third-party)*. **The best lead for the women and for ATP 2015–20** | Form at [smt.com/contact-us](https://smt.com/contact-us/) ("General Inquiry"). Named: Stephen Kemper (Sr Business Development Manager). +1 919-493-9390 (search excerpt) | Per-serve records or maxima only? Which events and years from 2015? AO 2025, RG 2025–26? Can SMT license them, or which rights holder must authorise it? |
| **Hawk-Eye** (Sony) | Per-serve speed wherever installed *(inference)*. Mostly a processor for the event organisers, but it says it retains data "indefinitely in order to maintain a historically accurate record" *(claimed)* | `hello@hawkeyeinnovations.com`; +44 (0)1256 268494. Named: Michael Markovich (CCO, Sony's sports businesses) | Direct licensing, or only with the rights holder's consent? Which ATP and WTA events had Hawk-Eye speed in each year? |
| **WTA / WTA Ventures** | The rights holder. No speed in its public API *(observed)*. Electronic line calling on every court only from 2026 *(documented)* | `feedback@wtatennis.com`; +1 727 895 5000 (from a 2019 page) | Does the WTA hold serve speed for its 250/500/1000 events, by year? Who licenses it? |
| **Stats Perform** (the WTA's official data supplier, 2021 to about 2030) | No speed field documented. Its own Q&A bot "do[es]n't have enough detail … to confirm" | [statsperform.com/contact](https://www.statsperform.com/contact/) (blocks automated reading; open it in a browser) | Does the WTA umpire feed or the Opta shot feed carry serve speed? Does a work order allow model training? |
| **Sportradar** (TDI's distributor) | **No speed field** in Tennis API v3, Live Data or the DDE statistics. Speed appears only in the former IMG ARENA live Slam tracking stream *(documented)* | `sales@sportradar.com`; [sportradar.com/contact-us](https://sportradar.com/contact-us/) | Does any product deliver serve speed as data? Is the DDE rally-summary history (for example RG 2025–26) kept? |
| **Matchstat / Tennis-API.com** | Per-match `averageFirstServeSpeed`, `averageSecondServeSpeed` and `fastestServe` in its schema *(documented)*. Its examples fill them only for Slam matches; they are null for Indian Wells 2024–26, Monte-Carlo 2026, RG 2026 and the 2025 ATP Finals *(observed)* | `api@tennis-api.com`; RapidAPI listing, free BASIC tier, then $29–99 a month | Fill rate by tour, tier and year; source; average over first serves in? A free-tier check would settle it |
| **Tennis Australia / Bolt6** (AO 2025) | Bolt6 line calling on every AO court from 2025; SMT radar *(claimed)* | Tennis Australia +61 3 9914 4000 (search excerpt); Cedric Cornelis (CCO). `sales@bolt6.ai` | Can AO 2025 per-serve speeds be licensed for research, and through whom? |
| **FFT** (RG 2025–26) | Infosys MatchBeats speeds *(search excerpt)* | No data contact found; via rolandgarros.com or Sportradar | Can the RG 2025–26 MatchBeats speeds be licensed? |
| **Golden Set Analytics** | Claims "the largest data set on tour … trajectory" data; selected clients only | `info@goldensetanalytics.com` | Do you license the data itself, and from what source? |

**Others checked:**
* *Holders of AO data, speed not stated:* TennisViz (form only), Infront Bettor and Catalist. Catalist alone openly allows prediction-market trading.
* *No serve-speed field or claim:* STATSCORE, Enetpulse, LSports, Live Tennis API, api-tennis.com's documentation, Data Sports Group, Goalserve, BetsAPI.
  * **Data Sports Group,** whose method page was highlighted when the request was made: its `get_matches` has `wind_speed` but no serve speed *(observed)*.
  * **api-tennis.com is an exception to its own documentation:** a third party's January 2025 copy shows "Average 1st Serve Speed" in its statistics *(observed, lane B)*. Worth one trial question.

**Licences** (where they could be read; lane C):
* **Sportradar** needs written consent for prediction-market use, has an AI-training clause and requires data to be destroyed at the end.
* **Stats Perform's** standard terms bar model training, archive building and betting.
* **TDI's** results site bars use for models or betting.
* **Catalist** is the only distributor seen that openly allows prediction-market trading.

**Draft inquiry** (lane C's text; not sent):

> **Subject:** Serve-speed data: coverage, sample and licence terms
>
> Hello,
>
> I run a small independent research project that models professional tennis matches. I am looking for serve-speed data, above all first-serve speed.
>
> Could you tell me:
> 1. Whether you offer serve speed per point, or a per-match average for each player (ideally the average speed of first serves in, with the number of serves it covers)?
> 2. For which tours, tiers and years (ATP 250/500/1000, WTA, Challenger, Grand Slams), and how far back your archive goes?
> 3. Whether you can share a sample payload, and which delivery formats you offer?
> 4. The price of a small, non-commercial research licence?
> 5. Whether the licence allows training statistical models on the data, and using the resulting forecasts for my own betting or prediction-market positions?
>
> If another party holds the rights, I would be grateful for a pointer to the right contact.
>
> Kind regards,
> [Name]

Two choices are the owner's:
* **Question 5's second half** is there so the request does not describe a betting use as purely "non-commercial research". Keep it or drop it.
* **Per-vendor lines** ("Specifically: …", one per vendor) are in lane C's notes, section 5.

**Suggested order:** TDI, then SMT, then Hawk-Eye, then the WTA and Stats Perform for the women. The Matchstat free tier first, if a cheap check is wanted.

## 5. What could be done first (options, not decisions)

1. **Download ManTennisData** (about 32 MB, pinned at `4e2d39f99e`) and re-pull it weekly. It is the single largest gain:
   * the men's 2025–26 feature from 13% to 49% of matches;
   * power from about 17% to about 51%;
   * the Polymarket window from 8% to 56%.

   Keep it as its own source, not mixed with point-based means: its averages sit a median 0.6 km/h above them. Drop values below 120 km/h.
2. **Fold in what is already on disk:**
   * Infosys key statistics, as their own source, like ManTennisData;
   * AO 2026 per-set averages;
   * Flashscore's crawl (plausibility-filtered);
   * RG 2018's mph speeds;
   * the 14 SirGenkii AO 2025 matches.
3. **The owner's decision on decryption,** now narrower:
   * the AO and RG Infosys files are the only route to AO 2025, RG 2025 and RG 2026;
   * the ATP files mostly duplicate ManTennisData, but add per-point speeds.
4. **For the women and for ATP 2015–20, there is no route but asking or paying.** Send the inquiry to SMT, the WTA with Stats Perform, Hawk-Eye and TDI. Women's tour speed is plausibly complete only from 2026, when every court is tracked.
5. **Then register the speed-family test** (14-day change, within-match fade, box-score serve form) on the chosen sources for the closed 2025–26 holdout, as the point-sequence study suggested.

## 6. Method, evidence and limits

* **Local measurement** (this session):
  * `src/eda/serve_speed_sources/coverage.py` (`--mantd` for the ManTennisData scenario) and `flashscore_crawl.py`;
  * tests in `test/serve_speed_sources/` (7, offline);
  * outputs in [data/studies/serve_speed_sources/](../../../data/studies/serve_speed_sources/README.md).
* **Research lanes,** run in parallel on 7 Oct 2026. Notes are in [research_notes/](../../../data/studies/serve_speed_sources/research_notes/), each with its own probe log:
  * **A1, tour-level public sources:** 96 requests of its own, plus two helpers' requests; about 330 logged in all.
  * **A2, Slams and ESPN:** 126 requests, at most 22 per host.
  * **B, open datasets:** GitHub through the owner's logged-in CLI, read-only; Kaggle, Hugging Face and research archives.
  * **C, paid vendors:** 61 requests, 20 page summaries, 49 searches.
* **Disclosures.**
  * **Flashscore's mobile site.** Lane A1 read 23 Flashscore mobile match pages as a bounded measurement. Their robots.txt disallows `/match/`, and the lane read that file only after its first two page loads.
  * **Encrypted files** were requested only to confirm they exist and to read their top-level keys.
  * **Stats Perform's Q&A bot** answered three questions. No email address was given to it.
* **Limits.**
  * **The frame** is a proxy for the model's frame with closing odds.
  * **Linking** is by names: ManTennisData links 98%; Flashscore uses the match-timing study's links.
  * **The ATP and Slam rows of section 3.3** are upper bounds.
  * **Vendor holdings** are claims or inferences until a vendor answers.
  * **Matchstat's fill rate** comes from its published examples only.
* **Earlier research this builds on:**
  * [granular data leads](../granular-data-leads/README.md) (24 Sep);
  * [gap sources](../gap-sources/README.md) (29 Sep);
  * the [official point feeds](../../studies/official_point_feeds/README.md);
  * the [Hugging Face handoff](../../studies/atp_pipeline_handoff/README.md).

  Those passes compared per-point width in general; this one asks only about speed. It supersedes the point-sequence study's statement that 2025–26 non-Slam speeds "exist only in ATP's encrypted Stats Centre files".

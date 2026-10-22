# Duplicate sources: are we using the most accurate one, and can they be combined?

16 October 2026 · Written for the owner · Research evidence and proposed repairs. **Nothing here has been applied:** every table the model reads is unchanged. Adopting any of it is the owner's call; §8 gives my recommendation for each item.

> **Updated 22 October 2026:** the owner approved the repairs. They are in the decided tables now and reach the model's training at the next retrain; see [Applied on 22 October 2026](#applied-on-22-october-2026) at the end and the [decision](../../decisions/2026-10-22-source-reconciliation-repairs.md).

**The owner's request** (16 Oct 2026): "For a lot of our data, we have multiple sources, some of those sources differ. We currently have sources that supply our main model and other sources are frozen out that duplicate in function. Do an analysis on where we have duplicate data THAT CAN POTENTIALLY DIFFER, see if we are using the most accurate source on average, and see if some sort of average or blend (or fixing corrupt data) can be built that uses a combination of these sources."

**How to read it.**
* *Observed* = computed here, with its file; *inferred* = reasoning; *suggestion* = not decided.
* "Stage 0" is the project's match table: every match the model learns from, with each player's nine box-score counts. It takes Sackmann's files where they exist (to 25 May 2026), Tennis My Life's (TML's) after, plus the decided repairs. "The model's copy" means Stage 0's values.
* Agreement is the share of player rows where two sources give the same number. **Higher is better.**
* Odds accuracy is in milli-log-loss per match (mLL). **Lower log loss is better; a negative difference means the candidate is more accurate.** "Better" or "worse" means the 95% interval clears 0; otherwise "unresolved", with P(better).
* The study's [process log](process_log.md) records how each number was reached, every bug and change of plan, and the subagents' briefs ([verbatim](subagent_briefs.md)).

## The answer in short

**Where the duplicates are.** Almost everything the model reads exists in two or more copies on disk (§1). The ones that can differ, and matter: box scores (they feed about 41 of the 57 inputs), results and scores, each match's context (surface, indoor, level, round, dates, seeds), birth dates, the closing odds, and the serve speeds.

**Are we using the most accurate source on average? Yes, for nearly everything.**
* **Box scores.** Each count was checked against the tours' own point-by-point records, recounted point by point.
  * At the ATP the model's copy agrees with them on 99.9–100% of every count.
  * At the WTA it agrees on 99.7–99.9% of aces, double faults, serve points, service games and break points, 99.1% of the points won behind each serve, and 98.7% of first serves in.
  * That is as good as the tours' own published boxes. Switching to those wholesale would not help; the third-party copies (SofaScore, the volunteer charts) count first serves differently and would be worse.
* **Results, context and ages.**
  * Winners almost never differ (2 matches).
  * The model's indoor rule is right on every event where its two sources disagree.
  * No age in the model's matches is a quarter-year off.
* **Two places where it is not the most accurate:**
  * the **odds stand-in** for the training rows since August 2025 that have no Pinnacle close (BetOnline alone);
  * the **ATP's published serve-speed average**, more than 5 km/h off its own point data in about 6% of matches.

**Can a combination do better? Yes, in four places, though not by averaging box scores.**
1. **Odds stand-in: blend three sharp prices.** The equal average, in log-odds, of BetOnline, the Betfair exchange and Polymarket's price 30 minutes before the start is more accurate than BetOnline alone on those rows: **−1.79 mLL [−2.75, −0.82], better** (4,340 matches; re-derived by me).
2. **Serve speed: trust the point data when the published average disagrees with it.** Taking the point mean when the published average is more than 5 km/h off repairs 576 history rows.
3. **Box scores: a majority of independent records, not an average.** Counts are facts, and mixing sources inside a match makes ratios no source recorded. A vote finds corrupt rows:
   * **122 Grand Slam matches with the two players' service-game counts swapped** (Australian Open and US Open 2016–17, Wimbledon 2016–17 and 2024, Roland Garros 2016): the fault the 9 Oct decision fixed at the Australian Open and Roland Garros, whose check started at 2019. Every independent check sides with the point record.
   * **74 matches where the tour's own box and its own point record agree with each other and not with ours** (46 of them truncated or copied boxes that do not fit the match score), plus 20 TML rows that fit the same pattern (19 women's rows of 2026 and one men's 2015 qualifying match; *corrected 22 Oct 2026*: an earlier version called all 20 women's 2026 rows. By 22 Oct, TML's own corrections had fixed the 19 women's rows; see the status note at the end).
4. **Context: the official record over a copy.** 15 events have the wrong tournament level in Stage 0 (11 of them, 319 model matches, in the model's frame); WTA Paris 2013–14 is filed as carpet instead of hard; 8 matches in the frame are filed as completed but were retirements.

**What it is worth to the model.** Each repair touches well under 1% of the rows behind any input. The model comparison can see effects only to about ±0.05–0.35 mLL, so it cannot measure these, and the odds stand-in lies entirely outside its seasons. Under the adoption framework these are **repairs: decided on the data evidence, with a model run only as a harm check.** I recommend bundling them into one candidate build (§8).

**Faults found in shared code** (§9). Two earlier findings were reader faults: the WTA's "short records" and "service games" (the 6 Oct data-continuity study), and SofaScore's "fewer break points from 2025", which is a defect in SofaScore's own match totals. None of the flagged faults reaches the data the model trains on today; I checked each against the accepted lower-level packages.

## 1. Where the duplicates are

| Data | Read by the model for | The model's source | Other copies on disk (sections below) | Verdict |
|---|---|---|---|---|
| **Box scores** (nine serve counts per player) | about 41 inputs: two-week form (16), the surface profile (21), points aggregates, serve/return ratings, hold rates | Stage 0: Sackmann, then TML; the Slams' own records for Wimbledon and the US Open 2026 and Roland Garros 2022–26; the 8 Oct corrections; accepted lower-level packages in the build's own tables | the WTA's box, its umpire log and point-by-point (2019–26); the ATP's key statistics in four copies (2018–26), its point files (2018–25), TDI (2026), ManTennisData (2015–26), the atptour.com scrape (1991–2024); the Slams' point files (2011–24); SofaScore, TennisLive, Flashscore, the Match Charting Project | The model's copy is the most accurate on average; 196 corrupt matches found (§2) |
| **Results and scores** (winner, set scores, completed/retired/walkover) | every label; Elo, games Elo; sets played in 14 days | Stage 0 | tennis-data, TennisLive's listings, Flashscore, api-tennis, the WTA's website records, SofaScore, the official feeds, ITF live data (14 sources; 743,623 of Stage 0's 873,681 matches have another, 67,006 of the model's 67,226 have two or more independent ones) | The model's copy right in nearly every disagreement; a few dozen corrupt rows (§3.1) |
| **Surface, indoor, level, round, best-of** | context inputs; the surface Elo offset and surface profile; the level layer | Stage 0 (Sackmann's codes refined by TML's); indoor: Stage 0's flag then tennis-data's Court (men), the WTA calendar then Court (women) | tennis-data, the WTA's editions and website, TennisLive, Flashscore, SofaScore | Indoor right everywhere; 15 level and 1 surface error (§3.2) |
| **Match dates and times** | the leak-proof clock; form windows; rest (the five-pattern stage) | the clock, built from about 13 timing sources | the same sources, compared with each other | Agree; 77 source dates fall outside the clock's window (§3.3) |
| **Seeds** | the five-pattern stage | Stage 0 | the WTA API, the Slam feeds, TDI, Infosys, SofaScore, TennisLive | Differ on at most 0.24% (§3.3) |
| **Birth dates** | age, age² | Sackmann's player files (via Stage 0) | TML, the WTA's player pages, the Live Tennis API, Tennis Abstract | No model row off by a quarter-year (§4) |
| **Closing odds** | the odds input | Pinnacle's close; BetOnline's last line where Pinnacle has none (August 2025 on); the books' average where neither prices a match | tennis-data's books (Bet365, the average and maximum, Betfair, its "Pinnacle" column), OddsTrader's ~60 books, Polymarket | Pinnacle is best where it exists (earlier study); for the stand-in rows a three-price blend beats BetOnline (§5) |
| **Serve speed** | the serve-speed stage (men) | one value per player-match: the point mean where held, else the ATP's published average | the ATP's average in four copies, its point files, the Slam feeds, the Hawk-Eye copy | The point mean is better where the two disagree (§6) |

*Dependent copies, not counted as independent evidence:* Open Tennis Data (built from tennis-data and Sackmann); TML's rows for the years Sackmann covers (they copy his values and his typos); the atptour.com scrape (the same ATP numbers Sackmann's files carry).

## 2. Box scores

### 2.1 How the referee works

Most copies descend from the same official scoring: the chair umpire's device feeds the tour's system, and Sackmann, TML, ManTennisData and the atptour.com scrape all copied the tour's published numbers. Two copies agreeing proves little. What settles a disagreement is **the tour's own point-by-point record of the same match, recounted point by point:**
* the WTA's umpire event log (2019–26);
* the ATP's point files: the Hugging Face copy (2021–24), the decrypted backfill (2018–21), the Challengers (2021–24), SirGenkii's copy (2025);
* TDI's points (2026);
* the Slams' point files in Sackmann's archive (2011–24).

A recount counts only where it holds every point and its set scores equal the match's.

Two checks need no referee, because a correct box score must fit its own match score:
* a player's games equal her holds, plus the opponent's breaks, plus tiebreaks won;
* the two service-game counts must follow the serving order the score implies (a tiebreak takes a serving turn but is not a service game).

**One limit on the WTA referee:** the subagent who recounted the umpire log chose its first-serve rule after seeing which version matched the WTA's box best. On first serves in and the points won behind each serve, the log is therefore not a blind referee of the WTA's box. Aces, double faults, serve points, service games and break points were not tuned.

### 2.2 Are we using the most accurate copy? Yes

**Against the tours' own point records** (observed; exact agreement, % of player rows; higher is better; [all tables](../../../data/studies/source_reconciliation/box/report_tables.md)):

| Referee | Rows | The model's copy | The tour's published box | Third parties |
|---|---:|---|---|---|
| WTA umpire log, 2019–26 | 49,080 | 99.65–99.92 on aces, double faults, serve points, service games, break points; 99.07–99.15 points won behind each serve; 98.65 first serves in | the same (99.67–99.88; 99.13–99.19; 98.72) | SofaScore 61–98; Match Charting Project 84–99.8 |
| ATP point files, 2021–24 | 55,010 | **99.88–100** on every count | the same (key statistics, ManTennisData, atptour.com) | SofaScore 89–99; Match Charting Project 83–99 |
| ATP Challengers, 2021–24 | 4,282 | 99.67–100 | the same | TennisLive 99.7–100 where it has the count |
| TDI points, 2026 | 7,052 | 99.60–99.97; the first-serve split 96.5–97.9 | ManTennisData the same (97.1 on first serves) | — |

* **The model's copy is as accurate as the tours' own published boxes.** Switching to them wholesale would not help: where they disagree, each is the odd one out about as often (next table).
* **TML's raw rows are worse on women's aces and double faults** (91% and 84%): its known fault of December 2024 – February 2026. Stage 0 is not affected, because Sackmann's rows cover those months.
* **TDI's first-serve split** disagrees with both our copy and ManTennisData by about 3%: TDI's serve labels, not our data.
* **Third parties count differently.** SofaScore and the volunteer charts disagree mostly on first serves in; SofaScore's set sums put men's Slam first serves 5 points higher, second serves booked as first. They are no stand-in for the official counts.
* **After the splice the WTA's own box is slightly ahead.** In 2025 and 2026 (Sackmann's last months, then TML's rows) the WTA's box agrees with its umpire log a little better than our copy does: in 2026, first serves in 99.8% against 98.9%, serve points 99.9% against 99.3%.

**Three-way votes** (observed). For every count: the model's copy, the tour's published box and the tour's point record. When exactly one differs, the other two outvote it (% of player rows; lower is better for the model's copy):

| | The model's copy is the odd one out | The tour's box | The point record |
|---|---|---|---|
| WTA, 49,080 rows | 0.06–0.23% per count | 0.09–0.15% | 0.01–1.12% (the 1.12 is first serves in) |
| ATP 2021–24, 55,010 rows | **0.00–0.02%** | 0.00% | 0.00–0.10% |
| ATP Challengers 2021–24, 4,280 rows | 0.00–0.02% | 0.07–0.14% | 0.00–0.30% |
| ATP 2015–24 with no point record (two scrapes of the ATP's pages), 176,566 rows | 0.00–0.01% | — | — |

Where the point record is the odd one out, it is mostly how it logs a let or a re-served fault, or a one-point gap that no record on disk can settle.

### 2.3 Fixing corrupt rows: a majority of independent records, not an average

**S1: Slam service games exchanged, 122 matches** (observed).
* **Where:** the Australian Open 2016–17, the US Open 2016–17, Wimbledon 2016–17 and 2024, and Roland Garros 2016.
* **The fault:** the model's two service-game counts are exactly the point record's exchanged. It is the "winner served first" fault the [9 Oct decision](../../decisions/2026-10-09-roland-garros-box-scores.md) corrected at the Australian Open (2019–26) and Roland Garros (2013–21). That decision's check found Wimbledon and the US Open clean, but it looked from 2019.
* **The evidence:**
  * every one has a complete point record whose set scores equal the match's;
  * its break points, aces and double faults equal the model's for both players (all 244 player rows), and its serve points in 242, so the point record's servers are right;
  * the model's box fails the games identity now and passes both identities once exchanged;
  * the 7 that volunteers charted side with the point record (4 complete charts).
* **The fix:** the decided action (exchange the two counts), written in the decided table's format.
* **Reach:** 619 training matches have a player with one of these matches in the previous 28 days.

**O1: the tour's whole box, 74 matches + 20** (observed).
* **The rule:** the tour's published box and its point record agree with each other on every count, and the model's copy differs.
  * WTA 58 (2021–26) and ATP 10 (2022–24) rest on a point record.
  * ATP 6 (2015–24) rest on two separate scrapes of the ATP's pages.
* **46 are plainly broken** in the model's copy: truncated or copied boxes that do not fit the score. For example, Monterrey 2021, 6-3 6-2: 7 and 7 service games for a 17-game match, and serve points 38 and 53 against the WTA's 51 and 65. Stage 0's checks caught the service games and blanked them, but kept the other, short counts.
* **28 differ by a point or two** and fit the score either way: small revisions, kept in the class but flagged.
* **3 differ only on the first-serve split**, where the WTA referee is not blind (§2.1), and Stage 0's box fits the score: flagged, and I recommend leaving them out.
* **Left out on purpose:** 26 matches that differed only by one service game at a retirement. The WTA's box counts the game in progress, Sackmann's rows mostly do: a convention, not corruption.
* **The fix:** the tour's whole box, with the action of the [8 Oct Adelaide repair](../../decisions/2026-10-08-corrupt-data-fixes.md) (F3). Every replacement holds all nine counts and fits the score.
* **20 more are TML rows:** 19 women's rows of 2026, where the model reads TML live, and one men's 2015 qualifying match that only TML holds. They belong to the open question of the source order after the splice (§8). *(Corrected 22 Oct 2026: an earlier version called all 20 women's 2026 rows.)*
* **Reach:** 120 training and 131 test matches within 28 days.

**Smaller, for review only.** 101 Slam matches have break points that differ from the point record while the service games agree. The model's box fails the games identity in 48 of them, and the point record's passes in most. Only 12 could take the point record's whole box, and fixing break points alone would mix sources. Listed, not proposed.

### 2.4 Blank boxes another source could fill

Not an accuracy question, but found on the way (observed):
* about 2,660 men's qualifying matches (2,116 of them 2015–18) and 309 Challengers have no box in Stage 0 while ManTennisData holds one;
* 151 WTA tour-level matches have one in the WTA's own box.

The qualifying and Challenger ones are lower-level data, so they would enter by the [gap-fill policy of 14 Oct](../../decisions/2026-10-14-lower-level-gap-fills.md). Its first condition asks that the source's whole box equal Stage 0's on at least 98% of the matches both hold. ManTennisData's does on 99.2% of tour-level qualifying, 99.5% of Challengers and 99.6% of Challenger qualifying. The second condition (that a fill closes a hole) is per season, and that policy's own check reads it.

## 3. Results, scores and the context of each match

### 3.1 Results and scores

From the [results report](../../../data/studies/source_reconciliation/context/REPORT.md); observed. 14 result sources were compared, and a disagreement is settled by an official record other than the source's own, else by the majority of the other independent sources.

* **When one source disagrees with Stage 0, Stage 0 is nearly always right.**
  * Winners differ in 185 links: Stage 0 right in 127, the source in 8.
  * Short scores: in 2,498 of 2,506, Stage 0 is right (the source stops early).
* **Contradicted by two or more independent sources:**
  * **2 winners**, both lower level: the Columbus 125 2021 final and the W35 Timaru 2025 final, where Sackmann's row swaps winner and loser;
  * **121 game scores and 137 statuses**, mostly in Sackmann's 2025–26 ITF rows (11 and 12 in the model's frame);
  * **15 matches Stage 0 calls "completed" that every source calls retirements** (8 in the frame: Guadalajara 2022 SF, Madrid and Berlin 2023 among them).
* **Not errors:** 1,214 of 1,310 unmarked retirements really are retirements whose RET marker is missing, and Stage 0 already infers them.

### 3.2 Surface, indoor and level

**Indoor (observed).** The model's indoor input is right on all 31 events where its two sources disagree (644 matches of the frame).
* **Men:** Stage 0's flag beats tennis-data's Court on all 10 (São Paulo 2016–17 and Santiago 2020–26 are outdoor).
* **Women:** the WTA's calendar beats Court on all 21 (Stuttgart 2010–17 was indoor clay at the Porsche Arena; Zhuhai 2015–19 and Dubai 2016 were outdoor).
* **So the calendar-first order for women, recommended on 9 Oct and awaiting your confirmation, is the more accurate one.**

**Level (observed).** On 61 main-tour events where sources disagree, Stage 0's level is wrong on 15:

| Event | Stage 0 | Right | Frame matches | Evidence |
|---|---|---|---:|---|
| Valencia 2014 / Vienna 2014 | 250 / 500 | 500 / 250 | 29 / 27 | they swapped tiers in 2015 (general knowledge) |
| WTA Zhuhai 2015 (Elite Trophy) | 500 | season finale | 15 | the WTA's record |
| WTA Brisbane, Moscow, Sydney 2017 | 250 | 500 | 84 | the WTA's record |
| WTA Moscow, Osaka 2019 | 250 | 500 | 54 | the WTA's record |
| WTA Guadalajara 2023 | 500 | 1000 | 54 | the WTA's record |
| WTA Strasbourg 2024 | 250 | 500 | 27 | the WTA's record |
| WTA Cleveland 2025 | 500 | 250 | 29 | the WTA's record |
| WTA Bol 2016–17, Zhengzhou 2017, Limoges 2019 | 250 | WTA 125 | 0 | the WTA's record |

*Inferred:* Stage 0's wrong levels follow TML's 250/500 codes, which Stage 0 uses to refine Sackmann's ambiguous ones.

**Surface (observed).** In the model's frame only WTA Paris 2013–14 is affected (54 matches): Stage 0 says carpet, while the WTA, tennis-data and Flashscore say hard. Outside the frame, 222 lower-level events differ, mostly carpet against hard at Challengers and ITF events.

**Round, best-of, draw size:** Stage 0 is right wherever they disagree. The differences are labels and conventions (Sackmann rounds a draw up to its bracket).

### 3.3 Dates, the clock and seeds

* **Match dates agree.** Most sources are more than a day off the others in at most 0.06% of matches.
* **The leak-proof clock** (each match's earliest start and latest finish) contains every source's date except **77 counted links**:
  * 52 fall before the earliest start, for example rain-delayed Wimbledon 2023 first-round matches whose first point was on 3–4 July against a window starting 5 July;
  * 25 fall after the latest finish.
  * *Inferred:* a date before the window means a match's inputs may be read after it started; a date after it means its result may count before it ended. Both are leak risks, small in number. They are for the match-timing study to check with its probe.
* **Seeds** differ on at most 0.24% of player rows where both sides give one.

## 4. Birth dates

Observed:
* **In the model's frame (134,452 player rows), no age is 0.25 years or more off** the majority of sources, or off Sackmann's file.
* Three frame players have dates that sources dispute: Yue Yuan, Alina Korneeva and Mate Delic. For the first two, Sackmann's date is the more credible (*inferred*).
* **Outside the frame,** 929 player rows (35 players, almost all women's ITF) carry an age 0.25 years or more off the majority. They are identity collisions: a young player filed under an older namesake's id (Ekaterina Kuznetsova's rows are 21 years off).

## 5. Closing odds where Pinnacle is missing

**The background.**
* The model's odds input is Pinnacle's closing price with the margin removed ([decision of 9 Oct](../../decisions/2026-10-09-pinnacle-first-odds-input.md)). Live, it is fed Pinnacle's current line.
* Pinnacle's close was recorded only to early September 2025. Since then the training rows carry BetOnline's last line as a stand-in, or the books' average where BetOnline has none: 5,281 rows of the latest model build, 4,340 of them played before 29 July 2026.
* The [odds-sources study](../odds_sources/README.md) settled the rest: where Pinnacle's close exists, Pinnacle alone is the most accurate price, and no blend of books beats it.

**What we hold for those rows** (observed, the 4,340 before 29 July):
* coverage: BetOnline 94%, the Betfair exchange 94%, Polymarket 30 minutes before the start 92%, Bet365 99%, the books' average 100%, OddsTrader's other books 97%;
* tennis-data's "Pinnacle" column covers only 21%. After July 2025 it is not Pinnacle's close (*inferred:* Pinnacle's price some hours earlier); it trails Pinnacle's own close by 3.05 mLL [0.06, 6.05] where both exist.

**Accuracy against results** (observed; lower log loss is better; **a negative difference means the candidate is more accurate than today's stand-in**):

| Stand-in for the missing Pinnacle close | Difference from today's (BetOnline) | Verdict |
|---|---|---|
| **Equal log-odds average of BetOnline, Betfair and Polymarket** (whichever price the match) | **−1.79 [−2.75, −0.82]** | **better** |
| BetOnline + Polymarket | −1.62 [−2.78, −0.46] | better |
| BetOnline + Betfair | −0.67 [−1.33, −0.01] | better |
| any single other price (Betfair, Polymarket, Bet365, the average, OddsTrader's median, Bet105) | −0.4 to −0.9 | unresolved (P(better) 0.66–0.95) |
| a "Pinnacle proxy" fitted where Pinnacle is known | −1.12 | unresolved (P 0.94) |

* **Re-derived by me** from the three member prices, with my own four-week blocks: −1.79 [−3.01, −0.57]; better in 12 of 12 blocks. The stand-in it is compared with equals the model's actual odds input on all 5,281 rows.
* It survives a correction for the 31 comparisons the subagent read. Recalibrating each price first leaves −1.46 [−2.30, −0.62]: the gain is information, not calibration.
* By slice: women −2.89 (better), men −0.74 (unresolved, P(better) 0.89); 2026 −2.09 (better), August–December 2025 −0.68.
* Polymarket carries most of it.

**What it means** (*inferred*). The three-price average is the more accurate stand-in for the Pinnacle close that was never recorded, so the training rows from August 2025 on would look more like what the model is fed live.
* **No new live feed is needed:** Betfair's closes are in tennis-data's files, and Polymarket's prices are on disk (the sharp benchmark's table, last refreshed 5 Oct; it needs refreshing as rows are added).
* **Two limits:**
  * "more accurate against results" is not proven "closer to Pinnacle": Polymarket's prices never overlap Pinnacle's close;
  * the decided model comparison (2020–2024) cannot see a change confined to rows from August 2025.

## 6. Serve speed

**The background.** The serve-speed stage reads each man's first-serve average per match from a history that holds one value per player-match: the mean of the timed first serves in the match's point record where one is held, else the ATP's published average (its "key statistic"), mostly through ManTennisData's copy of the ATP's Stats Centre pages.

**What was found** (observed; [speed report](../../../data/studies/source_reconciliation/speed/REPORT.md)):
* **At the Slams every source agrees** with the point mean to about 1 km/h.
* **At tour level the four copies of the ATP's published average are one number** (ManTennisData equals the Hugging Face copy on 11,782 of 11,783 player-matches).
* **That number is more than 5 km/h off the same match's point mean in about 6% of player-matches,** and more than 10 km/h off in about 1.5%. The cause is a corrupt set-level average that the match value inherits: Eubanks at Indian Wells 2021 reads 360 km/h in set 1, giving 257 for the match against 200 from his points.
* **Where the two disagree, the point mean is nearer the player's own norm** (his other matches within 91 days): 74% of the time for gaps of 5–10 km/h, 93% above 20.

**A combination that beats the current choice.**
* Take the point mean whenever the published average is more than 5 km/h off it, where a complete point record exists. That repairs **576 history rows** (559 of them ManTennisData's), with a median correction of 7 km/h.
* A median of the sources is worse: with two sources it halves an error instead of removing it.
* The 8 Oct audit's validity filters (an average at or above the maximum, and so on) catch few errors: 43% precision, 12% recall.

**How far it moves the model's speed input** (observed with the project's own code, which reproduces the current input exactly). The 28-day speed form moves by a full unit (about 0.9 points of win probability in an even match) in **29 of 7,070 men's matches of 2024–26** and 33 of 11,594 in 2019–23; by half a unit in 163 and 222. Today's live inputs are unaffected, since every changed row is older than the 364-day window. The repair changes the history the stage's coefficients are fitted on.

**What cannot be fixed this way:** about 10,200 rows, 7,099 of them from 2025–26, hold only the published average, with no point record to check it against. At the measured rate about 600 of them are more than 5 km/h off. Live rows are the same: the daily collector holds the published average only, so the live input keeps that tail while the history would be cleaner.

**Re-checked by me** with separate code on the subagent's files: 576 rows changed, the same movement counts (29 and 33), and 5.8% of published averages more than 5 km/h off on a slightly wider filter.

## 7. What it would mean for the model

* **The size** (observed):
  * the box repairs touch about 200 matches among 870,000;
  * the level fix, 319 frame matches;
  * the speed repair, 576 history rows;
  * the odds stand-in, about 4,300 training rows from August 2025.
* **What the comparison can see.** The decided model comparison resolves about ±0.05 mLL for a change of this kind, and about ±0.35 across an odds change. A repair of this size is expected far below that (*inferred* from the adoption framework's resolution check). The odds stand-in lies entirely outside its 2020–2024 seasons.
* **So none of this can be shown to improve the model's log loss,** and none was model-tested. The [adoption framework](../adoption_framework/README.md) classifies these as **repairs**:
  * they are adopted on the data evidence;
  * the model run serves only as a harm check (default harm: worse by more than 0.10 mLL with the whole interval below 0);
  * they earn no edge credit.
* **What keeping the status quo forgoes:**
  * correct service games in the hold-based inputs of about 600 training matches;
  * correct boxes behind about 250 matches' two-week form;
  * the right tournament level for 319 matches;
  * the cleaner speed history behind the speed coefficients;
  * a training odds input closer to the live one for the last 14 months.

## 8. Recommendations and decisions for the owner

| # | Item | Kind | My recommendation | What it takes |
|---|---|---|---|---|
| 1 | **S1**: exchange the service games of the 122 Slam matches back | repair | **Adopt.** The same fault and fix as the 9 Oct decision, at editions its check did not reach; every independent check sides with it | The decided table's action; the table is written (`box/slam_svgms_candidates.csv`). If you want the 8 Oct standard, three reviewers confirm it first (I can run them) |
| 2 | **O1**: the tour's whole box for 74 matches | repair | **Adopt the 71; leave out the 3 that differ only on the first-serve split.** There the referee was tuned to the box, and Stage 0's own box fits the score, so the evidence is one record against one | The decided `replace_box` action; table written (`box/official_candidates.csv`, column `x_split_only`) |
| 3 | **The 20 TML rows of 2026** and the open source order after the splice | repair / source order | **Take the WTA's own box where its box and its umpire log agree against TML.** For 2025–26 the WTA's box is the more accurate copy | Your decision on the data-continuity study's § 4.5 for WTA tour events |
| 4 | **Levels** (15 events) and **WTA Paris 2013–14's surface** | repair | **Adopt** | A small extension of Stage 0's builder: its hand-made level rules match an event by name and code, not by year, so a per-event correction table (like the date corrections of 14 Oct) is needed |
| 5 | **Statuses**: the 8 frame matches filed as completed that were retirements | repair | **Adopt**; take the lower-level ones (2 winners, 113 scores and statuses) by the candidate route | A row-correction table |
| 6 | **Women's indoor order: the WTA's calendar first** | confirmation | **Confirm.** It is right on all 21 disagreeing events | Your word |
| 7 | **Speed: the point mean when the published average is > 5 km/h off** (576 rows) | repair | **Adopt**, as the 130 impossible records were on 8 Oct (into the live feed's corrected history); the daily engine then refits the speed coefficients | A rebuilt corrected history (the alternative is already built: `speed/histories/ks_within5.parquet`) |
| 8 | **Odds: the three-price stand-in** for training rows without a Pinnacle close | repair of training rows | **Adopt as a candidate build**, the live input unchanged | The odds input's construction gains the rule; Polymarket's table refreshed at build time |
| 9 | **ManTennisData's ~2,100 qualifying boxes** (and 309 Challengers) | expansion by policy | **Run them through the 14 Oct gap-fill policy**, whose checks decide | A package build by that policy's route |
| 10 | **Bundle 1, 2, 4, 5, 7 and 8 into one candidate build** with the default harm check | — | **Yes.** One harm check for one batch of repairs, as the framework's "policies, not instances" asks | `run_chain.py --setup --candidate`, the fits, `compare.py` (GPU; after tonight's template build) |
| 11 | **Fix the shared-code faults in §9** | maintenance | **Yes**, in their owners' modules | Small edits, each with its test |

**Not recommended:** averaging box counts; a median of speed sources; the audit's speed filters; the "Pinnacle proxy" (it leans on the books' maximum, which stopped tracking Pinnacle in August 2025); switching wholesale to the tours' published boxes; SofaScore's match totals as a box source (read its set sums if it is ever used).

## 9. Faults found in shared code and data

Reported by the subagents and checked by me where they could touch the model. Not fixed (other modules), and none reaches today's training data.

| Fault | Where | Effect found | Reaches the model's data? |
|---|---|---|---|
| Reads the WTA's empty Slam boxes (rows of zeros) and its Slam "service games played" (really games won) as counts | `src/eda/data_continuity/sources.py`, `wta_api()` | The data-continuity study's "short WTA records of 2024–25" and "9% of 2026 service games differ" are artifacts | No (a study reader) |
| Reads SofaScore's match totals, which are wrong in Dec 2024 – Aug 2025 and Feb – Jun 2026 (break points faced match its own points in 39–82% of rows, against 98–100% otherwise; its set sums are right) | `data_continuity/sources.py`, `sofascore()`; `candidate_stage0.py`'s SofaScore loader | The data-continuity study's "SofaScore records fewer break points from 2025" is this defect | No: SofaScore is not a box source of any accepted package (checked) |
| Assigns the server point by point and gets 2.3% wrong (rally files file some double faults under the receiver) | `src/eda/shot_level/points.py`, `infosys` | Point means of 90 speed-history rows | Only those 90 rows (the repair in item 7 does not depend on them) |
| Links the 2018 ATP Finals final to the same pair's round-robin match | a shot-level link | One speed row | One row |
| Keeps WTA-website scores from the listing's side | `candidate_stage0.py`, `load_wta_site` | 2,368 linked comparison rows | No: none of the feed's 49,001 added matches has a reversed score (checked) |
| Takes TennisLive's `winner_id` at retirements, where it names the retiring player | `candidate_stage0.py`'s side-swap rule | 85 matches | No: all 417 accepted TennisLive completions are on the right player by name (checked) |
| Misses second-serve foot faults as double faults (2019–21) | `official_point_feeds/verify_wta.py` | 190 double faults | No |
| The TML–Sackmann pairs file is stale for TML's Challenger files | `data/studies/data_continuity/tml_vs_sackmann_pairs.parquet` | 28,145 pairs point at other rows | No (a study output) |

## 10. What this does not show

* **No model reading.** Every verdict here is about data accuracy. The repairs' effect on log loss is below what the comparison can see (§7), and the odds stand-in has not been model-tested.
* **Agreement among copies is not truth.** The official point record is the best referee on disk, but it comes from the same scoring system as the published box; where both are wrong together, nothing here can tell. The volunteer charts are the only fully independent record, and they cover few matches.
* **The WTA referee was tuned on the first-serve split** (§2.1). The ATP's point files have explicit servers in the backfill and Challengers; in the Hugging Face copy the server is derived (the rule reproduces the explicit server on 99.99% of 477,034 points).
* **Before 2019 there is no official point record for most tour matches,** except the Slams and a few ATP events. Sackmann's 2013–18 rows can be checked only against copies of the same ATP numbers and partial third parties; the training seasons' boxes are therefore the least checked.
* **Judgments from general knowledge:** the venues behind the indoor verdicts and the two men's level verdicts were not checked online (no network was allowed). The indoor ones agree with the indoor study's web-checked venues where they overlap.
* **The odds blend's slices** for men (−0.74) and for August–December 2025 (−0.68) are unresolved; the overall gain is resolved. These are archived closes, not fills.
* **The helpers' classification choices** for results (which disagreements count as conventions) were made after seeing the disagreement listings, never outcomes; the raw classes are kept so the counts can be redone.

## 11. Files and reproduction

| Part | Code (`src/eda/source_reconciliation/`) | Outputs (`data/studies/source_reconciliation/`) |
|---|---|---|
| Frozen inputs | `snapshot.py`, `common.py` | `_snapshot/` (Stage 0, the link files, the data map's table; `manifest.json` with SHA-256) |
| Box readers | `lead_raw.py`, `lead_slam_pbp.py`, `wta_*.py`, `atp_*.py`, `tp_*.py` | `box/readers/<reader>.parquet` and `.json` (27 readers) |
| Box comparison | `box_engine.py`, `box_votes.py`, `box_fill.py`, `exposure.py`, `report_tables.py` | `box/engine_*.csv`, `votes*.csv`, `fill_*`, `report_tables.md` |
| Box corrections | `lead_slam_corrections.py`, `lead_official_corrections.py` | `box/slam_svgms_candidates.csv/.json`, `slam_bp_review.csv`, `official_candidates*.csv/.json` |
| Results, context, birth dates | `ctx_*.py` | `context/` (`REPORT.md` and its tables) |
| Odds | `odds_*.py`, `lead_check_odds.py` | `odds/` (`REPORT.md`, `scores_tables.md`, `lead_check.json`) |
| Speed | `spd_*.py`, `lead_check_speed.py` | `speed/` (`REPORT.md`, `t1_*`–`t3_*`, `lead_check.json`) |
| The subagents' reports | — | `box/REPORT_wta.md`, `REPORT_atp.md`, `REPORT_third.md`, `context/REPORT.md`, `odds/REPORT.md`, `speed/REPORT.md` |
| Tests | `test/source_reconciliation/test_lead.py` (5) | — |

Run from the repository root in Git Bash (all CPU; no GPU, no network, nothing written outside the study's folders):

```
./python.sh src/eda/source_reconciliation/snapshot.py          # once; --force replaces the snapshot
./python.sh src/eda/source_reconciliation/lead_raw.py           # ~1 min
./python.sh src/eda/source_reconciliation/lead_slam_pbp.py      # ~5 min
# the subagents' readers, in the orders their reports give (wta_*, atp_*, tp_*: ~20, 20 and 8 min)
./python.sh src/eda/source_reconciliation/box_engine.py         # ~6 min
./python.sh src/eda/source_reconciliation/box_votes.py
./python.sh src/eda/source_reconciliation/lead_slam_corrections.py
./python.sh src/eda/source_reconciliation/lead_official_corrections.py
./python.sh src/eda/source_reconciliation/box_fill.py
PYTHONIOENCODING=utf-8 ./python.sh src/eda/source_reconciliation/report_tables.py
# context: ctx_selflink, ctx_tml, ctx_results --stage all, ctx_context --part all, ctx_dob, ctx_summary (~20 min)
# odds: odds_coverage, odds_psx, odds_proxy, odds_score, odds_checks, odds_summary; then lead_check_odds.py
# speed: spd_build --fresh, spd_checks, spd_agree, spd_consensus, spd_spdl; then lead_check_speed.py
./python.sh -m pytest test/source_reconciliation -q -p no:cacheprovider
```

## Status on 22 October 2026

The owner asked whether the findings were still to be dealt with, since the model was retrained on 21 Oct. Checked the same day (read-only) in today's shared tables (rebuilt 21 Oct) and in the live model's own build (`template_2026-10-21b`, live since 21 Oct):

| Finding | Still present? |
|---|---|
| 122 Slam matches with service games exchanged | **Yes, all 122** |
| 74 whole boxes the tours' own records contradict | **Yes, all 74** |
| The 20 TML rows | **19 fixed** by TML's own women's corrections, accepted 21 Oct; the men's 2015 qualifying row is still wrong |
| 15 events at the wrong level | **Yes, all 15** |
| WTA Paris 2013–14 filed as carpet | **Yes** |
| 8 frame matches filed as completed, retirements by every source | **Yes, all 8** |
| 576 serve-speed history rows with a corrupt published average | **Yes, all 576** (the history files are unchanged since 8 Oct) |
| The odds stand-in where Pinnacle is missing | The live model still uses BetOnline from August 2025. The 21 Oct amendment brings TennisExplorer's Pinnacle closes from November 2025 at the next retrain; August–October 2025 stay on BetOnline |

The retrain did not deal with them because none was adopted: this study proposed them, and a retrain rebuilds the tables from the sources with the decided corrections only.

## Applied on 22 October 2026

The owner approved the repairs the same day ([decision](../../decisions/2026-10-22-source-reconciliation-repairs.md)).

**What was done** (observed; records in `data/studies/source_reconciliation/applied/`):
* **Into the decided tables** (`data/studies/input_data_audit/fixes/`), each repair first re-checked against today's raw rows (`apply_repairs.py`):
  * S1, 122 Slam service-game exchanges;
  * O1, 71 whole boxes (the 3 split-only rows left out);
  * the 8 frame statuses (a new action that adds the missing retirement marker);
  * 15 editions' levels and WTA Paris 2010–14's surface, in a new per-edition table (`event_corrections.csv`) that Stage 0's builder now applies.
* **The builder change** is the per-edition table. *A correction to § 8 item 4:* Paris is corrected for 2010–14, not only 2013–14. The same fault and the same three sources hold for all five editions; only 2013–14 have training rows.
* **The dry run:**
  * Stage 0 built twice from today's dump: **exactly the 1,166 matches the repairs name changed**, and nothing else did.
  * After the repairs, every repaired match reads its corrected value.
  * The history check allows the template.
* **The speed history** (`apply_speed.py`):
  * The 576 rows are repaired in a new layer of the live history, with stage 2's column rebuilt on it. The old history still reproduces today's column exactly, and the repaired column equals this study's.
  * Today's speed form moves for 0 of 1,101 players.
  * Its own harm check (the retrain's harm check cannot see a speed-history change): 2020–2024, both tours, both stages, **+0.008 [−0.026, +0.042] mLL per match (positive = the repair better), unresolved, P(better) 0.68: no harm.**
* *A correction to the status reply of 22 Oct:* the speed repair could go in at once. The model in use reads its own copy of the speed history, written by its retrain, so the live stage 2 does not refit. The repair reaches stage 2 through the next retrain's copy.

**When it reaches the model.**
* Prediction runs build their own match table from the decided tables, so they read the repairs from their next run.
* Training takes them at the next retrain, after the shared tables are rebuilt (B6).
* The retrain cannot miss them: they are listed in `data/studies/current_best_model/pending_at_retrain.json`, the retrain's plan refuses to start until the shared tables hold them, and the retrain script checks the built model before fitting.

**Found and fixed on the way:**
* Tennis My Life's women's file of 22 Oct made every match-table build stop at the player-id alias check. The check now accepts an alias the source itself has made redundant.
* Replays of a model now read the correction tables it was built with, so its proof stays exact.

**Not applied:**
* the 20th TML row (lower-level; the source-order question);
* the lower-level winners, scores and statuses (the candidate route);
* the S2 review list;
* the odds blend;
* ManTennisData's qualifying boxes;
* the women's indoor order (still awaiting the owner's confirmation).

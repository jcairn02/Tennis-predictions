# Match timing: when each round is played, how late it runs, and where match days can be found

**Status: research, not a decision.** Checked on 5 October 2026; every URL was accessed that day. Most of the 872,704 matches in the project's table carry only Sackmann's `tourney_date` and a round. This page gives the rules for an earliest-start and latest-finish window per match. The windows are in **[data/studies/match_timing/schedule_rules.csv](../../../data/studies/match_timing/schedule_rules.csv)** (455 rows, each with a source URL and notes; the last three, for the 2021 Australian Open qualifying, were added later on 5 October by the [match-timing study](../../studies/match_timing/README.md)). The timeline files already in that folder belong to separate work and were not touched.

Labels: **observed** (a fetched primary page, or the project's own data), **secondary** (Wikipedia and similar), **provider claim**, **inference**, **unknown**.

## Reading the windows

* **Anchor.** Offsets count days from Sackmann's `tourney_date` moved to the nearest Monday (Tue −1, Wed −2, Thu −3, Fri +3, Sat +2, Sun +1).
  * *Why* [observed]: 97.0% of the 872,704 rows are Monday-dated, but not all. Sackmann's dictionary says "usually the Monday of the tournament week" [provider claim]. In 2010–15 he dated Indian Wells, Miami and five Masters at their main-draw start (Thu, Wed or Sun). In 2025–26 he did the same for the 12-day events (Wed, Sun or Thu).
  * *Effect* [observed]: every 12-day event lands on the Monday of its first week in every era; for example, Madrid 2023–24 (Monday-dated) and 2025–26 (Wednesday-dated) align.
* **Exceptions.**
  * Davis Cup and Fed/BJK Cup ties are dated tie by tie; their rows count from Sackmann's own date.
  * The 2023–26 BJK Cup Finals, Play-offs and Qualifiers have their own rows.
  * ATP London 2012 Olympics is dated Wednesday 25 July, but play began Saturday 28 July: add 7.
* **Columns.** Offsets are local days at the venue.
  * `earliest_day_offset`: the first day a match of the round can start.
  * `latest_day_offset`: the last day one was, or by rule may be, still in progress, including the 2010–26 slips found.
  * `typical_day_offset`: the usual day.
* **Which row applies.** Named event rows beat pattern rows. Tour-level qualifying is `TQ`; Slam qualifying is `GSQ`.
* **Within an event, the draw already orders a player's own rounds** [inference]. The windows matter for other players' and other events' results.

## 1. The standard schedules

| Level | Standard days (offsets) | Changes 2010–26 | Basis |
|---|---|---|---|
| Grand Slams | Two days per round in week 1; R16 Sun–Mon (6–7); QF Tue–Wed; SF W Thu (10), M Fri (11); F W Sat (12), M Sun (13) | **Sunday start:** RG always (since 2006), AO from 2024, US Open from 2025 (R128 from −1). **Wimbledon:** Middle Sunday rest to 2021 (play in 2016 only), R16 on Monday (7); play scheduled from 2022. **US Open 2010–14:** men a day later; men's final Monday (weather 2010–12, scheduled 2013–14); women's final Sunday 2011–12 | secondary (Wikipedia day-by-day pages), checked against observed tennis-data days and Flashscore start/end times |
| Slam qualifying | 4–5 days, week before | **AO:** Wed–Sat (2015–18), Tue–Fri (2019–20), Doha (men) and Dubai (women) 10–13 January 2021 (Q1 10–11, Q2 12, Q3 13; secondary, checked later on 5 October; recorded in the data as their own events dated 10 January), Mon–Thu (2022–26). **RG:** Mon–Fri (2018–25). **Wimbledon:** Mon–Thu. **US Open:** Tue–Fri to 2023, Mon–Thu from 2024, none in 2020 | secondary; per-round split inference |
| 12-day 1000s (96 draw) | Q Mon–Tue (0–1), R1 Wed–Thu (2–3), F Sunday (13); WTA Miami, Madrid and Rome F Saturday (12) | IW and Miami throughout (IW men R1 Thu–Fri to 2022); Madrid, Rome and Shanghai from 2023; WTA Beijing from 2024. Canada 2025–26 Sun–Thu (F 10); Cincinnati 2025 Thu–Mon (F 14) | observed (ATP/WTA previews, tennis-data) |
| One-week 1000s | Q Sat–Sun, R64 Sun–Tue, F Sunday (6) | **WTA:** Doha, Dubai, Wuhan (to 2019) Sun–Sat; Madrid to 2019 and Beijing to 2023 from Saturday (−2). **Scheduled Monday finals:** Canada and Cincinnati 2024 (Montreal: "Singles Final: Monday, 12 August not before 7:30 p.m."), Rome 2020. **Cincinnati 2020:** Sat–Sat (−2) | observed |
| 500 and 250 | Main draw Monday (often Sunday), F Sunday; Saturday before a Slam or the Finals | **Saturday finals** (tennis-data 2010–26): ATP 250 24%, ATP 500 10%, WTA 250 30%, WTA 500 33%. **ATP Asian swing 2023–25:** Wed/Thu start, F Tue/Wed (8–9). **January 2021:** Thu–Wed (F 9) | rule (ATP 7.21B; WTA V.B.8a) and observed |
| Tour qualifying | Sat–Sun | **ATP 250:** 3 rounds to 2015; Sun–Mon default from 2022. **WTA:** 2 rounds from 2021 | rule |
| Season finals | ATP Finals Sun–Sun (RR −1..4, SF 5, F 6); Mon–Mon in 2012–13 | **Next Gen:** Tue–Sat (Wed–Sun from 2024). **WTA Finals:** Tue–Sun 2010–13; Sun–Sun 2015–19; Wed–Wed 2021; Mon–Mon 2022; Sun–Mon 2023 (rain); Sat–Sat 2024–25 (−2) | secondary and observed |
| Team, Olympics | Davis Cup ties Fri–Sun to 2018, "two consecutive days" from 2019 (Regulations 22.2.2), Finals ties one day. BJK World Group Sat–Sun. Laver Cup Fri–Sun. Olympics Sat–Sun (R64 −2) | United Cup 2023 began −4 against Sackmann's Monday; ATP Cup 2020 −3; BJK Finals 2024 dated 13 Nov, played 14–20 Nov | secondary and observed |
| ATP Challenger | **Q:** Sat–Mon, 3 rounds (to 2018); one round on day one (2019–Mar 2020); Sun–Mon, 2 rounds (2021+). **Main draw:** Mon–Tue start; F Sunday (Saturday 13–16%) | **2019:** 48/56 draws (R1 coded R64). **Event length:** 9 days from Aug 2020, 8 days 2021–22. **2023:** categories 50–175. **2024+:** 75–125 events before a Slam end Saturday | rule (ATP rulebooks 2015–25) and observed |
| WTA 125 | Q Sat–Sun (to 2020) or Sunday; main draw Mon–Tue; F Sunday | Main draw may start Saturday to Wednesday (2025 per-diem clause) | thin rule; secondary spot checks |
| ITF | **To 2018:** main draw to "begin no later than Tuesday and … finish no later than Sunday"; qualifying "immediately prior". **2019+:** "Qualifying may start on Sunday or Monday and can be played over 1, 2 or 3 days. Main draw should begin on a Tuesday" | **2019:** Transition Tour. **2020:** 7-day events may end Saturday. **2022:** women's 48-draws start Monday | rule (ITF regulations 2013–25) and observed |

**Observed below tour level** (project data):
* **Men's ITF 2021–24** (api-tennis): main draw began Tuesday at 75% of events (Wednesday 18%, Monday 5%). Finals were Sunday 91%, Saturday 7%, Monday 2%.
* **Futures 2011–16** (Sackmann's point-by-point copy): main draws began Monday or Tuesday, and about 38% of events ended Saturday.
* **Challenger finals:** Sunday 83%, Saturday 16%, Monday 1% (Flashscore 2009–18), and 85% / 13% / 2% (api-tennis 2021–24).
* **Challenger qualifying:** Saturday–Monday in 2011–16 (matches by day: Fri 19, Sat 2,054, Sun 1,702, Mon 806, Tue 28). Sunday–Monday at 87% of events in 2021–24.
* **Women's ITF:** the WTA website dates most events Monday–Sunday [provider record]. Exceptions: 2010–18 has Tuesday–Sunday (9%) and Monday–Saturday (4%); in 2019–22, Tuesday–Sunday is the most common pattern.

## 2. How far schedules slip

* **Finals: at most one day late at any level checked.**
  * *Slams:* RG 2012 and the US Open 2010–12 men's finals were played on Monday; the AO 2012 final ended about 01:40 Monday.
  * *Tour level:* at least 18 rain-delayed Monday finals in 2010–26, about 1–3 a year (e.g. Rome 2012, Munich 2015, WTA Finals 2023, Delray Beach 2024). None slipped two days [observed and secondary; a lower bound].
  * *Lower levels (2021–24):* Monday finals at 2–3% of Challengers and 2% of men's ITF events. Some are Sunday-night finals in the Americas dated Monday on a Central European clock.
* **Earlier rounds: up to two days late.**
  * RG 2016 R16 (day 7 → 9); US Open 2011 R16 (8 → 10).
  * Wimbledon 2014 R32 (5 → 7); Wimbledon 2016 R128 and Isner–Mahut 2010 (1 → 3).
  * Montreal 2010 SF (5 → 7); Houston 2023 doubled up R2+QF and SF+F.
* **After midnight** [observed]: share of matches ending on the next local day (Flashscore, ATP 2012–24): Acapulco 8.3%, AO 3.4%, Washington 3.0%, US Open 2.7%, Miami 1.4%, Indian Wells 0.25%. Wimbledon has an 11 pm curfew.
* **Rules** [observed]: one extra day for weather, more only with approval (ATP 7.21F, WTA V.B.8, ITF). Davis Cup ties can be postponed (61.1.2).
* **How well the CSV holds** [observed, project data]:
  * *Main tour:* tennis-data days 2010–26 fall inside their row for 99.84% of Slam, 99.96% of 1000, 99.99% of 500/250 and 98.97% of Finals matches (79,657). With one extra day the figure is 99.98–100%; what remains are six wrong tennis-data dates.
  * *Men's ITF 2021–24:* 99.6–99.9% inside.
  * *Challengers 2021–24:* 97.6–99.6% inside; the misses are mostly api-tennis event keys that merge two editions [inference].
  * *Flashscore Challengers 2010–25:* every R64–R16 match inside.

**Recommended margin [inference].**
* **Every row:** latest possible finish = `latest_day_offset` + 1 day. This covers post-midnight finishes and one more weather day than was seen.
* **Rows without a day-level check:** add a second day. These are ITF and Challenger qualifying before 2016, all ITF before 2019, WTA 125 and Slam qualifying.
* **Dates kept in different clocks:** add a second day here too.
* **The blunt alternative:** "known only after the event's final + 1" is always safe, but delays early-round results by up to two weeks.

## 3. Where lower-level match days can be found

| Source | Old ITF match dates | Qualifying | Access | Automated extraction |
|---|---|---|---|---|
| **Tennis Explorer** (Livesport s.r.o.) | **Men:** yes, but pooled as "Futures YYYY" for 2010–20, without event names; Turkey F2 2014 is timed ("10:40"), and 8 of 8 scores match Core Tennis. **Women:** per event from 2010 (Surprise $25k 2017 final "20.02. 01:00"). Times from about 2014 [observed] | Dated (Turkey F2 2014, Surprise 2017, a 2014 Challenger, a 2016 WTA 125) | HTML, "GMT+1" | **Terms §2.11:** content may not be used "by embedding, aggregating, scraping or recreating it without our express consent"; §2.10 bars substantial extraction. **robots.txt:** /redirect/, /terms-of-use/, /contact/ only |
| **SofaScore** | Women's ITF from 2014 (Surprise 2014/2017 timestamped, within 10 minutes of Tennis Explorer); men's from 2017–18 [observed] | Separate qualifying tournaments from 2018 [unverified] | JSON, Unix epoch | Terms unreadable (JavaScript). Covered by the owner's decisions of 23–25 Sep |
| **TennisLive** | `startTimestamp` for ITF from about 2019 [observed, gap-sources sample] | 2025–26 | HTML/JSON | HTTP 403 today; same decisions |
| Livesport archives (BetExplorer, Flashscore) | Partial (Murcia/Sevilla 2014); women's 2017 not found | Rarely | HTML/JS | Flashscore terms §2.9–2.10 bar scraping |
| **On disk:** Flashscore ITF crawl | UTC dates, no rounds. Women 400–1,900 a year in 2011–19, 3,300–19,500 in 2020–26; men from 2019 | None | Held | — |
| **On disk:** Sackmann point-by-point copy | Dated subset, Jul 2011–Feb 2017: about 19,800 Futures and 19,600 Challenger main-draw matches | About 5,100 Challenger, 90 Futures | Held | CC BY-NC-SA |
| WTA API / WTA site | ITF: no match dates (Kaggle copy included). WTA 125: `MatchTimeStamp` (UTC; start or end unknown) [observed] | WTA 125 | JSON | 24 Sep decision |
| itftennis.com | Bot protection, empty bodies [observed] | — | — | Terms bar means "not intentionally made available" [snippet] |
| Core Tennis, Tennis Abstract, UTS | Tournament date only [observed] | Undated | — | — |
| OnCourt; Sportradar | **OnCourt:** paid; claims ITF results since 2002–05, match dates unknown. **Sportradar:** dropped the ITF Tour from its Tennis API in 2025 [provider claim] | — | Paid | Contractual |
| Matchstat, live-tennis.eu, OddsPortal | HTTP 403, or archive paths disallowed by robots.txt | — | — | Unknown |

**Ranked routes** [inference]:
* **(a) Women's ITF before 2023:** SofaScore (approved route; 2014+ seen), then Tennis Explorer (2010+, needs Livesport's consent), with the Flashscore crawl as a cross-check.
* **(b) Men's ITF before 2021:** Tennis Explorer's "Futures YYYY" (consent needed; join on names, a date window and the round), then the point-by-point copy (2011–16), then SofaScore from 2017–18.
* **(c) Qualifying:**
  * *Challenger:* the point-by-point copy (2011–16), Tennis Explorer, and api-tennis 2021–24 (on disk).
  * *WTA 125:* the WTA API.
  * *ITF:* Tennis Explorer before 2018; SofaScore or TennisLive afterwards (to verify).

## 4. Time zones

| Source | Clock of the date | Evidence |
|---|---|---|
| Sackmann, Tennis My Life | Tournament week only | provider claim |
| tennis-data.co.uk ("Date of match") | UK clock: equals the Europe/London date in 94–99% of 1,404 ATP matches (2012–24) whose UTC, UK, CET and venue dates differ. 7 of the 8 such AO matches follow the local date | observed |
| Flashscore export (on disk) | UTC date of the start, in all of 1,774 such matches | observed |
| Flashscore, SofaScore websites | The viewer's device time zone | provider claim |
| SofaScore, TennisLive APIs | Unix epoch (UTC) | observed |
| api-tennis | "Default timezone: Europe/Berlin": +1 h winter, +2 h summer; the date is the CET date in all of 330 such matches | provider claim, observed |
| Tennis Explorer | "GMT+1" (whether it is a fixed offset is unknown) | observed |
| WTA API | UTC | observed |
| Live Tennis API (Zenodo v1.0.0–1.0.1) | Labelled "UTC", actually Israel time | vendor correction |

**Off-by-one patterns** [observed]:
* **Americas evenings move a day later** in UTC sources (from 20:00 EDT), UK sources (19:00) and CET sources (18:00). For example, tennis-data dates the Montreal 2024 final (Monday, 7:30 pm) Tuesday.
* **Australian and Asian mornings move a day earlier** in UTC sources.
* **Post-midnight finishes** end on the next local day.
* **tennis-data has whole-day errors:** the 2010 US Open men's final is dated Sunday although it was played Monday, and the 2011 Wimbledon and 2025 Madrid men's finals are dated Saturday.

**Rule** [inference]: convert dates to venue-local days before applying the CSV. A local day D at UTC offset o is the interval [D − o, D + 1 − o). Where a source's clock is unknown, widen by a day on each side.

## Unverified or unknown

* **Slam qualifying:** the per-day Q1/Q2/Q3 split, and the dates for AO 2010–14, 2017 and 2022; RG 2010–17; Wimbledon 2010–14 and 2016; US Open 2010–14 and 2016–17.
* **Slam round days:** official schedule pages did not render, so the days rest on Wikipedia plus the project's data.
* **Rulebooks not found:** ATP 2010–14, 2017–18 and 2023; ITF January 2019; Davis Cup 2010–18; Fed/BJK Cup.
* **Round days not established:** the BJK Cup Finals 2024–25, United Cup quarter-finals, the World Team Cup 2010–12, the Challenger Tour Finals 2011–15 and the WTA Elite Trophy 2023.
* **Patterns not established:** whether Challenger main draws really started Sunday in 2021–25, and the women's ITF Saturday-final share after 2019. The Flashscore crawl's 18% is an upper bound.
* **Sources:**
  * *Tennis Explorer:* completeness, and whether date-only rows are imputed.
  * *SofaScore:* qualifying before 2018.
  * *Others:* whether OnCourt dates matches; the terms of Matchstat and live-tennis.eu.
* **2026 pages** were edited after the model's knowledge cutoff and were not cross-checked.

## Method and limits

* **Lanes.** Four research lanes ran in parallel: Grand Slams; other tour-level events; Challenger, WTA 125 and ITF rules; and dated sources. The lead checked key claims and re-fetched the Montreal and Cincinnati 2024 schedules. The lanes' shared web-search quota ran out (200 of 200) partway through.
* **Local checks.** These used scratch scripts run with `./python.sh`, not saved in the repo. Inputs:
  * `data/studies/feature_alpha_audit/repairs/repair_date_audit.parquet` (tennis-data days for 79,669 main-tour matches);
  * the Flashscore export;
  * api-tennis fixtures for 2021–24;
  * the Flashscore ITF crawl;
  * `data/raw/point_shot_sources/pbp_copy_2018/`;
  * the WTA-site Kaggle copy;
  * the gap-sources samples.
* **Deviations.**
  * One lane read Wayback PDFs with `C:/Users/zerom/miniforge3/python.exe` (pypdf), not `./python.sh`.
  * The fetch tool saved PDF copies outside the repo.
  * One lane fetched two paths that robots.txt disallows, once each: Tennis Explorer's `/terms-of-use/` and one Tennis Abstract `/jsmatches/` file.
  * Nothing was bought or bulk-downloaded.

## Sources (accessed 5 October 2026)

**Rules**
* ATP rulebooks:
  * 2015: https://www.atptour.com/~/media/files/rulebook/2015/2015_atp_rulebook_2015jan18.pdf
  * 2016: https://www.atptour.com/-/media/files/rulebook/2016/2016-atp-rulebook_13oct16.pdf
  * 2019: https://www.atptour.com/-/media/files/rulebook/2019/2019-atp-rulebook_chapter-1_atp-circuit-regulations.pdf
  * 2020: https://www.atptour.com/-/media/files/rulebook/2020/2020-atp-rulebook_03mar20.pdf
  * 2020 Challenger addendum: https://www.atptour.com/-/media/files/rulebook/2020/2020-atp-rulebook-challenger-addendum_25aug.pdf
  * 2021 Challenger addendum: https://www.atptour.com/-/media/files/rulebook/2021/2021-atp-rulebook-challenger-addendum-16mar.pdf
  * 2022: https://www.itftennis.com/media/7357/2022-atp-rulebook_23dec.pdf
  * 2024: https://www.itftennis.com/media/11553/2024-rulebook-atp.pdf
  * 2025, chapter 1: https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-1_atp-circuit-regulations_20may.pdf
  * 2025, chapter 7: https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-7_the-competition_23dec.pdf
  * 2026, chapter 7: https://www.atptour.com/-/media/files/rulebook/2026/2026-rulebook-chapter-7_the-competition_25jan26.pdf
* ATP Challenger changes (July 2018): https://www.atptour.com/-/media/sites/atp-tour/press/press-releases/23-july-2018-atp-challenger-tour-enhancements.pdf
* WTA rulebooks:
  * 2019: https://wtafiles.wtatennis.com/pdf/publications/2019WTARulebook.pdf
  * 2021: https://photoresources.wtatennis.com/wta/document/2021/03/08/d6d2c650-e3b4-42e7-ab2b-e539d4586033/2021Rulebook.pdf
  * 2024: https://www.itftennis.com/media/11824/2024-wta-rulebook.pdf
  * 2025: https://www.itftennis.com/media/13920/2025-wta-rulebook.pdf
* ITF:
  * 2013 regulations: https://web.archive.org/web/20130222074526/http://www.itftennis.com/media/136302/136302.pdf
  * 2017 regulations: https://tennis.tppwb.be/Aftnet/media/Media/Documents/Arbitrage/Pro-Circuit.pdf
  * Transition Tour FAQ: https://web.archive.org/web/20180203074458/http://www.itftennis.com/procircuit/about-pro-circuit/transition-tour-faqs.aspx
  * 2019 regulations: https://www.itftennis.com/media/1971/1.pdf
  * 2020 regulations: https://www.itftennis.com/media/3870/itf-world-tennis-tour-regulations-amended-august-2020.pdf
  * 2022 requirements: https://www.itftennis.com/media/7953/2022-mens-womens-itf-world-tennis-tour-organisational-requirements.pdf
  * 2025 regulations: https://www.itftennis.com/media/15118/2025-wtt-regulations.pdf
* Davis Cup Regulations 2025: https://www.blta.bm/wp-content/uploads/2025/02/2025-Davis-Cup-Regulations.pdf

**Schedules and slips**
* ATP previews (`https://www.atptour.com/en/news/<slug>`):
  * montreal-2024-atp-masters-1000-history-draw-schedule
  * cincinnati-2024-atp-masters-1000-history-draw-schedule
  * indian-wells-2025-atp-masters-1000-history-draw-schedule
  * madrid-2025-atp-masters-1000-history-draw-schedule
  * toronto-2025-atp-masters-1000-history-draw-schedule
  * cincinnati-2025-atp-masters-1000-history-draw-schedule
  * beijing-2024-atp-500-history-draw-schedule
* WTA previews (`https://www.wtatennis.com/news/<id>`): 4226291, 4233079, 4257535, 4321854
* Slam days: Wikipedia "<year> <Slam> – Day-by-day summaries", e.g. https://en.wikipedia.org/wiki/2016_French_Open_%E2%80%93_Day-by-day_summaries
* AO 2021 qualifying (checked later on 5 October):
  * https://en.wikipedia.org/wiki/2021_Australian_Open_%E2%80%93_Men%27s_singles_qualifying
  * https://en.wikipedia.org/wiki/2021_Australian_Open_%E2%80%93_Women%27s_singles_qualifying
  * https://www.tennis.com.au/news/2021/01/11/more-aussies-advance-in-australian-open-2021-qualifying
  * https://www.tennis.com.au/news/2021/01/12/aussies-march-on-in-australian-open-2021-qualifying
  * https://www.tennis.com.au/news/2021/01/13/three-aussies-set-for-final-australian-open-2021-qualifying-round
  * https://www.wtatennis.com/news/1969819/ao-recap-day-1
  * https://www.wtatennis.com/news/1972373/babos-battles-to-victory-as-australian-open-qualifiers-are-settled
* Format announcements:
  * AO 2024 Sunday start: https://www.tennismajors.com/australian-open-news/2024-australian-open-to-start-on-a-sunday-becomes-15-day-event-717920.html
  * US Open 2025 Sunday start: https://www.si.com/tennis/us-open-2025-will-start-one-day-earlier-add-15th-day-major-tournament
  * Wimbledon Middle Sunday: https://www.tennismajors.com/wimbledon-news/open-doors-vaccines-no-hawk-eye-live-what-we-learned-from-the-wimbledon-press-conference-336018.html
* Slips:
  * RG 2012 final: https://www.espn.com/tennis/french12/story/_/id/8033759/2012-french-open-final-novak-djokovic-rafael-nadal-suspended-rain
  * RG 2016 washout: https://www.foxnews.com/sports/for-the-1st-time-in-16-years-french-open-is-washed-out
  * RG 2019 semi-final: https://africa.espn.com/tennis/story/_/id/26920606/djokovic-thiem-semifinal-suspended-rain
  * Wimbledon 2018 semi-final: https://africa.espn.com/tennis/story/_/id/24090029/wimbledon-2018-novak-djokovic-rafael-nadal-semifinal-halted-wimbledon-curfew
  * Rome 2012 final: https://amp.foxsports.com/stories/tennis/djokovic-nadal-final-pushed-to-monday
  * Montreal 2010: https://www.tennis.com/news/articles/wozniacki-wins-monday-semi-and-final-for-rogers-cup
  * WTA Finals 2023: https://www.tntsports.co.uk/tennis/wta-finals/2023/semi-final-between-aryna-sabalenka-and-iga-swiatek-suspended-until-sunday-as-rain-wreaks-more-havoc-_sto9871062/story.shtml
  * Delray Beach 2024: https://tennistourtalk.com/107249/delray-beach-open-finals-washed-out-to-be-played-monday
  * Houston 2023: https://www.10sballs.com/2023/04/07/rain-cancels-play-in-houston-on-friday/

**Sources and time zones**
* Tennis Explorer:
  * Terms: https://www.tennisexplorer.com/terms-of-use/
  * robots.txt: https://www.tennisexplorer.com/robots.txt
  * 2014 results: https://www.tennisexplorer.com/results/?type=atp-single&year=2014&month=02&day=05
  * Surprise 2017: https://www.tennisexplorer.com/surprise-itf/2017/wta-women/
* Flashscore:
  * Terms: https://www.flashscore.com/terms-of-use/
  * Time-zone FAQ: https://www.flashscore.com/faq/capabilities
* SofaScore:
  * Help page: https://sofascore.helpscoutdocs.com/article/19-match-times-are-late-or-early-why
  * Surprise seasons: https://api.sofascore.com/api/v1/unique-tournament/6980/seasons
* api-tennis documentation: https://api-tennis.com/documentation
* tennis-data.co.uk notes: http://www.tennis-data.co.uk/notes.txt
* Core Tennis, Turkey F2 2014: https://www.coretennis.net/majic/pageServer/0r0100000c/en/tid/41912/Tournament-Rounds.html
* WTA order of play: https://wtafiles.wtatennis.com/pdf/draws/2017/3200/OP.pdf
* Sackmann point-by-point copy: https://github.com/ppaulojr/tennis_pointbypoint

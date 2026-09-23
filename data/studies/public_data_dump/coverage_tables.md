# Public data dump coverage tables

Generated 2026-09-22T22:35:29+00:00 by src/ingest/public_dump/build_manifest.py from the staged Parquet files. Dates are the verbatim min/max of the named column (tournament-week dates for Sackmann/TML, match dates for tennis-data.co.uk, scheduled UTC for the Live Tennis API index); row counts are physical rows.

## By branch and source

| Branch | Source | Files | Rows | MB | Earliest | Latest | Routes |
|---|---|---:|---:|---:|---|---|---|
| matches | live_tennis_api_zenodo | 1 | 173,571 | 3.1 | 2023-01-01 01:05:00 | 2026-08-13 23:50:00 |  |
| matches | open_tennis_data | 10 | 110,262 | 3.7 | 2020-01-05 | 2026-08-29 |  |
| matches | sackmann_archive | 96 | 882,094 | 28.7 | 20091228 | 20260602 |  |
| matches | tennis_my_life | 104 | 304,076 | 14.8 | 20000103 | 20260921 |  |
| odds | polymarket | 86 | 62,720,194 | 253.6 | 2024-01-28T00:00:00+00:00 | 2027-12-31T23:59:00+00:00 |  |
| odds | tennis_data_couk | 229 | 106,996 | 7.0 | 2000-01-03 | 2029-07-20 | wayback=229 |
| players | live_tennis_api_zenodo | 1 | 32,678 | 0.6 |  |  |  |
| players | open_tennis_data | 1 | 1,216 | 0.0 |  |  |  |
| players | sackmann_archive | 2 | 137,483 | 2.3 |  |  |  |
| players | tennis_my_life | 1 | 12,903 | 0.5 |  |  |  |
| points | live_tennis_api_zenodo | 1 | 951,064 | 11.7 | 2026-06-01 12:09:27.301627 | 2026-07-01 03:32:34.811345 |  |
| points | match_charting_project | 38 | 4,537,499 | 48.2 | 19600529 | 20260909 |  |
| points | sackmann_archive | 166 | 2,328,041 | 35.6 | 2011 | 2024 |  |
| rankings | sackmann_archive | 6 | 2,537,744 | 14.5 | 20100101 | 20260608 |  |
| rankings | tennis_my_life | 1 | 2,298 | 0.0 |  |  |  |

## Rows by tournament-type value (verbatim source labels)

### matches/live_tennis_api_zenodo

| Value | Rows |
|---|---:|
| 271 | 37,379 |
| 281 | 36,851 |
| 270 | 35,642 |
| 265 | 16,476 |
| 266 | 15,950 |
| 282 | 9,999 |
| 272 | 5,659 |
| 267 | 5,116 |
| 268 | 4,545 |
| 275 | 1,500 |
|  | 1,064 |
| 264 | 782 |
| utr_men | 681 |
| 287 | 630 |
| utr_women | 516 |
| 266_inferred | 312 |
| 278 | 149 |
| 277 | 148 |
| 279 | 85 |
| 280 | 80 |
| 265_inferred | 3 |
| 285 | 2 |
| 273 | 2 |

### matches/open_tennis_data

| Value | Rows |
|---|---:|
| other | 532 |
| wta_500 | 112 |
| grand_slam | 64 |
| masters_1000 | 58 |
| wta_1000 | 35 |
| tour_finals | 21 |

### matches/sackmann_archive

| Value | Rows |
|---|---:|
| S | 184,063 |
| 15 | 166,721 |
| C | 123,220 |
| 25 | 114,974 |
| 10 | 69,663 |
| A | 46,309 |
| G | 32,292 |
| I | 24,100 |
| 35 | 17,438 |
| P | 17,148 |
| M | 15,299 |
| 50 | 15,148 |
| 60 | 15,129 |
| 100 | 9,506 |
| 75 | 8,222 |
| D | 7,919 |
| PM | 7,354 |
| 80 | 3,098 |
| 40 | 2,741 |
| F | 779 |
| W | 436 |
| O | 320 |
| 50+H | 184 |
| 35+H | 31 |

### matches/tennis_my_life

| Value | Rows |
|---|---:|
| C | 121,838 |
| 250 | 49,496 |
| G | 35,802 |
| M | 19,758 |
| 500 | 16,464 |
| D | 14,255 |
| I | 11,350 |
| T1 | 4,651 |
| T3 | 4,562 |
| T2 | 4,329 |
| P | 4,120 |
| 1000 | 3,865 |
| PM | 3,426 |
| P5 | 3,171 |
| T4 | 2,912 |
| A | 935 |
| F | 915 |
| T5 | 913 |
| O | 894 |
|  | 374 |
| W | 46 |

### odds/polymarket

| Value | Rows |
|---|---:|
| itf | 20,593,357 |
| challenger_125_inferred | 14,630,051 |
| doubles | 8,157,407 |
| tour_1000 | 4,068,897 |
| slam_main | 3,937,653 |
| tour_250 | 3,621,051 |
| tour_500 | 2,422,151 |
| tour_qualifying | 2,012,016 |
| slam_juniors | 1,550,613 |
| slam_qualifying | 1,390,669 |
| tour_finals | 222,032 |
| team_exhibition | 63,068 |
| ITF World Tennis Tour | 17,930 |
| None | 11,766 |
| Challenger / WTA 125 (inferred from bare names) | 7,021 |
| Doubles (all tiers) | 2,794 |
| other | 1,833 |
| Main-tour qualifying (1000/500/250) | 1,699 |
| Masters 1000 / WTA 1000 (main draw) | 1,660 |
| ATP 250 / WTA 250 (main draw) | 1,538 |
| outrights | 1,154 |
| ATP 500 / WTA 500 (main draw) | 1,017 |
| Grand Slam singles (main draw) | 1,007 |
| Grand Slam qualifying | 832 |
| Grand Slam juniors | 692 |
| Props, exact-score wrappers & other | 159 |
| Tour Finals (ATP/WTA/Next Gen) | 51 |
| Team events & exhibitions | 50 |
| Tournament-winner futures (mostly Slams) | 26 |

### odds/tennis_data_couk

| Value | Rows |
|---|---:|
| Grand Slam | 21,336 |
| International | 19,747 |
| ATP250 | 17,861 |
| Premier | 10,432 |
| Masters 1000 | 9,458 |
| ATP500 | 6,705 |
| WTA250 | 4,697 |
| WTA1000 | 3,616 |
| Masters | 3,418 |
| WTA500 | 2,624 |
| International Gold | 2,537 |
| Tier 3 | 1,115 |
| Tier 1 | 1,065 |
| Tier 2 | 895 |
| Tier 4 | 774 |
| Tour Championships | 360 |
| Masters Cup | 330 |
| WTA251 | 1 |
| WTA252 | 1 |
| WTA253 | 1 |
| WTA254 | 1 |
| WTA255 | 1 |
| WTA256 | 1 |
| WTA257 | 1 |
| WTA258 | 1 |
| WTA259 | 1 |
| WTA260 | 1 |
| WTA261 | 1 |
| WTA262 | 1 |
| WTA263 | 1 |
| WTA264 | 1 |
| WTA265 | 1 |
| WTA266 | 1 |
| WTA267 | 1 |
| WTA268 | 1 |
| WTA269 | 1 |
| WTA270 | 1 |
| WTA271 | 1 |
| WTA272 | 1 |
| WTA273 | 1 |

## Every staged file

| File | Rows | Date column | Earliest | Latest | Short/long rows | Route |
|---|---:|---|---|---|---|---|
| data/dump/matches/live_tennis_api_zenodo/matches.parquet | 173,571 | scheduled_time_utc | 2023-01-01 01:05:00 | 2026-08-13 23:50:00 | 0/0 |  |
| data/dump/matches/open_tennis_data/catalog.parquet | 10 |  |  |  | 0/0 |  |
| data/dump/matches/open_tennis_data/completed.parquet | 26,619 | date | 2020-01-05 | 2026-08-29 | 0/0 |  |
| data/dump/matches/open_tennis_data/coverage.parquet | 59 |  |  |  | 0/0 |  |
| data/dump/matches/open_tennis_data/fixtures.parquet | 24 | date |  |  | 0/0 |  |
| data/dump/matches/open_tennis_data/health.parquet | 2 |  |  |  | 0/0 |  |
| data/dump/matches/open_tennis_data/matches.parquet | 26,643 | date | 2020-01-05 | 2026-08-29 | 0/0 |  |
| data/dump/matches/open_tennis_data/provenance.parquet | 53,491 |  |  |  | 0/0 |  |
| data/dump/matches/open_tennis_data/quarantine.parquet | 2,556 |  |  |  | 0/0 |  |
| data/dump/matches/open_tennis_data/sources.parquet | 95 |  |  |  | 0/0 |  |
| data/dump/matches/open_tennis_data/tournaments.parquet | 763 | start_date | 2020-01-06 | 2026-08-23 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2010.parquet | 3,030 | tourney_date | 20100103 | 20101203 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2011.parquet | 3,015 | tourney_date | 20110102 | 20111202 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2012.parquet | 3,009 | tourney_date | 20120101 | 20121116 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2013.parquet | 2,944 | tourney_date | 20121230 | 20131115 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2014.parquet | 2,901 | tourney_date | 20131229 | 20141121 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2015.parquet | 2,943 | tourney_date | 20150104 | 20151127 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2016.parquet | 2,941 | tourney_date | 20160104 | 20161125 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2017.parquet | 2,911 | tourney_date | 20170102 | 20171124 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2018.parquet | 2,897 | tourney_date | 20180101 | 20181123 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2019.parquet | 2,806 | tourney_date | 20181231 | 20191124 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2020.parquet | 1,462 | tourney_date | 20200106 | 20201116 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2021.parquet | 2,733 | tourney_date | 20210104 | 20211205 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2022.parquet | 2,917 | tourney_date | 20220103 | 20221127 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2023.parquet | 2,986 | tourney_date | 20230102 | 20231127 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2024.parquet | 3,076 | tourney_date | 20240101 | 20241218 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2025.parquet | 2,944 | tourney_date | 20241227 | 20251217 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_2026.parquet | 1,449 | tourney_date | 20260104 | 20260525 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_doubles_2010.parquet | 1,295 | tourney_date | 20100103 | 20101121 | 0/1295 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_doubles_2011.parquet | 1,281 | tourney_date | 20110102 | 20111120 | 0/1281 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_doubles_2012.parquet | 1,300 | tourney_date | 20120101 | 20121105 | 0/1300 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_doubles_2013.parquet | 1,260 | tourney_date | 20121230 | 20131104 | 0/1260 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_doubles_2014.parquet | 1,275 | tourney_date | 20131229 | 20141109 | 0/1275 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_doubles_2015.parquet | 1,317 | tourney_date | 20150104 | 20151115 | 0/1317 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_doubles_2016.parquet | 1,354 | tourney_date | 20160104 | 20161114 | 0/1354 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_doubles_2017.parquet | 1,313 | tourney_date | 20170102 | 20171113 | 0/1313 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_doubles_2018.parquet | 1,285 | tourney_date | 20180101 | 20181112 | 0/1285 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_doubles_2019.parquet | 1,363 | tourney_date | 20181231 | 20191111 | 0/1363 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_doubles_2020.parquet | 270 | tourney_date | 20200106 | 20200306 | 0/270 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2010.parquet | 15,074 | tourney_date | 20091228 | 20101220 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2011.parquet | 16,635 | tourney_date | 20101227 | 20111219 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2012.parquet | 18,313 | tourney_date | 20120102 | 20121224 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2013.parquet | 19,951 | tourney_date | 20130107 | 20131223 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2014.parquet | 20,862 | tourney_date | 20140106 | 20141222 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2015.parquet | 21,291 | tourney_date | 20150105 | 20151214 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2016.parquet | 19,850 | tourney_date | 20160104 | 20161219 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2017.parquet | 18,503 | tourney_date | 20170102 | 20171204 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2018.parquet | 16,986 | tourney_date | 20180101 | 20181224 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2019.parquet | 16,598 | tourney_date | 20181231 | 20191230 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2020.parquet | 4,586 | tourney_date | 20200106 | 20201228 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2021.parquet | 11,833 | tourney_date | 20210104 | 20211227 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2022.parquet | 16,306 | tourney_date | 20220103 | 20221226 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2023.parquet | 17,626 | tourney_date | 20230102 | 20231225 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2024.parquet | 18,423 | tourney_date | 20240101 | 20241216 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2025.parquet | 17,906 | tourney_date | 20241230 | 20251229 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_futures_2026.parquet | 6,894 | tourney_date | 20260105 | 20260601 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2010.parquet | 6,597 | tourney_date | 20100103 | 20101122 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2011.parquet | 6,371 | tourney_date | 20110102 | 20111121 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2012.parquet | 6,426 | tourney_date | 20120101 | 20121127 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2013.parquet | 6,464 | tourney_date | 20121230 | 20131118 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2014.parquet | 6,424 | tourney_date | 20131229 | 20141117 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2015.parquet | 6,898 | tourney_date | 20150104 | 20151123 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2016.parquet | 9,849 | tourney_date | 20160104 | 20161121 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2017.parquet | 9,141 | tourney_date | 20170102 | 20171120 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2018.parquet | 9,920 | tourney_date | 20180101 | 20181119 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2019.parquet | 8,970 | tourney_date | 20181231 | 20191118 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2020.parquet | 3,288 | tourney_date | 20200106 | 20201130 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2021.parquet | 7,497 | tourney_date | 20210104 | 20211213 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2022.parquet | 10,016 | tourney_date | 20220103 | 20221128 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2023.parquet | 10,663 | tourney_date | 20230101 | 20231127 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2024.parquet | 11,190 | tourney_date | 20240101 | 20241125 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2025.parquet | 11,629 | tourney_date | 20241230 | 20251124 | 0/0 |  |
| data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2026.parquet | 5,745 | tourney_date | 20260104 | 20260601 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2010.parquet | 2,781 | tourney_date | 20100104 | 20101106 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2011.parquet | 2,804 | tourney_date | 20110103 | 20111105 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2012.parquet | 2,849 | tourney_date | 20120102 | 20121103 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2013.parquet | 2,714 | tourney_date | 20121231 | 20131028 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2014.parquet | 2,785 | tourney_date | 20131230 | 20141108 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2015.parquet | 2,651 | tourney_date | 20150105 | 20151114 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2016.parquet | 2,923 | tourney_date | 20160104 | 20161112 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2017.parquet | 2,862 | tourney_date | 20170102 | 20171111 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2018.parquet | 2,756 | tourney_date | 20180101 | 20181110 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2019.parquet | 2,743 | tourney_date | 20181231 | 20191216 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2020.parquet | 1,276 | tourney_date | 20200106 | 20201109 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2021.parquet | 2,597 | tourney_date | 20210106 | 20211110 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2022.parquet | 2,594 | tourney_date | 20220103 | 20221113 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2023.parquet | 2,810 | tourney_date | 20230102 | 20231110 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2024.parquet | 2,689 | tourney_date | 20240101 | 20241125 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2025.parquet | 2,795 | tourney_date | 20241227 | 20251101 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_2026.parquet | 1,295 | tourney_date | 20260104 | 20260525 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2010.parquet | 15,975 | tourney_date | 20100104 | 20101220 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2011.parquet | 17,159 | tourney_date | 20110103 | 20111219 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2012.parquet | 16,605 | tourney_date | 20111226 | 20121224 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2013.parquet | 18,696 | tourney_date | 20121231 | 20131223 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2014.parquet | 18,817 | tourney_date | 20131230 | 20141222 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2015.parquet | 19,727 | tourney_date | 20141229 | 20151221 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2016.parquet | 19,380 | tourney_date | 20160104 | 20161219 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2017.parquet | 18,897 | tourney_date | 20170102 | 20171225 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2018.parquet | 18,576 | tourney_date | 20180101 | 20181217 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2019.parquet | 29,423 | tourney_date | 20181231 | 20191230 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2020.parquet | 9,426 | tourney_date | 20200106 | 20201228 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2021.parquet | 24,189 | tourney_date | 20210104 | 20211227 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2022.parquet | 33,105 | tourney_date | 20220103 | 20221226 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2023.parquet | 34,322 | tourney_date | 20230102 | 20231225 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2024.parquet | 38,281 | tourney_date | 20240101 | 20241216 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2025.parquet | 21,615 | tourney_date | 20241230 | 20251229 | 0/0 |  |
| data/dump/matches/sackmann_archive/wta/wta_matches_qual_itf_2026.parquet | 8,975 | tourney_date | 20260104 | 20260602 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2000_challenger.parquet | 3,534 | tourney_date | 20000130 | 20001210 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2001_challenger.parquet | 4,030 | tourney_date | 20010107 | 20011209 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2002_challenger.parquet | 3,579 | tourney_date | 20011231 | 20021208 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2003_challenger.parquet | 3,968 | tourney_date | 20021230 | 20031229 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2004_challenger.parquet | 4,154 | tourney_date | 20040111 | 20041212 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2005_challenger.parquet | 4,340 | tourney_date | 20050109 | 20051226 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2006_challenger.parquet | 4,464 | tourney_date | 20060108 | 20061126 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2007_challenger.parquet | 4,587 | tourney_date | 20070128 | 20071118 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2008_challenger.parquet | 5,022 | tourney_date | 20080127 | 20081130 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2009_challenger.parquet | 4,774 | tourney_date | 20090111 | 20091130 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2010_challenger.parquet | 4,340 | tourney_date | 20100110 | 20101128 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2011_challenger.parquet | 4,214 | tourney_date | 20110109 | 20111127 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2012_challenger.parquet | 4,231 | tourney_date | 20120108 | 20121127 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2013_challenger.parquet | 4,324 | tourney_date | 20121231 | 20131124 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2014_challenger.parquet | 4,386 | tourney_date | 20131230 | 20141123 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2015_challenger.parquet | 4,603 | tourney_date | 20150111 | 20151129 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2016_challenger.parquet | 4,929 | tourney_date | 20160110 | 20161127 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2017_challenger.parquet | 4,495 | tourney_date | 20170107 | 20171126 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2018_challenger.parquet | 4,684 | tourney_date | 20180106 | 20181125 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2019_challenger.parquet | 3,244 | tourney_date | 20181231 | 20190616 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2020_challenger.parquet | 2,184 | tourney_date | 20200112 | 20201130 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2021_challenger.parquet | 4,344 | tourney_date | 20210124 | 20211219 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2022_challenger.parquet | 5,391 | tourney_date | 20220109 | 20221128 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2023_challenger.parquet | 5,693 | tourney_date | 20230107 | 20231127 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2024_challenger.parquet | 6,063 | tourney_date | 20071231 | 20241125 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2025_challenger.parquet | 6,411 | tourney_date | 20241230 | 20251124 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_challenger/2026_challenger.parquet | 5,790 | tourney_date | 20260105 | 20260914 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2000.parquet | 3,378 | tourney_date | 20000103 | 20001208 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2001.parquet | 3,311 | tourney_date | 20010101 | 20011130 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2002.parquet | 3,213 | tourney_date | 20011231 | 20021129 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2003.parquet | 3,218 | tourney_date | 20021230 | 20031128 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2004.parquet | 3,288 | tourney_date | 20040105 | 20041203 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2005.parquet | 3,263 | tourney_date | 20050103 | 20051202 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2006.parquet | 3,267 | tourney_date | 20060102 | 20061201 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2007.parquet | 3,192 | tourney_date | 20070101 | 20071130 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2008.parquet | 3,123 | tourney_date | 20071231 | 20081121 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2009.parquet | 3,085 | tourney_date | 20090104 | 20091204 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2010.parquet | 3,030 | tourney_date | 20100103 | 20101203 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2011.parquet | 3,015 | tourney_date | 20110102 | 20111202 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2012.parquet | 3,009 | tourney_date | 20120101 | 20121116 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2013.parquet | 2,944 | tourney_date | 20121230 | 20131115 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2014.parquet | 2,901 | tourney_date | 20131229 | 20141121 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2015.parquet | 2,945 | tourney_date | 20150104 | 20151127 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2016.parquet | 2,970 | tourney_date | 20160104 | 20161125 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2017.parquet | 2,936 | tourney_date | 20170102 | 20171124 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2018.parquet | 2,926 | tourney_date | 20180101 | 20181123 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2019.parquet | 2,806 | tourney_date | 20181231 | 20191124 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2020.parquet | 1,466 | tourney_date | 20200103 | 20201116 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2021.parquet | 2,735 | tourney_date | 20210104 | 20211205 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2022.parquet | 2,918 | tourney_date | 20220103 | 20221127 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2023.parquet | 2,995 | tourney_date | 20230102 | 20231127 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2024.parquet | 3,076 | tourney_date | 20240101 | 20241218 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2025.parquet | 2,944 | tourney_date | 20241229 | 20251222 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_main/2026.parquet | 2,259 | tourney_date | 20260102 | 20260913 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2007_atp_quali.parquet | 1,756 | tourney_date | 20070101 | 20071028 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2008_atp_quali.parquet | 1,687 | tourney_date | 20071231 | 20081026 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2009_atp_quali.parquet | 1,737 | tourney_date | 20090104 | 20091108 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2010_atp_quali.parquet | 1,823 | tourney_date | 20100103 | 20101107 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2011_atp_quali.parquet | 1,843 | tourney_date | 20110102 | 20111107 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2012_atp_quali.parquet | 1,854 | tourney_date | 20120101 | 20121029 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2013_atp_quali.parquet | 1,861 | tourney_date | 20121230 | 20131028 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2014_atp_quali.parquet | 1,805 | tourney_date | 20131229 | 20141027 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2015_atp_quali.parquet | 1,862 | tourney_date | 20150104 | 20151102 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2016_atp_quali.parquet | 1,292 | tourney_date | 20160104 | 20161031 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2017_atp_quali.parquet | 1,308 | tourney_date | 20170101 | 20171030 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2018_atp_quali.parquet | 1,305 | tourney_date | 20171231 | 20181029 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2019_atp_quali.parquet | 1,293 | tourney_date | 20181231 | 20191028 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2020_atp_quali.parquet | 635 | tourney_date | 20200106 | 20201108 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2021_atp_quali.parquet | 1,290 | tourney_date | 20210107 | 20211107 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2022_atp_quali.parquet | 1,318 | tourney_date | 20220103 | 20221031 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2023_atp_quali.parquet | 1,336 | tourney_date | 20230101 | 20231106 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2024_atp_quali.parquet | 1,342 | tourney_date | 20231231 | 20241103 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2025_atp_quali.parquet | 1,292 | tourney_date | 20241229 | 20251102 | 0/0 |  |
| data/dump/matches/tennis_my_life/atp_qualifying/2026_atp_quali.parquet | 1,105 | tourney_date | 20260104 | 20260828 | 0/0 |  |
| data/dump/matches/tennis_my_life/ongoing/challenger_ongoing_tourneys.parquet | 60 | tourney_date | 20260921 | 20260921 | 0/0 |  |
| data/dump/matches/tennis_my_life/ongoing/ongoing_tourneys.parquet | 100 | tourney_date | 20260918 | 20260920 | 0/0 |  |
| data/dump/matches/tennis_my_life/ongoing/wta_ongoing_tourneys.parquet | 28 | tourney_date | 20260921 | 20260921 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2000_wta.parquet | 2,357 | tourney_date | 20000103 | 20001113 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2001_wta.parquet | 2,882 | tourney_date | 20001231 | 20011111 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2002_wta.parquet | 2,924 | tourney_date | 20011230 | 20021106 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2003_wta.parquet | 2,717 | tourney_date | 20021230 | 20031122 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2004_wta.parquet | 2,805 | tourney_date | 20040105 | 20041127 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2005_wta.parquet | 2,843 | tourney_date | 20050103 | 20051107 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2006_wta.parquet | 2,787 | tourney_date | 20060102 | 20061106 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2007_wta.parquet | 2,778 | tourney_date | 20070101 | 20071105 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2008_wta.parquet | 2,791 | tourney_date | 20071231 | 20081103 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2009_wta.parquet | 2,722 | tourney_date | 20090105 | 20091107 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2010_wta.parquet | 2,781 | tourney_date | 20100104 | 20101106 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2011_wta.parquet | 2,804 | tourney_date | 20110103 | 20111105 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2012_wta.parquet | 2,849 | tourney_date | 20120102 | 20121103 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2013_wta.parquet | 2,714 | tourney_date | 20121231 | 20131028 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2014_wta.parquet | 2,785 | tourney_date | 20131230 | 20141108 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2015_wta.parquet | 2,651 | tourney_date | 20150105 | 20151114 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2016_wta.parquet | 2,923 | tourney_date | 20160104 | 20161112 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2017_wta.parquet | 2,831 | tourney_date | 20170102 | 20171111 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2018_wta.parquet | 2,756 | tourney_date | 20180101 | 20181110 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2019_wta.parquet | 2,743 | tourney_date | 20181231 | 20191216 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2020_wta.parquet | 1,276 | tourney_date | 20200106 | 20201109 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2021_wta.parquet | 2,597 | tourney_date | 20210106 | 20211117 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2022_wta.parquet | 2,594 | tourney_date | 20220103 | 20221113 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2023_wta.parquet | 2,810 | tourney_date | 20221229 | 20231110 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2024_wta.parquet | 2,658 | tourney_date | 20231229 | 20241115 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2025_wta.parquet | 2,622 | tourney_date | 20241230 | 20251114 | 0/0 |  |
| data/dump/matches/tennis_my_life/wta_main/2026_wta.parquet | 2,153 | tourney_date | 20260104 | 20260921 | 0/0 |  |
| data/dump/odds/polymarket/event_index.parquet | 37,680 | sport_date | 2024-01-28T00:00:00+00:00 | 2027-12-31T23:59:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/market_index.parquet | 464,266 | gameStartTime | 2024-07-12 14:30:00+00 | 2026-09-24 13:00:00+00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/challenger_125_inferred/2025-10.parquet | 105,958 | sport_date | 2025-10-11T09:00:00+00:00 | 2025-10-19T13:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/challenger_125_inferred/2026-02.parquet | 910,411 | sport_date | 2026-02-13T12:30:00+00:00 | 2026-02-28T16:05:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/challenger_125_inferred/2026-03.parquet | 1,827,838 | sport_date | 2026-03-01T09:45:00+00:00 | 2026-03-31T22:15:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/challenger_125_inferred/2026-04.parquet | 2,160,289 | sport_date | 2026-04-01T00:20:00+00:00 | 2026-04-30T21:35:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/challenger_125_inferred/2026-05.parquet | 1,642,147 | sport_date | 2026-05-01T03:05:00+00:00 | 2026-05-31T18:20:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/challenger_125_inferred/2026-06.parquet | 2,006,949 | sport_date | 2026-06-01T08:00:00+00:00 | 2026-06-30T23:40:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/challenger_125_inferred/2026-07.parquet | 2,064,726 | sport_date | 2026-07-01T01:10:00+00:00 | 2026-07-31T23:40:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/challenger_125_inferred/2026-08.parquet | 1,564,900 | sport_date | 2026-08-01T08:00:00+00:00 | 2026-08-31T15:35:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/challenger_125_inferred/2026-09.parquet | 2,265,431 | sport_date | 2026-09-01T03:00:00+00:00 | 2026-09-22T22:15:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/doubles/2026-05.parquet | 1,102,928 | sport_date | 2026-05-13T18:00:00+00:00 | 2026-05-31T12:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/doubles/2026-06.parquet | 1,913,834 | sport_date | 2026-06-01T09:00:00+00:00 | 2026-06-30T15:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/doubles/2026-07.parquet | 2,199,515 | sport_date | 2026-07-01T10:00:00+00:00 | 2026-07-31T22:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/doubles/2026-08.parquet | 1,275,136 | sport_date | 2026-08-01T00:00:00+00:00 | 2026-08-29T21:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/doubles/2026-09.parquet | 1,629,284 | sport_date | 2026-09-01T04:00:00+00:00 | 2026-09-22T17:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/itf/2026-05.parquet | 2,347,764 | sport_date | 2026-05-13T18:36:54+00:00 | 2026-05-31T17:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/itf/2026-06.parquet | 3,264,684 | sport_date | 2026-06-01T17:00:00+00:00 | 2026-06-30T23:15:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/itf/2026-07.parquet | 3,955,476 | sport_date | 2026-07-01T01:00:00+00:00 | 2026-07-31T19:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/itf/2026-08.parquet | 4,513,507 | sport_date | 2026-08-01T01:00:00+00:00 | 2026-08-31T18:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/itf/2026-09.parquet | 6,273,096 | sport_date | 2026-09-01T00:00:00+00:00 | 2026-09-22T20:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_juniors/2026-01.parquet | 315,067 | sport_date | 2026-01-24T00:00:00+00:00 | 2026-01-31T02:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_juniors/2026-02.parquet | 3,070 | sport_date | 2026-02-01T00:00:00+00:00 | 2026-02-01T00:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_juniors/2026-05.parquet | 97,047 | sport_date | 2026-05-31T09:00:00+00:00 | 2026-05-31T17:20:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_juniors/2026-06.parquet | 338,058 | sport_date | 2026-06-01T09:00:00+00:00 | 2026-06-06T13:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_juniors/2026-07.parquet | 467,704 | sport_date | 2026-07-04T10:00:00+00:00 | 2026-07-12T12:05:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_juniors/2026-09.parquet | 321,115 | sport_date | 2026-09-06T15:10:00+00:00 | 2026-09-12T16:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_main/2026-01.parquet | 986,594 | sport_date | 2026-01-18T00:00:00+00:00 | 2026-01-31T08:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_main/2026-02.parquet | 2,722 | sport_date | 2026-02-01T08:30:00+00:00 | 2026-02-01T08:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_main/2026-05.parquet | 968,744 | sport_date | 2026-05-24T09:05:00+00:00 | 2026-05-31T18:25:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_main/2026-06.parquet | 596,105 | sport_date | 2026-06-01T09:10:00+00:00 | 2026-06-30T19:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_main/2026-07.parquet | 347,950 | sport_date | 2026-07-01T10:00:00+00:00 | 2026-07-12T15:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_main/2026-08.parquet | 386,031 | sport_date | 2026-08-30T15:05:00+00:00 | 2026-08-31T23:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_main/2026-09.parquet | 633,250 | sport_date | 2026-09-01T00:55:00+00:00 | 2026-09-13T18:10:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_qualifying/2026-01.parquet | 282,321 | sport_date | 2026-01-11T23:00:00+00:00 | 2026-01-15T03:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_qualifying/2026-05.parquet | 301,180 | sport_date | 2026-05-19T08:00:00+00:00 | 2026-05-22T14:20:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_qualifying/2026-06.parquet | 340,767 | sport_date | 2026-06-22T10:00:00+00:00 | 2026-06-25T14:45:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/slam_qualifying/2026-08.parquet | 455,117 | sport_date | 2026-08-24T15:00:00+00:00 | 2026-08-28T17:45:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/team_exhibition/2025-09.parquet | 1,130 | sport_date | 2025-09-21T00:00:00+00:00 | 2025-09-21T00:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/team_exhibition/2025-10.parquet | 2,154 | sport_date | 2025-10-18T18:00:00+00:00 | 2025-10-18T18:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/team_exhibition/2026-09.parquet | 59,615 | sport_date | 2026-09-02T02:00:00+00:00 | 2026-09-20T17:20:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_1000/2025-09.parquet | 292,776 | sport_date | 2025-09-23T00:00:00+00:00 | 2025-09-30T00:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_1000/2025-10.parquet | 426,838 | sport_date | 2025-10-01T00:00:00+00:00 | 2025-10-31T19:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_1000/2025-11.parquet | 3,441 | sport_date | 2025-11-01T13:30:00+00:00 | 2025-11-02T14:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_1000/2026-02.parquet | 220,592 | sport_date | 2026-02-08T07:00:00+00:00 | 2026-02-21T15:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_1000/2026-03.parquet | 1,046,560 | sport_date | 2026-03-04T18:00:00+00:00 | 2026-03-29T20:45:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_1000/2026-04.parquet | 628,468 | sport_date | 2026-04-05T11:40:00+00:00 | 2026-04-30T20:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_1000/2026-05.parquet | 491,600 | sport_date | 2026-05-01T14:10:00+00:00 | 2026-05-17T15:25:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_1000/2026-08.parquet | 942,861 | sport_date | 2026-08-02T15:05:00+00:00 | 2026-08-23T23:10:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_250/2025-09.parquet | 93,025 | sport_date | 2025-09-18T00:00:00+00:00 | 2025-09-23T00:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_250/2025-10.parquet | 491,778 | sport_date | 2025-10-13T02:30:00+00:00 | 2025-10-31T15:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_250/2025-11.parquet | 133,415 | sport_date | 2025-11-01T06:00:00+00:00 | 2025-11-08T15:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_250/2026-01.parquet | 447,636 | sport_date | 2026-01-04T07:05:00+00:00 | 2026-01-17T04:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_250/2026-02.parquet | 523,974 | sport_date | 2026-02-01T11:00:00+00:00 | 2026-02-28T22:45:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_250/2026-03.parquet | 169,851 | sport_date | 2026-03-01T18:00:00+00:00 | 2026-03-31T23:20:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_250/2026-04.parquet | 232,205 | sport_date | 2026-04-01T00:45:00+00:00 | 2026-04-19T13:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_250/2026-05.parquet | 136,430 | sport_date | 2026-05-17T12:00:00+00:00 | 2026-05-23T13:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_250/2026-06.parquet | 474,136 | sport_date | 2026-06-08T09:00:00+00:00 | 2026-06-28T10:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_250/2026-07.parquet | 781,147 | sport_date | 2026-07-13T08:30:00+00:00 | 2026-07-31T23:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_250/2026-08.parquet | 89,188 | sport_date | 2026-08-01T01:00:00+00:00 | 2026-08-29T20:10:27+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_250/2026-09.parquet | 32,760 | sport_date | 2026-09-21T03:05:00+00:00 | 2026-09-22T13:45:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_500/2025-09.parquet | 219,007 | sport_date | 2025-09-19T03:00:00+00:00 | 2025-09-30T00:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_500/2025-10.parquet | 299,791 | sport_date | 2025-10-01T00:00:00+00:00 | 2025-10-26T14:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_500/2026-01.parquet | 173,473 | sport_date | 2026-01-04T01:05:00+00:00 | 2026-01-17T02:15:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_500/2026-02.parquet | 611,941 | sport_date | 2026-02-01T09:05:00+00:00 | 2026-02-28T15:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_500/2026-03.parquet | 52,415 | sport_date | 2026-03-01T00:00:00+00:00 | 2026-03-31T22:05:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_500/2026-04.parquet | 356,737 | sport_date | 2026-04-01T00:45:00+00:00 | 2026-04-19T14:10:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_500/2026-05.parquet | 116,884 | sport_date | 2026-05-17T10:40:00+00:00 | 2026-05-23T12:40:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_500/2026-06.parquet | 345,683 | sport_date | 2026-06-08T13:30:00+00:00 | 2026-06-27T09:05:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_500/2026-07.parquet | 122,205 | sport_date | 2026-07-27T14:00:00+00:00 | 2026-07-31T22:55:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_500/2026-08.parquet | 63,670 | sport_date | 2026-08-01T01:00:00+00:00 | 2026-08-29T23:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_500/2026-09.parquet | 50,750 | sport_date | 2026-09-21T03:05:00+00:00 | 2026-09-22T09:20:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_finals/2025-11.parquet | 164,416 | sport_date | 2025-11-01T15:10:00+00:00 | 2025-11-16T17:10:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_finals/2025-12.parquet | 57,262 | sport_date | 2025-12-17T11:10:00+00:00 | 2025-12-21T17:10:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_qualifying/2025-09.parquet | 83,019 | sport_date | 2025-09-21T00:00:00+00:00 | 2025-09-30T00:00:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_qualifying/2025-10.parquet | 234,595 | sport_date | 2025-10-03T00:00:00+00:00 | 2025-10-26T15:15:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_qualifying/2025-11.parquet | 25,619 | sport_date | 2025-11-01T08:00:00+00:00 | 2025-11-02T13:20:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_qualifying/2026-01.parquet | 196,646 | sport_date | 2026-01-02T00:05:00+00:00 | 2026-01-31T15:05:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_qualifying/2026-02.parquet | 257,054 | sport_date | 2026-02-01T07:05:00+00:00 | 2026-02-23T01:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_qualifying/2026-03.parquet | 338,492 | sport_date | 2026-03-01T18:05:00+00:00 | 2026-03-31T10:15:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_qualifying/2026-04.parquet | 201,124 | sport_date | 2026-04-04T09:10:00+00:00 | 2026-04-21T17:35:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_qualifying/2026-05.parquet | 123,945 | sport_date | 2026-05-04T08:05:00+00:00 | 2026-05-17T14:05:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_qualifying/2026-06.parquet | 156,297 | sport_date | 2026-06-06T10:20:00+00:00 | 2026-06-21T15:15:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_qualifying/2026-07.parquet | 179,294 | sport_date | 2026-07-11T08:00:00+00:00 | 2026-07-27T02:45:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_qualifying/2026-08.parquet | 157,827 | sport_date | 2026-08-01T14:30:00+00:00 | 2026-08-24T00:30:00+00:00 | 0/0 |  |
| data/dump/odds/polymarket/price_history/tour_qualifying/2026-09.parquet | 41,807 | sport_date | 2026-09-19T02:05:00+00:00 | 2026-09-22T10:35:00+00:00 | 0/0 |  |
| data/dump/odds/tennis_data_couk/atp/atp250/2009.parquet | 1,275 | Date | 2009-01-04 | 2009-11-01 | 21/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2010.parquet | 1,192 | Date | 2010-01-04 | 2010-10-31 | 450/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2011.parquet | 1,188 | Date | 2011-01-02 | 2011-10-30 | 5/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2012.parquet | 1,160 | Date | 2012-01-01 | 2012-10-21 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2013.parquet | 1,152 | Date | 2012-12-31 | 2013-10-20 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2014.parquet | 1,121 | Date | 2013-12-30 | 2014-10-19 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2015.parquet | 1,062 | Date | 2015-01-05 | 2015-10-25 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2016.parquet | 1,054 | Date | 2016-01-04 | 2016-10-23 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2017.parquet | 1,108 | Date | 2017-01-01 | 2017-10-22 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2019.parquet | 1,085 | Date | 2018-12-31 | 2019-10-20 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2020.parquet | 521 | Date | 2020-01-06 | 2020-11-14 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2021.parquet | 1,160 | Date | 2021-01-07 | 2021-11-13 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2022.parquet | 1,189 | Date | 2022-01-03 | 2022-10-23 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2023.parquet | 1,081 | Date | 2023-01-01 | 2023-11-11 | 3/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2024.parquet | 1,081 | Date | 2023-12-31 | 2024-11-09 | 4/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2025.parquet | 834 | Date | 2024-12-29 | 2025-11-08 | 598/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp250/2026.parquet | 598 | Date | 2026-01-04 | 2026-08-02 | 8/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2009.parquet | 366 | Date | 2009-02-09 | 2009-11-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2010.parquet | 397 | Date | 2010-02-08 | 2010-11-07 | 125/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2011.parquet | 397 | Date | 2011-02-07 | 2011-11-06 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2012.parquet | 365 | Date | 2012-02-13 | 2012-10-28 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2013.parquet | 389 | Date | 2012-10-01 | 2013-10-27 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2014.parquet | 389 | Date | 2014-02-10 | 2014-10-26 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2015.parquet | 478 | Date | 2015-02-09 | 2015-11-01 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2016.parquet | 482 | Date | 2016-02-08 | 2016-10-30 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2017.parquet | 435 | Date | 2017-02-13 | 2017-10-29 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2019.parquet | 435 | Date | 2019-02-11 | 2019-10-27 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2020.parquet | 186 | Date | 2020-02-10 | 2020-11-01 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2021.parquet | 294 | Date | 2021-03-01 | 2021-10-31 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2022.parquet | 400 | Date | 2022-02-07 | 2022-10-30 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2023.parquet | 404 | Date | 2023-02-13 | 2023-10-29 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2024.parquet | 404 | Date | 2024-02-12 | 2024-10-27 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2025.parquet | 512 | Date | 2025-02-03 | 2025-10-26 | 389/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/atp500/2026.parquet | 372 | Date | 2026-02-09 | 2026-08-03 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2000.parquet | 508 | Date | 2000-01-17 | 2000-08-28 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2001.parquet | 508 | Date | 2001-01-15 | 2001-08-27 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2003.parquet | 508 | Date | 2003-01-13 | 2003-09-07 | 389/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2005.parquet | 508 | Date | 2005-01-17 | 2005-09-11 | 4/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2007.parquet | 508 | Date | 2007-01-15 | 2007-09-09 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2008.parquet | 508 | Date | 2008-01-14 | 2008-09-08 | 7/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2009.parquet | 508 | Date | 2009-01-19 | 2009-09-14 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2010.parquet | 508 | Date | 2010-01-18 | 2010-09-12 | 127/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2011.parquet | 508 | Date | 2011-01-17 | 2011-09-12 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2012.parquet | 508 | Date | 2012-01-16 | 2012-09-10 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2013.parquet | 508 | Date | 2013-01-14 | 2013-09-09 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2014.parquet | 508 | Date | 2014-01-13 | 2014-09-08 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2015.parquet | 508 | Date | 2015-01-19 | 2015-09-13 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2016.parquet | 508 | Date | 2016-01-18 | 2016-09-11 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2017.parquet | 508 | Date | 2017-01-16 | 2017-09-10 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2019.parquet | 508 | Date | 2019-01-14 | 2019-09-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2020.parquet | 381 | Date | 2020-01-20 | 2020-10-11 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2021.parquet | 508 | Date | 2021-02-08 | 2021-09-12 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2022.parquet | 508 | Date | 2022-01-17 | 2022-09-11 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2023.parquet | 508 | Date | 2023-01-16 | 2023-09-10 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2024.parquet | 508 | Date | 2024-01-14 | 2024-09-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2025.parquet | 508 | Date | 2025-01-12 | 2025-09-07 | 381/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/grand_slam/2026.parquet | 381 | Date | 2026-01-18 | 2026-07-12 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/international/2000.parquet | 1,404 | Date | 2000-01-03 | 2000-11-20 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/international/2001.parquet | 1,412 | Date | 2001-01-01 | 2001-10-22 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/international/2003.parquet | 1,373 | Date | 2002-12-30 | 2003-10-26 | 843/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/international/2005.parquet | 1,342 | Date | 2005-01-03 | 2005-10-30 | 63/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/international/2007.parquet | 1,326 | Date | 2007-01-01 | 2007-10-28 | 60/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/international/2008.parquet | 1,259 | Date | 2007-12-31 | 2008-10-26 | 31/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/international_gold/2000.parquet | 469 | Date | 2000-02-14 | 2000-10-09 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/international_gold/2001.parquet | 461 | Date | 2001-02-19 | 2001-10-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/international_gold/2003.parquet | 398 | Date | 2003-02-17 | 2003-11-12 | 222/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/international_gold/2005.parquet | 445 | Date | 2005-02-14 | 2005-10-16 | 9/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/international_gold/2007.parquet | 398 | Date | 2007-02-19 | 2007-10-14 | 6/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/international_gold/2008.parquet | 366 | Date | 2008-02-18 | 2008-10-12 | 4/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters/2000.parquet | 567 | Date | 2000-03-13 | 2000-11-13 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters/2001.parquet | 567 | Date | 2001-03-12 | 2001-10-29 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters/2003.parquet | 567 | Date | 2003-03-10 | 2003-11-02 | 294/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters/2005.parquet | 599 | Date | 2005-03-11 | 2005-11-06 | 7/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters/2007.parquet | 559 | Date | 2007-03-09 | 2007-11-04 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters/2008.parquet | 559 | Date | 2008-03-13 | 2008-11-02 | 9/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2009.parquet | 567 | Date | 2009-03-12 | 2009-11-15 | 4/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2010.parquet | 567 | Date | 2010-03-11 | 2010-11-14 | 246/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2011.parquet | 567 | Date | 2011-03-10 | 2011-11-13 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2012.parquet | 559 | Date | 2012-03-08 | 2012-11-04 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2013.parquet | 567 | Date | 2013-03-07 | 2013-11-03 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2014.parquet | 567 | Date | 2014-03-06 | 2014-11-02 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2015.parquet | 567 | Date | 2015-03-12 | 2015-11-08 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2016.parquet | 567 | Date | 2016-03-10 | 2016-11-06 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2017.parquet | 567 | Date | 2017-01-02 | 2017-11-05 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2019.parquet | 567 | Date | 2019-03-07 | 2019-11-03 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2020.parquet | 164 | Date | 2020-08-22 | 2020-11-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2021.parquet | 512 | Date | 2021-03-24 | 2021-11-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2022.parquet | 520 | Date | 2022-03-10 | 2022-11-06 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2023.parquet | 695 | Date | 2023-03-08 | 2023-11-05 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2024.parquet | 695 | Date | 2024-03-06 | 2024-11-03 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2025.parquet | 775 | Date | 2025-03-05 | 2025-11-02 | 625/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_1000/2026.parquet | 435 | Date | 2026-03-04 | 2026-05-17 | 95/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2000.parquet | 15 | Date | 2000-11-27 | 2000-11-27 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2001.parquet | 15 | Date | 2001-11-12 | 2001-11-12 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2003.parquet | 15 | Date | 2003-11-10 | 2003-11-17 | 15/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2005.parquet | 15 | Date | 2005-11-13 | 2005-11-20 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2007.parquet | 15 | Date | 2007-11-11 | 2007-11-18 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2008.parquet | 15 | Date | 2008-11-09 | 2008-11-16 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2009.parquet | 15 | Date | 2009-11-22 | 2009-11-29 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2010.parquet | 15 | Date | 2010-11-21 | 2010-11-28 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2011.parquet | 15 | Date | 2011-11-20 | 2011-11-27 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2012.parquet | 15 | Date | 2012-11-05 | 2012-11-12 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2013.parquet | 15 | Date | 2013-11-04 | 2013-11-11 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2014.parquet | 15 | Date | 2014-11-09 | 2014-11-16 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2015.parquet | 15 | Date | 2015-11-15 | 2015-11-22 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2016.parquet | 15 | Date | 2016-11-13 | 2016-11-20 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2017.parquet | 15 | Date | 2017-11-12 | 2017-11-19 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2019.parquet | 15 | Date | 2019-11-10 | 2019-11-17 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2020.parquet | 15 | Date | 2020-11-15 | 2020-11-22 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2021.parquet | 15 | Date | 2021-11-14 | 2021-11-21 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2022.parquet | 15 | Date | 2022-11-13 | 2022-11-20 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2023.parquet | 15 | Date | 2023-11-12 | 2023-11-19 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2024.parquet | 15 | Date | 2024-11-10 | 2024-11-17 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/atp/masters_cup/2025.parquet | 15 | Date | 2025-11-09 | 2025-11-16 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2007.parquet | 508 | Date | 2007-01-15 | 2007-09-09 | 3/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2008.parquet | 508 | Date | 2008-01-14 | 2008-09-07 | 5/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2009.parquet | 508 | Date | 2009-01-19 | 2009-09-14 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2010.parquet | 508 | Date | 2010-01-18 | 2010-09-12 | 127/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2011.parquet | 508 | Date | 2011-01-17 | 2011-09-11 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2012.parquet | 508 | Date | 2012-01-16 | 2012-09-09 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2013.parquet | 508 | Date | 2013-01-14 | 2013-09-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2014.parquet | 508 | Date | 2014-01-13 | 2014-09-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2015.parquet | 508 | Date | 2015-01-19 | 2015-09-12 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2016.parquet | 508 | Date | 2016-01-18 | 2016-09-10 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2017.parquet | 508 | Date | 2017-01-16 | 2017-09-09 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2018.parquet | 508 | Date | 2018-01-15 | 2018-09-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2019.parquet | 508 | Date | 2019-01-14 | 2019-09-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2020.parquet | 381 | Date | 2020-01-20 | 2020-10-10 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2021.parquet | 508 | Date | 2021-02-08 | 2021-09-11 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2022.parquet | 508 | Date | 2022-01-17 | 2022-09-10 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2023.parquet | 508 | Date | 2023-01-16 | 2023-09-09 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2024.parquet | 508 | Date | 2024-01-14 | 2024-09-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2025.parquet | 508 | Date | 2025-01-12 | 2025-09-06 | 382/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/grand_slam/2026.parquet | 381 | Date | 2026-01-18 | 2026-07-11 | 9/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/international/2009.parquet | 969 | Date | 2009-01-04 | 2009-11-08 | 25/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/international/2010.parquet | 1,053 | Date | 2010-01-03 | 2010-11-07 | 375/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/international/2011.parquet | 1,047 | Date | 2011-01-02 | 2011-11-06 | 6/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/international/2012.parquet | 996 | Date | 2012-01-01 | 2012-11-04 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/international/2013.parquet | 1,024 | Date | 2012-12-30 | 2013-11-03 | 3/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/international/2014.parquet | 1,058 | Date | 2013-12-29 | 2014-11-02 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/international/2015.parquet | 992 | Date | 2015-01-04 | 2015-10-25 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/international/2016.parquet | 1,050 | Date | 2016-01-03 | 2016-10-22 | 4/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/international/2017.parquet | 1,019 | Date | 2017-01-01 | 2017-10-21 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/international/2018.parquet | 988 | Date | 2017-12-31 | 2018-10-20 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/international/2019.parquet | 1,013 | Date | 2018-12-30 | 2019-10-20 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/international/2020.parquet | 422 | Date | 2020-01-05 | 2020-10-25 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2009.parquet | 941 | Date | 2009-01-11 | 2009-10-25 | 14/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2010.parquet | 872 | Date | 2010-01-10 | 2010-10-10 | 361/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2011.parquet | 898 | Date | 2011-01-09 | 2011-10-09 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2012.parquet | 888 | Date | 2012-01-08 | 2012-10-07 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2013.parquet | 895 | Date | 2013-01-06 | 2013-10-06 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2014.parquet | 895 | Date | 2013-12-29 | 2014-10-05 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2015.parquet | 991 | Date | 2015-01-04 | 2015-10-24 | 3/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2016.parquet | 934 | Date | 2016-01-03 | 2016-10-22 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2017.parquet | 943 | Date | 2017-01-01 | 2017-10-21 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2018.parquet | 943 | Date | 2017-12-31 | 2018-10-20 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2019.parquet | 921 | Date | 2018-12-31 | 2019-10-20 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2020.parquet | 252 | Date | 2020-01-06 | 2020-09-21 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/premier/2023.parquet | 59 | Date | 2023-09-30 | 2023-10-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tier_1/2007.parquet | 546 | Date | 2007-01-30 | 2007-10-21 | 20/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tier_1/2008.parquet | 519 | Date | 2008-02-18 | 2008-10-12 | 7/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tier_2/2007.parquet | 461 | Date | 2007-01-07 | 2007-10-28 | 8/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tier_2/2008.parquet | 434 | Date | 2008-01-06 | 2008-10-26 | 7/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tier_3/2007.parquet | 574 | Date | 2006-12-31 | 2007-11-04 | 37/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tier_3/2008.parquet | 541 | Date | 2007-12-30 | 2008-11-02 | 21/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tier_4/2007.parquet | 387 | Date | 2007-01-01 | 2007-10-07 | 35/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tier_4/2008.parquet | 387 | Date | 2007-12-30 | 2008-10-05 | 22/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2007.parquet | 15 | Date | 2007-11-06 | 2007-11-11 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2008.parquet | 15 | Date | 2008-11-04 | 2008-11-09 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2009.parquet | 15 | Date | 2009-10-27 | 2009-11-01 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2010.parquet | 15 | Date | 2010-10-26 | 2010-10-31 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2011.parquet | 15 | Date | 2011-10-25 | 2011-10-30 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2012.parquet | 15 | Date | 2012-10-23 | 2012-10-28 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2013.parquet | 15 | Date | 2013-10-22 | 2013-10-27 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2014.parquet | 15 | Date | 2014-10-20 | 2014-10-26 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2015.parquet | 30 | Date | 2015-10-25 | 2015-11-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2016.parquet | 30 | Date | 2016-10-23 | 2016-11-06 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2017.parquet | 30 | Date | 2017-10-22 | 2017-11-05 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2018.parquet | 30 | Date | 2018-10-21 | 2018-11-04 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2019.parquet | 30 | Date | 2019-10-22 | 2019-11-03 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2021.parquet | 15 | Date | 2021-11-10 | 2021-11-18 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2022.parquet | 15 | Date | 2022-10-31 | 2022-11-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2023.parquet | 30 | Date | 2023-10-24 | 2023-11-06 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2024.parquet | 15 | Date | 2024-11-02 | 2024-11-09 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/tour_championships/2025.parquet | 15 | Date | 2025-11-01 | 2025-11-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta1000/2021.parquet | 418 | Date | 2021-03-23 | 2021-10-17 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta1000/2022.parquet | 528 | Date | 2022-02-20 | 2022-10-24 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta1000/2023.parquet | 600 | Date | 2023-02-19 | 2023-09-24 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta1000/2024.parquet | 750 | Date | 2024-02-11 | 2024-10-13 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta1000/2025.parquet | 830 | Date | 2025-02-09 | 2025-10-12 | 680/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta1000/2026.parquet | 490 | Date | 2026-02-08 | 2026-05-16 | 95/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta250/2021.parquet | 899 | Date | 2021-02-13 | 2021-11-12 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta250/2022.parquet | 926 | Date | 2022-01-04 | 2022-10-17 | 3/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta250/2023.parquet | 930 | Date | 2023-01-02 | 2023-10-22 | 3/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta250/2024.parquet | 743 | Date | 2023-12-31 | 2024-11-04 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta250/2025.parquet | 678 | Date | 2024-12-29 | 2025-11-02 | 462/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta250/2026.parquet | 521 | Date | 2026-01-04 | 2029-07-20 | 5/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta251/2021.parquet | 1 | Date | 2021-07-06 | 2021-07-06 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta252/2021.parquet | 1 | Date | 2021-07-06 | 2021-07-06 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta253/2021.parquet | 1 | Date | 2021-07-07 | 2021-07-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta254/2021.parquet | 1 | Date | 2021-07-07 | 2021-07-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta255/2021.parquet | 1 | Date | 2021-07-07 | 2021-07-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta256/2021.parquet | 1 | Date | 2021-07-07 | 2021-07-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta257/2021.parquet | 1 | Date | 2021-07-07 | 2021-07-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta258/2021.parquet | 1 | Date | 2021-07-07 | 2021-07-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta259/2021.parquet | 1 | Date | 2021-07-07 | 2021-07-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta260/2021.parquet | 1 | Date | 2021-07-07 | 2021-07-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta261/2021.parquet | 1 | Date | 2021-07-07 | 2021-07-07 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta262/2021.parquet | 1 | Date | 2021-07-08 | 2021-07-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta263/2021.parquet | 1 | Date | 2021-07-08 | 2021-07-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta264/2021.parquet | 1 | Date | 2021-07-08 | 2021-07-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta265/2021.parquet | 1 | Date | 2021-07-08 | 2021-07-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta266/2021.parquet | 1 | Date | 2021-07-08 | 2021-07-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta267/2021.parquet | 1 | Date | 2021-07-08 | 2021-07-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta268/2021.parquet | 1 | Date | 2021-07-08 | 2021-07-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta269/2021.parquet | 1 | Date | 2021-07-08 | 2021-07-08 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta270/2021.parquet | 1 | Date | 2021-07-09 | 2021-07-09 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta271/2021.parquet | 1 | Date | 2021-07-09 | 2021-07-09 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta272/2021.parquet | 1 | Date | 2021-07-09 | 2021-07-09 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta273/2021.parquet | 1 | Date | 2021-07-09 | 2021-07-09 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta274/2021.parquet | 1 | Date | 2021-07-10 | 2021-07-10 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta275/2021.parquet | 1 | Date | 2021-07-10 | 2021-07-10 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta276/2021.parquet | 1 | Date | 2021-07-11 | 2021-07-11 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta500/2021.parquet | 581 | Date | 2021-01-06 | 2021-10-24 | 2/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta500/2022.parquet | 392 | Date | 2022-01-03 | 2022-10-09 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta500/2023.parquet | 364 | Date | 2023-01-01 | 2023-10-15 | 0/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta500/2024.parquet | 474 | Date | 2023-12-31 | 2024-10-27 | 1/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta500/2025.parquet | 474 | Date | 2024-12-29 | 2025-10-26 | 343/0 | wayback |
| data/dump/odds/tennis_data_couk/wta/wta500/2026.parquet | 339 | Date | 2026-01-04 | 2026-08-03 | 6/0 | wayback |
| data/dump/players/live_tennis_api_zenodo/players.parquet | 32,678 |  |  |  | 0/0 |  |
| data/dump/players/open_tennis_data/players.parquet | 1,216 |  |  |  | 0/0 |  |
| data/dump/players/sackmann_archive/atp/atp_players.parquet | 66,912 |  |  |  | 0/0 |  |
| data/dump/players/sackmann_archive/wta/wta_players.parquet | 70,571 |  |  |  | 0/0 |  |
| data/dump/players/tennis_my_life/ATP_Database.parquet | 12,903 |  |  |  | 0/0 |  |
| data/dump/points/live_tennis_api_zenodo/points_sample_2026-06.parquet | 951,064 | timestamp_utc | 2026-06-01 12:09:27.301627 | 2026-07-01 03:32:34.811345 | 0/0 |  |
| data/dump/points/match_charting_project/metadata/charting-m-matches.parquet | 7,566 | Date | 19600529 | 20260521 | 2/0 |  |
| data/dump/points/match_charting_project/metadata/charting-w-matches.parquet | 4,264 | Date | 19790928 | 20260909 | 9/0 |  |
| data/dump/points/match_charting_project/points/charting-m-points-2010s.parquet | 357,229 | match_id[:8] | 20100108 | 20191124 | 0/0 |  |
| data/dump/points/match_charting_project/points/charting-m-points-2020s.parquet | 547,478 | match_id[:8] | 20200103 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/points/charting-w-points-2010s.parquet | 178,658 | match_id[:8] | 20100106 | 20191214 | 0/0 |  |
| data/dump/points/match_charting_project/points/charting-w-points-2020s.parquet | 353,755 | match_id[:8] | 20200106 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-KeyPointsReturn.parquet | 60,464 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-KeyPointsServe.parquet | 60,464 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-NetPoints.parquet | 59,396 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-Overview.parquet | 56,850 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-Rally.parquet | 96,706 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-ReturnDepth.parquet | 270,002 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-ReturnOutcomes.parquet | 310,496 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-ServeBasics.parquet | 45,341 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-ServeDirection.parquet | 45,341 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-ServeInfluence.parquet | 30,235 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-ShotDirection.parquet | 59,997 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-ShotDirOutcomes.parquet | 174,687 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-ShotTypes.parquet | 352,384 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-SnV.parquet | 51,300 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-SvBreakSplit.parquet | 164,871 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-m-stats-SvBreakTotal.parquet | 164,871 | match_id[:8] | 19600529 | 20260521 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-KeyPointsReturn.parquet | 34,038 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-KeyPointsServe.parquet | 34,040 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-NetPoints.parquet | 32,537 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-Overview.parquet | 28,014 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-Rally.parquet | 54,682 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-ReturnDepth.parquet | 151,813 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-ReturnOutcomes.parquet | 176,894 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-ServeBasics.parquet | 25,536 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-ServeDirection.parquet | 25,536 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-ServeInfluence.parquet | 17,024 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-ShotDirection.parquet | 33,495 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-ShotDirOutcomes.parquet | 92,845 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-ShotTypes.parquet | 185,921 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-SnV.parquet | 6,277 | match_id[:8] | 19800906 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-SvBreakSplit.parquet | 93,246 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/match_charting_project/stats/charting-w-stats-SvBreakTotal.parquet | 93,246 | match_id[:8] | 19790928 | 20260909 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2011-ausopen-matches.parquet | 179 | match_id[:4] | 2011 | 2011 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2011-ausopen-points.parquet | 31,523 | match_id[:4] | 2011 | 2011 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2011-frenchopen-matches.parquet | 194 | match_id[:4] | 2011 | 2011 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2011-frenchopen-points.parquet | 34,340 | match_id[:4] | 2011 | 2011 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2011-usopen-matches.parquet | 161 | match_id[:4] | 2011 | 2011 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2011-usopen-points.parquet | 27,309 | match_id[:4] | 2011 | 2011 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2011-wimbledon-matches.parquet | 117 | match_id[:4] | 2011 | 2011 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2011-wimbledon-points.parquet | 21,368 | match_id[:4] | 2011 | 2011 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2012-ausopen-matches.parquet | 167 | match_id[:4] | 2012 | 2012 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2012-ausopen-points.parquet | 29,001 | match_id[:4] | 2012 | 2012 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2012-frenchopen-matches.parquet | 172 | match_id[:4] | 2012 | 2012 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2012-frenchopen-points.parquet | 31,184 | match_id[:4] | 2012 | 2012 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2012-usopen-matches.parquet | 171 | match_id[:4] | 2012 | 2012 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2012-usopen-points.parquet | 30,975 | match_id[:4] | 2012 | 2012 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2012-wimbledon-matches.parquet | 140 | match_id[:4] | 2012 | 2012 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2012-wimbledon-points.parquet | 25,920 | match_id[:4] | 2012 | 2012 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2013-ausopen-matches.parquet | 179 | match_id[:4] | 2013 | 2013 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2013-ausopen-points.parquet | 31,688 | match_id[:4] | 2013 | 2013 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2013-frenchopen-matches.parquet | 186 | match_id[:4] | 2013 | 2013 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2013-frenchopen-points.parquet | 33,248 | match_id[:4] | 2013 | 2013 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2013-usopen-matches.parquet | 167 | match_id[:4] | 2013 | 2013 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2013-usopen-points.parquet | 30,353 | match_id[:4] | 2013 | 2013 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2013-wimbledon-matches.parquet | 146 | match_id[:4] | 2013 | 2013 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2013-wimbledon-points.parquet | 25,691 | match_id[:4] | 2013 | 2013 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2014-ausopen-matches.parquet | 158 | match_id[:4] | 2014 | 2014 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2014-ausopen-points.parquet | 27,659 | match_id[:4] | 2014 | 2014 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2014-frenchopen-matches.parquet | 254 | match_id[:4] | 2014 | 2014 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2014-frenchopen-points.parquet | 44,426 | match_id[:4] | 2014 | 2014 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2014-usopen-matches.parquet | 187 | match_id[:4] | 2014 | 2014 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2014-usopen-points.parquet | 33,159 | match_id[:4] | 2014 | 2014 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2014-wimbledon-matches.parquet | 253 | match_id[:4] | 2014 | 2014 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2014-wimbledon-points.parquet | 47,619 | match_id[:4] | 2014 | 2014 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2015-ausopen-matches.parquet | 209 | match_id[:4] | 2015 | 2015 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2015-ausopen-points.parquet | 38,309 | match_id[:4] | 2015 | 2015 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2015-frenchopen-matches.parquet | 208 | match_id[:4] | 2015 | 2015 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2015-frenchopen-points.parquet | 37,208 | match_id[:4] | 2015 | 2015 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2015-usopen-matches.parquet | 176 | match_id[:4] | 2015 | 2015 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2015-usopen-points.parquet | 31,442 | match_id[:4] | 2015 | 2015 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2015-wimbledon-matches.parquet | 252 | match_id[:4] | 2015 | 2015 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2015-wimbledon-points.parquet | 46,819 | match_id[:4] | 2015 | 2015 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2016-ausopen-matches.parquet | 231 | match_id[:4] | 2016 | 2016 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2016-ausopen-points.parquet | 41,312 | match_id[:4] | 2016 | 2016 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2016-frenchopen-matches.parquet | 176 | match_id[:4] | 2016 | 2016 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2016-frenchopen-points.parquet | 32,165 | match_id[:4] | 2016 | 2016 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2016-usopen-matches.parquet | 172 | match_id[:4] | 2016 | 2016 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2016-usopen-points.parquet | 30,606 | match_id[:4] | 2016 | 2016 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2016-wimbledon-matches.parquet | 126 | match_id[:4] | 2016 | 2016 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2016-wimbledon-points.parquet | 29,102 | match_id[:4] | 2016 | 2016 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2017-ausopen-matches.parquet | 237 | match_id[:4] | 2017 | 2017 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2017-ausopen-points.parquet | 43,933 | match_id[:4] | 2017 | 2017 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2017-frenchopen-matches.parquet | 242 | match_id[:4] | 2017 | 2017 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2017-frenchopen-points.parquet | 43,122 | match_id[:4] | 2017 | 2017 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2017-usopen-matches.parquet | 165 | match_id[:4] | 2017 | 2017 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2017-usopen-points.parquet | 30,067 | match_id[:4] | 2017 | 2017 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2017-wimbledon-matches.parquet | 254 | match_id[:4] | 2017 | 2017 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2017-wimbledon-points.parquet | 45,774 | match_id[:4] | 2017 | 2017 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-ausopen-matches-doubles.parquet | 126 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-ausopen-matches-mixed.parquet | 31 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-ausopen-matches.parquet | 253 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-ausopen-points-doubles.parquet | 18,084 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-ausopen-points-mixed.parquet | 3,693 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-ausopen-points.parquet | 47,540 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-frenchopen-matches-doubles.parquet | 126 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-frenchopen-matches-mixed.parquet | 30 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-frenchopen-matches.parquet | 253 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-frenchopen-points-doubles.parquet | 18,392 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-frenchopen-points-mixed.parquet | 3,533 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-frenchopen-points.parquet | 45,529 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-usopen-matches.parquet | 178 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-usopen-points.parquet | 31,851 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-wimbledon-matches.parquet | 254 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2018-wimbledon-points.parquet | 49,281 | match_id[:4] | 2018 | 2018 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-ausopen-matches-doubles.parquet | 125 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-ausopen-matches-mixed.parquet | 31 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-ausopen-matches.parquet | 254 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-ausopen-points-doubles.parquet | 18,469 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-ausopen-points-mixed.parquet | 3,287 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-ausopen-points.parquet | 46,663 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-frenchopen-matches-doubles.parquet | 124 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-frenchopen-matches-mixed.parquet | 31 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-frenchopen-matches.parquet | 252 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-frenchopen-points-doubles.parquet | 17,952 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-frenchopen-points-mixed.parquet | 3,713 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-frenchopen-points.parquet | 46,185 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-usopen-matches-doubles.parquet | 103 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-usopen-matches-mixed.parquet | 27 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-usopen-matches.parquet | 251 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-usopen-points-doubles.parquet | 14,926 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-usopen-points-mixed.parquet | 3,217 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-usopen-points.parquet | 47,893 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-wimbledon-matches-doubles.parquet | 124 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-wimbledon-matches-mixed.parquet | 46 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-wimbledon-matches.parquet | 254 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-wimbledon-points-doubles.parquet | 23,713 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-wimbledon-points-mixed.parquet | 6,757 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2019-wimbledon-points.parquet | 47,045 | match_id[:4] | 2019 | 2019 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-ausopen-matches-doubles.parquet | 125 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-ausopen-matches-mixed.parquet | 31 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-ausopen-matches.parquet | 253 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-ausopen-points-doubles.parquet | 18,320 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-ausopen-points-mixed.parquet | 3,822 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-ausopen-points.parquet | 46,530 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-frenchopen-matches-doubles.parquet | 125 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-frenchopen-matches.parquet | 254 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-frenchopen-points-doubles.parquet | 18,683 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-frenchopen-points.parquet | 46,273 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-usopen-matches-doubles.parquet | 57 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-usopen-matches.parquet | 248 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-usopen-points-doubles.parquet | 8,169 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2020-usopen-points.parquet | 45,157 | match_id[:4] | 2020 | 2020 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-ausopen-matches-doubles.parquet | 126 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-ausopen-matches-mixed.parquet | 31 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-ausopen-matches.parquet | 254 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-ausopen-points-doubles.parquet | 18,083 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-ausopen-points-mixed.parquet | 3,690 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-ausopen-points.parquet | 44,412 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-frenchopen-matches-doubles.parquet | 125 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-frenchopen-matches-mixed.parquet | 15 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-frenchopen-matches.parquet | 254 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-frenchopen-points-doubles.parquet | 17,405 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-frenchopen-points-mixed.parquet | 1,612 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-frenchopen-points.parquet | 46,313 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-usopen-matches-doubles.parquet | 125 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-usopen-matches-mixed.parquet | 30 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-usopen-matches.parquet | 253 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-usopen-points-doubles.parquet | 18,054 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-usopen-points-mixed.parquet | 3,733 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-usopen-points.parquet | 47,867 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-wimbledon-matches-doubles.parquet | 121 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-wimbledon-matches-mixed.parquet | 39 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-wimbledon-matches.parquet | 253 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-wimbledon-points-doubles.parquet | 19,493 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-wimbledon-points-mixed.parquet | 6,062 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2021-wimbledon-points.parquet | 47,106 | match_id[:4] | 2021 | 2021 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2022-usopen-matches-doubles.parquet | 125 | match_id[:4] | 2022 | 2022 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2022-usopen-matches-mixed.parquet | 31 | match_id[:4] | 2022 | 2022 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2022-usopen-matches.parquet | 252 | match_id[:4] | 2022 | 2022 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2022-usopen-points-doubles.parquet | 19,347 | match_id[:4] | 2022 | 2022 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2022-usopen-points-mixed.parquet | 3,893 | match_id[:4] | 2022 | 2022 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2022-usopen-points.parquet | 47,243 | match_id[:4] | 2022 | 2022 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2022-wimbledon-matches-doubles.parquet | 125 | match_id[:4] | 2022 | 2022 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2022-wimbledon-matches-mixed.parquet | 22 | match_id[:4] | 2022 | 2022 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2022-wimbledon-matches.parquet | 252 | match_id[:4] | 2022 | 2022 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2022-wimbledon-points-doubles.parquet | 24,329 | match_id[:4] | 2022 | 2022 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2022-wimbledon-points-mixed.parquet | 3,584 | match_id[:4] | 2022 | 2022 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2022-wimbledon-points.parquet | 46,361 | match_id[:4] | 2022 | 2022 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2023-usopen-matches-doubles.parquet | 124 | match_id[:4] | 2023 | 2023 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2023-usopen-matches-mixed.parquet | 31 | match_id[:4] | 2023 | 2023 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2023-usopen-matches.parquet | 253 | match_id[:4] | 2023 | 2023 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2023-usopen-points-doubles.parquet | 19,206 | match_id[:4] | 2023 | 2023 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2023-usopen-points-mixed.parquet | 3,785 | match_id[:4] | 2023 | 2023 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2023-usopen-points.parquet | 45,445 | match_id[:4] | 2023 | 2023 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2023-wimbledon-matches-doubles.parquet | 123 | match_id[:4] | 2023 | 2023 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2023-wimbledon-matches-mixed.parquet | 31 | match_id[:4] | 2023 | 2023 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2023-wimbledon-matches.parquet | 254 | match_id[:4] | 2023 | 2023 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2023-wimbledon-points-doubles.parquet | 17,984 | match_id[:4] | 2023 | 2023 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2023-wimbledon-points-mixed.parquet | 5,171 | match_id[:4] | 2023 | 2023 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2023-wimbledon-points.parquet | 48,676 | match_id[:4] | 2023 | 2023 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2024-usopen-matches-doubles.parquet | 125 | match_id[:4] | 2024 | 2024 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2024-usopen-matches-mixed.parquet | 30 | match_id[:4] | 2024 | 2024 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2024-usopen-matches.parquet | 253 | match_id[:4] | 2024 | 2024 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2024-usopen-points-doubles.parquet | 18,847 | match_id[:4] | 2024 | 2024 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2024-usopen-points-mixed.parquet | 3,743 | match_id[:4] | 2024 | 2024 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2024-usopen-points.parquet | 45,289 | match_id[:4] | 2024 | 2024 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2024-wimbledon-matches.parquet | 252 | match_id[:4] | 2024 | 2024 | 0/0 |  |
| data/dump/points/sackmann_archive/slam_pointbypoint/2024-wimbledon-points.parquet | 48,155 | match_id[:4] | 2024 | 2024 | 0/0 |  |
| data/dump/rankings/sackmann_archive/atp/atp_rankings_10s.parquet | 915,618 | ranking_date | 20100104 | 20191230 | 0/0 |  |
| data/dump/rankings/sackmann_archive/atp/atp_rankings_20s.parquet | 516,461 | ranking_date | 20200106 | 20251229 | 0/0 |  |
| data/dump/rankings/sackmann_archive/atp/atp_rankings_current.parquet | 36,468 | ranking_date | 20260105 | 20260608 | 0/0 |  |
| data/dump/rankings/sackmann_archive/wta/wta_rankings_10s.parquet | 621,308 | ranking_date | 20100101 | 20191230 | 0/0 |  |
| data/dump/rankings/sackmann_archive/wta/wta_rankings_20s.parquet | 412,744 | ranking_date | 20200106 | 20251229 | 0/0 |  |
| data/dump/rankings/sackmann_archive/wta/wta_rankings_current.parquet | 35,145 | ranking_date | 20260105 | 20260608 | 0/0 |  |
| data/dump/rankings/tennis_my_life/atp_rankings_2026-08-31.parquet | 2,298 |  |  |  | 0/0 |  |

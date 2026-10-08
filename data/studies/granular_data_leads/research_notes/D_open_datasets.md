# Lane D: open datasets, academic datasets and code repositories for granular professional tennis data

All sources were accessed on 24 Sep 2026. Research only; nothing here is an approved source. Supporting files were kept in the session scratchpad, not in the repository.

**Evidence labels:** [observed] = the file or API response was read; [provider claim] = the dataset's author says it; [third-party report] = someone else describes the source; [search excerpt] = from a search result; [inference] = reasoning; [not stated] = the source says nothing.

**Method:**
- **APIs, all read-only:** GitHub via `gh api` (the owner's existing CLI login, which only raises rate limits); Kaggle's public API without logging in; Hugging Face (HF); Zenodo, Harvard Dataverse, Figshare, OSF, Mendeley, arXiv, Crossref and Semantic Scholar.
- **Downloads:** partial HTTP reads of 300 KB or less; every saved file under 5 MB.
- **WebSearch:** 3 calls.
- **Interpreters:** parsing used `./python.sh`; text was pulled from two PDFs with the base interpreter `C:/Users/zerom/miniforge3/python.exe` (pypdf), because the `tennis` env has no PDF library; one R `.rds` file was read with a small scratch reader. Nothing was installed and no project file was modified.

## 0. Bottom line

1. **Biggest find: Grand Slam Hawk-Eye tracking on GitHub** (`hawkilol/tennisSlamBallTracking`, sourced from the Infosys "Court Vision" feature).
   - **Coverage:** 2,027 singles matches. Australian Open 2020–2024: 124–127 matches per draw per year, essentially the whole main draw. Roland-Garros 2019–2024: 41–113 matches per draw per year, tracked courts only.
   - **Contents:** raw per-point JSON with 3-D ball positions (hit, peak, net, bounce) for every shot, plus server and receiver positions; a processed 64-column per-point CSV.
   - **New to the project:** AO and RG 2022–2024 point data (the held Sackmann archive stops at 2021 for these two events), and the 3-D coordinates for every year.
   - **Rights red flag:** the 2022–2024 files appear to come from decrypting an encrypted Infosys API.
2. **`ryurko/hawkeye`** is an older (July 2021) scrape of the same source, apparently made before the encryption: 805 matches (AO 2020–21, RG 2019–21, a few doubles and qualifying), per-shot trajectory files and per-point files.
3. **`skoval/monash-return-impact`**: 126,455 ATP return-impact 3-D positions from 1,287 matches at 36 events, 2018 to February 2020. The only open per-point tracking file found for the ATP tour outside the Slams.
4. **The Match Charting Project pre-2010 point files exist and were never downloaded.** `charting-m-points-to-2009.csv` (38,025,307 bytes) and `charting-w-points-to-2009.csv` (6,181,461 bytes), in the same commit the held snapshot used (`1813a13`). They add points for about 2,382 matches whose metadata is held. Sackmann on the export being smaller than the website: "This is by design. I'll no longer make all matches available here."
5. **"From AO to AI" (Tennis Australia / CrowdANALYTIX, 2018) survives on GitHub:** 13,000 AO rally points with 28 Hawk-Eye-derived columns and a winner / forced error / unforced error label. No match or player identifiers, no test labels, no licence stated.
6. **The three undocumented archives are identified:** marcosjn2 (Kaggle) = SofaScore-scraped win/loss point sequences 2015–2025; TennisDB (HF) = features from an amateur swing-detection video set; st311-tennis (Kaggle) = frames from a Mendeley amateur clip set.
7. **Other:** `skoval/tennis-match-data` (2016–17 point strings that mark aces, double faults and second serves, including 15,382 ITF men's matches); several single-match shot datasets; computer-vision datasets (F3Set, RacketVision, TrackNet, TenniSet, OSL) of little use for prediction. Tennis Australia's 2023 "AO Data Slam" release of 120,000 tracking points: no public copy found.

## 1. Ranked leads

### L1. `hawkilol/tennisSlamBallTracking`: Court Vision data, AO 2020–2024 and RG 2019–2024

- **URLs:** data https://github.com/hawkilol/tennisSlamBallTracking (latest commit `f97a9b31e6`, 2025-04-08; data added in `458601a`, "add dataset files 2019-2024", 2024-10-01). Scraper and decryption code https://github.com/hawkilol/TennisCC (`src/AO_scrap_API.py`, `src/API_Decryption.js`).
- **Granularity:** tracking (3-D ball positions for every shot, player positions at the serve) and point level.
- **Per-point CSV, 64 columns, verbatim [observed]:** `point_ID, set_num, game_num, point_num, serve_num, server_id, returner_id, point_winner_id, court_side, serve_speed_kph, serve_type, fault_distance_missed_m, x_ball_serve_impact, y_ball_serve_impact, z_ball_serve_impact, rally_length, point_end_type, error_type, trapped_by_net, last_stroke_type, last_hand, last_stroke_net_height_m, winner_placement, unforcedErrorPlacement, is_break_point, is_break_point_converted, is_track_avail, x_serve_bounce, y_serve_bounce, z_serve_bounce, serve_dir, z_net_serve, x_net_serve, y_net_serve, last_ball_impact_x, last_ball_impact_y, last_ball_impact_z, last_ball_bounce_x, last_ball_bounce_y, last_ball_bounce_z, serve_return_impact_x, serve_return_impact_y, serve_return_impact_z, serve_return_net_x, serve_return_net_y, serve_return_net_z, serve_return_bounce_x, serve_return_bounce_y, serve_return_bounce_z, spin_rpm, is_fault, is_doublefault, is_tiebreak, is_ace, is_prev_doublefault, is_prev_ace, server_score, returner_score, player1, player2, p1_cum_games, p2_cum_games, p1_cum_sets, p2_cum_sets`
- **Values observed in one match (AO 2024 men's first round `MS101`):** `point_end_type` Faulty Serve, Forced Error, Unforced Error, Winner, Ace, DoubleFault; `serve_type` Slice, Flat, Kick, Pronated; `last_stroke_type` Ground, Drop, Passing, Volley, Overhead, Approach; `winner_placement` Cross Court, Down the Line; `serve_dir` Wide, T, Body; `error_type` Long, Net, Wide Error.
- **Raw JSON [observed]:** 82 keys in the first 300 KB of that match's file. `trajectoryData` is a list of `{x, y, z, position}` with `position` = hit, peak, net, bounce or last; a 14-shot rally carried a hit/peak/net/bounce set for every stroke. Positions: `serverCordinate`, `receiverCordinate`, `serveBounceCordinate`, `ballHitCordinate`, `ballPeakCordinate`, `ballNetCordinate`, `ballBounceCordinate`, `ballLastCordinate`. Ball and outcome: `ballSpeed`, `returnSpeed`, `spin`, `heightAboveNet`, `distanceOutsideCourt`, `pointEndType`, `strokeType`, `serveType`, `errorType`, `winnerPlacement`, `unforcedErrorPlacement`, `trappedByNet`. Context: `runAroundForeHand`, `rallyLength`, `cruciality`, `returnPlacement`, `breakPoint`, `breakPointConverted`, `isTieBreak`, scoreboard fields.
- **Match catalogue columns [observed]:** `year, player1, player2, player1_id, player2_id, player1_country, player2_country, player1_seed, player2_seed, court_name, court_id, num_sets_completed, match_type, match_status, match_id, tournament, league, player1_ranking, player2_ranking, player1_points, player2_points`.
- **New versus held:** AO and RG 2022–2024 coverage; in every year, 3-D serve, return and last-shot positions, spin, serve type, error type, per-shot ball positions. No Wimbledon or US Open.
- **Coverage (catalogue counts) [observed]:**

  | Draw | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
  |---|---|---|---|---|---|---|
  | AO men | – | 124 | 126 | 126 | 127 | 127 |
  | AO women | – | 126 | 127 | 126 | 127 | 127 |
  | RG men | 42 | 47 | 66 | 113 | 58 | 65 |
  | RG women | 41 | 46 | 57 | 112 | 56 | 61 |

  Match status: 1,852 completed, 137 marked "I", 38 retired. Files: 3.29 GB raw JSON and 163 MB per-point CSV; the Git repository is about 243 MB. Roughly 0.5 million per-point rows, faults as separate rows [inference]. RG covers tracked courts only; `courtvisionpython` says Court Vision "should cover all courts for the Australian Open since 2021 and all show courts for Roland Garros" [third-party report].
- **Quality caveats [observed]:** two RG 2024 samples had tracking on only 36–42% of rows (AO 2022 and 2023 samples about 100%); faults are separate rows; some faults show a serve speed of "0 KPH".
- **Access and licence:** repository licence GPL-3.0 [observed], which covers code; data rights [not stated]. README: "Scraped Hawk-Eye serve tracking dataset from the Australian Open (2020-2024) and Roland Garros (2019-2024)." [provider claim]
- **Red flag [observed]:** `AO_scrap_API.py` runs `decrypted = decryptor.update(base64.b64decode(data['response']))…` against `https://itp-ao-sls.infosys-platforms.com/prod/api/court-vision/year/2024/eventId/580/matchId/MS701/pointId/0_0_0`; `API_Decryption.js` also rotates browser user-agent strings. The `courtvisionpython` README: "Unfortunately, it seems the endpoints have been encrypted, so retrieving data no longer works." [third-party report]
- **Confidence: Medium.** Trivial to obtain; lawful use doubtful (2022–2024 files came from getting around encryption; the data belongs to Tennis Australia, the FFT and Infosys).

### L2. `ryurko/hawkeye`: 2021 scrape of the same data

- **URL:** https://github.com/ryurko/hawkeye (latest commit `981c81204f`, 2021-07-17). No licence [observed].
- **Fields [observed]:** `ball_trajectory/*.csv`: `point_ID, set_num, game_num, point_num, serve_num, strike_index, position, x, y, z`; `play_by_play/*.csv`: the same column family as L1; `misc/`: match catalogue and player ids; `example/all_djokovic_data.csv` 78.8 MB.
- **Coverage [observed], 805 matches:** AO men 2020/2021 124/126; AO women 2020/2021 126/127; RG men 2019/2020/2021 42/47/56; RG women 41/46/57; RG doubles and qualifying 13.
- **README [provider claim]:** "This repo contains tracking data in tennis, scraped from CourtVision." "These matches are from the 2019, 2020, 2021 Roland Garros and 2020, 2021 Australian Open." "We only have (x,y,z) ball locations when the ball is hit (`hit`), at the highest point of a trajectory (`peak`), as the ball reaches the net (`net`) and when the ball hits the ground (`bounce`)." "`Let` points are not available."
- **New versus held:** mostly a subset of L1; cleaner provenance because it predates the encryption [inference from dates].
- **Confidence: Medium** (obtainable; no licence).

### L3. `skoval/monash-return-impact`: ATP tour return-impact tracking, 2018–2020

- **URL:** https://github.com/skoval/monash-return-impact, file `data/position.rds` (1,322,288 bytes). No licence [observed].
- **Columns [observed]:** `match_id, X, Y, Z, serve, player, opponent, playerid, event_name, year, surface, Ad, Clay, Grass, server_n, receiver_n, ServeType, AdT, AdBody, AdWide, DeuceT, DeuceBody, DeuceWide, server_id, return_id`. `match_id` looks like `2018/352/MS001` (year / ATP tournament id / match code); `playerid` is an ATP player id.
- **Coverage [observed]:** 126,455 rows; 1,287 matches; 36 events; 84 players. Matches by year: 219 in 2018, 886 in 2019, 182 in 2020. Surface: hard 101,118 rows, clay 18,524, grass 6,813. Serve: 74,883 first serves, 51,572 second serves. The paper reports "142,803 return points played by 141 top players" (arXiv 2202.00583) [provider claim], so the public file is a subset [inference].
- **README [provider claim]:** "Using recently released tracking data summaries on the ATP Tour website of the 2D position of the ball at the time of return impact"; "The dataset includes return impact for returned points in ATP singles matches for events between 2018 and 2020."; "This project is sponsored by Zelus Analytics".
- **New versus held:** entirely new (no non-Slam tracking is held); narrow width (no point outcome or score).
- **Confidence: Medium** (easy to get, rights unclear; ATP site terms bar systematic retrieval).

### L4. Match Charting Project pre-2010 point files: in the public export, not in the held snapshot

- **Files at `1813a13` (2026-09-18) [observed]:** `charting-m-points-to-2009.csv` 38,025,307 bytes; `charting-w-points-to-2009.csv` 6,181,461; `charting-m-points-2010s.csv` 36,475,702; `charting-m-points-2020s.csv` 56,590,483; `charting-w-points-2010s.csv` 18,179,925; `charting-w-points-2020s.csv` 35,592,435.
- **History [observed]:** the pre-2010 files first appear in commit `e5bf7a2` ("thru 11 sep 2023"); men's last updated 2026-05-25, women's 2026-09-18.
- **Schema [observed]:** the same 14 columns as the held files (`match_id, Pt, Set1, Set2, Gm1, Gm2, Pts, Gm#, TbSet, Svr, 1st, 2nd, Notes, PtWinner`). The files end with the 1960 RG final, coded as score only. In 11 samples of 60 KB, 97.1% of men's rows and 98.8% of women's rows had shot codes.
- **Missing [observed]:** of 7,566 men's and 4,264 women's metadata rows, 1,996 and 420 have no points; 1,966 and 416 of those are pre-2010. About 2,382 matches should gain points; 34 matches from 2010 on have no points, unexplained.
- **Why the website has more:** GitHub issue #9 (2019-05-04), JeffSackmann: "**This is by design. I'll no longer make all matches available here.**" The follow-up question ("For whom will the entire dataset be available?…") was not answered. The Tennis Abstract charting page [observed] shows "18,267 matches!", "2,844,323 points!", "10,753,733 shots!" (men 10,119, women 8,148) and "**Much of the data is available, free, to researchers.**" So about 6,400 charts are website-only by design, and the men's export also lags the site [inference].
- **Licence:** CC BY-NC-SA 4.0, as for the held MCP data. **Confidence: High** (same source and licence; about 44 MB).

### L5. "From AO to AI: Predicting How Points End in Tennis" (Tennis Australia and CrowdANALYTIX, January 2018)

- **Copies [observed]:** https://github.com/ml874/Predicting-How-Points-End-in-Tennis (commit `952f2bc2bc`), folder `tennis_data/`: `mens_train_file.csv` 1,044,761 bytes; `womens_train_file.csv` 1,055,127; `mens_test_file.csv` 414,716; `womens_test_file.csv` 209,877; `AO2AI_Hackathon_DataDictionary.docx` 8,777; `AUS_SubmissionFormat.csv`. Also `dineshjrd/Tennis_end_points` (same files, different line endings [inference], plus a CrowdANALYTIX PDF), `priyanks179/tennis-class-prediction` (men's training only), `spikey007/Tennis-Data-Set` (merged and renumbered [inference]). No Kaggle or HF copy.
- **Granularity:** one row per point of three or more shots, with Hawk-Eye-derived features of the last two shots.
- **Columns, verbatim [observed]:** `rally, serve, hitpoint, speed, net.clearance, distance.from.sideline, depth, outside.sideline, outside.baseline, player.distance.travelled, player.impact.depth, player.impact.distance.from.center, player.depth, player.distance.from.center, previous.speed, previous.net.clearance, previous.distance.from.sideline, previous.depth, opponent.depth, opponent.distance.from.center, same.side, previous.hitpoint, previous.time.to.net, server.is.impact.player, id, train, outcome, gender`
- **Data dictionary [observed]:** "The dataset includes point outcomes of rallies only (where the number of shots hit exceeds two…). All points were played at a past Australian Open." "Both the men's and women's data have 5,000 points for training. There will be 2,000 points for testing the men's and 1,000 points for testing the women's solutions." Speed m/s, net clearance cm (can be negative), distances metres. `hitpoint` F, B, V, U; `outcome` W, FE, UE.
- **Rows [observed]:** men's train 5,000 (UE 2,118 / W 1,684 / FE 1,198); women's train 5,000 (UE 2,258 / W 1,668 / FE 1,074); men's test 2,000 and women's test 1,000, unlabelled. Rallies 3 to 38 shots.
- **Anonymisation [observed]:** no match, player, set, score, date or year; the AO year is unstated, probably 2017 or earlier [inference].
- **Context [search excerpt]:** "the single biggest release of multi-camera tracking data obtained from the Hawk-Eye System in the history of tennis… 750 data scientists… analysed 10,000 points."
- **Licence:** not stated. **Confidence: Medium** (2.7 MB, unlicensed, not joinable to matches or players).

### L6. `skoval/tennis-match-data`: 2016–17 point strings with ace, double-fault and second-serve codes

- **URL:** https://github.com/skoval/tennis-match-data (commit `224836560e`, 2017). No licence [observed].
- **Fields [observed]:** `date, start_time, tournament, type, tour, draw, server1, server2, winner, pbp, score, adf_flag, round, surface, duration, status, server1_age, server2_age, server1_ioc, server2_ioc, server1_rank, server2_rank`.
- **README [provider claim]:** matches "validated using the Universal Match Object to insure that point progressions produce scores that match 'official' scores"; codes S, R, A (ace), D (double fault); "lowercase letters indicate that the point was played on a 2nd Serve."
- **Coverage [observed]:** `ITF-Men_Singles_pbpx` 15,382 matches, 2016-05-04 → 2017-02-10, 496 tournaments, 2,101 qualifying matches, all with second-serve codes; `ATP_Singles_pbpx` 1,313 (2016-05 → 2017-02); `WTA_Singles_pbpx` 1,199 (2016-01 → 2017-02). Also ITF women, doubles, WTA 125K, Davis Cup, Fed Cup and juniors (file sizes only).
- **New versus held:** the held Sackmann point strings mark aces and double faults but never second serves (0% lowercase in `pbp_copy_2018`) [observed]; this adds serve number for May 2016 to February 2017. Upstream source [not stated].
- **Confidence: Medium** (public, about 26 MB, unlicensed, short window).

### L7. Kaggle `marcosjn2` "Tennis Point-by-Point Match Dataset (2015–2026)": SofaScore win/loss point sequences

- **Metadata [observed]:** `atp-matches.jsonl` 145,024,923 bytes and `wta-matches.jsonl` 118,527,233 bytes; MIT label; no description; published 2025-08-29.
- **Schema [observed from four 300 KB partial reads]:** `key`; `meta.{event_id, gender, source, date, created_at_utc, version}`; `tournament.{name, slug, unique_name, ground_type, points}`; `round.{name, number}`; `players.home/away.{id, name, slug, country_alpha3}`; `sequence.{match_winner, set_sequence}`; `sequence.sets[].{set_number, set_winner, game_sequence}`; `sequence.sets[].games[].{game_number, is_tiebreak, server_side, server_name, point_sequence, point_sequence_server_relative, game_winner}`.
- **Provenance [observed]:** every sampled record has `"source": "sofascore"`.
- **Coverage:** samples 2015-06-20 to 2025-06-28 [observed]; qualifying included; tournament points none, 250, 500, 1000 and 2000; no Challenger or ITF seen [observed]; roughly 24,000 ATP and 23,000 WTA matches [inference].
- **New versus held:** 2018–2022 tour-level point-winner sequences; each point only 1/0 (no aces, double faults, serve number or timestamps).
- **Confidence: Low** (the MIT label is not credible for SofaScore-scraped data).

### L8. F3Set tennis shot labels

- **Source:** https://github.com/F3Set/F3Set, `data/f3set-tennis/`: `train.json`, `val.json`, `test.json` (about 10 MB), `events.txt`, `elements.txt`, `videos.csv` (151 rows) [observed].
- **Label elements (29) [observed]:** `near, far, deuce, middle, ad, serve, return, stroke, fh, bh, gs, slice, volley, smash, drop, lob, T, B, W, CC, DL, DM, II, IO, approach, in, winner, forced-err, unforced-err`.
- **Coverage [observed]:** 72 men's and 79 women's videos, 2003–2023, mostly 2019–22; 40 AO, 40 US Open, 29 Wimbledon, 11 Olympics. Video names follow MCP match ids, and **101 of 151 match held MCP match ids**; it largely duplicates MCP content, adding frame timing.
- **Confidence: Medium to obtain, low value.**

### L9. Single-match shot and tracking datasets (low value)

| Dataset | Content [observed] | Licence |
|---|---|---|
| Kaggle `robseidl` AO 2019 final (Djokovic–Nadal), hand-annotated | `events.csv` (865 shots with hitter and receiver positions); `points.csv` (142 points) | CC BY 4.0 |
| Kaggle `robseidl` Queen's 2019 doubles | same structure plus ball bounces | CC BY-ND 4.0 |
| `glad94/Djokovic-Nadal_RG2022_Data` (RG 2022 quarter-final) | `events.csv` with shot side, shot type, X/Y, outcome, serve speed | CC0 |
| `opengoalapp/tennis_tracking` (RG men's final, probably 2021) | Court Vision shot trajectory and per-point files | MIT label on the code |
| RG 2025 final ball-tracking exercise (e.g. `AdambHatim/tennis-hit-bounce-detection`, 313 point files, copied in ~10 repos) | per frame x/y in broadcast pixels, visible, air/hit/bounce | not stated; described as a "Sport Scientist Computer Vision & ML Exercise" [third-party report] |

### L10. Computer-vision datasets (low value for prediction)

| Dataset | What it has |
|---|---|
| RacketVision (AAAI 2026; HF `linfeng302/RacketVision`, MIT) | 431 tennis rally clips; ball pixel positions and racket keypoints; source events not stated |
| TrackNet (arXiv 1907.03698) | "the men's singles final at the 2017 Summer Universiade" (81 clips, 20,844 frames) plus "9 additional videos … partially labeled"; frame, visibility, X, Y, flying/hit/bouncing. Not a tour event |
| TenniSet | "five singles matches from the 2012 London Olympics"; event labels plus 746 point captions; MIT |
| OSL Dallas 2026 (HF) | 5 Dallas Open 2026 broadcasts, 3 labelled with 1,946 swing timestamps; no licence stated |
| OSL / soccernetpro tennis (HF, AGPL-3.0) | swing-timing clips |
| Kaggle `hamolyavlad` | RG 2023 serve clips as tensors; 48.7 GB; licence unknown |
| Kaggle `greg1982` | Wimbledon 2017 final clips of winners and non-winners |
| Vid2Player3D | not released: "license issues of the video footage" |

## 2. Dead ends

- HF Tang1166/TennisDB: 877 feature files and 876 amateur swing clips labelled "tennis swing" (网球挥拍), 25 fps, named by initials and dates. Not professional.
- Kaggle joekinder/st311-tennis: `Frames/…/Indoor Field/Cross-court Shot/Top-View/ICT01/frame_*.jpg`, matching the Mendeley 75m8vz7jr2 amateur clips.
- `skoval/deuce`: bundles only Sackmann and tennis-data.co.uk data (slam point-by-point 1,032,076 rows, 124,247 point strings, 670,790 MCP points, odds, Elo). No tracking.
- `courtvisionr` / `courtvisionpython`: code only; endpoints encrypted.
- `petertea96` repos (Tea & Swartz, *Annals of Operations Research* 2022, DOI 10.1007/s10479-021-04481-7): code only; their RG Court Vision JSON "was saved in early December 2020".
- Papers whose data is not public: Space-Time VON CRAMM (US Open 2019 tracking); Fernando et al. 2019 (AO 2012 Hawk-Eye); SportsNGEN; arXiv 2110.01527; Fitzpatrick et al. 2023 (Wimbledon 2016–18 Hawk-Eye; article page 403).
- AO Data Slam 2023 ("120,000 points"; "Predict the next serve"): no copy on GitHub, Kaggle or HF.
- TrackNetV2 and V3: badminton. HF Tennis_3D: synthetic-looking trajectories. CalTennis: practice and match play from 40 players, not tour broadcasts. HF `yonggest`, `racketpose`, `racketdb`; Kaggle `tenis-backview`: amateur.
- Zenodo: coaching, medical and aggregate items only. Dataverse: nothing new. Figshare 31059832: 4,669 hand-coded 2021 Slam points from the quarter-finals on. OSF 9c2d8: MCP-derived; pjuw8: match level only.
- Code-only repos: `glad94/infotennis`, `MatAci` (MatchBeats scraper), `mitch-mooney/tennis`, `RinoCattabiani`.
- Wimbledon and US Open SlamTracker caches, and MatchBeats dumps, for 2022+: none found.

## 3. Access log (summary)

- GitHub API: MCP tree, README, data dictionary, file history, issues #9, #16, #18, #22, #25, commit `1813a13`; about 45 repository searches and 14 code searches; trees and READMEs of about 60 repositories.
- Partial reads from GitHub: MCP pre-2010 files (20 KB head, 3 KB tail, 11 × 60 KB samples); first 300 KB of one hawkilol JSON; five hawkilol per-point CSVs in memory.
- Full small downloads (each under 5 MB, scratchpad only): AO to AI (6 files, 2.78 MB); skoval `position.rds` and the `ITF-Men` / `ATP` / `WTA_Singles_pbpx.csv` files; hawkilol match catalogue and one match's per-point CSV; RG 2025 exercise `ball_data_1.json`; F3Set README, `elements.txt`, `videos.csv`; robseidl AO 2019 (111 KB); OSF 9c2d8 Excel (3.87 MB); the tennisabstract.com charting page (4.53 MB).
- Kaggle (no login): view and list calls for 7 datasets, about 30 searches; partial reads of the marcosjn2 ATP file (bytes 0–299,999; 72,000,000–72,299,999; last 300,000) and WTA file (59,000,000–59,299,999).
- Hugging Face: 18 searches, 15 metadata calls; TennisDB zip last 300 KB plus three small internal files; RacketVision small JSON and card; OSL Dallas card; one Tennis_3D sequence file.
- Other APIs: Mendeley, Zenodo, Dataverse, Figshare, OSF, arXiv (9 queries), Crossref, Semantic Scholar.
- Web pages fetched: TrackNet and TenniSet PDFs, the ausopen.com "AO Data Slam" article, the CrowdANALYTIX contest page (empty). Blocked with 403: on-the-t.com, medium.com, tandfonline.

## 4. Leads passed to other lanes

1. Infosys Court Vision: AO endpoint seen in code `https://itp-ao-sls.infosys-platforms.com/prod/api/court-vision/year/{y}/eventId/580/matchId/{id}/pointId/0_0_0`, now AES-encrypted; RG and ATP endpoints catalogued in `glad94/infotennis/references/api-info/`. The lawful route is a licence or research agreement with Tennis Australia, the FFT or Infosys.
2. Tennis Australia has released Hawk-Eye data twice through CrowdANALYTIX (2018, about 10–13k points; 2023 "AO Data Slam", 120,000 points): ask about research access and joinable identifiers.
3. ATP Stats Centre: Kovalchik's project used return-impact tracking summaries from atptour.com; check whether they still exist and on what terms. Zelus Analytics, the sponsor, is a possible commercial contact.
4. Wimbledon / Hawk-Eye: Sheffield Hallam's study of Wimbledon 2016–18 (302 men's and 139 women's matches) suggests an academic data-sharing route.
5. Tennis Abstract: about 6,400 charts are website-only "by design"; researcher access could be requested from Sackmann.
6. SofaScore: marcosjn2 shows a full scrape back to 2015 is technically possible; the terms are the blocker.
7. Peter Tea's SFU thesis (etd21466) probably documents the RG Court Vision fields for 2019–20 [inference].

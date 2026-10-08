# Lane B: open datasets, code repositories and archives for serve speed (7 Oct 2026)

**Status: research, not a decision.** Everything was read on 7 October 2026. Nothing was bought, no account was opened, no form was submitted, nobody was contacted, and nothing was decrypted. GitHub was read through the owner's `gh` login (read-only; it only raises rate limits). Samples were kept in the session scratchpad (`…/scratchpad/laneB/`); nothing but this file was written to the repository.

**Question.** Where can match-level (or finer) serve speed, above all the mean speed of first serves (ideally first serves in) and the number of serves behind it, be had for the project's gaps? This lane covers open datasets, repositories that commit data, and archives. Gaps, in the brief's order:
1. ATP tour level outside the Slams, May 2025 to today;
2. WTA tour level outside the Slams, any year;
3. Australian Open 2025, Roland-Garros 2025 and 2026;
4. ATP tour level outside the Slams, 2015–2020;
5. Challenger and WTA 125.

**Evidence labels:** **[observed]** = I saw the field and its values (or its absence) in a file or response; **[documented]** = the provider's schema, code or README; **[claimed]** = marketing or the publisher's own description; **[third-party]** = someone else reports it; **[search]** = a search-engine excerpt only; **[inference]** = my reasoning. All URLs were accessed on 7 Oct 2026.

**Sibling lane.** Lane A1 (`A1_tour_public.md`, same folder) covers official sites, Flashscore, aggregators and broadcasters. It also lists `serve-and-volley`. Where its findings bound this lane's, I cite them rather than repeat them.

## 0. Bottom line

* **Gap 1 is largely fillable from one open repository: GitHub `msolonskyi/ManTennisData`.**
  * It holds the ATP Stats Centre's rendered **Key Stats speeds** as plain CSV: per player per match, "Max Speed", "1st Serve Average Speed" and "2nd Serve Average Speed" in km/h, next to first serves in and the rest of the box score [observed].
  * **Coverage:** ATP tour level and Challengers, from late 2021 to the week before last; head commit `4e2d39f99e`, 4 Oct 2026; committed weekly [observed].
  * **New to the project:** 2,896 tour-level matches with speed from tournaments starting on or after 14 Apr 2025 (1,952 main draw, 944 qualifying), plus 735 Challenger matches [observed]. The held decrypted copies end in April 2025 (earlier lanes).
  * **Checked against held data:** for all 333 player-matches where the held SirGenkii key stats carry a speed (Jan–Apr 2025), its first- and second-serve averages are **identical**. Against the held point-level speeds, the figure behaves as the mean of first serves in: median +0.57 km/h, 73.5% of 702 player-matches within 1 km/h [observed].
  * **Limits:** no Slams; no match dates (only tournament dates and round); many events lack speed in some years (Barcelona, Munich and Houston in every year read; Halle 2024–26; Hamburg 2025–26) [observed]. It is a scrape of atptour.com pages rendered in Chrome, under an MIT label with no data licence [observed]. atptour.com's terms forbid systematic retrieval (earlier lanes).
* **Gap 2 (WTA, outside the Slams): nothing open.**
  * No public dataset with WTA non-Slam speed was found on GitHub, Kaggle, Hugging Face, Zenodo, Figshare, Dataverse or OSF [observed, absence within these searches].
  * The WTA API's match stats have no speed key [observed: one response; lane A1 saw the same for `stats` and `advanced-stats`]. So no official-site scrape can contain WTA speed [inference].
* **Gap 3 (AO 2025, RG 2025–26): nothing useful.**
  * The only open copies with speed found are 26 AO 2025 men's main-draw matches (`henrynye/M4R`, api-tennis JSON) and 7 (`KacWNK`, Livesport JSON), match level only [observed].
  * ManTennisData has no Slam speed. No 2025–26 copy of the Sackmann Slam point files, the AO or RG Infosys feeds, or Court Vision exists in the places searched [observed, absence].
* **Gap 4 (ATP 2015–2020): nothing open.**
  * ManTennisData has 0 speed values before 2021 in 12,000–14,000 rows a year [observed]. Its scraper reads the same rendered pages, so the ATP site itself lacks them [inference; lane A1 reports the same from the 2019 JSON].
  * The academic Hawk-Eye studies found (2003–2008 tournaments; one ATP 250 over three years; Dubai 2013) did not publish their data [third-party/search].
* **Gap 5 (Challenger): partial, 2026 only.** ManTennisData has speed for 690 Challenger matches in 2026 (16 events since May 2025: Monastir 2025, then in 2026 Zagreb, Prostějov, Nottingham, Poznań, Roehampton and others) and about 45–83 a year in 2022–25 [observed]. Nothing for WTA 125.
* **Re-checked and still unchanged** [observed]:
  * the Hugging Face `atlas-polybot/atp-pipeline-handoff` (`ea3d94d`, 19 Jun 2026), and no public "main repo" behind it;
  * the forks of `glad94/infotennis`, `SirGenkii/infotennis`, `glad94/infotennis_v2`, `hawkilol/*` and `Aneeshers/tennis-sackmann-archive`: no data after June 2026 (Sackmann mirrors) or April 2025 (Infosys).

## 1. Finds

### F1. `msolonskyi/ManTennisData`: ATP Stats Centre Key Stats speeds, Oct 2021 – Oct 2026 (main find)

* **Where.** https://github.com/msolonskyi/ManTennisData, "ATP and DC Tennis Results and Statistics" [observed, GitHub API]:
  * owner `msolonskyi` (no display name on the profile; account from 2015, 8 public repositories); repository created 14 Jun 2021; 6 stars, 0 forks;
  * licence label MIT (repository); no data licence or provenance note in the 201-byte README;
  * head `4e2d39f99e`, 4 Oct 2026, "atp update 2026-10-04".
* **Update cadence** [observed, commit history]. One commit every Sunday at about 14:10 UTC through 2025 and 2026. Older seasons are revised too: `atp/matches_2025.csv` was last changed on 30 Aug 2026; `matches_2022.csv` has 20 commits.
* **Collector** [observed, code]. https://github.com/msolonskyi/tennisAnalyzer (branch `developer`, head `12e64cd5ca`, 20 Apr 2026; MIT label):
  * `python/loader/store_atp_stats.py` saves each atptour.com stats page through a Chrome browser (`_request_url_by_chrome`);
  * `python/loader/stats_atp_loader.py` parses the rendered HTML (`div[@class='speedkmh1 label']`): "Max Speed", "1st Serve Average Speed", "2nd Serve Average Speed";
  * so the ATP's own page script decrypts the Infosys files in the browser, and the repository keeps the rendered numbers [inference]. The owner does not decrypt anything himself [observed in the code read].
* **Files** [observed]: `atp/matches_1999.csv` … `matches_2026.csv` (1.6–5.1 MB each, 102.6 MB in all), `atp/tournaments.csv`, `atp/players.csv`, and the Davis Cup equivalents under `dc/`.
* **Speed fields, per match, both players** [observed]: `win_/los_fastest_first_serves_kmh` (the page's "Max Speed"), `win_/los_average_first_serves_kmh`, `win_/los_average_second_serve_kmh`. `win_/los_fastest_second_serve_kmh` exists but is never filled.
  * **The serves behind the average:** `win_/los_first_serves_in` and `…_first_serves_total` sit in the same row.
  * **Also:** winners, forced and unforced errors, net points.
  * **Keys:** ATP player codes (`winner_code`, `loser_code`), ATP tournament id and match code (inside `stats_url`, e.g. `…/stats-centre/archive/2026/747/ms015`), stage (`stadie_id`: Q1, R32, F…). These are the same keys as Tennis My Life and the Infosys copies.
  * **No match date:** only the tournament's `start_dtm` and `finish_dtm`.
* **Coverage: matches with an average first-serve speed for at least one player, by year and series** [observed; `mantd_detail.py`; "1000" = Masters, "atp" = 250/500, Finals and team events, "ch" = Challenger, "gs" = Slams]:

  | Year | 1000 | atp | ch | gs |
  |---|---:|---:|---:|---:|
  | 2014–2020 | 0 | 0 | 0 | 0 |
  | 2021 | 74 / 707 | 169 / 2,167 | 0 / 6,330 | 0 / 956 |
  | 2022 | 585 / 718 | 878 / 2,353 | 83 / 8,895 | 0 / 956 |
  | 2023 | 910 / 959 | 914 / 2,137 | 47 / 9,484 | 0 / 956 |
  | 2024 | 922 / 959 | 1,495 / 2,179 | 47 / 10,053 | 0 / 956 |
  | 2025 | 954 / 1,049 | 730 / 1,980 | 45 / 10,508 | 0 / 956 |
  | 2026 (to Beijing/Tokyo, starting 30 Sep) | 811 / 842 | 841 / 1,641 | 690 / 9,629 | 0 / 955 |

  * 10,195 match rows with speed in 2021–26; 10,057 have both players' values.
  * The 2021 values start in October (Stockholm, Antwerp, Vienna, Paris, the Finals), as in `serve-and-volley` (lane A1, §3.4).
* **The gap window** [observed]:
  * **From tournaments starting on or after 1 May 2025:** tour level 2,776 matches with speed of 4,190 rows (main draw 1,870 of 2,716); Challenger 735 of 16,641; Slams 0 of 1,672.
  * **After the held SirGenkii copy (tournaments starting on or after 14 Apr 2025):** 2,896 tour level (1,952 main draw, 944 qualifying) plus 735 Challenger.
  * **Madrid 2025:** 120 of 131, falls in that window.
  * **Monte-Carlo 2025:** 75 of 76 with speed; the held SirGenkii copy has only its first 32 matches.
* **Which events, 2023–26** (matches with speed / rows; tour level; from the per-event pivot in `mantd_detail.py`) [observed]:
  * **Always, or nearly always, filled:** Indian Wells, Miami, Madrid, Rome, Monte-Carlo, Montreal/Toronto, Cincinnati (87/131 in 2025), Shanghai, Paris, Washington, Winston-Salem, Eastbourne, Los Cabos, Chengdu, Beijing, Vienna, Basel, Stockholm, Hong Kong, Almaty, the ATP Finals.
  * **Never filled in the years read:** Barcelona, Munich, Houston, Estoril, Laver Cup, United Cup.
  * **Filled in some years only:**

    | Event | 2023 | 2024 | 2025 | 2026 |
    |---|---|---|---|---|
    | Halle | 41/43 | 0/43 | 0/43 | 0/43 |
    | Hamburg | 0/42 | 41/43 | 0/43 | 0/43 |
    | Rotterdam | 41/43 | 42/43 | 0/43 | 43/43 |
    | Brisbane | – | 47/49 | 0/49 | 0/49 |
    | Dubai, Doha, Acapulco | 26–31 of 39–43 | 37–39 | 0 | 40–42 |
    | Stuttgart, 's-Hertogenbosch, Mallorca, Gstaad, Båstad, Kitzbühel, Tokyo | mixed | filled | 0 | 0 |
    | Buenos Aires, Rio, Santiago, Montpellier | 0 | 0 | 0 | filled |

  * **Reading [inference]:** the never-filled clay events fit lane A1's finding that the Stats Centre took speed only from Hawk-Eye installations. The year-to-year switching at grass and hard events (Halle, Rotterdam, Dubai) does not fit a fixed installation, so some gaps may be page or scraper failures. This could be settled against the held decrypted copy for 2022–24.
* **When the speeds appeared** [observed, file history]:
  * every snapshot of `matches_2025.csv` up to 5 Oct 2025 (`bcda598a53`) has **no** speed at all;
  * by 16 Nov 2025 (`38b89e4576`) it has 1,726. The loader's commits of 19 Oct – 9 Nov 2025 ("ARP STATS processing was improved", "11.2025 fixes were added") fit speed parsing being added then and back-filled to 2021 [inference].
  * **In 2026 the lag is under a week.** The 30 Aug 2026 snapshot already had Winston-Salem (final 29 Aug) at 55/59, and the 4 Oct snapshot has Beijing at 36/38.
* **Cross-checks against data the project holds** (read-only; `verify_mantd.py`) [observed]:
  * **SirGenkii key stats** (`data/raw/gap_sources/sirgenkii/backup_sql/infotennis4_atp_key_stats.sql`, match level `set_n = 0`):
    * 333 player-matches carry a speed in both sources (tournaments 336, 360, 403, 404, 410, 4462);
    * **all 333 are equal** for the first-serve average, and all 333 for the second-serve average;
    * the key stats use −999 for missing.
  * **SirGenkii rally analysis** (one row per point, `serve` = 1 or 2, `serve_speed`; servers inferred from aces and double faults by game parity):
    * the key-stats first-serve average minus the mean speed of points played on the first serve: median +0.51 km/h, 75.8% within 1 km/h (339 player-matches);
    * ManTennisData minus the same mean: median +0.57, 73.5% within 1 km/h (702 player-matches);
    * one outlier is −187 km/h.
    * **[inference]** "1st Serve Average Speed" is the mean speed of first serves **in**, rounded. Its `first_serves_in` column is the count behind it (a median of 4 more than the rally rows that carry a speed).
* **Quality** [observed]:
  * of 20,252 player values, 31 are below 120 km/h (minimum 14) and one is above 230 (232);
  * filter these, as the main session now does for Flashscore (40–270 km/h);
  * rows can exist with full box-score stats and blank speed.
* **Overlap with held data:**
  * 2021–24 overlaps the Hugging Face Infosys copy (2021–24), which has point-level speeds;
  * Jan – mid-Apr 2025 overlaps SirGenkii;
  * mid-April 2025 onward is new;
  * **Challengers:** whether the held Infosys Challenger rows (2021–24) carry speed was not checked. The handoff study says only that they classify aces and double faults [not determined]. Challenger speeds from 2025 on are new either way.
* **Licence and terms:**
  * MIT label on the repository; the numbers are ATP/Infosys data [observed];
  * atptour.com's terms forbid "Systematic retrieval of data" and wagering use (earlier lanes, `docs/research/granular-data-leads/…`; not re-read today).
* **Confidence: high** on content and accuracy (exact agreement with the held copy); **medium** on fitness for use (rights, and event gaps that may be partly the scraper's).
* **Next steps (options, not decisions):**
  1. Pin `4e2d39f99e` and keep `atp/matches_2021.csv` … `2026.csv` plus `tournaments.csv` and `players.csv` (about 32 MB) in the gitignored raw area, with a receipt.
  2. Join to Tennis My Life, or the data map, by (year, ATP tournament id, the pair of ATP codes) for match dates.
     * Rolling 14- and 364-day windows need the leak-proof clock (`timing.parquet`).
     * The feature is a player's own matches in order, so it is safe by construction once dated.
  3. Weight by `first_serves_in`; drop values outside about 120–240 km/h.
  4. Repeat the equality check on 2022–24 against the Hugging Face Infosys copy. It also tells whether event-year gaps (Halle 2024, Hamburg 2025) are in the source or the scraper.
  5. Re-pull weekly. A row's speed can arrive weeks after the match (the late-2025 backfill), so for live use the project would need its own capture.

### F2. `serve-and-volley/atp-world-tour-tennis-data`: rendered Key Stats, Oct 2021 – 2022 (copy known to lane A1)

* **Where.** https://github.com/serve-and-volley/atp-world-tour-tennis-data, head `a92c6192c5` (28 Aug 2023), 222 stars, 109 forks; no licence file. Lane A1 reports CC BY 4.0 per the README [third-party: lane A1].
* **Files** [observed]:
  * `csv/3_match_stats/match_stats_extended_2021.csv`: 257 rows, 7 events;
  * `match_stats_extended_2022.csv`: 1,547 rows, 35 events;
  * no header.
* **Fields** [observed]: winner and loser max, average first- and second-serve speed (km/h and mph), net points, winners, unforced errors.
* **Fill** [observed]: 246 and 1,439 rows with the winner's first-serve average above 0. There are impossible values (maxima of 460, 878 and 905 km/h).
* **Copies:** `chboudry/PariTennis` `data_scrapped/atp_matchs-stats-advanced.csv` (1,804 rows = the same two files) [observed]. Of 109 forks, the three pushed after Aug 2023 add no extended file [observed]:
  * `datasets/atp-world-tour-tennis-data`: a 2018 datahub snapshot;
  * `mccodycasey`;
  * `dsw225`.
* **Value:** a subset of F1 and of the held Infosys copy. Useful only as a second plain-text check.

### F3. `henrynye/M4R`: api-tennis.com JSON, ATP tour, Aug 2022 – Jan 2025

* **Where** [observed]: https://github.com/henrynye/M4R, head `7b0a523235` (7 Aug 2025), 224 MB, no licence. It appears to be a university research project (prediction and betting) [inference from file names].
* **Contents** [observed]:
  * `matches_api_info/<id>_matches_api_info/*.json`: 6,950 files, 325 MB, for 64 ATP tour events (folders are BetsAPI ids mapped to api-tennis keys);
  * dates from 23 Aug 2022 (US Open) to 21 Jan 2025 (Australian Open);
  * each file is the api-tennis "event" object: `pointbypoint` (score per point, no serve number), `scores`, `statistics`.
* **Speed** [observed]:
  * `statistics` rows have `stat_name` "Average 1st Serve Speed" / "Average 2nd Serve Speed", e.g. `"185 km/h"`, at match level only (`stat_period: match`);
  * in a 41-file sample spread over the id range, no file before January 2025 has them; statistics blocks appear from March 2024;
  * **all 337 January-2025 files** were read: 56 have speed. These are Hong Kong 30 of 36 (all 9 qualifying) and AO 2025 men's main draw 26 of 115; none at Brisbane, Adelaide or Auckland.
* **Value:** 26 AO 2025 matches (gap 3). It is also evidence that api-tennis.com, a paid vendor (earlier lanes: $40–120 a month), passes on a Flashscore-style speed statistic from January 2025 [inference].
* **Confidence:** high on content, low on value.

### F4. `KacWNK/Bachelor_Thesis-…`: Livesport (Flashscore) statistics, ATP 2024 – Jan 2025

* **Where** [observed]: https://github.com/KacWNK/Bachelor_Thesis-predicting_results_of_the_tennis_matches_using_machine_learning_models, head `006940c870` (23 Apr 2025), MIT label.
* **Files** [observed]: `raw_data/livesport/match_details_2024.json` (9.2 MB, 2,752 ATP main-draw matches, 31 Dec 2023 – 9 Nov 2024) and `match_details_2025.json` (215 matches, 29 Dec 2024 – 17 Jan 2025). The statistic labels are Livesport's.
* **Speed** [observed]:
  * 2024: "Average 1st/2nd Serve Speed" on **1** of 2,752 matches (a Shanghai match). "Distance Covered (metres)" is on 200.
  * January 2025: 34 of 215 (Hong Kong 27 of 27, AO 7 of 103).
* **Value:** corroborates lane A1's finding that Flashscore's 2024 ATP speeds are almost absent and its 2025–26 ones sporadic. Gives 7 AO 2025 matches.

### F5. Davis Cup speeds (aside)

`msolonskyi/ManTennisData` `dc/matches_YYYY.csv` carries the same speed columns. 95 matches have speed in 2023, 99 in 2024 and 0 in 2025 [observed]. This is not a project gap.

## 2. Status by gap

| Gap | Open source with speed | Matches | Evidence |
|---|---|---|---|
| 1 ATP non-Slam, May 2025 → today | ManTennisData | 2,776 tour-level (Masters 1,318 / 1,422; 250/500/Finals 1,458 / 2,768) from 1 May 2025; 2,896 from 14 Apr 2025 | observed |
| 2 WTA non-Slam | none found | 0 | observed absence (searches §5); WTA API has no speed key (observed) |
| 3 AO 2025 | henrynye (api-tennis), KacWNK (Livesport) | 26 + 7 men's main-draw matches, match level; women none | observed |
| 3 RG 2025, RG 2026 | none | 0. `3573b4n/roland-data-garros` (RG 2026, refreshed every 15 min) has results only | observed |
| 4 ATP non-Slam 2015–2020 | none | 0. ManTennisData has none before Oct 2021 | observed |
| 5 Challenger | ManTennisData | 735 from May 2025 (690 in 2026); 45–83 a year in 2022–25 | observed |
| 5 WTA 125 | none | 0 | observed absence |

## 3. Leads for other lanes (not open datasets)

* **atptour.com rendered Stats Centre pages show "SERVICE SPEED"** (Max Speed, 1st and 2nd Serve Average Speed) [documented: two scrapers' code].
  * `msolonskyi/tennisAnalyzer` renders them in Chrome.
  * `maninka123/Tennis-tour-dashboard` `scripts/[Test] apt_recent_match_data.py` reads them through the r.jina.ai rendering proxy and parses a "SERVICE SPEED" section.
  * Neither was run here.
  * This is the route behind F1, and the project could repeat it for live capture. That is the official-feed lane's call, under atptour.com's terms.
* **api-tennis.com** (paid) returns "Average 1st/2nd Serve Speed" in its event statistics: ATP observed from January 2025 (F3) [observed].
  * `Stattrackrr/stattrackr` `lib/tennis/apiTennis.ts` maps "Average 1st serve speed", "Average 2nd serve speed" and "Distance covered metres" for both tours [documented in code].
  * WTA coverage is not observed.
* **EdgeLab** (dev.to posts, June 2026) claims "serve speed datasets" sold on Gumroad, built from "the ATP's official speed data and WTA records" [claimed]. Provenance unverified; the posts look machine-written [inference]. Paid lane only, low confidence.
* **Decryption code exists in public repositories:**
  * `nipunagarwalla/courtside` (`backend/scrapers/infosys/decrypt.py`, handles the `{lastModified, response, data}` envelope; created 18 Jul 2026);
  * `hawkilol/TennisCC`.
  * Both are code only, with no data committed [observed]. Not used.

## 4. Dead ends (checked today)

**GitHub, code and data**
* **Content pipelines and app caches:**
  * `robertyang87/tennislive` (17 GB, a social-media content pipeline): 3 Flashscore `df_st_1.txt` statistics files in 2026 (Tiafoe–Michelsen, Djokovic–Medvedev Beijing 2026 semi-final, one more); no dataset.
  * `maninka123/Tennis-tour-dashboard`: its WTA stats cache has no speed.
  * `sharp-signals/Tennis`: player caches only.
  * `Stattrackrr/stattrackr`: code only.
  * `LHBUSA/tennis`, `thekasser/tennis-wta-atp`, `TNM91/tennis-data` (amateur league app).
* **Scrapes with stats but no speed:**
  * `NoiseQuotient/ATP-Match-Data-Scraper-2025`: 3,268 ATP 2025 matches with the site's box score, net points, winners and errors, but no speed columns [observed].
  * `Anmaya1856/Tennis-Monte-Carlo-Kalshi`: `atp.db` comes from `/-/Hawkeye/MatchStats/Complete`, whose JSON has no speed key [observed, sample `temp.json`, Monte-Carlo 2026 final].
  * `Shawnzhang01-bit/ATP-Tennis-Serve-Analysis-Paper` (2024 serve data): no speed column.
  * `DSArevalo4/ATPtour`, `choukroun-gabriel/ATP_Scraper_Project_ITC2020`, `gmalbert/tennis-predictions`, `nick-benelli/Tennis-Data-Pipeline`, `riddlejack/Alcaraz`, `LuckyLoser91/TennisCourtLog`, `FBruzzesi/atp_stats_webapp`, `Francois-b-24/tennis-analytics`, `Rodrig972/tennis_stats`, `joco66sk/tennis-stats-app`: no "speed" in the heads of their largest data files [observed, `speed_scan.py`].
* **Code only:**
  * `Gdkff/async_tennis_project_for_airflow` (tennis24 statistics parser);
  * `douglasbc/tennis_model` (Flashscore and OnCourt ingestion; OnCourt's paid database has `FAST` and `A1S` fields per its code);
  * `nnikolovskiii/tennis-atp-scraper` (MongoDB);
  * `glad94/infotennis_v2` (MotherDuck warehouse behind the owner's token; no public share in the README);
  * `kaushikilango/BaselineData`, `fragiovis/ATP-oracle`, `acpuchades/apt-learn`, `jacopobortolo/TennisStatsV2`, `lfavole/rolandgarros-scores` (Infosys proof of concept), `Aitor-Quint-04/TennisMatrix` (data sample only).
* **Slam and Roland-Garros 2025–26:**
  * `3573b4n/roland-data-garros`: RG 2026 draws and results, no statistics.
  * Single matches only: `Smee18/QSA-Project` and `tanguycesar/Roland-Garros-Final-Analysis` (RG 2025 final positions); the RG 2025 hit/bounce exercise repositories (broadcast pixels, known).
  * Code search for Sackmann file names `2025-ausopen-points.csv`, `2025-frenchopen-points.csv`, `2026-…`: 0 hits. Caveat: code search skips files over 384 KB, so this is weak evidence.
* **Forks re-checked:** `menceladam/infotennis` (Elo model branch only); `Dvago432` and the others identical; no forks of `SirGenkii`, `infotennis_v2` or `hawkilol`. The 11 newest `Aneeshers/tennis-sackmann-archive` forks are all pushed at 25 Jun 2026 [observed].
* **atlas-polybot "main repo":** code search for `atp-pipeline-handoff`, `infosys_deep`, `flashscore_gql_stats`, `DATA_COLUMN_GUIDE` and `atlas-polybot` finds nothing related; the Hugging Face organisation has 1 dataset [observed].

**Kaggle** (26 searches; views of 14 datasets; partial reads of 3 files, 5 reads in all)
* `minhducnguyen9705/tennis-match-dataset` (7 GB): Sackmann-derived features, no speed [observed head].
* `ehallmar/a-large-tennis-dataset-for-atp-and-itf-betting` (2018): ATP-site box score, no speed [observed head].
* `diphibnh/tennis-matches-814047-matches`: results only.
* No speed in any of these:
  * `karimmaj` (tennis-data.co.uk);
  * `mahmoudehab6677` AO 2026 (results);
  * `guillemservera` (Sackmann);
  * `mohammadkumail110` (Tennis Abstract);
  * `thedevastator` WTA 2016–18 (Sackmann);
  * `gianvitonesca9`, `antoniosinner`, `nehaahuja1`, `anianih`.
* Not a tour source: `hamolyavlad/tennis-serve-speed-estimation-512` (48.7 GB of RG 2023 serve clips as tensors).
* Slam-only, held via SlamTracker: `rewantbhriguvanshi` Wimbledon 2024.
* No hits at all for "flashscore", "livesport", "hawk-eye tennis" or "tennis match statistics 2025".

**Hugging Face** (20 searches, 243 datasets listed; 13 inspected)
* `AaditTennis/ATP-Tennis-Matches-Dataset-2015-to-2025` (and its `EmmanuelTimilehi` twin): results only.
* `Neuromediator/tennis-dashboard-data`: a Sackmann-based DuckDB and models.
* `mvpeav/tennis-predictions`: predictions only.
* `bensynapse/atp-2015-results`: Live Tennis API sample.
* Not tour data: `fulgence10`, `groundhog2107`, `LGG100` (robotics).
* Known: `alifend910/tennis_points.json`, momentum datasets (Wimbledon 2023).
* `atlas-polybot` unchanged.

**Research repositories and papers**
* **Zenodo, Figshare, Dataverse, OSF/SHARE** (4 queries each): coaching, biomechanics and medical studies; the Zenodo "ATP Tennis dataset" (10245175: season leaderboards 2020–23).
* **Figshare 32082720:** WTA in-match serve kinematics from video, no speed table.
* **Figshare 9560204 and 9560012:** ATP 250 and multi-event ball-tracking studies; the PDFs only.
* **Figshare 20797555:** "Revisiting loss aversion" (Dubai 2013 serve speed and location): article only.
* **HAL 01636404 and 01975336:** Hawk-Eye 2003–2008, 1,729 matches; no data release found [search].

**Web and forums** (5 WebSearch calls, 1 WebFetch)
* No Reddit or forum post sharing serve-speed tables.
* Tennis Abstract's jsfrags have Slam-only speeds (lane A1).

**WTA API** (1 request)
* `api.wtatennis.com/tennis/tournaments/2051/2026/matches/LS014/stats`: 4 rows (match and three sets), 32 keys, none about speed [observed].

## 5. Search log (7 Oct 2026)

* **GitHub code search, 79 queries** (`laneB/search_log.jsonl` holds 78 of them with totals and hits; one more was a direct 100-hit listing of "Average 1st serve speed").
  * **Speed field names:** "Average 1st serve speed" (72), "Average 2nd serve speed", "1st serve average speed" (6), "avg 1st serve speed", avg_first_serve_speed, first_serve_avg_speed, avg_1st_serve_speed, 1st_serve_speed, FirstServeSpeed, averageServeSpeed, fastest_serve, serve_speed_kph (2,816), "serveSpeed" atp (388), Speed_KMH, average_first_serves_kmh (54), fastest_first_serves_kmh, "1st Serve Average Speed", speedkmh1.
  * **Hosts and routes:** itp-atp-sls, itp-ao-sls, itp-rg, prod-scores-api.ausopen, rolandgarros.com/api, api.wtatennis.com (with speed, with stats), Hawkeye/MatchStats, match-beats, rally-analysis, keystats, court-vision, stats-centre/archive/2025 and /2026, match-stats/archive/2026.
  * **Decryption:** infosys decrypt, court-vision decrypt, match-beats decrypt.
  * **Flashscore feed markers:** "SG÷Average", "SG÷Aces".
  * **api-tennis labels:** "Atp Singles"/"Wta Singles" with "Average 1st Serve Speed".
  * **OnCourt fields:** A1S_1 FAST_1.
  * **File names:** filename:2025-ausopen-points.csv and 6 others.
  * **atlas-polybot folder names.**
* **GitHub repository search, 25 queries:** flashscore tennis, tennis24, livesport, atptour, atp scraper/stats, wta scraper/match statistics, tennis data/dataset/stats (pushed since mid-2025), hawkeye tennis, serve speed, tennis serve, roland garros 2025, australian open 2025, roland garros data, ausopen data, court vision, slamtracker, grand slam point by point.
* **GitHub reads:** metadata and trees of about 60 repositories; fork lists of 8; file histories of `ManTennisData` (2 files) and `tennisAnalyzer` (1). Several hundred core API calls (the hourly counter had reset before it could be read).
* **raw.githubusercontent.com downloads** (each file under 6 MB, 105 MB in all, scratchpad only):
  * ManTennisData `atp/matches_2014–2026.csv` and `tournaments.csv` at `4e2d39f99e`, plus 6 older snapshots of `matches_2025.csv` and `matches_2026.csv`, and DC 2023–25;
  * henrynye: 41 sampled files plus all 337 from January 2025;
  * KacWNK: 2 JSON and 2 CSV;
  * serve-and-volley: 2 CSV;
  * chboudry: 2 CSV;
  * NoiseQuotient: 1 xlsx;
  * Anmaya1856: scraper and sample JSON;
  * maninka123: 2 scripts and 2 caches;
  * Shawnzhang01: 1 xlsx;
  * RG 2026 dashboard: CSVs and scraper;
  * msolonskyi: loader code.
* **Kaggle** (anonymous public API): 26 searches plus a 300-row "tennis" listing by update date; 14 dataset views; 5 partial reads of signed storage URLs (6–80 KB; two zip members decoded in memory).
* **Hugging Face Hub API:** 20 searches plus one author listing; 13 dataset views, with their READMEs or reports.
* **Zenodo, Figshare, Harvard Dataverse, SHARE/OSF:** 4 queries each, plus 4 Figshare and 1 Zenodo record reads.
* **WebSearch:** 5 calls ("average first serve speed" dataset; reddit serve-speed spreadsheet; RG/AO 2025 point-by-point; ATP 2016–19 Hawk-Eye dataset; site:reddit.com serve speed). **WebFetch:** 1 (dev.to EdgeLab post).
* **Official API:** 1 request to api.wtatennis.com (200, 2.2 KB).
* **No 429, challenge or block was met.**

## 6. Scratchpad files (not in the repository)

`…/scratchpad/laneB/`:
* **Helpers:** `gh_search.py`, `gh_repo.py`, `speed_scan.py`, `kaggle_search.py`, `kaggle_view.py`, `hf_view.py`, `repo_search.py`.
* **Checks:** `henrynye_sample.py`, `henrynye_late.py` (→ `henrynye/late_summary.csv`), `mantd_check.py`, `mantd_detail.py` (→ `mantd/speed_rows_2021_2026.csv`, 10,195 rows), `verify_mantd.py`.
* **Logs:** `search_log.jsonl`, `repo_log.jsonl`, `kaggle_log.jsonl`, `repo_search_results.jsonl`.
* **Samples:** under `mantd/`, `henrynye/`, `kac/`, `sv/`, `chb/`, `noise/`, `anmaya/`, `rg26/`, `tennislive/`, `misc/`, `kaggle/`, `hf/`.

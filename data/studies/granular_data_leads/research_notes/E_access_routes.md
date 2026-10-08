# Lane E: can rows 9–13 actually be obtained, publicly or by paying? (24 Sep 2026)

**Owner direction, 24 Sep 2026 (verbatim):** "See if you can obtain their results publically or a PAID service. An "ask them to see if you can" is not viable path for our data extraction. If it says no scraping but the data is public, that doesnt count. We will disregard that suggestion."

**How it was applied here:**
* Asking a provider or author for permission, a research licence or a copy is not treated as a route.
* A no-scraping clause on data the site serves publicly is not treated as ruling the source out. This follows the owner's 23 Sep decision on SofaScore and TennisLive. The terms are still recorded, and the reading is open to correction.
* Buying counts. Self-serve purchases (a published price, card checkout) are kept apart from sales-led licences. A licence that allows the project's use only with the vendor's written consent counts as an ask, as in the parallel rows 2–6 follow-up.

**Scope:** the five sources in rows 9–13 of [the leads page](../../../../docs/research/granular-data-leads/README.md): TDI Tennis Results, the SirGenkii fork, the Monash return-impact file, `skoval/tennis-match-data` and From AO to AI.
* The synthesis is [TDI and open data](../../../../docs/research/granular-data-leads/access-routes-tdi-and-open-data.md).
* Rows 2–6 (Slam feeds, WTA) are in [access routes](../../../../docs/research/granular-data-leads/access-routes.md).

**Evidence labels:** [observed] = read today; [provider claim]; [third-party report]; [search excerpt]; [inference]; [not stated].

## 0. Verdict per source

| Row | Source | Public route | Paid route | Verdict |
|---|---|---|---|---|
| 9 | **TDI Tennis Results** (ATP Tour and Challenger points since 2025) | **Partial.** The site lists only the last ~93 days (from about 24 Jun 2026). Every later match can be captured going forward. Old pages keep their points, but nothing public lists their ids: 634 from the Wayback Machine, plus single matches found by search. No published copy exists anywhere | **None licensed.** Sportradar sells the same fields only as live bet-settlement markets (ATP 250+ singles, no Challengers, no archive) to bookmakers and prediction-market platforms. Self-serve options: an Apify scraper of the same site ($18.75 per 1,000 matches, same window); Live Tennis API tags from 12 Sep 2026 only | Obtainable from 24 Jun 2026 onward. **January 2025 to June 2026 is not obtainable in bulk** from TDI |
| 10 | **SirGenkii fork** (decrypted ATP, Jan–Apr 2025) | **Yes**, a GitHub download. Also **a far larger public copy of the same Infosys data**: Hugging Face `atlas-polybot/atp-pipeline-handoff`, 2021–2024, ≈37,300 ATP Tour, Challenger and qualifying matches, with Court Vision tracking for 4,570 tour-level matches | None | Obtainable. 2021–Apr 2025 is covered by the two copies; May 2025 onward exists only in the encrypted ATP files |
| 11 | **Monash return impact** (ATP 2018–20) | **Yes**, 1.3 MB. No fuller release exists; the polybot Court Vision files would let return impacts be derived for 2021–24 [inference] | None | Obtainable |
| 12 | **`skoval/tennis-match-data`** (2016–17, second serves marked) | **Yes.** It is a fork of `TennisVisuals/tennis-match-data` (Charles Allen), which holds a little more. The upstream feed is unnamed, and the data has not been updated since Feb 2017 | None | Obtainable; a closed dataset |
| 13 | **From AO to AI** (AO Hawk-Eye features) | **Yes**, 2.7 MB. **It can now be joined:** a 2019 Tennis Australia release (`camroach87/etc3250-kaggle`, AO 2017–18, ≈53,900 points) has match and point ids. 10,795 of the 13,000 rows link to it, which also recovers labels for 1,218 of the 3,000 unpublished test rows | None | Obtainable, and mostly joinable |

## 1. TDI Tennis Results: the public route

### What the site lets a client list [observed]

* **The listing is a rolling window of about 93 days, measured by timestamp.**
  * `?date=2026-06-24` listed 45 matches.
  * `?date=2026-06-23` listed 1, that day's last match, at 17:47 UTC on 24 Sep.
  * The 24 Sep pass saw an older date fall back silently to today's list.
* **The filters are held to the same window.**
  * The listing's URL state (nuqs, server-rendered) is `tournamentId`, `playerId`, `date`, `sort`, `display` and `filter`.
  * `?playerId=` for Adam Walton returned 18 matches, 24 Jun–23 Sep 2026. His Brisbane 2025 match (`dd5b89e8…`, whose page still serves points) was not among them.
  * Adding `&date=2025-01-01` returned no matches.
  * The tournament filter lists 85 tournaments. They appear to be the window's own (Mallorca, Winston-Salem and Hangzhou among them) [inference]. The player filter lists 2,719 players.
* **The site offers nothing else that lists matches.**
  * `/robots.txt`, `/sitemap.xml` and `/sitemap-index.xml` return the app shell.
  * The only routes are the listing, `/en/results/{id}` and five information pages.
  * The tRPC client (`/api/trpc`, header `x-trpc-source: nextjs-react`) is configured in the layout. None of the 12 current bundles or 54 archived ones (May 2025 onward, from the Wayback Machine, decompressed where needed) calls a named procedure; only the layouts mention the endpoint. The pages fetch on the server. No procedure names were guessed.
  * Match ids are random version-4 UUIDs, so they cannot be derived from ATP match codes.
* **Old match pages keep their points.**
  * A May 2025 id recovered from the Wayback Machine (Draper v Alcaraz, Rome, `2025#416#MS006`) returned HTTP 404 with 127 points.
  * Those points carry `outcome`, `totalShots`, `winningShotType`, `errorType` and `situation`.
  * This matches the 24 Sep pass (10 of 10 older pages, back to 31 Dec 2024).
* **Page titles carry the ATP match code** on every page checked and in search results, for example `Tiafoe vs Walton | 2025#339#MS020 | Tennis Results`. That gives an exact join to ATP ids, but only in the TDI-to-ATP direction.

### Where ids from before the window can be found

| Source | Match ids from before 24 Jun 2026 | Evidence |
|---|---|---|
| Wayback Machine | **634**: 6 captured match pages, plus the listings in 9 homepage captures (May 2025: 145; Oct 2025: 1; Nov 2025: 134; Feb 2026: 83; Mar 2026: 131; Apr 2026: 140). The Mar/Apr 2025 and May 2026 captures carry no links | [observed]; list in [tdi_wayback_match_ids.csv](../tdi_wayback_match_ids.csv) |
| Common Crawl | **None.** All 21 crawls from CC-MAIN-2025-05 to CC-MAIN-2026-39 answer "No Captures found" for `results.tennisdata.com/*` and `*.tennisdata.com` | [observed] |
| Search engines | Some match pages are indexed under their titles, e.g. "Hurkacz vs Mensik \| 2025#416#MS010 \| Tennis Results". That allows a lookup one match at a time, which is presumably how the 24 Sep pass found its ten old ids. It is not a bulk list | [search excerpt] |
| ATP payloads saved on 24 Sep (Hawk-Eye stats, the app's live gateway, Infosys) | None; no version-4 UUIDs at all | [observed] |

### Verdict on the public route

* **Obtainable:**
  * everything in the window (from about 24 Jun 2026);
  * every later match, if the listing is read at least once every three months (daily or weekly in practice);
  * the 634 archived ids;
  * single matches found by search.
* **Not obtainable in bulk:** January 2025 to June 2026. The pages still exist, but nothing public lists their ids.
  * [Inference] At roughly 60 matches per Challenger event (singles, doubles and qualifying) and 80 per tour event, that period holds on the order of 20,000 matches. The archived ids are a few percent of it.
* **Scale of a window crawl** [inference from two days observed: 45 and 132 matches]: several thousand pages of 0.4–2 MB. At one request every two to three seconds, that is a few hours.
* **Terms** (unchanged from the 24 Sep pass): no scraping or text and data mining "for any purpose, including … statistical models or AI systems"; personal, domestic use only; an EU text-and-data-mining opt-out. The database owners are TDI Database (UK) and TDI Database (EU).

### The same data by another public door (needs a separate decision)

The ATP's Infosys Stats Centre files (row 14 of the leads page) are addressed by ATP match code: `…/match-beats/{year}/{tournament}/{match}/data.json`. The ids are deterministic, so they can be listed from the ATP calendars and draws, unlike TDI's.

* **Coverage** [observed, 24 Sep]: files exist for tour level and for Challenger main draws and qualifying.
* **Fields** [third-party report]: per point, serve 1/2, result (A, DF, W, UE, FE), stroke, rally and serve speed.
* **Already-decrypted copies cover most of the history, but not TDI's period** (§3):
  * the polybot dump holds 2021–2024;
  * the SirGenkii dump holds January–April 2025.
* **The catch for May 2025 onward:** only the encrypted files remain. The key method is published by third parties. Decrypting goes beyond ignoring a no-scraping clause, so it is left to the owner. Nothing was decrypted.

## 2. TDI and its data: paid routes

From a vendor search run in parallel: 51 web searches plus fetches of TDI, Sportradar, Live Tennis API, Apify, marketplace and tracking-vendor pages. Nothing was signed up for or bought. Its payloads are in the session scratchpad.

**Bottom line:** no licensed product sells TDI's per-point outcome data to a buyer like this project. What can be bought is either a scraper of TDI's own site or data that starts in September 2026.

* **Sportradar is TDI's exclusive distributor.**
  * TDI stories [observed]: Sportradar won "the global ATP data and betting streaming rights starting 2024", "a six-year rights cycle beginning in 2024" (13 Mar 2023). The rights cover "global data and streaming rights for betting, and media data rights, for all ATP Tour and ATP Challenger Tour events" (12 Dec 2023).
  * A Polymarket release of 3 Aug 2026 names Polymarket the ATP's official prediction-market provider, with "Official real-time data and odds for all matches delivered by TDI's exclusive distribution partner, Sportradar" [provider claim, via summariser].
* **The only commercial outlet for the per-point outcome fields is Sportradar's "ATP Players & Micro Markets"** in its Unified Odds Feed [observed: docs page, spec PDF, roadmap].
  * **Markets:**
    * 1292 serve outcome ("point after rally / ace / double fault");
    * 1293 point outcome ("… winner / … error");
    * 1294 total shots ("Total number of completed shots in the rally");
    * 1295 last stroke;
    * 1483 error type ("net / out / no error").
  * The stroke definitions match TDI's definitions page word for word [inference: same source].
  * **Coverage:** "exclusively available for… ATP 250, ATP 500, ATP 1000, Nitto ATP Finals, Next Gen ATP Finals", men's singles, from 17 Feb 2025 (the error-type market from 13 Oct 2025). "Not available for Challenger events". A roadmap slide lists "Sep 2026: ATP Challenger Tour Coverage Expansion", not marked released.
  * **Form:** live bet-settlement messages, re-requestable only within a recovery window. There is **no archive**.
  * **Access:** "please contact your dedicated sales representative", so bookmakers and prediction-market platforms only.
  * **Licence (Sportradar "Official ATP Addendum", 2 Dec 2024)** [observed]:
    * an ITIA data-sharing agreement;
    * "return or destroy any Licensed Materials" at the end;
    * "not… acquire or use any unofficial TDI feeds; (ii) collate data".
* **TDI's own "Tennis Data Platform"** [observed and provider claim].
  * A page last updated 20 Feb 2025 says it launched "In January" with "a comprehensive archive of historical data and… an open 'sandbox' environment".
  * There is no link, sign-up or documentation. None of 33 likely subdomains resolves. Certificate-transparency logs show only the apex, `www.` and `results.`.
  * Nothing to buy was found.
* **Tennis IQ** (the ATP's Hawk-Eye insights) is open to ATP and Challenger players and ATP coach members [provider claim]. That is eligibility, not a purchase.
* **Live Tennis API** (self-serve) [observed at v1.13.49, 24 Sep 2026].
  * `serve` and `outcome` were "Added 2026-09-12". Tour events were "First measured… from the week of 2026-09-22".
  * The 22 Sep re-join covers only matches the service streamed itself. There is no backfill, and "a reconstruction carries no clock and no tags at all".
  * **Prices:** core Pro at $29.99 a month, which includes bulk monthly downloads; history passes at $49 for a month or $399 for a year. Bulk files carry the tags only from `schema_version` 2 (months built from 22 Sep 2026).
  * **Terms §3:** "(a) Resell, redistribute… as a competing data feed or bulk dataset… (c) Scrape, cache, or store the data beyond what is reasonably necessary to operate your application".
* **Apify `sian.agency/tennis-point-by-point-scraper`** (self-serve) [observed; rechecked in this lane].
  * **Price:** "$18.75 / 1,000 match records" (up to $75 on Apify's free plan).
  * **Output:** TDI's own fields (`pointBreakdown` with `outcome`, `serve`, `totalShots`, `winningShotType`, `errorType` and `situation`), under titles in TDI's "A vs B | Year#Event#Match | Tennis Results" form. TDI is never named.
  * **Coverage:** it finds matches through TDI's player directory, which reaches back only about 93 days (§1). It therefore adds no history over scraping the site directly [inference].
  * 192 users; created 22 Jul 2026.
  * **Examined on 25 Sep 2026 without an account**, through Apify's public API (`/v2/acts/sian.agency~tennis-point-by-point-scraper`, `/v2/actor-builds/pUkyw1ffoqUYg0C1g`: README, changelog, input schema) [observed].
    * **Operations:** `discover-players` ("about 2,600 players"), `discover-tournaments`, `discover-matches` and `discover-tournament-matches` (match lists, not billed), `scrape-matches` (by player) and `scrape-match-ids` (any match ids, up to 250 a run).
    * **No date input.** Its directories are TDI's filter lists, so discovery reaches only TDI's ~93-day window. Supplied ids can be older, and TDI still serves old pages.
    * **ITF and WTA are not covered.** The changelog claims "any ATP, WTA, Challenger or ITF event", and the README says coverage is "strongest on ATP Challenger and ITF events". TDI's directory held 85 tournaments on 24 Sep, all ATP Tour or Challenger.
    * **Output:** TDI's `ExpandedPointDetails` point objects and statistics rows ("40–90 statistic rows" a match), plus `completedAtUtc`. The sample is a 6 Jul 2026 Challenger qualifying match.
    * **Price per match record by tier:** FREE $0.075; BRONZE $0.025; SILVER $0.021875; GOLD and above $0.01875. Plus $0.05 (free) or $0.005 per actor start.
      * [search excerpt] Apify's blog and third-party guides map Bronze to the Starter plan, Silver to Scale and Gold to Business. Apify's own pricing documentation does not state the mapping.
    * **Free plan:** "25 players or tournaments per discovery run, 5 matches per player, and 5 matches per run, up to 30 runs a day". Direct REST calls need a paid plan.
    * **Operation:** source code hidden; requests go through "our own residential proxy network".
    * **Runs:** 1,174 in all; in the last 30 days 349 succeeded and 11 failed. The last run started on 25 Sep 2026.
* **Nothing else:**
  * **Marketplaces with nothing relevant:** Datarade (odds only), Snowflake (Stats Perform schedules and results), AWS Marketplace, RapidAPI, Opendatabay, SportsDataIO, BigDataBall, TheSportsDB, Sportmonks, Oddin. None sells ATP points with outcome, rally or serve number.
  * **Infosys data:** no seller or scraper was found for MatchBeats, Rally Analysis or Court Vision.
* **Tracking (the paid counterpart of rows 10, 11 and 13):** nobody sells per-shot ATP, WTA or Slam tracking to a buyer outside the federations and bookmakers.
  * Hawk-Eye: "partners".
  * TennisViz: demo or call-back only.
  * Golden Set Analytics: "selected clients" (a 2019 blog: £80,000 a year).
  * Bolt6 and PlayReplay: hardware.
  * Teamworks/Zelus: no tennis.
  * Sportradar's Slam tracking: live only.

## 3. The four GitHub datasets: still downloadable [observed, 24 Sep 2026, `gh api`]

| Row | Repository | Status today | Files | Licence | Last push |
|---|---|---|---|---|---|
| 10 | `SirGenkii/infotennis` (fork of `glad94/infotennis`) | Public, not archived | `backup_sql/`: `infotennis4_atp_rally_analysis.sql` 21.3 MB, `…_stroke_analysis.sql` 9.2 MB, `…_court_vision.sql` 1.9 MB, `…_key_stats.sql` 1.65 MB, `…_results.sql` 0.3 MB, `…_calendars.sql` 9 KB; all from commit `1bb7527dda` (7 Apr 2025) | MIT, covering code only | 11 Apr 2025 |
| 11 | `skoval/monash-return-impact` | Public | `data/position.rds` 1,322,288 bytes (the repository is 445 MB in all, so fetch the file alone) | None | 17 Jun 2021 |
| 12 | `skoval/tennis-match-data`, **a fork of `TennisVisuals/tennis-match-data`** | Both public | The parent (pushed 23 Feb 2017) has 21 files, including `CHALLENGER_Singles_pbp.csv` (1.57 MB), which the fork lacks, and slightly larger `_pbpx` files. The fork (12 Feb 2017) has 20 | None on either | 2017 |
| 13 | `ml874/Predicting-How-Points-End-in-Tennis` (also `dineshjrd/Tennis_end_points`) | Public | `tennis_data/`: men's and women's train and test CSVs, `AO2AI_Hackathon_DataDictionary.docx`, `AUS_SubmissionFormat.csv` | None | Feb 2018 |

**The parent's README** [observed]: the files follow Sackmann's point-by-point format and were "validated using the Universal Match Object".
* `_pbp.csv` files code points with only S and R.
* `_pbpx.csv` files add A (ace) and D (double fault); lowercase letters mark second-serve points when `adf_flag` is true.
* The upstream feed is not named.

### Public copies found by a parallel search

**The search covered:** about 75 GitHub code searches and 60 repository searches; Sourcegraph; about 60 Kaggle terms; Hugging Face name and full-text search; Zenodo, Figshare, Dataverse, OSF, data.world and the Apify store. Samples under 5 MB each were kept in the session scratchpad. This lane re-checked the three main finds itself (metadata, file lists, and one range read).

* **No published copy of TDI data exists** [observed, across all the places above].
  * **Near misses:**
    * The Apify scraper (§2).
    * `superdev1230/tennisviz-processor`: one anonymised TennisViz match, useful only as a schema example.
    * `joaoopedroandrade/tennis-scraper`: code that scrapes TDI's Performance Rating.
* **Hugging Face `atlas-polybot/atp-pipeline-handoff`: decrypted ATP Stats Centre data for 2021–2024.**
  * **Publication** [observed, this lane]:
    * public, not gated, no licence, no dataset card;
    * 5,764 files; created 1 Jun 2026, last changed 19 Jun 2026; 424 downloads;
    * total size about 152 GB, as reported by the parallel search (not rechecked here).
  * **`data/tennis/infosys_deep/`**, one JSONL per year:
    * 2021: 117 MB;
    * 2022: 941 MB;
    * 2023: 1,004 MB;
    * 2024: 1,046 MB;
    * a few kB for 2018–19.
  * **`infosys_full/`** runs to 3.0 GB for 2024, and adds `court_vision`.
  * **`court_vision/`** has 4,570 per-match files.
  * **Points** [observed, this lane]: the first 15 records of the 2024 file (a range read) carry per-point `rally_analysis` rows. Their keys are `courtSide, crucialPoint, hand, pointEndType, pointId, score, serve, serveDir, serveSpeed, set, setPoint, shotType, t1BreakPoint, t1NetPoint, t2BreakPoint, t2NetPoint, tieBreak`.
  * **Coverage** [provider claim, checkpoint files]: 1,549 matches in 2021, 11,262 in 2022, 12,017 in 2023 and 12,502 in 2024.
  * **Width by level** [observed by the parallel search, 250 matches]:
    * **Tour level:** full winner, forced-error and unforced-error outcomes, and a serve speed on almost every point.
    * **Challengers:** serve 1/2 and ace or double fault only; everything else "UNCLASSIFIED". This lane's range read agrees, for four 2024 Challenger matches.
    * 59% of sampled matches had point rows.
  * **Court Vision:** 298 matches in 2021, 1,348 in 2022, 791 in 2023 and 2,119 in 2024 (610 of those qualifying). Per-shot x/y/z at hit, peak, net and bounce.
  * **Also in the dump:** Flashscore (127 GB), ATP box scores, Sackmann files, and Tennis Abstract and Match Charting Project material.
  * **Its `RAW_DATA_SOURCES.md`** [observed]: "Years: 1990–2024… (2025–2026 live in the owner's main repo and are still being scraped; ask if you need them.)" Asking is not a route.
  * **Rights:** decrypted Infosys/ATP data, no licence; atptour.com forbids systematic retrieval.
* **The 2016–17 point strings** [observed].
  * **Producer:** Charles Allen (TennisVisuals, now CourtHive).
  * **The upstream holds more than the fork:**
    * ATP `_pbpx`: 1,360 matches (fork: 1,313), identical strings for the 1,278 matches both hold;
    * ITF men's: 15,689 (fork: 15,382);
    * a `CHALLENGER_Singles_pbp.csv` of 5,251 matches (2012–13 and February 2017), winner codes only.
  * **Second-serve points:** about 36% of ATP `_pbpx` points.
  * **Feed and status:** the feed is not named. His documentation says Sackmann's strings came from "XML files provided by a 3rd party" [third-party report]. Nothing has been published since February 2017, and nothing is sold.
* **Monash return impact:** no fuller release. arXiv 2202.00583 has only version 1, with no supplement or data statement.
  * The repository's `phyllis` branch holds a 54.7 MB `.RData` with the same 126,455 rows, split by first and second serve and by grass [observed by the parallel search].
* **Tennis Australia's 2019 release: `camroach87/etc3250-kaggle`** [observed, this lane: `data/ao_training.rda` 12.1 MB, `ao_test_unlabelled.rda` 12.0 MB, `ao_sample_predictions.csv` 0.5 MB; pushed 22 May 2019; no licence].
  * **Provenance:** a Monash course competition. "The data set is provided by Tennis Australia… modelled on this competition conducted in 2018, but new data is provided" [provider claim]. It covers "men's and women's singles matches from the 2017 and 2018 Australian Open".
  * **Rows** [observed by the parallel search]:
    * training: 49,914 shot rows (26,928 points, outcome F/U/W);
    * test: 49,971 rows (26,929 points, 333 matches, no outcome but `serverwon`).
  * **Ids:** `matchid` and `pointid` (e.g. `2017_MS101_1_1_7`), which should join to the Slam point archive [inference].
  * **Link to From AO to AI** [inference from matching speed to four decimals, plus serve and hit point]:
    * 10,795 of the 13,000 rows of 2018 link uniquely, 10,764 of them to AO 2017;
    * where both sets are labelled, the labels agree on 98.8%;
    * 1,218 of the 3,000 unpublished 2018 test rows gain labels.
    * The linking scripts are in the session scratchpad; the method is unreviewed.
* **Aside, row 8:** Hugging Face `ramizheman/TennisNLData` (public, no licence, 9,257 files, last changed 6 Jun 2026) holds Tennis Abstract chart JSONs with full point logs.
  * The parallel search matched **3,053 of the 6,447 website-only charts** to them by file name.
* **No copy anywhere:** Tennis Australia's 2023 "AO Data Slam"; decrypted MatchBeats files.

## 4. Method

* **TDI:** 21 requests to `results.tennisdata.com` between 17:32 and 17:47 UTC, spaced 1.5–3.5 s. curl_cffi with the Chrome profile, from the project's `tennis` environment. No challenge was served; every response was 200, except the old match page (404, with its data).
  * Of the 21: the homepage and three missing-file paths; 12 JavaScript bundles; four filtered listings; one old match page.
  * Log: [E_tdi_access_probe_log.tsv](../probe_logs/E_tdi_access_probe_log.tsv).
* **Wayback Machine:**
  * three CDX queries;
  * 11 homepage captures;
  * 57 archived JavaScript bundles (54 readable, 11 of them after gzip decompression).
* **Common Crawl:** the collection list, then one index query per crawl since 2025 (21), plus one domain-wide check.
* **GitHub:** read-only `gh api` calls.
* **Hugging Face:** two dataset-metadata calls, two tree listings, and one 1.5 MB range read of `infosys_deep/2024_data.jsonl`.
* **Other:** one WebSearch and one WebFetch (the Apify page).
* **Two parallel searches**, one for vendors and one for public copies, ran the searches and fetches listed in §2 and §3. Their reports are summarised there. Their scripts and samples, like this lane's payloads, were kept in the session scratchpad, not here.

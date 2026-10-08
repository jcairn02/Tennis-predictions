# TDI Tennis Results and four open datasets: can the data be had publicly, or bought?

**Status: research, not a decision.** Read on 24 September 2026.
* Nothing was bought, no account or trial was opened, no provider was contacted, and nothing was decrypted.
* No bulk download was attempted. TDI's site was read with 21 requests.

This follows up rows 9–13 of the [granular data leads](README.md):
* TDI Tennis Results;
* the SirGenkii fork of decrypted ATP data;
* the Monash return-impact file;
* `skoval/tennis-match-data`;
* From AO to AI.

Rows 2–6 (the Slam feeds and the WTA API) are covered in [access routes](access-routes.md).

## How the instruction is read

The owner's instruction (24 September): "See if you can obtain their results publically or a PAID service. An "ask them to see if you can" is not viable path for our data extraction. If it says no scraping but the data is public, that doesnt count. We will disregard that suggestion."

* **Asking is not a route.** That covers permission, a research licence or a copy from a rights holder, author or vendor. A paid licence that allows the project's use only with the vendor's written consent is an ask too, as on the rows 2–6 page.
* **A no-scraping clause on publicly served data does not rule a source out.** This reading follows the last sentence of the instruction and the owner's 23 September decision on SofaScore and TennisLive. Terms are still recorded.
* **Under the stricter reading,** where such a clause does rule a source out, TDI's site drops out. The four datasets are downloads, not scraping; their hosts allow downloading. But none carries a data licence, and three come from sites whose terms forbid collection.

## Bottom line

* **TDI Tennis Results can be had publicly from about 24 June 2026 onward. January 2025 to June 2026 cannot be had in bulk, publicly or by paying.**
  * **What the site lists:** only a rolling window of about 93 days.
  * **Old match pages still serve every point,** but nothing public lists their ids:
    * the Wayback Machine holds 634;
    * Common Crawl holds none;
    * search engines find single matches.
  * **No licensed product sells this data to a buyer like this project.** Sportradar, TDI's exclusive distributor, sells the same fields only as live bet-settlement markets to bookmakers and prediction-market platforms.
  * **What can be bought self-serve adds no history:**
    * an Apify scraper of the same site, which sees the same window;
    * Live Tennis API tags, which start on 12 September 2026.
  * **No published copy of TDI data exists.**
* **All four open datasets can still be downloaded, and none is sold.** Larger public copies found on this pass change their value:
  * **Hugging Face `atlas-polybot/atp-pipeline-handoff`** holds decrypted ATP Stats Centre data for 2021–2024. It is the same kind of data as the SirGenkii fork, which adds January–April 2025:
    * about 37,300 tour, Challenger and qualifying matches;
    * point outcomes at tour level;
    * Court Vision tracking for 4,570 tour-level matches.
  * **`camroach87/etc3250-kaggle`** is Tennis Australia's 2019 release for the Australian Open 2017–18: about 53,900 points, with match and point ids. 10,795 of From AO to AI's 13,000 rows link to it.
* **Nobody sells tennis tracking to a buyer outside the federations and bookmakers.** So no paid version of rows 10, 11 or 13 exists.
* **The nearest substitute for TDI's missing history is the ATP's own Infosys data.**
  * Decrypted copies reach April 2025.
  * May 2025 onward would need the project to decrypt the ATP files itself (row 14). That is a separate decision from ignoring a no-scraping clause.

## By source

| Row | Source | Public today | Sold? | Obtainable |
|---|---|---|---|---|
| 9 | **TDI Tennis Results** (ATP Tour and Challenger points since January 2025) | The listing covers a rolling ~93 days; every later match can be captured going forward. Older pages keep their points, but only 634 older ids are recoverable (Wayback Machine), plus single matches through search engines | Not with a licence this project can get (table below) | From about 24 Jun 2026 on; not January 2025 – June 2026 in bulk |
| 10 | **`SirGenkii/infotennis`** (decrypted ATP, January–April 2025) | Yes: six SQL dumps, 34 MB. The larger Hugging Face copy covers 2021–2024 | No | Yes, 2021 to April 2025 across the two copies |
| 11 | **`skoval/monash-return-impact`** (ATP returns, 2018–20) | Yes, 1.3 MB. No fuller release exists. Return impacts for 2021–24 could be derived from the Hugging Face Court Vision files [inference] | No | Yes |
| 12 | **`skoval/tennis-match-data`** (2016–17, second serves marked) | Yes. It is a fork of `TennisVisuals/tennis-match-data` (Charles Allen), which holds a little more: 1,360 ATP and 15,689 ITF men's matches with second-serve marks, and a winner-only Challenger file. Nothing has been added since February 2017; the upstream feed is unnamed | No | Yes; a closed dataset |
| 13 | **From AO to AI** (Australian Open Hawk-Eye features, 2018 contest) | Yes, 2.7 MB. It is now joinable through the 2019 Tennis Australia release (mostly AO 2017) | No | Yes, and mostly joinable |

## TDI's site: what it lets a client list

All observed on 24 September 2026 unless marked.

* **The listing is a rolling window of about 93 days, measured by timestamp.**
  * `?date=2026-06-24` listed 45 matches.
  * `?date=2026-06-23` listed only that day's last match.
  * Older dates fall back to today's list.
* **The filters stay inside the window.** The listing's URL state is `tournamentId`, `playerId`, `date`, `sort`, `display` and `filter`, all rendered on the server.
  * Adam Walton's player filter returned 18 matches, 24 June – 23 September 2026, and none from 2025.
  * The tournament filter offers 85 tournaments.
* **Nothing else lists matches.**
  * There is no robots.txt or sitemap.
  * There is no player, tournament or archive route.
  * The tRPC endpoint is configured, but no procedure is called from the browser in the current bundles or in 54 archived ones back to May 2025.
  * Match ids are random version-4 UUIDs.
* **Old pages keep their points.** A May 2025 page (Draper v Alcaraz, Rome) returned HTTP 404 with all 127 points, each with outcome, rally length, last stroke, error type and net position.
* **Page titles carry the ATP match code**, e.g. `Tiafoe vs Walton | 2025#339#MS020 | Tennis Results`. That gives an exact join to ATP ids once a page is found.
* **Size of the gap** [inference]: at about 60 matches per Challenger event and 80 per tour event, January 2025 – June 2026 holds on the order of 20,000 matches. The 634 archived ids are a few percent of that.
* **Terms:**
  * no scraping or text and data mining "for any purpose, including … statistical models or AI systems";
  * personal, domestic use only;
  * an EU text-and-data-mining opt-out.

## Paid routes, and what blocks each

| Product | What it has | History | Buyer, price | Blocker |
|---|---|---|---|---|
| **Sportradar "ATP Players & Micro Markets"** (Unified Odds Feed) | Per point: serve outcome, winner or error by player, total shots, last stroke, net or out. ATP 250 and up, men's singles, from 17 Feb 2025; "not available for Challenger events" | None: live settlement messages | Bookmakers and prediction-market platforms, through a sales representative; no price | Live only. The ATP addendum requires destroying licensed materials at the end and bars collating data |
| **Sportradar Tennis API v3** | Per point: first-serve fault, ace, double fault, winner; no outcome type | A rolling window of seasons | Businesses, through sales; no price | Display only; betting or prediction-market use needs written consent (an ask) |
| **TDI "Tennis Data Platform"** | Claims "a comprehensive archive" and an open "sandbox" | Not stated | No sign-up, link or documentation; no subdomain resolves | Nothing to buy |
| **ATP Tennis IQ** | Hawk-Eye insights | Not stated | ATP and Challenger players and ATP coach members | Eligibility, not purchase |
| **Live Tennis API** | Per point: serve 1/2 and ace / double fault / winner / forced / unforced error. ATP and Challenger full; WTA and ITF aces and double faults only | Tags from 12 Sep 2026; no backfill (checked to v1.13.49) | Self-serve: $29.99 a month with bulk downloads, or $49 for a month's pass | Terms bar storing data "beyond what is reasonably necessary" and bulk resale |
| **Apify `sian.agency/tennis-point-by-point-scraper`** | TDI's own fields, scraped (the source is not named); its tournament directory is TDI's (ATP and Challenger only, despite its ITF and WTA claims) | TDI's ~93-day window through its player and tournament directories; no date input. Any older match whose id is supplied (`scrape-match-ids`, 250 a run) | Self-serve, per match: $0.075 on Apify's free plan (5 matches a run, 30 runs a day), $0.025 on Starter, $0.01875 ($18.75 per 1,000) on Business. Listing match ids is not billed | No history beyond the site; buying a scrape grants no rights |
| **Tracking vendors** (Hawk-Eye, TennisViz, Golden Set Analytics, Sportradar DDE) | Per-shot tracking | — | Partners, selected clients or bookmakers; demos by call-back | Not sold to a buyer like this project |

**Also checked, nothing relevant:**
* Datarade (odds only);
* Snowflake (Stats Perform schedules);
* AWS Marketplace, RapidAPI and Opendatabay;
* SportsDataIO and BigDataBall (box scores);
* TheSportsDB, Sportmonks and Oddin.

**Market context:** Polymarket became the ATP's official prediction-market provider in August 2026, with "Official real-time data and odds for all matches delivered by TDI's exclusive distribution partner, Sportradar" [provider claim].

## The open copies found

* **Hugging Face `atlas-polybot/atp-pipeline-handoff`.**
  * **Publication** (all checked on this pass): public, not gated, no licence, no card; created 1 June 2026, last changed 19 June 2026.
  * **Size and layout:**
    * about 152 GB in all, 127 GB of it Flashscore (the whole was not checked here);
    * the Stats Centre data sits in `infosys_deep/` (JSONL per year, 2021–2024, about 3.1 GB);
    * `infosys_full/` (adds Court Vision, 7 GB);
    * `court_vision/` (4,570 per-match files, 0.3 GB).
  * **Per point:** `pointEndType`, `serve`, `serveDir`, `serveSpeed`, `shotType`, `hand`, the net-point and break-point flags and the score. These were confirmed in a range read of the 2024 file.
  * **Width by level:** tour level carries winner, forced and unforced outcomes. Challengers carry serve number and ace or double fault only.
  * **Its own note** says 2025–26 exists but is not published ("ask if you need them").
* **`camroach87/etc3250-kaggle`.**
  * Tennis Australia data for a 2019 Monash course contest: AO 2017–18 men's and women's singles.
  * About 26,900 labelled and 26,900 unlabelled points, with `matchid` and `pointid` (e.g. `2017_MS101_1_1_7`).
  * **Matching From AO to AI to it** (on speed, serve and hit point):
    * 10,795 of the 13,000 rows link uniquely;
    * where both sets are labelled, the labels agree on 98.8%;
    * 1,218 of the 3,000 never-published test rows gain their labels.
    * The method is unreviewed.
* **`TennisVisuals/tennis-match-data`**, the upstream of row 12. Its README says the points were "validated using the Universal Match Object" and follow Sackmann's format; lowercase letters mark second-serve points.
* **An aside for row 8:** Hugging Face `ramizheman/TennisNLData` (no licence) holds Tennis Abstract chart files with full point logs. 3,053 of the 6,447 website-only charts match by file name.

## What follows (options, not decisions)

1. **Keep TDI's current window before it slides.**
   * The ids are the scarce part: one listing read per day of the window, about 93 requests, keeps them all.
   * The pages can then be fetched at any time.
   * Each day of delay loses a day at the window's far end.
2. **Capture TDI going forward.** Read the listing at least once a quarter (in practice daily or weekly), then fetch the pages. An adapter would sit beside the SofaScore and TennisLive ones in `src/ingest/point_sources/`.
3. **Take the open copies.** Download only the needed folders of the Hugging Face dump (`infosys_deep/`, `court_vision/`), not all 152 GB. The SirGenkii SQL, the Monash file, the TennisVisuals upstream, and From AO to AI with the 2019 release come to about 90 MB together.
4. **Decide on the ATP's own Infosys files for May 2025 onward.** Decrypted by the project, they would give tour-level outcomes for most of TDI's missing period. Only the Challenger rows would stay thin.

## Not determined

* The size of TDI's gap, which is inferred from draw sizes, not counted.
* Whether paid search APIs could recover many more TDI ids (untested).
* How the window crawl fares at scale: 21 requests met no bot challenge.
* The Hugging Face copy's completeness: 59% of 250 sampled matches had point rows.
* The From AO to AI link method.
* Legal effect. This page reads what the sites and vendors say; it is not legal advice.

## Evidence

* [Lane E](../../../data/studies/granular_data_leads/research_notes/E_access_routes.md): the TDI probes, the paid-route search, the public-copy search and the checks on the four downloads.
* [E_tdi_access_probe_log.tsv](../../../data/studies/granular_data_leads/probe_logs/E_tdi_access_probe_log.tsv): the 21 TDI requests.
* [tdi_wayback_match_ids.csv](../../../data/studies/granular_data_leads/tdi_wayback_match_ids.csv): the 634 recoverable older TDI match ids, with the capture each came from.

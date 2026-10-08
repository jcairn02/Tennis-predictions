# Slam feeds and the WTA API: can the data be had publicly, or bought?

**Status: research, not a decision.** Read on 24 September 2026. Nothing was bought, no account or trial was opened, no provider was contacted, and no vendor chat or Q&A agent was used. No bulk download was attempted.

This follows up rows 2–6 of the [granular data leads](README.md):
* the Wimbledon scoring feeds;
* the US Open scoring feeds;
* the Australian Open 2026 match centre;
* IBM's extras;
* the WTA API.

## How the instruction is read

The instruction as this session received it (24 September):
* "See if you can obtain their results publically or a PAID service."
* "An 'ask them to see if you can' is not viable path for our data extraction."
* "If it says no scraping but the data is public, that doesnt count."

**The likely intent.**
* A parallel session working on rows 9–13 quotes the same instruction with one more sentence: "We will disregard that suggestion" ([E_access_routes.md](../../../data/studies/granular_data_leads/research_notes/E_access_routes.md)).
* Read with that sentence, and with the owner's 23 September decision to collect SofaScore and TennisLive regardless of their terms, a no-scraping clause on public data does **not** rule a source out.
* That is taken here as the likely intent.

**The stricter reading is answered too.** Under it, such a clause does rule a source out. The facts are the same under both readings.

**Either way:**
* asking a rights holder is not a route;
* a paid licence that allows the project's use only with the vendor's written consent is an ask as well.

## Bottom line

* **Publicly: all five can be obtained today, if a no-scraping clause does not rule a source out.** Every source served its data, without a login, to the 24 September probes. The practical limits:
  * **Australian Open 2026.** It is the only edition served and will probably disappear in January 2027, so it is the most urgent. No paid or open copy replaces it.
  * **Wimbledon 2019 and 2021–2025.** These sit on an archive host (`2025.wimbledon.com`) that could be retired at any time.
  * **Wimbledon 2026.** The bot manager sends automated requests for the singles draw files to robots.txt. The earlier pass listed matches from the daily completed-match files instead.
  * **US Open.** A plain client gets its connection reset; a browser user agent gets the files.
  * **WTA.** Served from 2022; 2019 returned 404.
    * *Listing every match:* third-party code does it through `api.wtatennis.com/tennis/tournaments/` and `…/tournaments/{id}/{year}/matches`, with an `account: wta` header. This was not tested here.
    * *Tier coverage:* not measured.
  * **IBM extras.** Likelihood-to-win exists only for 2025–26 singles main draws; serve biomechanics only for the US Open 2026 singles main draw.
  * **Bulk collection** has not been tried. Rate limits and bot management at scale are untested.
* **Under the stricter reading, only Wimbledon 2026 from `www.wimbledon.com` passes, and only for personal, non-commercial use.**
  * *What it covers:* about 601 matches (every 2026 event, including qualifying and doubles) and the 2026 likelihood-to-win files.
  * *Why it passes:* AELTC's terms have no scraping clause, and the www robots.txt does not block the feed paths.
  * *Four points for the owner to judge:*
    * whether betting on Polymarket with models built on the data is "commercial";
    * whether downloading a whole edition is "extracts";
    * whether modifying downloads falls under clause 6.4, which forbids modifying downloaded copies "in any way";
    * whether the bot manager counts as the site "otherwise prohibit[ing] such activities" (clause 6.3(iii)).
* **What the sites say** (quoted [below](#terms-and-robotstxt-quoted)):
  * The US Open, Tennis Australia and the WTA forbid automated collection in their terms.
  * AELTC's terms do not, but they limit use to personal, non-commercial purposes. Wimbledon's archive host also disallows every robot in robots.txt.
* **No service sells any of the five datasets, or the editions that are no longer served** (AO 2022–25, US Open 2019–21, WTA before 2022).
  * **Nobody sells:**
    * IBM's per-point stroke-and-error sentence, the only record of forced errors;
    * likelihood-to-win, serve biomechanics or TennisViz metrics;
    * the AO match centre's per-point forehand/backhand outcomes.

    IBM, Hawk-Eye, TennisViz and Infosys produce these for the events and sell none of them.
  * **Official Slam data is sold live, not as an archive,** to betting operators and licensed prediction-market firms:
    * **Sportradar** holds Wimbledon, the US Open and Roland-Garros, since buying IMG ARENA (closed November 2025). Wimbledon signed direct with it in June 2026, qualifying included.
    * **Infront Bettor** holds the Australian Open for 2026–29, and **Catalist Sports** resells it in the US.
  * **Paid products that do sell history are thinner, and their licences block this project's use** (table below).
* **Nothing open fills the gap.**
  * Sackmann's Slam point archive has been deleted from GitHub. It was the source of the Slam data the dump holds.
  * Its last commit (11 October 2024) had no 2025–26 or qualifying files, no clock times and no stroke/error text.
  * Every other open Slam point dataset found is a copy or subset of it.

## By source

| Row | Source | Public today | What the site says about automated collection | Sold anywhere? | Passes the stricter reading? |
|---|---|---|---|---|---|
| 2 | Wimbledon feeds, 2026 (`www`) | Yes. The bot manager deflects the singles draw files | **Terms:** no scraping clause; personal, non-commercial "extracts" allowed; commercial use needs a licence from AELTC or its official licensors. **robots.txt:** feed paths not disallowed | No. Sportradar's Tennis API has a thinner version (table below) | Yes, for personal, non-commercial use |
| 2 | Wimbledon feeds, 2019 and 2021–25 (archive host) | Yes | Same terms. robots.txt: `Disallow: /` | As above, within its rolling window | No |
| 3 | US Open feeds, 2022–26 | Yes, with a browser user agent | Terms forbid scraping and downloading | As above | No |
| 4 | AO 2026 match centre | Yes, probably until January 2027 | Terms forbid automated collection | No. The official feed (Infront, Catalist) is live only; its fields are not published | No |
| 5 | IBM extras | Yes | Follows the host | No | Only Wimbledon 2026 likelihood-to-win |
| 6 | WTA API | Yes, 2022 onward | Terms forbid automated access and harvesting. The documented V2 API sits behind a Microsoft login with no sign-up | Stats Perform (exclusive WTA rights), Sportradar, Live Tennis API: all blocked (table below) | No |

## Paid routes, and what blocks each

| Product | Covers | History for sale | Per point | Buyer, price | Blocker |
|---|---|---|---|---|---|
| **Sportradar Tennis API v3** (media API) | All four Slams, point by point from round 1. The Slam data is Sportradar's own collection; its official tennis data is "for ATP tournaments only". WTA 1000/500 from round 1; WTA 250/125 from the semi-finals | A rolling window: "at least the current season and the two adjacent editions" | Clock time, server, winner, score, ace or double fault, first-serve fault. No winner/error type or stroke; winners and errors by wing are Slam match totals | Businesses, through sales. The 30-day trial is for evaluation only. No price | Terms of 5 Aug 2026: no prediction-market or betting use "without Company's prior written consent" (an ask). "All historical data" is destroyed on termination |
| **Stats Perform (Opta)** | WTA official data, exclusive to the end of the decade. Tennis archive "from 2021". Held AO official data 2023–25 | Marketed as "the training and calibration layer for prediction market pricing", configurable for "an operator's specific requirements" | WTA: millisecond time, first serve, shot type and stroke codes, zone; win probability, momentum, leverage | Organisations, through sales. No price | Standard licence (Dec 2025) bars ML training, building "archival files" and betting. A negotiated work order can override it (an ask) |
| **Sportradar Live Data and DDE** (the former IMG ARENA feeds) | Official Wimbledon (main draw and qualifying), US Open, Roland-Garros | None: live only. The replay server is a testing tool | **Live Data:** winner, ace or double fault, service fault. **DDE tracking** (live, being retired): stroke, forced or unforced, speeds | Betting operators; Kalshi, licensed prediction-market firms and Kalshi's market makers | Live only. Derived data destroyed on termination |
| **Infront Bettor**, and **Catalist Sports** in the US | Official AO 2026–29. Catalist also covers ITF, Davis Cup and Billie Jean King Cup | Not stated | Not published | Sportsbooks. Catalist also serves "market makers, quantitative trading teams and prediction-market platforms". Sales only | Live only; fields unknown. Catalist's FAQ does allow market makers on Kalshi and Polymarket |
| **Enetpulse** | ATP and WTA, including Slams | Point by point "since 2020", an "exclusive product" via sales | Score after each point. Timestamps are batch times, not point times | Businesses | Score sequence only, none of the feeds' extra fields. Licence not public |
| **Live Tennis API** | **Slams:** score only. 2013–22 rebuilt; its own capture since 2023. **WTA:** ace and double-fault tags from 12 Sep 2026 | Yes, self-serve | Slams: no outcome. Times are the vendor's capture times | Individuals, $9.99–$399 | Terms bar storing data "beyond what is reasonably necessary". Part of its catalogue is Match Charting Project data, licensed "Non-commercial use only" |

**Other vendors:**
* *Resell scrapes:* SportsAPI Pro (SofaScore-shaped), Apify's SofaScore scraper, BetsAPI.
* *Score-only or unverified:* api-tennis.com, Goalserve, Matchstat, STATSCORE/LSports, Podium, Data Sports Group.

Details are in [lane G](../../../data/studies/granular_data_leads/research_notes/G_vendor_history.md).

## Terms and robots.txt, quoted

All read with `curl` and a Chrome user agent, 17:31–17:53 UTC, 24 Sep 2026.

**Wimbledon: AELTC Digital Platforms Terms of Use.**
* https://www.wimbledon.com/en_GB/terms_of_use. The same text is on the archive host's copy, https://2025.wimbledon.com/en_GB/cms/feeds/about_wimbledon/acceptable_use_policy.xml, whose metadata carries a 2015 date. No revision date is shown.
* No clause mentions scraping, robots, crawling, data mining, statistics or scores.
* 6.2: "You must not use any part of or any content obtained from an AELTC Digital Platform for commercial purposes without first obtaining a licence from AELTC or from AELTC's official licensors (as may be applicable)."
* 6.3: "You may print one copy of, and/or may download extracts of, any page(s) from an AELTC Website or AELTC App provided that: (i) such extracts are used only by you for personal, non-commercial purposes; (ii) such action is not otherwise in breach of any other applicable terms and conditions …; and (iii) the relevant AELTC Website or AELTC App does not otherwise prohibit such activities."
* 6.4: "You must not modify the paper or digital copies of any materials you have printed or downloaded in any way …"
* 11.2: "You agree not to reproduce, duplicate, copy or re-sell any part of an AELTC Digital Platform in contravention of these Terms of Use."
* 11.5: "You must not make use of any technological, automated or manual processes in order to circumvent or manipulate the intended functionality of any Service on an AELTC Digital Platform, in particularly (but without limitation) in order to gain an unfair and/or unauthorised advantage to accessing tickets to The Championships."

**Wimbledon robots.txt.**
* `www.wimbledon.com` ("Updated: Aug 2023"): 13 `Disallow` lines for `User-agent: *`, including `/api/`, `/matchvideo/` and `/webview/`. None covers `/en_GB/scores/feeds/` or `/clouddata/`.
* `2025.wimbledon.com`: `User-Agent: *` / `Disallow: /`. The earlier Slam notes had checked only the www host.

**US Open: USTA Terms of Use** ("Last revised: April 30th, 2024").
* https://www.usopen.org/en_US/info/terms/index.html; the text was read from `/en_US/cms/feeds/general_content/terms.xml`.
* "The USTA grants you a limited license to access and make personal, non-commercial use of the USTA Site. In accordance with these Terms of Use, you are not permitted to download any material … except for printing single copies of pages …"
* "You shall not use the USTA Site in a manner that … (iii) results in the scraping or copying of information, data, or content, or (iv) circumvents or overrides security features."
* robots.txt does not disallow `/en_US/scores/feeds/` or `/clouddata/`.

**Australian Open: Tennis Australia "Conditions of Use – Online Systems".**
* https://www.tennis.com.au/about-us/reports-publications-national-policies/conditions-of-use, linked from ausopen.com's footer.
* The live page returns 403, so it was read from the Wayback capture of 8 May 2026.
* 3(g): users agree not to "collect content from any Online System using automated means (such as harvesting bots, robots, spiders, or scrapers)".
* 6: "no material from an Online System may be distributed or copied for any commercial purpose. You may save, print, copy or reproduce material from the Online Systems solely for your personal (non-commercial) education or information."
* ausopen.com's other footer link, `/ao-terms-conditions`, now leads to the AO 2027 ticket conditions.
* `prod-scores-api.ausopen.com` has no robots.txt (403, "Missing Authentication Token").

**WTA: Terms and Conditions** ("Last Updated: April 06, 2020").
* https://www.wtatennis.com/terms-and-conditions.
* "You must not: "harvest" (or collect) information from the WTA Sites using an automated software tool or manually on a mass basis (unless we have given you separate written permission to do so)."
* "use automated means to access the WTA Sites … This prohibition does not apply to search engines accessing the WTA Sites solely for web indexing purposes."
* robots.txt: www allows everything; `api.wtatennis.com` returns 404.

## Side findings

* **Sackmann's other repositories are gone too.** `tennis_atp`, `tennis_wta` and `tennis_pointbypoint` return 404 on GitHub; only `tennis_MatchChartingProject` remains. Anything the project takes from them in future must come from mirrors.
* **IBM's 2016 "Datapalooza" release is the only open, first-party IBM Slam point data found.**
  * *Where:* `github.com/ibm-datapalooza/wimbledon-datasets`, licensed Apache-2.0.
  * *What:* Wimbledon 2014 and 2015 men's and ladies' singles, rounds 1–3. Per point it gives timestamps of the first serve, second serve and point end; the stroke; and winner, forced or unforced error.
  * *What it adds:* clock times and forced errors for up to 448 matches the dump already holds [inference from draw sizes].
  * *Caveat:* AELTC's permission is not stated.
* **Catalist is the only feed found whose own FAQ names Polymarket market makers as allowed users.** It covers AO, ITF, Davis Cup and Billie Jean King Cup, live only. Sportradar also serves licensed prediction-market firms and Kalshi's market makers. Both matter for the later venue stage, not for history.

## Not determined

* **Collection at scale.** Whether collecting whole editions works in practice (rate limits, bot management), and how complete the WTA's tiers are.
* **Prices.** None are published for any sales-only product.
* **Individual buyers.** Whether an individual can contract with Sportradar's prediction-market unit, Infront, Catalist or Stats Perform.
* **The official AO feed.** Its fields are not published. Unknown:
  * whether it carries per-point forehand/backhand outcomes and times, or keeps an archive;
  * whether Stats Perform can still supply its 2023–25 AO data.
* **Sportradar's contract.** It both grants a licence "perpetual (solely for archiving purposes)" and requires destroying "all historical data" on termination.
* **Legal effect.** This page reads what the sites and vendors say. It is not legal advice on how far those terms bind.

## Evidence

* [Lane F](../../../data/studies/granular_data_leads/research_notes/F_slam_licensees.md): who holds and sells the Slams' official data.
* [Lane G](../../../data/studies/granular_data_leads/research_notes/G_vendor_history.md): vendors of historical Slam point data.
* [Lane H](../../../data/studies/granular_data_leads/research_notes/H_wta.md): WTA terms, rights and paid routes.
* [Lane I](../../../data/studies/granular_data_leads/research_notes/I_open_datasets.md): open datasets and the Sackmann archive.
* The practical access facts come from [the Slam notes](../../../data/studies/granular_data_leads/research_notes/B_grand_slams.md) and [the tour notes](../../../data/studies/granular_data_leads/research_notes/A_tour_official.md). The WTA match-list route comes from third-party code saved during lane H.
* The terms pages and robots.txt files were read in the session scratchpad and not kept.

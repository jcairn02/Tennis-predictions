# Commercial, paywalled, and private tennis data

This is an evidence inventory, not an approved source selection, architecture, procurement decision, or roadmap. Sources were checked on **10 September 2026**. The target market window is **10 September 2025 through 10 September 2026**; claims about older archives are assessed separately from coverage of that window. An advertised archive, a documented response, a downloaded demonstration, and a licensed production dataset are different levels of evidence.

The strongest finding is that tennis has several materially different data supply chains. Paying one vendor does not automatically obtain every tour, every historical season, every point, or permission to train models. Official men's-tour data, women's-tour data, ITF data, Grand Slam data, and private tracking data must be evaluated separately. Broad commercial coverage claims should be reconciled against the actual Polymarket event inventory before they are treated as useful coverage.

## Findings that change the source search

* **Sportradar's ITF World Tennis Tour coverage stopped in 2025.** Its January 2025 changelog explicitly removes that circuit while retaining Davis Cup and Billie Jean King Cup. Infront became the ITF data partner; LSports documents an Infront distribution agreement. An old Sportradar brochure can therefore give the wrong answer for the entire target year. [Sportradar change notice](https://developer.sportradar.com/sportradar-updates/changelog/tennis-api-coverage-updates), [ITF announcement](https://www.itftennis.com/en/news-and-media/articles/infront-to-become-itf-official-data-partner/), [LSports agreement](https://www.lsports.eu/lsports-to-become-itfs-official-data-distributor/).
* **Sportradar's standard historical match access is a rolling catalog, not a guaranteed decades-long match archive.** Current documentation describes the current season and two adjacent editions; competitor-level records can reach 2007. A separate historical export, if offered, needs its own specification. [Historical-data guide](https://developer.sportradar.com/tennis/docs/tennis-ig-historical-data).
* **OnCourt is more than a desktop statistics viewer.** It advertises access to its Microsoft Access database for licensed users and a separate MySQL-dump/update service. This is an unusually concrete potential route to broad historical lower-tour data. [OnCourt](https://www.oncourt.info/index.html), [database distribution](https://www.oncourt.info/tennis_provider.html).
* **Private tracking archives exist, but public visualizations do not establish raw-data availability.** TDI describes an archive and sandbox; Tennis IQ is a player/coach platform; TennisViz and Golden Set Analytics describe sophisticated tracking-derived services. Their export coverage, research admission, betting use, and price are largely unpublished. [TDI platform](https://www.tennisdata.com/tennis-data-platform), [Tennis IQ release](https://www.atptour.com/-/media/sites/atp-tour/press/press-releases/atp-tennis-iq-august-2025-release.pdf), [TennisViz](https://tennisviz.com/), [Golden Set Analytics](https://goldensetanalytics.com/why-use-analytics/).
* **Even purpose-built historical vendors need timestamp audits.** Live Tennis API distinguishes reconstructed score sequences from observed points, but its commercial and academic pages disagree about when observation began. Its public Australian Open 2016 final example also uses 18 January as `event_date`; that cannot be treated as the final's playing date. [Commercial history](https://livetennisapi.com/historical-tennis-data-api), [academic description](https://livetennisapi.com/data/academic), [30 January final report](https://www.tennis.com/news/articles/kerber-wins-first-major-title-with-three-set-upset-of-serena-at-aussie-open).

## Evidence labels

| Label | Meaning |
|---|---|
| Primary rights evidence | Rights holder or contracting party describes a partnership; verifies the announcement, not delivery quality |
| Provider documentation | Endpoint, field, coverage, or price described by the provider; no paid payload inspected |
| Downloaded public example | Actual public example retrieved and parsed; may be old, curated, or inconsistent with production |
| Private lead | A relevant collection/service is described, but external access is not demonstrated |
| Unresolved | Access, provenance, historical depth, rights, or competing claims remain unverified |

No paid account, purchase, signup, or vendor outreach was performed. Most commercial databases could therefore be audited at the documentation and provenance level, not for production completeness. Unknown historical depth is recorded as unknown, rather than inferred from how long a company has existed.

## Official rights and distribution

### ATP Tour and ATP Challenger Tour: TDI and Sportradar

ATP identifies TDI as its data venture with ATP Media. Its December 2023 announcement gives Sportradar global betting data/streaming and media-data rights across ATP Tour and Challenger events. The earlier tender identifies a six-year cycle beginning in 2024. These statements establish the modern rights route; they do not imply that a low-cost media API includes the fastest betting feed or underlying optical tracking. [ATP agreement](https://www.atptour.com/en/news/sportradar-atp-partnership-december-2023), [rights-cycle announcement](https://investors.sportradar.com/news-releases/news-release-details/sportradar-wins-major-bid-atp-rights).

Polymarket's own **3 August 2026** announcement names Sportradar data and odds as settlement inputs under its TDI agreement and describes roughly 20,000 seasonal matches, including qualifying, main draws, singles, and doubles. It describes streaming to registered U.S. users. This is relevant supply-chain evidence, **not evidence that every such match had a tradable Gamma market throughout the preceding year**, and not proof that international Polymarket and Polymarket US expose identical contracts. [Polymarket-issued release](https://www.prnewswire.com/news-releases/polymarket-secures-exclusive-atp-tour-streaming-rights-for-prediction-markets-302841534.html).

### WTA: Stats Perform / Opta / RunningBall

Stats Perform markets exclusive official WTA umpire-chair data plus a separate low-latency shot-level feed and betting video. Its product page explicitly includes qualifiers in streaming coverage. The product is sold to licensed sportsbooks and pricing providers; historical licensing is a separate question from access to current video. Its RunningBall speed comparisons are vendor measurements, not independently reproduced latency results. [WTA partnership](https://www.statsperform.com/wta/), [current WTA betting product](https://www.statsperform.com/products/official-wta-data-streaming/).

The July 2026 developer knowledge base now lists tennis historical data **from 2021**, but does not give a tennis competition-by-season completeness matrix on that page. ATP, WTA 125, ITF, doubles, and qualifying depth should not be inferred from the headline. The same page promotes model calibration for prediction markets. [Historical coverage statement](https://developers.statsperform.com/historical-sports-data-for-pricing-models).

### ITF World Tennis Tour: Infront, with LSports distribution

The ITF's 2023 announcement awarded Infront global data and betting-streaming rights for 2025–2029, replacing Sportradar after 2024. The ITF announced an extension in October 2025. This is the relevant chain for M15/M25 and women's ITF events in the market window. LSports identifies itself as an official distributor and technology partner from 2025 under an Infront contract. Its broad tennis offering also contains independently collected data; official status should be tracked per competition/feed. [ITF award](https://www.itftennis.com/en/news-and-media/articles/infront-to-become-itf-official-data-partner/), [ITF extension](https://www.itftennis.com/en/news-and-media/articles/infront-and-itf-extend-global-partnership/), [LSports distribution](https://www.lsports.eu/lsports-to-become-itfs-official-data-distributor/).

Infront is a **quote-only, private historical-archive lead** in this audit. The public announcements do not expose a backfill API, the earliest retained point tape, historical corrections, export pricing, or a license for an independent bettor's model training. Those are unresolved commercial questions, not reasons to discard the source.

### Grand Slams are a separate rights check

Sportradar's June 2026 Wimbledon renewal identifies Wimbledon, Roland-Garros, and the US Open within its tennis rights portfolio after acquiring IMG ARENA in 2025. Wimbledon main draw and qualifying are explicit. This does not establish uniform shot-level archives for all three tournaments. [Wimbledon renewal and portfolio](https://investors.sportradar.com/news-releases/news-release-details/sportradar-nets-official-wimbledon-tennis-data-and-av-betting).

Infront's **15 September 2025** Tennis Australia announcement covers Australian Open data and streaming, qualifying and TA tournaments, and collaboration with the Game Insights Group. It establishes an additional route during the target year. Precise contract start, retrospective rights, historical fields, and archive eligibility remain unspecified. Older Australian Open/Stats Perform relationships should not be substituted for this current rights check. [Infront / Tennis Australia](https://www.infront.sport/news/sports-betting/infront-bettor-expands-tennis-portfolio-through-exclusive-australian-open-video-and-data-rights-partnership).

### UTR Pro Tennis Tour

Sportradar documents exclusive PTT betting data and streaming from January 2025, with over 20,000 annual matches claimed. PTT is not synonymous with ITF or ATP Challenger, even when player populations overlap. Whether this deserves acquisition depends on observed market coverage and on its usefulness for player-history enrichment. [UTR partnership](https://sportradar.com/content-hub/news/utr-sports-selects-sportradar-in-long-term-wide-ranging-partnership/).

## Commercial API and archive inventory

### Sportradar Tennis v3

This is the best-documented general commercial API examined. It exposes competition, season, event, and competitor IDs, rankings, brackets, summaries, timelines, and competitor merge mappings. Authentication is mandatory; no production payload or trial account was opened. Public match schemas document UTC start times, status and coverage information, while live data and probability products have separate delivery paths. [Overview](https://developer.sportradar.com/tennis/reference/overview), [event summary schema](https://developer.sportradar.com/tennis/reference/sport-event-summary), [betting live-feed documentation](https://docs.sportradar.com/live-data/introduction/information-per-sport/tennis).

The published tiers make a meaningful distinction: Grand Slams have extended statistics; ATP/Challenger standard statistics and point-by-point from round one; selected high-tier WTA/team events standard statistics and points; WTA 250/125 point coverage starts at semifinals in the generic tier guide; lower team ties can be game-only/results-only. Per-match coverage flags and the exported competition-season matrix should override a blanket tour assumption. [Coverage tiers and matrix](https://developer.sportradar.com/tennis/docs/tennis-ig-data-coverage-tiers).

The historical guide describes retained match summaries/statistics/timelines while a season remains in the rolling catalog. It also warns that a listed future season may contain no matches. **Presence in a catalog is not evidence of playable data.** Price and dedicated older exports are quote-only/unverified here. [Historical guide](https://developer.sportradar.com/tennis/docs/tennis-ig-historical-data).

### Stats Perform historical tennis and MA21

Public MA21 documentation exposes fixture UUID, scheduled and actual start, last-update time, match-end time, coverage level, statuses including retirement/walkover, and prediction states indexed by point. This is unusually useful metadata for temporal joins, but MA21 is a **prediction feed**, not proof of access to every raw score/shot input. Its suggested polling cadence is not the RunningBall low-latency feed's cadence. Historical point-range queries are documented. [MA21 field and endpoint reference](https://developers.statsperform.com/feed-ma21-tennis-predictions).

Pricing and tennis-specific archive counts are not publicly established in the inspected materials. **A signed model-training/archive license is required to make this candidate usable:** the December 2025 standard MLA restricts ML/AI model use and bulk archival storage except where the agreement authorizes them. A marketing page about pricing models is not that authorization. [MLA, section 4(c)](https://www.statsperform.com/legal/mla-december-2025/), [WTA-specific conditions](https://www.statsperform.com/legal/wta-terms-conditions/).

### LSports Tennis Premium

LSports claims 130,000 fixtures, 2,000 tournaments, and a mix of official and independent data, with ATP, WTA, and ITF packages. Its public explanation names web, television/in-venue, and computer-vision collection. These are meaningful provenance categories, but not a verified statement that each match has points or a retained history. Historical start date, timestamp fidelity, archived odds depth, downstream modeling rights, and pricing are not established. [Premium description](https://www.lsports.eu/lsports-tennis-premium-featured-in-online-gaming-quarterly-report/), [official ITF distribution and collection methods](https://www.lsports.eu/lsports-to-become-itfs-official-data-distributor/).

### Enetpulse

The live website advertises ATP/WTA/Grand Slams, point scoring, results, rankings, profiles, and a test period. Its language varies between all games and most tour-level matches; use the narrower interpretation until a coverage export resolves it. [Tennis product](https://enetpulse.com/tennis-data/).

The public package PDF is more informative: Basic and Live advertise 400+ tournaments; Premium 100+, with match statistics and point history. Premium lists Grand Slams, ATP and WTA; lower tours appear in Basic/Live. It provides concrete serve/return metrics and doubles career statistics. No explicit earliest historical season or current price is provided. The PDF is undated and uses some older tournament terminology, so it is a package guide, not a 2026 completeness census. [Tennis package PDF](https://enetpulse.com/wp-content/uploads/Tennis-Packages.pdf).

### Goalserve

Goalserve advertises ATP, WTA, Challenger, ITF, juniors, exhibitions and team competitions, XML/JSON, match statistics, point history and odds. Its FAQ describes five-second live point updates and UTC event times. Public tennis pricing shows **$150/month** and **$1,200/year**; six-month figures conflict between page sections ($900 versus $1,000), so they should not be treated as a reliable quote. [Price table](https://www.goalserve.com/enivacy-policy/sport-data-feeds/tennis-api/prices), [coverage](https://www.goalserve.com/en/sport-data-feeds/tennis-api/coverage), [description](https://www.goalserve.com/en/sport-data-feeds/tennis-api/description).

The public 2019 sample was downloaded and parsed; it demonstrates actual fields but also defects. Results are detailed below. Earliest production history, historic point timestamps, redistribution and model-training permission remain unverified. [Scores example](https://www.goalserve.com/en/sport-data-feeds/tennis-api/sample/34), [odds example](https://www.goalserve.com/en/sport-data-feeds/tennis-api/sample/35), [player example](https://www.goalserve.com/en/sport-data-feeds/tennis-api/sample/72).

### API Tennis — api-tennis.com

Published plans are **$40/$60/$80/$120 monthly**, with a 14-day trial and different request budgets; in-play odds/WebSocket appear on higher tiers. [Pricing](https://api-tennis.com/).

The v2.9.5 documentation supports date-range fixtures, inline scores/points/statistics, rankings, players, draws, and odds. It exposes event/player/tournament keys and singles/doubles/qualifying categories; default timezone is **Europe/Berlin**, with an override. No earliest complete season is guaranteed. Examples contain editorial inconsistencies: player key 1905 appears with Djokovic in a player example and Sinner in a news example. This is a documentation defect, not an established production ID collision. [REST documentation](https://api-tennis.com/documentation), [WebSocket documentation](https://api-tennis.com/documentation_websocket).

The published terms disclaim data guarantees and separately leave image rights to the consumer. They do not establish upstream official-data authorization or an explicit, perpetual bulk-training license. [Terms](https://api-tennis.com/terms-of-use).

### Live Tennis API — livetennisapi.com

The historical product advertises 97,901 reconstructed 2013–2022 ATP/WTA/Challenger matches, plus a 2023-onward collection including ITF and doubles. Historical plans list **$29/$99/$299 monthly**, and one-off month/year packages. Its strongest design feature is explicit separation of reconstructed and observed rows, separate ID spaces, coverage flags, and null timestamps where no observation exists. Its key weaknesses are upstream provenance and conflicting public documentation. No paid payload was audited. [Historical product](https://livetennisapi.com/historical-tennis-data-api).

The academic page offers a public Zenodo sample and application-based noncommercial access. It says live observation began **12 October 2025**, whereas the commercial page says **March 2026**. They cannot both be assumed to describe the same timestamp layer. The stated 98.2% having a sequence on the academic page also differs from the commercial page's 75% point-complete claim; those may be different metrics, not necessarily a contradiction. The archived sample labels its date at tournament level. [Academic release](https://livetennisapi.com/data/academic), [Zenodo DOI](https://doi.org/10.5281/zenodo.22048731).

Terms describe a best-effort single-region service, restrict raw redistribution and excessive storage, and make no accuracy guarantee. Reconcile those restrictions with sold bulk-history packages and intended long-term training retention before any purchase. [Terms](https://livetennisapi.com/terms).

The separate [public-data audit](public-tennis-data.md) downloaded the linked Zenodo files: its match index lacks winner/final-score columns, the player crosswalk is incomplete, and only 3,447 of 5,380 sampled tapes end at the declared winning-set threshold. Retirement or incomplete capture can explain some endings; this is not a measured corruption rate. The deposited README also differs from the website's provenance claims. See the [actual file audit](../../../data/studies/tennis_data_audit/public/table_audit.json) before treating the advertised archive counts as ready training rows.

### BetsAPI — betsapi.com

The published tennis event package is **$20/month, 3,600 requests/hour**. Separate bookmaker products have separate prices; the cheap tennis event package must not be represented as all bookmaker odds. Token-authenticated endpoints and rate limits are documented. Historical point/stat coverage and earliest reliable tennis date were not verified in this lane. This is a potentially inexpensive event-identity and result source, with provenance and licensed betting reuse unresolved. [Price table](https://betsapi.com/mm/pricing_table), [API documentation](https://betsapi.com/docs/). `betsapi.net` is a different domain and was not treated as the same provider.

### SportDevs

An official SportDevs Postman collection documents tennis endpoints for match statistics, game-level powers, team composition, leagues, and seasons. Examples include doubles teams and component IDs; Bearer authentication and pagination are specified. A named seasons endpoint is evidence of an API shape, not proof of a complete historical archive. The sample also contains generic placeholder values and a questionable gender field on a male doubles team; production accuracy remains untested. Reliable current pricing, earliest year, licensed source lineage, and historical point timestamps were not established. [Provider Postman documentation](https://www.postman.com/sportdevs-8904928/sportdevs-api/documentation/gzwmkab/tennis-api), [seasons endpoint](https://www.postman.com/sportdevs-8904928/sportdevs-api/request/azqyvzo/seasons-by-league).

### STATSCORE

The tennis-specific product advertises ATP/WTA/Challenger/ITF/Grand Slam coverage, draws/rankings, serve metrics and playing context, with Starter/Edge/Elite tiers. Its more general SportsAPI emphasizes edited pre/post-match data. Neither page proves an earliest tennis season, full point tape for all tours, or a public archive price. Requestable payloads and coverage should be evaluated as a separate feed purchase; widgets are not an export entitlement. [Tennis API](https://www.statscore.com/landing-page-tennisapi/), [SportsAPI](https://www.statscore.com/products/sportsapi/), [coverage inventory](https://www.statscore.com/coverage/).

### Broadage

Broadage explicitly includes tennis, provides an API documentation portal, and says subscribers joining midseason can access the whole active season. It says its test feed is real-time rather than scrambled. This establishes a testable commercial lead but **does not establish prior-season history**. Player and match photographs are excluded in its FAQ. Price, archival depth, match-level tennis statistics, and point history remain unverified. [API FAQ](https://www.broadage.com/support/api), [developer portal](https://www.broadage.com/developers/documentation/index).

### Data Sports Group

DSG lists 768 tennis competitions on its live homepage and markets historical data and modeling inputs. Its public tennis schema documents singles, doubles, mixed, team, wheelchair and soft-tennis disciplines, `generated_utc`, versioned output, stable discipline IDs, and XML/JSON. Those discipline categories need filtering before matching ordinary tennis markets. A tennis-specific historical start and competition-level depth are still unknown; broad claims of decades of data cannot fill that gap. [DSG coverage](https://datasportsgroup.com/), [tennis disciplines schema](https://dsg-api.com/doc/tennis/get_disciplines/923/), [analytics product](https://datasportsgroup.com/sportstech/).

### Tennis-API.com — a distinct, unresolved vendor

This similarly named site advertises ATP/WTA/Challenger/ITF, history, and odds in indexed primary text, but direct retrieval returned a challenge page. It is not api-tennis.com. No raw sample, history start, current price, or upstream license was verified. Keep it as a lead, not a substituted citation for another company. [Coverage page](https://tennis-api.com/api-coverage/).

## Specialist databases and private archives

| Source | What the evidence supports | Access and unresolved issues |
|---|---|---|
| **OnCourt desktop** | Claims 1.6m+ matches; ATP main 1990+, Challenger 1998+, qualifying 2000+, men's Futures 2004+, WTA 1997+, women's ITF $25k+ 2002 / $10k 2005, ATP/WTA doubles 2003+, team tennis and junior Slams. Statistics, Pinnacle odds movement, and point replays are features, without field-level history start dates. [Coverage](https://www.oncourt.info/index.html) | Windows license €48.95/year or €88.95 lifetime; update renewal €24/year published. Access-password and export are advertised, but data source, actual retained odds timestamps and betting/training rights need confirmation. [Order page](https://www.oncourt.info/order.html) |
| **OnCourt database distribution** | MySQL dump with an updater, players, tournaments, rankings, statistics and bookmaker odds; separate XML live feed. [Service](https://www.oncourt.info/tennis_provider.html) | Published $200 setup + $50/month for updates; XML live $50/month. Page is old/undated, so price is an observed listing, not a current quote. No installation/purchase attempted. |
| **TennisStats Premium** | Past seasons, singles/doubles and per-player CSV downloads explicitly offered. A concrete export route rather than merely rendered charts. [Premium](https://tennisstats.com/premium) | £9.99/month listed. No earliest year, whole-database export, upstream lineage, point archive, or model-training rights established. |
| **Tennis Insight** | Match previews, filterable player results/stats, trends, odds context and community observations down to Challenger/ITF. [About](https://tennisinsight.com/about-us/) | Public/basic/pro web tiers; €5/14 days, €20/3 months, €30/6 months, €50/13 months on signup. No verified bulk API/export or exact archive start. Community tips are separate observations, not ground truth. [Membership](https://tennisinsight.com/sign-up/) |
| **Ultimate Tennis Statistics** | Author explicitly identifies Sackmann-derived ATP data with corrections; no WTA, qualifying, Challenger or Futures inclusion promised on the inspected About page. [About](https://www.ultimatetennisstatistics.com/about) | Free frontend/code; not an independent premium data warehouse. Code Apache-2.0 does not license source data or every algorithm commercially. Docker database advertises season 2021, not current history. [Repository licenses](https://github.com/mcekovic/tennis-crystal-ball), [Docker snapshot](https://hub.docker.com/r/mcekovic/uts-database) |
| **TennisDB** | Public statistics and research, with explicit Sackmann-derived material and corresponding noncommercial/share-alike conditions. [Terms](https://tennis-db.com/terms) | Useful discovery/validation frontend; source independence and commercial data rights cannot be inferred from a different website name. |
| **TDI Tennis Data Platform** | Official description says umpire, performance and tracking streams can be combined, with historical archive and sandbox. [Platform](https://www.tennisdata.com/tennis-data-platform) | No public sandbox endpoint, admission rule, downloadable coverage matrix, archive year, or price found. A high-value private lead. |
| **ATP Tennis IQ / PIF** | August 2025 release describes player/coach access expanded across ATP and Challenger, scouting, video and wearables. [Release](https://www.atptour.com/-/media/sites/atp-tour/press/press-releases/atp-tennis-iq-august-2025-release.pdf) | Designed for players/coaches; this does not establish access for an independent trading project. Wearable heart/load data is especially distinct from public match statistics. [Wearables announcement](https://www.atptour.com/-/media/sites/atp-tour/press/press-releases/27-june-2024-atp-approves-in-competition-wearables.pdf) |
| **TennisViz** | Processes ball/player tracking into shot type, shot quality, situation and tactics; supplies performance/broadcast insights. [Product](https://tennisviz.com/), [TDI partnership](https://tennisviz.com/tennis-data-innovations-tennisviz-unveil-new-fan-insights-announce-partnership/) | Contact/contract route; earliest archive, raw-versus-derived access, per-court completeness, model version history and price unpublished. |
| **Hawk-Eye / SkeleTRACK** | Provider describes 29 skeletal points and seven racket points, extending tracking beyond center-of-mass information. [Technical description](https://www.hawkeyeinnovations.com/news/4211958/the-future-of-data-tracking-in-sport) | Hardware/data service and rights-holder relationships. Technology capability is not a public archive entitlement; tournament, court, year and export rights unknown. |
| **Golden Set Analytics / GameSetMap** | Claims private historical and trajectory data across tens of thousands of matches, serving selected players. GameSetMap's author confirms acquisition in 2017. [GSA](https://goldensetanalytics.com/why-use-analytics/), [GameSetMap provenance](https://gamesetmap.com/?author=1) | Bespoke, exclusive player service; no public dataset/API/price or betting license. Old site copy limits confidence about current inventory. |
| **Tennis Analytics / VS. Sports** | Indexed/video-linked analysis platform and a public 2019 professional match-report example show serve/return and rally-length statistics. [Current product](https://www.vssports.us/tennis/), [sample report](https://www.tennisanalytics.net/wp-content/uploads/2019/06/Tennis-Analytics-demo-match-report-2019.pdf) | Coaching/report service; full professional corpus, wholesale raw access and archive coverage not proven. Direct current product retrieval failed; indexed provider text available. |
| **TennisProfiler** | Author describes extensive manual observation and work used by federations, academies and ATP/WTA/ITF coaches. [Information](https://www.tennisprofiler.com/information) | Expert profiles and private charting lead; not a verified bulk historical dataset. |
| **Game.Set.Math** | Video-based tactical analysis and player-development service with amateur, transition and academy packages. [GSM](https://gsmtennis.pro/) | Quote-only; customer-upload analysis does not imply a licensable tour-wide archive. |
| **Tennis TV** | ATP match video plus classics dating to 1990 are advertised. [Premium FAQ](https://support.tennistv.com/hc/en-us/articles/21873145583004-What-is-Tennis-TV-Premium) | Viewing rights differ from download, charting redistribution, training, and data extraction rights. Archive selection is not comprehensive for all tour/court/year combinations. |
| **DTB tennis.de** | Federation ranking/LK archives and match portraits moved behind license/premium membership in 2025. [DTB notice](https://www.tennis.de/news/spielen/2025/mybigpoint-wird-zu-tennis-de---eingeschraenkte-nutzung-ab-mitte-.html) | Domestic-history enrichment lead, particularly for emerging players. Not a demonstrated Polymarket event dataset; bulk access and downstream commercial rights unknown. |
| **Court Shark** | Advertises historical match analytics and live market monitoring with 280k+ matches since 1991. [Product](https://courtshark.ai/) | Analytics UI, currently advertising $20/month introductory premium; no verified raw export or independent source lineage. Model predictions and real observations must remain separate. |

Tennis Abstract remains a major **public-source** ecosystem; no verified premium bulk-data product was found in this commercial search. It should not be listed as paid simply because other commercial services reuse similar tennis statistics. Tennis Navigator appears in older academic and competitor material, but a functioning current primary sales/API source was not established. Sportmonks' current FAQ/docs did not establish a tennis product; it is therefore **not counted as confirmed tennis coverage**. [Sportmonks FAQ](https://www.sportmonks.com/faq/).

## Direct quality audit: Goalserve public example

The [public score XML](https://www.goalserve.com/en/sport-data-feeds/tennis-api/sample/34) was retrieved at **2026-09-10T21:31:04Z** and parsed with a self-contained PowerShell utility. This is an actual downloaded documentation example for **26–27 February 2019**, not an authenticated query against the last year's production data.

| Check | Observed result |
|---|---:|
| Tournament blocks | 6 |
| Match rows | 142 |
| Distinct match IDs | 141 |
| Player/team rows | 284 |
| Singles player rows with empty ID | 19 |
| Doubles team rows with an empty component ID | 12 |
| Duplicate match IDs | 1 |
| Finished rows without exactly one winner | 1 |

The duplicate ID `40237712` attaches Rojer/Tecau to different opponents on different days. Event `40237710` is finished with neither winner marked and no games recorded. Doubles use separate component IDs; tiebreak-losing set values appear in strings such as `6.2`; deciding match tiebreaks can occupy the third-set field. A parser that assumes unique event IDs, integer set scores, two fully identified individual players, or a winner for every finished row will mishandle this example. These are observed example defects/encoding properties, **not estimated production error rates**.

Artifacts: [audit JSON](../../../data/studies/tennis_data_audit/commercial/goalserve-sample-audit.json), [downloaded XML](../../../data/studies/tennis_data_audit/commercial/goalserve-public-sample-34.xml), [reproduction utility](../../../src/eda/audit_commercial_tennis_sample.ps1). SHA-256 is recorded with the audit. The utility uses PowerShell directly and does not invoke or replace the project's Python environment.

## Market alignment and unresolved commercial questions

These are questions needed to evaluate evidence, not a build sequence or approval gate.

1. **Coverage:** For each actual Polymarket tournament, discipline and round, how many matches exist in the vendor's archived schedule, how many have statistics, and how many have complete points? Counts need denominators and a date-stamped coverage manifest. Separate ATP main, qualifying, Challenger, WTA 125/250, ITF men's/women's, doubles, team ties, exhibitions and outright markets.
2. **Identity:** Are IDs stable across postponement, opponent replacement, aliases, name changes, qualifier placeholders, walkovers, merges, and doubles pair changes? Does the vendor expose upstream official IDs and correction mappings? A Polymarket token/condition ID is still a separate identifier.
3. **Time:** Distinguish tournament start, scheduled match time, actual start, point occurrence, vendor capture, publication, correction and export generation. A point sequence without a wall clock can support score-state modeling, but cannot establish which score a trader knew at a historical market price.
4. **Outcome:** How are retirement, walkover, disqualification, abandoned/resumed play, awarded matches and different doubles tiebreak formats represented? A tennis database winner may differ from a particular market's settlement rule.
5. **History:** Do paid historical and live products share definitions? Is history corrected after the fact? Is there a retained revision log, or only the latest rewritten truth? Can the exact requested year be exported now, including events dropped after a rights change?
6. **Rights:** Does the contract permit internal betting analysis, model training, derived predictions, perpetual retained research copies, backup, combining vendors, and publishing aggregate results? Are prediction-market use and personal bettor use included, or only regulated operator/media use? What survives termination?
7. **Quality:** Can a bounded sample include a postponed match, a retirement, a walkover, two same-name players, a lower-tier doubles match and an early-round WTA 125/ITF match? Those cases test the real gaps more effectively than a hand-picked Grand Slam final.

A sportsbook odds archive is complementary evidence, not a replacement for historical Polymarket bid/ask, depth, fills and settlement rules. Conversely, market trade history alone does not reconstruct the tennis score observed at trade time. The intended data investigation needs both sides of that join, with ambiguous matches preserved explicitly.

## Licensing observations

Sportradar's official ATP addendum preserves TDI ownership, imposes integrity obligations, and requires return/destruction of licensed material at termination. Additional terms for official live ATP products restrict combining certain unofficial inputs. These are product-contract observations, not a claim that the same clauses apply to every media SKU. Retention and multi-source research rights need explicit agreement. [ATP addendum, 2 December 2024](https://sportradar.com/official-atp-addendum/?lang=en-us).

Stats Perform's standard MLA is an especially clear example of why **paid access does not itself authorize training or an archive**. Live Tennis API's bulk-history marketing also needs reconciliation with its general storage restriction. OnCourt is unusually explicit about own-development database access, but its broad statement does not settle every redistribution, upstream-rights or automated betting use. Publicly visible source code licenses and data licenses must remain separate.

The standard Stats Perform MLA also separately restricts betting activity and supplying derived odds, models or probabilities in section 4(r), except within the agreed Permitted Usage. Permission to retain data or train a model alone therefore does not settle permission for the intended betting application; the specific product agreement matters. [MLA, section 4(r)](https://www.statsperform.com/legal/mla-december-2025/).

The [machine-readable source register](commercial-sources.json) records provider URLs, evidence status, access/rights limitations and retrieval metadata. It includes negative findings and private leads intentionally: absence of a public download is not absence of valuable data, and an advertised feed is not proof that its history fits the market.

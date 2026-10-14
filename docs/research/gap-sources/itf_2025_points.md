# ITF points for January 2025 to February 2026: sources other than SofaScore

**Status: research, not a decision.** Checked on 13 October 2026, for the hole that work package P7 found in SofaScore's ITF point records ([P7 report](../../studies/gap_downloads/README.md#sofascore-by-edition-itf-work-package-p7)). Nothing was bought, no account was opened and nothing was decrypted. No request went to SofaScore, the ITF's live-data API or tennislive.net. One request reached itftennis.com by mistake (see [Requests made](#requests-made)).

## The hole

* **Size [observed].** P7's frozen target list (`data/studies/gap_downloads/sofascore_itf_points_2025_2026_matches.csv.gz`, frozen 12 Oct 2026 14:57 UTC) holds **42,876 ITF main-draw singles** in edition weeks from 30 Dec 2024 to 23 Feb 2026: men 21,316, women 21,560. P7's "about 40,000" counts the same matches more loosely.
* **Why SofaScore is empty [provider claims; inference].**
  * The ITF's official data moved from Sportradar to Infront from 2025 ([Infront, 15 Sep 2023](https://www.infront.sport/news/sports-media-rights/infront-secures-landmark-five-year-global-partnership-with-international-tennis-federation): five years of data and betting-streaming rights, "more than 58,000 tennis matches annually", 650+ umpire handheld devices).
  * Sportradar's API now lists its ITF tier as "up to 2024 only: data directly from ITF umpires via Sportradar devices ... Point-by-point from round 1" ([coverage tiers](https://developer.sportradar.com/tennis/docs/tennis-ig-data-coverage-tiers), page updated 28 Jul 2026).
  * Inference: the sites that took ITF points from the old feed lost them in 2025. The same break shows below in TennisLive (January 2025) and in Flashscore and the Live Tennis API (from July 2025).

## In short

* **Flashscore is the lead.** Its live site serves complete point records for ITF matches of 2025 (4 of 4 checked with a match duration on record; 0 of 4 without one). The handoff copy on disk holds **Flashscore match ids for 40,847 of the 42,876 targets (95%)**, so no listing is needed. By the duration proxy, about **28,400 targets (66%) have a complete record**: 93% of the targets in edition weeks to June 2025, 45% from July 2025 [inference from 8 checks].
* **The handoff copy itself has no points** [observed, all 965,501 records read]. It has results, set scores, start and end times, durations and two point-derived statistics.
* **TennisLive complements Flashscore.** In the ten careers' 285 men's matches of the window, TennisLive has partial points for 88 of the 96 that lack Flashscore's proxy [observed]. It has none in January 2025 [observed], where Flashscore's proxy covers 91% of the targets [inference].
* **The ITF's own API** holds complete records and statistics by match id for 2025 [observed on 5 of 6, earlier research], but ids for the window can still only be found for about 390 main-draw matches.
* **Paid vendors** do not look like they add matches. The Live Tennis API's index lists 29,381 targets, 27,811 of them also in Flashscore's proxy [observed]. The other vendors' claims are unmeasured.
* **No public dataset** with ITF points of 2025 was found on GitHub, Kaggle, Hugging Face or Zenodo.

## Sources

"Targets" are the 42,876 matches above. *Complete* means every set has as many games as the score, as in P6 and P7.

| Source | What it holds for the window | Targets reached | Route and cost | Evidence |
|---|---|---:|---|---|
| **Flashscore, live** (`df_mh` feed) | Complete points: server, score after each point, break/set/match-point flags, tiebreaks point by point. No ace or double-fault codes. Both tours, main draw | ≈28,400 complete (to Jun 2025 ≈93%; from Jul 2025 ≈45%) | 1 request per match, ids on disk for 40,847 targets; ≈30 h at 2 s + 1 s; free | 8 feeds read [observed]; coverage by proxy [inference] |
| Flashscore, handoff copy on disk | Results, set scores, start/end times, duration; "Last 10 balls" and "Match points saved" per set; box score on 44 records | 40,847 linked; no points | On disk | Census of every record [observed] |
| **TennisLive** | Partial points (set-closing games usually missing), 8 match statistics. Both tours; qualifying thin | ≈90% from Feb 2025; none in Jan 2025 | P8: 1 page per match, via P4's listings; ≈10 h for the ≈14,500 Flashscore lacks | Careers and pages on disk [observed]; not contacted |
| **ITF live-data API** (Stadion) | Complete points and 34-40 statistics by match id; qualifying where recorded | Ids for ≈389 main-draw singles | Ids are the obstacle: the draw sheets refused a browser today; one route untested | Earlier research and files on disk [observed]; not contacted |
| Live Tennis API | Index held (Zenodo v1.0.2). Points claimed for 99% of indexed ITF singles, 2023-25 "expanded after the match from a third-party feed" | 29,381 listed, 1,570 beyond Flashscore's proxy | $49 per month of history or $399 a year; Starter $29/mo; free academic programme (non-commercial) | Index [observed]; points [provider claim] |
| API-Tennis | `pointbypoint` in fixtures for past dates, ITF included | Unmeasured | $40-120/mo, 14-day trial; account needed | [provider claim] |
| Goalserve; Statscore; Enetpulse | Point-by-point for ATP, WTA, Challenger and ITF (Goalserve, Statscore); ATP and WTA only stated (Enetpulse) | Unmeasured | Goalserve $150/mo, "free 30 days trial"; others B2B | [provider claim; search snippets, except Goalserve's trial ([prices page](https://www.goalserve.com/sport-data-feeds/tennis-api/prices))] |
| Infront (official ITF data, 2025-) | The umpire-device feed for every covered match | Presumably all | B2B; no public or historical access stated | [provider claim] |
| Sportradar | Nothing: ITF World Tennis Tour "up to 2024 only" | 0 | – | [provider claim] |
| Tennis Explorer | Results, set scores, odds, head-to-head; no point or game progress | 0 points | – | 1 match page [observed] |
| AiScore | Unknown: Cloudflare challenge (HTTP 403) to a scripted client | – | Browser only | [observed block] |
| Apify actors (e.g. `crawlplant/tennis-point-by-point`) | Flashscore's records, resold | As Flashscore | $2 per 1,000 matches with points (free plan) | [provider claim] |

### Flashscore, live site

* **The feed [observed, 13 Oct 2026].**
  * The match page (`https://www.flashscore.com/match/<id>/`) carries the event's tab list in its common feed; for M15 Kotka, 21 May 2025 (Faurel v Wessels, id `pEB63x2M`) it is `DX: MH,OD,HH,DR`. MH is the point-by-point tab; there is no statistics tab (ST).
  * The page's own settings give the feed host and header: `https://global.flashscore.ninja/2/x/feed/df_mh_1_<id>`, header `x-fsign: SW9D1eZo` (`feed_sign` in the page). No login, token exchange or decryption.
* **What a record holds [observed; codes read from the data].**
  * Per game: games after it (`HC`/`HE`), server (`HG`), lost serve (`HH`) and the score after each point (`HL`). The game's last point is implied by the game winner.
  * Flags `|B1|` break point, `|B2|` set point, `|B3|` match point. Tiebreaks list every point with its server (`HD`/`HF` give the tiebreak score).
  * No aces, double faults or point times. That is the grain of SofaScore's records less the ace/double-fault codes.
* **The checks** (8 feeds, 4-5 s apart, all HTTP 200, no challenge):

  | Match (dump's date) | Duration in the dump | Feed |
  |---|---|---|
  | M15 Sharm El Sheikh, 30 Jan 2025 | 2:03 | complete, tiebreak included |
  | M15 Kotka, 21 May 2025 | 1:59 | complete |
  | W35 Kursumlijska Banja 2, 6 Aug 2025 | 2:05 | complete (3 sets) |
  | M25 Sheffield, 6 Feb 2026 | 3:05 | complete, tiebreak included |
  | W15 Kaltenkirchen, 30 Aug 2025 | – | empty |
  | W15 Santa Tecla, 2 Oct 2025 | – | empty |
  | M15 Tauranga, 17 Dec 2025 | – | empty |
  | W15 Antalya 4, 19 Feb 2026 | – | empty |

* **Sizing by the duration proxy [inference].** In the handoff copy, a match duration is filled when Flashscore recorded the match's end, which the 8 checks tie to the point record. Applied to the linked targets:

  | Edition weeks | Targets | Flashscore id on disk | With a duration (≈ complete points) |
  |---|---:|---:|---:|
  | 30 Dec 2024 - Jun 2025 | 18,897 | 17,720 | 17,553 (93%) |
  | Jul 2025 - Feb 2026 | 23,979 | 23,127 | 10,863 (45%) |
  | Men / women, all | 21,316 / 21,560 | 20,187 / 20,660 | 13,348 / 15,068 |

  By month, the window's records carry a duration for 97-99% to June 2025 and for 30-70% from July, except the men's December 2025 (16 of 637). The fall matches the Live Tennis API's index month by month (below).
* **"Last 10 balls" is not evidence of points.** It is on 99% of the window's records, including the four empty ones.
* **Not reached:** 2,029 targets did not link (540 ties, 1,489 without a candidate). The ids embedded in the head-to-head feeds add 26 of them. The rest would need Flashscore's event listings (about one request per event) or a better link.
* **Collecting.** One feed request per match: about 40,800 (or about 28,400 if the proxy is trusted, plus a check sample). At the plan's 2 s plus up to 1 s, about 30 hours. Nine requests met no block; behaviour at volume is unmeasured. Rights: Flashscore's terms forbid extraction; the [8 October decision](../../decisions/2026-10-08-scraping-approved.md) covers publicly served data, and the [collection plan](../../studies/gap_downloads/collection-plan.md#not-in-this-plan) lists a fresh Flashscore crawl as allowed.

### Flashscore, the handoff copy on disk

* **Read in full [observed].** 187 files, 965,501 records, none unparseable (`flashscore_full` 642,971; `flashscore_gql_stats` 47,401; `flashscore_bruteforce` 125,929; `flashscore_data` 97,749; `flashscore_daily` 51,451). Hugging Face commit `ea3d94d79f5d…`.
* **No point field anywhere.**
  * The keys are match facts, Flashscore's raw head-to-head feed (`h2h_json`: past results with ids, dates and set counts), a set summary (`sui_raw`) and up to 23 statistics (`stats_detail_json`).
  * `available_data`, Flashscore's own tab list, names the point-by-point tab (MH) on 88,586 of the 230,899 records that carry it, but the crawler never fetched that tab. No ITF record of the window carries `available_data`.
* **The window's ITF records** (tournament names `M15 …`, `W35 …`):
  * *Volume:* 42,791 distinct ids (men 21,258, women 21,533; M15 13,366, M25 7,892, W15 10,152, W35 5,852, W50 2,287, W75 2,378, W100 864).
  * *Draw:* no round field; 40,841 of them link to main-draw targets.
  * *Fields:* every one finished, with set scores for 99.5%. A duration, with distinct start and end times, for 29,614. "Last 10 balls" and "Match points saved" per set for 42,536. A box score for 44.
* **The link rule:** same tour; the Flashscore date within the edition week (Monday −3 to +8 days); each player's first surname word among a target player's name words; one candidate, or one whose grade is in the target's event name. By month, 88-98% of targets link (73-85% in the first week, 30 Dec 2024).

### TennisLive

Not contacted (reserved for other collectors). From files on disk:

* **The ten careers' 2025 ITF main draws** (`data/studies/point_shot_sources/scrape/verification_matches.csv`; men only) [observed]: points on 231 of 253, complete for 1. 177 lack only the set-closing games; statistics on 246.
* **By month:** none in January 2025 (0 of 18). The 16 January pages held (6 events) have no points and statistics on 15; 9 show the site's "not available" notice. Points from 3 Feb 2025 on, and on 99% of the careers' matches of 2026.
* **Against Flashscore** (the careers' 285 matches of Jan 2025 - Feb 2026, linked to the handoff records) [observed]:

  | | TennisLive points | none | All |
  |---|---:|---:|---:|
  | Flashscore duration (≈ complete points) | 174 | 15 | 189 |
  | No duration | 88 | 8 | 96 |

* **Expected for the targets [inference]:** partial points for about 90% of what Flashscore lacks, January 2025 excepted. P4's sample since June 2026 has points on 85 of 100 men's and 92 of 100 women's ITF main-draw pages.
* **Collecting:** P8 as planned, aimed first at the ≈14,500 targets without Flashscore's proxy: about 10 hours at P5's observed 1,430 pages an hour.

### The ITF's live-data API

Not contacted (reserved for P1 and P12). From files on disk:

* **It holds complete 2025 records [observed].**
  * The research of 29 Sep found statistics and points for 5 of 6 sampled 2025 main-draw matches ([lane C](../../../data/studies/gap_sources/research_notes/C_itf_listings.md)).
  * The staged ITF live-data tables (`data/dump/points/itf_live/`) hold 8 such matches of March-June 2025, with 94-148 points each.
* **Ids are the obstacle.**
  * *The day list* refuses dates more than 14 days back.
  * *Archived copies:* the Internet Archive's day lists on disk (`data/raw/gap_sources/itf/other/web.archive.org/stadion/`) include five inside the window. They hold 389 main-draw singles ids (30 Jan 2025: 124; 17 Mar: 6; 16 May: 116; 9 Jun: 9; 29 Jan 2026: 134) and 851 qualifying.
  * *Generic routes:* another session's probe today found them closed (`match/<id>?include=round.draw.event` 422; `round/`, `event/`, `match?filter[...]`, `event?filter[tennisId]` 404) ([itf_stadion_probe.json](../../../data/studies/gap_downloads/itf_stadion_probe.json)).
  * *itftennis.com's draw sheets (P12):* another session's Chrome probe today got the 2025 calendar and event filters, but `GetDrawsheet` answered HTTP 403 three times and the probe stopped (22:39 UTC; [itf_site_probe.json](../../../data/studies/gap_downloads/itf_site_probe.json)).
* **The last route, tested afterwards: closed [observed].** The ITF's widget library builds `custom/matchesByCourt/<id>`, with or without `?date=`. Asked for W75 Zagreb 2025's Stadion event id (`450e8ad4-…`), without a date and with `?date=2025-05-14`, it answered HTTP 404 both times (13 Oct 2026, about 23:05 UTC, 2 requests with receipts under `data/raw/point_sources/itf_stadion_probe/`).

### Live Tennis API

* **The index is held** (Zenodo record 23018680, v1.0.2, staged 8 Oct 2026) [observed].
  * *ITF singles in the window:* 14,376 men's and 15,596 women's, all main draw.
  * *Against the targets:* it lists 29,381; 27,811 of them also have Flashscore's proxy, so it adds 1,570 (557 of them from the week of 30 June 2025 on).
  * *Its fall from July 2025 tracks Flashscore's:* in December 2025 it has 16 men's matches.
* **Claims** (its pages, read 29 Sep 2026; copies in `data/raw/gap_sources/itf/other/livetennisapi.com/`):
  * *Coverage:* point sequences for 35,377 of 35,642 indexed ITF men's and 37,132 of 37,379 women's singles of 2023-Aug 2026.
  * *Source:* those of 2023-25 were "expanded after the match from a third-party feed, without capture timestamps". It also claims "ITF point depth from 2025 via the governing body's own umpire feed".
  * *Prices:* history from $29/mo (per match) or $99/mo (bulk); one-off $49 a month of history or $399 a year. The January 2023 onward data is free for "non-commercial academic research".
* **Inference.**
  * Its round labels ("M15 Gimcheon - Final") follow API-Tennis's form, as in the handoff's API-Tennis files, so its third-party feed is probably API-Tennis.
  * Either way, it covers nearly the same matches as Flashscore (27,811 of its 29,381).
  * The academic terms may not fit a betting project.

### SofaScore (other sessions)

Another session's probe today ([sofascore_uncovered_probe.json](../../../data/studies/gap_downloads/sofascore_uncovered_probe.json)) found, for 6 flagged events (one per sampled month):
* `/point-by-point` 404 for all 6;
* `/tennis-power` (SofaScore's momentum series) HTTP 200 for all 6, but empty (`"tennisPowerRankings": []`), as for the two controls with points, so it carries no point winners;
* `/statistics` 200 for 2, with six items only (aces, double faults, service points and games won, the longest runs).

### Datasets and sites with nothing for the window

* **Public datasets** (searches of 13 Oct 2026):
  * none with ITF points of 2025 on GitHub, Kaggle, Hugging Face or Zenodo;
  * [`livetennisapi/tennis-match-outcome-studies`](https://huggingface.co/datasets/livetennisapi/tennis-match-outcome-studies) is aggregates only ("no per-match rows"; CC BY 4.0);
  * the Live Tennis API's Zenodo record has points for June 2026 only;
  * the Kaggle SofaScore scrape `marcosjn2` ends in June 2025 and draws on SofaScore.
* **Tennis Explorer** ([match 2808045](https://www.tennisexplorer.com/match-detail/?id=2808045), Futures 2025, 26 Jan 2025): results, set scores, odds and head-to-head only.
* **Not checked:** 365Scores, LiveScore, Scores24 (no public statement found), BetsAPI (no claim found).

## Box scores (secondary)

* **Already held:** Sackmann's box scores cover most of the window. The [collection plan](../../studies/gap_downloads/collection-plan.md#p7-sofascore-in-chrome-itf-2025-2026-then-itf-2018-2024) counts them for 96% of the 49,180 Stage 0 matches of 2025-26 that P7 reaches.
* **Flashscore adds few** [observed]:
  * the handoff copy has a box score for 44 of the window's 42,791 records, and the page checked has no statistics tab;
  * its point records give points won on serve, break points and games per player, but not aces, double faults or first serves [inference].
* **Elsewhere:** TennisLive's pages carry 8 match totals, and the ITF API carries 34-40 statistics by match id.

## Recommendation (ranked)

1. **Flashscore point feeds for the 40,847 targets with an id on disk.**
   * Start with a seeded trial of about 200 across months and both tours, to measure the duration proxy; then the bulk (about 30 h at 2 s + 1 s).
   * Expected: about 28,400 complete records, mostly January-June 2025.
   * It needs no listing; P7's requests for these targets are almost all answered 404.
2. **TennisLive pages (P8) for what Flashscore leaves:** about 14,500 targets, mostly July 2025 - February 2026. Expected: partial points for about 90%, none in January 2025.
3. **The ITF's own API, if ids can be had.** It is the only route found to complete records, with statistics, for the second half of 2025. But the draw sheets refused a browser today, and `matchesByCourt` answered 404 for a 2025 event.
4. **Paid sources only if 1-3 fall short.** The Live Tennis API's index mirrors Flashscore's coverage; API-Tennis and Goalserve are unmeasured and need accounts; Infront's official feed is a commercial negotiation.

**For the owner:**
* any purchase or sign-up (Live Tennis API packages, about $500-700 for the window; API-Tennis or Goalserve trials; the academic programme; Infront);
* where a Flashscore package goes in the order of work.

The collection itself falls under the 8 October decision.

## Method

* **Census.** Each Flashscore file was streamed at below-normal priority (no file loaded whole), with key unions per folder, the statistic names, feed codes, ITF records by year and the window's distinct ids.
* **Links.** Flashscore and Live Tennis API records were linked to P7's frozen targets by tour, edition week and surname words (rule above).
* **TennisLive.** Its pages were read from `data/dump/points/tennislive/` (staged 10 Oct 2026) and the careers' verification table.
* **Scratch only.** The scripts and per-match tables were scratch files and are not in the repository; the counts above are their output.
* **The answers are kept.** The 8 point feeds and the match page read are copied, unchanged, to `data/raw/gap_sources/flashscore_itf_2025/` (gitignored): `df_mh_1_<id>.txt`, of which the four empty feeds are 0 bytes, and `match_pEB63x2M.html`.

## Requests made

All on 13 Oct 2026, UTC, one at a time:
* **www.flashscore.com:** 1 match page (22:39:44).
* **global.flashscore.ninja:** 8 point feeds (22:40:27-22:42:09), all HTTP 200.
* **tennisexplorer.com:** 2 pages (about 22:42-22:43).
* **aiscore.com:** 2 (HTTP 403 and a Cloudflare challenge, 22:44:41).
* **itftennis.com: 1 by mistake.** A fetch of the news article "Infront to become ITF Official Data Partner" at about 22:43 returned no content. The brief reserved that host. It came after the other session's draw-sheet refusal (22:39), so it did not cause it.
* **Vendor and press pages (about 22:44-22:52):** infront.sport, sporsora.com, tech.sportbusiness.com (403), apify.com, api-tennis.com (3), huggingface.co, developer.sportradar.com, goalserve.com.
* **Searches:** a search engine; no request to SofaScore, the Stadion API or tennislive.net.

## Limits

* **The proxy rests on 8 checks.** The trial in step 1 should measure it before the bulk.
* **Links by names.** About 5% of targets did not link; a few links may be wrong.
* **Men only for TennisLive's 2025 measure.** The careers are men; P4's 2026 sample has women's pages too.
* **Vendors' claims stay claims.** Nothing was bought or trialled.
* **Untested:** Flashscore's qualifying coverage was not measured.

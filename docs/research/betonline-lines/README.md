# BetOnline tennis lines, 2024–2026: where the opening and closing prices are

**Status: research, not a decision.** Checked on 6 October 2026; every URL was accessed that day. The owner then had OddsTrader's lines pulled: [results](#pulled-from-oddstrader-7-october-2026-utc). Three lanes ran in parallel (free websites and archives, odds APIs and paid vendors, published datasets), and the claims this page relies on were then re-checked directly. Labels: **observed** (a price, file or response actually seen), **documented** (the provider's own documentation), **provider claim**, **inference**, **unknown**.

**Nothing was bought and no account was opened.** OddsTrader's odds service was read for a coverage census and a six-request cross-check; its terms (below) govern any further automated use. **This repository is public:** raw prices from OddsTrader or The Odds API must not be committed, because both sets of terms forbid republishing them.

## The answer

One free source holds BetOnline's tennis opening and closing lines for all of 2024–2026. One paid source holds part of them under a licence that allows modelling. Nothing else checked covers 2024–2025.

| | 1. OddsTrader | 2. The Odds API (historical) | 3. OddsPapi |
|---|---|---|---|
| Cost | Free, no login | Paid only: $30/month (20k credits) to $119/month (5M) | Free key; historical calls do not count against the quota [documented] |
| BetOnline tennis seen | **2024, 2025 and 2026** [observed] | **2026** [observed]; 2024–25 **unknown** | Book listed; tennis **unknown** |
| Years | 2018 onward on sample dates | Per tournament: Slams from 2020–21, others from August 2024, 2025 or 2026 | January 2026 onward only [documented] |
| Opening and closing | First recorded line, last pre-match line and every move, each timestamped; moneyline and total games | Built from 5-minute snapshots | Every price change, timestamped [documented] |
| Matches reachable | About 97% of tour-level singles, qualifying included; no Challenger or ITF | At most 48% of 2024–26 main-tour matches: Slams, 1000s, some 500s | Unknown |
| Terms | Personal and informational use; "Automated access may require written permission" | Allows keeping the data and training models; no raw redistribution | No resale as a standalone product |

**Order suggested for the owner's decision:** ask OddsTrader for written permission for a one-off historical pull; if it is refused, buy a month of The Odds API.

## Pulled from OddsTrader, 7 October 2026 (UTC)

The owner chose to pull opening and last lines without asking first ([decision](../../decisions/2026-10-06-oddstrader-betonline-lines.md)). The pull took 339 requests with no block or error.
* Data: `data/raw/oddstrader/` and `data/dump/odds/oddstrader/`, both gitignored.
* Evidence (counts only): [data/studies/betonline_lines/](../../../data/studies/betonline_lines/README.md).
* `betonline_matches.parquet` has one row per singles match, with opening and closing prices and the flags below.

| Singles played, 1 Jan 2024 – 6 Oct 2026: 22,854 | Match winner | Total games |
|---|---|---|
| BetOnline opening and last line | 22,203 (97.2%) | 19,805 (86.7%) |
| Clean opening and close | 21,469 | 19,625 |
| Close flagged uncertain | 587 | 180 |

* **The project's main tour.** 14,713 of the 14,737 tennis-data.co.uk matches of 2024–2026 were found. 14,562 of them (98.8%) have BetOnline's opening and last match-winner line.
* **Timing** (match winner).
  * Openings came a median of 19 hours before the listed start; 10% within 7.6 hours, 10% over 52 hours.
  * Last lines: 75% at or before the listed start, 22% within 30 minutes after it, and 2.5% (561) later.
  * Half the last lines are marked off the board: the moment BetOnline took the market down.
* **Margins.** BetOnline's median overround is 1.039 on the match winner, at both opening and close, and 1.047 on total games.
* **Uncertain closes.** Late and broken closes are mostly the same matches: 379 of the 561 late last lines also fail the two-sided test, against 26 of the 21,642 on time. A close is flagged when it is stamped over 30 minutes after the listed start, or its two sides do not form a market (overround outside 1.00–1.15).
* **SportsBetting.ag** is the same feed. All 27,927 comparable opening lines equal BetOnline's in price, line and time, and 27,925 of 27,927 last lines do. It adds no match BetOnline lacks.
* **Total games** were thinner before 2026: 80–84% of matches in 2024–25, 97% in 2026.
* **Line history was not pulled.** It would take about 1,200 requests for the 587 flagged matches, and picking their close would still need actual start times.
* **Against Pinnacle** (study of 8 Oct 2026): BetOnline's 2024–2025 closes are as sharp as Pinnacle's, a tie at +0.3 milli-log-loss. Its margin is 3.75% against 2.79%. [Report](../../studies/betonline_lines/README.md).

## 1. OddsTrader

OddsTrader's ATP and WTA pages load their prices from the site's own odds service. It answered without a login or a challenge on 6 October 2026. For each match and bookmaker it serves:
* the opening line;
* the current line (for a finished match, the last pre-match line);
* the full line history.

Each price carries a millisecond UTC timestamp. Markets are moneyline and total games; there is no games handicap. BetOnline is book 8; its sister brand SportsBetting.ag is book 131.

**Prices seen** [observed; 2025 and 2026 rows fetched live for this check]:

| Match | BetOnline opening (UTC) | BetOnline last line (UTC) |
|---|---|---|
| US Open 2024 final: Sinner v Fritz | Sinner −375 / Fritz +305, 7 Sep 03:27 | −450 / +360, 8 Sep 08:33; eight recorded lines in all |
| Madrid 2025, 25 April: Raducanu v Kostyuk | Raducanu −105 / Kostyuk −115, 24 Apr 13:19 | −120 / +100, 25 Apr 08:02 |
| French Open 2026 first round: Monfils v Gaston | Monfils −105 / Gaston −115, 22 May 15:34 | −133 / +113, 25 May 18:27; 16 recorded lines in all |

**Book 8 is BetOnline's feed** [observed]. Its prices equal The Odds API's `betonlineag` prices at the same moments in both matches compared:
* *Monfils v Gaston, 25 May 2026.* The Odds API's 17:25 UTC snapshot shows Monfils −128 / Gaston +108. OddsTrader shows −128 / +108 in force from 16:54 to 18:16 UTC.
* *Vallejo v Norrie, 26 May 2026.* The Odds API's 11:55 UTC snapshot shows Vallejo −135. OddsTrader shows −135 from 11:51 UTC.

**Coverage.** The table counts singles matches with both a BetOnline opening and a last line [observed]. The website lane took the census. ATP 2025 and WTA 2026 were re-counted here from its saved files and agree. One day was re-measured live: Madrid, 25 April 2025, 16 of 17 singles matches.

| Year | ATP singles | WTA singles |
|---|---|---|
| 2024 | 4,070 of 4,163 (97.8%) | 3,853 of 3,988 (96.6%) |
| 2025 | 3,833 of 3,921 (97.8%) | 3,684 of 3,822 (96.4%) |
| 2026 (to about 2 Oct) | 3,333 of 3,404 (97.9%) | 3,337 of 3,464 (96.3%) |

These counts include tour-level and Grand Slam qualifying. No Challenger or ITF events were found on the service, and doubles are sparse. Sample dates in 2018–2023 were also mostly covered [observed by the lane, not re-checked].

**Before treating these as openings and closings:**
* *Opening.* It is the first line OddsTrader recorded for BetOnline, not a time BetOnline certifies. Slam first-round lines appeared about three days before play: 22 May for Monfils v Gaston on 25 May.
* *Closing.* The last recorded line can be stamped at or after the listed start; the US Open 2024 final's total moved at 18:15 against an 18:00 listing. Listed times are schedules, and the services disagree: Monfils v Gaston was listed at 18:30 on OddsTrader and 18:15 on The Odds API. A true close needs the actual start time from another source, with every line after it dropped. The project's match-timing windows are day-level, too coarse for this.
* *No documentation.* The service is undocumented and unsupported; field meanings were inferred from responses. It can change without notice.
* *Names.* Players appear as "Last, First" with OddsTrader's own ids, not ATP or WTA ids. Joins to project matches will go by name and date, so unmatched rows should be kept, not dropped.

**Terms** (updated 17 August 2026) [documented]:
* "You may use OddsTrader for lawful personal and informational purposes."
* "Automated access may require written permission. Do not overload systems, bypass rate limits, create a competing odds database through unauthorized extraction, republish proprietary feeds, circumvent access controls, or use data in violation of provider rights."
* The robots file signals `search=yes,ai-train=no,use=reference`.

A bulk pull for modelling is automated access, so written permission is the clean route.

## 2. The Odds API, historical snapshots

* **BetOnline tennis prices exist in the archive** [observed].
  * A third party saved two historical responses for `tennis_atp_french_open` (25 and 26 May 2026; [file](https://raw.githubusercontent.com/anthony-mccrovitz/Overlay/main/data/clv/closing/tennis_atp_french_open_2026-05-25_historical.json)). Their neighbouring snapshots are five minutes apart. `betonlineag` prices 26 of 40 and 24 of 41 listed matches.
  * A public [GitHub capture](https://github.com/kalyandinavahi0809/sports-odds-intelligence-platform) of the live feed holds pre-match BetOnline prices for 649 matches in 26 tennis tournaments, May–October 2026. 89% were captured only once, typically 0.8 hours before the listed start, so it is near-close at best.
* **2024–25: unknown.**
  * The provider's 2021 NFL sample has `betonlineag` on all 15 games, so the book was on the feed then [documented sample]. Whether it priced tennis in 2024–25 was not established.
  * "Historical data will only be available from the time that coverage is added for a sport, bookmaker or market" [documented].
* **Tournaments and start dates.** Each tournament is a separate key with its own start ([tennis page](https://the-odds-api.com/sports/tennis-odds.html)): "Grand Slams, ATP 1000, ATP 500, WTA 1000 and WTA 500".
  * Slams from 2020–21.
  * Canada, Cincinnati, Beijing, Shanghai (part), Wuhan and Paris from August–October 2024.
  * The other 1000s and Doha/Dubai from 2025.
  * 17 more tournaments, mostly 500s, from 2026.
  * Mainly match winner; "limited coverage" of game spreads and totals.
* **Reachable share of the project's main-tour matches.** This is the ceiling, assuming BetOnline priced every match in a covered tournament ([script](../../../src/eda/betonline_lines/odds_api_coverage.py), tennis-data.co.uk dump to 29 September 2026):

| Year | Reachable | Share |
|---|---|---|
| 2024 | 1,521 of 5,193 | 29% |
| 2025 | 2,670 of 5,149 | 52% |
| 2026 | 2,859 of 4,395 | 65% |
| **2024–2026** | **7,050 of 14,737** | **48%** |

* **Cost** [documented; arithmetic is inference].
  * Snapshots are taken every 5 minutes since September 2022. "Historical data is only available on paid usage plans."
  * A sport-level request costs "10 per region per market"; the event-level one costs that much per event. Empty responses are free. Up to ten named bookmakers count as one region.
  * The reachable matches fall on 880 tournament-days. A full 5-minute pull of match winners is 880 × 288 × 10 ≈ 2.5M credits: one $119 month, which also leaves room for the check.
* **Opening and closing.**
  * *Opening* = the first snapshot listing BetOnline.
  * *Close* = the last snapshot before the actual start. `commence_time` is the schedule and drifts; snapshots after the start carry in-play prices.
* **Terms** ([31 August 2026](https://the-odds-api.com/terms-and-conditions.html)): permits "Storing our data and retaining it indefinitely" and "Using our data to train statistical and machine learning models"; resale as a raw feed is prohibited.

## 3. Other routes checked

The SportsGameOdds and OddsPapi rows were re-checked against the providers' pages. The others are lane reports, with the evidence level they recorded.

| Source | BetOnline tennis 2024–26? | Why not, or what it holds |
|---|---|---|
| OddsPapi | Unknown | BetOnline listed (`betonline.ag`); history "since January 2026"; `/v4/historical-odds` "always free. Calls never increment your request count"; three books per call. A free key would settle it for 2026 |
| SportsGameOdds | No for 2024–25 | History "from February 2024" on Pro ($299/month). Per-book opening and closing only "since January 2026". Before that a finished event returns "the last price that bookmaker offered", which for live-priced matches is the price just before the end |
| The Rundown | No | BetOnline listed; tennis added May 2026; terms forbid training or validating any model without written consent |
| Odds-API.io | No | BetOnline listed; closing odds back to December 2025; no line movement for BetOnline |
| OpticOdds / OddsJam | No | BetOnline not in the public book list (LowVig is); API keeps a rolling two-month window |
| SharpAPI, Unabated, SportsDataIO | No or unknown | Long history enterprise-only; tennis or BetOnline not shown |
| BetsAPI | No | BetOnline not in its source list |
| BigDataBall | No | Tennis opening and closing 2024–2026, but from "Bovada or FanDuel… or any available sportsbook", not BetOnline |
| OddsWarehouse | No | Maximum and average odds only (tennis-data.co.uk style) |
| OddsPortal | No | Archived bookmaker lists show BetOnline switched off from December 2018 to the last snapshot (November 2023); terms forbid scraping |
| BetExplorer, TennisExplorer | No | Openings and moves for other books (bet365, Pinnacle and others), none BetOnline |
| Action Network, WagerTalk, OddsShark, SportsbookReview, Covers, VegasInsider | No | No BetOnline tennis column, no past dates, no tennis page, or line history behind a paid tier |
| BetOnline itself | No | No public feed, results page with prices, or line history; Wayback captures are empty JavaScript shells |
| Kaggle, Hugging Face, Zenodo, papers | No for 2024–26 | See [older years](#older-years). No paper using BetOnline tennis odds was found |

## Sister brands

* **SportsBetting.ag** [observed]:
  * Identical to BetOnline in 15,005 of 15,017 matched ATP rows of the 2011–2018 Kaggle file.
  * On OddsTrader from 5 January 2026, with openings identical in 242 of 242 and last lines in 241 of 242 (website lane).
* **LowVig** (The Odds API key `lowvig`): identical to BetOnline in 793 of 797 same-snapshot match-winner pairs, May–October 2026 [observed].
* Both can stand in for gaps, but they can differ for minutes, so label them separately.
* **TigerGaming:** not found with tennis prices anywhere checked.

## Older years

* **Kaggle, [ehallmar](https://www.kaggle.com/datasets/ehallmar/a-large-tennis-dataset-for-atp-and-itf-betting):** free, with no stated licence [observed].
  * 15,018 ATP matches with a BetOnline price, May 2011 to August 2018, mostly main tour, no WTA.
  * One price per match, dated but untimed, labelled neither opening nor closing.
  * Its book ids match the old SportsbookReview odds pages, which then carried BetOnline tennis [inference].
* **OddsTrader** sample dates 2018–2023 (above).

## Next checks (suggestions, not decisions)

1. **OddsTrader: done** without asking, on the owner's decision ([above](#pulled-from-oddstrader-7-october-2026-utc)). What remains is the 587 flagged closes. Their line history (about 1,200 requests) is only worth pulling together with actual start times to choose the close.
2. **A licensed fallback,** if OddsTrader's service closes or objects: one $119 month of The Odds API. Probe `betonlineag` on a 2024 and a 2025 Slam first; a $30 month allows about 2,000 such probes if only the check is wanted.
3. **Optional:** a free OddsPapi key shows whether BetOnline tennis is there for 2026.
4. **Keep prices out of git.** `data/raw/` and `data/dump/` are ignored; this repository is public, so no price may move into a tracked folder.

## Sources (accessed 6 October 2026)

* OddsTrader: [ATP page](https://www.oddstrader.com/atp/), [terms](https://www.oddstrader.com/terms-of-use/), [robots.txt](https://www.oddstrader.com/robots.txt)
* The Odds API: [historical data](https://the-odds-api.com/historical-odds-data/), [tennis keys and start dates](https://the-odds-api.com/sports/tennis-odds.html), [plans](https://the-odds-api.com/), [terms](https://the-odds-api.com/terms-and-conditions.html), [closing-line script](https://github.com/the-odds-api/apps-script)
* OddsPapi: [historical odds](https://oddspapi.io/us/docs/get-historical-odds), [requests and quota](https://oddspapi.io/us/docs/requests-and-quota), [BetOnline page](https://oddspapi.io/sportsbooks/betonline.ag)
* SportsGameOdds: [FAQ](https://sportsgameodds.com/docs/faq)
* Odds-API.io: [historical guide](https://docs.odds-api.io/guides/historical); The Rundown: [changelog](https://docs.therundown.io/changelog.md); OpticOdds: [historical endpoint](https://developer.opticodds.com/reference/get_fixtures-odds-historical); SharpAPI: [BetOnline page](https://sharpapi.io/sportsbooks/betonline-odds-api); BetsAPI: [odds](https://betsapi.com/docs/events/odds.html); BigDataBall: [tennis](https://www.bigdataball.com/datasets/tennis-data/); OddsWarehouse: [ATP](https://oddswarehouse.com/products/atp-mens-tennis-historical-sports-betting-odds)
* OddsPortal [terms](https://www.oddsportal.com/terms/); BetExplorer [tennis](https://www.betexplorer.com/tennis/); TennisExplorer [match page](https://www.tennisexplorer.com/match-detail/?id=2716791)
* Datasets: [ehallmar (Kaggle)](https://www.kaggle.com/datasets/ehallmar/a-large-tennis-dataset-for-atp-and-itf-betting), [GitHub capture of The Odds API](https://github.com/kalyandinavahi0809/sports-odds-intelligence-platform), [third-party French Open 2026 historical responses](https://github.com/anthony-mccrovitz/Overlay)

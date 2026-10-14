# Earlier-than-close tennis lines for Pinnacle and BetOnline: what exists, free and paid

8 October 2026 · Written for the owner · Research, not a decision. Every URL was accessed on 8 Oct 2026. Labels: **observed** (seen in data this project holds), **documented** (the provider's own documentation), **provider claim** (marketing or summary text), **inference**, **unknown**.

**The owner's question.** "Does it make sense to find a way to get EARLIER than closing line data for both betonline and pinnacle and train on that then bet then? is this possible with whats online, even if I paid?"

## The short answer

* **For training, the evidence says it would not help.** The [bet-timing study](../../studies/bet_timing/README.md) trained the model on BetOnline's opening line and on its last line, using the same rows, and fed both models the opening line.
  * They tie: +0.22 [−0.09, +0.54] mLL (+ = the opening-trained model better).
  * The model trained on closes is sized right at the opening.
  * Betting at BetOnline's opening line instead of its last line does not change the edge.
* **Early sharp lines have two other uses.**
  1. **Measuring whether betting Pinnacle early pays.** The project held no Pinnacle price before the close on 8 Oct. Since 9 Oct it holds Pinnacle's openings for 2018–Sep 2025 ([update below](#update-9-october-2026-pinnacle-on-oddstrader-and-pinnacles-own-site)).
  2. **A sharper input for Polymarket's early bets.** Fed Polymarket's own price 24 hours out, the model inherits 65% of that price's softness. Fed a sharp book's line from the same moment, it would inherit that line's error instead. *Inference:* better when the sharp line is sharper; untested.
* **Yes, it is possible.**
  * BetOnline's line history is free on OddsTrader. Openings and last lines are observed back to 2018; the full per-match history comes through the same service, untested before 2024.
  * Pinnacle's full line history is for sale from 2021 (BettingIsCool, from €99 a month), and as 5-minute snapshots from 2022 (The Odds API, $119–249 for one month).
  * Pinnacle's own API closed to the public on 23 July 2025.

## What exists

| Source | Books | What it holds | From | Cost | Status here |
|---|---|---|---|---|---|
| **OddsTrader's odds service** (adapter `src/ingest/oddstrader.py`) | BetOnline; SportsBetting.ag (the same feed) | Opening line, last line and **every line move with its time**. `lineHistory` is one side per request [observed: the adapter's research] | 2018 [observed: openings and last lines pulled for 2018–2026] | Free; about two requests per match | Openings and last lines held. Line history not pulled: about 68,000 requests for the 34,000 main-tour matches, about two days at the adapter's pace |
| **BettingIsCool Pinnacle Data API** ([api.bettingiscool.com](https://api.bettingiscool.com/)) | Pinnacle only | "Every odds movement for every event, ordered chronologically"; opening and closing lines with de-vigged probabilities; tennis moneyline, spreads and totals [documented] | 2021 [documented] | €99/month Starter (15-minute delay on live data), €199 Pro, €299 Enterprise, €599 Enterprise+; the same 2021– history on every tier [documented] | Not bought. Token cost per tennis match and bulk export: unknown |
| **The Odds API** ([historical guide](https://the-odds-api.com/liveapi/guides/v4/#get-historical-odds), [bookmakers](https://the-odds-api.com/sports-odds-data/bookmaker-apis.html)) | Pinnacle (EU region: "Odds are from public website which may incur a delay"); BetOnline (US and EU regions) [documented] | Snapshots of every event of a tournament: every 10 minutes from 6 Jun 2020, every 5 minutes from Sep 2022 [documented]. Tennis by tournament: Slams, 1000s and some 500s and 250s [documented] | Jun 2020 | Paid plans only for history; 10 credits per region per market per snapshot. $30/month for 20k credits, $59 for 100k, $119 for 5M, $249 for 15M [documented] | Not bought. The 6 Oct check found BetOnline's tennis history starting in 2020–21 for Slams and 2024–26 for other events [observed then]. *Inference:* hourly snapshots of every covered tournament, 2022–2026, both regions, are about a million credits, within one month of the $119 plan |
| **OddsPapi** ([historical-odds docs](https://oddspapi.io/us/docs/get-historical-odds)) | 350+ books including Pinnacle [documented]; BetOnline not confirmed | The full price history per bookmaker, timestamped [documented] | **January 2026** [documented] | Free developer tier; one call per 5 seconds, one fixture and at most three books per call [documented] | Too recent to train on; usable from 2026 onward |
| **BetExplorer / TennisExplorer / OddsPortal** | Pinnacle and others, not BetOnline | Openings and moves [observed on BetExplorer and TennisExplorer in the [BetOnline lines research](../betonline-lines/README.md)] | Many seasons | Free; covered by the [scraping approval](../../decisions/2026-10-08-scraping-approved.md). OddsPortal's odds feed is encoded | No scraper built; whether the moves carry exact times: unknown |
| **OnCourt** (Windows tennis database) | Pinnacle | "Odds movement" for past and upcoming matches [provider claim] | Unknown | Shareware ($38.95 in 2013) | Granularity and timestamps undocumented |
| **Betfair historical data** | Betfair Exchange (not a book) | BASIC: 1-minute last traded prices; paid tiers: the full order book [documented in the earlier archive research] | About 2015 | BASIC free with an account; paid tiers' prices are behind the login (the site refused this session's request: HTTP 403). Not available to US residents | The adapter `src/ingest/betfair_history.py` is ready; no account |
| **Pinnacle's own API** | Pinnacle | Live prices only, no history | — | "Closed for the general public since July 23rd, 2025"; access by application to api@pinnacle.com for "select high value bettors & commercial partnerships", academics and pregame handicapping projects ([summary](https://dev.to/ryankr/pinnacle-killed-its-public-api-heres-how-to-get-pinnacle-odds-in-2026-with-code-39pe)) [provider claim, quoted by third parties] | Third-party Pinnacle-sourced feeds have appeared since (PinnAPI, PinnWire, PinnOdds) [provider claims]; not evaluated |

**Also relevant.** tennis-data.co.uk's Pinnacle closes, the project's only Pinnacle prices, stop on 13–14 January 2026 [observed]. A model trained on Pinnacle's closes, and a live input that uses Pinnacle, both need one of the sources above from 2026 onward.

## Update, 9 October 2026: Pinnacle on OddsTrader, and Pinnacle's own site

From the [odds-sources study](../../studies/odds_sources/README.md), under the [scraping approval](../../decisions/2026-10-08-scraping-approved.md):
* **OddsTrader holds Pinnacle** [observed]. Its odds service serves the lines of about 60 books, not only BetOnline's. Book id 20 is Pinnacle: its last line equals tennis-data's Pinnacle close on 69% of 33,146 main-tour matches, and its margin is Pinnacle's (2.5%).
  * Its opening and last lines, each with a time, cover January 2018 to **7 September 2025**, on 77–97% of each season's main-tour matches; nothing after.
  * Both were pulled on 9 Oct for the matches tennis-data lists, 2018–2026: 491 requests, no block (`src/ingest/oddstrader.py --books-eids`).
  * So the project now holds Pinnacle prices before the close: an opening a median 35 hours before the listed start.
* **tennis-data's Pinnacle column stops being Pinnacle's close in August 2025** [observed]. It matched Pinnacle's own last line (both sides the same price) on 55–72% of matches every month from October 2024 to June 2025, then 50% in July and 14% in August and September, with a median gap ten times wider. *Inference:* the source lost Pinnacle's feed when Pinnacle's public API closed (23 July 2025), as OddsTrader did.
* **Pinnacle's website serves its prices to logged-out visitors** [observed]. Its pages read them from a "guest" service that the site's own configuration names (`www.pinnacle.com/config/app.json`).
  * Four probe requests on 9 Oct returned 106 upcoming tennis matchups with full-match moneylines.
  * Raw copies and receipts are in `data/raw/pinnacle/` (gitignored).
  * No adapter has been built. A live recorder of Pinnacle's prices is feasible and free.

## Suggested next steps (not decisions)

1. **Start recording live prices with their times:** BetOnline through OddsTrader, Polymarket through its API, and Pinnacle through a third-party feed or OddsPapi. That builds the training and evaluation history from now on, for any horizon, at no cost.
2. **For the Polymarket test (use 2 above),** the cheapest route:
   * BetOnline's line 24 hours out from OddsTrader's free line history, on the about 2,600 matches with a Polymarket 24-hour price: about 5,200 requests, about 4 hours.
   * Pinnacle's from one month of BettingIsCool (€99–199) or The Odds API ($119).
3. **Not suggested:** buying multi-season early-line history to train on. The bet-timing study found no gain from training on early prices.

## Sources

* [BettingIsCool: Pinnacle Data API](https://api.bettingiscool.com/) and [bettingiscool.com](https://bettingiscool.com/)
* [The Odds API: historical odds guide](https://the-odds-api.com/liveapi/guides/v4/#get-historical-odds), [bookmakers](https://the-odds-api.com/sports-odds-data/bookmaker-apis.html), [sports](https://the-odds-api.com/sports-odds-data/sports-apis.html)
* [OddsPapi: historical odds](https://oddspapi.io/us/docs/get-historical-odds)
* [Pinnacle API closure (DEV Community summary)](https://dev.to/ryankr/pinnacle-killed-its-public-api-heres-how-to-get-pinnacle-odds-in-2026-with-code-39pe), [pinnacleapi documentation (GitHub)](https://github.com/pinnacleapi/pinnacleapi-documentation), [Odds-API.io on the shutdown](https://odds-api.io/blog/pinnacle-api-shutdown-alternatives)
* [OnCourt (FastSpring store)](https://sites.fastspring.com/oncourt/)
* [Betfair historical data](https://historicdata.betfair.com/) (refused this session's request), [Betfair historic data workbook](https://github.com/betfair/historic-data-workbook)

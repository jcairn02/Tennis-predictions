# Lane F: who holds and sells the Slams' official data (24 Sep 2026)

Follow-up lane for [access routes](../../../../docs/research/granular-data-leads/access-routes.md). Question: can the Wimbledon, US Open and Australian Open point data (rows 2–5 of the [granular data leads](../../../../docs/research/granular-data-leads/README.md)) be bought or licensed from a paid service? Asking a rights holder for permission was out of scope. Read-only: no sign-up, trial, form, purchase, email or contact. The agent's report as returned, lightly edited; its scratch files stayed in the session scratchpad. Its HTML-to-text helper ran on the system `python`, not `./python.sh`.

**Labels:** [obs] read by the agent; [pc] provider claim; [3p] third-party report; [se] search excerpt only; [inf] inference; [ns] not stated; (WF) quoted through WebFetch. S-numbers point to the sources at the end.

## Bottom line

No paid route sells the historical IBM-grade Slam data, for any year [inf: none of the vendor pages or docs read offers them]. That data is:
- the per-point stroke/error "Sentence", including forced errors;
- serve width and depth, return depth, rally count, distance run and kick height;
- likelihood-to-win, TennisViz metrics and limb tracking.

Official Slam data is sold business-to-business, and live:
- **Sportradar:** Wimbledon, the US Open and Roland-Garros.
- **Infront Bettor**, and its US reseller **Catalist**: the Australian Open.

The only paid product with some history is Sportradar's Tennis API. Its history is short and its per-point fields thin. Its licence forbids betting and prediction-market use without written consent.

## Background checked

- **IMG ARENA** held Wimbledon, US Open and Roland-Garros betting rights (S7, WF). It never held the Australian Open. Stats Perform had the AO for 2023–25 [obs, S14]; Infront Bettor has it from 2026 [obs, S12].
- **Sportradar's purchase of IMG ARENA** was agreed on 19 Mar 2025 (S7, WF) and closed on 3 Nov 2025 [obs, S7]. On 4 Jun 2026 Wimbledon signed its first direct deal with Sportradar, "beyond 2026" [obs, S6].
- **The 30 Sep 2026 "closure" is half right.** The old imgarena.com host is retired that day, but the feed moved to a new domain (srarena.io) from May 2026. After 2026 the data moves to Sportradar's Live Data and Unified Odds feeds [obs, S1].
- **"Full shot and tracking data" at the Slams is unconfirmed.**
  - The player-and-ball tracking feed is documented, but the docs do not say whether it runs at the Slams.
  - Its sample data comes from a non-Slam 2022 match [obs, S3].
  - Its pages still list only the old domain [obs].

## Table

| Rights holder | Licensee / vendor | Product | Slams / years / tiers | Per-point fields | Archive? | Who may buy | Price | Licence limits (archive / ML / betting and prediction markets) | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| AELTC, USTA | Sportradar (ex-IMG ARENA) | "Tennis on DDE" legacy feed (REST + WebSocket) | Wimbledon (main draw and qualifying per S6), US Open, RG. The docs list organisations "ATP/AELTC/USTA/FFT" [obs] | **Umpire feed:** point start and end timestamps (ms), server, fault / foot fault (so serve number), Ace/DoubleFault/Standard, score. **Tracking feed:** stroke, "Error", "Forced", speeds, spin, distance, x/y/z [obs, S2, S3] | None documented. Replay only within a match; the stats stream has "no facility to replay" [obs] | Betting operators, who need a Bookmaker ID [inf, S5] | [ns] | Betting terms: destroy all data and anything derived from it at termination; no resale [obs, S10]. ML use not addressed [inf] | **Live only**, being retired |
| AELTC, USTA | Sportradar | Live Data XML / Unified Odds feed (the successor) | Events marked "GS*": RG, US Open, Wimbledon [obs, S4] | Point winner with an ace/double-fault flag, service fault, challenges. No stroke, winner or error types [obs] | Replay server: booked matches "can be replayed forever", others ≤60 days. It is a testing tool [obs] | Betting operators; "Kalshi and other licensed prediction market entities" and Kalshi's "brokers and market makers" [obs, S11] | [ns] | Same betting terms | **Live only** |
| All four Slams (not labelled "official") | Sportradar US | Tennis API v3 (media) | Tier 1 "Grand Slams"; a rolling window of the current season plus two adjacent editions [obs, S8] | Time (to the second), server, point winner, score, ace/double_fault/server_won/receiver_won, first-serve fault. Forehand/backhand winners, errors and unforced errors per match only, so forced errors can be derived per match, not per point [obs/inf] | Yes, about 2–3 editions | Businesses ("B2B"). The 30-day self-serve trial (1,000 calls) is for evaluation only; production goes through sales [obs, S9] | [ns] | Display on your own websites/apps only; no gambling or prediction-market use without consent; destroy "all historical data … derivatives" at termination [obs, S9] | **Paid but licence blocks our use** |
| Tennis Australia | Infront Bettor (Stats Perform had it 2023–25) | AO, AO qualifying and TA events: betting data and video | AO 2026–29 [3p/se, S20] | Umpire "live fast-path" data [pc]; no public spec [ns] | [ns] | "licensed sportsbooks" [pc, S12] | [ns] | [ns] | **Live only**; field depth unconfirmed |
| Tennis Australia | Catalist Sports (Infront's exclusive US reseller) | Official data for US sportsbooks and prediction markets | AO 2026– | "Level 2 and Level 3 official data" [pc, S13]; spec [ns] | [ns] | Licensed US sportsbooks; "market makers, quantitative trading teams and prediction-market platforms" [pc] | [ns] | The FAQ answers "Yes" to live trading, to settlement and to market makers on Kalshi/Polymarket [obs]. Archive and ML [ns] | **Live only.** The only route found that openly allows prediction-market trading; whether an individual can buy is unknown |
| AELTC, USTA | IBM | SlamTracker, Likelihood to Win, Serve Quality | — | — | — | — | — | Output feeds power the Slams' own apps [obs, S15] | **Not sold** |
| All | Hawk-Eye (Sony) | Tracking data | — | — | — | — | — | Acts as a processor for event organisers [obs, S16] | **Not sold** by Hawk-Eye |
| — | TennisViz | Performance and media portals (shot quality etc.) | Listed partners: TDI (ATP), USTA Player Development. No Wimbledon deal listed [obs, S17] | — | — | Players, coaches, media; demo request only | [ns] | [ns] | **Not sold** as data |
| Tennis Australia | Infosys | AO digital platform, Win Predictor | — | — | — | — | — | No data licensing mentioned (WF, S21) | **Not sold** |
| — | Golden Set Analytics; Immersiv | Golden Set: scouting for pros, "works only with selected clients" [obs]. Immersiv: only a 2017 Roland-Garros AR demo [se] | — | — | — | — | — | — | **Not sold** |

Related context:
- **Polymarket:** Sportradar now supplies Polymarket's US platform with "Tennis Grand Slams" data [obs, S11].
- **Kalshi and the US Open:** Kalshi's deal is sponsorship and integrity work, not a data sale [obs, S19].
- **Prices:** none are published anywhere.

## Key quotes

- **Domain change:** "enforced decommission of the imgarena.com and imgarena.dev domain urls by 30th September 2026. The new domain url will be srarena.io and will be made available in May 2026" [obs, S1]
- **Tracking feed:** "For availability of P&B Tracking feeds across specific Tournaments and Tours, please contact support@openbet.com" [obs, S3]
- **Wimbledon deal:** "continues Sportradar's exclusive global distribution of official data and AV betting rights. The agreement covers both The Championships main draw and the Qualifying Competition." [obs, S6]. The GlobeNewswire version says "establish our first direct agreement" (WF).
- **Tennis API coverage:** "Grand Slams | Extended match stats. 100% point-by-point from round 1." [obs, S8]
- **Tennis API history:** "Archive what you need before a season ages out of the rolling window" [obs, S8]
- **Terms (5 Aug 2026):** "Customer shall not use … any related data, content or outputs for any prediction market, trading platform, financial product or similar offering without Company's prior written consent" [obs, S9]
- **Betting terms (17 Feb 2025), 6.2:** "destroy all Services, products, solutions, content, and/or data in its possession that have been derived from the Services" [obs, S10]
- **Catalist FAQ:** "Can market makers use the feed on Kalshi, Polymarket, and other prediction platforms?: Yes" [obs, S13]
- **Hawk-Eye:** "These sports customers may make use of our data to enhance their commercial products and services, including certain data feed products they may provide to third parties." [obs, S16]

## Not determined

- **Prices and buyers.** No prices were found. It is also unknown whether an individual, rather than a firm or market maker, can contract with Sportradar's prediction-market unit, Infront or Catalist.
- **The AO field spec from Infront/Catalist.** Unknown whether they carry per-point forehand/backhand winner/forced/unforced and timestamps, whether they keep an archive, and what their contract terms are.
- **The tracking feed.** Whether it ever ran at Wimbledon or the US Open, and what happens to it after 30 Sep 2026.
- **Stats Perform's AO archive.** Whether it can supply its 2023–25 AO archive.
- **Wimbledon rights history.** When IMG ARENA's Wimbledon rights started. Stats Perform listed Wimbledon among its partners in 2023 [pc]; the nature of that is unverified.
- **US Open rights.** The length of the US Open rights deal.
- **Tennis API official status.** Whether its Slam data is official: tier 1 lacks the "Official data" label that tier 2 has.
- **Sportradar's conflicting clauses.** Clause 2.2 grants a licence "perpetual (solely for archiving purposes)", but 7.4 requires destroying everything at termination. Which prevails was not determined.
- **Wimbledon and AO site terms.** The pages need JavaScript to render. They were read separately by curl; see [access routes](../../../../docs/research/granular-data-leads/access-routes.md#terms-and-robotstxt-quoted).
- **Media distribution.** No official licensee for non-betting media distribution of Slam data turned up.

## Sources

- S1: https://docs.sportradar.com/tennis/domain-url-changes.md
- S2: https://docs.sportradar.com/tennis/stream-endpoints-websockets/events-id-stream-tennis/response-model.md
- S3: https://docs.sportradar.com/tennis/p-and-b-tracking-websockets/rally-summary-feed.md
- S4: https://docs.sportradar.com/live-data/introduction/information-per-sport/tennis.md and …/replay-server.md
- S5: https://docs.sportradar.com/audiovisual/migration-from-img-arena-to-sportradar-streaming-platform.md
- S6: https://sportradar.com/content-hub/news/sportradar-nets-official-wimbledon-tennis-data-and-av-betting-rights-deal/
- S7: https://sportradar.com/content-hub/news/sportradar-announces-close-of-acquisition-of-img-arena-and-its-strategic-portfolio-of-global-sports-betting-rights/ and https://www.sec.gov/Archives/edgar/data/1836470/000110465925025344/tm259190d2_ex99-1.htm
- S8: https://developer.sportradar.com/tennis/docs/tennis-ig-data-coverage-tiers.md, …/tennis-ig-historical-data.md, …/reference/sport-event-timeline.md
- S9: https://developer.sportradar.com/sportradar-updates/page/terms-and-conditions.md and https://developer.sportradar.com/getting-started/docs/your-account.md
- S10: https://sportradar.com/general-terms-and-conditions-betting-data/
- S11: https://sportradar.com/content-hub/news/sportradar-and-kalshi-announce-first-of-its-kind-data-and-infrastructure-global-partnership-for-prediction-markets/ and https://sportradar.com/content-hub/news/sportradar-and-polymarket-significantly-expand-prediction-market-partnership-to-more-than-20-global-sports-leagues-and-competitions/
- S12: https://www.infront.sport/news/sports-betting/infront-bettor-expands-tennis-portfolio-through-exclusive-australian-open-video-and-data-rights-partnership
- S13: https://catalistsports.com/news/catalist-sport-delivers-exclusive-australian-open-2026-data-to-us-sportsbooks/ and https://catalistsports.com/catalist-predictions-tennis-data/
- S14: https://www.prnewswire.com/news-releases/stats-perform-to-exclusively-distribute-australian-open-video-and-data-rights-in-extensive-new-partnership-with-tennis-australia-to-make-every-game-set-and-match-mean-more-301720198.html
- S15: https://www.ibm.com/new/product-blog/inside-the-ibm-architecture-that-powers-fan-engagement-at-the-us-open
- S16: https://www.hawkeyeinnovations.com/privacy-notice-for-sports-data
- S17: https://tennisviz.com/news/
- S19: https://news.kalshi.com/p/kalshi-us-open-official-prediction-market-partner
- S20: https://x.com/SportBusiness/status/1958848137029685648
- S21: https://www.prnewswire.com/in/news-releases/infosys-and-tennis-australia-bring-ai-first-experiences-and-accessibility-to-australian-open-2026-302673473.html

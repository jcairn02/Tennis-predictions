# Polymarket tennis market census

The accessible catalog is much broader than ATP/WTA main-tour match winners. It includes lower tours, qualifying, doubles, team competitions, exhibitions, tournament and season futures, and multiple score/finish contracts for the same match. **A sporting-results database and a history of tradable contracts are separate datasets that must be joined.**

This report is current research, not a roadmap or an approved source choice. Its principal evidence is a saved, reproducible snapshot of the public international Polymarket Gamma API, retrieved on **10 September 2026**. Polymarket US is a distinct product; no US-venue market census was performed. Every discovered event has an ID, original URL, dates, tags and series in the [event inventory](../../../data/studies/tennis_data_audit/polymarket/events.jsonl). Full contract rules, token/condition IDs and snapshot fields are in the [compressed contract inventory](../../../data/studies/tennis_data_audit/polymarket/markets.jsonl.gz).

## Scope and counting definitions

The requested calendar window is **10 September 2025 through 10 September 2026**, inclusive, implemented as `2025-09-10T00:00:00Z <= t < 2026-09-11T00:00:00Z`. The snapshot was taken before the last day ended; open and later-scheduled matches remain visible as open. This is a calendar-date interpretation, not an exact rolling 365-day interval ending at the retrieval second.

Two universes answer different parts of the question:

* **Sporting-date universe:** event `startTime`, otherwise `eventDate`, otherwise a date in the slug, otherwise `endDate`, falls in the window. This is the basis for the tables below. Fallbacks are flagged; an outright's end date is not a match timestamp.
* **Metadata trading-overlap universe:** the event's reported opening/start or creation date precedes the cutoff and its recorded final close does not precede the window. This retains futures traded before their eventual sporting outcome, and events with missing sporting dates. It is a candidate list, not proof of an actual fill during the interval.

The sporting-date universe contains **33,320 tennis event records and 406,190 distinct contracts** after removing nine confirmed college-football records incorrectly tagged tennis. Of those contracts, **166,512 have positive reported lifetime volume**, **510 explicitly report zero**, and **239,168 have missing/null volume fields**. Missing is not zero trading. There are 31,469 event records with positive reported lifetime volume. These are metadata observations, not an estimate of distinct physical matches, historical liquidity, or turnover during the year.

The broader metadata-overlap set has **33,474 event records with 409,313 attached contracts**, including 154 events outside or missing the sporting-date window. This count is at the event-wrapper level: 25 attached contracts had already closed before the window, so it is not a contract-level trading-overlap count. Seven closed contracts in the attached set lack a closing timestamp. The [overlap-only inventory](../../../data/studies/tennis_data_audit/polymarket/overlap-only-events.json) includes US Open futures ending after the cutoff, end-of-year ranking markets, qualification markets and other long-horizon questions. Do not omit those merely because their `endDate` lies outside the year.

These results come from **34,197 unique all-time records**: 34,192 under tennis tag `864`, plus five records under discovered tour/tournament tags that were absent from tag `864`. Cursor sweeps terminated normally; event and market IDs were checked for duplicates. [Audited metrics](../../../data/studies/tennis_data_audit/polymarket/audited-summary.json), [request manifest with hashes](../../../data/studies/tennis_data_audit/polymarket/request-manifest.json), [Gamma data model](https://docs.polymarket.com/market-data/overview).

**Completeness boundary:** this is a census of accessible records under discovered tags, supplemented by primary tour/tournament tags. It cannot prove the absence of deleted, untagged, privately available, or historically relabeled contracts. A positive lifetime volume field does not timestamp the trading; counting fills specifically inside the window requires trade records. No full-year trade-by-trade census or historical depth audit of every token was performed.

## Market families actually present

The following groups are mutually exclusive in this analysis. Series names describe Polymarket organization; they are **not a sporting tier taxonomy**. In particular, the ATP series includes Challenger and qualifying events; WTA includes WTA 125. Some Wimbledon events are assigned only to the Wimbledon series. Legacy doubles markets existed before the later doubles-series metadata was created.

| Catalog grouping | Event records | Contracts | Events with positive lifetime volume | Earliest sporting date in this grouping |
|---|---:|---:|---:|---|
| [ITF series](https://polymarket.com/event/itf-hipfl-ramos-2026-05-13) | 15,874 | 206,050 | 15,062 | 2026-05-13 |
| [ATP series (includes lower tiers / qualifying)](https://polymarket.com/event/atp-augeraliassime-vs-musetti-2025-10-08) | 8,730 | 99,239 | 8,182 | 2025-10-08 |
| [WTA series (includes qualifying / WTA 125)](https://polymarket.com/event/wta-tomljanovic-ruzic-2025-10-12) | 4,643 | 51,893 | 4,368 | 2025-10-12 |
| [ATP doubles series](https://polymarket.com/event/atp-doubles-ambrzei-olivvil-2026-05-13) | 1,817 | 22,938 | 1,767 | 2026-05-13 |
| [Wimbledon series only](https://polymarket.com/event/atp-faria-grenier-2026-06-22) | 801 | 13,782 | 742 | 2026-06-22 |
| [Legacy / other tennis (no recognized series)](https://polymarket.com/event/korea-open-laura-siegemund-vs-sofia-kenin-2025-09-15) | 754 | 3,691 | 658 | 2025-09-15 |
| [WTA doubles series](https://polymarket.com/event/wta-doubles-noskval-huntpeg-2026-05-13) | 701 | 8,597 | 690 | 2026-05-13 |

ITF accounts for almost half the event records in this sporting-date universe. A source restricted to main-tour singles therefore does not represent the observed market inventory. This is a coverage finding, not a recommendation to bet ITF or to weight every listed contract equally.

The [full competition/name inventory](polymarket-competition-inventory.md) lists observed league/title families with event counts, contract counts, date span and an example link. It deliberately preserves provider names instead of inventing a canonical tournament mapping. One physical match can have multiple event wrappers, and one town hosts multiple ITF editions in a year.

Lower-tier evidence is concrete. [Cassis: Droguet–Chazal](https://polymarket.com/event/atp-droguet-chazal-2026-09-07) is in the ATP product family; the ATP's [2026 Challenger calendar](https://www.atptour.com/-/media/files/calendar-pdfs/2026/2026-27-atp-challenger-calendar-as-of-18-jun-2026.pdf) lists Cassis, Tulln, Seville, Shanghai, Istanbul and Phan Thiet in that week's Challenger schedule. [Montreux's WTA page](https://www.wtatennis.com/tournaments/1112/montreux-125/2026) identifies it as WTA 125, not a WTA 250 main-tour event. Tour and tier must be joined from sporting evidence rather than guessed from `atp-` or `wta-` slugs.

## How the accessible inventory changes over the year

| Sporting month | Event records | Contracts | ITF-series event records | Events with positive lifetime volume |
|---|---:|---:|---:|---:|
| 2025-09 | 391 | 479 | 0 | 380 |
| 2025-10 | 789 | 1,057 | 0 | 787 |
| 2025-11 | 127 | 330 | 0 | 127 |
| 2025-12 | 22 | 234 | 0 | 22 |
| 2026-01 | 996 | 10,074 | 0 | 996 |
| 2026-02 | 1,186 | 11,445 | 0 | 1,186 |
| 2026-03 | 1,507 | 14,273 | 0 | 782 |
| 2026-04 | 1,598 | 14,637 | 0 | 1,596 |
| 2026-05 | 3,790 | 21,658 | 1,766 | 3,765 |
| 2026-06 | 5,907 | 71,407 | 3,363 | 5,889 |
| 2026-07 | 6,698 | 103,277 | 3,986 | 6,612 |
| 2026-08 | 6,514 | 97,877 | 4,182 | 6,048 |
| 2026-09 | 3,795 | 59,442 | 2,577 | 3,279 |

The first and last months are partial. The expansion in catalog breadth during 2026 changes the relevant training/data population. November–December also differ because of the tennis calendar. Neither effect can be reduced to a single average number of matches per week. The gaps between listed records and positive-volume records include missing fields, particularly in March and late summer; they must not be interpreted as zero trading or no demand.

Polymarket's August 2026 partnership announcement describes ATP/Challenger data and streaming rights and approximately 20,000 seasonal matches. That rights inventory is not interchangeable with the measured Gamma catalog or with active depth. See the [commercial rights analysis](commercial-tennis-data.md) for the distinction between distribution rights and actual historical access.

## Contract types and their historical labels

| Gamma contract type | Distinct contracts | Positive lifetime volume | First sporting date observed | Example |
|---|---:|---:|---|---|
| `tennis_first_set_totals` | 83,530 | 30,836 | 2025-11-07 | [Contract](https://polymarket.com/event/atp-sachko-tien-2025-11-07/atp-sachko-tien-2025-11-07-first-set-total-7pt5) |
| `tennis_match_totals` | 83,520 | 34,546 | 2025-11-07 | [Contract](https://polymarket.com/event/atp-sachko-tien-2025-11-07/atp-sachko-tien-2025-11-07-match-total-20pt5) |
| `tennis_set_games_totals` | 61,796 | 8,919 | 2026-06-10 | [Contract](https://polymarket.com/event/wta-preston-tan-2026-06-09/wta-preston-tan-2026-06-09-set-2-total-8pt5) |
| `tennis_set_handicap` | 37,555 | 17,181 | 2025-11-09 | [Contract](https://polymarket.com/event/atp-zverev-shelton-2025-11-09/atp-zverev-shelton-2025-11-09-set-handicap-home-1pt5) |
| `moneyline` | 33,116 | 30,722 | 2025-09-18 | [Contract](https://polymarket.com/event/atp-gille-vs-stalder-2025-09-18/atp-gille-vs-stalder-2025-09-18) |
| `tennis_set_totals` | 28,385 | 14,806 | 2025-11-07 | [Contract](https://polymarket.com/event/atp-sachko-tien-2025-11-07/atp-sachko-tien-2025-11-07-set-totals-2pt5) |
| `tennis_first_set_winner` | 27,685 | 14,305 | 2025-11-09 | [Contract](https://polymarket.com/event/atp-zverev-shelton-2025-11-09/atp-zverev-shelton-2025-11-09-first-set-winner-Zverev-vs-Shelton) |
| `tennis_completed_match` | 26,069 | 8,008 | 2026-05-09 | [Contract](https://polymarket.com/event/atp-heide-holmgre-2026-05-09/atp-heide-holmgre-2026-05-09-completed-match) |
| `tennis_set_winner` | 20,573 | 5,089 | 2026-06-10 | [Contract](https://polymarket.com/event/wta-preston-tan-2026-06-09/wta-preston-tan-2026-06-09-set-2-winner-preston-vs-tan) |
| `not_set` | 2,252 | 1,604 | 2025-09-15 | [Contract](https://polymarket.com/event/korea-open-laura-siegemund-vs-sofia-kenin-2025-09-15/korea-open-laura-siegemund-vs-sofia-kenin-2025-09-15) |
| `tennis_exact_score` | 889 | 93 | 2026-08-30 | [Contract](https://polymarket.com/event/atp-faria-brooksb-2026-08-30-exact-score/atp-faria-brooksb-2026-08-30-exact-score-player1-3-0) |
| `tennis_game_handicap` | 820 | 403 | 2026-08-22 | [Contract](https://polymarket.com/event/wta-udvardy-arango-2026-08-22/wta-udvardy-arango-2026-08-22-game-handicap-away-1pt5) |

An unset type includes older moneylines and non-match questions; it is not a single missing category to discard. The dates above are first observed sporting dates in the selected catalog, not independently established product launch dates. Multiple alternate lines explain why totals substantially outnumber matches.

| Target | Minimum sporting history needed to reconstruct a label | Additional market evidence |
|---|---|---|
| Match winner | Correct participants/teams, official winner/advancement, walkover/retirement/default status | Actual contract rule, token orientation, deadline and payout |
| Set winner | Ordered set scores; whether the set began/finished; format | Set number and rules if never played or unfinished |
| Game / set totals and handicaps | Set-by-set games and tiebreak interpretation; completed/incomplete status; best-of format | Exact line, period, inclusive/exclusive boundary and settlement rule |
| Exact score | Match-format-aware set score; match completion | Outcome enumeration, including any Not Completed alternative |
| Completed match | Explicit completion versus retirement/walkover/default/abandonment | Wording defining completion, not simply a winner field |
| Tournament winner / advancement | Full draw, round results, entrants/replacements, winner and tournament completion | Named selection, other outcome, withdrawal and cancellation handling |
| Season rankings / qualification | Ranking snapshots, points, calendar/qualification rules | As-of date and threshold; not a match-winner target |
| Conduct / participation / promotion props | Official announcements, reports, footage, or promoter's specific statistic | Source hierarchy and adjudicated rules; ordinary match CSVs are insufficient |

## Events a main-tour singles CSV misses

* **Qualifying:** [Fucsovics–Misolic, Japan Open qualifying](https://polymarket.com/event/atp-fucsovics-vs-misolic-2025-09-22). Draw stage matters even when both players are familiar main-tour names.
* **Doubles:** [Hangzhou Arneodo/Gille–Chandrasekar/Stalder](https://polymarket.com/event/atp-gille-vs-stalder-2025-09-18). A shortened slug or two outcome labels can conceal four underlying people; store pair membership and both component identities.
* **Team competition:** [2025 Davis Cup Spain–Germany semifinal](https://polymarket.com/event/davis-cup-semi-finals-spain-vs-germany) concerns a tie, not a single player match; [Laver Cup winner](https://polymarket.com/event/laver-cup) is a team tournament outcome. Rubber results, lineup and format are distinct inputs.
* **Exhibitions:** [Sabalenka–Kyrgios](https://polymarket.com/event/battle-of-the-sexes-aryna-sabalenka-vs-nick-kyrgios) explicitly uses special exhibition rules; [Garden Cup Paul–Kyrgios](https://polymarket.com/event/garden-cup-tommy-paul-vs-nick-kyrgios) and [Six Kings Slam](https://polymarket.com/event/six-kings-slam-alexander-zverev-vs-taylor-fritz) are further observed cases. Do not treat them as ordinary tour matches without format evidence.
* **Alternative formats:** [Next Gen Finals winner](https://polymarket.com/event/next-gen-atp-finals-winner) requires the tournament's actual format, not a hard-coded conventional set structure.
* **Non-score questions:** [Wimbledon racket break](https://polymarket.com/event/wimbledon-2026-any-player-to-break-a-racket-20260620155754557), [dress-code violation](https://polymarket.com/event/wimbledon-2026-any-player-to-violate-dress-code-20260620160431642) and [Kyrgios code violation](https://polymarket.com/event/wimbledon-2026-will-nick-kyrgios-receive-a-code-violation-20260618161544278). These require a different evidence source and should remain distinguishable from performance predictions.

## Measured quality of the market metadata

| Check | Observed result | Meaning |
|---|---:|---|
| Confirmed non-tennis records carrying tennis tag | 9 | Tags alone are not a clean sport filter |
| Selected date from `startTime` | 32,777 | Usually the most useful catalog schedule field; not proof of actual first serve or historical schedule revision |
| Selected date from `eventDate` | 476 | Date-only and potentially local; precision is weaker |
| Selected date from `endDate` | 67 | Mostly outright/other fallback cases, explicitly weaker |
| `eventDate` differs from UTC day in `startTime` | 3,328 | Could be timezone/scheduling semantics, not automatically wrong data |
| Median `endDate` minus `startTime` | 7 days | End date often includes a settlement buffer; using it as the playing date breaks joins |
| End/start separation at least six days | 30,416 | The date-field problem affects most of this sample |
| Missing event `gameId` | 2,834 | Cannot rely solely on this identifier for legacy and non-match markets |
| Distinct nonmissing `gameId` values | 30,315 | Still not a validated physical-match count |
| `gameId` values used by multiple event records | 169 groups | Often distinct wrappers/contracts; deduplicate deliberately for sporting joins |
| Repeated exact event-title groups | 116 | May be rescheduled duplicates or genuine rematches; title alone is unsafe |
| Missing contract condition ID / rule text | 0 / 0 | Good metadata presence, not proof of correctness |
| Token/outcome array-length disagreement | 0 | Necessary structural check passes; outcome meaning still needs interpretation |
| Closed contracts with snapshot prices 0.50/0.50 | 18,761 | Do not label every settled contract as binary 0/1 or interpret 0.50 as stake refund |

The [nine excluded records](../../../data/studies/tennis_data_audit/polymarket/excluded-non-tennis.json) are consecutive college-football events, including [Bethune-Cookman–South Carolina State](https://polymarket.com/event/cfb-bcook-scarst-2025-09-13). They were excluded using their sport/series metadata and checked titles. A complete semantic inspection of every event title was not performed; remaining misclassification is an explicit residual risk.

The 0.50/0.50 count is a snapshot-price pattern, not an independently verified on-chain payout count. Likewise, returned `outcomePrices` and final `lastTradePrice` are not historical pre-match prices. A settlement-quality study must compare the rule, sporting outcome, resolution lifecycle and actual payout.

## Match dates, availability and settlement are separate joins

Four clocks need to stay separate: sporting occurrence, provider publication, market observation, and resolution. A retrospective corrected result with an exact date is useful for a label but may not establish what a model could know before the match. A tournament-start date cannot timestamp the second round; a market's end date often follows the match by a week; a reconstructed point sequence without observation times cannot place each point against an actual historical order book.

The rule itself also changes the target. [Kudermetova–Kenin in September 2025](https://polymarket.com/event/wta-kudermetova-vs-kenin-2025-09-27) awards a walkover to the advancing player. The sampled 2026 moneylines in the [market-history report](market-history-and-odds.md) instead settle pre-start walkovers at 0.50/0.50. A single timeless rule for all Polymarket tennis would mislabel the history. A share bought at 0.80 and settled at 0.50 loses 0.30 before costs; it is not a zero-return sportsbook void.

The [public-data audit](public-tennis-data.md) includes a measured conservative join to an actual results payload, retaining ambiguous and unmatched events. It is evidence of some reconstructable overlap, not a certified all-market player crosswalk. The commercial report identifies alternate access routes for the categories that public main-tour files leave out.

## Reproducibility and limits

The [census utility](../../../src/eda/tennis_data_audit/polymarket_census.py) fetched `sports`, tennis tag metadata, and complete keyset event sweeps. It requested 500 rows, observed 100-row pages, and followed `next_cursor` until exhausted instead of assuming a short page ended the results. Additional sweeps used each discovered primary tennis tag while excluding tag 864. They found five older records; none changes the sporting-window count. Original response bytes are compressed, with URL, retrieval time, HTTP date and SHA-256 in the manifest. [Official pagination reference](https://docs.polymarket.com/api-reference/events/list-events-keyset-pagination).

The [offline analysis](../../../src/eda/tennis_data_audit/analyze_polymarket_census.py) applies the explicit date hierarchy, excludes confirmed football records, checks ID uniqueness, and produces the metrics and competition inventory. These are research utilities, not an approved ingestion architecture. They used an explicitly selected existing `ufc-monitor` Python interpreter with the standard library because the project's dedicated `tennis` environment is absent; no environment was installed or changed.

The snapshot is not transactionally frozen across every page. Pagination stabilizes traversal but does not prevent metadata from changing during retrieval. Gamma may revise old records, and the saved data is current truth rather than a complete revision history. Known gaps remain: full untagged/deleted discovery, a canonical competition/round crosswalk, physical-match deduplication, exact first-serve revisions, time-bounded fill counts, all-token historical prices, and representative historical L2 completeness. Those are limitations on conclusions, not an approved build schedule.

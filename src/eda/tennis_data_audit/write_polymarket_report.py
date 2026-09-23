"""Render the observed census tables into a research report, without new requests."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs/research/tennis-data-audit"
DATA = ROOT / "data/studies/tennis_data_audit/polymarket"


def main():
    s = json.loads((DATA / "audited-summary.json").read_text(encoding="utf-8"))
    raw = json.loads((DATA / "summary.json").read_text(encoding="utf-8"))
    text = """# Polymarket tennis market census

The accessible catalog is much broader than ATP/WTA main-tour match winners. It includes lower tours, qualifying, doubles, team competitions, exhibitions, tournament and season futures, and multiple score/finish contracts for the same match. **A sporting-results database and a history of tradable contracts are separate datasets that must be joined.**

This report is current research, not a roadmap or an approved source choice. Its principal evidence is a saved, reproducible snapshot of the public international Polymarket Gamma API, retrieved on **10 September 2026**. Polymarket US is a distinct product; no US-venue market census was performed. Every discovered event has an ID, original URL, dates, tags and series in the [event inventory](../../../data/studies/tennis_data_audit/polymarket/events.jsonl). Full contract rules, token/condition IDs and snapshot fields are in the [compressed contract inventory](../../../data/studies/tennis_data_audit/polymarket/markets.jsonl.gz).

## Scope and counting definitions

The requested calendar window is **10 September 2025 through 10 September 2026**, inclusive, implemented as `2025-09-10T00:00:00Z <= t < 2026-09-11T00:00:00Z`. The snapshot was taken before the last day ended; open and later-scheduled matches remain visible as open. This is a calendar-date interpretation, not an exact rolling 365-day interval ending at the retrieval second.

Two universes answer different parts of the question:

* **Sporting-date universe:** event `startTime`, otherwise `eventDate`, otherwise a date in the slug, otherwise `endDate`, falls in the window. This is the basis for the tables below. Fallbacks are flagged; an outright's end date is not a match timestamp.
* **Metadata trading-overlap universe:** the event's reported opening/start or creation date precedes the cutoff and its recorded final close does not precede the window. This retains futures traded before their eventual sporting outcome, and events with missing sporting dates. It is a candidate list, not proof of an actual fill during the interval.

"""
    text += f"""The sporting-date universe contains **{s['sport_window_tennis_events']:,} tennis event records and {s['sport_window_contracts']:,} distinct contracts** after removing nine confirmed college-football records incorrectly tagged tennis. Of those contracts, **{s['positive_lifetime_volume_contracts']:,} have positive reported lifetime volume**, **{s['zero_lifetime_volume_contracts']:,} explicitly report zero**, and **{s['missing_lifetime_volume_contracts']:,} have missing/null volume fields**. Missing is not zero trading. There are {s['positive_lifetime_volume_events']:,} event records with positive reported lifetime volume. These are metadata observations, not an estimate of distinct physical matches, historical liquidity, or turnover during the year.

The broader metadata-overlap set has **{s['metadata_overlap_tennis_events']:,} event records with {s['metadata_overlap_contracts']:,} attached contracts**, including {s['metadata_overlap_only_events']} events outside or missing the sporting-date window. This count is at the event-wrapper level: 25 attached contracts had already closed before the window, so it is not a contract-level trading-overlap count. Seven closed contracts in the attached set lack a closing timestamp. The [overlap-only inventory](../../../data/studies/tennis_data_audit/polymarket/overlap-only-events.json) includes US Open futures ending after the cutoff, end-of-year ranking markets, qualification markets and other long-horizon questions. Do not omit those merely because their `endDate` lies outside the year.

These results come from **{raw['all_time_unique_events']:,} unique all-time records**: {raw['discovery_counts']['tennis']:,} under tennis tag `864`, plus five records under discovered tour/tournament tags that were absent from tag `864`. Cursor sweeps terminated normally; event and market IDs were checked for duplicates. [Audited metrics](../../../data/studies/tennis_data_audit/polymarket/audited-summary.json), [request manifest with hashes](../../../data/studies/tennis_data_audit/polymarket/request-manifest.json), [Gamma data model](https://docs.polymarket.com/market-data/overview).

**Completeness boundary:** this is a census of accessible records under discovered tags, supplemented by primary tour/tournament tags. It cannot prove the absence of deleted, untagged, privately available, or historically relabeled contracts. A positive lifetime volume field does not timestamp the trading; counting fills specifically inside the window requires trade records. No full-year trade-by-trade census or historical depth audit of every token was performed.

## Market families actually present

The following groups are mutually exclusive in this analysis. Series names describe Polymarket organization; they are **not a sporting tier taxonomy**. In particular, the ATP series includes Challenger and qualifying events; WTA includes WTA 125. Some Wimbledon events are assigned only to the Wimbledon series. Legacy doubles markets existed before the later doubles-series metadata was created.

| Catalog grouping | Event records | Contracts | Events with positive lifetime volume | Earliest sporting date in this grouping |
|---|---:|---:|---:|---|
"""
    for c in s["classes"]:
        text += f"| [{c['label']}]({c['example_url']}) | {c['events']:,} | {c['contracts']:,} | {c['positive_volume_events']:,} | {c['first_date'][:10]} |\n"
    text += """
ITF accounts for almost half the event records in this sporting-date universe. A source restricted to main-tour singles therefore does not represent the observed market inventory. This is a coverage finding, not a recommendation to bet ITF or to weight every listed contract equally.

The [full competition/name inventory](polymarket-competition-inventory.md) lists observed league/title families with event counts, contract counts, date span and an example link. It deliberately preserves provider names instead of inventing a canonical tournament mapping. One physical match can have multiple event wrappers, and one town hosts multiple ITF editions in a year.

Lower-tier evidence is concrete. [Cassis: Droguet–Chazal](https://polymarket.com/event/atp-droguet-chazal-2026-09-07) is in the ATP product family; the ATP's [2026 Challenger calendar](https://www.atptour.com/-/media/files/calendar-pdfs/2026/2026-27-atp-challenger-calendar-as-of-18-jun-2026.pdf) lists Cassis, Tulln, Seville, Shanghai, Istanbul and Phan Thiet in that week's Challenger schedule. [Montreux's WTA page](https://www.wtatennis.com/tournaments/1112/montreux-125/2026) identifies it as WTA 125, not a WTA 250 main-tour event. Tour and tier must be joined from sporting evidence rather than guessed from `atp-` or `wta-` slugs.

## How the accessible inventory changes over the year

| Sporting month | Event records | Contracts | ITF-series event records | Events with positive lifetime volume |
|---|---:|---:|---:|---:|
"""
    for m in s["monthly"]:
        text += f"| {m['month']} | {m['events']:,} | {m['contracts']:,} | {m['itf_series_events']:,} | {m['positive_volume_events']:,} |\n"
    text += """
The first and last months are partial. The expansion in catalog breadth during 2026 changes the relevant training/data population. November–December also differ because of the tennis calendar. Neither effect can be reduced to a single average number of matches per week. The gaps between listed records and positive-volume records include missing fields, particularly in March and late summer; they must not be interpreted as zero trading or no demand.

Polymarket's August 2026 partnership announcement describes ATP/Challenger data and streaming rights and approximately 20,000 seasonal matches. That rights inventory is not interchangeable with the measured Gamma catalog or with active depth. See the [commercial rights analysis](commercial-tennis-data.md) for the distinction between distribution rights and actual historical access.

## Contract types and their historical labels

| Gamma contract type | Distinct contracts | Positive lifetime volume | First sporting date observed | Example |
|---|---:|---:|---|---|
"""
    for t in s["market_types"]:
        text += f"| `{t['type']}` | {t['contracts']:,} | {t['positive_volume_contracts']:,} | {t['first_sport_date'][:10]} | [Contract]({t['example_url']}) |\n"
    text += """
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

"""
    text += f"""| Check | Observed result | Meaning |
|---|---:|---|
| Confirmed non-tennis records carrying tennis tag | {s['known_non_tennis_excluded']} | Tags alone are not a clean sport filter |
| Selected date from `startTime` | {s['date_basis']['startTime']:,} | Usually the most useful catalog schedule field; not proof of actual first serve or historical schedule revision |
| Selected date from `eventDate` | {s['date_basis']['eventDate']:,} | Date-only and potentially local; precision is weaker |
| Selected date from `endDate` | {s['date_basis']['endDate']:,} | Mostly outright/other fallback cases, explicitly weaker |
| `eventDate` differs from UTC day in `startTime` | {s['startTime_vs_eventDate_utc_day_disagreements']:,} | Could be timezone/scheduling semantics, not automatically wrong data |
| Median `endDate` minus `startTime` | {s['median_endDate_minus_startTime_days']:.0f} days | End date often includes a settlement buffer; using it as the playing date breaks joins |
| End/start separation at least six days | {s['endDate_minus_startTime_at_least_6days']:,} | The date-field problem affects most of this sample |
| Missing event `gameId` | {s['missing_game_id']:,} | Cannot rely solely on this identifier for legacy and non-match markets |
| Distinct nonmissing `gameId` values | {s['unique_nonmissing_game_ids']:,} | Still not a validated physical-match count |
| `gameId` values used by multiple event records | {s['repeated_game_id_groups']:,} groups | Often distinct wrappers/contracts; deduplicate deliberately for sporting joins |
| Repeated exact event-title groups | {s['repeated_exact_title_groups']:,} | May be rescheduled duplicates or genuine rematches; title alone is unsafe |
| Missing contract condition ID / rule text | {s['missing_condition_id']} / {s['missing_resolution_text']} | Good metadata presence, not proof of correctness |
| Token/outcome array-length disagreement | {s['bad_token_outcome_alignment']} | Necessary structural check passes; outcome meaning still needs interpretation |
| Closed contracts with snapshot prices 0.50/0.50 | {s['closed_contracts_half_half_snapshot']:,} | Do not label every settled contract as binary 0/1 or interpret 0.50 as stake refund |

"""
    text += """The [nine excluded records](../../../data/studies/tennis_data_audit/polymarket/excluded-non-tennis.json) are consecutive college-football events, including [Bethune-Cookman–South Carolina State](https://polymarket.com/event/cfb-bcook-scarst-2025-09-13). They were excluded using their sport/series metadata and checked titles. A complete semantic inspection of every event title was not performed; remaining misclassification is an explicit residual risk.

The 0.50/0.50 count is a snapshot-price pattern, not an independently verified on-chain payout count. Likewise, returned `outcomePrices` and final `lastTradePrice` are not historical pre-match prices. A settlement-quality study must compare the rule, sporting outcome, resolution lifecycle and actual payout.

## Match dates, availability and settlement are separate joins

Four clocks need to stay separate: sporting occurrence, provider publication, market observation, and resolution. A retrospective corrected result with an exact date is useful for a label but may not establish what a model could know before the match. A tournament-start date cannot timestamp the second round; a market's end date often follows the match by a week; a reconstructed point sequence without observation times cannot place each point against an actual historical order book.

The rule itself also changes the target. [Kudermetova–Kenin in September 2025](https://polymarket.com/event/wta-kudermetova-vs-kenin-2025-09-27) awards a walkover to the advancing player. The sampled 2026 moneylines in the [market-history report](market-history-and-odds.md) instead settle pre-start walkovers at 0.50/0.50. A single timeless rule for all Polymarket tennis would mislabel the history. A share bought at 0.80 and settled at 0.50 loses 0.30 before costs; it is not a zero-return sportsbook void.

The [public-data audit](public-tennis-data.md) includes a measured conservative join to an actual results payload, retaining ambiguous and unmatched events. It is evidence of some reconstructable overlap, not a certified all-market player crosswalk. The commercial report identifies alternate access routes for the categories that public main-tour files leave out.

## Reproducibility and limits

The [census utility](../../../src/eda/tennis_data_audit/polymarket_census.py) fetched `sports`, tennis tag metadata, and complete keyset event sweeps. It requested 500 rows, observed 100-row pages, and followed `next_cursor` until exhausted instead of assuming a short page ended the results. Additional sweeps used each discovered primary tennis tag while excluding tag 864. They found five older records; none changes the sporting-window count. Original response bytes are compressed, with URL, retrieval time, HTTP date and SHA-256 in the manifest. [Official pagination reference](https://docs.polymarket.com/api-reference/events/list-events-keyset-pagination).

The [offline analysis](../../../src/eda/tennis_data_audit/analyze_polymarket_census.py) applies the explicit date hierarchy, excludes confirmed football records, checks ID uniqueness, and produces the metrics and competition inventory. These are research utilities, not an approved ingestion architecture. They used an explicitly selected existing `ufc-monitor` Python interpreter with the standard library because the project's dedicated `tennis` environment is absent; no environment was installed or changed.

The snapshot is not transactionally frozen across every page. Pagination stabilizes traversal but does not prevent metadata from changing during retrieval. Gamma may revise old records, and the saved data is current truth rather than a complete revision history. Known gaps remain: full untagged/deleted discovery, a canonical competition/round crosswalk, physical-match deduplication, exact first-serve revisions, time-bounded fill counts, all-token historical prices, and representative historical L2 completeness. Those are limitations on conclusions, not an approved build schedule.
"""
    (DOCS / "polymarket-census.md").write_text(text, encoding="utf-8")
    sources = [
        ("POLY01", "Polymarket Gamma sporting metadata", "https://gamma-api.polymarket.com/sports", "Public API observed", "Current sport/tag/series metadata; not historical listing coverage"),
        ("POLY02", "Polymarket tennis tag", "https://gamma-api.polymarket.com/tags/slug/tennis", "Public API observed", "Tag864; includes nine confirmed football false positives"),
        ("POLY03", "Gamma event keyset reference", "https://docs.polymarket.com/api-reference/events/list-events-keyset-pagination", "Documentation and endpoint observed", "Stable cursor sweeps; API capped request at100 rows; deleted/untagged universe not established"),
        ("POLY04", "Gamma market data model", "https://docs.polymarket.com/market-data/overview", "Provider documentation", "Event/market/token distinction; current metadata is not past executable quotes"),
        ("POLY05", "ATP Challenger 2026 calendar", "https://www.atptour.com/-/media/files/calendar-pdfs/2026/2026-27-atp-challenger-calendar-as-of-18-jun-2026.pdf", "Official sporting calendar", "Versioned calendar lists Cassis/Tulln/Seville/etc; not an actual match-time feed"),
        ("POLY06", "Montreux WTA125 2026", "https://www.wtatennis.com/tournaments/1112/montreux-125/2026", "Official tournament record", "Tier, draw sizes and edition; dynamic data may update"),
        ("POLY07", "September2025 walkover rule example", "https://polymarket.com/event/wta-kudermetova-vs-kenin-2025-09-27", "Market rules observed", "Advancing player wins pre-start walkover here; not the later50/50 template"),
        ("POLY08", "Davis Cup semifinal team market", "https://polymarket.com/event/davis-cup-semi-finals-spain-vs-germany", "Market observed", "Team tie outcome; not a single player match"),
        ("POLY09", "Sabalenka-Kyrgios exhibition", "https://polymarket.com/event/battle-of-the-sexes-aryna-sabalenka-vs-nick-kyrgios", "Market observed", "Special format and exhibition resolution sources"),
        ("POLY10", "Wimbledon conduct market", "https://polymarket.com/event/wimbledon-2026-any-player-to-break-a-racket-20260620155754557", "Market observed", "Conduct evidence required; match results alone insufficient")]
    records = [{"id": sid, "name": name, "url": url, "category": "Polymarket inventory / alignment", "coverage": limit,
                "granularity": "Metadata / contract rules / tournament calendar", "access": "Public read access",
                "rights": "Public visibility is not a blanket redistribution license", "evidence_status": status,
                "limitations": limit, "accessed_at": "2026-09-10"} for sid,name,url,status,limit in sources]
    (DOCS / "polymarket-sources.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print("Wrote polymarket-census.md and 10 source records")


if __name__ == "__main__":
    main()

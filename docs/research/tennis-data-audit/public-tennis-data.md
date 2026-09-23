# Public tennis data: coverage, source quality, and market alignment

Public tennis data is extensive, but there is no verified single free source that supplies current results, reliable match timestamps, historical pre-match information, complete point sequences, and reusable commercial rights across every tennis population offered by Polymarket. Deep historical singles results are much easier to obtain than current lower-tier data, doubles identity, timestamped points, original draw versions, or injury information known before a bet.

The requested sporting window is **10 September 2025 through 10 September 2026**. Observations below were made on 10 September 2026. A source bearing a `2026` filename does not necessarily reach September. This document distinguishes measurements of downloaded files, provider descriptions, existing local snapshots, and leads whose payloads were not examined. It is research evidence, not an approved source selection or implementation roadmap.

The most consequential findings are these:

- The original Sackmann ATP, WTA, general point-by-point, and Grand Slam point-by-point repository URLs returned **404** in this investigation. A public archival mirror works. Its 2026 main-tour match files stop at **25 May 2026 tournament dates**, with lower tiers reaching 1–2 June and rankings 8 June. The current Tennis Abstract website carries newer material; the website and downloadable archives have different freshness. [Original ATP](https://github.com/JeffSackmann/tennis_atp), [archival mirror](https://github.com/Aneeshers/tennis-sackmann-archive), [Tennis Abstract](https://www.tennisabstract.com/).
- **Tennis My Life has working, current public CSV downloads** for ATP, WTA, Challenger, qualifying, and ongoing events. Freshly inspected ATP ongoing records reach September 9, 2026 in their recorded date field. This materially improves the current-source picture, although mixed date semantics, key defects, and conflicting rights notices remain. [Current download page](https://stats.tennismylife.org/tennis-match-database), [payload audit](../../../data/studies/tennis_data_audit/public/tml_audit.json).
- Open Tennis Data provides a real downloadable replacement candidate with useful provenance, but its latest inspected release is explicitly a **preview**, has substantial missing cohorts, and is assembled from existing sources. Its 26,619 completed records contain only **68 quarterfinal rows**, versus 1,350 semifinal rows. The inspected 2025 Wimbledon cohort omits every quarterfinal. [Repository](https://github.com/ryantjx/tennis-match-data), [pinned release manifest](https://github.com/ryantjx/tennis-match-data/releases/download/data-v3-20260905T083014Z/manifest.json).
- There is measurable market overlap: **2,460 Polymarket event candidates** matched a unique public result by normalized full player names and a calendar date within one day. That covers 2,459 distinct sporting results and 25,255 attached contracts. It is a conservative linkage demonstration, **not** a market coverage percentage or settlement validation. [Candidate-link evidence](../../../data/studies/tennis_data_audit/public/polymarket_public_candidate_links.json).
- The Live Tennis API public Zenodo deposit is a substantial new resource: **173,571 match metadata rows**, 32,678 players, and **951,064 timestamped score-state rows** covering 5,380 June matches. However, its match index contains **neither the winner nor the final score**, and only 25.1% of players appearing in those matches have the advertised Sackmann crosswalk. Its public point tapes often stop before a declared match-winning set total. [Zenodo deposit](https://zenodo.org/records/22048731), [measured table audit](../../../data/studies/tennis_data_audit/public/table_audit.json).
- Official WTA draw PDFs contain more useful context than ordinary CSV datasets: qualifying and lucky-loser status, withdrawals, retirement reasons, and publication timestamps. Those are genuine research leads for injury/context work, but the final document's later information cannot be treated as known before earlier rounds. [Inspected Dubai 2026 draw](https://wtafiles.wtatennis.com/pdf/draws/2026/718/MDS.pdf).

The [50-source public register](public-sources.json) records access, coverage, rights, evidence status, and limitations. [Commercial sources](commercial-tennis-data.md) cover paid feeds and restricted products. Market-history findings are maintained separately in this research directory.

## Measured match between public results and Polymarket

The candidate-link exercise used the downloaded Polymarket event and market inventory and the immutable Open Tennis Data release `data-v3-20260905T083014Z`. Only events whose sporting date came from `startTime` were considered. A title had to split into two player names around `vs`; explicit doubles separators and question titles were excluded. Unicode accents, punctuation, and repeated spaces were normalized; no surname-only or fuzzy-name matching was used. A unique sporting result with the same unordered pair and a date within one calendar day produced a candidate.

| Result | Measured count |
|---|---:|
| Tennis-tagged event records in the raw sporting window | 33,329 |
| Excluded because date basis was not `startTime` | 543 |
| Excluded explicit doubles/question titles | 2,712 |
| Other titles not splitting into two names | 2 |
| Titles admitted to the pair comparison | 30,072 |
| Unique full-name/date candidates | **2,460** |
| Exactly the same calendar day | 2,340 |
| One-day calendar tolerance | 120 |
| Candidate events linked to ATP / WTA source rows | 1,284 / 1,176 |
| Distinct sporting results | 2,459 |
| Contracts attached to candidate events | 25,255 |
| Candidate source outcomes: completed / retired / walkover | 2,391 / 49 / 20 |

The raw tennis tag contains nine college-football false positives, removed in the separate census analysis. None acquires a tennis-result candidate here. The other unmatched records combine several different causes: genuine lower-tier or doubles populations outside this source, missing source results, names that require aliases, and date discrepancies. One cannot divide the candidate total by every tennis-tagged event and call the quotient a source coverage estimate.

The source itself has only **2,995 result rows in the requested window**, and the candidates span 15 September 2025 through 29 August 2026. It is not a September-complete result inventory. The 120 date-tolerant links need timezone, rescheduling, and official-result checks. Two market events point to one sporting result, which also needs inspection rather than silent deduplication. No tournament-name reconciliation or contract-by-contract outcome verification has been claimed.

The saved candidate file includes Polymarket event URLs, result identifiers, sporting date, players, tournament, score, status, source lineage, market IDs, condition IDs, outcome labels, and CLOB token IDs. The 49 retirement and 20 walkover candidates make the settlement problem concrete: knowing who advanced does not establish whether a match-winner, set, total, or handicap contract paid. [Link summary](../../../data/studies/tennis_data_audit/public/polymarket_public_link_summary.json), [unmatched records](../../../data/studies/tennis_data_audit/public/polymarket_public_unmatched.json), [reproducible comparison](../../../src/eda/tennis_data_audit/link_public_results_to_polymarket.py).

## Sackmann: deep history, available mirrors, and current gaps

The accessible [archival repository](https://github.com/Aneeshers/tennis-sackmann-archive) preserves upstream documentation and declares the same CC BY-NC-SA 4.0 license. Its [Hugging Face mirror](https://huggingface.co/datasets/Aneeshers/tennis-sackmann-archive) is alternate hosting, not a second independently collected dataset. The original repositories' 404 responses do not establish why they are unavailable or whether they will return.

The ATP upstream description distinguishes tour-level main draws, a combined tour-qualifying/Challenger file, and Futures files. Statistics were historically strongest at tour level from 1991, Challengers from 2008, and tour qualifying from 2011. Rankings are mostly complete from 1985, with intermittent earlier years and a missing 1982. Crucially, age and rank refer to `tourney_date`, normally the event's opening Monday. [Preserved ATP documentation](https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/atp/UPSTREAM_README.md).

The WTA layout is different: tour-level matches are separate from `wta_matches_qual_itf_YYYY.csv`, which combines ITF, tour qualifying, and some ITF qualifying. Looking for ATP-style WTA `qual_chall` or `futures` filenames produces 404s and would incorrectly imply there is no lower-tier women's data. [Preserved WTA documentation](https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/wta/UPSTREAM_README.md).

| Downloaded file population | 2024 rows | 2025 rows | 2026 rows | Latest 2026 `tourney_date` |
|---|---:|---:|---:|---|
| ATP main file | 3,076 | 2,944 | 1,449 | 2026-05-25 |
| ATP qualifying + Challenger | 11,190 | 11,629 | 5,745 | 2026-06-01 |
| ATP Futures | 18,423 | 17,906 | 6,894 | 2026-06-01 |
| WTA main file | 2,689 | 2,795 | 1,295 | 2026-05-25 |
| WTA qualifying + ITF | 38,281 | 21,615 | 8,975 | 2026-06-02 |

These are physical CSV row counts, not independently established tour completeness. The requested-window counts based on tournament date are ATP main 2,075, ATP qualifying/Challenger 8,841, ATP Futures 11,583, WTA main 1,772, and WTA qualifying/ITF 15,001 across the two files. They are useful inventory counts but **not exact match-date counts**. The 2025 US Open main draws fall before the requested September 10 boundary; historical Slam archives are relevant for deeper training history, not automatically part of the target-year cohort.

The raw data has several measurable quality issues:

- ATP main-file `w_ace` is missing in 259/2,944 rows in 2025 and 258/1,449 in 2026. WTA's equivalent is missing in 82/2,795 and 183/1,295. A result row is not proof that serve/return statistics exist.
- ATP Futures 2024 has no `w_ace` or match-duration values in any of its 18,423 rows, but only 480 of 17,906 ATP Futures 2025 rows lack `w_ace`. WTA lower-tier 2024 is missing that field in 35,487/38,281 rows; 2025 is missing it in only 431/21,615. The availability discontinuity is large enough to require a source/provenance explanation before estimating trends.
- WTA lower-tier row counts fall from 38,281 to 21,615 between 2024 and 2025, approximately 43.5%. That does not prove that the sport shrank. A change in represented populations, qualifying inclusion, or collection coverage is an unresolved explanation.
- The 2025 WTA main file mixes `Clay` and `clay`, contains 36 missing surfaces, and includes legacy or lower-tier-looking level values such as `50+H` and `35+H`. A fixed assumption that every main-file row is a WTA 250-or-higher match needs checking against actual tournament identity. Missing surfaces also occur in 2024 and 2026.
- The sampled ATP/WTA main files have no duplicated `(tourney_id, match_num)` keys. Basic serve arithmetic nevertheless identifies isolated rows where second-serve points won exceed the implied number of second serves: one ATP-main 2024 row, two side-level violations in ATP qualifying/Challenger 2025, and one each in WTA lower-tier 2024 and 2025. These checks detect only obvious inconsistencies, not all errors.
- The 2025 ATP main file contains 252 rows labeled `D`, and WTA has team-event rows too. Team competition belongs to the source population even when a simplistic “ATP season” label hides it.

The [CSV audit](../../../data/studies/tennis_data_audit/public/csv_audit.json) records every field's missingness, level/round/surface counts, duplicate checks, special score codes, player counts, and dates. [Arithmetic checks](../../../data/studies/tennis_data_audit/public/table_audit.json) and [source receipts](../../../data/studies/tennis_data_audit/public/fetch_receipts.json) preserve the exact evidence.

Sackmann supplies stable numeric player IDs that are valuable for longitudinal history. A source-specific player ID is not a universal tennis ID, however. Provider crosswalks, former names, transliterations, initials, and doubles teams still require explicit mapping. The archive includes ATP doubles files only through **2020**, consistent with the preserved README's suspension notice. It is not a source for present-year doubles, despite being a strong singles-history resource.

## Fresh public alternatives and why their qualifications matter

**Tennis My Life is a material current alternative.** Its live download page supplies separate ATP main, Challenger, ATP qualifying, WTA, and ongoing-tournament CSVs. The live website, rather than its older GitHub repository, is the current distribution point. Its ATP IDs can be linked to official ATP profiles; its date dictionary still describes the tournament week. The publisher says the WTA additions use previously available online CSVs and have weaker assurance than its ATP product. [Current database and downloads](https://stats.tennismylife.org/tennis-match-database), [historical repository](https://github.com/Tennismylife/TML-Database).

| TML file fetched September 10 | Rows | Latest recorded `tourney_date` | Missing winner ace count |
|---|---:|---|---:|
| ATP 2025 | 2,944 | 2025-12-22 | 193 |
| ATP 2026 | 2,132 | 2026-08-30 | 12 |
| WTA 2025 | 2,622 | 2025-11-14 | 108 |
| WTA 2026 | 1,968 | 2026-08-24 | 39 |
| Challenger 2025 | 6,411 | 2025-11-24 | 78 |
| Challenger 2026 | 5,389 | 2026-09-01 | 18 |
| ATP qualifying 2026 | 1,105 | 2026-08-28 | 5 |
| ATP ongoing | 124 | 2026-09-09 | 0 |
| WTA ongoing | 124 | 2026-08-30 | 0 |
| Challenger ongoing | 165 | 2026-09-07 | 0 |

These are fresh successful payload fetches, a stronger observation than simply reading a “daily updated” claim. They extend the current match/statistics options well beyond the Sackmann mirror. Season and ongoing files should not be concatenated blindly: completed matches may migrate between them, and their date fields need per-file examination. An initially attempted Challenger ongoing filename returned 404. Following the exact filename in the public manifest succeeded: 165 rows across Cassis, Genoa, Istanbul, Phan Thiet, Shanghai, Seville, and Tulln, including seven retirements. All 165 have winner/loser serve-stat fields, while both entry-code fields are blank throughout. This is an example of an initial failed URL concealing a working source. [Measured TML audit](../../../data/studies/tennis_data_audit/public/tml_audit.json), [public file manifest](https://stats.tennismylife.org/api/data-files).

The files also refute an unqualified “fully corrected” interpretation. ATP 2025 has 480 repeated `(tourney_id, match_num)` keys, driven by blank match numbers, despite no fully identical rows. ATP 2026 has two repeated keys: `2026-416/1` is attached to both a Munich match and a match labeled Rome Masters; Cincinnati's match number 79 is used for two different pairs. WTA 2026 has one malformed-width row and 64 missing winner IDs. These are observed defects in useful data, not grounds for discarding the source. The key choice and quarantines must accommodate them.

Rights are unresolved across the publisher's own surfaces: the website labels its dataset MIT, while the repository describes noncommercial use unless explicitly permitted and cautions about ATP/source rights. That conflict should remain explicit instead of selecting whichever statement is more convenient. No commercial permission was obtained. [Website notice](https://stats.tennismylife.org/tennis-match-database), [repository rights notice](https://github.com/Tennismylife/TML-Database#license--credits).

**Open Tennis Data.** The pinned September 5 release supplies Parquet files for completed matches, fixtures, players, tournaments, provenance, source policies, coverage, health, and quarantine. Measurements show 26,619 terminal rows, 24 fixtures, 1,216 referenced players, and 763 referenced tournament identities. The latest completed date is **29 August 2026**. The result table has 25,724 normal completions, 711 retirements, 179 walkovers, and five defaults. [Release manifest](https://github.com/ryantjx/tennis-match-data/releases/download/data-v3-20260905T083014Z/manifest.json).

Its own release reasons identify missing expected tournament/draw inventory and missing original source-retrieval timestamps. All 26,619 completed rows cite tennis-data.co.uk; 25,822 also cite Sackmann and 1,026 cite Wikimedia. Reconciliation therefore does not provide three independent collections. Quarantine contains 1,664 `unmatched_exact_date`, 842 `ambiguous_exact_date`, and 50 `conflicting_exact_date` observations. There are two rows with round `Qualifying competition` despite the declared main-draw-only scope. The severe quarterfinal gap is observable without guessing a hidden denominator: only 68 QFs across the entire release, and none in the 2025 Wimbledon result subset. [Measured release audit](../../../data/studies/tennis_data_audit/public/table_audit.json), [quarantine records](../../../data/studies/tennis_data_audit/public/open_tennis_quarantine_records.json).

The project excludes Challenger, WTA 125, ITF, qualifying, doubles, rankings, and match statistics. Its MIT software license does not apply to all underlying data rights; the data has source-specific terms and is represented as a research product. Its [source policy](https://github.com/ryantjx/tennis-match-data/blob/main/docs/SOURCES.md) treats Sackmann dates as tournament-level, keeps exact-date conflicts out of completed results, and distinguishes policy-blocked official-site adapters. That honesty is useful, but it does not remove the observed coverage deficits. [Data terms](https://github.com/ryantjx/tennis-match-data/blob/main/DATA_LICENSE.md).

**TennisData.app.** The download page advertises 2021–2026 ATP and WTA season CSVs covering main tours and Challenger events. It describes persistent player IDs, home/away orientation, `winner_code`, match statistics, and available match-winner/first-set odds, usually closing prices. It claims coverage above 95% and current files updated several times daily. The page is a promising current lead, but the download flow includes a bot check and the direct request returned 403. No CSV row count or completeness estimate was independently measured. Its permissive page language should be read alongside the actual terms and upstream rights before commercial use is assumed. [Download page](https://tennisdata.app/downloads/).

**Tennis Abstract's live pages.** The homepage and surface-speed tables contain 2026 material later than the downloaded GitHub metadata. The current website therefore remains worth investigating even though some original repositories are unavailable. It should not be treated as a supported live API or as a promise that every displayed statistic can be exported. [Current site](https://www.tennisabstract.com/), [surface-speed table](https://www.tennisabstract.com/reports/atp_surface_speed.html).

## Results plus bookmaker odds: the tennis-data.co.uk payload

Direct HTTP downloads returned 503; HTTPS retries failed during TLS negotiation. This audit therefore inspected **pre-existing local workbooks**, clearly distinguished from files freshly downloaded on September 10. The 2026 local ATP snapshot ends June 7 and WTA June 6. Their results do not establish current site freshness. [ATP source index](http://www.tennis-data.co.uk/alldata.php), [WTA source index](http://www.tennis-data.co.uk/alldataw.php).

| Local snapshot | Rows | Last match date | Bet365 pairs present | Pinnacle pairs present | BFE pairs present |
|---|---:|---|---:|---:|---:|
| ATP 2025 | 2,644 | 2025-11-16 | 2,632 | 2,534 | 651 |
| WTA 2025 | 2,505 | 2025-11-08 | 2,487 | 2,391 | 638 |
| ATP 2026 | 1,296 | 2026-06-07 | 1,293 | 71 | 1,198 |
| WTA 2026 | 1,248 | 2026-06-06 | 1,244 | 101 | 1,136 |

The table counts both cells being nonmissing, not valid executable prices. No one-sided bookmaker pairs were found. There are nevertheless **eight explicit zero cells** in the inspected 2025 bookmaker columns: two Bet365 and two Pinnacle cells in ATP, plus four BFE cells in WTA. Additional cells equal 1.00. A populated cell must therefore pass a decimal-odds validity check before conversion to probability; zero is neither an ordinary decimal quote nor the same as missing. The saved audit separates pairs present, pairs absent, one-sided pairs, explicit zeros, and odds at or below one. The last nonmissing `PSW`/`PSL` dates are **13 January 2026 for ATP** and **14 January 2026 for WTA** in these snapshots. The inherited claim that free Pinnacle closes ended in February is not supported by this measured local evidence. These dates describe the files, not a proven global shutdown date for the provider's feed.

The 2024 files lack `BFEW`/`BFEL`; these appear in 2025–2026. Missing bookmaker values and changing bookmaker composition mean `AvgW`/`AvgL` and `MaxW`/`MaxL` are not stationary substitutes for a particular book. None of these columns supplies a full timestamped price path, quote size, order book, or proof of execution availability.

Special outcomes are material: ATP 2025 contains 104 retired and 22 walkover rows; WTA 2025 contains 73 and 18. The local 2026 files contain 32/11 and 35/9 respectively. ATP 2024 also has two `Awarded` records. A loader that drops non-completed matches is changing the available market population and may remove exactly the contracts whose settlement behavior matters. See the full schema, per-column missingness, duplicate checks, and per-book last observation dates in the [table audit](../../../data/studies/tennis_data_audit/public/table_audit.json).

## Points and shots: several different products, not one data layer

**Match Charting Project.** The raw repository provides detailed human annotations of shot type, direction, return depth, errors, and associated aggregates. Its manually observed shot fields are different from the automated tennis scoring feeds' scoreboard states. [Project documentation](https://github.com/JeffSackmann/tennis_MatchChartingProject).

The downloaded match metadata contains **7,566 men's rows** and **4,080 women's rows**, ending at match IDs dated May 21 and May 24, 2026. Only 276 men's and 317 women's metadata rows fall in the requested year. There are two malformed-width men's rows and nine women's rows, plus one and seven duplicated match IDs respectively. Some short rows shift values into the wrong columns: a normal dictionary-based parser can read `RR` as a date or an umpire name as the surface. The malformed examples are preserved in the [table audit](../../../data/studies/tennis_data_audit/public/table_audit.json).

The website's January 2026 article discusses **17,000 charts**, while the retrieved GitHub match files total 11,646 rows. Those are different published surfaces and do not reconcile as a single current export. The metadata's optional `Time` field is missing in 3,472 men's and 2,411 women's rows; where present it can be informal local text such as `5pm`. It is not a standardized capture timestamp. [Publisher's 17,000-chart article](https://www.tennisabstract.com/blog/2026/01/03/17000-matches/).

MCP is valuable for bounded style/shot studies, including historical opponents, but chart availability is selected by contributor interest, available video, player prominence, and tournament. A chart submitted after an event may describe the match accurately while still being unavailable to a historical pre-match model. The source's CC BY-NC-SA terms also persist when the data is repackaged by a teaching site such as [SCORE's Grand Slam shot dataset](https://data.scorenetwork.org/tennis/tennis-shot-level-data.html).

**Grand Slam score-by-score archive.** The inspected mirror contains 166 CSV files for 2011–2024, with tournament/year and event-type differences. The 2024 US Open match files contain 253 singles, 125 doubles, and 30 mixed-doubles records, with blank `round` fields throughout these three metadata files. That is not evidence of an exhaustive 254/126/31 played-or-scheduled match census: withdrawals, collection gaps, and how unplayed matches are represented require reconciliation. It is also not a current-year source. Field populations vary across Slamtracker-style and transformed AO/French Open datasets. [Archived Slam directory](https://github.com/Aneeshers/tennis-sackmann-archive/tree/main/slam_pointbypoint), [preserved upstream description](https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/slam_pointbypoint/UPSTREAM_README.md).

**Older point strings.** Sackmann's separate `tennis_pointbypoint` project stores strings of server/returner outcomes with game/set delimiters, covering many lower-tier matches primarily around 2012–2015. Its README expressly describes incomplete coverage, possible duplicates, and retirement exclusion by its validation process. An absent ace/double-fault flag is not proof that no aces/double faults occurred. The original URL was not downloadable in this session, so this is documented historical availability, not an audited recent feed. [Project](https://github.com/JeffSackmann/tennis_pointbypoint).

**Live Tennis API's public observed-state sample.** The downloaded Zenodo index has 173,571 distinct match IDs and 23,683 participating player IDs; no self-matches or missing player foreign keys were found. Scheduled timestamps run from 1 January 2023 to 13 August 2026, with 50,399 records in the requested sporting year. Missing metadata includes 6,880 surfaces, 58,719 indoor flags, 3,130 tournament keys, 1,064 tier keys, and 5,643 rounds. Public `matches.csv` contains only match metadata and statuses, not a winner or final result. [Public deposit and dictionary](https://zenodo.org/records/22048731).

| Public point-sample property | Measured result |
|---|---:|
| Score-state rows / distinct matches | 951,064 / 5,380 |
| Missing server | 39,848 rows, 4.19% |
| Missing current-point score for each player | 5,710 rows, 0.60% |
| Negative / zero timestamp steps within match | 0 / 0 |
| Consecutive identical score states | 379 |
| Gaps exceeding five / thirty minutes | 6,213 / 468 |
| Median / maximum rows per match | 132 / 5,899 |
| Final state reaches declared best-of winning set count | 3,447 matches, 64.1% |

Capture timestamps run from June 1, 2026 12:09 UTC through July 1 03:32 UTC, which is consistent with a June-match sample extending past midnight. Every sampled match ID joins to the public index. Long gaps can reflect rain, suspensions, or missed observation; the audit does not label every gap an error. Similarly, the 35.9% whose last state does not show the winning set total includes possible retirements and scoreboard truncation. It cannot be treated as a complete final-score label without replay and status checks. State rows are not necessarily one completed tennis point each, and the 5,899-row maximum warrants inspection of transitions before estimating rally or point counts.

The player's `sackmann_id` field is populated for 6,304/32,678 profile rows. Among the 23,683 players actually used, only 5,947, or **25.1%**, are mapped. Both participants are mapped in 120,435/173,571 matches, or 69.4%. Missing biography is extensive: 24,285 countries, 24,944 birthdays, and 30,685 handedness values. The crosswalk is helpful for popular-player matches, but the statement that the ecosystems simply “join cleanly” overstates lower-tier identity completeness.

The deposit README and current website also conflict. The downloaded README says live recording since January 2023 and approximately 75% point coverage; the current academic page says observed collection began **12 October 2025**, with 98.2% having some point sequence and only 22,031 matches having live-observed states. These may involve different provenance classes and revised documentation, but they are not interchangeable claims. The public sample is real and audited; completeness of the private corpus remains a provider claim. No contact or academic application was made, and this betting project should not assume qualification for a noncommercial academic program. [Current academic description](https://livetennisapi.com/data/academic), [commercial audit](commercial-tennis-data.md).

## Official sources: useful coverage beyond the usual CSV lists

The official sites are valuable as authorities for draw structure, match outcomes, entry status, and contextual facts. Public visibility is not evidence of a supported bulk feed. Dynamic rendering, blocked requests, revisions, and separate data rights make them different acquisition problems from downloadable CSVs.

| Population / information | Specific official sources | What was established | Remaining limitation |
|---|---|---|---|
| ATP tour and Challenger results | [ATP 2025 archive](https://www.atptour.com/en/scores/results-archive?year=2025), [ATP stats](https://www.atptour.com/stats/) | Tournament archive includes singles/doubles result links; official statistical pages exist | 2026 archive/ranking requests returned 403; no complete bulk payload audited |
| WTA main, qualifying, doubles | [Dubai 2025 draw tabs](https://www.wtatennis.com/tournaments/718/Dubai-500/2025/draws), [2026 static draw](https://wtafiles.wtatennis.com/pdf/draws/2026/718/MDS.pdf) | Distinct draw types, seeds, byes, entry codes, scores and special outcomes | Final draw PDFs do not preserve every original bracket version |
| Rankings | [WTA singles rankings](https://www.wtatennis.com/rankings/singles), [ATP rankings](https://www.atptour.com/en/rankings/singles) | WTA visible rows include points, age, tournament count and a by-date filter | Current rank does not imply historical publication-time availability |
| ITF men's/women's/junior events | [World Tennis Tour results](https://www.itftennis.com/en/tournament-calendar/results/?categories=All&circuitcode=WT&matchtype=S), [women's calendar](https://www.itftennis.com/en/tournament-calendar/womens-world-tennis-tour-calendar/), [live scoring](https://www.itftennis.com/en/world-tennis-tour-live/) | Circuit filters and official event results/calendar exist | Results round-up shows finalists; the complete match history requires individual draws; point retention not established |
| Australian Open | [Past-draw page](https://ausopen.com/history/past-draws/mens-singles) | This particular static page links men's PDFs for 2007–2019 | It does not substantiate 2025–2026 coverage; current AO result surfaces need separate inspection |
| Roland-Garros | [Official results](https://www.rolandgarros.com/en-us/results), [ATP 2025 draw](https://www.atptour.com/en/scores/archive/roland-garros/520/2025/draws) | Official and ATP draw routes exist; event-type breadth extends beyond singles | Dynamic result routes and year handling need validation |
| Wimbledon | [2025 men's draw PDF](https://assets.wimbledon.com/archive/draws/pdfs/draws/2025_MS_A4.pdf), [archive frontend](https://www.wimbledon.com/en_GB/draws/archive) | A static archived draw exists | Frontend extraction mostly returned UI; complete statistics archive not bulk audited |
| US Open | [2025 men's draw PDF](https://www.usopen.org/en_US/scores/draws/2025_MS_draw.pdf), [year-by-year history](https://www.usopen.org/en_US/visit/year_by_year.html) | Public bracket includes entry codes and special score annotations | Bracket-column text extraction needs visual reconciliation; no quote or capture times |
| Davis Cup | [2025 results](https://www.daviscup.com/en/draws-results/2025/finals) | Finals, qualifiers, and world/regional groups have official archive routes | A tie and an individual rubber are different targets; extracted page lacked the dynamic rubber payload |
| Billie Jean King Cup | [2025 results](https://www.billiejeankingcup.com/en/draws-results/2025/finals) | Finals, qualifiers, playoffs and regional-group structure | Same team/rubber and dynamic-payload caveats |
| United Cup | [Official results](https://www.unitedcup.com/en/scores/results) | 2026 results display individual matches, mixed doubles, tie scores, court, umpire and duration | Duration is not actual UTC start; tie-winning and player-winning outcomes differ |
| Laver Cup | [2025 scores](https://lavercup.com/scores-results-2025) | Twelve September 19–21 matches, singles/doubles, scores and durations; team points vary by day | Match tiebreaks and day-weighted team scores require event-specific interpretation |

A notable supplementary route is static tournament documentation. The [WTA draw PDF](https://wtafiles.wtatennis.com/pdf/draws/2026/718/MDS.pdf) inspected here includes an explicit release time and lists withdrawals separately from retirements, with reasons such as injury, illness, and change of schedule. The [WTA United Cup final notes](https://wtafiles.wtatennis.com/pdf/matchnotes/2026/2084_F.pdf) and [ATP Challenger media guide](https://www.atptour.com/-/media/files/rankings-and-stats/atp-challenger-tour-media-guide.pdf) are additional official context/statistical cross-checks. These documents add detail that source-list summaries often miss; they are not a historical disclosure-time database unless versions and publication evidence are retained.

## Public aggregators, injuries, conditions, and less obvious leads

[CoreTennis](https://www.coretennis.net/) publicly advertises approximately 4.43 million results, 219,717 profiles and 130,885 tournaments at access, with ATP, WTA, Challenger, WTA 125, World Tennis Tour and junior navigation. Those are provider site totals, not counts downloaded or matched against markets. The breadth makes it useful for identity and lower-tier result checks; a very large total can also conceal large populations irrelevant to the market cohort.

[Tennis Explorer's inspected player page](https://www.tennisexplorer.com/player/davidovich-fokina/) contains actual match dates, rounds, scores, two-sided odds and a dated injury history. The injury entries include generic `retired`/`walkover` and occasional body-part descriptions. They may reflect a retirement and the time until the player's return; they are not a complete medical record or proof that a condition was disclosed before a bet. Doubles and mixed-doubles tabs offer another identity/result route. [TennisLive](https://www.tennislive.net/) remains a useful additional candidate, but its payload completeness and terms were not measured here.

[Tennis Abstract surface-speed ratings](https://www.tennisabstract.com/reports/atp_surface_speed.html) are available for ATP tour seasons back to 1991; the inspected page was updated August 31, 2026. The rating is an opponent-adjusted ace-rate proxy and implicitly mixes balls, weather, players, and surface. It is not direct physical Court Pace Index measurement. Using the final rating for the same tournament to predict earlier matches would incorporate later outcomes. [ITF's technical booklet](https://www.itftennis.com/media/15639/2026-technical-booklet.pdf) provides a distinct equipment/court-measurement reference, not a match-by-match physical measurement archive.

Weather history is obtainable from [Open-Meteo's official historical API](https://open-meteo.com/en/docs/historical-weather-api), whose [published schema](https://github.com/open-meteo/open-meteo/blob/main/openapi/historical-weather.yml) includes temperature, humidity, precipitation, wind, and timestamps. Reanalysis is retrospective. Forecasts available before a match, actual court location, roof use, indoor status, and rain delays are separate facts. A city-day weather join is a contextual approximation, especially for multi-site events and covered courts.

[ITIA sanctions](https://www.itia.tennis/news/sanctions/) provide official eligibility context. Decision publication date, effective suspension dates, and the underlying incident date should remain separate. A later disciplinary decision cannot be backfilled into historical pre-match information as if the public knew it then.

Further research datasets exist beyond ordinary tennis tabular files. [SCORE](https://data.scorenetwork.org/tennis/tennis-shot-level-data.html) offers a curated MCP derivative for teaching. [TennisExpert](https://github.com/LZYAndy/TennisExpert), linked from its authors' [2026 paper](https://arxiv.org/abs/2603.13397), is a video-understanding benchmark. These can support specific analysis or extraction experiments; neither is evidence of exhaustive recent market-aligned match data. Copies on Kaggle, Hugging Face, and other GitHub repositories should first be traced to their upstream source: extra hosting, a different file format, or a new dataset title does not create independent observations.

## Quality judgments by intended use

| Intended question | Public evidence that can support it | Material gap |
|---|---|---|
| Long-history singles opponent strength and results | Sackmann archive, TML history, official result cross-checks | Archive freshness, dates at tournament level, population drift, rights |
| Recent ATP/WTA match labels linked to Polymarket | Conservative Open Tennis Data candidates; current TML files; tennis-data snapshots; official draw checks | Open Tennis Data missing QF/recent cohorts; TML dates and key defects; exact-date and identity reconciliation |
| Challenger / ITF prehistory | TML current Challenger CSVs; Sackmann lower-tier files; ITF official draws; CoreTennis; restricted/current feed candidates | Lower-tier coverage discontinuities, ITF current freshness, weak crosswalks |
| Present-year doubles and mixed doubles | Official draws, team-event results, vendor/public-index leads | Old ATP doubles archive stops 2020; teams need four player identities and event-specific scoring |
| Historical live-state research | Zenodo observed June score-state sample; older Slam points | Sparse/truncated tapes, original collection dates, precise market/score synchronization |
| Shot-style or tactical analysis | MCP raw annotations and aggregates | Selected matches, malformed metadata, submission-time availability, no complete court tracking |
| Injuries and withdrawals known before betting | Official contemporaneous draw/notice versions, dated announcements | No audited complete disclosure-time injury table; final documents contain hindsight |
| Outright tournament probabilities | Draw structure, field, withdrawals, qualifiers, match outcomes | Historical draw versions, replacement rules, elimination knowledge times |
| Handicap / games / sets settlement | Set scores, match tiebreak rules, retirement/default status | Provider score conventions and actual contract rules can differ |
| Historical execution/ROI | Sporting data supplies labels and covariates | It does not supply Polymarket bids/asks, fee versions, traded size, or executable prices |

“High quality” is therefore conditional. The archive can be excellent for older results and unsuitable for current execution. An official final draw can be authoritative about who advanced and still leak future information into an injury predictor. An observed timestamp can prove when a collector saw a scoreboard state without proving that every preceding point was captured. A consistent numeric ID can identify a profile without proving that it is the same human in another provider.

## Evidence and reproducibility

Downloaded research artifacts are under [the public evidence directory](../../../data/studies/tennis_data_audit/public/). Each successful fetch has a URL, access time, byte count, SHA-256, content type and available server metadata. GitHub tree responses preserve the inspected repository tree identifiers. Files were obtained from named public URLs; failed source requests are retained as evidence rather than filled with guesses. The inherited tennis-data workbooks remain in their original location and are explicitly labeled as earlier local snapshots.

The standalone [download/CSV audit](../../../src/eda/tennis_data_audit/audit_public_payloads.py) and [current TML audit](../../../src/eda/tennis_data_audit/audit_tml.py) use the explicitly identified `ufc-monitor` interpreter and Python's standard library. The [Parquet/XLSX/point-state inspection](../../../src/eda/tennis_data_audit/audit_public_tables.py) and [market candidate comparison](../../../src/eda/tennis_data_audit/link_public_results_to_polymarket.py) used the existing `ufc-ag` environment because it already contains pandas, pyarrow and Excel readers. No package was installed, no production source adapter was changed, and these utilities do not select a system architecture.

Remaining uncertainty is recorded at the source level. Public download failures are not evidence that no data exists. A documented paid or academic programme is not evidence that its full payload meets the advertised coverage. No provider was contacted, no account was created, and no subscription or rights agreement was entered into. The [machine-readable public source register](public-sources.json) keeps those distinctions explicit for later source evaluation.

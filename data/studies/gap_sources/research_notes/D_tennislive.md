# D: TennisLive.net against the data map's gaps

- **Question.** For each sampled gap match:
  - Does TennisLive.net have its match page?
  - Does the page carry point-by-point (the score after each point, per game, with the server)?
  - Does it carry the match statistics block?
  - Is the point record complete?
- **Site and access.** <https://www.tennislive.net/>, read by program on 29 Sep 2026 between 17:41 and 18:21 UTC.
  - Every request's time and status is in `data/raw/gap_sources/tennislive/_requests.jsonl`.
  - Robots.txt disallows `/api/player-*`, and the site's terms forbid automated extraction. This was a bounded measurement under the owner's decision of 23 Sep 2026 to collect TennisLive regardless, for non-commercial research.
  - 449 requests were used of the lane's 1,000.
  - There was no block: no 429, no Cloudflare challenge, no CAPTCHA, no login. The single HTTP 403 was my own session error (section 4).
- **Sample.** The 226 `role == "check"` rows of `data/studies/gap_sources/sample_matches.csv`, drawn by `src/eda/gap_sources/sample.py` with seed 20260929.
- **Labels.** **[observed]** means read from the pages and API answers downloaded here. **[inference]** means my reasoning. **[not determined]** means the question stays open.

---

## 1. Bottom line

1. **TennisLive holds nearly every sampled gap match, with points and statistics [observed].**
   - Page found for 223 of 226 matches, a point record for 222, and the statistics block on all 223 pages.
   - By gap (matches checked: page found / point record / complete record / statistics block):

   | Gap | Checked | Page | Points | Complete | Statistics |
   |---|---|---|---|---|---|
   | itf_detail | 84 | 81 | 80 | 3 | 81 |
   | challenger_points_2025 | 32 | 32 | 32 | 1 | 32 |
   | atp_points_2025 | 36 | 36 | 36 | 2 | 36 |
   | wta_2018_points | 32 | 32 | 32 | 0 | 32 |
   | slam_points_ao_rg | 42 | 42 | 42 | 2 | 42 |

2. **The records are almost never complete: they usually lack every set's closing game [observed].**
   - Only 8 of the 222 point records have every game, and 7 of those 8 are retirements. An unfinished last set has no closing game to lose.
   - Among finished matches, 1 of 212 is complete: Jovic v Parrizas Diaz, Australian Open 2025.
   - 191 records (86%) lack only set-closing games, and 23 (10%) fall short in other ways.
   - Across the 531 finished sets in the point records, 35% list their closing game. For 7-6 sets it is 1.4%: the tiebreak is almost never listed.
   - Games listed without their points come on top of that: 357 of the 4,600 listed games. In 2025-26, 35 of 36 ATP records and all 32 Challenger records have at least one.
   - Overall, 4,243 of the 4,996 games in the final scores (85%) have their points listed. The median record covers 88.5% of its match's games.
3. **ITF, men against women [observed; tiny samples, 2 editions per tour and year]:**

   | ITF main draws | 2018 | 2019-21 | 2022-23 | 2024 | All |
   |---|---|---|---|---|---|
   | Men: page / points | 6 / 6 of 6 | 18 / 18 of 18 | 12 / 11 of 12 | 6 / 6 of 6 | 42 / 41 of 42 |
   | Women: page / points | 3 / 3 of 6 | 18 / 18 of 18 | 12 / 12 of 12 | 6 / 6 of 6 | 39 / 39 of 42 |
   | Women: median share of games with points | 0.86 | 0.66 | 0.94 | 0.94 | 0.90 |

   - **Women's ITF is covered like men's from 2019 [observed].** The only women's misses are one whole edition, Hammamet $15K 2018. TennisLive lists its results but has no match or tournament pages for it.
   - Men's 2018 was covered (6 of 6, two editions). The ten-career study's 26% was for 2012-18 pooled, so the two are compatible **[inference]**.
   - The men's miss is a Salerno 2022 page that has the statistics but no points.
   - Some women's editions of 2019-20 have thin records. W15 Moscow 2019 lists 17-25% of its games with points; both W15 Monastir 2020 editions list 33-47%.
4. **The statistics block equals the official box score almost everywhere below the Slams [observed].**
   - The comparison covered 16 fields per match: aces, double faults, serve points, first serves in and won, second-serve points won, break points faced and saved, for both players.
   - Identical: Challenger 31 of 31, WTA 2018 32 of 32, ATP 34 of 36.
   - The 2 other ATP matches have the two players' statistics exchanged. There, TennisLive's own point record agrees with the official figures about who served more, so the block is probably at fault **[inference]**.
   - At the Slams, 29 of 42 are identical and the rest differ by 1 to 6 in a few fields (626 of 672 fields equal).
   - For itf_detail, where no box score is held, the block is the only source and could not be checked.
5. **Identification is solid [observed].**
   - Every sampled match was found in a player's season listing, and its listed set scores equal the reference score in all 226.
   - The page's final score equals it on all 223 pages.
   - The page's winner is the reference winner on all 217 pages where both are known.

---

## 2. Results

### 2.1 By gap

Shares with Wilson 95% intervals, raw over the checked matches. The intervals are too narrow; see section 4.

| Gap | Checked | Page found | With points | Complete | Only set-closing missing | Other shortfall | Median share of games with points | Records under 50% of games | With statistics |
|---|---|---|---|---|---|---|---|---|---|
| atp_points_2025 | 36 | 36 (100%; 90-100) | 36 (100%; 90-100) | 2 (6%; 2-18) | 31 | 3 | 0.88 | 0 | 36 (100%; 90-100) |
| challenger_points_2025 | 32 | 32 (100%; 89-100) | 32 (100%; 89-100) | 1 (3%; 1-16) | 28 | 3 | 0.87 | 1 | 32 (100%; 89-100) |
| itf_detail | 84 | 81 (96%; 90-99) | 80 (95%; 88-98) | 3 (4%; 1-10) | 66 | 11 | 0.93 | 10 | 81 (96%; 90-99) |
| slam_points_ao_rg | 42 | 42 (100%; 92-100) | 42 (100%; 92-100) | 2 (5%; 1-16) | 34 | 6 | 0.89 | 4 | 42 (100%; 92-100) |
| wta_2018_points | 32 | 32 (100%; 89-100) | 32 (100%; 89-100) | 0 (0%; 0-11) | 32 | 0 | 0.89 | 0 | 32 (100%; 89-100) |
| **all** | 226 | 223 (99%; 96-100) | 222 (98%; 96-99) | 8 (4%; 2-7) | 191 | 23 | 0.885 | 15 | 223 (99%; 96-100) |

**Weighted to the gap.** Each stratum was weighted by its number of gap matches (`weighted_to_gap` in the summary). The results move little:

- itf_detail: 96.1% page found, 94.8% with points, 2.8% complete.
- ITF men: 97.3% with points. ITF women: 92.2%, pulled down by women's 2018.
- The other gaps: 100% with points.

### 2.2 ITF by tour and period

| Stratum | Checked | Page found | With points | Complete | Only set-closing missing | Other shortfall | Median share of games with points | Editions with points: all / some / none |
|---|---|---|---|---|---|---|---|---|
| Men 2018 | 6 | 6 | 6 | 0 | 5 | 1 | 0.93 | 2 / 0 / 0 |
| Men 2019-21 | 18 | 18 | 18 | 0 | 15 | 3 | 0.93 | 6 / 0 / 0 |
| Men 2022-23 | 12 | 12 | 11 | 0 | 11 | 0 | 0.94 | 3 / 1 / 0 |
| Men 2024 | 6 | 6 | 6 | 0 | 5 | 1 | 0.93 | 2 / 0 / 0 |
| Women 2018 | 6 | 3 | 3 | 0 | 3 | 0 | 0.86 | 1 / 0 / 1 |
| Women 2019-21 | 18 | 18 | 18 | 2 | 11 | 5 | 0.66 | 6 / 0 / 0 |
| Women 2022-23 | 12 | 12 | 12 | 1 | 11 | 0 | 0.94 | 4 / 0 / 0 |
| Women 2024 | 6 | 6 | 6 | 0 | 5 | 1 | 0.94 | 2 / 0 / 0 |
| **Men, all** | 42 | 42 (100%; 92-100) | 41 (98%; 88-100) | 0 (0%; 0-8) | 36 | 5 | 0.93 | 13 / 1 / 0 |
| **Women, all** | 42 | 39 (93%; 81-98) | 39 (93%; 81-98) | 3 (7%; 2-19) | 30 | 6 | 0.90 | 13 / 0 / 1 |

By year (6 matches each), every stratum has a point record for all six matches except three. Men 2022 has 5: the Salerno page without points. Women 2018 has 3: Amarante $15K 3 of 3, Hammamet $15K 0 of 3. The three complete women's records are all retirements.

### 2.3 Completeness in detail

| | Games per set equal the score | One game short | More than one short |
|---|---|---|---|
| Finished sets, all 531 | 186 (35%) | 325 (61%) | 20 (4%) |
| Final sets | 43% | 55% | 2% |
| Earlier sets | 30% | 65% | 5% |
| Sets ending 7-6 | 1.4% | 93% | 6% |
| WTA 2018 sets (72) | 0 | 72 | 0 |

- **"Other shortfall" (23 records) [observed]:**
  - Jumps: one block moves the games score by several games, with no points (for example 1-0 then 6-1).
  - Missing set panels: Alcaraz v Zverev, Australian Open 2026, has no set-1 panel.
  - Near-empty records: Raisma v Maric, Hungary F1 2018, lists 1 game of 15.
- **Records under 50% of games with points (15)** cluster by edition: W15 Moscow 2019 (all 3 matches, 17-25%), both W15 Monastir 2020 editions (33-47%), M25 Geelong 2020, Australian Open 2024 (4 of 4 checked), and one match each at Cervia 2026, Hungary F1 2018 and Salerno 2022.
- **Complete records.** A record with every game and every game's points: 2 of 222.

### 2.4 Statistics block

- Every one of the 223 pages carries the same 8 match-level rows: first serve (in / serve points), first-serve points won, second-serve points won, break points converted, return points won, total points won, double faults, aces. All except the last two carry counts, not only percentages. There are no per-set statistics.
- Against the official box score (Sackmann columns, from the reference row):

| Gap | Compared | All 16 fields equal | Players exchanged | Fields equal |
|---|---|---|---|---|
| atp_points_2025 | 36 | 34 | 2 | 546 / 576 |
| challenger_points_2025 | 31 | 31 | 0 | 492 / 492 |
| wta_2018_points | 32 | 32 | 0 | 512 / 512 |
| slam_points_ao_rg | 42 | 29 | 0 | 626 / 672 (largest difference 6) |

- **The two exchanges.** Hijikata v Ugo Carabelli (Hangzhou 2025) and Bautista Agut v O'Connell (Winston-Salem 2025). The figures below are serve points by page order.
  - Hijikata v Ugo Carabelli: TennisLive's own point record has 104 against 70, counted over its listed non-tiebreak games. Its statistics block says 82 against 114, and the official box score says 114 against 82 **[observed]**.
  - Bautista Agut v O'Connell: the record has 25 against 36, the block 37 against 26 **[observed]**.
  - Two sources against one: the block probably has the players the wrong way round **[inference]**.

### 2.5 How the matches were found

| Route | Matches |
|---|---|
| First player's listing, plain hyphenated slug | 191 (including the 3 Hammamet $15K 2018 matches, listed with results only) |
| Second player's listing, plain slug | 21 |
| A listing, with a slug seen in another player's listing | 10 |
| First player's listing, slug from the site search | 2 (Danielle Collins → `danielle-rose-collins`; "V. Dell'Elba" → `vito-dellelba`) |
| Second player's listing, names matched loosely | 2 ("Illia Biloborodko" is listed as "Illya Beloborodko") |
| **All** | 226 |

- Slug failures:
  - Four guessed slugs answered HTTP 404: `danielle-collins`, `alison-riske-amritraj` (TennisLive has `alison-riske`), and api-tennis's abbreviations `v-dellelba` and `a-picchione`.
  - One slug, `illia-biloborodko`, exists as a separate empty profile.
- The site search was used 5 times.
- Requests: 210 listing pages, 223 match pages, 4 session pages, 5 searches and 2 site scripts. Also 1 refused and 4 unknown-slug listing calls, which makes 449 in all.

---

## 3. Method

1. **Reference score.** Each match's final score is taken from the row of the source that created it in the data map. That is Tennis My Life for 122 matches and Sackmann for 103; one ITF match (M15 Salerno 2022, created from api-tennis) uses api-tennis's set scores. The same rows give the official box score (Sackmann columns) wherever one exists, which is every points-gap match but one. The ITF gap has none by definition.
2. **Session.** TennisLive's JSON endpoints require the `X-TennisLive-Token` of a page fetched in the same session; the page also sets the session cookie `TENNISLIVESESSID`. Each run therefore opened with one player page.
3. **Player slug.** Tried in order, first for the player whose season listing was already cached (or whose slug had been seen), then for the other player:
   - a slug seen for the same name in a listing or search answer already on disk;
   - the plain hyphenated name ("adam-walton");
   - the site's own search, `GET /api/search?q=<name>` (the search box's endpoint, same token), then the surname alone.

   An unknown slug answers HTTP 404 on the listing endpoint **[observed]**.
4. **Season listing.** `GET /api/player-matches?tour=<atp|wta>&slug=<slug>&discipline=singles&year=<season>&surface=all&offset=<n>`. The adapter `src/ingest/point_sources/tennislive.py` reads this endpoint too. It returns 60 matches a page, newest first. Pages were read until the listing passed the tournament week.
5. **Match identification.** The listed opponent had to share a name word with the other player, and the match had to start 10 days before to 21 days after the tournament week start (`d`).
   - Ties went first to agreement of the listed set scores with the reference score, then to the draw (qualifying or main), then to the tournament's own dates.
   - At a year boundary the neighbouring season was read too.
   - Fallback: when no name word was shared, near-identical words (similarity 0.8 or more, 4+ letters) were accepted, but only if the listed set scores equal the reference score. This found the two Beloborodko matches.
6. **Match page.** `GET /<tour>/match/<p1>-VS-<p2>/<tournament>/`, parsed with the adapter's `parse_match_page` (unchanged).
   - *Point record:* at least one point state is listed.
   - *Games per set:* the game blocks in each set panel, aligned by set number.
   - *Completeness:* uses the rules of `src/eda/point_shot_sources/verify_scrape.py` (`completeness`, `short_kind`, imported).
     - **complete:** every set lists as many games as the score. A retirement's unfinished game or a match tiebreak written as one game also counts.
     - **only set-closing games missing:** every set that falls short lacks exactly one game, and its last listed game ends one game before the set score.
     - **other shortfall:** any other shortfall.
   - *Share of games with points:* (games listed − games listed without points) / games in the score.
7. **Statistics.** The statistics block is present if the page's statistics panel has rows. It was then compared field by field with the reference box score, with both players aligned by name. Break points faced and saved are read from the opponent's "break points converted".
8. **Pace and stops.** One request at a time, at least 2 s after the previous answer plus up to 1 s of random jitter. curl_cffi presented Safari's fingerprint, as the adapter does. Any HTTP 403 or 429, Cloudflare challenge or CAPTCHA page stopped the run at once with no retry. The lane's budget was 1,000 requests over all runs, counted in the ledger. Every answer is cached with a receipt, so a rerun asks only for what is missing.
9. **Runs**, all on 29 Sep 2026 (UTC):
   - 6 requests of exploration by hand (17:41-17:45).
   - A 5-match dry run, 10 requests (17:52).
   - The full run, 431 requests (17:53-18:16, no stop).
   - A top-up of 2 match pages (18:20), after the loose-name fallback found the two Beloborodko matches.
   - The tables were then rebuilt offline from the cache.

---

## 4. Caveats

- **Sample sizes and clustering.** Each ITF tour-year has 6 matches from 2 editions, so per-year shares rest on two tournaments. A Slam edition has 1-2 matches. Outcomes are shared within an edition: the Hammamet miss, and the thin records of W15 Moscow 2019 and W15 Monastir 2020. The Wilson intervals treat matches as independent and are therefore too narrow. The effective sample is nearer the number of editions: 28 ITF, 8 Challenger, 9 ATP, 8 WTA 2018 and 22 Slam. The women's 2018 figure (3 of 6) is one edition of two.
- **The HTTP 403.** The lane's fourth request, made by hand while exploring, reused a token from a page fetched in an earlier Python session. The listing endpoint refused it with 403, with no Cloudflare marker. I stopped, logged refusal bodies from then on, and made one request in the documented flow (page and API call in one session), which answered 200. No 403 or 429 followed in the remaining 445 requests. I count it as a session-token error on my side, not a block by the site; the owner may judge otherwise.
- **"Complete" is a game count, not an audit of each point.** Each point state was not checked against another point source; no other source of points exists for these gaps. Games listed without points are reported separately. The game-winning point of a regular game is implied, not listed (the adapter's docstring).
- **Retirements** make "complete" easier to reach: 7 of the 8 complete records are among the 10 retirement records.
- **Slug and name matching.** 27 matches were found through the second player's listing: in some the first player's slug failed, in others the second player's listing was already cached. Two needed the site search and two a loose name match. All 226 were confirmed by listed set scores equal to the reference. The `found_via` column records the rebuild's path through the cache, which differs from the live run for one match: uid 384157 was found through the second player's listing live, the first player's in the rebuild, with the same page.
- **A URL quirk [observed].** The page of Dell'Elba v Picchione (listed under "ATP M15 Salerno", 7 Sep 2022) has the tournament slug `m15-monastir-2022-34` in its URL. Its date, score and players agree with the reference, so the match is right and the slug is TennisLive's.
- **Provenance [not determined].** TennisLive does not say where its point data comes from. The small Slam statistics differences suggest it computes statistics from its own point feed rather than copying official box scores **[inference]**. The dropped set closers and missing game points look like gaps in a live-score feed rather than deliberate omission **[inference]**.
- **Not measured.**
  - Qualifying outside the tour-level strata: the ITF gap is main draws only.
  - Doubles.
  - Whether pages change or disappear over time.
  - How many of the drawn editions' other matches ("listing" rows) are held. Only the check rows were read.
- **Rights.** The API path read is disallowed by robots.txt and the terms forbid bulk extraction. This measurement is not permission.

---

## 5. Files

- `src/eda/gap_sources/tennislive_probe.py`: the probe. Rerun it with `./python.sh src/eda/gap_sources/tennislive_probe.py`; `--offline` rebuilds the tables from the cache with no request.
- `data/studies/gap_sources/tennislive_matches.csv`: one row per check match. It records how the match was found (`found_via`, `attempts`, `listing_slug`), the URL, and the listing's and page's score against the reference. It also has the page status, games per set listed against the score's, games listed without points, the share of games with points, the verdict, the statistics, the box-score comparison and winner agreement.
- `data/studies/gap_sources/tennislive_summary.json`: counts and Wilson 95% intervals by gap, stratum, and ITF tour × period and year, plus stratum-weighted shares, an edition-level view, request counts by kind and status, the refusal, and every run.
- `data/raw/gap_sources/tennislive/` (gitignored):
  - verbatim answers: player pages, listings, searches, gzipped match pages, and the two site scripts read to learn the search call;
  - `_receipts.jsonl`: URL, time, status and hash of each answer;
  - `_requests.jsonl`: every request, retries included;
  - `_runs.jsonl`: one line per run.

---

## Follow-up: men's ITF after June 2026

- **Question.** Does TennisLive list men's ITF World Tennis Tour results after June 2026, that is ISO weeks 27-36 (29 Jun - 6 Sep 2026)? No file the project holds lists them: Polymarket gives winners only, the Live Tennis API index ends on 13 Aug, and SofaScore is blocking the project.
- **Access.**
  - TennisLive was read on 29 Sep 2026, 18:41-18:50 UTC, with the lane's client and rules (at least 2 s after each answer plus up to 1 s jitter, stop on any block). No 403, 429, challenge or CAPTCHA occurred.
  - 75 requests of the follow-up's 300 (ledger lines 450-524).
  - Two MediaWiki API requests (18:38 UTC) fetched Wikipedia's "2026 ITF Men's World Tennis Tour (July–September)" (revision 1377046069) and the women's page (revision 1377146714).
  - Neither itftennis.com nor SofaScore was used.

### Bottom line

1. **Yes: TennisLive lists men's ITF events after June 2026 in full, qualifying included [observed].**
   - All 8 sampled men's events (M15/M25, one each in weeks 27, 28, 30, 31, 32, 34, 35 and 36) are on the site.
   - Main-draw singles: 248 of 248 matches with a result, 31 in each 32-draw. Every one has a match page.
   - Qualifying: listed for all 8 events, 318 matches, all with a result. Qualifying draws had 24, 40, 54 or 56 matches.
   - Each event's final is dated in its week. For the 7 events with a Wikipedia entry, TennisLive's finalists and final score agree with Wikipedia. The eighth (week 27, from the Live Tennis index) agrees with the index's final pairing.
2. **Point-by-point on 18 of 24 men's main-draw matches read (3 per event) [observed].**
   - 0 are complete. 14 lack only set-closing games, and 4 fall short in other ways.
   - The median record lists 87% of the match's games with their points.
   - The 6 matches without points are in 3 events: Figueira da Foz (week 27) 2 of 3, Bucharest (week 28) 3 of 3, Kraków (week 34) 1 of 3. Four of their pages show the site's "Complete game and point progress is not available" notice.
   - All 24 pages carry the statistics block (the same 8 rows as elsewhere).
3. **Women's events, for comparison [observed].**
   - 3 of 3 events: W15 Monastir (week 29), W50 Hamburg (week 33), W75 Tianjin (week 36).
   - Main-draw singles: 93 of 93 with a result. Qualifying: listed, 88 matches.
   - Points on 9 of 9 matches read: 1 complete (a retirement), 7 lacking only set-closing games, 1 other shortfall. Median 90% of games with points.
   - Statistics on 9 of 9.
   - The men's and women's pictures are the same: full listings, and records with the usual TennisLive shape. Men's pages lack points in a few events.

| Week (start) | Event | Found through | TennisLive page | Main draw: with result / listed, of full | Qualifying: with result / listed | Final (TennisLive) | Reads with points | Complete / closers only / other | With statistics | Requests |
|---|---|---|---|---|---|---|---|---|---|---|
| 27 (29 Jun) | M25 Figueira da Foz | Carl Emil Overbeck (index) | `/atp-men/m25-figueira-da-foz-2026/` | 31/31 of 31 | 24/24 | Overbeck d. Schoen 6-1 3-6 6-3, 5 Jul | 1/3 | 0 / 0 / 1 | 3/3 | 7 |
| 28 (6 Jul) | M15 Bucharest | Ilya Snițari | `/atp-men/m15-bucharest-2026-1/` | 31/31 of 31 | 56/56 | Snitari d. Papoe 6-4 6-4, 12 Jul | 0/3 | 0 / 0 / 0 | 3/3 | 7 |
| 30 (20 Jul) | M25+H Bacău | Radu Mihai Papoe | `/atp-men/m25-bacau-2026/` | 31/31 of 31 | 54/54 | Papoe d. Cazacu 6-0 6-0, 26 Jul | 3/3 | 0 / 2 / 1 | 3/3 | 6 |
| 31 (27 Jul) | M15 Kuršumlijska Banja | Andrea de Marchi | `/atp-men/m15-kursumlijska-banja-2026-10/` | 31/31 of 31 | 56/56 | De Marchi d. Krstic 6-4 6-3, 2 Aug | 3/3 | 0 / 3 / 0 | 3/3 | 6 |
| 32 (3 Aug) | M25 Londrina | Felipe Meligeni Alves (`felipe-meligeni-rodrigues-alves`, seen in a listing) | `/atp-men/m25-londrina-2026/` | 31/31 of 31 | 24/24 | Meligeni Alves d. Saraiva dos Santos 6-3 7-5, 8 Aug | 3/3 | 0 / 2 / 1 | 3/3 | 6 |
| 34 (17 Aug) | M15 Kraków | Daniel Michalski | `/atp-men/m15-krakow-2026/` | 31/31 of 31 | 40/40 | Michalski d. Agwi 6-2 3-0 ret., 23 Aug | 2/3 | 0 / 1 / 1 | 3/3 | 6 |
| 35 (24 Aug) | M25 Poznań | Daniel Michalski | `/atp-men/m25-poznan-2026/` | 31/31 of 31 | 40/40 | Michalski d. Savano 6-2 6-1, 30 Aug | 3/3 | 0 / 3 / 0 | 3/3 | 6 |
| 36 (31 Aug) | M15 Nonthaburi | Arthur Weber | `/atp-men/m15-nonthaburi-2026/` | 31/31 of 31 | 24/24 | Weber d. Bouzige 7-5 7-6, 6 Sep | 3/3 | 0 / 3 / 0 | 3/3 | 6 |
| 29 (13 Jul) | W15 Monastir | Yuliya Perapekhina | `/wta-women/w15-monastir-2026-20/` | 31/31 of 31 | 40/40 | Perapekhina d. Dotsenko 6-4 6-2, 19 Jul | 3/3 | 0 / 3 / 0 | 3/3 | 6 |
| 33 (10 Aug) | W50 Hamburg | Anna Sisková | `/wta-women/w50-hamburg-2026/` | 31/31 of 31 | 24/24 | Sisková d. McAdoo 7-6 1-6 6-3, 16 Aug | 3/3 | 0 / 2 / 1 | 3/3 | 6 |
| 36 (31 Aug) | W75 Tianjin | Joanna Garland | `/wta-women/w75-tianjin-2026/` | 31/31 of 31 | 24/24 | Garland d. Astakhova 6-3 6-2, 6 Sep | 3/3 | 1 / 2 / 0 | 3/3 | 6 |

"Requests" attributes to each event its listing, tournament page, results section and match pages. A listing shared by two events (Michalski's) is counted in both. The follow-up's other requests were 2 home pages and 2 player pages opening sessions, one site script (`tournament.js`), and 5 pages of the wrong Monastir edition (see caveats). In all, 75.

### Method

1. **Events.** The seed was 20260929.
   - Men: M25 in weeks 27, 30, 32 and 35; M15 in weeks 28, 31, 34 and 36. One event was drawn at random per week, from Wikipedia's list for weeks 28-36 (6-13 events per level and week).
   - Week 27 is on Wikipedia's April-June page, which was not read. It was drawn from the 6 M25 events of the Live Tennis API index. The index's two naming variants of one event, "ITF M25 Skopje Men" and "M25 Skopje", were merged; its times were taken as Israel time, UTC+3.
   - Women: W15 in week 29, W35/W50 in week 33, W75/W100 in week 36.
   - Wikipedia gives each event's winner and final score, runner-up, semifinalists and quarterfinalists; the index gives its players.
2. **Locating an event.** Through the 2026 season listing of one of its players: the winner first, with the slug rules of the main probe. The event is the listing group whose name has the level and city and whose matches fall in the week.
   - Cities with an event every week put the previous week's final inside that window. The group nearest mid-week therefore comes first.
   - The pick was checked: the event's final must be dated in its week, and its players must be Wikipedia's finalists.
3. **Listing an event.** TennisLive's tournament page (`/atp-men/<event>/`, `/wta-women/<event>/`) loads its lists from `GET /api/tournament-section?tour=<atp|wta>&slug=<event>&section=results`, with the session token. The call was read from the site's `tournament.js`.
   - The results section lists every match by round: qualifying rounds, main-draw rounds and doubles, each with its score, winner and match URL.
   - The page's own totals agree with it; Figueira da Foz, for one, shows 55 singles, which is 31 main-draw plus 24 qualifying.
4. **Reading matches.** Three main-draw singles matches per event were drawn at random (seed + event number) from those with a result. They were parsed with the adapter's `parse_match_page`. The verdict rules are the main probe's, applied against the page's own final score.

### Caveats

- **Small sample.**
  - 8 men's and 3 women's events, 3 matches read in each. The listing result (every event complete) is strong for these events.
  - The share of matches with points is not a firm estimate: the pages without points cluster by event, and Bucharest has 0 of 3.
  - For comparison, the earlier point-sources study found TennisLive point records for 99% of the ten career players' 108 ITF main-draw matches of 2026.
- **One mis-identification, caught.** For W15 Monastir (week 29), the first pass took the previous week's Monastir edition, `w15-monastir-2026-19`, whose final Perapekhina also won. Its final date and runner-up disagreed with Wikipedia. The rule was fixed to pick the group nearest mid-week and check the final, and the right edition (`-20`) was read. The wrong edition's 5 pages cost requests and stay in the cache unused.
- **Completeness has no independent score** except the finals: every read is judged against TennisLive's own final score. The finals agree with Wikipedia in 10 of 10 events.
- **Wikipedia is a volunteer list.** The events were drawn from its tables; how complete they are was not checked.
- **What "listed" shows.** "Listed with a result" means the tournament's results section shows the match finished with a score. It does not show that every point of the match is available.

### Files

- `src/eda/gap_sources/tennislive_itf_after_june.py`: rerun it with `./python.sh src/eda/gap_sources/tennislive_itf_after_june.py`; `--offline` rebuilds from the cache.
- `data/studies/gap_sources/tennislive_itf_after_june.csv`: one row per event. It has the source of the event's names, how it was found, the TennisLive URL, and the final check. It also has main-draw and qualifying counts, by round; the listed final against Wikipedia's; the three reads (points, verdicts, statistics); and requests.
- `data/studies/gap_sources/tennislive_itf_after_june_matches.csv`: the 33 matches read.
- `data/studies/gap_sources/tennislive_itf_after_june_summary.json`: the men's and women's totals, the request counts by kind (with the Wikipedia receipts and revision ids), and any stop.
- Raw answers are under `data/raw/gap_sources/tennislive/`: `tournaments/`, match pages, listings, and `assets/tournament.js`. The two Wikipedia API answers are under `data/raw/gap_sources/wikipedia/`, with `_receipts.jsonl`.

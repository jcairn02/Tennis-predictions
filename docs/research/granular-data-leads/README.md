# Granular tennis data the project does not hold: where to find it, ranked by confidence

**Status: research, not a decision.** Sources read on 24 September 2026. Nothing was bought, no account or trial was opened, no provider was contacted and nothing was decrypted. Scope is all professional tennis (tour, Challenger, ITF, Slams, men and women), not only the ten careers of the [point- and shot-level study](../../studies/point_shot_sources/README.md), which this page extends.

**What was looked for, in priority order:**

1. **Shot by shot:** every stroke of a rally, or ball and player tracking.
2. **Point by point with the nature of each point:**
   * who won it, in order;
   * first or second serve;
   * ace, double fault, winner, forced or unforced error;
   * rally length, serve speed, stroke, clock time.

"New" means new coverage (matches not held) or new width (fields that held records of the same match lack).

Evidence notes, probe logs and the chart-gap list are in [data/studies/granular_data_leads/](../../../data/studies/granular_data_leads/).

**Follow-up, same day: [access routes](access-routes.md)** checks whether rows 2–6 can be had publicly or from a paid service; asking permission does not count.
* If a no-scraping clause does not rule a source out (the likely intent), all five can be obtained publicly today.
* Under the stricter reading, only Wimbledon 2026 passes, and only for personal, non-commercial use.
* No service sells any of the five datasets.

**Follow-up for rows 9–13: [TDI and open data](access-routes-tdi-and-open-data.md).**
* **TDI Tennis Results can be had publicly only from about 24 June 2026 on.** The site lists a rolling ~93 days, and no public or paid source lists older matches; 634 ids survive in the Wayback Machine.
* **No licensed product sells TDI's point data to a buyer like this project.** Sportradar sells the fields live, to bookmakers and prediction-market platforms only.
* **The four open datasets can all still be downloaded; none is sold.** Larger public copies exist:
  * decrypted ATP Stats Centre data for 2021–2024 on Hugging Face;
  * a 2019 Tennis Australia release that makes From AO to AI joinable.

## Bottom line

* **Shot-by-shot data you can add today, under the licence you already hold:** the Match Charting Project's pre-2010 point files.
  * They sit in the same GitHub commit as the export the dump took, but were never staged.
  * They should supply points for about 2,382 of the 2,416 charted matches the dump lists without points (the pre-2010 ones; the files were sampled, not downloaded). The other 34 are unexplained.
* **6,447 more charted matches exist only on tennisabstract.com.**
  * That is 55% more than the export holds (35% of the website's 18,262 charts): 3,060 of them from 2019–2026, and 60% of them women's matches.
  * Sackmann withholds them from the export "by design". Asking is not a route (owner, 24 Sep). The pages can be parsed, and 3,053 of the charts are already in a public Hugging Face copy (`ramizheman/TennisNLData`, no licence).
* **The Slams' own scoring feeds hold about 4,470 point-level matches not in the dump:**
  * Wimbledon 2019 and 2021–2026, including qualifying and 2024 doubles;
  * US Open 2022–2026, including qualifying;
  * Australian Open 2026.

  They also add per-point clock times and a sentence naming the stroke and error type to about 2,400 matches the dump already holds.
  * The US Open's, Tennis Australia's and Roland-Garros's terms bar automated extraction.
  * AELTC's terms bar only commercial use without a licence. However, the `2025.wimbledon.com` archive host's robots.txt disallows every robot ([access routes](access-routes.md)).
  * The Australian Open serves only its current edition, so 2026 will probably vanish in January 2027.
* **Ball tracking is publicly reachable in four places:**
  * GitHub copies of Hawk-Eye "Court Vision" data for the Australian Open 2020–2024 and Roland-Garros 2019–2024: 2,027 matches, a 3-D ball position for every shot.
  * The ATP's own Court Vision files: tour level from 2021, encrypted.
  * A decrypted copy of those ATP files on Hugging Face: 4,570 tour-level matches, 2021–2024 (found on the second pass).
  * A 2018–2020 ATP return-position file.

  All but the return-position file carry a rights problem: their data was decrypted from Infosys feeds, by others or (for the ATP files) it would have to be.
* **The widest point data outside the Slams is official and public, but off limits.** TDI's "Tennis Results" site shows the following for every ATP Tour and Challenger match since 2025 (for Challengers, only from late 2025 or early 2026):
  * first or second serve;
  * winner, forced or unforced error;
  * net or out;
  * rally length;
  * last stroke;
  * who was at the net;
  * a UTC time for each point.

  Its terms forbid scraping and model training. The site lists only the last ~93 days, and no licensed paid route exists for a buyer like this project ([TDI and open data](access-routes-tdi-and-open-data.md)).
* **First or second serve on non-Slam points** is available from:
  * TDI (2025 onward);
  * the ATP's encrypted MatchBeats files;
  * Sportradar's public widget feed (kept for only about two weeks, so it can only be captured going forward);
  * Live Tennis API (paid, from 12 Sep 2026);
  * 2016–17 point strings that mark second serves.
* **The Data Sports Group link you highlighted has no point history.** None of its 24 tennis methods returns one; it has only live current-game fields. Twelve other vendors and sites also add nothing the dump lacks; they are listed under [Checked and set aside](#checked-and-set-aside).

## The baseline: what the dump already holds

| Held source | Matches | Per-point width |
|---|---|---|
| Slam point archive (Sackmann, via mirror) | Main-draw singles 2011–2024 (AO and RG only to 2021, no Wimbledon 2020); doubles and mixed for AO/RG 2018–21, US Open 2019–24 and Wimbledon 2019 and 2021–23. **No qualifying.** | See below the table |
| Match Charting Project export | 11,822 matches listed; points for 9,406 (only the 2010s and 2020s point files were staged) | Every shot: serve direction, stroke, direction, depth, error type, outcome |
| Sackmann point strings, two copies | 2011–2017, all tiers down to Futures | Winner and server of each point, aces and double faults |
| Live Tennis API sample | June 2026, 5,380 matches | Score state and UTC time per point |
| SofaScore and TennisLive (being pulled) | The ten careers | Score after each point, server, break/set/match-point flags; SofaScore marks aces and double faults |

**The Slam archive's per-point fields** are ace, double fault, serve number (from 2014; AO from 2015), winner and unforced-error flags, net points, serve speed, rally count, serve width and depth, return depth, winner stroke side, distance run and IBM's momentum score. It has no clock time, only elapsed time. The forced-error field is blank after 2011. **AO and RG 2018–21 lack placement, return depth, winner stroke, distance run and elapsed time.**

SofaScore's statistics also carry winners and errors by stroke for 85 of its events: its 2024–2026 Slam matches, plus some 2023 ATP and ITF events. Those are match totals, not per point.

The other files named in the request were scanned too:
* **The source register** (139 records): its point and shot entries were covered by the 23 September study, which already lists its stale entries.
* **`tennis-data-terrain.html`:** a landscape overview with no further sources.
* **The TennisLive match pages:** they hold only score progression, server and break-point markers, which the adapter already parses.
* **The Tennis Abstract index** (`meta.html`): it produced the 6,447-chart gap.

## The list, highest to lowest confidence

**Confidence** is how sure we are that the data is there and that the project could get it. Rights are a separate column and are the owner's call; a high place is not a recommendation to ignore a site's terms.

**Evidence labels:**
* **seen:** we read the payload today, or the file listing and samples;
* **documented:** the provider publishes a schema or example;
* **claimed:** the provider only says so.

| # | Source | Grain | New coverage | New width | Evidence | How you would get it | Rights | In register |
|---|---|---|---|---|---|---|---|---|
| 1 | **MCP pre-2010 point files** (`charting-m-points-to-2009.csv`, `charting-w-points-to-2009.csv`) | Shot | About 2,382 matches from 1960–2009 whose metadata is held (34 later matches without points stay unexplained) | None beyond MCP | Seen: repository tree, sizes, samples | Download two files, 44 MB, from the commit the dump already used | CC BY-NC-SA 4.0, as held | Yes (PUB005); not staged |
| 2 | **Wimbledon scoring feeds**, 2019 and 2021–2026 | Point, with tracking-derived fields | ≈2,445 matches: qualifying 2019 and 2021–24 (≈1,119), 2024 doubles (124), every event of 2025 (≈601) and 2026 (≈601) | Per-point start and end time; a sentence naming stroke and error type (the only record of forced errors); kick height; court side; challenges. Also added to ≈1,260 held matches | Seen: draws, point histories and statistics for every year | Public JSON on the `2025.wimbledon.com` archive host (2026 on www) | AELTC allows extracts for "personal, non-commercial purposes"; commercial use needs a licence. The archive host's robots.txt is `Disallow: /` | No |
| 3 | **US Open scoring feeds**, 2022–2026 | Point, with tracking-derived fields | 1,356 matches: qualifying 2022–24 (247; only ≈37% had full data then), every event of 2025 (509) and 2026 (600) | As row 2; also added to ≈1,130 held matches | Seen | Public JSON (a browser user agent is needed) | USTA forbids use that "results in the scraping or copying of information, data, or content" | No |
| 4 | **Australian Open 2026 match centre** | Point nature | 604 matches: singles, qualifying, doubles. AO 2022–25 are no longer served (65 Wayback captures) | Per point: forehand/backhand winner, forced or unforced error; ace; double fault; service winner; Unix time. Per set: serve speeds, winners and errors by stroke family | Seen: 9 of 9 samples | Public JSON; **probably removed in January 2027** | Tennis Australia forbids collecting content "using automated means" | No |
| 5 | **IBM extras at the US Open and Wimbledon** | Player-tracking and model outputs | US Open 2026 serve biomechanics (≈254 singles matches); likelihood-to-win per point (both Slams, 2025–26 singles); US Open 2026 key moments; Wimbledon 2024–25 TennisViz metrics per set | All new: ball toss, knee and trunk angles, racket speed, bounce distance from target; win probability after every point; shot quality | Seen | Public JSON | As rows 2–3 | No |
| 6 | **WTA official API** (`api.wtatennis.com/…/point-by-point`) | Point order and time | WTA matches; seen for 2022, 2024 and 2026 (2019 not served); tier coverage not measured | Per point: UTC time and win probability. Per match and set: winners and errors by wing, fault reasons, rally-length buckets, net approaches | Seen | Public JSON, no login | Terms forbid automated access and harvesting ([access routes](access-routes.md)) | No (only the stats hub) |
| 7 | **Court Vision copies on GitHub**: `hawkilol/tennisSlamBallTracking` (AO 2020–24, RG 2019–24, 2,027 singles matches) and `ryurko/hawkeye` (805 matches, 2019–21) | **Tracking** | AO and RG 2022–24 (≈1,225 matches) are new even at point level; tracking is new for all | 3-D ball position at hit, peak, net and bounce for every shot; server and receiver positions; spin; net clearance; serve type; error type; point-end type; rally length; serve speed | Seen: catalogues, per-point CSVs, one raw JSON | Clone the repository (243 MB; 163 MB of CSV, 3.3 GB of raw JSON) | **The 2022–24 files were decrypted from Infosys feeds**; no data licence; the data belongs to Tennis Australia, the FFT and Infosys | No |
| 8 | **Tennis Abstract website-only charts** | Shot | 6,447 matches (men 2,557, women 3,890; 3,060 from 2019–2026) | As MCP: every shot, in words that map back to MCP codes | Seen: the index and two full chart pages | Parse 6,447 pages (robots.txt allows `/charting/`). 3,053 are already in a public Hugging Face copy, `ramizheman/TennisNLData` | CC BY-NC-SA, but kept out of the export "by design" | Yes (PUB007); gap not measured before |
| 9 | **TDI "Tennis Results"** (`results.tennisdata.com`) | Point nature, the widest outside the Slams | Every ATP Tour (non-Slam) and Challenger match, singles and doubles, main draw and qualifying, since January 2025 (*claimed*; 13 match pages read). Challenger outcome fields only start somewhere between July 2025 and March 2026 | Per point: first or second serve; faults and lets; winner, forced or unforced error; net or out; rally length; last-shot type; who was at the net; UTC time. TennisViz metrics per match and set | Seen | Each match page embeds its points. The listing covers a rolling ~93 days. Older pages still hold their points, but only 634 older ids can be found ([TDI and open data](access-routes-tdi-and-open-data.md)) | **Terms forbid scraping and use for "statistical models or AI systems"** (EU text-and-data-mining opt-out). No licensed paid route | No (only TDI's business platform) |
| 10 | **`SirGenkii/infotennis` fork** | Point nature, some tracking | ATP tour, January–April 2025: ≈136,900 main-draw points; key statistics for 929 matches; 8 Monte-Carlo matches with per-shot x/y/z | Point-end type, shot count, serve number, serve speed, net-point flag | Seen: SQL dumps | Download. A 2021–24 copy of the same data is on Hugging Face (`atlas-polybot/atp-pipeline-handoff`) | Decrypted Infosys data; the licence covers code only | No |
| 11 | **`skoval/monash-return-impact`** | Tracking, narrow | ATP 2018 to February 2020: 126,455 returns, 1,287 matches, 36 events | Ball 3-D position at return impact, serve number, serve direction, ATP match ids | Seen | Download, 1.3 MB | No licence; built from atptour.com summaries | No |
| 12 | **`skoval/tennis-match-data`** | Point nature | May 2016 to February 2017: 15,382 ITF men's, 1,313 ATP, 1,199 WTA (plus ITF women, doubles, WTA 125K, team and junior files) | A second-serve mark on each point, which the held Sackmann strings lack; aces and double faults | Seen | Download, about 26 MB. The upstream, `TennisVisuals/tennis-match-data`, holds slightly more | No licence; the feed behind it is not stated | No |
| 13 | **"From AO to AI"** (Tennis Australia and CrowdANALYTIX, 2018) | Tracking-derived features | 13,000 AO rally points, 10,000 of them labelled | For the last two shots: speed, net clearance, depth, distance from sideline, stroke side, both players' positions, distance travelled; outcome as winner, forced or unforced error | Seen | Download, 2.7 MB | No licence. No ids of its own, but 10,795 of the 13,000 rows link to a 2019 Tennis Australia release that has match and point ids (`camroach87/etc3250-kaggle`) | No |
| 14 | **ATP Stats Centre files** (Infosys: MatchBeats, Rally and Stroke Analysis, Key Stats, Court Vision) | Point nature and **tracking** | MatchBeats: tour level from 2021, Challenger from 2023 (files seen, contents not decoded). Court Vision: tour level only | Per point: serve number; ace, double fault, winner, unforced or forced error; stroke; rally; serve speed (third-party description). Court Vision: per-shot 3-D ball and player positions, spin, net clearance | Files seen; encrypted | Download with browser headers, then AES-decrypt; third parties publish the method. Decrypted copies exist for 2021 – April 2025 (row 10) | atptour.com forbids "systematic retrieval of data"; decrypting needs your explicit decision | No |
| 15 | **Infosys AO and RG match centres** | Point nature and tracking | AO 2022–26, RG 2018–26 | As row 14 | MatchBeats files seen but encrypted; Court Vision API blocked (403); 957 RG MatchBeats captures on Wayback, also encrypted | No plain route | Slam terms forbid automated extraction | No |
| 16 | **Sportradar's public widget feed** ("gismo", `lsc.fn.sportradar.com`) | Point | ATP, Challenger (including qualifying), WTA, WTA 125, UTR, juniors. No ITF | First-serve fault, ace, double fault, and a Unix time for every serve and point | Seen: 16 probes, matching Sportradar's own box score | Point events are kept about 11–18 days, so forward capture only | Unlicensed; widget ids are issued "upon obtaining a license" | No |
| 17 | **Live Tennis API outcome tags** | Point nature | From 12 Sep 2026 only. ATP and Challenger get all five outcomes; WTA and ITF only aces and double faults | Serve number and ace / double fault / winner / forced / unforced error per point, with time | Documented | Paid, $9.99–99 a month | Its terms limit storage | Yes (product); the fields are new |
| 18 | **Sportradar Tennis API v3** | Point | ATP and Challenger point by point from round 1; WTA 250 and 125 from the semi-finals; a rolling window of the current season plus two adjacent editions | First-serve fault, result (ace, double fault, server or receiver won), time | Documented: public OpenAPI | Enterprise quote | Display only; no betting or prediction-market use; data destroyed on termination | Yes |
| 19 | **STATSCORE incidents** | Point, serve by serve | Claims ATP, WTA, Challenger, ITF and Slams; history not stated | First serve in or fault, net, second serve, double fault, ace, foot fault | Documented | Paid add-on | Contract | Yes |
| 20 | **Stats Perform MA21** | Point, with shot type | Fullest for the WTA; archive from 2021 | `isFirstServe`, `shotType`, `stroke`, `isVolley`, `zone` | Documented | Enterprise | Licence bars ML training and building archives | Yes |
| 21 | **Research-access requests** | Tracking, shot | See below the table | Ball and player tracking | Existence documented; access unknown | Ask: not a route (owner, 24 Sep) | Per agreement | Partly |
| 22 | **Licence-only tracking** | Tracking | See below the table | Per-shot tracking | Claimed and documented | Business contract | Contract | Partly |
| 23 | **Kaggle `marcosjn2`** (a SofaScore scrape) | Point order only | ATP and WTA tour level, 2015–2025 (≈47,000 matches, inferred) | None: win or loss per point only | Seen: partial reads | Download, 263 MB | SofaScore-derived; its MIT label is not credible | No |
| 24 | **Small shot and video sets** | Shot, video | F3Set (151 matches, 101 already charted in MCP); single-match sets (AO 2019 final, RG 2022 quarter-final); TrackNet, TenniSet, RacketVision, OSL | Frame timing, ball pixel positions | Seen | Download | Mixed | Partly |

**Row 21, who to ask:**
* Tennis Australia: its 2023 "AO Data Slam" released 120,000 tracking points; no public copy was found.
* USTA and IBM: the US Open's "SlamTracker 3D" lets fans "follow ball positions in real-time", behind a Firebase sign-in. Per-serve limb tracking may also exist.
* AELTC and Hawk-Eye: Wimbledon 2016–18 tracking has gone to academic studies.
* Sackmann: the full Match Charting Project.

**Row 22, who sells it:**
* TDI's Tennis Data Platform (a sandbox is claimed).
* TennisViz and Hawk-Eye.
* Sportradar Live Data (ball bounce coordinates).
* Sportradar DDE, the former IMG ARENA Slam tracking feed: live only, and its REST host closes on 30 Sep 2026.
* Golden Set Analytics.

### Notes on the top rows

* **Rows 2–5 (Slam feeds).**
  * *Coverage flags.* Coverage comes from each draw file's `statsLevel` flag ("H" = full data). One US Open match marked "H" in its draw had an empty history, so the counts can slightly overcount.
  * *Pre-2025 Wimbledon qualifying* had no electronic line calling. Its points carry outcome, stroke side and clock time, but no speed, placement or distance.
  * *Clock times.* `EpochTimeStart` and `EpochTimeEnd` were filled on every sampled point from 2019 to 2026. They would allow an exact join to Polymarket price histories.
  * *Likelihood-to-win rows* lag the point by a median of 63 seconds, so join them on point number.
  * *Terms quoted in full* in [the Slam notes](../../../data/studies/granular_data_leads/research_notes/B_grand_slams.md).
* **Row 7 (Court Vision copies).**
  * The per-point CSV has 64 columns, from `serve_speed_kph`, `spin_rpm` and `serve_dir` through the serve, return and last-shot bounce coordinates to `point_end_type`.
  * The raw JSON keeps a hit/peak/net/bounce set for every stroke of a rally.
  * Two RG 2024 samples had tracking on only 36–42% of rows; AO 2022–23 samples had about 100%.
  * `ryurko/hawkeye` predates the encryption, so its 2019–21 subset is the cleaner cross-check.
* **Row 8 (website charts).** Each chart page embeds a `pointlog` that spells out every shot, for example: "1st serve wide, fault (long). 2nd serve down the T; backhand return down the middle (very deep); forehand inside-out …, unforced error". Checked on a 2018 chart (Wozniacki v Errani) and a 2026 chart; both carried a full point log. The list with URLs is [tennis_abstract_chart_gap.csv](../../../data/studies/granular_data_leads/tennis_abstract_chart_gap.csv).
* **Row 9 (TDI).**
  * About 446 of the ten careers' matches would carry full per-point outcomes: 129 tour-level matches of 2025–26 and 317 Challenger matches of 2026 (inferred from the ATP activity files).
  * Live Tennis API's new outcome tags (row 17) almost certainly come from this same official ATP/TDI point feed.
* **Row 14 (ATP Stats Centre).** The files return 403 to a plain request and 200 with a browser user agent plus `Referer`/`Origin` headers. Each holds `{"lastModified", "response"}`, the response being base64 AES ciphertext. A StackOverflow answer and two GitHub scrapers describe a key built from `lastModified`; that description was not tested here.

## Width: which per-point stats each source adds

Every source below gives the point winner, order, server and score; most give break, set and match-point flags.

**Legend:**
* ✓ seen in a payload;
* d documented by the provider or a third party, not seen;
* a match or set totals only;
* p partial (some years, courts or events);
* – absent.

| Source | Clock time | Ace, DF | 1st / 2nd serve | How it ended (W / FE / UE, net / out) | Last stroke | Rally length | Serve speed | Serve / return placement | Net approach | Every shot | Ball 3-D, spin | Player position, movement | Model metrics |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| *Held:* Slam archive 2011–24 | – | ✓ | ✓ | p (W, UE) | p | p | ✓ | p | ✓ | – | – | p | p |
| *Held:* MCP export | – | ✓ | ✓ | ✓ | ✓ | ✓ | – | ✓ | ✓ | ✓ | – | – | – |
| *Held:* Sackmann strings | – | ✓ | – | – | – | – | – | – | – | – | – | – | – |
| *Held:* SofaScore, TennisLive | – | ✓ (SofaScore) | – | a | a | – | – | – | – | – | – | – | – |
| *Held:* Live Tennis API sample | ✓ | – | – | – | – | – | – | – | – | – | – | – | – |
| MCP pre-2010 files, website charts | – | ✓ | ✓ | ✓ | ✓ | ✓ | – | ✓ | ✓ | ✓ | – | – | – |
| Wimbledon and US Open feeds | ✓ | ✓ | ✓ | ✓ | ✓ | p | p | p | ✓ | – | – | p | p |
| AO 2026 match centre | ✓ | ✓ | – | ✓ | p | – | a | – | – | – | – | – | – |
| WTA API | ✓ | a | – | a | a | a | – | – | a | – | – | – | ✓ |
| Court Vision copies (AO, RG) | – | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | p | p | ✓ | ✓ | – |
| TDI Tennis Results | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | ✓ | – | – | – | a |
| ATP MatchBeats and Rally files | – | d | d | d | d | d | d | – | d | – | – | – | – |
| ATP Court Vision files | d | d | d | d | d | d | d | d | – | p | d | d | – |
| SirGenkii fork (ATP, Jan–Apr 2025) | – | ✓ | ✓ | ✓ | – | ✓ | ✓ | – | ✓ | – | p | – | – |
| Sportradar widget feed | ✓ | ✓ | ✓ | – | – | p | – | – | – | – | – | – | – |
| Live Tennis API tags (from Sep 2026) | d | d | d | d | – | – | – | – | – | – | – | – | – |
| `skoval` 2016–17 strings | – | ✓ | ✓ | – | – | – | – | – | – | – | – | – | – |
| Monash return impact | – | – | ✓ | – | – | – | – | ✓ | – | – | p | – | – |
| From AO to AI | – | – | ✓ | ✓ | ✓ | ✓ | – | p | – | – | p | ✓ | – |
| Sportradar API v3 | d | d | d | a | a | – | – | – | – | – | – | – | – |
| STATSCORE | – | d | d | – | – | – | – | – | – | – | – | – | – |
| Stats Perform MA21 | d | – | d | – | d | – | – | p | – | – | – | – | – |

**Notes on specific cells:**
* **Wimbledon and US Open, rally length:** rally counts are patchy before 2025.
* **Wimbledon and US Open, speed and placement:** these need line-calling cameras. Main draws have them; US Open qualifying from 2022 and Wimbledon qualifying from 2025.
* **Wimbledon and US Open, model metrics:** likelihood-to-win 2025–26, US Open 2026 serve biomechanics, Wimbledon 2024–25 TennisViz.
* **Court Vision copies, every shot:** coordinates are given for every stroke, but a stroke type only for the last one.
* **Sportradar widget feed, rally length:** only a proxy, the seconds from serve to point end.
* **Slam archive, model metrics:** IBM's per-point momentum score only.
* **From AO to AI, placement and ball columns:** they describe the last two shots of the rally (depth, distance from sideline, speed, net clearance), not the serve or return.

**The width that is missing outside the Slams and the charts, and where it is:**

| Missing width | Where it is |
|---|---|
| First or second serve | TDI (2025–); ATP Stats Centre files (encrypted, 2021–; decrypted copies for 2021 – April 2025); Sportradar widget feed (forward only); Live Tennis API tags (paid, Sep 2026–); `skoval` strings (2016–17) |
| How the point ended | TDI; ATP MatchBeats; the decrypted Stats Centre copies (tour level, 2021 – April 2025); AO 2026; Live Tennis API tags |
| Rally length and last stroke | TDI; ATP Rally Analysis |
| Clock time per point | TDI; the Slam feeds, including editions already held; WTA API; Sportradar widget feed |
| Tracking | The Court Vision copies (AO and RG on GitHub; ATP 2021–24 on Hugging Face); ATP Court Vision files; the Monash return-impact file; From AO to AI (joinable through the 2019 Tennis Australia release) |

## Checked and set aside

**No width beyond what is held:**
* **Enetpulse:** score after each point only; its per-point times are batch update times.
* **Score-level APIs:**
  * api-tennis.com: score plus break, set and match-point flags only.
  * Matchstat / Tennis-API.com and its apparent white label SportsAPI365.
  * Goalserve: its samples carry no points.
  * **Data Sports Group:** no point method at all.
  * BetsAPI and Podium.
  * Broadage: matches within ±7 days only.
* **Other sites and products:**
  * The OnCourt replay: score and server only.
  * Flashscore and Tennis24.
  * The SofaScore resellers on RapidAPI.
  * LSports: live counters only.

**No per-point data, or no history kept:**
* atptour.com's Hawk-Eye statistics JSON: a box score, even at tour level.
* ProTennisLive: 503 errors; a token-only API with no per-point structure.
* The ATP app's live gateway: last point only, while the match is live.
* The United Cup: an ATP box score.
* Davis Cup, Billie Jean King Cup, the Laver Cup and the Olympics: no statistics found.
* Wimbledon's archive of 49 classic matches: negligible volume.
* The US Open Power Index: player level.

**Not professional or not new:**
* HF TennisDB and Kaggle st311-tennis: amateur video.
* `skoval/deuce`: bundles Sackmann data.
* Kaggle `alessiore02`: a Sackmann copy.

## What could be done first (options, not decisions)

1. **Stage the MCP pre-2010 point files.** Same source and licence as data already held. It fills the missing points of 2,382 of the 2,416 charted matches that lack them.
2. **Decide on the Slam feeds before they disappear.**
   * The Australian Open 2026 match centre (about 604 requests) will probably be replaced in January 2027.
   * The `2025.wimbledon.com` host that serves Wimbledon's older years could be retired at any time.
   * The US Open's and Tennis Australia's terms bar automated extraction, and Wimbledon's archive host bars it in robots.txt. The owner's 23 September decision covered SofaScore and TennisLive only.
3. **Ask for permission where the width is** (on 24 September the owner ruled asking out as a route; see [access routes](access-routes.md)):
   * TDI: how every ATP and Challenger point since 2025 ended.
   * Sackmann: 6,447 charts.
   * Tennis Australia: tracking.
   * USTA and IBM: 3-D ball positions.
4. **Decide whether data decrypted by others, or by the project, is acceptable:**
   * the GitHub Court Vision copies (row 7);
   * the SirGenkii fork (row 10);
   * the Hugging Face copy of 2021–24 ATP Stats Centre data ([TDI and open data](access-routes-tdi-and-open-data.md));
   * the ATP Stats Centre files (row 14).
5. **Capture going forward only if in-play point data is wanted from now on:** Sportradar's widget feed or Live Tennis API's tags.

## For the source register (not applied; the register is generated from its JSON files)

* **Missing from the register:**
  * the Wimbledon, US Open and Australian Open scoring feeds and the IBM extras;
  * the WTA API;
  * TDI Tennis Results;
  * the Infosys files for the ATP, AO and RG;
  * the GitHub Court Vision copies, the SirGenkii fork, the Monash return-impact file, `skoval/tennis-match-data`, From AO to AI and `marcosjn2`;
  * found on the follow-up: the Hugging Face ATP Stats Centre copy (`atlas-polybot/atp-pipeline-handoff`), `camroach87/etc3250-kaggle`, `TennisVisuals/tennis-match-data` and `ramizheman/TennisNLData`;
  * Sportradar's widget feed, Live Data and DDE.
* **Corrections:**
  * PUB005: the dump staged no pre-2010 point files.
  * PUB007: the export gap is 6,447 charts, withheld by design.
  * The 23 September note that Wimbledon 2024 was unreachable: the `2025.wimbledon.com` host serves 2019 and 2021–2025.

## Side findings for work in progress

* **SofaScore's point codes** (0 standard, 1 ace, 2 double fault) match Sportradar's published code list for its point events (inference).
* **Server shift at game end.**
  * Sportradar's feed already shows the next game's server on a game-ending point.
  * Some of the SofaScore records pulled so far may do the same. In [sofascore_point_codes.json](../../../data/studies/point_shot_sources/scrape/sofascore_point_codes.json), 161 of 8,861 ace-coded points were won by the player marked as receiving, and 94 of 6,784 double-fault-coded points by the player marked as serving.
  * Worth a check before those codes are used.

## Method and limits

* **What was done.**
  * Local measurement of the held data (schemas, fill rates, the chart gap).
  * Four research passes run in parallel on 24 September 2026: tour official data, Slam feeds, commercial vendors, open datasets.
  * Each pass's notes and probe logs are in [research_notes/](../../../data/studies/granular_data_leads/research_notes/) and [probe_logs/](../../../data/studies/granular_data_leads/probe_logs/).
  * The chart gap is reproducible with `./python.sh src/eda/granular_data_leads/mcp_website_gap.py`.
  * A follow-up the same day checked access routes:
    * rows 2–6 in [access routes](access-routes.md) (lanes F–I);
    * rows 9–13 in [TDI and open data](access-routes-tdi-and-open-data.md) (lane E, including 21 more TDI requests).
* **How sites were read.**
  * Public pages and APIs only. Some probes sent a browser user agent with `Referer` and `Origin` headers.
  * Several sites whose terms forbid automated access were read as bounded measurements, not acquisitions:
    * TDI: about 25 requests, 13 of them match pages;
    * the Slam feeds: about 300 requests, mostly draw files;
    * Infosys: mostly HEAD requests;
    * Sportradar's widget feed: 16 requests.
  * GitHub was read through the owner's logged-in `gh` CLI, which only raises rate limits.
* **Limits.**
  * **Slam counts** come from draw-file flags, which can slightly overcount.
  * **TDI's coverage** beyond the pages read is the provider's claim.
  * **The Infosys file contents** are third-party descriptions, because nothing was decrypted.
  * **The GitHub datasets' counts** come from their own catalogues.
  * **The paid feeds' fields** are documentation only.
  * **Nothing here was measured match by match** against the ten careers, except the inferred TDI reach.

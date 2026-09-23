> HISTORICAL LLM RESEARCH — unapproved seed material, preserved from the inherited one-shot output. Claims of verification, decisions, phases, deadlines, and exclusions below are the prior LLM's assertions, not current project policy or an approved roadmap. Paths below describe the old repository layout; start at the archive index.

# 02 — Data & Tools Landscape (verified June 2026)

*Sources: multi-agent research run 2026-06-10 (full raw facts + adversarial verifications in
`docs/research_raw/sackmann-ecosystem.md` and `research_raw/odds-data-apis.md`) plus hands-on
verification in this repo (downloaders in `src/ingest/` were actually run against the live
sources on 2026-06-10).*

## The free data spine (what this repo already downloads)

### Jeff Sackmann's GitHub repos — results + match stats, no odds

`tennis_atp` / `tennis_wta`: per-year match CSVs 1968–2026, players files, rankings by decade.
49 columns per match: tournament metadata, winner/loser bios, score, and nine serve stats per
player (aces, double faults, serve points, 1st-in/won, 2nd-won, serve games, break points
saved/faced). Verified live on 2026-06-10 — both repos last pushed 2026-06-08, ATP 2026 file has
1,449 rows (current through June 8).

**The things that will bite you (all verified):**

- **The 2025 hiatus.** Zero commits 2024-12-30 → 2026-05-06: the entire 2025 season was missing
  for ~16 months before being backfilled in May 2026. Cadence since resumption is ~biweekly.
  **Never build the pipeline assuming this repo is fresh** — wire a fallback current-season
  results source from day one (candidates: TML-Database / stats.tennismylife.org, recommended in
  Sackmann's own issue #270; OnCourt, below; Flashscore scraping).
- **Serve-stat eras differ by tour.** ATP: stats from 1991 (tour-level), 2008 (Challengers),
  2011 (qualifying). **WTA: measured non-empty serve stats = 0% in 1999, 12% in 2003, 70% in
  2008, 95% in 2016, ~98% now** — a women's model needs a feature fallback for the long
  historical tail (mirrors the UFC pipeline's separate women's handling).
- **Score-code taxonomy** (adversarially verified against all 59 ATP files, 199,389 rows):
  `W/O` (1,301 rows) but also `' W/O'` with leading space (10 rows, never fixed), `Walkover`
  spelled out (6 Davis Cup rows), `RET` (4,012) + one `' RET'`, `DEF` (157) / `Def.` (4) /
  `Default` (3), `ABD` (22), `UNK` (96, pre-1987), 9 NaN. **Normalize `score.strip()` and match
  against sets** — and note `minutes` is 0.0 (not blank) on most W/O rows, so minutes-notnull is
  NOT a valid played-match filter. The RET score string itself tells you whether a set was
  completed (e.g. `1-4 RET` = no completed set), which matters for settlement-aware labels (doc 03).
- **Davis Cup rows** (`tourney_level == 'D'`) are mixed into the per-year files and are the main
  source of blank surfaces (all 53 blank-surface 2023 rows are Davis Cup). Coverage is patchy
  (multiple open issues). Exclude or special-case them.
- **Player identity issues are real**: duplicated players, father/son confusion (the Martin Damm
  case), brothers — open issues as of 2025-2026. The May 2026 resumption commit itself admits
  "some duplicate player records, some assorted missing ITF matches".
- **License**: CC BY-NC-SA 4.0 (attribution, non-commercial). Whether a private for-profit
  betting pipeline is "commercial" is legally unsettled; issue #269 asked Sackmann exactly this
  in March 2026 and sits unanswered. Practical exposure for personal, non-redistributed use is
  minimal, but don't ever resell/redistribute derived data.

### tennis-data.co.uk — the free results+odds join

One Excel workbook per tour-year: ATP 2000–2026, WTA 2007–2026 (odds columns from 2001/2007).
Decimal odds, near-closing prices sourced from OddsPortal ("most recent before play starts").
Updated weekly (verified: banner said June 7 on June 10). Modern files carry only:
`B365W/L` (Bet365), `PSW/PSL` (Pinnacle), `MaxW/L`, `AvgW/L`, and — since 2025 — `BFEW/BFEL`
(Betfair Exchange, undocumented in the site's own notes.txt).

**The headline discovery (verified by direct parse, and visible in this repo's downloaded
files): the Pinnacle columns are DEAD.** PSW/PSL fill rates: 99.6% (2024) → 95.8% (2025, decay
starting ~July, sharp break October) → **5.5% (2026: 71 January rows, zero from February
onward)**. The adversarially-verified cause: **OddsPortal delisted Pinnacle between Jan 1 and
Feb 1, 2026** (Wayback-bracketed) — not, as first assumed, the July 2025 Pinnacle API shutdown
directly. Meanwhile `BFEW/BFEL` is 92.4% filled in 2026.

**Consequences:**
1. Any backtest spanning 2025–2026 must splice its sharp-price reference from PSW/PSL to
   BFEW/BFEL around Oct 2025–Jan 2026 — and the two are NOT equivalent (exchange odds are
   commission-free gross prices; bookmaker odds embed vig). Nobody has published a guide for
   this splice; we have to validate BFE semantics empirically against Betfair historic data.
2. Going forward, free Pinnacle closing prices for tennis no longer exist anywhere — if we want
   Pinnacle CLV (closing line value: the price you got vs the closing price), **we must capture
   Pinnacle quotes ourselves from day one** or pay for them (below).

## Odds feeds (post-Pinnacle-API-shutdown reality)

Pinnacle closed its public API on **July 23, 2025** (bespoke access for "select high value
bettors & commercial partnerships" via api@pinnacle.com; with strict limits — 1 request per 2
minutes per endpoint per sport, 2 IPs; was ~€5,000/month when public). The post-shutdown menu:

| Source | What | Price | Notes (verified) |
|---|---|---|---|
| **Pinnacle guest API** (guest.api.arcadia.pinnacle.com) | live odds + `maxRiskStake` limits, read-only | free | A verifier pulled live ATP/WTA/Challenger/ITF moneylines + limits with a guest key on 2026-06-10. Unofficial, could close anytime — but currently the cheapest direct Pinnacle read. |
| **the-odds-api.com** | multi-book snapshots incl. Pinnacle (key `pinnacle`, EU region, "from public website, may incur delay") | free 500 credits/mo; $30/mo 20K; $59/mo 100K | Historical snapshots back to June 2020 at 10-min (5-min from Sep 2022) intervals, 10× credit cost; no native opening-line endpoint — reconstruct from snapshots. Tennis = match-winner mainly; spreads/totals thin. |
| **BetsAPI** | Pinnacle odds product; live events incl. Bet365 feeds | ~$10/mo packages | Its Pinnacle API reference is hosted on Pinnacle's own GitHub org (pinnacleapi.github.io/betsapi) — looks like a sanctioned redistribution channel. |
| **bettingiscool.com Pinnacle archive** | every Pinnacle line movement incl. openers + closers, tennis from Jan 2021 | €49–249/mo | The most complete historical Pinnacle tennis line-movement source available to individuals. The shortcut to a CLV/line-movement backfill 2021–2026. |
| **pinnodds.com** | live Pinnacle stream (MQTT/WebSocket), ~100–500ms claimed | $0–299/mo, **pays in crypto** | Gray-area (authenticated tap of Pinnacle's broker); longevity risk; fits crypto rails. |
| **OddsPortal scraping** | multi-book odds + movement | free + proxies | Medium difficulty; OddsHarvester (GitHub) actively maintained (v0.3.0, May 2026), covers tennis markets incl. movement. Pinnacle no longer listed on OddsPortal (since Jan 2026). |
| **Betfair historical files** | full exchange price/volume history since 2016, tennis package | Basic free (1-min, last price); Advanced/Pro paid | **Caveat: Betfair blocks Canadians** — even the data-purchase flow needs a Betfair login. May be unavailable; price list is behind login. |
| **OpticOdds / OddsJam API** | enterprise multi-book | sales-call pricing | Not realistic for a solo bettor. |
| **api-tennis.com** | tennis-specific scores + soft-book odds | $40–80/mo | No Pinnacle evidenced; useful as scores feed, not sharp prices. |

## OnCourt — the cheap commercial spine (verified in depth)

oncourt.info (Windows desktop app): **48.95 EUR/year or 88.95 EUR lifetime, 24 EUR/year
renewal, accepts USDT (Tron)** — fits the crypto rails. Live DB counter on 2026-06-10:
**2,023,382 matches** (ATP from 1990, WTA 1997, Challengers 1998, qualifying 2000, ITF 2002+,
juniors 2003), 778,492 with stats, **intraday updates** ("Updated: 49 min ago" observed).
Includes **Pinnacle odds with odds-movement history** (Pinnacle is the only book; movement
granularity/timestamps undocumented), Excel export, and — decisive — **licensed users get the
password to the underlying Microsoft Access database (OnCourt.mdb) for their own development**.
Community projects (damienld/Tennis-predict, RileyCullen/oncourt-parser) confirm reading the
.mdb directly is the standard automation pattern. A separate B2B MySQL-dump feed exists
($200 + $50/mo) if the .mdb route proves restrictive.

**Why it matters:** for ~€50/year it simultaneously solves (a) the Sackmann freshness problem
(intraday results), (b) lower-tier coverage (Challenger/ITF depth), and (c) some historical
Pinnacle odds-movement data. Verify the .mdb's odds-movement timestamps before trusting it for
CLV — granularity is publicly undocumented.

## Point-by-point and in-play data (the hard wall)

- Official point-level data flows from the umpire's tablet through exclusive rights deals:
  ATP/Challenger → Tennis Data Innovations → Sportradar (2024–2029); ITF → Infront (2025–2029).
  Enterprise licensing only (reported $500–1,000/mo entry, $10K+/mo realistic) — not a solo-bettor option.
- Sackmann's `tennis_slam_pointbypoint` is **stale** (last commit Oct 2024; no AO/RG since 2023;
  nothing from 2025–2026). `tennis_pointbypoint` (non-slam) dead since 2017.
- Match Charting Project: alive (17,768 matches charted as of June 2026, commits through
  May 2026) but volunteer-selected → biased toward famous matches; good for elite-player
  serve/return tendency priors, not an unbiased training sample.
- In-play latency: market suspensions reset within 1–2s of each point; books get
  umpire-tablet signals; Betfair adds ~5s bet delay specifically to blunt courtsiders. **An
  individual polling scraped scoreboards cannot win the in-play latency race in 2026.** In-play
  modeling is Phase-5 material at best (manual, slower markets), not a foundation.
- Live scores for monitoring (not edge): Sofascore unofficial API (needs ~25–30s between calls),
  Flashscore scrapers/Apify actors, BetsAPI events ($10/mo class).

## R/Python package landscape

- **welo** (R, CRAN, active — manual re-rendered May 2026): Weighted Elo per Angelini, Candila &
  De Angelis (2022) — the K = 250/(N+5)^0.4 spec with optional 1.1× slam multiplier, margin-of-victory
  weighting, plus betting backtest functions. **Feeds entirely off tennis-data.co.uk** (2013+).
  Useful as a reference implementation to validate our Elo numbers against.
- **deuce** (R, GitHub-only, Kovalchik): ~274MB bundled Sackmann-derived datasets + Elo;
  sporadically refreshed (Jul–Aug 2025 after a 2.5-year gap). Snapshot tool, not a feed.
- **Python: nothing maintained.** skelo (Elo/Glicko2 estimators) and tennisim (point→match
  simulators) both dormant since 2022. **We write our own loaders — same as UFC.** (Already
  started: `src/ingest/`, `src/ratings/elo.py`.)

## What this repo has verified hands-on (2026-06-10)

- `download_sackmann.py` pulls ATP 2023–2025 clean (625KB/650KB/617KB files, header-validated).
- `download_tennis_data_couk.py` pulls ATP+WTA 2024–2026 via the `/{year}/{year}.xlsx` and
  `/{year}w/` URL patterns (xlsx first try, zip fallback ready).
- The 2026 ATP workbook: 1,296 rows through the French Open final, header
  `...,B365W,B365L,PSW,PSL,MaxW,MaxL,AvgW,AvgL,BFEW,BFEL` — and PSW/PSL blank on recent rows,
  confirming the Pinnacle-column death first-hand.
- Elo walk-forward on the three downloaded seasons: log loss 0.638 / accuracy 62.9% post
  burn-in, top-5 ratings Sinner-Alcaraz-Djokovic — pipeline spine works end to end.

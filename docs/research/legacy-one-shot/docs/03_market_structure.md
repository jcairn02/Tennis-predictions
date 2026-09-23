> HISTORICAL LLM RESEARCH — unapproved seed material, preserved from the inherited one-shot output. Claims of verification, decisions, phases, deadlines, and exclusions below are the prior LLM's assertions, not current project policy or an approved roadmap. Paths below describe the old repository layout; start at the archive index.

# 03 — Market Structure: Books, Settlement Rules, Microstructure (June 2026)

*Sources: multi-agent research run 2026-06-10 with adversarial verification of decision-critical
facts (raw archives: `research_raw/crypto-marketmaker-books.md`, `research_raw/retirement-void-rules.md`,
`research_raw/microstructure-inefficiencies.md`). Settlement rules were double-verified (2 votes
each). Facts marked (m) are medium-confidence single-source; verify before money moves on them.*

## 0. The constraint that shapes everything: province

Canadian access splits cleanly (verified):
- **Compliance-conscious crypto operators geo-block Ontario specifically** while serving the
  rest of Canada: Stake, BC.Game, Sportsbet.io, SX Bet, Polymarket (permanently banned by an
  OSC settlement until ≥ April 2027), and per some third-party reviews Cloudbet (its own
  restricted list omits Canada entirely — conflicting; needs a signup test).
- **Costa Rica grey books serve all provinces including Ontario**: BetOnline, Bookmaker.eu, Bet105.
- **Pinnacle serves Ontario only via fiat-only pinnacle.ca** (AGCO-licensed; Ontario's framework
  bars crypto deposits). Other provinces use pinnacle.com international, which takes
  **BTC/LTC/USDT (converted to fiat balance; USDT max $125K CAD/deposit)**.
- **Betfair Exchange: Canadians blocked outright** — the entire Betfair tennis-trading ecosystem
  (bots, exchange data with login, lay hedging) is off the table.

## 1. The book menu (tennis, crypto, market-maker lens)

| Book | Crypto | Tennis margin | Winners tolerance | Tennis limits | API | Retirement rule (moneyline) |
|---|---|---|---|---|---|---|
| **Pinnacle** | BTC/LTC/USDT → fiat balance | ~2–3% (102–103% book) | **Winners Welcome** (published policy, decade-standing) | measured live 2026-06-10: ATP median ~$2–4K, max $6K; Challenger $1–2.5K; ITF $150–450; ramps toward start; re-bet after interval allowed | public API closed Jul 2025; guest read API exists (unofficial); bespoke via api@pinnacle.com | **1 set completed = action** (verified 2×) |
| **BetOnline** | ~17 coins (m) | baseline ~-110 ≈ 4.8%; reduced-juice promos selective (m) | sharp-tolerant but documented limiting of winners (live limits cut) (m) | high on mainlines (m) | none | **1 set = action** (verified 2×) |
| **Bookmaker.eu** | BTC/ETH/LTC/USDT/USDC; payouts capped $10K × 5/week | unmeasured (m) | "welcomes winners" but degraded — limiting reports (m) | $40K+ US sports anecdotes; tennis unknown | none | **VOID on retirement (full match)**; DQ = action (verified 2×; internal inconsistency documented) |
| **Bet105** | crypto-only (BTC/ETH/USDT/USDC), $250K/week out | -105/-105 on US mainlines; tennis unverified (m) | claims equal limits for winners; shallow track record (relaunched 2024, Costa Rica) (m) | five-figure anecdotes (m) | none | **1 set = action** (aggregator-sourced; book's own rules page dead — confirm with support) |
| **Cloudbet** | 20+ coins, crypto-native | ~3.5–5.9% measured (NOT Pinnacle class) (m) | "built for sharps" — book's own claim, unverified (m) | tennis ~0.02–0.06 BTC/match in dated review — small; verify (m) | **self-serve Feed + Trading + Account APIs** (unique among conventional books) | **1 set = action**; live = "same as prematch" (verified, current rules page); Bet Builder voids on any retirement |
| **Sportsbet.io** | crypto-native | ~8% measured (m) — retail | retail behavior toward winners (m) | — | none | **VOID on retirement** (verified) |
| **Stake** | 20+ coins + CAD balances | ~4–5%; 2–3% slams (m) | undocumented either way | — | none (OpticOdds carries its odds) | **VOID on retirement** (verified, indexed text) |
| **BC.Game** | 130+ coins | average crypto-book class (m) | undocumented | — | none | **unverifiable** (rules page bot-blocked; BetBy platform template = void) — also Anjouan license since Dec 2024 = counterparty risk |
| **Polymarket** | USDC on Polygon | taker fee ≈ 0.75–1% notional at evens; **maker rebates 20–25%** | n/a (exchange) | depth: $42M traded on 2026 French Open winner market; per-match depth below slams unquantified | **full CLOB API + py-clob-client** | **advancing player WINS even on 1st-game retirement; walkover/cancel = 50-50 resolution (NOT a refund — real P&L event)**; rules are per-market templates (re-read every market) |
| **SX Bet** | USDC on-chain (SX rollup) | no trading fees; cost = spread | n/a (P2P exchange) | niche liquidity, unquantified — sample via API | **public read API + authenticated betting API** | **1 set = action** (verified); totals: overs stand if threshold passed (asymmetric — clarify with support) |
| **Brokers: Sportmarket / AsianConnect / BetInAsia** | BTC/USDT/USDC accepted; Canada accepted (all three) (m) | underlying books' sharp class (PS3838/SBObet/IBCbet ~102–103%) | brokers advertise never limiting; Asian books price winners rather than ban (m) | per-book on slip | Sportmarket undocumented; **BetInAsia BLACK Pull/Push API: €600 setup + terminated under £50K/month turnover** | follows underlying book |
| *(reference)* bet365 | no crypto | retail | limits winners aggressively | — | none | VOID base rule + "final set" clause (scope unclear) + Retirement Guarantee promo (opponent retires = paid; Bet-Credits) |

**Practical menu reading** (my synthesis): Pinnacle is the anchor (price quality + winners
policy + limits). Brokers are the post-API-era route to Pinnacle-class prices at scale with
automation. Cloudbet is strategically interesting *despite* mid margins because it's the only
conventional book with a self-serve bet-placement API — its prices may lag sharp moves (a
mid-margin book with an API can be picked off by a model anchored to sharper prices, if limits
allow). Polymarket + SX Bet are the crypto-native exchanges with full APIs and near-zero fees —
plus the most bettor-favorable retirement rules on the action side.

## 2. Settlement rules are an EV layer, not a footnote

Retirements ended **4.8% of ATP-level matches in 2025** (record high; ~2.9–3.4% at
Challenger/ITF; ~39% of slam retirements happen in set 2, a substantial minority before one
completed set). Books settle the SAME retired match differently (all rules above verified):

- **Void unless match completed**: Stake, Bookmaker.eu, Sportsbet.io, bet365(base)
- **One set completed = action**: Pinnacle, BetOnline, Cloudbet, SX Bet, Bet105, Betfair Exchange
- **Ball served = action (advancing player wins, even retirement at 0-0 in set 1)**: Polymarket
  — which also uniquely resolves walkovers at 50-50 (both sides paid $0.50/share: holding a 75c
  favorite into a walkover LOSES 25c/share; holding the dog GAINS).

**EV decomposition** (from the research, worth wiring into `src/betting/`): for a bet on player
A at decimal odds d, with retirement probability r (split r₁ before / r₂ after one completed
set), q = P(A advances | retirement), p_c = P(A wins | completed):

```
EV_void_book     = (1−r)·(p_c·d − 1)
EV_one_set_book  = (1−r)·(p_c·d − 1) + r₂·(q·d − 1)
EV_polymarket    = (1−r)·(p_c·d − 1) + r·(q·d − 1)      (+ 50-50 walkover term)
```

Same quoted price ⇒ different EV by venue: **injury-doubt players are worth more at void books**
(refund shields the retirement scenario the market has priced in); **healthy opponents of
injury-doubt players are worth more at action venues** (they get paid on the retirement). This
"rule arbitrage" is documented practice among professionals (arbusers thread), and **nobody
quantifies the rule premium publicly** — doc 04 makes this a core opportunity.

**Kelly under void rules**: a void outcome is a push with probability π — renormalize win/loss
probabilities by (1−π) and scale exposure; void-book positions on injury-doubt players carry
lower effective variance per nominal stake. Bet sizing must be venue-aware, not just EV.

**Training labels**: a retired match's "winner" is settlement-dependent and injury-contaminated.
Plan: train the win-probability model on completed matches; maintain a separate per-player
retirement/withdrawal hazard estimate; settle every backtest bet under the actual rule of the
venue it would have been placed at. (Sackmann's RET score strings tell you whether a set
completed — see doc 02.)

## 3. Microstructure and documented inefficiencies

- **Line origination**: market-makers (Pinnacle, Bookmaker/CRIS, Circa) post first at small
  limits and ramp toward start ("limits tend to increase towards the start of the event" —
  Pinnacle's own wording; the specific "25% of max" ladder folklore was REFUTED as
  third-party illustration). For tennis specifically, Pinnacle + Betfair lead; others lag by
  minutes or more.
- **Open vs close**: Sports Trading Network, 68,361 Pinnacle tennis matches 2015–2019:
  opening-price efficiency gradient 0.825 vs 1.0 at close — **openers are measurably softer than
  closers, and prices don't fully converge even by close**. No public study quantifies
  open-to-close movement magnitude by tour tier — buildable from our own capture (doc 04).
- **Favorite-longshot bias (tennis-specific, verified)**: blanket-backing ATP favorites ≈ −2.0%
  ROI vs −5.6% for dogs (~40K matches, Pinnacle closing); ROI collapses above ~6.0 decimal; a
  10%-implied longshot wins ~6% (≈ −40% ROI). Lahvička (~45K matches): FLB is **strongest in
  lower-ranked matches, later rounds, high-profile events** — consistent with books defending
  against insider info, not bettor irrationality. Exchange prices show FLB too. **Implication:
  our model's +EV dog picks must clear a higher bar than +EV favorites; consider asymmetric EV
  thresholds by odds bucket** (echoes the UFC pipeline's delta_udog bar).
- **CLV nuance (tennis-specific)**: Pinnacle's close is the standard skill benchmark, BUT a
  ~3,000-bet ATP case study showed +8.9% realized ROI where devigged closing lines implied
  −0.2% — tennis closes are efficient *on average*, not per-bet; CLV can understate a sharp
  tennis bettor. Track CLV as a health metric, not the sole verdict (and remember: from Feb 2026
  free Pinnacle closes don't exist — we must capture our own; doc 02).
- **Devig method matters in tennis**: odds-proportional (logarithmic) vig removal tracked
  outcomes at +0.47% vs breakeven across 68K matches; equal-split devig was −2.73%. Use
  odds-proportional devig for the *market-probability feature*. (The EV gate itself stays on raw
  vig-inclusive odds, exactly like the UFC pipeline.)
- **In-play is the market**: ~90% of tennis bets at Entain brands are in-play (highest of any
  sport); tennis is the #2 sport for operator integrity alerts and in-play volume. We
  deliberately cede this to Phase 5+ — the latency wall (doc 02) makes pre-match/early lines the
  solo quant's wedge.
- **Integrity by tier (ITIA, verified quarter by quarter)**: alerts 2023: 101, 2024: 95,
  2025: 68, Q1 2026: 21 — **overwhelmingly Challenger/ITF; zero at slams/ATP-WTA main level in
  most quarters** (~0.2% of matches alerted overall). Combined with ITF limits ($150–450 at
  Pinnacle, measured) and sketchy injury info, the lower tiers offer the softest prices
  (Kovalchik's 10–20pp accuracy drop) but tiny capacity and real fixing tails. Challenger is the
  interesting middle: limits only 2–4× below main tour, alert rates low single digits/quarter.
- **WTA**: 11.5% more matchup intransitivity than ATP (the GNN paper's profitable subset);
  structurally noisier vs rankings (higher-rank wins 62–68%). The famous "Wikipedia buzz" WTA
  ROI paper (17–29%) was **debunked** — profits traced to a single mispriced outlier bet;
  post-2020 out-of-sample profits vanish. Lesson: treat all published WTA inefficiency claims
  skeptically; validate everything walk-forward.
- **Fatigue/scheduling**: the one rigorous test (post-final-set-tiebreak, n=88, 2013-14) found
  the effect real but **priced** (−2.98% level-stakes). Everything else (ATP-250 winner's curse
  etc.) is unverified folklore — i.e., an open research lane, not a known edge.

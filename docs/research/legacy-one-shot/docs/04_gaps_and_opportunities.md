> HISTORICAL LLM RESEARCH — unapproved seed material, preserved from the inherited one-shot output. Claims of verification, decisions, phases, deadlines, and exclusions below are the prior LLM's assertions, not current project policy or an approved roadmap. Paths below describe the old repository layout; start at the archive index.

# 04 — Gaps in the Market, and What a Solution Looks Like

*Synthesis of both research workflows (June 2026): the 14 verified academic findings (doc 01),
the 242-fact tools/market sweep (docs 02–03), and the ~30 explicit "nobody covers this" gaps the
research agents logged (preserved verbatim in `docs/research_raw/*.md` under "Gaps noticed").
Ranked by how directly a solo quant with an existing UFC betting pipeline can exploit them.*

## The one-sentence market read

Every consumer betting tool on earth defines "value" as *soft retail books deviating from
Pinnacle* — a workflow structurally useless to someone who can only bet market-maker books —
while the academic literature proves the market-maker's own price is beatable only on
structurally-blind subsets; **nobody productizes finding those subsets, capturing the data they
require, or pricing the settlement rules they interact with.** That's the lane.

## Tier 1 — gaps we should build against immediately

### Gap 1: No opening-line / line-movement capture exists for tennis (and free Pinnacle closes just died)
**Evidence:** tennis-data.co.uk = closing-ish only, Pinnacle column dead since Feb 2026 (doc 02);
the-odds-api = snapshots, no opening endpoint; OnCourt movement granularity undocumented;
Pinnacle Odds Dropper holds history but as an alert UI, no bulk export; bettingiscool (€49+/mo)
is the only movement archive and starts 2021. Nobody sells timestamped Pinnacle open→close
pairs a quant can join to model probabilities.
**Solution shape:** a **day-one odds recorder** — poll the Pinnacle guest API (+ the-odds-api as
backup, + Cloudbet/SX/Polymarket APIs since they're free) on a schedule (e.g. at line open, then
hourly, then 5-min near start), store every quote with timestamps in a local DB. This is the
**proprietary asset no competitor sells**, it compounds daily, and it's exactly the
"market momentum" data class already studied in the UFC pipeline (where line history had to be
begged from a friend's HF dump — this time we record it ourselves from day one). Cost: ~zero.
Optionally backfill 2021–2025 from bettingiscool for one or two months' subscription.

### Gap 2: Settlement-rule-aware EV is computed by nobody
**Evidence:** retirements ended 4.8% of 2025 ATP matches; rule classes verified to differ
across our bookable venues (void vs one-set vs Polymarket's advancing-player + 50-50 walkover);
academic benchmarks *exclude* retired matches entirely; no product or repo documents how
mid-match retirements hit training labels or venue EV; the rule premium in prices is
unquantified anywhere.
**Solution shape:** (a) a per-player **retirement/withdrawal hazard model** (recent
retirements, MTOs, age, walkover history — Sackmann data carries the labels; Tennis Abstract
documents non-randomness); (b) the **venue-EV layer** from doc 03's decomposition formulas, so
the same model probability prices differently at Pinnacle (one-set) vs Stake (void) vs
Polymarket (action); (c) backtests that settle each bet under the actual venue rule. This is
genuinely novel — published nowhere — and it converts a 1-in-20-matches risk event from noise
into edge (bet injury-doubt players where bets void; bet their opponents where retirements pay).

### Gap 3: No public model is odds-aware AND walk-forward honest AND calibrated AND staked
**Evidence:** open-source tennis repos are uniformly stale (2017–2020), ATP-biased, random-split
validated, accuracy-only, retirement-blind, and never distinguish opening vs closing odds in
training (verified across the most-starred repos; the one honest repo reports NEGATIVE ROI
reproducing a published paper). The methodological bar the UFC pipeline already clears —
market-anchored features, temporal validity, calibration, fractional Kelly, CLV tracking — is
unmet publicly in tennis.
**Solution shape:** port the UFC v2.5 discipline onto the tennis spine that's already scaffolded
here. **The stack itself is the edge** — not a secret model, but unleaked validation + market
anchoring + selective betting. Doc 01's verified precedents (Sipko's uncertainty-filtered ANN,
the intransitivity-gated GNN: +3.26% at Pinnacle 2023–2025) all profit by *betting a subset*.

### Gap 4: The bettable-book set is unscanned and unmeasured
**Evidence:** scanners don't cover the crypto/market-maker set (BetBurger's own stats: ~1
valuebet at Pinnacle on average); no published 2026 tennis margins for BetOnline, Bookmaker.eu,
Bet105, BC.Game; Cloudbet/SX/Polymarket tennis depth below slams unquantified; all expose free
APIs or odds via aggregators.
**Solution shape:** a small **margin/limit/depth monitor** over OUR books (Pinnacle guest API
maxRiskStake included — limits ARE market signal), producing the per-book overround table nobody
publishes, plus cross-book best-price routing under rule-adjusted EV (Gap 2). A model anchored
to Pinnacle prices picking off the slower mid-margin API books (Cloudbet) is a realistic
secondary income stream — that's the soft-book game, but inside the books we're allowed to use.

## Tier 2 — research lanes the literature leaves open (our studies pipeline)

### Gap 5: Unstudied scheduling/fatigue micro-angles
The only rigorous test (post-final-set-tiebreak) found the effect priced; back-to-backs,
late-night finishes, quick turnarounds, travel/timezone jumps are folklore. We have the exact
study machinery (UFC studies workflow) to test these walk-forward against captured odds.

### Gap 6: Favorite-longshot bias by tier/tour is unbuilt
Published FLB curves are ATP-aggregate only. tennis-data archives → FLB ROI curves by
ATP/WTA/Challenger and by era, feeding asymmetric EV thresholds by odds bucket.

### Gap 7: Sub-top-30 pricing weakness vs capacity
Verified: ALL models including bookmakers lose 10–20pp accuracy outside the top 30; ITIA alerts
concentrate at ITF (~95% sub-main-tour); measured limits: ITF $150–450 (skip — integrity tail +
no capacity), **Challenger $1,000–2,525 (only 2–4× below main tour — the interesting middle)**.
Nobody publishes a Challenger-focused model with honest validation.

### Gap 8: The name-crosswalk nobody maintains
Sackmann player_id ↔ tennis-data "Federer R." ↔ book feed names: every project re-implements
fuzzy joins; failure modes (father/son, brothers) match Sackmann's open identity bugs. We need
it anyway — maintained as a versioned mapping table with loud unmatched-row warnings (UFC
pipeline has the same pattern for fighter aliases).

### Gap 9: WTA is second-class everywhere
Public repos skip it; its serve stats only complete from ~2016 (measured); it shows MORE
intransitivity (the one verified profitable signal class) and noisier outcomes. A
separately-validated women's model (the UFC pipeline already does exactly this split) on a
properly audited WTA dataset is uncontested ground. Caution: the one famous WTA-inefficiency
paper was debunked — every claim gets walk-forward verification here.

## Tier 3 — noted, deliberately NOT pursued now

- **In-play modeling**: 90% of handle, but the latency wall (1–2s suspensions, umpire-tablet
  rights chains, ~5s exchange delays) is unwinnable solo in 2026. Revisit only as slow-market
  manual angles (e.g., between-sets entry) after pre-match works. (Phase 5+.)
- **ITF tier**: softest prices, but $150–450 limits + the integrity tail isn't worth the
  bankroll's tail risk.
- **Betfair ecosystem**: blocked for Canadians. All exchange-bot tooling is moot.
- **Buying picks** (MatchSignal €799–2,749/mo, tipsters): sells signals, not data/probabilities
  a quant can validate or blend; unaudited claims; wrong side of the build-vs-buy line for us.
- **Courtsiding / latency arms race**: rights-holder enforcement + capital intensity; no.

## Competitive moat summary

| Asset | Who else has it | Our cost |
|---|---|---|
| Timestamped multi-book tennis line history incl. openers (from day one) | nobody sells it | ~zero (APIs are free; cron + SQLite) |
| Settlement-rule-aware EV + retirement hazard | published nowhere | math is done (doc 03); model is a feature on data we already ingest |
| Walk-forward-honest, calibrated, market-anchored tennis model | no public repo; syndicates private | port of existing UFC discipline |
| Per-book tennis margin/limit/depth table for the crypto+MM set | unpublished anywhere | a monitoring script |
| Audited WTA dataset + separate women's model | nobody public | known pattern from UFC women's split |

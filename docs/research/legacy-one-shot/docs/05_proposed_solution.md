> HISTORICAL LLM RESEARCH — unapproved seed material, preserved from the inherited one-shot output. Claims of verification, decisions, phases, deadlines, and exclusions below are the prior LLM's assertions, not current project policy or an approved roadmap. Paths below describe the old repository layout; start at the archive index.

# 05 — Proposed Solution Architecture

*What we build, given docs 01–04. Design principle: port the UFC pipeline's proven discipline
(temporal validity, Bayesian shrinkage, calibration, EV gate on raw odds, fractional Kelly with
uncertainty haircuts, CLV tracking) onto tennis's better data and deeper market — and add the
two genuinely novel layers the research surfaced: a day-one odds recorder and
settlement-rule-aware EV.*

## System overview

```
                    ┌─ INGEST ────────────────────────────────────────────┐
 Sackmann CSVs ───► │ results+stats loader (chronology, score-code policy)│
 tennis-data.xlsx ► │ odds join (name crosswalk, BFE/PS splice)           │
 OnCourt .mdb ────► │ freshness fallback + Challenger/ITF depth [Phase 1+]│
                    └──────────────┬──────────────────────────────────────┘
                                   ▼
 Pinnacle guest API ─┐  ┌─ ODDS RECORDER (day one, always on) ────────────┐
 the-odds-api ───────┼► │ timestamped quotes: open → close, every book    │
 Cloudbet/SX/Poly ───┘  │ + Pinnacle maxRiskStake (limits-as-signal)      │
                        └──────────────┬──────────────────────────────────┘
                                       ▼
                    ┌─ FEATURES (all strictly pre-match) ─────────────────┐
                    │ ratings: surface-blend Elo (done) → WElo → serve/   │
                    │   return Bayesian aggregates (UFC-style shrinkage)  │
                    │ schedule/fatigue, H2H-shrunk, rank/points           │
                    │ market: devigged (odds-proportional) open + current │
                    │ retirement-hazard per player                        │
                    └──────────────┬──────────────────────────────────────┘
                                   ▼
                    ┌─ MODELS ────────────────────────────────────────────┐
                    │ LR baseline → LightGBM → AutoGluon (UFC v2.5 port)  │
                    │ symmetric A/B rows, RANDOMIZED sides, walk-forward  │
                    │ separate ATP / WTA models (UFC men/women pattern)   │
                    │ calibration on out-of-fold walk-forward preds only  │
                    └──────────────┬──────────────────────────────────────┘
                                   ▼
                    ┌─ BETTING LAYER ─────────────────────────────────────┐
                    │ venue-EV: rule-aware (void/one-set/action) formulas │
                    │ EV gate on RAW vig-inclusive odds (UFC convention)  │
                    │ FLB-asymmetric thresholds by odds bucket            │
                    │ uncertainty gate (sigma-rubric port) + frac Kelly   │
                    │   with push-renormalization + caps                  │
                    │ bet log → CLV vs own captured closes + realized ROI │
                    └─────────────────────────────────────────────────────┘
```

## Component decisions (with reasoning)

**Ratings stack.** Start from the verified-best odds-free baseline (FiveThirtyEight Elo spec —
already implemented + tested in `src/ratings/elo.py`, K = 250/(m+5)^0.4, slam ×1.1, surface
blend). Add Weighted Elo (margin-of-victory by sets/games — Angelini & Candila 2022; cross-check
numbers against the welo R package). Then serve/return Bayesian aggregates from Sackmann's
nine per-match serve stats — the UFC pipeline's shrinkage machinery (prior toward
surface×tour mean, K tuned on walk-forward loss) maps one-to-one. Skip point-level
Markov/Stan models initially: verified to lag Elo pre-match (doc 01); revisit only as the
in-play foundation much later.

**Market anchor.** Train WITH market features (devigged opening + latest price, odds-proportional
devig per doc 03) — verified as the only route to market parity; the model's job is the
residual, same as UFC v2.5's use of market logit. Two market features tennis adds that UFC
lacked at first: line movement so far (from our recorder) and limit level (Pinnacle
maxRiskStake — books reveal confidence through limits).

**Two models, not one.** ATP and WTA separately (women's serve stats only complete from ~2016;
intransitivity and noise profiles differ; mirrors the UFC men's/women's split that already
works). Challenger matches go in the ATP training pool with a tier feature; ITF excluded.

**Labels and retirement.** Win-prob model trains on completed matches (drop W/O + pre-1-set
RET per the score-code policy in doc 02). A separate light retirement-hazard model (per-player
recent RET/W/O history, age, recent MTO-heavy matches if available) feeds the venue-EV layer —
not the win-prob model.

**Betting layer.** Venue-aware EV via doc 03's decomposition (the same probability prices
differently at Pinnacle vs Stake vs Polymarket); EV gate evaluated on raw vig-inclusive prices
(the UFC convention — conservative, must clear the actual vig); FLB-asymmetric minimum-EV
thresholds by odds bucket (dogs need a bigger modeled edge than favorites — doc 03); fractional
Kelly (~0.3×) with the UFC sigma-style uncertainty haircut concept — Sipko and the GNN paper
both prove uncertainty/subset gating is where tennis profit lives — extended with
push-probability renormalization for void-rule books.

**Execution venues (initial).** Anchor: Pinnacle (manual bets; crypto rails outside Ontario,
pinnacle.ca fiat if Ontario — province check is step one of Phase 4). Secondary: Cloudbet
(API automation, mid-margin — model anchored to sharper prices picks it off when its line
lags), SX Bet + Polymarket (API, near-zero fees, favorable action rules, depth to be sampled).
Brokers (Sportmarket/AsianConnect) when volume justifies PS3838-class limits with automation.
BC.Game skipped (license risk, unverifiable rules). Betfair impossible (Canada).

**Ops cadence.** Tennis is daily, not UFC's biweekly: the master notebook pattern becomes a
small daily routine — refresh results (Sackmann/OnCourt), recorder runs continuously on cron,
predictions generated each morning for the next ~36h of matches, bets placed manually
(Pinnacle) + via API (Cloudbet/SX/Polymarket) where edges clear the gate, everything logged.
Match volume (~60 ATP+WTA main-tour matches/week in season) is the portfolio advantage over
UFC (~13 fights/fortnight): more bets, faster feedback, tighter CLV statistics.

## What we deliberately do NOT build (and why)

- **In-play engine** — latency wall (docs 02/03). Phase 5+ at most, slow-market angles only.
- **ITF betting** — $150–450 limits + integrity tail; not worth bankroll risk.
- **Scraper warfare on protected sites** — Sofascore/Flashscore only as monitoring fallbacks;
  the model runs on Sackmann/tennis-data/OnCourt + book APIs.
- **A devig-based EV gate** — feature-devig yes, but the bet gate stays raw-odds (UFC lesson).
- **Buying picks/SaaS** — MatchSignal-class products sell unverifiable signals; we build assets.

## Carry-overs from UFC (direct ports)

| UFC asset | Tennis equivalent |
|---|---|
| Bayesian feature shrinkage + K tuning | serve/return aggregates with surface×tour priors |
| Red/blue symmetric pairwise training | A/B rows with RANDOMIZED sides (winner-first sources!) |
| Calibration on walk-forward OOF preds | same, per tour |
| EV on raw odds + delta_udog asymmetry | same + FLB-bucket thresholds |
| Sigma uncertainty rubric → stake haircut | uncertainty gate (data-completeness flags: short history, qualifier, long layoff, tier jump, retirement-risk) |
| CLV tracking vs Pinnacle close | CLV vs OWN captured closes (free Pinnacle closes are dead) |
| Betting history builder | same one-command pattern, multi-venue with rule-aware settlement |
| Studies workflow (src/eda + docs/studies) | identical conventions already scaffolded |

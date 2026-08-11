# Roadmap

Each phase ends with an explicit verify step (no phase is "done" without it).
Status as of 2026-06-10: **Phase 0 complete, Phase 1 partially complete.**

## Phase 0 — Scaffold + research ✅ (2026-06-10)
- [x] Repo structure, env shim, conda spec, CLAUDE.md conventions
- [x] Research: academic landscape (verified), data/tools, books/rules, microstructure, gaps
  → docs/01–05 + raw archives in docs/research_raw/
- [x] Working downloaders (Sackmann, tennis-data.co.uk) — live-verified
- [x] Surface-blend Elo (538 spec incl. slam K×1.1) + betting math — 16 tests passing
- [x] End-to-end smoke: ATP 2023–2025 walk-forward log loss 0.638 / acc 0.629

## Phase 1 — Data foundation
- [ ] Full backfill: Sackmann ATP+WTA 1990–2026 (+ qual_chall for Challenger tier), tennis-data
  2001–2026 ATP / 2007–2026 WTA
- [ ] Loader hardening: score-code policy (strip + {W/O, Walkover, RET, DEF…} sets — see doc 02),
  Davis Cup exclusion flag, tourney_level filter
- [ ] Name crosswalk: Sackmann player_id ↔ tennis-data names, versioned mapping file, loud
  unmatched warnings (target ≥99.5% odds-join rate on 2015+ main tour)
- [ ] **Odds recorder v1 (DAY ONE asset)**: cron-driven capture of Pinnacle guest API (odds +
  maxRiskStake) + the-odds-api free tier for our books → SQLite/parquet with timestamps
- [ ] Decide province question (Ontario vs not) → determines Pinnacle crypto rails + which
  crypto books are even legal; verify Cloudbet signup; sample SX/Polymarket tennis depth via API
- [ ] Optional: OnCourt license (~€49, USDT) + .mdb reader spike; bettingiscool 1-month (€49)
  spike to evaluate 2021–2025 Pinnacle movement backfill
- **Verify:** reproduce published Elo benchmark — full-history Elo walk-forward on 2014 ATP
  season ≈ 70% accuracy / ~0.59 log loss (Kovalchik's Table 4 number for the 538 spec); odds
  join coverage report; recorder runs 7 consecutive days without gaps.

## Phase 2 — Features
- [ ] Serve/return Bayesian aggregates (UFC-style shrinkage; surface×tour priors; K tuned
  walk-forward) — ATP first, WTA with 2016+ stat-era handling
- [ ] Schedule/fatigue block (days-since, games/sets last 7/14d, on-court time in event)
- [ ] H2H with shrinkage; rank/points diffs; tier feature (tour vs Challenger)
- [ ] Market features: odds-proportional devig of open + latest captured price; line-movement-so-far;
  Pinnacle limit level
- [ ] Retirement-hazard model v0 (per-player RET/W-O history, age)
- [ ] Symmetric A/B training frame with randomized sides (winner-first leak check = the FIRST test)
- **Verify:** each feature block's marginal walk-forward Δlog-loss reported vs Elo+market base;
  leak tests (shuffle-date and side-assignment tests) pass.

## Phase 3 — Models + calibration
- [ ] LR baseline (few diffs) → LightGBM full frame → AutoGluon port of UFC v2.5 setup;
  ATP and WTA separately
- [ ] Walk-forward eval harness: expanding window, per-era metrics, calibration curves,
  log loss vs devigged close AND vs devigged open
- [ ] Calibration fit on walk-forward OOF only
- **Verify:** model beats Elo+market baseline OOS; calibration slope ∈ [0.9, 1.1] per tour;
  beats-the-open on a held-out era (beating the close is NOT required to proceed — selective
  subsets are the goal, per doc 01).

## Phase 4 — Betting layer + paper trading
- [ ] Venue-EV (rule-aware formulas), FLB-asymmetric thresholds, uncertainty gate
  (sigma-rubric port), fractional Kelly with push renormalization + caps
- [ ] config/books.yaml finalized after account-level verification (rules quotes, real limits,
  actual margins measured from our own recorder)
- [ ] Bet log + CLV-vs-own-close + settlement-rule-correct backtester
- [ ] **4–8 weeks paper trading** across the in-season calendar
- **Verify:** paper CLV vs own captured closes > 0 with n ≥ 200 gated bets; realized paper ROI
  within CI of backtest expectation; only then real stakes (small).

## Phase 5 — Scale + research lanes (post-live)
- [ ] Studies (src/eda + docs/studies, UFC conventions): FLB by tier/tour; open-vs-close
  magnitude by tier from our recorder; scheduling angles; Challenger-focused model;
  rule-premium quantification (the doc 04 Tier-2 lanes)
- [ ] Cloudbet/SX/Polymarket API execution automation; broker evaluation at volume
- [ ] WTA intransitivity-class features; women's model parity audit
- [ ] In-play: reassess the latency landscape only after pre-match is profitable

## Standing data-ops rules (from day one)
- Recorder uptime is sacred — every missed day is unrecoverable proprietary data.
- Sackmann is NOT assumed fresh (2025 hiatus precedent) — freshness check + OnCourt/TML fallback.
- Any backtest crossing Oct 2025–Jan 2026 must handle the PSW→BFE sharp-reference splice explicitly.

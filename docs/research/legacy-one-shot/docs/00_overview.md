> HISTORICAL LLM RESEARCH — unapproved seed material, preserved from the inherited one-shot output. Claims of verification, decisions, phases, deadlines, and exclusions below are the prior LLM's assertions, not current project policy or an approved roadmap. Paths below describe the old repository layout; start at the archive index.

# Tennis-predictions — Research Overview & Index

*Project kicked off 2026-06-10. Everything below was produced by two multi-agent research
workflows (170 agents total, ~2,400 web fetches/searches) with adversarial verification of
decision-critical claims, plus hands-on verification (every downloader in this repo was run
against the live sources; the Elo baseline was smoke-tested on real 2023–2025 ATP data).*

## Executive summary

**The thesis.** Tennis is the right next sport for this betting program: two-player, deep liquid
markets, vastly better public data than MMA (every match since 1968 with serve stats since
1991, free), ~60 main-tour matches a week for fast feedback — and a verified academic consensus
that mirrors the UFC experience: the market is the best forecaster, nobody beats it head-on, and
all published profit comes from betting selective subsets where the market is structurally
blind. The UFC pipeline's discipline (market-anchored models, calibration, EV gating,
uncertainty-haircut Kelly, CLV tracking) is precisely the unproductized methodology.

**The five load-bearing discoveries:**
1. **Free Pinnacle tennis closing odds died in Feb 2026** (OddsPortal delisted Pinnacle;
   tennis-data.co.uk's PSW columns are 94.5% blank in 2026, Betfair-Exchange columns quietly
   replaced them). Nobody sells timestamped open→close tennis line history. **Recording our own
   odds from day one is the single highest-value, near-zero-cost asset.**
2. **Settlement rules differ per book and nobody prices them**: retirements ended a record 4.8%
   of 2025 ATP matches; verified rules range from void-on-retirement (Stake, Bookmaker.eu)
   through one-set-action (Pinnacle, BetOnline, Cloudbet, SX) to Polymarket's
   advancing-player-wins + walkover-50-50. Rule-aware EV + a retirement-hazard model is a
   genuinely novel edge layer.
3. **The bettor's province decides the book menu**: Ontario is geo-blocked by most crypto books
   and gets fiat-only Pinnacle; the rest of Canada gets crypto Pinnacle + the full crypto set.
   Betfair is blocked for all Canadians. (Phase-1 decision point.)
4. **The verified model hierarchy**: bookmaker consensus 72% / FiveThirtyEight-Elo 70% (exact
   spec implemented + tested in this repo) / best ML ~70% — and the only verified recent
   profitable result (+3.26% ROI, 1,903 Pinnacle bets, 2023–2025) bet ONLY high-intransitivity
   matchups. Selectivity is the product.
5. **Every consumer tool is built backwards for us**: scanners define value as soft-book
   deviation FROM Pinnacle (BetBurger's own data: ~1 valuebet at Pinnacle vs 711 surebets);
   no tracker syncs Pinnacle/crypto books; open-source repos are stale, random-split, and
   retirement-blind. The market-maker-only quant workflow exists nowhere — we build it.

## Reading order

| Doc | Contents |
|---|---|
| [01_academic_landscape.md](01_academic_landscape.md) | Verified literature: model hierarchy, exact Elo spec, profitability precedents, in-play/momentum evidence, leak-detection lessons |
| [02_data_and_tools.md](02_data_and_tools.md) | Sackmann ecosystem (incl. the 2025 hiatus + score-code taxonomy), tennis-data odds (incl. the Pinnacle-column death), odds APIs, OnCourt, point-by-point wall, package landscape |
| [03_market_structure.md](03_market_structure.md) | Book-by-book table (crypto/margins/limits/APIs/winner-tolerance/Canada), settlement-rule classes + venue-EV math, microstructure (line origination, open-vs-close, FLB, CLV nuance, ITIA integrity by tier) |
| [04_gaps_and_opportunities.md](04_gaps_and_opportunities.md) | The gap analysis: 9 ranked gaps with solution shapes; what we deliberately skip |
| [05_proposed_solution.md](05_proposed_solution.md) | System architecture + component decisions + UFC carry-over map |
| [roadmap.md](roadmap.md) | Phases 0–5 with verify gates; Phase 0 complete |
| [research_raw/](research_raw/) | Full structured fact archives per research angle, with per-fact sources and adversarial verification verdicts (incl. refuted-and-corrected claims) |

## What already runs (Phase 0, verified)

```bash
conda env create -f environment.yml          # one-time
./python.sh src/ingest/download_sackmann.py --tour atp --start 2023 --end 2025
./python.sh src/ingest/download_tennis_data_couk.py --tour both --start 2024 --end 2026
./python.sh src/eda/smoke_elo_walkforward.py # -> log loss 0.638, acc 0.629, Sinner #1
./python.sh -m pytest                        # 16 tests
```

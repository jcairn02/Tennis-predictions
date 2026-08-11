# Tennis-predictions

Tennis match outcome prediction for betting at market-maker sportsbooks (crypto-funded).
Sister project to [UFC-Predictions](../UFC-Predictions/) — same philosophy, ported to a sport
with far richer public data and a deeper market: temporally-valid features, calibrated
probabilities, expected-value gating on raw odds, fractional-Kelly staking with uncertainty
haircuts, and closing-line-value tracking.

**Status (2026-06-10):** Phase 0 complete — research + working scaffold. See
[docs/00_overview.md](docs/00_overview.md) for the executive summary and reading order, and
[docs/roadmap.md](docs/roadmap.md) for what's next.

## Why tennis, in one paragraph

Two-player sport (the UFC modeling experience transfers), free canonical data (every pro match
since 1968, serve stats since 1991, free closing odds since 2001), ~60 main-tour matches a week
(fast feedback, tight statistics), and a verified research consensus that rewards exactly the
discipline this program already practices: the market is the best public forecaster, and the
only published profits come from betting *selective subsets* where the market is structurally
blind — uncertainty-gated, settlement-rule-aware, market-anchored betting. Two genuinely novel
layers surfaced by the research: nobody records tennis opening→closing line history anymore
(free Pinnacle closes died Feb 2026 — we capture our own from day one), and nobody prices
per-book retirement settlement rules (4.8% of 2025 ATP matches ended in retirement; rules
verified to differ across our books).

## Quickstart

```bash
conda env create -f environment.yml      # one-time: creates the `tennis` env
./python.sh -m pytest                    # 16 tests (Elo + betting math)
./python.sh src/ingest/download_sackmann.py --tour atp --start 2023 --end 2025
./python.sh src/ingest/download_tennis_data_couk.py --tour both --start 2024 --end 2026
./python.sh src/eda/smoke_elo_walkforward.py
# -> 9,006 matches, walk-forward log loss 0.638 / accuracy 0.629 (post burn-in),
#    top Elo: Sinner, Alcaraz, Djokovic — the spine works end to end.
```

## Layout

```
docs/            research reports 00-05 + roadmap + raw research archives (research_raw/)
config/          books.yaml — verified per-book crypto/limits/settlement-rule facts
src/ingest/      downloaders (live-verified) + chronological match loader
src/ratings/     surface-blended Elo, FiveThirtyEight spec (verified vs Kovalchik 2016)
src/betting/     EV / fractional Kelly / CLV math (decimal-odds-native)
src/features/    (stubs — Phase 2)   src/models/  (stubs — Phase 3)
src/eda/         scratch + study scripts
test/            pytest suites
data/raw/        downloaded source data (gitignored; rebuild via src/ingest/)
scripts/         notebooks only (none yet)
```

`CLAUDE.md` carries the working conventions (env shim, git policy, file-placement rules,
core principles). Read it before contributing.

# src/features/ — planned interfaces (stubs)

Implemented in the Phase 2 milestone (see docs/roadmap.md). Planned modules:

- `serve_return.py` — rolling/Bayesian-shrunk serve & return aggregates from Sackmann
  per-match stats (1st-in %, 1st/2nd-won %, ace & DF rates, break points saved/converted;
  return mirrors). Same prior philosophy as the UFC pipeline's Bayesian feature averages:
  shrink small samples toward a (surface, tour)-level prior; tune K on walk-forward loss.
- `schedule_fatigue.py` — days since last match, matches/sets/games played in last 7/14 days,
  time-on-court accumulation in current event, back-to-back-week flags, travel/timezone proxy.
- `head_to_head.py` — H2H counts/win rate with shrinkage (raw H2H is noisy and overrated).
- `market.py` — market-derived features from tennis-data odds (devigged close as the
  market-probability feature, open-vs-close drift once an odds-capture pipeline exists).
  NOTE: devig here is for FEATURES; the EV gate in src/betting/ stays vig-inclusive.
- `build_training_frame.py` — assemble symmetric A-vs-B difference rows. Side assignment
  MUST be randomized (sources are winner-first; using file order leaks the label).

Every feature: computed strictly from data dated BEFORE the match (temporal validity).

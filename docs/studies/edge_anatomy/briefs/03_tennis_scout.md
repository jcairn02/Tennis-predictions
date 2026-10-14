## Your role: the tennis-signal scout (round 1)

(The shared context in `00_shared_context.md` comes first in your prompt.)

Your question: **which tennis information is plausibly NOT priced by the 2025–26 closing line, and why?** A signal is a good candidate when there is a mechanism for the market to miss it now: it is hard to compute, slow to update, under-weighted by the bettors who move the line, newly available, or created by a recent change in the sport (2025–26 rule, ball, court-speed, calendar or scheduling changes, the growth of Challenger and WTA 125 events, new players, injuries and returns). Signals the earlier studies found priced (surface Elo, surface statistics, rating systems, momentum, streaks, shot-level rates) need a new angle to be listed.

Cover:
1. **10–20 candidate signals, ranked.** For each: the mechanism; why the 2025–26 close might miss it (and the strongest reason it might not); the data the repository holds for it (paths: `data/data_map.yaml`, `docs/studies/feature_universe/universe.csv` and its U-ids, the serve-speed panel under `data/studies/serve_speed_tabpfn/live/`, the official point feeds, the lower-level box scores, the match-timing table, the odds tables); earlier evidence in the repository with its direction key; and a cheap test against the 2025–26 close with its likely resolution.
2. **The owner's thesis.** He expects the edge in point-by-point and per-statistic offence/defence profiles. Say which candidates fit it, which do not, and whether the evidence so far supports it.
3. **What is surely priced.** A short list of tennis information you would expect any 2025–26 closing line to hold already, with the reason, so the team stops spending effort there.
4. **What would need new data,** with the source and the cost (the scraping approval in `CLAUDE.md` covers publicly served data).

Write your memo to `docs/studies/edge_anatomy/team/tennis_scout.md`.

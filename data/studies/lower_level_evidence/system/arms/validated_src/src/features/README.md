# Feature work

Reserved home; no feature interfaces or implementation milestone are approved. [Inherited suggestions](../../docs/research/legacy-one-shot/src/features/README.md) are archived. New studies belong in `src/eda/` and `docs/studies/` until their role is decided.

One rule is decided ([the match clock, 5 Oct 2026](../../docs/decisions/2026-10-05-match-timing.md)). A feature that lets one player's result reach another player's inputs must read the leak-proof timeline: a result counts only from the day after its latest possible finish, and a match reads the state of its earliest possible start. This covers ratings solved together, smoothed ratings and statistics of a field. The timeline is `data/studies/match_timing/timing.parquet`, built by `src/eda/match_timing/timing.py`. The leak-proof IOS solver is `src/eda/match_timing/ios_time.py`, and the leak-proof TrueSkill Through Time is `ttt_pass_timed` in `src/eda/rating_systems/ratings.py`.

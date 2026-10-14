# Ideas to test

Future ideas that look promising enough to test, kept in one place. Each is a suggestion, not a decision; decisions go in [docs/decisions/](../docs/decisions/README.md).

* Score every idea against both stages of the [current best model](../docs/decisions/2026-10-07-speed-nudge.md), never the TabPFN fit alone.
* Once an idea is tested, move it to **Tested** as one line: the verdict and a link to its report in `docs/studies/`.

## Open

- [ ] **Run a cheap test of the opponent-adjusted version of `points_52w`.** Added 8 Oct 2026, from the [event levels study](../docs/studies/event_levels/README.md#what-it-means).
  - **Why:** the study found `points_52w` (Stage 4's `mu_points|52 weeks`) is the one model input built from raw rates. The same players win more points at Challengers, against weaker opponents, so a Challenger-heavy year inflates it.
  - **Versions to try:**
    1. Stage 4's existing `mu_points|adjusted` in `studies/predictability_diagnostic/stage4_features.parquet`. It adjusts for the opponents faced, but over the whole career, not 52 weeks.
    2. A 52-week adjusted form. It needs no new data: `history_sums` in [stage4_features.py](../src/eda/predictability_diagnostic/stage4_features.py#L564) already keeps the adjusted sums from before the last 52 weeks.
  - **Test:** swap each version in for `points_52w` (the model's copy is built by [`rebuild.points_52w`](../src/eda/match_timing/rebuild.py#L115)) and score it against both stages.

## Tested

None yet.

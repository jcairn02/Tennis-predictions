# Latency follow-up: can the speed signal stay predictive when speeds arrive late?

**Written by the lead on 7 October 2026, before any computation of this follow-up.** The scenarios and readings below are fixed now. Everything here is **exploratory**:
* 2024–2026 results were opened by the pre-registered test (look ledger row 34);
* nothing here can change that test's result or the owner's decision of 7 Oct (`docs/decisions/2026-10-07-speed-nudge.md`).

## The owner's question (7 Oct 2026)

> "This is a huge issue and changes the value of what we are doing. I didnt understand this. If we CANT get the speed reading in time, is there a way to make it still predictive?"

**The issue.** The backtest let a match's speed reach the next match's feature from `lf + 1`, the day after it surely finished. At bet time, today's sources arrive later:
* **ManTennisData** (all tour-level speeds from 2025 on) is scraped from the ATP's pages and published **every Sunday**;
* **the Slam feeds** are collected **after each event** (download-cadence decision of 6 Oct).

**Observed, values only.** In men's 2024–26 test matches, 53% of players' latest speed reading was within 7 days of the match, and 31% within 1 day.

## Availability scenarios (fixed now)

Each panel row gets a day from which it may enter any feature: the filter's history and the as-of edition offsets alike.

| Id | Scenario | Rule |
|---|---|---|
| **A** | Instant (the backtest as run) | `lf + 1` |
| **B** | **Today's sources, going forward** | **Tour level and Challengers** (key statistics and any non-Slam row): the first weekly ManTennisData publication after the match. The engineer fixes the exact weekday and hour rule from the repository's commit history, read-only; if that cannot be established, the next Sunday after `lf`, usable from the Monday. **Slams** (every Slam source): the day after the event's last main-draw day, + 2 days for collection. **Box scores** (Tennis My Life, downloaded daily): `lf + 1` |
| L1, L3, L7, L14 | Fixed lags | `lf + 1 + L` days for every speed row (sensitivity) |

Scenario B applies the going-forward cadence to every season, including 2024–25. It does not apply the accidents of history (ManTennisData's autumn-2025 backfill), because the question is what a live system would have from now on.

## Methods under each scenario (fixed now)

| Id | Method |
|---|---|
| **M0** | The study's feature as built (`spd_f`), recomputed on the rows available under the scenario. Constants and the 14-day half-life unchanged |
| M1 | As M0, with the filter's half-life (and only it) re-tuned for the scenario. Result-free: next-match speed on ≤ 2022, checked on 2023, as in R1 |
| **M2** | **Nowcast fill.** A history match whose speed is not yet available but whose box score is (aces, double faults, first serves in, first- and second-serve points won, service points) enters the filter as a speed estimate from its box score, with its own, larger noise variance. Estimated within player and result-free on ≤ 2022, checked on 2023. The modeller designs it and documents it before the outcome run |

## Readings

1. **Result-free first** (≤ 2023 statistic targets), for every scenario × method:
   * the within-match A − B next-match speed difference (the auditor's T1);
   * the mechanism gate with edition fixed effects (first-serve points won, service points won, aces; per SD).
   * How much of scenario A's information survives?
2. **Feature values, 2024–26** (no outcomes): the correlation of each variant with A's `spd_f` and its SD; men.
3. **Exploratory outcome reading, men 2024–26** (the owner's "is it still predictive").
   * The walk-forward nudge (S9's shrunk and unshrunk formulas, refitted per variant on 2019..Y−1), against the calibrated base. mLL, positive = the nudge better, block interval.
   * S0's information test for each variant, in log-odds per unit of the variant's own column.
   * **The headline comparisons, fixed now:**
     * B-M0, today's sources with no fix;
     * B-M2, today's sources with the nowcast;
     * each against A (the +0.41 of the study).
   * Everything else is descriptive. The instant variant must first reproduce S9 exactly (+0.41 [+0.04, +0.78] shrunk) as a check of the harness.
4. The run that reads outcomes happens **once**, after the variants are built and checked. It is logged in the look ledger.
